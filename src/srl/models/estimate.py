"""Panel estimation (linearmodels ``PanelOLS``) and result export.

Inference caveat: the main panel has 12 partners, far too few clusters for conventional
cluster-robust standard errors. Report them only alongside small-cluster alternatives (e.g., wild
cluster bootstrap, randomization inference) - to be added and logged in docs/decisions.md.
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

import pandas as pd

from srl.models.design import build_design
from srl.models.specs import ModelSpec
from srl.utils.config import get_path
from srl.utils.io import write_table

logger = logging.getLogger(__name__)

MIN_CLUSTERS_WARNING = 30


def fit_spec(panel: pd.DataFrame, spec: ModelSpec, *, entity_col: str = "iso3",
             time_col: str = "year"):
    """Estimate ``spec`` on ``panel``; returns a linearmodels results object."""
    from linearmodels.panel import PanelOLS

    df, exog = build_design(panel, spec, entity_col=entity_col, time_col=time_col)
    data = df.set_index([entity_col, time_col])[[spec.outcome, *exog]].dropna()
    if data.empty:
        raise ValueError(f"{spec.name}: no complete observations")
    data = data.assign(const=1.0)

    n_entities = data.index.get_level_values(0).nunique()
    if spec.cov_type == "clustered" and n_entities < MIN_CLUSTERS_WARNING:
        logger.warning("%s: only %d clusters - conventional clustered SEs are unreliable; "
                       "report small-cluster inference", spec.name, n_entities)

    model = PanelOLS(data[spec.outcome], data[["const", *exog]],
                     entity_effects=spec.entity_effects, time_effects=spec.time_effects,
                     drop_absorbed=True)
    fit_kwargs: dict = {"cov_type": spec.cov_type}
    if spec.cov_type == "clustered":
        fit_kwargs["cluster_entity"] = spec.cluster in {"entity", "twoway"}
        fit_kwargs["cluster_time"] = spec.cluster in {"time", "twoway"}
    return model.fit(**fit_kwargs)


def save_result(result, spec: ModelSpec, *, suffix: str = "") -> dict[str, Path]:
    """Write summary text, coefficient table and run metadata for one fitted model."""
    name = f"{spec.name}{suffix}"
    models_dir = get_path("outputs.models", mkdir=True)
    summary_path = models_dir / f"{name}.txt"
    summary_path.write_text(str(result.summary), encoding="utf-8")

    coefs = pd.DataFrame({
        "term": result.params.index,
        "estimate": result.params.to_numpy(),
        "std_error": result.std_errors.to_numpy(),
        "p_value": result.pvalues.to_numpy(),
    })
    coef_path = write_table(coefs, get_path("outputs.tables", mkdir=True) / f"{name}_coefficients.csv")

    meta = {"spec": spec.name, "hypothesis": spec.hypothesis, "outcome": spec.outcome,
            "nobs": int(result.nobs), "entity_effects": spec.entity_effects,
            "time_effects": spec.time_effects, "cov_type": spec.cov_type, "cluster": spec.cluster,
            "run_date": date.today().isoformat()}
    meta_path = models_dir / f"{name}_meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"summary": summary_path, "coefficients": coef_path, "meta": meta_path}
