from pathlib import Path

BANNER_OPEN = "<!-- grim:status -->"
BANNER_CLOSE = "<!-- /grim:status -->"


def write_working_doc(
    root: Path,
    kind: str,
    name: str = "a.md",
    *,
    raw_fm: str = "",
    interior: str | None = "",
    body: str = "# Doc\n",
) -> Path:
    """Write a spec or plan under root/docs/<kind>/<name>.

    raw_fm is used verbatim so malformed frontmatter can be expressed.
    interior is the banner block's contents; pass None to omit the block
    entirely, which is the only way to exercise the missing-block path.
    """
    d = root / "docs" / kind
    d.mkdir(parents=True, exist_ok=True)
    parts = [f"---\n{raw_fm}\n---\n\n"]
    if interior is not None:
        parts.append(f"{BANNER_OPEN}\n{interior}{BANNER_CLOSE}\n\n")
    parts.append(body)
    path = d / name
    path.write_text("".join(parts), encoding="utf-8")
    return path


def write_spec(root: Path, name: str = "a.md", **kw) -> Path:
    return write_working_doc(root, "specs", name, **kw)


def write_plan(root: Path, name: str = "a.md", **kw) -> Path:
    return write_working_doc(root, "plans", name, **kw)


def banner_interior(path: Path) -> str:
    """The bytes between the delimiters, for asserting on written output."""
    import grim

    text = path.read_text(encoding="utf-8")
    span = grim._banner_span(text)
    assert span is not None, f"{path} has no banner block"
    return text[span[0] : span[1]]


def write_component(
    root: Path,
    ctype: str,
    slug: str,
    *,
    status: str = "current",
    date: str = "2026-07-24",
    body: str = "Body text.",
    cid: str | None = None,
    extra: dict | None = None,
    raw_fm: str | None = None,
) -> Path:
    """Write a component file under root/docs/components/<ctype>/<slug>.md.

    raw_fm, when given, is used verbatim as the frontmatter (for malformed
    cases); otherwise a well-formed frontmatter is assembled.
    """
    d = root / "docs" / "components" / ctype
    d.mkdir(parents=True, exist_ok=True)
    if raw_fm is None:
        lines = [
            f"id: {cid or f'{ctype}-{slug}'}",
            f"type: {ctype}",
            f"status: {status}",
        ]
        for key, value in (extra or {}).items():
            lines.append(f"{key}: {value}")
        lines.append(f"date: {date}")
        raw_fm = "\n".join(lines)
    path = d / f"{slug}.md"
    path.write_text(f"---\n{raw_fm}\n---\n\n{body}\n", encoding="utf-8")
    return path
