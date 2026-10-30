"""(f397) The spellbook (engine/spells.py; data/rules/spells.yaml): damage spells on ranks and forms. A rank sets a spell's base and its
flat mana; a form sets how strong, costly, slow and frequent it is; spell power counts through a coefficient that never changes with
rank. Ranks are learned from spell books and teachers once the level allows, each a spell of its own that takes the place of the rank
below among the spells brought. Techniques keep their tiers."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("mage", 3)
simlib.install(stub)
import ui.console as uc
NOTES = []
for f_ in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f_, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from engine import ability_slots, combat, inventory as inv, leveling, spells, spellcraft
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
check("the spellbook's data checks clean", spells.problems() == [], spells.problems())

# ---- a mage as creation makes one
c, _ = simlib.make_character("mage", random.Random(3))
ranked = [a for a in c.actives if spells.is_ranked(a)]
check("a mage's damage spells are on ranks: rank I, a form of the spellbook, a flat cost and the form's cooldown",
      ranked and all(a.rank == 1 and a.spell_form in spells.FORMS and a.line and a.cooldown == spells.cooldown(a.spell_form) for a in ranked),
      [(a.name, a.rank, a.spell_form, a.cooldown) for a in c.actives])
check("...techniques keep their tiers", all(not spells.is_ranked(a) for a in c.actives if a.resource.value == "stamina"))

# ---- the planner gives forms by how hard a spell was meant to hit
rng = random.Random(1)
slots = [dict(ability_slots._base(), effect="damage", resource="mana", reach="ranged", tier=t) for t in ("light", "moderate", "heavy") * 20]
ability_slots.assign_forms(slots, rng)
heavy = {s["spell_form"] for s in slots if s["tier"] == "heavy"}
light = {s["spell_form"] for s in slots if s["tier"] == "light"}
check("a heavy spell is planned as a lance or a charged spell, a light one as a bolt or a curse", heavy <= {"lance", "charged"} and light <= {"bolt", "curse"},
      (heavy, light))
text = ability_slots.mechanic_text(dict(slots[2], element="fire"))
check("the model is told the form and the rank when it names a spell", "rank I spell" in text and ("Lance" in text or "Charged" in text), text)

# ---- in a fight: the rank's base, the coefficient, the form's power, a flat cost
from engine import items, ability_traits as AT
c.equipment["main_hand"] = items.make("arcane_staff", "common", 20)
me = combat.fighter_from_character(c)
dummy = combat.fighter_from_creature(world.bestiary["bandit"], 5, "normal", "d", "dummy", start="near")
dummy.max_hp = dummy.hp = 10 ** 6
fight = combat.Combat(fighters=[me, dummy], place="x", conditions=[])
combat.ensure_field(fight)
seen = []
_apply = combat.apply_damage
combat.apply_damage = lambda cmb, att, dfn, mult, *a, **k: seen.append((att.weapon_damage, mult)) or _apply(cmb, att, dfn, mult, *a, **k)
bolt = combat.Move(id="b1", name="Ember Bolt", effect="damage", tier="light", reach="ranged", resource="mana", attribute="intelligence",
                   spell_form="bolt", rank=3, line="b1")
lance = bolt.model_copy(update={"id": "l1", "spell_form": "lance", "cooldown": 2})
me.mana = me.max_mana = 10 ** 4
sp = me.offhand_spell + (me.weapon_damage if me.damage_type == "magical" else 0)
combat.act_ability(fight, me, bolt, dummy, random.Random(1))
want = spells.base(3) + spells.coefficient(bolt) * sp
honed = 1 + AT.T["plain_damage"]                        # a plain damage ability's own edge (Honed), as for any ability
check("a bolt hits with its rank's base and the coefficient's share of the caster's spell power (a staff's), at a bolt's power",
      sp > 0 and seen and abs(seen[-1][0] - want) < 0.01 and abs(seen[-1][1] - honed) < 1e-9, (seen[-1:], want, sp))
combat.act_ability(fight, me, lance, dummy, random.Random(1))
check("...a lance at its form's power", abs(seen[-1][1] - spells.FORMS["lance"]["power"] * honed) < 1e-9, seen[-1:])
check("the cost is flat: the rank's mana times the form's, at any level", combat.cost_of(me, bolt, fight) == spells.mana(bolt)
      and combat.cost_of(me, lance, fight) == round(spells.RANKS[3]["mana"] * spells.FORMS["lance"]["mana"]))
me.level = 120
check("...and the same at level 120", combat.cost_of(me, bolt, fight) == spells.mana(bolt))
combat.apply_damage = _apply
charged = bolt.model_copy(update={"id": "c1", "spell_form": "charged", "cast_turns": 2})
check("a charged spell takes two turns and is cast as the engine's charged form", spellcraft.cast_turns(charged) == 2 and spellcraft.form_of(charged) == "charged")
blast = bolt.model_copy(update={"id": "x1", "spell_form": "blast"})
wolves = [combat.fighter_from_creature(world.bestiary["wolf"], 5, "normal", f"w{i}", f"Wolf {i}", start="near") for i in range(3)]
for w in wolves:
    w.zone_id = "z"
hit, share = spellcraft.targets(types.SimpleNamespace(battlefield=object()), me, blast, wolves[0], wolves)
check("a blast strikes every foe in the area at its full power each", len(hit) == 3 and share == 1.0, (len(hit), share))
hit, share = spellcraft.targets(types.SimpleNamespace(battlefield=object()), me, blast, wolves[0], wolves[:1])
check("...and on a lone foe it spreads thin", len(hit) == 1 and share == spells.FORMS["blast"]["lone"], share)

# ---- learning ranks
c2, _ = simlib.make_character("mage", random.Random(4))
line = next(iter(spells.lines(c2)))
check("rank II is out of reach at level 1", spells.learn(c2, line) is None and spells.learnable(c2) == [])
leveling.level_up(c2, 9)
count = spells.distinct(c2.actives)
was = spells.top(c2, line)
c2.prepared = [a.id for a in c2.actives][:5]
if was.id not in c2.prepared:
    c2.prepared = [was.id] + c2.prepared[:4]
new = spells.learn(c2, line, "Lava Lance", "A spear of molten rock.")
check("at level 10 rank II is learned: a new spell of the same line and form, a rank higher, under its own name",
      new is not None and new.rank == 2 and new.line == line and new.spell_form == was.spell_form and new.name == "Lava Lance", new)
check("...it takes the place of rank I among the spells brought; rank I stays in the book", new.id in c2.prepared and was.id not in c2.prepared
      and any(a.id == was.id for a in c2.actives))
check("...and it is not a new ability against the room for abilities", spells.distinct(c2.actives) == count)
check("a name the model leaves out is the old one with its numeral", spells.fallback_name(new, 3) == "Lava Lance III")
c3, _ = simlib.make_character("mage", random.Random(5))
leveling.level_up(c3, 49)
spells.catch_up(c3)
check("a character made at level 50 has every line at rank IV, what they would have learned on the way",
      all(spells.top(c3, l).rank == 4 for l in spells.lines(c3)), {l: spells.top(c3, l).rank for l in spells.lines(c3)})
f3 = combat.fighter_from_character(c3)
check("...and brings only the top rank of each", all(m.rank == 4 for m in f3.moves if m.rank), [(m.name, m.rank) for m in f3.moves if m.rank])

# ---- books and teachers, in the world
from npc.models import NPC
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from llm.contracts import ActionIntent
shutil.rmtree("saves/spells_test", ignore_errors=True)
store = CampaignStore.open_or_create("spells_test")
store.meta.seed = 4; store.meta.minutes = 720; store.save_meta()
pc, _ = simlib.make_character("mage", random.Random(6))
leveling.level_up(pc, 29)
spells.catch_up(pc)
for l in list(spells.lines(pc)):                       # back to rank II, to learn III
    pc.actives = [a for a in pc.actives if not (a.line == l and a.rank > 2)]
pc.prepared = []
pc.coins = 10 ** 6
store.save_player(PlayerState(character=pc, location="trading_square", guild_rank="E"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
c = ws.player.character
ws.to_pack(inv.make_good("tome_third_circle", 1))
lines_ = list(spells.lines(c))
NOTES.clear()
target = spells.top(c, lines_[0])
ws.on_use(ActionIntent(kind="use", item="tome of the third circle"), f"I study the tome for {spells.plain_name(target.name)}.")
check("reading a tome of the third circle teaches rank III of the spell the line names, and uses the book up",
      spells.top(c, lines_[0]).rank == 3 and not inv.find(ws.pack, "tome of the third circle"), (NOTES[-3:], spells.top(c, lines_[0]).rank))
ws.to_pack(inv.make_good("tome_third_circle", 1))
other = spells.top(c, lines_[1])
check("a line that names a spell book carried, with a reading verb, is read without the interpreter",
      ws.spell_book_turn(f"I pore over the tome for {spells.plain_name(other.name)}.") and spells.top(c, lines_[1]).rank == 3
      and not ws.spell_book_turn("I read the notice board."), spells.top(c, lines_[1]).rank)
ws.to_pack(inv.make_good("tome_fifth_circle", 1))
NOTES.clear()
ws.halted = False
ws.on_use(ActionIntent(kind="use", item="tome of the fifth circle"), "I read the tome.")
check("a tome above the character's level is refused, and kept", ws.halted and inv.find(ws.pack, "tome of the fifth circle")
      and any("beyond you until level 70" in n for n in NOTES), NOTES)
teacher = NPC(id="t1", name="Ilsa Morn", people="human", role="guild_instructor", location="trading_square")
ws.present = ws.present + [teacher]
NOTES.clear()
ws.on_train(ActionIntent(kind="train", item="the next rank of my spells"), "Can you teach me the next rank of my spells?")
check("a teacher with nothing the level allows says when the next rank comes within reach", not getattr(ws, "rank_options", None)
      and any("level 45" in n for n in NOTES), NOTES)
c.level = 45
NOTES.clear()
ws.on_train(ActionIntent(kind="train", item="the next rank of my spells"), "Can you teach me the next rank of my spells?")
check("a teacher offers the next rank of each spell the level allows, with the fee", getattr(ws, "rank_options", None)
      and any("to rank IV" in n for n in NOTES), NOTES)
coins = c.coins
ws.on_learn_ability(ActionIntent(kind="learn_ability", item="1"), "I'll learn the first one.")
check("...and teaches the one chosen, for the fee", c.coins < coins and sum(spells.top(c, l).rank == 4 for l in lines_) == 1,
      [(spells.top(c, l).name, spells.top(c, l).rank) for l in lines_])
NOTES.clear()
ws.ranks_in_reach(45)
check("a level-up that brings no new rank says nothing of ranks", not any("within your reach" in n for n in NOTES), NOTES)
ws.ranks_in_reach(44)
check("...reaching level 45 says rank IV is within reach", any("Rank IV" in n for n in NOTES), NOTES)
cx = spells.make_codex(40, random.Random(3), "cold")
ws.name_codex(cx, "the frost giant")
ws.to_pack(cx)
ws.halted = False
ws.on_use(ActionIntent(kind="use", item="codex"), "I open the codex and study it.")
known = next((a for a in c.actives if a.named), None)
check("a codex found and named is read in the world: its named spell is learned and the codex spent",
      known is not None and known.element == "cold" and not any(spells.is_codex(i) for i in ws.pack), [a.name for a in c.actives][-3:])
from scenes.combat_scene import CombatScene
c.spell_days = {known.id: ws.minutes - 60}
wolf = combat.fighter_from_creature(world.bestiary["wolf"], 45, "normal", "w1", "wolf", start="near")
cs = CombatScene.begin(ws, world.bestiary["wolf"], [wolf], "x")
check("a named spell cast within the day is not ready in the next fight", cs.fight.player.cooldowns.get(known.id, 0) > 1000,
      cs.fight.player.cooldowns)
ws.combat = None
ws.store.save_combat(None)
store.close()
shutil.rmtree("saves/spells_test", ignore_errors=True)

# ---- books from the fallen
r = random.Random(2)
drops = [spells.book_drop(30, "boss", r) for _ in range(200)]
got = [d for d in drops if d is not None]
check("a boss leaves a spell book of the rank its level allows about half the time", 70 < len(got) < 130 and all(d.good == "tome_third_circle" for d in got), len(got))
check("...an ordinary foe at level 5 leaves none (rank I is everyone's)", all(spells.book_drop(5, "boss", r) is None for _ in range(50)))

# ---- named spells: codices from bosses and the highest contracts
r = random.Random(7)
check("no codex is found below the named spells' level", all(spells.codex_drop(30, r) is None for _ in range(200)))
got = [spells.codex_drop(60, r, "fire") for _ in range(400)]
got = [g for g in got if g is not None]
check("a boss at level 60 leaves a codex now and then (about 15%)", 30 < len(got) < 95 and all(g.spell["element"] == "fire" and g.spell["rank"] == 4
      and g.spell["form"] in spells.N["forms"] for g in got), len(got))
check("an S contract pays one about half the time, an E contract never", 140 < sum(spells.contract_codex("S", 60, r) is not None for _ in range(400)) < 260
      and all(spells.contract_codex("E", 60, r) is None for _ in range(100)))
cx = got[0]
cx.spell.update(name="Starfall", description="The sky opens.")
c5, _ = simlib.make_character("mage", random.Random(8))
leveling.level_up(c5, 59)
spells.catch_up(c5)
check("a codex found at level 60 cannot be read at level 40", "beyond you until level 50" in spells.can_read(c5.model_copy(update={"level": 40}), cx))
before = spells.distinct(c5.actives)
named = spells.learn_named(c5, cx)
check("reading it gives a named spell: its form, its rank, stronger and costlier than a ranked one, a day between casts",
      named.named and named.rank == 4 and named.cooldown_days == 1 and spells.power(named) == spells.FORMS[named.spell_form]["power"] * spells.N["power"]
      and spells.mana(named) == round(spells.RANKS[4]["mana"] * spells.FORMS[named.spell_form]["mana"] * spells.N["mana"]), named)
check("...it never ranks up, and does not take an ability's room", named.line not in spells.lines(c5) and spells.distinct(c5.actives) == before)
from ui import console as real_console
check("...and its card says so", "named" in spells.card(named).lower() and "once a fight" in " · ".join(real_console._ability_facts(named, 60)))
f5 = combat.fighter_from_character(c5)
nm = next((m for m in f5.moves if m.named), None)
check("a named spell is brought when there is room", nm is not None, [m.name for m in f5.moves])
dummy5 = combat.fighter_from_creature(world.bestiary["bandit"], 60, "normal", "d", "dummy", start="near")
dummy5.max_hp = dummy5.hp = 10 ** 7
fight5 = combat.Combat(fighters=[f5, dummy5], place="x", conditions=[])
combat.ensure_field(fight5)
f5.mana = f5.max_mana = 10 ** 4
combat.act_ability(fight5, f5, nm, dummy5, random.Random(1))
check("once cast, it is spent for the fight, and the cast is kept for the day", combat.can_use(f5, nm, fight5) is not None
      and nm.id in f5.counters.get("day_cast", []))
c5.spell_days = {nm.id: 1000}
check("...and is not ready again until a day has passed", spells.day_locked(c5, named, 1000 + 60) > 0 and spells.day_locked(c5, named, 1000 + 1440) == 0)

# ---- the card
from ui import console as real_console
c4, _ = simlib.make_character("mage", random.Random(3))
a = next(a for a in c4.actives if spells.is_ranked(a))
facts = " · ".join(real_console._ability_facts(a, 50))
check("an ability's card says its rank and its flat mana, at any level", f"{spells.mana(a)} mana" in facts and "rank I" in facts, facts)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
