"""(f390) Two things a night's runs showed that nothing caught.
- A run spent four hours (1,086 turns) at the mouth of a mine: a world event had closed the wild above it, the mouth's only way out ran
  through that wild, and every step out was refused, 741 times, with nothing said of when it would open. A closure stops people going
  in; it never shuts in whoever is already there. A way that is closed now says how long it will stay so.
- On a warmer night the narrator slipped words of other alphabets into one passage in a hundred ("One keeps his head down, 그의 gaze
  fixed on the ground"; "it лишь skims across"). The gateway sends such an answer back like any other it cannot accept."""
import random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import ui.console as uc
NOTES = []
for f in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
import llm.gateway as gw
from engine import guard, mapview, pulse
from llm.contracts import Narration
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/way_out_test", ignore_errors=True)
store = CampaignStore.open_or_create("way_out_test")
store.meta.seed = 3; store.meta.minutes = 600; store.meta.turn = 1; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="trading_square", guild_rank="E"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.rng = random.Random(7)          # the journeys below take the same time every run: the closure's days left are checked against it
ws.ensure_dungeons()
d = store.load_dungeons()[0]
wild, mouth = d["place"], d["entrance"]

# ---- the way out
check("a dungeon's mouth lets out onto the wild above it, closed or not", {mouth, wild} <= pulse.way_out(ws.world, mouth), pulse.way_out(ws.world, mouth))
inner = next(p for p in ws.world.places.values() if p.parent)
check("...and a place lets out through every place it lies within", {inner.id, inner.parent} <= pulse.way_out(ws.world, inner.id))
check("...but nowhere else", "trading_square" not in pulse.way_out(ws.world, mouth))

def close(place: str, days: float) -> None:
    state = store.load_world_state()
    state.setdefault("effects", []).append({"kind": "closed", "place": place, "until": ws.minutes + int(days * 1440),
                                            "text": "The Weeping Standing Stone", "cause": "The Weeping Standing Stone"})
    store.save_world_state(state)

close(wild, 3)
town = mapview.top_of(ws.world, "trading_square")
ws.player.location = mouth
NOTES.clear()
ws.halted = False
ws.travel_route(wild, "We climb back out.")
check("standing at the mouth of a dungeon beneath a closed wild, the player can still climb out", ws.player.location == wild and not ws.halted,
      (ws.player.location, NOTES))
check("...and is told the way is shut to anyone going in, not to them", any("nothing stops you leaving" in n for n in NOTES), NOTES)
ws.player.location = mouth
ws.halted = False
ws.travel_route(town, "We head back to town.")
check("...and can go on through it to anywhere", ws.player.location != mouth, (ws.player.location, NOTES))
dest = town
ws.player.location = dest
NOTES.clear()
ws.halted = False
ws.travel_route(mouth, "Back down the mine.")
check("from outside, the closed wild still bars the way in", ws.player.location == dest and ws.halted, (ws.player.location, NOTES))
check("...and says how long it will stay closed, in days", any(re.search(r"is closed: The Weeping Standing Stone\. It should open again in about [1-3] days?\.$", n)
                                                                 for n in NOTES), NOTES)
close(wild, 200)
NOTES.clear()
ws.travel_route(mouth, "Back down the mine.")
check("...or that nobody can say, when it is closed for good", any("Nobody can say when it will open again" in n for n in NOTES), NOTES)

# ---- words of another alphabet
check("a word in Korean in an English line is found", guard.foreign(["One keeps his head down, 그의 gaze fixed on the ground"]) == "그의")
check("...and in Japanese, even against a comma", guard.foreign(["A guard pivots slightly,彼の boots scuffing"]) == "彼の")
check("...and in Russian", guard.foreign(["it лишь skims across a seam in the scales"]) == "лишь")
check("Latin letters with marks, money signs and dashes are English enough", guard.foreign(["Şükrü at the café paid 0₲ 0Ş 60₵ — fair"]) == "")
check("a name the request itself carries is not the model losing its language", guard.foreign(["Борис nods."], "Ask Борис about the road.") == "")

answers = iter(['{"text": "One keeps his head down, 그의 gaze fixed on the ground."}', '{"text": "One keeps his head down, his gaze fixed on the ground."}'])
SENT = []
def chat(**k):
    SENT.append(k["messages"])
    return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=next(answers)))
gw._client = types.SimpleNamespace(chat=chat)
got = gw.generate("narrate", "You narrate.", "The prisoners walk at your side.", Narration)
check("the gateway sends such a passage back, and the player reads the one written again", got.text == "One keeps his head down, his gaze fixed on the ground.", got.text)
check("...told to write in English, the word named", len(SENT) == 2 and "English" in SENT[1][-1]["content"] and "그의" in SENT[1][-1]["content"], SENT[-1][-1:])

shutil.rmtree("saves/way_out_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
