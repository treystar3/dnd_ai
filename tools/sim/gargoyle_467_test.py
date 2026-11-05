"""(f467) The gargoyle, whole: a summoner's party kills a foe and the game dies right after the round's commit, before its telling. The
save holds the fight over, the experience counted once and one kill in the event log; the next load tells what stood once, after a line
that says it is of before, through the installed bindings and never in the machinery's words; a load after that shows nothing and
changes nothing; the recording carries what was recovered and replays in a child process. The same kill with its telling failing is told
by the fight's stand-ins now and leaves nothing for the next load; with the tail failing it stays finished with no second kill; a defeat
whose goddess line fails is a death that stands, the player waking once."""
import json
import pathlib
import shutil
import subprocess
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("summoner", 3)
simlib.install(stub)
import config
import ui.console as uc
from core.interrupts import Interrupt
from engine import combat, crashlog, failures, operation
from llm import gateway
from scenes import combat_scene as cs
from storage import statehash
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


NAME = "gargoyle_467"
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
config.TURN_LOG_PATH = f"saves/{NAME}/turns.jsonl"
config.CRASH_LOG_PATH = f"saves/{NAME}/crash.log"
SHOWN = simlib.quiet_console()
real = simlib.below()                                   # (f518) the stub's stand-in, taken before the failing one goes in over it
FAIL = {"titles": set(), "raised": 0}


def chat(**k):
    if k["format"].get("title") in FAIL["titles"]:
        FAIL["raised"] += 1
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


failing = simlib.stand_in(chat=chat)


def kills(store):
    return store._db.execute("SELECT count(*) FROM event_log WHERE kind = 'kill'").fetchone()[0]


def fight(ws, name="wolf 1", level=1, rank="normal", hp=1, damage=None):
    creature = ws.world.bestiary["wolf"]                  # a beast: its death is always a kill (a fallen outlaw may live and yield, f392)
    foe = combat.fighter_from_creature(creature, level, rank, "e1", name=name)
    foe.hp = foe.max_hp = hp
    if damage:
        foe.weapon_damage = damage
    sc = cs.CombatScene.begin(ws, creature, [foe], "It is on you:")
    ws.combat = sc
    stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
    return sc


def texts():
    return [t for k, t in SHOWN]


# ---- the kill, and the game dead between the round's commit and its telling
g = simlib.campaign(NAME, cls="summoner", seed=3, location="parth")
ws, store = g.scene, g.store
ws.enter("parth")
check("a summoner's party: the wolf fights beside them", any(c.name == "Grey Wolf" for c in ws.player.character.companions))
fight(ws)
xp0, kills0 = store.load_player().character.xp, kills(store)
g.crash_after_commit("line")
SHOWN.clear()
try:
    ws.turn("I attack the wolf")
    stopped = False
except Interrupt:
    stopped = True
check("the game stops right after the round's commit, before anything of it is shown", stopped and not any("Victory" in t for t in texts()), (stopped, texts()[:4]))
check("...the save holds the fight over, the experience counted once and one kill in the log", store.load_combat() is None and store.load_player().character.xp > xp0
      and kills(store) == kills0 + 1, (store.load_combat(), store.load_player().character.xp, xp0, kills(store), kills0))
pending = store.unshown()
check("...and the round's entry waits to be shown, with its calls and its untold passages marked", len(pending) == 1 and list(pending.values())[0]["kind"] == "line"
      and any(c[0] == "marker" for c in list(pending.values())[0]["calls"]) and any("Victory" in " ".join(map(str, c[1])) for c in list(pending.values())[0]["calls"]),
      {k: (v["kind"], [c[0] for c in v.get("calls", [])]) for k, v in pending.items()})
xp1, kills1 = store.load_player().character.xp, kills(store)
g.close()
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

# ---- the next load tells it once, recorded; the load after shows nothing and changes nothing
g2 = simlib.campaign(NAME, cls="summoner", seed=3, location="parth", fresh=False)
ws2, store2 = g2.scene, g2.store
OUT = pathlib.Path(f"saves/{NAME}_rec")
shutil.rmtree(OUT, ignore_errors=True)
stub.plan = [{"kind": "look"}]
SCRIPT = ["I look around.", "quit"]
uc.ask = lambda *a, **k: SCRIPT.pop(0) if SCRIPT else "quit"
g2.session.record(folder=OUT)                            # after the script's ask is in place: the recorder wraps it
SHOWN.clear()
ws2.run()
shown = texts()
later = next((i for i, t in enumerate(shown) if t in failures.F["shown_later"]), None)
victory = next((i for i, t in enumerate(shown) if t.startswith("Victory.")), None)
check("the next load says once that this is of before, then shows what stood: the Victory line among it", later is not None and victory is not None and later < victory, shown[:8])
check("...in the world's words, never the machinery's", not any(failures.MACHINERY.search(t) for t in shown[:victory + 1] if t), shown[:victory + 1])
check("...the fight is not resumed, nothing is counted twice, and nothing waits past the load", ws2.combat is None and store2.load_player().character.xp == xp1
      and kills(store2) == kills1 and store2.unshown() == {}, (ws2.combat, store2.load_player().character.xp, xp1, kills(store2), kills1, store2.unshown()))
