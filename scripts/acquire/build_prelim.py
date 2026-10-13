"""Build low-risk preliminary derived files from the raw layer (no composite indices, no
proximity or convergence variables, no recognition measures).

Outputs (data/interim/prelim/):
    macro_country_year.csv                  WDI + Atlas ECI, one row per country-year
    income_classification_country_year.csv  World Bank FY classification, one row per country-FY
    trade_country_year.csv                  Korea-partner-year bilateral trade (Comtrade + Atlas)
    trade_product_country_year.parquet/.csv partner-product-year HS92 4-digit exports (Atlas)
    trade_bilateral_product_year.parquet    Korea<->partner HS92 4-digit flows (Atlas)
    event_transitions.csv                   formal status transitions (verified + candidates)
"""

import argparse
import json
import re
from pathlib import Path

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd
from bs4 import BeautifulSoup

from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import write_table

RAW = get_path("data.raw")
PANEL = ["KOR", "BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM", "CHN"]
M49 = {
    "KOR": 410,
    "BRN": 96,
    "KHM": 116,
    "IDN": 360,
    "LAO": 418,
    "MYS": 458,
    "MMR": 104,
    "PHL": 608,
    "SGP": 702,
    "THA": 764,
    "TLS": 626,
    "VNM": 704,
    "CHN": 156,
    "JPN": 392,
    "USA": 840,
}
ISO_OF = {v: k for k, v in M49.items()}


def latest(source: str) -> Path:
    runs = sorted(p for p in (RAW / source).iterdir() if p.is_dir())
    return runs[-1]


def out_dir() -> Path:
    path = get_path("data.interim") / "prelim"
    path.mkdir(parents=True, exist_ok=True)
    return path


# --------------------------------------------------------------------------- macro
WDI_NAMES = {
    "NY.GDP.MKTP.CD": "gdp_usd",
    "NY.GDP.MKTP.KD": "gdp_const2015_usd",
    "NY.GDP.MKTP.KD.ZG": "gdp_growth_pct",
    "NY.GDP.PCAP.CD": "gdppc_usd",
    "NY.GDP.PCAP.KD": "gdppc_const2015_usd",
    "NY.GDP.PCAP.PP.CD": "gdppc_ppp_current",
    "NY.GDP.PCAP.PP.KD": "gdppc_ppp_const",
    "NY.GNP.PCAP.CD": "gnipc_atlas_usd",
    "SP.POP.TOTL": "population",
    "SL.GDP.PCAP.EM.KD": "gdp_per_worker_ppp_const",
    "NV.IND.MANF.CD": "mva_usd",
    "NV.IND.MANF.KD": "mva_const2015_usd",
    "NV.IND.MANF.ZS": "mva_share_gdp_pct",
    "NV.IND.TOTL.ZS": "industry_share_gdp_pct",
    "TX.VAL.TECH.CD": "hightech_exports_usd",
    "TX.VAL.TECH.MF.ZS": "hightech_share_manuf_exports_pct",
    "TX.VAL.MANF.ZS.UN": "manuf_share_merch_exports_pct",
    "TX.VAL.MRCH.CD.WT": "merch_exports_usd",
    "TM.VAL.MRCH.CD.WT": "merch_imports_usd",
    "NE.EXP.GNFS.CD": "exports_gs_usd",
    "NE.TRD.GNFS.ZS": "trade_share_gdp_pct",
    "BX.KLT.DINV.CD.WD": "fdi_inflow_usd",
    "BX.KLT.DINV.WD.GD.ZS": "fdi_inflow_pct_gdp",
    "BM.KLT.DINV.CD.WD": "fdi_outflow_usd",
    "BM.KLT.DINV.WD.GD.ZS": "fdi_outflow_pct_gdp",
    "IP.PAT.RESD": "patent_apps_resident",
    "IP.PAT.NRES": "patent_apps_nonresident",
    "GB.XPD.RSDV.GD.ZS": "rnd_pct_gdp",
    "SP.POP.SCIE.RD.P6": "researchers_per_million",
}


