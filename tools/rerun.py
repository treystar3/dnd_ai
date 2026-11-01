"""(f441) Play a recorded session again through the real turn, and say where it parts from the recording: the rebuild's Stage 1.

    python3 tools/rerun.py recordings/<name>            replay; stop at the first input whose state, outcomes or words differ
    python3 tools/rerun.py recordings/<name> --loose    answers served by order and kind even where a prompt's words changed (for a
                                                        stage that changes prompts); only the state and outcomes are compared
    python3 tools/rerun.py --golden [--rebless]         replay the kept stub recording (data/replay/sessions/stub_short); with
                                                        --rebless, record it again and print what changed, to read before keeping it

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


class Parted(Exception):
    """The replay has parted from the recording."""


def load(folder: Path) -> dict:
    rows = lambda name: [json.loads(l) for l in (folder / name).read_text(encoding="utf-8").splitlines() if l.strip()]
    with gzip.open(folder / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
        calls = [json.loads(l) for l in f if l.strip()]
    return {"meta": json.loads((folder / "meta.json").read_text(encoding="utf-8")), "inputs": rows("inputs.jsonl"), "calls": calls,
            "turns": rows("turns.jsonl")}


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
    from scenes.world import WorldScene
    from storage.campaign import CampaignStore
    from world.loader import campaign_world
    from engine import ledger
    store = CampaignStore.open_or_create(name)
    ws = WorldScene(store, campaign_world(), load_traits(), store.load_player())

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
        store.close()
        shutil.rmtree(ROOT / "saves" / name, ignore_errors=True)
        streams.STRICT = False
    matched = state["input"] - (1 if state["parted"] else 0)
    return {"matched": max(0, matched), "of": len(inputs_main), "parted": state["parted"], "calls": state["call"], "recorded_calls": len(calls)}


# ---------- the kept stub recording

def make_stub_recording(folder: Path, n: int = 40, seed: int = 39, persona: str = "wanderer") -> Path:
    """Record a session of n inputs under the stub, chosen by the night bot: walks, talk, road stops and fights, a pane command, and
    a turn whose model call fails and is rolled back, then said again. Run in a process of its own (it installs the stub)."""
    import random
    import simlib
    stub = simlib.Stub("warrior", seed)
    simlib.install(stub)
    from engine import recording
    from llm import gateway
    from npc.traits import load_traits
    from scenes.world import WorldScene
    from storage.campaign import CampaignStore, PlayerState
    from ui import console
    from world.loader import authored, campaign_world
    import nightbot
    save = "rerun_make_" + folder.name
    shutil.rmtree(ROOT / "saves" / save, ignore_errors=True)
    store = CampaignStore.open_or_create(save)
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
    ws = WorldScene(store, campaign_world(), load_traits(), store.load_player())
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
    rec = recording.Recorder(store, folder=folder).install()
    try:
        ws.run()
    finally:
        rec.close()
        store.close()
        shutil.rmtree(ROOT / "saves" / save, ignore_errors=True)
    return folder


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("recording", nargs="?", help="a recording folder (recordings/<name>)")
    ap.add_argument("--loose", action="store_true", help="serve answers by order and kind even where a prompt's words changed")
    ap.add_argument("--golden", action="store_true", help="replay the kept stub recording")
    ap.add_argument("--rebless", action="store_true", help="with --golden: record it again, and say what changed")
    ap.add_argument("--make", metavar="FOLDER", help="record a stub session into FOLDER (used by the tests)")
    ap.add_argument("--inputs", type=int, default=40)
    a = ap.parse_args()
    if a.make:
        make_stub_recording(Path(a.make), a.inputs)
        print(f"recorded {a.make}")
        return 0
    if a.golden and a.rebless:
        old = load(GOLDEN) if (GOLDEN / "meta.json").exists() else None
        tmp = GOLDEN.with_name("stub_short_new")
        make_stub_recording(tmp, a.inputs)
        new = load(tmp)
        if old:
            changed = [t["i"] for t, u in zip(old["turns"], new["turns"]) if t["state"]["all"] != u["state"]["all"]]
            print(f"inputs whose state differs from the kept recording: {changed[:20] or 'none'}; calls {len(old['calls'])} -> "
                  f"{len(new['calls'])}; inputs {len(old['inputs'])} -> {len(new['inputs'])}")
        shutil.rmtree(GOLDEN, ignore_errors=True)
        tmp.rename(GOLDEN)
        print(f"kept {GOLDEN.relative_to(ROOT)}: read the differences above before committing it")
        return 0
    folder = GOLDEN if a.golden else Path(a.recording or "")
    if not (folder / "meta.json").exists():
        ap.error(f"no recording at {folder}")
    out = replay(folder, loose=a.loose)
    if out["parted"]:
        print(f"parted at input {out['parted']['input']} of {out['of']}: {out['parted']['why']}")
        return 1
    print(f"all {out['of']} inputs matched ({out['calls']} model calls served)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
