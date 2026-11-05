"""(f533) Thinking on and off, task by task, measured before the owner decides which of the game's calls should think.

The owner asked to try thinking for the judgment calls (reading the player's line, rulings, the audit's two checks, the canon check,
reading a move in a fight) and to keep it off for prose. This tool measures what it costs and what it changes, on a server of either
kind the game may run on:

  1. Recorded requests. The first try of each chosen task's calls in recordings (a night's run folders, a recording folder, or the
     night's zip as fetched) is sent again, once with thinking off and once on, to each server given: Ollama (/api/chat, its `think`)
     and llama-server (/v1/chat/completions, the template's enable_thinking, the schema as its JSON grammar). Each answer is scored by
     the game's own contract (it parses, it validates), against the decision the night recorded (the plan's kinds, the ruling's sense,
     the audit's match, the move, the canon verdict), for leaked thinking (an answer that is not the JSON alone), for being cut off, and
     timed: wall seconds, the server's own counts, and what the call would take on the minimum card (data/measured/card_profile.yaml).
     Thinking off and on go in turn for each request, the order alternating, so neither always finds the prompt already cached.
  2. The game's own evaluations (--evals, against Ollama, which the game speaks to until f528): tools/interp_eval.py on the night
     corpus and tools/ruling_eval.py, both --live, once with thinking off and once with it on for the chosen tasks (DND_THINK_TASKS):
     how many of their cases each gets right.

    python tools/think_ab.py --recordings post_e_full.zip --server ollama=http://127.0.0.1:11434 --server llama=http://127.0.0.1:8080
    python tools/think_ab.py --recordings nightrun/ --server ollama=http://127.0.0.1:11434 --per-task 60 --evals --out think_ab/

It writes results.jsonl (one row a call, with the first response's raw fields from each server, to learn their names), summary.json and
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TASKS = ("interpret_action", "ruling", "audit_meaning", "audit_compare", "canon_check", "combat_interpret")
DECISION = {                                   # what each answer decides, compared with what the night decided (None: free text only)
    "ActionPlan": lambda d: [a.get("kind") for a in d.get("actions", [])],
    "Ruling": lambda d: d.get("sense"),
    "AuditVerdict": lambda d: d.get("matches"),
    "CombatIntent": lambda d: [d.get("kind"), d.get("target", ""), d.get("ability", "")],
    "CanonCheck": lambda d: d.get("verdict"),
    "AuditMeaning": None,
}
SAMPLER_KEYS = ("temperature", "top_k", "top_p", "min_p", "typical_p", "repeat_penalty", "repeat_last_n", "presence_penalty",
                "frequency_penalty")


# ---------- what was recorded

def recorded_rows(path: Path):
    """Every call row of the recordings at path: a .zip (each */calls.jsonl.gz inside), one recording folder, or a folder of them."""
    path = Path(path)
    if path.suffix == ".zip":
        with zipfile.ZipFile(path) as z:
            for name in sorted(n for n in z.namelist() if n.endswith("calls.jsonl.gz")):
                with gzip.open(io.BytesIO(z.read(name)), "rt", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            yield dict(json.loads(line), _from=name)
        return
    files = [path / "calls.jsonl.gz"] if (path / "calls.jsonl.gz").exists() else sorted(path.rglob("calls.jsonl.gz"))
    for p in files:
        with gzip.open(p, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    yield dict(json.loads(line), _from=str(p))


def pick(rows, tasks, per_task: int, seed: int = 533) -> dict[str, list[dict]]:
    """Each task's first tries that were answered (the request as first made, the night's own decision beside it), a fixed sample of
    at most per_task, in the order they were made."""
    by: dict[str, list[dict]] = {t: [] for t in tasks}
    for r in rows:
        t = r.get("task")
        msgs = (r.get("request") or {}).get("messages") or []
        if t in by and r.get("kind") == "chat" and len(msgs) == 2 and not r.get("error") and r.get("answer"):
            by[t].append(r)
    rng = random.Random(seed)
    out = {}
    for t, rs in by.items():
        keep = sorted(rng.sample(range(len(rs)), per_task)) if len(rs) > per_task else range(len(rs))
        out[t] = [rs[i] for i in keep]
    return out


def schema_of(title: str):
    from llm import contracts
    return getattr(contracts, title)


# ---------- the two servers

def _options(row: dict, think: bool, room: int) -> dict:
    opts = {k: v for k, v in ((row.get("request") or {}).get("options") or {}).items() if k != "num_thread"}
    if think:
        opts["num_predict"] = int(opts.get("num_predict") or 0) + room
    return opts


def ollama_body(row: dict, schema, think: bool, room: int, model: str | None = None) -> dict:
    req = row.get("request") or {}
    import config
    return {"model": model or req.get("model") or config.MODEL, "messages": req.get("messages"), "format": schema.model_json_schema(),
            "options": _options(row, think, room), "think": bool(think), "stream": False, "keep_alive": req.get("keep_alive", "30m")}


def llama_body(row: dict, schema, think: bool, room: int, model: str | None = None) -> dict:
    """The same request as llama-server takes it: the schema as its JSON grammar, every sampler sent (the game's measured table under
    the call's own values, llm/sampling.py BASE, so none of the server's own defaults apply), thinking by the template's switch."""
    from llm.sampling import BASE
    import config
    req = row.get("request") or {}
    opts = _options(row, think, room)
    samplers = {**BASE, **{k: v for k, v in opts.items() if k in SAMPLER_KEYS}}
    body = {"model": model or req.get("model") or config.MODEL, "messages": req.get("messages"),
            "response_format": {"type": "json_schema", "json_schema": {"name": row.get("title") or schema.__name__,
                                                                         "schema": schema.model_json_schema(), "strict": True}},
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


def read_ollama(resp: dict) -> dict:
    m = resp.get("message") or {}
    return {"content": m.get("content") or "", "thinking": m.get("thinking") or "", "finish": resp.get("done_reason"),
            "prompt_tokens": resp.get("prompt_eval_count"), "answer_tokens": resp.get("eval_count"),
            "server_seconds": round((resp.get("total_duration") or 0) / 1e9, 3) or None,
            "fields": sorted(resp), "message_fields": sorted(m)}


def read_llama(resp: dict) -> dict:
    ch = (resp.get("choices") or [{}])[0]
    m = ch.get("message") or {}
    usage, timings = resp.get("usage") or {}, resp.get("timings") or {}
    ms = (timings.get("prompt_ms") or 0) + (timings.get("predicted_ms") or 0)
    return {"content": m.get("content") or "", "thinking": m.get("reasoning_content") or "", "finish": ch.get("finish_reason"),
            "prompt_tokens": usage.get("prompt_tokens", timings.get("prompt_n")), "answer_tokens": usage.get("completion_tokens", timings.get("predicted_n")),
            "server_seconds": round(ms / 1000, 3) if ms else None, "fields": sorted(resp), "message_fields": sorted(m),
            "timing_fields": sorted(timings)}


SERVERS = {"ollama": ("/api/chat", ollama_body, read_ollama), "llama": ("/v1/chat/completions", llama_body, read_llama)}


# ---------- scoring

def score(title: str, content: str, recorded: str) -> dict:
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
        schema.model_validate_json(text)
        out["valid"] = True
    except Exception as e:
        out["error"] = f"refused by the contract: {str(e).splitlines()[0][:160]}"
    decide = DECISION.get(title)
    if decide is not None:
        try:
            out["agree"] = decide(got) == decide(json.loads(recorded))
        except Exception:
            out["agree"] = None
    return out


def card_seconds(prompt_tokens, answer_tokens, profile: dict) -> float | None:
    """What the call would take on the minimum card, from its measured speeds (the thinking is written at the answer's speed)."""
    try:
        return round(float(prompt_tokens or 0) / float(profile["prompt_tokens_per_second"])
                     + float(answer_tokens or 0) / float(profile["answer_tokens_per_second"]), 2)
    except Exception:
        return None


def profile() -> dict:
    import yaml
    p = ROOT / "data" / "measured" / "card_profile.yaml"
    return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}) if p.exists() else {}


