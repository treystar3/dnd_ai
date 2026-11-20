"""(f781) A fault the game carries on past is written down, and a fence stops a new silent handler (TASK_FAILURE-2,
docs/design/33_audit_fix_plan/task_failure.md; silent-excepts-1, docs/design/32_code_audit/tables/silent_excepts.md).

A fault is written to logs/crash.log "so it still surfaces" (f449). A broad `except Exception` that passes, or answers for the
fault, left no record anywhere. Held here:
- engine/crashlog.py carried(where, quiet=(), **context): an Interrupt goes on up; a type in `quiet` (a failure filed elsewhere) is only
  counted; any other Exception is recorded once per (where, error type) a session and counted after that, one `where` naming one
  subject; it never raises a fault of its own, even when the record itself fails, and a `quiet` that is no exception type is refused
  as the block is entered. Its count is capped at crashlog.KEEP and is a row of engine/owned.py the session settles: before it is
  emptied, crashlog.settle() writes the faults met more than once with their counts.
- its first users, the five handlers the audit's wider table sorts "record it once": a scene cache and a declared state that cannot
  be copied for the rollback (engine/session.py begin_turn, kept by reference), the embedder turned off for the session (llm/embed.py
  vectors), and the server's context sized from the numbers in code (llm/runtime.py needed_context); and a sixth the plan left
  unsorted, what a let-go fight was for (services/fight.py purpose_of: the ordinary cases read by shape, only a purpose there that
  does not read is carried).
- the fence: every broad handler (bare, Exception, BaseException, alone or in a tuple) in the game's own code (what
  owned_state_633_test calls the game: every .py git lists, tracked or not, outside tools/, data/, docs/, .claude/ and the root
  harnesses) passes when it re-raises (a `raise` at the top of its body), or writes down what it caught (a call of engine.crashlog's
  record or note, by whatever import), or stands in a list here, keyed by file and function with a reason each. Two rings, the
  audit's two tables: ring one, a handler whose whole body is pass, continue, break, `...` or a return of a constant, and a
  contextlib.suppress of Exception or BaseException; ring two, any other that carries on. Each ring has a list of handlers left as
  they are, with why, and a list still to mend, each naming what empties it. A third rule, the Interrupt's: a broad handler round a
  direct model call (llm.gateway generate, llm.backend chat and embed, llm.embed vectors, closest and whole, engine.relevance pick,
  stands_out and ranked), or one that writes down, must let an Interrupt through (an earlier handler of the same try catching
  Interrupt and raising it, or the broad one re-raising). The lists may only shrink: a handler found and not listed fails, and so
  does a listed one no longer found.
- one where names one subject: a carried() in the game's own code that hands on a parameter of its function as it is in its context
  (task=task) names it in its where, so a tally failing for four tasks is an entry each and the settled count names them.
What the fence does not read: a handler outside the game's own code (tools/, simbot.py and the other root harnesses); a handler of a
named type, however wide (OSError, ValueError, RuntimeError); a broad catch spelled through a name (`E = Exception`, a tuple held in a
name, a suppress handed a name); except* (a TryStar is not walked); a handler that writes down in one branch only (any such call
counts); whether what is written down is the fault itself; a re-raise: any `raise` at the top of a handler's body counts, though an
early return in an `if` before it carries on; the count by function: a handler mended and a new one added in the same function keep
the count and pass; "not sorted" on a list is an open hatch, a reason that names no feature; and, for the Interrupt rule, a model call
reached through a method, a protocol or a helper, among them scenes/law_actions.py's judge_object, engine/events.py's
populate_place, engine/intent_audit.py's AuditAsk, scenes/passive_hooks.py's ensure_board (tavern_ear) and npc/backfill.py's
life._ask in the background lane (start.run); only the direct calls above are seen.
Run: python tools/sim/carried_faults_781_test.py"""
import ast
import math
import subprocess
import sys
import tempfile
import shutil
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 7))
import config

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

SCRATCH = Path(tempfile.mkdtemp(prefix="carried_781_")).resolve()
for key, fn in (("LOG_PATH", "llm_calls.jsonl"), ("TURN_LOG_PATH", "turns.jsonl"), ("REFUSALS_LOG_PATH", "refusals.jsonl"), ("CRASH_LOG_PATH", "crash.log")):
    setattr(config, key, str(SCRATCH / "logs" / fn))               # what the game writes down stays here, never in the project's logs/
from engine import crashlog
from llm.errors import Cancelled, LLMError


def entries() -> list[str]:
    """crash.log's entries as they stand on disk."""
    p = crashlog.path()
    return [e for e in p.read_text(encoding="utf-8").split(crashlog.SEP) if e.strip()] if p.exists() else []


def mark() -> list[dict]:
    """The entries crashlog.SESSION holds now: it keeps only the last KEEP, so its length says nothing once full. Held, so no
    new entry can take the identity of one let go."""
    return list(crashlog.SESSION)


def new_wheres(since: list[dict]) -> list[str]:
    old = {id(e) for e in since}
    return [e["where"] for e in crashlog.SESSION if id(e) not in old]


def count(where: str, kind: str) -> int:
    """How many times carried has met this (where, error type) since the session last settled its count."""
    return (crashlog.CARRIED.get((where, kind)) or (0,))[0]


# ---- 1. the helper
carried = getattr(crashlog, "carried", None)
check("(f781) engine/crashlog.py has carried(where, quiet=(), **context), the one way to carry on past a fault and write it down",
      carried is not None)
