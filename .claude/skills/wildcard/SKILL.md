---
name: wildcard
description: >-
  Owner-invoked (or scheduled) AUTONOMOUS divergence→one-card skill — the safe
  autonomous sibling of pathfinder. Grounded on a pathfinder run's saved evidence
  (fresh or previous: position brief, product-audit, market-scan, roadmap-branches),
  it diverges under several independent frames, critiques/converges, and emits ONE
  evidence-grounded candidate backlog card for the owner to revise / approve / discard.
  Safe to run unattended because the output is a card (bounded, reversible) — it never
  sets direction, never implements, never edits the backlog. Use when the owner says
  "run wildcard", "surprise me with an opportunity", "what am I missing", or schedules an
  away-mode discovery job. NOT autonomous convergence (direction stays owner-gated via
  pathfinder) and NOT a card factory (one self-critiqued card per run).
---

<!-- horus-skill-version: 1 -->

# wildcard — autonomous divergence → one grounded candidate card

**Status: v0 (calibrated 2026-07-21; not yet bundled).** This SKILL.md is the working
draft. The `wildcard` backlog card drives refinement; registering it in
`horus/skills.py` (byte-identical dual-install + version wiring) is a dedicated-session
step. The "previous run" grounding depends on `pathfinder-structured-outcome`.

## What it is / hard boundaries

- **Advisory, owner-gated, bounded output.** Emits exactly ONE candidate backlog card as a
  *proposal*. NEVER sets direction, NEVER implements, NEVER creates/edits cards until the
  owner accepts the proposal.
- **Safe to run unattended** precisely because the output is a card — reversible, zero
  blast radius. That is why divergence can be autonomous while pathfinder's convergence
  stays attended.
- One card per run, self-critiqued. Not a flood.

## Grounding — a pathfinder run (never free-roaming)

- **Previous run (default):** load the last pathfinder run's artifacts — position brief,
  product-audit receipt, market-scan receipt, roadmap-branches divergence tree (see
  `pathfinder-structured-outcome` for the run bundle/manifest). Cheap; if the run is old,
  say so and cite the artifact dates.
- **Fresh run:** if the owner wants current evidence, run pathfinder's evidence steps
  (product-audit / market-scan) first, then proceed. More costly.
- **Fallback:** if no pathfinder run exists, ground on the live session's accumulated
  context plus the backlog — and SAY that is the grounding (as the 2026-07-21 calibration
  did). Every emitted card cites the specific artifacts/signals it was grounded in.

## Procedure

1. **Diverge — N isolated frames.** Generate ~5-7 candidate opportunities, each from a
   DISTINCT frame (e.g. shipped-vs-used, recurring friction, an underserved user domain,
   cost/efficiency, decay/staleness, autonomous-safe automation). Each frame reasons from
   the grounding evidence independently — frames must not anchor on each other. (Prior
   art: the isolated-branches / no-cross-anchoring design in github.com/uditakhourii/adhd.)
2. **Converge — critic pass.** Score every candidate and REJECT with explicit reasons:
   too big (a direction change, not a card) · too obvious / top-of-mind · already covered
   by an existing card or skill · too abstract to scope. Check each against the existing
   backlog so the winner is not a duplicate. Prefer the NON-OBVIOUS, well-grounded,
   well-scoped survivor.
3. **Emit ONE candidate card** — a proper draft (Why with cited grounding · rough shape ·
   open questions · non-goals · source) PLUS a short trace of the divergence set and why
   the winner beat the rejects. The trace is the owner's calibration signal.

## Output

- The ONE candidate card (draft — owner revises/approves/discards; only then is it written
  to `.horus/backlog/`).
- The divergence + critique trace (compact): each frame considered and the one-line reason
  it lost — so the owner judges the reasoning, not just the result.

## Quality bar

- Exactly one card; cite its grounding; must be non-obvious (surface something not already
  carded or top-of-mind); self-critiqued against the backlog for duplication.
- If nothing clears the bar, say so and emit NO card — better than backlog spam.

## Non-goals

- Not autonomous convergence — direction/roadmap choice stays owner-gated (pathfinder).
- Not autonomous implementation — an accepted card follows refine → approve → implement.
- Not a card factory — one per run.

## References

- Backlog: `wildcard` (refinement driver), `pathfinder-structured-outcome` (grounding
  substrate), `pathfinder` / `scope-cards` / `market-scan` (divergence machinery reused),
  `autotest-e2e-away-mode-drill` (safe autonomous-loop food).
- Prior art: github.com/uditakhourii/adhd (isolated N-frame divergence + separate critic).
- Calibration: 2026-07-21 dry-run (grounded on the live session) produced the
  `backlog-librarian` card; the owner judged the output good → this v0 draft.
