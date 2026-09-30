"""Sentence segmentation (rule-based baseline).

Splits on sentence-final punctuation followed by whitespace and on paragraph breaks, while
protecting common abbreviations (``U.S.``, ``Rep.``, ``Dr.``) and decimals. This is a transparent
baseline; a dedicated Korean segmenter can replace it later (log the change in docs/decisions.md
and re-run validation, since sentence boundaries change sentence-level counts).
"""

from __future__ import annotations

import re

_ABBREVIATIONS = ("U.S.", "U.K.", "U.N.", "Rep.", "Dem.", "Mr.", "Ms.", "Dr.", "No.", "Vol.",
                  "e.g.", "i.e.", "etc.", "vs.", "Jan.", "Feb.", "Aug.", "Sept.", "Oct.", "Nov.",
                  "Dec.")
_PLACEHOLDER = "\u0000"
_BOUNDARY = re.compile(r"(?<=[.!?。])[\"'”’)\]]*\s+|\n{2,}")


def split_sentences(text: str, *, min_chars: int = 1) -> list[str]:
    """Split ``text`` into sentences; drops fragments shorter than ``min_chars``."""
    if not text:
        return []
    protected = text
    for abbr in _ABBREVIATIONS:
        protected = protected.replace(abbr, abbr.replace(".", _PLACEHOLDER))
    protected = re.sub(r"(?<=\d)\.(?=\d)", _PLACEHOLDER, protected)
    pieces = _BOUNDARY.split(protected)
    sentences = [p.replace(_PLACEHOLDER, ".").strip() for p in pieces]
    return [s for s in sentences if len(s) >= min_chars]
