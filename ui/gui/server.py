"""A tiny local web server for the GUI: serves the page, streams events out (SSE) and takes typed lines in (POST).

Bound to 127.0.0.1 only. Every request except the static files needs the random token the page was opened with, and the Host
header must be the local address, so no other site or machine can drive the game."""

import json
import re
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from core import paths
from urllib.parse import parse_qs, urlparse

from ui.gui.bridge import MENU, PINNABLE

WEB = (paths.BUNDLE / "ui" / "gui" / "web") if paths.FROZEN else Path(__file__).resolve().parent / "web"
STATIC = {"/app.js": "text/javascript; charset=utf-8", "/style.css": "text/css; charset=utf-8", "/map.jpg": "image/jpeg",
          "/home_bg.jpg": "image/jpeg"}     # (f345) the home page's backdrop: the map without its names, cropped past the west coast
for _f in ("literata-latin-400-normal", "literata-latin-400-italic", "literata-latin-600-normal", "literata-latin-700-normal"):
    STATIC[f"/fonts/{_f}.woff2"] = "font/woff2"                       # (f326) the reading face for the story column
STATIC["/fonts/cinzel-decorative-latin-700-normal.woff2"] = "font/woff2"   # (f345) the game's name on the home page
PREF_DEFAULTS = {"pinned": "#character", "width": 400, "hidden": False, "theme": "dark", "order": [], "text": {}, "measure": "full"}
MEASURES = ("narrow", "book", "wide", "full")       # the story column's width (app.js MEASURES): full stretches to the pane's edges
TEXT_KINDS = ("narration", "speech", "speaker", "note", "wait", "combat", "echo", "pane")   # what the Settings pane styles (app.js TEXT_KINDS)
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
MAX_BODY = 65536



def prefs_path() -> Path:
    from storage.campaign import SAVES_DIR
    return SAVES_DIR / "gui_prefs.json"


