"""The per-character function draw, one-ability-per-function repair, and the nineteen newer field functions."""
import shutil, sys, random, types
sys.path.insert(0, ".")
import simlib
STUB = simlib.Stub("mage", 5)
simlib.install(STUB)
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from core.models import Companion
from engine import needs
needs.N.update(hunger_per_hour=0, fatigue_per_hour=0, fight={'hunger': 0, 'fatigue': 0})     # this test jumps days at a time; hunger is tested in needs_test
from engine import field, dungeons, inventory as inv, checks, combat, abilities
from engine import ability_traits as AT
from llm.contracts import ActionIntent, ActiveProposal
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(name, cond, extra=""):
    if not cond:
        bad.append(f"{name} {extra}")
    print(("ok   " if cond else "FAIL ") + name, "" if cond else extra)

# ---------- the draw ----------
def interp(arch, fams, themes=(), companions=False):
    return types.SimpleNamespace(custom_class=arch, combat_identity="", summary="", themes=list(themes), families=list(fams),
                                 archetype=types.SimpleNamespace(value=arch), uses_companions=companions)
sizes, seen_sets = set(), set()
for i in range(60):
    offers = field.draw(interp("rogue", ["rogue"], ["thief"]), random.Random(i))
    sizes.add(len(offers))
    check_dupes = len(set(offers)) == len(offers)
    seen_sets.add(tuple(sorted(offers)))
    if not check_dupes:
        bad.append(f"duplicate function in draw {offers}")
check("a draw is 4 or 5 functions", sizes <= {4, 5} and sizes, sizes)
check("characters are offered different sets", len(seen_sets) > 30, len(seen_sets))
check("a social class is offered enough for its 8 outside abilities", len(field.draw(interp("support", ["bard"]), random.Random(1), minimum=8)) == 8)
check("revivify only for companion classes", all("revivify" not in field.draw(interp("mage", ["mage"]), random.Random(i), count=12, lesson=True) for i in range(30)))
check("companion classes can be offered revivify", any("revivify" in field.draw(interp("support", ["summoner"], companions=True), random.Random(i), count=8, lesson=True) for i in range(60)))
hits = sum("pickpocket" in field.draw(interp("rogue", ["rogue"], ["thief"]), random.Random(i), lesson=True) for i in range(300))
base = sum("pickpocket" in field.draw(interp("mage", ["mage"], ["wizard"]), random.Random(i), lesson=True) for i in range(300))
check("the draw leans toward the class", hits > base * 1.8, (hits, base))
o = AT.draw_offers(interp("mage", ["mage"]), random.Random(3), min_functions=5)
check("offers carry functions", len(o["functions"]) >= 5 and "Outside-combat functions on offer" in AT.offer_lines(o))
check("lesson offers are small and skip owned", len(AT.draw_offers(interp("mage", ["mage"]), sizes={"riders": 3, "shapes": 2, "buffs": 1, "functions": 2}, owned_functions={"scout"})["functions"]) == 2)

# ---------- one ability per function ----------
def prop(name, fn, effect="utility", desc="d"):
    return ActiveProposal(name=name, description=desc, effect=effect, tier="light", reach="self", resource="stamina",
                          context="out_of_combat", field_use=fn)
skills = [prop("A", "scout"), prop("B", "scout"), prop("C", "barter"), prop("D", "shadow"), prop("Sneaking about", "")]
field.repair(skills, ["scout", "barter", "pickpocket"])
fns = [s.field_use for s in skills]
check("repair keeps one per function", fns.count("scout") == 1 and fns[0] == "scout")
check("repair drops functions not on offer", skills[3].field_use != "shadow")
check("repair gives unused offered functions", all(f in ("", "scout", "barter", "pickpocket") for f in fns), fns)


# ---------- the full ability set must obey the offer ----------
from llm.contracts import ActiveSet
base_offers = {"riders": [], "shapes": [], "buffs": [], "commands": [], "functions": ["scout", "barter", "bless", "trapfinder"]}
def util(i, fn):
    return ActiveProposal(name=f"Util {i}", description="a clever trick", effect="utility", tier="light", reach="self",
                          resource="stamina", context="out_of_combat", field_use=fn)
