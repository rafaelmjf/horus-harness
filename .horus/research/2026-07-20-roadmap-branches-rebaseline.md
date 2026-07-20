# Roadmap branches: deepen-own-use re-baseline — 2026-07-20

**What this document is.** The divergence step of the 2026-07-20 pathfinder
calibration run: alternative roadmaps the owner chooses between, built from the
inward audit (`.horus/audits/2026-07-20-product.md`), the outward scan
(`.horus/research/2026-07-20-market-rebaseline.md`), and the two 2026-07-17
branch-tree receipts whose unresolved items are carried forward, not
re-derived. It proposes a tree; **it never merges the tree** — picking is the
owner's convergence decision. Intent: **deepen-own-use** (Horus is the engine;
the owner's data/BI projects are the games).

## 1. Where we are

Horus set out to be a repo-local product owner for AI coding agents and, per
the audit, now *is* one in three verified layers: a workflow-agnostic utility
substrate, a small machine-read continuity contract, and optional
product-owner rituals. Life stage per facet: **Accounts & isolation is
converged** (first facet at its definition of done) and **Distribution is
steady-state** (five releases crossed the full gauntlet this window; one
automation rung open). **Continuity core is one move from done** — the
contract needs declaring, everything else is proven daily. **Dashboard/cockpit
is met-for-the-owner** via the terminal UI over SSH, with the web-launch
ambition now an open question and five dead pre-tmux commands still aboard.
**Autonomous dispatch is built-but-unproven-at-volume** — the loop delivered
one real card and then starved for eligible work. **Delegation calibration has
drifted** — its DoD says model-picking, its own measurements say honest-cost
gating. **PO lifecycle and Introspection are the active frontier**: the
curation pipeline landed and is being calibrated by this very run, while
improvements still don't propagate (126 stale skill installs) and drift
detection still depends on the owner noticing. Overall position in one line:
**the engine is essentially built; what it lacks is declared edges, fuel for
its proven loop, and evidence from the games it was built for.**

## 2. Where the market is

Distilled from the scan receipt (cited there, not re-argued): the *agent
memory* category is funded and crowded but solves conversational recall in
runtime databases — a different job than committed PO state, which has no
named occupant. The *inner-loop workflow* space is owned (superpowers, ~174k
stars, marketplace-distributed), while spec-kit occupies the adjacent
planning-artifact zone per-feature; the documented practice of composing the
two proves layered workflows over shared repo artifacts work in the wild. The
*session cockpit* space is commoditizing fast — Claude Code natively ships
phone control and a session dashboard — but stops at one account, one machine,
one provider, no scheduling, no fleet. **One verdict: Horus's own-use wedge —
multi-account, cross-project, cross-provider continuity plus delegated
authority — is untouched; everything adjacent to it is being commoditized.**
Risks: native absorption of substrate pieces (real, ongoing); building
workflow ceremony no game ever asks for.

## 3. The tree

```
Engine built, edges undeclared; loop proven once, starving;
games (BI projects) barely started using it.
├── A  Declare the engine's API ......... Continuity core + X6      [secondary]
├── B  Run the games .................... PO lifecycle (frontier)   [primary]
├── C  Feed the proven loop ............. Autonomous dispatch       [secondary]
├── D  Close the improvement loop ....... Introspection             [secondary]
├── E  Cockpit rationalization .......... Dashboard / cockpit       [filler]
├── S1 BI-work continuity profile ....... (no facet — speculative)  [explore]
├── S2 Fleet recall plane ............... (no facet — speculative)  [park]
└── P  Parked branches: X4 hold · X5 keep-or-drop · X2 daily brief  [park]
```

## 4. The branches

### A — Declare the engine's API (secondary)

