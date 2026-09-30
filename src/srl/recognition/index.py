"""Recognition indices from horizontal (H) and vertical (V) frame counts.

All indices are oriented so that HIGHER = more horizontal (peer-like) recognition.

- ``share``:   H / (H + V)                        in [0, 1]; undefined when H + V = 0
- ``balance``: (H - V) / (H + V)                  in [-1, 1]; undefined when H + V = 0
- ``logit``:   ln((H + s) / (V + s))              empirical logit (Lowe, Benoit, Mikhaylov &
               Laver 2011, LSQ), defined everywhere; ``s`` = smoothing (default 0.5)

Competitive/threat framing is NOT part of these indices; it is kept as a separate measure so that
H5 (recognition catches up while competitive concern stays high) remains testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

METHODS = ("share", "balance", "logit")


def recognition_index(horizontal: pd.Series, vertical: pd.Series, *, method: str = "logit",
                      smoothing: float = 0.5) -> pd.Series:
    h = horizontal.astype(float)
    v = vertical.astype(float)
    total = h + v
    if method == "share":
        out = h / total.where(total > 0)
    elif method == "balance":
        out = (h - v) / total.where(total > 0)
    elif method == "logit":
        out = np.log((h + smoothing) / (v + smoothing))
    else:
        raise ValueError(f"method must be one of {METHODS}")
    return pd.Series(out, index=horizontal.index, name=f"recognition_{method}")


def add_recognition_indices(df: pd.DataFrame, *, horizontal_col: str = "frame_horizontal",
                            vertical_col: str = "frame_vertical",
                            methods: tuple[str, ...] = METHODS,
                            smoothing: float = 0.5) -> pd.DataFrame:
    """Return ``df`` with one ``recognition_<method>`` column per method."""
    out = df.copy()
    for method in methods:
        out[f"recognition_{method}"] = recognition_index(
            df[horizontal_col], df[vertical_col], method=method, smoothing=smoothing)
    return out
