"""Tests for the small Markdown-subset renderer."""

from horus import markdown


def test_headings_and_paragraphs():
    out = markdown.render("# Title\n\nSome text.")
    assert "<h2>Title</h2>" in out
    assert "<p>Some text.</p>" in out


def test_task_list_markers():
    out = markdown.render("- [x] done\n- [ ] todo\n- [~] partial")
    assert 'class="task done"' in out
    assert 'class="task todo"' in out
    assert 'class="task partial"' in out


def test_inline_code_and_fence():
    out = markdown.render("Use `horus init`.\n\n```\nraw\n```")
    assert "<code>horus init</code>" in out
    assert "<pre><code>" in out


def test_html_is_escaped():
    out = markdown.render("a <script>alert(1)</script> b")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_pipe_table_rendering():
    md = "| Capability | Notes |\n|---|---|\n| Bronze `ingest` | system of record |\n"
    out = markdown.render(md)
    assert "<table>" in out and "</table>" in out
    assert "<th>Capability</th>" in out
    assert "<td>system of record</td>" in out
    assert "<code>ingest</code>" in out  # inline code inside cells
    assert "|---|" not in out  # separator row consumed, not rendered


def test_non_table_pipes_are_not_tables():
    # A pipe line without a following separator row stays a paragraph.
    out = markdown.render("a | b and not a table")
    assert "<table>" not in out
