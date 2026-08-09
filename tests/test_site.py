"""Tests for the static fleet site builder — fully offline via an injected fetcher."""

import json

from horus import site


def _fake_repo():
    """One repo's remote content: a PRD, two topics, three cards (one inactive, one
    untopiced) — enough to exercise every filter the reader applies."""
    files = {
        ".horus/PRD.md": "---\nstatus: active\n---\n\n# Proj — PRD\n\nA tool that does the thing.\n",
        ".horus/topics": ["alpha.md", "settled-one.md", "README.md", "notes.txt"],
        ".horus/topics/alpha.md": (
            "---\nstate: open\npriority: high\n---\n\n# alpha — purpose\n\n"
            "## The problem\n\nAlpha is broken in a measurable way.\n\n"
            "## What we are building\n\nA fix with rails.\n"
        ),
        ".horus/topics/settled-one.md": (
            "---\nstate: settled\npriority: low\n---\n\n# settled-one\n\n"
            "## The problem\n\nA question was open.\n\n"
            "## What was decided\n\nWe chose the second option.\n"
        ),
        ".horus/backlog": ["live.md", "parked.md", "loose.md"],
        ".horus/backlog/live.md": (
            "---\nstatus: open\ntopic: alpha\nreadiness: ready\ntype: feature\n---\n\n"
            "# live — does the useful thing\n"
        ),
        ".horus/backlog/parked.md": (
            "---\nstatus: shelved\ntopic: alpha\ntype: bug\n---\n\n# parked — not now\n"
        ),
        ".horus/backlog/loose.md": "---\nstatus: open\ntype: chore\n---\n\n# loose — no topic\n",
    }

    def fetch(full_name, path, ref):
        return files.get(path)

    return fetch


def _project(**kw):
    base = dict(name="proj", full_name="owner/proj", url="https://example/proj",
                default_branch="main", pushed_at="2026-08-09T10:00:00Z")
    base.update(kw)
    return site.SiteProject(**base)


def test_reads_topics_and_active_topiced_cards(tmp_path):
    p = site.read_project(_project(), fetch=_fake_repo())
    assert [t.name for t in p.topics] == ["alpha", "settled-one"]
    assert p.topics[0].problem == "Alpha is broken in a measurable way."
    assert p.topics[0].solution == "A fix with rails."
    # `## What was decided` is the settled variant of the solution heading.
    assert p.topics[1].state == "settled"
    assert p.topics[1].solution == "We chose the second option."
    # Only the active, topiced card survives: shelved is excluded, untopiced is
    # excluded (a card without a topic has no place on a topic page).
    assert [c.name for c in p.cards] == ["live"]
    assert p.cards[0].status == "Ready" and p.cards[0].summary == "does the useful thing"
    assert p.vision == "A tool that does the thing."


def test_non_markdown_and_readme_are_skipped(tmp_path):
    p = site.read_project(_project(), fetch=_fake_repo())
    assert all(not t.name.lower().startswith("readme") for t in p.topics)
    assert "notes" not in [t.name for t in p.topics]


def test_unreadable_backlog_still_yields_topics():
    """Partial data is kept — one broken path must not blank the whole project."""
    full = _fake_repo()

    def fetch(fn, path, ref):
        return None if path.startswith(".horus/backlog") else full(fn, path, ref)

    p = site.read_project(_project(), fetch=fetch)
    assert len(p.topics) == 2 and p.cards == []


def test_completely_unreadable_repo_is_empty_not_raising():
    p = site.read_project(_project(), fetch=lambda *a: None)
    assert p.topics == [] and p.cards == [] and p.vision == ""


def test_unknown_topic_state_falls_back_to_open():
    files = {".horus/topics": ["x.md"],
             ".horus/topics/x.md": "---\nstate: bogus\n---\n\n# x\n\n## The problem\n\nP.\n"}
    p = site.read_project(_project(), fetch=lambda fn, path, ref: files.get(path))
    assert p.topics[0].state == "open"


def test_pushed_at_gates_the_rebuild():
    p = _project(pushed_at="2026-08-09T10:00:00Z")
    assert site.needs_rebuild(p, None) is True                              # no prior
    assert site.needs_rebuild(p, {}) is True                                # empty prior
    assert site.needs_rebuild(p, {"pushed_at": "2026-08-09T10:00:00Z"}) is False
    assert site.needs_rebuild(p, {"pushed_at": "2026-08-08T09:00:00Z"}) is True
    # Malformed prior state rebuilds rather than serving stale data silently.
    assert site.needs_rebuild(p, {"pushed_at": ""}) is True
    assert site.needs_rebuild(_project(pushed_at=""), {"pushed_at": "x"}) is True


def test_json_carries_freshness_per_project():
    p = site.read_project(_project(read_at="2026-08-09T12:00:00Z"), fetch=_fake_repo())
    data = json.loads(site.to_json([p], generated_at="2026-08-09T12:00:00Z"))
    assert data["schema_version"] == 1
    assert data["generated_at"] == "2026-08-09T12:00:00Z"
    only, = data["projects"]
    # Both stamps are required: when the repo last moved, and when we last looked.
    assert only["pushed_at"] == "2026-08-09T10:00:00Z"
    assert only["read_at"] == "2026-08-09T12:00:00Z"
    assert [t["name"] for t in only["topics"]] == ["alpha", "settled-one"]


def test_load_previous_round_trips_and_tolerates_junk(tmp_path):
    assert site.load_previous(tmp_path) == {}          # absent
    (tmp_path / "fleet.json").write_text("not json", encoding="utf-8")
    assert site.load_previous(tmp_path) == {}          # unreadable → full rebuild
    p = site.read_project(_project(), fetch=_fake_repo())
    (tmp_path / "fleet.json").write_text(site.to_json([p], generated_at="t"), encoding="utf-8")
    prev = site.load_previous(tmp_path)
    assert prev["owner/proj"]["pushed_at"] == "2026-08-09T10:00:00Z"
    assert site.needs_rebuild(p, prev["owner/proj"]) is False
