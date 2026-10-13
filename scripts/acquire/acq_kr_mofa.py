"""Acquire the Korean MOFA text corpus (www.mofa.go.kr; robots.txt: 'Allow: /').

Phases (run in order; each is resumable because existing raw files are skipped):
  lists    complete inventory of every configured board (document-count denominators)
  search   board full-content search for every country alias (document-level hits)
  views    document pages: ALL documents of small boards; alias hits for large boards
  papers   Diplomatic White Paper PDFs (Korean board m_4105)

Nothing is classified here. Metadata/text tables are built by scripts/acquire/build_gov_documents.py
from the raw HTML.
"""

import argparse
import re

import _bootstrap  # noqa: F401

from srl.acquisition.egov_board import Board, BoardHarvester, alias_slug
from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw, write_folder_readme
from srl.utils.cli import run_step
from srl.utils.config import load_config

SOURCE_ID = "kr_mofa"
SITE = "https://www.mofa.go.kr"
BOARDS = [
    # section, board_id, label, doc_type, language, fetch_all_views
    ("www", "m_4080", "보도자료 (press releases)", "press_release", "ko", False),
    ("www", "m_24815", "보도참고 및 설명자료 (explanatory releases)", "press_release", "ko", True),
    ("www", "m_4078", "외교부 브리핑 (spokesperson briefings)", "briefing", "ko", False),
    ("www", "m_20140", "연설 (speeches)", "speech", "ko", True),
    ("www", "m_4095", "기고·인터뷰 (op-eds, interviews)", "speech", "ko", False),
    ("www", "m_29514", "2026년 정상 외교활동 (summit diplomacy 2026)", "summit", "ko", True),
    ("www", "m_28650", "2025년 정상 외교활동 (summit diplomacy 2025)", "summit", "ko", True),
    ("www", "m_4175", "연도별 업무계획 (annual work plans)", "plan", "ko", True),
    ("eng", "m_5676", "Press Releases", "press_release", "en", False),
    ("eng", "m_5679", "Press Briefings", "briefing", "en", False),
    ("eng", "m_5689", "Speeches - Minister", "speech", "en", True),
    ("eng", "m_5690", "Speeches - Vice Ministers", "speech", "en", True),
    ("eng", "m_5691", "Speeches - Senior officials", "speech", "en", True),
]
PANEL = ["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM", "CHN"]
# Extra search strings beyond config/countries.yaml names/aliases (search recall only; final
# country attribution is re-done locally with srl.text.entities and its shields).
EXTRA_KO = {"CHN": ["한·중", "한중"], "VNM": ["한·베"], "IDN": [], "ASEAN": ["아세안"]}
EXTRA_EN = {"VNM": ["Viet Nam", "Vietnam"], "LAO": ["Lao", "Laos"], "ASEAN": ["ASEAN"]}


def search_terms() -> dict[str, dict[str, list[str]]]:
    cfg = load_config("countries")["countries"]
    terms = {"ko": {}, "en": {}}
    for iso in PANEL:
        c = cfg[iso]
        terms["ko"][iso] = list(
            dict.fromkeys([c["name_ko"], *c.get("aliases_ko", []), *EXTRA_KO.get(iso, [])])
        )
        en = [
            c["name"],
            *[a for a in c.get("aliases_en", []) if len(a) > 3 and "," not in a],
            *EXTRA_EN.get(iso, []),
        ]
        terms["en"][iso] = list(dict.fromkeys(en))
    terms["ko"]["ASEAN"] = EXTRA_KO["ASEAN"]
    terms["en"]["ASEAN"] = EXTRA_EN["ASEAN"]
    return terms


def slug(term: str) -> str:
    return alias_slug(term)


