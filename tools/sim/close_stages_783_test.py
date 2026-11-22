"""(f783) A close runs every stage, whatever the one before it did (TASK_FAILURE-14, docs/design/33_audit_fix_plan/task_failure.md;
engine6-7): the closes of the same shape beside the campaign's and the recorder's (session_453_test and recorder_440_test hold those),
each through crashlog.run_every, with a fault planted in an early stage. The later stages still run and the first error is the one
raised, a note on it naming its stage:
- the load screen's close (llm/launch.py Screen.close): a model server whose close raises still lets the single-copy lock go, and a
  source that will not come off still closes the server; stand-ins, no server;
- the game's own server stopped (llm/runtime.py stop_for_game): the same three, the same way;
- a replay's end (tools/rerun.py replay): a session whose close raises still puts back the source, the guard on a real server, the
  strict session, the budget and the settings, and drops the replay's save, in a replayer that plays several sessions in one process;
- a stub recording's end (tools/rerun.py make_stub_recording): the planted model and the stub still taken away and the save dropped.
The runtime's own close (llm/runtime.py Runtime.close, a source whose close raises) is held in server_522_test, on its fake server.
Run: python tools/sim/close_stages_783_test.py"""
import os
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 783))
SHOWN = simlib.quiet_console()
import config
config.CRASH_LOG_PATH = str(simlib.saves_path("close_stages_783_logs", "crash.log"))   # the faults this test makes stay out of logs/
from engine import budget, recording, streams
from engine.session import CampaignSession
from llm import backend, launch, runtime
from storage import campaign
import rerun

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


# ---- the load screen and the game's server: stand-ins for the source, the server and the lock
order: list = []


class Server:
    def __init__(self, fault=None):
        self.fault = fault

    def close(self):
        order.append("server")
        if self.fault is not None:
            raise self.fault


class Lock:
    def release(self):
        order.append("lock")


def undo_of(fault=None):
    def undo():
        order.append("source")
        if fault is not None:
            raise fault
    return undo


for stage in ("server", "source"):
    fault = RuntimeError(f"the {stage} refused")
    order.clear()
    sc = launch.Screen(say=lambda *a: None, ask=lambda: "quit")
    sc.undo, sc.rt, sc.lock = undo_of(fault if stage == "source" else None), Server(fault if stage == "server" else None), Lock()
    try:
        sc.close()
        got = None
    except RuntimeError as e:
        got = e
    name = "the model server" if stage == "server" else "the interface's source"
    check(f"(f783) the load screen closed with {name} refusing: that error is raised, naming the stage, and every stage after it still "
          "ran, the single-copy lock let go", got is fault and order == ["source", "server", "lock"] and sc.lock is None
          and fault.__notes__ == [f"closing the load screen: {name}"], (got, order, getattr(fault, "__notes__", None)))

    order.clear()
    fault = RuntimeError(f"the {stage} refused, as the game stops")
    runtime._GAME.update(rt=Server(fault if stage == "server" else None), lock=Lock(), undo=undo_of(fault if stage == "source" else None))
    try:
        runtime.stop_for_game()
        got = None
    except RuntimeError as e:
        got = e
    want = ["server", "source", "lock"]
    check(f"(f783) the game's own server stopped with {name} refusing: that error is raised, naming the stage, and every stage "
          "after it still ran, the lock let go", got is fault and order == want and not runtime._GAME
          and fault.__notes__ == [f"stopping the game's model server: {name}"], (got, order, getattr(fault, "__notes__", None)))


# ---- a replay's end and a stub recording's end: the session's close raises after it has closed
real_close = CampaignSession.close
fault = RuntimeError("the session's close refused")


def refusing(self) -> None:
    real_close(self)
    raise fault


def env() -> str | None:
    return os.environ.get("MERAVIA_NO_SERVER")


source_before, env_before = backend.source(), env()
profile_before, slow_before, cached_before = dict(budget.PROFILE), budget.SLOW, budget.CACHED
settings_before = (config.THINK_TASKS, config.THINK_ROOM, config.SAMPLING_ARM)
copy = simlib.saves_path("close_stages_783_rec")
shutil.rmtree(copy, ignore_errors=True)
shutil.copytree(rerun.golden("stub_short"), copy)
budget.SLOW, budget.CACHED = True, True                   # the replay sets its own from the recording; these must come back
config.THINK_TASKS, config.SAMPLING_ARM = frozenset({"narrate"}), "f783 arm"
marked = (dict(budget.PROFILE), budget.SLOW, budget.CACHED, config.THINK_TASKS, config.THINK_ROOM, config.SAMPLING_ARM)
CampaignSession.close = refusing
try:
    rerun.replay(copy)
    got = None
except RuntimeError as e:
    got = e
finally:
    CampaignSession.close = real_close
save = Path(campaign.SAVES_DIR) / f"rerun_{copy.name}_{os.getpid()}"
put_back = {"source": backend.source() is source_before, "guard": env() == env_before, "strict": streams.STRICT is False,
            "budget": (dict(budget.PROFILE), budget.SLOW, budget.CACHED) == marked[:3],
            "settings": (config.THINK_TASKS, config.THINK_ROOM, config.SAMPLING_ARM) == marked[3:], "save": not save.exists()}
check("(f783) a replay whose session's close raises: that error is raised, naming the stage, and the source, the guard on a real "
      "server, the strict session, the budget and the settings are put back and the replay's save dropped",
      got is fault and all(put_back.values()) and "ending a replay: its session" in getattr(fault, "__notes__", []),
      (got, put_back, getattr(fault, "__notes__", None)))
budget.PROFILE.clear()
budget.PROFILE.update(profile_before)
budget.SLOW, budget.CACHED = slow_before, cached_before
config.THINK_TASKS, config.THINK_ROOM, config.SAMPLING_ARM = settings_before
streams.STRICT = False

fault = RuntimeError("the session's close refused, at a stub recording's end")
made = simlib.saves_path("close_stages_783_made")
shutil.rmtree(made, ignore_errors=True)
CampaignSession.close = refusing
try:
    rerun.make_stub_recording(made, n=2)
    got = None
except RuntimeError as e:
    got = e
finally:
    CampaignSession.close = real_close
save = Path(campaign.SAVES_DIR) / ("rerun_make_" + made.name)
check("(f783) a stub recording whose session's close raises: that error is raised, naming the stage, and the planted model and the "
      "stub are still taken away and its save dropped", got is fault and backend.source() is source_before and not save.exists()
      and env() == env_before and "ending a stub recording: its session" in getattr(fault, "__notes__", []),
      (got, backend.source(), source_before, save.exists(), getattr(fault, "__notes__", None)))

for p in (copy, made, simlib.saves_path("close_stages_783_logs")):
    shutil.rmtree(p, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
