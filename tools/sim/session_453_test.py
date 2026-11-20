"""(f453) One campaign's session, born when the save opens and closing everything it owns (engine/session.py). Two campaigns in one
process, the shape no test had: A plays, fills the ledger, binds the journal, the ids and the pronouns, sets a discount, opens a turn,
and leaves two threads blocked in the model (a backfill of its people, and a creation-like call handed to the session); A.close()
returns within config.CLOSE_WAIT_SECONDS, after which nothing A set remains (simlib.residue() == {}), its jobs are forgotten, both threads
are orphans and its store is closed. B opens and plays with a recorder installed; the orphans are then released and each makes its call:
B's recording has no row for them and A's database gained nothing. main.py opens every campaign through the session and builds nothing
of its own; a scene built the old way adopts a session; the Threshold hands the session the creation's background thread."""
import pathlib, shutil, sqlite3, sys, threading, time
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 53)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import config
from engine import canon, enchanting, ledger, names, recording, streams
from engine.session import CampaignSession
from llm import gateway
from npc import backfill, life
from scenes.world import WorldScene
from world.loader import authored

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

for n in ("session_453_a", "session_453_b", "session_453_rec"):
    shutil.rmtree(simlib.saves_path(n), ignore_errors=True)
GATE = threading.Event()                                   # the model, slow: both background calls wait on it until the test lets them go
real_ask = life._ask
def slow_ask(*a, **k):
    GATE.wait(15)
    return real_ask(*a, **k)
life._ask = slow_ask

# ---- A plays, and leaves things behind
a = simlib.campaign("session_453_a", cls="warrior", seed=53)
check("a campaign opened by the helper is a session, and its scene's session is the same one", isinstance(a.session, CampaignSession)
      and a.scene.session is a.session and a.scene.store is a.store and a.scene.world is a.world)
ws = a.scene
stub.plan = [{"kind": "look"}]
for line in ("I look around.", "I wait a while.", "I look again."):
    ws.turn(line)
check("three turns played: the ledger holds the last, the journal and the ids are bound, the dice are keyed",
      ledger.last() is not None and canon.journal_bound() is not None and "player" in canon.ids().values() and streams.key() != "unseeded", simlib.residue())
enchanting.set_discount(10)
names.set_cast({"Maren": "she"})
life.FIRST_BATCH = 4
ws.enter("guild_house")
ws.start_backfill()
check("A's people are being written in the background", backfill.pending(store=a.store) and len(backfill.threads(a.store)) == 1, backfill.threads(a.store))
job_thread = backfill.threads(a.store)[0]
made = {"calls": 0}
def creation_like():
    GATE.wait(15)
    from llm import backend                                # (f517) through the interface, where the recorder's layer sees the call
    from llm.sampling import Sampling
    from pydantic import create_model
    backend.chat([{"role": "user", "content": "slot 1: farmer"}], create_model("ResidentSet", x=(str, "")), Sampling(0.5), 50)
    made["calls"] += 1
own_thread = threading.Thread(target=creation_like, daemon=True)
own_thread.start()
check("a thread handed to the session is its own", a.session.own(own_thread) is own_thread and own_thread in a.session.threads() and job_thread in a.session.threads())
ledger.add("gained", say="a coin, for the test")             # a look turn records nothing: a row by hand, so the ledger is in the residue
before = simlib.residue()
check("before the close, the residue names what A set", {"caches.journal", "caches.ids", "caches.cast", "caches.discount", "registers.rows", "streams.DEFAULT"} <= set(before), before)
a_rows = a.store._db.execute("SELECT count(*) FROM event_log").fetchone()[0]
rs_calls = stub.calls.get("ResidentSet", 0)

