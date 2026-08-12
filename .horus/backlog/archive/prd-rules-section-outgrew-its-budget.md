---
status: shipped
priority: medium
created: 2026-08-01
created_by: agent
readiness: shaping
readiness_reason: "The measurement is done and unambiguous; the method is not. Which of 84 rules are still load-bearing is a judgement call per rule, and the answer shapes whether this is one consolidation pass, a retirement policy, or a second file. Needs an owner-attended session — an agent deleting rules it finds unfamiliar is exactly the wrong reader."
topic: continuity-core
type: feature
tier: medium
parallel: safe
surface: .horus/PRD.md (## Rules), .horus/archive/history.md (the sanctioned destination), horus/consolidate.py (the budget + per-entry signals that keep firing)
shipped_pr: 492
shipped_sha: bc32140
---

# prd-rules-section-outgrew-its-budget — 84 rules, 66% of the file, and every close now fights the cap

## Why — measured 2026-08-01, at the v0.0.81 close

```
PRD.md total          59,480 chars   (budget warns at 45,000, urgent at 60,000)
## Rules              37,710 chars   84 entries · 66% of the body
## Vision              7,772
## Shipped             6,829
## Backlog             1,765
```

Two closes in a row have now spent real effort *just getting back under the cap* — the
2026-07-31 pass took Rules from 22 over-budget entries to 0 (#474), and this close had
to merge two rules and route two narratives to `archive/history.md` purely to make room
for three new lines. That is the tell: the per-entry contract is being met (only 1 of 84
exceeds ~600 chars) while the section as a whole is the problem. **Trimming entries
cannot fix a count problem.**

## Intended outcome

`## Rules` holds what a fresh session must know to not repeat a failure, at a size that
does not tax every future close. The acceptance line: **when a session finishes an
ordinary continuity close, adding this campaign's rules should not require deleting
someone else's.**

## Broad boundaries

Likely candidates, none decided:

- **Retirement, not deletion.** A rule whose referent is gone (the drill legs, a shipped
  card, a superseded mechanism) moves to `archive/history.md` with its evidence, the way
  narratives already do. Nothing is lost; the reader stops paying for it.
- **Grouping.** The Rules section is flat and topic-sorted only by accident. Several
  clusters (accounts/isolation, dispatch/envelope, tmux/hosts, release/distribution) are
  large enough that a fresh session reads all 84 to find 6.
- **A second file.** The budget signal exists because PRD.md is read on every launch.
  Rules that only bind a *specific* activity (release mechanics, tmux/host traps) may not
  belong in the always-loaded file at all.

Non-goal: raising the budget. The budget is measuring the right thing — what a fresh
agent pays to read the file — and 59,480 chars genuinely is a lot to load at every launch.

## Open decisions

- [session] Retire-vs-group-vs-split, above. These are not independent: grouping first
  makes retirement candidates visible, and splitting is only worth it if grouping is not
  enough.
- [session] What earns a rule its place. Candidate test: a rule stays if a session could
  plausibly repeat its failure *this quarter*. That test would retire several 2026-07
  entries whose mechanism has since been replaced — which is either the point or too
  aggressive, and the owner should say which.
- [refine] Whether `horus consolidate` should signal entry COUNT alongside characters.
  It currently reports the section's size and its over-cap entries, and neither
  number told the story here; "84 entries" did.

## Reviews

- 2026-08-01 — Carded at the v0.0.81 continuity close, per *card what you won't do now*:
  this survives the boundary and was actively costing the close it was found in. Not
  attempted inline, deliberately — deciding which of 84 rules are dead is an owner call,
  and an agent that has read them once is the worst reader for it.

### 2026-08-02 — Rafael Figueiredo (manual)

2026-08-02 — DELIVERED across #491 (pilot) and #492 (batch), and closed here with the numbers. Acceptance line was 'finishing an ordinary continuity close should not require deleting someone else's rules'; that now holds. Measured: `## Rules` 84 -> 61 entries and 37,519 -> 26,756 chars; PRD.md 59,480 -> 48,656; budget headroom 2,550 -> 11,344, which is the figure that matters — at 2,550 a normal close went straight over the cap and the last one spent ~10 of its ~20 turns clawing back. The finding that reshaped the work: routing is DELETION-dominant, not migration-dominant. 13 of the first 19 rules were already stated in their destination skill, usually more fully, because the skills were written from the same knowledge — so the rules were duplicated, not homeless. That also means the article's conflicting-instruction failure mode was literally present: one instruction, two wordings, both loaded. Two open decisions were resolved: the five general-engineering entries were KEPT (cheap, and their failures were recent and repeated), and the C group (30 rules -> code docstrings) was declined as deletion-with-extra-steps at migration cost — if those are worth keeping the code should already say it, as `datums.py:1019` did. Rules 51/52 had no destination until `horus-release` was created in #496, which absorbed them and the two duplicate prose copies.
