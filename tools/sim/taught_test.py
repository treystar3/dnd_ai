"""Taught-only and level-gated field functions; Bind a Beast (rules and the fight); the fallen and Speak with a Corpse."""
import random, shutil, sys
from types import SimpleNamespace as NS
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from core.models import Ability
from engine import combat, field, lessons, taming, clock
from engine import ability_traits as AT
from llm.contracts import ActionIntent as A, ClassInterpretation, LessonNames
from core.models import Archetype
from npc.models import NPC
from npc.traits import load_traits
from scenes.combat_scene import CombatScene
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

F = field.F["functions"]
TAUGHT = {"picklock", "pickpocket", "shadow", "revivify", "word_of_recall", "phantom_steed", "summon_labor", "bind_beast", "speak_corpse"}
LEVELED = {"shelter", "trapfinder", "snare", "commune", "bless"}
check("the taught-only list is as agreed", {f for f, s in F.items() if s.get("taught_only")} == TAUGHT, {f for f, s in F.items() if s.get("taught_only")})
check("the level-gated list is as agreed", {f for f, s in F.items() if s.get("min_level")} == LEVELED and all(F[f]["min_level"] == 5 for f in LEVELED))
check("commune was renamed", F["commune"]["label"] == "commune with spirits" and "speak_corpse" in F and "bind_beast" in F)

def ic(arch, fams, pack=False):
    return ClassInterpretation(archetype=Archetype(arch), custom_class="X", combat_identity="x", themes=["spear"], summary="x",
                               families=list(fams), uses_companions=pack)
classes = [ic("rogue", ["rogue"]), ic("mage", ["necromancer"], True), ic("support", ["healer"]), ic("warrior", ["ranger"], True)]
creation = {fn for i in classes for seed in range(80) for fn in field.draw(i, random.Random(seed), count=12)}
check("creation never draws a taught-only or level-gated function", not (creation & (TAUGHT | LEVELED)), creation & (TAUGHT | LEVELED))
check("creation still draws the open ones", len(creation) >= 10, creation)
l1 = {fn for i in classes for seed in range(80) for fn in field.draw(i, random.Random(seed), count=12, lesson=True, level=1)}
l5 = {fn for i in classes for seed in range(80) for fn in field.draw(i, random.Random(seed), count=12, lesson=True, level=5)}
check("a first lesson can teach taught-only functions but not level-gated ones", TAUGHT & l1 and not (l1 & LEVELED), (l1 & LEVELED))
check("by level 5 a lesson can teach the level-gated ones too", LEVELED <= l5 | {"x"} or len(LEVELED & l5) >= 4, LEVELED & l5)
check("companion-only revivify still needs companions", all("revivify" not in field.draw(classes[0], random.Random(s), count=14, lesson=True) for s in range(40)))

# ---------- Bind a Beast: the rules
world = load_world()
c, _ = simlib.make_character("warrior", random.Random(1))
c.level = 10; c.attributes.wisdom = 20; c.attributes.charisma = 20
wolf = world.bestiary["wolf"]
def foe(level=10, share=1.0, rank="normal", creature=wolf):
    e = combat.fighter_from_creature(creature, level, rank, "e1", creature.id)
    e.hp = e.max_hp * share
    return e
bind = Ability.model_validate({**c.actives[0].model_dump(), "id": "bind", "name": "Beast Bond", "effect": "control", "context": "both",
                              "field_use": "bind_beast", "resource": "stamina", "tier": "moderate", "reach": "ranged"})
