---
status: shipped
priority: medium
created: 2026-07-20
created_by: owner
last_refined: 2026-07-20
readiness: ready
autonomy: eligible
readiness_reason: "Artifact chosen by the owner 2026-07-26: the Horus-managed block's working discipline in templates.py, so it reaches every project, both agents, and all machines — the exact sharing failure this card is about. Remaining work is one tight instruction line plus the memory sweep, both bounded."
last_refined: 2026-07-26
tier: small
parallel: safe
phase: converge
type: bug
vision_facet: "Introspection & self-improvement"
surface: "horus/templates.py (_SHARED_BODY working discipline + BLOCK_VERSION bump), projected CLAUDE.md/AGENTS.md blocks, tests/test_templates.py"
shipped_pr: 410
shipped_sha: 7b6334d
---

# process-fixes-live-in-process-not-memory — shared artifacts, not one agent's recall

## Why

**Owner rule (2026-07-20, general to all Horus projects):** a mistake that is an
error in the process must be fixed in the process itself — skills, managed
blocks, PRD Rules, cards — never only in an agent's private memory, because
agent memories are not shared across agents and accounts. Observed instance:
after auto-merging a format-contract change without a rendered confirmation
(the `merge-release-owner-gate` failure class, evidence in that card's
Reviews), the corrective "render-confirm before merging contract changes"
discipline was written into the Claude agent's memory — invisible to Codex,
other accounts, and other machines.

## Intended outcome

The render-confirm-before-merge discipline lives in **the Horus-managed block's
working discipline** (`horus/templates.py` `_SHARED_BODY`), sitting alongside
"Reproduce the gate; never trust the report" — chosen by the owner 2026-07-26 because
it propagates to every project, both agents, and every machine on upgrade, which is
precisely the sharing failure this card exists to fix. It must be **one tight line**,
not a paragraph: this text is loaded by every session. `BLOCK_VERSION` bumps with it.

Plus a short sweep confirming no other 2026-07-20 calibration correction exists only
in agent memory (the questionnaire format and receipt spines already live in the
skills — verify, don't assume).

## Non-goals

- No new memory-sync machinery; the fix is putting rules where they already
  travel (repo artifacts).
- Agent memory may still carry pointers/copies — it just can't be the only home.

## Source

Owner correction 2026-07-20 in the calibration session;
`merge-release-owner-gate` Reviews entry of the same date.

## Acceptance

- The managed block carries a single-line render-confirm-before-merge discipline; both
  projected copies (`CLAUDE.md`, `AGENTS.md`) regenerate from `templates.py` and
  `BLOCK_VERSION` is bumped so `upgrade-project` refreshes downstream projects.
- The sweep result is recorded: for each 2026-07-20 calibration correction, either the
  shared artifact that already carries it, or the artifact it was moved into.
- Gate: full suite green on the exact SHA. Probe: scaffold a throwaway project and
  confirm the new discipline line appears in its `AGENTS.md` managed block.

## Reviews

- 2026-07-26 — Refined with the owner. **Artifact chosen: the managed block's working
  discipline.** Reach is the deciding factor — a rule that failed *because it lived in
  one agent's memory* is not fixed by putting it somewhere else narrow. The managed
  block travels to every project, both agents, and every machine on upgrade.
  `merge-release-owner-gate`'s scope was considered and declined: a card is read when
  someone works that card, not when a session is merely merging, which is exactly when
  the discipline is needed. PRD Rules alone was declined as repo-local.

  Constraint attached: **one tight line, not a paragraph** — this text loads in every
  session, and the managed block already has a `managed-instruction-drift-lint` card
  open against it. Minted **Ready / eligible**, tier small.

  Note the recursion: this card is itself the durable artifact for a rule that had been
  living in one agent's head, so filing it already did half the job.

## Sweep result — 2026-07-26 (verified, not assumed)

The card asked for a short sweep confirming no other 2026-07-20 calibration correction
lives only in agent memory. Checked:

- **Questionnaire format** — lives in the shared artifact. `horus/skills.py` carries the
  literal screen spec and the corrected rule verbatim: *"Strictly one card per exchange —
  one at a time, never batched"*, with the note that it was the twice-corrected failure
  mode. Nothing memory-only.
- **Receipt spines** — live in the shared artifact; the skill bodies specify them
  throughout (`product-audit`, `market-scan`, `roadmap-branches`, `scope-cards`,
  `process-retrospective`, `skill-audit` all name their dated receipt).
- **Render-confirm before merging a contract change** — this WAS memory-only. It is the
  one correction the sweep found unshared, and it is what this card moves into the
  managed block. Its evidence remains in `merge-release-owner-gate`'s Reviews (card still
  active, not archived), which stays the owner of the eventual hard guard.

Conclusion: one correction was memory-only, now fixed; the other two were already durable.