if carried is not None:
    try:
        with carried("f781 probe: a cancel"):
            raise Cancelled("the campaign that asked is closing")
        out = None
    except Cancelled as e:
        out = e
    check("an Interrupt raised inside carried comes out: a cancel is never a fault", isinstance(out, Cancelled), out)
    try:
        with carried("f781 probe: the window closed"):
            raise KeyboardInterrupt
        out = None
    except KeyboardInterrupt as e:
        out = e
    check("...and so does what is no Exception (Ctrl+C)", isinstance(out, KeyboardInterrupt), out)

    n0, f0 = mark(), len(entries())
    went_on = 0
    for i in range(60):
        with carried("f781 probe: sixty", probe=i):
            raise ValueError(f"fault number {i}")
        went_on += 1
    check("the same ValueError raised sixty times at one place leaves one crash entry and a count of sixty, and the game goes on each time",
          new_wheres(n0) == ["f781 probe: sixty"] and len(entries()) - f0 == 1 and count("f781 probe: sixty", "ValueError") == 60
          and went_on == 60, (new_wheres(n0), len(entries()) - f0, dict(crashlog.CARRIED)))
    check("...and that entry is record()'s, with where, the error, the context given and the traceback",
          "f781 probe: sixty: ValueError: fault number 0" in entries()[-1] and "probe: 0" in entries()[-1] and "Traceback" in entries()[-1], entries()[-1][:300])
    with carried("f781 probe: sixty"):
        raise KeyError("another kind")
    check("...another type at the same place is an entry of its own", new_wheres(n0) == ["f781 probe: sixty"] * 2, new_wheres(n0))

    before, f0 = list(crashlog.SESSION), len(entries())
    with carried("f781 probe: quiet", quiet=(LLMError, OSError)):
        raise LLMError("the gateway has filed this one")
    with carried("f781 probe: quiet", quiet=(LLMError, OSError)):
        raise PermissionError("a log that cannot be written now")
    with carried("f781 probe: quiet", quiet=LLMError):
        raise LLMError("one type given alone")
    check("a quiet type (a failure filed elsewhere, given in a tuple or alone) leaves no crash entry and crashlog.SESSION as it was, "
          "and is counted", crashlog.SESSION == before and len(entries()) == f0 and count("f781 probe: quiet", "LLMError") == 2
          and count("f781 probe: quiet", "PermissionError") == 1, (crashlog.SESSION[len(before):], dict(crashlog.CARRIED)))

    for bad_quiet in (None, (ValueError, "not a type"), [ValueError]):
        ran = []
        try:
            with carried("f781 probe: a bad quiet", quiet=bad_quiet):
                ran.append(1)
            refused = None
        except TypeError as e:
            refused = e
        check(f"a quiet that is no exception type ({bad_quiet!r}) is refused as the block is entered, before the work runs, never out of "
              "the handler", isinstance(refused, TypeError) and not ran, (refused, ran))

    from engine import owned, session
    row = owned.STATE.get("engine.crashlog.CARRIED")
    f0 = len(entries())
    session.reset()
    told = entries()[-1] if len(entries()) > f0 else ""
    check("the count is a row of engine/owned.py the session settles: before it is emptied, one entry names each fault written down "
          "and met again, with its count (a quiet one stays out, a fault met once is not repeated)",
          row is not None and row.put_back is not None and crashlog.CARRIED == {} and len(entries()) == f0 + 1
          and "f781 probe: sixty (ValueError): 60 times" in told and "KeyError" not in told and "quiet" not in told, told)
    f0 = len(entries())
    with carried("f781 probe: once"):
        raise ValueError("met once")
    session.reset()
    check("...and a session whose faults were each met once settles with no entry beyond theirs", len(entries()) == f0 + 1, len(entries()) - f0)

    for i in range(crashlog.KEEP + 25):
        with carried(f"f781 probe: cap {i}"):
            raise RuntimeError("one of many places")
    check("the once-store never passes its cap (crashlog.KEEP, the entries crash.log keeps); the newest places are the ones kept",
          len(crashlog.CARRIED) == crashlog.KEEP and (f"f781 probe: cap {crashlog.KEEP + 24}", "RuntimeError") in crashlog.CARRIED
          and ("f781 probe: cap 0", "RuntimeError") not in crashlog.CARRIED, len(crashlog.CARRIED))

    real_record = crashlog.record
    def refused(*a, **k):
        raise RuntimeError("the record itself fails")
    crashlog.record = refused
    try:
        with carried("f781 probe: the record fails"):
            raise ValueError("a fault to write down")
        went = True
    except BaseException as e:
        went = e
    finally:
        crashlog.record = real_record
    check("carried never raises a fault of its own: a record that itself fails costs the caller nothing, and the fault is still counted",
          went is True and count("f781 probe: the record fails", "ValueError") == 1, went)

    session.reset()

# ---- 2. its first users: the five handlers sorted "record it once"
import copy
from engine import actor


class Uncopyable:
    """What a scene cache can hold that deepcopy refuses (a handle, a lock)."""
    def __deepcopy__(self, memo):
        raise TypeError("this cache holds a handle that cannot be copied")


g = simlib.campaign("carried_781", seed=7, location="parth")
ws = g.scene
ws._handle = Uncopyable()
ws._handle_too = Uncopyable()                             # a second cache failing the same way: a subject of its own
ws.odd_state = Uncopyable()
ws.ROLLED = (*type(ws).ROLLED, "odd_state")
n0 = mark()
g.session.begin_turn(ws)
snap = actor.turn_of(ws).snapshot
held, rolled = snap[1], snap[2]
first = new_wheres(n0)
g.session.begin_turn(ws)
check("(f781) a scene cache and a declared state that cannot be copied for the rollback are kept by reference, as before, and each is "
      "written down once a session under its own name: two caches failing the same way are two entries",
      held.get("_handle") is ws._handle and held.get("_handle_too") is ws._handle_too and rolled.get("odd_state") is ws.odd_state
      and sorted(first) == sorted(["a scene cache copied for the rollback (kept by reference): _handle",
                                   "a scene cache copied for the rollback (kept by reference): _handle_too",
                                   "a scene's declared state copied for the rollback (kept by reference): odd_state"])
      and new_wheres(n0) == first, (first, new_wheres(n0)))
