"""(f504) The active-effect kinds and the stage tables as data, with both-ways allow-list checks. stages.yaml's blow path equals the
literal list recorded here from engine/combat.py take_damage (likewise status_eligibility from add_status, the stacking recipes from
raw_damage, mitigate, pools.maximum, resist_factor and mechanics, and hit_steps from _apply_damage: the last read from the source by
its hit_step calls, in order), so a hand reorder fails a test before it moves a fixture; every stage id has a function and every
function is in the yaml (and the same for the recipes); a copy with an unknown id makes the check name it; EffectDef refuses
assignment; every status row of combat.yaml, every ability buff, every command that lasts, every summon form and the three f499 marks
have a kind; and the stage functions, not yet wired, give what take_damage gives on a battery of random blows (the record included),
so f505 can switch the callers with the fixtures as the only remaining proof. Nothing stays in the process."""
import ast
import copy
import pathlib
import random
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 4))
import yaml
from pydantic import ValidationError
from engine import bosses, combat, damage, data_check, effects, stacking, streams

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

ST = yaml.safe_load(pathlib.Path("data/rules/stages.yaml").read_text(encoding="utf-8"))
AE = yaml.safe_load(pathlib.Path("data/rules/active_effects.yaml").read_text(encoding="utf-8"))
CB = yaml.safe_load(pathlib.Path("data/rules/combat.yaml").read_text(encoding="utf-8"))

# ---- the orders, pinned to the literals recorded from engine/combat.py
BLOW = ["petrified", "before_damage", "resistance", "blood_pact", "category_ward", "hardening", "aegis", "last_stand", "stoneskin",
        "plating", "spellward", "unbroken", "guardian", "companion_durability", "barrier", "stoneform", "mana_veil", "mana_shield",
        "nothing_through", "ward_conversion", "rounded", "duel_floor", "lifeline", "tether", "boss_last_stand", "breath", "mentor_floor",
        "deathless", "deathward", "yields_floor", "health", "on_fall", "after_damage", "healing_after_damage", "release", "morale",
        "avenger", "yields_break", "boss_after_damage", "second_wind", "rebound"]
ELIGIBILITY = ["unyielding", "earthshaker", "stoneform", "iron_will", "element_ward", "attune_extend", "sanctified", "boss_resisted",
               "perk_transform", "bloodless", "affliction_law", "record", "crippling_chain", "winding_cancel"]
RECIPES = {"base_damage": ["flat", "percent"], "mitigate": ["percent", "flat"], "pools": ["percent", "flat", "needs"],
           "resistance": ["sum", "clamp"], "mechanics": ["additive"]}
check("stages.yaml's blow path is take_damage's order, as recorded", ST["damage"]["blow"] == BLOW, ST["damage"]["blow"])
check("...its status eligibility is add_status's order", ST["status_eligibility"] == ELIGIBILITY, ST["status_eligibility"])
check("...its stacking recipes are today's, each part in its order", ST["stacking"] == RECIPES, ST["stacking"])
check("...the bypasses are declared: a tick and a torn wound", set(ST["damage"]) == {"blow", "dot_tick", "tear"}
      and ST["damage"]["dot_tick"] == ["tick_floor", "tick_health", "tick_on_tick", "tick_duel_end"] and ST["damage"]["tear"] == ["tick_floor", "tear_health"], ST["damage"])

# the hit steps, read from _apply_damage's source in order: every hit_step call's label, and the two delegations between them
src = pathlib.Path("engine/combat.py").read_text(encoding="utf-8")
tree = ast.parse(src)
fn = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_apply_damage")
labels = []
for node in ast.walk(fn):
    if not isinstance(node, ast.Call):
        continue
    f = node.func
    name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
    if name == "hit_step" and len(node.args) >= 3:
        arg = node.args[2]
        if isinstance(arg, ast.Constant) and arg.value:
            labels.append((node.lineno, arg.value))
        elif isinstance(arg, ast.Subscript) and isinstance(arg.value, ast.Dict):
            labels.append((node.lineno, " | ".join(k.value for k in arg.value.keys if isinstance(k, ast.Constant) and k.value in ("graze", "crit")).replace("graze | crit", "")
                           or "Glancing blow | Critical hit"))
    elif name in ("hit_mult", "damage_mult") and isinstance(f, ast.Attribute):
        labels.append((node.lineno, ("spellcraft." if name == "hit_mult" else "combat_perks.") + name))
steps_in_code = [l for _, l in sorted(labels)]
steps_in_code = [("Glancing blow | Critical hit" if "Glancing" in s else s) for s in steps_in_code]
check("...and its hit steps are _apply_damage's hit_step calls, in order, with the two delegations where they fall",
      ST["hit_steps"] == steps_in_code and len(steps_in_code) == 23, (ST["hit_steps"], steps_in_code))

