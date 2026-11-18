"""(f719) The live gate: what a person meets first, measured on the real model and this card, in one command.

    python tools/live_gate.py             the whole gate: the reading corpus, then the played script
    python tools/live_gate.py --quick     sixty cases and the script's first fifteen lines, for before a playtest
    python tools/live_gate.py --stub      the stand-in model: measures nothing real (the test suite's)

1. Reading: the corpus (data/replay/interp_cases.yaml) through tools/interp_eval.py on the real model: the share read right, by kind.
2. A played script (data/replay/gate_script.yaml): typed lines played through the real turn from a fixed save and seed, by
   tools/nightrun.py with the script as its player. From its rows and counts:
   - inventions: of the passages checked for a creature the game does not have here (f701), those sent back, per hundred; and,
     roughly, the capitalised words inside a sentence that are no name of the run's or of the game's data, per hundred passages
     shown;
   - stiff speech: of the spoken replies checked (f714: while the turn has room), the share sent back as stiff;
   - (f723) speech: what a townsperson's reply and a companion's read (the median and the 95th percentile, in characters) and
     the share of them accepted on the first try, from the run's call log by the nights' measure (tools/latency.py); and leaks:
     of the replies to the script's lines that ask about something else (a line's `tempts`), those that say a piece of the
     town's news, a happening or a posting, counted roughly by the piece's own words; (f729) and of those marked lines, how many
     had news or a happening around them (a count that had none could only have failed on a posting), and what the reading
     before a reply reads (gate.yaml readings), apart from the speakers;
   - time: the median and the 95th percentile of seconds by the turn's shape, the lines over the limit, the stand-ins shown.
3. Held against the owner's floors (data/replay/gate.yaml). A floor that is not set is reported, not held.

The whole gate on the real model, played to its last line, writes data/measured/live_gate.yaml and a dated report under
docs/measure/. Any other run writes only to its own folder (--out). Exit code 1 when a set floor is not met, 2 when the gate
could not run or the script ended early."""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import statistics
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))
import yaml

SCRIPT = ROOT / "data" / "replay" / "gate_script.yaml"
FLOORS = ROOT / "data" / "replay" / "gate.yaml"
MEASURED = ROOT / "data" / "measured" / "live_gate.yaml"
REPORTS = ROOT / "docs" / "measure"
UNREAD = 0.1          # a reading the model failed for more than this share of its cases is no measure of reading
# a floor's name -> (where its number is in the measures, whether more is better)
HELD = {
    "reading_share": (("reading", "share"), True),
    "phantoms_per_100": (("inventions", "phantoms_per_100"), False),
    "unknown_names_per_100": (("inventions", "unknown_names_per_100"), False),
    "stiff_sent_back_share": (("speech", "stiff_sent_back_share"), False),
    "leaks": (("speech", "leaked"), False),
    "leak_lines_with_news": (("speech", "leak_lines_with_news"), True),
    "townsperson_prompt_p95_chars": (("speech", "townsperson_prompt_p95"), False),
    "first_try_share": (("speech", "first_try_share"), True),
    "p95_seconds": (("time", "p95_seconds"), False),
    "over_limit": (("time", "over_limit"), False),
    "stand_ins": (("time", "stand_ins"), False),
}


TEMPTS = ("news", "happenings", "board")       # (f723) what a script line can mark as a leak in its reply (the truth view's facets)


def floors(path: Path = FLOORS) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def floors_problems(F: dict | None = None) -> list[str]:
    """The startup check of data/replay/gate.yaml (engine/data_check.py gate_problems), for a file read here."""
    from engine import data_check
    return data_check.gate_problems(floors() if F is None else F, measured={k: {} for k in ("reading", "inventions", "speech", "time")})


def pick_cases(cases: list[dict], n: int, group) -> list[dict]:
    """n cases drawn evenly by kind, each kind's in the file's order: the same ones every run."""
    by: dict[str, list[dict]] = {}
    for c in cases:
        by.setdefault(group(c), []).append(c)
    out, depth = [], 0
    while len(out) < min(n, len(cases)):
        for kind in sorted(by):
            if depth < len(by[kind]) and len(out) < n:
                out.append(by[kind][depth])
        depth += 1
    return out


