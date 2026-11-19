"""(f757) The line of a blow comes before what the blow set off (found by the code audit, engine2-3: a killing blow on a chief that
made his goblins run was handed to the narrator as "The first goblin breaks, seeing the chief fall" and only then "You hit the chief",
and the narrator is told to keep the order of EVENTS). Every line told inside a damage path (a barrier taking the blow, a floor, a
rout, a torn wound, thorns, a guard's share, an arc's kill) reaches the story after the line of the blow or the side effect that caused
it, and the fight's log keeps the same order. The finder's case (a killing blow that routs, and a riposte that does), then the kind:
a barrier, a torn wound, thorns and what the thorns themselves set off, a guard's share, a Storm Chosen arc's kill, a flurry whose
second strike kills (its strikes still one line, what they set off after it), a fence over seeded rounds (every line a damage path
tells inside a blow sits after that blow's line), and the fence in tools/purity.py: damage outside a blow goes through the one helper
that places its caller's line first. No die moves: only where lines sit.
Run: python tools/sim/cause_first_757_test.py"""
import random
import re
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 1))
simlib.quiet_console()
import purity
from engine import battlefield as bf
from engine import combat
from engine import damage as DMG
from engine import martial
from engine.combat import Move

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


def fighter(fid, side, hp=10 ** 6, dex=12, dmg=12, level=5, **kw):
    attrs = {a: 12 for a in combat.ATTRIBUTES}
    attrs["dexterity"] = dex
    return combat.Fighter(id=fid, name=fid, side=side, level=level, attrs=attrs, hp=hp, max_hp=kw.pop("max_hp", hp), stamina=10 ** 4,
                          max_stamina=10 ** 4, mana=10 ** 4, max_mana=10 ** 4, weapon_damage=dmg, weapon_attrs=["strength"], hold=2, **kw)


def fight(*fs, **kw):
    f = combat.Combat(fighters=list(fs), record=True, serial="cf", **kw)
    combat.ensure_field(f)
    f.opened = True
    return f


def where(f, pred):
    """Indexes of the story's lines that pred holds for."""
    return [i for i, s in enumerate(f.story) if pred(s)]


def blow_at(f, rec):
    """Where the blow's own line stands: the line carrying its tag."""
    got = where(f, lambda s: s.endswith(f"[{rec['tag']}]"))
    return got[0] if got else None


def first_blow(f, att, dfn):
    return next((h for h in f.hits if h["att"] == att.name and h["dfn"] == dfn.name), None)


def before_all(i, later):
    return i is not None and bool(later) and all(i < j for j in later)


# ---- 1. the finder's case: a killing blow on the chief makes the goblins run (engine2-3)
found = None
for seed in range(200):
    p = fighter("player", "player", dmg=10 ** 5)
    chief = fighter("chief", "enemy", hp=50, level=8, dmg=0.001)
    g1, g2 = fighter("goblin 1", "enemy", level=2, dmg=0.001), fighter("goblin 2", "enemy", level=2, dmg=0.001)
    f = fight(p, chief, g1, g2)
    bf.engage(f, p, chief)
    combat.act_attack(f, p, chief, random.Random(seed))
    if not chief.alive and where(f, lambda s: " breaks" in s):
        found = (f, p, chief)
        break
check("(a seed where the chief's fall routs the goblins)", found is not None)
if found:
    f, p, chief = found
    i = blow_at(f, first_blow(f, p, chief))
    routs = where(f, lambda s: " breaks" in s)
    check("the blow that fells the chief is told before any goblin breaks", before_all(i, routs), f.story)
    hit_log = [k for k, l in enumerate(f.log) if l.startswith(f"{p.name} ") and f" {chief.name}: " in l and "damage" in l]
    fled = [k for k, l in enumerate(f.log) if re.search(r"goblin \d (flees|yields|surrenders)", l)]
    check("...and the fight's log keeps the same order: the blow, then the flight", bool(hit_log) and before_all(hit_log[0], fled), f.log)

