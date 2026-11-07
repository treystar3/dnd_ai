"""(f441) Play a recorded session again through the real turn, and say where it parts from the recording: the rebuild's Stage 1.

    python3 tools/rerun.py recordings/<name>            replay; stop at the first input whose state, outcomes or words differ
    python3 tools/rerun.py recordings/<name> --loose    answers served by order and kind even where a prompt's words changed (for a
                                                        stage that changes prompts); only the state and outcomes are compared
    python3 tools/rerun.py --golden [--rebless]         replay the kept stub recording (data/replay/sessions/stub_short); with
                                                        --rebless, record it again and print what changed, to read before keeping it
    python3 tools/rerun.py recordings/<name> --time URL (f443) send every recorded request to the llama-server at URL (on this machine) as the replay meets it,
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
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
from llm.errors import Failure     # noqa: E402  (f514) imports nothing of the server's
GOLDEN = ROOT / "data" / "replay" / "sessions" / "stub_short"
SCRIPTS = ROOT / "data" / "replay" / "scripts"        # (f476) a kept recording made from a script: data/replay/scripts/<name>.py


def golden(name: str = "stub_short") -> Path:
    """(f476) A kept recording by name: stub_short (the night bot's), stub_party and stub_fight (f495) (each a script's)."""
    return ROOT / "data" / "replay" / "sessions" / name


from core.interrupts import Interrupt    # (f449) raised on purpose, and let through every catch that would otherwise make it a failed try


class Parted(Interrupt):
    """The replay has parted from the recording."""


class Unreplayable(ValueError):
    """(f517, R5) A recording a replay cannot serve faithfully: two recorded calls were on their way at once (the replay serves them one
    after another, so which answer went to which call is not known), or its calls are out of their order."""


def refusal(meta: dict, calls: list, replaying: bool = True) -> str:
    """(f517, R5) Why a recording cannot be replayed, or '' when it can: a call marked as overlapping another, meta's overlapped count
    above 0 (a recording made before f517 has none: 0), or the calls' numbers not rising in the file's order. A gap is allowed (a
    cancelled call writes no row). (f527) Rows in the old client's form (done, tokens) cannot be served either; a re-bless still reads
    such a recording to compare against (replaying=False)."""
    if replaying and any(isinstance(c, dict) and ("done" in c or "tokens" in c) and "finish" not in c and "usage" not in c for c in calls):
        return "its rows hold the old client's fields (done, tokens: made before f527); the replay serves the interface's (finish, usage)"
    flagged = [c.get("i") for c in calls if c.get("overlap")]
    if flagged:
        return f"{len(flagged)} recorded call(s) overlapped another (calls {flagged[:5]}); a replay serves calls one after another"
    if int(meta.get("overlapped") or 0) > 0:
        return f"meta.json counts {meta['overlapped']} overlapping call(s); a replay serves calls one after another"
    numbers = [c.get("i") for c in calls]
    if all(isinstance(n, int) for n in numbers):
        bad = next((j for j in range(1, len(numbers)) if numbers[j] <= numbers[j - 1]), None)
        if bad is not None:
            return f"the calls are out of their order at row {bad} (call {numbers[bad]} after call {numbers[bad - 1]})"
    return ""


def load(folder: Path, replaying: bool = True) -> dict:
    """A recording's four files, read. (f517) Refused (Unreplayable) when its calls cannot be served one after another as recorded;
    (f527) replaying=False reads a recording only to compare against, whatever form its rows have."""
    rows = lambda name: [json.loads(l) for l in (folder / name).read_text(encoding="utf-8").splitlines() if l.strip()]
    with gzip.open(folder / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
        calls = [json.loads(l) for l in f if l.strip()]
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    why = refusal(meta, calls, replaying)
    if why:
        raise Unreplayable(f"{folder}: {why}")
    return {"meta": meta, "inputs": rows("inputs.jsonl"), "calls": calls, "turns": rows("turns.jsonl")}


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


def neutral_of(row: dict, schema_sha: str | None = None) -> dict:
    """(f527) A recorded row's request in the neutral form: as it is when the row already holds one (made since f527), else rebuilt from
    the request in the old client's shape the recorder wrote before (model, messages, format's title, options, think): the base laid under the
    options, num_predict as the ceiling, the schema's fingerprint from the contract of that title (or `schema_sha`, the new row's, for
    a schema built at run time, which a title alone cannot rebuild)."""
    import hashlib
    import config
    from llm import contracts, sampling
    r = row.get("request") or {}
    if row.get("kind") == "embed":
        return {"model": config.EMBED_MODEL, "input": r.get("input")}
    if "schema_sha" in r:
        return r
    title = row.get("title", "")
    opts = {k: v for k, v in (r.get("options") or {}).items() if k not in ("num_thread", "num_ctx")}
    n_predict, temperature = opts.pop("num_predict", None), opts.pop("temperature", None)
    cls = getattr(contracts, title, None)
    sha = (hashlib.sha256(json.dumps(cls.model_json_schema(), sort_keys=True).encode("utf-8")).hexdigest()[:16]
           if isinstance(cls, type) and hasattr(cls, "model_json_schema") else schema_sha)
    return {"model": config.MODEL, "messages": r.get("messages"), "schema": title, "schema_sha": sha,
            "sampling": {**sampling.BASE, **opts, "temperature": temperature}, "max_tokens": n_predict, "think": bool(r.get("think")),
            "voice": None}


def translate(old: dict, new: dict) -> list[str]:
    """(f527) The kept recording's rows against the new one's, request by request: each old row's request in the neutral form, hashed
    (engine/recording.py request_hash), and the two sequences of fingerprints aligned (difflib: the longest common run, so a dropped or
    an added row never throws the rest off). Returns one line per row that found no match: an old row the new recording no longer makes
    (named with its number, input and title), a new row the kept one never had, or a pair of the same title whose words differ, named
    with the fields that moved. Empty: every request is the same one, only written anew."""
    import difflib
    from engine import recording
    o, n = old["calls"], new["calls"]
    nh = [c.get("req") for c in n]
    shas_by_title: dict = {}                               # (f527's review) a title built at run time may have several shapes in one recording
    for c in n:
        if c.get("kind") == "chat":
            shas_by_title.setdefault(c.get("title"), []).append((c.get("request") or {}).get("schema_sha"))
    neutral, oh = [], []
    for c in o:
        shas = list(dict.fromkeys(shas_by_title.get(c.get("title"), [None])))
        tried = [(neutral_of(c, sha), None) for sha in shas]
        tried = [(k, recording.request_hash(k)) for k, _ in tried]
        k, h = next(((k, h) for k, h in tried if h in nh), tried[0])    # the shape that matches a new row, else the first seen
        neutral.append(k)
        oh.append(h)
    FIELDS = ("messages", "schema", "schema_sha", "sampling", "max_tokens", "think", "voice", "input", "model")

    def name(c):
        return f"call {c.get('i')} (input {c.get('input')}, {c.get('kind')} {c.get('title', '')!r})"
    out = []
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, oh, nh, autojunk=False).get_opcodes():
        if tag == "equal":
            continue
        if tag == "delete":
            out += [f"old {name(o[i])} is not made any more" for i in range(i1, i2)]
        elif tag == "insert":
            out += [f"new {name(n[j])} is new" for j in range(j1, j2)]
        else:                                                       # replace: pair them up as far as they go
            for k in range(max(i2 - i1, j2 - j1)):
                a = o[i1 + k] if i1 + k < i2 else None
                b = n[j1 + k] if j1 + k < j2 else None
                if a is None:
                    out.append(f"new {name(b)} is new")
                elif b is None:
                    out.append(f"old {name(a)} is not made any more")
                elif a.get("kind") == b.get("kind") and a.get("title", "") == b.get("title", ""):
                    na, nb = neutral[i1 + k], b.get("request") or {}
                    moved = [f for f in FIELDS if na.get(f) != nb.get(f)]
                    out.append(f"old {name(a)} -> new call {b.get('i')}: the request's words differ in {moved or ['?']}")
                else:
                    out.append(f"old {name(a)} against new {name(b)}: no match")
    return out


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


class Replay:
    """(f518) A recording's calls as the model's source (llm/backend.py use; R1: it replaces everything below the recorder): each call
    the game makes is served the next row, in the file's order, once its kind, its title and (unless loose) its request's fingerprint
    are the row's; on_call(row, k) is told with the old client's arguments (--time sends them to a llama-server on a live card). A recorded answer is
    served as the old client gave it (its done_reason and counts), a recorded error is raised as the Failure it was read as
    (llm/backend.py legacy_failure: no import of the old client), and anything else the game asks for parts the replay. Its facts are
    the recording's (R4): an embedder when the recording had one."""

    name = "replay"

    def __init__(self, calls: list, meta: dict, loose: bool = False, on_call=None):
        import threading
        self.rows, self.meta, self.loose, self.on_call = list(calls), dict(meta), loose, on_call
        self.at = 0
        self._lock = threading.Lock()

    def _row(self, kind: str, k: dict, request=None) -> dict:
        from engine import recording
        from llm import backend
        from llm.errors import Failure
        title = k.get("schema", "") if kind == "chat" else ""                     # (f527) the neutral request's schema title
        with self._lock:
            if self.at >= len(self.rows):
                raise Parted(f"the game made a call the recording does not have (a {kind}, '{title}')")
            row = self.rows[self.at]
            self.at += 1
        if row["kind"] != kind or row.get("title", "") != title:
            raise Parted(f"call {row['i']} (input {row['input']}): the game asked for a {kind} '{title}', the recording has a "
                         f"{row['kind']} '{row.get('title', '')}'")
        if not self.loose and recording.request_hash(k) != row["req"]:
            raise Parted(f"call {row['i']} (input {row['input']}, '{title}'): the game asked in other words than the recording")
        if self.on_call:
            self.on_call(row, k, request)
        err = row.get("error")
        if err:
            if isinstance(err, dict):                                           # (f527) the interface's own kind and detail
                raise Failure(err.get("kind") or "server", str(err.get("detail") or ""))
            raise backend.legacy_failure(err)                                   # a row from before f527 (load() refuses such a recording; kept for a row served by hand)
        return row

    def chat(self, req, deadline=None):
        from llm import backend
        row = self._row("chat", backend.neutral_request(req), req)
        return backend.Reply(text=row.get("answer", ""), finish=row.get("finish") or "stop", usage=row.get("usage") or None)

    def embed(self, texts):
        from llm import backend
        row = self._row("embed", backend.embed_request(texts), texts)
        return backend.Embedding(vectors=(row.get("answer") or {}).get("embeddings"))

    def load(self, progress=None) -> None:
        pass

    def close(self) -> None:
        pass

    def state(self) -> str:
        return "ready"

    def facts(self) -> dict:
        import config
        return {"source": self.name, "model": self.meta.get("model", config.MODEL), "embed_model": config.EMBED_MODEL,
                "embedder": bool(self.meta.get("embed"))}


