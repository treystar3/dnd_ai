"""(f533) Thinking on and off, task by task, measured before the owner decides which of the game's calls should think.

The owner asked to try thinking for the judgment calls (reading the player's line, rulings, the audit's two checks, the canon check,
reading a move in a fight) and to keep it off for prose. This tool measures what it costs and what it changes, on a llama-server (the
engine the game ships with; (f532) nothing else is measured against):

  1. Recorded requests. The first try of each chosen task's calls in recordings (a night's run folders, a recording folder, or the
     night's zip as fetched) is sent again, once with thinking off and once on, to each server given (/v1/chat/completions, the
     template's enable_thinking, the schema as its grammar). Each answer is scored by the game's own contract (it parses, it
     validates), against the decision the night recorded (the plan's kinds, the ruling's sense, the audit's match, the move, the canon
     verdict), for leaked thinking (an answer that is not the JSON alone), for being cut off, and timed: wall seconds, the server's own
     counts, and what the call would take on the minimum card (data/measured/card_profile.yaml). Thinking off and on go in turn for
     each request, the order alternating, so neither always finds the prompt already cached.
  2. The game's own evaluations (--evals, on the llama-server named: the children run with DND_BACKEND=llama at that URL, and an
     embedder when --embed-url names one): tools/interp_eval.py on the night corpus and tools/ruling_eval.py, both --live, once with
     thinking off and once with it on for the chosen tasks (DND_THINK_TASKS): how many of their cases each gets right. The ruling's
     evaluations score the act's one ruling (act_ruling, f608): a case is right when its sense is and its changes are.

    python tools/think_ab.py --recordings post_e_full.zip --server llama=http://127.0.0.1:8080
    python tools/think_ab.py --recordings nightrun/ --server llama=http://127.0.0.1:8080 --per-task 60 --evals --out think_ab/
    (f534) python tools/think_ab.py --recordings post_e.zip --server llama=URL --tasks act_ruling,road_event,pulse_cataclysm,pulse_thread \
               --room 8192 --num-ctx 32768 --evals ruling_complex,events --out think_ab_room8192/
      a writing task (road_event) is replayed and timed with its text kept to be read; the evaluations are chosen by name (interp,
      ruling, ruling_complex: the improvised actions of several steps, ruling_act: acts on things and a situation's parts,
      ruling_road: the old ruling the road still asks, events: the model writing campaigns and cataclysms)

It writes results.jsonl (one row a call, with the first response's raw fields from the server, to learn their names), summary.json and
summary.md (a table per server, task and setting). It sends nothing anywhere but the servers named."""
from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import random
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TASKS = ("interpret_action", "act_ruling", "ruling", "audit_meaning", "audit_compare", "canon_check", "combat_interpret")
WRITING = ("road_event",)                      # (f534) writing tasks: replayed and timed, their text kept to be read; nothing to agree with
EVENT_TASKS = ("pulse_cataclysm", "pulse_thread", "event_judge", "thread_telling")   # what the events evaluation asks the model for
KNOWN = TASKS + WRITING + EVENT_TASKS
DECISION = {                                   # what each answer decides, compared with what the night decided (None: free text only)
    "ActionPlan": lambda d: [a.get("kind") for a in d.get("actions", [])],
    "Ruling": lambda d: d.get("sense"),
    "ActRuling": lambda d: d.get("sense"),
    "AuditVerdict": lambda d: d.get("matches"),
    "CombatIntent": lambda d: [d.get(k) or "" for k in ("kind", "target", "ability", "item", "move", "approach", "step")]
                              + [(d.get("buff_for") or "").replace("self", "")],          # '' and 'self' are both the player
    "CanonCheck": lambda d: d.get("verdict"),
    "AuditMeaning": None,
    "RoadEvent": None,
}
SAMPLER_KEYS = ("temperature", "top_k", "top_p", "min_p", "typical_p", "repeat_penalty", "repeat_last_n", "presence_penalty",
                "frequency_penalty")


# ---------- what was recorded

WARNINGS: list[str] = []          # what the reading had to step over (a cut-off file, a bad line), for the summary


def _lines(name: str, f):
    """The rows of one calls.jsonl.gz, as far as it can be read: a run killed or zipped mid-night leaves a file with no end, and a row
    half-written; the rows before stand, and the gap is said."""
    n = 0
    try:
        for line in f:
            if line.strip():
                try:
                    row = json.loads(line)
                except ValueError:
                    WARNINGS.append(f"{name}: a row that is not JSON after {n} rows, stepped over")
                    continue
                n += 1
                yield dict(row, _from=name)
    except (EOFError, OSError, zlib.error) as e:        # gzip.BadGzipFile is an OSError
        WARNINGS.append(f"{name}: read {n} rows, then {type(e).__name__}: {str(e)[:80]} (a run cut off: the rest is lost)")


