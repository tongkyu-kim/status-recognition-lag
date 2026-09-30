# Exploratory notebooks

For exploration only: inspecting raw files, KWIC review of country aliases and frame terms, and
trying out measures.

Rules:

- Name notebooks `YYYY-MM-DD_<initials>_<topic>.ipynb`.
- Import project code from `srl` and read paths via `srl.utils.config.get_path`. Never use
  absolute paths.
- Read data only. Never write to `data/raw`, `data/processed` or `outputs/`.
- No number, table or figure reported in the paper may come from a notebook. Once an analysis is
  settled, move it into `src/srl/` and a numbered script.
- Outputs are stripped on commit (`nbstripout` via pre-commit).
