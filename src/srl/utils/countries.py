"""Country registry and name normalization (dataset names -> ISO3).

The registry is built from ``config/countries.yaml``. :func:`normalize_key` reduces a name to a
comparison key (Unicode-normalized, accent-free, case-folded, punctuation-insensitive), and
:func:`to_iso3` maps any configured name, alias, Korean name or ISO3 code to the canonical ISO3.

Text matching in running prose (with Korean particles, compounds, shields such as "South China
Sea") is handled separately in :mod:`srl.text.entities`.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from srl.utils.config import ConfigError, load_config


@dataclass(frozen=True)
class Country:
    iso3: str
    name: str
    role: str
    iso2: str | None = None
    iso_numeric: str | None = None
    name_ko: str | None = None
    aliases_en: tuple[str, ...] = ()
    aliases_ko: tuple[str, ...] = ()
    demonyms_en: tuple[str, ...] = ()
    notes: str = ""

    @property
    def names(self) -> tuple[str, ...]:
        """All names used for dataset normalization (ISO3, official, Korean, aliases)."""
        candidates = (self.iso3, self.name, self.name_ko, *self.aliases_en, *self.aliases_ko)
        return tuple(dict.fromkeys(n for n in candidates if n))


_DROP_CHARS = re.compile(r"[.'`’]")
_SPACE_CHARS = re.compile(r"[,\-‐–—·ㆍ・/()\[\]]")
_WHITESPACE = re.compile(r"\s+")


def normalize_key(name: str) -> str:
    """Reduce a country name to a comparison key.

    Steps: NFKC; strip diacritics (``Việt Nam`` -> ``viet nam``) while preserving Hangul;
    case-fold; ``&`` -> ``and``; drop periods/apostrophes; treat commas, hyphens, middle dots,
    slashes and brackets as spaces; collapse whitespace; drop a leading ``the``.
    """
    text = unicodedata.normalize("NFKC", str(name))
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = unicodedata.normalize("NFC", text).casefold()
    text = text.replace("&", " and ")
    text = _DROP_CHARS.sub("", text)
    text = _SPACE_CHARS.sub(" ", text)
    text = _WHITESPACE.sub(" ", text).strip()
    return re.sub(r"^the ", "", text)


def _as_tuple(value: Iterable[str] | None) -> tuple[str, ...]:
    return tuple(value or ())


@lru_cache(maxsize=1)
def load_countries() -> dict[str, Country]:
    """Return the country registry keyed by ISO3."""
    cfg = load_config("countries").get("countries", {})
    registry = {}
    for iso3, spec in cfg.items():
        registry[iso3] = Country(
            iso3=iso3,
            name=spec["name"],
            role=spec["role"],
            iso2=spec.get("iso2"),
            iso_numeric=spec.get("iso_numeric"),
            name_ko=spec.get("name_ko"),
            aliases_en=_as_tuple(spec.get("aliases_en")),
            aliases_ko=_as_tuple(spec.get("aliases_ko")),
            demonyms_en=_as_tuple(spec.get("demonyms_en")),
            notes=spec.get("notes", "") or "",
        )
    return registry


def build_alias_index(countries: dict[str, Country]) -> dict[str, str]:
    """Map normalized keys to ISO3; raise :class:`ConfigError` on conflicting aliases."""
    index: dict[str, str] = {}
    conflicts = []
    for country in countries.values():
        for name in country.names:
            key = normalize_key(name)
            existing = index.setdefault(key, country.iso3)
            if existing != country.iso3:
                conflicts.append(f"{name!r} -> {existing} and {country.iso3}")
    if conflicts:
        raise ConfigError("Conflicting country aliases: " + "; ".join(conflicts))
    return index


@lru_cache(maxsize=1)
def _default_index() -> dict[str, str]:
    return build_alias_index(load_countries())


def to_iso3(name: object, *, strict: bool = False) -> str | None:
    """Map a country name/alias/ISO3 code to ISO3.

    Returns ``None`` for missing or unrecognized names unless ``strict=True``, in which case an
    unrecognized name raises ``KeyError``.
    """
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return None
    iso3 = _default_index().get(normalize_key(str(name)))
    if iso3 is None and strict:
        raise KeyError(f"Unrecognized country name: {name!r} (add an alias in config/countries.yaml)")
    return iso3


def normalize_country_series(series: pd.Series, *, strict: bool = False) -> pd.Series:
    """Vectorized :func:`to_iso3` over unique values."""
    mapping = {value: to_iso3(value, strict=strict) for value in series.dropna().unique()}
    return series.map(mapping)


def unmatched_names(series: pd.Series) -> list[str]:
    """Distinct non-missing names in ``series`` that do not map to any configured country."""
    return sorted(str(v) for v in series.dropna().unique() if to_iso3(v) is None)


def panel_definition(panel: str = "main") -> tuple[str, list[str]]:
    """Return ``(incumbent_iso3, partner_iso3_list)`` for a configured panel."""
    panels = load_config("countries").get("panels", {})
    if panel not in panels:
        raise ConfigError(f"Panel '{panel}' not defined in config/countries.yaml")
    spec = panels[panel]
    return spec["incumbent"], list(spec["partners"])


def group_members(group: str, year: int | None = None) -> list[str]:
    """Members of a country group (e.g., ASEAN), optionally as of a given year."""
    groups = load_config("countries").get("groups", {})
    if group not in groups:
        raise ConfigError(f"Group '{group}' not defined in config/countries.yaml")
    members = groups[group].get("members", {})
    return sorted(iso for iso, since in members.items() if year is None or since <= year)
