---
status: open
priority: low
readiness: shaping
readiness_reason: "The launch-defaulting use is well-motivated, but the field's second consumer (fleet alias discovery) is worth less than it first appeared, and the auto-stamp point needs picking. Shape before building."
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
vision_facet: "Accounts & isolation"
tier: medium
type: feature
parallel: safe
phase: explore
surface: "PRD.md frontmatter key; horus/closure.py (auto-stamp from registry); horus/terminal_tui.py (launch account default); horus/github_catalog.py (already parses remote PRD frontmatter)"
---

# prd-worked-by-account — record which account(s) a project's work actually happened under

## Why — the primary case is launch defaulting, not discovery

Claude Code keys transcript history **per config dir**: ambient runs land in
`~/.claude/projects/<slug>/`, isolated accounts in
`~/.horus/accounts/<agent>-<alias>/projects/<slug>/` (recorded in
`new-machine-setup-guidance`, 2026-07-20). So launching a project under the wrong
account silently orphans its history — the session starts, nothing errors, and the
prior context is simply absent.

Today nothing records which account a project's work lives under, so the owner has to
remember per project. A `worked_by` frontmatter key lets the TUI **default the launch
account to the one the project was last worked under**, which is the same
don't-rely-on-recall argument that motivates the discovery case below, applied where
the data is local to the project.

## Secondary case — cross-machine alias discovery (weaker than it first looked)

Owner's concern (2026-07-20): when replicating a setup on a new machine, the risk is
**getting an alias wrong** — `claude-work` vs `work-claude` vs `claude work` — which
recall cannot be trusted with, and a wrong alias silently creates a *new* account
rather than reusing the intended one.

`worked_by` would make the alias set discoverable without a clone, because
`github_catalog.discover()` **already fetches `.horus/PRD.md` from every remote Horus
repo and parses its frontmatter** (`github_catalog.py:178-179`) — reading one more key
is a couple of lines, and `gh auth login` is a prerequisite for onboarding anyway. A
2026-07-20 probe confirmed 7 remote Horus projects resolve for owner `rafaelmjf` from
cache, no clone required.

**But measured against reality it earns little:** the owner's canonical set is three
aliases (`claude-personal`, `claude-work`, `codex-personal`), stable across machines.
Discovery would do a `gh` round-trip across 7 repos to rebuild a 3-element list — and a
same-day probe confirmed **no PRD carries any account key today**, so it returns empty
until every project has closed once after the feature ships. Machine two (Linux) will
be manual regardless. The cheap fallback — run `horus account` on the old machine and
transcribe two lines of authoritative output — removes the typo risk just as
completely, without a feature:

```
$ horus account
isolated accounts: claude-personal, claude-work
$ horus account --agent codex
isolated accounts: codex-personal
```

**Therefore: justify this card on launch defaulting alone.** Fleet discovery is a side
effect it enables later, not a reason to build it. If the account set ever grows past
what the owner can recite, revisit.

## Design constraints

- **Derive it; never hand-maintain it.** `registry.SessionRecord.account`
  (`registry.py:137`) already records the account per session, machine-locally.
  Auto-stamp `worked_by` at close from the registry. A hand-written list drifts, and a
  drifted list is worse than none because it reads as authoritative.
- **It must change a behavior on day one.** Per this repo's agent-first boundary,
  structure earns its place by making a session act more correctly or cheaply. Wired to
  the TUI launch default it clears that bar; as a field nothing reads it is a log, which
  the same rules warn against.
- **Aliases stay generic.** Once stamped into committed PRDs across a fleet, aliases
  become structured, harvestable public data. They are already non-secret by design
  (the real email never lands in a commit — that rule holds; `accounts.toml` is
  machine-local and gitignored) and already appear in committed prose across 20+ files,
  so this adds no exposure *in kind*. But keep aliases to `personal` / `work` and never
  a client or employer name — cheap now, annoying to retrofit fleet-wide later.
- **One field with a consumer beats four fields with none.** Frontmatter is cheap to
  add and expensive to retire, since every reader must tolerate both shapes forever.
  Treat "more metadata fields later" as a pattern, not a plan.

## Acceptance (draft)

- `worked_by` is stamped at close from the registry, listing the account aliases that
  ran sessions in this project.
- The TUI launch screen defaults to the project's most recent `worked_by` account,
  overridable as now.
- Absent/empty `worked_by` changes nothing (every existing project keeps working).
- Gate: full suite green on the exact SHA. Probe: close a project after a session under
  one account; confirm the field appears and the next TUI launch preselects it.

## Source

Owner proposal + evidence probe, 2026-07-20.
