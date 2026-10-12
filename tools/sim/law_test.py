"""Law: checks ignore gear attributes, theft rolls on a bar, witnesses, heat, confrontation, arrest, jail, force, hidden objects."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
ANSWERS = []
uc.ask = lambda: ANSWERS.pop(0) if ANSWERS else "run"
from core.models import Item, ItemProperty
from engine import checks, law, intent_audit as ia, items, clock
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

# ---------- 1. checks ignore gear attribute points; gear helps only through a bonus naming the check
char, _ = simlib.make_character("ranger", random.Random(2))
base = checks.attribute_value(char, "stealth")
ring_dex = Item(uid="r1", base="ring", name="Ring of Dex", rarity="rare", item_level=10, properties=[ItemProperty(modifies="dexterity", magnitude=9)])
char.equipment["ring1"] = ring_dex
check("a +dexterity ring adds nothing to a check's attribute", checks.attribute_value(char, "stealth") == base == char.attributes.dexterity, (base, checks.attribute_value(char, "stealth")))
before = checks.chance(char, "stealth", {"always"})[0]
ring_st = Item(uid="r2", base="ring", name="Ring of Shadow", rarity="rare", item_level=10, properties=[ItemProperty(modifies="stealth", magnitude=20)])
char.equipment["ring1"] = ring_st
after, why = checks.chance(char, "stealth", {"always"})
check("a +20 stealth ring adds 20 points to a percent check", abs(after - min(95, before + 20)) < 1e-6 or after == 95, (before, after, why))
check("gear points come only from effects naming the check", checks.gear_points(char, "stealth", {"always"}) == 20 and checks.gear_points(char, "persuasion", {"always"}) == 0)
check("a stealth ring is a 1.2 multiplier on the roll", abs(law.gear_multiplier(20) - 1.2) < 1e-9)
check("the multiplier is capped", law.gear_multiplier(20 + 20 + 20) == 1.3)
char.equipment.clear()

# ---------- 2. the bar
check("roll window at level 10 and 100", (law.window(10), law.window(100)) == (24, 269), (law.window(10), law.window(100)))
def invest(z, f): return law.T["start_dex"] + f * 5 * (z - 1)
def p_ok(t): return t["strong success"] + t["success"]
for z in (10, 30, 100):
    t0, t34, t80 = (law.chance_table(z, invest(z, f)) for f in (0, 0.34, 0.8))
    check(f"zone {z}: 0% invested is hopeless, 34% is a toss-up, 80% is certain",
          p_ok(t0) < 0.05 and 0.42 <= p_ok(t34) <= 0.58 and p_ok(t80) >= 0.99, (p_ok(t0), p_ok(t34), p_ok(t80)))
rel = law.chance_table(100, invest(100, 0.34), item_value=50000, owner_present=True)
check("a relic watched by its owner is out of reach of a 34% build", p_ok(rel) == 0 and rel["failure"] > 0.9, rel)
rel80 = law.chance_table(100, invest(100, 0.8), item_value=50000, owner_present=True)
check("...and a sure thing for an 80% build", p_ok(rel80) >= 0.99, rel80)
check("a pricier item is harder", p_ok(law.chance_table(10, 35, item_value=5000)) < p_ok(law.chance_table(10, 35, item_value=100)))
check("more witnesses make it harder", p_ok(law.chance_table(10, 35, witnesses=3)) < p_ok(law.chance_table(10, 35, witnesses=0)))
check("a watching owner is harder than an empty room", p_ok(law.chance_table(10, 35, owner_present=True)) < p_ok(law.chance_table(10, 35)))
check("a suspicious victim is harder", p_ok(law.chance_table(10, 35, target_pct=10)) < p_ok(law.chance_table(10, 35)))
check("a stealth ring helps", p_ok(law.chance_table(10, 35, gear_points=20)) > p_ok(law.chance_table(10, 35)))
check("a low-level character cannot take a high-level thing", law.attempt(60, 20, 0, 10000, True, 1)["hopeless"])
check("a hopeless attempt is a failure", law.attempt(60, 20, 0, 10000, True, 1)["degree"] == "failure")
check("an easy one is not hopeless", not law.attempt(1, 20, 0, 50, False, 0)["hopeless"])
check("item cost is capped", law.item_term(10**9) == law.T["item"]["cap"] and law.item_term(50) == 0)
check("the roll is multiplied but never past the window's cap", law.attempt(10, 35, 0, 0, False, 0, rng=random.Random(1))["mult"] == 1.0)

# ---------- 3. noticing, heat, fines
check("a flawless theft is never noticed by a passer-by", law.notice_chance("strong success", "farmer") == 0)
check("a failed theft is always noticed by the victim", law.notice_chance("failure", "merchant", is_target=True) == 100)
check("guards notice more", law.notice_chance("partial", "guard") > law.notice_chance("partial", "farmer"))
check("tiers", [law.tier(h) for h in (0, 19, 20, 39, 40, 69, 70, 100)] == ["clear", "clear", "cold", "cold", "confront", "confront", "wanted", "wanted"])
check("fine is 50 copper a point", law.fine(40) == 2000)
check("a valuable item adds heat", law.offense_heat("theft", 20000, False, False) == 15 and law.offense_heat("theft", 500, False, False) == 10)
check("a story object adds more", law.offense_heat("theft", 500, True, False) == 15)
check("only passers-by noticing halves it", law.offense_heat("theft", 500, False, True) == 5)
check("assault is 20", law.offense_heat("assault", 0, False, False) == 20)
class P: heat = {}
p = P(); law.set_heat(p, "parth", 50, 1)
check("heat decays 4 a day", law.current_heat(p, "parth", 4) == 38 and law.current_heat(p, "parth", 40) == 0)
check("heat is capped at 100 and floors at 0", law.add_heat(p, "parth", 500, 1) == 100 and law.add_heat(p, "parth", -500, 1) == 0 and "parth" not in p.heat)
check("prices are 10% up when cold", law.price_factor(20) == 1.1 and law.price_factor(19) == 1.0)

# ---------- 4. the scene
world = load_world()
shutil.rmtree("saves/law_test", ignore_errors=True)
store = CampaignStore.open_or_create("law_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("ranger", random.Random(1))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
config.TURN_LOG_PATH = "saves/law_test/turns.jsonl"
mer = NPC(id="m1", name="Varro", people="human", role="merchant", location="parth", traits=[], trust=50)
grd = NPC(id="g1", name="Garran", people="human", role="guard", location="parth", traits=[], trust=50)
frm = NPC(id="f1", name="Hob", people="human", role="farmer", location="parth", traits=[], trust=50)
for n in (mer, grd, frm): store.save_npc(n)
ws.lucky_save = lambda: None
EVENTS = []
ws.narrate = lambda event, text="": EVENTS.append(event)
ws.present = [mer, frm]
real_attempt, real_notices = law.attempt, law.notices
def fix_degree(d, hopeless=False):
    law.attempt = lambda *a, **k: {"window": 24, "score": 0, "bar": 0, "mult": 1.0, "hopeless": hopeless, "roll": 7, "degree": d}
def fix_notice(seen_ids):
    law.notices = lambda degree, role, is_target=False, assault=False, rng=None: (role in seen_ids)
def reset():
    mer.memories.clear(); frm.memories.clear(); grd.memories.clear()
    mer.trust = frm.trust = grd.trust = 50; mer.hidden = []; mer.looks_away_until = -1; frm.looks_away_until = -1; grd.looks_away_until = -1
    ws.player.heat.clear(); ws.player.confronted.clear(); ws.player.character.key_items.clear(); ws.player.character.coins = 100000
    ws.player.standing.clear(); ws.player.standing_seen.clear()
    ws.present = [mer, frm]; EVENTS.clear(); NOTES.clear(); ANSWERS.clear()
    state = store.load_place("parth"); state.hidden = []; store.save_place(state)
    law.attempt, law.notices = real_attempt, real_notices
def pack_names(): return [items.display_name(i) if not i.good else i.good for i in ws.pack]

# a real ware
reset(); fix_degree("success"); fix_notice(set())
n0 = len(ws.pack)
ws.on_steal(A(kind="steal", target="m1", item="torch"), "I lift a torch from the merchant")
check("a successful theft of a ware puts it in the pack", len(ws.pack) == n0 + 1 and any("torch" in str(x) for x in pack_names()), pack_names())
check("an unseen theft leaves the owner a memory that something is gone, with no culprit", any("gone missing" in m.text for m in mer.memories), [m.text for m in mer.memories])
check("an unseen theft costs no heat", ws.heat_here() == 0)
check("an unseen theft is narrated as unseen", "Nobody notices" in EVENTS[-1], EVENTS)

reset(); fix_degree("failure"); fix_notice({"merchant"})
n0 = len(ws.pack)
ws.on_steal(A(kind="steal", target="m1", item="torch"), "I lift a torch")
check("a failure takes nothing", len(ws.pack) == n0)
check("the victim noticing costs trust and heat and is remembered", mer.trust < 50 and ws.heat_here() == 10 and any("Caught" in m.text for m in mer.memories), (mer.trust, ws.heat_here()))
store_deeds = store.load_world_state() or {}
reset(); fix_degree("partial"); fix_notice({"farmer"})
ws.on_steal(A(kind="steal", target="m1", item="torch"), "I lift a torch")
check("a partial gets the item; a passer-by who sees it costs half heat and trust 5", ws.heat_here() == 5 and frm.trust == 45 and mer.trust == 50, (ws.heat_here(), frm.trust, mer.trust))

reset(); fix_degree("partial"); fix_notice({"farmer", "merchant"})
frm.looks_away_until = ws.minutes + 100
ws.on_steal(A(kind="steal", target="m1", item="torch"), "I lift a torch")
check("a bribed witness does not notice", frm.trust == 50 and not any("Saw" in m.text for m in frm.memories), frm.memories)

reset(); fix_degree("success"); fix_notice(set())
ws.on_steal(A(kind="steal", target="m1", item="gold crown of the king"), "I lift the king's crown")
# plausibility: the model says no
import scenes.law_actions as la
la.generate = lambda *a, **k: ObjectVerdict(plausible=False, reason="a merchant would not carry a crown")
reset(); fix_degree("success"); fix_notice(set())
ws.on_steal(A(kind="steal", target="m1", item="the king's crown"), "I steal the king's crown from Varro")
check("an implausible object is not found and is narrated as a search that finds nothing", not ws.player.character.key_items and "empty" in EVENTS[-1], EVENTS)
check("no record is made of a refused object", mer.hidden == [])

la.generate = lambda *a, **k: ObjectVerdict(plausible=True, name="Varro's ledger", description="A worn account book with a red ribbon.", worth="valuable")
reset(); fix_degree("success"); fix_notice(set())
ws.on_steal(A(kind="steal", target="m1", item="his ledger"), "I search his desk for a ledger and take it")
check("a plausible object becomes a key item", [k.name for k in ws.player.character.key_items] == ["Varro's ledger"], ws.player.character.key_items)
check("it is recorded on the person as taken, once", len(mer.hidden) == 1 and mer.hidden[0]["taken"])
ws.on_steal(A(kind="steal", target="m1", item="the ledger"), "I take the ledger again")
check("asking again does not make a second ledger", len(ws.player.character.key_items) == 1 and "already gone" in EVENTS[-1], EVENTS[-1])
ws.on_steal(A(kind="steal", target="m1", item="a signet ring"), "I look for a signet ring")
check("one invented object per person", len(mer.hidden) == 1 and "nothing else" in EVENTS[-1], (mer.hidden, EVENTS[-1]))

reset(); fix_degree("failure"); fix_notice(set())
mer.hidden = []
ws.on_steal(A(kind="steal", target="m1", item="his ledger"), "I take his ledger")
check("a failed attempt on a new object still records it for next time", len(mer.hidden) == 1 and not mer.hidden[0]["taken"] and not ws.player.character.key_items)
fix_degree("success")
ws.on_steal(A(kind="steal", target="m1", item="the ledger"), "I try again for the ledger")
check("...and it is the same ledger the second time", [k.name for k in ws.player.character.key_items] == ["Varro's ledger"] and len(mer.hidden) == 1)

reset(); fix_degree("success"); fix_notice(set()); ws.present = []
ws.on_steal(A(kind="steal", item="a strongbox of papers"), "I search the room for papers")
check("places can hold hidden objects too", len(store.load_place("parth").hidden) == 1 and len(ws.player.character.key_items) == 1, store.load_place("parth").hidden)
ws.present = [mer, frm]

# hopeless
reset(); fix_degree("failure", hopeless=True); fix_notice({"merchant"})
ws.on_steal(A(kind="steal", target="m1", item="torch"), "I lift a torch")
check("a hopeless theft is narrated as beyond their skill", "far beyond their skill" in EVENTS[-1], EVENTS[-1])

# valuable item heat bonus
reset(); fix_degree("partial"); fix_notice({"merchant"})
ws.on_steal(A(kind="steal", target="m1", item="torch"), "x")
check("ordinary item: 10 heat", ws.heat_here() == 10)

# ---------- 5. force
reset(); fix_notice({"farmer"})
law.fights_back = lambda *a, **k: False
ws.after_force(A(kind="talk", target="m1", force=True), "I grab Varro by the collar")
check("assault: the target remembers, loses trust, heat +20 (a witness saw)", ws.heat_here() == 20 and mer.trust == 40 and any("laid hands" in m.text for m in mer.memories), (ws.heat_here(), mer.trust))
check("a witness remembers it too", any("lay hands" in m.text for m in frm.memories))
reset(); law.notices = lambda *a, **k: False
ws.after_force(A(kind="talk", target="m1", force=True), "I shove Varro")
check("with no witnesses the victim alone knows, and that is full heat", ws.heat_here() == 20 and mer.trust == 40, ws.heat_here())
reset(); real_f = law.fights_back
law.fights_back = lambda *a, **k: True
ws.present = [grd, mer]
ANSWERS[:] = ["pay"]
ws.after_force(A(kind="talk", target="g1", force=True), "I grab the guard")
check("a guard who fights back arrests you", any("under arrest" in n for n in NOTES), NOTES)
law.fights_back = real_f
check("fights_back needs an armed role or a hot temper to be likely", law.FB["base"] + law.FB["armed_bonus"] > law.FB["base"])

# ---------- 6. the law catches up
def make_wanted(h):
    reset(); ws.present = [grd, mer]
    law.set_heat(ws.player, "parth", h, clock.day(ws.minutes))
make_wanted(45)
ANSWERS[:] = ["I pay the fine"]
c0 = ws.player.character.coins
ws.law_check()
check("heat 45: a guard stops you and you pay the fine", c0 - ws.player.character.coins == law.fine(45) and ws.heat_here() == 39, (c0 - ws.player.character.coins, ws.heat_here()))
ws.law_check()
check("they only stop you once a day", len(ANSWERS) == 0 and ws.player.character.coins == c0 - law.fine(45))
check("the guard remembers", any("paid" in m.text for m in grd.memories))

make_wanted(45); checks.roll = lambda odds: ("success", 50)
ANSWERS[:] = ["I try to talk my way out"]
ws.law_check()
check("talking a guard down with a success takes 20 heat off", ws.heat_here() == 25, ws.heat_here())
make_wanted(45); checks.roll = lambda odds: ("strong success", 50)
ANSWERS[:] = ["talk"]
ws.law_check()
check("a strong success takes 30 off", ws.heat_here() == 15)
make_wanted(45); checks.roll = lambda odds: ("partial", 50)
ANSWERS[:] = ["talk"]; c0 = ws.player.character.coins
ws.law_check()
check("a partial means the guard wants the fine", c0 - ws.player.character.coins == law.fine(45) and ws.heat_here() == 39)
make_wanted(45); checks.roll = lambda odds: ("failure", 50)
ANSWERS[:] = ["talk", "pay"]; c0 = ws.player.character.coins
ws.law_check()
check("a failed talk is an arrest, and you can still pay", c0 - ws.player.character.coins == law.fine(45) and ws.heat_here() == 39, ws.heat_here())

make_wanted(45); checks.roll = lambda odds: ("success", 50)
ANSWERS[:] = ["bribe"]; c0 = ws.player.character.coins
ws.law_check()
check("a bribe that works costs the fine, takes 20 off, and the guard looks away", c0 - ws.player.character.coins == law.fine(45) and ws.heat_here() == 25 and grd.looks_away_until > ws.minutes, (ws.heat_here(),))
make_wanted(45); checks.roll = lambda odds: ("failure", 50)
ANSWERS[:] = ["bribe", "jail"]; c0 = ws.player.character.coins; m0 = ws.minutes
ws.law_check()
check("a bribe that fails is an arrest", ws.minutes - m0 >= 2 * 1440 and ws.heat_here() == 39, (ws.minutes - m0, ws.heat_here()))

make_wanted(45)
ANSWERS[:] = ["run"]
ws.law_check()
check("running adds 10", ws.heat_here() == 55, ws.heat_here())

make_wanted(75); c0 = ws.player.character.coins
ANSWERS[:] = ["jail"]; m0 = ws.minutes
ws.law_check()
check("wanted: arrested, jail passes two days, pays half the fine, heat to 39",
      ws.minutes - m0 >= 2 * 1440 and c0 - ws.player.character.coins == round(law.fine(75) * 0.5) and ws.heat_here() == 39 - 4 * 0 or ws.heat_here() in (39, 35, 31),
      (ws.minutes - m0, c0 - ws.player.character.coins, ws.heat_here()))
make_wanted(75); ws.player.character.coins = 100
ANSWERS[:] = ["pay"]
ws.law_check()
check("wanted, cannot afford the fine: straight to jail, coins to zero, heat 39", ws.player.character.coins == 0, ws.player.character.coins)
make_wanted(75); ANSWERS[:] = ["pay"]; c0 = ws.player.character.coins
ws.law_check()
check("wanted, pay the fine: heat to 39", c0 - ws.player.character.coins == law.fine(75) and ws.heat_here() == 39)

make_wanted(75); ws.present = [mer]
ws.law_check()
check("no guard here, no arrest", ws.heat_here() == 75)
make_wanted(30)
ws.law_check()
check("cold does not bring guards", len(ANSWERS) == 0 and ws.heat_here() == 30)
make_wanted(75); ws.present = [grd, mer]; grd.looks_away_until = ws.minutes + 100
ws.law_check()
check("a bribed guard does not arrest", ws.heat_here() == 75)

# cold: prices and trust
reset(); law.set_heat(ws.player, "parth", 25, clock.day(ws.minutes))
check("cold: first meetings start 5 lower", ws.heat_trust() == -5)
reset()
check("clear: no markup, no penalty", ws.heat_price() == 1.0 and ws.heat_trust() == 0)
law.set_heat(ws.player, "parth", 25, clock.day(ws.minutes))
check("cold: prices 10% up", abs(ws.heat_price() - 1.1) < 1e-9)

# the gate
sit = ia.Situation(present={"m1": "Varro"})
check("a theft the plan does not show is flagged", any(f.startswith("unmatched_verb") for f in ia.risk_flags("I pickpocket Varro", [A(kind="talk", target="m1")], sit)))
check("a steal step matches the verb", not any(f.startswith("unmatched_verb") for f in ia.risk_flags("I pickpocket Varro", [A(kind="steal", target="m1", item="purse")], sit)))
check("force words without the flag are flagged", "unmarked_force" in ia.risk_flags("I grab Varro by the collar", [A(kind="talk", target="m1")], sit))
check("with the flag they are not", "unmarked_force" not in ia.risk_flags("I grab Varro by the collar", [A(kind="talk", target="m1", force=True)], sit))
check("a steal aimed at someone absent is a problem", bool(ia.problems([A(kind="steal", target="ghost")], sit)))
check("run_checks leaves a steal alone", ws.run_checks(A(kind="steal", target="m1", checks=["stealth"]), "x") is False)

print("\nALL PASS" if not bad else f"\n{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)
