"""The only place the game talks to Ollama.

Every call is schema-constrained, validated, retried on failure, and logged.
On a failed validation the model is shown its answer and the reason it was
rejected, so the retry can fix the specific problem.
Callers get a validated proposal object or an LLMError, never raw text.
"""

import contextlib
import json
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

import config

from core.interrupts import Interrupt   # (f449) an exception raised on purpose (a replay parted) is never a failed try
from llm.errors import Cancelled, Failure, LLMError, NoServer   # (f514) the classes live where importing them starts nothing; LLMError stays here


def keep_extra_fields() -> None:
    """(f475) Keep what the server reports beyond the client's own fields (a cached-prompt count). (f514) Done when the real client is
    built, not at import, so importing the gateway no longer imports the client's package; a test that builds the client's replies
    itself calls this first."""
    try:
        import ollama
        ollama.ChatResponse.model_config["extra"] = "allow"
        ollama.ChatResponse.model_rebuild(force=True)
    except Exception:
        pass


class _LazyClient:
    """(f514) The model client, built on its first use rather than when the gateway is imported, so the import chain (engine/budget.py,
    engine/data_check.py through scenes.world, main.py) starts nothing and imports no server client. Reading a method, asking
    hasattr, and assigning over a method (a test's or a recording script's stand-in; since f517 the recorder, the busy light and the
    night's counter are layers of llm/backend.py instead) build nothing; the client is built when a call is made, or when its inner parts
    are read (the turn's deadline sets the inner timeout).
    Under MERAVIA_NO_SERVER (tools/run_suite.py sets it) nothing is ever built: a call raises NoServer (a ConnectionError, what a
    missing server raises), so no test can reach a real model by accident. (f518) Nothing outside llm/ touches it: the suite answers
    through a stand-in source (llm/backend.py StandIn), so assigning over one of its methods is refused, and reached() counts every
    time something tried to reach the real client."""

    METHODS = ("chat", "embed", "embeddings", "generate", "pull", "push", "list", "show", "ps", "create", "delete", "copy")

    def __init__(self):
        object.__setattr__(self, "_real", None)
        object.__setattr__(self, "_lock", threading.Lock())
        object.__setattr__(self, "_reached", 0)

    def __setattr__(self, name, value):
        if name in _LazyClient.METHODS:              # (f518) a stand-in is a source (llm/backend.py StandIn), never a patch on the client
            raise AttributeError(f"the model client's {name} is not assigned over: install a stand-in source (llm/backend.py use)")
        object.__setattr__(self, name, value)

    def built(self) -> bool:
        return self._real is not None

    def reached(self) -> int:
        """(f518) How many times something tried to reach the real client (a call, or a read of its inner parts)."""
        return self._reached

    def real(self):
        object.__setattr__(self, "_reached", self._reached + 1)
        if self._real is None:
            if os.environ.get("MERAVIA_NO_SERVER"):
                raise NoServer("no model server here (MERAVIA_NO_SERVER is set: the test suite never reaches a real model)")
            with self._lock:
                if self._real is None:
                    import ollama
                    keep_extra_fields()
                    object.__setattr__(self, "_real", ollama.Client(timeout=config.REQUEST_TIMEOUT))
        return self._real

    def __getattr__(self, name):
        if name.startswith("__") or name in ("_real", "_lock", "_reached"):
            raise AttributeError(name)
        if name in _LazyClient.METHODS:
            def call(*a, **k):
                return getattr(self.real(), name)(*a, **k)
            call.__name__ = name
            return call
        return getattr(self.real(), name)


_client = _LazyClient()
_writes = 0


def reached() -> int:
    """(f518) How many times the process tried to reach the real model client (0 under the suite, where only stand-ins answer)."""
    return _client.reached() if isinstance(_client, _LazyClient) else 0


def built() -> bool:
    """(f518) Whether the real model client was built in this process (never under the suite's switch)."""
    return _client.built() if isinstance(_client, _LazyClient) else True
SYSTEM_PREVIEW = 300
from llm.sampling import RETRY_TEMPERATURE_STEP, shifted   # (f515) one sampling, worked out in llm/sampling.py; these names stay here

T = TypeVar("T", bound=BaseModel)


