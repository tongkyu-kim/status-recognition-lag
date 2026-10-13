# -*- coding: utf-8 -*-
"""P4 -- Elite disagreement / institutional heterogeneity in recognition of Korea (Japan Diet).

Proposition (pre-specified before looking at results): government/ruling-coalition speakers show
a HIGHER peer-recognition share than opposition speakers, because ministers answering on behalf of
the government have institutional reasons to project confidence in bilateral relations and avoid
alarmist competitive framing, while opposition members use foreign economic comparisons
instrumentally to criticize government policy.

Unit of observation: the classified SENTENCE (n=175, jpn_kor), joined to speaker/speaker_group/
house metadata already captured at sampling time (data/annotations/jpn_kor_recognition_sample.csv)
-- no new acquisition. Multiple sentences from the same speech are NOT separately flagged here;
Phase 5 safeguard #5 (cluster by speech) is addressed by also reporting speech-level counts
(n_speeches column) so a reader can see how much the sentence-level n overstates independent
observations.

Government-coalition classification: LDP (自由民主党), and its historical coalition partners when
in government (New Liberal Club in 1980s coalitions, Komeito 1999-2009 and 2012-2024, etc.) are
hard to assign correctly without an external cabinet-composition dataset this project does not
have. To avoid inventing historical coalition membership, this pilot uses a DEFENSIBLE, documented
simplification instead: LDP (自由民主党, including compound labels starting with it, e.g.
"自由民主党・無所属の会") vs. every other named party vs. unaffiliated/missing (government
officials answering without a party label, coded as speaker_role in the API but not resolved
here). This is reported as a limitation, not presented as a validated government/opposition split.
"""
import sys

import pandas as pd
from scipy import stats

from srl.utils.config import get_path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")


def main() -> None:
    sample = pd.read_csv(get_path("data.raw").parent / "annotations" / "jpn_kor_recognition_sample.csv")
    cls = pd.read_csv(get_path("data.interim") / "recognition" / "jpn_kor_llm_classified.csv")
    df = cls.merge(sample[["item_id", "speaker", "speaker_group", "institution", "doc_id"]],
                    on="item_id", how="left")
    df = df[df["direction_mismatch"] != 1]

    df["bloc"] = df["speaker_group"].apply(
        lambda g: "LDP" if isinstance(g, str) and g.startswith("自由民主党")
        else ("unaffiliated/no-party-label" if pd.isna(g) or g == "" else "other-party"))

    print("=== Composition ===")
    print(df.groupby("bloc").size())
    print("\nSpeech-level n (unique doc_id) by bloc, to show sentence-n does not equal independent-n:")
    print(df.groupby("bloc")["doc_id"].nunique())

    scored = df[df["R"] != "R0"]
    print(f"\nScored (non-R0) sentences: {len(scored)} from {scored['doc_id'].nunique()} speeches")

    tab = pd.crosstab(scored["bloc"], scored["R"].isin(["R4", "R5"]))
    tab.columns = ["not_peer", "peer"]
    tab["n"] = tab.sum(axis=1)
    tab["peer_share"] = tab["peer"] / tab["n"]
    print("\n=== Peer-share by political bloc (scored sentences) ===")
    print(tab.to_string())

    if "LDP" in tab.index and "other-party" in tab.index:
        table2x2 = [[tab.loc["LDP", "peer"], tab.loc["LDP", "not_peer"]],
                    [tab.loc["other-party", "peer"], tab.loc["other-party", "not_peer"]]]
        _, p = stats.fisher_exact(table2x2)
        print(f"\nFisher's exact test, LDP vs other-party, peer vs not: p = {p:.3f}")
    else:
        print("\nInsufficient cells for LDP vs other-party test.")

    # house (chamber) comparison as a secondary institutional split
    tab_house = pd.crosstab(scored["institution"], scored["R"].isin(["R4", "R5"]))
    tab_house.columns = ["not_peer", "peer"]
    tab_house["n"] = tab_house.sum(axis=1)
    tab_house["peer_share"] = tab_house["peer"] / tab_house["n"]
    print("\n=== Peer-share by chamber (House of Representatives vs Councillors) ===")
    print(tab_house.to_string())

    out = get_path("outputs.diagnostics").parent / "exploratory" / "new_mechanisms"
    out.mkdir(parents=True, exist_ok=True)
    tab.to_csv(out / "p4_peer_share_by_bloc.csv")
    tab_house.to_csv(out / "p4_peer_share_by_chamber.csv")

    # qualitative: show a few contrasting examples if available
    print("\n=== Example LDP items (R4/R5) ===")
    for _, r in scored[(scored.bloc == "LDP") & (scored["R"].isin(["R4", "R5"]))].head(3).iterrows():
        print(f"  {r['item_id']} ({r['year']}): {r['notes'][:150]}")
    print("\n=== Example other-party items (R4/R5) ===")
    for _, r in scored[(scored.bloc == "other-party") & (scored["R"].isin(["R4", "R5"]))].head(3).iterrows():
        print(f"  {r['item_id']} ({r['year']}): {r['notes'][:150]}")
    print("\n=== Example other-party items (R1/R3, dismissal/threat) ===")
    for _, r in scored[(scored.bloc == "other-party") & (scored["R"].isin(["R1", "R3"]))].head(3).iterrows():
        print(f"  {r['item_id']} ({r['year']}): {r['notes'][:150]}")


if __name__ == "__main__":
    main()
