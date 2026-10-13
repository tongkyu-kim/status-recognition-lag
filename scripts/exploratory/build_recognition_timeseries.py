# -*- coding: utf-8 -*-
"""Aggregate the LLM-assisted R0-R5 classifications (data/interim/recognition/*_llm_classified.csv)
into period-level descriptive series and compare against the verified material crossover dates
(data/processed/industrial_crossover_candidates.csv).

EXPLORATORY / PROVISIONAL. Classifications are LLM-assisted (this agent, single-pass, no human
validation), not a validated measure -- see docs/measurement_protocol.md. Small per-period N;
read as directional, not confirmatory. Excludes direction_mismatch=1 items.
"""
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from srl.utils.config import get_path  # noqa: E402

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")

R_ORDER = ["R0", "R1", "R2", "R3", "R4", "R5"]
BLUE, ORANGE, GREEN, PURP = "#2a78d6", "#eb6834", "#1baf7a", "#8858d6"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(case: str) -> pd.DataFrame:
    path = get_path("data.interim") / "recognition" / f"{case}_llm_classified.csv"
    df = pd.read_csv(path)
    df = df[df["direction_mismatch"] != 1].copy()
    return df


def period_index(df: pd.DataFrame, period: int = 4) -> pd.DataFrame:
    df = df.copy()
    df["period"] = (df["year"] // period) * period
    scored = df[df["R"] != "R0"]
    rows = []
    for p, g in df.groupby("period"):
        n_total = len(g)
        s = scored[scored["period"] == p]
        n_scored = len(s)
        n_peer = (s["R"].isin(["R4", "R5"])).sum()
        n_subordinate = (s["R"].isin(["R1"])).sum()
        n_achievement = (s["R"] == "R2").sum()
        n_threat = (s["R"] == "R3").sum()
        rows.append({
            "period": p, "n_total": n_total, "n_scored": n_scored,
            "peer_share": n_peer / n_scored if n_scored else float("nan"),
            "subordinate_share": n_subordinate / n_scored if n_scored else float("nan"),
            "achievement_share": n_achievement / n_scored if n_scored else float("nan"),
            "threat_share": n_threat / n_scored if n_scored else float("nan"),
            "threat_coexists_rate": g["threat_coexists"].mean(),
        })
    return pd.DataFrame(rows).sort_values("period")


def main() -> None:
    out = get_path("outputs.diagnostics").parent / "exploratory"
    out.mkdir(parents=True, exist_ok=True)

    kor_chn = load("kor_chn")
    jpn_kor = load("jpn_kor")
    print(f"kor_chn: {len(kor_chn)} classified (direction-consistent); "
          f"R distribution:\n{kor_chn['R'].value_counts().reindex(R_ORDER).fillna(0).astype(int)}")
    print(f"\njpn_kor: {len(jpn_kor)} classified (direction-consistent); "
          f"R distribution:\n{jpn_kor['R'].value_counts().reindex(R_ORDER).fillna(0).astype(int)}")

    kc_series = period_index(kor_chn)
    jk_series = period_index(jpn_kor)
    kc_series.to_csv(out / "kor_chn_recognition_timeseries.csv", index=False)
    jk_series.to_csv(out / "jpn_kor_recognition_timeseries.csv", index=False)
    print("\n--- kor_chn period series ---")
    print(kc_series.round(2).to_string(index=False))
    print("\n--- jpn_kor period series ---")
    print(jk_series.round(2).to_string(index=False))

    # crossover dates, from the audited table (reliable rows only)
    cross = pd.read_csv(get_path("data.processed") / "industrial_crossover_candidates.csv")
    cross["crossover_year"] = pd.to_numeric(cross["crossover_year"], errors="coerce")
    reliable = cross[cross["reliability"].str.contains("reliable", case=False, na=False)
                      & ~cross["reliability"].str.contains("UNRELIABLE", na=False)]
    jpn_kor_cross = reliable[(reliable.incumbent == "JPN") & (reliable.challenger == "KOR")]
    kor_chn_cross = reliable[(reliable.incumbent == "KOR") & (reliable.challenger == "CHN")]
    print("\nJPN->KOR reliable crossovers:\n", jpn_kor_cross[["industry", "crossover_year"]].to_string(index=False))
    print("\nKOR->CHN reliable crossovers:\n", kor_chn_cross[["industry", "crossover_year"]].to_string(index=False))

    fig, axes = plt.subplots(1, 2, figsize=(13, 4.6), facecolor=SURFACE)
    for ax, (series, cross_rows, title) in zip(
        axes,
        [(jk_series, jpn_kor_cross, "Japan's recognition of Korea"),
         (kc_series, kor_chn_cross, "Korea's recognition of China")],
        strict=True,
    ):
        ax.set_facecolor(SURFACE)
        ax.plot(series["period"], series["peer_share"], color=ORANGE, linewidth=2, marker="o",
                markersize=4, label="Peer share (R4+R5 / scored)")
        ax.plot(series["period"], series["threat_share"], color=PURP, linewidth=1.5, marker="s",
                markersize=3, linestyle="--", label="Competitive-threat share (R3 / scored)")
        for _, r in cross_rows.iterrows():
            ax.axvline(r["crossover_year"], color=GREEN, linewidth=1, linestyle=":")
            ax.text(r["crossover_year"], 1.02, r["industry"], rotation=90, fontsize=6.5,
                    color=INK2, ha="right", va="bottom", transform=ax.get_xaxis_transform())
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        ax.set_ylim(-0.05, 1.05)
        ax.set_title(title, fontsize=10, color=INK, loc="left")
        ax.set_xlabel("4-year period", fontsize=8, color=INK2)
    axes[0].legend(fontsize=7.5, frameon=False, loc="upper left")
    fig.suptitle("Exploratory recognition series vs. verified material crossovers (LLM-assisted, "
                 "single-pass, unvalidated -- n per period often <10, read as directional only)",
                 fontsize=9.5, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(out / "recognition_vs_crossovers.png", dpi=160, facecolor=SURFACE)
    print(f"\nsaved {out / 'recognition_vs_crossovers.png'}")


if __name__ == "__main__":
    main()