def _transport(e: BaseException) -> tuple[bool, bool]:
    """(f514) Whether a failed try timed out, and whether it was the server's failure (a dropped connection, a server error), read
    without importing the client's packages: if httpx or ollama is not loaded, none of their errors can exist."""
    hx, ol = sys.modules.get("httpx"), sys.modules.get("ollama")
    timed_out = hx is not None and isinstance(e, hx.TimeoutException)
    server = isinstance(e, ConnectionError) or (hx is not None and isinstance(e, hx.HTTPError)) \
        or (ol is not None and isinstance(e, ol.ResponseError))
    return timed_out, server


# (f516) What a failed try of each kind does: whether it ends the tries, whether the turn's budget is charged for it. A deadline ends the
# tries as a timeout always did (a second request to a stalled server only queues behind the first); the server's failure is one failed
# try, charged, and the next goes; a server that cannot be reached, or a model still loading, ends the tries and costs nothing (f522
# restarts the child); a request refused before it was read (too big for the context, or one the server calls invalid) ends the tries,
# costs nothing, and is filed apart from an outage (refusals: request_refused). Anything else the call raises is "the call failed", one
# failed try, charged, as before (f449). A cancel never gets here: it is an Interrupt (llm/backend.py _cancelled).
ENDS = frozenset({"deadline", "unreachable", "loading", "too_big", "invalid"})
FREE = frozenset({"unreachable", "loading", "too_big", "invalid"})
REFUSED = frozenset({"too_big", "invalid"})


def failed_try(e: BaseException, limit) -> tuple[str, str]:
    """(f516) A failed try's kind ('' for anything that is no Failure) and the words the logs give it. A Failure the old client's error
    was read as (llm/backend.py failure_of) is worded from that error, exactly as before, so nothing logged or recorded moves."""
    from llm import backend
    f = backend.failure_of(e)
    if f is None:
        return "", f"the call failed: {type(e).__name__}: {str(e)[:200]}"
    kind, kind_name = f.kind, (f.legacy or ("", ""))[0]
    text = (f.legacy or ("", f.detail))[1]
    if kind == "cancelled":
        return kind, f.detail or "cancelled"
    if kind == "deadline":                          # (f518) worded from the limit when the try had one: a source that keeps the limit
        on_limit = limit is not None and (not f.legacy or getattr(f, "client_limit", False))   # itself, or the old client's timeout
        return kind, timeout_words(limit, on_client=on_limit)                                   # the budget set; never by reading a client
    if kind == "server":
        return kind, f"the model server failed: {text[:200] or kind_name or 'no reason given'}"
    if kind in ("unreachable", "loading"):
        return kind, f"the model server {'could not be reached' if kind == 'unreachable' else 'was still loading the model'}" \
                     + (f": {f.detail[:200]}" if f.detail else "")
    if kind in REFUSED:
        return kind, ("the request was refused before it was read: "
                      + ("too big for the model's context" if kind == "too_big" else "the server called it invalid")
                      + (f" ({f.detail[:200]})" if f.detail else ""))
    return kind, f"the call failed: {kind}: {f.detail[:200]}"


def warm(client=None) -> None:
    """Load the model now, on a background thread, so the first real call (the character's name, the first scene) does not pay for the load.
    Same context size as every other call, or Ollama would load it twice. Quiet if Ollama is not there; the real call reports that."""
    c = _client if client is None else client      # (f518) the client OllamaShape holds (a test's spy, or the real one)

    def run():
        from llm import backend
        try:                                        # (f517) through the layers as the model's load: the busy light shows while it warms
            backend.loading(lambda: c.chat(model=config.MODEL, think=config.THINK,
                                                 messages=[{"role": "user", "content": "Reply with one word: ready."}],
                                                 options={"num_ctx": config.NUM_CTX, "num_predict": 4, **threads()},
                                                 keep_alive=config.KEEP_ALIVE))
        except Exception:
            pass
    threading.Thread(target=run, daemon=True, name="model-warmup").start()


def unload(client=None) -> None:
    """Tell Ollama to drop the model from memory now (the game is closing). Quiet if Ollama is not there."""
    if not getattr(config, "UNLOAD_ON_EXIT", True):
        return
    try:
        (_client if client is None else client).chat(model=config.MODEL, messages=[], keep_alive=0)
    except Exception:
        pass


