---
status: open
priority: high
readiness: shaping
readiness_reason: "Fresh-context no-change/revise/reconsider review remains an attended owner decision."
created: 2026-07-19
last_refined: 2026-07-19
vision_facet: "Introspection & self-improvement"
phase: explore
tier: medium
type: chore
parallel: safe
created_by: owner
surface: .horus/backlog/review-session-control-calibration.md, horus/launch.py, horus/routines.py, horus/skills.py, horus/terminal_tui.py, .agents/skills/*, .claude/skills/*
---

# review-session-control-calibration — independently review the controls learned in the first Codex session

## Why

The first substantial Codex session on horus-harness exposed several places where
otherwise useful Horus process guidance became ambient friction. Claude Code had handled
the same general workflow smoothly, while Codex tended to interpret imperative context
literally and execute the apparent sequence immediately. That speed may be a useful model
characteristic rather than a defect; the failure was that the surrounding contracts did
not distinguish context, authorization, backlog delivery, and optional process clearly
enough for both behaviors.

The session corrected the observed problems and shipped them in v0.0.70. Those corrections
were made with the full conversational context available, so they now need one independent
fresh-context review before being treated as settled input to any later model decision map.

## What happened and what was decided

### 1. Resume context was mistaken for authorization

The authored resume handoff listed a skill rewrite, testing, release, and deployment. Codex
treated the sequence as an instruction and one-shotted it instead of using it as orientation.
The deeper issue was not raw speed: the generated resume prompt used imperative language and
did not contain a stop boundary.

**Decision (#358):** normal resume prompts authorize fetch/branch verification and minimum
context reads only. They then require the fresh session to summarize its understanding and
ask permission before editing, testing, dispatching, merging, releasing, or deploying.
Continuity may suggest a release with reasons, but may never order or chain one; release
confirmation is separate.

### 2. Delegation analysis loaded without an owner request

`execution-decision` metadata said to use it at ordinary feature/fix planning boundaries and
whenever `execution_recommendation` needed setting. `horus-consolidate` reinforced that path,
so merely planning inline work loaded a delegation rubric that had no job in the session.

**Decision (#359):** `execution-decision` is owner-invoked only. Building, fixing, reviewing,
planning, or filling `execution_recommendation` does not trigger it. Continuity defaults to a
direct `continue-as-is` reason; the delegation skill loads only when the owner explicitly asks
whether or how to delegate or requests a worker/subagent plan.

### 3. Inline batch confused backlog cards with incidental findings

Inline batch correctly required each real, self-contained backlog card to travel through its
own PR. It incorrectly extended that ceremony to small ad-hoc findings discovered during the
same audit/calibration session, causing a single fix to be committed, opened as a PR, and
merged before the owner could continue touching the same generator and skill files.

**Decision (#359):** classify the unit first. Existing or owner-approved independently
schedulable backlog cards keep the one-card/one-PR path. Related ad-hoc findings accumulate as
green named commits on one pushed batch branch, with no manufactured card or PR per finding.
Promote a finding only when it is deferred, expands the batch materially, needs independent
acceptance/prioritization, or should become dispatchable later.

### 4. A direct mode was missing

The useful contrast appeared to be three distinct postures, not one universal amount of
process. Standard fits one defined delivery; Inline Batch fits several cards or related
findings in one warm recoverable campaign; Codex's fast literal style can also be valuable
when the owner wants minimal orchestration.

**Decision (#360/#361, v0.0.70):** add **All Gas No Breaks**. Its explicit launch selection
authorizes direct work on the current request or authored handoff without a preflight
permission ceremony, and suppresses automatic Horus decision/planning/curation workflows.
It does not expand authority or remove delivery safety: exact-commit gates, proportional live
probes, repository git policy, and explicit authority boundaries remain. Releases, session
closure, pauses, and handoffs still require canonical Horus continuity. The TUI now shows a
spaced summary beneath all three choices.

## Action — fresh-context review only

In a fresh agent context, read `PRD.md`, this card, and the delivered evidence in PRs
#358–#361 / v0.0.70. Review whether:

1. each issue is attributed to the correct contract rather than to model preference alone;
2. Standard, Inline Batch, and All Gas No Breaks now have distinct, internally consistent
   meanings;
3. the normal resume consent boundary and the All Gas direct-resume exception coexist
   without ambiguity;
4. delegation remains explicitly owner-invoked in every consumer;
5. hard-boundary continuity and deterministic delivery safety survived the simplification.

Do not implement changes during this review. Return a concise verdict and the evidence behind
it. Only after owner approval should any accepted gap become a bounded follow-up edit/card.

## Exit / acceptance

The fresh review ends in one explicit verdict recorded under `## Reviews`:

- **no-change** — the four decisions are coherent and the card can be closed;
- **revise** — name the exact conflicting text/behavior and propose the smallest bounded
  follow-up, without implementing it; or
- **reconsider** — identify which decision is invalid and what fresh evidence overturned it.

The review is complete only when it checks both Claude and Codex projections plus the TUI
launch/resume wiring; a prose-only opinion without inspecting the shipped surfaces is not the
requested fresh-context test.

## Non-goals

- No implementation, skill rewrite, launch-mode change, release, or decision-map update.
- No broad audit of unrelated Horus skills or the full product surface.
- No conclusion that one agent style is globally better; preserve the possibility that
  different models earn different postures for different use cases.

## Source

Owner-requested close-out card from the 2026-07-19 Codex session; delivered evidence is PRs
#358–#361 and release v0.0.70.

## Reviews

### Independent fresh-context review — 2026-07-19 (Claude, All Gas session)

**Verdict: `revise`.** The four v0.0.70 decisions are individually well-attributed and the
delivery-safety floor survived, but the shipped controls have two concrete gaps: an internal
contradiction inside the All Gas resume prompt, and session modes existing only on the TUI
surface. Both are bounded. The addendum's continuity-axis simplification is corroborated by
the code, but is larger than the smallest coherent change and should follow separately.

Surfaces inspected: `horus/launch.py`, `horus/routines.py` (diff of #358 and #360),
`horus/skills.py`, `horus/terminal_tui.py`, `horus/closure.py`, `horus/config.py`,
`horus/cli.py`, `horus/dashboard.py`, `horus/terminal_app.py`, both `.claude/skills/` and
`.agents/skills/` projections, and `CLAUDE.md` / `AGENTS.md` / `horus/templates.py`.
`uv run python -m pytest` over the six touched test modules: **188 passed**, so every finding
below is a scope/coverage gap on a green tree, not a broken behavior.

**1. Attribution is correct for issues 1–3, thinner for issue 4.** Each of the first three
names the specific under-specified text rather than blaming model preference — the imperative
`next_prompt` with no stop boundary, `execution-decision`'s over-broad trigger metadata,
inline batch's failure to classify the unit. Issue 4 ("a direct mode was missing") rests on a
single Codex session and is a posture judgment rather than a contract defect; the card's own
non-goals already preserve that, so this is a note, not an objection.

**2. Mode meanings are distinct inside the TUI, but modes do not exist outside it.**
`launch.mode_preamble` and `stop_before_execution=False` are referenced **only** from
`horus/terminal_tui.py:2596,2602`. `grep session_mode` returns nothing in `horus/dashboard.py`,
`horus/cli.py`, `horus/terminal_app.py`, or `horus/launcher.py`; those surfaces all call
`routines.resume_prompt(root)` at its `stop_before_execution=True` default
(`terminal_app.py:99`, `dashboard.py:1564,4151`, `cli.py:705,737,2250`). This contradicts
`launch.py`'s own module docstring, which claims "exactly one launch path … regardless of
whether the trigger was a terminal command or a click," and it means a dashboard or
`horus open --mode resume` launch silently gets Standard's contract with no way to express a
mode. It also cuts against the Dashboard/cockpit facet DoD (launch/resume any project from
web or phone).

**3. The consent boundary and the All Gas exception genuinely conflict — smallest bounded
fix.** In All Gas, `routines.py` frames the authored handoff as "Authored handoff:" and closes
"Proceed directly with the in-scope work." But the managed block (`CLAUDE.md:31-34`,
`AGENTS.md:32-34`, `horus/templates.py:42-44`) instructs every consolidation to *author*
`next_prompt` text that itself says "ask permission before editing, testing, dispatching,
merging, releasing, or deploying" — and the current `PRD.md` `next_prompt` does exactly that.
So an All Gas resume delivers a wrapper saying proceed around a payload saying stop. Observed
live: this session was launched All Gas, read that contradiction, and deferred to the payload,
stopping for permission — the mode's stated purpose was nullified by continuity prose it does
not control. The bounded fix is to make the two authorship rules aware of each other: either
the All Gas wrapper explicitly supersedes an embedded ask-permission clause, or the managed
block stops baking the consent sentence into `next_prompt` and leaves consent to the wrapper
that knows the mode. Recommend the latter — one authority for consent, chosen at launch.

**4. Delegation is owner-invoked in every consumer, with one wording snag.**
`execution-decision`'s frontmatter (`horus/skills.py:1124-1136`) is unambiguous, and
`horus-consolidate` disclaims the trigger at two points (`:199`, `:307`, mirrored in both
projections). The exception is `horus/skills.py:619`: "Before creating `execution.md` or a
worker handoff, apply `execution-decision` and its shared rubric" — an unqualified imperative
of exactly the shape that caused issue 1. Entering `horus-execution` is itself owner-invoked
so the practical risk is low, but the sentence should be conditioned for consistency.

**5. Hard-boundary continuity and delivery safety survived.** Both mode skills retain branch/PR
policy, exact-commit gates, live probes, and hard-boundary consolidation; the two projections
are byte-identical (`diff` clean for both skills). Separately, the addendum's claim that
`continuity_granularity` is a colliding third axis is **confirmed in code**: it is live at
`config.py:71`, `closure.py:84-99,341,369`, `resume_preflight.py:104`, `cli.py:2867,3430`, and
the TUI settings pane — and *neither* mode skill consults it, while both restate the
hold-to-hard-boundary rule unconditionally. The axis is real, redundant, and safe to remove on
the evidence; but it is a wider change than findings 2 and 3, so it should be its own card
rather than part of the minimal revision.

**Proposed follow-ups, smallest first (not implemented, pending owner approval):**

1. Resolve the All Gas consent contradiction (finding 3) — one authority for consent.
2. Plumb `session_mode` through the non-TUI launch surfaces, or explicitly scope modes to the
   TUI and correct `launch.py`'s docstring (finding 2).
3. Condition the `horus-execution` delegation sentence (finding 4).
4. Separate card: remove the `continuity_granularity` axis per the addendum (finding 5).

The TUI launch-form collapse proposed in the addendum is orthogonal to this verdict and needs
no finding here; it is a UX consolidation the owner can authorize independently.

### Follow-up session context — 2026-07-19

The next owner/Codex session revisited the same control surface while testing the shipped
desktop new-window launch. No implementation followed; the owner agreed that the later
fresh-context review should consider these decisions together with the first session:

- **Remove continuity as a separate configurable axis.** The global
  `handoff | delivery | manual` setting collides with launch modes: Inline Batch inherently
  requires handoff-style batching, while All Gas restates the same hard-boundary rule even
  though its distinct purpose is directness and suppression of optional process. The intended
  simplification is one universal invariant: git/PR evidence preserves deliveries between
  boundaries, and canonical continuity is consolidated once at a real pause, session end,
  agent/account/machine handoff, release, or dispatch boundary that needs durable context.
  Remove the TUI setting, user configuration, project-frontmatter override, and conditional
  hook/PR-gate behavior rather than adding per-session override machinery.
- **Keep the three launch modes focused on working posture.** Standard is one bounded delivery
  with normal repo-guided execution and applicable workflows; Inline Batch is several related
  cards/findings in one warm recoverable campaign; All Gas works directly from minimum context
  and avoids automatic planning, delegation, grooming, curation, audits, manufactured cards,
  execution plans, retrospectives, and session notes unless explicitly requested. All modes
  retain branch/PR/exact-gate/live-probe safety and the universal hard-boundary consolidation.
- **Collapse the post-account TUI launch flow into one review form.** After the owner selects
  fresh/resume/card and an account, show model, reasoning effort, session mode, and permission
  posture together with Launch focused by default. Persist an explicit per-agent profile only
  when the owner selects `Save as defaults`; occasional overrides apply to one launch. Keep
  window behavior in Settings because it is an environmental desktop/mobile preference.
- **Show help on demand, not permanently.** The compact review form shows only selected values
  with radio markers. Entering a row expands its alternatives and their concise descriptions;
  selecting or collapsing returns to the compact form. Mode help must define "guided workflow,"
  enumerate Inline Batch hard boundaries, and name the optional ceremony All Gas suppresses.
- **Use official model names with manually maintained purpose copy.** Do not expose Horus aliases,
  scrape provider docs at launch, or promise automatic discovery that the native CLIs do not
  provide. Claude family selectors may continue to target the provider's latest family member,
  while Horus updates displayed standard names and short provider-grounded intended-use text
  deliberately when model releases change. An unavailable remembered model falls back visibly
  to the agent default.
- **Keep scheduled work separate.** Autonomous scheduled workers do not use this attended TUI
  form or its Standard mode; their one-card behavior remains owned by the dispatch envelope and
  supervisor contract.

The independent review should therefore evaluate both the already-shipped v0.0.70 controls and
this proposed simplification. A `revise` verdict should identify the smallest coherent change;
this addendum is context, not authorization to implement it.
