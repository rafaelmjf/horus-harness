---
status: shelved
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-28
refine_passes: 2
readiness: shaping
readiness_reason: "Per the 2026-07-20 Findings (below): the install is already current (0.0.73), WSL2 is already installed, and the native capability inventory is done. Remaining open question is the recommendation. This session (2026-07-21) narrows it: native Windows is fine for the owner's local-project work, but the 'attach any session' / persistence experience is exactly what degrades native, so WSL+tmux (already present) is the path for THAT. First concrete step: run the TUI under WSL+tmux and validate attach-any-session end to end, then confirm the native-for-local + WSL-for-attach split as the recommendation."
topic: distribution
type: spike
---

# windows-native-horus-setup — the best way to run horus on Windows, given the TUI's recent growth

## Why

The owner has horus installed on their Windows machine but it has been **stale for
a while**, and the last several releases added a lot of **TUI** capability that may
not be cleanly Windows-native — most of it assumes tmux, which horus only uses for
managed/persistent sessions on **Linux/macOS/WSL** (native Windows keeps the direct
host: no managed tmux, so no session persistence, no cross-viewer attach, no
`horus open --target`). The owner wants to know, exploratorily, what the right
Windows setup actually is before sinking time into either upgrading in place or
changing surfaces.

## Intended outcome

A clear recommended Windows setup for the owner (and documentable for other
Windows users), backed by an explicit list of which recent TUI features work
native, which degrade, and which need WSL — plus a decision on whether to invest
in native-Windows TUI parity or steer Windows users to WSL and/or the native app.

## Broad boundaries

An investigation that lists and assesses the alternatives, not an implementation.
The candidates to weigh:

- **WSL2** — full Linux parity: tmux persistence, managed sessions, every TUI
  feature works; cost is the WSL layer and the Windows/Linux filesystem boundary,
  and GUI/native-app things live on the Windows side.
- **Native Windows (Windows Terminal / PowerShell)** — the CLI is a three-OS
  target and runs; the question is exactly which TUI features degrade (tmux
  persistence, attach, cross-viewer) versus fail versus work fine (the `fcntl`
  lazy-import and Git-Bash hook path already exist). Enumerate this concretely.
- **Native app on Windows** — cross-links `native-app-account-launch-spike`:
  possibly the best Windows path is the desktop app rather than the TUI at all.
- **Git Bash / MSYS** middle ground (hooks already run through Git Bash on
  Windows) — is there partial tmux/persistence there, or not worth it.

First step (the "stale install" premise was already disproven — see Findings below;
the install is current and WSL2 is installed): run the TUI under the already-installed
WSL2 + tmux and validate the owner's "attach any session" experience end to end — that
is precisely the capability the inventory marks as degraded on native Windows. This
validation doubles as the evidence for the recommendation.

Non-goals: not committing to native-Windows TUI feature parity as an outcome (that
is one possible conclusion, not the premise); no new Windows-only runtime.

## Open decisions for backlog-refine

- The recommended default setup, and whether it differs for "owner's machine"
  vs "any Windows user."
- Invest in native-Windows TUI parity, or explicitly steer Windows to WSL / the
  app and document the native-Windows TUI as best-effort.
- Whether this stays one exploratory card or splits into (a) the stale-install
  upgrade + compat inventory and (b) any parity work that inventory justifies.

## Findings — Windows machine setup run, 2026-07-20 (owner-attended)

The premise "the install is stale" was **false**: it was already 0.0.73, matching
the repo. What was actually wrong was everything around it. Done and verified this
session on the owner's Windows 11 box:

- **Shadowed binary** — a `pip`-installed `horus-harness` 0.0.1 sat in
  `Python312\Scripts` behind the uv shim. `doctor machine` caught it unprompted
  with the right fix. Uninstalled.
- **Accounts** — none existed (`account: null` on every session, auto-generated
  aliases). Now `claude-personal` + `codex-personal` aliased and isolated from the
  live logins, and `claude-work` provisioned + mapped (awaiting one login).