FALLBACKS: list[str] = []          # every task that gave up and left its caller to written lines, in order (the live check reads this)
OUTCOMES: list[tuple[str, bool, int]] = []      # (task, succeeded, attempts used), the most recent few hundred, for anyone measuring
TALLY: dict[str, dict[str, int]] = {}           # task -> {calls, failed, attempts} for the whole session (engine/turnlog.py writes it out)
_TASK = threading.local()                       # (f468) the task the calling thread is making a call for (the recorder files it with the call)
_DEADLINE_LOCK = threading.Lock()               # (f468) around the client's timeout being set and put back


@contextlib.contextmanager
def _deadline(seconds, client=None):
    """(f468) The budget's deadline on the client's own timeout for one call (engine/budget.py deadline: what is left of the turn's
    minute, never under the floor), put back after. Only when the client has an inner httpx client with a timeout (the real
    ollama.Client; nothing under the suite's stub or the replayer). The lock is around the setting and the putting back, not the call:
    another thread's call in that window reads the shorter timeout and may fail a try early (the plan's accepted risk).
    (f518) For the client given (OllamaShape's), and nothing is read when the try has no deadline; yields whether it set the timeout,
    so a timed-out try is worded from the limit only when the limit was what cut it (failed_try)."""
    if seconds is None:
        yield False
        return
    inner = getattr(_client if client is None else client, "_client", None)
    if inner is None or not hasattr(inner, "timeout"):
        yield False
        return
    import httpx                                    # (f514) only here, where the real client (and so httpx) already exists
    with _DEADLINE_LOCK:
        before = inner.timeout
        inner.timeout = httpx.Timeout(float(seconds))
    try:
        yield True
    finally:
        with _DEADLINE_LOCK:
            inner.timeout = before


def timeout_words(limit, on_client: bool = False) -> str:
    """(f493) A timed-out try, by the limit it had: the turn's time left when the budget's limit cut it (llm/gateway.py _deadline set
    it on the client, or the source kept it itself), else the client's own. The post-D night logged 'timed out after 120s' for tries
    cut at the budget's deadline some 44 seconds in. (f518) Reads no client: failed_try says whether the limit was the one applied."""
    if limit is not None and on_client:
        return f"timed out after {round(float(limit))}s (what was left of the turn's time)"
    return f"timed out after {config.REQUEST_TIMEOUT}s"


def _chars(system: str, user) -> int:
    """(f468) What a call reads, in characters: the budget's price is from text alone."""
    from engine.prompt import Prompt
    return len(system or "") + len(user.render() if isinstance(user, Prompt) else str(user or ""))


def shape(system: str, typed, user_text) -> dict:
    """(f475) A call's shape, logged beside it and outside its request's hash: what it reads in characters, where they go (the system
    prompt, then each typed part), the tail that changes from call to call (engine/prompt.py tail), and its prompt version, a hash of
    the system text and the layout (version.layout): new wording keeps the layout's half, a reordering moves it."""
    import hashlib
    system = system or ""
    if typed is not None:
        parts, tail, skel = typed.sizes(), len(typed.tail()), typed.skeleton()
    else:
        parts, tail, skel = [], len(str(user_text or "")), ""
    version = hashlib.sha256(system.encode("utf-8")).hexdigest()[:8] + "." + hashlib.sha256(skel.encode("utf-8")).hexdigest()[:6]
    return {"chars": len(system) + len(str(user_text or "")), "sizes": [["system", "", len(system)]] + [[k, l, n] for k, l, n in parts],
            "tail_chars": tail, "prompt_version": version}


def cached_count(response) -> int | None:
    """(f475) The prompt tokens the server read from its cache, when it says (a field the client does not name); None when it does not."""
    extra = getattr(response, "model_extra", None) or {}
    for k, v in sorted(extra.items()):
        if "cache" in k and isinstance(v, int) and not isinstance(v, bool):
            return v
    return None


def _tally(task: str, ok: bool, attempts: int) -> None:
    OUTCOMES.append((task, ok, attempts))
    del OUTCOMES[:-500]
    t = TALLY.setdefault(task, {"calls": 0, "failed": 0, "attempts": 0})
    t["calls"] += 1
    t["failed"] += not ok
    t["attempts"] += attempts


