"""(f750) The passage after a fight is told only of the player's own who died in that fight (scenes1-7). Its request listed every hire
in the registry who had died in the last half hour of the clock: a hire killed in one dungeon chamber was named again, among the
player's own "who died in this fight", when the next chamber was won twelve minutes later with nobody falling, and the narrator was
told not to pass over the death; it was told a second time, in a fight they were not in. The list is now the fight's own record:
the hires its end buried or killed (services/fight.py end), named from their registry rows, with who struck the blow.
The case that found it: two dungeon chambers won one after the other, the first with a death. Second cases of the kind: a hire
who died outside any fight five minutes before a fight won; a hire killed in a fight the player fled, then a fight won at once.
Controls: the fight that kills names its dead with who struck them; two who die in one fight (one decided dead as they fell, one
old-style hireling killed at the end) are both named; a hire carried out alive is not. Held in a saves folder of its own."""
import random
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, ".")
import simlib

stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import ui.console as uc

for fn in ("narrate", "say", "npc_says", "dialogue", "ledger", "note"):
    uc.put(fn, lambda *a, **k: None)
from engine import combat, entities, quirks
from engine import party as party_rules
from llm.contracts import ActionIntent
from scenes import combat_scene as cs
from storage import campaign as cmod

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NAME = Path(__file__).stem
HEAD = "THE PLAYER'S OWN WHO DIED IN THIS FIGHT"
ASKED = []
real_fresh = cs.fresh


def spy(task, system, request, *a, **k):
    ASKED.append((task, request))
    return real_fresh(task, system, request, *a, **k)


cs.fresh = spy


def hire(i, name, role, pronoun, permanent=True):
    m = {"id": f"h{i}", "name": name, "role": role, "level": 20, "permanent": permanent, "rank": "F", "bond": 12, "pronoun": pronoun,
         "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "a sellsword", "temper": ["blunt"], "motive": "coin",
         "line": "will not take from the poor"}
    quirks.roll(m, random.Random(i))
    return m


def strike_down(sc, name, dies=None):
    """A foe of this fight strikes the ally down; for a hire, the dice that decide their fate say dead (dies True) or carried out."""
    f = sc.fight
    ally = next(a for a in f.fighters if a.side == "ally" and a.name == name)
    foe = next(e for e in f.fighters if e.side == "enemy")
    ally.hp = 1
    for i in range(200):
        combat.apply_damage(f, foe, ally, 1.0, "bites", random.Random(i))
        if not ally.alive:
            break
    if dies is not None:
        was = party_rules.P["death_when_down"]
        party_rules.P["death_when_down"] = 1.0 if dies else 0.0
        sc.hires_down()
        party_rules.P["death_when_down"] = was
    return f.felled_by.get(ally.id, "")


def end(sc, how="victory"):
    """The fight's real end (CombatScene.finish): won, every foe down; or fled. The passage's line of the player's own dead, or None."""
    f = sc.fight
    if how == "victory":
        for e in f.fighters:
            if e.side == "enemy":
                e.hp = 0
    f.over = how
    ASKED.clear()
    sc.finish()
    after = [r for t, r in ASKED if t == "combat_aftermath"]
    return after, next((ln for ln in (after[-1].split("\n") if after else []) if HEAD in ln), None)


def wolf_fight():
    creature = world.bestiary["wolf"]
    sc = cs.CombatScene.begin(ws, creature, [combat.fighter_from_creature(creature, 3, "normal", "e1", name="wolf 1")], "It is on you:")
    ws.combat = sc
    return sc


def named(e, by=""):
    """How the request names one of the player's dead: as the kept session holds it (stub_fight: "Bodnock Whoof (he, gnome; killed
    by Marrow Hask)")."""
    return f"{e.name} ({e.pronoun}, {entities.people_word(world, e.people)}" + (f"; killed by {by}" if by else "") + ")"


BASE = Path(tempfile.mkdtemp(prefix="aftermath_dead_"))
cmod.SAVES_DIR = BASE                                        # nothing here can reach the real saves/
game = simlib.campaign(NAME, seed=4, minutes=600, turn=0, location="parth", char_seed=2)
store, world = game.store, game.world
game.player.character.level = 30
store.save_player(game.player)
ws = game.scene
ws.enter("parth")
ws.player.party = [hire(1, "Odly Garth", "fighter", "she"), hire(2, "Thavin Liar", "mage", "he")]
ws.player.party_mode = "with"
ws.ensure_dungeons()

# ---- the case that found it: a hire dies in one dungeon chamber; the next chamber is won some minutes later with nobody falling
found = None
for d in store.load_dungeons():
    if d.get("fixed"):
        continue
    for fi, fl in enumerate(d["floors"]):
        ch = fl["chambers"]
        for ci in range(len(ch) - 1):
            if ch[ci]["kind"] == "fight" and ch[ci + 1]["kind"] == "fight" and not ch[ci].get("boss") and not ch[ci + 1].get("boss"):
                found = found or (d, fi, ci)
