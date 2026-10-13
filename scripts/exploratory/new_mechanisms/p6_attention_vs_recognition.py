# -*- coding: utf-8 -*-
"""P6 -- Attention vs. recognition: does growing discourse VOLUME about Korea track growing
RECOGNITION, or move independently?

Proposition (pre-specified): attention (raw speech volume mentioning Korea) and recognition
(peer-share among classified sentences) are only weakly related period to period -- attention
responds to any newsworthy event (trade friction, territorial disputes, diplomatic visits), while
recognition responds specifically to accumulated material position. A period can show rising
attention without rising recognition (e.g. a trade dispute spike) or rising recognition without a
volume spike (a quiet shift in how existing coverage frames the relationship).

Attention measure: ALL 10,742 full-text JPN Diet speeches matching the korea_catchup/competition/
economy queries (not just the 5,594 relevant-sentence subset or the 175 classified items) --
this is the broadest, least-filtered volume measure available and is NOT a recognition measure.
Recognition measure: peer-share among classified (non-R0) sentences, same periods as before.

This pilot explicitly checks the brief's own concern: "increased attention [could] reflect changes
in source coverage ... rather than substantive political salience." The NDL API's own documented
coverage is uneven across the 1980-2024 window for unrelated institutional reasons (digitization
history), so any attention spike must be read with that caveat, not as evidence of a real
salience change, unless corroborated qualitatively.
"""
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from srl.utils.config import get_path  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

BLUE, ORANGE = "#2a78d6", "#eb6834"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
PERIOD = 4


def main() -> None:
    speeches = pd.read_parquet(get_path("data.interim") / "text" / "jp_diet_speeches.parquet")
    speeches = speeches[speeches["year"].notna()].copy()
    speeches["year"] = speeches["year"].astype(int)
    speeches["period"] = (speeches["year"] // PERIOD) * PERIOD
    attention = speeches.groupby("period").size().rename("n_speeches").reset_index()

    cls = pd.read_csv(get_path("data.interim") / "recognition" / "jpn_kor_llm_classified.csv")
    cls = cls[cls["direction_mismatch"] != 1]
    cls["period"] = (cls["year"] // PERIOD) * PERIOD
    scored = cls[cls["R"] != "R0"]
    rec = scored.groupby("period").apply(
        lambda g: (g["R"].isin(["R4", "R5"])).sum() / len(g), include_groups=False
    ).rename("peer_share").reset_index()
    rec_n = scored.groupby("period").size().rename("n_scored").reset_index()

    merged = attention.merge(rec, on="period", how="left").merge(rec_n, on="period", how="left")
    print("=== Attention (full-corpus speech count) vs recognition (peer share), by period ===")
    print(merged.round(3).to_string(index=False))

    valid = merged.dropna(subset=["peer_share"])
    if len(valid) >= 4:
        corr = valid["n_speeches"].corr(valid["peer_share"])
        print(f"\nPearson correlation, attention volume vs peer_share (n={len(valid)} periods): r = {corr:.3f}")
        print("(descriptive only -- 7-8 period-level observations, not a basis for inference)")
    out = get_path("outputs.diagnostics").parent / "exploratory" / "new_mechanisms"
    out.mkdir(parents=True, exist_ok=True)
    merged.to_csv(out / "p6_attention_vs_recognition.csv", index=False)

    fig, ax1 = plt.subplots(figsize=(8.5, 4.5), facecolor=SURFACE)
    ax1.set_facecolor(SURFACE)
    ax1.bar(attention["period"], attention["n_speeches"], width=3, color=BLUE, alpha=0.35,
            label="Attention: Diet speeches mentioning Korea (full corpus, n=10,742)")
    ax1.set_ylabel("Speeches per 4-yr period", fontsize=8, color=BLUE)
    ax1.tick_params(axis="y", colors=BLUE, labelsize=8)
    for s in ("top",):
        ax1.spines[s].set_visible(False)
    ax1.tick_params(axis="x", colors=INK2, labelsize=8)

    ax2 = ax1.twinx()
    ax2.plot(valid["period"], valid["peer_share"], color=ORANGE, linewidth=2, marker="o",
              label="Recognition: peer share (classified subset, n=175 sentences)")
    ax2.set_ylabel("Peer share (R4+R5 / scored)", fontsize=8, color=ORANGE)
    ax2.tick_params(axis="y", colors=ORANGE, labelsize=8)
    ax2.set_ylim(-0.05, 1.05)
    for s in ("top",):
        ax2.spines[s].set_visible(False)

    fig.legend(fontsize=7.5, frameon=False, loc="lower center", bbox_to_anchor=(0.5, -0.02), ncol=1)
    fig.suptitle("Attention (speech volume) vs. recognition (peer share), Japan's Diet discourse on Korea",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0.08, 1, 0.95))
    fig.savefig(out / "p6_attention_vs_recognition.png", dpi=160, facecolor=SURFACE)
    print(f"\nsaved {out / 'p6_attention_vs_recognition.png'}")


if __name__ == "__main__":
    main()
