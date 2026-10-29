"""Martial techniques (f233): forms (strike, sweep, flurry, windup, counter), deterministic maneuvers decided by size, martial control
as a contested maneuver, the planner's hit counts by family, and no more Lunge."""
import random
import sys
sys.path.insert(0, ".")
import simlib; simlib.install(simlib.Stub("warrior", 1))
from engine import ability_slots as AS, ability_traits as AT, battlefield as bf, combat, martial as MA
from engine.battlefield import Battlefield, BattleZone, BattleEdge
from engine.combat import Move
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def player(**kw):
    attrs = {a: 10 for a in combat.ATTRIBUTES}; attrs["strength"] = 16
    return combat.Fighter(id="player", name="you", side="player", level=5, attrs=attrs, hp=10**5, max_hp=10**5, stamina=10**5,
                          max_stamina=10**5, weapon_damage=12, weapon_attrs=["strength"], hold=3, accuracy=300, **kw)

def foe(i=1, hp=10**6, size="Medium", **kw):
    return combat.Fighter(id=f"e{i}", name=f"foe {i}", side="enemy", level=5, attrs={a: 8 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
                          weapon_damage=8, behaviors={"fearless": 1}, zone_id="a", size=size, accuracy=300, **kw)

def fight(*fs):
    f = combat.Combat(fighters=list(fs), record=False)
    f.battlefield = Battlefield(zones={z: BattleZone(id=z, name=z) for z in "ab"}, edges=[BattleEdge(a="a", b="b")], start="a")
    for x in fs:
        x.zone_id = x.zone_id or "a"
    return f

def tech(name="Cut", tier="moderate", effect="damage", reach="melee", **kw):
    return Move(id=name.lower(), name=name, effect=effect, tier=tier, reach=reach, resource="stamina", **kw)

rng = random.Random(4)

# ---- forms
p, a, b, c = player(), foe(1), foe(2), foe(3)
f = fight(p, a, b, c)
bf.engage(f, p, a); bf.engage(f, p, b)
combat.act_ability(f, p, tech("Whirl", martial_form="sweep"), a, rng)
check("sweep hits everyone engaged with you", a.hp < a.max_hp and b.hp < b.max_hp and c.hp == c.max_hp, (a.hp, b.hp, c.hp))

p, e = player(), foe(); f = fight(p, e); bf.engage(f, p, e)
combat.act_ability(f, p, tech("Storm", martial_form="flurry", hits=4), e, rng)
check("flurry hits the set number of times", sum(1 for l in f.log if "Storm" in l or "strikes again" in l) == 4, f.log)
check("...and its card says so", "4 times, each for 31%" in AT.describe(tech("Storm", martial_form="flurry", hits=4)), AT.describe(tech("Storm", martial_form="flurry", hits=4)))

# (f371) a flurry is one attack: one line for the narrator, one marker, one figure, one row in the log, each strike kept for the working
import re
from scenes.combat_scene import place_figures
p, e = player(), foe(); f = fight(p, e); f.record = True; bf.engage(f, p, e)
combat.act_ability(f, p, tech("Lance Volley", martial_form="flurry", hits=3), e, random.Random(4))
mine = [h for h in f.hits if h["att"] == p.name]
told = [s for s in f.story if "Lance Volley" in s]
check("a flurry is one record with each strike in its parts", len(mine) == 1 and len(mine[0]["parts"]) == 3 and mine[0]["planned"] == 3
      and mine[0]["final"] == sum(x["final"] for x in mine[0]["parts"] if x["outcome"] in ("hit", "crit", "graze")), [(h["label"], h.get("figure")) for h in mine])
check("...told to the narrator as one line, strikes in one motion, with one marker", len(told) == 1 and "three strikes in one motion" in told[0]
      and len(re.findall(r"\[h\d+\]", " ".join(f.story))) == 1 and not any("strikes again" in s or "keeps coming" in s for s in f.story), f.story)
check("...with one figure that counts the hits and sums the damage", re.fullmatch(r"\((3|\d of 3) hits(, \d critical)?, \d+ damage.*\)", mine[0]["figure"]) is not None, mine[0]["figure"])
check("...and one line in the combat numbers", sum(1 for l in f.log if "Lance Volley" in l or "strikes again" in l) == 1, f.log)
out = place_figures("You drive the lance in three quick thrusts [h1].", f.hits, False)
check("...so the passage carries one number for it", out.count("damage") == 1 and mine[0]["figure"] in out, out)
nxt = combat.new_hit(f, p, e, "strikes")
check("...and the next blow's tag is new, though the strikes' records were folded away", nxt["tag"] not in {h["tag"] for h in f.hits if h is not nxt}, [h["tag"] for h in f.hits])
first_two = [x["final"] for x in mine[0]["parts"][:2]]
if all(first_two):                                         # with this seed the first two strikes land: a foe that dies to the second
    p, e = player(), foe(hp=first_two[0] + 1); f = fight(p, e); f.record = True; bf.engage(f, p, e)
    combat.act_ability(f, p, tech("Lance Volley", martial_form="flurry", hits=3), e, random.Random(4))
    mine = [h for h in f.hits if h["att"] == p.name]
    check("a flurry that drops its target early is still one attack, and says the rest never came", len(mine) == 1 and len(mine[0]["parts"]) == 2
          and mine[0]["planned"] == 3 and any("down before the third strike can follow" in s for s in f.story), (f.story, [h.get("figure") for h in mine]))
p, e = player(), foe(); f = fight(p, e); bf.engage(f, p, e)
combat.act_ability(f, p, tech("Lance Volley", martial_form="flurry", hits=3), e, rng)
check("without records (the odds simulated) every strike is still struck and logged", sum(1 for l in f.log if "Lance Volley" in l or "strikes again" in l) == 3, f.log)

p, e = player(), foe(); f = fight(p, e); bf.engage(f, p, e)
combat.act_ability(f, p, tech("Crusher", martial_form="windup"), e, rng)
check("a wind-up does nothing on its first turn", e.hp == e.max_hp and p.charging)
f.round += 1; acts = combat.start_turn(p, f, rng)
check("...lands on the next, and that turn goes to it", e.hp < e.max_hp and acts is False)
p, e = player(), foe(); f = fight(p, e); bf.engage(f, p, e)
combat.act_ability(f, p, tech("Crusher", martial_form="windup"), e, rng)
MA.maneuver(f, foe(9), p, tech("Jar", maneuver="stagger"), rng)        # an enemy staggers the one winding up
check("...and a stagger breaks it", not p.charging)

p, e = player(), foe(); f = fight(p, e); bf.engage(f, p, e)
combat.act_ability(f, p, tech("Riposte", martial_form="counter"), e, rng)
check("counter readies, and deals nothing yet", e.hp == e.max_hp and p.counter_move)
h = p.hp
combat.apply_damage(f, e, p, 1.0, "hits", rng)
check("...the first engaged attacker is answered", e.hp < e.max_hp and not p.counter_move, f.log[-3:])
p2 = player(); e2 = foe(); f2 = fight(p2, e2); bf.engage(f2, p2, e2)
tot_plain = tot_met = 0
for i in range(30):
    q = player(); x = foe(); g = fight(q, x); bf.engage(g, q, x)
    h0 = q.hp; combat.apply_damage(g, x, q, 1.0, "hits", random.Random(i)); tot_plain += h0 - q.hp
    q = player(); x = foe(); g = fight(q, x); bf.engage(g, q, x)
    combat.act_ability(g, q, tech("Riposte", martial_form="counter"), x, random.Random(i))
    h0 = q.hp; combat.apply_damage(g, x, q, 1.0, "hits", random.Random(i)); tot_met += h0 - q.hp
check("...and its blow lands weakened", tot_met < tot_plain * 0.85, (tot_plain, tot_met))
p, e = player(), foe(); f = fight(p, e); bf.engage(f, p, e)
combat.act_ability(f, p, tech("Riposte", martial_form="counter"), e, rng)
combat.start_turn(p, f, rng)
check("...and it lapses at your next turn", not p.counter_move)

# ---- maneuvers, by size
def hit_with(mid, size="Medium", **fk):
    p, e = player(), foe(size=size, **fk); f = fight(p, e); bf.engage(f, p, e)
    for i in range(10):
        if combat.act_ability(f, p, tech("M", maneuver=mid), e, random.Random(i)) is None and any(MA.MANEUVERS[mid]["label"] in l for l in f.story) or e.statuses or e.sundered:
            break
    return p, e, f
p, e, f = hit_with("trip"); check("trip knocks a man down", "prone" in e.statuses)
p, e, f = hit_with("trip", "Huge"); check("...but not a giant", "prone" not in e.statuses)
p, e, f = hit_with("pin", "Large"); check("pin works only on your size or smaller", "grappled" not in e.statuses)
p, e, f = hit_with("pin"); check("...and holds your own size", "grappled" in e.statuses)
p, e, f = hit_with("disarm", category="beast"); check("disarm does nothing to claws and fangs", "weakened" not in e.statuses)
p, e, f = hit_with("disarm", category="person"); check("...but knocks a weapon aside", "weakened" in e.statuses)
p, e, f = hit_with("rend", category="undead"); check("rend cannot bleed the dead", "bleeding" not in e.statuses)
p, e, f = hit_with("rend"); check("...but bleeds the living", "bleeding" in e.statuses)
p, e, f = hit_with("sunder", armor=100); check("sunder breaks armor", e.sundered == 15, e.sundered)
p, e, f = hit_with("hamstring"); check("hamstring slows", "slowed" in e.statuses)
p, e, f = hit_with("feint"); check("feint exposes", "exposed" in e.statuses)

# ---- martial control: a maneuver, contested
got = 0
for i in range(20):
    p, e = player(), foe(); f = fight(p, e); bf.engage(f, p, e)
    combat.act_ability(f, p, tech("Leg Sweep", effect="control", maneuver="trip"), e, random.Random(i))
    got += "prone" in e.statuses
    if e.hp != e.max_hp:
        bad.append("martial control dealt damage")
check("martial control trips without dealing damage, when it wins the contest", got >= 8, got)

# ---- the planner
counts = {}
for fam in (["guardian"], ["warrior"], ["monk"], ["monk", "guardian"]):
    seen = set(); forms = set(); man = 0; techs = 0; riders = 0
    for seed in range(200):
        r = random.Random(seed)
        slots = [dict(AS._base(), effect="damage", resource="stamina", reach="melee", tier="moderate", rider="rend") for _ in range(4)]
        slots.append(dict(AS._base(), effect="control", resource="stamina", reach="melee", tier="light", rider="chill"))
        AS.assign_martial(slots, fam, r)
        for s in slots:
            if s["martial_form"] == "flurry": seen.add(s["hits"])
            if s["martial_form"]: forms.add(s["martial_form"])
            if s["maneuver"]: man += 1
            riders += bool(s["rider"])
            techs += 1
    counts[tuple(fam)] = (max(seen) if seen else 0, forms, man / techs, riders)
check("a juggernaut is offered flurries of 2 at most", counts[("guardian",)][0] == 2, counts[("guardian",)])
check("a warrior up to 3", counts[("warrior",)][0] == 3, counts[("warrior",)])
check("a monk up to 6", counts[("monk",)][0] == 6, counts[("monk",)])
check("a mixed class takes the highest of its families", counts[("monk", "guardian")][0] == 6)
check("every form is planned", counts[("warrior",)][1] == {"strike", "sweep", "flurry", "windup", "counter"}, counts[("warrior",)][1])
check("techniques carry maneuvers, never chance riders", counts[("warrior",)][3] == 0 and counts[("warrior",)][2] > 0.6, counts[("warrior",)])
check("Lunge is gone", "lunge" not in AT.SHAPES)
s = dict(AS._base(), effect="damage", resource="stamina", reach="melee", martial_form="flurry", hits=3, n=1, tier="light")
check("a flurry named as one blow is sent back", AS.text_problem(s, "Heavy Blow", "a single crushing strike") != "")
check("...and one named as several is fine", AS.text_problem(s, "Triple Cut", "three quick slashes in a row") == "", AS.text_problem(s, "Triple Cut", "three quick slashes in a row"))

print("\nFAILED:", bad if bad else "none")
sys.exit(1 if bad else 0)
