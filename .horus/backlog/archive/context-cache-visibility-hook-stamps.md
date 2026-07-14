---
status: retired
priority: later
tier: sonnet
created: 2026-07-10
---
> Retired 2026-07-14 (owner triage): context-cache visibility is already shipped in
> the dashboard/session surfaces. Hook-generation stamps have no observed downgrade
> failure; re-open that narrower guard only if content comparison actually regresses.

# Context-cache visibility + hook generation stamps

**Context-cache visibility:** how cold/expired sessions warn
(companion/launch/hook/dashboard). **Hook generation stamps:** version-mark
content-compared hook configs like the managed block if payloads change, else an old
CLI offers a downgrade "refresh".
