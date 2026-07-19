"""The one-shot ``horus run`` executor shared by foreground and tmux runners."""

from __future__ import annotations

import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from horus import adapters, datums, delivery, notify, registry, runlog


@dataclass(frozen=True)
class RunRequest:
    session_id: str
    agent: str
    project: Path
    prompt: str
    account: str | None
    posture: str
    model: str | None
    effort: str | None
    worker: bool
    resume: str | None
    dispatch_base_sha: str | None
    dispatch_pending: int
    delivery_expected: bool = False
    watch: bool = False
    proxied: bool = False
    # An away-mode batch id: when the last worker sharing it terminates, one aggregate
    # `schedule-batch-complete` signal fires (see horus/batch.py). None = not batched.
    batch: str | None = None

    def payload(self) -> dict:
        row = asdict(self)
        row["project"] = self.project.as_posix()
        return row

    @classmethod
    def from_payload(cls, payload: object) -> "RunRequest":
        if not isinstance(payload, dict):
            raise ValueError("runner run request is invalid")
        project = payload.get("project")
        session_id = payload.get("session_id")
        agent = payload.get("agent")
        prompt = payload.get("prompt")
        posture = payload.get("posture")
        if not all(isinstance(value, str) for value in (project, session_id, agent, prompt, posture)):
            raise ValueError("runner run request is missing required fields")
        if posture not in {value.value for value in adapters.PermissionPosture}:
            raise ValueError("runner run request has invalid posture")
        for name in ("account", "model", "effort", "resume", "dispatch_base_sha", "batch"):
            if payload.get(name) is not None and not isinstance(payload[name], str):
                raise ValueError(f"runner run request has invalid {name}")
        if not isinstance(payload.get("worker"), bool) or not isinstance(payload.get("dispatch_pending"), int):
            raise ValueError("runner run request has invalid worker metadata")
        if not isinstance(payload.get("delivery_expected", False), bool):
            raise ValueError("runner run request has invalid delivery expectation")
        if not isinstance(payload.get("watch", False), bool):
            raise ValueError("runner run request has invalid watch flag")
        if not isinstance(payload.get("proxied", False), bool):
            raise ValueError("runner run request has invalid proxied flag")
        root = Path(project)
        if not root.is_dir():
            raise ValueError("runner project directory is missing")
        return cls(
            session_id=session_id, agent=agent, project=root, prompt=prompt,
            account=payload.get("account"), posture=posture, model=payload.get("model"),
            effort=payload.get("effort"), worker=payload["worker"], resume=payload.get("resume"),
            dispatch_base_sha=payload.get("dispatch_base_sha"),
            dispatch_pending=payload["dispatch_pending"],
            delivery_expected=payload.get("delivery_expected", False), watch=payload.get("watch", False),
            proxied=payload.get("proxied", False), batch=payload.get("batch"),
        )


