# When Does a Rising State Become a Peer? Economic Catch-Up, Recognition Resistance, and Status Transitions in East Asia

**Status: exploratory draft.** This manuscript reports work completed in a single autonomous
research session (2026-10-13/14). It distinguishes verified descriptive findings from
exploratory, single-pass LLM-assisted classifications throughout, per the labeling discipline in
`docs/measurement_protocol.md`. No section claims validation this project has not performed.

## 1. Introduction

Established powers do not always grant peer status to states that have materially converged on
them. Japan's elite discourse, as this paper documents, continued describing Korea as "catching
up" and "right behind" in shipbuilding as late as 2008 -- six years after Korean firms had already
overtaken Japanese firms' global export share in that industry, by the project's own audited
trade data. By 2020, the same discourse had shifted to an unambiguous admission that Japan's
"top share until the 1990s" had been "largely taken" by Korean and Chinese competitors. The gap
between these two moments is the empirical object of this paper: not whether recognition lags
material convergence, but when, by how much, and under what conditions.

## 2. Literature and theoretical framework

Summarized from `docs/literature_review.md` and `docs/theoretical_framework.md` (verified
citations only; see `references/references.bib`). Status is treated as relational and granted,
not possessed (Duque 2018); resource-recognition gaps are the expected case, not an anomaly to
regress away (Røren and Beaumont 2019); the behaviorally consequential quantity is a *status
deficit* -- material rank minus recognized rank -- evaluated within a local reference group, not a
global hierarchy (Renshon 2016, 2017). Five competing mechanisms (M1-M5) are specified in
`docs/theoretical_framework.md`; the strongest literature anchor found is Claudia Kim's (2024)
"stigma shifting," which this paper's closing section returns to directly. Seven of nine
literature topic areas named in the original research brief remain unsearched (disclosed in
`docs/literature_review.md` §3); this paper does not claim comprehensive coverage.

## 3. Case selection

Two primary cases: Japan's recognition of Korea (jpn_kor) and Korea's recognition of China
(kor_chn). Rationale, data availability, and the asymmetry between the two cases'
corpus coverage are in `docs/case_selection.md`.

## 4. Data and measurement

### 4.1 Material status

