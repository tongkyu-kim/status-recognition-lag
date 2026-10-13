# Status Proximity and Recognition Lag in Changing Economic Hierarchies

> **2026-10-13 -- project reframed.** The organizing question is now *when does a rising state
> become recognized as a peer, and why does recognition sometimes lag material convergence even
> after it occurs* -- turning points and the Korean concept of 무시 (musi: neglect, dismissal,
> status denial, delayed recognition, status reproduction), not a single continuous "lag" variable.
> Primary cases: Japan->Korea and Korea->China (see `config/cases.yaml`, `docs/case_selection.md`,
> `docs/theoretical_framework.md`). The original H1-H5 project below is preserved unchanged and
> was NOT reinterpreted as evidence for the new framework -- see `legacy/README.md` for its
> results and `outputs/reports/research_overhaul_report.md` for a full account of what changed,
> what remains unverified, and what requires manual action. The description immediately below
> (through "Current status") documents the **original** project as background; for the current
> one read, in order: `docs/theoretical_framework.md`, `docs/case_selection.md`,
> `docs/measurement_protocol.md` (design only, not yet implemented), and
> `docs/data_access_requirements.md`.

Research code and documentation for an international political economy project on how
governments recognize states that are converging on them economically.

## Research question (legacy framing -- see notice above for the current one)

When lower-ranked states converge toward an incumbent's material and industrial position, does
the incumbent's **political recognition** of them adjust more slowly than their **objective
economic status**, and under what conditions?

## Theoretical mechanism

Economic convergence should raise the salience of a partner and therefore government attention:

$$\text{Economic convergence} \rightarrow \text{Greater government attention}$$

Recognition need not follow. When convergence is combined with competitive overlap and
economic interdependence, it may generate status pressure that slows recognition:

$$\text{Convergence} + \text{Competitive overlap} + \text{Interdependence}
\rightarrow \text{Status pressure} \rightarrow \text{Recognition lag}$$

Conceptually,

$$\text{RecognitionLag}_{it} = \mathbb{E}\left[\text{Recognition}_{it} \mid \text{ObjectiveStatus}_{it}\right] - \text{ObservedRecognition}_{it}$$

The repository does not fix a single formula. Several operationalizations are computed side by side
(see [docs/research_design.md](docs/research_design.md)).

## Hypotheses

| | Hypothesis |
|---|---|
| **H1** Economic salience | Greater bilateral economic importance increases government attention toward the partner. |
| **H2** Status proximity | Recognition lag is greatest among lower-ranked states approaching the incumbent's material and industrial position, not among the most distant states. |
| **H3** Competitive overlap | The status-proximity effect is stronger when the rising state's industrial/export structure increasingly overlaps with the incumbent's. |
| **H4** Interdependence amplification | The status-proximity effect is stronger when the incumbent is highly exposed economically to the rising state. |
| **H5** Recognition catch-up | Once a rising state achieves sufficiently high and sustained capability, recognition catches up even if competitive concern remains high. |

Together, H2 and H5 imply that the relationship between status proximity and recognition may be
nonlinear.

## Empirical scope

- **Main setting:** the Republic of Korea as incumbent, with China and all ASEAN member states as
  partners (Brunei Darussalam, Cambodia, Indonesia, Lao PDR, Malaysia, Myanmar, Philippines,
  Singapore, Thailand, Timor-Leste, Viet Nam).
- **Unit of analysis:** directed dyad Korea → partner, annual (partner-year). Text measures are
  built from sentence- and document-level data.
- **Period:** to be fixed once source coverage is verified.
- **Possible historical extensions** (not yet in scope): US → Japan (1970s–1980s);
  Japan → Korea (1990s–2000s).

## Data acquisition (2026-09-30)

Public data are retrieved by `scripts/acquire/acq_*.py` (polite, robots-aware, write-once; D015).
Low-risk derived files are built by `scripts/acquire/build_prelim.py` and
`build_gov_documents.py`, diagnostics by `quality_checks.py`, and the catalog by `build_catalog.py`.
Start with:

- [docs/data_collection_status.md](docs/data_collection_status.md): what we have and what is missing
- [docs/manual_data_tasks.md](docs/manual_data_tasks.md): what a human must retrieve, and how
- [docs/data_sources.md](docs/data_sources.md) and `metadata/source_catalog.csv`: sources and terms

