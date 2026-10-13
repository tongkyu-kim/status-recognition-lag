"""Acquire trade/industry ministry press releases from www.motir.go.kr (산업통상부; formerly
산업통상자원부 MOTIE, www.motie.go.kr now redirects here). robots.txt allows all but /kor/search.

Phases: lists (full inventory) -> search (content search per country alias) -> views (hits)
-> legacy (all releases carrying the 2016-12-09 migration date; full text + original date in body).
The on-site archive starts in 2014; predecessor ministries (지식경제부 MKE 2008-13, 산업자원부
MOCIE 1998-2008) are NOT on this site - see docs/manual_data_tasks.md and the korea.kr source.
"""

import argparse
import re

import _bootstrap  # noqa: F401
from bs4 import BeautifulSoup

from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "kr_motie"
SITE = "https://www.motir.go.kr"
BOARDS = {
    "ATCL3f49a5a8c": ("보도자료 (press releases)", "press_release"),
    "ATCLe0854704d": ("보도설명자료 (explanatory releases)", "press_release"),
}
ROWS = 100
LEGACY_DATE = "2016-12-09"  # migration date of imported pre-2014 releases
TERMS = {
    "CHN": ["중국", "한·중", "한중"],
    "VNM": ["베트남", "한·베"],
    "IDN": ["인도네시아", "인니"],
    "MYS": ["말레이시아"],
    "THA": ["태국"],
    "PHL": ["필리핀"],
    "SGP": ["싱가포르"],
    "KHM": ["캄보디아"],
    "LAO": ["라오스"],
    "MMR": ["미얀마"],
    "BRN": ["브루나이"],
    "TLS": ["동티모르"],
    "ASEAN": ["아세안"],
}


def parse_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for tr in soup.select("table tbody tr"):
        a = tr.select_one('a[href*="/view"]')
        if a is None:
            continue
        m = re.search(r"/article/(ATCL\w+)/(\d+)/view", a["href"])
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        date = next((t for t in tds if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t)), "")
        rows.append(
            {
                "board": m.group(1),
                "seq": m.group(2),
                "row_number": tds[0].replace(",", ""),
                "category": tds[1] if len(tds) > 6 else "",
                "title": a.get_text(" ", strip=True),
                "department": tds[-4] if len(tds) >= 5 else "",
                "date": date,
            }
        )
    return rows


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=args.interval)

    def page(rel: str, params: dict, board: str) -> str | None:
        if raw_exists(SOURCE_ID, rel):
            return (raw_dir(SOURCE_ID) / rel).read_text(encoding="utf-8")
        url = f"{SITE}/kor/article/{board}"
        r = sess.get(url, params=params)
        if r.status_code != 200:
            logger.error("%s %s -> %s", url, params, r.status_code)
            return None
        save_raw(SOURCE_ID, rel, r.content, url=r.url, http_status=200)
        return r.content.decode("utf-8", errors="replace")

    def harvest(board: str, prefix: str, extra: dict) -> list[dict]:
        first = page(f"{prefix}/p0001.html", {"pageIndex": 1, "rowPageC": ROWS, **extra}, board)
        if not first:
            return []
        rows = parse_list(first)
        total = int(rows[0]["row_number"]) if rows and rows[0]["row_number"].isdigit() else 0
        for p in range(2, -(-total // ROWS) + 1):
            html = page(f"{prefix}/p{p:04d}.html", {"pageIndex": p, "rowPageC": ROWS, **extra}, board)
            rows += parse_list(html or "")
        return rows

    phases = args.phases.split(",")
    hits: dict[str, set[str]] = {b: set() for b in BOARDS}
    for board, (label, _) in BOARDS.items():
        if "lists" in phases:
            inv = harvest(board, f"lists/{board}", {})
            logger.info(
                "%s (%s): %d documents; dates %s..%s",
                board,
                label,
                len(inv),
                min((r["date"] for r in inv if r["date"]), default=""),
                max((r["date"] for r in inv if r["date"]), default=""),
            )
        if "search" in phases or "views" in phases:
            for words in TERMS.values():
                for w in words:
                    slug = re.sub(r"[^0-9A-Za-z가-힣]+", "_", w).strip("_")
                    rows = harvest(
                        board, f"search/{board}/{slug}", {"searchCondition": 2, "searchKeyword": w}
                    )
                    hits[board].update(r["seq"] for r in rows)
                    logger.info("%s content search %r: %d hits", board, w, len(rows))
    if "legacy" in phases:
        # Legacy releases (MOCIE/MKE/... era) were imported into motir.go.kr with the migration date
        # 2016-12-09; their pages carry the full text and the original release date in the body.
        board = "ATCL3f49a5a8c"
        legacy = []
        for f in sorted((raw_dir(SOURCE_ID) / "lists" / board).glob("p*.html")):
            legacy += [
                r["seq"] for r in parse_list(f.read_text(encoding="utf-8")) if r["date"] == LEGACY_DATE
            ]
        legacy = sorted(set(legacy), key=int, reverse=True)
        logger.info("legacy (migration-dated) releases: %d", len(legacy))
        n = 0
        for seq in legacy:
            rel = f"views/{board}/{seq}.html"
            if raw_exists(SOURCE_ID, rel):
                continue
            url = f"{SITE}/kor/article/{board}/{seq}/view"
            r = sess.get(url)
            if r.status_code == 200:
                save_raw(SOURCE_ID, rel, r.content, url=url, http_status=200, log=False)
                n += 1
                if n % 500 == 0:
                    logger.info("legacy views fetched: %d / %d", n, len(legacy))
        logger.info("legacy views fetched: %d", n)

    if "views" in phases:
        for board, seqs in hits.items():
            n = 0
            for seq in sorted(seqs, key=int, reverse=True):
                rel = f"views/{board}/{seq}.html"
                if raw_exists(SOURCE_ID, rel):
                    continue
                url = f"{SITE}/kor/article/{board}/{seq}/view"
                r = sess.get(url)
                if r.status_code == 200:
                    save_raw(SOURCE_ID, rel, r.content, url=url, http_status=200)
                    n += 1
            logger.info("%s: %d new views (distinct hits %d)", board, n, len(seqs))

    write_folder_readme(
        SOURCE_ID,
        f"""
# Korea trade/industry ministry (산업통상부, www.motir.go.kr) - web archive retrieval

Institution naming (record provenance; do not silently merge):
- 산업통상부 (site title at retrieval, domain motir.go.kr) - current
- 산업통상자원부 MOTIE (2013-03 .. 2025 reorganisation; www.motie.go.kr redirects to motir.go.kr)
- 지식경제부 MKE (2008-02 .. 2013-03) and 산업자원부 MOCIE (1998 .. 2008): NOT on this site.
- Trade negotiation (통상교섭본부) sat in 외교통상부 (MOFAT) 1998-2013 -> trade texts before 2013
  are in the MOFA corpus, not here.

Boards: {", ".join(f"{k} = {v[0]}" for k, v in BOARDS.items())}
Layout: `lists/<board>/pNNNN.html` (full inventory, {ROWS} rows/page); `search/<board>/<alias>/`
(site content search, searchCondition=2); `views/<board>/<seq>.html` (documents hit by any alias).
Stable URL: {SITE}/kor/article/<board>/<seq>/view. Attachments (PDF/HWP) listed, not downloaded.
Script: scripts/acquire/acq_kr_motie.py
""",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phases", default="lists,search,views,legacy")
    p.add_argument("--interval", type=float, default=1.2)
    run_step("acq_kr_motie", main, p)