check("(a dungeon of this seed has two fight chambers in a row)", found is not None)
d, fi, ci = found
d["cleared"] = [fi, ci - 1] if ci > 0 else ([fi - 1, len(d["floors"][fi - 1]["chambers"]) - 1] if fi > 0 else [-1, -1])
ws.save_dungeon(d)
ws.player.location = d["entrance"]
store.save_player(ws.player)
ws.enter(d["entrance"])

ws.on_delve(ActionIntent(kind="delve"), "I go down.")
sc = ws.combat
by = strike_down(sc, "Thavin Liar", dies=True)
after, line = end(sc)
thavin = store.load_entity("hire:h2")
check("(the first chamber's fight kills Thavin, struck down by a foe of it)", thavin is not None and thavin.state == "dead" and by
      and all(m["name"] != "Thavin Liar" for m in ws.player.party), (thavin, by))
check("the fight that kills a hire names them among the player's own who died in it, with who struck the blow, in the kept words",
      line is not None and line.endswith(": " + named(thavin, by)), line)
died_at = thavin.since

ws.on_delve(ActionIntent(kind="delve"), "I go on.")
sc = ws.combat
check("(the next chamber's fight begins with Odly alone beside the player, and nobody felled)",
      sc is not None and [a.name for a in sc.fight.fighters if a.side == "ally"] == ["Odly Garth"] and not sc.fight.felled_by,
      sc and [a.name for a in sc.fight.fighters if a.side == "ally"])
after, line = end(sc)
check("the next chamber, won minutes later with nobody falling, is told of no death of the player's own",
      after and line is None, (ws.minutes - died_at, line))

ws.advance(10)
after, line = end(wolf_fight())
check("...nor is a fight won ten minutes after that", after and line is None, (ws.minutes - died_at, line))

# ---- a second case of the kind: a hire who died outside any fight, five minutes before a fight is won
ws.enter("parth")
wenna = hire(3, "Wenna Cole", "scout", "she")
ws.player.party.append(wenna)
ws.party_service.kill(wenna, "a fall from the old wall", in_fight=False)
check("(Wenna is dead in the registry, outside any fight)", getattr(store.load_entity("hire:h3"), "state", "") == "dead"
      and wenna not in ws.player.party, store.load_entity("hire:h3"))
ws.advance(5)
after, line = end(wolf_fight())
check("a hire who died outside any fight five minutes before a fight is won is not told as dead in it", after and line is None, line)

# ---- another: a hire killed in a fight the player fled, then a fight won at once
bran = hire(4, "Bran Teague", "fighter", "he")
ws.player.party.append(bran)
sc = wolf_fight()
strike_down(sc, "Bran Teague", dies=True)
fled_after, _ = end(sc, "fled")
check("(Bran died in a fight the player fled, which has no passage after it)", not fled_after and bran not in ws.player.party
      and getattr(store.load_entity("hire:h4"), "state", "") == "dead", [m["name"] for m in ws.player.party])
ws.advance(3)
after, line = end(wolf_fight())
check("a fight won three minutes after a fight fled is not told of the death in the fight before", after and line is None, line)

# ---- controls: two who die in one fight are both named; one carried out alive is not
ws.advance(60)
ash, rook, mill = hire(5, "Ash Penrow", "fighter", "he"), hire(6, "Rook Dannel", "fighter", "she", permanent=False), hire(7, "Mill Orra", "priest", "she")
ws.player.party += [ash, rook, mill]
sc = wolf_fight()
by_ash = strike_down(sc, "Ash Penrow", dies=True)
by_rook = strike_down(sc, "Rook Dannel")                 # an old-style hireling who goes down does not get up: the fight's end kills them
strike_down(sc, "Mill Orra", dies=False)
after, line = end(sc)
ash_e, rook_e = store.load_entity("hire:h5"), store.load_entity("hire:h6")
check("(Ash and Rook are dead in the registry, Mill carried out alive and still in the party)",
      ash_e is not None and ash_e.state == "dead" and rook_e is not None and rook_e.state == "dead" and mill in ws.player.party,
      (ash_e, rook_e, [m["name"] for m in ws.player.party]))
check("two who die in one fight are both named, each with who struck them (one decided dead as they fell, one killed at its end)",
      line is not None and named(ash_e, by_ash) in line and named(rook_e, by_rook) in line and by_ash and by_rook, line)
check("...and no one else: not the hire carried out alive, nor the dead of the fights before",
      line is not None and all(n not in line for n in ("Mill Orra", "Odly Garth", "Thavin Liar", "Wenna Cole", "Bran Teague")), line)

ws.combat = None
cs.fresh = real_fresh
game.close()
shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
