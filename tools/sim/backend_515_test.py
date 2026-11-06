"""(f515) The game's own interface to the model, with an Ollama-shaped source behind it that sends exactly today's request.

- The request the source builds equals, key for key and in order, what the gateway sent before f515 (an oracle copied from it), for
  every task the budget knows, three tries, the night's temperature and repeat shifts on and off, and several answer lengths.
- One sampling plan: an untuned task keeps a 1.2 ceiling and sends no repeat penalty of its own (the base table's 1.0 is for
  llama-server, never in today's request); the tuned tasks send what the kept recordings hold.
- The turn's deadline reaches the source from the turn's own thread, and none from another.
- Layers, sources and lanes: each undo removes exactly its own; embeddings go through the interface with today's request.

Run: python tools/sim/backend_515_test.py"""

import gzip
import json
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import yaml
from pydantic import BaseModel

import config
from engine import budget, recording
from llm import backend, gateway, sampling
import simlib

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


class Read(BaseModel):
    x: str


# ---- the oracle: the gateway's request before f515, copied
def _oracle_shifted(task, base, top, tuned):
    add, rep = float(getattr(config, "TEMP_ADD", 0) or 0), float(getattr(config, "REPEAT_ADD", 0) or 0)
    if task in getattr(config, "BOT_TASKS", ()):
        return base, top, tuned
    if add and base >= getattr(config, "WARM_FROM", 0.5):
        base, top = min(1.5, base + add), min(1.5, top + add)
    if rep and "repeat_penalty" in tuned:
        tuned = dict(tuned, repeat_penalty=round(tuned["repeat_penalty"] + rep, 3))
    return base, top, tuned


def oracle(task, temperature, attempt, max_tokens, messages, schema):
    tuned = dict(getattr(config, "SAMPLING", {}).get(task, {}))
    base = tuned.pop("temperature", temperature)
    top = min(1.2, base + 0.1) if task in getattr(config, "SAMPLING", {}) else 1.2
    base, top, tuned = _oracle_shifted(task, base, top, tuned)
    return dict(model=config.OLLAMA_MODEL, think=config.THINK, messages=messages, format=schema.model_json_schema(),     # (f527) Ollama's tag
                options={"temperature": min(top, base + 0.15 * attempt), "num_ctx": config.NUM_CTX, "num_predict": max_tokens,
                         **gateway.threads(), **tuned},
                keep_alive=config.KEEP_ALIVE)


tasks = sorted(set((yaml.safe_load((ROOT / "data/rules/budget.yaml").read_text(encoding="utf-8")).get("tasks") or {}))
               | set(getattr(config, "SAMPLING", {})))
messages = [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}]
mismatch, compared = [], 0
saved = (config.TEMP_ADD, config.REPEAT_ADD, getattr(config, "NUM_THREAD", 0))
for temp_add, rep_add in ((0.15, 0.1), (0.0, 0.0), (0.3, 0.0)):
    for threads_n in (0, 6):
        config.TEMP_ADD, config.REPEAT_ADD, config.NUM_THREAD = temp_add, rep_add, threads_n
        for task in tasks:
            for temperature in (0.3, 0.8, 1.0):
                plan = sampling.resolve(task, temperature)
                for attempt in range(3):
                    for max_tokens in (800, 2048, 3000):
                        req = backend.ChatRequest(messages=messages, schema=Read, sampling=plan.at(attempt), max_tokens=max_tokens)
                        got, want = backend.ollama_kwargs(req), oracle(task, temperature, attempt, max_tokens, messages, Read)
                        compared += 1
                        if got != want or list(got) != list(want) or list(got["options"]) != list(want["options"]):
                            mismatch.append((task, temp_add, rep_add, threads_n, temperature, attempt, max_tokens))
config.TEMP_ADD, config.REPEAT_ADD, config.NUM_THREAD = saved
check(f"the source's request equals the gateway's before f515, key for key and in order ({compared} compared, {len(tasks)} tasks)",
      not mismatch and compared > 1000, mismatch[:5])

# ---- the recorder's fingerprint covers exactly what is sent
config.NUM_THREAD = 6
req = backend.ChatRequest(messages=messages, schema=Read, sampling=sampling.resolve("narrate", 0.8).at(1), max_tokens=2048)
sent, neutral = backend.ollama_kwargs(req), backend.neutral_request(req)
h6 = recording.request_hash(neutral)
config.NUM_THREAD = 0
check("(f527) the neutral request holds nothing of the machine: the thread count and the context the Ollama request carries are not in it",
      "num_thread" in sent["options"] and "num_ctx" in sent["options"] and "num_thread" not in json.dumps(neutral) and "num_ctx" not in json.dumps(neutral)
      and set(neutral) == {"model", "messages", "schema", "schema_sha", "sampling", "max_tokens", "think", "voice"}, neutral.keys())
check("...so the recorder's fingerprint is the same whatever the thread count", recording.request_hash(backend.neutral_request(req)) == h6)
config.NUM_THREAD = saved[2]

# ---- one sampling plan
untuned = next(t for t in tasks if t not in config.SAMPLING and t not in config.BOT_TASKS)
p = sampling.resolve(untuned, 0.8)
check(f"an untuned task ({untuned}) keeps a 1.2 ceiling (before the night's warm shift) and sends no sampler value of its own",
      p.ceiling == min(1.5, 1.2 + (config.TEMP_ADD if 0.8 >= config.WARM_FROM else 0)) and p.explicit == {}, p)
