"""(f793) B3's first step (docs/design/36_b3_plain_prose.md): a task named in data/rules/prose.yaml plain_text is answered as plain
text, with no grammar and with a stop list, the narrator's one sentence about JSON swapped for one about the passage, and the text
wrapped into its contract the moment it arrives, so every check that reads an answer reads it as before. The switch ships empty (off),
and off, a request is what it was. The owner on 2026-11-22: "okay let's begin B3 then", and "Yes, recommended answers".
The case that found it: the narration of a turn (`narrate`). Second cases of the kind: the other three narration tasks share the
sentence and the contract; each shape a plain answer can come in wrong is sent back with its reason and the passage asked for again,
never JSON; the game's own gate, the content guard and undash read a wrapped answer as a JSON one; a cut-off is asked for again as a
passage; the stand-in and the recorder carry the flag; and data_check refuses a task that cannot be plain.
Run: python tools/sim/plain_prose_793_test.py"""
import json
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 1)
simlib.install(stub)

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


from llm import backend, gateway, llama, plain                 # noqa: E402
from llm.contracts import Narration                             # noqa: E402
from llm.sampling import Sampling                               # noqa: E402
from scenes import world_prompts, combat_prompts                # noqa: E402

JSON_LINE = 'Respond only with JSON matching the schema, with the prose in "text".'
check("the switch ships off: no task is plain", plain.RULES["plain_text"] == [], plain.RULES["plain_text"])
check("the narration tasks may be plain, each with its contract", {t: c for t, c in plain.RULES["can_be_plain"].items()}
      == {"narrate": "Narration", "combat_opening": "Narration", "combat_narrate": "Narration", "combat_aftermath": "Narration"},
      plain.RULES["can_be_plain"])
check("...and the narration's contract names its one prose field", plain.field_of(Narration) == "text")
for name, text in (("the narrator's", world_prompts.NARRATOR_SYSTEM), ("the fight's round", combat_prompts.NARRATE_SYSTEM),
                   ("the fight's aftermath", combat_prompts.AFTERMATH_SYSTEM)):
    check(f"{name} prompt holds the one sentence the switch swaps, once", text.count(JSON_LINE) == 1, text[-200:])
check("...and so does the fight's opening", combat_prompts.START_SYSTEM.count(JSON_LINE) == 1, combat_prompts.START_SYSTEM[-120:])

# ---- the request
req = backend.ChatRequest(messages=[{"role": "user", "content": "x"}], schema=Narration, sampling=Sampling(temperature=0.7), max_tokens=300)
body = llama.llama_body(req)
check("off, a request carries its grammar and no stop list, as before", "grammar" in body and "stop" not in body, sorted(body))
check("...and its neutral form has no plain flag, so its fingerprint is what it was", "plain" not in backend.neutral_request(req))
preq = backend.ChatRequest(messages=req.messages, schema=Narration, sampling=Sampling(temperature=0.7), max_tokens=300, plain="text")
pbody = llama.llama_body(preq)
check("a plain request has no grammar and has the stop list", "grammar" not in pbody and pbody.get("stop") == plain.RULES["stop"], sorted(pbody))
check("...the same room to write (no limit added)", pbody["n_predict"] == body["n_predict"], (pbody["n_predict"], body["n_predict"]))
check("...and its neutral form says plain, so it is fingerprinted apart", backend.neutral_request(preq).get("plain") == "text")
check("the stand-in's request says plain too", backend.legacy_kwargs(preq).get("plain") == "text" and "plain" not in backend.legacy_kwargs(req))

# ---- the call, through the gateway with a stand-in that answers in turn
SEEN = []
ANSWERS = []


def answer(**k):
    SEEN.append(k)
    text = ANSWERS.pop(0) if ANSWERS else "You stand in the rain."
    return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content=text))


held = simlib.stand_in(chat=answer)
SYSTEM = world_prompts.NARRATOR_SYSTEM


def told(answers, task="narrate", on=True):
    SEEN.clear()
    ANSWERS[:] = list(answers)
    plain.RULES["plain_text"] = [task] if on else []
    try:
        return gateway.generate(task, SYSTEM, "GAME EVENT: the player looks around.", Narration, retries=2)
    finally:
        plain.RULES["plain_text"] = []


r = told(["You stand at the edge of the square, rain on the cobbles."])
check("the case: a plain narration is taken as the passage", isinstance(r, Narration) and r.text == "You stand at the edge of the square, rain on the cobbles.",
      getattr(r, "text", r))
sys0 = SEEN[0]["messages"][0]["content"] if SEEN else ""
check("...asked as plain, its prompt's JSON sentence swapped for the passage's", SEEN and SEEN[0].get("plain") == "text"
      and JSON_LINE not in sys0 and sys0.count(plain.RULES["plain_line"]) == 1, sys0[-200:])
r = told([json.dumps({"text": "You look around."})], on=False)
check("off: the same call is asked as JSON, its prompt as written", SEEN and "plain" not in SEEN[0] and SEEN[0]["messages"][0]["content"] == SYSTEM)
for task in ("combat_opening", "combat_narrate", "combat_aftermath"):
    r = told(["Steel rings in the clearing."], task=task)
    check(f"{task} goes plain the same way", getattr(r, "text", "") == "Steel rings in the clearing." and SEEN[0].get("plain") == "text", r)

