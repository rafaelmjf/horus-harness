---
status: active
last_updated: 2026-06-30
---

# History — bumps in the road

Curated, durable context: the problems that bit us and the lessons that shaped the
design. **Not** a timeline and **not** open issues (those live in `roadmap.md`) —
just the war stories worth carrying forward.

## Windows virtualenv `pythonw.exe` wrappers are not the whole process tree

The mascot/dashboard lifecycle looked fixed because `stop_dashboard()` terminated and
waited on the `Popen` handle it created. On Windows under a virtualenv, that handle can
be only the venv `pythonw.exe` launcher; the real base-Python `pythonw.exe -m horus
dashboard` remains as a child and keeps port 8765 alive after the mascot quits. The same
wrapper pattern appears for the companion itself. **Lesson:** when Horus owns a
windowless Windows child, reap the process tree (`taskkill /T /F` for this lightweight
tier), not just the immediate `Popen` process. A real smoke should spawn a dashboard,
stop it, and verify the port has no listener.

## Usage hook overrode an explicit command and left work unpushed

A Codex session hit 90% usage; the closure hook fired and, on an explicit "commit and
push to remote", committed only `.horus/` via `horus close --commit`, did **not** push
(left the branch "ahead 2"), left the source/test/doc work uncommitted, and stopped.
Three failures from one string: the injected `USAGE_CLOSURE_INSTRUCTION` ended with
"commit with `horus close --commit`. Then stop — do not resume the main task." The
agent obeyed the injected imperative over the user's actual request; the instruction
never mentioned `--push`; and `horus close --commit` stages only the continuity
pathspec by design, so the real work was never committed. **Lessons:** (1) a hook is a
*signal*, never an authority over an explicit user command — injected context must
defer to the user (frame it "context, not a command") and, at a stop, *ask* rather than
force-divert; (2) closure that stays local-only defeats the cross-machine guarantee —
always `--commit --push` and always push committed work; (3) a closure instruction that
commits only `.horus/` must explicitly tell the agent to commit/push its actual work
too, or that work is silently stranded.

## A live companion is not proof the dashboard server is live

The dashboard stopped opening even though `horus app --open` was still running. The companion
process had outlived the dashboard child it spawned, so opening the app sent the browser to
`127.0.0.1:8765` with no listener. A separate restart wrinkle made this harder to reason
about: disabling `allow_reuse_address` everywhere prevented duplicate Windows dashboard binds,
but on POSIX it can also block a clean restart while the old socket is in `TIME_WAIT`.
**Lessons:** (1) before opening a local dashboard URL, probe the HTTP server, not just the
companion process; (2) if a companion owns the dashboard child, a click/open action should
repair a dead child by restarting it; (3) single-instance socket policy is OS-specific —
Windows needs duplicate-bind protection, POSIX needs port reuse for clean restarts.

## A worker handoff file can fake delegation if the supervisor writes it after doing the work

The first dashboard follow-up phase under the new execution workflow fixed a real bug, but
it did **not** actually test the frontier/standard split: the supervising session created
the phase handoff and then implemented/reviewed the work itself. The terminal made this
ambiguous, and the user correctly challenged whether a standard worker had actually run.
**Lesson:** when workflow validation is the goal, "delegated" must be observable: a distinct
worker/subagent/session does the implementation and leaves the note. If the current
environment cannot spawn one, the supervisor should stop instead of simulating the workflow.
`horus-execution` v2 now makes this a hard gate for model-separation tests.

## ctypes silently truncated 64-bit handles; only live-exercise caught it

`horus focus` (raise a session's window) used `ctypes.windll.user32`/`kernel32` without
declaring `argtypes`/`restype`. ctypes then defaults every argument to a 32-bit `int`, so
on 64-bit Windows the `HWND`s and the Toolhelp `HANDLE` were **truncated** —
`GetWindowThreadProcessId` got a corrupt handle (never matched a pid) and
`CreateToolhelp32Snapshot`'s handle was mangled (so the descendant walk silently fell back
to `{pid}`). The function returned `False` every time while looking completely correct. The
unit tests passed because they only hit the early `pid is None` return — they never exercised
the FFI path at all. It surfaced only by launching a real window and calling the function
against its pid. **Lessons:** (1) always declare `argtypes`/`restype` for ctypes calls that
touch handles/pointers — the default `int` is a 64-bit truncation trap; (2) FFI/`ctypes` code
is invisible to early-return unit tests — leave one live-exercise check behind, not just a
None-guard test; (3) a started session began as a stale-base mistake earlier this same day —
verify against reality (the remote, the running process, the actual window), not against what
looks right.

