"""(f781) The crash log never raises and loses no entry, and a line typed in the page reaches the game whole: a follow-up completing f781,
found by the review across phase 6.

f781 and f783 hold that crashlog.record() never raises, but it wrote strict UTF-8 and caught only OSError: an entry holding half a
surrogate pair (a line typed in the page passed as its context, an error's words) raised UnicodeEncodeError, out of the turn after its
rollback, last_failure and op.crashed never set; and an exception or a context value whose __str__ raised raised out of it too. A line
typed in the page holding half a pair (an emoji the page split, which its JSON sends as the escape) never reached a turn's fault at
all: the turn's dice are seeded from the line, the seed refused it, and the line ended the game. Two threads writing a fault at once
each read crash.log, added theirs and wrote it back, so entries were lost (f782 put the gateway's bookkeeping, which runs on background
lanes, under carried). And f782's five wheres kept the task in the context, so a tally failing for four tasks wrote one entry and
counted four, the count naming no task. Held here:
- record() and note() write half a pair as its escape, wherever it stands (the where, the error, the context, the traceback), and
  never raise: an exception whose __str__ raises is written as its type, a context value so as its type;
- a line from outside is taken in whole (core.typed.whole): half a pair, high or low, is dropped, never shown, and a pair sent in two
  halves is its one character. Every channel's ask in the game's own code passes its line through it (the terminal's, and the page's,
  which answers its channel), so a channel added later (a player at another machine) does too, or fails here; and the page's choice
  sent as JSON inside its line (creation's "Anything else") is made whole where the engine keeps it (engine/look.py clean).
- end to end through the page's own server: a line holding half a pair, in a turn the game breaks on, is played, its fault rolled back
  and written down with the line whole, the player reads the narrator's line, nothing broken reaches the page, and the game goes on;
  and creation's first page, posted with the escape in "Anything else", keeps the words whole in the look the world sees;
- crash.log loses no entry to writers at once: four threads writing a hundred faults each leave four hundred entries;
- each of the gateway's and the audit's carried wheres names its task (or what it counted), so each task failing is an entry of its
  own and the settled count names it.
Run: python tools/sim/crash_log_781b_test.py"""
import ast
import builtins
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 9))
import config

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

SCRATCH = Path(tempfile.mkdtemp(prefix="crash_log_781b_")).resolve()
config.CRASH_LOG_PATH = str(SCRATCH / "crash.log")              # what this test writes down stays here
config.LOG_PATH = str(SCRATCH / "llm_calls.jsonl")
from engine import crashlog

HALF, LOW = chr(0xD83D), chr(0xDE00)                             # the two halves of one emoji
SMILE = chr(0x1F600)
BS = chr(92)
ESCAPE = BS + "ud83d"                                            # how JSON writes HALF


def broken_text(s: str) -> bool:
    """Whether a text holds half a surrogate pair, or the replacement character a broken one is shown as."""
    return any(0xD800 <= ord(c) <= 0xDFFF or ord(c) == 0xFFFD for c in s)


def entries() -> list[str]:
    p = crashlog.path()
    return [e for e in p.read_text(encoding="utf-8").split(crashlog.SEP) if e.strip()] if p.exists() else []


def mark() -> list[dict]:
    return list(crashlog.SESSION)


def new(since: list[dict]) -> list[dict]:
    old = {id(e) for e in since}
    return [e for e in crashlog.SESSION if id(e) not in old]


# ---- (a) record() and note() never raise, whatever they are handed
try:
    raise RuntimeError(f"the road {HALF} is not on the map")
except RuntimeError as caught:
    fault = caught
n0, f0 = mark(), len(entries())
try:
    crashlog.record(fault, f"a where {HALF}", text=f"I say hi {HALF}")
    raised = None
except BaseException as e:
    raised = e
written = entries()[-1] if len(entries()) > f0 else ""
check("(f781) record() never raises on half a surrogate pair, in the where, the error, the context and the traceback: the entry is "
      "kept and written whole, the half pair as its escape", raised is None and len(new(n0)) == 1 and len(entries()) == f0 + 1
      and f"I say hi {ESCAPE}" in written and f"a where {ESCAPE}" in written and f"the road {ESCAPE}" in written
      and "Traceback" in written, (repr(raised), len(new(n0)), len(entries()) - f0, written[:300]))