**Thesis.** Own-use payoff: every future decision — which workflow rides a
project, what a BI project must maintain, what the fabric probe measures —
gets a named yardstick instead of an implicit one in two parser modules.
**Market position:** spec-kit already commits planning artifacts but per
feature, not as living product state; you already have the contract *working*
(fabric runs production on the session tier) but still lack it *declared*;
therefore these items. **Roadmap:** 1. `x6-continuity-contract-declaration`
(existing) — name the session tier and dispatch tier, field by field, plus the
import-boundary discipline; weak point: over-formalizing into a spec nobody
reads — keep it one page. 2. `x6-workflow-alternatives-refresh` (existing) —
now with the scan's finding baked in: **spec-kit is the primary subject**, the
combo practice the coexistence evidence; still gated on your attended go.
3. *Second-order:* the workflow-swap experiment — findings from 2 become their
own card, pointed at a disposable repo or pbi-ecosystem, never fabric.
**Converged when:** the contract is citable and one external-workflow verdict
(coexist/borrow/exclusive/drop) is evidence-backed. Cost: ~2 attended
sessions. **Implied Vision edit:** Continuity core DoD gains "…and the
machine-read contract is explicitly declared"; X6 remains a branch until its
disposition.

### B — Run the games (primary)

**Thesis.** The intent is own-use for data/BI work; the audit says decision
quality and tier sufficiency are the *only* unproven parts of the engine — and
only real usage proves them. This branch spends sessions in the games, not the
engine. **Market position:** session managers and native phone features
manage *running agents* but nothing resumes a *product* across weeks and
machines; you already have fabric live on the session tier but pbi-ecosystem
stale at day one and zero recorded probe observations; therefore these items.
**Roadmap:** 1. `x6-fabric-contract-probe` (existing) — refine its evidence
bar first (what counts as an observation, where it lands), then just *use*
fabric: the deploy-validation and PG-onboarding work queued in its own PRD.
2. Revive pbi-ecosystem — run its Layer-1 theme work as a normal
Horus-steered project; its friction is the second probe datum stream.
3. Fleet convergence pass (carried from the 2026-07-17 tree, still undone) —
a read-out with real verdicts on 2–3 fleet projects once probe evidence
exists; *second-order: its findings become cards*. 4. `explore-converge-
lifecycle` (existing, Deferred) — stays deferred until 1–3 yield the per-card
usage signal it waits for; this branch is what produces that signal.
**Converged when:** one BI project demonstrably ran market→backlog→ship on
Horus with less re-explaining than before, and the probe verdict (tier 1
suffices / dispatch tier earned) is written. Cost: absorbed into real work —
that's the point. **Implied Vision edit:** PO-lifecycle frontier note becomes
"loop built; open gap is convergence driven by real usage evidence" (carried
forward from the prior tree, still true).

### C — Feed the proven loop (secondary)

