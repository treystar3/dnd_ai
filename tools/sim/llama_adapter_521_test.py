"""(f521) The llama-server adapter, against tools/sim/fake_llama.py (an in-process server on a free loopback port).

- The body is pure: the same request and machine give the same bytes; a request field changes the request's own fingerprint, a machine
  field (the slot) changes the body and never the fingerprint.
- Every sampler is sent, the base table under the task's own values, so none of llama-server's defaults apply: hire_chat at repeat
  1.22 with top_k 64 and min_p 0, an untuned task at repeat 1.0 over 64. Thinking is off on every request unless the task was chosen
  to think, which then gets its room. A voice sends its adapter; a voice with none is invalid.
- Each status on its kind: a 503 while loading is waited on and is no try (three of them then an answer is one answer, under a deadline
  shorter than the wait), and too long a load is 'loading'; 400 past the context is too_big; any other 400 and a keyless 401 are
  invalid; a schema the grammar refuses (500) is invalid; an embed text past the batch (500) is too_big; any other 500 is the server's;
  refused and dropped connections are unreachable.
- A cancel from another thread ends the call as cancelled within 1.5 s, and the server sees the caller hang up; an expired deadline is
  deadline; a 'length' answer that filled the slot is full, one that did not is not.
- usage: prompt counts the cached tokens too, wait_ms is never negative, load_ms is gone.
- No proxy setting is ever used; the key goes with every request; embeddings come back in the order asked.
- The switch: DND_BACKEND=llama makes a llama-server at DND_LLAMA_URL the default source (only on this machine); otherwise (f528) the
  game's own runtime, unstarted until the game or a tool starts it.
- data_check refuses a misspelt sampler key, a value out of range, and a fraction where a whole number belongs.

Run: python tools/sim/llama_adapter_521_test.py"""

import os
import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools" / "sim"))

from pydantic import BaseModel

import config
from fake_llama import FakeLlama
from llm import backend, gateway, llama, sampling
from llm.errors import Cancelled, Failure

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


class Read(BaseModel):
    x: str


def req(task="stranger_read", temperature=0.1, attempt=0, max_tokens=60, text="hello", voice=None):
    plan = sampling.resolve(task, temperature)
    return backend.ChatRequest(messages=[{"role": "system", "content": "sys"}, {"role": "user", "content": text}], schema=Read,
                               sampling=plan.at(attempt), max_tokens=max_tokens, voice=voice)


def kind_of(fn):
    try:
        fn()
    except Failure as f:
        return f.kind
    except Cancelled:
        return "Cancelled"
    except Exception as e:
        return type(e).__name__
    return None


# ---- the body
r1 = req()
b_a, b_b = llama.body_bytes(llama.llama_body(r1, {"slot": 0})), llama.body_bytes(llama.llama_body(req(), {"slot": 0}))
check("the same request and machine give the same bytes", b_a == b_b)
b_slot1 = llama.llama_body(r1, {"slot": 1})
check("a machine field changes the body", b_slot1["id_slot"] == 1 and llama.llama_body(r1, {"slot": 0})["id_slot"] == 0)
check("the fingerprint is the request's alone", set(llama.neutral(r1)) == {"model", "messages", "schema", "schema_sha", "sampling",
      "max_tokens", "think", "voice"} and llama.neutral_hash(r1) == llama.neutral_hash(req()))
check("a request field changes the fingerprint", llama.neutral_hash(req(attempt=1)) != llama.neutral_hash(r1)
      and llama.neutral_hash(req(text="other")) != llama.neutral_hash(r1)
      and llama.neutral_hash(req(max_tokens=61)) != llama.neutral_hash(r1))
