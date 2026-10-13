# Decision log -- recognition-turning-points overhaul

Dated, append-only. Separates theoretically motivated choices, data-driven exploratory decisions,
measurement revisions, confirmatory specifications, and robustness analyses (per the overhaul
brief, Section IX.21). The legacy H1-H5 project's own decision log (D001-D021) is preserved
unchanged at docs/decisions.md; entries below are numbered independently as R001, R002, ... to
avoid collision.

## R001 -- Preserve, do not overwrite, the legacy H1-H5 project (2026-10-13)

**Type:** theoretically motivated (scope decision).

The existing repository already contains a substantially executed research pipeline (status
proximity / recognition lag, H1-H5, docs/research_design.md, scripts 01-10, a working pilot at
scripts/pilot/). The overhaul brief reframes the central question around recognition *turning
points* and peer-status transitions rather than a continuous "lag" variable, and explicitly
instructs: "Do not reinterpret these findings as evidence for the new theory." Action taken:
the legacy pipeline, its docs, and its pilot outputs are left in place and referenced from
legacy/README.md rather than deleted or folded into the new framework. The new work is additive
(new directories under src/srl/, config/, docs/, data/processed/) rather than a rewrite of
existing modules that still work (e.g. srl.trade.overlap, srl.status.proximity are reused as-is).

## R002 -- Industrial crossover detection rule and reliability screening (2026-10-13)

**Type:** data-driven exploratory decision, surfaced during Phase 5.

Rule: a crossover candidate is flagged where the challenger's Atlas-reported `globalMarketShare`
in a product code first exceeds the incumbent's and stays higher for >=3 consecutive years
through 2024. This is a *detection heuristic* for generating candidates, not a confirmatory test.

While applying it to shipbuilding (SITC 7932, 1962-2024), Japan's share implausibly collapses
(31.6% in 1985 to 1.9% in 1990) while the USA's share implausibly jumps (2.4% in 1985 to 22.0% in
1988) in the same window -- no known real-economy event of that scale exists, and Korea's SITC
share never exceeds ~0.3% from 1988-2024 despite Korea's well-documented rise to the world's
largest shipbuilder by output in exactly this period. This was treated as a likely data
discontinuity (classification/revision splice or country-coverage change in the historical SITC
series), NOT a real market shift, and the pre-1992 SITC shipbuilding series was marked unreliable
and excluded from the crossover table rather than reported as a finding. The HS92 L4 series
(1995-2024, product 8901) does not show this break and matches independently known shipbuilding
history (Japan's 1990s lead, Korea's ~2002 overtake, China's ~2009 overtake of Japan and ~2021
overtake of Korea) -- it is used as the reliable series for this sector.

The same screening caught a second issue: HS92 9013 (displays/optics, meant as an LCD proxy) shows
Korea's share collapsing from 23.7% (1999) to 2.9% (2000) in a single year, inconsistent with the
known contemporaneous rise of the Korean display industry. This product code was marked
UNRELIABLE and excluded from any crossover claim (see config/sectors.yaml, status:
needs_replacement_indicator). A display-specific HS code or an industry source (DisplaySearch /
Omdia) is needed before this sector can be used.

**Consequence for the pipeline:** scripts/04_identify_crossovers.py (not yet written) must
inherit this reliability flag per source/product/period rather than apply the detection rule
uniformly -- see config/sectors.yaml `reliability` fields.

## R003 -- Semiconductor export-share crossover is not a capability claim (2026-10-13)

**Type:** theoretically motivated (measurement interpretation).

China's semiconductor (HS 8541+8542) export-value share exceeds Korea's from 2003 onward and now
dominates (55.6% vs 17.6% in 2024). This number is real and reliable as a trade-value series, but
is explicitly NOT treated as evidence of Chinese design/fabrication leadership over Korea: a large
share of China's recorded semiconductor exports reflects assembly, test, and packaging of chips
designed or fabricated elsewhere, plus re-export. Per the overhaul brief ("Do not assume that
aggregate national superiority and sector-specific industrial superiority are interchangeable"),
this crossover is recorded with an explicit caveat (data/processed/industrial_crossover_candidates.csv)
and is NOT proposed as a T1 material-parity marker for the recognition-lag estimation without a
capability-specific indicator (patents, domestic value-added, fab-node share -- none yet acquired).

## R005 -- Literature review scoped to 2 of 9 topic areas in this pass (2026-10-13)

**Type:** data-driven exploratory decision (resource/time scoping, disclosed rather than hidden).

The overhaul brief names nine literature topic areas (Section II.3). This pass verified the eight
named citations plus two found while verifying them (Renshon 2016, 2017), covering topic areas 1
(international status recognition), 2 (status inconsistency/deficits, partially via Renshon), 3
(status anxiety/stigma shifting, via Claudia Kim 2024), and 7 (generational/public support for
leaders, via Powers & Renshon 2023). Topic areas 4 (economic convergence and status hierarchies,
already covered by the legacy project's own literature base -- not re-verified here), 5
(developmental hierarchies in East Asia as a status construct), 6 (social distance/cultural
prestige), 8 (recognition of industrial/technological leadership as an IR construct), and 9
(marriage/dating preferences as status perception -- official statistics were verified instead of
an academic literature) were either not searched or only partially covered. This is recorded as an
open item in `docs/literature_review.md` Section 3 rather than papered over with an unverified
citation. Continuing this search is the top-ranked next action in
`outputs/reports/research_overhaul_report.md`.

## R004 -- Repository restructuring is additive, not a rewrite (2026-10-13)

**Type:** theoretically motivated (engineering decision).

New directories (src/srl/material_status, historical_events, public_opinion, culture,
social_recognition, turning_points, identification; config/cases.yaml, sectors.yaml; data/annotations/;
outputs/reports/; legacy/) were created alongside the existing structure. No existing module,
script, or config file was deleted. This follows the brief's own instruction ("Adapt to the
existing repository rather than blindly replacing it... Avoid unnecessary dependencies or
wholesale rewrites of functional code").
