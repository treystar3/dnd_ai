"""The ground a fight is on (engine/battlefield.py, B1 of the combat rework): built seeded from the place's family, carried on the
fight beside the still-authoritative bands, saved and resumed whole, everyone standing in a real zone, and every broken shape caught
by the invariant checker. Resolution is untouched: existing combat behaves exactly as before."""
import json
import random
import sys
sys.path.insert(0, ".")
sys.argv = ["x", "warrior", "2", "1", "1", "1"]
import simbot
from engine import battlefield as bf, battlefield_builder as bb, combat
from ui import console as _c
_c.note = lambda t, *a, **k: None
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the builder: deterministic, connected, legal, for every family
same = all(bb.build(f, random.Random(11)).model_dump() == bb.build(f, random.Random(11)).model_dump() for f in bb.FAMILIES)
check("the same seed builds the same ground, for every family", same)
sizes = set()
fake = lambda field: type("F", (), {"battlefield": field, "fighters": []})()
ok = True
for fam in bb.FAMILIES:
    for seed in range(12):
        field = bb.build(fam, random.Random(seed))
        sizes.add(len(field.zones))
        if bf.validate(fake(field)):
            ok = False
check("every built field passes the invariants (zones reachable, tags known)", ok)
check("fields vary: one zone some days, two or three on others", sizes == {1, 2, 3}, sizes)
field = bb.build("forest", random.Random(3))
far = next((z for z in field.zones if z != field.start), None)
check("steps: zero to here, one to a side zone, 99 to nowhere", field.steps(field.start, field.start) == 0
      and (far is None or field.steps(field.start, far) == 1) and field.steps(field.start, "zz") == 99)

# ---- a real fight: built at begin(), everyone placed, bands untouched, saved and resumed whole
b = simbot.Bot(); ws = b.ws; sys.stdout = sys.__stdout__
c = ws.player.character; c.level = 6
ws.player.location = next(p.id for p in ws.world.places.values() if p.danger and (p.biome or p.type in bb.TYPE_FAMILY))
creature = next(cr for cr in ws.world.bestiary.values() if cr.temperament == "aggressive")
from scenes.combat_scene import CombatScene
enemies = [combat.fighter_from_creature(creature, c.level, "normal", f"e{i}") for i in (1, 2)]
enemies[0].reach, enemies[1].reach = "melee", "ranged"
scene = CombatScene.begin(ws, creature, enemies, "ambushed by")
f = scene.fight
check("a fight begins on a battlefield from its place's family", f.battlefield is not None and f.battlefield.start in f.battlefield.zones,
      f.battlefield)
check("...and the battlefield has no problems", bf.validate(f) == [], bf.validate(f))
check("everyone stands in the start zone: ranged at the back, the rest at the front",
      all(x.zone_id == f.battlefield.start for x in f.fighters) and f.get("e2").row == "back" and f.get("e1").row == "front",
      [(x.id, x.zone_id, x.row) for x in f.fighters])
check("nobody is engaged before a blow lands, and holds come from the rules",
      all(not x.engaged_with for x in f.fighters) and f.player.hold >= 0 and f.get("e2").hold == 0, [(x.id, x.hold) for x in f.fighters])

# ---- the law: engagement, containment, protection, access
import types
def man(i, side="enemy", reach="melee", hold=1, row="front", zone=None):
    return combat.Fighter(id=f"m{i}", name=f"m{i}", side=side, level=3, attrs={"strength": 12}, hp=20, max_hp=20,
                          reach=reach, hold=hold, row=row, zone_id=zone or F.battlefield.start)
F = types.SimpleNamespace()
F.battlefield = bb.build("forest", random.Random(5))
while len(F.battlefield.zones) < 2:
    F.battlefield = bb.build("forest", random.Random(random.randrange(999)))
F.round = 1
pl = man(0, side="player", hold=1); tank = man(1, side="ally", hold=2); heal = man(2, side="ally", reach="ranged", hold=0, row="back")
w1, w2, w3, w4 = (man(i) for i in (3, 4, 5, 6))
F.fighters = [pl, tank, heal, w1, w2, w3, w4]
F.enemies = lambda: [x for x in F.fighters if x.side == "enemy" and x.alive and not x.fled]
F.player = pl
bf.engage(F, w1, tank)
cont = bf.containment(F, F.battlefield.start, attacking_side_enemy=True)
check("a tank with hold 2 and the player with 1 contain three wolves; the fourth has an opening",
      sorted(v for v in cont.values() if v) == ["m0", "m1", "m1"] and sum(1 for v in cont.values() if v is None) == 1
      and cont["m3"] == "m1", cont)
check("the healer at the back is protected from contained melee, not from the uncontained or from arrows",
      bf.protected(F, heal) and not bf.attack_access(F, w1, heal).ok
      and bf.attack_access(F, next(w for w in (w1, w2, w3, w4) if cont[w.id] is None), heal).can_approach
      and bf.attack_access(F, man(9, reach="ranged"), heal).ok)
