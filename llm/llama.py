"""(f521) The llama-server adapter: the request as llama-server takes it, sent and read back on the neutral kinds. Behind a switch, not yet
used: the game's default source stays the Ollama-shaped one until f528 (GOALS.md, owner's decisions of 2026-11-05: the game ships
llama.cpp's llama-server; "let's go with the neutral"). DND_BACKEND=llama with DND_LLAMA_URL (and DND_LLAMA_KEY, DND_LLAMA_EMBED_URL)
points a session at a llama-server someone started by hand, for the measurements f527 waits on; f522 starts and stops the server itself.

The body (llama_body) is pure: the request and the machine's facts in, the dict sent out, the same bytes for the same inputs (body_bytes).
- messages as the gateway made them; the schema as its grammar, sent as `grammar` (llm/gbnf.py, llama.cpp's own converter written out;
  f527, the owner's fence choice: never response_format, whose Gemma 4 chat parser writes a ```json fence into the answer);
- every sampler, BASE under the task's own values (llm/sampling.py Sampling.resolved), so llama-server's own defaults (top_k 40,
  min_p 0.05, its repeat window) never apply: the table every night ran on, the owner's "keep them as they are";
- n_predict, the answer's ceiling (with a thinking task's room, as Ollama's num_predict carried it, f534);
- thinking off on every request unless the task was chosen to think (config.THINK_TASKS): chat_template_kwargs enable_thinking,
  which the pod confirmed on 407 of 407 calls, and without which the model thinks (scratchpad pod533 report);
- cache_prompt; id_slot from the machine (the lane's slot, f523); a voice's adapter as lora, from the machine.
What the machine adds (the slot, the adapter's index) is never in the request's own fingerprint (neutral, neutral_hash): a request
hashes the same whichever slot it ran on. f527 makes neutral_hash the recorder's request hash.

The transport is a plain socket to the loopback address with the launch's bearer key: it reads no proxy settings (the sandbox and a
player's machine may both set HTTPS_PROXY). The caller sends, waits and reads on its own socket in half-second steps (select), watching
its deadline and its cancel flag to the last byte of the answer, so a server that stalls or trickles mid-answer is cut off at the
deadline and a cancel is never lost once the answer has begun; a cancel closes the caller's own connection, which llama-server
notices within about a second and frees the slot (measured on the pod: 1.02, 1.02 and 0.05 s).

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
import json
import os
import re
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
          "typical_p": (0.0, 1.0, False), "repeat_penalty": (0.5, 2.0, False), "repeat_last_n": (0, 8192, True),
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
    voice, the model, and whether it thinks. Nothing of the machine (slot, adapter index, threads, context) and never the deadline.
    (f527) The interface's own form, backend.neutral_request: the recorder's row and fingerprint."""
    from llm import backend
    return backend.neutral_request(req)


def neutral_hash(req) -> str:
    from llm import backend
    return backend.request_hash(neutral(req))[:16]


_GRAMMARS: dict[str, str] = {}                      # schema fingerprint -> its grammar (a dynamic schema's ids vary; the cache is capped)
_GRAMMARS_MAX = 256
_GRAMMARS_LOCK = threading.Lock()                   # (f527's review) two lanes build bodies at once


def grammar_of(schema: dict) -> str:
    """(f527) The grammar llama-server is sent for this schema: llama.cpp's own conversion (llm/gbnf.py), headed by a comment naming the
    contract and its fingerprint (the grammar parser skips comments; a fake server reads the name). A schema the converter does not take
    is a refused request (invalid), never a server fault."""
    from llm import gbnf
    key = hashlib.sha256(json.dumps(schema, sort_keys=True).encode("utf-8")).hexdigest()[:16]
    with _GRAMMARS_LOCK:
        text = _GRAMMARS.get(key)
    if text is None:
        try:
            text = f"# Meravia {schema.get('title') or 'schema'} {key}\n" + gbnf.grammar(schema)
        except gbnf.SchemaError as e:
            raise Failure("invalid", f"the schema {schema.get('title') or '?'} has no grammar: {str(e)[:200]}")
        with _GRAMMARS_LOCK:
            while len(_GRAMMARS) >= _GRAMMARS_MAX:
                _GRAMMARS.pop(next(iter(_GRAMMARS)), None)
            text = _GRAMMARS.setdefault(key, text)      # the first builder's text, so the cache gives one object for one schema
    return text


