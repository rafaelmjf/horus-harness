# Roadmap branches: deepen-own-use re-baseline — 2026-07-17 (convergence-test run)

Intent: **deepen-own-use** (audience = the owner; build-vs-adopt per capability).
Inputs: pinned position brief (2026-07-17), market receipt
`.horus/research/2026-07-17-repo-local-po-rebaseline.md` (reused, owner-approved).

> **Convergence-test integrity note.** This run deliberately did NOT read the held-out
> receipt `2026-07-17-pathfinder-branch-tree.md`. However, the PRD frontmatter's
> `next_action` field (read to start the session) contains a one-line spoiler naming
> that tree's branch labels (agent-neutrality / PO-loop proof / external-priors
> rescope / fleet-knowledge-plane). The branch *contents, roadmaps, and push-backs*
> below are independently derived from the brief + cards + market receipt, but branch
> *selection* cannot be considered fully blind. Weigh the comparison accordingly.

## 1. Where we are

Horus has, in ten days of dogfooding, shipped its way to near-done on most of what it
first set out to be. **Continuity core** is *converged as written*: a fresh session
resumes the exact next step from durable state alone, fetch-first, with closure gates
and a required PR freshness check that have survived real incidents. The three open
cards are one fresh incident-backed correctness gap (two parallel sessions writing one
continuity, PR #287) and two deliberately evidence-gated deferrals (workflow overrides,
scoped requirements) waiting for a real content project to onboard. The caveat: the
facet's definition of done says "durable state," and the market evidence below argues
the *distinctive* half of that DoD — agent-neutrality, resume across Claude AND Codex —
is understated in it.

**Dashboard / cockpit** and **Accounts & isolation** are *steady-state*: the owner
launches and resumes any project from web, phone, or terminal TUI, and every account
runs isolated by default with corruption guarded at the CLI. Each facet holds exactly
one open card, both toil-reduction, both incident-backed (projection drift observed
twice; settings drift bit live on 2026-07-17). **Introspection & self-improvement** is
*converged with zero open cards* — the audit/retrospective suite exists and has been
used for real verdicts. **Distribution** is *steady-state for own use*: v0.0.59 on
PyPI, three-OS smoke, hosted dashboard current; its two cards are explicitly pinned to
a future external-distribution milestone or already demoted to the instruction rung.

**Delegation calibration** is *built-but-unproven*: the measured-datum spine, dispatch
consent envelopes, and honest cost accounting all exist, but five open cards are mostly
deferrals waiting for a real campaign to show whether the remaining machinery (stall
timers, supervision taxonomy, window semantics) earns its keep — and one confirmed bug
(a stale datum that permanently confounds usage attribution) undermines the evidence
the whole facet is supposed to produce. **PO lifecycle** is the *active frontier*: the
divergence→convergence machinery (facets, read-out, market-scan, this very factored
pathfinder flow) shipped in the last 48 hours and has been exercised only on Horus
itself.

**Overall position in one line:** a maintenance-menu backlog (no high-priority card
anywhere) on top of five near-done facets — the project's real open question is not
any card but which *driving thread* comes next, and the two candidates the position
itself nominates are proving the just-built PO loop and deepening what no native agent
can do (neutrality, fleet).

## 2. Where the market is

Distilled from `2026-07-17-repo-local-po-rebaseline.md`.

**The landscape in shells.** Innermost: every agent CLI now ships repo-local markdown
memory natively (CLAUDE.md + auto-MEMORY.md + subagent memory as of Feb '26;
.clinerules/memory-bank on the Cline side) — agent-locked, single-repo. Next shell:
per-feature spec pipelines (GitHub Spec-Kit, claude-task-master) that decompose one
PRD into tasks but hold no living project state between features. Outer shell: memory
*infrastructure* (mem0-style MCP servers) — persistence plumbing, not a planning
plane. Nobody in any shell has a cross-project fleet surface.

**One verdict: YELLOW.** The memory primitive is table stakes — but no single
competitor covers the triad Horus actually stakes: agent-NEUTRAL continuity that
resumes the exact next step, a cross-project fleet cockpit, and a living
divergence→convergence roadmap ritual.

**Risks.** (1) Native subagent memory is accelerating — anything Horus builds that is
"better memory" is on a collision course with the platforms; the moat is only what
they structurally won't build (neutrality across vendors, fleet, PO ritual). (2) The
receipt's open interop question cuts for own-use too: if Horus doesn't *read* the
native memories, the owner maintains two stores by hand. (3) n=1 audience means every
build decision must clear the build-vs-adopt bar, not the differentiation bar.

## 3. The tree

