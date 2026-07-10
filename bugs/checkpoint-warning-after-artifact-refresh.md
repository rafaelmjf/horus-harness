# Bug: Checkpoint warning cannot identify dashboard-generated artifact changes

## Status

Confirmed on 2026-07-10 with `horus 0.0.31`. This is a downstream symptom of
`bugs/refresh-artifacts-leaves-dirty-worktree.md`, not evidence that the checkpoint
gate itself is incorrect.

## Symptom

After **Refresh artifacts** modified five tracked files in `horus-hub`, the Stop hook
reported:

```text
[Horus checkpoint] This session is ending with 5 uncommitted change(s) in the
working tree; commit before closing ...
```

That count exactly matched:

- `.claude/settings.json`
- `.codex/hooks.json`
- `.horus/PRD.md`
- `AGENTS.md`
- `CLAUDE.md`

The refresh action generated the initial changes. A later continuity session also
edited `.horus/PRD.md`, making the final state mixed: four purely generated files and
one file containing both a generated version stamp and authored continuity changes.

## Current behavior

`closure.checkpoint_gate` runs `git status --porcelain`, counts every non-empty line,
and emits the generic uncommitted-change warning. `_checkpoint_hook` then renders
that finding through `CHECKPOINT_ADVISORY`.

This is correct safety behavior:

- tracked generated assets still need committing and propagation;
- the hook must not assume a dirty file is safe merely because Horus can generate a
  similarly named file;
- suppressing generated files would allow real edits inside managed or mixed files
  to be stranded;
- the hook is advisory, not blocking.

The hook does not normally emit on every immediate Stop event. It writes a
per-session checkpoint sentinel and re-arms after `REARM_SECONDS` (currently 1800
seconds), so an unresolved dirty tree can produce the warning again after 30 minutes.

## Problem

The warning has no provenance. It cannot distinguish:

1. changes created by the dashboard refresh;
2. ordinary user/agent changes;
3. a mixed file containing both generated and authored changes; or
4. generated changes that have drifted since the refresh.

Consequently, the message is accurate but low-actionability. A user who just clicked
Refresh artifacts sees a generic warning without being told that the dashboard caused
the dirty state or how to reconcile it safely.

## Recommendation

### Fix the producer first

Implement the dirty-worktree preflight and workflow-aware integration described in
`bugs/refresh-artifacts-leaves-dirty-worktree.md`. With an automatic branch/PR policy,
a successful refresh should not leave the default checkout dirty, so this warning
should not occur in the normal path.

Do not weaken `checkpoint_gate` to compensate for the producer bug.

### Add provenance-aware classification

If refresh writes the proposed ignored machine receipt with starting commit, paths,
and before/after hashes, checkpoint handling can classify each dirty path by comparing
its current hash and diff with the receipt:

- `generated-exact`: current content exactly matches the recorded generated output;
- `generated-plus-authored`: a generated path changed again after refresh;
- `unrelated`: not declared by the receipt;
- `receipt-stale`: starting commit or expected baseline no longer matches.

The receipt is evidence only. Classification must fail closed to ordinary dirty when
hashes, baseline, or repository identity do not match.

### Improve the advisory, not the verdict

Examples:

```text
[Horus checkpoint] 5 uncommitted changes remain: 4 match the artifact refresh from
v0.0.31; .horus/PRD.md also has later edits. Reconcile or commit them before closing.
```

```text
[Horus checkpoint] 5 uncommitted Horus-generated artifact changes remain from the
dashboard refresh. Workflow policy is branch-pr-automerge; the refresh did not finish
integration. Resume or repair that operation before closing.
```

The finding remains `warn`, still contributes to `close --check`, and still re-arms
normally until the repository reaches a committed checkpoint.

## Acceptance criteria

- A plain dirty repository with no valid receipt retains the current generic warning.
- An exact generated-only diff is identified as generated but is still warned about.
- A generated file modified after refresh is identified as mixed and is never treated
  as safe or clean.
- An unrelated dirty path is always reported, even when a valid refresh receipt exists.
- A stale, malformed, cross-repository, or hash-mismatched receipt is ignored safely.
- Automatic refresh integration that completes successfully leaves no dirty checkout,
  so the checkpoint hook stays silent.
- Failed automatic integration reports the recoverable branch/worktree or PR in the
  checkpoint advisory when that data is available.
- Existing sentinel/re-arm and warn-versus-block behavior remains unchanged.

## Relevant code

- `horus/closure.py`: `checkpoint_gate` dirty-tree finding.
- `horus/cli.py`: `_checkpoint_hook` and sentinel handling.
- `horus/native_hooks.py`: `REARM_SECONDS` and checkpoint sentinel storage.
- `horus/templates.py`: `CHECKPOINT_ADVISORY`.
- `tests/test_checkpoint_hook.py`: warning and re-arm coverage.
- `tests/test_closure.py`: dirty-worktree gate coverage.
