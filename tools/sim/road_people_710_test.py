"""(f710) The people a road happening shows are people of the game (the owner, 2026-11-16: docs/design/22_road_people_f710.md; found
in the third blind play: docs/play/2026-11-16_blind_play_journal.md). On the King's Pass a happening bearing on a matter showed two
dazed men under a lean-to muttering "We dig. At night."; it was rolled a sight, so the walk went on, and when f709 walked back to it
`I crouch beside the two men and ask them where it is they dig at night.` went to my own archer: the men were words in a passage.
Held here: a happening that bears on a matter and is rolled a sight is a meeting: the walk stops and one person is there (the writer's
role, else the wanderer); that person holds the matter's next clue (a knows row, f483), and saying it marks it found; the clue the
scene shows is found on the road as before; walking on, the person goes with the stop and the clue stays unfound for the town; a sight
with no matter still goes on, kept, its writer told no one in it is met; a find with a matter stays a find; road.yaml matter_meets
false gives the old way. Tested on a second matter as well, whose shown clue is a thing seen (a signpost).
Run: python tools/sim/road_people_710_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from llm.contracts import RoadEvent
from engine import matters, memory
import scenes.road_actions as ra

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("road_people_710", seed=5, location="parth")
ws, store = g.scene, g.store
world = ws.world
road = next(r for r in world.roads.values() if r.from_ == "parth" and r.to in world.places and world.travel_minutes(r.from_, r.to) >= 180)
a, b = road.from_, road.to
saved = {k: ra.R[k] for k in ("hostile", "kinds", "matter_meets")}
ra.R["hostile"] = 0
prompts = []
EV = {}
def gen(task, system, user, *x, **k):
    prompts.append(user)
    return EV["ev"].model_copy(deep=True)
real_gen = ra.generate
ra.generate = gen
real_chance = matters.D.get("road", {}).get("chance", 0.5)
matters.D.setdefault("road", {})["chance"] = 1.0


def thread(tid, title, clues):
    th = {"id": tid, "title": title, "place": a, "status": "active", "groups": ["everyone"], "sender": "", "opened": ws.minutes,
          "stage": 0, "stages": [{"description": f"{title}: something is wrong on the road.", "effects": []}], "paths": [],
          "clues": [{"text": c, "holder": "", "npc": "", "found": False} for c in clues], "times": [ws.minutes, ws.minutes + 9000]}
    state = store.load_world_state() or {}
    state["threads"] = [t for t in state.get("threads", []) if t["id"] != tid] + [th]
    state.setdefault("history", [])
    store.save_world_state(state)


def happen(kind, ev, meets=True):
    if ws.player.road:
        ws.leave_road(a)
    ws.enter(a)
    ra.R["kinds"], ra.R["matter_meets"] = {kind: 1}, meets
    EV["ev"] = ev
    prompts.clear()
    return ws.road_event([a, b], a, b, world.travel_minutes(a, b), 0.5, "We walk on.", [], walked=120)


def th_of(tid):
    return next(t for t in store.load_world_state()["threads"] if t["id"] == tid)


thread("dig", "The voice from the Greywood", ["We dig. At night. I know where.", "They dig under the old chapel by the ford."])
men = RoadEvent(title="The Echo of the Greywood", journey="You walk on.", kind="meeting", meets_role="wanderer",
                scene="Two dazed men sit under a lean-to, muttering: 'We dig. At night. I know where.'", detail="two dazed men")
out = happen("sight", men)
here = [n for n in ws.present if n.role == "wanderer"]
check("a matter's happening rolled a sight stops the walk, with one person there", out == "stopped" and ws.player.road and len(here) == 1,
      (out, [(n.id, n.role) for n in ws.present]))
th = th_of("dig")
check("...the clue the scene shows is found on the road, as before", th["clues"][0]["found"] and th["clues"][0]["by"] == "on the road", th["clues"])
knows = [r for r in memory.records(store, here[0].id) if r["kind"] == "knows"] if here else []
check("...and the person met holds the matter's next clue as theirs to tell", [r["about"] for r in knows] == ["thread:dig:1"]
      and knows[0]["text"].startswith("They dig under the old chapel"), knows)
check("...which their talk is given to know", here and [f.id for f in matters.clue_facts(store, world, store.load_npc(here[0].id))] == ["clue:dig:1"])
check("...and saying it marks it found, by them", here and matters.mark_found(ws, store.load_npc(here[0].id), ["clue:dig:1"]) and th_of("dig")["clues"][1]["found"],
      th_of("dig")["clues"])
check("the writer is told someone is here, met, never a passing sight", prompts and "Someone is here" in prompts[-1], prompts[-1][-300:] if prompts else "")

thread("sign", "Who rules Parth", ["A fresh signpost: BY ORDER OF THE SHEPHERD, ALL PASSAGE MUST BE REGISTERED.", "The Shepherd's men camp at the mill."])
post = RoadEvent(title="The Shepherd's Sign", journey="You walk on.", kind="meeting", meets_role="",
                 scene="A fresh signpost by the bend: BY ORDER OF THE SHEPHERD. A traveller leans on it, watching you read.", detail="a traveller")
out = happen("sight", post)
here = [n for n in ws.present if n.role == ra.R["stop_roles"]["meeting"]]
check("a second matter, its clue a thing seen: the walk stops, the writer naming no role gives the wanderer", out == "stopped" and len(here) == 1,
      (out, [(n.id, n.role) for n in ws.present]))
held = [r["about"] for r in memory.records(store, here[0].id) if r["kind"] == "knows"] if here else []
check("...who holds the next clue of that matter", held == ["thread:sign:1"], held)
who = here[0].id if here else ""
ws.leave_road(b)
ws.enter(b)
check("walking on, the person goes with the stop, and the clue they did not tell stays unfound for the town",
      who not in [n.id for n in ws.present] and not th_of("sign")["clues"][1]["found"] and not th_of("sign")["clues"][1]["npc"],
      th_of("sign")["clues"])

thread("debt", "The fisher's debt", ["Nets cut on the shore at night.", "Everyone owes everyone here. I'm only the one who asked to be paid."])
state = store.load_world_state()
next(t for t in state["threads"] if t["id"] == "debt")["clues"][1]["holder"] = "fisher"
store.save_world_state(state)
met = RoadEvent(title="A traveller", journey="You walk on.", kind="meeting", meets_role="wanderer",
                scene="A traveller sits by the road mending a net: 'Nets cut on the shore at night.'", detail="a traveller")
out = happen("meeting", met)
here = [n for n in ws.present if n.role == "wanderer"]
rows = [r for r in memory.records(store, here[0].id) if r["kind"] == "knows"] if here else []
check("anyone met at a stop a matter's happening made holds its next clue, a meeting rolled as one too", out == "stopped" and len(rows) == 1, rows)
check("...and a clue written in another's voice (the fisher's 'I') is held as heard, quoted and said whose, never as their own",
      rows and rows[0]["text"].startswith("Something heard from a fisher: \"Everyone owes everyone here. I'm only")
      and rows[0]["source"] == "heard", rows)
check("...still theirs to tell, and found when told", here and matters.mark_found(ws, store.load_npc(here[0].id), ["clue:debt:1"])
      and th_of("debt")["clues"][1]["found"], th_of("debt")["clues"])

from engine import retrieval
town = retrieval.people_in_town(store, world, "parth")
speaker = town[0] if town else None
thread("rope", "The cut rope", ["A bell rope hangs cut at the chapel.", "I saw a cut rope myself, and it points to the miller.", "Ask the ghost."])
state = store.load_world_state()
rope = next(t for t in state["threads"] if t["id"] == "rope")
rope["clues"][1]["npc"] = speaker.id if speaker else ""
rope["clues"][2]["holder"] = "ghost_of_the_mill"
store.save_world_state(state)
out = happen("meeting", met)
here = [n for n in ws.present if n.role == "wanderer"]
rows = [r for r in memory.records(store, here[0].id) if r["kind"] == "knows" and r["about"].startswith("thread:rope")] if here else []
check("a situation's evidence, in the words of the particular person it names, is held as heard from their trade, never as one's own",
      speaker and rows and rows[0]["text"].startswith(f"Something heard from {'an' if speaker.role[:1] in 'aeiou' else 'a'} "
                                                      f"{speaker.role.replace('_', ' ')}: \"I saw a cut rope myself") and rows[0]["source"] == "heard",
      (speaker and speaker.role, rows))
thread("ghost", "The mill ghost", ["Lights in the old mill.", "Ask the ghost."])
state = store.load_world_state()
next(t for t in state["threads"] if t["id"] == "ghost")["clues"][1]["holder"] = "ghost_of_the_mill"
store.save_world_state(state)
out = happen("meeting", met)
here = [n for n in ws.present if n.role == "wanderer"]
rows = [r for r in memory.records(store, here[0].id) if r["kind"] == "knows" and r["about"] == "thread:ghost:1"] if here else []
check("...and a trade the world does not know is 'someone'", rows and rows[0]["text"].startswith("Something heard from someone: \"Ask the ghost."), rows)

plain = RoadEvent(title="A far caravan", journey="You walk on.", kind="sight", scene="Far off, a caravan crawls along the ridge.")
state = store.load_world_state(); state["threads"] = []; store.save_world_state(state)
out = happen("sight", plain)
check("a sight with no matter goes on, kept as a landmark", out == "go" and any(m["title"] == "A far caravan" for m in ws.landmarks()), out)
check("...its writer told that no one in it is met or spoken with", prompts and "no one in it is met" in prompts[-1], prompts[-1][-300:] if prompts else "")

thread("find", "The lost ledger", ["A ledger page, torn, in the ditch.", "The clerk burned the rest."])
lost = RoadEvent(title="A torn page", journey="You walk on.", kind="find", scene="A torn page lies in the ditch.", detail="a page")
out = happen("find", lost)
check("a find with a matter stays a find (a stop, and nobody made for it)", out == "stopped" and ws.player.road.get("kind") == "find"
      and not any(n.role == "wanderer" for n in ws.present), (out, ws.player.road and ws.player.road.get("kind")))

thread("old", "The old way", ["One.", "Two."])
out = happen("sight", men.model_copy(update={"kind": "sight"}), meets=False)
check("road.yaml matter_meets false gives the old way: the sight goes on", out == "go", out)

ra.generate = real_gen
matters.D["road"]["chance"] = real_chance
ra.R.update(saved)
g.close()
shutil.rmtree("saves/road_people_710", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
