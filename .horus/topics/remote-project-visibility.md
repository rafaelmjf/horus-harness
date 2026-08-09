---
state: open
priority: high
created: 2026-08-09
---

# remote-project-visibility — see the whole fleet without cloning it

## The problem

The daily cockpit reads **local clones**, so it can only show projects checked out on the machine you happen to be sitting at. Cloning every project to get an overview means carrying repositories you are not working on — dead weight on that machine.

This is not something the cockpit can grow into; reading the local filesystem is what it *is*.

Meanwhile every session ends by pushing, so remote genuinely knows the current state of every project. Almost nothing reads it: continuity fields are fetched, but branches are invisible and no backlog cards are read at all.

## What we are building

**A read-only view sourced from remote**, listing every project with its topics, feature branches and cards, without cloning anything.

Everything shown is a **projection over committed files** — never generated prose — so it cannot drift from the repository and cannot be confidently wrong. It states its own freshness on the face of it, per project, because a page that looks current while being stale is worse than one that admits its age.

Actuation stays out deliberately. No launching, no terminals, no writes: that half of the older cockpit went unused once tmux, herdr and ssh covered it, and it is what made the old surface compete with the cockpit instead of complementing it.
