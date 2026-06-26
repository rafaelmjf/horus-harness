---
project: horus-harness
status: active
current_focus: "MVP5 (app cohesion / lifecycle) — making the loosely-wired pieces feel like one app. This session: (1) SHIPPED — the self-restart footgun is guarded (a hosted in-app agent can no longer restart/kill the dashboard hosting its own PTY; `horus guard-host` PreToolUse hook + `pty_host` env markers). (2) FRONTEND — tried a pywebview shell to own the window lifecycle but it was unstable + slow on Win11, so REVERTED to the proven Edge `--app` + Tk mascot (refreshed art). Settled on a two-tier frontend: lightweight Edge+mascot ships now via uv (with known lifecycle drawbacks accepted); a separate downloadable proper native app (PySide/Electron/Tauri — TBD) is where real window-lifecycle ownership + taskbar icon land, sharing the same Python server + web UI. Still open: the structural session-host daemon. Continuity (the moat) stays the headline; the continuity-debt backlog (~85 done roadmap items, ~48 missing features rows, ~40 sessions to distill) remains the standing opt-in cleanup job."
last_updated: 2026-06-26
---

# Horus Harness

Horus is a lightweight, project-centric continuity and control panel for official coding-agent CLIs.

It helps run and observe Claude Code, Codex, and future agents across concrete accounts and environments while keeping project state coherent in the repository.

## Core Thesis

The main value is not Telegram control by itself. The main value is project continuity:

- a project dashboard showing current projects, recaps, roadmap, and pending work;
- official CLI sessions under different accounts;
- visibility into which agent/account/environment worked on a project;
- repo-local `.horus/` files that native Claude/Codex sessions can use without Horus running;
- closure rituals that prevent useful work from disappearing into stale conversations.

Near-term feature design is native-app-first: whenever Horus adds a capability,
define how it works inside Claude Code and Codex using their own surfaces
(instructions, skills, hooks, local config) before building a Horus-owned session
or orchestration layer. Horus-owned sessions remain the later path for unattended
or cross-session control that native apps cannot cover cleanly.

## Current Shape

Horus should model:

```text
project + agent + account + environment + session
```

It should not model abstract identity profiles yet.

## Companion App Direction

The next product slice is a small always-on-top Horus companion/mascot. Its first
job is not orchestration; it is presence. The mascot should make Horus visibly
"active" while staying lightweight: click to open the dashboard, show simple
status, and eventually surface closure/usage nudges from the native-app bridge.

This should feel like a native companion to Claude Code/Codex, not a replacement
for them. The native apps remain where agent work happens. Horus provides the
project continuity layer, dashboard, and a gentle visual affordance for state
that would otherwise be hidden in terminal output or hook logs.

## Near-Term Scope

First useful version:

- initialize repo-local `.horus/` project continuity files;
- render a project dashboard from those files;
- maintain session summaries and roadmap state;
- inspect instruction compatibility between `AGENTS.md` and `CLAUDE.md`;
- project bundled routines into native Claude Code/Codex skill locations;
- install small native hooks for app-level signals such as usage rollover;
- ship a minimal always-on-top companion/mascot that opens the dashboard;
- later wire real Codex/Claude sessions into the same project view.

## Out Of Scope For Now

- multi-user SaaS;
- generalized agent marketplace;
- full distributed worker control plane;
- identity profile abstraction;
- broad automatic rule conversion;
- long-term memory system beyond repo-local project continuity.
