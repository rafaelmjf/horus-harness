---
status: shelved
shelved_on: 2026-08-01
priority: medium
created: 2026-07-30
created_by: owner
readiness: shaping
readiness_reason: "The problem is measured, not suspected — 5 of 6 non-main worktrees on this machine are provably dead, and the friction has already bitten once. What is NOT settled is the shape: whether cleanup is a `horus` verb, a closure-time advisory, or a documented manual command. That is a [session] decision about where the routine lives, not an editorial one."
phase: converge
type: bug
tier: low
parallel: safe
vision_facet: "Distribution"
surface: "git worktree (no Horus code owns this today), horus/cli.py (if it becomes a verb), the closure/consolidate advisory path (if it becomes a signal)"
---

# stale-worktree-accumulation — merged worktrees are never reclaimed, and `git worktree prune` cannot find them

## Why — owner, 2026-07-30

Worktrees accumulate one per dispatched worker and per parallel branch, and
nothing ever removes them. Measured on this machine on 2026-07-30:

| worktree branch | PR | state | commits ahead of main |
|---|---|---|---|
| `bug/delegation-only-execution-trigger` | #437 | **OPEN** | 3 |
| `docs/herdr-session-loss-cards` | #452 | MERGED | 2 |
| `feat-tui-backlog-field-picker` | #287 | MERGED | 1 |
| `worker/campaign-supervision-launch` | none | — | **0** |
| `worker/campaign-supervision-launch-v2` | #265 | MERGED | 1 |
| `worker/provider-model-selector-contract` | #266 | MERGED | 1 |

**Five of six are dead.** #265/#266/#287 are hundreds of PRs behind current
(#453), so these have been stale for weeks. One holds no commits at all.

## The concrete harm, already observed

This is not hypothetical friction. On 2026-07-30, merging #452 with
`gh pr merge 452 --squash --delete-branch` **failed its cleanup step**:

```
failed to delete local branch docs/herdr-session-loss-cards:
  cannot delete branch ... used by worktree at
  /home/rafa/projects/horus-harness-wt-docs-herdr-session-loss-cards
```

So every squash-merge from a worktree silently leaves both the branch and the
worktree behind, which is exactly the loop that produced the table above. The
mechanism is self-sustaining: the cleanup that would have prevented the mess is
the thing the mess breaks.

## The trap — why the obvious fix does not work

Two standard tools both fail here, and a cleanup routine that reaches for either
will either delete nothing or delete something live:

1. **`git worktree prune` is a no-op.** It only removes worktrees whose
   *directory* has disappeared. All six directories exist on disk, so prune
   reclaims none of them.
2. **`git branch --merged` cannot see a squash-merge.** This repo squash-merges,
   which creates no ancestry link. Verified: `docs/herdr-session-loss-cards`
   reports `merged_into_main=0` *minutes after being merged*. Any routine keyed
   on ancestry will conclude every merged worktree is still live and reclaim
   nothing.

So detection has to come from **PR state**, not from git topology —
`gh pr list --head <branch> --state all` returning `MERGED` — with "0 commits
ahead of `origin/main`" as the offline fallback for the no-PR case.

## What to build

A routine that reclaims a worktree only when it is provably dead:

- Its PR is `MERGED`, **or** it is 0 commits ahead of `origin/main` and has no
  open PR.
- Its working tree is clean (`git status --porcelain` empty).
- It has no unpushed commits.

Then `git worktree remove` + delete the local branch.

## Guardrails

- **Never touch a worktree with an open PR** — `bug/delegation-only-execution-trigger`
  (#437) is the live counter-example in the table above, and it is also
  `CONFLICTING`, so it looks stale by every proxy except the one that matters.
- **Dirty or unpushed ⇒ refuse, loudly.** Do not "clean" work that only exists on
  this machine. Reclaiming is a convenience; losing a branch is not recoverable
  from continuity prose.
- **Report, then act.** The first useful version may be advisory-only: print the
  reclaimable list at closure and let the owner run one command. That is cheaper
  than a verb and answers whether the automation is even wanted.
- Worktrees are per-machine and gitignored, so this can never be driven from
  durable `.horus/` state — it is a local hygiene routine by nature.

## Open decisions

- **Where the routine lives**: a `horus worktree prune`-style verb, an advisory
  emitted by `horus close`/`consolidate` alongside the existing staleness
  advisories, or documented manual commands with no code at all. [session] —
  this decides whether Horus grows a git-hygiene surface, which the Vision does
  not obviously hold today.
- Whether it also fixes the *upstream* cause by preferring `gh pr merge` from the
  main checkout rather than from the worktree holding the branch. [refine]
- Whether the no-PR + 0-commits-ahead case is reclaimed automatically or always
  asked about. [refine]

## Source

Observed live during the 2026-07-30 resume session, after `gh pr merge 452
--delete-branch` failed on a worktree-held branch. Owner carded it in the same
session and explicitly deferred the fix, judging the accumulation non-urgent
because every worktree was clean. Related: [[herdr-live-test-stops-owner-server]]
(the same session's "isolation the code claims but does not enforce" theme).