- **Statusline** — was a hand-rolled PowerShell script, so `rate_limits` were never
  recorded and usage was permanently empty **with no error**. Now `horus statusline`
  in ambient `~/.claude` and both isolated accounts.
- **Repos** — workspace consolidated to `C:\Users\Rafa\projects`; horus-harness,
  fabric-metadata-driven-medallion, pbi-ecosystem cloned there and the `projects`
  list repointed.

**Native-Windows capability inventory** (probed, not inferred):

- *Works native:* full CLI core, launch-in-new-window, the TUI (ships a `_WinPty`),
  dashboard/app, tkinter mascot, hooks via Git Bash, statusline + usage recording,
  account isolation, worktrees, `gh`, VS Code tasks, foreground `horus run`.
- *Degrades:* `terminal_sessions.tmux_available()` is hard-`False` on `nt`, so no
  persistent managed sessions, no cross-viewer attach; `--target tmux` and detached
  workers fall back to the current TTY / a new window.
- *Unavailable:* `horus schedule` (needs `systemd --user` timers) — so the whole
  scheduled-dispatch + supervise loop is Linux-only here. `native-windows` as a
  *remote* target stays a deliberate documented gap.
- WSL2 (Ubuntu) **is installed** on this machine, so the tmux/scheduler path is
  available without changing anything if the owner wants it.

This answers the "which features degrade" half of the card. The remaining open
question is the recommendation itself (native vs WSL vs app) — and the owner's
usage so far is local-project work on this machine, not autonomous dispatch, which
points at native-Windows-is-fine, but that is a judgment to confirm, not a finding.

## Source

In-session, 2026-07-20 (owner-flagged as intended next focus). Grounding: the
tmux-persistence rule (Linux/macOS/WSL only) and the three-OS Distribution facet
in `.horus/PRD.md`.

## Reviews

- 2026-07-28 — **high → medium; `order: 20` removed** (owner, refine pass). Two things had
  gone stale. First, the priority: the question that was actually blocking the owner — which
  TUI features degrade on native Windows — is already answered by the 2026-07-20 probed
  inventory, the daily driver is Linux, and what remains is a validation run plus a
  documentation-grade recommendation. Second, the ordering: `order: 20` meant "second slot,
  behind `session-remote-control-default`", and that card shipped in #386 — so the stamp
  pointed at a vacant first slot and made a medium-priority Shaping card lead its queue for
  no reason. Removed, leaving the Shaping pool deliberately unsequenced.

  Open decisions remain as listed and are `[session]`-class: the invest-in-native-parity vs
  steer-Windows-to-WSL call is strategic, which is why this card has now been screened twice
  without converting.

- 2026-07-21 — **Kept shaping, ordered #2** (`order: 20`) (owner, refine pass):
  promoted to the second slot behind `session-remote-control-default`. The
  recommendation stays open, but this session narrows it: native Windows is fine for
  local work while the "attach any session" experience is the degraded-native piece, so
  WSL+tmux (already installed per the 2026-07-20 Findings) is the path for that. First
  step reframed to *validate* the TUI under WSL+tmux — not "upgrade a stale install,"
  which the Findings had already disproven (install was current at 0.0.73).

### 2026-08-01 — owner + agent (manual)
Verdict: reference — native confirmed for PBI; SSH measured; skew is the real risk

REFERENCE, measured live this session rather than inferred.

**Corrects this card's premise.** horus is ALREADY installed native on the Windows box —
`horus 0.0.73` at `C:\Users\Rafa\.local\bin\horus.exe`, with `horus-harness`,
`fabric-metadata-driven-medallion` and `pbi-ecosystem` registered under
`workspace_root = "C:/Users/Rafa/projects"`. So "whether to install" is settled. The live
question is **native vs WSL for work already being done there**.

**State.** WSL2 Ubuntu is installed and **Stopped** (alongside a `docker-desktop` distro) —
native is already what actually gets used.

