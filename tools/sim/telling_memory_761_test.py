"""(f761) What the checks and prompts remember of the telling is kept across a close. Found by the audit (trace-replay-1): a save
closed and opened again was handed back only its last six passages, and everything else the checks and prompts read of what had
been written started empty at every launch: the worn-word watches (f349), the lines said in town for the house-voice guard (f350),
how the last passages after a fight began and what they opened on (f412), the exemplar draws (f583), which hires have had a frame
in this town (f347) and the partings heard lately (f347). For the first nine to thirty lines of each sitting the model was not told
which words it had worn out, and a phrase three people used before the break passed the check.

The kind: memory of what has been written that a check or a prompt reads on a later line. The opening's table (engine/actor.py
OPENING) keeps each such name in one row of the save, the telling, written with the operation that added to it and put back as the
scene is made. The case that found it: the worn prose words and the house phrase, before a close and after the open. Second cases
of the kind: how the last passages after a fight began, told to the next one after an open; every name the row keeps reads after
the open as it read at the close, and a damaged entry leaves only that memory to start empty; what the opening told before a first
line is kept when nothing is typed; an operation that fails takes back what it added, the row with it; after every line of a played
session the row holds what the scene remembers; the row is not state and never holds more than its caps after two hundred of each;
each of the eight noting sites, called alone, marks the row due itself, and every function that stores a name the row keeps on a
scene calls telling.noted (a census of the source); and a watch kept in its reduced form answers as one that kept the passages whole.
Run: python tools/sim/telling_memory_761_test.py"""
import ast
import io
import json
import random
import re
import sys
import time
from collections import deque
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, ".")
import simlib

stub = simlib.Stub("warrior", 7)
ASKED = []                                                   # every model call: (title, the last message)


def chat(**k):
    ASKED.append((k["format"].get("title", "?"), k["messages"][-1]["content"]))
    return simlib.Stub.chat(stub, **k)


stub.chat = chat
held = simlib.install(stub)
simlib.quiet_console()
sys.stdout = io.StringIO()                                   # the pane, the header and the fight's state: the checks print apart
import config
from engine import actor, combat, partings, pulse, quirks, voices, voice_rules, worn
from scenes import combat_scene as cs
from storage import statehash

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


NAME = Path(__file__).stem
LOGS = simlib.saves_path(f"{NAME}_logs")
LOGS.mkdir(parents=True, exist_ok=True)
config.CRASH_LOG_PATH, config.TURN_LOG_PATH = str(LOGS / "crash.log"), str(LOGS / "turns.jsonl")    # the faults made here stay here
try:
    from engine import telling
except ImportError:                                          # (before the row was built)
    telling = None
NAMES = {"_worn", "_said_in_town", "_after_starts", "_after_opened", "_exemplars", "_framed_hires", "_partings_heard"}
KEPT = {n for n, r in actor.OPENING.items() if r.fate == getattr(actor, "IN_SAVE", "") and r.why.split(":")[0] == "telling"}
check("the opening's table keeps what the checks and prompts remember of the telling in the save's telling row, and owes none of it",
      KEPT == NAMES and not [n for n in NAMES if actor.OPENING[n].fate == actor.OWED], (sorted(KEPT), {n: actor.OPENING[n].fate for n in NAMES}))


def memory(ws) -> dict:
    """What the scene remembers of the telling, by name, in a form two scenes are compared in (read here, not by the game's reader)."""
    d, out = ws.__dict__, {}
    if d.get("_worn"):
        out["_worn"] = {k: (len(getattr(w, "passages", getattr(w, "texts", ()))), sorted(w.counts().items()), w.worn()) for k, w in d["_worn"].items()}
    if d.get("_said_in_town") is not None:
        out["_said_in_town"] = [(t, who, sorted(g)) for t, who, g in d["_said_in_town"]]
    for n in ("_after_starts", "_after_opened", "_partings_heard"):
        if n in d:
            out[n] = list(d[n])
    if "_exemplars" in d:
        out["_exemplars"] = {k: list(v) if isinstance(v, (list, tuple)) else v for k, v in d["_exemplars"].items()}
    if "_framed_hires" in d:
        out["_framed_hires"] = sorted(d["_framed_hires"])
    return out


