"""(f441) Play a recorded session again through the real turn, and say where it parts from the recording: the rebuild's Stage 1.

    python3 tools/rerun.py recordings/<name>            replay; stop at the first input whose state, outcomes or words differ
    python3 tools/rerun.py recordings/<name> --loose    answers served by order and kind even where a prompt's words changed (for a
                                                        stage that changes prompts); only the state and outcomes are compared
    python3 tools/rerun.py --golden [--rebless]         replay the kept stub recording (data/replay/sessions/stub_short); with
                                                        --rebless, record it again and print what changed, to read before keeping it
    python3 tools/rerun.py recordings/<name> --time URL (f443) send every recorded request to the model at URL as the replay meets it,
                                                        and keep how long each took (timed.jsonl) for tools/card_profile.py

A recording (engine/recording.py) holds the save as the session opened, every input, and every model call in order. The replay copies
the save into a scratch one, builds the scene the way main.py does, feeds the inputs, and serves each recorded answer to the call the
game makes in its place: a call that asks for something else (another kind of answer, or, unless --loose, other words) is the first
sign the code now plays differently. After every input the save's fingerprint (storage/statehash.py), the turn's outcomes and the
words shown are compared with the recording's. Recorded failures are raised again, so retries and rolled-back turns repeat.

Run it from the repository root. Exit status 0 when every input matched."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
GOLDEN = ROOT / "data" / "replay" / "sessions" / "stub_short"
SCRIPTS = ROOT / "data" / "replay" / "scripts"        # (f476) a kept recording made from a script: data/replay/scripts/<name>.py


def golden(name: str = "stub_short") -> Path:
    """(f476) A kept recording by name: stub_short (the night bot's), stub_party (a script's)."""
    return ROOT / "data" / "replay" / "sessions" / name


from core.interrupts import Interrupt    # (f449) raised on purpose, and let through every catch that would otherwise make it a failed try


class Parted(Interrupt):
    """The replay has parted from the recording."""


def load(folder: Path) -> dict:
    rows = lambda name: [json.loads(l) for l in (folder / name).read_text(encoding="utf-8").splitlines() if l.strip()]
    with gzip.open(folder / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
        calls = [json.loads(l) for l in f if l.strip()]
    return {"meta": json.loads((folder / "meta.json").read_text(encoding="utf-8")), "inputs": rows("inputs.jsonl"), "calls": calls,
            "turns": rows("turns.jsonl")}


def report_rebless(old: dict, new: dict) -> None:
    """(f459) What moved between the kept recording and the new one, read before a re-bless is accepted: the inputs whose state differs
    and in which tables, the calls (count, title order, every request that differs), the outcomes and the shown words per input, and
    the first shown line that moved. A difference the feature did not predict is a stop, not a bless."""
    ot, nt = old["turns"], new["turns"]
    changed = [(t, u) for t, u in zip(ot, nt) if t["state"]["all"] != u["state"]["all"]]
    print(f"inputs whose state differs from the kept recording: {[t['i'] for t, _ in changed][:20] or 'none'}; calls {len(old['calls'])} -> "
          f"{len(new['calls'])}; inputs {len(old['inputs'])} -> {len(new['inputs'])}")
    for t, u in changed[:10]:
        print(f"  input {t['i']}: tables that differ: {[k for k in t['state'] if k != 'all' and t['state'].get(k) != u['state'].get(k)]}")
    titles_old, titles_new = [c.get("title") for c in old["calls"]], [c.get("title") for c in new["calls"]]
    if titles_old != titles_new:
        k = next((j for j, (x, y) in enumerate(zip(titles_old, titles_new)) if x != y), min(len(titles_old), len(titles_new)))
        print(f"the calls' titles part at call {k}: {titles_old[k:k + 3]} -> {titles_new[k:k + 3]}")
    else:
        print("the calls' titles are the same, in the same order")
    req = [(c.get("i"), c.get("input"), c.get("title")) for c, d in zip(old["calls"], new["calls"]) if c.get("req") != d.get("req")]
    print(f"calls whose request differs: {len(req)}" + (": " + ", ".join(f"call {i} (input {n}, {t})" for i, n, t in req[:12]) if req else ""))
    if req:                                                                     # (f476) grouped by title
        by = {}
        for _, _, t in req:
            by[t] = by.get(t, 0) + 1
        print("  by title: " + ", ".join(f"{t} {n}" for t, n in sorted(by.items(), key=lambda x: (-x[1], str(x[0])))))
    report_rows(old, new, changed)
    report_placement(old, new)
    print(f"inputs whose outcomes differ: {[t['i'] for t, u in zip(ot, nt) if t.get('outcomes') != u.get('outcomes')][:20] or 'none'}")
    moved = [(t, u) for t, u in zip(ot, nt) if t.get("shown") != u.get("shown")]
    print(f"inputs whose shown words differ: {[t['i'] for t, _ in moved][:20] or 'none'}")
    for t, u in moved[:3]:
        a, b = t.get("shown_text"), u.get("shown_text")
        if a is None or b is None:
            print(f"  input {t['i']}: {t.get('lines')} -> {u.get('lines')} lines (the kept recording holds no text to compare)")
            continue
        k = next((j for j, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))
        print(f"  input {t['i']}: line {k + 1} moved: {a[k] if k < len(a) else '(none)'!r} -> {b[k] if k < len(b) else '(none)'!r}")


def report_rows(old: dict, new: dict, changed: list) -> None:
    """(f476) For each input whose state differs, the rows and keys that moved, from each recording's own record of what it changed
    (engine/recording.py rows): what the new one changed that the kept one did not, and the other way, every key named."""
    for t, u in changed[:12]:
        a, b = t.get("rows"), u.get("rows")
        if a is None or b is None:
            print(f"  input {t['i']}: {'the kept recording' if a is None else 'the new one'} holds no rows to compare")
            continue
        for table in sorted(set(a) | set(b)):
            x, y = a.get(table, {}), b.get(table, {})
            for part in ("added", "gone", "changed"):
                px, py = x.get(part) or {}, y.get(part) or {}
                if isinstance(px, list) or isinstance(py, list):
                    px, py = {str(k): "" for k in (px or [])}, {str(k): "" for k in (py or [])}
                for key in sorted(set(px) | set(py), key=str):
                    vx, vy = px.get(key), py.get(key)
                    if vx == vy:
                        continue
                    if part == "changed" and isinstance(vx, dict) and isinstance(vy, dict):
                        cols = sorted(set(vx) | set(vy))
                        moved = [f"{c} {vx.get(c, '(unchanged)')!r} -> {vy.get(c, '(unchanged)')!r}" for c in cols if vx.get(c) != vy.get(c)]
                        print(f"  input {t['i']}: {table} {key} {part}: " + "; ".join(moved))
                    else:
                        print(f"  input {t['i']}: {table} {key} {part}: {vx!r} -> {vy!r}")


def placement(rec: dict) -> dict:
    """(f476) Each task's calls by the kind of operation they were made inside (engine/recording.py call op, joined to the turn's
    operations), or "outside": where Bundle D moves a call out of a transaction, this is what moves."""
    kind_of = {o["id"]: o["kind"] for t in rec["turns"] for o in (t.get("operations") or [])}
    out: dict = {}
    for c in rec["calls"]:
        task = c.get("task") or c.get("title") or c.get("kind", "?")
        where = kind_of.get(c.get("op") or "", "outside") if c.get("op") else "outside"
        out.setdefault(task, {})
        out[task][where] = out[task].get(where, 0) + 1
    return out


def report_placement(old: dict, new: dict) -> None:
    a, b = placement(old), placement(new)
    moved = [(t, a.get(t, {}), b.get(t, {})) for t in sorted(set(a) | set(b)) if a.get(t) != b.get(t)]
    if not moved:
        print("calls by operation kind: unchanged")
        return
    print("calls by operation kind that moved:")
    for t, x, y in moved:
        print(f"  {t}: {x} -> {y}")


def _failure(err: list):
    import httpx
    import ollama
    kind, text = (err + ["", ""])[:2]
    if "Timeout" in kind:
        return httpx.ReadTimeout(text)
    if kind == "ResponseError":
        return ollama.ResponseError(text)
    if kind in ("HTTPError", "ConnectError", "RemoteProtocolError"):
        return httpx.HTTPError(text)
    return ConnectionError(text)


def replay(folder: Path, loose: bool = False, quiet: bool = True, on_call=None) -> dict:
    """Replay one recording. Returns {"matched": n inputs, "of": n, "parted": None | {...where and how}}. on_call(row, k) is told of
    every call the game makes, with the recorded row it was served (the real-card timing, f443, sends the same request to a model)."""
    rec = load(folder)
    from engine import recording, streams
    from llm import embed, gateway
    from storage import statehash
    if rec["meta"].get("data") != statehash.data_hash():
        print("warning: this recording was made on other rules or content (its data hash differs); differences may be that", file=sys.stderr)
    streams.STRICT = True
    from engine import budget
    profile_before = dict(budget.PROFILE)
    if isinstance(rec["meta"].get("profile"), dict):                                   # (f468) the speeds the recording priced its calls at:
        budget.PROFILE.update({k: float(v) for k, v in rec["meta"]["profile"].items() if k in ("read_tps", "write_tps") and v})   # the replay defers where it did
    import config, tempfile
    scratch = Path(tempfile.mkdtemp(prefix="rerun_logs_"))         # a replay's own logs never mix with real play's
    config.LOG_PATH, config.TURN_LOG_PATH, config.PULSE_LOG_PATH = (str(scratch / n) for n in ("llm_calls.jsonl", "turns.jsonl", "pulse.jsonl"))
    config.AUDIT_LOG = config.REFUSALS_LOG = False
    embed._state.update(ok=bool(rec["meta"].get("embed")), fixed=bool(rec["meta"].get("embed")), failed=False)
    from npc import life
    life.FIRST_BATCH = rec["meta"].get("backfill", life.FIRST_BATCH)

    calls, inputs, turns = list(rec["calls"]), list(rec["inputs"]), list(rec["turns"])
    state = {"call": 0, "input": 0, "shown": [], "parted": None}

    def serve(kind: str, k: dict):
        if state["call"] >= len(calls):
            raise Parted(f"the game made a call the recording does not have (a {kind}, '{(k.get('format') or {}).get('title', '')}')")
        row = calls[state["call"]]
        state["call"] += 1
        title = (k.get("format") or {}).get("title", "") if isinstance(k.get("format"), dict) else ""
        if row["kind"] != kind or row.get("title", "") != title:
            raise Parted(f"call {row['i']} (input {row['input']}): the game asked for a {kind} '{title}', the recording has a "
                         f"{row['kind']} '{row.get('title', '')}'")
        if not loose and recording.request_hash(k) != row["req"]:
            raise Parted(f"call {row['i']} (input {row['input']}, '{title}'): the game asked in other words than the recording")
        if on_call:
            on_call(row, k)
        if row.get("error"):
            raise _failure(row["error"])
        if kind == "embed":
            return types.SimpleNamespace(embeddings=(row.get("answer") or {}).get("embeddings"))
        return types.SimpleNamespace(done_reason=row.get("done", "stop"), message=types.SimpleNamespace(content=row.get("answer", "")),
                                     **(row.get("tokens") or {}))

    gateway._client = types.SimpleNamespace(chat=lambda **k: serve("chat", k), embed=lambda **k: serve("embed", k))

    from ui import console
    for name in recording.STORY:
        if hasattr(console, name):
            setattr(console, name, lambda *a, _n=name, **k: state["shown"].append(" ".join(str(x) for x in a) + "".join(f" {v}" for v in k.values())))
    console.panel = lambda name, data: False
    if quiet:
        for name in ("out", "status_block", "combat_state", "show_header", "debug"):
            if hasattr(console, name):
                setattr(console, name, lambda *a, **k: None)

    # the save as the session opened, under a scratch name
    name = "rerun_" + folder.name
    shutil.rmtree(ROOT / "saves" / name, ignore_errors=True)
    (ROOT / "saves" / name).mkdir(parents=True)
    shutil.copy(folder / "start.db", ROOT / "saves" / name / "campaign.db")
    from npc.traits import load_traits
    from engine.session import CampaignSession
    from engine import ledger
    session = CampaignSession.open(name)                    # (f453) the campaign's session, as main.py opens it
    store = session.store
    ws = session.scene(load_traits(), store.load_player())

    def check_input() -> None:
        """The input just played against what the recording says it did."""
        i = state["input"]
        want = next((t for t in turns if t["i"] == i), None)
        if want is None:
            return
        got = statehash.digest(store)
        shown = hashlib.sha256("\n".join(state["shown"]).encode("utf-8")).hexdigest()
        if got["all"] != want["state"]["all"]:
            tables = [t for t in got if t != "all" and got[t] != want["state"].get(t)]
            raise Parted(f"after input {i} ({inputs_main[i - 1]['text']!r}) the state differs, in: {', '.join(tables)}")
        if json.loads(json.dumps(ledger.LAST, default=str)) != want["outcomes"]:
            raise Parted(f"after input {i} ({inputs_main[i - 1]['text']!r}) the turn recorded other outcomes")
        if "operations" in want:                                                       # (f463) the operations committed, their ids, kinds and rows
            ops = [{"id": o["id"], "kind": o["kind"], "rows": o["rows"]} for o in store.load_operations()["ops"] if o.get("steps") == store.meta.steps]
            if json.loads(json.dumps(ops, default=str)) != want["operations"]:
                raise Parted(f"after input {i} ({inputs_main[i - 1]['text']!r}) the line committed other operations "
                             f"({[o['kind'] for o in ops]} against {[o['kind'] for o in want['operations']]})")
        from engine import operation
        presented, operation.PRESENTED[:] = json.loads(json.dumps(operation.PRESENTED, default=str)), []
        if "presented" in want and presented != want["presented"]:                     # (f467) what reached the page and how: shown, a stand-in, recovered at the load
            raise Parted(f"after input {i} ({inputs_main[i - 1]['text']!r}) the page was given other outcomes "
                         f"({[p['how'] for p in presented]} against {[p['how'] for p in want['presented']]})")
        if not loose and shown != want["shown"]:
            raise Parted(f"after input {i} ({inputs_main[i - 1]['text']!r}) the player was shown other words "
                         f"({len(state['shown'])} lines against {want['lines']})")
        state["shown"] = []

    inputs_main = [r for r in inputs if r["main"]]
    queue = list(inputs)

    def ask(*a, **k):
        main = bool(k.get("main", a[0] if a else False))
        if main and state["input"]:
            check_input()
        if not queue:
            if main:
                return "quit"
            raise Parted("the game asked a question the recording never answered")
        row = queue.pop(0)
        if row["main"] != main:
            raise Parted(f"the game {'waited for a new line' if main else 'asked a question mid-turn'} where the recording "
                         f"{'answered a question' if main else 'gave a new line'} ({row['text']!r})")
        if main:
            state["input"] += 1
        return row["text"]

    console.ask = ask
    try:
        ws.run()
        if state["input"]:
            check_input()
    except Parted as e:
        state["parted"] = {"input": state["input"], "why": str(e)}
    finally:
        session.close()
        shutil.rmtree(ROOT / "saves" / name, ignore_errors=True)
        streams.STRICT = False
        budget.PROFILE.clear()
        budget.PROFILE.update(profile_before)
    matched = state["input"] - (1 if state["parted"] else 0)
    return {"matched": max(0, matched), "of": len(inputs_main), "parted": state["parted"], "calls": state["call"], "recorded_calls": len(calls)}


def timer(folder: Path, url: str):
    """(f443) An on_call for replay(): the same request, sent to the model at url (the card the game is built for), timed, its counts
    kept in the recording's timed.jsonl. The game goes on with the recorded answer, so the session stays the one recorded."""
    import time
    import ollama
    live = ollama.Client(host=url, timeout=900)
    out = (folder / "timed.jsonl").open("w", encoding="utf-8")
    COUNTS = ("prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration", "load_duration", "total_duration")

    def on_call(row: dict, k: dict) -> None:
        t0 = time.perf_counter()
        err, got = "", {}
        try:
            r = live.embed(**k) if row["kind"] == "embed" else live.chat(**k)
            got = {c: getattr(r, c, None) for c in COUNTS}
        except Exception as e:                      # the card failing a call is a measure too
            err = f"{type(e).__name__}: {str(e)[:200]}"
        out.write(json.dumps({"i": row["i"], "input": row["input"], "kind": row["kind"], "title": row.get("title", ""),
                              "seconds": round(time.perf_counter() - t0, 3), "tokens": {c: v for c, v in got.items() if v is not None},
                              "error": err}) + "\n")
        out.flush()
    return on_call


