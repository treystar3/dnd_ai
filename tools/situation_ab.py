"""(f543) A situation's parts proposed with thinking off and on, measured before the owner decides whether the proposal thinks (f544).

The owner's direction: thinking belongs where the model makes a typed proposal the engine checks, never in what the player reads. This
tool measures it on the one call that may think, the situation's parts (engine/situations.py prompt, llm/contracts.py SituationParts):

  1. A scratch world, the same for the same --seed: a fresh campaign (saves/situation_ab*, removed after the run), each case's town
     peopled by the engine with names it draws itself (no model), so PEOPLE has ids and every arm reads the same town.
  2. Cases: --cases N of (a pressure at a settlement, the rare or the campaign tier), chosen on the seed; each case's prompt is the one
     the game would send (situations.prompt), its request the one llama-server would be sent (tools/think_ab.py llama_body: every
     sampler, the template's enable_thinking), the answer's shape sent to every arm alike as response_format (--constraint schema,
     f544: the server binds it after the thinking; the game's own raw grammar binds from the first token, so nothing could think),
     and the ```json fence Gemma 4 then writes around an answer taken off and counted.
  3. Arms (data/rules/situations.yaml thinking.arms): off; capped per request at a budget of thinking tokens (the server's field,
     --budget-field, sent only on a capped arm); uncapped within the background slot (data/runtime/server.yaml slot_ctx). Before any
     case: the server's slot must hold that slot, a thinking call must come back with thinking, and a call capped at a small budget
     must come back answered with its thinking near that budget, or the run stops there (a field the server ignores would otherwise
     measure a different arm). The arms go in turn for each case, the order turning, so none always finds the prompt cached.
  4. Each answer scored by the game's own contract and check (situations.check against the scratch world): the parts accepted by kind,
     every reason a part was dropped, how the call finished (stop, length, thought_out: the room spent on thinking with no answer, or
     failed), the tokens, and what the call would take on the minimum card (data/measured/card_profile.yaml); a capped call that went
     past its budget, a thinking call that came back without thinking, and an answer that is not the JSON alone are flagged.
  5. Blind packs (pack/pack_N.md; key.json apart, beside the results): each case's accepted parts as the engine renders them, each
     part worded by its own content (no model prose; the same parts read the same whatever the arm or the order), each thinking arm
     paired with off in both slot orders, a case at most once a pack, so no card is seen again: each pack for its own reader. Readers
     write one line a pair: its number, then A, B or tie.
  6. The decision, by the rule fixed in advance (situations.yaml thinking): an arm goes in only if readers prefer it in prefer_share of
     the reads that are not ties, more often than not in each slot order, with no fewer parts accepted per proposal than off (a failed
     call keeps none), its p90 on the card within slot_seconds (a failed call is past any limit), and the server holding its budget.
     summary.md says which, or that thinking stays off.

    python tools/situation_ab.py --server http://127.0.0.1:8080 --cases 30 --out situation_ab/
    python tools/situation_ab.py --server URL --cases 30 --out situation_ab/ --resume        a stopped run picked up where it was
    python tools/situation_ab.py --pack situation_ab/                                          the packs made again from the results
    python tools/situation_ab.py --decide situation_ab/ --reads r1.txt r2.txt --measured data/measured/situation_thinking.yaml
    python tools/situation_ab.py --stub --cases 4 --out scratch/situation_ab/     the whole run through the game's gateway, no server

It writes results.jsonl (one row a case and arm, as each comes), summary.md (as the run goes), meta.json, key.json and pack/. A run
stopped (an interrupt, SIGTERM, the server failing --give-up calls in a row) keeps every row and writes its packs. It sends nothing
anywhere but the server named."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import re
import shutil
import signal
import sys
import time
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TASK = "situation_parts"
TIERS = ("rare", "campaign")
SCRATCH = "situation_ab"
KINDS = ("person", "resource", "tie", "condition", "evidence")
PROBE_BUDGET = 64                  # the small budget the probe asks for; its thinking must stay near it
PROBE_MOST = 4 * PROBE_BUDGET      # thinking past this on the probe: the server did not hold the budget
OVER = 1.25                        # a capped call whose thinking passes its budget by more than this was not held to it
READ = re.compile(r"(?:pair\s*)?(\d+)\s*[:.)\-–—]*\s*\b(a|b|tie)\b", re.I)


def slot_tokens() -> int:
    """The background slot's context: the runtime's own (data/runtime/server.yaml slot_ctx), so the measurement is of the slot the game
    gives the call."""
    from llm import runtime
    return int((runtime.settings().get("server") or {}).get("slot_ctx") or 16384)


# ---------- the scratch world

def _residents_stub(seed: int):
    """simlib's stand-in, its residents named by the game's own name builder (npc/names.py) on the seed, so a town reads as one."""
    import simlib
    from npc import names

    class Residents(simlib.Stub):
        def a_ResidentSet(self, u, k):
            roles = re.findall(r"slot \d+: (\w+)", u)
            out = []
            for i, r in enumerate(roles):
                name, _ = names.pick("human", self.taken, self.rng)
                self.taken.append(name)
                out.append({"slot": i + 1, "name": name, "epithet": f"the {r.replace('_', ' ')}", "description": "A person of the town.",
                            "activity": "going about their work"})
            return {"residents": out}
    stub = Residents("warrior", seed)
    stub.taken = []
    return stub


def build_world(seed: int, name: str = SCRATCH):
    """A fresh scratch campaign on the seed: (session, store, world, catalog). Only a save named for this tool is ever made afresh."""
    from engine.session import CampaignSession
    from npc.traits import load_traits
    from storage.campaign import SAVES_DIR
    if not name.startswith(SCRATCH):
        raise SystemExit(f"the scratch save's name must begin with {SCRATCH!r} (it is removed and made afresh): {name!r}")
    shutil.rmtree(SAVES_DIR / name, ignore_errors=True)
    session = CampaignSession.open(name)
    store = session.store
    store.meta.seed = seed
    store.save_meta()
    return session, store, session.world, load_traits()


def drop_world(session, name: str) -> None:
    from storage.campaign import SAVES_DIR
    try:
        session.close()
    finally:
        shutil.rmtree(SAVES_DIR / name, ignore_errors=True)


def cases(world, n: int, seed: int) -> list[dict]:
    """N cases of (pressure, tier) on the seed, at settlements (a wild place has no people of its own for a situation to cast, so
    there is little to propose there and nothing to tell the arms apart by): the pressures in a seeded order, the tiers in turn (and
    turned again each time the pressures come round, so a pressure met twice is met at both tiers); each case's place where the
    pressure is, or a town of its region (as pulse.start_thread finds one)."""
    from engine import pulse, retrieval
    order = sorted(world.pressures)
    random.Random(f"{seed}:cases").shuffle(order)
    found = []
    for pid in order:
        pr = world.pressures[pid]
        place = world.places.get(pr.place) or pulse.region_town(world, pr.place, random.Random(f"{seed}:{pid}"))
        if not place:
            continue
        town = pulse.town_of(world, place.id)
        if any(world.places[q].residents for q in retrieval.town_places(world, town)):
            found.append((pid, place.id, town))
    out = []
    for i in range(n if found else 0):
        pid, place, town = found[i % len(found)]
        out.append({"i": i, "pressure": pid, "tier": TIERS[(i + i // len(found)) % len(TIERS)], "place": place, "town": town,
                    "trouble": world.pressures[pid].description})
    return out


def people_towns(store, world, catalog, towns) -> None:
    from npc.life import populate_place
    for town in sorted(set(towns)):
        populate_place(store, world, town, catalog)


def prompt_of(store, world, case: dict, t: int) -> dict:
    """The case's prompt as a birth with no way through offered yet would be asked it (ways False, as score checks it)."""
    from engine import situations
    system, user = situations.prompt(store, world, store.load_world_state() or {}, world.places[case["place"]], case["tier"], t,
                                     case["trouble"], ways=False)
    return {"system": system, "user": user, "hash": hashlib.sha256((system + "\n" + user).encode("utf-8")).hexdigest()[:16]}


