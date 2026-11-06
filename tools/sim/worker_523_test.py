"""(f523) The model worker, on tools/sim/fake_llama.py with scripted timings.

- Preemption: a background call in flight gives the card back when a foreground call comes, within 1.5 s (the server sees it hang
  up); it is sent again once the foreground has been idle, and the layers above see one call and no error.
- A foreground call is never held, and two in the nested shape (one made inside a layer of another) both finish.
- promote() (settle, result) starts a waiting background call at once, with no idle wait.
- After max_cancels a background call runs beside a turn.
- The layers see the caller's own thread in both lanes, and the turn's budget, the gateway's task and the operation read as before.
- close() mid-call ends it Cancelled with nothing counted; in a STRICT session nothing is ever preempted.
- Closing campaign A cancels A's background call and not B's; a session's close cancels its backfill before joining it.
- A background call never lights the busy light.

Run: python tools/sim/worker_523_test.py"""

import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "sim"))

from pydantic import BaseModel

from fake_llama import FakeLlama
from llm import backend, gateway, llama, sampling, worker
from llm.errors import Cancelled, Failure

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


class Read(BaseModel):
    x: str


def chat(text="u"):
    return backend.chat([{"role": "system", "content": "s"}, {"role": "user", "content": text}], Read,
                        sampling.resolve("stranger_read", 0.1).at(0), 40)


def in_lane(lane, fn, session=None, out=None, key="r"):
    def run():
        try:
            with backend.lane(lane, session=session):
                out[key] = fn()
        except BaseException as e:
            out[key] = e
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


