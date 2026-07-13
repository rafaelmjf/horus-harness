---
date: 2026-07-13T13:29:47
agent: codex
account: personal
environment: host
project: horus-harness
status: closed
summary: "terminal cockpit KPIs backlog and multi-session flow"
---

# terminal cockpit KPIs backlog and multi-session flow

## Summary

Accepted the owner's v0.0.47 Termius PASS, then expanded the terminal UI into the
requested project cockpit. Shipped v0.0.48 with account usage, project KPIs,
unified cross-agent launch choices, backlog/card drill-down, card-first resume,
multi-session guidance, and mobile-natural touch direction.

## Key Points

- Replaced the misleading `ambient` label with the configured alias while retaining
  `None` as the actual launch value: the picker now shows Claude personal, Claude
  work, and Codex personal, and will include future mapped accounts automatically.
- The home screen reads existing usage snapshots without network calls and displays
  5h/weekly percentages plus reset times. Project rows show open tmux sessions with
  agent/account identity and active backlog/bug counts instead of clipped prose.
- Project navigation is Resume / Fresh / Backlog. Both launch modes share one combined
  Claude/Codex account picker. Backlog cards are sorted now→deferred, labelled by card
  type, open into a wrapped full-description page, and can seed a resumed session with
  that card explicitly first.
- Multi-session behavior stays on the proven tmux substrate: `Ctrl-b d` detaches
  without closing the agent and returns to Horus; another session can launch, and `s`
  lists/attaches either one. The UI footer and README now expose this flow.
- Desktop mouse-wheel behavior stays conventional. Mouse/touch events invert only in
  narrow (<64-column) SSH terminals so Termius swipe-up moves options upward; physical
  arrow keys are never inverted. `HORUS_TUI_INVERT_MOUSE_SCROLL` is the escape hatch.
- Verification: 1,270 tests passed after the version bump; focused account/backlog/
  usage/terminal gates passed; live 39x20 PTY covered the account/reset rail, project
  KPIs, combined picker, priority list, wrapped card detail, and clean screen restore.
- PR #201 merged at `afe6356`; release PR #202 merged at `a42355d`; PyPI publish and
  install smoke passed on Windows/macOS/Linux. Mandatory hosted deployment reports
  0.0.48 at `/health` and keeps `/` gated with 403. No real agent/model tokens were
  consumed by implementation probes.

## Next

- Owner tests touch direction, KPI/account accuracy, backlog/card-first resume, and
  two concurrent tmux sessions in Termius. On PASS, return to orphan-process reaping.

## Checkpoints (auto-harvested)

- `afe6356` Expand terminal project cockpit (#201)
- `a42355d` Release 0.0.48 (#202)
- `bc82b00` Update continuity for terminal cockpit v0.0.48 (#203)
