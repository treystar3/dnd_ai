"""Campaigns and cataclysms brought up to the rest (f324): a campaign lands near the player; the cataclysm's telling is checked; a town
hit while the player stands in it is fought for at the gate, and holds when the gate is held; a fallen town is ruined, then rebuilding,
and remembers; the crown leads its own war and its death is news; a town in the path shows it when the player is there."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from npc.models import NPC
from engine import pulse, events, towns, matters, deeds
from llm.contracts import CataclysmProposal, CataclysmStage
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/cataclysm_v2_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("cataclysm_v2_test")
store.meta.seed = 8; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 90; char.coins = 10**5
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square")
now = ws.minutes
state = pulse.empty_state(now); store.save_world_state(state)
narrated = []
ws._narrate_now = lambda event, player_text="": narrated.append(event)
notes = []
_note = console.note
console.note = lambda t, *a, **k: notes.append(t)

# ---- 1. a campaign lands near the player when a marked pressure is near
marked = [p for p in world.pressures.values() if p.campaign]
dist = events.distances(world, "parth")
near_marked = [p for p in marked if pulse.town_of(world, p.place) == "parth" or dist.get(pulse.town_of(world, p.place), 10**9) <= 600 or p.place == "wend_vale"]
pr, place = pulse.place_by_band(store, world, marked, random.Random(5), must_pressure=True)
check("a campaign takes a marked pressure in the nearest band that has one", pr is not None and pr.campaign and (not near_marked or pr in near_marked), (pr and pr.id, [p.id for p in near_marked]))

# ---- 2. the telling is checked like speech
prop = CataclysmProposal(title="The Ash Tide", news="Smoke over the Greywood, and Oswin Lovell swears the sky is wrong.", stages=[CataclysmStage(name="Omens", description="Birds leave the wood.", signs="Dogs will not settle.")])
sp = dict(prop.spoken())
check("the cataclysm's news, stages and signs are what gets checked", "news" in sp and "stage 1" in sp and "signs 1" in sp and "Omens" not in sp.values())
from engine import truth
check("...and an invented name in them is caught", truth.coined(prop.news, "ORIGIN: greywood", truth.world_words(world)) != "")

# ---- 3. the fall is a condition, then a recovery
st = store.load_world_state(); st["fallen"] = {"parth": now - 5 * 1440}; store.save_world_state(st)
c = towns.condition(store, world, "trading_square", now)
check("a town that fell five days ago is ruined, and the streets say so", c.name == "ruined" and "clearing" in c.crowd, (c.name, c.why))
st["fallen"] = {"parth": now - 40 * 1440}; store.save_world_state(st)
check("...forty days on it is rebuilding", towns.condition(store, world, "trading_square", now).name == "rebuilding")
store.journal(now - 600, "npc_gone", "", "z1", "Hob is gone: killed in the fall", {"how": "killed in the fall", "place": "parth"})
check("...a ruin outranks mourning; rebuilding does not", towns.condition(store, world, "trading_square", now).name == "mourning")
st["fallen"] = {"parth": now - 2 * 1440}; store.save_world_state(st)
check("...", towns.condition(store, world, "trading_square", now).name == "ruined")
st["fallen"] = {}; store.save_world_state(st)

# ---- 4. the crown leads its own side, and its death is news
check("the monarch heads the roles a war's leaders are drawn from", events.C["leader_roles"][0] == "monarch")
king = NPC(id="king1", name="Aldric Vane", people="human", role="monarch", location="trading_square", description="The king.")
store.save_npc(king)
ps = store.load_place("trading_square"); ps.residents = ps.residents + ["king1"]; store.save_place(ps)
th = {"id": "cat1", "title": "The Ash Tide", "tier": "cataclysm", "kind": "invasion", "place": "greywood", "antagonist": "the Ash Tide", "stage": 1, "status": "active",
      "stages": [{"description": "Omens.", "effects": [], "signs": "Dogs will not settle."}, {"description": "The host reaches the Wend.", "effects": [], "signs": "Smoke on the north road."}],
      "fallout": {"description": "", "effects": []}, "times": [now - 1440, now, now + 14 * 1440], "made": now - 1440, "groups": ["everyone"], "paths": [],
      "hit_towns": ["parth"], "hits": [[], ["parth"]], "fallen": [], "level": 90, "scope_places": ["parth"], "leaders": [], "boss": "", "door": "scene", "summons": "pending", "moment": "", "sender": "", "clues": [], "touched": False, "answered": False, "opened": now}
st = store.load_world_state(); st["threads"] = [th]; store.save_world_state(st)
toll, flee = events.C["toll"]["falls"], events.C["flee_share"]
events.C["toll"]["falls"], events.C["flee_share"] = 5.0, 0.0
caught = events._catch_people(store, world, st, th, "parth", True, "", now, random.Random(1))
events.C["toll"]["falls"], events.C["flee_share"] = toll, flee
check("when the capital's crown dies in a fall, the whole kingdom hears", any("The crown is dead: Aldric Vane" in n["text"] for n in st.get("news", [])) and store.load_npc("king1").gone, [n["text"][:60] for n in st.get("news", [])][-2:])
check("...and the town remembers it", any("Aldric Vane, who ruled" in m for m in matters.town_memory(store, world, "trading_square", now)))
store.save_world_state(st)

# ---- 5. hit while the player stands there: an assault at the gate, not a roll
ws.enter("trading_square")
st = store.load_world_state()
spawn = events.add_spawn(store, world, st, "cat1", "greywood", "wolf", False, now - 1440, days=30, level=88, need=3)
st["assaults"] = []
store.save_world_state(st)
rng = random.Random(0)
events.on_stage(store, world, ws.catalog, st, th, now, rng)
check("a cataclysm reaching the town the player is in queues an assault instead of rolling the town", st.get("assaults") and st["assaults"][0]["town"] == "parth", st.get("assaults"))
store.save_world_state(st)
narrated.clear()
events.apply_player_events(ws)
check("...the host comes at the gate: a moment, and a fight with the cataclysm's own creatures", ws.combat is not None and getattr(ws, "assault", None) and any("REACHES PARTH" in e and "at the gate" in e for e in narrated), (bool(ws.combat), narrated[-1:][0][:80] if narrated else ""))
check("...the town is not yet decided", "parth" not in store.load_world_state().get("fallen", {}))
ws.combat = None
rep_before = ws.player.reputation.get("parth", 0)
events.assault_over(ws, "victory")
st = store.load_world_state()
check("the gate held: the town holds without a roll, and the kingdom hears who stood there", "parth" not in st.get("fallen", {}) and any("stood at the gate" in n["text"] for n in st["news"]), [n["text"][:70] for n in st["news"]][-2:])
check("...it is a deed the judge can read, the town thinks more of them, and remembers", any(d["kind"] == "defend" for d in st["deeds"]) and ws.player.reputation.get("parth", 0) > rep_before
      and any("stood at the gate" in m for m in matters.town_memory(store, world, "trading_square", now)))
check("...and the fight is told", any("holds" in n for n in notes[-2:]), notes[-2:])

# ---- 6. a town in the path, with the player there, is a scene
st = store.load_world_state(); st["player_events"] = [{"kind": "warn", "town": "parth", "title": "The Ash Tide"}]; store.save_world_state(st)
narrated.clear()
events.apply_player_events(ws)
check("word that the town lies in the path is shown as a scene when the player stands in it", any("LIES IN THE PATH" in e for e in narrated), narrated[-1:])
check("a cataclysm's anchors may send for the player (door six on its towns)", matters.D["weights"]["cataclysm"].get("summons", 0) > 0)

console.note = _note
shutil.rmtree("saves/cataclysm_v2_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
