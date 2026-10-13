"""Build the Korean government document table from the raw web-archive layer.

Sources: kr_mofa, kr_motie (motir.go.kr), kr_policy_briefing (korea.kr, 2008-14 trade/industry
lineage), kr_presidential_office (Presidential Archives + current Office).

Outputs
    data/interim/prelim/gov_documents_korea.csv      one row per document (metadata only)
    data/interim/text/gov_documents_korea_text.parquet  doc_id + full text (where retrieved)
    outputs/diagnostics/gov_corpus_coverage.csv       source x year counts (inventory / text / hits)
    outputs/diagnostics/gov_mention_surface_counts.csv  alias surface forms matched (for KWIC review)

Nothing is classified. ``site_search_hits`` = aliases for which the site's own content search
returned the document; ``mentions_*`` = local counts by srl.text.entities (shields applied).
Both are candidate attention inputs that need validation.
"""

import argparse
import hashlib
import json
import os
import pickle
import re
import time
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
from pathlib import Path

import _bootstrap  # noqa: F401
import pandas as pd
from bs4 import BeautifulSoup

from srl.acquisition.egov_board import parse_list_page, parse_view_page
from srl.acquisition.extract import html_block_text, sniff_and_extract
from srl.utils.cli import run_step
from srl.utils.config import get_path
from srl.utils.io import write_table

RAW = get_path("data.raw")
PARTNERS = ["BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM", "CHN"]
MOFA_BOARDS = {  # key -> (doc_type, language, label)
    "www_m_4080": ("press_release", "ko", "보도자료"),
    "www_m_24815": ("press_release", "ko", "보도참고·설명자료"),
    "www_m_4078": ("briefing", "ko", "외교부 브리핑"),
    "www_m_20140": ("speech", "ko", "연설"),
    "www_m_4095": ("op_ed_interview", "ko", "기고·인터뷰"),
    "www_m_29514": ("summit", "ko", "정상 외교활동 2026"),
    "www_m_28650": ("summit", "ko", "정상 외교활동 2025"),
    "www_m_4175": ("plan", "ko", "연도별 업무계획"),
    "eng_m_5676": ("press_release", "en", "Press Releases"),
    "eng_m_5679": ("briefing", "en", "Press Briefings"),
    "eng_m_5689": ("speech", "en", "Speeches - Minister"),
    "eng_m_5690": ("speech", "en", "Speeches - Vice Ministers"),
    "eng_m_5691": ("speech", "en", "Speeches - Senior officials"),
}
ALIAS_ISO = {  # search-folder slug -> ISO3 / group (site-search provenance only)
    "중국": "CHN",
    "한_중": "CHN",
    "한중": "CHN",
    "China": "CHN",
    "People_s_Republic_of_China": "CHN",
    "Mainland_China": "CHN",
    "베트남": "VNM",
    "월남": "VNM",
    "한_베": "VNM",
    "Viet_Nam": "VNM",
    "Vietnam": "VNM",
    "Socialist_Republic_of_Viet_Nam": "VNM",
    "Socialist_Republic_of_Vietnam": "VNM",
    "인도네시아": "IDN",
    "인니": "IDN",
    "Indonesia": "IDN",
    "Republic_of_Indonesia": "IDN",
    "말레이시아": "MYS",
    "Malaysia": "MYS",
    "태국": "THA",
    "Thailand": "THA",
    "Kingdom_of_Thailand": "THA",
    "필리핀": "PHL",
    "Philippines": "PHL",
    "The_Philippines": "PHL",
    "Republic_of_the_Philippines": "PHL",
    "싱가포르": "SGP",
    "싱가폴": "SGP",
    "Singapore": "SGP",
    "Republic_of_Singapore": "SGP",
    "캄보디아": "KHM",
    "Cambodia": "KHM",
    "Kingdom_of_Cambodia": "KHM",
    "Kampuchea": "KHM",
    "라오스": "LAO",
    "Lao_PDR": "LAO",
    "Lao": "LAO",
    "Laos": "LAO",
    "Lao_P_D_R": "LAO",
    "Lao_People_s_Democratic_Republic": "LAO",
    "미얀마": "MMR",
    "버마": "MMR",
    "Myanmar": "MMR",
    "Burma": "MMR",
    "Republic_of_the_Union_of_Myanmar": "MMR",
    "브루나이": "BRN",
    "브루나이_다루살람": "BRN",
    "Brunei": "BRN",
    "Brunei_Darussalam": "BRN",
    "Negara_Brunei_Darussalam": "BRN",
    "동티모르": "TLS",
    "티모르레스테": "TLS",
    "티모르_레스테": "TLS",
    "Timor_Leste": "TLS",
    "East_Timor": "TLS",
    "Democratic_Republic_of_Timor_Leste": "TLS",
    "아세안": "ASEAN",
    "ASEAN": "ASEAN",
}


