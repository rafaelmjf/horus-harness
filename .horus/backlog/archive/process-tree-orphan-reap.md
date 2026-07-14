---
status: retired
priority: high
tier: opus
created: 2026-07-14
type: bug
parallel: exclusive
surface: horus/process_tree.py, horus/adapters/base.py, horus/cli.py, horus/registry.py, horus/dashboard.py
---

> Retired 2026-07-14 (owner decision after design PR #231): manual cleanup is
> acceptable at the current incident rate. Safe automation would require
> cross-platform containment, registry schema changes, helper runners, and risky
> termination logic. Re-open only if orphan incidents become frequent or exact-handle
> manual recovery becomes burdensome; the unimplemented design is preserved below.

# Reap process-tree orphans after failed runs, with positive confirmation

> Prioritized 2026-07-14 (owner triage): two real incidents make this the highest-value
> reliability feature after the bounded correctness batch. It needs an Opus design
> pass before Sonnet implementation because cross-platform process ownership and kill
> safety are ambiguous; do not generalize the tmux reaper blindly.

Dead workers have left children holding ports: a ghost probe server on 8899 corrupted
a supervisor probe (2026-07-04), and a setsid-detached dashboard orphan served the
hosted app for seven hours while systemd reported it dead (2026-07-12). The hosted
deploy version check caught the latter; the runtime did not.

## Required design boundary

- Distinct from the shipped tmux orphan reaper. Walk the failed run's process tree
  cross-platform using registry ownership/pid evidence.
- Put safety in code: act only on positive ownership + terminal failure confirmation;
  absence of a registry record is never permission to kill.
- At minimum, surface “tracked pid still has children” in `horus tail` and the
  dashboard before enabling termination.
- Define Linux/macOS process-group behavior and native Windows process-tree behavior,
  including PID reuse and already-exited races, before implementation.

## Verification

Design a deterministic fake-process-tree gate plus isolated live probes. Prove owned
failed trees are reaped, unrelated processes and missing-record trees survive, and
report-only fallback works where safe termination cannot be established.

## Preserved design proposal (not approved for implementation)

### Finding: a PID walk after failure is too late

Today `horus run` stores the provider CLI's PID and writes the terminal registry
status only after that process exits. That PID is useful for liveness, but it is not
durable ownership evidence:

- a child may call `setsid`, outlive the provider CLI, and be reparented before Horus
  observes the failure (the hosted-dashboard incident did exactly this);
- PID and process-group identifiers can be reused after their original owner exits;
- attended window launches may register a terminal-emulator/viewer PID rather than the
  agent itself; and
- `taskkill /T` or `killpg` applied to a stale identifier can therefore affect a tree
  Horus did not launch.

The fix must establish a scope **before** the agent can spawn tools. A later ancestry
scan is diagnostic evidence only; it can never upgrade an unscoped record into kill
authority.

### Scope and non-goals

First implementation applies only to headless `horus run` sessions. Automatic
termination is narrower still: a run must have been launched with `--worker`, must
finish with registry status `failed`, and must have a strong OS scope whose identity
still matches.

Not in this card:

- attended `horus open`, current-terminal, window, PTY, or tmux cleanup (tmux keeps its
  separate positive-confirmation reaper);
- killing successful runs, non-worker runs, `stale` rows, or arbitrary PIDs supplied by
  a user;
- port scanning or command-line matching as ownership evidence;
- a daemon, scheduler, remote-target protocol, or new native dependency; and
- claiming full macOS coverage when a descendant escapes its process group.

### Data contract: ownership and outcome are separate axes

Add two optional, backward-compatible JSON objects to `AgentSession` / `SessionRecord`:

1. `process_scope` — immutable launch evidence:
   - `run_id`: the pre-launch Horus `run_session_id`, not a provider session id;
   - `kind`: `linux-cgroup-v2`, `windows-job`, or `posix-process-group`;
   - `ref`: a validated OS handle/name/path derived from `run_id`;
   - `leader_pid` plus an OS birth identity (`/proc` start ticks or Windows creation
     time), never PID alone;
   - `authority`: `strong` or `report-only`; and
   - `coverage`: an explicit phrase such as `contained-tree` or
     `process-group-only`.
2. `process_tree` — mutable observation/result:
   - `state`: `unknown`, `clear`, `children-live`, `reaped`, or `reap-failed`;
   - `live_count`, `checked_at`, `action`, and a short safe `detail`;
   - no command lines, environment, or persisted PID list; recycled PIDs must never
     become later authority.

The session remains `failed` after its children are reaped. Do not overload registry
status with process-tree state; the two facts answer different questions.

### One process-scope primitive

Create `horus/process_tree.py` as the only OS-specific boundary. Callers receive
JSON-safe values and never implement their own PID walk:

```text
spawn_scoped(argv, cwd, env, run_id) -> (Popen, ScopeDescriptor)
inspect_scope(descriptor)            -> TreeReport
terminate_scope(descriptor, grace)   -> TreeReport
```

`AgentAdapter._launch` uses `spawn_scoped`; the descriptor travels on
`AgentSession` and into the registry once the provider session id exists. At run end,
`cmd_run` persists the inspection result after `registry.track` has recorded the final
status. `horus tail` and the dashboard render only that canonical registry result.

If the provider fails before yielding a session id, no registry record exists: clean
up only the immediate `Popen` handle already owned by the current process, record no
tree claim, and never search-and-kill by the pre-launch token.

### Platform boundary

| Platform | Launch scope | Evidence and action |
| --- | --- | --- |
| Linux with delegated cgroup v2 | A small Horus scope runner enters a per-run cgroup before it execs the provider CLI; descendants inherit membership. | `cgroup.procs` is the ownership set. Phase 1 reports only. After promotion, send TERM to current members, wait a bounded grace, then use `cgroup.kill` when available; it handles concurrent forks. Validate the cgroup path under Horus's delegated root before every read/write. |
| Linux without writable/delegated cgroup v2 | New POSIX session/process group. | `report-only`, explicitly partial. Never auto-kill by a recycled PGID. |
| macOS | New POSIX session/process group. | `report-only`, explicitly partial: `killpg` can signal a group, but a `setsid` child can escape and the stored PGID can later be reused. Surface the limitation instead of implying containment. |
| Native Windows | A named Job Object plus a Horus scope runner that is assigned before it spawns the provider CLI; do not allow breakaway. | Job membership is the ownership set. Phase 1 reports only. After promotion, `TerminateJobObject` is allowed only while the named job and registry scope match. Do not use `taskkill /T` as the safety primitive. If assignment/nesting fails, downgrade to `report-only`. |

The runner/parent handshake is required on Linux and Windows: assigning a normal
`Popen` after it starts leaves a fork-before-assignment race. The helper inherits the
provider's stdout so the existing JSONL stream/parser contract remains unchanged.

### Reap eligibility truth table

| Registry/scope condition | Report | Automatic termination |
| --- | --- | --- |
| no matching registry record | no ownership claim | never |
| missing scope or identity mismatch | `unknown` / reason | never |
| session still running or only `stale` | current observation only | never |
| successful `exited` session | warn if children remain | never |
| failed non-worker run | warn if children remain | never |
| failed worker + report-only scope | `children-live` + limitation | never |
| failed worker + matching strong scope | `children-live` | only after the report-first promotion gate |
| inspection/permission error | `reap-failed` + reason | never |

Termination is idempotent. Re-inspect membership and identity immediately before each
action; an already-empty scope becomes `clear`, while any mismatch fails closed.

### Report-first rollout

**Phase 1 — observation, no termination:**

- add the shared scope abstraction and optional registry fields;
- establish the best available scope on headless runs;
- persist the final `process_tree` report;
- append one line to `horus tail`'s terminal result; and
- show `tree clear`, `N children live (report-only)`, or an explicit inspection error
  in the dashboard Sessions row/card.

This phase ships with every backend hard-disabled for termination. Gather one real
failed-worker observation on Linux plus the platform gates below before promotion.

**Phase 2 — guarded reap:**

- enable only `linux-cgroup-v2` and `windows-job` strong scopes;
- only for failed `--worker` records that pass the truth table;
- TERM + grace + `cgroup.kill` on Linux, `TerminateJobObject` on Windows;
- macOS and all fallback scopes remain permanently report-only until a stronger native
  containment primitive is designed and proven.

### Deterministic and live gates

Unit tests use a fake scope backend, not the real process table, and prove:

- only `failed + worker + strong + identity-match` reaches terminate;
- success, non-worker, stale, missing-record, missing-scope, identity-mismatch, and
  report-only cases never terminate;
- unrelated fake processes survive, empty/already-exited races are idempotent, and
  PID reuse becomes a visible mismatch; and
- old registry JSON without the new fields still loads unchanged.

Integration tests spawn only test-owned helpers:

- Linux strong-capability CI: a helper leaves a child inside an isolated cgroup; phase
  1 reports it, phase 2 reaps it, and a same-user process outside the cgroup survives.
  When cgroup delegation is unavailable, assert the honest report-only fallback.
- Windows: a helper/job contains a child; assignment or nesting failure must downgrade,
  never fall back to `taskkill /T`.
- macOS: a process-group child is reported where observable; a deliberately escaped
  child demonstrates the explicit incomplete-coverage label and is cleaned up by the
  test using its exact live handle, never by Horus discovery.

Every live probe carries its own exact handles and teardown. No probe may inspect or
act on the user's existing registry, tmux server, ports, or unrelated process tree.

### Owner approval gate

Approve these three decisions before implementation:

1. **Recommended:** automatic reap is limited to failed `horus run --worker` sessions;
   other runs report only.
2. **Recommended:** ship/report Phase 1 separately and require one real failed-worker
   observation before enabling Phase 2 termination.
3. **Recommended:** Linux cgroup v2 and Windows Job Objects may gain strong automatic
   reap; macOS remains explicitly report-only rather than blocking the feature or using
   unsafe PGID killing.

Primary references: Python `subprocess` session/group semantics
(https://docs.python.org/3/library/subprocess.html), Linux cgroup v2 containment and
`cgroup.kill` (https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html),
Windows Job Objects
(https://learn.microsoft.com/en-us/windows/win32/procthread/job-objects), Apple
`killpg(2)`
(https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/killpg.2.html),
and Linux PID birth/parent/group fields
(https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html).
