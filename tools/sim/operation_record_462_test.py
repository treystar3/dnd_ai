"""(f462) The operation record in storage, behaviour-neutral: a commit inside a transaction writes the record and the presentation entry
together or not at all; a stale revision writes nothing; the window drops the oldest past retention; mark_shown clears an entry and the
state digest never sees any of it; the write fence, armed, refuses a save outside any operation and lets reads, operations and mark_shown
through; ledger.rollback_op takes back one operation's rows and totals; the operations' ids come from a stream of their own that moves no
other die; the digest's six tables stand; nothing opens an operation yet, so the golden replays as it is (golden_replay_test)."""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from engine import ledger, operation, session, streams
from storage import campaign as cs, statehash
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


g = simlib.campaign("op_record_462")
store = g.store
simlib.quiet_console()

# ---- a commit, whole with its transaction, outside the digest
d0 = statehash.digest(store)
streams.begin(store.meta.seed, store.meta.steps, "I buy a knife")
ledger.begin()
with store.transaction():
    op = operation.begin("action:buy", store.meta.steps, 0, store.revision(), "I buy a knife")
    ledger.add("gained", what="knife", facts={"what": "a worn knife", "who": None}, say="GAINED: a worn knife.")
    op.lines.append("You buy the knife.")
    entry = store.commit_operation(op, first_of_line=True)
operation.end("committed")
rec = store.load_operations()
check("the record holds the commit, its rows stamped with the operation, its facts kept, its revision bumped",
      rec["revision"] == 1 and len(rec["ops"]) == 1 and rec["ops"][0]["id"] == op.id and rec["ops"][0]["kind"] == "action:buy"
      and rec["ops"][0]["rows"][0]["op"] == op.id and rec["ops"][0]["rows"][0]["facts"] == {"what": "a worn knife"} and entry["revision"] == 1, rec)
check("the ledger's row carries the operation, and the operation keeps the row", ledger.ROWS and ledger.ROWS[0]["op"] == op.id and op.rows == ledger.ROWS, ledger.ROWS)
check("its held lines wait in the presentation entry", store.unshown() == {op.id: {"lines": ["You buy the knife."], "steps": store.meta.steps, "kind": "action:buy", "calls": []}}, store.unshown())   # calls: f467
check("find_operation finds it, and nothing else", store.find_operation(op.id) == rec["ops"][0] and store.find_operation("nope") is None)
check("the operation is closed", operation.current() is None and op.state == "committed")
d1 = statehash.digest(store)
check("the record and the entry are outside the state digest", d0 == d1, [k for k in d0 if d0[k] != d1[k]])
plain = ledger.add("found", what="a clue")
check("a row made with no operation open carries no stamp", "op" not in plain and "facts" not in plain, plain)

# ---- a raise after the commit, inside the same transaction, leaves neither the record nor the entry
try:
    with store.transaction():
        op2 = operation.begin("action:drop", store.meta.steps, 1, store.revision(), "and drop it")
        store.commit_operation(op2)
        raise RuntimeError("the action fell over after its record was written")
except RuntimeError:
    operation.end("rolled_back")
check("a rolled-back transaction takes the record and the entry with it", store.revision() == 1 and store.find_operation(op2.id) is None
      and op2.id not in store.unshown() and op2.state == "rolled_back", store.load_operations())

# ---- a stale revision writes nothing; a commit needs an open transaction
try:
    with store.transaction():
        op3 = operation.begin("action:late", store.meta.steps, 1, 0, "late")
        store.commit_operation(op3)
    stale = False
except cs.StaleOperation:
    stale = True
operation.end("rolled_back")
check("a commit over a revision it did not see is stale, and writes nothing", stale and store.revision() == 1 and len(store.load_operations()["ops"]) == 1)
try:
    opx = operation.begin("x", store.meta.steps, 2, store.revision())
    store.commit_operation(opx)
    bare = False
except RuntimeError as e:
    bare = "transaction" in str(e) and not isinstance(e, cs.StaleOperation)
operation.end("rolled_back")
check("...and a commit outside any transaction is refused", bare and store.revision() == 1)
try:
    operation.begin("a", 1, 0, 0)
    operation.begin("b", 1, 1, 0)
    twice = False
except RuntimeError:
    twice = True
operation.end("rolled_back")
check("two operations cannot be open at once", twice)

# ---- the window: the oldest records go past retention
for i in range(7):
    with store.transaction():
        o = operation.begin("action:step", store.meta.steps, i + 2, store.revision(), f"step {i}")
        store.commit_operation(o, keep=5)
    operation.end("committed")
rec = store.load_operations()
check("the record keeps the last `keep` operations, the oldest dropped first", len(rec["ops"]) == 5 and rec["revision"] == 8
      and [o["text"] for o in rec["ops"]] == [f"step {i}" for i in range(2, 7)], [(o["text"], o["revision"]) for o in rec["ops"]])
