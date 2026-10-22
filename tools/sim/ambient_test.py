"""Ambient happenings (f331, engine/ambient.py): the ordinary day of a town, chosen by the engine with no model call - market day, a funeral,
the watch out when the stranger is wanted, a thin market - joins HAPPENING HERE for the narrator and every speaker; the narrator hears the
town's news; coming back to a town after a while away, the narrator is handed once what changed there in the meantime."""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import ambient, clock, law, pulse, truth
import scenes.world_prompts as wp

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/ambient_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("ambient_test")
store.meta.seed = 8; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square")
store.save_world_state(pulse.empty_state(ws.minutes))
DAY = 1440

def at(day, hour=12):
    return (day - 1) * DAY + (hour - clock.WAKE_HOUR) * 60          # minute 0 is the first morning's waking hour

# ---- market day, by the town's own count, in working hours
n = next(r for r in ambient.A["rules"] if r["id"] == "market_day")["when"]["market_day"]
day = next(d for d in range(2, 40) if (d + sum(map(ord, "parth"))) % n == 0)
check("market day comes round every so many days, in the working hours", any("arket day" in l for l in ambient.lines(store, world, "trading_square", at(day))))
check("...not at night", not any("arket" in l for l in ambient.lines(store, world, "trading_square", at(day, 23))))
check("...and not the day after", not any("arket" in l for l in ambient.lines(store, world, "trading_square", at(day + 1))))
check("...the line is the same all day", ambient.lines(store, world, "trading_square", at(day, 9)) == ambient.lines(store, world, "trading_square", at(day, 15)))
check("nothing is ambient in the wild", ambient.lines(store, world, "greywood", at(day)) == [])

# ---- a funeral after a death, the watch when the stranger is wanted, a thin market when prices are high
now = at(day + 1)
store.journal(now - DAY, "npc_gone", "", "x1", "Old Tam is gone: killed by wolves on the sheep hill", {"how": "killed by wolves on the sheep hill", "place": "parth"})
lines = ambient.lines(store, world, "trading_square", now)
check("someone of the town killed lately means a funeral, with their name", any("Old Tam" in l for l in lines), lines)
law.set_heat(ws.player, "parth", 50, clock.day(now))
lines = ambient.lines(store, world, "trading_square", now, ws.player)
check("a wanted stranger finds the watch out", any("watch" in l for l in lines), lines)
check("...only when the player is given", not any("watch" in l for l in ambient.lines(store, world, "trading_square", now)))
ws.player.heat = {}
st = store.load_world_state(); st["effects"] = [{"kind": "prices", "place": "parth", "value": 25, "until": now + DAY, "cause": "test"}]; store.save_world_state(st)
check("high prices make a thin, dear market", any("thin and dear" in l for l in ambient.lines(store, world, "trading_square", now)))
st["effects"] = []; store.save_world_state(st)

# ---- through the truth layer: the narrator and every speaker see the day; the narrator hears the news
store.meta.minutes = at(day)
st = store.load_world_state()
pulse.add_news(st, "The miller's cart lost a wheel on the King's Road.", "parth", store.meta.minutes - 60, ["everyone"])
store.save_world_state(st)
scene = truth.scene_of(ws)
nv = scene.view(truth.NARRATOR, "narrator")
check("the ambient line is a happening for the narrator", any("arket day" in l for l in nv.lines("happenings")), nv.lines("happenings"))
check("...and for the townsfolk", any("arket day" in l for l in scene.view(truth.viewer_for_npc(ws.residents[0], world), "townsfolk").lines("happenings")) if ws.residents else True)
check("the narrator hears what the town is talking about", any("lost a wheel" in l for l in nv.lines("news")), nv.lines("news"))
requests = []
_nr = wp.narration_request
wp.narration_request = lambda *a, **k: (requests.append((a[9] if len(a) > 9 else k.get("happenings"), k.get("news"))), _nr(*a, **k))[1]
from scenes.world import WorldScene as _W
_W._narrate_now(ws, "the player looks around")
check("the narration request carries the day's happening and the news", any("arket day" in h for h in requests[-1][0]) and any("lost a wheel" in n for n in requests[-1][1]), requests[-1])
check("...and the prompt names the news as background only", "WHAT PEOPLE HERE ARE TALKING ABOUT" in _nr("noon", ws.place, [], "x", news=["a thing"]))

# ---- since you were last here
then = store.meta.minutes - 3 * DAY
st = store.load_world_state()
st["threads"].append({"id": "a1", "title": "Wolves at the hill", "tier": "normal", "place": "parth", "kind": "threat", "pressure": "", "stage": 0, "status": "active",
                      "stages": [{"description": "Sheep are going from the hill.", "effects": []}], "fallout": {"description": "x", "effects": []},
                      "times": [then + DAY, then + 9 * DAY], "groups": ["everyone"], "made": then + DAY})
st["history"].append({"minute": then + 2 * DAY, "text": "The quarrel at the mill - settled by the watch.", "place": "trading_square"})
store.save_world_state(st)
since = ambient.since(store, world, "parth", then, store.meta.minutes)
check("coming back after days away, the plain changes are one line for the narrator", len(since) == 1 and "SINCE THE PLAYER WAS LAST HERE" in since[0]
      and "begun since: Wolves at the hill" in since[0] and "ended since: The quarrel" in since[0], since)
check("...nothing for a short absence", ambient.since(store, world, "parth", store.meta.minutes - 60, store.meta.minutes) == [])
check("...nothing on a first visit", ambient.since(store, world, "parth", None, store.meta.minutes) == [])
ws.player.last_in = {}
ws.enter("kelpmoor")
check("leaving a town notes when", ws.player.last_in.get("parth") == ws.minutes, ws.player.last_in)
ws.player.last_in["parth"] = then
store.meta.minutes += 10
ws.enter("trading_square")
check("coming back, the scene holds the lines for the next narration", any("SINCE THE PLAYER" in l for l in ws.__dict__.get("_arrival_lines", [])), ws.__dict__.get("_arrival_lines"))
_W._narrate_now(ws, "the player arrives")
check("...which the narrator is handed once", any("SINCE THE PLAYER" in h for h in requests[-1][0]) and "_arrival_lines" not in ws.__dict__)
wp.narration_request = _nr

shutil.rmtree("saves/ambient_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
