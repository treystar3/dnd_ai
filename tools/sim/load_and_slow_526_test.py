"""(f526) The load screen and slow machines, on fake llama-server launchers and a fake runtime, with the owner's lines laid over
data/rules/launch.yaml in the test alone (until f527 adds them, nothing here is shown and main.py starts the server as f522 does).

- The devices and the class: --list-devices read; the class from a table (a 3060 wholly on the card, one with layers on the processor,
  an RX 7600 XT on Vulkan, an integrated card alone, no card, an NVIDIA card whose old driver CUDA cannot use).
- The ladder: CUDA with an NVIDIA device, else Vulkan on its device with the most memory (named to the server), else the processor.
- Slow mode: below the minimum the turn's deadline is None and a call outside a turn keeps the hang guard, not the 120 s; at the
  minimum both are as before; the kept recordings replayed in slow mode match every input; the slow warning shows once a launch.
- The load: begin() returns at once (the home page is drawn while it loads); Continue before ready shows exactly one loading line and
  goes on at ready; a call made while it loads waits behind the same line; progress only rises and stops at ready; a failed load shows
  the could-not-wake page with Try again and Quit, and Play slowly on the processor when that build is here; a machine that cannot hold
  the model is told the memory it needs; another game open, or damaged files, end the start with their line.
- Dormant: with no launch.yaml the screen is off and no line is shown; the startup check reads the lines once they are there.

Run: python tools/sim/load_and_slow_526_test.py"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "sim"))

from pydantic import BaseModel

from engine import budget
from llm import backend, launch, llama, runtime, sampling
from llm.errors import Failure

no_server_before = os.environ.pop("MERAVIA_NO_SERVER", None)
bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


class Read(BaseModel):
    x: str


def req():
    return backend.ChatRequest(messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], schema=Read,
                               sampling=sampling.resolve("stranger_read", 0.1).at(0), max_tokens=40)


CFG = runtime.settings()
OVERLAY = {"loading": "The world is still gathering itself.", "slow": "This world will move slowly here, but it will move.",
           "damaged": "Something the world needs is missing ({why}).", "could_not_wake": "The world would not wake ({why}).",
           "already_open": "The world is already open in another window.", "no_memory": "The world needs {needed} GB to wake.",
           "try_again": "Try again", "quit": "Quit", "slowly": "Play slowly on the processor"}

# ---- the devices and the class
listed = ["Available devices:", "  CUDA0: NVIDIA GeForce RTX 3060 (12287 MiB, 11200 MiB free)",
          "  Vulkan0: AMD Radeon RX 7600 XT (16368 MiB, 16000 MiB free)", "  Vulkan1: Intel(R) UHD Graphics 770 (2048 MiB, 2000 MiB free)"]
devs = launch.parse_devices(listed)
check("--list-devices is read into devices", [(d["id"], d["api"], d["mib"]) for d in devs]
      == [("CUDA0", "cuda", 12287), ("Vulkan0", "vulkan", 16368), ("Vulkan1", "vulkan", 2048)], devs)
d3060, drx, digpu = devs
table = [
    ("a 3060 wholly on the card", ("cuda", d3060, "49/49"), "minimum"),
    ("a 3060 with layers on the processor", ("cuda", d3060, "43/49"), "below"),
    ("an RX 7600 XT 16 GB on Vulkan, wholly on it", ("vulkan", drx, "49/49"), "minimum"),
    ("an integrated card alone", ("vulkan", digpu, "49/49"), "below"),
    ("no card at all", ("cpu", None, None), "below"),
    ("an NVIDIA 12 GB card through Vulkan (an old driver)", ("vulkan", {"id": "Vulkan0", "api": "vulkan",
                                                                         "name": "NVIDIA GeForce RTX 3060", "mib": 12287}, "49/49"), "below"),
]
for name, args, want in table:
    got = launch.classify(*args, CFG)
    check(f"the class: {name}", got["class"] == want and got["slow"] == (want != "minimum"), got)

# ---- the ladder
check("the ladder: CUDA when it lists an NVIDIA device", launch.choose_build(["cuda", "vulkan", "cpu"], {"cuda": listed[:2]}) == ("cuda", None))
check("the ladder: else Vulkan, on its device with the most memory",
      launch.choose_build(["cuda", "vulkan", "cpu"], {"cuda": [], "vulkan": listed}) == ("vulkan", "Vulkan0"))
check("the ladder: else the processor", launch.choose_build(["cuda", "vulkan", "cpu"], {"cuda": [], "vulkan": []}) == ("cpu", None))
check("the memory a machine is told it needs is the model files' and a quarter more",
      launch.memory_needed_gib(CFG) == -(-int(sum(int(m["size"]) for m in CFG["models"].values()) * 1.25) // 2 ** 30))

# ---- the fake builds: each build's launcher lists its own devices (FAKE_LIST_<build>), and loads as llama-server does
LAUNCHER = """#!{py}
import os, sys, time, json
sys.path.insert(0, {sim!r})
args = sys.argv[1:]
build = os.path.basename(os.path.dirname(os.path.abspath(sys.argv[0])))
with open(os.environ["FAKE_ARGV"], "a") as f:
    f.write(json.dumps([build] + args) + "\\n")
