"""The audit log (f314): every call to the model, written for a person to read afterwards.

One Markdown file per session in FOLDER, logs/audit under the one logs folder (f779: core.paths.logs(); a test's own under the suite),
with its numbers in data/rules/audit_log.yaml, while config.AUDIT_LOG, its one switch, is on (f778). For
each call: which turn it belongs to and what the player typed, why the game made the call, the system prompt (in full the first time,
then by reference while it is unchanged), the user prompt in full - with the typed parts marked when the prompt was built from them
(engine/prompt.py: what is an instruction, what is a fact, what is history) - the model's answer, and the verdict: accepted, or rejected
with the reason it was sent back. Nothing is trimmed; a file that grows past the limit says so and stops. (f779) The folder keeps the
newest keep_sessions session files: the older ones go when a session's file is named.

The gateway (llm/gateway.py) reports every attempt here; the world scene reports the turn (note_turn)."""
from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import datetime
from pathlib import Path

import yaml

import config
from core import paths, yamlio

A = yamlio.safe_load((Path(paths.BUNDLE) / "data" / "rules" / "audit_log.yaml").read_text(encoding="utf-8"))   # (f777) a built game's data is in the bundle
FOLDER = Path("logs/audit")           # (f779) placed by core.paths when named: in the one logs folder; a night tool's own, absolute

_lock = threading.Lock()
_path: Path | None = None
_count = 0
_turn: tuple[int, str] = (-1, "")
_turn_written: tuple = (-2, "")
_system_seen: dict[str, tuple[str, int]] = {}      # task -> (hash of the system prompt, entry number it was written in full)
_first_attempt: dict[str, int] = {}                 # task -> entry number of the latest first attempt (a retry's prompt is that one again)
_full = False


def enabled() -> bool:
    """Whether calls are written: config.AUDIT_LOG, the log's one switch (f778: audit_log.yaml holds none)."""
    return bool(config.AUDIT_LOG)


def path() -> Path:
    global _path
    if _path is None:
        folder = paths.written(FOLDER)                                 # (f777) beside the exe, with the other logs
        folder.mkdir(parents=True, exist_ok=True)
        _path = folder / f"{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.md"
        _path.write_text(f"# Audit log - session started {datetime.now().isoformat(timespec='seconds')}\n\n"
                         "Every call to the model this session: the turn it served, why it was made, the prompts in full, the answer, and the verdict.\n\n",
                         encoding="utf-8")
        prune(folder, keep=_path)                                      # (f779) the folder keeps a window of sessions, this one among them
    return _path


SESSION_FILE = re.compile(r"\d{4}-\d{2}-\d{2}_\d{6}\.md")            # a session's file as path() names it


def number(key: str) -> float | None:
    """A number of audit_log.yaml's (keep_sessions, max_mb), or None when the table holds none: the startup check refuses that, and a
    tool that skips the check must never fail the call being recorded over it (f566)."""
    v = A.get(key)
    return v if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def prune(folder: Path, keep: Path | None = None) -> None:
    """The folder keeps keep_sessions session files (audit_log.yaml) and the rest are removed. `keep`, the session just named, is always
    kept and counts as one of them, whatever its name: a clock set back, or a folder copied from another machine, can name it before
    files already there. The others kept are the latest by name, which is the time each was named on the clock that named it. Only files
    of a session's own dated name are touched. Never raises: with no number for keep_sessions every file stays, and a file that cannot
    be removed now is left for the next session."""
    window = number("keep_sessions")
    if window is None:
        return
    try:
        others = sorted(p for p in Path(folder).iterdir() if p.is_file() and SESSION_FILE.fullmatch(p.name)
                        and (keep is None or p.name != Path(keep).name))
    except OSError:
        return
    room = int(window) - (keep is not None)
    for p in (others[:-room] if room > 0 else others):
        try:
            p.unlink()
        except OSError:
            pass


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
    """One attempt of one call. messages are the full messages sent (system, user, and on a retry the rejected answer and the complaint).
    (f566) Never raises: the file that cannot be written (a full disk, a scanner holding it) must never fail the call it records, which
    the gateway files here right after the answer is accepted, outside the tries' own error handling. (f782) A write the system refuses
    is only counted; any other fault is written down once (crashlog.carried)."""
    from engine import crashlog
    with crashlog.carried(f"the audit log, a try's entry: {task}", quiet=(OSError,)):
        _record(task, attempt, elapsed, messages, raw, error, typed, model)


def _record(task: str, attempt: int, elapsed: float, messages: list[dict], raw: str, error: str | None, typed=None, model: str = "") -> None:
    global _count, _turn_written, _full
    if not enabled():
        return
    with _lock:
        p = path()
        if _full:
            return
        ceiling = number("max_mb")                                     # (f779) none in the table: nothing more is written, nothing raised
        if ceiling is None or p.stat().st_size > ceiling * 1024 * 1024:
            with p.open("a", encoding="utf-8", errors="backslashreplace") as f:
                f.write("\n---\n\n**The log has reached its size limit for this session; later calls are not recorded.**\n")
            _full = True
            return
        n = _count + 1                                  # (f782) this entry's number, and what it changes, kept only once it is written
        lines = []
        turn = _turn
        heading = turn != _turn_written
        if heading:
            lines.append(f"\n---\n\n# Turn {turn[0]}: \"{turn[1]}\"\n" if turn[0] >= 0 else f"\n---\n\n# {turn[1] or 'Before the first turn'}\n")
        why = A["tasks"].get(task, "")
        verdict = "accepted" if error is None else f"rejected - {error}"
        from engine import actor, operation as _op
        op = _op.current()
        where = f" · operation {op.id} ({op.kind})" if op is not None else " · outside any operation"      # (f471) the key to the turn log's ops
        who = actor.who()
        where += f" · actor {who}" if who else " · no actor"                                               # (f629) who it was made for
        lines.append(f"\n## #{n} · {task} · attempt {attempt + 1} · {elapsed:.1f}s" + (f" · {model}" if model else "") + where)
        lines.append(f"**Why:** {why or task}  ")
        lines.append(f"**Verdict:** {verdict}\n")
        system = next((m["content"] for m in messages if m["role"] == "system"), "")
        seen = _system_seen.get(task)
        h = _h(system)
        whole = not (seen and seen[0] == h)
        if not whole:
            lines.append(f"**System prompt:** unchanged since #{seen[1]}.\n")
        else:
            lines.append("<details><summary><b>System prompt</b></summary>\n\n```text\n" + system.strip() + "\n```\n</details>\n")
        user = next((m["content"] for m in messages if m["role"] == "user"), "")
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
        with p.open("a", encoding="utf-8", errors="backslashreplace") as f:
            f.write("\n".join(lines))
        _count = n
        if heading:
            _turn_written = turn
        if whole:
            _system_seen[task] = (h, n)
        if attempt == 0:
            _first_attempt[task] = n


def summary() -> str:
    return f"{path()} ({_count} calls recorded)" if enabled() else "the audit log is off (config.AUDIT_LOG)"
