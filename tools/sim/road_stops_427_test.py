"""(f427) Road events, as the owner settled review Q2: "all road events that something noteworthy happens should be a stop for the
player", and a passing sight is not one. The f425 night showed the old way: only a rare event stopped the walk, so a find was taken
without a word (nine items, a second iron helm among them), a hazard rolled itself, and someone in need paid the player ("Your help is
remembered, and repaid.") for help never given while the walk went on. Now what the player could act on stops the walk and waits for them:
a find lies there to be picked up ("let the player pick up items they find if they choose"), a hazard waits for how they get past ("stop
the player to decide how to get past"), and someone in need is helped only if the player helps; walking past them draws a word from the
party, for or against ("Walking past someone in need should get a hire reaction either positive or negative")."""
import json, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 27))
import ui.console as uc
SHOWN = []
for fn in ("narrate", "say", "note", "ledger"):
    setattr(uc, fn, lambda *a, _fn=fn, **k: SHOWN.append((_fn, str(a[0]) if a else "")))
uc.panel = lambda name, data: False
import scenes.road_actions as ra
from llm.contracts import ActionIntent, RoadEvent
from pydantic import ValidationError
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/road_stops_427_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("road_stops_427_test")
store.meta.seed = 27; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(27))
char.level = 20
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("parth")
from tools import nightrun
nightrun.hire_party(ws, 3)
temps = ["gentle", "mercenary", "devout"]
for m, t in zip(ws.player.party, temps):
    m["temper"] = [t] + [x for x in (m.get("temper") or [])[1:2]]
crew = [m["id"] for m in ws.player.party]

# ---- the rules
check("what stops the walk is what the player could act on, by kind, not a rare tier", set(ra.R["stops"]) == {"find", "meeting", "hazard", "aid"}
      and "interrupt" not in ra.R, ra.R.get("stops"))

road = next(r for r in world.roads.values() if r.from_ in world.places and r.to in world.places and world.travel_minutes(r.from_, r.to) >= 180)
a, b = road.from_, road.to
ra.R["hostile"] = 0
prompts = []
real_gen = ra.generate
ra.generate = lambda task, system, user, *x, **k: (prompts.append(user), real_gen(task, system, user, *x, **k))[1]

def happen(kind: str) -> str:
    if ws.player.road:
        ws.leave_road("parth")
    ws.enter(a)
    ra.R["kinds"] = {kind: 1}
    SHOWN.clear()
    return ws.road_event([a, b], a, b, world.travel_minutes(a, b), 0.5, "I walk on", [], walked=120)

# ---- a passing sight is told inside the walk, which goes on
check("a passing sight does not stop the walk", happen("sight") == "go" and not ws.player.road)

# ---- a find lies there, untouched, until the player picks it up
pack_before = len(ws.pack)
out = happen("find")
ground = ws.ground_here()
check("a find stops the walk", out == "stopped" and ws.player.road and ws.player.location == ws.player.road["id"], out)
check("...and lies there: nothing is put in the pack", len(ws.pack) == pack_before and len(ground) == 1, (len(ws.pack), pack_before, ground))
check("...the writer is told it lies there untouched", prompts and "untouched" in prompts[-1] and "finds and takes" not in prompts[-1], prompts[-1][-400:])
check("...and the player is shown what lies there", any(k == "ledger" and t.startswith("Lying here:") for k, t in SHOWN), SHOWN[-4:])
from engine import inventory as inv
name = inv.label(ground[0]) if ground else ""
ws.on_pick_up(ActionIntent(kind="pick_up", item=name), f"I pick up the {name}")
check("picking it up takes it, if they choose", len(ws.pack) == pack_before + 1 and not ws.ground_here(), (len(ws.pack), ws.ground_here()))