def _alias_folder_map() -> dict[str, str]:
    """Search-folder name -> ISO3, from config/countries.yaml terms through the same slug function
    the collectors use (plus the static map below for the Korean compound forms)."""
    from srl.acquisition.egov_board import alias_slug
    from srl.utils.config import load_config

    out = dict(ALIAS_ISO)
    for iso, c in load_config("countries")["countries"].items():
        if iso not in PARTNERS:
            continue
        for t in [c["name"], c.get("name_ko"), *c.get("aliases_en", []), *c.get("aliases_ko", [])]:
            if t:
                out.setdefault(alias_slug(t), iso)
    return out


PRESIDENT_TERMS = [
    ("노태우", "1988-02-25"),
    ("김영삼", "1993-02-25"),
    ("김대중", "1998-02-25"),
    ("노무현", "2003-02-25"),
    ("이명박", "2008-02-25"),
    ("박근혜", "2013-02-25"),
    ("문재인", "2017-05-10"),
    ("윤석열", "2022-05-10"),
    ("이재명", "2025-06-04"),
]


def administration(date: str) -> str:
    admin = ""
    for name, start in PRESIDENT_TERMS:
        if date and date >= start:
            admin = name
    return admin


def runs(source: str) -> list[Path]:
    root = RAW / source
    return sorted(p for p in root.iterdir() if p.is_dir()) if root.exists() else []


def read(path: Path) -> str:
    return path.read_bytes().decode("utf-8", errors="replace")


# --------------------------------------------------------------------------- cached parallel parsing
def _work(task: tuple[str, str]):
    name, path = task
    return PARSERS[name](read(Path(path)))


def parse_many(name: str, paths: list[Path]) -> dict[Path, object]:
    """Parse files with PARSERS[name] in a process pool; results cached by (size, mtime) so a
    rebuild only parses new or changed raw files."""
    # Disposable cache kept OUTSIDE Dropbox (sync locks files and would upload hundreds of MB).
    base = Path(
        os.environ.get("SRL_CACHE_DIR") or Path(os.environ.get("LOCALAPPDATA", Path.home())) / "srl_cache"
    )
    cache_path = base / "parse_cache" / f"{name}.pkl"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache = pickle.loads(cache_path.read_bytes()) if cache_path.exists() else {}
    out, todo = {}, []
    for p in paths:
        st = p.stat()
        key, sig = str(p.relative_to(RAW)), (st.st_size, st.st_mtime_ns)
        hit = cache.get(key)
        if hit is not None and hit[0] == sig:
            out[p] = hit[1]
        else:
            todo.append((p, key, sig))
    if todo:
        workers = max(1, (os.cpu_count() or 2) - 1)
        with ProcessPoolExecutor(max_workers=workers) as ex:
            results = ex.map(_work, [(name, str(p)) for p, _, _ in todo], chunksize=32)
            for (p, key, sig), res in zip(todo, results, strict=True):
                out[p] = res
                cache[key] = (sig, res)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_bytes(pickle.dumps(cache, protocol=pickle.HIGHEST_PROTOCOL))
        for attempt in range(5):  # antivirus/indexers can briefly lock a fresh file on Windows
            try:
                tmp.replace(cache_path)
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(2)
    return out


FOLDER_ISO: dict[str, str] = {}


