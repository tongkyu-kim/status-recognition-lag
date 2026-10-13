"""Historical feasibility (Japan -> Korea): yearly counts of Diet speeches mentioning Korea.

Uses the National Diet Library's documented Diet Record API (https://kokkai.ndl.go.jp/api.html;
public, no key). Only counts are requested (maximumRecords=1); `numberOfRecords` of each JSON
response is the count of matching speeches. Queries: 韓国; 韓国+経済; 韓国+追い上げ (catch-up);
韓国+競争 (competition). The full-text collection is deferred until the extension is in scope.
"""

import argparse
import json
from urllib.parse import quote

import _bootstrap  # noqa: F401

from srl.acquisition.fetch import PoliteSession, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "jp_diet"
API = "https://kokkai.ndl.go.jp/api/speech"
QUERIES = {
    "korea": "韓国",
    "korea_economy": "韓国 経済",
    "korea_catchup": "韓国 追い上げ",
    "korea_competition": "韓国 競争",
}


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=2.0)
    for year in range(args.start, args.end + 1):
        for key, q in QUERIES.items():
            rel = f"counts/{key}_{year}.json"
            if raw_exists(SOURCE_ID, rel):
                continue
            url = (
                f"{API}?any={quote(q)}&from={year}-01-01&until={year}-12-31"
                f"&maximumRecords=1&recordPacking=json"
            )
            r = sess.get(url)
            if r.status_code == 200:
                save_raw(SOURCE_ID, rel, r.content, url=url, http_status=200)
                n = json.loads(r.content).get("numberOfRecords")
                logger.info("%s %d: %s", key, year, n)
    write_folder_readme(
        SOURCE_ID,
        f"""
# Japan National Diet Record API - feasibility counts

- API: {API} (NDL; public, documented at https://kokkai.ndl.go.jp/api.html). `any=` is a
  full-text AND search over speech text; `numberOfRecords` = number of matching speeches.
- Queries: {QUERIES}; years {args.start}-{args.end}; one JSON per query-year in `counts/`.
- Full speech texts (speaker, party, committee, date) are available from the same API
  (maximumRecords <= 100 per call) when the Japan -> Korea extension is taken up.
Script: scripts/acquire/acq_jp_diet_counts.py
""",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=int, default=1980)
    p.add_argument("--end", type=int, default=2010)
    run_step("acq_jp_diet_counts", main, p)
