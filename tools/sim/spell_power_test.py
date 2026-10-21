"""Spell power: a flat stat from foci (main hand, off hand) and, lower, from gear; the multiplier is the casting attribute."""
import random, sys, statistics
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import combat as C, items, loot, equipment
from core.models import Item, ItemProperty
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

def F(id, side, **k):
    d = dict(id=id, name=id, side=side, level=20, attrs={a: 14 for a in C.ATTRIBUTES}, hp=10 ** 7, max_hp=10 ** 7, weapon_damage=0, weapon_name="wand",
             reach="ranged", damage_type="magical", weapon_attrs=["intelligence"], armor=0, ward=0, stamina=500, max_stamina=500, mana=500, max_mana=500)
    d.update(k); return C.Fighter(**d)
def mv(channel=False, **k):
    d = dict(id="m", name="Bolt", effect="damage", tier="moderate", reach="ranged", resource="mana", attribute="intelligence", channel=channel)
    d.update(k); return C.Move(**d)
def trace(move, **kw):
    p = F("p", "player", **kw); e = F("e", "enemy", band="engaged"); p.moves = [move]
    cmb = C.Combat(fighters=[p, e]); cmb.record = True
    for i in range(40):
        C.act_ability(cmb, p, move, e, random.Random(i))
    return next(h["base"] for h in cmb.hits if h.get("base"))

check("magic_power is gone", "magic_power" not in C.Fighter.model_fields and "magic_power" not in items.FLAGS)
check("no material carries a magic_power flag", all("magic_power" not in {**m.weapon_flags, **m.armor_flags} for m in items.MATERIALS.values()))
sp = [m for m in items.MATERIALS.values() if any(e.modifies == "spell_power" for e in m.any + m.weapon + m.armor)]
check("the three old magic power materials now give spell power", {m.id for m in sp} == {"ember_silk", "treant_heartwood", "glowcap_timber"}, [m.id for m in sp])

g = C.growth(20)
t = trace(mv(), weapon_damage=7, attrs={**{a: 14 for a in C.ATTRIBUTES}, "intelligence": 40})
check("a spell reads spell base + spell power", [n for n, v in t["parts"]] == ["spell base", "spell power"] and abs(t["parts"][0][1] - 6 * g) < 0.2 and t["parts"][1][1] == 7, t)
check("no flat attribute bonus on a spell; the attribute is the multiplier 1 + attr/50", t["attr_bonus"] == 0 and abs(t["magic"] - 1.8) < 0.001, t)
check("the base is spell base + spell power", abs(t["base"] - (6 * g + 7)) < 0.2, t)
check("total = base x variance x multiplier x tier", abs(t["total"] - t["base"] * t["variance"] * 1.8 * t["multiplier"] * (1 + t["pct"] / 100)) < 0.3, t)

parts = dict(trace(mv(), offhand_spell=5, weapon_damage=7)["parts"])
check("an off-hand focus adds to spell power with the main-hand focus", parts["spell power"] == 12, parts)

gear = F("p", "player", weapon_damage=0, bonuses=[C.Bonus(modifies="spell_power", trigger="always", magnitude=4, flat=True)])
tg = trace(mv(), weapon_damage=0, bonuses=[C.Bonus(modifies="spell_power", trigger="always", magnitude=4, flat=True)])
check("gear spell power helps a spell with no focus in hand", [n for n, v in tg["parts"]] == ["spell base", "spell power"] and tg["parts"][1][1] == 4, tg)
td = trace(mv(), weapon_damage=0, bonuses=[C.Bonus(modifies="damage", trigger="always", magnitude=9, flat=True)])
check("flat gear damage stays out of a plain spell", td["flat"] == 0, td)

def ch(**kw):
    p = F("p", "player", reach="melee", damage_type="physical", weapon_attrs=["strength"], weapon_damage=40, **kw)
    e = F("e", "enemy", band="engaged"); m = mv(True, reach="melee"); p.moves = [m]
    cmb = C.Combat(fighters=[p, e], record=True)
    for i in range(40): C.act_ability(cmb, p, m, e, random.Random(i))
    return next(h["base"] for h in cmb.hits if h.get("base"))
