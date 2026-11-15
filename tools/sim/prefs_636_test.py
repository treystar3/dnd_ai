"""(f636) A player's preferences on the actor (docs/design/20_phase3_plan.md; engine/actor.py Prefs).
#dialogue, #numbers and #debug flipped three flags on `config`, the process's: with a second player, one player's #debug would
have shown the engine's decisions on the other's screen and opened the debug commands to both. Held here:
- the three are one set the actor points at (Prefs), every actor's the process's one while a scene has one character, and a
  new set is as the game starts: no debug, the fight's numbers shown, conversations narrated;
- each command flips the preference of the actor whose turn it is and says so, in the words it used;
- everything that read a flag reads the preference: the debug lines, the gateway's rejections, the help, #pulse, #world,
  #levelup, the enchanter's absence, the window's status; the numbers under a round; a townsperson's, the mentor's and a
  companion's framed words and the party's exchange;
- two actors given preferences of their own keep them apart, a command flips its own actor's, and a thread no entry runs on
  has the process's;
- a preference is the player's for the run, as it was: a campaign's close puts none back and the session's residue names none;
- --debug at the start sets it (main.py options);
- the three names are gone from config, for a reader and a writer, and no file of the repository uses one: its code read
  as a syntax tree, and the text of every file of any kind.
Run: python tools/sim/prefs_636_test.py"""
import ast
import shutil
import subprocess
import sys
import threading
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import config
import ui.console as console
from engine import actor, combat, owned, session
from llm import gateway
from llm.contracts import ActionIntent
from scenes import combat_scene as cs
from scenes import voice
from ui.gui import bridge as bridge_mod

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

CALLS, PRINTED = [], []
for _name in ("narrate", "say", "npc_says", "dialogue", "ledger", "note", "combat_numbers", "wait", "out"):
    console.put(_name, lambda *a, _n=_name, **k: CALLS.append((_n, a)))
console.put("panel", lambda name, data: False)
console.put("print", lambda *a, **k: PRINTED.append(" ".join(str(x) for x in a)))
STATUS = ("Day 3, dusk", "light rain", "Trading Square, Parth", "a quiet corner", {"health": (40.4, 52), "mana": (0, 0), "stamina": (11.0, 40)},
          3, 2, 12345)

# ---- one set, the process's while no actor has its own
P = actor.prefs()
P.reset()
check("with no actor bound the preferences are the process's one set, and a scene's actor shares it", P is actor.PROCESS.prefs
      and actor.ActorContext().prefs is P)
new = actor.Prefs()
check("a new set is as the game starts: no debug, the fight's numbers shown, conversations narrated",
      (new.debug, new.numbers, new.dialogue) == (False, True, True) and list(actor.Prefs.FRESH) == ["debug", "numbers", "dialogue"] and new.held() == {},
      (vars(new), list(actor.Prefs.FRESH)))

# ---- the names are gone from config, for a reader and for a writer
GONE = {"DEBUG": "debug", "COMBAT_NUMBERS": "numbers", "NARRATED_DIALOGUE": "dialogue"}
for name, pref in GONE.items():
    said = []
    for act in (lambda: getattr(config, name), lambda: setattr(config, name, True)):
        try:
            act()
            said.append("")
            break                                          # the name is there: setting it would only break the rest
        except AttributeError as e:
            said.append(str(e))
    check(f"config.{name} is gone: reading it raises and says what to ask, and so does setting it",
          len(said) == 2 and all(f"config.{name}" in s and f"actor.prefs().{pref}" in s for s in said) and name not in vars(config), said)
was_tokens = config.MAX_TOKENS
config.MAX_TOKENS = was_tokens + 1
check("...and config's settings are read and set as they were", config.MAX_TOKENS == was_tokens + 1 and not hasattr(config, "NO_SUCH_SETTING"))
config.MAX_TOKENS = was_tokens

# ---- a scene
BASE = Path("saves/prefs_636")
g = simlib.campaign("prefs_636", cls="warrior", seed=5, location="parth")
ws = g.scene
config.TURN_LOG_PATH = str(BASE / "turns.jsonl")
ws.enter("parth")
check("a scene's actor has the process's preferences", ws.actor.prefs is P)


