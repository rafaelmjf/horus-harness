---
status: in-progress
priority: high
tier: sonnet
created: 2026-07-11
parallel: exclusive
surface: horus/dashboard.py, horus/pty_host.py, horus/pty_session.py
folded_into: mobile-terminal-ux-hardening
---

> **CHECKED AGAINST PR #171 (2026-07-14, tier0-supervision-verbs acceptance
> cleanup):** `mobile-terminal-ux-hardening` shipped via PR #171
> (`68b4125`, merged 2026-07-12) — but its own PR body explicitly scopes
> **symptom 2 (this card's mobile-no-input bug) as OUT OF SCOPE**: "untouched
> beyond the pre-existing input-failure surfacing, per the card." PR #171 only
> touched `horus/dashboard.py` CSS/JS sizing+lifecycle and `horus/pty_host.py`
> resize-debounce — no `access_gate.py`/`_same_origin` change, which is where
> this card's own diagnosis (§"Investigation 2026-07-12") pins the input-path
> suspects. **Leaving this card open** — not resolved by #171, still needs the
> on-phone decision tree in that section run against the live hosted dashboard.

> **REACTIVATED (2026-07-12, owner session):** investigation session traced the full
> input path and concluded this is **our stack, not Claude Code** — the transport
> (`onData` → POST `/pty/input` → Access-JWT + `_same_origin` gate → PTY write) is
> TUI-agnostic; codex and claude receive identical bytes. Fix authorized inline this
> session. Findings + on-phone diagnostic tree in §"Investigation 2026-07-12" below.

> **FOLDED IN (2026-07-12) → `mobile-terminal-ux-hardening.md`** (symptom 2), but
> kept as the **distinct** root-cause track: the diagnosis session determined this is
> the exposed-mode / Cloudflare-Access / same-origin POST-path family, **not** the
> sizing/lifecycle cluster the redesign targets, and it did not reproduce in the
> headless sizing harness (no auth gate there). Investigate the `/pty/input` POST
> path on the exposed host separately. History kept for provenance. See
> `docs/terminal-mobile-desktop-diagnosis.md` §4.

# Mobile terminal accepts no input on the hosted/mobile app

**[bug]** The in-app terminal (`target=='app'`, `pty_host.host.start` path) accepts
no keyboard input on the hosted/mobile dashboard, though it worked days ago. Prime
suspects, in rough recency order: the exposed-mode/Cloudflare-Access commits
(`662f155`, `e4fb8fd`) and the rejected-input change (`36412bf`) — any of these
could have broken the input event path (same-origin POST guard, SSE/keystroke
wiring, or an access-gate check firing on the PTY input route). Reproduce on the
hosted/exposed dashboard specifically; the desktop/local `horus app` terminal is
not confirmed broken and may be a useful differential.

`parallel: exclusive` — shares `horus/dashboard.py`, `horus/pty_host.py`,
`horus/pty_session.py` surface with any other card touching the in-app terminal;
do not run concurrently with `pwa-installable` or `responsive-mobile-pass` without
checking overlap first.

## Investigation 2026-07-12 (inline session, no dispatch)

**Conclusion: solvable, not fundamental.** The input path never touches the agent
TUI, so "claude vs codex" is irrelevant to *this* bug (the rendering gap is a
separate, mostly-upstream issue — see `terminal-claude-rendering-levers.md`).

Since `36412bf`, a rejected/failed input POST prints a one-time red notice in the
terminal — that makes the phone itself the diagnostic. **On-phone decision tree**
(owner-only, ~2 min, on the live hosted dashboard):

1. Tap the **keybar** buttons (Esc/arrows/⏎) — they bypass the soft keyboard and
   POST directly.
2. Read the outcome:
   - Keybar works, typed letters don't → client-side: soft keyboard → xterm.js
     hidden-textarea/IME (known xterm mobile weakness). Not the POST path.
   - Nothing + red `[input not delivered (403)]` → app-side gate:
     `access_gate.authorized` or tightened `_same_origin` (dashboard.py:4312).
     Candidate: cloudflared `httpHostHeader` rewriting Host so
     `Origin != scheme://Host` → every exposed-mode POST 403s.
   - Nothing + red `[input not delivered — network error]` → Cloudflare edge
     intercepting POST: **expired Access session** (page + old SSE stay alive; new
     POSTs 302 to the cross-origin Access login, fetch dies on CORS). Matches
     "worked days ago". PWA note: iOS installed-PWA cookie jar is separate from
     Safari's, so the PWA's Access session can be dead while Safari's is fine.
   - Nothing, **no notice at all** → `onData` never fires → focus/keyboard issue.

Actionable without the phone: verify tunnel `httpHostHeader` vs `_same_origin`
expectations; make expiry/blocked-POST failures recoverable in-page (detect and
offer reload) instead of one dead red line.
