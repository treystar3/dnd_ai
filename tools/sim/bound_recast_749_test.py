"""(f749) A Bound summon made anew in a fight walks into the next one (found by the audit, fight-abilities-3: a summoner whose Warden
was destroyed in one fight was told "Cast its spell again to make it anew"; the Warden, cast in the next fight, paid for and told as
taking shape, stood to the end, and the fight after began without it and with nothing said, since only a cast outside a fight mended
the bond). What a fight did to a summoner's bond is written back to the character from how the fight ended, by the service's one writer
of a fight's record, for each character from its own fighter: a Bound summon of the bond's spell standing at the end mends the bond
(and binds a character who had none); one destroyed leaves it broken and the note is said; a fight in which it was neither made nor
destroyed leaves it as it was. Whichever way the fight ended (won, fled, lost). A second Bound spell is still refused in a fight, nothing
paid, and the bond is not switched. A second character in the fight has its own bond written from its own fighter: neither the
first's loss nor the first's mending is laid on it. The same through the real scene and the save: the character loaded from the save
carries the mended bond, and the next fight it walks in."""
import os
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("summoner", 1)
simlib.install(stub)
SHOWN = simlib.quiet_console()
sys.stdout = open(os.devnull, "w", encoding="utf-8")         # the fight's panes; the checks go to the real stdout
from core.models import Ability, Summoned
from engine import battlefield_builder as bb, combat, streams, summons
from scenes import combat_scene as cs
from services.fight import FightSpec
from storage import saves

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NOTE = "Your Bound summon was unmade in the fight."
rng = random.Random(3)

# ---- through the fight service: begin (the Bound summon walks in, or not), the fight, close and end (the one writer of its record)
NAME = "bound_recast"
g = simlib.campaign(NAME, cls="summoner", seed=7, location="parth")
ws = g.scene
ws.enter("parth")
c = ws.player.character
WARDEN = c.bound_summon
check("(the stand-in summoner is bound to its Warden)", WARDEN == "call_the_warden" and not c.bound_broken, (WARDEN, c.bound_broken))
svc = cs.service_of(ws, random.Random(11))
creature = ws.world.bestiary["wolf"]


def begin(who=None):
    if who is not None:
        svc.characters = list(who)
    foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "wolf", "near")
    foe.behaviors["fearless"] = 1
    foe.hp = foe.max_hp = 10 ** 6
    f, _ = svc.begin(FightSpec(creature=creature, enemies=[foe], battlefield=bb.duel_ground(), place="the test ground"))
    return f


def walks_in(f, who=None):
    return summons.bound_of(f, who or f.player) is not None


def cast(f, mid, who=None):
    """The spell cast in the fight as a round casts it: (the refusal or None, the mana paid, the line told)."""
    p = who or f.player
    p.mana = p.max_mana = 10 ** 4
    p.cooldowns = {}
    f.story = []
    before = p.mana
    why = combat.act_ability(f, p, next(m for m in p.moves if m.id == mid), None, rng)
    return why, before - p.mana, " ".join(str(s) for s in f.story)


def destroy(f, who=None):
    b = summons.bound_of(f, who or f.player)
    if b is not None:
        combat.take_damage(f, b, b.hp * 10, f.get("e1"), rng, "magical")
    return b


def end(f, how="victory"):
    """The fight over as the scene's finish ends it: the row dropped, then the party's record written. The notes for the player."""
    f.over = how
    ending = svc.close(f)
    return svc.end(f, ending.fallen, how == "victory", False).notes


def unmade(notes):
    return [n for n in notes if NOTE in n]


# the case that found it: destroyed in fight 1, made anew and standing through fight 2, fight 3 begins
f = begin()
check("fight 1: the Warden walks in with the summoner", walks_in(f))
destroy(f)
notes = end(f)
check("...destroyed in it, the bond is broken and the note says to cast its spell again", c.bound_broken and len(unmade(notes)) == 1, (c.bound_broken, notes))
f = begin()
check("fight 2: broken, it does not walk in", not walks_in(f))
why, paid, told = cast(f, WARDEN)
check("...its spell is cast in the fight: not refused, mana paid, told that it takes shape", why is None and paid > 0 and "takes shape" in told, (why, paid, told))
check("...and it stands to the end", walks_in(f))
notes = end(f)
check("made anew in a fight and standing at its end, the bond is mended", not c.bound_broken and c.bound_summon == WARDEN, (c.bound_broken, c.bound_summon))
check("...and nothing says it was unmade", not unmade(notes), notes)
f = begin()
check("fight 3: the Warden made anew in fight 2 walks in", walks_in(f), c.bound_broken)
end(f)

