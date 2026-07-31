#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml>=6"]
# ///
"""reconcile - resolve a branch's draft components against what it built.

Phase B of finish-docs. The agent forms the verdict, which is irreducibly
agentic; this script executes it, proves it legal, and prints the audit line.
That split is deliberate: a scored agent baseline (finish-docs/tests/) found an
unaided agent already gets reconciliation semantics right, and what it cannot
supply is a validated writer, an enforced refusal, and a deterministic report.
Prose describing how to judge buys nothing; a refusal buys everything.

Legality is never re-decided here. Phase A accumulated eleven divergences from
grim by reimplementing grim's checks, so this applies its writes and then asks
grim whether the result is valid, rolling back if it is not. grim owns the
rules; this owns the transaction.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import re
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _grim_module  # noqa: E402 - sibling module, resolved from this file's directory

PROMOTE, AMEND, SUPERSEDE, DROP, KEEP = "promote", "amend", "supersede", "drop", "keep-draft"
OUTCOMES = (PROMOTE, AMEND, SUPERSEDE, DROP, KEEP)
CURRENT, SUPERSEDED = "current", "superseded"

EVIDENCE_MAX = 300
NOTE_GROUP_CAP = 5

# Exit codes. 4 is separate from 1 on purpose: "you owe me input" and "you got
# it wrong" prompt completely different behaviour, and an agent that cannot
# tell them apart retries blindly instead of reading.
OK, WRONG, USAGE, INPUT_REQUIRED = 0, 1, 2, 4

# Imported rather than reimplemented. Anything added here must be a pure
# helper - judgment stays behind the subprocess boundary.
REQUIRED_GRIM_API = (
    "load_config", "load_store", "resolve_merge_base", "coerce_fm",
    "FM_RE", "LEGAL_TRANSITIONS", "_glob_hit",
)


class Refusal(Exception):
    """Something is wrong with the request or the store. Nothing was written."""

    def __init__(self, message: str, code: int = WRONG):
        super().__init__(message)
        self.code = code


def load_grim(grim_path: Path):
    """grim's pure helpers. PEP 723 metadata is inert on import, which is why
    this script declares its own PyYAML dependency above rather than grim's."""
    try:
        return _grim_module.load_grim(grim_path, REQUIRED_GRIM_API)
    except _grim_module.GrimImportError as exc:
        raise Refusal(str(exc), USAGE) from None


def git(root: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True)


