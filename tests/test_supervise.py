"""Tests for the unattended verify → merge → close → escalate supervisor.

The acceptance the card pins, at the unit layer, with every external effect
(CI watch, freshness gate, live probe, gh merge, close, ship, notify, andon)
injected so nothing here touches the network, git, or systemd:

- green + no merge authority        → verified, merges nothing (the safe default);
- green + authority + no basis      → escalate (never accept on self-report);
- red required check / freshness    → escalate + halt dependents, merge nothing;
- authority + basis + no probe      → escalate (never merge without the live probe);
- authority + basis + probe fails   → escalate;
- authority + basis + probe passes  → merge + close + ship;
- already-merged PR                 → idempotent no-op;
- exit code reflects accept(0) vs escalate(1).
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from horus import cli, notify, supervise


def _ctx(**kw) -> supervise.SupervisionContext:
    base = dict(
        root=Path("/repo"),
        pr_ref="42",
        head_sha="abc123def456",
        base_ref="basesha000",
        card="my-card",
        delivery_expected=True,
        merge_authority=False,
        session_id="sess-1",
        envelope_name="trip",
    )
    base.update(kw)
    return supervise.SupervisionContext(**base)


@pytest.fixture
def _no_real_effects(monkeypatch):
    """All gates green, all actions succeed, no escalation transport, no andon —
    each test overrides only the seam it is about."""
    monkeypatch.setattr(supervise, "_verify_ci", lambda root, ref, *, timeout: (True, "abc123def456"))
    monkeypatch.setattr(supervise, "_verify_freshness", lambda root, base: (True, ""))
    monkeypatch.setattr(supervise, "_run_probe", lambda root, probe, **k: (True, ""))
    monkeypatch.setattr(supervise, "_pr_state", lambda root, ref: "OPEN")
    merges: list[str] = []
    ships: list[str] = []
    monkeypatch.setattr(supervise, "_merge_pr", lambda root, ref: merges.append(ref) or (True, ""))
    monkeypatch.setattr(supervise, "_close_continuity", lambda root: (True, ""))
    monkeypatch.setattr(supervise, "_ship_card", lambda root, card, **k: ships.append(card))
    escalations: list[str] = []

    def _fake_escalate(esc, **kw):
        escalations.append(esc.summary)
        return notify.EscalationResult(sink="telegram", delivered=True)

    monkeypatch.setattr(supervise.notify, "escalate", _fake_escalate)
    monkeypatch.setattr(supervise, "halt_dependents", lambda root, card, reason: [("dep-card", "schedid")])
    return {"merges": merges, "ships": ships, "escalations": escalations}


# --------------------------------------------------------------------------- #
# Verify-only (the safe default)
# --------------------------------------------------------------------------- #


def test_green_without_merge_authority_verifies_but_merges_nothing(_no_real_effects):
    out = supervise.supervise(_ctx(merge_authority=False))
    assert out.verdict == "verified"
    assert out.exit_code == 0
    assert _no_real_effects["merges"] == []       # never merged
    assert _no_real_effects["escalations"] == []  # a clean verify is silent


# --------------------------------------------------------------------------- #
# Escalation paths
# --------------------------------------------------------------------------- #


def test_red_required_check_escalates_and_halts_dependents(monkeypatch, _no_real_effects):
    monkeypatch.setattr(supervise, "_verify_ci", lambda root, ref, *, timeout: (False, "required checks failure on abc123"))
    out = supervise.supervise(_ctx(merge_authority=True))
    assert out.verdict == "escalated"
    assert out.exit_code == 1
    assert _no_real_effects["merges"] == []
    assert any("required checks failure" in s for s in _no_real_effects["escalations"])
    assert out.halted == ("dep-card",)  # andon fired


def test_failed_freshness_gate_escalates(monkeypatch, _no_real_effects):
    monkeypatch.setattr(supervise, "_verify_freshness", lambda root, base: (False, "1 delivery commit pending"))
    out = supervise.supervise(_ctx(merge_authority=True))
    assert out.verdict == "escalated"
    assert any("freshness gate failed" in s for s in _no_real_effects["escalations"])
    assert _no_real_effects["merges"] == []


def test_merge_authority_without_a_pinned_basis_refuses_and_escalates(_no_real_effects):
    # self-report only: no dispatch base / no delivery expectation
    out = supervise.supervise(_ctx(merge_authority=True, base_ref=None, delivery_expected=False))
    assert out.verdict == "escalated"
    assert any("refusing to accept on self-report" in s for s in _no_real_effects["escalations"])
    assert _no_real_effects["merges"] == []


def test_merge_authorized_but_no_probe_refuses_to_merge(_no_real_effects):
    out = supervise.supervise(_ctx(merge_authority=True), probe=None)
    assert out.verdict == "escalated"
    assert any("no live probe declared" in s for s in _no_real_effects["escalations"])
    assert _no_real_effects["merges"] == []


def test_probe_failure_escalates_and_merges_nothing(monkeypatch, _no_real_effects):
    monkeypatch.setattr(supervise, "_run_probe", lambda root, probe, **k: (False, "probe exited 1"))
    out = supervise.supervise(_ctx(merge_authority=True), probe="pytest -q")
    assert out.verdict == "escalated"
    assert any("live probe failed" in s for s in _no_real_effects["escalations"])
    assert _no_real_effects["merges"] == []


# --------------------------------------------------------------------------- #
# The accept path
# --------------------------------------------------------------------------- #


def test_all_green_authorized_and_probe_passes_merges_closes_ships(_no_real_effects):
    out = supervise.supervise(_ctx(merge_authority=True), probe="pytest -q")
    assert out.verdict == "merged"
    assert out.exit_code == 0
    assert _no_real_effects["merges"] == ["42"]
    assert _no_real_effects["ships"] == ["my-card"]
    assert _no_real_effects["escalations"] == []


def test_already_merged_pr_is_an_idempotent_noop(monkeypatch, _no_real_effects):
    monkeypatch.setattr(supervise, "_pr_state", lambda root, ref: "MERGED")
    out = supervise.supervise(_ctx(merge_authority=True), probe="pytest -q")
    assert out.verdict == "noop"
    assert out.exit_code == 0
    assert _no_real_effects["merges"] == []  # not merged twice


def test_no_pr_or_sha_escalates(_no_real_effects):
    out = supervise.supervise(_ctx(pr_ref=None))
    assert out.verdict == "escalated"
    assert any("nothing delivered" in s for s in _no_real_effects["escalations"])


# --------------------------------------------------------------------------- #
# Andon graph (pure logic)
# --------------------------------------------------------------------------- #


def test_transitive_dependents_walks_the_whole_chain():
    deps = {
        "a": set(),
        "b": {"a"},        # b depends on a
        "c": {"b"},        # c depends on b (transitively on a)
        "d": {"x"},        # unrelated
    }
    dependents = supervise._transitive_dependents("a", deps)
    assert dependents == {"b", "c"}
    assert "d" not in dependents


def test_scheduled_card_parses_the_card_flag():
    assert supervise._scheduled_card(("horus", "run", "--card", "foo", "--account", "x")) == "foo"
    assert supervise._scheduled_card(("horus", "run", "prompt")) is None


def test_halt_dependents_halts_only_transitive_dependents(monkeypatch):
    # cards: b→a, c→b, e→d ; failed card = a ⇒ halt b and c only
    monkeypatch.setattr(supervise, "_card_deps", lambda root: {
        "a": set(), "b": {"a"}, "c": {"b"}, "d": set(), "e": {"d"},
    })

    class _Sched:
        def __init__(self, ident, card, fired=False, halted=False):
            self.id = ident
            self.command = ("horus", "run", "--card", card)
            self.fired = fired
            self.halted = halted

    scheds = [
        _Sched("s1", "b"), _Sched("s2", "c"), _Sched("s3", "e"),
        _Sched("s4", "b", fired=True),      # already fired — leave it
    ]
    monkeypatch.setattr(supervise.schedule, "load_all", lambda: scheds)
    halted_ids: list[str] = []
    monkeypatch.setattr(supervise.schedule, "halt", lambda ident, reason: halted_ids.append(ident) or True)

    halted = supervise.halt_dependents(Path("/repo"), "a", "red gate")
    assert {card for card, _ in halted} == {"b", "c"}   # e is independent, fired-b skipped
    assert {sched_id for _, sched_id in halted} == {"s1", "s2"}  # (card, schedule_id) pairs
    assert set(halted_ids) == {"s1", "s2"}


def test_escalation_carries_a_release_button_per_halted_dependent(monkeypatch):
    """Andon-reply: an escalation that halted dependents offers a one-tap `release
    <id>` per halted dispatch, so the owner re-arms it from the phone."""
    captured: dict = {}

    def _capture(esc, **kw):
        captured["actions"] = esc.actions
        return notify.EscalationResult(sink="telegram", delivered=True)

    monkeypatch.setattr(supervise.notify, "escalate", _capture)
    monkeypatch.setattr(
        supervise, "halt_dependents",
        lambda root, card, reason: [("dep-b", "s1"), ("dep-c", "s2")],
    )
    ctx = supervise.SupervisionContext(
        root=Path("/repo"), pr_ref="7", head_sha="abc", base_ref="base",
        card="a", delivery_expected=True, merge_authority=False, session_id="sess1234",
    )
    outcome = supervise._escalate_and_halt(ctx, "red gate")
    assert outcome.halted == ("dep-b", "dep-c")  # card names preserved for the CLI
    data = {label: cb for label, cb in captured["actions"]}
    assert data.get("Release dep-b") == "release s1"
    assert data.get("Release dep-c") == "release s2"


def test_resolve_context_treats_a_non_session_as_a_verify_only_pr(monkeypatch):
    # empty registry ⇒ target is not a session id ⇒ PR ref, verify-only
    monkeypatch.setattr(supervise.registry.Registry, "default", classmethod(lambda cls: _EmptyReg()))
    ctx = supervise.resolve_context("123", path="/repo")
    assert ctx is not None
    assert ctx.pr_ref == "123"
    assert ctx.merge_authority is False
    assert ctx.delivery_expected is False


class _EmptyReg:
    def all(self):
        return []


# --------------------------------------------------------------------------- #
# Deferred targets — resolve a card/branch to its worker session at fire time
# --------------------------------------------------------------------------- #


def _rec(session_id, **kw):
    base = dict(session_id=session_id, agent="claude", project="/repo")
    base.update(kw)
    return supervise.registry.SessionRecord(**base)


class _Reg:
    def __init__(self, records):
        self._records = records

    def all(self):
        return self._records


class _Env:
    def __init__(self, name, merge_authority=False):
        self.name = name
        self.merge_authority = merge_authority


def _stub_registry(monkeypatch, records):
    monkeypatch.setattr(supervise.registry.Registry, "default", classmethod(lambda cls: _Reg(records)))


def _stub_envelopes(monkeypatch, envs, ledgers):
    monkeypatch.setattr(supervise.envelope, "load_all", lambda: envs)
    monkeypatch.setattr(supervise.envelope, "read_ledger", lambda name: ledgers.get(name, []))


def test_resolve_deferred_by_card_binds_the_newest_dispatch_keeping_base_and_authority(monkeypatch):
    """A `--card` target resolves at fire time to the newest worker session dispatched
    for that card — with its pinned base + PR + the envelope's merge authority, so a
    supervisor scheduled before the worker existed can still merge under authority."""
    rec = _rec("sessAAA", dispatch_base_sha="base1", delivery_head_sha="head1",
               delivery_pr_number=99, delivery_expected=True)
    _stub_registry(monkeypatch, [_rec("noise"), rec])
    _stub_envelopes(monkeypatch, [_Env("away", merge_authority=True)], {"away": [
        {"ts": "2026-07-19T01:00:00+00:00", "card": "my-card", "session_id": "old-sess"},
        {"ts": "2026-07-19T01:30:00+00:00", "card": "my-card", "session_id": "sessAAA"},
    ]})
    ctx = supervise.resolve_deferred(card="my-card", path="/repo")
    assert ctx is not None
    assert ctx.session_id == "sessAAA"      # newest ledger row for the card
    assert ctx.base_ref == "base1"          # pinned dispatch base survives
    assert ctx.pr_ref == "99"
    assert ctx.merge_authority is True       # envelope authority survives the deferral
    assert ctx.card == "my-card"


def test_resolve_deferred_by_card_with_no_dispatch_returns_none(monkeypatch):
    _stub_registry(monkeypatch, [])
    _stub_envelopes(monkeypatch, [_Env("away")], {"away": []})
    assert supervise.resolve_deferred(card="ghost", path="/repo") is None


def test_resolve_deferred_by_branch_picks_the_newest_record(monkeypatch):
    old = _rec("s-old", delivery_branch="auto/x", updated_at="2026-07-19T01:00:00+00:00",
               dispatch_base_sha="b0", delivery_head_sha="h0")
    new = _rec("s-new", delivery_branch="auto/x", updated_at="2026-07-19T02:00:00+00:00",
               dispatch_base_sha="b1", delivery_head_sha="h1", delivery_pr_number=7)
    _stub_registry(monkeypatch, [old, new])
    _stub_envelopes(monkeypatch, [], {})
    ctx = supervise.resolve_deferred(branch="auto/x", path="/repo")
    assert ctx is not None
    assert ctx.session_id == "s-new" and ctx.pr_ref == "7" and ctx.base_ref == "b1"


def test_resolve_deferred_by_branch_with_no_match_returns_none(monkeypatch):
    _stub_registry(monkeypatch, [_rec("s", delivery_branch="auto/other")])
    _stub_envelopes(monkeypatch, [], {})
    assert supervise.resolve_deferred(branch="auto/missing", path="/repo") is None


def test_escalate_unresolved_escalates_and_halts_never_merges(_no_real_effects):
    """A deferred target that resolves to nothing must escalate (andon), not fail
    silently — and it merges nothing (there is nothing to merge)."""
    outcome = supervise.escalate_unresolved(card="my-card", path="/repo")
    assert outcome.verdict == "escalated"
    assert outcome.exit_code == 1
    assert outcome.halted == ("dep-card",)          # halted the card's dependents
    assert _no_real_effects["merges"] == []          # nothing merged
    assert any("no worker session found" in s for s in _no_real_effects["escalations"])


# --- cmd_supervise wiring for deferred targets --------------------------------


def _supervise_ns(**kw):
    base = dict(target=None, card=None, branch=None, path=None, probe=None)
    base.update(kw)
    return argparse.Namespace(**base)


def test_cmd_supervise_refuses_more_than_one_selector(capsys):
    assert cli.cmd_supervise(_supervise_ns(target="sess1", card="c")) == 2
    assert "exactly one" in capsys.readouterr().out


def test_cmd_supervise_refuses_no_selector(capsys):
    assert cli.cmd_supervise(_supervise_ns()) == 2
    assert "exactly one" in capsys.readouterr().out


def test_cmd_supervise_deferred_resolves_then_supervises(monkeypatch):
    ctx = _ctx()
    seen = {}

    def _resolve(**kw):
        seen["kw"] = kw
        return ctx

    def _supervise(c, probe=None):
        seen["ctx"] = c
        return supervise.SuperviseOutcome(verdict="verified", reason="ok")

    monkeypatch.setattr(cli.supervise, "resolve_deferred", _resolve)
    monkeypatch.setattr(cli.supervise, "supervise", _supervise)
    assert cli.cmd_supervise(_supervise_ns(card="my-card")) == 0
    assert seen["kw"]["card"] == "my-card" and seen["ctx"] is ctx


def test_cmd_supervise_deferred_no_match_escalates(monkeypatch, capsys):
    called = {}

    def _escalate(**kw):
        called["kw"] = kw
        return supervise.SuperviseOutcome(verdict="escalated", reason="no worker session found for card c")

    monkeypatch.setattr(cli.supervise, "resolve_deferred", lambda **kw: None)
    monkeypatch.setattr(cli.supervise, "escalate_unresolved", _escalate)
    assert cli.cmd_supervise(_supervise_ns(card="c")) == 1  # escalated → non-zero
    assert called["kw"]["card"] == "c"
    assert "escalated" in capsys.readouterr().out
