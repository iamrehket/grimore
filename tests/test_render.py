import grim
from helpers import write_component


def load(root):
    cfg = grim.load_config(root)
    return cfg, grim.load_store(cfg)


def test_store_hash_ignores_non_current_components(tmp_path):
    write_component(tmp_path, "adr", "kept", status="current")
    _, store = load(tmp_path)
    baseline = grim.store_hash(store)
    write_component(tmp_path, "adr", "draftling", status="draft")
    write_component(tmp_path, "adr", "old", status="superseded")
    _, store = load(tmp_path)
    assert grim.store_hash(store) == baseline


def test_store_hash_changes_with_current_content(tmp_path):
    write_component(tmp_path, "adr", "kept", body="One.")
    _, store = load(tmp_path)
    h1 = grim.store_hash(store)
    write_component(tmp_path, "adr", "kept", body="Two.")
    _, store = load(tmp_path)
    assert grim.store_hash(store) != h1


def test_demote_headings():
    body = "# Title\n\nprose # not a heading\n\n## Sub\n\n###### Deep"
    assert grim.demote_headings(body, 1) == "## Title\n\nprose # not a heading\n\n### Sub\n\n###### Deep"
    assert grim.demote_headings(body, 2).startswith("### Title")