def row(store):
    return store._kv("telling")


def live(ws):
    """The live memory as the row would hold it (the game's own writer), or None before there was one."""
    return json.loads(json.dumps(telling.dump(ws))) if telling is not None else None


G = simlib.campaign(NAME, cls="warrior", seed=7, minutes=300, location="parth", char_seed=2)
G.player.character.level = 30
G.store.save_player(G.player)
G.scene.enter("parth")


def play(line, plan=None):
    stub.plan = [dict(p) for p in (plan or [{"kind": "look"}])]
    G.scene.turn(line)


def town(ws):
    return pulse.town_of(ws.world, ws.player.location)


# ---- the case that found it: the worn prose words and the house phrase, before a close and after the open
play("I look around.")
ws = G.scene
for i in range(5):                                           # through the scene's own noting (what remember_narration and a reply call)
    ws.note_worn(f"The steady rain falls on the quiet square, and a weary guard gives a faint nod. Passage {i}.")
for who in ("npc_a", "npc_b", "npc_c"):
    voices.heard(ws, town(ws), who, "Quiet enough, most days.")
play("I look around.")                                       # a line through the real turn: noted before it, kept with its commit
words, house = ws.worn_words("prose"), sorted(voices.house_phrases(ws, town(ws), "npc_d"))
check("(before the close: the prose watch has worn faint, quiet, steady and weary, and three people have said 'quiet enough most days')",
      words == ["faint", "quiet", "steady", "weary"] and house == ["quiet enough most days"], (words, house))
ws = G.reopen()                                              # closed, and opened again as main.py opens a save
check("after the open the prose watch still has them worn", ws.worn_words("prose") == words, ws.worn_words("prose"))
check("...and the house-voice guard still hears the phrase three people said before the close",
      sorted(voices.house_phrases(ws, town(ws), "npc_d")) == house, sorted(voices.house_phrases(ws, town(ws), "npc_d")))
ASKED.clear()
play("I look around.")
narr = [u for t, u in ASKED if t == "Narration"]
told = next((ln for u in narr for ln in u.splitlines() if ln.startswith("WORDS YOU HAVE WORN OUT")), "")
check("the first passage after the open is told the words it has worn out", told and all(w in told for w in words), told or [u[-400:] for u in narr])
n = ws.present[0] if ws.present else None
check("(someone of the town is here to talk to)", n is not None)
ASKED.clear()
play(f"I ask {n.label('player')} how things are.", [{"kind": "talk", "target": n.id, "speech": "How are things?"}])
sent_back = [u for t, u in ASKED if "is how everyone in this town has been talking lately" in u]
check("...and a fourth person's 'Quiet enough, most days.' after the open is sent back as how everyone here has been talking",
      sent_back and "quiet enough most days" in sent_back[0], [(t, u[-160:]) for t, u in ASKED][-6:])

# ---- a second case of the kind: how the last passages after a fight began, told to the next one after an open
AFTER = []
real_fresh = cs.fresh


def spy(task, system, request, *a, **k):
    if task == "combat_aftermath":
        AFTER.append(request)
    return real_fresh(task, system, request, *a, **k)


cs.fresh = spy


def won_fight():
    """A wolf fought here and every foe of it down: the fight's real end and its passage (CombatScene.finish)."""
    ws = G.scene
    creature = ws.world.bestiary["wolf"]
    sc = cs.CombatScene.begin(ws, creature, [combat.fighter_from_creature(creature, 3, "normal", "e1", name="wolf 1")], "It is on you:")
    ws.combat = sc
    for e in sc.fight.fighters:
        if e.side == "enemy":
            e.hp = 0
    sc.fight.over = "victory"
    sc.finish()


