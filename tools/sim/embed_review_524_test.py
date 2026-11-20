"""(f524's review, fixed) The embedder's server through the chat server's restarts, its own deaths and the place decision, on a launcher
that runs tools/sim/fake_llama.py as "llama-server" (flag files in the run's folder make it fail or load slowly).

- A chat server's restart keeps this session's live embedder (the pid file named it, and the restart's stale-child sweep killed it).
- Two calls that find one dead embedder start one new one, with no false crash note, embeddings staying on.
- A call that reaches the embedder while it is being started again waits and is answered; the facts keep the decision.
- An embedder that was off at the load stays off after a chat server's restart (the recording's meta said so).
- The place decision reads the chat model's own "offloaded" line, never the draft model's after it.
- A chat server that fails its restart stops the embedder with it, and nothing starts an embedder on the failed runtime.
- (f784) Every way the model is brought back brings the embedder with it: Try again after a failed restart, the same through the load
  screen (a turn's call, the could-not-wake page, the call answered), Play slowly on the processor, Try again after a first load that
  failed once its embedder had started, and Try again after the chat server's second death took the embedder with it. An embed call
  on its way when the runtime stops the embedder is no death of the embedder's and decides nothing. An embedder that failed on its own
  at the load stays off through all of it, its reason kept in the facts.
- A port taken before the embedder binds is retried on another; the facts' refusal is its own type.

Run: python tools/sim/embed_review_524_test.py"""

import copy
import json
import os
import shutil
import signal
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel

from llm import backend, embed, runtime, sampling
from llm.errors import Failure, NotFinal
sys.path.insert(0, str(ROOT / "tools" / "sim"))
import fake_runtime

no_server_before = os.environ.pop("MERAVIA_NO_SERVER", None)
bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


class Read(BaseModel):
    x: str


def chat():
    try:
        backend.chat([{"role": "user", "content": "u"}], Read, sampling.resolve("stranger_read", 0.1).at(0), 40)
    except Exception as ex:
        return type(ex).__name__
    return "answered"


LAUNCHER = """#!{py}
import os, sys, time, json
sys.path.insert(0, {sim!r})
base = {base!r}
args = sys.argv[1:]
with open(os.path.join(base, "argv.jsonl"), "a") as f:
    f.write(json.dumps(args) + "\\n")
if "--list-devices" in args:
    print("Available devices:"); print("  CUDA0: NVIDIA GeForce RTX 3060 (12287 MiB, 11200 MiB free)"); sys.exit(0)
port, key = int(args[args.index("--port") + 1]), args[args.index("--api-key") + 1]
embedding = "--embeddings" in args
def flag(name):
    return os.path.exists(os.path.join(base, name))
if embedding and flag("embed_fail"):
    print("error: failed to load the embedding model", flush=True); sys.exit(3)
if not embedding and flag("chat_fail"):
    print("error: failed to load the chat model", flush=True); sys.exit(3)
ctx = int(args[args.index("-c") + 1]) // int(args[args.index("-np") + 1])
from fake_llama import FakeLlama
def script(path, body, n):
    if path == "/v1/embeddings":
        texts = body.get("input") or []
        if any(t.startswith("clustering: slow") for t in texts):
            return {{"vectors": [[1.0, 0.0] for _ in texts], "delay": 3.0}}
        if any(t.startswith("clustering: stall") for t in texts):     # (f784) still on its way when a failed restart has ended
            return {{"vectors": [[1.0, 0.0] for _ in texts], "delay": 10.0}}
        return {{"vectors": [[float(len(t)), 1.0] for t in texts]}}
    return {{"content": '{{"x": "y"}}'}}
try:
    fake = FakeLlama(key=key, slot_ctx=ctx, port=port, loading=10 ** 9, script=script)
except OSError:
    print("main: couldn't bind HTTP server socket, hostname: 127.0.0.1, port: " + str(port), flush=True); sys.exit(1)
print("0.00.054 I srv    load_model: loading model 'x'", flush=True)
delay = 0.2
if embedding and flag("embed_load_seconds"):
    delay = float(open(os.path.join(base, "embed_load_seconds")).read())
time.sleep(delay)
if not embedding:
    print("load_tensors: offloaded " + os.environ.get("FAKE_OFFLOAD", "49/49") + " layers to GPU", flush=True)
    if os.environ.get("FAKE_DRAFT_OFFLOAD"):
        print("common_speculative_init_result: loading draft model 'draft.gguf'", flush=True)
        print("load_tensors: offloaded " + os.environ["FAKE_DRAFT_OFFLOAD"] + " layers to GPU", flush=True)
fake.loading = 0
print("0.04.120 I srv  server_run_i: model loaded", flush=True)
while True:
    time.sleep(1)
"""


