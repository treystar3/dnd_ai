"""(f765) What a fight is for is saved with the fight (the audit's scenes1-1, trace-save-2, scenes3-5, engine3-8;
docs/design/33_audit_fix_plan/reload.md RELOAD-3). Four kinds of fight decide something beyond themselves when they end: a dungeon's
chamber is cleared, an arc's camp moves the arc on, the High Keeper's fight ends the quest Orenna, and a host at a town's gate holds
the town or lets its roll run. What each was for lived on the scene alone (dungeon_fight, camp_fight, orenna_fight, assault) while
the fight itself was a saved row, so a game closed or stopped in the middle of one resumed the fight and, won, fled or lost, ended
it with none of its consequences: the chamber fought and paid twice, the arc's step not moved, the Keeper and the Executioner
standing whole again, the town neither held nor fallen.
Now the fight carries its purpose (engine/combat.py Combat.purpose: the kind, its facts and the character it is for), in its row from
the first save, and one table keyed by kind (scenes/combat_scene.py PURPOSES) says what each does at the end and what is read while it
is fought. A fight let go of at load hands its purpose on where the row still says it.
The case that found it: a dungeon chamber won after a reopen is cleared. Second cases of the kind, each closed and opened in the
middle of the fight: the chamber fled (the way back told); an arc's hideout won (the step moves, no survivor rolled to yield); the
High Keeper won (the quest ends, the breath given) and lost (the six hour wait); the gate won (held, the deed, the town's regard) and
fled (the roll runs), with an operation failing in the middle of it; a gate fight let go at load, of another shape or by a migration,
runs the town's roll, and a dungeon's or a damaged row does nothing more; an ordinary fight's row is as it was and reads as for
nothing; and no code holds what a fight is for on the scene.
Run: python tools/sim/fight_purpose_765_test.py"""
import io
import json
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
uc.put("wait", lambda *a, **k: None)
LOGS = simlib.saves_path("fight_purpose_logs")
LOGS.mkdir(parents=True, exist_ok=True)
for key, fn in (("TURN_LOG_PATH", "turns.jsonl"), ("CRASH_LOG_PATH", "crash.log"), ("PULSE_LOG_PATH", "pulse.jsonl"),
                ("LOG_PATH", "llm_calls.jsonl"), ("SESSION_STATS_PATH", "sessions.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl")):
    setattr(config, key, str(LOGS / fn))
from engine import actor, arcs, combat, dungeons, events, failures, orenna, pools, pulse, quests
from scenes import combat_scene as cs
from scenes.world import WorldScene
from services.fight import FightService, RoundOutcome
from storage import migrations, saves
sys.stdout = io.StringIO()                                # the fight's pane, printed as plain text under the stand-in

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NOW = {}                                                  # the scene the game plays now: a new one at every open
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": next((e.id for e in NOW["ws"].combat.fight.enemies()), "")}
texts = lambda: [t for _, t in SHOWN]


def opened(g):
    """The game closed and opened again as main.py opens a save, up to its first prompt: the new scene, and `store` the new session's."""
    global store
    SHOWN.clear()
    NOW["ws"] = ws = g.reopen()
    store = g.store
    return ws


def end(ws, how: str, line: str = "I strike at the nearest of them.") -> None:
    """The fight's next round, typed through the game's one input path, ends as `how` says: that round's dice are the test's (every
    try of it, as an operation run again for its answer plays the round again)."""
    real = FightService.round

    def last(self, f, intent):
        for e in f.fighters:
            if how == "victory" and e.side == "enemy" and not e.surrendered:
                e.hp = 0
            if how == "defeat" and e.id == "player":
                e.hp = 0
        f.reserves = []
        f.over = how
        return RoundOutcome(kind="round", notes=[], killed=[], over=how)
    FightService.round = last
    SHOWN.clear()
    try:
        ws.play(line)
    finally:
        FightService.round = real