def threads() -> dict:
    """(f370) The runner's CPU threads, when config.NUM_THREAD sets them; nothing otherwise, so Ollama keeps its own default."""
    n = int(getattr(config, "NUM_THREAD", 0) or 0)
    return {"num_thread": n} if n > 0 else {}


def generate(
    task: str,
    system: str,
    user,
    schema: type[T],
    temperature: float = config.DEFAULT_TEMPERATURE,
    retries: int = 2,
    validation_context: dict | None = None,
    max_tokens: int = config.MAX_TOKENS,
    relaxed_context: dict | None = None,
    _quiet: bool = False,
) -> T:
    """`user` is a string, or an engine.prompt.Prompt of typed parts; with a Prompt, any speech in the answer (a schema's spoken()) is checked
    for words lifted from the instructions. With relaxed_context, a call that fails every try is made once more under those looser checks
    (the repetition guard off, say) before giving up: the fallback ladder every speaker shares.
    (f468) The turn's budget is asked first (engine/budget.py allow): a call it does not allow raises its own error, a kind of LLMError
    so the site's fallback stands, that is no failure of the model's (no fallback counted, no refusal filed, no tally)."""
    from engine import asked, budget, operation
    if asked.wanted(task):                          # (f485) an operation needs it: asked outside its transaction, and the operation run again
        from engine.prompt import Prompt
        k = asked.key(task, system, user.render() if isinstance(user, Prompt) else str(user), getattr(schema, "__name__", ""))
        return asked.call(task, k, lambda: generate(task, system, user, schema, temperature, retries, validation_context, max_tokens,
                                                    relaxed_context, _quiet))
    budget.allow(task, _chars(system, user))
    operation.note_legacy(task)                     # (f470) made inside an operation's transaction: the ratchet's residue
    try:
        return _generate(task, system, user, schema, temperature, retries, validation_context, max_tokens)
    except LLMError as e:
        again = getattr(e, "failure", "") in ("unreachable", "loading", "thought_out") or (getattr(e, "failure", "") in REFUSED and getattr(e, "whole", True))
        if relaxed_context is not None and not again:   # (f516) nothing there to read it, or the request as first made refused before it
            try:                                        # was read, is refused again; a retry refused for the draft it carried is not
                return _generate(task, system, user, schema, temperature, 1, relaxed_context, max_tokens)
            except LLMError:
                pass
        if not _quiet:
            FALLBACKS.append(task)
            del FALLBACKS[:-200]
            try:
                from engine import refusals
                if getattr(e, "failure", "") in REFUSED:          # (f516) the request itself, not the model or the server
                    refusals.note("request_refused", task, "the request was refused before it was read; a written fallback was used")
                elif getattr(e, "transport", True):               # (f449) two different troubles, two kinds: the owner's log filed a refused line as an outage
                    refusals.note("model_down", task, "the model server failed or timed out; a written fallback was used")
                else:
                    refusals.note("bad_answer", task, "every answer was refused; a written fallback was used")
            except Exception:
                pass
        raise


