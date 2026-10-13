"""Video-frame and comment coding sheets, plus a transparent dictionary PRE-SCREEN.

Nothing here produces final labels. ``video_frame`` and all comment categories are coded by humans
following docs/youtube_coding_protocol.md. The dictionary flags (``dict_*``) exist only to
(a) oversample rare frames when drawing coding samples and (b) serve as the Stage-3 baseline that
will be evaluated against human codes. They are computed from title + description (+ transcript
text if a human has supplied it), never from the title alone when more text exists.
"""

from __future__ import annotations

import re

import pandas as pd

VIDEO_FRAMES = [
    "neutral_info",
    "upward_status",
    "overtaking",
    "competitive",
    "korean_contribution",
    "deferential",
    "mutual_dependence",
    "threat",
    "general_profile",
]
COMMENT_CATEGORIES = [
    "capability_recognition",
    "horizontal_recognition",
    "dismissal",
    "attribution_discounting",
    "status_threat",
    "mockery_of_claims",
    "deference_reward",
    "competitive_recognition",
    "neutral_unrelated",
]

# Candidate patterns only; precision/recall are unknown until evaluated against human codes.
FRAME_PATTERNS = {
    "overtaking": r"추월|따라잡|앞질|제치|넘어섰|넘어선|역전|턱밑|코앞",
    "competitive": r"경쟁|위협|라이벌|맞수|견제|잠식|빼앗",
    "upward_status": r"강국|선진국|굴기|부상|급성장|고속\s*성장|용이 되|떠오르",
    "korean_contribution": r"한국\s*기업|삼성|LG|현대|한국\s*덕분|한국이\s*만든|한국\s*투자",
    "deferential": r"한국에서\s*배우|한국을\s*배우|한국\s*배우|롤모델|새마을|ODA|원조|도움을\s*요청|감사",
    "mutual_dependence": r"공급망|생산기지|의존|협력|파트너",
    "threat": r"위기|충격|비상|무너|망한|큰일",
}


def dictionary_prescreen(videos: pd.DataFrame) -> pd.DataFrame:
    text = videos["title"].fillna("") + "\n" + videos["description"].fillna("")
    if "transcript_text" in videos:
        text = text + "\n" + videos["transcript_text"].fillna("")
    out = videos.copy()
    for frame, pat in FRAME_PATTERNS.items():
        out[f"dict_{frame}"] = text.str.contains(pat, regex=True, flags=re.IGNORECASE)
    out["dict_text_basis"] = "title+description" + ("+transcript" if "transcript_text" in videos else "")
    return out


def video_coding_sheet(videos: pd.DataFrame) -> pd.DataFrame:
    keep = [
        "video_id",
        "url",
        "countries",
        "families",
        "year",
        "channel_title",
        "title",
        "description",
        "caption_langs",
        "caption_manual_ko",
    ]
    sheet = videos[[c for c in keep if c in videos]].copy()
    for f in VIDEO_FRAMES:
        sheet[f"frame_{f}"] = ""  # 0/1, multi-label allowed
    sheet["frame_primary"] = ""  # one of VIDEO_FRAMES
    sheet["status_claim_intensity"] = ""  # 0-3, see protocol
    sheet["industry_korean_status_bearing"] = ""  # 0/1 (semiconductors, EV/battery, shipbuilding...)
    sheet["coder_id"] = ""
    sheet["notes"] = ""
    return sheet


def comment_coding_sheet(sample: pd.DataFrame, videos: pd.DataFrame) -> pd.DataFrame:
    ctx = videos[["video_id", "title"]].rename(columns={"title": "video_title"})
    sheet = sample[["comment_id", "video_id", "country", "year", "text", "like_count"]].merge(
        ctx, on="video_id", how="left"
    )
    for c in COMMENT_CATEGORIES:
        sheet[c] = ""  # 0/1, multi-label
    sheet["target_is_partner"] = ""  # 1 if the comment's status content concerns the partner state
    sheet["uncertain"] = ""
    sheet["coder_id"] = ""
    sheet["notes"] = ""
    return sheet
