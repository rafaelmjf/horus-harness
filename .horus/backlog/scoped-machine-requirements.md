---
status: open
priority: medium
readiness: deferred
readiness_reason: "Defer trigger (a real project requirement declaration) is now satisfied by fabric; whether it un-defers is the 2026-07-20 refinement pass's call."
tier: medium
created: 2026-07-15
last_refined: 2026-07-20
vision_facet: "Continuity core"
type: feature
parallel: safe
surface: horus/machine_requirements.py, horus/terminal_tui.py, horus/dashboard.py
---

# Platform- and capability-scoped machine requirements

The current declaration treats every missing item as a project-wide warning. Mixed
projects can still do useful Linux work while Windows-only capabilities such as Power
BI Desktop or Word are absent, so a global warning would misstate readiness.

## Acceptance

- A requirement may name supported platforms and whether it is core readiness or an
  optional capability, while existing declarations retain their current meaning.
- The canonical inspector filters platform-inapplicable items and distinguishes a
  missing optional capability from a project-blocking requirement.
- Doctor, resume, dashboard, and TUI reuse that one result and render `needed_for`.
- The schema stays declarative: probes are still never executed and shell syntax stays
  rejected.
- Fixtures cover Power BI Desktop validation, CV document rendering, and an unchanged
  cross-platform CLI requirement.

## Execution

Implement only after onboarding provides real project declarations to test against.
No migration is blocked because platform-specific limitations can remain PRD prose in
the first pass.

## Reviews

- **2026-07-20 (owner, scope-cards gate):** scope widened — requirements also cover
  per-project **skill and CLI-version needs**, not just OS tools: the owner's fabric
  example ("this project requires certain skills and the horus CLI") is exactly this
  card's job, and fabric's 0.0.73 refresh provides the first real declaration the
  defer was waiting for (fabric needs `horus >= horus_min_version` plus specific
  bundled skills present). The skill-presence probe should reuse `skills.py`
  states, never a second checker. Un-defer decision belongs to backlog-refine.