**Thesis.** The dispatch machinery is the engine's most expensive proven
feature and it idles; own-use dividend is real work shipping during owner-away
windows — but only if genuinely-ready work exists, never manufactured filler.
**Market position:** nothing external offers envelope-gated unattended
execution with independent verification; you already have the loop but only
one eligible card; therefore these items. **Roadmap:** 1. Backlog-refinement
pass (the chain's final step) minting Ready—Autonomous eligible cards — the
audit's six prune candidates (`brainstorm`, `vscode-task`, `vscode-open`,
`overhead`, `app`/`mascot`, `focus`) are ideal first mints: small,
deterministic, code-only removals. 2. `autotest-e2e-away-mode-drill`
(existing, Gated on the weekly reset) — the repeatable drill.
3. `verify-guidance-long-running-services` (existing, the lone eligible card)
— feed it to the loop as the live test. 4. X3 close-out (existing, Gated on
the drill). 5. `telegram-group-project-topics` (existing, Ready—Attended) —
steering ergonomics once multiple dispatches run. 6. `warm-supervised-worker-
poc` + `remote-open-model-worker-probe` (existing, Shaping) — decide at
refinement whether either earns an attended envelope this cycle; the prior
tree's "priors-first external benchmarks" item folds into the same decision
(adopt external tier priors only when a real dispatch needs a tier call —
baseline: 97 own datums are small-n and confounded). **Converged when:** the
loop has consumed ≥3 real cards unattended with zero manufactured work.
Cost: refinement session + drill + supervised runs. **Implied Vision edit:**
Delegation calibration is **rescoped** (the audit's routed question): rename
to *Delegation economics*, DoD draft — "Every dispatch names its dividend
(time-shift, capacity, parallelism) and passes the honest-cost gate; tier
choice reads external priors first, own datums as residual; never
auto-routing."

### D — Close the improvement loop (secondary)

**Thesis.** Own-use cost of drift is now measured: stale prose taught a
deleted knob fleet-wide, and the audit skill itself wandered off intent until
you interrupted. This branch makes improvement propagate and drift
self-surface. **Market position:** no external tool refreshes what a CLI
previously wrote into repos (superpowers has the same unsolved problem); you
already have detection pieces (`skill map`, doctor) and two hand-refresh
datums; therefore these items. **Roadmap:** 1. The step-skill rewrites from
this calibration run (audit v3, market-scan v7, roadmap-branches v4 + the
scope/refine tweaks) — each receipt already carries its feedback block;
*in-flight by owner commitment.* 2. `skill-drift-surfacing-and-refresh`
(existing, Shaping) — the dedicated design session; field evidence is already
in-card (one-command refresh, dry-run-zero receipt, missing per-skill
selection, the integrate gap). 3. `tui-fleet-artifact-refresh` (existing,
Gated on 2). 4. Audit-advisory interval fix — releases AND days (small card at
refinement). **Converged when:** a CLI upgrade is followed by one owner-gated
fleet refresh that lands via each project's own PR policy, and the next audit
finds zero silently-stale managed prose. Cost: ~1 design session + 1 build
card + the rewrites. **Implied Vision edit:** Introspection DoD gains "…and
accepted improvements propagate to every project that carries the artifact."

### E — Cockpit rationalization (filler)

**Thesis.** Spend nothing here except deletions and one honest decision; the
market is commoditizing this layer for free. **Market position:** native
Remote Control / Agent View now cover the single-session phone window; you
already have the TUI-over-SSH cockpit that won your real workflow but still
carry web-launch ambitions and five dead commands; therefore these items.
**Roadmap:** 1. Decide the Dashboard DoD rescope (routed question) — draft:
"fleet state and launch/resume via the TUI from any device incl. phone; the
web app is a read-mostly viewer; native session windows are adopted, not
competed with." 2. Prune the six dead commands (decided at refinement, likely
via branch C's loop). 3. `tui-backlog-refine-and-order` +
`tui-toggle-card-into-scheduler` (existing, Gated) — keep gated; they ride on
C's outcomes, not this branch. **Converged when:** the rescoped DoD is written
and the dead surface is gone. Cost: decisions + removals only. **Implied
Vision edit:** the Dashboard DoD rescope above; Accounts & isolation gets its
"(done 2026-07-20 — maintenance)" marker — both are owner convergence calls
this receipt only drafts.

## 5. Speculative branches

### S1 — BI-work continuity profile (explore; re-tests an implicit boundary)

**Gap named:** Horus assumes the product lives in a git repo and the agent
rides a coding CLI — but the actual games (Fabric workspaces, semantic models,
Power BI assets, deployment environments) keep load-bearing state *outside*
git. The boundary "repo-local is the source of truth" is a hypothesis fresh
usage will test. **Idea:** a continuity profile for data/BI projects — what of
workspace/deployment state the PRD must mirror for a fresh session to resume
BI work honestly. **Cheapest PoC:** zero new machinery — during branch B's
fabric probe, log every moment where resume failed because truth lived outside
git; ≥3 real instances ⇒ shape a card from the log. **Fits intent:** it *is*
the intent. **Risk:** scope-creep toward a BI platform tool; the profile must
stay a continuity convention, never an integration.

### S2 — Fleet recall plane (park; carried from prior tree's X1)

**Gap named:** 105 archived cards, a growing receipts shelf, and a fleet of
PRDs exceed any context window; grep is the only recall. The scan adds new
evidence: cognee-class engines are built for exactly this and integrate with
the Claude Agent SDK — compose, never build. **Cheapest PoC:** one-shot index
of this repo's `.horus/` with a memory engine; ask five real questions a
session actually had this week; compare against grep. **Why park:** no session
has yet *failed* for lack of recall — run the PoC only when one does. Re-tests
the "no runtime services" posture, so the verdict is owner-level.

## 6. Existing-backlog dispositions (nothing inherited silently)

| Cards | Disposition |
| --- | --- |
| `x6-continuity-contract-declaration`, `x6-workflow-alternatives-refresh` | Branch A, items 1–2 |
| `x6-fabric-contract-probe`, `explore-converge-lifecycle` | Branch B, items 1 and 4 |
| `verify-guidance-long-running-services`, `autotest-e2e-away-mode-drill`, X3 close-out umbrella, `telegram-group-project-topics`, `warm-supervised-worker-poc`, `remote-open-model-worker-probe` | Branch C |
| `skill-drift-surfacing-and-refresh`, `tui-fleet-artifact-refresh` | Branch D, items 2–3 |
| `tui-backlog-refine-and-order`, `tui-toggle-card-into-scheduler` | Branch E item 3 — stay Gated on C |
| `merge-release-owner-gate`, `dispatch-receipt-seam` | **Not branch-bound** — control-plane hardening, Shaping, scheduled by owner priority independent of direction (push-back considered and rejected: both guard the loop C feeds, reason stands) |
| X4 umbrella + 4 held children + `x4-pi-harness-via-proxy` | **Park** — reconfirm the 2026-07-18 hold; Pi child stays Gated on the X5 review as written |
| X5 umbrella + 6 children | **Park with a deadline** — the routed keep-or-drop goes to the owner at refinement; recommendation: archive the branch with reactivation triggers in-card (deferred-and-untouched two cycles running is a silent commitment) |
| `product-naming` | Park until direction settles (unchanged from prior tree); the scan's positioning line feeds it when it wakes |
| `account-settings-sync`, `project-workflow-overrides`, `scoped-machine-requirements`, `codex-usage-window-semantics`, `deferred-supervision-completion-receipt`, `fresh-vs-resume-context-split`, `worker-progress-heartbeat`, `openrouter-provider-support` | **Defer unchanged** — each is correctly evidence-gated in-card; no branch invalidates its trigger |
| Prior tree's X2 (owner daily brief) | Park unchanged — still brushes the continuous-monitoring out-of-scope line |

## 7. Recommendation, held loosely

**B primary**: the intent is own-use, the engine's only unproven claims are
usage claims, and every other branch's value compounds through B's evidence
(S1 rides inside it for free). **A and C secondary**: A is two cheap sessions
that make B's probe measurable; C turns refinement output into away-time
throughput — run C's refinement step regardless, since the chain ends there
anyway. **D secondary but partially in-flight** (the skill rewrites are
already owner-committed; the design session can wait for a quiet slot). **E
filler** — decisions and deletions only. **X4/X5/X2 park**, with X5 getting an
explicit keep-or-drop at refinement rather than another quiet cycle. The owner
reorders freely.

## Owner verdict at the gate (2026-07-20)

The owner reordered: **C primary** — and widened: if this repo lacks enough
genuinely-ready autonomous work, source it from low-ceremony fleet projects
(`agentic-gym-coach`, `agentic-travel-guide` named) as well-defined-task
suppliers for the end-to-end automation test. **B deferred until after the
owner's upcoming trip** — the BI projects demand the most personal input of
anything in the fleet, so they are explicitly not the pre-trip focus. **A /
X6 demoted to what it was built as**: a skills test introduced today, not a
priority path — its subjectivity is the reason. E's deletions feed C. Owner
also volunteered candidate task families for autonomous testing in this repo
(TUI improvements, usage analytics, TUI visuals for backlog/vision analysis,
surfacing pathfinder receipts beyond bare .md files, skills mined from
repeatedly-asked owner questions, cross-project skill+CLI requirement
tracking) and invited agent-found candidates — these go to `scope-cards`.

**Calibration feedback for the roadmap-branches skill text:** sections 1–2
read as repetitive with the product-audit receipt — the tree should *cite*
the audit's standings table and add only the life-stage judgment and position
line, never restate facet detail. And: owner metaphors (e.g. "engine/games")
are examples to test against, not canon to echo — reuse only where the load
genuinely fits.
