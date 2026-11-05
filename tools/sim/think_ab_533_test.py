"""(f533) Thinking on and off, task by task: the game's switch for chosen tasks, and the tool that measures it (tools/think_ab.py).

- The switch: DND_THINK_TASKS names the tasks whose calls think; they ask for it, with THINK_ROOM more tokens to think in, and every
  other call goes as before (THINK). Off (the default), what is sent is exactly what was sent before.
- The tool, run against a local stand-in of both servers (an Ollama /api/chat and a llama-server /v1/chat/completions on 127.0.0.1):
  the first tries of the chosen tasks in the kept recordings are sent with thinking off and on, in turn, the order alternating; Ollama
  is asked with its `think`, the call's own options (the machine's threads left out) and more room to think; llama-server with the
  template's switch, the schema as its JSON grammar and every sampler (the game's table under the call's own values). Each answer is
  scored: valid by the game's contract, its decision against the night's, leaked thinking caught, timed, with what it would take on
  the minimum card; the summary is written per server, task and setting, with the servers' raw field names kept to learn them.
- The game's own evaluations are run with the switch off and then on, against the Ollama server named, and their scores read.

Run: python tools/sim/think_ab_533_test.py"""

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
    "from engine import recording",
    "R = create_model('R', x=(str, ''))",
    "out = {}",
    "for task in ('ruling', 'narrate', 'interpret_action'):",
    "    k = backend.ollama_kwargs(backend.ChatRequest(messages=[{'role': 'user', 'content': 'x'}], schema=R, sampling=sampling.resolve(task, 0.3).at(0), max_tokens=200))",
    "    out[task] = {'think': k['think'], 'num_predict': k['options']['num_predict'], 'keys': list(k)}",
    "out['room'] = config.THINK_ROOM",
    "print(json.dumps(out))",
])


def child(env_add: dict) -> dict:
    env = dict(os.environ, PYTHONPATH=str(ROOT), MERAVIA_NO_SERVER="1")
    env.pop("DND_THINK_TASKS", None)
    env.update(env_add)
    r = subprocess.run([sys.executable, "-c", CHILD], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    return json.loads(r.stdout.strip().splitlines()[-1])


off = child({})
on = child({"DND_THINK_TASKS": "ruling,interpret_action"})
check("off (the default), every call goes as before: no thinking, the answer's own ceiling",
      all(off[t]["think"] is False and off[t]["num_predict"] == 200 for t in ("ruling", "narrate", "interpret_action")), off)
check("named in DND_THINK_TASKS, a task's calls think, with THINK_ROOM more tokens to think in", on["ruling"]["think"] is True
      and on["ruling"]["num_predict"] == 200 + on["room"] and on["interpret_action"]["think"] is True, on)
check("...while every other task's calls are as before, the arguments in the same order", on["narrate"]["think"] is False
      and on["narrate"]["num_predict"] == 200 and on["narrate"]["keys"] == off["narrate"]["keys"], on["narrate"])

# ---- 2. the tool, against a stand-in of both servers
SEEN = {"ollama": [], "llama": []}
STUB = simlib.Stub("warrior", 33)            # the suite's stand-in model writes each answer, as it would for the game


def answer(schema: dict, messages: list) -> str:
    try:
        return STUB.chat(format=schema, messages=messages).message.content
    except Exception:                         # a handler that needs a night bot (a fight's reading): the schema's own shape instead
        return json.dumps(simlib._fill(schema, schema))


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        if self.path == "/api/chat":
            SEEN["ollama"].append(body)
            content = answer(body["format"], body["messages"])
            think = body.get("think")
            resp = {"model": body["model"], "message": {"role": "assistant", "content": content, **({"thinking": "I weigh it. " * 20} if think else {})},
                    "done": True, "done_reason": "stop", "prompt_eval_count": 1000, "eval_count": 40 + (120 if think else 0),
                    "total_duration": 2_500_000_000}
        elif self.path == "/v1/chat/completions":
            SEEN["llama"].append(body)
            content = answer(body["response_format"]["json_schema"]["schema"], body["messages"])
            think = body["chat_template_kwargs"]["enable_thinking"]
            if think and body["response_format"]["json_schema"]["name"] == "Ruling":
                content = "<think>is it plausible?</think>" + content                # the risk: thinking inside the answer
            resp = {"choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content,
                                                                                    **({"reasoning_content": "Hmm. " * 30} if think else {})}}],
                    "usage": {"prompt_tokens": 1000, "completion_tokens": 40 + (120 if think else 0)},
                    "timings": {"prompt_n": 1000, "prompt_ms": 400.0, "predicted_n": 40, "predicted_ms": 900.0}}
        else:
            self.send_response(404)
            self.end_headers()
            return
        data = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_address[1]}"
OUT = Path("saves/think_ab_533")
shutil.rmtree(OUT, ignore_errors=True)
import contextlib
import io
said = io.StringIO()
with contextlib.redirect_stdout(said):
    rc = think_ab.main(["--recordings", "data/replay/sessions", "--server", f"ollama={url}", "--server", f"llama={url}", "--per-task", "3",
                        "--out", str(OUT)])