# ---- both ways
check("every stage a path names has a function, and every function is named by a path", set(damage.STAGES) == {i for ids in ST["damage"].values() for i in ids})
check("every recipe has a function, and every function a recipe, with its parts", set(stacking.RECIPES) == set(ST["stacking"])
      and all(tuple(ST["stacking"][r]) == stacking.PARTS[r] for r in ST["stacking"]))
check("the tree passes the check", data_check.tables_problems() == [], data_check.tables_problems())
st2 = copy.deepcopy(ST); st2["damage"]["blow"].insert(3, "a_stage_nobody_wrote")
check("a stage the data names that no function runs is named", any("a_stage_nobody_wrote" in p and "no stage" in p for p in data_check.tables_problems(ST=st2)),
      data_check.tables_problems(ST=st2))
st3 = copy.deepcopy(ST); st3["damage"]["blow"].remove("rebound")
check("...and a function no path names", any("'rebound'" in p and "no path names" in p for p in data_check.tables_problems(ST=st3)), data_check.tables_problems(ST=st3))
st4 = copy.deepcopy(ST); st4["stacking"]["mitigate"] = ["percent", "flat", "moonlight"]; st4["stacking"].pop("pools")
found = data_check.tables_problems(ST=st4)
check("...a recipe's unknown part, and a recipe the table forgot", any("moonlight" in p for p in found) and any("'pools'" in p for p in found), found)
ae2 = copy.deepcopy(AE); ae2["kinds"]["slowed"]["family"] = "mood"; ae2["kinds"]["burning"]["deltas"] = "statuses.smoke"; ae2["kinds"]["quarry"]["expiry"] = "never"
found = data_check.tables_problems(AE=ae2)
check("...a kind's unknown family, a deltas row combat.yaml does not hold, an unknown expiry",
      any("slowed" in p and "mood" in p for p in found) and any("burning" in p and "smoke" in p for p in found) and any("quarry" in p and "never" in p for p in found), found)
cb2 = copy.deepcopy(CB); cb2["statuses"]["dizzy"] = {"accuracy": -5}
check("...and a status row with no kind", any("statuses.dizzy" in p for p in data_check.tables_problems(CB=cb2)), data_check.tables_problems(CB=cb2))
check("the startup check carries the tables", data_check.check() == [], data_check.check())

# ---- the kinds
try:
    effects.KINDS["slowed"].family = "mood"
    frozen = False
except (ValidationError, TypeError, AttributeError):
    frozen = True
check("EffectDef refuses assignment", frozen and effects.KINDS["slowed"].family == "status")
check("six families, the expiry and stacking rules as declared", effects.FAMILIES == ("stat_modifier", "damage_redirect", "triggered_reaction", "status", "movement", "summon")
      and set(effects.EXPIRY) >= {"fight", "rounds", "turns_of_target", "charges", "while_status"} and set(effects.STACKING) == {"replace", "refresh", "stack", "strongest", "bigger"})
T = yaml.safe_load(pathlib.Path("data/rules/ability_traits.yaml").read_text(encoding="utf-8"))
S = yaml.safe_load(pathlib.Path("data/rules/summons.yaml").read_text(encoding="utf-8"))
missing = [k for k in CB["statuses"] if k not in effects.KINDS or effects.KINDS[k].family != "status"]
check("every status row of combat.yaml is a status kind, with its deltas row", not missing and all(effects.KINDS[k].deltas == f"statuses.{k}" for k in CB["statuses"]), missing)
check("...the affliction law as recorded: a burn's strongest, a wound's bigger, a poison's stack, the rest refresh",
      effects.KINDS["burning"].stacking == "strongest" and effects.KINDS["bleeding"].stacking == "bigger" and effects.KINDS["poisoned"].stacking == "stack"
      and all(effects.KINDS[k].stacking == "refresh" for k in CB["statuses"] if k not in ("burning", "bleeding", "poisoned")))
missing = [k for k in T["buffs"] if k not in effects.KINDS]
check("every ability buff is a kind, replaced by a new casting", not missing and all(effects.KINDS[k].stacking == "replace" and effects.KINDS[k].expiry == "rounds" for k in T["buffs"]), missing)
check("every command that lasts, the stance, the rousing rider and the relics' lasting power are kinds",
      all(k in effects.KINDS for k in ("guard", "press", "hold", "distract", "stance", "rouse", "relic_buff", "renew", "bolster")))
check("every summon form is a kind of the summon family, the bound one lasting the fight",
      all(k in effects.KINDS and effects.KINDS[k].family == "summon" for k in S["forms"]) and effects.KINDS["bound"].expiry == "fight")
