"""Quality diagnostics for the preliminary files (section 11 of the collection brief).

Writes to outputs/diagnostics/:
    qc_summary.csv                one row per check with a status and a count
    macro_missing_years.csv       indicator x country: first/last year and gaps within span
    trade_quality.csv             Korea-partner-year flags: negatives, mirror gaps, breaks, HS revisions
    macro_breaks.csv              |log change| > threshold in level series (possible source breaks)
    wdi_unit_check.csv            unit / source-note per indicator (unit changes)
    country_name_check.csv        dataset names that do not normalize to a configured ISO3
    coverage_table.csv            source x construct coverage (compact table for the status report)
"""

import argparse
import json

import _bootstrap  # noqa: F401
import numpy as np
import pandas as pd

from srl.utils.cli import run_step
from srl.utils.config import get_path, load_config
from srl.utils.countries import unmatched_names
from srl.utils.io import write_table

PANEL = ["KOR", "BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM", "CHN"]
LEVELS = [
    "gdp_usd",
    "gdppc_usd",
    "gdppc_ppp_const",
    "mva_usd",
    "hightech_exports_usd",
    "merch_exports_usd",
    "patent_apps_resident",
    "gdp_per_worker_ppp_const",
]


def main(args, logger) -> None:
    pre = get_path("data.interim") / "prelim"
    diag = get_path("outputs.diagnostics", mkdir=True)
    raw = get_path("data.raw")
    qc = []

    macro = pd.read_csv(pre / "macro_country_year.csv")
    macro = macro[macro["iso3"].isin(PANEL)]
    qc.append(("macro duplicate country-year rows", int(macro.duplicated(["iso3", "year"]).sum())))
    ind_cols = [c for c in macro.columns if c not in ("iso3", "year", "wdi_lastupdated")]
    rows = []
    for c in ind_cols:
        for iso, g in macro.groupby("iso3"):
            yrs = g.loc[g[c].notna(), "year"]
            if yrs.empty:
                rows.append(
                    {
                        "indicator": c,
                        "iso3": iso,
                        "first": None,
                        "last": None,
                        "n_obs": 0,
                        "gaps_in_span": None,
                    }
                )
                continue
            span = set(range(int(yrs.min()), int(yrs.max()) + 1))
            rows.append(
                {
                    "indicator": c,
                    "iso3": iso,
                    "first": int(yrs.min()),
                    "last": int(yrs.max()),
                    "n_obs": len(yrs),
                    "gaps_in_span": len(span - set(yrs.astype(int))),
                }
            )
    miss = pd.DataFrame(rows)
    write_table(miss, diag / "macro_missing_years.csv")
    # all-13 balanced window per indicator (key for proximity feasibility)
    bal = []
    for c in ind_cols:
        m = miss[miss["indicator"] == c]
        ok = m["n_obs"] > 0
        bal.append(
            {
                "indicator": c,
                "countries_with_data": int(ok.sum()),
                "common_start": m.loc[ok, "first"].max() if ok.any() else None,
                "common_end": m.loc[ok, "last"].min() if ok.any() else None,
                "countries_missing": "|".join(m.loc[~ok, "iso3"]),
            }
        )
    write_table(pd.DataFrame(bal), diag / "macro_balanced_window.csv")

    br = []
    for c in [x for x in LEVELS if x in macro]:
        g = macro.sort_values("year").groupby("iso3")[c]
        d = (
            np.log(macro.sort_values("year")[c].where(lambda s: s > 0))
            .groupby(macro.sort_values("year")["iso3"])
            .diff()
        )
        flagged = (
            macro.sort_values("year")
            .loc[d.abs() > 0.5, ["iso3", "year"]]
            .assign(indicator=c, dlog=d[d.abs() > 0.5])
        )
        br.append(flagged)
        del g
    breaks = pd.concat(br, ignore_index=True) if br else pd.DataFrame()
    write_table(breaks, diag / "macro_breaks.csv")
    qc.append(("macro |dlog|>0.5 year-on-year jumps (inspect)", len(breaks)))

    units = []
    wdi_run = sorted((raw / "wb_wdi").iterdir())[-1]
    for f in sorted((wdi_run / "meta").glob("*.json")):
        m = json.loads(f.read_text(encoding="utf-8"))
        m = m[1][0] if isinstance(m, list) and len(m) > 1 else {}
        units.append(
            {
                "indicator": m.get("id"),
                "name": m.get("name"),
                "unit": m.get("unit"),
                "source": (m.get("source") or {}).get("value"),
                "note": (m.get("sourceNote") or "")[:300],
            }
        )
    write_table(pd.DataFrame(units), diag / "wdi_unit_check.csv")
    ppp = [u["name"] for u in units if u["name"] and "PPP" in u["name"]]
    qc.append(("WDI PPP series base year (see names)", len(ppp)))

    tr = pd.read_csv(pre / "trade_country_year.csv")
    vals = [c for c in tr.columns if c.endswith(("_kr", "_mirror", "_world")) or c.startswith("atlas_")]
    neg = int((tr[vals] < 0).sum().sum())
    qc.append(("negative trade values", neg))
    qc.append(("trade duplicate partner-year rows", int(tr.duplicated(["partner", "year"]).sum())))
    tr = tr.sort_values(["partner", "year"])
    tr["hs_revision_kor"] = (
        tr["hs_class_kor"].ne(tr.groupby("partner")["hs_class_kor"].shift())
        & tr.groupby("partner")["hs_class_kor"].shift().notna()
    )
    tr["hs_revision_partner"] = (
        tr["hs_class_partner"].ne(tr.groupby("partner")["hs_class_partner"].shift())
        & tr.groupby("partner")["hs_class_partner"].shift().notna()
    )
    tr["flag_mirror_gap_gt25pct"] = tr["mirror_gap_kor_exports"].abs() > 0.25
    dl = np.log(tr["kor_total_trade_with_partner"].where(lambda s: s > 0)).groupby(tr["partner"]).diff()
    tr["flag_trade_break_dlog_gt_0_7"] = dl.abs() > 0.7
    tr["flag_missing_kor_reported"] = tr["kor_exports_to_partner_kr"].isna()
    tr["flag_missing_mirror"] = tr["partner_imports_from_kor_mirror"].isna()
    tr["comtrade_vs_atlas_ratio"] = tr["kor_exports_to_partner_kr"] / tr["atlas_kor_exports_to_partner"]
    flags = [c for c in tr.columns if c.startswith("flag_") or c.startswith("hs_revision")]
    write_table(
        tr[
            [
                "partner",
                "year",
                "hs_class_kor",
                "hs_class_partner",
                "mirror_gap_kor_exports",
                "comtrade_vs_atlas_ratio",
                *flags,
            ]
        ],
        diag / "trade_quality.csv",
    )
    for c in flags:
        qc.append((f"trade {c}", int(tr[c].sum())))

    names = []
    wdi_names = []
    for f in sorted(wdi_run.glob("indicator_*.json"))[:1]:
        for page in json.loads(f.read_text(encoding="utf-8")):
            wdi_names += [o["country"]["value"] for o in (page[1] or [])]
    names.append(("WDI", unmatched_names(pd.Series(wdi_names))))
    ct_run = sorted((raw / "un_comtrade").iterdir())[-1]
    recs = []
    for f in sorted((ct_run / "totals").glob("*.json")):
        recs += json.loads(f.read_text(encoding="utf-8")).get("data", [])
    ct = pd.DataFrame(recs)
    if "reporterDesc" in ct:
        names.append(("Comtrade reporterDesc", unmatched_names(ct["reporterDesc"])))
        names.append(("Comtrade partnerDesc", unmatched_names(ct["partnerDesc"])))
        codes = ct.groupby("reporterDesc")["reporterCode"].nunique()
        qc.append(("Comtrade reporters with >1 numeric code over time", int((codes > 1).sum())))
    write_table(
        pd.DataFrame([{"dataset": d, "unmatched_name": n} for d, ns in names for n in ns]),
        diag / "country_name_check.csv",
    )
    qc.append(
        ("dataset country names not normalizable (excl. aggregates; see file)", sum(len(n) for _, n in names))
    )

    inc = pd.read_csv(diag / "income_classification_consistency.csv")
    qc.append(
        (
            "income class != recomputed from current GNI vintage (revisions; expected)",
            int((~inc["consistent"]).sum()),
        )
    )

    gov = pre / "gov_documents_korea.csv"
    if gov.exists():
        g = pd.read_csv(gov, low_memory=False)
        qc.append(("gov documents: duplicate doc_id", int(g["doc_id"].duplicated().sum())))
        qc.append(
            ("gov documents: cross-source duplicates (title+date)", int(g["is_cross_source_duplicate"].sum()))
        )
        qc.append(("gov documents: missing date", int(g["date"].isna().sum())))

    write_table(pd.DataFrame(qc, columns=["check", "count"]), diag / "qc_summary.csv")
    write_table(coverage_table(macro, tr, gov), diag / "coverage_table.csv")
    logger.info("QC:\n%s", pd.DataFrame(qc, columns=["check", "count"]).to_string(index=False))