def grim_lint(root: Path, grim_path: Path) -> tuple[int, list[dict], str]:
    """(exit code, errors, raw stderr) from `grim lint --json --strict`.

    --strict matters: without it an unresolvable merge-base makes
    resolve_merge_base return None, and both check_transitions and
    check_touched_paths then return nothing at all - so the gate would be blind
    to illegal transitions and touched-path hits on a script whose entire
    purpose is a status transition.
    """
    result = subprocess.run(
        [sys.executable, str(grim_path), "lint", "--json", "--strict", "--root", str(root)],
        capture_output=True, text=True,
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError:
        # A config error exits before any JSON reaches stdout, and an unhandled
        # exception prints a traceback to stderr. Treating "no errors found in
        # the JSON" as success would keep the writes after grim failed to
        # evaluate them at all.
        return result.returncode, [], (result.stderr or result.stdout).strip()
    return result.returncode, report.get("errors", []), (result.stderr or "").strip()


def assert_clean(root: Path, grim_path: Path, when: str, errors_code: int = USAGE) -> None:
    """Raise unless grim answered, and answered clean.

    `errors_code` separates the two ways this fails after a write: grim failing
    to run at all is an environment problem (USAGE), while grim rejecting the
    result is the verdict being wrong (WRONG).
    """
    code, errors, detail = grim_lint(root, grim_path)
    # E090 is banner drift, the normal state before `lint --fix`; the documented
    # next step resolves it and reconciliation is about to change it again.
    blocking = [e for e in errors if e.get("code") != "E090"]
    if code not in (0, 1) or (code == 1 and not errors):
        raise Refusal(
            f"grim lint could not evaluate the store {when}: "
            f"exit {code}{': ' + detail if detail else ''}", USAGE,
        )
    if blocking:
        lines = "\n".join(
            f"  {e.get('code')} {e.get('path')}: {e.get('message')}" for e in blocking[:10]
        )
        more = "" if len(blocking) <= 10 else f"\n  ... and {len(blocking) - 10} more"
        raise Refusal(
            f"grim reports {len(blocking)} error(s) {when}:\n{lines}{more}", errors_code
        )


@dataclasses.dataclass
class Verdict:
    cid: str
    outcome: str
    arg: str | None
    evidence: str

    @property
    def display(self) -> str:
        token = f"{self.outcome}={self.arg}" if self.arg else self.outcome
        return f"{self.cid}:{token}"


def parse_verdict(raw: str) -> Verdict:
    parts = raw.split(":", 2)
    if len(parts) != 3:
        raise Refusal(
            f"malformed --verdict {raw!r}; expected 'ID:OUTCOME[=ARG]:EVIDENCE'", USAGE
        )
    cid, token, evidence = (p.strip() for p in parts)
    outcome, _, arg = token.partition("=")
    if outcome not in OUTCOMES:
        raise Refusal(
            f"unknown outcome {outcome!r} in {raw!r}; expected one of {', '.join(OUTCOMES)}",
            USAGE,
        )
    if outcome == SUPERSEDE and not arg:
        raise Refusal(f"{raw!r}: supersede needs a successor, as supersede=<component-id>", USAGE)
    if outcome != SUPERSEDE and arg:
        raise Refusal(f"{raw!r}: {outcome} takes no '=' argument", USAGE)
    # Mandatory for every outcome, with no exceptions to remember. It reaches
    # the transcript verbatim, so the audit trail survives losing stdout.
    if not evidence:
        raise Refusal(f"{raw!r}: evidence is required - say why this is the right call", USAGE)
    if "\n" in evidence or len(evidence) > EVIDENCE_MAX:
        raise Refusal(
            f"{raw!r}: evidence must be a single line of at most {EVIDENCE_MAX} characters",
            USAGE,
        )
    return Verdict(cid, outcome, arg or None, evidence)


def read_component(path: Path, grim) -> tuple[str, dict, str]:
    """(raw text, parsed frontmatter, body) decoded from bytes.

    Bytes, not text mode: text mode normalizes CRLF on read, and writing back
    would rewrite line endings this branch never asked to touch.
    """
    import yaml

    raw = path.read_bytes().decode("utf-8")
    m = grim.FM_RE.match(raw)
    if not m:
        raise Refusal(f"{path} has no parseable frontmatter")
    fm = yaml.safe_load(m.group(1))
    if not isinstance(fm, dict):
        raise Refusal(f"{path} frontmatter is not a mapping")
    return raw, grim.coerce_fm(fm), m.group(2)


def splice_status(raw: str, new_status: str, grim) -> str:
    """Replace the status value in place, touching nothing else.

    A raw-byte splice rather than a reserialize: normalize_component rewrites
    the whole file, reorders frontmatter and re-spaces the body, so rebuilding
    from parsed data would smear unrelated changes across a diff whose whole
    job is to be reviewable. lint --fix normalizes afterwards if it wants to.
    """
    m = grim.FM_RE.match(raw)
    if m is None:
        raise Refusal("cannot splice a file with no frontmatter")
    fm_text = m.group(1)
    status_re = re.compile(r"^(status:[ \t]*)(\S+)[ \t]*$", re.MULTILINE)
    found = status_re.search(fm_text)
    if found is None:
        raise Refusal("frontmatter has no status: line to replace")
    if status_re.search(fm_text, found.end()) is not None:
        raise Refusal("frontmatter has more than one status: line")
    start = m.start(1) + found.start(2)
    end = m.start(1) + found.end(2)
    return raw[:start] + new_status + raw[end:]


def splice_supersedes(raw: str, targets: list[str], grim) -> str:
    """Write the supersedes: list, replacing an existing line or inserting one."""
    m = grim.FM_RE.match(raw)
    if m is None:
        raise Refusal("cannot splice a file with no frontmatter")
    fm_text = m.group(1)
    value = "[" + ", ".join(targets) + "]"
    existing = re.compile(r"^supersedes:[ \t]*.*$", re.MULTILINE).search(fm_text)
    if existing is not None:
        start, end = m.start(1) + existing.start(), m.start(1) + existing.end()
        return raw[:start] + f"supersedes: {value}" + raw[end:]
    # FIELD_ORDER puts supersedes straight after status; inserting there keeps
    # the file already-normalized so lint --fix has nothing to reshuffle.
    anchor = re.compile(r"^status:[ \t]*\S+[ \t]*$", re.MULTILINE).search(fm_text)
    if anchor is None:
        raise Refusal("frontmatter has no status: line to anchor supersedes: against")
    at = m.start(1) + anchor.end()
    # Always "\n": grim's own FM_RE requires LF, so a CRLF component fails
    # E001 at preflight and never reaches this. Splicing the surrounding file's
    # convention would imply support that does not exist upstream.
    return raw[:at] + "\n" + f"supersedes: {value}" + raw[at:]


def discover_specs(root: Path, cfg, base: str) -> list[Path]:
    result = git(root, "-c", "diff.relative=false", "diff", "--no-renames",
                 "--name-only", "-z", base)
    if result.returncode != 0:
        raise Refusal(f"git diff against {base} failed: {result.stderr.strip()}", USAGE)
    specs_dir = cfg.specs.resolve()
    out = []
    for name in result.stdout.split("\0"):
        if not name.endswith(".md"):
            continue
        path = root / name
        if path.is_file() and specs_dir in path.resolve().parents:
            out.append(path)
    return sorted(set(out))


def touched_paths(root: Path, base: str) -> list[str]:
    result = git(root, "-c", "diff.relative=false", "diff", "--no-renames",
                 "--name-only", "-z", base)
    return sorted(n for n in result.stdout.split("\0") if n)


def refuse_untracked(root: Path, cfg) -> None:
    """Untracked files under the governed directories are a hard stop.

    git diff reports tracked paths only, so an unstaged spec is invisible to
    discovery - and a zero-spec refusal does not cover it, because one tracked
    spec satisfies that check while an untracked spec and its untracked draft
    stay outside the required set entirely. Nothing downstream catches it
    either: E090 is tolerated and an unstamped spec with a draft is valid.
    """
    dirs = []
    for d in (cfg.components, cfg.specs):
        try:
            dirs.append(d.resolve().relative_to(root.resolve()).as_posix())
        except ValueError:
            continue
    if not dirs:
        return
    result = git(root, "ls-files", "--others", "--exclude-standard", "-z", "--", *dirs)
    if result.returncode != 0:
        raise Refusal(f"git ls-files failed: {result.stderr.strip()}", USAGE)
    untracked = sorted(n for n in result.stdout.split("\0") if n)
    if untracked:
        listing = "\n".join(f"  {p}" for p in untracked)
        raise Refusal(
            "untracked files under the governed directories; reconciliation cannot "
            "see them and would report a completeness it did not check:\n"
            f"{listing}\n  git add them first",
            USAGE,
        )


@dataclasses.dataclass
class Plan:
    """What will be written, decided entirely before anything is."""

    intents: dict[str, str] = dataclasses.field(default_factory=dict)
    sources: dict[str, str] = dataclasses.field(default_factory=dict)
    edges: dict[str, list[str]] = dataclasses.field(default_factory=dict)


def compose(verdicts: list[Verdict]) -> Plan:
    """One final intent per component, or a refusal naming the collision.

    supersede=<new-id> promotes the successor, and a branch-new successor is
    itself a draft carrying its own verdict - so a rule that only inspected
    cascade targets would let A:supersede=B, B:supersede=C, C:keep-draft
    promote C in defiance of its explicit verdict, and leave B both promoted
    and superseded.
    """
    plan = Plan()

    def claim(cid: str, intent: str, source: str) -> None:
        previous = plan.intents.get(cid)
        if previous is not None and previous != intent:
            raise Refusal(
                f"conflicting intents for {cid!r}: {plan.sources[cid]} makes it "
                f"{previous}, {source} makes it {intent}. Say which one stands."
            )
        plan.intents[cid] = intent
        plan.sources.setdefault(cid, source)

    for v in verdicts:
        if v.outcome in (PROMOTE, AMEND):
            claim(v.cid, CURRENT, v.display)
        elif v.outcome == DROP:
            claim(v.cid, SUPERSEDED, v.display)
        elif v.outcome == SUPERSEDE:
            successor = v.arg or ""  # parse_verdict guarantees it is set
            claim(v.cid, SUPERSEDED, v.display)
            claim(successor, CURRENT, v.display)
            plan.edges.setdefault(successor, [])
            if v.cid not in plan.edges[successor]:
                plan.edges[successor].append(v.cid)
        elif v.outcome == KEEP:
            # An explicit "no change", recorded so silence is never the way out.
            previous = plan.intents.get(v.cid)
            if previous is not None:
                raise Refusal(
                    f"conflicting intents for {v.cid!r}: {plan.sources[v.cid]} makes it "
                    f"{previous}, {v.display} leaves it draft. Say which one stands."
                )
            plan.sources.setdefault(v.cid, v.display)
    return plan


def check_cycles(plan: Plan, existing: dict[str, list[str]]) -> None:
    """Reject supersede cycles. grim cannot: two mutually-superseding
    components lint clean, which is why resolve_live_successors carries a
    visited set rather than trusting the graph to be acyclic."""
    graph: dict[str, set[str]] = {}
    for successor, targets in list(existing.items()) + list(plan.edges.items()):
        graph.setdefault(successor, set()).update(targets)
    state: dict[str, int] = {}

    def visit(node: str, trail: list[str]) -> None:
        if state.get(node) == 2:
            return
        if state.get(node) == 1:
            cycle = " -> ".join(trail[trail.index(node):] + [node])
            raise Refusal(f"supersede cycle: {cycle}")
        state[node] = 1
        for nxt in sorted(graph.get(node, ())):
            visit(nxt, trail + [node])
        state[node] = 2

    for node in sorted(graph):
        visit(node, [])


def check_edges_accounted(plan: Plan, statuses: dict[str, str],
                          existing: dict[str, list[str]]) -> None:
    """Every edge target of a promoted component must be explicitly superseded.

    Printing the edge is not enough: an agent that hand-writes supersedes: into
    a component body before running would route around the report entirely. And
    an auto-cascade would flip a live decision without anyone stating that it
    should be flipped, which is the whole failure this skill exists to prevent.
    """
    for cid, intent in sorted(plan.intents.items()):
        if intent != CURRENT:
            continue
        targets = set(existing.get(cid, ())) | set(plan.edges.get(cid, ()))
        for target in sorted(targets):
            if statuses.get(target) == SUPERSEDED:
                continue  # already flipped in an earlier branch
            if plan.intents.get(target) == SUPERSEDED:
                continue
            raise Refusal(
                f"promoting {cid!r} would take effect on its supersede target "
                f"{target!r}, which no verdict accounts for. Add "
                f"--component {target} --verdict '{target}:supersede={cid}:<why>' "
                f"so the flip is stated rather than inferred."
            )


def body_changed_since_base(root: Path, base: str, path: Path, body: str) -> int | None:
    """Changed body lines vs the merge-base, or None if new on this branch."""
    rel = path.resolve().relative_to(Path(git(root, "rev-parse", "--show-toplevel")
                                          .stdout.strip()).resolve()).as_posix()
    show = git(root, "show", f"{base}:{rel}")
    if show.returncode != 0:
        return None
    m = re.match(r"\A---\r?\n(.*?)\r?\n---\r?\n(.*)\Z", show.stdout, re.DOTALL)
    if m is None:
        return None
    old, new = m.group(2).strip("\n").splitlines(), body.strip("\n").splitlines()
    if old == new:
        return 0
    return sum(1 for line in new if line not in old) + sum(1 for line in old if line not in new)


def note_worklist(touched: list[str], cfg, store, grim) -> tuple[list[tuple], list[tuple]]:
    """Touched paths no component claims, grouped and capped.

    The bound is computed rather than read: an open-ended pass over the diff is
    what the design explicitly rules out, and cap-and-split follows explain-diff.
    """
    governed = []
    for d in (cfg.components, cfg.current, cfg.specs, cfg.plans):
        try:
            governed.append(d.resolve().relative_to(cfg.root.resolve()).as_posix() + "/")
        except ValueError:
            continue
    claimed = set()
    for c in store.components:
        globs = c.fm.get("paths")
        if c.status == CURRENT and isinstance(globs, list) and all(isinstance(g, str) for g in globs):
            claimed.update(p for p in touched if grim._glob_hit(p, globs))
    groups: dict[str, int] = {}
    for path in touched:
        if path in claimed or any(path.startswith(g) for g in governed):
            continue
        key = path.split("/", 1)[0] + "/" if "/" in path else path
        groups[key] = groups.get(key, 0) + 1
    ranked = sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))
    return ranked[:NOTE_GROUP_CAP], ranked[NOTE_GROUP_CAP:]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reconcile",
        description="Reconcile a branch's draft components against what it built.",
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--grim", type=Path, help="path to grim (default: <root>/tools/grim.py)")
    parser.add_argument("--branch-diff", action="store_true",
                        help="discover specs the branch changed")
    parser.add_argument("--spec", type=Path, action="append", default=[])
    parser.add_argument("--component", action="append", default=[],
                        help="widen scope to a component no in-scope spec references")
    parser.add_argument("--verdict", action="append", default=[],
                        help="ID:OUTCOME[=ARG]:EVIDENCE; repeatable")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    try:
        return run(args)
    except Refusal as exc:
        print(f"error: {exc}", file=sys.stderr)
        return exc.code


