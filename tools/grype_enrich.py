#!/usr/bin/env python3
"""grype_enrich -- merge grype JSON with MITRE CVE Record context for agent triage.

Input:  grype `-o json` output (via -f FILE, or piped on stdin).
        Also accepts a plain list of CVE IDs (args, or newline file) for ad-hoc use.
Output: one enriched record per grype match, combining:
          - grype's own scoring, passed through untouched
            (severity, cvss, epss, risk, KEV, CWE, fix state, purl, locations)
          - a derived package `class` (os-package | application-dependency | ...)
          - CVE-Record context pulled from MITRE CVE Services (no API key):
            authoritative description, CWE, upstream affected ranges,
            affected modules/routines (code-path signal when present),
            tagged references, and CISA ADP SSVC decision points.
          - a compact `triage` block distilling the signals an agent needs.

The point is context for a downstream agent to judge *reachability* -- e.g. a
perl `deb` CVE in a Python service is usually base-image noise, while a CPython
xml-parsing CVE needs investigation. The tool surfaces the signals; it does not
render the verdict (class alone does NOT separate those two -- both are `deb`).

Notes / limits:
  - MITRE `affected` is the UPSTREAM range. The distro-fixed version is grype's
    `fix.versions` (from the Debian/Ubuntu/etc. security tracker). Both are kept.
  - GHSA-only matches (no aliased CVE) and very-new CVEs have no MITRE record;
    the tool falls back to grype's description and flags it. For GHSA richness,
    OSV (https://api.osv.dev/v1/vulns/{id}) is the better source -- not wired in.
  - Stdlib only. MITRE responses are cached per CVE within a run.

Usage:
  grype my-fastapi:latest -o json | python grype_enrich.py > enriched.json
  python grype_enrich.py -f scan.json --min-severity high --summary
  python grype_enrich.py -f scan.json --jsonl --no-enrich
  python grype_enrich.py CVE-2025-1234 CVE-2024-5678        # ad-hoc CVE mode
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

MITRE = "https://cveawg.mitre.org/api/cve/{cve}"
UA = {"User-Agent": "grype-enrich/1.0"}

# Package types that live in the base OS image rather than the app's dep graph.
OS_TYPES = {
    "deb", "rpm", "rpm-source", "apk", "portage", "alpm", "nix",
    "msrc-kb", "linux-kernel", "linux-kernel-module",
}
SEV_RANK = {"negligible": 0, "unknown": 1, "low": 1, "medium": 2, "high": 3, "critical": 4}


# --------------------------------------------------------------------------- #
# HTTP + MITRE CVE Record parsing
# --------------------------------------------------------------------------- #
def _get(url: str, retries: int = 3, delay: float = 6.0) -> dict:
    req = urllib.request.Request(url, headers=UA)
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise
            if e.code in (429, 503) and attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
                continue
            raise
    raise RuntimeError("unreachable")


def _en(items, key, lang_key="lang"):
    for it in items or []:
        if it.get(lang_key) == "en":
            return it.get(key)
    return items[0].get(key) if items else None


def _cwes_from_problemtypes(problem_types):
    out, seen = [], set()
    for pt in problem_types or []:
        for d in pt.get("descriptions", []) or []:
            cid, name = d.get("cweId"), d.get("description")
            k = cid or name
            if k and k not in seen:
                seen.add(k)
                out.append({"id": cid, "name": name})
    return out


def _fmt_affected(affected):
    out = []
    for a in affected or []:
        default = a.get("defaultStatus")
        ranges = []
        for v in a.get("versions", []) or []:
            status = v.get("status", default)
            base, lt, lte = v.get("version"), v.get("lessThan"), v.get("lessThanOrEqual")
            if lt is not None:
                ranges.append(f">={base} <{lt} [{status}]")
            elif lte is not None:
                ranges.append(f">={base} <={lte} [{status}]")
            elif base is not None:
                ranges.append(f"{base} [{status}]")
        out.append({
            "product": a.get("product"),
            "vendor": a.get("vendor"),
            "default_status": default,
            "ranges": ranges,
            "modules": a.get("modules") or [],
            "program_files": a.get("programFiles") or [],
            "program_routines": [r.get("name") for r in (a.get("programRoutines") or []) if r.get("name")],
        })
    return out


def _refs(refs):
    return [{"url": r.get("url"), "tags": r.get("tags", [])} for r in (refs or []) if r.get("url")]


def _dedupe_refs(refs):
    seen, out = set(), []
    for r in refs:
        if r["url"] not in seen:
            seen.add(r["url"])
            out.append(r)
    return out


def parse_record(data: dict) -> dict:
    meta = data.get("cveMetadata", {})
    containers = data.get("containers", {})
    cna = containers.get("cna", {})
    adps = containers.get("adp", []) or []

    description = _en(cna.get("descriptions"), "value")
    cwes = _cwes_from_problemtypes(cna.get("problemTypes"))
    affected = _fmt_affected(cna.get("affected"))
    references = _refs(cna.get("references"))
    ssvc = None

    for adp in adps:
        if not cwes:
            cwes = _cwes_from_problemtypes(adp.get("problemTypes"))
        if not affected:
            affected = _fmt_affected(adp.get("affected"))
        references += _refs(adp.get("references"))
        for m in adp.get("metrics", []) or []:
            other = m.get("other") or {}
            if other.get("type") == "ssvc":
                opts = {}
                for o in (other.get("content", {}) or {}).get("options", []) or []:
                    opts.update(o)
                ssvc = opts or ssvc

    return {
        "state": meta.get("state"),
        "description": description,
        "cwe": cwes,
        "affected": affected,
        "references": _dedupe_refs(references),
        "ssvc": ssvc,
        "source": "mitre-cve-services",
    }


def fetch_record(cve: str, cache: dict, delay: float) -> dict | None:
    if cve in cache:
        return cache[cve]
    try:
        rec = parse_record(_get(MITRE.format(cve=cve), delay=max(delay, 6.0)))
    except urllib.error.HTTPError as e:
        rec = None if e.code == 404 else {"error": f"http {e.code}", "source": "mitre-cve-services"}
    except Exception as e:  # network / parse
        rec = {"error": str(e), "source": "mitre-cve-services"}
    cache[cve] = rec
    return rec


# --------------------------------------------------------------------------- #
# grype normalization
# --------------------------------------------------------------------------- #
def classify(ptype, language):
    if language:
        return "application-dependency"
    if ptype in OS_TYPES:
        return "os-package"
    if ptype == "binary":
        return "binary"
    return "unknown"


def _grype_cwes(cwes):
    out = []
    for c in cwes or []:
        if isinstance(c, str):
            out.append(c)
        elif isinstance(c, dict):
            out.append(c.get("id") or c.get("cwe") or c.get("name"))
    return [c for c in out if c]


def normalize_match(match: dict) -> dict:
    v = match.get("vulnerability", {})
    art = match.get("artifact", {})
    related = match.get("relatedVulnerabilities", []) or []

    ids = [i for i in ([v.get("id")] + [r.get("id") for r in related]) if i]
    cve = next((i for i in ids if i.upper().startswith("CVE-")), None)
    aliases = [i for i in ids if i != cve]

    ptype = art.get("type")
    language = art.get("language") or None
    md = match.get("matchDetails", []) or []
    epss = (v.get("epss") or [{}])[0]
    cvss0 = (v.get("cvss") or [{}])[0]
    fix = v.get("fix", {}) or {}

    return {
        "id": v.get("id"),
        "cve": cve,
        "aliases": aliases,
        "package": {
            "name": art.get("name"),
            "version": art.get("version"),
            "type": ptype,
            "language": language,
            "class": classify(ptype, language),
            "purl": art.get("purl"),
            "locations": [l.get("path") for l in art.get("locations", []) or [] if l.get("path")],
            "upstreams": [u.get("name") for u in art.get("upstreams", []) or [] if u.get("name")],
            "match_types": sorted({d.get("type") for d in md if d.get("type")}),
            "matchers": sorted({d.get("matcher") for d in md if d.get("matcher")}),
        },
        "fix": {"state": fix.get("state"), "versions": fix.get("versions", []) or []},
        "grype": {
            "severity": v.get("severity"),
            "cvss_base": (cvss0.get("metrics") or {}).get("baseScore"),
            "epss": epss.get("epss"),
            "epss_percentile": epss.get("percentile"),
            "risk": v.get("risk"),
            "kev": bool(v.get("knownExploited")),
            "cwes": _grype_cwes(v.get("cwes")),
            "namespace": v.get("namespace"),
            "description": v.get("description"),
        },
    }


def build_triage(rec: dict) -> dict:
    g = rec["grype"]
    cr = rec.get("cve_record") or {}
    affected = cr.get("affected") or []
    refs = cr.get("references") or []
    ssvc = cr.get("ssvc") or {}
    exploit_ref = any(
        t.lower() == "exploit" for r in refs for t in (r.get("tags") or [])
    )
    code_path = any(
        a.get("modules") or a.get("program_files") or a.get("program_routines")
        for a in affected
    )
    return {
        "class": rec["package"]["class"],
        "fix_available": rec["fix"]["state"] == "fixed" and bool(rec["fix"]["versions"]),
        "fix_state": rec["fix"]["state"],
        "kev": g["kev"],
        "epss": g["epss"],
        "risk": g["risk"],
        "ssvc_exploitation": ssvc.get("Exploitation"),
        "exploit_reference": exploit_ref,
        "has_code_path_detail": code_path,
        "record_state": cr.get("state"),
    }


# --------------------------------------------------------------------------- #
# Input handling
# --------------------------------------------------------------------------- #
def load_input(args) -> tuple[str, list]:
    """Return (mode, items). mode is 'grype' (list of matches) or 'cve' (list of ids)."""
    if args.cves:
        return "cve", list(args.cves)

    raw = None
    if args.file and args.file != "-":
        with open(args.file) as fh:
            raw = fh.read()
    elif args.file == "-" or not sys.stdin.isatty():
        raw = sys.stdin.read()
    if not raw:
        raise SystemExit("no input: give a grype JSON via -f/stdin, or CVE IDs as args")

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        ids = [ln.strip() for ln in raw.splitlines() if ln.strip().upper().startswith("CVE-")]
        return "cve", ids

    if isinstance(data, dict) and "matches" in data:
        return "grype", data["matches"]
    if isinstance(data, list) and all(isinstance(x, str) for x in data):
        return "cve", data
    raise SystemExit("unrecognized input: expected grype JSON (`matches`) or a CVE-ID list")


def cve_only_record(cve: str, cache: dict, delay: float) -> dict:
    rec = {"id": cve, "cve": cve, "aliases": [],
           "package": {"class": "unknown"}, "fix": {"state": None, "versions": []},
           "grype": {"severity": None, "epss": None, "risk": None, "kev": False,
                     "cwes": [], "description": None}}
    r = fetch_record(cve, cache, delay)
    rec["cve_record"] = r or {"note": "no MITRE record (GHSA-only, too new, or rejected)"}
    rec["triage"] = build_triage(rec)
    return rec


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def emit_summary(recs):
    for r in recs:
        p, g, t = r["package"], r["grype"], r.get("triage", {})
        cr = r.get("cve_record") or {}
        head = f"{r.get('cve') or r['id']}  [{p.get('class')}]"
        pkg = f"{p.get('type') or '?'}:{p.get('name')} {p.get('version') or ''}".strip()
        fix = f"fix:{r['fix']['state']}" + (f"->{','.join(r['fix']['versions'])}" if r["fix"]["versions"] else "")
        score = f"sev={g.get('severity')} epss={g.get('epss')} risk={g.get('risk')}"
        flags = []
        if t.get("kev"):
            flags.append("KEV")
        if t.get("ssvc_exploitation"):
            flags.append(f"ssvc:{t['ssvc_exploitation']}")
        if t.get("exploit_reference"):
            flags.append("exploit-ref")
        if cr.get("state") and cr["state"] != "PUBLISHED":
            flags.append(cr["state"])
        cwe = ",".join(g.get("cwes") or [c.get("id") for c in cr.get("cwe", []) if c.get("id")])
        print(f"\n{head}  {pkg}  {fix}  {score}" + (f"  {' '.join(flags)}" if flags else ""))
        if cwe:
            print(f"    CWE: {cwe}")
        if p.get("locations"):
            print(f"    at: {', '.join(p['locations'][:4])}")
        desc = cr.get("description") or g.get("description")
        if desc:
            print(f"    {desc.strip().splitlines()[0][:300]}")
        for a in cr.get("affected", []) or []:
            bits = []
            if a.get("ranges"):
                bits.append("upstream " + "; ".join(a["ranges"][:3]))
            if a.get("modules"):
                bits.append("modules=" + ",".join(a["modules"]))
            if a.get("program_routines"):
                bits.append("routines=" + ",".join(a["program_routines"]))
            if bits:
                print(f"    {' | '.join(bits)}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Enrich grype JSON with MITRE CVE-Record context.")
    ap.add_argument("cves", nargs="*", help="ad-hoc CVE IDs (bypasses grype input)")
    ap.add_argument("-f", "--file", help="grype JSON file, or '-' for stdin")
    ap.add_argument("--no-enrich", action="store_true", help="normalize grype only; no network")
    ap.add_argument("--delay", type=float, default=0.0, help="seconds between MITRE calls")
    ap.add_argument("--min-severity", help="drop matches below this grype severity")
    ap.add_argument("--fixed-only", action="store_true", help="keep only matches with a fix available")
    ap.add_argument("--keep-rejected", action="store_true", help="keep CVEs whose record state is REJECTED")
    ap.add_argument("--jsonl", action="store_true", help="emit one JSON object per line")
    ap.add_argument("--summary", action="store_true", help="human-readable summary instead of JSON")
    args = ap.parse_args()

    mode, items = load_input(args)
    cache: dict = {}
    min_rank = SEV_RANK.get((args.min_severity or "").lower()) if args.min_severity else None

    recs = []
    if mode == "cve":
        for cve in items:
            recs.append(cve_only_record(cve, cache, args.delay) if not args.no_enrich
                        else {"cve": cve, "note": "enrichment skipped"})
    else:
        for i, match in enumerate(items):
            rec = normalize_match(match)
            if min_rank is not None and SEV_RANK.get((rec["grype"]["severity"] or "").lower(), -1) < min_rank:
                continue
            if args.fixed_only and not (rec["fix"]["state"] == "fixed" and rec["fix"]["versions"]):
                continue
            if not args.no_enrich and rec["cve"]:
                if i and args.delay:
                    time.sleep(args.delay)
                r = fetch_record(rec["cve"], cache, args.delay)
                rec["cve_record"] = r or {"note": "no MITRE record (GHSA-only, too new, or rejected)"}
            rec["triage"] = build_triage(rec)
            state = (rec.get("cve_record") or {}).get("state")
            if state == "REJECTED" and not args.keep_rejected:
                continue
            recs.append(rec)

    if args.summary:
        emit_summary(recs)
    elif args.jsonl:
        for r in recs:
            print(json.dumps(r, ensure_ascii=False))
    else:
        print(json.dumps(recs, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())