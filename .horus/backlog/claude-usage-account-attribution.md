---
status: open
priority: high
readiness: ready
readiness_reason: "Root cause is measured, not inferred: the reported number was matched byte-for-byte to a specific org's row in the desktop app's own usage record, and the correct number for the live session was found in the same file. The fix surface is one module, and a local, org-tagged source already exists on disk. Nothing to shape."
autonomy: attended
created: 2026-08-13
created_by: claude
last_refined: 2026-08-13
refine_passes: 1
topic: accounts-isolation
tier: medium
type: bug
parallel: safe
surface: "horus/claude_usage.py (credentials_path/_claude_home, latest_usage, usage_findings); the UserPromptSubmit/Stop/PreToolUse hooks in a project's .claude/settings.json; the overseer==worker advisory in the account-scoped usage path"
---

# claude-usage-account-attribution — usage is read from the CLI login, not the session's account

## Why — measured on disk, 2026-08-13

A `pbi-ecosystem` session running under the **Claude Code desktop app** was told, on every
user turn and on three blocked stop attempts, that its 5-hour usage was at **95%** and it
could be cut off mid-task. The session was actually at **15%**. It spent four turns on
closure pressure that did not apply, and the agent repeated the wrong number to the owner
as fact until the owner corrected it.

The desktop app keeps its own usage record at
`%APPDATA%\Claude\plan-usage-history.json` — `{version: 2, samples: [{t, org, u:{fh, sd}}]}`,
sampled roughly every five minutes and **tagged by org**. Both accounts are in it:

| org | samples | last sample | 5h | weekly |
|---|---:|---|---:|---:|
| `ceeaba38…` (= `rafamjf@gmail.com`, the ambient CLI login) | 2527 | 18:40:43 | **95%** | 66% |
| `39b76ea7…` (the account the live session was running under) | 157 | 19:07:14 (live) | **15%** | 26% |

`horus usage check --target claude` reported `5h 95%, weekly 66%` — an exact match for
`ceeaba38`, whose last sample predates the account switch at ~18:44.

## Root cause

`claude_usage.credentials_path()` resolves to `$CLAUDE_CONFIG_DIR/.credentials.json`, else
`~/.claude/.credentials.json`. Both are **Claude Code CLI** login state.

Under the **desktop app** the session's account is not recorded in either. The app can be
signed into a different account than the CLI, and switching accounts in the app does not
touch the CLI's credentials — `~/.claude/.credentials.json` was last written at 18:27, before
the switch, and nothing updated it.

Horus then reads a perfectly valid token, receives a 200 from the OAuth `/usage` endpoint,
and reports the answer with full confidence. **There is no check that the account behind the
token is the account the session is running under.** The failure is silent by construction:
every signal Horus has says success.

`--account` does not rescue it. On this machine:

- `--account claude-personal` → also 95% (it maps to the same underlying account), **and**
  emits `overseer==worker: 'claude-personal' is the account this session runs under` — an
  inference from ambient config stated as measurement, and wrong here. A dispatch routed on
  that basis goes to the wrong account.
- `--account claude-work` → no reading available (its isolated dir cannot authenticate).
- `CLAUDE_CONFIG_DIR` is **unset** in the hook subprocess, so the ambient fallback is what
  actually runs.

The hooks in the affected project pass no `--account` at all:

```
UserPromptSubmit -> horus usage check --target claude --hook --threshold 90 || exit 0
Stop            -> horus usage check --target claude --hook --threshold 90 || exit 0
PreToolUse      -> horus usage guard  --target claude --hook || exit 0
```

## The design tension this exposes

`--account`'s own help text says unknown aliases *"fail, never fall back to the ambient
account"* — so silent fallback was already understood to be dangerous, and was closed on the
alias path. The **default** path still has exactly that failure mode, and it is the path the
hooks use.

Sibling of [[codex-isolated-config-leak]]: there an isolated account still points at the
ambient home; here a session's usage is read from the ambient login. Same root shape — an
account-scoped question answered from ambient state.

## What to do

Ordered cheapest-first; rung 1 alone removes the harm.

