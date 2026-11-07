"""(f543) A situation's parts proposed with thinking off and on, measured before the owner decides whether the proposal thinks (f544).

The owner's direction: thinking belongs where the model makes a typed proposal the engine checks, never in what the player reads. This
tool measures it on the one call that may think, the situation's parts (engine/situations.py prompt, llm/contracts.py SituationParts):

  1. A scratch world, the same for the same --seed: a fresh campaign (saves/situation_ab), each case's town peopled by the engine with
     names it draws itself (no model), so PEOPLE has ids and every arm reads the same town.
  2. Cases: --cases N of (a pressure of the world, the rare or the campaign tier), chosen on the seed; each case's prompt is the one
     the game would send (situations.prompt), its request the one llama-server would be sent (tools/think_ab.py llama_body: the schema
     as its grammar, every sampler, the template's enable_thinking).
  3. Arms (data/rules/situations.yaml thinking.arms): off; capped per request at a budget of thinking tokens (the server's field,
     --budget-field, sent only on a capped arm; the response's fields are recorded so its name is confirmed on the pod's first call);
     uncapped within the background slot. The arms go in turn for each case, the order turning, so none always finds the prompt cached.
  4. Each answer scored by the game's own contract and check (situations.check against the scratch world): the parts accepted by kind,
     every reason a part was dropped, how the call finished (stop, length, thought_out: the room spent on thinking with no answer), the
     tokens, and what the call would take on the minimum card (data/measured/card_profile.yaml).
  5. A blind pack (pack.md, key.json apart): each case's accepted parts as the engine renders them (no model prose), each thinking arm
     paired with off in both slot orders, no arm named anywhere in a card. Readers write one line a pair: its number, then A, B or tie.
  6. The decision, by the rule fixed in advance (situations.yaml thinking): with --reads, an arm goes in only if readers prefer it in
     prefer_share of the reads that are not ties, the preference holding in both slot orders, with no fewer parts accepted per
     proposal than off, and its p90 on the card within slot_seconds. summary.md says which, or that thinking stays off.

    python tools/situation_ab.py --server http://127.0.0.1:8080 --cases 30 --out situation_ab/
    python tools/situation_ab.py --decide situation_ab/ --reads reads.txt --measured data/measured/situation_thinking.yaml
    python tools/situation_ab.py --stub --cases 4 --out scratch/situation_ab/     the whole run through the game's gateway, no server

It writes results.jsonl (one row a case and arm), summary.md (as the run goes), pack.md and key.json. It sends nothing anywhere but the
server named."""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import shutil
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TASK = "situation_parts"
TIERS = ("rare", "campaign")
SCRATCH = "situation_ab"
READ = re.compile(r"^\s*(?:pair\s*)?(\d+)\s*[:.)\-]?\s*(a|b|tie)\b", re.I)


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
    """A fresh scratch campaign on the seed: (session, store, world, catalog)."""
    from engine.session import CampaignSession
    from npc.traits import load_traits
    from storage.campaign import SAVES_DIR
    shutil.rmtree(SAVES_DIR / name, ignore_errors=True)
    session = CampaignSession.open(name)
    store = session.store
    store.meta.seed = seed
    store.save_meta()
    return session, store, session.world, load_traits()


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
    from engine import situations
    system, user = situations.prompt(store, world, store.load_world_state() or {}, world.places[case["place"]], case["tier"], t,
                                     case["trouble"])
    return {"system": system, "user": user, "hash": hashlib.sha256((system + "\n" + user).encode("utf-8")).hexdigest()[:16]}


def row_of(p: dict) -> dict:
    """The request as the game's gateway would make it (system then user; the task's sampling, its first try; the answer's ceiling)."""
    from engine import situations
    from llm import sampling
    spec = situations.S["proposal"]
    plan = sampling.resolve(TASK, float(spec["temperature"]))
    return {"request": {"messages": [{"role": "system", "content": p["system"]}, {"role": "user", "content": p["user"]}],
                        "sampling": plan.at(0).resolved(), "max_tokens": int(spec["max_tokens"])}}


def body_of(row: dict, arm: str, spec: dict, budget_field: str, slot: int, model: str | None = None) -> dict:
    """The llama-server body for one arm: think_ab's, with the room a thinking arm gets (its budget, or the slot for uncapped, never more
    than the context holds) and the budget field on a capped arm alone."""
    from llm.contracts import SituationParts
    from tools import think_ab
    think_ab.NUM_CTX = slot
    room = int(spec["budget"]) if spec.get("budget") else slot
    body = think_ab.llama_body(row, SituationParts, bool(spec["think"]), room, model)
    if spec["think"] and spec.get("budget"):
        body[budget_field] = int(spec["budget"])
    return body


