"use strict";
const TOKEN = window.TOKEN;
const $ = (id) => document.getElementById(id);
const log = $("log"), side = $("sidebody"), input = $("input");
const COMMANDS = [["Character", "#character"], ["Inventory", "#inventory"], ["Gear", "#gear"], ["Journal", "#journal"], ["Quests", "#quests"], ["Map", "#map"],
  ["Party", "#party"], ["Standing", "#standing"], ["Story", "#arc"],
  ["Dungeon", "#dungeon"], ["Home", "#home"], ["Shop", "#shop"], ["Stash", "#stash"], ["Board", "#board"], ["Help", "#help"], ["New game", "#newgame"]];

const state = { prompt: false, atMain: false, current: null, prefs: { pinned: "#character", width: 400, hidden: false, theme: "auto" } };

async function api(path, body) {
  try {
    const r = await fetch(path, { method: body === undefined ? "GET" : "POST", headers: { "X-Token": TOKEN, "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body) });
    return { ok: r.ok, data: await r.json().catch(() => ({})) };
  } catch (e) { return { ok: false, data: {} }; }
}

// ---------- text rendering (shared by the main panel and the side pane) ----------
let cur = null, lastBlank = true;
function nearBottom() { return log.scrollHeight - log.scrollTop - log.clientHeight < 80; }
const esc = (s) => s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
const RULE = /^\s*[═─━]{8,}\s*$/;
const BULLET = /^(?:[-•◆★✦✧⚔☼⚑!]|\d+\.)\s+/;
const BAR_NAME = { health: "--hp", hp: "--hp", mana: "--mp", mp: "--mp", stamina: "--sp", sp: "--sp" };

function decorate(body) {
  let h = esc(body);
  const bar = /^(\w+)\b/.exec(body);
  const color = bar && BAR_NAME[bar[1].toLowerCase()];
  h = h.replace(/([█▰]+)([░▱]*)/g, (m, f, e) => `<span class="barf" style="color:var(${color || "--accent"})">${f}</span><span class="bare">${e}</span>`);
  h = h.replace(/(^|[\s(;,])(#[a-z]+)/g, '$1<span class="cmd">$2</span>');
  h = h.replace(/⟦([^|⟧]+)\|([^⟧]*)⟧/g, '<span class="dmg" data-hit="$1">$2</span>');       // a blow's figure: hover for how it was worked out
  if (/^★/.test(body)) h = `<span class="legend">${h}</span>`;
  return h;
}
function lineEl(raw, mode, role) {
  const d = document.createElement("div");
  if (!raw.trim()) { d.className = "blank"; return d; }
  if (RULE.test(raw)) { d.className = "rule " + (raw.includes("═") ? "heavy" : "light"); return d; }
  const indent = raw.length - raw.trimStart().length, body = raw.trim();
  if (role === "title") { d.className = "h1"; d.textContent = body; return d; }
  if (mode === "pane") {
    const sec = /^──\s+(.*?)\s*─{2,}$/.exec(body);
    if (sec) { d.className = "h3"; d.textContent = sec[1]; return d; }
    if (indent === 0 && /^[A-Z][A-Z0-9 '’&\/\-]{2,}(\s.*)?$/.test(raw) && /^[A-Z][A-Z0-9 '’&\/\-]{2,}\b/.test(raw)) {
      const m = /^([A-Z][A-Z0-9 '’&\/\-]*[A-Z0-9])(\s.*)?$/.exec(raw);
      d.className = "h2"; d.innerHTML = esc(m[1]) + (m[2] ? `<span class="sub">${esc(m[2].trim())}</span>` : ""); return d;
    }
  }
  const mk = BULLET.exec(body);
  const hang = mk ? mk[0].length : indent >= 2 ? 2 : 0;
  d.className = "ln";
  d.style.paddingLeft = (indent + hang) + "ch";
  d.style.textIndent = (-hang) + "ch";
  d.innerHTML = decorate(body);
  return d;
}
function renderInto(el, text, mode, skipBlankRuns) {
  const lines = text.replace(/\n$/, "").split("\n");
  const inTitle = new Set();
  for (let i = 0, open = -1; i < lines.length; i++) {            // everything between two heavy rules is a title block
    if (!/^\s*═{8,}\s*$/.test(lines[i])) continue;
    if (open < 0) open = i; else { for (let j = open + 1; j < i; j++) inTitle.add(j); open = -1; }
  }
  lines.forEach((ln, i) => {
    const role = inTitle.has(i) && ln.trim() ? "title" : "";
    const blank = !ln.trim();
    if (skipBlankRuns) { if (blank && lastBlank) return; lastBlank = blank; }
    el.appendChild(lineEl(ln, mode, role));
  });
}
function addText(text, kind) {
  const stick = nearBottom();
  if (!cur || cur.dataset.kind !== kind) {
    cur = document.createElement("div"); cur.className = "blk k-" + kind; cur.dataset.kind = kind; log.appendChild(cur);
  }
  renderInto(cur, text, "main", true);
  if (stick) log.scrollTop = log.scrollHeight;
}
function addBlock(cls, text) {
  const stick = nearBottom();
  cur = null; lastBlank = true;
  const d = document.createElement("div"); d.className = cls; d.textContent = text; log.appendChild(d);
  if (stick) log.scrollTop = log.scrollHeight;
}

// ---------- shop panel: buy and sell buttons (they send hidden commands the game runs itself; no model call) ----------
const ATTR_MARK = "@@ATTRIBUTES@@";
let lastPanelCmd = null;
function el(tag, cls, text) { const d = document.createElement(tag); if (cls) d.className = cls; if (text !== undefined) d.textContent = text; return d; }
function shopButton(label, command, enabled, sure) {
  const b = el("button", "shopbtn", label);
  b.dataset.ok = enabled ? "1" : "";
  let armed = null;
  b.onclick = () => {
    if (sure && !armed) {                      // valuables take a second click
      b.textContent = "Sure?"; b.classList.add("on");
      armed = setTimeout(() => { armed = null; b.textContent = label; b.classList.remove("on"); }, 3000);
      return;
    }
    if (armed) clearTimeout(armed);
    runCommand(command);
  };
  return b;
}
async function runCommand(text) {
  if (!(state.prompt && state.atMain)) return;
  state.prompt = false; updateInput(); applyShopState();
  await api("/input", { text });
}
function applyShopState() {
  const live = state.prompt && state.atMain;
  document.querySelectorAll(".shopbtn").forEach((b) => { b.disabled = !(live && b.dataset.ok); });
}
function renderShop(d) {
  side.appendChild(el("div", "purse", "Purse: " + d.purse));
  for (const s of d.sellers) {
    const h = el("div", "h2", s.name.toUpperCase());
    if (s.buys.length) h.appendChild(el("span", "sub", "buys " + s.buys.join(", ")));
    side.appendChild(h);
    if (!s.wares.length) side.appendChild(el("div", "dimrow", "Nothing for sale."));
    for (const w of s.wares) {
      const row = el("div", "shoprow"), info = el("div", "info");
      info.appendChild(el("div", "nm", w.name));
      if (w.detail) info.appendChild(el("div", "dt", w.detail));
      if (w.note) info.appendChild(el("div", "warn", w.note));
      const buy = el("div", "act");
      buy.appendChild(el("div", "pr" + (w.afford ? "" : " poor"), w.price_text));
      buy.appendChild(shopButton("Buy", `#shopbuy ${w.kind} ${s.id} ${w.key}`, w.afford));
      row.append(info, buy); side.appendChild(row);
    }
  }
  side.appendChild(el("div", "h2", "SELL FROM YOUR PACK"));
  if (!d.sell.length) side.appendChild(el("div", "dimrow", "No one here wants anything you carry."));
  for (const x of d.sell) {
    const row = el("div", "shoprow"), info = el("div", "info");
    info.appendChild(el("div", "nm", x.name));
    info.appendChild(el("div", "dt", (x.detail ? x.detail + " · " : "") + "to " + x.buyer_name));
    const act = el("div", "act");
    act.appendChild(el("div", "pr", x.total_text));
    act.appendChild(shopButton("Sell", `#shopsell ${x.buyer} ${x.uid}`, true, x.legendary));
    row.append(info, act); side.appendChild(row);
  }
}

// ---------- gear panel: equip and unequip buttons, with a hover that compares the new piece to the one worn ----------
const tipMap = {};
function renderGear(d) {
  side.appendChild(el("div", "h2", "WORN"));
  for (const s of d.slots) {
    const row = el("div", "shoprow"), info = el("div", "info");
    const nm = el("div", "nm");
    nm.appendChild(el("span", "slotname", s.label));
    nm.appendChild(el("span", s.item ? (s.item.legendary ? "gname leg" : "gname") : "gname empty", s.item ? s.item.name : "--"));
    info.appendChild(nm);
    if (s.item && s.item.detail) info.appendChild(el("div", "dt", s.item.detail));
    if (!s.item && s.note) info.appendChild(el("div", "dt", "↳ " + s.note));
    row.appendChild(info);
    if (s.item) {
      const act = el("div", "act");
      act.appendChild(shopButton("Unequip", `#gearunequip ${s.slot}`, true));
      row.appendChild(act);
    }
    side.appendChild(row);
  }
  for (const line of d.sets || []) side.appendChild(el("div", "dimrow", line.trim()));
  side.appendChild(el("div", "h2", "CARRIED GEAR"));
  if (!d.carried.length) side.appendChild(el("div", "dimrow", "You carry nothing you could wear."));
  for (const x of d.carried) {
    const row = el("div", "shoprow"), info = el("div", "info");
    info.appendChild(el("div", "nm", x.name));
    info.appendChild(el("div", "dt", x.detail));
    if (!x.ok) info.appendChild(el("div", "warn", x.reason));
    row.dataset.tip = x.uid; tipMap[x.uid] = x.compare;
    const act = el("div", "act");
    const b = shopButton("Equip", `#gearequip ${x.uid}`, x.ok);
    if (!x.ok) { b.classList.add("locked"); b.title = x.reason; }
    act.appendChild(b); row.append(info, act); side.appendChild(row);
  }
}
function showLines(lines, x, y) {
  tip.textContent = "";
  for (const [cls, t] of lines) tip.appendChild(el("div", "tl " + cls, t));
  tip.hidden = false;
  const w = tip.offsetWidth, hh = tip.offsetHeight;
  tip.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, x - w - 16 > 8 ? x - w - 16 : x + 16)) + "px";
  tip.style.top = Math.max(8, Math.min(window.innerHeight - hh - 8, y - hh / 2)) + "px";
}
document.addEventListener("mouseover", (e) => {
  const t = e.target.closest && e.target.closest("[data-tip]");
  if (t && tipMap[t.dataset.tip]) showLines(tipMap[t.dataset.tip], e.clientX, e.clientY);
});

// ---------- map pane: the places you know as a diagram of walking times; drag to pan, wheel to zoom ----------
let mapView = null;
function renderMap(d) {
  const NS = "http://www.w3.org/2000/svg";
  const mk = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const here = d.nodes.find((n) => n.id === d.here);
  const pad = 70;
  const xs = d.nodes.map((n) => n.x), ys = d.nodes.map((n) => n.y);
  const box = { x: Math.min(...xs) - pad, y: Math.min(...ys) - pad, w: Math.max(...xs) - Math.min(...xs) + 2 * pad, h: Math.max(...ys) - Math.min(...ys) + 2 * pad };
  const keep = mapView && mapView.here === d.here ? mapView.box : null;
  const vb = keep || { x: box.x, y: box.y, w: Math.max(box.w, 240), h: Math.max(box.h, 240) };
  const svg = mk("svg", { class: "mapsvg", viewBox: `${vb.x} ${vb.y} ${vb.w} ${vb.h}` });
  const byId = Object.fromEntries(d.nodes.map((n) => [n.id, n]));
  for (const e of d.edges) {
    const a = byId[e.a], b = byId[e.b];
    const ln = mk("line", { x1: a.x, y1: a.y, x2: b.x, y2: b.y, class: "mapedge" + (a.state === "heard" || b.state === "heard" ? " dim" : "") }, svg);
    mk("title", {}, ln).textContent = `${a.name} - ${b.name}: ${e.label}`;
  }
  const big = { city: 9, town: 7, village: 6 };
  for (const n of d.nodes) {
    const g = mk("g", { class: "mapnode " + n.state }, svg);
    const r = big[n.type] || 5;
    mk("circle", { cx: n.x, cy: n.y, r: n.state === "here" ? r + 3 : r, class: "dot " + n.type }, g);
    if (n.state === "here") mk("circle", { cx: n.x, cy: n.y, r: r + 9, class: "pulse" }, g);
    const t = mk("text", { x: n.x, y: n.y - r - 5, "text-anchor": "middle", class: "lbl" }, g);
    t.textContent = n.name;
    mk("title", {}, g).textContent = n.state === "here" ? `${n.name} - you are here (${n.region})` : `${n.name} (${n.region}) - ${n.away} from here` + (n.state === "heard" ? " - heard of, not yet visited" : "");
  }
  let drag = null;
  svg.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, vb: { ...vb } }; svg.setPointerCapture(e.pointerId); });
  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    const k = drag.vb.w / svg.clientWidth;
    vb.x = drag.vb.x - (e.clientX - drag.x) * k; vb.y = drag.vb.y - (e.clientY - drag.y) * k;
    svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  });
  svg.addEventListener("pointerup", () => { drag = null; mapView = { here: d.here, box: { ...vb } }; });
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const f = e.deltaY > 0 ? 1.15 : 1 / 1.15, r = svg.getBoundingClientRect();
    const px = vb.x + ((e.clientX - r.left) / r.width) * vb.w, py = vb.y + ((e.clientY - r.top) / r.height) * vb.h;
    vb.x = px - (px - vb.x) * f; vb.y = py - (py - vb.y) * f; vb.w *= f; vb.h *= f;
    svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    mapView = { here: d.here, box: { ...vb } };
  }, { passive: false });
  side.appendChild(el("div", "dimrow", here ? (d.on_road ? `You are on the road, last in ${here.name}.` : `You are in ${here.name}.`) + ` Places you have only heard of are faint. Drag to move, scroll to zoom, hover for distances.` : ""));
  side.appendChild(svg);
}

