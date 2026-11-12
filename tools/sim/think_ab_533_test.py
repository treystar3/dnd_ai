"""(f533) Thinking on and off, task by task: the game's switch for chosen tasks, and the tool that measures it (tools/think_ab.py).

- The switch: DND_THINK_TASKS names the tasks whose calls think; they ask for it, with THINK_ROOM more tokens to think in, and every
  other call goes as before (THINK). Off (the default), what is sent is exactly what was sent before. A name the game does not call is
  refused at startup (engine/data_check.py); a thinking try is charged for its thinking, and one whose thinking used all the room ends
  the tries with that reason (the cut-off retry would only think as long again). A replay asks as its recording did, whatever the
  shell says, and the suite never takes the game's settings from the shell that ran it.
- The tool, run against a local stand-in of llama-server (/v1/chat/completions on 127.0.0.1): the first tries of the chosen tasks in
  the kept recordings are sent with thinking off and on, in turn, the order alternating; the server
  is asked with its `think`, the call's own options and more room to think; llama-server with the template's switch, the schema as its
  JSON grammar and every sampler (the game's table under the call's own values). Each answer is scored: valid by the game's contract
  (the ruling's own context too), its decision against the night's, leaked thinking caught, timed, with what it would take on the
  minimum card; every rate is over all the calls, so a setting that fails more is not flattered. A server still loading is waited for,
  one that keeps failing is left, and the summary is written as the run goes, so a stop keeps what was measured.
- The game's own evaluations are run with the switch off and then on, on the llama-server named, with the same room, and their
  scores read out of every case (a ruling not given counts as wrong; interp_eval goes on past a case the model failed).

Run: python tools/sim/think_ab_533_test.py"""

import gzip
import json
import os
import shutil
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
os.chdir(ROOT)

import simlib
import think_ab

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


# ---- 1. the game's switch, in processes of their own (it is read from the environment once)
CHILD = "\n".join([
    "import json, sys",
    "sys.path.insert(0, '.')",
    "from pydantic import create_model",
    "import config",
    "from llm import backend, sampling",
    "R = create_model('R', x=(str, ''))",
    "out = {}",
    "for task in ('ruling', 'narrate', 'interpret_action'):",
    "    k = backend.legacy_kwargs(backend.ChatRequest(messages=[{'role': 'user', 'content': 'x'}], schema=R, sampling=sampling.resolve(task, 0.3).at(0), max_tokens=200))",
    "    out[task] = {'think': k['think'], 'num_predict': k['options']['num_predict'], 'keys': list(k)}",
    "out['room'] = config.THINK_ROOM",
    "from engine import data_check",
    "out['problems'] = [p for p in data_check.budget_problems() if 'THINK' in p]",
    "print(json.dumps(out))",
])


def child(code: str, env_add: dict) -> dict:
    env = dict(os.environ, PYTHONPATH=str(ROOT), MERAVIA_NO_SERVER="1")
    for k in [k for k in env if k.startswith("DND_")]:
        env.pop(k)
    env.update(env_add)
    r = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (r.stdout + r.stderr)[-1500:]}


off = child(CHILD, {})
on = child(CHILD, {"DND_THINK_TASKS": "ruling,interpret_action"})
check("off (the default), every call goes as before: no thinking, the answer's own ceiling",
      all(off[t]["think"] is False and off[t]["num_predict"] == 200 for t in ("ruling", "narrate", "interpret_action"))
      and off["problems"] == [], off)
check("named in DND_THINK_TASKS, a task's calls think, with THINK_ROOM more tokens to think in", on["ruling"]["think"] is True
      and on["ruling"]["num_predict"] == 200 + on["room"] and on["room"] == 8192 and on["interpret_action"]["think"] is True
      and on["problems"] == [], on)
check("...while every other task's calls are as before, the arguments in the same order", on["narrate"]["think"] is False
      and on["narrate"]["num_predict"] == 200 and on["narrate"]["keys"] == off["narrate"]["keys"], on["narrate"])