def notes(command: str) -> list[str]:
    CALLS.clear()
    ws.command(command)
    return [str(a[0]) for n, a in CALLS if n == "note"]


# ---- the commands flip the preference and say so
check("#debug flips the debug preference and says so", notes("#debug") == ["Debug mode on."] and P.debug is True
      and notes("#debug") == ["Debug mode off."] and P.debug is False, (CALLS, vars(P)))
check("#numbers flips whether the fight's numbers are shown", notes("#numbers") == ["Combat numbers hidden."] and P.numbers is False
      and notes("#numbers") == ["Combat numbers shown."] and P.numbers is True, (CALLS, vars(P)))
check("#dialogue flips whether conversations are narrated", notes("#dialogue") == ["Conversations shown as plain dialogue."] and P.dialogue is False
      and notes("#dialogue") == ["Conversations narrated."] and P.dialogue is True, (CALLS, vars(P)))

# ---- everything that read the debug flag reads the preference
ws.present = [n for n in ws.present if n.role != "enchanter"]


def debug_shown() -> bool:
    PRINTED.clear()
    console.debug("a decision")
    return any("[debug] a decision" in p for p in PRINTED)


def debug_readers() -> dict:
    out = {"the console's debug line": debug_shown()}
    PRINTED.clear()
    gateway._debug("a rejection")
    out["the gateway's rejection"] = any("a rejection" in p for p in PRINTED)
    kept, real_debug = [], console.now("debug")
    console.put("debug", lambda message: kept.append(message))        # a tool that keeps the debug lines whatever the preference
    gateway._debug("a rejection kept")
    console.put("debug", real_debug)
    out["...where a tool keeps the debug lines"] = kept == ["a rejection kept"]
    PRINTED.clear()
    console.show_help()
    out["the help's debug command"] = any("#levelup" in p for p in PRINTED)
    out["#pulse"] = not any("#pulse is a debug pane" in s for s in notes("#pulse"))
    out["#world"] = not any("#world is a debug command" in s for s in notes("#world"))
    level = ws.player.character.level
    ws.command("#levelup")
    out["#levelup"] = ws.player.character.level == level + 1
    CALLS.clear()
    ws.enchant_command("")
    out["enchanting with no enchanter"] = not any("no enchanter here" in str(a[0]) for n, a in CALLS if n == "note")
    b = bridge_mod.Bridge()
    b.status_block(*STATUS)
    out["the window's status"] = [ev["debug"] for _, ev in b.log if ev["k"] == "status"][-1]
    return out


off = debug_readers()
P.debug = True
on = debug_readers()
P.debug = False
check("with debug off nothing of it is shown or allowed", not any(off.values()), off)
check("with the preference on, every reader of it shows or allows it", all(on.values()), on)

# ---- conversations narrated or plain
asked = []
real_generate = voice.generate


def counting(task, *a, **k):
    asked.append(task)
    return real_generate(task, *a, **k)


voice.generate = counting
route = []
ws.narrate_dialogue = lambda *a, **k: route.append("narrated")
ws.show_speech = lambda *a, **k: route.append("plain")
smith = next(n for n in ws.residents if n.role == "smith")
ws.present = [smith] + [n for n in ws.present if n.id != smith.id]
hire = {"id": "h1", "name": "Odly Garth", "role": "fighter", "people": "human", "rank": "F", "blurb": "a sellsword with a dented shield", "level": 2,
        "bond": 12, "permanent": True, "pronoun": "she", "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": []}
ws.player.party = [hire]


def dialogue_readers() -> dict:
    out = {}
    route.clear()
    ws.on_talk(ActionIntent(kind="talk", target=smith.id, speech="Do you have arrows?"), "Do you have arrows?")
    out["a townsperson's words"] = route[-1:] == ["narrated"]
    ws._framed_here = set()
    asked.clear()
    ws.mentor_show("Then let's get you on the board.", reply_to="hello")
    out["the mentor's"] = "dialogue_frame" in asked
    asked.clear()
    ws.companion_show(hire, "We should move before dark.", reply_to="shall we go?", why=["the player spoke to them"])
    out["a companion's"] = "dialogue_frame" in asked
    asked.clear()
    ws.exchange_frame([["Odly Garth", "It will rain before dusk."]])
    out["the party's exchange"] = bool(asked)
    return out


