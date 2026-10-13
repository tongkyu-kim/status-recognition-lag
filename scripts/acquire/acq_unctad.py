"""Acquire UNCTADstat bulk files (public bulk-download endpoint used by the UNCTADstat Data Centre).

- US.FdiFlowsStock: FDI inward/outward flows and stocks by economy, annual (US$ at current prices).
unctad.org (main site) blocks automated clients (HTTP 403); the 2014 bilateral FDI statistics
tables are therefore a manual task (docs/manual_data_tasks.md).
"""

import argparse

import _bootstrap  # noqa: F401

from srl.acquisition.fetch import PoliteSession, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "unctad"
BULK = "https://unctadstat-api.unctad.org/bulkdownload/{0}/{1}"
DATASETS = {"US.FdiFlowsStock": "US_FdiFlowsStock"}


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=3)
    for ds, fname in DATASETS.items():
        url = BULK.format(ds, fname)
        r = sess.get(url, timeout=300)
        if r.status_code != 200:
            logger.error("%s: HTTP %s", ds, r.status_code)
            continue
        cd = r.headers.get("Content-Disposition", "")
        name = cd.split("filename=")[-1].strip('"; ') if "filename=" in cd else f"{fname}.7z"
        save_raw(SOURCE_ID, name, r.content, url=url, http_status=200, notes=ds)
        logger.info("%s -> %s (%d bytes, magic %r)", ds, name, len(r.content), r.content[:4])
    write_folder_readme(
        SOURCE_ID,
        f"""
# UNCTADstat bulk downloads

- Endpoint: {BULK.format("<dataset>", "<file>")} (public; same endpoint as the Data Centre's
  "bulk download" button at https://unctadstat.unctad.org/datacentre/)
- Datasets: {", ".join(DATASETS)}
- Licence: UNCTADstat terms of use (free use with attribution). Script: scripts/acquire/acq_unctad.py
""",
    )


if __name__ == "__main__":
    run_step("acq_unctad", main, argparse.ArgumentParser(description=__doc__))
