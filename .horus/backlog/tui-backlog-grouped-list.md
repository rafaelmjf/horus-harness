---
status: open
priority: medium
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "The value + low-risk shape are clear; the group-by dimensions to ship first, default grouping, and in-group sort are open. Explore the grouping UX, then it's a small TUI build."
order: 30
phase: explore
type: feature
vision_facet: "Dashboard / cockpit"
---

# tui-backlog-grouped-list — collapsible group-by sections in the TUI backlog list

## Why — owner, 2026-07-21

The backlog is growing fast (68+ cards; this session alone added ~14), and the flat TUI
list is where it's felt. The current list is great for "start on a card now," poor for
"see the shape." The metadata to fix it already exists on every card (`readiness`,
`autonomy`, `vision_facet`/`branch`, `priority`, `phase`, `status`, `order`) — so grouping
is cheap on the data side; it surfaces structure already being maintained.

## What (the cheap, low-risk win — stage 1)

A configurable **group-by** on the existing list: collapsible section headers (with
per-group counts) generated from a chosen dimension — status, facet/branch, autonomy,
readiness, or priority. Same list, folded into groups. Works at **any width**;
phone/remote-control safe (no horizontal layout). The columns aren't sacred — the
*group-by lens* is; this is one rendering of it, the board is the other.

## Why this first (staging)

Stage 1 of the two-stage visualization idea; the bold stage is a true kanban board
(`tui-backlog-kanban-board`), whose success hinges on width-adaptive rendering. Grouped
list gets ~80% of the "see the shape" value with none of the geometry risk, ships
independently, and de-risks the board. Ordered **#3** (after `session-remote-control-default`
#1, `windows-native-horus-setup` #2).

## Open questions

- Which group-by dimensions ship first (status + facet likely); default grouping.
- In-group sort (priority? `order`?).
- Interaction with the existing card-open flow.
- Position vs `tui-backlog-refine-and-order` (refine/order surface) and
  `tui-vision-backlog-read-out` (read-out) — this is the *browse/visualise* surface;
  complement, don't duplicate.

## Non-goals

- Not the kanban board (that's `tui-backlog-kanban-board`).
- Not editing cards from the view — browse/visualise only.

## Source

In-session, 2026-07-21 (owner: backlog-visualisation need, validated by the session's own
card growth). Related: `tui-backlog-kanban-board`, `tui-backlog-refine-and-order`,
`tui-vision-backlog-read-out`.
