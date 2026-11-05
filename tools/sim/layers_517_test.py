"""(f517) The recorder, the night's counter and the window's busy light are layers of the game's own model interface, and a recording
whose calls overlapped is refused.

- The three layers, put on in every order and taken off in every order, leave none behind, and nest by rank (the recorder outermost).
- A recorded row is byte for byte the row the client patch wrote: the three kept recordings, made again in their own processes, give
  the same rows (their time aside), turns and inputs; the old client's own answer fields (done_reason, the raw token counts, the cached
  prompt tokens) and its errors are kept as they were; a cancelled call writes no row.
- The player's side deciding its line, and a closed session's thread, pass unrecorded, and are never counted as an overlap.
- Two recorded calls on their way at once: the second is marked, meta.json counts it, and tools/rerun.py refuses the recording; once
  both are done, the next call is not marked. A recorder closed while a call is on its way writes nothing after it.
- The busy light lights for a foreground chat and for the model's warm-up, never for an embedding or a background call.
- The night's counter counts the game's chats and embeds, `main` still meaning the main thread, and never the warm-up.

Run: python tools/sim/layers_517_test.py"""

import gzip
import itertools
import json
import os
import shutil
import subprocess
import sys
import threading
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
os.chdir(ROOT)
import simlib
stub = simlib.Stub("warrior", 17)
simlib.install(stub)
simlib.quiet_console()

from pydantic import create_model

import config
from engine import recording
from llm import backend, gateway
from llm.errors import Cancelled, Failure
from llm.sampling import Sampling
from storage.campaign import CampaignStore
from ui import console

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


BASE = Path("saves/layers_517")
shutil.rmtree(BASE, ignore_errors=True)
BASE.mkdir(parents=True)
config.LOG_PATH = str(BASE / "llm_calls.jsonl")
Read = create_model("Read", x=(str, ""))


def chat(title="Read", messages=None):
    return backend.chat(messages or [{"role": "user", "content": title}], create_model(title, x=(str, "")), Sampling(0.5), 50)