def reading(live: bool, source=None, n: int = 0) -> dict:
    """The corpus read, by the real model when live: the share right, and each kind's."""
    import interp_eval
    cases = interp_eval.load_cases()
    if n:
        cases = pick_cases(cases, n, interp_eval.group_of)
    got = interp_eval.evaluate(cases, live=live, quiet=True, source=source)
    by_kind = {k: [int(x) for x in v.split("/")] for k, v in got["by_kind"].items()}
    right = sum(r for r, _ in by_kind.values())                    # as the game is: an owed case is a wrong one
    return {"cases": got["cases"], "right": right, "share": round(right / got["cases"], 3) if got["cases"] else None,
            "by_kind": {k: {"right": r, "of": t} for k, (r, t) in by_kind.items()},
            "model_failed": got["model_failed"], "repairs": sum(got["repairs"].values()), "wrong": sorted(got["wrong"] + got["owed"])}


def load_script(path: Path = SCRIPT) -> dict:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    lines = raw.get("lines") or []
    if not lines or not all(isinstance(l, dict) and str(l.get("say") or "").strip() and str(l.get("shape") or "").strip() for l in lines):
        raise SystemExit(f"{path}: a list of lines, each with what is typed (say) and the turn's shape (shape)")
    odd = [l["say"] for l in lines if not isinstance(l.get("tempts") or [], list) or set(l.get("tempts") or []) - set(TEMPTS)]
    if odd:
        raise SystemExit(f"{path}: a line's tempts is a list from {', '.join(TEMPTS)}: {odd[0]!r}")
    return {"setup": dict(raw.get("setup") or {}), "lines": lines}


def play(script: Path, out: Path, stub: bool, lines: int = 0, attach: bool = False) -> tuple[list[dict], dict]:
    """The script played by the night run, in a process of its own: its turn rows and its run record."""
    s = load_script(script)
    setup = s["setup"]
    cmd = [sys.executable, str(ROOT / "tools" / "nightrun.py"), "--script", str(script), "--out", str(out),
           "--save", "live_gate_stub" if stub else "live_gate",     # one name: the next run clears the last one's save
           "--seed", str(setup.get("seed", 719)), "--class", str(setup.get("cls", "warrior")), "--start", str(setup.get("start", "green")),
           "--party", str(setup.get("party", 2)), "--turns", str(min(lines, len(s["lines"])) if lines else len(s["lines"]))]
    cmd += ["--stub"] if stub else []
    cmd += ["--attach"] if attach else []
    done = subprocess.run(cmd, cwd=ROOT, env={**os.environ, "PYTHONUTF8": "1"}, capture_output=stub, text=True, encoding="utf-8", errors="replace")
    if done.returncode or not (out / "run.json").exists():
        raise SystemExit(f"the script could not be played (the night run left {done.returncode}): see {out / 'errors.log'}"
                         + (("\n" + (done.stderr or "")[-600:]) if stub else ""))
    rows = [json.loads(l) for l in (out / "turns.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    info = json.loads((out / "run.json").read_text(encoding="utf-8"))
    import latency
    calls = latency.load(out / "llm_calls.jsonl")
    info["speakers"], info["readings"] = speakers(calls), readings(calls)    # (f723, f729) from the run's own call log
    return rows, info


def _p95(xs: list[float]) -> float:
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(round(0.95 * (len(xs) - 1))))] if xs else 0.0


def timing(rows: list[dict], limit: float) -> dict:
    """Seconds by the turn's shape: the script's own word for each line, and "fight" for any line played inside one."""
    by: dict[str, list[float]] = {}
    for r in rows:
        by.setdefault("fight" if r.get("combat") else str(r.get("kind") or "other"), []).append(float(r.get("seconds") or 0))
    every = [x for xs in by.values() for x in xs]
    return {"inputs": len(rows), "median_seconds": round(statistics.median(every), 1) if every else None,
            "p95_seconds": round(_p95(every), 1) if every else None,
            "by_shape": {k: {"n": len(xs), "median": round(statistics.median(xs), 1), "p95": round(_p95(xs), 1)} for k, xs in sorted(by.items())},
            "over_limit": sum(1 for x in every if x > limit), "limit_seconds": limit,
            "stand_ins": sum(len(r.get("stand_ins") or []) for r in rows), "model_failed": sum(1 for r in rows if r.get("hesitated"))}


INSIDE = re.compile(r"(?<=[a-z,;])[ \t]+([A-Z][a-z]{2,})\b")     # a capitalised word after a small letter or a comma: inside its sentence
NAME = re.compile(r"\b[A-Z][a-z]{2,}\b")


