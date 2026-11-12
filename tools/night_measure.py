"""(f602) Two questions phase 2's pod session asks of a night that the other readers do not answer (docs/design/14_phase2_plan.md, the
pod session), read from the run folders a night writes (tools/nightrun.py):

1. The two slots (f536: the understanding alone on its own slot, every other call on the shared one, data/runtime/server.yaml slot_of).
   Does the understanding's cached prompt hold from turn to turn? Its first try each turn held when the server had at least half its
   prompt cached (the system message, the same from one turn to the next, is most of it; the character share of the system message is
   shown beside, as a proxy that runs high), with the spread of the cached share; the server's own log, by slot, says how often it restored
   a checkpoint and how often it read a prompt whole. Does a background call on the shared slot make the turn wait? While one holds the
   shared slot, a turn's call bound for it takes the understanding's slot instead (llm/llama.py _machine_for_call): such a moved call
   costs the next understanding a re-read rather than a queue. Read here: the calls the understanding's slot took beyond its own (from
   the log, when it kept the night's start), and the waits beyond the server's own work (llm/llama.py wait_ms) of the turn's own calls
   (a call's lane and slot as logged, when the call log carries them) on turns with background calls beside turns without.
2. Births and situation rulings a game day: the calls of a situation's parts (situation_parts), of a situation's ruling (event_judge)
   and of an act's (act_ruling), within the turns' clock, their seconds on the card the night ran on and on the minimum card, scaled as
   tools/card_profile.py scales (data/rules/cards.yaml: compute for reading, bandwidth for writing; an estimate, and said so), and the
   situations born, by tier, by who made them and how many were within a character's reach when born (f599).

    python tools/night_measure.py RUN_DIR... [--measured-on "RTX 4090"] [--card "RTX 3060 12GB"]

The card a night ran on is read from its run.json (server.device, by cards.yaml patterns) when --measured-on is not given."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools import card_profile

TASKS = ("situation_parts", "event_judge", "act_ruling")
MARKS = {"prompts": "new prompt", "restored": "restored context checkpoint", "whole": "forcing full prompt re-processing"}
SLOT_LINE = re.compile(r"\bid\s+(\d+) \| task -?\d+ \| (.*)")
STARTED = "load_tensors"                               # (f602) the server's first lines: a log that keeps them kept the whole night
WAITED_MS = 1000                                       # (f602) a wait the player would feel: a second beyond the server's own work
HELD = 0.5                                             # (f602) a cache that held: half the prompt or more cached
SHORT_DAYS = 1.0                                       # (f602) under a game day, a day's rate is an extrapolation, and said so


class Run:
    def __init__(self, folder: Path):
        self.folder = folder
        self.calls = _jsonl(folder / "llm_calls.jsonl")
        self.turns = _jsonl(folder / "turns.jsonl")
        self.pulse = _jsonl(folder / "pulse.jsonl")
        meta = folder / "run.json"
        self.meta = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        self.slot_of, self.other, self.slots_from = _slots_of(folder)
        self.log, self.rotated = [], (folder / "llama-server.log.1").exists()
        for name in ("llama-server.log.1", "llama-server.log"):          # the older file first: the log rotates
            p = folder / name
            if p.exists():
                self.log += p.read_text(encoding="utf-8", errors="replace").splitlines()
        self.whole_log = any(STARTED in line for line in self.log[:400])

    def slot(self, c: dict) -> int:
        t = c.get("tokens") or {}
        return int(t["slot"]) if isinstance(t.get("slot"), int) else self.slot_of.get(c.get("task", ""), self.other)


def _slots_of(folder: Path) -> tuple[dict, int, str]:
    """(f602) The run's task-to-slot map: its run/server.json while the server ran (a finished night removes it), else the game's own
    data/runtime/server.yaml; empty when neither says."""
    server = folder / "run" / "server.json"
    if server.exists():
        s = json.loads(server.read_text(encoding="utf-8"))
        return {str(k): int(v) for k, v in (s.get("slot_of") or {}).items()}, int(s.get("other_slot") or 0), "run/server.json"
    p = ROOT / "data" / "runtime" / "server.yaml"
    if p.exists():
        import yaml
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        s = cfg.get("server") if isinstance(cfg.get("server"), dict) else cfg
        if isinstance(s.get("slot_of"), dict):
            return {str(k): int(v) for k, v in s["slot_of"].items()}, int(s.get("other_slot") or 0), "data/runtime/server.yaml"
    return {}, 0, ""


def _jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    out = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue                                   # a line cut short when the night was stopped
    return out


def load(folder) -> Run:
    return Run(Path(folder))


def _p(xs: list[float], q: float) -> float | None:
    if not xs:
        return None
    xs = sorted(xs)
    if q == 0.5:
        return round(statistics.median(xs), 2)
    return round(xs[min(len(xs) - 1, int(q * len(xs)))], 2)


def _share(c: dict) -> float:
    t = c.get("tokens") or {}
    return int(t.get("cached") or 0) / int(t["prompt"]) if t.get("prompt") else 0.0


def _system_share(c: dict) -> float | None:
    system = sum(int(s[2]) for s in c.get("sizes") or [] if isinstance(s, list) and len(s) == 3 and s[0] == "system")
    return system / int(c["chars"]) if c.get("chars") and system else None


def played(run: Run) -> list[dict]:
    """The turns the night played to the end: timed, neither hesitated nor broken by an error."""
    return [t for t in run.turns if isinstance(t.get("seconds"), (int, float)) and not t.get("hesitated") and not t.get("error")]


def slots(run: Run) -> dict:
    """(1) The understanding's slot: the first try of each turn after the first, how many held their cache; the server's log by slot;
    the calls the understanding's slot took beyond its own; the turn's own calls' waits on turns with background calls and without."""
    mine = [t for t, s in run.slot_of.items() if s != run.other]
    u_slot = run.slot_of[mine[0]] if mine else None
    tried = [c for c in run.calls if c.get("task") in mine and (c.get("tokens") or {}).get("prompt")]
    first, seen = [], set()
    for c in tried:
        if int(c.get("attempt") or 0) == 0 and c.get("turn") not in seen:
            seen.add(c.get("turn"))
            first.append(c)
    after = first[1:]
    shares = [_share(c) for c in after]
    systems = [x for x in (_system_share(c) for c in after) if x is not None]
    log: dict[int, dict] = {}
    for line in run.log:
        m = SLOT_LINE.search(line)
        if not m:
            continue
        row = log.setdefault(int(m.group(1)), dict.fromkeys(MARKS, 0))
        for k, mark in MARKS.items():
            if m.group(2).startswith(mark):
                row[k] += 1
    moved, moved_from = None, ""
    if u_slot is not None and any(isinstance((c.get("tokens") or {}).get("slot"), int) for c in run.calls):
        moved, moved_from = sum(1 for c in run.calls if (c.get("tokens") or {}).get("slot") == u_slot and c.get("task") not in mine), "the call log"
    elif u_slot is not None and run.whole_log and u_slot in log:
        moved, moved_from = max(0, log[u_slot]["prompts"] - len(tried)), "the server's log"   # every try is a prompt begun on its slot
    lanes = any("lane" in (c.get("tokens") or {}) for c in run.calls)
    background = {t.get("turn") for t in played(run) if int(t.get("background_calls") or 0) > 0}
    split = {}
    for name, rows in (("with", [t for t in played(run) if t.get("turn") in background]),
                       ("without", [t for t in played(run) if t.get("turn") not in background])):
        turns = {t.get("turn") for t in rows}
        own = [c for c in run.calls if c.get("turn") in turns and c.get("tokens")
               and (not lanes or (c.get("tokens") or {}).get("lane") != "background")]
        ws = [int(c["tokens"].get("wait_ms") or 0) for c in own]
        fw = [float(t["first_word"]) for t in rows if isinstance(t.get("first_word"), (int, float))]
        split[name] = {"turns": len(rows), "calls": len(ws), "wait_p50_ms": _p(ws, 0.5), "wait_p90_ms": _p(ws, 0.9), "most_ms": max(ws, default=0),
                       "over_1s": sum(1 for w in ws if w > WAITED_MS), "first_word_p50": _p(fw, 0.5), "first_word_p90": _p(fw, 0.9)}
    return {"understanding": {"slot": u_slot, "tasks": sorted(mine), "turns": len(first), "held": sum(1 for x in shares if x >= HELD),
                              "of": len(after), "share_p10": _p(shares, 0.1), "share_p50": _p(shares, 0.5), "share_p90": _p(shares, 0.9),
                              "system_p50": _p(systems, 0.5)},
            "map_from": run.slots_from, "log": log, "log_lines": len(run.log), "rotated": run.rotated, "whole_log": run.whole_log,
            "moved": moved, "moved_from": moved_from, "lanes": lanes, "split": split}


