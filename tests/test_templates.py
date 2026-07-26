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
