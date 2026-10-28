"""Plays a campaign with the real model for hours and logs what every turn cost: a run for a machine left on overnight.

    python tools/nightrun.py [--hours 6] [--turns 0] [--class warrior] [--level 13] [--seed 1] [--out DIR] [--stub]
    nightrun.bat --hours 6                 (Windows: the same, through the game's own Python environment)
    nightrun.bat --runs 4 --hours 2        a night of four runs one after another, each its own process, seed and class (f361)
    nightrun.bat --start veteran            begin as someone with a past (f367, data/rules/starts.yaml); a night rotates through them
    nightrun.bat --persona hunter           play as one kind of player (f368, tools/nightbot.py PERSONAS); a night rotates through them too

A bot plays the way a player plays (tools/nightbot.py, f368): with goals it keeps across turns (a contract taken, done and reported;
a situation the world brought to it followed to one of its endings; a place it has not seen), a persona that weights what it cares
about (--persona; a night rotates through them), a level band it keeps to on roads as well as in the wild, and lines the model writes
from what the game just said, so a conversation's second line answers the first. The real model reads them. summary.md ends with
the measures of how player-like the run was: distinct lines, lines picking up the passage before, contracts finished, situations
followed and ended by the player, deaths above the band. The run keeps
every log in full under logs/nightrun/<when>/: every model call with Ollama's own counts (tokens read and written, the time each
took, model loads), every turn with its wall time, the time to its first word, the calls and retries it took, and a transcript.
At the end tools/latency.py writes summary.md there; it can be run again on the folder at any time.

The character starts past Maren's tutorial (--level 13, in a save of its own that the home page never lists), so the run is
ordinary play: towns, roads, talk, fights; --level 1 plays the tutorial too, though the bot does not know her script and may wander. --stub plays with the stand-in model instead (the test suite uses it) and measures
nothing real. Ollama must be running with the game's model downloaded; the run stops on its own if the model stops answering.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import shutil
import subprocess
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from nightbot import ROTATION as PERSONAS, Bot, persona_for      # (f368) the player with goals; Bot stays importable from here (tools/eventrun.py)

HESITATION = "The world seems to hesitate"          # what the game says when a turn's model call failed and was rolled back


def die(message: str) -> None:
    print(message)
    sys.exit(1)


class Run:
    """The harness: the console hooks that record the transcript and the time to the first word, the wrapped model client that counts
    every call, and the turn rows."""

    def __init__(self, out: Path, hours: float, turns: int, live: bool):
        self.out, self.hours, self.max_turns, self.live = out, hours, turns, live
        self.started = time.time()
        self.rows: list[dict] = []
        self.turn_file = (out / "turns.jsonl").open("a", encoding="utf-8")
        self.transcript = (out / "transcript.md").open("a", encoding="utf-8")
        self.errors = (out / "errors.log").open("a", encoding="utf-8")
        self.current: dict | None = None             # the turn being played
        self.t_line = 0.0
        self.first_word: float | None = None
        self.calls: list[dict] = []
        self.sub_answers = 0
        self.hesitations = 0                         # turns in a row the model failed
        self.reason = ""
        self.stop_when = None                        # a run with a goal (tools/eventrun.py) says when it is reached
        self.passage: list[str] = []                 # (f368) everything the game said since the last line: what the bot's next line answers

    # ---- the console: everything the game prints goes to the transcript, and the first story line stamps the time
    def install_console(self) -> None:
        from ui import console
        self.real = {k: getattr(console, k) for k in ("narrate", "say", "npc_says", "dialogue", "note", "wait", "ledger", "out",
                                                     "combat_numbers", "combat_panel", "debug", "ask", "status_block", "header")}
        console.narrate = lambda text: self.seen("", text)
        console.say = lambda text, speaker="": self.seen(speaker or "says", text)
        console.npc_says = lambda label, speech, gesture="": self.seen(label, speech + (f" ({gesture})" if gesture else ""))
        console.dialogue = lambda before, speaker, speech, after: self.seen(speaker, " ".join(x for x in (before, f'"{speech}"', after) if x))
        console.note = lambda message, *a, **k: self.noted(str(message))
        console.wait = lambda message: self.noted(str(message))
        console.ledger = lambda message: self.noted(str(message))
        console.out = lambda text="": self.noted(str(text))
        console.combat_numbers = lambda lines: self.noted("\n".join(f"    {l}" for l in lines))
        console.combat_panel = lambda lines: None
        console.status_block = lambda *a, **k: None
        console.header = lambda text: None
        console.debug = lambda message: None
        console.ask = self.ask

    def seen(self, who: str, text: str) -> None:
        if self.first_word is None and self.current is not None:
            self.first_word = time.time() - self.t_line
        self.passage.append((f"{who}: " if who else "") + text.strip())
        self.transcript.write((f"**{who}:** " if who else "") + text.strip() + "\n\n")

    def noted(self, text: str) -> None:
        if HESITATION in text:
            self.hesitations += 1
            if self.current is not None:
                self.current["hesitated"] = True
        self.passage.append(text.strip())
        self.transcript.write(f"_{text.strip()}_\n\n")

    # ---- the model client: every call counted against the turn it served
    def install_client(self) -> None:
        from llm import gateway as gw
        client = gw._client
        real_chat, real_embed = client.chat, getattr(client, "embed", None)
        main = threading.main_thread()

        def chat(**k):
            t0 = time.perf_counter()
            ok = True
            try:
                return real_chat(**k)
            except Exception:
                ok = False
                raise
            finally:
                msgs = k.get("messages") or []
                self.calls.append({"kind": "chat", "schema": (k.get("format") or {}).get("title", "?"), "seconds": time.perf_counter() - t0,
                                   "retry": len(msgs) > 2, "ok": ok, "main": threading.current_thread() is main})

        def embed(**k):
            t0 = time.perf_counter()
            try:
                return real_embed(**k)
            finally:
                self.calls.append({"kind": "embed", "schema": "", "seconds": time.perf_counter() - t0, "retry": False, "ok": True,
                                   "main": threading.current_thread() is main, "texts": len(k.get("input") or [])})

        client.chat = chat
        if real_embed is not None:
            client.embed = embed

    # ---- the prompt: the bot answers; the harness times the turn around it
    def ask(self, main: bool = False, menu: bool = False) -> str:
        if not main:                                  # a yes/no the bot's own line brought up: agree a couple of times, then stop
            self.sub_answers += 1
            return "yes" if self.sub_answers <= 2 else "no"
        self.close_turn()
        reason = self.done()
        if reason:
            self.reason = reason
            return "quit"
        text, kind = self.bot.decide()
        self.passage = []
        self.sub_answers = 0
        self.current = {"n": len(self.rows) + 1, "time": datetime.now().isoformat(timespec="seconds"), "kind": kind, "text": text,
                        "where": self.bot.where(), "turn": self.bot.ws.store.meta.turn, "level": self.bot.c.level,
                        "hp": round(self.bot.hp(), 2), "combat": bool(self.bot.ws.combat),
                        **{k: v for k, v in (getattr(self.bot, "meta", None) or {}).items() if not k.startswith("_")}}   # (f368) goal, persona, source, refers
        self.transcript.write(f"### {self.current['n']} · {self.current['time'][11:]} · {self.current['where']}\n\n> {text}\n\n")
        self.transcript.flush()
        self.first_word, self.calls = None, []
        self.t_line = time.time()
        return text

    def close_turn(self) -> None:
        if self.current is None:
            return
        row = self.current
        chats = [c for c in self.calls if c["kind"] == "chat"]
        embeds = [c for c in self.calls if c["kind"] == "embed"]
        row.update(seconds=round(time.time() - self.t_line, 2), first_word=None if self.first_word is None else round(self.first_word, 2),
                   chat_calls=sum(1 for c in chats if c["main"]), chat_seconds=round(sum(c["seconds"] for c in chats if c["main"]), 2),
                   retries=sum(1 for c in chats if c["retry"]), failed_calls=sum(1 for c in chats if not c["ok"]),
                   background_calls=sum(1 for c in chats if not c["main"]),
                   embed_calls=sum(1 for c in embeds if c["main"]), embed_seconds=round(sum(c["seconds"] for c in embeds if c["main"]), 2),
                   schemas=dict(collections.Counter(c["schema"] for c in chats if c["main"])),
                   hesitated=row.get("hesitated", False), level_after=self.bot.c.level, deaths=self.bot.c.deaths)
        if not row["hesitated"]:
            self.hesitations = 0
        self.rows.append(row)
        self.turn_file.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.turn_file.flush()
        print(f"#{row['n']:<4} {row['seconds']:6.1f}s  {row['kind']:<8} {row['text'][:60]:<60}  "
              f"{row['chat_calls']} calls {row['chat_seconds']:.1f}s" + (f"  first word {row['first_word']}s" if row["first_word"] else "")
              + ("  (model failed)" if row["hesitated"] else ""), flush=True)
        self.current = None

    def done(self) -> str:
        if self.stop_when is not None:
            why = self.stop_when()
            if why:
                return why
        if self.max_turns and len(self.rows) >= self.max_turns:
            return f"turn limit ({self.max_turns})"
        if time.time() - self.started >= self.hours * 3600:
            return f"time limit ({self.hours:g} hours)"
        if self.hesitations >= 12:
            return "the model stopped answering (12 turns failed in a row)"
        if self.live and self.hesitations >= 3:
            from llm import setup_check
            if not setup_check.server_up():
                return "Ollama stopped answering"
        return ""

    def finish(self, extra: dict) -> None:
        self.close_turn()
        for f in (self.turn_file, self.transcript, self.errors):
            f.close()
        info = {"ended": datetime.now().isoformat(timespec="seconds"), "turns": len(self.rows), "reason": self.reason,
                "hours": round((time.time() - self.started) / 3600, 2), **extra}
        (self.out / "run.json").write_text(json.dumps(info, indent=1), encoding="utf-8")


def ended_by_player(path: Path) -> int:
    """(f368) Situations the player ended, from the run's own world log."""
    n = 0
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                if r.get("kind") == "end" and r.get("how") == "player":
                    n += 1
    except OSError:
        pass
    return n