class _NoServer:
    """(f518) While a recording is made or replayed, the process has no model server (MERAVIA_NO_SERVER), so nothing it does can
    reach a real model: a --rebless outside the suite never records a live answer."""

    def __enter__(self):
        self.before = os.environ.get("MERAVIA_NO_SERVER")
        os.environ["MERAVIA_NO_SERVER"] = "1"

    def __exit__(self, *exc):
        if self.before is None:
            os.environ.pop("MERAVIA_NO_SERVER", None)
        else:
            os.environ["MERAVIA_NO_SERVER"] = self.before


def replay(folder: Path, loose: bool = False, quiet: bool = True, on_call=None) -> dict:
    """Replay one recording. Returns {"matched": n inputs, "of": n, "parted": None | {...where and how}}. on_call(row, k, request) is told
    of every call the game makes, with the recorded row it was served, the neutral request and the request itself (the real-card timing,
    f443, sends the same request to a model)."""
    rec = load(folder)
    from engine import recording, streams
    from llm import embed
    from storage import statehash
    if rec["meta"].get("data") != statehash.data_hash():
        print("warning: this recording was made on other rules or content (its data hash differs); differences may be that", file=sys.stderr)
    streams.STRICT = True
    from engine import budget
    profile_before = dict(budget.PROFILE)
    slow_before = budget.SLOW
    cached_before = budget.CACHED
    budget.CACHED = bool(rec["meta"].get("budget_cached"))                           # (f538) made before f538: reuse was charged as read
    budget.SLOW = bool(rec["meta"].get("slow"))                                      # (f526) a recording made below the minimum card
    if isinstance(rec["meta"].get("profile"), dict):                                   # (f468) the speeds the recording priced its calls at:
        budget.PROFILE.update({k: float(v) for k, v in rec["meta"]["profile"].items() if k in budget.DEFAULT_PROFILE and v})   # the replay defers where it did
    import config, tempfile
    think_before = (config.THINK_TASKS, config.THINK_ROOM)         # (f533) the replay asks as the recording did: its tasks thought, or none
    config.THINK_TASKS = frozenset(rec["meta"].get("think_tasks") or ())
    config.THINK_ROOM = int(rec["meta"].get("think_room", config.THINK_ROOM))
    scratch = Path(tempfile.mkdtemp(prefix="rerun_logs_"))         # a replay's own logs never mix with real play's
    config.LOG_PATH, config.TURN_LOG_PATH, config.PULSE_LOG_PATH = (str(scratch / n) for n in ("llm_calls.jsonl", "turns.jsonl", "pulse.jsonl"))
    config.CRASH_LOG_PATH, config.SESSION_STATS_PATH = str(scratch / "crash.log"), str(scratch / "sessions.jsonl")   # (f518) nor its faults
    config.AUDIT_LOG = config.REFUSALS_LOG = False
    from engine import crashlog
    from llm import backend
    embed.reset()                                                  # (f518) the embedder is the recording's (Replay's facts), from a fresh state
    from npc import life
    life.FIRST_BATCH = rec["meta"].get("backfill", life.FIRST_BATCH)

    calls, inputs, turns = list(rec["calls"]), list(rec["inputs"]), list(rec["turns"])
    state = {"call": 0, "input": 0, "shown": [], "parted": None}
    source = Replay(calls, rec["meta"], loose=loose, on_call=on_call)
    crashes0 = len(crashlog.SESSION)
    no_server = _NoServer()
    no_server.__enter__()
    undo_source = backend.use(source)                              # (f518) a source, no longer a patch on the client

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
    name = f"rerun_{folder.name}_{os.getpid()}"             # (f529) this process's own: two replays of one recording at once (the suite
    shutil.rmtree(ROOT / "saves" / name, ignore_errors=True)   # runs tests in parallel) never share a save
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
        undo_source()
        no_server.__exit__()
        embed.reset()
        shutil.rmtree(ROOT / "saves" / name, ignore_errors=True)
        streams.STRICT = False
        budget.PROFILE.clear()
        budget.PROFILE.update(profile_before)
        budget.SLOW = slow_before
        budget.CACHED = cached_before
        config.THINK_TASKS, config.THINK_ROOM = think_before
    matched = state["input"] - (1 if state["parted"] else 0)
    return {"matched": max(0, matched), "of": len(inputs_main), "parted": state["parted"], "calls": source.at, "recorded_calls": len(calls),
            "crashed": len(crashlog.SESSION) - crashes0, "logs": str(scratch)}   # (f518) faults the replay hit (its own crash.log)


