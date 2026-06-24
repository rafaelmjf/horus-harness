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
