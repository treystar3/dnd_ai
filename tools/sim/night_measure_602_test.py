"""(f602) What a night says of the two questions phase 2's pod session asks and the other readers do not answer
(docs/design/14_phase2_plan.md, the pod session): (1) the two slots (f536): does the understanding's cached prompt hold from turn to
turn on its own slot, and does a background call on the shared slot make the player's turn wait (or move its call to the understanding's
slot); (2) births and situation rulings: their count and seconds a game day, priced on the minimum card from the card they were measured
on (data/rules/cards.yaml, as tools/card_profile.py scales), and how many births were within reach. tools/night_measure.py reads a run
folder as a night writes it; this test makes one whose answers are known, and reads it again as a finished night leaves it.
Run: python tools/sim/night_measure_602_test.py"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
from tools import night_measure as M

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


BASE = ROOT / "saves" / f"night_measure_602_{os.getpid()}"            # its own folder: two runs at once never share it
RUN = BASE / "20261112_0803_warrior_1"
shutil.rmtree(BASE, ignore_errors=True)
(RUN / "run").mkdir(parents=True)
(RUN / "run" / "server.json").write_text(json.dumps({"slot_of": {"interpret_action": 0}, "other_slot": 1}), encoding="utf-8")
(RUN / "run.json").write_text(json.dumps({"server": {"device": "CUDA0: NVIDIA GeForce RTX 4090 (24076 MiB)"}}), encoding="utf-8")


def call(turn, task, prompt, cached, read_ms, write_ms, wait_ms=0, attempt=0):
    return {"time": "2026-11-12T08:16:13+00:00", "turn": turn, "task": task, "attempt": attempt, "seconds": (read_ms + write_ms + wait_ms) / 1000,
            "tokens": {"prompt": prompt, "out": 50, "read_ms": read_ms, "write_ms": write_ms, "cached": cached, "wait_ms": wait_ms},
            "chars": 10000, "sizes": [["system", "", 6500], ["fact", "RIGHT NOW", 3500]]}


calls = [
    call(1, "interpret_action", 3000, 0, 900, 300),               # the first: nothing to hold yet
    call(2, "interpret_action", 3000, 2500, 120, 300),            # held
    call(3, "interpret_action", 3000, 2700, 100, 300),            # held
    call(3, "interpret_action", 3100, 3050, 20, 300, attempt=1),  # its retry: the same prompt again, no turn-to-turn measure
    call(4, "interpret_action", 3000, 300, 880, 300),             # lost
    call(2, "narrate", 2000, 0, 500, 900, wait_ms=40),
    call(3, "narrate", 2000, 0, 500, 900, wait_ms=2600),          # waited, on a turn with background calls
    call(3, "situation_parts", 4000, 0, 1000, 2000),              # a birth's parts
    call(5, "situation_parts", 4000, 0, 1000, 2000, attempt=1),   # its retry: a call made, counted
    call(5, "event_judge", 3000, 0, 800, 1200),                   # a situation ruling
    call(6, "situation_parts", 4000, 0, 1000, 2000),              # on a turn the bot hesitated on: outside the played clock
]
(RUN / "llm_calls.jsonl").write_text("\n".join(json.dumps(c) for c in calls) + "\n", encoding="utf-8")

turns = [{"n": i, "turn": i, "seconds": s, "first_word": f, "background_calls": b, "state": {"minutes": m}}
         for i, (s, f, b, m) in enumerate([(5.0, 2.0, 0, 480), (6.0, 2.5, 0, 960), (12.0, 6.0, 2, 1440), (7.0, 3.0, 1, 2400),
                                            (8.0, 3.0, 0, 3360)], 1)]
turns.append({"n": 6, "turn": 6, "hesitated": True, "seconds": 1.0, "state": {"minutes": 3400}})
turns.append({"n": 7, "turn": 7, "seconds": 9.0, "error": "KeyError: x", "background_calls": 3, "state": {"minutes": 9999}})   # broken
(RUN / "turns.jsonl").write_text("\n".join(json.dumps(t) for t in turns) + "\n", encoding="utf-8")

pulse = [{"t": 600, "kind": "thread", "tier": "normal", "made_by": "engine", "reach": True},
         {"t": 1500, "kind": "thread", "tier": "rare", "made_by": "model"},
         {"t": 2000, "kind": "thread", "tier": "uncommon", "made_by": "engine", "reach": False},
         {"t": 2100, "kind": "news", "text": "not a birth"},
         {"t": 2200, "kind": "thread", "text": "Wolves: the model wrote no way to end it, so the alpha will haunt the wood"},
         {"t": 2300, "kind": "thread", "text": "[cataclysm:fire] The burning from Parth - begins"},
         {"t": 9000, "kind": "thread", "tier": "normal", "made_by": "engine", "reach": True}]        # after the played clock
(RUN / "pulse.jsonl").write_text("\n".join(json.dumps(p) for p in pulse) + "\n", encoding="utf-8")

new0 = lambda n: f"1.00.000.{n:03d} I slot   operator(): id  0 | task {n} | new prompt, n_ctx_slot = 16384, n_keep = 0, task.n_tokens = 3000"
(RUN / "llama-server.log.1").write_text("\n".join([
    "0.03.121.165 I load_tensors: offloading 47 repeating layers to GPU",
    "0.03.121.166 I load_tensors: offloaded 49/49 layers to GPU",
    new0(10), "1.00.000.011 I slot   operator(): id  0 | task 10 | forcing full prompt re-processing due to lack of cache data",
    new0(11), new0(12),
]) + "\n", encoding="utf-8")
(RUN / "llama-server.log").write_text("\n".join([
    new0(20), "2.00.000.001 I slot   operator(): id  0 | task 20 | restored context checkpoint (pos_min = 1715, pos_max = 2738)",
    new0(30), "3.00.000.001 I slot   operator(): id  0 | task 30 | restored context checkpoint (pos_min = 1715, pos_max = 2738)",
    new0(31),                                                      # six on slot 0 for five tries of its own: one moved there
    "4.00.000.000 I slot   operator(): id  1 | task 40 | new prompt, n_ctx_slot = 16384, n_keep = 0, task.n_tokens = 302",
    "4.00.000.001 I slot   operator(): id  1 | task 40 | forcing full prompt re-processing due to lack of cache data",
]) + "\n", encoding="utf-8")

run = M.load(RUN)
s = M.slots(run)
u = s["understanding"]
check("the understanding's slot is the run's own (run/server.json slot_of), its first try a turn read from the call log, a retry left out",
      u["slot"] == 0 and u["tasks"] == ["interpret_action"] and u["turns"] == 4 and s["map_from"] == "run/server.json", u)
check("...the cache held when half the prompt or more was cached: 2 of the 3 after the first, the spread and the system's share beside it",
      (u["held"], u["of"]) == (2, 3) and u["share_p50"] == 0.83 and u["share_p10"] == 0.1 and u["system_p50"] == 0.65, u)
log = s["log"]
check("the server's own log, both files in order, by slot: new prompts, checkpoints restored, prompts processed whole",
      log[0] == {"prompts": 6, "restored": 2, "whole": 1} and log[1] == {"prompts": 1, "restored": 0, "whole": 1}, log)
check("...a log that kept the night's start says how many calls the understanding's slot took beyond its own tries: 1",
      s["whole_log"] and s["rotated"] and s["moved"] == 1, (s["whole_log"], s["moved"]))
sp = s["split"]
check("the turn's calls' waits on turns with background calls beside turns without; the hesitated and the broken turns left out",
      sp["with"]["turns"] == 2 and sp["without"]["turns"] == 3 and sp["with"]["most_ms"] == 2600 and sp["with"]["over_1s"] == 1
      and sp["without"]["most_ms"] == 40 and sp["with"]["first_word_p50"] == 4.5 and not s["lanes"], sp)

d = M.per_day(run, read=6.5, write=2.8)
check("game days from the played turns' clock (the hesitated and the broken turns' minutes left out): 480 to 3360 is 2 days",
      d["days"] == 2.0 and not d["short"], d["days"])
b = d["tasks"]["situation_parts"]
check("births' parts within the played turns: every attempt a call, its seconds measured and on the target (read x6.5, write x2.8)",
      b["calls"] == 2 and b["seconds"] == 6.0 and b["target_seconds"] == round(2 * (1.0 * 6.5 + 2.0 * 2.8), 1) and b["per_day"] == 1.0, b)
j = d["tasks"]["event_judge"]
check("...and the situation rulings beside them; a task the night made no call of is there, at nothing",
      j["calls"] == 1 and j["target_seconds"] == round(0.8 * 6.5 + 1.2 * 2.8, 1) and d["tasks"]["act_ruling"]["calls"] == 0, d["tasks"])
bb = d["births"]
check("births within the clock: by tier (a cataclysm by its mark), by who made them, within reach; a boss's haunting and news are none",
      bb["all"] == 4 and bb["per_day"] == 2.0 and bb["tiers"] == {"cataclysm": 1, "normal": 1, "rare": 1, "uncommon": 1}
      and bb["made_by"] == {"?": 1, "engine": 2, "model": 1} and (bb["in_reach"], bb["reach_of"]) == (1, 2), bb)

check("the card a night ran on is read from its run.json, by cards.yaml's patterns", M.card_of(run) == "RTX 4090", M.card_of(run))
f = M.factors("RTX 4090", "RTX 3060 12GB")
check("the factors are card_profile's: compute for reading, bandwidth for writing", abs(f[0] - 82.6 / 12.7) < 1e-9 and abs(f[1] - 1008 / 360) < 1e-9, f)

# ---- a finished night removes run/server.json: the game's own slot map stands in, and says so
shutil.rmtree(RUN / "run")
done = M.slots(M.load(RUN))
check("a finished night (no run/server.json): the slot map is the game's own data/runtime/server.yaml, named as the source",
      done["map_from"] == "data/runtime/server.yaml" and done["understanding"]["slot"] is not None and done["understanding"]["turns"] == 4, done["map_from"])

# ---- a night whose calls say their slot and lane (llm/llama.py, f602): the moved calls and the turn's own waits read exactly
LANED = BASE / "20261112_1200_mage_2"
LANED.mkdir(parents=True)
laned = [dict(call(1, "interpret_action", 3000, 0, 900, 300), tokens={**call(1, "interpret_action", 3000, 0, 900, 300)["tokens"], "slot": 0, "lane": "foreground"}),
         dict(call(2, "interpret_action", 3000, 2500, 120, 300), tokens={**call(2, "interpret_action", 3000, 2500, 120, 300)["tokens"], "slot": 0, "lane": "foreground"}),
         dict(call(2, "narrate", 2000, 0, 500, 900), tokens={**call(2, "narrate", 2000, 0, 500, 900)["tokens"], "slot": 0, "lane": "foreground"}),   # moved
         dict(call(2, "npc_profile", 2000, 0, 500, 900, wait_ms=5000), tokens={**call(2, "npc_profile", 2000, 0, 500, 900, wait_ms=5000)["tokens"],
                                                                              "slot": 1, "lane": "background"})]          # its own wait, not the turn's
(LANED / "llm_calls.jsonl").write_text("\n".join(json.dumps(c) for c in laned) + "\n", encoding="utf-8")
(LANED / "turns.jsonl").write_text("\n".join(json.dumps(t) for t in [
    {"n": 1, "turn": 1, "seconds": 4.0, "first_word": 2.0, "background_calls": 0, "state": {"minutes": 480}},
    {"n": 2, "turn": 2, "seconds": 9.0, "first_word": 3.0, "background_calls": 1, "state": {"minutes": 960}}]) + "\n", encoding="utf-8")
ls = M.slots(M.load(LANED))
check("a call that says its slot: the moved one is counted from the call log, exactly",
      ls["lanes"] and ls["moved"] == 1 and ls["moved_from"] == "the call log", (ls["moved"], ls["moved_from"]))
check("...and a background call's own wait is not the turn's: the turn with background calls waited on none of its own",
      ls["split"]["with"]["calls"] == 2 and ls["split"]["with"]["most_ms"] == 0, ls["split"])

env = {**os.environ, "PYTHONUTF8": "1"}
r = subprocess.run([sys.executable, "tools/night_measure.py", str(RUN)], cwd=ROOT, capture_output=True, text=True, timeout=120, env=env)
check("the command reads the card from the run and prints both answers, every target figure marked an estimate",
      r.returncode == 0 and "### The two slots" in r.stdout and "### Births and situation rulings a game day" in r.stdout
      and "Measured on the RTX 4090" in r.stdout and "Seconds (RTX 3060 12GB, an estimate)" in r.stdout
      and "within a character's reach when born: 1 of 2" in r.stdout, (r.returncode, r.stdout[-900:], r.stderr[-600:]))
(RUN / "run.json").unlink()
r = subprocess.run([sys.executable, "tools/night_measure.py", str(RUN)], cwd=ROOT, capture_output=True, text=True, timeout=120, env=env)
check("...and a run that does not say its card is not passed off as the minimum card: it asks for --measured-on",
      r.returncode != 0 and "--measured-on" in (r.stdout + r.stderr), (r.returncode, r.stdout[-300:], r.stderr[-300:]))
shutil.rmtree(BASE, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
