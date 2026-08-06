"""The serialized digest.

This is where the walker, the boundary, and the provenance index become one
artifact, so the format is pinned by a golden covering every event label, a
violation, all three provenance cases, and the truncation note. Ordering gets
its own assertion: a repeat-comparison cannot catch an order that is stable
but unspecified, because the same code emits the same arbitrary sequence twice.
"""

import re

import grim
from helpers import write_spec
from history_fixture import History


def rendered(root, **kw):
    text = grim.render_digest(grim.digest(grim.load_config(root), **kw))
    # Hashes vary per run; assert their shape and position, not their value.
    return re.sub(r"\b[0-9a-f]{7,40}\b", "<sha>", text)


def full_history(root):
    """Every event label, a violation, and all three provenance cases."""
    h = History(root)
    write_spec(
        h.root,
        "2026-05-01-first.md",
        raw_fm="components:\n  - adr-alpha\n  - adr-bravo",
    )
    write_spec(h.root, "2026-05-02-second.md", raw_fm="components:\n  - adr-bravo")

    h.write("adr", "alpha", status="draft")
    h.write("adr", "bravo", status="current")
    h.write("adr", "charlie", status="superseded")
    h.commit("first landing", when="2026-05-01T12:00:00+0000")

    h.write("adr", "alpha", status="current")
    h.write("adr", "delta", status="draft")
    h.commit("second landing", when="2026-05-02T12:00:00+0000")

    h.write("adr", "bravo", status="superseded")
    h.write("adr", "delta", status="superseded")
    h.commit("third landing", when="2026-05-03T12:00:00+0000")

    h.write("adr", "echo", status="current")
    h.commit("fourth landing", when="2026-05-04T12:00:00+0000")

    h.write("adr", "bravo", status="current")
    h.commit("fifth landing, illegal", when="2026-05-05T12:00:00+0000")
    return h


GOLDEN = """\
# Catch-up digest

Since 2026-05-01 on main. 9 events across 5 landings.

## 2026-05-01 - <sha>

- adr-alpha - added, draft (absent -> draft)
  - docs/specs/2026-05-01-first.md
- adr-bravo - added, live (absent -> current)
  - docs/specs/2026-05-01-first.md
  - docs/specs/2026-05-02-second.md
- adr-charlie - added, already superseded (absent -> superseded)

## 2026-05-02 - <sha>

- adr-alpha - promoted (draft -> current)
  - docs/specs/2026-05-01-first.md
- adr-delta - added, draft (absent -> draft)

## 2026-05-03 - <sha>

- adr-bravo - superseded (current -> superseded)
  - docs/specs/2026-05-01-first.md
  - docs/specs/2026-05-02-second.md
- adr-delta - abandoned (draft -> superseded)

## 2026-05-04 - <sha>

- adr-echo - added, live (absent -> current)

## 2026-05-05 - <sha>

- adr-bravo - lifecycle violation (superseded -> current)
  - docs/specs/2026-05-01-first.md
  - docs/specs/2026-05-02-second.md
"""


def test_the_serialized_shape_is_pinned(tmp_path):
    h = full_history(tmp_path)
    assert rendered(h.root, since="2026-05-01") == GOLDEN


def test_a_truncated_clone_says_so_once_not_per_line(tmp_path):
    h = History(tmp_path / "origin")
    h.write("adr", "old", status="current")
    h.commit("ancient", when="2026-05-01T12:00:00+0000")
    h.write("adr", "recent", status="draft")
    h.commit("recent", when="2026-05-09T12:00:00+0000")
    clone = h.shallow_clone(tmp_path / "shallow", depth=1)

    text = rendered(clone)
    assert text.count("truncated") == 1
    assert "History is truncated" in text


def test_an_empty_range_says_so(tmp_path):
    h = History(tmp_path)
    h.write("adr", "thing", status="current")
    h.commit("landed", when="2026-05-01T12:00:00+0000")

    assert "No component changes in range." in rendered(h.root, since="2026-06-01")


def test_ordering_holds_across_a_commit_touching_many_components(tmp_path):
    # A stable but unspecified order passes a byte-comparison against itself
    # while remaining undefined for the next implementer, so ordering needs an
    # assertion of its own rather than riding on the determinism suite.
    h = History(tmp_path)
    slugs = ["zulu", "mike", "alpha", "kilo", "bravo", "yankee", "delta"]
    for slug in slugs:
        h.write("adr", slug, status="current")
    h.commit("bulk", when="2026-05-01T12:00:00+0000")

    listed = re.findall(r"^- (adr-\S+)", rendered(h.root), re.MULTILINE)
    assert listed == sorted(f"adr-{s}" for s in slugs)


def test_singular_counts_read_correctly(tmp_path):
    h = History(tmp_path)
    h.write("adr", "thing", status="current")
    h.commit("landed", when="2026-05-01T12:00:00+0000")

    assert "1 event across 1 landing." in rendered(h.root)