f0 = len(entries())
try:
    crashlog.note(f"a note's where {HALF}", f"and its words {HALF}")
    raised = None
except BaseException as e:
    raised = e
check("...and so does note()", raised is None and len(entries()) == f0 + 1 and f"and its words {ESCAPE}" in entries()[-1],
      (repr(raised), len(entries()) - f0))


class Unsayable(Exception):
    """An exception whose words cannot be read."""
    def __str__(self):
        raise RuntimeError("these words cannot be said")


class Mute:
    """A context value whose words cannot be read."""
    def __str__(self):
        raise ValueError("nor these")


try:
    raise Unsayable()
except Unsayable as caught:
    unsayable = caught
n0, f0 = mark(), len(entries())
try:
    got = crashlog.record(unsayable, "f781b probe: unsayable", thing=Mute(), text="look")
    raised = None
except BaseException as e:
    got, raised = None, e
written = entries()[-1] if len(entries()) > f0 else ""
check("(f781) record() never raises on an exception, or a context value, whose __str__ raises: the error is its type, the value its "
      "type, the rest written as ever", raised is None and got is not None and got["error"] == "Unsayable" and len(entries()) == f0 + 1
      and "f781b probe: unsayable: Unsayable" in written and "  thing: Mute" in written and "  text: look" in written
      and "Traceback" in written, (repr(raised), got, written[:300]))

# ---- (a) a line from outside is taken in whole, at every channel's ask
from core.typed import whole
from ui import console
cases = {f"I say hi {HALF}": "I say hi ", f"a{HALF}b": "ab", f"{LOW}x": "x", chr(0xDC80) + chr(0xDC81): "", HALF: "",
         HALF + LOW: SMILE, f"ok {SMILE} fine": f"ok {SMILE} fine", "plain": "plain"}
made = {ascii(k): ascii(whole(k)) for k, v in cases.items() if whole(k) != v}
check("(f781) core.typed.whole takes a line in whole: half a pair, high or low, is dropped (never shown as broken text), a pair sent in "
      "two halves is its one character, a whole line is as it was", not made, made)
real_input = builtins.input
said = iter([f"  look at the {HALF}  ", HALF])
builtins.input = lambda prompt="": next(said)
try:
    typed = [console.Stdout().ask(main=True), console.Stdout().ask(main=True)]
finally:
    builtins.input = real_input
check("...the terminal's ask gives the game the line whole, and a line that was only half a pair is no line (the loop skips it)",
      typed == ["look at the", ""], [ascii(t) for t in typed])


def dotted(node) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        head = dotted(node.value)
        return None if head is None else f"{head}.{node.attr}"
    return None


def unwhole(text: str) -> tuple[list[str], int]:
    """Each method named ask of a class (a channel's answer to console.ask, or what answers it for the page's channel) that does not pass
    its line through whole(); and how many such methods were read."""
    out, seen = [], 0
    for cls in ast.walk(ast.parse(text)):
        if isinstance(cls, ast.ClassDef):
            for fn in cls.body:
                if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name == "ask":
                    seen += 1
                    if not any(isinstance(c, ast.Call) and (dotted(c.func) or "").rpartition(".")[2] == "whole" for c in ast.walk(fn)):
                        out.append(f"{cls.name}.ask")
    return out, seen


PLANTED = {
    "class Net(Channel):\n    def ask(self, main=False, menu=False):\n        return self.sock.recv().decode().strip()\n": ["Net.ask"],
    "class Window:\n    def ask(self, main=False):\n        text = self.inbox.get()\n        return text.strip()\n": ["Window.ask"],
    "class Outer:\n    class Seat(Channel):\n        def ask(self):\n            return input('> ')\n": ["Seat.ask"],
    "from core.typed import whole\nclass Window:\n    def ask(self, main=False):\n        return whole(self.inbox.get()).strip()\n": [],
    "from core import typed\nclass Net(Channel):\n    def ask(self):\n        return typed.whole(self.sock.recv()).strip()\n": [],
    "def ask(ws, actor_id, words):\n    return words\n": [],
}
wrong = {src: unwhole(src)[0] for src, want in PLANTED.items() if unwhole(src)[0] != want}
check("(f781) the rule catches a channel's ask that hands the game its line as it came (a socket's, a window's inbox, a class inside "
      "another), and passes one through whole() by either import, and an ask that is no channel's method", not wrong, wrong)
