# -*- coding: utf-8 -*-
"""Pilot test of the central hypothesis -- recognition lags material convergence, then rises --
using the 343 LLM-assisted R0-R5 classifications (data/interim/recognition/*_llm_classified.csv)
against the verified material crossover dates (data/processed/industrial_crossover_candidates.csv).

EXPLORATORY / PROVISIONAL. No human-coded validation exists for any classified item (see
docs/measurement_protocol.md). Uses exact small-sample statistics (Fisher's exact test, exact
binomial CIs) throughout rather than asymptotic methods, because per-window n is small (often
<30) -- this is a deliberate choice, not an oversight; a normal-approximation CI or chi-square
test would overstate precision here.

Design: for each case, split classified (non-R0) sentences into three windows relative to the
EARLIEST reliable material crossover for that case:
  PRE        : year < crossover
  EARLY-POST : crossover <= year < crossover+10
  LATE-POST  : year >= crossover+10
H1 (lag):      PRE and EARLY-POST peer-shares are NOT significantly different (no immediate jump)
H2 (catch-up): LATE-POST peer-share IS significantly higher than EARLY-POST (eventual rise)
Both must hold for the "recognition lags, then catches up" pattern to be supported as stated.
"""
import sys

from scipy import stats

import pandas as pd

from srl.utils.config import get_path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

LAG_YEARS = 10  # EARLY-POST vs LATE-POST boundary; a round-number choice, not fitted


def load(case: str) -> pd.DataFrame:
    df = pd.read_csv(get_path("data.interim") / "recognition" / f"{case}_llm_classified.csv")
    return df[(df["direction_mismatch"] != 1) & (df["R"] != "R0")].copy()


def earliest_reliable_crossover(cross: pd.DataFrame, incumbent: str, challenger: str) -> float:
    rows = cross[(cross.incumbent == incumbent) & (cross.challenger == challenger)
                 & cross["reliability"].str.contains("reliable", case=False, na=False)
                 & ~cross["reliability"].str.contains("UNRELIABLE", na=False)]
    years = pd.to_numeric(rows["crossover_year"], errors="coerce").dropna()
    return float(years.min())


def window_counts(df: pd.DataFrame, crossover: float) -> pd.DataFrame:
    df = df.copy()
    df["window"] = pd.cut(df["year"], bins=[-float("inf"), crossover - 1,
                                              crossover + LAG_YEARS - 1, float("inf")],
                           labels=["PRE", "EARLY-POST", "LATE-POST"])
    rows = []
    for w in ["PRE", "EARLY-POST", "LATE-POST"]:
        g = df[df["window"] == w]
        n = len(g)
        n_peer = (g["R"].isin(["R4", "R5"])).sum()
        ci = stats.binomtest(n_peer, n, p=0.5).proportion_ci(confidence_level=0.90, method="exact") \
            if n else None
        rows.append({"window": w, "n": n, "n_peer": int(n_peer),
                     "peer_share": n_peer / n if n else float("nan"),
                     "ci90_lo": ci.low if ci else float("nan"), "ci90_hi": ci.high if ci else float("nan")})
    return pd.DataFrame(rows)


def fisher_on_raw(raw: pd.DataFrame, w1: str, w2: str) -> float:
    g1 = raw[raw.window == w1]["R"].isin(["R4", "R5"])
    g2 = raw[raw.window == w2]["R"].isin(["R4", "R5"])
    table = [[g1.sum(), len(g1) - g1.sum()], [g2.sum(), len(g2) - g2.sum()]]
    if min(len(g1), len(g2)) == 0:
        return float("nan")
    _, p = stats.fisher_exact(table)
    return p


def run_case(case: str, incumbent: str, challenger: str, cross: pd.DataFrame) -> None:
    print(f"\n{'=' * 70}\n{case}: {incumbent} -> {challenger}\n{'=' * 70}")
    crossover = earliest_reliable_crossover(cross, incumbent, challenger)
    if pd.isna(crossover):
        print("No reliable crossover date found for this pair -- cannot anchor the test.")
        return
    print(f"Earliest reliable material crossover used as T1: {crossover:.0f}")

    df = load(case)
    df["window"] = pd.cut(df["year"], bins=[-float("inf"), crossover - 1,
                                              crossover + LAG_YEARS - 1, float("inf")],
                           labels=["PRE", "EARLY-POST", "LATE-POST"])
    summary = window_counts(df, crossover)
    print("\nWindow summary (peer_share = R4+R5 share; 90% exact binomial CI):")
    print(summary.round(3).to_string(index=False))

    p_pre_early = fisher_on_raw(df, "PRE", "EARLY-POST")
    p_early_late = fisher_on_raw(df, "EARLY-POST", "LATE-POST")
    p_pre_late = fisher_on_raw(df, "PRE", "LATE-POST")
    print(f"\nFisher's exact test, peer-share (R4+R5) vs. not:")
    print(f"  PRE vs EARLY-POST   p = {p_pre_early:.3f}  (H1: expect NOT significant -- no immediate jump)")
    print(f"  EARLY-POST vs LATE-POST p = {p_early_late:.3f}  (H2: expect significant -- eventual rise)")
    print(f"  PRE vs LATE-POST    p = {p_pre_late:.3f}  (overall change)")

    early = summary[summary.window == "EARLY-POST"].iloc[0]
    late = summary[summary.window == "LATE-POST"].iloc[0]
    pre = summary[summary.window == "PRE"].iloc[0]
    h1_supported = (p_pre_early > 0.10) if not pd.isna(p_pre_early) else None
    h2_supported = (p_early_late < 0.10 and late["peer_share"] > early["peer_share"]) \
        if not pd.isna(p_early_late) else None
    print(f"\nH1 (no immediate jump at crossover) supported at alpha=0.10: {h1_supported}")
    print(f"H2 (recognition rises in the long run after crossover) supported at alpha=0.10: {h2_supported}")
    verdict = "SUPPORTED" if (h1_supported and h2_supported) else (
        "NOT SUPPORTED" if (h1_supported is not None and h2_supported is not None) else "INCONCLUSIVE (insufficient n)")
    print(f"Central hypothesis (lag-then-catch-up) for this case: {verdict}")

    out = get_path("outputs.diagnostics").parent / "exploratory"
    summary.insert(0, "case", case)
    summary.insert(1, "crossover_year", crossover)
    summary.to_csv(out / f"{case}_turning_point_test.csv", index=False)


def main() -> None:
    cross = pd.read_csv(get_path("data.processed") / "industrial_crossover_candidates.csv")
    run_case("jpn_kor", "JPN", "KOR", cross)
    run_case("kor_chn", "KOR", "CHN", cross)
    print("\n" + "=" * 70)
    print("NOTE: kor_chn's only 'reliable' crossover (batteries, ~1996) was explicitly flagged")
    print("in docs/decision_log.md as a divergent-growth pattern, not a reversal of established")
    print("Korean leadership -- this test is run for completeness but the theoretical fit of")
    print("'lag-then-catch-up' to this specific pair/industry is weaker than for jpn_kor/shipbuilding.")


if __name__ == "__main__":
    main()
