"""(f543) A situation's parts asked for: the proposal's prompt (engine/situations.py prompt, engine/pulse_prompts.py PARTS_SYSTEM), the
task in the budget's and the audit log's tables, the stand-in's answer (simlib.Stub.a_SituationParts), and the offline runner that
measures thinking in the proposal before the owner decides (tools/situation_ab.py), run against a local stand-in of llama-server.

- The prompt: lean, ids beside names, every list in a fixed order, the same world giving the same text; the town's people without the
  trades no situation casts, the trades its places are written with that nobody has met, other trades only at a tier that may bring
  someone new, the roads that touch the town (a shut one said so), the goods, the caps of the tier; the system text gives every word of
  the closed lists (data_check holds it).
- The stand-in's answer is checked whole at the rare tier; its bad answer (past the caps, the player, nobody, the game's ids) is dropped
  part by part with the reasons, within the caps.
- The runner: the cases the same for the same seed (prompt hashes equal in two runs); the arms in turn, the order turning; thinking off
  sent with no budget field and the template's switch off, a capped arm with the field and its room, uncapped within the slot; each
  answer scored by the contract and the check (kept by kind, the drop reasons, finish incl. thought_out, tokens, card seconds); the
  blind pack in both slot orders with no arm named, no id and no underscore in a card; the decision by the rule fixed in advance.
- The measured file the decision writes passes the game's check; one naming an arm the data does not know is refused.
Run: python tools/sim/situation_ab_543_test.py"""
import copy
import json
import os
import random
import re
import shutil
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from engine import data_check, pulse, situations
from engine import pulse_prompts as pp
from tools import situation_ab as ab

bad: list[str] = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name, "" if ok else detail)
    if not ok:
        bad.append(name)


# ---- the tables
found = data_check.task_literals()
check("the task is asked for in the engine and by the runner's stand-in path", any(w.startswith("engine/situations.py") for w in found.get("situation_parts", []))
      and any(w.startswith("tools/situation_ab.py") for w in found.get("situation_parts", [])), found.get("situation_parts"))
check("the budget's table and the audit log know it, and the tables are whole", not data_check.budget_problems(), data_check.budget_problems())
import yaml
B = yaml.safe_load(open("data/rules/budget.yaml"))["tasks"]["situation_parts"]
check("...an optional call, dropped past the budget (nothing on the turn's required path)", B.get("need") == "optional" and B.get("later") == "dropped", B)
check("situations.yaml (proposal, thinking arms and rule) passes its check", not situations.problems(), situations.problems())
S0 = copy.deepcopy(situations.S)
held = pp.PARTS_SYSTEM
pp.PARTS_SYSTEM = held.replace("rid_of_rival", "rid of a rival")
check("a word of the closed lists missing from the proposal's prompt is refused", any("rid_of_rival" in p for p in situations.problems()))
pp.PARTS_SYSTEM = held
situations.S["thinking"]["arms"]["off"] = {"think": True}
situations.S["thinking"]["arms"]["budget_x"] = {"think": True, "budget": 0}
situations.S["thinking"]["prefer_share"] = 0.4
probs = situations.problems()
check("arms the rule cannot read are refused: off thinking, a budget of 0, a share a coin toss would pass", any("arms.off" in p for p in probs)
      and any("budget_x.budget" in p for p in probs) and any("prefer_share" in p for p in probs), probs)
situations.S.clear(); situations.S.update(S0)

# ---- the prompt
g = simlib.campaign("situation_ab_543", seed=7, location="trading_square")
ws = g.scene
ws.enter("trading_square")
store, world = g.store, ws.world
town = pulse.town_of(world, "trading_square")
place = world.places[town]
rows = __import__("engine.retrieval", fromlist=["x"]).people_in_town(store, world, town)
state = store.load_world_state() or pulse.empty_state(ws.minutes)
road = sorted(rid for rid, r in world.roads.items() if town in (r.from_, r.to))[0]
state = dict(state, effects=list(state.get("effects", [])) + [{"kind": "closed", "place": road, "until": ws.minutes + 1440, "value": 0}])
system, user = situations.prompt(store, world, state, place, "rare", ws.minutes, "A caravan is late.")
again = situations.prompt(store, world, state, place, "rare", ws.minutes, "A caravan is late.")
one = lambda key, u=user: (re.search(rf"^{re.escape(key)}: (.*)$", u, re.M) or [None, ""])[1]
check("the same world gives the same prompt", (system, user) == again)
check("the system text is the proposal's own", system == pp.PARTS_SYSTEM)
check("PEOPLE holds the town's people by id, name and trade", all(f"{n.id}: {n.name}, {n.role}" in user for n in rows
      if n.role not in situations.S["never_roles"]), user)
