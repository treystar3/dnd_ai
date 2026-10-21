"""The debug pulse log, the #pulse pane, and the land knowledge given to NPCs."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import config
import ui.console as uc
NOTES, PANELS = [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.panel = lambda name, data: (PANELS.append((name, data)) or True)
from engine import pulse, pulselog
from npc import land, prompts
from npc.life import populate_place
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/pulse_log_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("pulse_log_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 6000; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
cat = load_traits()
populate_place(store, world, "parth", cat)
npcs = [store.load_npc(i) for i in store.list_npcs()]
npc = npcs[0]
state = pulse.empty_state(0)

pulselog.clear()
pulselog.begin(1440)
row = pulselog.note("thread", "[normal] A test at Parth")
pulse.apply_effects(store, world, cat, state,
                    [{"kind": "mood", "npc": npc.id, "text": "rattled"},
                     {"kind": "mark", "place": "parth", "text": "a scorch on the gate"},
                     {"kind": "move", "npc": npc.id, "place": "nowhere"},
                     {"kind": "prices", "place": "parth", "value": 1.3, "days": 2}],
                    "normal", 1440, "A test", raw=True, row=row)
res = [e["result"] for e in row["effects"]]
check("an applied effect is logged as applied", res[0] == "applied" and res[1] == "applied", res)
check("an effect naming an unknown place is logged as ignored", res[2].startswith("ignored"), res)
check("the effect line names the person and the place", npc.name in row["effects"][0]["text"] and "Parth" in row["effects"][1]["text"], row["effects"][:2])
check("the change really happened", store.load_npc(npc.id).mood == "rattled")

pulselog.begin(1440 + 360); pulselog.begin(1440 + 720); pulselog.close()
kinds = [r["kind"] for r in pulselog.LOG]
check("quiet pulses merge into one row", kinds == ["thread", "quiet"] and pulselog.LOG[-1]["count"] == 2, kinds)

shutil.rmtree("saves/pulse_log_test_b", ignore_errors=True)
ws = WorldScene(store, world, cat, store.load_player())
config.DEBUG = False
PANELS.clear(); NOTES.clear(); ws.command("#pulse")
check("without --debug the pane refuses", not PANELS and any("debug" in n for n in NOTES), NOTES)
config.DEBUG = True
PANELS.clear(); ws.command("#pulse")
name, d = PANELS[-1]
check("with --debug the pulse pane opens, newest first", name == "pulse" and d["rows"][0]["kind"] == "quiet" and d["rows"][1]["kind"] == "thread", [r["kind"] for r in d["rows"]])
check("the pane carries the effects of an event", len(d["rows"][1]["effects"]) == 4)
config.DEBUG = False

lines = land.land_lines(world, "parth")
silver = next(l for l in lines if l.startswith("silverleaf"))
check("the land lists where silverleaf really grows", "Greywood" in silver and "south fields" in silver and "Willowmead orchards" not in silver, silver)
check("game animals are listed", any(l.startswith("venison") for l in lines))
far = land.land_lines(world, "ironvein")
check("a place with no herbs near says so", all("none that you know of" in l for l in far if l.startswith(("silverleaf", "moonpetal"))), far[:2])
req = prompts.conversation_request(npc, world.places["parth"], [], [], [], "Where is silverleaf?", [], [], [], land=lines)
check("the land is in the NPC's prompt", "THE LAND AROUND YOU" in req and "Greywood" in req)
check("the rules tell NPCs not to guess", "Never say a herb grows somewhere the list does not give" in prompts.CONVERSATION_SYSTEM)
shutil.rmtree("saves/pulse_log_test", ignore_errors=True)
print("ALL PASS" if not bad else "FAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
