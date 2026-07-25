from pathlib import Path


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
