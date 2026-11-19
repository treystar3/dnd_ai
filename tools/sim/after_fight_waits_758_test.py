"""(f758) What waits on the next line after a fight is in the save: the yielded foe's question and the road walk to resume (the
audit's trace-save-3; docs/design/33_audit_fix_plan/reload.md RELOAD-9). A foe who yields at a fight's end and is not taken captive
waits on the player's word ("Spare it, or finish it?"), and a won road fight walks on once that word is given. Both were held on the
scene alone (held_yield, resume_pending), and the saved road was emptied of where the walk was going, so a game closed there, or
stopped between the fight's commit and its telling, lost them: "I spare it." after the open was a line about nobody (no mercy shown,
nothing killed), and the walk did not go on.
Now the yield is the world's question (engine/questions.py: ask_next, answered by on_answer_yield), the fighters in its data, so the
opening asks it again, a failed operation takes it back and the next line answers it; and the walk to take up is the saved road's
(its `resume`, marked won by the fight) until resume_road has run.
The case that found it: a wolf yields at a fight's last round, the game is closed and opened, and "I spare it." is answered. Second
cases of the kind: "I finish it" after an open kills it and leaves its remains; a line about something else lets it slip away and is
read as new; a walk away while it waits leaves it behind (no kill from afar); an operation that fails at the fight's end takes the
question back; a won road fight with a foe held, closed and opened, spares and then walks on to where the walk was going, any
question of another kind holds the walk as well, and with none held it walks on in the same line; the game stopped between the
fight's commit and its telling takes the answer at the next load; and the scene holds neither any more.
Run: python tools/sim/after_fight_waits_758_test.py"""
import io
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 5)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import config
import ui.console as uc
uc.put("status_block", lambda *a, **k: None)
uc.put("combat_state", lambda *a, **k: False)
LOGS = simlib.saves_path("after_fight_waits_logs")
LOGS.mkdir(parents=True, exist_ok=True)
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, str(LOGS / fn))
from core.interrupts import Interrupt
from engine import actor, combat, leveling, mapview, roads
from scenes.combat_scene import CombatScene
from scenes.world import WorldScene
from storage import saves
sys.stdout = io.StringIO()                                # the fight's pane, printed as plain text under the stand-in

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NOW = {}                                                  # the scene the game plays now: a new one at every open
TOLD = []                                                 # what the narrator is asked to tell
real_narration = stub.a_Narration
stub.a_Narration = lambda u, k: (TOLD.append(u), real_narration(u, k))[1]
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": next((e.id for e in NOW["ws"].combat.fight.enemies()), "")}
SPARE = "Spare it, or finish it?"


def opened(g):
    """The game closed and opened again as main.py opens a save, up to its first prompt: (the new scene, what the opening showed)."""
    SHOWN.clear()
    ws = g.reopen()
    NOW["ws"] = ws
    return ws, [t for _, t in SHOWN]


def fresh(name: str, seed: int, at: str):
    g = simlib.campaign(name, seed=seed, location=at, minutes=420)
    ws = g.scene
    leveling.level_up(ws.player.character, 5)
    ws.enter(at)
    g.store.save_player(ws.player)
    NOW["ws"] = ws
    return g, ws


def fight(ws, how: str = "In the trees,", held: bool = True) -> None:
    """Wolves at the player: with `held`, the first has thrown itself down and yielded, and the last stands one blow from the end."""
    beast = ws.world.bestiary["wolf"]
    ids = ("e1", "e2") if held else ("e2",)
    ws.combat = CombatScene.begin(ws, beast, [combat.fighter_from_creature(beast, 2, "normal", i, f"wolf {i[1]}", "near") for i in ids], how)
    f = ws.combat.fight
    if held:
        down = f.get("e1")
        down.hp, down.fled, down.surrendered = 2, True, True
    f.get("e2").hp = 1
    ws.store.save_combat(ws.combat.to_json())


def win(ws, line: str = "I strike at the wolf.") -> bool:
    """The fight's rounds, typed through the game's one input path, until it is won."""
    SHOWN.clear()
    for _ in range(25):
        if ws.combat is None:
            break
        ws.play(line)
    return ws.combat is None


def held_out() -> bool:
    """The player was shown the yielded wolf's question as the fight ended."""
    return any(SPARE in t for _, t in SHOWN)


def answer(ws, line: str, plan=None) -> dict:
    """One line typed after the fight: what it did (Spared deeds, kills, notes, what the narrator was asked, whether the line was
    read by the interpreter as a line of its own)."""
    seen = []
    real = ws.notice
    ws.notice = lambda d: (seen.append(d.kind), real(d))[1]
    stub.plan = list(plan or [{"kind": "look"}])
    SHOWN.clear()
    TOLD.clear()
    read0 = stub.calls.get("ActionPlan", 0)
    ws.play(line)
    ws.notice = real
    return {"seen": seen, "notes": [t for _, t in SHOWN], "told": list(TOLD), "read": stub.calls.get("ActionPlan", 0) > read0}


