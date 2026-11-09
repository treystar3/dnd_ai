"""(f529) The developer tools' model server: the game's own llama-server (llm/runtime.py), started and stopped by the tool as the game
starts and stops it, so a night or an evaluation measures what a player gets; or, with --attach, the running game's server (one game at
a time: a tool never starts a second server beside it, llm/runtime.py game_open).

    import runtime_cli
    runtime_cli.add_args(ap)                             # --attach
    server = runtime_cli.load(args, out=folder)          # started (its logs in `out`, its run files in out/run), the interface's source, ready
    ...
    server.report()                                      # what ran, for a run.json: the build, the device, the class, the model's sha
    server.close()                                       # this tool's own children stopped and the source taken away; the game's never

A tool under its stand-in (--stub) never calls this. DND_BACKEND=llama (a server started by hand, DND_LLAMA_URL) waits for that server
and stops nothing. Several runs at once (tools/nightrun.py
--parallel) are as many servers, each in its own process with its own run folder, so one run's close never reaches a sibling's."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from core import paths

FETCH_HINT = ("Fetch them first: python tools/fetch_runtime.py --models, and --build cuda (or vulkan, cpu; Linux CUDA adds --from-source). "
              "tools/HOSTED.md has the steps on a rented box.")


def add_args(ap) -> None:
    ap.add_argument("--attach", action="store_true", help="(f529) use the open game's own model server instead of starting one (run/server.json)")


class Server:
    """The server a tool runs on, however it came to be: close() undoes exactly what load() did."""

    def __init__(self, kind: str, rt=None, undo=None, src=None, run_dir: Path | None = None, own_run_dir: bool = False):
        self.kind, self.rt, self.undo, self.src, self.run_dir, self.own_run_dir = kind, rt, undo, src, run_dir, own_run_dir

    @property
    def source(self):
        """The source this server answers through: what a live tool gives its stand-in as `below`, so the titles it passes on reach the
        server and not the stub under them (llm/backend.py StandIn)."""
        if self.src is not None:
            return self.src
        from llm import backend
        return backend.source()

    def facts(self) -> dict:
        from llm import backend
        try:
            return backend.facts()
        except Exception as e:                                # (f524) facts asked before the load decided them: a report, not a crash
            return {"error": f"{type(e).__name__}: {e}"[:160]}

    def report(self) -> dict:
        """(f529) What this run's model ran on, for its run.json (tools/nightrun.py): the source, the build and device, the machine's class
        (llm/launch.py classify) and why, the layers on the card, the slot's context, the embedder and where it sits, the model's id and
        sha from data/runtime/server.yaml, and a warning for each thing that makes turns slower than the card profile says."""
        from llm import runtime
        f = self.facts()
        own = self.rt is not None                                   # the game's own server: its files checked against server.yaml
        cfg = self.rt.cfg if own else runtime.settings()
        chat = next((v for v in (cfg.get("models") or {}).values() if v.get("role") == "chat"), {})
        out = {"source": f.get("source"), "kind": self.kind, "build": f.get("build"), "device": f.get("device"), "class": f.get("class"),
               "class_why": f.get("class_why"), "offloaded": f.get("offloaded"), "slot_ctx": f.get("slot_ctx"), "slots": f.get("slots"),
               "embedder": f.get("embedder"), "embed_device": f.get("embed_device"), "embed_failure": f.get("embed_failure"),
               "model": config.MODEL, "model_sha": chat.get("sha256") if own else None,
               "llama_cpp": (cfg.get("llama_cpp") or {}).get("tag") if own else None,
               "threads": int(getattr(config, "NUM_THREAD", 0) or 0), "warnings": []}
        if not own:
            out["warnings"].append(f"a server this tool did not start ({self.kind}): its model and build were not checked against "
                                   "data/runtime/server.yaml")
        if f.get("error"):
            out["warnings"].append(f["error"])
        if f.get("class") and f["class"] != "minimum":
            out["warnings"].append(f"the machine is below the minimum card ({f.get('class_why') or 'no reason given'}): turns run slower "
                                   "than the card profile says")
        if f.get("embedder") is False and f.get("embed_failure"):
            out["warnings"].append(f"no embedder this session: {f['embed_failure']}")
        return out

    def close(self) -> None:
        if self.undo is not None:
            self.undo()
            self.undo = None
        if self.rt is not None:
            self.rt.close()                               # this tool's own children, never another process's (llm/runtime.py close)
            self.rt = None
        elif self.kind == "attached" and self.src is not None:
            self.src.close()                              # (f523) nothing of this tool's waits for the game's card any more
        if self.own_run_dir and self.run_dir is not None:
            shutil.rmtree(self.run_dir, ignore_errors=True)


def load(args=None, *, attach: bool | None = None, out: Path | str | None = None, run_dir: Path | str | None = None,
         logs: Path | str | None = None, adapters=None, say=print, progress=None) -> Server:
    """The model server for this tool, ready: started from runtime/ and models/ as the game starts its own (the files checked first), or
    the open game's with --attach. Its logs go to `logs` (default: `out`, else logs/), its run files to `run_dir` (default: out/run, else
    a folder of this process's own under run/, removed at close). Refused in plain words when the game is open and --attach was not
    given, or when the files are not in place. `adapters`: LoRA adapters (GGUF) loaded as voices by their stems (tools/lora_eval.py)."""
    from llm import backend
    kind = str(getattr(config, "BACKEND", "runtime") or "runtime")
    attach = bool(getattr(args, "attach", False)) if attach is None else attach
    if adapters and (kind != "runtime" or attach):
        raise SystemExit("adapters load only on a server this tool starts itself: drop DND_BACKEND and --attach")
    if kind == "llama":                                   # (f521) a server started by hand: wait for it, start nothing
        backend.load(progress)
        say(f"model server: the llama-server at {os.environ.get('DND_LLAMA_URL', 'DND_LLAMA_URL')} (started by hand)")
        return Server("llama", src=backend.source())
    from llm import runtime
    if attach:
        src = runtime.attach()                            # Failure("unreachable") in plain words when no game's server.json is there
        undo = backend.use(src)
        try:
            src.load(progress)
        except BaseException:
            undo()
            raise
        say(f"model server: the open game's, on port {src.chat_server.port}" + (" with its embedder" if src.embed_server else ""))
        return Server("attached", undo=undo, src=src)
    if runtime.game_open():
        raise SystemExit("The game is open, and its model server with it: run this tool with --attach to use that server, or close the game first.")
    problems = runtime.runtime_problems(check_files=True)
    if problems:
        raise SystemExit("The model server's files are not in place:\n" + "\n".join(f"  - {p}" for p in problems) + "\n" + FETCH_HINT)
    own = run_dir is None and out is None
    run_dir = Path(run_dir) if run_dir is not None else (Path(out) / "run" if out is not None else Path(paths.APP) / "run" / f"tool_{os.getpid()}")
    logs = Path(logs) if logs is not None else (Path(out) if out is not None else Path(paths.APP) / "logs")
    rt = runtime.Runtime(run_dir=run_dir, logs=logs, adapters=adapters)
    managed = runtime.Managed(rt)
    undo = backend.use(managed)
    try:
        rt.load(progress)
    except BaseException:
        undo()
        rt.close()
        if own:
            shutil.rmtree(run_dir, ignore_errors=True)
        raise
    f = rt.facts()
    say(f"model server: llama-server ({f.get('build')}) on {f.get('device') or 'the processor'}, class {f.get('class')}"
        + (f" ({f.get('class_why')})" if f.get("class_why") else "") + f", {f.get('slot_ctx')} tokens a slot, embedder "
        + (f"on the {f.get('embed_device')}" if f.get("embedder") else "off") + (f"; {len(rt.adapters)} adapter(s)" if rt.adapters else ""))
    return Server("runtime", rt=rt, undo=undo, src=managed, run_dir=run_dir, own_run_dir=own)
