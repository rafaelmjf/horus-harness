"""Empirical model-calibration datums — the measured half of the delegation spine.

Two consumer flows decide the same thing ("implement directly, or delegate/plan,
and how much?"): the in-project ``horus-execution`` skill (subagents) and the
multi-project cockpit dispatch (sessions). They should share ONE calibration +
verification rubric backed by REAL data instead of hand-written prose datums in
session notes. This module is the low-overhead empirical loop under that rubric.

Two data layers, kept strictly separate:

- **Measured datums** (this module, ``~/.horus/datums.json``): one row per tracked
  ``horus run``, written mechanically at launch/completion (the whole overhead win
  — the mechanical half writes itself, zero agent overhead), then closed with an
  agent-supplied qualitative half (``outcome``/``shape``/``note``) via
  ``horus datum close``.
- **Owner priors** (``~/.horus/capabilities.toml``, hand-edited, fleet-global):
  per-model constraints/cautions that shape HOW to use a model — read here but
  never written by a run. This also carries the optional price-for-capability
  fields (``price_in``/``price_out``/``capability_note``/``researched_at``) and
  lifecycle provenance (``available``/``retires_at``) —
  see the ``older-models-in-roster`` backlog card. Populating THOSE fields is a
  separate agent web-research pass; this module only parses, displays, and
  nudges on staleness (``staleness_warning``) — it never fetches the network.

HARD BOUNDARY (do not cross): the harness MEASURES and DISPLAYS; the AGENT judges.
``outcome`` is ALWAYS agent-supplied, NEVER an auto-scoring function. Nothing here
returns or suggests an executable model pick, and nothing auto-routes a dispatch.
The roll-up is the picture the agent reads — data only, advisory forever.
"""

from __future__ import annotations

import json
import re
import time
import tomllib
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from horus import config

# Agent-supplied review outcomes. Only QUALITY_OUTCOMES belong in the quality
# denominator; operational endings remain visible without grading work that was
# never completed or tested.
QUALITY_OUTCOMES: tuple[str, ...] = ("clean", "nudged", "bounced")
OPERATIONAL_OUTCOMES: tuple[str, ...] = ("died", "void")
OUTCOMES: tuple[str, ...] = QUALITY_OUTCOMES + OPERATIONAL_OUTCOMES

# Mechanically-captured process-exit axis (why the run ENDED — distinct from quality).
EXITS: tuple[str, ...] = ("completed", "crashed", "usage-death")

# Agent-supplied supervisor-cost half (the 2026-07-14 frozen schema — see the
# `datum-supervisor-cost-envelope` backlog card). Set ONLY via `horus datum
# close`'s optional flags, same hard boundary as `outcome`: the agent judges,
# the harness records — never inferred, never auto-scored.
OVERSIGHT_LEVELS: tuple[str, ...] = ("light", "moderate", "heavy")
COUNTERFACTUALS: tuple[str, ...] = ("direct-session", "one-worker", "multi-worker")
DIVIDENDS: tuple[str, ...] = ("positive", "neutral", "negative")

# Freshness axis for the mechanical usage snapshots (`usage_launch`/`usage_close`).
# "fresh" only ever means "this read reflects the provider's own live/cached state
# at read time" — it is never a judgment about whether the number itself is good.
USAGE_FRESHNESS: tuple[str, ...] = ("fresh", "stale", "unavailable")

# How many recent outcomes the roll-up surfaces per model.
LAST_N = 5

# Best-effort heuristic: an adapter-level ERROR line that looks like a usage/quota
# wall (not a normal failing tool call). Only ever inspected on ERROR events, so
# prose that merely mentions "rate limit" can't misclassify a clean run.
_USAGE_DEATH_RE = re.compile(
    r"usage[ _-]?limit|rate[ _-]?limit|quota|exhaust|out of (?:tokens|credit)|"
    r"insufficient_quota|429|too many requests",
    re.IGNORECASE,
)


def datums_path() -> Path:
    return config.config_dir() / "datums.json"