def run(args) -> int:
    root = args.root.resolve()
    grim_path = (args.grim or root / "tools" / "grim.py").resolve()
    grim = load_grim(grim_path)

    if not (args.branch_diff or args.spec or args.component):
        raise Refusal("pass --branch-diff, --spec, or --component to set the scope", USAGE)

    assert_clean(root, grim_path, "before reconciling")
    cfg = grim.load_config(root)
    refuse_untracked(root, cfg)
    base, findings = grim.resolve_merge_base(cfg, True)
    if base is None:
        detail = "; ".join(f.message for f in findings) or "no merge-base"
        raise Refusal(f"cannot resolve a merge-base: {detail}", USAGE)

    store = grim.load_store(cfg)
    by_id = {c.cid: c for c in store.components if isinstance(c.cid, str)}
    statuses = {cid: c.status for cid, c in by_id.items()}
    existing_edges = {
        cid: [t for t in c.supersedes if isinstance(t, str)]
        for cid, c in by_id.items() if c.supersedes
    }

    specs = [(root / s).resolve() for s in args.spec]
    for path in specs:
        if not path.is_file() or cfg.specs.resolve() not in path.parents:
            raise Refusal(f"--spec must name a file under {cfg.specs}, got {path}", USAGE)
    if args.branch_diff:
        found = discover_specs(root, cfg, base)
        if not found and not args.component:
            raise Refusal(
                "--branch-diff discovered no specs. A completeness check over an "
                "empty set guarantees nothing, so this refuses rather than "
                "reporting success. Name components with --component, or use the "
                "no-spec fast path.", USAGE,
            )
        specs += found
    specs = sorted(set(specs))

    import yaml

    required: dict[str, str] = {}
    for path in specs:
        m = grim.FM_RE.match(path.read_bytes().decode("utf-8"))
        fm = yaml.safe_load(m.group(1)) if m else None
        refs = (fm or {}).get("components") or []
        if not isinstance(refs, list):
            raise Refusal(f"{path.name}: components: is not a list")
        for cid in refs:
            if isinstance(cid, str) and statuses.get(cid) == "draft":
                required[cid] = f"referenced by {path.name}"
    # A draft the branch created but forgot to reference in any spec would
    # otherwise sit outside every check.
    for name in touched_paths(root, base):
        candidate = (root / name).resolve()
        for cid, c in by_id.items():
            if c.path.resolve() == candidate and c.status == "draft":
                required.setdefault(cid, "created on this branch")
    for cid in args.component:
        if cid not in by_id:
            raise Refusal(f"--component {cid!r} names no component in the store", USAGE)
        required[cid] = "named with --component"

    verdicts = [parse_verdict(raw) for raw in args.verdict]
    seen: set[str] = set()
    for v in verdicts:
        if v.cid in seen:
            raise Refusal(f"two verdicts for {v.cid!r}; give exactly one")
        seen.add(v.cid)

    missing = sorted(set(required) - seen)
    if not verdicts or missing:
        return survey(root, base, cfg, store, grim, specs, required, missing, args)

    for v in verdicts:
        if v.cid not in required:
            raise Refusal(
                f"{v.cid!r} is not in scope; add --component {v.cid} to widen it deliberately"
            )
        if v.arg is not None and v.arg not in by_id:
            raise Refusal(f"{v.display}: successor {v.arg!r} is not a component in the store")

    plan = compose(verdicts)
    check_cycles(plan, existing_edges)
    check_edges_accounted(plan, statuses, existing_edges)

    for cid, intent in sorted(plan.intents.items()):
        source = statuses.get(cid)
        if source == intent:
            continue
        if (source, intent) not in grim.LEGAL_TRANSITIONS:
            raise Refusal(
                f"{cid!r} is {source!r}; {intent!r} is not a legal transition from there"
            )
    for v in verdicts:
        if v.outcome in (PROMOTE, AMEND) and statuses.get(v.cid) != "draft":
            raise Refusal(f"{v.display}: only a draft can be {v.outcome}d, this is "
                          f"{statuses.get(v.cid)!r}")

    return apply(root, base, grim_path, grim, cfg, by_id, plan, verdicts,
                 existing_edges, statuses, args)


