"""(f475) Measure first (GOALS.md S7): a prompt's parts are measured (their sizes make the rendered prompt; the layout is its skeleton;
the tail is the part that changes); every call's log row and recording row carries its shape (chars, sizes, tail, prompt version) and
the server's cached-prompt count when it gives one, outside the request's hash; a night's summary measures the speech tasks (prompt
characters and first-try acceptance); card_profile --expected prices answers at their expected sizes; the training data keeps one prompt
version per task; the server report warns of a model off the card; and the baseline's task names are checked at startup."""
import gzip
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import config
import ollama
from pydantic import BaseModel
from engine.prompt import Prompt
from engine import data_check, recording
from llm import gateway, setup_check
import latency
gateway.keep_extra_fields()      # (f514) the client's replies keep the server's extra fields once the real client is built; this test builds its own
import card_profile
import lora_dataset

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- the prompt's parts, measured
p = Prompt().instruction("Speak plainly.", "HOW YOU SPEAK").fact("Bram keeps the inn.\nHe was born here.", "WHO YOU ARE").history("Morning.")
check("the parts' sizes and the blank lines between them make the rendered prompt",
      sum(n for _, _, n in p.sizes()) + 2 * (len(p.parts) - 1) == len(p.render()), (p.sizes(), len(p.render())))
check("the tail is the last part when none is marked", p.tail() == "Morning.", p.tail())
q = Prompt().fact("Bram keeps the inn.", "WHO YOU ARE").mark_tail().history("Morning.").instruction("Answer now.", "NOW")
check("...and everything from the mark when one is", q.tail() == "Morning.\n\nNOW: Answer now.", q.tail())
a = gateway.shape("SYSTEM", p, p.render())
reworded = Prompt().instruction("Speak very plainly.", "HOW YOU SPEAK").fact("Bram keeps the old inn.\nHe was born here.", "WHO YOU ARE").history("Evening.")
reordered = Prompt().fact("Bram keeps the inn.\nHe was born here.", "WHO YOU ARE").instruction("Speak plainly.", "HOW YOU SPEAK").history("Morning.")
check("the prompt version stays with new wording, and moves when the parts are reordered",
      gateway.shape("SYSTEM", reworded, reworded.render())["prompt_version"] == a["prompt_version"]
      and gateway.shape("SYSTEM", reordered, reordered.render())["prompt_version"] != a["prompt_version"], a)
check("...and its system half moves with the system text", gateway.shape("OTHER", p, p.render())["prompt_version"].split(".")[0]
      != a["prompt_version"].split(".")[0])
check("a call's shape counts what it reads and where", a["chars"] == len("SYSTEM") + len(p.render()) and a["sizes"][0] == ["system", "", 6]
      and [s[1] for s in a["sizes"][1:]] == ["HOW YOU SPEAK", "WHO YOU ARE", ""] and a["tail_chars"] == len("Morning."), a)

# ---- a call's log row and recording row carry the shape and the cached count, outside the request's hash
class Read(BaseModel):
    x: str


def answer(**k):
    return ollama.ChatResponse(model="m", done=True, done_reason="stop", message={"role": "assistant", "content": '{"x": "fine"}'},
                               prompt_eval_count=400, eval_count=5, prompt_eval_duration=10**8, eval_duration=10**7,
                               prompt_eval_cached_count=300)


log = Path("saves/measure_first_475_calls.jsonl")
log.unlink(missing_ok=True)
config.LOG_PATH = str(log)
game = simlib.campaign("measure_first_475")
real_chat = gateway._client.chat
gateway._client.chat = answer
folder = Path("saves/measure_first_475_rec")
shutil.rmtree(folder, ignore_errors=True)
rec = recording.Recorder(game.store, folder=folder).install()
got = gateway.generate("work_offer_read", "Read the offer.", p, Read)
rec.close()
gateway._client.chat = real_chat
rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()]
row = rows[-1] if rows else {}
check("the call log's row carries the shape and the server's cached count", got.x == "fine" and row.get("chars") == len("Read the offer.") + len(p.render())
      and row.get("prompt_version") and row.get("tail_chars") == len("Morning.") and (row.get("tokens") or {}).get("cached") == 300, row)