## Public-discourse extension (YouTube)

Digitally expressed public recognition in Korean YouTube comments, compared with government
recognition (H-P1 to H-P5). Official YouTube Data API v3 only; commenter identities are minimized at
ingest. See [docs/youtube_data_design.md](docs/youtube_data_design.md),
[docs/youtube_coding_protocol.md](docs/youtube_coding_protocol.md) and
[docs/youtube_collection_status.md](docs/youtube_collection_status.md). Needs an API key (task Y1).

## Repository structure

```text
status-recognition-lag/
├── config/            paths, countries, sources, analysis settings, model specs, frame dictionary
├── data/
│   ├── raw/           immutable source files: raw/<source_id>/<YYYY-MM-DD>/   (not in Git)
│   ├── interim/       cleaned canonical tables                                 (not in Git)
│   ├── processed/     analytical measures and the partner-year panel           (not in Git)
│   ├── external/      third-party reference tables (concordances, code lists)  (not in Git)
│   └── raw_manifest.csv   checksums and provenance of every raw file           (in Git)
├── src/srl/           importable package: acquisition, cleaning, trade, status, text,
│                      attention, recognition, panel, models, figures, utils
├── scripts/           numbered production pipeline, 01 → 10
├── notebooks/exploratory/   exploratory work only; never a source of reported results
├── outputs/           tables, figures, models, diagnostics (regenerated by scripts)
├── tests/             unit tests
├── docs/              research design, variable dictionary, data sources, coding protocol,
│                      decision log
└── replication/       specification of the eventual public replication package
```

## Workflow

```sh
python -m pip install -e ".[dev]"      # or: conda env create -f environment.yml
pre-commit install

make test                              # or: python tasks.py test   (no make on Windows)
make sources                           # list candidate sources and raw-file counts
# deposit raw files by hand under data/raw/<source_id>/<YYYY-MM-DD>/, then:
make register-raw                      # checksum into data/raw_manifest.csv
make pipeline                          # verify-raw → trade → status → text → attention
                                       #   → recognition → panel → models → figures
```

| Step | Script | Output |
|---|---|---|
| 01 | `01_collect_data.py` | raw-file registration and verification (no downloading) |
| 02 | `02_clean_trade.py` | canonical trade tables |
| 03 | `03_build_status_measures.py` | status proximity, interdependence, competitive overlap |
| 04 | `04_collect_government_text.py` | document table from deposited texts and metadata |
| 05 | `05_process_text.py` | sentences and country/group mentions |
| 06 | `06_build_attention_measures.py` | attention measures |
| 07 | `07_build_recognition_measures.py` | recognition frames and indices; coding samples |
| 08 | `08_build_panel.py` | partner-year panel with recognition-lag variants |
| 09 | `09_run_models.py` | estimates for specifications marked `ready` |
| 10 | `10_make_figures.py` | production figures |

Scripts exit with code 2 when inputs are missing, 3 when a stage awaits a data-dependent design
decision, and 4 when a configuration setting is undecided. They do not guess.

## Current status

**Scaffold only.** No data have been acquired and no results exist. All data sources are candidates
awaiting validation. The recognition-frame dictionary contains unvalidated seed terms. Open design
decisions are tracked in [docs/decisions.md](docs/decisions.md).

## Reproducibility principles

1. No fabricated data. No invented sources, URLs or credentials.
2. Raw data are immutable. Writes into `data/raw` are refused in code, and raw files are
   checksummed in `data/raw_manifest.csv`.
3. Every derived table is produced by a script from configuration. There are no hard-coded or
   absolute paths.
4. Exploratory notebooks are kept separate. Reported numbers come only from `scripts/`.
5. A deterministic seed (`config/analysis.yaml`) is used for all sampling and stochastic steps.
6. Methodological choices are dated and justified in `docs/decisions.md`.
7. Variables are defined in `docs/variable_dictionary.md` before they are used in models.
8. The public replication package contains only what is needed to reproduce the analysis and is
   legally shareable (see [replication/README.md](replication/README.md)).

## Data availability and licence

Code is released under the MIT licence ([LICENSE](LICENSE)). Third-party data remain subject to
their providers' terms and are redistributed only where permitted.

## Citation

To be added.
