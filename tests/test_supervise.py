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

from pathlib import Path

import pytest

from horus import notify, supervise


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
    monkeypatch.setattr(supervise, "halt_dependents", lambda root, card, reason: ["dep-card"])
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

    halted_cards = supervise.halt_dependents(Path("/repo"), "a", "red gate")
    assert set(halted_cards) == {"b", "c"}      # e is independent, fired-b skipped
    assert set(halted_ids) == {"s1", "s2"}


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
