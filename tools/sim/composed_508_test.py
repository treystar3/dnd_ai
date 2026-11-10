"""(f508) The composed Fighter: nine parts (identity, stats, resources, position, carried, kit, turn, behaviour, summon), each holding
its own fields and refusing any other; every flat name of the old Fighter is declared by exactly one part and reads and writes through a
property to it (never a second copy); a fighter is built flat as every builder and test does, or nested as the row is, and a flat f507 row
folds into the parts; the dump is nested; a row with a key no part declares is refused and resume lets the fight go with its reason. The
fight holds several player fighters in shape (decision 9): players names them, player is the first, a round runs with enemies striking
either, and the service's sync writes each one's character. The Character <-> Fighter paths are the service's alone: a spy on the
character during a scripted round sees health, stamina, mana, spell_days and orenna_breath written only from FightService.sync; the
party's record after a fight (a hire's wounds and mana, the fallen's fates, the companions, the bound summon) is written by
FightService.end alone, the scene telling its notes. The fixture tool times the odds when run by hand. Nothing stays in the process."""
import inspect
import json
import os
import random
import shutil
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from core.models import Character
from engine import battlefield_builder as bb, combat, effects as fx, party as party_rules
from scenes import combat_scene as cs
from services.fight import FightService, FightSpec, RoundIntent
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

console.combat_state = lambda data: False
console.combat_panel = lambda lines: None

# ---- the parts and the flat names
FLAT_NAMES = """id name side level flaw flaw_used size category creature spawn rank attrs hp max_hp stamina max_stamina mana max_mana
weapon_name weapon_damage weapon_attrs reach damage_type element hit_element armor ward evasion_penalty zone_id row position_tags
engaged_with hold pace winding covering starts_far defending effects cooldowns moves bonuses move_round kill_round attacked_since_turn
temperament armor_pierce crit_resist offhand_spell spell_mult spell_share adaptive legendary slays ally_role mech_names can_heal order
order_target story_id always_miss spell_parts spell_kind weary tether summon_form summon_owner summon_of summon_until summon_tier
summon_cast wards hardening_stacks windwalker_ready deathward_used breath yields_at yield_text bound second_wind_used conditional shield
fled first_blood_used relentless aegis_round archmage_used spells_cast counters relic_uses boss family behaviors surrendered talked
recent_casts last_mobility shadow last_hurt_by charging casting sundered counter_move corroded armor_weight wears_metal attuned""".split()
declared = {n: [p for p, cls in combat.PARTS.items() if n in cls.model_fields] for n in FLAT_NAMES}
check("every flat field name of the old Fighter (107) is declared by exactly one of nine parts, and the parts declare nothing else",
      len(FLAT_NAMES) == 107 and all(len(v) == 1 for v in declared.values()) and set(combat.FLAT) == set(FLAT_NAMES) and len(combat.PARTS) == 9
      and set(combat.PARTS) == {"identity", "stats", "resources", "position", "carried", "kit", "turn", "behaviour", "summon"}, [n for n, v in declared.items() if len(v) != 1])
check("every part refuses a key it does not declare", all(cls.model_config.get("extra") == "forbid" for cls in combat.PARTS.values()) and combat.Fighter.model_config.get("extra") == "forbid")

def fighter(fid="player", side="player", hp=100, **kw):
    return combat.Fighter(id=fid, name=fid, side=side, level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=hp, max_hp=hp, stamina=50,
                          max_stamina=50, mana=40, max_mana=40, weapon_damage=12, hold=2, **kw)
f = fighter(legendary={"hex": 1}, zone_id="a")
dump = f.model_dump()
check("a fighter builds flat and dumps nested: the nine parts and no flat key", list(dump) == list(combat.PARTS) and "hp" not in dump and dump["resources"]["hp"] == 100.0
      and dump["kit"]["legendary"] == {"hex": 1} and dump["position"]["zone_id"] == "a", list(dump))
f.hp = 42
f.counters["x"] = 1
fx.put_status(f, "slowed", 2)
check("a flat name reads and writes on its part: never a second copy", f.resources.hp == 42 and f.hp == 42 and f.turn.counters is f.counters and f.carried.effects is f.effects
      and f.statuses == {"slowed": 2} and f.identity.id == f.id, (f.resources.hp, f.hp))