check("...and a cache that copies is copied, as before", "_handle" in held and all(held[k] is not getattr(ws, k) for k in held
      if not k.startswith("_handle") and isinstance(held[k], (dict, list, set))),
      [k for k in held if not k.startswith("_handle") and held[k] is getattr(ws, k)][:5])
del ws._handle, ws._handle_too, ws.odd_state, ws.ROLLED
actor.turn_of(ws).snapshot = None
g.session.close()

from llm import embed


def embed_with(fn, name: str):
    """vectors() asked once with a stand-in embedder answering by fn: (what it gave, whether the embedder is off, the new crash wheres,
    what was raised)."""
    h = simlib.stand_in(embed=fn, name=name)
    embed._cache.clear()
    embed.reset()
    n0 = mark()
    try:
        got, raised = embed.vectors([f"a line {name} never embedded"]), None
    except BaseException as e:
        got, raised = None, e
    finally:
        h()
    off = embed.failed()
    embed.reset()
    return got, off, new_wheres(n0), raised


def misshapen(**k):
    return {"no": "embeddings"}                       # an answer of the wrong shape: the game's own fault reading it


def gone(**k):
    raise ConnectionError("the embedder's server went away")


def too_big(**k):
    from llm.errors import Failure
    raise Failure("too_big", "the request does not fit")


def cancelled(**k):
    raise Cancelled("the campaign that asked is closing")


got, off, wheres, raised = embed_with(misshapen, "misshapen")
check("(f781) an embed call that fails with the game's own fault turns the embedder off for the session, as before, and is written down",
      got is None and off and raised is None and len(wheres) == 1 and "embedder" in wheres[0], (got, off, wheres, raised))
got, off, wheres, raised = embed_with(gone, "gone")
check("...a failure of the embedder's server turns it off as before, and is no crash of the game's", got is None and off and wheres == []
      and raised is None, (got, off, wheres, raised))
got, off, wheres, raised = embed_with(too_big, "too big")
check("...a request too big is that call's own fallback: the embedder stays on, nothing written", got is None and not off and wheres == [],
      (got, off, wheres))
got, off, wheres, raised = embed_with(cancelled, "cancelled")
check("...and a cancel goes on up, the embedder left on and nothing written", isinstance(raised, Cancelled) and not off and wheres == [],
      (raised, off, wheres))

from core import paths
from llm import runtime
real_bundle = paths.BUNDLE
n0 = mark()
plain = runtime.needed_context()
check("the server's context read from the measured ceilings writes nothing down", new_wheres(n0) == [], new_wheres(n0))
bare_bundle = SCRATCH / "bundle"
(bare_bundle / "data" / "rules").mkdir(parents=True)
paths.BUNDLE = bare_bundle
try:
    n0 = mark()
    fallen = runtime.needed_context()
    expect = math.ceil(36500 / 4.0) + 2 * runtime.largest_answer()
finally:
    paths.BUNDLE = real_bundle
sized = [{k: v for k, v in e.items() if k.startswith("sized")} for e in crashlog.SESSION if id(e) not in {id(x) for x in n0}]
check("(f781) the server's context sized from the numbers in code when the measured ceilings and budget.yaml cannot be read, as before, "
      "and each written down with the number it was sized from", fallen == expect and len(new_wheres(n0)) == 2
      and all("server's context" in w for w in new_wheres(n0)) and sized == [{"sized_from": 36500}, {"sized_at": 4.0}],
      (fallen, expect, new_wheres(n0), sized))

import json
from services.fight import FightService
n0 = mark()
ordinary = {"no notice": None, "the bare notice": "1", "a row that is not JSON": "{cut", "a row of another shape": "[1, 2]",
            "a fight with no purpose": json.dumps({"fight": {"round": 3}}), "a notice with no purpose": json.dumps({"fight": {"purpose": None}})}
read = {label: FightService.purpose_of(raw) for label, raw in ordinary.items()}
check("(f781) what a let-go fight was for: no notice, the bare notice \"1\", a row that is not JSON (CombatScene.resume writes that "
      "one down) and a row with no purpose all read None, and nothing is written down", all(v is None for v in read.values())
      and new_wheres(n0) == [], (read, new_wheres(n0)))
kept = FightService.purpose_of(json.dumps({"fight": {"purpose": {"kind": "gate", "data": {"town": "parth"}, "by": "p1"}}}))
check("...a purpose that reads is handed on, as before", kept is not None and kept.kind == "gate" and kept.data == {"town": "parth"}
      and new_wheres(n0) == [], (kept, new_wheres(n0)))
lost = FightService.purpose_of(json.dumps({"fight": {"purpose": {"kind": 5, "flag": True}}}))
check("...and a purpose of another shape is None and one entry: lost with the fight, never silently", lost is None
      and len(new_wheres(n0)) == 1 and "let-go fight" in new_wheres(n0)[0], (lost, new_wheres(n0)))

# ---- 3. the fence
NOT_GAME = {"tools", "data", "docs", ".claude"}
HARNESS = {"simlib", "simbot", "simreport", "smoke_test", "bestiary_check", "world_check"}
BROAD = {"Exception", "BaseException"}
WRITERS = {"engine.crashlog": {"record", "note"}}
MODEL = {"llm.gateway": {"generate"}, "llm.backend": {"chat", "embed"}, "llm.embed": {"vectors", "closest", "whole"},
         "engine.relevance": {"pick", "stands_out", "ranked"}}
DEFS = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)