on = dialogue_readers()
check("(the scene spoke: a townsperson was answered each time)", route[-1:] == ["narrated"], route)
P.dialogue = False
off = dialogue_readers()
check("...plainly, when conversations are not narrated", route[-1:] == ["plain"], route)
P.dialogue = True
check("with conversations narrated, every speaker's words are framed", all(on.values()), on)
check("with the preference off, none is: the words alone", not any(off.values()), off)
voice.generate = real_generate
del ws.narrate_dialogue, ws.show_speech

# ---- the numbers under a round
creature = ws.world.bestiary["bandit"]
foe = combat.fighter_from_creature(creature, 3, "normal", "e0", name="bandit 1")
foe.hp = foe.max_hp = 10 ** 5
ws.narrate_with = lambda *a, **k: None
sc = cs.CombatScene.begin(ws, creature, [foe], "It is on you:")
ws.combat = sc


def numbers_shown() -> int:
    CALLS.clear()
    sc.fight.story = ["you strike the bandit"]
    sc.narrate_round_now("I swing at the bandit")
    return [n for n, _ in CALLS].count("combat_numbers")


shown = numbers_shown()
P.numbers = False
hidden = numbers_shown()
P.numbers = True
check("a narrated round is followed by its numbers, and not when the preference is off", (shown, hidden) == (1, 0), (shown, hidden))
ws.combat = None

# ---- two actors keep theirs apart
mine, theirs = actor.Prefs(), actor.Prefs()
one, two = actor.ActorContext(prefs=mine), actor.ActorContext(prefs=theirs)
mine.debug, theirs.numbers = True, False
with actor.bind(one):
    first = (actor.prefs() is mine, debug_shown())
    elsewhere = []
    t = threading.Thread(target=lambda: elsewhere.append((actor.prefs() is P, debug_shown())))
    t.start()
    t.join()
with actor.bind(two):
    second = (actor.prefs() is theirs, debug_shown())
check("an actor with preferences of its own reads its own: one player's debug is not shown to another", first == (True, True) and second == (True, False)
      and (P.debug, P.numbers) == (False, True), (first, second, vars(P)))
check("...and a thread no entry runs on has the process's", elsewhere == [(True, False)], elsewhere)
own = ws.actor.prefs = actor.Prefs()
flipped = (notes("#debug"), notes("#numbers"), notes("#dialogue"))
inside = not any("#world is a debug command" in s for s in notes("#world"))
check("a command flips the preference of the actor whose turn it is, and no other's", (own.debug, own.numbers, own.dialogue) == (True, False, False)
      and (P.debug, P.numbers, P.dialogue) == (False, True, True) and flipped == (["Debug mode on."], ["Combat numbers hidden."],
                                                                               ["Conversations shown as plain dialogue."]), (vars(own), vars(P), flipped))
check("...and its turn reads it: the debug command it opened is open to it", inside and not debug_shown())
ws.actor.prefs = P

# ---- the player's for the run: no campaign's close puts one back
P.debug, P.numbers, P.dialogue = True, False, False
g.close()
session.reset()
named = [k for k in session.residue() if "pref" in k.lower() or "config" in k.lower()]
check("a preference is the player's for the run: a campaign's close puts none back, and the session's residue names none",
      (P.debug, P.numbers, P.dialogue) == (True, False, False) and not named and len(P.held()) == 3, (vars(P), named))
g = simlib.campaign("prefs_636", fresh=False)
again = g.scene
check("...nor does the next one's opening: its scene's actor has them as they were left", again.actor.prefs is P
      and (P.debug, P.numbers, P.dialogue) == (True, False, False), vars(P))
g.close()
ROWS = [f"engine.actor.Prefs.{n}" for n in actor.Prefs.FRESH]
check("each is a row of the table: the actor's, put back by the player alone; config has no row left for them",
      all(k in owned.STATE and owned.STATE[k].scope == owned.ACTOR and owned.STATE[k].put_back is None and "the player" in owned.STATE[k].resets for k in ROWS)
      and not [k for k in owned.STATE if k in {f"config.{n}" for n in GONE}], [k for k in owned.STATE if "Prefs" in k or k.startswith("config.")])
P.reset()

