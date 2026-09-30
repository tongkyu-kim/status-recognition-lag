#!/usr/bin/env python
"""Cross-platform task runner (equivalent to the Makefile; use where `make` is unavailable).

    python tasks.py test
    python tasks.py pipeline
    python tasks.py clean-derived --yes
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def script(name: str, *args: str) -> list[str]:
    return [PY, str(ROOT / "scripts" / name), *args]


TASKS: dict[str, list[list[str]]] = {
    "setup": [[PY, "-m", "pip", "install", "-e", ".[dev]"], ["pre-commit", "install"]],
    "test": [[PY, "-m", "pytest"]],
    "lint": [[PY, "-m", "ruff", "check", "src", "scripts", "tests", "tasks.py"]],
    "sources": [script("01_collect_data.py", "--mode", "status")],
    "register-raw": [script("01_collect_data.py", "--mode", "register")],
    "verify-raw": [script("01_collect_data.py", "--mode", "verify")],
    "trade": [script("02_clean_trade.py")],
    "status": [script("03_build_status_measures.py")],
    "text": [script("04_collect_government_text.py"), script("05_process_text.py")],
    "attention": [script("06_build_attention_measures.py")],
    "recognition": [script("07_build_recognition_measures.py")],
    "panel": [script("08_build_panel.py")],
    "models": [script("09_run_models.py")],
    "figures": [script("10_make_figures.py")],
}
PIPELINE = ["verify-raw", "trade", "status", "text", "attention", "recognition", "panel", "models",
            "figures"]
TASKS["pipeline"] = [cmd for step in PIPELINE for cmd in TASKS[step]]

# Only derived locations; data/raw and data/external are never touched.
DERIVED_DIRS = ["data/interim", "data/processed", "outputs/tables", "outputs/figures",
                "outputs/models", "outputs/diagnostics"]
KEEP = {".gitkeep", "README.md"}


def clean_derived(confirm: bool) -> int:
    targets = [p for d in DERIVED_DIRS for p in (ROOT / d).rglob("*")
               if p.is_file() and p.name not in KEEP]
    if not confirm:
        print(f"Would delete {len(targets)} derived file(s); re-run with --yes to confirm.")
        return 0
    for path in targets:
        path.unlink()
    print(f"Deleted {len(targets)} derived file(s).")
    return 0


def run(commands: list[list[str]]) -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(ROOT / "src"), env.get("PYTHONPATH")]))
    for cmd in commands:
        print("+", " ".join(Path(c).name if c == PY else c for c in cmd), flush=True)
        code = subprocess.call(cmd, cwd=ROOT, env=env)
        if code != 0:
            return code
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("task", choices=[*TASKS, "clean-derived"])
    parser.add_argument("--yes", action="store_true", help="Confirm clean-derived")
    args = parser.parse_args()
    if args.task == "clean-derived":
        return clean_derived(args.yes)
    return run(TASKS[args.task])


if __name__ == "__main__":
    sys.exit(main())
