---
name: explain-diff
description: Turn a code diff into a rich, self-contained HTML guide (or plain markdown) that explains what changed, why, which design decisions are load-bearing, and what questions remain - so the human and the agent start the next iteration with shared understanding. Use when the user asks to explain a diff or change, walk through what was implemented, prepare a change walkthrough or PR explanation, or hand off a large change for review. Works on the current session's changes (warm) or any git range or PR (cold). Not a code review - this skill explains intent and implications, it does not judge or hunt for bugs.
---

# Explain a Diff

Produce an explanation guide for a change. You author a JSON payload (prose in
markdown); `render.py` does everything mechanical - validation, pulling hunk
code from git, diagrams, styling, interactivity - at zero token cost. Never
hand-write HTML. Never paste code into the payload; point at it.

## Pipeline

1. Resolve the diff and mode:
   - **warm**: the change was made in this session. Rationale comes from the
     conversation; label decisions `"provenance": "stated"`.
   - **cold**: an arbitrary range, branch, or PR (`gh pr checkout` first).
     Read the code, infer intent, and label decisions `"provenance": "inferred"`.
     Never present inferred rationale as stated.
2. Author `explanation.json` (see Authoring below). Put it in the scratch
   directory unless the user wants it kept.
3. Render and open:

   ```bash
   uv run <skill-dir>/render.py explanation.json --repo <repo-root> --open --write-hashes
   ```

   Markdown target (PR descriptions, docs): add `--format md`.
   The script fails loudly on schema violations, bad hunk refs, dangling ids,
   or malformed mermaid - fix the payload and re-run. A drift WARNING means
   the code changed since hashes were written; re-check your annotations.

## Analysis method

Build the explanation around intent, not files:

1. **Verdict first** - one sentence: what does the system do now that it
   did not do before. This is the `verdict` field; everything hangs off it.
2. **Group hunks into 2-5 moves** - e.g. "introduce outbox table", "reroute
   send path". Never walk file-by-file. Mechanical churn (renames, imports,
   lockfiles) goes in one `fallout` section, acknowledged and out of the way.
3. **Surface load-bearing decisions.** A decision is load-bearing if
   reversing it later would cost more than re-doing this diff, or if other
   parts of the change silently assume it. Each gets a `decision` section
   with `reversal_cost` and rejected `alternatives`.
4. **Implications** - what the reader's mental model must update: new
   invariants, changed edge behavior, operational consequences (migrations,
   config, perf). Use `narrative` or `comparison` sections.
5. **Open questions** - genuine decision points, each phrased so an answer
   unblocks the next loop. These become `question` sections and feed the
   page's feedback composer (the user clicks Approve/Discuss/Change and
   pastes the composed prompt back to you).

Caps: at most ~6 `hunk` sections - pick only load-bearing code; the guide is
a lens, not an archive. Use a `diagram` only when structure genuinely helps
(data flow, state machines, before/after topology) - wire `links` from node
names to decision/question ids so the diagram is clickable.

## Authoring the payload

Schema: `schema.json` (validated on render). Reference: `examples/payload.example.json`.

Section vocabulary:

| Type | Use for |
|---|---|
| `narrative` | Prose under a heading (markdown) |
| `diagram` | Mermaid source plus optional `links` {node label -> "#id"} |
| `decision` | Load-bearing choice: id, provenance, reversal_cost, alternatives |
| `hunk` | `{file, lines "N-M", ref}` - code is extracted by render.py. Use `"ref": "WORKTREE"` for uncommitted changes, a commit/branch otherwise |
| `comparison` | Before/after, two markdown columns |
| `question` | Open question with id |
| `fallout` | Collapsed list of mechanical changes |

Rules:
- Ids are lowercase (`d1`, `q1`, ...) and unique; diagram `links` must target them.
- No emojis anywhere in the payload.
- Always pass `--write-hashes` on first render so later re-renders detect drift.
- Line numbers in `hunk` refer to the file at `ref` (for WORKTREE: as on disk
  now). Verify with `sed -n 'START,ENDp' file` before authoring.

## Sizing

Small diff (< 100 lines): verdict, one narrative, 1-2 decisions or questions.
Skip diagrams. Medium: add hunks and a comparison. Large: full vocabulary,
but still 2-5 moves - if you need more, the change should have been split,
and saying so is part of the explanation.