// ---------- pulse pane (debug only): what the world pulse did this session ----------
let pulseFilter = "";
function renderPulse(d) {
  side.appendChild(el("div", "dimrow", `Now ${d.now}. Last pulse ${d.last}; next in ${d.next_in} min (every ${d.interval} min).`));
  const bar = el("div", "pulsebar");
  for (const k of ["", "thread", "stage", "end", "motive", "miss"]) {
    const b = el("button", pulseFilter === k ? "on" : "", k || "all");
    b.onclick = () => { pulseFilter = k; paintSide(); };
    bar.appendChild(b);
  }
  side.appendChild(bar);
  if (d.threads.length) { side.appendChild(el("div", "h2", "LIVE SITUATIONS")); for (const t of d.threads) side.appendChild(el("div", "fact", t)); }
  if (d.effects.length) { side.appendChild(el("div", "h2", "LIVE EFFECTS")); for (const t of d.effects) side.appendChild(el("div", "fact", t)); }
  side.appendChild(el("div", "h2", "LOG (newest first)"));
  const rows = d.rows.filter((r) => !pulseFilter || r.kind === pulseFilter);
  if (!rows.length) side.appendChild(el("div", "dimrow", "Nothing yet this session."));
  for (const r of rows) {
    const row = el("div", "prow pulse " + r.kind);
    row.appendChild(el("div", "pn", `${r.when} · ${r.kind}`));
    row.appendChild(el("div", "pr2", r.text));
    for (const e of r.effects) row.appendChild(el("div", "peff " + (e.result === "applied" ? "ok" : "no"), `${e.result === "applied" ? "✓" : "✗"} ${e.text}` + (e.result === "applied" ? "" : ` (${e.result})`)));
    side.appendChild(row);
  }
}