# ---- 2. the same, set off by a riposte inside a foe's turn: the riposte's hit before the rout (the finder's check, seed 23's shape)
found = None
for seed in range(200):
    p = fighter("player", "player", dmg=10 ** 5)
    p.legendary["riposte"] = 1
    chief = fighter("chief", "enemy", hp=50, level=8, dmg=5, always_miss=True)
    g1, g2 = fighter("goblin 1", "enemy", level=2, dmg=0.001), fighter("goblin 2", "enemy", level=2, dmg=0.001)
    f = fight(p, chief, g1, g2)
    bf.engage(f, chief, p)
    combat.apply_damage(f, chief, p, 1.0, "attacks", random.Random(seed))
    if not chief.alive and where(f, lambda s: " breaks" in s):
        found = (f, p, chief)
        break
check("(a seed where the riposte fells the chief and the goblins run)", found is not None)
if found:
    f, p, chief = found
    miss = where(f, lambda s: s.startswith("The chief goes for you"))
    i = blow_at(f, first_blow(f, p, chief))
    check("the miss, then the riposte's hit, then the goblins breaking", bool(miss) and before_all(miss[0], [i] if i is not None else [])
          and before_all(i, where(f, lambda s: " breaks" in s)), f.story)

# ---- 3. a barrier takes the blow: told after the blow it took
p = fighter("player", "player", dmg=30)
wolf = fighter("wolf 1", "enemy", shield=3)
f = fight(p, wolf)
bf.engage(f, p, wolf)
for seed in range(50):
    if wolf.shield <= 0:
        break
    combat.apply_damage(f, p, wolf, 1.0, "attacks", random.Random(seed))
rec = next((h for h in f.hits if h.get("outcome") in martial.LANDS), None)
barrier = where(f, lambda s: "barrier takes the blow" in s)
check("a barrier's line follows the blow it took", rec is not None and before_all(blow_at(f, rec), barrier), f.story)

# ---- 4. a torn wound: told after the bite that tore it, in the story and in the log
found = None
for seed in range(100):
    p = fighter("player", "player", hp=4000)
    wolf = fighter("wolf 1", "enemy", dmg=10)
    f = fight(p, wolf)
    bf.engage(f, wolf, p)
    combat.add_status(f, p, "bleeding", 3, wolf)
    combat.apply_damage(f, wolf, p, 1.0, "attacks", random.Random(seed))
    if where(f, lambda s: "wound open again" in s):
        found = (f, p, wolf)
        break
check("(a seed where the bite lands on the open wound)", found is not None)
if found:
    f, p, wolf = found
    i = blow_at(f, first_blow(f, wolf, p))
    check("a torn wound is told after the bite that tore it", before_all(i, where(f, lambda s: "wound open again" in s)), f.story)
    bite = [k for k, l in enumerate(f.log) if l.startswith(f"{wolf.name} attacks {p.name}: ")]
    tear = [k for k, l in enumerate(f.log) if "wound tears" in l]
    check("...and logged after it", bool(bite) and before_all(bite[0], tear), f.log)

# ---- 5. thorns: told after the hit that met them; and what the thorns set off (the striker's own barrier) after the thorns
found = None
for seed in range(100):
    p = fighter("player", "player", hp=4000)
    p.legendary["thorns"] = 50
    wolf = fighter("wolf 1", "enemy", dmg=10, shield=1)
    f = fight(p, wolf)
    bf.engage(f, wolf, p)
    combat.apply_damage(f, wolf, p, 1.0, "attacks", random.Random(seed))
    if where(f, lambda s: "(Thorns)" in s):
        found = (f, p, wolf)
        break
check("(a seed where the bite lands on the thorns)", found is not None)
if found:
    f, p, wolf = found
    i = blow_at(f, first_blow(f, wolf, p))
    thorns = where(f, lambda s: "(Thorns)" in s)
    own = where(f, lambda s: "barrier takes the blow" in s)
    check("thorns are told after the hit that met them", before_all(i, thorns), f.story)
    check("...and the striker's barrier, which the thorns struck, after the thorns", bool(thorns) and before_all(thorns[0], own), f.story)

