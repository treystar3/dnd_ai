"""Passives are written in the background while the player reads and picks abilities."""
import sys, time, threading, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import ui.console as uc
LOG = []
uc.wait = lambda m, *a, **k: LOG.append(("wait", m))
uc.note = lambda m, *a, **k: LOG.append(("note", m))
uc.debug = lambda m, *a, **k: None
uc.show_actives = lambda a: LOG.append(("show_actives",))
uc.show_passives = lambda a: LOG.append(("show_passives",))
from character import creation
from llm.contracts import PlayerTurn, ClassInterpretation
from llm.gateway import LLMError
from core.models import Archetype
from scenes.goddess import ThresholdScene, Step
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def scene(passive_delay=0.0, fail_first=False):
    s = ThresholdScene.__new__(ThresholdScene)
    ThresholdScene.__init__(s)
    s.interp = ClassInterpretation(archetype=Archetype("warrior"), custom_class="X", combat_identity="x", themes=["a"], summary="x")
    s.step = Step.CONFIRM_CLASS
    s.speak = lambda text: LOG.append(("speak", text[:30]))
    calls = {"n": 0, "thread": []}
    creation.generate_actives = lambda interp: [types.SimpleNamespace(name=f"A{i}", description="d") for i in range(15)]
    def gp(interp, actives):
        calls["n"] += 1
        calls["thread"].append(threading.current_thread().name)
        time.sleep(passive_delay)
        if fail_first and calls["n"] == 1:
            raise LLMError("bad")
        return [types.SimpleNamespace(name=f"P{i}", description="d") for i in range(15)]
    creation.generate_passives = gp
    creation.check_active_picks = lambda options, picks: None
    creation.check_passive_picks = lambda options, picks: None
    return s, calls

# starts after the actives are shown and the goddess has spoken, runs off the main thread
LOG.clear()
s, calls = scene(passive_delay=0.3)
s.on_confirm_class(PlayerTurn(kind="confirm"))
check("actives are shown first", LOG[1][0] == "show_actives" and LOG[2][0] == "speak", LOG)
check("passives are not ready yet while the player reads", s.passives_job is not None and not s.passives_job.ready)
check("they run in a background thread", True)
time.sleep(0.05)
check("the background thread did the work", calls["thread"] and calls["thread"][0] != threading.main_thread().name, calls["thread"])
t0 = time.time()
s.on_actives(PlayerTurn(kind="answer", picks=[1, 2]))
waited = time.time() - t0
check("picking before they are ready waits for them, with a note", waited > 0.1 and any(e[0] == "wait" and "settling" in e[1] for e in LOG), (waited, LOG))
check("the player then reaches the passives step with them", s.step == Step.PASSIVES and len(s.passive_options) == 15)
check("passives were generated once", calls["n"] == 1, calls)

# ready before the player picks: no waiting
LOG.clear()
s, calls = scene(passive_delay=0.0)
s.on_confirm_class(PlayerTurn(kind="confirm"))
time.sleep(0.2)
check("ready passives are used at once", s.passives_job.ready)
LOG.clear()
s.on_actives(PlayerTurn(kind="answer", picks=[1, 2]))
check("no wait note when ready", not any(e[0] == "wait" for e in LOG))
check("step moves on", s.step == Step.PASSIVES)

# a failed background attempt is retried once, blocking
s, calls = scene(passive_delay=0.0, fail_first=True)
s.on_confirm_class(PlayerTurn(kind="confirm"))
time.sleep(0.2)
s.on_actives(PlayerTurn(kind="answer", picks=[1, 2]))
check("a failed background attempt is retried", calls["n"] == 2 and s.step == Step.PASSIVES, calls)

# both fail: the player is told and can pick again
s, calls = scene(passive_delay=0.0)
creation.generate_passives = lambda interp, actives: (_ for _ in ()).throw(LLMError("bad"))
s.on_confirm_class(PlayerTurn(kind="confirm"))
time.sleep(0.2)
LOG.clear()
s.on_actives(PlayerTurn(kind="answer", picks=[1, 2]))
check("when passives cannot be made, the step does not advance and the player is told", s.step == Step.ACTIVES and any(e[0] == "note" for e in LOG))
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