def row_of(p: dict) -> dict:
    """The request as the game's gateway would make it (system then user; the task's sampling, its first try; the answer's ceiling)."""
    from engine import situations
    from llm import sampling
    spec = situations.S["proposal"]
    plan = sampling.resolve(TASK, float(spec["temperature"]))
    return {"request": {"messages": [{"role": "system", "content": p["system"]}, {"role": "user", "content": p["user"]}],
                        "sampling": plan.at(0).resolved(), "max_tokens": int(spec["max_tokens"])}}


CONSTRAINTS = ("schema", "grammar")


def body_of(row: dict, spec: dict, budget_field: str, slot: int, model: str | None = None, constraint: str = "schema") -> dict:
    """The llama-server body for one arm: think_ab's, with the room a thinking arm gets (its budget, or the slot for uncapped, never more
    than the slot holds beside the prompt and the answer) and the budget field on a capped arm alone.

    (f544) The answer's shape, the same for every arm so thinking is the one thing that differs: "schema" (the default) sends it as
    response_format, as f533 did, which the server's chat template turns into a grammar that binds only after the thinking; "grammar"
    sends the game's own raw grammar (llm/llama.py since f527), which binds from the first token, so a call asked to think cannot."""
    from llm.contracts import SituationParts
    from tools import think_ab
    think_ab.NUM_CTX = slot
    room = int(spec["budget"]) if spec.get("budget") else slot
    body = think_ab.llama_body(row, SituationParts, bool(spec["think"]), room, model)
    if constraint == "schema":
        body.pop("grammar", None)
        body["response_format"] = {"type": "json_schema", "json_schema": {"name": "SituationParts", "schema": SituationParts.model_json_schema(),
                                                                          "strict": True}}
    if spec["think"] and spec.get("budget"):
        body[budget_field] = int(spec["budget"])
    return body


FENCE = re.compile(r"^```[a-zA-Z]*\s*\n?(.*?)\n?```\s*$", re.S)


def unfenced(content: str) -> tuple[str, bool]:
    """(f544) The answer without the ```json fence Gemma 4's chat parser writes around a response_format answer (f527 found it):
    (the text, whether it was fenced). The contract reads the JSON inside; the fence is counted, never a leak."""
    text = (content or "").strip()
    m = FENCE.match(text)
    return (m.group(1).strip(), True) if m else (text, False)


# ---------- scoring

def finish_of(got: dict) -> str:
    """stop, length, thought_out (cut off with thinking written and no answer begun, as llm/gateway.py names it), or failed."""
    if got.get("finish") is None and not got.get("content"):
        return "failed"
    f = got.get("finish") or ""
    if f == "length":
        return "thought_out" if got.get("thinking") and not (got.get("content") or "").strip() else "length"
    return f or "unknown"


def thinking_tokens(got: dict) -> int | None:
    """The server counts thinking and answer as one: shared out by their length."""
    th, co, n = got.get("thinking") or "", got.get("content") or "", got.get("answer_tokens")
    if not n or not (th or co):
        return None
    return round(n * len(th) / (len(th) + len(co)))


