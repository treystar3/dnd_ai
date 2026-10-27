"""(f352) Routines: some townspeople have one period of the day at one other place in their town, drawn by the engine and kept nowhere. In
that period they are away from their work and present at the routine place doing what people do there; their neighbours can say where they
are; walking to them goes where they are."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import clock, pulse, routines
from npc import life
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
check("the rules are data: a chance, role overrides, slots by period and kind of place, doings by kind of place",
      routines.problems({p.type for p in world.places.values()}, set(clock.PERIOD_NAMES), set(world.roles)) == [] and routines.chance("innkeeper") == 0 and 0 < routines.chance("smith") < 1,
      routines.problems({p.type for p in world.places.values()}, set(clock.PERIOD_NAMES), set(world.roles)))

class Row:
    def __init__(self, id, role, location): self.id, self.role, self.location, self.away_until = id, role, location, -1
r = routines.routine_for(world, 3, Row("n1", "smith", "parth"))
check("a routine is the same every time it is asked for", r == routines.routine_for(world, 3, Row("n1", "smith", "parth")))
hits = [routines.routine_for(world, s, Row("n1", "smith", "parth")) for s in range(200)]
check("about as many smiths have one as the chance says, and every routine is a period at a place of the town that is not their work",
      0.3 < sum(1 for h in hits if h) / 200 < 0.6 and all(h["when"] in clock.PERIOD_NAMES and h["place"] != "parth" and pulse.town_of(world, h["place"]) == "parth" for h in hits if h), sum(1 for h in hits if h))
class Held(Row):
    def __init__(self, *a): super().__init__(*a); self.protected = True
check("someone the story holds in place never has one", all(routines.routine_for(world, s, Held("n9", "smith", "parth")) is None for s in range(50)))
check("an innkeeper never has one; nobody in the wild does", all(routines.routine_for(world, s, Row("n2", "innkeeper", "tilted_plough")) is None for s in range(50))
      and routines.routine_for(world, 3, Row("n3", "hunter", next(p.id for p in world.places.values() if p.danger))) is None)
one = next((s, h) for s, h in enumerate(hits) if h)
seed, rt = one
smith = Row("n1", "smith", "parth")
at = next(m for m in range(0, 1440, 15) if clock.period(m) == rt["when"])
off = next(m for m in range(0, 1440, 15) if clock.period(m) != rt["when"] and 7 <= clock.hour(m) < 18)
check("in its period they are at the routine place and away from their work; outside it, at their work",
      routines.where_now(world, seed, smith, at) == rt["place"] and routines.away(world, seed, smith, at) and routines.where_now(world, seed, smith, off) == "parth")
check("the routine is told the way a neighbour says it", routines.usual_line(world, seed, smith).startswith("at ") and ("most" in routines.usual_line(world, seed, smith) or "days" in routines.usual_line(world, seed, smith)), routines.usual_line(world, seed, smith))
d1 = routines.doing_at("inn", random.Random(1)); d2 = routines.doing_at("inn", random.Random(1), taken=[d1])
check("a routine doing is what people do at that kind of place, and not one already taken", d1 != d2 and d1 in routines.R["doings"]["inn"] and routines.doing_at("mountains", random.Random(1)) in routines.R["doings"]["default"])

# ---- in a scene
shutil.rmtree("saves/routines_test", ignore_errors=True)
store = CampaignStore.open_or_create("routines_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
console.narrate = lambda text: None
console.note = lambda text: None
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.player.mentor["never"] = True
ws.enter("parth"); ws.enter("tilted_plough"); ws.enter("parth_temple"); ws.enter("parth")
from engine import retrieval
rows = retrieval.people_in_town(store, world, "parth")
with_routine = [(r, routines.routine_for(world, 3, r)) for r in rows]
with_routine = [(r, rt) for r, rt in with_routine if rt]
check("some of Parth's people have a routine", len(with_routine) >= 2, len(with_routine))
row, rt = with_routine[0]
at = next(m for m in range(0, 1440 * 2, 15) if clock.period(m) == rt["when"] and m > ws.minutes)
store.meta.minutes = at
ws.enter(rt["place"])
check("in that period they are present at their routine place, on their routine, doing what people do there",
      any(n.id == row.id for n in ws.present) and row.id in ws._routine_here and next(n.activity for n in ws.present if n.id == row.id) in routines.R["doings"].get(world.places[rt["place"]].type, routines.R["doings"]["default"]),
      ([n.id for n in ws.present], ws._routine_here, rt))
ws.enter(row.location)
check("...and not at their work", not any(n.id == row.id for n in ws.present))
off = next(m for m in range(at, at + 1440, 15) if clock.period(m) != rt["when"] and clock.in_hours(m, world.roles[row.role].hours))
store.meta.minutes = off
ws.enter(row.location)
check("...and back at their work outside it", any(n.id == row.id for n in ws.present), (clock.period(off), [n.id for n in ws.present]))
here, known = life.social_circle(next(n for n in ws.present if n.id != row.id) if len(ws.present) > 1 else ws.residents[0], store, world)
check("their neighbours can say where they usually are", any(row.name in k and "most" in k for k in known) or any(row.name in h for h in here), known[:4])
store.meta.minutes = at
ws.enter("parth")
notes = []
console.note = lambda text: notes.append(text)
ws.go_to_person(row, f"I go and find {row.name}")
check("walking to someone goes where they are at this hour", ws.player.location == rt["place"] and ws.last_spoken == row.id, (ws.player.location, notes))
shutil.rmtree("saves/routines_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
