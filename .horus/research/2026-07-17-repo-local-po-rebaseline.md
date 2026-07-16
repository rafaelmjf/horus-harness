# Market scan: repo-local product-owner re-baseline — 2026-07-17

Trigger: re-baseline (kickstart dogfood, light comparative sweep — owner-approved envelope)

## Problem / JTBD (hypothesis)

"When I run coding-agent CLIs (Claude Code, Codex) across many repos, I want a
repo-local memory + planning layer that any agent session can pick up — so I can
resume the exact next step, see my whole fleet, and steer each project's direction
without babysitting context." Frame as a hypothesis to validate, not a finding.

Current alternatives people use: native CLAUDE.md/MEMORY.md; Cline/Roo memory-bank
markdown; claude-task-master PRD→tasks; GitHub Spec-Kit spec→plan→tasks; hand-kept
notes / issue trackers.

## Competitive teardown

| Competitor | Does well | Gap (vs Horus) | Positioning | Price |
|---|---|---|---|---|
| **Claude Code native memory** (CLAUDE.md + auto MEMORY.md + subagent memory v2.1.33 Feb'26 + Plan mode) | Zero-config, loads every session, subagents now carry own MEMORY.md | **Claude-only**; single-repo; no cross-project fleet/dashboard; no vision/backlog/convergence lifecycle; subagents don't share learnings; Plan/Explore skip CLAUDE.md | Built into the agent | Included |
| **GitHub Spec-Kit** (spec→plan→tasks→implement, 30+ agents) | Structured per-feature pipeline, quality gates, broad agent support | **Per-feature pipeline, NOT living continuity** — verified: no persistent project memory, backlog state, or session resume | Spec-driven methodology + `specify` CLI | OSS free |
| **claude-task-master / Taskmaster AI** (15.5k★) | PRD→task decomposition, dependency graph, MCP drop-in, uses your subscription tokens | Decomposes ONE PRD into tasks; no living vision/convergence, no fleet/dashboard, per-project | Task-manager MCP for Cursor/Windsurf/Roo/CC | OSS |
| **Cline / Roo "Memory Bank"** (6 markdown files incl. activeContext.md/progress.md) | Repo-local markdown persistent context that survives sessions | Verified: mostly **project-DESCRIPTION docs**, not roadmap/backlog priorities; **agent-specific** (Cline custom instructions), not neutral; no cross-project/convergence | Custom-instruction methodology | OSS |
| *(one-liner)* **agentmemory / mem0-style MCP memory** | Benchmarked cross-tool persistent memory | Memory *infra*, not a product-owner/planning plane | Memory MCP server | OSS/SaaS |

## Prior-art verdict: **YELLOW**

The **memory primitive is saturated** — every agent now ships repo-local markdown
continuity (native MEMORY.md, .clinerules, memory-bank/, task-master). "We have
markdown memory" is table stakes, not a wedge. BUT the specific triad Horus stakes
is **not covered by any single competitor**:
1. **Agent-NEUTRAL** repo-local continuity that resumes the *exact next step*
   fetch-first (native memories are agent-locked: CLAUDE.md=Claude, .clinerules=Cline);
2. **Cross-project FLEET** dashboard/cockpit (nobody above has one);
3. **PO-lifecycle** — vision→facets→convergence "breathing roadmap" as a repo-local
   ritual (spec-kit/task-master do per-feature/one-PRD; none do living convergence).

## Vision draft (PR-FAQ, 1 para)

*Headline:* "Horus is the agent-neutral product-owner plane that sits **above** the
coding agents — not another memory file. Where each CLI has its own locked-in memory
(CLAUDE.md, .clinerules) and spec pipelines (Spec-Kit, Task-Master) run one feature at
a time, Horus keeps one repo-local `.horus/` any agent can resume from, gives you a
cross-project fleet cockpit, and runs the divergence→convergence roadmap ritual that
keeps a real product from sprawling." The differentiation leans on **fleet +
convergence-lifecycle + neutrality**, and explicitly NOT on "repo-local markdown
memory" as if novel.

## Open questions / hard FAQ

1. **Why now:** native subagent memory (Feb'26) is accelerating — is Horus continuity
   about to be subsumed by native MEMORY.md, or does agent-neutrality + fleet stay a moat?
2. **Why us:** the moat is fleet + convergence, not memory. Is that enough to matter to
   anyone but a power user running many repos across Claude+Codex? (n=1 owner today.)
3. **Biggest risk:** building "better memory" where the world already has table stakes,
   instead of doubling down on the two things nobody else has.
4. **Interop vs compete:** should Horus *read/adopt* CLAUDE.md + memory-bank + .clinerules
   into `.horus/` (be the neutral layer above them) rather than be a parallel store?
5. **Compose spec pipelines:** sit above Spec-Kit/Task-Master per-feature runs as the
   continuity+fleet layer? (PRD already says "NOT spec-kit depth" — this validates it.)

## Market-size sanity

Crowded and well-named ("memory bank", "task master", "spec kit") for the *memory/task*
slice; the *agent-neutral fleet product-owner* slice is near-empty but also near-n_market
(power users running many repos across multiple agent CLIs) — differentiation, not TAM,
is the question.

## Candidate backlog items

- **Rescope "Continuity core" DoD to lead with agent-NEUTRALITY + cross-agent resume**
  — the one thing native memory structurally can't do — rather than "durable state"
  generically. (facet rescope, from the saturation finding.)
- **[explore] Native-memory interop** — read/adopt CLAUDE.md, MEMORY.md, memory-bank/,
  .clinerules INTO `.horus/` so Horus is the neutral layer above agent-locked memories,
  not a competing store. (from FAQ Q4.)
- **[explore] Sit-above-spec-pipelines** — compose Spec-Kit/Task-Master per-feature runs
  under Horus continuity+fleet instead of reimplementing spec depth. (from FAQ Q5.)
- **Product naming should encode the wedge** ("fleet product owner"), not "memory" —
  feeds the existing `product-naming` card. (from the naming-saturation finding.)

## Sources

- https://code.claude.com/docs/en/sub-agents
- https://vectorize.io/articles/claude-code-memory
- https://github.github.com/spec-kit/
- https://github.com/github/spec-kit
- https://github.com/eyaltoledano/claude-task-master
- https://cline.bot/blog/memory-bank-how-to-make-cline-an-ai-agent-that-never-forgets
- https://docs.cline.bot/prompting/cline-memory-bank
- https://github.com/rohitg00/agentmemory
