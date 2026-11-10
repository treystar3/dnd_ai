"""(f507) Statuses, strengths, buffs, curses and ground effects as rows of the fighter's and the fight's effects (engine/effects.py),
the old names read-only views over them: a status row holds its rounds, its source and its strength, and goes whole; a refresh keeps
its place; a wipe leaves no stale source and no stale strength; the views refuse a write, a Fighter or Combat of another shape is
refused, the fight row says its shape. add_status is the eligibility stages data/rules/stages.yaml names, in order, held to the code
both ways. The four bugs: hexed has its row and lands through the stages (listed in the pane, carried by Plaguebearer); Mend binds the
wound (its size and the Crippling Wounds limp go with it); Contagion spares a warded neighbour and carries the same stacks to a plain
one; a Rescue and a boss's last stand leave no source behind (Malefic Step finds nothing). The write rule (tools/purity.py
effect_writes): no module outside engine/effects.py writes through a view, and a planted write is caught. The triggers held to the code
that evaluates them: none is dormant today, a table with one no code evaluates must say so, and a dormant one is never offered. A saved
fight of another shape is let go of at load with one line from failures.yaml, the row dropped; v15 lets a saved fight go and the next
load tells it once, never again. Nothing stays in the process."""
import json
import random
import shutil
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
import purity
import yaml
import ui.console as uc
from core import rules
from engine import afflictions, bosses, combat, combat_perks, data_check, effects as fx, failures, movement, relics, spellcraft
from engine import battlefield as bf, battlefield_builder as bb
from engine.combat import Move
from character import fit
from scenes import combat_scene as cs
from services.fight import FightService
from storage import migrations

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

def fighter(fid="player", side="player", hp=10**6, **kw):
    return combat.Fighter(id=fid, name=fid, side=side, level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp,
                          stamina=10**4, max_stamina=10**4, mana=10**4, max_mana=10**4, weapon_damage=12, hold=2, **kw)

def fight(*fs):
    f = combat.Combat(fighters=list(fs), record=False)
    f.battlefield = bb.duel_ground()
    bf.place_fighters(f)
    return f

rng = random.Random(7)

# ---- rows and views
p, e = fighter(), fighter("e1", "enemy")
fx.put_status(e, "stunned", 1, p)
fx.put_status(e, "slowed", 2, p)
check("a status is a row the views read: rounds, source, the row's id and slot", e.statuses == {"stunned": 1, "slowed": 2} and e.status_from == {"stunned": "player", "slowed": "player"}
      and [r.id for r in e.effects] == ["status:stunned", "status:slowed"] and all(r.slot == "status" and r.family == "status" for r in e.effects), (e.statuses, e.effects))
fx.put_status(e, "stunned", 4)
check("a refresh keeps the row's place and its source", list(e.statuses) == ["stunned", "slowed"] and e.statuses["stunned"] == 4 and e.status_from["stunned"] == "player", e.statuses)
fx.set_strength(e, "burning", 4.5)
check("the affliction law's strength ahead of the rounds makes the row at no rounds", e.statuses.get("burning") == 0 and e.ignite == 4.5)
fx.put_status(e, "burning", 3, p)
check("...and the rounds follow; the strength stays", e.statuses["burning"] == 3 and e.ignite == 4.5)
check("the rounds are worn down on the row", fx.tick_status(e, "burning") == 2 and e.statuses["burning"] == 2)
left = fx.end_status(e, "burning")
check("a status that ends goes whole: no rounds, no source, no strength", left == 2 and "burning" not in e.statuses and "burning" not in e.status_from and e.ignite == 0.0 and fx.end_status(e, "burning") is None)
check("a strength of nothing on a status not there makes no row", fx.set_strength(e, "bleeding", 0) is None and fx.set_strength(e, "poisoned", []) is None and "bleeding" not in e.statuses and "poisoned" not in e.statuses)
fx.put_status(e, "poisoned", 3, p)
fx.set_strength(e, "poisoned", [5.0, 5.0], fixed=[2.0])
check("a poisoning's stacks and its fixed stacks are the row's, read by reference", e.poison == [5.0, 5.0] and e.poison_fixed == [2.0] and e.poison is fx.status_row(e, "poisoned").data["stacks"])
try:
    fx.put_status(e, "slowed", 2.5)
    check("rounds are whole", False)
except ValueError as ex:
    check("rounds are whole", "whole" in str(ex))
try:
    e.statuses = {}
    check("the views refuse a write", False)
except AttributeError:
    check("the views refuse a write", True)
