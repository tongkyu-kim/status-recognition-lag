"""Model specifications loaded from ``config/models.yaml``."""

from __future__ import annotations

from dataclasses import dataclass, field

from srl.utils.config import load_config

STATUSES = {"planned", "design_pending", "ready", "retired"}


@dataclass(frozen=True)
class ModelSpec:
    name: str
    hypothesis: str
    outcome: str
    regressors: tuple[str, ...]
    status: str = "planned"
    controls: tuple[str, ...] = ()
    lags: dict[str, tuple[int, ...]] = field(default_factory=dict)
    polynomial: dict[str, int] = field(default_factory=dict)
    interactions: tuple[tuple[str, str], ...] = ()
    center_interactions: bool = True
    entity_effects: bool = True
    time_effects: bool = True
    cov_type: str = "clustered"
    cluster: str = "entity"
    notes: str = ""


def load_model_specs() -> list[ModelSpec]:
    cfg = load_config("models")
    defaults = cfg.get("defaults", {})
    specs = []
    for raw in cfg.get("specs", []):
        merged = {**defaults, **raw}
        if merged.get("status", "planned") not in STATUSES:
            raise ValueError(f"{merged['name']}: status must be one of {sorted(STATUSES)}")
        specs.append(ModelSpec(
            name=merged["name"],
            hypothesis=merged["hypothesis"],
            outcome=merged["outcome"],
            regressors=tuple(merged.get("regressors", [])),
            status=merged.get("status", "planned"),
            controls=tuple(merged.get("controls", [])),
            lags={k: tuple(v) for k, v in (merged.get("lags") or {}).items()},
            polynomial=dict(merged.get("polynomial") or {}),
            interactions=tuple(tuple(pair) for pair in merged.get("interactions") or []),
            center_interactions=bool(merged.get("center_interactions", True)),
            entity_effects=bool(merged.get("entity_effects", True)),
            time_effects=bool(merged.get("time_effects", True)),
            cov_type=merged.get("cov_type", "clustered"),
            cluster=merged.get("cluster", "entity"),
            notes=merged.get("notes", "") or "",
        ))
    names = [s.name for s in specs]
    if len(names) != len(set(names)):
        raise ValueError("Duplicate model spec names in config/models.yaml")
    return specs