def unknown_names(told: list[str], known: set[str]) -> list[str]:
    """Roughly: the capitalised words inside a sentence that no person or place of the run is called and the game's data
    nowhere holds. A word that opens a sentence, a quotation or a line is never counted. A count to watch move, not a verdict
    on any one word."""
    return [w for p in told for w in INSIDE.findall(p) if w.lower() not in known]


def game_names(root: Path = ROOT) -> set[str]:
    """Every capitalised word the game's own data holds (the world, the rules): its places, landmarks, feasts, creatures, peoples."""
    words: set[str] = set()
    for folder in ("world", "rules"):
        for f in sorted((root / "data" / folder).rglob("*")):
            if f.is_file() and f.suffix in (".yaml", ".json"):
                words.update(w.lower() for w in NAME.findall(f.read_text(encoding="utf-8", errors="ignore")))
    return words


def known_names(info: dict, rows: list[dict], game: set[str] | None = None) -> set[str]:
    words = set(game_names() if game is None else game)

    def add(text) -> None:
        words.update(w.lower() for w in re.findall(r"[A-Za-z]+", str(text or "")))

    add(info.get("character"))
    for name in (info.get("cast") or {}):
        add(name)
    for m in info.get("party") or []:
        add(m.get("name") if isinstance(m, dict) else m)
    for r in rows:
        add(r.get("where"))
    return words


def speakers(calls: list[dict]) -> dict:
    """(f723) Each kind of speaker's replies in a call log, by the measure the nights use (tools/latency.py first_tries, f475): how
    many, the share accepted on the first try, what the prompt read. The kinds and their tasks are data (data/replay/gate.yaml)."""
    import latency
    return {kind: latency.first_tries(calls, tuple(tasks)) for kind, tasks in (floors().get("speakers") or {}).items()}


def readings(calls: list[dict]) -> dict:
    """(f729) The reading before each kind of speaker's reply (gate.yaml readings), by the same measure as a speaker's: no
    reply, so never counted among the speakers."""
    import latency
    return {kind: latency.first_tries(calls, tuple(tasks)) for kind, tasks in (floors().get("readings") or {}).items()}


def said_piece(words: str, pieces: list[str]) -> str:
    """(f723) The first of these lines of news that the words carry (npc/life.py carries: the rule a fact revealed is held to),
    or ''. Roughly: a line with fewer than two longer words in common is no match."""
    from npc import life
    spoken = set(re.findall(r"[a-z]{5,}", words.lower()))
    return next((p for p in pieces if life.carries(words, p) and len(set(re.findall(r"[a-z]{5,}", p.lower())) & spoken) >= 2), "")


def speech(rows: list[dict], info: dict, lines: list[dict] | None) -> dict:
    """(f723) What the speech work is judged by. The speaking prompt's size and the first tries, by kind of speaker: the run's
    call log by the nights' own measure (tools/latency.py first_tries). Leaks: a script line that asks about something else is
    marked with what would be a leak in its reply; the reply is the first thing said aloud in its turn (the party's talk after
    it is not it), its words alone; a marked line counts only where the town had such a piece to bring up. (f729) Of the
    marked lines that count, those with news or a happening among what they mark: with none, the count could only have failed
    on a posting. The reading before a reply is apart from the speakers; what a townsperson's reply reads in all is roughly
    its speaking and its own reading (the two medians added: the call log does not pair them)."""
    by = {k: v for k, v in (info.get("speakers") or {}).items()}
    calls = sum(v["calls"] for v in by.values() if v)
    left = [dict(l) for l in lines or []]
    answered, examples, replies, carried, near_news = 0, [], 0, 0, 0
    read_by = dict(info.get("readings") or {})
    town = by.get("townsperson") or {}
    for r in rows:
        line = next((l for l in left if str(l.get("say")) == str(r.get("text"))), None)      # by what was typed: a row is its line's
        if line is not None:
            left.remove(line)
        said = r.get("said") or []
        if not said:
            continue
        replies += 1
        who, words = said[0]
        around = r.get("around") or {}
        carried += bool(said_piece(words, [p for name in ("news", "happenings") for p in around.get(name) or []]))
        pieces = [p for name in ((line or {}).get("tempts") or []) for p in around.get(name) or []]
        if not pieces:
            continue
        answered += 1
        near_news += any(around.get(name) for name in ((line or {}).get("tempts") or []) if name != "board")
        piece = said_piece(words, pieces)
        if piece:
            examples.append({"line": r.get("n"), "typed": str(r.get("text") or "")[:120], "who": who, "said": words[:300], "piece": piece[:200]})
    return {"speakers": by, "readings": read_by, "townsperson_prompt_p95": town.get("p95"),
            "townsperson_reads_in_all_p50": (town["p50"] + ((read_by.get("townsperson") or {}).get("p50") or 0)) if town.get("p50") is not None else None,
            "leak_lines_with_news": near_news if answered else None,
            "first_try_share": round(sum(v["first_try"] * v["calls"] for v in by.values() if v) / calls, 3) if calls else None,
            "leaks": {"lines": answered, "with_news": near_news, "leaked": len(examples), "replies": replies, "carried_news": carried, "examples": examples[:12]},
            "leaked": len(examples) if answered else None, "leak_share": round(len(examples) / answered, 3) if answered else None}


