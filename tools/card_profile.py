"""(f443) What a turn costs on the machine the game is built for, measured, never guessed.

The owner set the budget: "a minimum of a gtx 3060 to play this game with a maximum of a 1 minute for the longest turn" (GOALS.md).
Stage 3's turn budget needs the true speeds of that card. A recording (engine/recording.py) keeps every model call with the server's own
counts (tokens read and written, and the time each took; f527: usage, in the interface's form), so a session recorded on the card
measures it directly:

    python3 tools/card_profile.py <recording> [--card "RTX 3060 12GB"] [--measured-on "RTX A4000"] [--vram-gb 11.2] [--write]

prints what each turn cost, every turn over the minute, and the card's speeds (tokens a second read and written, a model load), and
with --write keeps those speeds in data/measured/card_profile.yaml for the budget to read (f459: a measurement, outside the data hash;
the budget's tunables, the 60 s among them, are data/rules/budget.yaml). A recording made elsewhere (a faster card, the
owner's own play) is re-timed on the card with tools/rerun.py --time <a llama-server on this machine>, which sends every recorded request to
it beside the replay and writes the same measures into the recording (timed.jsonl) for this tool to read.

(f444) When the card itself cannot be had (Runpod rents no RTX 3060), --measured-on names the card the recording was made on, and every
call's reading and writing time is scaled to --card by the two cards' compute and memory bandwidth (data/rules/cards.yaml): an
estimate, kept as one (scaled_from in the profile). --vram-gb, what the model and its context took on the measuring card, says whether
they would fit on the target at all; a model that spills off the card runs many times slower than any scaling says."""
from __future__ import annotations

import argparse
import gzip
import json
import statistics
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))                 # (f468) --estimate prices the calls with the game's own engine/budget.py
PROFILE = ROOT / "data" / "measured" / "card_profile.yaml"


def budget_limit() -> float:
    """(f459) The owner's limit for the longest turn, from data/rules/budget.yaml: one number, read wherever the budget is judged."""
    import yaml
    return float(yaml.safe_load((ROOT / "data" / "rules" / "budget.yaml").read_text(encoding="utf-8"))["limit_seconds"])


BUDGET = budget_limit()


