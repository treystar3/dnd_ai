"""(f449) A turn survives any fault, and the game goes on. The owner's night of 2026-11-01: two tries of one call timed out (four minutes),
the third failed in a way the gateway did not count as a failed try, and the error climbed out of the turn to "Something went wrong and
the game has to stop", with nothing written down. Now: anything a model call raises is one failed try (llm/gateway.py), one timeout ends
the tries, an exception raised on purpose (core/interrupts.py: the replayer's Parted) passes through untouched, and the refusal kind tells
a server down from every answer refused. Any exception a turn or a pane command raises rolls the turn back (the save and the scene),
is told to the player in the narrator's words (the second time the same line fails that way, told to be left), and goes to
logs/crash.log with the line and the place (engine/crashlog.py). main.py writes there too for what still ends the game. With it, the
smaller things the same logs showed: a stage direction in brackets taken out of a line (engine/hygiene.py unstage), a trade's doing bound
to the kind of place it belongs to (doings.yaml `at`: no furrow walked in the town square), and attacking a creature that lives here but
is not in view goes looking for it instead of "There's nothing here to fight"."""
import json, random, re, shutil, sys, types
from pathlib import Path
sys.path.insert(0, ".")
import httpx
import simlib
stub = simlib.Stub("warrior", 9)
simlib.install(stub)
import config
from ui import console
SHOWN = []
for fn in ("narrate", "say", "note", "ledger", "out"):
    setattr(console, fn, lambda *a, _fn=fn, **k: SHOWN.append((_fn, str(a[0]) if a else "")))
console.panel = lambda *a, **k: False
from core.interrupts import Interrupt
from llm import gateway
from llm.contracts import ActionIntent, ActionPlan
from llm.gateway import LLMError, generate
from engine import crashlog, data_check, doings, encounters, failures, hygiene, refusals, turnlog
from storage import statehash
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from world.loader import campaign_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

SAVE = "turn_survives_449"
shutil.rmtree(f"saves/{SAVE}", ignore_errors=True)
Path(f"saves/{SAVE}").mkdir(parents=True)
config.CRASH_LOG_PATH = f"saves/{SAVE}/crash.log"
config.TURN_LOG_PATH = f"saves/{SAVE}/turns.jsonl"
config.TURN_LOG = True

check("the data (failure lines, doings' places, hygiene's reasons) checks clean", data_check.check() == [], data_check.check()[:3])

# ---- the gateway: anything the call raises is a failed try; one timeout ends the tries; an Interrupt passes through
real = gateway._client
calls = []
def client(fn):
    gateway._client = types.SimpleNamespace(chat=fn, embed=getattr(real, "embed", None))

def boom(**k):
    calls.append("boom"); raise RuntimeError("the client fell over")
client(boom); calls.clear(); n0 = len(refusals.SESSION)
try:
    generate("interpret_action", "s", "u", ActionPlan, max_tokens=50)
    got = None
except LLMError as e:
    got = e
check("an error the gateway did not list is a failed try, not the end of the game: three tries, then the turn's own failure",
      isinstance(got, LLMError) and len(calls) == 3 and getattr(got, "transport", None) is True, (type(got).__name__, len(calls)))
check("...and the refusal filed is the server's failure", refusals.SESSION[n0:] and refusals.SESSION[-1]["kind"] == "model_down", refusals.SESSION[n0:])

def slow(**k):
    calls.append("slow"); raise httpx.ReadTimeout("stalled")
client(slow); calls.clear()
try:
    generate("interpret_action", "s", "u", ActionPlan, max_tokens=50)
    got = None
except LLMError as e:
    got = e
check("one timeout ends the tries: a second request would only queue behind the stalled one", isinstance(got, LLMError) and len(calls) == 1, len(calls))

class Stop(Interrupt):
    pass
def stop(**k):
    calls.append("stop"); raise Stop("the replay parted")