def build_macro(logger) -> pd.DataFrame:
    run = latest("wb_wdi")
    rows = []
    for f in sorted(run.glob("indicator_*.json")):
        for page in json.loads(f.read_text(encoding="utf-8")):
            for obs in (page[1] or []) if isinstance(page, list) and len(page) > 1 else []:
                rows.append(
                    {
                        "iso3": obs["countryiso3code"],
                        "year": int(obs["date"]),
                        "indicator": obs["indicator"]["id"],
                        "value": obs["value"],
                    }
                )
    long = pd.DataFrame(rows)
    wide = long.pivot_table(index=["iso3", "year"], columns="indicator", values="value", aggfunc="first")
    wide = wide.rename(columns=WDI_NAMES).reset_index()
    vintage = json.loads((run / "wdi_source_record.json").read_text(encoding="utf-8"))
    wide["wdi_lastupdated"] = vintage[1][0].get("lastupdated") if isinstance(vintage, list) else ""
    # Atlas ECI (HS92 1995+, SITC 1962+) incl. ECI rank among ranked countries
    arun = latest("complexity_atlas")
    loc = pd.DataFrame(
        json.loads((arun / "meta/locationCountry.json").read_text(encoding="utf-8"))["data"][
            "locationCountry"
        ]
    )
    loc["cid"] = loc["countryId"]
    for cls in ("HS92", "SITC"):
        cy = pd.DataFrame(
            json.loads((arun / f"countryYear_{cls}.json").read_text(encoding="utf-8"))["data"]["countryYear"]
        )
        cy = cy.merge(loc[["cid", "iso3Code"]], left_on="countryId", right_on="cid", how="left")
        cy[f"eci_rank_{cls.lower()}"] = cy.groupby("year")["eci"].rank(ascending=False, method="min")
        cy[f"eci_n_ranked_{cls.lower()}"] = cy.groupby("year")["eci"].transform("count")
        cy = cy.rename(
            columns={
                "iso3Code": "iso3",
                "eci": f"eci_{cls.lower()}",
                "coi": f"coi_{cls.lower()}",
                "exportValue": f"atlas_exports_{cls.lower()}",
            }
        )
        wide = wide.merge(
            cy[
                [
                    "iso3",
                    "year",
                    f"eci_{cls.lower()}",
                    f"eci_rank_{cls.lower()}",
                    f"eci_n_ranked_{cls.lower()}",
                    f"coi_{cls.lower()}",
                    f"atlas_exports_{cls.lower()}",
                ]
            ],
            on=["iso3", "year"],
            how="left",
        )
    wide = wide[wide["year"] >= 1960].sort_values(["iso3", "year"])
    logger.info(
        "macro: %d rows, %d countries, %d-%d",
        len(wide),
        wide["iso3"].nunique(),
        wide["year"].min(),
        wide["year"].max(),
    )
    return wide


# --------------------------------------------------------------------------- income classes
GROUP = {
    "L": "low",
    "LM": "lower_middle",
    "UM": "upper_middle",
    "H": "high",
    "..": None,
    "LM*": "lower_middle",
}


