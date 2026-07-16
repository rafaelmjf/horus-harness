---
status: active
feature: "Optional Campaign Supervision launch from the terminal TUI"
created: 2026-07-16
updated: 2026-07-16
---

# Execution Plan — Campaign Supervision launch

One bounded worker phase. The completed Drive-to-Git campaign in `horus-agent`
proved the cockpit contract through ordinary Resume; this phase adds only the
optional dedicated entry point now that its semantics are evidenced.

## Phase 1 — Campaign launch prompt + TUI affordance

- status: ready
- mode: delegated
- worker_agent: claude
- worker_model: sonnet-5
- worker_effort: medium
- worker_account: ambient/default Claude personal
- worker_tier: scoped-impl lead
- attempts: 1
- delegation_basis: owner-directed use of expiring personal-Claude weekly capacity
  plus useful parallel protection of the supervisor context; the scope is fenceable
  and no longer overlaps the detached-receipt work.
- scope: `horus/terminal_tui.py`, `horus/routines.py`, and focused tests only.
- handoff: `.horus/temp/campaign-supervision-launch.md`
- gate: `uv run pytest -q tests/test_terminal_tui.py tests/test_terminal_sessions.py tests/test_routines.py`
- runtime_gate: supervisor drives one non-mutating terminal-TUI frame showing
  Campaign as optional and visibly distinct from Fleet Review.

### Constraints

- Direct project launch remains the default path.
- Ask for the campaign outcome and target set; do not invent a project archetype.
- Apply need-first inline-versus-dispatch judgment per bounded unit.
- Never auto-select a model/account, auto-spawn a worker, or treat cross-project
  scope alone as a dispatch dividend.
- Target repositories retain branch/PR/gate/continuity authority.
- Do not edit `PRD.md`, backlog cards, or this execution plan; the supervisor owns
  durable continuity.

### Acceptance

Required CI must be green on the worker's exact PR SHA, then the supervisor drives
the runtime frame. Any different model/account/effort/scope or a second attempt
requires renewed owner approval.