```
Horus 2026-07-17 — five facets near-done for n=1; frontier = PO loop just shipped;
moat per market = the triad natives won't build (neutral, fleet, PO ritual).
│
├── A  Agent-neutrality deepening ......... Continuity core (rescope)  [primary]
├── B  PO-loop proof-of-value ............. PO lifecycle               [secondary]
├── C  Calibration: prove-or-prune ........ Delegation calibration     [secondary]
├── D  Fleet-toil polish .................. Dashboard + Accounts       [filler]
├── X1 Fleet knowledge plane .............. (no facet — speculative)   [explore-PoC]
└── X2 Owner daily brief .................. (no facet — speculative)   [park]
```

## 4. The branches

### Branch A — Agent-neutrality deepening (primary)

**Thesis.** The owner runs Claude Code and Codex daily across one fleet. Native memory
is agent-locked by construction and getting better fast — so under deepen-own-use, the
build-vs-adopt answer is: adopt native memory where it exists, and build only the
neutral layer above it that lets *either* agent pick up *exactly* where the other
left off. That is also the single capability whose absence the owner pays for most
often: every cross-agent handoff today rides on PRD prose being good enough.

**Market position.** Repo-local markdown memory exists already (native
CLAUDE.md/MEMORY.md, .clinerules) but is locked to one agent and blind to siblings;
Horus already has vendor-neutral `.horus/` + dual projections + closure gates but
still misses a *proven* cross-agent resume (no deterministic parity check) and
*reads none* of the native stores it sits above; therefore these items.

