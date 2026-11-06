"""(f521) The llama-server adapter: the request as llama-server takes it, sent and read back on the neutral kinds. Behind a switch, not yet
used: the game's default source stays the Ollama-shaped one until f528 (GOALS.md, owner's decisions of 2026-11-05: the game ships
llama.cpp's llama-server; "let's go with the neutral"). DND_BACKEND=llama with DND_LLAMA_URL (and DND_LLAMA_KEY, DND_LLAMA_EMBED_URL)
points a session at a llama-server someone started by hand, for the measurements f527 waits on; f522 starts and stops the server itself.

The body (llama_body) is pure: the request and the machine's facts in, the dict sent out, the same bytes for the same inputs (body_bytes).
- messages as the gateway made them; the schema as llama-server's JSON grammar (response_format json_schema, strict);
- every sampler, BASE under the task's own values (llm/sampling.py Sampling.resolved), so llama-server's own defaults (top_k 40,
  min_p 0.05, its repeat window) never apply: the table every night ran on, the owner's "keep them as they are";
- n_predict, the answer's ceiling (with a thinking task's room, as Ollama's num_predict carried it, f534);
- thinking off on every request unless the task was chosen to think (config.THINK_TASKS): chat_template_kwargs enable_thinking,
  which the pod confirmed on 407 of 407 calls, and without which the model thinks (scratchpad pod533 report);
- cache_prompt; id_slot from the machine (the lane's slot, f523); a voice's adapter as lora, from the machine.
What the machine adds (the slot, the adapter's index) is never in the request's own fingerprint (neutral, neutral_hash): a request
hashes the same whichever slot it ran on. f527 makes neutral_hash the recorder's request hash.

The transport is the standard library's http.client to the loopback address with the launch's bearer key: it reads no proxy settings
(the sandbox and a player's machine may both set HTTPS_PROXY). The caller waits on its own socket in half-second steps (select),
watching its deadline and its cancel flag; a cancel closes the caller's own connection, which llama-server notices within about a
second and frees the slot (measured on the pod: 1.02, 1.02 and 0.05 s).

What comes back, on the neutral kinds (llm/errors.py):
- 503 while the model loads is waited on, in steps, and is not a try: neither the deadline's clock nor a try counts the wait, which
  load_wait bounds (then 'loading');
- 400 exceed_context_size_error is too_big; any other 400, 401, 403 or 404 is invalid, as is a 500 the grammar converter raises over a
  schema (the pod saw "JSON schema error", no fault of the server's); an embed text past the batch is a 500 "too large to process",
  too_big; any other 5xx is the server's;
- a connection refused or reset is unreachable; the deadline passing is deadline; a cancel is cancelled (the interface makes it
  Cancelled, never a failed try).
usage: prompt (the tokens read, prompt_n plus cache_n), out (written, thinking included), read_ms, write_ms, total_ms, cached, wait_ms
(the wall time the server's own timings do not show: the cache copy, the queue), finish, and full: a 'length' answer whose request and
answer filled the slot's context (the gateway's too_big, f516). load_ms goes: llama-server loads once, at start."""

from __future__ import annotations

import hashlib
import http.client
import json
import os
import select
import socket
import threading
import time

import config
from llm.errors import Failure

SAMPLER_KEYS = ("temperature", "top_k", "top_p", "min_p", "typical_p", "repeat_penalty", "repeat_last_n", "presence_penalty",
                "frequency_penalty", "dry_multiplier", "xtc_probability")
# Each sampler's lowest and highest sensible value, and whether it is a whole number: data_check refuses anything else, so a misspelt
# or out-of-range key in config.SAMPLING cannot pass through to llama-server and be ignored there (sampler_problems).
RANGES = {"temperature": (0.0, 2.0, False), "top_k": (0, 1000, True), "top_p": (0.0, 1.0, False), "min_p": (0.0, 1.0, False),
          "typical_p": (0.0, 1.0, False), "repeat_penalty": (0.5, 2.0, False), "repeat_last_n": (-1, 8192, True),
          "presence_penalty": (-2.0, 2.0, False), "frequency_penalty": (-2.0, 2.0, False), "dry_multiplier": (0.0, 5.0, False),
          "xtc_probability": (0.0, 1.0, False)}
