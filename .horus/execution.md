---
status: completed
current_feature: "Usage-limit survival kit (backlog #1): worker-aware emergency state-save + horus run usage preflight + PreToolUse usage guard — one delegated phase (claude/personal, Opus 4.8, full-auto, worktree)."
supervisor_tier: frontier
worker_tier: frontier
delegation_basis: "High volume (three sub-features across usage modules, native_hooks, cli, adapters + tests), low ambiguity once the design below is pinned, deterministic pytest gate. Delegation buys context hygiene; supervisor keeps the hook-guard invariant review and the rescue git-safety review. Work account is at its window edge (resets 21:10 Berlin), so the worker runs on personal/Opus per Rafa."
last_updated: 2026-07-04
---

# Execution Plan — usage-limit survival kit

Single delegated phase: the three sub-features share one seam (usage reading,
hook installation, run launch path) and land together as one PR.

## Active Phases

| phase | status | difficulty | mode | worker_agent | worker_tier | delegation_basis | handoff_note | review gate |
|---|---|---|---|---|---|---|---|---|
| survival-kit | merged (PR #115 → v0.0.25; one bounce: no-upstream rescue push; supervisor reproduced CI green on 8319e4e + three live probes incl. sentinel-suppression cross-check; main push CI green post-merge) | medium-high | delegated | claude (account personal, model opus, posture full-auto, worktree) | frontier | see frontmatter | `.horus/temp/survival-kit.md` (worker creates in worktree) | full pytest suite green (required CI on the PR) + supervisor live probes: (1) `horus run` preflight warn/refuse against a faked usage report, (2) guard hook rescue-commit in a scratch worker worktree, (3) main-checkout rescue ref leaves index/worktree untouched |

## Phase spec — survival-kit

Backlog #1. Evidence: two workers died at the usage limit mid-run (2026-07-03,
2026-07-04) with uncommitted code. Three sub-features, all deterministic and
hook-side (zero model tokens):

### (a) Cached usage snapshot (shared substrate)

- A small helper (own module `horus/usage_snapshot.py` or similar) returning the
  freshest usage percent for a target agent+account, with a **file cache under
  `~/.horus/cache/`, TTL ~60s** (key: agent + account alias or "default").
- Claude: `claude_usage.latest_usage` honoring the account's isolated
  `CLAUDE_CONFIG_DIR` mapping (see `horus account`); Codex: `codex_usage`.
- Any failure (no creds, network, timeout ≤5s) → `None`. Never raise, never block.

### (b) `horus run` usage preflight

- Before spawn/resume in `cmd_run`, for claude/codex adapters only (the fake
  adapter is exempt — tests depend on it), read the **target account's** usage.
- 5h window ≥80%: print a warning (percent + reset time), continue.
- ≥95%: **refuse** with exit 2 naming the reset time; `--force` proceeds anyway.
- Unreadable usage: proceed silently (preflight is best-effort, never a wall).

### (c) PreToolUse usage guard + emergency state-save

- New hook command (suggest `horus usage guard --hook`; reuse `usage check`
  internals where sensible), installed as a **PreToolUse** hook for Claude and
  Codex via new `install_*` functions in `native_hooks.py`, wired wherever the
  existing usage hooks are wired (init / upgrade-project / hook sync). Follow the
  existing marker-comment merge pattern so old configs update cleanly.
- Behavior on each fire, reading the cached snapshot (a):
  - **≥90%** (existing advisory threshold): inject an `additionalContext`
    advisory — once per re-arm window (reuse the `closure_already_fired`-style
    marker pattern) so it doesn't nag every tool call.
  - **≥97%** (emergency threshold): perform the **emergency state-save**, once
    per session/window, then inject context saying state was rescued and the
    agent should wrap up. **Never deny the tool call, never force a closure.**
- Emergency state-save, worker-aware:
  - **Worker context** (linked git worktree — `git rev-parse --git-common-dir`
    points outside the checkout — or the env marker below): rescue-commit the
    FULL tree (`git add -A`) to the current branch with a clear
    `horus rescue:` subject, then best-effort `git push` (failure tolerated,
    reported in the injected context). Disposable branch ⇒ product code safe.
  - **Main checkout**: commit **only `.horus/**`** to a rescue ref
    `refs/horus/rescue/<UTC-timestamp>` built with a **temporary index**
    (`GIT_INDEX_FILE`) — the user's index, HEAD, and working tree must be
    untouched. No push. Nothing staged, nothing checked out, no reset ever.
- Adapter env marker: `SpawnSpec` spawns export `HORUS_RUN_SESSION_ID` (and
  `HORUS_RUN_WORKER=1` when `--worker`) in the child env for claude/codex
  adapters, giving hooks a deterministic worker signal; linked-worktree
  detection stays as the fallback for sessions not launched via `horus run`.

### Hard requirements (hook-guard invariant — supervisor will review these)

- Hook commands signal via **stdout JSON + exit 0**, always — including every
  failure path. Per-OS silence guards (`|| exit 0` POSIX/Git Bash; the PS
  5.1-safe probe pattern for Codex Windows) on every committed command string,
  exactly like the existing hooks in `native_hooks.py`.
- The only guaranteed spelling is the `horus` console script.
- PreToolUse must be fast: cache hit is the hot path; cache-miss fetch timeout
  ≤5s; on any error, silent pass (exit 0, no JSON needed).
- Three OS targets. Forward-slash paths in anything written to JSON/TOML.

### Fences

- Do NOT touch: `dashboard.py`, `runlog.py`, `worktree.py`, `registry.py`
  reconciliation, `PRD.md`, hub-related surfaces.
- Do not change the existing 90% Stop/UserPromptSubmit advisory semantics —
  (c) adds PreToolUse coverage beside them.
- Keep the version bump OUT of this phase (release is supervisor mechanics).

### Gate (worker runs, supervisor reproduces)

```
uv run python -m compileall -q horus tests && uv run pytest -q
```

Expected: full suite green. Baseline: main is green (push CI success on
97b7ff6, 2026-07-04). New tests required: snapshot cache TTL + failure paths;
preflight warn/refuse/`--force`/fake-exempt; guard JSON shape + re-arm marker;
rescue-commit in a scratch worker worktree; main-checkout rescue ref leaving
index/HEAD/worktree byte-identical (tmp git repos, no network).
