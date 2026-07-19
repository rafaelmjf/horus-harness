---
status: open
priority: low
readiness: ready
autonomy: eligible
created: 2026-07-18
last_refined: 2026-07-19
vision_facet: "Introspection & self-improvement"
phase: converge
tier: medium
type: feature
parallel: safe
created_by: agent
surface: shared verification guidance — the managed-block "reproduce the gate" discipline (CLAUDE.md/AGENTS.md) and/or the bundled verify/horus-execution skill
---

# verify-guidance-long-running-services — "active + emits its signal", not "it installed"

**Why (2026-07-18, generalized from #322):** the `203/EXEC` crash-loop escaped the
live probe because it accepted `activating`/"unit installed" as proof. The general
lesson — a long-running service/daemon's verification means it reaches running
state AND emits its expected signal (journal/health), never just that it started —
belongs in SHARED guidance so it travels across models and accounts, not one
model's memory.

## How

- Add one line to the managed-block "reproduce the gate" / runtime-gate discipline
  (which already says "drive the real surface once; mocked tests bless nonexistent
  flags"): for a service/daemon, confirm it reaches `active`/running AND logs/serves
  its expected signal, not merely that the unit/process installed or started.
- Keep it concise; it's an extension of the existing runtime-gate rule, not a new
  section. If a bundled skill (verify / horus-execution) is the better home, add it
  there instead — pick ONE home, don't duplicate.
- Managed-block edits bump the block version; skill edits bump the skill version
  (existing rules).

## Acceptance

- The shared guidance names the long-running-service verification bar; it projects
  to Claude + Codex (managed block or bundled skill, whichever is chosen).
- No duplication across block and skill.

## Non-goals

- No automated service-health framework — this is the deterministic self-verify
  card's job (`service-installers-self-verify-active`); this card is the guidance rung.
