"""Collect documentary evidence for Korea-partner partnership upgrades (supports manual task V1).

Searches the Korean government corpus (full texts) for partnership-tier phrases co-occurring with
establishment/upgrade verbs and a partner mention, and lists the earliest matching documents per
country x tier. Output is EVIDENCE for a human to confirm dates and wording - it does not change
event_transitions.csv.

Output: outputs/diagnostics/partnership_evidence.csv
"""

import argparse
import re

import _bootstrap  # noqa: F401
import pandas as pd

from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import write_table

# Tiers are matched independently and overlap: the generic "strategic_partnership" pattern also
# matches inside the more specific tiers, so read the `context` column before recording a date.
TIERS = {
    "comprehensive_strategic_partnership": r"포괄적\s*전략적\s*동반자"
    r"|Comprehensive\s+Strategic\s+Partnership",
    "special_strategic_partnership": r"특별\s*전략적\s*동반자|Special\s+Strategic\s+Partnership",
    "strategic_cooperative_partnership": r"전략적\s*협력\s*동반자"
    r"|Strategic\s+Cooperative\s+Partnership",
    "strategic_partnership": r"전략적\s*동반자|Strategic\s+Partnership",
    "comprehensive_partnership": r"포괄적\s*(?:협력\s*)?동반자"
    r"|Comprehensive\s+(?:Cooperative\s+)?Partnership",
}
ACTION = r"격상|수립|발전시키기로|upgrad|elevat|establish"
PARTNERS = ["CHN", "VNM", "IDN", "THA", "MYS", "PHL", "SGP", "KHM", "LAO", "MMR", "BRN", "TLS", "ASEAN"]


def main(args, logger) -> None:
    pre = get_path("data.interim") / "prelim"
    meta = pd.read_csv(pre / "gov_documents_korea.csv", low_memory=False)
    text = pd.read_parquet(get_path("data.interim") / "text" / "gov_documents_korea_text.parquet")
    docs = meta.merge(text[["doc_id", "text"]], on="doc_id", how="inner")
    rows = []
    for tier, pat in TIERS.items():
        tier_re, act_re = re.compile(pat, re.I), re.compile(ACTION, re.I)
        for d in docs.itertuples():
            body = f"{d.title}\n{d.text}"
            m = tier_re.search(body)
            if not m:
                continue
            window = body[max(0, m.start() - 300) : m.end() + 300]
            if not act_re.search(window):
                continue
            for iso in PARTNERS:
                if getattr(d, f"mentions_{iso}", 0) > 0:
                    rows.append(
                        {
                            "country": iso,
                            "tier": tier,
                            "date": d.date,
                            "doc_id": d.doc_id,
                            "title": d.title,
                            "url": d.url,
                            "context": re.sub(r"\s+", " ", window)[:400],
                        }
                    )
    ev = pd.DataFrame(rows)
    if ev.empty:
        logger.warning("No evidence found (is full text available yet?)")
        write_table(ev, get_path("outputs.diagnostics", mkdir=True) / "partnership_evidence.csv")
        return
    ev = ev.sort_values(["country", "tier", "date"])
    first = ev.groupby(["country", "tier"]).head(5)
    write_table(first, get_path("outputs.diagnostics", mkdir=True) / "partnership_evidence.csv")
    logger.info(
        "Earliest evidence per country x tier:\n%s", ev.groupby(["country", "tier"])["date"].min().to_string()
    )


if __name__ == "__main__":
    run_step("verify_partnerships", main, argparse.ArgumentParser(description=__doc__))
