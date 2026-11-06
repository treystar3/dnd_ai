"""(f515) The game's own interface to whatever runs the model (the owner's decision, 2026-11-05: "let's go with the neutral").

    chat(messages, schema, sampling, max_tokens, deadline=None, voice=None) -> Reply(text, finish, usage)
    embed(texts) -> Embedding(vectors, usage)
    load(progress=None), close(), state(), facts()

The gateway (llm/gateway.py) is the only caller of chat; the embedder (llm/embed.py) the only caller of embed. Everything above the
gateway is unchanged: the 59 generate() call sites never see this module.

Behind the interface sits one source at a time. Until the game moves to llama-server (f528) the source is OllamaShape: it sends exactly
today's request to whatever llm.gateway._client holds (the real client, the suite's stand-in, the replayer), so nothing a test, a
recording or a night sees changes. ollama_kwargs() builds that request. (f527) The recorder's row and its fingerprint are the
interface's own, neutral form: neutral_request() (the messages, the schema's title and fingerprint, every sampler with the base under
the task's own, the answer's ceiling, whether it thinks, the voice, the model id) and embed_request() (the model and the texts), hashed
whole by request_hash(); nothing of the machine (threads, slots, context) and never the deadline is in either.

use(source) swaps the source; wrap(layer, rank) adds a layer around every call. Both return an undo handle, and a handle removes exactly
its own layer whatever order they are removed in. (f517) The recorder (engine/recording.py, rank RECORDER, outermost), the night's
counter (tools/nightrun.py, COUNTER) and the window's busy light (ui/gui/bridge.py, BUSY) are layers: nothing patches the model client
in place any more. A layer sees op 'chat' (a ChatRequest), 'embed' (a list of texts) or 'load' (the model's warm-up, loading(): no
request, no answer to keep) and passes what it does not handle straight down. lane(name) names the lane a thread's calls are made in
(foreground unless a thread says otherwise; the busy light counts the foreground's alone, and f523 declares the background lanes).

(f517, f527) What the recorder writes is the neutral request and the Reply as the interface gives it (text, finish, usage), whatever
source answered: the old client's own fields (done_reason, raw counts) are read into the Reply by reply_of and kept nowhere else.

(f516) A source fails one try by raising llm.errors.Failure of a kind (loading, too_big, invalid, server, unreachable, deadline,
cancelled); the gateway decides what each kind does. failure_of() is the one mapping from the old client's errors to those kinds, so
nothing recorded moves: a timeout is a deadline, Ollama's own error, an HTTP error and Python's ConnectionError are the server's, each
with the old error's (type, text) kept as legacy; anything else is no Failure at all (the gateway's "the call failed", as before). A
cancelled Failure leaves the interface as Cancelled, an Interrupt: never a failed try."""

import contextlib
import hashlib
import json
import threading
from dataclasses import dataclass, field

import config
from core.interrupts import Interrupt
from llm.errors import KINDS, Cancelled, Failure, NoServer
from llm.sampling import Sampling

FINISHES = ("stop", "length", "cancelled")


@dataclass
class Reply:
    text: str
    finish: str | None = "stop"
    usage: dict | None = None

# (f517) The ranks of the three layers, lowest outermost: the recorder sees every call whole (its seconds include the layers inside it,
# as when it patched the client last), then the night's counter, then the busy light. A worker, if f523 ever makes it a layer rather
# than part of the source, goes below all three (R1: nothing below the recorder decides an answer), so a foreground call it queues
# still lights the busy light.
RECORDER, COUNTER, BUSY = 10, 20, 30


@dataclass
class Embedding:
    vectors: list
    usage: dict | None = None


@dataclass
class ChatRequest:
    messages: list
    schema: type
    sampling: Sampling
    max_tokens: int
    voice: str | None = None


# ------------------------------------------------------------------ the old client's errors, on the neutral kinds (f516)

def failure_of(e: BaseException) -> Failure | None:
    """The Failure a try's error is, or None when it is none of the kinds (the gateway's "the call failed", one failed try, as before). The
    old client's errors are read as they always were (llm/gateway.py _transport): a timeout is a deadline; Ollama's own error, an HTTP
    error and Python's ConnectionError (the client's while Ollama restarts) are the server's, one failed try. Each keeps its (type, text).
    (f518) No model server in the process at all (NoServer, the suite's switch with nothing installed) is unreachable, with no legacy
    pair: one try, nothing charged; a ConnectionError raised on purpose is still the server's."""
    if isinstance(e, Failure):
        return e
    if isinstance(e, NoServer):
        f = Failure("unreachable", str(e)[:200])
        f.__cause__ = e
        return f
    from llm import gateway
    timed_out, server = gateway._transport(e)
    if not (timed_out or server):
        return None
    f = Failure("deadline" if timed_out else "server", str(e)[:200], legacy=(type(e).__name__, str(e)))
    f.__cause__ = e
    return f


