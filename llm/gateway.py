"""The only place the game talks to Ollama.

Every call is schema-constrained, validated, retried on failure, and logged.
On a failed validation the model is shown its answer and the reason it was
rejected, so the retry can fix the specific problem.
Callers get a validated proposal object or an LLMError, never raw text.
"""

import json
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TypeVar

import httpx
import ollama
from pydantic import BaseModel, ValidationError

import config

_client = ollama.Client(timeout=config.REQUEST_TIMEOUT)
_writes = 0
SYSTEM_PREVIEW = 300
RETRY_TEMPERATURE_STEP = 0.15

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    pass


def warm() -> None:
    """Load the model now, on a background thread, so the first real call (the character's name, the first scene) does not pay for the load.
    Same context size as every other call, or Ollama would load it twice. Quiet if Ollama is not there; the real call reports that."""
    def run():
        try:
            _client.chat(model=config.MODEL, think=config.THINK, messages=[{"role": "user", "content": "Reply with one word: ready."}],
                         options={"num_ctx": config.NUM_CTX, "num_predict": 4}, keep_alive=config.KEEP_ALIVE)
        except Exception:
            pass
    threading.Thread(target=run, daemon=True, name="model-warmup").start()


def unload() -> None:
    """Tell Ollama to drop the model from memory now (the game is closing). Quiet if Ollama is not there."""
    if not getattr(config, "UNLOAD_ON_EXIT", True):
        return
    try:
        _client.chat(model=config.MODEL, messages=[], keep_alive=0)
    except Exception:
        pass


FALLBACKS: list[str] = []          # every task that gave up and left its caller to written lines, in order (the live check reads this)
OUTCOMES: list[tuple[str, bool, int]] = []      # (task, succeeded, attempts used), the most recent few hundred, for anyone measuring
TALLY: dict[str, dict[str, int]] = {}           # task -> {calls, failed, attempts} for the whole session (engine/turnlog.py writes it out)


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
    (the repetition guard off, say) before giving up: the fallback ladder every speaker shares."""
    try:
        return _generate(task, system, user, schema, temperature, retries, validation_context, max_tokens)
    except LLMError:
        if relaxed_context is not None:
            try:
                return _generate(task, system, user, schema, temperature, 1, relaxed_context, max_tokens)
            except LLMError:
                pass
        if not _quiet:
            FALLBACKS.append(task)
            del FALLBACKS[:-200]
            try:
                from engine import refusals
                refusals.note("model_down", task, "the call gave up after every try; a written fallback was used")
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

    tuned = dict(getattr(config, "SAMPLING", {}).get(task, {}))
    base = tuned.pop("temperature", temperature)
    top = min(1.2, base + 0.1) if task in getattr(config, "SAMPLING", {}) else 1.2      # a retry warms a tuned task only a little
    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            response = _client.chat(
                model=config.MODEL,
                think=config.THINK,
                messages=messages,
                format=schema.model_json_schema(),
                options={"temperature": min(top, base + RETRY_TEMPERATURE_STEP * attempt),
                         "num_ctx": config.NUM_CTX, "num_predict": max_tokens, **tuned},
                keep_alive=config.KEEP_ALIVE,
            )
        except (httpx.TimeoutException, httpx.HTTPError, ollama.ResponseError, ConnectionError) as e:
            # A timeout, a dropped connection, a server error (Ollama answers 500 when the model hits its own repeat limit) or a server
            # that cannot be reached at all (the client raises Python's own ConnectionError while Ollama restarts) is one failed attempt,
            # not the end of the game: the next try goes out warmer, and the turn rolls back if every try fails (f370).
            last_error = e
            what = (f"timed out after {config.REQUEST_TIMEOUT}s" if isinstance(e, httpx.TimeoutException)
                    else f"the model server failed: {str(e)[:200] or type(e).__name__}")
            _log(task, attempt, time.perf_counter() - start, messages, "", what)
            audit.record(task, attempt, time.perf_counter() - start, messages, "", what, typed, config.MODEL)
            _debug(f"{task} (attempt {attempt + 1}): {what}")
            continue
        raw = (response.message.content or "").replace("\ufffd", "-")      # a broken character from the model becomes a dash
        elapsed = time.perf_counter() - start
        usage = _usage(response)

        if response.done_reason == "length":
            last_error = LLMError("cut off at the length limit")
            reason = "the answer was cut off because it was far too long. Keep every field short."
            _log(task, attempt, elapsed, messages, raw[:2000], reason, usage)
            audit.record(task, attempt, elapsed, messages, raw, reason, typed, config.MODEL)
            messages = messages[:2] + [{"role": "user", "content": f"Your last answer was rejected: {reason} Respond again with the complete JSON."}]
            continue

        try:
            result = schema.model_validate_json(raw, context=validation_context)
            reason = ""
            if hasattr(result, "spoken"):
                from engine import truth
                given = system + "\n" + messages[1]["content"]
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
                    cat, hit = guard.check(guard.strings_of(result))
                    if cat:
                        reason = guard.reason(cat)
                        try:
                            from engine import refusals
                            refusals.note("guarded", task, f"{cat}: {hit}")
                        except Exception:
                            pass
            if not reason:
                _log(task, attempt, elapsed, messages, raw, None, usage)
                audit.record(task, attempt, elapsed, messages, raw, None, typed, config.MODEL)
                _tally(task, True, attempt + 1)
                return result
            last_error = LLMError(reason)
        except ValidationError as e:
            last_error = e
            reason = _summarize(e)
        _log(task, attempt, elapsed, messages, raw, reason, usage)
        audit.record(task, attempt, elapsed, messages, raw, reason, typed, config.MODEL)
        _debug(f"rejected {task} (attempt {attempt + 1}): {reason[:200]}")
        messages = messages[:2] + [
            {"role": "assistant", "content": raw},
            {"role": "user", "content": f"That answer was rejected: {reason}\nFix this and respond again with the complete JSON."},
        ]

    _tally(task, False, retries + 1)
    raise LLMError(f"{task}: no valid response after {retries + 1} attempts") from last_error


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


def _usage(response) -> dict | None:
    """Ollama's own counts for one answer: tokens read and written, and the milliseconds each took (plus a model load, if one happened).
    None under a stand-in model, which reports none."""
    count = getattr(response, "prompt_eval_count", None)
    if count is None:
        return None
    ms = lambda name: round((getattr(response, name, 0) or 0) / 1e6)
    return {"prompt": count, "out": getattr(response, "eval_count", 0) or 0, "read_ms": ms("prompt_eval_duration"),
            "write_ms": ms("eval_duration"), "load_ms": ms("load_duration"), "total_ms": ms("total_duration")}


def _log(task, attempt, elapsed, messages, raw, error, usage=None):
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
    with _log_lock:
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        _writes += 1
        if _writes % 50 == 1:
            trim_log(path)
