"""(f524) The embedder's own server, decided at the load, with the runtime folder pointed at a launcher that runs fake_llama as
"llama-server" (an embed child when it is started with --embeddings).

- The embed child's flags: the embedding model, --embeddings, mean pooling, one slot, context, batch and micro-batch at the settings',
  on the card, or on the processor (--device none) when the chat model is not wholly on the card.
- A load whose embedder fails leaves the session with embeddings off for its life, saying why; the chat server is ready all the same.
- Reading the facts before the load is final is refused.
- A 9,000-character text reaches the request capped at the settings' length.
- too_big and cancelled are that call's own fallback: embeddings stay on.
- An embedder that dies is started again once and the call answered; the next death turns embeddings off for the session, said once
  in crash.log.
- An embed made while a chat is in flight is answered at once: it holds no chat slot.
- The cache is the embedder's: another embedder's vectors are not kept.

Run: python tools/sim/embed_server_524_test.py"""

import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from pydantic import BaseModel

import config
from llm import backend, embed, runtime, sampling
from llm.errors import Cancelled, Failure

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


def wait_for(cond, seconds=8.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.05)
    return cond()


class Read(BaseModel):
    x: str


LAUNCHER = """#!{py}
import os, sys, time, json
sys.path.insert(0, {sim!r})
args = sys.argv[1:]
with open(os.environ.get("FAKE_ARGV", "/dev/null"), "a") as f:
    f.write(json.dumps(args) + "\\n")
if "--list-devices" in args:
    print("Available devices:"); print("  CUDA0: NVIDIA GeForce RTX 3060 (12287 MiB, 11200 MiB free)"); sys.exit(0)
port, key = int(args[args.index("--port") + 1]), args[args.index("--api-key") + 1]
embedding = "--embeddings" in args
if embedding and os.environ.get("FAKE_EMBED_FAIL"):
    print("error: failed to load the embedding model", flush=True); sys.exit(3)
ctx = int(args[args.index("-c") + 1]) // int(args[args.index("-np") + 1])
print("0.00.054 I srv    load_model: loading model 'x'", flush=True)
time.sleep(float(os.environ.get("FAKE_LOAD_SECONDS", "0.2")))
if not embedding:
    print("load_tensors: offloaded " + os.environ.get("FAKE_OFFLOAD", "49/49") + " layers to GPU", flush=True)
from fake_llama import FakeLlama
limit = int(os.environ.get("FAKE_EMBED_LIMIT", "0") or 0)
log = os.environ.get("FAKE_REQ_LOG", "/dev/null")


def script(path, body, n):
    with open(log, "a") as f:
        f.write(json.dumps({{"path": path, "pid": os.getpid(), "lens": [len(t) for t in body.get("input") or []]}}) + "\\n")
    if path == "/v1/embeddings":
        texts = body.get("input") or []
        if limit and any(len(t) > limit for t in texts):
            return {{"status": 500, "type": "server_error", "message": "input (3000 tokens) is too large to process. increase the physical batch size"}}
        if any(t.startswith("clustering: slow") for t in texts):
            return {{"vectors": [[1.0, 0.0] for _ in texts], "delay": 3.0}}
        return {{"vectors": [[float(len(t)), 1.0] for t in texts]}}
    if body["messages"][-1]["content"].startswith("slow"):
        return {{"content": '{{"x": "slow"}}', "delay": 2.0}}
    return {{"content": '{{"x": "y"}}'}}
fake = FakeLlama(key=key, slot_ctx=ctx, port=port, script=script)
print("0.04.120 I srv  server_run_i: model loaded", flush=True)
while True:
    time.sleep(1)
"""

base = Path(tempfile.mkdtemp(prefix="emb524_"))
rt_dir, models_dir, run_dir, logs_dir = base / "runtime", base / "models", base / "run", base / "logs"
(rt_dir / "cuda").mkdir(parents=True)
models_dir.mkdir()
exe = rt_dir / "cuda" / runtime.exe_name()
exe.write_text(LAUNCHER.format(py=sys.executable, sim=str(ROOT / "tools" / "sim")))
exe.chmod(0o755)
CFG = runtime.settings()
for m in CFG["models"].values():
    (models_dir / m["file"]).write_bytes(b"gguf")
