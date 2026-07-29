---
name: launch-model-refresh
description: >-
  Owner-invoked refresh of the models the Horus TUI offers when launching a
  session (`[launch_models]` in config.toml, read by the launch form). On the
  owner's signal ("a new model shipped / became default", "refresh the launch
  models", "which older models are still supported"), an agent researches the
  VENDOR'S OWN model-deprecation docs (Anthropic for Claude, OpenAI for Codex),
  identifies which `--model` selectors are still Active (including older pinned
  versions the /model picker hides), proposes the config change for owner
  approval, then writes it. Evidence-first and owner-gated: it PROPOSES and,
  once approved, writes `config.set_launch_models(...)`; it never auto-runs,
  never polls, and never exposes a model past its retirement date. Sibling of
  `automated-model-roster-grounding` (that grounds calibration TIERS/PRICES from
  benchmarks; this grounds launch AVAILABILITY from vendor docs) — different data
  and sources, kept separate.
---

<!-- horus-skill-version: 1 -->

# launch-model-refresh — keep the TUI's launchable model list current from vendor docs

The Horus TUI launch form offers a `--model` selector per agent. The list comes from
`config.launch_models_for(<agent>)` (the `[launch_models]` table in
`~/.horus/config.toml`) when set, else the adapter's built-in default. This skill keeps
that owner-curated list current, because there is **no API that enumerates the
selectors a CLI accepts** — the trustworthy source is the vendor's own model docs, read
by an agent.

Owner-invoked only. Trigger on an explicit signal: a new model shipped or became the
default, a model is being retired, or "refresh the launch models". Never scheduled,
never auto-polled.

## 1. Research the vendor's model status (cite sources + an as-of date)

Per-vendor recipe (the sources differ in shape — do not assume one generic fetch):

- **Claude** — one authoritative table at
  `https://platform.claude.com/docs/en/docs/about-claude/model-deprecations`: each API
  model name with its state (Active / Legacy / Deprecated / Retired), deprecation date,
  and retirement date. Active + Legacy models are launchable; Deprecated are launchable
  but dated; Retired fail. The bare aliases (`opus`/`sonnet`/`haiku`/`fable` = latest)
  come from `https://code.claude.com/docs/en/model-config`.
- **Codex/OpenAI** — TWO pages, merged: the active list at
  `https://developers.openai.com/api/docs/models/all` (the `gpt-5.x` / `-codex` family)
  UNION the shutdown dates at `https://developers.openai.com/api/docs/deprecations`. A
  model with a shutdown date already in the past is effectively retired — exclude it.

Record, per selector: exact `--model` string, status, retirement/shutdown date,
recommended replacement. Fetch the page; never answer model status from memory.

## 2. Propose the config change (owner-gated — do NOT write yet)

Read the current list (`config.launch_models_for(<agent>)`, or the adapter default when
unset). Present a diff:

- **Add** — Active/Legacy selectors the owner is likely to want that are not yet listed
  (name the older pinned versions explicitly).
- **Drop** — anything now Retired, or past its shutdown date.
- **Flag** — Active-but-Deprecated selectors with a near retirement date (show the date),
  so the owner decides whether to keep them.

Do NOT dump every Active model — a vendor may list ~10. Propose a **curated subset**: the
latest-family aliases plus the specific versions the owner is comparing or has reason to
pin. The owner picks the final set. This curation is judgment and stays owner-gated.

## 3. Write only what the owner approved

Persist with `config.set_launch_models("<agent>", [<selectors>])` (an empty list removes
the override, reverting to the adapter default). Confirm the written list back, and note
the source URLs + the as-of date so the next refresh knows the baseline. Nothing else is
touched; the TUI picks up the new list on its next launch.

## Boundaries

- Owner-invoked and owner-gated at the write step; never auto-run, auto-poll, or
  auto-widen. Propose, then write what was approved.
- Never expose a selector past its retirement/shutdown date, and never guess a selector
  from memory — the vendor doc is the only source.
- Availability only. Calibration tiers/prices are `automated-model-roster-grounding`'s
  concern; do not touch `horus/datums.py` priors here.
- The list is the owner's curated subset for launching, not a mirror of every Active model.

## v2 six-lane projects (fallback)

Structure-independent: this skill reads vendor model docs and writes machine-local
`~/.horus/config.toml` (`[launch_models]`), never a project's continuity lanes — so it
works identically whether a project is on the v3 `PRD.md` structure or the v2 six lanes.
Nothing here routes into `PRD.md`, `roadmap.md`, or `decisions.md`.