body = llama.llama_body(r1)
check("every sampler is sent", all(k in body for k in llama.SAMPLER_KEYS), [k for k in llama.SAMPLER_KEYS if k not in body])
check("thinking is off on every request", body["chat_template_kwargs"] == {"enable_thinking": False})
from llm import gbnf
check("the answer's ceiling as n_predict, the schema as its grammar (f527: `grammar`, llama.cpp's own conversion, never response_format)",
      body["n_predict"] == 60 and body["grammar"].splitlines()[0].startswith("# Meravia Read ")
      and body["grammar"].split("\n", 1)[1] == gbnf.grammar(Read.model_json_schema()) and "response_format" not in body
      and body["cache_prompt"] is True and body["stream"] is False, body.get("grammar", "")[:120])
check("no slot named, none sent", "id_slot" not in body)

hire = llama.llama_body(req("hire_chat", 1.0))
want_rep = round(config.SAMPLING["hire_chat"]["repeat_penalty"] + config.REPEAT_ADD, 3)     # (f527) the table is data/rules/sampling.yaml
check("hire_chat is sent its repeat with the base under it",
      hire["repeat_penalty"] == want_rep and hire["top_k"] == 64 and hire["min_p"] == 0.0 and hire["repeat_last_n"] == 192
      and hire["typical_p"] == 1.0 and hire["dry_multiplier"] == 0.0 and hire["xtc_probability"] == 0.0,
      {k: hire[k] for k in llama.SAMPLER_KEYS})
check("hire_chat's repeat is 1.22 with the night's shift", want_rep == 1.22 or config.REPEAT_ADD != 0.1, want_rep)
plain = llama.llama_body(req("interpret_action", 0.2))
check("an untuned task: repeat 1.0 over 64, top_k 64, min_p 0", plain["repeat_penalty"] == 1.0 and plain["repeat_last_n"] == 64
      and plain["top_k"] == 64 and plain["min_p"] == 0.0 and plain["top_p"] == 0.95, {k: plain[k] for k in llama.SAMPLER_KEYS})

before = config.THINK_TASKS
config.THINK_TASKS = frozenset({"ruling"})
try:
    tr = req("ruling", 0.3, max_tokens=200)
    tb = llama.llama_body(tr)
    check("a task chosen to think thinks, with its room", tb["chat_template_kwargs"]["enable_thinking"] is True
          and tb["n_predict"] == 200 + backend.think_room(tr.messages, 200) and tb["n_predict"] > 200, tb["n_predict"])
finally:
    config.THINK_TASKS = before

vb = llama.llama_body(req(voice="maren"), {"lora": {"maren": 1, "hire": 0}})
check("a voice sends its adapter and no other", vb["lora"] == [{"id": 0, "scale": 0.0}, {"id": 1, "scale": 1.0}], vb.get("lora"))
check("a voice with no adapter loaded is invalid", kind_of(lambda: llama.llama_body(req(voice="maren"), {})) == "invalid")
nb = llama.llama_body(req(), {"lora": {"maren": 1, "hire": 0}})
check("a call with no voice names every adapter at nothing", nb["lora"] == [{"id": 0, "scale": 0.0}, {"id": 1, "scale": 0.0}], nb.get("lora"))


# ---- statuses, against the fake
fake = FakeLlama(key="k1", slot_ctx=1000)
src = llama.LlamaServer(llama.Server(fake.port, "k1", step=0.1, load_wait=5.0), llama.Server(fake.port, "k1", step=0.1),
                        machine={"slot_ctx": 1000})

fake.script = lambda p, b, n: {"content": '{"x": "y"}', "timings": {"cache_n": 40, "prompt_n": 60, "predicted_n": 12}}
rep = src.chat(r1)
check("an answer comes back as a Reply", rep.text == '{"x": "y"}' and rep.finish == "stop", rep)
u = rep.usage or {}
check("usage counts the cached tokens in the prompt", u.get("prompt") == 100 and u.get("cached") == 40 and u.get("out") == 12, u)
check("usage keeps the timings and no load", "load_ms" not in u and u.get("wait_ms", -1) >= 0 and u.get("read_ms") == 50
      and u.get("write_ms") == 200 and u.get("total_ms") == 250 and u.get("full") is False, u)