c.actives.append(bind)
check("the character's binder is found", taming.binder(c).id == "bind")
check("a healthy wolf of the same level can be bound", taming.bind_check(c, foe(), wolf) == "")
check("...but not one a level above (no margin for other classes)", "too strong" in taming.bind_check(c, foe(11), wolf))
check("a boss cannot be bound", "cannot be bound" in taming.bind_check(c, foe(rank="boss"), wolf))
leg = next(v for v in world.bestiary.values() if v.rarity == "legendary" and v.category in taming.T["categories"] and not v.unique)
check("a legendary creature is refused to a non-companion class", "beyond" in taming.bind_check(c, foe(10, creature=leg), leg), taming.bind_check(c, foe(10, creature=leg), leg))
check("people are refused", "not something" in taming.bind_check(c, foe(10, creature=world.bestiary[next(k for k, v in world.bestiary.items() if v.category == "hostile people")]), world.bestiary[next(k for k, v in world.bestiary.items() if v.category == "hostile people")]))
hurt, full = taming.bind_chance(c, foe(share=0.3), wolf, "moderate"), taming.bind_chance(c, foe(share=1.0), wolf, "moderate")
half = taming.bind_chance(c, foe(share=0.5), wolf, "moderate")
check("a hurt creature is easier than an unhurt one", hurt > full, (hurt, full))
check("at half health there is no penalty", abs(half - hurt) < 1e-9, (half, hurt))
check("an unhurt creature costs the full penalty", abs((half - full) - taming.T["bind"]["unhurt_penalty"]) < 1e-9 or full == taming.T["min_chance"], (half, full))
check("tiers cap the odds", all(taming.bind_chance(c, foe(share=0.1), wolf, t) <= taming.T["bind"]["ceiling"][t] + 1e-9 for t in ("light", "moderate", "heavy")))
c.attributes.wisdom = c.attributes.charisma = 400
check("a light ability can never beat its ceiling however wise", taming.bind_chance(c, foe(share=0.1), wolf, "light") == taming.T["bind"]["ceiling"]["light"])
check("the odds are never below the floor", taming.bind_chance(c, foe(share=1.0), wolf, "light") >= taming.T["min_chance"])
c.attributes.wisdom = c.attributes.charisma = 20

# ---------- Bind a Beast: in a fight
class Clock:
    def __init__(self): self.t = 1000
ws = NS(player=NS(character=c, field={}), world=world, minutes=1000)
ws.field_ready_in = lambda a: max(0, ws.player.field.get("cd", {}).get(a.id, 0) - ws.minutes)
ws.field_cooldown_start = lambda a: ws.player.field.setdefault("cd", {}).__setitem__(a.id, ws.minutes + field.cooldown_minutes(a))
p = combat.fighter_from_character(c)
e = foe(10, 0.3)
fight = combat.Combat(fighters=[p, e])
sc = CombatScene.__new__(CombatScene)
sc.ws, sc.fight, sc.rng, sc.tamed = ws, fight, random.Random(3), []
move = next(m for m in p.moves if m.id == "bind")
check("the combat scene recognises the binder", sc.binding_ability(move).id == "bind" and sc.binding_ability(p.moves[0]) is None or sc.binding_ability(p.moves[0]) is not None and p.moves[0].id == "bind")
stam = p.stamina
n0 = len(c.companions)
for _ in range(60):
    sc.rng = random.Random(random.random())
    ws.player.field.clear(); ws.minutes += 2000
    p.stamina = stam
    if e not in fight.fighters: break
    sc.try_bind(move, bind, e)
check("repeated tries eventually bind it, as a permanent tamed companion", sc.tamed == ["Wolf"] and len(c.companions) == n0 + 1 and taming.tamed(c)[-1].source == "tamed", sc.tamed)
check("a bound creature leaves the fight", e not in fight.fighters)
# the daily limit and the cost
e2 = foe(10, 0.2); fight.fighters.append(e2)
c.level = 40; c.companions[:] = [x for x in c.companions if x.source != "tamed"]; c.level = 10
ws.player.field.clear(); p.stamina = stam
sc.rng = random.Random(1); chance = taming.bind_chance(c, e2, wolf, "moderate")
sc.rng = NS(random=lambda: 0.999)                                  # always fails
sc.try_bind(move, bind, e2)
check("a failed bind costs the ability's price", p.stamina < stam, (p.stamina, stam))
check("a failed bind still uses the day's charge", ws.field_ready_in(bind) > 0 and e2 in fight.fighters)
NOTES.clear(); st2 = p.stamina
sc.try_bind(move, bind, e2)
check("a second try the same day is refused and becomes an attack", any("more before you can do it again" in n for n in NOTES) and p.stamina == st2 or any("attack instead" in n for n in NOTES), NOTES)
# the cap
ws.player.field.clear()
c.companions.append(taming.bind(c, wolf, "wolf"))
c.companions.append(taming.bind(c, wolf, "wolf"))
check("the companion cap stops a second bind", "release one first" in taming.bind_check(c, foe(10, 0.2), wolf), taming.bind_check(c, foe(10, 0.2), wolf))
taming.release(c, "wolf"); taming.release(c, "wolf")

