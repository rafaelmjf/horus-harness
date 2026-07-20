# Market scan: repo-local product-owner layer for coding agents — 2026-07-20

**What this document is.** The outward twin of the 2026-07-20 product audit: a
shallow, cited sweep of what the world already offers in the three spaces Horus
occupies, so the convergence step can judge facets and branches on inward +
outward evidence together. It proposes; it changes nothing.

- **Intent:** broaden-adoption (owner-confirmed) — verdicts read as market-gap:
  is the space taken?
- **Trigger:** re-baseline (pathfinder calibration run, step 2).
- **Depth:** shallow pass — top public results, pages opened only where a
  teardown row depends on them; secondary-source rows are marked. A deeper
  pass is offered at the end, not assumed.

**Problem / JTBD (hypothesis, not a finding):** *When I run multiple AI coding
agents across several projects, accounts, and machines as a solo
owner-operator, I want every fresh session to already know the project's state
and next step — and approved work to proceed safely while I'm away — so I can
steer many projects from anywhere without re-explaining context or babysitting
terminals.* Current alternatives people actually use: a hand-written
CLAUDE.md + the agent's native memory, an opinionated skills framework
(superpowers), spec-driven artifact kits (spec-kit), session-manager apps
(Conductor, Omnara), and now Claude Code's own Remote Control / Agent View.

## Competitive teardown (three lanes)