def card_of(run: Run) -> str:
    """(f602) The card a night ran on, by its run.json's device and data/rules/cards.yaml's patterns; '' when it does not say."""
    import yaml
    device = str(((run.meta.get("server") or {}).get("device")) or "")
    pats = (yaml.safe_load((ROOT / "data" / "rules" / "cards.yaml").read_text(encoding="utf-8")) or {}).get("patterns") or {}
    return next((name for name, pat in pats.items() if device and re.search(pat, device)), "")


def factors(measured_on: str, card: str) -> tuple[float, float]:
    """How many times longer the target card takes to read and to write: card_profile's own scaling (compute, bandwidth)."""
    cs = card_profile.cards()
    for c in (measured_on, card):
        if c not in cs:
            raise SystemExit(f"{c!r} is no card data/rules/cards.yaml knows: {', '.join(cs)}")
    src, dst = cs[measured_on], cs[card]
    return src["tflops"] / dst["tflops"], src["bandwidth_gbs"] / dst["bandwidth_gbs"]


def per_day(run: Run, read: float = 1.0, write: float = 1.0) -> dict:
    """(2) Game days from the played turns' clock; each situation task's calls (every attempt) made within those turns and their seconds,
    measured and on the target, a day; the situations born within that clock, by tier, by who made them and within reach. A note on the
    world's pulse is no birth: a birth carries its tier, a cataclysm its own mark."""
    rows = [t for t in played(run) if isinstance(t.get("state"), dict) and isinstance(t["state"].get("minutes"), int)]
    mins = [int(t["state"]["minutes"]) for t in rows]
    lo, hi = (min(mins), max(mins)) if mins else (0, 0)
    days = round((hi - lo) / 1440, 2)
    turns = {t.get("turn") for t in rows}
    tasks = {}
    for task in TASKS:
        cs = [c for c in run.calls if c.get("task") == task and c.get("turn") in turns]
        secs = sum(float(c.get("seconds") or 0) for c in cs)
        target = sum(float(card_profile.scaled({"usage": c.get("tokens") or {}, "seconds": c.get("seconds")}, read, write)["seconds"] or 0)
                     for c in cs)
        tasks[task] = {"calls": len(cs), "seconds": round(secs, 1), "target_seconds": round(target, 1),
                       "per_day": round(len(cs) / days, 2) if days else None,
                       "target_seconds_per_day": round(target / days, 1) if days else None}
    born = []
    for p in run.pulse:
        if p.get("kind") != "thread" or not (lo <= int(p.get("t") or 0) <= hi):
            continue
        if p.get("tier"):
            born.append(p)
        elif str(p.get("text", "")).startswith("[cataclysm:"):
            born.append({**p, "tier": "cataclysm"})
    tiers, made = {}, {}
    for p in born:
        tiers[p["tier"]] = tiers.get(p["tier"], 0) + 1
        made[p.get("made_by") or "?"] = made.get(p.get("made_by") or "?", 0) + 1
    reach = [p for p in born if "reach" in p]
    return {"days": days, "short": days < SHORT_DAYS, "tasks": tasks,
            "births": {"all": len(born), "per_day": round(len(born) / days, 2) if days else None, "tiers": dict(sorted(tiers.items())),
                       "made_by": dict(sorted(made.items())), "in_reach": sum(1 for p in reach if p["reach"]), "reach_of": len(reach)}}


