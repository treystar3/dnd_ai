"""(f751) An opening by declaration: every name the world scene holds says what an opening does with it, and a session closed and
opened part-way is held equal to the same session played straight. Found by the audit (trace-replay-2): nothing compared the two, so
a feature that kept something a later line reads on the scene alone passed its own test, and the loss showed only when a player
stopped for the night (the talk, a crafting boost, what a resumed fight was for, a pending errand, the day's cap on people ruled in,
the worn words, the hire who spoke last, a moment rolled again at the open).

engine/actor.py OPENING declares, beside ATTRS, every row of ATTRS and every private name set on a scene: kept in a row of the save
(which), made again from the save at the open, forgotten (why), or owed: meant to be kept by the owner's default and lost today, with
the feature that keeps it. The turn's fields need no row: a line sets each before it reads it.

Checked two ways. The census (the walk of f720, simlib.scene_names): every such name has a fate, no row is of a name nothing sets,
each forgotten or owed row says why, and what is owed only falls (the ratchet of f450). By running, under the stand-in model: a
script played once straight, forgetting what is declared forgotten and what is owed (simlib.Game.forget) where the other run closes
the game and opens it again as main.py opens a save (simlib.Game.reopen), each input's state, operations, requests and shown words
compared: a name lost that is not declared lost parts them. What an opening shows and asks before its first prompt is held apart (it
is not an input, f721): no model call, and nothing the straight session had not shown but its own lines. Openings where the bot
never closes: in the middle of a talk and of a fight, with a question standing, with an act waiting for its ruling, and stopped
between a commit and its telling. A case known to differ names the feature that removes the difference and the shape of every
difference it may show, and the list only shrinks.
Run: python tools/sim/reopen_declared_751_test.py"""
import ast
import collections
import contextlib
import inspect
import io
import json
import re
import sys
import textwrap
import time
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
import config
from core.interrupts import Interrupt
from engine import actor, failures, leveling, mapview, recording
from scenes.world import WorldScene
from storage import saves
from ui import console

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


recording.prune = lambda *a, **k: None                  # the owner's recordings are never pruned by a test
O = getattr(actor, "OPENING", {})
FATES = tuple(getattr(actor, k, k) for k in ("IN_SAVE", "REMADE", "FORGOTTEN", "OWED"))
fate = lambda k: {n for n, r in O.items() if r.fate == getattr(actor, k, k)}

# ---- the census
own, outside, computed = simlib.scene_names()
names = {n for n in set(own) | set(outside) if n != "<computed>"}
private = {n for n in names if n.startswith("_")}
view = lambda n: isinstance(inspect.getattr_static(WorldScene, n, None), property)
check("the census finds the scene's rows and its private names", len(actor.ATTRS) >= 40 and len(private) >= 50, (len(actor.ATTRS), len(private)))
undeclared = sorted((set(actor.ATTRS) | private) - set(O))
check("every row of ATTRS and every private name set on a scene says what an opening does with it", not undeclared, undeclared)
check("...and the table holds nothing else: no field of the turn, no property, no name nothing sets",
      O and not [n for n in O if n in actor.FIELDS or view(n) or n not in names], sorted(n for n in O if n in actor.FIELDS or view(n) or n not in names))
check("each is kept in a row of the save, made again from the save, forgotten or owed, and says which row, from what or why",
      O and all(r.fate in FATES and r.why.strip() for r in O.values()), sorted(n for n, r in O.items() if r.fate not in FATES or not r.why.strip()))
OWED_NOW = 11                                            # (the ratchet) a name kept by a feature that lands is taken off the count
WHO = re.compile(r"(RELOAD|STALE_COPIES)-\d+$|reported$")
check("what is owed names who keeps it (a feature of the plan, or reported to the owner) and what a player meets",
      all(WHO.match(r.why.split(":")[0]) and r.why.split(":", 1)[1:] for n, r in O.items() if n in fate("OWED")),
      sorted(n for n, r in O.items() if n in fate("OWED") and not (WHO.match(r.why.split(":")[0]) and r.why.split(":", 1)[1:])))
check("...and only falls: a name its feature keeps is taken off the count", len(fate("OWED")) == OWED_NOW, (len(fate("OWED")), OWED_NOW, sorted(fate("OWED"))))
init = simlib.stored_names(ast.parse(textwrap.dedent(inspect.getsource(WorldScene.__init__))), ("self",))
cleared = fate("FORGOTTEN") | fate("OWED")
check("a forgotten or owed name the scene's constructor sets says what a new scene holds, so forgetting it is what an opening does",
      not [n for n in cleared if n in init and O[n].fresh is None], sorted(n for n in cleared if n in init and O[n].fresh is None))

