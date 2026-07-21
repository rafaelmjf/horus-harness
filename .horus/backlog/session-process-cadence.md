---
status: open
priority: medium
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "A real revisit with a known failure to avoid (the deleted session-mode axis, #368). The efficient-cadence design is open and must NOT reintroduce frontloaded launch modes. Explore directions before drafting."
phase: explore
type: chore
vision_facet: "Continuity core"
---

# session-process-cadence — a more usage-efficient continuity/ceremony cadence, without reviving launch modes

## Why — owner, 2026-07-21

The per-session *process cadence* — how often continuity happens, PR granularity, and the
merge ceremony — is more expensive than it needs to be. Today's session is the evidence:
**8 PRs just to grow the backlog** (great for continuity/durability, poor on usage
efficiency). Two concrete frictions:

- **PR / continuity granularity.** One-PR-per-card, merged immediately, is durable but
  burns CI + merge overhead for bulk capture work. Surfaced this session: the granularity
  is an agent judgment call, *not* a rule — so it can be tuned.
- **The merge gate blocks topic-jumps.** `horus close --check` refuses a merge on
  Unclassified cards, which strands you if you need to jump to another topic before
  running backlog-refine (see `close-check-unclassified-cards-advisory`).

## The failure to avoid (learned — do not repeat)

We already tried "modes" and they failed:

- `launch-mode-process-skill` / **inline-batch** attached a posture skill at launch
  (#307, #326), then **All Gas No Breaks** (#360, aimed mainly at Codex) to strip ceremony.
- They frontloaded skills at session start, cost a turn, and delivered inconsistently — so
  the whole session-mode axis was **deleted in #368** ("Delete the session-mode axis; one
  launch form, one continuity rule"). CLAUDE.md now codifies "no session mode … context
  chosen at launch, authority is the permission posture."

Current state is the deliberate in-between: cheap (no frontloaded skills) but continuity
still runs often. This card revisits *efficiency* — WITHOUT reviving frontloaded modes.

## Candidate directions (open — sketches, not decisions)

- **One session branch, merge at the boundary (leading):** push each capture to a
  *single* session branch as you go — durable, never stranded — and merge that one branch
  ONCE at the real boundary (session end / pause), not per card. This separates "don't
  strand" (commit + push, incremental) from "don't over-ceremony" (merge, once) — the
  tension that drove the eager per-card merging. The boundary is the session end, not each
  capture moment. (This card's own final PR is meant to demonstrate it.)
- **Un-block topic-jumps at the gate:** make Unclassified advisory (that IS
  `close-check-unclassified-cards-advisory`) so ceremony never strands a jump.
- **Cadence as behaviour, not launch-mode:** any "do a lot in a row, checkpoint at the
  boundary" posture should be an in-session behaviour the agent adopts from the *work*,
  not a skill loaded at launch (the #368 lesson).

## Non-goals

- **Do NOT reintroduce frontloaded session-mode skills** (inline-batch / all-gas —
  deleted in #368 for good reasons). This is behavioural cadence + gate ergonomics, not a
  launch-mode revival.
- Not relaxing delivery safety — branches / commits / pushed refs / gates stay durable.

## Evidence

- Mode trail: **#307**, **#326** (inline-batch), **#359** (delegation / inline-batching
  calibration), **#360** (All Gas No Breaks) → **#368 deleted the axis**.
- `close-check-unclassified-cards-advisory` — the topic-jump block, filed from a
  pbi-ecosystem session.
- This session (2026-07-21): 8 PRs / ~12 cards, all continuity, mobile-driven.
- **Mid-session recurrence (2026-07-21), the sharpest datum:** even *after* this card was
  written, the pattern repeated — a PR was batched (2 items) yet still **merged
  immediately while the session had more work coming**. Owner caught it. The failure isn't
  per-card-vs-batched PRs; it's treating every capture as a continuity *boundary* and
  merging, when the boundary is the session end / pause (the CLAUDE.md rule already says
  "consolidate once at a real boundary"). A written instruction — freshly carded, even —
  did NOT hold the behaviour, which is direct evidence the control may need a stronger
  rung than instruction (per the repo's instruction → deterministic-signal → hard-guard
  ladder).

## Related

- `close-check-unclassified-cards-advisory` (the gate-ergonomics half).
- `continuity-sync-friction` (staleness + frontmatter hotspot — different friction, same
  "make continuity cheaper" family).
- `concurrency-safe-continuity` (the parallel-agent regime).

## Source

In-session process discussion, 2026-07-21 (owner: "today is an example of a proper session
that did 7 PRs just to grow the backlog … not that efficient in terms of usage").
Instruction/skill targets: the CLAUDE.md continuity-cadence rules + the `gh pr merge` /
`horus close --check` gate.
