"""Static host-portability contract for every shipped skill."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = (
    "AskUserQuestion",
    "superpowers:brainstorming",
    "superpowers:writing-plans",
)


def shipped_skills():
    return sorted(
        path / "SKILL.md"
        for path in ROOT.iterdir()
        if path.is_dir() and (path / "SKILL.md").is_file()
    )


def test_every_shipped_skill_is_free_of_host_specific_workflow_dependencies():
    skills = shipped_skills()
    assert skills

    violations = []
    for skill in skills:
        text = skill.read_text(encoding="utf-8")
        for dependency in FORBIDDEN:
            if dependency in text:
                violations.append(f"{skill.relative_to(ROOT)}: {dependency}")

    assert violations == []


def test_align_defines_the_negotiated_capability_fallbacks():
    text = (ROOT / "align" / "SKILL.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    assert "structured-choice interaction when available" in normalized
    assert "numbered plain text otherwise" in normalized
    assert "available general design workflow" in normalized
    assert "without creating components" in normalized
    assert "available implementation-plan workflow" in normalized
    assert "doc-components/templates/plan.md" in normalized