def priors_path() -> Path:
    return config.config_dir() / "capabilities.toml"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Canonical model names — a real rename, not an alias/mirror (see the
# `model-name-normalization-and-datum-migration` backlog card). Measured
# datums and owner priors/pricing must key on the SAME versioned name
# (`sonnet-5`, not bare `sonnet`) or they render as two half-complete rows
# that never join.
# ---------------------------------------------------------------------------

# Owner-maintained fallback map, small and living next to `capabilities.toml`.
# Only consulted when an adapter didn't expose what actually ran (see
# `canonical_model_name`) — a static map like this goes stale the moment a
# family default moves (`sonnet` -> `sonnet-6` later), so resolved-capture is
# always preferred and this is the fallback, not the primary path. The GPT-5.6
# family is the exception: OpenAI documents the unsuffixed name as an alias for
# Sol, so legacy generic datums/priors must join the canonical Sol row.
ALIAS_TO_CANONICAL: dict[str, str] = {
    "sonnet": "sonnet-5",
    "haiku": "haiku-4.5",
    "opus": "opus-4.8",
    "gpt-5.6": "gpt-5.6-sol",
}

# Matches a Claude Code resolved model id, e.g. "claude-haiku-4-5-20251001" or
# "claude-sonnet-5-20260101" -> ("haiku", "4", "5") / ("sonnet", "5", None).
_RESOLVED_MODEL_RE = re.compile(
    r"^claude-(?P<family>sonnet|opus|haiku|fable)-(?P<major>\d+)(?:-(?P<minor>\d+))?-\d{8}$"
)


def canonical_model_name(alias: str | None, *, resolved: str | None = None) -> str | None:
    """Normalize a captured model to its canonical versioned name.

    Prefers ``resolved`` — the concrete model an adapter reports it actually ran
    (e.g. Claude Code's ``system/init`` event carries ``"claude-haiku-4-5-
    20251001"`` even when the run was launched with the bare alias ``haiku``) —
    since that stays correct across a family-default move that a static map
    would mis-record. Falls back to :data:`ALIAS_TO_CANONICAL` when no
    resolution is available (e.g. Codex's stream reports no model at all). A
    name that's already canonical, or unrecognized (a literal
    version string), passes through unchanged."""
    if resolved:
        match = _RESOLVED_MODEL_RE.match(resolved)
        if match:
            family, major, minor = match.group("family", "major", "minor")
            return f"{family}-{major}.{minor}" if minor else f"{family}-{major}"
    if alias in ALIAS_TO_CANONICAL:
        return ALIAS_TO_CANONICAL[alias]
    return alias


# ---------------------------------------------------------------------------
# Vendor-neutral delegation tiers (`vendor-neutral-delegation-tiers` card).
#
# A card/envelope ``tier:`` names a CAPABILITY POINT, never a vendor. Historic
# values named Claude models (``sonnet``/``opus``), which silently defaulted
# delegation to Claude — a Codex/GPT worker at the same capability point was
# never even a candidate. The canonical vocabulary is now
# ``low | medium | high | frontier``; legacy model-named values alias in, so no
# card-migration wave is needed. The provider choice is made at DISPATCH time
# from available capacity + owner choice — never from the label.
#
# The per-provider equivalence (which model, at which effort) is an OWNER PRIOR
# (the card's 2026-07-17 table) until measured evidence matures. It is display/
# advisory only and is NEVER consulted to auto-pick or auto-route a model — that
# hard boundary is unchanged (see PRIORS_SEED / render_model_rollup docstrings).
# ---------------------------------------------------------------------------

NEUTRAL_TIERS: tuple[str, ...] = ("low", "medium", "high", "frontier")


@dataclass(frozen=True)
class TierPeer:
    """One provider's model at a neutral tier's capability point (owner prior).

    ``effort`` is the effort level that rides WITH the tier for that model, so a
    tier names a capability *point*, not a bare model id (e.g. ``low`` = Luna on
    ``high`` effort). ``None`` leaves the effort to the launcher's default."""

    provider: str            # "claude" | "codex"
    model: str               # canonical model name — joins the datum/prior roster
    effort: str | None = None


# Owner-prior equivalence table, keyed by neutral tier. A model may legitimately
# appear at more than one point (Terra at medium and high, by effort); the
# alias map below resolves such a model to its HIGHEST point so a card tagged
# with that model isn't under-authorized.
TIER_EQUIVALENCE: dict[str, tuple[TierPeer, ...]] = {
    "frontier": (TierPeer("claude", "fable-5"), TierPeer("codex", "gpt-5.6-sol", "high")),
    "high": (TierPeer("claude", "opus-4.8"), TierPeer("codex", "gpt-5.6-terra", "high")),
    "medium": (TierPeer("claude", "sonnet-5"), TierPeer("codex", "gpt-5.6-terra", "medium")),
    "low": (TierPeer("claude", "haiku-4.5"), TierPeer("codex", "gpt-5.6-luna", "high")),
}


def _build_model_tier_map() -> dict[str, str]:
    """Reverse the equivalence table to ``canonical model -> neutral tier``.

    Single source of truth: derived from :data:`TIER_EQUIVALENCE` so the alias
    map can never drift from the rendered mapping. A model at two points takes
    its highest (``frontier`` > ``high`` > ``medium`` > ``low``)."""
    rank = {tier: i for i, tier in enumerate(NEUTRAL_TIERS)}
    out: dict[str, str] = {}
    for tier, peers in TIER_EQUIVALENCE.items():
        for peer in peers:
            if peer.model not in out or rank[tier] > rank[out[peer.model]]:
                out[peer.model] = tier
    return out


_MODEL_TO_TIER: dict[str, str] = _build_model_tier_map()


def normalize_tier(value: str | None) -> str | None:
    """Map a card/envelope ``tier:`` value to its vendor-neutral tier.

    A neutral value (``low|medium|high|frontier``) passes through. A model-named
    value (``sonnet``, ``opus-4.8``, ``gpt-5.6-sol``, …) resolves through its
    canonical model name to the capability point it names. Returns ``None`` for
    an empty or unrecognized value: the vocabulary is a CLOSED set, so an
    unknown tier is a typo to reject, not a new tier to invent."""
    if value is None:
        return None
    v = value.strip().casefold()
    if not v:
        return None
    if v in NEUTRAL_TIERS:
        return v
    canonical = canonical_model_name(v) or v
    return _MODEL_TO_TIER.get(canonical) or _MODEL_TO_TIER.get(v)


# ---------------------------------------------------------------------------
# The datum row
# ---------------------------------------------------------------------------


@dataclass
class Datum:
    """One measured run. Mechanical fields are written automatically at
    launch/completion; the qualitative half (``outcome``/``shape``/``note``) is
    filled by the agent via ``horus datum close``."""

    session_id: str
    model: str | None = None
    # --- mechanical, captured at launch --------------------------------------
    launched_at: str = ""
    project: str | None = None
    account: str | None = None
    effort: str | None = None
    agent: str | None = None
    worker: bool = False
    posture: str | None = None
    environment: str = "host"
    # Horus's durable run id keys the datum; this retains the adapter-native
    # resumable conversation/thread id once it is known.
    agent_session_id: str | None = None
    # --- mechanical, captured at completion ----------------------------------
    completed_at: str | None = None
    runtime_seconds: float | None = None
    exit: str | None = None            # one of EXITS
    returncode: int | None = None
    delivery_expected: bool = False
    delivery_status: str = "unknown"
    dispatch_base_sha: str | None = None
    delivery_branch: str | None = None
    delivery_head_sha: str | None = None
    delivery_pushed_sha: str | None = None
    delivery_pr_number: int | None = None
    delivery_local_changes: bool | None = None
    delivery_continuity_closed: bool | None = None
    delivery_checked_at: str | None = None
    # Captured only where an adapter already surfaces them at completion; left
    # None otherwise (we never block on a field an adapter doesn't expose).
    tokens: int | None = None
    pr_opened: bool | None = None
    ci: str | None = None
    # --- mechanical usage snapshots, best-effort readings only (NEVER a
    # computed delta/cost score — see `capture_usage_snapshot`) --------------
    usage_launch: dict | None = None   # captured at `record_launch`
    usage_close: dict | None = None    # captured at process completion
    # --- qualitative, agent-supplied at review time --------------------------
    outcome: str | None = None         # one of OUTCOMES
    shape: str | None = None           # ambiguity/volume/runtime, agent's words
    note: str | None = None
    closed_at: str | None = None
    # --- agent-supplied supervisor-cost half, set only via `horus datum
    # close`'s optional flags (all None until an agent judges them) ----------
    oversight: str | None = None       # one of OVERSIGHT_LEVELS
    follow_on: int | None = None       # additional worker/PR cycles beyond the primary
    counterfactual: str | None = None  # one of COUNTERFACTUALS
    dividend: str | None = None        # one of DIVIDENDS
    # Provenance so backfilled calibration data reads honestly next to live runs.
    source: str = "run"                # "run" | "backfill"

    @classmethod
    def from_row(cls, row: dict) -> "Datum":
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in row.items() if k in known})


def classify_exit(status: str, *, saw_usage_signal: bool) -> str:
    """Map an adapter run status to a mechanical exit condition.

    Usage-death is distinguished from an ordinary crash so the data can separate
    "the window died under it" from "the work itself failed" — a usage signal
    wins regardless of the raw status.
    """
    if saw_usage_signal:
        return "usage-death"
    return "completed" if status == "exited" else "crashed"


def looks_like_usage_death(error_text: str | None) -> bool:
    """Whether an ERROR event's text looks like a usage/quota wall."""
    return bool(error_text) and bool(_USAGE_DEATH_RE.search(error_text))


# ---------------------------------------------------------------------------
# Mechanical usage snapshots (`usage_launch` / `usage_close`) — readings only,
# NEVER a predicted cost score. Captured once at launch and once at process
# completion. A report may subtract comparable readings after the fact; the
# agent's qualitative judgment still lands separately via the `--dividend` flag.
# ---------------------------------------------------------------------------


def capture_usage_snapshot(
    agent: str | None,
    account: str | None,
    *,
    since: str | None = None,
    persist_cache: bool = True,
) -> dict[str, dict]:
    """Best-effort snapshot of every readable usage surface (claude, codex).

    One entry per target, e.g. ``{"claude": {"pct_5h": 42, "pct_weekly": 37,
    "read_at": "...", "freshness": "fresh"}, "codex": {...}}``. Readings only —
    the agent judges the delta at close, in prose; nothing here computes one.
    A failed/unreadable target renders ``{"freshness": "unavailable", ...}``
    rather than ever blocking the launch or the close it's attached to (wrapped
    in a blanket ``except`` on top of each target's own best-effort read, so an
    unexpected import/environment failure can't escape this function).

    ``account`` is the account for whichever of the two targets actually
    matches ``agent`` (the session's own agent+account); the other target is
    read under its own default account, since a snapshot's purpose is fleet
    capacity visibility, not just the one surface this run happened to use.

    ``since`` (an ISO timestamp — normally the run's own ``launched_at``) lets
    the Codex entry detect the exact failure mode this schema was frozen to
    catch: a cached rate-limit snapshot that predates this run entirely (Codex
    only refreshes its usage cache when Codex itself runs a turn) reads
    ``stale``, not ``fresh``, even though the read itself succeeded.

    ``persist_cache=False`` keeps projections such as resume preflight strictly
    read-only: Claude is read live without updating the shared usage cache. Datum
    capture keeps the default ``True`` so its existing hot-path cache behavior is
    unchanged.
    """
    try:
        return {
            "claude": _claude_usage_entry(
                account if agent == "claude" else None,
                persist_cache=persist_cache,
            ),
            "codex": _codex_usage_entry(account if agent == "codex" else None, since=since),
        }
    except Exception:  # noqa: BLE001 (best-effort: never blocks the launch/close it's attached to)
        read_at = _now_iso()
        return {
            "claude": {"freshness": "unavailable", "read_at": read_at},
            "codex": {"freshness": "unavailable", "read_at": read_at},
        }


