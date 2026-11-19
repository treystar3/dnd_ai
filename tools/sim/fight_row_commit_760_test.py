"""(f760) The fight's row is written with every operation's commit: the fight in memory equals its row when an operation ends (found
by the code audit, pane-commands-2: a level 8 mage spent a point on constitution and one on intelligence from the Character pane in
the middle of a fight; the bars rose, but only the fighter in memory had them, and the next typed line, which resumes the fight from
its row when its operation stands down to ask the model, put back con 20, int 32 and the old maximums, as did closing and opening the
save, and as did #allocate answered yes). The kind is any handler or telling that changes the fight in memory inside an operation
and does not save the row; the second case here has no attribute in it: the opening's telling and a round's telling note what was
read of the fight and which ground was told after the row was last written, and a game closed straight after forgot them. Controls:
a command that fails at its last drawing step leaves row and memory as they were, and a won fight leaves no row. The watch: at the
end of every input under the suite's switch, a fight out of step with its row is counted and the last few kept. Every line goes
through play().
Run: python tools/sim/fight_row_commit_760_test.py"""
import json
import shutil
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace as NS
sys.path.insert(0, ".")
import config
LOGS = Path(tempfile.mkdtemp(prefix="fight_row_commit_"))
config.CRASH_LOG_PATH = str(LOGS / "crash.log")              # the control's fault is this test's, not the game's log
config.TURN_LOG_PATH = str(LOGS / "turns.jsonl")
import simlib
stub = simlib.Stub("mage", 3)
simlib.install(stub)
stub.bot = NS(combat_choice=lambda: {"kind": "attack", "target": "e1"})
SHOWN = simlib.quiet_console()
from ui import console as _console
for _n in ("out", "status_block", "combat_state", "combat_panel", "show_header", "debug", "show_player_block", "show_inventory"):
    if hasattr(_console, _n):
        _console.put(_n, lambda *a, **k: None)
from engine import combat, inventory, operation, pools
from scenes.world import WorldScene
from services.fight import FightService
from storage import saves, worldrow

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


REQ, FAIL = [], {"on": False}
real = simlib.below()


def chat(**k):
    if k["format"].get("title") == "Narration":
        REQ.append(k["messages"][-1]["content"])
        if FAIL["on"]:
            raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


spy = simlib.stand_in(chat=chat, name="fight_row_commit_spy")


def apart(ws) -> list[str]:
    """Where the fight in memory and its row differ, read here by the test itself."""
    raw = ws.store.load_combat()
    if ws.combat is None:
        return ["a row with no fight"] if raw else []
    if raw is None:
        return ["a fight with no row"]

    def walk(a, b, path=""):
        if isinstance(a, dict) and isinstance(b, dict):
            return [p for k in sorted(set(a) | set(b)) for p in walk(a.get(k), b.get(k), f"{path}.{k}")]
        if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
            return [p for i, (x, y) in enumerate(zip(a, b)) for p in walk(x, y, f"{path}[{i}]")]
        return [] if a == b else [path]
    return walk(json.loads(ws.combat.to_json()), json.loads(raw))[:8]


def row_fighter(ws):
    return FightService.resume(ws.store.load_combat())[0].player


def fresh_parts(ws, p) -> list[str]:
    """The character's own parts of a fighter that a fighter built from the character now would not have."""
    c = ws.player.character
    f = combat.fighter_from_character(c, "player")
    return [k for k, a, b in (("attrs", p.attrs, f.attrs), ("max_hp", p.max_hp, f.max_hp), ("max_mana", p.max_mana, f.max_mana),
                              ("ward", round(p.ward, 6), round(f.ward, 6))) if a != b]


def open_game(name: str, hp: int = 5000):
    g = simlib.campaign(name, cls="mage", seed=4, location="south_fields")
    ws = g.scene
    ws.enter("south_fields")
    c = ws.player.character
    c.level = 8
    c.unspent_points = 6
    inventory.add(c.inventory, inventory.make_good("healing_draught", 2), 99)
    pools.fill_missing(c)
    g.store.save_player(ws.player)
    creature = ws.world.bestiary["wolf"]
    foe = combat.fighter_from_creature(creature, 4, "normal", "e1", name="wolf 1")
    foe.max_hp = foe.hp = hp
    ws.wildlife = (creature, [foe])
    stub.plan = [{"kind": "attack", "target": "wolf"}]
    ws.play("I attack the wolf.")                              # the fight begins from a typed line
    stub.plan = None
    return g, ws


