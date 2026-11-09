"""(f536) The understanding's own slot. The slot a call takes follows the gateway's task, from data/runtime/server.yaml slot_of: the
understanding (interpret_action) alone on slot 0, so the checkpoint the server keeps at the end of its system message is never thrown
away by another task's prompt; every other call, the background lane's included, on the other slot. The settings check names a bad map;
the game's run file carries the map to a tool that attaches; a caller's own map by lane (f523's shape) still works; nothing of the slot
is in the request the recorder keeps."""
import copy
import json
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "sim"))

from pydantic import BaseModel   # noqa: E402

import simlib                    # noqa: E402
from fake_llama import FakeLlama  # noqa: E402
from llm import backend, gateway, llama, runtime, sampling  # noqa: E402
from llm import worker as worker_mod  # noqa: E402

bad = []


def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {extra}"))
    if not ok:
        bad.append(name)


class Read(BaseModel):
    x: str


def req(text="hello"):
    return backend.ChatRequest(messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": text}], schema=Read,
                               sampling=sampling.resolve("stranger_read", 0.1).at(0), max_tokens=60)


# ---- 1. the settings: the map, read and checked
cfg = runtime.settings()
s = cfg["server"]
check("the shipped settings put the understanding alone on slot 0 and everything else on slot 1",
      s.get("slot_of") == {"interpret_action": 0} and s.get("other_slot") == 1, (s.get("slot_of"), s.get("other_slot")))
check("...as the machine's map", runtime.slot_map(s) == {"tasks": {"interpret_action": 0}, "default": 1}, runtime.slot_map(s))
check("...and the settings check passes them", not [p for p in runtime.runtime_problems(cfg) if "slot" in p])
wrong = copy.deepcopy(cfg)
wrong["server"]["slot_of"] = {"interpret_action": 2}
wrong["server"]["other_slot"] = -1
probs = runtime.runtime_problems(wrong)
check("a slot past the server's or below zero is named", any("server.slot_of" in p and "0 to 1" in p for p in probs)
      and any("server.other_slot" in p for p in probs), probs)
wrong["server"]["slot_of"] = ["interpret_action"]
check("...and a map that is not task names to numbers", any("server.slot_of" in p for p in runtime.runtime_problems(wrong)))

# ---- 2. the adapter sends the task's slot; the lane no longer decides it
fake = FakeLlama(key="k1", slot_ctx=1000)
fake.script = lambda p, b, n: {"content": '{"x": "y"}'}
src = llama.LlamaServer(llama.Server(fake.port, "k1", step=0.1), machine={"slot_ctx": 1000, "slots": runtime.slot_map(s)})
try:
    def slot_under(task=None, lane=None):
        n = len(fake.chats())
        with backend.lane(lane or "foreground"):
            if task is None:
                src.chat(req())
            else:
                with backend.task(task):
                    src.chat(req())
        chats = fake.chats()
        return chats[-1]["body"].get("id_slot") if len(chats) > n else "no call"
    check("the understanding's call takes slot 0", slot_under("interpret_action") == 0, slot_under("interpret_action"))
    check("a telling's call takes slot 1, whatever its lane", slot_under("narrate") == 1 and slot_under("npc_conversation", "background") == 1
          and slot_under("player_line", "input") == 1, (slot_under("narrate"), slot_under("npc_conversation", "background")))
    check("...so does a call made for no task (a tool's)", slot_under() == 1 and slot_under(None, "background") == 1)
    check("...and the understanding's call takes slot 0 from any lane", slot_under("interpret_action", "background") == 0)
    body = fake.chats()[-1]["body"]
    check("the request itself names no task: the slot is the machine's, outside the recording",
          "task" not in body and backend.neutral_request(req()).get("slot") is None and "slot" not in backend.neutral_request(req()))
    # a caller's own map by lane (f523's shape) still places by lane
    lanes = llama.LlamaServer(llama.Server(fake.port, "k1", step=0.1), machine={"slot_ctx": 1000, "slots": {"foreground": 0, "background": 1}})
    with backend.task("interpret_action"):
        lanes.chat(req())
    fg = fake.chats()[-1]["body"].get("id_slot")
    with backend.lane("background"), backend.task("interpret_action"):
        lanes.chat(req())
    check("a map by lane (a caller's own, f523's shape) still places by lane", fg == 0 and fake.chats()[-1]["body"].get("id_slot") == 1,
          (fg, fake.chats()[-1]["body"].get("id_slot")))
finally:
    fake.close()

# ---- 3. the gateway names the task for the source, and only while the call is made
seen = []


def answer(**kw):
    seen.append(backend.current_task())
    return type("R", (), {"message": type("M", (), {"content": '{"x": "ok"}'})(), "done_reason": "stop"})()


