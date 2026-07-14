---
date: 2026-07-14T23:29:08
agent: codex
account: personal
environment: host
project: horus-harness
status: in-progress
summary: "Implemented one safe project-machine readiness result across doctor, resume, dashboard, and TUI; first fabric declaration remains before closure."
---

# project-declared machine readiness across all launch surfaces

## Summary

Implemented the owner-expanded `project-machine-requirements` card with the TUI
as a fourth consumer, without introducing a second parser or probe path.

## Key Points

- Added a dependency-free `.horus/requirements.md` parser for a narrow
  YAML-like frontmatter schema (`tools`/`configs`, with `name`, `probe`,
  `install`, and `needed_for`).
- Put safety in the probe model: a committed tool probe is only a
  `shutil.which` executable-name lookup; a config probe is only a path-existence
  check. Shell command text is rejected and never executed.
- `doctor project` emits canonical readiness findings; `horus resume` prepends
  the canonical missing-machine warning.
- Dashboard project cards/details show a readiness badge and warning panel; the
  TUI project frame shows the same warning above Resume/Fresh launch choices.
- Added user-facing schema/safety documentation.
- Verification: 475 impacted tests and the full 1,455-test suite passed. A live
  isolated declaration produced the expected warning in doctor, resume,
  dashboard, and the actual TUI frame renderer.
- Consolidation found 14 active notes after this note was created; the two
  oldest already-distilled notes were moved to the local archive, leaving 12.

## Next

- Add the first real declaration to fabric, verify it through all four
  consumers, then finish the harness PR and ask before the next backlog card.
