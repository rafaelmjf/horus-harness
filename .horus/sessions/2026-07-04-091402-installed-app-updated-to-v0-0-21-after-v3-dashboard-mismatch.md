---
date: 2026-07-04T09:14:02
agent: claude
account: personal
environment: host
project: horus-harness
status: closed
summary: "installed app updated to v0.0.21 after v3 dashboard mismatch"
---

# installed app updated to v0.0.21 after v3 dashboard mismatch

## Summary

Rafa restarted the Horus app after v0.0.21 but still saw empty NEXT sections,
`cli outdated`, and v2-style missing-lane health failures for PRD projects. Root cause:
the globally installed `horus` on PATH was still `0.0.18` while the repo/release was
`0.0.21`, so the app process was running pre-v3 dashboard/health logic.

## What changed

- Verified mismatch: `horus --version` returned `0.0.18`; `uv run horus --version`
  returned `0.0.21`.
- Reinstalled the global tool with the floor-pinned command:
  `uv tool install --force --python 3.12 horus-harness`.
- Ran `horus upgrade-project --all --apply`; the three real repos were already in sync
  after the reinstall, and a stale scratch `proto` registration under `/tmp/claude-1000`
  was refreshed before removal.
- Removed the scratch registration with `horus forget .../scratchpad/proto`.
- Verified a fresh installed dashboard on port 8773 reports 3 projects, all healthy,
  all with populated NEXT, PRD-backed health, and projections in sync.

## Durable lesson

After release, debug the running app version first. A stale installed CLI can mimic a
continuity migration bug because the old dashboard still expects six lanes.

## Summary

What this session set out to do and what happened.

## Key Points

- ...

## Next

- ...
