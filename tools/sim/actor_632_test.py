"""(f632) The actor's context and the clock's view (engine/actor.py; docs/design/20_phase3_plan.md). A scene has one actor: the
player's record, the dice, where the text goes, the clock and the turn's context. The scene's `player` is a view over it, and so
is the party's and the fight's, so no rebind of the record (a reload after a failed operation, the pulse, an arc's end) can leave
one of them holding the old one. The actor is bound inside the scene's five entries (open_world, run, turn, handle, command) and
the pulse, and the one bound before is back on the way out; with none bound the process's own dice and screen answer, as before.
The clock is a view with no state over the save's meta, and its advance is the one writer of the time in play.
Run: python tools/sim/actor_632_test.py"""
import ast
import re
import shutil
import sys
import types
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as console
from engine import actor, pulse, streams
from llm.gateway import LLMError
from scenes import combat_scene
from scenes.world import WorldScene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


class Page(console.Channel):
    def __init__(self):
        self.text = []

    def write(self, text: str, end: str = "\n") -> None:
        self.text.append(text + end)


# ---- with no actor bound
none = actor.current()
check("with no actor bound the process's own answers: its dice, the console's channel as it stands, no player",
      none is actor.PROCESS and none.dice is streams.DEFAULT and none.out is None and none.player is None and streams.current() is streams.DEFAULT
      and console.channel() is console.STDOUT)

