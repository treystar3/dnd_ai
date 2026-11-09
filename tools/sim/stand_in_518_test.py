"""(f518) The suite's stand-in, the replayer and every test answer through the game's own model interface; nothing outside llm/
touches the embedder's state or the interface's lists.

- The fence (tools/model_fence.py): no file outside llm/ reads or writes embed._state or the interface's lists, in code or in a child
  script held in a string.
- One way for errors: a stand-in's errors are read on the kinds (a plain ConnectionError the server's, a Failure its own kind, no server
  at all unreachable, anything else no kind), and a recorded error row (every one in the three kept recordings) replays as the kind it
  was recorded as.
- Nothing installed: under the suite's switch a call fails at once as unreachable (one try), builds and starts nothing; a planted
  ConnectionError is still the server's (three tries).
- A timed-out try is worded from the turn's limit exactly when that limit cut it, and no client is read to say so.
- The sources are a stack: each handle takes away exactly its own. A stand-in is handed the turn's deadline only when its function
  names it, sends a PASS on below it, and has an embedder exactly when given one; the embedder's answer is the source's (R4).
- A replay holds the no-server switch while it serves and puts it back, takes its source away, and a faulted turn fails the command.
- The three kept recordings, made again through the stand-in, give byte-identical rows: tools/sim/layers_517_test.py checks it.

Run: python tools/sim/stand_in_518_test.py"""

import gzip
import json
import os
import subprocess
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
os.chdir(ROOT)
os.environ["MERAVIA_NO_SERVER"] = "1"

from pydantic import create_model

import config
from llm import backend, embed, gateway
from llm.errors import Failure, LLMError, NoServer
from llm.sampling import Sampling

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


Read = create_model("Read", x=(str, ""))
MSG = [{"role": "user", "content": "Read"}]
config.LOG_PATH = "saves/stand_in_518_llm_calls.jsonl"

# ---- 1. the fence
import model_fence
found = model_fence.problems()
check("no file outside llm/ reads or writes the embedder's state or the interface's lists", found == [], found[:10])

# ---- 2. one way for errors
OLD = [ConnectionError("down"), Failure("server", "bad gateway"), Failure("deadline", "stalled"), Failure("too_big", "over"),
       NoServer("none here"), RuntimeError("fell over")]


def raised_by(source) -> BaseException | None:
    undo = backend.use(source)
    try:
        backend.chat(MSG, Read, Sampling(0.5), 50)
        return None
    except BaseException as e:
        return e
    finally:
        undo()


def shape(e):
    return (type(e).__name__, getattr(e, "kind", None), getattr(e, "legacy", None))


same = []
for err in OLD:
    def boom(**k):
        raise err
    a = raised_by(backend.StandIn(chat=boom))
    same.append((type(err).__name__ + (f":{err.kind}" if isinstance(err, Failure) else ""), shape(a)))
kinds = {n: k for n, (_, k, _) in same}
check("a stand-in's errors are read on the kinds: a ConnectionError is the server's (its pair kept), a Failure its own kind, no server "
      "at all unreachable, and anything else no kind (the call failed)",
      kinds == {"ConnectionError": "server", "Failure:server": "server", "Failure:deadline": "deadline", "Failure:too_big": "too_big",
                "NoServer": "unreachable", "RuntimeError": None}
      and next(s for n, s in same if n == "ConnectionError")[2] == ("ConnectionError", "down"), (kinds, same))

from engine import recording
ERROR_ROWS = 12                    # (f527) the error rows the three kept recordings hold after the one re-bless
trip = []
for err in OLD[:-1] + [Failure("server", "down"), Failure("deadline")]:
    f = backend.failure_of(err)
    written = recording._error(f)                                   # (f527) {kind, detail}, the interface's own
    trip.append((type(err).__name__, f.kind, written["kind"]))
check("an error written to a recording replays as the kind it was read as (written, then read back)", all(a == b for _, a, b in trip), trip)
rows = []
for name in ("stub_short", "stub_party", "stub_fight"):
    with gzip.open(ROOT / "data/replay/sessions" / name / "calls.jsonl.gz", "rt", encoding="utf-8") as fh:
        rows += [json.loads(l) for l in fh if l.strip() and '"error"' in l]
errs = [r["error"] for r in rows if r.get("error")]
check(f"(f527) every error row in the three kept recordings ({len(errs)}) is the server's failure, in the interface's own form",
      len(errs) == ERROR_ROWS and all(isinstance(e, dict) and e.get("kind") == "server" and e.get("detail") for e in errs), errs[:4])
import inspect
import rerun
replay_src = inspect.getsource(rerun.Replay)
check("...and the replayer imports neither of the old client's packages to do it (its old _failure is gone)",
      not any(w in replay_src for w in ("import ollama", "import httpx", "from ollama", "from httpx")) and not hasattr(rerun, "_failure"))

