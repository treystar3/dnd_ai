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

use(source) swaps the source; wrap(layer, rank) adds a layer around every call. Both return an undo handle, and a handle removes exactly
its own layer whatever order they are removed in. (f517) The recorder (engine/recording.py, rank RECORDER, outermost), the night's
counter (tools/nightrun.py, COUNTER) and the window's busy light (ui/gui/bridge.py, BUSY) are layers: nothing patches the model client
in place any more. A layer sees op 'chat' (a ChatRequest), 'embed' (a list of texts) or 'load' (the model's warm-up, loading(): no
request, no answer to keep) and passes what it does not handle straight down. lane(name) names the lane a thread's calls are made in
(foreground unless a thread says otherwise; the busy light counts the foreground's alone, and f523 declares the background lanes).

(f517) What the recorder writes is rebuilt from the neutral request (ollama_kwargs, embed_kwargs) and, for the old client's own answer
fields (its done_reason and raw token counts, which Reply.usage rounds), from Reply.legacy, which only OllamaShape fills: so a row
recorded through the layer is byte for byte the row the client patch wrote.

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
    legacy: dict | None = None          # (f517) the old client's own answer fields, as the recorder writes them: {done, tokens}


TOKEN_FIELDS = ("prompt_eval_count", "eval_count", "prompt_eval_duration", "eval_duration", "load_duration", "total_duration")

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


def embed_kwargs(texts: list) -> dict:
    """(f517) Exactly the arguments the embedder sent the Ollama client before f515, in the same order (llm/embed.py vectors): what
    OllamaShape.embed sends and what the recorder writes and hashes."""
    from llm.gateway import threads
    return dict(model=config.EMBED_MODEL, input=texts, keep_alive=config.KEEP_ALIVE, **({"options": threads()} if threads() else {}))


def legacy_answer(response) -> dict:
    """(f517) The old client's own answer fields, exactly as engine/recording.py read them off the response before f517: its done_reason
    ('stop' when the response has none at all) and every raw token count it has, durations in nanoseconds, with the server's cached
    prompt tokens when it says (llm/gateway.py cached_count)."""
    from llm import gateway
    tokens = {t: getattr(response, t, None) for t in TOKEN_FIELDS if getattr(response, t, None) is not None}
    cached = gateway.cached_count(response)
    if cached is not None:
        tokens["cached"] = cached
    return {"done": getattr(response, "done_reason", "stop"), "tokens": tokens}


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
        return Reply(text=response.message.content or "", finish=getattr(response, "done_reason", None), usage=gateway._usage(response),
                     legacy=legacy_answer(response))

    def embed(self, texts: list[str]) -> Embedding:
        from llm import embed as _embed
        try:
            r = _embed._client().embed(**embed_kwargs(texts))
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


def loading(run):
    """(f517) The model's warm-up (llm/gateway.py warm), run through the layers as op 'load': the busy light shows while it loads, as it did
    when it patched the client; the recorder and the night's counter pass it by, as a warm-up was never theirs."""
    return _through("load", None, lambda _: run())


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
