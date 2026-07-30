# Wildcard — branch-first divergence (2026-07-31)

Five proposals, ranked, all at **branch/feature level**. Owner-invoked run 3, after
runs 1-2 were judged to have produced only skill/process adjustments (see the
`wildcard` card for that finding). Skills, process and hygiene were excluded from
this run by construction; frames were pinned to the four `vision-branch-*` umbrellas.

**Nothing here is decided.** These are proposals for the owner to dispose of.

**Grounding:** the four branch umbrellas and their cards (current), plus the
2026-07-20 pathfinder bundle — which was already **10 days and six releases old** at
run time. The owner declined a refresh first. Treat standing claims as sourced from
the umbrellas/cards, not the stale position brief.

| # | Do this | Advances | Kind | Effort |
|---|---|---|---|---|
| 1 | Arm and run the away-mode drill — its deferral date has passed | X3 (archives the branch) | probe | multi-account session |
| 2 | Settle the three decisions blocking the continuity-contract declaration | X6 child 1 + **closes Continuity core** | decision | one exchange |
| 3 | Define the fabric probe's evidence bar while the probe still runs | X6 child 3 | decision | one exchange |
| 4 | Measure whether the proxy statusline leak persists | X4 (unblocks disposition) | evidence read | ~20 min |
| 5 | Redraft `x4-pi-harness-via-proxy` into something launchable | X4 stage 1.1 | decision | one session |

## 1 — Arm and run the away-mode drill

- **Do this:** find the one remaining always-green leg, arm the drill, run it end to end.
- **Change if accepted:** `autotest-e2e-away-mode-drill` leaves `readiness: deferred` —
  its reason reads *"Deferred until after 2026-07-29"* and **that date passed with
  nothing re-classifying it**. A passing run archives
  `vision-branch-x3-scheduling-and-autonomous-execution`, whose Current state says the
  drill is its *only* closure gate. The two reserved legs
  (`verify-guidance-long-running-services`, `audit-advisory-interval`) get spent.
- **Why:** X3 is the one branch already promoted to a facet, and the 2026-07-20 audit
  rates Autonomous dispatch *"machinery done, needs eligible work"* — this is that work.
- **Not included:** `warm-supervised-worker-poc`, which the umbrella says does not hold
  X3 open.
- **Risk / honest blocker:** the roster has **one** confirmed always-green leg plus one
  reserved; Reviews say *"still need ~2 more small always-green legs."* So the real
  first step is a leg search, not the drill. Spends real multi-account weekly capacity —
  precisely what the 2026-07-21 deferral was waiting on.

## 2 — Settle the three decisions blocking the continuity-contract declaration

- **Do this:** decide where the contract is declared (docs vs code constants vs README),
  the exact field list per tier, and how tier names surface to users.
- **Change if accepted:** `x6-continuity-contract-declaration` leaves `shaping` (blocked
  on exactly those three) and becomes writable; the implicit contract behind
  `resolve_focus`, the backlog parser and `closure` becomes declared, with named session
  and dispatch tiers.
- **Why:** two at once — X6's child #1 against that branch's headline gap (*"the contract
  is implicit, not declared"*), and the 2026-07-20 audit's routing table lists
  **"Contract declaration closes Continuity core"**, making it the single move that
  finishes a facet's DoD. Nothing has acted on that routing in ten days.
- **Not included:** the workflow-swap experiment (X6 child 4), which the umbrella says
  must not be pre-invented.
- **Risk:** declaring a contract makes it a promise; over-declaring freezes internals
  still worth moving.

## 3 — Define the fabric probe's evidence bar while it still runs

- **Do this:** decide what observations count, where findings land, what triggers the
  tier verdict — now, not after.
- **Change if accepted:** `x6-fabric-contract-probe` gains a written evidence bar and a
  landing place, so production BI use deposits contract-sufficiency findings instead of
  passing unrecorded.
- **Why:** the branch's only *live* evidence source (card: probe is live, owner using
  fabric in production) while X6's gap list calls real non-SWE evidence *"only
  starting."* A wasting asset — every day without a bar is evidence not captured.
- **Not included:** no instrumentation; fabric keeps being used exactly as now.
- **Risk:** too tight a bar turns production use into reporting overhead and the owner
  stops feeding it.

## 4 — Measure whether the proxy statusline leak persists

- **Do this:** check whether a clean Claude Code session still shows the broken
  statusline, and whether untoggling the proxy reverted it.
- **Change if accepted:** answers an open question with a **pre-decided consequence** —
  the X4 umbrella says if it does not revert, *"this is grounds to revert the proxy
  implementation (v0.0.65) entirely."* X4 Reviews gain a dated resolution; v0.0.65's
  fate stops hanging.
- **Why:** one of three named defects from the 2026-07-18 net-negative trial, and the
  cheapest to settle. Blocks a disposition, not a build.
- **Not included:** the slowness finding and the ~20%-weekly-capacity finding, which
  need a real trial.
- **Risk:** if the answer is "still leaking", the routed consequence is a revert — and
  reverts are the convergence step's call, not this proposal's.

## 5 — Redraft `x4-pi-harness-via-proxy` into something launchable

- **Do this:** answer what PI is as a launchable harness, how it takes a base-URL plus
  credential, and whether it is a first-class adapter or a thinner launch profile.
- **Change if accepted:** the card moves from `shaping` toward `ready`; its Notes
  already ask for the plan to be redrafted in a fresh session, and its gate was narrowed
  2026-07-28 so the **attended** probe is unblocked.
- **Why:** the only X4 work the owner's 2026-07-18 verdict allows to proceed.
- **Not included:** anything unattended stays gated on the X5 review.
- **Risk:** X4's premise took a net-negative verdict; a design session on its one
  surviving child may be good money after bad — idea 4 is the cheaper read on whether
  the branch deserves it.

## Deliberately excluded — X5, in full

Its six children are real feature work and the incident that spawned it was real (a
model crashed the workstation; recovery via tty3). But the branch is deferred under an
owner-confirmed **undated** hold and PRD says explicitly *"do not re-raise it as a
finding."* Proposing its children would be re-raising it. Recorded so a later reader
sees it was considered and excluded deliberately, not overlooked.
