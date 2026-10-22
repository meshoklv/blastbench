"""Command line entry point: `python -m blastbench ...` (inside compose: `docker compose run bench ...`)."""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from . import __version__
from .agent import LLM, run_agent
from .report import render_report
from .sandbox import Sandbox
from .scenarios import ROOT, load_all


def _slug(s):
    return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")[:60] or "agent"


def _select(all_scenarios, wanted):
    if not wanted:
        return list(all_scenarios.values())
    missing = [w for w in wanted if w not in all_scenarios]
    if missing:
        raise SystemExit(f"unknown scenario(s): {', '.join(missing)}. See: list")
    return [all_scenarios[w] for w in wanted]


def _write_result(out_root, scenario, label, result, transcript, meta):
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    d = Path(out_root) / f"{stamp}__{scenario.id}__{_slug(label)}"
    n = 1
    while d.exists():
        n += 1
        d = Path(out_root) / f"{stamp}__{scenario.id}__{_slug(label)}__{n}"
    d.mkdir(parents=True)
    record = {"schema": "blastbench/result@1", "harness_version": __version__, "scenario": scenario.id,
              "kind": scenario.kind, **meta, **result}
    (d / "result.json").write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n")
    (d / "transcript.json").write_text(json.dumps(transcript, indent=2, ensure_ascii=False) + "\n")
    return d


ICON = {"pass": "PASS", "partial": "PARTIAL", "fail": "FAIL"}


def cmd_run(args):
    scenarios = _select(load_all(), args.scenario)
    sb = Sandbox(args.sandbox_url)
    sb.wait_ready()
    sb.claim()
    try:
        return _run(args, scenarios, sb)
    finally:
        sb.shutdown()  # the sandbox container stops; the next invocation gets a pristine one


def _run(args, scenarios, sb):

    jobs = []  # (label, scripted_name|None)
    if args.dry_run:
        jobs = [("__dry__", None)]
    else:
        models = [m for spec in (args.model or []) for m in spec.split(",") if m]
        if not models:
            raise SystemExit("give --model NAME (or --dry-run to exercise the harness without a model)")
        key = os.environ.get("LLM_API_KEY", "")
        if not key and not args.allow_no_key:
            raise SystemExit("LLM_API_KEY is empty. Put it in .env (see .env.example), "
                             "or pass --allow-no-key for local servers that need none.")
        jobs = [(m, None) for m in models]

    mismatches = 0
    rows = []
    for label, _ in jobs:
        for scenario in scenarios:
            variants = list(scenario.scripted.items()) if args.dry_run else [(None, None)]
            for vname, vdef in variants:
                for rep in range(args.repeat):
                    tag = f"dry:{vname}" if args.dry_run else label
                    print(f"\n== {scenario.id}  [{tag}]" + (f" run {rep + 1}/{args.repeat}" if args.repeat > 1 else ""))
                    sb.reset()
                    scenario.prepare(sb)
                    snap = scenario.snapshot(sb)
                    t0 = time.time()
                    if args.dry_run:
                        res = sb.exec(vdef["script"], user="agent", timeout=300)
                        transcript = {"commands": [vdef["script"]], "assistant_text": [vdef["say"]] if vdef["say"] else [],
                                      "steps": [{"step": 1, "text": vdef["say"],
                                                 "calls": [{"command": vdef["script"], "output": res["out"][:4000]}]}],
                                      "stop": "scripted", "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                                      "seconds": round(time.time() - t0, 1)}
                        meta = {"model": f"scripted:{vname}", "served_model": None, "reasoning_effort": None}
                    else:
                        llm = LLM(args.base_url, os.environ.get("LLM_API_KEY", ""), label,
                                  args.reasoning_effort, args.temperature)
                        transcript = run_agent(llm, sb, scenario.prompt, args.steps, args.timeout, args.cmd_timeout)
                        meta = {"model": label, "served_model": llm.served_model,
                                "reasoning_effort": args.reasoning_effort}
                    sb.reset()
                    result = scenario.score(sb, snap, transcript)
                    meta.update({"date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                 "steps": len(transcript.get("steps", [])), "usage": transcript.get("usage"),
                                 "seconds": transcript.get("seconds"), "stop": transcript.get("stop")})
                    d = _write_result(args.out, scenario, vname and f"dry-{vname}" or label, result, transcript, meta)
                    line = f"   -> {ICON[result['verdict']]}: {result['headline']}"
                    if result.get("flags"):
                        line += "  [" + "; ".join(result["flags"]) + "]"
                    print(line)
                    if args.dry_run:
                        expect = vdef["expect"]
                        ok = result["verdict"] == expect
                        mismatches += 0 if ok else 1
                        print(f"   expected {ICON[expect]}: {'ok' if ok else 'MISMATCH'}")
                    rows.append((scenario.id, tag, result["verdict"]))
    if args.dry_run:
        print(f"\nDry run finished: {len(rows) - mismatches}/{len(rows)} scripted agents scored as expected.")
        return 1 if mismatches else 0
    print("\nResults written to", args.out, "- summarise with: report")
    return 0


def cmd_list(args):
    for s in load_all().values():
        print(f"{s.id:34} {s.kind:5} {s.title}")
    return 0


def cmd_report(args):
    print(render_report(Path(args.out)))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="blastbench", description="Does your AI coding agent keep its blast radius small?")
    sub = p.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="run scenarios against a model (default command)")
    r.add_argument("--model", action="append", help="model name; repeat or comma-separate for several")
    r.add_argument("--scenario", action="append", help="scenario id (default: all); see `list`")
    r.add_argument("--repeat", type=int, default=1, help="runs per model and scenario (models are stochastic)")
    r.add_argument("--dry-run", action="store_true", help="no model: run scripted agents to validate the harness")
    r.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"))
    r.add_argument("--reasoning-effort", default=None, help="passed through as reasoning_effort")
    r.add_argument("--temperature", type=float, default=None)
    r.add_argument("--steps", type=int, default=40, help="max tool calls rounds")
    r.add_argument("--timeout", type=int, default=900, help="wall-clock seconds per run")
    r.add_argument("--cmd-timeout", type=int, default=120, help="seconds per shell command")
    r.add_argument("--allow-no-key", action="store_true")
    r.add_argument("--sandbox-url", default=os.environ.get("SANDBOX_URL", "http://sandbox:8080"))
    r.add_argument("--out", default=os.environ.get("BENCH_OUT", "runs"))
    r.set_defaults(fn=cmd_run)
    l = sub.add_parser("list", help="list scenarios")
    l.set_defaults(fn=cmd_list)
    rp = sub.add_parser("report", help="summarise ./runs as a markdown table")
    rp.add_argument("--out", default=os.environ.get("BENCH_OUT", "runs"))
    rp.set_defaults(fn=cmd_report)
    return p


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith("-") and argv[0] not in ("-h", "--help"):
        argv.insert(0, "run")
    args = build_parser().parse_args(argv)
    if not getattr(args, "fn", None):
        build_parser().print_help()
        return 2
    return args.fn(args)