LEGACY_ERRORS = {"Timeout": "deadline"}     # (f518) a recorded error's type name -> its kind; a name holding 'Timeout' is a deadline,
                                            # every other name the server's (ConnectionError, ResponseError, HTTPError and the rest)


def legacy_failure(err) -> Failure:
    """(f518) A recorded error row's [type name, text] as the Failure a replay raises, with no import of the old client's packages: a
    timeout's name is a deadline, any other the server's, each keeping the recorded pair as its legacy (so the gateway words it as it
    was worded when it was recorded). A neutral Failure recorded without a pair (['Failure', '<kind>: <detail>']) keeps its kind."""
    name, text = ((list(err or []) + ["", ""])[:2])
    name, text = str(name), str(text)
    if name == "Failure":
        kind, _, detail = text.partition(": ")
        return Failure(kind if kind in KINDS else "server", detail if kind in KINDS else text)
    kind = next((k for part, k in LEGACY_ERRORS.items() if part in name), "server")
    return Failure(kind, text[:200], legacy=(name, text))


PASS = object()      # (f518) a stand-in's handler returns this to send the request on below it (a live tool's real titles)


def _send(fn, kwargs: dict, deadline=None, client=None, hand_deadline: bool = False):
    """(f518) The one way a request in the old client's shape is sent, by OllamaShape and by a stand-in alike: the old client's errors on
    the neutral kinds (failure_of), anything else as it is, an Interrupt untouched. With a client (OllamaShape's), the turn's deadline is
    set on its own timeout as before, and the Failure says whether that limit was the one applied (failed_try words it so); a stand-in
    names no client, so nothing reads the real one, and is handed the deadline only when its function asks for it by name."""
    from llm import gateway
    applied = False
    try:
        if client is not None:
            with gateway._deadline(deadline, client) as applied:
                return fn(**kwargs)
        return fn(**kwargs, deadline=deadline) if hand_deadline else fn(**kwargs)
    except Interrupt:
        raise                                           # stopped on purpose (a replay parted, a cancel): never a failure of the model's
    except Exception as e:
        f = failure_of(e)
        if f is None or f is e:
            raise
        f.client_limit = applied
        raise f from e


def reply_of(response) -> "Reply":
    """(f518) The old client's answer as the interface's Reply: its text, its finish, its counts rounded for the budget (usage), and its
    own fields for the recorder (legacy). A Reply given back as it is."""
    from llm import gateway
    if isinstance(response, Reply):
        return response
    return Reply(text=response.message.content or "", finish=getattr(response, "done_reason", None), usage=gateway._usage(response))


def embedding_of(response) -> "Embedding":
    if isinstance(response, Embedding):
        return response
    return Embedding(vectors=response["embeddings"] if isinstance(response, dict) else response.embeddings)


def title(req: ChatRequest) -> str:
    """(f518) A request's schema title, as the old client's format carried it (a stand-in's handlers and a live tool route by it)."""
    return req.schema.model_json_schema().get("title", "") if req is not None else ""


# ------------------------------------------------------------------ the Ollama-shaped source (until f528)

def think_room(messages: list, max_tokens: int) -> int:
    """(f534) The tokens a thinking call is given to think in: THINK_ROOM, but never more than the context holds beside the prompt
    (counted at three characters a token, more than it takes, so the estimate errs towards less room) and the answer's own ceiling."""
    chars = sum(len(str(m.get("content") or "")) for m in messages)
    fits = int(config.NUM_CTX) - chars // 3 - int(max_tokens) - 256
    return max(0, min(int(getattr(config, "THINK_ROOM", 0) or 0), fits))


def ollama_kwargs(req: ChatRequest) -> dict:
    """Exactly the arguments the gateway sent the Ollama client before f515, in the same order (llm/gateway.py _generate). (f533) A task
    chosen to think (config.THINK_TASKS) asks for it, with THINK_ROOM more tokens to think in; every other call as THINK says."""
    from llm import gateway
    s = req.sampling
    think = config.THINK if getattr(s, "think", None) is None else bool(s.think)
    room = think_room(req.messages, req.max_tokens) if getattr(s, "think", None) else 0
    return dict(model=config.OLLAMA_MODEL, think=think, messages=req.messages, format=req.schema.model_json_schema(),
                options={"temperature": s.temperature, "num_ctx": config.NUM_CTX, "num_predict": req.max_tokens + room, **gateway.threads(),
                         **s.explicit},
                keep_alive=config.KEEP_ALIVE)


