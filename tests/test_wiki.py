"""Tests for the experimental `horus wiki` read-model generator.

Covers the two pieces the spike must get right: entity extraction from imperfect
PRD markdown (bullet, numbered, bold-paragraph, qualified headings) and the two
cross-project link-detection paths (name mentions + explicit frontmatter lists),
plus the read-only / idempotence invariants against a small on-disk fixture fleet.
"""

from __future__ import annotations

from pathlib import Path

from horus import wiki

# A PRD whose Backlog mixes a bullet + a numbered list, whose Shipped uses the
# bold-paragraph shape (no bullets), and whose Rules heading carries a qualifier.
ALPHA_PRD = """---
status: active
current_focus: "wire alpha to beta"
next_action: "ship the beta bridge"
depends_on: "[[beta-svc]]"
---

# Alpha — PRD

## Vision

Alpha does things and leans on gamma-tool sometimes.

## Backlog

- **First item** with a wrapped
  continuation line that has no marker.
1. Second item as a numbered entry.
2. Third item mentioning gamma-tool inline.

## Shipped

One line per capability; details in git history.
**Bridge v1** shipped the first cut.
**Bridge v2** hardened it.

## Rules (load-bearing)

- **Rule one** is load-bearing.
- **Rule two** also.
"""

BETA_PRD = """---
status: active
current_focus: "serve alpha"
---

# beta-svc — PRD

## Backlog

- Nothing references anyone here.

## Shipped

- **Only** a plain bullet.

## Rules

- **Be nice.**
"""


def test_section_matches_qualified_heading():
    body = wiki.frontmatter.parse(ALPHA_PRD).body
    assert wiki._section(body, "Rules").strip().startswith("- **Rule one**")
    assert wiki._section(body, "Backlog")
    assert wiki._section(body, "Missing") == ""


def test_top_level_items_bullets_and_numbers():
    body = wiki.frontmatter.parse(ALPHA_PRD).body
    items = wiki._top_level_items(wiki._section(body, "Backlog"))
    assert len(items) == 3
    # Continuation line without a marker is not its own item.
    assert items[0] == "**First item** with a wrapped"
    assert items[1] == "Second item as a numbered entry."


def test_shipped_bold_paragraph_fallback():
    body = wiki.frontmatter.parse(ALPHA_PRD).body
    items = wiki._top_level_items(wiki._section(body, "Shipped"))
    # Non-bold preamble line is dropped; each bold entry is one item.
    assert items == ["**Bridge v1** shipped the first cut.", "**Bridge v2** hardened it."]


def test_extract_node_pulls_all_sections():
    node = wiki.extract_node("alpha", "/x/alpha", ALPHA_PRD, {"current_focus": "wire alpha to beta"})
    assert node.has_prd
    assert len(node.backlog) == 3
    assert len(node.shipped) == 2
    assert len(node.rules) == 2


def test_link_detection_mentions_and_explicit():
    alpha = wiki.extract_node("alpha", "/x/alpha", ALPHA_PRD, {"current_focus": "wire alpha to beta"})
    beta = wiki.extract_node("beta-svc", "/x/beta-svc", BETA_PRD, {"current_focus": "serve alpha"})
    gamma = wiki.extract_node("gamma-tool", "/x/gamma-tool", None, {})
    nodes = [alpha, beta, gamma]
    wiki.link_nodes(nodes, {"alpha": ALPHA_PRD, "beta-svc": BETA_PRD, "gamma-tool": None})

    # (a) mention: alpha's body names gamma-tool -> a mention edge.
    assert "mention" in alpha.links.get("gamma-tool", set())
    # (b) explicit: alpha's `depends_on: [[beta-svc]]` -> a depends_on edge.
    assert "depends_on" in alpha.links.get("beta-svc", set())
    # beta mentions "alpha" in its current_focus -> mention edge back to alpha.
    assert "mention" in beta.links.get("alpha", set())
    # No self-links.
    assert "alpha" not in alpha.links


def test_mention_does_not_match_substring():
    # "alpha" must not match inside "alphabet".
    node = wiki.extract_node("host", "/x/host", "# host\n\nWe love the alphabet.\n", {})
    other = wiki.extract_node("alpha", "/x/alpha", "# alpha\n", {})
    wiki.link_nodes([node, other], {"host": "We love the alphabet.", "alpha": "# alpha\n"})
    assert "alpha" not in node.links


def _write_fixture_fleet(tmp_path: Path) -> list[str]:
    paths = []
    for name, prd in (("alpha", ALPHA_PRD), ("beta-svc", BETA_PRD)):
        root = tmp_path / name
        (root / ".horus").mkdir(parents=True)
        (root / ".horus" / "PRD.md").write_text(prd, encoding="utf-8")
        paths.append(str(root))
    return paths


def test_generate_is_read_only_and_idempotent(tmp_path):
    project_paths = _write_fixture_fleet(tmp_path)
    sources = {
        p: (Path(p) / ".horus" / "PRD.md").read_text(encoding="utf-8") for p in project_paths
    }
    out = tmp_path / "wiki"

    written = wiki.generate(project_paths, out)
    assert (out / "index.md") in written
    assert (out / "projects" / "alpha.md") in written

    # Read-only: source PRDs are untouched.
    for p, original in sources.items():
        assert (Path(p) / ".horus" / "PRD.md").read_text(encoding="utf-8") == original

    # The generated alpha note shows the wikilink to beta-svc.
    alpha_note = (out / "projects" / "alpha.md").read_text(encoding="utf-8")
    assert "[[beta-svc]]" in alpha_note
    assert "do not edit" in alpha_note.lower()

    # Idempotent: a second run produces byte-identical files.
    snapshot = {p.read_text(encoding="utf-8"): p for p in out.rglob("*.md")}
    wiki.generate(project_paths, out)
    for content, p in snapshot.items():
        assert p.read_text(encoding="utf-8") == content


def test_six_lane_project_is_best_effort(tmp_path):
    root = tmp_path / "legacy"
    (root / ".horus").mkdir(parents=True)
    (root / ".horus" / "roadmap.md").write_text(
        "---\ncurrent_focus: legacy focus\n---\n# roadmap\n", encoding="utf-8"
    )
    nodes = wiki.load_nodes([str(root)])
    assert len(nodes) == 1
    assert nodes[0].has_prd is False
    note = wiki.render_project_note(nodes[0])
    assert "Six-lane" in note
