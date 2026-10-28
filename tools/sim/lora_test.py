"""(f361) A night run's logs become training data: calls regrouped from their rows, accepted answers kept (minus the habits the game only
nudges), rejected drafts paired with the answers that replaced them, the newest run held out; the trainer's dry run checks the files
and writes the Modelfile; the evaluator scores logged and model answers the way the game judges them, through the gateway's client."""
import json, shutil, sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 1)
simlib.install(stub)
sys.path.insert(0, "tools")
import lora_dataset, lora_eval, lora_train
from llm import contracts
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

L = lora_dataset.L
check("the rules name a contract for every task, and a short prompt with a default", all(t in L["schemas"] for t in L["tasks"]) and "default" in L["short_system"]
      and all(hasattr(contracts, v) for v in L["schemas"].values()), [v for v in L["schemas"].values() if not hasattr(contracts, v)])

# ---- a fake pair of runs, logged the way the gateway logs (system prompts shortened, as before f361)
base = Path("saves/lora_test"); shutil.rmtree(base, ignore_errors=True)
SYS = "You are a townsperson. Many rules follow. [...shortened in log]"
def row(task, attempt, user, raw, error=None, retry_of=None):
    msgs = [{"role": "system", "content": SYS}, {"role": "user", "content": user}]
    if attempt:
        msgs += [{"role": "assistant", "content": "[previous answer - see the entry before this one]"}, {"role": "user", "content": f"That answer was rejected: {retry_of}"}]
    return json.dumps({"time": "t", "turn": 1, "task": task, "model": "m", "attempt": attempt, "seconds": 1.0, "messages": msgs, "raw": raw, "error": error})
U_TALK = "THE ONE IN FRONT OF YOU: the miller\nHOW YOU TALK:\n  - short sentences, one thing in each, none past twenty words\nPLAYER: Where is the mill?"
U_NARR = "PLACE: the yard\nEVENT: the player waits"
NUDGE = '\n\nYOUR DRAFT ENDED SENTENCES ON A TRAILING PARTICIPLE ("his hand resting on the hilt"; "her shoulders dropping"). End each sentence on its verb. Write it fresh, with the same events.'
long = json.dumps({"speech": "The mill is past the bridge and you take the left fork at the oak and then it is a mile or so on from there and you cannot miss it.", "intent": "small_talk"})
short = json.dumps({"speech": "The mill is past the bridge. Left at the oak.", "intent": "small_talk"})
draft = json.dumps({"text": "He nods, his hand resting on the hilt. She turns away, her shoulders dropping. The door shuts."})
clean = json.dumps({"text": "He nods and rests his hand on the hilt. She turns away. The door shuts."})
err = "this person speaks in short sentences, one thing in each, none past twenty words, and never one that runs on: no sentence over 20 words"
run1 = base / "run1"; run1.mkdir(parents=True)
(run1 / "llm_calls.jsonl").write_text("\n".join([
    row("npc_conversation", 0, U_TALK, long, err),
    row("populate_place", 0, "slots", json.dumps({"people": []})),                       # another call's row between the attempts (a background thread)
    row("npc_conversation", 1, U_TALK, short, None, err),
    row("narrate", 0, U_NARR, draft),
    row("narrate", 0, U_NARR + NUDGE, clean),                                            # the narrator's rewrite of the draft above
    row("narrate", 0, "PLACE: the gate", json.dumps({"text": "The gate stands open. Rain falls on the yard."})),
    row("npc_conversation", 0, "PLAYER: Hello", json.dumps({"speech": "Well, the mill is past the bridge.", "intent": "small_talk"})),
    row("interpret_action", 0, "PLAYER TYPED: I look around", json.dumps({"actions": [{"kind": "look"}]})),
    row("hire_chat", 0, "PLAYER: How far?", json.dumps({"speech": "It is... a way yet... a long way.", "gesture": ""})),
]) + "\n", encoding="utf-8")
run2 = base / "run2"; run2.mkdir()
(run2 / "llm_calls.jsonl").write_text("\n".join([
    row("narrate", 0, "PLACE: the inn", json.dumps({"text": "The fire is low. Nobody looks up."})),
    row("npc_conversation", 0, "PLAYER: Any work?", json.dumps({"speech": "Ask at the hall.", "intent": "small_talk"})),
]) + "\n", encoding="utf-8")