# ---------- the run

def measure(chosen: dict[str, list[dict]], servers: list[tuple[str, str]], thinks=(False, True), room: int = 1024,
            timeout: float = 300.0, model: str | None = None, out=None, say=print) -> list[dict]:
    card = profile()
    results = []
    for name, base in servers:
        kind = name.split("=")[0] if "=" in name else name
        path, body_of, read = SERVERS[kind]
        say(f"{name}: warming the model ({base})")
        warm_row = next((r for rs in chosen.values() for r in rs), None)
        if warm_row is not None:
            post(base.rstrip("/") + path, body_of(warm_row, schema_of(warm_row["title"]), False, 0, model), timeout)
        for task, rows in chosen.items():
            for n, row in enumerate(rows):
                order = list(thinks) if n % 2 == 0 else list(reversed(thinks))
                for think in order:
                    schema = schema_of(row["title"])
                    status, resp, took = post(base.rstrip("/") + path, body_of(row, schema, think, room, model), timeout)
                    got = read(resp) if status == 200 and isinstance(resp, dict) else {"content": "", "thinking": "", "finish": None,
                                                                                          "prompt_tokens": None, "answer_tokens": None,
                                                                                          "server_seconds": None}
                    sc = score(row["title"], got["content"], row.get("answer", "")) if status == 200 else \
                        {"parsed": False, "valid": False, "leaked": False, "agree": None, "error": f"HTTP {status}: {str(resp)[:200]}"}
                    res = {"server": kind, "url": base, "task": task, "title": row["title"], "think": think, "row": row.get("i"),
                           "from": row.get("_from", ""), "status": status, "seconds": round(took, 3), **sc,
                           "finish": got.get("finish"), "cut": got.get("finish") == "length", "prompt_tokens": got.get("prompt_tokens"),
                           "answer_tokens": got.get("answer_tokens"), "server_seconds": got.get("server_seconds"),
                           "thinking_chars": len(got.get("thinking") or ""), "answer_chars": len(got.get("content") or ""),
                           "card_seconds": card_seconds(got.get("prompt_tokens"), got.get("answer_tokens"), card),
                           "recorded_seconds": row.get("seconds")}
                    if n == 0:
                        res["raw_fields"] = {k: got.get(k) for k in ("fields", "message_fields", "timing_fields") if k in got}
                    results.append(res)
                    if out is not None:
                        out.write(json.dumps(res, ensure_ascii=False) + "\n")
                        out.flush()
            say(f"  {task}: {len(rows)} requests, thinking {'/'.join('on' if t else 'off' for t in thinks)}")
    return results


