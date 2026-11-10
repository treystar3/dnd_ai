"""(f570) Cover and harm from the surroundings go better where the ground has something for them. To make cover (create_cover) the
improviser's zone wants cover, concealment, hard going or a squeeze; to bring the surroundings down on a foe (damage) the foe's zone
wants something to drop, kick or topple (hazardous, elevated, cover, hard going). Where there is none the act is still tried, never
refused: its odds take combat.yaml improv.scant_odds and a line from the scant pool says the ground is poor, naming a zone next to it
that would serve, if any. A fight with no battlefield takes no shift. The line is picked without dice and reads differently on a retry."""
import random, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 70)
simlib.install(stub)
from engine import checks, combat, combat_improv, data_check
from engine.battlefield import BattleEdge, BattleZone, Battlefield
from world.loader import authored

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = authored()
I = combat.RULES["improv"]
POOL = I["scant"]

def ground(here_tags, near_tags=None, foe_zone=None):
    zones = {"z1": BattleZone(id="z1", name="open ground", tags=here_tags)}
    edges = []
    if near_tags is not None:
        zones["z2"] = BattleZone(id="z2", name="a jumble of boulders", tags=near_tags)
        edges.append(BattleEdge(a="z1", b="z2"))
    if foe_zone:
        zones["z3"] = BattleZone(id="z3", name="a scree slope", tags=foe_zone)
        edges.append(BattleEdge(a="z1", b="z3"))
    return Battlefield(zones=zones, edges=edges, start="z1")

def fight(field, name="the troll"):
    char, _ = simlib.make_character("warrior", random.Random(2))
    me = combat.fighter_from_character(char)
    troll = combat.fighter_from_creature(world.bestiary["troll"], 3, "normal", "e1", name=name)
    f = combat.Combat(fighters=[me, troll], place="greywood")
    f.battlefield = field
    for x in (me, troll):
        x.zone_id = "z1" if field else x.zone_id
    return f, me, troll

def fills(case, near="the jumble of boulders"):
    return {l.format(here="the open ground", Here="The open ground", near=near, target="the troll") for l in case}

# ---- the rule: which ground is poor
f, me, t = fight(ground(["open"]))
why = combat_improv.scant_ground(f, me, t, "create_cover")
check("cover on open ground, nothing near: poor ground, said in the world's voice", why in fills(POOL["create_cover"]["none"]), why)
f, me, t = fight(ground(["open"], ["cover", "difficult"]))
why = combat_improv.scant_ground(f, me, t, "create_cover")
check("...with boulders next to it: the line names them", why in fills(POOL["create_cover"]["near"]) and "the jumble of boulders" in why, why)
f, me, t = fight(ground(["cover"]))
check("cover where there is cover: no word, no shift", combat_improv.scant_ground(f, me, t, "create_cover") is None)
ok = True
for tag in ("concealed", "difficult", "narrow"):
    f, me, t = fight(ground([tag]))
    ok = ok and combat_improv.scant_ground(f, me, t, "create_cover") is None
check("...and where the zone is concealed, hard going or narrow", ok)
f, me, t = fight(ground(["open"]))
why = combat_improv.scant_ground(f, me, t, "damage")
check("harm from the surroundings with nothing around the foe: poor ground, naming the foe", why in fills(POOL["damage"]["none"])
      and "the troll" in why, why)
f, me, t = fight(ground(["open"], foe_zone=["hazardous"]))
t.zone_id = "z3"
check("...the foe's zone decides, not the improviser's: a hazardous slope serves", combat_improv.scant_ground(f, me, t, "damage") is None)
f, me, t = fight(ground(["open"]))
check("the other improvisations want nothing of the ground", all(combat_improv.scant_ground(f, me, t, e) is None
                                                               for e in combat_improv.EFFECTS if e not in ("create_cover", "damage")))
f, me, t = fight(None)
check("a fight with no battlefield takes no shift", combat_improv.scant_ground(f, me, t, "create_cover") is None
      and combat_improv.scant_ground(f, me, t, "damage") is None)

# ---- every zone is said definitely and in the singular, whatever its name's shape
import re
from pathlib import Path
names = sorted(set(re.findall(r"name: ([^,}]+)", Path("data/rules/battlefields.yaml").read_text(encoding="utf-8"))))
said = [combat_improv.definite(n) for n in names]
check("every authored zone name becomes a definite phrase", len(names) > 50 and all(d.startswith("the ") for d in said),
      [d for d in said if not d.startswith("the ")])
check("...never 'the a', 'the the' or a bare preposition", not any(re.match(r"the (a|an|the|among|between) ", d) for d in said),
      [d for d in said if re.match(r"the (a|an|the|among|between) ", d)])
check("...the shapes: an article, a place, a plural", (combat_improv.definite("a small clearing"), combat_improv.definite("among the pillars"),
      combat_improv.definite("the reeds")) == ("the small clearing", "the ground among the pillars", "the ground of reeds"))
f, me, t = fight(ground(["open"]))
f.battlefield.zones["z1"].name = "a small clearing"
why = combat_improv.scant_ground(f, me, t, "create_cover")
check("a line that starts with the zone starts definitely", not why.startswith("A ") and "a small clearing" not in why, why)

