---
name: fleet-curation
description: >-
  Review and clean a portfolio of Horus projects from a fleet-curator workspace.
  Use when the user asks what remains valuable across projects, wants stale or
  obsolete backlog archived, wants a project placed on hold, or explicitly opens
  Fleet Review in the TUI. Reads the remote-authoritative horus fleet --review
  digest first, keeps remote shipped truth separate from local work, and requires
  owner approval before changing target-project continuity.
---

<!-- horus-skill-version: 1 -->

# Fleet curation

This is an occasional portfolio-maintenance workflow, not an overseer required for
ordinary delivery. Direct project sessions remain the default.

## Review

1. Fetch the curator workspace, verify its branch against origin, and run
   `horus fleet --review`. Treat REMOTE SHIPPED TRUTH as canonical. Treat LOCAL
   WORKING STATE as a separate warning/provenance layer; never silently combine it
   with remote continuity or pull a target worktree.
2. Use the shared manifest only for project identity and lifecycle. Project code,
   PRD, backlog, capability ledger, and closure stay in the target repository.
3. Read a target PRD/card only after selecting that project. Judge value from the
   owner's current workflow and already-shipped capability; do not manufacture a
   score, ranking, model choice, or automatic archive plan.
4. Present a concise recommendation with explicit buckets: continue now, defer
   until a named trigger, retire because shipped/obsolete/no consumer, or keep as
   optional history. Ask the owner before applying target-project changes.

## Apply an approved cleanup

1. Enter each approved target repository separately. Fetch all remotes, verify the
   current branch against origin/default, read its PRD, and honor its instructions
   and CLI version floor.
2. Continuity-only cleanup may archive complete cards with rationale and update the
   PRD/status. Preserve card content and provenance. Never delete history merely to
   make a queue small.
3. Any source implementation leaves curator mode: use the target project's normal
   execution decision, feature branch, deterministic gate, PR, and continuity close.
4. Keep each repository at a green committed-and-pushed checkpoint. Do not make a
   cross-repo mega-commit, auto-dispatch work, or change external infrastructure
   without separate owner authority.

## v2 six-lane projects (fallback)

The fleet-review command may report remote continuity unavailable for a project
that has no PRD yet. If that project is selected, read its remote
`project.md`/`roadmap.md`/`features.md` lanes explicitly and apply the same
remote-vs-local separation. Any approved cleanup follows that project's six-lane
closure rules; migration to PRD structure is separate and opt-in.

## Close

Record only durable fleet-level decisions in the curator workspace. Do not copy
project facts into it. Refresh its PRD/session summary and push the checkpoint; the
next review should be reproducible from the manifest plus target remotes.