won_fight()
won_fight()
play("I look around.")
ws = G.scene
starts, opened = list(ws.__dict__.get("_after_starts") or []), list(ws.__dict__.get("_after_opened") or [])
check("(two fights won: how their passages began and what they opened on are remembered)", len(starts) == 2 and len(opened) == 2, (starts, opened))
ws = G.reopen()
AFTER.clear()
won_fight()
req = AFTER[-1] if AFTER else ""
head = next((ln for ln in req.splitlines() if ln.startswith("DO NOT BEGIN LIKE THESE")), "")
pick = next((ln[len("OPEN ON: "):] for ln in req.splitlines() if ln.startswith("OPEN ON: ")), None)
check("after the open, the next passage after a fight is told how the last ones began", head and all(s in head for s in starts), head or req[:300])
check("...and opens on none of the last ones' openings", pick is not None and pick not in opened[-int(combat.RULES["aftermath"]["not_again"]):],
      (pick, opened))

# ---- every name the row keeps reads after the open as it read at the close
ws = G.scene
ws.player.party = [{"id": "h1", "name": "Odly Garth", "role": "fighter", "level": 20, "permanent": True, "rank": "F", "bond": 12,
                    "pronoun": "she", "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "a sellsword",
                    "temper": ["blunt"], "motive": "coin", "line": "will not take from the poor"}]
quirks.roll(ws.player.party[0], random.Random(1))
ws.player.party_mode = "with"
ws.hire_frame_reasons(ws.player.party[0], "", False)        # her first words in this town earn a frame
partings.line(ws, ws.present[0], "Goodbye.")                # a parting heard
voices.heard(ws, town(ws), "npc_e", "The mill has been quiet since the frost, they say.")
play("I look around.")
ws = G.scene
at_close = memory(ws)
check("(at the close the scene remembers something under every name the row keeps)", set(at_close) == NAMES, sorted(NAMES - set(at_close)))
ws = G.reopen()
after = memory(ws)
check("every name the row keeps reads after the open as it read at the close", after == at_close,
      sorted(k for k in NAMES if after.get(k) != at_close.get(k)))
check("...so the hire framed before the close is not framed again in the same town", ws.hire_frame_reasons(ws.player.party[0], "", False) == [],
      ws.hire_frame_reasons(ws.player.party[0], "", False))
good = json.loads(json.dumps(row(G.store) or {}))
damaged = dict(good, _after_starts=[1, 2], _exemplars={**good.get("_exemplars", {}), "last:narration:general": 5})
opened = SimpleNamespace(store=SimpleNamespace(load_telling=lambda: damaged))
if telling is not None:
    telling.restore(opened)
got = memory(opened)
check("a damaged entry in the row leaves only that memory to start empty, and every other is read back as it was",
      telling is not None and set(got) == NAMES - {"_after_starts", "_exemplars"} and all(got[k] == at_close[k] for k in got), sorted(got))

# ---- what the opening tells before a first line is kept when nothing is typed
from ui import console
H = simlib.campaign(f"{NAME}_new", cls="warrior", seed=7, minutes=300, turn=0, location="parth", char_seed=2)
was = console.channel().get("ask")
console.put("ask", lambda *a, **k: "quit" if k.get("main", a[0] if a else False) else "yes")
H.scene.run()                                                # a new game's waking, as main.py plays it, and quit at the first prompt
console.put("ask", was)
first = memory(H.scene)
again = H.reopen()                                           # closed with nothing typed, and opened: it wakes again
prose = again.__dict__.get("_worn", {}).get("prose")
kept = len(getattr(prose, "passages", getattr(prose, "texts", ()))) if prose else 0
check("what the opening told before a first line is kept at a close with nothing typed (its passage, and the next waking's after it)",
      first.get("_worn", {}).get("prose", (0,))[0] == 1 and kept == 2, (first.get("_worn"), kept))
H.close()

# ---- an operation that fails takes back what it added, the row with it
ws = G.scene
store = G.store
row0, mem0 = row(store), memory(ws)
real_commit = store.commit_operation


def failing(op, *a, **k):
    if op.kind == "passage":
        raise RuntimeError("the game's own fault, after the row was written")
    return real_commit(op, *a, **k)


