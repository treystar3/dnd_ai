"""(f334) An inner life for everyone, without the model: a person born into a town has the circles they hear news from and - for the
share their traits allow - a goal in the engine's words, or the clock by which the drift hands them one later; the first conversation
keeps that goal's meaning; a goal nobody watched runs its course into the town's memory and a mood; and a mood shows on the person."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import ui.console as uc
uc.note = lambda m, *a, **k: None; uc.narrate = lambda t: None; uc.say = lambda *a, **k: None; uc.wait = lambda *a, **k: None
from storage.campaign import CampaignStore, PlayerState
from npc import life
from npc.traits import load_traits
from world.loader import load_world
from engine import drift, matters, pulse, truth
from scenes.world import WorldScene
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/inner_life_test", ignore_errors=True)
st = CampaignStore.open_or_create("inner_life_test")
st.meta.seed = 5; st.meta.minutes = 9 * 60; st.save_meta()
world = load_world(); catalog = load_traits()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="trading_square"))
now = st.meta.minutes
DAY = 1440
D = drift.rules()
V = D["motives"]

# ---- born with the engine's share
people = life.populate_place(st, world, "trading_square", catalog)
check("a town's people are made", len(people) >= 3, len(people))
check("every one of them hears the news of their circles from birth", all(n.knowledge_groups and "everyone" in n.knowledge_groups for n in people), [(n.name, n.knowledge_groups) for n in people][:3])
with_goal = [n for n in people if n.motive]
without = [n for n in people if not n.motive]
check("the share their traits allow have a goal in the engine's words, dated", all(n.motive_since == now and n.tier == "background" for n in with_goal), [(n.name, n.motive, n.motive_since) for n in with_goal][:3])
check("...and the rest have the clock by which the drift may hand them one", all(n.motive_done_at == now for n in without), [(n.name, n.motive_done_at) for n in without][:3])
seeds = {s.format(role=n.role.replace("_", " "), town="Parth") for n in people for pool in V["seeds"].values() for s in pool}
check("a goal comes from the phrase table, with the role and the town filled in", all(n.motive in seeds for n in with_goal), [n.motive for n in with_goal][:3])
check("the same seed gives the same people the same goals", life.inner_life(people[0], st, world) is None and all(st.load_npc(n.id).motive == n.motive for n in people))

# ---- the first conversation keeps the goal's meaning
n = with_goal[0] if with_goal else people[0]
if not n.motive:                                              # the roll may leave a small town without one: give this person the engine's goal by hand
    n.motive, n.motive_since, n.motive_done_at = "to be the richest farmer in Parth", now, -1
    st.save_npc(n)
goal = n.motive
life.promote(n, st, world, catalog)
check("promotion keeps the engine's goal when the model restates nothing, and makes them known", n.motive == goal and n.tier == "known" and n.motive_since == now, (n.motive, n.tier))

# ---- a goal nobody watched runs its course
state = pulse.empty_state(now)
quiet = next((n for n in people if n.tier == "background" and n.motive and n.id != n.id), None)
others = [x for x in people if x.tier == "background" and x.id != n.id]
if quiet is None and others:                                  # the one just promoted is known now; another, by hand
    quiet = others[0]; quiet.motive = "to be the richest farmer in Parth"; quiet.motive_since = now; quiet.motive_done_at = -1
    st.save_npc(quiet)
check("there is someone whose goal nobody watched", quiet is not None)
if quiet is not None:
    quiet.motive_since = now - V["lasts_days"] * DAY - 1
    st.save_npc(quiet)
    drift.catch_up(st, world, state, now + 2 * DAY, random.Random(1))
    st.save_world_state(state)
    q = st.load_npc(quiet.id)
    remembered = matters.town_memory(st, world, "trading_square", now + 2 * DAY)
    check("it ends without a model call: the goal is gone, the cooldown runs, a mood is left", q.motive == "" and q.motive_done_at > 0 and q.motive_since == 0 and q.mood and q.mood_until > now, (q.motive, q.motive_done_at, q.mood))
    check("...and the town remembers it by name", any(q.name in line for line in remembered), remembered[-2:])
    drift.catch_up(st, world, state, now + 2 * DAY + (V["cooldown_days"] + 40) * DAY, random.Random(2))
    st.save_world_state(state)
    q = st.load_npc(quiet.id)
    check("in time the drift may hand them another", q.motive_done_at == -1 or q.motive_done_at > now + 2 * DAY, (q.motive, q.motive_done_at))

# ---- a mood shows on the person
ws = WorldScene(st, world, catalog, st.load_player())
mood_npc = people[-1]
mood_npc.mood, mood_npc.mood_until = "uneasy since the wolves came down", now + 6 * DAY
st.save_npc(mood_npc)
ws.present = [mood_npc]
shown = next(p for p in truth._present_people(ws) if p.id == mood_npc.id)
check("a mood shows on the person as they are seen, not as a note to the interpreter", "Lately: uneasy since the wolves came down" in shown.desc and "uneasy" not in shown.note, (shown.desc[-60:], shown.note))

shutil.rmtree("saves/inner_life_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
