# Theoretical framework (v2): recognition turning points and peer status

*Supersedes the organizing framework of `docs/research_design.md` (legacy H1-H5) as the project's
primary theoretical structure. The legacy document is preserved unchanged; see `legacy/README.md`.*

## 1. Central question

When does an established state begin recognizing a rising state as its peer, and why might social
recognition lag behind material convergence?

## 2. The Korean concept of 무시 (musi) as the organizing phenomenon

무시 is treated as a family of related but empirically distinct phenomena, not a single variable:

| Component | What it means here | What would falsify its presence |
|---|---|---|
| **Neglect** | Insufficient attention to a documented achievement | Achievement is covered at a rate comparable to a matched baseline (Outcome A, Section V.12 of the design) |
| **Dismissal** | Achievement acknowledged but minimized | Coverage exists but framing actively downgrades significance (Outcome C) |
| **Status denial** | Subordinate status attributed despite material parity | A validated peer-recognition measure stays below threshold after T1 (material parity) |
| **Delayed recognition** | Parity eventually acknowledged, after a measurable gap | A validated peer-recognition measure crosses threshold at T3 > T1 |
| **Status reproduction** | A once-subordinate state reproduces the pattern toward a newer challenger | The same four components recur in a *different* dyad where the original challenger is now the incumbent |

These are measured as **separate outcomes** (Section III.5 below), not collapsed into one index.
Claudia Kim's "stigma shifting" (kim2024status) is the closest existing theorization of the last
component and is engaged directly in Section 4, M5.

## 3. Material status vs. perceived status (independent dimensions)

Material status: GDPpc, productivity, relative industrial production, export market share, RCA,
sector-specific technological leadership (patents, global market share in named industries),
measured from WDI / Atlas of Economic Complexity / Comtrade -- see `config/sectors.yaml` and
`data/processed/industrial_crossover_candidates.csv` for what is already computed for the Japan-
Korea and Korea-China pairs.

Perceived status: four domains (economic, political, cultural, social -- Section III.5.B of the
brief), each measured independently before any aggregation is attempted. No aggregate recognition
index is constructed in this pass; construct validity and dimensionality must be examined first
(this is an explicit brief requirement, Section III.5).

**Hard distinction, and the central measurement design problem of this whole project:**
*recognition of achievement* (an incumbent acknowledges the challenger leads in some domain) is not
*recognition as a peer* (the incumbent treats the challenger as a social/political equal). An
incumbent can concede the former while actively denying the latter -- this is precisely what the
musi "dismissal" and "status denial" components describe, and it is why `docs/measurement_protocol.md`
requires the media-classification scheme to separate these as different categories rather than
different scores on one scale.

## 4. Competing mechanisms (M1-M5)

Each mechanism's observable implication is stated so the mechanisms can be distinguished, not just
listed.

**M1. Material convergence.** Recognition tracks material capability with some lag but no
systematic resistance. *Observable implication:* recognition measures move with material-status
measures at a roughly constant lag across cases and domains; no residual effect of overlap,
interdependence, or stigma-shifting history once material status is controlled.

**M2. Status threat and defensive differentiation.** Established societies resist peer status when
the challenger threatens their standing. Powers & Renshon (powers2023international) show publics
respond to status-loss expectations with lowered political support, giving a plausible
micro-foundation: granting peer status may be politically costly for incumbent elites when the
public perceives threat. *Observable implication:* recognition lags more where competitive overlap
or geopolitical threat perception is high (this is close to, but conceptually prior to, the legacy
project's H3/H4 -- see `legacy/README.md` for why those specific legacy tests are not reused
directly).

**M3. Cultural normalization.** Exposure, familiarity, and prestige (media, tourism, popular
culture) raise recognition independent of economic convergence. *Observable implication:*
recognition changes correlate with cultural-exposure measures (e.g., the recent sharp rise in
Korean favorability toward Japan found in 2025 polling -- Asan Institute's favorability score
reaching an all-time high, EAI's favorable-view share rising from 28.9% in 2023 to 63.3% in 2025,
both found during the data-access search, see `docs/data_access_requirements.md`) even where
material convergence is flat over the same short window.

**M4. Generational replacement.** Recognition change reflects cohort turnover, not individual
belief revision. *Observable implication:* survey time series decomposed by birth cohort show
younger cohorts starting from a different baseline rather than older cohorts' views shifting in
place -- requires age-disaggregated survey data (not yet acquired; see data-access report).

**M5. Hierarchy reproduction.** States that once struggled for recognition reproduce similar
resistance toward newer challengers. Directly grounded in kim2024status's stigma-shifting
mechanism. *Observable implication:* Korea's recognition-withholding behavior toward China (if
found) should correlate, case-by-case, with the specific stigma dimensions Korea itself
experienced vis-a-vis Japan (not merely with generic "Korea had low status once") -- this is a much
stronger and more falsifiable test than an unstructured hierarchy-reproduction claim, and it is the
test Kim's framework licenses.

**Do not treat these as mutually exclusive.** The brief is explicit that no mechanism is assumed
correct; the turning-point design (Section IV) and the crossover design (Section V.11) are built to
produce evidence that can favor some combination over others, not to confirm a preferred one.

## 5. What this framework does not yet resolve

- No aggregation rule across the four perceived-status domains (economic/political/cultural/social)
  is proposed. This is deliberate (brief Section III.5) pending construct-validity work.
- M3 and M4 both require data not yet acquired (cultural-exposure time series; age-disaggregated
  survey panels). They are stated here as testable, not as tested.
- The mechanisms are not yet mapped onto formal turning-point definitions (T1-T4, brief Section
  IV.9) for each case pair -- that mapping belongs in `docs/identification_strategy.md` once the
  Japanese-side media corpus (currently missing, see `config/cases.yaml`) exists.