store.commit_operation = failing
play("I look around.")
store.commit_operation = real_commit
check("an operation that fails after writing the row takes it back: the row is as it was before the line", row(store) == row0)
check("...and so is what the scene remembers", memory(ws) == mem0, sorted(k for k in NAMES if memory(ws).get(k) != mem0.get(k)))
play("I look around.")
check("(the same line standing changes both)", row(store) != row0 and memory(ws) != mem0)

# ---- after every line of a played session the row holds what the scene remembers
LINES = [("I look around.", [{"kind": "look"}]),
         ("I ask how things are.", [{"kind": "talk", "target": "{0}", "speech": "How are things?"}]),
         ("Goodbye.", [{"kind": "look"}]),
         ("I wait a while.", [{"kind": "wait", "wait_minutes": 120}]),
         ("I ask about the roads.", [{"kind": "talk", "target": "{1}", "speech": "What are the roads like?"}]),
         ("I kneel and pray a while.", [{"kind": "pray"}]),
         ("I look around.", [{"kind": "look"}])]
apart = []
for i, (line, plan) in enumerate(LINES):
    ps = G.scene.present
    plan = [{k: (ps[int(v[1])].id if isinstance(v, str) and v.startswith("{") and len(ps) > int(v[1]) else v) for k, v in p.items()} for p in plan]
    play(line, plan)
    if telling is None or row(store) != live(G.scene):
        apart.append((i + 1, line))
check("after every line of a played session the row holds what the scene remembers", not apart, apart)
ws = G.scene
away = next(pid for pid, p in sorted(ws.world.places.items()) if p.type in ("town", "village") and pulse.town_of(ws.world, pid) != town(ws))
ws.enter(away)                                               # a new town: the hires framed are of the town left
play("I look around.")
check("...and a new town's hires are framed afresh in the row as on the scene", telling is not None and row(store) == live(G.scene)
      and (row(store) or {}).get("_framed_hires") == [], (row(store) or {}).get("_framed_hires"))
ws.enter("parth")

# ---- the row is not state: no digest, no revision
check("the row is named beside the presentation as not state", ("kv", "telling") in statehash.NOT_STATE_ROWS, statehash.NOT_STATE_ROWS)
d0, rev0 = statehash.digest(store), store.revision()
if telling is not None:
    G.scene.note_worn("One more passage, quietly told.")
    telling.save(G.scene)
check("...so writing it moves neither the state's digest nor the record's revision", telling is not None and statehash.digest(store) == d0
      and store.revision() == rev0 and row(store) == live(G.scene))

# ---- the row never holds more than its caps, after two hundred of each
ws = G.scene
sc = cs.CombatScene.begin(ws, ws.world.bestiary["wolf"], [combat.fighter_from_creature(ws.world.bestiary["wolf"], 3, "normal", "e1", name="wolf 1")], "It is on you:")
for i in range(200):
    ws.note_worn(f"Passage {i}: a wearily {random.Random(i).choice(['steady', 'quiet', 'faint'])} light on the {i}th stone, softly told.")
    ws.note_worn(f"said {i}", {"speech": f"Word {i}, quietly, as they say here, honestly.", "before": f"Before {i}.", "after": ""})
    voices.heard(ws, town(ws), f"npc_{i % 9}", f"Line {i} of the town and the long road home, number {i}.")
    sc.aftermath_opening()
    ws.exemplars("narration", random.Random(i).choice(["general", "night", "interior"]))
for i in range(12):
    sc.aftermath_now([], [], [], 0, "a wolf")
for i in range(14):
    partings.line(ws, ws.present[0], "Goodbye.")