def remains(ws) -> int:
    return sum(1 for x in ws.store.load_place(ws.player.location).carcasses if x.get("creature") == "wolf")


# ---- the case that found it: a wolf yields at the fight's last round; the game is closed, opened, and "I spare it." answered
g, ws = fresh("after_fight_waits", 5, "greywood")
fight(ws)
check("(the fight is won, one wolf having yielded, and the player is asked)", win(ws) and held_out(), ws.combat and ws.combat.fight.over)
asked = g.store.load_question() or {}
check("the yielded wolf's question is kept in the save as the fight ends", asked.get("kind") == "yield" and SPARE in asked.get("question", ""), asked)
ws, shown = opened(g)
check("...the opening asks it again", any(SPARE in t for t in shown), shown[-4:])
got = answer(ws, "I spare it.")
check("'I spare it.' after the open spares the wolf: the mercy is a deed, and the narrator tells it",
      "spared" in got["seen"] and any("The player spares" in t for t in got["told"]), (got["seen"], got["notes"][:4]))
check("...and the line was the answer, not a new line about nobody", not got["read"] and g.store.load_question() is None, got)

# ---- an operation that fails at the fight's end takes the question back; the fight is played again and asks it
fight(ws)
real_over = ws.orenna_fight_over
ws.orenna_fight_over = lambda outcome: (_ for _ in ()).throw(RuntimeError("a fault at the fight's end"))
ws.play("I strike at the wolf.")
while ws.combat is not None and ws.combat.fight.get("e2").hp > 0 and not ws.line_failed:
    ws.play("I strike at the wolf.")
check("(the round that won failed on the game's own fault)", bool(ws.line_failed), [o.kind for o in ws.line_ops])
check("an operation that fails at the fight's end takes the question back: none stands, and the fight is still on",
      g.store.load_question() is None and ws.combat is not None, (g.store.load_question(), ws.combat))
ws.orenna_fight_over = real_over
check("(played again, the fight is won)", win(ws))
check("...and its question is asked", (g.store.load_question() or {}).get("kind") == "yield", g.store.load_question())

# ---- "I finish it" after an open kills it and leaves its remains
ws, shown = opened(g)
before = remains(ws)
got = answer(ws, "I finish it.")
check("'I finish it.' after the open kills the wolf that yielded: the narrator tells a kill, and its remains lie here",
      any("The player kills" in t for t in got["told"]) and remains(ws) == before + 1 and "kill" in got["seen"], (got["seen"], before, remains(ws)))
check("...the line was the answer", not got["read"] and g.store.load_question() is None, got["read"])

# ---- a line about something else lets it slip away, said so, and is read as a line of its own
fight(ws)
check("(the fight is won again, a wolf yielded)", win(ws) and held_out())
got = answer(ws, "I look around the trees.")
check("a line about something else lets it slip away, with the note, and is read as new; nothing is spared or killed",
      any("slips away" in n for n in got["notes"]) and got["read"] and "spared" not in got["seen"] and "kill" not in got["seen"]
      and g.store.load_question() is None, got)


def wolves_at(ws, place: str) -> int:
    return sum(1 for x in ws.store.load_place(place).carcasses if x.get("creature") == "wolf")


# ---- a walk away while it waits (a pane's #goto leaves the question standing, f460): no blow lands from afar
fight(ws)
check("(the fight is won again, a wolf yielded)", win(ws) and held_out())
fought_at = ws.player.location
ws.player.visited.append("parth")                         # a town the character knows the way to, for the pane's Go
ways = ws.places_data()
away = next((r["id"] for r in ways["local"] + ways["far"] if r["id"] != fought_at), "")
chance = roads.R["chance_per_leg"]
roads.R["chance_per_leg"] = 0.0
ws.play(f"#goto {away}")
roads.R["chance_per_leg"] = chance
before = (remains(ws), wolves_at(ws, fought_at))
got = answer(ws, "I finish it.")
check("a walk away while the yield waits leaves the wolf behind: 'I finish it.' kills nothing from afar, and it slips away",
      ws.player.location != fought_at and any("slips away" in n for n in got["notes"]) and "kill" not in got["seen"]
      and (remains(ws), wolves_at(ws, fought_at)) == before and g.store.load_question() is None,
      (away, ws.player.location, got["seen"], got["notes"][:3], before))
g.close()
saves.drop("after_fight_waits")


# ---- the road: a won fight with a foe held, closed and opened, spares and then walks on to where the walk was going
R = roads.R
KEEP = {k: R[k] for k in ("chance_per_leg", "hostile", "kinds", "max_per_trip")}