## Started work on a stale local main (fetch before trusting local refs)

A session "continued" from `git log -1` (local only) and built a whole dashboard tab on a
base that was 20 commits behind `origin/main` — before MVP3 even existed — and asserted "no
CLIs installed" from a stale `.horus/roadmap.md` when `claude` was in fact on PATH. The work
had to be stashed and redone against real main. The pickup `next_prompt` *already* said
"fetch-first, verify from the REMOTE"; it was ignored. **Lesson:** at session start in this
repo, `git fetch` and compare to `origin/<branch>` before trusting local refs or `.horus`
prose; the continuity files describe the last *committed* state, which may itself be behind.

## Windows backslash paths silently broke TOML config (forward-slash everything)

The multi-account `[config_dirs]` writer (PR #6) stored paths verbatim: on Windows that
means `"work" = "C:\Users\…"`, and `\U`/`\w` are invalid escapes in a TOML *basic* string —
so `tomllib` raised, the tolerant loader swallowed it, and the whole map read back **empty**.
The feature looked fine on POSIX and in tests that used `/`-paths; it only broke on a real
Windows `--set-dir`. Caught later when the `horus run` test used a real tmp path. **Lesson:**
this project already learned to store the projects list forward-slashed for exactly this
reason — apply it to *every* path written to TOML/JSON config, and don't let a tolerant
"return {} on parse error" reader hide a serializer bug. Config-dir paths are now normalized
to forward slashes on write (`Path` reads them back fine on every OS).

## Building the real adapter reshaped the contract (one stream line → many events)

The adapter contract first had `parse_event(line) -> AgentEvent | None` — fine for the
FakeAdapter, whose stream is one event per line. But the first real adapter (Claude Code)
showed a single `assistant` stream-json line routinely carries *several* content blocks
(a text block **and** a tool_use block), so one event per line silently dropped the
tool_use. **Lesson:** validate a contract against the real thing early — the fake agreed
with my wrong assumption because I designed both. `parse_event` now returns a **list**
(zero or more events). Also learned from the real CLI: `claude -p` stream-json needs
`--verbose`; it waits ~3s on stdin unless you pass `stdin=DEVNULL`; and `system/init`
echoes the session id, so resume needs no pre-assigned id.

## A moving-major action tag that didn't exist silently broke every release

The v0.0.2 PyPI publish failed instantly: the workflow pinned `astral-sh/setup-uv@v8`,
but that action publishes only `vX.Y.Z` tags (latest `v8.2.0`) — there is no rolling
`v8` major tag, so `@v8` was unresolvable. A "bump CI actions" commit had introduced it
after the working v0.0.1 release, so it lay dormant until the next release. **Lesson:**
don't assume an action ships a moving major tag; pin a tag you've confirmed exists
(`@v8.2.0`). A release workflow only runs at release time, so a broken pin hides until
the worst moment — verify the tag resolves, not just that the YAML looks right.

A session handoff (`next_prompt`) told the next session to "resume on the
`mvp2.5-git-aware-dashboard` branch." That branch existed on `origin` but the
pickup machine had never fetched it, so `git branch -a` didn't list it. The pickup
agent concluded the branch didn't exist, that the local branch *was* the work, and
nearly proceeded on stale assumptions — when in fact the local branch had already
been merged into `main` and retired on the remote, and the real work lived on the
unfetched branch. **Lesson:** a session pickup must `git fetch --all --prune` and
reason from the *remote* state FIRST — local refs are a stale cache, and continuity
that travels via git (handoffs across machines/sessions) is exactly the case where
they're most likely wrong. Fixed for now by making `next_prompt` start with a
fetch-first + verify-branch step; deeper options (record `branch:`/push state in the
summary, a `horus resume` command) are tracked in roadmap.md.

## Claude's subscription usage IS readable — via the OAuth `/usage` endpoint

While building the Claude-side usage→closure hook, I checked four surfaces (CLI verbs,
local caches, the session transcript, `--debug` API output) and wrongly concluded
Claude Code exposes no subscription usage locally. The user pushed back ("`/usage`
clearly shows it"), and they were right: the `/usage` TUI reads it from
`GET /api/oauth/usage` — visible as a string in the CLI binary. **Lesson:** when a
client UI displays data, it came from an endpoint; find that endpoint (grep the
binary, watch the network) before concluding "unavailable." Also: the signal that
fired the Codex closure was the **5h rate limit (92%)**, not context (52.7%) — for
Opus, quota fills long before context, so the usage signal is the one that matters.

## Deterministic inference produced drifting, truncated `.horus/`

The first `horus init` mined README/STATUS/CLAUDE docs to pre-populate `.horus/`.
A real agent's review of the seeded fabric repo flagged two failures: multi-line
bullets truncated mid-sentence, and copying existing prose created a *second*
drifting "what's next" alongside the project's own docs. **Lesson:** don't
mechanically parse prose into continuity — `init` now scaffolds clean templates +
a `README.md` that says "distill from canonical docs, point at them, don't
duplicate." Rich population is the deferred LLM-based `horus infer`.

## Drift checking can't use byte-equality on the managed blocks

The `HORUS:BEGIN/END` blocks in `AGENTS.md` and `CLAUDE.md` are intentionally not
identical — each ends with a line naming the *other* file. **Lesson:**
`doctor instructions` normalizes/ignores that cross-reference line, or it reports
false drift on every run.

## A routine's "verify" step must be reachable by following the routine

The first `horus consolidate` flagged roadmap↔features overlaps purely on shared
capability *name*, while the skill correctly told the agent to **keep both** (split:
action points in roadmap, status in features). So a correct split never cleared the
warning — the success criterion contradicted the rule. An independent validation
agent caught it and noted it could loop or delete ledger rows chasing zero.
**Lesson:** align the machine signal with the rule. The cross-reference pointer
(`→ features.md`) is the detectable marker of an *intentional* split, so consolidate
now treats a cross-referenced item as reconciled and only flags un-split ones. When a
routine emits a "now re-run to confirm" step, make that zero actually reachable.

## A machine-local SQLite session registry cut against the ethos

Considered a SQLite session/event registry early. It presupposed Horus
orchestrating sessions (the deferred execution layer) and added a machine-local
store at odds with the file-first, git-synced, lightweight design. **Lesson:**
session `.md` files are ephemeral context that distills into the durable lanes;
at solo scale re-parsing markdown is instant. Registry deferred until real live
processes exist to track.

## A blocking GUI under console `python.exe` keeps the terminal window alive

`horus app` left a console window open for the whole session. Cause: it ran under
console-subsystem `python.exe`, and Tk's `mainloop` blocks, so the attached console
never closed. **Lesson:** on Windows a GUI must run under windowless `pythonw.exe` —
the companion now re-execs itself (`relaunch_without_console`, `DETACHED_PROCESS`,
`HORUS_DETACHED` loop guard, `--no-detach` escape hatch) and the parent exits.
Trade-off to remember: a detached child has **no console**, so a GUI startup failure
is now silent — a log-file/error-dialog fallback is the follow-up if it ever bites.

## An in-app agent restarted the app it was hosted in — and killed itself

A session running inside the dashboard's in-app PTY terminal was editing `dashboard.py`,
then restarted the app to see its change live. The dashboard process *hosts the PTY*, so the
restart tore down the session's own host — it killed itself mid-task, before committing, with
no session note (the work was recoverable from the working tree). Compounding it: the dashboard
page is static (no auto-refresh) and Python doesn't hot-reload, so even after the code landed
the running server kept serving the old in-memory build and the open window kept showing a
stale snapshot — which read as "the feature isn't there." **Lessons:** (1) an agent hosted in
the app must not be able to restart/kill its own host — decouple the session-host lifecycle
from a code reload (the deferred standalone session-host daemon is the structural fix), flagged
as MVP5; (2) when verifying a dashboard change, a long-running server holds an old in-memory
build and the page won't auto-refresh — restart the server and hard-reload before concluding
anything; (3) to confirm a "missing" UI element, check what the *server* actually renders
(fetch the HTML) before trusting the window. **Update 2026-06-26:** lesson (1)'s
agent-triggered path is now guarded — `pty_host` marks the PTY env and a Claude
PreToolUse(Bash) `horus guard-host --hook` refuses a hosted agent's restart/kill-the-host
command (decisions.md). That stops the *agent* footgun; a user/crash/code-reload restart still
drops live PTYs, so the standalone daemon remains the structural fix.

## pywebview was the worst of both worlds — live-test the shell before graduating to it

To fix the app-lifecycle gaps (closing the dashboard window didn't quit the app; stale Edge
tabs), we decided to graduate the UI shell from "Edge `--app=` + Tk mascot" to a Python-owned
**pywebview** window. On paper it was perfect: system webview (no bundled Chromium), stays
Python, cross-OS, owns the window lifecycle for free. The headless checks passed (API shape
validated against pywebview 6.2.1 with `start()` stubbed). Then it met the real Win11 machine:
it **crashed intermittently** (`AccessibilityObject.Bounds … maximum recursion depth exceeded`,
pywebview's WinForms/WebView2 layer — at startup and after load) and tab switches took **~4 s**.
A plain Edge `--app` window of the same dashboard was fast and stable. **Lessons:** (1) the
Chromium *engine* was never the problem — pywebview's *wrapper* was; when a thin layer over a
known-good engine misbehaves, suspect the layer. (2) A GUI shell can't be validated headless —
API-shape smoke tests (stubbing the event loop) prove nothing about stability/perf; only a live
run on the target OS does. (3) Don't rip out a working lightweight thing for a theoretically-
better one before live-testing the replacement. We reverted to the Edge `--app` + Tk mascot
(uncommitted, so a clean `git checkout` restored it) and made the "proper native app" a
separate, deliberately-evaluated future package instead. Also measured en route: the dashboard
server renders in ~15 ms, but a cold `/control` was 750 ms because account usage hits the OAuth
`/usage` endpoint synchronously per render — a real perf item for the proper app (load usage
async). See decisions.md "pywebview Tried and Rejected".

## Skills do not solve periodic native-app checks

The first instinct for a context-rollover warning was "build a skill that gets
called every few actions." But skills are invocation units, not reliable timers.
Codex has a native hook surface with a `Stop` event, so the better bridge is a
small hook that calls `horus usage check --hook` and lets the in-app skill handle
the actual closure work when nudged. **Lesson:** choose the native primitive that
matches the trigger shape - skills for cognitive routines, hooks for event-driven
checks.

## A hook file can be installed and still be semantically wrong

The Codex usage hook existed in `.codex/hooks.json`, the repo was trusted, and `codex doctor`
was clean, but the hook still was not valid for the intended closure behavior: over-threshold
hook mode printed a human `[warn] ...` line. Current Codex `Stop` hooks require structured JSON
on stdout, so tests that only asserted "exits 0" missed the actual contract failure. **Lessons:**
(1) validate native hooks against the app's stdout contract, not just file shape; (2) install
both the pre-task hook and the between-turn safety net when the native app supports both; (3)
include a forced-threshold smoke test that parses the emitted JSON.

## Linux validation exposed hidden Windows and shell assumptions

The 2026-06-27 Linux smoke pass proved the file-first CLI, dashboard rendering, POSIX stdlib
PTY transport, headless Codex adapter, and structured hook JSON all work in principle. It also
found assumptions that Windows dogfooding hid: installed hooks wrote `python -m ...` even though
many Linux hosts only have `python3`; hosted Codex PTYs inherited the parent `TERM=dumb`; POSIX
`horus open` did not open a real terminal and still reported success after Codex refused to
start; the advertised Python 3.11 support was not covered by a clean test path; and the Tk
companion needs explicit Linux desktop/Tk prerequisites or a graceful fallback. **Lessons:**
cross-platform is not just avoiding Windows-only imports — hook command strings, terminal
environment, process launch semantics, test runners, and GUI dependencies all need live Linux
smokes before calling a feature portable.