for wrong, what in (("Here is the narration: You walk in.", "a label"), ('"You walk in under the arch."', "quotes"),
                    ("## The Square\nYou walk in.", "a heading"), ('{"text": "You walk in."}', "JSON"),
                    ("You walk in.\n\n(Note: I kept it short.)", "a note"), ("", "nothing")):
    r = told([wrong, "You walk in under the arch."])
    retry = SEEN[1]["messages"][-1]["content"] if len(SEEN) > 1 else ""
    check(f"a passage with {what} is sent back, and the passage asked for again, never JSON",
          getattr(r, "text", "") == "You walk in under the arch." and len(SEEN) == 2 and "JSON" not in retry and "passage" in retry, (r, retry))

for wrong, what in (("```\nYou walk in.\n```", "a code block"), ("You walk in.\n- the rain\n- the cobbles", "bullets"),
                    ("**The Square**\nYou walk in.", "a bold heading"), ("Here’s the narration: You walk in.", "a curly label")):
    r = told([wrong, "You walk in under the arch."])
    check(f"...and so is one with {what}", getattr(r, "text", "") == "You walk in under the arch." and len(SEEN) == 2, (r, len(SEEN)))

# ---- real passages, whose own words look like a wrapper's, pass at the first try (the shapes name the wrapper, never the passage)
for real in ("Sure enough, the latch gives: beyond it, a stair winds down into the dark.",
             "Here is where the road ends: a ring of standing stones, leaning together like old men.",
             "Of course the ferryman wants more: two silver, and he does not meet your eye.",
             "The passage narrows: you squeeze through sideways, stone cold against your back.",
             '"Down!" Bram hauls you behind the cart as the bolt strikes the wood. "Stay there."',
             "“Down!” Bram hauls you behind the cart. “Stay there.”",
             "The wolves are gone.\n\n* * *\n\nMorning finds you stiff and cold.",
             "The sign on the door reads Note: closed for the burial, and the shutters are drawn.",
             '"Okay," Bram says, and the ferry pushes off.'):
    r = told([real, "a second try that should never be asked for"])
    check(f"a real passage passes at once: {real[:48]!r}", getattr(r, "text", "") == real.strip() and len(SEEN) == 1, (getattr(r, "text", r), len(SEEN)))

r = told(["You walk in — the rain follows."])
check("undash reads a wrapped answer as a JSON one", getattr(r, "text", None) is not None and "—" not in r.text, getattr(r, "text", r))
r = told(["You walk in. mud_r_road gleams.", "You walk in, the cobbles gleaming."])
check("the game's output gate sends back a leak in a plain answer", getattr(r, "text", "") == "You walk in, the cobbles gleaming." and len(SEEN) == 2,
      (getattr(r, "text", r), len(SEEN)))
r = told(["It sits among the rocks, watching you avec a steady focus.", "It sits among the rocks, watching you with a steady focus."])
check("the content guard sends back a foreign word in a plain answer", getattr(r, "text", "").endswith("with a steady focus.") and len(SEEN) == 2,
      (getattr(r, "text", r), len(SEEN)))
from engine import phantoms                                    # noqa: E402
phantoms.use(lambda: ["dragon", "wolf"])                         # the world's creatures, as the game gives them
r = told(["A dragon lands on the roof beside you, wings folding.", "Rain drums on the roof beside you."])
phantoms.use(None)
check("...and the phantom check, a creature the game does not have here", getattr(r, "text", "") == "Rain drums on the roof beside you." and len(SEEN) == 2,
      (getattr(r, "text", r), len(SEEN)))


def cut(**k):
    SEEN.append(k)
    if len(SEEN) == 1:
        return types.SimpleNamespace(done_reason="length", message=types.SimpleNamespace(content="You walk in and the"))
    return types.SimpleNamespace(done_reason="stop", message=types.SimpleNamespace(content="You walk in."))


held()
held = simlib.stand_in(chat=cut)
SEEN.clear()
plain.RULES["plain_text"] = ["narrate"]
try:
    r = gateway.generate("narrate", SYSTEM, "GAME EVENT: x", Narration, retries=2)
finally:
    plain.RULES["plain_text"] = []
retry = SEEN[1]["messages"][-1]["content"] if len(SEEN) > 1 else ""
check("a cut-off plain passage is asked for again as a passage, never JSON", getattr(r, "text", "") == "You walk in." and "JSON" not in retry, retry)
held()

# ---- the stand-in the suite plays with
k = dict(model="m", think=False, messages=[{"role": "user", "content": "x"}], format=Narration.model_json_schema(), options={}, plain="text")
got = stub.chat(**k).message.content
check("the suite's stand-in answers a plain request with the passage alone", got and not got.lstrip().startswith("{"), got)
k.pop("plain")
check("...and a JSON request as JSON, as before", stub.chat(**k).message.content.lstrip().startswith("{"))

# ---- the data check
from engine import data_check                                   # noqa: E402
saved = json.loads(json.dumps(plain.RULES))
plain.RULES["plain_text"] = ["npc_conversation"]
probs = data_check.plain_problems(plain.RULES)
check("data_check refuses a task in plain_text that cannot be plain", any("npc_conversation" in p for p in probs), probs)
plain.RULES.clear(); plain.RULES.update(saved)
plain.RULES["can_be_plain"] = {**plain.RULES["can_be_plain"], "exchange": "Exchange"}
probs = data_check.plain_problems(plain.RULES)
check("...and a contract that names no prose field", any("Exchange" in p for p in probs), probs)
plain.RULES.clear(); plain.RULES.update(saved)
check("...and the shipped file passes", data_check.plain_problems(plain.RULES) == [], data_check.plain_problems(plain.RULES))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
