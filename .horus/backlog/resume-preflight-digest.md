---
title: "One-verb resume preflight: bundle the session-start ritual into a model-ready digest"
status: open
priority: high
tier: sonnet
parallel: safe
type: task
surface: horus resume / status / usage / fetch-check, frontmatter projection, sessions registry
created: 2026-07-14
created_by: overseer
---

# Resume preflight digest — one verb, model-ready output

Owner ask 2026-07-14 (cockpit retrospective). Every session start runs the same
deterministic ritual as ~8 separate commands whose verbose outputs are loaded piecemeal
into the model's context: `git fetch --all --prune` + branch-vs-origin, `horus status`,
per-project PRD frontmatter reads, `horus usage check` ×2 targets, version-floor check,
active-session/collision scan. None of it needs a model; the model needs the DIGEST.

Extend `horus resume` (or add a preflight mode) to do all of it in one verb and emit ONE
compact block designed for LLM consumption:

- fetch + git freshness per relevant repo (ahead/behind/dirty/upstream-gone),
- usage for BOTH targets with freshness tags (reuse the datum-envelope snapshot reader),
- version floor vs `horus_min_version`,
- the target project's frontmatter handoff (current_focus/next_action/next_prompt/
  execution_recommendation) — and in cockpit mode, every registered project's,
- open (unclosed) datums, running/stale sessions + collision warnings,
- any hygiene warnings (`close --check`-style), one line each.

Design constraints: **read-only projection + the sanctioned fetch refresh** (offer
`--no-fetch`); deterministic signals only — it surfaces, never interprets or recommends
(no ceded judgment, no auto-routing); lean status lines, not command dumps; `--stdout`
JSON for tooling. Absorbs/links the `fleet-frontmatter-reader` and
`lean-cockpit-context-rewarm` asks; complements `resume-session-liveness-reconcile`.

Acceptance: a cockpit session starts work after ONE command whose output fits in one
screen; focused tests; live run on this machine covering cockpit (fleet) + single-project
modes.
