"""Event-study specifications (only if later justified).

Candidate events: formal partnership upgrades, FTA entry into force, threshold crossings in
status proximity (H5). Requirements before implementation: events defined and dated ex ante from
documented sources; staggered-adoption-robust estimator; pre-trend diagnostics; explicit
treatment of never-treated partners. With 12 partners, power will be limited.
"""

from __future__ import annotations


def event_study(*args, **kwargs):
    raise NotImplementedError("Event-study design not justified/specified yet")
