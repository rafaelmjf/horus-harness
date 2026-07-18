---
status: open
priority: medium
created: 2026-07-18
vision_facet: "Dashboard / cockpit"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/terminal_tui.py (new pane + keybinding), calls existing schedule/notify/warmup/statusline CLI primitives (no new state path)
---

# tui-control-settings-pane — a machine Control pane in the TUI

**Why (owner, 2026-07-18):** stateful, machine-level controls have no home in the
TUI today (`s` = sessions, `d` = defaults are per-project/launch). The trigger is
the always-on steering listener (`horus notify listen --service`): the owner wants
to activate/deactivate it from the TUI, and to bundle other useful machine
settings/actions in one pane reached by a shortcut (like `s`/`d`).

## How (stays within the TUI-thin rule)

The pane RENDERS + TRIGGERS existing CLI primitives — never a second state path
(existing Rule). Everything it needs already exists:

- **Machine services** — steering listener: status badge from
  `schedule.listen_service_active`/`listen_service_installed`; on = `install_listen_service`,
  off = `remove_listen_service`, restart = `restart_listen_service`. Scheduler +
  linger status read-only (`schedule.availability` / `linger_enabled`) with the
  `loginctl enable-linger` hint when off.
- **Quick actions** — `warmup`, `notify test` (`notify.escalate` sample),
  `statusline --install`.
- **Settings** — decide (in-card): a NEW `Control` pane (`c`/gear key) vs.
  extending the existing `Defaults` (`d`) pane; and which extras earn a slot.

## Acceptance

- A keybinding opens the pane; it shows the listener's live status and toggles it
  on/off/restart via the existing primitives (no reimplemented systemd logic).
- Read-only machine facts (scheduler/linger/notify-sink) render with actionable
  hints, never silent.
- No second parser/state path; a live isolated probe drives the toggle end-to-end.

## Non-goals

- Not a settings *framework* — one good pane over the primitives that exist; add
  toggles only as real controls appear (the "we don't need a fancy widget" bar).
- No new machine mutation the CLI can't already do (the pane is a front-end).

## Open questions (owner)

- New `Control` pane vs. extend `Defaults`?
- Which extras beyond the listener earn a slot (warmup / notify-test / statusline)?
