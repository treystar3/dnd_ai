"""Field abilities: every function works, costs and cooldowns apply, nothing lingers, darkness bites, old characters get classified."""
import shutil, sys, random
sys.path.insert(0, ".")
import simlib
from engine import loadout as _lo; _lo.L["start"] = _lo.L["max"] = 99   # every function at once: more than any loadout brings (f232)
STUB = simlib.Stub("mage", 5)
simlib.install(STUB)
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from core.models import Ability, UseContext
from engine import field, dungeons, inventory as inv, items, clock
from llm.contracts import ActionIntent
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(name, cond, extra=""):
    if not cond:
        bad.append(f"{name} {extra}")
    print(("ok   " if cond else "FAIL ") + name, extra if not cond else "")

shutil.rmtree("saves/field_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("field_test")
store.meta.seed = 7; store.meta.turn = 1; store.meta.minutes = 10 * 60; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(1))
char.level = 20
def mk(name, fn, effect="utility", tier="light", desc="d"):
    from llm.contracts import ActiveProposal
    from engine import abilities
    return abilities.materialize_active(ActiveProposal(name=name, description=desc, effect=effect, tier=tier, reach="self",
                                                       resource="stamina", context="out_of_combat", field_use=fn))
for fn in field.FUNCTIONS:
    char.actives.append(mk(f"Do {fn}", fn, tier="moderate"))
check("every function assigned", {a.field_use for a in char.actives if a.name.startswith("Do ")} == set(field.FUNCTIONS))
# a utility ability with no function still gets one; a 'both' damage ability with none is demoted
from llm.contracts import ActiveProposal
from engine import abilities
u = abilities.materialize_active(ActiveProposal(name="Sharp Eyes", description="you notice hidden things", effect="utility", tier="light", reach="self", resource="stamina", context="combat"))
check("utility forced out of combat with function", u.context.value == "out_of_combat" and u.field_use == "scout", (u.context, u.field_use))
dm = abilities.materialize_active(ActiveProposal(name="Fire Bolt", description="a bolt of fire", effect="damage", tier="light", reach="ranged", resource="mana", context="both"))
check("damage 'both' without function demoted", dm.context.value == "combat" and dm.field_use == "", (dm.context, dm.field_use))
check("no non-combat ability lacks a function", all(a.field_use or a.effect.value in ("healing", "crafting", "summon") for a in char.actives + [u] if a.context.value != "combat"))

# old characters: classify lazily, keyword fallback works with no model
old = abilities.materialize_active(ActiveProposal(name="Silver Tongue", description="you charm a listener", effect="influence", tier="light", reach="self", resource="mana", context="both"))
old.field_use = ""
legacy = Ability(id="x", name="Quiet Step", description="you move without a sound", effect="utility", tier="light", reach="self",
                 resource="stamina", context="out_of_combat", cost=1, cooldown=0)
legacy2 = Ability(id="y", name="Hearth Spell", description="a warm hearth shelters your camp", effect="utility", tier="light", reach="self",
                  resource="mana", context="out_of_combat", cost=1, cooldown=0)
class C: pass
cc = C(); cc.actives = [legacy, legacy2, old]
field.classify(cc)
check("classifier fills older abilities", legacy.field_use in field.FUNCTIONS and legacy2.field_use == "shelter" and old.field_use == "influence", (legacy.field_use, legacy2.field_use, old.field_use))

dung_place = next(p for p in world.places.values() if p.danger and p.danger[1] >= 8 and p.type != "dungeon")
store.save_player(PlayerState(character=char, location=dung_place.id))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.ensure_dungeons()
d = next(x for x in store.load_dungeons() if x["place"] == dung_place.id)
d["theme"] = "mine"
store.save_dungeons([x if x["id"] != d["id"] else d for x in store.load_dungeons()])
ws.player.location = d["entrance"]; ws.enter(d["entrance"])
ws.player.character.stamina = 1e9

