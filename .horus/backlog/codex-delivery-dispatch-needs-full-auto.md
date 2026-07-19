---
status: open
priority: high
created: 2026-07-19
vision_facet: "Autonomous dispatch"
phase: converge
tier: sonnet
type: bug
parallel: safe
created_by: agent
surface: horus/cli.py (horus run arg validation) + horus/schedule.py (schedule run arm-time check) — refuse/repair a codex delivery dispatch armed with a network-off sandbox posture
---

# codex-delivery-dispatch-needs-full-auto — a delivery dispatch that structurally can't deliver must be refused at arm time

**Why (observed field failure 2026-07-19, away-batch-3 drill):** the third real
away-mode dispatch — `codex-usage-window-semantics` → codex-personal — armed as:

```
horus run "…" --unattended --envelope away-batch-3 --account codex-personal \
  --agent codex --worker codex --effort medium \
  --worktree away/codex-usage-window-semantics --expect-delivery
```

The codex worker fully implemented the card, made the suite green, and committed
locally — then **could not deliver**: `--worker codex` selects the `auto-edit`
preset, i.e. the safe workspace-write sandbox with **network/socket access OFF**,
so `git fetch/push` and `gh pr` fail (`Could not resolve host: github.com`), and
the worktree's real git dir lives in the parent repo's `.git/worktrees/…` —
outside the sandbox's writable root — so even a local commit needs an out-of-band
`/tmp` clone. Net: 13m of work, no PR. `--expect-delivery` correctly flagged it
`delivery blocked`, but only *after* the spend.

The CLI already documents the cure (`horus run --worker` help, `cli.py:4692`):
codex git/PR delivery requires `--posture full-auto` (bypasses approvals AND
sandbox). So this is not a missing capability — it is a **mis-armed dispatch that
was structurally incapable of the delivery it was told to produce**, discovered
only by post-mortem. Per this repo's ladder (instruction → signal → gate) and
"safety in code, not the reviewer", the contradiction should be caught before the
worker is ever launched.

## How

- At `horus run` argument-validation time (and therefore at `horus schedule run`
  arm time, which shells the same command): if `--agent codex` resolves to a
  network-off sandbox posture (the `codex=auto-edit` / workspace-write preset, or
  any posture that is not `full-auto`) AND the run demands a git delivery
  (`--expect-delivery`, and/or `--worktree` whose only point is a branch to push),
  REFUSE with a clear message naming the fix (`--posture full-auto`), or
  auto-upgrade the posture with a printed note. Refuse-by-default is safer than a
  silent auto-upgrade for an unattended dispatch — pick refuse and make the
  operator opt in.
- Keep it a static pre-launch check (no real network/systemd) — the escape point
  is the *arming*, so guard the arming.
- Applies equally to a foreground `horus run` and a scheduled `horus schedule run`
  (the drill's path). One shared validator, both call sites.

## Acceptance

- `horus run --agent codex --worker codex --worktree B --expect-delivery` (no
  `--posture full-auto`) fails fast at validation with a message naming
  `--posture full-auto`, before any worker/tmux/worktree is created.
- The same combination with `--posture full-auto` is accepted unchanged.
- Claude delivery dispatches (whose `--worker` preset already bypasses the
  sandbox) are unaffected.
- `horus schedule run …` inherits the check (it arms the same `horus run` argv).
- Unit test over the validator: codex+delivery+non-full-auto → error; codex+
  delivery+full-auto → ok; claude+delivery → ok; codex+no-delivery → ok.

## Non-goals

- Not a change to codex's default sandbox posture for non-delivery runs (a
  read/implement-only codex run in the safe sandbox stays valid).
- Not a network-enablement mechanism — the fix is posture selection, which already
  exists; this only prevents the contradictory combination.
- Not related to the `codex-usage-window-semantics` card's own content (that card
  remains deferred pending upstream window stabilization; its away-batch-3
  implementation was not adopted).