def execute(request: RunRequest, *, watcher: Callable[[str, Path], None] | None = None) -> int:
    """Run exactly one adapter execution, retaining the Horus id as the key.

    This deliberately owns no terminal process.  A foreground caller and the
    managed tmux runner both enter here, so parsing, logging, hooks/account
    environment, registry writes, usage capture, and completion are identical.
    """
    try:
        adapter = adapters.get_adapter(request.agent)
    except KeyError as exc:
        print(exc)
        return 2

    spec = adapters.SpawnSpec(
        prompt=request.prompt,
        project_dir=request.project,
        account=request.account,
        posture=adapters.PermissionPosture(request.posture),
        model=request.model,
        effort=request.effort,
        worker=request.worker,
        run_session_id=request.session_id,
        proxied=request.proxied,
    )
    reg = registry.Registry.default()
    record = reg.get(request.session_id)
    if record is None:
        record = registry.SessionRecord(
            session_id=request.session_id, agent=request.agent, project=request.project.as_posix(),
            account=request.account, pid=os.getpid(), agent_session_id=request.resume,
            dispatch_base_sha=request.dispatch_base_sha, delivery_expected=request.delivery_expected,
        )
        reg.upsert(record)
    try:
        run = adapter.resume(request.resume, spec) if request.resume else adapter.spawn(spec)
    except adapters.AccountMismatch as exc:
        reg.update(request.session_id, termination_reason="launch-error")
        reg.set_status(request.session_id, "failed")
        print(f"Refusing to run: {exc}")
        return 2
    except OSError as exc:
        reg.update(request.session_id, termination_reason="launch-error")
        reg.set_status(request.session_id, "failed")
        print(f"Failed to start {request.agent}: {exc}")
        return 1

    launch_fields: dict[str, object] = {"agent_session_id": run.session.session_id}
    # A detached tmux run is hosted by the runner process, which remains alive
    # while delivery evidence, usage, and the terminal datum are finalized.
    # Replacing that durable PID with the adapter child creates a false-death
    # window as soon as the child exits: a concurrent ``sessions`` reconcile can
    # then overwrite the runner's clean terminal receipt with stale/blocked.
    # Foreground runs have no durable host, so their adapter child stays the
    # correct liveness PID. In-memory adapters have no child and keep whichever
    # launcher/runner PID was already registered.
    if run.session.pid is not None and record.launch_target != "tmux":
        launch_fields["pid"] = run.session.pid
    reg.update(request.session_id, **launch_fields)
    log = runlog.RunLog()
    log.bind(request.session_id)
    store = datums.DatumStore.default()
    run_started = time.monotonic()
    saw_usage_signal = False
    resolved_model: str | None = None
    watcher_pending = request.watch
    started_native_id = run.session.session_id

    runlog.append_event(
        request.session_id,
        "start",
        agent=request.agent,
        agent_session_id=started_native_id,
        account=request.account,
        project=request.project.as_posix(),
        pid=run.session.pid,
        argv={
            "prompt": request.prompt,
            "posture": request.posture,
            "model": request.model,
            "effort": request.effort,
            "resume": request.resume,
            "dispatch_base_sha": request.dispatch_base_sha,
            "continuity_pending": request.dispatch_pending,
            "delivery_expected": request.delivery_expected,
        },
    )
    usage_launch = datums.capture_usage_snapshot(request.agent, request.account)

    def record_launch(native_id: str | None, resolved: str | None) -> None:
        store.record_launch(datums.Datum(
            session_id=request.session_id, agent_session_id=native_id,
            model=datums.canonical_model_name(request.model, resolved=resolved),
            launched_at=runlog.utc_iso(), project=request.project.as_posix(), account=request.account,
            effort=request.effort, agent=request.agent, worker=request.worker, posture=request.posture,
            environment=run.session.environment, usage_launch=usage_launch,
            delivery_expected=request.delivery_expected, dispatch_base_sha=request.dispatch_base_sha,
        ))

    record_launch(started_native_id, resolved_model)

    def emit(line: str) -> None:
        print(line)
        log.line(line)

    for ev in run:
        if ev.type is adapters.EventType.SESSION_STARTED and ev.raw:
            resolved_model = ev.raw.get("model") or resolved_model
        native_id = run.session.session_id or ev.session_id
        reg.update(request.session_id, agent_session_id=native_id, last_activity_at=runlog.utc_iso())
        if ev.type is adapters.EventType.SESSION_STARTED:
            record_launch(native_id, resolved_model)
        runlog.append_event(
            request.session_id, "activity", agent_session_id=native_id, event_type=ev.type.value,
        )
        if watcher_pending and watcher is not None:
            watcher_pending = False
            watcher(request.session_id, request.project)
        if ev.type is adapters.EventType.ERROR and datums.looks_like_usage_death(ev.text):
            saw_usage_signal = True
        if ev.type is adapters.EventType.SESSION_STARTED:
            emit(f"... session {ev.session_id}")
        elif ev.type is adapters.EventType.ASSISTANT_TEXT and ev.text:
            emit(ev.text)
        elif ev.type is adapters.EventType.TOOL_USE:
            emit(f"  [tool] {ev.tool}")
        elif ev.type is adapters.EventType.ERROR:
            emit(f"  [error] {ev.text or ''}")

    session = run.session
    status = session.status
    ended_at = runlog.utc_iso()
    try:
        session_end = datetime.fromisoformat(ended_at)
    except ValueError:  # utc_iso is controlled, but delivery must never break completion
        session_end = None
    evidence = delivery.capture_delivery_evidence(
        request.project, dispatch_base_sha=request.dispatch_base_sha, session_end=session_end,
    )
    delivery_status = delivery.classify_delivery(
        status, delivery_expected=request.delivery_expected,
        dispatch_base_sha=request.dispatch_base_sha, evidence=evidence,
    )
    reg.update(
        request.session_id, agent_session_id=session.session_id, termination_reason="natural",
        delivery_status=delivery_status, **evidence.fields(),
    )
    reg.set_status(request.session_id, status, returncode=session.returncode)
    runlog.append_event(
        request.session_id, "result", agent_session_id=session.session_id,
        status=status, rc=session.returncode, delivery_status=delivery_status,
        delivery_expected=request.delivery_expected, **evidence.fields(), ended_at=ended_at,
    )
    store.record_completion(
        request.session_id, exit=datums.classify_exit(status, saw_usage_signal=saw_usage_signal),
        runtime_seconds=round(time.monotonic() - run_started, 3), returncode=session.returncode,
        delivery_status=delivery_status, delivery_expected=request.delivery_expected,
        dispatch_base_sha=request.dispatch_base_sha, **evidence.fields(),
    )
    if request.worker:
        actual = next(
            (row for row in datums.worker_breakdown(store.all()) if row["run_id"] == request.session_id),
            None,
        )
        if actual is not None:
            emit("\n" + datums.render_worker_breakdown([actual]).rstrip())
        result = _escalate_completion(
            request, status, delivery_status, evidence, saw_usage_signal=saw_usage_signal,
        )
        if result is not None and not result.delivered and result.error:
            emit(f"  [notify] {result.describe()}")
        elif result is not None and result.delivered:
            emit(f"  [notify] {result.describe()}")
        # Last-one-out: if this worker is the final leg of its batch to terminate, one
        # aggregate batch-complete signal fires now (idempotent; best-effort, never
        # fails the run). Import lazily so a plain `horus run` avoids the schedule read.
        if request.batch:
            try:
                from horus import batch as _batch
                batch_result = _batch.emit_if_complete(request.batch, request.project)
                if batch_result is not None:
                    emit(f"  [notify] batch {request.batch}: {batch_result.describe()}")
            except Exception:  # noqa: BLE001 — a rollup signal must never break completion
                pass
    emit(f"\n{status} — session {request.session_id} (account {request.account or '-'})")
    return 0 if status == "exited" else 1


