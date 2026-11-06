"""(f534) Thinking with room to finish, and the measures for the improvised, the road and the big events.

- The room is raised (THINK_ROOM 8,192) and never more than the context holds: a thinking call is given its room only as far as the
  context has space beside its prompt and its answer, in the game (llm/backend.py think_room) and in tools/think_ab.py (room_for, from
  the server's own count of the prompt as the night recorded it). --num-ctx gives every replayed call a larger context.
- Road events are measured like the judgment calls, with nothing to agree with (a scene is written, not decided): each answer's text
  and the head and tail of its thinking are kept, to be read.
- The evaluations are chosen by name: the interpreter's, the ruling's, the ruling's improvised actions of several steps
  (data/replay/ruling_cases_complex.yaml) and the events' (tools/event_eval.py, the model writing the campaigns and cataclysms); each
  must have one of its tasks chosen to think; the context goes to them too; and the interpreter's 'no usable reading' is counted.
- tools/interp_eval.py clears a question the last case left open, so the next case is read for itself.

Run: python tools/sim/thinking_room_534_test.py"""

import contextlib
import gzip
import io
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
import yaml

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


# ---- 1. the game's room: raised, and within the context
CHILD = "\n".join([
    "import json, sys",
    "sys.path.insert(0, '.')",
    "from pydantic import create_model",
    "import config",
    "from llm import backend, sampling",
    "R = create_model('R', x=(str, ''))",
    "out = {'room': config.THINK_ROOM, 'ctx': config.NUM_CTX}",
    "for name, chars in (('short', 10), ('long', 6000)):",
    "    k = backend.legacy_kwargs(backend.ChatRequest(messages=[{'role': 'user', 'content': 'x' * chars}], schema=R, sampling=sampling.resolve('ruling', 0.3).at(0), max_tokens=500))",
    "    out[name] = k['options']['num_predict']",
    "print(json.dumps(out))",
])


def child(env_add: dict) -> dict:
    env = dict(os.environ, PYTHONPATH=str(ROOT), MERAVIA_NO_SERVER="1")
    for k in [k for k in env if k.startswith("DND_")]:
        env.pop(k)
    env.update(env_add)
    r = subprocess.run([sys.executable, "-c", CHILD], cwd=ROOT, env=env, capture_output=True, text=True, timeout=120)
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except Exception:
        return {"error": (r.stdout + r.stderr)[-800:]}


wide = child({"DND_THINK_TASKS": "ruling"})
narrow = child({"DND_THINK_TASKS": "ruling", "DND_NUM_CTX": "4096"})
check("the room to think in is raised to 8,192 tokens, and a call whose context has space for it gets all of it",
      wide.get("room") == 8192 and wide.get("short") == 500 + 8192, wide)