| Lane | Competitor | Does well | Gap vs Horus's job | Positioning / price | Evidence |
| --- | --- | --- | --- | --- | --- |
| Memory | **cognee** | Open-source agent memory as a knowledge-graph+vector engine on one Postgres; memory-native API (remember/recall/improve/forget); self-improving retrieval; plugs into Claude Agent SDK, LangGraph, etc.; $7.5M seed | Stores *extracted conversational/semantic facts* in a runtime service; no notion of a project's decisions/backlog/next-step as committed, human-readable repo files; needs a running engine | "The open-source AI memory platform for agents"; OSS + managed cloud | [github.com/topoteretes/cognee](https://github.com/topoteretes/cognee), [cognee.ai](https://www.cognee.ai/) |
| Memory | **mem0** | Vector-first bolt-on memory, largest community (~47k stars), automatic extraction, free tier | Same category gap as cognee; per-user recall, not per-project PO state | OSS core; Pro graph ~$249/mo | [developersdigest.tech comparison](https://www.developersdigest.tech/blog/best-ai-agent-memory-providers-2026) *(secondary)* |
| Memory | **Zep / Graphiti** | Temporal knowledge graph — "what was true, when"; strongest on temporal benchmarks (LongMemEval 63.8%) | Same; a fact database, not a working ritual or repo artifact | Flex ~$125/mo · 50k credits | [same comparison](https://www.developersdigest.tech/blog/best-ai-agent-memory-providers-2026) *(secondary)* |
| Memory | **Letta** | Full agent runtime; agent manages its own memory like an OS (RAM/disk paging) | An execution environment — adopting it means moving *into* Letta, the opposite of riding native CLIs | OSS + cloud | [same comparison](https://www.developersdigest.tech/blog/best-ai-agent-memory-providers-2026) *(secondary)* |
| Workflow | **superpowers** | The dominant opinionated *inner loop*: brainstorm → spec → plan → worktree → TDD subagents → fresh-agent review → finish; ~174k stars; Anthropic marketplace plugin | Owns *how to build one thing well*; no cross-project memory, no fleet, no backlog/vision lifecycle, no unattended execution | Free OSS plugin; "an engineering culture as markdown" | [github.com/obra/superpowers](https://github.com/obra/superpowers), [andrew.ooo review](https://andrew.ooo/posts/superpowers-agentic-skills-framework-claude-code/) |
| Workflow | **spec-kit** (GitHub) | Spec-driven artifacts — constitution / spec / plan / tasks — committed to the repo as durable files; the closest occupant of Horus's *planning-artifact zone* | Per-feature artifacts, not a living product state (vision/backlog/shipped/rules) or resume handoff; no fleet, accounts, or dispatch | Free OSS; "the *what* before the *how*" | [dev.to spec-kit vs superpowers](https://dev.to/truongpx396/spec-kit-vs-superpowers-a-comprehensive-comparison-practical-guide-to-combining-both-52jj) |
| Workflow | *combo practice* | The community already composes them: spec-kit for the *what*, superpowers for the *how* — proof that workflow layers CAN coexist over shared repo artifacts | The combo still lacks the outer loop (market → vision → convergence) and everything below (accounts, fleet, unattended) | — | [same dev.to article](https://dev.to/truongpx396/spec-kit-vs-superpowers-a-comprehensive-comparison-practical-guide-to-combining-both-52jj) |
| Cockpit | **Claude Code native** (Remote Control · Dispatch · Agent View) | Phone as a window into a local session (all plans, research preview); start tasks from phone; `claude agents` dashboard for parallel sessions (shipped 2026-05-11) | One account, one machine, one provider; no scheduling, no authority envelopes, no cross-project fleet state, no Codex | Bundled free with Claude Code | [radar.firstaimovers.com guide](https://radar.firstaimovers.com/claude-code-remote-control-dispatch-multi-device-guide-2026) *(secondary — verify against official docs in a deeper pass)* |
| Cockpit | **Conductor** | Mac desktop cockpit; a git worktree per agent workspace; clean diff review; Claude + Codex; local-first | Single machine, single account per agent; review-centric, no continuity or dispatch | Free Mac app | [nimbalyst roundup](https://nimbalyst.com/blog/best-agent-management-tools-2026/) *(secondary)* |
| Cockpit | **Omnara / AgentsRoom** | Phone-first steering of running agents; AgentsRoom adds a desktop cockpit beyond Claude/Codex | Session steering, not project memory; no continuity contract, no envelopes | Freemium | [agentsroom.dev roundup](https://agentsroom.dev/blog/best-multi-agent-coding-tools) *(secondary)* |
| Cockpit | **Vibe Kanban** | Kanban board over agent tasks; was the category's poster child | Company shut down 2026-04-10; continues as community OSS — a cautionary datum on the category as a *business* | Apache-2.0, community | [nimbalyst kanban piece](https://nimbalyst.com/blog/claude-code-session-kanban-organize-ai-agents/) *(secondary)* |

## Verdict — market-gap per lane (broaden-adoption frame)

| Lane | Saturation | Reading |
| --- | --- | --- |
| Agent memory | **Red** as a memory *database* — four funded/famous players | But Horus is not in that category: git-committed, human-readable PO state (decisions, backlog, next step) has **no named occupant**. The lane is red for what Horus shouldn't build and green for what it already is. cognee et al. are potential *composition partners* (semantic recall over `.horus/` archives), not competitors. |
| Opinionated workflow | **Red** for the inner loop (superpowers won it — 174k stars, marketplace distribution); **yellow** in the planning-artifact zone (spec-kit overlaps but is per-feature, not living product state) | The *outer loop* — market → vision → convergent roadmap → backlog readiness, run repo-local — is **green/unoccupied**. The documented spec-kit+superpowers combo practice is outward proof for X6's coexistence hypothesis: layered workflows over shared repo artifacts already happen in the wild. |
| Substrate / cockpit | **Red and commoditizing fast** for single-machine, single-account session management — the native apps now ship phone control and a session dashboard for free | The surviving gap is exactly Horus's shape: **multi-account isolation with honest usage, cross-project fleet continuity, cross-provider (Claude + Codex), and envelope-gated unattended execution with independent verification**. Nobody in the shallow pass covers any two of those together. Native absorption is the standing risk. |

## Verdict — build / adopt / compose per capability (deepen-own-use frame)

Added after owner review: the confirmed working intent is own-use; the
broaden-adoption verdict above was requested as a calibration test. Same
evidence, own-use reading:

| Capability | Call | Reasoning from the teardown |
| --- | --- | --- |
| Committed PO memory (decisions / backlog / next step as repo files) | **Build / keep** | No external occupant; the memory-DB category solves conversational recall, a different job. |
| Semantic recall over grown `.horus/` archives | **Compose later, never build** | cognee-class engines are good at exactly this and integrate with Claude Agent SDK; only worth wiring if real BI-project use shows a recall need. |
| Inner-loop engineering workflow (TDD, spec, review rituals) | **Adopt selectively, don't build** | superpowers won that space; X6's re-scan tests coexistence over the contract — Horus stays outer-loop. |
| Planning-artifact conventions | **Keep contract; borrow selectively** | spec-kit's constitution/spec/plan/tasks are per-feature conventions worth reading for ideas; the living product state stays ours. |
| Single-machine session cockpit / phone window | **Adopt native as it matures** | Remote Control / Agent View cover the session-window job free; keep Horus effort on what native lacks (feeds the Dashboard-DoD convergence question). |
| Multi-account isolation + honest usage | **Keep (done)** | Nothing external offers it; facet reads converged. |
| Fleet continuity + envelope-gated unattended dispatch with independent verification | **Build / keep** | Unique in the shallow pass; the core own-use dividend. |

## Vision draft (PR-FAQ, one paragraph)

*Horus turns every git repository into a self-briefing product. Any AI coding
agent — Claude, Codex, whatever comes next — opens the repo and already knows
what the product is, what was decided, what shipped, and the exact next step;
the owner steers a whole fleet of such projects from a terminal, browser, or
phone, across isolated provider accounts with honest usage; and work the owner
pre-approved ships while they are away, under a bounded, revocable authority,
verified by an independent supervisor rather than the worker's own word. The
agents and their vendors keep improving execution; Horus owns what they all
still lack — durable product memory and safe delegation of the owner's
intent.*

**Hard FAQ:**

1. **Why now?** Agent CLIs commoditized execution and are now commoditizing
   session cockpits (Remote Control, Agent View); the coordination layer above
   — continuity, fleet, authority — is validated demand and still unowned.
2. **Why us?** Dogfooded: 105 shipped work items, the unattended loop proven
   on a real delivery, and a deliberately small machine-read contract instead
   of a framework to move into.
3. **Biggest risk?** Native absorption — Anthropic/OpenAI shipping
   multi-account, scheduling, or fleet views would erase the substrate moat.
   The durable position is the vendor-neutral committed contract and the
   cross-provider posture, which a single vendor is structurally unlikely to
   offer.
4. **Second risk?** Solo-shaped: the product serves owner-operators; the team
   story (multi-human) is an explicit non-goal today, which caps the audience.
5. **Would people pay?** Unproven — the adjacent cockpit category has already
   produced one shutdown (Vibe Kanban); the memory category raises venture
   money. Adoption ≠ revenue in this space.

**Market-size sanity:** the space is demonstrably real (a $7.5M seed in memory,
174k stars in workflow, native phone features shipping) but thin as a
standalone business — one line, as promised.

## Candidate backlog items (owner disposes; none created here)

| Candidate | From which gap/assumption |
| --- | --- |
| Name **spec-kit** as the primary subject of the X6 alternatives re-scan (`x6-workflow-alternatives-refresh`) — it is the closest planning-artifact overlap, and the spec-kit+superpowers combo is live coexistence evidence | Workflow lane: yellow zone + combo practice |
| Explore-phase probe: semantic recall over `.horus/` archives via a composable memory engine (cognee-class) — adopt/compose, never build a memory DB | Memory lane: red-as-DB / partner-as-recall |
| Fold the native Remote Control / Agent View facts into the Dashboard-facet convergence question the product audit already routed (did TUI-over-SSH win; what is web-launch for?) | Cockpit lane: native commoditization |
| Positioning line for README/naming work: "the layer the native apps stop at — accounts, fleet, continuity, delegated authority" (feeds the existing `product-naming` card, no new card) | Cockpit verdict's surviving gap |

## Sources (every page opened)

- https://github.com/topoteretes/cognee
- https://www.cognee.ai/
- https://www.developersdigest.tech/blog/best-ai-agent-memory-providers-2026
- https://github.com/obra/superpowers
- https://andrew.ooo/posts/superpowers-agentic-skills-framework-claude-code/
- https://dev.to/truongpx396/spec-kit-vs-superpowers-a-comprehensive-comparison-practical-guide-to-combining-both-52jj
- https://radar.firstaimovers.com/claude-code-remote-control-dispatch-multi-device-guide-2026
- https://nimbalyst.com/blog/best-agent-management-tools-2026/
- https://nimbalyst.com/blog/claude-code-session-kanban-organize-ai-agents/
- https://agentsroom.dev/blog/best-multi-agent-coding-tools

*Shallow-pass caveat: rows marked (secondary) rest on roundup/aggregator
articles; a deeper pass would verify against primary docs, changelogs, and
pricing pages.*

## Calibration feedback to encode in the market-scan skill text

- Owner's standing intent is deepen-own-use; the broaden-adoption verdict was a
  calibration request. Both verdicts from one teardown worked — keep that.
- End every scan with an explicit follow-up offer: dive deeper into ONE named
  topic from the receipt (example the owner gave: the one-line market-size
  claim) or proceed to the next step. Depth stays owner-pulled, never pushed.
- Receipt format followed the audit calibration (fixed spine, consolidated
  tables, no-context prose, content pasted in the terminal) — carry the same
  rules into the skill text.
