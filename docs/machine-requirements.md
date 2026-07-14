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
    probe: fab
    install: uv tool install fab
    needed_for: Fabric workspace operations
  - name: Power BI reader
    probe: pbir
    install: install pbir for this machine
    needed_for: report inspection
configs:
  - name: Power BI credentials
    probe: ~/.config/pbir/credentials.json
    install: configure pbir credentials
    needed_for: authenticated Power BI work
---

# Machine requirements

Access to the tenant is also required and cannot be probed automatically.
```

The frontmatter is intentionally narrow: `tools` and `configs` are lists whose
items use `name`, `probe`, `install`, and `needed_for` scalar fields.

Safety is structural:

- a tool `probe` is one executable name checked through the operating system's
  command lookup; it is never run;
- a config `probe` is a path existence check, with `~` and environment variables
  expanded; relative paths resolve from the project root;
- shell commands are rejected as invalid probes;
- non-probeable dependencies belong in the Markdown body as prose.
