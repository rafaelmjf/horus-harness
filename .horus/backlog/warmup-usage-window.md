---
status: open
priority: medium
created: 2026-07-18
vision_facet: "Accounts & isolation"
tier: low
type: feature
parallel: safe
created_by: owner
surface: horus/warmup.py (new), horus/cli.py (`horus warmup`), horus/notify_listen.py (grammar verb)
---

# warmup — start the 5h usage window on demand

**Why (owner, 2026-07-18):** Claude's 5-hour usage window only starts counting
from the first turn on an account — until then `horus usage` has nothing to
track. The owner wants a command that opens one cheap throwaway turn ("hi") per
Claude account so the window **starts now**, then closes. On a heavy day the
owner may later `horus schedule run --at ... -- warmup` every 5h to keep the
window aligned and maximize capacity — but that pacing stays ad-hoc; no extra
machinery here (it composes with the existing scheduler).

## How

- `horus/warmup.py`: for each configured Claude account (its isolated
  `CLAUDE_CONFIG_DIR`), run one `claude -p "hi"` subprocess (a cheap model by
  default) to register a turn, then exit. Best-effort: one account's failure is
  reported, never fatal to the others; never crosses account credentials.
- `horus warmup [--account <alias>] [--model M]`: warm all configured accounts,
  or just one. Prints a per-account result.
- Add a `warmup` verb to the `notify_listen` grammar so it can be kicked from the
  phone (bounded, deterministic — no LLM).

## Acceptance

- `horus warmup` opens one turn per configured Claude account under its own
  isolated config dir and reports ok/fail per account.
- A single account can be targeted with `--account`.
- The `warmup` verb in `horus notify listen` maps 1:1 to `horus warmup`.
- Composes with `horus schedule` for the ad-hoc every-5h idea (no new scheduling
  code).

## Non-goals

- No automatic/periodic warmup loop — pacing is the owner's ad-hoc `schedule`
  call.
- No Codex warmup (Codex usage-window semantics differ; separate card if wanted).