t0 = time.monotonic()
a.close()
took = time.monotonic() - t0
check("A closes within the bound, leaving the two blocked threads behind rather than waiting the whole call", config.CLOSE_WAIT_SECONDS - 0.5 < took < config.CLOSE_WAIT_SECONDS + 2, took)
check("...and nothing A set remains: every owned binding is at its initial value", simlib.residue() == {}, simlib.residue())
check("...its background jobs are forgotten", not backfill.pending(store=a.store) and backfill.threads(a.store) == [])
check("...both threads are orphans, still running", own_thread in recording.ORPHANS and job_thread in recording.ORPHANS and own_thread.is_alive() and job_thread.is_alive())
try:
    a.store.load_player()
    closed = False
except Exception:
    closed = True
check("...and its store is closed", closed and a.session.closed)
a.close()
check("closing again does nothing", a.session.closed and simlib.residue() == {})

# ---- B opens and records; the orphans are released and are not B's
b = simlib.campaign("session_453_b", cls="warrior", seed=54)
rec = b.session.record(folder=simlib.saves_path("session_453_rec"))
check("the session installs the recorder once", b.session.record() is rec and b.session.recorder is rec and streams.STRICT)
b.scene.turn("I look around.")
n_before = rec.n_call
check("B's turn was recorded", n_before > 0, n_before)
GATE.set()
own_thread.join(10); job_thread.join(10)
check("the orphans ran to the end once let go, each making its call", not own_thread.is_alive() and not job_thread.is_alive() and made["calls"] == 1
      and stub.calls.get("ResidentSet", 0) == rs_calls + 2, (stub.calls.get("ResidentSet", 0), rs_calls))
check("...and B's recording has no row for either", rec.n_call == n_before, (rec.n_call, n_before))
check("...and B's residue is B's own, not empty while it plays", "caches.journal" in simlib.residue())
b.close()
check("B closed: the recorder is put back and the bindings are clean", simlib.residue() == {} and not streams.STRICT and (simlib.saves_path("session_453_rec") / "turns.jsonl").exists())
db = sqlite3.connect(simlib.saves_path("session_453_a/campaign.db"))
check("A's database gained nothing from its orphans", db.execute("SELECT count(*) FROM event_log").fetchone()[0] == a_rows)
db.close()
check("the dead orphans are forgotten at the next close", own_thread not in recording.ORPHANS and job_thread not in recording.ORPHANS)

# ---- a scene built the old way adopts a session; nothing is reset under it
from storage.campaign import CampaignStore, PlayerState
canon.set_ids({**canon.ids(), "someone": "x"})
st = CampaignStore.open_or_create("session_453_b")
old = WorldScene(st, authored(), a.catalog, st.load_player())
check("a scene built the old way has a session of its own, adopted, over the store and a wrapped world", old.session.adopted and old.session.store is st
      and old.world is old.session.world and type(old.world).__name__ == "CampaignWorld")
check("...and adopting resets nothing a test set up", canon.ids().get("someone") == "x" or "player" in canon.ids().values())
st.close()

# ---- the sources
src = pathlib.Path("main.py").read_text(encoding="utf-8")
loop = src[src.index("    while True:"):]
check("main.py opens every campaign as a session inside the loop, before the scene", "CampaignSession.open(" in loop
      and loop.index("CampaignSession.open(") < loop.index("session.scene(") and "session.close()" in loop)
check("...and builds no store, world, scene or recorder of its own", not any(s in src for s in ("campaign_world", "CampaignStore.open_or_create", "WorldScene(", "load_world", "Recorder(")))
check("the Threshold hands the session the creation's background thread", "self.session.own(self.passives_job.thread)" in pathlib.Path("scenes/goddess.py").read_text(encoding="utf-8"))
check("the replayer opens its campaigns through the session too", pathlib.Path("tools/rerun.py").read_text(encoding="utf-8").count("CampaignSession.open(") == 2)
check("the bound lives in config", isinstance(config.CLOSE_WAIT_SECONDS, (int, float)) and config.CLOSE_WAIT_SECONDS <= 5)