1. **Fail instead of guessing.** Establish the org behind the token and the org of the
   running session; on mismatch (or when the session's org cannot be determined), report
   *"no usage signal for this session's account"* and let closure logic treat it as no
   signal. The module already degrades silently on a missing token, offline machine or
   schema drift — this is the same contract extended to identity. A wrong number is worse
   than no number, because no number cannot make someone act.
2. **Read the desktop app's record when running under the desktop app.**
   `%APPDATA%\Claude\plan-usage-history.json` is local, needs no token and no network, and
   is **org-tagged**, so it is per-account correct by construction. It would have returned
   15% here. Caveats to carry: it is undocumented internal state (so is the `/usage`
   endpoint already), and it is sampled, so it lags by up to ~5 minutes — acceptable for a
   closure signal, and honest lag beats confident misattribution.
3. **Detect the surface.** `curate.py` and `terminal_tui.py` already reference desktop-app
   paths; `claude_usage.py` has no notion that the desktop app exists. Decide CLI-vs-desktop
   before choosing a source.
4. **Stop asserting `overseer==worker` from ambient config.** Either derive it from the
   session's real account or downgrade it to "cannot determine".

## Acceptance

- With the desktop app signed into an account other than the CLI login, `horus usage check
  --target claude` either reports **that session's** figure or reports no signal. It never
  reports the other account's figure.
- The stop/prompt hooks do not raise closure pressure on a session whose real usage is below
  the threshold.
- A regression check that survives the endpoint: construct the mismatch from fixtures (two
  orgs in a `plan-usage-history.json`, a token resolving to the wrong one) and assert the
  reading is refused rather than attributed.

## Shipped — rungs 1 and 3, 2026-08-14

Rung 3 turned out to be the key that made rung 1 exact rather than heuristic. The
desktop app files every session as
`claude-code-sessions/<accountUuid>/<organizationUuid>/<hostSessionId>.json`, and the
session knows its own id from `CLAUDE_CODE_HOST_SESSION_ID` — so the session's account
is **measured off disk**, not inferred from ambient config or from the most-recent
usage sample. `CLAUDE_CODE_ENTRYPOINT` (`claude-desktop` vs `cli`) selects the surface,
and both vars are inherited by hook subprocesses, so the detection works on the hot
path that actually misreported.

- `claude_usage.Identity` / `session_identity()` / `identity_for_config()` /
  `check_attribution()` — matched on `accountUuid` first, `organizationUuid` as
  fallback. Account-first matters because a `claude_team` org holds several member
  accounts with separate limit pools; org-only matching would call two colleagues the
  same account.
- `latest_usage()` enforces attribution **by default**; an explicit `--account` query
  opts out via `require_session_attribution=False`, since it asks for that account's
  figure and makes no claim about the session.
- `_usage_account()` / `_claude_session_alias()` route the hook and the default check
  to the session's *own* registered account, so the outcome is the session's real
  number rather than merely a refusal. Unregistered account → refusal, as designed.
- `usage_findings()` names identity as the cause instead of blaming token/network.
- Suite-wide: `CLAUDECODE`, `CLAUDE_CODE_ENTRYPOINT`, `CLAUDE_CODE_HOST_SESSION_ID`
  now cleared in `conftest.py` — they leak from a developer's own session into pytest
  and would make attribution tests read live identity and behave differently in CI.

Verified live on 2026-08-14, this machine, desktop session on `ceeaba38` while the CLI
login was `39b76ea7` — the mismatch reproduced with the orgs swapped relative to the
original observation. Same session, same moment: the installed (unfixed) CLI reported
`5h 22%, weekly 49%` (the work account) while the working tree reported the session's
own account. Discriminating hook probe at `--threshold 30`, between the two accounts'
figures: fixed fired the advisory at the session's real 59%, unfixed stayed silent at
the ambient 22%. Full suite: 28 pre-existing local failures before and after, identical
sets — no regressions. 10 new fixture-built tests; `compileall` clean.

**Still open — rungs 2 and 4.** Rung 2 (read `plan-usage-history.json`) is now the
fallback for a session whose account is *not* registered as an isolated account, where
the fix currently refuses; the record is org-tagged and tokenless, so it would answer
correctly. Note it is sampled ~5-minutely and lags: measured here, its last `ceeaba38`
sample read `sd 85` at 09:50 while the weekly window had reset to `0` at ~10:00 — so it
must be read as a lagging signal, never as current truth. Rung 4
(`_overseer_collision` asserting `overseer==worker` from ambient config) is untouched
and can now be derived from `session_identity()`.

## Note on scope

This is about **attribution**, not about the reading being stale or the endpoint being
undocumented. Both of those are known and already handled best-effort. The defect is that
Horus cannot tell whose number it is holding, and says it with certainty anyway.