# ---- 3. nothing installed
CHILD = r'''
import json, multiprocessing, os, subprocess, sys, time
sys.path.insert(0, ".")
started = []
real_init = subprocess.Popen.__init__
def spy(self, *a, **k):
    started.append(str(a[0] if a else k.get("args")))
    return real_init(self, *a, **k)
subprocess.Popen.__init__ = spy
from pydantic import create_model
from llm import backend, gateway
from llm.errors import Failure, LLMError
from llm.sampling import Sampling
from engine import budget, refusals
Read = create_model("Read", x=(str, ""))
t0 = time.perf_counter()
try:
    backend.chat([{"role": "user", "content": "x"}], Read, Sampling(0.5), 50)
    kind = None
except Failure as e:
    kind = e.kind
took = time.perf_counter() - t0
b = budget.open(limit=600)
n0 = len(refusals.SESSION)
try:
    gateway.generate("work_offer_read", "Read the offer.", "Morning.", Read, retries=2)
    gen = None
except LLMError as e:
    gen = e.failure
charged = len(b.charges)
budget.close()
print(json.dumps({"kind": kind, "took": took, "gen": gen, "attempts": gateway.OUTCOMES[-1][2] if gateway.OUTCOMES else None,
                  "charged": charged, "refusal": [r["kind"] for r in refusals.SESSION[n0:]],
                  "packages": [m for m in ("httpx",) if m in sys.modules], "procs": started, "children": len(multiprocessing.active_children())}))
'''
r = subprocess.run([sys.executable, "-c", CHILD], cwd=ROOT, env=dict(os.environ, MERAVIA_NO_SERVER="1", PYTHONPATH=str(ROOT)),
                   capture_output=True, text=True, timeout=300)
try:
    got = json.loads(r.stdout.strip().splitlines()[-1])
except Exception:
    got = {"error": (r.stdout + r.stderr)[-600:]}
check("with nothing installed a call fails at once as unreachable", got.get("kind") == "unreachable" and got.get("took", 9) < 1.0, got)
check("...a generate() gives up after one try, charged nothing, filed as the model down", got.get("gen") == "unreachable"
      and got.get("attempts") == 1 and got.get("charged") == 0 and got.get("refusal") == ["model_down"], got)
check("...and nothing was imported or started", got.get("packages") == [] and got.get("procs") == [] and got.get("children") == 0, got)


def down(**k):
    raise ConnectionError("the model server cannot be reached")


undo = backend.use(backend.StandIn(chat=down))
try:
    gateway.generate("work_offer_read", "Read the offer.", "Morning.", Read, retries=2)
    planted = None
except LLMError as e:
    planted = (e.failure, gateway.OUTCOMES[-1][2])
finally:
    undo()
check("...while a planted ConnectionError is still the server's failure: three tries (design_plan.md:665)", planted == ("server", 3), planted)

# ---- 4. a timed-out try's words: from the turn's limit when a source's own Failure met one; a replayed pair of the old client's as the client's own
cases = []
for legacy, limit, want in ((("ReadTimeout", "x"), None, "120"), (("ReadTimeout", "x"), 44.2, "120"), (None, None, "120"), (None, 44.2, "44")):
    f = Failure("deadline", "x", legacy=legacy)
    kind, words = gateway.failed_try(f, limit)
    cases.append((legacy is not None, limit, kind == "deadline" and f"after {want}s" in words.replace(str(config.REQUEST_TIMEOUT), "120")))
check("a timed-out try is worded from the turn's limit exactly when a source's own failure met one (a replayed pair of the old client's is the client's own)",
      all(ok for *_, ok in cases), cases)

# ---- 5. the sources are a stack; a stand-in's deadline, PASS, calls and embedder
a, b, c = backend.StandIn(name="a"), backend.StandIn(name="b"), backend.StandIn(name="c")
ua, ub, uc = backend.use(a), backend.use(b), backend.use(c)
ub()
top1 = backend.source()
uc()
top2 = backend.source()
ua()
check("the sources are a stack: each handle takes away exactly its own, in any order, the newest left answering",
      top1 is c and top2 is a and backend.source().name == "no-server", (top1.name, top2.name))

seen = {}


def with_deadline(deadline=None, **k):
    seen["deadline"], seen["keys"] = deadline, sorted(k)
    return types.SimpleNamespace(message=types.SimpleNamespace(content='{"x": "ok"}'))


def kwargs_only(**k):
    seen["only"] = sorted(k)
    return types.SimpleNamespace(message=types.SimpleNamespace(content='{"x": "ok"}'))


undo = backend.use(backend.StandIn(chat=with_deadline))
backend.chat(MSG, Read, Sampling(0.5), 50, deadline=37.0)
given = dict(seen)
backend.chat(MSG, Read, Sampling(0.5), 50)
none_given = seen.get("deadline")
undo()
LEGACY = ["format", "messages", "model", "options", "think"]
check("a stand-in whose function names `deadline` is handed the turn's deadline (None for a call with none), beside the old "
      "client's arguments", given.get("deadline") == 37.0 and given.get("keys") == LEGACY and none_given is None, (given, none_given))
undo = backend.use(backend.StandIn(chat=kwargs_only))
backend.chat(MSG, Read, Sampling(0.5), 50, deadline=37.0)
undo()
check("...while one taking **k alone is never handed a `deadline` key: the old client's arguments, exactly", seen.get("only") == LEGACY,
      seen.get("only"))