def _generate(task, system, user, schema, temperature, retries, validation_context, max_tokens):
    from engine.prompt import Prompt, copied
    from llm import audit
    typed = user if isinstance(user, Prompt) else None
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": typed.render() if typed else user},
    ]
    last_error: Exception | None = None
    _TASK.shape = form = shape(system, typed, messages[1]["content"])      # (f475) logged with every attempt; the recorder keeps it too

    from llm import backend, sampling
    plan = sampling.resolve(task, temperature)                  # (f515) the task's sampling, its ceiling and its shifts, once
    said = []                                   # (f447) the complaints so far: the same one twice running ends the tries
    transport = False                           # (f449) whether the call itself failed (a timeout, the server), as against every answer refused
    failure = ""                                # (f516) the last try's failure kind, '' when it was answered (and the answer refused)
    from engine import budget
    _TASK.name = task
    for attempt in range(retries + 1):
        start = time.perf_counter()
        chars = sum(len(str(m.get("content") or "")) for m in messages)           # (f468) what this attempt reads: a retry reads the draft too
        limit = budget.deadline()                                               # (f493) the limit this try had, for its message
        try:                                                                      # (f515) through the game's own interface; until f528
            reply = backend.chat(messages, schema, plan.at(attempt), max_tokens, deadline=limit)   # its source sends today's request
        except Interrupt:
            raise                                                   # (f449) stopped on purpose (a replay parted), (f516) or cancelled: never a failed try
        except Exception as e:
            # A timeout, a dropped connection, a server error (Ollama answers 500 when the model hits its own repeat limit) or a server
            # that cannot be reached at all (the client raises Python's own ConnectionError while Ollama restarts) is one failed attempt,
            # not the end of the game: the next try goes out warmer, and the turn rolls back if every try fails (f370). (f449) So is
            # anything else the call raises: on the owner's night of 2026-11-01 the third try failed in a way the list here did not name,
            # and the error climbed out of the turn and ended the game. And one timeout ends the tries: a second request to a stalled
            # server only queues behind the first (two tries cost four minutes of waiting), so the turn rolls back at the first.
            # (f516) Each on its kind (ENDS, FREE above); the old client's errors read exactly as they did.
            failure, what = failed_try(e, limit)
            if failure == "cancelled":
                raise Cancelled(what) from e
            if failure not in FREE:
                budget.charge(task, chars)                          # (f468) a try that failed cost what it would have written
            last_error = e.__cause__ if isinstance(e, Failure) and e.legacy and e.__cause__ is not None else e   # the client's own error kept
            transport = transport or failure not in REFUSED
            _log(task, attempt, time.perf_counter() - start, messages, "", what, shape=form)
            audit.record(task, attempt, time.perf_counter() - start, messages, "", what, typed, config.MODEL)
            _debug(f"{task} (attempt {attempt + 1}): {what}")
            if failure in ENDS:
                break
            continue
        failure = ""
        raw = (reply.text or "").replace("\ufffd", "-")                    # a broken character from the model becomes a dash
        elapsed = time.perf_counter() - start
        usage = reply.usage
        thinking = bool(getattr(plan.at(attempt), "think", None))  # (f533) a task chosen to think (config.THINK_TASKS)
        written = len(raw)
        if thinking and (usage or {}).get("out"):                   # (f533) its thinking is written too: priced from the tokens the server
            written = max(written, int(usage["out"] * float(budget.B.get("chars_per_token") or 4)))   # counted (a replay has them recorded)
        budget.charge(task, chars, written)                         # (f468) every attempt is charged, a rejected draft too (decision 9)

        if reply.finish == "length" and (usage or {}).get("full"):
            # (f516) a full slot (the request and its answer filled the context, f521): the request was too big, not the answer long. No
            # cut-off retry is sent, and nobody is told they went round in circles. The try is charged above: it ran.
            failure = "too_big"
            last_error = Failure("too_big", "the request and its answer filled the model's context")
            what = "the request was too big: it and its answer filled the model's context"
            _log(task, attempt, elapsed, messages, raw[:2000], what, usage, shape=form)
            audit.record(task, attempt, elapsed, messages, raw, what, typed, config.MODEL)
            break
        if reply.finish == "length" and thinking and not raw.strip():
            # (f533) the thinking used all the room before the answer began. Telling it to shorten its fields would not reach the
            # thinking, and the next try would think as long again: the tries end here, with the reason named.
            failure = "thought_out"                                     # read by generate(): no relaxed retry, which would think as long
            last_error = LLMError("the thinking used all the room before the answer began")
            what = "the thinking used all its room before the answer began"
            _log(task, attempt, elapsed, messages, "", what, usage, shape=form)
            audit.record(task, attempt, elapsed, messages, "", what, typed, config.MODEL)
            break
        if reply.finish == "length":
            last_error = LLMError("cut off at the length limit")
            reason = cut_off_reason(task, schema, max_tokens)
            _log(task, attempt, elapsed, messages, raw[:2000], reason, usage, shape=form)
            audit.record(task, attempt, elapsed, messages, raw, reason, typed, config.MODEL)
            if said and said[-1] == reason:
                break
            said.append(reason)
            messages = messages[:2] + [{"role": "user", "content": f"Your last answer was rejected: {reason} Respond again with the complete JSON."}]
            continue

        try:
            result = schema.model_validate_json(raw, context=validation_context)
            reason = ""
            if hasattr(result, "spoken"):
                from engine import truth
                given = system + "\n" + messages[1]["content"] + "".join("\n" + str(x) for x in (validation_context or {}).get("given_also", ()))   # (f486)
                known = (validation_context or {}).get("known", ())
                for who, text in result.spoken():
                    lifted = copied(text, system, typed) if typed is not None else ""
                    if lifted:
                        reason = (f"{(who + ': ') if who else ''}'{lifted}' is the instructions' own wording; they describe how to speak and are "
                                  "never lines to say. Say it in your own words")
                        break
                    wrong = truth.check_speech(text, given, known)          # (f315) nothing named that the speaker was not told of
                    if wrong:
                        reason = f"{(who + ': ') if who else ''}{wrong}"
                        break
            if not reason:                                                       # (f364) the content guard: the line the game draws
                from engine import guard
                if guard.guarded(task):
                    alien = guard.foreign(guard.strings_of(result), system + "\n" + str(messages[1]["content"]))   # (f390) another alphabet
                    cat, hit = ("script", alien) if alien else guard.check(guard.strings_of(result))
                    if not cat:                                                  # (f391) the machinery in the prose: JSON, codes, 'the player'
                        from engine import hygiene
                        kind, found = hygiene.problem(task, result)
                        if kind:
                            reason = f"{hygiene.reason(kind)} (not '{found}')"
                    if cat:
                        reason = f"{guard.script_reason() if cat == 'script' else guard.reason(cat)} (not '{hit}')"   # (f370) the word named, or the model writes it again
                        try:
                            from engine import refusals
                            refusals.note("guarded", task, f"{cat}: {hit}")
                        except Exception:
                            pass
            if not reason:
                _log(task, attempt, elapsed, messages, raw, None, usage, shape=form)
                audit.record(task, attempt, elapsed, messages, raw, None, typed, config.MODEL)
                _tally(task, True, attempt + 1)
                try:
                    from engine import hygiene
                    hygiene.undash_answer(task, result)                  # (f396, f403) no dashes in the story, the narrator's or a speaker's
                except Exception:
                    pass
                try:
                    from engine import guard, names
                    if guard.guarded(task):                              # (f412) a name it was told, written wrong ('Zorra' for Zurra)
                        names.mend_answer(result, system + "\n" + str(messages[1]["content"]))
                except Exception:
                    pass
                return result
            last_error = LLMError(reason)
        except ValidationError as e:
            last_error = e
            reason = _summarize(e)
        _log(task, attempt, elapsed, messages, raw, reason, usage, shape=form)
        audit.record(task, attempt, elapsed, messages, raw, reason, typed, config.MODEL)
        _debug(f"rejected {task} (attempt {attempt + 1}): {reason[:200]}")
        if said and said[-1] == reason:         # (f447) told the same thing twice and it answered the same way: a third try is wasted time
            break
        said.append(reason)
        messages = messages[:2] + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": f"That answer was rejected: {reason}\nFix this and respond again with the complete JSON."},
        ]

    _tally(task, False, attempt + 1)
    err = LLMError(f"{task}: no valid response after {attempt + 1} attempts")
    err.transport = transport                   # (f449) read by generate(): a server down is not the same refusal as every answer refused
    err.failure = failure                       # (f516) ...and a request refused before it was read is neither
    err.whole = len(messages) == 2              # (f516) whether that last try was the request as first made, or a retry carrying its draft
    raise err from last_error