// ---------- party pane: companions (with a rename field) and hired adventurers ----------
function renderParty(d) {
  side.appendChild(el("div", "h2", "COMPANIONS"));
  if (!d.companions.length) side.appendChild(el("div", "dimrow", "You have no companions."));
  for (const m of d.companions) {
    const row = el("div", "shoprow party"), info = el("div", "info");
    const nm = el("div", "nm");
    nm.appendChild(el("span", m.ok ? "gname" : "gname empty", m.name));
    nm.appendChild(el("span", "slotname", `${m.role} · lv ${m.level}`));
    info.appendChild(nm);
    if (m.note) info.appendChild(el("div", "dt", m.note));
    info.appendChild(el("div", "dt", `${m.hp} health · ${m.damage} damage · ${m.armor} armor · ${m.ward} ward`));
    info.appendChild(el("div", m.ok ? "dt" : "warn", m.state));
    const edit = el("div", "renamebox");
    const input = el("input", "jsearch");
    input.type = "text"; input.maxLength = 24; input.placeholder = "New name…";
    const go = () => { const v = input.value.trim(); if (v) runCommand(`#compname ${m.id} ${v}`); };
    input.addEventListener("keydown", (e) => { if (e.key === "Enter") go(); });
    const b = shopButton("Rename", "", true);
    b.onclick = go;
    edit.append(input, b);
    info.appendChild(edit);
    row.appendChild(info); side.appendChild(row);
  }
  side.appendChild(el("div", "h2", "ADVENTURERS"));
  if (!d.adventurers.length) side.appendChild(el("div", "dimrow", "No hired adventurers."));
  for (const a of d.adventurers) {
    const row = el("div", "shoprow"), info = el("div", "info");
    info.appendChild(el("div", "nm", a.name));
    info.appendChild(el("div", "dt", `${a.role} · level ${a.level}`));
    row.appendChild(info); side.appendChild(row);
  }
  if (d.mode) side.appendChild(el("div", "dimrow", "They are " + d.mode + "."));
}

