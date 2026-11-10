"""(f503) scenes/combat_scene.py is a coordinator over services/fight.py. The service publishes FightBegun, RoundFought and FightEnded
in order, each with the fight's serial, and none of them is a journal row; a fight's end drops the row, writes the experience, the coin
and the carcasses; a damaged row resumes to None with its reason, and the scene lets the fight go (the reason in logs/crash.log); the
same scripted fight played through the scene and through the service alone gives the same blows (the hits records) and the same rows;
the proposal is validated into a RoundIntent (a target not in the fight falls to the closest foe; words to a wolf are refused as a free
action); a draught that is not carried is refused before anything is drunk; a death publishes PlayerFell; the scene keeps its name, its
attributes and its three-argument constructor, and its service rolls the scene's own die. Nothing stays in the process."""
import json
import shutil
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import combat, crashlog, domain_events as de, streams
from engine import battlefield_builder
from scenes import combat_scene as cs
from services.fight import FightService, FightSpec, RoundIntent
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

console.combat_state = lambda data: False
console.combat_panel = lambda lines: None
EVENTS = []
FIGHT_KINDS = ("fight_begun", "round_fought", "fight_ended", "player_fell")


def listen(ws):
    EVENTS.clear()
    ws.session.bus.subscribe(de.Event, lambda e: EVENTS.append(e) if e.kind in FIGHT_KINDS else None)


def wolf(ws, hp=None):
    creature = ws.world.bestiary["wolf"]
    foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "wolf", "near")
    foe.behaviors["fearless"] = 1                           # it never runs, so the fight ends when one side falls
    if hp is not None:
        foe.hp = foe.max_hp = hp
    return creature, foe


def through_scene(name, hp=None, rounds=12):
    """A fight from a fresh campaign, through the scene (the executor and the stub's intents): the rows saved after each input."""
    game = simlib.campaign(name, cls="warrior", seed=3, location="south_fields")
    ws, store = game.scene, game.store
    ws.enter("south_fields")
    listen(ws)
    creature, foe = wolf(ws, hp)
    ws.wildlife = (creature, [foe])
    stub.plan = [{"kind": "attack", "target": "wolf"}]
    stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
    ws.turn("I attack the wolf.")                            # each input reseeds the streams from (seed, steps, text): new_input
    stub.plan = None
    steps = [store.meta.steps]
    rows = [json.loads(store.load_combat())] if store.load_combat() else []
    for k in range(rounds):
        if ws.combat is None:
            break
        ws.turn("I strike at the wolf.")
        steps.append(store.meta.steps)
        if store.load_combat():
            rows.append(json.loads(store.load_combat()))
    return game, ws, store, rows, steps


def bare(row):
    """A row with the scene's memory of the telling (shown, ground_told) left out, and the serial (the ids stream's draw at the fight's place in the
    input; the scene's input draws ids before it, the service alone does not) written as S, in the blows' ids too."""
    f = json.loads(json.dumps(row["fight"]))
    f.pop("shown", None)
    f.pop("ground_told", None)                       # (f571) the scene's memory of what ground it told, the same kind
    serial = f.get("serial", "")
    f["serial"] = "S"
    for h in f.get("hits", []):
        h["id"] = h["id"].replace(serial, "S", 1)
    for row_ in f.get("effects", []):
        for k, v in list(row_.items()):
            if isinstance(v, str) and serial and serial in v:
                row_[k] = v.replace(serial, "S")
    return f


# ---- through the scene: the events in order, the row dropped, the rewards written
game, ws, store, rows, STEPS = through_scene("fight_service_503_a")
c = ws.player.character
kinds = [e.kind for e in EVENTS]
serials = {e.serial for e in EVENTS}
check("a fight through the scene publishes FightBegun, then a RoundFought a round, then FightEnded, all with the fight's serial",
      kinds[:1] == ["fight_begun"] and kinds[-1] == "fight_ended" and all(k == "round_fought" for k in kinds[1:-1]) and len(kinds) >= 3
      and len(serials) == 1 and serials == {rows[0]["fight"]["serial"]}, (kinds, serials))
