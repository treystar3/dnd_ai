"""(f440) A recording of a play session that the real turn can replay (tools/rerun.py): the rebuild's Stage 1.

Every later stage of the rebuild is checked against what the game did before it. A recording keeps everything a session depended on
from outside the save, so the same session can be played again through the same code (or through the code a stage has changed) and
compared input by input:

  recordings/<name>/start.db       the save as the session opened (an sqlite backup, taken before anything is played)
  recordings/<name>/meta.json      the seed, the data hash (storage/statehash.py), the model, the version and commit, the start state
  recordings/<name>/inputs.jsonl   every line the player gave, a question's answer mid-turn and a pane's command included
  recordings/<name>/calls.jsonl.gz every call to the model, in order: the request in full, the answer or the failure, its time
  recordings/<name>/turns.jsonl    after each input: the state's fingerprint, what the turn recorded, and what the player was shown

It wraps the model client and the console in place, the way the night runs do (tools/nightrun.py install_client), so whatever is
installed (the terminal, the window, a test, a night run) is recorded as it is. A recording session is strict (engine/streams.py
STRICT): the background people and the embedding model's arrival are fixed at an input's edge, so the session can replay exactly.
Only RECORD_KEEP recordings are kept; the oldest go first."""
from __future__ import annotations

import gzip
import hashlib
import json
import shutil
import sqlite3
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "recordings"
STORY = ("narrate", "say", "npc_says", "dialogue", "note", "wait", "ledger")   # what the player reads (engine/turnlog.py), and the engine's facts


def request_hash(k: dict) -> str:
    """What a call asked for, as one fingerprint: the conversation, the answer's shape and the sampling. The threads setting is the
    machine's, not the game's, and is left out."""
    opts = {o: v for o, v in (k.get("options") or {}).items() if o != "num_thread"}
    fmt = k.get("format") or {}
    body = {"model": k.get("model"), "messages": k.get("messages"), "format": fmt.get("title", "") if isinstance(fmt, dict) else str(fmt),
            "schema": hashlib.sha256(json.dumps(fmt, sort_keys=True, default=str).encode()).hexdigest()[:16], "options": opts,
            "input": k.get("input")}
    return hashlib.sha256(json.dumps(body, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")).hexdigest()


def commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


class Recorder:
    def __init__(self, store, name: str = "", folder: Path | None = None):
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
        from llm import embed
        from npc import life
        (self.dir / "meta.json").write_text(json.dumps({
            "made": datetime.now(timezone.utc).isoformat(timespec="seconds"), "seed": store.meta.seed, "steps": store.meta.steps,
            "turn": store.meta.turn, "data": statehash.data_hash(), "model": config.MODEL, "version": VERSION,
            "commit": commit(), "start": statehash.digest(store), "embed": embed.available(), "backfill": life.FIRST_BATCH,
            "save": store.meta.name}, indent=1), encoding="utf-8")
        self.inputs = (self.dir / "inputs.jsonl").open("w", encoding="utf-8")
        self.calls = gzip.open(self.dir / "calls.jsonl.gz", "wt", encoding="utf-8")
        self.turns = (self.dir / "turns.jsonl").open("w", encoding="utf-8")
        self.n_input, self.n_call, self.shown, self.open_input, self.inside = 0, 0, [], False, False
        self.undo = []
        prune()

    # ---- what the session depended on from outside the save
    def install(self) -> "Recorder":
        from llm import gateway
        from ui import console
        client = gateway._client
        real_chat, real_embed = client.chat, getattr(client, "embed", None)

        def chat(**k):
            return self._call("chat", real_chat, k)

        def embed(**k):
            return self._call("embed", real_embed, k)

        self.undo.append((client, "chat", real_chat))
        client.chat = chat
        if real_embed is not None:
            self.undo.append((client, "embed", real_embed))
            client.embed = embed
        real_ask = console.ask

        def ask(*a, **k):
            main = bool(k.get("main", a[0] if a else False))
            if main:
                self._end_input()
            text = real_ask(*a, **k)
            self.inputs.write(json.dumps({"i": self.n_input + (1 if main else 0), "main": main, "text": text, "turn": self.store.meta.turn,
                                          "steps": self.store.meta.steps}, ensure_ascii=False) + "\n")
            self.inputs.flush()
            if main:
                self.n_input += 1
                self.open_input = True
            return text

        self.undo.append((console, "ask", real_ask))
        console.ask = ask
        for name in STORY:
            fn = getattr(console, name, None)
            if fn is None:
                continue

            def told(*a, _fn=fn, **k):
                if self.inside:                          # one function passing its words to another (a ledger line shown as a note)
                    return _fn(*a, **k)
                self.shown.append(" ".join(str(x) for x in a) + "".join(f" {v}" for v in k.values()))
                self.inside = True
                try:
                    return _fn(*a, **k)
                finally:
                    self.inside = False
            self.undo.append((console, name, fn))
            setattr(console, name, told)
        return self

    def _call(self, kind: str, real, k: dict):
        t0 = time.perf_counter()
        row = {"i": self.n_call, "input": self.n_input, "kind": kind, "title": ((k.get("format") or {}).get("title", "")
               if isinstance(k.get("format"), dict) else ""), "req": request_hash(k),
               "request": {key: v for key, v in k.items() if key != "format"}}
        self.n_call += 1
        try:
            out = real(**k)
        except Exception as e:
            row.update(error=[type(e).__name__, str(e)[:500]], seconds=round(time.perf_counter() - t0, 3))
            self._write_call(row)
            raise
        row["seconds"] = round(time.perf_counter() - t0, 3)
        if kind == "embed":
            row["answer"] = {"embeddings": getattr(out, "embeddings", None) or (out.get("embeddings") if isinstance(out, dict) else None)}
        else:
            row["answer"] = (out.message.content or "")
            row["done"] = getattr(out, "done_reason", "stop")
            row["tokens"] = {t: getattr(out, t, None) for t in ("prompt_eval_count", "eval_count", "prompt_eval_duration", "eval_duration",
                                                                 "load_duration", "total_duration") if getattr(out, t, None) is not None}
        self._write_call(row)
        return out

    def _write_call(self, row: dict) -> None:
        self.calls.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        self.calls.flush()

    def _end_input(self) -> None:
        """After an input: the state, what the turn recorded, and what was shown."""
        if not self.open_input:
            return
        from engine import ledger
        from storage import statehash
        self.turns.write(json.dumps({"i": self.n_input, "turn": self.store.meta.turn, "steps": self.store.meta.steps,
                                     "state": statehash.digest(self.store), "outcomes": ledger.LAST,
                                     "shown": hashlib.sha256("\n".join(self.shown).encode("utf-8")).hexdigest(), "lines": len(self.shown)},
                                    ensure_ascii=False, default=str) + "\n")
        self.turns.flush()
        self.shown, self.open_input = [], False

    def close(self) -> Path:
        self._end_input()
        for obj, name, fn in reversed(self.undo):
            setattr(obj, name, fn)
        self.undo = []
        for f in (self.inputs, self.calls, self.turns):
            f.close()
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
