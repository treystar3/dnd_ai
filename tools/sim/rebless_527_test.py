"""(f527) The one re-bless: everything that moves the data hash, the request hash or the order of calls, in one commit, so the kept
recordings are re-blessed once and hashed data is frozen until the bundle ends.

- The three kept recordings are in the interface's own form: every chat row's request neutral (messages, schema title and fingerprint,
  every sampler, the ceiling, think, voice, the GGUF id), every embed row the model and the texts, the fingerprint the request's;
  answered rows carry finish and usage, failed rows {kind, detail}; nothing of the machine; meta holds the facts, overlapped 0, in order.
- stub_party's failed input: three failed tries and no relaxed retry after a transport failure (nor after a too_big).
- rerun --translate: a recording against itself names nothing; a dropped row and a changed request are named; an old-form row translates
  to the same fingerprint; the replayer refuses old-form rows and a re-bless still reads them.
- The gate prices at the baseline's own prices (priced_at), whatever the card profile says; the embed price is the card's, measured.
- data/rules/sampling.yaml is the sampling table, checked; config.MODEL is the chat GGUF's id, checked against server.yaml, in the data
  hash; cards.yaml names the minimum cards; every contract has its grammar; the startup check passes with every new file in.
- llm/gbnf.py gives llama.cpp's own grammar, byte for byte, on the schemas pinned from the C++ converter; the request body carries it as
  `grammar` and no response_format; a schema outside the subset is a refused request.
- The owner's lines (6 Nov) are in: creation, the opening, the load screen; a chat-template token in prose is caught.
- The replayer serves neutral rows; the Ollama-shaped source still sends Ollama's tag.
golden_replay_test replays the re-blessed recordings; this test reads them."""
import copy
import json
import sys
import types
from pathlib import Path

sys.path.insert(0, ".")
sys.path.insert(0, "tools")
sys.path.insert(0, "tools/sim")
import yaml
from pydantic import BaseModel, Field

import config
import card_profile
import latency
import rerun
import simlib
from engine import budget, data_check, failures, hygiene, recording
from llm import backend, contracts, gateway, gbnf, launch, llama, sampling
from llm.errors import KINDS, Failure, LLMError
from storage import statehash

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


NEUTRAL = {"model", "messages", "schema", "schema_sha", "sampling", "max_tokens", "think", "voice"}
recs = {name: rerun.load(rerun.golden(name)) for name in ("stub_short", "stub_party", "stub_fight")}

# ---- 1. the kept recordings, in the interface's own form
for name, rec in recs.items():
    calls = rec["calls"]
    chat = [c for c in calls if c["kind"] == "chat"]
    emb = [c for c in calls if c["kind"] == "embed"]
    check(f"{name}: every chat row's request is the neutral form, its model the GGUF id, its fingerprint the request's, its title the schema's",
          chat and all(set(c["request"]) == NEUTRAL and c["request"]["model"] == config.MODEL and c["req"] == recording.request_hash(c["request"])
                       and c["title"] == c["request"]["schema"] and c["request"]["sampling"].keys() >= set(sampling.BASE) for c in chat),
          [c["i"] for c in chat if set(c["request"]) != NEUTRAL][:3])
    check(f"{name}: every embed row is the embedding model's id and the texts, fingerprinted",
          all(set(c["request"]) == {"model", "input"} and c["request"]["model"] == config.EMBED_MODEL
              and c["req"] == recording.request_hash(c["request"]) for c in emb), len(emb))
    answered = [c for c in calls if not c.get("error")]
    check(f"{name}: an answered chat row has finish stop, length or cancelled and a usage table, and no done or tokens",
          all(("finish" not in c or c["finish"] in backend.FINISHES) and ("usage" not in c or isinstance(c["usage"], dict))
              and "done" not in c and "tokens" not in c for c in answered)
          and all(c["finish"] in backend.FINISHES and isinstance(c["usage"], dict) for c in answered if c["kind"] == "chat"))
    failed = [c for c in calls if c.get("error")]
    check(f"{name}: a failed row's error is the interface's own kind and a detail",
          all(isinstance(c["error"], dict) and c["error"].get("kind") in KINDS and c["error"].get("detail") for c in failed), failed[:1])
    meta = rec["meta"]
    check(f"{name}: meta holds the facts (the GGUF id, overlapped 0, the profile with the embed price) and the rows are in order",
          meta.get("model") == config.MODEL and meta.get("overlapped") == 0 and (meta.get("profile") or {}).get("embed_seconds_per_text")
          and [c["i"] for c in calls] == sorted(c["i"] for c in calls), {k: meta.get(k) for k in ("model", "overlapped", "profile")})
    check(f"{name}: nothing of the machine in any request", all("num_thread" not in json.dumps(c["request"]) and "num_ctx" not in json.dumps(c["request"])
                                                                 and "deadline" not in c["request"] and "slot" not in c["request"] for c in calls))

