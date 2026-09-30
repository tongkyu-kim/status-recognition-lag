"""Compile alias/term lists into regular expressions and resolve overlapping matches.

Rules shared by entity matching and dictionary-based frame scoring:

- Latin-script terms: case-insensitive, whole-word (``(?<!\\w)term(?!\\w)``); internal whitespace
  matches any whitespace run; apostrophes match ``'`` or ``’``; hyphens match common dash variants.
- Short all-caps acronyms (<= 5 letters, e.g., ``US``, ``PRC``, ``ODA``): case-sensitive, so the
  pronoun "us" is not read as the United States.
- Hangul terms: plain substring match, because Korean particles attach directly to nouns
  (``베트남과``, ``중국은``). False positives are handled by shields and validated patterns.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

_HANGUL = re.compile(r"[ᄀ-ᇿ㄰-㆏가-힣]")
_APOSTROPHES = "['’]"
_HYPHENS = "[-‐–]"


def has_hangul(text: str) -> bool:
    return bool(_HANGUL.search(text))


def is_acronym(term: str) -> bool:
    letters = term.replace(".", "")
    return letters.isascii() and letters.isalpha() and letters.isupper() and len(letters) <= 5


def term_to_regex(term: str) -> str:
    """Return a regex string for ``term`` following the module-level rules."""
    parts = []
    for token in term.split():
        escaped = re.escape(token).replace("'", _APOSTROPHES).replace(r"\-", _HYPHENS)
        parts.append(escaped)
    body = r"\s+".join(parts)
    if has_hangul(term):
        return body
    if is_acronym(term):
        body = f"(?-i:{body})"
    return rf"(?<!\w){body}(?!\w)"


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    label: str
    kind: str
    priority: int = 1

    @property
    def length(self) -> int:
        return self.end - self.start


def find_spans(text: str, patterns: Iterable[tuple[str, str, int, re.Pattern[str]]]) -> list[Span]:
    """Find all (possibly overlapping) matches of labelled patterns.

    ``patterns`` yields ``(label, kind, priority, compiled_pattern)``.
    """
    spans = []
    for label, kind, priority, pattern in patterns:
        for m in pattern.finditer(text):
            if m.end() > m.start():
                spans.append(Span(m.start(), m.end(), label, kind, priority))
    return spans


def resolve_overlaps(spans: Iterable[Span]) -> list[Span]:
    """Greedy leftmost-longest selection of non-overlapping spans.

    Sorted by start, then longer span first, then lower ``priority`` value first (shields use 0),
    then label (for determinism).
    """
    selected: list[Span] = []
    last_end = -1
    for span in sorted(spans, key=lambda s: (s.start, -s.length, s.priority, s.label)):
        if span.start >= last_end:
            selected.append(span)
            last_end = span.end
    return selected
