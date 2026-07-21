# Mobile access to agent sessions — terminal persistence, session sharing, and account-switch friction — 2026-07-21

## Scope

Discussion receipt, not a decision. It captures a wide-ranging architecture
conversation that started from the Windows-machine SSH setup (done the prior day, to
run Horus and work with Power BI files) and unwound into: why terminal sessions do or
don't survive dropped connections, how "attachable terminals" actually work, why the
native Claude/Codex mobile apps can (or can't) reach a running CLI session, the iOS
sandbox limits on smoothing account switching, and whether a small self-hosted Horus
phone chat frontend is worth exploring. No credentials or tokens here.

The owner's framing throughout: **never compete with what someone else does better.**
The native mobile apps are good; the only things worth owning are the gaps and the
middle layer (account switching) that no vendor will solve for this multi-account,
multi-agent setup.

## The problem, separated into its real parts

The conversation kept converging because several distinct problems were tangled
together. Pulling them apart:

1. **Session survival across a dropped connection.** A bare PowerShell-over-SSH session
   (via Tabby/Terminus) dies when the connection drops; a tmux session survives. Windows
   has no native tmux.
2. **Multi-client / "attach from anywhere" (mirroring).** Being able to view/drive one
   live session from more than one place (desktop + phone), like the old Horus webapp.
3. **Mobile access to a running agent** (Claude Code / Codex CLI) specifically.
4. **Account-switch friction on the phone** — the papercut that, historically, kicked off
   the whole Horus → webapp → tmux-TUI saga in the first place.

The key realization is that 1–3 are all the *same* underlying question — *was the session
born inside something shareable?* — and 4 is a separate, largely unfixable identity
problem.

## Core technical findings

### Why a bare SSH shell dies and tmux doesn't

A shell run directly over SSH is a child of the SSH channel; the channel is its
controlling terminal. Drop the connection and sshd tears down the channel, the shell is
hung up, and its process tree goes with it. Reconnecting opens a *fresh* shell — there is
nothing left on the server to reattach to. tmux is different because the tmux **daemon**
is not a child of the SSH connection: it owns the pty, your shell lives inside it, and
any client attaches to tmux over a local socket. That decoupling is the whole feature.

### The one fundamental boundary: you can only attach to a session *born shareable*

You cannot retroactively adopt an already-running terminal that wasn't started inside a
sharing server — **on any OS, including Unix.** You can't wrap a bare shell in tmux after
the fact there either. On Windows this is sharper because of history:

- Windows historically had **no pty**. The console subsystem (conhost) welded I/O to a
  specific window; the only "in" was screen-scraping (`ReadConsoleOutput`) + input
  injection after `AttachConsole(pid)` — fragile, single-attach, not a shareable stream.
  This is *why* "tmux for Windows" never materialized.
- **ConPTY** (`CreatePseudoConsole`, Windows 10 1809 / 2018) finally gave Windows a
  pty-like VT byte stream. It's what makes Windows Terminal, VS Code's terminal, and
  OpenSSH-on-Windows work. So the primitive to *build* a tmux-style server now exists.
- **But ConPTY handles are private to the process that created them.** There is no OS API
  to enumerate running ConPTYs and hand their master to another controller. So attaching
  to a GUI terminal window you opened manually (e.g. via RustDesk) is blocked by design;
  launching *into* your own session server is entirely possible. Same rule as Unix.

### Two ways to share: pty bytes vs. structured state

- **tmux / pty-level sharing** relays raw terminal bytes. Coupled to the terminal, the
  console, the transport. A client must reach the socket (via SSH).
- **Application-level sharing** relays the *semantic session* — messages, tool calls,
  tool results, diffs, approvals. The terminal is just one rendering. This is what Claude
  Code remote control does, and what the old Horus webapp did. It's transport-decoupled:
  any authenticated client can subscribe.

This distinction explains the old webapp's failure mode (below) and why text-via-web is
easy while terminal-via-web is hard.

### Cloud rendezvous via an outbound connection

Claude Code is already a client of Anthropic's backend (for inference), so it holds an
authenticated *outbound* channel. Remote control rides it: the process publishes session
state up, the phone subscribes down, input flows back. Neither end accepts inbound
connections — both dial a broker that pairs them. Same NAT-punching pattern as
RustDesk/TeamViewer. This is why it works **regardless of where the session was launched
from** — the launch context never touches the relay; only the live process + its
connection matter. (Corollary: the process must stay alive on the box — launch it in a
persistent place, e.g. the console/desktop session or tmux, not a droppable SSH shell.)

### Why the old webapp failed — and why text-via-web wouldn't

The webapp streamed a *terminal* (pty bytes into a browser terminal). Faithfully
rendering a full-screen TUI — cursor addressing, alt-screen redraws, box-drawing, and the
killer, matching terminal **geometry** to a resizing phone viewport — is what produced the
"scrambled terminal." A **text/chat** frontend that renders *structured events* as
reflowing bubbles has none of that. The failure was terminal emulation, not "web."

### iOS sandbox blocks a Horus-style account-switch helper

Horus swaps accounts by pointing `CLAUDE_CONFIG_DIR` at a different profile — trivial on a
server you own. On iOS, every app is sandboxed: no third-party app can read/write another
app's files, session, or keychain (keychain sharing requires same developer team +
entitlements). So a helper app **cannot** swap the official Claude app's active account.
What iOS *does* allow — deep links / App Intents (only if the app exposes them),
Password AutoFill — doesn't help here (see next). The switch is trivial only inside an app
you own yourself.