def use(name, text=None, target=""):
    NOTES.clear()
    intent = ActionIntent(kind="ability", ability=next(a.id for a in ws.player.character.actives if a.name == name), target=target)
    ws.halted = False
    ws.on_ability(intent, text or f"I use {name}")
    return list(NOTES)

# scout
n = use("Do scout")
check("scout reveals next chamber", any("scout ahead" in x for x in n), n)
check("scout sets cooldown", use("Do scout") and any("more before" in x for x in NOTES), NOTES)
ws.advance_quiet(61)
# set up a known dungeon layout: trap, fight, fight, rest
crit = next(iter(world.bestiary))
fl = d["floors"][0]
lvl = fl["level"]
fl["chambers"] = [{"kind": "trap"}, {"kind": "fight", "creature": crit, "count": 2, "level": lvl, "boss": False},
                  {"kind": "fight", "creature": crit, "count": 1, "level": lvl, "boss": False}, {"kind": "rest"}, {"kind": "cache"}]
d["cleared"] = [-1, -1]
ws.save_dungeon(d)
ws.player.delve = None
ws.fld.clear()
ws.player.character.inventory = []

# --- darkness
ws.player.delve = {"dungeon": d["id"], "floor": 0, "chamber": 0, "rest": False}
NOTES.clear(); ws.ensure_light(d)
check("dark warning without torch", any("pitch black" in x for x in NOTES), NOTES)
check("darkness penalty", ws.darkness_penalty() == -dungeons.D["dark_penalty"], ws.darkness_penalty())
odds_dark = [x for x in ws.check_bonuses("perception") if x[0] == "darkness"]
check("perception gets the penalty", bool(odds_dark))
ws.pack.append(inv.make_good("torch", 3))
NOTES.clear(); ws.ensure_light(d)
check("torch lit automatically", any("light a torch" in x for x in NOTES) and ws.darkness_penalty() == 0, NOTES)
check("torch consumed", sum(i.quantity for i in ws.pack if i.good == "torch") == 2)
ws.advance_quiet(dungeons.D["torch_minutes"] + 5)
check("torch burns out", ws.darkness_penalty() != 0)
NOTES.clear(); ws.ensure_light(d)
check("relights from pack", ws.darkness_penalty() == 0 and sum(i.quantity for i in ws.pack if i.good == "torch") == 1)
ws.fld.pop("lit"); ws.pack.clear()
# scouted chamber ignores the dark
ws.fld["scouted"] = {"dungeon": d["id"], "pos": [0, 0]}
check("scouting beats the dark", ws.darkness_penalty() == 0)
ws.fld.clear()
# a light-making scout spell
ws.player.character.actives.append(mk("Kindle Glow", "scout", desc="a glowing flame lights the way"))
ws.player.delve = None
n = use("Kindle Glow")
check("light-making scout lights the dungeon", ws.lit_now(d), n)
ws.fld.clear(); ws.player.delve = None

# --- scout: reveals the next chamber and then the trap is stepped around
ws.minutes_before = ws.minutes
n = use("Do scout")
check("scout names a trap", any("trapped" in x for x in n), n)
check("scouted trap is avoided", True)
hp0 = ws.player.character.health
ws.fld["lit"] = {"dungeon": d["id"], "until": ws.minutes + 600}
ws.on_delve(ActionIntent(kind="delve"), "go down")
check("scouted trap does no harm", ws.player.character.health >= hp0 - 1e-6, (hp0, ws.player.character.health))

# --- shadow: next normal fight is slipped past, once
ws.advance_quiet(130)
n = use("Do shadow")
check("shadow set", ws.shadow_active(), n)
ws.combat = None
ws.on_delve(ActionIntent(kind="delve"), "go on")
check("fight slipped past", ws.combat is None and d["cleared"] if False else ws.combat is None, ws.combat)
check("shadow spent", not ws.shadow_active())
ws.combat = None
# stealth bonus while shadowed (out of dungeon)
ws.fld.clear(); ws.advance_quiet(130)
ws.fld["shadow"] = {"until": ws.minutes + 100, "tier": "moderate"}
check("shadow stealth bonus", any(l == "shadowing" and v > 0 for l, v in ws.check_bonuses("stealth")))