def survey(root, base, cfg, store, grim, specs, required, missing, args) -> int:
    touched = touched_paths(root, base)
    offered, omitted = note_worklist(touched, cfg, store, grim)
    lines = ["SCOPE"]
    for path in specs:
        lines.append(f"  spec {path.relative_to(root).as_posix()}")
    for cid, why in sorted(required.items()):
        lines.append(f"  {cid}  ({why}) - needs a verdict")
    if not required:
        lines.append("  no drafts in scope; nothing to reconcile")
    if offered:
        lines.append("")
        lines.append(f"NOTE WORKLIST ({len(offered)} group(s) offered, cap {NOTE_GROUP_CAP})")
        for key, count in offered:
            lines.append(f"  {key:<28} {count} file(s), claimed by no component")
        if omitted:
            summary = ", ".join(f"{k} ({n})" for k, n in omitted)
            lines.append(f"  omitted below the cap: {summary}")
    if missing:
        lines.append("")
        lines.append("VERDICT REQUIRED for:")
        for cid in missing:
            lines.append(f"  --verdict '{cid}:<outcome>:<why>'")
        lines.append(f"  outcomes: {', '.join(OUTCOMES)}")
    print("\n".join(lines))
    if args.json:
        print(json.dumps({"required": sorted(required), "missing": missing,
                          "groups": offered, "omitted": omitted}, indent=2))
    # Nothing in scope needs a decision, so there is no input to ask for. Only
    # an outstanding verdict earns exit 4.
    return INPUT_REQUIRED if missing else OK


