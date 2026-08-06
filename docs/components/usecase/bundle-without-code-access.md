---
id: usecase-bundle-without-code-access
type: usecase
status: current
date: 2026-08-01
---

# Reading the project's decisions without code access

A reader with no way into the repository still needs what the store knows: an
agent drafting release notes with no checkout, a reviewer handed a file in a
ticket, a subagent with no filesystem access. The same artifact serves a
contributor coming back from weeks on other projects who wants the project's
current beliefs in one piece rather than a directory to navigate. grim render
emits a single self-contained markdown bundle carrying every live component,
ordered coherently and stamped with the store and commit it came from, so the
reader receives something they can be handed.
