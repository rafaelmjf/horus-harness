---
status: open
priority: low
tier: sonnet
created: 2026-07-15
vision_facet: "Distribution"
type: feature
parallel: safe
surface: horus/initialize.py, horus/templates.py, horus/doctor_machine.py
---

# horus init optionally scaffolds a minimal project CI gate

Two freshly created private repos in the migration campaign (pbi-ecosystem, rmjf-vault)
had **no CI at all**, so the "reproduce the gate — observe a required check green on the
exact commit" discipline had nothing to observe. Acceptance fell back entirely to the
cockpit's manual file-level checks plus the owner's eyeball. A newly onboarded repo
should be able to have a deterministic green gate from day one.

## Acceptance

- `horus init` can scaffold a minimal, opt-in CI workflow (a `--ci` flag or a prompt)
  that runs the checks Horus already knows: `horus doctor project`, `git lfs fsck` when
  LFS is in use, and a project build/test step when one is detectable (else a no-op that
  still goes green).
- The scaffold is a plain committed workflow file the repo owns; it is not required and
  existing repos are untouched unless asked.
- The generated gate passes on a clean freshly-migrated repo (doctor ok, lfs fsck ok).
- Interacts cleanly with [[project-workflow-overrides]] (a repo may declare it wants no
  CI) — the scaffold respects that rather than forcing a workflow.
- Tests cover: scaffold on a repo with LFS, scaffold on a plain docs/vault repo, and
  skip when the project opts out.

## Boundaries

- Minimal and generic; do not encode per-language build matrices or archetypes. Detect a
  build step or emit a doctor-only gate.
- The gate is for *acceptance observability*, not deployment; deploy pipelines stay
  project-owned (e.g. the rmjf-notes Pages workflow).

## Reviews

- 2026-07-16 — Owner session demoted this to the instruction rung (priority
  medium→low): an agent asked to onboard a repo can already write a minimal CI
  workflow — existing capability defeats the implementation. New first step: one line
  in the onboard/migration skill guidance ("ensure a deterministic CI gate exists;
  scaffold a doctor-only workflow if absent"). Promote back to scaffold *code* only
  if agents observably fail at it repeatedly. Per the controls ladder, the cheap rung
  goes first.