TIME_DEADLINE = 900.0       # the seconds one re-timed call may take: a slow card's longest passage is the measure, never cut (the hang guard is 120 s)


def timer(folder: Path, url: str, key: str = "", embed_url: str | None = None, embed_key: str = ""):
    """(f443, f532) An on_call for replay(): the same request, sent to a llama-server on this machine at url (the game's own build started
    by hand on the card the game is built for, or DND_BACKEND=llama's; a loopback address, as the adapter takes), timed, its counts kept in
    the recording's timed.jsonl in the interface's form (usage: prompt, out, read_ms, write_ms, cached, and load_ms when the model loaded
    before the call; tools/card_profile.py reads it). The game goes on with the recorded answer, so the session stays the one recorded. A
    chat is rebuilt from the request exactly: its messages, its schema as the grammar, every sampler as recorded, the answer's ceiling as
    recorded (a thinking call's room is in it), thinking as recorded. An embedding goes to embed_url's server when one is named, else its
    row says it was skipped. Raises Failure when a server is not answering at the start."""
    import time
    from llm import llama
    from llm.sampling import BASE
    chat_server = llama.Server(llama._port_of(url, "--time"), key)
    embed_server = llama.Server(llama._port_of(embed_url, "--time-embed"), embed_key) if embed_url else None
    llama.LlamaServer(chat_server, embed_server).load()            # waits for the server(s) to be ready
    out = (folder / "timed.jsonl").open("w", encoding="utf-8")

    def on_call(row: dict, k: dict, request) -> None:
        from llm import backend
        t0 = time.perf_counter()
        err, usage, skipped = "", {}, ""
        try:
            if row["kind"] == "embed":
                texts = list(request) if isinstance(request, (list, tuple)) else list(request["input"])
                if embed_server is None:
                    skipped = "no embedding server (--time-embed URL)"
                else:
                    status, payload, wall, loading = embed_server.request("POST", "/v1/embeddings", llama.embed_body(texts), TIME_DEADLINE)
                    if status != 200:
                        err = f"HTTP {status}: {str(payload)[:200]}"
                    else:
                        usage = {"prompt": int(((payload or {}).get("usage") or {}).get("prompt_tokens") or 0), "total_ms": round(wall)}
                        if loading:
                            usage["load_ms"] = round(loading)
            else:
                neutral = backend.neutral_request(request) if isinstance(request, backend.ChatRequest) else dict(request)
                if isinstance(request, backend.ChatRequest):
                    schema = request.schema.model_json_schema()
                else:                                   # a bare neutral row: the contract its title names
                    from llm import contracts
                    schema = getattr(contracts, str(neutral.get("schema") or "")).model_json_schema()
                sampling = {**BASE, **(neutral.get("sampling") or {})}
                body = {"model": neutral.get("model"), "messages": neutral["messages"], "grammar": llama.grammar_of(schema),
                        **{key_: sampling[key_] for key_ in llama.SAMPLER_KEYS if key_ in sampling},
                        "n_predict": int(neutral["max_tokens"]), "chat_template_kwargs": {"enable_thinking": bool(neutral.get("think"))},
                        "cache_prompt": True, "stream": False}
                status, payload, wall, loading = chat_server.request("POST", "/v1/chat/completions", body, TIME_DEADLINE)
                if status != 200 or not isinstance(payload, dict):
                    err = f"HTTP {status}: {str(payload)[:200]}"
                else:
                    usage = llama.usage_of(payload, wall, None)
                    if loading:                     # the model loading before this call answered (card_profile reads it as load_ms)
                        usage["load_ms"] = round(loading)
        except Exception as e:                      # the card failing a call is a measure too
            err = f"{type(e).__name__}: {str(e)[:200]}"
        out.write(json.dumps({"i": row["i"], "input": row["input"], "kind": row["kind"], "title": row.get("title", ""),
                              "seconds": round(time.perf_counter() - t0, 3), "usage": usage, "error": err,
                              **({"skipped": skipped} if skipped else {})}) + "\n")
        out.flush()
    return on_call