# ---- (f783) closing a campaign runs every stage, whatever the one before it did (TASK_FAILURE-14; engine6-7)
from engine import crashlog, domain_events
from engine import session as session_mod
from llm import backend
import ui.console as uc
config.CRASH_LOG_PATH = str(simlib.saves_path("session_453_logs", "crash.log"))     # the faults this part makes stay out of logs/
recording.FOLDER = simlib.saves_path("session_453_recordings")                       # ...and the recorder's trimming out of recordings/
wait_was, config.CLOSE_WAIT_SECONDS = config.CLOSE_WAIT_SECONDS, 0.2                 # each close waits this long for the thread held open


def new_wheres(since: list) -> list:
    """The places of the crash entries written since `since` (crashlog.SESSION as it stood), by identity: it keeps only the last few."""
    return [e["where"] for e in crashlog.SESSION if all(e is not s for s in since)]


run_every = getattr(crashlog, "run_every", None)
check("(f783) engine/crashlog.py has run_every(where, *stages): each stage runs whatever the one before it did", run_every is not None)
if run_every is not None:
    ran = []

    def step(n, fault=None):
        def run():
            ran.append(n)
            if fault is not None:
                raise fault
        return run
    first, since = ValueError("the first stage's fault"), list(crashlog.SESSION)
    try:
        run_every("f783 probe", ("one", step(1, first)), ("two", step(2, KeyError("the second's"))), ("three", step(3)))
        got = None
    except BaseException as e:
        got = e
    check("...the first error is raised once the last stage has run, and a later one is written down once, under its stage's name",
          ran == [1, 2, 3] and got is first and new_wheres(since) == ["f783 probe: two"], (ran, got, new_wheres(since)))
    ran.clear()
    try:
        run_every("f783 probe", ("one", step(1, KeyboardInterrupt())), ("two", step(2)))
        got = None
    except BaseException as e:
        got = e
    check("...and what is no Exception (Ctrl+C) in a stage still lets the later ones run before it goes on up",
          ran == [1, 2] and isinstance(got, KeyboardInterrupt), (ran, got))
    ran.clear()
    first = ValueError("the first stage's fault, again")
    try:
        run_every("f783 probe", ("one", step(1, first)), ("two", step(2, KeyboardInterrupt())), ("three", step(3)))
        got = None
    except BaseException as e:
        got = e
    check("...and Ctrl+C in a later stage, after one that failed, still lets the stage after it run, then goes on up holding the "
          "first as its context", ran == [1, 2, 3] and isinstance(got, KeyboardInterrupt) and got.__context__ is first, (ran, got))
    entry = crashlog.record(first, "f783 probe: what main.py writes")
    log = crashlog.path().read_text(encoding="utf-8").split(crashlog.SEP)[-1]
    check("...and the error raised names its stage in a note, which the crash entry main.py writes carries",
          getattr(first, "__notes__", None) == ["f783 probe: one"] and "f783 probe: one" in log and entry["where"] in log,
          (getattr(first, "__notes__", None), log[-300:]))

# reset() puts back every owned binding whatever the one before it did (the session's last stage, and every open)
real_owned = session_mod._owned
canon.set_ids({**canon.ids(), "someone": "x"})
enchanting.set_discount(10)
names.set_cast({"Maren": "she"})
dirty = sorted(simlib.residue())
rows = real_owned()
at = next(i for i, r in enumerate(rows) if r[0] in dirty)          # the first dirty row: the fault goes just before it
fault = RuntimeError("a put back refused")

def refused() -> None:
    raise fault
session_mod._owned = lambda: rows[:at] + [("f783 probe row", refused, lambda: True, lambda: "")] + rows[at:]
try:
    session_mod.reset()
    got = None
except RuntimeError as e:
    got = e
finally:
    session_mod._owned = real_owned
check("(f783) reset() with a put back refused in the middle: every row after it is still put back, and that error is raised, "
      "naming the row", 0 < at < len(rows) - 1 and len(dirty) >= 3 and got is fault and simlib.residue() == {}
      and getattr(fault, "__notes__", None) == ["putting back the owned state: f783 probe row"], (at, dirty, got, simlib.residue()))


