# Roadmap branches: deepen-own-use re-baseline — 2026-07-31

**Intent:** deepen-own-use (audience = one solo owner-operator). Verdicts are
build / adopt / compose per capability.
**Inputs:** position brief (this session) · inward audit
`.horus/audits/2026-07-31-product.md` · market scan
`.horus/research/2026-07-31-market-scan-build-vs-adopt.md` · prior tree
`2026-07-20-roadmap-branches-rebaseline.md`.

## 1. Where we are

Facet standings are in the audit — not restated. Life-stage on top:

| Facet | Life stage |
|---|---|
| Continuity core | **steady-state** — 64 sessions resumed; cross-machine untested this window |
| Accounts & isolation | **steady-state** — both accounts live, isolation holding |
| Introspection & self-improvement | **converged for now** — strongest facet; the prior tree's branch D |
| Distribution | **steady-state, throttled** — 6 releases in 11 days, then 19 commits held |
| Dashboard / cockpit | **active frontier + defect** — the moat, and it reports 56% of sessions falsely |
| Delegation calibration | **built-but-unproven** — no dispatch this window |
| Autonomous dispatch | **built-but-unproven** — 11 open cards, 0 timers ever armed |
| PO lifecycle | **active frontier, stalled** — 47 explore vs 27 converge |

**Honest overall position:** the engine is proven and the *operational plane* is the
differentiator — but the two facets carrying the most open work (Autonomous dispatch,
PO lifecycle) are the two with the least evidence of use.

**Carry-forward from the 2026-07-20 tree, re-justified not inherited:**

| Prior branch | What happened | Now |
|---|---|---|
| **B — Run the games** *(was primary)* | **not executed**; PO lifecycle still weakest | returns as **C**, with a sharper reason |
| **D — Close the improvement loop** *(was secondary)* | **executed** — wildcard v5, budgets, 5 audit receipts | retired: Introspection is now the strongest facet |
| **A — Declare the engine's API** | untouched; owner said this session "no problems felt" | folded into **B** with a *new* justification (MCP needs a declared contract) |
| **C — Feed the proven loop** | untouched; 0 timers armed | returns as **D**, now with a shrink option |
| **E — Cockpit rationalization** *(filler)* | untouched | promoted to **A** — today's audit found a real defect |
| **S1 — BI-work continuity profile** | owner declared fabric non-influential (2026-07-31) | dropped, reason recorded |
| **S2 — Fleet recall plane** | parked | re-enters as **S2** in changed form |

## 2. Where the market is

Cited from the scan receipt, stated once: three teams independently reached repo-local
Markdown continuity (AICTX, agent-memory, memories.sh); **none is adoptable here** —
all single-project, none spanning accounts or agents. Meanwhile the platform moved
*up*: `claude agents` ships session rows with PR links and honest `Working` /
`Needs input` states (CHANGELOG 2.1.198–2.1.212), and Agent Teams exists behind an
env flag.

**One verdict:** the differentiator is no longer the file format — it is the span
(multi-agent × multi-account × multi-project). **Risks:** the platform keeps absorbing
upward; and Codex's own session surface was **never examined** — a hole big enough to
change branch A, since Horus is half-Codex.

## 3. The tree

```
Horus v0.0.79 (+19 unreleased) — engine proven, operational plane is the moat.
Two facets hold the most open work and the least evidence of use.
│
├── A  Make the cockpit tell the truth ...... Dashboard / cockpit        [primary]
├── B  Open the contract to agents (MCP) .... Continuity core + Distrib  [secondary]
├── C  Make the PO loop actually run ........ PO lifecycle               [secondary]
├── D  Spend the dispatch machinery — or shrink it .. Autonomous dispatch [filler]
├── S1 Codex parity audit .................. (no facet — speculative)   [primary-cheap]
└── S2 Cross-machine fleet READ ............ (re-tests an out-of-scope line) [park]
```

## 4. The branches

### A — Make the cockpit tell the truth *(primary)*

**Thesis.** The scan says the cockpit is the only real moat; the audit says it lies
about 56% of sessions. Under deepen-own-use, a daily surface that misreports your own
behaviour is the highest-value defect in the product.

**Market position.** *Session views exist already* — `claude agents` has rows, PR
links and honest states — *but they miss* Codex, accounts, and cross-project fleet.
*You already have* that span, *but still miss* honest states on it. *Therefore:* fix
the state model, and scope the registry to what only Horus can add.

**Roadmap.**
1. **Give an owner-initiated close its own terminal status.** Why: `stop_session` and
   `reap_orphans` both write `status="failed"`, so `termination_reason="stopped"` is
   the only thing distinguishing a close from a failure, and no surface reads it. How:
   add a `stopped` terminal state to `registry.TERMINAL`; render it distinctly in the
   TUI and dashboard; backfill is unnecessary (`termination_reason` already carries the
   truth). Weak point: `TERMINAL` is consumed in several places — reaping and
   freshness must keep treating `stopped` as terminal. Non-goal: no change to how
   sessions are stopped.
