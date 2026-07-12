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
  never written by a run.

HARD BOUNDARY (do not cross): the harness MEASURES and DISPLAYS; the AGENT judges.
``outcome`` is ALWAYS agent-supplied, NEVER an auto-scoring function. Nothing here
returns or suggests an executable model pick, and nothing auto-routes a dispatch.
The roll-up is the picture the agent reads — data only, advisory forever.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path

from horus import config

# Agent-supplied quality axis (the qualitative half of a datum, set at review time).
OUTCOMES: tuple[str, ...] = ("clean", "nudged", "bounced", "died")

# Mechanically-captured process-exit axis (why the run ENDED — distinct from quality).
EXITS: tuple[str, ...] = ("completed", "crashed", "usage-death")

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
    # --- mechanical, captured at completion ----------------------------------
    completed_at: str | None = None
    runtime_seconds: float | None = None
    exit: str | None = None            # one of EXITS
    returncode: int | None = None
    # Captured only where an adapter already surfaces them at completion; left
    # None otherwise (we never block on a field an adapter doesn't expose).
    tokens: int | None = None
    pr_opened: bool | None = None
    ci: str | None = None
    # --- qualitative, agent-supplied at review time --------------------------
    outcome: str | None = None         # one of OUTCOMES
    shape: str | None = None           # ambiguity/volume/runtime, agent's words
    note: str | None = None
    closed_at: str | None = None
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

    # --- writes (best-effort: swallow I/O so measurement never breaks a run) --

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
            if tokens is not None:
                row["tokens"] = tokens
            if pr_opened is not None:
                row["pr_opened"] = pr_opened
            if ci is not None:
                row["ci"] = ci
            self._save(rows)
        except (OSError, TypeError, ValueError):
            pass

    def close(self, prefix: str, *, outcome: str, shape: str | None, note: str | None) -> Datum:
        """Attach the agent-supplied qualitative half to a datum, resolved by id
        prefix. Raises ``LookupError`` for no/ambiguous match, ``ValueError`` for
        an out-of-vocabulary outcome. This is the ONLY path that sets ``outcome``
        — never inferred, never auto-scored."""
        if outcome not in OUTCOMES:
            raise ValueError(f"outcome must be one of {', '.join(OUTCOMES)} (got {outcome!r})")
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
        self._save(rows)
        return Datum.from_row(row)


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

schema_version = 1

[models."opus-4.8"]
tier = "design / ambiguity / verify gate"

[models."sonnet-5"]
tier = "scoped-impl lead"

[models."haiku-4.5"]
tier = "mechanical (unproven)"

[models."fable-5"]
tier = "frontier (early)"

[models."gpt-5.6"]
tier = "frontier codex"
strength = "frontier codex, self-verifies, PR-disciplined"
caution = "token-hungry — needs tightly-scoped task + explicit stopping point + budget headroom"
guard = "do not dispatch near usage ceiling"

[models."gpt-5.5"]
tier = "codex (early)"
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
    clean_count: int = 0
    last_outcomes: list[str] = field(default_factory=list)


def build_model_rollup(datums: list[Datum], priors: dict[str, dict]) -> list[ModelRollup]:
    """One row per model across BOTH layers (union of priors + measured models).

    Priors supply tier/strength/caution/guard; datums supply the measured counts
    and the most-recent outcomes. Deterministic ordering: most clean datums first,
    then name — so the proven leads sort to the top without any ranking judgment
    being encoded. Purely descriptive; it recommends nothing."""
    by_model: dict[str, list[Datum]] = {}
    for d in datums:
        if d.model:
            by_model.setdefault(d.model, []).append(d)

    rollups: list[ModelRollup] = []
    for model in sorted(set(priors) | set(by_model)):
        prior = priors.get(model, {})
        rows = sorted(by_model.get(model, []), key=lambda d: d.launched_at)
        closed = [d for d in rows if d.outcome]
        last = [d.outcome for d in closed][-LAST_N:]
        rollups.append(
            ModelRollup(
                model=model,
                tier=prior.get("tier"),
                strength=prior.get("strength"),
                caution=prior.get("caution"),
                guard=prior.get("guard"),
                total_datums=len(rows),
                closed_datums=len(closed),
                clean_count=sum(1 for d in closed if d.outcome == "clean"),
                last_outcomes=list(reversed(last)),  # most-recent first
            )
        )
    rollups.sort(key=lambda r: (-r.clean_count, r.model))
    return rollups


def render_model_rollup(rollups: list[ModelRollup]) -> str:
    """Human-readable text of the roll-up. Data only — describes what was measured
    and what the owner flagged; never names a model to pick."""
    lines = [
        "Model calibration roll-up — DATA ONLY (the agent judges; this measures).",
        f"Sources: measured datums {datums_path()} · owner priors {priors_path()}",
        "",
    ]
    if not rollups:
        lines.append("(no models — no datums recorded and no owner priors seeded yet)")
        return "\n".join(lines) + "\n"
    for r in rollups:
        tier = r.tier or "—"
        clean = f"{r.clean_count} clean / {r.closed_datums} closed / {r.total_datums} total"
        lines.append(f"{r.model:<12} tier: {tier}")
        lines.append(f"{'':<12} datums: {clean}")
        if r.last_outcomes:
            lines.append(f"{'':<12} last: {' '.join(r.last_outcomes)}")
        if r.strength:
            lines.append(f"{'':<12} strength: {r.strength}")
        if r.caution:
            lines.append(f"{'':<12} caution: {r.caution}")
        if r.guard:
            lines.append(f"{'':<12} guard: {r.guard}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def rollup_to_dict(rollups: list[ModelRollup]) -> dict:
    """Machine-readable roll-up (for ``--stdout``/agent consumers). Data only."""
    return {
        "note": (
            "Data-only model calibration roll-up (measured datums + owner priors). "
            "Advisory: the agent judges the pick; this names no model to use."
        ),
        "models": [asdict(r) for r in rollups],
    }


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
) -> str:
    """Human-readable delegation decision matrix. DISPLAY-ONLY: renders the tier
    ladder (owner priors + measured datums) next to the rubric's shape->tier and
    tier-trust->verification tables. Never picks or routes a model."""
    lines = [
        "Delegation decision matrix — DISPLAY-ONLY (renders the rubric; never picks or routes a model).",
        f"Sources: measured datums {datums_path()} · owner priors {priors_path()}",
        "",
        "Tier ladder (owner priors + measured datums):",
    ]
    if not rollups:
        lines.append("  (no models — no datums recorded and no owner priors seeded yet)")
    else:
        for r in rollups:
            tier = r.tier or "—"
            clean = f"{r.clean_count} clean / {r.closed_datums} closed / {r.total_datums} total"
            lines.append(f"  {r.model:<12} tier: {tier}")
            lines.append(f"  {'':<12} datums: {clean}")
            if r.last_outcomes:
                lines.append(f"  {'':<12} last: {' '.join(r.last_outcomes)}")
            if r.caution:
                lines.append(f"  {'':<12} caution: {r.caution}")
            if r.guard:
                lines.append(f"  {'':<12} guard: {r.guard}")
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
        "roles": shape_tiers,
        "verification_dial": verification_dial,
    }
