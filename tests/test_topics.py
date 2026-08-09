"""Tests for `.horus/topics/` — groupings that state their own purpose."""

from horus import backlog, backlog_tree, topics


def _topic(root, name, *, state="open", priority="medium", problem="Something hurts."):
    d = root / ".horus" / "topics"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.md").write_text(
        f"---\nstate: {state}\npriority: {priority}\n---\n\n"
        f"# {name} — a purpose\n\n## The problem\n\n{problem}\n\n"
        f"## What we are building\n\nThe thing.\n",
        encoding="utf-8",
    )


def _card(root, name, *, topic=None, status="open"):
    d = root / ".horus" / "backlog"
    d.mkdir(parents=True, exist_ok=True)
    lines = ["---", f"status: {status}"]
    if topic:
        lines.append(f"topic: {topic}")
    lines += ["type: feature", "---", "", f"# {name} — does a thing", ""]
    (d / f"{name}.md").write_text("\n".join(lines), encoding="utf-8")


def test_absent_directory_is_not_an_error(tmp_path):
    assert topics.load_topics(tmp_path) == []
    assert topics.findings(tmp_path, []) == []


def test_silent_until_a_project_opts_in(tmp_path):
    """A repo using neither topics nor the key must not be nagged — adopting is
    per-project, so the read-out has to stay quiet by default."""
    _card(tmp_path, "plain-card")
    assert topics.findings(tmp_path, backlog.load_cards(tmp_path)) == []


def test_loads_state_priority_and_purpose(tmp_path):
    _topic(tmp_path, "account-isolation", priority="high",
           problem="Isolation is nominal: a copied config leaks the shared home.")
    t, = topics.load_topics(tmp_path)
    assert t.name == "account-isolation"
    assert t.title.startswith("account-isolation")
    assert t.state == "open" and t.priority == "high"
    assert t.purpose == "Isolation is nominal: a copied config leaks the shared home."


def test_unknown_state_falls_back_to_open(tmp_path):
    """A malformed state must never be guessed into `settled` — that would hide a
    topic that still has work."""
    _topic(tmp_path, "t", state="whatever")
    assert topics.load_topics(tmp_path)[0].state == "open"


def test_missing_problem_heading_still_loads(tmp_path):
    d = tmp_path / ".horus" / "topics"
    d.mkdir(parents=True)
    (d / "sparse.md").write_text("---\nstate: open\n---\n\n# sparse\n\nprose\n", encoding="utf-8")
    t, = topics.load_topics(tmp_path)
    assert t.purpose == ""


def test_members_and_priority_sort(tmp_path):
    _topic(tmp_path, "b-topic", priority="high")
    _topic(tmp_path, "a-topic", priority="low")
    _card(tmp_path, "one", topic="b-topic")
    _card(tmp_path, "two", topic="b-topic")
    cards = backlog.load_cards(tmp_path)
    assert [c.name for c in topics.members(cards, "b-topic")] == ["one", "two"]
    assert topics.members(cards, "a-topic") == []
    ordered = sorted(topics.load_topics(tmp_path), key=topics.sort_key)
    assert [t.name for t in ordered] == ["b-topic", "a-topic"]  # high before low


def test_card_topic_reads_the_named_field_and_the_raw_record(tmp_path):
    _card(tmp_path, "c", topic="'quoted-topic'")
    card, = backlog.load_cards(tmp_path)
    assert card.topic == "quoted-topic"          # named field, quotes stripped
    assert topics.card_topic(card) == "quoted-topic"
    # A Card built without the field (as older callers do) still resolves via `fields`.
    bare = backlog.Card(
        path=card.path, name="x", status="open", priority="", tier="", created="",
        parallel="", surface=(), type="feature", vision_facet="", phase="converge",
        readiness="", readiness_reason="", autonomy="", last_refined="",
        shipped_pr="", shipped_sha="", shipped="", title="x",
        fields=(("topic", "from-fields"),),
    )
    assert topics.card_topic(bare) == "from-fields"


def test_dangling_topic_reference_warns(tmp_path):
    """A card naming a topic with no file loses its thesis silently — the one
    condition here that is a warn rather than advisory."""
    _card(tmp_path, "orphan", topic="ghost")
    findings = topics.findings(tmp_path, backlog.load_cards(tmp_path))
    assert any(f.level == "warn" and "ghost" in f.message for f in findings)


