# Measurement protocol (skeleton -- not yet implemented)

**Status: design only.** No multilingual classifier, codebook, or human-coding interface has been
built in this pass. This document records the design decisions made so far so implementation can
proceed without re-deriving them; it is not a usable protocol yet.

## Classification categories (per brief Section III.6)

A sentence/statement is classified into exactly one of:

1. Explicit recognition of parity or superiority
2. Recognition of material achievement without broader peer recognition
3. Explicit assertion of incumbent superiority
4. Dismissal or depreciation of challenger achievement
5. Threat acknowledgment
6. Neutral descriptive reporting
7. No relevant status attribution

**Design decision (inherited from the brief, not yet tested):** categories 1 and 2 must be kept
distinct at the classification stage, not merged post hoc -- an item coded "achievement recognized,
peer status not granted" (category 2) is a different empirical object from category 1, and the
legacy project's dictionary (`config/recognition_frames.yaml`, H/V/C frames) does not make this
distinction. This is the specific reason the legacy dictionary is retained for comparison only
(`legacy/README.md`) rather than extended.

## What is reused vs. what is new

- Sentence segmentation and entity matching (`src/srl/text/segmentation.py`, `entities.py`) --
  reused as-is; language-agnostic at the mechanical level, though matcher entity lists would need
  Japanese/Chinese country-name variants added.
- The legacy dictionary scorer (`src/srl/recognition/dictionary.py`) -- kept only as a baseline
  comparison, per the brief's explicit instruction not to use it as the primary measure.
- A new 7-category classifier (dictionary baseline -> embeddings -> supervised -> optional
  LLM-assisted, per brief Section III.6) -- not started. Belongs in `src/srl/recognition/` as new
  modules alongside (not replacing) the legacy ones.

## Validation sample (400-600 items)

Not yet drawn. Stratification variables specified by the brief: case, period, language, framing.
Blocked on: (a) the Japanese-side corpus not existing yet (`docs/data_access_requirements.md`
priority 1) -- without it, a jpn_kor-side sample cannot be drawn; (b) no coding interface built.
The legacy `scripts/pilot/build_frames.py` already produces a KWIC sample mechanism
(`outputs/pilot/kwic_frame_samples.csv`) that could be adapted as a starting point for the
interface, but this has not been done.

## Open question not resolved here

Whether embeddings/supervised/LLM-assisted backends should be validated per-language
independently (brief's explicit requirement, Section III.6) or share a single cross-lingual model
-- this is an implementation choice that depends on which backend is chosen first, and is deferred
to whoever implements `src/srl/recognition/` next.