# ---------- scoring

def finish_of(got: dict) -> str:
    """stop, length, or thought_out (cut off with thinking written and no answer begun), as llm/gateway.py names the last."""
    f = got.get("finish") or ""
    if f == "length":
        return "thought_out" if got.get("thinking") and not (got.get("content") or "").strip() else "length"
    return f or "unknown"


def score(content: str, store, world, case: dict, t: int, seed: int) -> dict:
    """The contract's reading, then the engine's check (the same die for every arm, so the same parts roll the same truth)."""
    from engine import situations
    from llm.contracts import SituationParts
    out = {"valid": False, "error": "", "accepted": {}, "accepted_n": 0, "dropped": [], "parts": []}
    text = (content or "").strip()
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
    return out


def card(store, world, case: dict, parts: list[dict]) -> str:
    """The accepted parts as the engine renders them, its lines alone (the header is the model's, not a reader's)."""
    from engine import situations
    text = situations.render(parts, store, world, f"ab:{case['pressure']}:{case['tier']}")
    lines = [ln for ln in text.splitlines() if ln.startswith("- ")]
    return "\n".join(lines) if lines else "(nothing the game could keep)"


def setting(store, world, case: dict) -> str:
    """What a reader judges the cards against: the tier, the place, the trouble, and the town's people by name and trade."""
    from engine import retrieval
    place = world.places[case["place"]]
    people = [f"{n.name} ({n.role.replace('_', ' ')})" for n in retrieval.people_in_town(store, world, case["town"])][:20]
    return (f"A {case['tier']} situation at {place.name}: {case['trouble'].strip()}\n"
            f"The town's people: {', '.join(people) or 'none met yet'}.")


# ---------- the run

def run(store, world, chosen: list[dict], arm_names: list[str], *, server: str = "", stub: bool = False, seed: int = 543,
        budget_field: str = "thinking_budget_tokens", model: str | None = None, timeout: float = 600.0, ready_wait: float = 600.0,
        out: Path | None = None, say=print) -> list[dict]:
    """Every case through every arm, the order turning case by case; a row a call, written to results.jsonl as it comes."""
    from engine import situations
    from tools import think_ab
    A = situations.arms()
    slot = int(situations.S["thinking"]["slot_tokens"])
    prof = think_ab.profile()
    t = int(store.meta.minutes or 0)
    url = server.rstrip("/") + "/v1/chat/completions" if server else ""
    rows: list[dict] = []
    sink = (out / "results.jsonl").open("w", encoding="utf-8") if out else None
    if url and chosen:
        first = body_of(row_of(prompt_of(store, world, chosen[0], t)), arm_names[0], A[arm_names[0]], budget_field, slot, model)
        ok, why = think_ab.ready(lambda: think_ab.post(url, dict(first, max_tokens=8), 120.0), ready_wait, say)
        if not ok:
            raise SystemExit(f"the server is not ready: {why}")
    for case in chosen:
        p = prompt_of(store, world, case, t)
        row = row_of(p)
        turn = case["i"] % len(arm_names)
        for arm in arm_names[turn:] + arm_names[:turn]:
            spec = A[arm]
            rec = {"case": case["i"], "arm": arm, "pressure": case["pressure"], "tier": case["tier"], "place": case["place"],
                   "prompt_hash": p["hash"], "think": spec["think"], "budget": spec.get("budget")}
            if stub:
                got = _stub_call(p, row)
            else:
                body = body_of(row, arm, spec, budget_field, slot, model)
                rec["budget_sent"] = body.get(budget_field)
                rec["max_tokens"] = body.get("max_tokens")
                status, resp, took = think_ab.post(url, body, timeout)
                rec["status"], rec["wall_seconds"] = status, round(took, 2)
                got = think_ab.read_llama(resp) if status == 200 and isinstance(resp, dict) else {"content": "", "error": str(resp)[:300]}
            rec["finish"] = finish_of(got) if got.get("finish") is not None or got.get("content") else "failed"
            for k in ("prompt_tokens", "answer_tokens", "fields", "message_fields", "timing_fields", "error"):
                if got.get(k) is not None:
                    rec[k] = got[k]
            thinking, content = got.get("thinking") or "", got.get("content") or ""
            rec["thinking_chars"], rec["content_chars"] = len(thinking), len(content)
            if rec.get("answer_tokens") and (thinking or content):            # the server counts both as one: shared out by their length
                rec["thinking_tokens"] = round(rec["answer_tokens"] * len(thinking) / (len(thinking) + len(content)))
            rec["card_seconds"] = think_ab.card_seconds(rec.get("prompt_tokens"), rec.get("answer_tokens"), prof)
            sc = score(content, store, world, case, t, seed)
            rec.update({k: v for k, v in sc.items() if k not in ("parts", "error")})
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
        if out:
            write_summary(out, rows, None, {"cases": len(chosen), "arms": arm_names, "seed": seed})
    if sink:
        sink.close()
    return rows