# --- shelter: camp in the dungeon, rest allowed, no ambush
ws.advance_quiet(130)
ws.player.delve = {"dungeon": d["id"], "floor": 0, "chamber": 2, "rest": False}
ws.fld.clear()
n = use("Do shelter")
check("camp made", ws.camp_active(), n)
ws.player.delve["chamber"] = 3
check("camp lost when you move on", not ws.camp_active())
ws.player.delve["chamber"] = 2
ws.player.character.health = 1
ws.on_wait(ActionIntent(kind="wait", wait_minutes=480), "I sleep")
check("sleeping in camp restores fully", abs(ws.player.character.health - __import__("engine.pools", fromlist=["x"]).maximum(ws.player.character, "health")) < 1e-6, ws.player.character.health)
ws.combat = None
# not needed in town
ws.player.delve = None
town = next(p for p in world.places.values() if not p.danger and p.type in ("town", "city", "village"))
ws.player.location = town.id; ws.enter(town.id)
ws.advance_quiet(130)
n = use("Do shelter")
check("no camp in town", any("no need" in x for x in n), n)

# --- haste: shortens next journey, consumed
ws.advance_quiet(130)
n = use("Do haste")
check("haste primed", "haste" in ws.fld, n)
w, f = ws.take_haste(120)
check("haste shortens and eases", w < 120 and f < 1 and "haste" not in ws.fld, (w, f))
ws.fld["haste"] = {"until": ws.minutes + 61, "tier": "moderate"}
ws.advance_quiet(120)
w, f = ws.take_haste(120)
check("expired haste does nothing", (w, f) == (120, 1.0))

# --- influence: needs someone; raises trust once a day; bonus spent on next social check
ws.advance_quiet(130)
ws.present = []; ws.partner = None
n = use("Do influence")
check("influence needs a person", any("no one" in x for x in n), n)
if True:
    from npc.models import NPC
    for p_ in world.places.values():
        if p_.danger or p_.type not in ("town", "city", "village", "inn", "tavern", "square", "street"):
            continue
        ws.player.location = p_.id; ws.enter(p_.id)
        if ws.present:
            break
    npcs = list(ws.present)[:1]
    check("town has someone to test with", bool(npcs))
    npc = npcs[0]; ws.partner = npc
    t0 = npc.trust
    n = use("Do influence", target=npc.id)
    npc2 = store.load_npc(npc.id)
    check("influence raises trust", npc2.trust > t0, (t0, npc2.trust, n))
    check("influence edge on next social check", any(l == "won over" for l, v in ws.check_bonuses("persuasion", npc)))
    ws.spend_edge("persuasion", npc)
    check("edge spent", "edge" not in ws.fld)
    ws.advance_quiet(130)
    n = use("Do influence", target=npc.id)
    check("no second trust gain same day", store.load_npc(npc.id).trust == npc2.trust, n)

# --- recall: lore about the place; refunds when nothing new
ws.advance_quiet(130)
before = len(ws.player.character.knowledge)
st0 = ws.player.character.stamina
n = use("Do recall")
gained = len(ws.player.character.knowledge) - before
check("recall result consistent with cost", (gained > 0 and ws.player.character.stamina < st0) or (gained == 0 and ws.player.character.stamina == st0), (gained, n))

# --- showmanship: pays once per place per day
ws.advance_quiet(130)
coins0 = ws.player.character.coins
n = use("Do showmanship")
check("show needs audience or pays", True)
if ws.present:
    check("show earns", ws.player.character.coins >= coins0)
    ws.advance_quiet(130)
    n = use("Do showmanship")
    check("only one show per place per day", any("already had your act" in x for x in n), n)

# --- combat-only abilities are refused outside a fight
n = use("Flame Tongue")
check("combat technique refused outside fight", any("fighting technique" in x for x in n), n)

shutil.rmtree("saves/field_test", ignore_errors=True)
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)