def apply(root, base, grim_path, grim, cfg, by_id, plan, verdicts,
          existing_edges, statuses, args) -> int:
    actions = []
    writes: dict[Path, str] = {}
    by_verdict = {v.cid: v for v in verdicts}

    for cid, intent in sorted(plan.intents.items()):
        component = by_id[cid]
        raw, _, body = read_component(component.path, grim)
        if component.path.is_symlink():
            raise Refusal(f"{component.path} is a symlink; refusing to write through it")
        text = writes.get(component.path, raw)
        if statuses.get(cid) != intent:
            text = splice_status(text, intent, grim)
        merged = sorted(set(existing_edges.get(cid, ())) | set(plan.edges.get(cid, ())))
        if merged and merged != sorted(existing_edges.get(cid, ())):
            # Merged as a set: a repeated target used to make check_edges report
            # the same successor twice as two live successors.
            text = splice_supersedes(text, merged, grim)
        writes[component.path] = text
        verdict = by_verdict.get(cid)
        changed = body_changed_since_base(root, base, component.path, body)
        actions.append({
            "id": cid, "from": statuses.get(cid), "to": intent,
            "outcome": verdict.outcome if verdict else "cascade",
            "evidence": verdict.evidence if verdict else "",
            "edges": merged,
            "amended": changed if changed else None,
            "new_on_branch": changed is None,
            "paths": component.fm.get("paths") or [],
        })

    touched = set(touched_paths(root, base))
    referenced = set()
    for path in cfg.specs.rglob("*.md") if cfg.specs.is_dir() else []:
        import yaml
        m = grim.FM_RE.match(path.read_bytes().decode("utf-8"))
        fm = yaml.safe_load(m.group(1)) if m else None
        for cid in (fm or {}).get("components") or []:
            if isinstance(cid, str):
                referenced.add(cid)

    report = render_report(actions, touched, referenced, grim, args.dry_run)
    print(report)

    snapshot = Path(tempfile.mkdtemp(prefix="reconcile-snapshot-"))
    originals = {path: path.read_bytes() for path in writes}
    for i, (path, data) in enumerate(originals.items()):
        (snapshot / f"{i}.bak").write_bytes(data)
    index = {path: snapshot / f"{i}.bak" for i, path in enumerate(originals)}

    def restore() -> None:
        for path, backup in index.items():
            path.write_bytes(backup.read_bytes())

    previous = signal.getsignal(signal.SIGINT)

    def on_interrupt(_signum, _frame):  # pragma: no cover - timing dependent
        restore()
        raise KeyboardInterrupt

    try:
        signal.signal(signal.SIGINT, on_interrupt)
        for path, text in writes.items():
            path.write_bytes(text.encode("utf-8"))
        try:
            assert_clean(root, grim_path, "after reconciling", errors_code=WRONG)
        except Refusal as exc:
            restore()
            raise Refusal(
                f"{exc}\n\nnothing was written; the store is exactly as it was", exc.code
            ) from None
        if args.dry_run:
            restore()
            print("\nDRY RUN: verified against grim, then rolled back. Nothing written.")
        else:
            print(f"\nWROTE {len(writes)} file(s). grim postflight: clean")
    except BaseException:
        restore()
        raise
    finally:
        signal.signal(signal.SIGINT, previous)
        shutil.rmtree(snapshot, ignore_errors=True)

    if args.json:
        print(json.dumps({"actions": actions, "dry_run": args.dry_run}, indent=2))
    return OK