def load_prefs() -> dict:
    try:
        raw = json.loads(prefs_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    out = dict(PREF_DEFAULTS)
    if raw.get("pinned") is None and "pinned" in raw:
        out["pinned"] = None
    elif isinstance(raw.get("pinned"), str):
        out["pinned"] = raw["pinned"] if raw["pinned"] in PINNABLE else "#character"
    if isinstance(raw.get("width"), (int, float)):
        out["width"] = max(240, min(900, int(raw["width"])))
    if isinstance(raw.get("hidden"), bool):
        out["hidden"] = raw["hidden"]
    if raw.get("theme") in ("auto", "light", "dark"):
        out["theme"] = raw["theme"]
    if _good_order(raw.get("order")):
        out["order"] = list(raw["order"])
    if _good_text(raw.get("text")):
        out["text"] = raw["text"]
    if raw.get("measure") in MEASURES:
        out["measure"] = raw["measure"]
    return out


def _good_order(v) -> bool:
    return isinstance(v, list) and len(v) <= 40 and all(isinstance(x, str) and x.startswith("#") and len(x) <= 24 for x in v)


def _good_text(v) -> bool:
    """{kind: {size?: 10..28, dark?: '#rrggbb', light?: '#rrggbb'}} for the kinds the window styles, nothing else."""
    if not isinstance(v, dict) or len(v) > len(TEXT_KINDS):
        return False
    for kind, spec in v.items():
        if kind not in TEXT_KINDS or not isinstance(spec, dict):
            return False
        for f, x in spec.items():
            if f == "size":
                if isinstance(x, bool) or not isinstance(x, (int, float)) or not 10 <= x <= 28:
                    return False
            elif f in ("dark", "light"):
                if not isinstance(x, str) or not _HEX.match(x):
                    return False
            else:
                return False
    return True


def prefs_problem(new) -> str:
    """Why these settings cannot be saved, or "" when every value is the right kind."""
    if not isinstance(new, dict):
        return "settings must be an object"
    for k, v in new.items():
        if k not in PREF_DEFAULTS:
            continue
        if k == "pinned" and not (v is None or (isinstance(v, str) and v in PINNABLE)):
            return "pinned must be a view that can be pinned"
        if k == "width" and not (isinstance(v, (int, float)) and not isinstance(v, bool)):
            return "width must be a number"
        if k == "hidden" and not isinstance(v, bool):
            return "hidden must be true or false"
        if k == "theme" and v not in ("auto", "light", "dark"):
            return "theme must be auto, light or dark"
        if k == "order" and not _good_order(v):
            return "order must be a list of commands"
        if k == "text" and not _good_text(v):
            return "text must be sizes (10-28) and colours (#rrggbb, per theme) by kind"
        if k == "measure" and v not in MEASURES:
            return "measure must be narrow, book, wide or full"
    return ""


def save_prefs(new: dict) -> dict:
    prefs = load_prefs()
    for k in PREF_DEFAULTS:
        if k in new:
            prefs[k] = new[k]
    prefs = {**PREF_DEFAULTS, **{k: v for k, v in prefs.items() if k in PREF_DEFAULTS}}
    try:
        prefs_path().parent.mkdir(parents=True, exist_ok=True)
        prefs_path().write_text(json.dumps(prefs), encoding="utf-8")
    except OSError:
        pass
    return load_prefs()


def make_server(bridge, token: str | None = None):
    token = token or secrets.token_urlsafe(16)

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *a):
            pass

        def _host_ok(self) -> bool:
            host = (self.headers.get("Host") or "").split(":")[0]
            return host in ("127.0.0.1", "localhost", "[::1]")

        def _authed(self, query) -> bool:
            return self._host_ok() and (self.headers.get("X-Token") or (query.get("t") or [""])[0]) == token

        def _send(self, code, body: bytes, ctype="application/json"):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _json(self, code, obj):
            self._send(code, json.dumps(obj).encode("utf-8"))

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if not self._host_ok():
                return self._send(403, b"forbidden", "text/plain")
            if u.path in STATIC:
                return self._send(200, (WEB / u.path[1:]).read_bytes(), STATIC[u.path])
            if not self._authed(q):
                return self._send(403, b"forbidden", "text/plain")
            if u.path == "/":
                html = (WEB / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", token)
                return self._send(200, html.encode("utf-8"), "text/html; charset=utf-8")
            if u.path == "/prefs":
                return self._json(200, load_prefs())
            if u.path == "/events":
                return self._events(q)
            self._send(404, b"not found", "text/plain")

        def _events(self, q):
            try:
                last = int(self.headers.get("Last-Event-ID") or (q.get("after") or ["0"])[0])
            except ValueError:
                last = 0
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            try:
                while True:
                    evs = bridge.since(last)
                    if evs:
                        chunk = "".join(f"id: {i}\ndata: {json.dumps(e)}\n\n" for i, e in evs)
                        last = evs[-1][0]
                    elif bridge.closed and bridge.finished.is_set():
                        return
                    else:
                        chunk = ": ping\n\n"
                    self.wfile.write(chunk.encode("utf-8"))
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionError, OSError):
                return

        def do_POST(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            if not self._authed(q):
                return self._send(403, b"forbidden", "text/plain")
            try:
                n = int(self.headers.get("Content-Length") or 0)
            except ValueError:
                return self._json(400, {"error": "bad length"})
            if n > MAX_BODY:
                return self._json(413, {"error": "too large"})
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json(400, {"error": "bad json"})
            if u.path == "/input":
                text = data.get("text")
                if not isinstance(text, str):
                    return self._json(400, {"error": "text"})
                if text.startswith("#") and not bridge.at_main and not (bridge.at_menu and text.strip().lower() in MENU):
                    return self._json(409, {"error": "not at the main prompt"})
                return self._json(200, {"ok": True}) if bridge.submit(text[:2000]) else self._json(409, {"error": "not waiting"})
            if u.path == "/update":
                from core import updates
                info = bridge.update_info
                if not info:
                    return self._json(409, {"error": "no update"})
                def work():
                    bridge.emit(k="update_progress", frac=0.0, text="Starting...")
                    error = updates.install(info, lambda f, t: bridge.emit(k="update_progress", frac=round(f, 3), text=t), bridge.close)
                    bridge.emit(k="update_progress", frac=1.0, text=error or "Installing the update - the game will close and come back.", error=bool(error))
                threading.Thread(target=work, daemon=True).start()
                return self._json(200, {"ok": True})
            if u.path == "/pin":
                cmd = data.get("command")
                if cmd is not None and not (isinstance(cmd, str) and cmd in PINNABLE):
                    return self._json(400, {"error": "that view cannot be pinned"})
                bridge.pinned = cmd
                bridge.dirty = False
                return self._json(200, {"ok": True})
            if u.path == "/prefs":
                problem = prefs_problem(data)
                if problem:
                    return self._json(400, {"error": problem})
                return self._json(200, save_prefs(data))
            self._send(404, b"not found", "text/plain")

    class Server(ThreadingHTTPServer):
        daemon_threads = True

    srv = Server(("127.0.0.1", 0), Handler)
    srv.token = token
    srv.url = f"http://127.0.0.1:{srv.server_address[1]}/?t={token}"
    return srv


def serve(srv) -> threading.Thread:
    t = threading.Thread(target=srv.serve_forever, daemon=True, name="gui-server")
    t.start()
    return t