def build_income(logger) -> pd.DataFrame:
    run = latest("wb_income_class")
    d = pd.read_excel(run / "OGHIST.xlsx", sheet_name="Country Analytical History", header=None)
    fys = d.iloc[4, 2:].tolist()
    rows = []
    for _, r in d.iloc[11:].iterrows():
        iso = r[0]
        if not isinstance(iso, str) or len(iso) != 3:
            continue
        for fy, v in zip(fys, r.iloc[2:].tolist(), strict=True):
            if isinstance(fy, str) and fy.startswith("FY"):
                rows.append(
                    {
                        "iso3": iso,
                        "fy": 1900 + int(fy[2:]) if int(fy[2:]) > 50 else 2000 + int(fy[2:]),
                        "income_code": v if isinstance(v, str) else None,
                        "source": "OGHIST.xlsx (Country Analytical History)",
                    }
                )
    inc = pd.DataFrame(rows)
    # FY26 / FY27 changes from the official classification notes (target countries only changed in FY27)
    last = inc[inc["fy"] == inc["fy"].max()].copy()
    fy26 = last.assign(
        fy=2026,
        source="OGHIST FY25 carried forward; FY26 note lists no change "
        "(FY26_updated_country_income_classification.pdf)",
    )
    fy26_changes = {"CPV": "UM", "CRI": "H", "WSM": "UM", "NAM": "LM"}
    fy26["income_code"] = [
        fy26_changes.get(i, c) for i, c in zip(fy26["iso3"], fy26["income_code"], strict=True)
    ]
    fy27_changes = {"JOR": "UM", "FSM": "UM", "PHL": "UM", "LKA": "UM", "TGO": "LM", "VNM": "UM"}
    fy27 = fy26.assign(
        fy=2027, source="FY26 carried forward; FY27 note (FY27_updated_country_income_classification.pdf)"
    )
    fy27["income_code"] = [
        fy27_changes.get(i, c) for i, c in zip(fy27["iso3"], fy27["income_code"], strict=True)
    ]
    for df, ch in ((fy26, fy26_changes), (fy27, fy27_changes)):
        df.loc[df["iso3"].isin(ch), "source"] = (
            df.loc[df["iso3"].isin(ch), "source"].str.replace("carried forward; ", "") + " [changed]"
        )
    inc = pd.concat([inc, fy26, fy27], ignore_index=True)
    inc["income_group"] = inc["income_code"].map(GROUP)
    inc["effective_from"] = (inc["fy"] - 1).astype(str) + "-07-01"
    inc["effective_to"] = inc["fy"].astype(str) + "-06-30"
    inc["gni_data_year"] = inc["fy"] - 2
    inc["calendar_year_announced"] = inc["fy"] - 1
    inc = inc.sort_values(["iso3", "fy"])
    inc["prev_income_code"] = inc.groupby("iso3")["income_code"].shift()
    inc["transition"] = (
        inc["income_code"].ne(inc["prev_income_code"])
        & inc["prev_income_code"].notna()
        & inc["income_code"].notna()
        & ~inc["income_code"].isin([".."])
        & ~inc["prev_income_code"].isin([".."])
    )
    logger.info("income: %d country-FY rows; FY%d-FY%d", len(inc), inc["fy"].min(), inc["fy"].max())
    return inc


def income_consistency(inc: pd.DataFrame, macro: pd.DataFrame) -> pd.DataFrame:
    """Recompute groups from the CURRENT WDI GNI vintage and the historical thresholds; mismatches
    reflect data revisions (classifications are fixed at announcement) and are expected."""
    run = latest("wb_income_class")
    th = pd.read_excel(run / "OGHIST.xlsx", sheet_name="Country Analytical History", header=None)
    fys, lm = th.iloc[4, 2:].tolist(), th.iloc[7, 2:].tolist()
    um = th.iloc[8, 2:].tolist()

    def upper(s):
        nums = re.findall(r"[\d,]+", str(s))
        return float(nums[-1].replace(",", "")) if nums else np.nan

    t = pd.DataFrame(
        {
            "fy": [2000 + int(f[2:]) if int(f[2:]) < 50 else 1900 + int(f[2:]) for f in fys],
            "lm_max": [upper(x) for x in lm],
            "um_max": [upper(x) for x in um],
            "l_max": [upper(x.split("-")[0]) - 1 if "-" in str(x) else np.nan for x in lm],
        }
    )
    m = inc.merge(t, on="fy").merge(
        macro[["iso3", "year", "gnipc_atlas_usd"]],
        left_on=["iso3", "gni_data_year"],
        right_on=["iso3", "year"],
        how="left",
    )
    g = m["gnipc_atlas_usd"]
    m["recomputed_code"] = np.select(
        [g <= m["l_max"], g <= m["lm_max"], g <= m["um_max"], g > m["um_max"]],
        ["L", "LM", "UM", "H"],
        default=None,
    )
    m = m[m["iso3"].isin(PANEL) & g.notna()]
    m["consistent"] = m["recomputed_code"] == m["income_code"].str.replace("*", "", regex=False)
    return m[
        ["iso3", "fy", "gni_data_year", "gnipc_atlas_usd", "income_code", "recomputed_code", "consistent"]
    ]


