"""(f490) Bundle D's closing, measured against the baseline: every speech task has a prompt ceiling (data/measured/prompt_ceilings.yaml,
reported, never enforced), at or above the briefs a fixture builds for it and the largest prompt each golden sends; the gate prices the
goldens at expected answers and fails an input dearer than its pre-D price; the night's summary sets each speech task beside the
baseline's (first tries and their move in points, p95 beside the baseline's and the ceiling, cache hits) and says whether the closing's
size and acceptance marks held; the ceilings are set from a night's p95, never under a golden's, with the closing's marks kept as
written; and the hosting notes count the context caches by slot, not by run."""
import json
import shutil
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import config
import latency
from engine import canon, data_check

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

C = latency.ceilings()
tops = {t: (v or {}).get("chars") for t, v in (C.get("ceilings") or {}).items()}
speech = list(latency.speech_tasks())

# ---- every speech task has a ceiling, and the file passes the startup check
check("every speech task has a ceiling", speech and all(tops.get(t) for t in speech), sorted(set(speech) - set(tops)))
check("...and the ceilings file passes the startup check", data_check.ceilings_problems() == [], data_check.ceilings_problems())
check("...which refuses a speech task with none, and a ceiling for a task that is not one",
      any("no ceiling for the speech task mentor_chat" in b for b in data_check.ceilings_problems({"ceilings": {}, "closing": C.get("closing")}))
      and any("made_up" in b for b in data_check.ceilings_problems(dict(C, ceilings=dict(C["ceilings"], made_up={"chars": 10})))))