def embed_kwargs(texts: list) -> dict:
    """(f517) Exactly the arguments the embedder sent the Ollama client before f515, in the same order (llm/embed.py vectors): what
    OllamaShape.embed sends and what the recorder writes and hashes."""
    from llm.gateway import threads
    return dict(model=config.OLLAMA_EMBED_MODEL, input=texts, keep_alive=config.KEEP_ALIVE, **({"options": threads()} if threads() else {}))


def neutral_request(req: ChatRequest) -> dict:
    """(f527) What a chat request is, whatever machine runs it: its messages, its schema's title and fingerprint, every sampler (the base
    under the task's own, Sampling.resolved), the answer's ceiling with the thinking room added, whether it thinks, its voice and the
    model id. Nothing of the machine (slot, adapter index, threads, context) and never the deadline. The recorder's row, and what
    request_hash fingerprints."""
    schema = req.schema.model_json_schema()
    s = req.sampling
    thinks = bool(config.THINK) if getattr(s, "think", None) is None else bool(s.think)
    room = think_room(req.messages, req.max_tokens) if getattr(s, "think", None) else 0
    return {"model": config.MODEL, "messages": req.messages, "schema": schema.get("title") or req.schema.__name__,
            "schema_sha": hashlib.sha256(json.dumps(schema, sort_keys=True).encode("utf-8")).hexdigest()[:16],
            "sampling": s.resolved(), "max_tokens": int(req.max_tokens) + room, "think": thinks, "voice": req.voice or None}


def embed_request(texts: list) -> dict:
    """(f527) What an embed request is: the embedding model's id and the texts."""
    return {"model": config.EMBED_MODEL, "input": list(texts)}


def request_hash(request: dict) -> str:
    """(f527) One fingerprint of a neutral request, whole (engine/recording.py request_hash is this)."""
    return hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


class OllamaShape:
    """The source until the game plays on llama-server: today's call, to the Ollama client (llm.gateway._client, or the client given: a
    test's spy on what is sent), with the turn's deadline on the client's own timeout as before (llm/gateway.py _deadline)."""

    name = "ollama"

    def __init__(self, client=None):
        self._given = client

    @property
    def client(self):
        from llm import gateway
        return self._given if self._given is not None else gateway._client      # read late: the lazy client, built on its first call

    def chat(self, req: ChatRequest, deadline=None) -> Reply:
        c = self.client
        return reply_of(_send(c.chat, ollama_kwargs(req), deadline, client=c))

    def embed(self, texts: list[str]) -> Embedding:
        return embedding_of(_send(self.client.embed, embed_kwargs(texts)))

    def load(self, progress=None) -> None:
        from llm import gateway
        gateway.warm(self.client)

    def close(self) -> None:
        from llm import gateway
        gateway.unload(self.client)

    def state(self) -> str:
        return "ready"

    def facts(self) -> dict:
        """(f518) The embedder is here when the Ollama server has its model (llm/embed.py probe: never under the suite's switch, and
        fixed for a strict session); a client given is a test's, with no embedder."""
        from llm import embed as _embed
        return {"source": self.name, "model": config.MODEL, "embed_model": config.EMBED_MODEL,
                "embedder": _embed.probe() if self._given is None else False}


class Untimed(OllamaShape):
    """(f518) The Ollama shape under the client's own timeout, never the turn's deadline: where a developer tool's live titles go (a
    stand-in's PASS, below=Untimed()). They ran so before f518, through a client patch the deadline never reached, and the tools do not
    warm the model first, so a cold model's first live call would otherwise be cut by the turn's limit and read as the scene failing."""

    name = "ollama-untimed"

    def chat(self, req: ChatRequest, deadline=None) -> Reply:
        return super().chat(req, None)


