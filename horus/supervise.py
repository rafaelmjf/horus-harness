"""Unattended verify → merge → close → escalate for a dispatched card.

A *scheduled* dispatch has no live supervisor. `horus supervise <session|pr>` is the
headless andon that runs after a worker finishes: it **independently verifies** the
delivery — never trusting the worker's own "done" — and then either accepts it (merge +
close + ship the card) or escalates a problem and halts dependent scheduled work.

The disciplines this encodes (AGENTS.md; `horus/delivery.py:88`):

- **Reproduce the gate, never trust the report.** Verification is a *required* CI check
  green on the EXACT head SHA (`mergewatch.watch`) + the freshness/continuity gate
  (`closure.pr_freshness_gate`) + — before an authorized merge — one live probe of the
  changed surface. `delivery-ready` is evidence for review, never merge authority.
- **Merge authority is opt-in and bounded.** A merge fires only when the run's standing
  envelope was created with merge authority (`envelope.merge_authority`, default false).
  Absent that, or absent a pinned dispatch base / `--expect-delivery`, supervise verifies
  and escalates but MERGES NOTHING — it never guesses.
- **The live probe is owner-authored and machine-local**, passed as ``--probe`` (never a
  committed command — committed probes are data, not commands). Merge authorized with no
  probe declared ⇒ refuse to merge and escalate; we never auto-merge without it.
- **Andon.** An escalation halts every scheduled dispatch whose card transitively
  ``depends-on`` the failed card, so no dependent work fires on a red base. Independent
  scheduled work is untouched, and the halt is visible in `horus schedule list`.
- **Best-effort escalation, deterministic verdict.** The push is best-effort
  (`notify.escalate` never raises); the accept/escalate verdict and exit code are not.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from horus import backlog, closure, envelope, mergewatch, notify, registry, schedule

_NO_WINDOW = (
    {"creationflags": getattr(subprocess, "CREATE_NO_WINDOW", 0)}
    if sys.platform == "win32"
    else {}
)

# How long verification waits for required checks to settle before treating a
# still-pending gate as "not green" and escalating. Unattended has no one to wait.
_WATCH_TIMEOUT = 1800.0


@dataclass(frozen=True)
class SupervisionContext:
    """Everything supervise needs, resolved from durable state (registry + envelope
    ledger), never from the worker's self-report."""

    root: Path
    pr_ref: str | None          # PR number/URL or head sha to verify + merge
    head_sha: str | None
    base_ref: str | None        # the pinned dispatch base (an exact sha)
    card: str | None
    delivery_expected: bool
    merge_authority: bool
    session_id: str | None = None
    envelope_name: str | None = None


@dataclass(frozen=True)
class SuperviseOutcome:
    verdict: str                # "merged" | "verified" | "escalated" | "noop"
    reason: str
    escalation: notify.EscalationResult | None = None
    halted: tuple[str, ...] = ()   # card names whose scheduled dispatch was halted

    @property
    def exit_code(self) -> int:
        # accept (merged/verified/noop) → 0; escalate → 1. The verdict is the gate.
        return 0 if self.verdict in {"merged", "verified", "noop"} else 1


# --------------------------------------------------------------------------- #
# Resolution — durable state only
# --------------------------------------------------------------------------- #


def _find_envelope_for_session(session_id: str) -> tuple[str | None, str | None, bool]:
    """(envelope_name, card, merge_authority) for the envelope that authorized this
    session, scanning every envelope's append-only ledger. Absent ⇒ (None, None, False):
    an unenveloped run has no merge authority, so supervise falls back to verify-only."""
    for env in envelope.load_all():
        for row in envelope.read_ledger(env.name):
            if row.get("session_id") == session_id:
                return env.name, (row.get("card") or None), bool(env.merge_authority)
    return None, None, False


def resolve_context(target: str, *, path: str | Path | None = None) -> SupervisionContext | None:
    """Resolve a session id/prefix (preferred) or a PR ref into a context.

    A session id gives the full picture — pinned base, delivery expectation, and the
    authorizing envelope's merge authority. A bare PR ref can be verified but never
    carries a dispatch base or merge authority, so it stays verify+escalate-only.
    """
    reg = registry.Registry.default()
    records = reg.all()
    matches = [r for r in records if r.session_id == target or r.session_id.startswith(target)]
    if len(matches) == 1:
        rec = matches[0]
        env_name, card, merge_authority = _find_envelope_for_session(rec.session_id)
        pr_ref = str(rec.delivery_pr_number) if rec.delivery_pr_number else rec.delivery_head_sha
        return SupervisionContext(
            root=Path(path) if path else Path(rec.project),
            pr_ref=pr_ref,
            head_sha=rec.delivery_head_sha,
            base_ref=rec.dispatch_base_sha,
            card=card,
            delivery_expected=bool(rec.delivery_expected),
            merge_authority=merge_authority,
            session_id=rec.session_id,
            envelope_name=env_name,
        )
    if matches:
        return None  # ambiguous prefix — caller escalates rather than guessing
    # Not a session id: treat as a PR ref, verify-only (no base, no authority).
    return SupervisionContext(
        root=Path(path) if path else Path.cwd(),
        pr_ref=target, head_sha=None, base_ref=None, card=None,
        delivery_expected=False, merge_authority=False,
    )


