"""The one way the game asks the model (through llm/backend.py, whatever source answers there).

Every call is schema-constrained, validated, retried on failure, and logged.
On a failed validation the model is shown its answer and the reason it was
rejected, so the retry can fix the specific problem.
Callers get a validated proposal object or an LLMError, never raw text.
"""

import contextlib
import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError

import config

from core.interrupts import Interrupt   # (f449) an exception raised on purpose (a replay parted) is never a failed try
from llm.errors import Cancelled, Failure, LLMError   # (f514) the classes live where importing them starts nothing; LLMError stays here


_writes = 0                                     # rows written to the call log this session (trim_log counts them)
SYSTEM_PREVIEW = 300
from llm.sampling import RETRY_TEMPERATURE_STEP, shifted   # (f515) one sampling, worked out in llm/sampling.py; these names stay here

T = TypeVar("T", bound=BaseModel)


# (f516) What a failed try of each kind does: whether it ends the tries, whether the turn's budget is charged for it. A deadline ends the
# tries (a second request to a stalled server only queues behind the first); the server's failure is one failed try, charged, and the
# next goes; a server that cannot be reached, or a model still loading, ends the tries and costs nothing (f522 restarts the child); a
# request refused before it was read (too big for the context, or one the server calls invalid) ends the tries, costs nothing, and is
# filed apart from an outage (refusals: request_refused). Anything else the call raises is "the call failed", one failed try, charged,
# as before (f449). A cancel never gets here: it is an Interrupt (llm/backend.py _cancelled).
ENDS = frozenset({"deadline", "unreachable", "loading", "too_big", "invalid"})
FREE = frozenset({"unreachable", "loading", "too_big", "invalid"})
REFUSED = frozenset({"too_big", "invalid"})


def failed_try(e: BaseException, limit) -> tuple[str, str]:
    """(f516) A failed try's kind ('' for anything that is no Failure) and the words the logs give it. A Failure read from a plain error
    (llm/backend.py failure_of: a ConnectionError raised on purpose) is worded from that error, as it always was."""
    from llm import backend
    f = backend.failure_of(e)
    if f is None:
        return "", f"the call failed: {type(e).__name__}: {str(e)[:200]}"
    kind, kind_name = f.kind, (f.legacy or ("", ""))[0]
    text = (f.legacy or ("", f.detail))[1]
    if kind == "cancelled":
        return kind, f.detail or "cancelled"
    if kind == "deadline":                          # (f518, f532) worded from the turn's limit when the try had one: a source keeps the
        on_limit = limit is not None and not f.legacy    # limit itself; a replayed pair of the old client's is worded as the client's own
        return kind, timeout_words(limit, on_client=on_limit)
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


FALLBACKS: list[str] = []          # every task that gave up and left its caller to written lines, in order (the live check reads this)
OUTCOMES: list[tuple[str, bool, int]] = []      # (task, succeeded, attempts used), the most recent few hundred, for anyone measuring
TALLY: dict[str, dict[str, int]] = {}           # task -> {calls, failed, attempts} for the whole session (engine/turnlog.py writes it out)
_TASK = threading.local()                       # (f468) the task the calling thread is making a call for (the recorder files it with the call)


def timeout_words(limit, on_client: bool = False) -> str:
    """(f493) A timed-out try, by the limit it had: the turn's time left when the budget's limit cut it (the source keeps the limit,
    llm/llama.py Server.request), else the source's own (config.REQUEST_TIMEOUT, or a slow machine's hang guard). The post-D night
    logged 'timed out after 120s' for tries cut at the budget's deadline some 44 seconds in."""
    if limit is not None and on_client:
        return f"timed out after {round(float(limit))}s (what was left of the turn's time)"
    from engine import budget
    if budget.SLOW:                                     # (f526) a slow machine's call is cut only at the hang guard
        return "timed out at the slow machine's hang guard"
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


def _tally(task: str, ok: bool, attempts: int) -> None:
    OUTCOMES.append((task, ok, attempts))
    del OUTCOMES[:-500]
    t = TALLY.setdefault(task, {"calls": 0, "failed": 0, "attempts": 0})
    t["calls"] += 1
    t["failed"] += not ok
    t["attempts"] += attempts


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
    from llm import backend
    try:
        with backend.task(task):                    # (f536) the source may place the call by its task (the understanding's own slot)
            return _generate(task, system, user, schema, temperature, retries, validation_context, max_tokens)
    except LLMError as e:
        again = (getattr(e, "failure", "") in ("unreachable", "loading", "thought_out") or getattr(e, "transport", False)
                 or (getattr(e, "failure", "") in REFUSED and getattr(e, "whole", True)))
        if relaxed_context is not None and not again:   # (f516) nothing there to read it, or the request as first made refused before it
            try:                                        # was read (too big, invalid), is refused again; a retry refused for the draft it
                                                        # carried is not, so the request as first made goes once more; (f527) nor after a
                                                        # transport failure on any try (the server, a timeout): looser checks mend no outage
                with backend.task(task):
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
            # A timeout, a dropped connection, a server error (a 500 when the model hits its own repeat limit) or a server that
            # cannot be reached at all (llama-server restarting, llm/runtime.py) is one failed attempt,
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
        budget.charge(task, chars, written, budget.cached_share(usage))   # (f468) every attempt is charged, a rejected draft too (decision 9);
                                                                    # (f538) the prompt the server reused from its cache is not

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
    """Keep the log small: past LOG_MAX_MB, keep only the most recent LOG_KEEP_ENTRIES entries. (f566) Never raises: a trim the system
    refuses (another process holding the log, or trimming it too) is left for the next one, the log whole and no temp behind."""
    path = path or Path(config.LOG_PATH)
    tmp = path.with_name(f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")   # (f566) its own temp, never another trim's
    try:
        limit = getattr(config, "LOG_MAX_MB", 5) * 1024 * 1024
        if not path.is_file() or path.stat().st_size <= limit:
            return
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        keep = lines[-getattr(config, "LOG_KEEP_ENTRIES", 300):]
        tmp.write_text("\n".join(keep) + "\n", encoding="utf-8", newline="\n")
        tmp.replace(path)
    except OSError:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


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
        try:                                            # (f566) a log that cannot be written never fails the call it records
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except OSError:
            return
        _writes += 1
        if _writes % 50 == 1:
            trim_log(path)