def _escalate_completion(
    request: RunRequest,
    status: str,
    delivery_status: str | None,
    evidence: "delivery.DeliveryEvidence",
    *,
    saw_usage_signal: bool,
) -> notify.EscalationResult | None:
    """Push a best-effort escalation when an unattended worker ends badly.

    Fires only for worker/unattended runs, and only on an actionable outcome — a run
    halted on usage, or a ``blocked``/``failed`` delivery. A clean accept stays silent
    (no ``success`` ping unless the owner opts in, which the event gate handles). Never
    raises: :func:`notify.escalate` is best-effort, so this can never fail completion.
    """
    branch = evidence.branch
    card = branch[len("auto/"):] if branch and branch.startswith("auto/") else None
    common = dict(
        project=request.project.name,
        session_id=request.session_id,
        card=card,
        sha=(evidence.head_sha or "")[:12] or None,
        pr=evidence.pr_number,
        inspect=f"horus sessions · session {request.session_id}",
    )
    if saw_usage_signal and status != "exited":
        esc = notify.Escalation(
            event=notify.USAGE_BAND, summary="unattended run halted on usage", **common,
        )
    elif delivery_status in {"blocked", "failed"}:
        esc = notify.Escalation(
            event=notify.DELIVERY_FAILED,
            summary=f"scheduled worker delivery {delivery_status}",
            **common,
        )
    else:
        return None
    return notify.escalate(esc)
