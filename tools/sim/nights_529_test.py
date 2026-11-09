"""(f529) The nights and every developer tool on the game's own llama-server (tools/runtime_cli.py), on fake launchers
(tools/sim/fake_runtime.py: a fake server answering every contract with the stand-in model).

- A night of three runs at once (tools/nightrun.py --parallel 3, the real game, no --stub) starts three servers on three ports, one a
  run, each closed by its own run (every run plays its turns to the end; no child is left); --record reaches the first run alone, the
  measuring runs play unrecorded; run.json carries what the model ran on (the build, the class, the model's sha) and the sampling base
  and table as data has them; the recorded run replays exactly (tools/rerun.py).
- The night script names no Ollama (tools/sim/night_script_445_test.py has the rest).
- No tool sends the backend the old client's keywords (model=, format=, options=, keep_alive=).
- The bot's line is on the input lane, and an input-lane call never takes the card from a background call (llm/worker.py); a foreground
  call does.
- runtime_cli: load refuses in plain words when the files are not in place, when the game is open, and when there is no game to attach
  to; a load in this process reports the build and the sha and is closed whole; the default is back after.
- server_back waits for a restarting server and gives up on one that failed for good (tools/sim/nightrun_test.py).

Run: python tools/sim/nights_529_test.py"""

import ast
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "tools" / "sim"))

import config
from llm import backend, runtime, sampling, worker
from llm.errors import Failure

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


from fake_runtime import Layout, THE_3060
base = Path(tempfile.mkdtemp(prefix="nights529_"))
lay = Layout(base)
CFG = runtime.settings()

# ---- a night of three runs at once, each on a server of its own
for d in glob.glob(str(ROOT / "saves" / "nights529*")):
    shutil.rmtree(d, ignore_errors=True)
out = base / "night"
env = lay.env(cuda=[THE_3060], FAKE_LOAD_SECONDS="0.3", FAKE_SEED="5")
r = subprocess.run([sys.executable, "tools/nightrun.py", "--runs", "3", "--parallel", "3", "--turns", "2", "--hours", "1", "--seed", "11",
                    "--out", str(out), "--save", "nights529", "--record"], cwd=ROOT, env=env, capture_output=True, text=True, timeout=1500)
runs = sorted((p for p in out.iterdir() if p.is_dir()), key=lambda p: int(p.name.rsplit("_", 1)[1])) if out.exists() else []
infos = [json.loads((p / "run.json").read_text(encoding="utf-8")) for p in runs if (p / "run.json").exists()]
check("three runs at once, on the game's own server, each to its turn limit", r.returncode == 0 and "3 at a time" in r.stdout and len(infos) == 3
      and all(i.get("turns") == 2 and i.get("reason") == "turn limit (2)" for i in infos), (r.stdout[-1500:], r.stderr[-1500:], [(i.get("turns"), i.get("reason")) for i in infos]))
chat_launches = [a for a in lay.argv() if "--port" in a and "--embeddings" not in a]
ports = {a[a.index("--port") + 1] for a in chat_launches}
check("three servers on three ports, one a run (and an embedder each)", len(chat_launches) == 3 and len(ports) == 3
      and len([a for a in lay.argv() if "--embeddings" in a]) == 3, (len(chat_launches), ports))
check("each run's server log sits with its logs, and each server loaded", all((p / "llama-server.log").exists() and "model loaded" in (p / "llama-server.log").read_text(encoding="utf-8", errors="replace") for p in runs), [p.name for p in runs])
left = subprocess.run(["pgrep", "-f", "--", str(lay.rt_dir)], capture_output=True, text=True)
check("no child is left after the night: each run closed its own", left.returncode == 1 and not left.stdout.strip(), left.stdout)
check("--record reaches the first run alone; the measuring runs play unrecorded", len(runs) == 3 and (runs[0] / "recording").is_dir()
      and not (runs[1] / "recording").exists() and not (runs[2] / "recording").exists(), [sorted(x.name for x in p.iterdir()) for p in runs])
srv = [i.get("server") or {} for i in infos]
check("run.json carries what the model ran on: the source, the build, the class, the model's sha, no warning at the minimum",
      srv and all(s.get("source") == "llama-server" and s.get("build") == "cuda" and s.get("class") == "minimum"
                  and s.get("model_sha") == CFG["models"]["chat"]["sha256"] and s.get("kind") == "runtime" and s.get("warnings") == [] for s in srv), srv[:1])
check("...and the sampling base and table as data has them", infos and all(i["sampling"]["base"] == dict(sampling.BASE)
      and i["sampling"]["table"] == {k: dict(v) for k, v in config.SAMPLING.items()} for i in infos), infos[0].get("sampling") if infos else None)
if runs and (runs[0] / "recording").is_dir():
    rr = subprocess.run([sys.executable, str(ROOT / "tools" / "rerun.py"), str(runs[0] / "recording")], capture_output=True, text=True, timeout=900,
                        cwd=str(ROOT), env={**os.environ, "MERAVIA_NO_SERVER": "1"})
    last = [l for l in (rr.stdout + rr.stderr).splitlines() if l.strip()][-1:] or [""]
    check("the recorded run replays exactly", rr.returncode == 0 and last[0].startswith("all ") and "inputs matched" in last[0], (rr.stdout + rr.stderr)[-800:])
else:
    check("the recorded run replays exactly", False, "no recording")
