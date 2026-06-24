# Horus - project continuity and control for official coding-agent CLIs

> **Brand / project:** Horus - the watchtower over your agents.
> **Repo / package:** `horus-harness` - a harness around official agent CLIs and repo-local project continuity.
> **Command:** `horus`
> **Status:** planning / pre-MVP.
> **Last refined:** 2026-06-24.

---

## 0. Current Thesis

Horus is a project-centric continuity and control panel for official coding-agent CLIs.

It helps the user work across accounts, agents, and environments while keeping each project understandable over time. The important artifact is not just an active session; it is the project state that survives after sessions go stale.

Core model:

```text
project + agent + account + environment + session
```

Core value:

- show all current projects;
- show what happened recently in each project;
- show roadmap and pending features;
- show which agents/accounts/environments are active;
- preserve continuity in repo-local files;
- run official Claude Code / Codex CLIs without reimplementing agent loops;
- optionally expose controls through Telegram or other chat surfaces later.

Telegram is a useful surface. It is not the core.

---

## 1. Product Principles

### Build For Current Needs

Design for the user's current workflow first.

Do not add abstractions only because they might help future users. In particular, avoid identity profiles, team workspaces, marketplaces, and distributed workers until actual use creates pressure.

### Project First

The dashboard should start with projects, not accounts, machines, or chat threads.

Project view should answer:

- What is this project?
- What happened last?
- What is the current focus?
- What is pending on the roadmap?
- Which sessions/accounts/environments are involved?
- Is continuity healthy?

### Native Tools Should Still Work

Horus must not trap work inside Horus.

If the user opens this repo directly in Claude Code or Codex, the agent should still find the project context and know how to maintain continuity.

### Lightweight But Opinionated

Horus should stay small, but it can enforce one strong workflow:

> A project-moving session is not complete until project continuity is updated.

---

## 2. Repo-Local Continuity

Each project can opt into Horus by adding:

```text
.horus/
  project.md
  roadmap.md
  decisions.md
  sessions/
```

### Files

`project.md`

- project purpose;
- current focus;
- product shape;
- important boundaries.

`roadmap.md`

- light frontmatter for dashboard parsing;
- plain Markdown roadmap and checklists;
- current focus.

`decisions.md`

- durable decisions and reasoning;
- dated entries;
- no ephemeral session chatter.

`sessions/`

- local project-progress journal;
- one file per project-moving session;
- light frontmatter plus prose;
- ignored by git by default.

### Git Policy

Commit:

```text
.horus/project.md
.horus/roadmap.md
.horus/decisions.md
```

Ignore:

```text
.horus/sessions/*.md
```

Reason: durable project state should travel with the repo; session summaries are supporting evidence and may contain local/account/process details.

---

## 3. Native Instruction Files

Horus should support both `AGENTS.md` and `CLAUDE.md` as native instruction files.

Do not force a single canonical file.

Use Horus-managed shared sections:

```md
<!-- HORUS:BEGIN shared-instructions -->
...
<!-- HORUS:END shared-instructions -->
```

Rules:

- shared managed blocks may be synced automatically;
- content outside managed blocks is agent-specific by default;
- Horus detects drift outside managed blocks;
- Horus does not silently merge arbitrary free-form changes;
- future command: `horus reconcile instructions`.

MVP behavior:

- create or check the managed blocks;
- warn when `AGENTS.md` and `CLAUDE.md` drift;
- do not attempt AI semantic merges.

Future behavior:

```text
horus reconcile instructions
horus reconcile instructions --ai
```

---

## 4. Dashboard

The dashboard is core. It should start read-only.

First dashboard slice:

- list projects;
- show project status/current focus from `.horus/project.md` and `.horus/roadmap.md`;
- show roadmap summary;
- show recent local session summaries when present;
- show decisions;
- show continuity health warnings;
- show configured agents/accounts/environments once execution exists.

Avoid becoming Vibe Kanban. Horus is not a project management suite; it is a continuity and control panel for agent-driven project work.

Implementation preference:

- local HTTP server;
- bind to `127.0.0.1`;
- optional Tailscale exposure later;
- no prompt input in the first dashboard version.

---

## 5. Session Closure

Sessions that move the project forward should leave a summary.

Create a session summary when a session contributes to project state:

- planning/refinement;
- code changes;
- debugging findings;
- failed attempts that taught something;
- roadmap updates;
- durable decisions;
- environment setup discoveries.

No summary needed for pure status checks or retries that add no new information.

### Session Summary Format

Use light frontmatter plus prose:

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

# Session Title

## Summary

...

## Key Points

- ...

## Next