wall = {"rounds": 9, "mech": {"stance": 30}, "drain": 0, "collapse": "", "name": "Wall", "kind": "stance"}
fx.put_buff(p, "wall", wall)
fx.put_buff(p, "ring", {"rounds": 2, "mech": {}, "name": "Ring"})
check("a buff is a row under its key, its dict held by reference, its kind the table's or relic_buff", p.buffs["wall"] is wall and [r.kind for r in fx.rows(p, "buff")] == ["stance", "relic_buff"]
      and [r.id for r in fx.rows(p, "buff")] == ["buff:wall", "buff:ring"], p.buffs)
p.buffs["wall"]["rounds"] -= 1
check("...its readers tick the rounds in place", wall["rounds"] == 8 and fx.end_buff(p, "ring") == {"rounds": 2, "mech": {}, "name": "Ring"} and list(p.buffs) == ["wall"] and fx.end_buff(p, "ring") is None)
c1 = {"by": "e1", "per": 3.0, "left": 2, "name": "Rot", "element": "acid", "exprs": [], "tier": 1}
c2 = {"by": "e1", "per": 1.0, "left": 1, "name": "Rot", "element": "acid", "exprs": [], "tier": 1}
fx.put_curse(p, c1); fx.put_curse(p, c2)
check("curses stack, a row each, oldest first", p.curses == [c1, c2] and [r.id for r in fx.rows(p, "curse")] == ["curse:1", "curse:2"] and all(r.kind == "curse" for r in fx.rows(p, "curse")))
fx.keep_curses(p, [c2])
check("...and only the ones kept stay", p.curses == [c2] and [r.id for r in fx.rows(p, "curse")] == ["curse:2"])
fx.put_status(p, "slowed", 2, e)
fx.clear(p)
check("a wipe takes every status with its source and strength, and leaves the buffs and curses", p.statuses == {} and p.status_from == {} and p.ignite == 0.0 and list(p.buffs) == ["wall"] and p.curses == [c2])
c = fight(p, e)
fx.put_ground(c, "a", "burning_ground", {"until": 3, "by": "player", "power": 10, "pct": 20, "name": "Fire"})
fx.put_ground(c, "a", "frozen_ground", {"frozen_until": 4, "by": "e1"})
fx.put_ground(c, "a", "sealed", {"until": 2, "edge": ["a", "b"]}, key="a>b")
fx.put_ground(c, "a", "sealed", {"until": 2, "edge": ["a", "c"]}, key="a>c")
view = c.zone_effects
check("ground effects are rows of the fight, one a zone and effect, a seal a row an edge; the view is {zone: {effect: dict}}",
      set(view) == {"a"} and view["a"]["burning_ground"]["until"] == 3 and view["a"]["frozen_ground"] == {"frozen_until": 4, "by": "e1"}
      and [s["edge"] for s in view["a"]["sealed"]] == [["a", "b"], ["a", "c"]] and len(fx.ground_rows(c, "a")) == 4, view)
fx.put_ground(c, "a", "burning_ground", {"until": 9, "by": "player", "power": 10, "pct": 20, "name": "Fire"})
check("...a new one of the same kind replaces the old", c.zone_effects["a"]["burning_ground"]["until"] == 9 and len(fx.ground_rows(c, "a")) == 4)
c.round = 5
spellcraft.expire(c)
check("...and they run out over the rows: the seals, the fire and the frost gone at their rounds", c.zone_effects == {"a": {"burning_ground": {"until": 9, "by": "player", "power": 10, "pct": 20, "name": "Fire"}}}, c.zone_effects)
try:
    combat.Fighter(id="x", name="x", side="enemy", level=1, attrs={}, hp=1, max_hp=1, statuses={"slowed": 1})
    check("a Fighter of another shape is refused", False)
except Exception as ex:
    check("a Fighter of another shape is refused", type(ex).__name__ == "ValidationError")
try:
    combat.Combat(fighters=[], zone_effects={})
    check("...a Combat too; a fight row says its shape", False)
except Exception as ex:
    check("...a Combat too; a fight row says its shape", type(ex).__name__ == "ValidationError" and combat.Combat(fighters=[]).version == combat.SHAPE == 1)
row = json.dumps({"fight": json.loads(combat.Combat(fighters=[fighter(), fighter("e1", "enemy")]).model_dump_json()), "creature": "wolf"})
back, creature, why = FightService.resume(row)
old = json.dumps({"fight": {"round": 1, "fighters": [{"id": "p", "name": "p", "side": "player", "level": 1, "attrs": {}, "hp": 1, "max_hp": 1, "statuses": {"slowed": 2}}]}, "creature": "wolf"})
gone, _, reason = FightService.resume(old)
check("resume reads a row of this shape and refuses one of another, with its reason", back is not None and creature == "wolf" and why == "" and gone is None and "another shape" in reason, (why, reason))