**Numbered roadmap.**
1. **`parallel-session-continuity-reconciliation`** (existing card, converge,
   medium) — two concurrent writers on one continuity is the sharpest current
   correctness gap in the resume story; incident-backed (PR #287). Why first: it is
   fully specified, cheap (extend existing pending-delivery detection), and every
   later cross-agent scenario multiplies the two-writers risk. Weak point: sibling-PR
   detection needs the GitHub remote — define offline behavior explicitly. Non-goal:
   no locking.
2. **Cross-agent resume parity probe** (new) — a deterministic check that a project's
   resume surface renders equivalently for Claude and Codex: same next step, same
   pinned brief, same gates, from `.horus/` alone. How: a `horus`-level parity
   verification (projection contents + resume preflight output compared across both
   agents' surfaces) plus one *live* round-trip — a real small task started in
   Claude, closed at a boundary, resumed and finished in Codex, then the reverse.
   Findings become their own cards (second-order). Weak point: "equivalent" needs a
   concrete definition — start with the deterministic fields (frontmatter, cards,
   managed block), not prose quality.
3. **[explore] Native-memory interop** (new, from receipt FAQ Q4) — read/adopt
   CLAUDE.md, auto-MEMORY.md, AGENTS.md (and later .clinerules) INTO the position
   Horus presents at resume, so the owner never hand-copies context between stores.
   Cheapest first step: `horus resume` lists native memory files present in the repo
   + account dir with staleness, as *inputs the session should read* — no ingestion,
   no second store. Weak point: auto-MEMORY.md is account-local and machine-local;
   scope the first pass to repo-committed files. Non-goal: never write native stores.
4. **Rescope "Continuity core" DoD** — lead with agent-neutrality: "a fresh session
   *of either agent* resumes the exact next step…" (draft text in Vision edits
   below). Last, because the rescope should follow the parity evidence, not precede it.

**Convergence criterion.** One real task has round-tripped Claude→Codex and
Codex→Claude with no re-derivation and no manual context copying; parallel-delivery
signal shipped; native-memory files surfaced at resume. Rough cost: 2–3 small PRs +
one live round-trip session + one explore PoC.

**Implied Vision edits.** Rescope facet **Continuity core** DoD to: "A fresh agent
session — Claude or Codex — resumes the exact next step from durable state alone,
fetch-first, across machines and across agents, with sibling deliveries impossible to
miss." No adds/retires.

### Branch B — PO-loop proof-of-value (secondary)

**Thesis.** The PO-lifecycle machinery is 48 hours old and has only ever run on the
repo that built it. Under deepen-own-use, the cheapest high-information move is to
*use* it before building more of it: run the loop on other fleet projects and observe
whether receipts actually change what ships. This is also the intent's own
anti-ceremony guard — if the ritual doesn't alter decisions on a second repo, that is
a retire signal worth having early.

**Market position.** Per-feature spec pipelines exist already (Spec-Kit, task-master)
but hold no living project direction; Horus already has the full
divergence→convergence toolchain but still misses any evidence it works off its home
repo; therefore these items.

**Numbered roadmap.**
1. **Run pathfinder on 2 non-Horus fleet projects** (new, session work not code) —
   pick the two most active other repos; each run produces a receipt + owner-gated
   cards via the normal flow. Success data: did the owner accept cards they wouldn't
   have written anyway? Findings become their own cards.
2. **Receipt→decision trace** (new, cheap) — after each run, one line in the receipt
   footer recording what the owner actually did (branch picked, cards written,
   anything retired). How: an owner-filled section, no tooling. Weak point: honesty
   depends on filling it at pick time, not later.
3. **`explore-converge-lifecycle`** (existing card, medium) — the deferred
   usage-ripeness flag ("explore card with usage but not yet converged"). Second-order:
   it needs a per-card usage signal that item 1's runs should reveal the shape of;
   do not build the signal speculatively.

**Convergence criterion.** Two non-Horus pathfinder runs completed with decision
traces; the loop either changed a real decision on ≥1 repo (keep, promote ripeness
work) or didn't (file the retire/demote verdict via product-audit). Rough cost:
mostly two owner-gated sessions; ≤1 small PR.

**Implied Vision edits.** None yet — this branch *tests* the PO-lifecycle facet's DoD
("the forward loop runs repo-local") rather than changing it. If both runs prove out,
the facet's frontier note moves from "discovery + convergence are the open gap" to
"proven on N repos."

### Branch C — Delegation calibration: prove-or-prune (secondary)

**Thesis.** Five open cards — the most of any facet — yet almost all are deferrals
waiting on evidence, and the facet's core promise (honest, measured delegation data)
is actively undermined by one known bug. Under deepen-own-use the branch is not "build
the taxonomy out"; it is: generate the one piece of evidence the owner explicitly
wants (can cheap local models take low-risk work?), fix the bug that poisons the
data, and then prune what real campaigns haven't justified.

**Market position.** Native CLIs are shipping subagent orchestration and usage
surfaces already, but they will never measure *across vendors and accounts* or price
the owner's actual local alternatives; Horus already has the datum spine and consent
envelopes but still misses any datum for non-Claude/Codex workers and carries a
confound bug; therefore these items.

**Numbered roadmap.**
1. **`remote-open-model-worker-probe`** (existing card, medium) — the only card in
   the facet that *generates new evidence* rather than refining plumbing. The card is
   already fully scoped with envelope gates. Weak point: discovery-first (no assumed
   runner/protocol); keep to the disposable-fixture boundary.
2. **`stale-datum-usage-overlap-reconciliation`** (existing card, medium, bug) —
   evidence integrity: one stale datum currently confounds every later same-account
   reading forever. Fix before the probe's datums land, or the probe's own evidence
   inherits the confound.
3. **Prune pass** (new, judgment not code) — with probe + one more real campaign in
   hand, apply prove-or-prune to the three deferred cards:
   `codex-usage-window-semantics` (park until upstream stabilizes — unchanged),
   `deferred-supervision-completion-receipt` remainder and
   `worker-progress-heartbeat` remainder (each ships only if the campaigns showed the
   need; otherwise retire with the kernel-already-shipped note). Findings become
   archive verdicts, not new cards.

**Convergence criterion.** Per-model probe conclusions recorded as datums/priors; the
confound bug closed; every remaining calibration card either evidence-justified or
explicitly parked/retired. Rough cost: one supervised probe session + one bug PR +
one judgment pass.

**Implied Vision edits.** None. (If the probe proves a real open-model dividend, a
follow-up may extend the facet's DoD wording from "model tier" to "model tier
including local/open workers" — promote only on evidence.)

### Branch D — Fleet-toil polish (filler)

**Thesis.** Two incident-backed toil sinks: bundled-skill/instruction projections
drift silently across the fleet (bit twice; resync is manual per-repo), and
per-account settings drift silently across isolated dirs (bit 2026-07-17). Neither
changes direction; both directly repay owner hours. Under deepen-own-use, filler
work is legitimate exactly when it is this concrete.

**Market position.** Nothing external addresses either (both are Horus-created
surfaces — isolation and projections are our own inventions); Horus already has
read-only drift *visibility* (Projection Sync, doctor flags) but still misses the
confirmed *apply* half; therefore these items.

**Numbered roadmap.**
1. **`tui-fleet-artifact-refresh`** (existing card, medium) — Projection Sync grows
   an owner-confirmed refresh-one/refresh-all with dry-run plan, per-target safety
   skips, and remote-default verification. Already exhaustively specified in the
   card. Weak point: it is the largest single card in the backlog — a phased
   execution plan is likely warranted at pick-up time.
2. **`account-settings-sync`** (existing card, low) — whitelist-key settings
   reconcile across `~/.horus/accounts/*` with diff-first apply + doctor drift flag.
   Small, already scoped.

**Convergence criterion.** One command (or TUI action) each brings projections and
account settings fleet-current with confirmation; drift warnings go quiet on a clean
machine. Rough cost: one chunky PR campaign + one small PR.

**Implied Vision edits.** None — pure convergence toward the existing Dashboard and
Accounts DoDs.

## 5. Speculative branches

### X1 — Fleet knowledge plane (explore-PoC)

**The gap.** Continuity is strictly per-repo, but the owner's hardest-won knowledge
is fleet-level: the tmux-isolation incident, the uv-install trap, the config-dir
corruption rule were each learned in ONE repo yet apply to every project on every
machine. Today they travel only via this repo's Rules section or the agent's
account-local memory — both invisible to a session in another project.
**The idea.** A read-mostly fleet-level knowledge surface — e.g. `horus rules
--fleet` aggregating the `## Rules` sections of all registered projects' PRDs
(fetch-first, labeled by source repo), surfaced at resume/dispatch so any session can
consult cross-project lessons without a second store. **Cheapest PoC:** a read-only
CLI verb that walks registered projects' cached PRDs and prints a deduplicated,
source-attributed rules digest; zero new files written. **Why it fits the intent:**
the owner *is* the fleet; every repeated incident across repos is direct own-use
cost. **The risk:** it drifts into a curated second memory store — exactly what the
"self-documentation is never curated" rule forbids; the PoC must stay a projection of
existing per-repo Rules, never an editable aggregate. (Contamination note: the
frontmatter spoiler named a similar direction; the derivation above is from this
run's position analysis, but discount novelty accordingly.)

### X2 — Owner daily brief (park)

**The gap.** The cockpit shows fleet *state*, but the owner still assembles the
day's agenda by scanning: which project has pending continuity, which usage window
reset, which worker finished overnight, which next_action is stalest. **The idea.**
One `horus brief` that ranks the fleet into a short owner agenda (pending deliveries
first, then stale continuity, then expiring account capacity), reusing
`resume --preflight --fleet` data only. **Cheapest PoC:** a sort-and-render pass over
the existing preflight digest. **Why it fits the intent:** it is the owner's actual
first question every morning. **The risk:** it is one ranking heuristic away from the
"no output recommends or selects" rule and one cron away from the out-of-scope
continuous-monitoring category — hence park until the fleet is big enough that
scanning measurably hurts.

## 6. Recommendation, held loosely

**Primary: A.** Agent-neutrality is simultaneously the market's clearest structural
moat and the owner's most-paid daily cost, and its first item is an already-scoped
incident-backed card — the branch starts converging this week without new research.
**Secondary: B** — it is nearly free (session work), guards against building PO
ceremony, and its evidence compounds the value of every other branch's future
pathfinder runs. **Secondary: C** — the probe is the one item the owner has
explicitly asked for; sequence the confound bugfix before it so the evidence lands
clean. **Filler: D** — pick up either card when a session wants bounded, well-specified
work between campaigns. **X1** deserves its zero-write PoC in some idle session;
**X2** stays parked. Existing-card push-backs embedded above, summarized:
`init-scaffolds-project-ci` → **retire candidate** (write the one onboarding-skill
guidance line it was demoted to, then archive); `product-naming`,
`codex-usage-window-semantics` → **park unchanged** (correctly evidence-gated);
`deferred-supervision-completion-receipt` + `worker-progress-heartbeat` remainders →
**defer pending Branch C's campaigns**; `project-workflow-overrides` +
`scoped-machine-requirements` → **defer pending a real onboarded content project**
(no branch manufactures that evidence).

## Post-run comparison outcome (added after reading the held-out receipt)

**Converged independently:** the A/B/D core branches (same primaries, same
load-bearing items — cross-agent parity, native-memory interop as explore,
DoD rescope after evidence), the push-back discipline, and the no-merged-tree
format. **Owner correction:** X1's fleet-knowledge-plane label was frontmatter-
contaminated and the held-out X3-adjacent direction was owner-steered in the other
session — neither counts as convergence evidence. **Diverged:** Branch C
(prove-or-prune here vs external-priors-first there) — root cause: the owner
push-back that rescoped C lived only in the held-out receipt, never in the
affected cards' Reviews. Process finding adopted: owner verdicts that must bind
future planning belong in card Reviews, not only in receipts. **Both runs
missed** scheduled autonomous dispatch (the owner's live strongest direction)
because it sat behind an out-of-scope declaration → roadmap-branches v2 now
requires speculative branches to re-test the out-of-scope list. Disposition:
scoping went to X3 (PR #289 cluster, promoted); this tree's A-imports (parity
protocol w/ pre-registered suspects, distillation interop mechanic) and the
external-priors-calibration idea remain unscoped candidates for the next
convergence pass.
