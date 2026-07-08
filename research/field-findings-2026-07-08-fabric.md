# Field findings from fabric session — workflow enforcement gaps (2026-07-08)

> Committed under `research/` (not `sessions/`) deliberately: session notes are
> git-ignored/local by contract, and these findings must be readable from any
> machine before the next horus-harness session.

**Source:** a full working session in `fabric-metadata-driven-medallion` on this
Windows machine (Claude Code), 2026-07-08 — the fabric-utils repo split + cleanup.
Written here as a findings drop for the next horus-harness session; no harness code
was changed. Findings were re-verified against **current main** (after pulling a
21-release-stale local clone — see F3, which is itself evidence).

## The user's target workflow (canonical statement, verbatim intent)

Pull latest before working → implement on a feature branch → open a PR, merge when
no issues → consolidate changes and merge to main, so work can continue on any
machine via Horus continuity.

## Findings

**F1 — [bug] Claude's PowerShell tool bypasses every Bash-matched hook.**
`native_hooks.py` registers the close (merge) and guard-host PreToolUse hooks under
`matcher: "Bash"` (default at ~L195; call sites ~L484/L498). On Windows, Claude Code
exposes a **PowerShell tool** and the agent prefers it — the entire fabric session
(commits, merges available, two pushes to main) ran through PowerShell with zero
firings of those guards. The `commandWindows` half is already solved (hook-guard
invariant); the *matcher* half is not. Hook matchers are regex on tool name, so
`"Bash|PowerShell"` is likely the whole fix (or empty matcher + fast tool-name
filter in the command). Affects the new `checkpoint --hook` reach too, wherever it
uses a Bash matcher. Suggest a regression test in `test_native_hooks.py` asserting
the matcher covers both shell tools.

**F2 — Satellite repos run stale hook generations until `upgrade-project` reaches
them.** fabric's `.claude/settings.json` (checked today) has the pre-`commandWindows`
hook payloads and predates the checkpoint Stop hook shipped 2026-07-08. Harness-side
this is a solved problem (projection-sync badge, `upgrade-project --all`, hook
generation stamps already in the backlog) — the field observation is simply: the
pending "[ops] Windows machine" backlog item is load-bearing; until it runs, the
strongest enforcement (checkpoint gate) exists only in repos scaffolded after it
shipped. Consider: dashboard/doctor surfacing "hooks N generations behind installed
CLI" per project (the projection-sync badge may already cover this — verify it
compares hook payloads, not just skills/blocks).

**F3 — Fetch-first is still discipline, not signal (live demo).** This machine's
horus-harness clone was **21 releases behind** (v0.0.5-era); I initially grepped
`native_hooks.py` on the stale tree and nearly filed an already-fixed finding
(missing `commandWindows`) as new. Same morning, fabric was only pulled because the
user asked. The fetch-first rule lives in managed-block text + `next_prompt`
convention; nothing deterministic fires at session start. Cheapest surface consistent
with "hooks advise, never override": a `UserPromptSubmit` (or SessionStart) hook that
does a cached behind-origin check and *injects a warning line* — the enforcement
analogue of `close`'s fetch-first guard, at the other end of the session. Ties into
the MVP2.5 git-aware overview item.

**F4 — Branch→PR policy is not yet projected, and direct-to-main goes unchallenged.**
In fabric I committed straight to main twice (refactor + continuity) and nothing
advised otherwise — consistent with current state (workflow-policy projection into
the managed block is an open backlog item; fabric has no required checks). Evidence
that of the user's four workflow stages, only "consolidate + push" currently has a
working gate (`close --check`, checkpoint gate) — stages 1–3 (pull-latest, feature
branch, PR) are convention only. The open "Workflow-policy" + "CI gate promotion /
init installs merge gate by default" backlog items are the right fixes; fabric is a
ready test satellite (it now also has a second repo, `fabric-utils`, born today with
no `.horus/`, no hooks, no remote until explicitly pushed — the "ungoverned satellite"
case).

**F5 — Copilot as the 3rd agent target: the rulesync trigger fires.** User intends a
Copilot-agent feature soon. Per the standing decision ("stay direct at two tools,
adopt rulesync at the 3rd; own the behavioral layer always"), Copilot should NOT be a
third hand-maintained projection — it's the trigger for Layer-1 via rulesync +
Layer-2 behavioral adapter only. The user's own words today: "I might just be working
on too many things at once, especially maintaining codex/claude" — the maintenance
pressure the decision predicted.

## Improvement suggestions beyond the findings (fresh-session checks)

- **Per-tool-call hook spawn cost:** fabric's PreToolUse wiring spawns up to three
  `horus` processes per Bash call (close + guard-host + usage guard). On tool-heavy
  sessions that's a real latency tax (Python process start each time). Measure; if
  material, consider one dispatcher entry point (`horus pretool --hook`) that runs
  all checks in a single process, or matcher-level narrowing.
- **PRD line cap:** PRD.md is ~279 lines against the ~250 target — next consolidate
  pass should trim (Rules is the growth area; several entries could compress).
- **Requirements probing worked as designed:** fabric's `.horus/requirements.md`
  correctly predicted this machine (no `fab`) and the session stayed repo-side. The
  planned `doctor`/`resume`/dashboard surfacing item would have made that automatic
  instead of remembered.

## Next

For the next horus-harness session: F1 is the actionable bug (small, testable);
F2/F4 fold into existing backlog items as evidence + a live test satellite; F3 is a
design decision (session-start signal); F5 is a reminder that the Copilot feature
should start at the rulesync decision, not at a third hand-rolled projection.
