# Omnigent

- **What it is:** An open-source **meta-harness** for AI agents, **open-sourced by
  Databricks** (positioned as "the Kubernetes for agents"). A uniform layer *above*
  command-line agents (Claude Code, Codex, Cursor, OpenCode, Hermes, Kiro, Pi) with
  three pillars — **Compose** (swap harnesses with a one-line YAML change), **Control**
  (stateful spend caps, model routing, approvals, OS sandbox via `bwrap`/`seatbelt`/Job
  Objects, credential brokering), **Collaborate** (real-time shared sessions over
  web:6767 / macOS app / mobile / REST). Runners run local or on Modal/Daytona/E2B/
  K8s/Databricks. A server daemon backs multi-device sync.
- **Where it overlaps Horus:** the execution/orchestration layer — Horus's MVP3/4
  (Claude/Codex adapters, session registry, in-app PTY cockpit, `run`/`open`, live
  oversight) and the planned native-app session cockpit.
- **Verdict:** **Cede orchestration; interop at the continuity boundary; not adopting
  now.** Omnigent is the *control/execution plane*; Horus should be the *durable memory
  plane*. Don't build a second control plane. Treat Omnigent as an **optional, per-task
  execution backend** later (its `Polly` orchestrator already does Horus's `execution.md`
  delegation model — plan → delegate to Claude/Codex/Pi sub-agents in parallel git
  worktrees → cross-vendor review → merge), wired via a Horus continuity MCP tool.

## Drift triggers — if you're about to build any of these, STOP

- A **multi-harness orchestrator** / harness-abstraction layer (swap Claude/Codex/Cursor).
- A **live session cockpit**: hosting/attaching/forking running agent sessions, multi-
  device session sync, real-time multi-user co-driving or commenting.
- **Sandboxing / credential brokering** as a security boundary for agent execution.
- **Cloud runners** / provisioning sandboxes per session (Modal/E2B/K8s/Databricks).
- A **policy engine** for spend caps / model routing / approval workflows at the
  execution layer.
- A **heavy native desktop app that is a session cockpit** (Omnigent already ships
  web + macOS + mobile).

→ In all of these, prefer **interop** (feed Omnigent `.horus/` continuity via MCP) or
**adopt** Omnigent as the execution backend. The one thing that stays squarely Horus's
is everything below.

## What stays Horus's (no overlap — the wedge)