# ---------- the kept stub recording

def make_stub_recording(folder: Path, n: int = 40, seed: int = 39, persona: str = "wanderer", rows: bool = True) -> Path:
    """Record a session of n inputs under the stub, chosen by the night bot: walks, talk, road stops and fights, a pane command, and
    a turn whose model call fails and is rolled back, then said again. Run in a process of its own (it installs the stub)."""
    import random
    import simlib
    stub = simlib.Stub("warrior", seed)
    simlib.install(stub)
    from engine import recording
    from engine.session import CampaignSession
    from llm import gateway
    from npc.traits import load_traits
    from storage.campaign import PlayerState
    from ui import console
    from world.loader import authored
    import nightbot
    save = "rerun_make_" + folder.name
    shutil.rmtree(ROOT / "saves" / save, ignore_errors=True)
    session = CampaignSession.open(save)                     # (f453)
    store = session.store
    store.meta.seed, store.meta.turn, store.meta.minutes = seed, 1, 480
    store.save_meta()
    char, _ = simlib.make_character("warrior", random.Random(seed))
    player = PlayerState(character=char, location=authored().start_location)
    player.mentor["never"] = True
    store.save_player(player)
    for name in recording.STORY:
        if hasattr(console, name):
            setattr(console, name, lambda *a, **k: None)
    console.panel = lambda name, data: False
    for name in ("out", "status_block", "combat_state", "show_header", "debug"):
        if hasattr(console, name):
            setattr(console, name, lambda *a, **k: None)
    fail = {"on": False}
    real = gateway._client

    def chat(**k):
        if fail["on"] and k["format"].get("title") == "ActionPlan":
            raise ConnectionError("the model server cannot be reached")
        return real.chat(**k)
    gateway._client = types.SimpleNamespace(chat=chat)
    ws = session.scene(load_traits(), store.load_player())
    bot = nightbot.Bot(ws, ws.world, random.Random(seed), stub=stub, persona=persona)
    stub.bot = bot
    count, last = {"n": 0}, {"text": "I look around."}

    def ask(*a, **k):
        if not k.get("main", a[0] if a else False):
            return "yes"
        count["n"] += 1
        fail["on"] = count["n"] == 6                    # the sixth line's turn fails and rolls back; the seventh says it again
        if count["n"] > n:
            return "quit"
        if count["n"] == 4:
            return "#stats"
        if count["n"] == 7:
            return last["text"]
        text, _kind = bot.decide()
        last["text"] = text
        return text
    console.ask = ask
    session.record(folder=folder, rows=rows)                # (f476) a kept recording names the rows each input changed
    try:
        ws.run()
    finally:
        session.close()
        shutil.rmtree(ROOT / "saves" / save, ignore_errors=True)
    return folder


