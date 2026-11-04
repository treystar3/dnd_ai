"""What the model's calls and the game's turns cost, from the logs.

    python tools/latency.py RUN_DIR                    a night run's folder (tools/nightrun.py): calls and turns, written to RUN_DIR/summary.md
    python tools/latency.py --calls logs/llm_calls.jsonl   any call log on its own (a real session's, for instance)
    python tools/latency.py --baseline RUN_DIR...          (f475) a night's speech-task sizes, first tries and continuity counts, as YAML
    python tools/latency.py --against RUN_DIR...           (f490) a night's speech tasks beside Bundle D's baseline and their ceilings
    python tools/latency.py --gate                         (f490) the goldens priced at expected answers against their pre-D prices;
                                                           (f510) fight inputs too, and every input under budget.yaml limit_seconds
    python tools/latency.py --fights                       (f510) the goldens' fight measures, to data/measured/bundle_e_fights.yaml
    python tools/latency.py --ceilings [RUN_DIR...]        (f490) each speech task's ceiling, from the night's p95 and the goldens
    python tools/latency.py --estimates RECORDING          (f490) a recording's inputs priced at expected answers, as the baseline keeps them

The call log carries one row per attempt: its task, its wall seconds and, since the gateway began keeping them, Ollama's own
counts (`tokens`: prompt and written tokens, the milliseconds each took, a model load). A night run adds turns.jsonl, one row per
typed line with its wall time, the time to its first word, and the calls it took.
"""
from __future__ import annotations

import collections
import json
import re
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def load(path: Path) -> list[dict]:
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass
    return rows


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    vs = sorted(values)
    return vs[min(len(vs) - 1, int(round(q * (len(vs) - 1))))]


def fmt(x: float, places: int = 1) -> str:
    return f"{x:.{places}f}"


