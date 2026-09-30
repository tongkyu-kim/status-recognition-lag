"""Country-name normalization (dataset names -> ISO3)."""

import pytest

from srl.utils.countries import normalize_key, to_iso3


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        # Viet Nam: WDI/UN spelling, common spelling, diacritics, official name, Korean
        ("Viet Nam", "VNM"),
        ("Vietnam", "VNM"),
        ("Việt Nam", "VNM"),
        ("Socialist Republic of Viet Nam", "VNM"),
        ("베트남", "VNM"),
        # Lao PDR: punctuation and apostrophe variants
        ("Lao PDR", "LAO"),
        ("Lao P.D.R.", "LAO"),
        ("Laos", "LAO"),
        ("Lao People’s Democratic Republic", "LAO"),
        ("라오스", "LAO"),
        # Korea: source-specific formats must not collide with the DPRK
        ("Korea, Rep.", "KOR"),
        ("Republic of Korea", "KOR"),
        ("South Korea", "KOR"),
        ("대한민국", "KOR"),
        ("Korea, Dem. People's Rep.", "PRK"),
        ("North Korea", "PRK"),
        # Hong Kong must not map to China
        ("Hong Kong SAR, China", "HKG"),
        ("China, Hong Kong SAR", "HKG"),
        ("People's Republic of China", "CHN"),
        ("중국", "CHN"),
        # Leading article, whitespace, case
        ("  the Philippines ", "PHL"),
        ("PHILIPPINES", "PHL"),
        # Timor-Leste variants
        ("Timor-Leste", "TLS"),
        ("Timor Leste", "TLS"),
        ("East Timor", "TLS"),
        ("동티모르", "TLS"),
        # Historical / alternative names
        ("Burma", "MMR"),
        ("Brunei", "BRN"),
        ("싱가폴", "SGP"),
        # ISO3 codes pass through
        ("IDN", "IDN"),
        ("khm", "KHM"),
    ],
)
def test_to_iso3_known_names(name, expected):
    assert to_iso3(name) == expected


def test_all_main_panel_names_normalize():
    for name in ["Brunei Darussalam", "Cambodia", "Indonesia", "Lao PDR", "Malaysia", "Myanmar",
                 "Philippines", "Singapore", "Thailand", "Timor-Leste", "Viet Nam", "China"]:
        assert to_iso3(name, strict=True) is not None


def test_unknown_name_returns_none_or_raises():
    assert to_iso3("Atlantis") is None
    assert to_iso3(None) is None
    assert to_iso3(float("nan")) is None
    with pytest.raises(KeyError):
        to_iso3("Atlantis", strict=True)


def test_timor_alone_is_not_timor_leste():
    # "Timor" alone is ambiguous (West Timor is part of Indonesia).
    assert to_iso3("Timor") is None


def test_normalize_key_preserves_hangul():
    assert normalize_key("베트남") == "베트남"
    assert normalize_key("Việt  Nam") == "viet nam"
