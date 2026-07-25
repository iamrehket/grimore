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
