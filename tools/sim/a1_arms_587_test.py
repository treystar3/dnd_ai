"""(f587) What A1 needs before it runs (docs/design/09 A1, the owner's design of 2026-11-11). The samplers DRY and XTC are sent whole:
DRY's base, allowed length and look-back and XTC's threshold join the strengths already sent, at neutral values that change nothing
while both stay off. The four arms are data (data/rules/sampling.yaml arms: DRY, XTC, both, min_p), laid over the six prose and speech
tasks only when a run names one (DND_SAMPLING_ARM), and checked at startup like every sampler value. And what A1 counts beside the
prose: each task's first-try acceptance, its rewrites, the name errors its answers were sent back for (by kind), and the names the
game mended silently (a misspelt speaker, a told name written a letter off), counted per task and kept in a night's run.json.
Run: python tools/sim/a1_arms_587_test.py"""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from engine import data_check, names, streams
from llm import gateway, llama, sampling
from llm.contracts import Narration
sys.path.insert(0, "tools")
import prose_measure as pm

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

S = config._SAMPLING_FILE
# ---- the samplers, whole
NEW = ("dry_base", "dry_allowed_length", "dry_penalty_last_n", "xtc_threshold")
check("DRY's base, allowed length and look-back and XTC's threshold are samplers the game sends", all(k in llama.SAMPLER_KEYS and k in llama.RANGES for k in NEW))
check("...at neutral values in the base, so nothing changes while DRY and XTC are off", {k: S["base"][k] for k in NEW}
      == {"dry_base": 1.75, "dry_allowed_length": 2, "dry_penalty_last_n": 0, "xtc_threshold": 0.1}
      and S["base"]["dry_multiplier"] == 0.0 and S["base"]["xtc_probability"] == 0.0, {k: S["base"].get(k) for k in NEW})
body = llama.llama_body(type("R", (), {"messages": [], "schema": Narration, "sampling": sampling.resolve("narrate", 0.9).at(0),
                                       "max_tokens": 10, "voice": None})())
check("...and every request carries them", all(k in body for k in NEW), sorted(body))