check("the key goes with the request", fake.chats()[-1]["headers"].get("authorization") == "Bearer k1")
check("the body sent is the adapter's", fake.chats()[-1]["raw"] == llama.body_bytes(llama.llama_body(r1, {"slot_ctx": 1000})))

for name, spec, want in [
    ("past the context is too_big", {"status": 400, "type": "exceed_context_size_error",
                                     "message": "the request exceeds the available context size, try increasing it"}, "too_big"),
    ("any other 400 is invalid", {"status": 400, "type": "invalid_request_error", "message": "bad"}, "invalid"),
    ("a schema the grammar refuses is invalid", {"status": 500, "type": "server_error", "message": "JSON schema error: unsupported"}, "invalid"),
    ("any other 500 is the server's", {"status": 500, "type": "server_error", "message": "something broke"}, "server"),
    ("a dropped connection is unreachable", {"drop": True}, "unreachable"),
]:
    fake.script = lambda p, b, n, s=spec: s
    check(name, kind_of(lambda: src.chat(r1)) == want, kind_of(lambda: src.chat(r1)))

keyless = llama.LlamaServer(llama.Server(fake.port, "", step=0.1))
fake.script = None
check("a keyless request is refused, invalid", kind_of(lambda: keyless.chat(r1)) == "invalid")

with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    dead_port = s.getsockname()[1]
nobody = llama.LlamaServer(llama.Server(dead_port, "", step=0.1))
check("a refused connection is unreachable", kind_of(lambda: nobody.chat(r1)) == "unreachable")
check("nobody listening: the health says so", nobody.state() == "failed" and nobody.chat_server.health() == "unreachable")

# 503 while loading: waited on, off the deadline's clock, no try
fake.loading = 3
fake.script = lambda p, b, n: {"content": '{"x": "z"}'}
n0 = len(fake.chats())
t0 = time.monotonic()
rep = src.chat(r1, deadline=0.25)
took = time.monotonic() - t0
check("three 503s then an answer is one answer", rep.text == '{"x": "z"}' and len(fake.chats()) - n0 == 4, len(fake.chats()) - n0)
check("the load's wait was not on the deadline's clock", took > 0.25, took)
fake.loading = 3
before_tally = dict(gateway.TALLY.get("stranger_read", {"calls": 0, "attempts": 0, "failed": 0}))
use = backend.use(src)
try:
    out = gateway.generate("stranger_read", "sys", "hi", Read, temperature=0.1)
finally:
    use()
after = gateway.TALLY.get("stranger_read", {})
check("through the gateway the loading wait is no try", out.x == "z" and after.get("attempts", 0) - before_tally["attempts"] == 1
      and after.get("failed", 0) == before_tally["failed"], (before_tally, after))
fake.loading = 1000
slow = llama.LlamaServer(llama.Server(fake.port, "k1", step=0.1, load_wait=0.3))
check("too long a load is 'loading'", kind_of(lambda: slow.chat(r1)) == "loading")
fake.loading = 2
src.load()
check("load waits for ready", src.state() == "ready")
fake.loading = 0

# a cancel from another thread
fake.script = lambda p, b, n: {"content": '{"x": "late"}', "delay": 10}
d0 = fake.disconnects
use = backend.use(src)
try:
    timer = threading.Timer(0.3, src.cancel)
    timer.start()
    t0 = time.monotonic()
    got = kind_of(lambda: backend.chat(r1.messages, Read, r1.sampling, 60))
    took = time.monotonic() - t0
finally:
    use()
check("a cancel ends the call as Cancelled", got == "Cancelled", got)
check("within 1.5 s", took < 1.5, took)
end = time.monotonic() + 2.0
while fake.disconnects == d0 and time.monotonic() < end:
    time.sleep(0.02)
check("the server sees the caller hang up", fake.disconnects == d0 + 1)
check("no call is left in flight", src.cancel() == 0)

# the deadline
fake.script = lambda p, b, n: {"content": '{"x": "late"}', "delay": 5}
t0 = time.monotonic()
got = kind_of(lambda: src.chat(r1, deadline=0.6))
took = time.monotonic() - t0
check("an expired deadline is deadline", got == "deadline" and took < 1.5, (got, took))