# ---------- the abilities as lessons
cw, _ = simlib.make_character("warrior", random.Random(2)); cw.level = 8
got = None
for seed in range(400):
    slots = lessons.plan(cw, lessons.Want("active", "control", "", "bind a beast to fight with me"), random.Random(seed))
    got = next((s for s in slots if s.get("field_use") == "bind_beast"), None)
    if got: break
check("a request to bind a beast can be answered with Bind a Beast", got is not None)
if got:
    check("it is a combat-and-outside control lesson with a function", (got["effect"], got["context"]) == ("control", "both"), got)
    line = lessons.slot_line(got)
    check("the model is told it works in a fight", "in a fight - bind a beast" in line and "outside combat" not in line, line)
    names = LessonNames.model_validate({"skills": [{"slot": s["n"], "name": f"Lesson {s['n']}", "description": "A learned thing."} for s in slots]},
                                       context={"slots": slots, "strict": True, "reserved_names": []})
    ab = next(b for b in lessons.build(slots, names) if getattr(b, "field_use", "") == "bind_beast")
    check("the built ability keeps the function", ab.field_use == "bind_beast" and ab.context.value == "both")
    check("it shows as a fight ability, not an outside one", field.fight_text(ab).startswith("Bind a beast") and field.outside_text(ab) == "")
chance_of = sum(any(s.get("field_use") == "bind_beast" for s in lessons.plan(cw, lessons.Want("active", "control", "", "x"), random.Random(i))) for i in range(300))
check("a plain control request sometimes brings it", 0 < chance_of < 150, chance_of)

# ---------- the fallen and Speak with a Corpse
shutil.rmtree("saves/taught_test", ignore_errors=True)
store = CampaignStore.open_or_create("taught_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 6000; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
speak = Ability.model_validate({**char.actives[0].model_dump(), "id": "spk", "name": "Grave Whisper", "effect": "utility", "context": "out_of_combat",
                                "field_use": "speak_corpse", "resource": "stamina", "tier": "light", "reach": "extended"})
char.actives.append(speak)
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
config.TURN_LOG_PATH = "saves/taught_test/turns.jsonl"
ws.narrate = lambda event, text="": None
ws.present = []
now = ws.minutes
def bodies(*specs):
    state = store.load_place("parth")
    state.bodies = [{"creature": "wolf", "name": n, "level": 6, "category": "beast", "rank": "normal", "minute": now - age, "asked": False,
                     **({"carried": "a rusty knife"} if carried else {})} for n, age, carried in specs]
    store.save_place(state)
bodies()
check("with no body there is nothing to question", ws.field_precheck(speak, A(kind="ability"), "speak") == "There is no body here that can still answer you.")
bodies(("Wolf", 60, True))
check("a fresh body can be questioned", ws.field_precheck(speak, A(kind="ability"), "speak") is None)
NOTES.clear(); out = ws.field_speak_corpse(speak, A(kind="ability"), "speak with the wolf")
check("a fresh body tells what it was, when it fell and what it carried", out and "wolf" in out and "rusty knife" in out and "ago" in out, (out, NOTES))
check("a body answers only once", not ws.bodies_here() and ws.field_speak_corpse(speak, A(kind="ability"), "again") is None)
bodies(("Wolf", 1440 * 2, True))
NOTES.clear(); out = ws.field_speak_corpse(speak, A(kind="ability"), "speak")
check("a body of two days says what and how, not what it carried", out and "ago" in out and "rusty knife" not in out and "faint" not in out, out)
bodies(("Wolf", 1440 * 4, True))
out = ws.field_speak_corpse(speak, A(kind="ability"), "speak")
check("an old body gives only what it was, and is faint", out and "ago" not in out and "rusty" not in out and "faint" in out, out)
bodies(("Wolf", 1440 * 7, True))
check("a body forgotten after six days is gone", not ws.bodies_here())
bodies(*[("Wolf", i, False) for i in range(20)])
check("a place keeps at most twelve bodies", len(ws.keep_bodies(store.load_place("parth").bodies)) == 12)
bodies(("Wolf", 10, False))
out = ws.field_speak_corpse(speak, A(kind="ability"), "speak")
check("a body that carried nothing says so", out and "nothing of worth" in out, out)
# Bind a Beast outside a fight
check("Bind a Beast is refused outside a fight", "used in a fight" in (ws.field_precheck(bind, A(kind="ability"), "bind") or ""))
print("\nFAILED:" if bad else "\nall passed", bad)
sys.exit(1 if bad else 0)
