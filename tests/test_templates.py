"""Tests for the scaffolded Vision guidance."""

from horus import templates


WHY = """**Why this exists.** The originating problem, who it was built for, and — if the
project was forked, split, or pivoted — what it inherited **on purpose** and what
that inheritance is for. A reader must be able to tell deliberate inheritance from
legacy without asking."""

SURFACES = """**Surfaces and audiences.** Once a project has more than one entry point, name each
and say who it serves (human operator, agent, CI, consumer). When the product *is*
an interface, this is load-bearing: an unlabelled surface will be mistaken for the
contract."""


def test_prd_template_includes_the_vision_intent_and_audience_guidance():
    prd = templates.prd_md("example", "2026-07-26")

    assert WHY in prd
    assert SURFACES in prd


def test_managed_block_and_infer_routine_include_vision_intent_and_audiences():
    block = templates.shared_block("AGENTS.md")

    assert "**Why this exists.** The originating problem, who it was built for" in block
    assert "**Surfaces and audiences.** Once a project has more than one entry point" in block
    assert "**Why this exists.** The originating problem, who it was built for" in templates.INFER_PROMPT_V3
    assert "**Surfaces and audiences.** Once a project has more than one entry point" in templates.INFER_PROMPT_V3
    assert 'ask the owner for "why this exists"' in templates.INFER_PROMPT_V3
    assert "rather than distilling it from inherited docs" in templates.INFER_PROMPT_V3


PROCESS_NOT_MEMORY = """- **Fix a process error in the process, never only in agent memory** — a private memory
  is invisible to other agents, accounts, and machines, so the correction must land in a
  skill, managed block, PRD rule, or card. Concretely: render and confirm a format or
  contract change before merging it, rather than remembering to."""


def test_managed_block_carries_the_process_not_memory_discipline():
    # A correction to the PROCESS must live where every agent, account, and machine can
    # see it. This rung exists because a real one ("render-confirm before merging a
    # contract change") was written into one agent's private memory instead — invisible
    # to Codex and to every other account (owner rule, 2026-07-20).
    for target in ("AGENTS.md", "CLAUDE.md"):
        assert PROCESS_NOT_MEMORY in templates.shared_block(target)


def test_process_not_memory_discipline_stays_one_bullet():
    # This text loads in EVERY session, so the rung is capped at one bullet: the card
    # scoped it as "one tight line, not a paragraph".
    body = PROCESS_NOT_MEMORY.split("\n")
    assert len(body) == 4, "keep the rung short — it is loaded by every session"
    assert sum(1 for line in body if line.startswith("- ")) == 1
