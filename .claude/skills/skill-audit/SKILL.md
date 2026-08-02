---
name: skill-audit
description: >-
  On-demand, evidence-first audit of ONE skill's text against reality: does
  every command/flag/path it references still match the live surface, where
  did real runs have to improvise around vague or missing instructions, and
  which of its internal steps became ceremony. Owner-invoked only ("audit the
  X skill", "test this skill", "improve this skill from that run") — there is
  deliberately no staleness advisory. Verdicts are revise (with the exact
  replacement text, owner-approved) / demote / defer / retire / no-change;
  the outcome lands in a dated `.horus/audits/` receipt. Never auto-edits a
  skill. For the whole product surface use `product-audit`; for one
  campaign's execution use `process-retrospective`.
---

<!-- horus-skill-version: 3 -->

# Skill audit — one skill's text vs reality

**Scope: Horus's own bundled skills, in the horus-harness repo.** This audits
skills whose source is `horus/skills.py`, so it is not installed into managed
projects — a consumer project has the projected `SKILL.md` copies but not the
generator that writes them, and a verdict there would have nowhere to land.
Auditing a target project's *own* skills is not supported yet.

You are auditing the *text* of one skill against how the world and its real
runs actually behaved. This is distinct from `product-audit` (the whole
product surface, prune-only, can never propose growth) and
`process-retrospective` (one campaign incident). This skill's whole purpose
is amendment — its verdict set includes the one thing product-audit forbids:
proposing better text.

## When this fires

- The owner asks to audit, test, or improve a specific skill.
- A real run just exposed the skill's instructions failing: the agent had to
  improvise, a referenced surface didn't exist, a step was ambiguous.
- **Never** on a schedule. There is no deterministic trigger by design;
  propose one only after un-audited skill drift causes an observed field
  failure (the control ladder, applied to itself).

## Scope: one skill per audit

Name the skill under audit before reading anything. Do not widen into a
sweep of the whole bundled set — that is a series of audits, each bounded.

## Questions (evidence, not recall)

1. **Fidelity.** Check every claim the skill's text makes against the live
   surface: commands and flags against `horus --help` / `horus <cmd> --help`,
   file paths and structure against the actual repo, named integration points
   against the code. Every mismatch is a finding — skills are instruction-ware
   and drift silently as the product moves.
2. **Executability.** Run the skill for real on a genuine trigger, or replay
   its most recent real run from the receipt/conversation. Log every place
   the executing agent improvised, interpreted ambiguity, fell back, or
   skipped ahead. Each improvisation is a missing or vague sentence in the
   skill — the gap is in the text, not the agent.
3. **Internal ceremony.** Which of the skill's own steps were skipped or
   rubber-stamped across recent invocations? A step every run bypasses is
   evidence against the step.

## Verdicts — five, because amendment is the point

Per finding: **revise** (propose the exact replacement text as a diff — the
owner approves before anything is edited), **demote** (weaker rung),
**defer** (revisit with the reason), **retire** (propose removal — the owner
acts), or **no-change**.

Applying an approved revise to a bundled skill means editing its constant in
`horus/skills.py` and bumping that skill's version marker, landed by PR like
any product change. Never edit the projected `SKILL.md` copies directly —
they are regenerated and the edit would be silently overwritten.

## Close the audit

- Write the receipt: `.horus/audits/<YYYY-MM-DD>-skill-<name>.md` — one page,
  never a transcript: verdict table (finding | verdict | one-line evidence),
  defers with reasons, and for each revise a pointer to the applied version
  bump (or its pending state).
- This skill audits itself under exactly the same rules — when its own
  instructions needed improvising around, that is a finding here.

## Two invariants an audit must check first

- **A skill's DESCRIPTION is where an invocation boundary lives.** The body is read
  only after the load decision is already made, so a correct boundary section in the
  body cannot stop a false trigger. Corollary for tests over skill prose: assert on
  **whitespace-normalized** content, since hard-wrapping breaks a raw-substring
  assertion on reflow rather than on meaning.
- **Any edit bumps the skill version, always.** The version-aware install skips
  same-version content, so an unbumped text change leaves committed projections
  silently stale. `Skill(name, N, text)` and the `horus-skill-version: N` marker
  inside that text are two copies of one number; when they disagree every
  `upgrade-project` reports "updated" forever while doctor never goes green. Resync
  with `horus skill install --force` (from working-tree source); never hand-edit a
  projected `SKILL.md`.

## Boundaries

- Advisory only: nothing is edited, demoted, or retired without the owner's
  approval of the specific diff or proposal.
- One skill per invocation; no telemetry; no new trigger machinery.

## v2 six-lane projects (fallback)

Structure-agnostic: the receipt still lands in `.horus/audits/` (the
directory is independent of PRD structure), and the fidelity check compares
each skill's v2 fallback section against the six-lane layout the project
actually uses — a skill whose fallback describes lanes the project no longer
has is a revise finding.
