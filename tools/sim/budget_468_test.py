"""(f468) The turn budget: a second is an estimate from text, the same in every process (the suite has no clock); the module imports no
clock; under a slow profile an optional frame that does not fit is dropped with its fallback standing and no refusal filed, a required
passage over the remainder is told by a stand-in with the outcome standing, and a line whose understanding cannot be afforded is not
taken; a rejected draft is charged twice; the deadline rides on the client's own timeout for the call and is put back, and another
thread's call in that window is neither charged nor refused; a recorded timeout replays as the same failure; a session recorded under a
slow profile replays in a child process with the stand-in chosen at the same call; the turn log's row carries the budget's measures; and
the stub's prompts estimate far under the owner's minute on the measured card."""
import ast
import json
import os
import pathlib
import shutil
import subprocess
import sys
import threading
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import httpx
import ui.console as uc
from engine import budget, failures, refusals, turnlog
from llm import gateway
from npc.models import NPC
from pydantic import BaseModel
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


B = budget.B
cpt = float(B["chars_per_token"])
MEASURED = dict(budget.PROFILE)
TUNABLES = {k: B[k] for k in ("limit_seconds", "margin_seconds", "floor_seconds", "reserve_seconds")}


def restore():
    budget.PROFILE.clear(); budget.PROFILE.update(MEASURED)
    B.update(TUNABLES)


# ---- the estimate, from text alone, the same in every process
got = budget.estimate("narrate", int(2500 * cpt), int(800 * cpt))
want = 2500 / budget.PROFILE["read_tps"] + 800 / budget.PROFILE["write_tps"]
check("estimate(a 2500-token prompt, an 800-token answer) is the prompt at the card's reading speed plus the answer at its writing speed",
      abs(got - want) < 0.1 and (abs(want - (2500 / 756.8 + 800 / 31.7)) < 0.1 if MEASURED == {"read_tps": 756.8, "write_tps": 31.7} else True), (got, want))
code = f"import sys; sys.path.insert(0, '.'); from engine import budget; print(repr(budget.estimate('narrate', {int(2500 * cpt)}, {int(800 * cpt)})))"
outs = [subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, env={**os.environ, "PYTHONHASHSEED": s}, timeout=120).stdout.strip() for s in ("1", "77")]
check("...and the same number in two processes with different PYTHONHASHSEED", outs[0] == outs[1] == repr(got), (outs, repr(got)))
check("a task's expected size stands in for an answer not yet written", abs(budget.estimate("narrate", 0) - B["tasks"]["narrate"]["answer_tokens"] / budget.PROFILE["write_tps"]) < 1e-9)