check("...but never more than the context holds beside the prompt and the answer (a 4,096 context, a 6,000-character prompt)",
      narrow.get("long") == 500 + (4096 - 6000 // 3 - 500 - 256) and narrow["long"] - 500 + 6000 // 3 + 500 <= 4096, narrow)
off = child({})
check("...and off, a call asks for its own ceiling only, as before", off.get("short") == 500 and off.get("long") == 500, off)

# ---- 2. the tool's room, and its context
row = {"request": {"messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
                   "options": {"num_ctx": 16384, "num_predict": 700, "temperature": 0.2}}, "tokens": {"prompt_eval_count": 12000}}
check("the tool gives a thinking call only the room its recorded context has beside its prompt (the server's own count) and answer",
      think_ab.room_for(row, think_ab._options(row, False, 0), 8192) == 16384 - 12000 - 700 - 256, think_ab.room_for(row, row["request"]["options"], 8192))
think_ab.NUM_CTX = 32768
opts = think_ab._options(row, True, 8192)
think_ab.NUM_CTX = None
check("...and --num-ctx gives every replayed call a larger context, so the whole room fits", opts["num_ctx"] == 32768
      and opts["num_predict"] == 700 + 8192, opts)

# ---- 3. road events, measured and kept to be read
SEEN = []


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
        return self.reply(200, {"build_info": "b-test", "total_slots": 1, "default_generation_settings": {"n_ctx": 32768}} if self.path == "/props"
                          else {"error": "no"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        SEEN.append(body)
        name = body["grammar"].splitlines()[0].split()[2]                        # (f527) "# Meravia <Title> <sha>": the grammar names its contract
        from llm import contracts as _contracts
        schema = getattr(_contracts, name).model_json_schema()
        content = json.dumps(simlib._fill(schema, schema))
        think = body["chat_template_kwargs"]["enable_thinking"]
        self.reply(200, {"choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content,
                                                                                        **({"reasoning_content": "The road bends. " * 60} if think else {})}}],
                         "usage": {"prompt_tokens": 3000, "completion_tokens": 300 + (500 if think else 0)},
                         "timings": {"prompt_n": 3000, "prompt_ms": 400.0, "predicted_n": 300 + (500 if think else 0), "predicted_ms": 900.0}})


server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_address[1]}"
OUT = Path("saves/thinking_room_534")
shutil.rmtree(OUT, ignore_errors=True)
with contextlib.redirect_stdout(io.StringIO()):
    rc = think_ab.main(["--recordings", "data/replay/sessions", "--server", f"llama={url}", "--tasks", "road_event", "--per-task", "5",
                        "--num-ctx", "32768", "--out", str(OUT / "road")])
