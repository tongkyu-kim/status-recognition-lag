"""Unit tests for the YouTube extension (no network, no API key)."""

import pandas as pd
import pytest

from srl.youtube import api, classify_frames, deduplicate, queries, tables


def test_hangul_share_and_korean_flag():
    assert tables.hangul_share("베트남 경제") == 1.0
    assert tables.is_korean("베트남이 한국을 추월?")
    assert not tables.is_korean("Vietnam is rising fast")
    assert not tables.is_korean("ㅋㅋ")  # jamo only: not syllables
    assert tables.hangul_share("123 !!!") != tables.hangul_share("123 !!!")  # NaN


def test_iso_duration():
    assert tables.iso_duration_seconds("PT1H2M3S") == 3723
    assert tables.iso_duration_seconds("PT45S") == 45
    assert tables.iso_duration_seconds("P1DT1S") == 86401


def test_minimize_comment_thread_drops_identity_and_hashes():
    salt = b"s"
    item = {
        "kind": "youtube#commentThread",
        "snippet": {
            "topLevelComment": {
                "kind": "youtube#comment",
                "id": "c1",
                "snippet": {
                    "authorDisplayName": "Real Name",
                    "authorProfileImageUrl": "http://x",
                    "authorChannelUrl": "http://y",
                    "authorChannelId": {"value": "UC123"},
                    "textOriginal": "hi",
                },
            }
        },
        "replies": {
            "comments": [
                {
                    "kind": "youtube#comment",
                    "id": "r1",
                    "snippet": {"authorDisplayName": "Other", "authorChannelId": {"value": "UC9"}},
                }
            ]
        },
    }
    out = api.minimize_comment_resource(item, salt)
    top = out["snippet"]["topLevelComment"]["snippet"]
    assert "authorDisplayName" not in top and "authorChannelId" not in top
    assert top["authorHash"] == api.hash_author("UC123", salt)
    assert "authorDisplayName" not in out["replies"]["comments"][0]["snippet"]


def test_duplicate_flags():
    df = pd.DataFrame(
        {
            "comment_id": list("abcd"),
            "video_id": ["v1", "v1", "v2", "v2"],
            "text": ["베트남 대단하다", "베트남  대단하다!!", "베트남 대단하다", "ㅋ"],
            "published_at": ["2020", "2021", "2020", "2020"],
            "author_hash": ["h1", "h2", "h1", "h3"],
        }
    )
    out = deduplicate.flag_duplicates(df).set_index("comment_id")
    assert out.loc["b", "dup_within_video"]
    assert out.loc["a", "dup_same_author_cross_video"] and out.loc["c", "dup_same_author_cross_video"]
    assert out.loc["d", "too_short"]


def test_pilot_plan_fits_one_day_and_covers_all_families():
    plan = queries.build_plan(pilot=True)
    est = queries.quota_estimate(plan)
    assert est["search_units"] <= 9500
    fams = {s.family for s in plan}
    assert {"profile", "upgrading", "overtaking", "deference", "dependence"} <= fams
    assert len({s.spec_id for s in plan}) == len(plan)


def test_prescreen_is_flag_only():
    v = pd.DataFrame({"title": ["베트남, 한국 추월하나"], "description": ["삼성 공장"]})
    out = classify_frames.dictionary_prescreen(v)
    assert out["dict_overtaking"].iloc[0] and out["dict_korean_contribution"].iloc[0]
    assert "video_frame" not in out  # final frames are human-coded


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("YOUTUBE_API_KEY", raising=False)
    monkeypatch.setattr(api, "_dotenv", lambda: {})
    with pytest.raises(api.MissingCredential):
        api.api_key()