def search_hits(run: Path) -> dict[tuple[str, str], set[str]]:
    """(board, seq) -> ISO set, from saved site-search pages."""
    hits: dict[tuple[str, str], set[str]] = {}
    sroot = run / "search"
    if not sroot.exists():
        return hits
    is_mofa = "kr_mofa" in str(run)
    pages = [
        (board_dir.name, FOLDER_ISO.get(alias_dir.name), f)
        for board_dir in sroot.iterdir()
        for alias_dir in board_dir.iterdir()
        if FOLDER_ISO.get(alias_dir.name)
        for f in alias_dir.glob("p*.html")
    ]
    parsed = parse_many("mofa_list", [f for _, _, f in pages]) if is_mofa else {}
    for board, iso, f in pages:
        seqs = (
            [r["seq"] for r in parsed[f]] if is_mofa else re.findall(r"/article/ATCL\w+/(\d+)/view", read(f))
        )
        for seq in seqs:
            hits.setdefault((board, seq), set()).add(iso)
    return hits


# --------------------------------------------------------------------------- per source
def mofa(logger) -> pd.DataFrame:
    rows = []
    for run in runs("kr_mofa"):
        hits = search_hits(run)
        for key, (dtype, lang, label) in MOFA_BOARDS.items():
            section, board_id = key.split("_", 1)
            inv = {}
            lists = parse_many("mofa_list", sorted((run / "lists" / key).glob("p*.html")))
            for f in sorted(lists):
                for r in lists[f]:
                    inv.setdefault(r["seq"], r)
            vdir = run / "views" / key
            views = parse_many("mofa_view", sorted(vdir.glob("*.html")) if vdir.exists() else [])
            for seq, r in inv.items():
                view = vdir / f"{seq}.html"
                v = views.get(view, {})
                rows.append(
                    {
                        "doc_id": f"kr_mofa:{key}:{seq}",
                        "source_id": "kr_mofa",
                        "institution": "MOFA",
                        "institution_label": "외교부" if r["date"] >= "2013-03-23" else "외교통상부",
                        "board": label,
                        "doc_type": dtype,
                        "language": lang,
                        "title": v.get("title") or r["title"],
                        "date": v.get("date") or r["date"],
                        "department": v.get("department") or r["department"],
                        "url": f"https://www.mofa.go.kr/{section}/brd/{board_id}/view.do?seq={seq}",
                        "text": v.get("text", ""),
                        "text_source": "html_body" if view.exists() else "",
                        "attachments": "|".join(a["name"] for a in v.get("attachments", [])),
                        "kogl": v.get("kogl", ""),
                        "site_search_hits": "|".join(sorted(hits.get((key, seq), set()))),
                        "raw_file": str(view.relative_to(RAW)) if view.exists() else "",
                    }
                )
    df = pd.DataFrame(rows).drop_duplicates("doc_id") if rows else pd.DataFrame()  # earliest run wins
    logger.info(
        "MOFA: %d documents, %d with text", len(df), (df["text"].str.len() > 0).sum() if len(df) else 0
    )
    return df


def parse_motie_view(html: str) -> dict:
    b = BeautifulSoup(html, "lxml")
    info = {
        li.select_one("em").get_text(strip=True): li.select_one("span").get_text(" ", strip=True)
        for li in b.select(".detail-info li")
        if li.select_one("em") and li.select_one("span")
    }
    body = b.select_one(".detail-cont")
    return {
        "title": b.select_one(".detail-tit").get_text(" ", strip=True) if b.select_one(".detail-tit") else "",
        "date": info.get("등록일", ""),
        "department": info.get("담당부서", ""),
        "text": html_block_text(body),
        "attachments": " | ".join(a.get("title", "") for a in b.select(".info-down a[title]")),
    }


