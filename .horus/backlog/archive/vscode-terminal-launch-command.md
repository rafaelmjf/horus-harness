---
status: shipped
priority: medium
created: 2026-07-18
vision_facet: "Dashboard / cockpit"
phase: converge
tier: sonnet
type: feature
parallel: safe
created_by: owner
surface: horus/vscode.py (existing vscode-task integration), horus/launcher.py (terminal open), new `horus vscode-open`/flag; interaction with the managed-tmux target
shipped_pr: 333
shipped_sha: b721156ab8ce20ac1ef8e823e13a36999a38e9ab
---

# vscode-terminal-launch-command — open a session in the VS Code terminal + project folder

**Why (owner, 2026-07-18):** the owner wants a command that launches a horus session in
the **VS Code integrated terminal**, already `cd`'d into the project folder — the
everyday "open this project and start working" action from the editor. An open question
the card must resolve: **how it plays with the managed-tmux target** (TUI/app sessions
attach a Horus-managed tmux session; a VS Code terminal launch must not fight that).

## How (to design in-card)

- A command/flag (e.g. `horus vscode-open <project>` or extend `horus vscode-task`) that
  opens VS Code on the project folder and starts the session in its integrated terminal.
  Reuse the existing `horus/vscode.py` task integration rather than a new mechanism.
- **tmux reconciliation (the crux):** decide the target contract for a VS Code terminal —
  either (a) the VS Code terminal attaches as a *viewer* of the Horus-managed tmux
  session (consistent with the terminal-persistence rule: "browser xterm and
  web-requested native windows attach as viewers"), or (b) it launches on its direct
  host when inside VS Code's own shell. Pick one, document why, keep `horus open --target`
  behavior explicit and stable (existing rule).
- Cross-platform: VS Code launch differs per OS (`code` CLI presence); degrade gracefully
  when `code` is absent (name the fallback, never crash — mirrors the watcher-terminal
  best-effort rule).

## Acceptance

- One command opens VS Code on the project and starts a working session in its integrated
  terminal at the project root.
- The tmux interaction is explicit and documented: the VS Code terminal either attaches
  as a managed-tmux viewer or runs direct, per the chosen contract — never a fake attach.
- `code` absent ⇒ a clear message + fallback, never a crash.

## Non-goals

- Not a VS Code extension; a CLI/launch-path feature only.
- No change to the existing `horus open --target` scripted behavior.