def calls_of(folder: Path) -> list[dict]:
    """The calls with their measures: the re-timed ones (timed.jsonl) when the recording was timed on the card, else as recorded."""
    timed = folder / "timed.jsonl"
    if timed.exists():
        return [json.loads(l) for l in timed.read_text(encoding="utf-8").splitlines() if l.strip()]
    with gzip.open(folder / "calls.jsonl.gz", "rt", encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


def cards() -> dict:
    import yaml
    return yaml.safe_load((ROOT / "data" / "rules" / "cards.yaml").read_text(encoding="utf-8"))["cards"]


def usage_of(c: dict) -> dict:
    """(f527) A call's counts in the interface's form, whichever shape the row has: `usage` (the recorder since f527: prompt, out,
    read_ms, write_ms, load_ms, cached), or the old client's `tokens` (prompt_eval_count, eval_count, the durations in nanoseconds,
    cached) from a recording or a timed.jsonl made before it."""
    u = c.get("usage")
    if isinstance(u, dict) and u:
        return {k: u[k] for k in ("prompt", "out", "read_ms", "write_ms", "load_ms", "cached") if u.get(k) is not None}
    t = c.get("tokens")
    if not isinstance(t, dict) or not t:
        return {}
    out = {}
    if t.get("prompt_eval_count") is not None:
        out["prompt"] = t["prompt_eval_count"]
    if t.get("eval_count") is not None:
        out["out"] = t["eval_count"]
    for src, dst in (("prompt_eval_duration", "read_ms"), ("eval_duration", "write_ms"), ("load_duration", "load_ms")):
        if t.get(src) is not None:
            out[dst] = t[src] / 1e6
    if t.get("cached") is not None:
        out["cached"] = t["cached"]
    return out


def scaled(c: dict, read: float, write: float) -> dict:
    """(f444) One call as the target card would take it: its reading time times `read` and its writing time times `write` (how many
    times faster the measuring card is at each), the rest (a load, the server's own time) as measured."""
    u = usage_of(c)
    rd, wr = float(u.get("read_ms") or 0), float(u.get("write_ms") or 0)
    secs = float(c.get("seconds") or 0)
    if not (rd or wr):
        return c
    new_rd, new_wr = rd * read, wr * write
    return {**c, "usage": {**u, "read_ms": round(new_rd), "write_ms": round(new_wr)}, "seconds": round(secs + (new_rd - rd + new_wr - wr) / 1000, 3)}


def system_share(c: dict) -> float | None:
    """(f535) The constant system message's share of a recorded chat's prompt, by characters of its messages; None when the row carries
    no messages (a re-timed row, timed.jsonl)."""
    ms = (c.get("request") or {}).get("messages") or []
    total = sum(len(str(m.get("content") or "")) for m in ms)
    if not total:
        return None
    return sum(len(str(m.get("content") or "")) for m in ms if m.get("role") == "system") / total


def requests_of(folder: Path) -> dict:
    """(f535) The recording's own request per call index: a re-timed row (timed.jsonl) carries the card's counts and no messages, so the
    system message's share is read from the row the recorder kept."""
    gz = folder / "calls.jsonl.gz"
    if not gz.exists():
        return {}
    with gzip.open(gz, "rt", encoding="utf-8") as f:
        return {r.get("i"): r.get("request") for r in (json.loads(l) for l in f if l.strip()) if r.get("request")}


def measure(folder: Path, read: float = 1.0, write: float = 1.0) -> dict:
    calls = [scaled(c, read, write) for c in calls_of(folder)] if (read, write) != (1.0, 1.0) else calls_of(folder)
    per_input: dict[int, float] = {}
    split: dict[int, list[float]] = {}                                      # (f535) a turn's seconds reading, reading the system, writing
    unknown = 0                                                             # chat rows whose system share could not be read
    requests = requests_of(folder) if (folder / "timed.jsonl").exists() else {}
    read, wrote, loads, embeds = [], [], [], []
    for c in calls:
        per_input[c.get("input", 0)] = per_input.get(c.get("input", 0), 0.0) + float(c.get("seconds") or 0)
        if c.get("kind") != "embed":
            u0 = usage_of(c)
            share = system_share(c if c.get("request") else {**c, "request": requests.get(c.get("i"))})
            if share is None and u0.get("read_ms"):
                unknown += 1
            sp = split.setdefault(c.get("input", 0), [0.0, 0.0, 0.0])
            sp[0] += float(u0.get("read_ms") or 0) / 1000
            sp[1] += float(u0.get("read_ms") or 0) / 1000 * (share or 0.0)
            sp[2] += float(u0.get("write_ms") or 0) / 1000
        if c.get("kind") == "embed":                                        # (f527) the embedder's seconds a text, measured too
            texts = len((c.get("request") or {}).get("input") or [])
            if texts and c.get("seconds"):
                embeds.append(float(c["seconds"]) / texts)
            continue
        u = usage_of(c)
        pe, pd = u.get("prompt"), u.get("read_ms")
        ec, ed = u.get("out"), u.get("write_ms")
        if pe and pd:
            read.append(pe / (pd / 1000))
        if ec and ed:
            wrote.append(ec / (ed / 1000))
        if u.get("load_ms"):
            loads.append(u["load_ms"] / 1000)
    turns = sorted(per_input.items())
    secs = [s for _, s in turns]
    return {
        "calls": len(calls), "turns": len(turns),
        "read_tps": round(statistics.median(read), 1) if read else None,
        "write_tps": round(statistics.median(wrote), 1) if wrote else None,
        "embed_s": round(statistics.median(embeds), 3) if embeds else None,
        "load_s": round(statistics.median(loads), 2) if loads else None,
        "median_turn_s": round(statistics.median(secs), 1) if secs else None,
        "p95_turn_s": round(sorted(secs)[int(0.95 * (len(secs) - 1))], 1) if secs else None,
        "longest_turn_s": round(max(secs), 1) if secs else None,
        "over": [(i, round(s, 1)) for i, s in turns if s > BUDGET],
        # (f535) at the median over the turns, each taken on its own: the seconds a turn reads prompts, the constant system messages'
        # part of that (None when a chat row's share could not be read), and the seconds it writes answers
        "read_s_p50": round(statistics.median(v[0] for v in split.values()), 1) if split else None,
        "system_s_p50": round(statistics.median(v[1] for v in split.values()), 1) if split and not unknown else None,
        "write_s_p50": round(statistics.median(v[2] for v in split.values()), 1) if split else None,
    }


REQUIRED_TITLES = {"ActionPlan": "interpret_action", "Narration": "narrate", "CombatIntent": "combat_interpret", "NPCReply": "npc_conversation", "NPCReplyMany": "npc_conversation",
                   "NPCProfile": "npc_profile", "ResidentSet": "populate_place", "Ruling": "ruling", "CanonCheck": "canon_check",
                   "Extracted": "canon_extract", "MentorReply": "mentor_chat", "MentorSpeech": "mentor_speech", "MentorLines": "mentor_voice",
                   "RoadEvent": "road_event", "LessonWant": "lesson_want", "LessonNames": "generate_lessons", "DiscoveryProposal": "discovery",
                   "PartyIntent": "party_intent", "CampIntent": "camp_intent", "StrangerRead": "stranger_read", "GoddessLine": "goddess_line"}
# (f468) A recording made before its call rows carried the task (f468's recorder): the required tasks by their schema's title, nearly enough.


def estimate_inputs(folder: Path, expected: bool = False) -> list[tuple[int, float]]:
    """(f468) Per input, the seconds the required path estimates from the recording's own text (engine/budget.py estimate: the prompt's
    characters read, the answer's written, at the card's speeds): the chat calls of required tasks and the embed calls those need. The
    done-when's measure, read from a night recording, never from the suite. (f475) `expected`: every answer priced at its task's
    expected size (budget.yaml answer_tokens), not the recorded one. A stand-in model's answers are a few words, so a stub recording
    priced by them measures the prompts alone; Bundle D's gate prices both goldens this way, before and after."""
    from engine import budget
    per: dict[int, float] = {}
    for c in calls_of(folder):
        i = int(c.get("input", 0))
        if c.get("kind") == "embed":
            texts = len((c.get("request") or {}).get("input") or [])
            per[i] = per.get(i, 0.0) + texts * float(budget.PROFILE.get("embed_seconds_per_text") or 0)    # (f527) the card's measured price
            continue
        task = c.get("task") or REQUIRED_TITLES.get(c.get("title", ""), "")
        if not task or budget.need(task) != "required":
            continue
        chars = sum(len(str(m.get("content") or "")) for m in (c.get("request") or {}).get("messages") or [])
        ans = c.get("answer") if isinstance(c.get("answer"), str) else None
        per[i] = per.get(i, 0.0) + budget.estimate(task, chars, len(ans) if ans is not None and not expected else None)
    return sorted(per.items())


def _embed_price() -> float:
    from engine import budget
    return float(budget.PROFILE.get("embed_seconds_per_text") or budget.DEFAULT_PROFILE["embed_seconds_per_text"])


def write(m: dict, card: str, model: str, source: str, scaled_from: str = "", fits: str = "") -> None:
    PROFILE.write_text(
        "# (f443, tools/card_profile.py) Measured on the card the game is built for (GOALS.md: an RTX 3060, no turn over a minute).\n"
        "# Written by the tool from a recording made or re-timed on that card; Stage 3's turn budget reads it. Do not hand-edit numbers.\n"
        "# (f459) A measurement, kept under data/measured, outside the data hash: re-timing it never re-blesses a recording. The budget's\n"
        "# hand-kept tunables are data/rules/budget.yaml.\n"
        f"card: \"{card}\"\nmodel: \"{model}\"\nmeasured: \"{date.today().isoformat()}\"\nsource: \"{source}\"\n"
        f"scaled_from: \"{scaled_from}\"            # (f444) empty when measured on the card itself; else an estimate from that card\n"
        f"fits: \"{fits}\"\n"
        f"calls: {m['calls']}\nturns: {m['turns']}\n"
        f"prompt_tokens_per_second: {m['read_tps']}\nanswer_tokens_per_second: {m['write_tps']}\n"
        f"embed_seconds_per_text: {m.get('embed_s') or _embed_price()}        # (f527) one text through the embedding model, on the card"
        f"{'' if m.get('embed_s') else ' (no embed call in the recording: the price before it, kept)'}\n"
        f"load_seconds: {m['load_s']}\n"
        f"median_turn_seconds: {m['median_turn_s']}\np95_turn_seconds: {m['p95_turn_s']}\nlongest_turn_seconds: {m['longest_turn_s']}\n"
        f"turns_over_budget: {len(m['over'])}\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("recording")
    ap.add_argument("--card", default="RTX 3060 12GB")
    ap.add_argument("--write", action="store_true", help="keep the speeds in data/measured/card_profile.yaml")
    ap.add_argument("--measured-on", default="", help="(f444) the card the recording was made on, when it is not --card: scale to --card")
    ap.add_argument("--vram-gb", type=float, default=0, help="(f444) what the model and its context took on the measuring card")
    ap.add_argument("--estimate", action="store_true", help="(f468) per input, the seconds the required path estimates (engine/budget.py), and the inputs over the limit")
    ap.add_argument("--expected", action="store_true", help="(f475) with --estimate: price every answer at its task's expected size, not the recorded one")
    a = ap.parse_args()
    folder = Path(a.recording)
    if a.estimate:
        rows = estimate_inputs(folder, expected=a.expected)
        over = [(i, s) for i, s in rows if s > BUDGET]
        for i, s in rows:
            print(f"input {i}: {s:.1f} s on the required path")
        print(f"inputs whose required path estimates over {BUDGET:g} s: {len(over)}"
              + (": " + ", ".join(f"input {i} ({s:.0f} s)" for i, s in over[:20]) if over else ""))
        return 0
    read = write_ = 1.0
    fits = ""
    if a.measured_on:
        C = cards()
        src, dst = C[a.measured_on], C[a.card]
        read, write_ = src["tflops"] / dst["tflops"], src["bandwidth_gbs"] / dst["bandwidth_gbs"]
        print(f"scaled from {a.measured_on} to {a.card}: reading x{1 / read:.2f} as fast, writing x{1 / write_:.2f} (an estimate)")
    if a.vram_gb:
        room = cards()[a.card]["memory_gb"]
        fits = f"{a.vram_gb:g} GB of {room} GB" + (" (fits)" if a.vram_gb <= room - 0.5 else " (does not fit: it would spill off the card)")
        print(f"memory: {fits}")
    m = measure(folder, read, write_)
    meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
    print(f"{m['turns']} turns, {m['calls']} calls on {a.card} ({meta.get('model')}): median {m['median_turn_s']} s a turn, 95% under "
          f"{m['p95_turn_s']} s, longest {m['longest_turn_s']} s; reads {m['read_tps']} and writes {m['write_tps']} tokens a second; "
          f"a load {m['load_s']} s")
    print(f"turns over {BUDGET:g} s: {len(m['over'])}" + (": " + ", ".join(f"input {i} ({s} s)" for i, s in m["over"][:20]) if m["over"] else ""))
    if m.get("read_s_p50") is not None:                                 # (f535) where a turn's model time goes, each part at its median
        sys_part = f"the constant system messages {m['system_s_p50']} s of it" if m.get("system_s_p50") is not None else "the system part unknown: no messages kept for some rows"
        print(f"at the median, a turn reads prompts for {m['read_s_p50']} s ({sys_part}) and writes answers for {m['write_s_p50']} s")
    if a.write:
        write(m, a.card, meta.get("model", ""), folder.name, a.measured_on, fits)
        print(f"kept in {PROFILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
