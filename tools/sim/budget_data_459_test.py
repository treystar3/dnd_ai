"""(f459) The turn budget's data, the stand-in lines, the measurement's new home, the owner's definitions, and the re-bless printout.
Bundle C's first feature changes no behaviour in play: it lays down the numbers the budget will read (data/rules/budget.yaml, with the one
table of the model's tasks every per-task list is now checked against), the plain lines that tell an outcome that stood when its passage
could not be written (data/rules/failures.yaml, engine/failures.py), moves the card's measured speeds out of the data hash
(data/measured/card_profile.yaml), writes the owner's 60 s definition and the Bundle C decisions into GOALS.md, teaches the recorder to
keep the shown lines and the re-bless to say what moved, and stops a replay's parting from being swallowed in work_offer_read."""
import copy, gzip, json, pathlib, random, shutil, subprocess, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 59))
import config
import yaml
from engine import data_check, failures, ledger
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- budget.yaml and the task table
B = yaml.safe_load(pathlib.Path("data/rules/budget.yaml").read_text(encoding="utf-8"))
check("budget.yaml loads, with the owner's limit and the retention numbers", B["limit_seconds"] == 60 and B["retention"]["operations"] > 0 and B["retention"]["deferred_turns"] > 0)
problems = data_check.check()
check("the startup check is clean on the tree as it stands", not problems, problems[:5])
found = data_check.task_literals()
check("every task the code calls is in the table, and every task in the table is called", set(found) == set(B["tasks"]), (sorted(set(found) ^ set(B["tasks"]))))
check("...and the understanding, the outcome and the passage are required while party talk and the pulse are optional",
      all(B["tasks"][t]["need"] == "required" for t in ("interpret_action", "narrate", "npc_conversation", "combat_narrate", "ruling"))
      and all(B["tasks"][t]["need"] == "optional" for t in ("exchange", "dialogue_frame", "pulse_thread", "event_judge")) and B["tasks"]["exchange"]["later"] == "deferred")
b2 = copy.deepcopy(B); b2["tasks"].pop("narrate")
check("a task the code calls that the table does not know fails the check", any("narrate" in p and "does not know" in p for p in data_check.budget_problems(b2, found)), data_check.budget_problems(b2, found)[:3])
b3 = copy.deepcopy(B); b3["tasks"]["nobody_calls_this"] = {"need": "optional", "later": "dropped", "answer_tokens": 10}
check("...as does a task nobody calls", any("nobody_calls_this" in p for p in data_check.budget_problems(b3, found)))
b4 = copy.deepcopy(B); b4["tasks"]["narrate"]["later"] = "dropped"; b4["tasks"]["exchange"].pop("later")
check("...a required task with a later, and an optional one without", sum("later" in p for p in data_check.budget_problems(b4, found)) >= 2)
b5 = copy.deepcopy(B); b5["floor_seconds"] = 59
check("...and a floor that leaves no room under the limit", any("room under the limit" in p for p in data_check.budget_problems(b5, found)))
A = yaml.safe_load(pathlib.Path("data/rules/audit_log.yaml").read_text(encoding="utf-8"))["tasks"]
check("the audit log explains every task, the nine it had missed included", set(A) >= set(B["tasks"]) and all(t in A for t in ("combat_aftermath", "ruling", "thread_telling", "named_spell")))
L = yaml.safe_load(pathlib.Path("data/rules/lora.yaml").read_text(encoding="utf-8"))
H = yaml.safe_load(pathlib.Path("data/rules/hygiene.yaml").read_text(encoding="utf-8"))
check("the voice lists, the narrator's tasks and the sampling table name only tasks the table knows",
      set(L["prose_tasks"] + L["speech_tasks"]) <= set(B["tasks"]) and set(H["narrator_tasks"]) <= set(B["tasks"]) and set(config.SAMPLING) <= set(B["tasks"]))