def _stub_call(p: dict, row: dict) -> dict:
    """--stub: the call through the game's own gateway (the stand-in answering), its tokens estimated from its characters."""
    from engine import situations
    from llm.contracts import SituationParts
    from llm.gateway import generate
    from llm.errors import LLMError
    spec = situations.S["proposal"]
    try:
        parts = generate("situation_parts", p["system"], p["user"], SituationParts, temperature=float(spec["temperature"]), max_tokens=int(spec["max_tokens"]))
    except LLMError as e:
        return {"content": "", "finish": "stop", "error": str(e)[:300]}
    content = parts.model_dump_json()
    return {"content": content, "thinking": "", "finish": "stop", "prompt_tokens": (len(p["system"]) + len(p["user"])) // 4,
            "answer_tokens": max(1, len(content) // 4)}


# ---------- the blind pack

def pack(rows: list[dict], seed: int) -> tuple[list[dict], dict]:
    """Each thinking arm against off, case by case, in both slot orders, shuffled on the seed. A pair whose two cards say the same
    thing word for word is left out (nothing to choose between) and counted. -> (items, key)."""
    by = {(r["case"], r["arm"]): r for r in rows}
    pairs, same = [], 0
    for (case, arm), r in sorted(by.items()):
        if arm == "off" or (case, "off") not in by:
            continue
        off = by[(case, "off")]
        if off["card"] == r["card"]:
            same += 1
            continue
        for a, b in ((off, r), (r, off)):
            pairs.append({"case": case, "setting": r["setting"], "A": a["card"], "B": b["card"], "arm_A": a["arm"], "arm_B": b["arm"]})
    random.Random(f"{seed}:pack").shuffle(pairs)
    items, key = [], {"same": same, "pairs": {}}
    for n, p in enumerate(pairs, 1):
        items.append({"pair": n, "setting": p["setting"], "A": p["A"], "B": p["B"]})
        key["pairs"][str(n)] = {"A": p["arm_A"], "B": p["arm_B"], "case": p["case"]}
    return items, key


def pack_text(items: list[dict]) -> str:
    out = ["# Situation cards, read blind", "",
           "Each pair is two ways the same situation could be made up: who is in it and how, what goods it turns on, how its people stand "
           "to each other, what it does to places and roads, and what evidence there is. Read both cards, then choose the one that makes "
           "the better situation, judging four things together: whether the parts fit the situation; whether they give a player ways "
           "in; whether they hang together; whether anything contradicts the world or the town's people. Write one line a pair in your "
           "reads file: the pair's number, then A, B or tie.", ""]
    for it in items:
        out += [f"## Pair {it['pair']}", "", it["setting"], "", "### A", "", it["A"], "", "### B", "", it["B"], ""]
    return "\n".join(out)


def read_reads(path: Path) -> list[tuple[str, str]]:
    """One read a line: a pair's number, then A, B or tie (several readers' lines may follow one another); '#' starts a comment."""
    reads = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = READ.match(line.split("#", 1)[0])
        if m:
            reads.append((m.group(1), m.group(2).lower()))
    return reads


# ---------- the decision

def _q(values, q):
    from tools import think_ab
    return think_ab._q(values, q)


def arm_stats(rows: list[dict]) -> dict:
    out = {}
    for arm in sorted({r["arm"] for r in rows}, key=lambda a: (a != "off", a)):
        rs = [r for r in rows if r["arm"] == arm]
        secs = [r["card_seconds"] for r in rs if r.get("card_seconds") is not None]
        reasons: dict[str, int] = {}
        kinds: dict[str, int] = {}
        for r in rs:
            for why in r.get("dropped") or ():
                reasons[why] = reasons.get(why, 0) + 1
            for k, n in (r.get("accepted") or {}).items():
                kinds[k] = kinds.get(k, 0) + n
        finishes: dict[str, int] = {}
        for r in rs:
            finishes[r.get("finish") or "?"] = finishes.get(r.get("finish") or "?", 0) + 1
        think = [r["thinking_tokens"] for r in rs if r.get("thinking_tokens") is not None]
        out[arm] = {"n": len(rs), "valid": sum(1 for r in rs if r.get("valid")), "finishes": finishes,
                    "finished_share": round(finishes.get("stop", 0) / len(rs), 3) if rs else None,
                    "accepted_per_proposal": round(sum(r.get("accepted_n", 0) for r in rs) / len(rs), 3) if rs else None,
                    "accepted_by_kind": kinds, "dropped": dict(sorted(reasons.items(), key=lambda kv: -kv[1])),
                    "p50_card_seconds": _q(secs, 0.5), "p90_card_seconds": _q(secs, 0.9),
                    "thinking_tokens_p50": _q(think, 0.5), "thinking_tokens_p90": _q(think, 0.9)}
    return out


def decide(rows: list[dict], key: dict, reads: list[tuple[str, str]], prefer_share: float | None = None,
           slot_seconds: float | None = None) -> dict:
    """The rule fixed in advance, arm by arm against off: prefer_share or more of its non-tie reads, more than half in each slot order,
    no fewer parts accepted per proposal than off, p90 card seconds within slot_seconds. The verdict: of the arms that pass, the one
    cheapest on the card at p90; else off."""
    from engine import situations
    T = situations.S["thinking"]
    share = float(T["prefer_share"] if prefer_share is None else prefer_share)
    slot = float(T["slot_seconds"] if slot_seconds is None else slot_seconds)
    stats = arm_stats(rows)
    pairs = key.get("pairs") or {}
    tallies: dict[str, dict] = {}
    for pair, choice in reads:
        k = pairs.get(str(pair))
        if not k:
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
        pref = round(won / read, 3) if read else None
        if pref is None or pref < share:
            why.append(f"readers preferred it in {won} of {read} reads that were not ties, below {share:.0%}")
        for order in ("A", "B"):
            w, n = t[order]
            if not n or w * 2 <= n:
                why.append(f"with it in slot {order}, readers preferred it in {w} of {n}: the preference does not hold in both orders")
        if (st.get("accepted_per_proposal") or 0) < (base.get("accepted_per_proposal") or 0):
            why.append(f"it kept {st['accepted_per_proposal']} parts a proposal, fewer than off's {base.get('accepted_per_proposal')}")
        p90 = st.get("p90_card_seconds")
        if p90 is None or p90 > slot:
            why.append(f"its p90 on the card is {p90} s, past the slot's {slot:g} s")
        verdicts[arm] = {"passes": not why, "why": why, "preferred_share": pref, "won": won, "read": read, "ties": t["ties"],
                         "by_order": {o: list(t[o]) for o in ("A", "B")}}
    passing = sorted((a for a, v in verdicts.items() if v["passes"]), key=lambda a: stats[a].get("p90_card_seconds") or 0)
    return {"verdict": passing[0] if passing else "off", "arms": verdicts, "stats": stats, "prefer_share": share, "slot_seconds": slot}


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
           "call would take on the minimum card (data/measured/card_profile.yaml); a closure of an only way is judged as at a birth with "
           "no way through offered yet.", "",
           "| arm | calls | valid | finished | parts kept a proposal | p50 s | p90 s | thinking tokens p50 / p90 |", "|---|---|---|---|---|---|---|---|"]
    for arm, st in stats.items():
        fin = ", ".join(f"{k} {v}" for k, v in sorted(st["finishes"].items()))
        out.append(f"| {arm} | {st['n']} | {st['valid']} | {fin} | {st['accepted_per_proposal']} | {st['p50_card_seconds']} | "
                   f"{st['p90_card_seconds']} | {st['thinking_tokens_p50']} / {st['thinking_tokens_p90']} |")
    out += ["", "## Parts kept, by kind, and why parts were dropped", ""]
    for arm, st in stats.items():
        kinds = ", ".join(f"{k} {v}" for k, v in sorted(st["accepted_by_kind"].items())) or "none"
        drops = "; ".join(f"{k} ({v})" for k, v in st["dropped"].items()) or "none"
        out.append(f"- **{arm}**: kept {kinds}. Dropped: {drops}.")
    if decision is not None:
        out += ["", "## The decision", "",
                f"The rule, fixed in advance: readers prefer the arm in {decision['prefer_share']:.0%} or more of the reads that are not "
                f"ties, more often than not in each slot order; no fewer parts kept a proposal than off; p90 on the card within "
                f"{decision['slot_seconds']:g} s.", ""]
        for arm, v in decision["arms"].items():
            out.append(f"- **{arm}**: " + ("passes." if v["passes"] else "does not pass: " + "; ".join(v["why"]) + ".")
                       + f" (reads: {v['won']} of {v['read']} preferred, {v['ties']} ties; in slot A {v['by_order']['A'][0]} of "
                       f"{v['by_order']['A'][1]}, in slot B {v['by_order']['B'][0]} of {v['by_order']['B'][1]})")
        out += ["", ("**Verdict: thinking goes into the proposal, as " + decision["verdict"] + ".**") if decision["verdict"] != "off"
                else "**Verdict: thinking stays off everywhere.**"]
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "summary.md").write_text("\n".join(out) + "\n", encoding="utf-8")


