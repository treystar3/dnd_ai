"""The creation perks in a fight (f209): every rule a player can be born with, run through its loop twice - the leap that resets on a
kill, the rot that walks on, the weave and the echo, fire that stacks and goes off, the stance that charges a heavy, blood for mana,
the summoner's bond and its unmaking, the cues and drums of a party. Numbers from data/rules/perks.yaml; hooks in engine/combat.py."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import battlefield as bf, battlefield_builder as bb, combat, combat_perks as perks
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

P = perks.P


def player(*mechs, moves=(), hp=400, stam=200, mana=200, attrs=14, dmg=10, **kw):
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs={a: attrs for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, stamina=stam, max_stamina=stam, mana=mana, max_mana=mana, weapon_damage=dmg, hold=1,
                          legendary={m: v for m, v in (x if isinstance(x, tuple) else (x, 1) for x in mechs)},
                          mech_names={(x[0] if isinstance(x, tuple) else x): (x[0] if isinstance(x, tuple) else x).replace("_", " ").title() for x in mechs},
                          moves=list(moves), **kw)

def foe(i, hp=10**6, category="hostile people", level=5, dmg=8, **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=level, attrs={a: 10 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, weapon_damage=dmg, category=category, behaviors={"fearless": 1}, **kw)

def spirit(hp=100, dmg=8, form="bound", of=""):
    """A summon standing for the player (the Bound one, unless a form is named) - since f222 summons are made, never companions."""
    f = combat.Fighter(id="ally_spirit", name="the spirit", side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                       hp=hp, max_hp=hp, weapon_damage=dmg, hold=1)
    f.summon_form, f.summon_owner, f.summon_of, f.summon_tier = form, "player", of, "light"
    return f

def beast(hp=100):
    """A companion: a tamed, living creature."""
    return combat.Fighter(id="ally_wolf", name="the wolf", side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, weapon_damage=8, hold=1)

def hire(hp=200):
    return combat.Fighter(id="ally_h", name="Tam", side="ally", level=5, attrs={a: 12 for a in combat.ATTRIBUTES},
                          hp=hp, max_hp=hp, weapon_damage=8, ally_role="fighter", hold=1)

def fight(*fs, conditions=(), record=True):
    f = combat.Combat(fighters=list(fs), conditions=list(conditions), record=record)
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    return f

def spell(mid, element="", tier="light", effect="damage", cooldown=0, attribute="intelligence", **kw):
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=effect, tier=tier, reach="ranged", resource="mana",
                attribute=attribute, element=element, cooldown=cooldown, **kw)

def skill(mid, tier="light", effect="damage", cooldown=0, **kw):
    return Move(id=mid, name=mid.replace("_", " ").title(), effect=effect, tier=tier, reach="melee", resource="stamina",
                cooldown=cooldown, **kw)

def engaged(f, a, b):
    bf.engage(f, a, b)

def last_hit(f, att=None):
    hs = [h for h in f.hits if h["outcome"] not in ("heal",) and (att is None or h["att"] == att)]
    return hs[-1] if hs else None

rng = random.Random(11)

# ---- Deathleap: a kill resets the last movement ability and returns its cost, twice (f223: Bloodscent as the movement)
leap = skill("leap", effect="mobility", cooldown=6, movement="bloodscent")
p = player("deathleap", moves=[leap], dmg=1)
f = fight(p, foe(1), foe(2), foe(3))
for n, e in ((1, f.get("e1")), (2, f.get("e2"))):
    f.round = n
    e.hp = e.max_hp * 0.3                                    # Bloodscent only follows the badly hurt
    before = p.stamina
    combat.act_ability(f, p, leap, e, rng)
    spent = before - p.stamina
    check(f"deathleap {n}: the leap is used and on cooldown", p.cooldowns.get("leap", 0) > 0 and spent > 0, (p.cooldowns, spent))
    e.hp, p.weapon_damage = 1, 10**5
    while e.alive:
        combat.act_attack(f, p, e, rng)
    p.weapon_damage = 1
    check(f"deathleap {n}: the kill resets it and pays it back", not e.alive and "leap" not in p.cooldowns and p.stamina >= before - 1, (e.alive, p.cooldowns, p.stamina, before))

# ---- Plaguebearer: afflictions walk from the dead to the nearest living, twice
p = player("plaguebearer", dmg=10**5)
f = fight(p, foe(1, hp=20), foe(2, hp=20), foe(3))
f.get("e1").statuses = {"poisoned": 3, "bleeding": 2}
while f.get("e1").alive:
    combat.act_attack(f, p, f.get("e1"), rng)
nxt = next(e for e in f.enemies() if e.statuses.get("poisoned") == 3 and e.statuses.get("bleeding") == 2)
check("plaguebearer 1: the rot walks on, rounds intact", nxt is not None and not f.get("e1").alive)
nxt.statuses["burning"] = 4
while nxt.alive:
    combat.act_attack(f, p, nxt, rng)
rest = f.enemies()[0]
check("plaguebearer 2: ...and again, carrying the whole load", not nxt.alive and rest.statuses.get("burning") == 4 and rest.statuses.get("poisoned", 0) >= 1, rest.statuses)

# ---- Threefold Weave: three kinds in a row, the third crits - twice over
fire, cold, bolt = spell("firebolt", "fire"), spell("frostlance", "cold"), spell("thunderspear", "lightning")
p = player("threefold_weave", moves=[fire, cold, bolt], mana=10**6)
f = fight(p, foe(1))
e = f.get("e1")
for n in (1, 2):
    outs = []
    for m in (fire, cold, bolt):
        combat.act_ability(f, p, m, e, rng)
        outs.append(last_hit(f)["outcome"])
    check(f"threefold weave {n}: the third kind of magic in a row is critical", outs[2] == "crit", outs)

# ---- Spell Echo: the same spell three times, and the third happens twice - twice over
p = player("spell_echo", moves=[fire], mana=10**6)
f = fight(p, foe(1))
e = f.get("e1")
for n in (1, 2):
    for _ in range(2):
        combat.act_ability(f, p, fire, e, rng)
    before = len(f.hits)
    combat.act_ability(f, p, fire, e, rng)
    check(f"spell echo {n}: the third cast resolves twice", len(f.hits) - before == 2, len(f.hits) - before)

# ---- Grave Chorus: a kill leaves an echo; the next working is repeated by it; echo kills leave none
p = player("grave_chorus", moves=[fire], mana=10**6, dmg=10**5)
f = fight(p, foe(1, hp=10), foe(2), foe(3, hp=10))
combat.act_attack(f, p, f.get("e1"), rng)
check("grave chorus 1: the kill leaves an echo standing", p.counters.get("echoes") == 1, p.counters)
before = len(f.hits)
combat.act_ability(f, p, fire, f.get("e2"), rng)
check("grave chorus 1: ...which repeats the next working once", len(f.hits) - before == 2 and not p.counters.get("echoes"), (len(f.hits) - before, p.counters))
while f.get("e3").alive:
    combat.act_attack(f, p, f.get("e3"), rng)
check("grave chorus 2: another kill, another echo", p.counters.get("echoes") == 1)
f.get("e2").hp = 5
before = len(f.hits)
combat.act_ability(f, p, fire, f.get("e2"), rng)                   # the first resolution kills; the echo finds nobody; no echo from an echo
check("grave chorus 2: the echo's own kill raises no echo", not p.counters.get("echoes"), p.counters)

# ---- Storm-Chosen: in a storm every blow arcs to the others in reach
p = player("storm_chosen")
f = fight(p, foe(1), foe(2), conditions=["in_storm"])
e1, e2 = f.get("e1"), f.get("e2")
engaged(f, e1, p); engaged(f, e2, p)
for n in (1, 2):
    before = e2.hp
    while e1.hp == 10**6:
        combat.act_attack(f, p, e1, rng)
    check(f"storm-chosen {n}: lightning arcs from the blow into the other", e2.hp < before, (before, e2.hp))
    e1.hp = e2.hp = 10**6

# ---- Firebrand: your ignites add to the burn instead of replacing it (f227)
p = player("firebrand")
f = fight(p, foe(1, hp=1000))
e = f.get("e1")
for n in (1, 2):
    p.counters["last_hit"] = 40
    combat.add_status(f, e, "burning", 3, p); combat.add_status(f, e, "burning", 3, p)
    before = e.hp
    combat.start_turn(e, f)
    check(f"firebrand {n}: two ignites add up to twice the burn", before - e.hp == 20, (e.ignite, before - e.hp))
    e.statuses.pop("burning", None); perks.on_status_end(e, "burning"); e.hp = 1000
q = player()
f = fight(q, foe(1, hp=1000)); e = f.get("e1")
q.counters["last_hit"] = 40
combat.add_status(f, e, "burning", 3, q); combat.add_status(f, e, "burning", 3, q)
check("without Firebrand the second ignite of the same size changes nothing", abs(e.ignite - 10) < 0.01, e.ignite)

# ---- Thermal Shock: fire on the slowed, cold on the burning - both go off
p = player("thermal_shock")
f = fight(p, foe(1, hp=10**6))
e = f.get("e1")
engaged(f, e, p)
for n, (el, status) in enumerate((("fire", "slowed"), ("cold", "burning")), 1):
    p.element = el
    e.statuses = {status: 3}
    while status in e.statuses:
        before = e.hp
        combat.act_attack(f, p, e, rng)
    check(f"thermal shock {n}: {el} on the {status} sets it off", status not in e.statuses and any("thermal shock" in l for l in f.log), e.statuses)

# ---- Deep Freeze: slowed twice over is frozen
p = player("deep_freeze")
f = fight(p, foe(1))
e = f.get("e1")
for n in (1, 2):
    e.statuses = {}
    combat.add_status(f, e, "slowed", 2, p)
    combat.add_status(f, e, "slowed", 2, p)
    check(f"deep freeze {n}: the second slow is a stun", "stunned" in e.statuses and "slowed" in e.statuses, e.statuses)

# ---- Open Wound (f311): your blows tear a wound twice as deep
from engine import afflictions as _af
def torn(with_perk):
    p = player("open_wound") if with_perk else player()
    f = fight(p, foe(1, hp=10**6))
    e = f.get("e1"); engaged(f, e, p)
    e.statuses = {"bleeding": 3}; e.bleed = 40
    f.log = []
    for i in range(30):
        combat.act_attack(f, p, e, random.Random(i))
        tears = [int(l.split(": ")[-1]) for l in f.log if "wound tears" in l]
        if tears:
            return tears[0], "bleeding" in e.statuses
    return 0, None
plain, _ = torn(False)
deep, still = torn(True)
check("open wound: a hit tears the wound twice as deep", plain > 0 and abs(deep - 2 * plain) <= 1, (plain, deep))
check("...and the wound stays open, to be torn again", still is True)

# ---- Crippling Wounds (f312): a wound you open slows its bearer while it stays open
p = player("crippling_wounds")
f = fight(p, foe(1, hp=10**6))
e = f.get("e1"); engaged(f, e, p)
combat.add_status(f, e, "bleeding", 3, p)
check("crippling wounds: your wound slows them", "slowed" in e.statuses and e.statuses["slowed"] == e.statuses["bleeding"], e.statuses)
_af.bind(f, e, "binds the cut")
check("...and when the wound closes, the slow goes with it", "slowed" not in e.statuses and "bleeding" not in e.statuses, e.statuses)
q = player()
f = fight(q, foe(1, hp=10**6))
e = f.get("e1")
combat.add_status(f, e, "bleeding", 3, q)
check("...a wound from someone without it does not slow", "slowed" not in e.statuses, e.statuses)

# ---- Bulwark Engine: hits taken in a stance charge the heavy; three make it sure
heavy = skill("crush", tier="heavy")
p = player("bulwark_engine", moves=[heavy], stam=10**6)
f = fight(p, foe(1))
e = f.get("e1"); engaged(f, e, p)
p.buffs["wall"] = {"rounds": 9, "mech": {"stance": 30}, "drain": 0, "collapse": "", "name": "Wall", "kind": "stance"}
for n in (1, 2):
    for _ in range(3):
        combat.take_damage(f, p, 5, e, rng)
    check(f"bulwark engine {n}: three blows in the stance are three charges", p.counters.get("bulwark") == 3, p.counters)
    combat.act_ability(f, p, heavy, e, rng)
    h = last_hit(f)
    check(f"bulwark engine {n}: the heavy spends them: +60% and it cannot miss", h["outcome"] != "miss" and any("charges" in s[0] for s in h["steps"]) and not p.counters.get("bulwark"), (h["outcome"], h["steps"]))

# ---- Red Mist: in the red, no stun, fear or slow, and heavies cost as lights
p = player("red_mist", moves=[heavy], hp=400)
f = fight(p, foe(1))
full = combat.cost_of(p, heavy, f)
p.hp = 100
for n, st in enumerate(("stunned", "frightened"), 1):
    check(f"red mist {n}: {st} does not take", not combat.add_status(f, p, st, 2, f.get("e1")) and st not in p.statuses)
light_cost = combat.cost_of(p, skill("jab"), f)
check("red mist: the heavy costs what a light does", combat.cost_of(p, heavy, f) == light_cost < full, (combat.cost_of(p, heavy, f), light_cost, full))

# ---- Pain Engine and Adrenaline: hurt comes back as mana, as stamina
for mid, pool in (("pain_engine", "mana"), ("adrenaline", "stamina")):
    p = player(mid, mana=200, stam=200); setattr(p, pool, 0)
    f = fight(p, foe(1))
    for n in (1, 2):
        before = getattr(p, pool)
        dealt = combat.take_damage(f, p, 40, f.get("e1"), rng)
        check(f"{mid} {n}: half the hurt returns as {pool}", abs(getattr(p, pool) - before - dealt * P[mid]["share"]) < 1, (dealt, getattr(p, pool) - before))

# ---- Overchannel: cast from blood, and the spell lands harder for it
p = player(("overchannel", 2), moves=[fire], mana=0)
f = fight(p, foe(1))
for n in (1, 2):
    hp0 = p.hp
    while True:
        combat.act_ability(f, p, fire, f.get("e1"), rng)
        h = last_hit(f)
        if h["outcome"] != "miss":
            break
    check(f"overchannel {n}: blood pays, and the spell is half again as strong", p.hp < hp0 and any("Overchannel" in s[0] for s in h["steps"]), (hp0 - p.hp, h["steps"]))

# ---- Overcast: a spell on cooldown is cast anyway, at double
cd = spell("comet", "fire", cooldown=3)
p = player("overcast", moves=[cd], mana=10**6)
f = fight(p, foe(1))
combat.act_ability(f, p, cd, f.get("e1"), rng)
base = combat.cost_of(player(moves=[cd]), cd, f)
for n in (1, 2):
    check(f"overcast {n}: the cooldown does not stop it, and it costs twice", combat.can_use(p, cd, f) is None and combat.cost_of(p, cd, f) == 2 * base, (combat.can_use(p, cd, f), combat.cost_of(p, cd, f), base))
    m0 = p.mana
    combat.act_ability(f, p, cd, f.get("e1"), rng)
    check(f"overcast {n}: ...and it resolves", m0 - p.mana == 2 * base and any("twice the price" in s for s in f.story), m0 - p.mana)


# ---- Pack Tactics: a companion's strike on your enemy is yours too
p = player("pack_tactics")
f = fight(p, hire(), foe(1))
e, a = f.get("e1"), f.get("ally_h")
engaged(f, p, e); engaged(f, a, e)
def tam_lands():
    return len([h for h in f.hits if h["att"] == "Tam" and h.get("outcome") != "miss"])
for n in (1, 2):
    f.round = n
    before = len([h for h in f.hits if h["att"] == "you"])
    for want in (1, 2):                                   # the first landed companion blow this round brings yours; a second does not
        start = tam_lands()
        for _ in range(50):
            combat.ally_turn(f, a, rng)
            if tam_lands() > start:
                break
    check(f"pack tactics {n}: you strike alongside the companion, once this round", len([h for h in f.hits if h["att"] == "you"]) == before + 1)

# ---- Martyr: half of what a companion takes is yours
p = player("martyr", hp=1000)
f = fight(p, hire(hp=1000), foe(1))
a = f.get("ally_h")
for n in (1, 2):
    p0, a0 = p.hp, a.hp
    combat.take_damage(f, a, 100, f.get("e1"), rng)
    check(f"martyr {n}: the blow is halved between you", abs((p0 - p.hp) - (a0 - a.hp)) <= 2 and p0 - p.hp >= 40, (p0 - p.hp, a0 - a.hp))

# ---- Bound Pair: a cast mends the summon, its blow refunds you
p = player("bound_pair", moves=[fire], mana=1000)
f = fight(p, spirit(), foe(1))
s, e = f.get("ally_spirit"), f.get("e1")
engaged(f, s, e)
for n in (1, 2):
    s.hp = 50
    combat.act_ability(f, p, fire, e, rng)
    check(f"bound pair {n}: the casting mends the summon", s.hp > 50, s.hp)
    p.mana = 100
    while not [h for h in f.hits if h["att"] == "the spirit" and h["outcome"] not in ("miss",)][n - 1:]:
        combat.ally_turn(f, s, rng)
    check(f"bound pair {n}: the summon's blow refunds mana", p.mana > 100, p.mana)

# ---- Unmaking: the summon ability with the summon out unmakes it, and everything near it burns
call = spell("call_spirit", effect="summon")
p = player("unmaking", moves=[call], mana=1000)
for n in (1, 2):
    f = fight(p.model_copy(deep=True), spirit(form="striker", of="call_spirit"), foe(1, hp=10**6), foe(2, hp=10**6))
    pp, s = f.player, f.get("ally_spirit")
    for e in f.enemies():
        bf.enter_zone(f, e, s.zone_id)
    combat.act_ability(f, pp, call, None, rng)
    check(f"unmaking {n}: the summon is gone and the enemies around it are hurt", not s.alive and all(e.hp < 10**6 for e in f.enemies()), [e.hp for e in f.enemies()])

# ---- Lasting Word: a buff cast does not fade
ward = spell("ward", effect="buff", buff="bulwark", buff_stat="armor")
p = player("lasting_word", moves=[ward], mana=1000)
f = fight(p, hire(), foe(1))
for n, give in enumerate((None, [f.get("ally_h")]), 1):
    combat.act_ability(f, p, ward, None, rng, give=give)
    r = (give or [p])[0]
    check(f"lasting word {n}: the buff on {r.name} lasts the fight", r.buffs.get("ward", {}).get("rounds") == P["lasting_word"]["rounds"], r.buffs)

# ---- Echoing Mend: a heal carries into the most wounded companion
mend = spell("mend", effect="healing")
p = player("echoing_mend", moves=[mend], mana=1000, hp=400)
f = fight(p, hire(hp=200), foe(1))
a = f.get("ally_h")
for n in (1, 2):
    p.hp, a.hp = 100, 50
    combat.act_ability(f, p, mend, None, rng)
    from engine import healing as _heal
    check(f"echoing mend {n}: the companion is healed half as much", a.hp == 50 + round(round(_heal.base(p, mend, p)) * 0.5), (a.hp, _heal.base(p, mend, p)))

# ---- Dread Ambusher: unseen, the strike is always critical
p = player("dread_ambusher")
f = fight(p, foe(1))
e = f.get("e1")
e.statuses["unaware"] = 1
combat.act_attack(f, p, e, rng)
check("dread ambusher 1: a surprised enemy is struck critical", last_hit(f)["outcome"] == "crit", last_hit(f)["outcome"])
e.statuses.pop("unaware", None); bf.gain(p, "concealed")
combat.act_attack(f, p, e, rng)
check("dread ambusher 2: ...and so is one struck from concealment", last_hit(f)["outcome"] == "crit")

# ---- Vessel: what lands on you lands on the summon
p = player("vessel")
f = fight(p, spirit(), foe(1))
s = f.get("ally_spirit")
for n, st in enumerate(("poisoned", "stunned"), 1):
    took = combat.add_status(f, p, st, 2, f.get("e1"))
    check(f"vessel {n}: {st} passes to the summon", not took and st not in p.statuses and st in s.statuses, (p.statuses, s.statuses))

# ---- Devourer: the summon grows on its kills
p = player("devourer")
f = fight(p, spirit(dmg=10**5), foe(1, hp=10), foe(2, hp=10))
s = f.get("ally_spirit")
for n in (1, 2):
    hp0, d0 = s.max_hp, s.weapon_damage
    e = f.enemies()[0]
    while e.alive:
        combat.apply_damage(f, s, e, 1.0, "attacks", rng)
    check(f"devourer {n}: health and damage grow on the kill", s.max_hp > hp0 and s.weapon_damage > d0, (s.max_hp, hp0))

# ---- Shared Skin: a fifth of your hurt is the summon's
p = player("shared_skin", hp=1000)
f = fight(p, spirit(hp=1000), foe(1))
s = f.get("ally_spirit")
for n in (1, 2):
    p0, s0 = p.hp, s.hp
    combat.take_damage(f, p, 100, f.get("e1"), rng)
    check(f"shared skin {n}: a fifth lands on the summon", abs((s0 - s.hp) - 20) <= 2 and abs((p0 - p.hp) - 80) <= 2, (p0 - p.hp, s0 - s.hp))

# ---- Provoke: the one you strike comes for you
p = player("provoke")
f = fight(p, hire(), hire().model_copy(update={"id": "ally_h2", "name": "Bel"}), foe(1))
e = f.get("e1"); engaged(f, p, e)
for n in (1, 2):
    f.round = n
    while e.counters.get("provoked") != n:
        combat.act_attack(f, p, e, rng)
    picks = {perks.pick_target(f, e, [p] + f.allies(), random.Random(s_)).id for s_ in range(20)}
    check(f"provoke {n}: its next action is aimed at you", picks == {"player"}, picks)

# ---- Mirror Plate: a stun or a knockdown comes back on its maker
p = player("mirror_plate")
f = fight(p, foe(1))
e = f.get("e1")
for n, st in enumerate(("stunned", "prone"), 1):
    e.statuses = {}; p.statuses = {}
    combat.add_status(f, p, st, 1, e)
    check(f"mirror plate {n}: {st} is mirrored onto the one who did it", st in e.statuses and st in p.statuses, (p.statuses, e.statuses))

# ---- Unbreakable: no blow takes more than half
p = player(("unbreakable", 50), hp=400)
f = fight(p, foe(1))
for n in (1, 2):
    p.hp = 400
    combat.take_damage(f, p, 10**5, f.get("e1"), rng)
    check(f"unbreakable {n}: a killing blow is capped at half", p.hp >= 200 - 1, p.hp)

# ---- War Drum: your heavy sets the companions' rhythm
p = player("war_drum", moves=[heavy], stam=10**6)
f = fight(p, hire(), foe(1))
a, e = f.get("ally_h"), f.get("e1")
engaged(f, p, e); engaged(f, a, e)
for n in (1, 2):
    while True:
        combat.act_ability(f, p, heavy, e, rng)
        if last_hit(f, "you")["outcome"] != "miss":
            break
    check(f"war drum {n}: the companion's next strike is set", a.counters.get("drum") == 1)
    while True:
        combat.ally_turn(f, a, rng)
        h = last_hit(f, "Tam")
        if h and h["outcome"] != "miss":
            break
    check(f"war drum {n}: ...and lands twice as hard, then the drum is spent", any("War Drum" in s[0] for s in h["steps"]) and not a.counters.get("drum"), h["steps"])

# ---- Fearmonger: even a failed threat frightens
p = player("fearmonger")
f = fight(p, foe(1), foe(2))
for n in (1, 2):
    e = f.get(f"e{n}")
    perks.failed_threat(f, e)
    check(f"fearmonger {n}: the one who laughed it off is frightened anyway", e.statuses.get("frightened") == P["fearmonger"]["rounds"], e.statuses)

# ---- Showstopper: your crit is a cue every companion follows
p = player("showstopper")
f = fight(p, hire(), foe(1))
a, e = f.get("ally_h"), f.get("e1")
engaged(f, p, e); engaged(f, a, e)
for n in (1, 2):
    while True:
        combat.act_attack(f, p, e, rng)
        if last_hit(f, "you")["outcome"] == "crit":
            break
    check(f"showstopper {n}: the cue is given", a.counters.get("cue") == 1)
    while True:
        combat.ally_turn(f, a, rng)
        h = last_hit(f, "Tam")
        if h["outcome"] != "miss":
            break
    check(f"showstopper {n}: ...and the companion's strike is critical", h["outcome"] == "crit" and not a.counters.get("cue"), h["outcome"])

# ---- Flow State: lights are free until the first blow lands
jab = skill("jab")
p = player("flow_state", moves=[jab])
f = fight(p, foe(1))
check("flow state 1: untouched, a light costs nothing", combat.cost_of(p, jab, f) == 0)
combat.take_damage(f, p, 10, f.get("e1"), rng)
check("flow state 2: the first blow lands, and lights cost again", combat.cost_of(p, jab, f) > 0)

# ---- Rampage: a kill in the red restores
p = player(("rampage", 25), hp=400, dmg=10**5)
f = fight(p, foe(1, hp=10), foe(2, hp=10))
for n in (1, 2):
    p.hp = 100
    e = f.enemies()[0]
    while e.alive:
        combat.act_attack(f, p, e, rng)
    check(f"rampage {n}: the kill restores a quarter", p.hp == 200, p.hp)

# ---- Consecration: a heal sears the undead pressing you
p = player("consecration", moves=[mend], mana=1000, hp=400)
f = fight(p, foe(1, category="undead"), foe(2, category="undead"))
for n in (1, 2):
    e = f.get(f"e{n}")
    engaged(f, p, e)
    p.hp = 100
    combat.act_ability(f, p, mend, None, rng)
    check(f"consecration {n}: the undead engaged with the healed is seared", e.hp < 10**6, e.hp)

# ---- Two-Fisted and Pack Alpha
p = player("two_fisted")
f = fight(p, foe(1))
check("two-fisted: two items a turn", perks.item_limit(f, p) == 2 and perks.item_limit(f, player()) == 1)
p = player("pack_alpha")
f = fight(p, beast(), foe(1, category="beast"))
picks = {(perks.pick_target(f, f.get("e1"), [p] + f.allies(), random.Random(s_)) or p).id for s_ in range(30)}
check("pack alpha: with the animal beside you, the beast goes for it, never you", picks == {"ally_wolf"}, picks)
f = fight(p, spirit(), foe(1, category="beast"))
check("pack alpha: a summon is not an animal companion", perks.pick_target(f, f.get("e1"), [p] + f.allies(), random.Random(1)) is None)

# ---- Overabundance: healing past full hardens into a barrier, up to the cap - an ability, then a draught's worth through mend()
mendspell = spell("mend", effect="healing", tier="heavy")
p = player("overabundance", moves=[mendspell])
f = fight(p, foe(1))
p.hp = p.max_hp - 10
combat.act_ability(f, p, mendspell, None, rng)
from engine import healing as _heal
heal = _heal.base(p, mendspell, p)
check("overabundance 1: the heal tops you up and the rest is a barrier", p.hp == p.max_hp and abs(p.shield - (heal - 10)) <= 1, (p.hp, p.shield, heal))
had = p.shield
healed, shielded = perks.mend(f, p, p, p.max_hp)             # a draught's worth, at full: all barrier, but never past the cap
cap = p.max_hp * P["overabundance"]["cap"]
check("overabundance 2: at full, the whole heal is barrier, capped at 40% of life", healed == 0 and shielded > 0 and p.shield == round(cap), (healed, shielded, p.shield, cap))
plain = player(moves=[mendspell]); g = fight(plain, foe(1)); plain.hp = plain.max_hp
perks.mend(g, plain, plain, 50)
check("...without the perk, healing past full is simply lost", plain.shield == 0)

# ---- Challenger: a call for single combat in a fight with people - the leader answers, the rest stand down, twice
for n, words in ((1, "I challenge your leader to single combat - face me alone"), (2, "send your champion, just you and me")):
    p = player("challenger", dmg=10)
    chief = foe(9, level=7, rank="elite"); chief.name = "the chief"
    f = fight(p, hire(), chief, foe(1), foe(2))
    f.get("e1").counters["x"] = 0
    took = perks.challenge(f, words, rng)
    standing = f.enemies()
    check(f"challenger {n}: the leader faces you alone and the rest stand down", took and standing == [chief] and all(e.fled for e in (f.get("e1"), f.get("e2"))), (took, [e.name for e in standing]))
    check(f"challenger {n}: ...and your companions hold back", all(a.order == "hold" for a in f.allies()))
    check(f"challenger {n}: it is one call a fight", not perks.challenge(f, words, rng))
p = player("challenger", dmg=10)
f = fight(p, foe(1, category="beast"), foe(2, category="beast"))
check("challenger: wolves do not take challenges", not perks.challenge(f, "fight me alone, one on one", rng))
p = player(dmg=10)
f = fight(p, foe(1), foe(2))
check("challenger: without the perk, the words are only words", not perks.challenge(f, "fight me alone, one on one", rng) and len(f.enemies()) == 2)

# ---- Glass Cannon: spells crit twice as often; no armor heavier than cloth
bolt = spell("bolt", element="fire")
for n in (1, 2):
    crits = {}
    for has_it in (False, True):
        p = player(*(["glass_cannon"] if has_it else []), moves=[bolt])
        f = fight(p, foe(1), record=False)
        p.spell_kind = "spell"
        hits = 0
        for s_ in range(3000):
            out, _ = combat.roll_attack(p, f.get("e1"), f, random.Random(n * 10000 + s_))
            hits += out == "crit"
        p.spell_kind = ""
        crits[has_it] = hits
    check(f"glass cannon {n}: a spell crits about twice as often", 1.7 <= crits[True] / max(1, crits[False]) <= 2.3, crits)
p = player("glass_cannon")
f = fight(p, foe(1), record=False)
plain = [combat.roll_attack(p, f.get("e1"), f, random.Random(s_))[0] == "crit" for s_ in range(3000)].count(True)
q = player(); g = fight(q, foe(1), record=False)
plain_q = [combat.roll_attack(q, g.get("e1"), g, random.Random(s_))[0] == "crit" for s_ in range(3000)].count(True)
check("...but a weapon blow is untouched", plain == plain_q, (plain, plain_q))
from engine import equipment as eq, items as itm, pools as _pools
import simlib as _sl2
gc, _ = _sl2.make_character("mage", random.Random(5))
from core.models import Passive, PowerTier
gc.passives.append(Passive(id="gc", name="Glass Cannon", description="d", tier=PowerTier.LIGHT, mechanic="glass_cannon", value=1))
heavy = next(b for b in itm.CATALOG.values() if b.slot == "body" and getattr(b, "weight", "") == "heavy" and not b.ward)
plate = itm.make_item(heavy.id, "common", 1, random.Random(1)) if hasattr(itm, "make_item") else None
if plate is None:
    from engine import crafting as _cr
    plate = _cr.make_gear(heavy, "iron", 30, random.Random(1), 0)
gc.level = 99
for a in ("strength", "dexterity", "constitution"):
    setattr(gc.attributes, a, 99)
msg = eq.check(gc, plate)
check("glass cannon: plate cannot be borne", msg is not None and "Glass Cannon" in msg, msg)

# ---- Conduit: a spell leaps on, one enemy per affliction on its target, at half; a leap never leaps
for n in (1, 2):
    p = player("conduit", moves=[bolt])
    f = fight(p, foe(1), foe(2), foe(3), foe(4))
    t = f.get("e1")
    for st in (["poisoned"], ["poisoned", "slowed"])[n - 1]:
        t.statuses[st] = 3
    before = {e.id: e.hp for e in f.enemies()}
    p.spell_kind = "spell"
    perks.conduct(f, p, t, 100, rng)
    p.spell_kind = ""
    struck = [e for e in f.enemies() if e is not t and e.hp < before[e.id]]
    check(f"conduit {n}: {n} affliction(s), {n} leap(s)", len(struck) == n, [e.id for e in struck])
p = player("conduit"); f = fight(p, foe(1), foe(2))
p.spell_kind = "spell"
before = f.get("e2").hp
perks.conduct(f, p, f.get("e1"), 100, rng)
check("conduit: no afflictions, no leap", f.get("e2").hp == before)

# ---- the draw never gates on the rolled kit: the world teaches abilities too, so every perk can be offered
import simlib as _sl
from character import creation
from llm.contracts import ClassInterpretation
interp = ClassInterpretation(archetype="warrior", custom_class="Dragoon", summary="s", families=["warrior", "rogue"],
                             primary_attributes=["strength"], focus="combat", uses_companions=False,
                             combat_identity="a leaping lancer", themes=["dragoon", "leap", "lancer"])
seen = set()
for seed in range(25):
    seen |= {o.mechanic for o in creation.draw_mechanics(interp, random.Random(seed)).values()}
check("a dragoon with no leap rolled can still be offered the leap perk", "deathleap" in seen and "quickstep" not in seen, sorted(seen))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
