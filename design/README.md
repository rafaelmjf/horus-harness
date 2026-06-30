# Handoff: Horus Dashboard Redesign

## Overview
Horus is a **local, single-user desktop companion** for coding-agent CLIs (Claude Code, Codex). It is a project-centric continuity & control panel: for each tracked repo it reads repo-local `.horus/` files (a six-lane continuity model — vision/focus, roadmap, features ledger, decisions, history, active execution plan) and renders them, plus account usage and a one-click way to launch an attended CLI session.

This package specifies a redesign of the dashboard, covering three surfaces: the **Projects overview (cockpit)**, the **Project detail page**, and **Settings**.

Two product values are baked into the design and must be preserved:
1. **Subscription auth only** — never display raw account emails/IDs, only friendly aliases.
2. **Deliberately lightweight** — minimal UI, minimal JS, fast.

## About the Design Files
`Horus Dashboard.html` is the design reference. **Unlike a typical handoff, this file was authored directly against the product's real technical constraints** (see below) and is intended to be **integrated into the existing server nearly as-is**, not re-implemented in a JS framework. Treat the HTML/CSS as the source of truth for both look and markup structure. The sample data is illustrative — wire the real `.horus/` data and account info into the same markup.

If you do choose to restructure (e.g. into Python templates / partials), preserve the exact CSS, class names, color tokens, and DOM structure so the rendered output is identical.

## Hard Technical Constraints (NON-NEGOTIABLE)
The page is server-rendered HTML from a **Python stdlib `http.server`** — the design honors all of these and your implementation must too:
- **No framework, no build step, no CDN, no external fonts or images.**
- **All styling lives in one inline `<style>` block.** System font stacks only (`-apple-system, "Segoe UI", Roboto, sans-serif`; mono `ui-monospace, Consolas`).
- **Near-zero JavaScript.** Only tiny vanilla snippets are allowed: the clipboard "copy" helper (`cp()`), and async-loading a panel via `fetch`. No client-side routing, no reactive components.
- **Interactive disclosure uses native `<details>`/`<summary>`.** Layout via flexbox/grid.
- **Single self-contained `.html` file**, droppable into the server. The mascot image is embedded as a base64 data-URI to satisfy "no external images".
- Palette is defined with **CSS custom properties** under `:root` (dark) and `.skin-light` (light) so it is trivial to retheme.

## Fidelity
**High-fidelity (hifi).** Final colors, typography, spacing, and interactions. Recreate/serve pixel-perfectly. Hex values, spacing, and behavior are all specified below and present in the file.

---

## Design Language

**Aesthetic:** sumi-e (Japanese ink wash) — **white/ink + shades of grey + a single red contrast**. The red (the "seal") is the falcon's gaze: it marks identity AND the single most important / attention-needing thing on screen. The brand is **Horus**, the Egyptian falcon god — watchful, calm presence.

**Color discipline (important):** the UI is intentionally near-monochrome. **Red is reserved** for: attention states (warnings, "artifacts outdated"), usage ≥80%, the "Refresh artifacts" action, the falcon identity (logo sun, the eye glyph), and links. Everything else is ink/grey shades. The **only** sanctioned non-red/grey colors are the two **account-provider chips** (Claude warm terracotta, Codex blue) — a deliberate brand-recognition exception, used nowhere else. **Green** appears in exactly one place: the "healthy" project status dot.

