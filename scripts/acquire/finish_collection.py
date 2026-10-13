"""Finish the government-text downloads, then rebuild every derived file (run by a one-off task).

1. In parallel (different hosts): MOFA search/views/white papers; MOTIR legacy pages.
2. Then, in order: build_gov_documents, build_prelim, build_odi_reports, verify_partnerships,
   quality_checks, build_catalog, register raw files (checksums -> data/raw_manifest.csv).
Every step is resumable; exit codes are written to outputs/diagnostics/finish_collection_status.txt.
"""

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PY = sys.executable
LOG = ROOT / "outputs" / "diagnostics" / "finish_collection_status.txt"


def note(msg: str) -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as fh:
        fh.write(f"{datetime.now().isoformat(timespec='seconds')}  {msg}\n")


def run(args: list[str]) -> int:
    env = dict(
        os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT / "src"), SRL_RETRIEVAL_DATE="2026-09-30"
    )  # resume in the original retrieval folder
    note("start " + " ".join(args))
    code = subprocess.call(
        [PY, *args], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    note(f"exit {code}: " + " ".join(args))
    return code


def main() -> int:
    env = dict(
        os.environ, PYTHONIOENCODING="utf-8", PYTHONPATH=str(ROOT / "src"), SRL_RETRIEVAL_DATE="2026-09-30"
    )  # resume in the original retrieval folder
    rebuild_only = "--rebuild-only" in sys.argv
    note("=== finish_collection started" + (" (rebuild only)" if rebuild_only else "") + " ===")
    jobs = [] if rebuild_only else [
        ["scripts/acquire/acq_kr_mofa.py", "--phases", "search,views,papers"],
        ["scripts/acquire/acq_kr_motie.py", "--phases", "legacy"],
    ]
    procs = [
        (
            j,
            subprocess.Popen(
                [PY, *j], cwd=ROOT, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ),
        )
        for j in jobs
    ]
    for j, p in procs:
        note(f"exit {p.wait()}: " + " ".join(j))
    for step in (
        ["scripts/acquire/build_gov_documents.py"],
        ["scripts/acquire/build_prelim.py"],
        ["scripts/acquire/build_odi_reports.py"],
        ["scripts/acquire/verify_partnerships.py"],
        ["scripts/acquire/quality_checks.py"],
        ["scripts/acquire/build_catalog.py"],
        ["scripts/01_collect_data.py", "--mode", "register"],
    ):
        run(step)
    note("=== finish_collection done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