# ---- the arms, as data
A = S["arms"]
check("the four arms, as the owner set them", A == {"dry": {"dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 2, "dry_penalty_last_n": 512},
                                                       "xtc": {"xtc_probability": 0.5, "xtc_threshold": 0.1},
                                                       "both": {"dry_multiplier": 0.8, "dry_base": 1.75, "dry_allowed_length": 2,
                                                                "dry_penalty_last_n": 512, "xtc_probability": 0.5, "xtc_threshold": 0.1},
                                                       "min_p": {"min_p": 0.05}}, A)
SIX = {"narrate", "combat_narrate", "npc_conversation", "hire_chat", "exchange", "dialogue_frame"}
check("...for the six prose and speech tasks only", set(S["arm_tasks"]) == SIX, S["arm_tasks"])
check("the startup checks pass", data_check.sampling_problems() == [] and llama.sampler_problems() == [],
      (data_check.sampling_problems(), llama.sampler_problems()))
broken = dict(S, arms=dict(A, dry=dict(A["dry"], dry_base=9.0), odd={"tempurature": 1.0}), arm_tasks=list(S["arm_tasks"]) + ["no_such_task"])
probs = data_check.sampling_problems(broken)
check("...and catch an arm value out of range, a misspelt sampler and a task that is no task", any("dry_base" in p for p in probs)
      and any("tempurature" in p for p in probs) and any("no_such_task" in p for p in probs), probs)

was = config.SAMPLING_ARM
try:
    config.SAMPLING_ARM = ""
    plain = sampling.resolve("narrate", 0.9).at(0).resolved()
    config.SAMPLING_ARM = "dry"
    dry = sampling.resolve("narrate", 0.9).at(0).resolved()
    interp = sampling.resolve("interpret_action", 0.2).at(0).resolved()
    config.SAMPLING_ARM = "both"
    both_hire = sampling.resolve("hire_chat", 1.0).at(0).resolved()
finally:
    config.SAMPLING_ARM = was
check("no arm named: today's sampling", plain["dry_multiplier"] == 0.0 and plain["xtc_probability"] == 0.0 and plain["min_p"] == 0.0)
check("an arm named: laid over a prose task's own values", dry["dry_multiplier"] == 0.8 and dry["dry_penalty_last_n"] == 512
      and dry["repeat_penalty"] == plain["repeat_penalty"], dry)
check("...never over a task outside the six (the reading of a line)", interp["dry_multiplier"] == 0.0, interp)
check("...and 'both' is DRY and XTC together", both_hire["dry_multiplier"] == 0.8 and both_hire["xtc_probability"] == 0.5)
check("a run names its arm by DND_SAMPLING_ARM, kept in its run.json", "DND_SAMPLING_ARM" in Path("config.py").read_text(encoding="utf-8")
      and '"sampling_arm"' in Path("tools/nightrun.py").read_text(encoding="utf-8"))

# ---- the silent name mends, counted per task
names.BY_TASK.clear()
stub.a_Narration = lambda u, k: {"text": "Zorra waits by the gate."}
streams.begin(3, 1, "look")
r = gateway.generate("narrate", "The people here: Zurra the miller.", "Zurra stands at the gate.", Narration)
check("a told name written a letter off is mended, and counted for its task", "Zurra" in r.text and names.BY_TASK.get("narrate") == 1,
      (r.text, dict(names.BY_TASK)))
check("...kept in a night's run.json", '"name_repairs": dict(names.BY_TASK)' in Path("tools/nightrun.py").read_text(encoding="utf-8"))
src = Path("engine/banter.py").read_text(encoding="utf-8")
check("a misspelt speaker the exchange mends is counted too", 'REPAIRS["speaker"] += 1' in src)

# ---- what the measure reads from a call log
d = Path(tempfile.mkdtemp(prefix="a1_587_"))


def row(task, attempt, error=None, **more):
    return json.dumps({"task": task, "attempt": attempt, "raw": json.dumps({"text": "x"}), "error": error, **more})


rows = [row("narrate", 0), row("narrate", 0, "'Bolt' is no one and nowhere you were told of; name only the people and places you were given"),
        row("narrate", 1), row("narrate", 0, rewrite_of_draft=["reused stale phrasing"]),
        row("hire_chat", 0, "you are answering Ana; Ost is someone else here. Do not call the player Ost: use their name, Ana, or none"),
        row("hire_chat", 1), row("exchange", 0, "speaker must be one of: Ana, Ost"), row("exchange", 1),
        row("npc_conversation", 0, "write it shorter"), row("npc_conversation", 1)]
(d / "llm_calls.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
(d / "run.json").write_text(json.dumps({"name_repairs": {"exchange": 2, "narrate": 1}}), encoding="utf-8")
acc = pm.acceptance([str(d / "llm_calls.jsonl")])
check("first-try acceptance per task: answers taken at their first try, of calls", acc["narrate"]["calls"] == 3
      and acc["narrate"]["first_try"] == 2 and acc["hire_chat"]["first_try"] == 0, acc)
check("...rewrites per task", acc["narrate"]["rewrites"] == 1, acc["narrate"])
check("...name errors per task, by kind; a refusal that is not about a name is not one", acc["narrate"]["name_errors"] == {"no one and nowhere": 1}
      and acc["hire_chat"]["name_errors"] == {"someone else here": 1} and acc["exchange"]["name_errors"] == {"not a speaker": 1}
      and acc["npc_conversation"]["name_errors"] == {}, acc)
check("...and the silent mends from the run beside the log", acc["exchange"]["mended"] == 2 and acc["narrate"]["mended"] == 1, acc)
rows2 = [row("hire_chat", 0, "write it shorter"), row("hire_chat", 1, "write it shorter"), row("hire_chat", 0, relaxed=True)]
(d / "norun").mkdir(exist_ok=True)
(d / "norun" / "relaxed.jsonl").write_text("\n".join(rows2) + "\n", encoding="utf-8")
acc2 = pm.acceptance([str(d / "norun" / "relaxed.jsonl")])
check("a relaxed last try is the same call, never a new one taken at its first try", acc2["hire_chat"]["calls"] == 1
      and acc2["hire_chat"]["first_try"] == 0, acc2)
check("...and a log with no run beside it shows its mends as not counted, never as none", acc2["hire_chat"]["mends_counted"] is False
      and pm.acceptance_table(acc2)[-1].endswith("| - |"), pm.acceptance_table(acc2))
rows3 = [row("exchange", 0, "everyone named must speak at least once"), row("exchange", 1)]
(d / "cast.jsonl").write_text("\n".join(rows3) + "\n", encoding="utf-8")
check("...and the cast left out of an exchange is a name error too", pm.acceptance([str(d / "cast.jsonl")])["exchange"]["name_errors"]
      == {"the cast left out": 1})
src_g = Path("llm/gateway.py").read_text(encoding="utf-8")
check("the gateway tags its relaxed last try in the log", "tagged(relaxed=True)" in src_g)
src_r = Path("engine/recording.py").read_text(encoding="utf-8") + Path("tools/rerun.py").read_text(encoding="utf-8")
check("a recording keeps the run's arm, a replay samples with it, a kept recording is made with none",
      'self.meta["sampling_arm"] = config.SAMPLING_ARM' in src_r and 'rec["meta"].get("sampling_arm")' in src_r
      and "the recording is made with none" in src_r)
out = d / "m.json"
pm.main([str(d / "llm_calls.jsonl"), "--json", str(out), "--samples", "0"])
check("the kept numbers carry them", "acceptance" in json.loads(out.read_text(encoding="utf-8")))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