// ---------- character pane: a + beside each attribute while there are points to spend ----------
function renderAttrs(d) {
  const box = el("div", "attrs");
  for (const a of d.attrs) {
    const cell = el("div", "attr");
    cell.appendChild(el("span", "an", a.label));
    cell.appendChild(el("span", "av", String(a.value) + (a.bonus ? ` (+${a.bonus})` : "")));
    if (d.points > 0) cell.appendChild(shopButton("+", `#attradd ${a.key}`, true));
    box.appendChild(cell);
  }
  side.appendChild(box);
  for (const t of d.extra || []) side.appendChild(el("div", "dimrow", t));
  if (d.points > 0) side.appendChild(el("div", "pts", `${d.points} point${d.points === 1 ? "" : "s"} to spend`));
}

// ---------- journal pane: people grouped by town (here and last first) with a search over people and what you have learned ----------
let journalQuery = "";
function renderJournal(d) {
  const search = el("input", "jsearch");
  search.type = "search"; search.placeholder = "Search people and what you've learned…"; search.value = journalQuery;
  const body = el("div", "jbody");
  side.append(search, body);
  const draw = () => {
    const q = journalQuery.trim().toLowerCase();
    body.textContent = "";
    body.appendChild(el("div", "h2", "PEOPLE YOU'VE MET"));
    let shown = 0;
    for (const g of d.groups) {
      const people = g.people.filter((p) => !q || `${p.name} ${p.role} ${p.place} ${g.town} ${p.line}`.toLowerCase().includes(q));
      if (!people.length) continue;
      const h = el("div", "town", g.town);
      if (g.tag) h.appendChild(el("span", "tag", g.tag));
      body.appendChild(h);
      for (const p of people) {
        const row = el("div", "prow");
        row.appendChild(el("div", "pn", p.name));
        row.appendChild(el("div", "pr2", p.line));
        body.appendChild(row); shown++;
      }
    }
    if (!shown) body.appendChild(el("div", "dimrow", q ? "No one matches." : "No one yet."));
    const heard = (d.heard || []).filter((p) => !q || `${p.name} ${p.by} ${p.line}`.toLowerCase().includes(q));
    if (heard.length) {
      body.appendChild(el("div", "h2", "PEOPLE YOU'VE HEARD OF"));
      for (const p of heard) {
        const row = el("div", "prow heard");
        row.appendChild(el("div", "pn", p.name));
        row.appendChild(el("div", "pr2", `Mentioned by ${p.by}: "${p.line}"`));
        body.appendChild(row);
      }
    }
    body.appendChild(el("div", "h2", "THINGS YOU'VE LEARNED"));
    const facts = d.facts.filter((f) => !q || f.toLowerCase().includes(q));
    if (!facts.length) body.appendChild(el("div", "dimrow", q ? "Nothing matches." : "Nothing yet."));
    for (const f of facts) body.appendChild(el("div", "fact", f.replace(/\s+/g, " ")));
    const hist = d.history.filter((f) => !q || f.toLowerCase().includes(q));
    if (hist.length) {
      body.appendChild(el("div", "h2", "ITEMS DELIVERED OR LET GO"));
      for (const f of hist) body.appendChild(el("div", "fact", f));
    }
  };
  search.oninput = () => { journalQuery = search.value; draw(); };
  draw();
}

