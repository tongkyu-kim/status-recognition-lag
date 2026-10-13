# Case selection

Full case definitions and data-availability status: `config/cases.yaml`. This document states the
rationale only.

## Primary cases: Japan->Korea, Korea->China

Chosen because (a) material-status data already exist back to 1960-1962 for both pairs (WDI,
Atlas), (b) a Korean-language recognition corpus already exists and directly applies to the
kor_chn direction (Korea as incumbent), and (c) three independently verified industrial crossovers
with plausible timing exist for the jpn_kor pair (shipbuilding ~2002, batteries ~2010,
semiconductors ~2013 -- see `data/processed/industrial_crossover_candidates.csv`), giving the T1
(material parity) side of the turning-point design real anchor dates to work from.

**Asymmetry that must be fixed before jpn_kor can be fully tested:** the existing corpus measures
Korea's recognition of others, not Japan's recognition of Korea. For jpn_kor, Japan is the
incumbent -- the case needs a Japanese-side corpus (see `docs/data_access_requirements.md`
priority 1). Until that exists, jpn_kor analysis is limited to the material-status/crossover side
plus whatever survey evidence (EAI/Genron) can be accessed.

## Historical extension: USA->Japan

Included only as far as data support comparable operationalization, per the brief. Material data
exist (WDI from 1960, Atlas from 1962). No media/recognition corpus exists for either side (US
press/government text, or Japan's historical self-positioning text) and none was acquired in this
pass. Kept as a historical-extension candidate, not a primary case, consistent with the brief.

## Exploratory extension: Korea->Vietnam

Chosen as a contrasting case *without* clear material parity (Vietnam's GDPpc-PPP ratio to Korea
was 0.18-0.26 over 1998-2024 in the legacy pilot panel -- see `legacy/README.md` and
`outputs/pilot/coverage.csv`), to test whether the turning-point framework correctly predicts
*no* T3 (peer-recognition transition) where material convergence has not occurred. This is a
negative/falsification case, not expected to show recognition catch-up, and its value is
specifically in NOT finding a transition.

## Case not pursued: a homogeneous "ASEAN" case

The brief explicitly warns against treating ASEAN as homogeneous. No aggregate ASEAN case is
defined; Vietnam is examined individually. The legacy project's 12-partner ASEAN+China panel
remains available (`legacy/`) if a wider exploratory comparison is wanted later, but it is not
part of the new case structure.