**The SSH bridge now works in both directions.** Windows→Linux is Tailscale SSH (see the
PRD rule). Linux→Windows is a real OpenSSH Server on the Windows box, key-authed via the
`~/.ssh/config` alias `pbi-win` (100.65.119.44). Tailscale SSH does **not** serve Windows
hosts, so that direction requires sshd; it was already running.

**What the bridge proved.** From Linux, `tools/query-model.ps1` ran end to end against a
model open in Desktop: ADOMD resolved, `msmdsrv` port auto-discovered (53105), DAX returned
rows in 32 ms, exit 0. The verification loop *can* be driven remotely.

**What it costs — three frictions, all sshd artifacts rather than anything inherent:**

1. **Quoting.** bash → ssh → PowerShell mangles nested quotes; every non-trivial call needs
   `-EncodedCommand` with base64 UTF-16LE.
2. **Exit codes flatten to 1.** The sshd `DefaultShell` there is PowerShell, which reports
   `$?` rather than the command's code: `exit 2`, `exit 3` and `exit 7` all came back as 1.
   This is the dangerous one — `query-model.ps1`'s contract is *"2 = usage/environment,
   1 = query error"*, so over SSH **"Desktop is not open" becomes indistinguishable from
   "your DAX is wrong"**, destroying exactly the signal `vision-deterministic-tooling`
   exists to give a weaker model. **Fix:** append `; exit $LASTEXITCODE` at BOTH shell
   levels — the login shell AND the inner `powershell -NoProfile -EncodedCommand`. Verified:
   0 / 1 / 2 then propagate correctly. Miss either level and it silently degrades to 0-or-1.
3. **Window-station isolation.** `MainWindowTitle` is empty for every `PBIDesktop` process
   over SSH, so there is no GUI introspection — which is what makes multi-instance
   disambiguation harder remotely than locally.

**A native install removes all three** (local invocation, no login shell in the chain, same
window station). That, plus report authoring being irreducibly visual, is why native stands
for PBI work.

**WSL is the wrong trade here.** What it buys — tmux persistence, cross-viewer attach,
`horus schedule` via systemd — is precisely what PBI authoring does not use, and the
autonomous-dispatch facet was shelved 2026-08-01 anyway. What it costs is a filesystem
boundary in the middle of the actual workflow: either the repos sit on `/mnt/c` (slow git
and file watching) or in the WSL filesystem where Desktop must reach them over `\\wsl$\`.
It also does not fix the window-title problem. Native keeps files, the PowerShell/ADOMD
tooling and the GUI on one side of every boundary.

**The real risk is not native-vs-WSL, it is VERSION SKEW — and neither option fixes it.**
Windows is on 0.0.73 while the Linux box is 0.0.79 plus 30 unreleased commits: six releases
behind. Skew bit twice on a SINGLE machine on 2026-08-01 (a retired line-cap signal read as
current; the entire shelve sweep invisible to the TUI). Two installs double that surface and
nothing gates it. Any recommendation ending in "keep horus on both machines" needs an
upgrade discipline attached, which this card does not yet propose.

**Scope, refined.** The card's open decision reads as a global "native vs WSL vs app". The
measured answer is narrower and is a third option: **native, scoped to Windows-bound
projects** (PBI, where both the GUI and the ADOMD tooling are Windows-native), with
Linux-native projects staying on Linux. Windows becomes a first-class host for a subset of
the fleet, not a second copy of everything.

**Still open.** The upgrade discipline for two installs; whether interactive Entra/Fabric
auth works over the bridge at all (untested — no TTY, so `publish-pbip-to-fabric-skill` may
not be remotable); and `pbi-ecosystem`'s `multi-instance-port-pick`, reproduced live here —
with two workbooks open, auto-discovery silently returned the FIRST model (13 tables vs the
second's 32) with exit 0 and no warning.

### 2026-08-12 — parked for topics-over-facets migration (owner)

Shelved as part of clearing the active field for the full facets→topics teardown (`retire-facets-for-topics`). Not declined on its own merits; unpark when the migration lands and the backlog model is stable. See `.horus/plans/topics-over-facets-migration.md`.
