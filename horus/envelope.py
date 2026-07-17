"""Standing dispatch envelopes — bounded pre-authorization for unattended dispatch.

The delegation rule requires the owner to approve the *exact envelope per launch*.
That is right for attended work and impossible for an unattended loop: a scheduled
worker fires while the owner is away. The resolution is not to route around the
rule but to narrow it: the owner creates an explicit, bounded, **expiring**
authorization artifact up front, and every unattended dispatch validates against
it and refuses to exceed it.

This module owns that artifact. It **bounds only** — it never selects a card, an
account, or a model, never estimates spend, and never routes. Selection stays with
the owner (or the card's own stamps) before scheduling; this is the wall that
selection runs into.

Two files per envelope under ``~/.horus/envelopes/`` (machine-local, never in a
repo — an envelope names accounts):

``<name>.toml``
    The bounds, written once at create. Only ``revoke`` mutates it (a flag), so a
    bad write can never silently widen an authorization.
``<name>.jsonl``
    An append-only ledger, one line per **authorized** dispatch. Attempt and
    per-day counts are *derived* by reading it — there is no mutable counter to
    lose an update or to race. It is also the honest record of what the envelope
    actually spent. Readers ignore unknown fields (forward-readable, like the
    session registry).

Bounds are read at fire time, so ``revoke`` grounds all pending scheduled work
immediately — the owner's kill switch. Live attached sessions are untouched:
this gates launch, not running processes.

**Tiers are an allow-list, not an ordered ceiling.** Today's cards carry
``tier: opus|sonnet``; the vendor-neutral tier vocabulary (low/medium/high/
frontier) lands separately. An allow-list bounds exactly as hard as a ceiling
without this module owning a total order that another card is about to redefine.
"""

from __future__ import annotations

import json
import re
import tomllib
from dataclasses import dataclass, replace
from datetime import date, datetime, timezone
from pathlib import Path

from horus import config

# An envelope name is a file stem and appears in refusal text: keep it boring.
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")

# Unattended dispatch fails closed on an unknown capacity signal. The attended
# preflight (`_run_usage_preflight`) treats unknown as a courtesy notice and
# proceeds; nobody is watching here, so unknown is a refusal instead.
USAGE_UNKNOWN_BOUND = "usage-floor"


class EnvelopeError(Exception):
    """A malformed envelope request (bad name, bad bounds, already exists)."""


@dataclass(frozen=True)
class Envelope:
    """One owner-created standing authorization. Bounds only — never a selector."""

    name: str
    created: str            # ISO date
    expires: str            # ISO date, required — no evergreen standing authority
    cards: tuple[str, ...]  # exact card names this envelope authorizes
    branch: str             # or a whole vision branch by name ("" if unused)
    accounts: tuple[str, ...]
    tiers: tuple[str, ...]  # allow-list of card `tier:` labels ("" empty = none)
    efforts: tuple[str, ...]  # allow-list of effort labels; empty = any effort
    usage_floor: int        # refuse below this % remaining in the account's window
    max_attempts_per_card: int
    max_dispatches_per_day: int
    merge_authority: bool   # may `horus supervise` merge on green, or verify+escalate only
    revoked: bool = False
    revoked_at: str = ""

    def expiry_date(self) -> date:
        return date.fromisoformat(self.expires)

    def is_expired(self, *, today: date) -> bool:
        """Expiry is inclusive: an envelope is live through the end of its ``expires`` day."""
        return today > self.expiry_date()

    def authorizes_card(self, card: str, *, branch: str = "") -> bool:
        """Whether ``card`` is inside the whitelist, directly or via its vision branch."""
        if card in self.cards:
            return True
        return bool(self.branch) and branch == self.branch


@dataclass(frozen=True)
class DispatchRequest:
    """What an unattended launch is asking to do, as the envelope sees it.

    ``tier``/``branch`` come from the card's own frontmatter, not from the caller —
    a scheduled run cannot talk its way past the tier bound by asserting a tier.

    ``account`` is the canonical ``<agent>-<alias>`` label (see
    ``config.resolve_account``), which is what an envelope stores: an alias alone
    names a different rate-limit pool under each agent.
    """

    card: str
    account: str | None
    tier: str = ""
    effort: str = ""
    branch: str = ""