def store_closed(store) -> bool:
    try:
        store._db.execute("SELECT 1")
    except sqlite3.ProgrammingError:
        return True
    return False


SPIED, BREAK = {}, {}                                   # what each stage was called with; the fault a stage raises in its place
def spy(stage, real):
    def fn(*a, **k):
        SPIED.setdefault(stage, []).append(a)
        if stage in BREAK:
            raise BREAK[stage]
        return real(*a, **k)
    return fn
real_cancel, real_orphan, real_drop, real_reset = backend.cancel_session, recording.orphan, backfill.drop, session_mod.reset
backend.cancel_session, recording.orphan = spy("cancel", real_cancel), spy("orphan", real_orphan)
backfill.drop, session_mod.reset = spy("drop", real_drop), spy("reset", real_reset)
CONSOLE = {n: uc.channel().get(n) for n in ("ask",) + recording.STORY}


class Refused:
    """A log the disk refuses: its write raises, or its close (the flush it makes) does; the file itself is closed either way."""
    def __init__(self, f, fault, at):
        self.f, self.fault, self.at = f, fault, at

    def write(self, s):
        if self.at == "write":
            raise self.fault
        return self.f.write(s)

    def flush(self):
        self.f.flush()

    def close(self):
        self.f.close()
        if self.at == "close":
            raise self.fault


def played(name: str, seed: int):
    """A campaign recorded into a folder of its own, one line played and its row still to write, a thread of its own held open, its
    store's close and its bus's clearing spied."""
    g = simlib.campaign(name, cls="warrior", seed=seed)
    rec = g.session.record(folder=simlib.saves_path(name + "_rec"))
    stub.plan = [{"kind": "look"}]
    g.scene.turn("I look around.")
    rec.open_input = True                                 # as after a line typed: its row is written as the recorder closes
    hold = threading.Event()
    held = g.session.own(threading.Thread(target=hold.wait, args=(15,), daemon=True))
    held.start()
    g.store.close = spy("store", g.store.close)
    g.session.bus.clear = spy("bus", g.session.bus.clear)
    return g, rec, held, hold


def closed_with(g, rec, faults: dict):
    """g closed with each stage named in `faults` raising its fault: 'meta', 'row' and 'calls' are the recorder's (meta.json, the last
    input's row, the call log's close), the rest the session's. Returns what the close raised."""
    for at, fault in faults.items():
        if at == "meta":
            (rec.dir / "meta.json").unlink()
            (rec.dir / "meta.json").mkdir()               # meta.json cannot be written: a folder stands in its place
        elif at == "row":
            rec.turns = Refused(rec.turns, fault, "write")
        elif at == "calls":
            rec.calls = Refused(rec.calls, fault, "close")
        else:
            BREAK[at] = fault
    SPIED.clear()
    try:
        g.close()
        return None
    except BaseException as e:
        return e
    finally:
        BREAK.clear()


ORDER = ("recorder", "cancel", "orphan", "drop", "store", "bus", "reset")
STAGE = {"meta": "recorder", "row": "recorder", "calls": "recorder"}
WHAT = {"meta": "meta.json (a folder in its place: the finder's case)", "row": "the last input's row (the disk full)",
        "calls": "the call log's close (the disk full at its flush)", "cancel": "the cancel of its background calls",
        "orphan": "the orphaning of its threads", "drop": "the forgetting of its jobs", "store": "the store's close",
        "bus": "the clearing of its bus", "reset": "the putting back of the owned state"}


def left(g, rec, held) -> dict:
    """What each stage of the close left: by its effect where it has one, else by the call it made."""
    return {"recorder": rec.closed and rec._layer not in backend.layers() and not streams.STRICT and g.session.recorder is None
                        and all(uc.channel().get(n) == f for n, f in CONSOLE.items()),
            "cancel": [a[0] for a in SPIED.get("cancel", [])] == [str(g.store.root)],
            "orphan": held in recording.ORPHANS,
            "drop": [a[0] is g.store for a in SPIED.get("drop", [])] == [True],
            "store": store_closed(g.store),
            "bus": isinstance(domain_events.current(), domain_events.IdleBus) and g.session.bus.subscribers() == 0,
            "reset": simlib.residue() == {}}


