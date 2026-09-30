# Variable dictionary

All variables are defined at the partner-year level (Korea → partner *j*, year *t*) unless noted.
"Expected direction" refers to the hypothesized relationship in the main models. **Status:**
`planned` (defined, not built), `available` (source data in hand), `constructed` (built by a
pipeline script and validated). Every variable is currently `planned`.

Notation: *K* = Korea, *j* = partner, *X* = exports, *M* = imports, *s* = product share.

## Objective status / status proximity

| Variable | Concept | Operationalization | Expected direction | Source | Temporal resolution | Status |
|---|---|---|---|---|---|---|
| `gdppc_prox` | Income proximity | log(GDPpc_j / GDPpc_K), constant-price PPP (method configurable) | Recognition: nonlinear (H2, H5) | Candidate: WB WDI / IMF | Annual | planned |
| `productivity_prox` | Productivity proximity | log ratio of output per worker (definition TBD) | as above | Candidate: TBD | Annual | planned |
| `mva_prox` | Industrial capability proximity | log ratio of MVA per capita (or MVA share; choose one) | as above | Candidate: UNIDO / WDI | Annual | planned |
| `expy_prox` | Export sophistication proximity | log ratio of EXPY (Hausmann, Hwang & Rodrik 2007) | as above | Computed from HS trade + GDPpc | Annual | planned |
| `hightech_export_share_prox` | Technology-intensive export proximity | log ratio of high-tech export share | as above | Candidate: WDI / computed | Annual | planned |
| `patents_prox` | Technological capability proximity | log ratio of patents (counting rules TBD) | as above | Candidate: WIPO | Annual | planned |
| `status_proximity_composite` | Overall status proximity | Mean of pooled z-scores of selected components (≥ 2 observed) | as above | Constructed | Annual | planned |

## Competitive overlap

| Variable | Concept | Operationalization | Expected direction | Source | Temporal resolution | Status |
|---|---|---|---|---|---|---|
| `esi` | Export-structure similarity | Finger–Kreinin Σ_k min(s_jk, s_Kk), HS6 | Moderator: amplifies lag (H3) | Candidate: BACI / Comtrade | Annual | planned |
| `rca_overlap` | Comparative-advantage overlap | Jaccard of products with RCA > 1 (alt.: Spearman of RCA) | Moderator (H3) | Computed from HS trade | Annual | planned |
| `sectoral_overlap` | Sectoral composition similarity | Cosine similarity of sector shares (concordance TBD) | Moderator (H3) | Candidate: trade / UNIDO | Annual | planned |
| `mfg_composition_similarity` | Manufacturing structure similarity | Cosine similarity of MVA shares by ISIC | Moderator (H3) | Candidate: UNIDO | Annual | planned |
| `high_value_overlap` | Overlap in high-value industries | Overlap restricted to a documented high-tech product list | Moderator (H3) | Computed | Annual | planned |

## Economic interdependence

| Variable | Concept | Operationalization | Expected direction | Source | Temporal resolution | Status |
|---|---|---|---|---|---|---|
| `trade_share` | Bilateral economic importance | (X_Kj + M_Kj) / (X_K + M_K) | Attention + (H1); moderator (H4) | Candidate: KCS / KITA / Comtrade | Monthly/annual | planned |
| `export_dependence` | Korean export exposure | X_Kj / X_K | Moderator (H4) | as above | Monthly/annual | planned |
| `import_dependence` | Korean import exposure | M_Kj / M_K | Moderator (H4) | as above | Monthly/annual | planned |
| `trade_growth` | Change in bilateral trade | Δ log(X_Kj + M_Kj) | Attention + (H1) | as above | Annual | planned |
| `trade_share_roll3` | Smoothed exposure | 3-year trailing mean of `trade_share` | as `trade_share` | Constructed | Annual | planned |
| `import_concentration` | Supply-chain concentration | HHI of Korean imports from j across HS products (or of suppliers for key products) | Moderator (H4) | Candidate: KCS / Comtrade | Annual | planned |
| `fdi_exposure` | Investment exposure | Korean FDI in j / total Korean outward FDI | Moderator (H4) | Candidate: TBD | Annual | planned |
| `gvc_exposure` | Value-chain exposure | Foreign value added from j in Korean output/exports | Moderator (H4) | Candidate: OECD TiVA / other MRIO | Annual | planned |

## Government attention

| Variable | Concept | Operationalization | Expected direction | Source | Temporal resolution | Status |
|---|---|---|---|---|---|---|
| `n_mentions` | Attention volume | Country mentions in official text | Outcome (H1) | Candidate: Korean government text | Document date → annual | planned |
| `n_sentences` | Attention volume | Sentences mentioning j | Outcome (H1) | as above | annual | planned |
| `n_documents` | Attention breadth | Documents mentioning j | Outcome (H1) | as above | annual | planned |
| `n_*_share` | Relative attention | Share among all foreign entities mentioned in the period | Outcome (H1) | Constructed | annual | planned |
| `n_events` | Diplomatic engagement | Summits, ministerial visits, joint statements | Outcome (H1) / control | Candidate: hand-compiled | Event date → annual | planned |

## Political recognition

| Variable | Concept | Operationalization | Expected direction | Source | Temporal resolution | Status |
|---|---|---|---|---|---|---|
| `frame_vertical` | Vertical positioning | Sentences/terms framing j as recipient, production base, emerging market, etc. | Falls with catch-up (H5) | Constructed from text | annual | planned |
| `frame_horizontal` | Horizontal positioning | Sentences/terms framing j as strategic/technological partner, peer, co-developer | Main outcome component | Constructed from text | annual | planned |
| `frame_competitive` | Competitive/threat recognition | Sentences/terms framing j as competitor/challenger | Rises with overlap; separate outcome (H5) | Constructed from text | annual | planned |
| `recognition_share` | Recognition index | H / (H + V) | Main outcome (H2–H5) | Constructed | annual | planned |
| `recognition_balance` | Recognition index | (H − V) / (H + V) | as above | Constructed | annual | planned |
| `recognition_logit` | Recognition index | ln((H + 0.5) / (V + 0.5)) | as above | Constructed | annual | planned |
| `partnership_tier` | Formal recognition | Ordinal tier of the official bilateral partnership designation | Benchmark | Candidate: official statements | Event date → annual | planned |

## Recognition lag (compared side by side; sign: positive = under-recognition)

| Variable | Concept | Operationalization | Expected direction | Source | Temporal resolution | Status |
|---|---|---|---|---|---|---|
| `lag_A_pooled` | Recognition lag | z(status) − z(recognition), pooled standardization | Descriptive; peaks at intermediate–high proximity (H2) | Constructed | annual | planned |
| `lag_A_within_year` | Recognition lag | as above, standardized within year | as above | Constructed | annual | planned |
| `lag_B_quadratic` | Recognition lag | Fitted − observed recognition from OLS on status + status² + year effects | as above | Constructed | annual | planned |
| `lag_C_*` | Adjustment speed | Partial-adjustment / local-projection estimates | Slower adjustment of recognition than attention | Constructed | annual or higher | planned |

## Identifiers and metadata

| Variable | Concept | Operationalization | Expected direction | Source | Temporal resolution | Status |
|---|---|---|---|---|---|---|
| `iso3` | Partner | ISO 3166-1 alpha-3 | — | config/countries.yaml | — | constructed |
| `year` | Time | Calendar year | — | — | Annual | constructed |
| `administration` | Korean administration | Indicator per presidential term | Control | Public record | Annual (split years TBD) | planned |