# --------------------------------------------------------------------------- trade
def build_trade(logger) -> pd.DataFrame:
    run = latest("un_comtrade")
    recs = []
    for f in sorted((run / "totals").glob("totals_*.json")):
        recs += json.loads(f.read_text(encoding="utf-8")).get("data", [])
    ct = pd.DataFrame(recs)
    ct = ct[
        (ct["cmdCode"] == "TOTAL")
        & (ct["motCode"] == 0)
        & (ct["partner2Code"] == 0)
        & (ct["customsCode"] == "C00")
    ]
    ct["rep"] = ct["reporterCode"].map(ISO_OF)
    ct["par"] = ct["partnerCode"].map(ISO_OF).fillna(ct["partnerCode"].map({0: "WLD"}))
    val = ct.groupby(["rep", "par", "refYear", "flowCode"])["primaryValue"].sum().rename("v").reset_index()
    get = val.set_index(["rep", "par", "refYear", "flowCode"])["v"]
    hs_class = ct.groupby(["rep", "refYear"])["classificationCode"].first()
    rows = []
    years = sorted(val["refYear"].unique())
    for p in PANEL[1:]:
        for y in years:
            g = lambda r, q, f, y=y: get.get((r, q, y, f), np.nan)  # noqa: E731
            rows.append(
                {
                    "partner": p,
                    "year": int(y),
                    "kor_exports_to_partner_kr": g("KOR", p, "X"),
                    "kor_imports_from_partner_kr": g("KOR", p, "M"),
                    "partner_exports_to_kor_mirror": g(p, "KOR", "X"),
                    "partner_imports_from_kor_mirror": g(p, "KOR", "M"),
                    "kor_exports_world": g("KOR", "WLD", "X"),
                    "kor_imports_world": g("KOR", "WLD", "M"),
                    "partner_exports_world": g(p, "WLD", "X"),
                    "partner_imports_world": g(p, "WLD", "M"),
                    "hs_class_kor": hs_class.get(("KOR", y)),
                    "hs_class_partner": hs_class.get((p, y)),
                }
            )
    tr = pd.DataFrame(rows)
    tr["kor_total_trade_with_partner"] = tr["kor_exports_to_partner_kr"] + tr["kor_imports_from_partner_kr"]
    tr["share_kor_trade"] = tr["kor_total_trade_with_partner"] / (
        tr["kor_exports_world"] + tr["kor_imports_world"]
    )
    tr["share_kor_exports"] = tr["kor_exports_to_partner_kr"] / tr["kor_exports_world"]
    tr["share_kor_imports"] = tr["kor_imports_from_partner_kr"] / tr["kor_imports_world"]
    tr["share_partner_exports_to_kor"] = tr["partner_exports_to_kor_mirror"] / tr["partner_exports_world"]
    tr["share_partner_imports_from_kor"] = tr["partner_imports_from_kor_mirror"] / tr["partner_imports_world"]
    tr = tr.sort_values(["partner", "year"])
    tr["kor_trade_growth"] = tr.groupby("partner")["kor_total_trade_with_partner"].pct_change(
        fill_method=None
    )
    tr["mirror_gap_kor_exports"] = (
        tr["partner_imports_from_kor_mirror"] / tr["kor_exports_to_partner_kr"]
    ) - 1
    # Atlas reconciled bilateral flows (HS92, 1995+)
    arun = latest("complexity_atlas")
    at = []
    for f in sorted((arun / "countryCountryYear").glob("HS92_KOR_*.json")):
        at += json.loads(f.read_text(encoding="utf-8"))["data"]["countryCountryYear"]
    at = pd.DataFrame(at)
    at["partner"] = at["partnerCountryId"].str.replace("country-", "").astype(int).map(ISO_OF)
    at = at.rename(
        columns={
            "exportValue": "atlas_kor_exports_to_partner",
            "importValue": "atlas_kor_imports_from_partner",
        }
    )
    tr = tr.merge(
        at[["partner", "year", "atlas_kor_exports_to_partner", "atlas_kor_imports_from_partner"]],
        on=["partner", "year"],
        how="outer",
    ).sort_values(["partner", "year"])
    tr["comtrade_source"] = "UN Comtrade public preview API, HS as reported, TOTAL, C00"
    logger.info("trade: %d partner-years; Comtrade years %s-%s", len(tr), min(years), max(years))
    return tr