def score(content: str, store, world, case: dict, t: int, seed: int) -> dict:
    """The contract's reading, then the engine's check (the same die for every arm, so the same parts roll the same truth)."""
    from engine import situations
    from llm.contracts import SituationParts
    out = {"valid": False, "error": "", "accepted": {}, "accepted_n": 0, "dropped": [], "parts": []}
    text, _ = unfenced(content)
    try:
        parts = SituationParts.model_validate_json(text)
    except Exception as e:
        out["error"] = f"refused by the contract: {str(e).splitlines()[0][:160]}" if text else "no answer"
        return out
    out["valid"] = True
    acc, dropped = situations.check(parts, store, world, case["tier"], random.Random(f"{seed}:{case['pressure']}:{case['tier']}:truth"),
                                    town=case["town"], ways=False, now=t)
    out["parts"] = acc
    out["accepted_n"] = len(acc)
    for a in acc:
        out["accepted"][a["kind"]] = out["accepted"].get(a["kind"], 0) + 1
    out["dropped"] = [r for _, r in dropped]
    out["dropped_parts"] = [{"part": part, "why": why} for part, why in dropped]   # (f544) what was refused, beside why
    out["proposed"] = {k: len(getattr(parts, k)) for k in ("people", "resources", "ties", "conditions", "evidence")}
    return out


def _content(part: dict) -> str:
    return json.dumps({k: v for k, v in part.items() if k not in ("true", "made_true", "lifted", "v")}, sort_keys=True)   # (f545's review)


def card(store, world, case: dict, parts: list[dict]) -> str:
    """The accepted parts as the engine renders them, in an order of their own (kind, then content) and each worded on a key of its
    content: the same parts give the same card, whatever arm proposed them and in whatever order."""
    from engine import situations
    lines = []
    for part in sorted(parts, key=lambda a: (KINDS.index(a["kind"]) if a["kind"] in KINDS else 9, _content(a))):
        key = f"ab:{case['pressure']}:{case['tier']}:" + hashlib.sha1(_content(part).encode("utf-8")).hexdigest()[:12]
        lines += [ln for ln in situations.render([part], store, world, key).splitlines() if ln.startswith("- ")]
    return "\n".join(lines) if lines else "(nothing the game could keep)"


def setting(store, world, case: dict) -> str:
    """What a reader judges the cards against: the tier, the place, the trouble, and the town's people by name and trade."""
    from engine import retrieval
    place = world.places[case["place"]]
    people = [f"{n.name} ({n.role.replace('_', ' ')})" for n in retrieval.people_in_town(store, world, case["town"])][:20]
    return (f"A {case['tier']} situation at {place.name}: {case['trouble'].strip()}\n"
            f"The town's people: {', '.join(people) or 'none met yet'}.")


# ---------- the server, checked before any case

def check_server(url_base: str, first: dict, arm_names: list[str], budget_field: str, model: str | None, slot: int,
                 say=print, timeout: float = 600.0, constraint: str = "schema") -> dict:
    """The slot the server gives a call must hold the game's slot; a thinking call must come back with its thinking; a call capped at
    PROBE_BUDGET must come back answered with its thinking near it. Any of these failing stops the run before a case is spent."""
    from engine import situations
    from tools import think_ab
    A = situations.arms()
    facts = think_ab.facts(url_base)
    out = {"facts": facts}
    n_ctx = facts.get("n_ctx")
    if isinstance(n_ctx, int) and n_ctx < slot:
        raise SystemExit(f"the server gives each slot {n_ctx} tokens of context, less than the game's slot of {slot}: start it so "
                         f"each slot holds {slot} (-c {slot} times its slots), or the uncapped arm is cut off by the slot, not its thinking")
    if not isinstance(n_ctx, int):
        say(f"  (the server did not say its slot's context; assumed to hold {slot})")
    thinking = [a for a in arm_names if A[a]["think"]]
    if not thinking:
        return out
    capped = [a for a in thinking if A[a].get("budget")]
    spec = {"think": True, "budget": PROBE_BUDGET} if capped else {"think": True, "budget": None}
    body = body_of(row_of(first), spec, budget_field, slot, model, constraint)
    if capped:
        body["max_tokens"] = int(situations.S["proposal"]["max_tokens"]) + 2048
    status, resp, took = think_ab.post(url_base.rstrip("/") + "/v1/chat/completions", body, timeout)
    got = think_ab.read_llama(resp) if status == 200 and isinstance(resp, dict) else {}
    th = thinking_tokens(got)
    out["probe"] = {"status": status, "seconds": round(took, 2), "finish": got.get("finish"), "thinking_chars": len(got.get("thinking") or ""),
                    "thinking_tokens": th, "content_chars": len(got.get("content") or ""), "budget_field": budget_field if capped else "",
                    "fields": got.get("fields"), "message_fields": got.get("message_fields")}
    if status != 200:
        raise SystemExit(f"the probe call failed (HTTP {status}): {str(resp)[:300]}")
    if not got.get("thinking"):
        raise SystemExit("a call asked to think came back with no thinking (no reasoning_content): the server or its template does not "
                         "honour enable_thinking" + (", and a raw grammar binds from the first token (--constraint schema lets it think)"
                                                     if constraint == "grammar" else "") + ", so every thinking arm would be measured as thinking off")
    if capped and (not (got.get("content") or "").strip() or th is None or th > PROBE_MOST):
        raise SystemExit(f"a call capped at {PROBE_BUDGET} thinking tokens thought about {th} and finished {got.get('finish')!r}: the server "
                         f"does not read the budget from {budget_field!r}; name the field it reads with --budget-field")
    say(f"  the server holds the slot, thinks when asked" + (f", and holds a thinking budget sent as {budget_field!r} ({th} tokens "
        f"thought against {PROBE_BUDGET})" if capped else ""))
    return out


# ---------- the run

