# Mechanism discovery report: beyond recognition lag

2026-10-14. Exploratory pilot. No independent human validation exists for any classification
referenced here (original R0-R5 labels or the new codings introduced in this pilot) -- see
`docs/measurement_protocol.md`. All figures/tables are reproducible by rerunning the scripts named
in each section from the repository root with `PYTHONPATH=src`.

## 0. What this pilot does NOT do

Per the assignment brief: it does not repeat the turning-point/crossover-date analysis (preserved
unchanged -- see `outputs/manuscript/manuscript_exploratory.md` §6a and
`scripts/exploratory/test_turning_point_hypothesis.py`, not touched in this pilot), does not
search for a better-fitting crossover date or window, and does not pool the two corpora without
flagging their different source composition.

## 1. Research foundation (Phase 1 inspection)

Confirmed before new work began: the existing manuscript tests ONE mechanism (material crossover
→ recognition transition, via a PRE/EARLY-POST/LATE-POST window test). It does not test whether
achievement acknowledgment coexists with hierarchy-preservation (P1), whether dismissal converts
to threat-framing rather than fading (P2), whether institutional position predicts framing (P4),
or whether attention volume and recognition move together or apart (P6). These four are genuinely
new tests, not restatements.

**Sampling-frame caveat, carried through every section below:** the 343 classified sentences are
a *stratified* draw (by 4-year period) from a keyword-filtered relevant pool (5,594 jpn_kor
sentences; 300 of 32,423 kor_chn sentences), not a random sample of all parliamentary/government
discourse. Any proportion reported below is a proportion of the *classified subset*, not an
estimate of prevalence across the full corpus, and should not be read as one.

## 2. Executed pilots

### P1 -- Recognition without status equality

