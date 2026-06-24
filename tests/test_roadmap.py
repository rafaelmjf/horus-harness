"""Tests for roadmap task parsing, progress, and next-step derivation."""

from horus import roadmap

SAMPLE = """# Roadmap

## Now

- [x] done one
- [x] done two
- [~] in progress here
- [ ] open task

## Later

- [ ] much later
"""


def test_parse_tasks_states_and_sections():
    tasks = roadmap.parse_tasks(SAMPLE)
    assert len(tasks) == 5
    assert tasks[0] == roadmap.Task("done", "done one", "Now")
    assert tasks[2].state == "partial"
    assert tasks[4].section == "Later"


def test_progress():
    pr = roadmap.progress(roadmap.parse_tasks(SAMPLE))
    assert (pr.done, pr.total) == (2, 5)
    assert pr.pct == 40


def test_next_step_prefers_in_progress():
    ns = roadmap.next_step(roadmap.parse_tasks(SAMPLE))
    assert ns.text == "in progress here"
    assert ns.section == "Now"


def test_next_step_falls_back_to_first_open():
    body = "## Now\n- [x] done\n- [ ] first open\n- [ ] second open\n"
    ns = roadmap.next_step(roadmap.parse_tasks(body))
    assert ns.text == "first open"


def test_next_step_none_when_all_done():
    body = "- [x] a\n- [x] b\n"
    assert roadmap.next_step(roadmap.parse_tasks(body)) is None


def test_empty_roadmap():
    assert roadmap.parse_tasks("") == []
    assert roadmap.progress([]).pct == 0
    assert roadmap.next_step([]) is None
