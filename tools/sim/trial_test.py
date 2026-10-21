"""The trial of rank: qualifying is not enough, you win the rank in a duel nobody can die in; and the pane's item buttons."""
import sys, random
sys.path.insert(0, ".")
sys.argv = ["x", "warrior", "2", "1", "1", "1"]
_out = sys.stdout
import simbot
from engine import combat, inventory, quests
from ui import console
from scenes.combat_scene import CombatScene
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""), file=_out)
    if not ok: bad.append(n)
notes = []
_o = console.note
console.note = lambda t, *a, **k: (notes.append(t), _o(t, *a, **k))[1]

b = simbot.Bot(); ws = b.ws; c = ws.player.character
c.level = 10; c.coins = 50000
ws.player.guild_rank = "F"; ws.player.guild_done = {"F": 5}
ws.store.meta.minutes = 1440 * 30 + 600
ws.enter("guild_house")

ws.promote_if_due()
check("meeting the numbers does not promote you", ws.player.guild_rank == "F" and ws.trial_due() == "E")
check("it tells you to take the trial", any("trial" in n for n in notes), notes[-2:])
ws.player.guild_done = {"F": 1}
notes.clear(); ws.handle("I'd like to take the trial")
check("without the numbers you are told what is missing and nothing starts", not ws.combat and any("not ready" in n for n in notes), notes)
ws.player.guild_done = {"F": 5}

ws.player.party = [{"id": "1-0", "name": "Tag Along", "role": "fighter", "level": 8, "rank": "F", "blurb": "x", "permanent": True, "base_level": 8, "hired_at": 10, "bond": 20}]
inventory.add(c.inventory, inventory.make_good("healing_draught", 2), 40)
notes.clear(); ws.handle("I'd like to take the trial")
f = ws.combat.fight if ws.combat else None
check("asking at the hall starts a duel", bool(ws.combat) and f.duel and f.no_rewards)
check("only you and the examiner are in it", sorted(x.side for x in f.fighters) == ["enemy", "player"], [x.name for x in f.fighters])
data = ws.combat.pane_data()
check("the pane shows the potions as not allowed here", data["items"] and not data["items"][0]["ready"] and "trial" in data["items"][0]["reason"], data["items"])
n0 = len(c.inventory)
notes.clear(); ws.command("#useitem healing draught")
check("an item cannot be used in a trial", any("No potions" in n for n in notes) and inventory.find(c.inventory, "healing draught") is not None, notes)

pre = dict(ws.player.trial["pools"])
ex = f.enemies()[0]
check("the examiner is a person of about the rank's bar", ex.level >= 10, ex.level)
rng = random.Random(1)
deaths0 = c.deaths
p = f.player
p.hp = 5
combat.take_damage(f, p, 500, ex, rng)
check("a blow that would kill you leaves you on 1 and loses the duel", p.hp == 1 and f.over == "defeat", (p.hp, f.over))
ws.combat.finish()
check("losing the trial keeps your rank, kills nobody and costs no death", ws.player.guild_rank == "F" and c.deaths == deaths0 and ws.combat is None)
check("your strength is as you walked in", all(abs(getattr(c, k) - v) < 1e-6 for k, v in pre.items()), pre)
check("you must wait before standing again", ws.player.trial.get("wait_until", 0) > ws.minutes)
notes.clear(); ws.handle("I'd like to take the trial")
check("and the hall refuses you until then", not ws.combat and any("Come back in" in n for n in notes), notes)
check("your hired party was untouched", len(ws.player.party) == 1 and ws.player.party[0]["bond"] == 20)

ws.store.meta.minutes += 1440 * 4
notes.clear(); ws.handle("I'd like to take the trial")
check("after the wait you may try again", bool(ws.combat))
f = ws.combat.fight
ex = f.enemies()[0]
ex.hp = 3
combat.take_damage(f, ex, 500, f.player, rng)
check("a blow that would kill the examiner leaves them on 1 and wins the duel", ex.hp == 1 and f.over == "victory" and ex.alive, (ex.hp, f.over))
ws.combat.finish()
check("winning promotes you and gives the badge", ws.player.guild_rank == "E" and any("rank E" in k.name for k in c.key_items), ws.player.guild_rank)
check("nothing was looted and no one died", c.deaths == deaths0 and ws.combat is None)

ws.player.trial = {}
b2 = simbot.Bot(); w2 = b2.ws; c2 = w2.player.character
c2.level = 10; w2.player.guild_rank = "F"; w2.player.guild_done = {"F": 5}
w2.store.meta.minutes = 1440 * 30 + 600
w2.enter("guild_house")
w2.handle("I'd like to take the trial")
f2 = w2.combat.fight
e2 = f2.enemies()[0]
f2.player.statuses["poisoned"] = 5          # (f234) an open wound no longer ticks; poison does
f2.player.hp = 2
for _ in range(3):
    combat.start_turn(f2.player, f2)
check("poison cannot kill you in a duel; it decides it", f2.player.hp == 1 and f2.over == "defeat", (f2.player.hp, f2.over))

b3 = simbot.Bot(); w3 = b3.ws; c3 = w3.player.character
w3.enter("guild_house")
inventory.add(c3.inventory, inventory.make_good("healing_draught", 2), 40)
c3.health = c3.health * 0.5
from world.loader import load_world
cr = next(x for x in w3.world.bestiary.values() if x.levels[0] <= 1 and not x.unique)
foe = combat.fighter_from_creature(cr, 1, "normal", "e1", cr.name, "far")
w3.combat = CombatScene.begin(w3, cr, [foe], "You meet")
d3 = w3.combat.pane_data()
check("in an ordinary fight the pane lists usable items", d3["items"] and d3["items"][0]["ready"] and d3["items"][0]["name"] == "healing draught", d3["items"])
hp0 = w3.combat.fight.player.hp
w3.command("#useitem healing draught")
check("the Use button heals you", w3.combat.fight.player.hp > hp0, (hp0, w3.combat.fight.player.hp))
check("and only one item a turn", not w3.combat.pane_data()["items"][0]["ready"])
w3.command("#useitem healing draught")
check("a second one the same turn is refused", inventory.find(c3.inventory, "healing draught").quantity == 1)

import tools.tune_trial as TT
rates = TT.trial_rates(runs=60)
check("the examiners are beaten roughly two times in three at every rank", all(0.5 <= w <= 0.92 for _, _, w, _ in rates), [(l, round(w, 2)) for l, _, w, _ in rates])
print("FAILED" if bad else "ALL PASS", bad, file=_out)
sys.exit(1 if bad else 0)