def rows(folder) -> list:
    with gzip.open(Path(folder) / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


shutil.rmtree("saves/layers_517_store", ignore_errors=True)
store = CampaignStore.open_or_create("layers_517_store")
n_rec = itertools.count()


def recorder():
    return recording.Recorder(store, folder=BASE / f"rec{next(n_rec)}")


def night_dir(name):
    d = BASE / name
    d.mkdir(parents=True, exist_ok=True)
    return d


# ---- 1. the three layers in every order, on and off
from ui.gui.bridge import Bridge
import nightrun
import rerun
CONSOLE = {k: getattr(console, k) for k in dir(console) if not k.startswith("__")}
client0 = gateway._client.chat
orders_ok, nest_ok, combos = True, True, 0
for on in itertools.permutations(("recorder", "counter", "busy")):
    for off in itertools.permutations(("recorder", "counter", "busy")):
        combos += 1
        rec, bridge, run = recorder(), Bridge(), nightrun.Run(night_dir("night"), 1, 1, live=False)
        put = {"recorder": lambda: rec.install(), "counter": lambda: run.install_client(), "busy": lambda: bridge.install()}
        take = {"recorder": rec.close, "counter": lambda: run.unwrap(), "busy": bridge.uninstall}
        for name in on:
            put[name]()
        got = backend.layers()
        nest_ok &= got == [rec._layer, got[1], bridge.busy_layer] and len(got) == 3
        for name in off:
            take[name]()
        orders_ok &= backend.layers() == [] and gateway._client.chat is client0
        for k, v in CONSOLE.items():
            setattr(console, k, v)                       # the console's own bindings are still put back by setattr (not this test's)
        sys.stdout = sys.__stdout__
check(f"the three layers put on in every order and taken off in every order leave none, the client untouched ({combos} orders)",
      orders_ok and combos == 36)
check("...and while all three are on they nest by rank: the recorder outermost, then the night's counter, then the busy light", nest_ok)

# ---- 2. the row form: the three kept recordings, made again in their own processes
CHILD = r'''
import gzip, json, os, shutil, sys
from pathlib import Path
ROOT = Path(sys.argv[1]); name = sys.argv[2]; W = Path(sys.argv[3]).resolve()
os.chdir(ROOT); sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tools"))
import nightrun, rerun, config
W.mkdir(parents=True, exist_ok=True)
for attr, fn in (("LOG_PATH", "llm_calls.jsonl"), ("TURN_LOG_PATH", "turns_log.jsonl"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                 ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl"), ("CRASH_LOG_PATH", "crash.log")):
    setattr(config, attr, str(W / fn))
config.AUDIT_LOG = config.REFUSALS_LOG = False
import storage.campaign as sc
sc.SAVES_DIR = W / "saves"
from engine import recording
recording.FOLDER = W / "recordings"
rerun.ROOT = W
folder = W / "rec"
shutil.rmtree(folder, ignore_errors=True)
if name == "stub_short":
    rerun.make_stub_recording(folder, 40)
else:
    import importlib.util
    spec = importlib.util.spec_from_file_location("script_" + name, ROOT / "data/replay/scripts" / (name + ".py"))
    script = importlib.util.module_from_spec(spec); spec.loader.exec_module(script)
    script.record(folder, W)
lines = lambda p: [l for l in gzip.open(p, "rt", encoding="utf-8") if l.strip()]
def masked(l):
    r = json.loads(l); r.pop("seconds", None)
    return json.dumps(r, ensure_ascii=False, default=str)
kept = ROOT / "data/replay/sessions" / name
old, new = lines(kept / "calls.jsonl.gz"), lines(folder / "calls.jsonl.gz")
differ = [i for i, (a, b) in enumerate(zip(old, new)) if masked(a) != masked(b)]
turns = lambda p: (p / "turns.jsonl").read_text(encoding="utf-8")
om, nm = json.loads((kept / "meta.json").read_text()), json.loads((folder / "meta.json").read_text())
print(json.dumps({"rows": [len(old), len(new)], "differ": differ[:10], "turns": turns(kept) == turns(folder),
                  "inputs": (kept / "inputs.jsonl").read_text(encoding="utf-8") == (folder / "inputs.jsonl").read_text(encoding="utf-8"),
                  "meta_keys": list(nm) == list(om) + ["overlapped"], "overlapped": nm.get("overlapped"),
                  "meta_moved": [k for k in om if om[k] != nm.get(k) and k not in ("made", "commit", "save")]}))
'''
env = dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONHASHSEED="1")
for name in ("stub_short", "stub_party", "stub_fight"):
    r = subprocess.run([sys.executable, "-c", CHILD, str(ROOT), name, str(BASE / f"re_{name}")], cwd=ROOT, env=env, capture_output=True,
                       text=True, timeout=900)
    try:
        got = json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        got = {"error": (r.stdout + r.stderr)[-800:]}
    check(f"{name}, recorded again through the layer, is the kept recording row for row (time aside), turn for turn and input for input",
          got.get("rows", [0, 1])[0] == got.get("rows", [0, 1])[1] and got.get("differ") == [] and got.get("turns") and got.get("inputs"), got)
    check(f"...its meta the same keys and values, with overlapped 0 at the end", got.get("meta_keys") and got.get("overlapped") == 0
          and got.get("meta_moved") == [], got)

# ---- 3. the old client's own answer fields and errors, through the layer, as the client patch wrote them
real_client = gateway._client
gateway.keep_extra_fields()


class Answer:
    def __init__(self, **extra):
        self.message = types.SimpleNamespace(content='{"x": "ok"}')
        self.__dict__.update(extra)


def one_row(chat_fn, title="Read"):
    gateway._client = types.SimpleNamespace(chat=chat_fn)
    rec = recorder().install()
    try:
        try:
            chat(title)
        except BaseException as e:
            pass
    finally:
        rec.close()
        gateway._client = real_client
    rs = rows(rec.dir)
    return rs, json.loads((rec.dir / "meta.json").read_text())


rs, _ = one_row(lambda **k: Answer(done_reason=None, prompt_eval_count=812, eval_count=40, prompt_eval_duration=123456789,
                                   eval_duration=9876543, model_extra={"prompt_cache_tokens": 300}))
check("an answer's raw counts are kept as the client gave them: durations in nanoseconds, the cached prompt tokens, done_reason None",
      len(rs) == 1 and rs[0]["done"] is None and rs[0]["tokens"] == {"prompt_eval_count": 812, "eval_count": 40,
                                                                     "prompt_eval_duration": 123456789, "eval_duration": 9876543,
                                                                     "cached": 300} and rs[0]["answer"] == '{"x": "ok"}', rs)
rs, _ = one_row(lambda **k: Answer())
check("...and an answer with no done_reason at all recorded as 'stop', with no counts", len(rs) == 1 and rs[0]["done"] == "stop"
      and rs[0]["tokens"] == {}, rs)
check("...its row in the order it always had", list(rs[0]) == ["i", "input", "kind", "title", "req", "task", "request", "op", "need",
                                                              "seconds", "answer", "done", "tokens"], list(rs[0]))