def dotted(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = dotted(node.value)
        return None if head is None else f"{head}.{node.attr}"
    return None


def kinds(t) -> list[str]:
    return [] if t is None else [(dotted(e) or "?").rsplit(".", 1)[-1] for e in (t.elts if isinstance(t, ast.Tuple) else [t])]


def broad(h) -> bool:
    return h.type is None or bool(set(kinds(h.type)) & BROAD)


def constant(n) -> bool:
    if n is None or isinstance(n, ast.Constant):
        return True
    if isinstance(n, (ast.Tuple, ast.List, ast.Set)):
        return all(constant(e) for e in n.elts)
    if isinstance(n, ast.Dict):
        return all(constant(k) for k in n.keys if k is not None) and all(constant(v) for v in n.values)
    if isinstance(n, ast.UnaryOp):
        return constant(n.operand)
    return False


def silent(body) -> bool:
    """Ring one's body: pass, continue, break, a bare constant (`...`, a string) or a return of a constant, and nothing else."""
    return all(isinstance(s, (ast.Pass, ast.Continue, ast.Break)) or (isinstance(s, ast.Return) and constant(s.value))
               or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)) for s in body)


def own(nodes):
    """Every node under these, but those of a function, a lambda or a class inside them."""
    todo = list(nodes)
    while todo:
        n = todo.pop()
        yield n
        if not isinstance(n, (*DEFS, ast.Lambda)):
            todo.extend(ast.iter_child_nodes(n))


def scan(text, module: str = "") -> list[tuple[str, str, int]]:
    """Each broad handler of a module that carries on without writing down what it caught (a contextlib.suppress of Exception or
    BaseException among them), and each round a direct model call, or writing down, that does not let an Interrupt through: (rule,
    function, line), the rule "one", "two" or "interrupt", the function dotted with its classes. `module` is the module's dotted name:
    in engine/crashlog.py its own record and note write down."""
    tree = text if isinstance(text, ast.AST) else ast.parse(text)
    mods, names = {}, {}                               # local name -> module (writers and model calls), local name -> (module, function)
    names.update({fn: (module, fn) for fn in WRITERS.get(module, ())})
    suppress = set()                                   # what contextlib.suppress is called here
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name in WRITERS or a.name in MODEL:
                    mods[a.asname or a.name] = a.name
                elif a.name == "contextlib":
                    suppress.add(f"{a.asname or a.name}.suppress")
        elif isinstance(n, ast.ImportFrom) and n.module == "contextlib" and not n.level:
            suppress |= {a.asname or a.name for a in n.names if a.name == "suppress"}
        elif isinstance(n, ast.ImportFrom) and n.module and not n.level:
            for a in n.names:
                full = f"{n.module}.{a.name}"
                if full in WRITERS or full in MODEL:
                    mods[a.asname or a.name] = full
                elif n.module in WRITERS or n.module in MODEL:
                    names[a.asname or a.name] = (n.module, a.name)

    def target(call) -> tuple[str, str] | None:
        d = dotted(call.func) or ""
        if d in names:
            return names[d]
        head, _, fn = d.rpartition(".")
        return (mods[head], fn) if head in mods else None

    def calls(nodes, table) -> bool:
        return any(isinstance(x, ast.Call) and (t := target(x)) is not None and t[1] in table.get(t[0], ()) for x in own(nodes))
    out = []

    def visit(node, stack) -> None:
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, DEFS):
                visit(ch, stack + [ch.name])
                continue
            where = ".".join(stack) or "<module>"
            if isinstance(ch, (ast.With, ast.AsyncWith)):
                for item in ch.items:
                    c = item.context_expr
                    if isinstance(c, ast.Call) and dotted(c.func) in suppress and set(sum((kinds(a) for a in c.args), [])) & BROAD:
                        out.append(("one", where, ch.lineno))
            if isinstance(ch, ast.Try):
                through = False
                model = calls(ch.body, MODEL)
                for h in ch.handlers:
                    raises = any(isinstance(s, ast.Raise) for s in h.body)
                    if "Interrupt" in kinds(h.type) and raises:
                        through = True
                    if not broad(h):
                        continue
                    writes = calls(h.body, WRITERS)
                    if (model or writes) and not through and not raises:
                        out.append(("interrupt", where, h.lineno))
                    if not raises and not writes:
                        out.append(("one" if silent(h.body) else "two", where, h.lineno))
            visit(ch, stack)
    visit(tree, [])
    return out


def counts(found, rule) -> dict:
    out: dict = {}
    for f, r, fn, _ in found:
        if r == rule:
            out[(f, fn)] = out.get((f, fn), 0) + 1
    return out