# ---- by running: the audit's scripts, straight and closed and opened
simlib.quiet_console()


class Run:
    """One session through the real turn under the stand-in model: straight, or closed and opened again at the inputs `at`. `at`
    holds input counts, or ("fight", n): the first input from n on that is played in a fight. Each part of the session is recorded
    (engine/recording.py); its rows are read back per input: (line, state, operations, requests, shown)."""

    def __init__(self, name: str, seed: int, script: str, at=(), reopen: bool = False, setup=None, most: int = 160, crash=None):
        self.name, self.seed, self.script, self.at, self.reopen, self.setup, self.most = name, seed, script, list(at), reopen, setup, most
        self.crash = crash                               # (input, kind): closed there by a stop after that kind's commit, not a quit
        self.n, self.fight_lines, self.again, self.first, self.crashes = 0, 0, False, True, 0
        self.openings: list[dict] = []
        self.forgot: list = []
        self.parts: list[Path] = []
        self.fault, self.keys_left, self.acts_at_close = "", [], []

    # -- the player's lines (the scripts the audit of trace-replay-2 played)
    def people(self):
        return list(self.g.scene.present)

    def top_here(self):
        return mapview.top_of(self.g.world, self.g.scene.player.location)

    def inside(self, kind):
        top = self.top_here()
        return next((pid for pid, p in self.g.world.places.items() if p.type == kind and mapview.top_of(self.g.world, pid) == top), "")

    def wild_near(self):
        here, w = self.g.scene.player.location, self.g.world
        for pid in w.neighbors(here) + w.neighbors(self.top_here()):
            p = w.places.get(pid)
            if p is not None and p.danger and p.type != "dungeon":
                return pid
        return ""

    def other_town(self):
        for pid, _ in sorted(mapview.graph(self.g.world).get(self.top_here(), {}).items(), key=lambda kv: (kv[1], kv[0])):
            if self.g.world.places[pid].type in ("town", "city", "village"):
                return pid
        return ""

    def s_town(self):
        yield "I look around.", [{"kind": "look"}]
        for k in range(3):
            ps = self.people()
            if k < len(ps):
                n = ps[k]
                yield f"I ask {n.label('player')} whether there is any work going.", [{"kind": "talk", "target": n.id, "speech": "Is there any work going?"}]
                yield "I'll take the job.", [{"kind": "work", "target": n.id}]
                yield "I'll do what you asked.", [{"kind": "accept_quest", "target": n.id}]
                yield f"I ask {n.label('player')} what the news is.", [{"kind": "talk", "target": n.id, "speech": "What news is there in town?"}]
        n = next((x for x in self.people() if self.g.scene.wares_of(x)), None)
        if n is not None:
            w = self.g.scene.wares_of(n)[0]
            ware = getattr(w, "name", "") or getattr(w, "item", "")
            yield "I haggle over the price.", [{"kind": "haggle", "target": n.id, "ware": ware}]
            yield "I buy it.", [{"kind": "buy", "target": n.id, "ware": ware}]
            yield "I slip something off the stall.", [{"kind": "steal", "target": n.id, "item": "a trinket"}]
        yield "I kneel and pray a while.", [{"kind": "pray"}]
        yield "I climb onto the roof to look over the town.", [{"kind": "other", "summary": "climb onto the roof"}]
        hall = self.inside("guild")
        if hall:
            yield "I walk to the guild hall.", [{"kind": "move", "destination": hall}]
            yield "I want to join the guild.", [{"kind": "join_guild"}]
            yield "I read the contract board.", [{"kind": "board"}]
            yield "I take the first contract.", [{"kind": "accept_quest", "item": "1"}]
            ps = self.people()
            if ps:
                yield "I ask for training.", [{"kind": "train", "target": ps[0].id, "item": "a new strike"}]
                yield "The first one.", [{"kind": "learn_ability", "item": "1"}]
        for kind in ("inn", "tavern", "temple", "market", "smithy"):
            pid = self.inside(kind)
            if pid:
                yield f"I walk to the {kind}.", [{"kind": "move", "destination": pid}]
                yield "I look around.", [{"kind": "look"}]
                ps = self.people()
                if ps:
                    yield "I say hello.", [{"kind": "talk", "target": ps[0].id, "speech": "Hello there. How are things?"}]
                    yield "I ask about the roads.", [{"kind": "talk", "target": ps[0].id, "speech": "What are the roads like? Where should I go?"}]
                    if len(ps) > 1:
                        yield "I play a round of dice.", [{"kind": "gamble", "target": ps[1].id, "item": "2 silver"}]

    def s_days(self, n=10):
        for k in range(n):
            yield "I wait out the day.", [{"kind": "wait", "wait_minutes": 16 * 60}]
            if k % 3 == 2:
                yield "I look around.", [{"kind": "look"}]
                ps = self.people()
                if ps:
                    yield "I ask what has been happening.", [{"kind": "talk", "target": ps[0].id, "speech": "What has been happening while I was away?"}]

    def s_wild(self):
        w = self.wild_near()
        if w:
            yield "I head out to the wild.", [{"kind": "move", "destination": w}]
        for k in range(3):
            yield "I gather what herbs I can find.", [{"kind": "forage"}]
            yield "I search for game.", [{"kind": "search"}]
            if getattr(self.g.scene, "wildlife", None):
                creature, foes = self.g.scene.wildlife
                yield f"I attack the {creature.name.lower()}.", [{"kind": "attack", "target": foes[0].name}]
            yield "I skin what I killed.", [{"kind": "harvest"}]
            yield "I follow the stream to see where it leads.", [{"kind": "explore", "seek": "a hidden spring"}]
        yield "I make camp and sleep until morning.", [{"kind": "wait", "wait_until": "morning"}]
        yield "I look around.", [{"kind": "look"}]

    def s_travel(self):
        t = self.other_town()
        if t:
            yield f"I set out for {self.g.world.places[t].name}.", [{"kind": "move", "destination": t}]
            for k in range(6):
                if self.top_here() == t:
                    break
                yield "I keep walking.", [{"kind": "move", "destination": t}]
            yield "I look around.", [{"kind": "look"}]
            ps = self.people()
            if ps:
                yield "I greet them.", [{"kind": "talk", "target": ps[0].id, "speech": "Good day. I've just come in off the road."}]

    def s_back(self):
        start = mapview.top_of(self.g.world, self.g.world.start_location)
        yield "I head back.", [{"kind": "move", "destination": start}]
        for k in range(6):
            if self.top_here() == start:
                break
            yield "I keep walking.", [{"kind": "move", "destination": start}]

    def s_asked(self):
        yield "I look around.", [{"kind": "look"}]
        yield "I throw away the old iron key.", [{"kind": "discard", "item": "Old Iron Key"}]
        yield "Yes.", [{"kind": "look"}]
        yield "I look around.", [{"kind": "look"}]
        yield from self.s_days(3)

    def s_act(self):
        yield "I look around.", [{"kind": "look"}]
        yield "I climb onto the roof to look over the town.", [{"kind": "other", "summary": "climb onto the roof"}]
        yield "I look around.", [{"kind": "look"}]
        yield from self.s_days(3)

    def lines(self):
        parts = {"town": [self.s_town, self.s_days, self.s_wild, self.s_travel, self.s_days, self.s_town],
                 "travel": [self.s_travel, self.s_town, self.s_days, self.s_back, self.s_town],
                 "wild": [self.s_wild, self.s_wild, self.s_travel, self.s_wild]}.get(self.script) or [getattr(self, f"s_{self.script}")]
        for p in parts:
            yield from p()

    # -- the session
    def choose(self, u, k):
        """The fight's intent: the nearest foe, or away when low."""
        from engine import pools
        ws = self.g.scene
        foes = ws.combat.fight.enemies() if ws.combat is not None else []
        me = ws.player.character
        if pools.current(me, "health") < 0.3 * pools.maximum(me, "health"):
            return {"kind": "flee"}
        return {"kind": "attack", "target": foes[0].id if foes else ""}

    def ask(self, *a, **k):
        if not k.get("main", a[0] if a else False):
            return "yes"
        ws = self.g.scene
        if self.first:                                   # what the opening showed before its first prompt is its own, not the next input's
            rec = self.g.session.recorder
            self.openings.append({"shown": list(rec.shown), "n": self.n})
            rec.shown.clear()
            self.first = False
        fighting = ws.combat is not None and not ws.combat.fight.over
        due = self.at and (self.n >= self.at[0] if isinstance(self.at[0], int) else (self.n >= self.at[0][1] and fighting))
        if due:
            self.at.pop(0)
            if self.reopen:
                from engine import act
                self.acts_at_close = act.waiting(ws, ws.acting)
                self.again = True
                return "quit"
            self.forgot.append((self.n, self.g.forget(owed=True)))      # straight: what an opening forgets, and what it loses today
        if self.crash and self.reopen and self.n + 1 == self.crash[0]:
            ws.crash_after_commit = self.crash[1]        # this line stops the game after that commit: the stop is this run's close
            self.at.pop(0)
        self.n += 1
        if self.n > self.most:
            return "quit"
        if fighting:
            self.fight_lines += 1
            return "quit" if self.fight_lines > 60 else "I strike at the nearest of them."
        try:
            text, plan = next(self.gen)
        except StopIteration:
            return "quit"
        self.stub.plan = plan
        return text

    def folder(self) -> Path:
        p = simlib.saves_path(self.name, f"rec_{len(self.parts)}")
        self.parts.append(p)
        return p

    def play(self) -> "Run":
        for c in (simlib.NAME_COUNTER, simlib.NARR_COUNTER, simlib.MOMENT_COUNTER):
            c[0] = 0
        self.stub = simlib.Stub("warrior", self.seed)
        held = simlib.install(self.stub)
        self.stub.ask_help = True
        self.stub.a_CombatIntent = self.choose
        self.stub.a_LootName = lambda u, k: {"name": "Reeve's Spur", "description": "A spur with a notched rowel, taken from the fields."}
        config.TURN_LOG_PATH = str(simlib.saves_path(self.name, "turns.jsonl"))
        self.g = g = simlib.campaign(self.name, cls="warrior", seed=self.seed, minutes=8 * 60 + 600 * 1440)
        try:
            c = g.player.character
            leveling.level_up(c, 5)
            c.coins = 5000
            g.player.guild_rank = "F"
            g.store.save_player(g.player)
            ws = g.scene
            hall, was = ws.guild_place_id(), ws.player.location
            ws.player.location = hall
            try:
                picks = ws.party_roster()[:2]
            finally:
                ws.player.location = was
            ws.player.character.coins += sum(m["fee"] for m in picks)
            with g.store.transaction():
                for m in picks:
                    ws.party_service.hire(m, ws.player.character.level)
            ws.enter(ws.player.location)
            if self.setup:
                self.setup(self, ws)
            g.store.save_player(ws.player)
            self.gen = self.lines()
            with contextlib.redirect_stdout(io.StringIO()):
                while True:
                    console.put("ask", self.ask)                    # under the recorder, which wraps what answers as it is installed
                    g.reopen(opening=False, record=self.folder())   # closed, and opened again as main.py opens a save
                    self.again, self.first = False, True
                    try:
                        g.scene.run()
                    except Interrupt:                        # stopped between a commit and its telling (f467): opened again
                        self.again, self.crashes = True, self.crashes + 1
                    if not self.again:
                        break
            self.keys_left = list(g.scene.player.character.key_items)
        except Exception as e:                           # the session's own fault is the test's finding, not its crash
            import traceback
            self.fault = f"{type(e).__name__}: {e} | " + traceback.format_exc().strip().splitlines()[-3][:200]
        finally:
            g.close()
            held()
        self.rows = self.read()
        saves.drop(self.name)
        return self

    def read(self) -> list[dict]:
        rows = []
        for k, rec in enumerate(self.parts):
            calls = collections.defaultdict(list)
            for c in recording.read_calls(rec):
                calls[c["input"]].append(c)
            turns = {t["i"]: t for t in map(json.loads, (rec / "turns.jsonl").read_text(encoding="utf-8").splitlines()) if t}
            if k < len(self.openings):
                self.openings[k]["calls"] = [c.get("title") for c in calls.get(0, [])]
            for inp in map(json.loads, (rec / "inputs.jsonl").read_text(encoding="utf-8").splitlines()):
                if not inp["main"] or inp["text"].strip().lower() == "quit":
                    continue
                t = turns.get(inp["i"]) or {}
                rows.append({"text": inp["text"], "state": t.get("state") or {}, "ops": [(o["id"], o["kind"]) for o in t.get("operations") or []],
                             "reqs": [c["req"] for c in calls.get(inp["i"], [])], "titles": [c.get("title") for c in calls.get(inp["i"], [])],
                             "calls": calls.get(inp["i"], []), "shown": t.get("shown_text") or [], "part": k, "rows": t.get("rows") or {}})
        return rows