def _ms(v) -> str:
    return "-" if v is None else f"{v / 1000:.1f}s"


def _section(name: str, s: dict, d: dict, measured_on: str, card: str) -> list[str]:
    u, b = s["understanding"], d["births"]
    est = "" if measured_on == card else ", an estimate"
    out = [f"## {name}", "", "### The two slots", ""]
    if u["slot"] is None:
        out += ["The run says nothing of its slots (no run/server.json and no data/runtime/server.yaml slot_of): not read.", ""]
    else:
        out += [f"The understanding ({', '.join(u['tasks'])}) on slot {u['slot']} (the map from {s['map_from']}): {u['turns']} turns; its "
                f"first try held the cache on {u['held']} of the {u['of']} after the first (half the prompt or more cached). The share "
                f"cached: p10 {u['share_p10']}, p50 {u['share_p50']}, p90 {u['share_p90']} (the system message's share of the characters, "
                f"p50 {u['system_p50']}, runs high as a share of tokens).", ""]
    out += ["| Slot | New prompts | Checkpoint restored | Read whole |", "| --- | ---: | ---: | ---: |"]
    out += [f"| {k} | {v['prompts']} | {v['restored']} | {v['whole']} |" for k, v in sorted(s["log"].items())]
    kept = ("the whole night" if s["whole_log"] else "the night's end only (the start was rotated away)") if s["log_lines"] else "nothing"
    out += ["", f"The server's log kept {kept}: {s['log_lines']} lines" + (", in two files" if s["rotated"] else "") + "."]
    out += [f"Calls the understanding's slot took beyond its own (moved there while a background call held the shared slot): {s['moved']} "
            f"(from {s['moved_from']})." if s["moved"] is not None else
            "Calls moved to the understanding's slot: not read (no call logged its slot, and the log did not keep the night's start)."]
    out += ["", "The turn's own calls' wait beyond the server's work" + ("" if s["lanes"] else
            " (the call log does not say a call's lane, so a background call made on the turn's number counts here too)") + ":", "",
            "| Turns | Count | Calls | Wait p50 | p90 | Longest | Over 1 s | First word p50 | p90 |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    out += [f"| {k} background calls | {r['turns']} | {r['calls']} | {_ms(r['wait_p50_ms'])} | {_ms(r['wait_p90_ms'])} | {_ms(r['most_ms'])} | "
            f"{r['over_1s']} | {r['first_word_p50']} | {r['first_word_p90']} |" for k, r in s["split"].items()]
    out += ["", "(a turn counts background calls that finished within it: the long turns, and those that met new people, have more; the "
            "split is a pointer, not a cause)", "", "### Births and situation rulings a game day", "",
            f"{d['days']} game days played" + (" (under a day: a day's rate is an extrapolation)" if d["short"] else "") + ".", "",
            f"| Task | Calls | A day | Seconds ({measured_on}) | Seconds ({card}{est}) | On the {card} a day{est} |",
            "| --- | ---: | ---: | ---: | ---: | ---: |"]
    out += [f"| {k} | {v['calls']} | {v['per_day']} | {v['seconds']} | {v['target_seconds']} | {v['target_seconds_per_day']} |"
            for k, v in d["tasks"].items()]
    out += ["", f"Situations born: {b['all']} ({b['per_day']} a day); by tier {b['tiers']}; made by {b['made_by']}; within a character's "
            f"reach when born: {b['in_reach']} of {b['reach_of']}.", ""]
    return out