g2.close()
turns = [json.loads(l) for l in (OUT / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
hows = [p["how"] for p in turns[0]["presented"]] if turns else []
check("the recording carries what was recovered at the reopened input: after the opening's own operation, before what the line showed",
      hows[:2] == ["shown", "recovered"] and hows.count("recovered") == 1 and len(hows) > 2, hows)
out = subprocess.run([sys.executable, "tools/rerun.py", str(OUT)], capture_output=True, text=True, timeout=600)
last = (out.stdout.strip().splitlines() or [""])[-1]
check("...and replays in a child process, the recovery compared", out.returncode == 0 and last.startswith("all ") and "inputs matched" in last,
      (out.returncode, out.stdout[-300:], out.stderr[-300:]))
shutil.rmtree(OUT, ignore_errors=True)

g3 = simlib.campaign(NAME, cls="summoner", seed=3, location="parth", fresh=False)
ws3, store3 = g3.scene, g3.store
ws3.open_world()
d0 = statehash.digest(store3)
SHOWN.clear()
check("a load after that shows nothing of before and changes nothing", ws3.recover_unshown() is False and not SHOWN and statehash.digest(store3) == d0, SHOWN[:3])
ws3.enter("parth")

# ---- the same kill with its telling failing: the fight's stand-ins now, nothing for the next load
fight(ws3)
FAIL["titles"] = {"Narration"}
SHOWN.clear()
raised0 = FAIL["raised"]
stood = ws3.turn("I attack the wolf")
check("(f518) the telling's failure was raised by the stand-in answering, a server's error tried three times",
      failing.live() and FAIL["raised"] - raised0 >= 3 and (FAIL["raised"] - raised0) % 3 == 0, (failing.live(), FAIL["raised"] - raised0))
lines = [t for k, t in SHOWN if k == "narrate"]
check("the kill whose telling fails is told by the fight's stand-ins now", stood is True and ws3.combat is None and any(t in failures.F["round_stood"] for t in lines)
      and [o.kind for o in ws3.line_untold] == ["round", "aftermath"], (stood, [o.kind for o in ws3.line_untold], lines[:3]))
check("...with nothing left for the next load, and the stand-ins on the record of what was presented", store3.unshown() == {}
      and [p["how"] for p in operation.PRESENTED if p["how"] == "stand_in"] == ["stand_in", "stand_in"], (store3.unshown(), operation.PRESENTED[-6:]))
FAIL["titles"] = set()

# ---- the same kill with the tail failing: finished, written down, no second kill
kills2 = kills(store3)
fight(ws3)


def failing_tick():
    raise KeyError("a tick that trips")


ws3.banter_tick = failing_tick
n_crash = len(crashlog.SESSION)
stood = ws3.turn("I attack the wolf")
del ws3.banter_tick
kills3 = kills(store3)
check("the kill whose tail fails stays finished, the fault written down as the world's", stood is True and ws3.combat is None and store3.load_combat() is None
      and [w["kind"] for w in ws3.world_failures()] == ["tail"] and len(crashlog.SESSION) == n_crash + 1 and crashlog.last()["where"] == "world", (stood, ws3.world_failures(), crashlog.last()))
stub.plan = [{"kind": "look"}]
stood = ws3.turn("I look around.")
check("...and the next line kills nothing again", stood is True and kills3 == kills2 + 1 and kills(store3) == kills3 and ws3.combat is None, (stood, kills(store3), kills3, kills2))

# ---- a defeat whose goddess line fails is a death that stands, the player waking once
c = ws3.player.character
c.health = 1
deaths0 = c.deaths
fight(ws3, name="great wolf", level=40, rank="elite", hp=10 ** 6, damage=10 ** 4)
FAIL["titles"] = {"GoddessLine"}
raised0 = FAIL["raised"]
for _ in range(6):
    stood = ws3.turn("I attack the great wolf")
    if ws3.combat is None or stood is not True:
        break
FAIL["titles"] = set()
check("(f518) the goddess line's failure was raised by the stand-in answering", FAIL["raised"] > raised0, FAIL["raised"] - raised0)
c2 = store3.load_player().character
check("a defeat whose goddess line fails is a death that stands, the player awake once, nothing waiting", stood is True and c2.deaths == deaths0 + 1 and ws3.combat is None
      and store3.unshown() == {} and "goddess" in [o.kind for o in ws3.line_untold], (stood, c2.deaths, deaths0, ws3.combat, [o.kind for o in ws3.line_untold]))

failing()
check("(f518) the failing stand-in is taken away, the stub answering again", not failing.live() and simlib.below().chat == stub.chat)
g3.close()
check("nothing of it stays in the process at the end", simlib.residue() == {}, simlib.residue())
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
