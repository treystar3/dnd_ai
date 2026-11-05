"""(f516) A model source's failures on the neutral kinds, and a cancel that is never a failure.

- Each kind a source raises does what the design's table says: the server's failure is one failed try, charged, and the next goes; a
  deadline ends the tries, charged, as a timeout always did; a server that cannot be reached or a model still loading ends the tries and
  costs nothing; a request refused before it was read (too big, invalid) ends the tries, costs nothing, gets no relaxed retry, and is
  filed as request_refused, apart from an outage. A full slot is too big: no cut-off retry, nobody told they went round in circles.
- The old client's errors map onto the kinds in one place (llm/backend.py failure_of), so nothing recorded or logged moves: Python's
  ConnectionError, an HTTP error and Ollama's own are the server's, a timeout is a deadline, anything else is "the call failed".
- A cancel is an Interrupt, whether a source raises it or tells it as a reply's finish: no try counted, nothing charged, no fallback, no
  refusal, no tally. Raised at a turn's understanding, inside an operation (at a call made inside it or asked outside it), in a talk
  turn, or through the game's own loop, it leaves the save as it was, shows no "not taken" line, writes nothing to logs/crash.log, keeps
  no answer for the call, and the session closes clean. main.guarded closes quietly on it, the night bot does not count it as the model
  failing, and a cancelled embed leaves embeddings on.
- A retry refused as too big for the draft it carried still gets the relaxed retry; a deadline from a source that keeps the limit itself
  is worded from that limit (the seconds the source was given), never by reading the old client.

Run: python tools/sim/failure_kinds_516_test.py"""

import json
import shutil
import sys
import types
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 5)
simlib.install(stub)
SHOWN = simlib.quiet_console(("narrate", "say", "note", "ledger", "out"))

import yaml
from pydantic import BaseModel

import config
from core.interrupts import Interrupt
from engine import asked, budget, crashlog, failures, refusals
from llm import backend, embed, gateway
from llm.errors import Cancelled, Failure, LLMError
from storage import statehash

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


SAVE = "failure_kinds_516"
shutil.rmtree(f"saves/{SAVE}", ignore_errors=True)
Path(f"saves/{SAVE}").mkdir(parents=True)
config.LOG_PATH = f"saves/{SAVE}/llm_calls.jsonl"
config.CRASH_LOG_PATH = f"saves/{SAVE}/crash.log"


class Read(BaseModel):
    x: str


TASKS = (yaml.safe_load(Path("data/rules/budget.yaml").read_text(encoding="utf-8")) or {}).get("tasks") or {}
TASK = next(t for t, v in TASKS.items() if (v or {}).get("need") == "required")


class Source:
    """A model source that fails every try with one kind, or answers with one reply."""
    name = "fake"

    def __init__(self, kind=None, reply=None, raw=None):
        self.kind, self.reply, self.raw, self.asked = kind, reply, raw, []

    def chat(self, req, deadline=None):
        self.asked.append([m["content"] for m in req.messages])
        if self.raw is not None:
            raise self.raw
        if self.kind:
            raise Failure(self.kind, f"the {self.kind} detail")
        return self.reply


class Script:
    """A model source that plays its steps in order: a Reply is answered, a kind's name is raised as that Failure."""
    name = "script"

    def __init__(self, *steps):
        self.steps, self.asked = list(steps), []

    def chat(self, req, deadline=None):
        self.asked.append([m["content"] for m in req.messages])
        step = self.steps.pop(0) if self.steps else backend.Reply(text='{"x": "ok"}')
        if isinstance(step, str):
            raise Failure(step, f"the {step} detail")
        return step


