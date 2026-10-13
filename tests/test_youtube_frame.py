"""Offline tests for the pre-registered YouTube sampling frame (no API calls)."""

from datetime import date

from srl.youtube import frame


def test_windows_identical_offsets_and_exclude_event_month():
    s1, e1 = frame.window("CHN", "P2")
    s2, e2 = frame.window("CHN", "P3")
    assert (s1, e1) == (date(2010, 7, 1), date(2011, 7, 1))  # months -12..-1
    assert (s2, e2) == (date(2011, 8, 1), date(2012, 8, 1))  # months +1..+12 (July 2011 excluded)
    for iso in frame.cfg()["events"]:
        starts = [frame.window(iso, p)[0] for p in ("P1", "P2", "P3", "P4")]
        ends = [frame.window(iso, p)[1] for p in ("P1", "P2", "P3", "P4")]
        assert all((e - s).days in (365, 366) for s, e in zip(starts, ends, strict=True))


def test_rfc3339_is_midnight_kst():
    assert frame.rfc3339_utc(date(2011, 8, 1)) == "2011-07-31T15:00:00Z"


def test_channel_not_on_youtube_cells_are_never_searched():
    plan = frame.plan_cells()
    ytn = plan[(plan["country"] == "VNM") & (plan["channel"] == "YTN")]
    assert set(ytn["plan_status"]) == {"channel_not_on_youtube"}  # YTN channel opened 2013-05
    assert (plan[plan["country"] == "IDN"]["plan_status"] == "search").all()


def _video(title, desc="", tags=(), dur="PT3M", lang="ko", ch=None, pub="2021-01-15T03:00:00Z", live="none"):
    ch = ch or frame.cfg()["channels"][0]["id"]
    return {
        "snippet": {
            "title": title,
            "description": desc,
            "tags": list(tags),
            "channelId": ch,
            "publishedAt": pub,
            "defaultAudioLanguage": lang,
            "liveBroadcastContent": live,
        },
        "contentDetails": {"duration": dur},
    }


ROW = {"country": "IDN", "window_start_kst": "2020-08-01", "window_end_kst_exclusive": "2021-08-01"}


def test_inclusion_rules():
    assert frame.classify(_video("인도네시아 니켈 수출 금지"), ROW)[0] == "included"
    assert frame.classify(_video("니켈 수출 금지", desc="인도네시아 정부가"), ROW)[0] == "manual_review"
    assert frame.classify(_video("니켈 수출 금지"), ROW) == (
        "excluded",
        "country_absent_from_title_description_tags (incidental match)",
    )
    assert frame.classify(_video("인도네시아 #shorts"), ROW)[0] == "excluded"
    assert frame.classify(_video("인도네시아", dur="PT45S"), ROW)[0] == "excluded"
    assert frame.classify(_video("인도네시아 뉴스", dur="PT2H"), ROW)[1].startswith("full_programme")
    assert frame.classify(_video("인도네시아", ch="UCnotwhitelisted"), ROW)[1] == "channel_not_in_whitelist"
    assert frame.classify(_video("인도네시아", pub="2021-08-01T00:30:00Z"), ROW)[1] == "outside_window"
    assert frame.classify(_video("Indonesia news", lang="en"), ROW)[0] == "excluded"
    assert frame.classify(None, ROW)[0] == "pending_metadata"
    assert frame.classify("missing", ROW)[0] == "excluded"


def test_hanja_rule_v3():
    row = {"country": "CHN", "window_start_kst": "2020-08-01", "window_end_kst_exclusive": "2021-08-01"}
    assert frame.classify(_video("美中 무역 갈등"), row)[0] == "included"
    assert frame.classify(_video("中 쓰촨성 대홍수"), row)[0] == "included"
    assert frame.classify(_video("北-中 관계 어디로"), row)[0] == "included"
    assert frame.classify(_video("中에 특사 파견"), row)[0] == "included"
    assert frame.classify(_video("회의 진행中 발언"), row)[0] == "manual_review"  # glued to Hangul


def test_tags_only_excluded_description_only_reviewed_v3():
    assert frame.classify(_video("니켈 수출", tags=["인도네시아"]), ROW)[0] == "excluded"
    assert frame.classify(_video("니켈 수출", desc="인도네시아 정부가"), ROW)[0] == "manual_review"


def test_day_sample_is_deterministic_and_within_window():
    row = {
        "cell_id": "CHN_P3_MBC",
        "window_start_kst": "2011-08-01",
        "window_end_kst_exclusive": "2012-08-01",
    }
    d1, d2 = frame.sampled_days(row), frame.sampled_days(row)
    assert d1 == d2 and len(d1) == frame.cfg()["search"]["dense_cell_rule"]["days_per_cell"]
    assert all(date(2011, 8, 1) <= d < date(2012, 8, 1) for d in d1)
    other = frame.sampled_days({**row, "cell_id": "CHN_P3_MBN"})
    assert other != d1  # independent draws per cell