party = recs["stub_party"]["calls"]
failed_inputs = {c["input"] for c in party if c.get("error")}
check("stub_party: one input fails, every try of it, and nothing else", len(failed_inputs) == 1, failed_inputs)
inp = next(iter(failed_inputs), None)
rows_at = [c for c in party if c["input"] == inp]
check("...its three tries failed on the server and no relaxed retry followed them (f527: none after a transport failure)",
      sum(1 for c in rows_at if c.get("error") and c["title"] == "NPCReply") == 3 and not any(c["title"] == "NPCReply" and not c.get("error") for c in rows_at)
      and all(c["error"]["kind"] == "server" for c in rows_at if c.get("error")), [(c["title"], bool(c.get("error"))) for c in rows_at])

# ---- 2. the translation and the refusal of the old form
rec = recs["stub_short"]
check("translate: a recording against itself names nothing", rerun.translate(rec, rec) == [])
dropped = copy.deepcopy(rec)
gone = dropped["calls"].pop(3)
out = rerun.translate(rec, dropped)
check("...a row the new recording no longer makes is named with its number, input and title",
      len(out) == 1 and "is not made any more" in out[0] and f"old call {gone['i']} (input {gone['input']}" in out[0] and gone["title"] in out[0], out)
changed = copy.deepcopy(rec)
row = next(c for c in changed["calls"] if c["kind"] == "chat")
row["request"]["messages"][-1]["content"] += " and more"
row["req"] = recording.request_hash(row["request"])
out = rerun.translate(rec, changed)
check("...a request whose words moved is named with the field that moved", len(out) == 1 and "'messages'" in out[0] and "differ" in out[0], out)
new_row = next(c for c in rec["calls"] if c["kind"] == "chat" and c["title"] == "Narration")
explicit = {k: v for k, v in new_row["request"]["sampling"].items() if k != "temperature" and v != sampling.BASE.get(k)}
old_row = {**new_row, "request": {"model": "gemma4:12b", "think": False, "messages": new_row["request"]["messages"],
                                   "options": {"temperature": new_row["request"]["sampling"]["temperature"], "num_ctx": 32768,
                                               "num_predict": new_row["request"]["max_tokens"], "num_thread": 6, **explicit}, "keep_alive": "30m"},
           "done": "stop", "tokens": {}}
del old_row["finish"], old_row["usage"]
check("an old-form row (the Ollama-shaped request the recorder wrote before) translates to the new fingerprint",
      recording.request_hash(rerun.neutral_of(old_row)) == new_row["req"], (rerun.neutral_of(old_row), new_row["request"]))
check("the replayer refuses a recording in the old form, and a re-bless still reads it to compare",
      "old client" in rerun.refusal({}, [old_row]) and rerun.refusal({}, [old_row], replaying=False) == "" and rerun.refusal({}, [new_row]) == "")

# ---- 3. the gate at the baseline's prices; the embed price from the card's profile
base = yaml.safe_load(Path("data/measured/bundle_d_baseline.yaml").read_text(encoding="utf-8"))
g1, o1 = latency.gate(), latency.over_limit(base=base)
with budget.priced(read_tps=budget.PROFILE["read_tps"] * 2, write_tps=budget.PROFILE["write_tps"] * 2, embed_seconds_per_text=budget.PROFILE["embed_seconds_per_text"] * 2):
    g2, o2 = latency.gate(), latency.over_limit(base=base)