def recorded_rows(path: Path):
    """Every call row of the recordings at path: a .zip (each */calls.jsonl.gz inside), one recording folder, or a folder of them."""
    path = Path(path)
    if path.suffix.lower() == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in sorted(n for n in z.namelist() if n.endswith("calls.jsonl.gz")):
                with gzip.open(io.BytesIO(z.read(name)), "rt", encoding="utf-8") as f:
                    yield from _lines(name, f)
        return
    files = [path / "calls.jsonl.gz"] if (path / "calls.jsonl.gz").exists() else sorted(path.rglob("calls.jsonl.gz"))
    for p in files:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            yield from _lines(str(p), f)


SKIPPED: dict[str, int] = {}
READY_POLL = 5.0                   # seconds between tries of a server that is still loading


def pick(rows, tasks, per_task: int, seed: int = 533) -> dict[str, list[dict]]:
    """Each task's first tries that were answered (the request as first made, the night's own decision beside it), a fixed sample of
    at most per_task, in the order they were made. Each task draws from its own seed, so its sample is the same whatever other tasks
    are chosen with it. Left out: a retry (it carries the draft: more than two messages; or, after a server error, the same two
    messages again at a warmer temperature) and a call the night made thinking (its room is already in its numbers)."""
    by: dict[str, list[dict]] = {t: [] for t in tasks}
    last: dict[tuple, list] = {}
    for r in rows:
        t = r.get("task")
        req = r.get("request") or {}
        msgs = req.get("messages") or []
        if t not in by or r.get("kind") != "chat":
            continue
        key = (r.get("_from"), t)
        again = last.get(key) == msgs              # the same request again, straight after it failed: the retry of a server error
        last[key] = msgs if r.get("error") else None
        if len(msgs) != 2 or r.get("error") or not r.get("answer"):
            continue
        if again:
            SKIPPED["a retry after a server error"] = SKIPPED.get("a retry after a server error", 0) + 1
            continue
        if req.get("think"):
            SKIPPED["made thinking"] = SKIPPED.get("made thinking", 0) + 1
            continue
        by[t].append(r)
    out = {}
    for t, rs in by.items():
        rng = random.Random(f"{seed}:{t}")
        keep = sorted(rng.sample(range(len(rs)), per_task)) if len(rs) > per_task else range(len(rs))
        out[t] = [rs[i] for i in keep]
    return out


def schema_of(title: str):
    from llm import contracts
    return getattr(contracts, title)


# ---------- the two servers

NUM_CTX: int | None = None          # (f534) --num-ctx: the context every replayed call is given, in place of the night's


def room_for(row: dict, opts: dict, room: int) -> int:
    """(f534) The room a thinking call gets: --room, but no more than its context holds beside its prompt (the server's own count of
    it, as the night recorded it, else three characters a token) and its answer's ceiling, as the game's llm/backend.py think_room."""
    toks = (row.get("tokens") or {}).get("prompt_eval_count") or (row.get("usage") or {}).get("prompt")    # (f527) either row form
    if not toks:
        toks = sum(len(str(m.get("content") or "")) for m in ((row.get("request") or {}).get("messages") or [])) // 3
    fits = int(opts.get("num_ctx") or 16384) - int(toks) - int(opts.get("num_predict") or 0) - 256
    return max(0, min(int(room), fits))


def _options(row: dict, think: bool, room: int) -> dict:
    """The recorded options (every sampler and the answer's ceiling; a row from before f527 had them in the old client's shape, its thread
    count dropped: threads are the server's own setting since f532), the context asked for (--num-ctx) and, thinking, the room that fits."""
    import config
    req = row.get("request") or {}
    if "options" in req:                                             # a row from before f527: the request in the old client's shape
        opts = {k: v for k, v in (req.get("options") or {}).items() if k != "num_thread"}
    else:                                                            # (f527) the neutral row: every sampler, and the answer's ceiling
        opts = dict(req.get("sampling") or {})
        if req.get("max_tokens") is not None:
            opts["num_predict"] = int(req["max_tokens"])
        opts.setdefault("num_ctx", int(getattr(config, "NUM_CTX", 16384) or 16384))
    if NUM_CTX:
        opts["num_ctx"] = int(NUM_CTX)
    if think:
        opts["num_predict"] = int(opts.get("num_predict") or 0) + room_for(row, opts, room)
    return opts


def llama_body(row: dict, schema, think: bool, room: int, model: str | None = None) -> dict:
    """The same request as llama-server takes it: the schema as its grammar (f527: `grammar`, llama.cpp's own conversion in llm/gbnf.py,
    never response_format, as the game sends it), every sampler sent (the game's measured table under the call's own values,
    llm/sampling.py BASE, so none of the server's own defaults apply), thinking by the template's switch."""
    from llm import llama as _llama
    from llm.sampling import BASE
    import config
    req = row.get("request") or {}
    opts = _options(row, think, room)
    samplers = {**BASE, **{k: v for k, v in opts.items() if k in SAMPLER_KEYS}}
    body = {"model": model or config.MODEL, "messages": req.get("messages"),
            "grammar": _llama.grammar_of(schema.model_json_schema()),
            "max_tokens": int(opts.get("num_predict") or 512), "chat_template_kwargs": {"enable_thinking": bool(think)}, "stream": False}
    body.update({k: v for k, v in samplers.items() if k in SAMPLER_KEYS})
    return body


