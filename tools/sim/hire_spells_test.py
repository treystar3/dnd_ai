"""(f400) Buffs without tiers, and hires who cast on the spellbook: a buff costs a flat sum by the rank the caster's level allows and
shows no tier anywhere; a hired mage or priest casts the player's spells at the highest rank their level allows (a name for each rank),
pays the flat cost from a pool like a player's, keeps what is left between fights and gets it back with time, and fights with what is in
their hands when it runs out. A hire who does not cast is as before."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("mage", 3)
simlib.install(stub)
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
for f_ in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f_, lambda *a, **k: None)
from engine import ability_traits as AT, combat, healing, loadout, party, pools, spells, techniques
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
check("the data checks clean", spells.problems() == [] and techniques.problems() == [], spells.problems() + techniques.problems())

# ---------- buffs: no tier
ch, _ = simlib.make_character("mage", random.Random(2))
ch.level = 30
buffs = [a for a in ch.actives if a.effect.value == "buff"]
if not buffs:
    from core.models import Ability
    b0 = next(a for a in ch.actives)
    buffs = [b0.model_copy(update={"id": "test_buff", "name": "Test Ward", "effect": type(b0.effect)("buff"), "buff": "arcaneward",
                                   "resource": type(b0.resource)("mana"), "reach": type(b0.reach)("self"), "rank": 0, "line": ""})]
    ch.actives.append(buffs[0])
b = buffs[0]
me = combat.fighter_from_character(ch)
mv = next((m for m in me.moves if m.id == b.id), None) or combat.Move(id=b.id, name=b.name, effect="buff", tier="moderate", reach="self",
                                                                        resource="mana", buff=b.buff)
costs = set()
for t in ("light", "moderate", "heavy"):
    mv.tier = t
    costs.add(combat.cost_of(me, mv))
check("a buff costs the same whatever tier it carries: it has none", len(costs) == 1, costs)
check("...a flat sum by the rank the caster's level allows", costs == {spells.buff_mana(30)} and spells.buff_mana(30) == spells.S["buffs"]["mana"][2],
      (costs, spells.buff_mana(30)))
check("...more at a higher rank, the same within one", spells.buff_mana(1) < spells.buff_mana(10) < spells.buff_mana(130)
      and spells.buff_mana(25) == spells.buff_mana(44), [spells.buff_mana(x) for x in (1, 10, 25, 44, 130)])
check("...and not a share of a pool any more", "buff_cost" not in AT.T)
facts = uc._ability_facts(b, 30)
check("its card shows that cost", f"{spells.buff_mana(30)} mana" in " · ".join(facts), facts)
rows = [l for l in loadout.lines(ch, 0, False) if b.name in l]
check("the book's list shows no tier for a buff", rows and all(w not in l for l in rows for w in ("light", "moderate", "heavy")), rows)
check("a buff's grade is nothing; a spell's is its rank and form; a technique's its tier",
      spells.grade(b) == "" and all(spells.grade(a).startswith("Rank ") for a in ch.actives if a.rank and not a.named))
check("Imbue's element lands at one strength, whoever casts it", AT.imbue_strength() in ("light", "moderate", "heavy"))
f = combat.Combat(fighters=[me, combat.fighter_from_creature(world.bestiary["wolf"], 30, "normal", "w", "Wolf", "engaged")], place="x", conditions=[])
mv.tier = "heavy"
me.mana = 10 ** 6
seen = {}
orig = combat._act_ability
def spy(c_, att, m_, *a, **k):
    seen["tier_now"] = att.counters.get("tier_now")
    return orig(c_, att, m_, *a, **k)
combat._act_ability = spy
combat.act_ability(f, me, mv, None, random.Random(1))
combat._act_ability = orig
check("a buff counts as no tier where perks look for one", seen.get("tier_now") == 0, seen)

# ---------- hires who cast
for L in (1, 10, 25, 50, 100, 130):
    m = party.fighter({"id": "m", "name": "Ilsa Vane", "role": "mage", "level": L})
    r = spells.highest_rank(L)
    ok = all(x.rank == r for x in m.moves) and {x.spell_form for x in m.moves} == {"blast", "lance", "bolt"}
    check(f"a level {L} mage casts rank {spells.numeral(r)}, a name for the rank", ok and m.moves[-1].name == techniques.kit("mage")[-1]["names"][r - 1],
          [(x.name, x.rank) for x in m.moves])
    check(f"...with a pool like a player's of their level and intelligence ({m.max_mana})", m.max_mana == pools.mana_of(L, m.attrs, "intelligence")
          and m.mana == m.max_mana)
p = party.fighter({"id": "p", "name": "Aldo Venn", "role": "priest", "level": 50})
check("a priest casts the player's heal at their rank, with wisdom", p.moves and p.moves[0].effect == "healing" and p.moves[0].rank == 4
      and p.moves[0].attribute == "wisdom" and p.max_mana == pools.mana_of(50, p.attrs, "wisdom"), p.moves)
fi = party.fighter({"id": "f", "name": "Bryn Tor", "role": "fighter", "level": 50})
check("a fighter does not cast: no mana, no spells, techniques as before", fi.max_mana == 0 and not fi.moves and techniques.casts("fighter") == "")
check("the hall and party panes say a caster's rank", "rank IV" in techniques.describe("mage", 50) and "Riven Lance" in techniques.describe("mage", 50)
      and "rank I " in techniques.describe("priest", 1), techniques.describe("mage", 50))

from engine import statsheet
rows = {r[0]: r for sec in statsheet.sheet(party.fighter({"id": "m", "name": "Ilsa Vane", "role": "mage", "level": 30}))["sections"]
        for r in sec.get("rows", [])}
check("a mage's sheet shows a rank III bolt at a hire's share", "rank III bolt" in rows.get("Spell damage", ["", "", ""])[2]
      and "70% for a hire" in rows["Spell damage"][2], rows.get("Spell damage"))


def fight(roles, level=30, foes=1, minutes=None, members=None):
    pl = combat.fighter_from_character(ch)
    ms = members or [{"id": f"t{i}", "name": f"Hire{i} Voss", "role": r, "level": level} for i, r in enumerate(roles)]
    allies = [party.fighter(x, minutes=minutes) for x in ms]
    en = [combat.fighter_from_creature(world.bestiary["wolf"], level, "normal", f"foe{i}", f"Wolf {i}", "engaged") for i in range(foes)]
    for e in en:
        e.hp = e.max_hp = 10 ** 6
    c = combat.Combat(fighters=[pl] + allies + en, place="x", conditions=[], record=True)
    c.round = 2
    return c, allies, en


# a cast costs the spell's flat mana, and the form's cooldown
c, (mage,), (wolf,) = fight(["mage"])
before = mage.mana
combat.ally_turn(c, mage, random.Random(1))
lance = techniques.spell(mage, techniques.kit("mage")[1])
check("a mage on a lone foe casts the lance first, paying its flat cost", before - mage.mana == spells.mana(lance)
      and any(f"uses {lance.name} on Wolf" in l for l in c.log), (before - mage.mana, spells.mana(lance), c.log[-3:]))
check("...and it rests as the form says", mage.cooldowns.get(lance.id) == spells.cooldown("lance") + 1, mage.cooldowns)
c.round = 3
m1 = mage.mana
combat.ally_turn(c, mage, random.Random(2))
bolt = techniques.spell(mage, techniques.kit("mage")[2])
check("...then bolts while the lance rests", m1 - mage.mana == spells.mana(bolt) and any(bolt.name in l for l in c.log[-3:]), c.log[-3:])
# share: a hire's spell against the same spell cast at the full share
hit_hire, hit_full = [], []
for i in range(300):
    for share, out in ((None, hit_hire), (1.0, hit_full)):
        c, (mg,), (w,) = fight(["mage"])
        if share:
            mg.spell_share = share
        combat.act_ability(c, mg, techniques.spell(mg, techniques.kit("mage")[2]), w, random.Random(i))
        out.append(w.max_hp - w.hp)
ratio = sum(hit_hire) / max(1, sum(hit_full))
check(f"a hire's spell hits at the share party.yaml casting gives ({ratio:.2f})", abs(ratio - party.P["casting"]["power"]) < 0.06, ratio)
# out of mana: what is in their hands
c, (mage,), (wolf,) = fight(["mage"])
mage.mana = 0
combat.ally_turn(c, mage, random.Random(3))
check("out of mana, a mage fights with the staff", any(l.startswith(f"{mage.name} attacks Wolf") for l in c.log[-3:])
      and not any(x.name in l for x in mage.moves for l in c.log[-3:]), c.log[-3:])
# three bunched: the blast
c, (mage,), wolves = fight(["mage"], foes=3)
combat.ally_turn(c, mage, random.Random(4))
blast = techniques.spell(mage, techniques.kit("mage")[0])
check("three foes bunched together: the blast, on every one", all(any(f"uses {blast.name} on {w.name}" in l for l in c.log) for w in wolves), c.log[-4:])

# the priest: heals and blessings from the same pool
c, (pr,), (wolf,) = fight(["priest"])
c.round = 1
m0 = pr.mana
combat.ally_turn(c, pr, random.Random(5))
check("a blessing is a buff: it costs a buff's mana", m0 - pr.mana == spells.buff_mana(30) and c.player.counters.get("blessed"), (m0 - pr.mana,))
c.round = 2
c.player.hp = c.player.max_hp * 0.5
m1 = pr.mana
combat.ally_turn(c, pr, random.Random(6))
heal = techniques.spell(pr, techniques.healing("priest"))
check("a heal costs the heal's flat mana", m1 - pr.mana == spells.mana(heal) and c.player.hp > c.player.max_hp * 0.5, (m1 - pr.mana, spells.mana(heal)))
c, (pr,), (wolf,) = fight(["priest"])
c.round = 1
pr.mana = 0
combat.ally_turn(c, pr, random.Random(7))
check("no mana: no blessing", not c.player.counters.get("blessed"))
c.round = 2
c.player.hp = c.player.max_hp * 0.5
combat.ally_turn(c, pr, random.Random(8))
check("...and no heal: the priest fights", c.player.hp == c.player.max_hp * 0.5 and any(l.startswith(f"{pr.name} attacks Wolf") for l in c.log[-3:]),
      c.log[-3:])

# a fight saved before spells had ranks: its priest has no spells and no mana on record
c, (pr,), (wolf,) = fight(["priest"])
pr.moves, pr.mana, pr.max_mana, pr.spell_share = [], 0, 0, 1.0
c.player.hp = c.player.max_hp * 0.5
combat.ally_turn(c, pr, random.Random(9))
check("a priest from a fight saved before ranks gets their spells, and heals", pr.moves and pr.max_mana > 0 and c.player.hp > c.player.max_hp * 0.5,
      (pr.moves, pr.max_mana, c.log[-2:]))

# mana between fights
mem = {"id": "h1", "name": "Ilsa Vane", "role": "mage", "level": 30, "permanent": True, "mana_frac": 0.2, "mana_at": 1000}
m = party.fighter(mem, minutes=1000)
check("a hire who spent their mana starts the next fight with what is left", abs(m.mana - m.max_mana * 0.2) < 1, (m.mana, m.max_mana))
m = party.fighter(mem, minutes=1000 + 120)
want = 0.2 + 2 * pools.RULES.regen_per_hour["mana"]
check("...and gets it back with time, as a player does", abs(m.mana - m.max_mana * want) < 1, (m.mana / m.max_mana, want))
check("...all of it, given long enough", party.mana_now(mem, 1000 + 60 * 24) == 1.0)

# the scene keeps it
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
shutil.rmtree("saves/hire_spells_test", ignore_errors=True)
store = CampaignStore.open_or_create("hire_spells_test")
store.meta.seed = 4; store.meta.minutes = 720; store.save_meta()
char, _ = simlib.make_character("mage", random.Random(3))
char.level = 30
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
mage_m = {"id": "h1", "name": "Ilsa Vane", "role": "mage", "level": 30, "permanent": True, "rank": "D", "bond": 10}
priest_m = {"id": "h2", "name": "Aldo Venn", "role": "priest", "level": 30, "permanent": True, "rank": "D", "bond": 10}
ws.player.party = [mage_m, priest_m]
ws.player.party_mode = "with"
fm = party.fighter(mage_m, "ally_h1", ws.minutes)
fm.mana = fm.max_mana * 0.25
fp = party.fighter(priest_m, "ally_h2", ws.minutes)
ws.party_after_fight([], [fm, fp], True, False)
check("after a fight the scene keeps what mana a hire has left", abs(mage_m.get("mana_frac", 1) - 0.25) < 0.01 and mage_m.get("mana_at") == ws.minutes
      and priest_m.get("mana_frac") == 1.0, (mage_m.get("mana_frac"), priest_m.get("mana_frac")))
check("...and the fields are ones a hire is known to keep", not party.unclassified(mage_m), party.unclassified(mage_m))
# tending by rank
check("a priest's care out of a fight is their heal at their rank: rank I as before ranks",
      round(techniques.tend_pct({"level": 1}, "after_fight")) == 25 and round(techniques.tend_pct({"level": 1}, "asked")) == 36)
check("...more from a priest of a higher rank", techniques.tend_pct({"level": 100}, "asked") > techniques.tend_pct({"level": 30}, "asked")
      > techniques.tend_pct({"level": 1}, "asked"))
store.close()
shutil.rmtree("saves/hire_spells_test", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
