"""(f466) The world's own operations, apart and failing apart: a pulse that fails after the player's purchase is rolled back alone (the
purchase and its line stand, the world as it was, the fault in crash.log as the world's, the player told nothing); a pulse that stands
keeps what it started when the player's passage fails; a quest whose issuer the pulse removes is gone after the line; the game's opening
is an operation whose id repeats, so an open stopped in the middle of it runs it again once and an open after a stood one runs nothing;
an arrival's moment stands with its stamps though its telling fails; and the pulse's cap counts a model call made, whatever came of it."""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from core.interrupts import Interrupt
from engine import crashlog, failures, pulse
from llm.gateway import LLMError
from npc.models import NPC
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


g = simlib.campaign("world_466", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/world_466/turns.jsonl"
config.CRASH_LOG_PATH = "saves/world_466/crash.log"
SHOWN = simlib.quiet_console()
real = simlib.below()                           # (f518) the stub answering now, taken before the wrapper goes in over it
LOG = []                                        # ("call", title) and ("commit", kind), in order
FAIL = {"titles": set(), "once": False}


def chat(**k):
    title = k["format"].get("title")
    LOG.append(("call", title))
    if title in FAIL["titles"]:
        if FAIL["once"]:
            FAIL["titles"].discard(title)
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


failing = simlib.stand_in(chat=chat, embed=None, name="world_466")
real_commit = store.commit_operation
real_catch_up = pulse.catch_up


def ops_of_input():
    return [o["kind"] for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps]


def thread_ids():
    return [t["id"] for t in (store.load_world_state() or {}).get("threads", [])]


def narrated():
    return [t for k, t in SHOWN if k == "narrate"]


herb = NPC(id="herb1", name="Tam Reed", people="human", role="herbalist", location="parth", traits=[], trust=50)   # a seller at hand
store.save_npc(herb)
ws.enter("parth")
ws.present, ws.residents = [herb], [herb]
ws.player.character.coins = 100000
store.save_player(ws.player)
now = ws.minutes
TH = {"id": "t466", "title": "Wolves out of the Greywood", "place": "parth", "tier": "normal", "kind": "threat", "stage": 0, "status": "active",
      "stages": [{"description": "Wolves at the pens.", "effects": []}], "fallout": {"description": "The wolves had their fill.", "effects": []},
      "resolution": "Thin the wolves.", "truth": "Something pushed them out.", "clues": [{"text": "Count the tracks.", "holder": "farmer", "npc": "", "found": False}],
      "reveal": "", "made_by": "engine", "told": False, "moment": "", "words": {"town": "Parth", "wild": "the Greywood"},
      "times": [now, now + 30 * 1440], "groups": ["everyone"], "paths": [], "scope_places": [], "made": now}


# ---- the pulse fails after it started something: rolled back alone, the purchase stands, the player reads nothing of it
def failing_catch_up(store_, world, catalog, now_):
    st = store_.load_world_state() or pulse.empty_state(now_)
    st.setdefault("threads", []).append(dict(TH, id="t_fail"))
    store_.save_world_state(st)
    raise KeyError("the pulse tripped over itself")


pulse.catch_up = failing_catch_up
stub.plan = [{"kind": "buy", "ware": "healing draught", "target": herb.id}]
coins0 = ws.player.character.coins
n_crash = len(crashlog.SESSION)
SHOWN.clear(); LOG.clear()
stood = ws.turn("I buy a healing draught from the herbalist.")
check("the purchase and its line stand though the world's pulse failed", stood is True and not ws.line_failed and store.load_player().character.coins < coins0
      and any(i.good == "healing_draught" for i in store.load_player().character.inventory), (stood, ws.line_failed, store.load_player().character.coins, coins0))
check("...the world is as it was: nothing the pulse started before its fault remains", "t_fail" not in thread_ids(), thread_ids())
check("...the fault is in crash.log as the world's, naming the operation", len(crashlog.SESSION) == n_crash + 1 and crashlog.last()["where"] == "world"
      and crashlog.last().get("operation") == "world" and "KeyError" in crashlog.last()["error"], crashlog.last())
check("...the player reads no line that the turn was not taken, and the passage was told", not any(t in failures.lines() for k, t in SHOWN) and narrated(), SHOWN[:6])
check("...the record holds the line, its passage and the world's other operations, the pulse's missing",
      ops_of_input() == ["action:buy", "passage", "arrival", "law", "tail"] and [o.kind for o in ws.line_world_failed] == ["world"], (ops_of_input(), [o.kind for o in ws.line_world_failed]))
check("...and the turn log hears of it, apart from the line's own failures", ws.world_failures() == [{"kind": "world", "error": crashlog.last()["error"][:200], "crash": True}], ws.world_failures())
check("...the line is halted by nothing: the turn counted", store.load_player() and ws.store.meta.turn == 2, ws.store.meta.turn)


# ---- the reverse: the pulse stands, the player's passage fails: what the pulse started stays, a stood line is read
def starting_catch_up(store_, world, catalog, now_):
    st = store_.load_world_state() or pulse.empty_state(now_)
    st.setdefault("threads", []).append(dict(TH, id="t_stands", told=True))
    store_.save_world_state(st)
    return {}


pulse.catch_up = starting_catch_up
ws.present, ws.residents = [herb], [herb]                 # a rollback refreshes who is present; the seller is at hand again
FAIL["titles"], FAIL["once"] = {"Narration"}, False
SHOWN.clear(); LOG.clear()
stood = ws.turn("I buy a healing draught from the herbalist.")
check("a pulse that stands keeps what it started when the player's passage fails", stood is True and "t_stands" in thread_ids() and not ws.line_world_failed,
      (stood, thread_ids(), [o.kind for o in ws.line_world_failed]))
check("...the passage was told by a stand-in, in the narrator's words", [o.kind for o in ws.line_untold] == ["passage"]
      and any(herb.label("player") in t and not failures.MACHINERY.search(t) for t in narrated()), narrated())
FAIL["titles"] = set()


# ---- a quest whose issuer the pulse removes is gone after the line, in the scene and in the save
bram = NPC(id="q466", name="Bram Holt", people="human", role="farmer", location="parth", traits=[], trust=50)
store.save_npc(bram)
from engine import quests
ws.player.quests.append(quests._quest("gather", "F", "Bring 2 healing draughts", ws.minutes, good="healing_draught", count=2, guild=False,
                                      issuer="q466", issuer_name="Bram Holt"))          # a personal request, in the engine's own shape
store.save_player(ws.player)


def removing_catch_up(store_, world, catalog, now_):
    pulse.remove_npc(store_, world, store_.load_npc("q466"), "left for the coast", now_, dead=False)
    return real_catch_up(store_, world, catalog, now_)


pulse.catch_up = removing_catch_up
stub.plan = [{"kind": "look"}]
SHOWN.clear()
stood = ws.turn("I look around.")
check("a quest whose issuer the pulse removed is gone after the line, in the scene and in the save", stood is True and not ws.line_world_failed
      and not any(q.get("issuer") == "q466" for q in ws.player.quests) and not any(q.get("issuer") == "q466" for q in store.load_player().quests),
      (stood, [o.kind for o in ws.line_world_failed], ws.player.quests, store.load_player().quests))
check("...and the one gone is gone", store.load_npc("q466").gone == "left for the coast")
pulse.catch_up = real_catch_up


# ---- an arrival's moment: its stamps commit with the arrival, its telling is a passage after; the telling failing undoes nothing
st = store.load_world_state()
st["threads"] = [dict(TH, id="t_moment", moment="pending", told=False)]
st["door_log"] = {}
store.save_world_state(st)
ws._door_loc = "parth"                                    # not arriving this turn: the moment waits for no roll


def commit_spy(op, *a, **k):
    LOG.append(("commit", op.kind))
    if op.kind == "arrival":
        FAIL["titles"] = {"Narration"}                   # the moment's telling, the passage after the arrival, fails every try
    elif op.kind == "law":
        FAIL["titles"] = set()                           # ...and nothing after it does
    return real_commit(op, *a, **k)


store.commit_operation = commit_spy
stub.plan = [{"kind": "look"}]
SHOWN.clear(); LOG.clear()
stood = ws.turn("I look around.")
th = next((t for t in store.load_world_state()["threads"] if t["id"] == "t_moment"), None)
check("the moment walked into stands, with its stamps, though its telling failed", stood is True and th and th["moment"] == "shown" and th.get("told") is True
      and "told_at" in th, th and {k: th.get(k) for k in ("moment", "told", "told_at")})
check("...the line's own passage stood before it; the moment's telling was a passage operation of its own, told by a stand-in",
      ops_of_input() == ["action:look", "passage", "world", "arrival", "law", "tail"] and [o.kind for o in ws.line_untold] == ["passage"] and not ws.line_world_failed,
      (ops_of_input(), [o.kind for o in ws.line_untold], [o.kind for o in ws.line_world_failed]))
check("...told after the arrival's commit, and the telling of the situation inside it", LOG.index(("commit", "arrival")) < len(LOG) - 1
      and LOG.index(("call", "ThreadTelling")) < LOG.index(("commit", "arrival")) < LOG.index(("call", "Narration"), LOG.index(("commit", "arrival"))), LOG)
store.commit_operation = real_commit
FAIL["titles"], FAIL["once"] = set(), False


# ---- the pulse's cap counts a model call made, whatever came of it
old_P = {k: v for k, v in pulse.P.items()}
pulse.P["eventful_chance"] = 1.0
pulse.P["kinds"] = {"thread": 1}
pulse.P["engine_roll"] = {}
pulse.P["tiers"] = {"rare": {"weight": 100, "stages": 1, "days": [1, 2], "resolved_by_others": 0.2},        # the model's, with no fallback
                    **{k: v for k, v in old_P["tiers"].items() if k in ("campaign", "cataclysm")}}
store.save_world_state(pulse.empty_state(ws.minutes))
ASKED = []
real_generate = pulse.generate


def failing_generate(task, *a, **k):
    ASKED.append(task)
    raise LLMError("the model gave nothing usable")


pulse.generate = failing_generate
pulse.catch_up(store, ws.world, ws.catalog, ws.minutes + 10 * 1440)          # ten days away: thirty pulses, each wanting a situation
pulse.generate = real_generate
check("a model that fails every try is asked as often as the cap allows an operation, not once a pulse",
      ASKED.count("pulse_thread") == pulse.P["max_new_events_per_action"] and set(ASKED) == {"pulse_thread"}, ASKED)
pulse.P.clear(); pulse.P.update(old_P)


# ---- the game's opening is an operation whose id repeats: stopped in the middle, it runs again once; stood, it runs no more
store.save_world_state(pulse.empty_state(ws.minutes))
last0 = store.load_world_state()["last"]
store.meta.minutes += 3 * pulse.INTERVAL                  # three pulses owed when the game opens
store.save_meta()
RAN = []


def interrupted_catch_up(store_, world, catalog, now_):
    st = store_.load_world_state()
    st["last"] = now_
    store_.save_world_state(st)                           # the clock moved, then the game was stopped
    raise Interrupt()


def counting_catch_up(store_, world, catalog, now_):
    RAN.append(now_)
    return real_catch_up(store_, world, catalog, now_)


pulse.catch_up = interrupted_catch_up
try:
    ws.open_world()
    stopped = False
except Interrupt:
    stopped = True
check("an interruption inside the opening's pulse leaves the world's clock unmoved", stopped and store.load_world_state()["last"] == last0 and store._armed is False,
      (stopped, store.load_world_state()["last"], last0))
pulse.catch_up = counting_catch_up
ws.open_world()
first = [o for o in store.load_operations()["ops"] if o["kind"] == "world:open"]
check("the next open runs the same opening once, and it stands", RAN == [ws.minutes] and store.load_world_state()["last"] == last0 + 3 * pulse.INTERVAL and len(first) == 1,
      (RAN, store.load_world_state()["last"], last0, len(first)))
ws.open_world()
check("a third open finds it committed and runs nothing", RAN == [ws.minutes] and len([o for o in store.load_operations()["ops"] if o["kind"] == "world:open"]) == 1, RAN)
pulse.catch_up = real_catch_up

check("the calls here were asked of the test's own stand-in, the failed tellings among them", failing.live() and failing.src.calls["Narration"] >= 3,
      dict(failing.src.calls))
failing()
g.close()
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
shutil.rmtree("saves/world_466", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