server.shutdown()
results = [json.loads(l) for l in (OUT / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
chosen = think_ab.pick(think_ab.recorded_rows(Path("data/replay/sessions")), think_ab.TASKS, 3)
n_rows = sum(len(rs) for rs in chosen.values())
check("the tool sends every chosen first try to each server with thinking off and on", rc == 0 and len(results) == 2 * 2 * n_rows
      and n_rows >= 8, (rc, len(results), n_rows))
check("...each request once off and once on, the order alternating so neither always finds the prompt cached",
      [r["think"] for r in results if r["server"] == "ollama"][:4] == [False, True, True, False], [r["think"] for r in results][:4])
o = [b for b in SEEN["ollama"][1:]]                                       # the first is the warm-up
check("Ollama is asked with its think switch, the schema, the call's own options without the machine's threads, and more room to think",
      all("think" in b and "format" in b and "num_thread" not in b["options"] for b in o)
      and any(b["think"] for b in o) and any(not b["think"] for b in o)
      and all(b["options"]["num_predict"] - 1024 == next(x for x in o if x["messages"] == b["messages"] and not x["think"])["options"]["num_predict"]
              for b in o if b["think"]), o[:1])
l_ = SEEN["llama"][1:]
check("llama-server is asked with the template's switch, the schema as its JSON grammar, and every sampler (the game's table under the call's)",
      all("chat_template_kwargs" in b and b["response_format"]["type"] == "json_schema" and b.get("top_k") == 64 and b.get("min_p") == 0.0
          and "temperature" in b for b in l_) and any(b["chat_template_kwargs"]["enable_thinking"] for b in l_), l_[:1])
first_ollama = next(r for r in results if r["server"] == "ollama" and "raw_fields" in r)
first_llama = next(r for r in results if r["server"] == "llama" and "raw_fields" in r)
check("...and the servers' raw field names are kept, to learn them on the pod (the timings among them)",
      "timing_fields" in first_llama["raw_fields"] and "prompt_ms" in first_llama["raw_fields"]["timing_fields"]
      and "message_fields" in first_ollama["raw_fields"], (first_ollama["raw_fields"], first_llama["raw_fields"]))
valid_off = [r for r in results if not r["think"]]
check("each answer is scored by the game's contract: an answer of the schema's shape is valid", all(r["valid"] for r in valid_off),
      [r for r in valid_off if not r["valid"]][:2])
leaks = [r for r in results if r["leaked"]]
check("...thinking inside the answer is caught as leaked, and is no valid answer",
      leaks and all(r["server"] == "llama" and r["title"] == "Ruling" and r["think"] and not r["valid"] for r in leaks), leaks[:2])
check("...its decision is set against the night's where it has one, and not for the audit's free-text reading",
      all(isinstance(r["agree"], bool) for r in results if r["title"] in ("ActionPlan", "CombatIntent", "AuditVerdict") and r["parsed"])
      and all(r["agree"] is None for r in results if r["title"] == "AuditMeaning"), [(r["title"], r["agree"]) for r in results][:6])
card = think_ab.profile()
want = round(1000 / card["prompt_tokens_per_second"] + 160 / card["answer_tokens_per_second"], 2)
check("...with what the call would take on the minimum card, the thinking written at the answer's speed",
      any(r["card_seconds"] == want and r["think"] for r in results if r["server"] == "ollama"), (want, [r["card_seconds"] for r in results][:4]))
check("...and the thinking measured", all(r["thinking_chars"] > 0 for r in results if r["think"])
      and all(r["thinking_chars"] == 0 for r in results if not r["think"]))
summary = json.loads((OUT / "summary.json").read_text(encoding="utf-8"))
keys = {(c["server"], c["task"], c["think"]) for c in summary["calls"]}
check("the summary is a row per server, task and setting, in summary.json and as a table in summary.md",
      len(keys) == 2 * 2 * sum(1 for rs in chosen.values() if rs) and "| server | task | thinking |" in (OUT / "summary.md").read_text(encoding="utf-8"),
      sorted(keys)[:4])
ruling_on = next(c for c in summary["calls"] if c["server"] == "llama" and c["task"] == "ruling" and c["think"] == "on")
check("...counting what leaked", ruling_on["leaked"] == ruling_on["n"] and ruling_on["valid_pct"] == 0.0, ruling_on)

# ---- 3. the game's own evaluations, the switch off and then on
ran = []
real_run = think_ab.subprocess.run


def fake_run(cmd, cwd=None, env=None, capture_output=None, text=None, timeout=None):
    ran.append({"cmd": cmd, "think": env.get("DND_THINK_TASKS"), "host": env.get("OLLAMA_HOST"), "switch": env.get("MERAVIA_NO_SERVER")})
    out = "\n41/50 right; intercepts took 0 line(s)" if "interp_eval.py" in " ".join(cmd) else "\n17 of 19 right"
    return subprocess.CompletedProcess(cmd, 0, out, "")


think_ab.subprocess.run = fake_run
try:
    ev = think_ab.evals("http://127.0.0.1:11434", ["ruling", "interpret_action"])
finally:
    think_ab.subprocess.run = real_run
check("the evaluations run live against the Ollama server named, thinking off and then on for the chosen tasks, and their scores are read",
      [(e["eval"], e["think"], e["right"], e["of"]) for e in ev] == [("interp_eval", "off", 41, 50), ("ruling_eval", "off", 17, 19),
                                                                   ("interp_eval", "on", 41, 50), ("ruling_eval", "on", 17, 19)]
      and [r["think"] for r in ran] == ["", "", "ruling,interpret_action", "ruling,interpret_action"]
      and all(r["host"] == "127.0.0.1:11434" and r["switch"] is None and "--live" in r["cmd"] for r in ran), (ev, ran))

shutil.rmtree(OUT, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
