---
status: open
priority: medium
created: 2026-07-21
created_by: owner
last_refined: 2026-07-28
refine_passes: 2
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
- ~~The merge gate blocks topic-jumps.~~ **DELIVERED** — `close-check-unclassified-cards-advisory`
  shipped in #409 (v0.0.75): card readiness no longer blocks a merge and `close --check` gates
  freshness only. This half of the card is closed; only granularity remains live.

## Scope after the 2026-07-28 rescope — one mechanism, two lanes

This card owns the **granularity policy**, and the policy has two lanes that should not share
a cadence:

- **Capture lane** — cards, notes, backlog growth. Cheap, batched onto a branch as you go,
  merged **once** at the real boundary.
- **Delivery lane** — code. Per-feature branch → PR, unchanged.

### The session branch, and why it is a durability mechanism (owner, 2026-07-28)

The original framing justified one-branch-merge-once on *cost* (8 PRs of CI + merge overhead).
The owner added the stronger justification: it is also a **recovery vehicle.** If a session
ends without a mergeable state, the branch is where continuity and partial work survive, and
the next session picks it up from there. That separates the two things the eager per-card
merging was conflating — "don't strand work" (commit + push, continuously) from "don't
over-ceremony" (merge, once, at the boundary).

The repo already reaches for this: *bound each step to a green, committed-and-pushed
checkpoint*, and the orchestration rule's *name any unreviewed-output branch in the handoff*.
What is missing is that `next_prompt` does not systematically name a live session branch, so
recovery depends on whoever wrote the handoff remembering to.

### The backlog branch (owner idea, 2026-07-28 — needs expansion)

A branch where new cards and ideas accumulate, instead of a branch + PR per card. It is the
**safest possible** long-lived branch, and there is evidence: card files are unique and
append-mostly, and the 2026-07-26 librarian pass confirmed they conflict zero times. Only
`PRD.md` frontmatter is the hotspot.

**But it has a hard bound that any design must respect.** A card that lives only on an
unmerged branch is **invisible to everything that consumes cards**: `horus fleet --backlog`,
the dispatch selector, `github_catalog.discover()` and remote fleet review all read
`origin/<default>` — that is the "Fleet review names its truth layers / REMOTE SHIPPED TRUTH"
rule, by design. A card's entire job is to carry work across a context boundary, and a card
on an unmerged branch fails at exactly that.

So: **a capture branch is safe for capture and dangerous for durability**, which bounds its
life — it may batch captures *within* a boundary, but it cannot outlive one without the cards
going dark to the fleet. Once that bound is accepted, it converges on the session branch
restricted to `.horus/backlog/`, i.e. the capture lane above.

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

## Related — three cards converge on ONE mechanism (flagged 2026-07-28)

Design it once. All three arrive at "delivery facts flow up per-unit; canonical narrative is
authored once by a supervisor at a boundary":

- **`concurrency-safe-continuity`** — the same mechanism for the *parallel multi-agent*
  regime: "feature branches carry delivery facts and do NOT write canonical `PRD.md`
  frontmatter; a single consolidation pass folds them in."
- **`dispatch-workflow-comparative-study`** — the same mechanism for *dispatched workers*
  (its surviving design directions 1-3). Its direction #4 was deleted on 2026-07-28 because
  it rested on the `continuity_granularity` knob that #368 removed.
- **This card** — the *sequential single-agent* case, which is the one actually biting today.

- ~~`close-check-unclassified-cards-advisory`~~ — shipped in #409; the gate-ergonomics half is
  delivered, not related work.
- `continuity-sync-friction` (staleness + frontmatter hotspot — different friction, same
  "make continuity cheaper" family).

## Open decisions

- Which lane boundary triggers a merge, and whether `next_prompt` must name a live session
  branch for the recovery case to be reliable. [session] — this is the mechanism design.
- How the capture branch's life is bounded so cards never go dark to the fleet. [session]
- Whether one mechanism serves all three cards above, or they stay separate. [session]
- Whether the control needs a rung above instruction. [refine] — the card's own sharpest
  datum says a freshly-written instruction did **not** hold the behaviour, which is evidence
  for the ladder's next rung; but see the guardrail below.

Every live item is `[session]`-class. That is why this card has been screened twice without
converting, and it is an honest reason rather than a refinement failure.

## Reviews

- 2026-07-28 — **Rescoped to the capture/delivery lane split; the gate half is delivered**
  (owner, refine pass). #409 closed the merge-gate friction, so the card was narrowed to
  granularity alone. The owner then materially extended it twice: the **session branch as a
  recovery vehicle** (continuity survives a session that ends un-mergeable; the next session
  resumes from the branch), and a new **backlog branch** idea for card capture. The
  fleet-visibility bound above was added as the constraint that idea has to respect — an
  unmerged card is invisible to `origin/<default>`, which is the whole point of a card.

  Also flagged, and the reason this stayed Shaping rather than converting: **three cards are
  designing the same mechanism.** Cross-links added in Related so it is designed once. The
  card keeps its hard non-goal — no revival of frontloaded session-mode skills (#368).

## Source

In-session process discussion, 2026-07-21 (owner: "today is an example of a proper session
that did 7 PRs just to grow the backlog … not that efficient in terms of usage").
Instruction/skill targets: the CLAUDE.md continuity-cadence rules + the `gh pr merge` /
`horus close --check` gate.
