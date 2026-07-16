---
status: active
current_feature: "Post-merge watch correctness + process retrospective"
created: 2026-07-16
updated: 2026-07-16
---

# Execution Plan — two isolated Claude workers

Two disjoint, owner-approved phases will start from the same merged plan SHA. The work
and personal accounts keep usage attribution isolated. The remote open-model probe card
is not part of this plan and carries no authorization to connect.

## Phase 1 — Post-merge check settling

- status: ready
- mode: delegated
- worker_agent: claude
- worker_model: `claude-sonnet-5` (provider selector; calibration key `sonnet-5`)
- worker_effort: medium
- worker_account: `work`
- usage_at_approval: live isolated OAuth reading — 5h 0% (reset unknown), weekly 1% (resets 2026-07-19 22:59)
- attempts: 1
- delegation_basis: owner-directed use of available isolated Claude capacity plus a
  crisp, fenceable implementation that avoids loading detail into the Codex supervisor.
- scope: `horus/mergewatch.py`, `horus/cli.py`, `tests/test_mergewatch.py`, and focused
  CLI tests only.
- handoff: `.horus/temp/merge-watch-post-merge-checks.md`
- gate: `uv run pytest -q tests/test_mergewatch.py tests/test_cli.py`
- runtime_gate: supervisor watches known merge SHA `28a96c25271fff06a19f858a8a8cf571ac97530b`
  with a short explicit timeout and observes success after its applicable push checks.

### Constraints

- Keep caller-supplied SHAs pinned and retain open-PR head-movement protection.
- Do not weaken PR required checks or treat merged state/prose as gate evidence.
- Do not edit `.horus/`, skill sources/projections, or unrelated tests.
- Any retry, fallback, or envelope change requires renewed owner approval.

## Phase 2 — Evidence-first process retrospective skill

- status: ready
- mode: delegated
- worker_agent: claude
- worker_model: `claude-sonnet-5` (provider selector; calibration key `sonnet-5`)
- worker_effort: medium
- worker_account: ambient/default personal
- usage_at_approval: live OAuth reading — 5h 33% (resets 2026-07-16 19:19), weekly 10% (resets 2026-07-17 09:59)
- attempts: 1
- delegation_basis: owner-directed use of available personal-Claude capacity and
  protection of the remaining Codex supervisor budget; code surfaces are independent
  from Phase 1.
- scope: canonical `.agents/skills/process-retrospective/`, generated Claude/Codex
  projections, and focused skill tests only.
- handoff: `.horus/temp/process-retrospective-skill.md`
- gate: skill quick-validation plus `uv run pytest -q tests/test_skills.py`
- runtime_gate: supervisor compares canonical/Claude/Codex projections and checks the
  output contract against today's raw campaign artifacts without another model call.

### Constraints

- Follow the system skill-creator initialization and validation workflow, but match the
  repository's lean canonical-skill convention and add no unused resources/artifacts.
- Keep the skill advisory, event-driven, evidence-first, capped, and owner-gated exactly
  as the card specifies; do not fold it into product-audit or consolidation.
- Do not edit `.horus/`, merge-watch code/tests, or unrelated skill behavior.
- Independent model forward-testing is outside this one-attempt envelope.
- Any retry, fallback, or envelope change requires renewed owner approval.