never = situations.S["never_roles"]
listed = re.findall(r"(\w+): [^;]+?, (\w+)", one("PEOPLE (id: name, trade)"))
check("...and none of a trade no situation casts", not any(r in never for _, r in listed) and listed, listed)
trades = [x.strip() for x in one("TRADES OF THE TOWN").split(",")]
others = [x.strip() for x in one("OTHER TRADES").split(",")]
check("the town's unmet trades and the world's other trades, apart, none of them a trade never cast or one already met",
      trades and others and not set(trades) & set(others) and not (set(trades) | set(others)) & set(never)
      and not set(trades) & {n.role for n in rows}, (trades, others))
_, u2 = situations.prompt(store, world, state, place, "uncommon", ws.minutes)
check("a tier that brings nobody new is shown no other trades, and its own caps", "OTHER TRADES" not in u2
      and f"AT MOST: {situations.S['caps']['parts']['uncommon']} parts" in u2 and "none from outside the town" in u2, u2[-300:])
check("...and THE TROUBLE, left unset, says what to fit instead", "THE TROUBLE: nothing set" in u2)
check("AT MOST carries the rare tier's caps from the data", f"AT MOST: {situations.S['caps']['parts']['rare']} parts in all; "
      f"{situations.S['caps']['people']} people, {situations.S['caps']['new_people']['rare']} of them from OTHER TRADES" in user, one("AT MOST"))
roads_line = one("ROADS (id: name, from - to)")
check("the roads that touch the town, a shut one said so, and no other road", f"{road}: " in roads_line and "(shut now)" in roads_line
      and all(town in (world.roads[r].from_, world.roads[r].to) for r in re.findall(r"(\w+): ", roads_line)), roads_line)
places_line = one("PLACES (id: name)")
check("the places are the town's own and those one road away, never a road stop", f"{town}: " in places_line
      and all(pulse.known(world, p) for p in re.findall(r"(\w+): ", places_line)), places_line)
check("every good of the world, by id and name", all(f"{gid}: " in one("GOODS (id: name)") for gid in situations._goods()))

amaranth = world.places["amaranth"]
lone = [rid for rid, r in world.roads.items() if "amaranth" in (r.from_, r.to)]
_, ua = situations.prompt(store, world, {}, amaranth, "rare", ws.minutes)
_, ua_ways = situations.prompt(store, world, {}, amaranth, "rare", ws.minutes, ways=True)
check("with no way through offered, a road that is the only way between its ends is said to be one; with one offered it is not",
      lone and all(f"{rid}: " in ua for rid in lone) and "(the only way between its ends: it cannot be closed)" in ua
      and "only way" not in ua_ways and "only way" not in roads_line.replace(f"{road}: ", ""), (lone, one("ROADS (id: name, from - to)", ua)))
check("the system text tells each who once, points_to among the proposal's own people, and the only way never closed",
      "Each who once" in pp.PARTS_SYSTEM and "points_to - the `who` of one of\n  your people" in pp.PARTS_SYSTEM
      and "only way between its ends is\n  never closed" in pp.PARTS_SYSTEM)
most = situations.S["proposal"]["people_most"]
situations.S["proposal"]["people_most"] = 1
_, u_few = situations.prompt(store, world, state, place, "rare", ws.minutes)
shown_ = re.findall(r"(\w+): [^;]+?, (\w+)", one("PEOPLE (id: name, trade)", u_few))
hidden = [n for n in rows if n.id not in {i for i, _ in shown_} and n.role not in never]
check("PEOPLE holds at most people_most, and the trades of those not shown are the town's own trades, never someone new",
      len(shown_) == 1 and hidden and all(n.role in one("TRADES OF THE TOWN", u_few).split(", ") and n.role not in one("OTHER TRADES", u_few).split(", ")
                                          for n in hidden if n.role != shown_[0][1]), (shown_, [n.role for n in hidden]))
day2 = situations.prompt(store, world, state, place, "rare", ws.minutes + 1440 * 3)[1]
check("...those shown are drawn on the situation's place and day: the same day the same, the order its own", u_few == situations.prompt(
      store, world, state, place, "rare", ws.minutes)[1] and re.findall(r"(\w+): [^;]+?, \w+", one("PEOPLE (id: name, trade)", day2)))
situations.S["proposal"]["people_most"] = most

# ---- the stand-in's answer, through the game's gateway
parts, acc, dropped = situations.propose(store, world, state, place, "rare", ws.minutes, random.Random(1), trouble="A caravan is late.",
                                         players=(ws.acting,))
caps = situations.S["caps"]
check("the stand-in's answer is kept whole at the rare tier, within its caps", acc and not dropped and len(acc) <= caps["parts"]["rare"],
      (acc, dropped))
check("...with a person of the town, someone new of another trade, a good, a tie and a rumour", {a["kind"] for a in acc} >= {"person", "resource", "tie", "evidence"}
      and any(a.get("bind") == "new" for a in acc) and any(a.get("bind") == "npc" for a in acc), acc)
_, acc_u, dropped_u = situations.propose(store, world, state, place, "uncommon", ws.minutes, random.Random(1))
check("...and at the uncommon tier it keeps to that tier's caps and brings nobody new", acc_u and not dropped_u
      and len(acc_u) <= caps["parts"]["uncommon"] and not any(a.get("new") for a in acc_u), (acc_u, dropped_u))
