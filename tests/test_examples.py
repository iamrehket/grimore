import shutil
from pathlib import Path

import grim

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_shipped_examples_lint_clean(tmp_path):
    """doc-components/examples/ is the clean fixture tree; lint must pass it.

    Copied into a store layout so the check is hermetic (no git, no repo
    config): schema, ids, edges, and avoid-term checks all run; the
    transition check downgrades to its documented W042 skip.
    """
    src = REPO_ROOT / "doc-components" / "examples"
    shutil.copytree(src, tmp_path / "docs" / "components")
    result = grim.run_lint(tmp_path)
    assert result.errors == [], [f"{f.code} {f.path}: {f.message}" for f in result.errors]


def test_examples_render(tmp_path):
    src = REPO_ROOT / "doc-components" / "examples"
    for type_dir in src.iterdir():
        if type_dir.is_dir():
            shutil.copytree(type_dir, tmp_path / "docs" / "components" / type_dir.name)
    cfg = grim.load_config(tmp_path)
    store = grim.load_store(cfg)
    out1 = grim.render_store(store)
    out2 = grim.render_store(grim.load_store(cfg))
    assert out1 == out2
    # Assert on unique body text, not ids: rendered output contains bodies only.
    assert "Number ADRs adr-0001" not in out1["decisions.md"]   # superseded body skipped
    assert "Draft until IAM-40 lands" not in out1.get("renderer.md", "")  # draft body skipped
