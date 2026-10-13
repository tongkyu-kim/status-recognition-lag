"""Japan -> Korea elite-discourse corpus: full-text Diet speeches.

Extends acq_jp_diet_counts.py (which only fetched yearly counts) per its own stated next step:
"Full speech texts ... are available from the same API ... when the Japan -> Korea extension is
taken up." National Diet Library Diet Record API (https://kokkai.ndl.go.jp/api.html); public,
documented, no key.

Scoped to the korea_catchup (101 speeches) and korea_competition (1,541) queries -- these target
economic-competition/catch-up framing directly, unlike the generic "korea" query (32,521 speeches,
mostly unrelated to industrial status). korea_economy (6,603) is included as a broader-but-still-
tractable third query. The bare "korea" query is deliberately NOT pulled in full text in this pass
(see docs/decision_log.md R006) -- it would require ~325 API calls at maximumRecords=100 and is
dominated by speeches with no status-relevant content.

Added 2026-10-14 (overnight execution). No prior H1-H5 treatment of this source existed.
"""

import argparse
import json

import _bootstrap  # noqa: F401

from srl.acquisition.fetch import PoliteSession, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "jp_diet"
API = "https://kokkai.ndl.go.jp/api/speech"
QUERIES = {
    "korea_catchup": "韓国 追い上げ",
    "korea_competition": "韓国 競争",
    "korea_economy": "韓国 経済",
}
PAGE_SIZE = 100


def fetch_query_year(sess: PoliteSession, logger, key: str, q: str, year: int) -> int:
    from urllib.parse import quote

    start = 1
    total_saved = 0
    while True:
        rel = f"fulltext/{key}_{year}_{start}.json"
        if raw_exists(SOURCE_ID, rel):
            start += PAGE_SIZE
            continue
        url = (
            f"{API}?any={quote(q)}&from={year}-01-01&until={year}-12-31"
            f"&startRecord={start}&maximumRecords={PAGE_SIZE}&recordPacking=json"
        )
        r = sess.get(url)
        if r.status_code != 200:
            logger.warning("%s %d start=%d: HTTP %d", key, year, start, r.status_code)
            break
        payload = json.loads(r.content)
        n_total = payload.get("numberOfRecords", 0)
        n_this = len(payload.get("speechRecord") or [])
        save_raw(SOURCE_ID, rel, r.content, url=url, http_status=200)
        total_saved += n_this
        logger.info("%s %d start=%d: saved %d (of %d total)", key, year, start, n_this, n_total)
        nxt = payload.get("nextRecordPosition")
        if not nxt or n_this == 0:
            break
        start = nxt
    return total_saved


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=2.0)
    grand_total = 0
    for year in range(args.start, args.end + 1):
        for key, q in QUERIES.items():
            n = fetch_query_year(sess, logger, key, q, year)
            grand_total += n
    logger.info("TOTAL speeches saved this run: %d", grand_total)
    write_folder_readme(
        SOURCE_ID,
        f"""
# Japan National Diet Record API - full-text speeches (Japan -> Korea elite discourse)

- API: {API} (NDL; public, documented at https://kokkai.ndl.go.jp/api.html).
- Queries (deliberately scoped, see script docstring): {list(QUERIES)}; years
  {args.start}-{args.end}; paginated at {PAGE_SIZE} records/call under `fulltext/`.
- Fields retained per speech: speechID, issueID, nameOfHouse, nameOfMeeting, issue, date, speaker,
  speakerGroup, speech (full text). Source: NDL Diet Record API JSON response, unmodified.
- The bare "korea" query (32,521 speeches total, 1980-2010 per the existing counts/ data) was NOT
  pulled in full text in this pass -- see docs/decision_log.md R006.
Script: scripts/acquire/acq_jp_diet_fulltext.py
""",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=int, default=1980)
    p.add_argument("--end", type=int, default=2024)
    run_step("acq_jp_diet_fulltext", main, p)
