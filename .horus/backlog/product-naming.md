---
status: open
priority: low
readiness: deferred
readiness_reason: "A strong front-runner emerged (horus-builder, 2026-07-21 — see Candidates/Reviews). The rename itself stays deferred until first external distribution (cost unchanged); the name is effectively pre-decided pending that + a PyPI-availability check + confirming the slight identity rebroadening it implies."
tier: medium
created: 2026-07-16
last_refined: 2026-07-21
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
- **horus-builder** (owner, 2026-07-21): **leading candidate.** Reframes the identity as
  "a toolbox gathering existing tools toward a purpose" — general in nature; already used
  to build itself, other products, and professional data/analytics work. *Pros:* clearly
  beats "harness" (no longer implies running the agent loop), approachable, general, and
  the self-building story is memorable. *Cons to weigh:* (1) "builder" is common/generic
  in software (crowded, low differentiation) and is functional rather than the *creative*
  name earlier wanted; (2) it names the *construction* layer — which the agent CLIs
  already do — while Horus's differentiator is the continuity/PO/memory/direction layer
  *above* building, so it risks pointing one layer too low. Both cons soften if the
  intended identity really is "general build toolbox (continuity as one tool)" rather than
  "repo-local PO" — a small, deliberate **identity rebroadening** to confirm (and reflect
  in the Vision tagline) when the name ships.

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

### 2026-07-21 — Rafael Figueiredo (manual)
Verdict: front-runner-identified

Owner: **horus-builder** is the leading candidate — it fits the lived reality (a general toolbox used to build itself, other products, and data/analytics work) and clearly beats harness/po/continuity. The rename stays DEFERRED until first external distribution (cost unchanged); the name is effectively pre-decided pending that + a PyPI-availability check. Open flag to resolve at ship time, not silently: "builder" subtly rebroadens the identity from "repo-local PO" toward "general build toolbox" — confirm that reframe and update the Vision tagline then. Agent assessment: builder is functional (not the "creative" earlier wanted) and names the construction layer rather than the continuity differentiator — acceptable IF the toolbox identity is the one intended. Note vs the earlier "creative not literal" steer: the owner has effectively shifted toward clear-and-fitting over creative-but-opaque, which is a reasonable update given why po/continuity were rejected.