def fill(utils):
    ps = list(utils)
    for j in range(15 - len(ps)):
        ps.append(ActiveProposal(name=f"Move {j}", description="d", effect="healing" if j < 3 else "damage", tier="light",
                                 reach="melee", resource="stamina", context="both" if j < 3 else "combat"))
    return ps[:15]
def vset(ps, need=5):
    try:
        return ActiveSet.model_validate({"skills": [x.model_dump() for x in ps]}, context={"offers": base_offers, "min_noncombat": need})
    except Exception as e:
        return str(e)
r = vset(fill([util(0, "scout"), util(1, "scout")]))
check("a repeated function is handed a different offered one", not isinstance(r, str) and len({x.field_use for x in r.skills if x.field_use}) == 2)
r = vset(fill([util(0, "scout")]))
check("too few outside abilities are filled up to the requirement from the functions on offer",
      not isinstance(r, str) and sum(1 for x in r.skills if x.context.value != "combat" and (x.effect.value in ("healing", "crafting", "summon") or x.field_use)) >= 5)
r = vset(fill([util(0, "scout")]), need=20)
check("a requirement the offer cannot meet is refused, and the offer is restated", isinstance(r, str) and "Functions on offer" in r, str(r)[:120])
r = vset(fill([util(0, "scout"), util(1, "barter")]))
check("two different offered functions pass", not isinstance(r, str), r if isinstance(r, str) else "")
r = vset(fill([util(0, "scout"), util(1, "shadow"), util(2, "barter")]))
check("a function that was not offered is replaced by one that was", not isinstance(r, str)
      and all(x.field_use in ("", *base_offers["functions"]) for x in r.skills))

