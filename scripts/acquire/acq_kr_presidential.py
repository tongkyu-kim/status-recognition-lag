"""Acquire Korean presidential speeches and briefings.

1. Presidential Archives (대통령기록관, www.pa.go.kr) speech database, 1948 - Yoon (2025):
   - `pa/export_speech_list.xls`: the site's own Excel export of the full speech inventory
   - `pa/lists/pNNNN.html`: list pages (oldest first, 100/page) - carry the stable artid
   - `pa/views/<artid>.html`: speech texts (form 연설문) for presidents from 노태우 (1988) onward
2. Presidential Office (www.president.go.kr, current administration from 2025-06):
   - `office/<board>/list_pNNN.json`: the board JSON the public page itself loads
   - `office/<board>/views/<BBS_CD>.html`: full document pages
robots.txt: pa.go.kr has none (error page); president.go.kr robots.txt is empty (no restrictions).
"""

import argparse
import json
import re

import _bootstrap  # noqa: F401
from bs4 import BeautifulSoup

from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step

SOURCE_ID = "kr_presidential_office"
PA = "https://www.pa.go.kr/research/contents/speech/index.jsp"
PA_EXPORT = "https://www.pa.go.kr/portal/research/speech/route.do"
OFFICE = "https://www.president.go.kr"
MODERN = ["노태우", "김영삼", "김대중", "노무현", "이명박", "박근혜", "문재인", "윤석열"]


def parse_pa_list(html: str) -> list[dict]:
    rows = []
    for tr in BeautifulSoup(html, "lxml").select("table tbody tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        a = tr.select_one("a[href*='artid=']")
        if not a or len(tds) < 6:
            continue
        m = re.search(r"catid=(\w+)&artid=(\d+)", a["href"])
        rows.append(
            {
                "no": tds[0],
                "president": tds[1],
                "form": tds[2],
                "speech_type": tds[3],
                "title": tds[4],
                "date": tds[5],
                "catid": m.group(1),
                "artid": m.group(2),
            }
        )
    return rows


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=args.interval)

    def cached(rel: str):
        return (raw_dir(SOURCE_ID) / rel).read_text(encoding="utf-8") if raw_exists(SOURCE_ID, rel) else None

    # ---- 1. Presidential Archives
    if "pa" in args.parts:
        if not raw_exists(SOURCE_ID, "pa/export_speech_list.xls"):
            r = sess.post(
                PA_EXPORT,
                data={
                    "priorityCatid": "c_pa02062",
                    "isExcel": "Y",
                    "excelType": "1",
                    "pageIndex": "1",
                    "pageUnit": "20",
                    "searchIn": "Y",
                },
            )
            save_raw(
                SOURCE_ID,
                "pa/export_speech_list.xls",
                r.content,
                url=PA_EXPORT,
                http_status=r.status_code,
                notes="site Excel export (HTML table), all speeches",
            )
        rows, page = [], 1
        while True:
            rel = f"pa/lists/p{page:04d}.html"
            html = cached(rel)
            if html is None:
                r = sess.get(PA, params={"pageIndex": page, "pageUnit": 100, "orderColumn": 1})
                html = r.content.decode("utf-8", errors="replace")
                save_raw(SOURCE_ID, rel, r.content, url=r.url, http_status=r.status_code)
            got = parse_pa_list(html)
            if not got:
                break
            rows += got
            page += 1
        logger.info("PA inventory: %d records on %d pages", len(rows), page - 1)
        targets = [r for r in rows if r["form"] == "연설문" and r["president"] in MODERN]
        logger.info("PA speech texts to fetch (%s): %d", "..".join([MODERN[0], MODERN[-1]]), len(targets))
        n = 0
        for r in targets:
            rel = f"pa/views/{r['artid']}.html"
            if raw_exists(SOURCE_ID, rel):
                continue
            url = f"{PA}?spMode=view&catid={r['catid']}&artid={r['artid']}"
            resp = sess.get(url)
            if resp.status_code == 200:
                save_raw(SOURCE_ID, rel, resp.content, url=url, http_status=200)
                n += 1
                if n % 250 == 0:
                    logger.info("PA: %d speech pages fetched", n)

    # ---- 2. Presidential Office (current administration)
    if "office" in args.parts:
        for board in ("speeches", "briefings"):
            page_html = sess.get(f"{OFFICE}/{board}").text
            form = BeautifulSoup(page_html, "lxml").select_one("#sendForm")
            params = {i["name"]: i.get("value", "") for i in form.select("input[type=hidden][name]")}
            params["pagePerCnt"] = 50
            items, page = [], 1
            while True:
                rel = f"office/{board}/list_p{page:03d}.json"
                body = cached(rel)
                if body is None:
                    params["pageNo"] = page
                    r = sess.post(
                        f"{OFFICE}/ajaxf/frBoard/bbsViewGalleryList.do",
                        data=params,
                        headers={"X-Requested-With": "XMLHttpRequest", "Referer": f"{OFFICE}/{board}"},
                    )
                    body = r.content.decode("utf-8")
                    got = json.loads(body)["data"]["list"]
                    if not got:
                        break
                    save_raw(
                        SOURCE_ID,
                        rel,
                        r.content,
                        url=r.url,
                        http_status=r.status_code,
                        notes=f"{board} JSON list page {page}",
                    )
                got = json.loads(body)["data"]["list"]
                if not got:
                    break
                items += got
                page += 1
            logger.info("Office %s: %d items", board, len(items))
            for it in items:
                rel = f"office/{board}/views/{it['BBS_CD']}.html"
                if raw_exists(SOURCE_ID, rel):
                    continue
                url = f"{OFFICE}/{board}/{it['BBS_CD']}"
                r = sess.get(url)
                if r.status_code == 200:
                    save_raw(SOURCE_ID, rel, r.content, url=url, http_status=200)

    write_folder_readme(
        SOURCE_ID,
        f"""
# Korean presidential speeches and briefings

## Presidential Archives (대통령기록관) - {PA}
- `pa/export_speech_list.xls`: the site's Excel export (HTML table) of the whole speech inventory
  (all presidents; forms: 연설문 text / 연설음성 audio / 연설동영상 video).
- `pa/lists/pNNNN.html`: list pages, oldest first, 100 rows; each row links to a stable
  `?spMode=view&catid=<catid>&artid=<artid>` page.
- `pa/views/<artid>.html`: speech TEXTS (form 연설문) for {", ".join(MODERN)}.
  Fields on the page: title, date, president, venue (국내/국외), type (취임사, 기념사, 축사, 성명/담화문,
  국회연설, 신년사, 회의, 환영사, 기타), bibliographic source, full text.
- Earlier presidents are in the inventory but texts were not fetched (outside study period).

## Presidential Office (대통령실/청와대) - {OFFICE}
- `office/<speeches|briefings>/list_pNNN.json`: JSON the public board page loads
  (`/ajaxf/frBoard/bbsViewGalleryList.do`), excerpts only; `views/<BBS_CD>.html`: full pages.
- Covers the current administration only (from June 2025). Moon/Yoon-era Office pages are archived
  by the Presidential Archives (web archive) - see docs/manual_data_tasks.md.

Administration metadata (president) is recorded per document. Script: scripts/acquire/acq_kr_presidential.py
""",
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parts", default="pa,office")
    p.add_argument("--interval", type=float, default=1.2)
    run_step("acq_kr_presidential", main, p)