def main(args, logger) -> None:
    sess = PoliteSession(SOURCE_ID, min_interval=args.interval)
    h = BoardHarvester(SOURCE_ID, sess)
    boards = [
        (Board(SITE, sec, bid, label, dtype, lang), allv) for sec, bid, label, dtype, lang, allv in BOARDS
    ]
    phases = args.phases.split(",")
    inventory = {}
    if "lists" in phases or "views" in phases:
        for b, _ in boards:
            inventory[b.key] = h.harvest_list(b)
    hits: dict[str, set[str]] = {}
    if "search" in phases or "views" in phases:
        terms = search_terms()
        for b, allv in boards:
            if allv:
                continue
            seqs: set[str] = set()
            for words in terms[b.language].values():
                for w in words:
                    seqs.update(h.harvest_search(b, w, slug(w)))
            hits[b.key] = seqs
            logger.info("%s: %d distinct documents hit by any alias", b.key, len(seqs))
    if "views" in phases:
        # Priority: small boards in full first, then alias hits of large boards (newest first).
        for b, allv in sorted(boards, key=lambda x: not x[1]):
            seqs = (
                [r["seq"] for r in inventory.get(b.key, [])]
                if allv
                else sorted(hits.get(b.key, set()), key=int, reverse=True)
            )
            n = h.fetch_views(b, seqs)
            logger.info("%s: %d new document pages (target %d)", b.key, n, len(seqs))
    if "papers" in phases:
        fetch_white_papers(sess, logger)
    write_folder_readme(SOURCE_ID, readme(boards))


def fetch_white_papers(sess: PoliteSession, logger) -> None:
    """Diplomatic White Paper PDFs listed on the Korean board m_4105 (all pages)."""
    page, got = 1, 0
    while True:
        rel = f"lists/www_m_4105/p{page:04d}.html"
        url = f"{SITE}/www/brd/m_4105/list.do?page={page}"
        if raw_exists(SOURCE_ID, rel):
            html = (raw_dir(SOURCE_ID) / rel).read_text(encoding="utf-8")
        else:
            r = sess.get(url)
            html = r.content.decode("utf-8", errors="replace")
            save_raw(SOURCE_ID, rel, r.content, url=url, http_status=r.status_code)
        links = re.findall(
            r'href="\./(down\.do\?brd_id=N8701&amp;seq=(\d+)&amp;data_tp=A&amp;'
            r'file_seq=(\d+))"[^>]*>\s*([^<]+?)\s*</a>',
            html,
        )
        if not links:
            break
        for href, seq, fseq, name in links:
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else "bin"
            rel = f"white_papers/wp_{seq}_{fseq}.{ext}"
            if raw_exists(SOURCE_ID, rel):
                continue
            # "./down.do" is relative to the board folder (/www/brd/m_4105/); /www/brd/down.do is a 404 page
            durl = f"{SITE}/www/brd/m_4105/{href.replace('&amp;', '&')}"
            r = sess.get(durl)
            if r.status_code == 200 and len(r.content) > 1000:
                save_raw(SOURCE_ID, rel, r.content, url=durl, http_status=200, notes=name.strip())
                got += 1
        page += 1
        if page > 30:
            break
    logger.info("White paper files downloaded: %d", got)


def readme(boards) -> str:
    rows = "\n".join(
        f"| `{b.key}` | {b.label} | {b.doc_type} | {b.language} | "
        f"{'all documents' if allv else 'documents hit by a country-alias content search'} |"
        for b, allv in boards
    )
    return f"""
# Korea Ministry of Foreign Affairs (MOFA) - web archive retrieval

Site: {SITE} (robots.txt: `User-agent: * / Allow: /`). Retrieval at <= 1 request per ~1.2 s.

| board key | board | doc_type | lang | full text retrieved for |
|---|---|---|---|---|
{rows}

Layout
- `lists/<board>/pNNNN.html`: every list page (50 rows) - complete inventory incl. titles, dates,
  departments. This is the denominator for attention measures.
- `search/<board>/<alias>/pNNNN.html`: MOFA's own full-content search (`srchTp=1`) per alias
  (aliases from config/countries.yaml + extras in the script). Search recall is the site's; hits
  are a superset for download purposes (e.g. '중국' also matches '남중국해').
- `views/<board>/<seq>.html`: document pages (title, date, department, body, attachment list).
  Stable URL: {SITE}/<section>/brd/<board_id>/view.do?seq=<seq>
- `white_papers/wp_<seq>_<file_seq>.pdf`: Diplomatic White Paper chapters (board m_4105).

Licence: Korean public-sector works; many pages carry a KOGL (공공누리) type mark, recorded per
document in the derived table. Redistribute derived measures, not full texts, unless the KOGL type
permits. Attachments (HWP/HWPX/PDF) are listed but not downloaded (except white papers).
Script: scripts/acquire/acq_kr_mofa.py
"""


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phases", default="lists,search,views,papers")
    p.add_argument("--interval", type=float, default=1.2)
    run_step("acq_kr_mofa", main, p)
