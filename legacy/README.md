# Legacy project: status proximity and recognition lag (H1-H5)

This directory is a pointer, not a copy. The original project is NOT moved -- it remains exactly
where it was: `docs/research_design.md`, `docs/decisions.md` (D001-D021), `scripts/01_collect_data.py`
through `scripts/10_make_figures.py`, `scripts/pilot/{build_frames,test_hypotheses}.py`,
`src/srl/status/`, `src/srl/trade/`, `src/srl/recognition/`, `src/srl/attention/`, `src/srl/panel/`,
`src/srl/models/`, and their outputs under `outputs/pilot/`.

## Why this is preserved unchanged

The 2026-10-13 overhaul (see `docs/decision_log.md` R001) reframes the central question from a
continuous "recognition lag" variable estimated across a 12-partner ASEAN+China panel toward
discrete recognition *turning points* for two primary case pairs (Japan->Korea, Korea->China).
Per the overhaul brief: "Do not reinterpret these findings as evidence for the new theory."

## What was found (summary; full detail in outputs/pilot/ and the 2026-09-14 session report)

A pilot run of `scripts/pilot/test_hypotheses.py` (first successful execution 2026-10-13, after
fixing a pandas index/column collision bug -- see git log) tested H1-H5 on the existing Korean-
government-text corpus:

- **H1** (salience -> attention): not supported. Lagged bilateral trade share does not predict
  government attention in any specification (p >= 0.6 throughout).
- **H2** (lag peaks at intermediate status proximity): weak/mixed. A significant concave
  relationship between proximity and recognition appears only in a less rigorous (year-FE-only,
  between-partner) specification; the preferred partner+year fixed-effects specification is not
  significant, and the shape found (smooth rise-then-plateau) does not match the specific
  "stall in the middle" pattern H2 predicts.
- **H3** (competitive overlap amplifies): not supported. Interaction coefficient has the wrong
  sign and is not significant.
- **H4** (interdependence amplifies): not supported. Same pattern as H3.
- **H5** (sustained capability -> catch-up): not supported in the regression (wrong sign); an
  event-study bin 4 years after World Bank income-group upgrades shows a marginal, non-robust
  uptick (p_wcb = 0.065, single point among ten).

**Known limitations, not corrected in this pilot:** the recognition measure is an unvalidated
dictionary-based classifier, applied to Korean-language text only; coverage is extremely
unbalanced (China alone supplies ~950 of ~1,370 framed sentences across the 12-partner panel;
Brunei has zero partner-years meeting the minimum-sentence threshold for the recognition outcome);
only 12 clusters, which the pilot already handles with a wild-cluster bootstrap but which limits
power regardless.

## What is reused by the new project

- `src/srl/trade/overlap.py` (`export_similarity_index`, Finger-Kreinin) -- reused directly for
  the new industrial-crossover work (`data/processed/industrial_crossover_candidates.csv`).
- `src/srl/status/proximity.py` (`relative_to_reference`) -- reused for material-status ratios.
- The Atlas of Economic Complexity and WDI raw data (`data/raw/complexity_atlas/`,
  `data/interim/prelim/macro_country_year.csv`) -- reused as-is; it already covers USA, JPN, KOR,
  CHN back to 1960-1962, which is exactly what the new case pairs need.
- The Korean-government text corpus and its acquisition pipeline (`src/srl/acquisition/`,
  `scripts/acquire/`) -- reused as the Korean-side recognition corpus for the kor_chn and (partly)
  jpn_kor cases; see `config/cases.yaml` for what is still missing (a Japanese-side corpus for
  jpn_kor, where Japan is the incumbent whose recognition of Korea is the object of interest).

## What is NOT reused without revision

- The recognition dictionary (`config/recognition_frames.yaml`, `src/srl/recognition/dictionary.py`)
  is kept for comparison only, per the overhaul brief ("Preserve it for comparison, but do not use
  it as the new primary recognition measure"). The new project needs a multilingual (Japanese,
  Korean, English, Chinese as needed), peer-vs-achievement-distinguishing classification scheme --
  see `docs/measurement_protocol.md`.
- The H1-H5 hypothesis frame itself is not reused as the organizing structure; the new project
  organizes around recognition turning points (T1-T4) and competing mechanisms (M1-M5) -- see
  `docs/theoretical_framework.md`.
