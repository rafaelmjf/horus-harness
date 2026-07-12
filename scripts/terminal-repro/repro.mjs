// Headless-CDP repro/verification harness for the terminal sizing+lifecycle
// cluster (docs/terminal-mobile-desktop-diagnosis.md). Drives the REAL
// dashboard terminal markup/CSS/JS (served by server.py) with
// chrome-headless-shell over the raw DevTools Protocol — Node 22's built-in
// fetch/WebSocket, no npm deps, matching the original diagnosis session.
//
// Not part of the pytest/CI gate: needs a local Chromium/chrome-headless-shell
// binary this repo doesn't install in CI. Run:
//   python3 scripts/terminal-repro/server.py 8999 &
//   node scripts/terminal-repro/repro.mjs
//
// Exits non-zero (with a printed failure list) if any assertion fails.

import { spawn } from "node:child_process";
import { setTimeout as delay } from "node:timers/promises";

const CHROME = process.env.HORUS_CHS_BIN
  || "/home/rafa/.cache/ms-playwright/chromium_headless_shell-1228/chrome-headless-shell-linux64/chrome-headless-shell";
const SERVER_URL = process.env.HORUS_REPRO_URL || "http://127.0.0.1:8999";

const failures = [];
function check(name, cond, detail) {
  const ok = !!cond;
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail !== undefined ? "  " + JSON.stringify(detail) : ""}`);
  if (!ok) failures.push(name);
}

// --- minimal CDP client (flat sessions, no deps) ---------------------------
class CDP {
  constructor(ws) {
    this.ws = ws;
    this.nextId = 1;
    this.pending = new Map();
    this.listeners = [];
    ws.addEventListener("message", (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.id !== undefined && this.pending.has(msg.id)) {
        const { resolve, reject } = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) reject(new Error(JSON.stringify(msg.error)));
        else resolve(msg.result);
      } else if (msg.method) {
        for (const fn of this.listeners) fn(msg);
      }
    });
  }
  send(method, params = {}, sessionId) {
    const id = this.nextId++;
    const payload = { id, method, params };
    if (sessionId) payload.sessionId = sessionId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.ws.send(JSON.stringify(payload));
    });
  }
  onEvent(fn) {
    this.listeners.push(fn);
  }
}

async function wsConnect(url) {
  const ws = new WebSocket(url);
  await new Promise((resolve, reject) => {
    ws.addEventListener("open", resolve, { once: true });
    ws.addEventListener("error", reject, { once: true });
  });
  return ws;
}

// Overrides matchMedia('(pointer:coarse)') with a controllable fake, since
// CDP's Emulation.setEmulatedMedia does not flip pointer:coarse (confirmed in
// the original diagnosis session — doc Sec 2 footnote 1). Initial state comes
// from ?coarse=1 in the URL so it's set before the page's own scripts run.
const COARSE_OVERRIDE_SCRIPT = `
(function(){
  var real = window.matchMedia ? window.matchMedia.bind(window) : null;
  var listeners = [];
  var state = { matches: new URLSearchParams(location.search).get('coarse') === '1' };
  window.__horusSetCoarse = function(v){
    state.matches = !!v;
    listeners.slice().forEach(function(fn){ try{ fn({matches: state.matches}); }catch(e){} });
  };
  window.matchMedia = function(q){
    if(q === '(pointer:coarse)'){
      return {
        get matches(){ return state.matches; },
        media: q,
        addEventListener: function(type, fn){ if(type==='change'){ listeners.push(fn); } },
        removeEventListener: function(type, fn){ listeners = listeners.filter(function(x){ return x!==fn; }); },
        addListener: function(fn){ listeners.push(fn); },
        removeListener: function(fn){ listeners = listeners.filter(function(x){ return x!==fn; }); }
      };
    }
    return real ? real(q) : { matches:false, media:q, addEventListener:function(){}, removeEventListener:function(){} };
  };
})();
`;

async function main() {
  const proc = spawn(CHROME, [
    "--headless", "--disable-gpu", "--no-sandbox",
    "--remote-debugging-port=0", "--hide-scrollbars",
    "--user-data-dir=/tmp/horus-terminal-repro-profile",
  ], { stdio: ["ignore", "ignore", "pipe"] });

  const wsUrl = await new Promise((resolve, reject) => {
    let buf = "";
    proc.stderr.on("data", (chunk) => {
      buf += chunk.toString();
      const m = buf.match(/DevTools listening on (ws:\/\/\S+)/);
      if (m) resolve(m[1]);
    });
    proc.on("exit", (code) => reject(new Error(`chrome-headless-shell exited early (${code})`)));
    setTimeout(() => reject(new Error("timed out waiting for DevTools listener")), 10000);
  });

  const browserWs = await wsConnect(wsUrl);
  const browser = new CDP(browserWs);

  const { targetId } = await browser.send("Target.createTarget", { url: "about:blank" });
  const { sessionId } = await browser.send("Target.attachToTarget", { targetId, flatten: true });

  const cdp = browser; // same connection; commands take sessionId
  await cdp.send("Page.enable", {}, sessionId);
  await cdp.send("Runtime.enable", {}, sessionId);
  await cdp.send("Page.addScriptToEvaluateOnNewDocument", { source: COARSE_OVERRIDE_SCRIPT }, sessionId);

  async function evalJs(expression) {
    const { result, exceptionDetails } = await cdp.send("Runtime.evaluate", {
      expression, awaitPromise: true, returnByValue: true,
    }, sessionId);
    if (exceptionDetails) throw new Error(JSON.stringify(exceptionDetails));
    return result.value;
  }

  async function navigate(url) {
    const loaded = new Promise((resolve) => {
      const off = cdp.onEvent((msg) => {
        if (msg.method === "Page.loadEventFired" && msg.sessionId === sessionId) resolve();
      });
    });
    await cdp.send("Page.navigate", { url }, sessionId);
    await loaded;
  }

  async function setViewport({ width, height, mobile = false, deviceScaleFactor = 1 }) {
    await cdp.send("Emulation.setDeviceMetricsOverride", {
      width, height, deviceScaleFactor, mobile,
    }, sessionId);
  }

  async function stateResizes() {
    const s = await evalJs(`fetch('/__state').then(r=>r.json())`);
    return s.resizes;
  }
  async function lastResize(tid) {
    const resizes = await stateResizes();
    const forId = resizes.filter((r) => r.id === tid);
    return forId.length ? forId[forId.length - 1] : null;
  }

  try {
    // ---- Phase 1: desktop load posts the FITTED size, not xterm's 80x24 default ----
    await setViewport({ width: 1280, height: 900 });
    await navigate(`${SERVER_URL}/`);
    await delay(400);
    const r1 = await lastResize("pty-1");
    check("desktop load posts a real fit (not 80x24 default)", r1 && !(r1.cols === 80 && r1.rows === 24), r1);
    const hostBox1 = await evalJs(`(function(){var h=document.getElementById('x-pty-1');return {w:h.clientWidth,h:h.clientHeight};})()`);
    check("the fitted size is plausible for the host's actual box (not a stale unrelated value)",
      r1 && hostBox1.w > 0 && r1.cols >= Math.floor(hostBox1.w / 20) && r1.cols <= Math.ceil(hostBox1.w / 4),
      { resize: r1, hostBox: hostBox1 });

    // ---- Phase 2: ResizeObserver refits on a host-size change that ISN'T a window resize ----
    await evalJs(`document.querySelector('.term-pane[data-tid="pty-1"]').style.height='160px'; 0`);
    await delay(300);
    const r2 = await lastResize("pty-1");
    check("host-height change without a window resize DOES refit", r2 && r1 && r2.rows < r1.rows, { before: r1, after: r2 });

    // restore, confirm it recovers too
    await evalJs(`document.querySelector('.term-pane[data-tid="pty-1"]').style.height=''; 0`);
    await delay(300);
    const r2b = await lastResize("pty-1");
    check("host-height restored DOES refit back up", r2b && r2 && r2b.rows > r2.rows, { after_shrink: r2, after_restore: r2b });

    // a genuine window resize (not just the host-box path above) still refits too
    await setViewport({ width: 1900, height: 900 });
    await delay(300);
    const r2c = await lastResize("pty-1");
    check("a genuine window resize still refits (no regression)", r2c && r2b && r2c.cols > r2b.cols, { before: r2b, after: r2c });
    await setViewport({ width: 1280, height: 900 });
    await delay(300);

    // ---- Phase 3: scroll containment on the host ----
    const containment = await evalJs(`(function(){
      var cs = getComputedStyle(document.querySelector('.xterm-host'));
      return { overscrollBehavior: cs.overscrollBehavior, touchAction: cs.touchAction };
    })()`);
    check("xterm-host has overscroll-behavior containment", containment.overscrollBehavior === "contain", containment);
    check("xterm-host has a touch-action restricting page-drag leak", containment.touchAction !== "auto", containment);

    // ---- Phase 4: coarse-pointer load -> fullscreen engages, BOTH tabs reachable ----
    await setViewport({ width: 390, height: 844, mobile: true, deviceScaleFactor: 3 });
    await navigate(`${SERVER_URL}/?coarse=1`);
    await delay(400);
    const fsOn = await evalJs(`document.body.classList.contains('term-fs')`);
    check("coarse-pointer load auto-engages fullscreen", fsOn === true, fsOn);

    const miniHit = await evalJs(`(function(){
      var btn = document.querySelector('.term-mini[data-tid="pty-2"]');
      var r = btn.getBoundingClientRect();
      var el = document.elementFromPoint(r.left + r.width/2, r.top + r.height/2);
      return el === btn || btn.contains(el);
    })()`);
    check("in fullscreen, the OTHER session's mini-switcher tab is tappable (not covered)", miniHit === true, miniHit);

    const switched = await evalJs(`(function(){
      document.querySelector('.term-mini[data-tid="pty-2"]').click();
      return document.querySelector('.term-pane[data-tid="pty-2"]').classList.contains('active')
        && document.querySelector('.term-pane[data-tid="pty-2"]').classList.contains('fs');
    })()`);
    check("tapping the mini-switcher actually switches sessions in fullscreen", switched === true, switched);

    // ---- Phase 5: live matchMedia change re-evaluates (symptom 8: desktop-after-mobile) ----
    await setViewport({ width: 1280, height: 900, mobile: false, deviceScaleFactor: 1 });
    await delay(150);
    await evalJs(`window.__horusSetCoarse(false); 0`);
    await delay(200);
    const fsAfterDesktop = await evalJs(`document.body.classList.contains('term-fs')`);
    check("mobile->desktop transition on a live page drops fullscreen (no reload)", fsAfterDesktop === false, fsAfterDesktop);

    // ---- Phase 6: close guard - a live session needs a second tap ----
    const closeGuard = await evalJs(`(function(){
      var btn = document.querySelector('.termclose[data-tid="pty-2"]');
      btn.click();
      var textAfterFirst = btn.textContent;
      return { textAfterFirst: textAfterFirst };
    })()`);
    const closedAfterFirst = (await evalJs(`fetch('/__state').then(r=>r.json())`)).closed;
    check("first close-tap on a live session does NOT close it yet", !closedAfterFirst.includes("pty-2"), closedAfterFirst);
    check("first close-tap arms a 'tap again' confirmation", /tap again/i.test(closeGuard.textAfterFirst), closeGuard);
    const closedAfterSecond = await evalJs(`(function(){
      document.querySelector('.termclose[data-tid="pty-2"]').click();
      return fetch('/__state').then(r=>r.json()).then(function(s){ return s.closed; });
    })()`);
    check("second close-tap closes the live session", closedAfterSecond.includes("pty-2"), closedAfterSecond);

    // ---- Phase 7: pop-out prefers in-app fullscreen on touch (reversible, no window.open trap) ----
    await evalJs(`window.__openCalled = 0; window.open = function(){ window.__openCalled++; return null; }; 0`);
    await evalJs(`window.__horusSetCoarse(true); 0`);
    await delay(150);
    const popoutTouch = await evalJs(`(function(){
      document.querySelector('.popout[data-tid="pty-1"]').click();
      return { openCalled: window.__openCalled, fs: document.querySelector('.term-pane[data-tid="pty-1"]').classList.contains('fs') };
    })()`);
    check("pop-out on touch does NOT call window.open (no mobile new-tab trap)", popoutTouch.openCalled === 0, popoutTouch);
    check("pop-out on touch engages in-app fullscreen instead", popoutTouch.fs === true, popoutTouch);
  } finally {
    proc.kill();
  }

  console.log("\n" + (failures.length ? `${failures.length} FAILED: ${failures.join(", ")}` : "ALL PASSED"));
  process.exit(failures.length ? 1 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