with gzip.open(folder / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
    crow = [json.loads(l) for l in f][-1]
check("...and so does the recording's", (crow.get("shape") or {}).get("prompt_version") == row.get("prompt_version")
      and (crow.get("tokens") or {}).get("cached") == 300, crow)
check("...beside the request, never in what its hash is made of", "shape" not in (crow.get("request") or {}) and "chars" not in (crow.get("request") or {})
      and [m["role"] for m in crow["request"]["messages"]] == ["system", "user"], sorted(crow.get("request") or {}))
check("a reply with no cached count says nothing of one",
      gateway.cached_count(ollama.ChatResponse(model="m", done=True, message={"role": "assistant", "content": ""})) is None)

# ---- the speech tasks, measured from a night's call log
night = [{"task": "npc_conversation", "attempt": 0, "chars": 20000, "error": None, "tail_chars": 900},
         {"task": "npc_conversation", "attempt": 0, "chars": 24000, "error": "rejected"},
         {"task": "npc_conversation", "attempt": 1, "chars": 24500, "error": None},
         {"task": "npc_conversation", "attempt": 0, "error": None, "messages": [{"role": "system", "content": "s" * 100}, {"role": "user", "content": "u" * 900}]},
         {"task": "narrate", "attempt": 0, "chars": 5000, "error": None}]
sm = latency.speech_measures(night)
c = sm.get("npc_conversation") or {}
check("first-try acceptance is the first tries accepted, of all first tries: 2 of 3", c.get("calls") == 3 and c.get("first_try") == round(2 / 3, 3), c)
check("...prompt sizes from the gateway's count, else the messages as logged, at the first try", c.get("max") == 24000 and c.get("p50") == 20000
      and c.get("tail_p50") == 900 and "narrate" not in sm, c)
check("a shortened system prompt is not counted as a size", latency.prompt_chars({"messages": [{"role": "system", "content": "x [...shortened in log]"},
                                                                                              {"role": "user", "content": "y"}]}) is None)
rows_ = latency.speech_table(night)
check("summary.md's speech table has a row per task measured", any(r.startswith("| npc_conversation | 3 | 67% |") for r in rows_), rows_)

# ---- answers priced at their expected sizes, and the training data's one version per task
gold = Path("data/replay/sessions/stub_short")
exp = dict(card_profile.estimate_inputs(gold, expected=True))
rec_ = dict(card_profile.estimate_inputs(gold))
check("--expected prices every answer at its task's size: dearer than the stub's few words, never cheaper",
      exp and all(exp[i] >= rec_.get(i, 0) - 1e-9 for i in exp) and sum(exp.values()) > sum(rec_.values()), (sum(exp.values()), sum(rec_.values())))
runs = Path("saves/measure_first_475_lora")
shutil.rmtree(runs, ignore_errors=True)
(runs / "a").mkdir(parents=True)
msgs = lambda u: [{"role": "system", "content": "S"}, {"role": "user", "content": u}]
calls_ = [{"time": "2026-11-01T00:00:00", "task": "npc_conversation", "attempt": 0, "messages": msgs("old"), "raw": '{"speech": "a"}', "error": None,
           "prompt_version": "aaaa1111.000001"},
          {"time": "2026-11-05T00:00:00", "task": "npc_conversation", "attempt": 0, "messages": msgs("new"), "raw": '{"speech": "b"}', "error": None,
           "prompt_version": "bbbb2222.000002"}]
(runs / "a" / "llm_calls.jsonl").write_text("\n".join(json.dumps(r) for r in calls_) + "\n", encoding="utf-8")
counts = lora_dataset.build([runs / "a"], [], runs / "out", prompts="full", tasks=["npc_conversation"])
nc = counts["train"]["npc_conversation"]
check("the training data keeps one prompt version per task, the newest", nc.get("calls") == 1 and nc.get("dropped: an older prompt version") == 1, dict(nc))
shutil.rmtree(runs, ignore_errors=True)

# ---- the server, and the baseline's task names
rep = setup_check.server_report(ps={"models": [{"name": "gemma4:12b", "size": 10_000_000_000, "size_vram": 7_000_000_000, "context_length": 4096}]},
                                version={"version": "0.12.0"})
check("the server report warns of a model not wholly on the card, and of another context", rep["version"] == "0.12.0" and len(rep["warnings"]) == 2
      and rep["loaded"][0]["vram_gb"] == 7.0, rep)
ok = setup_check.server_report(ps={"models": [{"name": "gemma4:12b", "size": 10, "size_vram": 10, "context_length": config.NUM_CTX}]}, version={})
check("...and of nothing when it is all there", not ok["warnings"], ok)
check("the baseline file passes the startup check", data_check.baseline_problems() == [], data_check.baseline_problems())
check("...and an unknown task in it is refused", any("made_up" in b for b in data_check.baseline_problems({"speech_tasks": ["npc_conversation", "made_up"]})))

game.store.close()
log.unlink(missing_ok=True)
shutil.rmtree(folder, ignore_errors=True)
shutil.rmtree("saves/measure_first_475", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
