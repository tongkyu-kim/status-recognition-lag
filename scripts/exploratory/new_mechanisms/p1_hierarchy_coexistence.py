# -*- coding: utf-8 -*-
"""P1 -- Recognition without status equality: does achievement acknowledgment (R2/R4/R5) coexist
with hierarchy-preserving language within the same passage?

Proposition (pre-specified): among achievement-acknowledging sentences, a recurring subset will
ALSO contain language that preserves hierarchy in a different dimension -- asserting continued
superiority on an unmentioned axis (quality vs. price), attributing the rival's gain to external
causes (subsidy, licensing leakage) rather than its own merit, or using delegitimizing labels
("nationalistic") alongside an otherwise peer-level acknowledgment. This is a genuinely different
claim from recognition-lag: it says recognition, when it does arrive, often arrives
PARTIAL/QUALIFIED rather than full, not merely LATE.

New coding: data/interim/recognition/p1_hierarchy_coexistence_coding.csv -- every R2/R4/R5 item
in both corpora (n=42 jpn_kor, n=31 kor_chn) was re-read by this agent specifically for this
pattern (a second, distinct pass from the original R0-R5 coding; see the file for the mechanism
label and evidence quote on each positively-coded item). Absence from that file = coded 0
(no hierarchy-preserving language found on re-reading), not "not reviewed."

MAJOR CAVEAT, stated before results are shown below: the two corpora differ in genre (Japanese
Diet = adversarial parliamentary debate; Korean MOFA/MOTIE/Presidential = controlled official
press material). Any difference found here is AT LEAST as plausibly a genre/source-composition
effect as a genuine cross-case theoretical difference (Phase 5 safeguard #8). This pilot does not
have a way to separate the two explanations with the data in hand.
"""
import sys

import pandas as pd
from scipy import stats

from srl.utils.config import get_path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    coded = pd.read_csv(get_path("data.interim") / "recognition" / "p1_hierarchy_coexistence_coding.csv")

    rows = []
    for case in ["jpn_kor", "kor_chn"]:
        cls = pd.read_csv(get_path("data.interim") / "recognition" / f"{case}_llm_classified.csv")
        achievement = cls[(cls["direction_mismatch"] != 1) & (cls["R"].isin(["R2", "R4", "R5"]))]
        positive = coded[coded["case"] == case]
        n_total = len(achievement)
        n_coexist = len(positive)
        rows.append({"case": case, "n_achievement_items": n_total,
                     "n_hierarchy_coexists": n_coexist,
                     "share": n_coexist / n_total if n_total else float("nan")})
    summary = pd.DataFrame(rows)
    print("=== Hierarchy-coexistence share among achievement-acknowledging (R2/R4/R5) items ===")
    print(summary.round(3).to_string(index=False))

    table = [[summary.loc[0, "n_hierarchy_coexists"],
              summary.loc[0, "n_achievement_items"] - summary.loc[0, "n_hierarchy_coexists"]],
             [summary.loc[1, "n_hierarchy_coexists"],
              summary.loc[1, "n_achievement_items"] - summary.loc[1, "n_hierarchy_coexists"]]]
    _, p = stats.fisher_exact(table)
    print(f"\nFisher's exact test, jpn_kor vs kor_chn hierarchy-coexistence rate: p = {p:.4f}")
    print("(See the module docstring's caveat: this is confounded with source genre and must")
    print(" NOT be read as a clean cross-case theoretical comparison without further work.)")

    print("\n=== Mechanism breakdown (jpn_kor only -- kor_chn has zero positive cases) ===")
    print(coded[coded.case == "jpn_kor"]["hierarchy_mechanism"].value_counts().to_string())

    out = get_path("outputs.diagnostics").parent / "exploratory" / "new_mechanisms"
    out.mkdir(parents=True, exist_ok=True)
    summary.to_csv(out / "p1_hierarchy_coexistence_summary.csv", index=False)


if __name__ == "__main__":
    main()