req = backend.ChatRequest(messages=messages, schema=Read, sampling=p.at(0), max_tokens=800)
check("...so today's request carries none of the base table's keys", set(backend.ollama_kwargs(req)["options"]) <= {"temperature", "num_ctx", "num_predict", "num_thread"},
      backend.ollama_kwargs(req)["options"])
check("...while the table for llama-server gives it repeat 1.0 over 64, top_k 64, top_p 0.95, min_p 0",
      {k: p.at(0).resolved()[k] for k in ("repeat_penalty", "repeat_last_n", "top_k", "top_p", "min_p")}
      == {"repeat_penalty": 1.0, "repeat_last_n": 64, "top_k": 64, "top_p": 0.95, "min_p": 0.0})
recorded = {}
for f in sorted((ROOT / "data/replay/sessions").glob("*/calls.jsonl.gz")):
    for line in gzip.open(f, "rt", encoding="utf-8"):
        row = json.loads(line)
        rp = ((row.get("request") or {}).get("sampling") or {}).get("repeat_penalty")     # (f527) the neutral row: every sampler, the base under
        if row.get("kind") == "chat" and rp is not None:
            recorded.setdefault(row.get("task"), set()).add(rp)
planned = {t: {sampling.resolve(t, 0.8).at(0).resolved()["repeat_penalty"]} for t in recorded}
check(f"the tuned tasks' repeat penalties are what the kept recordings hold ({', '.join(f'{t} {sorted(v)}' for t, v in sorted(recorded.items()))})",
      recorded and planned == recorded, (planned, recorded))

# ---- the turn's deadline reaches the source from the turn's thread only
seen = []


class Fake:
    name = "fake"

    def chat(self, req, deadline=None):
        seen.append(deadline)
        return backend.Reply(text='{"x": "ok"}', finish="stop", usage=None)


before = backend.source()
undo = backend.use(Fake())
required = next(t for t, v in (yaml.safe_load((ROOT / "data/rules/budget.yaml").read_text(encoding="utf-8")).get("tasks") or {}).items()
                if (v or {}).get("need") == "required")
b = budget.open(limit=60)
got = gateway.generate(required, "Read the offer.", "Morning.", Read, retries=0)
turn_deadline = seen[-1] if seen else "none"
out = {}
t = threading.Thread(target=lambda: out.update(r=gateway.generate(required, "Read the offer.", "Morning.", Read, retries=0)))
t.start()
t.join()
other_deadline = seen[-1] if len(seen) > 1 else "none"
budget.close()
undo()
check("a generate() goes through the interface and reads the reply", got.x == "ok" and out.get("r") is not None and out["r"].x == "ok")
check("...with the turn's deadline when made on the turn's thread", isinstance(turn_deadline, float) and 0 < turn_deadline <= 60, turn_deadline)
check("...and none when made on another thread", other_deadline is None, other_deadline)
check("...and the source put back is the Ollama-shaped one it replaced", backend.source() is before and isinstance(before, backend.OllamaShape),
      (backend.source(), before))

# ---- layers, lanes
calls = []
u1 = backend.wrap(lambda op, r, call: (calls.append(("outer", op)), call(r))[1], rank=10)
u2 = backend.wrap(lambda op, r, call: (calls.append(("inner", op)), call(r))[1], rank=20)
undo = backend.use(Fake())
backend.chat(messages, Read, sampling.resolve("narrate", 0.8).at(0), 100)
check("layers are called outermost by rank, then the source", calls == [("outer", "chat"), ("inner", "chat")], calls)
u1()
check("...and an undo removes exactly its own layer", len(backend.layers()) == 1)
u2()
undo()
check("...leaving none", backend.layers() == [])
check("the lane is foreground unless a thread says otherwise", backend.current_lane() == "foreground")
with backend.lane("background"):
    inner = backend.current_lane()
check("...and a block names its lane, then puts it back", inner == "background" and backend.current_lane() == "foreground")

# ---- embeddings through the interface, with today's request
asked = []


class EmbedClient:
    def embed(self, **k):
        asked.append(k)
        return {"embeddings": [[1.0, 0.0] for _ in k["input"]]}


undo_embed = backend.use(backend.OllamaShape(client=EmbedClient()))   # (f518) real play's embedder path, on a fake client
vec = backend.embed(["clustering: a", "clustering: b"])
undo_embed()
check("an embedding goes through the interface and the Ollama-shaped source, and returns the vectors", vec.vectors == [[1.0, 0.0], [1.0, 0.0]]
      and len(asked) == 1, (vec, asked))
check("...and taking it away puts the default Ollama-shaped source back", backend.source() is before)
check("...asked with today's request (the embed model, the texts as given, keep-alive), exactly the embedder's arguments",
      asked and asked[0]["model"] == config.OLLAMA_EMBED_MODEL and asked[0]["input"] == ["clustering: a", "clustering: b"]
      and asked[0]["keep_alive"] == config.KEEP_ALIVE and asked[0] == backend.embed_kwargs(["clustering: a", "clustering: b"])
      and list(asked[0]) == list(backend.embed_kwargs(["clustering: a", "clustering: b"])), asked)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