def build_hs2(logger) -> pd.DataFrame:
    """Korea x partner x HS2 chapter x year from Comtrade (both reporting directions kept)."""
    run = latest("un_comtrade")
    recs = []
    for f in sorted((run / "hs2").glob("hs2_KOR_*.json")):
        recs += json.loads(f.read_text(encoding="utf-8")).get("data", [])
    df = pd.DataFrame(recs)
    if df.empty:
        return df
    df = df[(df["motCode"] == 0) & (df["partner2Code"] == 0) & (df["customsCode"] == "C00")]
    df["reporter"] = df["reporterCode"].map(ISO_OF)
    df["partner_iso"] = df["partnerCode"].map(ISO_OF)
    out = df.rename(columns={"refYear": "year", "cmdCode": "hs2", "flowCode": "flow",
                             "primaryValue": "value_usd", "classificationCode": "hs_class"})
    out["dyad_partner"] = np.where(out["reporter"] == "KOR", out["partner_iso"], out["reporter"])
    out["reported_by"] = np.where(out["reporter"] == "KOR", "KOR", "partner")
    out = out[["dyad_partner", "year", "hs2", "reporter", "partner_iso", "reported_by", "flow",
               "value_usd", "hs_class"]].sort_values(["dyad_partner", "year", "reported_by", "flow", "hs2"])
    logger.info("hs2: %d rows; dyads %s", len(out), out.groupby("dyad_partner")["year"].nunique().to_dict())
    return out


