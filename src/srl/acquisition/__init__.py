"""Data acquisition: source registry and raw-file inventory.

Policy: this package intentionally contains NO automated downloaders or scrapers. Files are
deposited by hand under ``data/raw/<source_id>/<YYYY-MM-DD>/`` and registered with
``scripts/01_collect_data.py --mode register``. An automated connector may be added only after the
source is validated (documentation, terms of use, licence, rate limits) and the decision is logged
in ``docs/decisions.md``.
"""
