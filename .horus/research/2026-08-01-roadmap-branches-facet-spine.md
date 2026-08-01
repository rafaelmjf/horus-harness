# Roadmap branches (v7): the facet spine — 2026-08-01

**Intent:** deepen-own-use. **Inputs pinned identically to the three rejected runs of
2026-07-31** — audit `.horus/audits/2026-07-31-product.md`, scan
`.horus/research/2026-07-31-market-scan-build-vs-adopt.md` — so any difference in this
tree is the skill, not the evidence.

**Consumes, does not re-derive:**
- `2026-07-31-roadmap-branches-rebaseline.md` §8 — branches A/C/D recorded unpicked;
  branch B (MCP) **withdrawn by the owner** and *not* re-proposed here (see §7).
- `2026-07-31-roadmap-branches-herdr-and-cockpit.md` — the v5 re-run. Its content was
  good and is carried forward; its *shape* was the defect. Three of its five branches
  targeted one facet while seven other facets went unexamined. Here that material
  becomes **one** facet branch (B) among eight.
- `2026-07-17-pathfinder-branch-tree.md` — the shape that worked.

**Evidence re-gathered this run rather than inherited** (claims discipline): the live
`~/.horus/registry.json` (246 rows), a live `herdr api snapshot`, the `TERMINAL`
vocabulary in `horus/registry.py`, and the installed-CLI version. Where my numbers
differ from the audit's, mine are stated and the difference explained.

---

## 1. Where we are

Facet standings: see the audit's table (§3) — not restated. What this tree adds is the
**life-stage** judgment per facet, and three corrections from live measurement.

| Facet | Life-stage | The one-line judgment |
|---|---|---|
| Continuity core | **steady-state, premise shifted** | Works. The reason it works is no longer the reason it was built. |
| Dashboard / cockpit | **active frontier, defective** | The differentiator, and it lies about 67% of recent sessions. |
| Accounts & isolation | **converged** | DoD met. Still carrying 8 open cards. |
| Delegation calibration | **built, never exercised** | 6 cards instrumenting a decision that was made 0 times this window. |
| PO lifecycle | **the open frontier** | Divergence ran 4× in one day. Convergence has never run once. |
| Introspection & self-improvement | **working as designed** | The strongest facet; its blind spot is that it needs the owner to fire it. |
| Autonomous dispatch | **built, unused** | Most-carded facet (11), zero armed timers, zero eligible cards. |
| Distribution | **strong, stalled** | 22 commits unreleased; the owner's own machine runs behind the repo. |

**Three corrections to the audit, measured live this session:**

1. **The cockpit defect is worse than reported.** The audit measured a 26-session window
   and found 36 of 38 `failed` rows were owner closes (56% of sessions). All-time:
   **73 of 246 rows are `('failed','stopped')` — 88% of every `failed` row in the
   registry's history**, and in the **last 30 sessions it is 20, or 67%**. It is getting
   worse, not better, because herdr sessions close through the same path.
2. **herdr adoption is steeper than reported.** The audit said 11 of 26 recent sessions.
   Live: **all 13 herdr sessions that have ever existed fall inside the last 30** —
   43% of recent traffic, from a standing start. Nothing else shipped recently has an
   adoption curve like it.
3. **The audit's `47 explore vs 27 converge` is not what the cards say.** Measured:
   **47 explore, 16 converge, and 12 cards carrying no `phase:` stamp at all.** The
   audit appears to have counted unstamped cards as converging. The real ratio is worse
   and there is a third category nobody is looking at.

**Position in one line:** every facet except one is either converged, unused, or
unexercised — the single facet that is both used daily and actively wrong is the
cockpit, and the project's forward loop has spent its energy on divergence while the
convergence half has never once run.

## 2. Where the market is

From the scan receipt, stated once. Three teams (AICTX, agent-memory, memories.sh)
independently reached repo-local Markdown continuity; none is adoptable here (all
single-project; the switching cost is 20 managed projects plus every skill, hook and
verb that keys on `.horus/`). The platform is moving up into session views:
`claude agents` ships rows with PR links and honest `Working`/`Needs input` states.

**The one verdict:** the differentiator has shifted from *what Horus stores* to *how
many things it spans* — multi-agent × multi-account × multi-project is the only
intersection nothing else occupies.