def motie(logger) -> pd.DataFrame:
    rows = []
    labels = {
        "ATCL3f49a5a8c": ("press_release", "보도자료"),
        "ATCLe0854704d": ("press_release", "보도설명자료"),
    }
    for run in runs("kr_motie"):
        hits = search_hits(run)
        for board, (dtype, label) in labels.items():
            inv = {}
            lists = parse_many("motie_list", sorted((run / "lists" / board).glob("p*.html")))
            for f in sorted(lists):
                for seq, r in lists[f]:
                    inv.setdefault(seq, r)
            vdir = run / "views" / board
            views = parse_many("motie_view", sorted(vdir.glob("*.html")) if vdir.exists() else [])
            for seq, r in inv.items():
                view = vdir / f"{seq}.html"
                v = views.get(view, {})
                date = v.get("date") or r["date"]
                rows.append(
                    {
                        "doc_id": f"kr_motie:{board}:{seq}",
                        "source_id": "kr_motie",
                        "institution": "MOTIE",
                        "institution_label": "산업통상자원부/산업통상부 (motir.go.kr archive)",
                        "board": label,
                        "doc_type": dtype,
                        "language": "ko",
                        "title": v.get("title") or r["title"],
                        "date": date,
                        "department": v.get("department", ""),
                        "url": f"https://www.motir.go.kr/kor/article/{board}/{seq}/view",
                        "text": v.get("text", ""),
                        "text_source": "html_body" if view.exists() else "",
                        "attachments": v.get("attachments", ""),
                        "kogl": "",
                        "site_search_hits": "|".join(sorted(hits.get((board, seq), set()))),
                        "raw_file": str(view.relative_to(RAW)) if view.exists() else "",
                    }
                )
    df = pd.DataFrame(rows).drop_duplicates("doc_id") if rows else pd.DataFrame()  # earliest run wins
    logger.info(
        "MOTIE: %d documents, %d with text", len(df), (df["text"].str.len() > 0).sum() if len(df) else 0
    )
    return df


def policy_briefing(logger) -> pd.DataFrame:
    rows = []
    for run in runs("kr_policy_briefing"):
        att_text: dict[str, list[tuple[str, str]]] = {}
        seen_hash = set()
        for f in sorted((run / "attachments").glob("*")):
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
            if digest in seen_hash:  # the same file is linked twice (바로보기 / 내려받기)
                continue
            seen_hash.add(digest)
            fmt, text = sniff_and_extract(f)
            att_text.setdefault(f.name.split("_")[0], []).append((fmt, text))
        for f in sorted((run / "lists").glob("*/p*.html")):
            soup = BeautifulSoup(read(f), "lxml")
            for a in soup.select('div.list_type li a[href*="pressReleaseView"]'):
                nid = re.search(r"newsId=(\d+)", a["href"]).group(1)
                src = [s.get_text(strip=True) for s in a.select(".source span")]
                title = a.select_one("strong").get_text(" ", strip=True) if a.select_one("strong") else ""
                view = run / "views" / f"{nid}.html"
                body = ""
                if view.exists():
                    vb = BeautifulSoup(read(view), "lxml")
                    body = (
                        html_block_text(vb.select_one(".article_body"))
                        if vb.select_one(".article_body")
                        else ""
                    )
                texts = [
                    t for fmt, t in att_text.get(nid, []) if t and not t.startswith("__EXTRACTION_ERROR__")
                ]
                text = "\n\n".join(texts) if texts else (body if len(body) > 200 else "")
                ministry = src[1] if len(src) > 1 else ""
                rows.append(
                    {
                        "doc_id": f"kr_policy_briefing:{nid}",
                        "source_id": "kr_policy_briefing",
                        "institution": "MOTIE",
                        "institution_label": ministry,
                        "board": "정책브리핑 보도자료 (A00015)",
                        "doc_type": "press_release",
                        "language": "ko",
                        "title": title,
                        "date": src[0].replace(".", "-") if src else "",
                        "department": "",
                        "url": f"https://www.korea.kr/briefing/pressReleaseView.do?newsId={nid}",
                        "text": text,
                        "text_source": ("attachment_" + "+".join(sorted({fmt for fmt, _ in att_text[nid]})))
                        if texts
                        else ("html_body" if text else ""),
                        "attachments": "",
                        "kogl": "",
                        "site_search_hits": "",
                        "raw_file": str(view.relative_to(RAW)) if view.exists() else "",
                    }
                )
    df = pd.DataFrame(rows).drop_duplicates("doc_id") if rows else pd.DataFrame()
    logger.info(
        "korea.kr: %d documents, %d with text", len(df), (df["text"].str.len() > 0).sum() if len(df) else 0
    )
    return df


