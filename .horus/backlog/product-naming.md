---
status: open
priority: low
tier: medium
created: 2026-07-16
vision_facet: "Distribution"
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

## Reviews

### 2026-07-16 — Rafael Figueiredo (manual)
Verdict: defer-name-keep-role

Owner (2026-07-16): the ROLE direction is settled — Horus is a repo-local product owner (Vision expanded this session). But keep the horus-harness package/repo name for now; renaming is mostly ceremony until first external distribution. Both listed candidates are REJECTED: horus-po (opaque suffix) and horus-continuity (under-describes a tool that also does discovery + roadmap grooming). Want a more CREATIVE name, not a literal one. Find/decide the official name when this card ships at first distribution; check PyPI availability then.
