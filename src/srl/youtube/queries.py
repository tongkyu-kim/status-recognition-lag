"""Build the search plan from config/youtube_queries.yaml and config/countries.yaml."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from srl.utils.config import load_config


@dataclass(frozen=True)
class SearchSpec:
    country: str  # ISO3
    family: str  # retrieval intent (NOT the coded frame)
    query: str
    order: str = "relevance"
    published_after: str | None = None
    published_before: str | None = None

    @property
    def year_slice(self) -> str:
        return self.published_after[:4] if self.published_after else "all"

    @property
    def spec_id(self) -> str:
        """Stable short id (file names, provenance joins)."""
        key = "|".join(
            [
                self.country,
                self.family,
                self.query,
                self.order,
                self.published_after or "",
                self.published_before or "",
            ]
        )
        return hashlib.sha1(key.encode("utf-8")).hexdigest()[:12]


def country_names_ko() -> dict[str, str]:
    return {iso: c["name_ko"] for iso, c in load_config("countries")["countries"].items()}


def build_plan(
    countries: list[str] | None = None, *, pilot: bool = False, families: list[str] | None = None
) -> list[SearchSpec]:
    cfg = load_config("youtube_queries")
    sampling = load_config("youtube_sampling")["video_selection"]
    names = country_names_ko()
    templates = cfg["templates"]
    if pilot:
        countries = countries or cfg["pilot"]["countries"]
        if cfg["pilot"].get("tier", "core") == "core":
            templates = cfg["pilot"]["core_templates"]
    countries = countries or [c for c in load_config("countries")["panels"]["main"]["partners"]]
    families = families or list(templates)
    orders = cfg["defaults"].get("orders", ["relevance"])
    after, before = sampling["published_after"], sampling["published_before"]

    plan: list[SearchSpec] = []
    for iso in countries:
        ko = names[iso]
        for fam in families:
            queries = [t.format(ko=ko) for t in templates.get(fam, [])]
            if templates is cfg["templates"]:  # country extras belong to the full tier
                queries += cfg.get("country_extra", {}).get(iso, {}).get(fam, [])
            for q in dict.fromkeys(queries):
                for order in orders:
                    plan.append(SearchSpec(iso, fam, q, order, after, before))

    if pilot and cfg["pilot"].get("year_sliced"):
        ys = cfg["pilot"]["year_sliced"]
        lo, hi = ys["years"]
        step = int(ys.get("window_years", 1))
        fam_of = {t: f for f, ts in cfg["templates"].items() for t in ts}
        for iso in ys["countries"]:
            for tmpl in ys["templates"]:
                for year in range(lo, hi + 1, step):
                    end = min(year + step, hi + 1)
                    plan.append(
                        SearchSpec(
                            iso,
                            fam_of.get(tmpl, "unknown"),
                            tmpl.format(ko=names[iso]),
                            "relevance",
                            f"{year}-01-01T00:00:00Z",
                            f"{end}-01-01T00:00:00Z",
                        )
                    )
    return list(dict.fromkeys(plan))


def quota_estimate(plan: list[SearchSpec], pages_per_query: int = 1) -> dict[str, int]:
    """Search cost dominates: 100 units per search page."""
    cost = load_config("youtube_sampling")["api"]["cost"]["search"]
    units = len(plan) * pages_per_query * cost
    daily = load_config("youtube_sampling")["api"]["daily_quota_units"]
    return {"n_searches": len(plan), "search_units": units, "days_at_default_quota": -(-units // daily)}
