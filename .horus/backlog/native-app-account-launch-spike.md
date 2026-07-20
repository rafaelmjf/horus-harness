---
status: open
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "Exact probe steps, which OS is authoritative for the finding, and the pass/fail bar are undecided — refine before running."
phase: explore
type: spike
vision_facet: "Accounts & isolation"
---

# native-app-account-launch-spike — can the TUI launch the desktop app under a chosen account

## Why

The owner runs the horus TUI on Linux as launch pad + account selector for the
`claude` **CLI**, keeping two accounts (personal / work) isolated via
`CLAUDE_CONFIG_DIR`. They also use the Claude Code **desktop app** and want the
same "pick an account, launch" from the TUI — today the second account only runs
inside a cumbersome Hyper-V VM. Docs research (2026-07-20) established the shape
but left the feasibility questions to a hands-on probe:

- The desktop app registers `claude://code/new?q=…&folder=…` (seeds prompt +
  working folder) but the deep link has **no account parameter**.
- The desktop app does **not** read `CLAUDE_CONFIG_DIR`; the account-isolation
  lever is Electron's `--user-data-dir` (own auth token, settings, sessions per
  dir) — a *different* store from the CLI config dir.
- There is no live hot-switch of a running instance; switching account means
  relaunching under the other profile.

## Intended outcome

A definitive yes/no on the launch mechanics, so a follow-on "TUI launches the app
under account X" feature (and any app-session-visibility work) can be scoped on
evidence — or dropped — instead of guessed. The rest of the native-app direction
follows only if this proves out.

## Broad boundaries

A disposable, hands-on probe — no launcher or provisioning code ships from it.
The basic experiment answers:

- **Compose:** can one launch set the account (`--user-data-dir=<profile>`) **and**
  land on a seeded folder/prompt in the same invocation, or are account and
  context mutually-exclusive launch channels?
- **Single-instance:** two instances under two `--user-data-dir` profiles → do
  both run, or does a machine-global single-instance lock allow only one?
- **Cross-user (Windows):** does "Run as different user" (`runas`) put the second
  account's app window on the current desktop, both visible at once?
- **Secondary, cheap while probing:** does the desktop app leave horus-visible
  traces — `~/.claude/projects/**` transcripts and project-local
  `.claude/settings.json` command hooks firing — which would decide whether app
  sessions are ever reconcilable.

Non-goals: not tmux-attachable (the app is its own process); not the
autonomous-dispatch path (CLI-only); no shipped code.

## Open decisions for backlog-refine

- Which OS is authoritative — Windows (where the owner lives; `runas` / Hyper-V
  apply) or the Linux beta box (Zorin 18 / Ubuntu 24.04, X11, app not yet
  installed) as a secondary bench.
- The two-auth-stores wrinkle (CLI config dir vs desktop profile → login twice
  per account) — is it acceptable, and does it belong in this spike's findings.
- Pass/fail bar and how the Linux beta's known gaps (no Computer Use, no Wayland
  hotkey) might confound a result.

## Source

In-session native-app exploration, 2026-07-20 (owner-attended); Claude Code docs
(deep-links, desktop-linux, platforms, env-vars). No separate receipt — this card
carries the trace.
