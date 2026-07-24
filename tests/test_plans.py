import grim


def write_plan(root, name, text):
    d = root / "docs" / "plans"
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8")


def check(root):
    return grim.check_plans(grim.load_config(root))


def test_plan_with_spec_is_clean(tmp_path):
    write_plan(tmp_path, "a.md", "---\nspec: docs/specs/a.md\n---\n\n# Plan\n")
    assert check(tmp_path) == []


def test_plan_without_spec_is_w060(tmp_path):
    write_plan(tmp_path, "a.md", "---\ntitle: x\n---\n\n# Plan\n")
    findings = check(tmp_path)
    assert [f.code for f in findings] == ["W060"]
    assert findings[0].level == "warning"
    assert findings[0].path == "docs/plans/a.md"


def test_plan_with_no_frontmatter_is_w060(tmp_path):
    write_plan(tmp_path, "a.md", "# Plan without frontmatter\n")
    assert [f.code for f in check(tmp_path)] == ["W060"]


def test_missing_plans_dir_is_clean(tmp_path):
    assert check(tmp_path) == []