def load_rows(folder: Path) -> list[dict]:
    return [json.loads(ln) for ln in (folder / "results.jsonl").read_text(encoding="utf-8").splitlines() if ln.strip()]


def finish_decision(folder: Path, rows: list[dict], reads_path: Path, measured: str = "", meta: dict | None = None,
                    slot_seconds: float | None = None) -> dict:
    key = json.loads((folder / "key.json").read_text(encoding="utf-8"))
    decision = decide(rows, key, read_reads(reads_path), slot_seconds=slot_seconds)
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


def main(argv=None) -> int:
    from engine import situations
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--server", default="", help="the llama-server to ask (its base URL)")
    ap.add_argument("--stub", action="store_true", help="the whole run through the game's gateway with the stand-in, no server")
    ap.add_argument("--cases", type=int, default=30)
    ap.add_argument("--seed", type=int, default=543)
    ap.add_argument("--arms", default=",".join(situations.arms()), help="which arms, by name (situations.yaml thinking.arms)")
    ap.add_argument("--budget-field", default="thinking_budget_tokens", help="the request's field the server reads a thinking budget from")
    ap.add_argument("--model", default=None)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--ready-wait", type=float, default=600.0)
    ap.add_argument("--out", default="situation_ab")
    ap.add_argument("--scratch", default=SCRATCH, help="the scratch campaign's save name (made afresh each run)")
    ap.add_argument("--decide", default="", help="decide from an earlier run's folder (with --reads)")
    ap.add_argument("--reads", default="", help="the readers' file: a pair's number, then A, B or tie, a line each")
    ap.add_argument("--slot-seconds", type=float, default=None, help="the background slot's p90 limit (default: situations.yaml)")
    ap.add_argument("--measured", default="", help="write the decision here as well (data/measured/situation_thinking.yaml)")
    a = ap.parse_args(argv)
    if a.decide:
        if not a.reads:
            ap.error("--decide needs --reads")
        folder = Path(a.decide)
        d = finish_decision(folder, load_rows(folder), Path(a.reads), a.measured, slot_seconds=a.slot_seconds)
        print(f"verdict: {d['verdict']} (see {folder / 'summary.md'})")
        return 0
    if not a.server and not a.stub:
        ap.error("name a --server, or --stub")
    names = [x.strip() for x in a.arms.split(",") if x.strip()]
    unknown = [x for x in names if x not in situations.arms()]
    if unknown or "off" not in names:
        ap.error(f"arms must be among {sorted(situations.arms())} and include off (got {names})")
    import simlib
    simlib.install(_residents_stub(a.seed))          # the town is peopled by the engine on the seed; the parts go to the server named
    session, store, world, catalog = build_world(a.seed, a.scratch)
    chosen = cases(world, a.cases, a.seed)
    people_towns(store, world, catalog, [c["town"] for c in chosen])
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    meta = {"cases": len(chosen), "arms": names, "seed": a.seed, "server": a.server or "stub", "budget_field": a.budget_field}
    print(f"{len(chosen)} case(s) x {len(names)} arm(s)" + (f" against {a.server}" if a.server else " through the stand-in"))
    rows = run(store, world, chosen, names, server=a.server, stub=a.stub, seed=a.seed, budget_field=a.budget_field, model=a.model,
               timeout=a.timeout, ready_wait=a.ready_wait, out=out)
    if a.server:
        from tools import think_ab
        meta["server_facts"] = think_ab.facts(a.server)
    items, key = pack(rows, a.seed)
    (out / "pack.md").write_text(pack_text(items), encoding="utf-8")
    (out / "key.json").write_text(json.dumps(key, indent=2), encoding="utf-8")
    (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    write_summary(out, rows, None, meta)
    if a.reads:
        d = finish_decision(out, rows, Path(a.reads), a.measured, meta, slot_seconds=a.slot_seconds)
        print(f"verdict: {d['verdict']}")
    print(f"{len(rows)} call(s); {len(items)} pair(s) to read in {out / 'pack.md'} (key apart in key.json); summary in {out / 'summary.md'}")
    session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
