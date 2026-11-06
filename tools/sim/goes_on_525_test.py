"""(f525) Creation and the opening go on through an outage, with lines laid over failures.yaml in the test (the owner reads the real
ones before f527 adds them; until then every path behaves as today).

- Every kind of call creation makes, failing every try in turn, still ends in a finished character; no line the player was shown
  speaks of the machinery or carries a dash.
- Every opening narration failing still reaches the first input, the same line for the same seed.
- A place's people that could not be written at the first entry are asked for again at the next input's edge, the player still there.
- (f525's review) A failed opening keeps what it was meant to tell; the goddess's stand-in keeps the engine's reason for a refused
  pick; the night's character is the seed's through an outage; no line list for a step she never speaks on.
- Without the lines laid over, behaviour is today's: the goddess's words failing ends creation, the opening failing ends the start,
  and creation's own notes are today's.

Run: python tools/sim/goes_on_525_test.py"""

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import simlib

stub = simlib.Stub("warrior", 3)
held = simlib.install(stub)

import ui.console as uc

SHOWN: list[str] = []
for f in ("narrate", "say", "npc_says", "dialogue", "ledger", "wait", "note", "out"):
    setattr(uc, f, (lambda name: lambda *a, **k: SHOWN.append(" ".join(str(x) for x in a)))(f))

from engine import failures, stats
from engine.failures import DASH, MACHINERY
from llm import backend
from llm.gateway import LLMError
from scenes.goddess import Step, ThresholdScene

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


OVERLAY = {
    "creation_fail": {k: [f"Her hand closes on nothing ({k}), and opens again. Tell it to her once more.",
                          f"The dark takes the {k} and gives it back unread. Say it again, child.",
                          f"It slips from her ({k}). Nothing is lost; say it once more."] for k in failures.CREATION_FAILS},
    "creation_stand_in": {s: [f"She waits, patient as stone ({s}).", f"Her eyes hold yours a while ({s}).",
                              f"She nods, and the dark nods with her ({s})."] for s in failures.CREATION_STEPS},
    "opening_untold": ["You wake on cold ground, breathing.", "Breath comes back to you, and with it the ground.",
                       "The world returns in a rush of air and earth."],
}


class Failing:
    """The stub, with every try of one kind of call failing a set number of times (the server away), each title counted. Two of
    creation's calls the stub cannot answer (reading the concept into a class, naming the fifteen abilities) are made here as creation
    makes them from what the stub's classes hold, failing the same way, as the gateway does once every try has failed."""

    def __init__(self, title: str | None, times: int = 6):
        self.title, self.left, self.titles = title, times, []

    def chat(self, **k):
        t = (k.get("format") or {}).get("title", "")
        self.titles.append(t)
        if t == self.title and self.left > 0:
            self.left -= 1
            raise ConnectionError("the server went away")
        return stub.chat(**k)

    def made(self, kind: str):
        self.titles.append(kind)
        if kind == self.title and self.left > 0:
            self.left -= 2                              # one creation step's call, failing every try
            raise LLMError(f"{kind}: no valid response")


import random as _random

from character import creation as _creation
from llm.contracts import ClassInterpretation
CURRENT: dict = {}


def _concept(concept, who=""):
    CURRENT["src"].made("concept")
    spec = simlib.CLASSES["warrior"]
    return ClassInterpretation(archetype=spec["archetype"], custom_class="Road Knight", combat_identity="x", themes=["roads"], summary="A knight of the roads.",
                               focus="balanced", families=spec["families"], primary_attributes=spec["primary"], casting_attribute=spec["casting"])


def _actives(interp, rng=None):
    CURRENT["src"].made("gifts")
    out, seen = [], set()
    for cls in simlib.CLASSES:
        if cls == "summoner":
            continue
        for a in simlib.make_character(cls, _random.Random(1))[0].actives:
            if a.name not in seen and a.effect.value not in ("command", "summon"):
                seen.add(a.name)
                out.append(a)
    return out[:15]


_creation.interpret_concept = _concept
_creation.generate_actives = _actives


def answer(s: ThresholdScene, said: dict) -> str:
    step = s.step
    said[step] = said.get(step, 0) + 1
    if said[step] > 12:
        return "#menu"                                  # a step asked a dozen times: stuck, so leave and let the check fail
    if step == Step.WHO:
        return "create:who {}"
    if step == Step.NAME:
        return "Ash" if said[step] == 1 else "create:name Ash"      # the first goes through the model's reading
    if step in (Step.CONCEPT, Step.CONFIRM_CLASS) and s.interp is None:
        return "create:calling a wandering knight of the old roads"
    if step == Step.CONFIRM_CLASS:
        return "create:confirm"
    if step in (Step.ACTIVES, Step.PASSIVES):
        return "create:picks 1 2 3"
    if step in (Step.STATS, Step.CONFIRM_STATS):
        return "create:stats " + json.dumps(stats.from_priorities(["strength", "vitality"]))
    return "#menu"


