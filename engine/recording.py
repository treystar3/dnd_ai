"""(f440) A recording of a play session that the real turn can replay (tools/rerun.py): the rebuild's Stage 1.

Every later stage of the rebuild is checked against what the game did before it. A recording keeps everything a session depended on
from outside the save, so the same session can be played again through the same code (or through the code a stage has changed) and
compared input by input:

  recordings/<name>/start.db       the save as the session opened (an sqlite backup, taken before anything is played)
  recordings/<name>/meta.json      the seed, the data hash (storage/statehash.py), the model, the version and commit, the start state
  recordings/<name>/inputs.jsonl   every line the player gave, a question's answer mid-turn and a pane's command included
  recordings/<name>/calls.jsonl.gz every call to the model, in order: the request in full, the answer or the failure, its time
  recordings/<name>/turns.jsonl    after each input: the state's fingerprint, what the turn recorded, and what the player was shown

(f732) A kept recording (under data/replay) holds its calls as plain calls.jsonl, which git stores as a delta at each re-bless;
read_calls reads either form, and is the one place a log is opened by its name.

(f517) It is a layer of the game's own interface to the model (llm/backend.py wrap, rank RECORDER, outermost) and wraps the console in
place, so whatever is installed beneath it (the real client, the window, a test's stand-in, a night run) is recorded as it is. (f527)
Each row is the request in the interface's own, neutral form (backend.neutral_request: the messages, the schema's title and
fingerprint, every sampler, the answer's ceiling, whether it thinks, the voice, the model id; an embed's model and texts) and its
fingerprint `req` (request_hash: the whole of that, nothing of the machine, never the deadline), with the reply's `answer`, `finish`
(stop, length or cancelled) and `usage` (the source's counts: prompt, out, read_ms, write_ms, cached, ...), or an `error` {kind, detail}
on the interface's kinds (llm/errors.py). A cancelled call writes no row: it is no answer and no failure, and its number is skipped. (R5) A recorded call that starts while another recorded call is still on its way is an overlap:
its row is marked, meta.json counts them (overlapped, written at close), and tools/rerun.py refuses such a recording, since a replay
serves the calls one after another. (f442) What the player's own side asks of the model
while it decides its line (the night bot writing its words) is the input, not the game: it is left out, since a replay feeds the line
itself; a call from another thread in that time (the background residents) is the game's and is kept. A recording session is strict (engine/streams.py
STRICT): the background people and the embedding model's arrival are fixed at an input's edge, so the session can replay exactly.
Only RECORD_KEEP recordings are kept; the oldest go first."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import shutil
import sqlite3
import subprocess
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import config
from engine import actor
from llm.errors import Failure                  # (f527) the interface's own failure kinds, no model client

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "recordings"
KEPT = ROOT / "data" / "replay"         # (f732) a recording kept in git: its call log is written plain, so a re-bless is stored as a delta
CALLS = ("calls.jsonl", "calls.jsonl.gz")   # a recording's call log: plain (kept), gzipped (played); read in this order
STORY = ("narrate", "say", "npc_says", "dialogue", "note", "wait", "ledger")   # what the player reads (engine/turnlog.py), and the engine's facts
ORPHANS: set = set()     # (f453) threads a closed session left running (a creation call, people being written): the Thread objects, never
                         # their idents, which the OS hands out again; their calls pass through the recorder unrecorded (_layer)


def orphan(threads) -> None:
    """(f453) A session closed with these threads still running (engine/session.py close): remembered, and the dead ones forgotten."""
    ORPHANS.difference_update({t for t in ORPHANS if not t.is_alive()})
    ORPHANS.update(threads)


def request_hash(k: dict) -> str:
    """(f527) What a call asked for, as one fingerprint: the neutral request whole (backend.neutral_request or embed_request), which holds
    nothing of the machine (threads, slots, context) and never the deadline."""
    from llm import backend
    return backend.request_hash(k)


def commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def _operation_id() -> str:
    """(f471) The operation a call is made inside, if any: the one place it is read. (f520) The calling thread's own (operation.current):
    a call made on another thread while the turn's operation is open is filed under none."""
    from engine import operation
    op = operation.current()
    return op.id if op is not None else ""