def presidential(logger) -> pd.DataFrame:
    rows = []
    for run in runs("kr_presidential_office"):
        inv = {}
        lists = parse_many("pa_list", sorted((run / "pa" / "lists").glob("p*.html")))
        for f in sorted(lists):
            for artid, r in lists[f]:
                inv.setdefault(artid, r)
        vdir = run / "pa" / "views"
        pa_views = parse_many("pa_view", sorted(vdir.glob("*.html")) if vdir.exists() else [])
        for artid, r in inv.items():
            if r["form"] != "연설문":
                continue
            view = run / "pa" / "views" / f"{artid}.html"
            text, venue, source_ref = "", "", ""
            if view in pa_views:
                text, venue, source_ref = pa_views[view]
            rows.append(
                {
                    "doc_id": f"kr_presidential:pa:{artid}",
                    "source_id": "kr_presidential_office",
                    "institution": "President",
                    "institution_label": f"대통령 {r['president']}",
                    "board": f"대통령기록관 연설기록 ({r['type']})",
                    "doc_type": "speech",
                    "language": "ko",
                    "title": r["title"],
                    "date": r["date"],
                    "department": venue,
                    "url": f"https://www.pa.go.kr/research/contents/speech/index.jsp?spMode=view&catid={r['catid']}&artid={artid}",
                    "text": text,
                    "text_source": "html_body" if text else "",
                    "attachments": source_ref,
                    "kogl": "",
                    "site_search_hits": "",
                    "raw_file": str(view.relative_to(RAW)) if view.exists() else "",
                    "president": r["president"],
                    "speech_type": r["type"],
                }
            )
        for board in ("speeches", "briefings"):
            odir = run / "office" / board / "views"
            office_views = parse_many("office_view", sorted(odir.glob("*.html")) if odir.exists() else [])
            for f in sorted((run / "office" / board).glob("list_p*.json")):
                for it in json.loads(f.read_text(encoding="utf-8"))["data"]["list"]:
                    view = run / "office" / board / "views" / f"{it['BBS_CD']}.html"
                    text = ""
                    if view in office_views:
                        text = office_views[view]
                    rows.append(
                        {
                            "doc_id": f"kr_presidential:office:{board}:{it['BBS_CD']}",
                            "source_id": "kr_presidential_office",
                            "institution": "President",
                            "institution_label": "대통령실 (이재명)",
                            "board": f"president.go.kr {board}",
                            "doc_type": "speech" if board == "speeches" else "briefing",
                            "language": "ko",
                            "title": it.get("SUBJECT", ""),
                            "date": it.get("WRITE_DT", "")[:10],
                            "department": "",
                            "url": f"https://www.president.go.kr/{board}/{it['BBS_CD']}",
                            "text": text or it.get("CONTENTS", ""),
                            "text_source": "html_body" if text else "list_excerpt",
                            "attachments": "",
                            "kogl": "",
                            "site_search_hits": "",
                            "raw_file": str(view.relative_to(RAW))
                            if view.exists()
                            else str(f.relative_to(RAW)),
                            "president": "이재명",
                            "speech_type": "",
                        }
                    )
    df = pd.DataFrame(rows).drop_duplicates("doc_id") if rows else pd.DataFrame()
    logger.info(
        "Presidential: %d documents, %d with text",
        len(df),
        (df["text"].str.len() > 0).sum() if len(df) else 0,
    )
    return df


# --------------------------------------------------------------------------- date repair
MOTIE_MIGRATION_DATE = "2016-12-09"  # legacy releases imported into motir.go.kr carry this date
_RELEASE_DATE = [
    re.compile(r"보도\s*일(?:시|자)?\s*[:：]?\s*((?:19|20)\d{2})\s*[.년]\s*(\d{1,2})\s*[.월]\s*(\d{1,2})"),
    re.compile(
        r"((?:19|20)\d{2})\s*년\s*(\d{1,2})\s*월\s*(\d{1,2})\s*일\s*\(?[월화수목금토일]?\)?\s*(?:\d{1,2}\s*시)?[^\n]{0,15}(?:조간|석간|보도)"
    ),
    re.compile(
        r"[‘'’]((?:\d{2}))\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})\s*\.?\s*\(?[월화수목금토일]?\)?\s*(?:조간|석간)"
    ),
]