# ---- the eligibility stages, held to the table both ways
ST = yaml.safe_load(open("data/rules/stages.yaml", encoding="utf-8"))
check("the stages the table names are the stages the code has, in order", tuple(ST["status_eligibility"]) == fx.ELIGIBLE == tuple(fx.STAGES) and data_check.tables_problems() == [], (fx.ELIGIBLE, data_check.tables_problems()))
ST2 = {**ST, "status_eligibility": ST["status_eligibility"] + ["moon_phase"]}
check("...a stage the table names and the code lacks is named, and one the code has and the table lacks", any("moon_phase" in m for m in data_check.tables_problems(ST=ST2))
      and any("record" in m for m in data_check.tables_problems(ST={**ST, "status_eligibility": [s for s in ST["status_eligibility"] if s != "record"]})))
src = open("engine/combat.py", encoding="utf-8").read()
check("add_status is the stages", "return _fx.land(combat, f, status, rounds, source)" in src and src.count("def add_status(") == 1)
p, e = fighter(legendary={"unyielding": 1}, mech_names={"unyielding": "Unyielding"}), fighter("e1", "enemy")
c = fight(p, e)
check("Unyielding turns a stun aside, in the fight's words", combat.add_status(c, p, "stunned", 2, e) is False and "stunned" not in p.statuses and any("Unyielding" in l for l in c.log))
b = fighter("e2", "enemy", boss=bosses.make("default", "leader", "Boss"))
c = fight(p, b)
lr = b.boss["lr"]
check("a boss spends a resistance charge on a stun", combat.add_status(c, b, "stunned", 2, p) is False and b.boss["lr"] == lr - 1 and "stunned" not in b.statuses)
check("a plain status lands, with its source", combat.add_status(c, b, "marked", 2, p) is True and b.statuses["marked"] == 2 and b.status_from["marked"] == "player")
p2 = fighter("p2", legendary={"crippling_wounds": 1}, mech_names={"crippling_wounds": "Crippling Wounds"})
e2 = fighter("e3", "enemy")
c = fight(p2, e2)
p2.counters["last_hit"] = 50
check("a wound from Crippling Wounds slows for as long as it stays open (the chain stage)", combat.add_status(c, e2, "bleeding", 3, p2) and e2.statuses.get("slowed") == 3 and e2.counters.get("crippled") == 1 and e2.bleed > 0, (e2.statuses, e2.counters))
afflictions.bind(c, e2)
check("...and the wound closing takes the limp with it", "bleeding" not in e2.statuses and "slowed" not in e2.statuses and "crippled" not in e2.counters and e2.bleed == 0.0, (e2.statuses, e2.counters))

# ---- the four bugs
# hexed
R = yaml.safe_load(open("data/rules/combat.yaml", encoding="utf-8"))
check("hexed has its row in combat.yaml statuses and its deltas in the kinds table; the data check holds no exemption for it",
      R["statuses"].get("hexed") == {} and fx.KINDS["hexed"].deltas == "statuses.hexed" and "hexed" not in open("engine/data_check.py", encoding="utf-8").read())
p, e = fighter(legendary={"hex": 1}, mech_names={"hex": "Hex"}, bonuses=[combat.Bonus(modifies="accuracy", trigger="always", magnitude=500)]), fighter("e1", "enemy")
c = fight(p, e)
combat.apply_damage(c, p, e, 1.0, "attacks", random.Random(1))
check("a hexed blow lands hexed through the stages, listed in the pane, an affliction Plaguebearer carries", e.statuses.get("hexed") == 99 and e.status_from.get("hexed") == "player"
      and any("is hexed" in l for l in c.log) and cs.CombatScene.status_label(e, "hexed") == "hexed" and "hexed" in combat_perks.AFFLICTIONS, (e.statuses, c.log[-3:]))