# --------------------------------------------------------------------------- #
# Effect seams — real implementations; tests monkeypatch these module functions.
# --------------------------------------------------------------------------- #


def _verify_ci(root: Path, ref: str, *, timeout: float) -> tuple[bool, str]:
    """Required CI green on the exact head SHA. (True, sha) or (False, why)."""
    try:
        outcome = mergewatch.watch(root, ref, timeout=timeout, emit=lambda _l: None)
    except mergewatch.MergeWatchError as exc:
        return False, f"could not watch checks: {exc}"
    if outcome.state == "success":
        return True, outcome.sha
    return False, f"required checks {outcome.state} on {outcome.sha[:12]}"


def _verify_freshness(root: Path, base_ref: str) -> tuple[bool, str]:
    """The continuity/freshness gate for this PR's diff. (True, "") or (False, why)."""
    findings = closure.pr_freshness_gate(root, base_ref)
    blocking = [f for f in findings if f.level in ("warn", "fail")]
    if blocking:
        return False, "; ".join(f.message for f in blocking)
    return True, ""


def _run_probe(root: Path, probe: str, *, timeout: float = 900.0) -> tuple[bool, str]:
    """Run the owner-authored, machine-local live probe in the project root.

    Shell execution is deliberate: the probe is owner-authored on THIS machine (the same
    trust level as the systemd unit that invokes supervise), not read from the repo."""
    try:
        result = subprocess.run(  # noqa: S602 - owner-authored machine-local command
            probe, shell=True, cwd=str(root), capture_output=True, text=True,
            timeout=timeout, **_NO_WINDOW,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return False, f"probe could not run: {exc}"
    if result.returncode == 0:
        return True, ""
    detail = (result.stderr or result.stdout or "").strip()
    return False, f"probe exited {result.returncode}: {detail[-200:]}"


def _pr_state(root: Path, ref: str) -> str | None:
    """The PR's state ("MERGED"/"OPEN"/"CLOSED") for idempotency, or None if unknown."""
    result = subprocess.run(  # noqa: S603
        ["gh", "pr", "view", ref, "--json", "state", "-q", ".state"],
        cwd=str(root), capture_output=True, text=True, **_NO_WINDOW,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _merge_pr(root: Path, ref: str) -> tuple[bool, str]:
    """Merge an already-verified-green PR now (not --auto, which would re-wait)."""
    result = subprocess.run(  # noqa: S603
        ["gh", "pr", "merge", ref, "--merge"],
        cwd=str(root), capture_output=True, text=True, **_NO_WINDOW,
    )
    if result.returncode == 0:
        return True, ""
    return False, (result.stderr or result.stdout or "").strip()


def _close_continuity(root: Path) -> tuple[bool, str]:
    """Supervisor owns canonical continuity: `close --commit --push` after a merge."""
    try:
        ok, detail = closure.commit_continuity(root, None, push=True)
        return bool(ok), detail
    except Exception as exc:  # noqa: BLE001 - close must not crash a completed merge
        return False, str(exc)


def _ship_card(root: Path, card: str, *, pr: str, sha: str) -> None:
    existing = backlog.find_card(root, card)
    if existing is None or existing.status == "shipped":
        return  # already shipped / no such card — idempotent
    backlog.ship(root, card, pr=pr, sha=sha)


# --------------------------------------------------------------------------- #
# Andon
# --------------------------------------------------------------------------- #


def _card_deps(root: Path) -> dict[str, set[str]]:
    deps: dict[str, set[str]] = {}
    for card in backlog.load_cards(root):
        raw = card.field_value("depends-on") or card.field_value("depends_on")
        deps[card.name] = {p.strip() for p in re.split(r"[,\n]", raw) if p.strip()}
    return deps


def _transitive_dependents(target_card: str, deps: dict[str, set[str]]) -> set[str]:
    """Every card that transitively depends on ``target_card``."""
    reverse: dict[str, set[str]] = {}
    for card, ds in deps.items():
        for d in ds:
            reverse.setdefault(d, set()).add(card)
    seen: set[str] = set()
    stack = [target_card]
    while stack:
        for dependent in reverse.get(stack.pop(), ()):
            if dependent not in seen:
                seen.add(dependent)
                stack.append(dependent)
    return seen


def _scheduled_card(command: tuple[str, ...]) -> str | None:
    for i, part in enumerate(command):
        if part == "--card" and i + 1 < len(command):
            return command[i + 1]
    return None


def halt_dependents(root: Path, failed_card: str, reason: str) -> list[str]:
    """Disarm every SCHEDULED, not-yet-fired dispatch whose card transitively
    depends on ``failed_card``. Returns the halted card names."""
    if not failed_card:
        return []
    dependents = _transitive_dependents(failed_card, _card_deps(root))
    halted: list[str] = []
    for sched in schedule.load_all():
        if sched.fired or sched.halted:
            continue
        card = _scheduled_card(sched.command)
        if card and card in dependents:
            if schedule.halt(sched.id, f"blocked: depends on failed card {failed_card} ({reason})"):
                halted.append(card)
    return halted


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #


def _escalate(ctx: SupervisionContext, summary: str) -> notify.EscalationResult:
    return notify.escalate(notify.Escalation(
        event=notify.SUPERVISE_GATE,
        project=ctx.root.name,
        summary=summary,
        session_id=ctx.session_id,
        card=ctx.card,
        sha=(ctx.head_sha or "")[:12] or None,
        pr=int(ctx.pr_ref) if (ctx.pr_ref or "").isdigit() else None,
        inspect=f"horus sessions · PR {ctx.pr_ref}" if ctx.pr_ref else "horus sessions",
    ))


def _escalate_and_halt(ctx: SupervisionContext, summary: str) -> SuperviseOutcome:
    result = _escalate(ctx, summary)
    halted = halt_dependents(ctx.root, ctx.card or "", summary) if ctx.card else []
    return SuperviseOutcome(
        verdict="escalated", reason=summary, escalation=result, halted=tuple(halted),
    )


def supervise(
    ctx: SupervisionContext,
    *,
    probe: str | None = None,
    watch_timeout: float = _WATCH_TIMEOUT,
) -> SuperviseOutcome:
    """Run the unattended acceptance gate for one delivery. See module docstring."""
    if ctx.pr_ref is None:
        return _escalate_and_halt(ctx, "no PR or head sha to verify — nothing delivered")

    # Idempotency: a re-fired supervise (or one the owner already merged) is a no-op.
    if str(ctx.pr_ref).isdigit() and _pr_state(ctx.root, ctx.pr_ref) == "MERGED":
        return SuperviseOutcome(verdict="noop", reason="PR already merged")

    # Never accept on the worker's self-report: a merge needs a pinned base + expectation.
    can_merge_basis = ctx.delivery_expected and bool(ctx.base_ref)

    # 1. Required CI green on the exact head SHA.
    ci_ok, ci_detail = _verify_ci(ctx.root, ctx.pr_ref, timeout=watch_timeout)
    if not ci_ok:
        return _escalate_and_halt(ctx, f"verification failed — {ci_detail}")

    # 2. Freshness/continuity gate (only meaningful with a pinned base).
    if ctx.base_ref:
        fresh_ok, fresh_detail = _verify_freshness(ctx.root, ctx.base_ref)
        if not fresh_ok:
            return _escalate_and_halt(ctx, f"freshness gate failed — {fresh_detail}")

    # Verified green. verify+escalate-only (the safe default) stops here — a clean verify
    # is not a failure, so no escalation (success is silent); the verdict carries it and a
    # human does the merge.
    if not ctx.merge_authority:
        return SuperviseOutcome(
            verdict="verified", reason="verified green; merge not authorized (verify+escalate only)")

    # Merge authorized ⇒ never accept on the worker's self-report: a pinned dispatch base
    # and an explicit delivery expectation are the proof this is a tracked delivery.
    if not can_merge_basis:
        return _escalate_and_halt(
            ctx, "merge authorized but no pinned dispatch base / delivery expectation — "
                 "refusing to accept on self-report")

    # 3. Merge authorized ⇒ the live probe is mandatory and owner-authored.
    if not probe:
        return _escalate_and_halt(
            ctx, "merge authorized but no live probe declared — refusing to merge unattended")
    probe_ok, probe_detail = _run_probe(ctx.root, probe)
    if not probe_ok:
        return _escalate_and_halt(ctx, f"live probe failed — {probe_detail}")

    # 4. All gates green + authorized + probe passed → merge, close, ship.
    merged, merge_detail = _merge_pr(ctx.root, ctx.pr_ref)
    if not merged:
        return _escalate_and_halt(ctx, f"verified green but merge failed — {merge_detail}")
    _close_continuity(ctx.root)
    if ctx.card and ctx.head_sha:
        _ship_card(ctx.root, ctx.card, pr=str(ctx.pr_ref), sha=ctx.head_sha)
    return SuperviseOutcome(verdict="merged", reason=f"merged PR {ctx.pr_ref} and shipped {ctx.card or '-'}")