def measures(read: dict, rows: list[dict], info: dict, limit: float, game: set[str] | None = None, lines: list[dict] | None = None) -> dict:
    told = [t for r in rows for t in r.get("told") or []]            # the narrator's passages as shown, one a telling
    checked = info.get("checked") or {}
    strange = unknown_names(told, known_names(info, rows, game))
    n_told, n_spoken = int(checked.get("told") or 0), int(checked.get("spoken") or 0)
    return {
        "reading": read,
        "inventions": {"passages_checked": n_told, "phantoms": int(checked.get("phantom") or 0),
                       "phantoms_per_100": round(100 * int(checked.get("phantom") or 0) / n_told, 1) if n_told else None,
                       "passages_shown": len(told), "unknown_names": len(strange),
                       "unknown_names_per_100": round(100 * len(strange) / len(told), 1) if told else None,
                       "examples": sorted(set(strange))[:12]},
        "speech": {"spoken_checked": n_spoken, "stiff": int(checked.get("stiff") or 0),
                   "stiff_sent_back_share": round(int(checked.get("stiff") or 0) / n_spoken, 3) if n_spoken else None,
                   **speech(rows, info, lines)},
        "time": timing(rows, limit),
    }


def held(m: dict, F: dict) -> list[str]:
    """Each set floor the measures do not meet, in a line. A set floor with nothing measured under it is not met."""
    bad = []
    for name, ((part, key), more_is_better) in HELD.items():
        floor, got = (F.get("floors") or {}).get(name), (m.get(part) or {}).get(key)
        if floor is None:
            continue
        if got is None:
            bad.append(f"{name}: not measured, against the floor {floor}")
        elif (got < floor) if more_is_better else (got > floor):
            bad.append(f"{name}: {got} against the floor {floor}")
    return bad


def ended_early(script_lines: int, wanted: int, rows: list[dict], info: dict) -> str:
    """Why the played script is not all of what was asked of it, or ''."""
    want = min(wanted, script_lines) if wanted else script_lines
    if len(rows) < want or not str(info.get("reason") or "").startswith("turn limit"):
        return f"{len(rows)} of {want} lines played ({info.get('reason') or 'no reason given'})"
    return ""


def partial(a, read: dict) -> list[str]:
    """Why this run, though played to its end, is not the whole gate on the real model: each reason in a few words."""
    why = [name for name, on in (("the stand-in model", a.stub), ("--quick", a.quick), ("--cases", a.cases), ("--lines", a.lines),
                                 ("--no-reading", a.no_reading), ("another script", Path(a.script).resolve() != SCRIPT.resolve())) if on]
    if read["cases"] and read["model_failed"] > UNREAD * read["cases"]:
        why.append(f"the model failed {read['model_failed']} of {read['cases']} readings")
    return why