f.resources.hp = 7
check("...and the part written is what the flat name reads", f.hp == 7)
back = combat.Fighter(**dump)
flat = {k: v for part in f.model_dump(mode="json").values() for k, v in part.items()}
folded = combat.Fighter(**flat)
check("a nested row loads; a flat f507 row folds into the parts and dumps nested, equal to the fighter it came from",
      back.hp == 100 and folded == f and folded.model_dump() == f.model_dump() and folded.statuses == {"slowed": 2}, (folded.hp, f.hp))
mixed = combat.Fighter(identity=f.identity, stats=f.stats.model_dump(), resources={"hp": 1, "max_hp": 1}, hp=3)
check("a part given whole and a flat key of it: the flat key lays over", mixed.hp == 3 and mixed.max_hp == 1 and mixed.id == "player")
c = f.model_copy(deep=True)
c.hp = 1
check("a deep copy is its own: the parts are copied", f.hp == 7 and c.hp == 1 and c.effects is not f.effects and c.statuses == f.statuses)
try:
    combat.Fighter(id="x", name="x", side="enemy", level=1, attrs={}, hp=1, max_hp=1, band="near")
    check("a key no part declares is refused", False)
except Exception as ex:
    check("a key no part declares is refused, by name", type(ex).__name__ == "ValidationError" and "band" in str(ex))
rowd = json.loads(combat.Combat(fighters=[fighter(), fighter("e1", "enemy")]).model_dump_json())
good = json.dumps({"fight": rowd, "creature": "wolf"})
rowd["fighters"][0]["turn"]["bogus"] = 1
badrow = json.dumps({"fight": rowd, "creature": "wolf"})
check("resume reads a nested row, and lets a row with a stray key go with its reason", FightService.resume(good)[0] is not None and FightService.resume(badrow)[0] is None
      and "ValidationError" in FightService.resume(badrow)[2] and "bogus" in FightService.resume(badrow)[2], FightService.resume(badrow)[2][:120])
src = open("engine/combat.py", encoding="utf-8").read()
check("the fight's own rows (the marks, the ground) and its players are on the fight, not a fighter", "players: list[str] = []" in src and "def player_fighters(self)" in src)

# ---- several player fighters in shape: the fight names them, the first is the player, a round strikes either, sync writes each
NAME = "composed_508"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws = game.scene
ws.enter("south_fields")
c1 = ws.player.character
c2, _ = simlib.make_character("mage", random.Random(5))
c2.id, c2.name = "p2", "Second"
svc = cs.service_of(ws, random.Random(11))
svc.characters = [c1, c2]
creature = ws.world.bestiary["wolf"]
foes = [combat.fighter_from_creature(creature, 1, "normal", f"e{i}", f"wolf {i}", "near") for i in (1, 2)]
for e in foes:
    e.behaviors["fearless"] = 1
fight, opening = svc.begin(FightSpec(creature=creature, enemies=foes, battlefield=bb.duel_ground(), place="the test ground"))
check("a fight with two characters holds two player fighters: players names them, player is the first, each bears its character's id",
      fight.players == ["player", "p2"] and fight.player.id == "player" and [f.id for f in fight.player_fighters()] == ["player", "p2"]
      and [c.id for c, _ in svc.cast(fight)] == ["player", "p2"] and fight.get("p2").name == "Second" and fight.get("p2").side == "player", (fight.players, [f.id for f in fight.fighters]))
struck = set()
for _ in range(8):
    if fight.over:
        break
    out = svc.round(fight, RoundIntent(kind="attack", target="e1", words="I strike"))
    struck |= {h["dfn"] for h in fight.hits if h.get("dfn") in ("you", "Second", fight.player.name)}
    struck |= {h["dfn"] for h in fight.hits if h.get("dfn") == "Second"}
hurt = [f.id for f in fight.player_fighters() if f.hp < f.max_hp]
check("a round runs with enemies striking either player fighter", fight.round > 1 and ("Second" in struck or "p2" in hurt) and ("player" in hurt or fight.player.name in struck or any(h.get("dfn") in ("you", fight.player.name) for h in fight.hits)), (struck, hurt, [(h.get("att"), h.get("dfn")) for h in fight.hits][:6]))
p2 = fight.get("p2")
p2.hp = 13.0
svc.sync(fight)
check("sync writes every player fighter's character: the second's bars are its own fighter's", c2.health == 13.0 and c1.health == float(fight.player.hp) and c2.mana == float(p2.mana), (c2.health, c1.health))
game.store.save_combat(None)
game.close()

