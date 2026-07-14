---
date: 2026-07-14T15:58:21
agent: claude
account: work
environment: host
project: horus-harness
status: done
summary: "Tier-0 supervision verbs and continuity hygiene"
---

# Tier-0 supervision verbs and continuity hygiene

## Summary

Claimed and shipped `.horus/backlog/tier0-supervision-verbs.md` (PR #221,
`8a3b4428`): three one-shot CLI verbs replacing the cockpit's mechanical
polling/reinstall tail — no daemon, watcher, router, or policy engine.

1. **`horus merge-watch <sha|pr>`** (new `horus/mergewatch.py`) — resolves a
   PR number/URL or literal sha to its owning repo + exact commit, reads the
   base branch's required-check contexts (falls back to watching every check
   present when protection is unknowable, mirroring
   `integration._has_required_checks`'s permissive stance), then polls
   GitHub's check-runs + legacy commit-status APIs until the watched set
   settles green or red. Emits one line per state change (never a CI-log
   tail); warns (never silently re-targets) if the PR's head moves off the
   pinned sha mid-poll. Exit 0 green / 1 red / 1 timeout.
2. **`horus reinstall <path> --verify <marker>`** (new `horus/reinstall.py`) —
   `uv cache clean <package>` then `uv tool install --force --reinstall
   --python <version> <path>`, then greps the FRESHLY INSTALLED on-disk
   surface (`uv tool dir`'s site-packages, not this process's already-imported
   modules — matters because this verb can be reinstalling its own running
   build) for `marker`. Surfaces a still-ACTIVE known systemd unit
   (`horus-dashboard.service`) as a restart nudge, never an automatic action.
3. **Acceptance cleanup** — `horus datum close --card` previously resolved the
   delivered card against `datum.project` directly, which is the WORKTREE path
   when the run used `--worktree` — so the stamp could land in a worktree
   that's later deleted, or miss a card that only exists in the primary
   checkout's `.horus/backlog/`. Fixed via new `worktree.primary_checkout()`
   (reads `git worktree list --porcelain`, whose main-worktree-first ordering
   is a git guarantee, not a naming-convention hack). New `--remove-worktree`
   flag optionally cleans up the worktree + branch in the same act, but only
   when `worktree.remove_if_merged()` confirms the branch looks merged
   (`[gone]` upstream track, or an ancestor of the fetched default branch) —
   refuses otherwise rather than risking unmerged work.

**Live-verified all three on this machine** (not just unit tests): watched
real PR #220 to green (3 required checks); reinstalled this branch as the
global `horus-harness` tool and confirmed a real marker
(`MergeWatchError`) found in the freshly-installed surface, with the
`horus-dashboard.service` restart note correctly surfacing (it's actually
active on this box) — then restored the global tool back to the released
v0.0.53 afterward so the machine's real install wasn't left pointing at a dev
branch. A real `horus run --worktree` + `datum close --card
--remove-worktree` in a scratch repo stamped the card in the primary checkout
and left the worktree/branch removed.

Then dogfooded the new tool on its own PR: `gh pr merge --auto`, then `horus
merge-watch 221` to watch it settle green and confirm the merge — the exact
loop this verb exists to replace.

## Continuity hygiene (folded into the same PR, separate commit)

- Archived `mobile-terminal-legibility.md` → `.horus/backlog/archive/` (folded
  into `mobile-terminal-ux-hardening`, shipped PR #171; its own banner already
  said not to action it standalone).
- Checked `mobile-terminal-interaction-regression.md` against PR #171: **not
  resolved** — the PR's own body explicitly scopes that card's symptom
  (mobile no-input on the hosted app) as out of scope. Left `in-progress`
  with the finding recorded on the card rather than blind-archiving it.
