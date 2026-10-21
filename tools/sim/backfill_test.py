"""Arriving somewhere new makes only a few residents before the scene is described (on shift and useful ones first); the rest are
made on a background thread while the player reads, and are never made twice."""
import sys, random, shutil, time, threading
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
uc.say = lambda t, s="": None
uc.narrate = lambda t: None
uc.note = lambda m, *a, **k: None
from engine import clock
from npc import life, backfill
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
CALLS = []
real = stub.a_ResidentSet
def counted(u, k):
    CALLS.append(u.count("slot "))
    time.sleep(0.2)
    return real(u, k)
stub.a_ResidentSet = counted

def fresh(name, minutes):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    st = CampaignStore.open_or_create(name)
    st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = minutes; st.save_meta()
    ch, _ = simlib.make_character("warrior", random.Random(2))
    st.save_player(PlayerState(character=ch, location="parth"))
    w = WorldScene(st, world, load_traits(), st.load_player())
    config.TURN_LOG_PATH = f"saves/{name}/turns.jsonl"
    w.narrate = lambda e, t="": None
    w.narrate_with = lambda *a, **k: None
    w.show_exits = lambda *a, **k: None
    return st, w

life.FIRST_BATCH = 4
st, w = fresh("backfill_test", 1800)
w.enter("guild_house")
want = sum(world.places["guild_house"].residents.values())
check("arrival makes only the first few", len(w.residents) == 4 and CALLS == [4], (len(w.residents), CALLS))
roles = {n.role for n in w.residents}
check("the people who serve are among them", "guild_clerk" in roles, roles)
check("the rest are still missing", life.unfinished(st, world, "guild_house"))
CALLS.clear()
t1 = time.time(); w.start_backfill(); took = time.time() - t1
check("the rest start in the background without waiting", backfill.pending("guild_house") and took < 0.1, took)
check("a second start does nothing while one runs", backfill.start(st, world, w.catalog, "guild_house") is False)
t0 = time.time()
while backfill.pending() and time.time() - t0 < 5:
    w.apply_backfill(); time.sleep(0.05)
check("the job was applied to the scene", len(w.residents) == want, (len(w.residents), want))
check("with one call for the missing people", CALLS == [want - 4], CALLS)
names = [n.name for n in w.residents]
check("nobody is made twice", len(names) == len(set(names)) and not life.unfinished(st, world, "guild_house"))
check("nothing more starts", w.start_backfill() is None and not backfill.pending())

# leaving and coming back while the job is running waits for it and makes nobody twice
st2, w2 = fresh("backfill_test2", 1800)
w2.enter("guild_house"); CALLS.clear()
w2.start_backfill()
w2.enter("guild_house")
check("re-entering settles the running job instead of asking again", CALLS == [want - 4] and len(w2.residents) == want, (CALLS, len(w2.residents)))

# at night the people on shift do not exist, so whoever is made first is simply the useful ones
st3, w3 = fresh("backfill_test3", 60)
w3.enter("parth")
first = [n.role for n in w3.residents]
check("a big place gets the same small first batch", len(first) == 4, first)
check("and fills in later", (w3.start_backfill(), [w3.apply_backfill() or time.sleep(0.05) for _ in range(60) if backfill.pending()])[0] is None
      and len(w3.store.load_place("parth").residents) == sum(world.places["parth"].residents.values()))

# the default does everything at once, as every other caller expects
life.FIRST_BATCH = None
st4, w4 = fresh("backfill_test4", 1800)
CALLS.clear()
w4.enter("guild_house")
check("without the split, everyone is made in one call", len(w4.residents) == want and CALLS == [want], CALLS)

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