def _ymd(y: str, m: str, d: str) -> str | None:
    year = int(y) if len(y) == 4 else (2000 + int(y) if int(y) < 50 else 1900 + int(y))
    try:
        return pd.Timestamp(year=year, month=int(m), day=int(d)).strftime("%Y-%m-%d")
    except ValueError:
        return None


# Ministry eras (name at the time -> validity window). A name in the text bounds the release date.
MINISTRY_ERAS = [
    (r"산업통상자원부|산업부", "2013-03-23", "2016-12-08"),
    (r"지식경제부|지경부", "2008-02-29", "2013-03-22"),
    (r"산업자원부|산자부", "1998-02-28", "2008-02-28"),
    (r"통상산업부|통산부", "1994-12-24", "1998-02-27"),
    (r"상공자원부", "1993-03-06", "1994-12-23"),
    (r"상공부", "1990-01-01", "1993-03-05"),
]
LEGACY_LO, LEGACY_HI = pd.Timestamp("1990-01-01"), pd.Timestamp("2016-12-08")
_WEEKDAY = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
_EXPLICIT = [
    re.compile(r"((?:19|20)\d{2})\s*[.년]\s*(\d{1,2})\s*[.월]\s*(\d{1,2})"),
    re.compile(r"[‘'’]\s*(\d{2})\s*\.\s*(\d{1,2})\s*\.\s*(\d{1,2})"),
]
_MD_WEEKDAY = re.compile(r"(\d{1,2})\s*(?:월|\.|/)\s*(\d{1,2})\s*일?\s*\(\s*([월화수목금토일])\s*\)")


def _era(text: str) -> tuple[pd.Timestamp, pd.Timestamp] | None:
    for pat, lo, hi in MINISTRY_ERAS:
        if re.search(pat, text):
            return pd.Timestamp(lo), pd.Timestamp(hi)
    return None


def _ok(d: str | None, era) -> bool:
    if not d:
        return False
    t = pd.Timestamp(d)
    lo, hi = era if era else (LEGACY_LO, LEGACY_HI)
    return max(lo, LEGACY_LO) - pd.Timedelta(days=31) <= t <= min(hi, LEGACY_HI) + pd.Timedelta(days=31)


def _weekday_date(text: str, era) -> str | None:
    """Unique year in the ministry era for which month/day falls on the stated weekday."""
    if not era:
        return None
    for m in _MD_WEEKDAY.finditer(text):
        mo, dd, wd = int(m.group(1)), int(m.group(2)), _WEEKDAY[m.group(3)]
        hits = []
        for y in range(era[0].year, era[1].year + 1):
            try:
                t = pd.Timestamp(year=y, month=mo, day=dd)
            except ValueError:
                continue
            if t.weekday() == wd and era[0] - pd.Timedelta(days=31) <= t <= era[1] + pd.Timedelta(days=31):
                hits.append(t)
        if len(hits) == 1:
            return hits[0].strftime("%Y-%m-%d")
    return None