class StandIn:
    """(f518) A model source for the suite, the recording scripts and the developer tools: chat(**k) and embed(**k) are the functions it
    answers with, given the old client's arguments (ollama_kwargs, embed_kwargs) and returning what the old client returned (an object
    with .message.content and perhaps .done_reason and raw counts; a dict with 'embeddings'), so simlib.Stub's handlers and every
    test's function serve unchanged. Its errors go the one way OllamaShape's go (_send). It reads no real client: a function that
    names a `deadline` parameter is handed the turn's deadline, any other is not; a function returning PASS sends the request on to
    `below` (or to Ollama), as a live tool's real titles go. No chat function: every chat is unreachable; no embed function: there
    is no embedder (facts), and an embed asked anyway is unreachable. `calls` counts the titles answered ('' for embeddings)."""

    def __init__(self, chat=None, embed=None, facts: dict | None = None, name: str = "stand-in", below=None):
        import collections
        import inspect
        self.chat_fn, self.embed_fn, self.name, self.below = chat, embed, name, below
        self._facts = dict(facts or {})
        self.calls = collections.Counter()
        self._count = threading.Lock()

        def names_deadline(fn) -> bool:
            try:
                p = inspect.signature(fn).parameters.get("deadline")
            except (TypeError, ValueError):
                return False
            return p is not None and p.kind in (p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY)
        self._hand = names_deadline(chat) if chat is not None else False

    def _down(self):
        return self.below if self.below is not None else OllamaShape()

    def chat(self, req: ChatRequest, deadline=None) -> Reply:
        if self.chat_fn is None:
            raise Failure("unreachable", "this stand-in answers no chat")
        with self._count:
            self.calls[title(req)] += 1
        got = _send(self.chat_fn, ollama_kwargs(req), deadline, hand_deadline=self._hand)
        if got is PASS:
            return self._down().chat(req, deadline)
        return reply_of(got)

    def embed(self, texts: list[str]) -> Embedding:
        if self.embed_fn is None:
            raise Failure("unreachable", "this stand-in has no embedder")
        with self._count:
            self.calls[""] += 1
        got = _send(self.embed_fn, embed_kwargs(texts))
        if got is PASS:
            return self._down().embed(texts)
        return embedding_of(got)

    def load(self, progress=None) -> None:
        loading(lambda: None)

    def close(self) -> None:
        pass

    def state(self) -> str:
        return "ready"

    def facts(self) -> dict:
        return {"source": self.name, "model": config.MODEL, "embed_model": config.EMBED_MODEL, "embedder": self.embed_fn is not None,
                **self._facts}


# ------------------------------------------------------------------ the one source, its layers, the lanes

_default = OllamaShape()
_sources: list[tuple[int, object]] = []              # (f518) (order added, source): the newest answers; each handle removes its own
_layers: list[tuple[int, int, object]] = []          # (rank, order added, layer), called lowest rank outermost
_lock = threading.Lock()
_added = 0
_lane = threading.local()


_switched = None                                     # (f521) the llama-server source DND_BACKEND=llama names, built on first use


def source():
    """The source answering now: the newest one put in (use), else the default: Ollama, or (f521) a llama-server started by hand when
    config.BACKEND is 'llama' (DND_BACKEND), built once on first use. The suite drops every DND_* setting, so it never switches."""
    global _switched
    with _lock:
        if _sources:
            return _sources[-1][1]
        if getattr(config, "BACKEND", "ollama") != "llama" or __import__("os").environ.get("MERAVIA_NO_SERVER"):
            return _default                             # (f521) under the suite's switch no default ever reaches a live server
        if _switched is None:
            from llm import llama
            _switched = llama.from_env()
        return _switched


def forget_switch() -> None:
    """(f521) The llama-server source the switch built is dropped, so the next default is built afresh from the settings as they are now."""
    global _switched
    with _lock:
        _switched = None


def use(src):
    """Make src the source; returns a handle that takes exactly it away again (f518: a stack, so handles undone in any order leave
    the sources still put in, newest answering, never one already taken away)."""
    global _added
    with _lock:
        _added += 1
        entry = (_added, src)
        _sources.append(entry)

    def undo():
        with _lock:
            if entry in _sources:
                _sources.remove(entry)
    return undo


def wrap(layer, rank: int = 50):
    """Add a layer around every call: layer(op, request, call) with op 'chat', 'embed' or 'load' and call(request) the rest of the way
    down. A layer re-raises what the call raises as it is (a bare raise): the gateway reads the very exception (its kind, the old
    client's error behind it). Returns a handle that removes exactly this layer, whatever order layers are removed in. A call already
    on its way keeps the layers it started with."""
    global _added
    with _lock:
        _added += 1
        entry = (rank, _added, layer)
        _layers.append(entry)
        _layers.sort(key=lambda e: (e[0], e[1]))

    def undo():
        with _lock:
            if entry in _layers:
                _layers.remove(entry)
    return undo