def create(title: str | None, overlay: bool = True):
    """One creation from the first page to the character, with `title` failing every try for a while."""
    src = Failing(title)
    CURRENT["src"] = src
    undo = backend.use(backend.StandIn(chat=src.chat, name="failing"))
    before = dict(failures.F)
    if overlay:
        failures.F.update(OVERLAY)
    SHOWN.clear()
    s = ThresholdScene()
    said: dict = {}
    uc.ask = lambda *a, **k: answer(s, said)
    try:
        got = s.run()
        err = None
    except LLMError as e:
        got, err = None, e
    finally:
        failures.F.clear()
        failures.F.update(before)
        undo()
    return got, err, list(SHOWN), src.titles


# ---- the kinds of call creation makes, from a run with nothing failing
clean, err, _, titles = create(None)
check("a creation with nothing failing finishes", clean is not None and err is None, err)
kinds = sorted(set(titles))
check("creation makes every kind of call it has", {"PlayerTurn", "GoddessLine", "concept", "gifts", "MechanicSet"} <= set(kinds), kinds)

# the owner's own beats (the opening and the send-off), fixed text a failure never writes: "answer" in "the ones who should answer" is
# the world's word, not the machinery's
AUTHORED = []
for f in ("opening.json", "send_off.json"):
    for row in json.loads((ROOT / "data" / f).read_text(encoding="utf-8")):
        AUTHORED += [part.strip() for part in str(row.get("text", "")).split("{name}") if part.strip()]


def authored(line: str) -> bool:
    return any(a in line for a in AUTHORED)


# ---- each kind failing in turn
for t in kinds:
    got, err, shown, _ = create(t)
    check(f"with every try of {t} failing for a while, creation still finishes", got is not None and err is None, err)
    leaks = [l for l in shown if MACHINERY.search(l) and "Character saved to" not in l and not authored(l)]
    check(f"no line shown speaks of the machinery ({t})", not leaks, leaks[:3])
    check(f"today's note never shows with the lines laid over ({t})", not any("The model couldn't" in l for l in shown),
          [l for l in shown if "The model couldn't" in l][:2])
    dashed = [l for l in shown if l in sum([sum(v.values(), []) if isinstance(v, dict) else v for v in OVERLAY.values()], []) and DASH.search(l)]
    check(f"no stand-in carries a dash ({t})", not dashed, dashed)

# ---- without the lines laid over: today's behaviour
got, err, shown, _ = create("GoddessLine", overlay=False)
check("without the lines, the goddess's words failing ends creation as before", got is None and isinstance(err, LLMError), err)
read_title = next((t for t in kinds if t not in ("GoddessLine",) and "PlayerTurn" in t), None)
if read_title:
    got, err, shown, _ = create(read_title, overlay=False)
    check("without the lines, creation's own note is today's", any("The model couldn't make sense of that" in l for l in shown), shown[-5:])
check("creation_line and the rest are None with no lines", failures.creation_line("interpret") is None
      and failures.creation_stand_in("name") is None and failures.opening_untold() is None)

# ---- the opening
import random


class Stop(Exception):
    pass


def opening(seed: int, fail: set, overlay: bool = True):
    """A new game's first entry and opening passage, with these kinds of call failing every try; stops at the first input."""
    shutil.rmtree("saves/goes_on_525", ignore_errors=True)
    src = Failing(None)

    def chat(**k):
        t = (k.get("format") or {}).get("title", "")
        if t in fail:
            raise ConnectionError("the server went away")
        return stub.chat(**k)
    undo = backend.use(backend.StandIn(chat=chat, name="failing opening"))
    before = dict(failures.F)
    if overlay:
        failures.F.update(OVERLAY)
    g = simlib.campaign("goes_on_525", seed=seed, turn=0)
    reached = {"n": 0}

    def ask(*a, **k):
        reached["n"] += 1
        raise Stop()
    uc.ask = ask
    SHOWN.clear()
    err = None
    try:
        g.scene.run()
    except Stop:
        pass
    except LLMError as e:
        err = e
    finally:
        failures.F.clear()
        failures.F.update(before)
        undo()
    shown = list(SHOWN)
    place = g.scene.player.location
    populated = g.session.store.load_place(place).populated
    return g, reached["n"], err, shown, populated


g1, n1, err1, shown1, _ = opening(5, {"Narration"})
g1.session.close()
check("the opening passage failing still reaches the first input", n1 == 1 and err1 is None, err1)
opened = [l for l in shown1 if l in OVERLAY["opening_untold"]]
check("the narrator's plain line stood in", len(opened) == 1, shown1[-6:])
g2, n2, err2, shown2, _ = opening(5, {"Narration"})
g2.session.close()
check("the same line for the same seed", [l for l in shown2 if l in OVERLAY["opening_untold"]] == opened)
g3, n3, err3, _, _ = opening(5, {"Narration"}, overlay=False)
g3.session.close()
check("without the lines the opening failing ends the start as before", n3 == 0 and isinstance(err3, LLMError), err3)

