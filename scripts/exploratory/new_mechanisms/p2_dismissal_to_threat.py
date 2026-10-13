# -*- coding: utf-8 -*-
"""P2 -- Competitive threat as a substitute for hierarchical dismissal, over time.

Proposition (pre-specified): early-period discourse about a rising challenger is dominated by
SUBORDINATE/dismissive framing (R1, or dismissive=1/stereotyping=1), while later-period discourse
shifts toward COMPETITIVE-THREAT framing (R3, or threat_coexists=1) even where outright dismissal
recedes -- i.e., the challenger stops being described as backward and starts being described as
dangerous, without necessarily passing through full peer recognition first.

This is DISTINCT from the turning-point hypothesis (which asks when peer recognition arrives). It
asks whether R1 (subordinate) and R3 (threat) trade off against each other in relative share over
time, which recognition-lag alone does not predict (recognition-lag predicts R1 recedes as R4/R5
rises, with no particular claim about R3).

Unit: classified (non-R0) sentence. Both corpora examined separately (not pooled -- different
source composition, per Phase 5 safeguard #8).
"""
import sys

import pandas as pd
from scipy import stats

from srl.utils.config import get_path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

def analyze(case: str) -> None:
    df = pd.read_csv(get_path("data.interim") / "recognition" / f"{case}_llm_classified.csv")
    df = df[(df["direction_mismatch"] != 1) & (df["R"] != "R0")].copy()
    # Split at the MEDIAN year of this case's own classified (non-R0) sample -- a rule fixed by
    # sample construction, not chosen to produce a particular result (Phase 5 safeguard #2).
    split = df["year"].median()
    df["era"] = df["year"].apply(lambda y: "early" if y < split else "late")

    print(f"\n{'='*60}\n{case} (split at median year {split:.0f}: early = before, late = at/after)\n{'='*60}")
    tab = pd.crosstab(df["era"], df["R"])
    for col in ["R1", "R2", "R3", "R4", "R5"]:
        if col not in tab.columns:
            tab[col] = 0
    tab = tab[["R1", "R2", "R3", "R4", "R5"]]
    tab_pct = tab.div(tab.sum(axis=1), axis=0).round(3)
    print("Counts:\n", tab.to_string())
    print("\nRow shares:\n", tab_pct.to_string())

    # core test: within subordinate-or-threat sentences (R1 or R3), does the R1:R3 ratio flip?
    sub_threat = df[df["R"].isin(["R1", "R3"])]
    tab2 = pd.crosstab(sub_threat["era"], sub_threat["R"])
    print("\nR1 (subordinate) vs R3 (threat) only, by era:\n", tab2.to_string())
    if tab2.shape == (2, 2):
        _, p = stats.fisher_exact(tab2.to_numpy())
        print(f"Fisher's exact test (R1 vs R3 composition, early vs late): p = {p:.3f}")
    else:
        print("Insufficient cells (need both R1 and R3 present in both eras) for a formal test.")

    out = get_path("outputs.diagnostics").parent / "exploratory" / "new_mechanisms"
    out.mkdir(parents=True, exist_ok=True)
    tab.to_csv(out / f"p2_{case}_R_by_era.csv")


def main() -> None:
    analyze("jpn_kor")
    analyze("kor_chn")


if __name__ == "__main__":
    main()
