"""Starting a fight (f248): buffs named as you strike go up first; a fighting ability named at something hostile opens the fight;
stealth decides surprise; an unaware target takes double damage (1.5x from an area attack); a boss is never caught unaware."""
import random
import sys
sys.path.insert(0, ".")
sys.argv = ["x", "mage", "2", "1", "1", "1"]
_out = sys.stdout
import simbot
from engine import combat, loadout
from engine.combat import Move
from core.models import Ability
from llm.contracts import ActionIntent
from ui import console
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""), file=_out)
    if not ok: bad.append(n)
notes = []
_o = console.note
console.note = lambda t, *a, **k: (notes.append(t), _o(t, *a, **k))[1]

# ---- the numbers
check("an unaware target takes double", combat.RULES["unaware_damage"] == 2.0)
check("...and one and a half from an area attack", combat.RULES["unaware_area_damage"] == 1.5)

def fighter(fid="player", side="player", **kw):
    return combat.Fighter(id=fid, name=fid, side=side, level=5, attrs={a: 12 for a in combat.ATTRIBUTES}, hp=10**6, max_hp=10**6,
                          stamina=10**4, max_stamina=10**4, mana=10**4, max_mana=10**4, weapon_damage=12, weapon_attrs=["strength"], hold=2, **kw)

def unaware_step(move):
    p, e = fighter(), fighter("e", "enemy")
    f = combat.Combat(fighters=[p, e], record=True)
    e.statuses["unaware"] = 1
    for i in range(40):
        f.hits = []
        combat.act_ability(f, p, move, e, random.Random(i))
        p.cooldowns.clear()
        for h in f.hits:
            for label, factor in h.get("steps", []):
                if label == "Unaware target":
                    return factor
    return None
bolt = Move(id="m_bolt", name="Bolt", effect="damage", tier="moderate", reach="ranged", resource="mana", spell_form="bolt")
blast = Move(id="m_blast", name="Blast", effect="damage", tier="moderate", reach="area", resource="mana", spell_form="blast")
check("a single-target spell on an unaware target: x2", unaware_step(bolt) == 2.0, unaware_step(bolt))
check("an area spell on an unaware target: x1.5", unaware_step(blast) == 1.5, unaware_step(blast))

# ---- bosses are never caught
p, e, b = fighter(), fighter("e", "enemy"), fighter("b", "enemy", rank="boss")
f = combat.Combat(fighters=[p, e, b])
caught = combat.surprise(f)
check("surprise catches the ordinary foe, not the boss", [x.id for x in caught] == ["e"] and "unaware" not in b.statuses)
b.statuses["unaware"] = 1
combat.opening(f, random.Random(1))
check("a boss marked unaware by any other road is put back on guard as the fight opens", "unaware" not in b.statuses and "unaware" in e.statuses)

# ---- in the world
bot = simbot.Bot(); ws = bot.ws; c = ws.player.character
cr = next(x for x in ws.world.bestiary.values() if x.levels[0] <= 1 and not x.unique)
def foe():
    e = combat.fighter_from_creature(cr, 1, "normal", "e1", cr.name, "near")
    e.hp = e.max_hp = 10**6                       # it lives through the opening blow, so the fight can be looked at
    return [e]
strike = next(a for a in loadout.prepared(c) if a.context.value == "combat" and a.effect.value == "damage")
ward = Ability(id="t_precision", name="Keen Sight", description="x", effect="buff", tier="light", reach="self", resource="mana",
               context="combat", cost=0, cooldown=0, buff="precision")
c.actives.append(ward)
c.prebuffs = []
loadout.prepared(c)
if ward.id not in c.prepared:
    c.prepared.append(ward.id)

def start(text, intent, sneaking=False, roll="success"):
    ws.combat = None
    ws.wildlife = (cr, foe())
    ws.sneaking, ws.queued_buffs, ws.fight_text, ws.halted = sneaking, [], text, False
    ws.resolve = lambda *a, **k: roll
    c.mana = 10**5
    getattr(ws, f"on_{intent.kind}")(intent, text)
    return ws.combat

sc = start("I cast Keen Sight and attack the beast", ActionIntent(kind="attack"))
check("a buff named as you attack goes up before the first blow", sc and "t_precision" in sc.fight.player.buffs, sc and sc.fight.player.buffs)
check("...and the fight has not yet had a blow (you strike next)", sc and sc.fight.round <= 1)

sc = start("Keen Sight", ActionIntent(kind="ability", ability="t_precision"))
check("a buff named alone with something hostile near is readied, not refused", ws.combat is None and not ws.halted and ws.queued_buffs == ["t_precision"], (ws.halted, ws.queued_buffs))
ws.on_attack(ActionIntent(kind="attack"), "Keen Sight")
check("...and goes up when the fight starts that turn", ws.combat and "t_precision" in ws.combat.fight.player.buffs)

sc = start(f"I sneak up and use {strike.name}", ActionIntent(kind="ability", ability=strike.id), sneaking=True, roll="success")
e = sc.fight.enemies()[0] if sc and sc.fight.enemies() else None
check("a fighting ability named at something hostile starts the fight", sc is not None)
check("...and is the opening action", sc and sc.fight.player_acted, sc and sc.fight.log)
check("...an unaware target took it at double", sc and any(st == ["Unaware target", 2.0] for h in sc.fight.hits for st in h.get("steps", [])),
      sc and [h.get("steps") for h in sc.fight.hits])
check("a successful stealth check: the enemy lost its first turn and is unaware no longer", e is not None and "unaware" not in e.statuses
      and any("caught unaware" in l for l in sc.fight.log), sc and sc.fight.log)

sc = start("I creep up and attack", ActionIntent(kind="attack"), sneaking=True, roll="failure")
check("a failed stealth check: no one is unaware", sc and not any("unaware" in x.statuses for x in sc.fight.enemies()))
sc = start("I creep up and attack", ActionIntent(kind="attack"), sneaking=True, roll="success")
check("a successful one: they are", sc and all("unaware" in x.statuses for x in sc.fight.enemies()))
sc = start("I attack", ActionIntent(kind="attack"))
check("no stealth, no surprise", sc and not any("unaware" in x.statuses for x in sc.fight.enemies()))

ws.combat, ws.wildlife = None, None
notes.clear(); ws.halted = False
ws.on_ability(ActionIntent(kind="ability", ability=strike.id), strike.name)
check("with nothing hostile near, a fighting ability is still refused", ws.halted and any("save it for a fight" in n for n in notes), notes)

print("FAILED" if bad else "ALL PASS", bad, file=_out)
sys.exit(1 if bad else 0)
