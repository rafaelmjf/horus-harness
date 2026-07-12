---
status: shipped
priority: low
tier: haiku
created: 2026-07-12
created_by: overseer
parallel: true
surface: capabilities.toml (owner priors), horus/datums.py, horus capabilities --models/--matrix
shipped: "2026-07-12 — capability built, PR open (branch feat/model-roster-pricing, PR #167). Extended the capabilities.toml owner-prior schema with optional back-compatible price_in/price_out/capability_note/researched_at fields (horus/datums.py: ModelRollup, build_model_rollup, _researched_at_str); surfaced pricing + capability note in `horus capabilities --models`/`--matrix`; added a non-blocking staleness WARNING (stderr, exit 0 unaffected) via datums.staleness_warning when the freshest researched_at is >14 days old or absent from every model. 23 new tests in test_datums.py, full suite green (1199). The actual web-research refresh (real price/capability data for active models) is NOT this PR — a separate agent-run pass, still open."
shipped_pr: 167
shipped_sha: c21749513925fa994a15199306be30cdcca66590
---

# Pricing-aware model-roster research process

**Owner redefinition (2026-07-12):** this card was originally "hand-seed old
models into the roster." The owner reframed it: the roster question is never
"is this model old?" — it's **"is this model CHEAPER than a current model at
comparable capability?"** An older/prior-frontier model earns roster space only
when price-for-capability says so. Age alone is never the reason to include OR
dismiss a model; today's frontier will be a candidate "older" model in a few
months, judged the same way.

## Architecture (owner-confirmed)

The AGENT does the web research on refresh and writes the data; the CLI only
READS it and warns if stale. Concretely:

- **Single source of truth**: the existing owner-priors file
  `~/.horus/capabilities.toml` — extended, not forked. Three new optional
  per-model fields, all back-compatible (a file/model without them parses and
  renders exactly as before):
  - `price_in` / `price_out` — USD per Mtok (million tokens), input/output.
  - `capability_note` — a short free-text line on what the model is actually
    good for, so price reads next to capability, not in isolation.
  - `researched_at` — an ISO date (`YYYY-MM-DD`) stamping when that price/note
    was last checked.
- **Refresh = an agent process, not CLI code.** Refreshing the roster means: an
  agent web-searches currently-active Claude + GPT/Codex models for current
  pricing and rough capability, applies the price-for-capability filter below,
  and hand-writes the resulting `price_in`/`price_out`/`capability_note`/
  `researched_at` fields into `capabilities.toml`. This is a **separate run**,
  done by an agent with web access — the CLI itself never fetches the network.
  This PR ships the reading/display/staleness code only; a later run populates
  real data.
- **Staleness is a nudge, never a gate.** `horus capabilities --models` and
  `--matrix` compute the freshest `researched_at` across all models and, when
  it's more than 14 days old (or no model has one at all), print
  `WARNING: model-roster priors are N days old — consider refreshing` (or the
  "no researched_at" variant) to stderr. The command still exits 0 and still
  prints its normal output — nothing blocks on this.

## The price-for-capability filter (methodology, for the refresh run)

For each candidate older/prior-frontier model, the refresh agent should judge:
capability roughly comparable to a model already in rotation, AND price
meaningfully lower (input or output per Mtok) → keep/add it with a
`capability_note` explaining the comparable use case. Otherwise drop it — being
merely *older* is not a qualifying signal either direction. This is the same
judgment the `delegation-rubric` skill's tier-trust ladder already leans on (see
`.claude/skills/delegation-rubric/SKILL.md` Step 1/3); the refresh run is what
keeps that ladder's price/capability inputs current. No code encodes this
filter — it is agent judgment applied at refresh time, same as `tier` /
`strength` / `caution` already are.

## Relationship

The *principle* (older models stay in the roster when cheap-for-capability) is
encoded in the `delegation-rubric` skill template. This card is the *process*:
the schema that carries price/capability data, the display surface, and the
staleness nudge that reminds an agent to re-run the research. The actual
price/capability datums for specific models are **not** this card's job to fill
in — that's the separate agent research run described above.

## Verification

`capabilities.toml` with `price_in`/`price_out`/`capability_note`/
`researched_at` set renders pricing and capability note in both `--models` and
`--matrix`, and prints the staleness WARNING when `researched_at` is >14 days
old; a `capabilities.toml` without any of the new fields renders identically to
before (no crash, no warning suppressed incorrectly — absent `researched_at`
across all models still warns, since silence about freshness is itself a
staleness signal); the warning never changes the command's exit code (still 0).