def build_products(logger) -> tuple[pd.DataFrame, pd.DataFrame]:
    arun = latest("complexity_atlas")
    prod = pd.DataFrame(
        json.loads((arun / "meta/productHs92_level4.json").read_text(encoding="utf-8"))["data"]["productHs92"]
    )[["productId", "code", "nameShortEn", "naturalResource", "greenProduct"]]
    pci = pd.DataFrame(
        json.loads((arun / "productYear_HS92_level4.json").read_text(encoding="utf-8"))["data"]["productYear"]
    )[["productId", "year", "pci"]]
    rows = []
    for f in sorted((arun / "countryProductYear").glob("HS92_L4_*.json")):
        rows += json.loads(f.read_text(encoding="utf-8"))["data"]["countryProductYear"]
    cpy = pd.DataFrame(rows)
    cpy["iso3"] = cpy["countryId"].str.replace("country-", "").astype(int).map(ISO_OF)
    cpy = cpy.merge(prod, on="productId", how="left").merge(pci, on=["productId", "year"], how="left")
    cpy = cpy.rename(
        columns={
            "code": "hs92_4",
            "nameShortEn": "product_name",
            "exportValue": "export_value",
            "importValue": "import_value",
            "exportRca": "export_rca",
            "globalMarketShare": "global_market_share",
        }
    )
    cpy = cpy[
        [
            "iso3",
            "year",
            "hs92_4",
            "product_name",
            "export_value",
            "import_value",
            "export_rca",
            "global_market_share",
            "pci",
            "naturalResource",
            "greenProduct",
        ]
    ].sort_values(["iso3", "year", "hs92_4"])
    rows = []
    for f in sorted((arun / "ccpy").glob("L4_KOR_*.json")):
        rows += json.loads(f.read_text(encoding="utf-8"))["data"]["countryCountryProductYear"]
    bi = pd.DataFrame(rows)
    bi["partner"] = bi["partnerCountryId"].str.replace("country-", "").astype(int).map(ISO_OF)
    bi = bi.merge(prod[["productId", "code"]], on="productId", how="left").rename(
        columns={
            "code": "hs92_4",
            "exportValue": "kor_exports_to_partner",
            "importValue": "kor_imports_from_partner",
        }
    )
    bi = bi[["partner", "year", "hs92_4", "kor_exports_to_partner", "kor_imports_from_partner"]]
    logger.info("products: %d country-product-years; bilateral %d rows", len(cpy), len(bi))
    return cpy, bi


# --------------------------------------------------------------------------- events
def _text(path: Path) -> str:
    return BeautifulSoup(path.read_bytes(), "lxml").get_text(" ", strip=True)


MONTHS = {
    m: i
    for i, m in enumerate(
        [
            "January",
            "February",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "November",
            "December",
        ],
        start=1,
    )
}