client(stop); calls.clear()
try:
    generate("interpret_action", "s", "u", ActionPlan, max_tokens=50)
    got = None
except Stop as e:
    got = e
except LLMError as e:
    got = e
check("an exception raised on purpose passes through untouched, on the first try", isinstance(got, Stop) and len(calls) == 1, (type(got).__name__, len(calls)))

def refused(**k):
    calls.append("refused"); return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content="not json at all"))
client(refused); calls.clear(); n0 = len(refusals.SESSION)
try:
    generate("interpret_action", "s", "u", ActionPlan, max_tokens=50)
except LLMError as e:
    got = e
check("every answer refused is the other kind of trouble: the refusal filed says bad_answer, not an outage",
      getattr(got, "transport", None) is False and refusals.SESSION[n0:] and refusals.SESSION[-1]["kind"] == "bad_answer", refusals.SESSION[n0:])
gateway._client = real

# ---- the turn: a fault inside it rolls the turn back, is told in the narrator's words, and is written down
store = CampaignStore.open_or_create(SAVE)
store.meta.seed = 9; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(9))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, campaign_world(), load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("parth")
coins0 = ws.player.character.coins
digest0 = statehash.digest(store)["all"]

def broken_handle(text):
    ws.player.character.coins += 100                     # a write the fault must not leave behind
    ws.store.save_player(ws.player)
    raise KeyError("road_3db1089b")
ws.handle = broken_handle
SHOWN.clear()
stood = ws.turn("go the te watchmen")
check("a turn the game itself breaks on is not taken, and does not end the game", stood is False and ws.last_crash and ws.last_failure.startswith("KeyError"),
      (stood, ws.last_failure))
check("...the save is rolled back whole and the scene put back to match", statehash.digest(store)["all"] == digest0 and ws.player.character.coins == coins0
      and store.load_player().character.coins == coins0, (ws.player.character.coins, coins0))
entry = crashlog.last()
log = Path(config.CRASH_LOG_PATH)
check("...and the fault is written to logs/crash.log with its traceback, the line and the place", entry and entry["where"] == "turn"
      and "KeyError" in entry["error"] and entry.get("text") == "go the te watchmen" and entry.get("place") == "parth" and log.exists()
      and "Traceback" in log.read_text(encoding="utf-8") and "go the te watchmen" in log.read_text(encoding="utf-8"), entry)
line1 = ws.failed_line("go the te watchmen")
check("the player reads a line in the narrator's words, never the machinery", line1 in failures.F["turn_not_taken"]
      and not failures.MACHINERY.search(line1), line1)
ws.turn("go the te watchmen")
line2 = ws.failed_line("go the te watchmen")
check("...and the same line failing twice running is told to be left", line2 in failures.F["turn_not_possible"] and not failures.MACHINERY.search(line2), line2)
check("the night tool's list of hesitations holds both kinds", set(failures.F["turn_not_possible"]) <= set(failures.lines()))

class Parted(Interrupt):
    pass
def parting(text):
    raise Parted("the replay parted")
ws.handle = parting
try:
    ws.turn("look")
    passed = False
except Parted:
    passed = True
check("an exception raised on purpose passes out of the turn untouched", passed)

# the loop goes on after a fault, and the turn log says the game crashed, not the model
del ws.handle
def broken_cmd(text):
    raise ValueError("a pane button's fault")
ws.command = broken_cmd
script = ["#stats", "quit"]
console.ask = lambda *a, **k: script.pop(0) if script else "quit"
SHOWN.clear()
try:
    ws.run()
    ran = True
except Exception as e:
    ran = f"{type(e).__name__}: {e}"
check("a pane command's fault is rolled back and the loop goes on to the next line", ran is True and crashlog.last()["where"] == "command"
      and any(t in failures.lines() for _, t in SHOWN), (ran, crashlog.last(), SHOWN[-3:]))
