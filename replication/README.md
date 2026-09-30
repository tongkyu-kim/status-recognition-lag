# Replication package (specification)

This folder will hold the public replication package, assembled at submission. It contains only
what is needed to reproduce the reported analysis and what may legally be shared.

## Will contain

- `code/`: the `srl` package, `scripts/01–10`, `config/`, `tasks.py`/`Makefile`, pinned
  environment (`requirements-lock.txt` / `environment.yml`)
- `data/`: derived analytical data where legally shareable (the partner-year panel, measure
  tables), with a codebook generated from `docs/variable_dictionary.md`
- `inputs.md`: for each source that cannot be redistributed, the exact dataset, version, retrieval
  date, query and expected file placement, plus checksums from `data/raw_manifest.csv`
- `results/`: numerical outputs, tables, figures and model results, exactly as produced by the
  scripts
- `README.md`: system requirements, run order, expected runtime, and a mapping from each table and
  figure to the script that produces it

## Will not contain

- Raw third-party data whose terms do not permit redistribution
- Exploratory notebooks
- Interpretive notes, drafts or manuscript-building material
- Credentials or local configuration
