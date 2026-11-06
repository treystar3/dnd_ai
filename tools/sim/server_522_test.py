"""(f522) The model server's children, with the runtime folder pointed at a launcher that runs tools/sim/fake_llama.py as
"llama-server" (it writes its argv and the load's log phases as llama-server does).

- The argv: loopback only, a port and a key, no web page, two slots at twice the slot's context, the fit step held at the full
  context (no -ngl), the cache capped, the draft model, the chat template.
- Its own process group and session, so Ctrl+C at the game never reaches it; killing the game kills it, even when load() ran on a
  thread that has ended (one long-lived spawner); its output lands in logs/llama-server.log.
- A request without the key is refused; the run files say where it is; a tool attaches with --attach and refuses without it while the
  game holds the lock; a second lock holder is refused.
- load(): progress only rises and ends at 1.0; a chat made while it loads waits and is no try; a granted context below the settings'
  is refused; close() twice leaves no child and no run files.
- A server that dies is started again once, the next death is 'failed'; the stale-child cleanup stops our own leftover and spares a
  process that is not ours.
- The data hash ignores data/runtime; runtime_problems() passes the shipped settings and names a context too small; fetch_runtime
  refuses a file whose checksum is wrong; MERAVIA_NO_SERVER never spawns.

Run: python tools/sim/server_522_test.py"""

import hashlib
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel

import config
from llm import backend, llama, runtime, sampling
from llm.errors import Failure, NoServer
from storage import statehash

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


def dead(pid: int) -> bool:
    try:
        st = Path(f"/proc/{pid}/status").read_text()
    except OSError:
        return True
    return "\nState:\tZ" in st or "\nState:\tX" in st


