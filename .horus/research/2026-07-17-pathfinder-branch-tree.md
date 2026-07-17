# Pathfinder branch tree — horus-harness, 2026-07-17 (second dogfood)

Intent: deepen-own-use (pre-declared in PRD next_action). Market evidence reused
from the same-day receipt `2026-07-17-repo-local-po-rebaseline.md` (zero new spend,
owner-approved). No cards were created from this run — the owner chose to build and
calibrate the skills first.

> **Held-out for the convergence test:** the owner intends to re-run pathfinder
> end-to-end with the factored skills WITHOUT feeding this receipt in, to check
> whether an independent run converges to similar findings. Do not use this file
> as input to that rerun; compare against it afterwards.

## Where we are (position root)

Infra era ending: **converged** — Accounts & isolation (DoD met: default+self-healing
isolation, one-live-process guard, per-account usage), Introspection & self-improvement
(product-audit / skill-audit / process-retrospective shipped, zero open cards),
Distribution (routine at v0.0.59). **Built but unproven** — PO lifecycle: facets,
convergence read-out, market-scan, pathfinder all shipped 2026-07-13..17 and had not
yet changed what gets built. **Active frontiers** — Delegation calibration (5 open
cards, over-instrumented on own data), Continuity core (neutrality claimed but never
verified; DoD still describes generic durability), Dashboard (1 card).

## Where the market is (shells → verdict → risk, from the reused receipt)

