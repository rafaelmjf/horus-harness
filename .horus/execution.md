---
status: in-progress
current_feature: "Worker-lifecycle campaign: attachable detached one-shot workers + the delivery-evidence/completion kernel (backlog: attachable-detached-worker-run, carrying the kernels of worker-progress-heartbeat and deferred-supervision-completion-receipt per their 2026-07-16 reviews)."
supervisor_tier: frontier
worker_tier: scoped-implementation
delegation_basis: "Phase 0 stayed direct because it was design/ambiguity work. Phase 1 is now schema-pinned, fenceable implementation with a full-suite + live-probe gate; the live proven scoped-implementation tier buys lower-tier savings and preserves the supervisor's cross-surface acceptance context beyond the handoff/review tax. Re-decide phase 2 after phase 1 lands."
last_updated: 2026-07-16
---

# Execution Plan — worker-lifecycle campaign

Drafted 2026-07-16 in the session that re-scoped the three worker-lifecycle cards,
so the design constraints below carry that context to the executing session. Keep
this file fluid; statuses move as phases land. (Previous completed plan:
usage-limit survival kit, PR #115 — see git history of this file.)

## Why this shape

Three cards described one feature from three angles (liveness, progress, delivery).
Implemented independently they would produce three consecutive registry/run-log
schema changes and risk inconsistent state taxonomies. One campaign, one schema
design, kernel-only scope: the periodic stall timer and the receipt trimmings are
explicitly deferred (see the two demoted cards' Reviews).

## Design constraints (phase 0 output must satisfy these)

- **One worker-state model, three orthogonal dimensions**, designed together even
  where only partially implemented now:
  - *liveness*: `running | exited | failed | stale` (reconciliation-owned);
  - *delivery*: `delivery-ready | blocked | no-op | failed | unknown` — backed by
    process status plus pushed SHA/PR/continuity receipt; `delivery-ready` is never
    acceptance or permission to merge;
  - *progress*: schema reserves the dimension (a last-activity timestamp slot);
    the periodic heartbeat/stall classifier is deferred — one field later, not a
    migration.
- **A clean exit with zero delivery evidence when the brief expected some is
  surfaced as `no-op`, never bare success** — this is the failure-evidenced kernel
  (gvfs-parked worker, 2026-07-15 campaign) and is in scope NOW.
- Detached execution reuses the managed tmux runner + one-shot adapter contracts;
  no daemon, no second adapter path, no auto-resume/auto-merge/auto-launch on exit.
- Launcher/caller death (including a foreground caller's SIGTERM on timeout) never
  kills a dispatched worker — the observed incident this campaign exists to fix.
- Every tmux-touching test/probe uses a private socket (`tmux -S <path>`); reapers
  act only on positive registry confirmation (standing rules).

## Phases

| phase | status | scope | gate |
|---|---|---|---|
| 0 state model + schema | complete (direct) | registry/run-log fields for the three dimensions; parity map against current foreground `horus run` fields | design below checked against every phase-0 constraint; no product code changed |
| 1 detached attachable one-shot | planned (delegated; scoped-implementation tier) | `horus run --worker … --detach` (or equivalent) on the managed tmux host; TUI attach/detach; natural-exit parity (status, rc, run log, datums, delivery facts); caller-death survival | full pytest + required CI green on the exact SHA + live probe: launch detached, kill the launcher, attach/detach, observe clean completion with parity fields recorded |
| 2 delivery-evidence + completion kernel | planned | `no-op` detection at exit; `delivery-ready|blocked|failed|unknown` exposed via sessions/CLI-JSON without prose parsing | tests for no-op, delivering, failed, unknown; live probe: a scripted worker that exits 0 delivering nothing must surface as `no-op` |

## Phase 0 frozen design (2026-07-16)

### Identity and one execution path

- `session_id` becomes the stable **Horus run id** used as the registry key, tmux
  target suffix, text/JSONL log key, datum key, hook rescue key, and CLI/TUI handle.
  It is allocated before tmux starts, so a detached launch can return a durable
  handle before the native CLI emits anything. Existing rows remain valid because
  their current id already serves all of those roles.
- Add nullable `agent_session_id` for the native Claude/Codex resumable id. For a
  legacy row, readers treat a missing value as `session_id`. Adapter
  `AgentSession.session_id` continues to mean this native id; the orchestration
  layer, not the adapter contract, owns the Horus run id.
- Split current `cmd_run` preparation from one shared run executor. Foreground
  calls it in-process. Detached launch writes the same validated execution spec
  to the existing 0600 tmux runner handoff and the runner calls that executor
  inside the managed pane. There is no nested/alternate adapter implementation:
  account isolation, posture/model/effort, hooks, usage capture, event parsing,
  registry/log/datum writes, and natural exit all stay in the shared executor.
- The parent returns only after tmux creation and the runner-pid registry handoff.
  After that handoff, parent exit or SIGTERM has no ownership edge to the tmux
  runner or agent child. A viewer is never part of the process-lifetime chain.

### Registry schema

Keep the JSON row additive and flat so old installations/rows degrade cleanly.
New writes carry these fields; absent fields read with the defaults shown.

| field | values / default | owner and meaning |
|---|---|---|
| `session_id` | UUID / existing id | stable Horus run identity |
| `agent_session_id` | string or `null` | native resumable conversation/thread id |
| `status` | `running\|exited\|failed\|stale` | liveness only; reconciliation owns corrections |
| `termination_reason` | string or `null` | optional cause such as `natural`, `launch-error`, `stopped`, `orphan-reaped`; never a second status |
| `returncode` | integer or `null` | process result, unchanged |
| `delivery_expected` | boolean, default `false` | explicit launch intent; never inferred from prompt prose |
| `delivery_status` | `delivery-ready\|blocked\|no-op\|failed\|unknown`, default `unknown` | delivery dimension only; never acceptance/merge permission |
| `dispatch_base_sha` | SHA or `null` | pinned comparison base captured before dispatch |
| `delivery_branch` | string or `null` | branch inspected at completion |
| `delivery_head_sha` | SHA or `null` | local HEAD observed at completion |
| `delivery_pushed_sha` | SHA or `null` | pushed commit attributable to this run |
| `delivery_pr_number` | integer or `null` | PR whose head contains the attributable pushed SHA |
| `delivery_local_changes` | boolean or `null` | dirty tree or local HEAD beyond the dispatch base |
| `delivery_continuity_closed` | boolean or `null` | supporting receipt fact, not delivery by itself |
| `delivery_checked_at` | UTC ISO timestamp or `null` | freshness of the evidence snapshot |
| `last_activity_at` | UTC ISO timestamp or `null` | progress slot, updated on normalized adapter events |

`updated_at` remains the row-mutation timestamp and must not double as progress.
The old `orphaned` value is read as legacy terminal state but is never newly
written: an explicit stop/reap records `failed` with `termination_reason`; a lost
process without a terminal result reconciles to `stale`. No periodic timer or
`stalled` state is introduced in this campaign.

### Delivery classification kernel

Evidence is always compared with `dispatch_base_sha`: an unchanged remote base is
not a delivery signal (the 2026-07-15 `stale-but-delivered` false positive). A PR
counts only when its head contains the attributable pushed SHA. Continuity closure
alone is supporting context and never promotes a run.

| condition at completion/reconciliation | `delivery_status` |
|---|---|
| still running, delivery not expected, or evidence cannot be inspected safely | `unknown` |
| clean exit + attributable pushed SHA newer than base (optionally PR) | `delivery-ready` |
| clean exit + only local/unpushed work beyond base | `blocked` |
| clean exit + delivery expected + no local or remote evidence beyond base | `no-op` |
| failed/stale + any local or attributable remote evidence | `blocked` |
| failed/stale + delivery expected + confirmed absence of evidence | `failed` |

This classifier is a pure function over liveness, intent, base, and captured git/PR
facts. Git/gh lookup remains best-effort, but probe failure yields `unknown` rather
than guessing. `delivery-ready` means “there is reviewable remote evidence”; it is
never an acceptance verdict and never triggers merge/resume/launch.

### Structured log and datum parity

- JSONL `start`, `activity`, and `result` events use the stable Horus `session_id`
  and carry `agent_session_id` once known. `activity` updates only the reserved
  timestamp slot; it does not classify stalls. `result` carries liveness,
  returncode, delivery status, and the minimal evidence fields above.
- The human text log stays a tee of the shared executor and is keyed by the Horus
  id, so `horus tail` works before the native id arrives.
- Datum `session_id` joins on the Horus id; add `agent_session_id` and mechanical
  `delivery_status`/pushed-SHA/PR fields at completion. Existing exit and qualitative
  axes stay unchanged. Foreground and detached runs call the same launch/completion
  writes exactly once.

### Foreground/detached parity map

| concern | foreground owner today | detached design |
|---|---|---|
| adapter spawn/resume + normalized events | `cmd_run` / adapter contract | same shared executor inside tmux runner |
| account, posture, model/effort, worker hooks | `SpawnSpec` + adapter env | same validated spec, no environment cloning |
| pinned base + pending-continuity signal | `cmd_run` before spawn | captured before handoff, carried in 0600 spec |
| registry PID/status/rc | `registry.track` + completion | stable pre-row, then same event/completion updates |
| run log + datum | `cmd_run` event loop | same event loop, keyed by Horus id |
| delivery facts | post-hoc `delivery.py` display | pure classifier persists a completion snapshot; display reads it |
| process lifetime | foreground caller owns adapter child | tmux runner owns adapter child after durable handoff |
| attach/detach | unavailable | existing managed tmux target/TUI actions while `running` |

### Native-input boundary found during design

The installed Claude CLI exposes realtime `--input-format stream-json`, but Codex
`exec` exposes only an initial stdin prompt and no live message channel. Therefore
the common phase-1 primitive guarantees attach/detach for observation and terminal
control, not cross-agent live clarification. Raw pane input must not be advertised
as portable or silently discarded. Claude-specific streaming input is a possible
later adapter capability; Codex clarification would require a native signal or an
explicit resume action after exit, and this campaign forbids inventing a second
adapter path or auto-resume. The phase-1 live gate remains attach/detach observation,
as authored above.

### Phase-0 constraint check

- Three dimensions are orthogonal: `status`, `delivery_status`, and
  `last_activity_at`; no composite `stale-but-delivered` state is stored.
- A clean expected-delivery exit without evidence deterministically becomes
  `no-op`.
- The managed tmux runner hosts the same one-shot executor; no daemon or second
  adapter path is added.
- The stable preallocated run id + runner handoff removes caller/viewer lifetime
  ownership.
- Tests and live probes must inject an explicit private `tmux -S <path>` socket;
  no probe may touch the default server, and reaping still requires a matching
  registry row plus terminal/dead state and idle/unattached confirmation.

## Deferred (do not implement in this campaign)

Periodic heartbeat/stall timer; `active|on-completion` supervision taxonomy;
usage-close snapshot embedded in the receipt; richer TUI receipt surface. Gated on
one real campaign using the detached primitive + a check of native-platform
progress/notification signals at that time.
