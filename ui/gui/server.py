"""A tiny local web server for the GUI: serves the page, streams events out (SSE) and takes typed lines in (POST).

Bound to 127.0.0.1 only. Every request except the static files needs the random token the page was opened with, and the Host
header must be the local address, so no other site or machine can drive the game."""

import json
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from core import paths
from urllib.parse import parse_qs, urlparse

WEB = (paths.BUNDLE / "ui" / "gui" / "web") if paths.FROZEN else Path(__file__).resolve().parent / "web"
STATIC = {"/app.js": "text/javascript; charset=utf-8", "/style.css": "text/css; charset=utf-8"}
PREF_DEFAULTS = {"pinned": "#character", "width": 400, "hidden": False, "theme": "auto"}


def prefs_path() -> Path:
    from storage.campaign import SAVES_DIR
    return SAVES_DIR / "gui_prefs.json"


def load_prefs() -> dict:
    try:
        raw = json.loads(prefs_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raw = {}
    out = dict(PREF_DEFAULTS)
    if "pinned" in raw and (raw["pinned"] is None or isinstance(raw["pinned"], str)):
        out["pinned"] = "#character" if raw["pinned"] == "#system" else raw["pinned"]
    if isinstance(raw.get("width"), (int, float)):
        out["width"] = max(240, min(900, int(raw["width"])))
    if isinstance(raw.get("hidden"), bool):
        out["hidden"] = raw["hidden"]
    if raw.get("theme") in ("auto", "light", "dark"):
        out["theme"] = raw["theme"]
    return out


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
                n = min(int(self.headers.get("Content-Length") or 0), 65536)
                data = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._json(400, {"error": "bad json"})
            if u.path == "/input":
                text = data.get("text")
                if not isinstance(text, str):
                    return self._json(400, {"error": "text"})
                if text.startswith("#") and not bridge.at_main:
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
                if cmd is not None and not (isinstance(cmd, str) and cmd.startswith("#") and len(cmd) < 40):
                    return self._json(400, {"error": "command"})
                bridge.pinned = cmd
                bridge.dirty = False
                return self._json(200, {"ok": True})
            if u.path == "/prefs":
                return self._json(200, save_prefs(data if isinstance(data, dict) else {}))
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
