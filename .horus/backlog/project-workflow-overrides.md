---
status: open
priority: medium
tier: medium
created: 2026-07-15
vision_facet: "Continuity core"
type: feature
parallel: safe
surface: horus/config.py, horus/integration.py, horus/dashboard.py
---

# Project-local workflow policy overrides

Workflow integration policy is currently machine-global even though code products,
generated publishing repositories, and high-frequency knowledge curation can require
different branch/commit/merge postures on the same machine.

## Acceptance

- A repo-local declaration can override integration, commit, and merge policy, with
  the machine policy as the explicit fallback.
- The resolved policy is visible in doctor/resume/TUI before an agent acts.
- Invalid project values fail visibly instead of silently falling back.
- Existing global configuration and repositories without overrides behave unchanged.
- Tests cover branch/PR software work, reviewed CV automation, and a direct-push content
  workflow without adding project archetypes.

## Execution

Defer until an onboarded content project demonstrates which override it actually
needs. Migrations themselves should use the default branch-to-PR workflow.