def differ(a: dict, b: dict) -> list[str]:
    """What two rows of the same input part on, in words."""
    out = []
    if a["state"].get("all") != b["state"].get("all"):
        flat = lambda r: {f"{t}.{how}.{key}": json.dumps(v, sort_keys=True, default=str) for t, hows in r.items() for how, keys in (hows or {}).items()
                          for key, v in (keys.items() if isinstance(keys, dict) else [("", keys)])}
        fa, fb = flat(a["rows"]), flat(b["rows"])
        moved = sorted(k + (f" {fb.get(k, '')[:60]}" if k in fb else " (straight only)") for k in set(fa) | set(fb) if fa.get(k) != fb.get(k))
        out.append("state " + ",".join(t for t in a["state"] if t != "all" and a["state"][t] != b["state"].get(t)) + (f" (this input wrote apart: {moved[:6]})" if moved else ""))
    if a["ops"] != b["ops"]:
        out.append(f"operations {[k for _, k in a['ops']]} / {[k for _, k in b['ops']]}")
    if a["reqs"] != b["reqs"]:
        if a["titles"] != b["titles"]:
            out.append(f"calls {a['titles']} / {b['titles']}")
        else:
            ca, cb = next((x, y) for x, y in zip(a["calls"], b["calls"]) if x["req"] != y["req"])
            ma = "\n".join(m["content"] for m in ca["request"].get("messages", [])).splitlines()
            mb = "\n".join(m["content"] for m in cb["request"].get("messages", [])).splitlines()
            only = [f"-{l[:110]}" for l in ma if l not in mb][:2] + [f"+{l[:110]}" for l in mb if l not in ma][:2]
            out.append(f"request {ca.get('title')} {only}")
    if a["shown"] != b["shown"]:
        out.append("shown words")
    return out


