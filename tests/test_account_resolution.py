"""Resolving a human account name to exactly one configured account.

An account's real identity is (agent, alias): `personal` is one rate-limit pool
under claude and a different one under codex. But accounts.toml keys on the alias
(`personal`) while the isolated dir it maps to is named `claude-personal`, so every
surface that shows a config dir invites the wrong name.

That mismatch did real, silent damage on the owner's machine: split usage caches
(`usage-claude-claude-personal.json` beside `usage-claude-personal.json`, written
by different sessions), and an envelope created against a misspelled account would
have authorized nothing while looking perfectly correct.
"""

from __future__ import annotations

import pytest

from horus import config


@pytest.fixture
def accounts(monkeypatch):
    """The owner's real shape: aliases are bare, dirs are `<agent>-<alias>`."""
    def _set(claude=("personal", "work"), codex=()):
        monkeypatch.setattr(
            config, "load_account_config_dirs", lambda: {a: f"/x/claude-{a}" for a in claude}
        )
        monkeypatch.setattr(
            config, "load_account_codex_homes", lambda: {a: f"/x/codex-{a}" for a in codex}
        )
    _set()
    return _set


def _label(text, **kw):
    r = config.resolve_account(text, **kw)
    return r.ref.label if r.ok else None


# --- the spellings a human actually uses ------------------------------------


@pytest.mark.parametrize("spelling", [
    "claude work", "work claude acc", "claude-work", "claude_work", "CLAUDE WORK",
    "  claude   work  ", "work (claude)", "my claude work account", "claude work acc",
    "work claude",
])
def test_every_way_of_saying_claude_work(accounts, spelling):
    assert _label(spelling) == "claude-work"


@pytest.mark.parametrize("spelling", [
    "claude personal", "personal claude acc", "claude-personal", "personal acc (claude)",
    "personal", "Personal", "claude.personal", "the claude personal account",
])
def test_every_way_of_saying_claude_personal(accounts, spelling):
    assert _label(spelling) == "claude-personal"


def test_the_canonical_label_is_an_accepted_spelling(accounts):
    """`claude-personal` is what the isolated DIR is called, so it is the name that
    surfaces suggest — accept it rather than fight it."""
    for ref in config.known_accounts():
        assert _label(ref.label) == ref.label


def test_known_accounts_are_labelled_agent_first(accounts):
    accounts(claude=("personal", "work"), codex=("personal",))
    assert [r.label for r in config.known_accounts()] == [
        "claude-personal", "claude-work", "codex-personal",
    ]


# --- ambiguity is refused, never guessed ------------------------------------


def test_a_bare_alias_shared_by_two_agents_is_ambiguous(accounts):
    accounts(claude=("personal",), codex=("personal",))
    r = config.resolve_account("personal")
    assert not r.ok
    assert "ambiguous" in r.error
    assert "claude-personal" in r.error and "codex-personal" in r.error


def test_naming_the_agent_resolves_the_ambiguity(accounts):
    accounts(claude=("personal",), codex=("personal",))
    assert _label("claude personal") == "claude-personal"
    assert _label("codex personal") == "codex-personal"


def test_caller_context_resolves_the_ambiguity(accounts):
    """`horus run --agent codex --account personal` is not ambiguous."""
    accounts(claude=("personal",), codex=("personal",))
    assert _label("personal", agent="codex") == "codex-personal"
    assert _label("personal", agent="claude") == "claude-personal"


def test_an_explicit_agent_in_the_name_beats_caller_context(accounts):
    accounts(claude=("personal",), codex=("personal",))
    assert _label("codex personal", agent="claude") == "codex-personal"


# --- unknown names are refused with the real ones named ---------------------


def test_unknown_account_is_refused_and_names_the_real_ones(accounts):
    r = config.resolve_account("typo")
    assert not r.ok
    assert "unknown account 'typo'" in r.error
    assert "claude-personal, claude-work" in r.error


def test_a_wrong_agent_is_refused_not_silently_reassigned(accounts):
    """`codex personal` must not fall back to claude-personal just because that
    exists — that would route work to a different subscription."""
    r = config.resolve_account("codex personal")
    assert not r.ok
    assert "unknown account" in r.error


def test_empty_and_missing_names_are_refused(accounts):
    for text in (None, "", "   "):
        r = config.resolve_account(text)
        assert not r.ok and "no account named" in r.error


def test_noise_alone_does_not_resolve(accounts):
    assert not config.resolve_account("my account").ok


def test_no_configured_accounts_says_so_and_points_at_the_fix(accounts):
    accounts(claude=(), codex=())
    r = config.resolve_account("personal")
    assert not r.ok
    assert "no isolated accounts are configured" in r.error
    assert "horus account --set" in r.error


# --- multi-token aliases ----------------------------------------------------


def test_a_multi_token_alias_resolves(accounts):
    accounts(claude=("work-phone",))
    assert _label("work phone") == "claude-work-phone"
    assert _label("claude work phone") == "claude-work-phone"
    assert _label("claude-work-phone") == "claude-work-phone"


def test_token_order_does_not_matter(accounts):
    accounts(claude=("work-phone",))
    assert _label("phone work") == "claude-work-phone"


def test_a_partial_alias_does_not_resolve(accounts):
    """`work` must not silently become `work-phone`: half a name is not a name."""
    accounts(claude=("work-phone",))
    assert not config.resolve_account("work").ok


def test_an_alias_containing_an_agent_name_resolves_as_itself(accounts):
    """`work-codex` is an alias, not "work" plus a hint. The literal alias is tried
    before the agent word is read as context and stripped."""
    accounts(claude=(), codex=("work-codex",))
    assert _label("work-codex") == "codex-work-codex"
    assert _label("work_codex") == "codex-work-codex"


def test_an_alias_named_after_the_other_agent_still_resolves(accounts):
    accounts(claude=("codex",), codex=())
    assert _label("codex") == "claude-codex"
