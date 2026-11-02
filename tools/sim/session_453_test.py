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
    shutil.rmtree(f"saves/{n}", ignore_errors=True)
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
      ledger.LAST is not None and canon.JOURNAL is not None and "player" in canon.IDS.values() and streams.key() != "unseeded", simlib.residue())
enchanting.DISCOUNT["percent"] = 10
names.set_cast({"Maren": "she"})
life.FIRST_BATCH = 4
ws.enter("guild_house")
ws.start_backfill()
check("A's people are being written in the background", backfill.pending(store=a.store) and len(backfill.threads(a.store)) == 1, backfill.threads(a.store))
job_thread = backfill.threads(a.store)[0]
made = {"calls": 0}
def creation_like():
    GATE.wait(15)
    gateway._client.chat(messages=[{"role": "user", "content": "slot 1: farmer"}], format={"title": "ResidentSet", "type": "object"}, model="x")
    made["calls"] += 1
own_thread = threading.Thread(target=creation_like, daemon=True)
own_thread.start()
check("a thread handed to the session is its own", a.session.own(own_thread) is own_thread and own_thread in a.session.threads() and job_thread in a.session.threads())
ledger.add("gained", say="a coin, for the test")             # a look turn records nothing: a row by hand, so the ledger is in the residue
before = simlib.residue()
check("before the close, the residue names what A set", {"canon.JOURNAL", "canon.IDS", "names.CAST", "enchanting.DISCOUNT", "ledger", "streams", "reactions"} <= set(before), before)
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
rec = b.session.record(folder=pathlib.Path("saves/session_453_rec"))
check("the session installs the recorder once", b.session.record() is rec and b.session.recorder is rec and streams.STRICT)
b.scene.turn("I look around.")
n_before = rec.n_call
check("B's turn was recorded", n_before > 0, n_before)
GATE.set()
own_thread.join(10); job_thread.join(10)
check("the orphans ran to the end once let go, each making its call", not own_thread.is_alive() and not job_thread.is_alive() and made["calls"] == 1
      and stub.calls.get("ResidentSet", 0) == rs_calls + 2, (stub.calls.get("ResidentSet", 0), rs_calls))
check("...and B's recording has no row for either", rec.n_call == n_before, (rec.n_call, n_before))
check("...and B's residue is B's own, not empty while it plays", "canon.JOURNAL" in simlib.residue())
b.close()
check("B closed: the recorder is put back and the bindings are clean", simlib.residue() == {} and not streams.STRICT and (pathlib.Path("saves/session_453_rec") / "turns.jsonl").exists())
db = sqlite3.connect("saves/session_453_a/campaign.db")
check("A's database gained nothing from its orphans", db.execute("SELECT count(*) FROM event_log").fetchone()[0] == a_rows)
db.close()
check("the dead orphans are forgotten at the next close", own_thread not in recording.ORPHANS and job_thread not in recording.ORPHANS)

# ---- a scene built the old way adopts a session; nothing is reset under it
from storage.campaign import CampaignStore, PlayerState
canon.IDS["someone"] = "x"
st = CampaignStore.open_or_create("session_453_b")
old = WorldScene(st, authored(), a.catalog, st.load_player())
check("a scene built the old way has a session of its own, adopted, over the store and a wrapped world", old.session.adopted and old.session.store is st
      and old.world is old.session.world and type(old.world).__name__ == "CampaignWorld")
check("...and adopting resets nothing a test set up", canon.IDS.get("someone") == "x" or "player" in canon.IDS.values())
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

life._ask = real_ask
for n in ("session_453_a", "session_453_b", "session_453_rec"):
    shutil.rmtree(f"saves/{n}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
