"""(f593) What an act can name, by code (engine/targets.py), and every change it can make (data/rules/changes.yaml). The people here,
the parts of the place the character knows, the things lying here and the things they carry, the roads out, and each live situation
whose trouble is here with its parts, numbered as a situation's ruling numbers them: each looked up again by its code to its record.
Built twice on the same world, the same thing has the same code; what is gone, unseen, carried by someone else, or a situation whose
trouble lies elsewhere, is not listed. The list of changes holds the situation ruling's words on the kinds they land on there, and the
startup check refuses a change on no kind, a kind that is none, or a situation word gone missing.
Run: python tools/sim/targets_593_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
simlib.quiet_console()
from engine import features, objects, pulse, retrieval, situation_parts, situations, targets
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("targets_593", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
rows = retrieval.people_in_town(store, world, town)
road = next(rid for rid in sorted(world.roads) if town in (world.roads[rid].from_, world.roads[rid].to))


def situation(tid: str, place: str, title: str) -> dict:
    st = store.load_world_state() or {}
    for k, v in pulse.empty_state(ws.minutes).items():
        st.setdefault(k, v)
    th = {"id": tid, "title": title, "tier": "rare", "place": place, "times": [ws.minutes, ws.minutes + 9 * 1440], "status": "active",
          "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Trouble.", "effects": []}],
          "kind": "politics", "groups": ["everyone"]}
    st.setdefault("threads", []).append(th)
    near = pulse.town_of(world, place)
    people = (retrieval.people_in_town(store, world, near) + rows)[:2]   # a far town not yet peopled takes this town's
    prop = {"people": [{"who": people[0].id, "stake": "blocks", "want": "left_alone"}, {"who": people[1].id, "stake": "harmed", "want": "safety"}],
            "evidence": [{"label": "a torn ledger page", "holder": place, "points_to": people[0].id, "certainty": "sure"}]}
    acc, _ = situations.check(SituationParts.model_validate(prop), store, world, "rare", random.Random(7), town=near, ways=False,
                              now=ws.minutes, players=(ws.acting,))
    situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
    store.save_world_state(st)
    return th


with ws.operation("test", "set the scene") as setup_op:
    here = situation("th593", "trading_square", "The occupied square")
    far_town = next(t for t in sorted(world.places) if world.places[t].type in ("town", "city", "village") and t != town
                    and not ({t} & {world.roads[r].from_ for r in world.roads if world.roads[r].to == town}))
    away = situation("th593far", far_town, "Trouble far away")
    features.ensure(ws, "trading_square")
    kind = features.kinds_here(world.places["trading_square"])[0]
    well = features.register(ws, "trading_square", "the old well", kind, "a mossy well in the corner", "known", "authored")
    unseen = features.register(ws, "trading_square", "the cellar door", kind, "a door under the steps", "unseen", "authored")
    rope = objects.make(store, "trading_square", "a rope ladder", "frayed", minute=ws.minutes)
    sack = objects.make(store, "trading_square", "a grain sack", "", minute=ws.minutes)
    objects.take(store, sack, ws.acting, ws.minutes)
    theirs = objects.make(store, "trading_square", "a lantern", "", minute=ws.minutes)
    objects.take(store, theirs, "another_character", ws.minutes)
    gone = objects.make(store, "trading_square", "a broken cup", "", minute=ws.minutes)
    objects.change(store, gone, "gone", ws.minutes)
    for e in features.here(store, "trading_square")[:1]:
        if e.state == "unseen":
            from engine import entities
            entities.move(store, e, "known", ws.minutes)
check("the scene is set", setup_op.state == "committed", (setup_op.state, getattr(setup_op, "error", None) or getattr(setup_op, "failure", None)))
ws.reread_here()
if not ws.present:
    ws.present = list(ws.residents[:2])

T = targets.targets_for(ws, ws.acting)
again = targets.targets_for(ws, ws.acting)
check("the prompt's lines are one per target, each opening on its code", [l.split(" ", 1)[0] for l in T.lines()] == T.codes())
check("built twice on the same world, the same things have the same codes", T.rows == again.rows and len(T.rows) >= 6, len(T.rows))
kinds = {t.code[0] for t in T.rows}
check("the people here, the parts of the place, the things, the roads out and a situation are all listed", {"p", "f", "o", "r", "s"} <= kinds, kinds)
people = [t for t in T.rows if t.kind == "person" and t.code.startswith("p")]
check("...each person here, looked up to their record", [t.ref for t in people] == [n.id for n in ws.present], (people, [n.id for n in ws.present]))
parts = [t for t in T.rows if t.kind == "part"]
known = [e for e in features.here(store, "trading_square") if e.state != "unseen"]
check("...each part of the place the character knows, never one unseen", {t.ref for t in parts} == {e.ref for e in known}
      and well.ref in {t.ref for t in parts} and unseen.ref not in {t.ref for t in parts}
      and all(store.load_entity(t.ref).state != "unseen" for t in parts), (parts, known))
things = {t.ref: t for t in T.rows if t.kind == "object"}
check("...the things lying here and those the character carries", rope.ref in things and sack.ref in things and "carried by you" in things[sack.ref].line,
      things)
check("...never one carried by someone else, nor one gone", theirs.ref not in things and gone.ref not in things)
check("...the roads out of the town", any(t.kind == "road" and t.ref == road for t in T.rows), [t for t in T.rows if t.kind == "road"])
sits = [t for t in T.rows if t.kind == "situation"]
check("a situation whose trouble is here is listed; one whose trouble is elsewhere is not", [t.ref for t in sits] == ["th593"], sits)
th = next(x for x in store.load_world_state()["threads"] if x["id"] == "th593")
lines = situation_parts.parts_lines(store, world, th, ws.acting)
mine = [t for t in T.rows if t.code.startswith("s1.")]
check("...its parts numbered as its ruling numbers them, each looked up to the part", [t.code for t in mine] == [f"s1.{i}" for i in range(1, len(lines) + 1)]
      and [t.ref for t in mine] == [f"th593#{i}" for i in range(len(lines))]
      and all(t.line.rsplit(" (p", 1)[0] in l for t, l in zip(mine, lines)), (mine, lines))
both = [t for t in mine if t.who and t.who in {p.ref for p in people}]
check("a person who is both here and a situation's part is one person: the part names their code and carries their id",
      both and all(f"({next(p.code for p in people if p.ref == t.who)})" in t.line for t in both), [(t.code, t.who, t.line) for t in mine])
check("...each part with its kind of target (a person, a piece of evidence)", {t.kind for t in mine} <= {"person", "evidence", "condition", "resource", "tie"}
      and "person" in {t.kind for t in mine} and "evidence" in {t.kind for t in mine}, [t.kind for t in mine])
check("a code is looked up, written either way ('o1', 'O1: the rope ladder')", T.get("o1") is not None and T.get("O1: the rope ladder") == T.get("o1")
      and not T.exists("o99") and T.kind_of("s1") == "situation")
with ws.operation("test", "a change") as op2:
    objects.change(store, store.load_entity(rope.ref), "broken", ws.minutes)
changed = targets.targets_for(ws, ws.acting)
before = {t.ref: t for t in T.rows}
after = {t.ref: t for t in changed.rows}
check("a thing's state is on its target, so a changed thing is a changed circumstance", op2.state == "committed"
      and before[rope.ref].state != after[rope.ref].state and "broken" in after[rope.ref].state
      and all(after[r].state == before[r].state for r in before if r != rope.ref and r in after), (before[rope.ref].state, after[rope.ref].state))
check("...and its tags, for what it can be used as", "climbable" in after[rope.ref].tags)
ws.player.party = [{"id": "hire_brena", "name": "Brena", "role": "sellsword"}]
with_party = targets.targets_for(ws, ws.acting)
ws.player.party = []
check("the character's companions are named too", any(t.code == "c1" and t.ref == "hire_brena" and "Brena" in t.line for t in with_party.rows))
check("no line names a place by its id", not any("trading_square" in t.line for t in T.rows), [t.line for t in T.rows if "trading_square" in t.line])
other = targets.targets_for(ws, "another_character")
check("built for another character: their things carried, never the first one's", any(t.ref == theirs.ref for t in other.rows)
      and not any(t.ref == sack.ref for t in other.rows))

# ---- the changes
C = targets.CH
check("a change lands on the kinds the list gives it, and no other", targets.lands_on("broken", "object") and targets.lands_on("broken", "tie")
      and not targets.lands_on("broken", "person") and targets.lands_on("state", "part") and not targets.lands_on("believes", "object"))
S = situations.S
check("every word of the situation ruling is a change, on the kinds it lands on there",
      all(set(r["kinds"]) <= set(C["changes"][w]["lands_on"]) for w, r in S["rulings"]["changes"].items()))
check("the startup check passes as shipped", targets.problems() == [])
broken = {"kinds": C["kinds"], "changes": dict(C["changes"], lifted={"lands_on": ["object"]}, smashed={"lands_on": ["vase"]}, odd={})}
broken["changes"].pop("believes")
p = targets.problems(broken)
check("...and refuses a situation word missing, one on other kinds than its own, a kind that is none, and a change on nothing",
      any("'believes' is missing" in x for x in p) and any("changes.lifted" in x for x in p) and any("'vase'" in x for x in p)
      and any("changes.odd" in x for x in p), p)
extra = {"kinds": C["kinds"] + ["situation"], "changes": dict(C["changes"], charmed={"lands_on": ["person"]})}
q = targets.problems(extra)
check("...a word on a person or a part the situation ruling does not have, and a change landing on a whole situation",
      any("changes.charmed" in x for x in q) and any("whole situation" in x for x in q), q)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
