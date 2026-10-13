# YouTube coding protocol (comments and videos)

Version 0.1 (pre-pilot), 2026-09-30. Revise after the pilot's first coding round and record every
change in [decisions.md](decisions.md).

## Principles

1. **Positioning, not sentiment.** Code how the comment positions the partner in a status order.
   Negative tone can carry high recognition; positive tone can carry vertical positioning.
2. **The partner must be the object.** Categories apply only when the status content concerns the
   partner state (or its economy, firms or people *as representatives of the state's standing*).
   Set `target_is_partner = 0` for comments only about Korea, the YouTuber, or unrelated topics, and
   code them I (neutral/unrelated).
3. **Multi-label.** A comment can carry several categories. Code everything that is present.
4. **Read the video context.** Use `video_title` (and the video itself if needed). A comment such
   as "결국 이렇게 될 줄" means different things under different videos.
5. **When unsure,** code your best reading and set `uncertain = 1`. Do not leave it blank.
6. **No inference about commenters,** including their demographics, politics or identity.

## Comment categories

| Code | Category | Code 1 when the comment ... | Not this category when ... |
|---|---|---|---|
| A | `capability_recognition` | acknowledges that the partner has materially advanced or is capable (technology, industry, growth, economic weight) | capability is mentioned only to deny it (→ C) |
| B | `horizontal_recognition` | treats the partner as a legitimate peer, partner or comparable actor ("대등한 파트너", "이제 비교 대상") | the "partnership" is framed as Korea helping a junior partner (→ G or vertical) |
| C | `dismissal` | explicitly minimizes or rejects the partner's advancement ("아직 멀었다", "한국이랑 비교 불가", "절대 못 따라온다") | the comment is critical of the partner on other grounds (e.g. politics) without denying economic standing |
| D | `attribution_discounting` | acknowledges success but attributes it away: Korean or foreign firms, foreign capital, cheap labour, copying or theft of technology, subsidies, external assistance | the attribution is neutral factual context without discounting (e.g. "삼성 투자 덕에 수출이 늘었다" in a descriptive thread → code A only, and D only if it serves to deny the partner's own standing) |
| E | `status_threat` | expresses concern that the partner may catch, surpass, displace or seriously compete with Korea | concern is only about security or politics with no status/economic dimension |
| F | `mockery_of_claims` | ridicules or delegitimizes the partner's (or the video's) claim of rising status ("국뽕", "정신승리", "선진국 ㅋㅋ") | ridicule targets the YouTuber or the Korean media rather than the partner's claim |
| G | `deference_reward` | responds positively to the partner learning from, depending on, requesting help from, or acknowledging Korea's leadership ("한국을 배우니 기특하다", "고마운 줄 아네") | positive statements about the partner unrelated to deference |
| H | `competitive_recognition` | explicitly acknowledges the partner as a serious industrial, economic or technological competitor (neutral or negative tone) | "competitor" is used mockingly to deny it (→ C / F) |
| I | `neutral_unrelated` | has no usable status content | any of A–H applies |

**Joint patterns to watch** (the pilot will show whether they are codable):

- A + D ("They grew, but only thanks to Korean factories"): acknowledged-but-discounted. This is
  the core pattern for Approach C.
- A + H + E, C = 0: high recognition combined with threat.
- C + F: resistance to a status claim (H-P3).
- G with a C-type contrast ("Unlike China, Vietnam respects Korea"): deference reward (H-P5).

### Worked examples (constructed, not real comments)

| Comment | A | B | C | D | E | F | G | H | I |
|---|---|---|---|---|---|---|---|---|---|
| 중국 전기차는 이미 우리보다 앞서서 무섭다 | 1 | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 0 |
| 베트남 성장 다 삼성 덕분이지 자기들 힘은 아님 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| 베트남이 한국 추월? 100년 걸려도 못함 ㅋㅋ | 0 | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 0 |
| 캄보디아 도와주는 건 좋은 일이다 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 (no status positioning of the partner) |
| 한국 배우겠다는 베트남 기특하네 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 | 0 |
| 싱가포르는 이미 우리보다 잘사는 나라, 배울 점 많다 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| 이제 베트남도 반도체에서 진짜 경쟁자다 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

## Video frames (video coding sheet)

Code from title + description (+ transcript or the video itself if the text is ambiguous). Frames
are multi-label; `frame_primary` is the dominant one.

| Frame | Definition |
|---|---|
| `neutral_info` | Economic information without a status claim or comparison |
| `upward_status` | Partner portrayed as rising, upgrading or becoming a power, without an explicit Korea comparison |
| `overtaking` | Partner catching, overtaking or threatening to overtake Korea |
| `competitive` | Partner as competitor to Korean firms or industries |
| `korean_contribution` | Partner's growth credited to Korean firms, aid or investment |
| `deferential` | Partner learning from Korea, seeking help, or acknowledging Korean leadership |
| `mutual_dependence` | Korea depends on the partner (production base, supply chains, markets) |
| `threat` | Alarm or crisis framing for Korea |
| `general_profile` | General country/economy profile (background) |

Also code `status_claim_intensity`: 0 = none; 1 = implicit (rising); 2 = explicit peer claim
("한국과 대등"); 3 = explicit superiority or overtaking claim. Code
`industry_korean_status_bearing` = 1 if the video centres on semiconductors, EVs/batteries,
shipbuilding, displays, automobiles, smartphones/electronics or steel.

## Reliability and classification plan

1. **Stage 1, human coding:** a stratified sample (country × year bin × frame × engagement). Two
   coders independently code a 50-comment overlap per major case; one coder codes the rest.
2. **Stage 2, reliability:** Krippendorff's α per category (nominal, binary), category prevalence,
   and a confusion table among C, D, E, F and between A and H. Categories with α < 0.67 after one
   revision round are merged or dropped, and the decision is logged.
3. **Stage 3, baselines:** (a) the dictionary baseline (`dict_*` flags; comment dictionaries to be
   written from Stage-1 examples); (b) a Korean transformer classifier (e.g. a KoELECTRA/KLUE-type
   encoder, multi-label head) trained on human codes; (c) optional LLM-assisted labels under D012
   (pinned model, versioned prompt, stored outputs) validated against held-out human codes.
4. **Stage 4, held-out evaluation:** precision, recall and F1 per class, macro-F1, and confusion
   matrices. Model labels are **never** ground truth; they are measurements with reported error.