def wait_for(cond, seconds=8.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return cond()


# a script: a user line starting "slow" answers after a delay; the first try of "once" is slow, later ones quick
tries: dict[str, int] = {}


def script(path, body, n):
    text = body["messages"][-1]["content"]
    tries[text] = tries.get(text, 0) + 1
    if text.startswith("slow"):
        return {"content": '{"x": "%s"}' % text, "delay": 4.0}
    if text.startswith("once") and tries[text] == 1:
        return {"content": '{"x": "%s"}' % text, "delay": 4.0}
    return {"content": '{"x": "%s"}' % text, "delay": 0.1}


fake = FakeLlama(key="k", script=script)
rows: list[dict] = []


def recorder(op, request, call):            # a layer like the recorder: one row a call it sees
    out = call(request)
    if op == "chat":
        rows.append({"thread": threading.get_ident(), "text": request.messages[-1]["content"], "lane": backend.current_lane()})
    return out


def source(**kw):
    w = worker.Worker(**{"max_cancels": 3, "resume_idle": 0.3, **kw})
    return llama.LlamaServer(llama.Server(fake.port, "k", step=0.1), None,
                             machine={"slot_ctx": 16384, "slots": {"foreground": 0, "background": 1, "input": 0}}, worker=w), w


# ---- preemption
src, w = source()
undo_src, undo_layer = backend.use(src), backend.wrap(recorder, rank=backend.RECORDER)
try:
    out = {}
    d0 = fake.disconnects
    bg = in_lane("background", lambda: chat("once-a"), session="A", out=out)
    wait_for(lambda: tries.get("once-a") == 1)
    time.sleep(0.2)
    t0 = time.monotonic()
    fg = chat("fg-1")
    took = time.monotonic() - t0
    check("a foreground call is answered at once beside a background one", fg.text == '{"x": "fg-1"}' and took < 1.5, took)
    check("the background call gave the card back within 1.5 s", wait_for(lambda: fake.disconnects > d0, 1.5))
    bg.join(10)
    check("the background call is answered with no error", getattr(out.get("r"), "text", "") == '{"x": "once-a"}', out.get("r"))
    check("it was sent again", tries.get("once-a") == 2, tries.get("once-a"))
    check("the layers above saw one call for it", [r["text"] for r in rows].count("once-a") == 1, rows)
    bg_row = next(r for r in rows if r["text"] == "once-a")
    check("the layers saw the caller's own thread, in its lane", bg_row["thread"] == bg.ident and bg_row["lane"] == "background")
    check("the worker counted the preemption", w.stats()["preempted"] == 1, w.stats())

    # ---- the nested shape: a foreground call made inside a layer of another
    def nested(op, request, call):
        if op == "chat" and request.messages[-1]["content"] == "outer":
            inner = chat("inner")
            got = call(request)
            got.text = got.text + "|" + inner.text
            return got
        return call(request)
    undo_n = backend.wrap(nested, rank=40)
    t0 = time.monotonic()
    r = chat("outer")
    undo_n()
    check("two foreground calls in the nested shape finish", r.text == '{"x": "outer"}|{"x": "inner"}' and time.monotonic() - t0 < 2.0, r.text)

    # ---- promote
    chat("fg-2")                                  # the idle clock starts now
    src2, w2 = source(resume_idle=5.0)
    undo2 = backend.use(src2)
    chat("fg-3")
    out = {}
    t0 = time.monotonic()
    bg = in_lane("background", lambda: chat("bg-p"), session="A", out=out)
    time.sleep(0.3)
    check("a background call waits out the idle time", "r" not in out)
    w2.promote(bg.ident)
    bg.join(5)
    check("promote() starts it at once", getattr(out.get("r"), "text", "") == '{"x": "bg-p"}' and time.monotonic() - t0 < 2.0,
          (out.get("r"), time.monotonic() - t0))
    undo2()

    # ---- max_cancels
    src3, w3 = source(max_cancels=1)
    undo3 = backend.use(src3)
    out = {}
    tries.clear()
    bg = in_lane("background", lambda: chat("slow-m"), session="A", out=out)
    wait_for(lambda: tries.get("slow-m") == 1)
    time.sleep(0.2)
    chat("fg-4")                                  # the first preemption
    wait_for(lambda: tries.get("slow-m") == 2, 5)
    time.sleep(0.2)
    d0 = fake.disconnects
    chat("fg-5")                                  # past max_cancels: it runs beside the turn
    bg.join(10)
    check("after max_cancels a background call runs beside a turn", getattr(out.get("r"), "text", "") == '{"x": "slow-m"}'
          and tries.get("slow-m") == 2 and w3.stats()["preempted"] == 1, (out.get("r"), tries.get("slow-m"), w3.stats()))
    undo3()

    # ---- STRICT: nothing preempted
    from engine import streams
    before = streams.STRICT
    streams.STRICT = True
    try:
        src4, w4 = source()
        undo4 = backend.use(src4)
        out = {}
        tries.clear()
        bg = in_lane("background", lambda: chat("once-s"), session="A", out=out)
        wait_for(lambda: tries.get("once-s") == 1)
        time.sleep(0.2)
        chat("fg-6")
        bg.join(10)
        check("in a STRICT session nothing is preempted", tries.get("once-s") == 1 and w4.stats()["preempted"] == 0
              and getattr(out.get("r"), "text", "") == '{"x": "once-s"}', (tries.get("once-s"), w4.stats()))
        undo4()
    finally:
        streams.STRICT = before

    # ---- sessions: A's closing cancels A's, not B's
    src5, w5 = source(resume_idle=0.0)
    undo5 = backend.use(src5)
    oa, ob = {}, {}
    ta = in_lane("background", lambda: chat("slow-A"), session="A", out=oa)
    tb = in_lane("background", lambda: chat("slow-B"), session="B", out=ob)
    wait_for(lambda: tries.get("slow-A") and tries.get("slow-B"))
    time.sleep(0.2)
    t0 = time.monotonic()
    w5.cancel_session("A")
    ta.join(3)
    check("closing campaign A cancels A's background call", isinstance(oa.get("r"), Cancelled) and time.monotonic() - t0 < 1.5, oa.get("r"))
    tb.join(10)
    check("and not B's", getattr(ob.get("r"), "text", "") == '{"x": "slow-B"}', ob.get("r"))
    oa = {}
    ta = in_lane("background", lambda: chat("bg-after"), session="A", out=oa)
    ta.join(3)
    check("a closed campaign's waiting call ends Cancelled too", isinstance(oa.get("r"), Cancelled), oa.get("r"))
    undo5()

    # ---- close() mid-call: Cancelled, nothing counted
    src6, w6 = source(resume_idle=0.0)
    undo6 = backend.use(src6)
    tally0 = dict(gateway.TALLY.get("stranger_read", {"calls": 0}))
    out = {}
    bg = in_lane("background", lambda: gateway.generate("stranger_read", "s", "slow-close", Read, temperature=0.1), session="A", out=out)
    wait_for(lambda: tries.get("slow-close"))
    time.sleep(0.2)
    t0 = time.monotonic()
    src6.close()
    bg.join(3)
    check("close() mid-call ends it Cancelled", isinstance(out.get("r"), Cancelled) and time.monotonic() - t0 < 1.5, out.get("r"))
    check("with nothing counted", gateway.TALLY.get("stranger_read", {"calls": 0}).get("calls") == tally0.get("calls"))
    undo6()

    # ---- the busy light
    lit = []

    class Bridge:
        busy_label = ""

        def __init__(self):
            self.lock, self.depth = threading.Lock(), 0

        def busy(self, on):
            lit.append(on)
    window = Bridge()
    from ui.gui import bridge as gb
    undo_busy = backend.wrap(lambda op, req, call: gb.Bridge.busy_layer(window, op, req, call), rank=backend.BUSY)
    out = {}
    bg = in_lane("background", lambda: chat("bg-busy"), session="B", out=out)
    bg.join(5)
    check("a background call never lights the busy light", lit == [] and getattr(out.get("r"), "text", "") == '{"x": "bg-busy"}', lit)
    chat("fg-busy")
    check("a foreground call does", True in lit, lit)
    undo_busy()
finally:
    undo_layer()
    undo_src()

# ---- a session's close cancels its backfill before joining it
import simlib
from engine import session as sess
from npc import backfill
fake2_tries = []


def script2(path, body, n):
    fake2_tries.append(time.monotonic())
    return {"content": "{}", "delay": 20.0}


fake2 = FakeLlama(key="k", script=script2)
w7 = worker.Worker(max_cancels=3, resume_idle=0.0)
src7 = llama.LlamaServer(llama.Server(fake2.port, "k", step=0.1), None, machine={"slot_ctx": 16384}, worker=w7)
g = simlib.campaign("worker523")
s = g.session
undo7 = backend.use(src7)
try:
    store = s.store
    done = threading.Event()

    def run():
        try:
            with backend.lane("background", session=str(store.root)):
                chat("bg-session")
        except BaseException:
            pass
        finally:
            done.set()
    t = threading.Thread(target=run, daemon=True)
    t.start()
    s.own(t)
    wait_for(lambda: fake2_tries)
    time.sleep(0.2)
    t0 = time.monotonic()
    s.close()
    check("a session's close cancels its background call, then joins it", done.is_set() and time.monotonic() - t0 < 2.0
          and not t.is_alive(), time.monotonic() - t0)
finally:
    undo7()
    fake2.close()
    import shutil
    shutil.rmtree("saves/worker523", ignore_errors=True)

fake.close()
print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