def _error(e: BaseException) -> dict:
    """(f527) A failed call's error as the row holds it: the interface's own kind and the detail (llm/errors.py); anything that is no
    Failure of the interface's is the server's, one failed try, with its type and text as the detail."""
    from llm import backend
    f = e if isinstance(e, Failure) else backend.failure_of(e)
    if f is not None:
        return {"kind": f.kind, "detail": str(f.detail or (f.legacy[1] if f.legacy else ""))[:500]}
    return {"kind": "server", "detail": f"{type(e).__name__}: {str(e)[:480]}"}


def _cancelled(e: BaseException | None = None, out=None) -> bool:
    """(f517) A call stopped on purpose, in any of the interface's three shapes: Cancelled, a Failure of kind cancelled, a reply whose
    finish is 'cancelled'."""
    from llm.errors import Cancelled, Failure
    if e is not None:
        return isinstance(e, Cancelled) or (isinstance(e, Failure) and e.kind == "cancelled")
    return getattr(out, "finish", None) == "cancelled"


def calls_file(folder) -> Path | None:
    """(f732) A recording's call log: calls.jsonl when it is there, else calls.jsonl.gz; None when it has neither."""
    return next((Path(folder) / n for n in CALLS if (Path(folder) / n).is_file()), None)


def is_calls(name) -> bool:
    """(f732) Whether a file's name, or a zip member's, is a recording's call log, in either form."""
    return str(name).replace("\\", "/").rsplit("/", 1)[-1] in CALLS


def call_lines(source, member: str = ""):
    """(f732) The lines of a recording's call log, as they are read: source a recording's folder, its log, or a zip with the log's
    member name. Lazy, so a log cut off mid-write gives the lines before the cut and then raises (EOFError, or zlib.error)."""
    if member:
        with zipfile.ZipFile(source) as z:
            raw, name = io.BytesIO(z.read(member)), member
    else:
        path = calls_file(source) if Path(source).is_dir() else Path(source)
        if path is None:
            raise FileNotFoundError(f"{source}: no call log ({' or '.join(CALLS)})")
        raw, name = path.open("rb"), path.name
    with raw, io.TextIOWrapper(gzip.GzipFile(fileobj=raw) if name.endswith(".gz") else raw, encoding="utf-8") as f:
        yield from f


def read_calls(source, member: str = "") -> list[dict]:
    """(f732) A recording's call rows, in order, whichever form its log has (call_lines)."""
    return [json.loads(line) for line in call_lines(source, member) if line.strip()]


def _calls_out(folder: Path):
    """(f732) The call log opened for writing, in the form its place keeps: plain under data/replay (a kept recording, and the folder a
    re-bless renames into place); anywhere else gzipped, with no time in its header, so the same rows give the same bytes."""
    return _log_writer(folder / CALLS[0 if folder.resolve().is_relative_to(Path(KEPT).resolve()) else 1])


def _log_writer(path: Path):
    """(f732) A call log opened for writing in the form its name says: plain, or gzipped with no time in its header."""
    if path.name.endswith(".gz"):
        return io.TextIOWrapper(gzip.GzipFile(path, "wb", mtime=0), encoding="utf-8", newline="\n")
    return path.open("w", encoding="utf-8", newline="\n")


CLOCK = ("seconds",)                     # (f732) a call row's wall-clock time: how long it took, no part of what the call was
MADE_AT = ("kv", "campaign", "created")  # (f732) the start save's clock time of making, as storage/statehash.py NOT_STATE sets it aside


def _content(db: Path):
    """(f732) A save database read whole: its version, its schema, every table's rows in their order, with the time it was made
    (MADE_AT) set aside. None when there is none."""
    if not db.is_file():
        return None
    table, key, field = MADE_AT
    con = sqlite3.connect(db.resolve().as_uri() + "?mode=ro&immutable=1", uri=True)   # (f732) no -wal or -shm left beside a recording
    try:
        out = [con.execute("PRAGMA user_version").fetchone()[0]]
        for kind, name, sql in con.execute("SELECT type, name, sql FROM sqlite_master ORDER BY type, name").fetchall():
            out.append((kind, name, sql))
            if kind != "table":
                continue
            try:
                rows, at = con.execute(f'SELECT rowid, * FROM "{name}" ORDER BY rowid').fetchall(), 1
            except sqlite3.OperationalError:                    # a table with no rowid: its rows, in an order of their own
                rows, at = sorted(con.execute(f'SELECT * FROM "{name}"').fetchall(), key=repr), 0
            if name == table:
                rows = [r[:at + 1] + (_without(r[at + 1], field),) + r[at + 2:] if r[at] == key else r for r in rows]
            out.append(rows)
    finally:
        con.close()
    return out


