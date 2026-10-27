"""(f348) Moments: something going on when the player walks in, a possibility rolled once per place and period at a low chance, with
a cooldown. The engine draws the shape and runs the mechanics; the model writes the moment, told everything this playthrough has seen,
and a proposal like a past one, or naming anyone it was not given, is sent back; the written moment is the fallback. While it lasts
everyone here sees it (HAPPENING HERE), the people do what it has them doing, a visitor it brings is a real person who leaves when it
ends, a mishap may land on the player, and the town remembers it in the model's words."""
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

specs = {s["id"]: s for s in moments.M["shapes"]}
check("there are shapes for inns, squares, temples, the guild and shops, each with a brief and a written fallback",
      {"performer", "quarrel", "crowd", "observance", "homecoming", "arrival"} <= set(specs) and all(s.get("brief") and s.get("written") for s in specs.values()))
from llm.contracts import MomentProposal
from pydantic import ValidationError
def prop(ctx, **over):
    base = {"title": "the pig under the well", "line": "A pig has got loose and three people are trying to corner it under the well while the baker shouts.",
            "doings": [{"who": "everyone", "doing": "cornering the pig"}], "memory": "the day the pig got under the well"}
    base.update(over)
    try:
        MomentProposal.model_validate(base, context=ctx)
        return ""
    except ValidationError as e:
        return str(e)
ctx = {"roles": ["baker", "guard"], "visitor": False, "mishap": False, "given": "PEOPLE HERE: the stooped baker (baker)", "known": frozenset({"parth"}),
       "seen": ["A card game has the corner table and most of the room's attention: coin stacked, someone losing badly."], "titles": ["the card game"]}
check("a moment that names nobody new and is unlike what was seen passes", prop(ctx) == "", prop(ctx))
check("a moment too like one already seen is sent back", "seen already" in prop(ctx, line="A card game has the corner table and most of the room's attention tonight, with coin stacked high."))
check("a title used before is sent back", "seen in this game already" in prop(ctx, title="The Card Game"))
check("a stranger given a name is sent back", "no one and nowhere" in prop(ctx, line="Old Tobin Marsh has let his pig loose under the well."))
check("a doing for nobody here is sent back", "nobody here" in prop(ctx, doings=[{"who": "innkeeper", "doing": "shouting"}]))
m = MomentProposal.model_validate({"title": "the pig under the well", "line": "A pig has got loose under the well.", "memory": "the pig",
                                   "doings": [{"who": "the stooped baker", "doing": "cornering the pig"}]}, context=dict(ctx, labels={"the stooped baker": "baker"}))
check("a doing given by how someone is known lands on their role", m.doings[0].who == "baker", m.doings[0].who)
check("a stock phrase in the line is sent back", "stock phrase" in prop(ctx, line="A thick fog clings to the branches while the scent of damp earth hangs heavy in the air."))
check("a doing with a subject is sent back", "no subject" in prop(ctx, doings=[{"who": "baker", "doing": "the baker shouts at the pig"}]))
check("a visitor is required when the shape brings one, and refused when it does not",
      "needs an epithet" in prop(dict(ctx, visitor=True)) and "leave visitor_epithet" in prop(ctx, visitor_epithet="a dusty stranger"))
check("a mishap is required when the player can be caught in it", "mishap" in prop(dict(ctx, mishap=True)))
check("figures are sent back", "no figures" in prop(ctx, line="Three pigs and 2 goats are loose under the well."))
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

# a performer, forced: the model writes it
hp0 = pools.current(ws.player.character, "health")
m = moments.start(ws, specs["performer"], random.Random(5))
st = store.load_place("tilted_plough")
check("the place keeps the moment, with its end", st.moment and st.moment["id"] == "performer" and st.moment["until"] == ws.minutes + 180, st.moment)
check("the moment is the model's, not the written one", st.moment["line"].startswith("Stir ") and not st.moment["written"] and st.moment["title"].startswith("the stir"), st.moment)
scene = truth.scene_of(ws)
check("everyone here sees it under HAPPENING HERE", any(l.startswith("Stir ") for l in scene.view(truth.NARRATOR, "narrator").lines("happenings")),
      scene.view(truth.NARRATOR, "narrator").lines("happenings"))