# ---- 6. a guard's share: the guard steps in after the blow, and what the share sets off (its barrier) after the guard's line
found = None
for seed in range(100):
    p = fighter("player", "player", hp=4000)
    p.legendary["guarded"] = 50
    odly = fighter("Odly", "ally", hp=4000, shield=1)
    wolf = fighter("wolf 1", "enemy", dmg=40)
    f = fight(p, odly, wolf)
    bf.engage(f, wolf, p)
    combat.apply_damage(f, wolf, p, 1.0, "attacks", random.Random(seed))
    if where(f, lambda s: "throws itself in the way" in s):
        found = (f, p, wolf)
        break
check("(a seed where the guard takes a share)", found is not None)
if found:
    f, p, wolf = found
    i = blow_at(f, first_blow(f, wolf, p))
    guard = where(f, lambda s: "throws itself in the way" in s)
    check("the guard's share is told after the blow it shared", before_all(i, guard), f.story)
    check("...and the guard's barrier after the guard's line", bool(guard) and before_all(guard[0], where(f, lambda s: "barrier takes the blow" in s)), f.story)

# ---- 7. a Storm Chosen arc kills a wolf that was not struck: the arc is told before the rout its kill set off
found = None
for seed in range(200):
    p = fighter("player", "player", dmg=200)
    p.legendary["storm_chosen"] = 1
    w1, w2 = fighter("wolf 1", "enemy", dmg=0.001), fighter("wolf 2", "enemy", hp=3, dmg=0.001)
    w3 = fighter("wolf 3", "enemy", dmg=0.001)
    f = fight(p, w1, w2, w3, conditions=["in_storm"])
    bf.engage(f, p, w1)
    combat.act_attack(f, p, w1, random.Random(seed))
    if not w2.alive and where(f, lambda s: "seeing the second wolf fall" in s):
        found = (f, p, w1)
        break
check("(a seed where the arc's kill routs the pack)", found is not None)
if found:
    f, p, w1 = found
    i = blow_at(f, first_blow(f, p, w1))
    storm = where(f, lambda s: s.startswith("The storm answers"))
    check("the blow, then the arc, then the wolves breaking at the arc's kill", bool(storm) and before_all(i, storm[:1])
          and before_all(storm[0], where(f, lambda s: "seeing the second wolf fall" in s)), f.story)


# ---- 8. a flurry whose second strike kills: its strikes are still one line, and what they set off follows it
def volley(seed, hp):
    p = fighter("player", "player", dmg=12)
    chief = fighter("chief", "enemy", hp=hp, max_hp=10 ** 6, level=8, dmg=0.001, shield=2)
    g1, g2 = fighter("goblin 1", "enemy", level=2, dmg=0.001), fighter("goblin 2", "enemy", level=2, dmg=0.001)
    f = fight(p, chief, g1, g2)
    bf.engage(f, p, chief)
    martial.flurry(f, p, chief, Move(id="volley", name="Lance Volley", effect="damage", tier="moderate", reach="melee",
                                     resource="stamina", martial_form="flurry", hits=2), 1.0, random.Random(seed))
    return f, chief


found = None
for seed in range(300):
    f, chief = volley(seed, 10 ** 6)                              # measured: what each strike deals, the barrier taking the first
    parts = next((h.get("parts") for h in f.hits if h.get("parts")), None)
    if not parts or len(parts) != 2 or not all(int(x.get("final") or 0) > 0 for x in parts):
        continue
    f, chief = volley(seed, int(parts[0]["final"]) + 1)           # the same strikes, the second now a killing one
    if not chief.alive and where(f, lambda s: " breaks" in s):
        found = f
        break