@dataclass(frozen=True)
class Refusal:
    """A violated bound. ``bound`` is the machine-readable name; ``message`` names it
    to a human. Every refusal path must produce one — never a bare False."""

    bound: str
    message: str


@dataclass(frozen=True)
class Spend:
    """What an envelope has already authorized, derived from its ledger."""

    attempts_by_card: dict[str, int]
    dispatches_today: int
    total: int


def envelopes_dir() -> Path:
    return config.config_dir() / "envelopes"


def envelope_path(name: str) -> Path:
    return envelopes_dir() / f"{name}.toml"


def ledger_path(name: str) -> Path:
    return envelopes_dir() / f"{name}.jsonl"


def _validate_name(name: str) -> str:
    name = name.strip()
    if not _NAME_RE.match(name):
        raise EnvelopeError(
            f"invalid envelope name {name!r}: use letters, digits, '.', '_', '-' "
            "(and start with a letter or digit)"
        )
    return name


def _toml_list(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(f'"{v}"' for v in values) + "]"


def _write(env: Envelope) -> None:
    envelopes_dir().mkdir(parents=True, exist_ok=True)
    lines = [
        "# Horus standing dispatch envelope (machine-local — names accounts, never commit).",
        "# Bounds only: this file authorizes, it never selects. Written at create;",
        "# only `horus envelope revoke` mutates it.",
        "",
        f'name = "{env.name}"',
        f'created = "{env.created}"',
        f'expires = "{env.expires}"',
        f"cards = {_toml_list(env.cards)}",
        f'branch = "{env.branch}"',
        f"accounts = {_toml_list(env.accounts)}",
        f"tiers = {_toml_list(env.tiers)}",
        f"efforts = {_toml_list(env.efforts)}",
        f"usage_floor = {env.usage_floor}",
        f"max_attempts_per_card = {env.max_attempts_per_card}",
        f"max_dispatches_per_day = {env.max_dispatches_per_day}",
        f"merge_authority = {'true' if env.merge_authority else 'false'}",
        f"revoked = {'true' if env.revoked else 'false'}",
        f'revoked_at = "{env.revoked_at}"',
        "",
    ]
    envelope_path(env.name).write_text("\n".join(lines), encoding="utf-8")


def _strs(raw: object) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    return tuple(str(v).strip() for v in raw if str(v).strip())


def load(name: str) -> Envelope | None:
    """The envelope by name, or ``None`` when it does not exist or cannot be read.

    A malformed envelope reads as absent rather than as permissive: every caller
    treats ``None`` as "no authorization", so corruption fails closed.
    """
    path = envelope_path(name)
    if not path.exists():
        return None
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    try:
        expires = str(data["expires"]).strip()
        date.fromisoformat(expires)  # an unparseable expiry is not an authorization
    except (KeyError, ValueError):
        return None
    return Envelope(
        name=str(data.get("name", name)),
        created=str(data.get("created", "")),
        expires=expires,
        cards=_strs(data.get("cards")),
        branch=str(data.get("branch", "")).strip(),
        accounts=_strs(data.get("accounts")),
        tiers=_strs(data.get("tiers")),
        efforts=_strs(data.get("efforts")),
        usage_floor=int(data.get("usage_floor", 0) or 0),
        max_attempts_per_card=int(data.get("max_attempts_per_card", 0) or 0),
        max_dispatches_per_day=int(data.get("max_dispatches_per_day", 0) or 0),
        merge_authority=bool(data.get("merge_authority", False)),
        revoked=bool(data.get("revoked", False)),
        revoked_at=str(data.get("revoked_at", "")),
    )


def load_all() -> list[Envelope]:
    """Every readable envelope, newest expiry first."""
    directory = envelopes_dir()
    if not directory.is_dir():
        return []
    found = [load(path.stem) for path in sorted(directory.glob("*.toml"))]
    return sorted(
        [e for e in found if e is not None], key=lambda e: (e.expires, e.name), reverse=True
    )


def create(
    *,
    name: str,
    expires: str,
    cards: tuple[str, ...] = (),
    branch: str = "",
    accounts: tuple[str, ...] = (),
    tiers: tuple[str, ...] = (),
    efforts: tuple[str, ...] = (),
    usage_floor: int = 0,
    max_attempts_per_card: int = 1,
    max_dispatches_per_day: int = 1,
    merge_authority: bool = False,
    today: date | None = None,
) -> Envelope:
    """Create and persist a bounded envelope. Raises ``EnvelopeError`` on bad bounds.

    Every bound is required to be *narrowing*: an envelope with no cards and no
    branch, or no accounts, authorizes nothing and is refused at create rather
    than silently never matching at fire time.
    """
    name = _validate_name(name)
    if envelope_path(name).exists():
        raise EnvelopeError(f"envelope {name!r} already exists; revoke it or choose another name")
    today = today or datetime.now(timezone.utc).date()
    try:
        expiry = date.fromisoformat(expires)
    except ValueError as exc:
        raise EnvelopeError(f"invalid --expires {expires!r}: use YYYY-MM-DD") from exc
    if expiry < today:
        raise EnvelopeError(f"--expires {expires} is in the past; an envelope must outlive its creation")
    if not cards and not branch:
        raise EnvelopeError("an envelope must authorize something: pass --card and/or --branch")
    if not accounts:
        raise EnvelopeError("an envelope must name at least one --account")
    # A misnamed account is the worst failure this artifact has: the envelope looks
    # created, the owner leaves for a week, and every dispatch silently refuses on a
    # bound nobody meant to set. Resolve every name to exactly one real account and
    # store the canonical `<agent>-<alias>` label — `personal` alone is a different
    # rate-limit pool under claude than under codex, so an envelope must not be
    # vague about which one it authorizes.
    resolved: list[str] = []
    for account_name in accounts:
        resolution = config.resolve_account(account_name)
        if not resolution.ok:
            raise EnvelopeError(
                f"{resolution.error} An envelope naming an account that does not "
                "resolve would authorize nothing."
            )
        if resolution.ref.label not in resolved:
            resolved.append(resolution.ref.label)
    accounts = tuple(resolved)
    if not tiers:
        raise EnvelopeError("an envelope must allow at least one --tier")
    if not 0 <= usage_floor <= 100:
        raise EnvelopeError(f"--usage-floor {usage_floor} must be between 0 and 100 (% remaining)")
    if max_attempts_per_card < 1:
        raise EnvelopeError("--max-attempts must be at least 1")
    if max_dispatches_per_day < 1:
        raise EnvelopeError("--max-dispatches-per-day must be at least 1")
    env = Envelope(
        name=name,
        created=today.isoformat(),
        expires=expires,
        cards=tuple(cards),
        branch=branch,
        accounts=tuple(accounts),
        tiers=tuple(tiers),
        efforts=tuple(efforts),
        usage_floor=usage_floor,
        max_attempts_per_card=max_attempts_per_card,
        max_dispatches_per_day=max_dispatches_per_day,
        merge_authority=merge_authority,
    )
    _write(env)
    return env


def revoke(name: str, *, now: datetime | None = None) -> Envelope | None:
    """Ground the envelope. Pending scheduled dispatches validate at fire time, so
    they are refused from this moment; live attached sessions keep running."""
    env = load(name)
    if env is None:
        return None
    now = now or datetime.now(timezone.utc)
    revoked = replace(env, revoked=True, revoked_at=now.isoformat(timespec="seconds"))
    _write(revoked)
    return revoked


def record_dispatch(
    name: str,
    request: DispatchRequest,
    *,
    session_id: str,
    now: datetime | None = None,
) -> None:
    """Append one authorized dispatch to the ledger. Call only after ``validate``
    returns ``None`` — the ledger is the record of what was *authorized*, and the
    attempt/day bounds are derived from it."""
    now = now or datetime.now(timezone.utc)
    envelopes_dir().mkdir(parents=True, exist_ok=True)
    row = {
        "ts": now.astimezone(timezone.utc).isoformat(timespec="seconds"),
        "card": request.card,
        "account": request.account or "",
        "tier": request.tier,
        "effort": request.effort,
        "session_id": session_id,
    }
    with ledger_path(name).open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def read_ledger(name: str) -> list[dict]:
    """Ledger rows, oldest first. Unreadable rows are skipped, not fatal: a partial
    line (a torn append) must not make the envelope unusable — but note this counts
    *fewer* dispatches, so pair it with the append being a single small write."""
    path = ledger_path(name)
    if not path.exists():
        return []
    rows: list[dict] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def spend(name: str, *, now: datetime | None = None) -> Spend:
    """What the envelope has authorized so far, derived from the ledger.

    ``dispatches_today`` counts by **UTC** date so the bound does not shift with the
    machine's timezone mid-trip."""
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(timezone.utc).date().isoformat()
    attempts: dict[str, int] = {}
    today_count = 0
    rows = read_ledger(name)
    for row in rows:
        card = str(row.get("card", ""))
        if card:
            attempts[card] = attempts.get(card, 0) + 1
        if str(row.get("ts", "")).startswith(today):
            today_count += 1
    return Spend(attempts_by_card=attempts, dispatches_today=today_count, total=len(rows))


def validate(
    env: Envelope,
    request: DispatchRequest,
    *,
    usage_remaining: int | None,
    now: datetime | None = None,
) -> Refusal | None:
    """The wall. ``None`` authorizes the dispatch; a ``Refusal`` names the exact
    violated bound.

    Checks run cheapest-and-most-fundamental first so the refusal a human reads is
    the most explanatory one (an expired envelope reports expiry, not a tier miss).
    """
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(timezone.utc).date()

    if env.revoked:
        return Refusal(
            "revoked",
            f"envelope {env.name!r} was revoked{f' at {env.revoked_at}' if env.revoked_at else ''}",
        )
    if env.is_expired(today=today):
        return Refusal("expired", f"envelope {env.name!r} expired on {env.expires} (today is {today.isoformat()})")
    if not env.authorizes_card(request.card, branch=request.branch):
        allowed = ", ".join(env.cards) or "(none)"
        via = f" or branch {env.branch!r}" if env.branch else ""
        return Refusal(
            "card-whitelist",
            f"card {request.card!r} is not authorized by envelope {env.name!r}; it allows: {allowed}{via}",
        )
    if request.account not in env.accounts:
        return Refusal(
            "account-set",
            f"account {request.account or '(none)'!r} is not in envelope {env.name!r}; "
            f"it allows: {', '.join(env.accounts)}. Accounts are named "
            "`<agent>-<alias>`, because one alias is a different rate-limit pool "
            "under each agent",
        )
    if request.tier not in env.tiers:
        return Refusal(
            "tier-allow-list",
            f"card tier {request.tier or '(unstated)'!r} is not allowed by envelope {env.name!r}; "
            f"it allows: {', '.join(env.tiers)}",
        )
    if env.efforts and request.effort and request.effort not in env.efforts:
        return Refusal(
            "effort-allow-list",
            f"effort {request.effort!r} is not allowed by envelope {env.name!r}; "
            f"it allows: {', '.join(env.efforts)}",
        )

    used = spend(env.name, now=now)
    attempts = used.attempts_by_card.get(request.card, 0)
    if attempts >= env.max_attempts_per_card:
        return Refusal(
            "attempts-per-card",
            f"card {request.card!r} has used {attempts} of {env.max_attempts_per_card} "
            f"attempts allowed by envelope {env.name!r}",
        )
    if used.dispatches_today >= env.max_dispatches_per_day:
        return Refusal(
            "dispatches-per-day",
            f"envelope {env.name!r} has used {used.dispatches_today} of "
            f"{env.max_dispatches_per_day} dispatches allowed today",
        )

    # The floor is opt-in, and fail-closed binds the bound the owner actually set.
    # With no floor (0) there is no capacity guarantee to verify, so an unreadable
    # signal is irrelevant and must not ground the dispatch. With a floor, unknown
    # capacity is NOT healthy capacity: nobody is watching, so it refuses.
    if env.usage_floor > 0:
        if usage_remaining is None:
            return Refusal(
                USAGE_UNKNOWN_BOUND,
                f"capacity is unknown for account {request.account or '(none)'!r} "
                "(offline, missing creds, or schema drift), so the "
                f"{env.usage_floor}% reserve floor of envelope {env.name!r} cannot be "
                "verified — an unattended dispatch fails closed",
            )
        if usage_remaining < env.usage_floor:
            return Refusal(
                USAGE_UNKNOWN_BOUND,
                f"account {request.account or '(none)'!r} has {usage_remaining}% of its window "
                f"remaining, below the {env.usage_floor}% reserve floor of envelope {env.name!r}",
            )
    return None