- Diagnosed and filed `close-self-referential-sha-dirty-tree.md`: the
  v0.0.53 release-consolidation session's commit `50a7548` got a session-note
  bullet appended AFTER it that names `50a7548` itself as one of the session's
  commits — structurally impossible to have committed atomically (the SHA
  doesn't exist until after the commit), and it sat uncommitted on `main`
  until this session. Two gaps: the self-referential-SHA pattern itself, and
  `horus close --commit` never re-checking the continuity tree is clean
  afterward. Proposed both a structural fix and a post-commit clean-tree
  guard; didn't implement it this session (separate card, separate slice).
  Resolved the stray edit by committing it (the content was accurate — the
  gap was procedural, not a content error).

## Key Points

- `worktree.primary_checkout` and `remove_if_merged` reuse signals already
  trusted elsewhere in this codebase (`git worktree list --porcelain`'s
  ordering guarantee; the `[gone]` upstream-track signature `gitstate.py`
  already uses for a merged-and-deleted branch) rather than inventing new
  heuristics.
- Found a real environment trap while live-testing `reinstall`: `uv cache
  clean` can block for minutes behind another `uv` process's lock on the same
  machine (hit this running the verb via `uv run horus reinstall` while other
  `uv run` processes were active) — bumped `reinstall.DEFAULT_TIMEOUT` from
  180s to 300s and documented it as a foreground, user-waited-on one-shot
  timeout, not a best-effort background-probe one. The real fix for MY test
  harness was to invoke the actual installed `horus` binary directly instead
  of nesting through `uv run`.
- Full suite: 1413 passed locally, including the new `test_mergewatch.py`
  (19), `test_reinstall.py` (7), and the `test_worktree.py`/`test_cli.py`
  additions for this PR. Required PR checks (`pytest 3.12`/`3.13`,
  `freshness`) and the exact merge-SHA `main` push all green, reproduced live
  via `horus merge-watch` itself, not trusted from a report.

## Next

- `tui-capabilities-screen` is next in the backlog (see PRD `next_action`):
  a thin TUI renderer over `capabilities.generate_project`, no new data path.
  Bounded, low-ambiguity — inline sonnet-5, no delegation needed.
- `close-self-referential-sha-dirty-tree.md` is open and unclaimed — a good
  small follow-up (medium priority) whenever `horus close`/`closure.py` gets
  touched next.

## Checkpoints (auto-harvested)

- `a141f99` Add tier-0 supervision verbs: merge-watch, reinstall --verify, card-close worktree fix
  Three one-shot CLI verbs that absorb the cockpit's mechanical polling/reinstall
  tail without a daemon/watcher/router:
  - `horus merge-watch <sha|pr>`: polls required checks on the exact pinned sha
    until they settle, one line per state change (not a CI-log tail); exits 0
    green / 1 red / 1 timeout. Warns (never re-targets) if a watched PR's head
    moves mid-poll.
  - `horus reinstall <path> --verify <marker>`: `uv cache clean` + force-reinstall
    from a local path, then greps the freshly-installed on-disk surface (not this
    process's already-imported modules) for `marker`; surfaces a still-active
    known systemd service as a restart nudge.
  - `horus datum close --card` now resolves the delivered card against the
    PRIMARY git checkout (via the new `worktree.primary_checkout`, which reads
    `git worktree list --porcelain`'s guaranteed main-worktree-first ordering),
    not the datum's own `project` path — which is the WORKTREE path when the run
    used `--worktree`. `--remove-worktree` optionally cleans up that worktree +
    branch in the same act, but only when the branch looks merged (`[gone]`
    upstream, or an ancestor of the fetched default branch) — never destructive
    by default.
  All three verified live on this machine: merge-watch against real PR #220
  (all three required checks resolved green); reinstall --verify against a real
  marker (found in the freshly reinstalled tool env, systemd note surfaced
  correctly); a real `--worktree` run closed with `--card --remove-worktree`
  stamped the card in the primary checkout and left the worktree/branch removed.
- `84c3b48` Continuity hygiene: archive folded card, note PR #171 scope, file close-guard bug
  - Archive `mobile-terminal-legibility.md` to `.horus/backlog/archive/` — it was
    folded into `mobile-terminal-ux-hardening` (shipped PR #171) and its own
    banner says not to action it standalone.
  - `mobile-terminal-interaction-regression.md`: checked against PR #171 and
    confirmed it did NOT resolve this card — the PR's own body scopes symptom 2
    (this card's mobile-no-input bug) explicitly out of scope. Left `in-progress`
    with the finding recorded, not blind-archived.
  - File `close-self-referential-sha-dirty-tree.md`: a real close/consolidate gap
    diagnosed from the cockpit — a step appended a bullet naming its OWN closing
    commit's SHA (50a7548) into the session note that commit closes, which can
    never itself be committed (the SHA doesn't exist until after the commit), and
    `horus close --commit` never re-checks the tree is clean afterward. Proposes
    a structural fix + a post-commit clean-tree guard.
  - Records the above bullet properly (its content was accurate; the gap is
    procedural) so this session note stays complete, resolving the stray
    uncommitted edit item A/B surfaced this bug.
- `8a3b442` Merge pull request #221 from rafaelmjf/feat/tier0-supervision-verbs
  Tier-0 supervision verbs: merge-watch, reinstall --verify, card-close worktree fix
- `37b3eef` Update Horus continuity (closure)
