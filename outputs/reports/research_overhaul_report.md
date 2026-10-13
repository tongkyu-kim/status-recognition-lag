# Research overhaul report

**Date:** 2026-10-13. **Scope:** Phase 1-3 substantially complete; Phase 4 (architecture) complete;
Phase 5 (material status + industrial crossovers) substantially complete for two of four case
pairs; Phases 6-8 (multilingual recognition measurement, survey pipeline, full pilot execution,
final testing) are scaffolded/designed but **not implemented**. This report distinguishes
completed work from proposed work throughout -- nothing below is labeled "done" unless a file,
test, or figure in this repository demonstrates it.

## What was preserved

The entire legacy status-proximity/recognition-lag project (`docs/research_design.md`,
`docs/decisions.md` D001-D021, `scripts/01-10`, `scripts/pilot/`, `src/srl/status`, `src/srl/trade`,
`src/srl/recognition`, `src/srl/attention`, `src/srl/panel`, `src/srl/models`, and all raw/interim/
processed data already collected) is untouched. See `legacy/README.md`. Git history was not
rewritten; a local checkpoint commit was made before any new work began (git log, commit `8deaba2`
and prior). Nothing was pushed to any remote.

## What was changed

- One genuine bug was fixed in `scripts/pilot/test_hypotheses.py` (a pandas index/column
  collision in `attention_measures()` that had never been exercised -- the pilot had never
  successfully run end-to-end before this session). Fixed and verified; see git log.
- That fixed pilot was then run for the first time, producing real H1-H5 results from the actual
  collected corpus (not fabricated) -- summarized honestly in `legacy/README.md` with explicit
  caveats (unvalidated dictionary, Korean-only text, 12 unbalanced clusters).

## What was downloaded

