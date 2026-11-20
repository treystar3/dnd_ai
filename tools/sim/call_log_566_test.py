"""(f566) The model's call log can never fail a call, and the fights play to their numbers when it cannot be written.

One full suite in about sixty (2026-11-06) moved shard 2 of the fight fixtures (mechanics:vessel..withering, its second round not
fought). The suite runs four tests at once and every one logs its stub's calls to the same logs/llm_calls.jsonl, which sits near
LOG_MAX_MB, so each trims it often, and every trim went through one shared temp file: a trim could find that temp moved by another
process's (FileNotFoundError), or on Windows have its replace refused while another process held the log open (PermissionError).
gateway._log raised that out of a call already answered, past every site's LLMError fallback, and the fight round's operation rolled
back: the round was not fought and every number after it moved. Neither the background people (npc/backfill.py: simlib.install turns the
first-batch split off, so no job runs in the fixtures) nor the machine's load decide a fight. Now:

- trim_log never raises, and leaves the log whole and no temp of its own behind when the system refuses its replace;
- three processes appending to and trimming one over-full log at once raise nothing (before: hundreds of errors a second);
- shard 2 plays to its recorded numbers, with no turn rolled back, while every write of its call log is refused;
- generate() gives its answer when neither the call log nor the audit log can be written;
- a turn rolled back by a fault is named by the fixtures (its case and the error), not left to read as moved numbers.

(f782) The gateway's own bookkeeping never costs an answer or leaves it half mended (TASK_FAILURE-13; llm1-2, silent-excepts-6):
- an answer holding half a surrogate pair is sent back and asked again (generate() raised UnicodeEncodeError out of the audit's
  write after one try); a half pair in what was sent is written to the call log and the audit as its escape;
- an audit append the system refuses leaves no entry number behind it ("unchanged since #N" pointing at an entry not written), and
  is no crash; a fault of any other kind writing the call log's row, the audit's entry or the gateway's tallies costs no answer
  and is written down once;
- each mend of a taken answer (no dashes, names put right) is made on a copy and taken whole or not at all: one that fails half way
  leaves the answer as the model wrote it, is written down, and the count A1 reads moves with the names the mend found; a cancel
  inside a mend goes on up;
- a mend that fails on the second item of a list, prose or models, leaves the list and the nested models untouched (the copy is
  deep; the same case with a copy one level deep comes back half mended, shown);
- a fence: in the gateway every mend of an answer's words (hygiene's undash_answer, undash, unwrap; names' mend_answer, mend_text, by
  any import) is made inside the lambda handed to _mended(), on that lambda's own answer, and the call log, the tallies and the audit
  (four functions, each found) write under crashlog.carried. Not read by that fence: a mend made through a function of another module
  that mends in its turn, by other means (str.replace, a setattr of words made some other way) or through a module reached by
  getattr or importlib; a lambda that mends its own copy and touches the answer as well; and a piece of bookkeeping not named in it."""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/sim")
import config
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

scratch = Path(tempfile.mkdtemp(prefix="call_log_566_"))
config.CRASH_LOG_PATH = str(scratch / "crash.log")          # the faults this test makes stay out of logs/crash.log
config.LOG_PATH = str(scratch / "calls.jsonl")

# ---- a trim whose replace the system refuses
log = scratch / "trim.jsonl"
lines = [json.dumps({"n": i, "raw": "x" * 100}) for i in range(40)]
log.write_text("\n".join(lines) + "\n", encoding="utf-8")
keep_mb, keep_n = config.LOG_MAX_MB, config.LOG_KEEP_ENTRIES
config.LOG_MAX_MB, config.LOG_KEEP_ENTRIES = 0.001, 3       # about a kilobyte: this log is over it
real_replace = Path.replace

def refuse(self, target):
    raise PermissionError(13, "The process cannot access the file because it is being used by another process")

Path.replace = refuse
raised = None
try:
    gateway.trim_log(log)
except Exception as e:
    raised = e
finally:
    Path.replace = real_replace
check("a trim whose replace is refused (another process holds the log) raises nothing", raised is None, repr(raised))
check("...leaves the log whole", log.read_text(encoding="utf-8").splitlines() == lines)
check("...and no temp file of its own behind", not [p.name for p in scratch.iterdir() if p.name.endswith(".tmp")],
      [p.name for p in scratch.iterdir()])
