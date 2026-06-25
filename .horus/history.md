---
status: active
last_updated: 2026-06-25
---

# History — bumps in the road

Curated, durable context: the problems that bit us and the lessons that shaped the
design. **Not** a timeline and **not** open issues (those live in `roadmap.md`) —
just the war stories worth carrying forward.

## Deterministic inference produced drifting, truncated `.horus/`

The first `horus init` mined README/STATUS/CLAUDE docs to pre-populate `.horus/`.
A real agent's review of the seeded fabric repo flagged two failures: multi-line
bullets truncated mid-sentence, and copying existing prose created a *second*
drifting "what's next" alongside the project's own docs. **Lesson:** don't
mechanically parse prose into continuity — `init` now scaffolds clean templates +
a `README.md` that says "distill from canonical docs, point at them, don't
duplicate." Rich population is the deferred LLM-based `horus infer`.

## Drift checking can't use byte-equality on the managed blocks

The `HORUS:BEGIN/END` blocks in `AGENTS.md` and `CLAUDE.md` are intentionally not
identical — each ends with a line naming the *other* file. **Lesson:**
`doctor instructions` normalizes/ignores that cross-reference line, or it reports
false drift on every run.

## A routine's "verify" step must be reachable by following the routine

The first `horus consolidate` flagged roadmap↔features overlaps purely on shared
capability *name*, while the skill correctly told the agent to **keep both** (split:
action points in roadmap, status in features). So a correct split never cleared the
warning — the success criterion contradicted the rule. An independent validation
agent caught it and noted it could loop or delete ledger rows chasing zero.
**Lesson:** align the machine signal with the rule. The cross-reference pointer
(`→ features.md`) is the detectable marker of an *intentional* split, so consolidate
now treats a cross-referenced item as reconciled and only flags un-split ones. When a
routine emits a "now re-run to confirm" step, make that zero actually reachable.

## A machine-local SQLite session registry cut against the ethos

Considered a SQLite session/event registry early. It presupposed Horus
orchestrating sessions (the deferred execution layer) and added a machine-local
store at odds with the file-first, git-synced, lightweight design. **Lesson:**
session `.md` files are ephemeral context that distills into the durable lanes;
at solo scale re-parsing markdown is instant. Registry deferred until real live
processes exist to track.
