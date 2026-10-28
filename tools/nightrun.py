"""Plays a campaign with the real model for hours and logs what every turn cost: a run for a machine left on overnight.

    python tools/nightrun.py [--hours 6] [--turns 0] [--class warrior] [--level 13] [--seed 1] [--out DIR] [--stub]
    nightrun.bat --hours 6                 (Windows: the same, through the game's own Python environment)

A bot plays the way a player types - a word with whoever is here, a walk to the next place, a look at the board, an improvised
try, a fight when one comes - choosing its lines from the scene's state with a seed, and the real model reads them. The run keeps
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
        self.transcript.write((f"**{who}:** " if who else "") + text.strip() + "\n\n")

    def noted(self, text: str) -> None:
        if HESITATION in text:
            self.hesitations += 1
            if self.current is not None:
                self.current["hesitated"] = True
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
        self.sub_answers = 0
        self.current = {"n": len(self.rows) + 1, "time": datetime.now().isoformat(timespec="seconds"), "kind": kind, "text": text,
                        "where": self.bot.where(), "turn": self.bot.ws.store.meta.turn, "level": self.bot.c.level,
                        "hp": round(self.bot.hp(), 2), "combat": bool(self.bot.ws.combat)}
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


class Bot:
    """Types what a player would, from what the scene shows: who is here, where the roads go, how the character is doing."""

    QUESTIONS = ["What's been happening around here lately?", "Do you know of any work going?", "What do you make of the roads these days?",
                 "Who runs things in this town?", "Tell me about yourself.", "Any news from the other towns?", "What should a stranger steer clear of here?"]
    TOPICS = ["the town", "work", "the road ahead", "the news", "their trade", "the weather lately"]
    IMPROV = ["I fish in the river for supper.", "I whistle an old marching tune.", "I climb the nearest tree for a look around.",
              "I carve a mark into the signpost.", "I try my luck at a game of dice.", "I practise sword forms for an hour.",
              "I sketch the view in my notebook.", "I check my boots for wear and mend a strap."]
    SEARCH = ["I carefully search the area for tracks.", "I look around.", "I listen for anything unusual.", "I take a good look at the people here."]
    LEAVE = ["Thanks, I'll let you get on.", "That's all I wanted to know. Good day.", "I'd best be moving on."]

    def __init__(self, ws, world, rng: random.Random, stub=None):
        self.ws, self.world, self.rng, self.stub = ws, world, rng, stub
        self.talks = 0                               # lines said in the conversation open now
        self.spoken_to: collections.deque = collections.deque(maxlen=6)
        self.been: collections.deque = collections.deque(maxlen=8)
        self.here_for = 0                            # turns spent at this place
        self.asked_hires: dict = {}                  # companion name -> the game day they were last asked how they are
        self.last_loc = ""
        self.last_text = ""
        from engine import actions
        self.kinds = set(getattr(actions, "KINDS", ()) or ())

    @property
    def c(self):
        return self.ws.player.character

    def hp(self) -> float:
        from engine import pools
        return self.c.health / max(1, pools.maximum(self.c, "health"))

    def where(self) -> str:
        return self.world.places[self.ws.player.location].name

    def intend(self, kind: str, **fields) -> dict:
        """The plan the stand-in interpreter answers with (the real model reads the words); an unknown kind becomes a look."""
        return {"kind": kind if kind in self.kinds else "look", **fields}

    def decide(self) -> tuple[str, str]:
        text, intent, kind = self.choose()
        same = self.__dict__.setdefault("_same", collections.deque(maxlen=4))
        same.append(text)
        if len(same) == same.maxlen and len(set(same)) == 1:              # the same line four times running is a loop, whatever it is: break it
            same.clear()
            if self.ws.combat:
                alive = [e for e in self.ws.combat.fight.enemies() if e.alive]
                tgt = min(alive, key=lambda e: e.hp) if alive else None
                text, intent, kind = (f"I attack {tgt.name}." if tgt else "I attack."), {"kind": "attack", "target": tgt.id if tgt else "", "summary": "bot"}, "fight"
            else:
                text, intent, kind = "I look around.", self.intend("look"), "look"
        if self.stub is not None:
            self.stub.plan = [intent]
        self.last_text = text
        loc = self.ws.player.location
        self.here_for = self.here_for + 1 if loc == self.last_loc else 0
        self.last_loc = loc
        if loc not in self.been:
            self.been.append(loc)
        return text, kind

    def choose(self) -> tuple[str, dict, str]:
        ws, rng = self.ws, self.rng
        c = self.c
        loc = ws.player.location
        p = self.world.places[loc]
        hp = self.hp()
        if ws.combat:
            return self.fight_line()
        if getattr(ws, "pending_clarify", None):
            return "I look around.", self.intend("look"), "look"
        if ws.partner is not None:
            self.talks += 1
            if self.talks <= rng.choice((2, 3)):
                q = rng.choice(self.QUESTIONS)
                return f'"{q}"', self.intend("talk", target=ws.partner.id, speech=q), "talk"
            self.talks = 0
            return rng.choice(self.LEAVE), self.intend("leave_conversation"), "leave"
        tired = c.fatigue >= 60 or c.hunger >= 60
        if hp < 0.5 or tired:
            return self.rest_line(p)
        present = [n for n in ws.present if n.id not in self.spoken_to]
        options: list[tuple[int, str]] = []
        in_town = p.danger is None
        if present:
            options.append((35 if in_town else 15, "talk"))
        options.append((15 if in_town and self.here_for < 4 else 40, "move"))
        if p.type == "guild":
            options.append((20, "board"))
        if p.type in ("shop", "smithy", "workshop", "inn"):
            options.append((15, "shop"))
        options += [(10, "improv"), (8 if in_town else 20, "search"), (5, "wait")]
        from engine import clock as _clock
        today = _clock.day(ws.minutes)
        unasked = [m for m in ws.player.party if self.asked_hires.get(m.get("name")) != today]
        if unasked:
            options.append((8, "hire"))                 # a check-in at most once a game day per companion: a real player does not nag
        pick = rng.choices([o[1] for o in options], weights=[o[0] for o in options])[0]
        if pick == "talk":
            n = rng.choice(present)
            self.spoken_to.append(n.id)
            self.talks = 1
            topic = rng.choice(self.TOPICS)
            q = rng.choice(self.QUESTIONS)
            return f"I go over to {n.label()} and ask about {topic}.", self.intend("talk", target=n.id, speech=q), "talk"
        if pick == "move":
            return self.move_line(p)
        if pick == "board":
            text = rng.choice(["I read the contract board.", "I ask the clerk what contracts are open for my rank.", "I look over the board for a job I can take."])
            return text, self.intend("look"), "board"
        if pick == "shop":
            text = rng.choice(["I look over the wares.", "I ask what a good blade would cost me.", "I order a meal and listen to the talk."])
            return text, self.intend("look"), "shop"
        if pick == "improv":
            text = rng.choice([t for t in self.IMPROV if t != self.last_text])
            return text, self.intend("other", summary=text), "improv"
        if pick == "search":
            text = rng.choice(self.SEARCH)
            return text, self.intend("search" if "search" in text else "look"), "search"
        if pick == "hire":
            m = rng.choice(unasked)
            self.asked_hires[m.get("name")] = today
            return f"I ask {m.get('name', 'my companion')} how they're holding up.", self.intend("look"), "hire"
        return "I wait an hour.", self.intend("wait", wait_minutes=60), "wait"

    def move_line(self, p) -> tuple[str, dict, str]:
        rng, world = self.rng, self.world
        level = self.c.level
        here = p.id
        near = [x for x in world.neighbors(here) if x in world.places]
        def safe(x):
            d = world.places[x].danger
            return d is None or d[1] <= level + 6
        local = [x for x in near if safe(x) and (world.places[x].parent == here or x == p.parent or (p.parent and world.places[x].parent == p.parent))]
        roads = [x for x in near if safe(x) and x not in local]
        fresh = lambda xs: [x for x in xs if x not in self.been] or xs
        if local and (not roads or rng.random() < 0.65):
            dest = rng.choice(fresh(local))
            text = rng.choice([f"I walk over to {world.places[dest].name}.", f"I head to {world.places[dest].name}."])
        elif roads:
            dest = rng.choice(fresh(roads))
            text = rng.choice([f"I set out for {world.places[dest].name}.", f"I take the road to {world.places[dest].name}."])
        else:
            return "I look around.", self.intend("look"), "look"
        return text, self.intend("move", destination=dest), "move"

    def rest_line(self, p) -> tuple[str, dict, str]:
        if p.type == "inn":
            return "I take a room and sleep until morning.", self.intend("wait", wait_until="dawn"), "rest"
        inn = next((x for x in self.world.neighbors(p.id) if self.world.places[x].type == "inn"), None)
        if inn and p.danger is None:
            return f"I walk over to {self.world.places[inn].name}.", self.intend("move", destination=inn), "move"
        return "I make camp and rest until morning.", self.intend("wait", wait_until="dawn"), "rest"

    # ---- a fight: the same choices a player makes, said as a player says them
    def fight_line(self) -> tuple[str, dict, str]:
        choice = self.combat_choice()
        f = self.ws.combat.fight
        target = next((e for e in f.enemies() if e.id == choice.get("target")), None)
        name = target.name if target else "the nearest enemy"
        kind = choice["kind"]
        if kind == "item":
            return "I drink a healing draught.", {}, "fight"
        if kind == "flee":
            return "I run for it.", {}, "fight"
        if kind == "ability":
            move = next((m for m in f.player.moves if m.id == choice["ability"]), None)
            if move:
                return f"I use {move.name} on {name}.", {}, "fight"
        return self.rng.choice([f"I attack {name}.", f"I strike at {name}.", f"I go for {name}."]), {}, "fight"

    def combat_choice(self) -> dict:
        """The decision as a CombatIntent (the stand-in model answers with it; the words above are what the real one reads)."""
        from engine import combat
        f = self.ws.combat.fight
        p = f.player
        enemies = [e for e in f.enemies() if e.alive]
        if not enemies:
            return {"kind": "attack", "target": "", "summary": "bot"}
        tgt = min(enemies, key=lambda e: e.hp)
        hpf = p.hp / max(1, p.max_hp)
        base = {"target": tgt.id, "summary": "bot"}
        if hpf < 0.5 and f.item_round != f.round and any(i.good == "healing_draught" for i in self.c.inventory):
            return dict(base, kind="item", item="healing draught")           # one a round: the game refuses a second, and the bot once drank 1,155 times running
        if (hpf < 0.35 and f.round > 1) or (len(enemies) >= 3 and f.round == 1 and any(e.rank != "normal" for e in enemies)):
            return dict(base, kind="flee")
        usable = [m for m in p.moves if not combat.can_use(p, m, f)]
        if hpf < 0.5:
            for m in usable:
                if m.effect == "healing":
                    return dict(base, kind="ability", ability=m.id)
        if hpf < 0.6 and f.round > 1:
            for m in usable:
                if m.effect == "defense" and m.id not in p.buffs:
                    return dict(base, kind="ability", ability=m.id)
        damage = [m for m in usable if m.effect == "damage"]
        if damage and self.rng.random() < 0.7:
            return dict(base, kind="ability", ability=self.rng.choice(damage).id, move="closer")
        return dict(base, kind="attack", move="closer")


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
    args = ap.parse_args()

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
    char, spec = simlib.make_character(args.cls, rng, perks=True)
    if args.level > 1:
        leveling.level_up(char, args.level - 1)
        spend_points(char, spec)
        outfit(char, spec, args.level, rng)
    store.save_player(PlayerState(character=char, location=world.start_location))
    ws = WorldScene(store, world, load_traits(), store.load_player())
    ws.player.mentor["never"] = True
    party = hire_party(ws, args.party)

    run = Run(out, args.hours, args.turns, live=not args.stub)
    bot = Bot(ws, world, random.Random(args.seed * 7 + 1), stub)
    run.bot = bot
    if stub is not None:
        stub.bot = bot
    run.install_console()
    run.install_client()
    print(f"Night run: {char.name}, {spec['name']}, level {char.level}, seed {args.seed}, with " + (", ".join(f"{m['name']} the {m['role']}" for m in party) or "nobody") + f"; logs in {out}; "
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
        run.finish({"character": char.name, "class": spec["name"], "level": ws.player.character.level, "deaths": ws.player.character.deaths, "seed": args.seed, "party": party,
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
