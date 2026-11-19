"""(f720) Rollback by declaration: every attribute of the world scene is declared once (engine/actor.py ATTRS) with what a failed
operation does with it: put back, left as it stands (with the reason), written only outside operations, read again from the
save, or set once. The lists the
session and the tests read (WorldScene.ROLLED, actor.HOMES, actor.UNLISTED) are that table's.

Checked three ways. The table's own shape. A census: every name the scene's classes set on `self`, and every name another
module sets on a scene, is private (`_`: copied and put back whole), a field of the turn, or a row of the table, and no row is
of a name nothing sets. And by running: a session of the stand-in model where every third operation fails at its end, and everything
the scene holds is compared with what the operation found: a name that differs and is not declared kept fails by its name; with the names found leaking (17 November) each on a case of its own, and
the ledger's told marks, which three callers put back by hand and the others did not."""
import ast
import collections
import contextlib
import inspect
import io
import random
import shutil
import sys
import textwrap
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 39)
held_stub = simlib.install(stub)
import config
from engine import actor, ledger
from engine.session import CampaignSession
from llm.gateway import LLMError
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import PlayerState
from ui import console
import nightbot

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


ROOT = Path(__file__).resolve().parent.parent.parent
F = actor.FIELDS
T = getattr(actor, "ATTRS", {})
HOWS = tuple(getattr(actor, k, k) for k in ("ROLLED", "KEPT", "OUTSIDE", "SAVED", "ONCE"))
by = lambda how: {k for k, a in T.items() if a.how == getattr(actor, how, how)}

# ---- the table
check("the scene's attributes are declared in one table", len(T) >= 40, len(T))
check("each is put back, kept, written outside operations, read again from the save or set once, and is one character's view or the scene's",
      T and all(a.how in HOWS and a.home in (actor.VIEW, actor.SCENE) for a in T.values()), [k for k, a in T.items() if a.how not in HOWS])
check("one that is not put back says why", all(a.why.strip() for a in T.values() if a.how != actor.ROLLED), [k for k, a in T.items() if a.how != actor.ROLLED and not a.why.strip()])
check("none is also a field of the turn, and none is private", not set(T) & set(F) and not [k for k in T if k.startswith("_")], sorted(set(T) & set(F)))
turn_back = {k for k, f in F.items() if actor.ROLLED in f.marks}
check("what a failed operation puts back is the table's: the turn's fields and the scene's rows, each with its home",
      actor.HOMES == {**{k: actor.TURN for k in turn_back}, **{k: T[k].home for k in by("ROLLED")}}, sorted(set(actor.HOMES) ^ (turn_back | by("ROLLED"))))
check("...and the scene's list is read from it", set(WorldScene.ROLLED) == set(actor.HOMES) and len(WorldScene.ROLLED) == len(actor.HOMES))
check("...and so is what a failure leaves as it stands", actor.UNLISTED == {k: T[k].home for k in by("KEPT") | by("OUTSIDE")}, sorted(set(actor.UNLISTED) ^ (by("KEPT") | by("OUTSIDE"))))
LEAKED = ("first_arrival", "revisit", "visitors", "assault", "learn_request", "repairs", "camp_events")
check("the names a failed operation left changed are put back", set(LEAKED) <= by("ROLLED"), sorted(set(LEAKED) - by("ROLLED")))


# ---- the census (f751) the walk is simlib's, one walk with reopen_declared's
own, outside, computed = simlib.scene_names()
stored = simlib.stored_names
# (f761) the telling's row is put back by names the opening's table gives (engine/telling.py names)
check("a name worked out at run time is set in three places only: the opening's private marks, the session's own putting back, and "
      "the telling's row put back",
      computed == {"WorldScene.opening_passage"} and outside.pop("<computed>", set()) == {"engine/session.py", "engine/telling.py"},
      (sorted(computed), sorted(outside.get("<computed>", []))))
view = lambda n: isinstance(inspect.getattr_static(WorldScene, n, None), property)       # the scene's name for what another holds: the actor's record, the save's question
declared = lambda n: n.startswith("_") or n in F or n in T or view(n)
check("the census reads the scene's classes and the modules around it", len(own) > 90 and "recent_narration" in own and "weight_hint" in outside, (len(own), len(outside)))
check("every name the scene's classes set on self is private, a field of the turn or a row of the table",
      not [n for n in own if n != "<computed>" and not declared(n)], sorted((n, sorted(own[n])) for n in own if n != "<computed>" and not declared(n)))
