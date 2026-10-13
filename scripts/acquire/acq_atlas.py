"""Acquire Atlas of Economic Complexity data via its public GraphQL API.

API docs: https://github.com/harvard-growth-lab/api-docs/blob/main/atlas.md (public, no
authentication; documented limit 120 requests/min - we use <= 60/min). Raw output is the unmodified
JSON response of each query; the query text is stored alongside in queries.jsonl.

Pulled (HS92 unless noted):
- classifications: locationCountry, productHs92 (levels 2/4/6), productSitc (level 4), dataAvailability
- countryYear (all countries; ECI, COI, GDP) for HS92 and SITC
- productYear level 4 (PCI) for HS92 and SITC
- countryProductYear level 4 for the panel + JPN/USA (HS92 1995+, SITC 1962+)
- countryCountryYear and countryCountryProductYear level 4 (folder ccpy/): Korea x each partner (HS92)
"""

import argparse
import json

import _bootstrap  # noqa: F401

from srl.acquisition.fetch import PoliteSession, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "complexity_atlas"
API = "https://atlas.hks.harvard.edu/api/graphql"
# Atlas country ids follow UN M49 numeric codes.
PANEL = {
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
}
EXTRA = {"JPN": 392, "USA": 840}
CPY_FIELDS = "countryId productId productLevel year exportValue importValue globalMarketShare exportRca"


def year_chunks(lo: int, hi: int, step: int):
    for start in range(lo, hi + 1, step):
        yield start, min(start + step - 1, hi)


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=1.0, headers={"Content-Type": "application/json"})
    log_lines = []

    def run(name: str, query: str) -> dict | None:
        if raw_exists(SOURCE_ID, name):
            return json.loads((_raw_path(name)).read_text(encoding="utf-8"))
        resp = sess.post(API, json={"query": query})
        body = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else None
        if resp.status_code != 200 or body is None or body.get("errors"):
            logger.error("%s: HTTP %s %s", name, resp.status_code, (resp.text or "")[:300])
            return None
        save_raw(SOURCE_ID, name, resp.content, url=API, http_status=200, notes=name)
        log_lines.append(json.dumps({"file": name, "query": query}, ensure_ascii=False))
        rows = next(iter(body["data"].values()))
        logger.info("%s: %s rows", name, len(rows) if isinstance(rows, list) else "obj")
        return body

    from srl.acquisition.fetch import raw_dir

    _raw_path = lambda name: raw_dir(SOURCE_ID) / name  # noqa: E731

    avail = run(
        "meta/dataAvailability.json", "{ dataAvailability { productClassification yearMin yearMax } }"
    )
    yr = {d["productClassification"]: (d["yearMin"], d["yearMax"]) for d in avail["data"]["dataAvailability"]}
    logger.info("Data availability: %s", yr)
    hs_lo, hs_hi = yr.get("HS92", (1995, 2023))
    si_lo, si_hi = yr.get("SITC", (1962, 2023))

    run(
        "meta/locationCountry.json",
        "{ locationCountry { countryId iso3Code iso2Code nameEn nameShortEn incomelevelEnum "
        "isTrusted inRankings reportedServ reportedServRecent } }",
    )
    for lvl in (2, 4, 6):
        run(
            f"meta/productHs92_level{lvl}.json",
            f"{{ productHs92(productLevel: {lvl}) {{ productId code nameEn nameShortEn productLevel "
            f"parent {{ productId }} topParent {{ productId }} naturalResource greenProduct "
            f"showFeasibility }} }}",
        )
    run(
        "meta/productSitc_level4.json",
        "{ productSitc(productLevel: 4) { productId code nameEn productLevel } }",
    )
    run("meta/metadata.json", "{ metadata { serverName ingestionCommit ingestionDate apiCommit } }")

    for cls, (lo, hi) in (("HS92", (hs_lo, hs_hi)), ("SITC", (si_lo, si_hi))):
        run(
            f"countryYear_{cls}.json",
            f"{{ countryYear(productClass: {cls}, yearMin: {lo}, yearMax: {hi}) {{ countryId year "
            f"exportValue importValue population gdp gdppc gdppcPpp gdppcConst eci eciFixed coi }} }}",
        )
        run(
            f"productYear_{cls}_level4.json",
            f"{{ productYear(productClass: {cls}, productLevel: 4, yearMin: {lo}, yearMax: {hi}) "
            f"{{ productId productLevel year exportValue pci complexityEnum }} }}",
        )
        for iso3, cid in {**PANEL, **EXTRA}.items():
            for a, b in year_chunks(lo, hi, 10):
                run(
                    f"countryProductYear/{cls}_L4_{iso3}_{a}_{b}.json",
                    f"{{ countryProductYear(countryId: {cid}, productClass: {cls}, productLevel: 4, "
                    f"yearMin: {a}, yearMax: {b}) {{ {CPY_FIELDS} }} }}",
                )

    for iso3, cid in PANEL.items():
        if iso3 == "KOR":
            continue
        run(
            f"countryCountryYear/HS92_KOR_{iso3}.json",
            f"{{ countryCountryYear(countryId: 410, partnerCountryId: {cid}, productClass: HS92, "
            f"yearMin: {hs_lo}, yearMax: {hs_hi}) {{ countryId partnerCountryId year exportValue "
            f"importValue }} }}",
        )
        for a, b in year_chunks(hs_lo, hs_hi, 10):
            run(
                f"ccpy/L4_KOR_{iso3}_{a}.json",  # short name: Windows MAX_PATH
                f"{{ countryCountryProductYear(countryId: 410, partnerCountryId: {cid}, "
                f"productClass: HS92, productLevel: 4, yearMin: {a}, yearMax: {b}) {{ countryId "
                f"partnerCountryId productId productLevel year exportValue importValue }} }}",
            )

    if log_lines:
        qpath = raw_dir(SOURCE_ID) / "queries.jsonl"
        with qpath.open("a", encoding="utf-8") as fh:
            fh.write("\n".join(log_lines) + "\n")
    write_folder_readme(
        SOURCE_ID,
        f"""
# Atlas of Economic Complexity (Growth Lab, Harvard) - GraphQL API retrieval

- Endpoint: {API} (public, no authentication; documented limit 120 req/min).
- Data availability at retrieval: {yr}
- Each `.json` file is the unmodified API response; `queries.jsonl` records the exact query per file.
- Country ids are UN M49 numeric codes; product ids are Atlas-internal
  (map via `meta/productHs92_level*.json`).
- Values are in current US$. Atlas trade data are Comtrade-based and reconciled by the Growth Lab
  (mirror-adjusted); they are NOT identical to reporter-declared customs data.
- Citation: Growth Lab at Harvard University, "The Atlas of Economic Complexity", https://atlas.hks.harvard.edu
- Bulk files (Harvard Dataverse doi:10.7910/DVN/T4CHWJ, CC0) sit behind a guestbook form and are
  listed as a manual task in docs/manual_data_tasks.md.
- Script: scripts/acquire/acq_atlas.py
""",
    )


if __name__ == "__main__":
    run_step("acq_atlas", main, argparse.ArgumentParser(description=__doc__))
