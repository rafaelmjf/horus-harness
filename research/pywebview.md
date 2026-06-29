# pywebview

- **What it is:** A Python-native library for embedding a webview (WebView2 on Windows)
  in a desktop window — a candidate shell for showing the Horus dashboard as a real,
  owned, killable window instead of a browser tab.
- **Where it overlaps Horus:** the companion/app shell — the "proper window lifecycle +
  taskbar identity" goal (closing the window closes the app; no stale browser tabs).
- **Verdict:** **Tried and REJECTED (2026-06-26). Do not re-propose.** Live-tested
  unstable on Win11 (WinForms/WebView2 recursion crash) and slow (~4 s to a tab).
  Reverted to the lightweight shell: Edge `--app` / owned-window + Tk mascot. A real
  native window remains a **separate planned package** — but the stack to evaluate there
  is PySide6 / Electron / Tauri, **not** pywebview.

## Drift triggers — if you're about to do this, STOP

- Reaching for **pywebview** (or "just embed a Python webview") to fix the dashboard
  window lifecycle / taskbar identity → it was tried and failed; see `.horus/history.md`
  and the `horus-frontend-stack` memory.

→ For the window-lifecycle/taskbar goal: the shipped lightweight path is the owned Edge
`--app` window (reused/raised on click) + Tk mascot; the heavyweight path is a separate
native-app package (PySide6 / Electron / Tauri), evaluated on its own.

## Sources

- `.horus/decisions.md` "pywebview Tried and Rejected" + `.horus/history.md`. (Internal
  finding, no external source.)
