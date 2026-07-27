"""Contract for the two-host plugin operator guide."""

from pathlib import Path

GUIDE = Path(__file__).resolve().parents[1] / "docs" / "plugin-hosts.md"


def guide_text():
    assert GUIDE.is_file()
    return GUIDE.read_text(encoding="utf-8")


def test_guide_pins_the_verified_host_baseline():
    text = guide_text()

    assert "2026-07-27" in text
    assert "Claude Code `2.1.220`" in text
    assert "Codex CLI `0.145.0`" in text
    assert ".claude-plugin/plugin.json" in text
    assert ".codex-plugin/plugin.json" in text


def test_guide_covers_the_claude_code_lifecycle():
    text = guide_text()

    assert "## Claude Code" in text
    assert "claude plugin marketplace add iamrehket/grimore" in text
    assert "claude plugin install grimore@grimore" in text
    assert "claude plugin marketplace update grimore" in text
    assert "claude plugin update grimore@grimore" in text
    assert "claude plugin list" in text
    assert "claude plugin uninstall grimore@grimore" in text
    assert "claude plugin marketplace remove grimore" in text


def test_guide_covers_the_codex_lifecycle():
    text = guide_text()

    assert "## Codex" in text
    assert "codex plugin marketplace add iamrehket/grimore" in text
    assert "codex plugin add grimore@grimore" in text
    assert "codex plugin marketplace upgrade grimore" in text
    assert "codex plugin list" in text
    assert "codex plugin remove grimore@grimore" in text
    assert "codex plugin marketplace remove grimore" in text
    assert "no standalone plugin validator" in text


def test_guide_requires_cache_safe_new_sessions_and_manifest_parity():
    text = guide_text()

    assert "Start a new Claude Code session" in text
    assert "Start a new Codex session" in text
    assert "cachebuster" in text
    assert "shared semantic version" in text
    assert "remove and reinstall" in text


def test_smoke_evidence_is_isolated_complete_and_advisory():
    text = guide_text()

    assert "CLAUDE_CONFIG_DIR" in text
    assert "CODEX_HOME" in text
    assert "mktemp -d" in text
    assert "claude plugin validate" in text
    for field in (
        "date",
        "CLI versions",
        "source commit",
        "commands",
        "outcomes",
        "cleanup status",
    ):
        assert field in text
    assert "recommended" in text
    assert "not a merge gate" in text