def llama_body(req, machine: dict | None = None) -> dict:
    """The body llama-server's /v1/chat/completions is sent for this request on this machine. Pure: no clock, no thread, no state."""
    from llm import backend
    m = machine or {}
    schema = _schema(req)
    room = backend.think_room(req.messages, req.max_tokens) if getattr(req.sampling, "think", None) else 0
    resolved = req.sampling.resolved()
    body = {"model": config.MODEL, "messages": req.messages, "grammar": grammar_of(schema)}    # (f527) the grammar itself, no fence
    body.update({k: resolved[k] for k in SAMPLER_KEYS})                 # every sampler, in one fixed order
    body.update({"n_predict": int(req.max_tokens) + room, "chat_template_kwargs": {"enable_thinking": thinks(req)},
                 "cache_prompt": True, "stream": False})
    if m.get("slot") is not None:
        body["id_slot"] = int(m["slot"])
    adapters = m.get("lora") or {}
    if req.voice and req.voice not in adapters:
        raise Failure("invalid", f"no adapter loaded for the voice {req.voice!r}")
    if adapters:                                        # every adapter named, every time: llama-server applies its own launch scales to
        on = int(adapters[req.voice]) if req.voice else None     # a request that names none (server-context.cpp launch_slot_with_task)
        body["lora"] = [{"id": int(i), "scale": 1.0 if int(i) == on else 0.0} for i in sorted({int(v) for v in adapters.values()})]
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
        self.no_deadline: float | None = None   # (f526) a call with no deadline's limit: config.REQUEST_TIMEOUT, or the hang guard below
                                                # the minimum card (llm/launch.py apply_slow)

    def _once(self, method: str, path: str, data: bytes | None, until: float | None, cancel: threading.Event | None):
        """One request and its whole answer on the caller's own socket: (status, payload). The send, the wait and the read are one loop
        in steps, each step watching the cancel flag and the deadline to the last byte (a server that stalls mid-answer, or trickles
        it, is cut off at the deadline, and a cancel is never lost once the answer has begun). Raises Failure for the connection's
        own troubles: refused, reset, aborted, closed before a whole answer, all unreachable."""

        def check():
            if cancel is not None and cancel.is_set():
                raise Failure("cancelled", "the call was cancelled")
            if until is not None and time.monotonic() >= until:
                raise Failure("deadline", "the call ran past its limit")

        try:
            sock = socket.create_connection((self.host, self.port), timeout=CONNECT_SECONDS)
        except OSError as e:
            raise Failure("unreachable", f"{type(e).__name__}: {e}"[:200]) from e
        try:
            head = [f"{method} {path} HTTP/1.1", f"Host: {self.host}:{self.port}", "Connection: close", "Accept: application/json"]
            if self.key:
                head.append(f"Authorization: Bearer {self.key}")
            if data is not None:
                head += ["Content-Type: application/json", f"Content-Length: {len(data)}"]
            out = memoryview(("\r\n".join(head) + "\r\n\r\n").encode("ascii") + (data or b""))
            sock.setblocking(False)
            sent = 0
            while sent < len(out):                      # the send, in steps: a server not reading cannot hold the caller past its limit
                check()
                _, writable, _ = select.select([], [sock], [], self.step)
                if writable:
                    try:
                        sent += sock.send(out[sent:sent + 65536])
                    except (BlockingIOError, InterruptedError):
                        continue
                    except OSError as e:
                        raise Failure("unreachable", f"{type(e).__name__}: {e}"[:200]) from e
            got = bytearray()
            while True:                                 # the wait and the read, in steps, to the end of the answer (Connection: close)
                check()
                readable, _, _ = select.select([sock], [], [], self.step)
                if not readable:
                    continue
                try:
                    chunk = sock.recv(65536)
                except (BlockingIOError, InterruptedError):
                    continue
                except OSError as e:
                    raise Failure("unreachable", f"{type(e).__name__}: {e}"[:200]) from e
                if not chunk:
                    break
                got += chunk
            check()                                     # a cancel that came with the last byte still counts
        finally:
            try:
                sock.close()                            # a cancel or a deadline closes the caller's own connection: the server frees the slot
            except OSError:
                pass
        return _parse(bytes(got))

    def request(self, method: str, path: str, body: dict | None = None, deadline: float | None = None,
                cancel: threading.Event | None = None):
        """The answer's (status, payload, wall ms, loading ms). A 503 while the model loads is waited on, off the deadline's clock and not
        a try, up to load_wait; deadline is the seconds this call may take (None: config.REQUEST_TIMEOUT, the hang guard outside a turn)."""
        data = body_bytes(body) if body is not None else None
        limit = float(self.no_deadline or config.REQUEST_TIMEOUT) if deadline is None else float(deadline)
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


