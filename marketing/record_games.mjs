// Records the course games being played (no sound) for ads.
// Opens fidel-english.html in hidden Chrome at phone size (1080x1920), plays each game by itself
// (mostly right answers, sometimes wrong), and saves the frames as JPEGs + a list for ffmpeg.
//
// Usage: node marketing/record_games.mjs <page url> <out dir> [chrome.exe]
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const [URL_, OUT, CHROME = "C:/Program Files/Google/Chrome/Application/chrome.exe"] = process.argv.slice(2);
const PORT = 9333, wait = ms => new Promise(r => setTimeout(r, ms));
mkdirSync(OUT, { recursive: true });

// what to record: [name, seconds, JS that opens the game]
const CLIPS = [
  ["village", 14, `renderGameStart(); setTimeout(() => document.querySelector("#gPlay")?.click(), 300);`],
  ["boss",    12, `GAME_START.boss();`],
  ["zombie",  11, `GAME_START.zombie();`],
  ["bomb",    11, `GAME_START.bomb();`],
  ["alien",   10, `GAME_START.alien();`],
  ["pet",      8, `openPet(); setTimeout(() => { document.querySelector("[data-adopt]")?.click(); setTimeout(() => { document.querySelector("#pAdopt")?.click(); setTimeout(() => document.querySelector(".modal [data-mb]")?.click(), 700); }, 500); }, 500);`],
];

// set up a paid student with progress before the page loads
const SETUP = `try {
  const today = new Date(), ds = today.getFullYear()+"-"+(today.getMonth()+1)+"-"+today.getDate();
  const old = JSON.parse(localStorage.getItem("fidel-english-v1") || "{}");
  if (!old.profile) localStorage.setItem("fidel-english-v1", JSON.stringify({
    profile:{ name:"Abebe", method:"phone", contact:"+251900000000", avatar:"🦁", goal:10, remind:"", created:Date.now() },
    months:4, trialStart:Date.now(), level:"int", placed:true, streak:12, last:ds, nudged:ds, reminded:ds, month:2,
    games:{ lv:2 }, best:{}, speak:{}, wrong:{} }));
} catch(e){}`;

// plays by itself: answers about 85% right, presses start/next buttons
const AUTOPLAY = `(() => {
  if (window.__auto) return; window.__auto = true;
  const st = document.createElement("style"); st.textContent = "#toast{display:none!important}"; document.head.append(st);
  const orig = askQ; askQ = function(el, q, done, opt){ orig(el, q, done, opt); el.__q = q; el.__t = Date.now(); };
  const vis = b => b && b.offsetParent !== null && !b.disabled;
  setInterval(() => {
    if (document.querySelector(".modal")) { document.querySelector(".modal [data-mb]")?.click(); return; }
    // Save the Village: the right word for the hyena in front
    if (typeof GS !== "undefined" && GS && GS.target && GS.state === "play" && !GS.__busy){
      const want = GS.target.w[0], bs = [...document.querySelectorAll("#gOpts [data-i]")].filter(vis);
      if (bs.length){ GS.__busy = true; const g0 = GS; setTimeout(() => { g0.__busy = false; }, 900);
        const ok = Math.random() < .88, b = bs.find(x => (x.textContent === want) === ok) || bs[0]; b.click(); return; }
    }
    // question games
    for (const el of document.querySelectorAll("*")){
      if (!el.__q || Date.now() - el.__t < 1100) continue;
      const bs = [...el.querySelectorAll("[data-c]")].filter(vis); if (!bs.length) continue;
      const ok = Math.random() < .85, q = el.__q;
      const b = bs.find(x => (q.opts[+x.dataset.c] === q.a) === ok) || bs[0];
      el.__t = Date.now() + 99999; b.click(); return;
    }
    for (const id of ["#gPlay", "#bsNext", "#zGo", "#boGo"]){ const b = document.querySelector(id); if (vis(b)){ b.click(); return; } }
    const pick = [...document.querySelectorAll("[data-boss],[data-bi],[data-lv]")].find(vis); if (pick){ pick.click(); return; }
  }, 450);
})();`;

const chrome = spawn(CHROME, ["--headless=new", `--remote-debugging-port=${PORT}`, `--user-data-dir=${join(OUT, "_profile")}`,
  "--hide-scrollbars", "--mute-audio", "--window-size=432,768", "about:blank"], { stdio: "ignore" });
let ver; for (let i = 0; i < 50 && !ver; i++){ await wait(200); ver = await fetch(`http://127.0.0.1:${PORT}/json/version`).then(r => r.json()).catch(() => null); }
const tgt = await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: "PUT" }).then(r => r.json());
const ws = new WebSocket(tgt.webSocketDebuggerUrl);
await new Promise(r => ws.onopen = r);
let id = 0; const pending = new Map(), handlers = [];
ws.onmessage = m => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)){ pending.get(d.id)(d); pending.delete(d.id); } else handlers.forEach(h => h(d)); };
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const run = async js => (await send("Runtime.evaluate", { expression: js, awaitPromise: true, returnByValue: true })).result;

await send("Page.enable"); await send("Runtime.enable");
await send("Emulation.setDeviceMetricsOverride", { width: 432, height: 768, deviceScaleFactor: 2.5, mobile: true });
await send("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "dark" }] });
await send("Page.addScriptToEvaluateOnNewDocument", { source: SETUP });
await send("Page.navigate", { url: URL_ });
for (let i = 0; i < 100; i++){ await wait(300); const r = await run("typeof askQ === 'function' && typeof GAME_START === 'object'"); if (r && r.value) break; }
await wait(800);
await run(AUTOPLAY);

for (const [name, secs, js] of CLIPS){
  const dir = join(OUT, name); mkdirSync(dir, { recursive: true });
  await run(js); await wait(1200);
  const frames = []; let n = 0;
  const h = d => { if (d.method !== "Page.screencastFrame") return;
    const f = join(dir, `f${String(n++).padStart(5, "0")}.jpg`); writeFileSync(f, Buffer.from(d.params.data, "base64"));
    frames.push([f, d.params.metadata.timestamp]); send("Page.screencastFrameAck", { sessionId: d.params.sessionId }); };
  handlers.push(h);
  await send("Page.startScreencast", { format: "jpeg", quality: 88, maxWidth: 1080, maxHeight: 1920, everyNthFrame: 1 });
  await wait(secs * 1000);
  await send("Page.stopScreencast"); handlers.splice(handlers.indexOf(h), 1);
  // ffmpeg concat list with real frame times
  let list = "";
  frames.forEach(([f, t], i) => { const dur = i + 1 < frames.length ? frames[i + 1][1] - t : 0.05; list += `file '${f.replace(/\\/g, "/")}'\nduration ${Math.max(0.01, dur).toFixed(3)}\n`; });
  if (frames.length) list += `file '${frames[frames.length - 1][0].replace(/\\/g, "/")}'\n`;
  writeFileSync(join(dir, "list.txt"), list);
  console.log(name, frames.length, "frames");
}
ws.close(); chrome.kill();
process.exit(0);
