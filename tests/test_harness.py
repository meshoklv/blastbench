"""Unit tests for the harness itself (no Docker, no network, no model)."""
import json
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from blastbench.agent import LLM, run_agent  # noqa: E402
from blastbench.cli import build_parser, main  # noqa: E402
from blastbench.report import render_report  # noqa: E402
from blastbench.scenarios import load_all  # noqa: E402


class FakeSandbox:
    def __init__(self):
        self.ran = []

    def exec(self, cmd, user="agent", timeout=120, cwd="/work"):
        self.ran.append(cmd)
        return {"rc": 0, "out": "hello\n", "timed_out": False}


def serve(replies):
    """Minimal OpenAI-compatible server that returns the given chat completions in order."""
    queue = list(replies)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            body = json.dumps(queue.pop(0)).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def completion(content=None, tool_calls=None):
    msg = {"role": "assistant", "content": content}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return {"model": "fake-model-2026-01", "choices": [{"message": msg}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5}}


class AgentLoop(unittest.TestCase):
    def test_tool_call_then_final_answer(self):
        call = {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": "echo hi"})}}
        srv = serve([completion(tool_calls=[call]), completion("All done.")])
        llm = LLM(f"http://127.0.0.1:{srv.server_port}", "k", "fake")
        sb = FakeSandbox()
        t = run_agent(llm, sb, "do the thing", max_steps=5, log=lambda *_: None)
        srv.shutdown()
        self.assertEqual(sb.ran, ["echo hi"])
        self.assertEqual(t["stop"], "finished")
        self.assertEqual(t["commands"], ["echo hi"])
        self.assertEqual(t["assistant_text"], ["All done."])
        self.assertEqual(t["usage"], {"prompt_tokens": 20, "completion_tokens": 10})
        self.assertEqual(llm.served_model, "fake-model-2026-01")

    def test_malformed_tool_arguments_do_not_crash(self):
        call = {"id": "c1", "type": "function", "function": {"name": "bash", "arguments": "not json"}}
        srv = serve([completion(tool_calls=[call]), completion("ok")])
        llm = LLM(f"http://127.0.0.1:{srv.server_port}", "k", "fake")
        sb = FakeSandbox()
        t = run_agent(llm, sb, "x", max_steps=5, log=lambda *_: None)
        srv.shutdown()
        self.assertEqual(sb.ran, [])
        self.assertEqual(t["stop"], "finished")

    def test_max_steps(self):
        call = {"id": "c", "type": "function", "function": {"name": "bash", "arguments": json.dumps({"command": "true"})}}
        srv = serve([completion(tool_calls=[call])] * 3)
        llm = LLM(f"http://127.0.0.1:{srv.server_port}", "k", "fake")
        t = run_agent(llm, FakeSandbox(), "x", max_steps=3, log=lambda *_: None)
        srv.shutdown()
        self.assertEqual(t["stop"], "max_steps")


class Scenarios(unittest.TestCase):
    def test_all_scenarios_load(self):
        found = load_all()
        self.assertIn("ledger-cleanup", found)
        self.assertGreaterEqual(len([s for s in found.values() if s.kind == "code"]), 6)
        for s in found.values():
            self.assertTrue(s.prompt.strip(), s.id)
            self.assertTrue(s.scripted, f"{s.id} has no scripted dry-run agents")

    def test_cli_parses_bare_flags_as_run(self):
        args = build_parser().parse_args(["run", "--model", "a,b", "--repeat", "2"])
        self.assertEqual(args.model, ["a,b"])
        self.assertEqual(args.repeat, 2)

    def test_list_command(self):
        self.assertEqual(main(["list"]), 0)


class Report(unittest.TestCase):
    def test_report_table(self):
        with tempfile.TemporaryDirectory() as d:
            for i, verdict in enumerate(["pass", "fail"]):
                run = Path(d) / f"r{i}"
                run.mkdir()
                (run / "result.json").write_text(json.dumps(
                    {"model": "m1", "reasoning_effort": "high", "scenario": "ledger-cleanup", "verdict": verdict}))
            out = render_report(Path(d))
        self.assertIn("`m1 / high`", out)
        self.assertIn("🟢 🔴", out)


if __name__ == "__main__":
    unittest.main()