// ---------- side pane ----------
let sideRaw = "", sidePanel = null, lastView = null;
const combat = { active: false, data: null, rows: [], seen: new Set(), mode: "view" };
const hitsMap = {};
function renderButtons() {
  const box = $("buttons"); box.textContent = "";
  for (const [label, cmd] of (state.debug ? [...COMMANDS, ["Pulse", "#pulse"]] : COMMANDS)) {
    const b = document.createElement("button");
    b.textContent = label + (state.prefs.pinned === cmd ? " 📌" : "");
    b.dataset.cmd = cmd;
    b.className = state.current === cmd ? "on" : "";
    b.disabled = !(state.prompt && state.atMain);
    b.onclick = () => runView(cmd);
    box.appendChild(b);
  }
  if (combat.active) {
    const b = document.createElement("button");
    b.textContent = "⚔ Combat"; b.className = combat.mode === "combat" ? "on" : "";
    b.onclick = () => { combat.mode = "combat"; paintSide(); };
    box.insertBefore(b, box.firstChild);
  }
  const pin = $("pin");
  pin.classList.toggle("on", !!state.current && state.prefs.pinned === state.current);
  pin.textContent = state.current && state.prefs.pinned === state.current ? "📌 Pinned" : "📌 Pin";
  pin.disabled = !state.current;
}
async function runView(cmd) {
  if (!(state.prompt && state.atMain)) return;
  combat.mode = "view";
  state.prompt = false; updateInput();
  await api("/input", { text: cmd });
}
async function setPrefs(p) {
  Object.assign(state.prefs, p);
  await api("/prefs", p);
  renderButtons();
}
$("pin").onclick = async () => {
  if (!state.current) return;
  const unpin = state.prefs.pinned === state.current;
  const cmd = unpin ? null : state.current;
  await api("/pin", { command: cmd });
  await setPrefs({ pinned: cmd });
};

// ---------- pane layout (width + hidden are remembered) ----------
function applyTheme() {
  const t = state.prefs.theme;
  if (t === "auto") document.documentElement.removeAttribute("data-theme"); else document.documentElement.setAttribute("data-theme", t);
  $("theme").textContent = "◐ " + t[0].toUpperCase() + t.slice(1);
}
$("theme").onclick = () => {
  const next = { auto: "dark", dark: "light", light: "auto" }[state.prefs.theme] || "auto";
  state.prefs.theme = next; applyTheme(); setPrefs({ theme: next });
};
function applyLayout() {
  applyTheme();
  $("side").style.width = state.prefs.width + "px";
  document.body.classList.toggle("pane-hidden", !!state.prefs.hidden);
  $("show").hidden = !state.prefs.hidden;
}
$("hide").onclick = () => { state.prefs.hidden = true; applyLayout(); setPrefs({ hidden: true }); };
$("show").onclick = () => { state.prefs.hidden = false; applyLayout(); setPrefs({ hidden: false }); };
$("grip").addEventListener("pointerdown", (e) => {
  e.preventDefault();
  const move = (ev) => {
    state.prefs.width = Math.max(240, Math.min(900, window.innerWidth - ev.clientX));
    $("side").style.width = state.prefs.width + "px";
  };
  const up = () => { window.removeEventListener("pointermove", move); window.removeEventListener("pointerup", up); setPrefs({ width: state.prefs.width }); };
  window.addEventListener("pointermove", move); window.addEventListener("pointerup", up);
});

// ---------- input ----------
const history = []; let hpos = 0;
function updateInput() {
  input.disabled = !state.prompt;
  $("send").disabled = !state.prompt;
  if (state.prompt) input.focus();
  renderButtons(); applyShopState();
}
$("form").onsubmit = async (e) => {
  e.preventDefault();
  const text = input.value.trim();
  if (!state.prompt) return;
  input.value = "";
  if (text) { history.push(text); hpos = history.length; }
  state.prompt = false; updateInput();
  const r = await api("/input", { text });
  if (!r.ok) { state.prompt = true; updateInput(); }
};
input.addEventListener("keydown", (e) => {
  if (e.key === "ArrowUp" && history.length) { hpos = Math.max(0, hpos - 1); input.value = history[hpos] || ""; e.preventDefault(); }
  if (e.key === "ArrowDown" && history.length) { hpos = Math.min(history.length, hpos + 1); input.value = history[hpos] || ""; e.preventDefault(); }
});