k = backend.ollama_kwargs(backend.ChatRequest(messages=[{"role": "user", "content": "Read"}], schema=Read, sampling=Sampling(0.5), max_tokens=50))
check("...its request the arguments the client was sent (the format aside) and its fingerprint theirs",
      rs[0]["request"] == json.loads(json.dumps({x: v for x, v in k.items() if x != "format"})) and rs[0]["req"] == recording.request_hash(k))


def down(**k):
    raise ConnectionError("the model server cannot be reached")


rs, _ = one_row(down)
check("a failed call's row keeps the old client's error, not the neutral kind it was read as",
      len(rs) == 1 and rs[0]["error"] == ["ConnectionError", "the model server cannot be reached"] and list(rs[0])[-2:] == ["error", "seconds"], rs)
import httpx
rs, _ = one_row(lambda **k: (_ for _ in ()).throw(httpx.ReadTimeout("the deadline cut it")))
check("...a timeout too", len(rs) == 1 and rs[0]["error"] == ["ReadTimeout", "the deadline cut it"], rs)


class Shape:
    name = "shape"

    def __init__(self, how):
        self.how = how

    def chat(self, req, deadline=None):
        if self.how == "failure":
            raise Failure("cancelled", "closing")
        if self.how == "raised":
            raise Cancelled("closing")
        return backend.Reply(text="", finish="cancelled")


for how in ("failure", "raised", "finish"):
    rec = recorder().install()
    undo = backend.use(Shape(how))
    try:
        try:
            chat()
        except Cancelled:
            pass
        undo()
        chat()
    finally:
        rec.close()
    rs = rows(rec.dir)
    check(f"a cancelled call ({how}) writes no row: the next call's row follows with its number, a gap the replayer accepts",
          [r["i"] for r in rs] == [1] and rerun.refusal(json.loads((rec.dir / "meta.json").read_text()), rs) == "", rs)

from llm import embed as _embed
real_embed_client = _embed._client
_embed._client = lambda: types.SimpleNamespace(embed=lambda **k: {"embeddings": [[1.0, 0.0] for _ in k["input"]]})
rec = recorder().install()
try:
    backend.embed(["clustering: a gate", "clustering: a road"])
finally:
    rec.close()
    _embed._client = real_embed_client
rs = rows(rec.dir)
check("an embedding's row: the arguments the embedder sent, its fingerprint, the vectors, in the order it always had",
      len(rs) == 1 and rs[0]["request"] == {"model": config.EMBED_MODEL, "input": ["clustering: a gate", "clustering: a road"],
                                            "keep_alive": config.KEEP_ALIVE}
      and rs[0]["answer"] == {"embeddings": [[1.0, 0.0], [1.0, 0.0]]} and rs[0]["need"] == "embed" and rs[0]["title"] == ""
      and list(rs[0]) == ["i", "input", "kind", "title", "req", "task", "request", "op", "need", "seconds", "answer"], rs)

# ---- 4. the player's side and a closed session's thread pass unrecorded, and never count as an overlap; two recorded calls do


class Gate:
    """A source whose calls of a title wait until let go, so two calls can be made to be on their way at once."""
    name = "gate"

    def __init__(self):
        self.started, self.go = threading.Event(), threading.Event()

    def chat(self, req, deadline=None):
        title = req.schema.model_json_schema().get("title")
        if title == "Slow":
            self.started.set()
            self.go.wait(10)
        if title == "Boom":
            raise RuntimeError("the call fell over")
        return backend.Reply(text='{"x": "ok"}')


def background(title="Slow"):
    t = threading.Thread(target=lambda: chat(title))
    t.start()
    return t


real_ask = console.ask


def ask(*a, **k):
    chat("PlayerLine")                                   # the player's side deciding its line, while the people are written
    return "I look around."


console.ask = ask                                        # the recorder wraps the console's ask, which marks the asking thread
gate = Gate()
undo = backend.use(gate)
rec = recorder().install()
t = background()
gate.started.wait(5)
console.ask(main=True)
orphan_thread = threading.Thread(target=lambda: chat("Orphaned"))
recording.orphan([orphan_thread])
orphan_thread.start()
orphan_thread.join(5)
gate.go.set()
t.join(5)
chat("After")
rec.close()
undo()
console.ask = real_ask
rs = rows(rec.dir)
meta = json.loads((rec.dir / "meta.json").read_text())
titles = [r["title"] for r in rs]
check("the player's side deciding its line, and a closed session's thread, pass unrecorded while a recorded call is on its way",
      "PlayerLine" not in titles and "Orphaned" not in titles and titles == ["Slow", "After"], titles)
