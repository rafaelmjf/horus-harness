---
project: horus-harness
status: active
current_focus: "v0.0.9 live on PyPI; riding the next release: projection-sync badge (PR #68), VS Code launch destination tier 1 (PR #70), and the open-continuity-PR nudge (PR #71 — doctor warn + async dashboard fragment; 591 tests green). Remaining UX-hardening items are per-OS/lifecycle direct work (graceful hooks, onboard artifact commits, startup visibility, install-smoke CI). Horus remains the durable memory plane (no session hosting)."
last_updated: 2026-07-02
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