def _q(values, q):
    v = sorted(x for x in values if isinstance(x, (int, float)))
    if not v:
        return None
    return round(v[min(len(v) - 1, int(round(q * (len(v) - 1))))], 2)


def summarise(results: list[dict]) -> list[dict]:
    rows = []
    keys = sorted({(r["server"], r["task"], r["think"]) for r in results}, key=lambda k: (k[0], TASKS.index(k[1]) if k[1] in TASKS else 99, k[2]))
    for server, task, think in keys:
        rs = [r for r in results if (r["server"], r["task"], r["think"]) == (server, task, think)]
        answered = [r for r in rs if r["status"] == 200]
        agreed = [r for r in rs if r["agree"] is not None]
        pct = lambda xs, n: round(100.0 * len(xs) / n, 1) if n else None
        rows.append({"server": server, "task": task, "think": "on" if think else "off", "n": len(rs), "answered": len(answered),
                     "valid_pct": pct([r for r in rs if r["valid"]], len(rs)), "parsed_pct": pct([r for r in rs if r["parsed"]], len(rs)),
                     "agree_pct": pct([r for r in agreed if r["agree"]], len(agreed)), "leaked": sum(1 for r in rs if r["leaked"]),
                     "cut": sum(1 for r in rs if r["cut"]), "seconds_median": _q([r["seconds"] for r in answered], 0.5),
                     "seconds_p90": _q([r["seconds"] for r in answered], 0.9),
                     "answer_tokens_mean": round(statistics.mean([r["answer_tokens"] for r in answered if r["answer_tokens"]]), 1)
                     if any(r["answer_tokens"] for r in answered) else None,
                     "thinking_chars_mean": round(statistics.mean([r["thinking_chars"] for r in answered]), 1) if answered else None,
                     "card_seconds_median": _q([r["card_seconds"] for r in answered], 0.5),
                     "card_seconds_p90": _q([r["card_seconds"] for r in answered], 0.9)})
    return rows


def evals(ollama_url: str, tasks, thinks=(False, True), timeout: float = 7200.0) -> list[dict]:
    """The game's own evaluations, --live against Ollama, thinking off and then on for the chosen tasks: how many cases each gets right."""
    host = re.sub(r"^https?://", "", ollama_url.rstrip("/"))
    runs = [("interp_eval", [sys.executable, "tools/interp_eval.py", "--corpus", "data/replay/interp_corpus.yaml", "--live"],
             r"(\d+)/(\d+) right"),
            ("ruling_eval", [sys.executable, "tools/ruling_eval.py", "--live"], r"(\d+) of (\d+) right")]
    out = []
    for think in thinks:
        env = {k: v for k, v in os.environ.items() if k != "MERAVIA_NO_SERVER"}
        env.update(OLLAMA_HOST=host, DND_THINK_TASKS=",".join(tasks) if think else "")
        for name, cmd, pattern in runs:
            t0 = time.perf_counter()
            r = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True, timeout=timeout)
            m = re.findall(pattern, r.stdout + r.stderr)
            right, total = (int(m[-1][0]), int(m[-1][1])) if m else (None, None)
            out.append({"eval": name, "think": "on" if think else "off", "right": right, "of": total, "rc": r.returncode,
                        "seconds": round(time.perf_counter() - t0, 1), "tail": (r.stdout + r.stderr).strip().splitlines()[-3:]})
    return out


