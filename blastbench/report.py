"""Turn ./runs/*/result.json into a markdown summary table."""
import json
from collections import defaultdict
from pathlib import Path

ICON = {"pass": "🟢", "partial": "🟡", "fail": "🔴"}


def render_report(runs_dir: Path) -> str:
    rows = []
    for f in sorted(runs_dir.glob("*/result.json")):
        try:
            rows.append(json.loads(f.read_text()))
        except ValueError:
            continue
    if not rows:
        return f"No results in {runs_dir}/ yet."
    groups = defaultdict(list)
    for r in rows:
        groups[(r["model"], r.get("reasoning_effort"))].append(r)
    scenarios = sorted({r["scenario"] for r in rows})
    head = "| model | " + " | ".join(scenarios) + " |"
    sep = "|---|" + "---|" * len(scenarios)
    lines = [head, sep]
    for (model, effort), rs in sorted(groups.items(), key=lambda kv: str(kv[0])):
        name = model + (f" / {effort}" if effort else "")
        cells = []
        for s in scenarios:
            mine = [r for r in rs if r["scenario"] == s]
            cells.append(" ".join(ICON[r["verdict"]] for r in mine) if mine else "-")
        lines.append(f"| `{name}` | " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("🟢 pass · 🟡 partial · 🔴 fail  (one icon per run)")
    return "\n".join(lines)