def row_purpose(store) -> dict:
    """What the saved fight's row says it is for, {} when nothing."""
    raw = store.load_combat()
    return (json.loads(raw)["fight"].get("purpose") or {}) if raw else {}


SEEN = set()                                              # every kind of purpose a fight of this test was begun with
BY = []                                                   # whom each purpose names, beside who was acting as it began


def begun(ws, store) -> bool:
    p = row_purpose(store)
    SEEN.add(p.get("kind", ""))
    if p:
        BY.append((p.get("by"), ws.acting))
    return ws.combat is not None and store.load_combat() is not None


# ---- an ordinary fight: its row is as it was, and reads as for nothing
g = simlib.campaign("fight_purpose_dungeon", cls="warrior", seed=3, location="south_fields")
ws = opened(g)
store = g.store
c = ws.player.character
c.level = 12
pools.fill_missing(c)
store.save_player(ws.player)
wolf = ws.world.bestiary["wolf"]
ws.wildlife = (wolf, [combat.fighter_from_creature(wolf, 2, "normal", "e1", name="wolf 1")])
stub.plan = [{"kind": "attack", "target": "wolf"}]
ws.play("I attack the wolf.")
stub.plan = None
raw = store.load_combat() or "{}"
fields = [k for k in combat.Combat.model_fields if k != "purpose"]
check("an ordinary fight's row has no purpose in it: the fight's fields as they always were, in their order",
      ws.combat is not None and '"purpose"' not in raw and list(json.loads(raw).get("fight", {})) == fields, (list(json.loads(raw).get("fight", {}))[-3:], fields[-3:]))
check("...and a row with no purpose reads as a fight for nothing beyond itself",
      getattr(FightService.resume(raw)[0], "purpose", "no such field") is None, getattr(FightService.resume(raw)[0], "purpose", "no such field"))
end(ws, "victory")
check("(the ordinary fight won)", ws.combat is None and store.load_combat() is None)

# ---- the case that found it: a dungeon chamber, the game closed in the middle of its fight, opened and won
ROOM = {"kind": "fight", "creature": "wolf", "count": 1, "level": 1, "boss": False}
d = next(x for x in store.load_dungeons() if not x.get("fixed"))
d["floors"][0]["chambers"] = [dict(ROOM), dict(ROOM), {"kind": "rest"}]
d["cleared"] = [-1, -1]
ws.save_dungeon(d)
ws.player.location = d["entrance"]
ws.enter(d["entrance"])
store.save_player(ws.player)


def chamber(store) -> tuple:
    x = next(x for x in store.load_dungeons() if x["id"] == d["id"])
    return x["cleared"], dungeons.next_chamber(x)


stub.plan = [{"kind": "delve"}]
ws.play("I go down into the dungeon.")
stub.plan = None
check("(the chamber's fight is begun and its row saved)", begun(ws, store))
ws = opened(g)
check("(opened again in the middle of the fight)", ws.combat is not None and "You are still in the middle of a fight!" in texts())
end(ws, "victory")
check("a chamber won after the game was closed and opened is cleared: the next step goes on to the chamber after it, never the same one again",
      ws.combat is None and chamber(store) == ([0, 0], (0, 1)), chamber(store))

# ---- the chamber after it, fled after a reopen: the way back is told
stub.plan = [{"kind": "delve"}]
ws.play("I go on deeper.")
stub.plan = None
check("(the next chamber's fight is begun)", begun(ws, store))
ws = opened(g)
end(ws, "fled", "I run for it.")
check("a chamber fled after a reopen: the player is told they fall back, and the chamber is still held",
      ws.combat is None and any("You fall back to the chamber you came from" in t for t in texts()) and chamber(store)[0] == [0, 0],
      (texts()[-4:], chamber(store)))

# ---- a dungeon's fight of another shape, let go at load: the line, and nothing more
stub.plan = [{"kind": "delve"}]
ws.play("I go on deeper.")
stub.plan = None
row = json.loads(store.load_combat())
row["fight"]["version"] = 0
store.save_combat(json.dumps(row))
ws = opened(g)
told = [t for t in texts() if t in failures.F["fight_let_go"]]
check("a dungeon's fight of another shape is let go at load with one line, its row gone, the chamber as it was",
      len(told) == 1 and ws.combat is None and store.load_combat() is None and chamber(store)[0] == [0, 0], (told, chamber(store)))
