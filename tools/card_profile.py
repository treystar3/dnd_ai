"""(f443) What a turn costs on the machine the game is built for, measured, never guessed.

The owner set the budget: "a minimum of a gtx 3060 to play this game with a maximum of a 1 minute for the longest turn" (GOALS.md).
Stage 3's turn budget needs the true speeds of that card. A recording (engine/recording.py) keeps every model call with Ollama's own
counts (tokens read and written, and the time each took), so a session recorded on the card measures it directly:

    python3 tools/card_profile.py <recording> [--card "RTX 3060 12GB"] [--measured-on "RTX A4000"] [--vram-gb 11.2] [--write]

prints what each turn cost, every turn over the minute, and the card's speeds (tokens a second read and written, a model load), and
with --write keeps those speeds in data/rules/card_profile.yaml for the budget to read. A recording made elsewhere (a faster card, the
owner's own play) is re-timed on the card with tools/rerun.py --time <the card's Ollama URL>, which sends every recorded request to
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
PROFILE = ROOT / "data" / "rules" / "card_profile.yaml"
BUDGET = 60.0


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


def scaled(c: dict, read: float, write: float) -> dict:
    """(f444) One call as the target card would take it: its reading time times `read` and its writing time times `write` (how many
    times faster the measuring card is at each), the rest (a load, the server's own time) as measured."""
    t = dict(c.get("tokens") or {})
    pd, ed = t.get("prompt_eval_duration") or 0, t.get("eval_duration") or 0
    secs = float(c.get("seconds") or 0)
    if not (pd or ed):
        return c
    new_pd, new_ed = pd * read, ed * write
    t.update(prompt_eval_duration=int(new_pd), eval_duration=int(new_ed))
    return {**c, "tokens": t, "seconds": round(secs + (new_pd - pd + new_ed - ed) / 1e9, 3)}


def measure(folder: Path, read: float = 1.0, write: float = 1.0) -> dict:
    calls = [scaled(c, read, write) for c in calls_of(folder)] if (read, write) != (1.0, 1.0) else calls_of(folder)
    per_input: dict[int, float] = {}
    read, wrote, loads = [], [], []
    for c in calls:
        per_input[c.get("input", 0)] = per_input.get(c.get("input", 0), 0.0) + float(c.get("seconds") or 0)
        t = c.get("tokens") or {}
        pe, pd = t.get("prompt_eval_count"), t.get("prompt_eval_duration")
        ec, ed = t.get("eval_count"), t.get("eval_duration")
        if pe and pd:
            read.append(pe / (pd / 1e9))
        if ec and ed:
            wrote.append(ec / (ed / 1e9))
        if t.get("load_duration"):
            loads.append(t["load_duration"] / 1e9)
    turns = sorted(per_input.items())
    secs = [s for _, s in turns]
    return {
        "calls": len(calls), "turns": len(turns),
        "read_tps": round(statistics.median(read), 1) if read else None,
        "write_tps": round(statistics.median(wrote), 1) if wrote else None,
        "load_s": round(statistics.median(loads), 2) if loads else None,
        "median_turn_s": round(statistics.median(secs), 1) if secs else None,
        "p95_turn_s": round(sorted(secs)[int(0.95 * (len(secs) - 1))], 1) if secs else None,
        "longest_turn_s": round(max(secs), 1) if secs else None,
        "over": [(i, round(s, 1)) for i, s in turns if s > BUDGET],
    }


def write(m: dict, card: str, model: str, source: str, scaled_from: str = "", fits: str = "") -> None:
    PROFILE.write_text(
        "# (f443, tools/card_profile.py) Measured on the card the game is built for (GOALS.md: an RTX 3060, no turn over a minute).\n"
        "# Written by the tool from a recording made or re-timed on that card; Stage 3's turn budget reads it. Do not hand-edit numbers.\n"
        f"card: \"{card}\"\nmodel: \"{model}\"\nmeasured: \"{date.today().isoformat()}\"\nsource: \"{source}\"\n"
        f"scaled_from: \"{scaled_from}\"            # (f444) empty when measured on the card itself; else an estimate from that card\n"
        f"fits: \"{fits}\"\n"
        f"calls: {m['calls']}\nturns: {m['turns']}\n"
        f"prompt_tokens_per_second: {m['read_tps']}\nanswer_tokens_per_second: {m['write_tps']}\nload_seconds: {m['load_s']}\n"
        f"median_turn_seconds: {m['median_turn_s']}\np95_turn_seconds: {m['p95_turn_s']}\nlongest_turn_seconds: {m['longest_turn_s']}\n"
        f"turns_over_budget: {len(m['over'])}\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("recording")
    ap.add_argument("--card", default="RTX 3060 12GB")
    ap.add_argument("--write", action="store_true", help="keep the speeds in data/rules/card_profile.yaml")
    ap.add_argument("--measured-on", default="", help="(f444) the card the recording was made on, when it is not --card: scale to --card")
    ap.add_argument("--vram-gb", type=float, default=0, help="(f444) what the model and its context took on the measuring card")
    a = ap.parse_args()
    folder = Path(a.recording)
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
    if a.write:
        write(m, a.card, meta.get("model", ""), folder.name, a.measured_on, fits)
        print(f"kept in {PROFILE.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
