---
status: active
feature: "Campaign launch + provider-selector guard"
created: 2026-07-16
updated: 2026-07-16
---

# Execution Plan — Campaign launch + provider-selector guard

Two independent, owner-approved worker phases. The first adds the evidenced Campaign
entry point. The second fixes the provider-selector defect exposed by its initial
five-second launch failure. Their code surfaces do not overlap.

## Phase 1 — Campaign launch prompt + TUI affordance

- status: ready
- mode: delegated
- worker_agent: claude
- worker_model: `claude-sonnet-5` (provider selector; calibration key `sonnet-5`)
- worker_effort: medium
- worker_account: ambient/default Claude personal
- worker_tier: scoped-impl lead
- attempts: one executable retry; the prior `sonnet-5` selector failure consumed the
  original attempt without entering the task
- delegation_basis: owner-directed use of expiring personal-Claude weekly capacity
  plus useful parallel protection of the supervisor context; the scope is fenceable
  and disjoint from Phase 2.
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
the runtime frame. Any different model/account/effort/scope or another executable
attempt requires renewed owner approval.

## Phase 2 — Provider-valid selector preflight + consent contract

- status: ready
- mode: delegated
- worker_agent: claude
- worker_model: `claude-sonnet-5` (provider selector; calibration key `sonnet-5`)
- worker_effort: medium
- worker_account: ambient/default Claude personal
- worker_tier: scoped-impl lead
- attempts: 1
- delegation_basis: owner-directed use of expiring personal-Claude capacity plus
  useful parallelism; the adapter/datums/skills surface is disjoint from Phase 1 and
  keeps the supervisor from loading implementation detail.
- scope: Claude adapter/model preflight, canonical datum preservation, bundled
  decision/execution consent guidance, and focused tests. No TUI/routines changes.
- handoff: `.horus/temp/provider-model-selector-contract.md`
- gate: `uv run pytest -q tests/test_claude_adapter.py tests/test_datums.py tests/test_skills.py tests/test_cli.py`
- runtime_gate: supervisor proves a calibration-only Claude label is rejected before
  worktree/session creation and a full provider selector reaches the adapter unchanged
  using a token-free fake/subprocess probe.

### Constraints

- Do not auto-select, silently translate, fall back, or probe a provider with model
  tokens. The owner approves the exact executable selector.
- Keep provider naming rules inside the adapter boundary.
- Preserve the canonical `sonnet-5` datum series after Claude reports the resolved
  model ID.
- Do not edit `PRD.md`, backlog cards, or this execution plan; the supervisor owns
  durable continuity.

### Acceptance

Required CI must be green on the worker's exact PR SHA, then the supervisor drives
the token-free preflight probe. Any different model/account/effort/scope or another
attempt requires renewed owner approval.