def _debug(message: str) -> None:
    """A rejection, shown in debug mode as it happens (the audit log keeps the whole of it)."""
    if not getattr(config, "DEBUG", False):
        return
    try:
        from ui import console
        console.debug(message)
    except Exception:
        pass


def _summarize(e: ValidationError) -> str:
    parts = []
    for err in e.errors():
        loc = ".".join(str(x) for x in err["loc"])
        msg = err["msg"].removeprefix("Value error, ")
        parts.append(f"{loc}: {msg}" if loc else msg)
    return "; ".join(parts)[:1500]


def _compact(messages: list[dict]) -> list[dict]:
    """Shorten system prompts for the log; they are the same on every call and make up most of its size."""
    if getattr(config, "LOG_FULL_PROMPTS", False):
        return messages
    out = []
    for m in messages:
        if m["role"] == "system" and len(m["content"]) > SYSTEM_PREVIEW:
            out.append({"role": "system", "content": m["content"][:SYSTEM_PREVIEW] + " [...shortened in log]"})
        elif m["role"] == "assistant":
            out.append({"role": "assistant", "content": "[previous answer - see the entry before this one]"})
        else:
            out.append(m)
    return out


def trim_log(path: Path | None = None) -> None:
    """Keep the log small: past LOG_MAX_MB, keep only the most recent LOG_KEEP_ENTRIES entries."""
    path = path or Path(config.LOG_PATH)
    limit = getattr(config, "LOG_MAX_MB", 5) * 1024 * 1024
    if not path.exists() or path.stat().st_size <= limit:
        return
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    keep = lines[-getattr(config, "LOG_KEEP_ENTRIES", 300):]
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(keep) + "\n", encoding="utf-8")
    tmp.replace(path)