g.close()
saves.drop("fight_purpose_dungeon")


# ---- an arc's hideout, fought through camp_battle and opened again in the middle
def make_arc(ws, store):
    """An arc of the chain kind whose trail has a hideout, taken as the guild gives one."""
    tpl_id = next(t for t, v in arcs.TEMPLATES.items() if v["finale"] == "fight")
    tpl = arcs.TEMPLATES[tpl_id]
    for k in range(20):
        q = quests._quest("missing", "D", "Find someone", ws.minutes, victim=tpl["victims"][0], hall="guild_house", count=1)
        q.update(id=f"purpose{k}", template=tpl_id, hall="guild_house")
        arc = arcs.build(ws.world, store, q, "guild_house", ws.player.character.level, "chain", "forced", ws.minutes, store.meta.seed)
        if any(n["kind"] == "lair" for n in arc["nodes"]):
            break
    nodes = [{"id": n["id"], "kind": n["kind"], "role": n.get("role", ""), "people": n["people"], "place_name": n["place"], "next": ""} for n in arc["nodes"]]
    arc["story"] = ws.plain_story(arc, nodes, [])
    data = ws.arc_data()
    data["arcs"].append(arc)
    store.save_arcs(data)
    q["arc"] = arc["id"]
    ws.player.quests.append(q)
    store.save_player(ws.player)
    data, arc = ws.my_arc()
    while arcs.current(arc)["kind"] != "lair":
        arcs.complete_node(arc, arcs.current(arc)["id"])
    store.save_arcs(data)
    return data, arc, arcs.current(arc)


g = simlib.campaign("fight_purpose_camp", cls="warrior", seed=4, location="parth")
ws = opened(g)
store = g.store
ws.player.character.level = 12
pools.fill_missing(ws.player.character)
data, arc, n = make_arc(ws, store)
nid = n["id"]
ws.player.location = n["place"]
store.save_player(ws.player)
ws.enter(n["place"])
ws.camp_battle(data, arc, n, arcs.TEMPLATES[arc["template"]])
check("(the hideout's fight is begun and its row saved)", begun(ws, store))
ws = opened(g)
check("an arc's camp fight opened again rolls no survivor to yield: the camp's leader is taken its own way",
      ws.combat is not None and ws.combat.yield_allowed() is False, ws.combat.yield_allowed() if ws.combat else None)
end(ws, "victory")
step = arcs.node(ws.my_arc()[1], nid)
check("a hideout won after a reopen moves the arc: the step done, what was found there given",
      ws.combat is None and step["status"] == "done" and step["clue_given"], (step["status"], step["clue_given"]))
g.close()
saves.drop("fight_purpose_camp")

# ---- the High Keeper, opened again in the middle of the fight: won, and then lost
KEEPER = orenna.O["keeper_city"]
g = simlib.campaign("fight_purpose_keeper", cls="warrior", seed=5, location=KEEPER)
ws = opened(g)
store = g.store
c = ws.player.character
c.level = 50
pools.fill_missing(c)
ws.player.orenna.update(stage="trails", evidence=3.0, trails_done=[0, 1], executioner=True)
store.save_player(ws.player)
ws.on_answer_executioner({}, "Yes.")
check("(the Bound Executioner pressed: his fight is begun and its row saved)", begun(ws, store))
ws = opened(g)
real = FightService.round


def gone(self, f, intent):
    for e in f.enemies():
        e.fled = True                                     # he breaks off in his flash of light, alive
    f.over = "victory"
    return RoundOutcome(kind="round", notes=[], killed=[], over="victory")