# ---- the AST fence: no clock, no usage
src = pathlib.Path("engine/budget.py").read_text(encoding="utf-8")
tree = ast.parse(src)
mods = {n.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for n in node.names} | \
       {(node.module or "").split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
check("engine/budget.py imports no clock and reads no usage: a second there is an estimate", not ({"time", "datetime"} & mods) and "perf_counter" not in src and "_usage" not in src, mods)

# ---- under a slow profile
g = simlib.campaign("budget_468", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/budget_468/turns.jsonl"
SHOWN = simlib.quiet_console()
tam = NPC(id="tam468", name="Tam Reed", people="human", role="farmer", location="parth", traits=[], trust=50)
herb = NPC(id="herb468", name="Wen Ashby", people="human", role="herbalist", location="parth", traits=[], trust=50)
store.save_npc(tam); store.save_npc(herb)
ws.enter("parth")
ws.present, ws.residents = [tam, herb], [tam, herb]
ws.player.character.coins = 100000
store.save_player(ws.player)

budget.PROFILE.update(read_tps=1e9, write_tps=10.0)              # the prompt costs nothing; every answer token a tenth of a second
B.update(limit_seconds=20, margin_seconds=0, floor_seconds=1, reserve_seconds=5)
stub.plan = [{"kind": "talk", "target": tam.id, "speech": "Good day to you."}]
n_ref, n_fall, frames0, stakes0 = len(refusals.SESSION), len(gateway.FALLBACKS), stub.calls.get("DialogueFrame", 0), stub.calls.get("BoardStakes", 0)
SHOWN.clear()
stood = ws.turn('I say to Tam, "Good day to you."')
check("an optional frame that does not fit after the reserve is dropped: not called, the reply made and standing plain, the talk stood",
      stood is True and stub.calls.get("DialogueFrame", 0) == frames0 and stub.calls.get("BoardStakes", 0) == stakes0 and stub.calls.get("NPCReply", 0) >= 1
      and ws.last_budget.get("calls") == 3 and not ws.last_budget.get("refused"), (stood, stub.calls.get("DialogueFrame", 0), frames0, ws.last_budget))
check("...the budget names what it dropped; no refusal is filed and no fallback counted", "dialogue_frame" in ws.last_budget.get("dropped", [])
      and ("board_stakes" in ws.last_budget.get("dropped", []) or stub.calls.get("BoardStakes", 0) == stakes0)    # (f486) a farmer's good day reads no board
      and len(refusals.SESSION) == n_ref and len(gateway.FALLBACKS) == n_fall and ws.last_budget["estimated"] > 0, (ws.last_budget, refusals.SESSION[n_ref:]))

B.update(limit_seconds=2.5, margin_seconds=0, floor_seconds=1, reserve_seconds=0.2)      # the understanding fits (two seconds), the passage does not
ws.present, ws.residents = [tam, herb], [tam, herb]
stub.plan = [{"kind": "buy", "ware": "healing draught", "target": herb.id}]
coins0 = store.load_player().character.coins
n_ref, n_fall = len(refusals.SESSION), len(gateway.FALLBACKS)
SHOWN.clear()
stood = ws.turn("I buy a healing draught from the herbalist.")
lines = [t for k, t in SHOWN if k == "narrate"]
check("a required passage over the remainder is told by a stand-in, the purchase standing", stood is True and store.load_player().character.coins < coins0
      and [o.kind for o in ws.line_untold] == ["passage"] and any(herb.label("player") in t and not failures.MACHINERY.search(t) for t in lines),
      (stood, store.load_player().character.coins, coins0, [o.kind for o in ws.line_untold], lines[:3]))
check("...the refusal is the budget's, not the model's: no refusal filed, no fallback counted, the stand-in on the budget's record",
      len(refusals.SESSION) == n_ref and len(gateway.FALLBACKS) == n_fall and ws.last_budget.get("stand_ins") == ["passage"] and "narrate" in ws.last_budget.get("refused", []),
      (refusals.SESSION[n_ref:], gateway.FALLBACKS[n_fall:], ws.last_budget))

B.update(limit_seconds=0.5, margin_seconds=0, floor_seconds=1, reserve_seconds=0.1)
plans0 = stub.calls.get("ActionPlan", 0)
n_ref = len(refusals.SESSION)
ws.present, ws.residents = [tam, herb], [tam, herb]
SHOWN.clear()
stood = ws.turn("I look around.")
check("with less than the floor left before the understanding, the line is not taken, nothing read, no refusal filed",
      stood is False and stub.calls.get("ActionPlan", 0) == plans0 and "budget" in ws.last_failure and len(refusals.SESSION) == n_ref and not ws.last_crash,
      (stood, ws.last_failure, stub.calls.get("ActionPlan", 0), plans0))
restore()

# ---- a rejected first draft charges twice; the deadline rides on the client's timeout; another thread's call is neither charged nor refused
class Tiny(BaseModel):
    ok: bool


class Fake:
    def __init__(self):
        self._client = types.SimpleNamespace(timeout=httpx.Timeout(120.0))
        self.answers = []
        self.seen = []
        self.other = None

    def chat(self, **k):
        self.seen.append(self._client.timeout)
        if self.other is None and threading.current_thread() is threading.main_thread():
            self.other = {}
            t = threading.Thread(target=lambda: self.other.update(got=gateway.generate("interpret_action", "s", "u", Tiny), charges=len(budget.CURRENT.charges)))
            t.start(); t.join()
        text = self.answers.pop(0) if self.answers else '{"ok": true}'
        return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=text))


real = gateway._client
fake = Fake()
gateway._client = fake
b = budget.open()
fake.answers = ["not json at all", '{"ok": true}']
fake.other = {}                                                   # no thread for this one
got = gateway.generate("interpret_action", "system words", "user words", Tiny)
check("a rejected first draft charges twice: both attempts on the budget", isinstance(got, Tiny) and [t for t, _ in b.charges] == ["interpret_action", "interpret_action"]
      and b.spent > 0 and abs(b.required_seconds - b.spent) < 1e-9, b.charges)
dl = b.deadline()
fake.other = None
got = gateway.generate("interpret_action", "system words", "user words", Tiny)
check("the deadline rides on the client's own timeout during the call, and is put back after", fake.seen[-2:] and fake.seen[-2] == httpx.Timeout(float(dl))
      and fake._client.timeout == httpx.Timeout(120.0), (fake.seen[-2:], dl, fake._client.timeout))
check("...and a call from another thread in that window is neither charged nor refused", isinstance(fake.other.get("got"), Tiny) and fake.other.get("charges") == 2
      and fake.seen[-1] == httpx.Timeout(float(dl)), fake.other)
summary = budget.close()
check("the budget closes with its summary, and open again starts from nothing", summary["calls"] == 3 and budget.CURRENT is None and budget.LAST["calls"] == 3, summary)
gateway._client = real

