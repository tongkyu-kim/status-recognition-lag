"""Build the ASEAN+3 industrial-similarity panel (pair-year and directed dyad-year).

Inputs (raw, read-only): Atlas of Economic Complexity GraphQL pulls
  data/raw/complexity_atlas/2026-09-30 (panel + JPN/USA; SITC 1962-; product metadata; PCI)
  data/raw/complexity_atlas/2026-10-14 (all countries HS92 L4; all ASEAN+3 bilateral totals)
and the parent project's WDI country-year file data/interim/prelim/macro_country_year.csv.

Definitions (asean3/docs/variable_dictionary.md):
  s_ikt     = x_ikt / sum_k x_ikt  (share of HS92 4-digit product k in i's exports to the world)
  ESI_ijt   = 100 * sum_k min(s_ikt, s_jkt)            Finger & Kreinin (1979), world-market version
  ESI_G     = 100 * sum_{k in G} min(s_ik, s_jk)        contribution of product group G (adds up)
  ESIw_G    = ESI on shares renormalised within G       composition similarity inside G
  PCI group = terciles of the mean 1995-1999 Atlas PCI (fixed, pre-period; no future information)
  PRODY_kt  = sum_c [ (x_ck/X_c) / sum_c (x_ck/X_c) ] * GDPpcPPP_ct   Hausmann, Hwang & Rodrik (2007)
  PRODY group = terciles of mean 1995-1999 PRODY (fixed, pre-period)
Rolling statistics use trailing windows only (t-2..t, t-4..t; change t vs t-10).

Outputs: asean3/data/processed/esi_pair_year.parquet, dyad_year.parquet (+ csv),
         asean3/outputs/diagnostics/econ_*.csv
"""

from __future__ import annotations

import itertools
import json
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

import _common as C

log = logging.getLogger("b01")
A1 = C.RAW / "complexity_atlas" / "2026-09-30"
A2 = C.RAW / "complexity_atlas" / "2026-10-14"
ISO_OF = {}


def load_json_rows(path: Path) -> list[dict]:
    body = json.loads(path.read_text(encoding="utf-8"))
    return next(iter(body["data"].values()))


def country_map() -> dict[str, str]:
    rows = load_json_rows(A1 / "meta/locationCountry.json")
    return {r["countryId"]: r["iso3Code"] for r in rows}


def load_cpy(cls: str) -> pd.DataFrame:
    files = sorted(A1.glob(f"countryProductYear/{cls}_L4_*.json"))
    if cls == "HS92":
        have = {f.name for f in files}
        files += [f for f in sorted(A2.glob("countryProductYear/HS92_L4_*.json")) if f.name not in have]
    frames = []
    for f in files:
        rows = load_json_rows(f)
        if rows:
            frames.append(pd.DataFrame(rows))
    d = pd.concat(frames, ignore_index=True)
    d["iso3"] = d.countryId.map(ISO_OF)
    d = d.drop_duplicates(["iso3", "productId", "year"])
    return d[["iso3", "productId", "year", "exportValue", "globalMarketShare", "exportRca"]]


def products(cls: str) -> pd.DataFrame:
    if cls == "HS92":
        p = pd.DataFrame(load_json_rows(A1 / "meta/productHs92_level4.json"))
        p["section2"] = p["parent"].map(lambda x: x["productId"] if isinstance(x, dict) else None)
        return p[["productId", "code", "nameShortEn", "naturalResource"]]
    p = pd.DataFrame(load_json_rows(A1 / "meta/productSitc_level4.json"))
    return p[["productId", "code", "nameEn"]]


def esi_matrix(shares: pd.DataFrame, cols: list[str]) -> dict[tuple[str, str], float]:
    """shares: index=product, columns=countries, values=shares summing to 1 per column."""
    out = {}
    for a, b in itertools.combinations(cols, 2):
        if a in shares and b in shares:
            out[(a, b)] = 100.0 * np.minimum(shares[a].to_numpy(), shares[b].to_numpy()).sum()
    return out