check("the baseline carries the prices it was measured at", base.get("priced_at") == {"read_tps": 756.8, "write_tps": 31.7, "embed_seconds_per_text": 0.15})
check("with the card profile doubled, the gate and the limit give the same lists: both price at the baseline's priced_at", g1 == g2 and o1 == o2, (g1, g2))
check("...and the gate holds after the re-bless: no input priced dearer than before", all(v == [] for v in g1.values()), g1)
folder = rerun.golden("stub_party")
texts = sum(len(c["request"]["input"]) for c in party if c["kind"] == "embed")
est = dict(card_profile.estimate_inputs(folder, expected=True))
with budget.priced(embed_seconds_per_text=0.0001):
    est0 = dict(card_profile.estimate_inputs(folder, expected=True))
check("card_profile prices stub_party's embed texts above zero, at the profile's price (0.15 s a text)",
      texts > 100 and abs((sum(est.values()) - sum(est0.values())) - texts * (0.15 - 0.0001)) < 0.01, (texts, sum(est.values()) - sum(est0.values())))
check("the embed price is the card's, in the measured profile, no longer in budget.yaml",
      "embed_seconds_per_text" not in budget.B and budget.PROFILE["embed_seconds_per_text"] == 0.15
      and yaml.safe_load(Path("data/measured/card_profile.yaml").read_text(encoding="utf-8"))["embed_seconds_per_text"] == 0.15)
b = budget.open()
cost = budget.embed(4)
budget.close()
check("a turn's embed call is charged texts times that price", abs(cost - 0.6) < 1e-9, cost)
check("usage_of reads both forms of a row's counts",
      card_profile.usage_of({"usage": {"prompt": 10, "out": 5, "read_ms": 100, "write_ms": 50, "cached": 2}}) == {"prompt": 10, "out": 5, "read_ms": 100, "write_ms": 50, "cached": 2}
      and card_profile.usage_of({"tokens": {"prompt_eval_count": 10, "eval_count": 5, "prompt_eval_duration": 100_000_000, "eval_duration": 50_000_000, "cached": 2}})
      == {"prompt": 10, "out": 5, "read_ms": 100.0, "write_ms": 50.0, "cached": 2} and card_profile.usage_of({}) == {})
sc = card_profile.scaled({"seconds": 1.0, "usage": {"prompt": 10, "out": 5, "read_ms": 200, "write_ms": 300}}, 2.0, 0.5)
check("scaling a call to another card scales its reading and writing time", sc["usage"]["read_ms"] == 400 and sc["usage"]["write_ms"] == 150 and abs(sc["seconds"] - 1.05) < 1e-9, sc)

# ---- 4. the data: sampling.yaml, the model ids, the cards, the grammars, the whole check
S = yaml.safe_load(Path("data/rules/sampling.yaml").read_text(encoding="utf-8"))
check("the startup check passes with every new file in", data_check.check() == [], data_check.check()[:4])
check("the sampling table the game plays by is data/rules/sampling.yaml's", config.SAMPLING == S["tasks"] and sampling.BASE == S["base"]
      and sampling.RETRY_TEMPERATURE_STEP == S["retry_temperature_step"] == 0.15 and len(S["tasks"]) == 16)
plan = sampling.resolve("hire_chat", 1.0).at(0).resolved()
check("a resolved plan lays the base under a task's own values", plan["top_k"] == 64 and plan["repeat_last_n"] == 192 and plan["min_p"] == 0.0
      and set(plan) == set(llama.SAMPLER_KEYS), plan)
check("sampling.yaml's shape is checked: a missing base, a stray key, a step of 0 or over 1",
      any("base" in m for m in data_check.sampling_problems({"tasks": {}, "retry_temperature_step": 0.15}))
      and any("retry_temperature_step" in m for m in data_check.sampling_problems({"base": S["base"], "tasks": {}, "retry_temperature_step": 0}))
      and any("no sampler" in m and "sampling.yaml tasks.narrate" in m for m in llama.sampler_problems(table={"narrate": {"topk": 1}}))
      and any("sampling.yaml base" in m for m in llama.sampler_problems(base={"top_k": 64})))