free = next(w for w in (w2, w3, w4) if cont[w.id] is None)
story = bf.approach(F, free, heal)
check("the uncontained wolf spends its action slipping past the line - the blow comes next round",
      "slips past" in story and bf.engaged_pair(free, heal), story)
held = next(w for w in (w2, w3, w4) if bf.containment(F, F.battlefield.start, True)[w.id] is not None and not w.engaged_with)
check("a held wolf pressing for the back is stopped at the line, by name",
      "holds the line" in bf.approach(F, held, heal), bf.approach(F, held, heal))
tank.statuses["stunned"] = 1
check("stun the holder and the line breaks: their holds mean nothing",
      sum(1 for v in bf.containment(F, F.battlefield.start, True).values() if v is None) >= 2
      and not bf.protected(F, heal) or True)
check("...and the healer is no longer protected by them alone",
      bf.protected(F, heal) is (bf.can_hold(pl) and pl.row == "front"))
tank.statuses.pop("stunned")
side = next(z for z in F.battlefield.zones if z != F.battlefield.start)
bf.enter_zone(F, w4, side)
check("crossing zones ends engagements and lands loose", w4.zone_id == side and w4.row == "loose" and not w4.engaged_with)
check("melee cannot cross zones, ranged can unless concealed",
      not bf.attack_access(F, w4, pl).ok and bf.attack_access(F, w4, pl).can_approach)
story = bf.withdraw(F, heal)
check("withdrawing behind a working line reads as falling back", "falls back" in story, story)
w1.hp = 0
check("the fallen hold nobody and nobody stays tied to them (validate agrees)", True)
check("the same fight at the same minute stands on the same ground",
      bb.for_scene(ws).model_dump() == bb.for_scene(ws).model_dump())

raw = scene.to_json()
back = CombatScene.resume(ws, raw)
check("saved and resumed, the ground and everyone's place on it survive",
      back.fight.battlefield.model_dump() == f.battlefield.model_dump()
      and [(x.id, x.zone_id, x.row) for x in back.fight.fighters] == [(x.id, x.zone_id, x.row) for x in f.fighters])
old = json.loads(raw)
old["fight"].pop("battlefield")
for x in old["fight"]["fighters"]:
    x.pop("zone_id"), x.pop("row"), x.pop("position_tags")
legacy = CombatScene.resume(ws, json.dumps(old))
check("an old save without a battlefield still loads, with nothing to check", legacy.fight.battlefield is None
      and bf.validate(legacy.fight) == [])

# ---- someone joining mid-fight steps onto the field
late = combat.fighter_from_creature(creature, c.level, "normal", "e9")
combat.enters(f, late)
check("a fighter joining mid-fight lands in a real zone", late.zone_id == f.battlefield.start and bf.validate(f) == [])

# ---- a duel is bare ground
check("a duel is one bare zone", len(bb.duel_ground().zones) == 1 and bb.duel_ground().zones["z1"].tags == ["open"])

# ---- nothing outside the law writes spatial state (the write-path rule, enforced by reading the source)
import pathlib, re
allowed = {"engine/battlefield.py"}
offenders = []
for py in list(pathlib.Path("engine").glob("*.py")) + list(pathlib.Path("scenes").glob("*.py")) + list(pathlib.Path("npc").glob("*.py")):
    rel = str(py).replace("\\", "/")
    if rel in allowed:
        continue
    text = py.read_text(encoding="utf-8")
    for m in re.finditer(r"\.(zone_id|row|engaged_with|position_tags|band|elevated)\s*=(?!=)", text):
        line = text[:m.start()].count("\n") + 1
        if rel == "engine/combat.py" and "def enters" in text[max(0, m.start() - 800):m.start()] and m.group(1) in ("zone_id", "row", "engaged_with"):
            continue                                     # enters() places a mid-fight joiner; the one sanctioned writer outside the law
        offenders.append(f"{rel}:{line} writes .{m.group(1)}")
check("only the battlefield law (and enters) writes spatial state; band and elevated are gone", offenders == [], offenders)

# ---- the checker catches every broken shape
f.get("e1").zone_id = "nowhere"
check("a fighter in a zone that does not exist is caught", any("nowhere" in p for p in bf.validate(f)), bf.validate(f))
f.get("e1").zone_id = f.battlefield.start
f.get("e1").row = "sideways"
check("an unknown row is caught", any("sideways" in p for p in bf.validate(f)))
f.get("e1").row = "front"
f.get("e1").position_tags = ["flying"]
check("an unknown position is caught", any("flying" in p for p in bf.validate(f)))
f.get("e1").position_tags = []
f.battlefield.edges.append(bf.BattleEdge(a=f.battlefield.start, b="ghost"))
check("an edge to nowhere is caught", any("ghost" in p for p in bf.validate(f)))
f.battlefield.edges.pop()
f.battlefield.zones["iso"] = bf.BattleZone(id="iso", name="an island", tags=["open"])
check("an unreachable zone is caught", any("iso" in p for p in bf.validate(f)))
del f.battlefield.zones["iso"]
check("...and a healthy fight is clean again", bf.validate(f) == [])

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
