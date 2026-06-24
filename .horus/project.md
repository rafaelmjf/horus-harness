---
project: horus-harness
status: planning
current_focus: "Define the project-first continuity MVP before implementation."
last_updated: 2026-06-24
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

## Current Shape

Horus should model:

```text
project + agent + account + environment + session
```

It should not model abstract identity profiles yet.

## Near-Term Scope

First useful version:

- initialize repo-local `.horus/` project continuity files;
- render a project dashboard from those files;
- maintain session summaries and roadmap state;
- inspect instruction compatibility between `AGENTS.md` and `CLAUDE.md`;
- later wire real Codex/Claude sessions into the same project view.

## Out Of Scope For Now

- multi-user SaaS;
- generalized agent marketplace;
- full distributed worker control plane;
- identity profile abstraction;
- broad automatic rule conversion;
- long-term memory system beyond repo-local project continuity.