def compare(label: str, seed: int, script: str, at, setup=None, most: int = 160, crash=None) -> dict:
    """The session straight and closed and opened at `at`: {"parted": ..., "inputs": n, "differ": {i: [...]}, "openings": [...]}."""
    t0 = time.perf_counter()
    a = Run(f"reopen_declared_{label}_a", seed, script, at, reopen=False, setup=setup, most=most, crash=crash).play()
    b = Run(f"reopen_declared_{label}_b", seed, script, at, reopen=True, setup=setup, most=most, crash=crash).play()
    out = {"faults": [x.fault for x in (a, b) if x.fault], "inputs": (len(a.rows), len(b.rows)), "differ": {}, "parted": None,
           "openings": b.openings[1:], "first": (a.openings[:1], b.openings[:1]), "forgot": a.forgot, "a": a, "b": b}
    for i, (ra, rb) in enumerate(zip(a.rows, b.rows)):
        if ra["text"] != rb["text"]:
            out["parted"] = (i + 1, ra["text"], rb["text"])
            break
        d = differ(ra, rb)
        if d:
            out["differ"][i + 1] = d
    out["seconds"] = round(time.perf_counter() - t0, 1)
    print(f"     [{label}] {out['inputs'][0]} inputs, opened again at {list(at)}, {out['seconds']} s: "
          f"{len(out['differ'])} differ{', parted at ' + str(out['parted'][0]) if out['parted'] else ''}", file=sys.__stdout__)
    for i, d in sorted(out["differ"].items())[:8]:
        print(f"       input {i} ({a.rows[i - 1]['text'][:40]!r}): {' | '.join(d)[:400]}", file=sys.__stdout__)
    for o in out["openings"]:
        print(f"       opening at input {o['n']}: calls {o.get('calls')} shown {[s[:60] for s in o['shown']]}", file=sys.__stdout__)
    return out


