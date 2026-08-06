"""The single-file bundle.

For a reader with no checkout: every live component in one artifact, ordered
the way the rendered view orders it, stamped with the store it came from and
the revision it was produced at.
"""

import grim
from history_fixture import History


def bundle(root):
    cfg = grim.load_config(root)
    return grim.render_bundle(cfg, grim.load_store(cfg))


def seeded(tmp_path):
    h = History(tmp_path)
    h.write("adr", "alpha", status="current", date="2026-05-01", body="Alpha decided.")
    h.write("term", "widget", status="current", date="2026-05-02", body="A widget is.")
    h.write("adr", "draftish", status="draft", body="Not live yet.")
    h.write("adr", "gone", status="superseded", body="No longer live.")
    h.commit("baseline")
    return h


def test_live_components_are_present(tmp_path):
    h = seeded(tmp_path)
    text = bundle(h.root)

    assert "Alpha decided." in text
    assert "A widget is." in text


def test_drafts_and_superseded_are_absent(tmp_path):
    h = seeded(tmp_path)
    text = bundle(h.root)

    assert "Not live yet." not in text
    assert "No longer live." not in text


def test_it_carries_the_store_hash_and_the_revision(tmp_path):
    h = seeded(tmp_path)
    cfg = grim.load_config(h.root)
    expected = grim.store_hash(grim.load_store(cfg))
    revision = h._git("rev-parse", "--short", "HEAD").strip()

    text = bundle(h.root)
    assert f"sha256:{expected}" in text
    assert revision in text


def test_a_clean_store_says_so(tmp_path):
    h = seeded(tmp_path)
    assert "matches that revision" in bundle(h.root)


def test_an_uncommitted_component_edit_is_reported(tmp_path):
    # The reader must never be told a revision describes bytes it does not.
    h = seeded(tmp_path)
    h.write("adr", "alpha", status="current", date="2026-05-01", body="Alpha revised.")

    text = bundle(h.root)
    assert "differs from that revision" in text
    assert "Alpha revised." in text


def test_edits_outside_the_component_store_do_not_change_the_bundle(tmp_path):
    # The bundle's declared inputs are the store, the configuration, and the
    # revision. Checking the whole working tree would make an unrelated edit
    # change the output, which the determinism constraint forbids.
    h = seeded(tmp_path)
    before = bundle(h.root)

    (h.root / "README.md").write_text("unrelated churn\n")
    (h.root / "src").mkdir(exist_ok=True)
    (h.root / "src" / "thing.py").write_text("x = 1\n")

    assert bundle(h.root) == before


def test_ordering_follows_the_rendered_view(tmp_path):
    # Same (date, id) ordering the committed views use, so a reader can line
    # the two up.
    h = History(tmp_path)
    h.write("adr", "later", status="current", date="2026-05-09", body="Later one.")
    h.write("adr", "earlier", status="current", date="2026-05-01", body="Earlier one.")
    h.write("adr", "zebra", status="current", date="2026-05-01", body="Same day, z.")
    h.commit("baseline")

    text = bundle(h.root)
    assert text.index("Earlier one.") < text.index("Same day, z.") < text.index("Later one.")


def test_sections_appear_in_a_stated_order(tmp_path):
    h = History(tmp_path)
    h.write("usecase", "doing", status="current", body="A use case.")
    h.write("adr", "choice", status="current", body="A decision.")
    h.write("term", "word", status="current", body="A term.")
    h.write("note", "sub", status="current", body="A note.", extra={"subsystem": "render"})
    h.commit("baseline")

    text = bundle(h.root)
    assert (
        text.index("# Charter")
        < text.index("# Decisions")
        < text.index("# Glossary")
        < text.index("# render")
    )


def test_regenerating_from_the_same_inputs_is_byte_identical(tmp_path):
    h = seeded(tmp_path)
    assert bundle(h.root) == bundle(h.root)


def test_an_empty_store_still_produces_a_bundle(tmp_path):
    h = History(tmp_path)
    (h.root / "README.md").write_text("nothing here\n")
    h.commit("baseline")

    text = bundle(h.root)
    assert "0 live components" in text