# ---- the stand-in lines
F = failures.F
check("failures.problems() accepts the new lists on the tree as it stands", failures.problems() == [], failures.problems()[:4])
check("...with a stood list for every kind of ledger row", set(F["stood"]) == set(ledger.KINDS))
rng = random.Random(3)
got = failures.stood_lines([{"kind": "gained", "facts": {"what": "a healing draught"}}, {"kind": "paid", "facts": {"who": "Tam the herbalist", "amount": "12 copper"}}], rng)
check("stood_lines fills the facts into one line per row", len(got) == 2 and "a healing draught" in got[0] and "Tam the herbalist" in got[1] and "12 copper" in got[1] and "{" not in "".join(got), got)
plain = failures.stood_lines([{"kind": "gained"}, {"kind": "nothing_of_the_kind"}], rng)
check("...a row with no facts, or of no known kind, is told by stood_any", len(plain) == 2 and all(l in F["stood_any"] for l in plain), plain)
draws = [failures.stood_lines([{"kind": "found", "facts": {"what": "a cache"}}], rng)[0] for _ in range(20)]
check("...and never the same line twice running", all(a != b for a, b in zip(draws, draws[1:])), draws[:4])
v = failures.victory_stood({"xp": "40"}, rng)
check("part_stood names what stood; shown_later, round_stood and goddess_silent stand alone; victory_stood takes the win's facts",
      "the herbs bought" in failures.part_stood("the herbs bought", rng) and failures.shown_later(rng) in F["shown_later"] and failures.round_stood(rng) in F["round_stood"]
      and failures.goddess_silent(rng) in F["goddess_silent"] and ("40" in v or v in F["victory_stood"]) and "{" not in v, v)
d = copy.deepcopy(F)
d["stood"]["gained"] = d["stood"]["gained"][:5] + ["{item} is yours."]
d["part_stood"][0] = "Part of that stood {done. The rest did not."
d["shown_later"][0] = "Before you left - this much had happened."
d["round_stood"][0] = "The model failed; the round stands."
d["victory_stood"][0] = d["victory_stood"][1]
d["goddess_silent"] = d["goddess_silent"][:4]
d["stood"]["bogus"] = list(F["stood_any"])
bad_ = failures.problems(d)
check("problems() rejects an unfillable placeholder, a brace left over, a dash, a machinery word, a duplicate, a short list and an unknown kind",
      any("{item}" in p or "cannot fill" in p for p in bad_) and any("brace" in p or "cannot be filled" in p for p in bad_) and any("dash" in p for p in bad_)
      and any("machinery" in p for p in bad_) and any("twice" in p for p in bad_) and any("goddess_silent" in p and "at least 6" in p for p in bad_)
      and any("stood.bogus" in p for p in bad_), bad_)
check("lines() is still the two old lists, and no stand-in is among them", set(failures.lines()) == set(F["turn_not_taken"]) | set(F["turn_not_possible"])
      and not (set(failures.lines()) & set(F["stood_any"]) | set(failures.lines()) & set(F["shown_later"])))
sys.path.insert(0, "tools")
import nightrun
check("...so the night never counts a survived narration failure as a hesitation", not any(l in nightrun.HESITATIONS for l in F["stood_any"] + F["part_stood"] + F["shown_later"]))

# ---- the measurement outside the data hash
check("the profile lives under data/measured and data/rules has none", pathlib.Path("data/measured/card_profile.yaml").exists() and not pathlib.Path("data/rules/card_profile.yaml").exists())
import card_profile
before = statehash.data_hash()
prof = pathlib.Path("data/measured/card_profile.yaml")
kept = prof.read_text(encoding="utf-8")
try:
    card_profile.write({"calls": 1, "turns": 1, "read_tps": 1.0, "write_tps": 1.0, "load_s": 0.0, "median_turn_s": 1.0, "p95_turn_s": 1.0, "longest_turn_s": 1.0, "over": []},
                       "RTX 3060 12GB", "gemma4:12b", "a test")
    check("rewriting the measurement moves no data hash", statehash.data_hash() == before and prof.read_text(encoding="utf-8") != kept)
finally:
    prof.write_text(kept, encoding="utf-8")
check("card_profile judges 'over budget' against the limit read from budget.yaml", card_profile.BUDGET == 60.0 and card_profile.budget_limit() == B["limit_seconds"])
golden = json.loads(pathlib.Path("data/replay/sessions/stub_short/meta.json").read_text(encoding="utf-8"))
check("the golden was made on this data: its hash is the tree's", golden["data"] == statehash.data_hash(), (golden["data"][:12], statehash.data_hash()[:12]))