check("...and every name another module sets on a scene", not [n for n in outside if not declared(n)], sorted((n, sorted(outside[n])) for n in outside if not declared(n)))
check("no row is of a name nothing sets", T and not set(T) - set(own) - set(outside), sorted(set(T) - set(own) - set(outside)))
give_back = stored(ast.parse(textwrap.dedent(inspect.getsource(WorldScene.give_back))), ("self",))
if "self.refresh_present(" in inspect.getsource(WorldScene.give_back):       # who is here is read again there, by the scene's one reader of it
    give_back |= {"present"}
saved = by("SAVED") | {"player"}
check("no row is a property of the scene: those hold nothing of their own", not [k for k in T if view(k)] and view("player") and view("pending_clarify"), [k for k in T if view(k)])
check("what is read again from the save, and the character's record, are read again where an operation gives back (give_back), and nothing else is written there by hand",
      saved and saved <= give_back and not [n for n in give_back if n not in saved and n not in F and n not in by("ROLLED")],
      (sorted(saved - give_back), sorted(n for n in give_back if n not in saved and n not in F and n not in by("ROLLED"))))

# ---- the names that leaked, each on a case of its own
simlib.quiet_console()
g = simlib.campaign("rollback_720", cls="warrior", seed=5, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/rollback_720/turns.jsonl"
ws.enter("parth")
ws.enter("parth")                                       # a place come back to: not a first arrival
found = (ws.first_arrival, ws.revisit)
new = next(p for p in ws.world.places if p not in ws.player.visited and ws.world.places[p].parent == "parth")
with ws.operation("action:move", "a walk that does not stand") as op:
    ws.enter(new)
    inside = (ws.first_arrival, ws.player.location)
    raise LLMError("the model failed")
check("a walk that did not stand leaves the arrival as the operation found it", op.state == "rolled_back" and inside == (True, new) and found == (False, True)
      and (ws.first_arrival, ws.revisit) == found and ws.player.location == "parth", (found, inside, ws.first_arrival, ws.revisit, ws.player.location))
caller = ws.residents[0]
with ws.operation("world", "someone comes looking, and the operation fails", world=True) as op:
    ws.visit(caller, ws.minutes + 120)
    inside = list(ws.visitors)
    raise LLMError("the model failed")
check("someone who came looking inside an operation that did not stand is no visitor", op.state == "rolled_back" and len(inside) == 1 and not getattr(ws, "visitors", []), getattr(ws, "visitors", None))
with ws.operation("world", "the host reaches the gate, and the operation fails", world=True) as op:
    ws.assault = {"thread": "t", "town": "parth", "stage": 0, "minute": ws.minutes}
    raise LLMError("the model failed")
check("a fight at the gate begun in an operation that did not stand decides no town", getattr(ws, "assault", None) is None, getattr(ws, "assault", None))
ws.learn_options, ws.learn_request = ["what was offered before"], "the sword"
with ws.operation("action:train", "a lesson asked for, and the operation fails") as op:
    ws.learn_options, ws.learn_request = ["what is offered now"], "the bow"
    raise LLMError("the model failed")
check("what was asked of an instructor goes back with what was offered for it", (ws.learn_options, ws.learn_request) == (["what was offered before"], "the sword"),
      (ws.learn_options, ws.learn_request))

# ---- the ledger's told marks: any operation that took rows to tell and did not stand
ledger.begin()
ws.begin_line()
with ws.operation("action:other", "a deed that stands") as op:
    ledger.add("refused", say="THE DEED.")
    store.save_player(ws.player)
check("(a deed stands, not yet told)", op.state == "committed" and ledger.untold() == ["THE DEED."], (op.state, ledger.untold()))
with ws.operation("tail", "the world's own telling fails", world=True) as op:
    took = ledger.told()
    raise LLMError("the model failed")
check("rows an operation took to tell are untold again when it does not stand, whoever asked", took == ["THE DEED."] and op.state == "rolled_back" and ledger.untold() == ["THE DEED."],
      (took, ledger.untold()))
with ws.operation("passage", "the telling stands") as op:
    ledger.told()
    store.save_player(ws.player)
check("...and stay told when it does", op.state == "committed" and ledger.untold() == [])
with ws.operation("tail", "a later operation fails", world=True) as op:
    ledger.told()
    ws.__dict__.setdefault("repairs", []).append({"rule": "made inside"})
    ws.camp_log("sneak", "made inside")
    raise LLMError("the model failed")
check("a row told by an operation that stood stays told when a later one does not", op.state == "rolled_back" and ledger.untold() == [], ledger.untold())
check("what an operation noted of its own doing (a repair, a try at a camp) goes back with it", not getattr(ws, "repairs", None) and not ws.camp_events,
      (getattr(ws, "repairs", None), ws.camp_events))
ledger.end()
store.arm(False)
g.close()
shutil.rmtree("saves/rollback_720", ignore_errors=True)


# ---- where the opening stands the player is the save's before the first line
g = simlib.campaign("rollback_720_open", cls="warrior", seed=5, location="south_fields")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/rollback_720_open/turns.jsonl"
at_first_line = {}


def first_line(*a, **k):
    at_first_line.update(memory=ws.player.spot, save=store.load_player().spot)
    return "quit"


console.put("ask", first_line)
with contextlib.redirect_stdout(io.StringIO()):
    ws.run()
check("the part of the place the opening stands the player at is in the save before any line is typed: a first operation that fails reads it back",
      at_first_line.get("memory") and at_first_line["save"] == at_first_line["memory"], at_first_line)
g.close()
shutil.rmtree("saves/rollback_720_open", ignore_errors=True)


# ---- by running: every third operation fails at its end
OPAQUE = ("WorldScene", "CombatScene", "CampaignStore", "CampaignSession", "World", "TraitCatalog", "ActorContext", "Streams")


def canon(v, depth=0, seen=frozenset()):
    if isinstance(v, (str, int, float, bool, type(None))):
        return v
    if depth > 7 or id(v) in seen or type(v).__name__ in OPAQUE:
        return f"<{type(v).__name__}>"
    seen = seen | {id(v)}
    if isinstance(v, random.Random):
        return ("Random", hash(v.getstate()))
    if isinstance(v, dict):
        return {str(k): canon(x, depth + 1, seen) for k, x in sorted(v.items(), key=lambda kv: str(kv[0]))}
    if isinstance(v, (list, tuple, collections.deque)):
        return [canon(x, depth + 1, seen) for x in v]
    if isinstance(v, (set, frozenset)):
        return sorted(str(canon(x, depth + 1, seen)) for x in v)
    if hasattr(v, "id") and hasattr(v, "model_dump"):
        return f"<{type(v).__name__} {v.id}>"             # a person or a record: who, not what the save holds of them
    if hasattr(v, "model_dump"):
        return {type(v).__name__: canon(v.model_dump(), depth + 1, seen)}
    if callable(v):
        return "<callable>"
    if hasattr(v, "__dict__"):
        return {type(v).__name__: canon({k: x for k, x in vars(v).items() if not k.startswith("_")}, depth + 1, seen)}
    return repr(v)[:80]


def first(x, y, path="") -> str:
    """Where two snapshots first part, for the failure's line."""
    if isinstance(x, dict) and isinstance(y, dict):
        for k in sorted(set(x) | set(y)):
            if x.get(k, "<none>") != y.get(k, "<none>"):
                return first(x.get(k, "<none>"), y.get(k, "<none>"), f"{path}.{k}")
    if isinstance(x, list) and isinstance(y, list):
        for i, (a, b) in enumerate(zip(x, y)):
            if a != b:
                return first(a, b, f"{path}[{i}]")
        return f"{path}: {len(x)} items -> {len(y)}"
    return f"{path}: {str(x)[:60]!r} -> {str(y)[:60]!r}"


def may_move(name: str) -> bool:
    """A failed operation may leave this changed: declared kept; a field of the turn that no failure puts back (the line's own
    record, which the failure itself writes); the step being done, none after a failure (give_back says so)."""
    if name in F:
        return actor.ROLLED not in F[name].marks or name == "step"
    return name in T and T[name].how == actor.KEPT


READ_FILLS = ("book_seen", "prepared", "loadout_room", "pronoun")   # what a read fills in on the record, in memory: the loadout settled by
# whoever reads it (engine/loadout.py prepared), the pronoun worked out from the character's own text (engine/truth.py). A reload
# undoes that and the next read does it again, the same


def snap(scene) -> dict:
    """Everything the scene holds: the turn's fields, every attribute that is not private or set once, the character's record
    (but what a read fills in again by itself), the fight by its serial, and which of the turn's rows are told."""
    out = {k: canon(v) for k, v in actor.turn_of(scene).values.items()}
    out.update({k: canon(v) for k, v in scene.__dict__.items() if not k.startswith("_") and k not in by("ONCE")})
    record = scene.player.model_dump()
    for k in READ_FILLS:
        record["character"].pop(k)
    out["player"] = canon(record)
    out["combat"] = scene.combat.fight.serial if scene.combat else None
    out["(told)"] = sorted(id(r) for r in ledger.this_turn() if r.get("told"))
    return out


count = {"ops": 0, "failed": 0}
moved: dict[str, collections.Counter] = {}
stood: set = set()
undeclared: set = set()
replaced: set = set()
real = WorldScene.operation


@contextlib.contextmanager
def failing(self, kind, text="", where="turn", world=False, op_id=""):
    count["ops"] += 1
    n = count["ops"]
    cm = real(self, kind, text, where, world, op_id)
    op = cm.__enter__()
    before, once = snap(self), {k: id(self.__dict__.get(k)) for k in by("ONCE")}
    planted = False
    try:
        try:
            yield op
            if n % 3 == 0:
                planted = True
                count["failed"] += 1
                raise LLMError("planted by the test")
        except BaseException as e:
            if not cm.__exit__(type(e), e, e.__traceback__):
                raise
        else:
            cm.__exit__(None, None, None)
    finally:
        if planted:
            after = snap(self)
            for k in sorted(set(before) | set(after)):
                if before.get(k, "<unset>") == after.get(k, "<unset>") or (k == "(told)" and after[k] == before[k]):
                    continue
                if may_move(k):
                    stood.add(k)
                else:
                    moved.setdefault(k, collections.Counter())[f"{kind} {first(before.get(k, '<unset>'), after.get(k, '<unset>'))}"] += 1
            replaced.update(k for k in once if id(self.__dict__.get(k)) != once[k])
        undeclared.update(k for k in self.__dict__ if not declared(k))
        undeclared.update(k for k in actor.turn_of(self).values if k not in F)


WorldScene.operation = failing
shutil.rmtree("saves/rollback_720_run", ignore_errors=True)
session = CampaignSession.open("rollback_720_run")
store = session.store
store.meta.seed, store.meta.turn, store.meta.minutes = 39, 1, 480
store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(39))
player = PlayerState(character=char, location=session.world.start_location)
player.mentor["never"] = True
store.save_player(player)
config.TURN_LOG_PATH = "saves/rollback_720_run/turns.jsonl"
ws = session.scene(load_traits(), store.load_player())
bot = nightbot.Bot(ws, ws.world, random.Random(39), stub=stub, persona="wanderer")
stub.bot = bot
typed = {"n": 0}


def ask(*a, **k):
    if not k.get("main", a[0] if a else False):
        return "yes"
    typed["n"] += 1
    return "quit" if typed["n"] > 40 else bot.decide()[0]


simlib.quiet_console()
console.put("ask", ask)
fault = ""
try:
    with contextlib.redirect_stdout(io.StringIO()):
        ws.run()
except Exception as e:                                   # the session's own fault is the test's finding, not its crash
    fault = f"{type(e).__name__}: {e}"
finally:
    WorldScene.operation = real
    session.close()
    shutil.rmtree("saves/rollback_720_run", ignore_errors=True)
check("a session is played with every third operation failed at its end", not fault and count["failed"] >= 40 and typed["n"] > 40, (fault, count, typed))
check("after each, everything the scene holds is as the operation found it, but what is declared kept and the line's own record of the failure",
      not moved, {k: dict(v) for k, v in moved.items()})
check("...the comparison saw the scene move: the failure's own record, and something declared kept", {"line_failed", "halted"} <= stood and stood & by("KEPT"), sorted(stood))
check("...what is set once is the same object", not replaced, sorted(replaced))
check("...and the scene holds nothing the table does not declare", not undeclared, sorted(undeclared))
held_stub()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
