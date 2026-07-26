# Backlog librarian — 2026-07-26

## Summary

70 active cards, 121 archived. **5 actionable findings** (2 satisfied dependencies, 2 state contradictions, 1 missing card), 0 stale, 0 duplicates, 0 broken links.

Highest-value review: **`tui-backlog-refine-and-order` is [high] Gated on a card that already shipped.** Its own reason says the gate would make it Ready—Attended, so a high-priority card has been sitting blocked on delivered work.

## Proposed actions

| ID | Category | Card(s) | Evidence | Proposed action | Confidence |
|---|---|---|---|---|---|
| L1 | Satisfied dependency + state contradiction | `tui-backlog-refine-and-order` [high, gated] | `depends-on: backlog-readiness-disposition`, which is `.horus/backlog/archive/backlog-readiness-disposition.md` with `status: shipped`. Card's own reason: *"Land backlog-readiness-disposition tooling first; then this becomes Ready—Attended."* | Remove `depends-on`; set `readiness: ready`, `autonomy: attended`; rewrite `readiness_reason` to state the tooling landed. Re-check scope before scheduling — it is `tier: high`. | high |
| L2 | Satisfied dependency | `explore-converge-lifecycle` [medium, deferred] | `depends-on: roadmap-convergence`, archived `status: shipped`. But the stated gate is different: *"Resume when Horus has a real per-card usage signal for the remaining usage-ripeness flag."* | Remove the stale `depends-on` only. **Keep `readiness: deferred`** — its real gate is unmet, so this is not a readiness change. | high |
| L3 | State contradiction | `codex-isolated-config-leak` [medium, gated] | Related section (line 99) reads *"`isolated-account-plugin-parity` — directly affected: **remedy 1** makes plugin parity a required companion"*, but the owner chose **remedy 3** on 2026-07-26 (`readiness_reason`). | Update the Related note to describe the consequence under remedy 3 (a dir from fresh `codex login` also carries no plugin block, so parity remains a companion — but for a different reason than remedy 1). | high |
| L4 | State contradiction (deterministic) | `PRD.md` readiness breakdown | `horus consolidate`: *"PRD readiness breakdown says Shaping (38) but 37 card(s) are in that queue"* | Correct the count to 37. Mechanical. | high |
| L5 | Missing card | `horus-wiki-readmodel` (none) | `origin/spike/horus-wiki-readmodel` carries 563 lines (`horus/wiki.py`, CLI wiring, `tests/test_wiki.py`) with **no backlog card, active or archived**. Module docstring: a read-only, idempotent projection of fleet `.horus/` into an Obsidian-compatible vault, *"never a second store"*. | Either file a card so the work is visible, or delete the branch. Note the owner already keeps `rmjf-vault` (Obsidian) in the fleet, so this is plausibly live rather than abandoned. | high |

## Needs owner interpretation

- **`skill-drift-surfacing-and-refresh` vs `skill-self-calibration-probe`** (both [low, shaping], Introspection & self-improvement). Adjacent but not duplicate on reading: the first is unified artifact-refresh *mechanics* (detect → preview → integrate → verify); the second is a replay PoC where a skill *notices its own* drift. Distinct intents, so not reported as hygiene debt — flagged only because a future convergence pass might reasonably merge them. Low confidence.
- **Four stranded git branches** surfaced by a separate audit this session and not by this pass (branches are outside this skill's evidence scope): `fix/codex-usage-stale-cache`, `design/process-tree-orphan-reap`, `feat/pwa-installable` all appear superseded; PR #117 `feat/structure-staleness-migration` has nothing left to detect (all 10 registered projects are v3). Disposition is the owner's.

## Clean checks

Explicitly checked, no findings:

- **Stale (>56 days):** none. Every active card has an evidenced touch within the window; the oldest are well inside it.
- **Duplicates / overlap:** 13 candidate pairs passed the prefilter (cap 25, **no truncation**); all were compared and none is a duplicate. The `MENTIONS` pairs are deliberate cross-references, not collisions — e.g. `account-settings-sync` vs `codex-isolated-config-leak` explicitly partition themselves ("that card owns settings *drift*; this card owns what gets copied at *creation*").
- **Broken links:** none. 8 `[[...]]` targets initially flagged resolve to real documents under `.horus/research/` (`2026-07-18-agent-host-freeze-incident`, `2026-07-18-claudex-first-session-findings`) — a false positive of a card-name-only check, not dangling links.
- **Terminal lifecycle states lingering active:** none. All 70 active cards are `status: open`.
- **Ready cards without `autonomy`:** none. **Non-Ready cards without `readiness_reason`:** none.
- **Unclassified cards:** none (`horus consolidate` confirms 0).

## Run facts

- Threshold: 56 days (default, not overridden). Effective date: 2026-07-26.
- Branch/SHA: `fix/codex-datum-window-labels` @ `23cc3c1` (fetched and verified against remote before analysis).
- Cards: 70 active, 121 archived. Every active card's frontmatter and body read once.
- Semantic pairs: 13 candidates after prefilter, cap 25, **no truncation**. Ranking: explicit mention → shared branch → shared facet → shared-term count.
- Signals used: `git fetch --all --prune`, `horus consolidate`, `git log -1 --format=%cs -- <card>` per card, frontmatter/body parse, `[[link]]` and backticked-name extraction.
- Limitations: `depends-on` resolution treats an archived `status: shipped` card as satisfied; archived bodies were read only for the two dependency targets. Branch-level evidence (L5) came from an owner-directed audit in the same session, not from this skill's normal scope.

## Boundary

Advisory only; no cards or continuity were changed.