# ring one: a handler whose whole body is pass, continue, break or a return of a constant
ONE_LEAVE = {
    ("core/updates.py", "latest_release"): (1, "the release check, off the game's thread: offline or an answer that does not read is no release offered"),
    ("core/updates.py", "_leave"): (1, "the game's last act before the installer (os._exit follows): the server is left to the OS's job object"),
    ("engine/crashlog.py", "carried"): (1, "crash.log's own writer: a fault in writing a fault down has nowhere to go; carried counted it first"),
    ("engine/pulse.py", "apply_effects"): (1, "the pulse log's row for an effect already applied: a log row lost, nothing of the world"),
    ("engine/recording.py", "commit"): (1, "git asked for the commit a recording names: no git is no commit named"),
    ("engine/threads.py", "problems"): (1, "an import inside the startup check: a game that cannot import it does not start anyway"),
    ("engine/turnlog.py", "_trim"): (1, "trimming the turn log, which trim_log guards itself"),
    ("engine/turnlog.py", "session_stats"): (2, "the session's stats row reads the tallies of modules that may not be loaded: a count missing from the row"),
    ("llm/audit.py", "_record"): (1, "the raw answer pretty-printed for the audit page: one that is not JSON is shown as written"),
    ("llm/backend.py", "_source_has"): (1, "a malformed DND_LLAMA_URL, written down as the reason (f523): the calls themselves then fail loudly"),
    ("llm/gateway.py", "generate"): (1, "filing the refusal row of a call that gave up: the LLMError is raised right after"),
    ("llm/gateway.py", "_generate"): (1, "filing the guarded refusal row: the call's reason is already set"),
    ("llm/gateway.py", "_debug"): (1, "the debug line of a rejected try: a console fault costs a debug line"),
    ("llm/runtime.py", "_pdeathsig"): (1, "prctl on Linux: no libc, or another system"),
    ("llm/runtime.py", "Runtime._load"): (1, "the load screen's callback (the slow-machine warning): the model is loaded whatever the page does"),
    ("llm/runtime.py", "Runtime._wait_ready"): (1, "the loading line's callback: a page fault costs a progress line"),
    ("llm/setup_check.py", "ram_gb"): (1, "the machine's memory: 0.0 is read as unknown"),
    ("llm/worker.py", "Worker._strict"): (1, "importing engine.streams to read STRICT: background calls then run as in live play"),
    ("storage/invariants.py", "known_places"): (1, "a save from before discoveries: the checker then reports more, not less"),
    ("storage/statehash.py", "data_hashes"): (1, "a wording-listed file that is not YAML is hashed whole, the stricter way"),
}
TF10 = "TASK_FAILURE-10"
ONE_TO_MEND = {
    ("engine/canon.py", "journal"): (1, f"{TF10}: remove the try (or carry, the owner's choice on the journal)"),
    ("engine/combat_perks.py", "is_challenge"): (1, f"{TF10}: remove the try (relevance.pick falls back by itself)"),
    ("engine/deeds.py", "log"): (1, f"{TF10}: remove the try (the operation rolls back)"),
    ("engine/events.py", "player_level"): (1, f"{TF10}: remove the try"),
    ("engine/events.py", "after_deed"): (1, f"{TF10}: ask whether the place is on the map, then carry (the owner's choice on the town's thanks)"),
    ("engine/events.py", "finish"): (1, f"{TF10}: the town's thanks (the owner's choice)"),
    ("engine/events.py", "_player_in"): (1, f"{TF10}: remove the try"),
    ("engine/events.py", "assault_over"): (1, f"{TF10}: the town's thanks (the owner's choice)"),
    ("engine/mentor.py", "build_of"): (1, f"{TF10}: narrow to KeyError"),
    ("engine/moments.py", "_town_last"): (1, f"{TF10}: remove the try"),
    ("engine/moments.py", "choose"): (1, f"{TF10}: remove the try"),
    ("engine/phantoms.py", "found"): (1, f"{TF10}: carry on with a record (crashlog.carried)"),
    ("engine/world_improv.py", "read_effect"): (1, f"{TF10}: remove the try (relevance.pick falls back by itself)"),
    ("scenes/audit_actions.py", "AuditActions.people_at"): (1, f"{TF10}: narrow to FileNotFoundError"),
    ("scenes/audit_actions.py", "AuditActions.pack_names"): (1, f"{TF10}: remove the try"),
    ("scenes/banter_actions.py", "BanterActions.party_news"): (1, f"{TF10}: remove the try"),
    ("scenes/combat_scene.py", "read_effect"): (1, f"{TF10}: remove the try (relevance.pick falls back by itself)"),
    ("scenes/law_actions.py", "LawActions.invent_lock"): (1, f"{TF10}: narrow to LLMError"),
    ("scenes/law_actions.py", "LawActions.on_answer_law"): (1, f"{TF10}: narrow to FileNotFoundError"),
    ("scenes/passive_hooks.py", "PassiveHooks.tavern_ear"): (1, f"{TF10}: carry, with LLMError quiet"),
    ("scenes/quirk_actions.py", "QuirkActions.gesturers"): (1, f"{TF10}: remove the try"),
    ("scenes/road_actions.py", "RoadActions.road_company"): (1, f"{TF10}: remove the try"),
    ("npc/backfill.py", "collect"): (1, "TASK_FAILURE-16: one transaction, carried"),
    ("scenes/dungeon_actions.py", "DungeonActions.void_dungeon_contracts"): (1, "scenes1-13, another workstream's: remove the try"),
}
# ring two: any other broad handler that carries on unwritten (a default set, a debug line, the error kept)
TWO_LEAVE = {
    ("character/creation.py", "PassivesInBackground._run"): (1, "the error kept for result(), which reports it and retries"),
    ("core/selfcheck.py", "run"): (1, "the self-check: a part that raises is that part's problem, written to selfcheck.log with its trace"),
    ("core/updates.py", "install"): (1, "the error's text returned to the update card"),
    ("engine/crashlog.py", "_said"): (1, "crash.log's own writer: a value whose __str__ raises is written as its type; it has nowhere to go"),
    ("engine/asked.py", "call"): (1, "kept and raised again by kind, by design"),
    ("engine/data_check.py", "_why"): (1, "a better message for a file that already failed: the loader's own words are the problem reported"),
    ("engine/data_check.py", "check"): (3, "reported as a startup problem"),
    ("engine/threads.py", "_effect"): (1, "a debug line: the startup check reads the template before play"),
    ("llm/gateway.py", "_generate"): (1, "one try of a model call: the call log's row and the tally are its record; a cancel goes up as Cancelled"),
    ("llm/launch.py", "Screen._load.run"): (1, "the error kept for the load screen"),
    ("llm/launch.py", "Screen._could_not_wake"): (1, "the machine's memory unknown"),
    ("llm/runtime.py", "runtime_problems"): (1, "the slot check skipped when the budget table cannot be read: the startup check reads that table"),
    ("llm/runtime.py", "Spawner._run"): (1, "the error kept for the caller"),
    ("llm/runtime.py", "Runtime._died"): (1, "the runtime marked failed: the load screen tells it"),
    ("main.py", "play"): (1, "told to the player: the llama-server at DND_LLAMA_URL could not be reached"),
    ("scenes/goddess.py", "ThresholdScene.show"): (1, "a creation page that cannot be drawn: a debug line, the conversation goes on"),
    ("scenes/world.py", "WorldScene.asked_operation"): (1, "kept and served back to the operation, by design"),
    ("services/fight.py", "FightService.resume"): (1, "why is returned; the caller writes it to crash.log ('fight row')"),
    ("storage/statehash.py", "dump"): (1, "an older save without that table"),
    ("storage/statehash.py", "wording_problems"): (1, "reported as a wording problem"),
    ("ui/gui/__init__.py", "_window"): (1, "the reason is shown and the game opens in the browser instead"),
}
TWO_TO_MEND = {
    ("engine/events.py", "_leaders"): (1, f"{TF10}: narrow to LLMError"),
    ("engine/field.py", "classify"): (1, f"{TF10}: narrow to LLMError"),
    ("engine/mentor.py", "empty_handed"): (1, f"{TF10}: narrow to KeyError"),
    ("engine/stakes.py", "_open_matter"): (1, f"{TF10}: narrow to the contract's ValidationError"),
    ("scenes/audit_actions.py", "AuditActions.ask_back"): (1, f"{TF10}: narrow to LLMError"),
    ("scenes/law_actions.py", "LawActions.create_object"): (1, f"{TF10}: narrow to LLMError"),
    ("scenes/world.py", "WorldScene.reach_of"): (2, f"{TF10}: remove the two tries"),
    ("engine/intent_audit.py", "audit"): (1, "TASK_FAILURE-11: catch LLMError alone; a failed audit is a line not taken"),
    ("npc/backfill.py", "start.run"): (1, "TASK_FAILURE-16: a job's own error written down, not dropped"),
    ("engine/pulse.py", "apply_effects"): (1, "not sorted: an effect the world cannot honour, dropped with a debug line (task_failure.md, Open)"),
}
# the Interrupt rule: a broad handler round a direct model call, or one that writes down, that does not let an Interrupt through
INTERRUPT_LEAVE = {
    ("llm/runtime.py", "start_for_game"): (1, "the game's own server failing to start: the plain line with the lock let go (f522); it starts "
                                              "before any campaign, so nothing can cancel it yet"),
    ("main.py", "play"): (1, "the way out of creation: a cleanup that fails is written down and the way out goes on (f742); closing the "
                             "session and discarding the game make no call an Interrupt could stop"),
    ("main.py", "guarded"): (1, "the top of the game: a cancel is let go just above it (except Cancelled), and whatever else reaches it ends "
                                "the game and is written down"),
}
INTERRUPT_TO_MEND = {
    ("engine/combat_perks.py", "is_challenge"): (1, f"{TF10}: remove the try"),
    ("engine/world_improv.py", "read_effect"): (1, f"{TF10}: remove the try"),
    ("scenes/combat_scene.py", "read_effect"): (1, f"{TF10}: remove the try"),
    ("engine/field.py", "classify"): (1, f"{TF10}: narrow to LLMError"),
    ("scenes/audit_actions.py", "AuditActions.ask_back"): (1, f"{TF10}: narrow to LLMError"),
}

