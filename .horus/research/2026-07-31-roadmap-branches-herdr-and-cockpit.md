# Roadmap branches (v5 re-run): host-native cockpit — 2026-07-31

**Intent:** deepen-own-use. **Same inputs as the rejected tree earlier today** — the
difference is the skill, not the evidence.
**Supersedes:** `2026-07-31-roadmap-branches-rebaseline.md` §8 (owner rejected all four
branches for being assembled from the backlog). A/C/D from that tree are NOT rebuilt here.

## 1. Where we are

Facet standings and life-stages: see the audit (`.horus/audits/2026-07-31-product.md`)
and the prior tree §1 — not restated.

**What changed since that tree:** the owner named the direction it missed —
*customising herdr to fit daily use, and improving the TUI* — and that direction had
almost no cards, which is exactly why a backlog-derived tree could not see it.

**Position in one line:** the engine is proven, the cockpit is the differentiator, and
the cockpit is currently **maintaining a parallel copy of state its own host already
publishes** — while getting that copy wrong on 56% of sessions.

## 2. Where the market is

From the scan receipt, once: three teams reached repo-local continuity independently,
none adoptable here; the platform moved up into session views (`claude agents`).

**Corrected verdict.** The scan said *session host: KEEP-THIN, do not deepen*. That was
a market instinct ("don't rebuild someone else's tool") applied to an own-use question,
and it is **wrong**: herdr carried 11 of 26 sessions since v0.0.78, making it the
most-adopted thing shipped recently. The right reading is not "don't deepen" but **"go
further into the host, and take LESS onto Horus"**.

**Risk:** herdr is a third-party dependency at v0.7.5 with a JSON API and no stability
promise Horus has verified.

## 3. The tree

```
Horus v0.0.79 (+21 unreleased) — cockpit is the moat, and it duplicates
state its own host already publishes, incorrectly, on 56% of sessions.
│
├── H  Adopt herdr as a STATE source, not just a pane host ... Dashboard/cockpit [primary]
├── W  Push work into herdr's native surfaces ............... Dashboard/cockpit [secondary]
├── P  Close the "no terminal command" half of the DoD ...... Dashboard/cockpit [secondary]
├── S1 Does host-native state generalise to Codex? .......... (no facet)        [cheap]
└── S2 Cross-machine fleet READ ............................ (out-of-scope re-test) [park]
```

All three named branches target one facet. That is not a defect of the tree — it is
what the evidence says: the differentiator and the friction are in the same place.

## 4. The branches

### H — Adopt herdr as a state source, not just a pane host *(primary)*

**Thesis.** Horus maintains a registry that guesses session state, and gets it wrong on
56% of rows. Its own host **already publishes the truth**, live and machine-readable.
Under deepen-own-use, consuming that is strictly better than maintaining a worse copy.

**Evidence (gathered this run, not recalled).** `herdr api snapshot` returns, per agent:

```json
{"agent":"claude","agent_status":"working","cwd":"/home/rafa/projects/horus-harness",
 "focused":true,"pane_id":"w2:p3","state_change_seq":127,
 "terminal_title":"⠂ Dispose of five wildcard branch proposals"}
```

That is agent, **live status**, project, focus, a stable pane id, a change counter for
cheap polling, and a **live task title** — for every herdr-hosted session at once.

**Market position.** *This exists already* — herdr publishes agent state — *but it
misses* Horus's projects, accounts and continuity. *You already have* the registry,
delivery tracking and accounts *but still miss* truthful live state. *Therefore:* read
the host's snapshot and keep only the delta.

**Roadmap.**
1. **Read `herdr api snapshot` for herdr-hosted rows.** Why: `agent_status` is exactly
   what `session-agent-state-awareness` was carded to build, already solved by the host.
   How: one call, keyed by `pane_id` (which Horus already stores as `target_ref`, e.g.
   `w2:p3`); cache on `state_change_seq` so polling is cheap. Weak points: herdr must be
   running (absent server ⇒ fall back to the registry, never an error); v0.7.5 API
   stability is unverified — pin the fields used and treat unknown shapes as absent.
   Non-goals: no screen-scraping, no polling loop in a paint path.
