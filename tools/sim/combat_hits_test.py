"""Every blow is recorded with how it was worked out; the figures land in the narration; the pane data is complete."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from scenes import combat_scene as cs
from npc.traits import load_traits
from engine import combat, money
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/combat_hits_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("combat_hits_test")
store.meta.seed = 4; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 8
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("parth")
me = combat.fighter_from_character(ws.player.character)
foes = [combat.fighter_from_creature(world.bestiary[b], 8, "normal", f"e{i}", name=f"{b} {i + 1}") for i, b in enumerate(["wolf", "wolf"])]
fight = combat.Combat(fighters=[me] + foes, place="parth")
fight.record = True
rng = random.Random(5)

landed = 0
for rnd in range(6):
    fight.hits, fight.story = [], []
    if not fight.enemies():
        break
    combat.act_attack(fight, fight.player, fight.enemies()[0], rng)
    for e in list(fight.enemies()):
        combat.enemy_turn(fight, e, rng)
    combat.finish_round(fight, rng)
    for h in fight.hits:
        check(f"round {rnd + 1} blow has an id, tag and figure", h["id"] and h["tag"] and h["figure"], h)
        if h["outcome"] in ("hit", "crit", "graze"):
            landed += 1
            b, steps = h["base"], h["steps"]
            prod = 1.0
            for _, f in steps:
                prod *= f
            raw = b["base"] * prod * (1 + b["pct"] / 100) * b["variance"] * b["magic"]
            check("steps multiply out to the raw damage", abs(raw - b["total"]) <= max(0.5, b["total"] * 0.02), (raw, b["total"], steps))
            d = h["defence"]
            check("defence turns raw into the taken figure", abs(d["before"] - b["total"]) <= 0.2 and d["after"] <= d["before"] + 0.2, d)
            check("final is what was dealt", abs(h["final"] - d["after"]) <= 1 or h["extras"] or fight.get(h["dfn"] and "") is None, (h["final"], d["after"], h["extras"]))
            check("figure shows the dealt number", str(h["final"]) in h["figure"])
        # the tag is in the story exactly once
        check("tag appears in the story", sum(f"[{h['tag']}]" in s for s in fight.story) == 1, (h["tag"], fight.story))
check("some blows landed", landed >= 2, landed)
check("hits are saved with the fight", combat.Combat(**fight.model_dump()).record is True)

# unrecorded fights (the odds simulation) keep no records and no tags
sim = combat.Combat(fighters=[combat.fighter_from_character(ws.player.character), combat.fighter_from_creature(world.bestiary["wolf"], 8, "normal", "x", name="wolf")], place="p")
combat.act_attack(sim, sim.player, sim.enemies()[0], random.Random(1))
check("no records when not recording", sim.hits == [] and all("[h" not in s for s in sim.story))

# ---- figures in the narration ----
hits = [{"id": "a-1-1", "tag": "h1", "figure": "(14 damage)"}, {"id": "a-1-2", "tag": "h2", "figure": "(miss)"}, {"id": "a-1-3", "tag": "h3", "figure": "(critical, 30 damage)"}]
t = cs.place_figures("You carve the beast. [h1] It lunges and misses. [h2]", hits, window=False)
check("tags become figures", t == "You carve the beast. (14 damage) It lunges and misses. (miss) (critical, 30 damage)", t)
t = cs.place_figures("You strike (h1) and it dies [H3].", hits, window=False)
check("tag spellings and case tolerated; a left-out figure is appended", "(14 damage)" in t and "(critical, 30 damage)" in t and "(miss)" in t and "[" not in t and "(h1)" not in t, t)
t = cs.place_figures("Nothing special [h9] here [h1] and again [h1].", hits, window=False)
check("unknown tags vanish and a repeat is dropped", t.count("(14 damage)") == 1 and "h9" not in t, t)
t = cs.place_figures("A blow lands. [h1]", hits[:1], window=True)
check("window gets a hoverable token", "⟦a-1-1|(14 damage)⟧" in t, t)
check("the engine never leaves a tag in prose", "[h" not in cs.place_figures("x [h1] y [h2] z [h3]", hits, False))
# (f377) a killing blow the narrator told without its tag: its figure goes on the sentence that tells it, not after the last miss
kill = [{"id": "k-1", "tag": "h1", "figure": "(14 damage)"}, {"id": "k-2", "tag": "h2", "figure": "(9 damage)"}, {"id": "k-3", "tag": "h3", "figure": "(miss)"}]
told = ["You use Lancer's Sweep on the wolf: a heavy blow - the wolf is dead [h1]", "The wolf bites you: a solid hit [h2]", "The wolf snaps at you and misses [h3]"]
said = ("The sizzling hiss of acid dies away as the coating loses its potency on your copper tip. You drive the lance into a low, violent sweep "
        "that catches the lead beast squarely across the chest. It slams into the earth and stays there, stone dead. The remaining wolves do not "
        "hesitate; they press inward.\n\nOne lunges and sinks its teeth deep into your side, the impact jarring your ribs [h2]. From the opposite "
        "flank, the final wolf snaps at your throat but finds only air, its jaws clattering shut against the wind [h3].")
t = cs.place_figures(said, kill, False, told)
check("(f377) a left-out killing blow's figure sits on the sentence that tells it, before the blows after it, and the passage keeps its paragraphs",
      "stone dead (14 damage)." in t and t.endswith("against the wind (miss).") and "\n\n" in t and t.index("(14 damage)") < t.index("(9 damage)"), t)
t = cs.place_figures('He roars, "Come on!" You swing wide and miss [h3].', kill, False, ["You strike the wolf [h1]", "x [h2]", "y [h3]"])
check("(f377) ...never inside words someone says, and two blows told in one sentence keep their order",
      '"Come on!" (14 damage)' in t and t.index("(9 damage)") < t.index("(miss)"), t)
check("opening events lose their tags", cs.TAG.sub("", "A wolf bites you. [h1]") == "A wolf bites you.")

# ---- pane data ----
scene = cs.CombatScene(ws, fight, "wolf")
d = scene.pane_data("even")
check("pane lists the enemies with hp and where they stand", all({"name", "hp", "max_hp", "where", "statuses"} <= set(e) for e in d["enemies"]) or not d["enemies"])
check("pane lists you with resources", {"hp", "max_hp", "stamina", "mana"} <= set(d["you"]))
check("pane lists your abilities", len(d["moves"]) == len(fight.player.moves) and all({"name", "cost", "ready", "reason", "left"} <= set(m) for m in d["moves"]))
if fight.player.moves:
    m = fight.player.moves[0]
    fight.player.cooldowns[m.id] = 3
    mv = next(x for x in scene.pane_data()["moves"] if x["id"] == m.id)
    check("a cooling ability says when it is ready", not mv["ready"] and mv["left"] == 2 and "2 turns" in mv["reason"], mv)
    fight.player.cooldowns[m.id] = 1
    mv = next(x for x in scene.pane_data()["moves"] if x["id"] == m.id)
    check("at 1 it is ready by the time you act", mv["ready"] or "Not enough" in mv["reason"], mv)
    fight.player.cooldowns[m.id] = 0
# terminal: show() prints text and the console says it did not handle the pane
check("terminal prints the old panel", console.combat_state({}) is False)
print("\nFAILED: " + ", ".join(bad) if bad else "\nall ok")
sys.exit(1 if bad else 0)
