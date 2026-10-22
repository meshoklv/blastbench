#!/usr/bin/env python3
"""Tiny command-execution server that lives inside the sandbox container.

It is reachable only over the compose-internal network. The first caller claims it
with a secret token (the runner does this before any untrusted process exists); after
that every request must carry the token, so the agent's own processes cannot use it.

Endpoints (JSON unless noted):
  GET  /health
  POST /claim   {token}
  POST /exec    {cmd, user, timeout, cwd}        -> {rc, out, timed_out}
  POST /put_tar ?dir=&user=[&private=1]  (body: tar bytes) -> {rc, out}
  POST /reset   {}                               -> kills every process of the agent user
  POST /shutdown {}                              -> stops the server (container exits, next run is fresh)
"""
import json
import os
import pwd
import signal
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

MAX_OUT = 60_000
STATE = {"token": None}
LOCK = threading.Lock()
ALLOWED_USERS = {"agent", "postgres"}


def demote(user, cwd):
    """Drop privileges first, then chdir: root has no DAC_OVERRIDE, so it could not enter a private dir."""
    pw = pwd.getpwnam(user)

    def fn():
        os.setgroups([])
        os.setgid(pw.pw_gid)
        os.setuid(pw.pw_uid)
        try:
            os.chdir(cwd)
        except OSError:
            os.chdir("/")

    return fn


def env_for(user):
    pw = pwd.getpwnam(user)
    return {
        "PATH": "/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin",
        "HOME": pw.pw_dir,
        "USER": user,
        "LANG": "C.UTF-8",
        "TERM": "dumb",
        "PAGER": "cat",
        "GIT_PAGER": "cat",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PGHOST": "127.0.0.1",
    }


def clip(data: bytes) -> str:
    text = data.decode("utf-8", errors="replace")
    if len(text) > MAX_OUT:
        half = MAX_OUT // 2
        text = text[:half] + f"\n...[{len(text) - MAX_OUT} chars truncated]...\n" + text[-half:]
    return text


def run(cmd, user="agent", timeout=120, cwd="/work", stdin=None):
    if user not in ALLOWED_USERS:
        return {"rc": 126, "out": f"bad user {user}", "timed_out": False}
    try:
        proc = subprocess.Popen(
            ["bash", "-c", cmd],
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            cwd=None, env=env_for(user),
            preexec_fn=demote(user, cwd), start_new_session=True,
        )
    except OSError as exc:
        return {"rc": 127, "out": f"spawn failed: {exc}", "timed_out": False}
    timed_out = False
    try:
        out, _ = proc.communicate(input=stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        timed_out = True
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        out, _ = proc.communicate()
    return {"rc": proc.returncode, "out": clip(out or b""), "timed_out": timed_out}


def kill_agent_processes():
    uid = pwd.getpwnam("agent").pw_uid
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            if os.stat(f"/proc/{entry}").st_uid == uid:
                os.kill(int(entry), signal.SIGKILL)
        except (ProcessLookupError, PermissionError, FileNotFoundError):
            pass


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args):  # keep the container log quiet
        pass

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return self.rfile.read(n) if n else b""

    def _authorized(self):
        tok = STATE["token"]
        return tok is not None and self.headers.get("Authorization") == f"Bearer {tok}"

    def do_GET(self):
        if self.path == "/health":
            return self._send(200, {"ok": True, "claimed": STATE["token"] is not None})
        self._send(404, {"error": "not found"})

    def do_POST(self):
        url = urlparse(self.path)
        raw = self._body()
        if url.path == "/claim":
            with LOCK:
                if STATE["token"] is not None:
                    return self._send(403, {"error": "already claimed"})
                try:
                    token = json.loads(raw)["token"]
                except (ValueError, KeyError):
                    return self._send(400, {"error": "token required"})
                if len(token) < 16:
                    return self._send(400, {"error": "token too short"})
                STATE["token"] = token
            return self._send(200, {"ok": True})
        if not self._authorized():
            return self._send(401, {"error": "unauthorized"})
        if url.path == "/exec":
            req = json.loads(raw or b"{}")
            res = run(req["cmd"], req.get("user", "agent"), int(req.get("timeout", 120)),
                      req.get("cwd", "/work"))
            return self._send(200, res)
        if url.path == "/put_tar":
            q = parse_qs(url.query)
            dest, user = q["dir"][0], q.get("user", ["agent"])[0]
            umask = "077" if q.get("private") else "022"
            res = run(f"umask {umask} && mkdir -p '{dest}' && tar -x -C '{dest}'", user, 60, "/",
                      stdin=raw)
            return self._send(200, res)
        if url.path == "/shutdown":  # one sandbox per runner invocation: the next run starts clean
            self._send(200, {"ok": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if url.path == "/reset":
            kill_agent_processes()
            return self._send(200, {"ok": True})
        self._send(404, {"error": "not found"})


if __name__ == "__main__":
    srv = ThreadingHTTPServer(("0.0.0.0", 8080), Handler)
    print("exec server ready", file=sys.stderr, flush=True)
    srv.serve_forever()