ws.combat = None
t0 = time.perf_counter()
play("I look around.")
took = time.perf_counter() - t0
r = row(store) or {}
V, H_ = voice_rules.V["worn"], voices.V.get("house", {})
pools = sum(len(v) for v in voice_rules.V["exemplars"].values() if isinstance(v, dict)) + 1
caps = {"_worn": all(len(r.get("_worn", {}).get(k, [])) <= int(V["keep"]) for k in ("prose", "speech")),
        "_said_in_town": len(r.get("_said_in_town", [])) <= int(H_.get("window", 60)),
        "_after_starts": len(r.get("_after_starts", [])) <= 4, "_after_opened": len(r.get("_after_opened", [])) <= 6,
        "_partings_heard": len(r.get("_partings_heard", [])) <= 10, "_exemplars": len(r.get("_exemplars", {})) <= 2 * pools}
size = len(json.dumps(r, ensure_ascii=False))
print(f"     the row after two hundred of each: {size} characters; the line that wrote it {took:.2f} s", file=sys.__stdout__)
check("the row never holds more than its caps after two hundred passages, lines and draws", r and all(caps.values()),
      {k: v for k, v in caps.items() if not v})
check("...and holds each passage of a watch reduced, never its text", r and not any(isinstance(p, str) for k in ("prose", "speech")
                                                                               for p in r.get("_worn", {}).get(k, [])))

# ---- each noting site marks the row due itself, never left to another note made in the same call (an aftermath's exemplar draw
# and its passage mark it too); and every function of the game that stores a name the row keeps calls telling.noted, so a name or a
# site added later is held to it as well
MARKS = []
real_noted = telling.noted if telling is not None else None


def marking(scene):
    f = sys._getframe(1)
    MARKS.append(f"{Path(f.f_code.co_filename).stem}.{f.f_code.co_qualname}")
    real_noted(scene)


def marks(call) -> list:
    """The sites that marked the row due while `call` ran alone, the mark taken back first."""
    G.scene.__dict__.pop("_telling_due", None)
    MARKS.clear()
    call()
    return list(MARKS) if G.scene.__dict__.get("_telling_due", 0) > 0 else []


ws = G.scene
SITES = {"world.WorldScene.note_worn": lambda: ws.note_worn("A grey light lies over the square."),
         "world.WorldScene.exemplars": lambda: ws.exemplars("narration", "general"),
         "voices.heard": lambda: voices.heard(ws, town(ws), "npc_z", "The ferry has run late since the river rose."),
         "partings.line": lambda: partings.line(ws, ws.present[0], "Farewell."),
         "party_actions.PartyActions.hire_frame_reasons": lambda: ws.hire_frame_reasons({"name": "Wenna Holt"}, "", False),
         "world.WorldScene.enter": lambda: ws.enter(away),
         "combat_scene.CombatScene.aftermath_opening": sc.aftermath_opening,
         "combat_scene.CombatScene.aftermath_now": lambda: sc.aftermath_now([], [], [], 0, "a wolf")}
unmarked = {}
if telling is not None:
    telling.noted = marking
    try:
        unmarked = {site: got for site, call in SITES.items() if site not in (got := marks(call))}
    finally:
        telling.noted = real_noted
ws.enter("parth")
check("each of the eight noting sites, called alone, marks the row due itself", telling is not None and not unmarked, unmarked)


def notes(fn) -> bool:
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "noted"
               and isinstance(n.func.value, ast.Name) and n.func.value.id == "telling" for n in ast.walk(fn))