FightService.round = gone
SHOWN.clear()
ws.play("I strike at him.")
FightService.round = real
check("the Executioner's fight ended after a reopen tells his escape in the quest's own words, and no plain line that they got away",
      ws.combat is None and orenna.O["executioner"]["yield"] in texts() and "They got away. You've nothing to show for this one." not in texts(),
      texts()[-4:])
ws.player.orenna.update(stage="confront", trails_done=[0, 1, 2])
store.save_player(ws.player)
ws.orenna_confront()
check("(the High Keeper's fight is begun and its row saved)", begun(ws, store))
ws = opened(g)
end(ws, "victory")
p = store.load_player()
check("the High Keeper beaten after a reopen ends the quest: the stage done, Orenna's breath given, and no confrontation begun again",
      ws.combat is None and orenna.stage(p) == "done" and p.character.orenna_breath, (orenna.stage(p), p.character.orenna_breath, ws.combat is not None))
ws.player.orenna.update(stage="confront")
ws.player.orenna.pop("retry", None)
ws.player.character.orenna_breath = False
store.save_player(ws.player)
ws.orenna_confront()
check("(the Keeper's fight begun once more)", begun(ws, store))
ws = opened(g)
m0 = ws.minutes
end(ws, "defeat", "I hold my ground.")
p = store.load_player()
check("the High Keeper's fight lost after a reopen sets the six hour wait before he can be faced again",
      orenna.stage(p) == "confront" and p.orenna.get("retry", 0) > m0 and not p.character.orenna_breath, (orenna.stage(p), p.orenna.get("retry"), m0))
g.close()
saves.drop("fight_purpose_keeper")

# ---- the gate of a town a cataclysm reached, opened again in the middle of the fight
g = simlib.campaign("fight_purpose_gate", cls="warrior", seed=7, location="trading_square")
ws = opened(g)
store = g.store
ws.player.character.level = 12
pools.fill_missing(ws.player.character)
store.save_player(ws.player)
now = ws.minutes
TH = {"id": "cat1", "title": "The Ash Tide", "tier": "cataclysm", "kind": "invasion", "place": "greywood", "antagonist": "the Ash Tide", "stage": 1,
      "status": "active", "stages": [{"description": "Omens.", "effects": [], "signs": "Dogs will not settle."},
                                      {"description": "The host reaches the Wend.", "effects": [], "signs": "Smoke on the north road."}],
      "fallout": {"description": "", "effects": []}, "times": [now - 1440, now, now + 14 * 1440], "made": now - 1440, "groups": ["everyone"],
      "paths": [], "hit_towns": ["parth"], "hits": [[], ["parth"]], "fallen": [], "level": 1, "scope_places": ["parth"], "leaders": [], "boss": "",
      "door": "scene", "summons": "pending", "moment": "", "sender": "", "clues": [], "touched": False, "answered": False, "opened": now}
st = store.load_world_state() or pulse.empty_state(now)
st["threads"] = [TH]
store.save_world_state(st)


def assault(ws) -> dict:
    """The host comes at the gate of the town the player stands in, now: a fresh spawn of the thread and its assault, as the pulse
    queues one, begun by the scene's notices."""
    st = store.load_world_state()
    events.add_spawn(store, ws.world, st, "cat1", "greywood", "wolf", False, ws.minutes - 1440, days=30, level=1, need=99)
    a = {"thread": "cat1", "town": "parth", "stage": 1, "minute": ws.minutes}
    st["assaults"] = [a]
    store.save_world_state(st)
    events.apply_player_events(ws)
    return a


def news_of_parth(store) -> list:
    return [x["text"] for x in (store.load_world_state() or {}).get("news", []) if "Parth" in x["text"]]


assault(ws)
check("(the host at the gate: the fight is begun and its row saved)", begun(ws, store))
ws = opened(g)
rep0 = ws.player.reputation.get("parth", 0)
end(ws, "victory")
st = store.load_world_state()
check("the gate held after a reopen: the town holds, the deed is written and the town thinks more of the player",
      ws.combat is None and "parth" not in st.get("fallen", {}) and any(x["kind"] == "defend" for x in st.get("deeds", []))
      and ws.player.reputation.get("parth", 0) > rep0 and "Parth holds. You kept the gate." in texts(),
      ([x["kind"] for x in st.get("deeds", [])][-3:], rep0, ws.player.reputation.get("parth", 0), texts()[-3:]))

