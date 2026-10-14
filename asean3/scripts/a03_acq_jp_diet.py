"""Japanese National Diet: speeches mentioning an ASEAN+3 target together with industry terms.

Observer = Japan (Diet members and government respondents; speaker attribution from the API).
API: https://kokkai.ndl.go.jp/api/speech (NDL, public, documented, no key). `any=` is a substring
AND search over speech text. Up to 100 records per call; pagination via nextRecordPosition.

Retrieval frame (fixed before looking at content):
  target alias  x  {産業 industry, 競争 competition, 技術 technology, 追い上げ catch-up, 追い抜 overtake}
  for each calendar year 2000-2024. Thailand's katakana name タイ is a substring of many words
  (ネクタイ, タイミング ...), so it is queried through particle-bound forms (タイの/タイは/タイに/タイと/日タイ)
  and filtered again downstream. 中国 also matches 中国地方 (Japanese region); filtered downstream.
Attention denominators: count-only queries (maximumRecords=1) for each alias-year.

Raw: data/raw/jp_diet/<date>/sp/<ISO>/<year>/<term>_<form>_<start>.json, cnt/<ISO>_<form>_<year>.json
"""

from __future__ import annotations

import argparse
import json
import logging
from urllib.parse import quote

import _common as C  # noqa: F401
from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw, write_folder_readme

SOURCE_ID = "jp_diet"
API = "https://kokkai.ndl.go.jp/api/speech"
ALIASES = {
    "KOR": ["韓国"], "CHN": ["中国"], "VNM": ["ベトナム"], "IDN": ["インドネシア"], "MYS": ["マレーシア"],
    "PHL": ["フィリピン"], "SGP": ["シンガポール"], "MMR": ["ミャンマー"], "KHM": ["カンボジア"],
    "LAO": ["ラオス"], "BRN": ["ブルネイ"], "TLS": ["東ティモール"],
    "THA": ["タイの", "タイは", "タイに", "タイと", "日タイ"],
}
TERMS = {"ind": "産業", "cmp": "競争", "tec": "技術", "cu": "追い上げ", "ov": "追い抜"}

log = logging.getLogger("a03")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2000)
    ap.add_argument("--end", type=int, default=2024)
    ap.add_argument("--targets", default=",".join(ALIASES))
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    sess = PoliteSession(SOURCE_ID, min_interval=1.2)

    def get(rel: str, q: str, year: int, start: int, maxrec: int) -> dict | None:
        if raw_exists(SOURCE_ID, rel):
            return json.loads((raw_dir(SOURCE_ID) / rel).read_text(encoding="utf-8"))
        url = (f"{API}?any={quote(q)}&from={year}-01-01&until={year}-12-31&startRecord={start}"
               f"&maximumRecords={maxrec}&recordPacking=json")
        r = sess.get(url)
        if r.status_code != 200:
            log.error("%s HTTP %s", rel, r.status_code)
            return None
        save_raw(SOURCE_ID, rel, r.content, url=url, http_status=200, log=False)
        return json.loads(r.content)

    for iso in args.targets.split(","):
        for fi, alias in enumerate(ALIASES[iso]):
            for year in range(args.start, args.end + 1):
                get(f"cnt/{iso}_{fi}_{year}.json", alias, year, 1, 1)
                for tk, term in TERMS.items():
                    start, total = 1, None
                    while True:
                        d = get(f"sp/{iso}/{year}/{tk}_{fi}_{start:05d}.json", f"{alias} {term}", year, start, 100)
                        if d is None:
                            break
                        total = int(d.get("numberOfRecords") or 0)
                        nxt = d.get("nextRecordPosition")
                        if not nxt or total == 0:
                            break
                        start = int(nxt)
                    log.info("%s %s %s %s: %s", iso, alias, year, term, total)
    write_folder_readme(SOURCE_ID, f"""
# Japan National Diet Record API - ASEAN+3 x industry-term speeches (asean3 study)

- API: {API} (public; https://kokkai.ndl.go.jp/api.html). Rate: 1 request / 1.2 s.
- Frame: alias x term x calendar year {args.start}-{args.end}; aliases {ALIASES}; terms {TERMS}.
- sp/<ISO>/<year>/<term>_<aliasIndex>_<startRecord>.json: full speech records (speaker, party,
  house, committee, date, speech text, URLs). cnt/: count-only alias queries (attention).
- Substring search: タイ and 中国 produce false matches; filtering is done in asean3/scripts/b01.
- Script: asean3/scripts/a03_acq_jp_diet.py
""")


if __name__ == "__main__":
    main()
