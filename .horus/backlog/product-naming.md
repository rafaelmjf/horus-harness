---
status: open
priority: low
tier: sonnet
created: 2026-07-16
type: ops
parallel: safe
surface: pyproject.toml (name/description), README tagline, GitHub about, scripts/deploy-hosted.sh, managed-block install text
---

# Product naming — track candidates, decide at distribution

`horus-harness` no longer describes the product: in agent-land a "harness" runs the
agent loop (Claude Code / Codex are the harnesses), and the PRD explicitly disclaims
orchestration. The product is a cross-model, repo-local continuity layer. Renaming the
PyPI package now costs real work (new package, deprecation shim, hosted deploy, install
docs, three-OS smoke) for zero functional gain — so this card is an idea ledger, not a
work order. Decide only at a real distribution milestone (first external users / public
launch).

## Candidates (append via `horus backlog review`)

- **horus-po** (owner, 2026-07-16): "product owner" — the lens is sharp (Horus keeps
  the PRD, backlog, shipped ledger, closure ritual, audits: a PO's memory and rituals,
  made repo-local so any agent can pick up the role). The string is weak: "po" is
  opaque/ambiguous as a suffix and doesn't self-describe.
- **horus-continuity** (audit discussion, 2026-07-16): honest and literal; less
  evocative.

## Acceptance

- Cheapest rung first (independent of rename): pyproject description, README tagline,
  and GitHub about all say "project continuity layer for coding-agent CLIs" — can ship
  any time.
- The rename decision itself stays deferred until first external distribution; check
  PyPI availability for the chosen name before attachment.
