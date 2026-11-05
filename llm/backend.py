"""(f515) The game's own interface to whatever runs the model (the owner's decision, 2026-11-05: "let's go with the neutral").

    chat(messages, schema, sampling, max_tokens, deadline=None, voice=None) -> Reply(text, finish, usage)
    embed(texts) -> Embedding(vectors, usage)
    load(progress=None), close(), state(), facts()

The gateway (llm/gateway.py) is the only caller of chat; the embedder (llm/embed.py) the only caller of embed. Everything above the
gateway is unchanged: the 59 generate() call sites never see this module.

Behind the interface sits one source at a time. Until the game moves to llama-server (f528) the source is OllamaShape: it sends exactly
today's request to whatever llm.gateway._client holds (the real client, the suite's stand-in, the replayer), so nothing a test, a
recording or a night sees changes. ollama_kwargs() builds that request, and legacy_projection() is what the recorder's request_hash has
always fingerprinted (the same request, the machine's thread count left out), so the hash covers exactly what is sent.

use(source) swaps the source; wrap(layer, rank) adds a layer around every call (the recorder and the busy light become layers in f517).
Both return an undo handle. lane(name) names the lane a thread's calls are made in (foreground unless a thread says otherwise; f523's
worker reads it).

(f516) A source fails one try by raising llm.errors.Failure of a kind (loading, too_big, invalid, server, unreachable, deadline,
cancelled); the gateway decides what each kind does. failure_of() is the one mapping from the old client's errors to those kinds, so
nothing recorded moves: a timeout is a deadline, Ollama's own error, an HTTP error and Python's ConnectionError are the server's, each
with the old error's (type, text) kept as legacy; anything else is no Failure at all (the gateway's "the call failed", as before). A
cancelled Failure leaves the interface as Cancelled, an Interrupt: never a failed try."""

import contextlib
import threading
from dataclasses import dataclass, field

import config
from core.interrupts import Interrupt
from llm.errors import Cancelled, Failure
from llm.sampling import Sampling

FINISHES = ("stop", "length", "cancelled")


@dataclass
class Reply:
    text: str
    finish: str | None = "stop"
    usage: dict | None = None


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
    error and Python's ConnectionError (the client's while Ollama restarts) are the server's, one failed try. Each keeps its (type, text)."""
    if isinstance(e, Failure):
        return e
    from llm import gateway
    timed_out, server = gateway._transport(e)
    if not (timed_out or server):
        return None
    f = Failure("deadline" if timed_out else "server", str(e)[:200], legacy=(type(e).__name__, str(e)))
    f.__cause__ = e
    return f


# ------------------------------------------------------------------ the Ollama-shaped source (until f528)

def ollama_kwargs(req: ChatRequest) -> dict:
    """Exactly the arguments the gateway sent the Ollama client before f515, in the same order (llm/gateway.py _generate)."""
    from llm import gateway
    s = req.sampling
    return dict(model=config.MODEL, think=config.THINK, messages=req.messages, format=req.schema.model_json_schema(),
                options={"temperature": s.temperature, "num_ctx": config.NUM_CTX, "num_predict": req.max_tokens, **gateway.threads(),
                         **s.explicit},
                keep_alive=config.KEEP_ALIVE)


def legacy_projection(req: ChatRequest) -> dict:
    """What engine/recording.py request_hash fingerprints of a chat: the request as sent, the machine's thread count left out."""
    k = ollama_kwargs(req)
    k["options"] = {o: v for o, v in k["options"].items() if o != "num_thread"}
    return k


class OllamaShape:
    """The source until the game plays on llama-server: today's call, to whatever llm.gateway._client holds, with the turn's deadline on
    the client's own timeout as before (llm/gateway.py _deadline)."""

    name = "ollama"

    def chat(self, req: ChatRequest, deadline=None) -> Reply:
        from llm import gateway
        try:
            with gateway._deadline(deadline):
                response = gateway._client.chat(**ollama_kwargs(req))
        except Interrupt:
            raise                                       # stopped on purpose (a replay parted): never a failure of the model's
        except Exception as e:
            f = failure_of(e)                           # (f516) the old client's errors on the neutral kinds; anything else as it is
            if f is None:
                raise
            raise f from e
        return Reply(text=response.message.content or "", finish=getattr(response, "done_reason", None), usage=gateway._usage(response))

    def embed(self, texts: list[str]) -> Embedding:
        from llm import embed as _embed
        from llm.gateway import threads
        try:
            r = _embed._client().embed(model=config.EMBED_MODEL, input=texts, keep_alive=config.KEEP_ALIVE,
                                       **({"options": threads()} if threads() else {}))
        except Interrupt:
            raise
        except Exception as e:
            f = failure_of(e)                           # (f516) as chat
            if f is None:
                raise
            raise f from e
        return Embedding(vectors=r["embeddings"] if isinstance(r, dict) else r.embeddings)

    def load(self, progress=None) -> None:
        from llm import gateway
        gateway.warm()

    def close(self) -> None:
        from llm import gateway
        gateway.unload()

    def state(self) -> str:
        return "ready"

    def facts(self) -> dict:
        return {"source": self.name, "model": config.MODEL, "embed_model": config.EMBED_MODEL}


# ------------------------------------------------------------------ the one source, its layers, the lanes

_source = OllamaShape()
_layers: list[tuple[int, int, object]] = []          # (rank, order added, layer), called lowest rank outermost
_lock = threading.Lock()
_added = 0
_lane = threading.local()


def source():
    return _source


def use(src):
    """Make src the source; returns a handle that puts the one before it back."""
    global _source
    with _lock:
        before, _source = _source, src

    def undo():
        global _source
        with _lock:
            _source = before
    return undo


def wrap(layer, rank: int = 50):
    """Add a layer around every call: layer(op, request, call) with op 'chat' or 'embed' and call(request) the rest of the way down.
    Returns a handle that removes exactly this layer, whatever order layers are removed in."""
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
def lane(name: str):
    """The calls this thread makes inside the block are in this lane ('foreground', 'background', 'input')."""
    before = getattr(_lane, "name", None)
    _lane.name = name
    try:
        yield
    finally:
        _lane.name = before


def current_lane() -> str:
    return getattr(_lane, "name", None) or "foreground"


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
    src = _source
    reply = _cancelled(lambda: _through("chat", req, lambda r: src.chat(r, deadline=deadline)))
    if getattr(reply, "finish", None) == "cancelled":
        raise Cancelled("the reply was cancelled")   # (f516) a cancel told as a reply's finish is the same Interrupt: never an answer
    return reply


def embed(texts: list[str]) -> Embedding:
    src = _source
    return _cancelled(lambda: _through("embed", list(texts), lambda t: src.embed(t)))


def load(progress=None) -> None:
    fn = getattr(_source, "load", None)
    if fn is not None:
        fn(progress)


def close() -> None:
    fn = getattr(_source, "close", None)
    if fn is not None:
        fn()


def state() -> str:
    fn = getattr(_source, "state", None)
    return fn() if fn is not None else "ready"


def facts() -> dict:
    fn = getattr(_source, "facts", None)
    return dict(fn()) if fn is not None else {}
