"""(f437) When a turn could not be taken because the model failed, the page said "The world seems to hesitate - the model couldn't
produce a usable answer. Nothing has changed; try again." 4 to 8 times a run on the f425 night: machinery, and always the same words.
Now it is a line in the narrator's own voice (data/rules/failures.yaml), never the same twice running; the game is as it was; and the
turn's row in the turn log says the model failed, while nothing is counted as a refusal of what the player typed."""
import json, random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 37))
import ui.console as uc
NOTES = []
uc.note = lambda t, *a, **k: NOTES.append(str(t))
for fn in ("narrate", "say", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import data_check, failures, refusals, turnlog
from llm import gateway
from llm.gateway import LLMError
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import campaign_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/outage_line_437_test", ignore_errors=True)
world = campaign_world()
store = CampaignStore.open_or_create("outage_line_437_test")
store.meta.seed = 37; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(37))
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
store.save_player(ws.player)

real = gateway._client
def chat(**k):
    if k["format"].get("title") == "ActionPlan":
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)
gateway._client = types.SimpleNamespace(chat=chat)
real_command = ws.command
def command(text):
    if text == "#fail":
        raise LLMError("the walk's passage could not be written")
    return real_command(text)
ws.command = command

ROWS = []
real_write = turnlog._write
turnlog._write = lambda r: ROWS.append(r)
refused_before = [r["kind"] for r in refusals.SESSION]
where, clock, coins = ws.player.location, store.meta.minutes, ws.player.character.coins
script = ["I look around the square", "I look around the square", "#fail", "quit"]
uc.ask = lambda *a, **k: script.pop(0) if script else "quit"
ws.run()
gateway._client, turnlog._write = real, real_write

LINES = set(failures.lines())
shown = [n for n in NOTES if n in LINES]
check("each turn the game could not take shows one of the narrator's lines for it", len(shown) == 3, NOTES[-6:])
check("...never the old machinery", not any("hesitate" in n or "model" in n.lower() for n in NOTES), [n for n in NOTES if "model" in n.lower()])
check("...and never the same words twice running", all(a != b for a, b in zip(shown, shown[1:])), shown)
check("the game is as it was: the place, the clock, the purse", (ws.player.location, store.meta.minutes, ws.player.character.coins) == (where, clock, coins),
      (ws.player.location, store.meta.minutes))
failed = [r for r in ROWS if r.get("rolled_back")]
check("the turn log marks each one rolled back, as a model failure with its reason", len(failed) == 3 and all(r.get("model_failed") for r in failed),
      [{k: r.get(k) for k in ("text", "rolled_back", "model_failed")} for r in ROWS][-4:])
new_refusals = [k for k in [r["kind"] for r in refusals.SESSION][len(refused_before):] if k != "model_down"]
check("...and nothing is counted as a refusal of what the player typed", new_refusals == [], new_refusals)

# ---- the lines are data, checked at startup
check("the lines pass the startup check", not failures.problems() and not [p for p in data_check.check() if "failures.yaml" in p])
check("...a line that speaks of the model fails it", failures.problems({"turn_not_taken": failures.lines()[:-1] + ["The model failed. Try again."]}))
check("...and so does a short list", failures.problems({"turn_not_taken": failures.lines()[:3]}))

# ---- the night tool counts them as failed turns
sys.path.insert(0, "tools")
import nightrun
check("the night tool counts each of the lines as a failed turn", all(any(h in l for h in nightrun.HESITATIONS) for l in LINES))

store.close()
shutil.rmtree("saves/outage_line_437_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