check("...the fight ended in a win, the row dropped", ws.combat is None and store.load_combat() is None and EVENTS[-1].outcome == "victory",
      (ws.combat, EVENTS[-1] if EVENTS else None))
check("...the experience written, the carcass left here", c.xp > 0 and len(store.load_place("south_fields").carcasses) == 1,
      (c.xp, store.load_place("south_fields").carcasses))
killed_kind = de.CreatureKilled(minute=0).kind
check("...and none of the fight's signals is a journal row (the kill, a deed, is one)", all(store.journal_tail(50, kind=k) == [] for k in FIGHT_KINDS)
      and store.journal_tail(50, kind=killed_kind) != [], ([k for k in FIGHT_KINDS if store.journal_tail(50, kind=k)], killed_kind, store.journal_tail(5)))
scene_rows = [bare(r) for r in rows]
game.close()
shutil.rmtree("saves/fight_service_503_a", ignore_errors=True)

# ---- the same fight through the service alone: the same blows, the same rows
game = simlib.campaign("fight_service_503_b", cls="warrior", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")
listen(ws)
svc = cs.service_of(ws)
creature, foe = wolf(ws)
near, later, notes, formed = svc.allies(False)
streams.begin(store.meta.seed, STEPS[0], "I attack the wolf.")            # the dice as the scene's inputs had them
ground = battlefield_builder.for_scene(ws, duel=False, big=battlefield_builder.big_kind([foe], [], ""))
with ws.operation("test:begin", "I attack the wolf."):
    fight, opening = svc.begin(FightSpec(creature=creature, enemies=[foe], allies=near, later=later, battlefield=ground, place=ws.place.name,
                                         conditions=sorted(ws.conditions()), initiated=True))
service_rows = [bare(json.loads(store.load_combat()))]
check("the service alone: the fight built, the row saved, the odds estimated, FightBegun published",
      fight.serial and opening.label in ("trivial", "favorable", "even", "dangerous", "deadly") and EVENTS and EVENTS[0].kind == "fight_begun"
      and EVENTS[0].serial == fight.serial and EVENTS[0].foes == ("wolf",), (fight.serial, opening.label, EVENTS[:1]))
k = 0
while not fight.over and k < 12 and k + 1 < len(STEPS):
    streams.begin(store.meta.seed, STEPS[k + 1], "I strike at the wolf.")
    with ws.operation("test:round", "I strike at the wolf."):
        outcome = svc.round(fight, RoundIntent(kind="attack", target="e1", words="I strike at the wolf."))
        svc.sync(fight)
        if not fight.over:                                  # the scene saves the row at a round's end; a fight over drops it (close)
            svc.save(fight, creature.name)
    if not fight.over:
        service_rows.append(bare(json.loads(store.load_combat())))
    k += 1
check("the same scripted fight through the service alone yields identical hits records and fight rows (up to the serial)",
      len(service_rows) == len(scene_rows) and all(a == b for a, b in zip(service_rows, scene_rows)) and len(service_rows) >= 2,
      (len(service_rows), len(scene_rows), next(((i, k2, a.get(k2), b.get(k2)) for i, (a, b) in enumerate(zip(service_rows, scene_rows)) for k2 in a if a.get(k2) != b.get(k2)), None)))
check("...and the fight ended the same way, in the round after the last row", fight.over == "victory" and fight.round == rows[-1]["fight"]["round"],
      (fight.over, fight.round, rows[-1]["fight"]["round"]))
check("...every round's blows are in its row, under the serial", all(r["hits"] and all(h["id"].startswith("S-") for h in r["hits"]) for r in service_rows[1:]),
      [[h["id"] for h in r["hits"]] for r in service_rows])
dead = [e for e in fight.fighters if e.side == "enemy" and not e.alive]
with ws.operation("test:end", "I strike at the wolf."):
    ending = svc.close(fight)
    svc.yields(fight, allowed=True)
    won = svc.rewards(fight, dead, [])
    levels = svc.award(won.xp, won.coins)
check("the end through the service: the row dropped, the minutes counted, the experience, the coin and the carcass written",
      store.load_combat() is None and ending.outcome == "victory" and ending.minutes >= 1 and ending.dead == dead and won.xp > 0
      and ws.player.character.xp == won.xp and len(store.load_place("south_fields").carcasses) == 1 and levels == 0,
      (ending, won.xp, ws.player.character.xp, store.load_place("south_fields").carcasses))
check("...FightEnded published with the outcome and the dead, after every RoundFought", [e.kind for e in EVENTS][-1] == "fight_ended"
      and EVENTS[-1].outcome == "victory" and EVENTS[-1].dead == ("the wolf",) and EVENTS[-1].serial == fight.serial, EVENTS[-1])

# ---- the proposal, validated: a target not in the fight falls to the closest foe; words to a wolf are a refused free action
creature, foe = wolf(ws)
streams.begin(store.meta.seed, 950, "again")
with ws.operation("test:begin2", "again"):
    fight2, _ = svc.begin(FightSpec(creature=creature, enemies=[foe], battlefield=battlefield_builder.for_scene(ws), place=ws.place.name,
                                    conditions=sorted(ws.conditions())))
    before = (fight2.round, foe.hp)
    talked = svc.round(fight2, RoundIntent(kind="talk", approach="persuade", target="e1", words="Easy, easy"))
    after_talk = (fight2.round, foe.hp)
    fought = svc.round(fight2, RoundIntent(kind="attack", target="nobody", words="I strike"))
check("words to a wolf are a free action that is refused: no round passes", talked.kind == "talk" and talked.problem and after_talk == before, (talked, before, after_talk))
check("a target the fight does not hold falls to the closest foe: the round is fought", fought.kind == "round" and fight2.round == before[0] + 1
      and any(h["dfn"] == "wolf" for h in fight2.hits), (fought, [(h["att"], h["dfn"]) for h in fight2.hits]))
item, why = svc.item_for(fight2, "a draught nobody carries")
check("a draught that is not carried is refused before anything is drunk", item is None and "nothing like that" in why, why)
check("the row written by the service resumes to the same fight; a damaged row resumes to None with its reason",
      svc.resume(svc.row(fight2, "wolf"))[0].serial == fight2.serial and svc.resume('{"creature": "wolf"}')[0] is None
      and "KeyError" in svc.resume('{"creature": "wolf"}')[2] and svc.resume("not json")[0] is None, svc.resume("not json"))
scene_none = cs.CombatScene.resume(ws, "{broken")
check("...and the scene lets such a fight go, the reason in the crash log", scene_none is None and crashlog.last() and "fight row" in crashlog.last()["where"],
      crashlog.last())

# ---- the scene keeps its shape; its service rolls its die
sc = cs.CombatScene(ws, fight2, "wolf")
check("CombatScene keeps its three-argument constructor and its attributes", sc.fight is fight2 and sc.ws is ws and sc.creature_name == "wolf"
      and sc.rng is streams.get("combat") and sc.fight_shown == [] and sc.tamed == [])
check("...and its service is built over the scene's own die (a test that steers sc.rng steers the service)", isinstance(sc.service, FightService)
      and sc.service.dice is sc.rng and sc.service.player is ws.player)
with ws.operation("test:fall", "again"):
    summary = svc.fall(fight2)
check("a death publishes PlayerFell and takes its price", EVENTS[-1].kind == "player_fell" and EVENTS[-1].serial == fight2.serial
      and ws.player.character.deaths == 1 and summary["deaths"] == 1, (EVENTS[-1], summary))
from engine import pools
pools.fill_missing(ws.player.character)

game.close()
shutil.rmtree("saves/fight_service_503_b", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
