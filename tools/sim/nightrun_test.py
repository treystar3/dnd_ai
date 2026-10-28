"""tools/nightrun.py plays turns on its own and leaves a run that tools/latency.py can read: with the stand-in model, a short run makes
its turn rows, its call log, a transcript and a summary, and stops at the turn limit. Also: the gateway keeps Ollama's own counts when
an answer carries them, and leaves them out when it does not."""
import json, shutil, subprocess, sys, types
from pathlib import Path
sys.path.insert(0, ".")
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# the gateway's counts
from llm import gateway
full = types.SimpleNamespace(prompt_eval_count=1234, eval_count=56, prompt_eval_duration=2.5e9, eval_duration=3.0e9, load_duration=0, total_duration=5.6e9)
u = gateway._usage(full)
check("an answer's counts are kept: tokens and milliseconds", u == {"prompt": 1234, "out": 56, "read_ms": 2500, "write_ms": 3000, "load_ms": 0, "total_ms": 5600}, u)
check("a stand-in's answer, which has none, gives none", gateway._usage(types.SimpleNamespace(done_reason="stop")) is None)

# a short run with the stand-in model
out = Path("saves/nightrun_test/out")
shutil.rmtree("saves/nightrun_test", ignore_errors=True)
shutil.rmtree("saves/nightrun_test_game", ignore_errors=True)
r = subprocess.run([sys.executable, "tools/nightrun.py", "--stub", "--turns", "12", "--seed", "3", "--hours", "1",
                    "--out", str(out), "--save", "nightrun_test_game"], capture_output=True, text=True, timeout=900)
check("the run finishes on its own", r.returncode == 0, (r.stdout[-1500:], r.stderr[-1500:]))
rows = [json.loads(l) for l in (out / "turns.jsonl").read_text(encoding="utf-8").splitlines()] if (out / "turns.jsonl").exists() else []
check("one row per turn, twelve turns", len(rows) == 12, len(rows))
need = {"n", "kind", "text", "where", "seconds", "first_word", "chat_calls", "chat_seconds", "retries", "embed_calls", "hesitated", "level"}
check("a row carries the line, where it was typed, its time, its first word and its calls", rows and all(need <= set(x) for x in rows), rows[:1])
check("the lines are what a player types, in several kinds", len({x["kind"] for x in rows}) >= 3 and all(x["text"].strip() for x in rows), [x["kind"] for x in rows])
check("the model's calls were counted against the turns", sum(x["chat_calls"] for x in rows) >= 12, [x["chat_calls"] for x in rows])
calls = (out / "llm_calls.jsonl").exists() and [json.loads(l) for l in (out / "llm_calls.jsonl").read_text(encoding="utf-8").splitlines()]
check("the run keeps its own call log, every attempt with its task and seconds", bool(calls) and all("task" in c and "seconds" in c for c in calls), bool(calls))
info = json.loads((out / "run.json").read_text(encoding="utf-8")) if (out / "run.json").exists() else {}
check("the run says why it stopped", info.get("reason") == "turn limit (12)" and info.get("turns") == 12, info)
check("the character set out with a full party from the home hall, of three different roles",
      len(info.get("party", [])) == 3 and len({m["role"] for m in info["party"]}) == 3 and all(m["name"] for m in info["party"]), info.get("party"))
check("a transcript was written", (out / "transcript.md").exists() and (out / "transcript.md").stat().st_size > 500)
from storage.campaign import CampaignStore as _CS
_st = _CS.open_or_create("nightrun_test_game"); _pl = _st.load_player(); _st.close()
check("the character past the tutorial is a guild member of a rank fitting its level, so contracts are play", _pl.guild_rank and _pl.guild_rank != "F", _pl.guild_rank)
summary = (out / "summary.md").read_text(encoding="utf-8") if (out / "summary.md").exists() else ""
check("the summary has the turns and the calls by task", "## Turns" in summary and "## Calls by task" in summary and "| interpret_action |" in summary, summary[:600])
# (f368) the bot plays as a persona with goals; the rows and the summary say so
check("every row says what the line was for, who was typing, and where the words came from",
      rows and all({"goal", "persona", "source", "refers"} <= set(x) for x in rows) and all(x["source"] == "template" for x in rows) and all(x["goal"] for x in rows), rows[:1])