def farthest(world, start: str) -> str:
    towns = [p.id for p in world.places.values() if not p.parent and not p.danger and p.type in ("town", "city", "village") and p.id != start]
    return max(((world.path(start, t) or ([], 0))[1], t) for t in towns)[1]


def to_stop(ws, start: str) -> tuple:
    """The walk from `start` stopped on the road, the stop holding where a won fight goes on to, as an ambush's does (road_event)."""
    R.update(chance_per_leg=1.0, hostile=0.0, kinds={"meeting": 1}, max_per_trip=9)
    dest = farthest(ws.world, start)
    stub.plan = [{"kind": "move", "destination": dest}]
    ws.play(f"I set out for {ws.world.places[dest].name}.")
    R.update(KEEP)
    R["chance_per_leg"] = 0.0
    road = ws.player.road or {}
    if road:
        road["resume"] = road.get("bound", dest)
        ws.store.save_player(ws.player)
    return dict(road), dest


g, ws = fresh("after_fight_road", 7, "parth")
stop, dest = to_stop(ws, "parth")
check("(the walk is stopped on the road, the stop holding where it goes on to)", stop.get("id") and stop.get("resume") == dest, stop)
fight(ws, "On the road,")
check("(the road fight is won, one wolf having yielded)", win(ws) and held_out(), ws.combat)
saved = g.store.load_player().road or {}
check("while the yield waits the walk waits: still at the stop, and the saved road keeps where the walk goes on to",
      ws.player.location == stop["id"] and saved.get("resume") == dest, (ws.player.location, saved.get("resume")))
ws, shown = opened(g)
check("...the opening asks the question again", any(SPARE in t for t in shown), shown[-4:])
got = answer(ws, "I spare it.")
check("'I spare it.' after the open spares the wolf, and the walk then goes on to where it was going",
      "spared" in got["seen"] and mapview.top_of(ws.world, ws.player.location) == dest, (got["seen"], ws.player.location, dest))
check("...and the road's record is spent: no walk is waiting", not (ws.player.road or {}).get("resume"), ws.player.road)

# ---- ...and with no foe held, a won road fight walks on in the line that won it, the saved road spent as the line ends
stop, dest2 = to_stop(ws, dest)
check("(the next walk is stopped on the road)", stop.get("id") and stop.get("resume") == dest2, stop)
ws.player.road["won"] = True                              # a won fight's mark, with a question of another kind standing
ws.store.save_question({"kind": "discard", "question": "Discard it for good? (y/n)", "data": {}})
held = ws.walk_due()
ws.store.clear_question()
check("any question the world asked holds the walk, not the yield's alone; once it is gone the walk is due", not held and ws.walk_due(), held)
ws.player.road.pop("won", None)
fight(ws, "On the road,", held=False)
check("a road fight won with none yielded walks on in the same line, to where the walk was going",
      win(ws) and g.store.load_question() is None and mapview.top_of(ws.world, ws.player.location) == dest2, (ws.player.location, dest2))
check("...and the save holds no walk waiting", not (g.store.load_player().road or {}).get("resume"), g.store.load_player().road)
g.close()
saves.drop("after_fight_road")


# ---- the game stopped between the fight's commit and its telling (f467): the next load asks, and takes the answer
g, ws = fresh("after_fight_crash", 9, "greywood")
fight(ws)
crashes, shown = 0, []
for _ in range(25):
    ws.crash_after_commit = "line"
    try:
        ws.play("I strike at the wolf.")
    except Interrupt:
        crashes += 1
    ws, shown = opened(g)
    if ws.combat is None:
        break
check("(the game stopped after the round that won stood, before it was told)", crashes >= 1 and ws.combat is None, (crashes, ws.combat))
check("...the next load asks the yielded wolf's question", any(SPARE in t for t in shown) and (g.store.load_question() or {}).get("kind") == "yield",
      (shown[-4:], g.store.load_question()))
before = remains(ws)
got = answer(ws, "I finish it.")
check("...and the answer is taken: the wolf is killed and its remains lie here", any("The player kills" in t for t in got["told"])
      and remains(ws) == before + 1 and not got["read"], (got["seen"], before, remains(ws)))
g.close()
saves.drop("after_fight_crash")

# ---- the scene holds neither: what waits is the save's
own, outside, _ = simlib.scene_names()
names = ("held_yield", "resume_pending")
check("no code holds a yield or a walk to resume on the scene, and no table declares them",
      not [n for n in names if n in own or n in outside or n in actor.ATTRS or n in getattr(actor, "OPENING", {})],
      [n for n in names if n in own or n in outside or n in actor.ATTRS])
check("...and the yield is the world's question, not an intercept", hasattr(WorldScene, "on_answer_yield")
      and not any(i.name == "yielded" for i in WorldScene.INTERCEPT_TABLE), [i.name for i in WorldScene.INTERCEPT_TABLE])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
