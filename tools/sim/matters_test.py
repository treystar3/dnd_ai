"""Matters (f317): a situation gets a door at birth; a word door puts the first clue in a person's concern; clues are facts a holder
knows and are found when their speech carries them; a hidden posting pays, reveals, and stays open; a path met ends it for any tier
and the town remembers; someone comes looking when the town thinks enough of the player - by name, once it knows them; the journal
lists only what was found; a door nobody answered opens another; anchors are made on the first visit and protected."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from npc.models import NPC
from engine import matters, pulse, events, deeds, truth
from llm.contracts import ThreadProposal, StageProposal, ClueProposal, PathProposal, QuestOffer
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/matters_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("matters_test")
store.meta.seed = 5; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(3))
char.level = 4; char.coins = 10**5
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.guild_rank = "F"
ws.enter("trading_square")
ws.enter("watch_tower")
ws.enter("guild_house")
ws.enter("tilted_plough")
ws.enter("trading_square")
now = ws.minutes
if not store.load_world_state():
    store.save_world_state(pulse.empty_state(now))
narrated = []
ws._narrate_now = lambda event, player_text="": narrated.append(event)

# ---- anchors: the town's people, made on the first visit, by what they are, and kept
from engine import retrieval
people = [store.load_npc(r.id) for r in retrieval.people_in_town(store, world, "parth")]
anchors = [n for n in people if n.anchor]
check("the town's anchors are made on the first visit, protected, with their note", {n.role for n in anchors} >= {"watch_captain", "guild_master"}
      and all(n.protected for n in anchors) and any("twenty years" in n.anchor for n in anchors), [(n.role, n.anchor[:30]) for n in anchors])

# ---- a situation is born with a door and what it carries
def proposal(**kw):
    base = dict(title="Sheep gone from the hill", place="parth", news="Sheep are going missing from the hill at night.", groups=["everyone"],
                stages=[StageProposal(description="Three ewes gone in a week; the shepherds blame wolves."),
                        StageProposal(description="A fourth is found penned behind the miller's barn.")],
                fallout=StageProposal(description="The shepherds give up and sell what is left."),
                truth="The miller's boy has been taking them to pay a debt in Kelpmoor; the wolves are a story.",
                clues=[ClueProposal(text="Wolves don't open gates, and that gate was opened.", holder="shepherd"),
                       ClueProposal(text="The miller's lad has been out nights, and he hasn't the look of a boy chasing girls.", holder="innkeeper")],
                paths=[PathProposal(name="Make the boy own it", how="Get the miller's lad to admit it.", kind="persuade", target="")],
                contract=QuestOffer(kind="hunt", what="wolf", count=2), reveal="The third ewe's throat is cut clean, not torn: a knife did it.")
    base.update(kw)
    return ThreadProposal(**base)

def birth(th_id, door_rng_seed, **kw):
    state = store.load_world_state()
    pr = proposal(**kw)
    th = {"id": th_id, "title": pr.title, "tier": "uncommon", "place": pr.place, "pressure": "", "stage": 0, "status": "active",
          "stages": [s.model_dump() for s in pr.stages], "fallout": pr.fallout.model_dump(), "times": [now, now + 1440, now + 2880], "made": now,
          "groups": ["everyone"], "resolution": pr.resolution, "paths": [], "contract": pr.contract.model_dump() if pr.contract else None}
    innkeeper = next((n for n in people if n.role == "innkeeper"), None)
    if innkeeper:
        pr.clues[1].holder = innkeeper.id
    state["threads"].append(th)
    matters.attach(store, world, state, th, pr, ws.player.reputation.get("parth", 0), random.Random(door_rng_seed), now)
    th["paths"] = events.build_paths(store, world, state, pr.paths, th, False)
    store.save_world_state(state)
    return th

th = birth("m1", 1)
state = store.load_world_state(); th = state["threads"][-1]
check("a new situation carries its truth, its clues and its door", th["truth"].startswith("The miller") and len(th["clues"]) == 2 and th["door"] in ("board", "board_more", "word", "scene"), th["door"])
check("a clue written for a person is theirs; one written for a role waits for the first of that role", th["clues"][1]["npc"] and th["clues"][0]["npc"] == "" , th["clues"])
check("the door used at the town is remembered, so the next is a different one", state["doors"]["parth"] == th["door"])
check("someone cannot come looking before the town thinks anything of the player", th["door"] != "summons")

# ---- the word door: the first clue is its holder's concern
th2 = None
for seed in range(1, 40):
    state = store.load_world_state(); state["threads"] = [t for t in state["threads"] if t["id"] != "m2"]; state["doors"]["parth"] = "board"; store.save_world_state(state)
    t = birth("m2", seed, contract=None, reveal="")
    if t["door"] == "word":
        th2 = t; break
check("a situation without a contract never goes to the board", th2 is not None and th2["door"] == "word")
holder = store.load_npc(th2["clues"][0]["npc"]) if th2 and th2["clues"][0]["npc"] else None
check("...and the first clue is now its holder's concern, which the profile writer leaves alone", holder is not None and holder.concern == th2["clues"][0]["text"] and holder.concern_from == "m2", (th2["clues"][0] if th2 else None))

# ---- clues in talk: a holder knows it; found when their words carry it
if holder:
    facts = matters.clue_facts(store, world, holder)
    check("the holder is given the clue as something they know, by id", any(f.id == "clue:m2:0" for f in facts), [f.id for f in facts])
    found = matters.mark_found(ws, holder, ["clue:m2:0"])
    check("when their speech carries it, it is found and the matter is the player's", found == [holder.concern]
          and next(t for t in store.load_world_state()["threads"] if t["id"] == "m2")["touched"])
    j = matters.journal(ws)
    check("the journal lists what was found, who said it, and how the matter stands - and nothing not found",
          any(m["title"] == th2["title"] and len(m["found"]) == 1 and holder.label() in m["found"][0] and m["standing"] == "still going on" for m in j), j)

# ---- the board with more behind it: the job pays, the reveal shows, the matter stays open
state = store.load_world_state(); state["doors"]["parth"] = "word"; store.save_world_state(state)
th3 = None
for seed in range(1, 60):
    state = store.load_world_state(); state["threads"] = [t for t in state["threads"] if t["id"] != "m3"]; store.save_world_state(state)
    t = birth("m3", seed)
    if t["door"] == "board_more":
        th3 = t; break
check("an ordinary-looking posting can hide more", th3 is not None and th3["hidden"])
if th3:
    state = store.load_world_state(); t3 = next(t for t in state["threads"] if t["id"] == "m3")
    check("...with no contract path: finishing the job is not the end of it", not any(p["kind"] == "contract" for p in t3["paths"]), t3["paths"])
    posted = pulse.post_contract(store, world, QuestOffer(**t3["contract"]), t3, now, plain=True)
    board = store.load_place("guild_house").board
    mine = [q for q in board if q.get("thread") == "m3"]
    check("...the posting reads as a plain job, nothing of the situation in its title", posted and mine and "(" not in mine[0]["title"], [q["title"] for q in mine])
    narrated.clear()
    events.after_deed(ws, deeds.log(store, "quest_done", now, "parth", thread="m3", title=mine[0]["title"]))
    t3 = next(t for t in store.load_world_state()["threads"] if t["id"] == "m3")
    check("...done and paid, the reveal is shown and the matter stays open at its next stage", t3["status"] == "active" and t3["revealed"] and t3["stage"] == 1
          and any("knife did it" in e for e in narrated), (t3["status"], t3["stage"], narrated[-1:]))
    check("...and the reveal is in the journal", any("knife" in f for m in matters.journal(ws) if m["title"] == t3["title"] for f in m["found"]))

# ---- a path met ends it, for any tier, and the town remembers
state = store.load_world_state(); t2 = next(t for t in state["threads"] if t["id"] == "m2")
t2["paths"] = [{"id": "talk_x", "name": "Make the boy own it", "how": "", "kind": "persuade", "target": holder.id if holder else "x", "spawn": "", "done": False}]
store.save_world_state(state)
events.after_deed(ws, deeds.log(store, "persuade", now, "parth", npc=holder.id if holder else "x", degree="strong success"))
t2 = next(t for t in store.load_world_state()["threads"] if t["id"] == "m2")
check("a path met ends an uncommon matter by the player's hand", t2["status"] == "resolved" and t2.get("result") == "player", (t2["status"], t2.get("result")))
mem = store.load_place("parth").memory
check("...the town remembers who settled it", mem and "settled by" in mem[-1]["text"] and char.name in mem[-1]["text"], mem)
check("...and every speaker in town is given that", any("lately:" in l and char.name in l for l in truth.scene_of(ws).view(truth.INTERPRETER, "interpreter").lines("town")))
check("...the holder remembers it too", holder is None or any(char.name in m.text for m in store.load_npc(holder.id).memories))
check("...and the town thinks more of the player", ws.player.reputation.get("parth", 0) >= 4, ws.player.reputation)
check("the journal says it was settled by you", any(m["title"] == t2["title"] and m["standing"] == "settled by you" for m in matters.journal(ws)), matters.journal(ws))

# ---- someone comes looking
ws.player.reputation["parth"] = 15
state = store.load_world_state(); state["threads"] = [t for t in state["threads"] if t["id"] not in ("m4",)]; state["door_log"] = {}; store.save_world_state(state)
t4 = birth("m4", 1, contract=None, reveal="")
state = store.load_world_state(); t4 = next(t for t in state["threads"] if t["id"] == "m4"); t4["door"], t4["summons"], t4["moment"] = "summons", "pending", ""; store.save_world_state(state)
for n in people:
    n.met_player = False; store.save_npc(n)
narrated.clear()
ws._door_loc = None
matters.on_arrival(ws)
t4 = next(t for t in store.load_world_state()["threads"] if t["id"] == "m4")
check("with the town's regard but nobody met, nobody comes (they do not know the player by name yet)", t4["summons"] == "pending" and not narrated, (t4["summons"], narrated[:1]))
ws.player.reputation["parth"] = 30
matters.on_arrival(ws)
t4 = next(t for t in store.load_world_state()["threads"] if t["id"] == "m4")
sender = store.load_npc(t4["sender"]) if t4.get("sender") else None
check("once the town knows them by name, an anchor comes looking though they never met", t4["summons"] == "met" and sender is not None and sender.anchor
      and any("comes looking for the player" in e and "has not met" in e for e in narrated), (t4["summons"], narrated[-1:][0][:120] if narrated else ""))
check("...and is here to be spoken to", sender is not None and any(n.id == sender.id for n in ws.present))
lines = matters.talk_lines(ws, sender) if sender else []
check("...and their prompt says why they came, and that they know the player by repute", len(lines) == 2 and "CAME LOOKING" in lines[0] and "never spoken" in lines[1], lines)
check("a second summons at the town waits for the cooldown", not matters._cooldown_ok(store.load_world_state(), "parth", "summons", now))

# ---- a moment, and a door nobody answered
state = store.load_world_state(); state["door_log"] = {}; store.save_world_state(state)
t5 = birth("m5", 2, contract=None, reveal="")
state = store.load_world_state(); t5 = next(t for t in state["threads"] if t["id"] == "m5"); t5["door"], t5["moment"], t5["summons"], t5["opened"] = "word", "", "", now - 4 * 1440
t5["answered"] = False; store.save_world_state(state)
state = store.load_world_state(); t5 = next(t for t in state["threads"] if t["id"] == "m5")
check("a word nobody listened to for three days becomes a scene", matters.reopen(store, world, state, t5, now) and t5["door"] == "scene" and t5["moment"] == "pending")
store.save_world_state(state)
narrated.clear()
ws._door_loc = "elsewhere"
random.seed(0)
matters.on_arrival(ws)
t5 = next(t for t in store.load_world_state()["threads"] if t["id"] == "m5")
check("the moment plays out in front of the player when they arrive, and is theirs to step into or not",
      t5["moment"] == "shown" and t5["touched"] and any("A MOMENT THE PLAYER WALKS INTO" in e for e in narrated), (t5["moment"], narrated[-1:][0][:80] if narrated else ""))
check("...and a moment's clue settles on someone present", any(c["npc"] for c in t5["clues"]), t5["clues"])
# ---- a find path: searching where it points
state = store.load_world_state(); state["threads"] = [t for t in state["threads"] if t["id"] != "m6"]; store.save_world_state(state)
t6 = birth("m6", 3, contract=None, reveal="", paths=[PathProposal(name="Find the penned ewes", how="Four ewes penned behind the barn, their marks cut out.", kind="find", target="trading_square")])
state = store.load_world_state(); t6 = next(t for t in state["threads"] if t["id"] == "m6")
check("a find path points at a real place", t6["paths"] and t6["paths"][0]["kind"] == "find" and t6["paths"][0]["target"] == "trading_square", t6["paths"])
import engine.checks as _checks
_roll = _checks.roll
_checks.roll = lambda odds, rng=None, c=None: ("success", 1)
narrated.clear()
ws.enter("trading_square")
found = matters.try_find(ws, "i search the square")
t6 = next(t for t in store.load_world_state()["threads"] if t["id"] == "m6")
check("searching where it points, a good roll finds it, shows it and ends the matter", found and t6["status"] == "resolved" and t6.get("result") == "player"
      and any("FINDS WHAT THEY WERE LOOKING FOR" in e for e in narrated), (found, t6["status"], narrated[-1:][0][:80] if narrated else ""))
_checks.roll = lambda odds, rng=None, c=None: ("failure", 99)
ws.enter("guild_house")
check("...and nowhere else there is nothing to find", not matters.try_find(ws, "i search"))
_checks.roll = _roll

# ---- the road: a happening on the way is part of a matter nearby
state = store.load_world_state(); state["threads"] = [t for t in state["threads"] if t["id"] != "m7"]
for t in state["threads"]:
    t["status"] = "resolved" if t["status"] == "active" else t["status"]          # only the road's own matter is live now
store.save_world_state(state)
t7 = birth("m7", 4, contract=None, reveal="", paths=[PathProposal(name="Kill the wolves", how="", kind="kill", target="wolf")])
matters.D["road"]["chance"] = 1.0
rm = matters.road_matter(ws, "parth", "willowmead", random.Random(0))
check("a live matter at the road's end can be what the road's happening is about", rm is not None and rm[0]["id"] == "m7" and rm[1] and rm[2] == "wolf", rm and (rm[0]["id"], rm[2]))
check("...the writer is told it, and the clue to carry", "THE MATTER nearby" in matters.road_lines(rm[0], rm[1], False) and rm[1] in matters.road_lines(rm[0], rm[1], False))
matters.road_shown(ws, "m7", carried=True)
t7 = next(t for t in store.load_world_state()["threads"] if t["id"] == "m7")
check("...a happening that carried a clue finds it, and the matter shows itself on the road once", t7["road"] and t7["clues"][0]["found"] and t7["clues"][0]["by"] == "on the road"
      and matters.road_matter(ws, "parth", "willowmead", random.Random(0)) is None)
check("a road with no matter at either end has none", matters.road_matter(ws, "kelpmoor", "saltmarsh_landing", random.Random(0)) is None)

shutil.rmtree("saves/matters_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
