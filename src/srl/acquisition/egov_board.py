"""Harvester for Korean e-government "brd" bulletin boards (list.do / view.do?seq=).

Used for www.mofa.go.kr (and any site built on the same eGovFrame board template). Three phases:

1. ``harvest_list``   - every list page of a board (complete document inventory = attention
   denominators). Raw list HTML is saved page by page.
2. ``harvest_search`` - the board's own full-content search (``srchTp=1``) for each country alias.
   Hits give document-level alias occurrence without downloading every document.
3. ``fetch_views``    - document pages (title, date, department, body, attachment list).

Parsing helpers (``parse_list_page`` / ``parse_view_page``) are pure functions of saved HTML, so
metadata can be rebuilt from the raw layer at any time.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Iterable
from dataclasses import dataclass
from urllib.parse import quote

from bs4 import BeautifulSoup

from srl.acquisition.extract import html_block_text
from srl.acquisition.fetch import PoliteSession, raw_dir, raw_exists, save_raw

logger = logging.getLogger(__name__)

_DATE = re.compile(r"(\d{4})[-.](\d{2})[-.](\d{2})")
_SEQ = re.compile(r"seq=(\d+)|f_view\('(\d+)'\)")


def alias_slug(term: str, max_len: int = 25) -> str:
    """Folder name for a search alias. Names longer than ``max_len`` are shortened with a hash
    (Windows MAX_PATH); shorter names are unchanged so earlier retrievals stay valid."""
    import hashlib

    s = re.sub(r"[^0-9A-Za-z가-힣]+", "_", term).strip("_") or "x"
    if len(s) > max_len:
        s = s[: max_len - 7] + "_" + hashlib.sha1(term.encode("utf-8")).hexdigest()[:6]
    return s


@dataclass(frozen=True)
class Board:
    site: str  # e.g. "https://www.mofa.go.kr"
    section: str  # e.g. "www" (Korean) or "eng"
    board_id: str  # e.g. "m_4080"
    label: str  # human-readable board name
    doc_type: str  # press_release | briefing | speech | white_paper | ...
    language: str  # ko | en

    @property
    def key(self) -> str:
        return f"{self.section}_{self.board_id}"

    def list_url(self, page: int, pitem: int = 50, word: str = "", tp: str = "") -> str:
        url = f"{self.site}/{self.section}/brd/{self.board_id}/list.do?page={page}&pitem={pitem}"
        if word:
            url += f"&srchTp={tp}&srchWord={quote(word)}"
        return url

    def view_url(self, seq: str) -> str:
        return f"{self.site}/{self.section}/brd/{self.board_id}/view.do?seq={seq}"


def parse_list_page(html: str) -> list[dict]:
    """Rows of a board list page: seq, title, department, date, has_attachment, row_number."""
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for tr in soup.select("table tbody tr"):
        link = tr.select_one('a[href*="view.do?seq="], a[onclick*="f_view("]')
        if link is None:
            continue
        m = _SEQ.search((link.get("href") or "") + " " + (link.get("onclick") or ""))
        seq = m.group(1) or m.group(2)
        for span in link.select("span.state"):
            span.decompose()
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        date = next(
            (f"{m.group(1)}-{m.group(2)}-{m.group(3)}" for c in reversed(cells) if (m := _DATE.search(c))), ""
        )
        number = cells[0] if cells and cells[0].isdigit() else ""
        dept = ""
        if len(cells) >= 4:  # number | title | (file) | dept | date
            dept = cells[-2] if not _DATE.search(cells[-2]) else ""
        rows.append(
            {
                "seq": seq,
                "title": link.get_text(" ", strip=True),
                "department": dept,
                "date": date,
                "has_attachment": bool(tr.select_one(".file, img[alt*='첨부']")),
                "row_number": number,
            }
        )
    return rows


def total_from_list(html: str) -> int:
    rows = parse_list_page(html)
    return int(rows[0]["row_number"]) if rows and rows[0]["row_number"] else len(rows)


def parse_view_page(html: str) -> dict:
    """Title, department, date, body text and attachments of a view.do page."""
    soup = BeautifulSoup(html, "lxml")
    head = soup.select_one(".bo_head")
    body = soup.select_one(".bo_con")
    title = ""
    if head is not None:
        h = head.select_one("h2, h3, h4, .tit, strong")
        title = h.get_text(" ", strip=True) if h else head.get_text(" ", strip=True)
    head_text = head.get_text(" ", strip=True) if head else ""
    m = _DATE.search(head_text)
    dept = re.search(r"부서명\s*(.+?)\s*(작성일|$)", head_text)
    files = []
    fbox = soup.select_one(".bo_file")
    if fbox is not None:
        files = [
            {"name": a.get_text(strip=True), "href": a.get("href")}
            for a in fbox.select("a")
            if "down.do" in (a.get("href") or "")
        ]
    kogl = soup.select_one(".kogl-select-wrap")
    return {
        "title": title,
        "date": f"{m.group(1)}-{m.group(2)}-{m.group(3)}" if m else "",
        "department": dept.group(1).strip() if dept else "",
        "text": html_block_text(body),
        "attachments": files,
        "kogl": " ".join(i.get("alt", "") for i in kogl.select("img")) if kogl else "",
    }


class BoardHarvester:
    def __init__(self, source_id: str, sess: PoliteSession):
        self.source_id = source_id
        self.sess = sess

    def _get_page(self, relname: str, url: str) -> str | None:
        if raw_exists(self.source_id, relname):
            return (raw_dir(self.source_id) / relname).read_text(encoding="utf-8")
        resp = self.sess.get(url)
        if resp.status_code != 200:
            logger.error("%s -> HTTP %s", url, resp.status_code)
            return None
        resp.encoding = "utf-8"
        save_raw(self.source_id, relname, resp.content, url=url, http_status=200)
        return resp.content.decode("utf-8", errors="replace")

    def harvest_list(self, board: Board, pitem: int = 50, max_pages: int | None = None) -> list[dict]:
        first = self._get_page(f"lists/{board.key}/p0001.html", board.list_url(1, pitem))
        if first is None:
            return []
        total = total_from_list(first)
        pages = -(-total // pitem)
        if max_pages:
            pages = min(pages, max_pages)
        logger.info("%s (%s): %d documents, %d pages", board.key, board.label, total, pages)
        rows = parse_list_page(first)
        for p in range(2, pages + 1):
            html = self._get_page(f"lists/{board.key}/p{p:04d}.html", board.list_url(p, pitem))
            if html:
                rows += parse_list_page(html)
        return rows

    def harvest_search(self, board: Board, word: str, slug: str, tp: str = "1", pitem: int = 50) -> list[str]:
        """Return seqs of documents whose content (tp=1) matches ``word``."""
        rel = f"search/{board.key}/{slug}/p0001.html"
        first = self._get_page(rel, board.list_url(1, pitem, word, tp))
        if first is None:
            return []
        total = total_from_list(first)
        seqs = [r["seq"] for r in parse_list_page(first)]
        for p in range(2, -(-total // pitem) + 1):
            html = self._get_page(
                f"search/{board.key}/{slug}/p{p:04d}.html", board.list_url(p, pitem, word, tp)
            )
            if html:
                seqs += [r["seq"] for r in parse_list_page(html)]
        logger.info("%s search %r: %d hits", board.key, word, len(seqs))
        return seqs

    def fetch_views(self, board: Board, seqs: Iterable[str]) -> int:
        n = 0
        for seq in seqs:
            rel = f"views/{board.key}/{seq}.html"
            if raw_exists(self.source_id, rel):
                continue
            if self._get_page(rel, board.view_url(seq)) is not None:
                n += 1
                if n % 250 == 0:
                    logger.info("%s: %d views fetched", board.key, n)
        return n