def _claude_usage_entry(account: str | None, *, persist_cache: bool = True) -> dict:
    from horus import usage_snapshot

    read_at = _now_iso()
    try:
        snap = (
            usage_snapshot.cached_usage("claude", account)
            if persist_cache
            else usage_snapshot._read_live("claude", account, timeout=usage_snapshot.FETCH_TIMEOUT)
        )
    except Exception:  # noqa: BLE001 (best-effort read; any failure -> unavailable)
        snap = None
    if snap is None or (snap.percent is None and snap.weekly_percent is None):
        return {"freshness": "unavailable", "read_at": read_at}
    # Claude's read is a live OAuth /usage call (or a still-fresh short-TTL cache
    # of one) — it counts as "fresh" at read time by construction.
    entry: dict = {"read_at": read_at, "freshness": "fresh"}
    if snap.percent is not None:
        entry["pct_5h"] = snap.percent
        entry["resets_5h"] = snap.resets_at
    if snap.weekly_percent is not None:
        entry["pct_weekly"] = snap.weekly_percent
        entry["resets_weekly"] = snap.weekly_resets_at
    return entry


def _codex_usage_entry(account: str | None, *, since: str | None) -> dict:
    from horus import codex_usage

    read_at = _now_iso()
    try:
        home = None
        if account:
            configured = config.load_account_codex_homes().get(account)
            home = Path(configured) if configured else None
        report = codex_usage.latest_account_usage(home=home)
    except Exception:  # noqa: BLE001 (best-effort read; any failure -> unavailable)
        report = None
    if report is None:
        return {"freshness": "unavailable", "read_at": read_at}
    entry: dict = {"read_at": read_at, "pct_context": report.context_percent}
    if report.primary_percent is not None:
        entry["pct_5h"] = report.primary_percent
        entry["resets_5h"] = getattr(report, "primary_resets_at", None)
    secondary_percent = getattr(report, "secondary_percent", None)
    if secondary_percent is not None:
        entry["pct_weekly"] = secondary_percent
        entry["resets_weekly"] = getattr(report, "secondary_resets_at", None)
    now = time.time()
    reset_expired = report.primary_resets_at is not None and report.primary_resets_at <= now
    predates_run = False
    if since:
        report_epoch = codex_usage._timestamp_key(report.timestamp)
        since_epoch = codex_usage._timestamp_key(since)
        predates_run = bool(report_epoch) and bool(since_epoch) and report_epoch < since_epoch
    entry["freshness"] = "stale" if (reset_expired or predates_run) else "fresh"
    return entry


def _iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if stamp.tzinfo is None:
        stamp = stamp.astimezone()
    return stamp.astimezone(timezone.utc)


def _registry_positive_completion(session_id: str) -> tuple[datetime, str, int | None] | None:
    """``(effective_end, exit, returncode)`` from POSITIVE terminal registry/
    run-event evidence only — a real reconciled ``exited``/``failed`` result.

    A dead PID, an absent row, or a merely ``stale`` row (dead PID, no result)
    is never treated as proof of the worker's outcome (see
    ``stale-datum-usage-overlap-reconciliation``); those cases return
    ``None`` and the caller keeps the interval open/confounded instead of
    fabricating a completion. Deferred import: :mod:`horus.registry` imports
    this module, so a module-level import here would cycle.
    """
    try:
        from horus import registry as registry_module

        row = registry_module.Registry.default().get(session_id)
    except Exception:  # noqa: BLE001 (best-effort: overlap classification must never raise)
        return None
    if row is None or row.status not in ("exited", "failed"):
        return None
    end = _iso_datetime(row.updated_at)
    if end is None:
        return None
    return end, classify_exit(row.status, saw_usage_signal=False), row.returncode


def _registry_genuinely_running(session_id: str) -> bool:
    """Whether the registry independently confirms this session is still live
    (not merely a PID that hasn't been checked)."""
    try:
        from horus import registry as registry_module

        row = registry_module.Registry.default().get(session_id)
    except Exception:  # noqa: BLE001
        return False
    return row is not None and row.status == "running"


def _effective_interval(row: Datum, *, now: datetime | None = None) -> tuple[datetime | None, datetime, bool]:
    """``(start, effective_end, bounded)`` for one datum.

    ``bounded`` is True when ``end`` reflects real evidence — the datum's own
    mechanical completion, or positive terminal registry/run-event evidence —
    rather than "still open as of now". An unbounded end keeps confounding
    overlap checks (the peer is genuinely live, or the evidence is missing/
    ambiguous) instead of ever being reported as resolved.
    """
    start = _iso_datetime(row.launched_at)
    end = _iso_datetime(row.completed_at)
    if end is not None:
        return start, end, True
    positive = _registry_positive_completion(row.session_id)
    if positive is not None:
        return start, positive[0], True
    return start, now or datetime.now(timezone.utc), False


def _overlap_peers(datum: Datum, peers: list[Datum]) -> list[dict]:
    """Tracked workers on the same account whose effective interval overlaps
    ``datum``'s, each named with its own run id and the interval actually used
    for the check — so a usage report can say exactly who overlapped instead
    of only "another tracked worker overlapped" (see
    ``stale-datum-usage-overlap-reconciliation``).
    """
    start, end, _ = _effective_interval(datum)
    if start is None:
        return []
    overlaps: list[dict] = []
    for peer in peers:
        if peer.session_id == datum.session_id or not peer.worker:
            continue
        if peer.agent != datum.agent or peer.account != datum.account:
            continue
        peer_start, peer_end, peer_bounded = _effective_interval(peer)
        if peer_start is None:
            continue
        if start <= peer_end and peer_start <= end:
            overlaps.append({
                "session_id": peer.session_id,
                "start": peer.launched_at,
                "end": peer_end.isoformat(timespec="seconds"),
                "bounded": peer_bounded,
            })
    return overlaps


def usage_accounting(datum: Datum, peers: list[Datum] | None = None) -> dict:
    """Classify stored start/end usage evidence without estimating future cost.

    A percentage-point delta is shown only for an explicit isolated account,
    fresh readings, the same provider reset window, and no overlapping tracked
    worker on that account. Ambient/default accounts are conservatively labelled
    shared because supervisor or unrelated activity cannot be separated.
    """
    target = datum.agent or ""
    start = (datum.usage_launch or {}).get(target)
    end = (datum.usage_close or {}).get(target)
    result = {"status": "unknown", "start": start, "end": end, "deltas": {}}
    if not isinstance(start, dict) or not isinstance(end, dict):
        result["detail"] = "start/end usage unavailable"
        return result
    if datum.account is None:
        result["status"] = "shared-account/confounded"
        result["detail"] = "ambient/default account may include supervisor or unrelated activity"
        return result
    overlaps = _overlap_peers(datum, peers or [])
    if overlaps:
        result["status"] = "concurrent/confounded"
        result["overlap_peers"] = overlaps
        peer_desc = ", ".join(f"{o['session_id']} [{o['start']}..{o['end']}]" for o in overlaps)
        result["detail"] = f"overlapping tracked worker(s): {peer_desc}"
        return result
    if start.get("freshness") != "fresh" or end.get("freshness") != "fresh":
        result["detail"] = "start/end readings are not both fresh"
        return result

    deltas: dict[str, float] = {}
    for label, pct_key, reset_key in (
        ("5h", "pct_5h", "resets_5h"),
        ("weekly", "pct_weekly", "resets_weekly"),
    ):
        before, after = start.get(pct_key), end.get(pct_key)
        start_reset, end_reset = start.get(reset_key), end.get(reset_key)
        if not isinstance(before, int | float) or not isinstance(after, int | float):
            continue
        if start_reset is None or start_reset != end_reset:
            continue
        deltas[label] = round(float(after) - float(before), 1)
    if not deltas:
        result["detail"] = "no fresh comparable provider window"
        return result
    result["status"] = "observed"
    result["deltas"] = deltas
    result["detail"] = "isolated account; no overlapping tracked worker"
    return result


def worker_breakdown(rows: list[Datum]) -> list[dict]:
    """Render-ready per-attempt worker actuals, grouped by native session id."""
    workers = sorted(
        (row for row in rows if row.worker),
        key=lambda row: (row.launched_at, row.session_id),
    )
    groups: dict[tuple[str | None, str | None, str], list[Datum]] = {}
    for row in workers:
        native = row.agent_session_id or row.session_id
        groups.setdefault((row.agent, row.account, native), []).append(row)

    breakdown: list[dict] = []
    for row in workers:
        native = row.agent_session_id or row.session_id
        group = groups[(row.agent, row.account, native)]
        breakdown.append({
            "run_id": row.session_id,
            "agent_session_id": row.agent_session_id,
            "agent": row.agent,
            "model": row.model,
            "account": row.account,
            "effort": row.effort,
            "runtime_seconds": row.runtime_seconds,
            "attempt": group.index(row) + 1,
            "attempts": len(group),
            "outcome": row.outcome,
            "exit": row.exit,
            "delivery_status": row.delivery_status,
            "launched_at": row.launched_at,
            "completed_at": row.completed_at,
            "usage": usage_accounting(row, workers),
        })
    return breakdown