check("the run's persona follows the seed when none is named, and the bot's measures are in run.json",
      info.get("persona") == "wanderer" and isinstance(info.get("bot"), dict) and {"contracts_taken", "doors_seen", "goals_done", "deaths_above_band", "places"} <= set(info["bot"])
      and isinstance(info.get("distinct"), float) and "ended_by_player" in info, (info.get("persona"), info.get("bot")))
check("the summary measures the play", "## Play" in summary and "| Distinct lines |" in summary and "playing as wanderer" in summary, summary[-1200:])
r2 = subprocess.run([sys.executable, "tools/latency.py", str(out)], capture_output=True, text=True, timeout=120)
check("tools/latency.py reads the folder again on its own", r2.returncode == 0 and "Calls by task" in r2.stdout, r2.stderr[-500:])
r3 = subprocess.run([sys.executable, "tools/latency.py", "--calls", str(out / "llm_calls.jsonl")], capture_output=True, text=True, timeout=120)
check("...and a call log on its own", r3.returncode == 0 and "| Task |" in r3.stdout, r3.stderr[-500:])
# (f361) a night of runs from one command: each its own process, seed and class, its own folder and save; a summary of the night at the end
import glob
for d in glob.glob("saves/nightrun_batch_test*"):
    shutil.rmtree(d, ignore_errors=True)
base = Path("saves/nightrun_test/night")
r4 = subprocess.run([sys.executable, "tools/nightrun.py", "--stub", "--runs", "2", "--parallel", "2", "--turns", "4", "--hours", "1", "--seed", "5", "--classes", "warrior,mage",
                     "--starts", "green,known", "--personas", "careful,talker", "--out", str(base), "--save", "nightrun_batch_test"], capture_output=True, text=True, timeout=1200)
runs = sorted((p for p in base.iterdir() if p.is_dir()), key=lambda p: int(p.name.rsplit("_", 1)[1])) if base.exists() else []   # by seed: two runs can share a minute
infos = [json.loads((p / "run.json").read_text(encoding="utf-8")) for p in runs if (p / "run.json").exists()]
check("two runs from one command (f370: both at once), each in its own folder named by its class and seed", r4.returncode == 0 and len(runs) == 2 and "2 at a time" in r4.stdout
      and runs[0].name.endswith("_warrior_5") and runs[1].name.endswith("_mage_6"), (r4.stdout[-800:], r4.stderr[-800:], [p.name for p in runs]))
check("...each a whole run of its own: its seed, its class, its turns", len(infos) == 2 and [i["seed"] for i in infos] == [5, 6] and all(i["turns"] == 4 for i in infos)
      and infos[0]["class"] != infos[1]["class"], infos)
check("...and its own starting point: the second began as someone known, at that start's level, with a past the town remembers",
      len(infos) == 2 and [i.get("start") for i in infos] == ["green", "known"] and infos[1]["level"] == 22 and infos[1].get("start_days") == 40
      and len(infos[1].get("past") or []) == 2 and infos[1].get("met_at_start", 0) >= 4, [(i.get("start"), i.get("level"), i.get("past"), i.get("met_at_start")) for i in infos])
check("...with a save of its own, so the second does not continue the first", sorted(Path(d).name for d in glob.glob("saves/nightrun_batch_test*")) == ["nightrun_batch_test_mage_6", "nightrun_batch_test_warrior_5"],
      glob.glob("saves/nightrun_batch_test*"))
check("...and its own persona, rotating through the ones named", [i.get("persona") for i in infos] == ["careful", "talker"], [i.get("persona") for i in infos])
night = list(base.glob("batch_*.md"))
check("the night is summed up in one file listing the runs, with each one's persona and its measures", len(night) == 1 and "_warrior_5" in night[0].read_text(encoding="utf-8")
      and "_mage_6" in night[0].read_text(encoding="utf-8") and "| careful |" in night[0].read_text(encoding="utf-8") and "Distinct lines" in night[0].read_text(encoding="utf-8"), night)
for d in glob.glob("saves/nightrun_batch_test*"):
    shutil.rmtree(d, ignore_errors=True)
shutil.rmtree("saves/nightrun_test", ignore_errors=True)
shutil.rmtree("saves/nightrun_test_game", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