def _without(text, field: str):
    try:
        value = json.loads(text)
    except (TypeError, ValueError):
        return text
    return {k: v for k, v in value.items() if k != field} if isinstance(value, dict) else value


def keep_unchanged(kept: Path, made: Path) -> dict:
    """(f732) A recording made again (made) keeps the kept one's bytes wherever only the clock moved, so a re-bless that changes
    nothing leaves the files as they were and a real change is the only line that moves. A call row that is the kept row in its
    place in every field but its time (CLOCK) is written as the kept line, its time included; the start save, when its content is
    the kept one's but for the time it was made, is the kept file. Returns {"calls": rows written anew, "of": rows, "start": "kept",
    "new" or "none"}."""
    kept, made = Path(kept), Path(made)
    old = [l if l.endswith("\n") else l + "\n" for l in call_lines(kept) if l.strip()] if calls_file(kept) else []
    new = [l if l.endswith("\n") else l + "\n" for l in call_lines(made) if l.strip()]

    def timeless(line: str) -> dict:
        return {k: v for k, v in json.loads(line).items() if k not in CLOCK}
    same = [j < len(old) and timeless(old[j]) == timeless(line) for j, line in enumerate(new)]
    with _log_writer(calls_file(made)) as f:
        f.write("".join(old[j] if s else line for j, (s, line) in enumerate(zip(same, new))))
    start = "none"
    if (made / "start.db").is_file():
        start = "kept" if _content(kept / "start.db") == _content(made / "start.db") else "new"
        if start == "kept":
            shutil.copyfile(kept / "start.db", made / "start.db")
    return {"calls": same.count(False), "of": len(new), "start": start}


