"""The places pane: what you can reach from here, how long it takes, and the Go button running the same travel as typing it."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from ui import console

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
lines, panels = [], []
console.note = lambda m: lines.append(m)
console.panel = lambda name, data: panels.append((name, data)) or True

shutil.rmtree("saves/places_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("places_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
store.save_player(PlayerState(character=char, location="ironvein_inn"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("ironvein_inn")

d = ws.places_data()
ids = [r["id"] for r in d["local"]]
check("the places in this town are listed", "ironvein_guild" in ids and "ironvein_forge" in ids, ids)
check("...never the place you stand in", "ironvein_inn" not in ids)
check("...with walking times, nearest first", all(r["away"] for r in d["local"]) and [r["minutes"] for r in d["local"]] == sorted(r["minutes"] for r in d["local"]))
check("nothing from another town is in the local list", all(r["id"].startswith("ironvein") for r in d["local"]), ids)
check("a new character knows no other town: nothing further afield until told", d["far"] == [], [r["id"] for r in d["far"]][:4])
check("...but the roads out are listed, with no ends", len(d["roads"]) > 0 and all(set(r) >= {"dir", "name"} for r in d["roads"]), d["roads"])
ws.player.heard.append("parth")
d = ws.places_data()
check("towns you have heard of are listed further afield", len(d["far"]) > 0 and all(r["id"] not in ids for r in d["far"]), [r["id"] for r in d["far"]][:4])
check("it is named for where you stand", d["town"] == "Ironvein" and d["here"] == "ironvein_inn", (d["town"], d["here"]))

ws.command("#exits")
check("#exits opens the pane", panels and panels[-1][0] == "places")

ws.command("#goto ironvein_guild")
check("Go walks to the place", ws.player.location == "ironvein_guild", ws.player.location)
check("...and the pane redraws from the new place", panels[-1][0] == "places" and panels[-1][1]["here"] == "ironvein_guild")
check("a button names its place exactly: no swap for a nearer place of the same kind", ws.nearest_alike("guild_house", "") == "guild_house")
ws.command("#goto ironvein_forge")
check("Go works from the new place too", ws.player.location == "ironvein_forge", ws.player.location)

lines.clear(); here = ws.player.location
ws.command("#goto nowhere_land")
check("an unknown place is refused", ws.player.location == here and any("don't know a way" in l for l in lines), lines)
lines.clear()
far = next(pid for pid in world.places if pid.startswith("eldervale") and pid not in {r["id"] for r in ws.places_data()["local"] + ws.places_data()["far"]})
ws.command(f"#goto {far}")
check("a place you have no way to is refused", ws.player.location == here and any("don't know a way" in l for l in lines), lines)

# not in the middle of a fight
ws.enter("ironvein_inn")
ws.combat = object()
lines.clear(); here = ws.player.location
for cmd in ("#goto ironvein_guild", "#shopbuy ware x y", "#boardjoin"):
    ws.command(cmd)
check("pane buttons are refused during a fight", ws.player.location == here and sum("middle of a fight" in l for l in lines) == 3, lines)
ws.combat = None
ws.command("#goto ironvein_guild")
check("...and work again afterwards", ws.player.location == "ironvein_guild", ws.player.location)
# (f313) what a town has, for the people in it to answer from: every building and tradesperson, or none and where the nearest is
from engine import truth as _tr
_w2 = ws.world
ws.enter("trading_square")
lines = _tr.scene_of(ws).view(_tr.NARRATOR, "interpreter").lines("town")
check("Parth's people know it has no smithy building and that a smith works without one", any(l.startswith("smithy: no smithy building in Parth") for l in lines), lines)
check("...and name the inn it does have", any(l.startswith("inn: ") and "none" not in l for l in lines), lines)
from npc import prompts as _pr
from npc.models import NPC as _NPC
_n = _NPC(id="b1", name="Phineas", people="human", role="baker", location="trading_square", description="A baker.")
_req = _pr.conversation_request(_n, _w2.places["trading_square"], [], [], [], "where is the smith?", [], [], [],
                                truth_text=_tr.scene_of(ws).view(_tr.viewer_for_npc(_n, _w2), "townsfolk").text())
check("...and the conversation request carries it", "WHAT THIS TOWN HAS" in _req and "smithy: no smithy building in Parth" in _req)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
