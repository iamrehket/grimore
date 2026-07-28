import grim

BLOCK = "<!-- grim:status -->\n<!-- /grim:status -->\n"


def write_plan(root, name, text):
    d = root / "docs" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def write_spec(root, name, text):
    d = root / "docs" / "specs"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def check(root):
    cfg = grim.load_config(root)
    findings, _ = grim.analyze_working_layer(cfg, grim.load_store(cfg))
    return findings


def spec_codes(root):
    """Only the spec:-convention codes; banner drift has its own suite."""
    return sorted(f.code for f in check(root) if f.code in {"W060", "W093"})


def test_plan_with_resolvable_spec_has_no_spec_findings(tmp_path):
    write_spec(tmp_path, "a.md", f"---\ncomponents: []\n---\n\n{BLOCK}\n# Spec\n")
    write_plan(tmp_path, "a.md", f"---\nspec: docs/specs/a.md\n---\n\n{BLOCK}\n# Plan\n")
    assert spec_codes(tmp_path) == []


def test_plan_without_spec_is_w060(tmp_path):
    write_plan(tmp_path, "a.md", f"---\ntitle: x\n---\n\n{BLOCK}\n# Plan\n")
    findings = [f for f in check(tmp_path) if f.code == "W060"]
    assert len(findings) == 1
    assert findings[0].level == "warning"
    assert findings[0].path == "docs/plans/a.md"


def test_plan_with_no_frontmatter_is_w060(tmp_path):
    write_plan(tmp_path, "a.md", f"{BLOCK}\n# Plan without frontmatter\n")
    assert spec_codes(tmp_path) == ["W060"]


def test_plan_with_unresolvable_spec_is_w093(tmp_path):
    write_plan(tmp_path, "a.md", f"---\nspec: docs/specs/gone.md\n---\n\n{BLOCK}\n# Plan\n")
    assert spec_codes(tmp_path) == ["W093"]


def test_plan_spec_escaping_the_root_is_w093(tmp_path):
    write_plan(tmp_path, "a.md", f"---\nspec: ../../../etc/passwd\n---\n\n{BLOCK}\n# Plan\n")
    assert spec_codes(tmp_path) == ["W093"]


def test_plan_pointing_at_an_ungoverned_file_is_w093(tmp_path):
    (tmp_path / "elsewhere").mkdir()
    (tmp_path / "elsewhere" / "legacy.md").write_text("# Legacy\n", encoding="utf-8")
    write_plan(tmp_path, "a.md", f"---\nspec: elsewhere/legacy.md\n---\n\n{BLOCK}\n# Plan\n")
    assert spec_codes(tmp_path) == ["W093"]


def test_missing_plans_dir_is_clean(tmp_path):
    assert check(tmp_path) == []