def tidy(g, rec, hold) -> None:
    """What a close left undone put right by hand, so the next case starts clean: the close itself is what is checked."""
    hold.set()
    if rec.unwrap is not None:
        rec.unwrap()
        rec.unwrap = None
    for ch, n, fn in reversed(rec.undo):
        ch.set(n, fn)
    rec.undo, rec.closed, streams.STRICT = [], True, False
    if not store_closed(g.store):
        type(g.store).close(g.store)
    real_reset()


CASES = [("meta",), ("row",), ("calls",), ("cancel",), ("orphan",), ("drop",), ("store",), ("bus",), ("reset",), ("calls", "store")]
names_made = []
for i, broken in enumerate(CASES):
    name = f"session_453_close_{i}"
    names_made += [name, name + "_rec"]
    g, rec, held, hold = played(name, 60 + i)
    faults = {at: None if at == "meta" else OSError(28, f"No space left on device ({at})") if at in STAGE else RuntimeError(f"refused: {at}")
              for at in broken}
    since = list(crashlog.SESSION)
    got = closed_with(g, rec, faults)
    raised = (isinstance(got, OSError) and str(got.filename or "").endswith("meta.json")) if broken[0] == "meta" else got is faults[broken[0]]
    done = left(g, rec, held)
    out = {STAGE.get(at, at) for at in broken} - {"recorder"}     # the recorder's take-off holds even when one of its writes failed
    missing = [s for s in ORDER if s not in out and not done[s]]
    if len(broken) == 1:
        check(f"(f783) a close refused at {WHAT[broken[0]]}: that error is raised, and every other stage still did its work"
              + (" (the recorder taken off, its background calls ended, its thread orphaned, its jobs forgotten, the store closed, the "
                 "bus idle, every owned binding put back)" if i == 0 else ""), raised and not missing, (got, missing))
    else:
        wheres = [w for w in new_wheres(since) if w.startswith("closing a campaign")]
        check(f"(f783) a close refused at {WHAT[broken[0]]} and then at {WHAT[broken[1]]}: the first is the error raised, the second is "
              "written down once under the store's stage, and every other stage still did its work",
              raised and not missing and len(wheres) == 1 and "store" in wheres[0], (got, missing, wheres))
    if broken == ("meta",):
        check("...and the error raised names the stage in notes, the recorder's own and the session's, so the crash entry says where",
              getattr(got, "__notes__", None) == ["closing a recording: meta.json", "closing a campaign: the recorder"],
              getattr(got, "__notes__", None))
        SPIED.clear()
        try:
            g.close()
            again = "returned"
        except BaseException as e:
            again = e
        check("...and a second close of the campaign whose close was refused does nothing", again == "returned" and not SPIED, (again, SPIED))
    if broken == ("row",):
        n_old = rec.n_call
        names_made.append("session_453_close_next")
        nxt = simlib.campaign("session_453_close_next", cls="warrior", seed=59)
        nxt.scene.turn("I look around.")
        check("...and the next campaign in the same process, with no recorder of its own, writes no call into the old recording",
              rec.n_call == n_old, (n_old, rec.n_call))
        nxt.close()
    tidy(g, rec, hold)
backend.cancel_session, recording.orphan, backfill.drop, session_mod.reset = real_cancel, real_orphan, real_drop, real_reset
config.CLOSE_WAIT_SECONDS = wait_was

life._ask = real_ask
for n in ("session_453_a", "session_453_b", "session_453_rec", "session_453_logs", "session_453_recordings", *names_made):
    shutil.rmtree(simlib.saves_path(n), ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
