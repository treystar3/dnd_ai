"""(f348) Moments: something going on when the player walks in, a possibility rolled once per place and period at a low chance, with
a cooldown; while it lasts everyone here sees it (HAPPENING HERE), the people do what it has them doing, a visitor it brings is a real
person who leaves when it ends, an effect may land on the player, and the town remembers it."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 1); simlib.install(stub)
from engine import clock, moments, pools, truth
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
from npc.traits import load_traits
from scenes.world import WorldScene
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

specs = {s["id"]: s for s in moments.M["moments"]}
check("there are moments for inns, squares, temples, the guild and shops", {"music", "brawl", "auction", "rite", "returning_party", "delivery"} <= set(specs))
check("the chance is a possibility, not a habit", all(0 < c <= 0.2 for c in moments.M["chance"].values()) and moments.M["cooldown_hours"] >= 24, moments.M["chance"])

shutil.rmtree("saves/moments_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("moments_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("tilted_plough")
# a quiet arrival: whatever the dice did, the roll is remembered for the period
st = store.load_place("tilted_plough")
check("an arrival rolls once for the place and period", st.moment_roll == f"{clock.day(ws.minutes)}:{clock.period(ws.minutes)}", st.moment_roll)
had = bool(st.moment)
if had:
    moments.end(ws, st)
st = store.load_place("tilted_plough"); st.moment_last = -10 ** 6; store.save_place(st)

# the music, forced
hp0 = pools.current(ws.player.character, "health")
m = moments.start(ws, specs["music"], random.Random(5))
st = store.load_place("tilted_plough")
check("the place keeps the moment, with its end", st.moment and st.moment["id"] == "music" and st.moment["until"] == ws.minutes + 180, st.moment)
scene = truth.scene_of(ws)
check("everyone here sees it under HAPPENING HERE, with the visitor named as they are known", any("has the room" in l and "a travelling player" in l.lower() for l in scene.view(truth.NARRATOR, "narrator").lines("happenings")),
      scene.view(truth.NARRATOR, "narrator").lines("happenings"))
visitor = next((n for n in ws.present if n.role == "traveling_player"), None)
check("the visitor is a real person here, named from their people's sounds", visitor is not None and len(visitor.name.split()) == 2 and store.npc_exists(visitor.id), visitor and visitor.name)
check("the innkeeper pulls ale, the rest dance", any(n.role == "innkeeper" and n.activity.startswith("pulling ale") for n in ws.present)
      and all(n.activity.startswith("dancing") for n in ws.present if n.role not in ("innkeeper", "server", "cook", "traveling_player")), [(n.role, n.activity) for n in ws.present])
check("the room is merry till it ends", all(n.mood == "merry" and n.mood_until == st.moment["until"] for n in ws.present if n.role != "traveling_player"))
check("a moment earns the narrator room", ws.weight_hint == "rich", ws.weight_hint)
ws.weight_hint = None
# stepping out and back in: the moment carries on, nothing new is rolled
ws.enter("parth"); ws.enter("tilted_plough")
check("stepping out and back in finds it still going", store.load_place("tilted_plough").moment.get("id") == "music" and any(n.role == "traveling_player" for n in ws.present))
# time passes: it ends, the visitor goes, the town remembers
ws.advance(200)
ws.run_pulse()
st = store.load_place("tilted_plough")
check("after its minutes it ends", not st.moment, st.moment)
check("the visitor took the road", store.load_npc(visitor.id).gone and not any(n.id == visitor.id for n in ws.present))
check("the town remembers the night", any("travelling player" in r["text"] for r in store.load_place("parth").memory), store.load_place("parth").memory[-2:])
check("the people are back to their own doings", not any(n.activity.startswith("dancing") for n in ws.present), [n.activity for n in ws.present])
# a brawl can hurt on the way in
hits = 0
for k in range(12):
    st = store.load_place("tilted_plough"); st.moment = {}; st.moment_last = -10 ** 6; store.save_place(st)
    c = ws.player.character; c.health = float(pools.maximum(c, "health"))
    moments.start(ws, specs["brawl"], random.Random(k))
    hits += pools.current(c, "health") < pools.maximum(c, "health")
    moments.end(ws, store.load_place("tilted_plough"))
check("a brawl sometimes catches the player on the way in, not always", 0 < hits < 12, hits)
# the cooldown and the town gap
st = store.load_place("tilted_plough"); st.moment_last = ws.minutes; st.moment_roll = ""; store.save_place(st)
n0 = sum(1 for _ in range(1))
ws.enter("parth"); ws.enter("tilted_plough")
check("no new moment inside the cooldown", not store.load_place("tilted_plough").moment)
st = store.load_place("guild_house"); st.moment_roll = ""; store.save_place(st)
ws.enter("guild_house")
check("...nor elsewhere in the town inside the gap", not store.load_place("guild_house").moment)
# the odds over many evenings at the inn, with the cooldowns cleared: a possibility
store.meta.minutes = next(m for m in range(ws.minutes, ws.minutes + 1440, 30) if clock.period(m) == "evening")
got = 0
for k in range(60):
    for pid in ("tilted_plough", "parth"):
        st = store.load_place(pid); st.moment = {}; st.moment_last = -10 ** 6; st.moment_roll = ""; store.save_place(st)
    store.meta.seed = 100 + k
    ws.enter("parth"); ws.enter("tilted_plough")
    if store.load_place("tilted_plough").moment:
        got += 1
        moments.end(ws, store.load_place("tilted_plough"))
check("over sixty evenings at the inn, a moment on some of them and most of them quiet", 2 <= got <= 25, got)
shutil.rmtree("saves/moments_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
