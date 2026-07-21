---
status: open
priority: low
created: 2026-07-21
created_by: owner
last_refined: 2026-07-21
readiness: shaping
readiness_reason: "Just captured as a pain-point; scope open. Likely a feature of the self-hosted chat-app direction rather than standalone — explore before drafting."
phase: explore
type: feature
vision_facet: "Distribution"
---

# app-usage-cost-opacity — native apps meter usage but surface no cost/context/cache visibility or control

## Why — owner, 2026-07-21

The native Claude apps (desktop/mobile) **are** usage-metered — the 5h / 7d limits are
token-based under the hood — but unlike the terminal (Claude Code) they surface none of
it: no token/context readout, no cache-expiry "start fresh to save X" hint, no way to see
what a long conversation is costing against your limits. So re-warming an expired cache
and dragging a large context both draw down your 5h/7d budget **invisibly, with no lever
to optimise**. A real pain when living in the native apps for account-switch-friendly work.

(Corrects an earlier in-session read that the apps are "flat / unmetered" — they are
metered; the gap is *visibility + control*, not the absence of cost.)

## Why this can only be OUR layer

We established the native app is closed + sandboxed — we cannot add a readout to it. This
visibility is therefore only deliverable in a layer we own: the self-hosted #1 chat app,
where our own SDK/API calls let us count context size, cache state, and per-conversation
usage and offer a "start fresh" affordance. So this is concrete feature-value for the
chat-app direction, reinforcing *why* owning the session/token layer matters — not a
bolt-on to the native app.

## Open questions

- Purely a `horus-phone-chat-poc` / chat-app feature, or does any of it stand alone?
- What is actually observable from our own layer (token counts, cache hits) vs not?

## Source

In-session, 2026-07-21, from a prompt-caching-cost discussion. Related:
`horus-phone-chat-poc` (and its north star).