rows = [json.loads(l) for l in Path(config.TURN_LOG_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
crashed = [r for r in rows if r.get("crashed")]
check("...and the turn log marks it as the game's fault, apart from the model's", crashed and all(not r.get("model_failed") for r in crashed)
      and "ValueError" in crashed[-1]["crashed"], [{k: r.get(k) for k in ("text", "crashed", "model_failed")} for r in rows[-3:]])
del ws.command

# ---- main.py still writes the faults that end the game
import main as game_main
n0 = len(crashlog.SESSION)
def dies():
    raise RuntimeError("before any campaign")
try:
    game_main.guarded(dies, None)
except RuntimeError:
    pass
check("a fault outside a turn is written down before the game stops", len(crashlog.SESSION) == n0 + 1 and crashlog.last()["where"].startswith("outside a turn"),
      crashlog.last())

# ---- the smaller things the same logs showed
spoken = ("The Ossuary isn't exactly known for being an easy walk.\n(Lammer looks toward the stranger.)\n"
          "Does your guild usually send you into places with a bit of a reputation?")
n0 = hygiene.REPAIRS["stage"]
out = hygiene.unstage(spoken)
check("a stage direction in brackets is taken out of a line, and counted as a repair", "(" not in out and "easy walk." in out
      and "Does your guild" in out and hygiene.REPAIRS["stage"] == n0 + 1, out)
check("...while an aside that is part of the sentence stays", hygiene.unstage("Bring it (as you asked) by dusk.") == "Bring it (as you asked) by dusk.")
src = Path("ui/console.py").read_text(encoding="utf-8")
check("...and the story's lines pass through it on the way to the screen", "hygiene.unstage(" in src)

picks = {doings.pick("farmer", "midday", random.Random(s), place_type="town") for s in range(60)}
field = {doings.pick("farmer", "midday", random.Random(s), place_type="fields") for s in range(60)}
check("a farmer in the town square is never walking a furrow there; in the fields they may be", "walking a furrow" not in picks and "walking a furrow" in field
      and picks, (picks, field))
check("...and the data check knows the kinds of place `at` may name", any("at" in p for p in doings.problems({"farmer"}, {"midday"}, {"town"})))

wild = next((p.id for p in ws.world.places.values() if p.danger and p.parent == "parth"), None) or \
    next(p.id for p in ws.world.places.values() if p.danger and not p.parent)
ws.enter(wild)
ws.wildlife = None
roster = encounters.ensure_roster(store, ws.world, wild)
name = ws.world.bestiary[roster[0]].name
SHOWN.clear()
ws.on_attack(ActionIntent(kind="attack", target=name), f"attack {name}")
check("attacking a creature that lives here but is not in view goes looking for it, instead of 'nothing here to fight'",
      any(k == "note" and "You go looking" in t and name.lower() in t for k, t in SHOWN) and not any("nothing here to fight" in t for _, t in SHOWN)
      and (ws.combat is not None or any(k == "narrate" for k, _ in SHOWN)), SHOWN[:4])
ws.combat = None; ws.wildlife = None
SHOWN.clear()
ws.on_attack(ActionIntent(kind="attack", target="a thing that lives nowhere"), "attack the thing")
check("...and a creature nothing here knows of still gets the plain answer", any("nothing here to fight" in t for _, t in SHOWN), SHOWN[:3])

# ---- the shape of the catches, in the source
world_src = Path("scenes/world.py").read_text(encoding="utf-8")
check("the turn's catch lets an Interrupt through before it catches everything else",
      world_src.index("except Interrupt:\n            raise") < world_src.index("except Exception as e:\n            # (f449)"))
gw = Path("llm/gateway.py").read_text(encoding="utf-8")
check("...and so does the gateway's", gw.index("except Interrupt:\n            raise") < gw.index("except Exception as e:\n            # A timeout"))
sys.path.insert(0, "tools")
import rerun
check("the replayer's Parted is such an exception", issubclass(rerun.Parted, Interrupt))

store.close()
shutil.rmtree(f"saves/{SAVE}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