Global export market share (Atlas of Economic Complexity's own `globalMarketShare` field,
HS92 4-digit, 1995-2024) for shipbuilding (HS 8901), semiconductors (HS 8541+8542), and storage
batteries (HS 8507), for USA/JPN/KOR/CHN. A fourth candidate sector, displays/LCDs (HS 9013), was
screened and found unreliable (a noisy composite category plus an implausible one-year collapse
in Korea's series) and is excluded from all claims below. A fifth data quality issue -- an
implausible break in the pre-1992 SITC shipbuilding series -- was also caught and excluded. Full
audit trail: `data/processed/industrial_crossover_candidates.csv`, `docs/decision_log.md` R002-R003.

**Verified crossover dates** (challenger's export share exceeds incumbent's, sustained ≥3 years):

| Pair | Industry | Year | Years sustained (through 2024) |
|---|---|---|---|
| JPN→KOR | Shipbuilding | ~2002 | 23 |
| JPN→KOR | Batteries | ~2010 | 15 |
| JPN→KOR | Semiconductors | ~2013 | 12 |
| KOR→CHN | Batteries | ~1996 | 28 (divergent-growth pattern, not a reversal of KOR leadership -- see caveat below) |
| KOR→CHN | Shipbuilding | ~2021 | 4 (weaker; a non-sustained near-crossover in 2011-12 preceded it) |

**Caveats carried forward into the recognition analysis below:**
- The KOR→CHN semiconductor "crossover" (China's export value share exceeding Korea's since
  2003) is explicitly NOT treated as a capability-parity marker: a large share of China's recorded
  semiconductor exports reflects assembly/test/re-export rather than design or fabrication
  capability (`docs/decision_log.md` R003). It is excluded from the quantitative comparison below.
- The KOR→CHN battery "crossover" (1996) reflects both countries starting from a similarly small
  base and China growing faster throughout, not Korea losing an established lead -- Japan, not
  Korea, was the real incumbent displaced in this industry.

### 4.2 Recognition (media/elite discourse)

**Japan→Korea.** A new corpus: 10,742 Japanese National Diet speeches (1980-2024) mentioning
Korea in economic/catch-up/competition-themed full-text searches, acquired via the National Diet
Library's public API (`scripts/acquire/acq_jp_diet_fulltext.py`, `build_jp_diet_corpus.py`). A
new Japanese sentence splitter was added (`src/srl/text/segmentation.py:split_sentences_ja`,
tested) since the existing splitter does not handle Japanese punctuation correctly. 5,594
sentences matched Korea + an economic/industrial keyword filter; 200 were drawn into a stratified
sample (`data/annotations/jpn_kor_recognition_sample.csv`), of which **175 were classified** by
this agent (`data/interim/recognition/jpn_kor_llm_classified.csv`).

**Korea→China.** Reused the existing Korean government corpus (kr_mofa, kr_motie,
kr_presidential_office; ~91k documents, pre-collected in the legacy project) via its existing
sentence-level extraction. 300 economically/industrially relevant China-mentioning sentences were
drawn into a stratified sample (`data/annotations/kor_chn_recognition_sample.csv`), of which
**168 were classified** (direction-consistent; `data/interim/recognition/kor_chn_llm_classified.csv`).

**Classification scheme:** R0 (no status attribution) through R5 (explicit challenger
superiority), per `docs/measurement_protocol.md`, with separate dismissive/stereotyping/
threat-coexists flags and a direction_mismatch flag (for sampled sentences that actually describe
the *reverse* direction, e.g. a Chinese official's praise of Korea appearing in a Korea-published
document). **Method: this agent (Claude, single pass, 2026-10-14), reading each sampled passage
directly and assigning labels with a written justification per item.** This is explicitly a
provisional, LLM-assisted classification under the brief's own terms (Section 5.5) -- it has NOT
been checked against human-coded labels, inter-rater reliability cannot be computed (there is no
second rater), and the annotation-ready files with empty human-label columns remain available for
that validation step. Combined R-distribution:

| | R0 | R1 | R2 | R3 | R4 | R5 |
|---|---|---|---|---|---|---|
| kor_chn (n=168) | 111 | 16 | 7 | 10 | 18 | 6 |
| jpn_kor (n=175) | 105 | 12 | 15 | 16 | 14 | 13 |

## 5. Empirical strategy

Sentences with R0 (no status attribution) are excluded from the period-level descriptive series
(they carry no information about recognition, per the brief's explicit instruction not to treat
absence as denial). For each 4-year period, two shares are computed over scored (non-R0)
sentences: **peer share** = (R4+R5)/scored, and **competitive-threat share** = R3/scored.
`scripts/exploratory/build_recognition_timeseries.py`. This is explicitly descriptive, not a
fitted model -- per-period n is frequently below 10 (see `outputs/exploratory/
{kor_chn,jpn_kor}_recognition_timeseries.csv` for exact counts per period), so no inferential
claim is made from period-to-period differences. No segmented-regression, change-point, or
event-study model was fit in this pass; that is explicitly left as future work (Section 8).

## 6. Preliminary findings

**Figure 1** (`outputs/exploratory/historical_overlap_chain.png`): export-structure overlap (Finger-
Kreinin index) rose for all three pairs in the USA→Japan→Korea→China chain from the 1960s to
today, but as a shared upward drift rather than a strict relay -- USA-Japan and Japan-Korea overlap
plateaued near their historic highs (~60-64) rather than declining as the next pair's overlap
rose, and Korea-China overlap, while rising every decade with no interruption, has not yet reached
the ceiling the earlier pairs reached.

**Figure 2** (`outputs/exploratory/industrial_crossovers_hs92.png`, Section 4.1): the three
verified crossover dates above.

**Figure 3** (`outputs/exploratory/recognition_vs_crossovers.png`): peer-recognition share and
competitive-threat share by period, with verified crossover dates marked.

**Japan's recognition of Korea, read against the shipbuilding crossover (~2002):** peer share is
low and essentially flat across the periods spanning the shipbuilding crossover and the following
decade (0.30 in 2000-03, 0.36 in 2004-07/2008-11, 0.33 in 2012-15) despite Korea's export share
having already and durably overtaken Japan's by 2002. It does not rise clearly until the 2020-23
period (0.67). Two individually-read quotations bracket this pattern directly: in 2008, a Diet
member described Korea as merely "catching up" and "right behind" Japan in shipbuilding
(`jpnkor_0113`) -- six years after the trade data show Korea's share had already overtaken Japan's;
in 2020, a different Diet member explicitly conceded Japan's "top share until the 1990s" had been
"largely taken" by Korean and Chinese firms (`jpnkor_0170`). Read together with the period series,
this is consistent with the paper's central hypothesis -- a material crossover in 2002 followed by
a recognition shift roughly a decade or more later -- but the n in each period (3-14) is too small
to support this as more than a directional, hypothesis-consistent pattern pending a validated
measure.

**Korea's recognition of China** shows a different, non-monotonic pattern: peer share rises
steadily from 1988 (0.00) to a peak of 0.75 in 2008-11, *before* the battery crossover's
conventional dating would predict (1996 is comparatively early in the series and peer share was
already 0.33-0.39 by then) -- then **declines** to 0.22 by 2020-23 even as China's material
position continued strengthening, with competitive-threat share rising concurrently (0.33 in
2020-23). This does not fit a simple "material convergence causes monotonically rising
recognition" story. It is consistent with a reading in which Korea's recognition of China shifted
from achievement-admiration (1990s-2000s, when several sampled MOFA documents explicitly state
China "surpassed Japan" -- `korchn_0172`, `korchn_0173`, both 2011) toward a more anxious, mixed
peer-plus-threat framing in the most recent period, including explicit 2024 concern about Chinese
universities aggressively recruiting Korean semiconductor/display/battery researchers
(`korchn_0290`). Whether this reflects a real shift in Korean elite sentiment or an artifact of
small per-period samples cannot be determined from this pass.

**A recurring attributional pattern** appears across both corpora and deserves explicit note: both
Japanese and Korean officials frequently acknowledge a challenger's rising capability while
attributing it to external factors (state subsidy, licensing leakage, cheap labor) rather than the
challenger's own merit (e.g. `jpnkor_0164`, `jpnkor_0181`, `jpnkor_0195`, `korchn_0290`). Some of
these attributions are independently documented real factors (e.g. Chinese state support for
shipbuilding and batteries is well established); this project does not have the evidence to judge,
case by case, whether a given attribution is accurate explanation or motivated minimization, and
flags this explicitly as an unresolved measurement question for Section 8 rather than coding it
as "dismissive" by default.

## 7. Discussion

Read together, the shipbuilding bracket (2008 vs. 2020 quotations) and the two period series are
the paper's strongest evidence for the central hypothesis -- that recognition can lag material
convergence by a decade or more, specifically in a case (Japan-Korea shipbuilding) with one of
this project's most reliable crossover dates. The Korea-China pattern complicates any simple
"recognition lags, then catches up" story: it suggests recognition can also *decline* after an
early peak, with competitive-threat framing rising in its place, which the original research
brief's six-way distinction (neglect / dismissal / status denial / delayed recognition / status
reproduction / threat acknowledgment) anticipates better than a single-lag model does. Claudia
Kim's (2024) stigma-shifting mechanism (M5) is the closest existing theorization of this kind of
dynamic shift and would be the natural next mechanism to test directly against these data, once a
validated recognition measure exists.

## 8. Limitations and next steps

This is explicitly a single-pass, unvalidated, exploratory classification. The most consequential
limitations: (1) no human-coded validation sample has been scored against these labels --
inter-rater reliability is literally unmeasured; (2) per-period sample sizes are frequently below
10, so the period series should be read as hypothesis-generating, not hypothesis-confirming; (3)
the Japan-Korea corpus is parliamentary debate (which includes partisan and rhetorical framing by
design) while the Korea-China corpus is government press material (more institutionally
controlled) -- the two are not measuring exactly the same kind of discourse, and no attempt was
made in this pass to harmonize or control for that difference; (4) the semiconductor crossover for
Korea-China was deliberately excluded from the quantitative comparison because export value
conflates capability with assembly/re-export, but no analogous check was performed for every
individual recognition-classified sentence that discusses semiconductors; (5) survey data (EAI/
Genron, Pew) were investigated for access terms only (`docs/data_access_requirements.md`) and are
not yet incorporated into any figure here. The next five ranked actions are in
`outputs/reports/overnight_research_results.md` §H.
