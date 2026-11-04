"""(f470) Prepare, then commit: the understanding (the interpreter and the audit) runs outside any transaction and writes nothing (the
fence says so); the first action is an operation of its own; a board refresh the interpreter's read brings due is a `board` operation
of its own, and a question the world asks back a `clarify` operation; a failed understanding commits nothing, not even the input's
count. The ratchet: every model task still called inside an operation's transaction is named in RECORDED, which may only shrink as the
families move out (the telling operations, whose one call is the operation, are not counted)."""
import shutil
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from engine import combat, operation, refusals
from llm import gateway
from npc.models import NPC
from scenes import combat_scene as cs
from storage import statehash
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


# The residue: tasks still asked for inside an operation's transaction after this feature. It may only shrink (a family moved out drops
# its tasks here); a task appearing that is not listed fails the suite. The understanding's tasks (interpret_action, audit_meaning,
# audit_compare, clarify) are gone from it with this feature.
RECORDED = frozenset({                                                  # (f485) the talk's five are asked outside (engine/asked.py); (f488) the
                                                                        # hires' and Maren's four; (f489) the party's own six: fifteen in all
    "road_event", "discovery", "ruling", "plausible_object", "classify_field", "camp_intent", "party_intent", "stranger_read",
    "pulse_thread", "pulse_motive", "pulse_cataclysm", "thread_telling", "board_stakes", "event_judge", "moment",
    "arc_story", "loot_name", "legendary_name", "accessory_name", "named_spell", "spell_rank", "generate_lessons", "lesson_want",
    "narrate",                                                          # (f497) combat_interpret asked outside; (f498) the three tellings and the
})                                                                      # opening (combat_opening) asked outside; narrate stays for its inline uses
UNDERSTANDING = {"interpret_action", "audit_meaning", "audit_compare", "clarify"}

NAME = "prepared_470"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="guild_house")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = f"saves/{NAME}/turns.jsonl"
config.CRASH_LOG_PATH = f"saves/{NAME}/crash.log"
SHOWN = simlib.quiet_console()
real = gateway._client
FAIL = {"titles": set()}
LOG = []


def chat(**k):
    title = k["format"].get("title")
    LOG.append(("call", title, operation.current().kind if operation.current() else None))
    if title in FAIL["titles"]:
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
clerk = NPC(id="clerk470", name="Odo Marr", people="human", role="guild_clerk", location="guild_house", traits=[], trust=50)
herb = NPC(id="herb470", name="Tam Reed", people="human", role="herbalist", location="guild_house", traits=[], trust=50)
store.save_npc(clerk); store.save_npc(herb)
ws.enter("guild_house")
ws.present, ws.residents = [clerk, herb], [clerk, herb]
ws.player.character.coins = 100000
store.save_player(ws.player)


def ops_of_input():
    return [o["kind"] for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps]


# ---- the understanding outside any transaction; the board refresh its own operation
stub.plan = [{"kind": "look"}]
LOG.clear()
stood = ws.turn("I read the board.")
ops = ops_of_input()
interp = [c for c in LOG if c[1] == "ActionPlan"]
check("the interpreter is asked outside any operation, and the board refresh its read brought due is an operation of its own, before the action",
      stood is True and interp and interp[0][2] is None and ops[:2] == ["board", "action:look"], (stood, ops, interp))
check("...the board stands with its postings, committed apart", store.load_place("guild_house").board_day >= 0 and store.load_place("guild_house").board, store.load_place("guild_house").board_day)
stakes = [c for c in LOG if c[1] == "BoardStakes"]
check("...the stakes' calls were made inside the board operation (named in the ratchet's residue)", all(c[2] == "board" for c in stakes), stakes)

# ---- a failed understanding commits nothing, not even the input's count
d0 = statehash.digest(store)
steps0, saved0 = store.meta.steps, store.load_operations()["revision"]
n_ref = len(refusals.SESSION)
FAIL["titles"] = {"ActionPlan"}
stood = ws.turn("I look around.")
FAIL["titles"] = set()
check("an ActionPlan failure is a line not taken: nothing committed, the digest equal, the input's count given back, no refusal of the line",
      stood is False and statehash.digest(store) == d0 and store.meta.steps == steps0 and store.load_operations()["revision"] == saved0
      and not ws.last_crash and ws.last_failure, (stood, store.meta.steps, steps0, store.load_operations()["revision"], saved0, ws.last_failure))

# ---- the first action is an operation of its own; its words and its writes are one record
stub.plan = [{"kind": "buy", "ware": "healing draught", "target": herb.id}]
ws.present, ws.residents = [clerk, herb], [clerk, herb]
coins0 = store.load_player().character.coins
SHOWN.clear()
stood = ws.turn("I buy a healing draught from the herbalist.")
rec = next((o for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps and o["kind"] == "action:buy"), None)
check("a purchase is its own operation: the coins and the paid row in one record, the understanding before it recorded nowhere",
      stood is True and store.load_player().character.coins < coins0 and rec and any(r["kind"] == "paid" for r in rec["rows"]) and ops_of_input()[0] == "action:buy",
      (stood, ops_of_input(), rec and [r["kind"] for r in rec["rows"]]))

# ---- a question asked back is a clarify operation of its own
ws.store.arm(True)
n_ops = len(store.load_operations()["ops"])
ws.ask_back("audit_failed", "I frob the wibble.", "no such thing here")
ws.store.arm(False)
check("the question the world asks back is a clarify operation of its own, the pending question kept in it",
      len(store.load_operations()["ops"]) == n_ops + 1 and store.load_operations()["ops"][-1]["kind"] == "clarify" and ws.pending_clarify is not None,
      ([o["kind"] for o in store.load_operations()["ops"][-2:]], ws.pending_clarify))
ws.pending_clarify = None

# ---- the ratchet: a session touching the families; what is still asked for inside an operation is named, and only ever fewer
stub.plan = [{"kind": "talk", "target": herb.id, "speech": "Good day to you."}]
ws.present, ws.residents = [clerk, herb], [clerk, herb]
ws.turn('I say to Tam, "Good day to you."')
stub.plan = [{"kind": "look"}]
ws.turn("I look around.")
creature = ws.world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", name="wolf 1")
foe.hp = foe.max_hp = 1
ws.wildlife = (creature, [foe])                                      # (f498) the fight begun through a line, so its opening is inside an operation
stub.plan = [{"kind": "attack", "target": "wolf"}]
ws.turn("I attack the wolf")
stub.plan = None
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
ws.turn("I attack the wolf")
legacy = set(operation.LEGACY)
print("legacy tasks this session:", sorted(legacy))
check("no task of the understanding is asked for inside an operation any more", not (legacy & UNDERSTANDING), sorted(legacy & UNDERSTANDING))
check("the ratchet: every task still asked for inside an operation is named in RECORDED (a family moved out may only shrink it)", legacy <= RECORDED, sorted(legacy - RECORDED))
check("...and the ratchet counts calls inside operations only: the telling operations are their one call and are left out",
      all(c[2] not in ("passage", "round", "aftermath", "goddess", "opening") or c[1] in ("Narration", "GoddessLine") for c in LOG), [c for c in LOG if c[2] in ("passage", "round")][:4])

gateway._client = real
g.close()
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
