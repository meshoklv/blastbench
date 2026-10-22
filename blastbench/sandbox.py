"""HTTP client for the exec server that runs inside the sandbox container."""
import io
import json
import secrets
import tarfile
import time
import urllib.error
import urllib.request


class Sandbox:
    def __init__(self, url: str):
        self.url = url.rstrip("/")
        self.token = None

    # -- low level ---------------------------------------------------------
    def _req(self, path, data=None, raw=False, timeout=300):
        headers = {"Content-Type": "application/octet-stream" if raw else "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        body = data if raw else (json.dumps(data).encode() if data is not None else None)
        req = urllib.request.Request(self.url + path, data=body, headers=headers,
                                     method="POST" if body is not None else "GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())

    def wait_ready(self, seconds=90):
        deadline = time.time() + seconds
        last = None
        while time.time() < deadline:
            try:
                return self._req("/health", timeout=3)
            except (urllib.error.URLError, OSError, ValueError) as exc:
                last = exc
                time.sleep(1)
        raise RuntimeError(f"sandbox at {self.url} did not become ready: {last}")

    def claim(self):
        """First caller wins: later requests (including the agent's own) need the token."""
        self.token = secrets.token_hex(24)
        try:
            self._req("/claim", {"token": self.token})
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                "sandbox is already claimed by another run - "
                "restart it with `docker compose restart sandbox`") from exc

    # -- API ---------------------------------------------------------------
    def exec(self, cmd, user="agent", timeout=120, cwd="/work"):
        res = self._req("/exec", {"cmd": cmd, "user": user, "timeout": timeout, "cwd": cwd},
                        timeout=timeout + 30)
        return res

    def put_tree(self, files: dict, dest: str, user="agent", private=False):
        """files: {relative_path: bytes}. Extracted into dest as `user`."""
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as tar:
            for name, content in sorted(files.items()):
                info = tarfile.TarInfo(name)
                info.size = len(content)
                info.mode = 0o644
                info.mtime = 0
                tar.addfile(info, io.BytesIO(content))
        res = self._req(f"/put_tar?dir={dest}&user={user}{'&private=1' if private else ''}", buf.getvalue(), raw=True)
        if res["rc"] != 0:
            raise RuntimeError(f"upload to {dest} failed: {res['out']}")

    def shutdown(self):
        try:
            self._req("/shutdown", {}, timeout=10)
        except (urllib.error.URLError, OSError, ValueError):
            pass

    def reset(self):
        self._req("/reset", {})

    def psql(self, db, query, user="postgres"):
        """Run one SQL statement as a superuser over the local socket. Returns stdout text."""
        q = query.replace("'", "'\"'\"'")
        res = self.exec(f"psql -h /run/postgresql -d {db} -At -v ON_ERROR_STOP=1 -c '{q}'",
                        user=user, cwd="/")
        if res["rc"] != 0:
            raise RuntimeError(f"psql failed: {res['out']}")
        return res["out"].strip()