def post(url: str, body: dict, timeout: float) -> tuple[int, dict | str, float]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            text = r.read().decode("utf-8", errors="replace")
            status = r.status
    except urllib.error.HTTPError as e:
        text, status = e.read().decode("utf-8", errors="replace"), e.code
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}", time.perf_counter() - t0
    took = time.perf_counter() - t0
    try:
        return status, json.loads(text), took
    except ValueError:
        return status, text, took


def read_llama(resp: dict) -> dict:
    ch = (resp.get("choices") or [{}])[0]
    m = ch.get("message") or {}
    usage, timings = resp.get("usage") or {}, resp.get("timings") or {}
    ms = (timings.get("prompt_ms") or 0) + (timings.get("predicted_ms") or 0)
    return {"content": m.get("content") or "", "thinking": m.get("reasoning_content") or "", "finish": ch.get("finish_reason"),
            "prompt_tokens": usage.get("prompt_tokens", timings.get("prompt_n")), "answer_tokens": usage.get("completion_tokens", timings.get("predicted_n")),
            "server_seconds": round(ms / 1000, 3) if ms else None, "fields": sorted(resp), "message_fields": sorted(m),
            "timing_fields": sorted(timings)}


SERVERS = {"llama": ("/v1/chat/completions", llama_body, read_llama)}


# ---------- scoring

def score(title: str, content: str, recorded: str, request: dict | None = None) -> dict:
    schema = schema_of(title)
    text = (content or "").strip()
    out = {"parsed": False, "valid": False, "leaked": bool(text) and not text.startswith("{") or "<think" in text.lower(),
           "agree": None, "error": ""}
    try:
        got = json.loads(text)
        out["parsed"] = isinstance(got, dict)
    except ValueError as e:
        out["error"] = f"not JSON: {str(e)[:80]}"
        return out
    try:
        schema.model_validate_json(text, context=context_of(title, request))
        out["valid"] = True
    except Exception as e:
        out["error"] = f"refused by the contract: {str(e).splitlines()[0][:160]}"
    decide = DECISION.get(title)
    if decide is not None and out["valid"]:          # only an answer the game would take decides anything
        try:
            out["agree"] = decide(got) == decide(json.loads(recorded))
        except Exception:
            out["agree"] = None
    return out


def context_of(title: str, request: dict | None = None):
    """What the game validates the answer against, where it gives the contract more than the answer (engine/ruling.py ask, engine/act.py
    context): the capabilities, checks and changes the ruling may name, and for the act's ruling the codes its request listed. Roles only
    clear a field, never refuse, so none are given."""
    from engine import checks, features, ruling
    if title == "Ruling":
        return {"capabilities": list(ruling.C), "checks": sorted(checks.CHECKS) + list(ruling.ATTRS), "roles": [],
                "becomes": list(features.F["becomes"])}
    if title == "ActRuling":
        from engine import act, targets
        return {"capabilities": list(ruling.C), "checks": sorted(checks.CHECKS) + list(ruling.ATTRS), "roles": [],
                "changes": list(targets.CH["changes"]), "codes": codes_of(request), "most": int(act.A["most_changes"]),
                "fails": list(act.A["fails"])}
    return None


def codes_of(request: dict | None) -> list[str]:
    """(f603) The target codes an act ruling's request listed under TARGETS, one a line, the code first."""
    text = "\n".join(str(m.get("content") or "") for m in ((request or {}).get("messages") or []))
    lines = text.split("\n")
    start = next((i for i, line in enumerate(lines) if line.startswith("TARGETS")), len(lines))
    codes = []
    for line in lines[start + 1:]:
        if not line.startswith("  ") or line.strip() == "(none)":
            break
        codes.append(line.split()[0])
    return codes


def card_seconds(prompt_tokens, answer_tokens, profile: dict) -> float | None:
    """What the call would take on the minimum card, from its measured speeds (the thinking is written at the answer's speed)."""
    if prompt_tokens is None or answer_tokens is None:
        return None
    try:
        return round(float(prompt_tokens) / float(profile["prompt_tokens_per_second"])
                     + float(answer_tokens) / float(profile["answer_tokens_per_second"]), 2)
    except Exception:
        return None


def profile() -> dict:
    import yaml
    p = ROOT / "data" / "measured" / "card_profile.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


# ---------- the run

