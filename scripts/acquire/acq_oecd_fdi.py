"""Acquire OECD FDI statistics by counterpart area (SDMX REST API, public, no key).

Reporters: KOR (main), JPN and USA (historical extensions). Counterparts: China + ASEAN members.
All other dimensions are wildcarded so that every published measure (flows/positions/income,
directional vs. asset-liability principle, inward/outward, resident SPE inclusion) is kept raw.
The OECD asks for moderate query rates, so only a handful of queries are sent.
"""

import argparse

import _bootstrap  # noqa: F401

from srl.acquisition.fetch import PoliteSession, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "oecd_fdi"
API = "https://sdmx.oecd.org/public/rest/data"
REPORTERS = ["KOR", "JPN", "USA"]
PARTNERS = [
    "CHN",
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
    "HKG",
    "KOR",
    "JPN",
    "W",
]
FLOWS = {
    "FDI_FLOW_CTRY": "OECD.DAF.INV,DSD_FDI@DF_FDI_FLOW_CTRY,1.0",
    "FDI_POS_CTRY": "OECD.DAF.INV,DSD_FDI@DF_FDI_POS_CTRY,1.0",
    "FDI_INC_CTRY": "OECD.DAF.INV,DSD_FDI@DF_FDI_INC_CTRY,1.0",
    "FDI_CTRY_IND_HIST": "OECD.DAF.INV,DSD_FDI@DF_FDI_CTRY_IND_HIST,1.0",
}


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=15, max_retries=4)
    # 13 dimensions: REF_AREA . MEASURE . UNIT . PRINCIPLE . ENTRY . TYPE_ENTITY . FDI_COMP .
    #                SECTOR . COUNTERPART_AREA . LEVEL_COUNTERPART . ACTIVITY . FREQ . COLLECTION
    key = ".".join(["+".join(REPORTERS), "", "", "", "", "", "", "", "+".join(PARTNERS), "", "", "A", ""])
    for name, flow in FLOWS.items():
        rel = f"{name}.csv"
        if raw_exists(SOURCE_ID, rel):
            continue
        url = f"{API}/{flow}/{key}?dimensionAtObservation=AllDimensions&format=csvfilewithlabels"
        r = sess.get(url, timeout=300)
        if r.status_code != 200:
            logger.error("%s: HTTP %s %s", name, r.status_code, r.text[:300])
            continue
        save_raw(SOURCE_ID, rel, r.content, url=url, http_status=200)
        logger.info("%s: %d bytes, %d lines", name, len(r.content), r.content.count(b"\n"))
    write_folder_readme(
        SOURCE_ID,
        f"""
# OECD FDI statistics by counterpart area (BMD4; historical BMD3)

- API: {API}/<dataflow>/<key>?format=csvfilewithlabels (OECD Data Explorer SDMX API; public)
- Key: reporters {REPORTERS}; counterparts {PARTNERS}; annual; all other dimensions wildcarded.
- Dataflows: {", ".join(f"{k} = {v}" for k, v in FLOWS.items())}
- Units/measures are in the file (UNIT_MEASURE, MEASURE, MEASURE_PRINCIPLE, ACCOUNTING_ENTRY);
  confidential cells are suppressed by reporters (appear missing / flagged in OBS_STATUS).
- Licence: OECD terms (CC BY 4.0 for most OECD data since 2024). Script: scripts/acquire/acq_oecd_fdi.py
""",
    )


if __name__ == "__main__":
    run_step("acq_oecd_fdi", main, argparse.ArgumentParser(description=__doc__))