def layers() -> list:
    with _lock:
        return [e[2] for e in _layers]


def _through(op: str, request, last):
    with _lock:
        chain = [e[2] for e in _layers]

    def step(i, req):
        if i == len(chain):
            return last(req)
        return chain[i](op, req, lambda r: step(i + 1, r))
    return step(0, request)


@contextlib.contextmanager
def lane(name: str, session: str | None = None):
    """The calls this thread makes inside the block are in this lane ('foreground', 'background', 'input'). (f523) A background lane
    names the campaign it works for (the save's folder), so closing that campaign cancels its calls and nobody else's."""
    before, before_session = getattr(_lane, "name", None), getattr(_lane, "session", None)
    _lane.name, _lane.session = name, session
    try:
        yield
    finally:
        _lane.name, _lane.session = before, before_session


def current_lane() -> str:
    return getattr(_lane, "name", None) or "foreground"


def current_session() -> str | None:
    return getattr(_lane, "session", None)


def _source_has(name: str):
    """The source's own method, or None. (f523's review) A source that cannot be made (a malformed DND_LLAMA_URL) fails its model calls,
    as it always did, never a save's opening or closing."""
    try:
        return getattr(source(), name, None)
    except Exception:
        return None


def promote(thread) -> None:
    """(f523) The turn waits on this background thread's work (npc/backfill.py settle and collect, creation's result()): its calls are
    never taken back from it again and start without waiting for the reading time, while the thread lives. The Thread itself is
    passed on, never only its ident. Nothing for a source with no worker."""
    fn = _source_has("promote")
    if fn is not None and thread is not None:
        fn(thread)


def waiting(run):
    """(f523's review) The turn waiting on a background job (backfill's collect, creation's result), run through the layers as op
    'wait': the busy light shows while the player waits on it, as it did when the job's call was the foreground's; the recorder and
    the night's counter pass it by, as they pass the model's warm-up."""
    return _through("wait", None, lambda _: run())


def cancel_session(key: str) -> int:
    """(f523) A campaign closing (engine/session.py close): its background calls end Cancelled, waiting or in flight; another
    campaign's go on. Returns how many were in flight; nothing for a source with no worker."""
    fn = _source_has("cancel_session")
    return int(fn(str(key)) or 0) if fn is not None else 0


def reopen_session(key: str) -> None:
    """(f523) The campaign is open again (the same save loaded after it was closed): its background calls may run."""
    fn = _source_has("reopen_session")
    if fn is not None:
        fn(str(key))


# ------------------------------------------------------------------ the interface

def _cancelled(run):
    """(f516, R3) A cancelled try leaves the interface as Cancelled, an Interrupt, whichever layer or source said so (a Failure of kind
    cancelled, Cancelled itself, or for chat a reply whose finish is 'cancelled'): never a failure."""
    try:
        return run()
    except Failure as f:
        if f.kind == "cancelled":
            raise Cancelled(f.detail or "cancelled") from f
        raise


def chat(messages: list, schema: type, sampling: Sampling, max_tokens: int, deadline=None, voice: str | None = None) -> Reply:
    req = ChatRequest(messages=messages, schema=schema, sampling=sampling, max_tokens=max_tokens, voice=voice)
    src = source()
    reply = _cancelled(lambda: _through("chat", req, lambda r: src.chat(r, deadline=deadline)))
    if getattr(reply, "finish", None) == "cancelled":
        raise Cancelled("the reply was cancelled")   # (f516) a cancel told as a reply's finish is the same Interrupt: never an answer
    return reply


def embed(texts: list[str]) -> Embedding:
    src = source()
    return _cancelled(lambda: _through("embed", list(texts), lambda t: src.embed(t)))


def loading(run):
    """(f517) The model's warm-up (llm/gateway.py warm), run through the layers as op 'load': the busy light shows while it loads, as it did
    when it patched the client; the recorder and the night's counter pass it by, as a warm-up was never theirs."""
    return _through("load", None, lambda _: run())


def load(progress=None) -> None:
    fn = getattr(source(), "load", None)
    if fn is not None:
        fn(progress)


def close() -> None:
    fn = getattr(source(), "close", None)
    if fn is not None:
        fn()


def state() -> str:
    fn = getattr(source(), "state", None)
    return fn() if fn is not None else "ready"


def facts() -> dict:
    """What the runtime is (R4): the source's own facts. A source that declares no embedder has none (llm/embed.py available)."""
    fn = getattr(source(), "facts", None)
    return dict(fn()) if fn is not None else {}
