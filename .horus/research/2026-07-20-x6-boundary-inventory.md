# X6 boundary inventory — substrate vs continuity contract vs workflow policy

Date: 2026-07-20 · Branch: `vision-branch-x6-workflow-selection-compatibility` ·
Method: inward-only — import-graph and consumer analysis over `horus/` at v0.0.73
(`fd24a8d` lineage), no web work, no third-party installs. Owner reviewed the
findings live in the originating session and directed the follow-up cards.

## Finding: three layers, not two

The umbrella card hypothesized two separable layers (utility platform vs
opinionated workflow). The code shows three, and the middle one is where the
compatibility question actually lives.

### 1. Session/account/scheduler substrate — workflow-agnostic today

`launch`, `launcher`, `run_executor`, `schedule`, `envelope`, `notify`,
`notify_listen`, `input_bridge`, `registry`, `tmux_runner`, usage capture,
accounts/isolation, the pty/terminal stack import **nothing** from `backlog`,
`continuity`, or `closure`. `launch.py` states its whole interface: agent +
account + permission posture + repo path + **a bare prompt string**
(`horus/launch.py:22`). `schedule.py` mechanics know a card only as a
pass-through name for the andon label. This layer would run any agent, in any
repo, with any prompt — workflow or no workflow.

### 2. Continuity contract — the small machine-read surface (the hinge)

What the cockpit features actually parse:

- **Session contract**: PRD **frontmatter** via the single chokepoint
  `frontmatter.resolve_focus` (`current_focus` / `next_action` / `next_prompt` /
  `execution_recommendation` / `last_updated`). Consumers: dashboard, TUI,
  resume-preflight, routines, templates, cli, github_catalog, skills. Nobody
  parses PRD.md ad hoc.
- **Dispatch contract**: the backlog **card frontmatter schema** (`backlog.py`
  parser; `readiness`/`autonomy` → `readiness_queue` gates scheduler admission
  at arm time; card scope feeds `horus run --card`; `supervise` →
  `backlog.ship` stamps delivery). Needed only for autonomous dispatch;
  attended projects can live on the session contract alone.
- **Closure discipline**: `closure.py` — what makes "pending delivery"
  computable across machines.

The deepest substrate→workflow coupling in the codebase is exactly one place:
`supervise.py` imports `backlog` + `closure` (`supervise.py:276-289`), because
accepting autonomous work means stamping a card shipped. Deliberate and
nameable.

### 3. Workflow policy — model-read prose + the ritual skills

Everything that makes our PRD look like our PRD: the Vision facet table,
convergence criteria, Shipped ledger, Rules, card *bodies* (Why / Acceptance /
Reviews). No tool parses these structurally except the consolidate facet
read-out — itself part of the workflow. The 17 bundled skills split the same
way: `horus-consolidate` / `horus-infer` / `horus-execution` **maintain the
contract** (core-adjacent); pathfinder / market-scan / roadmap-branches /
scope-cards / backlog-refine / product-audit / skill-audit /
process-retrospective are **direction-setting rituals** — callable, optional,
and no code path breaks without them. (Owner confirmation: pathfinder was never
intended as core.)

## The two-loops framing

- **Horus's workflow is an outer loop**: what to build next, how a fresh
  session resumes, when work is ready to dispatch, when direction is
  re-examined. Product-owner territory.
- **Superpowers-class bundles (obra/superpowers, mattpocock/skills, agent-skills
  collections) are an inner loop**: how to implement well once you know what to
  build — spec-first, TDD, review rituals; established SWE practice adapted to
  agents (consistent with the 2026-07-16 po-capabilities receipt, which found
  them inward-facing and high-ceremony — that verdict is background, not
  current evidence).

They collide only in the shared artifact zone: both want to own "what is the
plan/spec/backlog document". The precise compatibility question is therefore:
**can an external bundle own the inner loop and its spec artifacts while the
Horus contract fields (frontmatter + card schema, or a thin projection into
them) stay authoritative for resume and dispatch?**

## Field datum: fabric-metadata-driven-medallion

A production Fabric ingestion project, Horus-onboarded, migrated to PRD v3:

- It runs on the **session contract only** — no `.horus/backlog/` directory at
  all; its backlog is a ~60-line prose section in PRD.md. A production data/BI
  project living happily on the lighter tier is live evidence for the two-tier
  contract split.
- It already ran the artifact-ownership contest once: `PROJECT_STATUS.md` was
  frozen 2026-06-25 with a SUPERSEDED banner pointing at `.horus/` — recorded
  reason "no double-bookkeeping". When two systems both owned the status/plan
  artifact, the observed resolution was **ownership transfer, not
  coexistence**.

## Implications adopted by the owner

1. Horus-as-product = substrate + continuity contract; the PO rituals are
   optional callable policy ("a call when we need to refine").
2. The boundary is not PRD-vs-backlog; it cuts through both files between
   machine-read frontmatter/schema and model-read prose.
3. Cheap option-preserving disciplines instead of a selector now: substrate
   modules never import workflow modules (true today, `supervise` the one named
   exception); workflow-structure reads keep funneling through the named
   chokepoints (`resolve_focus`, `backlog` parser, `closure`).
4. The engine analogy: substrate + contract = the game engine; workflow prose
   and skill bundles = per-game content. Horus is a stepping stone toward
   data/BI use cases needing fewer SWE formalities, so the real-project probe
   is a data project (fabric), not another code repo.
5. A workflow-*swap* experiment (installing a foreign bundle to test
   conflict/coexistence) belongs in a disposable repo or pbi-ecosystem — never
   first in the production probe.

## Feeds

Cards shaped from this receipt: `x6-continuity-contract-declaration`,
`x6-workflow-alternatives-refresh`, `x6-fabric-contract-probe` (all
`branch: vision-branch-x6-workflow-selection-compatibility`).
