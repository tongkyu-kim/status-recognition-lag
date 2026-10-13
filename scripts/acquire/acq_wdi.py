"""Acquire World Bank WDI series for the main panel (+ JPN/USA for historical extensions).

Raw output: one JSON file per indicator (API response pages concatenated as a JSON list), plus
indicator metadata and the WDI source record (for the database's last-updated date).
"""

import argparse
import json

import _bootstrap  # noqa: F401

from srl.acquisition.fetch import PoliteSession, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "wb_wdi"
API = "https://api.worldbank.org/v2"
COUNTRIES = [
    "KOR",
    "BRN",
    "KHM",
    "IDN",
    "LAO",
    "MYS",
    "MMR",
    "PHL",
    "SGP",
    "THA",
    "TLS",
    "VNM",
    "CHN",
    "HKG",
    "MAC",
    "JPN",
    "USA",
    "WLD",
]
INDICATORS = {
    "NY.GDP.MKTP.CD": "GDP (current US$)",
    "NY.GDP.MKTP.KD": "GDP (constant 2015 US$)",
    "NY.GDP.MKTP.KD.ZG": "GDP growth (annual %)",
    "NY.GDP.PCAP.CD": "GDP per capita (current US$)",
    "NY.GDP.PCAP.KD": "GDP per capita (constant 2015 US$)",
    "NY.GDP.PCAP.PP.CD": "GDP per capita, PPP (current international $)",
    "NY.GDP.PCAP.PP.KD": "GDP per capita, PPP (constant international $)",
    "NY.GNP.PCAP.CD": "GNI per capita, Atlas method (current US$)",
    "SP.POP.TOTL": "Population, total",
    "SL.GDP.PCAP.EM.KD": "GDP per person employed (constant PPP $)",
    "NV.IND.MANF.CD": "Manufacturing, value added (current US$)",
    "NV.IND.MANF.KD": "Manufacturing, value added (constant 2015 US$)",
    "NV.IND.MANF.ZS": "Manufacturing, value added (% of GDP)",
    "NV.IND.TOTL.ZS": "Industry (incl. construction), value added (% of GDP)",
    "TX.VAL.TECH.CD": "High-technology exports (current US$)",
    "TX.VAL.TECH.MF.ZS": "High-technology exports (% of manufactured exports)",
    "TX.VAL.MANF.ZS.UN": "Manufactures exports (% of merchandise exports)",
    "TX.VAL.MRCH.CD.WT": "Merchandise exports (current US$)",
    "TM.VAL.MRCH.CD.WT": "Merchandise imports (current US$)",
    "NE.EXP.GNFS.CD": "Exports of goods and services (current US$)",
    "NE.TRD.GNFS.ZS": "Trade (% of GDP)",
    "BX.KLT.DINV.CD.WD": "Foreign direct investment, net inflows (BoP, current US$)",
    "BX.KLT.DINV.WD.GD.ZS": "Foreign direct investment, net inflows (% of GDP)",
    "BM.KLT.DINV.CD.WD": "Foreign direct investment, net outflows (BoP, current US$)",
    "BM.KLT.DINV.WD.GD.ZS": "Foreign direct investment, net outflows (% of GDP)",
    "IP.PAT.RESD": "Patent applications, residents",
    "IP.PAT.NRES": "Patent applications, nonresidents",
    "GB.XPD.RSDV.GD.ZS": "Research and development expenditure (% of GDP)",
    "SP.POP.SCIE.RD.P6": "Researchers in R&D (per million people)",
}


def fetch_indicator(sess: PoliteSession, code: str) -> tuple[list, str]:
    pages, page, url = [], 1, ""
    while True:
        url = (
            f"{API}/country/{';'.join(COUNTRIES)}/indicator/{code}"
            f"?format=json&per_page=20000&date=1960:2026&page={page}"
        )
        resp = sess.get(url)
        resp.raise_for_status()
        body = resp.json()
        pages.append(body)
        if not isinstance(body, list) or len(body) < 2 or body[0].get("pages", 1) <= page:
            return pages, url
        page += 1


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=0.5)
    src = sess.get(f"{API}/sources/2?format=json")
    save_raw(SOURCE_ID, "wdi_source_record.json", src.content, url=src.url, http_status=src.status_code)
    for code, label in INDICATORS.items():
        pages, url = fetch_indicator(sess, code)
        meta = pages[0][0] if isinstance(pages[0], list) else pages[0]
        if isinstance(meta, dict) and "message" in meta:
            logger.error("%s: API error %s", code, meta["message"])
            continue
        save_raw(
            SOURCE_ID,
            f"indicator_{code}.json",
            json.dumps(pages, ensure_ascii=False),
            url=url,
            http_status=200,
            notes=label,
        )
        m = sess.get(f"{API}/indicator/{code}?format=json")
        save_raw(
            SOURCE_ID, f"meta/indicator_{code}_meta.json", m.content, url=m.url, http_status=m.status_code
        )
        n = sum(len(p[1] or []) for p in pages if isinstance(p, list) and len(p) > 1)
        logger.info("%s (%s): %d observations", code, label, n)
    write_folder_readme(
        SOURCE_ID,
        f"""
# World Bank World Development Indicators - API retrieval

- Endpoint: {API}/country/<ISO3 list>/indicator/<code>?format=json&per_page=20000&date=1960:2026
- Countries: {", ".join(COUNTRIES)}
- Indicators: {len(INDICATORS)} (see `indicator_*.json`; metadata incl. source notes in `meta/`)
- Database vintage: see `wdi_source_record.json` (`lastupdated`).
- Licence: CC BY 4.0 (World Bank Open Data terms of use).
- Files are the unmodified API responses (list of pages, each `[paging_meta, observations]`).
- Script: scripts/acquire/acq_wdi.py
""",
    )


if __name__ == "__main__":
    run_step("acq_wdi", main, argparse.ArgumentParser(description=__doc__))