check("the f499 marks are kinds (the rows keep their own family words until f507)", all(k in effects.KINDS for k in ("quarry", "withering", "last_heal"))
      and effects.KINDS["hexed"].family == "status" and not effects.KINDS["hexed"].deltas)
check("the ground's effects and a curse are kinds", all(k in effects.KINDS for k in ("frozen_ground", "ball_lightning", "burning_ground", "snowdrift", "earthen_barricade", "curse")))

# ---- the stage functions give what take_damage gives: a battery of random blows, the record included (not yet wired: f505)
game = simlib.campaign("tables_504", cls="warrior", seed=4, location="south_fields")      # the bestiary, through the one helper (f450)
world = game.scene.world
char, _ = simlib.make_character("warrior", random.Random(1))
MECHS = ["blood_pact", "hardening", "aegis", "last_stand", "stoneskin", "plating", "spellward", "unbroken", "guardian", "mana_veil",
         "mana_shield", "ward_conversion", "deathless", "deathward", "second_wind", "retribution", "spellmirror", "avenger", "stoneform",
         "penetrating", "lifeline", "martyr", "unbreakable"]
IDS = [cid for cid in ("wolf", "bandit", "skeleton", "goblin", "ogre", "awakened_shrub", "young_red_dragon") if cid in world.bestiary]


def build(seed: int):
    r = random.Random(seed)
    p = combat.fighter_from_character(char)
    ally = combat.companion_fighter(world.bestiary["wolf"], 3, "ally_c1", "Grey")
    foes = [combat.fighter_from_creature(world.bestiary[cid], r.randint(1, 12), "normal", f"e{i + 1}", f"{cid} {i + 1}")
            for i, cid in enumerate(r.sample(IDS, 2))]
    if r.random() < 0.3:
        foes[0].rank = "boss"
        foes[0].boss = bosses.make(bosses.kit_for(foes[0].category), "leader", foes[0].name)
    f = combat.Combat(fighters=[p, ally] + foes, place="the test ground", record=True, serial="t504", round=r.randint(1, 5))
    combat.ensure_field(f)
    f.duel = r.random() < 0.08
    f.mentor = r.random() < 0.08
    for x in f.fighters:
        x.legendary = {m: r.choice([10, 25, 50]) for m in r.sample(MECHS, r.randint(0, 4))}
        x.mech_names = {m: m.title() for m in x.legendary}
        x.shield = r.choice([0.0, 0.0, 15.0, 40.0])
        x.mana = r.uniform(0, x.max_mana) if x.max_mana else 0.0
        x.hp = r.uniform(1, x.max_hp)
        if r.random() < 0.08:
            x.statuses["petrified"] = 2
        x.tether = r.choice([0, 0, 0, 30])
        x.breath = r.random() < 0.1
        x.yields_at = r.choice([0.0, 0.0, 0.0, 0.3])
        x.hardening_stacks = r.randint(0, 3)
        x.counters = dict(x.counters)
    dfn = r.choice(f.fighters)
    src = r.choice(f.fighters + [None])
    return f, dfn.id, (src.id if src is not None else None), r.uniform(0, 160), r.choice(["physical", "magical"]), r.random() < 0.7


def run(path_fn, f, d, s, amount, dtype, seed, recorded):
    g = f.model_copy(deep=True)
    dfn, src = g.get(d), (g.get(s) if s else None)
    rec = combat.new_hit(g, src or g.player, dfn, "hits") if recorded else None
    snap = streams.snapshot()
    try:
        dealt = path_fn(g, dfn, amount, src, random.Random(seed), dtype, rec)
    finally:
        streams.restore(snap)
    return dealt, g.model_dump(), rec


streams.begin(4, 504, "the battery")
parted, tried = None, 0
for seed in range(300):
    f, d, s, amount, dtype, recorded = build(seed)
    a = run(lambda g, dfn, am, src, rng, dt, rec: combat.take_damage(g, dfn, am, src, rng, dt, rec=rec), f, d, s, amount, dtype, seed, recorded)
    b = run(lambda g, dfn, am, src, rng, dt, rec: damage.resolve("blow", g, dfn, am, src, rng, dt, rec=rec), f, d, s, amount, dtype, seed, recorded)
    tried += 1
    if a != b:
        diff = next((k for k in a[1] if a[1][k] != b[1][k]), None)
        parted = (seed, a[0], b[0], diff, a[2], b[2])
        break
check(f"resolve('blow') gives what take_damage gives on {tried} random blows: the damage dealt, every fighter, the story, the record", parted is None, parted)

game.close()
import shutil
shutil.rmtree("saves/tables_504", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