def _runtime_label(seconds: float | None) -> str:
    if seconds is None:
        return "unknown"
    total = max(0, round(seconds))
    minutes, secs = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{secs:02d}s"
    return f"{minutes}m{secs:02d}s"


def _usage_reading_label(entry: object) -> str:
    if not isinstance(entry, dict):
        return "unavailable"
    parts = []
    if isinstance(entry.get("pct_5h"), int | float):
        parts.append(f"5h={entry['pct_5h']:g}%")
    if isinstance(entry.get("pct_weekly"), int | float):
        parts.append(f"weekly={entry['pct_weekly']:g}%")
    if not parts:
        return str(entry.get("freshness", "unavailable"))
    return "/".join(parts) + f"[{entry.get('freshness', 'unknown')}]"


def render_worker_breakdown(rows: list[dict]) -> str:
    if not rows:
        return "No worker runs recorded.\n"
    lines = ["Worker actuals (observed readings only; never an estimate):"]
    for row in rows:
        usage = row["usage"]
        if usage["status"] == "observed":
            deltas = ", ".join(f"{window} {delta:+g}pp" for window, delta in usage["deltas"].items())
            usage_label = f"observed {deltas}"
        else:
            usage_label = f"{usage['status']} ({usage.get('detail', 'no detail')})"
        usage_label += (
            f" start={_usage_reading_label(usage.get('start'))}"
            f" end={_usage_reading_label(usage.get('end'))}"
        )
        lines.append(
            f"  {row['run_id'][:8]} {row['agent'] or '-'} model={row['model'] or '-'} "
            f"account={row['account'] or 'default'} effort={row['effort'] or 'default'} "
            f"runtime={_runtime_label(row['runtime_seconds'])} "
            f"attempt={row['attempt']}/{row['attempts']} "
            f"outcome={row['outcome'] or row['exit'] or 'open'} usage={usage_label}"
        )
    return "\n".join(lines) + "\n"