def run(store, world, chosen: list[dict], arm_names: list[str], *, server: str = "", stub: bool = False, seed: int = 543,
        budget_field: str = "thinking_budget_tokens", model: str | None = None, timeout: float = 600.0, out: Path | None = None,
        constraint: str = "schema",
        sink=None, done: set | None = None, rows: list | None = None, give_up: int = 5, meta: dict | None = None, say=print) -> list[dict]:
    """Every case through every arm, the order turning case by case; a row a call, written to `sink` as it comes. `done` holds the
    (case, arm) already measured (a resumed run). Stops after `give_up` failed calls in a row (the server is not answering)."""
    from engine import situations
    from tools import think_ab
    A = situations.arms()
    slot = slot_tokens()
    prof = think_ab.profile()
    t = int(store.meta.minutes or 0)
    url = server.rstrip("/") + "/v1/chat/completions" if server else ""
    rows = rows if rows is not None else []
    done = done or set()
    failed_run = 0
    for case in chosen:
        p = prompt_of(store, world, case, t)
        row = row_of(p)
        turn = case["i"] % len(arm_names)
        for arm in arm_names[turn:] + arm_names[:turn]:
            if (case["i"], arm) in done:
                continue
            spec = A[arm]
            rec = {"case": case["i"], "arm": arm, "pressure": case["pressure"], "tier": case["tier"], "place": case["place"],
                   "prompt_hash": p["hash"], "think": spec["think"], "budget": spec.get("budget")}
            if stub:
                got = _stub_call(p)
            else:
                body = body_of(row, spec, budget_field, slot, model, constraint)
                rec["budget_sent"] = body.get(budget_field)
                rec["max_tokens"] = body.get("max_tokens")
                status, resp, took = think_ab.post(url, body, timeout)
                rec["status"], rec["wall_seconds"] = status, round(took, 2)
                got = think_ab.read_llama(resp) if status == 200 and isinstance(resp, dict) else {"content": "", "error": str(resp)[:300]}
            rec["finish"] = finish_of(got)
            for k in ("prompt_tokens", "answer_tokens", "fields", "message_fields", "timing_fields", "error"):
                if got.get(k) is not None:
                    rec[k] = got[k]
            thinking, content = got.get("thinking") or "", got.get("content") or ""
            rec["thinking_chars"], rec["content_chars"] = len(thinking), len(content)
            th = thinking_tokens(got)
            if th is not None:
                rec["thinking_tokens"] = th
            rec["card_seconds"] = think_ab.card_seconds(rec.get("prompt_tokens"), rec.get("answer_tokens"), prof) if rec["finish"] != "failed" else None
            bare, rec["fenced"] = unfenced(content)
            rec["leaked"] = bool(bare) and (not bare.startswith("{") or "<think" in bare.lower())
            rec["no_thinking"] = bool(spec["think"]) and rec["finish"] != "failed" and not stub and not thinking
            rec["over_budget"] = bool(spec.get("budget")) and rec["finish"] != "failed" and (
                rec["finish"] == "thought_out" or (th or 0) > OVER * int(spec["budget"]))
            sc = score(content, store, world, case, t, seed)
            rec.update({k: v for k, v in sc.items() if k not in ("parts", "error")})
            rec["answer"] = unfenced(content)[0]                                  # (f544) the proposal whole, as the contract read it,
            rec["kept_parts"] = sc["parts"]                                       # what the check kept,
            rec["thinking"] = thinking                                            # and the thinking that came before it
            if sc["error"] and not rec.get("error"):                              # the server's own error, when it gave one, stands
                rec["error"] = sc["error"]
            rec["card"] = card(store, world, case, sc["parts"])
            rec["setting"] = setting(store, world, case)
            rows.append(rec)
            if sink:
                sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
                sink.flush()
            say(f"  case {case['i'] + 1}/{len(chosen)} {arm}: {rec['finish']}, {rec['accepted_n']} part(s) kept"
                + (f", {len(rec['dropped'])} dropped" if rec["dropped"] else "") + (f" ({rec['error']})" if rec.get("error") else ""))
            failed_run = failed_run + 1 if rec["finish"] == "failed" else 0
            if give_up and failed_run >= give_up:
                say(f"  {failed_run} calls failed in a row: the server is not answering; stopped")
                if meta is not None:
                    meta["stopped"] = f"{failed_run} failed calls in a row"
                return rows
        if out:
            write_summary(out, rows, None, meta or {})
    return rows