def report(folders: list[Path], measured_on: str, card: str) -> str:
    runs = [load(f) for f in folders]
    if not measured_on:
        found = {card_of(r) for r in runs}
        if len(found) != 1 or "" in found:
            raise SystemExit("the card the night ran on: give --measured-on (its run.json does not say, or the runs differ)")
        measured_on = found.pop()
    read, write = factors(measured_on, card) if measured_on != card else (1.0, 1.0)
    out = [f"# A night's slots and situations (tools/night_measure.py, f602)", "",
           f"Measured on the {measured_on}; seconds on the {card} are an estimate from it (reading x{read:.2f}, writing x{write:.2f}; "
           f"data/rules/cards.yaml)." if measured_on != card else f"Measured on the {card} itself.", ""]
    pooled = {"days": 0.0, "births": 0, "tasks": {t: [0, 0.0] for t in TASKS}}
    for run in runs:
        s, d = slots(run), per_day(run, read, write)
        out += _section(run.folder.name, s, d, measured_on, card)
        pooled["days"] += d["days"]
        pooled["births"] += d["births"]["all"]
        for t, v in d["tasks"].items():
            pooled["tasks"][t][0] += v["calls"]
            pooled["tasks"][t][1] += v["target_seconds"]
    if len(runs) > 1 and pooled["days"]:
        days = pooled["days"]
        out += ["## The night, pooled", "", f"{round(days, 2)} game days over {len(runs)} runs; situations born {round(pooled['births'] / days, 2)} a "
                f"day; on the {card}" + ("" if measured_on == card else " (an estimate)") + ", a day: "
                + "; ".join(f"{t} {round(c / days, 2)} calls, {round(sec / days, 1)} s" for t, (c, sec) in pooled["tasks"].items()) + ".", ""]
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("runs", nargs="+")
    ap.add_argument("--measured-on", default="", help="the card the night ran on (data/rules/cards.yaml); else read from each run.json")
    ap.add_argument("--card", default="RTX 3060 12GB", help="the card to price on (the minimum card)")
    a = ap.parse_args()
    print(report([Path(r) for r in a.runs], a.measured_on, a.card))
    return 0


if __name__ == "__main__":
    sys.exit(main())