**The scan's `session host: KEEP-THIN, do not deepen` line is wrong for this intent**,
and the v5 receipt already corrected it: that is a market instinct ("don't rebuild
someone else's tool") applied to an own-use question. The correct reading is *go further
into the host and take less onto Horus* — which is the opposite of deepening Horus.

**Risks, once:** herdr is a third-party dependency at v0.7.5 with no stability promise
Horus has verified; and if `claude agents` adds multi-account and Codex, the cockpit's
value narrows to fleet-of-projects only.

## 3. The tree

```
Horus v0.0.79 (+22 unreleased) — 8 facets: 2 converged, 3 built-but-unused,
1 daily-and-defective, 1 frontier that only ever diverges, 1 stalled on a release.
│
├── A  The thesis was never token economy ......... Continuity core        [secondary]
├── B  Stop guessing what the host publishes ...... Dashboard / cockpit    [PRIMARY]
├── C  Declare it done ........................... Accounts & isolation    [filler, subtractive]
├── D  Stop calibrating what is never dispatched .. Delegation calibration [secondary, subtractive]
├── E  Run the convergence pass that never ran .... PO lifecycle           [PRIMARY]
├── F  Give a skill a shape test .................. Introspection          [filler]
├── G  Arm it once, or stop building it ........... Autonomous dispatch    [secondary, subtractive]
├── H  Cut the release ........................... Distribution            [filler, decision]
│
├── X1 Does host-native state generalise to Codex?  (no facet yet)         [cheap, gates B]
├── X2 Cross-machine fleet READ .................. (no facet yet)          [park, re-tests out-of-scope]
└── X3 Mine the registry you already fill ........ (no facet yet)          [RAN THIS SESSION — converged]
```

**X3 was answered, not just proposed.** Its drop criterion was "one read-only query
decides it", so I ran the query rather than asking you to authorise it. It converged, and
its finding — **8 of 35 delivery-expecting sessions never pushed a SHA, all 8 of them
dispatched workers** — bears directly on branch G. See §5.

**Four of eight facet branches are subtractive or decisions** — they propose retiring,
freezing, or rescoping rather than adding work. That is deliberate: advancing a facet
includes shrinking it, and on a backlog of 75 open cards with 3 ready, the honest
direction for most facets is *less*.

---

## 4. The branches

### A — The thesis was never token economy → *Continuity core* (secondary)

**The problem.** Horus was built because a fresh agent session started from zero and you
had to re-explain the project. The fix was to write things down — and then to worry a
lot about how *much* was written down, because context was scarce and expensive. Eleven
PRs in the last window cut committed continuity from 276,884 to about 71,000 characters.
But context stopped being scarce: Opus 5 ships a million tokens, against which the whole
59KB PRD is rounding error. So the project has just finished optimising hard against a
cost that mostly evaporated, while the thing that *is* still true — that this state
survives across sessions, across two different vendors' agents, and across machines —
has a leg that has never been tested. The Vision claims "across machines". Nobody has
ever checked.

**The proposed solution.** Say out loud what continuity is actually for, so future work
optimises the right property: durable cross-session, cross-vendor state — not saving
tokens. Then test the one claim that is load-bearing and unverified (cross-machine), and
stop extending the size machinery now that its original justification is gone.

**Thesis.** Under deepen-own-use, a premise that has quietly gone false is more dangerous
than a missing feature: it keeps directing effort. The size-budget work was good
engineering aimed at a target that moved, and the only way to stop repeating that is to
restate the target.

**Market position.** *This exists already* — three teams ship repo-local continuity and
the agent CLIs ship their own memory — *but they miss* cross-vendor and cross-machine
durability, being single-project and agent-locked. *You already have* the neutral store
in git *but still miss* any verification that it actually crosses a machine boundary.
*Therefore:* restate, verify, and stop building size machinery.

**Roadmap.**
1. **Restate the Continuity-core DoD around durable cross-vendor state.** Why: the
   current framing invites token-economy work. How: a Vision edit (draft in "implied
   edits" below). This is the audit's routed suggestion #5 and the scan's open question
   #4 — both already point here; this branch just gives them a home.
2. **Verify the cross-machine claim once, with a receipt.** Why: it is asserted in a DoD
   and has never been exercised. How: push from this machine, resume the same project
   cold on a second machine, score against a fixed checklist (fetch-first fires · exact
   `next_action` recovered · version floor respected · closure path works). Weak point:
   local recovery notes are gitignored by design, so anything they carry is *supposed*
   to be lost — the test must distinguish "correctly absent" from "broken". Non-goal: any
   sync mechanism; git stays the only cross-machine layer.
3. **Freeze the size-budget machinery at what shipped.** Why: its justification was
   context scarcity. How: a defer/retire candidate on any further budget/cap work,
   routed to convergence — not decided here. Keep the budgets that exist (they also
   serve readability, which is still true); add no more.

**Convergence criterion.** The DoD names durable cross-vendor state, one cross-machine
resume is verified by receipt, and no open card proposes new size instrumentation.
**Cost:** one short session plus one two-machine test.

**Implied Vision edits.** Rescope **Continuity core**'s DoD to lead with vendor-neutral
durability rather than bare resumption: *"Any official agent CLI, on any machine,
resumes the exact next step from the same durable `.horus/` state alone, fetch-first —
no agent-locked memory and no Horus runtime required."* No facet added or retired.

---

### B — Stop guessing what the host already publishes → *Dashboard / cockpit* (PRIMARY)

**The problem.** You open the cockpit and most of what you closed yesterday is sitting
there in red, marked failed. Right now that is **73 rows all-time and 20 of your last
30 sessions** — 67% of recent work reported as failure when you simply closed a session
normally. The daily surface, the one thing the market scan says is the actual
differentiator, is lying to you about most of its rows. Meanwhile the program that hosts
those sessions already knows the truth and publishes it: I asked it during this run and
it returned, for every live session at once, the agent, its live status, the project, a
stable pane id, a change counter, and the literal task title of what it is doing right
now.

**The proposed solution.** Closed sessions look closed. Running sessions show what they
are actually doing, in words, taken from the host that owns that fact rather than
guessed from a process table. Horus keeps and shows only what nothing else knows —
projects, accounts, delivery, continuity.

**Thesis.** This is the one facet that is used every day *and* wrong, so under
deepen-own-use it outranks everything. It is also the cheapest kind of fix available:
deleting a guess and reading an answer.

**Root cause, found this run.** This is not a stray line to patch. `horus/registry.py:29`
declares `TERMINAL = {"exited", "failed", "orphaned", "stale"}` — there is **no terminal
status meaning "the owner closed it"**. So `stop_session` at
`horus/terminal_sessions.py:375` writes `termination_reason="stopped"` and then has
nowhere to put the status except `failed`; `reap_orphans` does the same at line 554. The
vocabulary is missing a word, and every path that closes a session honestly is forced to
lie. Relatedly, **no registry row has a `host` field at all** (246 of 246 are `None`) —
host is inferred by string-matching the shape of `target_ref`.

**Market position.** *This exists already* — `claude agents` ships a native session list
with honest states, and herdr publishes live agent state — *but they miss* Horus's
projects, accounts, Codex coverage and delivery tracking. *You already have* the registry,
delivery tracking and the fleet view *but still miss* truthful live state, which is the
part your host is giving away for free. *Therefore:* consume the host's truth, keep the
delta, and stop maintaining a worse copy.

**Roadmap.**
1. **Add the missing terminal status.** Why: it is the root cause, and it fixes every
   path at once rather than per-host. How: extend the `TERMINAL` vocabulary with a
   `stopped` (owner-initiated) state, migrate the 73 existing `('failed','stopped')` rows
   which are unambiguously identifiable by their `termination_reason`, and update the
   TUI/dashboard status colouring. Weak point: `TERMINAL` membership is tested in at
   least four places (`registry.py:317,457,498`) — the new status must be terminal
   everywhere or reaping will loop. Non-goal: a general status-vocabulary redesign.
2. **Read `herdr api snapshot` for herdr-hosted rows.** Why: `agent_status` is precisely
   what the card `session-agent-state-awareness` was written to *build*, and the host
   already solved it. How: one call keyed by `pane_id`, which Horus already stores as
   `target_ref` in exactly that form (`w2:p3`); cache on `state_change_seq` so polling is
   cheap. Weak points: herdr must be running — an absent server falls back to the
   registry and is never an error; v0.7.5 has no stability promise, so pin the fields
   consumed and treat unknown shapes as absent. Non-goals: no screen-scraping, no polling
   inside a paint path.
3. **Show the live task title.** Why: `terminal_title` is a free per-session "what is it
   doing right now" label Horus has no other way to produce. How: surface it in the TUI
   session rows and the dashboard.
4. **Give the registry a real `host` field.** Why: host is currently inferred from
   `target_ref` string shape, which is why host-specific behaviour is awkward to write.
   How: populate on launch from the known launch target; backfill is optional.
5. **Decide the honest DoD for "no terminal command".** Why: the facet promises
   launch/resume from web or phone with no terminal command; delivered reality is a
   read-mostly dashboard plus Termius SSH into the TUI, which *is* a terminal command.
   How: this is a decision, not a build — either it is in (and needs an authority model
   that respects the never-mints-authority rule, which becomes its own card) or it is out
   and the DoD text should stop claiming it. Second-order: the authority design is a
   separate card only if the answer is "in".
6. **Scope the registry to the delta.** Why: once 2–4 land, some of what Horus stores is
   a worse copy of what the host answers. Findings become their own cards.

**Convergence criterion.** For any hosted session, every state the cockpit shows is
either sourced from the host that owns it or is something only Horus knows — nothing is
guessed — and no owner-initiated close is ever displayed as a failure. **Cost:** item 1
is a short session on its own and delivers most of the honesty win; items 2–4 are one
more; item 5 is a decision.

**Implied Vision edits.** No facet added or retired. Sharpen **Dashboard / cockpit**'s
DoD with a truthfulness clause: *"…and every state it reports is either true by
construction or sourced from the host that owns it."* Conditionally, per item 5, drop
"no terminal command" if the decision is "out". This also extends the Vision's existing
**native-app-first** principle from agent CLIs to *hosts*.

---

### C — Declare it done → *Accounts & isolation* (filler, subtractive)

**The problem.** This facet works. Both accounts are in real use, isolation is on by
default, per-account usage is visible, and the audit calls it strong with the DoD met.
It is also still carrying **8 open cards**. Work continues on a finished thing because
nothing ever declares it finished.

**The proposed solution.** Say it is done. Route its open cards to defer/retire
candidates and let the facet earn new work only from a real incident.

**Thesis.** Under deepen-own-use the scarcest resource is the owner's attention, and a
converged facet holding 8 cards spends it on maintenance that no longer buys anything.

**Market position.** *This exists already* — nothing, actually; per-account isolation
across two vendors is not something the scan found anyone else doing. *You already have*
the full capability *but still miss* a way to mark a facet complete so it stops
accumulating. *Therefore:* the item here is a status declaration, not a build.

**Roadmap.**
1. **Walk the 8 cards and mark each a defer or retire candidate**, argued against the
   DoD, routed to the convergence pass (branch E) — decided there, never here.
2. **Record the facet as converged** in the Vision, with the evidence line that supports
   it, so a future audit reads it as steady-state rather than under-served.

**Convergence criterion.** The facet is marked converged and its open-card count is
materially lower without any capability being lost. **Cost:** part of one convergence
session; no engineering.

**Implied Vision edits.** None to the DoD text. Add a converged marker to
**Accounts & isolation**.

---

### D — Stop calibrating what is never dispatched → *Delegation calibration* (secondary, subtractive)

**The problem.** The facet exists to help decide whether to do work here or hand it to
another agent, and to pick a model tier from measured data. In the window the audit
covers, **that decision was made zero times** — no dispatch happened at all. There are
still 6 open cards refining the instrumentation. The owner already made this critique
once, on 2026-07-17: the gap is over-reliance on small-n, confounded, single-task-mix
data of our own when public benchmarks rank tiers for free.

**What actually happened to that critique — checked card by card this run, and it is not
what the earlier trees assumed.** The *cleanup* half was carried out: of the four cards
the 2026-07-17 branch C named as defer/retire candidates, three
(`stale-datum-usage-overlap-reconciliation`, `codex-usage-window-semantics`,
`codex-usage-stale-snapshot-gates-dispatch`) are archived. But the *corrective* half was
never started — `external-priors-calibration`, the one new card that would have made the
rubric read priors-first, **was never created at all**. So the facet did the subtraction
and skipped the fix, which is the opposite of the failure mode I expected to find and a
better argument for doing item 1 now.

**The proposed solution.** Rank tiers from external evidence, keep our own measurements
only for the residual nobody else measures (this harness's own bounce/nudge rates,
per-account throughput), and let the facet go quiet until a real dispatch happens.

**Thesis.** Instrumentation built ahead of the decision it serves is the most expensive
kind of unused code, because it keeps generating maintenance cards. Deepen-own-use says
the facet should shrink until usage pulls it back.

**Market position.** *This exists already* — public benchmarks and leaderboards rank
model tiers continuously and for free — *but they miss* our harness's own residual
behaviour. *You already have* a datum store and a rubric *but still miss* external
priors, which is the part that would actually carry the ranking. *Therefore:* priors
first, own datums as residual, and fewer cards either way.

**Roadmap.**
1. **Fold sourced external priors into the rubric** so it reads priors-first and own
   datums as the residual. Why: it is the correction the owner asked for in 2026-07-17
   and the only part of it never done. How: the owner-priors slot in
   `horus capabilities --models`; repeatable per model generation. Weak point: priors go
   stale on a model refresh — the refresh path must be named or this becomes its own
   drift. Note `automated-model-roster-grounding` (open, this facet) is the closest
   existing card and may already be this item under another name — check before creating
   anything new.
2. **Route the remaining maintenance cards to defer/retire candidates** against the
   convergence pass — `deferred-supervision-completion-receipt`, `worker-progress-heartbeat`,
   `dispatch-workflow-comparative-study` — on the argument that supervision and
   heartbeat instrumentation only matters once a real dispatch exists to supervise, and
   there are currently none.
3. **Gate further work on a real dispatch happening.** Second-order by construction: if
   branch G arms a real dispatch, its findings become this facet's next cards.

**Convergence criterion.** A tier recommendation cites external evidence, and the facet's
card count went down rather than up. **Cost:** one session for item 1; items 2–3 are
convergence decisions.

**Implied Vision edits.** Rescope **Delegation calibration**'s DoD to name external
priors as the primary source and own measurements as the residual, rather than implying
all calibration is self-measured.

---

### E — Run the convergence pass that has never run → *PO lifecycle* (PRIMARY)

**The problem.** The Vision's central claim about how this project works is that ideas
diverge, get used, and then converge — dropped, trimmed, or promoted. The divergence half
runs constantly. **The convergence half has never run once.** The evidence is this very
day: four divergence trees were produced on 2026-07-31 and 2026-08-01, and zero
convergence passes have ever happened. The backlog shows the accumulation — 75 open
cards, of which **3 are ready**, 26 are deferred, and 47 are exploratory. Nothing in the
system removes anything, so everything stays.

**The proposed solution.** Actually run a convergence pass, with real verdicts that kill
or rescope real things. Not another list of what could be done — a session whose output
is a smaller backlog.

**Thesis.** This is the facet the audit calls weakest and the Vision calls the open
frontier, and it is the bottleneck on every other branch here: four of the eight facet
branches in this tree end by routing candidates to a convergence pass that does not
exist. Building the convergence step is what makes the rest of this tree executable.

**A caution worth stating.** The machinery was declared shipped (`roadmap-convergence`,
archived) and the pass still never ran. So the missing thing is probably not more
machinery — it is a session that spends the decisions. Building more convergence tooling
before running one pass by hand would repeat the mistake this facet already made.

**Market position.** *This exists already* — nothing does. Spec-Kit and task-master run
per-feature pipelines with no living lifecycle; the continuity tools store state and
never prune it. *You already have* the convergence read-out and the divergence tree *but
still miss* a single instance of a decision that removed work. *Therefore:* the item is
to run it, not to build it.

**Roadmap.**
1. **Run one convergence pass by hand, with this tree as its agenda.** Why: four branches
   here already produced defer/retire candidates; that is a real agenda rather than a
   synthetic one. How: walk the candidates from A3, C1, D2, G2 plus the 26 deferred
   cards, and give each an actual verdict — kill, rescope, or keep with a reason. Weak
   point: the temptation is to keep everything "just in case", which is what produced 26
   deferred; a pass that removes nothing has failed and should be reported as such.
2. **Resolve the 12 unstamped cards.** Why: measured this run — 12 cards carry no `phase:`
   at all, so they are invisible to the explore/converge ratio that this facet is judged
   by. The ratio everyone has been quoting is wrong because of them.
3. **Decide whether the 26 deferred cards are parked or actually dropped.** Why: over a
   third of the backlog, including the whole X5 branch under an *undated* hold. The audit
   routed this here (#3). How: each deferred card gets either a dated trigger or a
   retirement.
4. **Decide what X6's probe is now**, given fabric was declared non-influential — the
   audit's routed suggestion #2, which has no other home.
5. **Only then** consider whether `explore-converge-lifecycle` needs building. Findings
   from the manual pass become its requirements; today it is a Deferred card waiting on a
   usage signal that a hand-run pass would produce directly.

**Convergence criterion.** One pass has run, the open-card count is materially lower,
every deferred card has a dated trigger or a retirement, and at least one real thing was
killed. **Cost:** one focused session, and it is the highest-leverage session available.

**Implied Vision edits.** Update the PO-lifecycle frontier note from "convergence is the
open gap" to whatever the first pass proves — likely that the gap was never machinery but
the decision session itself. No facet added or retired.

---

### F — Give a skill a shape test → *Introspection & self-improvement* (filler)

**The problem.** This is the healthiest facet — five audit receipts in the window,
budgets shipped, the audit gate neither skipped nor rubber-stamped. But its blind spot
showed up sharply in the last two days: the `roadmap-branches` skill was rewritten from
v4 to v7 across **three rejected runs in a single day**, and every rejection came from
the owner reading the output and saying it was the wrong shape. The skill's own text had
warned about that exact failure since v4 and the failure happened anyway. Nothing
automatic ever checked whether what came out matched what the skill said should come out.

**The proposed solution.** For the few skills that declare a concrete output shape, check
the output against it cheaply, so the owner is not the only detector.

**Thesis.** Under deepen-own-use the cost being paid is the owner's time reading a wrong
artifact and re-running — three times in one day is a real, dated, measured cost.

**Honest caveat, stated because this facet's own doctrine demands it.** This is one step
from ceremony. A shape checker that lints prose would be exactly the kind of overhead
this project keeps deleting. It is worth doing only in the narrowest form — a handful of
structural assertions on skills that declare a fixed template — and worth dropping fast
if it fires on correct output.

**Market position.** *This exists already* — nothing comparable; skill/prompt libraries
ship no output-shape verification. *You already have* skill-audit for evidence-based
review *but still miss* anything between "the owner rejects it" and "a full audit".
*Therefore:* one narrow structural check, or nothing.

**Roadmap.**
1. **Assert the declared structure on skills that have one.** Why: `roadmap-branches`
   declares six numbered sections and a required per-branch element list; that is
   mechanically checkable. How: a check over the emitted receipt, not the skill text.
   Weak point: only a handful of skills declare a fixed shape — this must not grow into
   linting every skill's prose. Non-goal: judging content quality, which is exactly what
   cannot be automated and is what skill-audit is for.
2. **Drop it if it produces a false positive on a receipt the owner accepted.** Dying
   cheap is a valid outcome.

**Convergence criterion.** Either a shape violation is caught before the owner sees it,
or the check is retired for firing wrongly. **Cost:** small; half a session.

**Implied Vision edits.** None.

---

### G — Arm it once, or stop building it → *Autonomous dispatch* (secondary, subtractive)

**The problem.** This is the **most-carded facet in the project — 11 open cards** — and
it has never run. I checked during this session: **no systemd timer is armed**, three
drill envelopes exist and none has fired, and zero cards are autonomous-eligible. The
machinery to run approved cards end-to-end unattended is complete and has processed
nothing. The audit is precise about why: the gap is eligible work, not capability.

**The proposed solution.** Put one real card through the loop end to end, unattended, and
see what actually breaks. If that cannot be done, freeze the facet and stop adding cards
to it.

**Thesis.** Eleven cards of unexercised machinery is the largest single block of
speculative work in the backlog. One real run converts it from belief to evidence, and it
is the only thing that makes the remaining ten cards either justified or deletable.

**The tension worth naming.** Branch E is about removing work, and this branch proposes
spending a session on a facet that has produced nothing. The argument for doing it anyway
is that the facet cannot be *fairly* trimmed until one real run tells you which of the 11
cards were real. The argument against is that a facet with zero pull after being fully
built is telling you something already. **This is a genuine fork and the owner should
decide it, not this tree.**

**Market position.** *This exists already* — `claude agents` runs background sessions and
Agent Teams exists experimentally — *but they miss* accounts, envelopes, pre-authorized
scope and independent CI verification. *You already have* all of that machinery *but
still miss* a single completed unattended run. *Therefore:* the item is one run, not more
capability.

**Roadmap.**
1. **Pick one genuinely eligible card and arm it.** Why: it is the only way to learn
   anything here. How: the strongest candidate is item 1 of branch B — the terminal-status
   fix is bounded, has a clear deterministic gate (tests plus a live registry check), and
   its blast radius is one status vocabulary. Weak point: the drill's two reserved legs
   must stay reserved; do not promote something merely to refill the queue, which the PRD
   explicitly forbids.
2. **Route the remaining cards to defer/retire candidates pending that run**, so the
   facet stops growing while unproven.

**Convergence criterion.** One card has gone from armed to merged without the owner
driving it, and the facet's card count is lower afterwards. **Cost:** one supervised run,
which by design costs little owner attention — that is the thing being tested.

**Implied Vision edits.** None yet. If the run fails to produce value, a future
convergence pass should consider whether the facet was promoted too early — recorded here
as a question, not a proposal.

---

### H — Cut the release → *Distribution* (filler, decision)

**The problem.** **22 commits sit unreleased** on top of v0.0.79, including four
fleet-facing fixes. Concretely, and verified in this session: the `horus` binary on this
machine is 0.0.79, and when I ran `horus consolidate` it printed the **old ~250-line PRD
cap** — the character-budget work that replaced that cap is in the unreleased commits. So
the machine you work on is running behind its own repo, and the fix for the exact signal
you rely on is invisible where you actually read it. The hosted dashboard is pinned and
only advances on an explicit upgrade plus restart.

**The proposed solution.** Cut the release, publish, and run the deploy script so the
tools you use daily are the tools this repo has actually built.

**Thesis.** This is not a direction, it is an overdue action with a compounding cost:
every session run against a stale CLI risks acting on a retired signal, as this one did.

**Market position.** Not applicable — this is internal cadence, not positioning.

**Roadmap.**
1. **Three-file bump → tag → `gh release create` → PyPI publish → `scripts/deploy-hosted.sh`.**
   The deploy script is mandatory and last: publishing does not update
   `horus.rafaelfigueiredo.com`, which runs a pinned install. Weak point: use
   `uv tool install --force --refresh`, never `uv tool upgrade --reinstall`, which
   silently stays on the old version.

**Convergence criterion.** `horus --version` on this machine matches the repo, and
`/health` is green with `/` still 403.

**Implied Vision edits.** None.

**Routing note.** The audit routed the release decision to *"owner, with the release
decision"* (#6), and the managed instructions are explicit that a release is never
chained off a plan — it is its own decision, taken with the owner, after continuity is
current. This branch therefore *surfaces* it with reasons and stops.

---

## 5. Speculative branches (no facet yet)

### X1 — Does host-native state generalise to Codex? *(cheap; gates branch B)*

**The gap.** Branch B rests on herdr publishing `agent_status`. Horus is **50 of 246
sessions Codex all-time**, and neither the scan nor any probe has examined whether
herdr's state detection works for a Codex pane — there is reason to doubt it, since
herdr appears to detect state by reading Claude's literal UI strings.

**The idea.** Launch one Codex session under herdr, read `api snapshot`, and compare the
fields against a Claude pane.

**Cheapest PoC.** Under an hour. One session, one API call, one comparison.

**Why it fits the intent.** B's value roughly halves if it covers one of your two agents.
This is the cheapest possible de-risking of the tree's primary branch.

**Converge / drop.** **Converges** if `agent_status` populates for Codex — B covers both
agents and its scope stands. **Dropped, and B explicitly rescoped to Claude-only**, if
detection is Claude-specific; Codex rows then keep the registry path, which is fine once
B item 1 has made that path honest. **Dying cheap is success here** — either outcome
improves B.

### X2 — Cross-machine fleet READ *(park; re-tests an out-of-scope line)*

**The gap.** The Vision puts the *distributed execution plane* out of scope, and that
line has never been re-tested against usage even though **Continuity core's DoD claims
"across machines"** and the audit could not measure it. An out-of-scope declaration is a
hypothesis, not a fact — and this project has promoted one before (single-machine
autonomous dispatch came in from that same line on usage evidence in 2026-07-17).

**The idea.** A strictly read-only cross-machine fleet view: what is running elsewhere,
never any control path. The out-of-scope line excludes multi-machine *control*, which
this deliberately does not touch.

**Cheapest PoC.** Piggyback on branch A item 2's two-machine test — while doing the
cross-machine resume, note every moment you had to guess at the other machine's state.
Zero marginal cost if A runs.

**Converge / drop.** **Converges** if the A2 test produces real moments of guessing.
**Dropped** if pushed git state already answers everything — which is the current
hypothesis and would retire the question for good.

### X3 — Mine the registry you already fill *(strongest new thought)*

**The gap.** Horus has been writing structured telemetry for **246 sessions** and has
never once read it back. Every row carries agent, account, project, launch target,
timestamps, and a full set of `delivery_*` fields — branch, expected vs pushed SHA, PR
number, delivery status, whether continuity was closed. That is a rich, already-paid-for
record of how this owner's work actually goes, and nothing consumes it. **No card
proposes reading it** — verified by search this run — which is precisely why no
backlog-derived tree could have proposed this, the same structural blindness that got
the v4 tree rejected.

**Its closest sibling, named honestly rather than ignored.** `usage-analytics-read-out`
(open, Accounts & isolation) shares the instinct — *render recorded history instead of
point-in-time readings* — but not the data or the question: it mines the **usage cache
and datums** to answer *which account has slack before I arm a batch*. X3 mines the
**session registry** to answer *which work I started never landed*. If both prove out
they are one surface with two feeds, and that is an argument for doing X3's one query
first rather than a reason to skip it.

**The idea.** Ask the data the questions currently answered by guessing: which projects
have gone quiet, which sessions ended without their delivery ever landing, whether one
account or agent produces more completed deliveries, how long real work actually takes.
Note this is *also* the honest test of a claim in branch B — that Horus should keep only
"what nothing else knows". Delivery history is exactly that, and it is currently
collected and discarded.

**Why it fits the intent.** Pure own-use: no new data collection, no new surface, and it
mines an asset already paid for. It also feeds branch E, since "which projects went
quiet" is direct convergence evidence.

**I ran the decisive query during this session** — it is read-only and free, so proposing
it rather than answering it would have been ceremony. The result:

```
sessions that expected a delivery:            35
  ...that never pushed a SHA:                  8   (23%)
  ...that never opened a PR:                   9
  ...whose continuity was never closed:        4
delivery_status: delivery-ready 25 · blocked 5 · unknown 4 · failed 1
```

**All 8 of the never-pushed sessions were worktree-isolated dispatched workers** — every
one has a `-wt-` path (`away/`, `auto/`, `worker-` branches). Not one was an interactive
session. So the registry has been quietly recording that **roughly a quarter of
dispatched work never reaches a pushed ref**, and nothing has ever surfaced it.

**The honest caveat.** "Never pushed" is not the same as "lost". At least four of the
eight correspond to work that later shipped by another route — the cards for
`stale-datum-usage-overlap`, `codex-usage-window-semantics` and
`vision-omits-intent-and-audiences` are all archived today. So the true reading is
**silent worker non-delivery followed by rework**, not permanent loss. That is a smaller
claim than it first looks, and still a real cost nobody was measuring.

**Converge / drop — this converged.** The query surfaced something the owner did not
know, and it is directly actionable. It also lands squarely on **branch G**: that branch
proposes arming one unattended dispatch, and this is the first hard evidence about how
dispatched work has historically behaved — a 23% silent-non-delivery rate is exactly the
argument for G's independent-verification discipline, and exactly the number G's one real
run should be measured against.

**What it earns.** Not a new subsystem — a small read-out, ideally folded into
`usage-analytics-read-out`'s surface rather than given its own.

---

## 6. Backlog disposition — done AFTER the branches

Per the skill's discipline, branches were built from facet-DoD-vs-code, owner friction,
and the audit/scan — then the cards were walked. **This tree does not claim to place all
75 cards**, and pretending otherwise is what produced the rejected v4 tree.

| Disposition | Cards |
|---|---|
| **Into B** | `session-close-ux-and-truthful-end-state` (the owner's two constraints ride here: never make a critical function depend on one session host — satisfied by item 1 fixing the vocabulary for *all* hosts before any herdr work; and the session-status column as a deletion candidate — item 6); `session-agent-state-awareness` (**largely retired by the host**, which already answers it); `herdr-server-shutdown-fragility`; `session-host-protocol`; `tui-fleet-artifact-refresh` |
| **Into A** | `concurrency-safe-continuity`, `continuity-sync-friction`, `scoped-machine-requirements`, `new-machine-setup-guidance` (all bear on the cross-machine claim A2 tests) |
| **Into D** | `automated-model-roster-grounding` (likely the priors work under another name — verify before creating), `remote-open-model-worker-probe`, `openrouter-provider-support`; **defer/retire candidates:** `deferred-supervision-completion-receipt`, `worker-progress-heartbeat`, `dispatch-workflow-comparative-study`. *(The 2026-07-17 tree's other named candidates — `stale-datum-usage-overlap-reconciliation`, `codex-usage-window-semantics`, `codex-usage-stale-snapshot-gates-dispatch` — are already archived; verified this run, not assumed.)* |
| **Into E** | `explore-converge-lifecycle` (but see E5 — it is gated *behind* the manual pass, not before it), `pathfinder-structured-outcome`, `vision-branch-x6-workflow-selection-compatibility`, plus **all 26 deferred cards** as the pass's agenda |
| **Into F** | `skill-self-calibration-probe`, `skill-drift-surfacing-and-refresh`, `managed-instruction-drift-lint` |
| **Into G** | `autonomous-advisory-dispatch-posture`, `dispatch-collision-guard`, `warm-supervised-worker-poc`, `window-aware-scheduling`; **reserved, do not promote:** `verify-guidance-long-running-services`, `audit-advisory-interval` |
| **Into C** | The 8 Accounts & isolation cards as defer/retire candidates for E — `account-settings-sync`, `native-app-account-launch-spike`, `prd-worked-by-account`, `isolated-account-plugin-parity`, `usage-analytics-read-out`, `codex-isolated-config-leak`, `account-login-verb`. **Exception: `merge-release-owner-gate` is not a defer candidate** — the 2026-07-28 refinement finding calls it the best-structured card in the repo and correctly routed it to its own session; it should keep that routing. |
| **Withdrawn, not re-proposed** | **MCP read path** — the market scan calls it the cheapest capability gap, but the owner withdrew it on 2026-07-31 with an argument this run found nothing to contradict: Horus drives Claude Code (189 sessions) and Codex (50), both of which already read files and run bash, so an MCP read path duplicates access they have twice over. Recorded as declined, not silently dropped. |
| **Untouched by this tree** | Everything else — notably X4 (model/harness plane) and X5 (safe execution boundaries, under an owner-confirmed undated hold the audit says not to re-raise). This tree makes no claim on them; if reorganising the backlog is the goal, that is `backlog-refine`, not a divergence tree. |

---

## 7. Recommendation, held loosely

**Two primaries, and they are complements rather than rivals.** **B** is the only facet
that is used every single day and actively wrong — 67% of your recent sessions reported
as failures is the kind of defect that quietly erodes trust in the surface the market
scan identifies as your entire moat. **E** is the bottleneck on everything else: four of
the eight branches here end by routing candidates to a convergence pass that has never
run, so without it this tree becomes another document that adds and never subtracts —
which is precisely the pathology it is diagnosing.

If only one thing happens, make it **B item 1** — the terminal-status fix. It is small,
it is the root cause rather than a symptom, it repairs every host path at once (honouring
the constraint that no critical function depend on one session host), and it is the best
candidate in the backlog for branch G's one real autonomous run.

**X1 before committing to B's full scope** — under an hour, and it decides whether B
covers one agent or two.

**D, C and G are the subtractive middle**, and they matter more than their posture tags
suggest: together they route roughly 25 cards to defer/retire candidates. They are cheap
because they mostly produce *decisions for E to spend*, not engineering.

**F is genuinely optional** and I would drop it before anything else here; it is included
because the three rejected runs are a real measured cost, not because the fix is
obviously worth building.

**H is not a direction and should not be treated as one** — it is surfaced with reasons
and left as the owner's decision, taken separately once continuity is current.

**Park X2.**

**X3 already paid for itself.** Running its query cost nothing and produced the single
most surprising number in this tree: 23% of dispatched work never reached a pushed ref,
invisible for 246 sessions. It needs no branch of its own — fold the read-out into
`usage-analytics-read-out`, and carry the finding into **G** as the baseline its one real
run gets measured against.

**A note on G, in light of X3.** X3's finding cuts both ways and I want to be straight
about it rather than let it read as support. It strengthens G's *premise* — dispatched
work really does fail silently, so independent verification is not paranoia. It also
weakens G's *cost estimate*: a facet whose historical delivery rate is 77% is not the
cheap "one supervised run" I described, and the fork I named inside G — is a fully built
facet with zero pull telling you something? — gets sharper, not softer, with this number
in hand.

**An honest note on shape.** This tree has eight facet branches because the facet table
has eight facets and each had something real to say — but four of them say *shrink*, and
one says *cut a release*. If that reads as thin, the honest reading is that the project
has more finished and unexercised facets than active ones, and the real work is
convergence rather than another direction.

---

## 8. Owner gate

Pick one or more branches (or amend the tree). Nothing has been written to the Vision, no
cards created, no backlog reordered — the chosen branch feeds `scope-cards`.

**Or dive deeper into one named topic before picking** — the candidates I would offer:
the exact `TERMINAL`-vocabulary change and its four call sites (B1); the convergence
pass's agenda in full, card by card (E); or the single registry query that decides X3.
