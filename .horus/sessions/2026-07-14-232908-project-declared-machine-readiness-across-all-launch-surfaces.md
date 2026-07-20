---
date: 2026-07-14T23:29:08
agent: codex
account: personal
environment: host
project: horus-harness
status: complete
summary: "Shipped one safe project-machine readiness result across doctor, resume, dashboard, and TUI, verified against fabric's existing declaration."
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
- The fetched remote-authoritative fabric repo already carried the promised
  declaration. Compatibility was adjusted to its existing contract: tool probes
  may include descriptive argv such as `fab --version` (only `fab` is looked up;
  nothing runs), and configs use `path:` with an optional display name.
- Verification: 475 impacted tests and the full 1,455-test suite passed. A live
  isolated declaration produced the expected warning in doctor, resume,
  dashboard, and the actual TUI frame renderer.
- Live first-consumer proof: fabric's unchanged declaration parsed with no
  issues and all four surfaces warned that this machine lacks `fab`, `pbir`,
  and `~/.config/pbir/config.json` before its deploy-oriented next action.
- Consolidation found 14 active notes after this note was created; the two
  oldest already-distilled notes were moved to the local archive, leaving 12.

## Next

- Finish PR #237, then ask before `datum-outcome-taxonomy-void-and-death`.

## Checkpoints (auto-harvested)

- `105c41a` feat: add project machine readiness across surfaces
- `2f2c7b3` fix: honor existing machine requirement declarations

- `2160ea6` feat: add project machine readiness across surfaces (#237)
  * feat: add project machine readiness across surfaces
  * fix: honor existing machine requirement declarations
  * Update Horus continuity (closure)

- `2bac6ad` Update Horus continuity (closure)

- `c73099e` Update Horus continuity (closure)