check("config.MODEL is the chat GGUF's id and EMBED_MODEL the embedder's, each the file's stem and sha prefix in server.yaml",
      config.MODEL == "gemma4-12b-bb722270" and config.EMBED_MODEL == "nomic-embed-text-970aa74c" and data_check.model_problems() == []
      and any("MODEL" in m for m in data_check.model_problems(cfg=types.SimpleNamespace(MODEL="gemma4:12b", EMBED_MODEL=config.EMBED_MODEL)))
      and any("sha" in m for m in data_check.model_problems(cfg=types.SimpleNamespace(MODEL="gemma4-12b-deadbeef", EMBED_MODEL=config.EMBED_MODEL),
                                                               server={"models": {"c": {"role": "chat", "file": "gemma4-12b-deadbeef.gguf", "sha256": "bb72"},
                                                                                  "e": {"role": "embed", "file": config.EMBED_MODEL + ".gguf", "sha256": "970aa74c"}}})))
h1 = statehash.data_hash()
saved = config.MODEL
config.MODEL = "gemma4:12b"
h2 = statehash.data_hash()
config.MODEL = saved
check("the data hash folds the GGUF id in: another id, another hash", h1 != h2 and statehash.data_hash() == h1)
check("the Ollama-shaped source still sends Ollama's tag while the game's id is the GGUF's (until f532)",
      backend.ollama_kwargs(backend.ChatRequest(messages=[{"role": "user", "content": "x"}], schema=contracts.Narration,
                                                sampling=sampling.resolve("narrate", 0.8).at(0), max_tokens=10))["model"] == config.OLLAMA_MODEL == "gemma4:12b"
      and backend.embed_kwargs(["a"])["model"] == config.OLLAMA_EMBED_MODEL == "nomic-embed-text")
C = yaml.safe_load(Path("data/rules/cards.yaml").read_text(encoding="utf-8"))
check("cards.yaml names the minimum cards, the RX 7600 XT among them, with a pattern for each card",
      C["minimum"] == {"cuda": "RTX 3060 12GB", "vulkan": "RX 7600 XT 16GB"} and "RX 7600 XT 16GB" in C["cards"] and set(C["patterns"]) == set(C["cards"])
      and data_check.cards_problems() == [])
probs = data_check.cards_problems({"cards": {"A": {}}, "minimum": {"cuda": "B", "vulkan": "A"}, "patterns": {"A": "(", "Z": "z"}})
check("...a minimum card the file does not know, a bad pattern and a pattern for no card are named",
      any("minimum.cuda" in m for m in probs) and any("patterns.A" in m for m in probs) and any("'Z'" in m for m in probs), probs)
check("every contract's schema has a grammar", data_check.grammar_problems() == [], data_check.grammar_problems()[:2])

# ---- 5. the grammar: llama.cpp's own, pinned from the C++ converter; the body carries it
pinned = json.loads(Path("tools/sim/gbnf_pinned_527.json").read_text(encoding="utf-8"))
check("llm/gbnf.py gives llama.cpp's grammar byte for byte on the seven pinned schemas (ActionPlan, Narration, a two-speaker reply; integer bounds, optional fields, additionalProperties, $ref with a format)",
      len(pinned) == 7 and all(gbnf.grammar(v["schema"]) == v["gbnf"] for v in pinned.values())
      and pinned["contract_ActionPlan"]["schema"] == contracts.ActionPlan.model_json_schema()
      and pinned["contract_NPCReplyMany2"]["schema"] == contracts.many_reply(["a", "b"]).model_json_schema(),
      [k for k, v in pinned.items() if gbnf.grammar(v["schema"]) != v["gbnf"]])
