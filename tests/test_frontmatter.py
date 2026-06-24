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