lo = ch(); hi = ch(attrs={**{a: 14 for a in C.ATTRIBUTES}, "intelligence": 64}, offhand_spell=10)
sp_lo, sp_hi = dict(lo["parts"])["spell"], dict(hi["parts"])["spell"]
check("a channeled strike's spell half takes the multiplier and the half share of spell power", abs(sp_lo - 0.5 * 6 * g * (1 + 14 / 50)) < 0.2 and abs(sp_hi - 0.5 * (6 * g + 10) * (1 + 64 / 50)) < 0.2, (sp_lo, sp_hi))
check("the weapon half is untouched by the spell attribute", dict(lo["parts"])["weapon"] == 40 == dict(hi["parts"])["weapon"])

for b in ("scrying_orb", "spell_tome", "prayer_censer", "tuning_fork", "oracle_orb", "grand_grimoire", "reliquary", "resonant_bell"):
    bi = items.CATALOG[b]
    check(f"{b} is an off-hand focus", bi.is_offhand_focus and not bi.is_weapon and bi.slot == "off_hand")
rng = random.Random(7)
seen = set()
for i in range(400):
    it = items.make("scrying_orb", rng.choice(["uncommon", "rare", "epic", "legendary"]), 30, rng=rng); loot.roll_gear(it, rng)
    seen |= {p.modifies for p in it.properties}
allowed = set(loot.gear_stats(items.make("scrying_orb", "rare", 30)))
check("an orb rolls from its own pool (spell power, mana, casting attribute...) and never accuracy or on-hit", "spell_power" in seen and "intelligence" in seen and not (seen & {"accuracy", "vampiric", "damage", "wisdom"}) and {x for x in seen if x.split("_")[0] not in ("fire","cold","lightning","poison","acid","necrotic","radiant","nature")} <= allowed, sorted(seen))
check("a censer casts with wisdom", "wisdom" in loot.gear_stats(items.make("prayer_censer", "rare", 30)) and "intelligence" not in loot.gear_stats(items.make("prayer_censer", "rare", 30)))
def mean_sp(base, n=600):
    r = random.Random(11); out = []
    for i in range(n):
        it = items.make(base, "epic", 30, rng=r); loot.roll_gear(it, r)
        out += [p.magnitude for p in it.properties if p.modifies == "spell_power"]
    return (statistics.mean(out) if out else 0), len(out)
m_orb, n_orb = mean_sp("scrying_orb"); m_robe, n_robe = mean_sp("robe") if "robe" in items.CATALOG else (0, 0)
m_wand, n_wand = mean_sp("wand")
check("a wand and an orb roll spell power", n_orb > 50 and n_wand > 50, (n_orb, n_wand))
cloth = [b for b in items.CATALOG.values() if b.ward and b.slot == "body"]
if cloth:
    m_cl, n_cl = mean_sp(cloth[0].id)
    check("cloth can roll spell power, at about half the strength of a focus", n_cl > 20 and m_cl < m_orb * 0.75, (n_cl, m_cl, m_orb))
heavy = [b for b in items.CATALOG.values() if b.weight == "heavy" and not b.ward and b.slot == "body"][0]
check("heavy armor never rolls spell power", mean_sp(heavy.id, 200)[1] == 0)
check("a shield never rolls spell power", mean_sp("wooden_shield", 200)[1] == 0)

c = simlib.make_character("mage", random.Random(3))[0]
c.level = 80
c.attributes.intelligence = 99; c.attributes.wisdom = 99
c.equipment.pop("off_hand", None)
def eq(base):
    it = items.make(base, "rare", 30); c.inventory.append(it); return equipment.equip(c, it)
eq("wand"); msg = eq("scrying_orb")
check("a wand and an orb are held together", c.equipment["main_hand"].base == "wand" and c.equipment["off_hand"].base == "scrying_orb", msg)
fi = C.fighter_from_character(c)
check("the orb's value is the fighter's off-hand spell power, not armor", fi.offhand_spell == items.value(c.equipment["off_hand"]) > 0 and fi.armor == C.fighter_from_character(c).armor)
eq("arcane_staff")
check("a two-handed staff puts the orb away", "off_hand" not in c.equipment)
msg = eq("scrying_orb")
check("an orb will not go on with a staff in hand", "hands are full" in msg.lower() and "off_hand" not in c.equipment, msg)
sh = items.make("wooden_shield", "rare", 30); c.inventory.append(sh); eq("wand"); equipment.equip(c, sh)
check("a shield and an orb compete for the off hand", c.equipment["off_hand"].base == "wooden_shield")
check("the summary reads as spell power", "spell power" in items.summary(items.make("scrying_orb", "rare", 30)))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS []")
sys.exit(1 if bad else 0)