stub.parts_bad = True
_, acc_b, dropped_b = situations.propose(store, world, state, place, "rare", ws.minutes, random.Random(1), players=(ws.acting,))
stub.parts_bad = False
R = situations.S["reasons"]
reasons = [r for _, r in dropped_b]
check("the bad answer is dropped part by part: the player, nobody, the game's ids, past the caps, a doubtful piece at a place",
      all(R[k] in reasons for k in ("player", "not_a_person", "raw_id", "not_a_good", "not_a_place", "claim_at_place"))
      and (R["people_cap"] in reasons or R["parts_cap"] in reasons), reasons)
check("...what stands keeps within the caps", len(acc_b) <= caps["parts"]["rare"] and sum(a["kind"] == "person" for a in acc_b) <= caps["people"], acc_b)
check("the card is the same for the same parts in any order, and its wording a part's own", ab.card(store, world, {"pressure": "p", "tier": "rare"}, acc)
      == ab.card(store, world, {"pressure": "p", "tier": "rare"}, list(reversed(acc)))
      and ab.card(store, world, {"pressure": "p", "tier": "rare"}, acc[:1]).splitlines()[0] in ab.card(store, world, {"pressure": "p", "tier": "rare"}, acc))

# ---- the runner, against a local stand-in of llama-server
SEEN: list[dict] = []
MODE = {"fail": False, "budget": True, "think": True, "n_ctx": 16384}
ANSWER = simlib.Stub("warrior", 5)
NATURAL = 1500                     # how long the stand-in thinks when nothing caps it


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def reply(self, code, obj):
        data = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path == "/props":
            return self.reply(200, {"build_info": "b-test", "total_slots": 1, "default_generation_settings": {"n_ctx": MODE["n_ctx"]}})
        return self.reply(404, {"error": "no"})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8"))
        if self.path != "/v1/chat/completions":
            return self.reply(404, {"error": "no route"})
        SEEN.append(body)
        if MODE["fail"] and body.get("max_tokens") != 8:                         # the warm-up answers; every call after it fails
            return self.reply(500, {"error": {"message": "the model fell over", "code": 500}})
        user = body["messages"][-1]["content"]
        think = body["chat_template_kwargs"]["enable_thinking"] and MODE["think"] and "grammar" not in body   # (f544) a raw grammar binds at once
        budget = body.get("thinking_budget_tokens") if MODE["budget"] else None
        ANSWER.parts_bad = budget == 1024                                        # the capped arm answers past every cap, with ids
        content = json.dumps(ANSWER.a_SituationParts(user, {}))
        thought = (min(budget, NATURAL) if budget else NATURAL) if think else 0
        finish = "stop"
        if think and budget is None and "PLACE: parth" in user and body.get("max_tokens", 0) > 4000:   # uncapped at Parth: all the room thought
            content, finish = "", "length"
        if content and "response_format" in body:
            content = "```json\n" + content + "\n```"                              # (f527) Gemma 4's parser fences a response_format answer
        resp = {"choices": [{"index": 0, "finish_reason": finish, "message": {"role": "assistant", "content": content,
                                                                             **({"reasoning_content": "hmm " * thought} if think else {})}}],
                "usage": {"prompt_tokens": 1200, "completion_tokens": thought + len(content) // 4},
                "timings": {"prompt_n": 1200, "prompt_ms": 300.0, "predicted_n": 150, "predicted_ms": 700.0}}
        self.reply(200, resp)


def runs(argv):
    """The runner's main, its refusal (SystemExit) given back as its words."""
    try:
        return ab.main(argv)
    except SystemExit as e:
        return str(e.code)


def calls(seen):
    """The calls of the cases themselves: not the warm-up, not the probe."""
    return [b for b in seen if b.get("max_tokens") != 8 and b.get("thinking_budget_tokens") != ab.PROBE_BUDGET]


server = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
threading.Thread(target=server.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{server.server_address[1]}"
tmp = Path(tempfile.mkdtemp(prefix="situation_ab_543_"))
out1, out2 = tmp / "one", tmp / "two"
args = ["--server", url, "--cases", "4", "--seed", "543", "--arms", "off,budget_1024,uncapped", "--scratch", "situation_ab_543_run"]
from storage.campaign import SAVES_DIR
ab.main(args + ["--out", str(out1)])
rows1 = ab.load_rows(out1)
seen1 = calls(SEEN)
check("the server is warmed first, with a call too small to measure", SEEN and SEEN[0]["max_tokens"] == 8, SEEN[:1])
probe = [b for b in SEEN if b.get("thinking_budget_tokens") == ab.PROBE_BUDGET]
meta1 = json.loads((out1 / "meta.json").read_text())
check("before any case the server is probed: a call capped at a small budget, its thinking held near it", len(probe) == 1
      and probe[0]["chat_template_kwargs"]["enable_thinking"] and meta1["probe"]["thinking_tokens"] <= ab.PROBE_MOST
      and meta1["facts"]["n_ctx"] == 16384, meta1.get("probe"))
check("the scratch save is removed after the run", not (SAVES_DIR / "situation_ab_543_run").exists())
SEEN.clear()
ab.main(args + ["--out", str(out2)])
rows2 = ab.load_rows(out2)
cases = sorted({r["case"] for r in rows1})
check("one row a case and arm", len(rows1) == 12 and len(cases) == 4 and {(r["case"], r["arm"]) for r in rows1}
      == {(c, a) for c in cases for a in ("off", "budget_1024", "uncapped")}, [(r["case"], r["arm"]) for r in rows1])
check("the same seed gives the same cases and the same prompts in a second run", [(r["case"], r["arm"], r["pressure"], r["tier"], r["prompt_hash"]) for r in rows1]
      == [(r["case"], r["arm"], r["pressure"], r["tier"], r["prompt_hash"]) for r in rows2] and len({r["prompt_hash"] for r in rows1}) > 1)
check("the cases are at settlements, at the rare and the campaign tiers both", {r["tier"] for r in rows1} == {"rare", "campaign"}
      and all(any(world.places[q].residents for q in __import__("engine.retrieval", fromlist=["x"]).town_places(world, pulse.town_of(world, r["place"])))
              for r in rows1), {(r["pressure"], r["place"]) for r in rows1})
check("the arms go in turn, the order turning case by case", [r["arm"] for r in rows1[:3]] == ["off", "budget_1024", "uncapped"]
      and [r["arm"] for r in rows1[3:6]] == ["budget_1024", "uncapped", "off"], [r["arm"] for r in rows1])
off_b = [b for b in seen1 if not b["chat_template_kwargs"]["enable_thinking"]]
cap_b = [b for b in seen1 if "thinking_budget_tokens" in b]
unc_b = [b for b in seen1 if b["chat_template_kwargs"]["enable_thinking"] and "thinking_budget_tokens" not in b]
spec_max = situations.S["proposal"]["max_tokens"]
check("thinking off: the template's switch off, no budget field, the answer's own ceiling", len(off_b) == 4 and all("thinking_budget_tokens" not in b
      and b["max_tokens"] == spec_max for b in off_b), [(b["max_tokens"], sorted(b)) for b in off_b][:1])
check("a capped arm: thinking on, the budget field at its budget, room for it beside the answer", len(cap_b) == 4
      and all(b["thinking_budget_tokens"] == 1024 and b["max_tokens"] == spec_max + 1024 for b in cap_b), [b.get("max_tokens") for b in cap_b])
slot = ab.slot_tokens()
check("uncapped: thinking on, no budget field, room up to what the runtime's slot holds beside the prompt and the answer", len(unc_b) == 4
      and slot == 16384 and all(spec_max + 1024 < b["max_tokens"] < slot for b in unc_b), [b.get("max_tokens") for b in unc_b])
check("every body carries the schema as response_format (never the raw grammar, which binds before any thinking) and the task's samplers",
      all(b["response_format"]["json_schema"]["name"] == "SituationParts" and "grammar" not in b and b["response_format"]["json_schema"]["schema"]
          and "temperature" in b and "top_k" in b for b in seen1), sorted(seen1[0]))
check("the fence around a response_format answer is taken off and counted, never a leak", all(r["fenced"] and not r["leaked"]
      for r in rows1 if r["content_chars"]) and any(r["fenced"] for r in rows1))
offs = [r for r in rows1 if r["arm"] == "off"]
caps_ = [r for r in rows1 if r["arm"] == "budget_1024"]
check("off's answers are kept whole", all(r["valid"] and r["accepted_n"] > 0 and not r["dropped"] for r in offs), [(r["accepted_n"], r["dropped"]) for r in offs])
check("the capped arm's bad answers are dropped part by part, every reason recorded", all(r["valid"] and len(r["dropped"]) >= 5
      and R["player"] in r["dropped"] for r in caps_), [r["dropped"] for r in caps_][:1])
check("each row has its finish, tokens, card seconds and the server's field names", all(r.get("finish") and r.get("prompt_tokens") == 1200
      and isinstance(r.get("card_seconds"), float) and "choices" in r.get("fields", []) for r in rows1), rows1[0])
check("the budget sent is recorded on the capped arm and on no other", all((r.get("budget_sent") == 1024) == (r["arm"] == "budget_1024") for r in rows1))
check("a capped call held to its budget is not flagged; no answer leaked thinking", not any(r["over_budget"] or r["leaked"] or r["no_thinking"] for r in rows1))
parth = [r for r in rows1 if r["arm"] == "uncapped" and r["place"] == "parth"]
check("an answer cut off with all its room spent thinking is thought_out, kept as nothing", parth and all(r["finish"] == "thought_out"
      and not r["valid"] and r["accepted_n"] == 0 and r["error"] == "no answer" for r in parth), [(r["place"], r["finish"]) for r in rows1 if r["arm"] == "uncapped"])
check("a thinking arm's tokens are shared out between its thinking and its answer", all(r["thinking_tokens"] == (1024 if r["arm"] == "budget_1024" else NATURAL)
      for r in rows1 if r["think"]) and all(not r.get("thinking_tokens") for r in offs), [(r["arm"], r.get("thinking_tokens")) for r in rows1])

# ---- the packs
key = json.loads((out1 / "key.json").read_text())
packs = sorted((out1 / "pack").glob("pack_*.md"))
texts = {p.name: p.read_text() for p in packs}
pairs = key["pairs"]
both = {}
for n, k in pairs.items():
    arm = k["B"] if k["A"] == "off" else k["A"]
    both.setdefault((k["case"], arm), set()).add("A" if k["A"] == arm else "B")
cards = [c for t_ in texts.values() for c in re.findall(r"^### [AB]\n\n(.*?)(?=\n\n## |\n\n### |\Z)", t_, re.S | re.M)]
check("each thinking arm against off in both slot orders, every pair in a pack", both and all(v == {"A", "B"} for v in both.values())
      and len(pairs) == 2 * len(both) and len(cards) == 2 * len(pairs) and sum(len(re.findall(r"^## Pair ", t_, re.M)) for t_ in texts.values()) == len(pairs),
      (len(pairs), len(cards), both))
per_pack = {}
for n, k in pairs.items():
    per_pack.setdefault(k["pack"], []).append(k["case"])
check("no pack holds a case twice, so no card is seen again by its reader", per_pack and all(len(v) == len(set(v)) for v in per_pack.values())
      and len(packs) == max(len(v) for v in {c: [n for n, k in pairs.items() if k["case"] == c] for c in {k["case"] for k in pairs.values()}}.values()), per_pack)
rows_by = {(r["case"], r["arm"]): r for r in rows1}
identical = sum(1 for (c, a), r in rows_by.items() if a != "off" and r["card"] == rows_by[(c, "off")]["card"])
check("a pair whose two cards say the same is left out, and counted", key["same"] == identical and identical >= 1, (key["same"], identical))
all_text = "\n".join(texts.values())
lower_ids = {w for w in list(world.places) + list(world.roads) if w != w.title().lower() or "_" in w}     # ids that are no plain word
check("no arm named, no id and no underscore in any pack", cards and not any(a in all_text for a in ("budget_1024", "uncapped", "thinking off", "thinking on"))
      and "_" not in all_text and not any(re.search(rf"\b{re.escape(i)}\b", " ".join(cards)) for i in lower_ids), [c[:200] for c in cards[:2]])
check("the key lies beside the results, not among the packs", not list((out1 / "pack").glob("*.json")) and (out1 / "key.json").exists())
check("the packs say what readers judge and how to answer", all("ways in" in t_ and "A, B or tie" in t_ for t_ in texts.values()))
check("the summary is written, its table one line an arm", all(f"| {a} |" in (out1 / "summary.md").read_text() for a in ("off", "budget_1024", "uncapped")))

# ---- a run already there, stopped, resumed
check("a second run into the same folder is refused without --force or --resume", "--resume" in str(runs(args + ["--out", str(out1)])))
import itertools
from tools import think_ab
real_post, count = think_ab.post, itertools.count()


def stops_after(n):
    def post(u, body, timeout):
        if body.get("max_tokens") != 8 and body.get("thinking_budget_tokens") != ab.PROBE_BUDGET and next(count) >= n:
            raise KeyboardInterrupt
        return real_post(u, body, timeout)
    return post


out5 = tmp / "stopped"
think_ab.post = stops_after(5)
runs(args + ["--out", str(out5)])
think_ab.post = real_post
rows5 = ab.load_rows(out5)
meta5 = json.loads((out5 / "meta.json").read_text())
check("an interrupted run keeps every row measured, says it stopped, and writes its packs and key", len(rows5) == 5 and meta5.get("stopped") == "interrupted"
      and (out5 / "key.json").exists() and "stopped early" in (out5 / "summary.md").read_text(), (len(rows5), meta5.get("stopped")))
SEEN.clear()
runs(args + ["--out", str(out5), "--resume"])
rows5b = ab.load_rows(out5)
check("--resume measures only what the run lacks", len(rows5b) == 12 and len({(r["case"], r["arm"]) for r in rows5b}) == 12
      and len(calls(SEEN)) == 7, (len(rows5b), len(calls(SEEN))))
check("...and the cards it ends with are the uninterrupted run's", {(r["case"], r["arm"]): r["card"] for r in rows5b} == {(r["case"], r["arm"]): r["card"] for r in rows1})
check("--resume with another seed is refused", "seed" in str(runs(["--server", url, "--cases", "4", "--seed", "544", "--arms", "off,budget_1024,uncapped",
                                                              "--scratch", "situation_ab_543_run", "--out", str(out5), "--resume"])))
check("a scratch save not named for the tool is never made afresh", "begin with" in str(runs(["--stub", "--cases", "1", "--scratch", "my_campaign",
                                                                                          "--out", str(tmp / "x")])))

# ---- a server that does not hold the budget, does not think, or gives a slot too small: stopped before any case
for what, change, words in (("ignores the budget field", {"budget": False}, "--budget-field"), ("does not think", {"think": False}, "no thinking"),
                            ("gives each slot less than the game's", {"n_ctx": 8192}, "slot")):
    MODE.update(change)
    outx = tmp / f"probe_{change.popitem()[0]}"
    said = runs(args + ["--out", str(outx)])
    MODE.update({"budget": True, "think": True, "n_ctx": 16384})
    check(f"a server that {what} stops the run before any case, its results untouched", words in str(said) and not (outx / "results.jsonl").exists(), said)

# ---- the game's own raw grammar: a call asked to think cannot, and the run says so before any case
outg = tmp / "grammar"
said = runs(args + ["--out", str(outg), "--constraint", "grammar"])
gb = [b for b in SEEN if "grammar" in b]
check("--constraint grammar sends the game's raw grammar, and with it the probe finds no thinking and names the schema as the way",
      "--constraint schema" in str(said) and gb and all("response_format" not in b for b in gb) and not (outg / "results.jsonl").exists(), said)
check("ab.unfenced takes a fence off and leaves plain JSON alone", ab.unfenced("```json\n{\"a\": 1}\n```") == ('{"a": 1}', True)
      and ab.unfenced('{"a": 1}') == ('{"a": 1}', False))

# ---- a server that fails: each call kept as failed, and the run stops after --give-up of them in a row
MODE["fail"] = True
out4 = tmp / "failing"
runs(["--server", url, "--cases", "3", "--seed", "543", "--arms", "off", "--scratch", "situation_ab_543_run", "--out", str(out4), "--give-up", "2"])
MODE["fail"] = False
rows4 = ab.load_rows(out4)
check("a call the server fails is kept as failed, its status and the server's words recorded, nothing kept from it", rows4
      and all(r["finish"] == "failed" and r["status"] == 500 and "fell over" in r.get("error", "") and r["accepted_n"] == 0
              and r["card_seconds"] is None for r in rows4), rows4[:1])
check("...and after --give-up failures in a row the run stops, saying so", len(rows4) == 2 and "stopped early" in (out4 / "summary.md").read_text())

# ---- the decision, by the rule fixed in advance, on planted rows and reads
def planted(x_secs=40.0, x_kept=3, cases_n=10, failed=0, **flags):
    rs = []
    for c in range(cases_n):
        rs.append({"case": c, "arm": "off", "accepted_n": 3, "accepted": {"person": 3}, "card_seconds": 9.0, "finish": "stop", "valid": True})
        bad_ = c < failed
        rs.append({"case": c, "arm": "budget_1024", "accepted_n": 0 if bad_ else x_kept, "accepted": {} if bad_ else {"person": x_kept},
                   "card_seconds": None if bad_ else x_secs, "finish": "failed" if bad_ else "stop", "valid": not bad_,
                   **{k: (c == 0) for k in flags}})
    return rs


def key_and_reads(a_wins, a_losses, b_wins, b_losses, ties=0):
    """Pairs with the thinking arm in slot A (a_*), then in slot B (b_*): its wins and losses, and ties spread over both."""
    k, reads, n = {"pairs": {}}, [], 0
    for slot_, wins, losses in (("A", a_wins, a_losses), ("B", b_wins, b_losses)):
        for i in range(wins + losses):
            n += 1
            k["pairs"][str(n)] = {"A": "budget_1024", "B": "off", "case": n} if slot_ == "A" else {"A": "off", "B": "budget_1024", "case": n}
            reads.append((str(n), slot_.lower() if i < wins else ("b" if slot_ == "A" else "a")))
    for i in range(ties):
        n += 1
        k["pairs"][str(n)] = {"A": "off", "B": "budget_1024", "case": n}
        reads.append((str(n), "tie"))
    return k, reads


k, reads = key_and_reads(4, 1, 3, 2, ties=2)
d = ab.decide(planted(), k, reads)
check("preferred in 7 of 10 reads that are not ties (2 ties), in both orders, no fewer parts, within the slot: in",
      d["verdict"] == "budget_1024" and d["arms"]["budget_1024"]["passes"] and d["arms"]["budget_1024"]["preferred_share"] == 0.7, d["arms"])
k, reads = key_and_reads(3, 2, 3, 2)
check("exactly 6 of 10, more than half in each order: in (the share is the owner's floor, met)", ab.decide(planted(), k, reads)["verdict"] == "budget_1024")
k, reads = key_and_reads(3, 2, 2, 3)
d = ab.decide(planted(), k, reads)
check("5 of 10: out, thinking stays off", d["verdict"] == "off" and not d["arms"]["budget_1024"]["passes"], d["arms"])
k, reads = key_and_reads(8, 0, 2, 4)
d = ab.decide(planted(), k, reads)
check("preferred overall (10 of 14) but only in one slot order: out", d["verdict"] == "off"
      and any("both orders" in w for w in d["arms"]["budget_1024"]["why"]), d["arms"])
k, reads = key_and_reads(5, 0, 3, 3)
d = ab.decide(planted(), k, reads)
check("8 of 11, but exactly half in one order: out", d["verdict"] == "off" and any("slot B" in w for w in d["arms"]["budget_1024"]["why"]), d["arms"])
k, reads = key_and_reads(4, 1, 3, 2)
d = ab.decide(planted(x_secs=130.0), k, reads)
check("a p90 of 130 s on the card, past the slot's 120: out", d["verdict"] == "off" and any("130" in w for w in d["arms"]["budget_1024"]["why"]), d["arms"])
d = ab.decide(planted(x_kept=2), k, reads)
check("fewer parts kept a proposal than off: out", d["verdict"] == "off" and any("fewer" in w for w in d["arms"]["budget_1024"]["why"]), d["arms"])
d = ab.decide(planted(failed=2), k, reads)
st = d["stats"]["budget_1024"]
check("failed calls are past any limit and keep no parts: 2 of 10 failed puts the p90 past the slot, and the parts a proposal fall", d["verdict"] == "off"
      and st["p90_card_seconds"] is None and st["failed"] == 2 and st["accepted_per_proposal"] == 2.4
      and any("past any limit" in w for w in d["arms"]["budget_1024"]["why"]), (st, d["arms"]["budget_1024"]["why"]))
check("...one failed in 10 leaves the p90 on the rest", ab.arm_stats(planted(failed=1))["budget_1024"]["p90_card_seconds"] == 40.0)
for flag, words in (("over_budget", "budget"), ("no_thinking", "without thinking")):
    d = ab.decide(planted(**{flag: True}), k, reads)
    check(f"an arm with a call flagged {flag} does not pass", d["verdict"] == "off" and any(words in w for w in d["arms"]["budget_1024"]["why"]), d["arms"])
d = ab.decide(planted(), {"pairs": {}}, [])
check("no reads at all: out", d["verdict"] == "off")
two = planted() + [{"case": c, "arm": "budget_2048", "accepted_n": 3, "accepted": {}, "card_seconds": 60.0, "finish": "stop", "valid": True} for c in range(10)]
k2, reads2 = key_and_reads(4, 1, 3, 2)
for n, v in list(k2["pairs"].items()):
    m = str(int(n) + 100)
    k2["pairs"][m] = {kk: ("budget_2048" if vv == "budget_1024" else vv) for kk, vv in v.items()}
    reads2.append((m, dict(reads2)[n]))
d = ab.decide(two, k2, reads2)
check("two arms passing: the one cheaper on the card at p90", d["verdict"] == "budget_1024" and d["arms"]["budget_2048"]["passes"], d["arms"])
check("uncapped that never thinks past the largest budget is warned of", any("uncapped never thought past" in w for w in ab.warnings_of(
      [{"case": 0, "arm": "uncapped", "thinking_tokens": 900, "card_seconds": 30.0, "accepted_n": 2}])))

# ---- the reads
rf = tmp / "reads.txt"
rf.write_text("# reader one\npair 1: A\n2 b\n3) tie   # unsure\n## Pair 12: A\n#13 B\nPair 21 \u2014 A\n19 A 20 B\n4 - B\n")
got_reads, unread = ab.read_reads(rf)
check("the reads: a pair's number then A, B or tie, as the pack's own headings or with any dash, several to a line, comments passed over",
      got_reads == [("1", "a"), ("2", "b"), ("3", "tie"), ("12", "a"), ("13", "b"), ("21", "a"), ("19", "a"), ("20", "b"), ("4", "b")]
      and not unread, (got_reads, unread))
rf.write_text("1 A\nthe second one felt thin\n")
check("...a line that is neither a read nor a comment is named, not passed over", ab.read_reads(rf)[1] and "felt thin" in ab.read_reads(rf)[1][0])


def refused(fn):
    try:
        fn()
        return ""
    except SystemExit as e:
        return str(e.code)


check("...and the decision refuses a reads file holding one", "neither a read nor a comment" in refused(lambda: ab.finish_decision(out1, rows1, rf)))

# ---- the decision written, and the measured file checked
lines = [f"{n} {'A' if kk['A'] == 'off' else 'B'}" for n, kk in key["pairs"].items()]          # every reader prefers off
rf.write_text("\n".join(lines[: len(lines) // 2]) + "\n")
rf2 = tmp / "reads2.txt"
rf2.write_text("# the second reader\n" + "\n".join(lines[len(lines) // 2:]) + "\n")
measured = tmp / "situation_thinking.yaml"
d = ab.finish_decision(out1, rows1, [rf, rf2], str(measured))
summary = (out1 / "summary.md").read_text()
check("two readers' files read together; readers who prefer off keep thinking off, the summary saying so with every arm's reasons",
      d["verdict"] == "off" and d["reads"] == len(lines) and "thinking stays off everywhere" in summary and "budget_1024**: does not pass" in summary
      and f"{key['same']} pair(s) left out" in summary, summary[-900:])
doc = yaml.safe_load(measured.read_text())
check("the measured file names the task, the arms and the verdict, and passes the game's check", doc["task"] == "situation_parts"
      and set(doc["arms"]) == {"off", "budget_1024", "uncapped"} and doc["verdict"] == "off" and not situations.measured_problems(doc), doc)
wrong = dict(doc, arms=dict(doc["arms"], budget_4096=doc["arms"]["off"]))
check("one naming an arm the data does not know is refused", any("budget_4096" in p for p in situations.measured_problems(wrong)))
check("...a verdict that is no arm, or a task the budget does not know, refused", any("verdict" in p for p in situations.measured_problems(dict(doc, verdict="maybe")))
      and any("task" in p for p in situations.measured_problems(dict(doc, task="situation_partz"))))
check("...a verdict for an arm that did not pass the rule, refused", any("did not pass" in p or "passed the rule" in p
      for p in situations.measured_problems(dict(doc, verdict="budget_1024"))))
check("...a measure that is no number, refused", any("p90_card_seconds" in p for p in situations.measured_problems(
      dict(doc, arms=dict(doc["arms"], off=dict(doc["arms"]["off"], p90_card_seconds="fast"))))))
check("...a file of the wrong shape is reported, never a crash", situations.measured_problems(["x"]) and situations.measured_problems(
      dict(doc, arms={"off": ["x"]})))
check("no measured file in the repository yet: nothing to check", situations.measured_problems() == []
      if not (ROOT / "data/measured/situation_thinking.yaml").exists() else True)
with (out1 / "results.jsonl").open("a") as f:
    f.write(json.dumps(dict(rows1[0], case=99)) + "\n")
check("results changed after the packs were made: the decision refuses them until the packs are made again",
      "make them again with --pack" in refused(lambda: ab.finish_decision(out1, ab.load_rows(out1), [rf, rf2])))
ab.main(["--pack", str(out1)])
check("...--pack makes them again from the results", json.loads((out1 / "key.json").read_text())["results_sha256"] == ab._sha(out1 / "results.jsonl"))

# ---- the data's own checks
S0 = copy.deepcopy(situations.S)
for path, value, words in ((("proposal", "max_tokens"), 0, "proposal.max_tokens"), (("proposal", "people_most"), "many", "proposal.people_most"),
                           (("thinking", "slot_seconds"), -5, "thinking.slot_seconds")):
    situations.S[path[0]][path[1]] = value
    check(f"situations.yaml {'.'.join(path)} of {value!r} is refused", any(words in p for p in situations.problems()))
    situations.S.clear(); situations.S.update(copy.deepcopy(S0))
held = pp.PARTS_SYSTEM
for word, rep, lst in (("kin,", "cousins,", "ties"), ("sure (they saw it", "certain (they saw it", "certainties")):
    pp.PARTS_SYSTEM = held.replace(word, rep, 1)
    check(f"a list word given only by chance elsewhere in the prompt is still missed ({lst})", any(f"lists.{lst}" in p for p in situations.problems()))
    pp.PARTS_SYSTEM = held

# ---- the stand-in path: the whole run through the game's gateway
out3 = tmp / "stub"
ab.main(["--stub", "--cases", "2", "--seed", "9", "--arms", "off,budget_1024", "--scratch", "situation_ab_543_stub", "--out", str(out3)])
rows3 = ab.load_rows(out3)
check("--stub runs every case and arm through the gateway, each answer kept", len(rows3) == 4 and all(r["valid"] and r["accepted_n"] > 0
      and r["finish"] == "stop" for r in rows3), rows3[:1])
made = ab._residents_stub


def empty_answers(seed):
    s_ = made(seed)
    s_.a_SituationParts = lambda u, k: {}                       # no part at all: the contract refuses every try
    return s_


ab._residents_stub = empty_answers
out6 = tmp / "stub_failing"
ab.main(["--stub", "--cases", "1", "--seed", "9", "--arms", "off", "--scratch", "situation_ab_543_stub", "--out", str(out6)])
ab._residents_stub = made
rows6 = ab.load_rows(out6)
check("--stub: a call the gateway gives up on is failed, never a stop", rows6 and all(r["finish"] == "failed" and r["error"] for r in rows6), rows6[:1])

server.shutdown()
shutil.rmtree(tmp, ignore_errors=True)
for name in ("situation_ab_543", "situation_ab_543_run", "situation_ab_543_stub"):
    shutil.rmtree(ROOT / "saves" / name, ignore_errors=True)
print("ALL PASS" if not bad else f"{len(bad)} FAILED: {bad}")
sys.exit(1 if bad else 0)