### The account-switch friction is server-enforced and unfixable client-side

- Switching accounts triggers Anthropic's email verification, delivered as a **magic
  link** (worse on mobile than an OTP code).
- No local helper can bypass server-side identity verification — that's the point of it; a
  bypass would be a security hole.
- A magic **link** can't even be autofilled the way an OTP code can (iOS code AutoFill
  handles codes, not URLs), and it forces the Mail → tap → app-handoff round-trip. The
  only lever is whether the link is a proper Universal Link (Anthropic's implementation,
  out of the owner's hands).
- The **only** structural escape is owning the session layer: verify each account **once**
  at enrollment, store a persistent session server-side, and make "switching" just picking
  a stored session — no re-verification ever. That is precisely what a self-hosted Horus
  chat frontend would give.

### Codex mobile finding (corrects the initial assumption)

Initial belief: "the Codex mobile app only steers the desktop app, not the CLI." **Web
check contradicts this** — the official Codex app (in the ChatGPT app) connects to Codex
"in whatever surface you already use (CLI, the desktop app, or the Chrome extension)" over
the same relay pattern. So the **CLI is supported.**

**However**, the gap is real for *this* setup for a different reason: the worker machine
must currently run **macOS**. Windows is listed "coming soon" with no committed date;
Linux isn't mentioned. The owner's Codex box is **Windows** → the Codex mobile app can't
reach it *at all* today. Meanwhile Claude Code remote control already works on that same
Windows box (used live this session).

Sources (secondary — OpenAI's own page 403'd): ofox.ai Codex-mobile-2026 writeup,
OpenAI "Work with Codex from anywhere", Engadget Codex-mobile coverage. Space moves fast;
re-verify before this is load-bearing.

## Approaches considered

| Approach | Survives drop? | Multi-client / mirror | Phone reach | Works on the Windows box *today* | Native or build | Account-switch | Notes |
|---|---|---|---|---|---|---|---|
| Bare PowerShell over SSH (Tabby) | ❌ dies with the channel | ❌ | via SSH app | ✅ (SSH set up) | native | n/a | The status quo limitation that started the thread |
| WSL + tmux | ✅ | ✅ strongest | any SSH client + phone SSH | ✅ (via WSL) | native (Unix tools) | n/a | Universal attach point; `/mnt/c` git perf caveat; natural home for the CLIs anyway |
| VS Code Server / code-server | ✅ (pty-host) | reconnect ✓, live-mirror weaker | browser (phone) / VS Code | ✅ | run a server | n/a | ConPTY-backed native-PowerShell persistence; **only VS Code clients**, not Tabby |
| RustDesk (already set up) | ✅ (console session persists) | screen-share, not detached | ✅ incl. phone | ✅ | native | manual | GUI remote control; the right tool for Power BI, not terminal work |
| RDP | ✅ (session-level) | ❌ (bumps console) | client per-OS | ✅ | native | n/a | Windows-native GUI persistence; not a terminal-sharing tool |
| **Claude Code remote control** | as long as process lives | ✅ app-layer | ✅ native app | ✅ **used live** | native | re-OAuth per switch | The clean answer for Claude CLI; app-layer sharing |
| Codex mobile app | as long as process lives | ✅ app-layer | ✅ native app | ❌ **Mac-only worker** | native | ChatGPT account | Supports CLI, but not Windows workers yet (coming soon) |
| iOS account-switch helper app | n/a | n/a | n/a | n/a | build | ❌ blocked | Sandbox forbids touching the official app's credentials |
| **Horus self-hosted chat frontend (#1)** | ✅ (server owns session) | ✅ (design choice) | ✅ browser/app you build | ✅ | **build (modest)** | ✅ solved (enroll once) | Text-only; own account layer; see conclusions |

## Conclusions

1. **The Windows terminal-persistence problem is solved without new code.** For terminal
   work the owner wants resumable, use **WSL + tmux** (universal attach: Tabby + phone
   SSH); for GUI/Power BI keep **RustDesk**. Bare PowerShell-over-SSH stays fine for
   throwaway CLI where a fresh shell on reconnect is acceptable.
2. **For the agents specifically, the native tools are the right daily drivers.** Claude
   Code remote control already gives phone access to CLI sessions on the Windows box
   (app-layer sharing, works regardless of launch context, as long as the process lives).
   Don't rebuild it.
3. **The account-switch friction cannot be fixed by any helper.** It's server-enforced
   email/magic-link verification; iOS sandboxing blocks a profile-swap helper anyway. The
   only structural fix is owning the session layer.
4. **The self-hosted Horus chat idea has a narrow but real justification** — but its
   durable value is *not* "Codex has no mobile" (that's a temporary, Windows-only,
   likely-closing gap). Its durable value is (a) **one unified phone UI across both
   agents** and (b) **your own account-switching layer** (enroll-once, no re-verify). Any
   build should lean on those, not on the Codex gap. Text-via-web is genuinely feasible;
   the real work is the **tool-permission approve/deny UX** and rich-content rendering, not
   the chat bubbles. Scope small; the CLI stays the daily driver.
5. **What no vendor will ever solve for this setup: smooth switching across *your*
   multiple accounts.** That is the through-line from the original Horus saga and the one
   genuinely owner-specific problem.

## Suggested exploration ideas (candidate cards — owner to disposition)

- **[near-term] Remote-control-enabled-by-default toggle.** Make Horus-launched sessions
  attachable via the native app without remembering to enable it. Ship as a **setting with
  a sensible default + per-launch override**, not hardcoded always-on (unattended worker
  sessions being cloud-attachable is a posture choice). Scope note: **Claude-only** (Codex
  has no equivalent); it makes sessions *reachable* but does **not** remove the phone
  account-switch step. Verify first: the exact mechanism to enable remote control at launch
  (CLI flag vs settings key vs in-session only) — quick claude-code-guide check.
- **[low-priority / casual] Self-hosted Horus phone chat frontend (target #1).** Text-only
  chat client to **Horus-server-owned** agent sessions (explicitly *not* mirroring the
  existing tmux `claude` session — that would be reimplementing remote control). Justify on
  unification + own account layer. Likely path: Claude Agent SDK (or `claude` CLI
  `stream-json`) for structured events; own server holds per-account sessions, switching is
  a dropdown. Real work = permission UX + rich blocks.
- **[not a card] Today's papercut mitigation.** For the account-switch friction *right
  now*: nothing to build. A magic link can't be autofilled; the best available smoothing is
  ensuring Apple Mail so any Universal Link handoff is as direct as possible. Accept it, or
  wait for #1.

## Open questions to verify before anything is load-bearing

- Exact mechanism to enable Claude Code remote control at launch (flag / setting / in-session).
- Whether Codex ships Windows worker support (closes the Codex-on-Windows gap → weakens #1's
  thin justification, not its durable one).
- Whether Anthropic's login magic link is a Universal Link into the app (marginal smoothing).
