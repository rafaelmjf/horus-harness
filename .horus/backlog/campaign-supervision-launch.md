---
status: claimed
priority: medium
tier: sonnet
created: 2026-07-15
type: feature
parallel: safe
surface: horus/terminal_tui.py, horus/routines.py
---

# Optional campaign-supervision launch from the TUI

The `horus-agent` workspace now distinguishes portfolio hygiene from an owner-selected
cross-project campaign. Fleet Review should not be stretched into implementation
planning, and selecting the repository's ordinary Resume action does not name the
campaign contract explicitly.

## Acceptance

- The TUI offers Campaign separately from Fleet Review when a compatible registered
  cockpit workspace exists.
- The launch prompt asks for the outcome and target set, preserves direct-project launch
  as the default, and applies need-first inline-versus-dispatch judgment per bounded unit.
- It does not auto-select a model/account, auto-spawn, or treat cross-project scope as a
  dispatch dividend.
- Target repositories retain their own branch/PR/gate/continuity authority.
- A prompt/frame test proves the launch is optional and distinct from Fleet Review.

## Execution

Implement after the repository-level campaign contract is exercised through the normal
Resume action. That validates the semantics before adding a dedicated UI affordance.
