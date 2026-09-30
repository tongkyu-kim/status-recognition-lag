"""LLM-assisted coding interface (optional; not configured).

No LLM client or API dependency is installed or imported by this project. If LLM-assisted coding
is adopted later, implement a backend satisfying :class:`LLMCoder`, and require:

- model identifier and version pinned in config; temperature 0 / deterministic settings logged;
- the exact prompt (the coding protocol) versioned in the repository;
- raw model outputs stored as raw inputs (immutable) with timestamps;
- validation against the human-coded sample with the same reliability statistics as human
  coders, reported per category and per language.
"""

from __future__ import annotations

from typing import Protocol

import pandas as pd


class LLMCoder(Protocol):
    def code_sentences(self, sentences: pd.DataFrame) -> pd.DataFrame:
        """Return one row per sentence with protocol categories and a rationale field."""
        ...


def get_llm_coder(config: dict | None = None) -> LLMCoder:
    raise NotImplementedError(
        "LLM-assisted coding is not configured. It is optional and must be explicitly set up and "
        "logged in docs/decisions.md."
    )