PLANTED = {                                            # source: the (rule, function) pairs the scan must find, no more
    "def f():\n    try:\n        g()\n    except Exception:\n        pass\n": [("one", "f")],
    "def f(xs):\n    for x in xs:\n        try:\n            g(x)\n        except Exception:\n            continue\n": [("one", "f")],
    "def f():\n    while True:\n        try:\n            g()\n        except Exception:\n            break\n": [("one", "f")],
    "def f():\n    try:\n        return g()\n    except Exception:\n        return None\n": [("one", "f")],
    "def f():\n    try:\n        return g()\n    except Exception:\n        return []\n": [("one", "f")],
    "def f():\n    try:\n        return g()\n    except Exception:\n        return -1\n": [("one", "f")],
    "def f():\n    try:\n        g()\n    except:\n        pass\n": [("one", "f")],
    "def f():\n    try:\n        g()\n    except Exception:\n        ...\n": [("one", "f")],
    "def f():\n    try:\n        g()\n    except BaseException:\n        pass\n": [("one", "f")],
    "def f():\n    try:\n        g()\n    except (KeyError, Exception):\n        return 0\n": [("one", "f")],
    "try:\n    import x\nexcept Exception:\n    x = None\n": [("two", "<module>")],
    "class A:\n    def m(self):\n        try:\n            return g()\n        except Exception as e:\n            self.error = e\n": [("two", "A.m")],
    "from ui import console\ndef f():\n    try:\n        g()\n    except Exception as e:\n        console.debug(f'gone ({e})')\n": [("two", "f")],
    "def f():\n    try:\n        a = g()\n    except Exception as e:\n        if isinstance(e, KeyError):\n            raise\n        a = {}\n": [("two", "f")],
    "def f():\n    def inner():\n        try:\n            g()\n        except Exception:\n            pass\n    return inner\n": [("one", "f.inner")],
    "from engine import relevance\nfrom engine import crashlog\ndef f(q, xs):\n    try:\n        return relevance.pick(q, xs)\n"
    "    except Exception as e:\n        crashlog.record(e, 'pick')\n        return []\n": [("interrupt", "f")],
    "from llm.gateway import generate as ask\ndef f():\n    try:\n        return ask('narrate', 's', 'u', None)\n    except Exception:\n"
    "        return None\n": [("interrupt", "f"), ("one", "f")],
    "from engine import crashlog\ndef f():\n    try:\n        g()\n    except Exception as e:\n        crashlog.record(e, 'f')\n": [("interrupt", "f")],
    "import contextlib\ndef f():\n    with contextlib.suppress(Exception):\n        g()\n": [("one", "f")],
    "from contextlib import suppress as hush\ndef f():\n    with hush(KeyError, BaseException):\n        g()\n": [("one", "f")],
    "from engine import refusals\ndef f():\n    try:\n        g()\n    except Exception as e:\n        refusals.note('refused', 'f', str(e))\n": [("two", "f")],
    # what passes
    "def f():\n    try:\n        g()\n    except Exception:\n        tidy()\n        raise\n": [],
    "def f():\n    try:\n        g()\n    except Exception as e:\n        raise RuntimeError('worse') from e\n": [],
    "from core.interrupts import Interrupt\nfrom engine import crashlog\ndef f():\n    try:\n        g()\n    except Interrupt:\n        raise\n"
    "    except Exception as e:\n        crashlog.record(e, 'f')\n": [],
    "from core.interrupts import Interrupt\nimport engine.crashlog\ndef f():\n    try:\n        g()\n    except Interrupt:\n        raise\n"
    "    except Exception as e:\n        engine.crashlog.note('f', str(e))\n": [],
    "from core.interrupts import Interrupt\nfrom engine.crashlog import record as written\ndef f():\n    try:\n        g()\n"
    "    except Interrupt:\n        raise\n    except Exception as e:\n        written(e, 'f')\n": [],
    "import contextlib\ndef f():\n    with contextlib.suppress(KeyError, FileNotFoundError):\n        g()\n": [],
    "def f():\n    try:\n        g()\n    except KeyError:\n        pass\n    except (OSError, ValueError):\n        return None\n": [],
    "from engine import crashlog\ndef f():\n    with crashlog.carried('f'):\n        g()\n": [],
    "from core.interrupts import Interrupt\nfrom engine import relevance, crashlog\ndef f(q, xs):\n    try:\n        return relevance.pick(q, xs)\n"
    "    except Interrupt:\n        raise\n    except Exception as e:\n        crashlog.record(e, 'pick')\n        return []\n": [],
    "from llm.gateway import LLMError, generate\ndef f():\n    try:\n        return generate('narrate', 's', 'u', None)\n    except LLMError:\n"
    "        return None\n": [],
    "class Bridge:\n    def install(self):\n        pass\ndef f(log):\n    try:\n        g()\n    except Exception as e:\n        log.note(e)\n        log.record(e)\n": [("two", "f")],
}
got = {src: sorted((r, fn) for r, fn, _ in scan(src)) for src in PLANTED}
wrong = {src: (got[src], sorted(want)) for src, want in PLANTED.items() if got[src] != sorted(want)}
check("(f781) the fence catches each form planted: pass, continue, break, a return of a constant (None, [], -1), a bare except, "
      "`except Exception: ...`, BaseException, a tuple holding Exception, contextlib.suppress of Exception or BaseException by any "
      "import, a default set at the module's top, the error kept, a debug line, a refusal filed in place of the fault, a re-raise in one "
      "branch only, a handler in a nested function, and a broad handler round a model call, or one that writes down, that lets no "
      "Interrupt through; and passes a re-raise, a raise from it, crashlog's record or note by any import with an Interrupt let through, "
      "a narrow handler, a narrow suppress, carried, a model failure caught as LLMError (a log object's note is not crashlog's)",
      not wrong, wrong)

