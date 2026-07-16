---
name: market-scan
description: >-
  Owner-invoked, evidence-first market/competitive research for a NEW idea or a
  PIVOT — the outward twin of product-audit (which looks inward). Use when the
  owner says "market scan", "research the landscape", "who else does this", "is
  this space taken", or when starting or redirecting a project. Frames the
  problem as a Jobs-To-Be-Done hypothesis, tears down 3-6 real competitors with
  fetched evidence, drafts a PR-FAQ-style vision paragraph, and caps market
  sizing to one line. Composes the deep-research harness for the evidence pass
  rather than reinventing search. Advisory only: it PROPOSES Vision text and
  candidate backlog cards in a dated receipt under `.horus/research/`; it never
  auto-writes the Vision or auto-creates cards. Not continuous monitoring.
---

<!-- horus-skill-version: 2 -->

# Market scan — look outward, propose, never auto-apply

You are researching the world OUTSIDE the repo — the market, competitors, prior
art — to inform a new idea or a pivot. product-audit prunes what Horus already
is; this scans what the world already offers, so the owner can decide where to
go. The output is a dated receipt that FEEDS the PRD Vision and the backlog; it
does not change them.

## Frame it to the intent — build-vs-adopt OR market-gap (ask, don't assume)

The SAME competitor evidence answers two different questions, and the owner's
intent decides which verdict you summarize toward. Do NOT default to the outward
adoption frame silently:

- **deepen-own-use** (personal/internal tool; audience = the owner) → read the
  scan as **build-vs-adopt**: per capability, is there something external with
  *more value* the owner should adopt or compose, or is it worth building/keeping?
  Here a green/yellow/red *saturation* verdict is the WRONG yardstick — a
  commoditized primitive is often table-stakes to adopt underneath, not a reason
  to stop. The verdict is a per-capability build / adopt / compose call.
- **broaden-adoption** (reach new users) → read it as the classic **market-gap**:
  prior-art, differentiation, is-the-space-taken.
- **both** → keep both verdicts side by side.

When `pathfinder` invokes this skill it passes the pinned intent + shipped/vision
brief; honor it. Standalone, ASK the owner the intent before spending.

## Before you spend — confirm the envelope

This skill fans out web research (it composes the `deep-research` harness), which
is a real token spend. Before any web work, state: the intent (deepen-own-use |
broaden-adoption | both), the trigger (new-idea | pivot), the problem/space in one
sentence, the competitors you already know, and the research depth — then get the
owner's confirmation. Match depth to the question; a light comparative sweep
usually beats a full adversarial report for a product decision.

## Bake in exactly the outward trio (+ one capped check)

1. **JTBD hypothesis** — "When [situation], I want [motivation], so I can
   [outcome]", plus the current alternatives people use. A skill cannot run real
   interviews, so frame this explicitly as a hypothesis to validate, not a
   finding.
2. **Competitive teardown** — 3-6 named competitors in a grid: does-well / gap /
   positioning / price, each row backed by a fetched URL. This is where
   `deep-research`'s fetch+verify does the work — invoke it, do not rebuild it.
3. **PR-FAQ vision paragraph** — a one-paragraph "if we build this, the headline
   is…" plus 3-5 hard FAQ questions (why now, why us, biggest risk). This feeds
   the PRD Vision almost verbatim.

Plus a **market-size sanity** line — ONE sentence ("big enough / already
saturated?"). Hard-cap it; never let it become a spreadsheet.

## Write the receipt (dated, committed, mirrors `.horus/audits/`)

`.horus/research/<YYYY-MM-DD>-<slug>.md`, one page:

```
# Market scan: <idea/pivot> — <YYYY-MM-DD>
Intent: deepen-own-use | broaden-adoption | both
Trigger: new-idea | pivot
Problem / JTBD (hypothesis): "When ___, I want ___, so I can ___"
Current alternatives: [list + links]
Competitive teardown:
  | Competitor | Does well | Gap | Positioning | Evidence (URL) |
Verdict (match to intent):
  - broaden-adoption → Prior-art verdict: green (gap) | yellow | red (saturated)
  - deepen-own-use  → Build-vs-adopt: per capability, build/keep | adopt | compose
Vision draft (PR-FAQ, 1 para): ...
Open questions / hard FAQ: [3-5]
Market-size sanity: <one line>
Candidate backlog items:
  - <candidate> — rationale, from which gap/assumption
Sources: [URLs from deep-research]
```

## Hand off — propose, the owner disposes

- The **Vision draft** + **verdict** (prior-art or build-vs-adopt, per intent) are written to be distilled into
  `PRD.md`'s Vision by `horus-consolidate` — you do not edit the Vision here.
- Each **candidate backlog item** becomes a candidate card the owner may accept,
  sourced to a specific gap/assumption. New exploratory directions enter as
  `phase: explore` cards; a proven direction can later be promoted into a Vision
  facet (the convergence read-out in `horus consolidate`).
- Advisory only: never auto-write the Vision, never auto-create cards.

## Composable (standalone or as a pathfinder step)

Inputs are a trigger + a one-line problem statement; outputs are the receipt
path, the Vision draft, and the candidate cards. Keep those clean so a larger
re-baseline flow can call this as one step and feed its output into a
divergence-directions proposal.

## Deliberately omit

Wardley mapping; a full Lean Canvas (an optional appendix at most); multi-
interview JTBD (label it a hypothesis instead); continuous monitoring / scraping
(the always-on SaaS category, out of scope); any mandatory-invocation or
red-flags ceremony.

## v2 six-lane projects (fallback)

No `.horus/PRD.md` — run the scan the same way and write the same receipt under
`.horus/research/`. Feed the Vision draft into `project.md` and candidate items
into `roadmap.md` at the owner's discretion, following that project's six-lane
closure rules.
