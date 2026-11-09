"""(f485) The talk read, asked and committed: the model calls a conversation needs (the reply, the profile, the frame, the parting, the
work offer read) are asked with no operation open, the operation standing down and running again to be given each answer (engine/
asked.py); a reply that fails leaves the save as it was, gives the input's count back, leaves no line and no row, and the same line
typed again sends the same request; a retried first talk opens a new conversation, the stance as it was; what the talk does first that
is its own (a hand-in, a walk) is an operation of its own and stands if the reply does not; a write inside a prepare is the game's fault;
a request that moved between attempts stops the operation with no second call; the restarted talk commits what the same talk asked
inline commits; the conversation is kept in the save and is there again when it is opened; and what is said aloud reaches those here
and awake: both characters, never a fallen hire, and a bystander keeps a name given aloud."""
import hashlib
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import config
from engine import asked, memory, operation, presence, regard
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

real = simlib.below()                   # (f518) the stub answering now, which the spy calls through to
FAIL = {"titles": set()}
LOG, REQ = [], []


def chat(**k):
    title = k["format"].get("title")
    LOG.append((title, operation.current().kind if operation.current() else None))
    if title == "NPCReply":
        REQ.append(hashlib.sha256(json.dumps(k["messages"], sort_keys=True).encode()).hexdigest()[:16])
    if title in FAIL["titles"]:
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


def open_game(name, fresh=True):
    g = simlib.campaign(name, cls="warrior", seed=3, location="guild_house", fresh=fresh)
    config.TURN_LOG_PATH, config.CRASH_LOG_PATH = f"saves/{name}/turns.jsonl", f"saves/{name}/crash.log"
    return g


def seat(g):
    """The hall's own people, here by the rules at this hour: the one spoken with (T) and one standing by (B)."""
    ws, store = g.scene, g.store
    ws.enter("guild_house")
    return ws, store


def T(ws):
    return sorted(n.id for n in ws.present)[0]


def B(ws):
    return sorted(n.id for n in ws.present)[1]


def talk(ws, words, target=None):
    stub.plan = [{"kind": "talk", "target": target or T(ws), "speech": words}]
    try:
        return ws.turn(f'I say, "{words}"')
    finally:
        stub.plan = None


held = simlib.stand_in(chat=chat, embed=None)       # (f518) the spy as the model's source, over the stub
NAME = "prepared_talk_485"
g = open_game(NAME)
ws, store = seat(g)

# ---- a reply that fails leaves nothing behind; typed again, the same request
stub.plan = [{"kind": "look"}]
ws.turn("I look around.")                                  # the board's first refresh at the hall is behind us: an operation of its own
stub.plan = None
tid, bid = T(ws), B(ws)
d0, steps0 = statehash.digest(store), store.meta.steps
LOG.clear(); REQ.clear()
FAIL["titles"] = {"NPCReply"}
stood = talk(ws, "Good day to you.")
FAIL["titles"] = set()
check("a reply that fails is a line not taken: the save as it was, the input's count given back, no conversation kept",
      stood is False and statehash.digest(store) == d0 and store.meta.steps == steps0 and store.load_talk() is None and ws.partner is None,
      (stood, store.meta.steps, steps0, store.load_talk()))
check("...no row was written for the one spoken with", not simlib.remembered(store, tid))
check("...and it was asked with no operation open, every try", [c for c in LOG if c[0] == "NPCReply"] and all(op is None for t, op in LOG if t == "NPCReply"), LOG)
first_req = REQ[0]
REQ.clear()
stood = talk(ws, "Good day to you.")
check("the same line typed again sends the same request, and is taken", stood is True and REQ == [first_req], (stood, REQ, first_req))
rec = store.load_talk() or {}
check("a first talk tried again opens the conversation it would have, kept in the save with its stance",
      rec.get("speaker") == tid and len(rec.get("lines") or []) == 2 and rec.get("stance", None) == (getattr(ws, "stance", "") or ""), rec)
check("the talk's calls were all made with no operation open (the reply, the profile, the frame)",
      held.live() and any(t == "NPCReply" for t, _ in LOG) and all(op is None for t, op in LOG if t in ("NPCReply", "NPCProfile", "DialogueFrame")), LOG)
check("...and none of the five is in the ratchet's residue", not (set(operation.LEGACY) & {"npc_conversation", "npc_profile", "dialogue_frame",
      "work_offer_read", "npc_parting"}), operation.LEGACY)
check("the night's partner is the open conversation's", (store.load_talk() or {}).get("speaker") == tid)

