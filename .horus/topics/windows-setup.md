---
state: open
priority: medium
created: 2026-08-09
---

# windows-setup — settle how this runs on Windows

## The problem

Horus runs on Windows and the install is current, so this is not a packaging gap. What is unresolved is the **recommendation**. Native Windows suits local project work, but session persistence — attaching to any running session from anywhere — is exactly the experience that degrades natively.

Without a settled answer, each new machine gets set up by improvisation.

## What we are building

**A confirmed split**: native Windows for local project work, WSL with tmux for persistence and attaching to sessions. Validated by running the cockpit under WSL end to end, rather than reasoned from documentation.
