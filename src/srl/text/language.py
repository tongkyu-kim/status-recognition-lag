"""Script-based language identification for a Korean/English corpus.

A deterministic heuristic is sufficient here because the corpus is (by design) Korean or English
official text. Documents that are neither should surface as ``other``/``unknown`` for review
rather than being silently classified. A statistical language identifier can be swapped in later.
"""

from __future__ import annotations

import re

_HANGUL = re.compile(r"[가-힣ᄀ-ᇿ㄰-㆏]")
_LATIN = re.compile(r"[A-Za-z]")
_OTHER_LETTER = re.compile(r"[^\W\d_]")


def detect_language(text: str, *, threshold: float = 0.6, min_letters: int = 10) -> str:
    """Return ``"ko"``, ``"en"``, ``"mixed"``, ``"other"`` or ``"unknown"``.

    Classifies by the share of Hangul vs. Latin letters among all letters. ``threshold`` is the
    share required for a single-language label; texts with fewer than ``min_letters`` letters
    are ``unknown``.
    """
    text = text or ""
    n_letters = len(_OTHER_LETTER.findall(text))
    if n_letters < min_letters:
        return "unknown"
    hangul = len(_HANGUL.findall(text)) / n_letters
    latin = len(_LATIN.findall(text)) / n_letters
    if hangul >= threshold:
        return "ko"
    if latin >= threshold:
        return "en"
    if hangul + latin >= threshold:
        return "mixed"
    return "other"
