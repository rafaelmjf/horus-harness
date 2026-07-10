# Bug: Refresh artifacts leaves an unexplained dirty worktree

## Status

Reproduced on 2026-07-10 against installed `horus 0.0.31`.

## Summary

The dashboard's **Refresh artifacts** action applies `upgrade-project` directly to
the registered project's active checkout. This is functionally correct, but it can
leave tracked generated files uncommitted without explaining their provenance or
honoring the configured workflow policy.

This was observed in `horus-hub`, whose workflow policy was:

```toml
[workflow]
integration = "branch-pr-automerge"
commit = "auto"
merge = "auto"
```

Despite that policy, pressing the button modified the active `main` checkout and
left it dirty. A later agent correctly refused to treat the worktree as closed, but
had to reconstruct whether the changes came from the user, another agent, or Horus.

## Observed changes

The button-generated changes were:

- `AGENTS.md`: managed instruction block v5 -> v7.
- `CLAUDE.md`: managed instruction block v5 -> v7.
- `.claude/settings.json`: refreshed Claude hooks.
- `.codex/hooks.json`: added the checkpoint hook.
- `.horus/PRD.md`: added `horus_min_version: 0.0.26`.

The four instruction/hook files were rewritten within four seconds:

```text
2026-07-09 23:43:56  AGENTS.md
2026-07-09 23:43:57  CLAUDE.md
2026-07-09 23:43:59  .claude/settings.json
2026-07-09 23:44:00  .codex/hooks.json
```

The PRD was subsequently edited by a continuity session, so its later mtime no
longer identifies the original refresh.

## Causal trace

The UI form posts to `/upgrade-project`. `process_upgrade_project` resolves the
registered project and calls:

```python
actions = upgrade.upgrade_project(root, apply=True)
```

That call refreshes instructions, the PRD minimum-version stamp, skills, and hooks.
It does not inspect or apply `[workflow]` commit/integration/merge policy.

The attribution was independently reproduced from clean `horus-hub` `HEAD`:

1. Export clean `HEAD` into a temporary directory.
2. Run `horus upgrade-project --path <temp> --apply --no-skills`.
3. Compare the generated files with the dirty active checkout.

Result:

```text
MATCH .claude/settings.json
MATCH .codex/hooks.json
MATCH AGENTS.md
MATCH CLAUDE.md
```

The temporary PRD diff was exactly the added `horus_min_version: 0.0.26` line.
There is no per-request dashboard access-log entry proving the click timestamp, but
the handler, clustered mtimes, and byte-for-byte clean reproduction establish the
cause.

## Why this matters

- A UI maintenance action creates repository state without making the Git
  consequence clear.
- The next agent cannot safely assume dirty files are generated; it must reproduce
  the generation or risk committing user changes.
- `horus close --check` correctly warns about the dirty checkout, but the refresh
  action provides no direct path to resolve it.
- The behavior contradicts the user's explicit automatic branch/PR workflow policy.
- Silently committing the active checkout would be worse: unrelated or user-authored
  changes could be swept into an automated commit.

Generated assets should remain tracked. They encode repository policy, hooks, and
agent instructions that must propagate to other clones. The fix is lifecycle and
provenance handling, not adding the files to `.gitignore`.

## Recommended behavior

### 1. Preflight before mutation

Inspect Git state and compute the upgrade plan before writing anything.

- If the active checkout has tracked, staged, or untracked changes, do not apply the
  refresh automatically.
- Show a blocked result with the existing dirty paths and the proposed generated
  paths.
- Offer the dry-run command and a **Launch reconciliation session** action.
- Never stash, reset, or include existing changes automatically.

This guard belongs in the mutation path, not only in UI text, because POST clients
can bypass a confirmation dialog.

### 2. Honor workflow policy when the checkout is clean

For automatic commit/integration policies, run the refresh in an isolated branch or
worktree:

1. Fetch and base the branch on the current remote default branch.
2. Apply the refresh.
3. Verify that the diff contains only the paths/actions declared by the upgrade plan.
4. Run `git diff --check` and a second dry run that reports all projections current.
5. Commit, push, create a PR, and merge according to `[workflow]`.
6. Report the branch/commit/PR outcome in the dashboard.

For a manual commit policy, applying into a clean active checkout is acceptable, but
the success screen must explicitly say that tracked files are now uncommitted and
list them.

### 3. Record deterministic provenance

Write an ignored machine receipt such as
`.horus/cache/last-artifact-refresh.json` containing:

- Horus version and timestamp;
- project path and starting commit;
- workflow policy selected;
- action status and generated path;
- before/after content hashes;
- resulting branch/commit/PR, when applicable.

The receipt is supporting evidence, not authority. A later reconciliation command
must still hash/compare the current files before classifying them as generated.

Consider exposing that comparison as a command, for example:

```text
horus upgrade-project --verify-diff
```

It should classify the worktree as generated-only, mixed, unrelated, or clean.

### 4. Make the result visible

Replace the current count-only redirect with a durable result panel, for example:

```text
5 artifacts refreshed in PR #123
```

or:

```text
Refresh blocked: worktree already has 2 unrelated changes
```

Do not generate a prose `.horus/sessions/` note automatically. A machine receipt is
more precise and does not pretend the CLI knows the surrounding session context.

## Suggested implementation order

1. **P0 safety:** dirty-worktree preflight, no mutation when dirty, and explicit
   post-action file list for manual mode.
2. **P1 provenance:** structured upgrade actions with paths/hashes plus an ignored
   receipt and deterministic diff verification.
3. **P2 workflow integration:** isolated branch/worktree, commit, push, PR, and merge
   according to `[workflow]`.

P0 removes ambiguity and prevents accidental mixing without requiring the full GitHub
automation in the first patch.

## Acceptance criteria

- Dirty checkout + dashboard POST: no project files change; response names the
  blocker and proposed refresh paths.
- Clean checkout + manual policy: only planned generated paths change; dashboard
  lists every uncommitted path and the exact next command.
- Clean checkout + `branch-pr-*`/automatic policy: the default checkout is not left
  dirty; generated changes land through the configured workflow.
- Existing staged, unstaged, and untracked files are never committed, stashed,
  reset, or overwritten by the refresh action.
- A post-refresh verification proves the generated files match the installed CLI.
- Partial failure leaves a named recoverable branch/worktree and reports it; it does
  not silently claim success.
- Tests cover the dirty refusal, manual result, automatic workflow dispatch, mixed
  changes, and failure recovery.

## Relevant code

- `horus/dashboard.py`: refresh forms, `process_upgrade_project`, and POST dispatch.
- `horus/upgrade.py`: `upgrade_project` and generated `UpgradeAction` records.
- `horus/config.py`: `[workflow]` policy loading.
- `tests/test_dashboard.py`: current refresh handler coverage.
- `tests/test_workflow_policy.py`: workflow policy behavior.