# ---- a hazard waits for how they mean to get past
ra.R["chance_per_leg"], legs_was = 0.0, ra.R["chance_per_leg"]
out = happen("hazard")
hz = (ws.player.road or {}).get("hazard")
check("a hazard stops the walk and waits", out == "stopped" and hz and hz.get("what"), (out, ws.player.road))
stop = ws.player.road["id"]
ahead = next(k for k in world.places[stop].connects if k != hz["behind"])
m0 = ws.minutes
SHOWN.clear()
ws.leaving_stop([stop, hz["behind"]], "I turn back the way we came")
check("...going back the way they came passes nothing", not any("costs you" in t for _, t in SHOWN) and ws.minutes == m0, SHOWN)
out = happen("hazard")
stop = ws.player.road["id"]
hz = ws.player.road["hazard"]
ahead = next(k for k in world.places[stop].connects if k != hz["behind"])
m0 = ws.minutes
SHOWN.clear()
ws.leaving_stop([stop, ahead], "We go around it by the long way")
check("...going around costs time and no risk", any(t.startswith("Going around") for _, t in SHOWN) and ws.minutes > m0, SHOWN)
out = happen("hazard")
stop = ws.player.road["id"]
hz = ws.player.road["hazard"]
ahead = next(k for k in world.places[stop].connects if k != hz["behind"])
SHOWN.clear()
ws.leaving_stop([stop, ahead], "I push on through")
check("...pushing on through is ruled as they try it", any(k == "note" for k, _ in SHOWN), SHOWN)
out = happen("hazard")
ws.stop_step(ActionIntent(kind="other", summary="cut a way through the brambles with my axe"), False)
check("...a way of their own (ruled like any attempt) is their way past", ws.player.road["hazard"].get("dealt"), ws.player.road["hazard"])

# ---- someone in need: helped only if the player helps; walked past, the party has a view
def seen(deed):
    return {m["id"]: (m.get("quirks") or {}).get("deeds_seen", {}).get(deed, 0) for m in ws.player.party}
coins0 = ws.player.character.coins
out = happen("aid")
aid = (ws.player.road or {}).get("aid")
check("someone in need stops the walk, and is there to help", out == "stopped" and aid and any(n.id == aid["who"] for n in ws.present),
      (out, ws.player.road and ws.player.road.get("aid"), [n.id for n in ws.present]))
check("...and nothing is paid for help not given", ws.player.character.coins == coins0 and not any("repaid" in t for _, t in SHOWN), SHOWN)
ws.stop_step(ActionIntent(kind="talk", target=aid["who"], speech="Do you need help?"), False)
check("...asking is not helping", not ws.player.road["aid"].get("helped"))
bonds = {m["id"]: m.get("bond", 0) for m in ws.player.party}
before = seen("pass_by")
stop = ws.player.road["id"]
ws.leaving_stop([stop, next(iter(world.places[stop].connects))], "I walk on")
after = seen("pass_by")
moved = {m["id"]: m.get("bond", 0) - bonds[m["id"]] for m in ws.player.party}
check("walking past them is seen by every hire with a view", all(after[i] == before[i] + 1 for i in crew), (before, after))
check("...for and against, by temperament (the gentle and the devout mind it, the mercenary does not)",
      moved[crew[0]] < 0 and moved[crew[1]] > 0 and moved[crew[2]] < 0, moved)
out = happen("aid")
aid = ws.player.road["aid"]
coins0 = ws.player.character.coins
help0 = seen("road_help")
SHOWN.clear()
ws.stop_step(ActionIntent(kind="give", item="bread", target=aid["who"]), False)
check("helping them is repaid, then", ws.player.road["aid"].get("helped") and ws.player.character.coins > coins0
      and any("repaid" in t for _, t in SHOWN), (ws.player.road["aid"], SHOWN))
check("...and the kind among the party are glad of it", seen("road_help")[crew[0]] == help0[crew[0]] + 1 and seen("road_help")[crew[1]] == help0[crew[1]])
before = seen("pass_by")
stop = ws.player.road["id"]
ws.leaving_stop([stop, next(iter(world.places[stop].connects))], "I walk on")
check("...and leaving once they have helped is not walking past", seen("pass_by") == before)
ws.leave_road("parth")
ra.R["chance_per_leg"] = legs_was
ra.generate = real_gen

# ---- the writer must say who is there
ctx = {"hostile": False, "checks": ["perception"], "kind": "aid", "want_journey": True, "stops": True, "roles": sorted(world.roles)}
def ok(**kw):
    body = dict(title="T", journey="You walk an hour.", scene="A man by a broken cart.", kind="aid")
    body.update(kw)
    try:
        RoadEvent.model_validate_json(json.dumps(body), context=ctx)
        return True
    except ValidationError:
        return False
check("someone in need is someone there: the writer names who they are", not ok() and ok(meets_role="farmer"))

store.close()
shutil.rmtree("saves/road_stops_427_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