def spend_points(c, spec) -> None:
    """Spend the levels' points the way the balance bots do: by the class's per-level weights, checked by the engine."""
    from engine import leveling
    names = list(spec["per_level"])
    spend: dict[str, int] = {}
    left = c.unspent_points
    while left > 0:
        for a in names:
            give = min(spec["per_level"][a], left)
            if give:
                spend[a] = spend.get(a, 0) + give
                left -= give
    if not leveling.check_allocation(c, spend):
        leveling.allocate(c, spend)


def outfit(c, spec: dict, level: int, rng: random.Random) -> None:
    """Gear and supplies for a character of this level, as one who reached it would carry: the class's weapon and armour at the level,
    a piece for the other slots, a stack of healing draughts and coin for rooms. The test helper's character has a level-one kit."""
    from engine import inventory, items, loot

    def piece(base_id: str, rarity: str):
        it = items.make(base_id, rarity, level, rng=rng)
        loot.roll_gear(it, rng)
        return it

    c.equipment["main_hand"] = piece(spec["weapon"], "epic")
    if spec.get("armor"):
        c.equipment[spec["armor"][1]] = piece(spec["armor"][0], "epic")
    for slot in ("head", "hands", "feet"):
        bases = [b for b in items.CATALOG.values() if b.slot == slot and b.min_level <= level]
        if bases and slot not in c.equipment:
            c.equipment[slot] = piece(rng.choice(bases).id, "rare")
    inventory.add(c.inventory, inventory.make_good("healing_draught", 8), 99)
    c.coins = max(c.coins, level * 2000)


