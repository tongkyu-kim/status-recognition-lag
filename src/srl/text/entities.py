"""Country / group entity matching in running text (Korean and English).

Entities come from ``config/countries.yaml``: ``countries`` (kind ``country``), ``groups`` such as
ASEAN (kind ``group``), and ``shields`` (kind ``shield``) - non-country spans such as
"South China Sea" / "남중국해" that are matched and then discarded so they do not count as
mentions of China. Overlaps resolve leftmost-longest, so "North Korea" wins over "Korea".

All aliases and patterns are candidates: validate them with keyword-in-context review on the
real corpus before relying on counts.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from srl.text.patterns import find_spans, resolve_overlaps, term_to_regex
from srl.utils.config import load_config

_PRIORITY = {"shield": 0, "country": 1, "group": 2}


@dataclass(frozen=True)
class Mention:
    entity_id: str
    entity_type: str
    start: int
    end: int
    surface: str


def _entity_terms(spec: dict[str, Any], *, include_demonyms: bool) -> list[str]:
    terms = [spec.get("name"), spec.get("name_ko"), *(spec.get("aliases_en") or []),
             *(spec.get("aliases_ko") or [])]
    if include_demonyms:
        terms += spec.get("demonyms_en") or []
    return list(dict.fromkeys(t for t in terms if t))


class EntityMatcher:
    """Compiled matcher for all configured entities."""

    def __init__(self, *, include_demonyms: bool = False, config: dict[str, Any] | None = None):
        cfg = config if config is not None else load_config("countries")
        self._patterns: list[tuple[str, str, int, re.Pattern[str]]] = []
        sections = (("countries", "country"), ("groups", "group"), ("shields", "shield"))
        for section, kind in sections:
            for entity_id, spec in (cfg.get(section) or {}).items():
                regexes = [term_to_regex(t) for t in
                           _entity_terms(spec, include_demonyms=include_demonyms and kind == "country")]
                regexes += list(spec.get("text_patterns") or [])
                for regex in regexes:
                    self._patterns.append(
                        (entity_id, kind, _PRIORITY[kind], re.compile(regex, re.IGNORECASE)))

    def find(self, text: str, *, keep_shields: bool = False) -> list[Mention]:
        """Return non-overlapping mentions in order of appearance."""
        if not text:
            return []
        spans = resolve_overlaps(find_spans(text, self._patterns))
        return [Mention(s.label, s.kind, s.start, s.end, text[s.start:s.end])
                for s in spans if keep_shields or s.kind != "shield"]

    def count(self, text: str, entity_types: tuple[str, ...] = ("country",)) -> Counter[str]:
        return Counter(m.entity_id for m in self.find(text) if m.entity_type in entity_types)

    def mask(self, text: str, token: str = "[COUNTRY]") -> str:
        """Replace country/group mentions with ``token`` (for masked human coding)."""
        out, cursor = [], 0
        for m in self.find(text):
            out.append(text[cursor:m.start])
            out.append(token)
            cursor = m.end
        out.append(text[cursor:])
        return "".join(out)


@lru_cache(maxsize=2)
def default_matcher(include_demonyms: bool = False) -> EntityMatcher:
    return EntityMatcher(include_demonyms=include_demonyms)


def find_country_mentions(text: str, *, include_demonyms: bool = False) -> list[Mention]:
    """Convenience wrapper using the configured default matcher."""
    return default_matcher(include_demonyms).find(text)