below = backend.StandIn(chat=lambda **k: types.SimpleNamespace(message=types.SimpleNamespace(content='{"x": "from below"}')), name="below")
top = backend.StandIn(chat=lambda **k: backend.PASS if k["format"]["title"] == "Read" else None, below=below)
undo = backend.use(top)
r = backend.chat(MSG, Read, Sampling(0.5), 50)
undo()
check("a stand-in's PASS sends the request on below it, and the stand-in counts what it was asked", r.text == '{"x": "from below"}'
      and top.calls["Read"] == 1 and below.calls["Read"] == 1, (r, dict(top.calls)))

embed.reset()
undo = backend.use(backend.StandIn(chat=kwargs_only, embed=lambda **k: {"embeddings": [[1.0] for _ in k["input"]]}))
with_embedder = embed.available()
undo()
undo = backend.use(backend.StandIn(chat=kwargs_only))
without = embed.available()
undo()
nothing = embed.available()
check("the embedder is the source's: a stand-in given one has it, one not given one has none, and the suite's default has none",
      with_embedder is True and without is False and nothing is False, (with_embedder, without, nothing))
import rerun
check("...a replay's is its recording's (R4)", rerun.Replay([], {"embed": True}).facts()["embedder"] is True
      and rerun.Replay([], {"embed": False}).facts()["embedder"] is False)
def broken(**k):
    raise ConnectionError("the embedder went away")


undo = backend.use(backend.StandIn(chat=kwargs_only, embed=broken))
embed.reset()
lost = embed.vectors(["clustering: a road"])
off = (embed.failed(), embed.available())
embed.reset()
back = (embed.failed(), embed.available())
undo()
check("...a failed embed turns embeddings off for the session, and embed.reset() turns them back on (no write of its state)",
      lost is None and off == (True, False) and back == (False, True), (lost, off, back))

# ---- 6. (f532) the old client and its shapes are gone: a source keeps the deadline itself (llm/llama.py), a stand-in is handed it
undo = backend.use(backend.StandIn(chat=lambda deadline=None, **k: (_ for _ in ()).throw(Failure("deadline", "stalled"))))
try:
    backend.chat(MSG, Read, Sampling(0.5), 50, deadline=44.2)
    cut = None
except Failure as e:
    cut = e
finally:
    undo()
check("a try cut at the turn's deadline is worded from that limit", cut is not None and cut.kind == "deadline"
      and gateway.failed_try(cut, 44.2)[1] == "timed out after 44s (what was left of the turn's time)", cut)
check("...and one with no limit from the source's own", gateway.failed_try(Failure("deadline", "stalled"), None)[1] == f"timed out after {config.REQUEST_TIMEOUT}s")

# ---- 7. the replayer: the no-server switch held and put back, its source taken away, a faulted turn failing the command
CHILD2 = "\n".join([
    "import json, os, sys",
    "sys.path.insert(0, '.'); sys.path.insert(0, 'tools')",
    "import rerun",
    "from llm import backend",
    "during = set()",
    "out = rerun.replay(rerun.golden('stub_short'), on_call=lambda row, k, *a: during.add(os.environ.get('MERAVIA_NO_SERVER')))",
    "print(json.dumps({'during': sorted(str(d) for d in during), 'after': os.environ.get('MERAVIA_NO_SERVER'),",
    "                  'source': type(backend.source()).__name__, 'matched': out['matched'], 'of': out['of'], 'crashed': out['crashed']}))",
])
env = {k: v for k, v in os.environ.items() if k != "MERAVIA_NO_SERVER"}
env.update(PYTHONPATH=str(ROOT))
run2 = subprocess.run([sys.executable, "-c", CHILD2], cwd=ROOT, env=env, capture_output=True, text=True, timeout=600)
try:
    got = json.loads(run2.stdout.strip().splitlines()[-1])
except Exception:
    got = {"error": (run2.stdout + run2.stderr)[-600:]}
check("a replay holds the no-server switch while it serves (so nothing reaches a live model), puts the switch back as it found it, and "
      "takes its source away", got.get("during") == ["1"] and got.get("after") is None and got.get("source") == "Unstarted"   # (f528) the
      and got.get("matched") == got.get("of") and got.get("crashed") == 0, got)                 # default the settings name: the game's own runtime, unstarted
import contextlib
import io
real_replay = rerun.replay
rerun.replay = lambda folder, **k: {"matched": 41, "of": 41, "parted": None, "calls": 89, "recorded_calls": 89, "crashed": 1, "logs": "x"}
argv, sys.argv = sys.argv, ["rerun.py", "--golden", "stub_short"]
said = io.StringIO()
try:
    with contextlib.redirect_stdout(said):
        rc = rerun.main()
finally:
    sys.argv = argv
    rerun.replay = real_replay
check("...and a turn that faulted while it replayed fails the command, though the state matched", rc == 1 and "faulted" in said.getvalue()
      and "all 41 inputs matched" not in said.getvalue(), (rc, said.getvalue()))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
