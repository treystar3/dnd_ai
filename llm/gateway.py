"""The only place the game talks to Ollama.

Every call is schema-constrained, validated, retried on failure, and logged.
On a failed validation the model is shown its answer and the reason it was
rejected, so the retry can fix the specific problem.
Callers get a validated proposal object or an LLMError, never raw text.
"""

import json
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


def generate(
    task: str,
    system: str,
    user: str,
    schema: type[T],
    temperature: float = config.DEFAULT_TEMPERATURE,
    retries: int = 2,
    validation_context: dict | None = None,
    max_tokens: int = config.MAX_TOKENS,
) -> T:
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    last_error: Exception | None = None

    for attempt in range(retries + 1):
        start = time.perf_counter()
        try:
            response = _client.chat(
                model=config.MODEL,
                think=config.THINK,
                messages=messages,
                format=schema.model_json_schema(),
                options={"temperature": min(1.2, temperature + RETRY_TEMPERATURE_STEP * attempt),
                         "num_ctx": config.NUM_CTX, "num_predict": max_tokens},
            )
        except httpx.TimeoutException as e:
            last_error = e
            _log(task, attempt, time.perf_counter() - start, messages, "", f"timed out after {config.REQUEST_TIMEOUT}s")
            continue
        raw = response.message.content
        elapsed = time.perf_counter() - start

        if response.done_reason == "length":
            last_error = LLMError("cut off at the length limit")
            reason = "the answer was cut off because it was far too long. Keep every field short."
            _log(task, attempt, elapsed, messages, raw[:2000], reason)
            messages = messages[:2] + [{"role": "user", "content": f"Your last answer was rejected: {reason} Respond again with the complete JSON."}]
            continue

        try:
            result = schema.model_validate_json(raw, context=validation_context)
            _log(task, attempt, elapsed, messages, raw, None)
            return result
        except ValidationError as e:
            last_error = e
            reason = _summarize(e)
            _log(task, attempt, elapsed, messages, raw, reason)
            messages = messages[:2] + [
                {"role": "assistant", "content": raw},
                {"role": "user", "content": f"That answer was rejected: {reason}\nFix this and respond again with the complete JSON."},
            ]

    raise LLMError(f"{task}: no valid response after {retries + 1} attempts") from last_error


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


def _log(task, attempt, elapsed, messages, raw, error):
    global _writes
    path = Path(config.LOG_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "time": datetime.now(timezone.utc).isoformat(),
        "task": task,
        "model": config.MODEL,
        "attempt": attempt,
        "seconds": round(elapsed, 2),
        "messages": _compact(messages),
        "raw": raw,
        "error": error,
    }
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    _writes += 1
    if _writes % 50 == 1:
        trim_log(path)