_log_lock = threading.Lock()


def cut_off_reason(task: str, schema, max_tokens: int) -> str:
    """(f433) What an answer cut off at its token ceiling is told on the retry. The owner: "No length limits on the narrator or the
    speakers" (GOALS.md, f375). The narrator and every speaker write under the runaway ceiling (PROSE_MAX_TOKENS), which no passage that
    holds what its moment holds comes near, so an answer cut off there went round in circles: it is told that, and never to be short,
    which was a length limit by the back door. A narrator's task, or any answer someone speaks in (a schema with spoken()), is told the
    same under a lower ceiling. Only the engine's own structured calls (reading a line, authoring records) are still asked to keep fields
    short so the JSON closes."""
    from engine import hygiene
    if max_tokens >= config.PROSE_MAX_TOKENS or task in hygiene.NARRATOR or hasattr(schema, "spoken"):
        return "the answer ran on until it was cut off, which means it went round in circles. Say what the moment holds once, then stop."
    return "the answer was cut off before the JSON was finished. Keep every field short."


def _usage(response) -> dict | None:
    """Ollama's own counts for one answer: tokens read and written, and the milliseconds each took (plus a model load, if one happened).
    None under a stand-in model, which reports none."""
    count = getattr(response, "prompt_eval_count", None)
    if count is None:
        return None
    ms = lambda name: round((getattr(response, name, 0) or 0) / 1e6)
    out = {"prompt": count, "out": getattr(response, "eval_count", 0) or 0, "read_ms": ms("prompt_eval_duration"),
           "write_ms": ms("eval_duration"), "load_ms": ms("load_duration"), "total_ms": ms("total_duration")}
    cached = cached_count(response)
    if cached is not None:
        out["cached"] = cached                          # (f475) of the prompt's tokens, how many the server had cached
    return out


_tag = threading.local()


@contextlib.contextmanager
def tagged(**fields):
    """(f385) Fields added to every call logged inside: a rewrite says it is one, and why, so its draft (the call before it, same task)
    reads as replaced in logs/llm_calls.jsonl."""
    before = getattr(_tag, "fields", None)
    _tag.fields = {**(before or {}), **fields}
    try:
        yield
    finally:
        _tag.fields = before


def _log(task, attempt, elapsed, messages, raw, error, usage=None, shape=None):
    global _writes
    path = Path(config.LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    from llm import audit
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "turn": audit.current_turn(),                   # joins this call to its row in the turn log (engine/turnlog.py)
        "task": task,
        "model": config.MODEL,
        "attempt": attempt,
        "seconds": round(elapsed, 2),
        "messages": _compact(messages),
        "raw": raw,
        "error": error,
    }
    if usage:
        entry["tokens"] = usage                         # what the call cost the model (tools/latency.py reads these)
    if shape:
        entry.update(shape)                             # (f475) chars, sizes, tail_chars, prompt_version: the prompt's shape, measured
    entry.update(getattr(_tag, "fields", None) or {})
    with _log_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        _writes += 1
        if _writes % 50 == 1:
            trim_log(path)
