# Data sources

**Every source below is a candidate that needs validation.** Before a source is used:

1. confirm coverage (partners, years, frequency, product level) and record it here;
2. read and record the terms of use and licence, including redistribution rights for the
   replication package;
3. record the access method and the verified landing page in `config/sources.yaml` (the `url`
   stays `null` until then);
4. deposit files by hand under `data/raw/<source_id>/<YYYY-MM-DD>/` and register them
   (`make register-raw`);
5. log the decision in [decisions.md](decisions.md) and set `status: validated` in
   `config/sources.yaml`.

No scrapers or automated downloaders exist in this repository. A connector may be added only
after step 5, and only if the provider's terms allow automated access.

Validation record template (copy per source):

```text
source_id:          e.g. baci
validated_on:       YYYY-MM-DD
coverage:           partners / years / frequency / classification & revision
access:             manual download | bulk file | documented API (version)
licence / terms:    summary + where recorded
redistribution:     allowed? derived data only? not allowed?
known issues:       e.g. mirror discrepancies, re-exports, revisions, confidentiality suppression
```

---

## Trade

**Needed:** monthly or annual bilateral Korean exports and imports by partner; HS-level trade if
available (for overlap measures, also world-level HS exports of all countries).

| source_id | Candidate source | Intended use | Open questions |
|---|---|---|---|
| `kcs_trade` | Korea Customs Service | Korea's bilateral trade, monthly, HS (national HSK lines) | Access route; historical depth; HS revision handling |
| `kita_trade` | Korea International Trade Association | Cross-check of KCS; convenient aggregates | Redistribution terms; consistency with KCS |
| `un_comtrade` | UN Comtrade | Partner-reported (mirror) flows; world denominators | Access tier; reporting gaps for some ASEAN members |
| `baci` | BACI (CEPII) | Reconciled HS6 bilateral flows for RCA/ESI/EXPY | Annual only; version pinning; licence terms |

Notes: Hong Kong/Macao re-exports (CHN vs. HKG) and Taiwan's reporting label need explicit rules.
Mirror statistics are a robustness check, not the default.

## Macro / status indicators

| source_id | Candidate source | Intended use | Open questions |
|---|---|---|---|
| `wb_wdi` | World Bank WDI | GDP per capita, MVA, high-tech export share | Exact indicator codes and vintages; coverage for Myanmar and Timor-Leste |
| `imf` | IMF datasets | Macro cross-checks; trade-by-partner statistics | Dataset names and vintages |
| `unido` | UNIDO industrial statistics | MVA and its sectoral composition | Access and licence; sector detail for small economies |
| `oecd` | OECD (TiVA, productivity) | GVC exposure; productivity | ASEAN coverage by dataset |
| `wipo` | WIPO IP statistics | Patent-based capability | Counting rules (office, families, by origin) |
| `complexity_atlas` | Atlas of Economic Complexity / OEC | Complexity cross-checks | Licence; methodology vs. own computation |

## Interdependence (FDI / GVC)

| source_id | Candidate source | Intended use | Open questions |
|---|---|---|---|
| `fdi_korea` | Korean outward/inward FDI statistics (provider TBD); UNCTAD bilateral FDI | FDI exposure | Flows vs. stocks; reporting basis; suppression |

## Government text (Korea)

| source_id | Candidate source | Intended use | Open questions |
|---|---|---|---|
| `kr_presidential_office` | Presidential Office releases, speeches; archived material of past administrations | Attention; recognition | Archive continuity across administrations |
| `kr_mofa` | Ministry of Foreign Affairs: press releases, speeches, Diplomatic White Papers | Attention; recognition | Korean vs. English coverage; document types |
| `kr_motie` | Trade/industry ministry releases (MOTIE / successor) | Economic framing of partners | Ministry renamings; institution crosswalk |
| `kr_national_assembly` | National Assembly plenary/committee minutes | Legislative framing (separate analysis) | Volume; speaker attribution |
| `kr_other_official` | Other official portals/archives | Coverage gaps | Duplicate syndicated releases |
| `kr_diplomatic_events` | Summits, visits, ministerial meetings, joint statements | Event counts; partnership tiers | Hand-coding rules; completeness |

Deposit format: text files plus a `metadata.csv` sidecar (schema in `data/README.md`). Check
licence terms for Korean public-sector works before redistributing any text. Derived measures
are the default for the replication package.

## Historical corpora (later extensions)

| source_id | Candidate source | Case |
|---|---|---|
| `jp_mofa_bluebook` | Japan MOFA Diplomatic Bluebooks | Japan → Korea |
| `jp_meti_whitepaper` | METI/MITI White Papers on International Economy and Trade | Japan → Korea |
| `us_frus` | Foreign Relations of the United States | US → Japan |
| `us_presidential` | US presidential public papers / archives | US → Japan |
| `us_ustr` | USTR reports and releases | US → Japan |

## Project-generated inputs

| source_id | Description |
|---|---|
| `human_coding` | Completed human coding sheets ([coding_protocol.md](coding_protocol.md)), treated as immutable raw inputs |
