---
status: open
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: shaping
readiness_reason: "The plumbing question is settled (the signal already exists) but the placement, the refresh trigger's blast radius, and whether the GitHub-identity panel earns permanent space are undecided. Refine before building."
phase: converge
type: feature
vision_facet: "Dashboard / cockpit"
surface: horus/terminal_tui.py, horus/fetchcheck.py, horus/fleet_review.py
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
  unrelated concept sharing the word. Reusing "stale" for remote-behind will
  confuse both.

**So this card is presentation and trigger, not plumbing.**

## Intended outcome

Opening the TUI answers "is what I am reading current?" without a fetch in the
paint path, and routes the owner to the project that needs attention.

## Acceptance (EARS-lite)

When the TUI opens with cached fetch state on disk, it should render each
project's remote-freshness (current / behind N / unknown) with the age of that
reading, without performing any network call during first paint.

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

**Known collision:** `tui-fleet-artifact-refresh` (gated) also adds a "Refresh"
action to the TUI, for *projection artifacts*. Two differently-scoped refresh verbs
on one surface is a UX problem to resolve deliberately, not discover later.

Non-goals: no background polling loop; no auto-pull; no new fetch implementation;
not the write-heavy projection refresh that the other card owns.

## Open decisions for backlog-refine

- Placement: freshness on each project row on Home, a dedicated section, or both.
- Does the GitHub-identity panel earn permanent space, or is `doctor` enough?
- How the two "refresh" verbs coexist (naming, or one entry point with two scopes).
- Whether an explicit refresh also refreshes usage/accounts, or strictly git.
- Behaviour when some projects are offline/unreachable — per-row unknown with age
  is the presumed answer, inherited from the primitive's silent no-op.

## Source

In-session brainstorm, 2026-07-20 (owner-attended), from the owner's own TUI
friction on the Windows machine. Prior art the owner named: the abandoned browser
dashboard explored this direction before the TUI became the cockpit.