# a full slot
fake.script = lambda p, b, n: {"content": '{"x": "y', "finish": "length", "timings": {"prompt_n": 900, "predicted_n": 100}}
rep = src.chat(r1)
check("a 'length' answer that filled the slot is full", rep.finish == "length" and rep.usage["full"] is True, rep.usage)
fake.script = lambda p, b, n: {"content": '{"x": "y', "finish": "length", "timings": {"prompt_n": 500, "predicted_n": 100}}
rep = src.chat(r1)
check("one that did not is not", rep.finish == "length" and rep.usage["full"] is False, rep.usage)

# a server that stalls mid-answer: the deadline and a cancel still hold to the last byte
fake.script = lambda p, b, n: {"content": '{"x": "slowly"}', "trickle": 0.25}
t0 = time.monotonic()
got = kind_of(lambda: src.chat(r1, deadline=1.0))
check("a trickled answer is cut at its deadline", got == "deadline" and time.monotonic() - t0 < 1.8, (got, time.monotonic() - t0))
timer = threading.Timer(0.3, src.cancel)
timer.start()
t0 = time.monotonic()
got = kind_of(lambda: src.chat(r1, deadline=30))
check("a cancel mid-answer is never lost", got == "cancelled" and time.monotonic() - t0 < 1.5, (got, time.monotonic() - t0))

# one thread's call cancelled, another's left
fake.script = lambda p, b, n: {"content": '{"x": "%s"}' % b["messages"][-1]["content"], "delay": 1.5}
res = {}


def call(key):
    try:
        res[key] = src.chat(req(text=key)).text
    except Failure as f:
        res[key] = f.kind
ta, tb = threading.Thread(target=call, args=("a",)), threading.Thread(target=call, args=("b",))
ta.start(); tb.start()
time.sleep(0.4)
src.cancel(ta.ident)
ta.join(5); tb.join(5)
check("cancel(thread) ends that thread's call and no other", res == {"a": "cancelled", "b": '{"x": "b"}'}, res)

# each lane's slot
lanes = llama.LlamaServer(llama.Server(fake.port, "k1", step=0.1), machine={"slot_ctx": 1000, "slots": {"foreground": 0, "background": 1}})
fake.script = lambda p, b, n: {"content": '{"x": "y"}'}
lanes.chat(r1)
fg_slot = fake.chats()[-1]["body"].get("id_slot")
with backend.lane("background"):
    lanes.chat(r1)
check("each lane is sent its own slot", fg_slot == 0 and fake.chats()[-1]["body"].get("id_slot") == 1, (fg_slot, fake.chats()[-1]["body"].get("id_slot")))

# a slot's context read from /props when the machine does not say
props = llama.LlamaServer(llama.Server(fake.port, "k1", step=0.1))
fake.script = lambda p, b, n: {"content": '{"x": "y', "finish": "length", "timings": {"prompt_n": 900, "predicted_n": 100}}
rep = props.chat(r1)
check("with no context given it is read from the server", props.slot_ctx() == 1000 and rep.usage["full"] is True, (props.slot_ctx(), rep.usage))