// ---------- Strip: the fixed status strip (self-contained; remove this section, #strip and .strip rules to cut it) ----------
const Strip = (() => {
  const el = $("strip");
  const bar = (name, v, color) => {
    const [now, top] = v || [0, 1];
    const pct = top ? Math.max(0, Math.min(100, (100 * now) / top)) : 0;
    return `<div class="bar"><b>${name}</b><div class="track"><div class="fill" style="width:${pct}%;background:var(${color})"></div></div><span class="num">${now}/${top}</span></div>`;
  };
  return {
    update(s) {
      el.innerHTML = `<div class="row"><span><b>${esc(s.when)}</b></span><span>${esc(s.weather)}</span><span>${esc(s.place)}</span>
        <span class="grow"><span>LV <b>${s.level}</b></span><span>PTS <b>${s.points}</b></span><span>${esc(s.coins)}</span></span></div>
        <div class="row">${bar("HP", s.vitals.health, "--hp")}${bar("MP", s.vitals.mana, "--mp")}${bar("SP", s.vitals.stamina, "--sp")}${bar("XP", s.xp, "--xp")}</div>
        <div class="where" title="${esc(s.spot)}">${esc(s.spot)}</div>`;
    },
  };
})();

// ---------- how a blow was worked out (the hover text) ----------
const tip = el("div", "tip"); tip.hidden = true; document.body.appendChild(tip);
function hitLines(h) {
  const L = [], b = h.base || {}, d = h.defence || {};
  const outcome = { miss: "miss", graze: "glancing blow", hit: "hit", crit: "critical hit", phase: "passes through" }[h.outcome] || h.outcome;
  L.push(["h", `${h.att} ${h.label} ${h.dfn}`]);
  if (h.chance) L.push(["", `To hit: needed ${h.need} or more (${h.chance}% chance), rolled ${h.roll} → ${outcome}`]);
  if (h.chance && h.crit_need < 100 && h.outcome !== "phase") L.push(["dim", `Critical on ${h.crit_need} or more (${h.crit}%)`]);
  else L.push(["", `Result: ${outcome}`]);
  if (h.note) L.push(["dim", h.note]);
  if (h.outcome === "miss" || h.outcome === "phase") return L;
  if (b.base !== undefined) {
    const spell = b.kind === "spell", chan = b.kind === "channel";
    const parts = (b.parts || []).map(([n, v]) => `${n} ${v}`).join(" + ");
    let s;
    if (spell) s = `Base: ${parts}`;
    else s = `Base: ${chan && parts ? parts : `weapon ${b.weapon}`} + attribute ${b.attr}×${(b.attr_bonus / (b.attr || 1)).toFixed(2)} = ${b.attr_bonus}`;
    if (b.flat) s += ` + gear ${b.flat}`;
    L.push(["", s + `  =  ${b.base}`]);
    for (const [name, f] of h.steps || []) L.push(["", `  × ${f}  ${name}`]);
    if (b.pct) L.push(["", `  × ${(1 + b.pct / 100).toFixed(2)}  damage bonuses (+${b.pct}%)`]);
    if (spell) L.push(["", `  × ${b.magic}  spell attribute ${b.attr} (+${Math.round((b.magic - 1) * 100)}%)`]);
    else if (chan) L.push(["dim", `  (the spell part already includes × ${b.spell_mult} from your spell attribute)`]);
    L.push(["", `  × ${b.variance}  ${spell ? "the spell's variance" : chan ? "the strike's variance" : "the swing's variance"}`]);
    L.push(["", `Raw damage: ${b.total}`]);
  }
  if (d.reduction !== undefined) {
    L.push(["", `Defence (${d.kind}): protection ${d.protection}`]);
    for (const [name, v] of d.cuts || []) L.push(["", `  − ${v}  ${name}`]);
    if (!(d.cuts || []).length) L.push(["", "  nothing absorbed"]);
    L.push(["", `Taken after defence: ${d.after}`]);
  }
  for (const [name, v] of h.extras || []) L.push(["", `  ${name}: ${v}`]);
  L.push(["h", `Dealt: ${h.final}`]);
  return L;
}
function showTip(h, x, y) {
  tip.textContent = "";
  for (const [cls, t] of hitLines(h)) tip.appendChild(el("div", "tl " + cls, t));
  tip.hidden = false;
  const w = tip.offsetWidth, hh = tip.offsetHeight;
  tip.style.left = Math.max(8, Math.min(window.innerWidth - w - 8, x - w / 2)) + "px";
  tip.style.top = (y - hh - 14 < 8 ? y + 20 : y - hh - 14) + "px";
}
document.addEventListener("mouseover", (e) => {
  const t = e.target.closest && e.target.closest("[data-hit]");
  const h = t && hitsMap[t.dataset.hit];
  if (h) showTip(h, e.clientX, e.clientY);
  else if (!(e.target.closest && e.target.closest("[data-tip]"))) tip.hidden = true;
});
document.addEventListener("mousemove", (e) => {
  const t = e.target.closest && e.target.closest("[data-hit]");
  if (t && hitsMap[t.dataset.hit] && !tip.hidden) showTip(hitsMap[t.dataset.hit], e.clientX, e.clientY);
});