check("(a seed where the volley's second strike fells the chief and routs the goblins)", found is not None)
if found:
    f = found
    one = where(f, lambda s: "strikes in one motion" in s)
    check("the flurry is still one line, with no strike told apart", len(one) == 1
          and not where(f, lambda s: "keeps coming" in s or "strikes again" in s), f.story)
    check("...and the barrier the first strike met, and the rout the second set off, follow it", bool(one)
          and before_all(one[0], where(f, lambda s: "barrier takes the blow" in s))
          and before_all(one[0], where(f, lambda s: " breaks" in s)), f.story)

# ---- 9. the fence: over seeded rounds, every line a damage path tells inside a blow sits after that blow's own line
WIN, PAIRS, SEEN = [], [], set()
_resolve, _apply, _new_hit = DMG.resolve, combat._apply_damage, combat.new_hit


def resolve(path, c, *a, **k):
    before = {id(s) for s in c.story}
    try:
        return _resolve(path, c, *a, **k)
    finally:
        rec = WIN[-1]["rec"] if WIN else None
        if rec is not None:
            for s in c.story:
                if id(s) not in before and id(s) not in SEEN:
                    SEEN.add(id(s))
                    PAIRS.append((s, rec))


def apply(c, *a, **k):
    WIN.append({"rec": None})
    try:
        return _apply(c, *a, **k)
    finally:
        WIN.pop()


def new_hit(c, att, dfn, label):
    rec = _new_hit(c, att, dfn, label)
    if WIN and WIN[-1]["rec"] is None:
        WIN[-1]["rec"] = rec
    return rec


DMG.resolve, combat._apply_damage, combat.new_hit = resolve, apply, new_hit
checked, wrong = 0, []
try:
    for seed in range(40):
        PAIRS.clear()
        SEEN.clear()
        p = fighter("player", "player", hp=5000, dmg=40)
        p.legendary.update({"thorns": 50, "guarded": 30, "riposte": 1})
        odly = fighter("Odly", "ally", hp=3000, dmg=25, shield=20)
        chief = fighter("chief", "enemy", hp=300, level=8, dmg=25, shield=30)
        gobs = [fighter(f"goblin {n}", "enemy", hp=120, level=2, dmg=20, shield=8) for n in (1, 2, 3)]
        f = fight(p, odly, chief, *gobs)
        for x in (chief, *gobs):
            bf.engage(f, x, p if x is not gobs[2] else odly)
        combat.add_status(f, p, "bleeding", 3, gobs[0])
        combat.add_status(f, chief, "bleeding", 3, p)
        rng = random.Random(seed)
        combat.act_attack(f, p, chief, rng)
        combat.finish_round(f, rng)
        for s, rec in PAIRS:
            i = next((n for n, x in enumerate(f.story) if x is s), None)
            j = blow_at(f, rec)
            if i is None or j is None:
                continue
            checked += 1
            if j > i:
                wrong.append((seed, s, f.story[j]))
finally:
    DMG.resolve, combat._apply_damage, combat.new_hit = _resolve, _apply, _new_hit
check("(the seeded rounds hold lines told inside damage paths: barriers, torn wounds, thorns, a guard, routs)", checked >= 40, checked)
check("every one sits after the line of the blow that set it off", not wrong, wrong[:4])

# ---- 10. the fence in tools/purity.py: damage outside a blow goes through the one helper that tells its caller's line first
calls = getattr(purity, "take_damage_calls", None)
missing = getattr(purity, "take_damage_exempt_missing", None)
check("no take_damage call outside the helper and the named list", calls is not None and calls() == [], calls() if calls else "no fence")
check("...every name on the list is still a call that exists (the list may only shrink)", missing is not None and missing() == [],
      missing() if missing else "no fence")
check("...and the list is short: the blow's own call", len(getattr(purity, "TAKE_DAMAGE_EXEMPT", ())) == 1, getattr(purity, "TAKE_DAMAGE_EXEMPT", None))
if calls:
    planted = "def zap(c, f, rng):\n    return C.take_damage(c, f, 3, None, rng)\n"
    check("...a planted call is caught", purity.take_damage_calls_in(planted, "engine/planted.py") == ["engine/planted.py:2 calls take_damage"],
          purity.take_damage_calls_in(planted, "engine/planted.py"))

check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