NOT_GAME = {"tools", "data", "docs", ".claude"}
HARNESS = {"simlib", "simbot", "simreport", "smoke_test", "bestiary_check", "world_check"}
game = [f for f in subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True,
                                  text=True, encoding="utf-8", check=True).stdout.split()
        if f.split("/")[0] not in NOT_GAME and Path(f).stem not in HARNESS and Path(f).is_file()]
read = {f: unwhole(Path(f).read_text(encoding="utf-8")) for f in game}
loose = [f"{f}: {a}" for f, (out, _) in read.items() for a in out]
check("...and every channel's ask in the game's own code takes its line in whole (the terminal's and the page's, read here), so one "
      "added later for another player's seat does too", not loose and sum(n for _, n in read.values()) >= 2
      and read.get("ui/console.py", ([], 0))[1] == 1 and read.get("ui/gui/bridge.py", ([], 0))[1] == 1, (loose, len(game)))

from engine import failures, look
dwarf = {"people": "dwarf", "pronoun": "she", "look": {"build": "stocky"}, "extra": f"a burn scar {HALF} along the jaw"}
kept = look.clean(json.loads(json.dumps(dwarf)))
check("(f781) the look keeps creation's 'Anything else' whole: the page's JSON escape, read back, is half a pair, dropped where the "
      "engine keeps the choice", kept["extra"] == "a burn scar along the jaw" and not broken_text(look.describe(kept)),
      (ascii(kept["extra"]), ascii(look.describe(kept))))

# ---- (a) end to end through the page's own server: a line, and creation's first page
from scenes.goddess import ThresholdScene
from ui.gui import server
from ui.gui.bridge import Bridge

g = simlib.campaign("crash_log_781b", seed=9, location="parth")
ws = g.scene


def broken_line(text):
    raise RuntimeError("the road road_3db1089b is not on the map")     # the game's own fault, inside the line's operation


ws.take_line = broken_line
b = Bridge()
b.install()
b.pinned, b.dirty = None, False
srv = server.make_server(b)
server.serve(srv)
base = srv.url.split("/?")[0]
ran: dict = {}


def wait_for(pred, t=60.0) -> bool:
    end = time.time() + t
    while time.time() < end:
        if pred():
            return True
        time.sleep(0.02)
    return False


def post(text: str) -> int:
    """The page's way in: its JSON, which writes half a pair as the escape."""
    r = urllib.request.Request(base + "/input", data=json.dumps({"text": text}).encode("ascii"), method="POST")
    r.add_header("X-Token", srv.token)
    try:
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code


def runs(fn, into: dict) -> threading.Thread:
    def go():
        try:
            into["got"] = fn()
            into["ended"] = True
        except BaseException as e:
            into["raised"] = e
    t = threading.Thread(target=go, daemon=True)
    t.start()
    return t


def since(last: int) -> list[dict]:
    return [e for i, e in b.log if i > last]