# ---------- the functions in play ----------
shutil.rmtree("saves/ff_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("ff_test")
store.meta.seed = 11; store.meta.turn = 1; store.meta.minutes = 10 * 60; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
char.level = 20
def mk(fn, tier="moderate", name=None):
    return abilities.materialize_active(prop(name or f"Do {fn}", fn, desc="does a thing"))
for fn in field.FUNCTIONS:
    a = mk(fn); a.tier = type(a.tier)(tier) if False else a.tier
    char.actives.append(a)
for a in char.actives:
    if a.name.startswith("Do "):
        a.tier = type(a.tier)("moderate")
dung_place = next(p for p in world.places.values() if p.danger and p.danger[1] >= 8 and p.type != "dungeon")
store.save_player(PlayerState(character=char, location=dung_place.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.ensure_dungeons()
d = next(x for x in store.load_dungeons() if x["place"] == dung_place.id)
d["theme"] = "ruin"
store.save_dungeons([x if x["id"] != d["id"] else d for x in store.load_dungeons()])
ws.player.location = d["entrance"]; ws.enter(d["entrance"])
char = ws.player.character
char.stamina = char.mana = 1e9

def use(fn, target="", text=None):
    NOTES.clear()
    ab = next(a for a in ws.player.character.actives if a.field_use == fn)
    ws.fld.get("cd", {}).pop(ab.id, None)
    ws.player.character.stamina = ws.player.character.mana = 10**6
    ws.player.character.hunger = ws.player.character.fatigue = 0.0
    ws.halted = False
    ws.on_ability(ActionIntent(kind="ability", ability=ab.id, target=target), text or f"I use {ab.name}")
    return list(NOTES)

crit = next(iter(world.bestiary))
fl = d["floors"][0]; lvl = fl["level"]
def layout(*kinds):
    dd = ws.dungeon_here()
    dd["floors"][0]["chambers"] = [{"kind": k, "creature": crit, "count": 1, "level": lvl, "boss": False} for k in kinds]
    for other in dd["floors"][1:]:
        for ch in other["chambers"]:
            if ch["kind"] in ("trap", "cache"):
                ch["kind"] = "rest"
    dd["cleared"] = [-1, -1]; ws.save_dungeon(dd); ws.player.delve = None
def chambers():
    return ws.dungeon_here()["floors"][0]["chambers"]
def at(cleared, **flags):
    dd = ws.dungeon_here(); dd["cleared"] = cleared
    for i, f_ in flags.items():
        dd["floors"][0]["chambers"][int(i[1:])].update(f_)
    ws.save_dungeon(dd)

# trapfinder
layout("fight", "trap", "rest")
n = use("trapfinder")
check("trapfinder disarms the next trap", chambers()[1].get("disarmed") is True and any("disarm" in x for x in n), n)
n = use("trapfinder")
check("...and finds none after", any("no more traps" in x for x in n), n)
ws.fld["lit"] = {"dungeon": d["id"], "until": ws.minutes + 9999}
hp = char.health
at([0, 0])
ws.player.delve = {"dungeon": d["id"], "floor": 0, "chamber": 0, "rest": False}
ws.on_delve(ActionIntent(kind="delve"), "go on")
check("a disarmed trap does no harm", char.health >= hp - 1e-6)
ws.player.delve = None

# picklock
field.F["picklock"]["locked_chance"] = 1.0
layout("rest", "cache")
n = use("picklock")
check("picklock opens the next locked cache", chambers()[1].get("picked") is True, n)
check("...and then none are left", any("No locked cache" in x for x in use("picklock")))
layout("rest", "cache")
dd = ws.dungeon_here()
check("an unopened cache reads as locked", ws.cache_locked(dd, 0, 1) and "locked" in ws.describe_chamber(dd["floors"][0]["chambers"][1], dd, 0, 1))
coins = []
for picked in (False, True):
    tot = 0
    for i in range(40):
        at([0, 0], c1={"picked": picked})
        ws.player.delve = {"dungeon": d["id"], "floor": 0, "chamber": 0, "rest": False}
        c0 = char.coins
        ws.on_delve(ActionIntent(kind="delve"), "go on")
        tot += char.coins - c0
    coins.append(tot)
check("a picked cache pays more", coins[1] > coins[0] * 1.4, coins)
field.F["picklock"]["locked_chance"] = 0.35
ws.player.delve = None; layout("rest")

# beastspeak and swift step
ws.fld.clear()
beast = types.SimpleNamespace(category="beast", name="Wolf"); undead = types.SimpleNamespace(category="undead", name="Wight")
n = use("beastspeak")
if ws.place.danger:
    check("beastspeak calms beasts here", ws.beasts_calm(beast) and not ws.beasts_calm(undead) or any("Nothing that lives" in x for x in n), n)
ws.fld["calm"] = {"loc": ws.player.location, "until": ws.minutes + 60}
check("calm beasts pass, other creatures do not", ws.beasts_calm(beast) and not ws.beasts_calm(undead))
ws.advance_quiet(90)
check("calm wears off", not ws.beasts_calm(beast))
use("swift_step")
f = ws.take_swift(120)
check("swift step eases fatigue and the road", f < 1.0 and ws.journey_event_factor < 1.0, (f, ws.journey_event_factor))
check("...once", ws.take_swift(120) == 1.0 and ws.journey_event_factor == 1.0)

# barter
use("barter")
check("barter gives a discount once", ws.barter_pct() == 15)
ws.use_barter()
check("...then it is spent", ws.barter_pct() == 0)

# people
town = next(p for p in world.places.values() if not p.danger and p.type in ("town", "city", "village"))
npc = None
for p_ in world.places.values():
    if p_.danger or p_.type not in ("town", "city", "village", "inn", "tavern", "square", "street"):
        continue
    ws.player.location = p_.id; ws.enter(p_.id)
    if ws.present:
        npc = ws.present[0]; break
check("a town with someone to test on", npc is not None)
ws.partner = npc
n = use("read_the_room", target=npc.id)
check("read the room tells mood, worry and trust", any(npc.label().capitalize() in x and "mood" in x for x in n), n)
t0 = npc.trust
n = use("intimidate", target=npc.id)
npc2 = store.load_npc(npc.id)
check("intimidate costs goodwill", npc2.trust == max(0, t0 - field.F["intimidate"]["trust_cost"]), (t0, npc2.trust))
check("...and aids only intimidation", any(l == "cowed" for l, v in ws.check_bonuses("intimidation", npc2))
      and not any(l in ("cowed", "won over") for l, v in ws.check_bonuses("persuasion", npc2)))
ws.spend_edge("persuasion", npc2)
check("a persuasion check does not spend it", "edge" in ws.fld)
ws.spend_edge("intimidation", npc2)
check("an intimidation check does", "edge" not in ws.fld)

# pickpocket
real_resolve = ws.resolve
ws.resolve = lambda check_, n_=None, **k: "success"
c0 = char.coins
n = use("pickpocket", target=npc.id)
check("pickpocket takes coin", char.coins > c0, n)
n = use("pickpocket", target=npc.id)
check("...but only once a day per person", any("already tried" in x for x in n) and True, n)
ws.fld["picked"] = {}
ws.resolve = lambda check_, n_=None, **k: "failure"
c0 = char.coins; t0 = store.load_npc(npc.id).trust
n = use("pickpocket", target=npc.id)
check("a caught thief gets nothing and is remembered", char.coins == c0 and store.load_npc(npc.id).trust < t0
      and any("Caught" in m.text or "caught" in m.text for m in store.load_npc(npc.id).memories), n)
ws.resolve = real_resolve
ws.partner = None

# commune
store.save_world_state({"threads": [{"id": "t1", "title": "Plague in the cellars", "place": town.id, "status": "active", "stage": 0,
                                      "tier": "minor", "groups": ["everyone"], "times": [1, 2],
                                      "stages": [{"description": "Sickness spreads below the streets.", "effects": []}]}],
                        "news": [], "effects": []})
n = use("commune")
check("commune tells of troubles", any("Plague in the cellars" in x for x in n), n)
store.save_world_state({"threads": [], "news": [], "effects": []})
check("a quiet land teaches nothing", any("quiet" in x for x in use("commune")))

# tinker
ws.pack.clear()
n = use("tinker")
check("tinker makes torches and bandages", sum(i.quantity for i in ws.pack if i.good == "torch") == 3
      and sum(i.quantity for i in ws.pack if i.good == "bandage") == 1, n)

# treat
from engine import pools
char.health = pools.maximum(char, "health") * 0.3
char.companions = [Companion(id="w", name="Grey", creature="wolf", fallen=True), Companion(id="x", name="Bones", dead=True)]
h0 = char.health
n = use("treat")
check("treat heals", char.health > h0 + 1, n)
check("treat gets a fallen companion up but not a dead one", not char.companions[0].fallen and char.companions[1].dead)
char.health = pools.maximum(char, "health"); char.companions[0].fallen = False
check("nothing to treat is refused", any("nothing to tend" in x for x in use("treat")))

# revivify
n = use("revivify")
check("revivify raises the dead", not char.companions[1].dead and any("rises" in x for x in n), n)
check("nobody left to revive", any("needs reviving" in x for x in use("revivify")))

# bless
use("bless")
check("bless helps every check", all(any(l == "blessed" for l, v in ws.check_bonuses(c_)) for c_ in checks.CHECKS))
ws.advance_quiet(field.F["bless"]["lasts_minutes"] + 5)
check("bless fades", not any(l == "blessed" for l, v in ws.check_bonuses("lore")))

# summon labor
ws.fld.pop("box", None)
check("no item box outside a house", not ws.can_store() or getattr(ws.place, "storage", False))
if not getattr(ws.place, "storage", False):
    use("summon_labor")
    check("summon labor puts the box in reach", ws.can_store())
    ws.advance_quiet(field.F["summon_labor"]["open_minutes"]["moderate"] + 5)
    check("...for a while", not ws.can_store())

# lucky break (a passive)
from core.models import Passive, PowerTier
ws.fld.pop("lucky", None)
check("no luck without the passive", ws.lucky_save() == "")
char.passives.append(Passive(id="lucky-break", name="Fool's Luck", description="d", tier=PowerTier.LIGHT, mechanic="lucky_break", value=1))
orig_roll = checks.roll
checks.roll = lambda odds, rng=None: ("failure", 99)
NOTES.clear()
r1 = ws.resolve("lore")
r2 = ws.resolve("lore")
checks.roll = orig_roll
check("the first failure each day is saved", r1 == "success" and any("lucky break" in x.lower() and "Fool's Luck" in x for x in NOTES), NOTES)
check("the second is not", r2 == "failure")
ws.advance_quiet(24 * 60)
checks.roll = lambda odds, rng=None: ("failure", 99)
check("it comes back tomorrow", ws.resolve("lore") == "success")
checks.roll = orig_roll
char.passives[-1].value = 2
ws.advance_quiet(24 * 60)
checks.roll = lambda odds, rng=None: ("failure", 99)
check("a stronger version saves two", [ws.resolve("lore") for _ in range(3)] == ["success", "success", "failure"])
checks.roll = orig_roll
check("lucky is no longer an ability function", "lucky" not in field.FUNCTIONS)
char.passives.pop()

# size up and snare: spent as a fight begins
ws.player.location = dung_place.id; ws.enter(dung_place.id)
foes = [combat.fighter_from_creature(world.bestiary[crit], 10, "normal", "e1", "foe", "near")]
foes[0].armor = 100; foes[0].ward = 50; hp0 = foes[0].hp
ws.fld["sized"] = {"loc": ws.player.location, "tier": "heavy", "until": ws.minutes + 100}
ws.fld["snare"] = {"loc": ws.player.location, "tier": "moderate", "until": ws.minutes + 100}
notes = ws.field_prep(foes)
check("size up thins defenses", foes[0].armor == 65 and foes[0].ward == round(50 * 0.65), (foes[0].armor, foes[0].ward))
check("a snare hurts them first", foes[0].hp == round(hp0 * 0.75) and len(notes) == 2, (foes[0].hp, hp0))
check("both are spent", "sized" not in ws.fld and "snare" not in ws.fld)
ws.fld["snare"] = {"loc": "somewhere else", "tier": "moderate", "until": ws.minutes + 100}
foes[0].hp = hp0
ws.field_prep(foes)
check("a snare laid elsewhere does nothing", foes[0].hp == hp0)

# word of recall
ws.fld["towns"] = []
towns = [p.id for p in world.places.values() if not p.danger and p.type in ("town", "city")][:2]
ws.enter(towns[0]); ws.enter(towns[1])
ws.player.delve = {"dungeon": d["id"], "floor": 0, "chamber": 0, "rest": False}
n = use("word_of_recall")
check("word of recall returns you to the last town you left", ws.player.location == towns[0] and ws.player.delve is None, (ws.player.location, n))
ab = next(a for a in char.actives if a.field_use == "word_of_recall")
check("...with a long cooldown", field.cooldown_minutes(ab) >= 240)

# phantom steed
n = use("phantom_steed")
check("phantom steed is yours to ride", ws.mount_info() and ws.mount_info()["id"] == "phantom_steed", n)
use("phantom_steed")
check("only ever one", sum(1 for m in ws.player.mounts if m["id"] == "phantom_steed") == 1)
check("...and faster than the cheap horses", ws.mount_info()["speed"] >= 0.30)

# distract: every enemy attack lands on the player while it lasts
def fighter(id_, side, hp=10**6):
    return combat.Fighter(id=id_, name=id_, side=side, level=20, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
                          weapon_damage=50, armor=0, ward=0)
p = fighter("p", "player"); pet = fighter("ally_pet", "ally"); foe = fighter("e", "enemy"); foe.band = "engaged"
cmb = combat.Combat(fighters=[p, pet, foe])
rng = random.Random(4)
for i in range(60):
    combat.enemy_turn(cmb, foe, rng)
hit_pet_free = pet.hp < pet.max_hp
pet.hp = pet.max_hp
p.buffs["d"] = {"rounds": 3, "mech": {"taunt": 1}, "drain": 0, "collapse": "", "name": "Distract", "kind": "distract"}
for i in range(60):
    combat.enemy_turn(cmb, foe, rng)
check("without a taunt the companion is sometimes hit", hit_pet_free)
check("while Distract lasts it never is", pet.hp == pet.max_hp)
check("distract is a command offered to companion classes", "distract" in AT.COMMANDS and "every enemy turns on you" in AT.command_text("distract", "light")
      and ActiveProposal(name="Jeer", description="d", effect="command", tier="light", reach="self", resource="stamina",
                         context="combat", command="distract").command == "distract")

print("ALL PASS" if not bad else f"FAILED: {bad}")
sys.exit(1 if bad else 0)