argv_log, req_log = base / "argv.jsonl", base / "req.jsonl"
os.environ.update(FAKE_ARGV=str(argv_log), FAKE_REQ_LOG=str(req_log))
for k in ("FAKE_EMBED_FAIL", "FAKE_OFFLOAD", "FAKE_EMBED_LIMIT", "FAKE_LOAD_SECONDS"):
    os.environ.pop(k, None)
no_server_before = os.environ.pop("MERAVIA_NO_SERVER", None)
rts: list = []


def new_rt():
    rt = runtime.Runtime(CFG, runtime=rt_dir, models=models_dir, run_dir=run_dir, logs=logs_dir, build="cuda")
    rts.append(rt)
    return rt


def embed_args():
    return [json.loads(l) for l in argv_log.read_text().splitlines() if "--embeddings" in l][-1]


try:
    # ---- the flags, on the card
    rt = new_rt()
    rt.load()
    a = embed_args()
    val = lambda f: a[a.index(f) + 1] if f in a else None
    e = CFG["embed"]
    check("the embed child's flags", val("--model") == str(models_dir / CFG["models"]["embed"]["file"]) and "--embeddings" in a
          and val("--pooling") == "mean" and val("-np") == "1" and val("-c") == str(e["ctx"]) and val("-b") == str(e["batch"])
          and val("-ub") == str(e["ubatch"]) and val("--host") == "127.0.0.1" and "--no-webui" in a and val("--api-key"), a)
    check("on the card when the chat model is wholly on it", "--device" not in a and rt.facts()["embed_device"] == "card")
    check("the embedder is on for the session", rt.facts()["embedder"] is True and rt.facts()["embed_failure"] == "")
    check("its warm-up was its first embed", any(json.loads(l)["path"] == "/v1/embeddings" for l in req_log.read_text().splitlines()))
    info = json.loads((run_dir / "server.json").read_text())
    check("the run files say where it is", info.get("embed_port") == rt.embed.port and len(json.loads((run_dir / "server.pid").read_text())) == 2)

    m = runtime.Managed(rt)
    undo = backend.use(m)
    embed.reset()
    try:
        check("embed.available() reads the load's decision", embed.available() is True)
        req_log.write_text("")
        got = embed.vectors(["word " * 1800])
        lens = [json.loads(l)["lens"] for l in req_log.read_text().splitlines() if json.loads(l)["path"] == "/v1/embeddings"]
        check("a 9,000-character text reaches the request capped", got is not None and lens and max(lens[-1]) == e["max_chars"], lens)
        # a validator embedding while a chat is in flight
        out = {}
        th = threading.Thread(target=lambda: out.setdefault("r", backend.chat(
            [{"role": "user", "content": "slow chat"}], Read, sampling.resolve("stranger_read", 0.1).at(0), 40)))
        th.start()
        time.sleep(0.3)
        t0 = time.monotonic()
        v = embed.vectors(["a validator's line, mid-attempt"])
        took = time.monotonic() - t0
        th.join(10)
        check("an embed made while a chat is in flight holds no chat slot", v is not None and took < 1.0 and "r" in out, took)
        # cancelled: that call's own
        res = {}

        def run_cancel():
            try:
                res["r"] = embed.vectors(["slow and long to embed"])
            except Cancelled:
                res["r"] = "Cancelled"
        th = threading.Thread(target=run_cancel)
        th.start()
        time.sleep(0.4)
        rt.source.cancel(th.ident)
        th.join(5)
        check("a cancelled embed is that call's own: embeddings stay on", res.get("r") == "Cancelled" and not embed.failed()
              and embed.available(), res)
        # the cache is the embedder's
        embed.vectors(["kept line"])
        before = rt.facts
        rt.facts = lambda: {**before(), "embed_model": "another-embedder"}
        req_log.write_text("")
        embed.vectors(["kept line"])
        asked = [l for l in req_log.read_text().splitlines() if json.loads(l)["path"] == "/v1/embeddings"]
        rt.facts = before
        check("another embedder's vectors are not kept", len(asked) == 1, asked)
        # a death, a restart; then off
        first = rt.embed.proc.pid
        os.kill(first, signal.SIGKILL)
        wait_for(lambda: not rt.embed.alive())
        v = embed.vectors(["after the first death"])
        check("an embedder that dies is started again once and the call answered", v is not None and rt.embed.proc.pid != first
              and rt.embed_restarts_left == 0 and not embed.failed(), (v, rt.embed_restarts_left))
        second = rt.embed
        os.kill(second.proc.pid, signal.SIGKILL)
        wait_for(lambda: not second.alive())
        v = embed.vectors(["after the second death"])
        crash = (logs_dir / "crash.log").read_text()
        check("the next death turns embeddings off for the session", v is None and embed.failed() and rt.facts()["embedder"] is False)
        check("said once in crash.log", crash.count("embeddings are off for this session") == 1, crash[-400:])
        check("the chat server goes on", json.loads(backend.chat([{"role": "user", "content": "u"}], Read,
                                                                 sampling.resolve("stranger_read", 0.1).at(0), 40).text)["x"] == "y")
    finally:
        undo()
        embed.reset()
    rt.close()

    # ---- too_big: that call's own
    os.environ["FAKE_EMBED_LIMIT"] = "200"
    rt = new_rt()
    rt.load()
    undo = backend.use(runtime.Managed(rt))
    embed.reset()
    try:
        v = embed.vectors(["x" * 400])
        check("a text the batch refuses is too_big: embeddings stay on", v is None and not embed.failed() and embed.available())
    finally:
        undo()
        embed.reset()
    rt.close()
    os.environ.pop("FAKE_EMBED_LIMIT", None)

    # ---- on the processor when the chat model is not wholly on the card
    os.environ["FAKE_OFFLOAD"] = "40/49"
    rt = new_rt()
    rt.load()
    a = embed_args()
    check("on the processor when the chat model is not wholly on the card", a[a.index("--device") + 1] == "none"
          and rt.facts()["embed_device"] == "processor", a)
    rt.close()
    os.environ.pop("FAKE_OFFLOAD", None)

    # ---- a failed embed load
    os.environ["FAKE_EMBED_FAIL"] = "1"
    rt = new_rt()
    rt.load()
    f = rt.facts()
    check("a failed embed load leaves the chat server ready", rt.state == "ready")
    check("and embeddings off for the session, saying why", f["embedder"] is False and f["embed_failure"], f)
    undo = backend.use(runtime.Managed(rt))
    embed.reset()
    try:
        check("embed.available() is off, so the recording's meta says so", embed.available() is False and embed.vectors(["x"]) is None)
    finally:
        undo()
        embed.reset()
    rt.close()
    os.environ.pop("FAKE_EMBED_FAIL", None)

    # ---- the facts before the load is final
    os.environ["FAKE_LOAD_SECONDS"] = "1.5"
    rt = new_rt()
    th = threading.Thread(target=rt.load)
    th.start()
    wait_for(lambda: rt.state == "loading", 5)
    got = None
    try:
        rt.facts()
    except RuntimeError:
        got = "refused"
    undo = backend.use(runtime.Managed(rt))
    try:
        early = embed.available()
    finally:
        undo()
    th.join(20)
    check("reading the facts before the load is final is refused", got == "refused" and rt.facts()["embedder"] is True)
    check("and the embedder reads that as not yet, never as a failure", early is False and not embed.failed())
    rt.state = "restarting"                             # the chat server's restart keeps the load's decision
    try:
        held = rt.facts()["embedder"]
    except RuntimeError:
        held = "refused"
    rt.state = "ready"
    check("a chat server's restart keeps the embedder's decision", held is True, held)
    rt.close()
    os.environ.pop("FAKE_LOAD_SECONDS", None)

    # ---- the settings' check
    bad_cfg = json.loads(json.dumps(CFG))
    bad_cfg["embed"]["max_chars"] = 300
    check("a cap under what a kept recording embeds is refused", any("max_chars" in p for p in runtime.runtime_problems(bad_cfg)))
finally:
    for rt in rts:
        try:
            rt.close()
        except Exception:
            pass
    if no_server_before is not None:
        os.environ["MERAVIA_NO_SERVER"] = no_server_before
    shutil.rmtree(base, ignore_errors=True)

print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
