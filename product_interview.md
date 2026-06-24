# Horus Product Interview

Date: 2026-06-24

Purpose: capture the reasoning that refined Horus before implementation. This is the product-shaping layer, not the technical build spec.

## Core Shift

The project started as a Telegram-driven, multi-agent coding control room. Through scrutiny, the core became sharper:

> Horus is a project-centric continuity and control panel for official coding-agent CLIs, across accounts and environments.

Telegram and other chat surfaces are useful, but they are not the core. The core is keeping project state, roadmap, recent work, agent sessions, accounts, and environments understandable across days and across tools.

## Main User Need

The current real need is:

- manage three different agent accounts;
- work in one or multiple projects at the same time;
- use official Claude Code and Codex sessions rather than reimplemented API loops;
- see project progress and recent agent work in one place;
- continue work from native Claude/Codex UIs even when Horus is not running;
- keep the system lightweight and shaped around current personal needs, not hypothetical future users.

The user explicitly chose current-needs-first design over future-user generality.

## Important Product Principles

### Build For Current Needs

Avoid abstractions that mainly help future users.

Rejected for now:

- abstract identity profiles;
- multi-user team support;
- broad platform behavior;
- general distributed infrastructure;
- full rules/skills marketplace behavior.

Keep the model concrete:

```text
project + agent + account + environment + session
```

### Project First

The dashboard should organize around projects, not accounts, identities, machines, or chat topics.

A project view should answer:

- What is this project?
- What happened in recent sessions?
- What changed regardless of whether Claude or Codex did it?
- What is currently pending?
- What is the roadmap?
- Which accounts/environments/sessions are active?
- Is the project context healthy?

### Horus Should Not Trap The Project

Horus should leave repo-local context that native tools can use directly.

If the user opens the project in Claude Code or Codex without Horus running, the agent should still be able to understand:

- project purpose;
- roadmap;
- decisions;
- latest useful session summaries;
- continuity rules.

This led to the repo-local `.horus/` structure.

### Lightweight, But Opinionated

Horus should stay small, but it can enforce a useful workflow.

Key opinion:

> A project-moving session is not truly complete until project continuity is updated.

That continuity update should be as automatic as possible, not a manual paperwork burden.

## Cynic Tests And Answers

### Why not just open two terminals?

Running two terminals solves execution, not coordination.

Horus is justified if it provides:

- project-level recap;
- visible agent/account/environment per session;
- durable session registry;
- roadmap and current focus;
- project continuity across agents and days;
- closure rituals that prevent lost context.

If Horus only launches terminals, it is not worth building.

### Why Telegram instead of native tools?

Telegram is useful for remote steering and notifications, but not as the primary product.

The native tools remain valuable. Horus should make them more useful by maintaining project continuity, not replace them.

Decision: Telegram is a plus feature, not core.

### Why not Claude Remote Control?

Claude Remote Control is useful but Claude-only and tied to one account/session surface.

Horus is for:

- multiple accounts;
- multiple agents;
- project-level continuity independent of vendor;
- native project files that survive outside Horus.

### Why not Hermes, OpenClaw, Vibe Kanban, kube-coder?

They overlap, but they are larger platforms or different products.

Horus should remain:

- local;
- project-first;
- small;
- official-CLI based;
- continuity-focused;
- account/environment aware.

## Identity Profiles

Identity profiles were scrutinized and rejected for now.

They would be useful if a single profile bundled:

- Claude account;
- Codex account;
- GitHub account;
- Linear/Slack/MCP credentials;
- policy defaults;
- project restrictions.

But the current need does not require that. The dashboard should show usage and sessions per project regardless of abstract identity grouping.

Decision:

```text
No identity profiles in MVP.
Use concrete agent accounts directly.
```

## Multi-Machine And VM Model

The user mainly works on one machine. A VM exists inside the main machine to run another Claude app with different credentials and to provide an isolated dev environment.

Longer-term possibility:

- move agent execution into the VM by default;
- keep Horus as the project dashboard/control panel;
- possibly have Horus installed on multiple machines later.

Decision:

```text
v0.1 can be single-machine.
Keep an environment label in the model.
Do not build true distributed workers yet.
```

## Repo-Local `.horus/`

The user chose repo-local continuity over global Horus-only state.

Reason:

- project-first approach;
- native Claude/Codex sessions should work without Horus running;
- project context travels with the repo;
- agents can update context directly.

Chosen initial structure:

```text
.horus/
  project.md
  roadmap.md
  decisions.md
  sessions/
```