# ---- the briefs a fixture builds fit their ceilings
log = Path("saves/closing_490_calls.jsonl")
log.unlink(missing_ok=True)
config.LOG_PATH = str(log)
game = simlib.campaign("closing_490", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter("guild_house")
npc = sorted((n for n in ws.present if n.role not in ("guild_clerk", "guild_master")), key=lambda n: n.id)[0]
ws.inferred_offer(npc, "I'll pay you ten copper to help me load the grain onto the cart.")
canon.judge("I was born in Parth.", ["I grew up in a fishing village on a cold coast.", "My family were temple servants."])
ws.mentor_talk("Is the guild hard on newcomers?")
stub.plan = [{"kind": "talk", "target": npc.id, "speech": "Good morning. Any news in town?"}]
ws.turn('I say to them, "Good morning. Any news in town?"')
h1 = {"id": "h1", "name": "Bram Hollin", "role": "fighter", "level": 3, "permanent": True, "temper": ["blunt"], "blurb": "a scarred sellsword",
      "active": True}
ws.player.party, ws.player.party_mode = [h1], "with"
store.save_player(ws.player)
stub.plan = [{"kind": "talk", "target": "hire:h1", "speech": "Where did you learn to fight, Bram?"}]
ws.turn('I say to Bram, "Where did you learn to fight?"')
stub.plan = None
ws.exchange({"Bram": "a scarred sellsword", "Isel": "a quiet healer"}, "They wait out the rain.", [], (2, 3))
rows = [json.loads(l) for l in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
built: dict[str, int] = {}
for r in rows:
    if r.get("task") in tops and isinstance(r.get("chars"), int):
        built[r["task"]] = max(built.get(r["task"], 0), r["chars"])
check("the fixture builds a brief for the speech tasks no golden makes", {"work_offer_read", "canon_check", "mentor_chat"} <= set(built), sorted(built))
check("...and for the townsfolk, the hire and the party among themselves", {"npc_conversation", "hire_chat", "exchange"} <= set(built), sorted(built))
over = {t: (n, tops[t]) for t, n in built.items() if n > tops[t]}
check("every brief the fixture builds is at or under its task's ceiling", built and not over, over)
game.close()
shutil.rmtree("saves/closing_490", ignore_errors=True)
log.unlink(missing_ok=True)

# ---- the goldens fit their ceilings
gold = latency.golden_sizes()
check("the goldens make most of the speech tasks", len(gold) >= 8, sorted(gold))
over = {t: (n, w, tops.get(t)) for t, (n, w) in gold.items() if not tops.get(t) or n > tops[t]}
check("...and every prompt a golden sends is at or under its task's ceiling", not over, over)

# ---- the gate: an input dearer than its pre-D price fails it
check("an input priced above its pre-D price is dearer, one the baseline never priced too",
      latency.dearer({1: 43.7, 2: 18.4, 3: 5.0}, {1: 43.1, 2: 18.5}, {1, 2, 3}) == [(1, 43.1, 43.7), (3, None, 5.0)])
check("...to the tenth of a second the baseline keeps, and only for the inputs with a speech call",
      latency.dearer({1: 43.14, 2: 99.0}, {1: 43.1, 2: 18.5}, {1}) == [])
held = latency.gate()
check("the gate prices the three goldens (stub_fight since f495)", set(held) == {"stub_short", "stub_party", "stub_fight"}, sorted(held))
check("...and all hold it: no input with a speech call dearer than before Bundle D (stub_party since f488's hire brief, stub_fight since it was kept)",
      all(held.get(g) == [] for g in ("stub_short", "stub_party", "stub_fight")), held)
import yaml
import card_profile
now = dict(card_profile.estimate_inputs(latency.GOLDENS / "stub_short", expected=True))
cheaper = {"estimates": {"stub_short": {i: round(s - 0.5, 1) for i, s in now.items()}}}
failed = latency.gate(cheaper).get("stub_short") or []
check("a golden priced against a baseline half a second under today's fails at every priced input with a speech or a fight call (f510), and only those",
      failed and {i for i, _, _ in failed} == (latency.speech_inputs(latency.GOLDENS / "stub_short") | latency.fight_inputs(latency.GOLDENS / "stub_short")) & set(now), failed[:4])

# ---- the summary's rows against the baseline
night = [{"task": "npc_conversation", "attempt": 0, "chars": 20000, "error": None},
         {"task": "npc_conversation", "attempt": 0, "chars": 24000, "error": "rejected"},
         {"task": "npc_conversation", "attempt": 1, "chars": 24500, "error": None},
         {"task": "npc_conversation", "attempt": 0, "chars": 1000, "error": None},
         {"task": "hire_chat", "attempt": 0, "chars": 9000, "error": None, "tokens": {"prompt": 2000, "cached": 500}},
         {"task": "narrate", "attempt": 0, "chars": 5000, "error": None}]
was = {"tasks": {"npc_conversation": {"first_try": 0.952, "p95": 36345}, "hire_chat": {"first_try": 0.978, "p95": 16275}}}
marks = {"ceilings": {"npc_conversation": {"chars": 36500}, "hire_chat": {"chars": 8500}}, "closing": C["closing"]}
got = latency.against(night, was, marks)
check("a speech task's row: calls, first tries now and before and the move in points, p95 now, before and its ceiling, the most, cache hits",
      "| npc_conversation | 3 | 67% | 95% | -28 | 24000 | 36345 | 36500 | 24000 | - |" in got
      and "| hire_chat | 1 | 100% | 98% | +2 | 9000 | 16275 | 8500 | 9000 | 25% |" in got and not any("narrate" in r for r in got), got)
size = next((r for r in got if r.startswith("Size:")), "")
check("...the size mark: tasks at or below the baseline's p95, npc_conversation's against its mark, the tasks over their ceiling",
      "2 of 2 tasks at or below the baseline's p95" in size and "npc_conversation's p95 24000 against the mark of 14000, not held" in size
      and "over their ceiling: hire_chat" in size, size)
acc = next((r for r in got if r.startswith("Acceptance:")), "")
check("...and the acceptance mark, with the task that fell", "not held (npc_conversation -28)" in acc and "hire_chat" not in acc.split("not held")[1], acc)
run = Path(tempfile.mkdtemp(prefix="closing_490_"))
(run / "llm_calls.jsonl").write_text("\n".join(json.dumps(r) for r in night) + "\n", encoding="utf-8")
text = latency.summarise(run)
check("a night's summary.md carries the speech tasks against the baseline", "## Speech tasks against Bundle D's baseline" in text
      and "| npc_conversation | 3 | 67% | 95% | -28 |" in text, text[-600:])

# ---- the ceilings set from a night's p95, never under a golden's, the closing's marks kept as written
got = latency.ceilings_from([run], kept=C)
check("a ceiling from the night's p95, rounded up", got["npc_conversation"]["chars"] == 24000 and "the night's p95 24000" in got["npc_conversation"]["from"],
      got["npc_conversation"])
check("...never under the largest prompt a golden sends", got["hire_chat"]["chars"] >= gold["hire_chat"][0] and got["hire_chat"]["chars"] % 500 == 0,
      (got["hire_chat"], gold["hire_chat"]))
check("...and a task neither the night nor a golden measures keeps its ceiling", got["mentor_chat"] == C["ceilings"]["mentor_chat"], got.get("mentor_chat"))
real = latency.CEILINGS
latency.CEILINGS = run / "prompt_ceilings.yaml"
shutil.copy(real, latency.CEILINGS)
written = latency.write_ceilings([run])
latency.CEILINGS = real
again = yaml.safe_load(written)
check("the file written keeps its header and the closing's marks as written, comments and all",
      written.startswith("# (f490") and "# first-try acceptance within this many points" in written and again["closing"] == C["closing"]
      and again["ceilings"]["npc_conversation"]["chars"] == 24000, written[-500:])
shutil.rmtree(run, ignore_errors=True)

# ---- the hosting notes: caches by slot, not by run; the training notes: the prompt version, pre-D speech nights written off
hosted = Path("tools/HOSTED.md").read_text(encoding="utf-8")
check("HOSTED.md: each run at once is a server of its own (f529), no Ollama, and the two-speaker count still runs on the box",
      "each run at once adds its own context cache" not in hosted and "its own llama-server" in hosted and "ollama" not in hosted.lower()
      and "--mode addressees" in hosted)
lora = Path("tools/LORA.md").read_text(encoding="utf-8")
check("LORA.md names the prompt version and writes off the speech nights before Bundle D", "prompt_version" in lora and "written off" in lora)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