# ---- the odds: lower on poor ground, by the data's amount, inside the bounds
f, me, t = fight(ground(["open"]))
good, poor = combat_improv.odds_for(me, "create_cover"), combat_improv.odds_for(me, "create_cover", scant=True)
check("poor ground lowers the odds by scant_odds", poor == max(I["min"], good + I["scant_odds"]), (good, poor, I["scant_odds"]))
check("...and never below the floor", combat_improv.odds_for(me, "disable", scant=True) >= I["min"])

# ---- through the resolver: always rolled, never refused
for scant_tags, expect in ((["open"], True), (["cover"], False)):
    f, me, t = fight(ground(scant_tags))
    seen = []
    real = checks.roll
    checks.roll = lambda odds, rng, *a, **k: seen.append(odds) or ("success", 1)
    try:
        combat_improv.resolve(f, me, t, "I duck behind the cart", random.Random(1), "create_cover")
    finally:
        checks.roll = real
    poor_said = any(l in fills(POOL["create_cover"]["none"]) for l in f.story)
    if expect:
        check("open ground: rolled at the lower odds, the poor ground said, and the cover still made",
              seen == [combat_improv.odds_for(me, "create_cover", True)] and poor_said and "covered" in me.position_tags,
              (seen, f.story, me.position_tags))
        check("...told in order: what was tried, the ground, what came of it",
              f.story[0].startswith("You try it") and f.story[1] in fills(POOL["create_cover"]["none"]) and len(f.story) >= 3, f.story)
        check("...and logged as poor ground", any("poor ground" in l for l in f.log), f.log)
    else:
        check("good ground: rolled at the usual odds, nothing said of the ground",
              seen == [combat_improv.odds_for(me, "create_cover")] and not poor_said, (seen, f.story))

f, me, t = fight(ground(["open"]))
real = checks.roll
checks.roll = lambda *a, **k: ("failure", 99)
try:
    combat_improv.resolve(f, me, t, "I duck behind the cart", random.Random(1), "create_cover")
finally:
    checks.roll = real
check("a failure on poor ground: tried, the ground, then the failure", len(f.story) == 3 and f.story[0].startswith("You try it")
      and f.story[1] in fills(POOL["create_cover"]["none"]) and "goes wrong" in f.story[2], f.story)

# ---- the lines: a pool, varied on a retry, no dice spent to choose
f, me, t = fight(ground(["open"]))
said = set()
for _ in range(6):
    said.add(combat_improv.scant_ground(f, me, t, "create_cover"))
    f.log.append("a retry")
check("a retry in the same round reads differently, from the pool", len(said) >= 2 and said <= fills(POOL["create_cover"]["none"]), said)
rng = random.Random(5); before = rng.getstate()
combat_improv.scant_ground(f, me, t, "create_cover")
check("...chosen without the fight's dice", rng.getstate() == before)

# ---- pronouns: a named person holds their ground, not its (f569's lines)
f, me, t = fight(ground(["cover"]), name="Captain Vell")
t.category = "hostile people"
real_contest = combat.contest
combat.contest = lambda *a, **k: "none"
real = checks.roll
checks.roll = lambda *a, **k: ("success", 1)
try:
    combat_improv.resolve(f, me, t, "I shove him", random.Random(1), "force_move")
finally:
    combat.contest = real_contest
    checks.roll = real
held = [l for l in f.story if "ground" in l]
check("a foe who holds their ground is said with the fight's own possessive", combat.possessive(t) == "their" and held and "their ground" in held[0], (held, combat.possessive(t)))

# ---- an ally who makes cover drags it between themselves and them, not itself
f, me, t = fight(ground(["cover"]))
me.side, me.name = "ally", "Maren Holt"
real = checks.roll
checks.roll = lambda *a, **k: ("success", 1)
try:
    combat_improv.resolve(f, me, t, "she ducks behind the cart", random.Random(1), "create_cover")
finally:
    checks.roll = real
check("an ally's cover is said with her own reflexive", any("herself" in l for l in f.story), f.story)

# ---- held at start-up
import copy
B2 = copy.deepcopy(I); B2["scant"]["damage"] = ["a list, not cases"]
check("a malformed pool is reported, not raised", any("scant.damage" in p for p in data_check.improv_problems(B2)))
check("the real data has no problems", data_check.improv_problems() == [], data_check.improv_problems())
B = copy.deepcopy(I)
B["effects"]["create_cover"]["needs"] = ["cover", "sandbags"]
B["scant"]["damage"]["near"] = ["Little to drop on {target}."]
B["scant"]["create_cover"]["none"].append("Little here {oops}.")
B["scant"]["create_cover"]["none"].append("Bare ground — little.")
B["scant_odds"] = 15
B["scant"]["distract"] = {"none": ["Little."], "near": ["Little; {near}."]}
found = data_check.improv_problems(B)
for what in ("sandbags", "damage", "oops", "dash", "scant_odds", "distract"):
    check(f"the start-up check names it: {what}", any(what in p for p in found), found)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