Nothing new was downloaded in this pass. All empirical work below reuses data already present in
`data/raw/complexity_atlas/` and `data/interim/prelim/` from the legacy collection run. See
`docs/data_access_requirements.md` for what is available-but-not-yet-downloaded (CEPII BACI, WVS,
Pew microdata) versus what needs further investigation (OECD TiVA, WIPO) versus what needs a
genuinely new acquisition effort (a Japanese-side media/government text corpus -- see "most
consequential gap" below).

## What was implemented

- New directory skeleton, additive (`src/srl/{material_status,historical_events,public_opinion,
  culture,social_recognition,turning_points,identification}`, `config/cases.yaml`,
  `config/sectors.yaml`, `data/annotations/`, `outputs/reports/`, `legacy/`). The new `src/srl/`
  subpackages are directories only -- **no code has been written into them yet**; they are not
  "implemented" in any functional sense, only scaffolded.
- `data/processed/industrial_crossover_candidates.csv`: a real, computed table of crossover
  candidates (incumbent/challenger/industry/date/source/reliability/limitations/confounders) for
  shipbuilding, semiconductors, and batteries, built from the Atlas of Economic Complexity's own
  `globalMarketShare` field (not self-estimated). Two sub-findings required flagging rather than
  reporting as clean results: the pre-1992 SITC shipbuilding series has an implausible break
  (documented in `docs/decision_log.md` R002) and the HS9013 display/optics proxy is unreliable
  (same entry). These are recorded as `UNRELIABLE` rows in the table, not silently dropped.
- Two unit tests (`tests/test_cases_sectors_config.py`) verifying the new config loads and is
  internally consistent. Full suite: **80/80 passing** (78 legacy + 2 new).
- `config/cases.yaml`, `config/sectors.yaml` -- real content reflecting the decisions actually
  made, not placeholders.
- Eight documentation files: `docs/literature_review.md`, `docs/theoretical_framework.md`,
  `docs/research_gap.md`, `docs/case_selection.md`, `docs/measurement_protocol.md`,
  `docs/data_access_requirements.md`, `docs/decision_log.md`, `legacy/README.md`.
  `references/references.bib`.

## What was successfully executed (produces real numbers/figures, verifiable by rerunning)

1. **Legacy pilot, first successful run** -- `outputs/pilot/{hypothesis_tests,event_study,
   phase_summary,coverage}.csv` + 3 figures. Rerun with `python scripts/pilot/test_hypotheses.py`.
2. **Historical industrial-overlap chain** (USA-JPN-KOR-CHN Finger-Kreinin export similarity,
   1962-2024, cross-checked HS92 vs SITC) -- `outputs/exploratory/historical_overlap_chain.{csv,png}`.
   This was produced in response to a direct question earlier in this session, not part of the
   formal overhaul brief, but reused directly as Section V.11 groundwork.
3. **Industrial crossover candidates** (shipbuilding, semiconductors, batteries; displays flagged
   unreliable) -- `outputs/exploratory/industrial_crossovers_hs92.png`,
   `outputs/exploratory/crossover_*.csv`, `data/processed/industrial_crossover_candidates.csv`.
4. **Literature verification** -- 8/8 named citations checked, plus 2 more found during
   verification (Renshon 2016, 2017). See `references/references.bib` for each entry's
   verification note and source.
5. **Data access reconnaissance** -- real, checked findings on WVS, Pew, CEPII BACI, EAI/Genron,
   Japan MHLW and Korea Statistics Korea marriage statistics. See
   `docs/data_access_requirements.md`.

## What preliminary results were obtained

The three reliable industrial crossover dates (HS92, 1995-2024, global export market share):

| Pair | Industry | Crossover year | Years sustained through 2024 |
|---|---|---|---|
| Japan -> Korea | Shipbuilding | ~2002 | 23 |
| Japan -> Korea | Batteries | ~2010 | 15 |
| Japan -> Korea | Semiconductors | ~2013 | 12 |
| Japan -> Korea/China | (China overtakes Japan in all three, later) | ships ~2009, batteries ~2004-5, semiconductors ~2007-8 | see CSVs |
| Korea -> China | Shipbuilding | ~2021 (weaker, 4 yrs, preceded by a non-sustained 2011-12 near-crossover) | 4 |
| Korea -> China | Semiconductors | ~2003 (value-share only -- NOT a capability claim, see caveat) | 21 |
| Korea -> China | Batteries | ~1996 (divergent-growth pattern, not catch-up-and-overtake -- see caveat) | 28 |

These are **material-status (T1) candidates only**. No recognition data exist yet for either side
of the jpn_kor case's incumbent (Japan), so no T2/T3/T4 turning point or recognition-lag estimate
was computed for jpn_kor. For kor_chn, the existing Korean-language corpus could in principle
support a T2/T3 analysis around these dates, but that analysis was **not run** in this pass (it
would require building the new multilingual/peer-vs-achievement classifier first, per
`docs/measurement_protocol.md`, since reusing the legacy H/V/C dictionary would violate the
brief's explicit instruction not to treat it as the primary measure).

## What remains unverified

- 7 of 9 literature topic areas (`docs/literature_review.md` Section 3).
- Whether EAI/Genron microdata (not just published report tables) are actually obtainable.
- Whether a Pew Global Attitudes raw-microdata download page exists (only published report PDFs
  were confirmed).
- OECD TiVA and WIPO access mechanics (not searched).
- Whether the shipbuilding/semiconductor/battery crossover dates would hold up under a
  display-quality-equivalent HS6-level check via CEPII BACI (not yet downloaded).

## What you (the user) need to do manually

Ranked by consequence, from `docs/data_access_requirements.md`:

1. Decide whether to commission/acquire a Japanese-side government and media text corpus. This is
   the single largest remaining gap and blocks the jpn_kor case's recognition side entirely.
   Candidate sources not yet checked for access: Japan MOFA, Diet full-text (beyond the existing
   mention-count series), major Japanese newspapers.
2. Attempt direct contact with EAI or Genron NPO about response-level survey data access (the
   published report tables are real and usable for descriptive work now; microdata would allow
   proper statistical modeling, e.g. the age-disaggregated test M4 needs).
3. If HS6-level trade resolution is wanted, download CEPII BACI (free, no registration) --
   mechanical work, no design decision needed.
4. Decide the project's Chinese-language scope (the brief lists it as "where necessary" --
   whether the kor_chn case needs China's own self-positioning text, or only Korea's text about
   China, is a scope call only you can make).
5. Decide whether to continue the literature search (7 topic areas remain) before or after further
   empirical work -- the brief's own Gate 1-3 structure (Section IX.22) suggests measurement
   feasibility (Gate 1) should be resolved first, which argues for prioritizing the Japanese
   corpus (item 1) over finishing the literature review.

## The three most consequential methodological risks

1. **The jpn_kor case cannot be tested as specified without new data acquisition of a scale
   comparable to the original Korean-corpus collection effort.** Everything computed so far for
   jpn_kor is material-status-side only; the central question (does Japan's recognition lag
   Korea's material convergence) has no recognition-side data yet.
2. **Export-value market share conflates capability with assembly/re-export activity**, most
   acutely for China's semiconductor numbers (R003 in `docs/decision_log.md`). Any downstream
   claim using these crossover dates as T1 markers must carry this caveat forward explicitly or
   risk a serious interpretive error the brief itself warns against.
3. **Historical trade-data series are not uniformly reliable across revisions and time windows** --
   the pre-1992 SITC shipbuilding break (R002) was caught by comparing against independently known
   industry history; there is no guarantee other series (e.g., the not-yet-checked BACI data, or
   SITC series for other sectors not yet examined) do not have similar undetected breaks. Any
   future crossover analysis should repeat the same plausibility screen before reporting a date.

## The next five research actions, ranked

1. Acquire or scope a Japanese-side recognition corpus (jpn_kor case; see risk 1 above).
2. Finish the literature review (7/9 topic areas remain; see `docs/literature_review.md` Section 3
   for the exact next queries).
3. Build the new multilingual, peer-vs-achievement-distinguishing classifier
   (`docs/measurement_protocol.md`) -- needed before any T2/T3 estimate can be computed for
   kor_chn, where the Korean-side text already exists.
4. Download CEPII BACI and re-verify the three reliable crossover dates at HS6 resolution as a
   robustness check.
5. Contact EAI/Genron about microdata access; if unavailable, build the descriptive (report-table-
   level) status-perception series as a fallback, clearly labeled as report-level rather than
   response-level evidence.