# ---- the hand-in before a reply that fails stands: its own operation
ws.player.quests = ws.player.quests + [{"id": "q485", "title": "Bring the herbs", "kind": "fetch", "issuer": tid, "letter": "F"}]
store.save_player(ws.player)
coins0 = ws.player.character.coins


def handin(nid):
    ws.player.character.coins += 77
    ws.player.quests = [q for q in ws.player.quests if q.get("id") != "q485"]
    return ["Bring the herbs"]


ws.turn_in = handin
FAIL["titles"] = {"NPCReply"}
stood = talk(ws, "I have your herbs.")
FAIL["titles"] = set()
del ws.turn_in
kinds = [o["kind"] for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps]
check("a hand-in before a reply that fails stands, its own operation; the talk after it does not",
      store.load_player().character.coins == coins0 + 77 and "action:handin" in kinds and "action:talk" not in kinds, (kinds, store.load_player().character.coins))

# ---- a write inside a prepare is the game's fault
d1 = statehash.digest(store)
real_prepare = ws.prepare_talk
ws.prepare_talk = lambda intent, text: store.save_npc(store.load_npc(bid))
stood = talk(ws, "One more thing.")
ws.prepare_talk = real_prepare
crash = Path(f"saves/{NAME}/crash.log")
check("a write inside a prepare is refused by the fence: the game's own fault, logged, the line not taken",
      stood is False and statehash.digest(store) == d1 and crash.exists() and "prepare_talk" in crash.read_text(), (stood, crash.exists()))

# ---- a request that moved between the attempts stops the operation, and the model is not asked twice
real_key = asked.key
n = {"k": 0}


def moving_key(*a):
    n["k"] += 1
    return real_key(*a) + str(n["k"])


asked.key = moving_key
LOG.clear()
d2 = statehash.digest(store)
stood = talk(ws, "And another.")
asked.key = real_key
check("a request that moved between the attempts is a fault: the line not taken, the model asked once", stood is False
      and statehash.digest(store) == d2 and sum(1 for t, _ in LOG if t == "NPCReply") == 1 and "Drift" in crash.read_text(), LOG)

# ---- the restarted talk commits what the same talk asked inline commits
def run_once(name, inline):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    gg = open_game(name)
    w, s = seat(gg)
    keep = asked._TASKS
    if inline:
        asked._TASKS = frozenset()
    try:
        talk(w, "Good day to you.")
        talk(w, "What do you sell?")
    finally:
        asked._TASKS = keep
    dump = statehash.dump(s)
    gg.close()
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
    return {t: rows for t, rows in dump.items() if t != "kv"}, [r for r in dump.get("kv", []) if "campaign" not in str(r)[:40]]


a, b = run_once("prepared_talk_485a", True), run_once("prepared_talk_485b", False)
check("the talk asked outside and run again commits what the same talk asked inline commits", a == b,
      [t for t in a[0] if a[0][t] != b[0].get(t)] + (["kv"] if a[1] != b[1] else []))

# ---- the conversation is there again when the save is opened
talk(ws, "Tell me about the herbs.")
lines = list(ws.convo)
g.close()
g = open_game(NAME, fresh=False)
ws, store = seat(g)
check("opened again mid-talk, the conversation is as it was: who, and its lines", ws.partner is not None and ws.partner.id == tid
      and [tuple(x) for x in ws.convo] == [tuple(x) for x in lines], (ws.partner and ws.partner.id, ws.convo[-2:], lines[-2:]))

# ---- what is said aloud reaches those here and awake
c1, c2 = simlib.two_characters(ws)
ws.characters = lambda: [c1, c2]
ws.player.party = [{"id": "h1", "name": "Ghak Skurz", "active": True, "permanent": True}, {"id": "h2", "name": "Ula Venn", "active": True, "fallen": True}]
heard = presence.hearers(ws)
check("both characters hear, and a hire here and awake; a fallen one does not", c1.id in heard and c2.id in heard and "hire:h1" in heard
      and "hire:h2" not in heard, heard)
del ws.characters
ws.player.party = []
presence.overheard_name(ws, next(n for n in ws.present if n.id == tid), ws.acting, "Arwen")
rows = simlib.remembered(store, bid, about="Arwen")
check("a bystander keeps a name given aloud, as heard, from the character, hearsay to them",
      [(r["kind"], r["source"]) for r in rows] == [("heard", ws.acting)] and regard.of(store.load_npc(bid), ws.acting).heard_of.get("source") == ws.acting, rows)

check("the spy was the model's source throughout, and every call it saw it answered", held.live() and LOG and sum(held.src.calls.values()) >= len(LOG),
      (held.live(), dict(held.src.calls), len(LOG)))
held()
check("...and taken away, the stub answers again", not held.live() and simlib.below().chat == stub.chat)
g.close()
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