check("...and neither is an overlap: nothing marked, meta.json counts 0, the replayer takes it", not any(r.get("overlap") for r in rs)
      and meta.get("overlapped") == 0 and rerun.refusal(meta, rs) == "", (meta.get("overlapped"), rs))
recording.ORPHANS.discard(orphan_thread)

gate = Gate()
undo = backend.use(gate)
rec = recorder().install()
t = background()
gate.started.wait(5)
chat("Second")
try:
    chat("Boom")
except Exception:
    pass
gate.go.set()
t.join(5)
chat("Later")
rec.close()
undo()
rs = rows(rec.dir)
meta = json.loads((rec.dir / "meta.json").read_text())
marked = [r["title"] for r in rs if r.get("overlap")]
check("two recorded calls on their way at once: the second is marked, and one that failed meanwhile too, keeping its error",
      sorted(marked) == ["Boom", "Second"] and next(r for r in rs if r["title"] == "Boom")["error"] == ["RuntimeError", "the call fell over"], rs)
check("...meta.json counts them", meta.get("overlapped") == 2, meta.get("overlapped"))
check("...once both are done the next call is not marked", next(r for r in rs if r["title"] == "Later").get("overlap") is None)
try:
    rerun.load(rec.dir)
    refused = ""
except rerun.Unreplayable as e:
    refused = str(e)
check("...and the replayer refuses the recording, saying why", "overlapped" in refused, refused)
check("...as it refuses one whose calls are out of their order", "out of their order" in rerun.refusal({}, [{"i": 0}, {"i": 2}, {"i": 1}]))
check("...while a recording made before f517 (no overlapped key, as the kept ones) or by hand ({seed: 1}) is taken",
      rerun.refusal({"seed": 1}, [{"i": 0}]) == "" and rerun.refusal({}, [{"i": 0}, {"i": 1}]) == "")

gate = Gate()
undo = backend.use(gate)
rec = recorder().install()
t = background()
gate.started.wait(5)
rec.close()
gate.go.set()
t.join(5)
undo()
check("a recorder closed while a call is on its way writes nothing after it: the call ends, the file stays whole and holds no row for it",
      not t.is_alive() and rows(rec.dir) == [] and json.loads((rec.dir / "meta.json").read_text()).get("overlapped") == 0)

# ---- 5. the busy light
events = []
bridge = Bridge()
bridge.busy = lambda on: events.append(on)
bridge.install()
undo = backend.use(Gate())
chat("Foreground")
lit_chat = list(events)
events.clear()
_embed._client = lambda: types.SimpleNamespace(embed=lambda **k: {"embeddings": [[1.0] for _ in k["input"]]})
undo()
backend.embed(["clustering: a gate"])
lit_embed = list(events)
undo = backend.use(Gate())
events.clear()
with backend.lane("background"):
    chat("Background")
lit_background = list(events)
events.clear()
backend.loading(lambda: None)
lit_load = list(events)
undo()
bridge.uninstall()
_embed._client = real_embed_client
for k, v in CONSOLE.items():
    setattr(console, k, v)
sys.stdout = sys.__stdout__
check("the busy light lights for a foreground chat, on then off", lit_chat == [True, False], lit_chat)
check("...never for an embedding", lit_embed == [], lit_embed)
check("...never for a call in the background lane (the lanes f523 names)", lit_background == [], lit_background)
check("...and for the model's warm-up at the home page, as when it patched the client", lit_load == [True, False], lit_load)
check("...and the warm-up goes through the layers: gateway.warm's call is the loading one", "backend.loading(" in
      (ROOT / "llm/gateway.py").read_text(encoding="utf-8"))

# ---- 6. the night's counter
run = nightrun.Run(night_dir("night2"), 1, 1, live=False)
handle = run.install_client()
undo = backend.use(Gate())
chat("Counted")
other = threading.Thread(target=lambda: chat("Elsewhere"))
other.start()
other.join(5)
backend.loading(lambda: None)
undo()
_embed._client = lambda: types.SimpleNamespace(embed=lambda **k: {"embeddings": [[1.0] for _ in k["input"]]})
backend.embed(["clustering: a", "clustering: b"])
_embed._client = real_embed_client
handle()
calls = [(c["kind"], c["schema"], c["main"]) for c in run.calls]
check("the night's counter counts the game's chats and embeds, `main` still the main thread, and never the warm-up",
      calls == [("chat", "Counted", True), ("chat", "Elsewhere", False), ("embed", "", True)] and run.calls[-1]["texts"] == 2, run.calls)
check("...and its handle takes it off", backend.layers() == [], backend.layers())

store.close()
shutil.rmtree("saves/layers_517_store", ignore_errors=True)
shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