th = None
try:
    th = runs(ws.run, ran)
    at_prompt = lambda: (b.waiting and b.at_main) or not th.is_alive()
    check("(the game reached its first prompt in the page)", wait_for(at_prompt) and th.is_alive(), ran)
    last = b.next_id - 1
    n0 = mark()
    status = post(f"I say hi {HALF}")
    wait_for(lambda: b.next_id - 1 > last)
    wait_for(at_prompt)
    told = since(last)
    shown = "".join(e.get("text", "") for e in told if e.get("k") == "text")
    echo = [e.get("text") for e in told if e.get("k") == "echo"]
    turn_fault = next((e for e in new(n0) if e.get("where") == "turn"), None)
    check("(f781) a line typed in the page holding half a pair, in a turn the game breaks on, is played: the turn is rolled back and "
          "the game goes on to its next prompt", status == 200 and th.is_alive() and "raised" not in ran and b.waiting and b.at_main
          and ws.last_crash and ws.last_failure.startswith("RuntimeError"), (status, ran, b.waiting, ws.last_crash, ws.last_failure))
    check("...the line reached the game whole, the half dropped, and the page echoes it as the game read it",
          echo == ["I say hi"] and turn_fault is not None and turn_fault.get("text") == "I say hi", ([ascii(x) for x in echo], turn_fault))
    log_text = crashlog.path().read_text(encoding="utf-8") if crashlog.path().exists() else ""
    check("...the fault is written down with its traceback, the line and the place",
          turn_fault is not None and "RuntimeError" in turn_fault["error"] and "the road road_3db1089b is not on the map" in log_text
          and "text: I say hi" in log_text and "place: parth" in log_text and "Traceback" in log_text, (turn_fault, log_text[-400:]))
    check("...and the player reads the narrator's line, never the machinery, and nothing broken reaches the page",
          any(line in shown for line in failures.F["turn_not_taken"]) and not failures.MACHINERY.search(shown)
          and not broken_text(shown + "".join(echo)), ascii(shown[-300:]))
    post("quit")
    th.join(timeout=30)
    check("...and the game is left as a player leaves it", ran.get("ended") is True and not th.is_alive(), ran)

    made_ = {}
    scene = ThresholdScene()
    th = runs(scene.who, made_)
    check("(creation's first page is up in the page)", wait_for(lambda: b.waiting or not th.is_alive()) and th.is_alive(), made_)
    last = b.next_id - 1
    inner = json.dumps(dwarf)                                    # the page: "create:who " + JSON.stringify(its choices)
    status = post("create:who " + inner)
    th.join(timeout=30)
    shown = "".join(e.get("text", "") for e in since(last) if e.get("k") == "text")
    choice = scene.who_choice or {}
    check("(f781) creation's first page posted with half a pair in 'Anything else', as the page's own escape inside its line, keeps the "
          "words whole: in the choice kept, the sentence the world sees, the goddess's prompt and the page",
          ESCAPE in inner and status == 200 and made_.get("got") is True and choice.get("extra") == "a burn scar along the jaw"
          and "a burn scar along the jaw" in scene.seen() and not broken_text(scene.seen() + scene.system + shown),
          (status, made_, ascii(choice.get("extra")), ascii(scene.seen())))
finally:
    b.close()
    if th is not None:
        th.join(timeout=10)
    srv.shutdown()
    b.uninstall()
    del ws.take_line
    g.session.close()

# ---- (b) crash.log loses no entry to writers at once
KEEP0 = crashlog.KEEP
crashlog.KEEP = 1000                                            # room for every entry of the probe
crashlog.CARRIED.clear()
threads_log = SCRATCH / "threads.log"
config.CRASH_LOG_PATH = str(threads_log)
gate = threading.Barrier(4)
n0 = mark()


def writer(t: int) -> None:
    gate.wait()
    for i in range(100):
        with crashlog.carried(f"f781b probe: thread {t}, fault {i}"):
            raise ValueError("one of four hundred")


pool = [threading.Thread(target=writer, args=(t,)) for t in range(4)]
for th_ in pool:
    th_.start()
for th_ in pool:
    th_.join()
kept_entries = entries()
check("(f781) crash.log loses no entry to writers at once: four threads writing a hundred faults each leave four hundred entries, each "
      "fault's own", len(new(n0)) == 400 and len(kept_entries) == 400
      and len({e.split(": ValueError")[0].split("  ", 1)[-1] for e in kept_entries}) == 400, (len(new(n0)), len(kept_entries)))
crashlog.KEEP = KEEP0
crashlog.CARRIED.clear()
config.CRASH_LOG_PATH = str(SCRATCH / "crash.log")

# ---- (c) one where names one subject: each task failing is an entry of its own, and the settled count names it
from pydantic import BaseModel
from llm import audit, gateway