2. **Derive honest end states from presence + intent.** A session absent from the
   snapshot has ended; `termination_reason` says whether the owner ended it. That closes
   the `failed`-vs-`stopped` defect for herdr rows in the same motion as
   `session-close-ux-and-truthful-end-state` closes it for the TUI path.
3. **Show the live task title in the TUI and dashboard.** `terminal_title` is a
   free, per-session "what is it doing" label Horus currently has no way to produce.
4. **Scope the registry to the delta** — projects, accounts, delivery, continuity —
   and stop storing what the snapshot answers better. Findings become their own cards.

**Convergence criterion.** For a herdr-hosted session, every state Horus shows comes
from the host or from something only Horus knows; nothing is guessed. **Cost:** one to
two sessions.

**Implied Vision edits.** None to the facet set. Sharpen **Dashboard / cockpit**'s DoD:
*"…and every state it reports is either true by construction or sourced from the host
that owns it."* This also makes the Vision's existing **native-app-first** principle
("design capabilities on Claude/Codex's own surfaces before a Horus-owned session
layer") apply to *hosts*, not only agent CLIs.

### W — Push work into herdr's native surfaces *(secondary)*

**Thesis.** The same argument as H, applied to verbs rather than state: herdr ships
capabilities Horus either reimplements or lacks.

**Evidence.** Unused by Horus today: `herdr worktree create|open|remove` (Horus builds
its own worktree isolation for dispatch, and carries a `stale-worktree-accumulation`
bug card — 5 dead worktrees on this machine); `herdr notification show` (Horus's only
push is Telegram); `herdr agent prompt` / `send-keys` / `read` (Horus routes remote
prompting through the Telegram input bridge); `herdr api schema` (a declared contract
Horus could pin against).

**Market position.** *This exists already* in the host *but misses* Horus's card and
envelope semantics. *You already have* dispatch, worktrees and Telegram *but still
miss* the cheaper native path. *Therefore:* delegate the mechanics, keep the policy.

**Roadmap.**
1. **Worktrees via herdr** where a herdr host is active — replaces bespoke setup and
   plausibly retires `stale-worktree-accumulation`, since herdr owns the lifecycle.
2. **Native desktop notification** alongside Telegram for on-machine escalations —
   Telegram is the away-mode channel; at the desk it is the wrong instrument.
3. **Evaluate `agent prompt` as a second input path** to a running session. Weak point:
   this touches the "never mints authority" rule — it must inherit the same owner-lock
   the Telegram bridge has, or it is out.
4. **Pin against `herdr api schema`** so a herdr upgrade breaks a test, not a session.

**Convergence criterion.** Horus implements no mechanic the host already provides, and
a herdr version bump is caught by CI. **Cost:** one session, plus one per adopted verb.

**Implied Vision edits.** None. This is the existing "Execution planes own
orchestration; Horus stays the memory/planning plane" boundary, applied one level down.

### P — Close the "no terminal command" half of the cockpit DoD *(secondary)*

**Thesis.** A facet-DoD-vs-delivered-code gap with **zero cards** — invisible to the
rejected tree. Dashboard/cockpit promises *"launches/resumes any project from web or
phone, **no terminal command**"*. Delivered: the hosted dashboard is read-mostly, and
phone access is Termius SSH into the TUI — which is a terminal command. Telegram's
grammar allows bounded mutations (`cancel`/`release`/`supervise`/`warmup`/`answer`) but
**not launch**, deliberately, because it never mints authority.

**Market position.** *This exists already* — `claude agents` and Claude Code on the web
launch sessions remotely — *but misses* Codex, accounts and projects. *You already
have* fleet state on the phone *but still miss* acting on it without a terminal.
*Therefore:* decide whether the DoD is the target or the DoD is wrong.

**Roadmap.**
1. **Decide the honest DoD.** Either launching from phone/web is in (and needs an
   authority model that does not violate the never-mints-authority rule), or it is out
   and the facet text should stop claiming it. Second-order: the authority design is its
   own card if the answer is "in".
2. **If in:** the cheapest real path is a Telegram launch verb bound to an existing
   envelope, since envelopes already encode pre-authorization. Weak point: envelopes
   were designed for dispatch, not interactive launch.

**Convergence criterion.** The DoD and the delivered surface agree — by building or by
rewriting. **Cost:** one decision, then one session if "in".

**Implied Vision edits.** Conditional rewrite of **Dashboard / cockpit**'s DoD to drop
"no terminal command" if the answer is "out".

## 5. Speculative branches

### S1 — Does host-native state generalise to Codex? *(cheap, tests H's premise)*

**Gap.** H rests on herdr publishing `agent_status`. Horus is 50-of-244 Codex all-time,
and the scan never examined Codex's own session surface — a hole flagged and still open.

**Idea.** Check whether herdr's `agent_status` is populated for a *Codex* pane the way
it is for Claude, and whether Codex publishes any equivalent itself.

**Cheapest PoC.** Launch one Codex session on herdr, read `api snapshot`, compare.
Under an hour.

**Why it fits.** H's value halves if it only works for one of two agents.

**Converge/drop.** *Converges* if `agent_status` populates for Codex → H covers both
agents. *Dropped, and H rescoped to Claude-only,* if herdr's detection is
Claude-specific — which the 2026-07-29 probe hinted at, since herdr scrapes Claude's
literal UI strings. **Dying cheap is success.**

### S2 — Cross-machine fleet READ *(park; re-tests an out-of-scope line)*

Carried unchanged from the rejected tree — the Vision excludes multi-machine *control*
while Continuity core's DoD claims *"across machines"*, and the audit could not measure
it. Read-only, no control path. **Converges** if a real cross-machine session shows the
owner guessing at the other machine's state; **dropped** if pushed git already covers it.

## 6. Backlog disposition — done AFTER the branches, per v5

| Disposition | Cards |
|---|---|
| **Into H** | `session-agent-state-awareness` (**largely retired by the host** — herdr already answers it), `session-close-ux-and-truthful-end-state` (new today), `herdr-server-shutdown-fragility`, `session-host-protocol` |
| **Into W** | `stale-worktree-accumulation` (**candidate for retirement** if herdr owns worktrees), `telegram-idea-capture`, `telegram-group-project-topics` |
| **Into P** | `horus-phone-chat-poc`, `tui-fleet-artifact-refresh` |
| **Into S1** | none — deliberately card-free, that is the point |
| **Untouched by this tree** | Everything else — the 47 explore cards, the accounts lane, the calibration lane, the dispatch lane, X4/X5/X6. **This tree does not claim to place them**, and pretending otherwise is what produced the rejected one. If reorganising them is the goal, that is `backlog-refine`, not a divergence tree. |

## 7. Recommendation, held loosely

**H primary.** It is the owner's stated direction, it is backed by evidence gathered
this run rather than inherited, and it makes the cockpit's worst defect a side effect of
a better architecture instead of a separate fix.

**S1 before committing to H's full scope** — under an hour, and it decides whether H is
one agent or two.

**W secondary**, and pleasantly subtractive: two of its items are candidates to *retire*
existing cards rather than add work.

**P secondary but different in kind** — it is a decision, not a build, and it may end in
rewriting the DoD rather than shipping anything. That is a legitimate outcome.

**Park S2.**

**Honest note on shape:** three of five branches target one facet. That is what the
evidence produced, not a failure to diverge — but it is worth the owner knowing that
this tree is *narrower* than the rejected one, deliberately.