def repair_motie_dates(docs: pd.DataFrame, logger) -> pd.DataFrame:
    """Flag the motir.go.kr migration batch and recover original dates where evidence exists.

    Methods, in order of reliability (recorded in `date_recovery`):
      body_release_date     release-date header ("보도일 : 1999. 1. 26.", "...일(목) 조간")
      korea_kr_exact_title  same title in the dated korea.kr inventory (2008-2014)
      body_explicit_date    first full date in the opening text (event date ~ release date)
      body_weekday_era      "3.4(목)" + ministry name -> the unique matching year in that era
      title_year_only       a year in the title (year only; date stays empty, date_reliable False)
    Every recovered date must fall in 1990-01-01..2016-12-08 and inside the ministry era if named.
    """
    docs["date_site"] = docs["date"]
    docs["date_reliable"] = True
    docs["date_recovery"] = ""
    mig = (docs["source_id"] == "kr_motie") & (docs["date"] == MOTIE_MIGRATION_DATE)
    docs.loc[mig, "date_reliable"] = False
    kr = docs[docs["source_id"] == "kr_policy_briefing"]
    kr_norm = dict(zip(kr["title"].map(lambda t: re.sub(r"\W+", "", str(t))), kr["date"], strict=False))
    n = dict.fromkeys(
        [
            "body_release_date",
            "korea_kr_exact_title",
            "body_explicit_date",
            "body_weekday_era",
            "title_year_only",
        ],
        0,
    )
    for i in docs.index[mig]:
        title = str(docs.at[i, "title"])
        head = docs.at[i, "text"][:800]
        era = _era(title + " " + head)
        date, method = None, ""
        for rx in _RELEASE_DATE:
            m = rx.search(head)
            if m and _ok(d := _ymd(*m.groups()), era):
                date, method = d, "body_release_date"
                break
        if date is None and _ok(d := kr_norm.get(re.sub(r"\W+", "", title)), era):
            date, method = d, "korea_kr_exact_title"
        if date is None:
            for rx in _EXPLICIT:
                m = rx.search(head)
                if m and _ok(d := _ymd(*m.groups()), era):
                    date, method = d, "body_explicit_date"
                    break
        if date is None and (d := _weekday_date(title + " " + head, era)):
            date, method = d, "body_weekday_era"
        if date:
            docs.at[i, "date"], docs.at[i, "date_reliable"], docs.at[i, "date_recovery"] = date, True, method
            n[method] += 1
            continue
        m = re.search(r"((?:19|20)\d{2})\s*년", title)
        if (
            m
            and LEGACY_LO.year <= int(m.group(1)) <= LEGACY_HI.year
            and (not era or era[0].year - 1 <= int(m.group(1)) <= era[1].year)
        ):
            docs.at[i, "date_recovery"] = "title_year_only"
            docs.at[i, "year_recovered"] = int(m.group(1))
            n["title_year_only"] += 1
    unresolved = mig & ~docs["date_reliable"]
    docs.loc[unresolved, "date"] = None
    logger.info(
        "MOTIE migration batch: %d docs dated %s; recovered %s; still without a full date %d",
        int(mig.sum()),
        MOTIE_MIGRATION_DATE,
        n,
        int(unresolved.sum()),
    )
    return docs


# --------------------------------------------------------------------------- assembly
def _motie_list(html: str) -> list[tuple[str, dict]]:
    out = []
    for tr in BeautifulSoup(html, "lxml").select("table tbody tr"):
        a = tr.select_one('a[href*="/view"]')
        if a is None:
            continue
        seq = re.search(r"/(\d+)/view", a["href"]).group(1)
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        date = next((t for t in tds if re.fullmatch(r"\d{4}-\d{2}-\d{2}", t)), "")
        out.append((seq, {"title": a.get_text(" ", strip=True), "date": date}))
    return out


