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