# ---------- the kept stub recording

def make_stub_recording(folder: Path, n: int = 40, seed: int = 39, persona: str = "wanderer", rows: bool = True) -> Path:
    """Record a session of n inputs under the stub, chosen by the night bot: walks, talk, road stops and fights, a pane command, and
    a turn whose model call fails and is rolled back, then said again. Run in a process of its own (it installs the stub)."""
    import random
    import simlib
    stub = simlib.Stub("warrior", seed)
    held = simlib.install(stub)
    from engine import recording
    from engine.session import CampaignSession
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

    def chat(**k):
        if fail["on"] and k["format"].get("title") == "ActionPlan":
            from llm.errors import Failure
            raise Failure("server", "the model server cannot be reached")     # (f527) the server's failure, in the interface's own kind
        return stub.chat(**k)
    planted = simlib.stand_in(chat=chat)                    # (f518) the stub with its failure planted, a source above the stub's own
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
    with _NoServer():                                       # (f518) nothing it does can reach a real model
        session.record(folder=folder, rows=rows)            # (f476) a kept recording names the rows each input changed
        try:
            ws.run()
        finally:
            session.close()
            planted()
            held()
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
    with _NoServer():                                       # (f518) nothing a script records can reach a real model
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
                    help="replay a kept recording (stub_short when no name is given; stub_party and stub_fight, made from their scripts)")
    ap.add_argument("--rebless", action="store_true", help="with --golden: record it again, and say what changed")
    ap.add_argument("--translate", action="store_true", help="(f527) with --rebless: every kept row's request in the neutral form against the new rows' fingerprints")
    ap.add_argument("--make", metavar="FOLDER", help="record a stub session into FOLDER (used by the tests)")
    ap.add_argument("--inputs", type=int, default=40)
    ap.add_argument("--time", metavar="URL", help="(f443) send every recorded request to the llama-server at URL beside the replay, and keep "
                    "how long each took in the recording's timed.jsonl (tools/card_profile.py reads it)")
    ap.add_argument("--time-key", default="", help="--time's API key, if the server has one")
    ap.add_argument("--time-embed", metavar="URL", default="", help="--time: the embedding llama-server beside it (else the embed rows are skipped)")
    a = ap.parse_args()
    import config
    if (a.make or a.rebless) and config.THINK_TASKS:              # (f533) a kept recording is made as the game ships: no task thinks
        print(f"note: DND_THINK_TASKS ({', '.join(sorted(config.THINK_TASKS))}) is set; the recording is made with no task thinking")
        config.THINK_TASKS = frozenset()
    if a.make:
        make_stub_recording(Path(a.make), a.inputs)
        print(f"recorded {a.make}")
        return 0
    if a.golden and a.rebless:
        target = golden(a.golden)
        old = load(target, replaying=False) if (target / "meta.json").exists() else None     # (f527) compared, not replayed
        tmp = target.with_name(target.name + "_new")
        shutil.rmtree(tmp, ignore_errors=True)
        try:                                                           # (f517) a re-record that cannot be replayed is never kept,
            if (SCRIPTS / f"{a.golden}.py").exists():                  # whichever way it was made (a script's census loads it too)
                make_scripted_recording(tmp, a.golden)                    # (f476) a script's recording
            else:
                make_stub_recording(tmp, a.inputs)
            new = load(tmp)
        except Unreplayable as e:
            shutil.rmtree(tmp, ignore_errors=True)
            print(f"refused: {e}")
            return 2
        if old:
            report_rebless(old, new)
            if a.translate:
                unmatched = translate(old, new)
                print(f"translated: {len(old['calls'])} kept requests against {len(new['calls'])} new; "
                      + ("every request the same, written anew" if not unmatched else f"{len(unmatched)} without a match:"))
                for line in unmatched[:40]:
                    print("  " + line)
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
    try:
        load(folder)                                                   # (f517) refused before anything is opened for writing:
        out = replay(folder, loose=a.loose, on_call=timer(folder, a.time, a.time_key, a.time_embed) if a.time else None)   # --time's timed.jsonl is kept
    except Unreplayable as e:
        print(f"refused: {e}")
        return 2
    except Failure as e:                                                # --time's server is not answering: a line, not a traceback
        print(f"the server at {a.time} is not answering: {e}")
        return 2
    if out["parted"]:
        print(f"parted at input {out['parted']['input']} of {out['of']}: {out['parted']['why']}")
        return 1
    if out.get("crashed"):                                             # (f518) a turn that faulted is no match, whatever the state
        print(f"{out['crashed']} turn(s) faulted while it replayed (see {out['logs']}/crash.log), though the state matched")
        return 1
    print(f"all {out['of']} inputs matched ({out['calls']} model calls served)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
