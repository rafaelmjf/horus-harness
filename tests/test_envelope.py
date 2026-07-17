"""Tests for standing dispatch envelopes — the bound an unattended run runs into.

Every refusal class named in the card's acceptance is covered here at the
validation layer, plus the guard as `horus run` actually calls it: the point of
binding at `cmd_run` is that a scheduler cannot route around it, so the guard is
tested through the same entry point a dispatcher uses.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from horus import backlog, cli, config, envelope

TODAY = date(2026, 7, 22)
NOW = datetime(2026, 7, 22, 9, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path, monkeypatch):
    """Envelopes live under ~/.horus; never touch the real one from a test."""
    monkeypatch.setattr(config, "config_dir", lambda: tmp_path / "horus-home")
    return tmp_path


def _make(**overrides) -> envelope.Envelope:
    bounds = dict(
        name="trip",
        expires="2026-07-28",
        cards=("card-a",),
        accounts=("claude-personal",),
        tiers=("sonnet",),
        usage_floor=30,
        max_attempts_per_card=2,
        max_dispatches_per_day=3,
        today=TODAY,
    )
    bounds.update(overrides)
    return envelope.create(**bounds)


def _req(**overrides) -> envelope.DispatchRequest:
    fields = dict(card="card-a", account="claude-personal", tier="sonnet")
    fields.update(overrides)
    return envelope.DispatchRequest(**fields)


# --- create: bounds must narrow, and must be well-formed ---------------------


def test_create_persists_and_round_trips():
    created = _make(branch="x3", efforts=("high",), merge_authority=True)
    loaded = envelope.load("trip")
    assert loaded == created
    assert loaded.merge_authority is True
    assert loaded.branch == "x3"


def test_create_refuses_evergreen_or_past_expiry():
    with pytest.raises(envelope.EnvelopeError, match="in the past"):
        _make(expires="2026-07-21")
    with pytest.raises(envelope.EnvelopeError, match="YYYY-MM-DD"):
        _make(expires="whenever")


def test_create_refuses_an_envelope_that_authorizes_nothing():
    """A no-card no-branch envelope would never match: refuse now, not at fire time."""
    with pytest.raises(envelope.EnvelopeError, match="authorize something"):
        _make(cards=())
    with pytest.raises(envelope.EnvelopeError, match="--account"):
        _make(accounts=())
    with pytest.raises(envelope.EnvelopeError, match="--tier"):
        _make(tiers=())


def test_create_refuses_duplicate_name():
    _make()
    with pytest.raises(envelope.EnvelopeError, match="already exists"):
        _make()


def test_create_refuses_a_name_that_is_not_a_safe_file_stem():
    with pytest.raises(envelope.EnvelopeError, match="invalid envelope name"):
        _make(name="../escape")


def test_envelope_content_never_lands_in_a_repo(tmp_path):
    """Accounts and thresholds are machine-local by construction."""
    _make()
    assert envelope.envelope_path("trip").is_relative_to(config.config_dir())
    assert not (tmp_path / ".horus").exists()


# --- validate: the in-bounds launch and every refusal class ------------------


def test_in_bounds_dispatch_is_authorized():
    env = _make()
    assert envelope.validate(env, _req(), usage_remaining=80, now=NOW) is None


def test_branch_authorizes_its_stamped_cards():
    env = _make(cards=(), branch="x3")
    assert envelope.validate(env, _req(card="any-child", branch="x3"), usage_remaining=80, now=NOW) is None
    refusal = envelope.validate(env, _req(card="other", branch="different"), usage_remaining=80, now=NOW)
    assert refusal.bound == "card-whitelist"


def test_refuses_card_outside_the_whitelist():
    env = _make()
    refusal = envelope.validate(env, _req(card="card-z"), usage_remaining=80, now=NOW)
    assert refusal.bound == "card-whitelist"
    assert "card-z" in refusal.message and "card-a" in refusal.message


def test_refuses_account_outside_the_set():
    env = _make()
    refusal = envelope.validate(env, _req(account="claude-work"), usage_remaining=80, now=NOW)
    assert refusal.bound == "account-set"
    assert "claude-work" in refusal.message


def test_refuses_tier_outside_the_allow_list():
    """An allow-list, so it holds without this module owning a tier ordering."""
    env = _make()
    refusal = envelope.validate(env, _req(tier="opus"), usage_remaining=80, now=NOW)
    assert refusal.bound == "tier-allow-list"
    assert "opus" in refusal.message


def test_refuses_an_unstated_card_tier():
    """A card with no `tier:` is not implicitly cheap — it is simply not allowed."""
    env = _make()
    refusal = envelope.validate(env, _req(tier=""), usage_remaining=80, now=NOW)
    assert refusal.bound == "tier-allow-list"


def test_effort_allow_list_is_optional_but_binds_when_set():
    assert envelope.validate(_make(), _req(effort="high"), usage_remaining=80, now=NOW) is None
    env = envelope.create(
        name="capped", expires="2026-07-28", cards=("card-a",), accounts=("claude-personal",),
        tiers=("sonnet",), efforts=("low",), max_attempts_per_card=2,
        max_dispatches_per_day=3, today=TODAY,
    )
    refusal = envelope.validate(env, _req(effort="high"), usage_remaining=80, now=NOW)
    assert refusal.bound == "effort-allow-list"


def test_refuses_below_the_usage_reserve_floor():
    env = _make()
    assert envelope.validate(env, _req(), usage_remaining=30, now=NOW) is None  # floor is inclusive
    refusal = envelope.validate(env, _req(), usage_remaining=29, now=NOW)
    assert refusal.bound == "usage-floor"
    assert "29%" in refusal.message and "30%" in refusal.message


def test_unknown_capacity_fails_closed():
    """Unattended has no one to read a courtesy notice: unknown refuses."""
    refusal = envelope.validate(_make(), _req(), usage_remaining=None, now=NOW)
    assert refusal.bound == "usage-floor"
    assert "unknown" in refusal.message


# --- expiry and revocation ---------------------------------------------------


def test_expiry_is_inclusive_then_refuses():
    env = _make(expires="2026-07-28")
    last_day = datetime(2026, 7, 28, 23, 0, tzinfo=timezone.utc)
    assert envelope.validate(env, _req(), usage_remaining=80, now=last_day) is None
    after = datetime(2026, 7, 29, 0, 30, tzinfo=timezone.utc)
    refusal = envelope.validate(env, _req(), usage_remaining=80, now=after)
    assert refusal.bound == "expired"
    assert "2026-07-28" in refusal.message


def test_revocation_grounds_pending_dispatches():
    _make()
    assert envelope.validate(envelope.load("trip"), _req(), usage_remaining=80, now=NOW) is None
    envelope.revoke("trip", now=NOW)
    refusal = envelope.validate(envelope.load("trip"), _req(), usage_remaining=80, now=NOW)
    assert refusal.bound == "revoked"


def test_revoking_an_unknown_envelope_reports_rather_than_creating_one():
    assert envelope.revoke("nope") is None


def test_a_malformed_envelope_reads_as_absent_not_permissive():
    _make()
    envelope.envelope_path("trip").write_text("this is not toml {{{", encoding="utf-8")
    assert envelope.load("trip") is None


def test_an_unparseable_expiry_is_not_an_authorization():
    _make()
    envelope.envelope_path("trip").write_text('name = "trip"\nexpires = "soon"\n', encoding="utf-8")
    assert envelope.load("trip") is None


# --- the ledger: attempts and per-day bounds derive from it ------------------


def test_attempts_per_card_bound_exhausts():
    env = _make(max_attempts_per_card=2)
    for _ in range(2):
        assert envelope.validate(env, _req(), usage_remaining=80, now=NOW) is None
        envelope.record_dispatch("trip", _req(), session_id="s", now=NOW)
    refusal = envelope.validate(env, _req(), usage_remaining=80, now=NOW)
    assert refusal.bound == "attempts-per-card"
    assert "2 of 2" in refusal.message


def test_attempts_are_counted_per_card_not_globally():
    env = _make(cards=("card-a", "card-b"), max_attempts_per_card=1)
    envelope.record_dispatch("trip", _req(card="card-a"), session_id="s", now=NOW)
    assert envelope.validate(env, _req(card="card-b"), usage_remaining=80, now=NOW) is None
    assert envelope.validate(env, _req(card="card-a"), usage_remaining=80, now=NOW).bound == "attempts-per-card"


def test_dispatches_per_day_bound_resets_on_the_next_utc_day():
    env = _make(cards=("card-a", "card-b", "card-c"), max_dispatches_per_day=2, max_attempts_per_card=5)
    for card in ("card-a", "card-b"):
        envelope.record_dispatch("trip", _req(card=card), session_id="s", now=NOW)
    refusal = envelope.validate(env, _req(card="card-c"), usage_remaining=80, now=NOW)
    assert refusal.bound == "dispatches-per-day"
    tomorrow = NOW + timedelta(days=1)
    assert envelope.validate(env, _req(card="card-c"), usage_remaining=80, now=tomorrow) is None


def test_ledger_is_append_only_and_survives_a_torn_line():
    envelope.record_dispatch("trip", _req(), session_id="s1", now=NOW)
    with envelope.ledger_path("trip").open("a", encoding="utf-8") as fh:
        fh.write('{"ts": "2026-07-22T10:00:00+00:00", "card": "card-a"\n')  # torn append
    envelope.record_dispatch("trip", _req(), session_id="s2", now=NOW)
    rows = envelope.read_ledger("trip")
    assert [r["session_id"] for r in rows] == ["s1", "s2"]


def test_spend_reports_what_the_envelope_actually_spent():
    envelope.record_dispatch("trip", _req(), session_id="s1", now=NOW)
    envelope.record_dispatch("trip", _req(card="card-b"), session_id="s2", now=NOW)
    envelope.record_dispatch("trip", _req(), session_id="s3", now=NOW - timedelta(days=2))
    used = envelope.spend("trip", now=NOW)
    assert used.attempts_by_card == {"card-a": 2, "card-b": 1}
    assert used.dispatches_today == 2
    assert used.total == 3


# --- merge authority: the flag item 4 (`horus supervise`) will read ----------


def test_merge_authority_defaults_to_verify_and_escalate_only():
    assert _make().merge_authority is False


def test_merge_authority_is_explicit_and_persisted():
    _make(merge_authority=True)
    assert envelope.load("trip").merge_authority is True


# --- the guard as `horus run` binds it ---------------------------------------


def _project(tmp_path: Path, *, tier: str = "sonnet", branch: str = "") -> Path:
    root = tmp_path / "proj"
    cards = root / ".horus" / "backlog"
    cards.mkdir(parents=True)
    stamps = f"branch: {branch}\n" if branch else ""
    (cards / "card-a.md").write_text(
        f"---\nstatus: open\npriority: high\ntier: {tier}\n{stamps}---\n\n# card-a\n",
        encoding="utf-8",
    )
    return root


def _args(root: Path, **overrides) -> argparse.Namespace:
    fields = dict(
        agent="claude", account="claude-personal", effort=None, path=str(root),
        unattended=True, envelope="trip", card="card-a",
    )
    fields.update(overrides)
    return argparse.Namespace(**fields)


@pytest.fixture
def _full_capacity(monkeypatch):
    monkeypatch.setattr(cli, "_envelope_usage_remaining", lambda agent, account: 90)


def test_guard_authorizes_an_in_bounds_run(tmp_path, _full_capacity):
    root = _project(tmp_path)
    _make()
    refusal, auth = cli._envelope_guard(_args(root), root)
    assert refusal is None
    assert auth.name == "trip"
    assert auth.request.tier == "sonnet"


def test_guard_reads_tier_from_the_card_not_the_caller(tmp_path, _full_capacity):
    """The bound is checked against the card's own frontmatter, so a dispatcher
    cannot assert a cheaper tier than the card carries."""
    root = _project(tmp_path, tier="opus")
    _make(tiers=("sonnet",))
    refusal, auth = cli._envelope_guard(_args(root), root)
    assert refusal == 2
    assert auth is None


def test_guard_resolves_a_branch_stamped_card(tmp_path, _full_capacity):
    root = _project(tmp_path, branch="x3")
    _make(cards=(), branch="x3")
    refusal, auth = cli._envelope_guard(_args(root), root)
    assert refusal is None
    assert auth.request.branch == "x3"


def test_unattended_without_an_envelope_is_refused(tmp_path, capsys):
    root = _project(tmp_path)
    refusal, auth = cli._envelope_guard(_args(root, envelope=None), root)
    assert refusal == 2 and auth is None
    assert "--unattended requires --envelope" in capsys.readouterr().out


def test_envelope_without_a_card_is_refused(tmp_path):
    root = _project(tmp_path)
    _make()
    refusal, _ = cli._envelope_guard(_args(root, card=None), root)
    assert refusal == 2


def test_guard_refuses_an_unknown_envelope(tmp_path):
    root = _project(tmp_path)
    refusal, _ = cli._envelope_guard(_args(root), root)
    assert refusal == 2


def test_guard_refuses_a_card_that_does_not_exist(tmp_path, _full_capacity):
    root = _project(tmp_path)
    _make(cards=("ghost",))
    refusal, _ = cli._envelope_guard(_args(root, card="ghost"), root)
    assert refusal == 2


def test_an_attended_run_without_an_envelope_passes_through(tmp_path):
    root = _project(tmp_path)
    refusal, auth = cli._envelope_guard(_args(root, unattended=False, envelope=None), root)
    assert refusal is None and auth is None


def test_force_does_not_override_an_envelope_bound(tmp_path, _full_capacity):
    """--force is an attended override for the usage preflight; the owner's standing
    authorization is not something a dispatcher may override."""
    root = _project(tmp_path, tier="opus")
    _make(tiers=("sonnet",))
    refusal, _ = cli._envelope_guard(_args(root, force=True), root)
    assert refusal == 2


def test_guard_refuses_when_capacity_is_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "_envelope_usage_remaining", lambda agent, account: None)
    root = _project(tmp_path)
    _make()
    refusal, _ = cli._envelope_guard(_args(root), root)
    assert refusal == 2


def test_agents_without_a_usage_window_report_full_capacity(monkeypatch):
    assert cli._envelope_usage_remaining("fake", None) == 100
