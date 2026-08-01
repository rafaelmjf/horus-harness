---
status: shelved
shelved_on: 2026-08-01
priority: low
readiness: shaping
readiness_reason: "Narrowed 2026-07-28: three of the five lifecycle steps are answered by the card's own field evidence, so the dedicated brainstorm is now scoped to the two that are not — SELECTION (which projects AND which skill classes) and INTEGRATE (nothing drives the commit/PR after the write). Both are [session]-class design questions, which is why this stays Shaping."
created: 2026-07-17
last_refined: 2026-07-28
refine_passes: 2
tier: medium
type: feature
vision_facet: "Introspection & self-improvement"
parallel: safe
surface: horus-managed project artifacts, upgrade/skill detection, fleet refresh planning, git workflow integration, remote verification
---

# Unified Horus artifact refresh — detect, preview, integrate, verify

Reinstalling or upgrading the Horus CLI does not refresh what Horus previously wrote
inside initialized projects. Bundled skills are the observed failure, but the product
problem is broader: managed instructions, hooks, workflow dependencies, and other
project artifacts can all lag the installed CLI. Detection, update, git integration,
and remote verification currently feel like separate partial operations.

## Narrowed scope (2026-07-28) — two steps, not five

The card's own field evidence (both sections below) answered three of the five steps, so the
brainstorm no longer needs to design them:

| Step | State |
|---|---|
| **Detect** + **Refresh** | **Answered.** "One command sufficed" — `upgrade-project --apply` covered blocks, all skill projections and hooks in one pass; the separately-advertised `skill install` path was never needed. The "two paths, no contract" concern **may reduce to a documentation fix.** |
| **Verify** | **Answered.** "Dry-run → apply → dry-run-zero is a clean idempotence receipt" — exactly the deterministic refresh-complete signal the lifecycle wanted. Caveat to carry: consumer repos may have no required checks, so Verify cannot assume they exist. |
| **Selection** | **OPEN — the hard part.** Per-project AND per-skill-class, not just which projects. Two traps already documented below: worktrees masquerade as projects (four `horus-harness-wt-*` dirs would take managed-block commits onto stale worker branches), and dormant projects should be skipped, composing with `fleet-curation`'s lifecycle state rather than ignoring it. Scale matters: 126 stale installs spanning several versions, so the plan must be idempotent and resumable, never one transactional sweep. |
| **Integrate** | **OPEN — and observed failing.** pbi-ecosystem carried a stranded *uncommitted* projection refresh for days: the tool wrote, nothing drove commit/branch/PR. The lifecycle must own integration, not assume a human finishes it. |

The original five-step framing is kept below as the design's shape.

The dedicated shaping session must design one owner-visible lifecycle:

1. **Detect** every Horus-managed artifact that is missing, stale, customized, or
   ineligible for automatic replacement.
2. **Preview** the exact per-project diff and repository workflow before writing.
3. **Refresh** only approved managed assets without overwriting unversioned/customized
   content silently.
4. **Integrate** through the target project's normal branch/commit/push/PR policy.
5. **Remote-verify** that the delivered default branch contains the new artifacts and
   the local checkout is clean and synchronized.

Existing evidence includes:

- The nudge is a passive one-line `tip:` after routine commands that lists every
  bundled skill name without distinguishing "not installed" from "outdated"; it reads
  as an ad and is easy to ignore.
- The launch/resume path does not check at all: a session can be launched in a mode
  whose posture skill is not installed and the mode silently degrades.
- There is no fleet-wide view: after a CLI upgrade, nothing tells the owner which of
  the N registered projects are behind. Only a per-project `horus doctor` shows it,
  and nothing prompts running doctor after an upgrade.
- Two refresh paths are advertised (`horus upgrade-project --apply --target X` and
  `horus skill install --target X`) without one end-to-end contract.

