"""Supervised recognition-frame classifier (planned).

Intended design: train on the human-coded sample (docs/coding_protocol.md) with a held-out test
split fixed by the project seed; report per-class precision/recall/F1 and compare with the
dictionary baseline on the same test set. Guard against leakage: split by document (not sentence)
and, for temporal validity, check performance across periods.
"""

from __future__ import annotations

import pandas as pd


def train(coded: pd.DataFrame, **kwargs):
    raise NotImplementedError("Supervised classifier awaits human-coded training data")


def predict(model, sentences: pd.DataFrame) -> pd.DataFrame:
    raise NotImplementedError("Supervised classifier awaits human-coded training data")
