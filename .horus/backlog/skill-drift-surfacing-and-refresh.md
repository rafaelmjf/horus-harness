---
status: open
priority: low
readiness: shaping
readiness_reason: "Dedicated owner brainstorm must unify detect, preview, refresh, git integration, and remote verification before implementation."
created: 2026-07-17
last_refined: 2026-07-19
tier: medium
type: feature
vision_facet: "Introspection & self-improvement"
parallel: safe
surface: horus-managed project artifacts, upgrade/skill detection, fleet refresh planning, git workflow integration, remote verification
---

# Unified Horus artifact refresh — detect, preview, integrate, verify

Reinstalling or upgrading the Horus CLI does not refresh what Horus previously wrote
inside initialized projects. Bundled skills are the observed failure, but the product
problem is broader: managed instructions, hooks, workflow dependencies, and other
project artifacts can all lag the installed CLI. Detection, update, git integration,
and remote verification currently feel like separate partial operations.

The dedicated shaping session must design one owner-visible lifecycle:

1. **Detect** every Horus-managed artifact that is missing, stale, customized, or
   ineligible for automatic replacement.
2. **Preview** the exact per-project diff and repository workflow before writing.
3. **Refresh** only approved managed assets without overwriting unversioned/customized
   content silently.
4. **Integrate** through the target project's normal branch/commit/push/PR policy.
5. **Remote-verify** that the delivered default branch contains the new artifacts and
   the local checkout is clean and synchronized.

Existing evidence includes:

- The nudge is a passive one-line `tip:` after routine commands that lists every
  bundled skill name without distinguishing "not installed" from "outdated"; it reads
  as an ad and is easy to ignore.
- The launch/resume path does not check at all: a session can be launched in a mode
  whose posture skill is not installed and the mode silently degrades.
- There is no fleet-wide view: after a CLI upgrade, nothing tells the owner which of
  the N registered projects are behind. Only a per-project `horus doctor` shows it,
  and nothing prompts running doctor after an upgrade.
- Two refresh paths are advertised (`horus upgrade-project --apply --target X` and
  `horus skill install --target X`) without one end-to-end contract.

**Evidence (2026-07-17, horus-agent):** a session was launched in `inline-batch` mode
(the launch-mode skill shipped in PR #307 / v0.0.60) but `inline-batch-session` was not
installed in the project, so the mode's posture instructions were silently absent. A
manual `horus skill install --target claude` then created 9 missing skills and updated
4 stale ones (horus-execution v13, delegation-rubric v8, execution-decision v3,
dispatch-decision v3) — none of which had surfaced as an actionable warning in the
normal resume/consolidate/close flow.

The related [[tui-fleet-artifact-refresh]] card already carries a detailed candidate
fleet workflow. It remains Gated on this shaping verdict so the session can decide
whether that card is the implementation, a child, or should be merged here.

## Shaping questions

- Which artifacts are genuinely Horus-managed and how is customization distinguished
  from stale generated content?
- Is there one canonical refresh service with skill-only/project/all projections, or
  separate commands sharing one plan/apply/integrate core?
- Which safety states must skip a project versus pause for an attended decision?
- How should launch-time warnings relate to fleet-wide refresh without becoming noise?
- Does the existing TUI fleet card remain the delivery card after this brainstorm?

## Exit

End the dedicated owner session with one bounded architecture and a disposition for
[[tui-fleet-artifact-refresh]]: merge, rescope as the implementation card, or retire as
duplicate. Then run `backlog-refine` before promoting any delivery card to Ready.

## Non-goals while Shaping

- No narrow warning-only fix before the full lifecycle is understood.
- No silent mass rewrite, auto-stash, force push, or bypass of repository policy.
- No assumption that skills are the only managed artifact that can drift.

## Field evidence — v0.0.73 made the fleet's prose stale (2026-07-19)

The drift this card describes stopped being hypothetical. v0.0.73 (#368) deleted
`continuity_granularity` from the code and rewrote the shared managed block, but only
this repo's block was updated. Every other project still teaches the retired setting:

```
agentic-cv-builder: granularity=1     agentic-ttrpg: granularity=1
agentic-gym-coach: granularity=1      fabric-metadata-driven-medallion: granularity=1
agentic-pbi-utils: granularity=1      fabric-utils: granularity=1
agentic-travel-guide: granularity=1   horus-agent: granularity=1
```

(grep for `continuity_granularity` in each `CLAUDE.md`; the consent sentence from #358
is absent because those blocks predate it — they are stale at *different* versions,
which is itself a requirement: refresh cannot assume one common baseline.)

Impact is moderate, not urgent: behavior is correct everywhere because it lives in
code. The cost is an agent reading a paragraph about a knob it cannot find — the exact
prose-teaching-what-the-code-does-not-do failure #368 removed here.

**Selection is the hard part, not propagation.** `horus upgrade-project` does the write;
deciding *where* is the design question this card owns. Two traps found while surveying:

1. **Worktrees masquerade as projects.** Four `~/projects/horus-harness-wt-*` directories
   report the same staleness, but `git worktree list` shows they are worktrees of THIS
   repo parked on old branches (`feat-tui-backlog-field-picker`,
   `worker/campaign-supervision-launch{,-v2}`, `worker/provider-model-selector-contract`).
   Refreshing them would commit managed-block changes onto stale worker branches. Any
   sweep over a projects directory must exclude worktrees — check `.git` being a file
   whose `gitdir:` points into another repo, not a directory.
2. **Dormant projects should be skipped, not refreshed.** A project on hold does not
   benefit from a block update; that is churn against a repo nobody is touching. This
   needs to compose with `fleet-curation`'s lifecycle state rather than ignore it.

Also note the scale: `horus skill map` reports **126 stale skill installs** across the
fleet at v0.0.73, spanning several versions — so the refresh plan must be idempotent and
resumable, never one big transactional sweep.
