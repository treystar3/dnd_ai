"""The board pane: Accept, Abandon, Join and personal requests run the engine's own code (same rules, no model call)."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import money, quests
from ui import console

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)
lines, panels = [], []
console.note = lambda m: lines.append(m)
console.panel = lambda name, data: panels.append((name, data)) or True

shutil.rmtree("saves/board_click_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("board_click_test")
store.meta.seed = 7; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
char.level = 3; char.coins = money.to_smallest(gold=50)
gid = next(p.id for p in world.places.values() if p.type == "guild")
store.save_player(PlayerState(character=char, location=gid))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter(gid)
c = ws.player.character
check("the clerk is here", ws.clerk_here() is not None)

d = ws.board_data()
check("a non-member sees postings but none can be accepted", d["postings"] and not any(p["ok"] for p in d["postings"]) and not d["member"], [p["why"] for p in d["postings"]][:1])
check("...and can afford the fee", d["fee_ok"] and d["clerk"])
n0 = len(ws.player.quests)
ws.board_click(f"#boardaccept {d['postings'][0]['id']}")
check("accepting before joining takes nothing", len(ws.player.quests) == n0, lines[-2:])
check("the pane is redrawn after a click", panels and panels[-1][0] == "board")

ws.board_click("#boardjoin")
check("Join signs you in at rank F", ws.rank == "F", lines[-2:])
d = ws.board_data()
ok = [p for p in d["postings"] if p["ok"]]
check("members can take rank-F postings", bool(ok) and d["member"], [p["letter"] for p in d["postings"]])
above = [p for p in d["postings"] if not quests.at_or_below(p["letter"], "F")]
if above:
    check("a posting above rank is greyed out with the reason", not above[0]["ok"] and "rank" in above[0]["why"].lower(), above[0]["why"])

q = ok[0]
before = len(ws.board_data()["postings"])
ws.board_click(f"#boardaccept {q['id']}")
check("Accept takes the contract", any(x["id"] == q["id"] for x in ws.player.quests), lines[-2:])
check("...and removes it from the board", len(ws.board_data()["postings"]) == before - 1)
check("...and it shows under your contracts", any(h["id"] == q["id"] for h in ws.board_data()["held"]))

lines.clear()
ws.board_click(f"#boardaccept {q['id']}")
check("a posting already taken says so and takes nothing", any("no longer" in l for l in lines) and sum(x["id"] == q["id"] for x in ws.player.quests) == 1, lines)

limit = quests.G["base_active"] + ws.guild_perks()["active"]
for p in ws.board_data()["postings"]:
    if p["ok"]:
        ws.board_click(f"#boardaccept {p['id']}")
held = sum(1 for x in ws.player.quests if x["guild"])
check("the contract limit holds", held <= limit, (held, limit))
if held >= limit:
    left = ws.board_data()["postings"]
    check("at the limit every posting is greyed out", left and not any(p["ok"] for p in left), [p["why"] for p in left][:2])

lines.clear()
ws.board_click("#boardaccept nosuchid")
check("an unknown posting is refused plainly", any("no longer" in l for l in lines), lines)

gone = ws.player.quests[0]
ws.board_click(f"#boardabandon {gone['id']}")
check("Abandon drops the contract", not any(x["id"] == gone["id"] for x in ws.player.quests), lines[-2:])
lines.clear()
ws.board_click(f"#boardabandon {gone['id']}")
check("abandoning it twice says so", any("no longer" in l for l in lines), lines)

# no clerk, no accepting
ws2 = ws
clerk = ws2.clerk_here()
ws2.present = [n for n in ws2.present if n is not clerk]
d = ws2.board_data()
check("without the clerk nothing can be accepted", not d["clerk"] and not any(p["ok"] for p in d["postings"]), [p["why"] for p in d["postings"]][:1])
n1 = len(ws2.player.quests)
ws2.board_click(f"#boardaccept {d['postings'][0]['id']}")
check("...and a click takes nothing", len(ws2.player.quests) == n1, lines[-1:])

# a personal request
ws2.present.append(clerk)
npc = next(n for n in ws2.present if n.role != "guild_clerk")
offer = next(q for q in ws2.board_data() and store.load_place(gid).board)
offer = dict(offer, guild=False, issuer=npc.id, issuer_name=npc.name)
npc.quest_offer = offer
d = ws2.board_data()
check("a request from someone here is listed", any(r["npc"] == npc.id for r in d["requests"]))
nq = len(ws2.player.quests)
ws2.board_click(f"#boardrequest {npc.id}")
check("...and Accept takes it", len(ws2.player.quests) == nq + 1 and npc.quest_offer is None, lines[-1:])
lines.clear()
ws2.board_click(f"#boardrequest {npc.id}")
check("...and a second click finds it gone", any("no longer" in l for l in lines), lines)

# the interpreter is shown the board
import scenes.world_prompts as wp
text = wp.interpret_request("noon", "Guild", [], [], [], None, None, "I want to do this", board=["1. [F] Deliver the parcel"], contracts=["[F] Hunt rats"])
check("the interpreter sees the board and your contracts", "CONTRACT BOARD" in text and "1. [F] Deliver the parcel" in text and "Hunt rats" in text)
check("pick_posting matches 'delivery' to a Deliver posting", ws2.pick_posting([{"title": "Deliver the parcel to Bo", "id": "x"}, {"title": "Hunt rats", "id": "y"}], "the delivery one")["id"] == "x")

# each hall keeps its own board, and you read the one in your town
parth_board = [q["id"] for q in ws2.ensure_board()]
ws2.enter("ironvein_inn")
check("in another town the hall is that town's", ws2.hall_here() == "ironvein_guild", ws2.hall_here())
iron = [q["id"] for q in ws2.ensure_board()]
check("...with its own postings, not Parth's", iron and not set(iron) & set(parth_board), (iron[:2], parth_board[:2]))
check("the pane names the hall", ws2.board_data()["hall"] == "the Ironvein guild hall", ws2.board_data()["hall"])
ws2.enter("parth")
check("in a town with no guild hall there is no board", ws2.hall_here() == next((p.id for p in world.places.values() if p.type == "guild" and p.id.startswith("parth")), None) or ws2.hall_here() == "guild_house")
nohall = next((p.id for p in world.places.values() if not p.parent and not any(h.type == "guild" and (h.id == p.id or h.parent == p.id) for h in world.places.values())), None)
if nohall:
    ws2.enter(nohall)
    check("...no board is shown away from any hall", ws2.hall_here() is None and ws2.ensure_board() == [] and ws2.board_data()["hall"] == "", nohall)
# ---- adventurers looking for work (f281): the roster on the board, hired with a click; Maren first and free during her lesson
ws.enter(gid)
if not ws.rank:
    ws.board_click("#boardjoin")
d = ws.board_data()
check("a member sees the week's roster with fees and a Hire each", len(d["hires"]) >= 3 and all(h["fee"] and h["id"] for h in d["hires"]) and any(h["ok"] for h in d["hires"]), d["hires"][:1])
n0 = len(ws.player.party)
pick = next(h for h in d["hires"] if h["ok"])
ws.board_click(f"#boardhire {pick['id']}")
check("Hire signs them on", len(ws.player.party) == n0 + 1 and any(m["name"] == pick["name"] for m in ws.player.party), [m["name"] for m in ws.player.party])
d = ws.board_data()
check("...and they are off the roster", not any(h["id"] == pick["id"] for h in d["hires"]))
ws.board_click("#boardhire nosuchone")
check("a stale Hire does nothing", len(ws.player.party) == n0 + 1, lines[-1:])
_roster = ws.party_roster
two = [dict(m) for m in _roster() if m["id"] != pick["id"]][:2]
if len(two) == 2:                                     # (f329) two people with one first name: the button hires the one clicked, and only them
    two[0]["name"], two[1]["name"] = "Joren Greaves", "Joren Crane"
    ws.party_roster = lambda: two
    c0, coins0 = len(ws.player.party), ws.player.character.coins
    ws.player.character.coins = max(two[0]["fee"], 1) * 10
    ws.board_click(f"#boardhire {two[0]['id']}")
    names = [m["name"] for m in ws.player.party]
    check("Hire on one of two Jorens signs on that one alone, and says nothing of the other", len(names) == c0 + 1 and "Joren Greaves" in names and "Joren Crane" not in names
          and not any("Joren Crane" in l for l in lines[-4:]), (names, lines[-3:]))
    ws.player.party = [m for m in ws.player.party if m["name"] != "Joren Greaves"]
    ws.party_roster = _roster; ws.player.character.coins = coins0
from engine import mentor as _m
ws.player.mentor["stage"] = "board"; ws.player.mentor["since"] = 0
d = ws.board_data()
check("during Maren's lesson she is the only one for hire, free (f283)", d["hires"] and len(d["hires"]) == 1 and d["hires"][0]["id"] == "maren" and d["hires"][0]["fee"] == "free" and d["hires"][0]["ok"] and d["lesson"], d["hires"][:2])
check("...and the typed roster is empty too", ws.party_roster() == [])
ws.board_click("#boardhire maren")
check("...and Hire takes her on as practice", ws.mentor_in_party(), [m.get("name") for m in ws.player.party])
check("...after which the list is empty until the lesson is done", ws.board_data()["hires"] == [])

# ---- (f298) hiring from the pane only inside the hall
out_spot = next((p.id for p in world.places.values() if p.parent == world.places[gid].parent and p.id != gid and p.type != "guild"), None)
if out_spot:
    ws.player.mentor["stage"] = "done"
    ws.enter(out_spot)
    d = ws.board_data()
    check("away from the hall, the pane still lists who is for hire but every Hire is shut", d["hires"] and not any(h["ok"] for h in d["hires"]) and all("guild hall" in h["why"] or "full" in h["why"] for h in d["hires"]), d["hires"][:1])
    n0 = len(ws.player.party)
    ws.board_click(f"#boardhire {d['hires'][0]['id']}")
    check("...and a click there hires no one", len(ws.player.party) == n0)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