KEEPS = set(telling.names()) if telling is not None else set()
ROOT = Path(simlib.__file__).resolve().parent
storing, silent = set(), []
for folder in ("engine", "services", "scenes", "npc", "world", "storage", "ui", "llm"):
    for p in sorted((ROOT / folder).rglob("*.py")):
        for fn in [n for n in ast.walk(ast.parse(p.read_text(encoding="utf-8"))) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
            if simlib.stored_names(fn, ("self", "ws", "scene", "world_scene"), through=("ws",)) & KEEPS:
                storing.add(f"{p.relative_to(ROOT).as_posix()}:{fn.name}")
                if not notes(fn):
                    silent.append(f"{p.relative_to(ROOT).as_posix()}:{fn.name}")
FOUND = {"engine/partings.py:line", "engine/voices.py:heard", "scenes/combat_scene.py:aftermath_now", "scenes/combat_scene.py:aftermath_opening",
         "scenes/party_actions.py:hire_frame_reasons", "scenes/world.py:note_worn", "scenes/world.py:exemplars", "scenes/world.py:enter"}
check("...and a census of the source finds every function that stores a name the row keeps on a scene, the eight among them, "
      "and each calls telling.noted", KEEPS == NAMES and FOUND <= storing and not silent, (sorted(FOUND - storing), silent))

# ---- a watch kept reduced answers as one that kept each passage whole


class Whole:
    """The watch as it kept its passages before this change: the text whole (engine/worn.py at f349)."""

    def __init__(self, keep):
        self.texts = deque(maxlen=keep)
        self.seed = set(worn.W.get("seed", []))

    def add(self, text):
        if (text or "").strip():
            self.texts.append(text)

    def _names(self):
        caps, lower = set(), set()
        for t in self.texts:
            for m in re.finditer(r"(^|[.!?:;]\s+|[\"\u201c(]\s*)?([A-Za-z][a-z']+)", t):
                w = m.group(2)
                if w[0].islower():
                    lower.add(w.lower())
                elif m.group(1) is None:
                    caps.add(w.lower())
        return caps - lower

    def counts(self, keep=()):
        skip = {w.lower() for k in keep for w in worn._WORD.findall(k or "")} | worn.STOP
        names, out = self._names(), {}
        for t in self.texts:
            seen = set()
            for w in worn._WORD.findall(t):
                base = worn._stem(w.lower().strip("'"), self.seed)
                if base in seen or base in skip or base in names or len(base) < 4:
                    continue
                if base in self.seed or worn._suffixed(base):
                    seen.add(base)
            for b in seen:
                out[b] = out.get(b, 0) + 1
        return out

    def worn(self, keep=()):
        least, top = int(worn.W.get("least", 4)), int(worn.W.get("top", 8))
        if len(self.texts) < least:
            return []
        c = self.counts(keep)
        return [w for w, n in sorted(c.items(), key=lambda kv: (-kv[1], kv[0])) if n >= least][:top]


ex = voice_rules.V["exemplars"]
corpus = [l for v in ex.values() if isinstance(v, dict) for pool in v.values() for l in pool] + list(ex.get("fight") or [])
corpus += ["Quiet enough, most days.", "[scene 4]", "Like that, mostly. Ask me again tomorrow.", "'Steady,' she says. Steady hands.",
           "Berric leans on the post, steadily. \"Weary?\" Berric asks. (Quietly) the Weary Hound's sign creaks.",
           "O'Brien's dog. The folks' faces, wearily unreadable; folks' talk. Faintness: faint. Mr. Steady came. Ms. Quiet left.",
           "“Faintly,” he said; the Faint Road runs east. Up the Steady Stair: steadiness, weariness, unreadable expression.",
           "'tis the gate's own. Dark, darker, darkness; Silence. silence! Calm: calmly. The Calmness of the Calm Sea."]
rng = random.Random(11)
passages = corpus + [" ".join(rng.sample(corpus, 3)) for _ in range(120)]
keep = int(worn.W.get("keep", 30))
a, b = worn.Watch(), Whole(keep)
apart, scenes = [], [["Parth", "the stout gatekeeper"], [], ["Berric", "Steady Stair"], ["the Weary Hound"]]
for i, p in enumerate(passages):
    a.add(p)
    b.add(p)
    for k in scenes:
        if a.worn(k) != b.worn(k) or a.counts(k) != b.counts(k):
            apart.append((i, k, a.worn(k), b.worn(k)))
check(f"a watch kept reduced answers worn() and counts() as one that kept {len(passages)} passages whole, at every step", not apart, apart[:3])
c = worn.Watch()
for p in passages[:40]:
    c.add(p)
back = worn.Watch.load(c.rows()) if hasattr(worn.Watch, "load") else None
check("...and read back from its row it answers the same", back is not None and back.worn() == c.worn() and back.counts() == c.counts())

G.close()
held()
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