def report(m: dict, bad: list[str], F: dict, about: dict) -> str:
    r, inv, sp, t = m["reading"], m["inventions"], m["speech"], m["time"]

    def show(v):
        return "not measured" if v is None else f"{v:g}" if isinstance(v, (int, float)) else str(v)

    def floor(name):
        v = (F.get("floors") or {}).get(name)
        return "not set" if v is None else f"{v:g}"

    out = [f"# The live gate, {about['date']}", "",
           f"{about['mode']}; model {about['model']}; {t['inputs']} lines played; {r['cases']} reading cases.", "",
           "## Against the floors", "",
           "| Measure | Now | Floor |", "|---|---|---|",
           f"| Lines read right (share) | {show(r['share'])} | {floor('reading_share')} |",
           f"| Passages sent back for a creature not there, per 100 checked | {show(inv['phantoms_per_100'])} | {floor('phantoms_per_100')} |",
           f"| Names the game does not hold, per 100 passages shown (rough) | {show(inv['unknown_names_per_100'])} | {floor('unknown_names_per_100')} |",
           f"| Spoken replies sent back as stiff (share of those checked) | {show(sp['stiff_sent_back_share'])} | {floor('stiff_sent_back_share')} |",
           f"| Leaks: replies that said news to a line that asked about something else | {show(sp.get('leaked'))} | {floor('leaks')} |",
           f"| Marked lines answered where the town had news or a happening, at least | {show(sp.get('leak_lines_with_news'))} | {floor('leak_lines_with_news')} |",
           f"| What a townsperson's reply reads, 95th percentile, characters | {show(sp.get('townsperson_prompt_p95'))} | {floor('townsperson_prompt_p95_chars')} |",
           f"| Spoken replies accepted on the first try (share) | {show(sp.get('first_try_share'))} | {floor('first_try_share')} |",
           f"| Seconds a turn, 95th percentile | {show(t['p95_seconds'])} | {floor('p95_seconds')} |",
           f"| Lines over {t['limit_seconds']:g} s | {show(t['over_limit'])} | {floor('over_limit')} |",
           f"| Stand-ins shown | {show(t['stand_ins'])} | {floor('stand_ins')} |", "",
           ("Under a floor: " + "; ".join(bad) + ".") if bad else "No set floor is missed." if any(v is not None for v in (F.get("floors") or {}).values())
           else "No floor is set yet: this run is a baseline.", "",
           "## Reading, by kind", "", "| Kind | Right | Of |", "|---|---|---|"]
    out += [f"| {k} | {v['right']} | {v['of']} |" for k, v in sorted(r["by_kind"].items())]
    out += ["", f"The model gave no usable reading for {r['model_failed']} cases; repairs fired {r['repairs']} times.", "",
            "## Time, by the turn's shape", "", "| Shape | Lines | Median s | 95th s |", "|---|---|---|---|"]
    out += [f"| {k} | {v['n']} | {v['median']:g} | {v['p95']:g} |" for k, v in t["by_shape"].items()]
    out += ["", f"All lines: median {show(t['median_seconds'])} s. The model failed {t['model_failed']} lines.", "",
            "## Inventions and speech", "",
            f"{inv['passages_checked']} passages were checked for a creature the game does not have there; {inv['phantoms']} were sent back once.",
            f"{inv['passages_shown']} passages were shown; in them, {inv['unknown_names']} capitalised words that are no name of the run's or of the game's data"
            + (f" ({', '.join(inv['examples'])})." if inv["examples"] else "."),
            f"{sp['spoken_checked']} spoken replies were checked for stiffness (a reply is checked while its turn has room for another try); "
            f"{sp['stiff']} were sent back once.", ""]
    if sp.get("leaks") is not None:
        lk = sp["leaks"]
        out += ["## The speaking prompt, first tries and leaks", "", "| Speaker | Replies asked for | Prompt, median chars | Prompt, 95th chars | Accepted on the first try |",
                "|---|---|---|---|---|"]
        for kind, v in sp["speakers"].items():
            v = v or {}
            out.append(f"| {kind} | {show(v.get('calls'))} | {show(v.get('p50'))} | {show(v.get('p95'))} | {show(v.get('first_try'))} |")
        for kind, v in (sp.get("readings") or {}).items():           # (f729) no speaker: its own rows, under theirs
            v = v or {}
            out.append(f"| the reading before a {kind}'s reply | {show(v.get('calls'))} | {show(v.get('p50'))} | {show(v.get('p95'))} | {show(v.get('first_try'))} |")
        if sp.get("townsperson_reads_in_all_p50") is not None:
            out += ["", f"A townsperson's reply reads roughly {sp['townsperson_reads_in_all_p50']} characters in all: the median of its speaking and of the reading "
                    "before it, added."]
        out += ["", f"{lk['lines']} of the script's lines that ask about something else were answered aloud where the town had something to bring up; "
                f"{lk['leaked']} of those replies said a piece of its news, a happening or a posting the line did not ask for (counted by the piece's "
                "own words: a rough count, each one below to be read).",
                (f"{lk.get('with_news', 0)} of those lines had news or a happening around them among what they mark; the rest had only postings."
                 if lk.get("with_news") else "None of those lines had news or a happening around it: this count could only have failed on a posting.")
                if lk["lines"] else "No marked line was answered aloud where the town had anything to bring up: the leaks are not measured.",
                f"Of all {lk['replies']} turns with a spoken reply, {lk['carried_news']} carried a piece of the town's news or a happening, asked for or not."]
        out += [f"- line {x['line']} ({x['typed']}): {x['who']} said \"{x['said']}\" against \"{x['piece']}\"" for x in lk["examples"]] + [""]
    return "\n".join(out)