# ---- a recorded timeout replays as the same failure; a session recorded under a slow profile replays in a child process
g.close()
shutil.rmtree("saves/budget_468", ignore_errors=True)
r = simlib.campaign("budget_468_rec", cls="warrior", seed=3, location="parth")
wr, sr = r.scene, r.store
config.TURN_LOG_PATH = "saves/budget_468_rec/turns.jsonl"
herb2 = NPC(id="herb468b", name="Wen Ashby", people="human", role="herbalist", location="parth", traits=[], trust=50)
sr.save_npc(herb2)
wr.player.character.coins = 100000
sr.save_player(wr.player)
CUT = {"on": False}


def cutting_chat(**k):
    if CUT["on"] and k["format"].get("title") == "ActionPlan":
        raise httpx.ReadTimeout("the deadline cut it")
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=cutting_chat)
SCRIPT = ["I look around.", "I look around.", "quit"]
uc.ask = lambda *a, **k: SCRIPT.pop(0) if SCRIPT else "quit"
budget.PROFILE.update(read_tps=1e9, write_tps=0.15)              # nearly seven seconds a token: the understanding leaves less than the floor
OUT = pathlib.Path("saves/budget_468_rec_out")
shutil.rmtree(OUT, ignore_errors=True)
r.session.record(folder=OUT)
wr.enter("parth")
wr.present, wr.residents = [herb2], [herb2]
stub.plan = [{"kind": "look"}]


def staged_turn(text):
    """The second line's understanding is cut by the deadline (the client raising a timeout); the first stands in for its passage."""
    CUT["on"] = SCRIPT == ["quit"]
    return real_turn(text)


real_turn = wr.turn
wr.turn = staged_turn
wr.run()
wr.turn = real_turn
r.close()
restore()
import gzip
calls = [json.loads(l) for l in gzip.open(OUT / "calls.jsonl.gz", "rt", encoding="utf-8") if l.strip()]
turns = [json.loads(l) for l in (OUT / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
meta = json.loads((OUT / "meta.json").read_text(encoding="utf-8"))
check("the recording's meta carries the speeds the budget priced its calls at, and each call its task", meta.get("profile") == {"read_tps": 1e9, "write_tps": 0.15}
      and meta.get("limit_seconds") == B["limit_seconds"] and all(c.get("task") for c in calls if c["kind"] == "chat"), (meta.get("profile"), [c.get("task") for c in calls][:6]))
cut = [c for c in calls if c.get("error")]
check("the deadline's cut is recorded as that error, with its task", cut and cut[-1]["error"][0] == "ReadTimeout" and cut[-1]["task"] == "interpret_action", [c.get("error") for c in cut])
check("...the first line's passage was refused under the slow profile and stood in for; the cut line was not taken", "stand_in" in [p["how"] for p in turns[0].get("presented", [])]
      and not any(c.get("task") == "narrate" for c in calls if c.get("input")) and len(turns) >= 2 and not turns[1].get("presented"),   # input 0 is the open's own passage
      ([[p["how"] for p in t.get("presented", [])] for t in turns], [(c.get("input"), c.get("task")) for c in calls]))
out = subprocess.run([sys.executable, "tools/rerun.py", str(OUT)], capture_output=True, text=True, timeout=600)
last = (out.stdout.strip().splitlines() or [""])[-1]
check("...and it replays in a child process, input by input, the budget priced as the recording's", out.returncode == 0 and last.startswith("all ") and "inputs matched" in last,
      (out.returncode, out.stdout[-400:], out.stderr[-400:]))
rows = [json.loads(l) for l in pathlib.Path("saves/budget_468_rec/turns.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
check("the turn log's rows carry the budget's measures: the estimate, the required path, the stand-ins; the cut line rolled back as the model's failure",
      rows and all("budget_seconds" in r_ and "required_seconds" in r_ for r_ in rows) and rows[0].get("stand_ins") == ["passage"]
      and all(r_["budget_seconds"] >= r_["required_seconds"] - 1 for r_ in rows) and rows[1].get("rolled_back") and rows[1].get("model_failed"),
      [{k: r_.get(k) for k in ("budget_seconds", "required_seconds", "stand_ins", "dropped", "rolled_back", "model_failed")} for r_ in rows])
shutil.rmtree(OUT, ignore_errors=True)
shutil.rmtree("saves/budget_468_rec", ignore_errors=True)
gateway._client = real

# ---- the stub's prompts estimate far under the minute on the measured card
check("the stub's own prompts (the understanding, a reply, a passage) estimate far under the owner's minute on the measured card",
      budget.estimate("interpret_action", 14500) < 10 and budget.estimate("npc_conversation", 22000) < 12 and budget.estimate("narrate", 8200) < 12
      and budget.PROFILE == MEASURED, (budget.estimate("interpret_action", 14500), budget.estimate("npc_conversation", 22000), budget.estimate("narrate", 8200)))
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