def render_unresolved_legacy_runs(rows: list[Datum]) -> str:
    """Explicit owner/supervisor remediation surface for stuck legacy runs —
    never printed as resolved, never auto-closed."""
    if not rows:
        return ""
    lines = [
        "Unresolved legacy run(s) — no terminal evidence and no confirmed-live "
        "process; each keeps confounding overlap checks until an owner/supervisor "
        "resolves it (`horus datum close <id> --outcome void`, or inspect the "
        "registry row by hand):"
    ]
    for row in rows:
        lines.append(f"  {row.session_id[:8]} launched={row.launched_at} account={row.account or 'default'}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Backfill — the known hand-written datums, so the roll-up renders immediately
# ---------------------------------------------------------------------------


def _backfill() -> dict[str, dict]:
    """Seed the store with the fleet's existing known datums (from session-note
    prose, 2026-07): Sonnet 5 = 10 clean scoped-impl datums; Opus 4.8 / Fable 5 /
    gpt-5.6 / gpt-5.5 = ~1 clean each; Haiku 4.5 = 0 (unproven). Deterministic
    ids + timestamps so tests and re-seeds are reproducible."""
    rows: dict[str, dict] = {}
    seed: list[tuple[str, int]] = [
        ("sonnet-5", 10),
        ("opus-4.8", 1),
        ("fable-5", 1),
        ("gpt-5.6", 1),
        ("gpt-5.5", 1),
    ]
    n = 0
    for model, count in seed:
        for i in range(count):
            n += 1
            sid = f"backfill-{model}-{i + 1:02d}"
            rows[sid] = asdict(
                Datum(
                    session_id=sid,
                    model=model,
                    launched_at=f"2026-07-01T00:{n:02d}:00+00:00",
                    exit="completed",
                    outcome="clean",
                    shape="backfilled from session-note calibration prose",
                    note="seed datum (2026-07); pre-dates automatic capture",
                    closed_at=f"2026-07-01T00:{n:02d}:00+00:00",
                    source="backfill",
                )
            )
    return rows


# ---------------------------------------------------------------------------
# The store — mirrors registry.json (single JSON keyed by session id)
# ---------------------------------------------------------------------------


class DatumStore:
    """Fleet-global measured-datum store at ``~/.horus/datums.json``.

    Model calibration is not project-specific, so — like the registry — it lives
    under ``~/.horus`` and is machine-local. Every write is best-effort: recording
    a datum must never be able to break the run it is measuring.
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    @classmethod
    def default(cls) -> "DatumStore":
        return cls(datums_path())

    # --- persistence ----------------------------------------------------------

    def _load(self) -> dict[str, dict]:
        """Rows keyed by session id. When the file is absent the backfill is
        returned as the virtual default; it becomes concrete on the first write."""
        if not self.path.exists():
            return _backfill()
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        rows = data.get("datums")
        return rows if isinstance(rows, dict) else {}

    def _save(self, rows: dict[str, dict]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps({"datums": rows}, indent=2) + "\n", encoding="utf-8")

    # --- reads ----------------------------------------------------------------

    def all(self) -> list[Datum]:
        return [Datum.from_row(row) for row in self._load().values()]

    def get(self, session_id: str) -> Datum | None:
        row = self._load().get(session_id)
        return Datum.from_row(row) if row else None

    def find(self, prefix: str) -> list[Datum]:
        """Datums whose session id starts with ``prefix`` (git-short-hash style)."""
        return [Datum.from_row(row) for sid, row in self._load().items() if sid.startswith(prefix)]

    def unresolved_legacy_runs(self, *, stale_after_hours: float = 24.0, now: datetime | None = None) -> list[Datum]:
        """Worker datums missing ``completed_at`` with no positive terminal
        evidence and no confirmed-live process backing them, old enough that
        they are not simply still in flight.

        These are exactly the rows a mere dead PID or absent registry entry
        must never silently resolve (see
        ``stale-datum-usage-overlap-reconciliation``) — they need an explicit
        owner/supervisor call (e.g. ``horus datum close <id> --outcome void``,
        or inspecting the registry row by hand), never an automatic close.
        """
        moment = now or datetime.now(timezone.utc)
        unresolved: list[Datum] = []
        for datum in self.all():
            if not datum.worker or datum.completed_at:
                continue
            launched = _iso_datetime(datum.launched_at)
            if launched is None or (moment - launched) < timedelta(hours=stale_after_hours):
                continue
            if _registry_positive_completion(datum.session_id) is not None:
                continue  # reconcile_missing_completions would resolve this one
            if _registry_genuinely_running(datum.session_id):
                continue  # genuinely live — confounds attribution, but not "unresolved"
            unresolved.append(datum)
        return unresolved

    # --- writes (best-effort: swallow I/O so measurement never breaks a run) --

    def reconcile_missing_completions(self) -> list[Datum]:
        """Backfill ``completed_at`` for worker datums that never got a
        mechanical completion, using ONLY positive terminal registry/run-event
        evidence — never a dead PID or an absent/stale registry row alone.

        A backfilled row gets a real bounded interval, so it stops confounding
        every later overlap check on the same account forever. Rows with no
        positive evidence (genuinely live, or merely ambiguous) are left
        untouched here; ``unresolved_legacy_runs`` surfaces the ambiguous ones
        for explicit remediation instead of a silent auto-close.
        """
        try:
            rows = self._load()
        except (OSError, json.JSONDecodeError):
            return []
        changed: list[Datum] = []
        for row in rows.values():
            if not row.get("worker") or row.get("completed_at"):
                continue
            session_id = str(row.get("session_id", ""))
            positive = _registry_positive_completion(session_id)
            if positive is None:
                continue
            end, exit_value, returncode = positive
            row["completed_at"] = end.isoformat(timespec="seconds")
            row["exit"] = exit_value
            if returncode is not None:
                row["returncode"] = returncode
            changed.append(Datum.from_row(row))
        if changed:
            try:
                self._save(rows)
            except OSError:
                return []
        return changed

    def record_launch(self, datum: Datum) -> None:
        """Write the mechanical launch row. An existing row (e.g. a resume of the
        same session) keeps its qualitative half but refreshes launch fields."""
        try:
            rows = self._load()
            existing = rows.get(datum.session_id, {})
            row = asdict(datum)
            for carried in ("outcome", "shape", "note", "closed_at"):
                if existing.get(carried) is not None:
                    row[carried] = existing[carried]
            rows[datum.session_id] = row
            self._save(rows)
        except (OSError, TypeError, ValueError):
            pass

    def record_completion(
        self,
        session_id: str,
        *,
        exit: str,
        runtime_seconds: float | None,
        returncode: int | None,
        tokens: int | None = None,
        pr_opened: bool | None = None,
        ci: str | None = None,
        delivery_status: str = "unknown",
        delivery_expected: bool = False,
        dispatch_base_sha: str | None = None,
        delivery_branch: str | None = None,
        delivery_head_sha: str | None = None,
        delivery_pushed_sha: str | None = None,
        delivery_pr_number: int | None = None,
        delivery_local_changes: bool | None = None,
        delivery_continuity_closed: bool | None = None,
        delivery_checked_at: str | None = None,
    ) -> None:
        try:
            rows = self._load()
            row = rows.get(session_id)
            if row is None:
                return
            row["completed_at"] = _now_iso()
            row["exit"] = exit
            row["runtime_seconds"] = runtime_seconds
            row["returncode"] = returncode
            row["delivery_expected"] = delivery_expected
            row["delivery_status"] = delivery_status
            row["dispatch_base_sha"] = dispatch_base_sha
            row["delivery_branch"] = delivery_branch
            row["delivery_head_sha"] = delivery_head_sha
            row["delivery_pushed_sha"] = delivery_pushed_sha
            row["delivery_pr_number"] = delivery_pr_number
            row["delivery_local_changes"] = delivery_local_changes
            row["delivery_continuity_closed"] = delivery_continuity_closed
            row["delivery_checked_at"] = delivery_checked_at
            row["usage_close"] = capture_usage_snapshot(
                row.get("agent"), row.get("account"), since=row.get("launched_at"),
                persist_cache=False,
            )
            if tokens is not None:
                row["tokens"] = tokens
            if pr_opened is not None:
                row["pr_opened"] = pr_opened
            if ci is not None:
                row["ci"] = ci
            self._save(rows)
        except (OSError, TypeError, ValueError):
            pass

    def close(
        self,
        prefix: str,
        *,
        outcome: str,
        shape: str | None,
        note: str | None,
        oversight: str | None = None,
        follow_on: int | None = None,
        counterfactual: str | None = None,
        dividend: str | None = None,
    ) -> Datum:
        """Attach the agent-supplied qualitative + supervisor-cost half to a datum,
        resolved by id prefix. Raises ``LookupError`` for no/ambiguous match,
        ``ValueError`` for an out-of-vocabulary outcome/oversight/counterfactual/
        dividend or a negative ``follow_on``. This is the ONLY path that sets
        these fields — never inferred, never auto-scored (the 2026-07-14 frozen
        cost-envelope schema keeps the same hard boundary as ``outcome``).

        Legacy datums that predate completion capture get a best-effort
        ``usage_close`` snapshot here. New runs already carry their mechanical
        end reading before this qualitative review happens."""
        if outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {', '.join(OUTCOMES)} (got {outcome!r})")
        if oversight is not None and oversight not in OVERSIGHT_LEVELS:
            raise ValueError(f"oversight must be one of {', '.join(OVERSIGHT_LEVELS)} (got {oversight!r})")
        if counterfactual is not None and counterfactual not in COUNTERFACTUALS:
            raise ValueError(f"counterfactual must be one of {', '.join(COUNTERFACTUALS)} (got {counterfactual!r})")
        if dividend is not None and dividend not in DIVIDENDS:
            raise ValueError(f"dividend must be one of {', '.join(DIVIDENDS)} (got {dividend!r})")
        if follow_on is not None and follow_on < 0:
            raise ValueError(f"follow-on must be >= 0 (got {follow_on!r})")
        rows = self._load()
        matches = [sid for sid in rows if sid.startswith(prefix)]
        if not matches:
            raise LookupError(f"No datum matching {prefix!r}. Run a session first, or check `horus sessions`.")
        if len(matches) > 1:
            raise LookupError(f"{prefix!r} is ambiguous ({len(matches)} datums); use more of the id.")
        row = rows[matches[0]]
        row["outcome"] = outcome
        row["shape"] = shape
        row["note"] = note
        row["closed_at"] = _now_iso()
        if oversight is not None:
            row["oversight"] = oversight
        if follow_on is not None:
            row["follow_on"] = follow_on
        if counterfactual is not None:
            row["counterfactual"] = counterfactual
        if dividend is not None:
            row["dividend"] = dividend
        if row.get("usage_close") is None:
            try:
                row["usage_close"] = capture_usage_snapshot(
                    row.get("agent"), row.get("account"), since=row.get("launched_at")
                )
            except Exception:  # noqa: BLE001 (best-effort: never blocks a close)
                pass
        self._save(rows)
        return Datum.from_row(row)

    def migrate_names(self) -> dict[str, int]:
        """One-time, idempotent rename of dispatch aliases already captured
        in ``datums.json`` (including bare Claude names and generic ``gpt-5.6``)
        to their canonical
        versioned name, via :data:`ALIAS_TO_CANONICAL`. Every other field on the
        row is preserved untouched; only the ``model`` value changes, so rows
        naturally merge under the canonical name in the roll-up (grouping is by
        that field, not a separate merge step).

        Returns ``{bare_alias: count_renamed}``. A record already on its
        canonical name has no entry in :data:`ALIAS_TO_CANONICAL` as a *key*
        (only as a value), so it is left untouched — re-running finds nothing
        left to rename and returns ``{}`` without writing the file at all,
        making a repeat run a true no-op, byte-for-byte."""
        if not self.path.exists():
            return {}
        rows = self._load()
        renamed: dict[str, int] = {}
        changed = False
        for row in rows.values():
            model = row.get("model")
            canonical = ALIAS_TO_CANONICAL.get(model) if model else None
            if canonical and canonical != model:
                row["model"] = canonical
                renamed[model] = renamed.get(model, 0) + 1
                changed = True
        if changed:
            self._save(rows)
        return renamed


# ---------------------------------------------------------------------------
# Owner priors (read-only here; seeded once, then hand-edited)
# ---------------------------------------------------------------------------

# Shipped seed — written to ~/.horus/capabilities.toml on first read if absent,
# then owned by the human. Tier tags + the one real owner flag (gpt-5.6) per the
# fleet's current calibration.
PRIORS_SEED = """\
# Owner priors for model calibration — HAND-EDITED, fleet-global.
#
# The qualitative counterpart to the measured datums in datums.json: per-model
# constraints and cautions that shape HOW to use a model, independent of (and
# never overwritten by) any measured outcome. `horus capabilities --models` reads
# this alongside the datums to render a data-only roll-up.
#
# HARD BOUNDARY: advisory data the agent reads — never a router, policy, or spend
# engine. Nothing consumes it to auto-pick or auto-route a model.
#
# Edit freely; add models as the fleet gains experience with them.
#
# Optional price-for-capability/lifecycle fields (all back-compatible — omit entirely and
# a model renders exactly as before). Filled in by a SEPARATE agent web-research
# refresh pass (see the `older-models-in-roster` backlog card), never hand-typed
# guesses and never fetched by this CLI:
#   price_in = 3.00           # USD per Mtok, input
#   price_out = 15.00         # USD per Mtok, output
#   capability_note = "..."   # what it's good for — can run long; full text
#                             # only ever shown in --stdout JSON / --verbose
#   capability_summary = "scoped-impl lead"  # a few words for the concise
#                             # table's CAPABILITY column; omit to fall back to
#                             # a word-safe truncation of capability_note
#   researched_at = 2026-07-10  # date this price/note was last checked; a
#                                # display command warns (non-blocking) when the
#                                # freshest researched_at across all models is
#                                # more than 14 days old or absent entirely
#   available = true             # current provider availability, when sourced
#   retires_at = 2026-08-31      # explicit provider retirement date only

schema_version = 1

[models."opus-4.8"]
tier = "design / ambiguity / verify gate"

[models."sonnet-5"]
tier = "scoped-impl lead"

[models."haiku-4.5"]
tier = "mechanical (unproven)"

[models."fable-5"]
tier = "frontier (early)"

[models."gpt-5.6-sol"]
tier = "frontier codex"
strength = "frontier codex, self-verifies, PR-disciplined"
caution = "token-hungry — needs tightly-scoped task + explicit stopping point + budget headroom"
guard = "do not dispatch near usage ceiling"
price_in = 5.0
price_out = 30.0
capability_summary = "flagship frontier codex"
capability_note = "OpenAI flagship GPT-5.6 variant; the generic gpt-5.6 name aliases Sol"
researched_at = 2026-07-14
available = true

[models."gpt-5.6-terra"]
tier = "value codex (early)"
price_in = 2.5
price_out = 15.0
capability_summary = "balanced value variant"
capability_note = "OpenAI balanced price/performance GPT-5.6 variant; retain early tier until measured evidence matures"
researched_at = 2026-07-14
available = true

[models."gpt-5.6-luna"]
tier = "high-volume codex (unproven)"
price_in = 1.0
price_out = 6.0
capability_summary = "cost-sensitive high volume"
capability_note = "OpenAI cost-sensitive, high-volume GPT-5.6 variant; unproven in local measured datums"
researched_at = 2026-07-14
available = true

[models."gpt-5.5"]
tier = "codex (early)"
price_in = 5.0
price_out = 30.0
capability_summary = "retained for measured comparison"
capability_note = "Prior generation retained only to keep its measured datum visible; price-dominated by newer Terra"
researched_at = 2026-07-14
"""


def load_priors(path: Path | None = None) -> dict[str, dict]:
    """Return the ``[models]`` table of owner priors, keyed by model.

    Seeds ``~/.horus/capabilities.toml`` from :data:`PRIORS_SEED` on first read
    (best-effort — a read-only home just falls back to the seed in memory)."""
    path = path or priors_path()
    if not path.exists():
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(PRIORS_SEED, encoding="utf-8")
        except OSError:
            return _parse_priors(PRIORS_SEED)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return _parse_priors(PRIORS_SEED)
    return _parse_priors(text)


def _parse_priors(text: str) -> dict[str, dict]:
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError:
        return {}
    models = data.get("models")
    return models if isinstance(models, dict) else {}


# ---------------------------------------------------------------------------
# Roll-up (pure: datums + priors in, data out — no pick, no suggestion)
# ---------------------------------------------------------------------------


@dataclass
class ModelRollup:
    model: str
    tier: str | None = None
    strength: str | None = None
    caution: str | None = None
    guard: str | None = None
    total_datums: int = 0
    closed_datums: int = 0
    quality_datums: int = 0
    clean_count: int = 0
    died_count: int = 0
    void_count: int = 0
    last_outcomes: list[str] = field(default_factory=list)
    # Supervisor-cost glance (2026-07-14 frozen schema): counts/median from
    # datums that carry the agent-supplied `--dividend`/`--oversight` close
    # flags. Zero on a model with none of that data yet — the renderer treats
    # zero-and-no-median as ABSENT (omitted), never shown as a literal 0.
    dividend_positive: int = 0
    dividend_neutral: int = 0
    dividend_negative: int = 0
    oversight_median: str | None = None
    # Price-for-capability fields (all optional, owner-prior, agent-researched —
    # see PRIORS_SEED docstring and the `older-models-in-roster` backlog card).
    price_in: float | None = None       # USD per Mtok, input
    price_out: float | None = None      # USD per Mtok, output
    capability_note: str | None = None  # short free-text: what it's good for
    capability_summary: str | None = None  # a few words, for the concise table
    researched_at: str | None = None    # ISO date (YYYY-MM-DD) last checked
    available: bool | None = None       # explicit owner-prior availability state
    retires_at: str | None = None       # explicit provider retirement date
    lifecycle: str | None = None        # derived display marker; never routing input


def _prior_date_str(value: object) -> str | None:
    """Normalize an owner prior's date-like value to an ISO date string.

    TOML lets a hand-editor write an unquoted date (``2026-07-10``), which
    ``tomllib`` parses as a native ``date``/``datetime`` — accept that form
    alongside a plain quoted string so either style round-trips."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


LIFECYCLE_SOON_DAYS = 30


def _lifecycle_marker(
    available: bool | None,
    retires_at: str | None,
    *,
    today: date | None = None,
) -> str | None:
    """Derive a display-only lifecycle marker from explicit owner provenance."""
    today = today or datetime.now(timezone.utc).date()
    retirement: date | None = None
    if retires_at:
        try:
            retirement = date.fromisoformat(retires_at[:10])
        except ValueError:
            pass
    if available is False:
        return f"retired {retires_at}" if retires_at else "retired"
    if retirement is not None:
        if retirement <= today:
            return f"retired {retires_at}"
        if retirement <= today + timedelta(days=LIFECYCLE_SOON_DAYS):
            return f"retires soon {retires_at}"
        return f"retires {retires_at}"
    if retires_at:
        return f"retires {retires_at}"
    if available is True:
        return "available"
    return None


# Ordinal ranking for a deterministic "median" oversight bucket per model —
# not a judgment, just a middle-of-the-sorted-list pick (lower median on an
# even count, so it never needs to invent a label between two rungs).
_OVERSIGHT_RANK: dict[str, int] = {level: i + 1 for i, level in enumerate(OVERSIGHT_LEVELS)}
_OVERSIGHT_BY_RANK: dict[int, str] = {rank: level for level, rank in _OVERSIGHT_RANK.items()}


def _oversight_median(values: list[str]) -> str | None:
    ranks = sorted(_OVERSIGHT_RANK[v] for v in values if v in _OVERSIGHT_RANK)
    if not ranks:
        return None
    mid = (len(ranks) - 1) // 2
    return _OVERSIGHT_BY_RANK[ranks[mid]]


def build_model_rollup(
    datums: list[Datum],
    priors: dict[str, dict],
    *,
    today: date | None = None,
) -> list[ModelRollup]:
    """One row per model across BOTH layers (union of priors + measured models).

    Priors supply tier/strength/caution/guard; datums supply the measured counts
    and the most-recent outcomes. Deterministic ordering: most clean datums first,
    then name — so the proven leads sort to the top without any ranking judgment
    being encoded. Purely descriptive; it recommends nothing."""
    by_model: dict[str, list[Datum]] = {}
    for d in datums:
        if d.model:
            model = canonical_model_name(d.model) or d.model
            by_model.setdefault(model, []).append(d)

    # Legacy alias priors provide a compatibility base, while an explicitly
    # authored canonical row wins field-by-field when both are present.
    canonical_priors: dict[str, dict] = {}
    for model, prior in priors.items():
        canonical = canonical_model_name(model) or model
        if canonical != model:
            canonical_priors.setdefault(canonical, {}).update(prior)
    for model, prior in priors.items():
        canonical = canonical_model_name(model) or model
        if canonical == model:
            canonical_priors.setdefault(canonical, {}).update(prior)

    rollups: list[ModelRollup] = []
    for model in sorted(set(canonical_priors) | set(by_model)):
        prior = canonical_priors.get(model, {})
        rows = sorted(by_model.get(model, []), key=lambda d: d.launched_at)
        closed = [d for d in rows if d.outcome]
        quality = [d for d in closed if d.outcome in QUALITY_OUTCOMES]
        last = [d.outcome for d in quality][-LAST_N:]
        dividends = [d.dividend for d in rows if d.dividend]
        oversights = [d.oversight for d in rows if d.oversight]
        available = prior.get("available") if isinstance(prior.get("available"), bool) else None
        retires_at = _prior_date_str(prior.get("retires_at"))
        rollups.append(
            ModelRollup(
                model=model,
                tier=prior.get("tier"),
                strength=prior.get("strength"),
                caution=prior.get("caution"),
                guard=prior.get("guard"),
                total_datums=len(rows),
                closed_datums=len(closed),
                quality_datums=len(quality),
                clean_count=sum(1 for d in quality if d.outcome == "clean"),
                died_count=sum(1 for d in closed if d.outcome == "died"),
                void_count=sum(1 for d in closed if d.outcome == "void"),
                last_outcomes=list(reversed(last)),  # most-recent first
                price_in=prior.get("price_in"),
                price_out=prior.get("price_out"),
                capability_note=prior.get("capability_note"),
                capability_summary=prior.get("capability_summary"),
                researched_at=_prior_date_str(prior.get("researched_at")),
                available=available,
                retires_at=retires_at,
                lifecycle=_lifecycle_marker(available, retires_at, today=today),
                dividend_positive=sum(1 for v in dividends if v == "positive"),
                dividend_neutral=sum(1 for v in dividends if v == "neutral"),
                dividend_negative=sum(1 for v in dividends if v == "negative"),
                oversight_median=_oversight_median(oversights),
            )
        )
    rollups.sort(key=lambda r: (-r.clean_count, r.model))
    return rollups


# Table columns for the tier ladder, shared by `render_model_rollup` and
# `render_delegation_matrix`. The CONCISE set (default — a CLI glance) is
# model/tier/price/datums/capability; the FULL set (--verbose/--full, power
# users) restores LAST (per-run outcome history) and RESEARCHED. LAST is
# insider delegation-quality judgment (clean/nudged/bounced), not
# CI/exit status — it needs a legend to read, so it's opt-in, never dropped
# from `--stdout` JSON. Free-text strength/caution/guard flags don't fit a
# column (they'd blow out alignment) so they render as a separate Notes
# section below the table instead of being dropped, in either mode.
_CONCISE_COLUMNS: tuple[str, ...] = ("model", "tier", "price", "datums", "capability")
_FULL_COLUMNS: tuple[str, ...] = ("model", "tier", "datums", "last", "price", "capability", "researched")
_TABLE_HEADERS: dict[str, str] = {
    "model": "MODEL",
    "tier": "TIER",
    "datums": "DATUMS",
    "last": "LAST",
    "price": "PRICE",
    "capability": "CAPABILITY",
    "researched": "RESEARCHED",
}
_CAPABILITY_NOTE_MAX = 60  # --verbose/--full capability column (fuller, still bounded)
_CAPABILITY_SUMMARY_MAX = 40  # concise capability column — a few words, not a paragraph


def _table_row(r: ModelRollup, *, verbose: bool) -> dict[str, str]:
    datum_bits = [f"{r.clean_count}/{r.quality_datums} clean"]
    if r.died_count:
        datum_bits.append(f"{r.died_count} died")
    if r.void_count:
        datum_bits.append(f"{r.void_count} void")
    return {
        "model": r.model,
        "tier": r.tier or "-",
        "datums": " · ".join(datum_bits),
        "last": " ".join(r.last_outcomes) if r.last_outcomes else "-",
        "price": _format_price(r),
        "capability": _capability_cell(r, verbose=verbose),
        "researched": r.researched_at or "-",
    }


def _capability_cell(r: ModelRollup, *, verbose: bool) -> str:
    """CAPABILITY column text. ``--verbose``/``--full`` shows a fuller (still
    bounded) slice of `capability_note`; the concise default shows a dedicated
    `capability_summary` when the owner authored one, else a word-safe
    truncation of `capability_note` — a few words, never a mid-word chop. The
    full text is always available in ``--stdout`` JSON regardless of mode."""
    if verbose:
        return _truncate(r.capability_note, _CAPABILITY_NOTE_MAX) if r.capability_note else "-"
    if r.capability_summary:
        return r.capability_summary
    if r.capability_note:
        return _word_truncate(r.capability_note, _CAPABILITY_SUMMARY_MAX)
    return "-"


def _truncate(text: str, width: int) -> str:
    return text if len(text) <= width else text[: width - 1].rstrip() + "…"


def _word_truncate(text: str, width: int) -> str:
    """Truncate at a word boundary (never mid-word) for a short "a few words"
    glance, unlike `_truncate`'s mid-word char cut used for the fuller view."""
    if len(text) <= width:
        return text
    cut = text[:width]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(",;.:—- ") + "…"


def _format_price(r: ModelRollup) -> str:
    """``$in/$out`` per Mtok, compact for a table column (``-`` for an unset side,
    or the whole cell when neither is set)."""
    if r.price_in is None and r.price_out is None:
        return "-"
    p_in = f"${r.price_in:g}" if r.price_in is not None else "-"
    p_out = f"${r.price_out:g}" if r.price_out is not None else "-"
    return f"{p_in}/{p_out}"


def render_tier_table(rollups: list[ModelRollup], *, verbose: bool = False) -> list[str]:
    """Aligned tier-ladder table lines (no title/sources header — callers add
    their own framing). Returns a placeholder line when there are no rollups.

    Concise by default (model/tier/price/datums/capability, for a CLI glance);
    pass ``verbose=True`` to restore LAST and RESEARCHED for power users."""
    if not rollups:
        return ["(no models — no datums recorded and no owner priors seeded yet)"]
    columns = _FULL_COLUMNS if verbose else _CONCISE_COLUMNS
    rows = [_table_row(r, verbose=verbose) for r in rollups]
    widths = {
        col: max(len(_TABLE_HEADERS[col]), *(len(row[col]) for row in rows)) for col in columns
    }

    def fmt(values: dict[str, str]) -> str:
        return "  ".join(values[col].ljust(widths[col]) for col in columns).rstrip()

    return [fmt(_TABLE_HEADERS), *(fmt(row) for row in rows)]


def render_tier_notes(rollups: list[ModelRollup]) -> list[str]:
    """Free-text strength/caution/guard owner flags, one line per model that has
    any — kept out of the table (they don't fit a column) but never dropped."""
    flagged = [r for r in rollups if r.strength or r.caution or r.guard]
    if not flagged:
        return []
    lines = ["Notes:"]
    for r in flagged:
        bits = []
        if r.strength:
            bits.append(f"strength: {r.strength}")
        if r.caution:
            bits.append(f"caution: {r.caution}")
        if r.guard:
            bits.append(f"guard: {r.guard}")
        lines.append(f"  {r.model}: " + " | ".join(bits))
    return lines


def render_cost_notes(rollups: list[ModelRollup]) -> list[str]:
    """Compact per-model supervisor-cost glance (2026-07-14 frozen schema): the
    dispatch-dividend tally and oversight median from datums carrying the
    agent-supplied `horus datum close --dividend`/`--oversight` flags. A model
    with none of that data yet is simply ABSENT from this section — never
    rendered as a literal zero (mirrors `render_tier_notes`'s pattern)."""
    flagged = [
        r for r in rollups
        if r.dividend_positive or r.dividend_neutral or r.dividend_negative or r.oversight_median
    ]
    if not flagged:
        return []
    lines = ["Cost:"]
    for r in flagged:
        bits = []
        if r.dividend_positive or r.dividend_neutral or r.dividend_negative:
            bits.append(f"dividend +{r.dividend_positive}/~{r.dividend_neutral}/-{r.dividend_negative}")
        if r.oversight_median:
            bits.append(f"oversight median: {r.oversight_median}")
        lines.append(f"  {r.model}: " + " · ".join(bits))
    return lines


def render_lifecycle_notes(rollups: list[ModelRollup]) -> list[str]:
    """Explicit lifecycle provenance, omitted entirely when no prior supplies it."""
    flagged = [r for r in rollups if r.lifecycle]
    if not flagged:
        return []
    return ["Lifecycle:", *(f"  {r.model}: {r.lifecycle}" for r in flagged)]


def _tier_peer_evidence(peer: TierPeer, by_model: dict[str, ModelRollup]) -> str:
    """One provider's cell in the neutral-tier map: ``provider=model[@effort]
    (evidence)`` where evidence is the model's measured clean-count when it has
    quality datums, else ``prior`` (owner-mapped, not yet measured locally)."""
    r = by_model.get(peer.model)
    if r and r.quality_datums:
        evidence = f"measured {r.clean_count}/{r.quality_datums} clean"
    else:
        evidence = "prior"
    model_label = peer.model + (f" @{peer.effort}" if peer.effort else "")
    return f"{peer.provider}={model_label} ({evidence})"


def render_tier_equivalence(rollups: list[ModelRollup]) -> list[str]:
    """Vendor-neutral tier -> per-provider model equivalence (owner prior),
    each annotated with its measured evidence from the roll-up.

    DISPLAY ONLY, like the roll-up: a card/envelope ``tier:`` names one of these
    capability points, and the provider is chosen at dispatch from capacity +
    owner choice — never from the label, never auto-routed here. Frontier on top
    (highest capability first)."""
    by_model = {r.model: r for r in rollups}
    lines = [
        "Vendor-neutral tiers (capability point -> provider model; owner prior + measured evidence):"
    ]
    for tier in reversed(NEUTRAL_TIERS):
        peers = TIER_EQUIVALENCE.get(tier, ())
        cells = " · ".join(_tier_peer_evidence(p, by_model) for p in peers) or "(no models mapped)"
        lines.append(f"  {tier:<8} {cells}")
    return lines


def tier_equivalence_to_dict(rollups: list[ModelRollup]) -> list[dict]:
    """Machine-readable neutral-tier map (for ``--stdout``/agent consumers)."""
    by_model = {r.model: r for r in rollups}
    out: list[dict] = []
    for tier in reversed(NEUTRAL_TIERS):
        peers = []
        for peer in TIER_EQUIVALENCE.get(tier, ()):
            r = by_model.get(peer.model)
            peers.append(
                {
                    "provider": peer.provider,
                    "model": peer.model,
                    "effort": peer.effort,
                    "evidence": "measured" if (r and r.quality_datums) else "prior",
                    "clean_datums": r.clean_count if r else 0,
                    "quality_datums": r.quality_datums if r else 0,
                }
            )
        out.append({"tier": tier, "peers": peers})
    return out


def render_model_rollup(rollups: list[ModelRollup], *, verbose: bool = False) -> str:
    """Human-readable text of the roll-up. Data only — describes what was measured
    and what the owner flagged; never names a model to pick. Concise by default
    (a CLI glance); ``verbose=True`` restores the LAST/RESEARCHED columns."""
    lines = [
        "Model calibration roll-up — DATA ONLY (the agent judges; this measures).",
        f"Sources: measured datums {datums_path()} · owner priors {priors_path()}",
        "",
    ]
    lines.extend(render_tier_table(rollups, verbose=verbose))
    lines.append("")
    lines.extend(render_tier_equivalence(rollups))
    lifecycle = render_lifecycle_notes(rollups)
    if lifecycle:
        lines.append("")
        lines.extend(lifecycle)
    notes = render_tier_notes(rollups)
    if notes:
        lines.append("")
        lines.extend(notes)
    cost = render_cost_notes(rollups)
    if cost:
        lines.append("")
        lines.extend(cost)
    return "\n".join(lines).rstrip() + "\n"


def rollup_to_dict(rollups: list[ModelRollup]) -> dict:
    """Machine-readable roll-up (for ``--stdout``/agent consumers). Data only."""
    return {
        "note": (
            "Data-only model calibration roll-up (measured datums + owner priors). "
            "Advisory: the agent judges the pick; this names no model to use."
        ),
        "models": [asdict(r) for r in rollups],
        "neutral_tiers": tier_equivalence_to_dict(rollups),
    }


# Non-blocking freshness nudge for the price/capability priors (see the
# `older-models-in-roster` backlog card): a display command warns, never gates.
STALE_PRIOR_DAYS = 14


def staleness_warning(
    rollups: list[ModelRollup], *, now: datetime | None = None, max_age_days: int = STALE_PRIOR_DAYS
) -> str | None:
    """A one-line non-blocking nudge when the price/capability priors look
    stale, or ``None`` when they're fresh enough to skip the nudge.

    "Fresh" is judged by the FRESHEST ``researched_at`` across all models —
    one model researched today is enough to call the roster fresh, since a
    partial refresh still moved the newest information forward. Warns when
    that freshest date is more than ``max_age_days`` old, OR when no model
    carries a ``researched_at`` at all (silence about freshness is itself a
    staleness signal). Never raises on an unparseable date — treated as absent
    for that model rather than failing the whole display command."""
    now = now or datetime.now(timezone.utc)
    freshest: datetime | None = None
    for r in rollups:
        if not r.researched_at:
            continue
        try:
            parsed = datetime.fromisoformat(r.researched_at)
        except ValueError:
            continue
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        if freshest is None or parsed > freshest:
            freshest = parsed
    if freshest is None:
        return "model-roster priors have no researched_at date set — consider refreshing"
    age_days = (now - freshest).days
    if age_days > max_age_days:
        return f"model-roster priors are {age_days} days old — consider refreshing"
    return None


# ---------------------------------------------------------------------------
# Delegation matrix — the tier ladder joined with the rubric's shape/verification
# tables (``horus capabilities --matrix``). DISPLAY-ONLY, like the roll-up above:
# these functions take the shape/verification tables as plain data (owned by
# ``horus.skills``) so this module stays free of a skills.py import; the CLI does
# the joining. No pick/route field anywhere — that boundary is asserted in tests.
# ---------------------------------------------------------------------------


def render_delegation_matrix(
    rollups: list[ModelRollup],
    shape_tiers: list[dict],
    verification_dial: list[dict],
    *,
    verbose: bool = False,
) -> str:
    """Human-readable delegation decision matrix. DISPLAY-ONLY: renders the tier
    ladder (owner priors + measured datums) next to the rubric's shape->tier and
    tier-trust->verification tables. Never picks or routes a model. Concise tier
    ladder by default; ``verbose=True`` restores the LAST/RESEARCHED columns."""
    lines = [
        "Delegation decision matrix — DISPLAY-ONLY (renders the rubric; never picks or routes a model).",
        f"Sources: measured datums {datums_path()} · owner priors {priors_path()}",
        "",
        "Tier ladder (owner priors + measured datums):",
    ]
    lines.extend(f"  {line}" for line in render_tier_table(rollups, verbose=verbose))
    lifecycle = render_lifecycle_notes(rollups)
    if lifecycle:
        lines.append("")
        lines.extend(f"  {line}" for line in lifecycle)
    notes = render_tier_notes(rollups)
    if notes:
        lines.append("")
        lines.extend(f"  {line}" for line in notes)
    lines.append("")
    lines.extend(render_tier_equivalence(rollups))
    lines.append("")
    lines.append("Shape -> tier role (delegation-rubric Step 3/4):")
    for row in shape_tiers:
        lines.append(f"  {row['shape']:<12} -> {row['tier_role']}")
        lines.append(f"  {'':<12}    {row['description']}")
    lines.append("")
    lines.append("Tier-trust -> verification depth (delegation-rubric Step 5):")
    for row in verification_dial:
        lines.append(f"  {row['tier_trust']:<10} -> {row['verification']}")
        lines.append(f"  {'':<10}    {row['description']}")
    return "\n".join(lines).rstrip() + "\n"


def delegation_matrix_to_dict(
    rollups: list[ModelRollup],
    shape_tiers: list[dict],
    verification_dial: list[dict],
) -> dict:
    """Machine-readable delegation matrix (for ``--stdout``/agent consumers).

    Joins the live tier ladder (``tiers`` — owner priors + measured datums, the
    same rows as ``rollup_to_dict``) with the rubric's ``roles`` (shape->tier)
    and ``verification_dial`` (tier-trust->verification) tables. DISPLAY-ONLY:
    no pick/route field anywhere — the agent applies this, nothing here
    auto-selects a model or auto-routes a dispatch.
    """
    return {
        "note": (
            "Delegation decision matrix — DISPLAY-ONLY. Joins measured datums + owner "
            "priors with the delegation-rubric's shape->tier and verification tables. "
            "Advisory: the agent applies this; it never auto-picks or auto-routes a model."
        ),
        "tiers": [asdict(r) for r in rollups],
        "neutral_tiers": tier_equivalence_to_dict(rollups),
        "roles": shape_tiers,
        "verification_dial": verification_dial,
    }