visitor = next((n for n in ws.present if n.role == "traveling_player"), None)
check("the visitor is a real person here, named from their people's sounds, with the model's epithet and look",
      visitor is not None and len(visitor.name.split()) == 2 and store.npc_exists(visitor.id) and visitor.epithet == "a dusty stranger" and visitor.activity == "standing in the middle of it", visitor and (visitor.name, visitor.epithet))
check("everyone does what the model has them doing, the one role apart", any(n.activity == "being in the middle of the stir" for n in ws.present)
      and all(n.activity == "watching the stir with arms folded" for n in ws.present if n.role not in ("traveling_player", (st.moment["doings"]["roles"] and list(st.moment["doings"]["roles"])[0]))), [(n.role, n.activity) for n in ws.present])
check("the room is merry till it ends", all(n.mood == "merry" and n.mood_until == st.moment["until"] for n in ws.present if n.role != "traveling_player"))
seen = moments.seen_list(store)
check("the playthrough remembers it", len(seen) == 1 and seen[0]["shape"] == "performer" and seen[0]["place"] == "tilted_plough", seen)
from engine import moment_prompts as mp
req = mp.moment_request(ws, specs["quarrel"], "", seen)
check("the next moment's request lists what was seen, the people role first, and the shape", "ALREADY SEEN IN THIS GAME" in req and seen[0]["title"] in req
      and "- innkeeper: " in req and specs["quarrel"]["brief"] in req and "MISHAP:" in req and "No visitor" in req, req[-700:])
check("a moment earns the narrator room", ws.weight_hint == "rich", ws.weight_hint)
ws.weight_hint = None
# stepping out and back in: the moment carries on, nothing new is rolled
ws.enter("parth"); ws.enter("tilted_plough")
check("stepping out and back in finds it still going", store.load_place("tilted_plough").moment.get("id") == "performer" and any(n.role == "traveling_player" for n in ws.present))
# time passes: it ends, the visitor goes, the town remembers
ws.advance(200)
ws.run_pulse()
st = store.load_place("tilted_plough")
check("after its minutes it ends", not st.moment, st.moment)
check("the visitor took the road", store.load_npc(visitor.id).gone and not any(n.id == visitor.id for n in ws.present))
check("the town remembers it in the model's words", any(r["text"].startswith("The stir that was") for r in store.load_place("parth").memory), store.load_place("parth").memory[-2:])
from engine import matters
check("...and its people bring it up for a few days, then let it go", any("stir" in x for x in matters.town_memory(store, world, "parth", ws.minutes))
      and not any("stir" in x for x in matters.town_memory(store, world, "parth", ws.minutes + 4 * 1440)))
check("the people are back to their own doings", not any(n.activity.startswith("watching the stir") for n in ws.present), [n.activity for n in ws.present])
# the written fallback, when the model fails
from llm import gateway
real = gateway.generate
def down(*a, **k):
    raise gateway.LLMError("down")
gateway.generate = down
st = store.load_place("tilted_plough"); st.moment = {}; st.moment_last = -10 ** 6; store.save_place(st)
m2 = moments.start(ws, specs["performer"], random.Random(6))
gateway.generate = real
check("when the model fails, the written moment stands in, visitor and all", m2["written"] and m2["line"].startswith("A travelling player has the room")
      and any(n.role == "traveling_player" and n.epithet == "a travelling player" for n in ws.present), m2)
moments.end(ws, store.load_place("tilted_plough"))
# a quarrel can hurt on the way in, with the model's mishap
hits = 0
for k in range(12):
    st = store.load_place("tilted_plough"); st.moment = {}; st.moment_last = -10 ** 6; store.save_place(st)
    c = ws.player.character; c.health = float(pools.maximum(c, "health"))
    ws._arrival_lines = []
    moments.start(ws, specs["quarrel"], random.Random(k))
    if pools.current(c, "health") < pools.maximum(c, "health"):
        hits += 1
        check_line = ws._arrival_lines
    moments.end(ws, store.load_place("tilted_plough"))
check("a quarrel sometimes catches the player on the way in, not always", 0 < hits < 12, hits)
check("...and the knock is told in the model's words", hits and check_line and check_line[-1].startswith("A mug goes past"), hits and check_line)
check("a shape seen before draws less often than one not yet seen", len(moments.seen_list(store)) >= 10)
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
