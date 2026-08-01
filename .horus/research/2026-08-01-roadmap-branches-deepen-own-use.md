# Roadmap branches: deepen-own-use re-baseline — 2026-08-01 (v8 run)

Intent: **deepen-own-use** (audience = the owner; build-vs-adopt per capability).
Inputs: audit `.horus/audits/2026-07-31-product.md`, market receipt
`.horus/research/2026-07-31-market-scan-build-vs-adopt.md` — the same pair pinned for
all four prior runs, so any difference here is the skill.

> **Run provenance.** This is the fifth attempt at this tree. Four were rejected:
> v4 assembled branches from backlog cards (grooming); v5/v6 dropped the facet walk and
> produced only exploration; v7 over-corrected into one-branch-per-facet and padded eight
> branches over eight facets. The skill was cut back to v8 before this run
> (`horus/skills.py`, PR #480) after tracing the regression to a 2026-07-20 calibration
> that turned section 1 from narrative into a citation — which is where the facet walk
> had been living. Evidence measured during the v7 run is carried forward here rather
> than re-derived, and is marked where it appears.

## 1. Where we are

Horus is eight facets deep and most of them are finished. That is the honest headline,
and it is the thing every recent tree has struggled to say plainly, because a backlog of
75 open cards looks like a project with 75 open problems rather than one with two.

**Continuity core** is *converged as written* and quietly standing on a shifted premise.
Sixty-four sessions have resumed from durable state since the stamp; the resume path,
the fetch-first discipline and the closure gates have all survived real incidents. What
changed underneath is the justification: continuity was argued as context economy, and
the last window spent eleven PRs cutting committed continuity from 276,884 to about
71,000 characters — good engineering aimed at a cost that has largely evaporated now that
Opus 5 ships a million tokens and the whole PRD is rounding error against it. The thesis
that survives is durable cross-session, cross-vendor state, and exactly one leg of it has
never been tested: the DoD says "across machines" and nobody has ever checked.

**Dashboard / cockpit** is the *active frontier and the only facet that is both used
every day and actively wrong*. The market receipt calls the multi-agent × multi-account ×
multi-project cockpit the one thing nothing else in the landscape occupies — and that
cockpit currently reports most of the owner's completed work as failure. Measured live
from the registry this session: 73 of 246 rows all-time are `('failed','stopped')`, which
is 88% of every `failed` row ever written, and in the last thirty sessions it is twenty —
**67%**. The audit put it at 56% over a 26-session window; it has got worse since, because
the newest host closes sessions through the same path. The cause is not a stray line:
`horus/registry.py:29` defines `TERMINAL = {"exited","failed","orphaned","stale"}` with no
word meaning *the owner closed it*, so `stop_session` (`terminal_sessions.py:375`) and
`reap_orphans` (line 554) both have nowhere honest to land. Meanwhile the host that runs
those sessions already publishes the truth: `herdr api snapshot`, queried this session,
returns per pane the agent, a live `agent_status`, the project, a stable `pane_id` Horus
already stores, a change counter, and the literal task title of what the session is doing
right now.

Three facets need no branch at all, and saying so is part of the read-out rather than an
omission from it. **Accounts & isolation** is *converged*: both accounts are in daily use
(claude 189 / codex 50 of 246 sessions), isolation is default, per-account usage is
visible, and the audit finds no drift — yet it still carries eight open cards, which is
maintenance on a finished thing rather than a direction. **Introspection &
self-improvement** is the *strongest facet this window* and is working exactly as
designed: five audit receipts, the budgets that replaced a structurally blind line cap,
and a `horus close --check` gate that has been neither skipped nor rubber-stamped. Its
one blind spot is real but small — it fires when the owner fires it, which is how a skill
could be revised three times in a day and still be wrong — and that is a note for the
convergence pass, not a roadmap. **Distribution** is *steady-state but stalled*: 22
commits sit unreleased on v0.0.79, and the stall is now self-demonstrating, because the
`horus` binary on this machine still printed the retired 250-line PRD cap when I ran
`horus consolidate` at the start of this session. The character-budget fix that replaced
that cap is sitting in the unreleased commits. That is an overdue action and the owner's
own decision to take, not a direction to choose between.

**Delegation calibration** and **Autonomous dispatch** are the same story told twice, and
the story is *built-but-never-exercised*. Calibration exists to choose between doing work
here and handing it to another agent, and in the window the audit covers that choice was
made zero times, while six cards continue to refine the instrumentation. Autonomous
dispatch is the most-carded facet in the project at eleven, with complete machinery,
three drill envelopes, zero armed timers (checked this session) and zero eligible cards.
Between them they hold seventeen open cards and have produced no evidence. The registry
does hold one hard fact about how dispatched work behaves, and nothing has ever read it:
of 35 sessions that expected a delivery, **8 never pushed a SHA — and all 8 were
worktree-isolated dispatched workers**, not one interactive session.

**PO lifecycle** is the *active frontier*, as the Vision itself says, and it is the
bottleneck on everything above. The breathing model promises that ideas diverge, get
used, and then converge — dropped, trimmed, or promoted. The divergence half runs
constantly; this receipt is the fifth instance of it in two days. **The convergence half
has never run once.** The accumulation is measurable: 75 open cards, of which 3 are ready,
26 deferred, 47 exploratory, and — measured card by card this session — **16 converging
with 12 carrying no `phase:` stamp at all**. The audit's widely-quoted "47 explore vs 27
converge" appears to have counted the unstamped twelve as converging; the real ratio is
worse, and there is a third bucket nobody is looking at.

**Overall position in one line:** five facets are finished or unexercised and need
decisions rather than work, one is stalled on a release the owner must simply take, and
the only two live questions are that the daily cockpit lies about most of its rows and
that the loop which is supposed to remove work has never removed any.

## 2. Where the market is

Distilled from `2026-07-31-market-scan-build-vs-adopt.md`.

**The landscape in shells.** Innermost: repo-local Markdown continuity is now
independently reinvented — AICTX, agent-memory and memories.sh all reached the same
design, and all three are single-project, two of them treating MCP as the primary agent
path. Next shell: the agent CLIs themselves moving up into session views, with
`claude agents` shipping rows with PR links and honest `Working`/`Needs input` states,
plus experimental Agent Teams. Outer shell: commercial memory infrastructure selling
lanes and semantic recall. **Nobody in any shell spans multiple agents, multiple
accounts, and multiple projects at once.**

**One verdict.** The differentiator has moved from *what Horus stores* to *how many
things it spans*. Repo-local continuity is table stakes and no longer an insight; the
fleet-and-accounts intersection is the entire remaining moat, and it exists because this
owner actually has that problem.

**Risks.** (1) The platform keeps absorbing upward — if `claude agents` adds multi-account
and Codex, the cockpit narrows to fleet-of-projects only. (2) herdr is a third-party
dependency at v0.7.5 with a JSON API and no stability promise Horus has verified.
(3) With n=1, every build must clear the build-vs-adopt bar, not the differentiation bar.

**One scan verdict is overridden here, as it was in the v5 receipt.** The scan says
*session host: KEEP-THIN, do not deepen*. That is a market instinct — don't rebuild
someone else's tool — applied to an own-use question, and it points the wrong way: herdr
went from zero to carrying 13 of the last 30 sessions, and the correct reading is *go
further into the host and take less onto Horus*, which is the opposite of deepening
Horus.

## 3. The tree

```
Horus v0.0.79 (+22 unreleased) — five facets finished or unexercised, one stalled
on a release; the live questions are a cockpit that lies and a loop that never prunes.
│
├── A  Cockpit tells the truth ......... Dashboard / cockpit                  [primary]
├── B  The loop's missing half ......... PO lifecycle                         [primary]
├── C  Prove-or-prune the unused ....... Delegation calib. + Autonomous disp. [secondary]
├── D  Continuity's real thesis ........ Continuity core (rescope)            [filler]
├── X1 Host-native state for Codex ..... (no facet — speculative)             [cheap, gates A]
├── X2 Cross-machine fleet READ ........ (no facet — speculative)             [park]
└── X3 Mine the registry ............... (no facet — RAN, converged)          [fold into C]
```

Four branches over eight facets. Accounts & isolation, Introspection and Distribution
get none, for the reasons given in section 1 — two are converged and the third needs a
release, not a direction. C deliberately spans two facets, because they have one problem
between them.

## 4. The branches

### Branch A — Cockpit tells the truth (primary)

**Thesis.** You open the cockpit and most of what you closed yesterday is sitting there
in red, marked failed. That is 67% of your last thirty sessions being reported as
failures when you simply closed them normally — on the surface you use every day, and the
one surface the market says nothing else in the landscape offers. Afterwards, closed
sessions look closed, and each running session shows in plain words what it is doing
right now, because that fact comes from the program hosting it rather than from Horus
guessing at a process table. Under deepen-own-use this outranks everything: it is the
only facet that is simultaneously the differentiator, in daily use, and wrong.

**Market position.** Native session lists exist already — `claude agents` shows honest
states, and herdr publishes live agent state per pane — but they miss Horus's projects,
accounts, Codex coverage and delivery tracking; Horus already has the registry, the fleet
view and delivery tracking but still misses truthful live state, which is precisely the
part its own host gives away for free; therefore these items.

**Numbered roadmap.**
1. **Add the missing terminal status** (new) — the root cause, and it repairs every host
   path at once rather than per-host, which is what keeps a critical function from
   depending on one session host. How: extend `TERMINAL` with an owner-initiated
   `stopped` state, migrate the 73 existing rows (unambiguously identifiable by
   `termination_reason`), and update TUI/dashboard colouring. Weak point: `TERMINAL`
   membership is tested at `registry.py:317`, `:457` and `:498` — the new status must be
   terminal in all of them or reaping will loop. Non-goal: a general status-vocabulary
   redesign.
2. **Read `herdr api snapshot` for herdr-hosted rows** (largely retires
   `session-agent-state-awareness`, existing/explore) — `agent_status` is exactly what
   that card was written to build, and the host already solved it. How: one call keyed by
   `pane_id`, which Horus already stores as `target_ref` in that exact form (`w2:p3`);
   cache on `state_change_seq` so polling stays cheap. Weak points: an absent herdr server
   must fall back to the registry and never error; v0.7.5 offers no stability promise, so
   pin the consumed fields and treat unknown shapes as absent. Non-goals: no
   screen-scraping, no polling in a paint path.
3. **Show the live task title** (new, small) — `terminal_title` is a free per-session
   "what is it doing" label Horus has no other way to produce.
4. **Give the registry a real `host` field** (new, small) — measured this session, all 246
   rows have `host: None` and the host is inferred by string-matching `target_ref`'s
   shape, which is why host-specific behaviour is awkward to write.
5. **Decide the honest DoD for "no terminal command"** (decision, not a build) — the facet
   promises launch/resume from web or phone with no terminal command; delivered reality is
   a read-mostly dashboard plus Termius SSH into the TUI, which *is* a terminal command.
   Either it is in — and needs an authority model that respects the never-mints-authority
   rule, which becomes its own card — or it is out and the DoD should stop claiming it.
   Second-order: the authority design exists only if the answer is "in".
6. **Scope the registry to the delta** (second-order) — once 1–4 land, some of what Horus
   stores is a worse copy of what the host answers. Findings become their own cards.

**Convergence criterion.** No owner-initiated close is ever displayed as a failure, and
for a hosted session every state shown is either sourced from the host that owns it or is
something only Horus knows. Rough cost: item 1 is a short PR and delivers most of the
honesty win on its own; 2–4 are one session; 5 is a decision.

**Implied Vision edits.** No facet added or retired. Sharpen **Dashboard / cockpit**'s DoD
with a truthfulness clause: *"…and every state it reports is either true by construction
or sourced from the host that owns it."* Conditionally, per item 5, drop "no terminal
command". This also extends the Vision's existing native-app-first principle from agent
CLIs to *hosts*.

### Branch B — The loop's missing half (primary)

**Thesis.** The project's central claim about how it works is that ideas diverge, get
used, then converge — dropped, trimmed, or promoted. Half of that has never happened. You
have run divergence five times in two days and convergence zero times ever, and the result
is a backlog where 75 cards are open, only 3 are ready, and 26 are parked with no dated
trigger. Afterwards the backlog is smaller, every deferred card has either a date or a
retirement, and you can tell what is actually next without reading 75 files. Under
deepen-own-use this is the bottleneck: three of the four branches here end by routing
candidates to a convergence pass that does not exist, so without it this receipt becomes
another document that adds and never subtracts — which is the exact pathology it is
diagnosing.

**A caution that belongs in the branch, not a footnote.** The convergence machinery was
declared shipped (`roadmap-convergence`, archived) and the pass still never ran. So the
missing thing is almost certainly not more tooling — it is a session that spends the
decisions. Building more convergence machinery before running one pass by hand would
repeat this facet's own mistake.

**Market position.** Per-feature spec pipelines exist already (Spec-Kit, task-master) and
the continuity tools store state, but none of them prunes — nobody ships a living
convergence lifecycle; Horus already has the read-out, the facet stamps and the divergence
tree but still misses a single instance of a decision that removed work; therefore these
items.

**Numbered roadmap.**
1. **Run one convergence pass by hand, with this receipt as its agenda** (new, session
   work not code) — branches A, C and D all produce defer/retire candidates, which is a
   real agenda rather than a synthetic one. How: walk those candidates plus the 26
   deferred cards and give each an actual verdict — kill, rescope, or keep with a stated
   reason. Weak point: the temptation is to keep everything "just in case", which is what
   produced 26 deferrals; **a pass that removes nothing has failed and should be reported
   as such.**
2. **Resolve the 12 unstamped cards** (new, cheap) — measured this session; they are
   invisible to the explore:converge ratio this facet is judged by, which is why the
   quoted ratio was wrong.
3. **Give every deferred card a dated trigger or a retirement** (new) — over a third of
   the backlog, including the whole X5 branch under an explicitly *undated* hold. The
   audit routed this here (suggestion #3).
4. **Decide what X6's probe is now** (existing card
   `vision-branch-x6-workflow-selection-compatibility`, explore) — fabric was declared
   non-influential, so the card's premise is gone; the audit routed this here (#2).
5. **Restate the continuity thesis** (from branch D's item 1; the audit routed it here,
   #5) — a Vision edit, decided in convergence rather than in a divergence tree.
6. **Only then** consider whether `explore-converge-lifecycle` (existing, Deferred) needs
   building. Second-order by construction: the hand-run pass produces exactly the per-card
   usage signal that card is waiting on. Do not build the signal speculatively.

**Convergence criterion.** One pass has run; the open-card count is materially lower;
every deferred card has a date or a retirement; and at least one real thing was killed.
Rough cost: one focused session, and it is the highest-leverage session available.

**Implied Vision edits.** Update the PO-lifecycle frontier note from "discovery +
convergence are the open gap" to whatever the first pass proves — most likely that the gap
was never machinery but the decision session itself. No facet added or retired.

### Branch C — Prove-or-prune the built-and-unused (secondary)

**Thesis.** Two facets — delegation calibration and autonomous dispatch — hold seventeen
open cards between them, have complete machinery, and have produced no evidence at all:
zero dispatches in the audit window, zero armed timers, zero autonomous-eligible cards.
This is the largest block of speculative work in the project, and every card in it is an
argument about a decision nobody is making. Afterwards you either have one real
end-to-end run that tells you which of the seventeen were worth having, or you have a
frozen facet that stops accruing cards. Under deepen-own-use, instrumentation built ahead
of the decision it serves is the most expensive kind of unused code, because it generates
maintenance forever.

**The evidence that makes this branch sharper than it was.** The registry query run this
session (see X3) found that of 35 delivery-expecting sessions, 8 never pushed a SHA and
**all 8 were dispatched workers**. That cuts both ways and both ways matter: it justifies
the independent-verification discipline as something other than paranoia, and it means a
historical delivery rate near 77% — so "one cheap supervised run" understates the cost.

**Market position.** The native CLIs are shipping background sessions and experimental
Agent Teams already, and public benchmarks rank model tiers continuously and for free, but
none of them measures across two vendors and two paid accounts or enforces a
pre-authorized envelope; Horus already has the datum spine, the envelopes and the
worktree isolation but still misses a single completed unattended run and any external
prior to rank tiers against; therefore these items.

**Numbered roadmap.**
1. **Fold sourced external priors into the rubric** (likely
   `automated-model-roster-grounding`, existing/unstamped — verify before creating
   anything new) so it reads priors-first and own datums as the residual. Why: this is the
   correction the owner asked for on 2026-07-17 and **the only part of it never done** —
   checked card by card this session, three of the four cards that critique named are
   archived, while `external-priors-calibration`, the one card that would have implemented
   the fix, was never created. The facet did the subtraction and skipped the correction.
   Weak point: priors go stale on a model refresh, so the refresh path must be named or
   this becomes its own drift.
2. **Arm exactly one real card end-to-end** (new) — the only way to learn anything here.
   The strongest candidate is branch A item 1: bounded, one status vocabulary of blast
   radius, and a deterministic gate (tests plus a live registry check). Weak point: the
   drill's two reserved legs (`verify-guidance-long-running-services`,
   `audit-advisory-interval`) must stay reserved — the PRD explicitly forbids promoting
   something to refill the queue.
3. **Route the remaining cluster to defer/retire candidates** pending that run —
   `deferred-supervision-completion-receipt`, `worker-progress-heartbeat`,
   `dispatch-workflow-comparative-study` on the calibration side; the dispatch cards on
   the other. Argument: supervision and heartbeat instrumentation only matters once there
   is a real dispatch to supervise. Decided in branch B, not here.
4. **Findings become their own cards** (second-order) — whatever item 2's run breaks is
   the facet's next real work, and cannot be pre-scoped.

**Convergence criterion.** A tier recommendation cites external evidence; one card has
gone from armed to merged without the owner driving it; and the two facets' combined card
count went down rather than up. Rough cost: one PR for item 1, one supervised run for
item 2, one judgment pass for item 3.

**Implied Vision edits.** Rescope **Delegation calibration**'s DoD to name external priors
as the primary source and own measurements as the residual, rather than implying all
calibration is self-measured. For **Autonomous dispatch**, none yet — but if item 2's run
produces no value, a future convergence pass should ask whether the facet was promoted too
early. Recorded as a question, not a proposal.

### Branch D — Continuity's real thesis (filler)

**Thesis.** Continuity was built and justified as a way to stop paying for context, and
that reason has quietly stopped being true — a million-token model makes the entire PRD
rounding error, right after eleven PRs were spent cutting it in half. Meanwhile the reason
that *is* still true, that this state survives across sessions, across two vendors, and
across machines, has one leg the DoD asserts and nobody has ever tested. Afterwards the
facet says what it actually delivers, the cross-machine claim is either verified or
withdrawn, and no future session spends effort optimising a cost that is gone. This is
filler in the sense that it is not urgent, and load-bearing in the sense that a false
premise keeps directing work.

**Market position.** Three teams ship repo-local continuity and the agent CLIs ship their
own memory, but all of it is single-project and agent-locked; Horus already has the
vendor-neutral store in git and dual managed blocks but still misses any verification that
it actually crosses a machine boundary; therefore these items.

**Numbered roadmap.**
1. **Restate the Continuity-core DoD around durable cross-vendor state** (new, prose) —
   the current framing invites token-economy work. Routed to branch B's pass as item 5,
   because a Vision edit is a convergence decision.
2. **Verify the cross-machine claim once, with a receipt** (new) — push from this machine,
   resume the same project cold on a second machine, score against a fixed checklist:
   fetch-first fires, exact `next_action` recovered, version floor respected, closure path
   works. Weak point: local recovery notes are gitignored *by design*, so the test must
   distinguish "correctly absent" from "broken". Non-goal: any sync mechanism — git stays
   the only cross-machine layer.
3. **Freeze the size-budget machinery at what shipped** (defer/retire candidate) — keep
   the budgets that exist, since they also serve readability, which is still true; add no
   more. Routed to branch B.

**Convergence criterion.** The DoD names durable cross-vendor state, one cross-machine
resume is verified by receipt, and no open card proposes new size instrumentation. Rough
cost: one two-machine test plus two convergence decisions.

**Implied Vision edits.** Rescope **Continuity core**'s DoD to lead with vendor-neutral
durability: *"Any official agent CLI, on any machine, resumes the exact next step from the
same durable `.horus/` state alone, fetch-first — no agent-locked memory and no Horus
runtime required."*

## 5. Speculative branches

### X1 — Host-native state for Codex (cheap; gates branch A)

**The gap.** Branch A rests on herdr publishing `agent_status`, and Horus is 50 of 246
sessions Codex all-time. Neither the scan nor any probe has checked whether herdr's state
detection works for a Codex pane, and there is reason to doubt it: herdr appears to detect
state by reading Claude's literal UI strings. **The idea.** Launch one Codex session under
herdr, read `api snapshot`, compare the populated fields against a Claude pane. **Cheapest
PoC:** under an hour, one session and one API call. **Why it fits the intent:** A's value
roughly halves if it covers one of the owner's two agents, so this is the cheapest
de-risking of the tree's primary branch. **Converge/drop:** *converges* if `agent_status`
populates for Codex, and A's scope stands as written; *dropped, with A explicitly rescoped
to Claude-only*, if detection is Claude-specific — Codex rows then keep the registry path,
which is perfectly fine once A item 1 has made that path honest. **Dying cheap is success
here** — either outcome improves A, which is why it should run first.

### X2 — Cross-machine fleet READ (park; re-tests an out-of-scope line)

**The gap.** The Vision puts the *distributed execution plane* out of scope, and that line
has never been re-tested against usage even though Continuity core's DoD claims "across
machines" and the audit could not measure it. An out-of-scope declaration is a hypothesis,
and this project has promoted one before — single-machine autonomous dispatch came in from
that same line on usage evidence in 2026-07-17. **The idea.** A strictly read-only
cross-machine fleet view: what is running elsewhere, with no control path, which is the
part the out-of-scope line actually excludes. **Cheapest PoC:** zero marginal cost if
branch D runs — during D's two-machine test, record every moment you had to guess at the
other machine's state. **Converge/drop:** *converges* if that list is non-empty;
*dropped, and the out-of-scope line confirmed*, if pushed git state already answers
everything, which is the current hypothesis.

### X3 — Mine the registry you already fill (RAN this session; converged)

**The gap.** Horus has written structured telemetry for 246 sessions and has never read it
back. Every row carries agent, account, project, launch target, timestamps and a full set
of `delivery_*` fields — branch, expected vs pushed SHA, PR number, delivery status,
whether continuity was closed. No card proposes reading it, which is exactly why no
backlog-derived tree could have surfaced it.

**Its drop criterion was a single read-only query, so I ran it rather than proposing it.**

```
sessions that expected a delivery:            35
  ...that never pushed a SHA:                  8   (23%)
  ...that never opened a PR:                   9
  ...whose continuity was never closed:        4
delivery_status: delivery-ready 25 · blocked 5 · unknown 4 · failed 1
```

All 8 never-pushed sessions carry a `-wt-` worktree path — every one a dispatched worker,
not one interactive session. **Honest caveat:** "never pushed" is not "lost" — at least
four correspond to work that later shipped by another route (`stale-datum-usage-overlap`,
`codex-usage-window-semantics` and `vision-omits-intent-and-audiences` are all archived
today), so the true reading is silent worker non-delivery followed by rework. Smaller than
it first looks, and still a cost nobody was measuring.

**Converged.** It surfaced something the owner did not know and is directly actionable —
and it belongs to branch C, as the baseline C's one real run gets measured against.
**What it earns:** not a subsystem, a small read-out, folded into `usage-analytics-read-out`
(existing, Accounts & isolation) rather than given its own surface. That card shares the
instinct — render recorded history instead of point-in-time readings — but mines the usage
cache to answer *which account has slack*; this mines the registry to answer *which work
never landed*. Two feeds, one surface.

## 6. Recommendation, held loosely

**Primary: A**, because it is the only facet that is simultaneously the differentiator, in
daily use, and wrong — and because its first item is the root cause rather than a symptom,
repairs every host path at once, and is small enough to ship on its own. **Run X1 before
committing to A's full scope**: under an hour, and it decides whether A covers one agent
or two. **Primary: B**, because three of the four branches here terminate in decisions
that only a convergence pass can spend, and because a loop that has diverged five times
and converged zero times is not a loop. If B never runs, this receipt joins the other four.
**Secondary: C** — genuinely subtractive, and now evidence-backed by X3; sequence its item
1 before item 2 so the priors land before anything is dispatched against them.
**Filler: D** — not urgent, but a false premise keeps directing work, and item 2 costs one
two-machine test. **Park X2**; fold **X3** into C.

**Not a branch, and deliberately so: cut the release.** 22 commits are unreleased, four of
them fleet-facing, and this session demonstrated the cost when a stale installed CLI
printed a retired signal. It is surfaced here with reasons and left where it belongs — the
owner's own decision, taken separately once continuity is current, never chained off a
plan.

**Existing-card push-backs, summarized.** `session-agent-state-awareness` → **largely
retired by the host** (herdr already answers it; fold the remainder into A2).
`session-close-ux-and-truthful-end-state` → **into A**, and it carries both standing owner
constraints — A1 fixes the vocabulary for every host before any herdr work, and the
cockpit's session-status column is a deletion candidate under A6 rather than a repair job.
`herdr-server-shutdown-fragility`, `session-host-protocol`, `tui-fleet-artifact-refresh`
→ **into A**. `concurrency-safe-continuity`, `continuity-sync-friction`,
`scoped-machine-requirements`, `new-machine-setup-guidance` → **into D** (all bear on the
cross-machine claim D2 tests). `automated-model-roster-grounding` → **into C1**, verify
before creating anything new. `remote-open-model-worker-probe`, `openrouter-provider-support`
→ **into C**, informed by C1. `deferred-supervision-completion-receipt`,
`worker-progress-heartbeat`, `dispatch-workflow-comparative-study` → **defer candidates**
pending C2's run. `explore-converge-lifecycle` → **gated behind B1**, not before it.
`vision-branch-x6-workflow-selection-compatibility` → **into B4**. The eight Accounts &
isolation cards → **defer/retire candidates for B**, with one exception:
`merge-release-owner-gate` keeps its own-session routing, which the 2026-07-28 refinement
finding got right. `usage-analytics-read-out` → **into C**, as X3's home.
`skill-self-calibration-probe`, `skill-drift-surfacing-and-refresh`,
`managed-instruction-drift-lint` → **park**; Introspection is the healthiest facet and
adding to it is ceremony. `verify-guidance-long-running-services`, `audit-advisory-interval`
→ **reserved, do not promote**. **MCP read path** → **withdrawn, not re-proposed**: the
scan calls it the cheapest capability gap, but this run found nothing to contradict the
owner's 2026-07-31 argument that Claude Code and Codex already read files and run bash, so
an MCP read path duplicates access they have twice over. **X4 and X5** → untouched by this
tree; X5 remains under an owner-confirmed undated hold the audit says not to re-raise.
**The 47 exploratory cards** → this tree does not claim to place them; if reorganising the
backlog is the goal, that is `backlog-refine`, not a divergence tree.

## 7. Owner gate

Pick one or more branches, or amend the tree. Nothing has been written to the Vision, no
cards created, no backlog reordered — the chosen branch feeds `scope-cards`.

Or dive deeper into one named topic first: the exact `TERMINAL` change and its four call
sites (A1); branch B's convergence agenda card by card; or X1's Codex probe, which is the
cheapest thing in this receipt and gates the primary branch.