- **Shell 1 — memory primitive: commoditized.** Native CLAUDE.md/MEMORY.md (+subagent
  memory Feb'26), Cline/Roo memory-bank, .clinerules, MCP memory servers. All
  agent-locked and machine-local. Adopt/compose, never compete.
- **Shell 2 — per-feature pipelines: occupied but orthogonal.** Spec-Kit,
  claude-task-master: no living continuity, no fleet, no resume. Components under
  Horus, not competitors.
- **Shell 3 — the triad (agent-neutral continuity × cross-project fleet × PO
  lifecycle): empty.** Nothing to adopt — build obligation for deepen-own-use.
- **Risk (once):** native memory keeps absorbing ground from below; hedge = interop
  (read native stores into `.horus/`), not racing them.

## The tree

```
WHERE WE ARE ── infra converged · PO loop built-unproven · neutrality unverified
│               calibration over-instrumented on own data
├── A. "One state, any agent"      → Continuity core (rescoped)   [recommended primary]
├── B. "The loop earns its keep"   → PO lifecycle                 [secondary]
├── C. "Dispatch you can trust"    → Delegation calib. (rescoped) [reduced to 2 items]
├── D. "Cockpit polish"            → Dashboard                    [filler]
├── X1. "Fleet knowledge plane"    → speculative, no facet yet    [strongest new thought]
└── X2. "Cross-agent deliberation" → speculative, no facet yet    [park until A-parity]
```

## Branches

### A — One state, any agent (primary)
Market position: repo-local memory exists everywhere but every implementation is
agent-locked + machine-local; you already have the neutral store (`.horus/` in git,
dual managed blocks) but miss verified Codex-supervisor parity and any path for
agent-private memories to flow back into the neutral store.
1. `cross-agent-resume-parity` — scripted A/B protocol: fresh Codex session on the
   isolated account, "resume this project", scored vs a fixed checklist (fetch-first ·
   exact next_action · version floor · consolidate flow · branch→PR→close closure);
   Claude control run; per-checkpoint receipt; each fail becomes a bug card.
   Pre-registered suspects: Claude-surface hooks (SessionStart fetch signal, Stop
   closure, merge gate) may not fire under Codex; interactive skill gates may degrade;
   deep-research composition untested.
2. Gap cards from #1 (cannot be pre-scoped — findings become their own cards).
3. `native-memory-interop` (explore) — NOT file sync / NOT a database; git stays the
   only cross-machine layer. One-way distillation: `horus consolidate` gains a
   read-only detector signal ("agent-private memory modified since last
   consolidation: <paths>"); the in-loop agent promotes durable non-secret facts into
   PRD/cards. PoC = one round trip (Claude private memory → PRD → Codex acts on it);
   dies cheap if traffic is trivia. Phase 2 (out of PoC): reverse projection.
4. `scoped-machine-requirements`, `project-workflow-overrides` (existing, retained).
Converged when: a fresh session of either CLI, on any machine, resumes the exact next
step with the same guardrails firing — verified by receipt.
Vision edit implied: Continuity-core DoD leads with cross-agent resume ("Any official
agent CLI resumes the exact next step from the same durable `.horus/` state alone,
fetch-first, across machines — no agent-locked memory required").

### B — The loop earns its keep (secondary)
Market position: nobody ships a living convergence lifecycle; you shipped the
machinery this week but it has not yet changed a decision — unproven ceremony until
a pass kills or rescopes something real.
1. `pathfinder-v2-calibration` — DONE via this session: factor into
   roadmap-branches + scope-cards + thin pathfinder (see findings below).
2. `fleet-convergence-pass` — read-outs with real verdicts on 2–3 fleet projects;
   first agenda: Branch C's defer/retire candidates.
3. `explore-converge-lifecycle` (existing) — usage-ripeness flag.
4. `product-naming` (existing) — name encodes the wedge (fleet product owner, not
   memory); falls out once direction settles.
Converged when: one full divergence→convergence cycle on ≥2 projects demonstrably
trimmed/redirected a backlog. Vision edit implied: PO-lifecycle frontier note →
"loop is built; open gap is convergence passes driven by real usage evidence".

### C — Dispatch you can trust (rescoped after owner push-back)
Owner critique accepted: the gap is over-reliance on own measured data (small-n,
confounded, one task mix) instead of external benchmarks/leaderboards/community
experience that already rank tiers for free. Own datums cover only the residual no
benchmark measures (our harness's nudge/bounce rates, effort levels, account
throughput).
1. `external-priors-calibration` (new) — sourced benchmark/leaderboard evidence
   folded into the owner-priors slot of `horus capabilities --models`; rubric reads
   priors-first, own-datums-as-residual; repeatable per model generation.
2. `remote-open-model-worker-probe` (existing) — cost lever, informed by #1.
3. Push-back on existing cluster: `stale-datum-usage-overlap-reconciliation` → low
   (fix only if confounded datums still distort a real decision after priors carry
   the load); `deferred-supervision-completion-receipt`, `worker-progress-heartbeat`,
   `codex-usage-window-semantics` → defer/retire candidates for the convergence pass.
Converged when: dispatches route to the cheapest adequate tier citing external
evidence, and the datum cluster shrank instead of grew.

### D — Cockpit polish (filler, no thesis)
`tui-fleet-artifact-refresh` → `account-settings-sync` → `init-scaffolds-project-ci`.

### X1 — Fleet knowledge plane (speculative; strongest new thought)
Gap: hard-won lessons live in one repo's `## Rules` (tmux socket trap, uv-install
trap, hook guard invariant) — paid for once, invisible to the next project; market
has nothing cross-project (native memories are per-repo AND per-agent). Idea: a
curated fleet-level rules/patterns layer under `~/.horus/` (or a meta-repo) that
`horus init` seeds new projects from and consolidation can PROMOTE a repo rule into —
repo stays source of truth; fleet layer is upstream inheritance, not sync. PoC:
hand-promote 3–5 portable rules, have init offer them, start one real project with
them inherited. Risk: curation decay — PoC must show inheritance beats re-derivation.

### X2 — Cross-agent deliberation (speculative; park until A-parity)
Gap: neutrality today is passive redundancy; nobody exploits two DIFFERENT models
sharing the same durable state. Idea: a repo-local ritual — one CLI drafts a decision,
the other critiques it against the same PRD; disagreement is a cheap review signal no
single-agent setup produces. PoC: one real decision through draft→cross-critique;
verdict = did the second model catch something material. Tension: must stay a ritual
(skill), never an execution plane.

## Recommendation (held loosely)

A primary · B secondary · C reduced to its two rescoped items · D filler · X1 earns
an explore card · X2 parks · spec-pipeline-compose drops off unless re-added (under
deepen-own-use it only matters if the owner actually wants to use those pipelines).

## Skill-calibration findings from this run (drove the v2 factoring)

1. Read-out must come FIRST (position → market → directions), direction pick second,
   diff/cards third — v1 gated on a facet diff before any overview.
2. Narrative depth, not bullets — descriptions were too shallow to decide on.
3. A plain numbered roadmap per branch.
4. Fixed read-out template with a no-repetition rule (market risk was stated twice).
5. Claims discipline: every "missing/weak/better" names its comparison baseline.
6. Re-justify the EXISTING backlog against intent with explicit push-back — v1
   inherited the 5-card calibration cluster and merely ordered it.
7. The deliverable is a BRANCH TREE of alternative roadmaps (incl. 1–2 speculative
   branches), not one merged roadmap — merging collapses the divergence.
8. Every proposed item ships as a fully populated, self-sufficient card draft
   (fresh agent + PRD + card = can start), except second-order items which stay
   explicitly "findings become their own cards".
9. Market evidence must appear INSIDE each branch ("exists but misses X / you have
   Y but miss Z / therefore these items").

Architecture decision (owner, this session): factor step 3 into `roadmap-branches`
and step 4 into `scope-cards`, each independently invocable and skill-auditable;
`pathfinder` v2 becomes the thin sequencer (intent gate → brief → market-scan →
roadmap-branches → scope-cards) with receipts as the interfaces between steps.
Convergence test planned: an independent e2e rerun should reproduce similar findings.
