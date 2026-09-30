"""Text cleaning applied to government documents before segmentation."""

from __future__ import annotations

import re
import unicodedata

_ZERO_WIDTH = re.compile(r"[​‌‍﻿]")
_HORIZONTAL_WS = re.compile(r"[ \t 　]+")
_MANY_NEWLINES = re.compile(r"\n{3,}")


def normalize_text(text: str) -> str:
    """NFKC-normalize, remove zero-width characters, and normalize whitespace.

    Keeps paragraph breaks (double newlines), which segmentation may use.
    """
    text = unicodedata.normalize("NFKC", text or "")
    text = _ZERO_WIDTH.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    text = _HORIZONTAL_WS.sub(" ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return _MANY_NEWLINES.sub("\n\n", text).strip()


def strip_boilerplate(text: str, source_id: str) -> str:
    """Remove source-specific boilerplate (headers, contact blocks, footers).

    TODO: define per-source rules after inspecting real documents; record them in
    docs/decisions.md. Until then this is an identity function by design.
    """
    return text
