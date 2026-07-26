---
status: open
priority: high
readiness: shaping
readiness_reason: "The symptom is captured with a worker log and two direct observations on unmodified main, but the mechanism is NOT identified and did not reproduce on demand — two hypotheses were checked and refuted. Needs a real repro before a fix can be scoped."
created: 2026-07-26
created_by: claude
vision_facet: "Continuity core"
tier: small
type: bug
parallel: safe
phase: converge
surface: "tests/test_datums.py:869 (test_capture_usage_snapshot_unavailable_on_failed_read), horus/datums.py:369 (_claude_usage_entry), horus/usage_snapshot.py:386 (cached_usage) / :148 (_read_claude), tests/conftest.py"
---

# usage-snapshot-test-flake-blocks-workers — a green-on-CI test fails locally and kills dispatched deliveries

## Why — cost a real worker delivery, 2026-07-26

A dispatched Codex worker (`gpt-5.6-terra` @medium, session `1da08b24`) completed
the `vision-omits-intent-and-audiences` card correctly, ran its required full-suite
gate, saw two failures, and — exactly as briefed — **refused to commit or push**
and reported them. One of those failures had nothing to do with its diff:

```
tests/test_datums.py::test_capture_usage_snapshot_unavailable_on_failed_read
E   AssertionError: assert 'fresh' == 'unavailable'
```

The supervisor reproduced that failure on **unmodified main** at ~13:07, then found
it passing from ~13:14 onward — 3× consecutively and inside two full suites (2233,
2235 passed). The worker's diff was then verified green and landed by hand (PR #405).

**The cost shape is what makes this high priority.** A dispatched worker cannot tell
an environmental flake from a real regression, and the correct behaviour when its
gate fails is to stop — so this defect converts a good worker run into a blocked
delivery plus a supervisor rescue. Every Codex dispatch in this repo is exposed.

## Why CI never catches it

The test asserts that with no reachable credentials the usage snapshot reads
`unavailable`. CI has no credentials, so CI always takes that path and is always
green. The failure only exists where a real logged-in account is reachable —
local sessions and dispatched workers, i.e. exactly where it does damage.

## Mechanism — NOT identified. Two hypotheses checked and refuted

Recording these so the next session does not re-walk them:

1. **"A ~10-minute usage-cache TTL; the dispatch writes a fresh entry."** Refuted:
   `cached_usage` resolves `_cache_path` under `cache_dir()` → `config.config_dir()`
   → `Path.home()`, which the test's faked `HOME` does isolate. A real cache entry
   is not reachable.
2. **"`CLAUDE_CONFIG_DIR` leaks past the faked `HOME` into a live OAuth read."**
   Plausible on inspection — `config.py:787` does resolve that var ahead of `HOME`,
   and it is always set under account isolation — but refuted as *sufficient*: with
   the clearing fixture removed, the test still passed. Token expiry was also ruled
   out as the differentiator (credentials valid until 18:37 that day, while
   `fetch_usage` returned `None` in 0.08s, i.e. without a network attempt).

Direct probing under a faked `HOME` returns `cached_usage("claude", None) → None`
in ~0.10s — the `unavailable` path the test wants. The `fresh` window could not be
recreated on demand.

## How — get a repro first

- Instrument `capture_usage_snapshot` / `_claude_usage_entry` to log which branch
  produced a non-`None` snapshot (cache hit vs live read) and from which path.
- Run it in a loop *during* a live Codex dispatch, since both observed failures
  were within ~5 minutes of two workers exiting. That correlation is unexplained
  and is the best lead.
- Only then decide the fix. Candidate directions, unranked: make the test assert
  on an injected reader rather than on ambient absence; or have
  `capture_usage_snapshot` take an explicit source so "no reachable credentials"
  is constructible instead of environmental.

## Acceptance

- The mechanism is stated with a reproduction someone else can run.
- The test is deterministic with a real logged-in account reachable — it must not
  depend on a network call failing to pass.
- Gate: full suite green on the exact SHA, run **with** credentials reachable.
- Probe: run the full suite during a live Codex dispatch and confirm it stays green.

## Deliberately not doing

- **Not deleting or skipping the test.** It guards a real contract (never fabricate
  a percent), and `xfail`/`skip` would hide the same trap from workers.
- **Not treating `tests/conftest.py` as the fix.** That fixture (PR pending) closes
  a genuine faked-`HOME`-vs-`CLAUDE_CONFIG_DIR`/`CODEX_HOME` isolation gap on its
  own merits and is suite-green, but it is **not demonstrated** to address this
  symptom. Do not close this card on it.

## Related

- `codex-usage-stale-snapshot-gates-dispatch` — adjacent, same subsystem: that card
  owns wrong/disagreeing usage *readings* gating dispatch; this one owns a *test*
  over that subsystem breaking worker deliveries.

## Source

Supervisor observation while landing two dispatched cards, 2026-07-26. Worker log:
`~/.horus/logs/runs/1da08b24-98d8-437b-bd96-eab2972b4444.log`.