if "--list-devices" in args:
    print("Available devices:")
    for l in json.loads(os.environ.get("FAKE_LIST_" + build, "[]")):
        print(l)
    sys.exit(0)
port, key = int(args[args.index("--port") + 1]), args[args.index("--api-key") + 1]
from fake_llama import FakeLlama
try:
    fake = FakeLlama(key=key, slot_ctx=int(args[args.index("-c") + 1]) // int(args[args.index("-np") + 1]) if "-np" in args else 2048,
                     port=port, loading=10 ** 9, script=lambda p, b, n: {{"content": '{{"x": "y"}}', "vectors": [[1.0, 0.0]],
                                                                         "delay": float(os.environ.get("FAKE_DELAY", "0"))}})
except OSError:
    print("main: couldn't bind HTTP server socket", flush=True); sys.exit(1)
time.sleep(float(os.environ.get("FAKE_LOAD_SECONDS", "0.2")))
if "--embeddings" not in args:
    print("load_tensors: offloaded " + os.environ.get("FAKE_OFFLOAD", "49/49") + " layers to GPU", flush=True)
fake.loading = 0
print("0.04.120 I srv  server_run_i: model loaded", flush=True)
while True:
    time.sleep(1)
"""
base = Path(tempfile.mkdtemp(prefix="load526_"))
rt_dir, models_dir, run_dir, logs_dir = base / "runtime", base / "models", base / "run", base / "logs"
for b in ("cuda", "vulkan", "cpu"):
    (rt_dir / b).mkdir(parents=True)
    exe = rt_dir / b / runtime.exe_name()
    exe.write_text(LAUNCHER.format(py=sys.executable, sim=str(ROOT / "tools" / "sim")))
    exe.chmod(0o755)
models_dir.mkdir()
for m in CFG["models"].values():
    (models_dir / m["file"]).write_bytes(b"gguf")
argv_log = base / "argv.jsonl"
os.environ["FAKE_ARGV"] = str(argv_log)


def new_rt(build=None, cfg=CFG):
    return runtime.Runtime(cfg, runtime=rt_dir, models=models_dir, run_dir=run_dir, logs=logs_dir, build=build)


def chat_argv():
    return [json.loads(l) for l in argv_log.read_text().splitlines() if "--port" in l and "--embeddings" not in l][-1]


real_lines = launch.lines
try:
    # ---- the ladder through the runtime, and the class it finds
    os.environ["FAKE_LIST_cuda"] = json.dumps([listed[1]])
    rt = new_rt()
    rt.load()
    f = rt.facts()
    check("the runtime takes the CUDA build when it lists an NVIDIA card", rt.build == "cuda" and chat_argv()[0] == "cuda", rt.build)
    check("a 3060 wholly on the card is at the minimum: the time limits stand", f["class"] == "minimum" and f["slow"] is False
          and budget.SLOW is False and rt.source.chat_server.no_deadline is None, f)
    rt.close()
    os.environ["FAKE_LIST_cuda"] = "[]"
    os.environ["FAKE_LIST_vulkan"] = json.dumps(listed[2:])
    rt = new_rt()
    rt.load()
    a = chat_argv()
    check("else the Vulkan build, its card with the most memory named to the server", rt.build == "vulkan" and a[0] == "vulkan"
          and a[a.index("--device") + 1] == "Vulkan0", a[:1] + a[-2:])
    check("an RX 7600 XT wholly on the card is at the minimum", rt.facts()["class"] == "minimum", rt.facts().get("class_why"))
    rt.close()
    os.environ["FAKE_LIST_vulkan"] = "[]"
    rt = new_rt()
    rt.load()
    check("else the processor build, below the minimum: slow", rt.build == "cpu" and rt.facts()["slow"] is True and budget.SLOW is True
          and rt.source.chat_server.no_deadline == float(CFG["server"]["hang_seconds"]), (rt.build, rt.facts().get("class")))
    rt.close()
    check("the slow machine's lifted limits go with its server", budget.SLOW is False)

    # ---- slow mode: the turn's deadline, the hang guard
    budget.open()
    try:
        normal = budget.deadline()
        budget.SLOW = True
        slow = budget.deadline()
    finally:
        budget.SLOW = False
        budget.close()
    check("below the minimum the turn's deadline is lifted; at it, it stands", normal is not None and slow is None, (normal, slow))
    from fake_llama import FakeLlama
    fk = FakeLlama(key="k", script=lambda p, b, n: {"content": '{"x": "y"}', "delay": float(b["messages"][-1]["content"])})
    srv = llama.Server(fk.port, "k")
    srv.no_deadline = 2.0                              # the hang guard, made short for the test

    def call(delay):
        try:
            srv.request("POST", "/v1/chat/completions", {"messages": [{"role": "user", "content": str(delay)}]}, None)
            return "answered"
        except Failure as e:
            return e.kind
    check("a call with no deadline runs to the hang guard", call(1.0) == "answered")
    check("and one past it is one failed try", call(3.0) == "deadline")
    fk.close()

    # ---- the kept recordings replayed in slow mode match every input
    for name in ("stub_short", "stub_party", "stub_fight"):
        copy = base / "slow" / name
        shutil.copytree(ROOT / "data" / "replay" / "sessions" / name, copy)
        meta = json.loads((copy / "meta.json").read_text())
        meta["slow"] = True
        (copy / "meta.json").write_text(json.dumps(meta))
        out = subprocess.run([sys.executable, str(ROOT / "tools" / "rerun.py"), str(copy)], capture_output=True, text=True, timeout=900,
                             cwd=str(ROOT), env={**os.environ, "MERAVIA_NO_SERVER": "1"})
        last = [l for l in (out.stdout + out.stderr).splitlines() if l.strip()][-1:] or [""]
        check(f"{name} replayed in slow mode matches every input", out.returncode == 0 and last[0].startswith("all ")
              and "inputs matched" in last[0], (out.stdout + out.stderr)[-600:])

    # ---- the load screen, with the owner's lines laid over
    launch.lines = lambda: dict(OVERLAY)
    check("with every line in, the screen is on", launch.screen_on())
    said: list[str] = []
    answers: list[str] = []
    seen: list[float] = []
    from core import paths as _paths
    saved = {k: getattr(_paths, k) for k in ("RUN", "RUNTIME", "MODELS", "APP")}
    _paths.RUN, _paths.RUNTIME, _paths.MODELS, _paths.APP = base / "game_run", rt_dir, models_dir, base / "app"
    os.environ["FAKE_LIST_cuda"] = json.dumps([listed[1]])
    os.environ["FAKE_LOAD_SECONDS"] = "1.5"
    try:
        sc = launch.Screen(say=said.append, ask=lambda: answers.pop(0) if answers else "quit", progress=seen.append)
        t0 = time.monotonic()
        began = sc.begin()
        took = time.monotonic() - t0
        check("begin() returns at once, so the home page is drawn while the model loads", began and took < 1.0 and not sc.ready(),
              (began, round(took, 2)))
        rt = sc.rt
        waits = []
        rt.on_wait = lambda: (waits.append(1), sc.loading_line())
        got = runtime.Managed(rt).chat(req())
        check("a call made while it loads waits behind the loading line, once", json.loads(got.text)["x"] == "y" and waits == [1]
              and said.count(OVERLAY["loading"]) == 1, (waits, said))
        said.clear()
        check("Continue after ready goes on at once with no loading line", sc.wait() and OVERLAY["loading"] not in said, said)
        check("progress only rises and ends at ready", seen == sorted(seen) and seen and seen[-1] == 1.0
              and len(seen) == len(set(seen)), seen)
        sc.close()

        # a slow machine: the warning once this launch, never twice
        os.environ["FAKE_OFFLOAD"] = "43/49"
        said.clear()
        sc = launch.Screen(say=said.append, ask=lambda: "quit")
        sc.begin()
        sc.done.wait(20)
        sc._ready(sc.rt.facts())                       # a second load in the same launch (Try again) says nothing more
        check("the slow warning shows once a launch, at the load", said.count(OVERLAY["slow"]) == 1, said)
        sc.close()
        os.environ.pop("FAKE_OFFLOAD", None)
        scenes_src = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "scenes").rglob("*.py"))
        check("and never from a scene", "launch." not in scenes_src)

        # Continue before ready: exactly one loading line, then the game
        said.clear()
        sc = launch.Screen(say=said.append, ask=lambda: "quit")
        sc.begin()
        ok = sc.wait()
        check("Continue before ready shows exactly one loading line and goes on at ready", ok and said.count(OVERLAY["loading"]) == 1
              and sc.ready(), said)
        sc.close()

        # a failed load: the could-not-wake page, Try again, Play slowly, Quit
        exe_cuda = rt_dir / "cuda" / runtime.exe_name()
        exe_cuda.chmod(0o644)
        said.clear()
        answers[:] = ["2"]                             # Play slowly on the processor
        sc = launch.Screen(say=said.append, ask=lambda: answers.pop(0) if answers else "quit")
        sc.rt_build_first = None
        sc.begin(build="cuda")
        ok = sc.wait()
        page = [l for l in said if l.startswith("  ")]
        check("a failed load shows the could-not-wake page with Try again, Play slowly and Quit", any(l.startswith("The world would not wake")
              for l in said) and page == ["  1. Try again", "  2. Play slowly on the processor", "  3. Quit"], said)
        check("and Play slowly on the processor loads the processor build", ok and sc.rt.build == "cpu" and sc.ready(), sc.rt.build)
        sc.close()
        said.clear()
        answers[:] = ["1", "3"]                        # Try again (fails again), then Quit
        sc = launch.Screen(say=said.append, ask=lambda: answers.pop(0) if answers else "quit")
        sc.begin(build="cuda")
        ok = sc.wait()
        sc.close()
        relock = runtime.GameLock(_paths.RUN)
        check("Try again tries again, and Quit ends the start with the lock let go", ok is False
              and said.count("  1. Try again") == 2 and relock.acquire(), said)
        relock.release()
        from llm import setup_check
        real_ram = setup_check.ram_gb
        setup_check.ram_gb = lambda: 4.0
        said.clear()
        sc = launch.Screen(say=said.append, ask=lambda: "quit")
        sc.begin(build="cuda")
        sc.wait()
        sc.close()
        setup_check.ram_gb = real_ram
        check("a machine that cannot hold the model is told the memory it needs",
              f"The world needs {launch.memory_needed_gib(CFG)} GB to wake." in said, said)
        exe_cuda.chmod(0o755)

        # another game open; damaged files
        held = runtime.GameLock(_paths.RUN)
        held.acquire()
        said.clear()
        sc = launch.Screen(say=said.append, ask=lambda: "quit")
        check("another game open ends the start with its line", sc.begin() is False and said == [OVERLAY["already_open"]], said)
        held.release()
        (models_dir / CFG["models"]["chat"]["file"]).rename(base / "moved.gguf")
        said.clear()
        sc = launch.Screen(say=said.append, ask=lambda: "quit")
        check("damaged files end the start with their line, the lock let go", sc.begin() is False and said
              and said[0].startswith("Something the world needs is missing") and runtime.GameLock(_paths.RUN).acquire(), said)
        (base / "moved.gguf").rename(models_dir / CFG["models"]["chat"]["file"])
    finally:
        for k, v in saved.items():
            setattr(_paths, k, v)
        os.environ.pop("FAKE_LOAD_SECONDS", None)
        launch.lines = real_lines

    # ---- dormant, and the startup check of the lines
    check("with no launch.yaml the screen is off and no line is shown", not launch.LINES_PATH.exists() and not launch.screen_on()
          and launch.line("loading") is None and launch.problems() == [])
    real_path = launch.LINES_PATH
    launch.LINES_PATH = base / "launch.yaml"
    launch.LINES_PATH.write_text(json.dumps({**OVERLAY, "loading": "The model server is loading.", "slow": "It will be slow - sorry.",
                                             "quit": "Quit {why}", "extra": "x"}))
    probs = launch.problems()
    launch.LINES_PATH = real_path
    check("the startup check reads the lines once they are there", any("machinery" in p for p in probs) and any("dash" in p for p in probs)
          and any("cannot fill" in p for p in probs) and any("no such line" in p for p in probs), probs)
    no_mach = json.loads(json.dumps(CFG))
    no_mach.pop("machine", None)
    check("the minimum card's memory is in the settings, checked", any("machine.minimum_cuda_mib" in p for p in runtime.runtime_problems(no_mach))
          and runtime.runtime_problems() == [], runtime.runtime_problems())
finally:
    launch.lines = real_lines
    for p in list(base.glob("**/server.pid")):
        runtime.stop_stale(p.parent, rt_dir)
    shutil.rmtree(base, ignore_errors=True)
    if no_server_before is not None:
        os.environ["MERAVIA_NO_SERVER"] = no_server_before

print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