def _stub_call(p: dict) -> dict:
    """--stub: the call through the game's own gateway (the stand-in answering), its tokens estimated from its characters."""
    from engine import situations
    from llm.contracts import SituationParts
    from llm.gateway import generate
    from llm.errors import LLMError
    spec = situations.S["proposal"]
    try:
        parts = generate("situation_parts", p["system"], p["user"], SituationParts, temperature=float(spec["temperature"]), max_tokens=int(spec["max_tokens"]))
    except LLMError as e:
        return {"content": "", "error": str(e)[:300]}                         # no finish: a failed call
    content = parts.model_dump_json()
    return {"content": content, "thinking": "", "finish": "stop", "prompt_tokens": (len(p["system"]) + len(p["user"])) // 4,
            "answer_tokens": max(1, len(content) // 4)}


# ---------- the blind packs

def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else ""


def pack(rows: list[dict], seed: int) -> tuple[list[list[dict]], dict]:
    """Each thinking arm against off, case by case, in both slot orders, spread over packs so that no pack holds a case twice (so no
    card is seen again by its reader), each pack shuffled on the seed. A pair whose two cards say the same is left out (nothing to
    choose between) and counted. -> (packs of items, key)."""
    by = {(r["case"], r["arm"]): r for r in rows}
    per_case: dict[int, list[tuple]] = {}
    same = 0
    for (case, arm), r in sorted(by.items()):
        if arm == "off" or (case, "off") not in by:
            continue
        off = by[(case, "off")]
        if off["card"] == r["card"]:
            same += 1
            continue
        per_case.setdefault(case, []).extend([(off, r), (r, off)])
    rng = random.Random(f"{seed}:pack")
    k = max((len(v) for v in per_case.values()), default=0)
    packs: list[list[tuple]] = [[] for _ in range(k)]
    for case in sorted(per_case):
        pairs = per_case[case]
        rng.shuffle(pairs)
        offset = rng.randrange(k)
        for j, pr in enumerate(pairs):
            packs[(j + offset) % k].append(pr)
    items, key, n = [], {"same": same, "pairs": {}}, 0
    for i, pk in enumerate(packs):
        rng.shuffle(pk)
        its = []
        for a, b in pk:
            n += 1
            its.append({"pair": n, "setting": a["setting"], "A": a["card"], "B": b["card"]})
            key["pairs"][str(n)] = {"A": a["arm"], "B": b["arm"], "case": a["case"], "pack": i + 1}
        items.append(its)
    return items, key


def pack_text(items: list[dict], n: int, of: int) -> str:
    out = [f"# Situation cards, read blind (pack {n} of {of})", "",
           "Each pair is two ways the same situation could be made up: who is in it and how, what goods it turns on, how its people stand "
           "to each other, what it does to places and roads, and what evidence there is. Read both cards, then choose the one that makes "
           "the better situation, judging four things together: whether the parts fit the situation; whether they give a player ways "
           "in; whether they hang together; whether anything contradicts the world or the town's people. Write one line a pair in your "
           "reads file: the pair's number, then A, B or tie (\"12 A\"). Read this pack alone: another reader reads each of the others.", ""]
    for it in items:
        out += [f"## Pair {it['pair']}", "", it["setting"], "", "### A", "", it["A"], "", "### B", "", it["B"], ""]
    return "\n".join(out)


def write_packs(folder: Path, rows: list[dict], seed: int) -> tuple[int, int]:
    """pack/pack_N.md and key.json from the rows, the key holding a fingerprint of the results and of every pack. -> (packs, pairs)."""
    items, key = pack(rows, seed)
    pdir = folder / "pack"
    shutil.rmtree(pdir, ignore_errors=True)
    pdir.mkdir(parents=True, exist_ok=True)
    key["packs"] = {}
    for i, its in enumerate(items, 1):
        path = pdir / f"pack_{i}.md"
        path.write_text(pack_text(its, i, len(items)), encoding="utf-8")
        key["packs"][path.name] = _sha(path)
    key["results_sha256"] = _sha(folder / "results.jsonl")
    (folder / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    return len(items), len(key["pairs"])


def read_reads(paths) -> tuple[list[tuple[str, str]], list[str]]:
    """Reads, a line each or several to a line: a pair's number, then A, B or tie ("12 A", "Pair 12: B", "## Pair 12 - tie"); a line
    that is only a comment (begins with #) is passed over, and words after " #" on a read's line are its comment. -> (reads, the
    lines that are neither read nor comment, as 'file:line: text')."""
    paths = [paths] if isinstance(paths, (str, Path)) else list(paths)
    reads, unread = [], []
    for path in paths:
        for i, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
            text = line.strip()
            if not text:
                continue
            core = text.lstrip("#").strip().split(" #", 1)[0]
            found = READ.findall(core)
            if found:
                reads += [(n, c.lower()) for n, c in found]
            elif not text.startswith("#"):
                unread.append(f"{Path(path).name}:{i}: {text[:80]}")
    return reads, unread


# ---------- the decision

def _q(values, q):
    from tools import think_ab
    v = think_ab._q(values, q)
    return None if v is None or math.isinf(v) else v


def arm_stats(rows: list[dict]) -> dict:
    out = {}
    for arm in sorted({r["arm"] for r in rows}, key=lambda a: (a != "off", a)):
        rs = [r for r in rows if r["arm"] == arm]
        secs = [r["card_seconds"] if r.get("card_seconds") is not None else math.inf for r in rs]   # a failed call: past any limit
        reasons: dict[str, int] = {}
        kinds: dict[str, int] = {}
        finishes: dict[str, int] = {}
        for r in rs:
            for why in r.get("dropped") or ():
                reasons[why] = reasons.get(why, 0) + 1
            for k, n in (r.get("accepted") or {}).items():
                kinds[k] = kinds.get(k, 0) + n
            finishes[r.get("finish") or "?"] = finishes.get(r.get("finish") or "?", 0) + 1
        think = [r["thinking_tokens"] for r in rs if r.get("thinking_tokens") is not None]
        out[arm] = {"n": len(rs), "valid": sum(1 for r in rs if r.get("valid")), "finishes": finishes,
                    "failed": sum(1 for r in rs if r.get("card_seconds") is None),
                    "finished_share": round(finishes.get("stop", 0) / len(rs), 3) if rs else None,
                    "accepted_per_proposal": round(sum(r.get("accepted_n", 0) for r in rs) / len(rs), 3) if rs else None,
                    "accepted_by_kind": kinds, "dropped": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
                    "p50_card_seconds": _q(secs, 0.5), "p90_card_seconds": _q(secs, 0.9),
                    "thinking_tokens_p50": _q(think, 0.5), "thinking_tokens_p90": _q(think, 0.9),
                    "thinking_tokens_most": max(think) if think else None,
                    "leaked": sum(1 for r in rs if r.get("leaked")), "no_thinking": sum(1 for r in rs if r.get("no_thinking")),
                    "fenced": sum(1 for r in rs if r.get("fenced")),
                    "over_budget": sum(1 for r in rs if r.get("over_budget"))}
    return out


def warnings_of(rows: list[dict]) -> list[str]:
    from engine import situations
    st, A, out = arm_stats(rows), situations.arms(), []
    for arm, s in st.items():
        if s["failed"]:
            out.append(f"{arm}: {s['failed']} of {s['n']} calls failed (counted as past the slot in its p90, and as no parts kept)")
        if s["leaked"]:
            out.append(f"{arm}: {s['leaked']} answers were not the JSON alone")
        if s["no_thinking"]:
            out.append(f"{arm}: {s['no_thinking']} calls asked to think came back without thinking")
        if s["over_budget"]:
            out.append(f"{arm}: {s['over_budget']} calls went past their thinking budget: the server did not hold it")
    budgets = [a["budget"] for a in A.values() if a.get("budget")]
    unc = st.get("uncapped")
    if unc and budgets and (unc["thinking_tokens_most"] or 0) <= max(budgets):
        out.append(f"uncapped never thought past {unc['thinking_tokens_most']} tokens, no more than the largest budget ({max(budgets)}): "
                   "it measured what a capped arm would, or the server caps thinking itself (--reasoning-budget)")
    return out


def decide(rows: list[dict], key: dict, reads: list[tuple[str, str]], prefer_share: float | None = None,
           slot_seconds: float | None = None) -> dict:
    """The rule fixed in advance, arm by arm against off: prefer_share or more of its non-tie reads, more than half in each slot order,
    no fewer parts accepted per proposal than off, p90 card seconds within slot_seconds, and every call held to its budget and
    thinking when asked. The verdict: of the arms that pass, the one cheapest on the card at p90; else off."""
    from engine import situations
    T = situations.S["thinking"]
    share = float(T["prefer_share"] if prefer_share is None else prefer_share)
    slot = float(T["slot_seconds"] if slot_seconds is None else slot_seconds)
    stats = arm_stats(rows)
    pairs = key.get("pairs") or {}
    tallies: dict[str, dict] = {}
    unknown = 0
    for pair, choice in reads:
        k = pairs.get(str(pair))
        if not k:
            unknown += 1
            continue
        arm, order = (k["B"], "B") if k["A"] == "off" else (k["A"], "A")
        t = tallies.setdefault(arm, {"A": [0, 0], "B": [0, 0], "ties": 0})       # per slot the arm sat in: [preferred, non-tie reads]
        if choice == "tie":
            t["ties"] += 1
            continue
        t[order][1] += 1
        t[order][0] += (choice.upper() == order)
    base = stats.get("off") or {}
    verdicts = {}
    for arm, st in stats.items():
        if arm == "off":
            continue
        t = tallies.get(arm, {"A": [0, 0], "B": [0, 0], "ties": 0})
        won, read = t["A"][0] + t["B"][0], t["A"][1] + t["B"][1]
        why = []
        if not read or Fraction(won, read) < Fraction(str(share)):
            why.append(f"readers preferred it in {won} of {read} reads that were not ties, below {share:.0%}")
        for order in ("A", "B"):
            w, n = t[order]
            if not n or w * 2 <= n:
                why.append(f"with it in slot {order}, readers preferred it in {w} of {n}: the preference does not hold in both orders")
        if (st.get("accepted_per_proposal") or 0) < (base.get("accepted_per_proposal") or 0):
            why.append(f"it kept {st['accepted_per_proposal']} parts a proposal, fewer than off's {base.get('accepted_per_proposal')}")
        p90 = st.get("p90_card_seconds")
        if p90 is None:
            why.append(f"its p90 on the card is past any limit ({st['failed']} of {st['n']} calls failed or gave no counts)")
        elif p90 > slot:
            why.append(f"its p90 on the card is {p90} s, past the slot's {slot:g} s")
        if st.get("over_budget"):
            why.append(f"{st['over_budget']} of its calls went past their thinking budget: the server did not hold it")
        if st.get("no_thinking"):
            why.append(f"{st['no_thinking']} of its calls came back without thinking: it was not measured as thinking")
        verdicts[arm] = {"passes": not why, "why": why, "preferred_share": round(won / read, 3) if read else None, "won": won,
                         "read": read, "ties": t["ties"], "by_order": {o: list(t[o]) for o in ("A", "B")}}
    passing = sorted((a for a, v in verdicts.items() if v["passes"]), key=lambda a: stats[a].get("p90_card_seconds") or 0)
    return {"verdict": passing[0] if passing else "off", "arms": verdicts, "stats": stats, "prefer_share": share, "slot_seconds": slot,
            "reads": len(reads), "unknown_reads": unknown, "same_pairs": key.get("same", 0)}


def measured_doc(rows: list[dict], decision: dict, meta: dict) -> dict:
    """What data/measured/situation_thinking.yaml holds (situations.measured_problems reads it at startup)."""
    arms = {}
    for arm, st in decision["stats"].items():
        v = decision["arms"].get(arm, {})
        arms[arm] = {"accepted_per_proposal": st["accepted_per_proposal"], "finished_share": st["finished_share"],
                     "p50_card_seconds": st["p50_card_seconds"], "p90_card_seconds": st["p90_card_seconds"],
                     "preferred_share": v.get("preferred_share"), "passes": v.get("passes", arm == "off")}
    return {"task": TASK, "cases": meta.get("cases"), "seed": meta.get("seed"), "measured": meta.get("when", ""), "arms": arms,
            "verdict": decision["verdict"]}


def write_summary(folder: Path, rows: list[dict], decision: dict | None, meta: dict) -> None:
    stats = arm_stats(rows)
    out = ["# Thinking in a situation's parts", "",
           f"{meta.get('cases')} case(s), seed {meta.get('seed')}, arms {', '.join(meta.get('arms') or stats)}. Card seconds are what a "
           "call would take on the minimum card (data/measured/card_profile.yaml); a failed call counts as past any limit. A closure of "
           "an only way is judged as at a birth with no way through offered yet. The answer's shape was sent to every arm as "
           f"{'response_format (the server binds it after any thinking; a ```json fence around an answer is taken off and counted)' if meta.get('constraint', 'schema') == 'schema' else 'the raw grammar the game sends, bound from the first token'}.", ""]
    if meta.get("stopped"):
        out += [f"**The run stopped early: {meta['stopped']}.**", ""]
    out += ["| arm | calls | valid | finished | parts kept a proposal | p50 s | p90 s | thinking tokens p50 / p90 |", "|---|---|---|---|---|---|---|---|"]
    for arm, st in stats.items():
        fin = ", ".join(f"{k} {v}" for k, v in sorted(st["finishes"].items()))
        out.append(f"| {arm} | {st['n']} | {st['valid']} | {fin} | {st['accepted_per_proposal']} | {st['p50_card_seconds']} | "
                   f"{st['p90_card_seconds'] if st['p90_card_seconds'] is not None else 'past any limit'} | "
                   f"{st['thinking_tokens_p50']} / {st['thinking_tokens_p90']} |")
    out += ["", "## Parts kept, by kind, and why parts were dropped", ""]
    for arm, st in stats.items():
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(st["accepted_by_kind"].items())) or "none"
        drops = "; ".join(f"{k} ({v})" for k, v in st["dropped"].items()) or "none"
        out.append(f"- **{arm}**: kept {kinds}. Dropped: {drops}." + (f" Fenced answers: {st['fenced']}." if st.get("fenced") else ""))
    warn = warnings_of(rows)
    if warn:
        out += ["", "## Warnings", ""] + [f"- {w}" for w in warn]
    if decision is not None:
        out += ["", "## The decision", "",
                f"The rule, fixed in advance: readers prefer the arm in {decision['prefer_share']:.0%} or more of the reads that are not "
                f"ties, more often than not in each slot order; no fewer parts kept a proposal than off; p90 on the card within "
                f"{decision['slot_seconds']:g} s; the server holding the arm's budget.", "",
                f"{decision['reads']} read(s); {decision['unknown_reads']} for a pair the key does not hold (passed over); "
                f"{decision['same_pairs']} pair(s) left out of the packs, their two cards the same.", ""]
        for arm, v in decision["arms"].items():
            out.append(f"- **{arm}**: " + ("passes." if v["passes"] else "does not pass: " + "; ".join(v["why"]) + ".")
                       + f" (reads: {v['won']} of {v['read']} preferred, {v['ties']} ties; in slot A {v['by_order']['A'][0]} of "
                       f"{v['by_order']['A'][1]}, in slot B {v['by_order']['B'][0]} of {v['by_order']['B'][1]})")
        out += ["", ("**Verdict: thinking goes into the proposal, as " + decision["verdict"] + ".**") if decision["verdict"] != "off"
                else "**Verdict: thinking stays off everywhere.**"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def load_rows(folder: Path) -> list[dict]:
    path = folder / "results.jsonl"
    if not path.exists():
        return []
    rows = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        if ln.strip():
            try:
                rows.append(json.loads(ln))
            except ValueError:                                                 # a row half-written when the run was killed
                pass
    return rows


def finish_decision(folder: Path, rows: list[dict], reads_paths, measured: str = "", meta: dict | None = None,
                    slot_seconds: float | None = None) -> dict:
    key_path = folder / "key.json"
    if not key_path.exists():
        raise SystemExit(f"no key.json in {folder}: make the packs first (--pack {folder})")
    key = json.loads(key_path.read_text(encoding="utf-8"))
    if key.get("results_sha256") != _sha(folder / "results.jsonl"):
        raise SystemExit("results.jsonl has changed since the packs were made (a resumed run?): make them again with --pack, and have "
                         "them read again")
    for name, sha in (key.get("packs") or {}).items():
        if _sha(folder / "pack" / name) != sha:
            raise SystemExit(f"pack/{name} is not the pack the key was made with")
    reads, unread = read_reads(reads_paths)
    if unread:
        raise SystemExit("lines in the reads that are neither a read nor a comment (begin a note with #):\n  " + "\n  ".join(unread[:10]))
    decision = decide(rows, key, reads, slot_seconds=slot_seconds)
    if meta is None and (folder / "meta.json").exists():
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    meta = meta or {"cases": len({r["case"] for r in rows}), "arms": sorted({r["arm"] for r in rows})}
    write_summary(folder, rows, decision, meta)
    (folder / "decision.json").write_text(json.dumps(decision, indent=2), encoding="utf-8")
    if measured:
        import yaml
        doc = measured_doc(rows, decision, {**meta, "when": time.strftime("%Y-%m-%d")})
        from engine import situations
        bad = situations.measured_problems(doc)
        if bad:
            raise SystemExit("the measured file would not pass the game's check: " + "; ".join(bad))
        Path(measured).parent.mkdir(parents=True, exist_ok=True)
        Path(measured).write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    return decision


def _stop(signum, frame):
    raise KeyboardInterrupt


def main(argv=None) -> int:
    from engine import situations
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", default="", help="the llama-server to ask (its base URL)")
    ap.add_argument("--stub", action="store_true", help="the whole run through the game's gateway with the stand-in, no server")
    ap.add_argument("--cases", type=int, default=30)
    ap.add_argument("--seed", type=int, default=543)
    ap.add_argument("--arms", default=",".join(situations.arms()), help="which arms, by name (situations.yaml thinking.arms)")
    ap.add_argument("--budget-field", default="thinking_budget_tokens", help="the request's field the server reads a thinking budget from")
    ap.add_argument("--constraint", default="schema", choices=CONSTRAINTS,
                    help="(f544) how the answer's shape is sent to every arm: schema (response_format; can think) or grammar (the game's own)")
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--ready-wait", type=float, default=600.0)
    ap.add_argument("--give-up", type=int, default=5, help="stop after this many failed calls in a row (0: never)")
    ap.add_argument("--out", default="situation_ab")
    ap.add_argument("--force", action="store_true", help="start again over the results already in --out")
    ap.add_argument("--resume", action="store_true", help="keep the results already in --out and measure only what they lack")
    ap.add_argument("--scratch", default=SCRATCH, help=f"the scratch campaign's save name (begins {SCRATCH!r}; made afresh, removed after)")
    ap.add_argument("--keep-scratch", action="store_true", help="leave the scratch save after the run")
    ap.add_argument("--pack", default="", help="make the packs and the key again from an earlier run's results")
    ap.add_argument("--decide", default="", help="decide from an earlier run's folder (with --reads)")
    ap.add_argument("--reads", nargs="+", default=[], help="the readers' files: a pair's number, then A, B or tie, a line each")
    ap.add_argument("--slot-seconds", type=float, default=None, help="the background slot's p90 limit (default: situations.yaml)")
    ap.add_argument("--measured", default="", help="write the decision here as well (data/measured/situation_thinking.yaml)")
    a = ap.parse_args(argv)
    if a.pack:
        folder = Path(a.pack)
        rows = load_rows(folder)
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8")) if (folder / "meta.json").exists() else {}
        packs, pairs = write_packs(folder, rows, int(meta.get("seed", a.seed)))
        print(f"{pairs} pair(s) in {packs} pack(s) under {folder / 'pack'}")
        return 0
    if a.decide:
        if not a.reads:
            ap.error("--decide needs --reads")
        folder = Path(a.decide)
        d = finish_decision(folder, load_rows(folder), a.reads, a.measured, slot_seconds=a.slot_seconds)
        print(f"verdict: {d['verdict']} (see {folder / 'summary.md'})")
        return 0
    if not a.server and not a.stub:
        ap.error("name a --server, or --stub")
    names = [x.strip() for x in a.arms.split(",") if x.strip()]
    unknown = [x for x in names if x not in situations.arms()]
    if unknown or "off" not in names:
        ap.error(f"arms must be among {sorted(situations.arms())} and include off (got {names})")
    out = Path(a.out)
    have = load_rows(out)
    if have and not (a.force or a.resume):
        raise SystemExit(f"{out / 'results.jsonl'} already holds {len(have)} row(s): --resume to go on with them, --force to start again")
    meta = {"cases": a.cases, "arms": names, "seed": a.seed, "server": a.server or "stub", "budget_field": a.budget_field,
            "constraint": a.constraint}
    if a.resume and have:
        was = json.loads((out / "meta.json").read_text(encoding="utf-8")) if (out / "meta.json").exists() else {}
        if (was.get("seed"), was.get("cases"), was.get("arms"), was.get("constraint", "schema")) != (a.seed, a.cases, names, a.constraint):
            raise SystemExit(f"--resume needs the run's own seed, cases, arms and constraint ({was.get('seed')}, {was.get('cases')}, "
                             f"{was.get('arms')}, {was.get('constraint', 'schema')})")
    else:
        have = []
    import simlib
    simlib.install(_residents_stub(a.seed))          # the town is peopled by the engine on the seed; the parts go to the server named
    session, store, world, catalog = build_world(a.seed, a.scratch)
    signal.signal(signal.SIGTERM, _stop)
    rows = list(have)
    started = False                                  # the results file opened by this run (or resumed): only then are packs made
    try:
        chosen = cases(world, a.cases, a.seed)
        meta["cases"] = len(chosen)
        people_towns(store, world, catalog, [c["town"] for c in chosen])
        print(f"{len(chosen)} case(s) x {len(names)} arm(s)" + (f" against {a.server}" if a.server else " through the stand-in"))
        if a.server and chosen:
            from tools import think_ab
            url = a.server.rstrip("/") + "/v1/chat/completions"
            first = prompt_of(store, world, chosen[0], int(store.meta.minutes or 0))
            warm = body_of(row_of(first), {"think": False, "budget": None}, a.budget_field, slot_tokens(), a.model, a.constraint)
            ok, why = think_ab.ready(lambda: think_ab.post(url, dict(warm, max_tokens=8), 120.0), a.ready_wait, print)
            if not ok:
                raise SystemExit(f"the server is not ready: {why}")
            meta.update(check_server(a.server, first, names, a.budget_field, a.model, slot_tokens(), timeout=a.timeout, constraint=a.constraint))
        out.mkdir(parents=True, exist_ok=True)
        (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        started = True
        with (out / "results.jsonl").open("a" if have else "w", encoding="utf-8") as sink:
            run(store, world, chosen, names, server=a.server, stub=a.stub, seed=a.seed, budget_field=a.budget_field, model=a.model,
                timeout=a.timeout, out=out, sink=sink, done={(r["case"], r["arm"]) for r in have}, rows=rows, give_up=a.give_up, meta=meta,
                constraint=a.constraint)
    except KeyboardInterrupt:
        meta["stopped"] = "interrupted"
        print("  interrupted: what was measured is kept")
    finally:
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        if a.keep_scratch:
            session.close()
        else:
            drop_world(session, a.scratch)
    if started:
        (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        rows = load_rows(out)
        packs, pairs = write_packs(out, rows, a.seed)
        write_summary(out, rows, None, meta)
        if a.reads and not meta.get("stopped"):
            d = finish_decision(out, rows, a.reads, a.measured, meta, slot_seconds=a.slot_seconds)
            print(f"verdict: {d['verdict']}")
        print(f"{len(rows)} call(s); {pairs} pair(s) to read in {packs} pack(s) under {out / 'pack'} (the key apart in key.json); "
              f"summary in {out / 'summary.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
