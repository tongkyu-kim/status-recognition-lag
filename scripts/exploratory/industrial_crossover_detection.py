# -*- coding: utf-8 -*-
"""Industrial crossover candidates: global export market share by product, USA/JPN/KOR/CHN.

Uses the Atlas of Economic Complexity's own `globalMarketShare` field (not self-computed).
Sources: data/raw/complexity_atlas/2026-09-30/countryProductYear/{SITC,HS92}_L4_<ISO3>_*.json

Product/code selection mirrors config/sectors.yaml -- keep both in sync if either changes.
Produced 2026-10-13; findings and reliability caveats are written up in
data/processed/industrial_crossover_candidates.csv and docs/decision_log.md R002/R003.

Run from the repository root: python scripts/exploratory/industrial_crossover_detection.py
"""
import json

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from srl.utils.config import get_path  # noqa: E402
from srl.utils.paths import project_root  # noqa: E402

RAW = project_root() / "data" / "raw" / "complexity_atlas" / "2026-09-30" / "countryProductYear"
COUNTRIES = ["USA", "JPN", "KOR", "CHN"]

TARGETS = {
    "shipbuilding": ("SITC", "product-SITC-1340", "SITC 7932 Ships, boats and other vessels"),
    "semiconductors": ("HS92", {"product-HS92-1744", "product-HS92-1745"},
                        "HS 8541+8542 Semiconductor devices + integrated circuits"),
    "displays_optics": ("HS92", "product-HS92-1802",
                         "HS 9013 Liquid crystal devices, lasers, optics (noisy proxy -- see decision_log R002)"),
    "batteries": ("HS92", "product-HS92-1710", "HS 8507 Electric storage (rechargeable) batteries"),
}

BLUE, ORANGE, GREEN, PURP = "#2a78d6", "#eb6834", "#1baf7a", "#8858d6"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def load(classif: str, country: str) -> list[dict]:
    out = []
    for f in sorted(RAW.glob(f"{classif}_L4_{country}_*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        out.extend(d["data"]["countryProductYear"])
    return out


def build_results() -> dict[str, pd.DataFrame]:
    results = {}
    for name, (classif, pid, label) in TARGETS.items():
        pid_set = pid if isinstance(pid, set) else {pid}
        rows = []
        for c in COUNTRIES:
            for r in load(classif, c):
                if r["productId"] in pid_set:
                    rows.append({"iso3": c, "year": r["year"], "exportValue": r.get("exportValue") or 0.0,
                                 "globalMarketShare": r.get("globalMarketShare")})
        df = pd.DataFrame(rows)
        agg = df.groupby(["iso3", "year"], as_index=False).agg(
            exportValue=("exportValue", "sum"), globalMarketShare=("globalMarketShare", "sum"))
        results[name] = agg
        print(f"\n=== {name} ({label}) ===")
        wide = agg.pivot(index="year", columns="iso3", values="globalMarketShare").sort_index()
        print((wide * 100).round(2).to_string())
    return results


def first_sustained_crossover(wide: pd.DataFrame, challenger: str, incumbent: str, min_run: int = 3):
    """First year challenger's share exceeds incumbent's, sustained >= min_run years. A detection
    heuristic for candidates only -- see docs/decision_log.md R002 for why this is not applied
    blindly (the pre-1992 SITC shipbuilding and HS9013 display series fail a plausibility check
    and must not be reported from this rule alone)."""
    if challenger not in wide.columns or incumbent not in wide.columns:
        return None
    gt = (wide[challenger] > wide[incumbent]).astype(int)
    run = gt.groupby((gt != gt.shift()).cumsum()).transform("size") * gt
    candidates = wide.index[(gt == 1) & (run >= min_run)]
    return int(candidates.min()) if len(candidates) else None


def make_chart(results: dict[str, pd.DataFrame], out_dir) -> None:
    def wide_pct(name):
        w = results[name].pivot(index="year", columns="iso3", values="globalMarketShare").sort_index()
        return w * 100

    ships, semi, batt = wide_pct("shipbuilding"), wide_pct("semiconductors"), wide_pct("batteries")
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.3), facecolor=SURFACE)
    panels = [(ships, "Shipbuilding\n(SITC 7932)"), (semi, "Semiconductors\n(HS 8541+8542)"),
              (batt, "Storage batteries\n(HS 8507)")]
    for ax, (d, title) in zip(axes, panels, strict=True):
        ax.set_facecolor(SURFACE)
        ax.plot(d.index, d["JPN"], color=BLUE, linewidth=2, label="Japan")
        ax.plot(d.index, d["KOR"], color=ORANGE, linewidth=2, label="Korea")
        ax.plot(d.index, d["CHN"], color=GREEN, linewidth=2, label="China")
        ax.plot(d.index, d["USA"], color=PURP, linewidth=1.2, linestyle=":", label="USA", alpha=0.6)
        for s in ("top", "right"):
            ax.spines[s].set_visible(False)
        for s in ("left", "bottom"):
            ax.spines[s].set_color(GRID)
        ax.tick_params(colors=INK2, labelsize=8)
        ax.grid(axis="y", color=GRID, linewidth=0.6)
        ax.set_title(title, fontsize=9.5, color=INK, loc="left")
        ax.set_ylabel("Global export market share (%)", fontsize=8, color=INK2)
    axes[0].legend(fontsize=8, frameon=False, loc="upper right")
    fig.suptitle("Industrial crossover candidates, global export market share (Atlas of Economic Complexity)",
                 fontsize=10.5, color=INK, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(out_dir / "industrial_crossovers_hs92.png", dpi=160, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    results = build_results()

    out_dir = get_path("outputs.diagnostics").parent / "exploratory"
    out_dir.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(out_dir / "industrial_crossovers.xlsx") as xl:
        for name, agg in results.items():
            wide = agg.pivot(index="year", columns="iso3", values="globalMarketShare").sort_index()
            (wide * 100).to_excel(xl, sheet_name=name)
    for name, agg in results.items():
        wide = agg.pivot(index="year", columns="iso3", values="globalMarketShare").sort_index()
        wide.to_csv(out_dir / f"crossover_{name}.csv")
    print("\nsaved:", out_dir / "industrial_crossovers.xlsx")

    print("\n=== candidate crossover years (challenger share > incumbent share, sustained >=3 yrs) ===")
    pairs = [("shipbuilding", "KOR", "JPN"), ("shipbuilding", "CHN", "KOR"), ("shipbuilding", "CHN", "JPN"),
             ("semiconductors", "KOR", "JPN"), ("semiconductors", "CHN", "KOR"),
             ("displays_optics", "KOR", "JPN"), ("displays_optics", "CHN", "KOR"),
             ("batteries", "KOR", "JPN"), ("batteries", "CHN", "KOR")]
    for industry, challenger, incumbent in pairs:
        wide = results[industry].pivot(index="year", columns="iso3", values="globalMarketShare").sort_index()
        yr = first_sustained_crossover(wide, challenger, incumbent)
        print(f"{industry:16s} {challenger} > {incumbent}: {yr}")

    make_chart(results, out_dir)
    print("saved chart:", out_dir / "industrial_crossovers_hs92.png")


if __name__ == "__main__":
    main()