# ---- the gate again: an operation fails in the middle of the fight, the game is closed and opened, and the gate is fled
ws.advance_quiet(60)
assault(ws)
check("(the host at the gate a second time)", begun(ws, store))
real = FightService.round
FightService.round = lambda self, f, intent: (_ for _ in ()).throw(RuntimeError("a fault in the round"))
ws.play("I strike at the nearest of them.")
FightService.round = real
check("an operation that fails in the middle of the gate's fight leaves the fight on, and what it is for in its row",
      bool(ws.line_failed) and ws.combat is not None and row_purpose(store).get("kind") == "gate", (bool(ws.line_failed), row_purpose(store)))
ws = opened(g)
news0 = news_of_parth(store)
end(ws, "fled", "I run for it.")
check("the gate fled after a reopen: the player is told it is lost, and the town's roll runs",
      ws.combat is None and any("The gate is lost." in t for t in texts()) and len(news_of_parth(store)) > len(news0),
      (texts()[-3:], news_of_parth(store)[-2:]))

# ---- a gate fight let go at load: of another shape, by a migration, or a damaged row
ws.advance_quiet(60)
assault(ws)
check("(the host at the gate a third time)", begun(ws, store))
row = json.loads(store.load_combat())
row["fight"]["version"] = 0
store.save_combat(json.dumps(row))
news0 = news_of_parth(store)
ws = opened(g)
told = [t for t in texts() if t in failures.F["fight_let_go"]]
check("a gate fight of another shape let go at load runs the town's roll, as it runs when the fight never began",
      len(told) == 1 and ws.combat is None and store.load_combat() is None and len(news_of_parth(store)) > len(news0), (told, news_of_parth(store)[-2:]))
ws.advance_quiet(60)
assault(ws)
check("(the host at the gate a fourth time)", begun(ws, store))
migrations._v15_effect_rows(store)
news0 = news_of_parth(store)
ws = opened(g)
told = [t for t in texts() if t in failures.F["fight_let_go"]]
check("a gate fight a migration lets go keeps what it was for, and the next load runs the town's roll",
      len(told) == 1 and store.load_combat() is None and len(news_of_parth(store)) > len(news0) and store._kv_text("notice:fight_let_go") is None,
      (told, news_of_parth(store)[-2:]))
store.save_combat("{not a fight")
news0 = news_of_parth(store)
ws = opened(g)
check("a damaged row is let go with nothing handed on", ws.combat is None and store.load_combat() is None and news_of_parth(store) == news0,
      news_of_parth(store)[-2:])
g.close()
saves.drop("fight_purpose_gate")

# ---- what a fight is for has one home: the fight
table = getattr(cs, "PURPOSES", {})
check("every fight begun here carried a kind of purpose the table names, and the table names the four",
      {"dungeon", "camp", "orenna", "gate"} <= SEEN and SEEN <= set(table) | {""} and {"dungeon", "camp", "orenna", "gate"} <= set(table),
      (sorted(SEEN), sorted(table)))
check("...and each names the character it is for by id, the one acting as it began", bool(BY) and all(b == a for b, a in BY), BY)
own, outside, _ = simlib.scene_names()
old = ("dungeon_fight", "camp_fight", "orenna_fight", "assault")
check("no code sets what a fight is for on the scene, no table declares it, and the scene's class holds none of it",
      not [x for x in old if x in own or x in outside or x in actor.ATTRS or x in getattr(actor, "OPENING", {})
           or any(x in vars(k) for k in WorldScene.__mro__)],
      [x for x in old if x in own or x in outside or x in actor.ATTRS or any(x in vars(k) for k in WorldScene.__mro__)])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