def wait_for(cond, seconds=8.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return cond()


LAUNCHER = """#!{py}
import os, sys, time, json
sys.path.insert(0, {sim!r})
args = sys.argv[1:]
with open(os.environ.get("FAKE_ARGV", "/dev/null"), "a") as f:
    f.write(json.dumps(args) + "\\n")
if "--list-devices" in args:
    print("Available devices:")
    print("  CUDA0: NVIDIA GeForce RTX 3060 (12287 MiB, 11200 MiB free)")
    sys.exit(0)
port, key = int(args[args.index("--port") + 1]), args[args.index("--api-key") + 1]
ctx = int(args[args.index("-c") + 1]) // int(args[args.index("-np") + 1])
granted = int(os.environ.get("FAKE_GRANTED", "0") or 0) or ctx
print("0.00.054 I srv    load_model: loading model '" + args[args.index("--model") + 1] + "'", flush=True)
time.sleep(float(os.environ.get("FAKE_LOAD_SECONDS", "0.3")))
print("0.03.273 I cmn          init: llama threadpool init, n_threads = 6", flush=True)
print("load_tensors: offloaded 49/49 layers to GPU", flush=True)
print("0.03.348 I common_speculative_init_result: loading draft model 'x'", flush=True)
from fake_llama import FakeLlama
fake = FakeLlama(key=key, slot_ctx=granted, port=port, script=lambda p, b, n: {{"content": '{{"x": "' + str(os.getpid()) + '"}}'}})
print("0.04.015 I srv    load_model: initializing, n_slots = 2, n_ctx_slot = " + str(granted), flush=True)
print("0.04.120 I srv  server_run_i: model loaded", flush=True)
while True:
    time.sleep(1)
"""

base = Path(tempfile.mkdtemp(prefix="srv522_"))
rt_dir, models_dir, run_dir, logs_dir = base / "runtime", base / "models", base / "run", base / "logs"
build = rt_dir / "cuda"
build.mkdir(parents=True)
models_dir.mkdir()
exe = build / runtime.exe_name()
exe.write_text(LAUNCHER.format(py=sys.executable, sim=str(ROOT / "tools" / "sim")))
exe.chmod(0o755)
CFG = runtime.settings()
for m in CFG["models"].values():
    (models_dir / m["file"]).write_bytes(b"gguf")
argv_log = base / "argv.jsonl"
os.environ["FAKE_ARGV"] = str(argv_log)
os.environ.pop("FAKE_GRANTED", None)
no_server_before = os.environ.pop("MERAVIA_NO_SERVER", None)
started: list = []                                   # every process this test starts by hand, killed at the end whatever happened


def new_rt(cfg=CFG):
    return runtime.Runtime(cfg, runtime=rt_dir, models=models_dir, run_dir=run_dir, logs=logs_dir, build="cuda")


try:
    # ---- the shipped settings, and the data's checks
    check("the shipped settings are clean", runtime.runtime_problems() == [], runtime.runtime_problems())
    small = json.loads(json.dumps(CFG))
    small["server"]["slot_ctx"] = 8192
    check("a context too small is named", any("slot_ctx" in p for p in runtime.runtime_problems(small)), runtime.runtime_problems(small))
    check("the context the game needs fits the slot", runtime.needed_context() <= CFG["server"]["slot_ctx"], runtime.needed_context())
    two = json.loads(json.dumps(CFG))
    two["models"]["embed2"] = dict(two["models"]["embed"])
    check("exactly one embedder", any("exactly one embedder" in p for p in runtime.runtime_problems(two)))

    hroot = base / "hashroot"
    (hroot / "data" / "rules").mkdir(parents=True)
    (hroot / "data" / "runtime").mkdir(parents=True)
    (hroot / "data" / "rules" / "a.yaml").write_text("a: 1\n")
    (hroot / "data" / "runtime" / "server.yaml").write_text("slots: 2\n")
    h1 = statehash.data_hash(hroot)
    (hroot / "data" / "runtime" / "server.yaml").write_text("slots: 1\n")
    h2 = statehash.data_hash(hroot)
    (hroot / "data" / "rules" / "a.yaml").write_text("a: 2\n")
    check("the data hash ignores data/runtime and not the rules", h1 == h2 and statehash.data_hash(hroot) != h2)

    # ---- load
    rt = new_rt()
    seen = []
    rt.load(progress=seen.append)
    child = rt.chat
    check("load ends ready", rt.state == "ready" and child is not None and child.alive(), rt.state)
    check("progress only rises and ends at 1.0", seen == sorted(seen) and seen[-1] == 1.0 and len(seen) >= 3, seen)
    args = [json.loads(l) for l in argv_log.read_text().splitlines() if "--port" in l][-1]

    def val(flag):
        return args[args.index(flag) + 1] if flag in args else None
    check("loopback, a port and a key, no web page", val("--host") == "127.0.0.1" and val("--port") == str(child.port)
          and val("--api-key") == child.key and len(child.key) >= 24 and "--no-webui" in args)
    check("two slots at twice the slot's context", val("-np") == "2" and val("-c") == "32768")
    check("the fit step held at the full context, no -ngl", val("--fit") == "on" and val("--fit-ctx") == "32768" and "-ngl" not in args)
    check("the cache capped, the batch, flash attention, the template", val("--cache-ram") == str(CFG["server"]["cache_ram_mib"])
          and val("-b") == "1024" and val("-ub") == "1024" and val("--flash-attn") == "auto" and "--jinja" in args)
    check("the draft model", val("--spec-type") == "draft-mtp" and val("--spec-draft-model") == str(models_dir / CFG["models"]["draft"]["file"])
          and val("--model") == str(models_dir / CFG["models"]["chat"]["file"]))
    check("its own process group and session", os.getpgid(child.proc.pid) != os.getpgid(0) and os.getsid(child.proc.pid) == child.proc.pid)
    check("its output in logs/llama-server.log", "model loaded" in (logs_dir / "llama-server.log").read_text())
    check("the devices are read", any("RTX 3060" in d for d in rt.facts()["devices"]), rt.facts().get("devices"))
    check("the layers on the card are read", rt.facts().get("offloaded") == "49/49", rt.facts().get("offloaded"))
    info = json.loads((run_dir / "server.json").read_text())
    check("the run files say where it is", info["port"] == child.port and info["key"] == child.key
          and json.loads((run_dir / "server.pid").read_text())[0]["pid"] == child.proc.pid)
    rq = urllib.request.Request(f"http://127.0.0.1:{child.port}/v1/chat/completions", data=b"{}", headers={"Content-Type": "application/json"})
    try:
        urllib.request.build_opener(urllib.request.ProxyHandler({})).open(rq, timeout=5)
        code = 200
    except urllib.error.HTTPError as e:
        code = e.code
    check("a request without the key is refused", code == 401, code)
    m = runtime.Managed(rt)
    rep = m.chat(req())
    check("a chat through the managed source", json.loads(rep.text)["x"] == str(child.proc.pid), rep.text)

    # ---- the lock, attach
    lock = runtime.GameLock(run_dir)
    check("the game takes the lock", lock.acquire())
    second = subprocess.run([sys.executable, "-c", f"import sys; sys.path.insert(0, {str(ROOT)!r}); from llm import runtime; "
                             f"from pathlib import Path; print(runtime.GameLock(Path({str(run_dir)!r})).acquire())"],
                            capture_output=True, text=True, timeout=60)
    check("a second lock holder is refused", second.stdout.strip() == "False", second.stdout + second.stderr)
    check("a tool without --attach refuses while the game is open", runtime.refuse_unless_attached(["tool.py"], run_dir) is not None)
    check("with --attach it goes on", runtime.refuse_unless_attached(["tool.py", "--attach"], run_dir) is None)
    att = runtime.attach(run_dir)
    check("--attach reaches the game's own server", json.loads(att.chat(req()).text)["x"] == str(child.proc.pid))
    lock.release()
    check("with the game closed a tool goes on", runtime.refuse_unless_attached(["tool.py"], run_dir) is None)

    # ---- a death, a restart, then failed
    first_pid = child.proc.pid
    os.kill(first_pid, signal.SIGKILL)
    wait_for(lambda: not child.alive())
    got = None
    try:
        m.chat(req())
    except Failure as f:
        got = f.kind
    check("the call that finds the server gone is one failed try", got == "unreachable", got)
    check("the server is started again once", rt.state == "ready" and rt.chat is not None and rt.chat.proc.pid != first_pid
          and rt.restarts_left == 0, (rt.state, rt.restarts_left))
    check("and answers", json.loads(m.chat(req()).text)["x"] == str(rt.chat.proc.pid))
    check("the death went to crash.log", "llama-server (chat) ended" in (logs_dir / "crash.log").read_text())
    second_child = rt.chat
    os.kill(second_child.proc.pid, signal.SIGKILL)
    wait_for(lambda: not second_child.alive())
    try:
        m.chat(req())
    except Failure:
        pass
    check("the next death is 'failed'", rt.state == "failed", rt.state)
    got = None
    try:
        m.chat(req())
    except Failure as f:
        got = f.kind
    check("a failed server answers no call", got == "unreachable")
    rt.close()

    # ---- close
    rt = new_rt()
    rt.load()
    c = rt.chat
    rt.close()
    rt.close()
    check("close() twice leaves no child and no run files", wait_for(lambda: not c.alive()) and not (run_dir / "server.json").exists()
          and not (run_dir / "server.pid").exists())

    # ---- a chat during the load waits
    os.environ["FAKE_LOAD_SECONDS"] = "1.5"
    rt = new_rt()
    th = threading.Thread(target=rt.load)
    th.start()
    wait_for(lambda: rt.state == "loading", 5)
    t0 = time.monotonic()
    rep = runtime.Managed(rt).chat(req())
    th.join()
    check("a chat made while it loads waits and is answered", rt.state == "ready" and json.loads(rep.text)["x"] == str(rt.chat.proc.pid)
          and time.monotonic() - t0 > 0.5)
    rt.close()
    os.environ["FAKE_LOAD_SECONDS"] = "0.3"

    # ---- a context the fit step shrank
    os.environ["FAKE_GRANTED"] = "8192"
    rt = new_rt()
    got = None
    try:
        rt.load()
    except Failure as f:
        got = f.kind
    c = rt.chat
    check("a granted context below the settings' is refused", got == "too_big" and rt.state == "failed", (got, rt.state))
    check("and leaves no child", c is None or wait_for(lambda: not c.alive()))
    os.environ.pop("FAKE_GRANTED", None)
    rt.close()

    # ---- killing the game kills the child, though load() ran on an ended thread
    parent = subprocess.Popen([sys.executable, "-c", f"""
import sys, threading, time, os
sys.path.insert(0, {str(ROOT)!r})
from pathlib import Path
from llm import runtime
rt = runtime.Runtime(runtime.settings(), runtime=Path({str(rt_dir)!r}), models=Path({str(models_dir)!r}), run_dir=Path({str(base / 'run2')!r}),
                     logs=Path({str(logs_dir)!r}), build="cuda")
t = threading.Thread(target=rt.load)
t.start(); t.join()
print(rt.chat.proc.pid, flush=True)
time.sleep(120)
"""], stdout=subprocess.PIPE, text=True, env={k: v for k, v in os.environ.items() if k != "MERAVIA_NO_SERVER"})
    started.append(parent)
    line = parent.stdout.readline().strip()
    cpid = int(line) if line.isdigit() else 0
    check("the parent started a child", cpid > 0 and not dead(cpid), line)
    parent.send_signal(signal.SIGKILL)
    parent.wait(timeout=10)
    check("killing the game kills the child", cpid > 0 and wait_for(lambda: dead(cpid), 8))

    # ---- the stale-child cleanup
    other = subprocess.Popen(["sleep", "60"])
    started.append(other)
    ours = build / "leftover-python"                    # a program that lives under our runtime folder, as a real llama-server does
    shutil.copy2(os.path.realpath(sys.executable), ours)
    leftover = subprocess.Popen([str(ours), str(exe), "--port", "0", "--api-key", "x", "-c", "32768", "-np", "2", "--model", "m"],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    started.append(leftover)
    time.sleep(0.3)
    run_dir.mkdir(exist_ok=True)
    (run_dir / "server.pid").write_text(json.dumps([{"pid": other.pid, "exe": shutil.which("sleep")},
                                                    {"pid": leftover.pid, "exe": runtime.exe_of(leftover.pid) or ""}]))
    stopped = runtime.stop_stale(run_dir, rt_dir)
    check("our own leftover is stopped", leftover.pid in stopped and wait_for(lambda: leftover.poll() is not None), stopped)
    check("a process that is not ours is spared", other.pid not in stopped and other.poll() is None)
    other.kill()
    other.wait()

    # ---- MERAVIA_NO_SERVER never spawns
    os.environ["MERAVIA_NO_SERVER"] = "1"
    rt = new_rt()
    n_before = len(argv_log.read_text().splitlines())
    got = None
    try:
        rt.load()
    except NoServer:
        got = "NoServer"
    check("MERAVIA_NO_SERVER never spawns", got == "NoServer" and rt.chat is None and len(argv_log.read_text().splitlines()) == n_before)
    os.environ.pop("MERAVIA_NO_SERVER", None)

    # ---- fetch_runtime refuses a wrong checksum
    blob = b"not the model" * 100

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            self.send_response(200)
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    fcfg = {"models": {"chat": {"role": "chat", "file": "c.gguf", "size": len(blob), "sha256": "0" * 64,
                                "source": f"http://127.0.0.1:{srv.server_address[1]}/c"},
                       "ok": {"role": "draft", "file": "d.gguf", "size": len(blob), "sha256": hashlib.sha256(blob).hexdigest(),
                              "source": f"http://127.0.0.1:{srv.server_address[1]}/d"}}}
    (base / "fetch.yaml").write_text(json.dumps(fcfg))
    dest = base / "fetched"
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "fetch_runtime.py"), "--settings", str(base / "fetch.yaml"), "--models",
                          "--models-dir", str(dest)], capture_output=True, text=True, timeout=120)
    check("fetch_runtime refuses a wrong checksum", out.returncode != 0 and not (dest / "c.gguf").exists()
          and not any(p.name.startswith("c.gguf") for p in dest.glob("*")), out.stdout[-400:] + out.stderr[-400:])
    check("and keeps a right one", (dest / "d.gguf").exists() and (dest / "d.gguf").read_bytes() == blob)
    srv.shutdown()
finally:
    for proc in started:
        if proc.poll() is None:
            proc.kill()
            proc.wait()
    for p in list(base.glob("**/server.pid")):
        runtime.stop_stale(p.parent, rt_dir)
    if no_server_before is not None:
        os.environ["MERAVIA_NO_SERVER"] = no_server_before
    shutil.rmtree(base, ignore_errors=True)

print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
