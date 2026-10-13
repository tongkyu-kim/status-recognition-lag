# Overnight execution log

Append-only, updated incrementally as work proceeds. Started 2026-10-14. Baseline: 80/80 tests
passing, HEAD at `6e7c594`, no uncommitted changes.

## 00:00 -- Start

Rapid audit confirms the prior overhaul's state matches its own report
(`outputs/reports/research_overhaul_report.md`). Proceeding directly to Priority 1 (recognition-
side data) per the execution brief's instruction not to re-litigate the audit or architecture.

Plan for this session, in priority order (adapted to what is actually reachable without
credentials or paywalled access):

1. Japanese Diet full-text corpus (NDL API, open, no key -- the existing `jp_diet` source only has
   yearly mention *counts*, not text; extending to full text is the single highest-value acquisition
   step available without credentials).
2. Check Japan MOFA / government press-release archive accessibility (analogous to the existing
   `kr_mofa` collection).
3. Korea->China recognition extraction from the EXISTING 91k-document Korean corpus (no new
   acquisition needed -- highest-leverage reuse).
4. Build and run an LLM-assisted multilingual classifier (this agent, as the model) on sampled
   passages, R0-R5 scheme, explicitly labeled provisional/unvalidated.
5. Build the 400-600 item stratified annotation-ready sample (empty human-label fields).
6. Survey data: fetch exact question wording / years / published figures for EAI/Genron, Pew,
   Asan Institute via WebFetch (report-level, not microdata -- microdata access was already found
   to be unconfirmed in the prior session).
7. Recognition time series construction.
8. Turning-point comparison against the already-verified material crossover dates.
9. Figures, manuscript, final report.

## Sequence actually executed

1. Audited baseline (80/80 tests, clean git state) -- confirmed, no rework needed.
2. Checked existing jp_diet source: only yearly counts existed (1980-2010), not full text. Its own
   acquisition script docstring already named full-text collection as the deferred next step.
3. Scoped the full-text pull to the pre-filtered catchup/competition/economy queries (1,642+6,603
   records across 1980-2024) rather than the generic "korea" query (32,521 records, too broad) --
   see `docs/decision_log.md` R006.
4. Ran `acq_jp_diet_fulltext.py` in the background (~5 min, NDL API, 2s/request polite interval)
   while classifying Korea-China sentences from the ALREADY-existing corpus in parallel (no
   acquisition needed for that half).
5. Built `jp_diet_speeches.parquet` (10,742 deduplicated speeches). Found the existing
   `split_sentences` does not handle Japanese sentence boundaries (no space after `。`); added
   `split_sentences_ja` with tests rather than changing the Korean-tuned shared function.
6. Built stratified, economic/industrial-keyword-filtered samples for both cases (200 JPN-KOR,
   300 KOR-CHN), matching the brief's stratification instruction (case/period/source).
7. Classified 175/200 and 168/300 (169 raw, 1 direction-mismatch) items by direct reading, in
   batches, checkpointing to CSV after each batch (per §13.4's incremental-checkpoint instruction).
   Caught and fixed: a CSV-quoting bug (unescaped commas in notes, 2 rows) found via a downstream
   parser error; an item-indexing slip (one placeholder row) found by inspection.
8. Built period-level recognition time series and compared against the three verified crossover
   dates; produced `recognition_vs_crossovers.png`.
9. Fixed two scripts carried over from the prior session that had hardcoded machine-specific paths
   and had been accidentally saved inside the gitignored `outputs/` tree -- moved to
   `scripts/exploratory/`, now portable and rerun-verified.
10. Added `.gitignore` exceptions for the newly-produced hand-authored artifacts (recognition
    classifications, manuscript, this report) that would otherwise have been silently excluded by
    the existing "regenerable outputs are not tracked" convention -- these are NOT regenerable by
    any script (they are this agent's own read-and-judge output), so the convention does not apply
    to them.
11. Wrote the manuscript and this final report, run full QA, committed locally.

## Time allocation (approximate, against the brief's suggested 35/25/15/10/10/5 split)

Actual: corpus acquisition ~20%, classification ~45%, crossover audit ~10%, time-series/figures
~10%, manuscript+reports ~15%, survey work ~0% (investigated in the prior session only, not this
one). Classification took a larger share than planned because doing it by direct reading --
genuinely, item by item, with a written justification each time -- is slow; the alternative
(a fast heuristic classifier) was deliberately not used because the brief explicitly requires the
model/method to be disclosed and provisional labels not overclaimed, and a cheap heuristic would
not have produced the individually-quotable findings (the 2008 vs. 2020 shipbuilding quotes) that
turned out to be this session's strongest evidence.
