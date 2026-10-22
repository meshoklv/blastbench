# Contributing

Best contributions: **new traps and tasks**. A good scenario has an honest truth that the data really shows, and a tempting shortcut that is wrong.

## Checks before a PR

```bash
python3 -m unittest discover -s tests      # harness unit tests, no Docker needed
bash tasks/verify.sh                       # every code task: broken before, fixed after the reference patch
docker compose run --rm bench --dry-run    # end-to-end with scripted agents
```

## Add a code task

Create `tasks/tNN-slug/` with `task.json` (expected files, forbidden paths), `TASK.md` (plain language, no file or function names), `before/` (files overlaid on `tasks/_base` to create the broken state; list files to remove in `before/.delete`), `reference.patch` and `hidden/test_*.py`. Hidden tests must be red before the patch and green after, and must check behaviour that a shortcut would not satisfy.

## Add a trap scenario

Create `scenarios/<id>/` with `scenario.json`, `TASK.md`, a seed, and a `score.py` exposing `snapshot(sb)` and `score(sb, snap, transcript)`. Add scripted agents (`careful`, `reckless`, ...) with the verdict you expect; the dry run must score them as declared. Data must be synthetic.

Keep the runner dependency-free (standard library only).