Omnigent has **no project-continuity / persistent-memory concept** — confirmed in its
README and the Databricks blog: sessions are server/DB-backed and *ephemeral by design*
("agents as stateless services coordinated through a central server, not as persistent
entities with git-integrated memory"). That is exactly Horus's core and Omnigent
explicitly doesn't go there:

- Durable repo-local `.horus/` continuity, **committed to git, readable by native agents
  even when nothing is running** (no server).
- Closure rituals, the dashboard contract, freshness gates, and the
  delegation rubric / working disciplines.
- Cross-machine **work-pickup**: rehydrate from `.horus/` lanes + `next_prompt` on any
  machine/account — no live session to reattach, no server to host.

## Codex research (verbatim, 2026-06-29)

> Evaluated Omnigent/OmniAgent as a potentially overlapping open-source tool around
> flexible multi-agent execution, subscription/API auth, collaboration, policies, and
> sandboxes.
>
> Recommendation: Horus should not integrate Omnigent as a core dependency and should not
> try to match its full server/runner/auth surface. Keep Horus focused on repo-local
> continuity, closure gates, native Claude/Codex hooks/skills, project inventory,
> next-action visibility, and cross-machine pickup. Treat Omnigent as a future interop
> target at the continuity boundary.
>
> - Omnigent is substantially ahead on hosted multi-agent execution: FastAPI server,
>   DB-backed sessions, WebSocket runner/host model, browser/mobile/desktop UI,
>   sharing/co-driving/forking, policies, sandbox providers, and many harness bridges.
> - Its auth/model story is broader than Horus's current account handling: API keys,
>   Claude/ChatGPT subscriptions through official CLIs, gateways, Databricks, OIDC/server
>   auth, and per-agent defaults.
> - That breadth is exactly why it should not become Horus's foundation right now;
>   adopting it would make Horus dependent on a large external orchestration platform and
>   blur the product into "another meta-harness."
> - Horus's stronger niche is durable project state in the repo: `.horus` lanes, closure
>   rituals, native hooks/skills, project dashboard, remote project catalog, and resume
>   prompts that survive across machines and native apps.
> - The promising later seam is small: export `.horus` state as Omnigent-readable
>   context/tools/agent bundle, optionally import/display Omnigent session ids or
>   statuses, and leave live execution/auth/sandboxing to Omnigent when the user
>   explicitly chooses that host.

## Claude research — additions to the Codex pass (2026-06-29)

The Codex pass and this one **converged independently**. Three things this pass added:

1. **Databricks backing.** Omnigent is a Databricks OSS project ("Kubernetes for
   agents"). Competing on orchestration means competing with a likely *standard*, not a
   peer — which strengthens the cede call.
2. **Confirmed (not inferred): no project memory.** Verified directly in the README +
   blog. This is the load-bearing fact under Horus's wedge.
3. **Freeze the cockpit we already shipped.** It's not just "don't match their surface
   going forward" — continuing to expand Horus's own MVP3/4 cockpit (adapters, PTY host,
   live oversight) and the planned native session-app is building a weaker Omnigent.
   Freeze what shipped as a "good enough local view"; redirect to continuity + interop.
   `Polly` already implements the supervisor/worker delegation model we encoded in
   `execution.md`, so Omnigent can be the *execution engine* — which means Horus needs
   its own cockpit even less.

## Fit against the current use case (2026-06-29)

Use case checked: continuity + different accounts across machines with resume-anytime +
`execution.md` outsourcing implementation to different agents.

- **Continuity:** Horus only. Omnigent adds nothing, threatens nothing.
- **Multi-account + resume across machines:** Horus's **work-pickup** (rehydrate from
  `.horus/`, no server) already covers "resume a project anytime, any account, any
  machine." Omnigent's `attach` only adds **live in-flight session reattach**, which
  needs an always-on deployed server — decided **not needed** (work-pickup is enough).
  Omnigent supports subscription auth, so it would not break the subscription-auth-only
  constraint if adopted.
- **execution.md delegation:** the strongest fit. `Polly` is a shipped implementation of
  the model. If/when running real multi-agent/parallel/cloud work, delegate to Omnigent
  rather than building it in Horus.

## Two planes (the division if/when adopted)

- **Horus = decision + memory plane:** durable continuity, the delegation decision
  (rubric), closure. Lightweight, git-native, **server-free**, subscription-auth. Always
  works with Omnigent absent.
- **Omnigent = optional execution plane:** meta-harness/runtime (Polly, sub-agents,
  sandboxes, cloud runners). Adopted **per-task**, never a Horus dependency.

**Non-goals:** no embedded Omnigent server; no Horus dependency on its runner/auth; no
migration of `.horus/` lanes into Omnigent's DB/session state (continuity stays in git);
Horus does not become a meta-harness or a second control plane; no live cross-machine
session reattach in Horus (work-pickup covers it).

## Suggested interop shape (continuity-MCP first) — NOT scheduled

Captured as direction only; not planned for implementation now.

1. **Keystone — `horus mcp` continuity server.** A stdio MCP server exposing read tools
   over `.horus/` (`get_next_prompt`, `get_project`, `get_roadmap`, `get_decisions`/
   `get_features`/`get_history`, maybe a `resume_context` bundle). Launched on demand by
   the client (no daemon → stays lightweight). **Universal:** Claude Code, Cursor, *and*
   Omnigent (`tools: {type: mcp}`) all consume it. This is the concrete form of "Horus is
   the memory plane for agentic coding"; Omnigent is the first consumer, not a special
   case.
2. **`horus export omnigent`** (thin, builds on #1): generate a Polly/agent YAML seeded
   with the Horus continuity MCP tool + `current_focus`/`next_prompt` as starting context
   + the `execution.md` tier mapping → Polly sub-agents.
3. **Dashboard read-back** (optional, later): display Omnigent session ids/status on the
   Horus project page; display-only, no control.

## Sources

- [omnigent.ai](https://omnigent.ai/)
- [Databricks blog — Introducing Omnigent](https://www.databricks.com/blog/introducing-omnigent-meta-harness-combine-control-and-share-your-agents)
- [omnigent-ai/omnigent (GitHub)](https://github.com/omnigent-ai/omnigent)