rows = [json.loads(l) for l in (OUT / "road" / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
check("road events are replayed off and on, with nothing to agree with, and each answer's text and its thinking's head and tail kept",
      rc == 0 and rows and {r["task"] for r in rows} == {"road_event"} and all(r["agree"] is None for r in rows)
      and all(r["answer"] for r in rows) and all(r["thinking_head"] and r["thinking_tail"] for r in rows if r["think"])
      and all(not r["thinking_head"] for r in rows if not r["think"]), rows[:1])
check("...each thinking call with the whole room the context asked for holds, written beside it", all(b["max_tokens"] >= 8192 for b in SEEN[1:] if b["chat_template_kwargs"]["enable_thinking"])
      and all(r["room"] == 8192 for r in rows if r["think"]), [b.get("max_tokens") for b in SEEN[:3]])
server.shutdown()

# ---- 4. the evaluations, by name
ran = []
real_run = think_ab.subprocess.run


def fake_run(cmd, cwd=None, env=None, capture_output=None, text=None, timeout=None):
    ran.append({"cmd": cmd, "think": env.get("DND_THINK_TASKS"), "ctx": env.get("DND_NUM_CTX"), "room": env.get("DND_THINK_ROOM")})
    joined = " ".join(cmd)
    if "event_eval.py" in joined:
        return subprocess.CompletedProcess(cmd, 0, "\n8/11 right in 312.4s (live: the model wrote the events)", "")
    if "interp_eval.py" in joined:
        return subprocess.CompletedProcess(cmd, 1, "\n150/170 right; intercepts took 0 line(s) that were not theirs and missed 0 that were "
                                                   "(live: the model's reading counted); the model gave no usable reading 7 time(s)", "")
    return subprocess.CompletedProcess(cmd, 0, "\n20 of 24 right; 4 with no ruling", "")


think_ab.subprocess.run = fake_run
try:
    ev = think_ab.evals("http://127.0.0.1:11434", ["ruling", "pulse_cataclysm"], room=8192, which=("ruling_complex", "events", "interp"),
                        num_ctx=32768)
finally:
    think_ab.subprocess.run = real_run
names = [(e["eval"], e["think"]) for e in ev]
check("the evaluations run by name: the improvised actions of several steps from their own case file, and the events' evaluation",
      ("ruling_eval_complex", "off") in names and ("event_eval", "on") in names
      and any("ruling_cases_complex.yaml" in " ".join(r["cmd"]) for r in ran) and any("event_eval.py" in " ".join(r["cmd"]) for r in ran), names)
by = {(e["eval"], e["think"]): e for e in ev}
check("...their scores read out of every case: a ruling not given is wrong, an event case counted as event_eval says, and the "
      "interpreter's cases with no usable reading counted", by[("ruling_eval_complex", "on")]["right"] == 20 and by[("ruling_eval_complex", "on")]["of"] == 28
      and by[("event_eval", "off")]["right"] == 8 and by[("event_eval", "off")]["of"] == 11
      and by[("interp_eval", "on")]["no_answer"] == 7, by)
check("...with the context and the room asked for, and thinking on only in the 'on' pass",
      all(r["ctx"] == "32768" and r["room"] == "8192" for r in ran)
      and {r["think"] for r in ran} == {"", "ruling,pulse_cataclysm"}, ran[:2])


def refused(argv) -> bool:
    try:
        with contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
            think_ab.main(argv)
        return False
    except SystemExit as e:
        return e.code == 2


base = ["--recordings", "data/replay/sessions", "--server", "llama=http://127.0.0.1:9", "--out", str(OUT / "refused")]
check("an evaluation none of whose tasks is chosen to think, or one the tool does not know, is refused before anything is sent",
      refused(base + ["--tasks", "ruling", "--evals", "events"]) and refused(base + ["--tasks", "ruling", "--evals", "nothing"])
      and not (OUT / "refused" / "results.jsonl").exists())

# ---- 5. the improvised actions of several steps
from llm.contracts import Need
CAPS = set(yaml.safe_load((ROOT / "data/rules/capabilities.yaml").read_text(encoding="utf-8")))
KINDS = set(Need.model_fields["kind"].annotation.__args__)
cases = yaml.safe_load((ROOT / "data/replay/ruling_cases_complex.yaml").read_text(encoding="utf-8"))
first = yaml.safe_load((ROOT / "data/replay/ruling_cases.yaml").read_text(encoding="utf-8"))
places = {c["at"] for c in first}
check("the second ruling set is improvised actions of several steps, each case well formed (a known place, a sense, needs and means "
      "the game has), with nonsense among them and pairs that only the character's means decide",
      len(cases) >= 20 and all(c["at"] in places and c["expect"] in ("yes", "cost", "no") for c in cases)
      and all(set(c.get("needs") or []) <= KINDS and set(c.get("means") or []) <= CAPS for c in cases)
      and sum(c["expect"] == "no" for c in cases) >= 6 and sum(1 for c in cases if "means" in c) >= 4
      and all(c["line"].count(",") + c["line"].count(" and ") + c["line"].count(" then ") >= 1 for c in cases)
      and not {c["line"] for c in cases} & {c["line"] for c in first}, len(cases))
r = subprocess.run([sys.executable, "tools/ruling_eval.py", "--cases", "data/replay/ruling_cases_complex.yaml"], cwd=ROOT,
                   env=dict(os.environ, MERAVIA_NO_SERVER="1"), capture_output=True, text=True, timeout=300)
check("...and ruling_eval reads it with --cases (offline, the cases with no ruling of their own are counted, not run)",
      r.returncode == 0 and f"; {len(cases)} need the model" in r.stdout, (r.returncode, r.stdout[-300:], r.stderr[-300:]))

# ---- 6. the interpreter's evaluation reads each case for itself
import interp_eval
bench = interp_eval.Bench(save="thinking_room_534")
try:
    bench.store.save_question({"kind": "law", "question": "Will you pay the fine?", "speaker": "", "turn": 1})
    bench.dress({})
    left = bench.store.load_question()
finally:
    bench.session.close()
    shutil.rmtree(ROOT / "saves" / "thinking_room_534", ignore_errors=True)
check("a question the last case left open (the law's, after a bribe) is cleared when the next case is dressed", left is None, left)

shutil.rmtree(OUT, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
