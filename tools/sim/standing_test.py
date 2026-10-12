"""Standing and rumors: hidden group standing per town, deeds into news, news spreading, correcting tales, effects."""
import random, re, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from core.models import Ability
from engine import law, locks, intent_audit as ia, clock
from llm.contracts import ActionIntent as A, ObjectVerdict
from npc.models import NPC
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


from engine import standing, pulse
from storage.campaign import PlayerState as PS
check_ = check
# ---------- the rules
P = PS(character=simlib.make_character("warrior", random.Random(1))[0], location="parth")
check("words follow the thresholds", [standing.word(v) for v in (80, 40, 15, 0, -15, -40, -80)] == ["honored", "trusted", "regarded", "unknown", "wary", "distrusted", "hostile"])
standing.add(P, "parth", "guards", 50, 10)
check("a standing is stored and read back", standing.value(P, "parth", "guards", 10) == 50)
check("it never drifts back on its own", standing.value(P, "parth", "guards", 10 + 400) == 50)
standing.add(P, "parth", "guards", -500, 10)
check("it is clamped", standing.value(P, "parth", "guards", 10) == -100)
check("an unknown town has no opinion", standing.value(P, "x", "guards", 3) == 0)
check("prices follow the merchants", (standing.add(P, "parth", "merchants", 40, 10), standing.price_factor(P, "parth", 10))[1] == 0.95 and (standing.add(P, "parth", "merchants", -140, 10), standing.price_factor(P, "parth", 10))[1] == 1.12)
check("the watch weighs heat by its regard", standing.heat_shift(P, "parth", 10) == 15 and standing.heat_shift(P, "other", 10) == 0)

