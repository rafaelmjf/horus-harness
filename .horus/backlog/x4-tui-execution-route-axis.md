---
status: open
priority: medium
created: 2026-07-18
tier: medium
type: feature
parallel: unsafe
phase: explore
created_by: owner
branch: vision-branch-x4-model-harness-plane
surface: horus/terminal_tui.py, horus/terminal_sessions.py, horus/launch.py, horus/registry.py, launch receipts
---

# x4-tui-execution-route-axis — make the complete model/harness/account route visible and selectable

## Why

The current TUI asks for a Claude account and then offers both Claude and GPT models.
When proxying is enabled, that account is only the Claude Code config profile; the
actual provider subscription is invisible. Subagent policy and usage source are
invisible too. The launch picker must tell the truth without becoming a router.
Evidence: [[2026-07-18-claudex-first-session-findings]].

## Design

- Preserve the existing sequential, TUI-thin launch flow, but expose these axes:
  harness → harness profile → model → provider credential → effort → subagent policy.
- Show a confirmation/readout of the complete route before launch, including which
  subscription supplies usage data.
- Auto-select only when exactly one valid route exists. Multiple credentials always
  require a deliberate choice or an explicit persisted default.
- Carry the route through `_Launch`, `SpawnSpec`, session registry, worker receipts,
  datums, and errors. Existing consumers remain forward-readable.
- Settings/Mission Control lists masked bound credentials and usage source/freshness.
- On cooldown, show the failed credential and available named alternatives; return to
  the relevant picker rather than mutating the route automatically.

## Acceptance

- A live `claude-work` + GPT Sol + `codex-personal` launch displays and records all
  three identities correctly.
- One valid credential auto-selects; two produce a picker; zero refuses with guided
  setup instructions.
- Switching `/model` across providers updates the displayed usage source honestly or
  labels it unknown when route identity cannot be proven.
- Registry/receipt JSON preserves route fields unknown to older readers.
- Native unproxied Claude/Codex launch flows retain their current byte-level defaults.

## Non-goals

- No automatic model/account recommendation or spend decision.
- No new agent session/runtime layer; reuse existing launch and tmux paths.
- No harness adapters beyond the X4 stage-2 cards.