STEP = 0.5                  # the caller looks at its deadline and its cancel flag this often while it waits
CONNECT_SECONDS = 5.0       # a loopback connect that takes longer than this is a server that is not there
LOAD_WAIT = 600.0           # the longest a call waits on a model still loading before it is 'loading' (f522 reads data/runtime)
INVALID = (400, 401, 403, 404, 405, 413, 422)


# ------------------------------------------------------------------ the request

def _schema(req) -> dict:
    return req.schema.model_json_schema()


def thinks(req) -> bool:
    s = req.sampling
    return bool(config.THINK) if getattr(s, "think", None) is None else bool(s.think)


def neutral(req) -> dict:
    """What a request is, whatever machine it runs on: its messages, its schema's title and fingerprint, every sampler, its ceiling, its
    voice, the model, and whether it thinks. Nothing of the machine (slot, adapter index, threads, context) and never the deadline."""
    from llm import backend
    schema = _schema(req)
    room = backend.think_room(req.messages, req.max_tokens) if getattr(req.sampling, "think", None) else 0
    return {"model": config.MODEL, "messages": req.messages, "schema": schema.get("title") or req.schema.__name__,
            "schema_sha": hashlib.sha256(json.dumps(schema, sort_keys=True).encode("utf-8")).hexdigest()[:16],
            "sampling": req.sampling.resolved(), "max_tokens": int(req.max_tokens) + room, "think": thinks(req),
            "voice": req.voice or None}


