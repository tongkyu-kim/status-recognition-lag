"""Integrity checks for the recognition-turning-points overhaul's new config (2026-10-13).

Mirrors the style of tests/test_config.py. Does not touch the legacy H1-H5 config tests.
"""

from srl.utils.config import load_config

REQUIRED_CASE_FIELDS = {"incumbent", "challenger", "role"}
VALID_ROLES = {"primary_case", "historical_extension", "exploratory_extension"}


def test_cases_config_loads_and_is_well_formed():
    cases = load_config("cases")["cases"]
    assert set(cases) == {"usa_jpn", "jpn_kor", "kor_chn", "kor_vnm"}
    for name, spec in cases.items():
        assert REQUIRED_CASE_FIELDS <= set(spec), name
        assert spec["role"] in VALID_ROLES, name
        assert spec["incumbent"] != spec["challenger"], name
    # exactly two primary cases, per docs/case_selection.md
    primary = [n for n, s in cases.items() if s["role"] == "primary_case"]
    assert set(primary) == {"jpn_kor", "kor_chn"}


def test_sectors_config_loads_and_matches_crossover_table():
    sectors = load_config("sectors")["sectors"]
    assert set(sectors) == {"shipbuilding", "semiconductors", "batteries", "displays_optics"}
    for name, spec in sectors.items():
        assert "hs92_l4" in spec and "hs92_product_ids" in spec, name
    # the one sector flagged unreliable must say so in its own config, not only in prose docs
    assert sectors["displays_optics"]["status"] == "needs_replacement_indicator"