# ---- --debug at the start
import main
main.options(["--debug"])
started = P.debug
main.options([])
check("--debug at the start sets the first player's preference, and a start without it leaves debug off", (started, P.debug) == (True, False),
      (started, P.debug))


# ---- the fence: no file loads or stores one of the three on config
def uses(source: str) -> list[str]:
    """Every load or store of one of the three names in this source: an attribute of config under any name it was imported by,
    the name imported from it, the name handed to getattr, setattr, hasattr or delattr, or the two long names anywhere."""
    tree = ast.parse(source)
    alias, out = set(), []
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            alias |= {a.asname or a.name for a in n.names if a.name == "config"}
        elif isinstance(n, ast.ImportFrom) and n.module == "config":
            out += [f"line {n.lineno}: from config import {a.name}" for a in n.names if a.name in GONE or a.name == "*"]
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and n.attr in GONE and (n.attr != "DEBUG" or (isinstance(n.value, ast.Name) and n.value.id in alias)):
            out.append(f"line {n.lineno}: {ast.unparse(n)}")
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in ("getattr", "setattr", "hasattr", "delattr") and len(n.args) >= 2 \
                and isinstance(n.args[1], ast.Constant) and n.args[1].value in GONE \
                and (n.args[1].value != "DEBUG" or (isinstance(n.args[0], ast.Name) and n.args[0].id in alias)):
            out.append(f"line {n.lineno}: {ast.unparse(n)[:60]}")
    return out


CAUGHT = {
    "a read": "import config\nif config.DEBUG:\n    pass\n",
    "a store": "import config\nconfig.DEBUG = True\n",
    "a flip": "import config\nconfig.COMBAT_NUMBERS = not config.COMBAT_NUMBERS\n",
    "under another name": "import config as c\nx = c.DEBUG\n",
    "a read with a default": "import config\nx = getattr(config, 'DEBUG', False)\n",
    "a long name read with a default, whatever holds it": "x = getattr(settings, 'NARRATED_DIALOGUE', True)\n",
    "the name handed to setattr": "import config\nsetattr(config, 'DEBUG', True)\n",
    "the name imported": "from config import NARRATED_DIALOGUE\n",
    "two targets in one statement": "import config\nwas, config.DEBUG = config.DEBUG, False\n",
    "an import inside a function": "def f():\n    import config as _c\n    return _c.DEBUG\n",
}
PASSED = {
    "the preference": "from engine import actor\nif actor.prefs().debug:\n    actor.prefs().numbers = False\n",
    "another module's DEBUG": "import logging\nlevel = logging.DEBUG\n",
    "another setting of config": "import config\nconfig.MAX_TOKENS = 900\nx = getattr(config, 'VOICED_MENTOR', True)\n",
    "a word in a docstring": '"""config.DEBUG was the switch"""\n',
}
check("the fence catches every way one of the three is loaded or stored", all(uses(s) for s in CAUGHT.values()), [k for k, s in CAUGHT.items() if not uses(s)])
check("...and passes what is not one", not any(uses(s) for s in PASSED.values()), {k: uses(s) for k, s in PASSED.items() if uses(s)})
FILES = [Path(p) for p in subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.py"], capture_output=True, text=True,
                                         check=True).stdout.split()]
ME = Path(__file__).name
found, unread = {}, []
for p in FILES:
    if p.name == ME or not p.exists():
        continue
    try:
        got = uses(p.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        unread.append(str(p))
        continue
    if got:
        found[str(p)] = got
check("no file in the repository loads or stores one: the game, the tools, the tests", len(FILES) > 700 and not found and not unread,
      ({p: u[:3] for p, u in list(found.items())[:12]}, unread))
SPELT = ["-e", "COMBAT_NUMBERS", "-e", "NARRATED_DIALOGUE", "-e", r"config\.DEBUG", "-e", r"config, *['\"]DEBUG"]
MAY = {"engine/actor.py": "says where each went", f"tools/sim/{ME}": "this test", "docs/design/20_phase3_plan.md": "the plan"}
spelt = subprocess.run(["git", "grep", "-I", "-l", "--untracked", *SPELT], capture_output=True, text=True).stdout.split()
check("...and none of any kind spells one, in code held as text or in a page's script (but where the names are said to be gone)",
      sorted(spelt) == sorted(MAY), spelt)

shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
