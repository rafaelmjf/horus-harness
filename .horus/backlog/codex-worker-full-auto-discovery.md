---
status: open
priority: now
tier: sonnet
created: 2026-07-10
---
# Make Codex worker network limits discoverable

The safe `--worker codex` preset maps to `auto-edit` / `workspace-write`, whose
sandbox has no network and cannot perform git-integrated dispatch or browser/server
verification. Preserve that safe default, but state in `horus run --help` and the
Codex adapter docstring that those workflows require `--posture full-auto`. Add a
help-surface regression test so the warning cannot silently disappear.
