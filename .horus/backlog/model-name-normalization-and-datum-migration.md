---
status: shipped
priority: high
tier: sonnet
type: feature
created: 2026-07-12
created_by: overseer
parallel: true
surface: horus/datums.py, horus/cli.py (capabilities render)
shipped_pr: 168
shipped_sha: 104b896f5f62d839dea1bb25e897a735e583fbca
shipped: "2026-07-12 — capability built, PR open (branch feat/model-name-normalization, PR #168). Real rename, not an alias: `horus run` now canonicalizes the captured model via datums.canonical_model_name(alias, resolved=...), preferring the adapter's own resolved model (Claude Code's system/init event carries e.g. \"claude-haiku-4-5-20251001\") over the small owner-maintained ALIAS_TO_CANONICAL fallback map (sonnet->sonnet-5, haiku->haiku-4.5, opus->opus-4.8), which only fires when no resolution is available (Codex's stream exposes none). One-time idempotent `horus datum migrate-names` (DatumStore.migrate_names()) renames bare-alias rows already in datums.json in place, preserving every field; a no-op re-run leaves the file byte-identical (verified manually: 11 sonnet + 2 haiku fixture rows migrated, re-run untouched). `capabilities --models`/`--matrix` now render an aligned table (model/tier/datums/last/price/capability/researched columns) instead of the vertical line-per-field block, with strength/caution/guard moved to a Notes section below (still surfaced, just not squeezed into a column); --stdout JSON shape and the no-pick/no-route boundary test are unchanged. 1208 tests green."
---

# Proper model names (rename, not alias) + datum migration + table rendering

**Owner decision (2026-07-12):** measured datums currently accrue under the bare
dispatch alias (`sonnet`, `haiku`) while owner priors + pricing live under the
canonical versioned name (`sonnet-5`, `haiku-4.5`), so `horus capabilities --models`
/`--matrix` shows the SAME model as two half-complete rows that never join. Fix by
using the **proper versioned name everywhere — a real rename, not an alias/mirror.**

## Scope

1. **Capture the proper name going forward.** At datum capture (`horus run`),
   normalize the model to its canonical versioned name. **Prefer the resolved concrete
   model** if the adapter exposes what actually ran; else fall back to an
   owner-maintained alias→canonical map (small, lives near `capabilities.toml`).
   Canonical set today: `sonnet`→`sonnet-5`, `haiku`→`haiku-4.5`, `opus`→`opus-4.8`,
   and GPT variants carry their suffix (`gpt-5.6-sol`/`-terra`/`-luna`, not bare
   `gpt-5.6`). NOTE the version-sensitivity risk: a static map mis-records once the
   family default moves (e.g. `sonnet`→`sonnet-6` later) — resolved-capture avoids it,
   so prefer it and only map where resolution isn't available.
2. **One-time idempotent `datums.json` migration.** Merge bare→proper
   (`sonnet` 11 records → `sonnet-5`, `haiku` 2 → `haiku-4.5`, etc.), preserving every
   record; re-running is a no-op. A `horus datum migrate-names` (or a flag) + test.
3. **Aligned TABLE rendering** for `capabilities --models`/`--matrix` — columns
   (model · tier · datums clean/total · last · $in/$out · capability · researched)
   so values compare at a glance instead of the current vertical line-per-field block.
   Keep `--stdout` JSON unchanged in shape. Display-only; no ranking here (that is the
   separate `model-ranking-synthesis` card).

## Verification

Fixture datums with bare + canonical keys migrate to one merged row byte-stably;
re-run is a no-op; the table renders aligned for a mixed roster; `--stdout` JSON
schema unchanged. Full suite green.
