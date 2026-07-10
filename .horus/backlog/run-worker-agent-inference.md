---
status: claimed
priority: now
tier: sonnet
created: 2026-07-10
---
# Infer the `horus run` adapter from `--worker`

`--worker {claude,codex}` names an agent but currently selects only a posture preset.
Because `--agent` silently defaults to Claude, `--worker codex` launches the wrong
adapter unless callers repeat `--agent codex`. When `--worker X` is supplied without
an explicit `--agent`, infer agent X; keep an explicit `--agent` authoritative. Add a
CLI test that observes the launched adapter.
