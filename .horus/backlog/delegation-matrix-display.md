---
status: open
priority: medium
tier: sonnet
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/cli.py, horus/datums.py, horus/skills.py (rubric template)
shipped: "2026-07-12 — capability built, PR open (branch feat/capabilities-matrix, PR #166). `horus capabilities --matrix` joins datums.build_model_rollup (tier ladder + measured datums) with new structured shape->tier / tier-trust->verification tables in skills.py (DELEGATION_SHAPE_TIERS, DELEGATION_VERIFICATION_DIAL) pulled from the delegation-rubric skill essence — no third source of truth. Display-only: --stdout emits JSON (tiers/roles/verification_dial), human default renders the ladder; a boundary test walks every JSON key and asserts no pick/route field. Delegation-rubric template also updated to keep older-but-capable/prior-frontier models in the roster (pick by capability, not recency) — skill version bumped 1->2. 1184 tests green."
---

# Display the delegation decision matrix from the CLI (agent-first)

**Owner ask (2026-07-12):** the decision matrix that powers dispatch suggestions
lives in harness (data: `capabilities --models` → `datums.render_model_rollup`;
logic: the `delegation-rubric` skill template in `skills.py`). Add a command that
displays it cleanly so **any agent OR user can call the right decision info
deterministically** instead of reading/parsing the rubric skill markdown.

**Agent-first (clarified by owner):** primary consumer is an agent making a dispatch/
execution decision — so it MUST emit machine-parseable **`--stdout` JSON** (tiers,
roles, live datums, verification dial), with a human-readable default. Same ethos as
`horus capabilities`. **Display-only — the hard boundary holds: it renders, it never
auto-picks or auto-routes a model.**

## What it renders

One view joining the two existing sources (do not fork a third source of truth):
- **Tier ladder** — each model's owner-prior `tier` + measured datums
  (`clean/closed/total`, recent `last_outcomes`) + `caution`/`guard`.
- **Shape → tier → verification** — the rubric's mapping (scoped-impl/novel/mechanical
  → tier; proven→observe-CI, unproven→CI+probe, runtime→owner-eyeball).

## Shape decision (recommendation — owner input 2026-07-12)

**DISPLAY-ONLY — the name must NOT read like an action.** Owner flagged that a bare
`horus delegation` sounds like it *starts* a delegation. It does not (and cannot — the
hard boundary forbids auto-routing). Anchor it under the already-read-only command so
the semantics are unambiguous: **recommended `horus capabilities --matrix`** (inherits
"reads and prints, never acts"). If a top-level verb is preferred instead, it must
carry an explicit display verb — `horus delegation show` — never the bare noun. Lock
one with owner before building.

Reuse `datums.render_model_rollup`; pull the shape→tier→verify table from the rubric
essence so it stays single-sourced. No pick/route field — assert its absence in a test.

## Fold in: older-but-capable models stay in the roster

Coupled owner point (2026-07-12): prior-frontier models (e.g. gpt-5.5/5.4, sonnet-4.6)
were frontier not long ago and may still be strong AND cheaper for current scoped/
mechanical work — don't dismiss by recency. Update the `delegation-rubric` template
(`skills.py`) to encode: **keep older-but-capable models in the test roster; pick by
capability-for-the-task, not recency; gather datums.** The display command should
surface any such models present in `capabilities.toml`. (Seeding specific priors is
the separate `older-models-in-roster` card.)

## Verification

`--stdout` emits valid JSON with tiers+datums+dial; human view renders the ladder;
boundary test asserts no pick/route field exists. CI green.