# no proxy setting is ever used
saved = {k: os.environ.get(k) for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy", "NO_PROXY", "no_proxy")}
for k in ("HTTPS_PROXY", "HTTP_PROXY", "https_proxy", "http_proxy"):
    os.environ[k] = "http://127.0.0.1:9"
for k in ("NO_PROXY", "no_proxy"):
    os.environ.pop(k, None)
try:
    fake.script = lambda p, b, n: {"content": '{"x": "direct"}'}
    check("no proxy setting is used", src.chat(r1).text == '{"x": "direct"}')
finally:
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v

# embeddings
fake.script = lambda p, b, n: {"payload": {"data": [{"index": 1, "embedding": [0.0, 1.0]}, {"index": 0, "embedding": [1.0, 0.0]}],
                                           "usage": {"prompt_tokens": 4}}}
e = src.embed(["a", "b"])
check("embeddings come back in the order asked", e.vectors == [[1.0, 0.0], [0.0, 1.0]])
check("the embed request is llama-server's", fake.requests[-1]["path"] == "/v1/embeddings"
      and fake.requests[-1]["body"] == {"model": config.EMBED_MODEL, "input": ["a", "b"], "encoding_format": "float"})
fake.script = lambda p, b, n: {"status": 500, "type": "server_error",
                               "message": "input (3000 tokens) is too large to process. increase the physical batch size (current batch size: 2048)"}
check("an embed text past the batch is too_big", kind_of(lambda: src.embed(["x" * 9000])) == "too_big")
check("a source with no embedder says so", kind_of(lambda: keyless.embed(["a"])) == "unreachable"
      and keyless.facts()["embedder"] is False and src.facts()["embedder"] is True)

# ---- the switch
saved_backend, saved_env = config.BACKEND, {k: os.environ.get(k) for k in ("DND_LLAMA_URL", "DND_LLAMA_KEY", "MERAVIA_NO_SERVER")}
try:
    config.BACKEND = "llama"
    os.environ["MERAVIA_NO_SERVER"] = "1"
    backend.forget_switch()
    check("under the suite's switch the default never reaches a live server", backend.source().name == "no-server")
    config.BACKEND = saved_backend
    os.environ.pop("MERAVIA_NO_SERVER", None)
    check("the default is the game's own runtime, unstarted until the game or a tool starts it (f528)",
          config.BACKEND == "runtime" and backend.source().name == "runtime")
    config.BACKEND = "llama"
    os.environ["DND_LLAMA_URL"], os.environ["DND_LLAMA_KEY"] = fake.url, "k1"
    backend.forget_switch()
    s = backend.source()
    check("DND_BACKEND=llama makes the llama-server the default", s.name == "llama-server" and s.chat_server.port == fake.port)
    fake.script = lambda p, b, n: {"content": '{"x": "switched"}'}
    check("and the gateway reaches it", gateway.generate("stranger_read", "sys", "hi", Read, temperature=0.1).x == "switched")
    os.environ["DND_LLAMA_URL"] = "http://10.1.2.3:8080"
    backend.forget_switch()
    check("only on this machine", kind_of(lambda: backend.source()) == "ValueError")
    os.environ["DND_LLAMA_URL"] = "http://127.0.0.1"
    backend.forget_switch()
    check("a URL with no port is refused in plain words", kind_of(lambda: backend.source()) == "ValueError")
finally:
    config.BACKEND = saved_backend
    backend.forget_switch()
    for k, v in saved_env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
check("the switch put back", backend.source().name == "no-server")

fake.close()

# ---- the data's check
check("the sampler table is clean", llama.sampler_problems() == [], llama.sampler_problems())
check("a misspelt key is refused", any("repet_penalty" in p for p in llama.sampler_problems({"narrate": {"repet_penalty": 1.1}})))
check("a value out of range is refused", any("top_p" in p for p in llama.sampler_problems({"narrate": {"top_p": 1.5}})))
check("a fraction where a whole number belongs is refused", any("top_k" in p for p in llama.sampler_problems({"narrate": {"top_k": 6.5}})))
check("a base with a key missing is refused", any("no base value" in p for p in llama.sampler_problems({}, {"top_k": 64})))
check("a repeat window below 0, which this server refuses, is refused", any("repeat_last_n" in p for p in llama.sampler_problems({"narrate": {"repeat_last_n": -1}})))
from engine import data_check
check("the shipped data is clean", data_check.check() == [], data_check.check()[:3])
saved_sampling = config.SAMPLING
config.SAMPLING = {**saved_sampling, "narrate": {**saved_sampling.get("narrate", {}), "repet_penalty": 1.1}}
try:
    check("data_check carries the sampler check", any("repet_penalty" in p for p in data_check.check()))
finally:
    config.SAMPLING = saved_sampling

print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
