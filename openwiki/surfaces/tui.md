---
type: terminal user interface
title: Terminal App and TUI Cockpit
description: The terminal fallback and prompt-toolkit cockpit, context-disciplined launches, responsive backlog views, and explicit refresh behavior.
tags: [tui, terminal, cockpit]
---

# Terminal App and TUI Cockpit

`horus app --terminal` and the `horus tui` alias expose the terminal-native peer of the dashboard. Both reuse the same project focus, registry, card, catalog, and `terminal_sessions` primitives rather than maintaining a second session model.

## Two terminal surfaces

- `terminal_app.run()` selects the full prompt-toolkit experience for interactive TTY conditions and offers a line-oriented fallback otherwise. The fallback can list projects/next actions, select fresh/resume Claude/Codex launches, select accounts, show sessions, and attach/close where host support permits.
- `terminal_tui.HorusTUI` is the daily cockpit: fleet grid, accounts/usage rail, launch forms, live/restorable sessions, project freshness/sync, remote catalog, cards/list/board, card review/edit, vision/receipts/capabilities/skills, and settings/mission controls.

The TUI constructor loads state before rendering; rendering is intentionally not a hidden network-fetch path. Explicit commands refresh fleet freshness or usage/cache state.

## Launch context discipline

`_launch_prompt` and related helpers build the minimum requested context at spawn time:

| Selection | Prompt contract |
|---|---|
| Fresh | Empty prompt; no accidental continuity injection. |
| Resume | Authored `routines.resume_prompt(root)` handoff. |
| Card | Card scope plus relevant resume context; card becomes the first task. |
| Refine | A generated refinement prompt at launch time. |

The launch form combines model, effort, permission posture, account, and context selection. Persisted defaults are agent-specific; a one-off override does not rewrite them. Actual session creation delegates to `terminal_sessions.launch_on(default_target(), ...)`, preserving host selection/readiness behavior shared with CLI and dashboard.

## Interaction and responsive behavior

Key bindings are screen-scoped; backlog actions do not leak to unrelated views. Backlog list and board views apply the shared readiness queues/filters, and the board degrades to the list on narrow terminals. `config.load_backlog_fields()` and `toggle_backlog_field()` persist the owner’s displayed frontmatter-field choices; `backlog.set_priority()` is a direct, narrow frontmatter mutation whose result is immediately reread/rendered. Card editor actions similarly make bounded field/body edits, whereas `start_refine_pass()` launches an **attended** refinement prompt: it proposes planning/readiness changes rather than silently auto-routing cards. Scrolling accommodates terminal/mobile input conventions. The TUI labels live, attachable, original-terminal-only, and restorable session state honestly rather than treating a stale registry row as active.

Remote catalog rendering is cache-only during paint. Starting a remote catalog project uses `remote_start.start_github_project`, the same local clone/register/upgrade primitive used elsewhere.

```sh
pytest -q tests/test_terminal_tui.py tests/test_terminal_sessions.py
# fallback surface only
pytest -q tests/test_terminal_sessions.py -k terminal_app
```

See [accounts and launch](../sessions/accounts-and-launch.md) for identity selection and [hosts and registry](../sessions/hosts-and-registry.md) for persistence and recovery semantics.