2. **`session-agent-state-awareness`** (existing, Shaping) — working/idle/blocked per
   session, mechanism already narrowed to hooks + host-supplied. Second-order on item 1:
   honest *terminal* states first, then live states.
3. **Evaluate `claude agents` as the single-agent view** and scope Horus's registry to
   the delta. Findings become their own cards.
4. **`herdr-server-shutdown-fragility`** (Gated) — needs the owner's report-upstream-vs-
   compensate call.
5. **`tui-fleet-artifact-refresh`** (Gated) — small, rides along.

**Convergence criterion.** Every session state the cockpit shows is true, and the
registry holds only what `claude agents` cannot. **Cost:** one to two sessions.

**Implied Vision edits.** None to the facet set. Sharpen **Dashboard / cockpit**'s DoD
to name honesty: *"…and every state it reports is true — a session the owner closed is
never reported as failed."*

### B — Open the contract to agents (MCP) *(secondary)*

**Thesis.** The single adopt/compose gap the scan found. Every comparable tool exposes
its memory over MCP — two make it the *primary* path — while Horus requires shelling
out to a 62-verb CLI.

**Market position.** *This exists already* (AICTX `aictx mcp-server`, agent-memory's
`memory.fetch_context`) *but misses* the fleet. *You already have* the richest state
*but still miss* the standard way an agent reads it. *Therefore:* a read-only MCP
server over the two chokepoints.

**Roadmap.**
1. **`x6-continuity-contract-declaration`** (existing, Shaping) — **re-justified with a
   new reason.** The owner said this session that no compatibility problem is being
   felt, and on *that* argument it stays parked. But exposing a contract over MCP means
   naming what the contract is; declaring it becomes a precondition rather than an
   abstract tidiness exercise.
2. **Read-only `horus mcp` stdio server** — three tools (`horus_resume`,
   `horus_backlog_list`, `horus_prd_read`) reading through `resolve_focus` and the
   backlog parser, so no second state path. Weak point: any agent that can run bash
   already gets this; the dividend is MCP-only clients and a standard shape. Non-goals:
   no write tools, no network transport, no auto-registration.
3. **`research-receipts-surfacing`** (existing, Shaping) — receipts are continuity an
   agent cannot currently find.

**Convergence criterion.** An MCP-capable agent gets project state without shelling out
or learning the file layout. **Cost:** one session for the server, plus the declaration.

**Implied Vision edits.** Add a row to the **surfaces** table (not the facet table):
`MCP server | agents, any vendor | No — a read path over the files`.

### C — Make the PO loop actually run *(secondary)*

**Thesis.** The prior tree made this primary and it did not happen; PO lifecycle is
still the weakest facet. 47 explore vs 27 converge, 26 Deferred — divergence has
outrun convergence, which is the one thing the Vision's breathing model says must not
persist.

**Market position.** *Nothing external does this* — memories.sh sells recall, not
product-owner rituals. *You already have* the divergence half working (this very run)
*but still miss* the convergence half. *Therefore:* run convergence on evidence.

**Roadmap.**
1. **A convergence pass over the 26 Deferred and 47 explore cards** — decide parked vs
   dropped. Why: a third of the backlog is parked, and "deferred indefinitely" is a
   decision nobody has made explicitly. How: `backlog-refine` with the audit as
   evidence. Non-goal: not a grooming pass over everything.
2. **`explore-converge-lifecycle`** (Deferred) — blocked on "a real per-card usage
   signal". Second-order: the signal is the prerequisite, and it may be cheaper than
   the card assumes now that dispatch records exist.
3. **`pathfinder-structured-outcome`** (Shaping) — this run's bundle should be
   machine-findable by the next one; the stale-bundle problem cost a wildcard run.
4. **`wildcard`** (Shaping) — v5 shipped and verified this session; the remaining work
   is registering it in the generator (`bundle-test-phase-skills`, Ready).

**Convergence criterion.** The explore:converge ratio moves on decisions, not on new
cards; every Deferred card is parked *with a trigger* or dropped. **Cost:** one owner
session.

**Implied Vision edits.** None. PO lifecycle's DoD already names convergence as the
frontier.

### D — Spend the dispatch machinery, or shrink it *(filler)*

**Thesis.** 11 open cards for a facet that has **never run unattended**. Under
deepen-own-use, that is either the biggest unrealised asset or the biggest carrying
cost, and the honest move is to force the question rather than keep the cards warm.