def render_report(actions, touched, referenced, grim, dry_run) -> str:
    lines = []
    for a in actions:
        verb = {CURRENT: "PROMOTE", SUPERSEDED: "SUPERSEDE"}[a["to"]]
        if a["outcome"] == DROP:
            verb = "DROP"
        prefix = "WOULD " if dry_run else ""
        lines.append(f"{prefix}{verb:<10} {a['id']}   {a['from']} -> {a['to']}")
        if a["edges"]:
            lines.append(f"  supersedes: {', '.join(a['edges'])}")
        if a["new_on_branch"]:
            lines.append("  new on this branch (amendment not distinguishable from authoring)")
        elif a["amended"]:
            lines.append(f"  body amended since the merge-base ({a['amended']} line(s))")
        if a["to"] == CURRENT and a["paths"]:
            hits = [p for p in touched if grim._glob_hit(p, a["paths"])]
            if not hits:
                # Reported, never gated: the acceptance case for this very
                # feature is a backfilled draft whose paths the branch does not
                # touch, so a gate here would refuse the thing it exists to do.
                lines.append(
                    f"  NOTE declares {', '.join(a['paths'])}, which this branch does not "
                    f"touch; the promotion rests on your judgement that it shipped earlier"
                )
        if a["to"] == CURRENT and a["id"] not in referenced:
            lines.append("  NOTE no spec references this component")
        if a["evidence"]:
            lines.append(f"  because: {a['evidence']}")
        if a["outcome"] == DROP:
            lines.append("  WARNING never built, so no spec referencing only this may be stamped")
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(main())