def build_events(inc: pd.DataFrame, logger) -> pd.DataFrame:
    ev = []
    for r in inc[inc["transition"] & inc["iso3"].isin(PANEL)].itertuples():
        src = (
            "https://datacatalogfiles.worldbank.org/ddh-published/0037712/DR0090754/OGHIST.xlsx"
            if r.fy <= 2025
            else "https://documents.worldbank.org/en/publication/documents-reports/"
            "documentdetail/099063026190549947"
        )
        ev.append(
            {
                "country": r.iso3,
                "event_type": "wb_income_classification",
                "event_name": f"World Bank income group change effective FY{r.fy}",
                "event_date": r.effective_from,
                "event_year": r.calendar_year_announced,
                "old_status": GROUP.get(r.prev_income_code),
                "new_status": r.income_group,
                "source": "World Bank Country and Lending Groups",
                "source_url": src,
                "verification": "verified_official_file",
                "notes": f"FY{r.fy}; based on {r.gni_data_year} Atlas GNI per capita; "
                f"announced 1 July {r.fy - 1}",
            }
        )
    # LDC (UN list as of 19 Dec 2024)
    ldc_url = "https://www.un.org/development/desa/dpad/wp-content/uploads/sites/45/publication/ldc_list.pdf"
    for iso, yr in {"KHM": 1991, "LAO": 1971, "MMR": 1987, "TLS": 2003}.items():
        ev.append(
            {
                "country": iso,
                "event_type": "ldc_inclusion",
                "event_name": "Included in UN LDC category",
                "event_date": "",
                "event_year": yr,
                "old_status": "",
                "new_status": "LDC",
                "source": "UN DESA, List of LDCs (as of 19 December 2024)",
                "source_url": ldc_url,
                "verification": "verified_official_file",
                "notes": "year of inclusion only",
            }
        )
    for iso, d, res in (("LAO", "2026-11-24", "A/RES/76/8"), ("KHM", "2029-12-19", "A/RES/79/230")):
        ev.append(
            {
                "country": iso,
                "event_type": "ldc_graduation_scheduled",
                "event_name": "Scheduled graduation from LDC category",
                "event_date": d,
                "event_year": int(d[:4]),
                "old_status": "LDC",
                "new_status": "graduated (scheduled)",
                "source": "UN DESA, List of LDCs (as of 19 December 2024)",
                "source_url": ldc_url,
                "verification": "verified_official_file",
                "notes": f"GA resolution {res}; future-dated - confirm it took effect",
            }
        )
    # WTO membership
    ev_run = latest("event_sources")
    names = {
        "BRN": "brunei_darussalam",
        "KHM": "cambodia",
        "CHN": "china",
        "IDN": "indonesia",
        "KOR": "korea_republic",
        "LAO": "lao_pdr",
        "MYS": "malaysia",
        "MMR": "myanmar",
        "PHL": "philippines",
        "SGP": "singapore",
        "THA": "thailand",
        "VNM": "vietnam",
        "TLS": "timor_leste",
    }
    files = {"LAO": ("wto_country_LAO_v2.html", "lao")}  # first LAO slug returned a soft 404
    for iso, slug in names.items():
        fname, slug = files.get(iso, (f"wto_country_{iso}.html", slug))
        f = ev_run / fname
        if not f.exists():
            continue
        m = re.search(
            r"(?:member of (?:the )?WTO|WTO member)\s+since\s+(\d{1,2})\s+(\w+)\s+(\d{4})", _text(f)
        )
        if m:
            date = f"{m.group(3)}-{MONTHS[m.group(2)]:02d}-{int(m.group(1)):02d}"
            ev.append(
                {
                    "country": iso,
                    "event_type": "wto_membership",
                    "event_name": "WTO membership",
                    "event_date": date,
                    "event_year": int(m.group(3)),
                    "old_status": "non-member",
                    "new_status": "WTO member",
                    "source": "WTO member information page",
                    "source_url": f"https://www.wto.org/english/thewto_e/countries_e/{slug}_e.htm",
                    "verification": "verified_official_page",
                    "notes": "",
                }
            )
        else:
            logger.warning("WTO date not parsed for %s", iso)
    # Korea FTAs (official portal fta.motir.go.kr)
    fta = {
        "sg": ("SGP", "Korea-Singapore FTA"),
        "asean": ("ASEAN", "Korea-ASEAN FTA"),
        "cn": ("CHN", "Korea-China FTA"),
        "vn": ("VNM", "Korea-Viet Nam FTA"),
        "kh": ("KHM", "Korea-Cambodia FTA"),
        "id": ("IDN", "Korea-Indonesia CEPA"),
        "ph": ("PHL", "Korea-Philippines FTA"),
        "ksdpa": ("SGP", "Korea-Singapore Digital Partnership Agreement"),
    }
    for cc, (iso, name) in fta.items():
        f = ev_run / f"fta_{cc}.html"
        if not f.exists():
            continue
        t = _text(f)
        m = re.search(r"(\d{4})년\s*(\d{1,2})월\s*(\d{1,2})일\s*[^.]{0,40}?발효", t)
        date = f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}" if m else ""
        ev.append(
            {
                "country": iso,
                "event_type": "fta_entry_into_force_korea",
                "event_name": name,
                "event_date": date,
                "event_year": int(m.group(1)) if m else np.nan,
                "old_status": "",
                "new_status": "in force",
                "source": "Korea FTA portal (fta.motir.go.kr)",
                "source_url": f"https://fta.motir.go.kr/ftamain/kfta/lov5/{cc}/1",
                "verification": "verified_official_page" if m else "parse_failed_check_manually",
                "notes": "first dated '...발효' statement on the agreement page; ASEAN = goods agreement"
                if cc == "asean"
                else "",
            }
        )
    ev.append(
        {
            "country": "MYS",
            "event_type": "fta_status_korea",
            "event_name": "Korea-Malaysia FTA",
            "event_date": "",
            "event_year": np.nan,
            "old_status": "",
            "new_status": "signed/concluded (not in force)",
            "source": "Korea FTA portal status list",
            "source_url": "https://fta.motir.go.kr/ftamain/kfta/lov3/my/1",
            "verification": "verified_official_page",
            "notes": "listed under 서명/타결 at retrieval",
        }
    )
    ev.append(
        {
            "country": "THA",
            "event_type": "fta_status_korea",
            "event_name": "Korea-Thailand CEPA",
            "event_date": "",
            "event_year": np.nan,
            "old_status": "",
            "new_status": "under negotiation",
            "source": "Korea FTA portal status list",
            "source_url": "https://fta.motir.go.kr/ftamain/kfta/lov1/th/1",
            "verification": "verified_official_page",
            "notes": "listed under 협상중 at retrieval",
        }
    )
    # Candidates requiring verification against the MOFA corpus / official joint statements
    for iso, name, yr, new in [
        ("CHN", "Korea-China strategic cooperative partnership", 2008, "strategic cooperative partnership"),
        (
            "VNM",
            "Korea-Viet Nam strategic cooperative partnership",
            2009,
            "strategic cooperative partnership",
        ),
        (
            "VNM",
            "Korea-Viet Nam comprehensive strategic partnership",
            2022,
            "comprehensive strategic partnership",
        ),
        ("IDN", "Korea-Indonesia strategic partnership", 2006, "strategic partnership"),
        ("IDN", "Korea-Indonesia special strategic partnership", 2017, "special strategic partnership"),
        (
            "ASEAN",
            "Korea-ASEAN comprehensive strategic partnership",
            2024,
            "comprehensive strategic partnership",
        ),
        ("THA", "Korea-Thailand strategic partnership", 2012, "strategic partnership"),
        ("KHM", "Korea-Cambodia strategic partnership", 2024, "strategic partnership"),
        ("PHL", "Korea-Philippines strategic partnership", 2024, "strategic partnership"),
        ("TLS", "Timor-Leste admitted to ASEAN", 2025, "ASEAN member"),
    ]:
        ev.append(
            {
                "country": iso,
                "event_type": "partnership_upgrade_korea"
                if "ASEAN member" not in new
                else "asean_membership",
                "event_name": name,
                "event_date": "",
                "event_year": yr,
                "old_status": "",
                "new_status": new,
                "source": "",
                "source_url": "",
                "verification": "candidate_unverified",
                "notes": "from background knowledge; verify date/wording in MOFA joint statements "
                "(scripts/acquire/verify_partnerships.py) before use",
            }
        )
    df = pd.DataFrame(ev)
    df = df[
        [
            "country",
            "event_type",
            "event_name",
            "event_date",
            "event_year",
            "old_status",
            "new_status",
            "source",
            "source_url",
            "verification",
            "notes",
        ]
    ].sort_values(["country", "event_year"])
    logger.info("events: %d (%s)", len(df), df["verification"].value_counts().to_dict())
    return df


def main(args, logger) -> None:
    out = out_dir()
    diag = get_path("outputs.diagnostics", mkdir=True)
    macro = build_macro(logger)
    write_table(macro, out / "macro_country_year.csv")
    inc = build_income(logger)
    write_table(inc, out / "income_classification_country_year.csv")
    write_table(income_consistency(inc, macro), diag / "income_classification_consistency.csv")
    if (RAW / "un_comtrade").exists():
        write_table(build_trade(logger), out / "trade_country_year.csv")
        write_table(build_hs2(logger), out / "trade_hs2_korea_partner_year.parquet")
    cpy, bi = build_products(logger)
    write_table(cpy, out / "trade_product_country_year.parquet")
    write_table(cpy[cpy["iso3"].isin(PANEL)], out / "trade_product_country_year.csv")
    write_table(bi, out / "trade_bilateral_product_year.parquet")
    write_table(build_events(inc, logger), out / "event_transitions.csv")


if __name__ == "__main__":
    run_step("build_prelim", main, argparse.ArgumentParser(description=__doc__))