# (the list only shrinks) A case known to differ: the feature that removes the difference, what a player meets, and the shape of every
# difference it may show (a difference of another shape fails the case). A case that no longer differs fails until it leaves the list.
KNOWN = {}
OWN_LINES = ("You are still in the middle of a fight!", *failures.F["shown_later"])   # what an opening says of its own, beside what was shown


def held(label: str, key: str, out: dict) -> None:
    """The case's comparison: equal, or (a case on KNOWN) differing only in the shape its feature names; and its openings make no
    model call and show nothing the straight session had not shown, but their own lines."""
    whole = not out["faults"] and not out["parted"] and out["inputs"][0] == out["inputs"][1] and out["inputs"][0] > 5
    check(f"{label}: closed and opened, the session plays the same lines to its end", whole, {k: out[k] for k in ("faults", "inputs", "parted")})
    a = out["a"]
    for o in out["openings"]:
        before = {s for r in a.rows[:o["n"]] for s in r["shown"]} | {s for x in a.openings for s in x["shown"]} | set(OWN_LINES)
        check(f"{label}: the opening at input {o['n']} makes no model call and shows only what was shown before",
              not o.get("calls") and set(o["shown"]) <= before, (o.get("calls"), [s[:80] for s in o["shown"] if s not in before]))
    if key not in KNOWN:
        check(f"{label}: every input ends in the same state, with the same operations, requests and words", not out["differ"],
              dict(list(out["differ"].items())[:4]))
        return
    feature, meets, shape, after_open = KNOWN[key]
    first = {o["n"] + 1 for o in out["openings"]}
    other = {i: [x for x in d if not re.match(shape, x) or (after_open and i not in first)] for i, d in out["differ"].items()}
    other = {i: d for i, d in other.items() if d}
    check(f"{label}: known to differ until {feature} ({meets}), and in nothing else", out["differ"] and not other,
          "it no longer differs: take it off the list" if not out["differ"] else dict(list(other.items())[:4]))