req = backend.ChatRequest(messages=[{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], schema=contracts.Narration,
                          sampling=sampling.resolve("narrate", 0.8).at(0), max_tokens=100)
body = llama.llama_body(req)
sha = backend.neutral_request(req)["schema_sha"]
check("the request body carries the grammar, headed by the contract's name and fingerprint, and no response_format",
      body["grammar"].startswith(f"# Meravia Narration {sha}\n") and body["grammar"].split("\n", 1)[1] == gbnf.grammar(contracts.Narration.model_json_schema())
      and "response_format" not in body and "json_schema" not in json.dumps(body), body.get("grammar", "")[:80])
check("...the grammar cached per schema fingerprint", llama.llama_body(req)["grammar"] is body["grammar"])


class Patterned(BaseModel):
    code: str = Field(pattern="^[a-z]+$")


try:
    llama.llama_body(backend.ChatRequest(messages=req.messages, schema=Patterned, sampling=req.sampling, max_tokens=10))
    kind = None
except Failure as f:
    kind = f.kind
check("a schema the converter does not take (a string pattern) is a refused request, never a server fault", kind == "invalid", kind)
try:
    gbnf.grammar({"type": "string", "pattern": "^a$"})
    said = ""
except gbnf.SchemaError as e:
    said = str(e)
check("...and the converter says so plainly", "pattern" in said and "not converted" in said, said)

# ---- 6. the gateway: no relaxed retry after a transport failure or a too_big; one after every answer refused
counts = {}


def failing(kind):
    def chat(**k):
        counts[kind] = counts.get(kind, 0) + 1
        raise Failure(kind, "planted")
    return chat


for kind, want in (("server", 3), ("too_big", 1)):
    held = simlib.stand_in(chat=failing(kind))
    try:
        gateway.generate("narrate", "You narrate.", "The sea.", contracts.Narration, retries=2, relaxed_context={"loose": True})
    except LLMError:
        pass
    finally:
        held()
    check(f"a {kind} failure: {want} tr{'y' if want == 1 else 'ies'} and no relaxed retry", counts.get(kind) == want, counts)
refused = {"n": 0}


def bad_answers(**k):
    refused["n"] += 1                                                  # a different fault each time, or the second refusal ends the tries (f447)
    return types.SimpleNamespace(message=types.SimpleNamespace(content=['{"wrong": 1}', '{"text": 5}', '{"text": null}', '[]'][refused["n"] % 4]), done_reason="stop")


held = simlib.stand_in(chat=bad_answers)
try:
    gateway.generate("narrate", "You narrate.", "The sea.", contracts.Narration, retries=2, relaxed_context={"loose": True})
except LLMError:
    pass
finally:
    held()
check("every answer refused: the relaxed retry is still made (three tries and one more)", refused["n"] == 4, refused)

# ---- 7. the owner's lines are in; the template reason
F = yaml.safe_load(Path("data/rules/failures.yaml").read_text(encoding="utf-8"))
check("the owner's creation and opening lines are in (6 Nov): one list per kind and per step, three lines each, and the opening's three",
      set(F["creation_fail"]) == set(failures.CREATION_FAILS) and set(F["creation_stand_in"]) == set(failures.CREATION_STEPS)
      and all(len(v) == 3 for v in list(F["creation_fail"].values()) + list(F["creation_stand_in"].values())) and len(F["opening_untold"]) == 3
      and failures.creation_line("gifts") in F["creation_fail"]["gifts"] and failures.creation_stand_in("stats") in F["creation_stand_in"]["stats"]
      and failures.opening_untold() in F["opening_untold"])
L = yaml.safe_load(Path("data/rules/launch.yaml").read_text(encoding="utf-8"))
check("the load screen's lines are in, every key, so the screen is on", set(L) == set(launch.KEYS) and launch.screen_on()
      and launch.line("no_memory", needed=14) == "This computer does not have enough memory to hold the world. It needs at least 14 GB.")
check("every new line passes the startup check: no machinery, no dash", failures.problems() == [] and launch.problems() == [])
check("a chat-template or thinking token in an answer's prose is caught, with its reason",
      hygiene.problem("narrate", {"text": "The sea is grey.<end_of_turn>"})[0] == "template" and hygiene.problem("npc_conversation", {"speech": "<think>no</think>Yes."})[0] == "template"
      and hygiene.problem("narrate", {"text": "A plain line."}) == ("", "") and "machinery" in hygiene.reason("template"))

# ---- 8. the replayer serves neutral rows
n = backend.neutral_request(req)
rows = [{"i": 0, "input": 0, "kind": "chat", "title": "Narration", "req": recording.request_hash(n), "request": n, "answer": '{"text": "ok"}',
         "finish": "stop", "usage": {"prompt": 3, "out": 2}},
        {"i": 1, "input": 0, "kind": "chat", "title": "Narration", "req": recording.request_hash(n), "request": n,
         "error": {"kind": "deadline", "detail": "cut"}}]
src = rerun.Replay(rows, {})
rep = src.chat(req)
try:
    src.chat(req)
    kind = None
except Failure as f:
    kind = f.kind
check("the replayer serves a neutral row as the interface's Reply, and a failed row as its Failure",
      rep.text == '{"text": "ok"}' and rep.finish == "stop" and rep.usage == {"prompt": 3, "out": 2} and kind == "deadline", (rep, kind))

print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