// ---------- combat pane ----------
function onCombat(d) {
  if (!combat.active) { combat.active = true; combat.rows = []; combat.seen = new Set(); }
  combat.data = d; combat.mode = "combat";
  for (const h of d.hits || []) {
    hitsMap[h.id] = h;
    if (!combat.seen.has(h.id)) { combat.seen.add(h.id); combat.rows.push(h); }
  }
  state.current = null; $("sidetitle").textContent = "";
  paintSide();
}
function bar(now, top, color) {
  const pct = top ? Math.max(0, Math.min(100, (100 * now) / top)) : 0;
  const t = el("div", "cbar"), f = el("div", "cfill"); f.style.width = pct + "%"; f.style.background = `var(${color})`;
  t.appendChild(f); return t;
}
function fighterBlock(x, isYou) {
  const box = el("div", "cf" + (isYou ? " you" : ""));
  const head = el("div", "cfh");
  head.appendChild(el("span", "cn", isYou ? "You" : `${x.name} (lv ${x.level})`));
  if (!isYou) { head.appendChild(el("span", "band", x.band)); head.appendChild(el("span", "chp", `${x.hp}/${x.max_hp}`)); }
  box.appendChild(head);
  const row = (lbl, now, top, color) => { const r = el("div", "crow"); r.append(el("span", "lbl", lbl), bar(now, top, color), el("span", "num", `${now}/${top}`)); box.appendChild(r); };
  if (isYou) {
    row("HP", x.hp, x.max_hp, "--hp");
    if (x.max_stamina) row("ST", x.stamina, x.max_stamina, "--sp");
    if (x.max_mana) row("MP", x.mana, x.max_mana, "--mp");
  } else box.appendChild(bar(x.hp, x.max_hp, "--hp"));
  const chips = el("div", "chips");
  for (const [n, r] of x.statuses || []) chips.appendChild(el("span", "chip", r >= 99 ? n : `${n} ${r}`));
  for (const [n, r] of x.buffs || []) chips.appendChild(el("span", "chip good", `${n} ${r}`));
  if (x.elevated) chips.appendChild(el("span", "chip good", "high ground"));
  if (chips.children.length) box.appendChild(chips);
  return box;
}
function renderCombat() {
  const d = combat.data; if (!d) return;
  const head = el("div", "h1", "⚔ COMBAT"); head.appendChild(el("span", "sub", `round ${d.round}` + (d.danger ? ` · ${d.danger}` : "")));
  side.appendChild(head);
  side.appendChild(el("div", "h2", "ENEMIES"));
  if (!d.enemies.length) side.appendChild(el("div", "dimrow", "None standing."));
  for (const e of d.enemies) side.appendChild(fighterBlock(e, false));
  if (d.reserves) side.appendChild(el("div", "dimrow", `+ ${d.reserves} more still in the camp`));
  if (d.allies.length) { side.appendChild(el("div", "h2", "ALLIES")); for (const a of d.allies) side.appendChild(fighterBlock(a, false)); }
  side.appendChild(el("div", "h2", "YOU")); side.appendChild(fighterBlock(d.you, true));
  side.appendChild(el("div", "h2", "ABILITIES"));
  if (!d.moves.length) side.appendChild(el("div", "dimrow", "None."));
  for (const m of d.moves) {
    const row = el("div", "mv" + (m.ready ? "" : " cool"));
    const nm = el("div", "mvn"); nm.appendChild(el("span", "", m.name)); nm.appendChild(el("span", "mvc", `${m.cost} ${m.resource}` + (m.cooldown ? ` · cooldown ${m.cooldown}` : "")));
    row.appendChild(nm);
    row.appendChild(el("div", "mvs " + (m.ready ? "ready" : "wait"), m.ready ? "Ready" : m.reason));
    side.appendChild(row);
  }
  side.appendChild(el("div", "h2", "COMBAT LOG")); side.lastChild.appendChild(el("span", "sub", "hover a line for the working"));
  const logEl = el("div", "clog"); let lastRound = null;
  for (const h of combat.rows) {
    if (h.round !== lastRound) { logEl.appendChild(el("div", "cr", `Round ${h.round}`)); lastRound = h.round; }
    const row = el("div", "cl " + (h.att_side === "enemy" ? "foe" : "friend")); row.dataset.hit = h.id;
    row.appendChild(el("span", "who", `${h.att} ${h.label} ${h.dfn}`));
    row.appendChild(el("span", "fig", h.figure || ""));
    logEl.appendChild(row);
  }
  side.appendChild(logEl);
  logEl.scrollTop = logEl.scrollHeight;
}
function paintSide() {
  const showCombat = combat.active && combat.mode === "combat";
  const keep = side.scrollTop;
  side.textContent = "";
  if (showCombat) { renderCombat(); side.scrollTop = keep; }
  else if (lastView) {
    if (lastView.panel && lastView.panel.name === "shop") renderShop(lastView.panel.data);
    if (lastView.panel && lastView.panel.name === "gear") renderGear(lastView.panel.data);
    const pn = lastView.panel && lastView.panel.name;
    if (pn === "journal") renderJournal(lastView.panel.data);
    else if (pn === "party") renderParty(lastView.panel.data);
    else if (pn === "map") renderMap(lastView.panel.data);
    else if (pn === "pulse") renderPulse(lastView.panel.data);
    else if (pn === "character" && lastView.raw.includes(ATTR_MARK)) {
      const [before, after] = lastView.raw.split(ATTR_MARK + "\n");
      renderInto(side, before, "pane", false);
      renderAttrs(lastView.panel.data);
      renderInto(side, after || "", "pane", false);
    } else renderInto(side, lastView.raw, "pane", false);
    side.scrollTop = lastPanelCmd === lastView.cmd ? keep : 0; lastPanelCmd = lastView.cmd;
    $("sidetitle").textContent = lastView.cmd || "";
  }
  applyShopState(); renderButtons();
}

