---
status: shipped
priority: medium
readiness: ready
autonomy: eligible
readiness_reason: "Reproduced with both ids in hand and the failure recorded in the run jsonl; the mismatch is visible in a single field, and the remedy is a choice between three small, offline, testable options."
created: 2026-07-27
created_by: claude
last_refined: 2026-07-27
vision_facet: "Autonomous dispatch"
tier: small
type: bug
parallel: safe
phase: converge
surface: "horus run --resume argument handling; the id shown by horus sessions / horus tail; run jsonl `agent_session_id`"
shipped_pr: 426
shipped_sha: ff6c65a
---

# resume-session-id-mismatch — the id you can see is not the id `--resume` wants

## Why — observed 2026-07-27, resuming a fabric-build drill worker

`horus sessions` and `horus tail` identify a run by its **horus** session id.
`horus run --resume` needs the **agent** session id. They are different values, and
passing the visible one fails:

```
horus run --resume e04e9d71-0912-48e2-91e6-d05d380939bc …     # the id sessions shows
  → runtime 0m02s · outcome=crashed · rc=1 · no error text
horus run --resume a3029e50-d702-463a-a16f-9c764bec0a72 …     # the agent id
  → resumes correctly, full context intact
```

The run's own jsonl records the mismatch plainly — for the failed attempt,
`agent_session_id` is set to the horus id that was passed in:

```json
{"event": "start", "session_id": "9f5062d1-…",
 "agent_session_id": "e04e9d71-…",
 "argv": {"resume": "e04e9d71-…", …}}
{"event": "result", "rc": 1, "status": "failed", …}
```

whereas a healthy run records the id the agent actually issued:

```json
{"agent_session_id": "a3029e50-d702-463a-a16f-9c764bec0a72", …}
```

## Why it is worth fixing rather than documenting

The failure is **silent**: two seconds, rc=1, no message naming the id or the
expectation. There is nothing to read that suggests trying a different value, and
the only id the operator has been shown is the wrong one. It cost one wasted
dispatch here (+0pp, because it died before doing anything) — but the same failure
inside a scheduled supervise/resume loop would look like a crashed worker rather
than a bad argument, which is the expensive version.

## Scope — one of these, not all three

1. **Accept either id.** Look the supplied value up in the run registry; if it is a
   horus session id, translate to its `agent_session_id` and proceed. Most
   forgiving, and the operator never has to know there are two ids.
2. **Show the agent id** in `horus sessions` (or a `--resume-id` column), so the
   value that is displayed is the value the flag takes.
3. **Fail loudly.** If the value is not a known agent session id, say so, and if it
   *is* a known horus session id, name the agent id to use instead.

Option 1 subsumes 3 and is probably the smallest surface. Whichever is chosen, the
error path should never again exit rc=1 with no text.

## Acceptance

- When an operator passes the id shown by `horus sessions` to `horus run --resume`,
  the session resumes — or the command explains exactly which id to use.
- A `--resume` given an unknown id exits with a message naming the problem, never a
  bare rc=1.
- Gate: the project's own test suite plus a regression test resuming by both id
  forms.
