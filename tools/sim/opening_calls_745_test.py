"""(f745) No model call on the way from the menu to the first input can stop a new game: the starting companion has an engine answer.

- A companion class's first waking (the kit not yet given), with every kind of call it makes failing every try in turn, StartingKit
  among them, reaches the first input with its companion and its weapon; a weapon class through the same loop, so a call added to
  the opening later with no engine answer fails here.
- The companion the engine had to choose is one of the kit's own options, called by its kind as a tamed one is, and the narrator is
  not told a name it was never given.
- An answer that names a creature off the list on every try ends in the engine's pick, not the end of the game.
- The same seed picks the same creature; the die is the campaign's (another seed can pick another), not the input's.
- A call stopped on purpose (Cancelled) is never answered for: it reaches the caller.

Run: python tools/sim/opening_calls_745_test.py"""

import random
import re
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
    uc.put(f, (lambda name: lambda *a, **k: SHOWN.append(" ".join(str(x) for x in a)))(f))

from character import kit
from engine import streams
from llm import backend
from llm.errors import Cancelled
from llm.gateway import LLMError
from storage import saves

bad: list[str] = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"  {detail}"))
    if not ok:
        bad.append(name)


def good_kit(u, k):
    """The model answering from the lists: the first weapon listed, the first creature listed, named Rook."""
    weapon = re.search(r"WEAPON OPTIONS:\n\s+(\S+):", u).group(1) if "WEAPON OPTIONS" in u else ""
    comp = re.search(r"COMPANION OPTIONS:\n\s+(\S+):", u)
    return {"weapon": weapon, "companion": comp.group(1) if comp else "", "companion_name": "Rook" if comp else ""}


def off_list(u, k):
    """The weapon from the list, the creature by a name of its own and not by its id, on every try."""
    out = good_kit(u, k)
    if out["companion"]:
        out["companion"] = "a grey wolf"
    return out


def title(k) -> str:
    return (k.get("format") or {}).get("title", "")


class Stop(Exception):
    pass


SAVE = "opening_calls_test"


def first_waking(cls: str, companions: bool, fail: set = frozenset(), seed: int = 5, answer=good_kit, steps: int = 0):
    """A new game's first run() up to its first input, its kit not yet given, every try of the titles in `fail` failing; `steps` is the
    count of inputs taken that the opening's own dice begin from."""
    stub.a_StartingKit = answer
    titles, told = [], []

    def chat(**k):
        t = title(k)
        titles.append(t)
        if t == "Narration":
            told.append(" ".join(str(m.get("content", "")) for m in k.get("messages", [])))
        if t in fail:
            raise ConnectionError("the server went away")
        return stub.chat(**k)
    undo = backend.use(backend.StandIn(chat=chat, name="opening"))
    g = simlib.campaign(SAVE, cls=cls, seed=seed, turn=0)
    if steps:
        g.store.meta.steps = steps
        g.store.save_meta()
    c = g.player.character
    c.kit_given, c.uses_companions, c.companions, c.equipment, c.coins, c.start_weapon = False, companions, [], {}, 0, ""
    g.store.save_player(g.player)
    reached = {"n": 0}

    def ask(*a, **k):
        reached["n"] += 1
        raise Stop()
    uc.put("ask", ask)
    SHOWN.clear()
    err = None
    try:
        g.scene.run()
    except Stop:
        pass
    except LLMError as e:
        err = e
    finally:
        undo()
    out = dict(reached=reached["n"], err=err, titles=titles, told=told, shown=list(SHOWN),
               saved=g.store.load_player().character, world=g.world)
    g.session.close()
    saves.drop(SAVE)
    return out


def armed(c) -> bool:
    return any(kit.items.base_of(i).is_weapon for i in c.equipment.values())


def companion_of(run):
    comps = run["saved"].companions
    return comps[0] if len(comps) == 1 else None


# ---- the companion class: a ranger who keeps a beast, the model answering
clean = first_waking("ranger", True)
check("a companion class's first waking, the model answering, reaches the first input", clean["reached"] == 1 and clean["err"] is None,
      clean["err"])
comp = companion_of(clean)
check("...with the companion the model named and a weapon", comp is not None and comp.name == "Rook" and armed(clean["saved"])
      and clean["saved"].kit_given, (comp, list(clean["saved"].equipment)))
check("the kit ask is on the opening path", "StartingKit" in clean["titles"], sorted(set(clean["titles"])))
kinds = sorted({t for t in clean["titles"] if t})
check("the loop below fails every kind of call the opening makes, the narrator's among them", {"StartingKit", "Narration"} <= set(kinds),
      kinds)