**Identity marks:**
- Header logo = a flat **red sun disc** (`.sun-mark`, hinomaru), NOT the mascot.
- A small geometric **Eye-of-Horus** SVG glyph (`.glyph`) appears red inside the "Next action" callout and the detail launch card.
- The **pixel-art falcon mascot** appears ONLY in a welcome popup shown on app open (`.welcome`), never in the chrome. (`assets/horus-mascot.png` is included; in the file it's an embedded base64 data-URI.)

---

## Design Tokens

Defined as CSS custom properties. Two themes: `:root` (dark, default) and `.skin-light` (light). Toggle is a pure-CSS checkbox (`#skin`) that adds `.skin-light` to `<body>`.

### Dark theme (`:root`)
| Token | Value | Use |
|---|---|---|
| `--bg` | `#15161a` | page ground |
| `--bg-2` | `#0e0f12` | command line bg, modal scrim |
| `--panel` | `#1d1e23` | cards / panels |
| `--panel-2` | `#191a1f` | inner / subtle surfaces, NEXT callout |
| `--raised` | `#26272d` | hover surfaces |
| `--border` | `#2f3036` | default hairline border |
| `--border-strong` | `#3e3f47` | stronger border, faint usage tier |
| `--hairline` | `#25262b` | dividers |
| `--ink` | `#eeeeef` | primary text, shipped marker |
| `--ink-2` | `#abacb2` | secondary text |
| `--ink-3` | `#7c7d84` | muted text, mid usage tier, in-progress marker |
| `--ink-faint` | `#5b5c62` | faintest text |
| `--seal` | `#df524a` | THE red — attention/identity/links |
| `--seal-strong` | `#c83f38` | red hover |
| `--seal-soft` | `rgba(223,82,74,.13)` | red wash bg |
| `--seal-line` | `rgba(223,82,74,.45)` | red border |
| `--go` | `#62b18c` | healthy status dot ONLY |
| `--go-soft` | `rgba(98,177,140,.13)` | healthy dot glow |
| `--claude` | `#d98a6a` | Claude provider chip only |
| `--codex` | `#7fb0e6` | Codex provider chip only |

### Light theme (`.skin-light`)
| Token | Value |
|---|---|
| `--bg` | `#f1f2f2` |
| `--bg-2` | `#e4e6e6` |
| `--panel` | `#ffffff` |
| `--panel-2` | `#f5f6f6` |
| `--raised` | `#ffffff` |
| `--border` | `#e3e5e5` |
| `--border-strong` | `#cdd0d0` |
| `--hairline` | `#edefef` |
| `--ink` | `#181a1a` |
| `--ink-2` | `#4d5252` |
| `--ink-3` | `#787d7d` |
| `--ink-faint` | `#9aa0a0` |
| `--seal` | `#d8362b` |
| `--seal-strong` | `#b62a20` |
| `--go` | `#2f8c5d` |
| `--claude` | `#bf5d39` |
| `--codex` | `#3f72a6` |

> Note: `--warn` / `--info` tokens still exist in the file for safety but the UI no longer uses amber, and `--info` is set equal to the red seal (links are red). Do not introduce amber.

### Radii / type / motion
- Radius: `--r-sm: 7px` (buttons, inputs), `--r-md: 11px` (callouts, small cards), `--r-lg: 16px` (panels, cards), `--r-pill: 999px` (badges, bars, rings).
- Spacing: 4px-based, generous. Card padding ~18px; panel padding 20px; section bands `padding: 22–30px 0`.
- Fonts: `--sans` system stack; `--mono` system monospace (branches, timestamps, file paths, commands).
- Type signature: **eyebrows** = 11px, `letter-spacing:.22em`, uppercase, `--ink-3`. Wordmark = uppercase, `letter-spacing:.36em`. Body 14.5px / line-height 1.5.
- Motion: `--t-fast: 140ms cubic-bezier(.4,0,.2,1)` (color/border), `--t-soft: 280ms cubic-bezier(.16,.84,.44,1)` (card lift). No bounces, no infinite loops.
- Shadows: `--shadow`, `--shadow-lift` (card hover) — soft, low, neutral.

### Usage color tiers (rings + weekly bars)
- **< 35%** → `--border-strong` (faint)
- **35–80%** → `--ink-3` (mid grey)
- **≥ 80%** → `--seal` (red)

### Feature ledger marker contrast (intentionally wide)
- **Shipped** → `--ink` (strongest)
- **In progress** → `--ink-3` (mid)
- **Planned** → `--border-strong` (lightest)

---

## Screens / Views

Routing between the three views is **pure CSS** via `:target` + `:has()` (no JS):
- `#overview` shows by default; `#detail` and `#settings` are hidden until targeted.
- `body:has(#detail:target) #overview { display:none }` etc. Nav tab active state is driven the same way.
- In the real app, the detail page would be its own server route; the single-file mock fakes it with anchors. Each project card links to `#detail`.

### 1. Header / nav (`header.top`, shared across views)
- Sticky, full-width, 64px tall, `--bg` at 86% with 12px backdrop blur, bottom hairline.
- Left: red sun disc `.sun-mark` (26px) + wordmark ("HORUS" uppercase wide-tracked + "project continuity & control panel" subtitle).
- Center: tabs **Projects** / **Settings** (active tab shows a red dot + `--ink` text).
- Right: pure-CSS theme toggle (`◗ Dark` / `◖ Light`).

### 2. Projects overview / cockpit (`#overview`)
Two-column page shell (`.ov-shell`): **300px left rail + 1fr main**, gap 30px. Below 1000px it stacks (rail on top).

- **Left rail (`.rail`, `position: sticky; top: 84px`)** — stays visible while the page scrolls. Contains the **Accounts** panel (`.acct-panel`, a collapsible `<details open>`):
  - In production this panel is **async-loaded via `fetch`** (placeholder comment in the markup: `<div id="accounts" data-src="/accounts">`).
  - Each account row (`.acct-c`): usage **ring** (SVG `<circle pathLength="100">` with `stroke-dasharray`), editable **alias** (an `<input>` styled as plain text; a small ✓ icon-button appears on hover/focus — implicit save), provider **chip** (Claude/Codex, brand-tinted), a small **`+`** session button, and a **weekly usage bar** (tiered color).
  - Footer: `+ Add account` and a `Remove an account` disclosure (`.remove-pop`) that reveals a menu listing each account with a remove action. Below the panel: the subscription-auth note.
- **Main column (`.ov-col`):**
  - **Greeting** (`.greet`): eyebrow "Cockpit", `<h2>` greeting, last-sync line; and a single **"Needs attention"** callout (`.attn-pill`, red) — the only KPI kept. Links to the project needing attention.
  - **"Under watch · Projects"** heading with meta "local projects · tracked on this machine".
  - **Project grid** (`.grid`, `repeat(auto-fill, minmax(372px, 1fr))`) of cards (see component below).
  - **GitHub remote catalog** and **Not tracked** — collapsible `<details class="fold">` sections.

#### Project card (`.pcard`)
- White/`--panel` card, `--r-lg`, hover = 2px lift + `--shadow-lift`. **The whole card is a click target** that opens the project: a stretched `<a class="card-link">` (absolute, `inset:0`, `z-index:0`) sits behind content (`z-index:1`); there is also a subtle **↗ open affordance** (`.pc-open`) in the header. **There is no big "Open project" button** (it was removed for being too loud/ambiguous).
- Header: project name (link), branch + last-activity (mono), and right-aligned **health dot** (`healthy` = green, `1 warning` = red, `planning` = grey) + ↗.
- Status line: neutral badges (`status active`, `N sessions`); attention badges in red (`⚠ artifacts outdated`, `N warnings`, `uncommitted`).
- **Next action callout** (`.next`): calm — `--panel-2` bg, `--border`, a **thin 3px red left rule** + a small red **eye glyph** + ink "NEXT ACTION" label. Body text + a "Recommended mode" line with an italic hint. Empty state (`.next.empty`) = dashed grey, no red. *This callout is deliberately NOT strongly colored — the red is just the rule + eye.*
- **Features summary** (`.feat`): a thin stacked bar (shipped/in-progress/planned in ink shades) + a legend with counts.
- Optional roadmap progress bar (`.roadprog`, grey fill).
- **Last session recap** (`.recap`) — mono timestamp + one paragraph; empty state is italic faint.
- Footer: **`Refresh artifacts`** button (red `.btn-warn`, only when relevant) and a **`Start a session`** disclosure (see launch UI). **No Offload control here** — offload lives on the detail page only.

### 3. Project detail page (`#detail`)
Two-column layout (`.dlayout`, `1fr 360px`, stacks below 1080px). Breadcrumb + title header (name, branch/status, health, badges) with a red **Refresh artifacts** and a **← Back**.

- **Main column (continuity story, top → bottom):**
  1. **Current focus** (`.horus/project.md`) — lead paragraph.
  2. **Roadmap · next** — the same calm NEXT callout + recommended mode + roadmap progress.
  3. **Features ledger** (`.horus/features.md`) — three buckets (Planned / In progress / Shipped) with counts and wide-contrast markers.
  4. **Decisions & history** — two lanes: durable decisions (dated rows) and a recent-history **timeline** (`.tline`).
  5. **Active execution plan** (`.horus/execution.md`) — phases table; status pills `done` (neutral), `active` (red, row highlighted), `planned` (outline).
- **Sidebar (sticky):**
  1. **Start a session** card (launch UI — see below).
  2. **Context cache** metrics — freshness, age, token overhead, lanes loaded (all neutral/ink).
  3. **Last session** summary + key/value details.
  4. **Manage Horus integration** — Refresh artifacts (red), "Stop tracking — keep `.horus/` files" (neutral), "Remove completely (delete .horus/)" (red `.btn-danger`).

### 4. Settings (`#settings`)
A simple form grid (`.settings-form`, `auto-fill minmax(300px, 1fr)`) of labeled `<select>` dropdowns for the workflow policy: default agent, permission posture, start mode, artifact-staleness threshold, context loading (lazy/eager), account-ID display (locked to "Friendly aliases only", disabled — enforces the product value), GitHub catalog refresh cadence, theme. Save (red `.btn-seal`) / Cancel.

---

## The launch UI ("Start a session")
Appears in card disclosures and the detail sidebar. Fields: **Agent** (Claude Code / Codex) and **Account** (alias) selects; on detail also **Permission posture**. Then **two intent buttons**:
- **▸ Resume — next action** (primary, ink-filled `.btn-go`) — resumes from the continuity handoff.
- **Fresh session** (neutral `.btn`) — starts clean.

The raw copyable launch command line was **removed** from this UI (it was redundant/noisy). The `cp()` clipboard helper remains in the file for any command-copy affordances you keep elsewhere.

---

## Interactions & Behavior
- **View routing:** CSS `:target` + `:has()`, no JS. Cards/links navigate via `href="#detail"`.
- **Theme toggle:** `#skin` checkbox toggles `.skin-light` on `<body>` (one-line inline `onclick`). Consider persisting via a server-side cookie/preference in production.
- **Disclosures:** native `<details>/<summary>` for Start-a-session, Offload/Remove, GitHub catalog, Not-tracked, account-remove menu, accounts panel.
- **Welcome popup:** `.welcome` is a fixed overlay shown on load (CSS-only via `#welcome` checkbox; "Enter the dashboard" label dismisses it). Holds the mascot. In production decide whether to show once per session.
- **Accounts panel:** async-loaded via `fetch` (see `data-src` placeholder).
- **Alias edit:** type in the inline input; a small ✓ icon-button (appears on hover/focus) commits.
- **Hover:** cards lift; buttons darken/translate 1px on press; the ↗ affordance fades in.
- **Clipboard copy:** `cp(btn)` writes `data-cmd` to clipboard and flips the label to "Copied ✓" for 1.4s.
- **Responsive:** rail/grid/detail layouts collapse to single column at 1000px / 1080px.

## State Management (server-side)
The server renders state from each repo's `.horus/` files and account data. Data needed per project: name, branch, dirty/clean, last-activity, status, session count, health, the six `.horus` lanes (focus, roadmap+next_action+recommended_mode, features by bucket, decisions, history, execution phases), artifact-staleness flag, context-cache freshness/age/token-overhead/lanes-loaded, last-session recap. Account data: alias, provider, current-window %, weekly %, reset timestamps. Settings: the workflow-policy fields. The Accounts strip is fetched separately (`/accounts`).

## Assets
- `assets/horus-mascot.png` — pixel-art falcon mascot, background removed to transparent (85×134). Embedded in the HTML as a base64 data-URI (welcome popup only). Provided by the user.
- All other graphics (sun disc, eye glyph, usage rings, falcon eye in footer) are **inline CSS/SVG** — no raster assets.
- Icons used are simple Unicode glyphs (↻ ▸ ↗ ✓ ⚠ ⎇ ✕ ◗ ◖). No icon font/CDN.

## Screenshots
In `screenshots/` (reference renders; note the preview width shows the responsive stacked layout — the accounts panel becomes a sticky 300px **left rail** at ≥1000px as described above):
- `01-overview-dark.png` — cockpit greeting, attention callout, project grid
- `02-accounts-rail-dark.png` — accounts panel (rings, brand chips, tiered usage bars)
- `03-detail-dark.png` — project detail top (focus + next action)
- `04-detail-launch-dark.png` — "Start a session" (two intent buttons) + context-cache metrics
- `05-settings-dark.png` — workflow-policy form
- `06-overview-light.png` — overview in the sumi-e light theme
- `07-detail-light.png` — detail in light theme

## Files
- `Horus Dashboard.html` — the complete, self-contained design (overview + detail + settings, both themes). This is the single source of truth.
- `assets/horus-mascot.png` — mascot (also embedded in the HTML).
- `screenshots/` — reference renders.
