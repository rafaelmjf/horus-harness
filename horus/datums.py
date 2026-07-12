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
  fields (``price_in``/``price_out``/``capability_note``/``researched_at``) —
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
import tomllib
from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime, timezone
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
# always preferred and this is the fallback, not the primary path. GPT variants
# already carry their suffix at the call site (`gpt-5.6-sol`, not bare
# `gpt-5.6`) so they need no entry here.
ALIAS_TO_CANONICAL: dict[str, str] = {
    "sonnet": "sonnet-5",
    "haiku": "haiku-4.5",
    "opus": "opus-4.8",
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
    name that's already canonical, or unrecognized (GPT variants, a literal
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

    def migrate_names(self) -> dict[str, int]:
        """One-time, idempotent rename of bare dispatch aliases already captured
        in ``datums.json`` (``sonnet``, ``haiku``, ``opus``) to their canonical
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
# Optional price-for-capability fields (all back-compatible — omit entirely and
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
    # Price-for-capability fields (all optional, owner-prior, agent-researched —
    # see PRIORS_SEED docstring and the `older-models-in-roster` backlog card).
    price_in: float | None = None       # USD per Mtok, input
    price_out: float | None = None      # USD per Mtok, output
    capability_note: str | None = None  # short free-text: what it's good for
    capability_summary: str | None = None  # a few words, for the concise table
    researched_at: str | None = None    # ISO date (YYYY-MM-DD) last checked


def _researched_at_str(value: object) -> str | None:
    """Normalize a prior's ``researched_at`` to an ISO date string.

    TOML lets a hand-editor write an unquoted date (``2026-07-10``), which
    ``tomllib`` parses as a native ``date``/``datetime`` — accept that form
    alongside a plain quoted string so either style round-trips."""
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, str):
        return value
    return None


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
                price_in=prior.get("price_in"),
                price_out=prior.get("price_out"),
                capability_note=prior.get("capability_note"),
                capability_summary=prior.get("capability_summary"),
                researched_at=_researched_at_str(prior.get("researched_at")),
            )
        )
    rollups.sort(key=lambda r: (-r.clean_count, r.model))
    return rollups


# Table columns for the tier ladder, shared by `render_model_rollup` and
# `render_delegation_matrix`. The CONCISE set (default — a CLI glance) is
# model/tier/price/datums/capability; the FULL set (--verbose/--full, power
# users) restores LAST (per-run outcome history) and RESEARCHED. LAST is
# insider delegation-quality judgment (clean/nudged/bounced/died), not
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
    return {
        "model": r.model,
        "tier": r.tier or "-",
        "datums": f"{r.clean_count}/{r.total_datums}",
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
    notes = render_tier_notes(rollups)
    if notes:
        lines.append("")
        lines.extend(notes)
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
    notes = render_tier_notes(rollups)
    if notes:
        lines.append("")
        lines.extend(f"  {line}" for line in notes)
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