def neutral_hash(req) -> str:
    return hashlib.sha256(json.dumps(neutral(req), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def llama_body(req, machine: dict | None = None) -> dict:
    """The body llama-server's /v1/chat/completions is sent for this request on this machine. Pure: no clock, no thread, no state."""
    from llm import backend
    m = machine or {}
    schema = _schema(req)
    room = backend.think_room(req.messages, req.max_tokens) if getattr(req.sampling, "think", None) else 0
    resolved = req.sampling.resolved()
    body = {"model": config.MODEL, "messages": req.messages,
            "response_format": {"type": "json_schema",
                                "json_schema": {"name": schema.get("title") or req.schema.__name__, "schema": schema, "strict": True}}}
    body.update({k: resolved[k] for k in SAMPLER_KEYS})                 # every sampler, in one fixed order
    body.update({"n_predict": int(req.max_tokens) + room, "chat_template_kwargs": {"enable_thinking": thinks(req)},
                 "cache_prompt": True, "stream": False})
    if m.get("slot") is not None:
        body["id_slot"] = int(m["slot"])
    if req.voice:
        adapters = m.get("lora") or {}
        if req.voice not in adapters:
            raise Failure("invalid", f"no adapter loaded for the voice {req.voice!r}")
        body["lora"] = [{"id": int(i), "scale": 1.0 if int(i) == int(adapters[req.voice]) else 0.0} for i in sorted(set(adapters.values()))]
    return body


def body_bytes(body: dict) -> bytes:
    return json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def embed_body(texts: list[str]) -> dict:
    return {"model": config.EMBED_MODEL, "input": list(texts), "encoding_format": "float"}


# ------------------------------------------------------------------ the transport

def _error_of(status: int, payload) -> Failure:
    """A refused answer's status and body on the kinds (the 503 of a loading model is waited on before this is reached)."""
    err = (payload.get("error") if isinstance(payload, dict) else None) or {}
    if isinstance(err, str):
        err = {"message": err}
    kind_word, message = str(err.get("type") or ""), str(err.get("message") or (payload if isinstance(payload, str) else ""))
    text = f"{status} {kind_word}: {message}".strip()[:300]
    low = (kind_word + " " + message).lower()
    if "exceed_context" in low or "context size" in low:
        return Failure("too_big", text)
    if status in INVALID:
        return Failure("invalid", text)
    if status >= 500 and "too large to process" in low:
        return Failure("too_big", text)                 # an embed text past the batch (the pod: an instant 500)
    if status >= 500 and ("json schema" in low or "grammar" in low):
        return Failure("invalid", text)                 # the schema would not convert: no fault of the server's, no use trying again
    return Failure("server", text)


class Server:
    """One llama-server at host:port, reached with its launch's key."""

    def __init__(self, port: int, key: str = "", host: str = "127.0.0.1", load_wait: float = LOAD_WAIT, step: float = STEP):
        self.host, self.port, self.key = host, int(port), key or ""
        self.load_wait, self.step = float(load_wait), float(step)
        self.loading_seconds = 0.0          # the time calls spent waiting on a loading model (not on any deadline's clock)

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json", "Connection": "close"}
        if self.key:
            h["Authorization"] = f"Bearer {self.key}"
        return h

    def _once(self, method: str, path: str, data: bytes | None, until: float | None, cancel: threading.Event | None):
        """One request and its answer: (status, payload, server-side wall ms). Raises Failure for the connection's own troubles."""
        conn = http.client.HTTPConnection(self.host, self.port, timeout=CONNECT_SECONDS)
        try:
            try:
                conn.connect()
            except (ConnectionRefusedError, socket.timeout, OSError) as e:
                raise Failure("unreachable", f"{type(e).__name__}: {e}"[:200]) from e
            conn.sock.settimeout(None)
            try:
                conn.request(method, path, body=data, headers=self._headers())
            except (BrokenPipeError, ConnectionResetError, OSError) as e:
                raise Failure("unreachable", f"{type(e).__name__}: {e}"[:200]) from e
            while True:                                 # the caller waits on its own socket, in steps
                if cancel is not None and cancel.is_set():
                    raise Failure("cancelled", "the call was cancelled")
                left = None if until is None else until - time.monotonic()
                if left is not None and left <= 0:
                    raise Failure("deadline", "the call ran past its limit")
                ready, _, _ = select.select([conn.sock], [], [], self.step if left is None else max(0.0, min(self.step, left)))
                if ready:
                    break
            left = None if until is None else max(0.5, until - time.monotonic())
            conn.sock.settimeout(left)
            try:
                resp = conn.getresponse()
                raw = resp.read()
            except socket.timeout as e:
                raise Failure("deadline", "the call ran past its limit") from e
            except (http.client.RemoteDisconnected, ConnectionResetError, BrokenPipeError, http.client.IncompleteRead) as e:
                raise Failure("unreachable", f"{type(e).__name__}: {e}"[:200]) from e
            text = raw.decode("utf-8", errors="replace")
            try:
                payload = json.loads(text) if text else {}
            except ValueError:
                payload = text
            return resp.status, payload
        finally:
            conn.close()                                # a cancel or a deadline closes the caller's own connection: the server frees the slot

    def request(self, method: str, path: str, body: dict | None = None, deadline: float | None = None,
                cancel: threading.Event | None = None):
        """The answer's (status, payload, wall ms, loading ms). A 503 while the model loads is waited on, off the deadline's clock and not
        a try, up to load_wait; deadline is the seconds this call may take (None: config.REQUEST_TIMEOUT, the hang guard outside a turn)."""
        data = body_bytes(body) if body is not None else None
        limit = float(config.REQUEST_TIMEOUT) if deadline is None else float(deadline)
        start = time.monotonic()
        waited = 0.0
        while True:
            t0 = time.monotonic()
            status, payload = self._once(method, path, data, t0 + max(0.0, limit - (t0 - start - waited)), cancel)
            if status != 503:
                return status, payload, (time.monotonic() - start - waited) * 1000.0, waited * 1000.0
            if waited >= self.load_wait:
                raise Failure("loading", f"the model was still loading after {int(waited)} s")
            w0 = time.monotonic()
            while time.monotonic() - w0 < self.step:         # wait a step, watching the cancel flag
                if cancel is not None and cancel.is_set():
                    raise Failure("cancelled", "the call was cancelled while the model loaded")
                time.sleep(min(0.05, self.step))
            waited += time.monotonic() - t0             # the whole 503 round is the load's, not the call's
            self.loading_seconds += time.monotonic() - t0

    def health(self) -> str:
        """'ready', 'loading' or 'unreachable', from /health."""
        try:
            status, _ = self._once("GET", "/health", None, time.monotonic() + CONNECT_SECONDS, None)
        except Failure:
            return "unreachable"
        return "ready" if status == 200 else "loading" if status == 503 else "unreachable"


# ------------------------------------------------------------------ the source

def usage_of(payload: dict, wall_ms: float, slot_ctx: int | None) -> dict:
    ch = (payload.get("choices") or [{}])[0]
    t = payload.get("timings") or {}
    u = payload.get("usage") or {}
    cached = int(t.get("cache_n") or 0)
    prompt = int(t["prompt_n"]) + cached if "prompt_n" in t else int(u.get("prompt_tokens") or 0)
    out = int(t["predicted_n"]) if "predicted_n" in t else int(u.get("completion_tokens") or 0)
    read_ms, write_ms = round(float(t.get("prompt_ms") or 0)), round(float(t.get("predicted_ms") or 0))
    finish = ch.get("finish_reason")
    full = bool(finish == "length" and slot_ctx and prompt + out >= int(slot_ctx))
    return {"prompt": prompt, "out": out, "read_ms": read_ms, "write_ms": write_ms, "total_ms": read_ms + write_ms, "cached": cached,
            "wait_ms": max(0, round(wall_ms - read_ms - write_ms)), "finish": finish, "full": full}


class LlamaServer:
    """A model source on the interface (llm/backend.py): chat on one llama-server, embeddings on another (or none). machine holds what
    the request does not: the slot each lane uses, the voices' adapters, the slot's context (to tell a full slot), the model ids."""

    name = "llama-server"

    def __init__(self, chat: Server, embed: Server | None = None, machine: dict | None = None):
        self.chat_server, self.embed_server = chat, embed
        self.machine = dict(machine or {})
        self._live: dict[int, threading.Event] = {}     # a thread's call in flight -> its cancel flag
        self._lock = threading.Lock()

    def _flag(self, cancel):
        flag = cancel if cancel is not None else threading.Event()
        with self._lock:
            self._live[threading.get_ident()] = flag
        return flag

    def _done(self):
        with self._lock:
            self._live.pop(threading.get_ident(), None)

    def cancel(self, thread_ident: int | None = None) -> int:
        """Cancel the call a thread has in flight (every call when no thread is named); returns how many were cancelled."""
        with self._lock:
            flags = [f for t, f in self._live.items() if thread_ident is None or t == thread_ident]
        for f in flags:
            f.set()
        return len(flags)

    def _machine_for_lane(self) -> dict:
        from llm import backend
        lane = backend.current_lane()
        m = dict(self.machine)
        slots = m.pop("slots", None) or {}
        if lane in slots:
            m["slot"] = slots[lane]
        return m

    def chat(self, req, deadline=None, cancel: threading.Event | None = None):
        from llm.backend import Reply
        body = llama_body(req, self._machine_for_lane())
        flag = self._flag(cancel)
        try:
            status, payload, wall_ms, _ = self.chat_server.request("POST", "/v1/chat/completions", body, deadline, flag)
        finally:
            self._done()
        if status != 200 or not isinstance(payload, dict) or "choices" not in payload:
            raise _error_of(status, payload)
        ch = (payload.get("choices") or [{}])[0]
        msg = ch.get("message") or {}
        usage = usage_of(payload, wall_ms, self.machine.get("slot_ctx"))
        return Reply(text=msg.get("content") or "", finish=ch.get("finish_reason"), usage=usage)

    def embed(self, texts: list[str]):
        from llm.backend import Embedding
        if self.embed_server is None:
            raise Failure("unreachable", "this llama-server source has no embedder")
        flag = self._flag(None)
        try:
            status, payload, wall_ms, _ = self.embed_server.request("POST", "/v1/embeddings", embed_body(texts), None, flag)
        finally:
            self._done()
        if status != 200 or not isinstance(payload, dict) or "data" not in payload:
            raise _error_of(status, payload)
        rows = sorted(payload.get("data") or [], key=lambda r: r.get("index", 0))
        if len(rows) != len(texts):
            raise Failure("server", f"{len(rows)} embeddings for {len(texts)} texts")
        return Embedding(vectors=[r.get("embedding") or [] for r in rows],
                         usage={"prompt": int((payload.get("usage") or {}).get("prompt_tokens") or 0), "wall_ms": round(wall_ms)})

    def _wait_ready(self) -> None:
        for s in [self.chat_server] + ([self.embed_server] if self.embed_server else []):
            start = time.monotonic()
            while True:
                h = s.health()
                if h == "ready":
                    break
                if h == "unreachable":
                    raise Failure("unreachable", f"no llama-server on port {s.port}")
                if time.monotonic() - start > s.load_wait:
                    raise Failure("loading", f"the model was still loading after {int(s.load_wait)} s")
                time.sleep(s.step)

    def load(self, progress=None) -> None:
        """Wait for the chat server (and the embedder) to say ready, through the layers as the model's load (the busy light shows while
        it waits); f522 starts them. 'loading' after load_wait, 'unreachable' at once."""
        from llm import backend
        backend.loading(self._wait_ready)

    def close(self) -> None:
        self.cancel()

    def state(self) -> str:
        h = self.chat_server.health()
        return "ready" if h == "ready" else "loading" if h == "loading" else "failed"

    def facts(self) -> dict:
        return {"source": self.name, "model": config.MODEL, "embed_model": config.EMBED_MODEL, "embedder": self.embed_server is not None,
                "slot_ctx": self.machine.get("slot_ctx")}


# ------------------------------------------------------------------ the switch, and the data's check

def _port_of(url: str) -> tuple[str, int]:
    rest = url.split("://", 1)[-1].split("/", 1)[0]
    host, _, port = rest.rpartition(":")
    return (host or "127.0.0.1"), int(port or 80)


def from_env() -> LlamaServer:
    """The source DND_BACKEND=llama names: a llama-server started by hand at DND_LLAMA_URL (its key DND_LLAMA_KEY), and its embedder at
    DND_LLAMA_EMBED_URL when there is one. Only the loopback address: a game never sends its prompts off the machine."""
    host, port = _port_of(os.environ.get("DND_LLAMA_URL", "http://127.0.0.1:8080"))
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError(f"DND_LLAMA_URL must be on this machine (127.0.0.1), not {host}")
    chat = Server(port, os.environ.get("DND_LLAMA_KEY", ""), host="127.0.0.1")
    embed = None
    if os.environ.get("DND_LLAMA_EMBED_URL"):
        ehost, eport = _port_of(os.environ["DND_LLAMA_EMBED_URL"])
        if ehost not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError(f"DND_LLAMA_EMBED_URL must be on this machine (127.0.0.1), not {ehost}")
        embed = Server(eport, os.environ.get("DND_LLAMA_EMBED_KEY", os.environ.get("DND_LLAMA_KEY", "")), host="127.0.0.1")
    ctx = int(os.environ.get("DND_LLAMA_SLOT_CTX", "0") or 0) or None
    return LlamaServer(chat, embed, machine={"slot_ctx": ctx})


def sampler_problems(table: dict | None = None, base: dict | None = None) -> list[str]:
    """Every sampler key config.SAMPLING and BASE name is one llama-server reads, with a value in its range: a misspelt key would be sent
    and silently ignored, a wild value sent as it is."""
    from llm import sampling
    table = getattr(config, "SAMPLING", {}) if table is None else table
    base = sampling.BASE if base is None else base
    bad = []

    def one(where, key, value):
        if key not in RANGES:
            bad.append(f"{where}: '{key}' is no sampler llama-server reads (one of {', '.join(SAMPLER_KEYS)})")
            return
        lo, hi, whole = RANGES[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (whole and not isinstance(value, int)):
            bad.append(f"{where}: '{key}' must be {'a whole number' if whole else 'a number'}, not {value!r}")
        elif not lo <= value <= hi:
            bad.append(f"{where}: '{key}' is {value}, outside {lo} to {hi}")
    for k, v in base.items():
        one("llm/sampling.py BASE", k, v)
    missing = [k for k in SAMPLER_KEYS if k != "temperature" and k not in base]
    if missing:
        bad.append(f"llm/sampling.py BASE: no base value for {', '.join(missing)}")
    for task, values in sorted(table.items()):
        for k, v in (values or {}).items():
            one(f"config.SAMPLING {task}", k, v)
    return bad
