"""(f528) A fake of the game's runtime folder for the tests: runtime/<build>/llama-server launchers that list the devices FAKE_LIST_<build>
names and then serve a fake llama-server (tools/sim/fake_llama.py) answering every contract by its title with the stand-in model
(simlib.Stub; the title is read from the grammar's first line, as llm/llama.py grammar_of writes it) and every embedding with
simlib.FakeEmbedder; the model files as placeholders; and the environment that points core.paths at it (MERAVIA_RUNTIME,
MERAVIA_MODELS) for a child process, or the patch that points this process's core.paths at it.

    from fake_runtime import Layout, THE_3060
    lay = Layout(base)                            # writes runtime/{cuda,vulkan,cpu}/llama-server and models/*.gguf under base
    env = lay.env(cuda=[THE_3060])                # os.environ for a child: the layout, the devices, no MERAVIA_NO_SERVER
    lay.patch_paths()                             # this process: core.paths RUN/RUNTIME/MODELS/APP at the layout, the env for its children
    lay.restore()                                 # ...and back
    lay.bodies()                                  # every body the fakes were sent, with its path (FAKE_BODIES); lay.argv() every launch

The launchers also read FAKE_LOAD_SECONDS (the load's length), FAKE_LOAD_UNTIL (a file the chat server's load waits for), FAKE_GRANTED (the context the server grants a slot), FAKE_OFFLOAD (the
layers on the card, 49/49), FAKE_FAIL_FILE (a file whose presence makes the next chat server fail to load, once), FAKE_DELAY (seconds
before each answer) and FAKE_SEED (the stand-in's seed), as the f522 and f526 tests' launchers do."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SIM = ROOT / "tools" / "sim"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

THE_3060 = "  CUDA0: NVIDIA GeForce RTX 3060 (12287 MiB, 11200 MiB free)"

LAUNCHER = """#!{py}
import os, sys, time, json, threading
sys.path.insert(0, {root!r})
sys.path.insert(0, {sim!r})
args = sys.argv[1:]
build = os.path.basename(os.path.dirname(os.path.abspath(sys.argv[0])))
if os.environ.get("FAKE_ARGV"):
    with open(os.environ["FAKE_ARGV"], "a") as f:
        f.write(json.dumps([build] + args) + "\\n")
if "--list-devices" in args:
    print("Available devices:")
    for l in json.loads(os.environ.get("FAKE_LIST_" + build, "[]")):
        print(l)
    sys.exit(0)
port, key = int(args[args.index("--port") + 1]), args[args.index("--api-key") + 1]
fail = os.environ.get("FAKE_FAIL_FILE", "")
if fail and os.path.exists(fail) and "--embeddings" not in args:
    os.remove(fail)
    print("error: failed to load the model", flush=True); sys.exit(3)
ctx = int(args[args.index("-c") + 1]) // int(args[args.index("-np") + 1]) if "-np" in args else 2048
granted = int(os.environ.get("FAKE_GRANTED", "0") or 0) or ctx
from fake_llama import FakeLlama
import simlib
from llm import contracts
stub = simlib.Stub("warrior", int(os.environ.get("FAKE_SEED", "1") or 1))
emb = simlib.FakeEmbedder()
lock = threading.Lock()
bodies = os.environ.get("FAKE_BODIES", "")
delay = float(os.environ.get("FAKE_DELAY", "0") or 0)

def title_of(body):
    first = (body.get("grammar") or "").split("\\n", 1)[0].split()
    return first[2] if len(first) >= 3 and first[1] == "Meravia" else ""

def script(path, body, n):
    if bodies:
        with lock, open(bodies, "a") as f:
            f.write(json.dumps({{"path": path, **body}}) + "\\n")
    if path == "/v1/embeddings":
        return {{"vectors": [emb.vec(t) for t in body.get("input") or []], "delay": delay}}
    t = title_of(body)
    cls = getattr(contracts, t, None)
    fmt = cls.model_json_schema() if cls is not None else {{"title": t}}
    with lock:
        r = stub.chat(messages=body.get("messages") or [], format=fmt, options={{}})
    return {{"content": r.message.content, "delay": delay}}

try:
    fake = FakeLlama(key=key, slot_ctx=granted, port=port, loading=10 ** 9, script=script)