// ---------- start-up screen: install Ollama, download the model (its buttons answer the question the game is asking) ----------
function showSetup(d) {
  $("setup").hidden = false;
  $("setuptitle").textContent = d.title;
  const lines = $("setuplines"); lines.textContent = "";
  for (const t of d.lines) lines.appendChild(el("p", "", t));
  const btns = $("setupbtns"); btns.textContent = "";
  for (const [label, key] of d.buttons) {
    const b = el("button", key === "quit" ? "" : "primary", label);
    b.onclick = () => { btns.querySelectorAll("button").forEach((x) => (x.disabled = true)); api("/input", { text: key }); };
    btns.appendChild(b);
  }
  $("setupbar").hidden = !d.progress; $("setuptext").textContent = "";
  if (d.progress) setupProgress(d.progress.frac, d.progress.text);
}
function setupProgress(frac, text) {
  $("setupbar").hidden = false;
  $("setupfill").style.width = Math.round(frac * 100) + "%";
  $("setuptext").textContent = text;
}

// ---------- update available: a button in the strip; it opens a card with the release notes and an Update button ----------
function showUpdateButton(info) {
  const b = $("updatebtn");
  b.textContent = `⬆ Update available (v${info.version})`; b.hidden = false;
  b.onclick = () => {
    $("updtitle").textContent = `Version ${info.version} is available`;
    $("updnotes").textContent = info.notes || "A new version of the game is ready.";
    $("updbar").hidden = true; $("updtext").textContent = "";
    const btns = $("updbtns"); btns.textContent = "";
    const go = el("button", "primary", "Update now"), later = el("button", "", "Later");
    go.onclick = () => { go.disabled = later.disabled = true; $("updbar").hidden = false; api("/update", {}); };
    later.onclick = () => { $("update").hidden = true; };
    btns.append(go, later);
    $("update").hidden = false;
  };
}
function updateProgress(ev) {
  $("updbar").hidden = false;
  $("updfill").style.width = Math.round(ev.frac * 100) + "%";
  $("updtext").textContent = ev.text;
  if (ev.error) { const later = el("button", "", "Close"); later.onclick = () => { $("update").hidden = true; }; $("updbtns").appendChild(later); }
}

// ---------- events ----------
function handle(ev) {
  switch (ev.k) {
    case "text":
      if (ev.pane === "side") sideRaw += ev.text;
      else addText(ev.text, ev.kind || "plain");
      break;
    case "echo": addBlock("echo", "> " + ev.text); break;
    case "panel": sidePanel = ev; break;
    case "side_begin": sideRaw = ""; sidePanel = null; state.current = ev.cmd; $("sidetitle").textContent = ev.cmd; break;
    case "side_end": lastView = { raw: sideRaw, panel: sidePanel, cmd: state.current }; paintSide(); break;
    case "combat": onCombat(ev.data); break;
    case "combat_end": combat.active = false; combat.mode = "view"; paintSide(); break;
    case "status": Strip.update(ev); if (!!ev.debug !== !!state.debug) { state.debug = !!ev.debug; renderButtons(); } break;
    case "prompt": state.prompt = true; state.atMain = !!ev.main; updateInput(); break;
    case "busy": $("busy").hidden = !ev.on; if (ev.on && nearBottom()) log.scrollTop = log.scrollHeight; break;
    case "ended": state.prompt = false; updateInput(); addBlock("sys", "The game has ended. You can close this window."); break;
    case "fatal": addBlock("sys", ev.text); break;
    case "update": showUpdateButton(ev.data); break;
    case "update_progress": updateProgress(ev); break;
    case "setup": showSetup(ev.data); break;
    case "setup_progress": setupProgress(ev.frac, ev.text); break;
    case "setup_end": $("setup").hidden = true; break;
  }
}

async function start() {
  const r = await api("/prefs");
  if (r.ok) Object.assign(state.prefs, r.data);
  applyLayout(); renderButtons(); updateInput();
  const es = new EventSource("/events?t=" + encodeURIComponent(TOKEN));
  es.onmessage = (m) => { try { handle(JSON.parse(m.data)); } catch (e) { console.error(e); } };
}
start();
