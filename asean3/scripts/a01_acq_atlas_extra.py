"""Atlas of Economic Complexity: extra pulls for the ASEAN+3 study.

Same public GraphQL endpoint and rules as scripts/acquire/acq_atlas.py (<= 1 request/s, write-once
raw files, one query per file recorded in queries.jsonl). Pulls:

1. countryProductYear HS92 level 4 for every country in the Atlas classification (needed for the
   all-country RCA weights of PRODY; the parent pull covered only the panel + JPN/USA).
2. countryCountryYear HS92 for every ASEAN+3 pair not already pulled (bilateral trade for
   dependence measures; the parent pull covered KOR x partner only).

Usage: python asean3/scripts/a01_acq_atlas_extra.py [--only pairs|cpy]
"""

from __future__ import annotations

import argparse
import itertools
import json
import logging

import _common as C  # noqa: F401  (sets sys.path)
from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw, write_folder_readme

SOURCE_ID = "complexity_atlas"
API = "https://atlas.hks.harvard.edu/api/graphql"
PARENT_DIR = C.RAW / SOURCE_ID / "2026-09-30"
CPY_FIELDS = "countryId productId productLevel year exportValue importValue globalMarketShare exportRca"
HS_LO, HS_HI = 1995, 2024

log = logging.getLogger("a01")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=["pairs", "cpy"], default=None)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    sess = PoliteSession(SOURCE_ID, min_interval=1.0, headers={"Content-Type": "application/json"})
    qlog = []

    def run(name: str, query: str) -> None:
        if raw_exists(SOURCE_ID, name) or (PARENT_DIR / name).exists():
            return
        resp = sess.post(API, json={"query": query})
        try:
            body = resp.json()
        except ValueError:
            body = None
        if resp.status_code != 200 or body is None or body.get("errors"):
            log.error("%s: HTTP %s %s", name, resp.status_code, (resp.text or "")[:200])
            return
        save_raw(SOURCE_ID, name, resp.content, url=API, http_status=200, notes=name)
        qlog.append(json.dumps({"file": name, "query": query}))
        rows = next(iter(body["data"].values()))
        log.info("%s: %s rows", name, len(rows) if isinstance(rows, list) else "obj")

    if args.only in (None, "pairs"):
        for a, b in itertools.combinations(sorted(C.M49), 2):
            if "KOR" in (a, b):
                other = b if a == "KOR" else a
                if (PARENT_DIR / f"countryCountryYear/HS92_KOR_{other}.json").exists():
                    continue
            run(
                f"countryCountryYear/HS92_{a}_{b}.json",
                f"{{ countryCountryYear(countryId: {C.M49[a]}, partnerCountryId: {C.M49[b]}, "
                f"productClass: HS92, yearMin: {HS_LO}, yearMax: {HS_HI}) {{ countryId "
                f"partnerCountryId year exportValue importValue }} }}",
            )

    if args.only in (None, "cpy"):
        meta = json.loads((PARENT_DIR / "meta/locationCountry.json").read_text(encoding="utf-8"))
        for c in meta["data"]["locationCountry"]:
            iso, cid = c["iso3Code"], int(c["countryId"].split("-")[1])
            if (PARENT_DIR / f"countryProductYear/HS92_L4_{iso}_1995_2004.json").exists():
                continue
            for a, b in ((1995, 2004), (2005, 2014), (2015, 2024)):
                run(
                    f"countryProductYear/HS92_L4_{iso}_{a}_{b}.json",
                    f"{{ countryProductYear(countryId: {cid}, productClass: HS92, productLevel: 4, "
                    f"yearMin: {a}, yearMax: {b}) {{ {CPY_FIELDS} }} }}",
                )

    if qlog:
        with (raw_dir(SOURCE_ID) / "queries.jsonl").open("a", encoding="utf-8") as fh:
            fh.write("\n".join(qlog) + "\n")
    write_folder_readme(
        SOURCE_ID,
        f"""
# Atlas of Economic Complexity - supplementary retrieval for the ASEAN+3 study

- Endpoint: {API} (public GraphQL, no authentication). Script: asean3/scripts/a01_acq_atlas_extra.py
- Complements data/raw/complexity_atlas/2026-09-30 (same endpoint, same field lists).
- countryProductYear/: HS92 4-digit exports for all Atlas countries (PRODY weights).
- countryCountryYear/: bilateral totals for ASEAN+3 pairs (first-named country = countryId).
- Each file is the unmodified API response; queries.jsonl records each query.
""",
    )


if __name__ == "__main__":
    main()