none = child(CHILD, {"DND_THINK_TASKS": "ruling", "DND_THINK_ROOM": "0"})
typo = child(CHILD, {"DND_THINK_TASKS": "interpret,ruling"})
check("an explicit DND_THINK_ROOM=0 is no room, and a name the game does not call is refused at startup, never thinking nowhere",
      none.get("room") == 0 and none["ruling"]["num_predict"] == 200
      and len(typo.get("problems", [])) == 1 and "interpret" in typo["problems"][0], (none.get("room"), typo.get("problems")))

GATE = "\n".join([
    "import json, sys, types",
    "sys.path.insert(0, '.')",
    "from llm import backend, gateway",
    "from llm.contracts import Ruling",
    "from engine import budget",
    "charged = []",
    "real = budget.charge",
    "budget.charge = lambda task, p, a=None, c=0.0: charged.append([task, p, a]) or 0.0",   # (f538) the reused share is the fourth
    "MODE = sys.argv[1]",
    "def chat(**k):",
    "    if MODE == 'overrun':",
    "        msg = types.SimpleNamespace(content='', thinking='I weigh it. ' * 400)",
    "        return types.SimpleNamespace(message=msg, done_reason='length', usage={'prompt': 900, 'out': 1524})",
    "    msg = types.SimpleNamespace(content='{\"sense\": \"yes\", \"why\": \"it can be done\"}', thinking='Hmm. ' * 100)",
    "    return types.SimpleNamespace(message=msg, done_reason='stop', usage={'prompt': 900, 'out': 300})",
    "src = backend.StandIn(chat=chat, name='thinker')",
    "undo = backend.use(src)",
    "try:",
    "    gateway.generate('ruling', 'Rule.', 'I climb the wall.', Ruling, temperature=0.3, max_tokens=500,",
    "                     relaxed_context={} if MODE == 'overrun' else None)",
    "    err = ''",
    "except gateway.LLMError as e:",
    "    err = str(e) + ' <- ' + str(e.__cause__)",
    "undo()",
    "print(json.dumps({'tries': src.calls['Ruling'], 'err': err, 'charged': charged, 'cpt': budget.B.get('chars_per_token')}))",
])
env_g = {"DND_THINK_TASKS": "ruling"}


def gate(mode: str, env_add: dict) -> dict:
    env = dict(os.environ, PYTHONPATH=str(ROOT), MERAVIA_NO_SERVER="1")
    for k in [k for k in env if k.startswith("DND_")]:
        env.pop(k)
    env.update(env_add)
    r = subprocess.run([sys.executable, "-c", GATE, mode], cwd=ROOT, env=env, capture_output=True, text=True, timeout=300)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (r.stdout + r.stderr)[-1500:]}


over = gate("overrun", env_g)
check("a thinking try whose thinking used all its room ends the tries at once, the reason named (no 'keep every field short' retry, "
      "nor the relaxed retry, which would think as long again)",
      over.get("tries") == 1 and "thinking used all the room" in over.get("err", ""), over)
check("...and it is charged for what it wrote, thinking and all (the server's own count, as a replay has it recorded)",
      over.get("charged") and over["charged"][0][2] == int(1524 * float(over["cpt"])), over.get("charged"))
plain = gate("answer", {})
check("unthinking, the same answer is charged as before: its own characters",
      plain.get("charged") and plain["charged"][0][2] == len('{"sense": "yes", "why": "it can be done"}'), plain)

genv = dict(os.environ, PYTHONPATH=str(ROOT), MERAVIA_NO_SERVER="1", DND_THINK_TASKS="interpret_action,audit_compare")
g = subprocess.run([sys.executable, "tools/rerun.py", "--golden"], cwd=ROOT, env=genv, capture_output=True, text=True, timeout=600)
check("a replay asks as its recording did: the kept recording still replays whole with DND_THINK_TASKS set in the shell",
      g.returncode == 0, (g.stdout + g.stderr)[-600:])