The structure may evolve after field testing. For now, do not split into `features/` or `deliverables/` until the files become too large.

## Git Policy For `.horus/`

Chosen default:

```text
Commit:
  .horus/project.md
  .horus/roadmap.md
  .horus/decisions.md

Ignore:
  .horus/sessions/
```

Reason:

- durable project state belongs in the repo;
- session summaries are supporting evidence and may contain private/account/process details;
- the dashboard can use sessions when present, but the repo should not depend on them.

Future idea:

```text
horus sync sessions
```

This could sync sessions privately without exposing them via git, but it is not important for MVP.

## Session Summaries

Rule:

> Create a session summary when the session contributes to project state.

This includes:

- planning/refinement;
- code changes;
- debugging findings;
- failed attempts that taught something;
- roadmap changes;
- durable decisions;
- environment discoveries.

No summary needed for:

- quick status checks;
- duplicate retries with no new information;
- failed sessions with no new learning.

Session summaries should use light frontmatter plus readable prose.

Example:

```md
---
date: 2026-06-24
agent: codex
account: personal
environment: host
project: horus-harness
status: done
summary: "Refined Horus into a project-centric continuity/control panel."
---

# Product Direction Refinement

## Summary

...
```

## Roadmap Format

Chosen format:

- light frontmatter for dashboard parsing;
- plain Markdown checklist for humans.

Example:

```md
---
status: active
current_focus: "Project continuity MVP"
---

# Roadmap

## MVP

- [ ] Initialize `.horus/`
- [ ] Build dashboard
```

## `AGENTS.md` And `CLAUDE.md`

The user does not want to choose a single canonical file.

Desired behavior:

- `AGENTS.md` and `CLAUDE.md` both remain native/canonical for their agents;
- if a shared instruction evolves in one, it should be reflected in the other;
- the user does not want to manually solve diffs between them.

Chosen starting model:

```text
Horus may automatically sync only marked shared sections.
Agent-specific sections remain untouched.
Drift outside shared sections is detected, not silently merged.
```

Managed block:

```md
<!-- HORUS:BEGIN shared-instructions -->
...
<!-- HORUS:END shared-instructions -->
```

Future command:

```text
horus reconcile instructions
```

This should:

- compare `AGENTS.md` and `CLAUDE.md`;
- sync safe managed-block changes;
- detect agent-specific drift;
- propose promotion/reconciliation when needed;
- optionally use AI later, but default to deterministic behavior.

## Closure Ritual

The user wants a standard closure ritual, enforced by default but configurable.

Reason:

- sessions go stale;
- attention often shifts to something else;
- returning the next day should not require resuming a bloated old session;
- project continuity should already be updated.

Chosen model:

- agents are instructed to maintain `.horus/`;
- Horus verifies continuity at session close;
- if missing, Horus triggers or requests closure;
- closure should happen in the background when possible.

Status implications:

```text
running -> closing -> closed
running -> needs_closure
idle -> stale -> closing -> closed_stale
```

Closure mode should be restricted to:

- `.horus/**`;
- `AGENTS.md`;
- `CLAUDE.md`.

It should not continue editing source code after the user has walked away.

## Stale Closure

Idea:

> If a project-moving session sits idle past a threshold, Horus automatically runs closure, updates `.horus/`, and informs the user.

This lets the user resume the old session if needed, or start fresh because continuity has already been preserved.

MVP can implement this later, but it is a core concept.

## Budget-Aware / Context Rollover Closure

Idea:

> If a session appears near its useful context or quota limit, Horus should recommend running closure and starting fresh.

Signals may include:

- known token/context usage if exposed;
- provider quota/refresh window if detectable;
- turn count;
- session duration;
- transcript/output size;
- rate-limit warnings;
- configurable thresholds.

MVP can start with heuristics rather than exact token accounting.

Suggested user-facing concept:

```text
context rollover
```

This is highly valuable because it helps preserve continuity before quota/context pain appears.

## Current Product Definition

Horus is best described as:

> A project-centric continuity and control panel for official coding-agent CLIs, helping the user run agents under different accounts/environments while keeping project state, roadmap, decisions, and session recaps coherent.

## Next Product Questions

- What should the first dashboard view look like?
- Should `horus init` create `AGENTS.md` and `CLAUDE.md` automatically, or ask first?
- What is the minimal closure verification for MVP?
- How much of the dashboard can be useful before agent execution is wired?
- Which session signals are easiest to use for context rollover?

