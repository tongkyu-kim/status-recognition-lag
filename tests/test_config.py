"""Configuration integrity: relative paths, country registry, sources, specs, frames."""

from pathlib import PurePosixPath

from srl.models.specs import load_model_specs
from srl.recognition.dictionary import load_frame_dictionary
from srl.utils.config import get_path, iter_path_entries, load_config
from srl.utils.countries import build_alias_index, load_countries, panel_definition
from srl.utils.paths import project_root

MAIN_PARTNERS = {"BRN", "KHM", "IDN", "LAO", "MYS", "MMR", "PHL", "SGP", "THA", "TLS", "VNM", "CHN"}


def test_all_paths_are_relative_and_inside_repo():
    root = project_root()
    for key, rel in iter_path_entries():
        assert not PurePosixPath(rel).is_absolute() and ":" not in rel, key
        assert "\\" not in rel, f"{key}: use forward slashes"
        assert get_path(key).resolve().is_relative_to(root), key


def test_country_registry_is_consistent():
    countries = load_countries()
    for iso3, country in countries.items():
        assert iso3 == country.iso3 and len(iso3) == 3 and iso3.isupper()
    build_alias_index(countries)  # raises on conflicting aliases


def test_main_panel_definition():
    incumbent, partners = panel_definition("main")
    assert incumbent == "KOR"
    assert set(partners) == MAIN_PARTNERS
    assert len(partners) == len(set(partners))
    countries = load_countries()
    assert all(countries[p].role == "partner" for p in partners)
    for iso3 in ("JPN", "USA", "TWN"):
        assert iso3 not in partners


def test_sources_are_candidates_without_invented_urls():
    sources = load_config("sources")["sources"]
    required = {"name", "category", "status", "access", "url", "licence", "reader", "column_map"}
    for sid, spec in sources.items():
        assert required <= set(spec), sid
        if spec["category"] != "internal":
            assert spec["status"] == "candidate", sid
            assert spec["url"] is None, f"{sid}: record URLs only after validation"


def test_model_specs_and_frames_load():
    specs = load_model_specs()
    assert {s.hypothesis for s in specs} >= {"H1", "H2", "H3", "H4", "H5"}
    assert all(s.status != "ready" for s in specs)  # nothing is estimable before data exist
    frames = load_frame_dictionary()
    assert set(frames["frames"]) == {"vertical", "horizontal", "competitive"}