check("the retention is budget.yaml's", operation.RETENTION.get("operations") == 200 and operation.RETENTION.get("deferred_turns") == 3, operation.RETENTION)
check("the entries of operations not yet shown outlive the window", len(store.unshown()) == 8, len(store.unshown()))

# ---- mark_shown clears one entry; the digest is the same before and after; the row goes when nothing is left to show
d2 = statehash.digest(store)
store.mark_shown(op.id)
check("mark_shown clears the operation's entry and nothing else", op.id not in store.unshown() and len(store.unshown()) == 7 and statehash.digest(store) == d2)
store.mark_shown("never-an-operation")
for oid in list(store.unshown()):
    store.mark_shown(oid)
check("with nothing left to show, the entries' row is gone", store.unshown() == {} and store._kv("presentation") is None and statehash.digest(store) == d2)

# ---- the write fence: armed, a row written outside any operation is a fault; reads, operations and mark_shown pass
player = store.load_player()
store.arm(True)
try:
    store.save_player(player)
    refused = False
except cs.WriteOutsideOperation:
    refused = True
check("armed, a save outside any operation is refused, though it opens a transaction of its own", refused)
with store.transaction():
    try:
        store.save_player(player)
        tx_only = False
    except cs.WriteOutsideOperation:
        tx_only = True
check("...and a transaction alone is not an operation", tx_only)
with store.in_operation(), store.transaction():
    store.save_player(player)
    o = operation.begin("action:fenced", store.meta.steps, 9, store.revision(), "fenced")
    o.lines.append("held")
    store.commit_operation(o)
operation.end("committed")
check("inside an operation the saves and the commit pass", store.find_operation(o.id) is not None and store.unshown() == {o.id: {"lines": ["held"], "steps": store.meta.steps, "kind": "action:fenced", "calls": []}})
try:
    store.load_player(); store.load_operations(); store.revision(); statehash.digest(store)
    reads = True
except cs.WriteOutsideOperation:
    reads = False
check("reads pass the fence", reads)
store.mark_shown(o.id)
check("mark_shown passes the fence, outside any operation", store.unshown() == {})
store.arm(False)
store.save_player(player)
check("disarmed, the store is as it was", store.load_player().location == player.location)

# ---- ledger.rollback_op takes back one operation's rows and totals
ledger.begin()
ledger.TOTALS.clear()
a = operation.begin("a", 1, 0, 0)
ledger.add("gained", what="x")
ledger.add("paid", who="y", amount=3)
operation.end("committed")
b = operation.begin("b", 1, 1, 0)
ledger.add("gained", what="z")
operation.end("committed")
check("rows under two operations are told apart", [r["op"] for r in ledger.ROWS] == [a.id, a.id, b.id] and a.id != b.id)
ledger.rollback_op(a.id)
check("rollback_op removes only that operation's rows and totals", [r.get("what") for r in ledger.ROWS] == ["z"] and dict(ledger.TOTALS) == {"gained": 1}, (ledger.ROWS, dict(ledger.TOTALS)))

# ---- the ids: decided by the input and their place in it, from a stream of their own
streams.begin(7, 3, "a line")
a1, a2 = streams.new_id(12, stream="ops"), streams.new_id(12, stream="ops")
nxt = streams.new_id(8)
streams.begin(7, 3, "a line")
b1, b2 = streams.new_id(12, stream="ops"), streams.new_id(12, stream="ops")
streams.begin(7, 3, "a line")
undisturbed = streams.new_id(8)
streams.begin(7, 4, "a line")
c1 = streams.new_id(12, stream="ops")
check("operation ids are decided by the input and their place in it", (a1, a2) == (b1, b2) and a1 != a2 and len(a1) == 12 and operation.ID_DIGITS == 12, (a1, a2, b1, b2))
check("...differ across inputs", c1 != a1)
check("...and move no die of the ids stream", undisturbed == nxt, (undisturbed, nxt))

# ---- the digest's tables stand; the record is named as not state; the session owns the open operation
check("the six tables are still the digest's", list(statehash.TABLES) == ["kv", "places", "npcs", "npc_memory", "event_log", "entities"])
check("the record's rows are named as not state", statehash.NOT_STATE_ROWS == {("kv", "operations"), ("kv", "presentation")})
dumped = statehash.dump(store)
check("...and the dump leaves them out though they are in the save", not any(r[0] in ("operations", "presentation") for r in dumped["kv"]) and store._kv("operations") is not None)
check("the session owns the open operation", "operation.CURRENT" in [n for n, *_ in session._owned()])
operation.begin("left open", 1, 0, 0)
g.close()
check("...and closing the campaign closes it", operation.current() is None and simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