# ---- a place's people, entered outside a line (as the first entry is)
g4, n4, err4, _, _ = opening(6, set())
check("a clean opening reaches the first input", n4 == 1 and err4 is None, err4)


def resident_down(**k):
    if (k.get("format") or {}).get("title", "") == "ResidentSet":
        raise ConnectionError("the server went away")
    return stub.chat(**k)
undo = backend.use(backend.StandIn(chat=resident_down, name="residents down"))
err = None
try:
    g4.scene.enter("parth")
except LLMError as e:
    err = e
finally:
    undo()
check("people that could not be written at an entry outside a line leave the game going", err is None, err)
check("and the place is not counted as peopled", g4.session.store.load_place("parth").populated is False)
check("it is marked to be asked again while the player is there", g4.scene.__dict__.get("_people_missing") == "parth")
g4.scene.repopulate()
check("the next input's edge asks again, the player still there", g4.session.store.load_place("parth").populated is True
      and len(g4.scene.residents) > 0 and "_people_missing" not in g4.scene.__dict__)
import inspect
from scenes.world import WorldScene
check("and the run loop asks at each input's edge", "self.repopulate()" in inspect.getsource(WorldScene.run))

# ---- a failed opening keeps what it was meant to tell
OPEN_FAIL = {"Narration"}


def narration_down(**k):
    if (k.get("format") or {}).get("title", "") in OPEN_FAIL:
        raise ConnectionError("the server went away")
    return stub.chat(**k)


g4.scene._arrival_lines = ["the smith has moved on to the mill"]
seen_before = set(g4.scene.__dict__.get("_happenings_seen", set()))
before_f = dict(failures.F)
failures.F.update(OVERLAY)
undo = backend.use(backend.StandIn(chat=narration_down, name="narration down"))
try:
    g4.scene.opening_passage("The player is here, picking up where they left off.")
finally:
    undo()
    failures.F.clear()
    failures.F.update(before_f)
check("a failed opening keeps what it was meant to tell", g4.scene.__dict__.get("_arrival_lines") == ["the smith has moved on to the mill"]
      and set(g4.scene.__dict__.get("_happenings_seen", set())) == seen_before, g4.scene.__dict__.get("_arrival_lines"))
g4.scene.enter("parth")
check("the next visit asks for them again", g4.session.store.load_place("parth").populated is True
      and len(g4.session.store.load_place("parth").residents) > 0)
g4.session.close()
shutil.rmtree("saves/goes_on_525", ignore_errors=True)

# ---- the goddess's stand-in keeps the engine's reason for a refused pick
import types
src = Failing("GoddessLine", times=10)
CURRENT["src"] = src
undo = backend.use(backend.StandIn(chat=src.chat, name="goddess down"))
before_f = dict(failures.F)
failures.F.update(OVERLAY)
real_check = _creation.check_active_picks
_creation.check_active_picks = lambda options, picks, keeps_companions=False: "a command ability needs something to command."
SHOWN.clear()
try:
    s = ThresholdScene()
    s.step = Step.ACTIVES
    s.active_options = _actives(None)
    s.on_actives(types.SimpleNamespace(picks=[1, 2, 3]))
finally:
    _creation.check_active_picks = real_check
    failures.F.clear()
    failures.F.update(before_f)
    undo()
check("the goddess's stand-in keeps the engine's reason for a refused pick",
      any("That can't be done: a command ability needs something to command." in l for l in SHOWN)
      and any(any(x in l for x in OVERLAY["creation_stand_in"]["actives"]) for l in SHOWN) and s.step == Step.ACTIVES, SHOWN[-4:])

# ---- the night's character is the seed's through an outage
sys.path.insert(0, str(ROOT / "tools"))
import random as _r
import nightrun
tries = {"n": 0}


def make(r):
    tries["n"] += 1
    v = (r.random(), r.random())
    if tries["n"] == 1:
        raise ConnectionError("the server went away")
    return v


r1, r2 = _r.Random("night:warrior"), _r.Random("night:warrior")
got = nightrun.made_through_outage(make, r1, wait=lambda: True)
want = (r2.random(), r2.random())
check("the night's character is the seed's through an outage, the stream where it would be", got == want and r1.getstate() == r2.getstate()
      and tries["n"] == 2)
refused = None
try:
    nightrun.made_through_outage(lambda r: (_ for _ in ()).throw(ConnectionError("down")), _r.Random(1), wait=lambda: True, stub=True)
except ConnectionError:
    refused = "raised"
check("and a stub night never waits", refused == "raised")

# ---- no line list for a step she never speaks on
check("no line list for a step she never speaks on", "farewell" not in failures.CREATION_STEPS
      and any("farewell" in p for p in failures.problems({"creation_stand_in": {"farewell": ["One.", "Two.", "Three."]}})))

held()
print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
