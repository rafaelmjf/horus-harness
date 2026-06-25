# Horus routines — contracts

A *routine* is a maintenance pass over a project's `.horus/` layer. Horus does the
deterministic, mechanical part (parse, detect, report) and — when judgement is
needed — emits a precise **prompt for the in-loop agent** (the Claude Code / Codex
session already running in the repo) to carry out. No subprocess is spawned.

This mirrors `horus close`, which verifies continuity and prints the closure ritual
for the running agent. The agent *is* the LLM; Horus orchestrates it with structure
and signals. The autonomous, Horus-spawns-its-own-agent variant is deferred to the
execution layer (MVP3); these contracts are forward-compatible with it (the same
prompt + signals can be handed to a spawned agent instead of printed).

Shared rules for every routine:

- **Scope of edits:** `.horus/**` only. A routine never edits source code, and
  (unlike `close`) never touches `AGENTS.md` / `CLAUDE.md` either — it only
  reshapes the continuity files.
- **Never invent.** The agent may move, merge, compress, and prune existing
  content. It may not fabricate status, dates, versions, or decisions. When intent
  is ambiguous, it leaves the content in place and flags it.
- **Idempotent.** Running a routine on an already-clean tree produces no changes.
- **Deterministic pre-pass first.** Horus computes signals in Python and prints
  them; the agent acts on those signals plus its reading of the files. The pre-pass
  must be safe to run with no agent present (it only reads + reports).

---

## `consolidate`

Keep the `.horus/` lanes in their lanes: route facts to the right file, prune what
is done or stale, and distill local session summaries into durable state. This is
the routine that makes a multi-lane structure honest — without it, `roadmap.md` and
`features.md` drift into two hand-maintained lists.

### The lanes and their boundaries

| File | Holds | Never holds |
|---|---|---|
| `project.md` | vision, shape, boundaries, current focus | task lists, changelogs |
| `roadmap.md` | open **action points** (any type), pruned when done | shipped capabilities, lessons |
| `features.md` | **capability ledger**: shipped / in-progress / planned *packages* | tasks/chores, the *why* |
| `decisions.md` | durable rules + reasoning, dated | open questions, status |
| `history.md` | curated lessons / "bumps in the road" | a timeline, open issues |
| `sessions/` | local ephemeral per-machine context | anything durable not yet distilled upward |

### Routing rules (the contract)

1. **Ship → ledger.** When a roadmap action point is done *and* it completed a
   shippable capability, close it on `roadmap.md` and add/update the matching row
   in `features.md` (move Planned/In-progress → Shipped; stamp the version from
   `config/VERSION` or the repo's convention if present, else leave blank).
2. **One-directional.** Facts flow roadmap → features on ship, **never** features →
   roadmap. A shipped capability does not regenerate action points.
3. **De-duplicate across lanes.** If the same item appears in both `roadmap.md` and
   `features.md`, split it: the *action points* stay in `roadmap.md`, the *capability
   status* stays in `features.md`, and each file points at the other rather than
   restating it. No fact is maintained in two places.
4. **Prune.** Remove done/obsolete roadmap items (they live in features/history/git
   now). Drop session summaries whose content has been fully distilled upward.
5. **Distill sessions.** Fold durable content from `sessions/*.md` into
   project/roadmap/features/decisions/history, then mark/remove the session.
6. **Keep lanes pure.** No tasks in `features.md`; no shipped packages lingering in
   `roadmap.md`; no open issues in `history.md`; no changelog in `project.md`.

### Deterministic pre-pass (Horus, Python)

Reads the lanes and reports, without mutating anything:

- **Lane presence** — which of the 6 lanes exist; missing recommended lanes
  (`features.md`, `history.md`).
- **Overlap candidates** — roadmap item text vs. `features.md` row text, matched on
  a normalized token-overlap heuristic; each hit is a candidate for rule 3. A roadmap
  item that already points back at `features.md` is treated as a *reconciled* split
  (the cross-reference is the split marker) and is reported as resolved, not flagged —
  so an in-progress/planned item legitimately in both lanes stops warning once split.
- **Done-but-unshipped** — roadmap items marked done (`[x]`) whose text has no
  corresponding `features.md` row (candidate for rule 1).
- **Sessions to distill** — session summaries present (candidates for rule 5).
- **Staleness** — `last_updated` age and lane mtimes.

### Emitted prompt

A consolidation ritual addressed to the in-loop agent: the routing rules above, the
computed signals, and the edit-scope/idempotency/no-invent constraints. The agent
performs the edits; re-running the pre-pass afterward should show the candidates
resolved.

---

## `distill-history`

Compress a large, raw log into the curated high-signal subset that belongs in
`history.md`: the problems that bit the project and the durable lessons. Most
valuable when onboarding Horus into a long-running project that already has a big
changelog (e.g. the fabric fixture's 1538-line archive).

### Signal test (what survives)

- **Keep:** a real problem the project hit + the durable lesson/design change it
  forced ("bumps in the road"). Anything a future agent would re-learn the hard way
  without it.
- **Drop:** routine changelog entries, version-bump noise, resolved-and-irrelevant
  incidents, anything already captured as a rule in `decisions.md` (cross-reference
  instead of duplicating).
- **Not a timeline, not open issues.** Open work goes to `roadmap.md`; this is
  carried-forward context only.

### Deterministic pre-pass (Horus, Python)

- Locate the source log (argument, or auto-detect `docs/HISTORY.md`,
  `CHANGELOG.md`, or the verbatim archive section inside `history.md`).
- Report its size (lines / headings / approximate entry count) and the current
  `history.md` curated size, so the compression target is explicit.

### Emitted prompt

A distillation ritual: the signal test above, the source log location and size, and
the instruction to write the curated subset into `history.md` (and mark the source
log as superseded/frozen rather than deleting it). Never invent incidents; only
compress what the log records.

---

## Status

Prototype: both routines are **agent-delegated** (pre-pass + emitted prompt), which
makes them invocable on any machine where an agent is already in the loop. The
autonomous, Horus-spawns-the-agent variant lands with the execution layer (MVP3).