**Proposition:** among achievement-acknowledging sentences (R2/R4/R5), a recurring subset will
also contain language that preserves hierarchy on a different dimension (continued-superiority
claims, external-cause attribution for the rival's gain, delegitimizing labels).

**Method:** every R2/R4/R5 item in both corpora (n=42 jpn_kor, n=31 kor_chn) was re-read a second
time, specifically for this pattern, and coded as a new binary variable with a named mechanism
and quote where positive (`data/interim/recognition/p1_hierarchy_coexistence_coding.csv`).
`scripts/exploratory/new_mechanisms/p1_hierarchy_coexistence.py`.

**Result:**

| Case | Achievement items | Hierarchy-coexists | Share |
|---|---|---|---|
| jpn_kor | 42 | 9 | 21.4% |
| kor_chn | 31 | 0 | 0.0% |

Fisher's exact test (jpn_kor vs kor_chn rate): **p = 0.0082**.

Six distinct mechanisms identified in jpn_kor: *superiority_in_other_dimension* (3 -- e.g.
`jpnkor_0176`, 2021: "Japan's advantage in internal ship quality remains unshaken" while conceding
price competitiveness to Korea/China), *subsidy_attribution* (2 -- e.g. `jpnkor_0170`, 2020:
share loss attributed to "state-supported" rivals), *explicit_qualification*, *delegitimizing_
label*, *entitlement_framing* ("regain its FORMER glory," `jpnkor_0177`), and *external_cause_
attribution* (technology "leaked" via licensing/regulation, `jpnkor_0195`).

**Within-corpus finding (not confounded):** the pattern is real and substantively diverse within
jpn_kor -- 9 independently-mechanisms-coded examples is not a fluke of one recurring phrase.

**Cross-corpus finding (CONFOUNDED, flagged before the result was computed):** the kor_chn rate
is literally zero across 31 achievement items. This is at least as plausibly a **genre effect**
as a theoretical difference: Japanese Diet speech is adversarial parliamentary debate where
ministers are pressed to explain decline and have institutional incentive to qualify or deflect;
Korean MOFA/MOTIE/Presidential material is controlled official press output, a genre that
structurally avoids defensive hedging. This pilot cannot separate the two explanations with the
data in hand -- see §6.

### P2 -- Competitive threat as a substitute for hierarchical dismissal

**Proposition:** early discourse is dominated by subordinate/dismissive framing (R1); later
discourse shifts toward competitive-threat framing (R3) even where dismissal recedes -- i.e. the
rival stops being "backward" and starts being "dangerous," which recognition-lag alone does not
predict (recognition-lag predicts R1 recedes as R4/R5 rises, with no claim about R3).

**Method:** each corpus split at its OWN median classified-sentence year (a rule fixed by sample
construction, not chosen after looking at results -- jpn_kor: 2010; kor_chn: 2002).
`scripts/exploratory/new_mechanisms/p2_dismissal_to_threat.py`.

**Result (R1-vs-R3 composition only, early vs late):**

| Case | Early R1/R3 | Late R1/R3 | Fisher's exact p |
|---|---|---|---|
| jpn_kor | 9 / 8 | 3 / 8 | 0.253 |
| kor_chn | 12 / 2 | 4 / 8 | **0.014** |

kor_chn shows a significant, substantial composition shift: subordinate framing drops from 12 to
4 instances while threat framing rises from 2 to 8, specifically among the sentences that are
*either* subordinate *or* threat-framed (i.e., not diluted by the many neutral/peer-framed
sentences). jpn_kor shows the same direction but does not reach significance at this sample size.

**This is a genuinely different claim from the turning-point result.** The turning-point test asks
whether peer share (R4+R5) rises; this test asks what *dismissal is replaced by*, and finds
(for kor_chn, significantly) that it is not primarily replaced by peer-equality language but by
threat language -- consistent with "competitive recognition" (Phase 4's named alternative) rather
than straightforward "recognition adjustment."

### P4 -- Institutional heterogeneity (Japan Diet only; Korean corpus has no comparable speaker metadata)

**Proposition:** government/ruling-coalition speakers show higher peer-recognition share than
opposition speakers.

**Method:** classified jpn_kor sentences joined to speaker/party/chamber metadata already captured
at sampling time (no new acquisition). LDP (自由民主党, including compound coalition labels) vs.
every other named party vs. unaffiliated-or-missing (a documented simplification, not a validated
government/opposition split -- see script docstring for why a fuller historical-coalition
resolution was not attempted). `scripts/exploratory/new_mechanisms/p4_institutional_heterogeneity.py`.

**Result:** LDP peer share 0.44 (n=16 scored) vs. other-party 0.34 (n=35 scored), Fisher's exact
**p = 0.547** -- not significant. Chamber (House of Representatives vs. Councillors) shows
essentially no difference (0.389 vs. 0.382).

**This is a genuine, informative null.** The proposition's direction is numerically present (LDP
higher) but nowhere near significant at this sample size, and the chamber split shows no
detectable difference at all. Institutional position is not a strong, easily-detected predictor
of recognition framing in this sample -- a useful constraint on future theorizing even though it
does not itself advance a new mechanism.

### P6 -- Attention vs. recognition

**Proposition:** discourse volume (attention) and peer-recognition share move largely
independently; a volume spike need not mean a recognition shift, and vice versa.

**Method:** attention = ALL 10,742 full-text Diet speeches matching the original acquisition
queries (not just the 5,594-sentence relevant pool or the 175 classified items) -- the broadest,
least-filtered volume measure available. Recognition = peer share among classified sentences, same
4-year periods as the turning-point analysis. `scripts/exploratory/new_mechanisms/
p6_attention_vs_recognition.py`; figure at `outputs/exploratory/new_mechanisms/
p6_attention_vs_recognition.png`.

**Result:** Pearson r = **-0.634** across 10 period-level observations (descriptive only -- 10
points is not a basis for inference). If anything, periods with MORE speeches about Korea have
LOWER peer-recognition shares, not higher -- the opposite of a naive "more attention = more
recognition" story, and consistent with volume spikes often being driven by friction events
(trade disputes, territorial disputes) that are not occasions for peer-status language. The
sharpest instance: 1996-99 had the highest speech volume in the entire series (1,276) with
peer-share effectively flat (data not independently classified for that exact period, but the
surrounding periods show no corresponding rise), while 2020-23's peer-share jump (0.667) occurs
with volume well below the series peak.

## 3. Qualitative supplements (evidence mined from existing coding, not new quantitative tests)

### P5 -- Triangular comparisons

The clearest, most theoretically load-bearing example remains `jpnkor_0030` (1986): PM Nakasone
telling Reagan that Japan now receives the same flow of cheaper imports from Korea/Taiwan that the
US once received from Japan -- an explicit, self-aware three-way historical parallel (USA→JPN→KOR)
from a head-of-government quotation, not an inference. Two further examples show Korea/China
grouped at PEER tier with established powers in the SAME sentence: `jpnkor_0132` (2011, grouped
with US/Europe on state-led export promotion) and `jpnkor_0147` (2015, grouped with
Australia/ASEAN/India as sharing "universal values and strategic interests"). These are read as
supportive, suggestive evidence for a triangular/relational status construction, but were not
converted into a systematic coded variable in this pass -- doing so properly would require
re-reading the FULL 5,594-sentence pool (not just the 343 classified items) for explicit
multi-country comparisons, which was judged lower priority than the four quantitative pilots above
given the session's time budget.

### P8 -- Persistence of historical leadership narratives

Four genuine hits, all shipbuilding/technology-specific and all from 2020 onward:
`jpnkor_0030` (1986, see above), `jpnkor_0170` (2020, "proudly held TOP SHARE... until the
1990s"), `jpnkor_0177` (2021, "REGAIN its former glory" -- explicitly concedes the glory was
lost while asserting a normative claim to reclaim it), and `jpnkor_0195` (2024, LNG-carrier "proud/
vaunted technology" narrative). The clustering of all the strongest examples in 2020-2024 is
itself informative: historical-leadership invocation appears to intensify, not fade, as material
decline becomes undeniable -- consistent with P8's proposition that past leadership is invoked
precisely *to maintain symbolic distinction* once the material basis for current leadership is
gone, rather than being simple nostalgic description.

### P3 -- Sectoral vs. national recognition (brief note, not a full pilot)

Only 6-8 classified items carry an explicit sector tag (shipbuilding) in either corpus -- too few
for any statistical test. The shipbuilding-tagged items skew heavily toward R3/R5 (competitive
threat / explicit admission), which is suggestive that sector-specific material evidence
(a verifiable, named crossover) produces sharper, more explicit recognition language than general
economic-competitiveness discourse -- but this observation is based on 6-8 items and is reported
as a hypothesis for future targeted sampling, not a finding.

## 4. Alternative explanations considered for each pilot

| Pilot | Primary mechanism tested | Alternative(s) evaluated | Can this pilot distinguish them? |
|---|---|---|---|
| P1 | Hierarchical differentiation (partial recognition) | Attention/genre effect (adversarial debate elicits more qualification than press releases) | No -- genuinely confounded; flagged explicitly, not resolved |
| P2 | Competitive recognition (threat replaces dismissal) | Recognition adjustment (dismissal simply fades as peer language rises) | Yes -- the two predict different R1/R3 trajectories, and the data favor competitive recognition for kor_chn |
| P4 | Institutional heterogeneity | Historical composition change (which parties exist/hold seats differs by era, confounding any era-based party comparison) | Partially -- the null result makes this moot for now, but a cleaner test would need era-stratified party comparison, not attempted here |
| P6 | Attention effects (volume ≠ salience/recognition) | Source-coverage artifact (NDL digitization is uneven across decades for institutional reasons unrelated to real-world salience) | No -- this pilot explicitly cannot rule out a digitization-coverage artifact and says so |

## 5. Measurement limitations (in addition to the pre-existing ones in `docs/measurement_protocol.md`)

- The P1 hierarchy-coexistence coding is a SECOND pass by the same single coder (this agent) who
  produced the original R0-R5 labels -- it is not independent in any sense; a different reader
  could reasonably code some of the 9 positive jpn_kor cases differently (several are judgment
  calls, e.g. whether "even if the plan's content is excellent" counts as hierarchy-preservation
  or simply an accurate qualifier).
- P2's early/late split uses the median of an already-small, non-random sample; a different
  stratified draw from the same relevant-sentence pool could shift the median year and change
  which sentences fall in which era.
- P4's LDP/other-party/unaffiliated split is a documented simplification that does not resolve
  actual historical coalition membership; a minister from a coalition partner answering on the
  government's behalf is coded as "other-party" here even when speaking in a government capacity.
- P6's attention measure inherits whatever coverage gaps exist in the NDL's own digitization of
  pre-1990s records; a period with fewer speeches in this dataset is not necessarily a period with
  fewer speeches in reality.

## 6. Cross-case implications

The single most important cross-case finding is methodological, not substantive: **P1's striking
cross-case gap (21% vs 0%) is most likely a product of genre, not theory**, and this pilot
recommends explicitly AGAINST citing the raw p=0.0082 as evidence that "Japan preserves hierarchy
more than Korea does." The right next step (§8) is a same-genre comparison -- either a Japanese
press-release corpus to compare against Japanese Diet debate, or (harder) a Korean National
Assembly debate corpus to compare against Korean MOFA press material -- before any cross-case
claim about this mechanism is defensible.

## 7. Recommendations for human validation

Highest priority: the 9 jpn_kor P1-positive items and a matched sample of 9 jpn_kor P1-negative
achievement items (18 total) -- this is small enough for a single human coder to do in under an
hour and would directly test whether the hierarchy-coexistence pattern is a real, reliably-
detectable signal or an artifact of this agent's own reading tendencies. Second priority: the
kor_chn R1-vs-R3 items used in the P2 test (14 pre + 12 post = 26 items) given the significant
result there carries the most weight of anything in this pilot.

## 8. What a future confirmatory analysis would need

1. A same-genre comparison corpus for P1 (see §6) before any cross-case claim.
2. A larger, non-stratified draw (or full-population classification within a bounded date range)
   for P2, to check the median-split result is not an artifact of which 4-year periods happened to
   be included in the original stratified sample.
3. A verified historical cabinet/coalition-composition dataset for a proper P4 test (this pilot's
   LDP/other split is not that).
4. Independent verification of the NDL's own digitization completeness by decade, to rule out the
   coverage-artifact alternative for P6.
