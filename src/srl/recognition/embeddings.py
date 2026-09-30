"""Embedding-based recognition measurement (planned).

Intended design: embed sentences mentioning a partner with a multilingual sentence encoder and
project them onto a vertical<->horizontal axis defined by anchor sentences (or train a light
classifier on top of embeddings). Anchors must be chosen ex ante and validated against the
human-coded sample. Adds a model dependency; pin model name and version in config when adopted.
"""

from __future__ import annotations

import pandas as pd


def score_sentences(sentences: pd.DataFrame, **kwargs) -> pd.DataFrame:
    raise NotImplementedError("Embedding-based scoring not implemented; see module docstring")