# ---- the write paths: a spy on the character during a scripted round through the scene
WRITES = []
_orig = Character.__setattr__
def spy(self, name, value):
    if name in ("health", "stamina", "mana", "spell_days", "orenna_breath"):
        fr = inspect.currentframe().f_back
        WRITES.append((name, fr.f_code.co_name, os.path.basename(fr.f_code.co_filename)))
    return _orig(self, name, value)
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")
creature = ws.world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "wolf", "near")
foe.behaviors["fearless"] = 1
foe.hp = foe.max_hp = 60
ws.wildlife = (creature, [foe])
stub.plan = [{"kind": "attack", "target": "wolf"}]
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
Character.__setattr__ = spy
try:
    ws.turn("I attack the wolf.")
    for _ in range(3):
        if ws.combat is None:
            break
        ws.turn("I strike again.")
finally:
    Character.__setattr__ = _orig
    stub.plan = None
writers = {(fn, file) for _, fn, file in WRITES}
check("during the rounds the character's bars, spell days and blessing are written from FightService.sync alone", WRITES and writers == {("sync", "fight.py")}, (writers, WRITES[:4]))
game.close()

# ---- the party's record after a fight: written by the service's end alone, the scene telling
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws = game.scene
ws.enter("south_fields")
offer = {"id": "1-0", "name": "Test Hire", "role": "fighter", "level": 5, "rank": "F", "blurb": "x", "temper": ["blunt"], "motive": "coin", "line": "x"}
m = party_rules.new_hire(offer, 10, 3)
ws.player.party = [m]
hire = party_rules.fighter(m, minutes=ws.minutes)
hire.hp = hire.max_hp * 0.5
fight = combat.Combat(fighters=[combat.fighter_from_character(ws.player.character), hire, combat.fighter_from_creature(creature, 1, "normal", "e1", "wolf", "near")],
                      place="the test ground")
after = cs.service_of(ws).end(fight, [], True, False)
check("end writes a hire's wounds and the fights counted, and returns who came through", abs(m["hp_frac"] - 0.5) < 0.01 and m["hp_at"] == ws.minutes and m.get("fights_total") == 1
      and [x["id"] for x, _ in after.seen] == [m["id"]] and not after.any_down and ws.player.party_last_fight["won"] is True, (m.get("hp_frac"), after.seen))
caster = party_rules.new_hire({**offer, "id": "1-1", "name": "Caster", "role": "priest"}, 10, 3)
ws.player.party = [m, caster]
cf = party_rules.fighter(caster, minutes=ws.minutes)
if cf.max_mana:
    cf.mana = cf.max_mana * 0.25
fight2 = combat.Combat(fighters=[combat.fighter_from_character(ws.player.character), hire, cf, combat.fighter_from_creature(creature, 1, "normal", "e1", "wolf", "near")], place="x")
cs.service_of(ws).end(fight2, [], False, False)
check("...and a casting hire's mana", (not cf.max_mana) or (abs(caster["mana_frac"] - 0.25) < 0.01 and caster["mana_at"] == ws.minutes), caster.get("mana_frac"))
down = party_rules.fighter(m, minutes=ws.minutes)
down.hp = 0
n0 = len(ws.player.party)
after = cs.service_of(ws, random.Random(1)).end(fight, [down], True, False)
check("a hire who went down is decided by end (carried out, or buried) and told", after.any_down and any("carried out" in n or "has fallen" in n for n in after.notes)
      and (len(ws.player.party) < n0 or ws.player.party[0].get("hp_frac") == 0.05), (after.notes, len(ws.player.party)))
scene_src = open("scenes/party_actions.py", encoding="utf-8").read()
svc_src = open("services/fight.py", encoding="utf-8").read()
check("the scene no longer writes the hires' wounds, mana or fates; the service's end does, and companions_after runs inside it",
      "mana_frac" not in scene_src and "decide_down" not in scene_src and "mana_frac" in svc_src and "def end(self, fight" in svc_src
      and svc_src.index("self.companions_after(fight") > svc_src.index("def end(self, fight") and "party_after_fight(fallen, f.fighters" in open("scenes/combat_scene.py", encoding="utf-8").read())
check("the fixture tool times the odds when run by hand", "--time" in open("tools/sim/fight_fixtures.py", encoding="utf-8").read() and "TIMES" in open("tools/sim/fight_fixtures.py", encoding="utf-8").read())
game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
