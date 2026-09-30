# Human coding protocol (v0.1, draft)

Purpose: produce a human-coded validation sample of government statements about partner states.
It is used to (a) validate and tune the dictionary baseline, (b) train and test later classifiers,
and (c) benchmark any LLM-assisted coding. Revise this protocol only between coding rounds, with a
version bump and a dated entry in [decisions.md](decisions.md).

## 1. Coding unit

- **Unit:** one sentence × one target partner (`unit_id = sentence_id|entity_id`). A sentence
  that mentions two partners yields two units, coded separately for each target.
- **Context:** coders see the preceding and following sentence and the document metadata
  (institution, document type, date). Masked rounds hide the partner's name and the date (see §6).
- **Language:** Korean and English units are coded by coders fluent in the language. Reliability is
  reported per language.

## 2. Categories

Coding has two parts: an attention flag, and recognition categories for attention-relevant units.

### A. Attention relevance
| Code | Meaning |
|---|---|
| `A1` relevant | The sentence says something substantive about the target partner, its economy or the bilateral relationship. |
| `A0` not relevant | Incidental mention only (list of attendees, location of an unrelated event, place name in a title, false-positive match). |

Only `A1` units receive recognition codes.

### B. Recognition (multi-label: code every category that applies)

| Code | Category | The sentence positions the partner… |
|---|---|---|
| `V` | Vertical recognition | …as below Korea in a developmental or hierarchical relation: recipient of aid or training, destination for technology transfer, low-cost production base, emerging or frontier market, object of development support. |
| `H` | Horizontal recognition | …as a peer or co-equal: strategic or technological partner, co-developer, joint innovator, party to reciprocal or mutually dependent relations, equal counterpart. |
| `C` | Competitive/threat recognition | …as a competitor, challenger or source of risk to Korea's economic or industrial position (catching up, displacing Korean firms, overcapacity, rivalry). |
| `N` | Neutral / unclassifiable | …in no identifiable relational position (factual reporting, schedules, neutral statistics), or the position cannot be determined. `N` cannot be combined with V/H/C. |

Record, for each unit: `attention` (A0/A1), `V`, `H`, `C`, `N` (0/1), `confidence` (1–3), and
`note` (free text, required when confidence = 1 or when V and H are both coded).

## 3. Core principles

1. **Relational position, not sentiment.** Vertical is not negative and horizontal is not positive.
   A warm statement about generous development support is still vertical. A cool statement that
   treats the partner as an equal negotiating counterpart is horizontal. Tone is not coded here.
2. **Code what the text asserts about the relationship, not what the coder knows.** Do not infer
   status from background knowledge of the partner's economy.
3. **Formal designations count, but code the sentence's use of them.** A sentence that only names
   an official partnership title is `H` with confidence ≤ 2 and the note "formal designation". A
   sentence that elaborates the peer relationship is `H` with higher confidence.
4. **Competitive framing is separate.** `C` records concern or rivalry. It may co-occur with `H`
   (a rival treated as a peer) or, less often, with `V`.
5. **Mixed framing is allowed.** A sentence can contain both `V` and `H` (e.g., "strategic partner"
   plus "capacity building"). Code both and add a note.
6. **Korea as subject vs. object.** Sentences about what Korea offers the partner (aid, know-how)
   are typically `V`. Sentences about what both sides do together on equal terms are typically `H`.

## 4. Decision rules (initial)

- Group references (ASEAN) are coded only when the unit's target is the group entity. Do not
  distribute group framing to member states at the coding stage.
- Quoted speech by a partner official is coded like Korean text. Record `speaker = partner` in the
  note, because these units may be excluded or analysed separately.
- ODA programme descriptions: code as usual. Such units are flagged later for sensitivity
  analyses (see research design §7, item 8).
- Future-oriented aspirations ("will become a strategic partner") are coded as the framing they
  express, with a note "aspirational".
- If a unit is a false-positive entity match (e.g., a place name), code `A0` and note
  "false match". These notes feed alias validation.

## 5. Illustrative sentences

*Constructed illustrations written for this protocol, **not quotations** from any government
source. They must be replaced by anchor examples from the real corpus after the pilot round.*

| Illustration | Codes |
|---|---|
| "Korea will expand vocational training programmes for [partner] engineers." | A1, V |
| "The two countries agreed to jointly develop next-generation battery technology as equal partners." | A1, H |
| "[Partner]'s rapid advance in shipbuilding is narrowing the gap with Korean firms." | A1, C |
| "The minister will visit [partner] from 3 to 5 May." | A1, N |
| "[Partner], a strategic partner, will receive expanded capacity-building support." | A1, V, H (note: mixed) |
| "The forum was held in [city in partner] on regional energy markets." | A0 (incidental location) |

## 6. Procedure

1. **Sampling.** Draw stratified samples by partner × year × source with the project seed
   (`python scripts/07_build_recognition_measures.py --draw-coding-sample`). Sample size is set in
   `config/analysis.yaml` after reliability and power planning.
2. **Training.** Coders study this protocol and code a training set. Discrepancies are discussed.
   Training units are excluded from reliability statistics.
3. **Pilot round.** Two coders independently code the same pilot sample. Revise categories and
   rules. Record every change with a version bump.
4. **Reliability rounds.** At least two coders independently code an overlapping subsample.
   Report Krippendorff's α (nominal) per category (A, V, H, C, N) and per language, plus Cohen's κ
   and raw agreement (`srl.recognition.validation`). Conventional benchmark: α ≥ 0.80 acceptable,
   0.667 ≤ α < 0.80 only for tentative conclusions (Krippendorff).
5. **Masked round (bias check).** Code a subsample with partner names and dates masked
   (`--mask-countries`). Systematic differences from unmasked coding indicate coder priors.
6. **Adjudication.** Disagreements in the reliability sample are resolved by discussion or a third
   coder. Adjudicated labels are stored separately from the original independent codes.
7. **Storage.** Completed coding sheets go to `data/raw/human_coding/<YYYY-MM-DD>/` and are
   registered like any raw input. They are never edited afterwards. Corrections are new files.

## 7. Coding sheet columns

`coding_order, unit_id, sentence_id, entity_id, source_id, date, text, coder_id, attention, V, H,
C, N, confidence, note, protocol_version`