def _pa_list(html: str) -> list[tuple[str, dict]]:
    out = []
    for tr in BeautifulSoup(html, "lxml").select("table tbody tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        a = tr.select_one("a[href*='artid=']")
        if a and len(tds) >= 6:
            m = re.search(r"catid=(\w+)&artid=(\d+)", a["href"])
            out.append(
                (
                    m.group(2),
                    {
                        "president": tds[1],
                        "form": tds[2],
                        "type": tds[3],
                        "title": tds[4],
                        "date": tds[5].replace(".", "-"),
                        "catid": m.group(1),
                    },
                )
            )
    return out


def _pa_view(html: str) -> tuple[str, str, str]:
    b = BeautifulSoup(html, "lxml")
    cells = {
        th.get_text(strip=True): th.find_next_sibling("td").get_text(" ", strip=True)
        for th in b.select("table.board-view th")
        if th.find_next_sibling("td")
    }
    return html_block_text(b.select_one("td.content")), cells.get("연설장소", ""), cells.get("출처", "")[:200]


def _office_view(html: str) -> str:
    return html_block_text(BeautifulSoup(html, "lxml").select_one(".view_txt"))  # president.go.kr body


PARSERS = {
    "mofa_list": parse_list_page,
    "mofa_view": parse_view_page,
    "motie_list": _motie_list,
    "motie_view": parse_motie_view,
    "pa_list": _pa_list,
    "pa_view": _pa_view,
    "office_view": _office_view,
}


def main(args, logger) -> None:
    from srl.text.entities import default_matcher

    FOLDER_ISO.update(_alias_folder_map())

    docs = pd.concat(
        [mofa(logger), motie(logger), policy_briefing(logger), presidential(logger)], ignore_index=True
    )
    docs["date"] = pd.to_datetime(docs["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    docs["text"] = docs["text"].fillna("")
    docs = repair_motie_dates(docs, logger)
    docs["year"] = pd.to_numeric(docs["date"].str[:4], errors="coerce").astype("Int64")
    if "year_recovered" in docs:
        docs["year"] = docs["year"].fillna(docs["year_recovered"].astype("Int64"))
    docs["administration"] = [
        p if isinstance(p, str) and p else administration(d if isinstance(d, str) else "")
        for p, d in zip(docs.get("president", pd.Series([""] * len(docs))), docs["date"], strict=True)
    ]
    docs["text"] = docs["text"].fillna("")
    docs["n_chars"] = docs["text"].str.len()
    docs["text_status"] = docs["n_chars"].gt(0).map({True: "full_text", False: "metadata_only"})
    # duplicates: identical normalized title+date across sources (syndicated copies)
    norm = docs["title"].fillna("").map(lambda t: re.sub(r"\W+", "", str(t)).lower())  # Python re: Unicode \W
    docs["dedup_key"] = [
        hashlib.sha1(f"{t}|{d}".encode()).hexdigest()[:16] for t, d in zip(norm, docs["date"], strict=True)
    ]
    docs["is_cross_source_duplicate"] = docs.duplicated("dedup_key", keep="first") & docs["dedup_key"].ne("")
    # local mention counts (candidate; validate with KWIC before use)
    matcher = default_matcher()
    surf = Counter()
    counts = []
    for text, title in zip(docs["text"], docs["title"].fillna(""), strict=True):
        ms = matcher.find(f"{title}\n{text}")
        c = Counter(m.entity_id for m in ms)
        surf.update((m.entity_id, m.surface) for m in ms)
        counts.append(c)
    for iso in PARTNERS + ["ASEAN"]:
        docs[f"mentions_{iso}"] = [c.get(iso, 0) for c in counts]
    docs["partners_mentioned"] = ["|".join(i for i in PARTNERS + ["ASEAN"] if c.get(i)) for c in counts]

    meta = docs.drop(columns=["text"])
    out = get_path("data.interim") / "prelim"
    write_table(meta, out / "gov_documents_korea.csv")
    write_table(
        docs[["doc_id", "language", "text"]][docs["n_chars"] > 0],
        get_path("data.interim") / "text" / "gov_documents_korea_text.parquet",
    )
    diag = get_path("outputs.diagnostics", mkdir=True)
    cov = (
        docs.groupby(["source_id", "doc_type", "language", "year"])
        .agg(
            n_documents=("doc_id", "size"),
            n_full_text=("text_status", lambda s: (s == "full_text").sum()),
            n_any_partner_mention=("partners_mentioned", lambda s: (s != "").sum()),
            **{
                f"n_{i}": (f"mentions_{i}", lambda s: (s > 0).sum())
                for i in [
                    "CHN",
                    "VNM",
                    "IDN",
                    "THA",
                    "SGP",
                    "KHM",
                    "LAO",
                    "MYS",
                    "PHL",
                    "MMR",
                    "BRN",
                    "TLS",
                    "ASEAN",
                ]
            },
        )
        .reset_index()
    )
    write_table(cov, diag / "gov_corpus_coverage.csv")
    write_table(
        pd.DataFrame([{"entity": e, "surface": s, "n": n} for (e, s), n in surf.most_common()]),
        diag / "gov_mention_surface_counts.csv",
    )
    dup_ids = docs.duplicated("doc_id").sum()
    logger.info(
        "TOTAL %d documents (%d full text); duplicate doc_id %d; cross-source duplicates %d",
        len(docs),
        (docs["text_status"] == "full_text").sum(),
        dup_ids,
        docs["is_cross_source_duplicate"].sum(),
    )


if __name__ == "__main__":
    run_step("build_gov_documents", main, argparse.ArgumentParser(description=__doc__))
