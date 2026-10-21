"""Hunger, fatigue, resting, eating and what neglect costs."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import needs, pools, checks, combat, inventory as inv
needs.N["enabled"] = True                      # the rules ship with the system off; these tests are about it running
from llm.contracts import ActionIntent
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/needs_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("needs_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, spec = simlib.make_character("warrior", random.Random(2))
char.level = 10
town = next(p for p in world.places.values() if p.type == "inn") if any(p.type == "inn" for p in world.places.values()) else next(p for p in world.places.values() if not p.danger)
store.save_player(PlayerState(character=char, location=town.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
c = ws.player.character
top = pools.maximum(c, "health")

# no passive regeneration
c.health = top / 2
ws.advance(600)
check("health does not come back by itself", abs(pools.current(c, "health") - top / 2) < 1, pools.current(c, "health"))
check("hunger and fatigue built over 10 hours", 18 < c.hunger < 24 and 22 < c.fatigue < 28, (c.hunger, c.fatigue))

# resting heals 20% an hour in a safe place
c.hunger = c.fatigue = 0.0; c.health = top * 0.2
ws.advance(60, wait="rest")
check("an hour's rest in a safe place heals 20% of max", abs(pools.current(c, "health") - top * 0.4) < top * 0.02, (pools.current(c, "health"), top))
check("a safe place is where you can rest", ws.safe_to_rest())

# stages and costs
for v, hw, fw in ((0, "Fed", "Rested"), (45, "Hungry", "Tired"), (75, "Starving", "Exhausted"), (95, "Famished", "Collapsing")):
    c.hunger = c.fatigue = float(v)
    check(f"words at {v}", needs.words(c) == (hw, fw), needs.words(c))
c.hunger = c.fatigue = 0.0
base_checks, _ = checks.chance(c, "persuasion", set())
base_stam, base_hp = pools.maximum(c, "stamina"), pools.maximum(c, "health")
c.hunger = c.fatigue = 100.0
p = needs.penalties(c)
check("both meters at the limit are a serious penalty", p["checks"] <= -50 and p["stamina"] <= -50 and p["health"] <= -30 and p["damage"] <= -30, p)
now_checks, _ = checks.chance(c, "persuasion", set())
check("checks fall", now_checks < base_checks - 20, (base_checks, now_checks))
check("max stamina and health fall", pools.maximum(c, "stamina") < base_stam * 0.6 and pools.maximum(c, "health") < base_hp * 0.8, (pools.maximum(c, "stamina"), base_stam))
f = combat.fighter_from_character(c)
check("damage dealt falls", f.weary <= -30, f.weary)
c.hunger = c.fatigue = 0.0
check("no penalty when fed and rested", needs.penalties(c)["checks"] == 0 and combat.fighter_from_character(c).weary == 0)

# famished halves rest healing
c.health = top * 0.2; c.hunger = 95.0; c.fatigue = 0.0
ws.advance(60, wait="rest")
gained = pools.current(c, "health") - top * 0.2 * (pools.maximum(c, "health") / top)
check("famished rest heals half as much", 0 < gained < top * 0.14, gained)

# sleeping clears fatigue
c.hunger = 0.0; c.fatigue = 80.0
ws.advance(480, wait="sleep")
check("a night's sleep clears fatigue", c.fatigue == 0.0, c.fatigue)
c.fatigue = 50.0
ws.advance(60, wait="rest")
check("a short rest eases fatigue a little", 46 < c.fatigue < 49, c.fatigue)

# exertion
c.hunger = c.fatigue = 0.0
ws.advance(60, exert=True)
a = (c.hunger, c.fatigue)
c.hunger = c.fatigue = 0.0
ws.advance(60)
check("exertion builds both faster", a[0] > c.hunger and a[1] > c.fatigue, (a, c.hunger, c.fatigue))
c.hunger = c.fatigue = 0.0; needs.fight(c)
check("a fight adds to both", c.hunger > 0 and c.fatigue > 0)

# eating
c.hunger = 80.0; c.health = top * 0.3
ration = inv.make_good("trail_ration", 1); c.inventory.append(ration)
ws.consume(ration)
check("a trail ration clears 35 hunger and heals a little", abs(c.hunger - 45) < 0.1 and pools.current(c, "health") > top * 0.3, c.hunger)
meat = inv.make_good("venison", 1)
ws.consume(meat)
check("venison clears 40", abs(c.hunger - 5) < 0.1, c.hunger)

# collapse
c.hunger = 0.0; c.fatigue = 100.0
NOTES.clear(); ws.collapse_check()
check("at 100 fatigue you collapse and sleep", any("sleep where you fall" in n for n in NOTES) and c.fatigue < 100, (NOTES, c.fatigue))

# old saves
from core.models import Character
d = c.model_dump(); d.pop("hunger"); d.pop("fatigue")
old = Character.model_validate(d)
check("old saves start fed and rested", old.hunger == 0 and old.fatigue == 0)
c.hunger = c.fatigue = 0.0
w = needs.marks(c); c.hunger = 41; c.fatigue = 75
v = needs.voice(w, needs.marks(c))
check("crossing stages speaks once per meter", len(v) == 2 and "stomach" in v[0] and "exhausted" in v[1].lower(), v)
check("no change, no words", needs.voice(needs.marks(c), needs.marks(c)) == [])
w = needs.marks(c); c.hunger = 0; c.fatigue = 0
check("easing back to fine says so", len(needs.voice(w, needs.marks(c))) == 2)
# switched off: nothing builds, nothing is penalised, nothing shown
needs.N["enabled"] = False
c.hunger = 95; c.fatigue = 95
pen = needs.penalties(c)
check("off: no penalties even with old high values", pen["checks"] == 0 and pen["stamina"] == 0 and pen["health"] == 0 and pen["damage"] == 0 and pen["rest_heal"] == 1.0, pen)
check("off: no warning tag, no stage words change", needs.warning(c) == "" and needs.words(c) == ("Fed", "Rested"), (needs.warning(c), needs.words(c)))
check("off: no collapse", not needs.collapsing(c))
c.hunger = 0; c.fatigue = 0
needs.tick(c, 600, exertion=True); needs.fight(c)
check("off: time and fighting build nothing", c.hunger == 0 and c.fatigue == 0, (c.hunger, c.fatigue))
check("off: crossing no stage says nothing", needs.voice(needs.marks(c), needs.marks(c)) == [])
needs.N["enabled"] = True
print("\nFAILED:" if bad else "\nALL PASS", bad or "")
sys.exit(1 if bad else 0)