def coverage_table(macro: pd.DataFrame, tr: pd.DataFrame, gov_path) -> pd.DataFrame:
    sources = load_config("sources")["sources"]

    def row(src, construct, countries, start, end, freq, limits):
        s = sources.get(src, {})
        return {
            "source": src,
            "construct": construct,
            "countries_covered": countries,
            "start_year": start,
            "end_year": end,
            "frequency": freq,
            "downloaded": s.get("status") in ("validated", "partial"),
            "validated": s.get("status") in ("validated", "partial"),
            "main_limitations": limits,
        }

    out = []
    g = macro[macro["gdppc_usd"].notna()]
    out.append(
        row(
            "wb_wdi",
            "A objective status",
            g["iso3"].nunique(),
            int(g["year"].min()),
            int(g["year"].max()),
            "annual",
            "MVA/high-tech/patents/R&D sparse for BRN, LAO, MMR, TLS and early years",
        )
    )
    e = macro[macro["eci_hs92"].notna()]
    out.append(
        row(
            "complexity_atlas",
            "A status (ECI) / C overlap (HS4 exports, RCA)",
            e["iso3"].nunique(),
            int(e["year"].min()),
            int(e["year"].max()),
            "annual",
            "ECI not computed for some small economies (BRN, LAO, MMR, TLS vary); HS4 only via API",
        )
    )
    k = tr[tr["kor_exports_to_partner_kr"].notna()]
    out.append(
        row(
            "un_comtrade",
            "D interdependence (bilateral totals, HS2)",
            k["partner"].nunique(),
            int(k["year"].min()),
            int(k["year"].max()),
            "annual",
            "preview API quota; mirror data sparse for LAO/MMR/TLS; HS2 dyads may be incomplete",
        )
    )
    out.append(
        row(
            "oecd_fdi",
            "D interdependence (FDI by counterpart)",
            12,
            1985,
            2024,
            "annual",
            "Korea-reported; confidentiality suppression; BMD3/BMD4 break ~2013",
        )
    )
    out.append(row("unctad", "D interdependence (aggregate FDI)", 13, 1970, 2024, "annual", "aggregate only"))
    out.append(
        row(
            "wb_income_class",
            "H formal transitions",
            13,
            1989,
            2027,
            "annual (FY)",
            "FY26/FY27 from official notes, not OGHIST file",
        )
    )
    out.append(
        row(
            "event_sources",
            "H formal transitions (WTO, LDC, FTA)",
            13,
            1995,
            2029,
            "event",
            "strategic partnerships still candidates (task V1)",
        )
    )
    if gov_path.exists():
        gv = pd.read_csv(gov_path, low_memory=False)
        for src, gg in gv.groupby("source_id"):
            ft = gg[gg["text_status"] == "full_text"]
            out.append(
                row(
                    src,
                    "E attention / F recognition (text)",
                    "n/a",
                    int(gg["year"].min()),
                    int(gg["year"].max()),
                    "document",
                    f"{len(gg)} docs inventoried, {len(ft)} with full text",
                )
            )
    out.append(
        row(
            "jp_diet",
            "historical E attention (JPN->KOR)",
            "n/a",
            1980,
            2010,
            "speech counts",
            "feasibility counts only",
        )
    )
    out.append(
        row(
            "youtube",
            "public attention / recognition",
            0,
            None,
            None,
            "comment",
            "not collected: API key required (task Y1)",
        )
    )
    return pd.DataFrame(out)


if __name__ == "__main__":
    run_step("quality_checks", main, argparse.ArgumentParser(description=__doc__))