def get(url: str, timeout: float = 20.0) -> tuple[int, dict | str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            text, status = r.read().decode("utf-8", errors="replace"), r.status
    except urllib.error.HTTPError as e:
        text, status = e.read().decode("utf-8", errors="replace"), e.code
    except Exception as e:
        return 0, f"{type(e).__name__}: {e}"
    try:
        return status, json.loads(text)
    except ValueError:
        return status, text


def facts(base: str) -> dict:
    """What the server says of itself: llama-server's build, context and slots (/props). Read after the warm-up, so the model is loaded."""
    base = base.rstrip("/")
    st, p = get(base + "/props")
    if not isinstance(p, dict):
        return {"status": st}
    dg = p.get("default_generation_settings") or {}
    return {"status": st, "build_info": p.get("build_info"), "model_path": p.get("model_path"), "total_slots": p.get("total_slots"),
            "n_ctx": dg.get("n_ctx"), "chat_template_caps": p.get("chat_template_caps")}


def ready(post_warm, ready_wait: float, say) -> tuple[bool, str]:
    """The warm-up as the gate: sent again every READY_POLL seconds while the server cannot be reached or answers 503 (llama-server says 'Loading
    model' until it has), up to ready_wait seconds; ready only on a 200."""
    t0 = time.perf_counter()
    while True:
        status, resp, _ = post_warm()
        if status == 200:
            return True, ""
        if status not in (0, 503) or time.perf_counter() - t0 > ready_wait:
            return False, f"HTTP {status}: {str(resp)[:300]}"
        say(f"  not ready yet ({status}); trying again in {READY_POLL:g} s")
        time.sleep(READY_POLL)


def measure(chosen: dict[str, list[dict]], servers: list[tuple[str, str]], thinks=(False, True), room: int = 1024,
            timeout: float = 300.0, model: str | None = None, out=None, say=print, ready_wait: float = 600.0,
            give_up: int = 5, about: dict | None = None) -> list[dict]:
    """Every chosen request to each server, thinking off and on in turn. A server that is not ready after ready_wait seconds is
    skipped, and one that fails give_up calls in a row is left there: neither burns its rows as wrong answers. `about` gathers each
    server's facts and what became of it."""
    card = profile()
    results = []
    about = {} if about is None else about
    for name, base in servers:
        kind = name.split("=")[0] if "=" in name else name
        path, body_of, read = SERVERS[kind]
        say(f"{name}: warming the model ({base})")
        warm_row = next((r for rs in chosen.values() for r in rs), None)
        if warm_row is None:
            break
        ok, why = ready(lambda: post(base.rstrip("/") + path, body_of(warm_row, schema_of(warm_row["title"]), False, 0, model), timeout),
                        ready_wait, say)
        about[name] = {"url": base, **facts(base)}
        if not ok:
            about[name]["skipped"] = f"not ready: {why}"
            say(f"{name}: SKIPPED, not ready: {why}")
            continue
        failed_in_row, stopped = 0, ""
        for task, rows in chosen.items():
            if stopped:
                break
            for n, row in enumerate(rows):
                if stopped:
                    break
                order = list(thinks) if n % 2 == 0 else list(reversed(thinks))
                for think in order:
                    schema = schema_of(row["title"])
                    status, resp, took = post(base.rstrip("/") + path, body_of(row, schema, think, room, model), timeout)
                    got = read(resp) if status == 200 and isinstance(resp, dict) else {"content": "", "thinking": "", "finish": None,
                                                                                          "prompt_tokens": None, "answer_tokens": None,
                                                                                          "server_seconds": None}
                    sc = score(row["title"], got["content"], row.get("answer", ""), row.get("request")) if status == 200 else \
                        {"parsed": False, "valid": False, "leaked": False, "agree": None, "error": f"HTTP {status}: {str(resp)[:200]}"}
                    res = {"server": name, "url": base, "task": task, "title": row["title"], "think": think, "row": row.get("i"),
                           "from": row.get("_from", ""), "status": status, "seconds": round(took, 3), **sc,
                           "finish": got.get("finish"), "cut": got.get("finish") == "length", "prompt_tokens": got.get("prompt_tokens"),
                           "answer_tokens": got.get("answer_tokens"), "server_seconds": got.get("server_seconds"),
                           "thinking_chars": len(got.get("thinking") or ""), "answer_chars": len(got.get("content") or ""),
                           "room": room_for(row, _options(row, False, 0), room) if think else 0,          # (f534) what this call had
                           "answer": (got.get("content") or "")[:6000],                                    # (f534) to be read
                           "thinking_head": (got.get("thinking") or "")[:800], "thinking_tail": (got.get("thinking") or "")[-800:],
                           "card_seconds": card_seconds(got.get("prompt_tokens"), got.get("answer_tokens"), card),
                           "recorded_seconds": row.get("seconds")}
                    if n == 0:
                        res["raw_fields"] = {k: got.get(k) for k in ("fields", "message_fields", "timing_fields") if k in got}
                    results.append(res)
                    if out is not None:
                        out.write(json.dumps(res, ensure_ascii=False) + "\n")
                        out.flush()
                    failed_in_row = 0 if status == 200 else failed_in_row + 1
                    if failed_in_row >= give_up:
                        stopped = f"{give_up} calls in a row failed, the last {res['error'][:200]}"
                        break
            say(f"  {task}: {len(rows)} requests, thinking {'/'.join('on' if t else 'off' for t in thinks)}")
        if stopped:
            about[name]["stopped"] = stopped
            say(f"{name}: STOPPED: {stopped}")
    return results


def _q(values, q):
    v = sorted(x for x in values if isinstance(x, (int, float)))
    if not v:
        return None
    return round(v[min(len(v) - 1, int(round(q * (len(v) - 1))))], 2)


def summarise(results: list[dict]) -> list[dict]:
    """A row per server, task and setting. Every rate is over all n calls (a call with no usable answer is not valid and does not
    agree), with agreement among the valid answers beside it; the times are over the answered calls, and how many were not is shown."""
    rows = []
    keys = sorted({(r["server"], r["task"], r["think"]) for r in results}, key=lambda k: (k[0], TASKS.index(k[1]) if k[1] in TASKS else 99, k[2]))
    for server, task, think in keys:
        rs = [r for r in results if (r["server"], r["task"], r["think"]) == (server, task, think)]
        answered = [r for r in rs if r["status"] == 200]
        decided = [r for r in rs if r["agree"] is not None]
        pct = lambda xs, n: round(100.0 * len(xs) / n, 1) if n else None
        has_decision = DECISION.get(rs[0]["title"]) is not None
        rows.append({"server": server, "task": task, "think": "on" if think else "off", "n": len(rs), "answered": len(answered),
                     "failed": len(rs) - len(answered),
                     "valid_pct": pct([r for r in rs if r["valid"]], len(rs)), "parsed_pct": pct([r for r in rs if r["parsed"]], len(rs)),
                     "agree_pct": pct([r for r in rs if r["agree"]], len(rs)) if has_decision else None,
                     "agree_valid_pct": pct([r for r in decided if r["agree"]], len(decided)) if has_decision else None,
                     "leaked": sum(1 for r in rs if r["leaked"]), "cut": sum(1 for r in rs if r["cut"]),
                     "thought": sum(1 for r in answered if r["thinking_chars"] > 0),
                     "seconds_median": _q([r["seconds"] for r in answered], 0.5), "seconds_p90": _q([r["seconds"] for r in answered], 0.9),
                     "answer_tokens_mean": round(statistics.mean([r["answer_tokens"] for r in answered if r["answer_tokens"]]), 1)
                     if any(r["answer_tokens"] for r in answered) else None,
                     "thinking_chars_mean": round(statistics.mean([r["thinking_chars"] for r in answered]), 1) if answered else None,
                     "card_seconds_median": _q([r["card_seconds"] for r in answered], 0.5),
                     "card_seconds_p90": _q([r["card_seconds"] for r in answered], 0.9)})
    return rows


OLD_RULING = re.compile(r"(\d+) of (\d+) right(?:; (\d+) with no ruling)?")
# (f608) the act's tally line: right by sense, of the cases ruled, the sense right with the changes wrong, the cases with no ruling
ACT_RULING = re.compile(r"new: (\d+) of (\d+) right;[^\n]*?changes wrong (\d+)(?:[^\n]*?; (\d+) with no ruling)?")
EVAL_PATTERNS = {"interp_eval": re.compile(r"(\d+)/(\d+) right"),
                 "ruling_eval": ACT_RULING, "ruling_eval_complex": ACT_RULING, "ruling_eval_act": ACT_RULING, "ruling_eval_road": OLD_RULING,
                 "event_eval": re.compile(r"(\d+)/(\d+) right in")}
INTERP_NO_READING = re.compile(r"the model gave no usable reading (\d+) time")
COMPLEX = "data/replay/ruling_cases_complex.yaml"
# (f534) The game's own evaluations, by the name --evals takes: (its name in the summary, its command after the interpreter, the tasks
# whose thinking it measures). Each runs live on the llama-server named, with the rest of the game stubbed.
ACT_CASES = "data/replay/ruling_cases_act.yaml"
EVALS = {"interp": ("interp_eval", ["tools/interp_eval.py", "--corpus", "{corpus}", "--live"], {"interpret_action"}),
         "ruling": ("ruling_eval", ["tools/ruling_eval.py", "--live", "--path", "new"], {"act_ruling"}),          # (f608) as the game rules
         "ruling_complex": ("ruling_eval_complex", ["tools/ruling_eval.py", "--live", "--path", "new", "--cases", COMPLEX], {"act_ruling"}),
         "ruling_act": ("ruling_eval_act", ["tools/ruling_eval.py", "--live", "--path", "new", "--cases", ACT_CASES], {"act_ruling"}),
         "ruling_road": ("ruling_eval_road", ["tools/ruling_eval.py", "--live", "--path", "old"], {"ruling"}),
         "events": ("event_eval", ["tools/event_eval.py", "--live"], set(EVENT_TASKS))}


def eval_score(name: str, text: str) -> dict:
    """The evaluation's last score line. interp_eval counts every case (a case the model failed is wrong); ruling_eval leaves the
    cases with no ruling out of its 'of', so here they are put back: right out of every case, a missing ruling counted as wrong. The
    act's ruling is right when its sense is and its changes are (f608)."""
    m = EVAL_PATTERNS[name].findall(text)
    if not m:
        return {"right": None, "of": None, "no_answer": None}
    last = m[-1]
    right, of = int(last[0]), int(last[1])
    if EVAL_PATTERNS[name] is ACT_RULING:
        none = int(last[3]) if last[3] else 0
        return {"right": right - int(last[2]), "of": of + none, "no_answer": none}
    if name.startswith("ruling_eval"):
        none = int(last[2]) if last[2] else 0
        return {"right": right, "of": of + none, "no_answer": none}
    if name == "interp_eval":                   # (f534) its cases with no usable reading are in its 'of' already; counted here too
        n = INTERP_NO_READING.findall(text)
        return {"right": right, "of": of, "no_answer": int(n[-1]) if n else 0}
    return {"right": right, "of": of, "no_answer": None}


def evals(llama_url: str, tasks, thinks=(False, True), timeout: float = 7200.0, room: int | None = None,
          corpus: str = "data/replay/interp_cases.yaml", folder: Path | None = None, done=None, which=("interp", "ruling"),
          num_ctx: int | None = None, embed_url: str | None = None) -> list[dict]:
    """The game's own evaluations (`which`, names in EVALS), --live on the llama-server at llama_url (f529: DND_BACKEND=llama, the server
    started by hand), thinking off and then on for the chosen tasks (with the same room to think in as the recorded calls had, and the
    context asked for): how many cases each gets right. Each child's whole output is kept in folder; `done` is told after each child,
    so the summary is rewritten as they finish."""
    runs = [(EVALS[w][0], [sys.executable] + [c.replace("{corpus}", corpus) for c in EVALS[w][1]]) for w in which]
    out = []
    for think in thinks:
        env = {k: v for k, v in os.environ.items() if k != "MERAVIA_NO_SERVER"}
        env.update(DND_BACKEND="llama", DND_LLAMA_URL=llama_url.rstrip("/"), DND_THINK_TASKS=",".join(tasks) if think else "")
        if embed_url:                                       # (f529's review) the game's embedder beside the chat server, when one is named
            env["DND_LLAMA_EMBED_URL"] = embed_url.rstrip("/")
        if room is not None:
            env["DND_THINK_ROOM"] = str(room)
        if num_ctx:
            env["DND_NUM_CTX"] = str(num_ctx)
        for name, cmd in runs:
            t0 = time.perf_counter()
            try:
                r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
                text, rc = (r.stdout or "") + (r.stderr or ""), r.returncode
            except subprocess.TimeoutExpired as e:
                text = (e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes) else (e.stdout or "")) + \
                       (e.stderr.decode("utf-8", "replace") if isinstance(e.stderr, bytes) else (e.stderr or ""))
                rc = "timeout"
            row = {"eval": name, "think": "on" if think else "off", **eval_score(name, text), "rc": rc,
                   "seconds": round(time.perf_counter() - t0, 1), "room": room if think else None,
                   "tail": text.strip().splitlines()[-3:]}
            if folder is not None:
                (folder / f"eval_{name}_{row['think']}.log").write_text(text, encoding="utf-8", newline="\n")
            out.append(row)
            if done is not None:
                done(out)
    return out


