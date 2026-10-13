"""Generate the machine-readable source catalog and the manual-task list.

Inputs  config/sources.yaml (sources), metadata/manual_actions.yaml (manual tasks), data/raw/ (files)
Outputs metadata/source_catalog.csv, metadata/source_catalog.json, metadata/manual_actions.csv,
        docs/manual_data_tasks.md
"""

import argparse
import json

import _bootstrap  # noqa: F401
import pandas as pd

from srl.utils.cli import run_step
from srl.utils.config import get_path, load_config, load_yaml
from srl.utils.paths import project_root

CLASS_TITLE = {
    "A": "A. Must be done manually",
    "B": "B. Recommended manual validation",
    "C": "C. Optional enhancements",
}


def raw_stats(source_id: str) -> dict:
    root = get_path("data.raw") / source_id
    if not root.exists():
        return {"raw_files": 0, "raw_mb": 0.0, "retrieved_on": ""}
    files = [p for p in root.rglob("*") if p.is_file() and p.name != "README.md"]
    runs = sorted(p.name for p in root.iterdir() if p.is_dir())
    return {
        "raw_files": len(files),
        "raw_mb": round(sum(p.stat().st_size for p in files) / 1e6, 1),
        "retrieved_on": "|".join(runs),
    }


def main(args, logger) -> None:
    meta = project_root() / "metadata"
    sources = load_config("sources")["sources"]
    rows = []
    for sid, s in sources.items():
        cov = s.get("coverage") or {}
        rows.append(
            {
                "source_id": sid,
                "name": s["name"],
                "category": s["category"],
                "constructs": "|".join(s.get("construct") or []),
                "status": s["status"],
                "access": s.get("access"),
                "url": s.get("url"),
                "licence": s.get("licence"),
                "redistribution": s.get("redistribution"),
                "coverage_countries": cov.get("countries"),
                "coverage_years": cov.get("years"),
                "frequency": cov.get("frequency"),
                "variables": s.get("variables"),
                "unit": s.get("unit"),
                "script": s.get("script"),
                "raw_path": f"data/raw/{sid}/<YYYY-MM-DD>/",
                **raw_stats(sid),
                "access_date": "2026-09-30" if s["status"] != "candidate" else "",
                "notes": s.get("notes"),
            }
        )
    cat = pd.DataFrame(rows)
    cat.to_csv(meta / "source_catalog.csv", index=False, encoding="utf-8")
    (meta / "source_catalog.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    logger.info("catalog: %d sources (%s)", len(cat), cat["status"].value_counts().to_dict())

    log = meta / "download_log.csv"
    if log.exists():
        dl = pd.read_csv(log, dtype=str, keep_default_na=False)
        dl["bytes"] = pd.to_numeric(dl["bytes"], errors="coerce").fillna(0)
        summ = (
            dl.groupby(["source_id", "outcome"])
            .agg(
                n_requests=("url", "size"),
                mb=("bytes", lambda b: round(b.sum() / 1e6, 1)),
                first=("timestamp", "min"),
                last=("timestamp", "max"),
            )
            .reset_index()
        )
        summ.to_csv(meta / "download_summary.csv", index=False, encoding="utf-8")
        logger.info("download log: %d requests summarized", len(dl))

    tasks = load_yaml("metadata/manual_actions.yaml")["tasks"]
    pd.DataFrame(tasks).to_csv(meta / "manual_actions.csv", index=False, encoding="utf-8")
    order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2, "DONE": 3}
    lines = [
        "# Manual data tasks",
        "",
        "Generated from `metadata/manual_actions.yaml` by `scripts/acquire/build_catalog.py` - edit the",
        "YAML, not this file. After any download, put the files in a **new dated folder** under the",
        "destination and run `python tasks.py register-raw` (checksums into `data/raw_manifest.csv`).",
        "Credentials go only into the git-ignored `.env` at the repository root.",
        "",
        "| id | class | priority | source |",
        "|---|---|---|---|",
    ]
    tasks_sorted = sorted(tasks, key=lambda t: (t["class"], order[t["priority"]], t["id"]))
    lines += [
        f"| [{t['id']}](#{t['id'].lower()}) | {t['class']} | {t['priority']} | {t['source']} |"
        for t in tasks_sorted
    ]
    for cls, title in CLASS_TITLE.items():
        lines += ["", f"## {title}", ""]
        for t in (x for x in tasks_sorted if x["class"] == cls):
            lines += [
                f"### {t['id']}",
                "",
                f"- **Source:** {t['source']}",
                f"- **Priority:** {t['priority']}",
                f"- **URL / navigation:** {t['url']}",
                f"- **What to do:** {t['instructions'].strip()}",
                f"- **File(s):** {t['file']}",
                f"- **Preferred filename:** `{t['preferred_filename']}`",
                f"- **Destination:** `{t['destination']}`",
                f"- **Why it is needed:** {t['why']}",
                "",
            ]
    (project_root() / "docs" / "manual_data_tasks.md").write_text(
        "\n".join(lines).rstrip() + "\n", encoding="utf-8"
    )
    logger.info("manual tasks: %d", len(tasks))

    # refresh the status report's snapshot section (derived files only)
    import write_snapshot

    write_snapshot.write()
    logger.info("docs/data_collection_status.md snapshot refreshed")


if __name__ == "__main__":
    run_step("build_catalog", main, argparse.ArgumentParser(description=__doc__))