def test_open_settled_and_memberless_are_distinguished(tmp_path):
    _topic(tmp_path, "with-work", state="open")
    _topic(tmp_path, "stated-only", state="open")
    _topic(tmp_path, "answered", state="settled")
    _card(tmp_path, "w", topic="with-work")
    findings = topics.findings(tmp_path, backlog.load_cards(tmp_path))
    msgs = " | ".join(f.message for f in findings)
    assert "topics with open work — with-work (1)" in msgs
    assert "stated but not yet broken into cards — stated-only" in msgs
    assert "settled topic(s)" in msgs and "answered" in msgs
    assert not any(f.level in ("warn", "fail") for f in findings)


def test_shelved_cards_are_not_counted_as_ungrouped(tmp_path):
    """Shelved work is deliberately left on the old grouping, so it must not be
    reported as a problem to fix."""
    _topic(tmp_path, "t")
    _card(tmp_path, "live", topic="t")
    _card(tmp_path, "parked", status="shelved")
    findings = topics.findings(tmp_path, backlog.load_cards(tmp_path))
    assert not any("carry no topic" in f.message for f in findings)


def test_topic_lens_sections(tmp_path):
    _topic(tmp_path, "alpha", priority="high", problem="Alpha hurts.")
    _topic(tmp_path, "empty-one", priority="low")
    _card(tmp_path, "a1", topic="alpha")
    _card(tmp_path, "loose")
    cards = backlog.load_cards(tmp_path)
    sections = backlog_tree.sections_for(cards, "topic", root=tmp_path)
    labels = [s.label for s in sections]
    assert labels == ["alpha", "empty-one", "Ungrouped"]
    assert sections[0].subtitle == "Alpha hurts."
    # A member-less topic still renders: an empty column is the honest picture of a
    # direction stated but not broken down, and hiding it hides what matters.
    assert sections[1].children == []
    assert [c.name for c in sections[2].children] == ["loose"]


def test_settled_topics_are_marked_in_the_lens(tmp_path):
    _topic(tmp_path, "done-thinking", state="settled")
    sections = backlog_tree.sections_for(backlog.load_cards(tmp_path), "topic", root=tmp_path)
    assert sections[0].label == "done-thinking · settled"


def test_topic_lens_is_registered(tmp_path):
    assert "topic" in backlog_tree.GROUP_BY_LENSES
    assert backlog_tree.GROUP_BY_LABELS["topic"] == "Topic"
    # Additive: the facet lens and its default are untouched.
    assert backlog_tree.DEFAULT_GROUP_BY == "facet"
    assert "facet" in backlog_tree.GROUP_BY_LENSES


def test_topic_lens_without_a_root_degrades_to_ungrouped(tmp_path):
    """`sections_for` is called from surfaces that may not pass a root; it must not
    raise, and must not silently drop cards."""
    _card(tmp_path, "a", topic="alpha")
    cards = backlog.load_cards(tmp_path)
    sections = backlog_tree.sections_for(cards, "topic")
    assert [s.label for s in sections] == ["Ungrouped"]
    assert len(sections[0].children) == 1


def test_tree_projection_carries_topics_in_text_and_json(tmp_path):
    """`horus backlog --tree` and its `--json` both surface topics. The JSON keeps
    the full thesis; only the text line truncates it. (The first cut of this shipped
    a wrong helper name that the unit tests never touched — the CLI probe caught it,
    so the JSON path is asserted here.)"""
    import json
    _topic(tmp_path, "alpha", priority="high", problem="A " + "very " * 60 + "long problem.")
    _topic(tmp_path, "answered", state="settled")
    _card(tmp_path, "a1", topic="alpha")

    tree = backlog_tree.build_tree(tmp_path)
    assert [(g.topic, g.state, len(g.children)) for g in tree.topics] == [
        ("alpha", "open", 1), ("answered", "settled", 0),
    ]

    text = backlog_tree.render_text(tree)
    assert "alpha (1 open)" in text
    assert "answered · settled (0 open)" in text
    assert "(no member cards yet)" in text
    assert "…" in text  # the long purpose is truncated for the tree line

    data = json.loads(backlog_tree.render_json(tree))
    assert [t["topic"] for t in data["topics"]] == ["alpha", "answered"]
    assert len(data["topics"][0]["purpose"]) > 150  # full prose, untruncated
    assert data["topics"][0]["cards"][0]["name"] == "a1"
    # Additive: the pre-existing projection keys are untouched.
    assert "branches" in data and "facets" in data and "readiness" in data
