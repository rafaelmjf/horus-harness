"""Tests for the minimal front-matter parser."""

from horus import frontmatter


def test_parses_quoted_and_bare_scalars():
    doc = frontmatter.parse(
        '---\n'
        'status: active\n'
        'current_focus: "Build the thing"\n'
        '---\n'
        '# Body\n\ntext\n'
    )
    assert doc.front_matter["status"] == "active"
    assert doc.front_matter["current_focus"] == "Build the thing"
    assert doc.body.startswith("# Body")


def test_no_front_matter_returns_full_body():
    doc = frontmatter.parse("# Just a doc\n\nno front matter")
    assert doc.front_matter == {}
    assert doc.body == "# Just a doc\n\nno front matter"


def test_unterminated_front_matter_is_treated_as_body():
    text = "---\nstatus: active\nstill going\n"
    doc = frontmatter.parse(text)
    assert doc.front_matter == {}
    assert doc.body == text


def test_colons_in_value_preserved():
    doc = frontmatter.parse('---\nsummary: "a: b: c"\n---\nbody\n')
    assert doc.front_matter["summary"] == "a: b: c"


# --------------------------------------------------------------------------- #
# resolve_focus — the PRD-first shared reader (structure v3 → v2 shim fallback)
# --------------------------------------------------------------------------- #

def _write_horus(root, rel, text):
    path = root / ".horus" / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


_PRD_FULL = (
    '---\n'
    'status: active\n'
    'current_focus: "PRD focus"\n'
    'next_action: "PRD next"\n'
    'next_prompt: "PRD prompt"\n'
    'execution_recommendation: "PRD exec"\n'
    'last_updated: 2026-07-03\n'
    '---\n# PRD\n'
)

_PROJECT_SHIM = '---\nstatus: shim\ncurrent_focus: "Shim focus"\nlast_updated: 2026-07-01\n---\n# P\n'
_ROADMAP_SHIM = (
    '---\nnext_action: "Shim next"\nnext_prompt: "Shim prompt"\n'
    'execution_recommendation: "Shim exec"\nlast_updated: 2026-07-01\n---\n# R\n'
)


def test_resolve_focus_prd_only(tmp_path):
    _write_horus(tmp_path, "PRD.md", _PRD_FULL)
    focus = frontmatter.resolve_focus(tmp_path)
    assert focus["current_focus"] == "PRD focus"
    assert focus["next_action"] == "PRD next"
    assert focus["next_prompt"] == "PRD prompt"
    assert focus["execution_recommendation"] == "PRD exec"
    assert focus["status"] == "active"
    assert focus["last_updated"] == "2026-07-03"


def test_resolve_focus_v2_shims_only(tmp_path):
    _write_horus(tmp_path, "project.md", _PROJECT_SHIM)
    _write_horus(tmp_path, "roadmap.md", _ROADMAP_SHIM)
    focus = frontmatter.resolve_focus(tmp_path)
    assert focus["current_focus"] == "Shim focus"
    assert focus["next_action"] == "Shim next"
    assert focus["next_prompt"] == "Shim prompt"
    assert focus["execution_recommendation"] == "Shim exec"
    assert focus["status"] == "shim"


def test_resolve_focus_prd_wins_per_field_with_shim_fallback(tmp_path):
    # Transitional v3: PRD carries only the focus; the rest still lives in shims.
    _write_horus(tmp_path, "PRD.md", '---\ncurrent_focus: "PRD focus"\n---\n# PRD\n')
    _write_horus(tmp_path, "project.md", _PROJECT_SHIM)
    _write_horus(tmp_path, "roadmap.md", _ROADMAP_SHIM)
    focus = frontmatter.resolve_focus(tmp_path)
    assert focus["current_focus"] == "PRD focus"  # PRD wins
    assert focus["next_action"] == "Shim next"  # per-field fallback
    assert focus["next_prompt"] == "Shim prompt"
    assert focus["execution_recommendation"] == "Shim exec"


def test_resolve_focus_current_focus_falls_back_to_roadmap(tmp_path):
    _write_horus(tmp_path, "roadmap.md", '---\ncurrent_focus: "Roadmap focus"\n---\n# R\n')
    assert frontmatter.resolve_focus(tmp_path)["current_focus"] == "Roadmap focus"


def test_resolve_focus_empty_when_nothing_exists(tmp_path):
    focus = frontmatter.resolve_focus(tmp_path)
    assert all(v == "" for v in focus.values())


def test_has_prd(tmp_path):
    assert not frontmatter.has_prd(tmp_path)
    _write_horus(tmp_path, "PRD.md", "# PRD\n")
    assert frontmatter.has_prd(tmp_path)
