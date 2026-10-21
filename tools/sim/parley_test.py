"""Speaking in a fight: free, one try per enemy, only to those who can listen. Surrender, prisoners, and handing them to the watch."""
import random, sys, shutil
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from scenes import combat_scene as cs
from npc.traits import load_traits
from engine import combat as C, parley, behaviors as B, money
from llm.contracts import CombatIntent, ActionIntent
bad = []
def check(n, ok, x=""):
    print(("PASS " if ok else "FAIL ") + n + (f"  {x}" if x else ""))
    if not ok: bad.append(n)

shutil.rmtree("saves/parley_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("parley_test")
store.meta.seed = 4; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 10
for a in ('charisma', 'strength', 'wisdom', 'dexterity', 'intelligence'):
    setattr(char.attributes, a, 15)
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")

def scene(cids, lvl=10, **hurt):
    me = C.fighter_from_character(ws.player.character)
    foes = [C.fighter_from_creature(world.bestiary[c], lvl, "normal", f"e{i}", name=f"{c} {i + 1}") for i, c in enumerate(cids)]
    fight = C.Combat(fighters=[me] + foes, place="parth")
    from engine import battlefield as _bf
    for f in foes:
        _bf.engage(fight, f, fight.player)
    return cs.CombatScene(ws, fight, cids[0]), fight, foes

# who can be spoken to
for cid, ok in (("bandit", True), ("goblin", True), ("ogre", True), ("young_red_dragon", True), ("wolf", False), ("skeleton", False), ("swarm_of_rats", False), ("gelatinous_cube", False), ("treant", False)):
    sc, f, foes = scene([cid])
    check(f"{cid}: " + ("can be spoken to" if ok else "cannot"), (parley.why_not(foes[0]) is None) == ok, parley.why_not(foes[0]))
sc, f, foes = scene(["bandit"]); foes[0].boss = {"kit": "person"}
check("a boss cannot be argued with", parley.why_not(foes[0]) is not None)

# odds respond to the situation
sc, f, (b,) = scene(["bandit"])
c = ws.player.character
fresh_odds = parley.odds(c, f, b, "intimidate")[0]
b.hp = b.max_hp * 0.4
hurt_odds = parley.odds(c, f, b, "intimidate")[0]
b.hp = b.max_hp * 0.2
bad_odds = parley.odds(c, f, b, "intimidate")[0]
check("a hurt foe is easier to frighten, a badly hurt one more so", fresh_odds < hurt_odds < bad_odds, (fresh_odds, hurt_odds, bad_odds))
sc, f, bs = scene(["bandit", "bandit", "bandit"])
check("being outnumbered costs points", parley.odds(c, f, bs[0], "persuade")[0] < parley.odds(c, scene(["bandit"])[1], scene(["bandit"])[2][0], "persuade")[0])
sc, f, (hi,) = scene(["bandit"], lvl=25)
check("a foe far above your level is hard to move", parley.odds(c, f, hi, "persuade")[0] < parley.odds(c, scene(["bandit"])[1], scene(["bandit"])[2][0], "persuade")[0])
sc, f, (el,) = scene(["bandit"]); el.rank = "elite"
sc2, f2, (pl,) = scene(["bandit"])
check("elites cost points", parley.odds(c, f, el, "persuade")[0] < parley.odds(c, f2, pl, "persuade")[0])
sc, f, (zl,) = scene(["cultist"])
parley.attempt(f, zl, "intimidate", c, random.Random(1))
check("...it fails and shuts the door", zl.talked and not zl.fled and any("no fear" in s for s in f.story), f.story)

# outcomes over many tries
def run(approach, hp_share=0.2, cids=("bandit",), n=300, lvl=10):
    res = {"yield": 0, "fled": 0, "stunned": 0, "none": 0}
    for s in range(n):
        sc, f, foes = scene(list(cids), lvl)
        t = foes[0]; t.hp = t.max_hp * hp_share
        parley.attempt(f, t, approach, c, random.Random(s))
        if t.surrendered: res["yield"] += 1
        elif t.fled: res["fled"] += 1
        elif "stunned" in t.statuses: res["stunned"] += 1
        else: res["none"] += 1
        check_once = t.talked
        assert check_once
    return res
r = run("intimidate"); check("intimidation makes a hurt bandit yield", r["yield"] > 100 and r["fled"] == 0, r)
r = run("persuade"); check("persuasion makes a foe stand down and leave, and nobody yields", r["fled"] > 50 and r["yield"] == 0, r)
r = run("deceive"); check("a lie makes it hesitate and nothing else", r["stunned"] > 50 and r["fled"] == 0 and r["yield"] == 0, r)
r = run("intimidate", 0.2, ("ogre",), lvl=10); check("an ogre made to give way bolts instead of yielding", r["fled"] > 20 and r["yield"] == 0, r)
r = run("intimidate", 1.0); print("   unhurt bandit, intimidate:", r)

# one try
sc, f, (b,) = scene(["bandit"]); b.hp = b.max_hp * 0.1
parley.attempt(f, b, "persuade", c, random.Random(1))
again = parley.attempt(f, b, "persuade", c, random.Random(2))
check("a second try is refused, whatever happened the first time", again is not None and "already" in again, again)

# it is a free action
sc, f, foes = scene(["bandit", "bandit"])
rd, mv = f.round, [t.hp for t in foes]
foes[0].hp = foes[0].max_hp * 0.1
sc.talk(CombatIntent(kind="talk", approach="intimidate", target=foes[0].id), foes[0], "Drop it or die")
check("talking does not use the round or let anyone strike", f.round == rd and f.player.hp == f.player.max_hp, (f.round, rd))
check("...and the fight goes on unless every foe broke", bool(f.over) == (not f.enemies()), (f.over, len(f.enemies())))
sc, f, foes = scene(["wolf"])
sc.talk(CombatIntent(kind="talk", approach="persuade", target=foes[0].id), foes[0], "Easy, easy")
check("words to a wolf change nothing and cost nothing", f.round == 1 and not foes[0].fled and not foes[0].talked)

# everyone yields -> victory and prisoners
sc, f, foes = scene(["bandit"]); foes[0].hp = foes[0].max_hp * 0.05
for s in range(40):
    foes[0].talked = False; foes[0].fled = False; foes[0].surrendered = False
    parley.attempt(f, foes[0], "intimidate", c, random.Random(s))
    if foes[0].surrendered: break
check("a bandit can be made to yield", foes[0].surrendered and foes[0].fled)
sc.fight.over = "victory"
ws.player.prisoners = {}
xp0 = ws.player.character.xp if hasattr(ws.player.character, "xp") else 0
sc.victory()
check("a yielded person becomes a prisoner you escort", len(ws.player.prisoners) == 1 and next(iter(ws.player.prisoners.values())).get("escort"), ws.player.prisoners)
pid = next(iter(ws.player.prisoners))
check("...and the random prisoner roll is skipped", getattr(ws, "surrender_took", False))
check("the prisoner is here", any(n.id == pid for n in ws.present))

# moving takes the prisoner along
ws.enter("parth")
dest = next(p for p in world.places if p != "parth" and world.places[p].type in ("town", "city", "village"))
ws.enter(dest)
check("an escorted prisoner follows you to the next place", store.load_npc(pid).location == dest and any(n.id == pid for n in ws.present), store.load_npc(pid).location)
ws.advance(60 * 24 * 5)
check("an escorted prisoner does not slip away", pid in ws.player.prisoners)

# hand over: needs the watch
ws.present = [n for n in ws.present if n.role not in ("guard", "watch_captain", "royal_guard")]
c0 = ws.player.character.coins
ws.on_hand_over(ActionIntent(kind="hand_over", target=pid), "I hand him over")
check("without a guard here, nothing is handed over", pid in ws.player.prisoners and ws.player.character.coins == c0)
from npc.models import NPC
guard = NPC(id="g1", name="Captain Marr", people="human", role="watch_captain", location=dest, description="grim")
store.save_npc(guard); ws.residents = ws.residents + [guard]; ws.refresh_present()
sl = ws.player.prisoners[pid].get("level", 1)
ws.on_hand_over(ActionIntent(kind="hand_over", target=pid), "I hand him over")
check("with a guard present the prisoner is taken and you are paid", pid not in ws.player.prisoners and ws.player.character.coins == c0 + sl * 12, (ws.player.character.coins - c0, sl * 12))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS []")
sys.exit(1 if bad else 0)
