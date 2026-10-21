"use strict";
const TOKEN = window.TOKEN;
const $ = (id) => document.getElementById(id);
const log = $("log"), side = $("sidebody"), input = $("input");
const COMMANDS = [["Character", "#character"], ["Stats", "#stats"], ["Inventory", "#inventory"], ["Gear", "#gear"], ["Journal", "#journal"], ["Quests", "#quests"], ["Map", "#map"], ["Places", "#exits"],
  ["Party", "#party"], ["Standing", "#standing"], ["Story", "#arc"],
  ["Dungeon", "#dungeon"], ["Home", "#home"], ["Shop", "#shop"], ["Stash", "#stash"], ["Board", "#board"], ["Help", "#help"], ["New game", "#newgame"]];

const PINNABLE = new Set(["#character", "#stats", "#inventory", "#gear", "#journal", "#quests", "#map", "#places", "#exits", "#party", "#standing", "#arc", "#dungeon", "#home", "#shop", "#stash", "#board", "#help", "#pulse"]);   // read-only views; New game and the rest are never pinned
const state = { prompt: false, atMain: false, current: null, prefs: { pinned: "#character", width: 400, hidden: false, theme: "auto", order: [] } };

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

function decorate(body, beats) {
  let h = esc(body);
  const bar = /^(\w+)\b/.exec(body);
  const color = bar && BAR_NAME[bar[1].toLowerCase()];
  h = h.replace(/([█▰]*)([░▱]+)|([█▰]+)/g, (m, f, e, g) => `<span class="barf" style="color:var(${color || "--accent"})">${f || g || ""}</span><span class="bare">${e || ""}</span>`);
  h = h.replace(/(^|[\s(;,])(#[a-z]+)/g, '$1<span class="cmd">$2</span>');
  h = h.replace(/⟦([^|⟧]+)\|([^⟧]*)⟧/g, (m, id, fig) => `<span class="dmg${/^\((\+|cured)/.test(fig) ? " heal" : ""}" data-hit="${id}">${fig.replace(/^\((.*)\)$/, "$1")}</span>`);       // a blow's figure: hover for how it was worked out
  if (beats) h = h.replace(/\(([^()<>]{3,}?)\)/g, '<span class="beat">($1)</span>');       // what someone does between their words
  if (/^★/.test(body)) h = `<span class="legend">${h}</span>`;
  return h;
}
function lineEl(raw, mode, role, kind) {
  const d = document.createElement("div");
  if (!raw.trim()) { d.className = "blank"; return d; }
  if (RULE.test(raw)) { d.className = "rule " + (raw.includes("═") ? "heavy" : "light"); return d; }
  const indent = raw.length - raw.trimStart().length, body = raw.trim();
  if (role === "title") { d.className = "h1"; d.textContent = body; return d; }
  if (mode === "main" && kind === "speech") {                     // the speaker's name as a label; their words in the reading face
    const who = /^(.{1,40}):$/.exec(body);
    if (who) { d.className = "spk"; d.textContent = who[1]; return d; }
    const inline = /^([^:"]{1,40}): (".*)$/.exec(body);
    if (inline) { const f = document.createDocumentFragment(); f.appendChild(el("div", "spk", inline[1])); const l = el("div", "ln"); l.innerHTML = decorate(inline[2], true); f.appendChild(l); return f; }
    d.className = "ln"; d.innerHTML = decorate(body, true); return d;
  }
  if (mode === "main" && kind === "note") { d.className = "ln"; d.innerHTML = decorate(body.replace(/^\[(.*)\]$/, "$1")); return d; }
  if (mode === "main" && kind === "wait") { d.className = "ln"; d.textContent = body.replace(/^\((.*)\)$/, "$1"); return d; }
  if (mode === "pane") {
    const note = /^\[(.*)\]$/.exec(raw.trim());                                        // (f327) a whole-line [note] in a pane is a note: no brackets
    if (note) return lineEl(note[1].replace(/\s+$/, ""), mode, role, kind);
    const help = /^\s{2}(#[a-z]+(?: \[n\])?|quit|\*text\*|"text")\s+(\S.*)$/.exec(raw);     // (f327) "  #command   what it does" as two columns
    if (help) { const r = el("div", "hrow"); r.appendChild(el("span", "hc", help[1])); const t = el("span", "ht"); t.innerHTML = decorate(help[2]); r.appendChild(t); return r; }
    const vb = /^(\w[\w ]*?)\s+([█▰]+[░▱]*|[░▱]+)\s+(\d+)\/(\d+)$/.exec(body);         // "Health  ████░░ 64/80" drawn as a bar
    if (vb) {
      const color = BAR_NAME[vb[1].toLowerCase()] || "--accent";
      const r = el("div", "crow wide"); r.append(el("span", "lbl", vb[1].toUpperCase()), bar(+vb[3], +vb[4], color), el("span", "num", `${vb[3]}/${vb[4]}`)); return r;
    }
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
  d.innerHTML = decorate(body, mode === "main" && kind === "narration");
  return d;
}
function renderInto(el, text, mode, skipBlankRuns, kind) {
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
    el.appendChild(lineEl(ln, mode, role, kind));
  });
}
// ---------- the ticker (f325): mechanics stay out of the story column; this turn's lines sit under the status strip until the next line is typed
const ticker = { lines: [] };
function tickerAdd(text) {
  for (const line of text.split("\n")) {
    const t = line.replace(/^\s*·\s*/, "").trim();
    if (t) ticker.lines.push(t);
  }
  tickerDraw();
}
function tickerClear() { ticker.lines = []; tickerDraw(); }
function tickerDraw() {
  const box = $("ticker"); if (!box) return;
  box.textContent = "";
  for (const t of ticker.lines.slice(-8)) box.appendChild(el("span", "tk" + (/^\+/.test(t) ? " gain" : ""), t));
  box.hidden = !ticker.lines.length;
}
function addText(text, kind) {
  if (kind === "ledger") { tickerAdd(text); return; }
  const stick = nearBottom();
  if (!cur || cur.dataset.kind !== kind) {
    cur = document.createElement("div"); cur.className = "blk k-" + kind; cur.dataset.kind = kind; log.appendChild(cur);
  }
  renderInto(cur, text, "main", true, kind);
  if (stick) log.scrollTop = log.scrollHeight;
}
function addEcho(text) {
  const stick = nearBottom();
  cur = null; lastBlank = true;
  const d = el("div", "echo"); d.append(el("span", "pc", "›"), el("span", "", text), el("span", "stamp", state.when || ""));
  log.appendChild(d);
  if (stick) log.scrollTop = log.scrollHeight;
}
function addBlock(cls, text) {
  const stick = nearBottom();
  cur = null; lastBlank = true;
  const d = document.createElement("div"); d.className = cls; d.textContent = text; log.appendChild(d);
  if (stick) log.scrollTop = log.scrollHeight;
}

// ---------- shop panel: buy and sell buttons (they send hidden commands the game runs itself; no model call) ----------
const ATTR_MARK = "@@ATTRIBUTES@@", ABIL_MARK = "@@ABILITIES@@";
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
      const wn = el("div", "nm"); wn.appendChild(named(w, w.name.replace(/^(a|an) /, ""))); info.appendChild(wn);
      if (w.detail) info.appendChild(el("div", "dt", tidy(w.detail)));
      if (w.note) info.appendChild(el("div", "warn", w.note));
      const buy = el("div", "act");
      buy.appendChild(el("div", "pr" + (w.afford ? "" : " poor"), w.price_short || w.price_text));
      buy.appendChild(shopButton("Buy", `#shopbuy ${w.kind} ${s.id} ${w.key}`, w.afford));
      row.append(info, buy); side.appendChild(row);
    }
  }
  side.appendChild(el("div", "h2", "SELL FROM YOUR PACK"));
  if (!d.sell.length) side.appendChild(el("div", "dimrow", "No one here wants anything you carry."));
  for (const x of d.sell) {
    const row = el("div", "shoprow"), info = el("div", "info");
    const xn = el("div", "nm"); xn.appendChild(named(x, x.name)); info.appendChild(xn);
    info.appendChild(el("div", "dt", (x.detail ? tidy(x.detail) + " · " : "") + "to " + x.buyer_name));
    const act = el("div", "act");
    act.appendChild(el("div", "pr", x.total_short || x.total_text));
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
    nm.appendChild(el("span", s.item ? "gname " + rarityOf(s.item) : "gname empty", s.item ? s.item.name : "--"));
    info.appendChild(nm);
    if (s.item && s.item.detail) info.appendChild(el("div", "dt", tidy(s.item.detail)));
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
    const cn = el("div", "nm"); cn.appendChild(named(x, x.name)); info.appendChild(cn);
    info.appendChild(el("div", "dt", tidy(x.detail)));
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

// ---------- map pane: the illustrated map of Rivia with fog of war; hover or tap a place for its levels, Go to travel; drag to pan, wheel to zoom ----------
let mapView = null;
function renderMap(d) {
  const NS = "http://www.w3.org/2000/svg";
  const mk = (tag, attrs, parent) => { const n = document.createElementNS(NS, tag); for (const k in attrs) n.setAttribute(k, attrs[k]); if (parent) parent.appendChild(n); return n; };
  const S = d.size || 1000;
  const here = d.nodes.find((n) => n.id === d.here);
  const byId = Object.fromEntries(d.nodes.map((n) => [n.id, n]));
  const xs = d.nodes.map((n) => n.x), ys = d.nodes.map((n) => n.y);
  const pad = 130;
  const fit = { x: Math.min(...xs) - pad, y: Math.min(...ys) - pad, w: Math.max(...xs) - Math.min(...xs) + 2 * pad, h: Math.max(...ys) - Math.min(...ys) + 2 * pad };
  const keep = mapView && mapView.here === d.here ? mapView.box : null;
  const fw = Math.max(fit.w, 300), fh = Math.max(fit.h, Math.round(fw * 0.7));                       // (f327) no forced square: the frame follows the known world
  const vb = keep || { x: fit.x - (fw - fit.w) / 2, y: fit.y - (fh - fit.h) / 2, w: fw, h: fh };
  if (!keep) { vb.x = Math.max(0, Math.min(S - vb.w, vb.x)); vb.y = Math.max(0, Math.min(S - vb.h, vb.y)); }      // ...and stays on the painted map
  const svg = mk("svg", { class: "mapsvg", viewBox: `${vb.x} ${vb.y} ${vb.w} ${vb.h}` });
  svg.style.aspectRatio = `${vb.w} / ${vb.h}`;
  // the painted map, then the fog over it with holes where you have been, along the roads you know and around places you have heard of
  mk("image", { href: d.image || "/map.jpg", x: 0, y: 0, width: S, height: S, preserveAspectRatio: "none" }, svg);
  const defs = mk("defs", {}, svg);
  const soft = mk("filter", { id: "mapsoft", filterUnits: "userSpaceOnUse", x: 0, y: 0, width: S, height: S }, defs);
  mk("feGaussianBlur", { stdDeviation: 11 }, soft);
  const fogMask = mk("mask", { id: "mapfog", maskUnits: "userSpaceOnUse", x: 0, y: 0, width: S, height: S }, defs);
  mk("rect", { x: 0, y: 0, width: S, height: S, fill: "white" }, fogMask);
  const holes = mk("g", { filter: "url(#mapsoft)", fill: "black" }, fogMask);
  const stamp = (pts, r, step) => {
    for (let i = 0; i + 1 < pts.length; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
      const len = Math.hypot(x2 - x1, y2 - y1), n = Math.max(1, Math.ceil(len / step));
      for (let k = 0; k <= n; k++) mk("circle", { cx: x1 + (x2 - x1) * k / n, cy: y1 + (y2 - y1) * k / n, r }, holes);
    }
  };
  const pathOf = (e) => (e.path && e.path.length > 1 ? e.path : [[byId[e.a].x, byId[e.a].y], [byId[e.b].x, byId[e.b].y]]);
  for (const e of d.edges) stamp(pathOf(e), byId[e.a].state === "heard" || byId[e.b].state === "heard" ? 24 : 34, 18);
  for (const n of d.nodes) mk("circle", { cx: n.x, cy: n.y, r: n.state === "here" ? 92 : n.state === "visited" ? 74 : 40 }, holes);
  mk("rect", { x: 0, y: 0, width: S, height: S, class: "mapfog", mask: "url(#mapfog)" }, svg);
  // roads: solid black between settlements, dashed to wild places, a faint dotted line underground
  for (const e of d.edges) {
    const dim = byId[e.a].state === "heard" || byId[e.b].state === "heard";
    const pl = mk("polyline", { points: pathOf(e).map((p) => p.join(",")).join(" "), class: "maproad " + (e.under ? "under" : e.main ? "main" : "minor") + (dim ? " dim" : ""), "vector-effect": "non-scaling-stroke" }, svg);
    mk("title", {}, pl).textContent = `${byId[e.a].name} - ${byId[e.b].name}: ${e.label}`;
  }
  // roads out to somewhere you do not know: a short dashed stub, no end
  for (const st of d.stubs || []) {
    const ln = mk("polyline", { points: `${st.x1},${st.y1} ${st.x2},${st.y2}`, class: "mapstub", "vector-effect": "non-scaling-stroke" }, svg);
    mk("title", {}, ln).textContent = `${st.label}: leads ${st.dir}, you do not know where it ends`;
    const hitln = mk("polyline", { points: `${st.x1},${st.y1} ${st.x2},${st.y2}`, class: "stubhit", "vector-effect": "non-scaling-stroke" }, svg);
    hitln.addEventListener("click", (e) => { if (moved) return; picked = null; showRoad(st); e.stopPropagation(); });
  }
  // places
  const marks = [];
  const house = (g, x, y, k) => mk("path", { d: `M${x - 4 * k},${y + 3 * k}V${y - 1.5 * k}L${x},${y - 5.5 * k}L${x + 4 * k},${y - 1.5 * k}V${y + 3 * k}Z`, class: "ico" }, g);
  const info = el("div", "mapinfo");
  let picked = null;
  const showInfo = (n) => {
    info.textContent = "";
    if (!n) { info.appendChild(el("div", "dimrow", "Hover or tap a place for its level range, then use Go to travel there. A dashed stub is a road to somewhere you do not know. Tap empty map to clear.")); return; }
    const head = el("div", "nm", n.name);
    info.appendChild(head);
    info.appendChild(el("div", "dt", `${n.type} · ${n.region}`));
    if (n.levels) info.appendChild(el("div", "lv", n.levels));
    info.appendChild(el("div", "dt", n.state === "here" ? "You are here." : n.state === "heard" ? `Heard of, not yet visited · ${n.away} away` : `${n.away} away`));
    if (n.state !== "here") { const b = shopButton("Go", `#mapgo ${n.id}`, true, n.minutes >= 240); info.appendChild(b); }
    applyShopState();
  };
  const showRoad = (st) => {
    info.textContent = "";
    info.appendChild(el("div", "nm", st.label));
    info.appendChild(el("div", "dt", `A road leading ${st.dir}. You do not know where it ends.`));
    info.appendChild(shopButton("Go", `#maproad ${st.dir}`, true, false));
    applyShopState();
  };
  for (const n of d.nodes) {
    const g = mk("g", { class: "mapnode " + n.state + " t-" + n.type }, svg);
    const ico = mk("g", { class: "icons" }, g);
    if (n.type === "city") {
      mk("rect", { x: -9, y: -4, width: 18, height: 8, class: "ico" }, ico);
      for (const [tx, sz] of [[-7, 0.8], [7, 0.8], [0, 1.15]]) { mk("rect", { x: tx - 3 * sz, y: -9 * sz - 1, width: 6 * sz, height: 12 * sz, class: "ico" }, ico); }
      for (const dx of [-3, 3]) house(ico, dx, 7, 0.65);
    } else if (n.type === "town") { house(ico, -5, 1, 1); house(ico, 4, -1, 0.9); house(ico, 0, 4, 0.8); }
    else if (n.type === "village") { house(ico, -3, 1, 0.85); house(ico, 3.5, 0, 0.75); }
    else { mk("path", { d: "M-4,-4L4,4M4,-4L-4,4", class: "wild" }, ico); }
    if (n.state === "here") { mk("circle", { r: 15, class: "pulse" }, g); mk("circle", { r: 4.5, class: "youare" }, g); }
    const settle = ["city", "town", "village"].includes(n.type);
    const t = mk("text", { y: (n.type === "city" ? 20 : settle ? 15 : 12) + (n.state === "here" ? 8 : 0), "text-anchor": "middle", class: "lbl" + (settle ? "" : " wildlbl") }, g);
    t.textContent = n.name.replace(/^the /i, "");
    const hit = mk("circle", { r: 14, class: "hit" }, g);
    hit.addEventListener("pointerenter", () => { if (!picked) showInfo(n); });
    // the panel keeps the last place you pointed at, so you can move down to its Go button; tap empty map to clear it
    hit.addEventListener("click", (e) => { if (moved) return; picked = picked === n ? null : n; showInfo(picked); svg.querySelectorAll(".mapnode.pick").forEach((q) => q.classList.remove("pick")); if (picked) g.classList.add("pick"); e.stopPropagation(); });
    marks.push({ g, n, t, settle });
  }
  // icons and text keep their size on screen whatever the zoom
  const relayout = () => {
    const k = vb.w / Math.max(1, svg.clientWidth || 480);
    for (const m of marks) {
      m.g.setAttribute("transform", `translate(${m.n.x} ${m.n.y}) scale(${k * 1.25})`);
      m.t.style.display = m.settle || m.n.state === "here" || vb.w < 520 ? "" : "none";
    }
  };
  let drag = null, moved = false;
  svg.addEventListener("pointerdown", (e) => { moved = false; drag = { x: e.clientX, y: e.clientY, vb: { ...vb } }; svg.setPointerCapture(e.pointerId); });
  svg.addEventListener("pointermove", (e) => {
    if (!drag) return;
    if (Math.hypot(e.clientX - drag.x, e.clientY - drag.y) > 4) moved = true;
    const k = drag.vb.w / svg.clientWidth;
    vb.x = drag.vb.x - (e.clientX - drag.x) * k; vb.y = drag.vb.y - (e.clientY - drag.y) * k;
    svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
  });
  svg.addEventListener("click", () => { if (moved) return; picked = null; svg.querySelectorAll(".mapnode.pick").forEach((q) => q.classList.remove("pick")); showInfo(null); });
  svg.addEventListener("pointerup", () => { drag = null; mapView = { here: d.here, box: { ...vb } }; setTimeout(() => { moved = false; }, 0); });
  svg.addEventListener("wheel", (e) => {
    e.preventDefault();
    const f = e.deltaY > 0 ? 1.15 : 1 / 1.15, r = svg.getBoundingClientRect();
    const px = vb.x + ((e.clientX - r.left) / r.width) * vb.w, py = vb.y + ((e.clientY - r.top) / r.height) * vb.h;
    vb.x = px - (px - vb.x) * f; vb.y = py - (py - vb.y) * f; vb.w *= f; vb.h *= f;
    svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`);
    mapView = { here: d.here, box: { ...vb } };
    relayout();
  }, { passive: false });
  side.appendChild(el("div", "dimrow", here ? (d.on_road ? `You are on the road, last in ${here.name}.` : `You are in ${here.name}.`) + " Unexplored lands are under fog. Drag to move, scroll to zoom." : ""));
  const bar = el("div", "mapbar");
  const setView = (box) => { Object.assign(vb, box); svg.setAttribute("viewBox", `${vb.x} ${vb.y} ${vb.w} ${vb.h}`); mapView = { here: d.here, box: { ...vb } }; relayout(); };
  const b1 = el("button", "", "Find me"), b2 = el("button", "", "Whole map");
  b1.onclick = () => { if (here) setView({ x: here.x - 150, y: here.y - 150, w: 300, h: 300 }); };
  b2.onclick = () => setView({ x: 0, y: 0, w: S, h: S });
  bar.append(b1, b2);
  side.appendChild(bar);
  side.appendChild(svg);
  showInfo(null);
  side.appendChild(info);
  relayout();
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

// ---------- board pane: contracts to take (Accept runs the same code as typing it), the ones you hold, and requests from people here ----------
function renderBoard(d) {
  side.appendChild(el("div", "purse", d.member ? `Guild rank ${d.rank}` : "Not a guild member"));
  if (!d.member) {
    const row = el("div", "shoprow"), info = el("div", "info");
    info.appendChild(el("div", "nm", "Join the adventurers' guild"));
    info.appendChild(el("div", "dt", `Joining fee ${d.fee}. Contracts can only be taken by members.`));
    if (!d.clerk) info.appendChild(el("div", "warn", "The clerk must be here to sign you in."));
    else if (!d.fee_ok) info.appendChild(el("div", "warn", `You cannot afford the fee (purse ${d.purse}).`));
    const act = el("div", "act");
    act.appendChild(shopButton("Join", "#boardjoin", d.clerk && d.fee_ok));
    row.append(info, act); side.appendChild(row);
  }
  side.appendChild(el("div", "h2", d.hall ? "CONTRACT BOARD · " + d.hall.toUpperCase() : "CONTRACT BOARD"));
  if (!d.hall) side.appendChild(el("div", "dimrow", "There is no guild hall here. Each hall keeps its own board."));
  else if (!d.postings.length) side.appendChild(el("div", "dimrow", "Nothing posted."));
  for (const q of d.postings) {
    const row = el("div", "shoprow"), info = el("div", "info");
    info.appendChild(el("div", "nm", `[${q.letter}] ${q.title}`));
    if (q.for) info.appendChild(el("div", "dt", q.for));                 // (f322) who asked, and why
    info.appendChild(el("div", "dt", `${q.reward} · ${q.xp} XP · ${q.limit}`));
    if (q.why) info.appendChild(el("div", "warn", q.why));
    const act = el("div", "act");
    const b = shopButton("Accept", `#boardaccept ${q.id}`, q.ok);
    if (q.why) b.title = q.why;
    act.appendChild(b);
    row.append(info, act); side.appendChild(row);
  }
  if (d.requests.length) side.appendChild(el("div", "h2", "REQUESTS FROM PEOPLE HERE"));
  for (const r of d.requests) {
    const row = el("div", "shoprow"), info = el("div", "info");
    info.appendChild(el("div", "nm", `[${r.letter}] ${r.title}`));
    info.appendChild(el("div", "dt", `asked by ${r.name}`));
    const act = el("div", "act");
    act.appendChild(shopButton("Accept", `#boardrequest ${r.npc}`, true));
    row.append(info, act); side.appendChild(row);
  }
  if (d.hall && d.hires) {
    side.appendChild(el("div", "h2", "ADVENTURERS LOOKING FOR WORK"));
    if (!d.hires.length) side.appendChild(el("div", "dimrow", d.member ? (d.lesson ? "Nobody else, while Maren is showing you the ropes." : "Nobody is free this week.") : "Join the guild to hire adventurers."));
    for (const h of d.hires) {
      const row = el("div", "shoprow"), info = el("div", "info");
      info.appendChild(el("div", "nm", `${h.name} · ${h.who}, rank ${h.rank}, level ${h.level}`));
      info.appendChild(el("div", "dt", `${h.blurb}; ${h.temper} · ${h.fee}`));
      if (h.why) info.appendChild(el("div", "warn", h.why));
      const act = el("div", "act");
      const b = shopButton("Hire", `#boardhire ${h.id}`, h.ok);
      if (h.why) b.title = h.why;
      act.appendChild(b);
      row.append(info, act); side.appendChild(row);
    }
  }
  side.appendChild(el("div", "h2", "YOUR CONTRACTS"));
  if (!d.held.length) side.appendChild(el("div", "dimrow", "You hold no contracts or requests."));
  for (const q of d.held) {
    const row = el("div", "shoprow"), info = el("div", "info");
    info.appendChild(el("div", "dt", q.line));
    const act = el("div", "act");
    act.appendChild(shopButton("Abandon", `#boardabandon ${q.id}`, true, true));
    row.append(info, act); side.appendChild(row);
  }
}

// ---------- places pane: where you can go from here, with walking times and Go buttons (same travel code as typing it) ----------
function renderPlaces(d) {
  if (!d.here) { side.appendChild(el("div", "dimrow", "You are not anywhere you know the way from.")); return; }
  side.appendChild(el("div", "purse", `${d.here_name} · ${d.town}`));
  const block = (title, rows) => {
    side.appendChild(el("div", "h2", title));
    if (!rows.length) side.appendChild(el("div", "dimrow", "Nowhere else."));
    for (const r of rows) {
      const row = el("div", "shoprow"), info = el("div", "info");
      info.appendChild(el("div", "nm", r.name));
      info.appendChild(el("div", "dt", (r.state === "heard" ? "heard of · " : "") + r.away));
      const act = el("div", "act");
      act.appendChild(shopButton("Go", `#goto ${r.id}`, true, r.minutes >= 240));
      row.append(info, act); side.appendChild(row);
    }
  };
  block("IN " + d.town.toUpperCase(), d.local);
  block("FURTHER AFIELD", d.far);
  if (d.roads && d.roads.length) {
    side.appendChild(el("div", "h2", "ROADS OUT"));
    for (const r of d.roads) {
      const row = el("div", "shoprow"), info = el("div", "info");
      info.appendChild(el("div", "nm", r.name));
      info.appendChild(el("div", "dt", `leads ${r.dir} · you do not know where it ends`));
      const act = el("div", "act");
      act.appendChild(shopButton("Go", `#goroad ${r.dir}`, true, false));
      row.append(info, act); side.appendChild(row);
    }
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
    info.appendChild(el("div", "dt", `${a.role} · rank ${a.rank} · level ${a.level}`));
    if (a.bond) {
      info.appendChild(el("div", "dt", `${a.bond} · ${a.health}% health`));
      info.appendChild(el("div", "dt", a.temper));
      if (a.line) info.appendChild(el("div", "dt", `Line they hold: ${a.line}`));
      if (a.promote) info.appendChild(el("div", "warn", `Ready for promotion: ${a.promote} (say "promote ${a.name.split(" ")[0]}")`));
    }
    if (a.tip) { row.dataset.tip = "adv:" + a.name; tipMap["adv:" + a.name] = a.tip; }
    row.appendChild(info); side.appendChild(row);
  }
  if (d.mode) side.appendChild(el("div", "dimrow", "They are " + d.mode + "."));
}

// ---------- stats pane: every number combat uses, in sections, each row with where it comes from ----------
function renderStats(d) {
  side.appendChild(el("div", "h2", d.title.toUpperCase()));
  if (d.unspent > 0) side.appendChild(el("div", "pts", `${d.unspent} attribute point${d.unspent === 1 ? "" : "s"} to spend (Character pane)`));
  for (const sec of d.sections) {
    side.appendChild(el("div", "h2", sec.title.toUpperCase()));
    if (sec.title === "Attributes") {
      const box = el("div", "attrs");
      for (const r of sec.rows) {
        const cell = el("div", "attr");
        cell.appendChild(el("span", "an", r[0].slice(0, 3).toUpperCase()));
        cell.appendChild(el("span", "av", String(r[1])));
        box.appendChild(cell);
      }
      side.appendChild(box);
      continue;
    }
    for (const [label, value, note] of sec.rows) {
      const row = el("div", "shoprow stat"), info = el("div", "info");
      const nm = el("div", "nm");
      nm.appendChild(el("span", "slotname", label));
      nm.appendChild(el("span", "gname", String(value)));
      info.appendChild(nm);
      if (note) info.appendChild(el("div", "dt", note));
      row.appendChild(info); side.appendChild(row);
    }
  }
}

// ---------- abilities and passives: listed by name, each read on hover ----------
function renderAbilities(d) {
  for (const [title, list, kind] of [["ACTIVE ABILITIES", d.abilities || [], "ab"], ["PASSIVES", d.passives || [], "ps"]]) {
    side.appendChild(el("div", "h2", title));
    if (!list.length) side.appendChild(el("div", "dimrow", "none"));
    list.forEach((x, i) => {
      const row = el("div", "shoprow hoverrow"), info = el("div", "info");
      info.appendChild(el("div", "nm", "◆ " + x.name));
      const key = `${kind}:${i}:${x.name}`;
      row.dataset.tip = key; tipMap[key] = x.tip;
      row.appendChild(info); side.appendChild(row);
    });
  }
  side.appendChild(el("div", "dimrow", "Hover a name to read what it does."));
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
const journalOpen = new Set();         // journal entries opened with a click; they stay open across redraws (f301)
function renderJournal(d) {
  // (f301) every entry is a name; a click opens what is known of it, another click closes it - easier to look through a long campaign
  const search = el("input", "jsearch");
  search.type = "search"; search.placeholder = "Search people and what you've learned…"; search.value = journalQuery;
  const body = el("div", "jbody");
  side.append(search, body);
  const titleOf = (t) => {                     // its first sentence, cut at about eight words
    const all = t.replace(/\s+/g, " ").trim().replace(/[.!]$/, "");
    const first = all.split(/\. | - /)[0];
    const words = first.split(" ");
    return words.length > 8 ? words.slice(0, 8).join(" ").replace(/[,;:]$/, "") + "…" : first + (first.length < all.length ? "…" : "");
  };
  const entry = (key, title, detail, cls) => {
    const row = el("div", "prow jentry" + (cls ? " " + cls : "") + (journalOpen.has(key) ? " open" : ""));
    row.appendChild(el("div", "pn", title));
    if (journalOpen.has(key) || journalQuery.trim()) row.appendChild(el("div", "pr2", detail));
    row.onclick = () => { journalOpen.has(key) ? journalOpen.delete(key) : journalOpen.add(key); draw(); };
    return row;
  };
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
      for (const p of people) { body.appendChild(entry("p:" + g.town + ":" + p.name, p.name, p.line)); shown++; }
    }
    if (!shown) body.appendChild(el("div", "dimrow", q ? "No one matches." : "No one yet."));
    const heard = (d.heard || []).filter((p) => !q || `${p.name} ${p.by} ${p.line}`.toLowerCase().includes(q));
    if (heard.length) {
      body.appendChild(el("div", "h2", "PEOPLE YOU'VE HEARD OF"));
      for (const p of heard) body.appendChild(entry("h:" + p.name, p.name, `Mentioned by ${p.by}: "${p.line}"`, "heard"));
    }
    const matters = (d.matters || []).filter((m) => !q || `${m.title} ${m.place} ${m.standing} ${m.found.join(" ")}`.toLowerCase().includes(q));
    if (matters.length) {                       // (f317) the matters you have touched: what you have found of each, nothing you have not
      body.appendChild(el("div", "h2", "MATTERS"));
      for (const m of matters) {
        const detail = (m.found.length ? m.found.map((f) => "- " + f).join("\n") : "You have seen it, and found nothing yet.") + "\n(" + m.standing + ")";
        body.appendChild(entry("m:" + m.title, `${m.title} - ${m.place}`, detail));
      }
    }
    body.appendChild(el("div", "h2", "THINGS YOU'VE LEARNED"));
    const facts = d.facts.filter((f) => !q || f.toLowerCase().includes(q));
    if (!facts.length) body.appendChild(el("div", "dimrow", q ? "Nothing matches." : "Nothing yet."));
    for (const f of facts) body.appendChild(entry("f:" + f, titleOf(f), f.replace(/\s+/g, " ")));
    const hist = d.history.filter((f) => !q || f.toLowerCase().includes(q));
    if (hist.length) {
      body.appendChild(el("div", "h2", "ITEMS DELIVERED OR LET GO"));
      for (const f of hist) body.appendChild(entry("i:" + f, titleOf(f), f));
    }
  };
  search.oninput = () => { journalQuery = search.value; draw(); };
  draw();
}

// ---------- (f327) rows shared by the inventory, stash and home panes: a name, what it does, what it is worth, a button when there is an action
// (f328) a name takes its rarity's colour: uncommon green, rare blue, epic purple, legendary gold with its star
const RARE = { uncommon: "r-uncommon", rare: "r-rare", epic: "r-epic", legendary: "leg" };
const rarityOf = (x) => (x && (RARE[x.rarity] || (x.legendary ? "leg" : ""))) || "";
const named = (x, text) => el("span", rarityOf(x), (rarityOf(x) === "leg" && !/^★/.test(text) ? "★ " : "") + text);
const tidy = (t) => (t || "").replace(/^(consumable|food|herb|material|gear|key) - /, "").replace(/^lv (\d+) (?=\S)/, "lv $1 · ");
const cap1 = (t) => (t ? t[0].toUpperCase() + t.slice(1) : t);
function itemRow(x, withUse) {
  const row = el("div", "row2"), info = el("div", "info"), nm = el("div", "nm");
  if (x.n) nm.appendChild(el("span", "idx", String(x.n)));
  nm.appendChild(named(x, x.name));
  if (x.qty > 1) { nm.appendChild(document.createTextNode(" ")); nm.appendChild(el("span", "pill", "×" + x.qty)); }
  info.appendChild(nm);
  if (x.detail) info.appendChild(el("div", "dt", tidy(x.detail)));
  if (x.flavour) info.appendChild(el("div", "q", `"${x.flavour}"`));
  row.appendChild(info);
  const act = el("div", "act");
  if (x.value) { const v = el("div", "val", x.value); if (x.qty > 1) v.appendChild(el("span", "ea", "each")); act.appendChild(v); }
  if (withUse && x.use) act.appendChild(shopButton("Use", `#useitem ${x.use}`, true));
  if (act.children.length) row.appendChild(act);
  return row;
}
function capRow(label, now, top, color) { const r = el("div", "crow wide"); r.append(el("span", "lbl", label), bar(now, top, color || "--accent"), el("span", "num", `${now}/${top}`)); return r; }
function purse(text, sub) { const p = el("div", "purse", text); if (sub) p.appendChild(el("span", "sub", " · " + sub)); return p; }
function h2(text, sub) { const h = el("div", "h2", text); if (sub) h.appendChild(el("span", "sub", sub)); return h; }

// ---------- inventory pane: the pack by kind, with Use on anything drinkable or edible; worn gear is the Gear pane's ----------
function renderInventory(d) {
  side.appendChild(purse(d.purse));
  side.appendChild(capRow("PACK", d.count, d.cap));
  for (const g of d.groups) {
    const rows = d.items.filter((x) => x.group === g);
    if (!rows.length) continue;
    side.appendChild(h2(g.toUpperCase()));
    for (const x of rows) side.appendChild(itemRow(x, true));
  }
  if (!d.items.length) side.appendChild(el("div", "dimrow", "Your pack is empty."));
  if (d.keys.length) {
    side.appendChild(h2("KEY ITEMS", "no slots · kept through death"));
    for (const k of d.keys) {
      const row = el("div", "row2"), info = el("div", "info"), nm = el("div", "nm");
      nm.appendChild(el("span", "pill" + (k.kind === "quest" ? " quest" : ""), k.kind)); nm.appendChild(document.createTextNode(" " + k.name));
      info.appendChild(nm); info.appendChild(el("div", "dt", k.detail + (k.source ? " · " + k.source : "")));
      row.appendChild(info); side.appendChild(row);
    }
  }
  side.appendChild(el("div", "hint", "Say it: drink a draught, drop the hides, sell the pelts to the hunter, brew a tonic… What you wear is in the Gear pane; your item box in Stash."));
}

// ---------- stash pane: the item box ----------
function renderStash(d) {
  side.appendChild(purse("Item box", d.where));
  side.appendChild(capRow("SLOTS", d.count, d.cap));
  if (!d.reachable) side.appendChild(el("div", "dimrow warn", "Not reachable from here: find an inn with storage, a guild hall with a strongroom, or your own house."));
  side.appendChild(h2("STORED"));
  if (!d.items.length) side.appendChild(el("div", "dimrow", "Nothing stored."));
  for (const x of d.items) side.appendChild(itemRow(x, false));
  side.appendChild(el("div", "hint", "Say 'put the longsword in the box' or 'take the bow out'. The box is in every inn with storage and in each home you own."));
}

// ---------- quests pane: what you hold, how far along, how long is left; the next rank as bars ----------
function renderQuests(d) {
  side.appendChild(purse(d.rank ? `Guild rank ${d.rank.rank}` : "Not a guild member"));
  side.appendChild(h2("IN HAND"));
  if (!d.rows.length) side.appendChild(el("div", "dimrow", "You have no contracts or requests in hand."));
  for (const q of d.rows) {
    const row = el("div", "row2"), info = el("div", "info");
    info.appendChild(el("div", "nm", `[${q.letter}] ${q.title}`));
    info.appendChild(el("div", "dt", q.for || (q.guild ? "guild contract" : "a request")));
    const pills = el("div", "pills");
    pills.appendChild(el("span", "pill" + (q.ready ? " gold" : /^\d+\/\d+$/.test(q.status) ? " ok" : ""), q.status));
    pills.appendChild(el("span", "pill" + (q.urgent ? " warn" : ""), q.left));
    info.appendChild(pills);
    const act = el("div", "act"); act.appendChild(shopButton("Abandon", `#questabandon ${q.id}`, true, true));
    row.append(info, act); side.appendChild(row);
  }
  if (d.rank && d.rank.next) {
    side.appendChild(h2("THE NEXT RANK", d.rank.next));
    for (const n of d.rank.needs) { const r = el("div", "req"); r.append(el("span", "lb", n.label), bar(Math.min(n.now, n.top), n.top, "--xp"), el("span", "num", `${n.now}/${n.top}`)); side.appendChild(r); }
    const r = el("div", "req"); r.append(el("span", "lb", "a trial"), el("span", "txt", d.rank.trial ? "you qualify: ask for the trial at a guild hall" : `against an examiner of rank ${d.rank.next}`)); side.appendChild(r);
  } else if (d.rank) side.appendChild(el("div", "dimrow", "There is no higher rank."));
}

// ---------- dungeon pane: the floors as bars ----------
function renderDungeon(d) {
  side.appendChild(purse(cap1(d.name)));
  const lead = el("div", "lead"); lead.append(`A ${d.theme} beneath ${d.beneath} · remade in `, el("b", "", `${d.remade_days} day${d.remade_days === 1 ? "" : "s"}`)); side.appendChild(lead);
  side.appendChild(h2("FLOORS"));
  for (const f of d.floors) {
    const m = el("div", "meter" + (d.on_floor === f.n ? " here" : "")), lb = el("span", "lb", `Floor ${f.n} `); lb.appendChild(el("span", "pill", f.letter));
    m.append(lb, bar(f.done, f.total, f.done >= f.total ? "--sp" : "--accent"), el("span", "num", `${f.done}/${f.total}`));
    if (f.boss) m.appendChild(el("span", "pill warn", "boss"));
    side.appendChild(m);
    if (f.sense) side.appendChild(el("div", "dimrow sense", "you sense: " + f.sense));
  }
  side.appendChild(el("div", "hint", d.on_floor ? `You are on floor ${d.on_floor}. Say 'go down' to press on, or 'climb out' to leave.` : "Say 'go down' at the entrance to delve. Your progress is kept until the place is remade."));
}

// ---------- home pane: what you own, what is for sale, the upgrades ----------
function renderHome(d) {
  if (!d.owned.length) side.appendChild(el("div", "dimrow", "You own no property yet."));
  for (const h of d.owned) {
    side.appendChild(purse(cap1(h.name), h.town));
    side.appendChild(el("div", "lead", (h.ruined ? "In ruins · " : "") + `yours since day ${h.day}` + (h.upgrades.length ? " · " + h.upgrades.map(cap1).join(", ") : "")));
  }
  if (d.for_sale) {
    side.appendChild(h2("FOR SALE HERE"));
    const row = el("div", "row2"), info = el("div", "info");
    info.appendChild(el("div", "nm", cap1(d.for_sale.name)));
    info.appendChild(el("div", "dt", "A land agent handles it; say 'buy a house'."));
    const act = el("div", "act"); act.appendChild(el("div", "val", d.for_sale.price));
    row.append(info, act); side.appendChild(row);
  }
  if (d.here) {
    side.appendChild(h2("UPGRADES"));
    for (const u of d.upgrades) {
      const row = el("div", "row2" + (u.state === "far" ? " far" : "")), info = el("div", "info"), nm = el("div", "nm", cap1(u.name));
      if (u.state === "built") { nm.appendChild(document.createTextNode(" ")); nm.appendChild(el("span", "pill ok", "built")); }
      info.append(nm, el("div", "dt", u.text)); row.appendChild(info);
      if (u.state !== "built") { const act = el("div", "act"); act.appendChild(el("div", "val" + (u.state === "far" ? " dim" : ""), u.state === "far" ? "far lands only" : u.price)); row.appendChild(act); }
      side.appendChild(row);
    }
    side.appendChild(el("div", "hint", `Say 'buy a hearth' (or garden, workshop, strongroom) to build one. Your purse: ${d.purse}.`));
  } else side.appendChild(el("div", "hint", `Your purse: ${d.purse}.`));
}

// ---------- standing pane: how this town regards you, what is said of you, the other towns, your titles ----------
function meterRow(label, value, word, scale) {
  const m = el("div", "meter sym"); m.appendChild(el("span", "lb", label));
  const t = el("div", "track"), pct = Math.min(50, Math.abs(value) / scale * 50);
  if (value > 0) { const f = el("div", "fillp"); f.style.width = pct + "%"; t.appendChild(f); }
  else if (value < 0) { const f = el("div", "filln"); f.style.width = pct + "%"; t.appendChild(f); }
  m.append(t, el("span", "wd", word)); return m;
}
function renderStanding(d) {
  if (d.wild) side.appendChild(el("div", "dimrow", "Nobody out here keeps a tally of you."));
  else {
    side.appendChild(purse(d.town));
    side.appendChild(meterRow("Townsfolk", d.value, d.word, 50));
    for (const g of d.groups) side.appendChild(meterRow(g.name, g.value, g.word, 100));
    if (!d.groups.length) side.appendChild(el("div", "dimrow", "No group here has formed an opinion of you yet."));
    side.appendChild(h2("WHAT IS SAID ABOUT YOU"));
    if (!d.rumors.length) side.appendChild(el("div", "dimrow", "Nobody here is talking about you."));
    for (const r of d.rumors) {
      const row = el("div", "row2"), info = el("div", "info"); info.appendChild(el("div", "tale", r.text)); row.appendChild(info);
      const act = el("div", "act"); act.appendChild(shopButton("Correct", `#correct ${r.n}`, true)); row.appendChild(act);
      side.appendChild(row);
    }
    if (d.rumors.length) side.appendChild(el("div", "hint", "A tale that is wrong can be set straight: Correct tries to, with whoever is here to hear it."));
  }
  if (d.elsewhere.length) { side.appendChild(h2("ELSEWHERE")); for (const e of d.elsewhere) side.appendChild(meterRow(e.name, e.value, e.word, 50)); }
  if (d.titles.length) { side.appendChild(h2("TITLES")); side.appendChild(el("div", "lead", d.titles.join(" · "))); }
}

// ---------- character pane: the worn pieces as rows (between the EQUIPMENT mark) ----------
const EQUIP_MARK = "@@EQUIPMENT@@";
function renderWorn(d) {
  if (!(d.worn || []).length) { side.appendChild(el("div", "dimrow", "nothing equipped")); return; }
  for (const w of d.worn) {
    const row = el("div", "row2 worn"), info = el("div", "info"), nm = el("div", "nm");
    nm.appendChild(el("span", "slotname", w.slot)); nm.appendChild(named(w, w.name));
    info.append(nm, el("div", "dt", tidy(w.detail))); row.appendChild(info); side.appendChild(row);
  }
}

// ---------- side pane ----------
let sideRaw = "", sidePanel = null, lastView = null;
const combat = { active: false, data: null, rows: [], seen: new Set(), mode: "view" };
const hitsMap = {};
function orderedCommands() {
  const all = state.debug ? [...COMMANDS, ["Pulse", "#pulse"]] : COMMANDS;
  const want = Array.isArray(state.prefs.order) ? state.prefs.order : [];
  const rank = (c) => { const i = want.indexOf(c[1]); return i < 0 ? 1000 + all.indexOf(c) : i; };
  return [...all].sort((a, b) => rank(a) - rank(b));      // buttons the player has placed come first, in their order; new ones keep their place at the end
}
let dragCmd = null;
function moveButton(from, to) {
  if (!from || from === to) return;
  const cmds = orderedCommands().map((c) => c[1]);
  cmds.splice(cmds.indexOf(from), 1);
  cmds.splice(cmds.indexOf(to), 0, from);
  setPrefs({ order: cmds });
}
function renderButtons() {
  const box = $("buttons"); box.textContent = "";
  for (const [label, cmd] of orderedCommands()) {
    const b = document.createElement("button");
    b.textContent = label + (state.prefs.pinned === cmd ? " 📌" : "");
    b.dataset.cmd = cmd;
    b.className = state.current === cmd ? "on" : "";
    b.disabled = !(state.prompt && state.atMain);
    b.onclick = () => runView(cmd);
    b.draggable = true;
    b.ondragstart = (e) => { dragCmd = cmd; e.dataTransfer.effectAllowed = "move"; try { e.dataTransfer.setData("text/plain", cmd); } catch (x) {} b.classList.add("dragging"); };
    b.ondragend = () => { dragCmd = null; b.classList.remove("dragging"); box.querySelectorAll(".dropat").forEach((x) => x.classList.remove("dropat")); };
    b.ondragover = (e) => { if (dragCmd) { e.preventDefault(); b.classList.add("dropat"); } };
    b.ondragleave = () => b.classList.remove("dropat");
    b.ondrop = (e) => { e.preventDefault(); const from = dragCmd; dragCmd = null; moveButton(from, cmd); };
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
  pin.title = state.current && state.prefs.pinned === state.current ? "Pinned: this view refreshes after every turn (click to unpin)" : "Pin this view: it refreshes after every turn";
  pin.disabled = !state.current || !PINNABLE.has(state.current);
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
  $("theme").title = "Colour theme: " + t + (t === "auto" ? " (follows Windows)" : "") + " - click to change";
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
  if (text.toLowerCase() === "#resetlayout") {
    await setPrefs({ order: [] });
    addEcho(text);
    addBlock("note", "The info pane's buttons are back in their original order.");
    return;
  }
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
      state.when = s.when;
      const [town, ...region] = s.place.split(" · ");
      el.innerHTML = `<div class="top"><span class="place">${esc(town)}${region.length ? `<span class="rg"> · ${esc(region.join(" · "))}</span>` : ""}</span>
        <span class="spot" title="${esc(s.spot)}">${esc(s.spot)}</span><span class="clock">${esc(s.when)}<span class="wx">${esc(s.weather)}</span></span></div>
        <div class="bars">${bar("HP", s.vitals.health, "--hp")}${bar("MP", s.vitals.mana, "--mp")}${bar("SP", s.vitals.stamina, "--sp")}${bar("XP", s.xp, "--xp")}
        <span class="right"><span class="lv">LV <b>${s.level}</b></span>${s.points ? `<span class="pts">${s.points} point${s.points === 1 ? "" : "s"} to spend</span>` : ""}<span class="coins">${esc(s.coins)}</span></span></div>`;
    },
  };
})();

// ---------- how a blow was worked out (the hover text) ----------
const tip = el("div", "tip"); tip.hidden = true; document.body.appendChild(tip);
function hitLines(h) {
  if (h.outcome === "heal") {
    const R = [["h", `${h.att} ${h.label} themselves`]];
    for (const [name, v] of h.extras || []) R.push(["", `  ${name}: ${v}`]);
    R.push(["h", h.final ? `Restored: ${h.final}` : h.figure.slice(1, -1)]);
    return R;
  }
  const L = [], b = h.base || {}, d = h.defence || {};
  const outcome = { miss: "miss", graze: "glancing blow", hit: "hit", crit: "critical hit", phase: "passes through" }[h.outcome] || h.outcome;
  L.push(["h", `${h.att} ${h.label} ${h.dfn}`]);
  if (h.chance) L.push(["", `To hit: needed ${h.need} or more (${h.chance}% chance), rolled ${h.roll} → ${outcome}`]);
  if (h.chance && (h.hit_steps || []).length > 1) {
    const sign = (v) => (v > 0 ? "+" : v < 0 ? "−" : "") + Math.abs(v);
    L.push(["dim", "  " + h.hit_steps.map(([n, v], i) => (i ? `${sign(v)} ${n}` : `${v} ${n}`)).join("  ") + `  =  ${h.chance}%`]);
  }
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
    const stat = d.kind === "magical" ? "ward" : "armour";
    L.push(["", `Defence (${d.kind}): ${d.who ? d.who + "'s " : ""}${stat} ${d.base_protection !== undefined ? d.base_protection : d.protection}`]);
    for (const [name, v] of d.prot_steps || []) L.push(["", `  ${v}  ${name}`]);
    if (d.base_protection !== undefined && (d.prot_steps || []).length) L.push(["", `  = ${d.protection} ${stat}`]);
    if (d.k !== undefined) {
      const raw = d.raw_reduction !== undefined ? d.raw_reduction : 100 * d.protection / Math.max(0.01, d.protection + d.k);
      L.push(["", `  ${d.protection} ${stat} = ${raw.toFixed(1)}% less damage` + (raw > d.reduction + 0.05 ? `, capped at ${d.reduction}%` : "")]);
    }
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
  if (!isYou) { head.appendChild(el("span", "band", x.where || "")); head.appendChild(el("span", "chp", `${x.hp}/${x.max_hp}`)); }
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
    const nm = el("div", "mvn"); nm.appendChild(el("span", "", m.name)); nm.appendChild(el("span", "mvc", (m.stamina_cost ? `${m.stamina_cost} stamina + ` : "") + `${m.cost} ${m.resource}` + (m.cooldown ? ` · cooldown ${m.cooldown}` : "")));
    row.appendChild(nm);
    row.appendChild(el("div", "mvs " + (m.ready ? "ready" : "wait"), m.ready ? "Ready" : m.reason));
    side.appendChild(row);
  }
  if ((d.items || []).length) {
    side.appendChild(el("div", "h2", "ITEMS"));
    for (const it of d.items) {
      const row = el("div", "mv" + (it.ready ? "" : " cool"));
      const nm = el("div", "mvn"); nm.appendChild(el("span", "", it.qty > 1 ? `${it.name} x${it.qty}` : it.name)); nm.appendChild(el("span", "mvc", it.text));
      row.appendChild(nm);
      if (it.ready) row.appendChild(shopButton("Use", `#useitem ${it.name}`, true));
      else row.appendChild(el("div", "mvs wait", it.reason));
      side.appendChild(row);
    }
  }
  side.appendChild(el("div", "h2", "COMBAT LOG")); side.lastChild.appendChild(el("span", "sub", "hover a line for the working"));
  const logEl = el("div", "clog"); let lastRound = null;
  for (const h of combat.rows) {
    if (h.round !== lastRound) { logEl.appendChild(el("div", "cr", `Round ${h.round}`)); lastRound = h.round; }
    const row = el("div", "cl " + (h.att_side === "enemy" ? "foe" : "friend")); row.dataset.hit = h.id;
    row.appendChild(el("span", "who", `${h.att} ${h.label} ${h.dfn}`));
    row.appendChild(el("span", "fig" + (h.outcome === "heal" ? " heal" : ""), h.figure || ""));
    logEl.appendChild(row);
  }
  side.appendChild(logEl);
  logEl.scrollTop = logEl.scrollHeight;
}
const labelOf = (cmd) => { const c = [...COMMANDS, ["Pulse", "#pulse"], ["Places", "#places"], ["Book", "#book"]].find((x) => x[1] === cmd); return c ? c[0] : (cmd || "").replace(/^#/, ""); };
function paintSide() {
  const showCombat = combat.active && combat.mode === "combat";
  const keep = side.scrollTop;
  side.textContent = "";
  if (showCombat) {
    renderCombat(); side.scrollTop = keep;
    const t = $("sidetitle"); t.textContent = "⚔ Combat";
    if (combat.data) t.appendChild(el("span", "sub", `round ${combat.data.round}` + (combat.data.danger ? ` · ${combat.data.danger}` : "")));
  }
  else if (lastView) {
    if (lastView.panel && lastView.panel.name === "shop") renderShop(lastView.panel.data);
    if (lastView.panel && lastView.panel.name === "gear") renderGear(lastView.panel.data);
    const pn = lastView.panel && lastView.panel.name;
    if (pn === "journal") renderJournal(lastView.panel.data);
    else if (pn === "inventory") renderInventory(lastView.panel.data);
    else if (pn === "stash") renderStash(lastView.panel.data);
    else if (pn === "quests") renderQuests(lastView.panel.data);
    else if (pn === "dungeon") renderDungeon(lastView.panel.data);
    else if (pn === "home") renderHome(lastView.panel.data);
    else if (pn === "standing") renderStanding(lastView.panel.data);
    else if (pn === "party") renderParty(lastView.panel.data);
    else if (pn === "stats") renderStats(lastView.panel.data);
    else if (pn === "board") renderBoard(lastView.panel.data);
    else if (pn === "places") renderPlaces(lastView.panel.data);
    else if (pn === "map") renderMap(lastView.panel.data);
    else if (pn === "pulse") renderPulse(lastView.panel.data);
    else if (pn === "character" && lastView.raw.includes(ATTR_MARK)) {
      const [before, after] = lastView.raw.split(ATTR_MARK + "\n");
      renderInto(side, before, "pane", false);
      renderAttrs(lastView.panel.data);
      const [mid, rest] = (after || "").split(ABIL_MARK + "\n");
      const [mid1, mid2] = mid.split(EQUIP_MARK + "\n");
      renderInto(side, mid1, "pane", false);
      if (mid2 !== undefined) { renderWorn(lastView.panel.data); renderInto(side, mid2, "pane", false); }
      if (rest !== undefined) renderAbilities(lastView.panel.data);
      if (rest) renderInto(side, rest, "pane", false);
    } else renderInto(side, lastView.raw, "pane", false);
    side.scrollTop = lastPanelCmd === lastView.cmd ? keep : 0; lastPanelCmd = lastView.cmd;
    $("sidetitle").textContent = labelOf(lastView.cmd);
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
    case "echo": tickerClear(); addEcho(ev.text); break;
    case "panel": sidePanel = ev; break;
    case "side_begin": sideRaw = ""; sidePanel = null; state.current = ev.cmd; $("sidetitle").textContent = labelOf(ev.cmd); break;
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