def watched(store) -> int:
    return int((getattr(store, "fight_watch", None) or {}).get("count", -1))


# ---- 1. the case that found it: two points from the pane, then the next typed line
g, ws = open_game("fight_row_commit_a")
check("(a fight is on)", ws.combat is not None and ws.store.load_combat() is not None)
cast = ws.player.character.casting_attribute or "intelligence"
ws.play("#attradd constitution")
check("#attradd constitution in a fight: the row is the fight in memory", ws.stood is True and not apart(ws), apart(ws))
ws.play(f"#attradd {cast}")
c = ws.player.character
check("...and after a second point: the row's fighter has what the character has",
      not apart(ws) and row_fighter(ws).attrs["constitution"] == c.attributes.constitution == 21
      and row_fighter(ws).attrs[cast] == getattr(c.attributes, cast) == 33, (apart(ws), row_fighter(ws).attrs, c.attributes))
ws.play("I attack the wolf.")
p = ws.combat.fight.player
check("the next typed line keeps them: the fighter is con 21, int 33 with the character's maximums",
      p.attrs["constitution"] == 21 and p.attrs[cast] == 33 and not fresh_parts(ws, p), (p.attrs, fresh_parts(ws, p), p.max_hp, p.max_mana))
check("...and the row is the fight in memory", not apart(ws), apart(ws))

# a control: a command that fails at its last drawing step leaves row and memory as they were
row0, con0, points0 = ws.store.load_combat(), c.attributes.constitution, c.unspent_points
fighter_con0 = ws.combat.fight.player.attrs["constitution"]
real_command = WorldScene.command


def broken(self, text, *a, **k):
    if text == "#character" and operation.current() is not None:
        raise RuntimeError("the character pane could not be drawn")
    return real_command(self, text, *a, **k)


WorldScene.command = broken
try:
    ws.play("#attradd constitution")
finally:
    WorldScene.command = real_command
c = ws.player.character
check("a point whose pane fails to draw is not spent: the command did not stand",
      ws.stood is False and c.attributes.constitution == con0 and c.unspent_points == points0, (ws.stood, c.attributes.constitution, c.unspent_points))
check("...the row is as it was, and the fight in memory is the row",
      ws.store.load_combat() == row0 and not apart(ws) and ws.combat.fight.player.attrs["constitution"] == fighter_con0, apart(ws))
check("the watch saw no fight out of step at the end of any input", watched(ws.store) == 0, getattr(ws.store, "fight_watch", None))

# the same two points, then the save closed and opened straight after
g.close()
g, ws = open_game("fight_row_commit_b")
ws.play("#attradd constitution")
ws.play(f"#attradd {cast}")
ws = g.reopen()
p = ws.combat.fight.player if ws.combat else None
check("closed and opened straight after the two points: the fight resumes with con 21, int 33 and the character's maximums",
      p is not None and p.attrs["constitution"] == 21 and p.attrs[cast] == 33 and not fresh_parts(ws, p),
      (p and p.attrs, p and fresh_parts(ws, p)))
g.close()

# through #allocate and its question answered yes
g, ws = open_game("fight_row_commit_c")
ws.play("#allocate con 2 int 2")
ws.play("yes")
c = ws.player.character
check("#allocate con 2 int 2 answered yes in a fight: the row's fighter has the points",
      c.attributes.constitution == 22 and not apart(ws) and row_fighter(ws).attrs["constitution"] == 22
      and row_fighter(ws).attrs["intelligence"] == c.attributes.intelligence, (c.attributes, apart(ws)))
ws.play("I attack the wolf.")
p = ws.combat.fight.player
check("...and the next typed line keeps them", p.attrs["constitution"] == 22 and not fresh_parts(ws, p) and not apart(ws),
      (p.attrs, fresh_parts(ws, p), apart(ws)))
