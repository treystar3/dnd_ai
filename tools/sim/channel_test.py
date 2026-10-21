"""Channeled abilities: a mana strike through the wielded weapon."""
import random, sys, statistics
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import combat as C
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

def F(id, side, **k):
    d = dict(id=id, name=id, side=side, level=20, attrs={a: 14 for a in C.ATTRIBUTES}, hp=10 ** 7, max_hp=10 ** 7, weapon_damage=40, weapon_name="sword",
             reach="melee", damage_type="physical", weapon_attrs=["strength"], armor=0, ward=0, stamina=500, max_stamina=500, mana=500, max_mana=500)
    d.update(k); return F_(d)
def F_(d): return C.Fighter(**d)
def mv(channel, **k):
    d = dict(id="m", name="Smite", effect="damage", tier="moderate", reach="melee", resource="mana", attribute="wisdom", channel=channel)
    d.update(k); return C.Move(**d)

def avg(p_kw, move, e_kw, n=300):
    out = []
    for i in range(n):
        p = F("p", "player", **p_kw); e = F("e", "enemy", band="engaged", **e_kw)
        p.moves = [move]
        cmb = C.Combat(fighters=[p, e]); h = e.hp
        C.act_ability(cmb, p, move, e, random.Random(i))
        out.append(h - e.hp)
    return statistics.mean(out)

plain, chan = mv(False), mv(True)
a_plain = avg({}, plain, {})
a_chan = avg({}, chan, {})
check("a channeled strike with a sword out-damages the same spell cast plain", a_chan > a_plain * 2, (round(a_plain), round(a_chan)))
pp = F("p", "player")
check("it costs half a spell's mana (f260)", abs(C.cost_of(pp, chan) - C.cost_of(pp, plain) * 0.5) <= 1, (C.cost_of(pp, plain), C.cost_of(pp, chan)))
tech = C.Move(id="t", name="T", effect="damage", tier=chan.tier, reach="melee", resource="stamina")
check("...plus a technique's full stamina", C.stamina_part(pp, chan) == C.cost_of(pp, tech) and C.stamina_part(pp, plain) == 0, (C.stamina_part(pp, chan), C.cost_of(pp, tech)))
tired = F("p", "player"); tired.stamina = 0
check("with no stamina it cannot be used", "stamina" in (C.can_use(tired, chan) or ""), C.can_use(tired, chan))
fresh = F("p", "player"); s0, m0 = fresh.stamina, fresh.mana
foe = F("e", "enemy", band="engaged"); C.act_ability(C.Combat(fighters=[fresh, foe]), fresh, chan, foe, random.Random(1))
check("using it spends both", fresh.stamina < s0 and fresh.mana < m0, (s0, fresh.stamina, m0, fresh.mana))
check("with a ranged weapon it cannot be used at all (f250)", C.can_use(F("p", "player", reach="ranged"), chan) and avg({"reach": "ranged"}, chan, {}) == 0)
check("nor with a magical focus (f250)", C.can_use(F("p", "player", damage_type="magical", weapon_damage=40), chan) and avg({"damage_type": "magical", "weapon_damage": 40}, chan, {}) == 0)
check("with a melee weapon in hand it can", C.can_use(F("p", "player"), chan) is None)
armored = avg({}, chan, {"armor": 200, "ward": 0})
warded = avg({}, chan, {"armor": 0, "ward": 200})
both = avg({}, chan, {"armor": 200, "ward": 200})
open_ = avg({}, chan, {})
check("it gets through the weaker of armor or ward", armored > both * 1.5 and warded > both * 1.5 and armored > open_ * 0.3, (round(armored), round(warded), round(both)))
cost_pl = avg({}, plain, {"armor": 200, "ward": 0})
check("a plain spell is stopped by ward only (armor does nothing to it)", abs(cost_pl - a_plain) < a_plain * 0.2, (round(cost_pl), round(a_plain)))
p = F("p", "player"); e = F("e", "enemy", band="engaged"); p.moves = [chan]
C.act_ability(C.Combat(fighters=[p, e]), p, chan, e, random.Random(1))
check("the weapon's damage and flags are put back after the strike", p.weapon_damage == 40 and p.damage_type == "physical" and not p.adaptive, (p.weapon_damage, p.damage_type, p.adaptive))
def trace(move, **kw):
    p = F("p", "player", **kw); e = F("e", "enemy", band="engaged"); p.moves = [move]
    cmb = C.Combat(fighters=[p, e]); cmb.record = True
    for i in range(40):
        C.act_ability(cmb, p, move, e, random.Random(i))
    return next(h["base"] for h in cmb.hits if h.get("base"))
t_spell = trace(plain, damage_type="magical", weapon_damage=3)
check("a spell's breakdown names the spell base and the focus", t_spell.get("kind") == "spell" and [n for n, v in t_spell["parts"]] == ["spell base", "spell power"], t_spell)
check("a plain spell with no focus lists only its base", [n for n, v in trace(plain, weapon_damage=0, damage_type="magical")["parts"]] == ["spell base"])
t_chan = trace(chan)
check("a channeled strike names the weapon and the spell part", t_chan.get("kind") == "channel" and [n for n, v in t_chan["parts"]] == ["weapon", "spell"], t_chan)
check("an ordinary weapon blow has no spell parts", "kind" not in (lambda p, e: (C.act_attack(C.Combat(fighters=[p, e], record=True), p, e, random.Random(1)), {})[1])(F("p", "player"), F("e", "enemy", band="engaged")))
for lv in (1, 10, 20):
    g = C.growth(lv)
    print(f"   level {lv}: sword 40 -> plain spell base {6 * g:.1f}, channeled {40 + 3 * g:.1f}")
def outcomes(att_kw, dfn_kw, n=4000):
    cnt = {"miss": 0, "graze": 0, "hit": 0, "crit": 0}; lows = []; hi = []
    for i in range(n):
        p = F("p", "player", **att_kw); e = F("e", "enemy", band="engaged", **dfn_kw)
        info = {}
        out, chance = C.roll_attack(p, e, C.Combat(fighters=[p, e]), random.Random(i), trace=info)
        cnt[out] += 1
        if out == "crit": lows.append(info["roll"])
        if out == "miss": hi.append(info["roll"])
    return cnt, lows, hi, info
cnt, crit_rolls, miss_rolls, info = outcomes({}, {})
check("high rolls are good: a crit needs a roll in the top of the range", crit_rolls and min(crit_rolls) >= info["crit_need"] - 0.1, (min(crit_rolls), info["crit_need"]))
check("a miss is a low roll, below the number needed", miss_rolls and max(miss_rolls) < info["need"] + 0.1, (max(miss_rolls), info["need"]))
check("about 5% of attacks crit at equal Dexterity", 0.03 < cnt["crit"] / 4000 < 0.07, cnt)
print("\nFAILED:" if bad else "\nALL PASS", bad or "")
sys.exit(1 if bad else 0)