def wait_for(cond, seconds=8.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return cond()


def kill(proc):
    fake_runtime.kill(proc.pid)
    wait_for(lambda: proc.poll() is not None)


class Env:
    def __init__(self, tag):
        self.base = Path(tempfile.mkdtemp(prefix=f"emb524_{tag}_"))
        self.rt_dir, self.models, self.run_dir, self.logs = (self.base / n for n in ("runtime", "models", "run", "logs"))
        (self.rt_dir / "cuda").mkdir(parents=True)
        self.models.mkdir()
        self.exe = self.rt_dir / "cuda" / runtime.exe_name()
        fake_runtime.write_exe(self.exe, LAUNCHER.format(py=sys.executable, sim=str(ROOT / "tools" / "sim"), base=str(self.base)))
        self.cfg = runtime.settings()
        for m in self.cfg["models"].values():
            (self.models / m["file"]).write_bytes(b"gguf")
        self.rts = []

    def flag(self, name, on=True, text="1"):
        p = self.base / name
        if on:
            p.write_text(text)
        elif p.exists():
            p.unlink()

    def new_rt(self, cfg=None):
        rt = runtime.Runtime(cfg or self.cfg, runtime=self.rt_dir, models=self.models, run_dir=self.run_dir, logs=self.logs, build="cuda")
        self.rts.append(rt)
        return rt

    def embed_argv(self):
        return [json.loads(l) for l in (self.base / "argv.jsonl").read_text().splitlines() if "--embeddings" in l][-1]

    def embedders(self):
        """The pids of this run's live embedder processes."""
        if os.name == "nt":                            # (f561) the launcher is the program itself on Windows
            return fake_runtime.windows_processes(self.exe, "--embeddings")
        out = []
        for d in os.listdir("/proc"):
            if not d.isdigit():
                continue
            try:
                cmd = open(f"/proc/{d}/cmdline", "rb").read().split(b"\0")
                st = open(f"/proc/{d}/stat").read().split(") ")[1].split()[0]
            except OSError:
                continue
            if st != "Z" and len(cmd) > 1 and cmd[1].decode(errors="replace") == str(self.exe) and b"--embeddings" in cmd:
                out.append(int(d))
        return out

    def cleanup(self):
        for rt in self.rts:
            try:
                rt.close()
            except Exception:
                pass
        for pid in self.embedders():
            fake_runtime.kill(pid)
        shutil.rmtree(self.base, ignore_errors=True)


# what exe_of reads for a native llama-server: its own path (the launcher is a script, so /proc/pid/exe is the interpreter; read the
# script's path from the command line, which is what a real binary's /proc/pid/exe says)
real_exe_of = runtime.exe_of


def native_exe_of(pid):
    try:
        cmd = open(f"/proc/{int(pid)}/cmdline", "rb").read().split(b"\0")
        if len(cmd) > 1 and cmd[1].endswith(runtime.exe_name().encode()):
            return os.path.realpath(cmd[1].decode())
    except OSError:
        return None
    return real_exe_of(pid)


if os.name != "nt":                                    # (f561) on Windows exe_of already reads the launcher's own path
    runtime.exe_of = native_exe_of

try:
    # ---- a chat server's restart keeps the live embedder
    env = Env("restart")
    try:
        rt = env.new_rt()
        rt.load()
        e1 = rt.embed
        undo = backend.use(runtime.Managed(rt))
        embed.reset()
        try:
            kill(rt.chat.proc)
            chat()
            check("a chat server's restart keeps this session's live embedder", rt.state == "ready" and rt.embed is e1 and e1.alive()
                  and env.embedders() == [e1.proc.pid], (rt.state, e1.proc.poll(), env.embedders()))
            check("and its embeddings answer through the new source at once", rt.source.embed_server is not None
                  and embed.vectors(["a line"]) is not None)
        finally:
            undo()
            embed.reset()
        rt.close()
        check("and a close leaves no embedder", wait_for(lambda: env.embedders() == [], 5), env.embedders())
    finally:
        env.cleanup()

    # ---- two calls that find one dead embedder
    env = Env("two")
    try:
        cfg = copy.deepcopy(env.cfg)
        cfg["server"]["restarts"] = 2
        rt = env.new_rt(cfg)
        rt.load()
        kill(rt.embed.proc)
        out, gate = [], threading.Barrier(2)

        def call(i):
            gate.wait()
            try:
                rt.embed_call([f"clustering: line {i}"])
                out.append("answered")
            except Failure as f:
                out.append(f"Failure {f.kind}")
        ts = [threading.Thread(target=call, args=(i,)) for i in range(2)]
        for t in ts:
            t.start()
        for t in ts:
            t.join(30)
        time.sleep(0.3)
        crash = (env.logs / "crash.log").read_text() if (env.logs / "crash.log").exists() else ""
        check("two calls on one dead embedder start one new one, and both are answered", out == ["answered", "answered"]
              and len(env.embedders()) == 1 and rt.facts()["embedder"] is True, (out, env.embedders()))
        check("with no crash note for a live child", "ended with code None" not in crash and "embeddings are off" not in crash)
    finally:
        env.cleanup()

    # ---- a call during the embedder's restart waits; the facts keep the decision
    env = Env("during")
    undo = unwrap = None
    try:
        rt = env.new_rt()
        rt.load()
        undo = backend.use(runtime.Managed(rt))
        embed.reset()
        env.flag("embed_load_seconds", text="2.0")

        def slow_layer(op, req, call):
            if op == "embed" and any("late" in t for t in req):
                time.sleep(0.6)
            return call(req)
        unwrap = backend.wrap(slow_layer, 40)
        kill(rt.embed.proc)
        res = {}
        c = threading.Thread(target=lambda: res.setdefault("C", embed.vectors(["a late line"])))
        c.start()
        time.sleep(0.1)
        a = threading.Thread(target=lambda: res.setdefault("A", embed.vectors(["the line that finds it dead"])))
        a.start()
        time.sleep(0.3)
        try:
            during = rt.facts()["embedder"]
        except NotFinal:
            during = "refused"
        a.join(20)
        c.join(20)
        check("a call reaching the embedder while it is started again waits and is answered", res.get("A") is not None
              and res.get("C") is not None and not embed.failed(), (res.keys(), embed.failed()))
        check("and the facts keep the session's decision meanwhile", during is True, during)
    finally:
        if unwrap:
            unwrap()
        if undo:
            undo()
        embed.reset()
        env.cleanup()

    # ---- an embedder off at the load stays off after a chat server's restart
    env = Env("off")
    undo = None
    try:
        env.flag("embed_fail")
        rt = env.new_rt()
        rt.load()
        undo = backend.use(runtime.Managed(rt))
        embed.reset()
        at_load = rt.facts()["embedder"]
        env.flag("embed_fail", on=False)
        kill(rt.chat.proc)
        chat()
        check("an embedder off at the load stays off after a chat server's restart", at_load is False and rt.state == "ready"
              and rt.facts()["embedder"] is False and env.embedders() == [], (at_load, rt.facts()["embedder"], env.embedders()))
    finally:
        if undo:
            undo()
        embed.reset()
        env.cleanup()

    # ---- the place decision reads the chat model's own line, never the draft's
    env = Env("place")
    try:
        os.environ["FAKE_OFFLOAD"], os.environ["FAKE_DRAFT_OFFLOAD"] = "40/49", "5/5"
        rt = env.new_rt()
        rt.load()
        check("the place decision reads the chat model's line, never the draft's after it", rt.facts()["offloaded"] == "40/49"
              and rt.facts()["embed_device"] == "processor" and "--device" in env.embed_argv(), rt.facts().get("offloaded"))
    finally:
        os.environ.pop("FAKE_OFFLOAD", None)
        os.environ.pop("FAKE_DRAFT_OFFLOAD", None)
        env.cleanup()

    # ---- a failed chat restart stops the embedder with it, and nothing starts an embedder on the failed runtime
    env = Env("failed")
    undo = None
    try:
        rt = env.new_rt()
        rt.load()
        undo = backend.use(runtime.Managed(rt))
        embed.reset()
        e1 = rt.embed
        budget_was = rt.embed_restarts_left
        flying: dict = {}

        def in_flight(key, text):
            """An embed call straight to the runtime, on a thread of its own (llm/embed.py's session switch is left out of it)."""
            try:
                flying[key] = rt.embed_call([text]) is not None
            except Failure as f:
                flying[key] = f.kind

        def embed_notes() -> int:
            return (env.logs / "crash.log").read_text().count("llama-server (embed)") if (env.logs / "crash.log").exists() else 0
        # (f784) an embed call on its way as the restart fails: the fake answers "stall" after 10 s, past the failed restart's 4 s
        going = threading.Thread(target=in_flight, args=("restart", "clustering: stall, on its way as the restart fails"))
        going.start()
        time.sleep(0.8)
        env.flag("chat_fail")
        kill(rt.chat.proc)
        chat()
        going.join(30)
        v = embed.vectors(["a line"])
        check("a failed chat restart stops the embedder with it: no embeddings while the runtime is failed, and the facts say why",
              rt.state == "failed" and not e1.alive() and rt.facts()["embedder"] is False
              and rt.facts()["embed_failure"] == "the model server stopped", (rt.state, rt.facts()["embedder"], rt.facts()["embed_failure"]))
        check("and nothing starts an embedder on the failed runtime", v is None and env.embedders() == []
              and not (env.run_dir / "server.json").exists(), (v, env.embedders()))
        check("(f784) an embed call on its way as the failed restart stops the embedder is no death of the embedder's: no crash note "
              "names it, its own restart is not spent, and the next load decides it", flying.get("restart") == "unreachable"
              and rt.embed_on is None and rt.embed_restarts_left == budget_was and embed_notes() == 0,
              (flying, rt.embed_on, rt.embed_restarts_left, embed_notes()))
        # (f784) Try again (the could-not-wake page's: the same runtime loaded again, never closed) brings the embedder back with it
        env.flag("chat_fail", on=False)
        rt.load()
        check("(f784) Try again after the failed restart brings the embedder back with the model: the facts say so, a new embedder "
              "runs, and the runtime and the game's embeddings answer", rt.state == "ready" and rt.facts()["embedder"] is True
              and rt.embed is not None and rt.embed is not e1 and rt.embed.alive() and len(env.embedders()) == 1
              and rt.embed_call(["clustering: a line straight to the runtime"]) is not None and embed.available()
              and embed.vectors(["a line after Try again"]) is not None,
              (rt.state, rt.facts()["embedder"], rt.facts()["embed_failure"], env.embedders()))

        # the chat server's second death (its one restart spent above: failed with no load), an embed call on its way on an
        # embedder that dies with it, then Try again
        budget_was, e2 = rt.embed_restarts_left, rt.embed
        going = threading.Thread(target=in_flight, args=("death", "clustering: stall, on its way at the second death"))
        going.start()
        time.sleep(0.8)
        kill(rt.chat.proc)
        chat()                                                          # the second death: failed, no restart left
        kill(e2.proc)                                                   # the embedder gone with it (the card's driver reset, say)
        going.join(30)
        while_failed = (rt.state, rt.facts()["embedder"], embed.vectors(["a line while it is failed"]), embed.failed(), rt.embed_on,
                        rt.embed_restarts_left == budget_was)
        rt.load()                                                       # Try again
        check("(f784) after the chat server's second death took the embedder with it, an embed call on its way decides nothing, no "
              "embedding is asked of the failed runtime, and Try again brings the embedder back", flying.get("death") == "unreachable"
              and while_failed == ("failed", False, None, False, True, True) and rt.state == "ready" and rt.facts()["embedder"] is True
              and embed.vectors(["a line after the second death"]) is not None and rt.embed.alive(),
              (flying, while_failed, rt.state, rt.facts()["embedder"], rt.facts()["embed_failure"]))
    finally:
        if undo:
            undo()
        embed.reset()
        env.cleanup()

    # ---- (f784) every way the model is brought back brings the embedder with it, or the facts say why not
    import config
    from llm import launch
    crash_was = config.CRASH_LOG_PATH
    logs = Path(tempfile.mkdtemp(prefix="emb524_logs_"))
    config.CRASH_LOG_PATH = str(logs / "crash.log")    # the load screen writes why it could not wake: here, never logs/

    # the load screen: a turn's call finds the restart failed, the could-not-wake page is answered Try again, and the call goes on
    env = Env("screen")
    undo = None
    said: list[str] = []
    try:
        rt = env.new_rt()
        screen = launch.Screen(say=said.append, ask=lambda: "1")      # "1": Try again
        screen.rt = rt                                                  # as begin() wires it, without the game's own lock or files
        rt.on_wait, rt.on_ready, rt.on_failed = screen.loading_line, screen._ready, screen.recover
        undo = backend.use(runtime.Managed(rt))
        embed.reset()
        screen._load()
        first = screen.wait() and rt.facts()["embedder"]
        e1 = rt.embed
        env.flag("chat_fail")
        kill(rt.chat.proc)
        found = chat()                                                  # the call that finds it dead: the restart fails, no page yet
        env.flag("chat_fail", on=False)
        again = chat()                                                  # the next: the page, Try again, the load, the call answered
        check("(f784) through the load screen: a call that finds the restart failed, the page answered Try again, is answered with the "
              "embedder back", first is True and found == "Failure" and again == "answered" and rt.facts()["embedder"] is True
              and rt.embed is not e1 and rt.embed.alive() and embed.vectors(["a line after the page"]) is not None,
              (first, found, again, rt.facts()["embedder"], rt.facts()["embed_failure"], said[-4:]))
    finally:
        if undo:
            undo()
        embed.reset()
        env.cleanup()

    # a first load that fails after its embedder has started (the same failure handler), then Try again; then a failed restart, and
    # Play slowly on the processor (the same runtime, loaded again on the processor's build)
    env = Env("late")
    real_classify, planted = launch.classify, {"left": 1}

    def classify_once(*a, **k):
        if planted["left"]:
            planted["left"] -= 1
            raise Failure("unreachable", "the load failed after the embedder had started")
        return real_classify(*a, **k)
    undo = None
    try:
        (env.rt_dir / "cpu").mkdir()
        fake_runtime.write_exe(env.rt_dir / "cpu" / runtime.exe_name(),
                               LAUNCHER.format(py=sys.executable, sim=str(ROOT / "tools" / "sim"), base=str(env.base)))
        rt = env.new_rt()
        launch.classify = classify_once                                 # the load's last step, after the embedder is up
        try:
            rt.load()
            first = "loaded"
        except Failure:
            first = "failed"
        launch.classify = real_classify
        stopped = env.embedders() == [] and rt.facts()["embedder"] is False
        rt.load()
        check("(f784) a first load that fails after its embedder started stops it with the model, and Try again brings both up",
              first == "failed" and stopped and rt.state == "ready" and rt.facts()["embedder"] is True and rt.embed.alive(),
              (first, stopped, rt.state, rt.facts()["embedder"], rt.facts()["embed_failure"]))
        env.flag("chat_fail")
        kill(rt.chat.proc)
        undo = backend.use(runtime.Managed(rt))
        chat()
        failed_restart = rt.state == "failed"
        env.flag("chat_fail", on=False)
        rt.build, rt.device_id = "cpu", None                            # what the page's "Play slowly on the processor" sets
        rt.load()
        check("(f784) Play slowly on the processor after a failed restart brings the embedder back too", failed_restart
              and rt.state == "ready" and rt.build == "cpu" and rt.facts()["embedder"] is True and rt.embed is not None
              and rt.embed.alive(), (failed_restart, rt.state, rt.build, rt.facts()["embedder"], rt.facts()["embed_failure"]))
    finally:
        launch.classify = real_classify
        if undo:
            undo()
        embed.reset()
        env.cleanup()

    # the pin: an embedder that failed on its own at the load stays off through a failed restart and Try again, and says why
    env = Env("alone")
    undo = None
    try:
        env.flag("embed_fail")
        rt = env.new_rt()
        rt.load()
        why = rt.facts()["embed_failure"]
        env.flag("embed_fail", on=False)
        env.flag("chat_fail")
        kill(rt.chat.proc)
        undo = backend.use(runtime.Managed(rt))
        chat()
        env.flag("chat_fail", on=False)
        rt.load()
        check("(f784) an embedder that failed on its own at the load stays off through a failed restart and Try again, its own reason "
              "kept", rt.state == "ready" and rt.facts()["embedder"] is False and env.embedders() == [] and why
              and rt.facts()["embed_failure"] == why, (rt.state, rt.facts()["embedder"], why, rt.facts()["embed_failure"]))
    finally:
        if undo:
            undo()
        embed.reset()
        env.cleanup()
        config.CRASH_LOG_PATH = crash_was
        shutil.rmtree(logs, ignore_errors=True)

    # ---- a port taken before the embedder binds is retried on another
    env = Env("bind")
    try:
        import socket
        taken = socket.socket()
        taken.bind(("127.0.0.1", 0))
        taken.listen(1)
        real_free_port, picks = runtime.free_port, []

        def second_taken():
            picks.append(1)
            return taken.getsockname()[1] if len(picks) == 2 else real_free_port()   # the chat's port first, then the embedder's
        runtime.free_port = second_taken
        rt = env.new_rt()
        try:
            rt.load()
        finally:
            runtime.free_port = real_free_port
        check("a port taken before the embedder binds is retried on another", rt.facts()["embedder"] is True
              and rt.embed.port != taken.getsockname()[1], (rt.facts()["embedder"], rt.embed_why))
        taken.close()
    finally:
        env.cleanup()

    # ---- the facts' refusal is its own type
    check("the facts' refusal is its own type, a RuntimeError", issubclass(NotFinal, RuntimeError) and NotFinal is not RuntimeError)
finally:
    runtime.exe_of = real_exe_of
    if no_server_before is not None:
        os.environ["MERAVIA_NO_SERVER"] = no_server_before

print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
