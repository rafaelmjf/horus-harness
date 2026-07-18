---
status: shipped
priority: medium
created: 2026-07-18
vision_facet: "Dashboard / cockpit"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/terminal_tui.py — split the `c` Control pane (shipped #325) into two panes; calls existing schedule/notify/warmup + future hermes/proxy toggle primitives (no new state path)
shipped_pr: 328
shipped_sha: 9cd5020
---

# tui-mission-control-and-settings-split — split Control into Mission Control + Settings

**Why (owner, 2026-07-18):** the Control pane shipped in #325 conflates two different
concerns — *feature switches I flip* (keep-warm/Tokenmaxxing, steering listener) and
*observability of the autonomous loop* (armed dispatches, recent runs). This card
**consolidates the owner's earlier open question** ("what belongs in the Control pane?"):
the answer is that two things did, and they should split. The seam became clear once more
on/off features arrived (hermes sink, the X4 CLIProxyAPI toggle) — they all want one
consistent home, distinct from scheduling/visibility.

## The split

**Mission Control** — *what will run / what ran* (read-mostly observability):
- Armed dispatches + Recent runs with outcome glyphs (`activity.collect` /
  `horus schedule status`, from [[autonomous-activity-timeline]]).
- Execution-readiness facts: scheduler availability, **linger** (with the enable-linger
  hint), standing **envelopes** (the authority governing what runs) + their revoke hint.
- Jumps/actions stay light (e.g. release an andon-halted dispatch); no feature switches here.

**Settings** — machine **feature toggles** (on/off, off by default):
- **Tokenmaxxing / keep-warm** per account `[x]/[ ]` ([[warmup-keep-window]]).
- **Steering listener** on/off + restart ([[notify-listen]]).
- **Notify sink / hermes** on/off (the escalation channel).
- **Proxy-api (CLIProxyAPI)** on/off with **guided setup** — the X4 optional-integration
  toggle ([[vision-branch-x4-model-harness-plane]] principles 1–2: optional not a
  dependency, guided setup not loose docs).
- Any future feature with the same on/off shape lands here by default.

## How (stays TUI-thin — existing rule)

- Two panes, each rendering cached state + triggering existing CLI primitives; no second
  parser/state path (the rule the #325 pane already follows via `_load_control`).
- Keybindings (owner, 2026-07-18): **`m` = Mission Control**, **`t` = Settings** (machine
  feature toggles). The `c` (Control) binding is removed. `t` chosen because `s` collides with
  sessions (kept — used more) and `c` reads as "control". Distinct from `d` **Defaults**
  (per-project *launch* posture) — Settings is a different axis (which machine features are on).
- A **toggle contract** for Settings items: `label · [x]/[ ]` + a status/detail line; a
  3rd-party toggle (hermes, proxy) whose backing isn't set up shows a **guided-setup** entry
  (install/OAuth/verify) instead of silently failing — the X4 guided-UX principle,
  generalised so every optional integration reuses it.

## Acceptance

- `m` opens Mission Control (armed + recent + readiness facts, read-mostly); the Settings
  pane holds every on/off feature toggle; nothing from the #325 Control pane is lost.
- A live isolated probe drives one toggle end-to-end and confirms Mission Control reflects
  real armed/recent state.
- No reimplemented systemd/notify logic; both panes call the existing primitives.

## Non-goals

- Not a settings *framework* — one toggle contract over the primitives that exist; add
  switches only as real features appear.
- No new machine mutation the CLI can't already do; the panes are front-ends.
- Guided-setup flows for hermes/proxy are their own follow-on cards (this card defines the
  slot + contract, not each integration's wizard).
