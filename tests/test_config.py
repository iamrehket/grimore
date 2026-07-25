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