files = [f for f in subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True,
                                   text=True, encoding="utf-8", check=True).stdout.split()
         if f.split("/")[0] not in NOT_GAME and Path(f).stem not in HARNESS and Path(f).is_file()]
found = [(f, r, fn, line) for f in files for r, fn, line in scan(Path(f).read_text(encoding="utf-8"), f[:-3].replace("/", "."))]
lines = {(f, r, fn): [line for g_, r_, fn_, line in found if (g_, r_, fn_) == (f, r, fn)] for f, r, fn, _ in found}


def against(rule: str, *lists) -> tuple[list, list]:
    """(found and not listed, listed and not found) for one rule: the handlers found by file and function against the lists' counts."""
    have = counts(found, rule)
    want: dict = {}
    for table in lists:
        for key, (n, _) in table.items():
            want[key] = want.get(key, 0) + n
    new = [f"{f}:{','.join(map(str, lines[(f, rule, fn)]))} ({fn}): {have[(f, fn)]} found, {want.get((f, fn), 0)} listed"
           for f, fn in have if have[(f, fn)] > want.get((f, fn), 0)]
    gone = [f"{f} ({fn}): {want[(f, fn)]} listed, {have.get((f, fn), 0)} found" for f, fn in want if want[(f, fn)] > have.get((f, fn), 0)]
    return new, gone


for rule, label, lists in (("one", "ring one (a body of pass, continue, break or a constant returned)", (ONE_LEAVE, ONE_TO_MEND)),
                           ("two", "ring two (any other broad handler that carries on unwritten)", (TWO_LEAVE, TWO_TO_MEND)),
                           ("interrupt", "the Interrupt rule (a broad handler round a model call, or one that writes down)",
                            (INTERRUPT_LEAVE, INTERRUPT_TO_MEND))):
    new, gone = against(rule, *lists)
    check(f"(f781) {label}: every handler of the game's own code that carries on without writing down what it caught is listed with a "
          f"reason, or it fails here (write it down with crashlog.carried or record, re-raise it, or list it)", not new, new)
    check(f"...and every one listed is still there: a list may only shrink, so one mended leaves it", not gone, gone)
reasons = [key for table in (ONE_LEAVE, ONE_TO_MEND, TWO_LEAVE, TWO_TO_MEND, INTERRUPT_LEAVE, INTERRUPT_TO_MEND) for key, (n, why) in table.items()
           if n < 1 or len(why.split()) < 4]
unnamed = [key for table in (ONE_TO_MEND, TWO_TO_MEND, INTERRUPT_TO_MEND) for key, (_, why) in table.items()
           if not why.startswith(("TASK_FAILURE-", "scenes1-13", "not sorted"))]
