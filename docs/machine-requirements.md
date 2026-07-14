# Project machine requirements

A project may commit `.horus/requirements.md` to describe tools and config files
that must exist on the current machine. The declaration is optional. When it is
present, the same read-only result appears in:

- `horus doctor project`;
- the beginning of `horus resume` prompts;
- the dashboard project badge and detail warning;
- the TUI project screen before its launch actions.

```markdown
---
kind: machine-requirements
tools:
  - name: Fabric CLI
    probe: fab --version
    install: uv tool install fab
    needed_for: Fabric workspace operations
  - name: Power BI reader
    probe: pbir --version
    install: install pbir for this machine
    needed_for: report inspection
configs:
  - name: Power BI credentials
    path: ~/.config/pbir/credentials.json
    install: configure pbir credentials
    needed_for: authenticated Power BI work
---

# Machine requirements

Access to the tenant is also required and cannot be probed automatically.
```

The frontmatter is intentionally narrow: `tools` and `configs` are lists. Tool
items use `name`, `probe`, `install`, and `needed_for`; config items use `path`
plus optional `name`, `install`, and `needed_for` scalar fields.

Safety is structural:

- a tool `probe` is an executable plus optional descriptive arguments; only the
  executable token is checked through the operating system's command lookup and
  the argv is never run;
- a config `path` is an existence check, with `~` and environment variables
  expanded; relative paths resolve from the project root;
- shell syntax is rejected as an invalid probe;
- non-probeable dependencies belong in the Markdown body as prose.