# a second case of the kind: made anew and destroyed again
c.bound_broken = True
f = begin()
why, paid, _ = cast(f, WARDEN)
destroy(f)
notes = end(f)
check("made anew and destroyed again in the same fight: still broken, and the note is said again",
      why is None and c.bound_broken and len(unmade(notes)) == 1, (why, c.bound_broken, notes))

# never cast again: broken, a fight, nothing made
c.bound_broken = True
f = begin()
notes = end(f)
check("a fight in which its spell is not cast: still broken, and no second note", c.bound_broken and not unmade(notes), (c.bound_broken, notes))

# a fight that ends in flight
c.bound_broken = True
f = begin()
cast(f, WARDEN)
notes = end(f, "fled")
check("made anew in a fight the summoner flees: the bond is mended (it goes with them)", not c.bound_broken and not unmade(notes), (c.bound_broken, notes))
f = begin()
check("...and walks into the next fight", walks_in(f))
end(f)

# a fight that ends in defeat (the scene's finish writes the record before it reads how the fight ended)
c.bound_broken = True
f = begin()
cast(f, WARDEN)
notes = end(f, "defeat")
check("made anew in a fight the summoner loses: the bond is mended", not c.bound_broken and not unmade(notes), (c.bound_broken, notes))
f = begin()
check("...and walks into the next fight", walks_in(f))
destroy(f)
notes = end(f, "defeat")
check("destroyed in a fight the summoner loses: broken, and the note is said", c.bound_broken and len(unmade(notes)) == 1, (c.bound_broken, notes))

# a second Bound spell in a fight: refused before anything is paid, and the bond is neither switched nor mended by it
WYRM = Ability(id="call_the_wyrm", name="Call the Wyrm", description="d", effect="summon", tier="moderate", reach="self", resource="mana",
               context="both", cost=10, cooldown=1, summon_form="bound", summoned=Summoned(name="the Wyrm"))
c.actives.append(WYRM)
c.prepared = list(c.prepared) + [WYRM.id]
c.bound_broken = False
f = begin()
check("(the second Bound spell is brought into the fight)", any(m.id == WYRM.id for m in f.player.moves), [m.id for m in f.player.moves])
why, paid, _ = cast(f, WYRM.id)
check("with the Warden standing, a second Bound spell is refused and nothing is paid", bool(why) and "cannot be changed" in why and paid == 0, (why, paid))
destroy(f)
end(f)
f = begin()
why, paid, _ = cast(f, WYRM.id)
check("with the bond broken, a second Bound spell is still refused in a fight, nothing paid", bool(why) and "only be changed outside a fight" in why and paid == 0, (why, paid))
end(f)
check("...and after it the bond is the Warden's still, and still broken", c.bound_summon == WARDEN and c.bound_broken, (c.bound_summon, c.bound_broken))
c.actives.remove(WYRM)
c.prepared = [x for x in c.prepared if x != WYRM.id]

# a summoner with no bond written (creation bonds every summoner; the same write covers it)
c.bound_summon, c.bound_broken = "", False
f = begin()
check("(with no bond, nothing walks in)", not walks_in(f))
cast(f, WARDEN)
end(f)
check("no bond, a Bound summon made in a fight and standing at its end: the bond is its spell's", c.bound_summon == WARDEN and not c.bound_broken, (c.bound_summon, c.bound_broken))

# two characters in one fight (checklist 8): each bond is written from its own fighter
c2, _ = simlib.make_character("summoner", random.Random(5))
c2.id, c2.name = "p2", "Second"
c2.bound_broken = True
c.bound_summon, c.bound_broken = WARDEN, False
f = begin([c, c2])
p2 = f.get("p2")
check("(two player fighters: the first's Warden walks in, the second's bond is broken)", p2 is not None and walks_in(f) and not walks_in(f, p2))
why, paid, _ = cast(f, c2.bound_summon, p2)
check("(the second casts its own Warden in the fight)", why is None and walks_in(f, p2), why)
destroy(f)
notes = end(f)
check("the second's Warden made anew and standing: the second's bond is mended", not c2.bound_broken, c2.bound_broken)
check("...while the first's, destroyed, is broken", c.bound_broken and unmade(notes), (c.bound_broken, notes))
c.bound_broken, c2.bound_broken = False, False
f = begin()
p2 = f.get("p2")
cast(f, c2.bound_summon, p2)
destroy(f, p2)
end(f)
check("the second's Warden destroyed: the second's bond is broken, and the first's, standing, is not", c2.bound_broken and not c.bound_broken, (c2.bound_broken, c.bound_broken))
svc.characters = [c]
c.bound_broken = False
ws.store.save_player(ws.player)
g.close()
saves.drop(NAME)

