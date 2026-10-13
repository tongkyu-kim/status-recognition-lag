"""Write the end-of-run snapshot into docs/data_collection_status.md (replaces the Snapshot section).

Called by scripts/acquire/build_catalog.py, so every rebuild refreshes the numbers. Reads only
derived files; no network.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd

from srl.utils.config import get_path
from srl.utils.paths import project_root

HEADER = "## Snapshot (end of run)"


def _table(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    lines += [
        "| " + " | ".join("" if pd.isna(v) else str(v).replace("|", "\\|") for v in row) + " |"
        for row in df.itertuples(index=False)
    ]
    return "\n".join(lines)


def build_snapshot() -> str:
    pre = get_path("data.interim") / "prelim"
    diag = get_path("outputs.diagnostics")
    parts = [
        HEADER,
        "",
        f"_Generated {datetime.now().isoformat(timespec='minutes')} (Korea time) by "
        "`scripts/acquire/write_snapshot.py`._",
        "",
    ]

    gov = pre / "gov_documents_korea.csv"
    if gov.exists():
        g = pd.read_csv(gov, low_memory=False)
        t = (
            g.groupby("source_id")
            .agg(
                documents=("doc_id", "size"),
                full_text=("text_status", lambda s: int((s == "full_text").sum())),
                first_year=("year", "min"),
                last_year=("year", "max"),
                mention_any_partner=("partners_mentioned", lambda s: int(s.fillna("").ne("").sum())),
            )
            .reset_index()
        )
        parts += ["### Korean government corpus", "", _table(t), ""]
        if "date_recovery" in g:
            m = g[g["source_id"] == "kr_motie"]
            rec = (
                m["date_recovery"]
                .fillna("")
                .replace("", "original_date")
                .value_counts()
                .rename_axis("MOTIR date source")
                .reset_index(name="documents")
            )
            parts += [
                "MOTIR dates (legacy releases imported with 2016-12-09 are repaired where evidence exists; "
                "`date_reliable` flags the rest):",
                "",
                _table(rec),
                "",
            ]

    rows = []
    for f in [
        "macro_country_year.csv",
        "income_classification_country_year.csv",
        "trade_country_year.csv",
        "trade_product_country_year.csv",
        "event_transitions.csv",
        "odi_korea_country_year.csv",
    ]:
        p = pre / f
        if p.exists():
            rows.append(
                {"file": f"data/interim/prelim/{f}", "rows": sum(1 for _ in p.open(encoding="utf-8")) - 1}
            )
    if rows:
        parts += ["### Preliminary derived files", "", _table(pd.DataFrame(rows)), ""]

    qc = diag / "qc_summary.csv"
    if qc.exists():
        parts += [
            "### Quality checks (`outputs/diagnostics/qc_summary.csv`)",
            "",
            _table(pd.read_csv(qc)),
            "",
        ]

    yt = get_path("data.processed") / "youtube_frame" / "NEXT_ACTION.txt"
    if yt.exists():
        parts += [
            "### YouTube sampling frame (daily task `SRL YouTube frame daily`)",
            "",
            "```text",
            yt.read_text(encoding="utf-8").strip(),
            "```",
            "",
        ]
    return "\n".join(parts).rstrip() + "\n"


def write() -> None:
    doc = project_root() / "docs" / "data_collection_status.md"
    text = doc.read_text(encoding="utf-8")
    head = text.split(HEADER)[0].rstrip() + "\n\n"
    doc.write_text(head + build_snapshot(), encoding="utf-8")


if __name__ == "__main__":
    import _bootstrap  # noqa: F401

    write()