suite_src = (ROOT / "tools/run_suite.py").read_text(encoding="utf-8")
check("...and the suite takes none of the game's DND_ settings from the shell that ran it", 'k.startswith("DND_")' in suite_src)

# ---- 2. the tool, against a stand-in of llama-server
SEEN = {"llama": []}
STUB = simlib.Stub("warrior", 33)            # the suite's stand-in model writes each answer, as it would for the game
MODE = {"loading": 0}


def answer(schema: dict, messages: list) -> str:
    try:
        return STUB.chat(format=schema, messages=messages).message.content
    except Exception:                         # a handler that needs a night bot (a fight's reading): the schema's own shape instead
        return json.dumps(simlib._fill(schema, schema))


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/props":
            return self.reply(200, {"build_info": "b-test", "total_slots": 1, "default_generation_settings": {"n_ctx": 32768}})
        return self.reply(404, {"error": "no"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        if MODE["loading"] > 0:
            MODE["loading"] -= 1
            return self.reply(503, {"error": {"message": "Loading model", "code": 503}})
        if self.path == "/v1/chat/completions":
            SEEN["llama"].append(body)
            name = body["grammar"].splitlines()[0].split()[2]           # (f527) "# Meravia <Title> <sha>": the grammar names its contract
            from llm import contracts as _contracts
            content = answer(getattr(_contracts, name).model_json_schema(), body["messages"])
            think = body["chat_template_kwargs"]["enable_thinking"]
            if think and name == "ActRuling":
                content = "<think>is it plausible?</think>" + content                # the risk: thinking inside the answer
            resp = {"choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content,
                                                                                    **({"reasoning_content": "Hmm. " * 30} if think else {})}}],
                    "usage": {"prompt_tokens": 1000, "completion_tokens": 40 + (120 if think else 0)},
                    "timings": {"prompt_n": 1000, "prompt_ms": 400.0, "predicted_n": 40, "predicted_ms": 900.0}}
        else:
            return self.reply(404, {"error": "no route"})
        self.reply(200, resp)


server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_address[1]}"
OUT = Path("saves/think_ab_533")
shutil.rmtree(OUT, ignore_errors=True)
import contextlib
import io
think_ab.READY_POLL = 0.05
MODE["loading"] = 3                           # the server is still loading the model: three answers of 503 before the first 200
said = io.StringIO()
with contextlib.redirect_stdout(said):
    rc = think_ab.main(["--recordings", "data/replay/sessions", "--server", f"llama={url}", "--per-task", "3", "--out", str(OUT)])