# ---- every kind of call the opening makes, failing every try in turn (the case that found it: StartingKit)
OPTIONS = {b.id for b in kit.companion_options(clean["world"])}
for t in kinds:
    run = first_waking("ranger", True, {t})
    check(f"with every try of {t} failing, a companion class still reaches the first input", run["reached"] == 1 and run["err"] is None,
          run["err"])
    comp = companion_of(run)
    check(f"...its kit given and saved, a companion and a weapon with it ({t})", run["saved"].kit_given and comp is not None
          and armed(run["saved"]), (run["saved"].kit_given, comp, list(run["saved"].equipment)))

# ---- the engine's pick, when the kit ask fails
down = first_waking("ranger", True, {"StartingKit"})
comp = companion_of(down)
if comp is not None:
    creature = down["world"].bestiary.get(comp.creature)
    check("the companion the engine chose is one of the kit's own options", comp.creature in OPTIONS, comp.creature)
    check("...called by its kind, as a tamed one is", creature is not None and comp.name == creature.name, (comp.name, comp.creature))
    check("...bonded before the player woke, as the model's would be", comp.source == "bonded before the player woke"
          and comp.description == f"a {creature.name.lower()}", (comp.source, comp.description))
    opening = [m for m in down["told"] if "bonded to them" in m]
    check("the narrator hears of the creature and is told no name", opening and f"{creature.name.lower()} is with them" in opening[0]
          and " named " not in opening[0].split("bonded to them")[0][-80:], opening[:1])
else:
    check("the engine chose a companion when the kit ask failed", False, down["saved"].companions)
named = [m for m in clean["told"] if "bonded to them" in m]
check("while the model's name still reaches the narrator", named and "named Rook" in named[0], named[:1])

# ---- an answer off the list on every try
off = first_waking("ranger", True, answer=off_list)
check("an answer naming a creature off the list on every try still reaches the first input", off["reached"] == 1 and off["err"] is None,
      off["err"])
comp = companion_of(off)
check("...and ends in the engine's pick", comp is not None and comp.creature in OPTIONS and comp.name != "Rook", comp)

# ---- the same seed, the same creature; the campaign's die, not the input's
again = first_waking("ranger", True, {"StartingKit"})
check("the same seed picks the same creature twice", companion_of(again) is not None and companion_of(down) is not None
      and companion_of(again).creature == companion_of(down).creature, (companion_of(again), companion_of(down)))
later = companion_of(first_waking("ranger", True, {"StartingKit"}, steps=9))
check("...and at another count of inputs taken, the same creature: not the opening's input dice", later is not None
      and companion_of(down) is not None and later.creature == companion_of(down).creature, (later, companion_of(down)))
picks = set()
for s in (5, 11, 12, 13):
    comp = companion_of(first_waking("ranger", True, {"StartingKit"}, seed=s))
    picks.add(comp.creature if comp else None)
check("another seed can pick another creature", None not in picks and len(picks) > 1, picks)

# ---- a weapon class through the same loop
plain = first_waking("warrior", False)
check("a weapon class's first waking reaches the first input", plain["reached"] == 1 and plain["err"] is None, plain["err"])
for t in sorted({t for t in plain["titles"] if t} | {"StartingKit"}):
    run = first_waking("warrior", False, {t})
    check(f"with every try of {t} failing, a weapon class still reaches the first input, armed", run["reached"] == 1 and run["err"] is None
          and run["saved"].kit_given and armed(run["saved"]) and not run["saved"].companions, run["err"])

# ---- a call stopped on purpose is never answered for
c, _ = simlib.make_character("ranger", random.Random(1))
c.kit_given, c.uses_companions, c.companions, c.equipment, c.coins, c.start_weapon = False, True, [], {}, 0, "shortbow"


def stopped(**k):
    if title(k) == "StartingKit":
        raise Cancelled("the session is closing")
    return stub.chat(**k)


undo = backend.use(backend.StandIn(chat=stopped, name="cancelled"))
got = None
try:
    kit.give_starting_kit(c, "Pathstalker (rogue): x", True, clean["world"], streams.fixed(5, "kit", c.id))
except Cancelled:
    got = "cancelled"
except Exception as e:                  # noqa: BLE001 (the test reports what came out instead)
    got = type(e).__name__
finally:
    undo()
check("a Cancelled raised inside the kit ask reaches the caller", got == "cancelled" and not c.companions, (got, c.companions))

held()
print(f"\n{'ALL PASS' if not bad else f'{len(bad)} FAILED: ' + ', '.join(bad)}")
sys.exit(1 if bad else 0)