gateway.trim_log(log)
check("a trim let through keeps the last entries", log.read_text(encoding="utf-8").splitlines() == lines[-3:])
config.LOG_MAX_MB, config.LOG_KEEP_ENTRIES = keep_mb, keep_n

# ---- three processes appending to and trimming one over-full log at once, as the suite's tests do
shared = scratch / "shared.jsonl"
code = r"""
import json, sys
sys.path[:0] = ["."]
import config
config.LOG_MAX_MB, config.LOG_KEEP_ENTRIES, config.LOG_PATH = 0.001, 5, sys.argv[1]
from llm import gateway
errors = []
for i in range(300):
    try:
        gateway._log("call_log_566", 0, 0.0, [{"role": "user", "content": "x" * 200}], "{}", None)
        gateway.trim_log()
    except Exception as e:
        errors.append(f"{type(e).__name__}: {e}")
print(json.dumps({"errors": len(errors), "first": errors[:2]}))
"""
procs = [subprocess.Popen([sys.executable, "-c", code, str(shared)], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
         for _ in range(3)]
outs = [p.communicate(timeout=300) for p in procs]
got = []
for out, err in outs:
    try:
        got.append(json.loads(out.strip().splitlines()[-1]))
    except (ValueError, IndexError):
        got.append({"errors": -1, "first": [err[-300:]]})
check("three processes appending to and trimming one over-full call log at once raise nothing", all(g["errors"] == 0 for g in got), got)
check("...and leave no temp file behind", not [p.name for p in scratch.iterdir() if p.name.endswith(".tmp")],
      [p.name for p in scratch.iterdir() if p.name.endswith(".tmp")])

# ---- shard 2 of the fight fixtures with every write of its call log refused (the shard's first play in this process, as in 494c)
import fight_fixtures as ff
refused = scratch / "refused"
refused.mkdir()
config.LOG_PATH = str(refused)                               # a folder: the system refuses every append (IsADirectory, or PermissionError)
writes = gateway._writes
records, _ = ff.play(2)
moved = [l for l in ff.compare(2, records) if not l.startswith("warning")]
check(f"shard 2 plays all {len(records)} of its fights to their recorded numbers while every write of its call log is refused",
      not moved, moved[:3])
check("...with no turn rolled back by a fault", not ff.FAULTS, ff.fault_lines())
check("...and the call log was refused all along (none of its writes stood)", gateway._writes == writes, gateway._writes - writes)

# ---- generate() answers when neither the call log nor the audit log can be written
from pydantic import BaseModel
import simlib
from llm import audit


class Reply(BaseModel):
    speech: str


class Answer:
    def __init__(self, text):
        self.message = type("M", (), {"content": text})()
        self.done_reason = "stop"


held = simlib.stand_in(chat=lambda **k: Answer('{"speech": "a cart rolls by"}'), embed=None, name="call_log_566")
audit_was = (config.AUDIT_LOG, audit._path, audit._full)
config.AUDIT_LOG, audit._path, audit._full = True, refused, False      # the audit's file a folder too: its append is refused
try:
    r = gateway.generate("narrate", "You are the narrator.", "plain user text", Reply, retries=0)
    err = None
except Exception as e:
    r, err = None, e
finally:
    config.AUDIT_LOG, audit._path, audit._full = audit_was
    held()
check("generate() gives its answer when neither the call log nor the audit log can be written", r is not None
      and r.speech == "a cart rolls by", repr(err))

# ---- a turn rolled back by a fault is named by the fixtures
first = next(c["id"] for c in ff.cases() if ff.shard_of(c) == 2)
config.LOG_PATH = str(scratch / "calls.jsonl")
real_log = gateway._log
fired = []

def failing_log(task, *a, **k):                              # the old failure put back for one call: an OSError out of an answered call
    if task == "combat_interpret" and not fired:
        fired.append(task)
        raise FileNotFoundError(2, "No such file or directory", "logs/llm_calls.tmp")
    return real_log(task, *a, **k)

gateway._log = failing_log
try:
    ff.play(2, only={first})
finally:
    gateway._log = real_log
check("a turn rolled back by a fault is named by the fixtures: its case and the error", fired and ff.FAULTS
      and ff.FAULTS[0]["case"] == first and "FileNotFoundError" in ff.FAULTS[0]["error"], (fired, ff.fault_lines()))

# ---- (f782) the gateway's own bookkeeping never costs an answer or leaves it half mended
import ast
import re
from engine import crashlog, hygiene, names
from llm.errors import Cancelled

config.LOG_PATH = str(scratch / "calls.jsonl")
calls_file = Path(config.LOG_PATH)
audit_file = scratch / "audit.md"
audit_kept = (config.AUDIT_LOG, audit._path, audit._full, audit._count, audit._turn_written, dict(audit._system_seen),
              dict(audit._first_attempt))


def fresh_audit(at: Path | None = None) -> None:
    """The audit log on, written to a file of this test's own (or `at`), its entries numbered from the start."""
    if at is None:
        audit_file.write_text("# f782\n", encoding="utf-8")
    config.AUDIT_LOG, audit._path, audit._full, audit._count = True, at or audit_file, False, 0
    audit._turn_written = (-2, "")
    audit._system_seen.clear()
    audit._first_attempt.clear()


def mark() -> list:
    return list(crashlog.SESSION)


def new_wheres(since: list) -> list[str]:
    old = {id(e) for e in since}
    return [e["where"] for e in crashlog.SESSION if id(e) not in old]


def answering(*texts):
    """A stand-in model answering these texts in turn (the last one again after them), and the list of calls it was asked."""
    asked = []

    def chat(**k):
        asked.append(1)
        return Answer(texts[min(len(asked), len(texts)) - 1])
    return chat, asked


def ask(chat, user="plain user text", schema=Reply, task="narrate", retries=2, system="You are the narrator."):
    """generate() once with the stand-in in: (the answer, what it raised)."""
    held_782 = simlib.stand_in(chat=chat, embed=None, name="call_log_782")
    try:
        return gateway.generate(task, system, user, schema, retries=retries), None
    except BaseException as e:
        return None, e
    finally:
        held_782()


def rows() -> list[str]:
    return calls_file.read_text(encoding="utf-8").splitlines() if calls_file.exists() else []


BS = chr(92)
LONE = '{"speech": "a ' + BS + 'ud83d and no more"}'          # half a surrogate pair, as the escape the grammar lets the model write
crashlog.CARRIED.clear()
fresh_audit()
n0 = mark()
chat, asked = answering(LONE, '{"speech": "a cart rolls by"}')
r, err = ask(chat)
text = audit_file.read_text(encoding="utf-8")
check("(f782) an answer holding half a surrogate pair is sent back and asked again, never a fault out of generate(): its rejected try "
      "is written to the audit, the half pair as its escape, and nothing to crash.log",
      err is None and r is not None and r.speech == "a cart rolls by" and len(asked) == 2 and "## #1" in text and "## #2" in text
      and BS + "ud83d" in text and new_wheres(n0) == [], (repr(err), len(asked), new_wheres(n0)))

fresh_audit()
n0, before = mark(), len(rows())
chat, asked = answering('{"speech": "a cart rolls by"}')
r, err = ask(chat, user="I say \ud83d to the guard")       # a real half pair in what was sent: a line typed in the page can hold one
text = audit_file.read_text(encoding="utf-8")
check("...and a half pair in what was sent (a line typed in the page) is written to the call log and the audit as its escape, the "
      "answer taken", err is None and r is not None and len(rows()) == before + 1 and "ud83d" in rows()[-1] and BS + "ud83d" in text
      and new_wheres(n0) == [], (repr(err), len(rows()) - before, new_wheres(n0)))

refused_audit = scratch / "audit_refused"
refused_audit.mkdir(exist_ok=True)
fresh_audit(at=refused_audit)                                       # a folder: the system refuses its append
n0 = mark()
chat, asked = answering('{"speech": "a cart rolls by"}')
got = [ask(chat)]
audit._path = audit_file
audit_file.write_text("# f782\n", encoding="utf-8")
got += [ask(chat), ask(chat)]
text = audit_file.read_text(encoding="utf-8")
heads = set(re.findall(r"^## #(\d+) ", text, re.M))
refs = re.findall(r"(?:unchanged since|the same as) #(\d+)", text)
check("...an audit append the system refuses costs no answer and leaves no number behind: every 'unchanged since #N' after it points at "
      "an entry that is there, and nothing is written to crash.log", all(e is None and a is not None for a, e in got) and refs
      and set(refs) <= heads and "1" in heads and new_wheres(n0) == [], (heads, refs, new_wheres(n0), [repr(e) for _, e in got]))

real_compact, real_h = gateway._compact, audit._h


def broken(*a, **k):
    raise RuntimeError("a fault in the bookkeeping itself")


fresh_audit()
crashlog.CARRIED.clear()
n0 = mark()
gateway._compact, audit._h = broken, broken
try:
    chat, asked = answering('{"speech": "a cart rolls by"}')
    got = [ask(chat), ask(chat)]
finally:
    gateway._compact, audit._h = real_compact, real_h
wheres = new_wheres(n0)
check("...a fault of any other kind writing the call log's row or the audit's entry costs no answer either, and each is written down "
      "once (not once a call)", all(e is None and a is not None and a.speech == "a cart rolls by" for a, e in got) and len(wheres) == 2
      and any("call log" in w for w in wheres) and any("audit" in w for w in wheres), (wheres, [repr(e) for _, e in got]))

real_tally, real_checked = gateway.TALLY, gateway.CHECKED


class Refusing(dict):
    """A tally that cannot be added to."""
    def setdefault(self, *a, **k):
        raise RuntimeError("a fault in the tally")

    def __setitem__(self, *a, **k):
        raise RuntimeError("a fault in the count")


crashlog.CARRIED.clear()
n0 = mark()
gateway.TALLY, gateway.CHECKED = Refusing(), Refusing(real_checked)
try:
    chat, asked = answering('{"speech": "a cart rolls by"}')
    r, err = ask(chat)
finally:
    gateway.TALLY, gateway.CHECKED = real_tally, real_checked
wheres = new_wheres(n0)
check("...and so does a fault in the gateway's tallies (each task's calls, the passages checked): the answer is taken and each is "
      "written down", err is None and r is not None and len(wheres) == 2 and any("tally" in w for w in wheres)
      and any("checked" in w for w in wheres), (repr(err), wheres))

config.AUDIT_LOG = False


class TwoLines(BaseModel):
    text: str = ""
    detail: str = ""


DASH = "—"
DASHED = json.dumps({"text": f"The gate {DASH} old oak {DASH} stands shut.", "detail": f"A latch {DASH} rusted {DASH} holds it."})
real_undash = hygiene.undash


def failing_second(real, fault):
    """The function `real`, raising `fault` the second time it is called (on the answer's second prose field)."""
    n = []

    def f(*a, **k):
        n.append(1)
        if len(n) == 2:
            raise fault
        return real(*a, **k)
    return f


chat, asked = answering(DASHED)
plain, err = ask(chat, schema=TwoLines, retries=0)
check("(f782) the dash mend of a taken answer, as before: no dashes in what the player reads", err is None and plain is not None
      and DASH not in plain.text + plain.detail, (repr(err), plain))
crashlog.CARRIED.clear()
n0 = mark()
hygiene.undash = failing_second(real_undash, RuntimeError("a fault inside the dash mend"))
try:
    half, err = ask(chat, schema=TwoLines, retries=0)
finally:
    hygiene.undash = real_undash
check("...a dash mend that fails half way leaves the answer whole as the model wrote it, never half mended, and is written down",
      err is None and half is not None and half.text == f"The gate {DASH} old oak {DASH} stands shut."
      and half.detail == f"A latch {DASH} rusted {DASH} holds it." and len(new_wheres(n0)) == 1 and "dash" in new_wheres(n0)[0],
      (repr(err), half, new_wheres(n0)))

TOLD = json.dumps({"text": "Zorra nods to you.", "detail": "Zorra waits by the gate."})
NAMING = dict(system="You tell what happens. Zurra is a hired guard.", user="Here: the gate. With the player walks Zurra, a guard.")
real_mend_text = names.mend_text
chat, asked = answering(TOLD)
r0, b0 = names.REPAIRS["name"] + names.REPAIRS["speaker"], names.BY_TASK["narrate"]
mended, err = ask(chat, schema=TwoLines, retries=0, **NAMING)
check("(f782) the name mend of a taken answer, as before: both names put right, and the count A1 reads moved with the names mended",
      err is None and mended is not None and mended.text == "Zurra nods to you." and mended.detail == "Zurra waits by the gate."
      and names.BY_TASK["narrate"] - b0 == names.REPAIRS["name"] + names.REPAIRS["speaker"] - r0 == 2, (repr(err), mended))
crashlog.CARRIED.clear()
n0 = mark()
r0, b0 = names.REPAIRS["name"] + names.REPAIRS["speaker"], names.BY_TASK["narrate"]
names.mend_text = failing_second(real_mend_text, RuntimeError("a fault inside the name mend"))
try:
    half, err = ask(chat, schema=TwoLines, retries=0, **NAMING)
finally:
    names.mend_text = real_mend_text
check("...a name mend that fails half way leaves both names as the model wrote them, is written down, and the count A1 reads moves "
      "with the names the mend found (names.REPAIRS), never apart from it", err is None and half is not None
      and half.text == "Zorra nods to you." and half.detail == "Zorra waits by the gate." and len(new_wheres(n0)) == 1
      and "name" in new_wheres(n0)[0] and names.BY_TASK["narrate"] - b0 == names.REPAIRS["name"] + names.REPAIRS["speaker"] - r0,
      (repr(err), half, new_wheres(n0), names.BY_TASK["narrate"] - b0, names.REPAIRS["name"] + names.REPAIRS["speaker"] - r0))

chat, asked = answering(DASHED)
n0 = mark()
calls0 = gateway.TALLY.get("narrate", {}).get("calls", 0)
hygiene.undash = failing_second(real_undash, Cancelled("the campaign that asked is closing"))
try:
    gone, err = ask(chat, schema=TwoLines, retries=0)
finally:
    hygiene.undash = real_undash
calls1 = gateway.TALLY.get("narrate", {}).get("calls", 0)
check("...and a cancel inside a mend goes on up: the answer is not taken, it is no fault, and the call is not tallied as a success "
      "(the tally is taken after the mends)", gone is None and isinstance(err, Cancelled) and new_wheres(n0) == [] and calls1 == calls0,
      (gone, repr(err), new_wheres(n0), calls1 - calls0))
chat, asked = answering(DASHED)
calls0 = gateway.TALLY.get("narrate", {}).get("calls", 0)
taken, err = ask(chat, schema=TwoLines, retries=0)
check("...while a call whose answer is taken is tallied once, as before", taken is not None
      and gateway.TALLY.get("narrate", {}).get("calls", 0) == calls0 + 1, gateway.TALLY.get("narrate"))


class Said(BaseModel):
    speech: str = ""


class Many(BaseModel):
    """Prose in a list, and models in a list: what a mend changes in place, and a copy made only one level deep would share."""
    paragraphs: list[str] = []
    said: list[Said] = []


DASH_TWO = [f"The gate {DASH} old oak {DASH} stands shut.", f"A latch {DASH} rusted {DASH} holds it."]
NAME_TWO = ["Zorra nods to you.", "Zorra waits by the gate."]
HALF_WAY = {                                           # label: (the answer, the mend made to fail on its second item, the call's words)
    "the dash mend, prose in a list": (json.dumps({"paragraphs": DASH_TWO}), "dashes", {}),
    "the dash mend, speech in a list of models": (json.dumps({"said": [{"speech": s} for s in DASH_TWO]}), "dashes", {}),
    "the name mend, prose in a list": (json.dumps({"paragraphs": NAME_TWO}), "names", NAMING),
    "the name mend, speech in a list of models": (json.dumps({"said": [{"speech": s} for s in NAME_TWO]}), "names", NAMING),
}


def half_way(raw: str, which: str, words: dict):
    """The answer generate() gives when the mend named fails on its second item, with what was raised."""
    chat, _ = answering(raw)
    if which == "dashes":
        hygiene.undash = failing_second(real_undash, RuntimeError("a fault inside the dash mend"))
    else:
        names.mend_text = failing_second(real_mend_text, RuntimeError("a fault inside the name mend"))
    try:
        return ask(chat, schema=Many, retries=0, **words)
    finally:
        hygiene.undash, names.mend_text = real_undash, real_mend_text


def as_written(answer: Many | None, raw: str) -> bool:
    return answer is not None and answer.model_dump() == Many.model_validate_json(raw).model_dump()


crashlog.CARRIED.clear()
deep = {label: half_way(*case) for label, case in HALF_WAY.items()}
check("(f782) a mend that fails on the second item of a list, prose or models, leaves the answer as the model wrote it: the list and the "
      "nested models are untouched, never half mended (the mend is made on a deep copy)",
      all(err is None and as_written(answer, HALF_WAY[label][0]) for label, (answer, err) in deep.items()),
      {label: (answer, repr(err)) for label, (answer, err) in deep.items()})
real_model_copy = BaseModel.model_copy


def shallow(self, *, update=None, deep=False):
    return real_model_copy(self, update=update, deep=False)


BaseModel.model_copy = shallow                         # a mutant: the copy made one level deep
try:
    mutant = {label: half_way(*case) for label, case in HALF_WAY.items()}
finally:
    BaseModel.model_copy = real_model_copy
check("...and the check is the one that holds it: with the copy made only one level deep, each of the four comes back half mended",
      all(answer is not None and not as_written(answer, HALF_WAY[label][0]) for label, (answer, err) in mutant.items()),
      {label: answer for label, (answer, err) in mutant.items()})


def dotted(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = dotted(node.value)
        return None if head is None else f"{head}.{node.attr}"
    return None


MENDS = {"hygiene": {"undash_answer", "undash", "unwrap"}, "names": {"mend_answer", "mend_text"}}   # what mends an answer's words


def mends_outside(text: str) -> list[int]:
    """Each line of the gateway that mends an answer's words outside the one way: a call of engine.hygiene's undash_answer, undash or
    unwrap, or engine.names' mend_answer or mend_text (by the module's name, any alias, a dotted path, or a name imported from it)
    anywhere but in the mend handed to _mended(); and a _mended() whose mend is not a lambda of one answer that mends that answer, its
    own parameter, and nothing else."""
    tree = ast.parse(text)
    alias, fns = {}, {}                                 # local name -> hygiene or names; local name -> (module, function)
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            for a in n.names:
                if a.name.rsplit(".", 1)[-1] in MENDS and a.asname:
                    alias[a.asname] = a.name.rsplit(".", 1)[-1]
        elif isinstance(n, ast.ImportFrom) and n.module:
            if n.module.rsplit(".", 1)[-1] in MENDS:
                fns.update({a.asname or a.name: (n.module.rsplit(".", 1)[-1], a.name) for a in n.names})
            else:
                alias.update({a.asname or a.name: a.name for a in n.names if a.name in MENDS})

    def mend_of(call) -> tuple[str, str] | None:
        d = dotted(call.func) or ""
        if d in fns:
            got = fns[d]
        else:
            head, _, fn = d.rpartition(".")
            got = (alias.get(head, head.rsplit(".", 1)[-1]), fn)
        return got if got[1] in MENDS.get(got[0], ()) else None
    out, inside = [], set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and dotted(n.func) == "_mended":
            mend = n.args[3] if len(n.args) > 3 else next((k.value for k in n.keywords if k.arg == "mend"), None)
            if not (isinstance(mend, ast.Lambda) and len(mend.args.args) == 1):
                out.append(n.lineno)
                continue
            own = mend.args.args[0].arg
            for x in ast.walk(mend.body):
                if isinstance(x, ast.Call) and mend_of(x):
                    inside.add(id(x))
                    if not any(isinstance(a, ast.Name) and a.id == own for a in x.args + [k.value for k in x.keywords]):
                        out.append(x.lineno)
    out += [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and mend_of(n) and id(n) not in inside]
    return sorted(out)


def unguarded(text: str, kept: tuple[str, ...]) -> list[str]:
    """The functions named in `kept` whose work is not all inside one `with crashlog.carried(...)` (a docstring, `global` and imports
    may stand before it), and those named and not there at all."""
    out, seen = [], set()
    for fn in ast.parse(text).body:
        if isinstance(fn, ast.FunctionDef) and fn.name in kept:
            seen.add(fn.name)
            body = [s for s in fn.body if not (isinstance(s, (ast.Global, ast.Import, ast.ImportFrom))
                                              or (isinstance(s, ast.Expr) and isinstance(s.value, ast.Constant)))]
            if not (len(body) == 1 and isinstance(body[0], ast.With)
                    and any(isinstance(i.context_expr, ast.Call) and (dotted(i.context_expr.func) or "").endswith("crashlog.carried")
                            for i in body[0].items)):
                out.append(fn.name)
    return out + [f"{name} (not found)" for name in kept if name not in seen]


KEPT = {"llm/gateway.py": ("_log", "_tally", "_count"), "llm/audit.py": ("record",)}
planted = {                                            # source: (the lines mends_outside names, what unguarded names for _tally)
    "def _generate(task, result):\n    hygiene.undash_answer(task, result)\n    return result\n": ([2], ["_tally (not found)"]),
    "def _generate(task, result, request):\n    names.mend_answer(result, request)\n": ([2], ["_tally (not found)"]),
    "from engine.hygiene import undash_answer\ndef _generate(task, result):\n    undash_answer(task, result)\n": ([3], ["_tally (not found)"]),
    "from engine.names import mend_answer as fix\ndef _generate(result, request):\n    fix(result, request)\n": ([3], ["_tally (not found)"]),
    "import engine.hygiene\ndef _generate(task, result):\n    engine.hygiene.undash_answer(task, result)\n": ([3], ["_tally (not found)"]),
    "from engine import hygiene as h\ndef _generate(result):\n    result.text = h.undash(h.unwrap(result.text))\n": ([3, 3], ["_tally (not found)"]),
    "from engine import names\ndef _generate(result, known):\n"
    "    result.text = names.mend_text(result.text, known, set())\n": ([3], ["_tally (not found)"]),
    "def _generate(task, result):\n"
    "    return _mended(task, result, 'dashes', lambda r: hygiene.undash_answer(task, result))\n": ([2], ["_tally (not found)"]),
    "def _generate(task, result, request):\n    return _mended(task, result, 'names', names.mend_answer)\n": ([2], ["_tally (not found)"]),
    "def _generate(task, result):\n"
    "    return _mended(task, result, 'dashes', lambda r: hygiene.undash_answer(task, r))\n": ([], ["_tally (not found)"]),
    "def _generate(task, result, request):\n"
    "    return _mended(task, result, 'names', mend=lambda a: names.mend_answer(a, request))\n": ([], ["_tally (not found)"]),
    "TALLY = {}\ndef _tally(task):\n    TALLY[task] = TALLY.get(task, 0) + 1\n": ([], ["_tally"]),
    "def _tally_calls(task):\n    pass\n": ([], ["_tally (not found)"]),
    "def _tally(task):\n    '''Counted.'''\n    from engine import crashlog\n    with crashlog.carried('the tally'):\n        pass\n": ([], []),
}
wrong = {src: (mends_outside(src), unguarded(src, ("_tally",))) for src, want in planted.items()
         if (mends_outside(src), unguarded(src, ("_tally",))) != want}
check("(f782) the fence catches each way round the one mend, planted: a mend of the answer called by the module, a name imported from it "
      "(aliased too), a dotted path, a field mended by hand with undash, unwrap or mend_text, a lambda handed to _mended() that mends the "
      "answer and not its own copy, a function handed in bare; and a piece of bookkeeping written outside carried, or renamed so it is "
      "no longer there; and passes the mend made the one way, by position or by name", not wrong, wrong)
outside = {f: (mends_outside(Path(f).read_text(encoding="utf-8")), unguarded(Path(f).read_text(encoding="utf-8"), kept))
           for f, kept in KEPT.items()}
check("...and in the gateway every mend of a taken answer goes through _mended(), and the call log's row, the tallies and the audit's "
      "entry are each written under crashlog.carried", all(not m and not u for m, u in outside.values()), outside)

(config.AUDIT_LOG, audit._path, audit._full, audit._count, audit._turn_written) = audit_kept[:5]
audit._system_seen.clear()
audit._system_seen.update(audit_kept[5])
audit._first_attempt.clear()
audit._first_attempt.update(audit_kept[6])

shutil.rmtree(scratch, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