results = [json.loads(l) for l in (OUT / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
chosen = think_ab.pick(think_ab.recorded_rows(Path("data/replay/sessions")), think_ab.TASKS, 3)
n_rows = sum(len(rs) for rs in chosen.values())
check("a server still loading is waited for (its 503s are not answers), then every chosen first try goes to the server, off and on",
      rc == 0 and MODE["loading"] == 0 and len(results) == 2 * n_rows and n_rows >= 8 and all(r["status"] == 200 for r in results),
      (rc, len(results), n_rows, said.getvalue()[-400:]))
check("...each request once off and once on, the order alternating so neither always finds the prompt cached",
      [r["think"] for r in results if r["server"] == "llama"][:4] == [False, True, True, False], [r["think"] for r in results][:4])
l_ = SEEN["llama"][1:]                                                    # the first is the warm-up
check("a thinking call is given more room than the same call unthinking, and only then",
      all(r["room"] > 0 for r in results if r["think"]) and all(r["room"] == 0 for r in results if not r["think"])
      and all(b["max_tokens"] > next(x for x in l_ if x["messages"] == b["messages"] and not x["chat_template_kwargs"]["enable_thinking"])["max_tokens"]
              for b in l_ if b["chat_template_kwargs"]["enable_thinking"]), l_[:1])
check("llama-server is asked with the template's switch, the schema as its grammar (f527), and every sampler (the game's table under the call's)",
      all("chat_template_kwargs" in b and b["grammar"].startswith("# Meravia ") and "response_format" not in b and b.get("top_k") == 64 and b.get("min_p") == 0.0
          and "temperature" in b for b in l_) and any(b["chat_template_kwargs"]["enable_thinking"] for b in l_), l_[:1])
first_llama = next(r for r in results if r["server"] == "llama" and "raw_fields" in r)
check("...and the server's raw field names are kept, to learn them on the pod (the timings among them)",
      "timing_fields" in first_llama["raw_fields"] and "prompt_ms" in first_llama["raw_fields"]["timing_fields"]
      and "message_fields" in first_llama["raw_fields"], first_llama["raw_fields"])
valid_off = [r for r in results if not r["think"]]
check("each answer is scored by the game's contract: an answer of the schema's shape is valid", all(r["valid"] for r in valid_off),
      [r for r in valid_off if not r["valid"]][:2])
leaks = [r for r in results if r["leaked"]]
check("...thinking inside the answer is caught as leaked, and is no valid answer, and decides nothing",
      leaks and all(r["server"] == "llama" and r["title"] == "ActRuling" and r["think"] and not r["valid"] and r["agree"] is None for r in leaks),
      leaks[:2])
check("...its decision is set against the night's where it has one and the answer is valid, and not for the audit's free-text reading",
      all(isinstance(r["agree"], bool) for r in results if r["title"] in ("ActionPlan", "CombatIntent", "AuditVerdict") and r["valid"])
      and all(r["agree"] is None for r in results if r["title"] == "AuditMeaning"), [(r["title"], r["agree"]) for r in results][:6])
card = think_ab.profile()
want = round(1000 / card["prompt_tokens_per_second"] + 160 / card["answer_tokens_per_second"], 2)
check("...with what the call would take on the minimum card, the thinking written at the answer's speed",
      any(r["card_seconds"] == want and r["think"] for r in results if r["server"] == "llama")
      and think_ab.card_seconds(None, 40, card) is None, (want, [r["card_seconds"] for r in results][:4]))
check("...and the thinking measured", all(r["thinking_chars"] > 0 for r in results if r["think"])
      and all(r["thinking_chars"] == 0 for r in results if not r["think"]))
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
keys = {(c["server"], c["task"], c["think"]) for c in summary["calls"]}
md = (OUT / "summary.md").read_text(encoding="utf-8")
check("the summary is a row per server, task and setting, in summary.json and as a table in summary.md, with the server's own facts",
      len(keys) == 2 * sum(1 for rs in chosen.values() if rs) and "| server | task | thinking |" in md
      and summary["meta"]["servers_about"]["llama"]["build_info"] == "b-test", (sorted(keys)[:4], summary["meta"].get("servers_about")))
ruling_on = next(c for c in summary["calls"] if c["server"] == "llama" and c["task"] == "act_ruling" and c["think"] == "on")
ruling_off = next(c for c in summary["calls"] if c["server"] == "llama" and c["task"] == "act_ruling" and c["think"] == "off")
check("...counting what leaked, every rate over all the calls: an answer that leaked agrees with nothing",
      ruling_on["leaked"] == ruling_on["n"] and ruling_on["valid_pct"] == 0.0 and ruling_on["agree_pct"] == 0.0
      and ruling_on["agree_valid_pct"] is None and ruling_on["thought"] == ruling_on["n"] and ruling_off["agree_pct"] is not None, ruling_on)
fake_rows = [{"server": "x", "task": "ruling", "title": "Ruling", "think": t, "status": 200, "valid": v, "parsed": v, "agree": a, "leaked": False,
              "cut": not v, "seconds": 1.0, "answer_tokens": 10, "thinking_chars": 5 if t else 0, "card_seconds": 1.0}
             for t, v, a in [(False, True, True)] * 8 + [(False, True, False)] * 2 + [(True, True, True)] * 4 + [(True, False, None)] * 6]
fs = {c["think"]: c for c in think_ab.summarise(fake_rows)}
check("...so a setting that cuts off more cannot look as if it agreed more (off 8 of 10; on 4 of 10, the 4 valid all agreeing)",
      fs["off"]["agree_pct"] == 80.0 and fs["on"]["agree_pct"] == 40.0 and fs["on"]["agree_valid_pct"] == 100.0, fs)

# the arguments that would waste a paid hour are refused before anything is sent
def refused(argv) -> bool:
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            think_ab.main(argv)
        return False
    except SystemExit as e:
        return e.code == 2


base = ["--recordings", "data/replay/sessions", "--server", f"llama={url}"]
check("a task name the tool does not measure, a kind named twice, a missing case file, a --model the evaluations cannot play, and a run over "
      "results already there are each refused before anything is sent",
      refused(base + ["--tasks", "interpret", "--out", str(OUT / "a")]) and refused(base + ["--server", f"llama={url}", "--out", str(OUT / "b")])
      and refused(base + ["--evals", "--corpus", "data/replay/nothing.yaml", "--out", str(OUT / "c")])
      and refused(base + ["--evals", "--model", "another:1b", "--out", str(OUT / "d")]) and refused(base + ["--out", str(OUT)]))
empty = OUT / "empty"
empty.mkdir(parents=True, exist_ok=True)
(empty / "results.jsonl").write_text("", encoding="utf-8")
with contextlib.redirect_stdout(io.StringIO()):
    rc_empty = think_ab.main(base + ["--tasks", "act_ruling", "--per-task", "1", "--out", str(empty)])
check("...while a results file a run left empty (it measured nothing) is no reason to refuse", rc_empty == 0
      and (empty / "results.jsonl").read_text(encoding="utf-8").strip() != "", rc_empty)
(OUT / "summary.md").unlink()
with contextlib.redirect_stdout(io.StringIO()):
    rc2 = think_ab.main(["--summarise", "--out", str(OUT)])
check("...and --summarise rebuilds the summary from the results already measured", rc2 == 0 and (OUT / "summary.md").exists())

SEEN["llama"].clear()
about: dict = {}
with contextlib.redirect_stdout(io.StringIO()):
    # the warm-up is answered, then the runner falls over: the server is left after give_up failures, its rows not burnt
    calls = {"n": 0}
    real_post = think_ab.post

    def flaky(u, body, timeout):
        calls["n"] += 1
        if calls["n"] > 1:
            return 500, {"error": "the runner fell over"}, 0.01
        return real_post(u, body, timeout)

    think_ab.post = flaky
    try:
        failing = think_ab.measure(chosen, [("llama", url)], ready_wait=1, give_up=5, about=about)
    finally:
        think_ab.post = real_post
check("a server that keeps failing is left after five failures in a row, and the summary says so, rather than burning every row",
      len(failing) == 5 and "stopped" in about.get("llama", {}), (len(failing), about))
with contextlib.redirect_stdout(io.StringIO()):
    MODE["loading"] = 10 ** 6
    never: dict = {}
    nothing = think_ab.measure(chosen, [("llama", url)], ready_wait=0.2, about=never)
    MODE["loading"] = 0
check("...and one that never becomes ready is skipped, nothing measured against it", nothing == [] and "skipped" in never.get("llama", {}), never)
server.shutdown()

# what the recordings give
tmp = OUT / "cut_rec"
tmp.mkdir(parents=True, exist_ok=True)
src_rows = [r for r in think_ab.recorded_rows(Path("data/replay/sessions/stub_short"))][:30]
blob = gzip.compress("".join(json.dumps({k: v for k, v in r.items() if k != "_from"}) + "\n" for r in src_rows).encode())
(tmp / "calls.jsonl.gz").write_bytes(blob[: len(blob) * 2 // 3])                # a run killed mid-night: the file has no end
think_ab.WARNINGS.clear()
kept = list(think_ab.recorded_rows(tmp))
check("a recording cut off mid-night gives the rows before the cut and says so, rather than ending the run",
      0 < len(kept) < 30 and len(think_ab.WARNINGS) == 1 and "cut off" in think_ab.WARNINGS[0], (len(kept), think_ab.WARNINGS))
rows_all = list(think_ab.recorded_rows(Path("data/replay/sessions")))
alone = think_ab.pick(rows_all, ["act_ruling"], 2)["act_ruling"]
among = think_ab.pick(rows_all, list(think_ab.TASKS), 2)["act_ruling"]
check("each task's sample is its own, the same whatever other tasks are chosen with it", [r["req"] for r in alone] == [r["req"] for r in among]
      and alone, ([r.get("i") for r in alone], [r.get("i") for r in among]))
same = {"messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], "options": {"temperature": 0.2}}
synthetic = [dict(kind="chat", task="ruling", title="Ruling", request=same, answer='{"sense": "yes"}', i=1, _from="f"),
             dict(kind="chat", task="ruling", title="Ruling", request=same, answer='{"sense": "yes"}', i=2, _from="f"),
             dict(kind="chat", task="ruling", title="Ruling", request=same, error=["ResponseError", "500"], i=3, _from="f"),
             dict(kind="chat", task="ruling", title="Ruling", request=same, answer='{"sense": "no"}', i=4, _from="f")]
think_ab.SKIPPED.clear()
kept_i = [r["i"] for r in think_ab.pick(synthetic, ["ruling"], 10)["ruling"]]
check("the same request answered twice is two first tries; only the one straight after a failed try is its retry, and left out",
      kept_i == [1, 2] and think_ab.SKIPPED == {"a retry after a server error": 1}, (kept_i, think_ab.SKIPPED))
decide = think_ab.DECISION["CombatIntent"]
check("a fight's reading agrees only when the whole move does: the way it moves, the item, the approach, whom it heals ('' and self alike)",
      decide({"kind": "move", "move": "back"}) != decide({"kind": "move", "move": "closer"})
      and decide({"kind": "ability", "ability": "heal", "buff_for": "self"}) == decide({"kind": "ability", "ability": "heal", "buff_for": ""})
      and decide({"kind": "talk", "approach": "persuade"}) != decide({"kind": "talk", "approach": "intimidate"}))
check("...and a ruling is held to the game's own context: a capability the game does not have is refused",
      think_ab.score("Ruling", json.dumps({"sense": "yes", "requires": ["flight_of_fancy"]}), "{}")["valid"] is False)
asked = {"messages": [{"role": "system", "content": "uses: the codes from TARGETS"},
                      {"role": "user", "content": "SCENE\nTARGETS (what the act can name, by code):\n  f1 the gate (feature)\n  p1 a guard (person)\nCHANGES"}]}
on_gate = json.dumps({"sense": "yes", "uses": ["f1"]})
check("...and an act's ruling to the codes its own request listed (f603): a code the request never gave is refused",
      think_ab.codes_of(asked) == ["f1", "p1"] and think_ab.score("ActRuling", on_gate, "{}", asked)["valid"] is True
      and think_ab.score("ActRuling", json.dumps({"sense": "yes", "uses": ["f9"]}), "{}", asked)["valid"] is False,
      (think_ab.codes_of(asked), think_ab.score("ActRuling", on_gate, "{}", asked)))

# ---- 3. the game's own evaluations, the switch off and then on
ran = []
real_run = think_ab.subprocess.run


def fake_run(cmd, cwd=None, env=None, capture_output=None, text=None, timeout=None):
    ran.append({"cmd": cmd, "think": env.get("DND_THINK_TASKS"), "host": env.get("DND_LLAMA_URL"), "switch": env.get("MERAVIA_NO_SERVER"),
                "room": env.get("DND_THINK_ROOM"), "backend": env.get("DND_BACKEND")})
    if "interp_eval.py" in " ".join(cmd):
        if env.get("DND_THINK_TASKS"):
            raise subprocess.TimeoutExpired(cmd, timeout, output=b"ok   a\nok   b\n")
        return subprocess.CompletedProcess(cmd, 0, "\n41/50 right; intercepts took 0 line(s)", "")
    return subprocess.CompletedProcess(cmd, 0, "\n17 of 19 right" + ("; 3 with no ruling" if env.get("DND_THINK_TASKS") else ""), "")


think_ab.subprocess.run = fake_run
seen_done = []
try:
    ev = think_ab.evals("http://127.0.0.1:11434", ["ruling", "interpret_action"], room=1536, corpus="data/replay/interp_cases.yaml",
                        folder=OUT, done=lambda rows: seen_done.append(len(rows)))
finally:
    think_ab.subprocess.run = real_run
check("the evaluations run live on the llama-server named (DND_BACKEND=llama at its URL, f529), thinking off and then on with the same "
      "room, and their scores are read out of every case: a ruling not given is a wrong one",
      [(e["eval"], e["think"], e["right"], e["of"], e["no_answer"]) for e in ev] == [
          ("interp_eval", "off", 41, 50, 0), ("ruling_eval", "off", 17, 19, 0), ("interp_eval", "on", None, None, None), ("ruling_eval", "on", 17, 22, 3)]
      and [r["think"] for r in ran] == ["", "", "ruling,interpret_action", "ruling,interpret_action"]
      and all(r["host"] == "http://127.0.0.1:11434" and r["backend"] == "llama" and r["switch"] is None and "--live" in r["cmd"]
              and r["room"] == "1536" for r in ran)
      and "data/replay/interp_cases.yaml" in ran[0]["cmd"], (ev, ran))
check("...an evaluation that runs out of time is a row of its own (the others still run), its output kept, and the summary rewritten "
      "after each", ev[2]["rc"] == "timeout" and (OUT / "eval_interp_eval_on.log").read_text(encoding="utf-8").startswith("ok   a")
      and seen_done == [1, 2, 3, 4], (ev[2], seen_done))

import latency
night = OUT / "night_run"
night.mkdir(parents=True, exist_ok=True)


def head_of(sampling: dict) -> str:
    (night / "run.json").write_text(json.dumps({"character": "A", "class": "warrior", "model": "m", "sampling": sampling}), encoding="utf-8")
    return latency.summarise(night).splitlines()[2]


base_night = head_of({"temp_add": 0, "repeat_add": 0, "think_tasks": [], "think_room": 1024})
thinking_night = head_of({"temp_add": 0, "repeat_add": 0, "think_tasks": ["ruling"], "think_room": 1024})
warm_night = head_of({"temp_add": 0.15, "repeat_add": 0.1, "think_tasks": [], "think_room": 1024})
check("a night's summary says when it thought, and calls a base-voice night neither warm nor thinking",
      "warm" not in base_night and "thinking" not in base_night and "thinking on for ruling (+1024 tokens)" in thinking_night
      and "warm calls +0.15 temperature" in warm_night, (base_night, thinking_night, warm_night))

import interp_eval
from llm.errors import LLMError


class FailingBench:
    def __init__(self, live=False, save=None, source=None):     # (f529) the server's source a live bench is given
        self.n = 0

    def run(self, case):
        self.n += 1
        if self.n == 2:
            raise LLMError("interpret_action: no valid response after 3 attempts")
        return {"handled_by": "interpret", "kinds": ["look"], "first": {}, "steps": [], "moves": [], "talked": [], "hire": [],
                "repairs": [], "read": None}


real_bench = interp_eval.Bench
interp_eval.Bench = FailingBench
try:
    cases = [{"name": f"c{i}", "text": "look", "expect": {"handled_by": "interpret", "kinds": ["look"]}} for i in range(3)]
    with contextlib.redirect_stdout(io.StringIO()) as printed:
        got_ev = interp_eval.evaluate(cases, live=True)
finally:
    interp_eval.Bench = real_bench
check("interp_eval goes on past a case the model failed every try: it is a wrong case, named, and the score line still comes",
      got_ev["right"] == 2 and got_ev["wrong"] == ["c1"] and got_ev["model_failed"] == 1 and got_ev["intercept_took_wrongly"] == 0
      and "2/3 right" in printed.getvalue(), (got_ev, printed.getvalue()[-300:]))

shutil.rmtree(OUT, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