def make_scripted_recording(folder: Path, name: str) -> Path:
    """(f476) Record a kept session from its script (data/replay/scripts/<name>.py): the script builds the save (setup), plants the
    stand-in model's answers, and gives each line with the actions the stub reads it as (STEPS); its CENSUS names what the recording
    must hold, and the maker refuses one that holds less. Run in a process of its own (it installs the stub)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(f"script_{name}", SCRIPTS / f"{name}.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    script.record(folder, ROOT)
    rec = load(folder)
    missing = script.census(rec)
    if missing:
        raise SystemExit(f"the {name} recording lacks what its script promises: {', '.join(missing)}")
    return folder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("recording", nargs="?", help="a recording folder (recordings/<name>)")
    ap.add_argument("--loose", action="store_true", help="serve answers by order and kind even where a prompt's words changed")
    ap.add_argument("--golden", nargs="?", const="stub_short", default=None, metavar="NAME",
                    help="replay a kept recording (stub_short when no name is given; stub_party, made from its script)")
    ap.add_argument("--rebless", action="store_true", help="with --golden: record it again, and say what changed")
    ap.add_argument("--make", metavar="FOLDER", help="record a stub session into FOLDER (used by the tests)")
    ap.add_argument("--inputs", type=int, default=40)
    ap.add_argument("--time", metavar="URL", help="(f443) send every recorded request to the model at URL beside the replay, and keep "
                    "how long each took in the recording's timed.jsonl (tools/card_profile.py reads it)")
    a = ap.parse_args()
    if a.make:
        make_stub_recording(Path(a.make), a.inputs)
        print(f"recorded {a.make}")
        return 0
    if a.golden and a.rebless:
        target = golden(a.golden)
        old = load(target) if (target / "meta.json").exists() else None
        tmp = target.with_name(target.name + "_new")
        shutil.rmtree(tmp, ignore_errors=True)
        if (SCRIPTS / f"{a.golden}.py").exists():
            make_scripted_recording(tmp, a.golden)                        # (f476) a script's recording
        else:
            make_stub_recording(tmp, a.inputs)
        new = load(tmp)
        if old:
            report_rebless(old, new)
        else:
            print(f"{a.golden}: kept for the first time ({len(new['inputs'])} inputs, {len(new['calls'])} calls)")
            for t, w in sorted(placement(new).items()):
                print(f"  {t}: {w}")
        shutil.rmtree(target, ignore_errors=True)
        tmp.rename(target)
        print(f"kept {target.relative_to(ROOT)}: read the differences above before committing it")
        return 0
    folder = golden(a.golden) if a.golden else Path(a.recording or "")
    if not (folder / "meta.json").exists():
        ap.error(f"no recording at {folder}")
    out = replay(folder, loose=a.loose, on_call=timer(folder, a.time) if a.time else None)
    if out["parted"]:
        print(f"parted at input {out['parted']['input']} of {out['of']}: {out['parted']['why']}")
        return 1
    print(f"all {out['of']} inputs matched ({out['calls']} model calls served)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
