# -*- coding: utf-8 -*-
"""Historical export-structure overlap along the USA->Japan->Korea->China chain.

Finger-Kreinin export similarity index (srl.trade.overlap.export_similarity_index), computed from
Atlas of Economic Complexity SITC Rev.1 L4 export values, 1962-2024.
Produced 2026-10-13 in response to a direct question; reused as groundwork for
data/processed/industrial_crossover_candidates.csv. See docs/decision_log.md.

Run from the repository root: python scripts/exploratory/historical_overlap_chain.py
"""

import json

import pandas as pd

from srl.trade.overlap import export_similarity_index
from srl.utils.config import get_path
from srl.utils.paths import project_root

RAW = project_root() / "data" / "raw" / "complexity_atlas" / "2026-09-30" / "countryProductYear"
COUNTRIES = ["USA", "JPN", "KOR", "CHN"]


def main() -> None:
    rows = []
    for c in COUNTRIES:
        for f in sorted(RAW.glob(f"SITC_L4_{c}_*.json")):
            d = json.loads(f.read_text(encoding="utf-8"))
            for r in d["data"]["countryProductYear"]:
                v = r.get("exportValue")
                if v is None or v <= 0:
                    continue
                rows.append((r["year"], c, r["productId"], v))

    df = pd.DataFrame(rows, columns=["year", "iso3", "product", "value"])
    df = df.groupby(["year", "iso3", "product"], as_index=False)["value"].sum()
    print("rows:", len(df), "years:", df["year"].min(), "-", df["year"].max())
    print(df.groupby("iso3")["year"].agg(["min", "max", "nunique"]))

    out_rows = []
    for ref in ["USA", "JPN", "KOR"]:
        esi = export_similarity_index(df, reference=ref, scale=100.0)
        esi["reference"] = ref
        out_rows.append(esi)
    esi_all = pd.concat(out_rows, ignore_index=True)

    chain = {
        ("USA", "JPN"): esi_all[(esi_all.reference == "USA") & (esi_all.iso3 == "JPN")],
        ("JPN", "KOR"): esi_all[(esi_all.reference == "JPN") & (esi_all.iso3 == "KOR")],
        ("KOR", "CHN"): esi_all[(esi_all.reference == "KOR") & (esi_all.iso3 == "CHN")],
    }

    out_dir = get_path("outputs.diagnostics").parent / "exploratory"
    out_dir.mkdir(parents=True, exist_ok=True)
    wide = None
    for (a, b), d in chain.items():
        d = d[["year", "esi"]].rename(columns={"esi": f"{a}_{b}"}).sort_values("year")
        wide = d if wide is None else wide.merge(d, on="year", how="outer")
    wide = wide.sort_values("year")
    wide.to_csv(out_dir / "historical_overlap_chain.csv", index=False)
    print(wide.to_string(index=False))

    wide["decade"] = (wide["year"] // 10) * 10
    print("\n--- decade means (ESI, 0-100) ---")
    print(wide.groupby("decade")[["USA_JPN", "JPN_KOR", "KOR_CHN"]].mean().round(1).to_string())


if __name__ == "__main__":
    main()