for d in glob.glob(str(ROOT / "saves" / "nights529*")):
    shutil.rmtree(d, ignore_errors=True)

# ---- no tool sends the backend the old client's keywords
offenders = []
for f in sorted((ROOT / "tools").glob("*.py")):
    tree = ast.parse(f.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            kws = {k.arg for k in node.keywords if k.arg}
            if "keep_alive" in kws or {"model", "format", "options"} <= kws:
                offenders.append(f"{f.name}:{node.lineno}")
check("no tool sends the old client's keywords (model=, format=, options=, keep_alive=) to anything", offenders == [], offenders)
check("the night script names no Ollama", "ollama" not in (ROOT / "tools" / "runpod_night.sh").read_text(encoding="utf-8").lower())

# ---- the bot's line is on the input lane, which never takes the card from a background call
import nightbot
from llm import gateway
lanes: list[str] = []
real_generate = gateway.generate
gateway.generate = lambda *a, **k: (lanes.append(backend.current_lane()), types.SimpleNamespace(line="I look around the square."))[1]
fake_bot = types.SimpleNamespace(c=types.SimpleNamespace(name="Ash", level=13), P={"text": "a steady player"},
                                 ws=types.SimpleNamespace(player=types.SimpleNamespace(party=[]), present=[], acting=None), recent=[],
                                 stats={"model_seconds": 0.0, "model_failed": 0}, goal_sentence=lambda text, intent, kind: (text, []),
                                 where=lambda: "the square", hp=lambda: 1.0)
try:
    line = nightbot.Bot.model_line(fake_bot, "look around", {"kind": "look"}, "look", "")
finally:
    gateway.generate = real_generate
check("the bot's line is asked for on the input lane", line == "I look around the square." and lanes == ["input"], (line, lanes))

w = worker.Worker(max_cancels=3, resume_idle=0.0)
flags: dict = {}
started, release = threading.Event(), threading.Event()


def background():
    def send(flag):
        flags.setdefault("flags", []).append(flag)
        started.set()
        release.wait(5)
        if flag.is_set():
            raise Failure("cancelled", "preempted")
        return "done"
    try:
        flags["result"] = w.background(send)
    except Exception as e:
        flags["result"] = e


t = threading.Thread(target=background, daemon=True)
t.start()
started.wait(5)
w.foreground(lambda _: "typed", lane="input")
input_left_it = not flags["flags"][0].is_set()
w.foreground(lambda _: "turn", lane="foreground")
foreground_took_it = flags["flags"][0].is_set()
release.set()
t.join(10)
check("an input-lane call never takes the card from a background call; a foreground call does, and the call is sent again unseen",
      input_left_it and foreground_took_it and flags.get("result") == "done" and w.preempted == 1 and len(flags["flags"]) == 2,
      (input_left_it, foreground_took_it, flags.get("result"), w.preempted))

# ---- runtime_cli in this process: the refusals, a load reported and closed whole
import runtime_cli
no_server_before = os.environ.pop("MERAVIA_NO_SERVER", None)
lay.patch_paths(cuda=[THE_3060], FAKE_LOAD_SECONDS="0.2")
try:
    got = None
    try:
        runtime_cli.load(attach=True)
    except Failure as f:
        got = f
    check("--attach with no game open is refused in plain words", got is not None and got.kind == "unreachable" and "no game" in (got.detail or ""), got)
    lock = runtime.GameLock(lay.run_dir)
    lock.acquire()
    try:
        runtime_cli.load(say=lambda m: None)
        got = None
    except SystemExit as e:
        got = str(e)
    finally:
        lock.release()
    check("while the game is open a tool is told to use --attach, and starts no server", got is not None and "--attach" in got
          and not [a for a in lay.argv() if "--port" in a and a not in chat_launches and "--embeddings" not in a], got)
    chat_file = lay.models_dir / CFG["models"]["chat"]["file"]
    chat_file.unlink()
    try:
        runtime_cli.load(say=lambda m: None)
        got = None
    except SystemExit as e:
        got = str(e)
    chat_file.write_bytes(b"gguf")
    check("missing files are refused with the fetch to run", got is not None and "not in place" in got and "fetch_runtime.py" in got, got)
    told: list[str] = []
    tool_out = base / "tool"
    tool_out.mkdir()
    server = runtime_cli.load(out=tool_out, say=told.append)
    rep = server.report()
    child = server.rt.chat.proc
    check("a load in this process: the source is the game's own server, its run files under the tool's folder, one line said",
          backend.source().name == "llama-server" and server.source is backend.source() and (tool_out / "run" / "server.json").exists()
          and len(told) == 1 and "class minimum" in told[0] and (tool_out / "llama-server.log").exists(), (told, backend.source().name))
    check("...reported: the build, the class, the model's sha, the embedder, the threads", rep["build"] == "cuda" and rep["class"] == "minimum"
          and rep["model_sha"] == CFG["models"]["chat"]["sha256"] and rep["embedder"] is True and rep["warnings"] == [] and "threads" in rep, rep)
    server.close()
    end = time.monotonic() + 10
    while child.poll() is None and time.monotonic() < end:
        time.sleep(0.1)
    check("...and closed whole: the child gone, the source taken away, the default back", child.poll() is not None
          and backend.source().name == "runtime", (child.poll(), backend.source().name))
finally:
    lay.restore()
    if no_server_before is not None:
        os.environ["MERAVIA_NO_SERVER"] = no_server_before
    shutil.rmtree(base, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
