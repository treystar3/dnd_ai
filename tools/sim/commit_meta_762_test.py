"""(f762) A commit saves the campaign's meta once (found by the audit, trace-turn-7). Every operation that stands saves its player
(save_player), and the meta, which holds the clock and the input's count, is written beside the player there; the first commit of
each input also wrote the same row a second time (commit_operation's first_of_line), which decided nothing.
Held here, for every operation that commits through the game's own paths: the commit's step (the player's save and the record)
writes each row of the save once, the campaign's meta among them, and the meta read back after it is the one in memory, with the
input's count.
The case that found it: a typed line whose first operation stands (a draught bought from the herbalist), with the operations after it.
Other cases of the kind: a pane's command, the first operation of its input; and the world's opening (world:open). And, as before:
the first operation that stands after one that failed is not the input's first, and its one write carries the count to the save.
Run: python tools/sim/commit_meta_762_test.py"""
import json
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
shown = simlib.quiet_console()
import config
from engine import act
from npc.models import NPC
from storage import saves

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NAME = "commit_meta_test"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = str(simlib.saves_path(NAME, "turns.jsonl"))
config.CRASH_LOG_PATH = str(simlib.saves_path(NAME, "crash.log"))

# ---- every row the store writes, and for each commit what its step wrote: from the player's save to the record's end
WRITES: list = []
COMMITS: list = []
start = [0]
real_put, real_save_player, real_commit = store._put, store.save_player, store.commit_operation


def put(key, text):
    WRITES.append(key)
    return real_put(key, text)


def save_player(*a, **k):
    start[0] = len(WRITES)                     # the last save of the player before a commit opens the commit's step
    return real_save_player(*a, **k)


def commit(op, *a, **k):
    entry = real_commit(op, *a, **k)
    COMMITS.append({"kind": op.kind, "index": op.index, "steps": op.steps, "rows": WRITES[start[0]:],
                    "saved": store._kv_text("campaign"), "memory": store.meta.model_dump_json()})
    return entry


store._put, store.save_player, store.commit_operation = put, save_player, commit


def committed(fn) -> list:
    n0 = len(COMMITS)
    fn()
    return COMMITS[n0:]


def twice(c: dict) -> list:
    return sorted({k for k in c["rows"] if c["rows"].count(k) > 1})


def held(name: str, tag: str, commits: list, count: int, first: bool = True) -> None:
    """`tag`: the case's short name, which each check carries; `commits`: what one input committed, in order; `count`: the input's
    count of every input (meta.steps). `first`: its first commit is the input's first operation."""
    check(f"{name}: operations of it stood", bool(commits), commits)
    if not commits:
        return
    head, rest = commits[0], commits[1:]
    if first:
        check(f"...its first operation is the input's first ({tag})", head["index"] == 0, (head["kind"], head["index"]))
    check(f"...the commit of the first operation that stands writes the campaign's meta once ({tag})", head["rows"].count("campaign") == 1,
          (head["kind"], head["index"], head["rows"]))
    check(f"...and writes no row twice ({tag})", not twice(head), (head["kind"], head["rows"]))
    check(f"...every commit after it writes the meta once and no row twice ({tag})",
          all(c["rows"].count("campaign") == 1 and not twice(c) for c in rest), [(c["kind"], c["rows"]) for c in rest])
    check(f"...the meta read back after each commit is the one in memory ({tag})", all(c["saved"] == c["memory"] for c in commits),
          [(c["kind"], c["saved"], c["memory"]) for c in commits if c["saved"] != c["memory"]])
    check(f"...and it carries the input's count, from the first operation that stands on ({tag})",
          all(json.loads(c["saved"])["steps"] == count == c["steps"] for c in commits),
          (count, [(c["kind"], json.loads(c["saved"])["steps"], c["steps"]) for c in commits]))


# ---- the world's opening: the first operation of what the world owes the save as the game opens
op_open = committed(ws.open_world)
held("the world's opening", "opening", op_open, store.meta.steps)
check("...it is the world's opening", [c["kind"] for c in op_open][:1] == ["world:open"], [c["kind"] for c in op_open])
ws.enter("parth")
store.save_player(ws.player)

# ---- the case that found it (trace-turn-7): a typed line whose first operation stands, and the operations after it
herb = NPC(id="herb1", name="Tam Reed", people="human", role="herbalist", location="parth", traits=[], trust=50)
store.save_npc(herb)
ws.enter("parth")
ws.present, ws.residents = [herb], [herb]
ws.player.character.coins = 100000
store.save_player(ws.player)
stub.plan = [{"kind": "buy", "ware": "healing draught", "target": herb.id}]
bought = committed(lambda: ws.turn("I buy a healing draught from the herbalist."))
held("a draught bought from the herbalist (trace-turn-7)", "line", bought, store.meta.steps)
check("...the draught's operation stood first, and more stood after it",
      [c["kind"] for c in bought][:1] == ["action:buy"] and len(bought) > 1, [c["kind"] for c in bought])

# ---- another of the kind: a pane's command, the first operation of its input
pane = committed(lambda: ws.command_input("#pronoun they"))
held("a pane's command that stands", "command", pane, store.meta.steps)
check("...it is the command's operation", [c["kind"] for c in pane] == ["command:pronoun"], [c["kind"] for c in pane])

# ---- as before: the first operation that stands after one that failed is not the input's first; its commit carries the count
TRIES = int(act.A["pending"]["tries"])
with ws.operation("test", "an act left waiting"):
    data = store.load_act_pending()
    data[ws.acting] = [{"words": "I bar the door with the bench.", "text": "I bar the door with the bench.", "place": ws.player.location,
                        "minute": ws.minutes, "tries": TRIES - 1}]
    store.save_act_pending(data)
real_take_up = act.take_up


def take_up(ws_, who, text):
    raise RuntimeError("the waiting act's own operation faults")


act.take_up = take_up
stub.plan = [{"kind": "wait", "summary": "waiting a while"}]
after_fail = committed(lambda: ws.turn("I wait a while."))
act.take_up = real_take_up
held("the first operation that stands after one that failed", "after a failure", after_fail, store.meta.steps, first=False)
check("...the operation that failed was the input's first, and the one that stood first came after it",
      "act:waiting" in [o.kind for o in ws.line_failed + ws.line_world_failed] and after_fail and after_fail[0]["index"] > 0,
      ([o.kind for o in ws.line_failed + ws.line_world_failed], [(c["kind"], c["index"]) for c in after_fail]))

# ---- and the save closed and opened again holds the count and the clock the last commit wrote
steps, minutes = store.meta.steps, store.meta.minutes
store._put, store.save_player, store.commit_operation = real_put, real_save_player, real_commit
g.close()
g = simlib.campaign(NAME, fresh=False)
check("the save opened again holds the count and the clock of the last commit", (g.store.meta.steps, g.store.meta.minutes) == (steps, minutes),
      ((steps, minutes), (g.store.meta.steps, g.store.meta.minutes)))
g.close()
saves.drop(NAME)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