def hire_party(ws, n: int) -> list[dict]:
    """Take on `n` adventurers from the home hall's roster, as a player of this level would have before setting out: the fee paid,
    the quirks rolled, the mix of roles the hall offers. Nothing is written by the model until they speak."""
    if n <= 0:
        return []
    from engine import party as rules
    hall = ws.guild_place_id()
    if not hall:
        return []
    c = ws.player.character
    was = ws.player.location
    ws.player.location = hall                        # the roster is the hall's
    try:
        offers = ws.party_roster()
    finally:
        ws.player.location = was
    picks, roles = [], set()
    for m in offers:                                 # one of each role first, then whoever is left
        if m["role"] not in roles:
            picks.append(m); roles.add(m["role"])
    picks += [m for m in offers if m not in picks]
    picks = picks[:min(n, rules.P["max_party"])]
    c.coins += sum(m["fee"] for m in picks)          # their fees are the player's past earnings, not this character's purse
    svc = ws.party_service
    with ws.store.transaction():
        for m in picks:
            svc.hire(m, c.level)
    ws.store.save_player(ws.player)
    return [{"name": m["name"], "role": m["role"], "level": m["level"], "people": m.get("people", "")} for m in ws.player.party]


def batch(args) -> None:
    """(f361) Several runs one after another, each a process of its own (a fresh game, a fresh save, nothing carried over in memory), the
    seed counting up from --seed and the class rotating through --classes (default: every class, from --class on). A run that dies does
    not end the night: the next starts. Each run's logs are a folder of their own under the out folder, named by when it started, its
    class and its seed, so tools/lora_dataset.py --runs-dir reads the whole night; batch_<when>.md there lists the runs when it is over."""
    import simlib
    classes = [c.strip() for c in args.classes.split(",") if c.strip()] or list(simlib.CLASSES)
    unknown = [c for c in classes if c not in simlib.CLASSES]
    if unknown:
        die(f"--classes must be of: {', '.join(simlib.CLASSES)} (not {', '.join(unknown)})")
    if not args.classes and args.cls in classes:
        classes = classes[classes.index(args.cls):] + classes[:classes.index(args.cls)]
    from engine import starts as _starts
    points = [s.strip() for s in args.starts.split(",") if s.strip()] or _starts.rotation()      # (f367) a night begins its runs at different points
    unknown = [s for s in points if s not in _starts.names()]
    if unknown:
        die(f"--starts must be of: {', '.join(_starts.names())} (not {', '.join(unknown)})")
    personas = [s.strip() for s in args.personas.split(",") if s.strip()] or list(PERSONAS)      # (f368) ...and as different kinds of player
    unknown = [s for s in personas if s not in PERSONAS]
    if unknown:
        die(f"--personas must be of: {', '.join(PERSONAS)} (not {', '.join(unknown)})")
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    base = Path(args.out or "logs/nightrun")
    base.mkdir(parents=True, exist_ok=True)
    plan = [(classes[i % len(classes)], args.seed + i, points[i % len(points)], personas[i % len(personas)]) for i in range(args.runs)]
    print(f"A night of {args.runs} runs, {args.hours:g} hours each ({args.runs * args.hours:g} in all): "
          + ", ".join(f"{c} seed {s} ({st}, {pe})" for c, s, st, pe in plan), flush=True)
    rows, stopped = [], False
    for i, (cls, seed, start, persona) in enumerate(plan, 1):
        when = datetime.now().strftime("%Y%m%d_%H%M")
        out = base / f"{when}_{cls}_{seed}"
        save = f"{args.save or 'nightrun_' + stamp}_{cls}_{seed}"
        cmd = [sys.executable, str(Path(__file__).resolve()), "--hours", str(args.hours), "--turns", str(args.turns), "--class", cls, "--level", str(args.level),
               "--seed", str(seed), "--party", str(args.party), "--out", str(out), "--save", save, "--start", start, "--persona", persona] \
            + (["--stub"] if args.stub else [])
        print(f"\n=== run {i} of {args.runs}: {cls}, seed {seed}, starting as {start}, playing as {persona} -> {out}", flush=True)
        started = time.time()
        proc = subprocess.Popen(cmd)
        try:
            code = proc.wait()
        except KeyboardInterrupt:                                     # the run has it too, and writes its summary before it goes
            print("\nstopping after this run writes its logs...", flush=True)
            try:
                code = proc.wait(timeout=180)
            except Exception:
                proc.kill()
                code = -1
            stopped = True
        info = {}
        try:
            info = json.loads((out / "run.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
        bot = info.get("bot") or {}
        rows.append({"run": out.name, "class": cls, "seed": seed, "start": start, "persona": persona, "exit": code, "minutes": round((time.time() - started) / 60, 1),
                     "distinct": f"{round(100 * info['distinct'])}%" if isinstance(info.get("distinct"), (int, float)) else "",
                     "done": bot.get("contracts_done", ""), "ended": info.get("ended_by_player", ""),
                     **{k: info.get(k, "") for k in ("turns", "hours", "level", "deaths", "reason")}})
        if stopped:
            break
    lines = [f"# A night of {len(rows)} run(s), started {stamp}", "",
             "| Run | Class | Seed | Start | Persona | Turns | Hours | Level | Deaths | Distinct lines | Contracts done | Ended by player | Stopped | Exit |",
             "| --- | --- | ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |"]
    for r in rows:
        lines.append(f"| {r['run']} | {r['class']} | {r['seed']} | {r['start']} | {r['persona']} | {r['turns']} | {r['hours']} | {r['level']} | {r['deaths']} | "
                     f"{r['distinct']} | {r['done']} | {r['ended']} | {r['reason']} | {r['exit']} |")
    text = "\n".join(lines) + "\n"
    (base / f"batch_{stamp}.md").write_text(text, encoding="utf-8")
    print("\n" + text)
    print(f"Logs: {base.resolve()}  (every folder above is a run; tools/lora_dataset.py --runs-dir {base} reads them all)")


def main() -> None:
    ap = argparse.ArgumentParser(description="Play a campaign with the real model for hours and log what every turn cost.")
    ap.add_argument("--hours", type=float, default=6.0, help="stop after this many hours (default 6)")
    ap.add_argument("--turns", type=int, default=0, help="stop after this many turns (default: no limit)")
    ap.add_argument("--class", dest="cls", default="warrior", help="the character's class (a key of simlib.CLASSES; default warrior)")
    ap.add_argument("--level", type=int, default=13, help="the character's starting level (default 13, past the tutorial; 1 plays it)")
    ap.add_argument("--seed", type=int, default=1, help="the campaign's seed and the bot's")
    ap.add_argument("--party", type=int, default=3, help="adventurers hired from the home hall before setting out (default 3, a full party; 0 for none)")
    ap.add_argument("--out", default="", help="where the logs go (default logs/nightrun/<when>)")
    ap.add_argument("--save", default="", help="the save folder's name (default nightrun_<when>; never listed on the home page)")
    ap.add_argument("--stub", action="store_true", help="play with the stand-in model (measures nothing real; for the test suite)")
    ap.add_argument("--runs", type=int, default=1, help="(f361) play this many runs one after another, each its own process with the seed counting up from --seed "
                                                        "and the class rotating; --hours is per run. A night left alone (default 1)")
    ap.add_argument("--classes", default="", help="with --runs: the classes to rotate through, comma-separated (default: every class, from --class on)")
    ap.add_argument("--start", default="green", help="(f367) the starting point (data/rules/starts.yaml): green, known, veteran, scarred, legend")
    ap.add_argument("--starts", default="", help="with --runs: the starting points to rotate through, comma-separated (default: the file's rotation)")
    ap.add_argument("--persona", default="", help=f"(f368) the kind of player the bot is: {', '.join(PERSONAS)} (default: by the seed, in that order)")
    ap.add_argument("--personas", default="", help="with --runs: the personas to rotate through, comma-separated (default: all, in order)")
    args = ap.parse_args()
    if args.runs > 1:
        batch(args)
        return

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = Path(args.out or f"logs/nightrun/{stamp}")
    out.mkdir(parents=True, exist_ok=True)
    save = args.save or f"nightrun_{stamp}"

    import config
    config.LOG_PATH = str(out / "llm_calls.jsonl")          # the run's own logs, kept whole: the game's trimming never touches them
    config.PULSE_LOG_PATH = str(out / "pulse.jsonl")        # (f355) what the world did, and what of it the player met
    config.TURN_LOG_PATH = str(out / "turns_game.jsonl")
    config.SESSION_STATS_PATH = str(out / "sessions.jsonl")
    config.REFUSALS_LOG_PATH = str(out / "refusals.jsonl")
    config.LOG_MAX_MB = 10 ** 6
    config.LOG_FULL_PROMPTS = True                           # (f361) every system prompt whole: a run's log is training data (tools/lora_dataset.py)

    import simlib
    if args.cls not in simlib.CLASSES:
        die(f"--class must be one of: {', '.join(simlib.CLASSES)}")
    stub = None
    if args.stub:
        stub = simlib.Stub(args.cls, args.seed)
        simlib.install(stub)
    else:
        from llm import setup_check
        if not setup_check.server_up():
            die("Ollama is not running. Start the Ollama app, wait a few seconds, and run this again.")
        if not setup_check.model_present():
            die(f"The model {config.MODEL} is not downloaded: run  ollama pull {config.MODEL}  first.")
        from llm import embed
        embed.pull_in_background()
        from llm.gateway import warm
        warm()

    from engine import data_check, leveling
    problems = data_check.check()
    if problems:
        die("The game's data has problems:\n" + "\n".join(f"  - {p}" for p in problems))
    from world.loader import load_world
    from npc.traits import load_traits
    from npc import backfill
    from storage.campaign import CampaignStore, PlayerState
    from scenes.world import WorldScene
    from engine import turnlog

    world = load_world()
    rng = random.Random(args.seed)
    shutil.rmtree(f"saves/{save}", ignore_errors=True)
    store = CampaignStore.open_or_create(save)
    store.meta.seed, store.meta.turn, store.meta.minutes = args.seed, 1, 8 * 60
    store.save_meta()
    from engine import quests, starts
    if args.start not in starts.names():
        die(f"--start must be one of: {', '.join(starts.names())}")
    point = starts.spec(args.start)
    persona = args.persona or persona_for(args.seed)                        # (f368) the kind of player
    if persona not in PERSONAS:
        die(f"--persona must be one of: {', '.join(PERSONAS)}")
    level = int(point.get("level") or args.level)                       # (f367) the starting point's level, else --level
    char, spec = simlib.make_character(args.cls, rng, perks=True)
    if level > 1:
        leveling.level_up(char, level - 1)
        spend_points(char, spec)
        outfit(char, spec, level, rng)
    player = PlayerState(character=char, location=world.start_location)
    if level > 1:
        player.guild_rank = point.get("rank") or quests.letter_for_level(level)   # (f366) past the tutorial means a member: the board, contracts and the hall's notice are play
    store.save_player(player)
    catalog = load_traits()
    began = starts.apply(store, world, catalog, player, args.start, rng, char.name)     # (f367) the clock, the record, the town's memory of them
    ws = WorldScene(store, world, catalog, store.load_player())
    ws.player.mentor["never"] = True
    party = hire_party(ws, args.party)

    run = Run(out, args.hours, args.turns, live=not args.stub)
    bot = Bot(ws, world, random.Random(args.seed * 7 + 1), stub, persona=persona, run=run)
    run.bot = bot
    if stub is not None:
        stub.bot = bot
    run.install_console()
    run.install_client()
    print(f"Night run: {char.name}, {spec['name']}, level {char.level}, seed {args.seed}, playing as {persona}, starting as {args.start} ({point.get('text', '')}; "
          f"{began['met']} met, {len(began['situations'])} past situations), with " + (", ".join(f"{m['name']} the {m['role']}" for m in party) or "nobody") + f"; logs in {out}; "
          f"stops after {args.hours:g} h" + (f" or {args.turns} turns" if args.turns else "") + ". Ctrl+C stops it early.", flush=True)

    restarts = 0
    try:
        while True:
            try:
                ws.run()
                break
            except KeyboardInterrupt:
                run.reason = "stopped by hand"
                break
            except Exception as e:
                restarts += 1
                run.errors.write(f"--- turn {len(run.rows) + 1}: {type(e).__name__}: {e}\n{traceback.format_exc()}\n")
                run.errors.flush()
                print(f"error: {type(e).__name__}: {str(e)[:100]} (restart {restarts})", flush=True)
                if run.current is not None:
                    run.current["error"] = f"{type(e).__name__}: {str(e)[:200]}"
                    run.close_turn()
                if restarts >= 20:
                    run.reason = "too many errors (20)"
                    break
                ws.combat = None
                try:
                    ws.reload_after_rollback()
                except Exception:
                    pass
    finally:
        try:
            store.save_player(ws.player)
        except Exception:
            pass
        store.close()
        backfill.drop(store)
        turnlog.write_session_stats()
        texts = [r.get("text", "") for r in run.rows]
        run.finish({"character": char.name, "class": spec["name"], "level": ws.player.character.level, "deaths": ws.player.character.deaths, "seed": args.seed, "party": party,
                    "start": args.start, "start_days": began["days"], "past": began["situations"], "met_at_start": began["met"],
                    "persona": persona, "bot": bot.report(), "distinct": round(len(set(texts)) / len(texts), 3) if texts else 0,      # (f368)
                    "ended_by_player": ended_by_player(Path(config.PULSE_LOG_PATH)),
                    "save": save, "restarts": restarts, "stub": args.stub, "model": config.MODEL})
        if not args.stub:
            from llm.gateway import unload
            unload()
    import latency
    summary = latency.summarise(out)
    try:
        import world_report                                     # (f355) the world's side of the run, appended to summary.md
        world = world_report.summarise(out / "pulse.jsonl")
        if world:
            (out / "summary.md").write_text(summary + "\n" + world, encoding="utf-8")
            summary += "\n" + world
    except Exception as e:                                      # the summary is a convenience; a missing world log never fails the run
        print(f"world report skipped: {e}")
    print()
    print(summary)
    print(f"\nLogs: {out.resolve()}")


if __name__ == "__main__":
    main()