**Market position.** *Agent Teams exists* (experimental, env-gated) but is in-session
orchestration, not scheduled unattended delivery. *You already have* envelopes,
timers, supervise and andon *but still miss* a single real run. *Therefore:* one run,
or a rescope.

**Roadmap.**
1. **Leg search for `autotest-e2e-away-mode-drill`** — roster is 2 of 3, and the
   deferral date passed 2026-07-29 with nothing re-classifying it. Also settle whether
   one leg should be a deliberately-partial fix (the 2026-07-26 reframe: can the loop
   catch work that passes every gate but is incomplete?).
2. **Run the drill.** Spends real multi-account weekly capacity — that is the point.
3. **If it will not be run: rescope the facet to attended dispatch** and disposition
   the 11 cards accordingly. This is a legitimate outcome, not a failure.

**Convergence criterion.** Either one unattended end-to-end run, or the facet's DoD is
rewritten to attended-only. **Cost:** one multi-account session, or one decision.

**Implied Vision edits.** Conditional: if rescoped, **Autonomous dispatch**'s DoD drops
"under a standing pre-authorized envelope" and becomes attended supervision.

## 5. Speculative branches

### S1 — Codex parity audit *(speculative, cheap, re-tests the moat's premise)*

**Gap it names.** Branch A rests on "the platform's session view is Claude-only". The
scan **never examined Codex's own session surface** — and Horus is half-Codex (14 of 64
sessions). If Codex ships an equivalent, the cockpit's moat is narrower than every
branch above assumes.

**Idea.** Read OpenAI's Codex release notes for a session-list/attach surface, then one
live probe of `codex` for equivalent verbs.

**Cheapest PoC.** One fetch plus one CLI probe — under an hour.

**Why it fits the intent.** It tests the single assumption the primary branch rests on,
for almost nothing.

**Converge/drop.** *Converges* if Codex has no fleet/session view → branch A's premise
is confirmed and this dies having done its job. *Dropped* — and A is rescoped — if
Codex ships one, because then Horus's registry is duplicating two first-party surfaces
rather than one. **Dying cheap is success here.**

### S2 — Cross-machine fleet READ *(speculative, park; re-tests an out-of-scope line)*

**The out-of-scope line under test.** The Vision excludes *"the distributed
execution/orchestration plane (multi-machine worker control)"*. But **Continuity core's
own DoD claims "across machines"**, credentials deliberately never travel, and the
audit found cross-machine resume **untested this window**. So the boundary and the DoD
are in tension, and the boundary has never been re-tested against use.

**Idea.** A read-only cross-machine fleet view — which projects/sessions exist on the
other machine — with **no control path whatsoever**. Reading is not orchestrating.

**Why park.** No evidence the owner hit this friction recently; the audit could not
even measure cross-machine resume. Parking is the honest posture until that evidence
exists.

**Converge/drop.** *Converges* if a real cross-machine session shows the owner guessing
at the other machine's state. *Dropped* if the next cross-machine session resumes fine
from pushed git — which would mean the existing spine already covers it.

## 6. Existing-backlog dispositions — nothing inherited silently

