# Research — prior-art guardrails

This folder is a **rail guard against reinventing tools that already exist.**

Horus is deliberately lightweight and continuity-first (see `.horus/decisions.md` and
the core-constraints). As the tool is refined, future feature ideas will naturally
drift — and some of that drift heads straight into territory a mature tool already
solves better (multi-agent orchestration, sandboxing, cross-tool rule projection, native
desktop shells, …).

Each entry here records a tool we evaluated, **where it overlaps Horus**, the **verdict**
(build / cede / interop / adopt), and — most importantly — a list of **drift triggers**:
concrete signals that you're about to build something this tool already does. When you
hit one, stop and reconsider: interop or adopt instead of reimplement.

This is evidence and reasoning. The *distilled rule* for each lives in
`.horus/decisions.md`; this folder holds the fuller analysis and sources behind it.

## How to use it

- **Before starting a substantial feature**, skim the drift-triggers below. If your idea
  matches one, read that entry before building.
- **After researching any new tool** (adopted, rejected, or interop target), add an entry
  here so the next drift is caught early.

## Index

| Tool | What it is | Verdict | Drift trigger (short) |
|---|---|---|---|
| [Omnigent](omnigent.md) | Databricks OSS meta-harness for agents | Cede orchestration; interop at the continuity boundary; not adopting now | Building a multi-harness orchestrator, live session cockpit, sandbox, multi-user collab, or cloud runner |
| [rulesync](rulesync.md) | Projects rules/skills/commands/MCP across 20+ agent tools | Stay direct at 2 tools; adopt at the 3rd | Building a generic rule/skill/MCP converter for a 3rd/4th agent tool |
| [pywebview](pywebview.md) | Python-native embedded webview window | Tried and **rejected** | Considering an embedded Python webview for the dashboard window |

## Entry template

```markdown
# <Tool>

- **What it is:**
- **Where it overlaps Horus:**
- **Verdict:** build / cede / interop / adopt — <one line>
- **Drift triggers:** (if you're about to build any of these, stop)
- **Notes / analysis:**
- **Sources:**
```