held = simlib.stand_in(chat=answer, name="task-seeing stand-in")
try:
    out = gateway.generate("narrate", "sys", "user", Read, retries=0)
    check("the gateway makes the call under its task's name", out.x == "ok" and seen == ["narrate"], seen)
    check("...and the name is gone once the call is made", backend.current_task() is None)
    seen.clear()
    try:
        gateway.generate("interpret_action", "sys", "user", Read, retries=1)
    except Exception:
        pass
    check("a retry is made under the same task", seen and all(t == "interpret_action" for t in seen), seen)
finally:
    held()

# ---- 4. the run file carries the map to a tool that attaches to the game's server
tmp = Path(tempfile.mkdtemp(prefix="slots536_"))
(tmp / "server.json").write_text(json.dumps({"port": 1, "key": "k", "pid": 0, "slot_ctx": 16384, "build": "cuda",
                                             "slot_of": {"interpret_action": 0}, "other_slot": 1}), encoding="utf-8")
att = runtime.attach(tmp)
check("a tool attached to the game's server places calls as the game does", att.machine.get("slots") == {"tasks": {"interpret_action": 0}, "default": 1},
      att.machine)
(tmp / "server.json").write_text(json.dumps({"port": 1, "key": "k", "pid": 0, "slot_ctx": 16384, "build": "cuda"}), encoding="utf-8")
check("...and a run file from before the map puts every call on slot 0", runtime.attach(tmp).machine.get("slots") == {"tasks": {}, "default": 0})

# ---- 5. (f536's review) a background call the turn may not take the card from holds the shared slot: the turn's call takes the
#         understanding's slot instead of queueing behind it on the server; a background call it does take the card from leaves it slot 1
tries: dict = {}


def script(path, body, n):
    text = body["messages"][-1]["content"]
    tries[text] = tries.get(text, 0) + 1
    return {"content": '{"x": "%s"}' % text, "delay": 1.5 if text.startswith("slow") else 0.05}


def wait_for(cond, seconds=6.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end and not cond():
        time.sleep(0.02)
    return cond()


def in_background(src, text, out):
    def run():
        try:
            with backend.lane("background", session="A"), backend.task("populate_place"):
                out[text] = src.chat(req(text))
        except BaseException as e:
            out[text] = e
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


fake2 = FakeLlama(key="k2", slot_ctx=1000, script=script)
held_src = llama.LlamaServer(llama.Server(fake2.port, "k2", step=0.1), machine={"slot_ctx": 1000, "slots": runtime.slot_map(s)},
                             worker=worker_mod.Worker(max_cancels=0, resume_idle=0.0))     # max_cancels 0: the turn never takes the card back
try:
    out: dict = {}
    t = in_background(held_src, "slow-held", out)
    check("a background call is in flight on the shared slot", wait_for(lambda: tries.get("slow-held") == 1) and fake2.chats()[-1]["body"].get("id_slot") == 1,
          (tries, fake2.chats()[-1]["body"].get("id_slot") if fake2.chats() else None))
    t0 = time.monotonic()
    with backend.task("narrate"):
        held_src.chat(req("fg-telling"))
    took = time.monotonic() - t0
    check("the turn's telling takes the understanding's slot and does not wait for it", fake2.chats()[-1]["body"].get("id_slot") == 0 and took < 1.0,
          (fake2.chats()[-1]["body"].get("id_slot"), round(took, 2)))
    with backend.task("interpret_action"):
        held_src.chat(req("fg-understanding"))
    check("...the understanding keeps its own slot", fake2.chats()[-1]["body"].get("id_slot") == 0)
    t.join(6)
    check("...and the background call was never taken from", getattr(out.get("slow-held"), "text", "") == '{"x": "slow-held"}' and tries.get("slow-held") == 1,
          (out.get("slow-held"), tries.get("slow-held")))
    with backend.task("narrate"):
        held_src.chat(req("fg-after"))
    check("with the shared slot free again, a telling takes it", fake2.chats()[-1]["body"].get("id_slot") == 1, fake2.chats()[-1]["body"].get("id_slot"))
    # a background call the turn does take the card from: the telling keeps the shared slot (the server frees it within a second)
    taking = llama.LlamaServer(llama.Server(fake2.port, "k2", step=0.1), machine={"slot_ctx": 1000, "slots": runtime.slot_map(s)},
                               worker=worker_mod.Worker(max_cancels=3, resume_idle=0.0))
    out2: dict = {}
    t2 = in_background(taking, "slow-taken", out2)
    wait_for(lambda: tries.get("slow-taken") == 1)
    with backend.task("narrate"):
        taking.chat(req("fg-takes"))
    fg_slot = fake2.chats()[-1]["body"].get("id_slot")
    check("a background call the turn takes the card from leaves the telling on the shared slot",
          fg_slot == 1 and wait_for(lambda: taking.worker.stats()["preempted"] >= 1), (fg_slot, taking.worker.stats()))
    t2.join(8)
finally:
    fake2.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