# ---- the same through the real scene: the rounds played by the turn, the fight ended by the scene, the character read from the save
NAME = "bound_recast_scene"
g = simlib.campaign(NAME, cls="summoner", seed=494, location="parth")
ws, store = g.scene, g.store
ws.enter("parth")
seed = store.meta.seed
WARDEN = ws.player.character.bound_summon
pick = {"ability": "", "then": "attack"}


def choose(u, k):
    f = ws.combat.fight
    up = f.enemies()
    target = up[0].id if up else ""
    if pick["ability"] and f.player.cooldowns.get(pick["ability"], 0) <= 0:
        mid, pick["ability"] = pick["ability"], ""
        return {"kind": "ability", "ability": mid, "target": target}
    return {"kind": pick["then"], "target": target}


stub.a_CombatIntent = choose
ENDED = []                                                   # how each fight the scene finished ended (the scene's own record of it)
_finish = cs.CombatScene.finish


def finish(self):
    ENDED.append(self.fight.over)
    return _finish(self)


cs.CombatScene.finish = finish


def scene_fight(n, kill=False, ability="", then="attack", weak_at=2):
    """One fight through the scene. Returns (walked in, standing at the last round, how it ended, the notes shown, the saved character)."""
    streams.begin(seed, 100000, f"fight{n}")
    foes = [combat.fighter_from_creature(ws.world.bestiary["wolf"], 10, "normal", "e1", "Wolf")]
    foes[0].behaviors["fearless"] = 1
    foes[0].max_hp = foes[0].hp = foes[0].max_hp * 12
    if then == "flee":                                       # a slow foe and a quick summoner: the flight is let to work in a few tries
        foes[0].attrs["dexterity"] = 1
    sc = cs.CombatScene.begin(ws, ws.world.bestiary["wolf"], foes, "It is on you:")
    ws.combat = sc
    f = sc.fight
    f.player.max_hp = f.player.hp = f.player.max_hp * 8
    if then == "flee":
        f.player.attrs["dexterity"] = 40
    walked = walks_in(f)
    if kill and walked:
        destroy(f)
    pick["ability"], pick["then"] = ability, then
    store.save_combat(sc.to_json())
    SHOWN.clear()
    ENDED.clear()
    stood = None
    for r in range(20):
        if ws.combat is None:
            break
        if r == weak_at:
            for e in ws.combat.fight.enemies():
                e.hp = 1.0
            store.save_combat(ws.combat.to_json())
        streams.begin(seed, 1000 * n + r + 1, f"f{n}r{r + 1}")
        ws.turn("I fight on")
        if ws.combat is not None:
            stood = walks_in(ws.combat.fight)
    how = ENDED[-1] if ENDED else ""
    if ws.combat is not None:
        store.save_combat(None)
        ws.combat = None
    return walked, stood, how, [t for k, t in SHOWN if k == "note"], store.load_player().character


ws.player.character.level = 10
store.save_player(ws.player)
walked, _, how, notes, saved = scene_fight(1, kill=True)
check("the scene, fight 1: the Warden walks in and is destroyed; the saved character's bond is broken, and the note shown",
      walked and how == "victory" and saved.bound_broken and any(NOTE in n for n in notes), (walked, how, saved.bound_broken, notes))
walked, stood, how, notes, saved = scene_fight(2, ability=WARDEN)
check("the scene, fight 2: it does not walk in; its spell is cast and it stands", not walked and stood, (walked, stood))
check("...the fight won, the character loaded from the save carries the mended bond, and no note says it was unmade",
      how == "victory" and not saved.bound_broken and not any(NOTE in n for n in notes), (how, saved.bound_broken, notes))
walked, _, how, _, saved = scene_fight(3)
check("the scene, fight 3: the Warden made anew in fight 2 walks in", walked, saved.bound_broken)
_, _, how, _, saved = scene_fight(4, kill=True)
check("(the scene, fight 4: destroyed again)", saved.bound_broken)
walked, stood, how, notes, saved = scene_fight(5, ability=WARDEN, then="flee", weak_at=99)
check("the scene, fight 5: made anew, and the summoner flees the fight", how == "fled" and stood, (how, stood))
check("...the character loaded from the save carries the mended bond", not saved.bound_broken, saved.bound_broken)
walked, _, _, _, _ = scene_fight(6)
check("...and the Warden walks into the next fight", walked)
g.close()
saves.drop(NAME)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