class Recorder:
    def __init__(self, store, name: str = "", folder: Path | None = None, rows: bool = False):
        from engine import streams
        from storage import statehash
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self.dir = Path(folder) if folder else FOLDER / (name or f"{store.meta.name}_{stamp}")
        if self.dir.exists():
            shutil.rmtree(self.dir)
        self.dir.mkdir(parents=True)
        self.store = store
        with store._lock:
            out = sqlite3.connect(self.dir / "start.db")
            try:
                store._db.backup(out)
            finally:
                out.close()
        streams.STRICT = True
        from core.version import VERSION
        from engine import budget
        from llm import embed
        from npc import life
        self.meta = {
            "made": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": store.meta.seed, "steps": store.meta.steps,
            "turn": store.meta.turn, **statehash.data_hashes(), "model": config.MODEL, "version": VERSION,     # (f718) "data" and "words"
            "commit": commit(), "start": statehash.digest(store), "embed": embed.available(), "backfill": life.FIRST_BATCH,
            "save": store.meta.name,
            "profile": dict(budget.PROFILE), "limit_seconds": budget.B.get("limit_seconds"),     # (f468) the speeds the budget priced calls at
            "budget_cached": bool(budget.CACHED)}                  # (f538) and whether a reused prompt was charged as reused
        if budget.SLOW:                                     # (f526) made below the minimum card: a replay lifts the same time limits
            self.meta["slow"] = True
        if getattr(config, "THINK_TASKS", None):            # (f533) the tasks that thought, and their room: a replay asks as they did
            self.meta.update(think_tasks=sorted(config.THINK_TASKS), think_room=config.THINK_ROOM)
        if getattr(config, "SAMPLING_ARM", ""):            # (f587) a measuring run's sampling arm: a replay samples as it did
            self.meta["sampling_arm"] = config.SAMPLING_ARM
        (self.dir / "meta.json").write_text(json.dumps(self.meta, indent=1), encoding="utf-8", newline="\n")
        self.inputs = (self.dir / "inputs.jsonl").open("w", encoding="utf-8", newline="\n")
        self.calls = _calls_out(self.dir)
        self.turns = (self.dir / "turns.jsonl").open("w", encoding="utf-8", newline="\n")
        self.n_input, self.n_call, self.shown, self.open_input, self.inside = 0, 0, [], False, False
        self.asking = None
        self.undo = []                       # what answered on the channel before this recorder, put back at close
        self.unwrap = None                   # (f517) the handle that takes the recorder's layer off the model interface
        self._lock = threading.Lock()        # (f517) the call's number, the calls on their way and each row written, together; never
        self.in_flight, self.overlapped, self.closed = 0, 0, False   # held across a call (a call may wait on another thread's)
        self.rows = rows                     # (f476) each input's turn row names the rows and keys it changed (a kept recording's re-bless)
        self.last_dump = statehash.dump(store) if rows else None
        prune()

    # ---- what the session depended on from outside the save
    def install(self, apart: bool = False) -> "Recorder":
        """Layer the model interface and wrap the console. apart (f442): the player's side is a program that reads the world through the scene
        while it decides its line (the night bot), and a read can write (the board refreshed when looked at): whatever it writes then is
        taken back, so the game alone changes the save, the same in the recording and in its replay. A person at the keyboard writes
        nothing while typing, so main.py leaves it off; holding the save closed while someone types would only stall the window."""
        from llm import backend
        from ui import console
        if self.unwrap is None:
            self.unwrap = backend.wrap(self._layer, rank=backend.RECORDER)       # (f517) a layer, no longer a patch on the client
        ch = console.channel()                   # (f635) the channel in use is the one recorded, and put back at close
        real_ask = ch.get("ask")

        def ask(*a, **k):
            main = bool(k.get("main", a[0] if a else False))
            if main:
                self._end_input()
            self.asking = threading.get_ident()
            try:
                text = self._apart(real_ask, a, k) if apart and main else real_ask(*a, **k)
            finally:
                self.asking = None
            self.inputs.write(json.dumps({"i": self.n_input + (1 if main else 0), "main": main, "text": text, "turn": self.store.meta.turn,
                                          "steps": self.store.meta.steps, "actor": actor.who()}, ensure_ascii=False) + "\n")   # (f629) whose line
            self.inputs.flush()
            if main:
                self.n_input += 1
                self.open_input = True
            return text

        self.undo.append((ch, "ask", real_ask))
        ch.set("ask", ask)
        for name in STORY:
            fn = ch.get(name)

            def told(*a, _fn=fn, **k):
                if self.inside:                          # one function passing its words to another (a ledger line shown as a note)
                    return _fn(*a, **k)
                self.shown.append(" ".join(str(x) for x in a) + "".join(f" {v}" for v in k.values()))
                self.inside = True
                try:
                    return _fn(*a, **k)
                finally:
                    self.inside = False
            self.undo.append((ch, name, fn))
            ch.set(name, told)
        return self

    def _apart(self, real_ask, a, k) -> str:
        """(f442) Ask, then take back whatever the asking wrote to the save. A new line is asked for between turns, outside any
        transaction, so this one is the outermost and its rollback undoes only what the asking did."""
        class Apart(Exception):
            pass
        got = {}
        try:
            with self.store.transaction():
                got["text"] = real_ask(*a, **k)
                raise Apart
        except Apart:
            pass
        return got["text"]

    def _layer(self, op: str, request, call):
        """(f517) The recorder's layer: one row per chat or embed this session makes, in the form it has always had (module docstring)."""
        if op not in ("chat", "embed") or self.closed:
            return call(request)                         # the model's warm-up is no call of the session's; a closed recorder records nothing
        if self.asking is not None and threading.get_ident() == self.asking:
            return call(request)                         # (f442) the player's side deciding its line: the input, not the game
        if threading.current_thread() in ORPHANS:
            return call(request)                         # (f453) a closed session's thread, still running: not this session's call
        t0 = time.perf_counter()
        from llm import backend, gateway
        with self._lock:
            i = self.n_call
            self.n_call += 1
            overlap = self.in_flight > 0                 # (R5) another recorded call is still on its way
            self.in_flight += 1
            self.overlapped += overlap
        try:
            k = backend.neutral_request(request) if op == "chat" else backend.embed_request(request)     # (f527) the neutral form
            row = {"i": i, "input": self.n_input, "kind": op, "title": k.get("schema", "") if op == "chat" else "",
                   "req": request_hash(k),
                   "task": getattr(gateway._TASK, "name", "") if op == "chat" else "",          # (f468) the task, for the budget's estimate (outside the hash)
                   "request": k}
            from engine import budget
            row["op"] = _operation_id()                                                         # (f471) the operation it was made inside, if any
            row["need"] = budget.need(row["task"]) if op == "chat" and row["task"] else ("embed" if op == "embed" else "")   # ...and whether the line needed it
            if op == "chat" and getattr(gateway._TASK, "shape", None):
                row["shape"] = dict(gateway._TASK.shape)                                         # (f475) the prompt's shape, outside the hash
            if overlap:
                row["overlap"] = True
            try:
                out = call(request)
            except Exception as e:
                if not _cancelled(e):                    # a cancel is no failure: no row
                    row.update(error=_error(e), seconds=round(time.perf_counter() - t0, 3))
                    self._write_call(row)
                raise
            if _cancelled(out=out):
                return out
            row["seconds"] = round(time.perf_counter() - t0, 3)
            if op == "embed":
                row["answer"] = {"embeddings": getattr(out, "vectors", None)}
            else:
                row["answer"] = (out.text or "")
                row["finish"] = out.finish if out.finish is not None else "stop"
                row["usage"] = dict(out.usage) if isinstance(out.usage, dict) else {}     # (f475, f527) the source's counts, the cached prompt tokens among them
            self._write_call(row)
            return out
        finally:
            with self._lock:
                self.in_flight -= 1

    def _write_call(self, row: dict) -> None:
        with self._lock:                                 # (f517) two calls finishing together never tear a line
            if self.closed:
                return                                   # a call still on its way when the session closed: its row goes nowhere
            self.calls.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
            self.calls.flush()

    def _end_input(self) -> None:
        """After an input: the state, what the turn recorded, and what was shown."""
        if not self.open_input:
            return
        from engine import ledger, operation
        from storage import statehash
        ops = [{"id": o["id"], "kind": o["kind"], "rows": o["rows"]}                                 # (f463) the operations the input committed
               for o in self.store.load_operations()["ops"] if o.get("steps") == self.store.meta.steps]
        presented = operation.take_presented()                                                      # (f467) what reached the page, and how
        row = {"i": self.n_input, "turn": self.store.meta.turn, "steps": self.store.meta.steps,
               "state": statehash.digest(self.store), "outcomes": ledger.last(), "operations": ops, "presented": presented,
               "shown": hashlib.sha256("\n".join(self.shown).encode("utf-8")).hexdigest(), "lines": len(self.shown),
               "shown_text": list(self.shown)}                       # (f459) the lines, for a re-bless to name the one that moved
        if self.rows:                                                # (f476) the rows and keys this input changed
            now = statehash.dump(self.store)
            row["rows"] = statehash.changes(self.last_dump, now)
            self.last_dump = now
        self.turns.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        self.turns.flush()
        self.shown, self.open_input = [], False

    def close(self) -> Path:
        self._end_input()
        if self.unwrap is not None:
            self.unwrap()                                # (f517) this recorder's layer, and only it, off the interface
            self.unwrap = None
        for ch, name, fn in reversed(self.undo):
            ch.set(name, fn)
        self.undo = []
        with self._lock:
            self.closed = True
            for f in (self.inputs, self.calls, self.turns):
                f.close()
        self.meta["overlapped"] = self.overlapped        # (R5) written at close, 0 when no recorded call overlapped another
        (self.dir / "meta.json").write_text(json.dumps(self.meta, indent=1), encoding="utf-8", newline="\n")
        from engine import streams
        streams.STRICT = False
        return self.dir


def prune(keep: int | None = None) -> None:
    """Only the newest recordings are kept (config.RECORD_KEEP); a recording kept on purpose lives under data/replay instead."""
    keep = getattr(config, "RECORD_KEEP", 5) if keep is None else keep
    if not FOLDER.exists():
        return
    made = sorted((d for d in FOLDER.iterdir() if (d / "meta.json").exists()), key=lambda d: (d / "meta.json").stat().st_mtime)
    for d in made[:-keep] if keep > 0 else made:
        shutil.rmtree(d, ignore_errors=True)