def _parse(raw: bytes):
    """A whole HTTP answer's (status, payload): its status line, a body by Content-Length or chunks, JSON where it is JSON."""
    head, sep, body = raw.partition(b"\r\n\r\n")
    if not sep:
        raise Failure("unreachable", "the server closed the connection before a whole answer")
    lines = head.decode("latin-1").split("\r\n")
    try:
        status = int(lines[0].split(" ", 2)[1])
    except (IndexError, ValueError) as e:
        raise Failure("unreachable", f"not an HTTP answer: {lines[0][:80]!r}") from e
    headers = {k.strip().lower(): v.strip() for k, _, v in (l.partition(":") for l in lines[1:]) if k}
    if "chunked" in headers.get("transfer-encoding", "").lower():
        out, rest = bytearray(), body
        while True:
            size_line, nl, rest = rest.partition(b"\r\n")
            if not nl:
                raise Failure("unreachable", "the server closed the connection mid-answer")
            size = int(size_line.split(b";")[0].strip() or b"0", 16)
            if size == 0:
                break
            if len(rest) < size:
                raise Failure("unreachable", "the server closed the connection mid-answer")
            out += rest[:size]
            rest = rest[size + 2:]
        body = bytes(out)
    elif "content-length" in headers:
        n = int(headers["content-length"])
        if len(body) < n:
            raise Failure("unreachable", "the server closed the connection mid-answer")
        body = body[:n]
    text = body.decode("utf-8", errors="replace")
    try:
        payload = json.loads(text) if text else {}
    except ValueError:
        payload = text
    return status, payload


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

    def __init__(self, chat: Server, embed: Server | None = None, machine: dict | None = None, worker=None):
        self.chat_server, self.embed_server = chat, embed
        self.machine = dict(machine or {})
        self.worker = worker                            # (f523) who may use the slots when (llm/worker.py); None sends at once
        self._props_read = self.machine.get("slot_ctx") is not None
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
        """(f523) Through the worker when there is one: a background call waits for the card and gives it back when the turn needs
        it (sent again below the layers, unseen above); a foreground call is sent at once. Always on the caller's own thread."""
        from llm import backend
        if self.worker is None:
            return self._send(req, deadline, cancel)
        lane = backend.current_lane()
        if lane == "background":
            return self.worker.background(lambda flag: self._send(req, deadline, flag), backend.current_session())
        return self.worker.foreground(lambda flag: self._send(req, deadline, cancel), lane)

    def promote(self, thread) -> None:
        if self.worker is not None:
            self.worker.promote(thread)

    def cancel_session(self, key: str) -> int:
        return self.worker.cancel_session(key) if self.worker is not None else 0

    def reopen_session(self, key: str) -> None:
        if self.worker is not None:
            self.worker.reopen_session(key)

    def _send(self, req, deadline=None, cancel: threading.Event | None = None):
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
        usage = usage_of(payload, wall_ms, self.slot_ctx())
        return Reply(text=msg.get("content") or "", finish=ch.get("finish_reason"), usage=usage)

    def slot_ctx(self) -> int | None:
        """The context one slot holds: the machine's, or read once from the server's /props when the machine did not say."""
        if not self._props_read:
            self._props_read = True
            try:
                status, payload, _, _ = self.chat_server.request("GET", "/props", None, 5.0)
                n = int(((payload or {}).get("default_generation_settings") or {}).get("n_ctx") or 0) if status == 200 and isinstance(payload, dict) else 0
                if n:
                    self.machine["slot_ctx"] = n
            except Failure:
                pass
        return self.machine.get("slot_ctx")

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
        if self.worker is not None:
            self.worker.close()                         # (f523) nothing waits for the card any more
        self.cancel()

    def state(self) -> str:
        h = self.chat_server.health()
        return "ready" if h == "ready" else "loading" if h == "loading" else "failed"

    def facts(self) -> dict:
        return {"source": self.name, "model": config.MODEL, "embed_model": config.EMBED_MODEL, "embedder": self.embed_server is not None,
                "slot_ctx": self.machine.get("slot_ctx")}


# ------------------------------------------------------------------ the switch, and the data's check

def _port_of(url: str, name: str) -> int:
    """The port of a loopback URL (http://127.0.0.1:PORT); a URL off this machine, or with no port, is refused in plain words."""
    m = re.fullmatch(r"(?:https?://)?(127\.0\.0\.1|localhost):(\d{1,5})/?", url.strip())
    if not m:
        raise ValueError(f"{name} must be this machine's address with its port, like http://127.0.0.1:8080, not {url!r}")
    return int(m.group(2))


def from_env() -> LlamaServer:
    """The source DND_BACKEND=llama names: a llama-server started by hand at DND_LLAMA_URL (its key DND_LLAMA_KEY), and its embedder at
    DND_LLAMA_EMBED_URL when there is one. Only the loopback address: a game never sends its prompts off the machine."""
    chat = Server(_port_of(os.environ.get("DND_LLAMA_URL", "http://127.0.0.1:8080"), "DND_LLAMA_URL"), os.environ.get("DND_LLAMA_KEY", ""))
    embed = None
    if os.environ.get("DND_LLAMA_EMBED_URL"):
        embed = Server(_port_of(os.environ["DND_LLAMA_EMBED_URL"], "DND_LLAMA_EMBED_URL"),
                       os.environ.get("DND_LLAMA_EMBED_KEY", os.environ.get("DND_LLAMA_KEY", "")))
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
        one("sampling.yaml base", k, v)
    missing = [k for k in SAMPLER_KEYS if k != "temperature" and k not in base]
    if missing:
        bad.append(f"sampling.yaml base: no base value for {', '.join(missing)}")
    for task, values in sorted(table.items()):
        for k, v in (values or {}).items():
            one(f"sampling.yaml tasks.{task}", k, v)
    return bad