g.close()

# ---- 2. the second case, no attribute in it: what the opening's telling noted
g, ws = open_game("fight_row_commit_d")
f = ws.combat.fight
check("(the opening was told, and noted what was read and which ground was told)", f.shown and f.ground_told, (f.shown, f.ground_told))
check("the input that opens a fight ends with what its telling noted in the row", not apart(ws), apart(ws))
shown0 = list(f.shown)
ws = g.reopen()
check("...closed and opened: the fight still has what was shown and the ground told",
      ws.combat is not None and ws.combat.fight.shown == shown0 and ws.combat.fight.ground_told, ws.combat and (ws.combat.fight.shown, ws.combat.fight.ground_told))
REQ.clear()
ws.play("I attack the wolf.")
rounds = [r for r in REQ if "THE GROUND NOW" in r or "ALREADY SHOWN" in r]
check("...and the next round's request lists what was shown", rounds and "ALREADY SHOWN IN THIS FIGHT" in rounds[0]
      and all(s in rounds[0] for s in shown0), [r[:300] for r in REQ])
check("the watch saw no fight out of step", watched(ws.store) == 0, getattr(ws.store, "fight_watch", None))
g.close()

# a round's telling: a fight whose opening was never told is told its ground by the first round, and that is kept
FAIL["on"] = True
g, ws = open_game("fight_row_commit_e")
FAIL["on"] = False
check("(the opening could not be told: no ground was told)", ws.combat is not None and ws.combat.fight.ground_told == {}, ws.combat and ws.combat.fight.ground_told)
ws.play("I attack the wolf.")
told = dict(ws.combat.fight.ground_told)
check("(the round's telling was given the ground and noted it)", told, told)
check("the round's telling: what it noted is in the row when the input ends", not apart(ws), apart(ws))
ws = g.reopen()
check("...closed and opened: each zone it told is still marked told",
      ws.combat is not None and set(told) <= set(ws.combat.fight.ground_told), ws.combat and ws.combat.fight.ground_told)
g.close()

# a control: the winning round leaves no fight row
SHOWN.clear()
g, ws = open_game("fight_row_commit_f", hp=1)
if ws.combat is not None:
    ws.play("I attack the wolf.")
won = any(t.startswith("Victory") for _k, t in SHOWN)
check("a won fight leaves no row and no fight", won and ws.combat is None and ws.store.load_combat() is None,
      (won, ws.combat, (ws.store.load_combat() or "")[:80]))
check("...and the watch saw nothing out of step", watched(ws.store) == 0, getattr(ws.store, "fight_watch", None))
g.close()

# ---- 3. the watch: a fight left out of step at an input's end is counted, the last few kept
g, ws = open_game("fight_row_commit_g")
step = getattr(ws, "fight_out_of_step", None)
check("in step after a typed line: the scene's own comparison finds nothing", step is not None and step() == [], step and step())
for i in range(9):
    with ws.input("(a probe)", "opening"):
        ws.combat.fight.player.hp -= 1                   # changed in memory, and no operation commits to write it
w = getattr(ws.store, "fight_watch", None) or {}
check("an input that ends with the fight out of step is counted, every time", w.get("count") == 9, w)
kept = w.get("last") or []
check("...the last few are kept, no more, each with where it differs",
      0 < len(kept) < 9 and all(any("hp" in x for x in e.get("apart", [])) for e in kept), kept)
check("...and the scene's comparison names the same place", step is not None and any("hp" in x for x in step()), step and step())
worldrow.WATCH_STALE = False
with ws.input("(a probe)", "opening"):
    pass
check("with the watch off (shipped play) nothing is noted", (getattr(ws.store, "fight_watch", None) or {}).get("count") == 9, w)
worldrow.WATCH_STALE = True
ws.play("#stats")
check("the next operation's commit writes it: in step again", step is not None and step() == [] and not apart(ws), apart(ws))
g.close()

spy()
for name in "abcdefg":
    saves.drop(f"fight_row_commit_{name}")
shutil.rmtree(LOGS, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