def last_logged() -> dict:
    rows = [json.loads(l) for l in Path(config.LOG_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows[-1] if rows else {}


def run(src, relaxed=None, retries=2, task=TASK, max_tokens=config.MAX_TOKENS):
    undo = backend.use(src)
    b = budget.open(limit=600)
    f0, r0, o0 = len(gateway.FALLBACKS), len(refusals.SESSION), len(gateway.OUTCOMES)
    t0 = dict(gateway.TALLY.get(task, {"calls": 0, "failed": 0, "attempts": 0}))
    try:
        got = gateway.generate(task, "Read the offer.", "Morning.", Read, retries=retries, relaxed_context=relaxed, max_tokens=max_tokens)
    except BaseException as e:
        got = e
    finally:
        budget.close()
        undo()
    t1 = gateway.TALLY.get(task, {"calls": 0, "failed": 0, "attempts": 0})
    return types.SimpleNamespace(err=got if isinstance(got, BaseException) else None, answer=None if isinstance(got, BaseException) else got,
                                 tries=len(src.asked), charged=len([c for c in b.charges if c[0] == task]),
                                 fallbacks=gateway.FALLBACKS[f0:], refusals=[r["kind"] for r in refusals.SESSION[r0:]],
                                 outcomes=gateway.OUTCOMES[o0:], tally=tuple(t1[k] - t0[k] for k in ("calls", "failed", "attempts")))


# ---- 1. each kind, by the design's table: (tries of 3, tries charged, refusal filed, the transport flag)
TABLE = {
    "server":      (3, 3, "model_down", True),
    "deadline":    (1, 1, "model_down", True),
    "unreachable": (1, 0, "model_down", True),
    "loading":     (1, 0, "model_down", True),
    "too_big":     (1, 0, "request_refused", False),
    "invalid":     (1, 0, "request_refused", False),
}
for kind, (tries, charged, filed, transport) in TABLE.items():
    r = run(Source(kind))
    got = (isinstance(r.err, LLMError), r.tries, r.charged, r.refusals, getattr(r.err, "transport", None), getattr(r.err, "failure", None),
           r.fallbacks, r.outcomes, r.tally)
    want = (True, tries, charged, [filed], transport, kind, [TASK], [(TASK, False, tries)], (1, 1, tries))
    check(f"{kind}: {tries} {'try' if tries == 1 else 'tries'}, {charged} charged, filed as {filed}, one fallback, counted as a failed call",
          got == want, (got, want))

r = run(Source("server"), relaxed={})
check("the relaxed retry after the server's failure is today's (three tries, then two under the looser checks)", r.tries == 5, r.tries)
for kind, said in (("too_big", "a request too big"), ("invalid", "an invalid request"), ("unreachable", "a server out of reach")):
    r = run(Source(kind), relaxed={})
    check(f"...while {said} gets none: it would only fail again", r.tries == 1, r.tries)

src = Script(backend.Reply(text="not json at all"), "too_big", backend.Reply(text='{"x": "ok"}'))
r = run(src, relaxed={})
check("...but a retry refused as too big for the draft it carried still gets the relaxed retry, which sends the request as first made",
      r.err is None and r.answer is not None and r.answer.x == "ok" and r.tries == 3 and len(src.asked[1]) == 4 and len(src.asked[2]) == 2,
      (repr(r.err), r.tries, [len(a) for a in src.asked]))

r = run(Source(reply=backend.Reply(text='{"x": "o', finish="length", usage={"full": True})))
row = last_logged()
check("a full slot (the request and its answer filled the context) is too big: one try, filed as request_refused",
      isinstance(r.err, LLMError) and r.tries == 1 and r.refusals == ["request_refused"] and r.err.failure == "too_big", vars(r))
check("...charged, since it ran, and nobody is told they went round in circles", r.charged == 1 and "circles" not in str(row.get("error"))
      and "too big" in str(row.get("error")), (r.charged, row.get("error")))
prose = config.PROSE_MAX_TOKENS
r = run(Source(reply=backend.Reply(text='{"x": "o', finish="length", usage={"full": True})), task="narrate", max_tokens=prose)
row = last_logged()
check("...the narrator's too: one try, request_refused, never told it went round in circles",
      r.tries == 1 and r.refusals == ["request_refused"] and "circles" not in str(row.get("error")), (r.tries, r.refusals, row.get("error")))
said = Source(reply=backend.Reply(text='{"x": "o', finish="length", usage=None))
run(said, task="narrate", max_tokens=prose)
check("...where an answer of the narrator's cut off at its own ceiling is told that (so the check above could fail)",
      len(said.asked) == 2 and "circles" in said.asked[1][-1], [a[-1][:80] for a in said.asked])
cut = Source(reply=backend.Reply(text='{"x": "o', finish="length", usage=None))
r = run(cut)
check("...while an answer cut off at its own ceiling still gets the cut-off retry, told why",
      r.tries == 2 and "Your last answer was rejected" in cut.asked[1][-1] and r.refusals == ["bad_answer"], (r.tries, cut.asked[1:], r.refusals))

# ---- 2. a cancel is never a failure
for label, src in (("raised as a Failure of kind cancelled", Source("cancelled")), ("raised as Cancelled itself", Source(raw=Cancelled("closing")))):
    r = run(src)
    check(f"a cancel {label} leaves as Cancelled, an Interrupt and no LLMError",
          isinstance(r.err, Cancelled) and isinstance(r.err, Interrupt) and not isinstance(r.err, LLMError), repr(r.err))
    check("...after one try, with nothing charged, no fallback, no refusal, nothing tallied",
          (r.tries, r.charged, r.fallbacks, r.refusals, r.outcomes, r.tally) == (1, 0, [], [], [], (0, 0, 0)), vars(r))

r = run(Source(reply=backend.Reply(text="", finish="cancelled")))
check("a cancel told as a reply's finish is the same: Cancelled, nothing charged, no fallback, no refusal, nothing tallied",
      isinstance(r.err, Cancelled) and (r.tries, r.charged, r.fallbacks, r.refusals, r.outcomes, r.tally) == (1, 0, [], [], [], (0, 0, 0)), vars(r))

# ---- a deadline from a source that keeps the limit itself is worded from that limit, never by reading the old client
import os
import re


class Given(Source):
    """Fails with a deadline, keeping the limit the gateway handed it."""
    def chat(self, req, deadline=None):
        self.deadline = deadline
        return super().chat(req, deadline)


env0 = os.environ.get("MERAVIA_NO_SERVER")
os.environ["MERAVIA_NO_SERVER"] = "1"
given = Given("deadline")
reached0 = gateway.reached()                    # (f518) every try to reach the real client (a call, a read of its inner timeout) counts
try:
    r = run(given)
    row = last_logged()
    reached = gateway.reached() - reached0
finally:
    if env0 is None:
        os.environ.pop("MERAVIA_NO_SERVER", None)
    else:
        os.environ["MERAVIA_NO_SERVER"] = env0
said = re.match(r"timed out after (\d+)s \(what was left of the turn's time\)", str(row.get("error", "")))
check("a new source's deadline is one try and the gateway's own failure, worded from the seconds the source was given",
      isinstance(r.err, LLMError) and r.tries == 1 and said is not None and given.deadline is not None
      and int(said.group(1)) == round(given.deadline), (repr(r.err), row.get("error"), getattr(given, "deadline", None)))
check("...and the old client is never read (never reached, nothing built, nothing raised out of the gateway)", reached == 0 and not gateway.built(),
      (reached, gateway.built()))

# ---- 3. the old client's errors, on the kinds, read as they always were
import httpx
import ollama
gateway.keep_extra_fields()
cases = {
    "ConnectionError": (ConnectionError("Failed to connect to Ollama"), "server"),
    "an HTTP error": (httpx.HTTPError("bad gateway"), "server"),
    "Ollama's own error": (ollama.ResponseError("repeat limit", 500), "server"),
    "a timeout": (httpx.ReadTimeout("stalled"), "deadline"),
}
for label, (e, kind) in cases.items():
    f = backend.failure_of(e)
    check(f"{label} is the {kind} kind, with the old error's type and text kept", f is not None and f.kind == kind
          and f.legacy == (type(e).__name__, str(e)) and f.__cause__ is e, (f and (f.kind, f.legacy)))
check("...and anything else is no kind at all (the gateway's 'the call failed', as before)", backend.failure_of(RuntimeError("x")) is None)

def through(exc, how, retries=2):
    """(f518) The old client's error raised by the client the Ollama-shaped source is given (its own path: the deadline on the client's
    timeout, then the call), or by a stand-in's chat (the suite's path); both send through the one function (llm/backend.py _send)."""
    calls = []

    def chat(**k):
        calls.append(k)
        raise exc
    if how == "ollama":
        undo = backend.use(backend.OllamaShape(client=types.SimpleNamespace(chat=chat)))
    else:
        undo = simlib.stand_in(chat=chat, embed=None)
    try:
        gateway.generate(TASK, "Read the offer.", "Morning.", Read, retries=retries, _quiet=True)
        got = None
    except BaseException as e:
        got = e
    finally:
        undo()
    return got, len(calls), last_logged().get("error")


for how, where in (("ollama", "through the Ollama-shaped source"), ("stand-in", "through a stand-in")):
    got, n, said = through(ConnectionError("Failed to connect to Ollama"), how)
    check(f"{where} a ConnectionError is three failed tries, logged as the server's, the client's error kept as the cause",
          isinstance(got, LLMError) and n == 3 and said == "the model server failed: Failed to connect to Ollama"
          and isinstance(got.__cause__, ConnectionError), (repr(got), n, said, repr(getattr(got, "__cause__", None))))
    got, n, said = through(httpx.ReadTimeout("stalled"), how)
    check("...a timeout one try, logged as timed out", isinstance(got, LLMError) and n == 1 and said.startswith("timed out after"), (n, said))
    got, n, said = through(RuntimeError("the client fell over"), how)
    check("...and an error of no kind three tries, 'the call failed' as before", isinstance(got, LLMError) and n == 3
          and said == "the call failed: RuntimeError: the client fell over", (n, said))
    got, n, said = through(Cancelled("closing"), how)
    check("...and a Cancelled from the client passes straight through on the first try", isinstance(got, Cancelled) and n == 1, (repr(got), n))
check("...and the stub answers again after", isinstance(backend.source(), backend.StandIn) and backend.source().name == "stub", backend.source())

# ---- 4. a cancel at a turn's understanding
crashlog_before = Path(config.CRASH_LOG_PATH).read_text(encoding="utf-8") if Path(config.CRASH_LOG_PATH).exists() else None
g = simlib.campaign(SAVE + "_turn", cls="warrior", seed=5, location="parth")
ws = g.scene
ws.enter("parth")
digest0 = statehash.digest(g.store)["all"]
crashes0 = len(crashlog.SESSION)


class CancelAt:
    """The stub answers every call but the one of this task, which is cancelled (the session closing under it)."""
    name = "cancel-at"

    def __init__(self, task):
        self.task, self.inner, self.cancelled = task, backend.source(), 0      # (f518) the stub answering now, taken before use()

    def chat(self, req, deadline=None):
        if getattr(gateway._TASK, "name", "") == self.task:
            self.cancelled += 1
            raise Failure("cancelled", "the session is closing")
        return self.inner.chat(req, deadline)

    def embed(self, texts):
        return self.inner.embed(texts)


src = CancelAt("interpret_action")
undo = backend.use(src)
SHOWN.clear()
try:
    ws.turn("I look around the square for anyone who needs a hand.")
    got = None
except BaseException as e:
    got = e
finally:
    undo()
check("a cancel at the understanding leaves the turn as Cancelled", isinstance(got, Cancelled) and src.cancelled == 1, (repr(got), src.cancelled))
check("...with the save as it was before the turn", statehash.digest(g.store)["all"] == digest0)
lines = set(failures.lines())
check("...no 'not taken' line shown", not any(t in lines for _, t in SHOWN), [t for _, t in SHOWN if t in lines])
after = Path(config.CRASH_LOG_PATH).read_text(encoding="utf-8") if Path(config.CRASH_LOG_PATH).exists() else None
check("...nothing written to logs/crash.log", after == crashlog_before and len(crashlog.SESSION) == crashes0, crashlog.SESSION[crashes0:])
s = asked.serving()
check("...no answers left served", s is None or not s.answers, s and len(s.answers))


class CancelAll:
    name = "cancel-all"

    def chat(self, req, deadline=None):
        raise Failure("cancelled", "the session is closing")


servings = []
real_begin = asked.begin


def keep_serving(sv):
    if sv is not None and sv not in servings:
        servings.append(sv)
    real_begin(sv)


asked.begin = keep_serving
from engine import operation
for task in ("interpret_action", "npc_conversation"):
    servings.clear()
    before = statehash.digest(g.store)["all"]
    undo = backend.use(CancelAll())
    try:
        ws.asked_operation("probe:" + task, "x", lambda op, _t=task: gateway.generate(_t, "sys", "user", Read))
        got = None
    except BaseException as e:
        got = e
    finally:
        undo()
    where = "asked outside the operation" if task in asked.tasks() else "made inside it"
    check(f"a cancel inside an operation, at a call {where} ({task}), leaves it as Cancelled with no answer kept for it",
          isinstance(got, Cancelled) and servings and all(not sv.answers for sv in servings), (repr(got), [len(sv.answers) for sv in servings]))
    check("...the operation closed, the save as it was, nothing written to logs/crash.log",
          operation.current() is None and asked.serving() is None and statehash.digest(g.store)["all"] == before
          and len(crashlog.SESSION) == crashes0, (operation.current(), len(crashlog.SESSION) - crashes0))
asked.begin = real_begin

from ui import console
script = ["I look around the square for anyone who needs a hand.", "quit"]
real_ask, console.ask = console.ask, lambda *a, **k: script.pop(0) if script else "quit"
SHOWN.clear()
undo = backend.use(CancelAt("interpret_action"))
try:
    ws.run()
    got = None
except BaseException as e:
    got = e
finally:
    undo()
    console.ask = real_ask
check("through the game's own loop, a cancel at the understanding leaves the loop as Cancelled and shows no 'not taken' line",
      isinstance(got, Cancelled) and not any(t in lines for _, t in SHOWN) and len(crashlog.SESSION) == crashes0,
      (repr(got), [t for _, t in SHOWN if t in lines]))
g.close()
check("...and the session closes clean", simlib.residue() == {}, simlib.residue())

g3 = simlib.campaign(SAVE + "_talk", cls="warrior", seed=5, location="tilted_plough")
ws3 = g3.scene
ws3.enter("tilted_plough")
npc = ws3.present[0] if ws3.present else None
check("the inn has someone to talk to", npc is not None)
stub.plan = [{"kind": "talk", "target": npc.id, "speech": "Good day to you. Is there work about?"}]
src = CancelAt("npc_conversation")
before, crashes3 = statehash.digest(g3.store)["all"], len(crashlog.SESSION)
undo = backend.use(src)
try:
    ws3.turn("I say good day and ask if there is work about.")
    got = None
except BaseException as e:
    got = e
finally:
    undo()
    stub.plan = [{"kind": "look"}]
check("a cancel of the townsfolk's answer in a talk turn (asked outside the line's operation) leaves as Cancelled, the save as it was",
      isinstance(got, Cancelled) and src.cancelled == 1 and statehash.digest(g3.store)["all"] == before
      and len(crashlog.SESSION) == crashes3 and operation.current() is None and asked.serving() is None, (repr(got), src.cancelled))
check("...the turn's budget closed and no thread of the session left running before it closes", budget.CURRENT is None
      and g3.session.threads() == [], (budget.CURRENT, g3.session.threads()))
g3.close()
check("...and that session closes clean too", simlib.residue() == {}, simlib.residue())

# ---- 5. main.guarded, the night bot, the embedder
import main as game_main
n0 = len(crashlog.SESSION)
SHOWN.clear()
bridge = types.SimpleNamespace(failed=False)


def closing():
    raise Cancelled("the game is closing")


try:
    game_main.guarded(closing, bridge)
    left = None
except BaseException as e:
    left = e
check("main.guarded closes quietly on a cancel: nothing raised, nothing written, nothing said, the window not marked failed",
      left is None and len(crashlog.SESSION) == n0 and not SHOWN and bridge.failed is False, (repr(left), SHOWN, bridge.failed))

import nightbot
g2 = simlib.campaign(SAVE + "_bot", cls="warrior", seed=5, location="parth")
ws2 = g2.scene
ws2.enter("parth")
bot = nightbot.Bot(ws2, g2.world, __import__("random").Random(5), stub=stub, persona="steady")
for kind, counted in (("cancelled", 0), ("server", 1)):
    before = bot.stats["model_failed"]
    undo = backend.use(Source(kind))
    try:
        line = bot.model_line("I search the place.", {"kind": "search"}, "search", "")
    finally:
        undo()
    check(f"the night bot's line {'cancelled is not' if not counted else 'failed by the server is'} counted as the model failing",
          line == "" and bot.stats["model_failed"] - before == counted, (line, bot.stats["model_failed"] - before))
g2.close()

cache0 = dict(embed._cache)


class EmbedSource:
    name = "embed-fake"

    def __init__(self, exc):
        self.exc = exc

    def embed(self, texts):
        raise self.exc

    def facts(self):
        return {"source": self.name, "embedder": True}      # (f518) the source says it has an embedder: that is what turns embeddings on


for label, exc, failed, raises in (("cancelled", Failure("cancelled", "closing"), False, True),
                                   ("Cancelled itself", Cancelled("closing"), False, True),
                                   ("too big", Failure("too_big", "over the batch"), False, False),
                                   ("the server's failure", Failure("server", "down"), True, False)):
    embed.reset()
    embed._cache.clear()
    undo = backend.use(EmbedSource(exc))
    try:
        out = embed.vectors(["the gate is shut tonight"])
        got = out
    except BaseException as e:
        got = e
    finally:
        undo()
    if raises:
        check(f"an embed {label} leaves as Cancelled, and embeddings stay on", isinstance(got, Cancelled) and embed.failed() is False,
              (repr(got), embed.failed()))
    else:
        check(f"an embed {label} is that call's fallback (None), and embeddings {'go off' if failed else 'stay on'}",
              got is None and embed.failed() is failed, (repr(got), embed.failed()))
embed.reset()
embed._cache.clear()
embed._cache.update(cache0)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