check("...each listed handler has its reason, and each still to mend names what empties it (a feature, or 'not sorted')",
      not reasons and not unnamed, (reasons, unnamed))
mended = [("engine/session.py", "CampaignSession.begin_turn"), ("llm/embed.py", "vectors"), ("llm/runtime.py", "needed_context"),
          ("services/fight.py", "FightService.purpose_of")]
check("(f781) the five sorted 'record it once', and purpose_of, are written down now and stand in no list",
      not [k for k in mended if any(k in t for t in (ONE_LEAVE, ONE_TO_MEND, TWO_LEAVE, TWO_TO_MEND))]
      and not [x for x in found if (x[0], x[2]) in mended], [x for x in found if (x[0], x[2]) in mended])


def unnamed(text) -> list[tuple[str, str]]:
    """(f781) Each crashlog.carried(...) that hands on a parameter of the function it stands in, as it is (task=task), in its context
    while its where does not name it: (function, parameter). The where named is the f-string's names; a where built elsewhere is not
    read. A value made in the function (a count, a number used) is context, no subject."""
    tree = ast.parse(text)
    mods, fns = {"engine.crashlog"}, set()
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and n.module == "engine.crashlog":
            fns |= {a.asname or a.name for a in n.names if a.name == "carried"}
        elif isinstance(n, ast.ImportFrom) and n.module == "engine":
            mods |= {a.asname or a.name for a in n.names if a.name == "crashlog"}
        elif isinstance(n, ast.Import):
            mods |= {a.asname for a in n.names if a.name == "engine.crashlog" and a.asname}
    out = []

    def visit(node, stack, params) -> None:
        for ch in ast.iter_child_nodes(node):
            if isinstance(ch, (ast.FunctionDef, ast.AsyncFunctionDef)):
                a = ch.args
                visit(ch, stack + [ch.name], {x.arg for x in a.posonlyargs + a.args + a.kwonlyargs})
                continue
            if isinstance(ch, ast.ClassDef):
                visit(ch, stack + [ch.name], set())
                continue
            d = dotted(ch.func) if isinstance(ch, ast.Call) else None
            if d and (d in fns or d.rpartition(".")[0] in mods and d.endswith(".carried")):
                where = ch.args[0] if ch.args else next((k.value for k in ch.keywords if k.arg == "where"), None)
                if isinstance(where, (ast.Constant, ast.JoinedStr)):
                    named = {x.id for x in ast.walk(where) if isinstance(x, ast.Name)}
                    out.extend((".".join(stack) or "<module>", k.value.id) for k in ch.keywords
                               if k.arg not in (None, "where", "quiet") and isinstance(k.value, ast.Name) and k.value.id in params
                               and k.value.id not in named)
            visit(ch, stack, params)
    visit(tree, [], set())
    return out


SUBJECTS = {                                           # source: the (function, parameter) pairs unnamed() must find, no more
    "from engine import crashlog\ndef _tally(task, ok):\n    with crashlog.carried('the tally of calls', task=task):\n        g()\n":
        [("_tally", "task")],
    "from engine.crashlog import carried as kept\ndef _count(name, once):\n    with kept('the count', what=name):\n        g()\n":
        [("_count", "name")],
    "import engine.crashlog as cl\nclass A:\n    def m(self, key):\n        with cl.carried('a cache', key=key, quiet=(OSError,)):\n"
    "            g()\n": [("A.m", "key")],
    "from engine import crashlog\ndef f(task):\n    def inner(task):\n        with crashlog.carried('inner', task=task):\n            g()\n"
    "    return inner\n": [("f.inner", "task")],
    # what passes
    "from engine import crashlog\ndef _tally(task):\n    with crashlog.carried(f'the tally of calls: {task}'):\n        g()\n": [],
    "from engine import crashlog\ndef f(task, what):\n    with crashlog.carried(f'the mend of the {what}: {task}', what=what):\n"
    "        g()\n": [],
    "from engine import crashlog\ndef f():\n    chars = 36500\n    with crashlog.carried('sized', sized_from=chars):\n        g()\n": [],
    "from engine import crashlog\ndef f(task, xs):\n    with crashlog.carried(f'embed: {task}', texts=len(xs)):\n        g()\n": [],
    "def f(task):\n    with carried('not crashlog', task=task):\n        g()\n": [],
}
wrong = {src: unnamed(src) for src, want in SUBJECTS.items() if unnamed(src) != want}
check("(f781) one where names one subject: the rule catches a carried() whose context hands on a parameter of its function that its "
      "where leaves out (by the module, a name imported from it, an alias, in a method and a nested function), and passes one the where "
      "names, a value made in the function, an expression, and a carried that is not crashlog's", not wrong, wrong)
loose = [f"{f} ({fn}): {p}" for f in files for fn, p in unnamed(Path(f).read_text(encoding="utf-8"))]
check("...and in the game's own code every carried() names in its where the subject it hands on, so a second subject failing the same "
      "way is an entry of its own and the settled count names it", not loose, loose)

one, two = sum(counts(found, "one").values()), sum(counts(found, "two").values())
print(f"     the game's own code: {len(files)} files; ring one {one} ({sum(n for n, _ in ONE_LEAVE.values())} left as they are, "
      f"{sum(n for n, _ in ONE_TO_MEND.values())} still to mend); ring two {two} ({sum(n for n, _ in TWO_LEAVE.values())} left, "
      f"{sum(n for n, _ in TWO_TO_MEND.values())} to mend); the Interrupt rule {sum(counts(found, 'interrupt').values())} "
      f"({sum(n for n, _ in INTERRUPT_LEAVE.values())} left, {sum(n for n, _ in INTERRUPT_TO_MEND.values())} to mend)")

shutil.rmtree(SCRATCH, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