def calls_table(rows: list[dict]) -> list[str]:
    """Per task: calls, how many needed a retry, seconds per attempt, tokens, speeds, loads. Sorted by the time spent."""
    by: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        by[r.get("task", "?")].append(r)
    lines = ["| Task | Calls | Retried | Rejected | Seconds p50 | p90 | Prompt tokens | Written | Read tok/s | Write tok/s | Loads | Total s |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    table = []
    for task, rs in by.items():
        calls = sum(1 for r in rs if r.get("attempt", 0) == 0) or len(rs)
        retried = sum(1 for r in rs if r.get("attempt", 0) > 0)
        rejected = sum(1 for r in rs if r.get("error"))
        secs = [float(r.get("seconds") or 0) for r in rs]
        toks = [r["tokens"] for r in rs if isinstance(r.get("tokens"), dict)]
        prompt = [t.get("prompt", 0) for t in toks]
        out = [t.get("out", 0) for t in toks]
        read_s = sum(t.get("read_ms", 0) for t in toks) / 1000
        write_s = sum(t.get("write_ms", 0) for t in toks) / 1000
        loads = sum(1 for t in toks if t.get("load_ms", 0) > 500)
        table.append((sum(secs), f"| {task} | {calls} | {retried} | {rejected} | {fmt(pct(secs, .5))} | {fmt(pct(secs, .9))} | "
                      f"{int(statistics.median(prompt)) if prompt else '-'} | {int(statistics.median(out)) if out else '-'} | "
                      f"{fmt(sum(prompt) / read_s, 0) if read_s else '-'} | {fmt(sum(out) / write_s, 1) if write_s else '-'} | {loads} | {fmt(sum(secs), 0)} |"))
    table.sort(key=lambda t: -t[0])
    lines += [t[1] for t in table]
    total = sum(float(r.get("seconds") or 0) for r in rows)
    lines.append(f"\n{len(rows)} attempts for {sum(1 for r in rows if r.get('attempt', 0) == 0)} calls, {fmt(total / 60, 1)} minutes in the model in all.")
    if not any(isinstance(r.get("tokens"), dict) for r in rows):
        lines.append("No token counts in this log: it was written before the gateway kept Ollama's counts, or by a stand-in model.")
    return lines


# (f475) The speech tasks Bundle D's briefs change, measured before they change (GOALS.md S7: prompt ceilings measured first). The list is
# the baseline's own (data/measured/bundle_d_baseline.yaml speech_tasks), read when it is there.
SPEECH = ("npc_conversation", "npc_parting", "npc_profile", "dialogue_frame", "work_offer_read", "hire_chat", "canon_extract", "canon_check",
          "exchange", "overheard", "mentor_chat")
BASELINE = Path(__file__).resolve().parent.parent / "data" / "measured" / "bundle_d_baseline.yaml"


def speech_tasks() -> tuple[str, ...]:
    try:
        import yaml
        got = (yaml.safe_load(BASELINE.read_text(encoding="utf-8")) or {}).get("speech_tasks")
        return tuple(got) if got else SPEECH
    except Exception:
        return SPEECH


def prompt_chars(row: dict) -> int | None:
    """(f475) What one attempt read, in characters: the gateway's own count since f475, else the messages as logged (a night logs them
    whole); None when the log shortened the system prompt and the true size cannot be known."""
    if isinstance(row.get("chars"), int):
        return row["chars"]
    msgs = row.get("messages") or []
    if any("[...shortened in log]" in str(m.get("content") or "") for m in msgs):
        return None
    return sum(len(str(m.get("content") or "")) for m in msgs[:2]) or None


def speech_measures(calls: list[dict]) -> dict:
    """(f475) Per speech task: calls, prompt characters (p50, p95, most) at the first try, the tail's p50 when logged, first-try
    acceptance (first tries with no error, of all first tries), and the share of prompt tokens the server had cached, when it said."""
    out = {}
    for task in speech_tasks():
        first = [r for r in calls if r.get("task") == task and int(r.get("attempt", 0) or 0) == 0]
        if not first:
            continue
        sizes = [c for c in (prompt_chars(r) for r in first) if c is not None]
        tails = [r["tail_chars"] for r in first if isinstance(r.get("tail_chars"), int)]
        toks = [r["tokens"] for r in first if isinstance(r.get("tokens"), dict) and isinstance(r["tokens"].get("cached"), int)]
        out[task] = {"calls": len(first), "first_try": round(sum(1 for r in first if not r.get("error")) / len(first), 3),
                     "p50": int(pct(sizes, .5)) if sizes else None, "p95": int(pct(sizes, .95)) if sizes else None,
                     "max": max(sizes) if sizes else None, "tail_p50": int(pct(tails, .5)) if tails else None,
                     "cached": round(sum(t["cached"] for t in toks) / max(1, sum(t.get("prompt", 0) for t in toks)), 3) if toks else None}
    return out


def speech_table(calls: list[dict]) -> list[str]:
    """(f475) The speech tasks' prompt sizes and first-try acceptance, for summary.md."""
    m = speech_measures(calls)
    if not m:
        return ["No speech calls on this night."]
    lines = ["| Speech task | Calls | First try accepted | Prompt chars p50 | p95 | Most | Tail p50 | Cached |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for task, r in m.items():
        cell = lambda v: "-" if v is None else str(v)
        lines.append(f"| {task} | {r['calls']} | {round(100 * r['first_try'])}% | {cell(r['p50'])} | {cell(r['p95'])} | {cell(r['max'])} | "
                     f"{cell(r['tail_p50'])} | {'-' if r['cached'] is None else str(round(100 * r['cached'])) + '%'} |")
    return lines


# (f490) Bundle D's closing: the night's speech tasks beside the baseline's, each task's prompt ceiling (data/measured/prompt_ceilings.yaml,
# reported and never enforced: GOALS.md S7), and the goldens priced with every answer at its expected size against their pre-D prices.
CEILINGS = Path(__file__).resolve().parent.parent / "data" / "measured" / "prompt_ceilings.yaml"
GOLDENS = Path(__file__).resolve().parent.parent / "data" / "replay" / "sessions"


def _yaml(path: Path) -> dict:
    try:
        import yaml
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def ceilings() -> dict:
    """(f490) Per speech task, its prompt ceiling in characters, and the closing's marks."""
    return _yaml(CEILINGS)


def against(calls: list[dict], base: dict | None = None, ceil: dict | None = None) -> list[str]:
    """(f490) The speech tasks on this night beside the baseline's: calls, first-try acceptance and its move in points, the prompt's p95
    beside the baseline's and the task's ceiling, the most, and the share of prompt tokens the server had cached. Then the closing's
    size and acceptance marks, each said as held or not (the bundle's other marks are read from the page and the blind reading)."""
    base = _yaml(BASELINE) if base is None else base
    ceil = ceilings() if ceil is None else ceil
    marks = ceil.get("closing") or {}
    was = base.get("tasks") or {}
    tops = {t: (v or {}).get("chars") for t, v in (ceil.get("ceilings") or {}).items()}
    m = speech_measures(calls)
    if not m:
        return ["No speech calls on this night."]
    cell = lambda v: "-" if v is None else str(v)
    lines = ["| Speech task | Calls | First try | Before | Points | Prompt p95 | Before | Ceiling | Most | Cached |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    dearer, over, fell = [], [], []
    for task, r in m.items():
        b = was.get(task) or {}
        moved = None if b.get("first_try") is None else round(100 * (r["first_try"] - b["first_try"]))
        if r["p95"] is not None and b.get("p95") is not None and r["p95"] > b["p95"]:
            dearer.append(task)
        if r["p95"] is not None and tops.get(task) and r["p95"] > tops[task]:
            over.append(task)
        if task in (marks.get("first_try_tasks") or []) and moved is not None and moved < -int(marks.get("first_try_points", 5)):
            fell.append(f"{task} {moved:+d}")
        lines.append(f"| {task} | {r['calls']} | {round(100 * r['first_try'])}% | {'-' if b.get('first_try') is None else str(round(100 * b['first_try'])) + '%'} | "
                     f"{'-' if moved is None else f'{moved:+d}'} | {cell(r['p95'])} | {cell(b.get('p95'))} | {cell(tops.get(task))} | {cell(r['max'])} | "
                     f"{'-' if r['cached'] is None else str(round(100 * r['cached'])) + '%'} |")
    conv = (m.get("npc_conversation") or {}).get("p95")
    mark = marks.get("npc_conversation_p95")
    lines.append("")
    lines.append(f"Size: {len(m) - len(dearer)} of {len(m)} tasks at or below the baseline's p95" + (f" (dearer: {', '.join(dearer)})" if dearer else "")
                 + (f"; npc_conversation's p95 {conv} against the mark of {mark}, " + ("held" if conv <= mark else "not held") if conv is not None and mark else "")
                 + f"; over their ceiling: {', '.join(over) if over else 'none'}.")
    lines.append(f"Acceptance: first tries within {marks.get('first_try_points', 5)} points of the baseline for "
                 f"{', '.join(marks.get('first_try_tasks') or []) or 'no task named'}: " + (f"not held ({'; '.join(fell)})" if fell else "held") + ".")
    return lines


def speech_inputs(folder: Path) -> set[int]:
    """(f490) The inputs of a recording that made a speech call."""
    import card_profile
    tasks = set(speech_tasks())
    return {int(c.get("input", 0)) for c in card_profile.calls_of(Path(folder)) if c.get("kind") != "embed"
            and (c.get("task") or card_profile.REQUIRED_TITLES.get(c.get("title", ""), "")) in tasks}


FIGHT_TASKS = ("combat_interpret", "combat_opening", "combat_narrate", "combat_aftermath", "goddess_line",      # (f510) the fight's own calls:
               "loot_name", "legendary_name", "accessory_name", "named_spell", "spell_rank")                    # its reading, its tellings, its naming
FIGHTS = Path(__file__).resolve().parent.parent / "data" / "measured" / "bundle_e_fights.yaml"


def fight_inputs(folder: Path) -> set[int]:
    """(f510) The inputs of a recording that made a fight call (FIGHT_TASKS)."""
    import card_profile
    return {int(c.get("input", 0)) for c in card_profile.calls_of(Path(folder)) if c.get("kind") != "embed"
            and (c.get("task") or card_profile.REQUIRED_TITLES.get(c.get("title", ""), "")) in FIGHT_TASKS}


def over_limit(root: Path = GOLDENS, limit: float | None = None, base: dict | None = None) -> dict[str, list[tuple[int, float]]]:
    """(f510) Per golden, the inputs whose required path, priced at expected answers on the card's profile, runs over budget.yaml
    limit_seconds. With `base` (the pre-D baseline's estimates), an input the baseline already priced over the limit is Bundle D's own
    debt and is left out, unless it is a fight input: those are Bundle E's, and every one must fit. Empty lists everywhere: the limit
    holds."""
    import card_profile
    if limit is None:
        limit = card_profile.budget_limit()
    out = {}
    for folder in sorted(p for p in Path(root).iterdir() if p.is_dir() and (p / "calls.jsonl.gz").exists()):
        before = {int(k): float(v) for k, v in ((base or {}).get("estimates") or {}).get(folder.name, {}).items()} if base else {}
        fights = fight_inputs(folder) if base else set()
        out[folder.name] = [(i, round(s, 1)) for i, s in card_profile.estimate_inputs(folder, expected=True)
                            if s > limit and not (before.get(i, 0.0) > limit and i not in fights)]
    return out


def fights_report(root: Path = GOLDENS) -> dict:
    """(f510) Per golden, per fight input: the required path's estimate at expected answers, the fight calls by task, the operations
    the input ran and how many of them were run again (an operation id seen at an earlier input: a restart after a rollback), and the
    odds' simulations (engine/combat.py danger runs eighty fights once per fight begun: an input with a combat_opening call)."""
    import card_profile
    from engine import combat as _combat
    import inspect
    runs = inspect.signature(_combat.danger).parameters["runs"].default
    out = {}
    for folder in sorted(p for p in Path(root).iterdir() if p.is_dir() and (p / "calls.jsonl.gz").exists()):
        calls = card_profile.calls_of(folder)
        est = dict(card_profile.estimate_inputs(folder, expected=True))
        turns = load(folder / "turns.jsonl")
        seen: set[str] = set()
        rows = {}
        for i in sorted(fight_inputs(folder)):
            mine = [c for c in calls if int(c.get("input", 0)) == i and c.get("kind") != "embed"]
            by_task = collections.Counter(t for t in ((c.get("task") or card_profile.REQUIRED_TITLES.get(c.get("title", ""), "")) for c in mine)
                                          if t in FIGHT_TASKS)                             # the fight's own calls; the line's others are not its
            ops = next((t.get("operations") or [] for t in turns if int(t.get("i", -1)) == i), [])
            ids = [o.get("id") for o in ops if o.get("id")]
            rows[i] = {"estimate": round(est.get(i, 0.0), 1), "calls": {k: v for k, v in sorted(by_task.items()) if k},
                       "operations": len(ids), "reruns": sum(1 for x in ids if x in seen),
                       "simulations": runs * by_task.get("combat_opening", 0)}
            seen |= set(ids)
        out[folder.name] = rows
    return out


def write_fights(root: Path = GOLDENS, note: str = "") -> str:
    """(f510) tools/latency.py --fights: the fight measures of the goldens, written to data/measured/bundle_e_fights.yaml (outside the
    data hash, engine/data_check.py fights_problems checks its shape). Returns the text written."""
    import yaml
    import card_profile
    body = {"note": note or "(f510, tools/latency.py --fights) Bundle E's fight measures on the goldens: per fight input of each recording, "
                           "the required path's seconds at expected answers on the card's profile, the fight calls by task, the operations "
                           "it ran and the re-runs among them, and the odds' simulations. A measurement, outside the data hash. "
                           "Do not hand-edit.",
            "limit_seconds": card_profile.budget_limit(), "fight_tasks": list(FIGHT_TASKS), "goldens": fights_report(root)}
    text = yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=140)
    FIGHTS.write_text(text, encoding="utf-8")
    return text


def fight_table(calls: list[dict], turns: list[dict], crashes: list[dict] = ()) -> list[str]:
    """(f510) The night's fights: calls per round (a round is a turn with a fight call), p95 seconds per fight task, fights let go at a
    load (crash.log rows written where the fight row is read), re-runs per round (a round's operations rolled back)."""
    fight_calls = [c for c in calls if c.get("task") in FIGHT_TASKS]
    if not fight_calls:
        return ["No fight calls."]
    rounds = collections.defaultdict(list)
    for c in fight_calls:
        rounds[c.get("turn")].append(c)
    by_turn = {r.get("turn"): r for r in turns}
    rolled = [sum(1 for o in (by_turn.get(t) or {}).get("ops") or [] if o.get("state") == "rolled_back") for t in rounds]
    lines = [f"{len(rounds)} rounds with a fight call; {fmt(len(fight_calls) / len(rounds), 1)} fight calls a round; "
             f"{fmt(sum(rolled) / len(rounds), 2)} operations rolled back a round; "
             f"{sum(1 for c in crashes if c.get('where') == 'fight row')} fights let go at a load.", "",
             "| Fight task | Calls | Seconds p50 | p95 | Failed |", "| --- | ---: | ---: | ---: | ---: |"]
    by_task = collections.defaultdict(list)
    for c in fight_calls:
        by_task[c["task"]].append(c)
    for task in FIGHT_TASKS:
        rs = by_task.get(task)
        if not rs:
            continue
        secs = [float(r.get("seconds") or 0) for r in rs]
        lines.append(f"| {task} | {len(rs)} | {fmt(pct(secs, .5))} | {fmt(pct(secs, .95))} | {sum(1 for r in rs if r.get('error'))} |")
    return lines


def dearer(now: dict, before: dict, inputs: set[int] | None = None) -> list[tuple[int, float | None, float]]:
    """(f490) The inputs priced above their pre-D price (to the tenth of a second the baseline keeps), of those with a speech call when
    they are named; an input the baseline never priced counts as dearer."""
    out = []
    for i, s in sorted(now.items()):
        if inputs is not None and i not in inputs:
            continue
        b = before.get(i)
        if b is None or round(s, 1) > float(b):
            out.append((i, b, round(s, 1)))
    return out


def gate(base: dict | None = None, root: Path = GOLDENS) -> dict[str, list[tuple[int, float | None, float]]]:
    """(f490) The goldens against their pre-D prices (the baseline's estimates), every answer at its expected size: per golden, the inputs
    with a speech call, (f510) or a fight call, priced dearer than before. Empty lists everywhere: the gate holds."""
    import card_profile
    base = _yaml(BASELINE) if base is None else base
    out = {}
    for name, before in (base.get("estimates") or {}).items():
        folder = Path(root) / name
        now = dict(card_profile.estimate_inputs(folder, expected=True))
        out[name] = dearer(now, {int(k): v for k, v in (before or {}).items()}, speech_inputs(folder) | fight_inputs(folder))
    return out


def golden_sizes(root: Path = GOLDENS) -> dict[str, tuple[int, str]]:
    """(f490) Per speech task, the largest prompt any golden recording sends, and the golden it is in."""
    import card_profile
    tasks = set(speech_tasks())
    out: dict[str, tuple[int, str]] = {}
    for folder in sorted(Path(root).iterdir()) if Path(root).exists() else []:
        if not (folder / "calls.jsonl.gz").exists():
            continue
        for c in card_profile.calls_of(folder):
            task = c.get("task") or card_profile.REQUIRED_TITLES.get(c.get("title", ""), "")
            if c.get("kind") == "embed" or task not in tasks:
                continue
            n = sum(len(str(m.get("content") or "")) for m in (c.get("request") or {}).get("messages") or [])
            if n > out.get(task, (0, ""))[0]:
                out[task] = (n, folder.name)
    return out


def ceilings_from(run_dirs: list[Path] = (), base: dict | None = None, root: Path = GOLDENS, kept: dict | None = None) -> dict:
    """(f490) Each speech task's ceiling: the night's p95 (the runs given; with none, the baseline night's), never under the largest
    prompt a golden sends, rounded up to `round_to`. A task measured by neither keeps the ceiling it had."""
    kept = ceilings() if kept is None else kept
    step = int(kept.get("round_to") or 500)
    night = speech_measures([r for d in run_dirs for r in load(Path(d) / "llm_calls.jsonl")]) if run_dirs else \
        ((_yaml(BASELINE) if base is None else base).get("tasks") or {})
    gold = golden_sizes(root)
    out = {}
    for task in speech_tasks():
        p95 = (night.get(task) or {}).get("p95")
        g, where = gold.get(task, (None, ""))
        if p95 is None and g is None:
            if (kept.get("ceilings") or {}).get(task):
                out[task] = dict(kept["ceilings"][task])
            continue
        chars = -(-max(x for x in (p95, g) if x is not None) // step) * step
        src = [f"{'the night' if run_dirs else 'the baseline night'}'s p95 {p95}" if p95 is not None else "",
               f"{where}'s largest {g}" if g is not None else ""]
        out[task] = {"chars": chars, "from": "; ".join(s for s in src if s)}
    return out


def write_ceilings(run_dirs: list[Path] = (), note: str = "") -> str:
    """(f490) data/measured/prompt_ceilings.yaml written from ceilings_from(), its closing marks kept as they were."""
    import yaml
    kept = ceilings()
    rows = ceilings_from(run_dirs, kept=kept)
    old = CEILINGS.read_text(encoding="utf-8") if CEILINGS.exists() else "# (f490) prompt ceilings\n"
    head = old.split("\nsource:")[0]
    marks = ("closing:" + old.split("\nclosing:", 1)[1]) if "\nclosing:" in old else ""      # the marks as written, comments and all
    body = {"source": note or (", ".join(Path(d).name for d in run_dirs) if run_dirs else "the baseline night and the goldens: the post-D night pending"),
            "round_to": int(kept.get("round_to") or 500),
            "ceilings": {t: {"chars": v["chars"], "from": v.get("from", "")} for t, v in rows.items()}}
    text = head.rstrip("\n") + "\n" + yaml.safe_dump(body, sort_keys=False, allow_unicode=True, width=140, default_flow_style=None) + marks
    CEILINGS.write_text(text, encoding="utf-8")
    return text


def baseline(run_dirs: list[Path], note: str = "") -> dict:
    """(f475) A night's measures as Bundle D's baseline (data/measured/bundle_d_baseline.yaml): the speech tasks over every run, and each
    run's continuity counts (tools/page_measures.py). The blind reading's memory-and-time counts are added by hand once it is read."""
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import page_measures
    calls, cont = [], {}
    for d in run_dirs:
        d = Path(d)
        calls += load(d / "llm_calls.jsonl")
        info = json.loads((d / "run.json").read_text(encoding="utf-8")) if (d / "run.json").exists() else {}
        m = page_measures.continuity(load(d / "turns_game.jsonl"), load(d / "turns.jsonl"), info)
        cont[d.name] = {"C1": [len(m["c1_time_slips"]), m["c1_time_spoken"]], "C2": [len(m["c2_met_as_stranger"]), len(m["c2_stranger_as_met"])],
                        "C3": [len(m["c3_open_as_done"]), len(m["c3_closed_as_open"])], "C4": {k: list(v) for k, v in m["c4_raised"].items()},
                        "C5": [len(m["c5_vanished"]), m["c5_lapsed"]],
                        "C6": [m["c6_false_name"][k] for k in ("kept", "spread", "after", "narrated", "planted")],
                        "C7": [[n, t, a, b] for n, t, a, b in m["c7_left_named"]], "C8": [len(m["c8_unseen_spoken_of"]), m["c8_witnesses_spoke"]]}
    return {"night": note or ", ".join(Path(d).name for d in run_dirs), "speech_tasks": list(speech_tasks()), "tasks": speech_measures(calls),
            "continuity": cont}


def turns_table(rows: list[dict]) -> list[str]:
    """Per kind of line the bot typed: how many, how long they took, how long to the first word, calls per turn."""
    by: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        by[r.get("kind", "?")].append(r)
    lines = ["| Line | Turns | Seconds p50 | p90 | First word p50 | p90 | Calls / turn | Model s / turn | Retries | Failed turns |",
             "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for kind, rs in sorted(by.items(), key=lambda kv: -len(kv[1])):
        secs = [float(r.get("seconds") or 0) for r in rs]
        first = [float(r["first_word"]) for r in rs if r.get("first_word") is not None]
        calls = [int(r.get("chat_calls") or 0) for r in rs]
        model = [float(r.get("chat_seconds") or 0) for r in rs]
        lines.append(f"| {kind} | {len(rs)} | {fmt(pct(secs, .5))} | {fmt(pct(secs, .9))} | {fmt(pct(first, .5)) if first else '-'} | "
                     f"{fmt(pct(first, .9)) if first else '-'} | {fmt(statistics.mean(calls), 1) if calls else '-'} | "
                     f"{fmt(statistics.mean(model), 1) if model else '-'} | {sum(int(r.get('retries') or 0) for r in rs)} | "
                     f"{sum(1 for r in rs if r.get('hesitated') or r.get('error'))} |")
    secs = [float(r.get("seconds") or 0) for r in rows]
    model = sum(float(r.get("chat_seconds") or 0) for r in rows)
    embeds = sum(int(r.get("embed_calls") or 0) for r in rows)
    embed_s = sum(float(r.get("embed_seconds") or 0) for r in rows)
    lines.append(f"\n{len(rows)} turns in {fmt(sum(secs) / 60, 1)} minutes; {fmt(100 * model / sum(secs), 0) if sum(secs) else '-'}% of it in the model; "
                 f"{embeds} embedding calls taking {fmt(embed_s, 1)} s; {sum(int(r.get('background_calls') or 0) for r in rows)} calls on background threads.")
    req = [float(r["required_seconds"]) for r in rows if r.get("required_seconds") is not None]
    if req:                                                                                  # (f468) the budget's measures, apart from the failed turns
        try:
            from engine import budget as _budget
            limit = float(_budget.B.get("limit_seconds") or 60)
        except Exception:
            limit = 60.0
        lines.append(f"The budget: {sum(len(r.get('deferred') or []) for r in rows)} optional calls deferred and "
                     f"{sum(len(r.get('dropped') or []) for r in rows)} dropped; {sum(1 for r in rows if r.get('stand_ins'))} turns told by a stand-in, "
                     f"{sum(1 for r in rows if 'passage' in (r.get('stand_ins') or []))} of them stood without a passage; "
                     f"{sum(int(r.get('recovered') or 0) for r in rows)} outcomes told at a load; "                                 # (f471)
                     f"the required path estimated at p50 {fmt(pct(req, .5))} s and p90 {fmt(pct(req, .9))} s, over {limit:g} s in "
                     f"{sum(1 for s in req if s > limit)} turns (apart from the failed turns above).")
    slow = sorted(rows, key=lambda r: -float(r.get("seconds") or 0))[:5]
    if slow:
        lines.append("\nSlowest turns:")
        for r in slow:
            lines.append(f"- {fmt(float(r.get('seconds') or 0))} s, {r.get('kind')}, {r.get('chat_calls')} calls, at {r.get('where')}: \"{r.get('text', '')[:70]}\"")
    return lines


def play_table(rows: list[dict], info: dict, pulse: list[dict]) -> list[str]:
    """(f368) How player-like the run was: the measures the night bot's goals and words are judged by (tools/nightbot.py)."""
    n = len(rows)
    share = lambda a, b: f"{a} of {b} ({round(100 * a / b)}%)" if b else "-"
    texts = [r.get("text", "") for r in rows]
    src = collections.Counter(r.get("source") for r in rows if r.get("source"))
    with_passage = [r for r in rows if "refers" in r]
    talk = [r for r in rows if r.get("kind") == "talk"]
    bot = info.get("bot") or {}
    done, dropped = bot.get("goals_done") or {}, bot.get("goals_dropped") or {}
    goals = collections.Counter((r.get("goal") or "-").split(":")[0] for r in rows)
    ended = sum(1 for p in pulse if p.get("kind") == "end" and p.get("how") == "player")
    waits = sum(1 for r in rows if r.get("kind") == "wait")
    lines = ["| Measure | Value |", "| --- | --- |",
             f"| Distinct lines | {share(len(set(texts)), n)} |",
             f"| Lines the model wrote | {src.get('model', 0)} (template {src.get('template', 0)}; model failed {bot.get('model_failed', 0)}, {fmt(float(bot.get('model_seconds') or 0), 0)} s) |",
             f"| Lines picking up the passage before | {share(sum(1 for r in with_passage if r.get('refers')), len(with_passage))}; in talk {share(sum(1 for r in talk if r.get('refers')), len(talk))} |",
             f"| Contracts taken / finished | {bot.get('contracts_taken', 0)} / {bot.get('contracts_done', 0)} |",
             f"| Situations met / followed / ended by the player | {bot.get('doors_seen', 0)} / {bot.get('doors_followed', 0)} / {ended} |",
             f"| Goals finished / given up | {sum(done.values())} / {sum(dropped.values())}"
             + (" (" + ", ".join(f"{k} {done.get(k, 0)}/{dropped.get(k, 0)}" for k in sorted(set(done) | set(dropped))) + ")" if done or dropped else "") + " |",
             f"| Deaths (above the level band) | {info.get('deaths', bot.get('deaths', 0))} ({bot.get('deaths_above_band', 0)}) |",
             f"| Fights | {bot.get('fights', sum(1 for r in rows if r.get('kind') == 'fight'))} |",
             f"| Waits | {share(waits, n)} |",
             f"| Places visited | {bot.get('places', len({r.get('where') for r in rows}))} |"]
    if goals:
        lines.append("\nTurns by goal: " + ", ".join(f"{k} {v}" for k, v in goals.most_common()))
    return lines


REFUSAL_WORDS = re.compile(r"\b(closed|not|no|nothing|can't|cannot|isn't|aren't|don't|nowhere|already|too|need|unknown|refuse)\b", re.I)
PRONOUNS = {"he": re.compile(r"\b(he|him|his|himself)\b", re.I), "she": re.compile(r"\b(she|her|hers|herself)\b", re.I)}


def _prose(calls: list[dict]) -> list[tuple[int, str, str]]:
    """(turn, task, text) for the prose of every accepted answer."""
    from engine import hygiene
    out = []
    for r in calls:
        if r.get("error") or not r.get("raw") or r.get("task") == "player_line":     # the bot's own lines are not the game's
            continue
        try:
            value = json.loads(r["raw"])
        except ValueError:
            continue
        for t in hygiene.prose_of(value):
            if t:
                out.append((int(r.get("turn") or 0), r.get("task", "?"), t))
    return out


def consistency_table(rows: list[dict], calls: list[dict], info: dict) -> list[str]:
    """(f391) What a reader of the night would trip over, counted: the machinery in the text, refusals said again and again, what the
    game believed against where the player was, captives held, people who left the party and were never spoken of again, and companions
    called by the wrong pronoun or people. Rough by design (a sentence may be about two people); the counts are for comparing nights."""
    from engine import hygiene
    lines = ["| Measure | Value |", "| --- | --- |"]
    reasons = {v.split(":")[0][:40]: k for k, v in hygiene.H["reasons"].items()}
    at_model = collections.Counter()
    for r in calls:
        err = str(r.get("error") or "")
        hit = next((k for head, k in reasons.items() if err.startswith(head)), None)
        if hit:
            at_model[hit] += 1
        elif err.startswith("write every word in English"):
            at_model["script"] += 1
    screen = info.get("hygiene") or {}
    lines.append(f"| Machinery sent back by the gateway | {sum(at_model.values())}" + (f" ({', '.join(f'{k} {v}' for k, v in at_model.most_common())})" if at_model else "") + " |")
    lines.append(f"| Machinery mended at the screen | {sum(screen.values())}" + (f" ({', '.join(f'{k} {v}' for k, v in sorted(screen.items()))})" if screen else "") + " |")
    keyed = []
    for r in rows:
        keys = {re.sub(r"\d+", "#", n.lower())[:90] for n in r.get("notes") or [] if REFUSAL_WORDS.search(n)}
        keyed.append(keys)
    longest, worst, again = 0, "", 0
    run: dict[str, int] = {}
    for i, keys in enumerate(keyed):
        run = {k: run.get(k, 0) + 1 for k in keys}
        for k, n in run.items():
            if n > longest:
                longest, worst = n, k
        if any(sum(1 for prev in keyed[max(0, i - 10):i] if k in prev) >= 2 for k in keys):
            again += 1
    lines.append(f"| Turns ending on a refusal said at least twice in the last ten | {again} |")
    lines.append(f"| Longest run of one refusal | {longest}" + (f' ("{worst[:70]}")' if worst else "") + " |")
    lines.append(f"| Goals the bot gave up on meeting the same refusal twice | {(info.get('bot') or {}).get('blocked', 0)} |")
    lines += goal_lines(rows, info)
    states = [r.get("state") or {} for r in rows]
    stale = sum(1 for s in states if s.get("delve") and not s.get("at_dungeon"))
    held, run_hold = 0, 0
    for s in states:
        run_hold = run_hold + 1 if s.get("party") and s.get("party_mode", "with") != "with" else 0
        held = max(held, run_hold)
    lines.append(f"| Turns the game believed the player was in a dungeon they had left | {stale} |")
    lines.append(f"| Longest run of the party held back | {held} turns |")
    lines.append(f"| Captives held at once (most) / longest held | {max((s.get('prisoners', 0) for s in states), default=0)} / "
                 f"{max((s.get('prisoner_days', 0) for s in states), default=0)} days |")
    prose = _prose(calls)
    left = []
    for a, b in zip(rows, rows[1:]):
        gone = set((a.get("state") or {}).get("party") or []) - set((b.get("state") or {}).get("party") or [])
        for name in gone:
            first = name.split()[0]
            after = sum(1 for t, _, text in prose if t > int(b.get("turn") or 0) and re.search(rf"\b{re.escape(first)}\b", text))
            left.append(f"{name} (turn {b.get('turn')}): named {after} times after")
    lines.append(f"| Left the party, and named afterwards | {'; '.join(left) if left else 'nobody left'} |")
    cast = info.get("cast") or {}
    firsts = {n.split()[0]: n for n in cast}
    from engine import look
    peoples = {spec["word"]: p for p, spec in look.L["peoples"].items()}
    wrong_pr = collections.Counter()
    wrong_pe = collections.Counter()
    for _, task, text in prose:
        for sent in re.split(r"(?<=[.!?])\s+", text):
            named = [n for f, n in firsts.items() if re.search(rf"\b{re.escape(f)}\b", sent)]
            if len(named) != 1:
                continue
            who = cast[named[0]]
            pr = who.get("pronoun")
            other = {"he": "she", "she": "he"}.get(pr)
            if other and PRONOUNS[other].search(sent) and not PRONOUNS[pr].search(sent):
                wrong_pr[(named[0], task)] += 1
            for word, pid in peoples.items():
                if who.get("people") and pid != who["people"] and re.search(rf"\b{re.escape(word)}\b", sent, re.I):
                    wrong_pe[(named[0], task)] += 1
    def top(c):
        return "; ".join(f"{n} in {t} {v}" for (n, t), v in c.most_common(4))
    lines.append(f"| Companion sentences with the other gender's pronoun | {sum(wrong_pr.values())}" + (f" ({top(wrong_pr)})" if wrong_pr else "") + " |")
    lines.append(f"| Companion sentences naming another people | {sum(wrong_pe.values())}" + (f" ({top(wrong_pe)})" if wrong_pe else "") + " |")
    return lines


def goal_lines(rows: list[dict], info: dict) -> list[str]:
    """(f393) GOAL.md, counted: facades met (the player reached for something the place or the passage named, and nothing was there),
    dead ends (looked for something unnamed, found nothing), attempts the game made room for (the turn's record: made), attempts it
    said no to in the world (refused), and additions per hour of play. The refusals log and each turn's record are the sources."""
    refs = info.get("_refusals") or []
    kinds = collections.Counter(r.get("kind") for r in refs)
    outcomes = collections.Counter(o.get("kind") for r in rows for o in (r.get("outcomes") or []))
    hours = float(info.get("hours") or 0) or 1.0
    made_how = collections.Counter(o.get("how") or "?" for r in rows for o in (r.get("outcomes") or []) if o.get("kind") == "made")
    party = {n for r in rows for n in ((r.get("state") or {}).get("party") or [])}
    false_no = [r for r in refs if r.get("kind") == "refused"
                and any(re.search(rf"\b{re.escape(n.split()[0])}\b", f"{r.get('text', '')} {r.get('why', '')}") for n in party if n)]
    return [f"| Facades met / dead ends | {kinds.get('facade', 0)} / {kinds.get('dead_end', 0)} |",
            f"| Attempts the world made room for / said no to in the world | {outcomes.get('made', 0)} / {kinds.get('refused', 0)} |",
            f"| ...made room for, by how (ruled: the game judged the attempt; narrated: adopted from a passage) | "      # (f414)
            + (", ".join(f"{k} {v}" for k, v in made_how.most_common()) or "none") + " |",
            f"| ...said no to, about someone in the party (likely a misread) | {len(false_no)} |",
            f"| Additions to the world per hour | {outcomes.get('made', 0) / hours:.1f} |",
            f"| Parts made different by an attempt (blocked, lit, cleared...) | {outcomes.get('changed', 0)} |"]


def summarise(run_dir: Path) -> str:
    run_dir = Path(run_dir)
    calls = load(run_dir / "llm_calls.jsonl")
    turns = load(run_dir / "turns.jsonl")
    pulse = load(run_dir / "pulse.jsonl")
    game_turns = load(run_dir / "turns_game.jsonl")
    info = {}
    if (run_dir / "run.json").exists():
        info = json.loads((run_dir / "run.json").read_text(encoding="utf-8"))
    info["_refusals"] = load(run_dir / "refusals.jsonl")          # (f393)
    lines = [f"# Night run: {run_dir.name}", ""]
    if info:
        lines.append(f"{info.get('character', '?')}, {info.get('class', '?')}, level {info.get('level', '?')}, {info.get('deaths', 0)} deaths; "
                     f"{info.get('turns', len(turns))} turns in {info.get('hours', '?')} hours; stopped: {info.get('reason', '?')}; "
                     + (f"starting as {info['start']}, playing as {info.get('persona', '?')}; " if info.get("start") else "") +
                     f"model {info.get('model', '?')}" + (" (stand-in)" if info.get("stub") else "")
                     + (f", warm calls {(info.get('sampling') or {}).get('temp_add', 0):+g} temperature and {(info.get('sampling') or {}).get('repeat_add', 0):+g} repeat penalty"
                        if any((info.get("sampling") or {}).values()) else "") + ".")
        lines.append("")
    lines += ["## Turns", ""]
    lines += turns_table(turns) if turns else ["No turns recorded."]
    if game_turns:
        handled = collections.Counter(r.get("handled_by", "?") for r in game_turns)
        lines += ["", "Lines by what read them: " + ", ".join(f"{k} {n}" for k, n in handled.most_common())]
    lines += ["", "## Play", ""] + play_table(turns, info, pulse) if turns else []
    if turns:
        lines += ["", "## Consistency", ""] + consistency_table(turns, calls, info)
    if game_turns:                                                  # (f414) what the page showed, counted from the page
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import page_measures
        lines += ["", "## The page", ""] + page_measures.table(game_turns, turns, calls, info)
        lines += ["", "## Continuity (from the page)", ""] + page_measures.continuity_table(game_turns, turns, info)    # (f474)
    lines += ["", "## Calls by task", ""]
    lines += calls_table(calls) if calls else ["No calls recorded."]
    if any(c.get("task") in FIGHT_TASKS for c in calls):             # (f510) the fights: calls a round, p95 a task, fights let go, re-runs
        lines += ["", "## Fights", ""] + fight_table(calls, turns, load(run_dir / "crash.log"))
    if calls:                                                       # (f475) the speech tasks Bundle D changes, measured first
        lines += ["", "## Speech tasks (prompt size and first try)", ""] + speech_table(calls)
        if BASELINE.exists():                                       # (f490) beside the baseline's, with each task's ceiling
            lines += ["", "## Speech tasks against Bundle D's baseline", ""] + against(calls)
    text = "\n".join(lines) + "\n"
    (run_dir / "summary.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return
    if args[0] == "--baseline":                                     # (f475) --baseline RUN_DIR... : the night's measures, as YAML
        import yaml
        print(yaml.safe_dump(baseline([Path(a) for a in args[1:]]), sort_keys=False, allow_unicode=True, width=140))
        return
    if args[0] == "--against":                                      # (f490) --against RUN_DIR... : the speech tasks beside the baseline's
        print("\n".join(against([r for a in args[1:] for r in load(Path(a) / "llm_calls.jsonl")])))
        return
    if args[0] == "--gate":                                         # (f490) the goldens against their pre-D prices; exit 1 when dearer
        got = gate()                                                # (f510) speech and fight calls alike, and every input under the limit
        for name, rows in got.items():
            print(f"{name}: " + ("every input with a speech or a fight call at or below its pre-D price" if not rows else
                                 "dearer than before: " + ", ".join(f"input {i} ({b} s before, {s} s now)" for i, b, s in rows)))
        over = over_limit(base=_yaml(BASELINE))                     # Bundle D's own over-limit inputs stand; a fight input never may
        for name, rows in over.items():
            print(f"{name}: " + ("every input under the limit, apart from those the baseline priced over it" if not rows else
                                 "over the limit: " + ", ".join(f"input {i} ({s} s)" for i, s in rows)))
        sys.exit(1 if any(got.values()) or any(over.values()) else 0)
    if args[0] == "--fights":                                       # (f510) the goldens' fight measures, written to data/measured/bundle_e_fights.yaml
        print(write_fights())
        return
    if args[0] == "--ceilings":                                     # (f490) --ceilings [RUN_DIR...] : write data/measured/prompt_ceilings.yaml
        print(write_ceilings([Path(a) for a in args[1:]]))
        return
    if args[0] == "--estimates":                                    # (f490) --estimates RECORDING : its inputs priced at expected answers
        import card_profile
        for i, s in card_profile.estimate_inputs(Path(args[1]), expected=True):
            print(f"    {i}: {round(s, 1)}")
        return
    if args[0] == "--calls":
        rows = load(Path(args[1] if len(args) > 1 else "logs/llm_calls.jsonl"))
        print("\n".join(calls_table(rows)) if rows else "No calls in that log.")
        return
    print(summarise(Path(args[0])))


if __name__ == "__main__":
    main()