except OSError:
    print("main: couldn't bind HTTP server socket", flush=True); sys.exit(1)
until = os.environ.get("FAKE_LOAD_UNTIL", "")
while until and "--embeddings" not in args and not os.path.exists(until):   # the chat server's load waits for the test's go-ahead
    time.sleep(0.05)
time.sleep(float(os.environ.get("FAKE_LOAD_SECONDS", "0.2") or 0))
if "--embeddings" not in args and "-lv" in args and int(args[args.index("-lv") + 1]) >= 4:
    print("load_tensors: offloaded " + os.environ.get("FAKE_OFFLOAD", "49/49") + " layers to GPU", flush=True)
print("0.04.015 I srv    load_model: initializing, n_slots = 2, n_ctx_slot = " + str(granted), flush=True)
fake.loading = 0
print("0.04.120 I srv  server_run_i: model loaded", flush=True)
while True:
    time.sleep(1)
"""


class Layout:
    def __init__(self, base: Path | str, cfg: dict | None = None):
        from llm import runtime
        self.base = Path(base)
        self.cfg = runtime.settings() if cfg is None else cfg
        self.rt_dir, self.models_dir = self.base / "runtime", self.base / "models"
        self.run_dir, self.app = self.base / "run", self.base / "app"
        self.argv_log, self.bodies_log = self.base / "argv.jsonl", self.base / "bodies.jsonl"
        for b in ("cuda", "vulkan", "cpu"):
            (self.rt_dir / b).mkdir(parents=True, exist_ok=True)
            exe = self.rt_dir / b / runtime.exe_name()
            exe.write_text(LAUNCHER.format(py=sys.executable, root=str(ROOT), sim=str(SIM)), encoding="utf-8")
            exe.chmod(0o755)
        self.models_dir.mkdir(exist_ok=True)
        for m in (self.cfg.get("models") or {}).values():
            (self.models_dir / m["file"]).write_bytes(b"gguf")
        self._saved: dict | None = None
        self._env_before: dict | None = None

    def env(self, cuda=None, vulkan=None, **extra) -> dict:
        """os.environ for a child process on this layout: the folders (the run folder too, so a child's lock probe never reaches the
        developer's own run/), the devices each build lists, the logs, no MERAVIA_NO_SERVER."""
        e = dict(os.environ)
        e.pop("MERAVIA_NO_SERVER", None)
        e.update(MERAVIA_RUNTIME=str(self.rt_dir), MERAVIA_MODELS=str(self.models_dir), MERAVIA_RUN=str(self.run_dir), FAKE_ARGV=str(self.argv_log),
                 FAKE_BODIES=str(self.bodies_log), FAKE_LIST_cuda=json.dumps(list(cuda or [])), FAKE_LIST_vulkan=json.dumps(list(vulkan or [])))
        e.update({k: str(v) for k, v in extra.items()})
        return e

    def patch_paths(self, cuda=None, vulkan=None, **extra) -> None:
        """This process on the layout: core.paths at it, and its environment as env() gives a child's (the launchers it spawns read it)."""
        from core import paths
        self._saved = {k: getattr(paths, k) for k in ("RUN", "RUNTIME", "MODELS", "APP")}
        paths.RUN, paths.RUNTIME, paths.MODELS, paths.APP = self.run_dir, self.rt_dir, self.models_dir, self.app
        self._env_before = dict(os.environ)
        os.environ.clear()
        os.environ.update(self.env(cuda, vulkan, **extra))

    def restore(self) -> None:
        from core import paths
        if self._saved is not None:
            for k, v in self._saved.items():
                setattr(paths, k, v)
            self._saved = None
        if self._env_before is not None:
            os.environ.clear()
            os.environ.update(self._env_before)
            self._env_before = None

    def bodies(self) -> list[dict]:
        if not self.bodies_log.exists():
            return []
        return [json.loads(l) for l in self.bodies_log.read_text(encoding="utf-8").splitlines() if l.strip()]

    def argv(self) -> list[list]:
        if not self.argv_log.exists():
            return []
        return [json.loads(l) for l in self.argv_log.read_text(encoding="utf-8").splitlines() if l.strip()]
