"""Dictionary-based recognition-frame scoring (baseline).

Frames and seed terms come from ``config/recognition_frames.yaml`` (unvalidated candidates).
Each sentence receives counts per frame (``frame_vertical``, ``frame_horizontal``,
``frame_competitive``) and per subframe (``sub_<frame>__<subframe>``). Overlapping term matches
resolve to the longest span, so "comprehensive strategic partnership" counts once.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import pandas as pd

from srl.text.patterns import find_spans, resolve_overlaps, term_to_regex
from srl.utils.config import load_yaml

DEFAULT_PATH = "config/recognition_frames.yaml"

CompiledFrames = list[tuple[str, str, int, re.Pattern[str]]]


def load_frame_dictionary(path: str = DEFAULT_PATH) -> dict[str, Any]:
    cfg = load_yaml(path)
    if "frames" not in cfg:
        raise ValueError(f"{path}: missing 'frames'")
    return cfg


def compile_frames(cfg: dict[str, Any]) -> CompiledFrames:
    """Compile to ``(label="<frame>__<subframe>", kind=<frame>, priority, pattern)`` tuples."""
    compiled = []
    for frame, frame_spec in cfg["frames"].items():
        for subframe, terms in (frame_spec.get("subframes") or {}).items():
            for lang in ("en", "ko"):
                for term in terms.get(lang) or []:
                    compiled.append((f"{frame}__{subframe}", frame, 1,
                                     re.compile(term_to_regex(term), re.IGNORECASE)))
    return compiled


def frame_names(cfg: dict[str, Any]) -> list[str]:
    return list(cfg["frames"])


def score_text(text: str, compiled: CompiledFrames) -> Counter[str]:
    """Count frame and subframe matches in one text."""
    counts: Counter[str] = Counter()
    for span in resolve_overlaps(find_spans(text or "", compiled)):
        counts[f"frame_{span.kind}"] += 1
        counts[f"sub_{span.label}"] += 1
    return counts


def score_sentences(sentences: pd.DataFrame, *, text_col: str = "text",
                    cfg: dict[str, Any] | None = None) -> pd.DataFrame:
    """Return ``sentences`` with frame and subframe count columns (zeros where absent)."""
    cfg = cfg or load_frame_dictionary()
    compiled = compile_frames(cfg)
    scores = pd.DataFrame([score_text(t, compiled) for t in sentences[text_col]],
                          index=sentences.index)
    frame_cols = [f"frame_{f}" for f in frame_names(cfg)]
    scores = scores.reindex(columns=sorted(set(scores.columns) | set(frame_cols)), fill_value=0)
    return pd.concat([sentences, scores.fillna(0).astype(int)], axis=1)