def write_summary(folder: Path, rows: list[dict], eval_rows: list[dict], meta: dict) -> None:
    (folder / "summary.json").write_text(json.dumps({"meta": meta, "calls": rows, "evals": eval_rows}, indent=1), encoding="utf-8")
    lines = [f"# Thinking on and off ({meta['made']})", "", f"Recordings: {meta['recordings']}. Tasks: {', '.join(meta['tasks'])}. "
             f"Up to {meta['per_task']} first tries a task; {meta['room']} more tokens to think in. Minimum card from "
             f"data/measured/card_profile.yaml ({meta.get('card') or 'none'}).", "",
             "| server | task | thinking | n | answered | valid % | agrees with the night % | leaked | cut off | s median | s p90 | answer tokens | thinking chars | card s median | card s p90 |",
             "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in rows:
        lines.append(f"| {r['server']} | {r['task']} | {r['think']} | {r['n']} | {r['answered']} | {r['valid_pct']} | {r['agree_pct']} | {r['leaked']} | "
                     f"{r['cut']} | {r['seconds_median']} | {r['seconds_p90']} | {r['answer_tokens_mean']} | {r['thinking_chars_mean']} | "
                     f"{r['card_seconds_median']} | {r['card_seconds_p90']} |")
    if eval_rows:
        lines += ["", "| evaluation | thinking | right | of | seconds |", "| --- | --- | --- | --- | --- |"]
        lines += [f"| {e['eval']} | {e['think']} | {e['right']} | {e['of']} | {e['seconds']} |" for e in eval_rows]
    (folder / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--recordings", required=True, help="a night's zip, a recording folder, or a folder holding recordings")
    ap.add_argument("--server", action="append", default=[], metavar="KIND=URL", help="ollama=URL or llama=URL (repeatable)")
    ap.add_argument("--tasks", default=",".join(TASKS))
    ap.add_argument("--per-task", type=int, default=40)
    ap.add_argument("--think", default="off,on", help="off, on, or off,on")
    ap.add_argument("--room", type=int, default=1024, help="more tokens to think in, when thinking is on")
    ap.add_argument("--model", default=None, help="the model's name on the servers (default: as recorded)")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--evals", action="store_true", help="also run interp_eval and ruling_eval --live against the Ollama server")
    ap.add_argument("--out", default="think_ab")
    a = ap.parse_args(argv)
    tasks = [t.strip() for t in a.tasks.split(",") if t.strip()]
    thinks = tuple(x.strip() == "on" for x in a.think.split(",") if x.strip())
    servers = []
    for s in a.server:
        kind, _, url = s.partition("=")
        if kind not in SERVERS or not url:
            ap.error(f"--server takes ollama=URL or llama=URL, not {s!r}")
        servers.append((kind, url))
    if not servers:
        ap.error("name at least one server (--server ollama=URL or llama=URL)")
    chosen = pick(recorded_rows(Path(a.recordings)), tasks, a.per_task)
    print("chosen: " + ", ".join(f"{t} {len(rs)}" for t, rs in chosen.items()))
    folder = Path(a.out)
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "results.jsonl").open("w", encoding="utf-8") as out:
        results = measure(chosen, servers, thinks, a.room, a.timeout, a.model, out)
    eval_rows = []
    if a.evals:
        url = next((u for k, u in servers if k == "ollama"), None)
        if url is None:
            print("--evals needs an Ollama server (the game speaks to Ollama until f528); skipped")
        else:
            eval_rows = evals(url, tasks, thinks)
    from datetime import datetime, timezone
    meta = {"made": datetime.now(timezone.utc).isoformat(timespec="seconds"), "recordings": str(a.recordings), "tasks": tasks,
            "per_task": a.per_task, "room": a.room, "servers": [f"{k}={u}" for k, u in servers], "card": profile().get("card")}
    rows = summarise(results)
    write_summary(folder, rows, eval_rows, meta)
    print((folder / "summary.md").read_text(encoding="utf-8"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