# ---- GOALS.md carries the owner's definition and the Bundle C decisions
goals = pathlib.Path("GOALS.md").read_text(encoding="utf-8")
check("GOALS.md carries the 60 s definition and the Bundle C decisions as the owner's", "within 60 seconds of model time on the RTX 3060" in goals
      and "each action of a typed line is its own operation" in goals and goals.index("within 60 seconds of model time") < goals.index("A turn the game cannot take leaves nothing behind"))

# ---- a replay's parting passes through work_offer_read
from core.interrupts import Interrupt
from scenes import work_actions
g = simlib.campaign("budget_data_459", seed=59, location="trading_square")
ws = g.scene
class Parted(Interrupt):
    pass
def chat(**k):
    raise Parted("the replay parted here")
parting = simlib.stand_in(chat=chat)       # (f518) the source that parts on every call, where the client was swapped before
npc = (ws.residents or [None])[0] or next(iter(ws.store.npc_rows(gone=False)), None)
try:
    try:
        ws.inferred_offer(npc, "There is work for you here, and pay.") if npc is not None else None
        passed = npc is None
    except Parted:
        passed = parting.live() and sum(parting.src.calls.values()) >= 1     # the parting came from the call that reached it
    except Exception as e:
        passed = False
        why = repr(e)
finally:
    parting()
check("a replay's parting raised inside work_offer_read reaches the caller", passed, locals().get("why", ""))
check("...and the parting source is taken away again (f518)", not parting.live())
g.close()
shutil.rmtree("saves/budget_data_459", ignore_errors=True)

# ---- the recorder keeps the shown lines, and a re-bless names the line that moved
from engine import recording
rec_a, rec_b = pathlib.Path("saves/budget_459_rec_a"), pathlib.Path("saves/budget_459_rec_b")
for p in (rec_a, rec_b):
    shutil.rmtree(p, ignore_errors=True)
import rerun
def make(folder, text):
    folder.mkdir(parents=True)
    (folder / "meta.json").write_text(json.dumps({"seed": 1}), encoding="utf-8")
    (folder / "inputs.jsonl").write_text(json.dumps({"i": 1, "main": True, "text": "look"}) + "\n", encoding="utf-8")
    with gzip.open(folder / "calls.jsonl.gz", "wt", encoding="utf-8") as f:
        f.write(json.dumps({"i": 0, "input": 1, "kind": "chat", "title": "Narration", "req": "a" if "old" in text else "b"}) + "\n")
    (folder / "turns.jsonl").write_text(json.dumps({"i": 1, "state": {"all": "x", "kv": "k"}, "outcomes": [], "shown": text, "lines": 2, "shown_text": ["A quiet lane.", text]}) + "\n", encoding="utf-8")
make(rec_a, "the old line"); make(rec_b, "the new line")
import io, contextlib
out = io.StringIO()
with contextlib.redirect_stdout(out):
    rerun.report_rebless(rerun.load(rec_a), rerun.load(rec_b))
text = out.getvalue()
check("--rebless's report names the input whose words moved, the line that moved and the request that differs",
      "shown words differ: [1]" in text and "'the old line' -> 'the new line'" in text and "request differs: 1" in text and "state differs from the kept recording: none" in text, text)
for p in (rec_a, rec_b):
    shutil.rmtree(p, ignore_errors=True)
g2 = simlib.campaign("budget_459_shown", seed=59)
import ui.console as uc
uc.ask = (lambda script: (lambda *a, main=False, **k: (script.pop(0) if main and script else "quit") if main else "yes"))(["I look around."])
simlib.quiet_console()
OUT = pathlib.Path("saves/budget_459_shown_out"); shutil.rmtree(OUT, ignore_errors=True)
g2.session.record(folder=OUT)
g2.scene.run()
g2.close()
turns = [json.loads(l) for l in (OUT / "turns.jsonl").read_text(encoding="utf-8").splitlines()]
check("the recorder keeps every input's shown lines beside their hash", turns and all("shown_text" in t and isinstance(t["shown_text"], list) for t in turns), turns[:1])
shutil.rmtree(OUT, ignore_errors=True); shutil.rmtree("saves/budget_459_shown", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