def sector_of(code: str) -> str | None:
    if not code[:2].isdigit():
        return None  # Atlas residual codes (e.g. XXXX unspecified)
    h2 = int(code[:2])
    if code in ("8541", "8542"):
        return "semicon"
    if h2 in (84, 85):
        return "machinery_electrical"
    if h2 == 87:
        return "vehicles"
    if h2 == 89:
        return "ships"
    if h2 in (72, 73):
        return "iron_steel"
    if 28 <= h2 <= 40:
        return "chem_plastics"
    if 50 <= h2 <= 64:
        return "textile_apparel_footwear"
    return None


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    ISO_OF.update(country_map())

    # ------------------------------------------------------------------ HS92 all countries
    hs = load_cpy("HS92")
    hs = hs[hs.year.between(1995, 2024)]
    prod = products("HS92")
    hs = hs.merge(prod, on="productId", how="left")
    log.info("HS92 rows %d, countries %d", len(hs), hs.iso3.nunique())
    cov = hs.groupby("year").iso3.nunique().rename("n_countries").reset_index()

    # PCI (Atlas productYear) and PRODY
    py = pd.DataFrame(load_json_rows(A1 / "productYear_HS92_level4.json"))
    cyr = pd.DataFrame(load_json_rows(A1 / "countryYear_HS92.json"))
    cyr["iso3"] = cyr.countryId.map(ISO_OF)
    gdp = cyr[["iso3", "year", "gdppcPpp", "exportValue"]].rename(columns={"exportValue": "X_total"})
    w = hs[hs.exportValue > 0][["iso3", "year", "productId", "exportValue"]].merge(gdp, on=["iso3", "year"])
    w = w[w.gdppcPpp.notna() & (w.X_total > 0)]
    w["sh"] = w.exportValue / w.groupby(["iso3", "year"]).exportValue.transform("sum")
    w["wt"] = w.sh / w.groupby(["productId", "year"]).sh.transform("sum")
    prody = (w.wt * w.gdppcPpp).groupby([w.productId, w.year]).sum().rename("prody").reset_index()
    prody_n = w.groupby("year").iso3.nunique().rename("n_prody_countries").reset_index()
    cov = cov.merge(prody_n, on="year", how="left")
    soph = py[["productId", "year", "pci"]].merge(prody, on=["productId", "year"], how="outer")
    soph.to_parquet(C.INTERIM / "product_sophistication_hs92.parquet", index=False)
    base = soph[soph.year.between(1995, 1999)].groupby("productId")[["pci", "prody"]].mean()
    for v in ("pci", "prody"):
        q = base[v].quantile([1 / 3, 2 / 3])
        base[f"{v}_grp"] = np.where(base[v] >= q.iloc[1], "high", np.where(base[v] < q.iloc[0], "low", "mid"))
        base.loc[base[v].isna(), f"{v}_grp"] = "na"
    prod = prod.merge(base.reset_index(), on="productId", how="left")
    prod["sector"] = prod.code.astype(str).map(sector_of)
    prod.to_csv(C.INTERIM / "product_groups_hs92.csv", index=False)
    corr = base[["pci", "prody"]].corr(method="spearman").iloc[0, 1]
    log.info("Spearman(PCI_9599, PRODY_9599) = %.3f", corr)

    # ------------------------------------------------------------------ ESI, ASEAN+3 pairs
    a3 = hs[hs.iso3.isin(C.ASEAN3)].merge(prod[["productId", "pci_grp", "prody_grp", "sector"]],
                                          on="productId", how="left")
    a3["exportValue"] = a3.exportValue.clip(lower=0).fillna(0)
    rows = []
    for yr, g in a3.groupby("year"):
        X = g.pivot_table(index="productId", columns="iso3", values="exportValue", aggfunc="sum", fill_value=0)
        tot = X.sum()
        valid = [c for c in X.columns if tot[c] > 0]
        S = X[valid] / tot[valid]
        meta = prod.set_index("productId").reindex(S.index)
        rec = {k: {"year": yr} for k in esi_matrix(S, valid)}
        for k, v in esi_matrix(S, valid).items():
            rec[k]["esi"] = v
        nonnat = ~meta.naturalResource.fillna(False).astype(bool)
        Xm = X.loc[nonnat, valid]
        Sm = Xm / Xm.sum().replace(0, np.nan)
        for k, v in esi_matrix(Sm.fillna(0), valid).items():
            rec[k]["esi_manuf"] = v
        for scheme in ("pci_grp", "prody_grp"):
            for grp in ("high", "mid", "low"):
                mask = (meta[scheme] == grp).to_numpy()
                for k, v in esi_matrix(S[mask], valid).items():
                    rec[k][f"esi_{scheme[:-4]}_{grp}"] = v
                Xg = X.loc[mask, valid]
                Sg = (Xg / Xg.sum().replace(0, np.nan)).fillna(0)
                for k, v in esi_matrix(Sg, valid).items():
                    rec[k][f"esiw_{scheme[:-4]}_{grp}"] = v
        for sec in sorted(prod.sector.dropna().unique()):
            mask = (meta.sector == sec).to_numpy()
            for k, v in esi_matrix(S[mask], valid).items():
                rec[k][f"esi_sec_{sec}"] = v
        # RCA overlap (Atlas exportRca) - Jaccard over products with RCA >= 1
        R = g.pivot_table(index="productId", columns="iso3", values="exportRca", aggfunc="first").fillna(0) >= 1
        for (a, b) in rec:
            if a in R and b in R:
                inter = int((R[a] & R[b]).sum())
                union = int((R[a] | R[b]).sum())
                rec[(a, b)]["rca_overlap_n"] = inter
                rec[(a, b)]["rca_jaccard"] = inter / union if union else np.nan
        for (a, b), r in rec.items():
            rows.append({"iso_a": a, "iso_b": b, **r})
    pair = pd.DataFrame(rows).sort_values(["iso_a", "iso_b", "year"])
    log.info("pair-year rows %d", len(pair))

    # SITC long-run ESI (1962-2024; panel countries only)
    si = load_cpy("SITC")
    si = si[si.iso3.isin(C.ASEAN3)]
    srows = []
    for yr, g in si.groupby("year"):
        X = g.pivot_table(index="productId", columns="iso3", values="exportValue", aggfunc="sum", fill_value=0)
        tot = X.sum()
        valid = [c for c in X.columns if tot[c] > 0]
        for (a, b), v in esi_matrix(X[valid] / tot[valid], valid).items():
            srows.append({"iso_a": a, "iso_b": b, "year": yr, "esi_sitc": v})
    sitc = pd.DataFrame(srows)
    pair = pair.merge(sitc, on=["iso_a", "iso_b", "year"], how="outer")
    pair = pair.sort_values(["iso_a", "iso_b", "year"]).reset_index(drop=True)

    g = pair.groupby(["iso_a", "iso_b"], group_keys=False)
    for v in ("esi", "esi_manuf", "esi_pci_high", "esi_pci_low", "esi_sitc"):
        pair[f"{v}_ma3"] = g[v].transform(lambda s: s.rolling(3, min_periods=3).mean())
        pair[f"{v}_ma5"] = g[v].transform(lambda s: s.rolling(5, min_periods=5).mean())
    # 10-year change needs consecutive years: shift by position after full year index
    full = pair.set_index(["iso_a", "iso_b", "year"])
    for v in ("esi", "esi_manuf", "esi_pci_high", "esi_sitc"):
        lag = full[v].rename(f"{v}_l10").reset_index()
        lag["year"] += 10
        pair = pair.merge(lag, on=["iso_a", "iso_b", "year"], how="left")
        pair[f"{v}_d10"] = pair[v] - pair[f"{v}_l10"]
        pair = pair.drop(columns=f"{v}_l10")
    pair = pair[pair.year >= 1962]
    pair.to_parquet(C.PROCESSED / "esi_pair_year.parquet", index=False)
    pair[pair.year >= 1995].to_csv(C.PROCESSED / "esi_pair_year.csv", index=False)

    # ------------------------------------------------------------------ directed dyad-year
    mac = pd.read_csv(C.ROOT / "data/interim/prelim/macro_country_year.csv")
    mac = mac[mac.iso3.isin(C.ASEAN3)][["iso3", "year", "gdp_usd", "gdppc_ppp_const", "gdppc_usd", "population",
                                        "eci_hs92", "eci_rank_hs92", "mva_usd", "merch_exports_usd"]]
    cx = a3.merge(prod[["productId", "naturalResource"]], on="productId", how="left", suffixes=("", "_p"))
    cx["manuf"] = ~cx.naturalResource.fillna(False).astype(bool)
    cx["hi"] = cx.pci_grp == "high"
    ctry = cx.groupby(["iso3", "year"]).apply(
        lambda d: pd.Series({"x_total": d.exportValue.sum(), "x_manuf": d.exportValue[d.manuf].sum(),
                             "x_pci_high": d.exportValue[d.hi].sum()}), include_groups=False).reset_index()
    ctry = ctry.merge(mac, on=["iso3", "year"], how="left")

    bil = []
    for f in list((A1 / "countryCountryYear").glob("HS92_*.json")) + list((A2 / "countryCountryYear").glob("HS92_*.json")):
        for r in load_json_rows(f):
            a, b = ISO_OF[r["countryId"]], ISO_OF[r["partnerCountryId"]]
            bil.append({"obs": a, "tgt": b, "year": r["year"], "x_ab": r["exportValue"], "m_ab": r["importValue"]})
    bil = pd.DataFrame(bil).drop_duplicates(["obs", "tgt", "year"])
    rev = bil.rename(columns={"obs": "tgt", "tgt": "obs", "x_ab": "m_ab", "m_ab": "x_ab"})
    bil = pd.concat([bil, rev]).drop_duplicates(["obs", "tgt", "year"])

    sym = pd.concat([pair, pair.rename(columns={"iso_a": "iso_b", "iso_b": "iso_a"})])
    sym = sym.rename(columns={"iso_a": "obs", "iso_b": "tgt"})
    dy = sym[sym.year.between(1995, 2024)].merge(bil, on=["obs", "tgt", "year"], how="left")
    o = ctry.add_prefix("o_").rename(columns={"o_iso3": "obs", "o_year": "year"})
    t = ctry.add_prefix("t_").rename(columns={"t_iso3": "tgt", "t_year": "year"})
    dy = dy.merge(o, on=["obs", "year"], how="left").merge(t, on=["tgt", "year"], how="left")
    dy["trade_ab"] = dy.x_ab.fillna(0) + dy.m_ab.fillna(0)
    dy["dep_trade_gdp_o"] = dy.trade_ab / dy.o_gdp_usd
    dy["dep_trade_gdp_t"] = dy.trade_ab / dy.t_gdp_usd
    dy["dep_asym"] = np.log(dy.dep_trade_gdp_o / dy.dep_trade_gdp_t)
    dy["rel_gdppc"] = np.log(dy.o_gdppc_ppp_const / dy.t_gdppc_ppp_const)   # >0 observer richer
    dy["rel_gdp"] = np.log(dy.o_gdp_usd / dy.t_gdp_usd)
    dy["rel_xmanuf"] = np.log(dy.o_x_manuf / dy.t_x_manuf)
    dy["rel_xhigh"] = np.log(dy.o_x_pci_high / dy.t_x_pci_high)
    dy["eci_gap"] = dy.o_eci_hs92 - dy.t_eci_hs92                            # >0 observer more complex
    dy["parity_gdppc"] = np.exp(-dy.rel_gdppc.abs())                          # 1 = parity
    dy["parity_xhigh"] = np.exp(-dy.rel_xhigh.abs())
    dy["dyad"] = dy.obs + "->" + dy.tgt
    dy["pair"] = [ "-".join(sorted(p)) for p in zip(dy.obs, dy.tgt)]

    # membership / statehood flags (historical, not retroactive)
    dy["both_asean"] = [int(C.ASEAN_ACCESSION.get(a, 9999) <= y and C.ASEAN_ACCESSION.get(b, 9999) <= y)
                        for a, b, y in zip(dy.obs, dy.tgt, dy.year)]
    wto = {k: int(v[:4]) for k, v in C.WTO_ACCESSION.items()}
    dy["both_wto"] = [int(wto[a] <= y and wto[b] <= y) for a, b, y in zip(dy.obs, dy.tgt, dy.year)]
    dy["tls_pre_state"] = [int(("TLS" in (a, b)) and y < C.STATEHOOD_FROM["TLS"]) for a, b, y in
                           zip(dy.obs, dy.tgt, dy.year)]

    geo = pd.read_csv(C.STUDY / "config/dyad_geo_history.csv")
    geo2 = geo.rename(columns={"iso_a": "iso_b", "iso_b": "iso_a"})
    geo = pd.concat([geo, geo2]).rename(columns={"iso_a": "obs", "iso_b": "tgt"})
    hier = pd.read_csv(C.STUDY / "config/directed_hierarchy.csv")
    dy = dy.merge(geo, on=["obs", "tgt"], how="left").merge(hier, on=["obs", "tgt"], how="left")
    for c in hier.columns:
        if c not in ("obs", "tgt", "source_note"):
            dy[c] = dy[c].fillna(0).astype(int)
    dy = dy.drop(columns=[c for c in dy.columns if c.startswith("source_note")])
    dy.to_parquet(C.PROCESSED / "dyad_year.parquet", index=False)
    dy.to_csv(C.PROCESSED / "dyad_year.csv", index=False)

    # ------------------------------------------------------------------ diagnostics
    cov.to_csv(C.OUT / "diagnostics/econ_hs92_country_coverage.csv", index=False)
    chk = pair[pair.year.between(1995, 2024)]
    diag = pd.DataFrame({
        "check": ["pairs", "pair-years 1995-2024", "esi range", "esi = sum(pci groups incl. na)",
                  "corr(esi, esi_sitc) 1995-2024", "spearman(PCI9599, PRODY9599)",
                  "dyad-years", "dyad-years missing bilateral trade"],
        "value": [chk[["iso_a", "iso_b"]].drop_duplicates().shape[0], len(chk),
                  f"{chk.esi.min():.2f}-{chk.esi.max():.2f}",
                  f"max abs diff {np.nanmax(np.abs(chk.esi - chk[[c for c in chk if c.startswith('esi_pci_') and c[-4:] in ('high', '_mid', '_low')]].sum(axis=1))):.3f} (residual = products without 1995-99 PCI)",
                  f"{chk[['esi', 'esi_sitc']].corr().iloc[0, 1]:.3f}", f"{corr:.3f}",
                  len(dy), int(dy.x_ab.isna().sum())],
    })
    diag.to_csv(C.OUT / "diagnostics/econ_panel_checks.csv", index=False)
    print(diag.to_string(index=False))


if __name__ == "__main__":
    main()