# ---- the case that found it: the travel script at seed 11, opened at inputs 7 and 14
travel = compare("travel", 11, "travel", (7, 14), most=16)
held("the travel script, seed 11, opened at 7 and 14", "travel", travel)

# ---- the second case of the kind: the town script at seed 7, opened at 9 (in the middle of a talk) and at 40
town = compare("town", 7, "town", (9, 40))
held("the town script, seed 7, opened at 9 and 40", "town", town)

# ---- opened in the middle of a fight
fight = compare("fight", 5, "wild", (("fight", 3),), most=40)
check("(the fight case opened the game in the middle of a fight)", fight["openings"] and any("middle of a fight" in " ".join(o["shown"]) for o in fight["openings"]),
      [o["shown"][:3] for o in fight["openings"]])
held("the wild script, seed 5, opened in the middle of a fight", "fight", fight)


# ---- opened with a question standing
def old_key(run, ws):
    from core.models import KeyItem
    ws.player.character.key_items.append(KeyItem(id="old_key", name="Old Iron Key", day=1))


asked = compare("asked", 7, "asked", (2,), setup=old_key)
check("(the question was standing at the close, and the opening asks it again)",
      any("Discard it for good?" in " ".join(o["shown"]) for o in asked["openings"]), [o["shown"] for o in asked["openings"]])
check("...and the answer after the open is taken as the answer", not any(k.name == "Old Iron Key" for k in asked["b"].keys_left), asked["b"].keys_left)
held("a question standing at the close", "asked", asked)


# ---- opened with an act waiting for its ruling (f596)
def ruling_down_at_2(run, ws):
    real = run.stub.a_ActRuling

    def down(u, k):
        if run.n == 2:                                   # the second line's ruling cannot be made, every try of it
            from llm.gateway import LLMError
            raise LLMError("the model is down")
        return real(u, k)
    run.stub.a_ActRuling = down


acted = compare("act", 7, "act", (2,), setup=ruling_down_at_2)
check("(an act was waiting for its ruling at the close)", acted["b"].acts_at_close, acted["b"].acts_at_close)
held("an act waiting for its ruling at the close", "act", acted)


# ---- the game stopped between a commit and its telling (f467), and opened again
crashed = compare("crash", 7, "town", (9,), crash=(9, "tail"), most=14)      # the line's last operation, and its party's words held
lost = [s for s in crashed["a"].rows[8]["shown"] if s not in crashed["b"].rows[8]["shown"]] if len(crashed["b"].rows) > 8 else ["?"]
check("(the game stopped after the tail of input 9 stood, before its words were shown)", crashed["b"].crashes == 1 and lost, (crashed["b"].crashes, lost))
check("...what stood and was never shown is shown by the opening", all(any(s in o["shown"] for o in crashed["openings"]) for s in lost),
      (lost, [o["shown"] for o in crashed["openings"]]))
crashed["differ"][9] = [x for x in crashed["differ"].get(9, []) if x != "shown words"]    # the stopped input's words: the opening showed them
crashed["differ"] = {i: d for i, d in crashed["differ"].items() if d}
held("stopped between a commit and its telling", "crash", crashed)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
