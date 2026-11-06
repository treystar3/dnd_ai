"""(f521) A stand-in llama-server for the tests: an in-process http.server on a free loopback port that answers /health,
/v1/chat/completions and /v1/embeddings the way llama-server does (the shapes read in llama.cpp's own source and seen on the pod), and
keeps every request it was sent. A test scripts what it answers: a status, a body, a delay before answering, timings. While it waits out
a delay it watches the caller's socket, so a caller that hangs up is noticed and counted (disconnects), as llama-server notices it and
frees the slot. It can also run as its own process (python tools/sim/fake_llama.py --port N --api-key K), for the tests that start a
server as a child (f522).

    fake = FakeLlama(key="k")                     # started at once; fake.port, fake.url
    fake.script = lambda path, body, n: {"content": '{"x": "y"}'}
    ...
    fake.close()

A script returns a dict, any of: status (200), content (the answer's text), finish ('stop'), timings (merged over the defaults),
reasoning (the thinking text), delay (seconds before answering), payload (the whole body, sent as it is), vectors (for embeddings),
message and type (an error's), drop (the connection closed with no answer, as a crashing server leaves it).
loading = N answers the next N requests (any path) with 503 'Loading model'."""

from __future__ import annotations

import json
import select
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def _default(path, body, n):
    if path == "/v1/embeddings":
        return {"vectors": [[1.0, 0.0, 0.0] for _ in (body.get("input") or [])]}
    return {"content": "{}"}


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):          # quiet
        pass

    @property
    def fake(self) -> "FakeLlama":
        return self.server.fake

    def _gone(self) -> bool:
        try:
            r, _, _ = select.select([self.connection], [], [], 0)
            if r:
                return self.connection.recv(1, socket.MSG_PEEK) == b""
        except OSError:
            return True
        return False

    def _send(self, status: int, payload) -> None:
        data = (payload if isinstance(payload, str) else json.dumps(payload)).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(data)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _loading(self) -> bool:
        with self.fake._lock:
            if self.fake.loading > 0:
                self.fake.loading -= 1
                return True
        return False

    def do_GET(self):
        if self._loading():
            return self._send(503, {"error": {"code": 503, "message": "Loading model", "type": "unavailable_error"}})
        if self.path == "/health":
            return self._send(200, {"status": "ok"})
        if self.path == "/props":
            return self._send(200, {"default_generation_settings": {"n_ctx": self.fake.slot_ctx}, "total_slots": self.fake.slots})
        return self._send(404, {"error": {"code": 404, "message": "File Not Found", "type": "not_found_error"}})

    def do_POST(self):
        size = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(size) if size else b""
        try:
            body = json.loads(raw.decode("utf-8")) if raw else {}
        except ValueError:
            body = {}
        with self.fake._lock:
            n = len(self.fake.requests)
            self.fake.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()}, "body": body,
                                       "raw": raw, "at": time.monotonic()})
        if self.fake.key and self.headers.get("Authorization", "") != f"Bearer {self.fake.key}":
            return self._send(401, {"error": {"code": 401, "message": "Invalid API Key", "type": "authentication_error"}})
        if self._loading():
            return self._send(503, {"error": {"code": 503, "message": "Loading model", "type": "unavailable_error"}})
        spec = (self.fake.script or _default)(self.path, body, n) or {}
        if spec.get("drop"):                            # the server dies mid-call: the connection closes with no answer
            self.close_connection = True
            try:
                self.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            return
        delay = float(spec.get("delay") or 0)
        end = time.monotonic() + delay
        while time.monotonic() < end:                   # waiting out the delay, watching for the caller hanging up
            if self._gone():
                with self.fake._lock:
                    self.fake.disconnects += 1
                    self.fake.disconnected_at.append(time.monotonic())
                return
            time.sleep(0.02)
        if "payload" in spec:
            return self._send(int(spec.get("status", 200)), spec["payload"])
        status = int(spec.get("status", 200))
        if status != 200:
            return self._send(status, {"error": {"code": status, "message": spec.get("message", "error"), "type": spec.get("type", "server_error")}})
        if self.path == "/v1/embeddings":
            vecs = spec.get("vectors") or []
            return self._send(200, {"object": "list", "data": [{"object": "embedding", "index": i, "embedding": v} for i, v in enumerate(vecs)],
                                    "usage": {"prompt_tokens": sum(len(str(t)) // 4 for t in body.get("input") or [])}})
        timings = {"cache_n": 0, "prompt_n": 100, "prompt_ms": 50.0, "predicted_n": 20, "predicted_ms": 200.0, **(spec.get("timings") or {})}
        msg = {"role": "assistant", "content": spec.get("content", "{}")}
        if spec.get("reasoning"):
            msg["reasoning_content"] = spec["reasoning"]
        return self._send(200, {"choices": [{"index": 0, "finish_reason": spec.get("finish", "stop"), "message": msg}],
                                "usage": {"prompt_tokens": timings["prompt_n"] + timings["cache_n"], "completion_tokens": timings["predicted_n"]},
                                "timings": timings, "id_slot": body.get("id_slot", 0)})


class FakeLlama:
    def __init__(self, key: str = "", slot_ctx: int = 16384, slots: int = 2, loading: int = 0, script=None, port: int = 0):
        self.key, self.slot_ctx, self.slots, self.loading, self.script = key, slot_ctx, slots, loading, script
        self.requests: list[dict] = []
        self.disconnects = 0
        self.disconnected_at: list[float] = []
        self._lock = threading.Lock()
        self.httpd = ThreadingHTTPServer(("127.0.0.1", port), _Handler)
        self.httpd.daemon_threads = True
        self.httpd.fake = self
        self.port = self.httpd.server_address[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self._thread = threading.Thread(target=self.httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        self._thread.start()

    def chats(self) -> list[dict]:
        return [r for r in self.requests if r["path"] == "/v1/chat/completions"]

    def close(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


def main(argv: list[str]) -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=0)
    ap.add_argument("--api-key", default="")
    ap.add_argument("--slot-ctx", type=int, default=16384)
    ap.add_argument("--loading", type=int, default=0)
    a, _ = ap.parse_known_args(argv)
    fake = FakeLlama(key=a.api_key, slot_ctx=a.slot_ctx, loading=a.loading, port=a.port)
    print(f"fake llama-server listening on 127.0.0.1:{fake.port}", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        fake.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
