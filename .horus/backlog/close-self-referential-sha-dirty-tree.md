---
status: open
priority: medium
tier: sonnet
created: 2026-07-14
created_by: overseer
parallel: safe
type: bug
surface: horus/closure.py (commit_continuity), horus/cli.py (cmd_close)
---

# `horus close` can strand a dirty tree: a commit can't reference its own SHA

## Observed (2026-07-14, tier0-supervision-verbs acceptance cleanup)

The v0.0.53 release-consolidation session committed `50a7548` ("Consolidate v0.0.53
release and owner verification"), then a later step appended a bullet to that SAME
session note (`.horus/sessions/2026-07-14-144033-release-v0-0-53.md`) listing
`50a7548` itself as one of the session's commits — and never re-committed it. The
edit sat uncommitted on `main` until this session found it.

## Two gaps

1. **Self-referential-SHA is structurally impossible to commit.** Listing "this
   session's own closing commit" inside the continuity note that same commit closes
   is a contradiction: the SHA doesn't exist until after the commit is made, so the
   line documenting it can never be *in* that commit — only in a follow-up one. Any
   closure step that writes a commit's own hash into a tracked continuity file
   guarantees a dirty tree afterward, by construction, not by mistake.
2. **No post-close clean-tree guard.** `horus close --commit` (`closure.commit_continuity`)
   stages and commits whatever continuity diff exists *at that moment* and returns —
   it never re-checks whether the continuity pathspec is dirty again afterward. A
   step that edits a continuity file post-commit (like the self-referential-SHA case
   above) leaves the tree stale with nothing surfacing it; `cmd_close`'s `--check`
   gate mode also only looks at `closure.freshness_gate`/`checkpoint_gate`, neither of
   which re-runs after `--commit`.

## Proposed fix (not just a description — pick one or combine)

- **Break the self-reference structurally**: never write "this commit's own SHA"
  into the note being committed. Either (a) note the commit list up to the
  *previous* commit only, and let the NEXT session's note (or a trailing
  `git commit --amend`-free follow-up) record the closing commit itself, or (b) if a
  session truly wants a self-contained commit list, make it a genuinely two-commit
  closure (content commit, then a tiny second commit appending its own predecessor's
  SHA) instead of a single edit that can never land.
- **Add a post-`--commit` clean-tree guard** in `cmd_close`/`commit_continuity`: after
  committing, re-run `git status --porcelain -- <continuity pathspec>`; if still
  dirty, print a warning (or fail `--check`) naming the stale file(s) instead of
  silently returning success. This is the general-case backstop — it catches this
  bug class regardless of which step caused the residual edit.

## Verification

A fixture that mimics this: commit continuity, then edit a tracked continuity file
again (simulating a self-referential or any other post-commit edit) — `horus close
--commit` (or `--check` run right after) surfaces the residual dirt instead of
reporting clean. Existing `horus close`/`closure.py` tests stay green.