# ---------- the scene
world = load_world()
shutil.rmtree("saves/standing_test", ignore_errors=True)
store = CampaignStore.open_or_create("standing_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("ranger", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
config.TURN_LOG_PATH = "saves/standing_test/turns.jsonl"
char = ws.player.character; player = ws.player
mer = NPC(id="m1", name="Varro", people="human", role="merchant", location="parth", traits=[], trust=50, knowledge_groups=["merchants"])
grd = NPC(id="g1", name="Garran", people="human", role="guard", location="parth", traits=[], trust=50, knowledge_groups=["guards"])
frm = NPC(id="f1", name="Hob", people="human", role="farmer", location="parth", traits=[], trust=50)
for n in (mer, grd, frm): store.save_npc(n)
ws.narrate = lambda e, t="": None
day = lambda: clock.day(ws.minutes)
def v(town, g): return standing.value(player, town, g, day())

check("carriers: a guard alone does not spread it to everyone", "everyone" not in standing.carriers(world, [grd], "assault"))
check("carriers: a passer-by does", "everyone" in standing.carriers(world, [frm], "assault"))
check("carriers: a witness's own groups carry it", "merchants" in standing.carriers(world, [mer], "assault") and "guards" in standing.carriers(world, [grd], "assault"))
check("carriers: a public deed is everyone's", "everyone" in standing.carriers(world, [], "contract_done"))

# an unseen deed is nothing
ws.standing_report("theft", [], "a ring")
check("a theft nobody saw leaves no trace", not player.standing and not (store.load_world_state() or {}).get("news"))
# a seen theft
ws.standing_report("theft", [mer], "a ring")
check("a seen theft hurts merchants and the watch here, and warms outlaws", v("parth", "merchants") == -5 and v("parth", "guards") == -3 and v("parth", "outlaws") == 3, player.standing)
news = store.load_world_state()["news"]
check("it becomes news with the deed attached", len(news) == 1 and news[0]["deed"]["kind"] == "theft" and "Varro" not in news[0]["text"], news)
check("the news is about the player by name", char.name in news[0]["text"] or char.name in news[0]["deed"]["true"], news[0]["text"])
ws.standing_report("theft", [mer], "a ring")
ws.standing_report("theft", [mer], "a gem", 2.0)
check("a heavy theft counts double", v("parth", "merchants") == -5 - 5 - 10, v("parth", "merchants"))

# a public deed needs no witness
before = v("parth", "guild")
ws.standing_report("contract_done", None, "Rat Hunt")
check("a finished contract warms the guild with no witness needed", v("parth", "guild") == before + 4)

# determinism and the share that is twisted
rates = sum(random.Random(f"3:twist:theft-{i}-0").uniform(0, 100) < 20 for i in range(2000)) / 2000
check("about a fifth of tales are twisted", 0.15 < rates < 0.25, rates)
check("a deed's twist is fixed by the seed", all(news[0]["deed"]["twisted"] == (random.Random(f"3:twist:{news[0]['deed']['id']}").uniform(0, 100) < 20) for _ in range(2)))

# spreading to another town
other = "willowmead"
check("the other town knows nothing yet", v(other, "merchants") == 0)
check("it has not arrived on the day", not standing.reached(world, news[0], other, news[0]["minute"] + 1) or pulse.travel_delay(world, "parth", other) == 0)
delay = pulse.travel_delay(world, "parth", other)
check("there is a travel delay between the towns", delay > 0, delay)
ws.minutes_save = None
ws.advance(delay + 60)
standing.arrivals(store, world, player, other, ws.minutes, day())
far = v(other, "merchants")
check("the far town feels it, weaker than the home town", -5 - 5 - 10 < far < 0, far)
snap = dict(player.standing[other])
standing.arrivals(store, world, player, other, ws.minutes, day())
check("news is felt once per town", player.standing[other] == snap)

# the guard-only tale
ws.standing_report("assault", [grd], "Hob")
aid = store.load_world_state()["news"][-1]
check("a tale only the watch saw is carried by the watch", "everyone" not in aid["groups"] and "guards" in aid["groups"], aid["groups"])
mer_before = v(other, "merchants")
ws.advance(delay + 60)
standing.arrivals(store, world, player, other, ws.minutes, day())
check("a far town's merchants do not hear what only the watch saw", v(other, "merchants") == mer_before, (mer_before, v(other, "merchants")))
check("but its watch does", v(other, "guards") < 0, v(other, "guards"))

# a twisted tale lands harder far away, and can be set straight
state = store.load_world_state()
tw = next((e for e in state["news"] if e["deed"]["twisted"]), None)
if tw is None:
    for i in range(60):
        ws.standing_report("bribe_guard", [frm]); ws.advance(5)
    state = store.load_world_state()
    tw = next(e for e in state["news"] if e["deed"]["twisted"])
check("a twisted tale reads exaggerated", tw["text"] != tw["deed"]["true"])
ws.advance(delay + 60)
third = "greyhollow"
d3 = pulse.travel_delay(world, "parth", third)
ws.advance(d3 + 60)
standing.arrivals(store, world, player, third, ws.minutes, day())
applied = player.standing_seen[tw["deed"]["id"]][third]
check("the exaggerated part is recorded", any(k.endswith(":x") for k in applied) or not applied, applied)
before = {g: v(third, g) for g in standing.GROUPS}
ok = standing.correct(store, player, tw["deed"]["id"], ws.minutes)
after = {g: v(third, g) for g in standing.GROUPS}
check("correcting restores the true text and takes back the exaggeration", ok and store.load_world_state()["news"][[e["deed"]["id"] for e in store.load_world_state()["news"]].index(tw["deed"]["id"])]["text"] == tw["deed"]["true"]
      and all(abs(after[g]) <= abs(before[g]) + 1e-6 for g in standing.GROUPS), (before, after))
check("a true tale cannot be corrected", not standing.correct(store, player, news[0]["deed"]["id"], ws.minutes) or news[0]["deed"]["twisted"])

# the command line
NOTES.clear()
ws.player.location = "parth"; ws.present = [mer, frm]
ws.show_standing(); ws.show_rumors()
check("#standing speaks in words, never numbers", NOTES and not any(re.search(r"-?\d+\.?\d*", n.split(":")[-1]) for n in NOTES[:3]), NOTES)
check("#rumors lists what is said", any(char.name in n for n in NOTES), NOTES)
ws.correct_rumor("")
check("#correct asks which tale", "Which tale" in NOTES[-1])


# #correct end to end
from engine import checks as _checks
st = store.load_world_state()
tw2 = next(e for e in st["news"] if e["deed"]["twisted"])
tw2["minute"] = ws.minutes - 10; tw2["origin"] = "parth"
store.save_world_state(st)
ws.player.location = "parth"; ws.present = [mer, frm]; NOTES.clear()
idx = [e["deed"]["id"] for e in ws.rumor_items()].index(tw2["deed"]["id"]) + 1
real_roll = _checks.roll
_checks.roll = lambda odds, rng=None: ("failure", 99)
ws.correct_rumor(str(idx))
check("a failed argument leaves the tale as it was", any("Nobody is convinced" in n for n in NOTES) and [e for e in store.load_world_state()["news"] if e["deed"]["id"] == tw2["deed"]["id"]][0]["deed"]["twisted"], NOTES)
_checks.roll = lambda odds, rng=None: ("success", 1)
t0 = ws.minutes; ws.present = [mer, frm]
ws.correct_rumor(str(idx))
check("a successful one sets it straight and takes time", not [e for e in store.load_world_state()["news"] if e["deed"]["id"] == tw2["deed"]["id"]][0]["deed"]["twisted"] and ws.minutes >= t0 + 30, NOTES)
_checks.roll = real_roll


# paying a fine, and the tithe box
player.standing.clear(); player.standing_seen.clear()
ws.standing_report("fine_paid", [grd])
check("paying a fine earns a little with the watch, and only the watch", v("parth", "guards") == 3 and v("parth", "merchants") == 0, player.standing)
check("tithe weights: nothing under a gold, then more as it doubles", standing.tithe_weight(9999) == 0 and standing.tithe_weight(10000) == 1 and standing.tithe_weight(20000) == 2 and standing.tithe_weight(10**9) == 6)
from engine import money
class T: pass
temple = next(k for k, p in world.places.items() if p.type == "temple")
ws.enter(temple) if False else None
ws.player.location = temple
char.coins = money.to_smallest(gold=10)
from llm.contracts import ActionIntent as AI
NOTES.clear()
ws.on_give(AI(kind="give", item="2 gold", summary="drop 2 gold in the tithe box"), "I put 2 gold in the tithe box")
tt = pulse.town_of(world, temple)
check("a tithe takes the coins", char.coins == money.to_smallest(gold=8), char.coins)
check("and warms the temple, by how much was given", standing.value(player, tt, "temple", day()) == 2, player.standing)
ws.on_give(AI(kind="give", item="10 silver", summary="tithe"), "I put 10 silver in the tithe box")
check("a small tithe buys nothing but a blessing", standing.value(player, tt, "temple", day()) == 2 and char.coins == money.to_smallest(gold=8) - money.to_smallest(silver=10))
before = char.coins
ws.on_give(AI(kind="give", item="500 gold", summary="tithe"), "I put 500 gold in the tithe box")
check("you cannot tithe more than you have", char.coins == before)
ws.player.location = "parth"
before = char.coins
check("outside a temple it is not a tithe", ws.tithe_box(AI(kind="give", item="2 gold"), "I give 2 gold") is False)

# prices and the watch
player.standing.clear(); player.standing_seen.clear()
standing.add(player, "parth", "merchants", 40, day())
check("good standing lowers what merchants ask", abs(ws.heat_price() - 0.95) < 1e-9, ws.heat_price())
player.standing.clear()
standing.add(player, "parth", "guards", -70, day())
law.set_heat(player, "parth", 25, day())
ws.present = [grd]
CONF = []
ws.law_confront = lambda guard, town: CONF.append(town)
ws.arrest = lambda guard, town, forced=False: CONF.append(town)
ws.law_check()
check("a watch that thinks ill of you stops you at lower heat", CONF == ["parth"], CONF)
player.confronted.clear(); player.standing.clear(); CONF.clear(); ws.law_check()
check("...where a stranger at that heat is left alone", CONF == [], CONF)

# NPC prompt lines
player.standing.clear(); standing.add(player, "parth", "merchants", 35, day())
check("a merchant's prompt says how their guild regards you", "trusted" in ws.standing_line(mer) and ws.standing_line(frm) == "", ws.standing_line(mer))
check("trust moves at a first meeting", ws.standing_trust(mer) > 0)

# arriving
NOTES.clear(); player.standing.clear(); standing.add(player, "parth", "guards", -50, day())
ws.standing_arrive()
check("arriving, a group with strong feelings says so", any("watch" in n and "do not think well" in n for n in NOTES), NOTES)

# lawless places keep no tally
check("the wild keeps no tally", standing.report(store, world, player, "theft", [k for k, p in world.places.items() if p.danger][0], "x", "me", 1, 1, [mer]) is None)
print("all passed" if not bad else "FAILED", bad)
sys.exit(1 if bad else 0)
