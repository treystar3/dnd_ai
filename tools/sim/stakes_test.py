"""Contracts with a who and a why (f322): a new posting names someone of the town who asked for it and why; the issuer carries it as a
concern and speaks of it; they remember who took it; done, the result lands where it would be seen, the town remembers, the place is
safer for a while, and a posting with more behind it opens a matter."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import stakes, pulse, deeds, truth
from llm.contracts import ActionIntent
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/stakes_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("stakes_test")
store.meta.seed = 4; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 4; char.coins = 10**5
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.guild_rank = "F"
ws.enter("parth")
ws.enter("trading_square")
ws.enter("guild_house")
if not store.load_world_state():
    store.save_world_state(pulse.empty_state(ws.minutes))
narrated = []
ws._narrate_now = lambda event, player_text="": narrated.append(event)

# the model's answer: a reason and a result for every posting it is asked about; more behind the first hunt
def answer(u, k):
    ids = [l.split(":")[0].strip() for l in u.split("POSTINGS:")[1].strip().splitlines()]
    out = []
    for i, pid in enumerate(ids):
        row = {"id": pid, "reason": f"I've lost three ewes this week and I can't watch the hill at night (posting {pid}).", "result": "the hill's flocks stop thinning"}
        if "MORE BEHIND IT" in u.split("POSTINGS:")[1].splitlines()[i]:
            row["more"] = {"truth": "The miller's lad takes them to pay a debt.", "reveal": "The third ewe's throat is cut clean: a knife did it.",
                           "clue": "Wolves don't open gates, and that gate was opened.", "path": {"name": "Make the lad own it", "how": "", "kind": "find", "target": "trading_square"}}
        out.append(row)
    return {"postings": out}
stub.a_BoardStakes = answer

board = ws.ensure_board()
with_issuer = [q for q in board if q.get("issuer") not in (None, "guild")]
check("new postings name someone of the town who asked, and why", with_issuer and all(q.get("reason") and q.get("issuer_name") for q in with_issuer), [(q["title"], q.get("issuer_name")) for q in board][:4])
q = with_issuer[0]
check("...the issuer is a person of this town with a fitting role", store.npc_exists(q["issuer"]) and q["issuer_role"].replace(" ", "_") in stakes.G["issuers"][q["kind"]], (q["kind"], q.get("issuer_role")))
issuer = store.load_npc(q["issuer"])
check("...and it is what is on their mind while it stands", issuer.concern == q["reason"] and issuer.concern_from == f"quest:{q['id']}")
check("...and the result is written down to land later", q.get("result") == "the hill's flocks stop thinning")
check("the board pane says who asked and why", any(p["for"].startswith(f"Posted for {q['issuer_name']}") and q["reason"] in p["for"] for p in ws.board_data()["postings"]))
tl = stakes.talk_lines(ws, issuer)
check("the issuer's prompt carries the job as their own trouble", tl and "YOU ASKED THE GUILD TO POST A JOB" in tl[0] and "Nobody has taken it yet" in tl[0], tl)

# ---- taking it
ws.on_accept_quest(ActionIntent(kind="accept_quest", item=str(board.index(q) + 1)), "")
issuer = store.load_npc(q["issuer"])
check("taken, the issuer hears who took it on", any("taken on my job" in m.text for m in issuer.memories), [m.text for m in issuer.memories][-2:])
check("...and their prompt says so", "has taken it on" in stakes.talk_lines(ws, issuer)[0])

# ---- done
held = next(x for x in ws.player.quests if x["id"] == q["id"])
held["progress"] = held["count"]
narrated.clear()
rep_before = ws.player.reputation.get("parth", 0)
ws.turn_in()
issuer = store.load_npc(q["issuer"])
check("done, the issuer remembers, is grateful, and the trouble leaves their mind", any("did my job" in m.text for m in issuer.memories) and issuer.concern == "" and issuer.concern_from == "")
spot = held.get("place") if held.get("place") in world.places else ws.player.location
check("...the result is a lasting mark where the work was", any("the hill's flocks stop thinning" in m for m in store.load_place(spot).marks), store.load_place(spot).marks)
check("...the town remembers it, through the truth layer", any("lately:" in l and "flocks stop thinning" in l for l in truth.scene_of(ws).view(truth.INTERPRETER, "interpreter").lines("town")))
st = store.load_world_state()
check("...and it is news", any("flocks stop thinning" in n["text"] for n in st.get("news", [])))
if held["kind"] in ("hunt", "bounty"):
    check("...a hunt done makes its place safer for a while", any(e["kind"] == "danger" and e["place"] == held["place"] and e["value"] < 0 for e in st["effects"]), st["effects"])
check("...and the narrator shows what is different", any("THE JOB IS DONE AND PAID" in e for e in narrated), narrated[-2:])

# ---- more behind it
from engine import quests as _q
takeable = lambda x: x.get("issuer") not in (None, "guild") and _q.at_or_below(x["letter"], "F") and x["kind"] != "missing"
more = [x for x in ws.ensure_board() if x.get("more") and takeable(x)] + [x for x in ws.player.quests if x.get("more")]
if not more:                                       # none of this board's postings drew the chain: give one the writer's extra, as the roll would have
    nxt = next(x for x in ws.ensure_board() if takeable(x))
    st_b = store.load_place("guild_house")
    for x in st_b.board:
        if x["id"] == nxt["id"]:
            x["more"] = {"truth": "The miller's lad takes them.", "reveal": "The third ewe's throat is cut clean: a knife did it.",
                         "clue": "Wolves don't open gates, and that gate was opened.", "path": {"name": "Find the penned ewes", "how": "Four ewes penned behind the barn.", "kind": "find", "target": "trading_square"}}
            nxt = x
    store.save_place(st_b)
    more = [nxt]
m = more[0]
board = ws.ensure_board()
n = next((i for i, x in enumerate(board, 1) if x["id"] == m["id"]), 0)
if n:
    ws.on_accept_quest(ActionIntent(kind="accept_quest", item=str(n)), "")
held = next(x for x in ws.player.quests if x["id"] == m["id"])
held["progress"] = held["count"]
narrated.clear()
import engine.quests as _qq, engine.inventory as _inv
_done, _rm = _qq.done, _inv.remove_goods
_qq.done = lambda q, pack: True; _inv.remove_goods = lambda *a, **k: None          # whatever the job was, it is done
ws.turn_in()
_qq.done, _inv.remove_goods = _done, _rm
th = next((t for t in store.load_world_state()["threads"] if t["title"] == m["title"]), None)
check("a job with more behind it opens a matter when paid: revealed, with its clue and its path", th is not None and th["revealed"] and th["door"] == "board_more"
      and th["clues"] and th["clues"][0]["npc"] and th["paths"] and th["paths"][0]["kind"] == "find", th and (th["clues"], th["paths"]))
check("...the reveal is shown as a thing found", any("MORE TO IT THAN THE POSTING SAID" in e and "knife" in e for e in narrated), narrated[-1:])
from engine import matters
check("...and it is in the journal as a matter", any(j["title"] == m["title"] for j in matters.journal(ws)))

shutil.rmtree("saves/stakes_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
