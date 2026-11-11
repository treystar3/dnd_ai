"""(f585) Every live model call is sent a seed of its own: a hash of the campaign's seed, its count of inputs, the task, the call's place
among this input's calls of that task, and the try. So a measurement's two runs of an unchanged game, on the same card, mostly write
the same words for the same prompt, and a change is compared with less noise; every input, task, call and retry still has its own seed,
so play differs from line to line as before. The seed is a hash, never a draw: no die the game rolls moves. Outside a campaign (the
home page, creation) no seed is sent and the server draws its own, as creation's entropy is meant. The seed is not part of the
request the recorder fingerprints, so every kept recording replays unchanged. It narrows the noise between runs, it does not end it
(the card's own arithmetic, batching across slots and a draft model can still move a word), and the same seed writes differently on
another card.
Run: python tools/sim/request_seed_585_test.py"""
import random
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import streams
from llm import backend, gateway, llama, sampling
from llm.contracts import Narration

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the seed, as a hash of its parts
s = gateway.request_seed
base = s("7:3:look", "narrate", 0, 0)
check("the same parts give the same seed", base == s("7:3:look", "narrate", 0, 0) and isinstance(base, int) and 0 <= base < 2 ** 31, base)
check("...each part moves it: the campaign's seed, the count of inputs, the task, the place among the task's calls, the try",
      len({base, s("8:3:look", "narrate", 0, 0), s("7:4:look", "narrate", 0, 0), s("7:3:look", "hire_chat", 0, 0),
           s("7:3:look", "narrate", 1, 0), s("7:3:look", "narrate", 0, 1)}) == 6)
check("...but not the words typed: the same count of inputs is the same seed whatever was said", s("7:3:look", "narrate", 0, 0) == s("7:3:wait", "narrate", 0, 0))
check("outside a campaign there is none (the server draws its own)", s("unseeded", "narrate", 0, 0) is None and s("", "narrate", 0, 0) is None)

# ---- through the gateway: what each try is sent
seen = []


def layer(op, req, call):
    if op == "chat":
        seen.append((gateway._TASK.name, getattr(req.sampling, "seed", None)))
    return call(req)


undo = backend.wrap(layer, rank=60)
answers = iter(["not an object", {"text": "A cart turns in at the gate."}])     # the first answer is refused (not an object): a second try
stub_chat = stub.a_Narration if hasattr(stub, "a_Narration") else None
stub.a_Narration = lambda u, k: next(answers, {"text": "The gate stands open."})
streams.reset()
gateway.generate("narrate", "sys", "req", Narration)
check("(outside a campaign) a call is sent no seed", seen and all(seed is None for _, seed in seen), seen)
seen.clear()
answers = iter(["not an object", {"text": "A cart turns in at the gate."}])
streams.begin(7, 3, "look")
dice_before, global_before = streams.snapshot(), random.getstate()
gateway.generate("narrate", "sys", "req", Narration)
first = list(seen)
check("a try refused and tried again is sent another seed", len(first) == 2 and first[0][1] != first[1][1]
      and first[0][1] == s("7:3:look", "narrate", 0, 0) and first[1][1] == s("7:3:look", "narrate", 0, 1), first)
seen.clear()
gateway.generate("narrate", "sys", "req", Narration)
gateway.generate("hire_chat", "sys", "req", Narration)
check("the next call of the same task in this input has its own; another task counts from its own first",
      [x for _, x in seen] == [s("7:3:look", "narrate", 1, 0), s("7:3:look", "hire_chat", 0, 0)], seen)
check("no die the game rolls moved: the streams and the global random module are as they were", streams.snapshot() == dice_before
      and random.getstate() == global_before)
streams.begin(7, 4, "look")
seen.clear()
gateway.generate("narrate", "sys", "req", Narration)
check("a new input counts again from its first call", [x for _, x in seen] == [s("7:4:look", "narrate", 0, 0)], seen)
for between in ("nothing", "a reset with no call (a save reopened)"):
    if between != "nothing":
        streams.reset()
    streams.begin(7, 3, "look")
    seen.clear()
    answers = iter(["not an object", {"text": "A cart turns in at the gate."}])
    gateway.generate("narrate", "sys", "req", Narration)
    check(f"the same input begun again, with {between} between (a line given back and typed again): the same seeds as the first time",
          seen == first, (seen, first))
import json, tempfile, config
from pathlib import Path
was = config.LOG_PATH
config.LOG_PATH = str(Path(tempfile.mkdtemp(prefix="seed585_")) / "calls.jsonl")
streams.begin(7, 9, "look")
gateway.generate("narrate", "sys", "req", Narration)
rows = [json.loads(l) for l in Path(config.LOG_PATH).read_text(encoding="utf-8").splitlines() if l.strip()]
config.LOG_PATH = was
check("each try's seed is kept in the call log", rows and rows[-1].get("seed") == s("7:9:look", "narrate", 0, 0), rows[-1:] if rows else rows)
undo()

# ---- where it goes, and where it does not
samp = sampling.resolve("narrate", 0.9).at(0)
seeded = sampling.Sampling(temperature=samp.temperature, explicit=dict(samp.explicit), think=samp.think, seed=12345)
req = backend.ChatRequest(messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], schema=Narration,
                          sampling=seeded, max_tokens=50)
plain = backend.ChatRequest(messages=req.messages, schema=Narration, sampling=samp, max_tokens=50)
check("llama-server is sent the seed", llama.llama_body(req).get("seed") == 12345)
check("...and a call with none is sent no seed key (the server draws)", "seed" not in llama.llama_body(plain))
check("the recorder's request is the same with or without it: every kept recording replays unchanged",
      backend.neutral_request(req) == backend.neutral_request(plain) and "seed" not in str(backend.neutral_request(req)["sampling"]))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
