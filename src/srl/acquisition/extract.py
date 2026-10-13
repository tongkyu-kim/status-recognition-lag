"""Plain-text extraction from government attachments: HWP 5.0 (OLE), HWPX (OWPML zip), DOCX, PDF.

HWP 5.0: the ``BodyText/SectionN`` streams hold a sequence of records; if the FileHeader
compression bit is set, each stream is raw-deflate compressed. Paragraph text lives in
HWPTAG_PARA_TEXT records (tag id 67) as UTF-16LE with inline control characters, which are
skipped (extended/inline controls occupy 8 UTF-16 units). Tables' cell text is ordinary paragraph
text and is kept. Distribution-protected ("배포용") documents are encrypted and yield "".
"""

from __future__ import annotations

import io
import re
import struct
import zipfile
import zlib
from pathlib import Path

HWPTAG_PARA_TEXT = 67
_CTRL_EXT = {1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23}  # 8-unit controls
_CTRL_CHAR = {0, 10, 13, 24, 25, 26, 27, 28, 29, 30, 31}  # 1-unit controls (10/13 = line breaks)


def _para_text(data: bytes) -> str:
    units = struct.unpack(f"<{len(data) // 2}H", data[: len(data) // 2 * 2])
    out, i = [], 0
    while i < len(units):
        u = units[i]
        if u < 32:
            if u in _CTRL_EXT:
                i += 8
                continue
            if u in (10, 13):
                out.append("\n")
            elif u == 9:
                out.append("\t")
                i += 8
                continue
            i += 1
            continue
        out.append(chr(u))
        i += 1
    # pair valid surrogates, replace lone ones (they cannot be stored as UTF-8 / Arrow strings)
    return "".join(out).encode("utf-16-le", "surrogatepass").decode("utf-16-le", "replace")


def hwp5_text(path: str | Path) -> str:
    import olefile

    with olefile.OleFileIO(str(path)) as ole:
        header = ole.openstream("FileHeader").read()
        flags = struct.unpack("<I", header[36:40])[0]
        compressed, encrypted = bool(flags & 1), bool(flags & 2)
        if encrypted:
            return ""
        sections = sorted(
            (e for e in ole.listdir() if e[0] == "BodyText"), key=lambda e: int(re.sub(r"\D", "", e[1]) or 0)
        )
        paras = []
        for entry in sections:
            raw = ole.openstream(entry).read()
            if compressed:
                raw = zlib.decompress(raw, -15)
            pos = 0
            while pos + 4 <= len(raw):
                head = struct.unpack("<I", raw[pos : pos + 4])[0]
                tag, size = head & 0x3FF, (head >> 20) & 0xFFF
                pos += 4
                if size == 0xFFF:
                    size = struct.unpack("<I", raw[pos : pos + 4])[0]
                    pos += 4
                if tag == HWPTAG_PARA_TEXT:
                    paras.append(_para_text(raw[pos : pos + size]))
                pos += size
    return "\n".join(p.strip() for p in paras if p.strip())


def hwpx_text(path: str | Path) -> str:
    with zipfile.ZipFile(path) as z:
        names = sorted(n for n in z.namelist() if re.match(r"Contents/section\d+\.xml$", n))
        parts = []
        for n in names:
            xml = z.read(n).decode("utf-8", errors="replace")
            xml = re.sub(r"</hp:p>", "\n", xml)
            parts.append(re.sub(r"<[^>]+>", "", xml))
    return re.sub(r"\n\s*\n+", "\n", "\n".join(parts)).strip()


def docx_text(path: str | Path) -> str:
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml").decode("utf-8", errors="replace")
    xml = re.sub(r"</w:p>", "\n", xml)
    xml = re.sub(r"<w:tab/>", "\t", xml)
    return re.sub(r"\n\s*\n+", "\n", re.sub(r"<[^>]+>", "", xml)).strip()


def pdf_text(path: str | Path) -> str:
    import pypdf

    reader = pypdf.PdfReader(str(path))
    text = "\n".join((p.extract_text() or "") for p in reader.pages).strip()
    if _hangul(text) < 0.3 * max(len(text), 1) or len(text) < 500:
        # pypdf misses Korean text set in fonts without a usable ToUnicode map; pdfminer often
        # recovers it. Keep whichever yields more Hangul. Image-only scans still need OCR.
        try:
            from pdfminer.high_level import extract_text

            alt = extract_text(str(path)).strip()
            if _hangul(alt) > _hangul(text):
                text = alt
        except Exception:  # noqa: BLE001 - pdfminer optional / malformed PDFs
            pass
    return text


def _hangul(text: str) -> int:
    return sum("가" <= c <= "힣" for c in text)


_BLOCK_TAGS = ["p", "div", "li", "tr", "table", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"]


def html_block_text(element) -> str:
    """Text of a BeautifulSoup element with line breaks only at block boundaries.

    ``get_text("\\n")`` breaks at every inline tag, which fragments tokens such as "한-인니".
    """
    if element is None:
        return ""
    el = element  # mutated in place (callers do not reuse it); copying large trees was very slow
    for br in el.find_all("br"):
        br.replace_with("\n")
    for tag in el.find_all(_BLOCK_TAGS):
        tag.insert_after("\n")
    text = el.get_text("")
    lines = (re.sub(r"[ \t\u00a0]+", " ", ln).strip() for ln in text.splitlines())
    return "\n".join(ln for ln in lines if ln)


def sniff_and_extract(path: str | Path) -> tuple[str, str]:
    """Return (format, text) based on file magic, not extension."""
    head = Path(path).read_bytes()[:8]
    try:
        if head.startswith(b"\xd0\xcf\x11\xe0"):
            return "hwp5", hwp5_text(path)
        if head.startswith(b"PK"):
            with zipfile.ZipFile(path) as z:
                names = z.namelist()
                if any(n.startswith("Contents/section") for n in names):
                    return "hwpx", hwpx_text(path)
                if "word/document.xml" in names:
                    return "docx", docx_text(path)
            return "zip", ""
        if head.startswith(b"%PDF"):
            return "pdf", pdf_text(path)
    except Exception as exc:  # corrupt / protected files: record and continue
        return "error", f"__EXTRACTION_ERROR__ {type(exc).__name__}: {exc}"[:300]
    return "unknown", ""


def extract_bytes(data: bytes, suffix: str = ".bin") -> tuple[str, str]:
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as fh:
        fh.write(data)
        name = fh.name
    try:
        return sniff_and_extract(name)
    finally:
        Path(name).unlink(missing_ok=True)


__all__ = ["hwp5_text", "hwpx_text", "pdf_text", "sniff_and_extract", "extract_bytes", "io"]
