"""Attribute sentence-level frame scores to partners and aggregate over time.

Attribution rule (baseline): a scored sentence is attributed to every country it mentions.
Alternatives to evaluate against human coding: restrict to single-country sentences; attribute
by proximity of frame term to entity mention; use a +/- 1 sentence context window.
"""

from __future__ import annotations

import pandas as pd

from srl.text.aggregation import add_period
from srl.utils.validation import require_columns


def attribute_frames(scored: pd.DataFrame, mentions: pd.DataFrame, *,
                     entity_types: tuple[str, ...] = ("country",),
                     exclude: tuple[str, ...] = ("KOR",)) -> pd.DataFrame:
    """Join sentence frame counts to distinct (sentence, entity) pairs.

    Adds ``multi_entity`` = sentence mentions more than one eligible entity.
    """
    require_columns(scored, ["sentence_id", "date"], "scored sentences")
    require_columns(mentions, ["sentence_id", "entity_id", "entity_type"], "mentions")
    pairs = (mentions[mentions["entity_type"].isin(entity_types) & ~mentions["entity_id"].isin(exclude)]
             [["sentence_id", "entity_id"]].drop_duplicates())
    pairs["multi_entity"] = pairs.groupby("sentence_id")["entity_id"].transform("size") > 1
    return pairs.merge(scored, on="sentence_id", how="left", validate="many_to_one")


def aggregate_frames(attributed: pd.DataFrame, *, freq: str = "Y",
                     frame_prefix: str = "frame_") -> pd.DataFrame:
    """Sum frame counts per entity and period; include ``n_sentences`` and ``n_framed``."""
    frame_cols = [c for c in attributed.columns if c.startswith(frame_prefix)]
    df = add_period(attributed, freq=freq)
    df["framed"] = (df[frame_cols].sum(axis=1) > 0).astype(int)
    out = df.groupby(["entity_id", "period"], as_index=False).agg(
        n_sentences=("sentence_id", "nunique"), n_framed=("framed", "sum"),
        **{c: (c, "sum") for c in frame_cols})
    return out
