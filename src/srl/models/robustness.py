"""Robustness grids: re-estimate a base spec with alternative measures.

Example: swap ``recognition`` for each recognition index and ``status_proximity`` for each
status measure, producing one spec per combination with a traceable name.
"""

from __future__ import annotations

import itertools
from dataclasses import replace

from srl.models.specs import ModelSpec


def _swap(values: tuple[str, ...], old: str, new: str) -> tuple[str, ...]:
    return tuple(new if v == old else v for v in values)


def expand_grid(base: ModelSpec, substitutions: dict[str, list[str]]) -> list[ModelSpec]:
    """Return specs for every combination of variable substitutions.

    ``substitutions`` maps a placeholder variable in ``base`` (outcome, regressor, control or
    interaction term) to a list of concrete panel columns.
    """
    keys = list(substitutions)
    specs = []
    for combo in itertools.product(*(substitutions[k] for k in keys)):
        spec = base
        for old, new in zip(keys, combo, strict=True):
            spec = replace(
                spec,
                outcome=new if spec.outcome == old else spec.outcome,
                regressors=_swap(spec.regressors, old, new),
                controls=_swap(spec.controls, old, new),
                interactions=tuple(_swap(pair, old, new) for pair in spec.interactions),
                lags={(new if k == old else k): v for k, v in spec.lags.items()},
                polynomial={(new if k == old else k): v for k, v in spec.polynomial.items()},
            )
        suffix = "__".join(combo)
        specs.append(replace(spec, name=f"{base.name}__{suffix}"))
    return specs