- ...
```

### Closure Ritual

Closure should be enforced by default but configurable.

Closure checks:

- session summary exists when work contributed to project state;
- roadmap updated if status changed;
- decisions updated if durable decisions were made;
- `AGENTS.md` / `CLAUDE.md` shared blocks remain aligned.

Closure mode may update:

```text
.horus/**
AGENTS.md
CLAUDE.md
```

Closure mode should not continue editing source code after the user has walked away.

---

## 6. Stale Closure And Context Rollover

### Stale Closure

If a project-moving session sits idle past a threshold, Horus should be able to run the closure ritual automatically and notify the user.

Goal:

- preserve continuity even when attention shifts;
- allow the user to return tomorrow and start fresh;
- keep old sessions resumable but not required.

### Context Rollover

Horus should warn when a session is likely near context/quota pain and suggest closure.

Initial signals can be heuristic:

- turn count;
- duration;
- output/transcript size;
- rate-limit text in output;
- configurable thresholds.

Future signals:

- actual token/context usage if CLI exposes it;
- provider quota refresh window;
- per-account usage meters.

User-facing concept:

```text
context rollover
```

Meaning: close and summarize the current session so the next session can start fresh from `.horus/`.

---

## 7. Accounts And Environments

Do not create identity profiles in MVP.

Model concrete accounts directly:

```text
agent = codex | claude
account = personal | work | client | ...
environment = host | vm | ...
```

Current reality:

- mainly one host machine;
- a VM may run another Claude app with different credentials;
- both host and VM can work on the same projects;
- VM isolation may become the default later.

MVP can be single-machine, but the data model should include `environment`.

---

## 8. Agent Execution

Horus wraps official CLIs as subprocesses. It does not call model APIs directly.

Initial execution target:

- Codex first;
- Claude second after permission/account behavior is tested.

Session identity:

```text
(project, agent, account, environment, external_session_id)
```

Horus owns:

- session registry;
- account selection;
- environment label;
- lock/closure state;
- dashboard status;
- continuity verification.

The official CLI owns:

- model auth;
- agent loop;
- tool semantics;
- provider-specific behavior;
- native session behavior.

---

## 9. Optional Chat Control

Telegram is useful later for:

- notifications;
- quick steering;
- remote status checks;
- closure/context rollover prompts;
- lightweight session commands.

Telegram is not the MVP center.

When added, it should use the same project/session registry as the dashboard, not become a separate architecture.

---

## 10. Security And Privacy

Non-negotiables:

- no secrets in `.horus/`;
- session summaries stay concise;
- session summaries are ignored by git by default;
- closure mode cannot keep editing source code;
- account choice is explicit and visible;
- work/personal accounts are never silently mixed;
- third-party skills/plugins require provenance and review;
- chat surfaces, when added, must use allowlists.

---

## 11. Short Roadmap

### Step 1 - Lock The Project Continuity Contract

- [x] Create `.horus/project.md`.
- [x] Create `.horus/roadmap.md`.
- [x] Create `.horus/decisions.md`.
- [x] Create `.horus/sessions/` with local ignore policy.
- [x] Capture the product interview in `product_interview.md`.
- [x] Add initial `AGENTS.md` and `CLAUDE.md` shared Horus-managed blocks.
- [ ] Define exact `horus init` output and prompts.
- [ ] Define session summary template.
- [ ] Define closure prompt template.

### Step 2 - Build A Read-Only Project Dashboard

- [ ] Create Python package skeleton.
- [ ] Discover configured projects.
- [ ] Parse `.horus/project.md` and `.horus/roadmap.md` frontmatter.
- [ ] Render project list.
- [ ] Render project detail page.
- [ ] Show roadmap, decisions, and recent local sessions.
- [ ] Show continuity warnings.

### Step 3 - Add Local Commands

- [ ] `horus init`
- [ ] `horus doctor project`
- [ ] `horus doctor instructions`
- [ ] `horus reconcile instructions` deterministic managed-block sync.

### Step 4 - Add Session Registry And Closure

- [ ] SQLite registry.
- [ ] Session/event state model.
- [ ] Closure states: `closing`, `needs_closure`, `closed_stale`.
- [ ] Verify session summary creation.
- [ ] Add stale closure threshold.
- [ ] Add context rollover heuristics.

### Step 5 - Add Agent Execution

- [ ] Configure accounts and environments.
- [ ] Add Codex adapter.
- [ ] Launch/resume Codex sessions.
- [ ] Associate sessions with projects.
- [ ] Run closure ritual through the same session.
- [ ] Add Claude adapter after Codex proves the loop.

### Step 6 - Optional Surfaces

- [ ] Telegram bridge.
- [ ] Tailscale exposure.
- [ ] VM/worker mode.
- [ ] `rulesync` integration.
- [ ] AI-assisted instruction reconciliation.
- [ ] Private session sync outside git.

---

## 12. Open Questions

- Should `horus init` create `AGENTS.md` and `CLAUDE.md` automatically or ask first?
- What should the first dashboard layout look like?
- What counts as a passing closure verification?
- Should stale closure be enabled by default or only warned at first?
- Which context rollover heuristics are useful before real token/quota data exists?
- Should project discovery be config-only at first, or scan directories for `.horus/`?

---

## 13. References

- `product_interview.md` - reasoning behind the current product choices.
- `codex-plan-review.md` - landscape and alternatives research.
- `.horus/project.md` - current project brief.
- `.horus/roadmap.md` - implementation roadmap.
- `.horus/decisions.md` - durable decisions.