class Said(BaseModel):
    speech: str = "a cart rolls by"


def broken(*a, **k):
    raise RuntimeError("a fault in the bookkeeping itself")


class Refusing(dict):
    def setdefault(self, *a, **k):
        raise RuntimeError("a fault in the tally")

    def __setitem__(self, *a, **k):
        raise RuntimeError("a fault in the count")


crashlog.CARRIED.clear()
n0 = mark()
real_tally = gateway.TALLY
gateway.TALLY = Refusing()
try:
    for task in ("narrate", "npc_says", "narrate", "situation_parts"):
        gateway._tally(task, True, 1)
finally:
    gateway.TALLY = real_tally
wheres = [e["where"] for e in new(n0)]
check("(f781) the gateway's tally failing for narrate, npc_says, narrate and situation_parts is three entries, one a task, each naming it",
      len(wheres) == 3 and all(any(t in w for w in wheres) for t in ("narrate", "npc_says", "situation_parts")), wheres)
f0 = len(entries())
crashlog.settle()
settled = entries()[-1] if len(entries()) > f0 else ""
check("...and the settled count names the task met again: narrate's tally, twice", "tally of calls: narrate (RuntimeError): 2 times"
      in settled and "npc_says (RuntimeError)" not in settled, settled)


def tally(task):
    gateway.TALLY = Refusing()
    try:
        gateway._tally(task, True, 1)
    finally:
        gateway.TALLY = real_tally


def counted(name):
    real = gateway.CHECKED
    gateway.CHECKED = Refusing(real)
    try:
        gateway._count(name, set())
    finally:
        gateway.CHECKED = real


def call_log(task):
    real = gateway._compact
    gateway._compact = broken
    try:
        gateway._log(task, 0, 0.1, [{"role": "user", "content": "u"}], "{}", None)
    finally:
        gateway._compact = real


audit_kept = (config.AUDIT_LOG, audit._path, audit._full, audit._count, audit._turn_written, dict(audit._system_seen),
              dict(audit._first_attempt))


def audited(task):
    real = audit._h
    (SCRATCH / "audit.md").write_text("# f781b\n", encoding="utf-8")
    config.AUDIT_LOG, audit._path, audit._full = True, SCRATCH / "audit.md", False
    audit._h = broken
    try:
        audit.record(task, 0, 0.1, [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], "{}", None)
    finally:
        audit._h = real


def mend(task, what="dashes"):
    gateway._mended(task, Said(), what, broken)


for label, site, subjects in (("the gateway's tally", tally, ("narrate", "npc_says")),
                              ("the gateway's count of answers checked", counted, ("told", "spoken")),
                              ("the call log's row", call_log, ("narrate", "npc_says")),
                              ("the audit's entry", audited, ("narrate", "npc_says")),
                              ("the gateway's mend of a taken answer", mend, ("narrate", "npc_says"))):
    crashlog.CARRIED.clear()
    n0 = mark()
    for s in subjects:
        site(s)
    wheres = [e["where"] for e in new(n0)]
    check(f"(f781) {label} failing for {subjects[0]} and then {subjects[1]} is two entries, each where naming its own",
          len(wheres) == 2 and subjects[0] in wheres[0] and subjects[1] in wheres[1] and subjects[1] not in wheres[0], wheres)
crashlog.CARRIED.clear()
n0 = mark()
mend("narrate", "dashes")
mend("narrate", "names")
wheres = [e["where"] for e in new(n0)]
check("...and the mend's two kinds for one task are two entries too, each naming the task and what it mended",
      len(wheres) == 2 and all("narrate" in w for w in wheres) and "dashes" in wheres[0] and "names" in wheres[1], wheres)
(config.AUDIT_LOG, audit._path, audit._full, audit._count, audit._turn_written) = audit_kept[:5]
audit._system_seen.clear()
audit._system_seen.update(audit_kept[5])
audit._first_attempt.clear()
audit._first_attempt.update(audit_kept[6])
crashlog.CARRIED.clear()

shutil.rmtree(SCRATCH, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