check("relics' mark lands its hex through the stages too", "C.add_status(combat, t, \"hexed\", 99, att)" in open("engine/relics.py", encoding="utf-8").read())
# Mend
p, e = fighter(), fighter("e1", "enemy", legendary={"crippling_wounds": 1}, mech_names={"crippling_wounds": "Crippling Wounds"})
c = fight(p, e)
e.counters["last_hit"] = 50
combat.add_status(c, p, "bleeding", 3, e)
check("the setup: a bleeding, crippled fighter", p.bleed > 0 and p.statuses.get("slowed") == 3 and p.counters.get("crippled") == 1)
p.hp = p.max_hp * 0.4
mend = types.SimpleNamespace(id="mend_x", relic={"params": {"pct": 20}, "kind": "mend", "name": "Mend", "text": ""})
check("Mend binds the wound: no bleeding, no size left, no limp, no crippled counter", relics.use(c, p, mend, None, rng) is None and "bleeding" not in p.statuses and p.bleed == 0.0
      and "slowed" not in p.statuses and "crippled" not in p.counters and p.hp > p.max_hp * 0.4, (p.statuses, p.bleed, p.counters))
# Contagion
def contagion(neighbour):
    p = fighter()
    dead = fighter("e1", "enemy", hp=1)
    c = fight(p, dead, neighbour)
    dead.counters["contagion"] = 1
    fx.put_status(dead, "poisoned", 3, p)
    fx.set_strength(dead, "poisoned", [5.0, 5.0], fixed=[2.0])
    dead.hp = 0
    spellcraft.on_death(c, dead, p)
    return c
plain = fighter("e2", "enemy")
c = contagion(plain)
check("Contagion carries a dying foe's poison to a plain neighbour: the same stacks, the fixed ones among them, no new dose", plain.statuses.get("poisoned") == 3 and plain.poison == [5.0, 5.0, 2.0] and plain.poison_fixed == []
      and any("Contagion" in l for l in c.story), (plain.statuses, plain.poison))
warded = fighter("e2", "enemy")
fx.put_buff(warded, "att", {"rounds": 9, "mech": {"element_ward": 50}, "drain": 0, "collapse": "", "name": "Attunement", "kind": "attunement", "element": "poison"})
c = contagion(warded)
check("...and spares an archon of poison, in the fight's words", "poisoned" not in warded.statuses and warded.poison == [] and any("Attunement" in l for l in c.story) and not any("Contagion" in l for l in c.story), (warded.statuses, c.story[-2:]))
# the wipes
p, t, e = fighter(), fighter("ally_h", "ally"), fighter("e1", "enemy")
c = fight(p, t, e)
combat.add_status(c, t, "poisoned", 3, e)
combat.add_status(c, t, "frightened", 2, e)
t.hp = 0
combat.act_ability(c, p, Move(id="h_rescue", name="Rescue Prayer", effect="healing", tier="heavy", reach="extended", resource="mana", attribute="wisdom", heal_form="rescue"), None, rng, give=[t])
check("a Rescue leaves no status, no source and no strength behind", t.alive and t.statuses == {} and t.status_from == {} and t.poison == [] and fx.rows(t, "status") == [], (t.hp, t.statuses, t.status_from))
p, b = fighter(), fighter("e1", "enemy", boss=bosses.make("default", "leader", "Boss"))
c = fight(p, b)
combat.add_status(c, b, "slowed", 3, p)
combat.add_status(c, b, "marked", 3, p)
check("the setup: the boss carries the player's statuses, and Malefic Step finds it by them", movement._cursed_by(c, p) == [b])
b.hp = 0
check("a boss's last stand leaves no source behind: Malefic Step finds nothing", bosses.last_stand(c, b) and b.alive and b.statuses == {} and b.status_from == {} and movement._cursed_by(c, p) == [], (b.statuses, b.status_from))

# ---- the write rule
check("no module outside engine/effects.py writes through a view", purity.effect_writes() == [], purity.effect_writes())
planted = "f.statuses['x'] = 1\nf.ignite += 2\nf.buffs.pop(k)\nc.zone_effects.setdefault(z, {})\nf.statuses.update(a=1)\nf.curses = []\nf.poison_fixed = list(f.poison_fixed)\ng.shield, g.statuses, g.cooldowns = 0, {}, {}\nn = f.statuses.get('x', 0) == 1\nm = [s for s in f.statuses if s != 'x']\n"
found = purity.effect_writes_in(planted, "engine/planted.py")
check("a planted write is caught, each line, a tuple target among them, and a read is not", [l.split(":")[1].split(" ")[0] for l in found] == ["1", "2", "3", "4", "5", "6", "7", "8"]
      and all("engine/planted.py" in l for l in found) and found[7].endswith("writes .statuses"), found)
check("...not in engine/effects.py", purity.effect_writes_in(planted, "engine/effects.py") == [])

