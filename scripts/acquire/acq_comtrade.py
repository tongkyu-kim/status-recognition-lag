"""Acquire UN Comtrade annual goods trade via the keyless public *preview* API.

Preview limits (observed 2026-09-30): one period per call, max 500 records per call, a few
requests per second at most (HTTP 429 otherwise), and a call-volume quota per time window
(~190 calls in 7 minutes exhausted it; HTTP 403 'Out of call volume quota' with Retry-After ~30 min).
Default spacing is therefore 10 s. A result with exactly 500 records is treated as
truncated and logged. The full API (up to 250k records/call) needs a free subscription key - see
docs/manual_data_tasks.md.

Queries (HS as reported, customs code C00, all modes of transport, no second partner):
  totals/  reporters = panel (13), partners = panel + World(0), flows X/M, cmdCode TOTAL
  hs2/     reporters = {KOR, p}, partners = {KOR, p}, flows X/M, cmdCode AG2 (Korea-reported and
           partner-reported/mirror flows for each Korea-partner dyad)
"""

import argparse
import time

import _bootstrap  # noqa: F401

from srl.acquisition.fetch import PoliteSession, log_download, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "un_comtrade"
API = "https://comtradeapi.un.org/public/v1/preview/C/A/HS"
# Comtrade reporter/partner codes (M49-based; verified against the reference list saved in meta/).
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
COMMON = "&motCode=0&partner2Code=0&customsCode=C00&includeDesc=true"
MAX_RECORDS = 500


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=args.interval, max_retries=6)
    for name, url in {
        "meta/reporters.json": "https://comtradeapi.un.org/files/v1/app/reference/Reporters.json",
        "meta/partners.json": "https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json",
    }.items():
        if not raw_exists(SOURCE_ID, name):
            r = sess.get(url)
            if r.status_code == 200:
                save_raw(SOURCE_ID, name, r.content, url=url, http_status=200)

    truncated, failed = [], []

    def fetch(name: str, query: str) -> None:
        if raw_exists(SOURCE_ID, name):
            return
        url = f"{API}?{query}{COMMON}"
        r = sess.get(url)
        for _ in range(3):  # quota window exhausted: wait as instructed by Retry-After, then retry
            if r.status_code != 403 or "quota" not in r.text.lower():
                break
            wait = int(r.headers.get("Retry-After", 1800)) + 30
            logger.warning("Comtrade call-volume quota exhausted; sleeping %ds (Retry-After)", wait)
            time.sleep(wait)
            r = sess.get(url)
        try:
            body = r.json()
        except ValueError:
            body = None
        if r.status_code != 200 or not isinstance(body, dict) or body.get("error") or "data" not in body:
            msg = (body or {}).get("error") if isinstance(body, dict) else r.text[:200]
            logger.error("%s: HTTP %s %s", name, r.status_code, msg)
            log_download(SOURCE_ID, url, http_status=r.status_code, outcome="failed", notes=str(msg)[:300])
            failed.append(name)
            return
        n = len(body["data"])
        note = f"{n} records" + ("; TRUNCATED at preview cap" if n >= MAX_RECORDS else "")
        if n >= MAX_RECORDS:
            truncated.append(name)
        save_raw(SOURCE_ID, name, r.content, url=url, http_status=200, notes=note)
        logger.info("%s: %s", name, note)

    codes = ",".join(str(c) for c in PANEL.values())
    for year in range(args.start, args.end + 1):
        fetch(
            f"totals/totals_{year}.json",
            f"reporterCode={codes}&partnerCode={codes},0&period={year}&cmdCode=TOTAL&flowCode=X,M",
        )
    if not args.totals_only:
        for iso3, code in PANEL.items():
            if iso3 == "KOR":
                continue
            for year in range(args.start, args.end + 1):
                fetch(
                    f"hs2/hs2_KOR_{iso3}_{year}.json",
                    f"reporterCode=410,{code}&partnerCode=410,{code}&period={year}&cmdCode=AG2&flowCode=X,M",
                )

    write_folder_readme(
        SOURCE_ID,
        f"""
# UN Comtrade - public preview API retrieval

- Endpoint: {API}?<query>{COMMON}
- Years requested: {args.start}-{args.end}. Classification: HS as reported (H0..H6 varies by
  reporter-year; see `classificationCode` in each record).
- `totals/totals_<year>.json`: reporters = 13 panel countries; partners = panel + World (0);
  flows X (exports) / M (imports); cmdCode TOTAL. Gives reporter- AND partner-reported (mirror)
  bilateral totals and each reporter's world totals.
- `hs2/hs2_KOR_<ISO3>_<year>.json`: HS 2-digit chapters, both Korea-reported and partner-reported
  flows of each Korea-partner dyad.
- `meta/`: Comtrade reporter / partner reference lists.
- Values: `primaryValue` in current US$ (exports FOB, imports CIF by convention).
- Truncated responses at the 500-record preview cap: {truncated or "none in this run"}
- Failed queries in this run: {failed or "none"}
- Licence/terms: UN Comtrade terms of use (https://comtradeplus.un.org/); data may be used with
  attribution; bulk redistribution of raw extracts is restricted - share derived data only.
- Script: scripts/acquire/acq_comtrade.py
""",
    )
    if truncated:
        logger.warning("Truncated: %s", truncated)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=int, default=1988)
    p.add_argument("--end", type=int, default=2025)
    p.add_argument("--interval", type=float, default=10.0)
    p.add_argument("--totals-only", action="store_true")
    run_step("acq_comtrade", main, p)