def keep(text: str, m: dict, under: list[str], about: dict, measured: Path = MEASURED, reports: Path = REPORTS) -> None:
    """The whole gate's run, kept: the measures where the startup check and the next run find them, and the dated report."""
    header = ("# (f719) The live gate's last whole run on the real model (tools/live_gate.py). A measurement: outside the data hash.\n"
              "# Do not hand-edit; run the gate again.\n")
    measured.write_text(header + yaml.safe_dump({"measured": about["date"], "model": about["model"], **m, "under": under},
                                                sort_keys=False, allow_unicode=True, width=140), encoding="utf-8", newline="\n")
    (reports / f"{about['date']}_live_gate.md").write_text(text, encoding="utf-8", newline="\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--quick", action="store_true", help="the quick gate: fewer cases and lines (data/replay/gate.yaml quick); writes only to --out")
    ap.add_argument("--stub", action="store_true", help="the stand-in model (the test suite's): measures nothing real")
    ap.add_argument("--script", default=str(SCRIPT), help="the script of typed lines (default data/replay/gate_script.yaml)")
    ap.add_argument("--out", default="", help="where this run's files go (default logs/live_gate/<when>)")
    ap.add_argument("--cases", type=int, default=0, help="read this many cases, drawn evenly by kind (default: all, or the quick run's)")
    ap.add_argument("--lines", type=int, default=0, help="play this many of the script's lines (default: all, or the quick run's)")
    ap.add_argument("--no-reading", action="store_true", help="leave the corpus out: the played script alone")
    import runtime_cli
    runtime_cli.add_args(ap)
    a = ap.parse_args(argv)
    F = floors()
    bad = floors_problems(F)
    if bad:
        print("data/replay/gate.yaml has problems:\n" + "\n".join(f"  - {p}" for p in bad))
        return 2
    if not Path(a.script).exists():
        print(f"no script at {a.script}: the gate's typed lines are the owner's to read first, and are not kept yet")
        return 2
    when = datetime.datetime.now()
    out = Path(a.out) if a.out else ROOT / "logs" / "live_gate" / when.strftime("%Y%m%d_%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    n_cases = a.cases or (F["quick"]["cases"] if a.quick else 0)
    n_lines = a.lines or (F["quick"]["lines"] if a.quick else 0)
    import config
    from engine import budget
    limit = float(budget.B["limit_seconds"])

    read = {"cases": 0, "right": 0, "share": None, "by_kind": {}, "model_failed": 0, "repairs": 0, "wrong": []}
    if not a.no_reading:
        server = None if a.stub else runtime_cli.load(a, out=out / "reading", say=lambda m_: print(m_, flush=True))
        try:
            read = reading(live=not a.stub, source=getattr(server, "source", None), n=n_cases)
        finally:
            if server is not None:
                server.close()                                    # the played script starts its own
        print(f"reading: {read['right']} of {read['cases']} right ({read['share']})", flush=True)
    rows, info = play(Path(a.script), out / "play", a.stub, n_lines, attach=bool(getattr(a, "attach", False)))
    early = ended_early(len(load_script(Path(a.script))["lines"]), n_lines, rows, info)
    m = measures(read, rows, info, limit, lines=load_script(Path(a.script))["lines"])
    under = held(m, F)
    why = partial(a, read)
    about = {"date": when.strftime("%Y-%m-%d"), "model": config.MODEL,
             "mode": f"the script ended early, {early}: no measure" if early else "the stand-in model: nothing here is a measure" if a.stub
             else "the whole gate" if not why else "a part of the gate (" + ", ".join(why) + ")"}
    text = report(m, under, F, about)
    (out / "live_gate.md").write_text(text, encoding="utf-8", newline="\n")
    (out / "live_gate.json").write_text(json.dumps({"about": about, **m, "under": under}, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    if not early and not why:
        keep(text, m, under, about)
    print(text)
    print(f"files: {out}")
    return 2 if early else 1 if under else 0


if __name__ == "__main__":
    sys.exit(main())
