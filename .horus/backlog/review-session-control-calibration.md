---
status: open
priority: high
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

- Pending the requested independent fresh-context review.

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
