from pathlib import Path

import pytest

import grim


def test_defaults(tmp_path):
    cfg = grim.load_config(tmp_path)
    assert cfg.root == tmp_path
    assert cfg.components == tmp_path / "docs" / "components"
    assert cfg.current == tmp_path / "docs" / "current"
    assert cfg.specs == tmp_path / "docs" / "specs"
    assert cfg.plans == tmp_path / "docs" / "plans"
    assert cfg.default_branch == "main"
    assert cfg.types == grim.COMPONENT_TYPES


def test_toml_overrides(tmp_path):
    (tmp_path / ".grimore.toml").write_text(
        '[grimore]\ncomponents = "store"\ndefault_branch = "trunk"\n'
        'types = ["adr", "term"]\n',
        encoding="utf-8",
    )
    cfg = grim.load_config(tmp_path)
    assert cfg.components == tmp_path / "store"
    assert cfg.default_branch == "trunk"
    assert cfg.types == ("adr", "term")


def test_invalid_toml_raises(tmp_path):
    (tmp_path / ".grimore.toml").write_text("not toml [", encoding="utf-8")
    with pytest.raises(grim.ConfigError):
        grim.load_config(tmp_path)


def test_unknown_component_type_raises(tmp_path):
    (tmp_path / ".grimore.toml").write_text(
        '[grimore]\ntypes = ["adr", "bogus"]\n', encoding="utf-8"
    )
    with pytest.raises(grim.ConfigError):
        grim.load_config(tmp_path)


def test_non_string_path_value_raises(tmp_path):
    (tmp_path / ".grimore.toml").write_text("[grimore]\ncomponents = 42\n", encoding="utf-8")
    with pytest.raises(grim.ConfigError):
        grim.load_config(tmp_path)


def test_scalar_types_value_raises(tmp_path):
    (tmp_path / ".grimore.toml").write_text('[grimore]\ntypes = "adr"\n', encoding="utf-8")
    with pytest.raises(grim.ConfigError):
        grim.load_config(tmp_path)


def test_overlapping_specs_and_plans_is_rejected(tmp_path):
    """Both dirs are walked as one pass and each file takes a single role, so
    an overlap would silently classify every plan as a spec."""
    (tmp_path / ".grimore.toml").write_text(
        '[grimore]\nspecs = "docs/wl"\nplans = "docs/wl"\n', encoding="utf-8"
    )
    with pytest.raises(grim.ConfigError, match="must not overlap"):
        grim.load_config(tmp_path)


def test_nested_specs_inside_plans_is_rejected(tmp_path):
    (tmp_path / ".grimore.toml").write_text(
        '[grimore]\nspecs = "docs/wl/specs"\nplans = "docs/wl"\n', encoding="utf-8"
    )
    with pytest.raises(grim.ConfigError, match="must not overlap"):
        grim.load_config(tmp_path)


def standing_waiver_config(tmp_path, entry):
    (tmp_path / ".grimore.toml").write_text(
        f"[grimore]\n\n[[grimore.standing_waiver]]\n{entry}\n", encoding="utf-8"
    )
    return tmp_path


def test_standing_waiver_parses(tmp_path):
    standing_waiver_config(
        tmp_path,
        'component = "adr-x"\npaths = ["a.json", "b/"]\nreason = "churns for other reasons"',
    )
    [sw] = grim.load_config(tmp_path).standing_waivers
    assert sw.component == "adr-x"
    assert sw.paths == ("a.json", "b/")
    assert sw.reason == "churns for other reasons"


def test_standing_waiver_requires_a_reason(tmp_path):
    # A bypass nobody has to justify is not reviewable. W071 already made the
    # component-plus-reason pairing the thing that makes a waiver auditable.
    standing_waiver_config(tmp_path, 'component = "adr-x"\npaths = ["a.json"]')
    with pytest.raises(grim.ConfigError, match="reason is required"):
        grim.load_config(tmp_path)


def test_standing_waiver_rejects_an_empty_reason(tmp_path):
    standing_waiver_config(
        tmp_path, 'component = "adr-x"\npaths = ["a.json"]\nreason = "   "'
    )
    with pytest.raises(grim.ConfigError, match="reason is required"):
        grim.load_config(tmp_path)


def test_standing_waiver_requires_paths(tmp_path):
    # Without paths it would be a component-wide bypass, which is what a
    # Grim-Waive trailer already is - and that one expires with the branch.
    standing_waiver_config(tmp_path, 'component = "adr-x"\npaths = []\nreason = "r"')
    with pytest.raises(grim.ConfigError, match="non-empty list"):
        grim.load_config(tmp_path)


def test_standing_waiver_rejects_unknown_keys(tmp_path):
    standing_waiver_config(
        tmp_path,
        'component = "adr-x"\npaths = ["a.json"]\nreason = "r"\nexpires = "never"',
    )
    with pytest.raises(grim.ConfigError, match="unknown key"):
        grim.load_config(tmp_path)


def test_no_standing_waivers_by_default(tmp_path):
    (tmp_path / ".grimore.toml").write_text("[grimore]\n", encoding="utf-8")
    assert grim.load_config(tmp_path).standing_waivers == ()
