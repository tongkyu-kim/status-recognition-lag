"""Duplicate and spam flags for comments (flags only - nothing is deleted).

- ``dup_within_video``: same normalized text already posted earlier under the same video
- ``dup_same_author_cross_video``: same hashed author posted the same normalized text on >1 video
  (copy-paste campaigns / bots)
- ``too_short``: fewer than ``min_chars`` non-space characters after normalization
Normalization: NFKC, lower-case, strip URLs/mentions/whitespace/punctuation runs.
"""

from __future__ import annotations

import re
import unicodedata

import pandas as pd

_URL = re.compile(r"https?://\S+|www\.\S+")
_MENTION = re.compile(r"@[\w\-.]+")
_NONWORD = re.compile(r"[\W_]+", re.UNICODE)


def normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text or "").lower()
    t = _URL.sub(" ", t)
    t = _MENTION.sub(" ", t)
    return _NONWORD.sub("", t)


def flag_duplicates(comments: pd.DataFrame, min_chars: int = 2) -> pd.DataFrame:
    if comments.empty:
        return comments.assign(
            dup_within_video=pd.Series(dtype=bool),
            dup_same_author_cross_video=pd.Series(dtype=bool),
            too_short=pd.Series(dtype=bool),
        )
    df = comments.sort_values(["video_id", "published_at"]).copy()
    df["text_norm"] = df["text"].map(normalize_text)
    df["too_short"] = df["text_norm"].str.len() < min_chars
    df["dup_within_video"] = df.duplicated(["video_id", "text_norm"], keep="first") & ~df["too_short"]
    by_author = df.dropna(subset=["author_hash"]).groupby(["author_hash", "text_norm"])["video_id"].nunique()
    spam_keys = set(by_author[by_author > 1].index)
    df["dup_same_author_cross_video"] = [
        (a, t) in spam_keys for a, t in zip(df["author_hash"], df["text_norm"], strict=True)
    ]
    return df.drop(columns="text_norm")


def duplicate_rate(comments: pd.DataFrame) -> float:
    if comments.empty:
        return float("nan")
    return float((comments["dup_within_video"] | comments["dup_same_author_cross_video"]).mean())