out = base / "data"
counts = lora_dataset.build([run1], [run2], out, prompts="short")
tr = counts["train"]
check("the retry pair: the rejected draft against the answer that passed, and that answer learned from", tr["npc_conversation"]["pairs (retry)"] == 1 and tr["npc_conversation"]["sft"] == 1
      and tr["npc_conversation"]["calls"] == 2, dict(tr["npc_conversation"]))
check("...a reply opening on 'Well,' is not learned from", tr["npc_conversation"]["dropped: stock opener"] == 1)
check("the narrator's rewrite: the draft is paired, not learned from; the rewrite and the clean passage are", tr["narrate"]["pairs (rewrite)"] == 1
      and tr["narrate"]["dropped: draft a rewrite replaced"] == 1 and tr["narrate"]["sft"] == 2, dict(tr["narrate"]))
check("a companion trailing off twice is not learned from", tr["hire_chat"]["dropped: trailing off"] == 1 and tr["hire_chat"]["sft"] == 0)
check("the interpreter's answer is", tr["interpret_action"]["sft"] == 1)
check("the held-out run lands under eval", counts["eval"]["narrate"]["sft"] == 1 and counts["eval"]["npc_conversation"]["sft"] == 1
      and (out / "eval" / "narrate.sft.jsonl").exists() and not (out / "train" / "hire_chat.sft.jsonl").exists())
sft = [json.loads(l) for l in (out / "train" / "narrate.sft.jsonl").read_text(encoding="utf-8").splitlines()]
check("an example carries the task's short system prompt and the request without the rewrite nudge",
      all(e["messages"][0]["content"] == L["short_system"]["narrate"] for e in sft) and all("YOUR DRAFT" not in e["messages"][1]["content"] for e in sft)
      and [e["messages"][2]["content"] for e in sft][0] == clean, sft)
pair = json.loads((out / "train" / "narrate.pairs.jsonl").read_text(encoding="utf-8").splitlines()[0])
check("the rewrite pair: the original request, the clean passage chosen, the draft rejected",
      pair["prompt"][1]["content"] == U_NARR and pair["chosen"][0]["content"] == clean and pair["rejected"][0]["content"] == draft)
summ = (out / "summary.md").read_text(encoding="utf-8")
check("the summary says what the pairs teach", "TRAILING PARTICIPLE" in summ and "short sentences" in summ and "| narrate |" in summ, summ[-600:])
full = lora_dataset.build([run1], [run2], base / "full", prompts="full")
check("with full prompts asked, a log that shortened them yields nothing, and says so",
      full["train"]["narrate"]["dropped: system prompt shortened in the log"] == 2 and full["train"]["narrate"]["sft"] == 0
      and not (base / "full" / "train").exists(), dict(full["train"]["narrate"]))

# ---- the trainer's dry run
code = lora_train.main(["--task", "narrate", "--data", str(out / "train"), "--out", str(base / "adapter"), "--dry-run"])
mf = (base / "adapter" / "Modelfile").read_text(encoding="utf-8") if (base / "adapter" / "Modelfile").exists() else ""
import config
check("the dry run checks the data and writes Ollama's Modelfile on the game's own model tag", code == 0 and f"FROM {config.MODEL}" in mf and "ADAPTER ./adapter" in mf, mf)
check("a file of the wrong shape is refused", lora_train.check_shape([{"messages": [{"role": "user", "content": "x"}]}], "sft")
      and lora_train.check_shape([{"prompt": [], "chosen": [{"content": "a"}], "rejected": [{"content": "a"}]}], "dpo"))
check("...and a pairs file of the right shape is not", lora_train.check_shape([pair], "dpo") == [])

# ---- the evaluator, through the gateway's client (the stub here)
rows, secs = lora_eval.evaluate(out / "eval" / "narrate.sft.jsonl", ["stub-model"])
check("the logged answers and each model's are scored the way the game judges them", set(rows) == {"logged", "stub-model"} and rows["logged"][0]["fits"] == 1
      and rows["logged"][0]["tails"] == 0 and stub.calls.get("Narration", 0) >= 1, (rows, dict(stub.calls)))
sc = lora_eval.score("npc_conversation", U_TALK + "\nnever asks the stranger anything back", long.replace("miss it.", "miss it, do you see?"), contracts.NPCReply)
check("the measurable parts of a kit are checked: a sentence past twenty words and a question from one who never asks", sc["kit"] == 2, sc)
tbl = lora_eval.table(rows, secs)
check("the table reads", tbl.startswith("| Model |") and "| logged |" in tbl and "| stub-model |" in tbl, tbl)

shutil.rmtree(base, ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