| Disposition | Cards |
|---|---|
| **Into A** | `session-agent-state-awareness`, `herdr-server-shutdown-fragility`, `tui-fleet-artifact-refresh`, `session-host-protocol`, `telegram-idea-capture` |
| **Into B** | `x6-continuity-contract-declaration` (new justification), `research-receipts-surfacing`, `continuity-sync-friction`, `concurrency-safe-continuity` |
| **Into C** | `explore-converge-lifecycle`, `pathfinder-structured-outcome`, `wildcard`, `bundle-test-phase-skills`, `decision-doc-skill`, `repeated-question-skill-mining`, `session-process-cadence` |
| **Into D** | `autotest-e2e-away-mode-drill`, `verify-guidance-long-running-services`, `audit-advisory-interval`, `fleet-sourced-autonomous-batch`, `tui-toggle-card-into-scheduler`, `window-aware-scheduling`, `dispatch-collision-guard`, `dispatch-receipt-seam`, `intent-preserving-goal-campaign`, `warm-supervised-worker-poc`, `autonomous-advisory-dispatch-posture`, `telegram-group-project-topics` |
| **Keep, steady-state** (no branch; ship when touched) | `merge-release-owner-gate` (high, own session), `refine-autonomy-hardening-lens`, `skill-drift-surfacing-and-refresh`, `managed-instruction-drift-lint`, `skill-self-calibration-probe`, `stale-worktree-accumulation`, `optional-host-ci-coverage`, `windows-native-horus-setup`, `new-machine-setup-guidance`, `product-naming`, `app-usage-cost-opacity`, `horus-phone-chat-poc` |
| **Keep, accounts lane** | `account-settings-sync`, `codex-isolated-config-leak`, `account-login-verb`, `isolated-account-plugin-parity`, `native-app-account-launch-spike`, `prd-worked-by-account`, `usage-analytics-read-out` |
| **Keep, calibration lane** | `automated-model-roster-grounding`, `dispatch-workflow-comparative-study`, `remote-open-model-worker-probe`, `deferred-supervision-completion-receipt`, `worker-progress-heartbeat`, `openrouter-provider-support` |
| **PUSH-BACK — retire candidates** | The **X4 cluster** (`vision-branch-x4-model-harness-plane`, `x4-pi-harness-via-proxy`, `x4-claudex-subagent-context-policy`, `x4-codex-usage-in-claude-code`, `x4-provider-credential-routing`, `x4-tui-execution-route-axis`) — the branch took a net-negative verdict 2026-07-18; its one open defect (the statusline leak) was **resolved 2026-07-31 with no revert needed**, so the branch has no live evidence pulling it forward and 6 cards of carrying cost. Argued through the intent: running other models is not something own-use has demanded in 13 days. |
| **PUSH-BACK — defer, do not re-raise** | The **X5 cluster** (7 cards) — owner-confirmed **undated** hold; PRD says explicitly do not re-raise as a finding. Named here for completeness only. |
| **PUSH-BACK — drop with reason** | `x6-fabric-contract-probe` — the owner declared fabric non-influential for these decisions (2026-07-31), which removes the probe's only evidence source. `x6-workflow-alternatives-refresh` — X6 stays alive for a superpowers-style swap test, but a *refresh* of alternatives is not that test. |
| **Unstamped umbrellas** | `vision-branch-x6-workflow-selection-compatibility` — kept alive by owner decision this session, pending a named probe (see A/S1 for what a real probe looks like). |
| **Steady-state, no action** | `fresh-vs-resume-context-split`, `scoped-machine-requirements`, `project-workflow-overrides`, `tui-campaign-native-goal-probe` |

## 7. Recommendation, held loosely

**A primary.** The intent is own-use, the scan says the cockpit is the only real moat,
and the audit says it is lying to you on 56% of sessions. Nothing else in the tree is
both defective and load-bearing.

**S1 first, though** — it is under an hour and branch A's premise depends on it. Doing
A without knowing what Codex ships risks building the differentiator on an assumption
the scan never tested.

**C secondary**, because it was the prior tree's primary and did not happen; if it is
skipped again, that is itself information worth acting on — it would mean convergence
is not something this project actually does, and the Vision should say so.

**B secondary**, cheap and self-contained. **D filler**, but with a real deadline: its
deferral date has already passed once.

**Park S2** until cross-machine friction is actually felt.

## 8. Owner verdict — the tree was REJECTED, and why (2026-07-31)

**No branch was picked.** The owner: *"I'm not really convinced by any so far, I could
see potential in customizing herdr to better fit our use, maybe improving the TUI and
so on, none of the listed items seem that relevant at the moment."*

**The diagnosis, owner-stated:** this is the same mistake `wildcard` kept making.
*"Pathfinder is meant to be an overall arch that explores new ideas and audits if we are
going on the right direction, not a way to refine our backlog. If I want to reorganize
existing work I'd go directly to backlog-refine."*

**The mechanism.** All four branches were assembled from facets that already had open
cards, so the tree could only re-arrange work already in the backlog. The direction the
owner actually wants — customising herdr to fit daily use, and TUI ergonomics — was
structurally invisible, because it has almost no cards (one Gated
`herdr-server-shutdown-fragility`, one Shaping `session-agent-state-awareness`). **A
tree built from the backlog can only propose what is already in the backlog.**

Note this skill's own text already warned that *"merely ordering the inherited backlog
is this skill's known failure mode"* — and it happened anyway, because §6 requires every
open card to land in a branch or be pushed back, which creates gravity pulling the
branches into card containers. Exactly parallel to wildcard v4, whose procedure said
"diverge over the branches" and therefore produced backlog triage.

**Also corrected here:** the scan's *session host: KEEP-THIN, do not deepen* verdict is
**wrong for this intent**. herdr carried 11 of 26 sessions since v0.0.78 — the
most-adopted thing shipped recently — and "don't rebuild someone else's tool" is a
market instinct, not an own-use one. Its configurable keybindings, and its
`notification` / `agent` / `pane` surfaces, are an unexplored customisation area.

**Branch B (MCP) is withdrawn** — the use case did not survive the owner's question:
Horus runs Claude Code (187 sessions) and Codex (50), both of which read files and run
bash, so an MCP read path duplicates access they already have twice over.

**Disposition:** A, C and D are recorded but unpicked — not live work. The next
re-baseline should inherit *this section*, not re-derive four branches already declined.
