---
status: shipped
priority: medium
tier: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-29
refine_passes: 3
readiness: ready
autonomy: attended
order: 30
phase: converge
type: feature
vision_facet: "Dashboard / cockpit"
parallel: exclusive
surface: horus/terminal_tui.py, horus/fetchcheck.py, horus/fleet_review.py
shipped_pr: 434
shipped_sha: c916d70
---

# tui-remote-freshness-indicator — see at TUI launch whether continuity is current

## Why

Continuity is remote-authoritative, so the TUI's first paint can show confident,
current-looking project state that is silently behind origin. The owner hit this
directly (2026-07-20): opened the TUI, read the focus lines, and had no way to
know which projects were stale without dropping to git. Acting on stale continuity
is exactly the failure the fetch-first rule exists to prevent — but the TUI is the
one launch surface that never fires it.

## What already exists — do NOT rebuild this

Established before scoping, so the card is not mis-sized as a sync engine:

- **`fetchcheck.fetch_and_state`** — the one fetch-first primitive: read-only fetch,
  never pull, TTL-cached 600s at `~/.horus/cache/fetch-check.json`, 10s hard
  timeout, silent no-op when offline / non-repo / no upstream.
- **`horus fleet` already renders `behind N` per project.** Verified live this
  session. The data layer is done.
- The TUI's existing "stale" counter is **skill-projection drift only** — an
  unrelated concept. That outbound screen is renamed **"Horus Assets Refresh"** as
  of 2026-07-29 (see `tui-fleet-artifact-refresh`), so the two directions no longer
  share a word: **"Refresh" = Horus assets outward; "Sync" = project state inward.**
  Render remote-behind as **"behind N"**, never "stale".

**So this card is presentation and trigger, not plumbing.**

## Intended outcome

Opening the TUI answers "is what I am reading current?" without a fetch in the
paint path, and routes the owner to the project that needs attention.

## Acceptance (EARS-lite)

When the TUI opens with cached fetch state on disk, it should render each
project's remote-freshness (current / behind N / unknown) with the age of that
reading, without performing any network call during first paint.

**Gate on the delivered SHA:** focused TUI tests assert (a) first paint renders
per-row freshness from cached state with zero network calls, (b) an explicit fleet
refresh fetches all registered projects concurrently under one global deadline with
rows resolving independently, and (c) offline/no-upstream rows render `unknown` with
age, never an error. **Live probe:** open the TUI against a fleet where one project's
`main` is behind origin and one is current; the behind project renders `behind N`
with the reading's age on its row, the current one renders `current`, and neither
triggers a fetch during first paint.

## Broad boundaries

**The latency answer — cache-only first paint.** Never fetch while painting. Render
last-known state tagged with its age; this is the pattern already proven by the
remote-only project start (PR #257), and the TTL cache exists precisely for it. A
refresh is then an *explicit* action: fetch all registered projects concurrently
under one global deadline, rows resolving independently, never blocking the UI.
Worst case must be bounded by the deadline, not by N × the 10s per-repo timeout.

**On the "pull latest from everything" button — push back.** Fetch is safe and
universal; pull is not. A fleet-wide pull mutates N working trees, breaks on dirty,
detached, ahead, or diverged checkouts, and is exactly what the existing rule
forbids ("Fleet review names its truth layers … neither is blended or pulled").
Proposed line: **fetch fleet-wide, pull only per-project, only offered when that
repo is clean and fast-forwardable.** And note that for most projects the correct
action is not "pull" but *resume this project* — which already runs preflight with
an explicit fetch. The indicator's job is routing the owner to the right project,
not turning the TUI into a git client.

**On the GitHub-identity panel.** `gh auth status` gives the login cheaply, and
`doctor machine` already checks it. Two cautions: it is machine-global, not
per-project, so it does not belong on project rows; and it is a *different axis*
from the Claude/Codex account panel it would sit under — GitHub identity vs agent
accounts. Placing them adjacent without naming the distinction invites the reading
that the agent account and the GitHub account are one thing. It also changes almost
never, which is weak justification for permanent screen space.

**Collision — RESOLVED (2026-07-29).** `tui-fleet-artifact-refresh` adds an outbound
refresh action; the risk was two same-named verbs on one surface. Resolved by the
naming split: that screen is **"Horus Assets Refresh"** (assets, outward) and the
inbound git action is **"Sync"** (state, inward, matching the shipped `horus sync`
CLI verb). This card owns the **see** half (render "behind N"); the inbound **act**
(the Sync button + fleet Sync-all) is `cockpit-sync-action` (order 40), sequenced
after this one.

Non-goals: no background polling loop; no auto-pull; no new fetch implementation;
not the write-heavy Horus Assets Refresh that the other card owns; **not the Sync
button itself — that is `cockpit-sync-action`.** This card renders freshness and
provides the explicit fleet-fetch trigger only.

## Decisions — RESOLVED in refine (2026-07-29)

- **Placement → freshness on each project row on Home.** The card's own job is
  "routing the owner to the project that needs attention," which argues for per-row
  over a separate section; a dedicated section would duplicate the signal. Show
  `current` / `behind N` / `unknown` plus the age of the reading, on the row.
- **GitHub-identity panel → dropped.** It is machine-global (not per-project),
  changes almost never, and `doctor machine` already checks it — weak justification
  for permanent screen space. Out of scope for this card.
- **The two "refresh" verbs → resolved by the naming split** (see the Collision
  note): "Horus Assets Refresh" (out) vs "Sync" (in). No shared verb remains.
- **Explicit refresh scope → strictly git freshness.** This card's fleet fetch
  updates remote-behind state only; usage/accounts stay on the existing `u refresh`.
- **Offline/unreachable → per-row `unknown` with age**, inherited from the
  primitive's silent no-op. Confirmed.

## Source

In-session brainstorm, 2026-07-20 (owner-attended), from the owner's own TUI
friction on the Windows machine. Prior art the owner named: the abandoned browser
dashboard explored this direction before the TUI became the cockpit.

## Reviews

- **2026-07-29 — Minted Ready/attended, `order: 30` (owner, refine pass).** All five
  open decisions resolved above (placement → per-row on Home; GH-identity panel →
  dropped; refresh-verb collision → resolved by the "Horus Assets Refresh" vs "Sync"
  naming split; refresh scope → strictly git; offline → per-row unknown+age). Scoped
  to the **see** half only; the inbound **act** (Sync button + fleet Sync-all) was
  carved into `cockpit-sync-action` (`order: 40`), which `depends-on` this card.
  Placed at 30/40 (after the existing `order: 10`/`20` attended cards) to avoid a
  queue collision, not as a priority call — reprioritize freely.
  `parallel: exclusive` because it and the act card both edit the hot `terminal_tui.py`.
  Attended, not eligible: it changes first-paint UX and wants a real render-confirm.