**Evidence (2026-07-17, horus-agent):** a session was launched in `inline-batch` mode
(the launch-mode skill shipped in PR #307 / v0.0.60) but `inline-batch-session` was not
installed in the project, so the mode's posture instructions were silently absent. A
manual `horus skill install --target claude` then created 9 missing skills and updated
4 stale ones (horus-execution v13, delegation-rubric v8, execution-decision v3,
dispatch-decision v3) — none of which had surfaced as an actionable warning in the
normal resume/consolidate/close flow.

The related [[tui-fleet-artifact-refresh]] card already carries a detailed candidate
fleet workflow. It remains Gated on this shaping verdict so the session can decide
whether that card is the implementation, a child, or should be merged here.

## Open decisions

- **Selection** granularity: which projects, and which skill classes within a project.
  [session] — the hard design question this card exists for.
- **Integrate**: what drives commit/branch/push/PR after the write. [session]
- Whether `tui-fleet-artifact-refresh` is the Integrate implementation card, a child, or a
  duplicate to retire. [session] — this card's Exit clause owes that disposition; it was
  deliberately NOT exercised on 2026-07-28, so that card stays Gated here.
- Whether the "two advertised paths" concern is just a documentation fix. [refine] — the
  2026-07-20 evidence says probably yes.

## Shaping questions

- Which artifacts are genuinely Horus-managed and how is customization distinguished
  from stale generated content?
- Is there one canonical refresh service with skill-only/project/all projections, or
  separate commands sharing one plan/apply/integrate core?
- Which safety states must skip a project versus pause for an attended decision?
- How should launch-time warnings relate to fleet-wide refresh without becoming noise?
- Does the existing TUI fleet card remain the delivery card after this brainstorm?

## Exit

End the dedicated owner session with one bounded architecture and a disposition for
[[tui-fleet-artifact-refresh]]: merge, rescope as the implementation card, or retire as
duplicate. Then run `backlog-refine` before promoting any delivery card to Ready.

## Non-goals while Shaping

- No narrow warning-only fix before the full lifecycle is understood.
- No silent mass rewrite, auto-stash, force push, or bypass of repository policy.
- No assumption that skills are the only managed artifact that can drift.

## Reviews

- 2026-07-28 — **Brainstorm narrowed from five steps to two** (owner, refine pass). Detect,
  Refresh and Verify were answered by this card's own field evidence from the two 2026-07-20
  hand refreshes; only Selection and Integrate remain genuinely open, and both are
  `[session]`-class, which is the honest reason this card has not converted. Priority left at
  low.

  Also settled, confirming the 2026-07-26 librarian's read: **`skill-self-calibration-probe`
  stays a separate card.** Adjacent but not duplicate — this card is unified artifact-refresh
  *mechanics* (detect → preview → integrate → verify); that one is a replay PoC where a skill
  notices *its own* drift. Distinct intents; do not merge them.

  Deliberately not done: `tui-fleet-artifact-refresh` was NOT freed from its gate on this
  card, even though its acceptance criteria already specify the Integrate half in detail.
  That disposition belongs to the brainstorm, per this card's Exit clause.

## Field evidence — v0.0.73 made the fleet's prose stale (2026-07-19)

The drift this card describes stopped being hypothetical. v0.0.73 (#368) deleted
`continuity_granularity` from the code and rewrote the shared managed block, but only
this repo's block was updated. Every other project still teaches the retired setting:

```
agentic-cv-builder: granularity=1     agentic-ttrpg: granularity=1
agentic-gym-coach: granularity=1      fabric-metadata-driven-medallion: granularity=1
agentic-pbi-utils: granularity=1      fabric-utils: granularity=1
agentic-travel-guide: granularity=1   horus-agent: granularity=1
```

(grep for `continuity_granularity` in each `CLAUDE.md`; the consent sentence from #358
is absent because those blocks predate it — they are stale at *different* versions,
which is itself a requirement: refresh cannot assume one common baseline.
2026-07-20: fabric-metadata-driven-medallion and pbi-ecosystem refreshed by hand —
see the field-evidence section below; the other six remain stale.)

Impact is moderate, not urgent: behavior is correct everywhere because it lives in
code. The cost is an agent reading a paragraph about a knob it cannot find — the exact
prose-teaching-what-the-code-does-not-do failure #368 removed here.

**Selection is the hard part, not propagation.** `horus upgrade-project` does the write;
deciding *where* is the design question this card owns. Two traps found while surveying:

1. **Worktrees masquerade as projects.** Four `~/projects/horus-harness-wt-*` directories
   report the same staleness, but `git worktree list` shows they are worktrees of THIS
   repo parked on old branches (`feat-tui-backlog-field-picker`,
   `worker/campaign-supervision-launch{,-v2}`, `worker/provider-model-selector-contract`).
   Refreshing them would commit managed-block changes onto stale worker branches. Any
   sweep over a projects directory must exclude worktrees — check `.git` being a file
   whose `gitdir:` points into another repo, not a directory.
2. **Dormant projects should be skipped, not refreshed.** A project on hold does not
   benefit from a block update; that is churn against a repo nobody is touching. This
   needs to compose with `fleet-curation`'s lifecycle state rather than ignore it.

Also note the scale: `horus skill map` reports **126 stale skill installs** across the
fleet at v0.0.73, spanning several versions — so the refresh plan must be idempotent and
resumable, never one big transactional sweep.

## Field evidence — two hand refreshes at 0.0.73 (2026-07-20)

Owner-directed refreshes of `fabric-metadata-driven-medallion` (PR #24) and
`pbi-ecosystem` (PR #2), done by hand as branch → `upgrade-project --apply` →
PR → merge. Observations for the design session:

- **One command sufficed.** `upgrade-project --apply` covered blocks, all skill
  projections, and hooks in one pass; the separately-advertised `skill install`
  path was never needed. The "two paths, no contract" concern may reduce to a
  documentation fix.
- **Dry-run → apply → dry-run-zero is a clean idempotence receipt.** The
  post-apply report showing zero pending items is exactly the deterministic
  "refresh complete" signal the lifecycle's Verify step wants.
- **No per-skill selection exists.** fabric — a deliberately minimal-ceremony
  production BI project (the X6 tier-1 probe) — received all nine PO-ritual
  skills because refresh is all-bundled-or-`--no-skills`. Hand-pruning would
  create "customized/missing" drift noise on the next refresh. Selection
  granularity is per-project AND per-skill-class, not just which projects.
- **The Integrate gap is real and observed.** pbi-ecosystem carried a stranded
  *uncommitted* projection refresh (v5–v9 era) for days — the tool wrote, but
  nothing drove commit/branch/PR, leaving the tree dirty and the delivery
  invisible. Regenerating with the current CLI cleanly superseded it, but the
  lifecycle must own integration, not assume the human finishes it.
- **Remote-verify was manual.** Both repos have no CI checks (direct-merge
  fallback per git policy); "delivered main contains the artifacts" was a
  hand-run grep + version probe. The Verify step cannot assume required checks
  exist in consumer projects.

## Field evidence — stale skill produced WRONG WORK, not stale prose (2026-07-30)

The first observed case where drift cost real output rather than reading oddly.
`fabric-build` ran `product-audit` at **v2** while the released CLI carried v3 and
main now carries v4 (#463) — a *third* distinct baseline, confirming this card's
"refresh cannot assume one common baseline" requirement from a second angle.

What the stale copy did, beyond being stale:

- It framed a **fabric-build** audit as a **Horus** audit ("You are auditing Horus
  itself, not a target project"), so the run had to improvise the Fabric ecosystem
  in place of the Claude Code / Codex changelogs the skill names, and the project's
  own CLI verbs in place of hardcoded `horus/*` paths.
- It produced a receipt (fabric-build PR #61) carrying `demote`/`defer`/`retire`
  verdicts — reviving the "prune, never grow" verdict machine the owner retired on
  2026-07-20 — and deliberately **skipped the `last_product_audit` stamp**, because
  the frame made the stamp look like Horus's own bookkeeping.
- Owner decision 2026-07-30: **do not stamp that audit retroactively.** The
  anti-ceremony guard makes the next audit read the previous receipt, so stamping
  would install a retired-contract receipt as fabric-build's calibration baseline.
  The stamp should be written by the first properly-framed v4 run instead.

**This escalates the impact argument above.** The v0.0.73 section rates drift
"moderate, not urgent" because "behavior is correct everywhere because it lives in
code." That reasoning holds for managed *prose* about a knob, and does not hold for
**skills**: a skill's text IS its behavior, so a stale skill is a stale program. Skill
drift and block drift are not one impact class. Whether that should lift this card's
`priority: low` is a [refine] question, deliberately not decided here.

**New Selection trap — the active project on a busy branch.** The two traps recorded
above are worktrees and *dormant* projects. fabric-build is the opposite failure:
fully live, a running session, sitting on a feature branch
(`docs/declarative-config-and-ecosystem`). Refreshing it mid-flight would land managed
artifacts on someone else's working branch. So Selection needs liveness on BOTH ends —
skip dormant, and defer or isolate *busy* — which composes with session state, not just
[[fleet-curation]]'s lifecycle state.

**New Integrate constraint — refresh is gated by RELEASE, not by upgrade.** A fix
merged to main does not reach the fleet: bundled skills ship in the CLI, so
`upgrade-project --apply` in a consumer project installs whatever the *installed
release* carries. v4 existed on main and was unreachable to every consumer until a
release cut. Any refresh lifecycle must therefore treat "is the fix released yet" as a
precondition, or it will confidently refresh projects to a version that predates the
fix it was run to deliver.

**Owed follow-up (not yet done):** after the next release, refresh fabric-build via
branch → `upgrade-project --apply` → PR, taking product-audit v2 → v4, then re-run the
audit there so it writes its own stamp. Sequenced behind the release deliberately;
hand-writing the v4 projection now would be generated content committed by hand.

Source: issue #462, fixed by #463 (skill scoping) and #464 (`releases_since` clock).
