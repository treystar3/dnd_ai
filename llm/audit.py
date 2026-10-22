"""The audit log (f314): every call to the model, written for a person to read afterwards.

One Markdown file per session under logs/audit/ (data/rules/audit_log.yaml). For each call: which turn it belongs to and what the player
typed, why the game made the call, the system prompt (in full the first time, then by reference while it is unchanged), the user prompt
in full - with the typed parts marked when the prompt was built from them (engine/prompt.py: what is an instruction, what is a fact, what
is history) - the model's answer, and the verdict: accepted, or rejected with the reason it was sent back. Nothing is trimmed; a file that
grows past the limit says so and stops.

The gateway (llm/gateway.py) reports every attempt here; the world scene reports the turn (note_turn)."""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
A = yaml.safe_load((ROOT / "data" / "rules" / "audit_log.yaml").read_text(encoding="utf-8"))

_lock = threading.Lock()
_path: Path | None = None
_count = 0
_turn: tuple[int, str] = (-1, "")
_turn_written: tuple = (-2, "")
_system_seen: dict[str, tuple[str, int]] = {}      # task -> (hash of the system prompt, entry number it was written in full)
_first_attempt: dict[str, int] = {}                 # task -> entry number of the latest first attempt (a retry's prompt is that one again)
_full = False


def enabled() -> bool:
    try:
        import config
        return bool(getattr(config, "AUDIT_LOG", A.get("enabled", True)))
    except Exception:
        return bool(A.get("enabled", True))


def path() -> Path:
    global _path
    if _path is None:
        folder = ROOT / A.get("folder", "logs/audit")
        folder.mkdir(parents=True, exist_ok=True)
        _path = folder / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.md"
        _path.write_text(f"# Audit log - session started {datetime.now().isoformat(timespec='seconds')}\n\n"
                         "Every call to the model this session: the turn it served, why it was made, the prompts in full, the answer, and the verdict.\n\n",
                         encoding="utf-8")
    return _path


def note_turn(turn: int, text: str) -> None:
    """The world scene says which turn is running and what the player typed; the next calls are filed under it."""
    global _turn
    _turn = (turn, text or "")


def current_turn() -> int:
    """The turn the calls being made belong to (-1 before play starts): the key that joins the model log to the turn log."""
    return _turn[0]


def _h(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:10]


def _typed_parts(prompt) -> str:
    """A prompt built from typed parts, rendered with each part's kind in the margin, so a reader sees what the model was told as a rule,
    as a fact, as material it may quote, and as history."""
    out = []
    for kind, label, text in prompt.parts:
        head = f"[{kind}{(' · ' + label) if label else ''}]"
        out.append(f"{head}\n{text}")
    return "\n\n".join(out)


def record(task: str, attempt: int, elapsed: float, messages: list[dict], raw: str, error: str | None, typed=None, model: str = "") -> None:
    """One attempt of one call. messages are the full messages sent (system, user, and on a retry the rejected answer and the complaint)."""
    global _count, _turn_written, _full
    if not enabled():
        return
    with _lock:
        p = path()
        if _full:
            return
        if p.stat().st_size > A.get("max_mb", 200) * 1024 * 1024:
            with p.open("a", encoding="utf-8") as f:
                f.write("\n---\n\n**The log has reached its size limit for this session; later calls are not recorded.**\n")
            _full = True
            return
        _count += 1
        lines = []
        if _turn != _turn_written:
            lines.append(f"\n---\n\n# Turn {_turn[0]}: \"{_turn[1]}\"\n" if _turn[0] >= 0 else f"\n---\n\n# {_turn[1] or 'Before the first turn'}\n")
            _turn_written = _turn
        why = A["tasks"].get(task, "")
        verdict = "accepted" if error is None else f"rejected - {error}"
        lines.append(f"\n## #{_count} · {task} · attempt {attempt + 1} · {elapsed:.1f}s" + (f" · {model}" if model else ""))
        lines.append(f"**Why:** {why or task}  ")
        lines.append(f"**Verdict:** {verdict}\n")
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        seen = _system_seen.get(task)
        h = _h(system)
        if seen and seen[0] == h:
            lines.append(f"**System prompt:** unchanged since #{seen[1]}.\n")
        else:
            _system_seen[task] = (h, _count)
            lines.append("<details><summary><b>System prompt</b></summary>\n\n```text\n" + system.strip() + "\n```\n</details>\n")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
        if attempt == 0:
            _first_attempt[task] = _count
        if attempt > 0 and task in _first_attempt:
            lines.append(f"**User prompt:** the same as #{_first_attempt[task]} (a retry sends the prompt again, with the complaint below).\n")
        elif typed is not None:
            lines.append("<details open><summary><b>User prompt</b> (typed parts: instruction = how to behave, fact = what is so, material = words it may use, history = what was said)</summary>\n\n```text\n"
                         + _typed_parts(typed) + "\n```\n</details>\n")
        else:
            lines.append("<details open><summary><b>User prompt</b></summary>\n\n```text\n" + user.strip() + "\n```\n</details>\n")
        complaint = [m["content"] for m in messages[2:] if m["role"] == "user"]
        if complaint:
            lines.append("**Sent back with:** " + complaint[-1].strip() + "\n")
        shown = raw.strip() if raw else "(no answer)"
        try:
            shown = json.dumps(json.loads(shown), ensure_ascii=False, indent=2)
        except Exception:
            pass
        lines.append("**Answer:**\n\n```json\n" + shown + "\n```\n")
        with p.open("a", encoding="utf-8") as f:
            f.write("\n".join(lines))


def summary() -> str:
    return f"{path()} ({_count} calls recorded)" if enabled() else "the audit log is off (config.AUDIT_LOG)"