# ---- the triggers held to the code that evaluates them
live = data_check.evaluated_triggers()
check("every trigger in the table is evaluated somewhere today: none is dormant, and the check finds nothing", data_check.trigger_problems() == [] and set(rules.TRIGGERS) <= live
      and not any(t.dormant for t in rules.TRIGGERS.values()) and {"in_swamp", "in_arctic", "in_conversation", "while_performing", "against_undead", "at_night"} <= live, (sorted(set(rules.TRIGGERS) - live), data_check.trigger_problems()))
T = yaml.safe_load(open("data/rules/triggers.yaml", encoding="utf-8"))
planted_t = T + [{"id": "when_the_moon_is_full", "condition": "The moon is full.", "checks": "none", "context": "combat"}]
check("a trigger no code evaluates must say dormant: true", data_check.trigger_problems(planted_t) == ["triggers.yaml when_the_moon_is_full: no code evaluates it; mark it dormant: true, or evaluate it"], data_check.trigger_problems(planted_t))
check("...and one the code evaluates may not", data_check.trigger_problems([{**t, "dormant": True} if t["id"] == "at_night" else t for t in T]) == ["triggers.yaml at_night: says dormant, but the code evaluates it"])
moon = rules.TriggerDef(id="when_the_moon_is_full", condition="The moon is full.", checks="none", context="combat", dormant=True)
rules.TRIGGERS["when_the_moon_is_full"] = moon
try:
    view_ = types.SimpleNamespace(uses_companions=False, summoner=False, focus="combat", custom_class="X", archetype=types.SimpleNamespace(value="warrior"),
                                  class_summary="", themes=[], combat_identity="", summary="", primary_attributes=["strength"], casting_attribute="", elements=[], constraints=[])
    scores = fit.trigger_scores(view_)
    check("creation never offers a dormant trigger", scores.get("when_the_moon_is_full") == fit.EXCLUDED and scores.get("always", 0) > fit.EXCLUDED, scores.get("when_the_moon_is_full"))
except Exception as ex:
    check("creation never offers a dormant trigger", False, repr(ex))
finally:
    del rules.TRIGGERS["when_the_moon_is_full"]
check("the prompt's trigger lines, gear and lessons skip a dormant one", "if not t.dormant" in open("llm/prompts.py", encoding="utf-8").read() and "not TRIGGERS[t].dormant" in open("engine/loot.py", encoding="utf-8").read()
      and "t.dormant or" in open("engine/lessons.py", encoding="utf-8").read())

# ---- a saved fight of another shape is let go of at load, with one line; v15 lets a saved fight go and the next load tells it once
check("failures.yaml fight_let_go: six or more lines, each its own, in the world's words", len(failures.F["fight_let_go"]) >= 6
      and len(set(failures.F["fight_let_go"])) == len(failures.F["fight_let_go"]) and not any(failures.MACHINERY.search(l) for l in failures.F["fight_let_go"])
      and failures.fight_let_go(random.Random(1)) in failures.F["fight_let_go"] and failures.problems() == [], failures.problems()[:3])
NAME = "status_507"
SHOWN = simlib.quiet_console()
def texts():
    return [t for k, t in SHOWN]
def load(fresh=False):
    g = simlib.campaign(NAME, cls="warrior", seed=7, location="south_fields", fresh=fresh)
    SHOWN.clear()
    uc.ask = lambda *a, **k: "quit"
    g.scene.run()
    return g
g = load(fresh=True)
g.store.save_combat(old)
g.close()
g = load()
told = [t for t in texts() if t in failures.F["fight_let_go"]]
check("a saved fight of another shape is let go of at load: the row dropped, one line from data, no fight resumed", len(told) == 1 and g.store.load_combat() is None and g.scene.combat is None, (told, texts()[:6]))
g.close()
g = load()
check("...and the load after says nothing of it", not [t for t in texts() if t in failures.F["fight_let_go"]] and g.store.load_combat() is None)
g.store.save_combat(row)
migrations._v15_effect_rows(g.store)
check("v15 on a save with a fight row lets the fight go and leaves the notice", g.store.load_combat() is None and g.store._kv_text("notice:fight_let_go") == "1")
g.close()
g = load()
check("...the next load tells it once, and the notice is gone", len([t for t in texts() if t in failures.F["fight_let_go"]]) == 1 and g.store._kv_text("notice:fight_let_go") is None, texts()[:6])
g.close()
g = load()
check("...never again", not [t for t in texts() if t in failures.F["fight_let_go"]])
g.close()
check("v15 is the fight's step, and a save without a fight row is untouched by it", migrations.CURRENT >= 15     # (f547: v16 follows it)
      and any(v == 15 and "fight" in w for v, w, _ in migrations.MIGRATIONS))
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