g = simlib.campaign("actor_632", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/actor_632/turns.jsonl"
ws.enter("parth")

# ---- the scene's actor
mine = ws.actor
check("a scene has one actor, the same each time: its player, the process's dice, the console's channel, a clock and the turn's context",
      isinstance(mine, actor.ActorContext) and ws.actor is mine and mine.dice is streams.DEFAULT and mine.out is None
      and isinstance(mine.clock, actor.Clock) and mine.turn is actor.turn_of(ws))
check("the scene's player is the actor's, and the scene keeps no record of its own", ws.player is mine.player and "player" not in ws.__dict__
      and isinstance(WorldScene.__dict__["player"], property))
check("the acting character is the actor's", ws.acting == mine.character_id == ws.player.character.id)
check("it sits under no name the session sweeps or rolls back", "actor" in ws.__dict__ and "actor" not in WorldScene.ROLLED)

# ---- a rebind reaches everything that holds the player
party, fight = ws.party_service, combat_scene.service_of(ws)
was = ws.player
with ws.operation("test", "a failing step") as op:
    raise LLMError("the model failed")
check("(a failed operation reloads the player: a new record)", op.state == "rolled_back" and ws.player is not was)
check("the actor is the one it was, holding the new record", ws.actor is mine and mine.player is ws.player)
check("a party's service and a fight's made before the reload stand on the new record, not the old one",
      party.player is ws.player and fight.player is ws.player and party.members is ws.player.party)
check("...and who fights as a player is the new record's character", fight.characters == [ws.player.character]
      and fight.characters[0] is ws.player.character and fight.characters[0] is not was.character)
second = simlib.stood_beside(ws, "second")
del ws.player_of
ws.player = second
check("a record put in the scene's place is the actor's, and the acting character is its", mine.player is second and ws.acting == "second"
      and party.player is second and fight.player is second)
ws.player = store.load_player()
check("...and back", ws.acting == "player" and party.player is ws.player)
stand_in = combat_scene.service_of(types.SimpleNamespace(player=second))
bare = combat_scene.service_of(types.SimpleNamespace())
check("a stand-in for a scene, with a record and no actor, gives the fight's service the record it has; one with neither, none",
      stand_in.player is second and stand_in.characters == [second.character] and bare.player is None and bare.characters == [])

# ---- bound inside each entry, and the one before back after
seen = {}


def spy(name, real):
    def inner(*a, **k):
        seen.setdefault(name, []).append(actor.current())
        return real(*a, **k)
    return inner


ENTRIES = ("open_world", "run", "turn", "handle", "command", "run_pulse")
real_catch_up, real_ask = pulse.catch_up, console.ask
simlib.quiet_console()
try:
    pulse.catch_up = spy("run_pulse", real_catch_up)
    with ws.operation("test", "the pulse", world=True):
        ws.run_pulse()
    ws.begin_line = spy("turn", ws.begin_line)
    stub.plan = [{"kind": "look"}]
    ws.turn("I look around.")
    ws.read_line = spy("handle", ws.read_line)            # handle's alone: turn reads the line in two halves
    stub.plan = [{"kind": "look"}]
    ws.handle("I look around.")
    ws.show_stats = spy("command", ws.show_stats)
    ws.command("#stats")
    store.find_operation = spy("open_world", store.find_operation)
    ws.open_world()
    del store.find_operation
    console.ask = spy("run", lambda *a, **k: "quit")
    ws.run()
finally:
    pulse.catch_up, console.ask = real_catch_up, real_ask
    del ws.begin_line, ws.read_line, ws.show_stats
for name in ENTRIES:
    check(f"the actor is bound while {name} runs", seen.get(name) and all(a is mine for a in seen[name]), seen.get(name))
check("every entry says it binds", all(getattr(getattr(WorldScene, n), "binds_actor", False) for n in ENTRIES),
      [n for n in ENTRIES if not getattr(getattr(WorldScene, n), "binds_actor", False)])
check("after them no actor is bound", actor.current() is actor.PROCESS)
main = ast.parse((Path(__file__).resolve().parent.parent.parent / "main.py").read_text(encoding="utf-8"))
called = {n.func.attr for n in ast.walk(main) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
          and isinstance(n.func.value, ast.Name) and n.func.value.id == "scene"}
check("the game goes into a scene by one of them alone (main.py): nothing of a scene runs there with no actor bound", called == {"run"}, called)

# ---- the actor's dice and page answer while it is bound, and the process's after
page, dice = Page(), streams.Streams()
mine.out, mine.dice = page, dice
inside = {}
try:
    with actor.bind(mine):
        inside["dice"] = streams.current() is dice and streams.get("scene") is dice.get("scene") and streams.get("scene") is not streams.DEFAULT.get("scene")
        inside["channel"] = console.channel() is page
        console.print("a line for this actor's page")
finally:
    mine.out, mine.dice = None, streams.DEFAULT
check("while an actor with dice and a page of its own is bound, the dice asked for are its and the console's text goes to its page",
      inside.get("dice") and inside.get("channel") and page.text == ["a line for this actor's page\n"], (inside, page.text))
check("...and after it the process's again", streams.current() is streams.DEFAULT and console.channel() is console.STDOUT
      and streams.get("scene") is streams.DEFAULT.get("scene"))
page, over = Page(), Page()
mine.out = page
ws.show_stats = lambda: console.print("the sheet")        # what the command shows, through the console's one way out
try:
    with actor.bind(mine):
        with console.use(over):                           # a channel put over the actor's (an operation's held lines, a tap)
            ws.command("#stats")
        told = (bool(over.text), list(page.text))
        ws.command("#stats")
finally:
    mine.out = None
    del ws.show_stats
check("an entry run inside a bound one binds nothing again: a channel put over the actor's in between keeps the text",
      told == (True, []) and over.text == ["the sheet\n"] and page.text == ["the sheet\n"], (told, over.text, page.text))
try:
    with actor.bind(mine):
        raise KeyError("a fault inside")
except KeyError:
    pass
check("a fault inside leaves no actor bound", actor.current() is actor.PROCESS and streams.current() is streams.DEFAULT)

# ---- two campaigns taken in turn on one thread
g2 = simlib.campaign("actor_632b", cls="warrior", seed=4, location="parth")
ws2 = g2.scene
ws2.enter("parth")
order = []
with actor.bind(ws.actor):
    order.append(actor.current() is ws.actor)
    real2 = ws2.begin_line
    ws2.begin_line = lambda: order.append(actor.current() is ws2.actor) or real2()
    stub.plan = [{"kind": "look"}]
    ws2.turn("I look around.")
    del ws2.begin_line
    order.append(actor.current() is ws.actor)
order.append(actor.current() is actor.PROCESS)
check("two scenes each see their own actor inside an entry, the one before after it, and none at the end", order == [True, True, True, True], order)
check("each scene's actor is its own, with its own player, clock and turn", ws2.actor is not ws.actor and ws2.actor.player is ws2.player
      and ws2.actor.turn is not ws.actor.turn and ws2.actor.clock is not ws.actor.clock)

# ---- the clock
clk = ws.actor.clock
check("the clock reads the save's time", clk.minutes == store.meta.minutes == ws.minutes)
store.meta.minutes = 7777
check("...as a test sets it", clk.minutes == 7777 and ws.minutes == 7777)
store.meta = store.meta.model_copy(update={"minutes": 8888})
check("...and when the meta is replaced whole (a reload, an asked restore)", clk.minutes == 8888 and ws.minutes == 8888)
from engine import clock as calendar
with ws.operation("test", "time passes") as op:
    ws.advance(1440)
check("time passing in play moves it, the day with it", op.state == "committed" and clk.minutes == 8888 + 1440
      and store.meta.day == calendar.day(8888 + 1440), (clk.minutes, store.meta.day))
before, old = clk.minutes, store.meta
with ws.operation("test", "time passes, then the step fails") as op:
    ws.advance(60)
    moved = clk.minutes
    raise LLMError("the model failed")
check("a failed operation's reload takes its time back, and the clock reads the meta put in the old one's place",
      op.state == "rolled_back" and moved == before + 60 and store.meta is not old and clk.minutes == before == ws.minutes
      and store.meta.day == calendar.day(before), (moved, before, clk.minutes, store.meta is old))
ROOT = Path(__file__).resolve().parent.parent.parent
writers = []
for folder in ("engine", "scenes", "services", "npc", "storage", "llm", "ui"):
    for path in sorted((ROOT / folder).rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target] if isinstance(node, ast.AugAssign) else []
            for t in targets:
                for x in ast.walk(t):
                    if isinstance(x, ast.Attribute) and x.attr in ("minutes", "day") and getattr(x.value, "attr", getattr(x.value, "id", "")) == "meta":
                        writers.append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
check("the clock is the one writer of the save's time in the game's code", writers and all(w.startswith("engine/actor.py:") for w in writers), writers)

# ---- what is left: the scene's player read by name, per directory; a count only falls
LEFT = {"scenes": 1087, "services": 63}
found = {d: sum(len(re.findall(r"\bself\.player\b", p.read_text(encoding="utf-8"))) for p in (ROOT / d).rglob("*.py")) for d in LEFT}
check("code reads `self.player` in the recorded number of places and no more (new code takes an id and asks player_of)",
      all(found[d] <= LEFT[d] for d in LEFT), found)
check("...and a count that fell is lowered here", found == LEFT, (found, LEFT))

g2.session.close()
g.session.close()
for name in ("actor_632", "actor_632b"):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