def write_summary(folder: Path, rows: list[dict], eval_rows: list[dict], meta: dict) -> None:
    (folder / "summary.json").write_text(json.dumps({"meta": meta, "calls": rows, "evals": eval_rows}, indent=1), encoding="utf-8", newline="\n")
    lines = [f"# Thinking on and off ({meta['made']})", "", f"Recordings: {meta['recordings']}. Tasks: {', '.join(meta['tasks'])}. "
             f"Up to {meta['per_task']} first tries a task; {meta['room']} more tokens to think in. Minimum card from "
             f"data/measured/card_profile.yaml ({meta.get('card') or 'none'}).", "",
             "Rates are over every call (one with no usable answer is not valid and does not agree); 'agrees among valid' is over the "
             "valid answers only. Times are over the answered calls; 'failed' counts the rest.", ""]
    for name, f in (meta.get("servers_about") or {}).items():
        lines.append(f"- {name}: " + ", ".join(f"{k} {v}" for k, v in f.items() if k not in ("url", "chat_template_caps")))
    for w in meta.get("warnings") or []:
        lines.append(f"- WARNING: {w}")
    lines += ["", "| server | task | thinking | n | answered | failed | valid % | agrees with the night % | agrees among valid % | leaked | "
              "cut off | thought | s median | s p90 | answer tokens | thinking chars | card s median | card s p90 |",
              "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['server']} | {r['task']} | {r['think']} | {r['n']} | {r['answered']} | {r['failed']} | {r['valid_pct']} | "
                     f"{r['agree_pct']} | {r['agree_valid_pct']} | {r['leaked']} | {r['cut']} | {r['thought']} | {r['seconds_median']} | "
                     f"{r['seconds_p90']} | {r['answer_tokens_mean']} | {r['thinking_chars_mean']} | {r['card_seconds_median']} | "
                     f"{r['card_seconds_p90']} |")
    if eval_rows:
        lines += ["", f"Evaluations: interp_eval on {meta.get('corpus')}, ruling_eval on data/replay/ruling_cases.yaml, ruling_eval_complex "
                  f"on {COMPLEX} and ruling_eval_act on {ACT_CASES} (these three the act's ruling, right in its sense and its changes), "
                  "ruling_eval_road on "
                  "data/replay/ruling_cases.yaml (the old ruling, the road's), event_eval on data/replay/event_cases.yaml; right out of every "
                  "case (no answer counts as wrong).", "",
                  "| evaluation | thinking | right | of | no answer | rc | seconds |", "| --- | --- | --- | --- | --- | --- | --- |"]
        lines += [f"| {e['eval']} | {e['think']} | {e['right']} | {e['of']} | {e.get('no_answer')} | {e['rc']} | {e['seconds']} |"
                  for e in eval_rows]
        for e in eval_rows:
            if e["right"] is None:
                lines.append(f"- {e['eval']} {e['think']}: no score line; it ended with: " + " / ".join(e.get("tail") or []))
    (folder / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def warnings_of(rows: list[dict]) -> list[str]:
    """What the table cannot say for itself: a thinking setting that did not think (the server's launch may hold it to no thinking)."""
    out = list(WARNINGS)
    for r in rows:
        if r["think"] == "on" and r["answered"] and r["thought"] == 0:
            out.append(f"{r['server']} {r['task']}: thinking on, but no answer came back with any thinking")
    out += [f"left out of the sample: {n} {why}" for why, n in SKIPPED.items()]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--recordings", help="a night's zip, a recording folder, or a folder holding recordings")
    ap.add_argument("--server", action="append", default=[], metavar="KIND=URL", help="llama=URL, the llama-server to measure on (once)")
    ap.add_argument("--tasks", default=",".join(TASKS), help="from " + ", ".join(KNOWN))
    ap.add_argument("--per-task", type=int, default=40)
    ap.add_argument("--think", default="off,on", help="off, on, or off,on")
    ap.add_argument("--room", type=int, default=8192, help="more tokens to think in, when thinking is on (no more than the context holds)")
    ap.add_argument("--num-ctx", type=int, default=0, help="(f534) the context every call is given (default: as the night recorded it)")
    ap.add_argument("--model", default=None, help="the model's name on the servers (default: as recorded)")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--ready-wait", type=float, default=600.0, help="seconds to wait for a server to be ready (a model loading)")
    ap.add_argument("--evals", nargs="?", const="interp,ruling", default="",
                    help="also run the game's evaluations --live on the llama-server named: names from " + ", ".join(EVALS)
                    + " (no value: interp,ruling)")
    ap.add_argument("--corpus", default="data/replay/interp_cases.yaml", help="interp_eval's case file for --evals")
    ap.add_argument("--embed-url", default="", help="--evals: an embedding llama-server started by hand (DND_LLAMA_EMBED_URL for the children); "
                                                   "without one the evaluations run with no embedder, their word checks in its place")
    ap.add_argument("--eval-timeout", type=float, default=7200.0)
    ap.add_argument("--summarise", action="store_true", help="rebuild summary.json and summary.md from the results already in --out")
    ap.add_argument("--force", action="store_true", help="measure again over results already in --out")
    ap.add_argument("--out", default="think_ab")
    a = ap.parse_args(argv)
    import config
    folder = Path(a.out)
    tasks = [t.strip() for t in a.tasks.split(",") if t.strip()]
    unknown = [t for t in tasks if t not in KNOWN]
    if unknown:
        ap.error(f"--tasks: {', '.join(unknown)} not among {', '.join(KNOWN)}")
    which = [w.strip() for w in a.evals.split(",") if w.strip()]
    bad_evals = [w for w in which if w not in EVALS]
    if bad_evals:
        ap.error(f"--evals: {', '.join(bad_evals)} not among {', '.join(EVALS)}")
    global NUM_CTX
    NUM_CTX = a.num_ctx or None
    thinks = tuple(x.strip() == "on" for x in a.think.split(",") if x.strip())
    servers, kinds = [], set()
    for s in a.server:
        kind, _, url = s.partition("=")
        if kind not in SERVERS or not url:
            ap.error(f"--server takes llama=URL, not {s!r}")
        if kind in kinds:
            ap.error(f"--server: {kind} named twice (one server of a kind a run; a second goes in a run of its own, with its own --out)")
        kinds.add(kind)
        servers.append((kind, url))
    from datetime import datetime, timezone
    meta = {"made": datetime.now(timezone.utc).isoformat(timespec="seconds"), "recordings": str(a.recordings), "tasks": tasks,
            "per_task": a.per_task, "room": a.room, "model": a.model or config.MODEL, "servers": [f"{k}={u}" for k, u in servers],
            "card": profile().get("card"), "corpus": a.corpus if a.evals else None, "threads": int(getattr(config, "NUM_THREAD", 0) or 0),
            "num_ctx": a.num_ctx or "as recorded", "evals": which}
    if a.summarise:
        results = [json.loads(l) for l in (folder / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        old = json.loads((folder / "summary.json").read_text(encoding="utf-8")) if (folder / "summary.json").exists() else {}
        meta = dict(old.get("meta") or meta, made=meta["made"])
        rows = summarise(results)
        write_summary(folder, rows, old.get("evals") or [], meta)
        print((folder / "summary.md").read_text(encoding="utf-8"))
        return 0
    if not a.recordings:
        ap.error("--recordings is needed (or --summarise)")
    if not servers:
        ap.error("name the server (--server llama=URL)")
    llama_url = next((u for k, u in servers if k == "llama"), None)
    if a.evals:
        if llama_url is None:
            ap.error("--evals needs a llama-server (--server llama=URL): since f528 the game speaks to no other")
        if not (ROOT / a.corpus).exists() and not Path(a.corpus).exists():
            ap.error(f"--corpus {a.corpus} does not exist (tools/interp_corpus.py builds one from a night's run folders)")
        a.corpus = str(Path(a.corpus).resolve()) if Path(a.corpus).exists() else str(ROOT / a.corpus)
        for w in which:
            if not EVALS[w][2] & set(tasks):
                ap.error(f"--evals {w} measures {', '.join(sorted(EVALS[w][2]))}: name one in --tasks")
        if a.model and a.model != config.MODEL:
            ap.error(f"--evals plays the game, which asks for {config.MODEL}; it cannot measure --model {a.model}")
    if (folder / "results.jsonl").exists() and (folder / "results.jsonl").stat().st_size and not a.force:
        ap.error(f"{folder / 'results.jsonl'} is there already: --force to measure again over it, or --summarise to read it")
    chosen = pick(recorded_rows(Path(a.recordings)), tasks, a.per_task)
    print("chosen: " + ", ".join(f"{t} {len(rs)}" for t, rs in chosen.items()))
    for w in WARNINGS:
        print("warning: " + w)
    if not any(chosen.values()) and not which:
        print(f"nothing to measure: no answered first try of {', '.join(tasks)} in {a.recordings}")
        return 2
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "chosen.json").write_text(json.dumps({t: [[r.get("_from"), r.get("i")] for r in rs] for t, rs in chosen.items()}, indent=1),
                                        encoding="utf-8", newline="\n")
    about: dict = {}
    meta["servers_about"] = about
    results, eval_rows = [], []

    def save(evs=None):
        if evs is not None:
            eval_rows[:] = evs                   # the evaluations so far: kept if the run is stopped before the next
        rows = summarise(results)
        meta["warnings"] = warnings_of(rows)
        write_summary(folder, rows, eval_rows, meta)

    try:
        with (folder / "results.jsonl").open("w", encoding="utf-8", newline="\n") as out:
            results = measure(chosen, servers, thinks, a.room, a.timeout, a.model, out, ready_wait=a.ready_wait, about=about)
        save()
        if a.evals:
            st, v = get(llama_url.rstrip("/") + "/health")
            if st != 200:
                print(f"--evals: the llama-server does not answer ({st}: {str(v)[:120]}); skipped")
            else:
                evals(llama_url, tasks, thinks, a.eval_timeout, a.room, a.corpus, folder, done=save, which=which, num_ctx=a.num_ctx or None,
                      embed_url=a.embed_url or None)
    except KeyboardInterrupt:
        if not results and (folder / "results.jsonl").exists():
            results = [json.loads(l) for l in (folder / "results.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        save()
        print("interrupted: the summary holds what was measured")
        return 130
    save()
    print((folder / "summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    import signal
    signal.signal(signal.SIGTERM, signal.default_int_handler)      # a kill keeps the summary, as a Ctrl-C does
    sys.exit(main())
