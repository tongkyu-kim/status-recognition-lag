"""Acquire pre-2014 trade/industry ministry press releases from 정책브리핑 (www.korea.kr).

korea.kr (Ministry of Culture, Sports and Tourism government portal) re-publishes every
ministry's press releases. Filtering by ``repCode=A00015`` returns the trade/industry ministry
lineage, labelled with the ministry name at the time (지식경제부 2008-13, 산업통상자원부 2013-).
Nothing is returned under this code before 2008 (산업자원부 era) - checked 2026-09-30.

For 2008-2013 the page body is usually a stub ("이 자료는 ... 보도자료를 전재") and the text is in
an HWP attachment. We therefore:
  1. harvest the complete list inventory for each year (titles, dates, ministry label);
  2. for items whose TITLE mentions a target country alias, download the page and its
     attachments (HWP/PDF) for later text extraction.
Bulk attachment download for all items is a documented next step (docs/manual_data_tasks.md).
robots.txt: allows all except /totalSearch.do (not used).
"""

import argparse
import re

import _bootstrap  # noqa: F401
from bs4 import BeautifulSoup

from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "kr_policy_briefing"
SITE = "https://www.korea.kr"
LIST = f"{SITE}/briefing/pressReleaseList.do"
REP_CODE = "A00015"
ALIASES = [
    "중국",
    "한·중",
    "한중",
    "베트남",
    "한·베",
    "인도네시아",
    "인니",
    "말레이시아",
    "태국",
    "필리핀",
    "싱가포르",
    "캄보디아",
    "라오스",
    "미얀마",
    "브루나이",
    "동티모르",
    "아세안",
    "ASEAN",
    "동남아",
]


def parse_list(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.select('div.list_type li a[href*="pressReleaseView"]'):
        m = re.search(r"newsId=(\d+)", a["href"])
        title = a.select_one("strong")
        src = [s.get_text(strip=True) for s in a.select(".source span")]
        out.append(
            {
                "news_id": m.group(1),
                "title": title.get_text(" ", strip=True) if title else "",
                "date": src[0] if src else "",
                "ministry": src[1] if len(src) > 1 else "",
            }
        )
    return out


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=args.interval)

    def get(rel: str, url: str, params: dict | None = None) -> str | None:
        if raw_exists(SOURCE_ID, rel):
            return (raw_dir(SOURCE_ID) / rel).read_text(encoding="utf-8")
        r = sess.get(url, params=params)
        if r.status_code != 200:
            logger.error("%s -> %s", url, r.status_code)
            return None
        save_raw(SOURCE_ID, rel, r.content, url=r.url, http_status=200)
        return r.content.decode("utf-8", errors="replace")

    inventory = []
    for year in range(args.start, args.end + 1):
        params = {"repCode": REP_CODE, "startDate": f"{year}-01-01", "endDate": f"{year}-12-31"}
        first = get(f"lists/{year}/p0001.html", LIST, {**params, "pageIndex": 1})
        if not first:
            continue
        m = re.search(r"총\s*(?:<[^>]+>\s*)*([\d,]+)\s*(?:<[^>]+>\s*)*건", first)
        total = int(m.group(1).replace(",", "")) if m else 0
        rows = parse_list(first)
        per_page = max(len(rows), 1)
        for p in range(2, -(-total // per_page) + 1):
            html = get(f"lists/{year}/p{p:04d}.html", LIST, {**params, "pageIndex": p})
            rows += parse_list(html or "")
        logger.info("%d: %d releases listed (site total %d)", year, len(rows), total)
        inventory += rows

    hits = [r for r in inventory if any(a in r["title"] for a in ALIASES)]
    logger.info("Title alias hits: %d of %d", len(hits), len(inventory))
    for r in hits:
        rel = f"views/{r['news_id']}.html"
        html = get(rel, f"{SITE}/briefing/pressReleaseView.do", {"newsId": r["news_id"]})
        if not html:
            continue
        soup = BeautifulSoup(html, "lxml")
        for i, a in enumerate(soup.select(".filedown a[href]")):
            href = a["href"]
            name = a.get_text(" ", strip=True)
            if "바로보기" in name or href.startswith("javascript"):
                continue
            ext = name.rsplit(".", 1)[-1].lower()[:5] if "." in name else "bin"
            frel = f"attachments/{r['news_id']}_{i}.{ext}"
            if raw_exists(SOURCE_ID, frel):
                continue
            url = href if href.startswith("http") else SITE + href
            resp = sess.get(url)
            if resp.status_code == 200 and len(resp.content) > 200:
                save_raw(SOURCE_ID, frel, resp.content, url=url, http_status=200, notes=name[:200])

    write_folder_readme(
        SOURCE_ID,
        f"""
# 정책브리핑 (www.korea.kr) - trade/industry ministry press releases {args.start}-{args.end}

- List: {LIST}?repCode={REP_CODE}&startDate=YYYY-01-01&endDate=YYYY-12-31&pageIndex=N
  (`lists/<year>/pNNNN.html`): complete inventory with title, date and ministry label at the time.
- `views/<newsId>.html` + `attachments/<newsId>_<i>.<ext>`: releases whose TITLE contains an alias
  ({", ".join(ALIASES)}). 2008-13 bodies are stubs; text is in the HWP attachment.
- No items exist under {REP_CODE} before 2008 (산업자원부 era not linked) - checked at retrieval.
- Licence: korea.kr content is 공공누리 (KOGL) per item; attachments are the ministries' own files.
Script: scripts/acquire/acq_kr_policy_briefing.py
""",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", type=int, default=2008)
    p.add_argument("--end", type=int, default=2014)
    p.add_argument("--interval", type=float, default=1.2)
    run_step("acq_kr_policy_briefing", main, p)
