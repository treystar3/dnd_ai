"""(f579) What the console writes, pinned as text. Every function of ui/console.py that prints is called with fixed arguments and what
reaches stdout is compared, character for character, with a kept copy (tools/sim/fixtures/console_bytes_579.json). The kept recordings
cannot hold this: their shown-words hash is taken from the calls, never from stdout. The foundations bundle puts an output channel
under these functions (docs/design/13_foundations_design.md f580); this is what that move must leave as it was: the blank lines, the
indents, the wrapping, the one print that ends without a newline.
The functions that draw a character's sheet read the game's data, so their text is compared only while the data is the data the copy was
taken on (the data hash); after a data change the test says so and compares the rest. Whatever the data, every function must write
exactly what the built-in print writes for the calls it makes, so the sheets stay pinned too. To take a new copy after a change that is meant
to alter what the player reads: python tools/sim/console_bytes_579_test.py --write
Run: python tools/sim/console_bytes_579_test.py"""
import ast
import contextlib
import io
import json
import random
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
import ui.console as console
from core.models import Archetype
from engine import items
from llm.contracts import ClassInterpretation
from storage import statehash

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

KEPT = Path(__file__).resolve().parent / "fixtures" / "console_bytes_579.json"
LONG = ("The ferry is late again and nobody on the landing is surprised; the ferryman's boy sits on a coil of rope, counting gulls, while "
        "two carters argue over whose turn it was to bring the lantern down from the toll house.")


def shown(fn) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):                # the way the window and every capturing tool take the console's text
        fn()
    return buf.getvalue()


def debug_on(message):
    was, config.DEBUG = config.DEBUG, True
    try:
        console.debug(message)
    finally:
        config.DEBUG = was


def debug_off(message):
    was, config.DEBUG = config.DEBUG, False
    try:
        console.debug(message)
    finally:
        config.DEBUG = was


# ---- arguments alone decide these
PLAIN = {
    "say": lambda: console.say("Horseshoes. Nails.\n(She wipes her hands on her apron.)\n" + LONG, "Brannoch"),
    "say, no speaker": lambda: console.say("Mind the mud."),
    "narrate": lambda: console.narrate("Rain on the thatch.\n\n" + LONG),
    "npc_says": lambda: console.npc_says("Ost the smith", LONG, "sets the tongs down"),
    "npc_says, no gesture": lambda: console.npc_says("Ost", "Ask the city for swords."),
    "dialogue": lambda: console.dialogue("She looks up from the ledger.", "Maren", LONG, "She goes back to it."),
    "dialogue, speech alone": lambda: console.dialogue("", "Maren", "No.", " "),
    "debug, on": lambda: debug_on("event judge: Trouble -> no"),
    "debug, off": lambda: debug_off("event judge: Trouble -> no"),
    "out": lambda: console.out("Saved. Until next time."),
    "out, nothing": lambda: console.out(),
    "setup_progress, part": lambda: console.setup_progress(0.5, "Waking the model"),
    "setup_progress, done": lambda: console.setup_progress(1.0, "Waking the model"),
    "wait": lambda: console.wait("the world turns"),
    "busy_text": lambda: console.busy_text("People go about their day."),
    "note": lambda: console.note("You are carrying too much to run."),
    "ledger": lambda: console.ledger("12 silver paid"),
    "header": lambda: console.header("The Trading Square"),
    "_section": lambda: console._section("PEOPLE YOU'VE MET"),
    "show_journal": lambda: console.show_journal([LONG, "The   mill  is  closed."], ["Ost, the smith at the square"], ["a letter, delivered"]),
    "show_journal, empty": lambda: console.show_journal([], []),
    "show_help": lambda: console.show_help(),
    "combat_panel": lambda: console.combat_panel(["You        HP 40/52", "Grey wolf  HP 9/30"]),
    "combat_numbers": lambda: console.combat_numbers(["12 slashing to the wolf", "the wolf misses"] * 4),
    "combat_numbers, none": lambda: console.combat_numbers([]),
    "status_block": lambda: console.status_block("Day 3, dusk", "light rain", "Trading Square, Parth", "a quiet corner by the well",
                                                 {"health": (40.4, 52), "mana": (0, 0), "stamina": (11.0, 40)}, 3, 2, 12345, (120, 400)),
}

# ---- these read the game's data (a class's abilities, an item's numbers): compared while the data is what the copy was taken on
char, spec = simlib.make_character("warrior", random.Random(1), perks=True)
interp = ClassInterpretation(archetype=Archetype(spec["archetype"]), custom_class=spec["name"], combat_identity="holds the line",
                             themes=["iron", "oaths"], summary="x", focus="balanced", uses_companions=False, summoner=False,
                             families=spec["families"], primary_attributes=spec["primary"], casting_attribute=spec["casting"])
blade = items.make(spec["weapon"], "common", 1, name="Oathkeeper", description="It has never been drawn in anger.")
SHEET = {
    "show_class": lambda: console.show_class(interp),
    "show_actives": lambda: console.show_actives(char.actives, 1),
    "show_lessons": lambda: console.show_lessons(list(char.actives[:1]) + list(char.passives[:1]), 1),
    "show_passives": lambda: console.show_passives(char.passives),
    "show_stat_rules": lambda: console.show_stat_rules(["Strength carries a heavy blade."]),
    "show_sheet": lambda: console.show_sheet({k: 10 + i for i, k in enumerate(console.stats.STAT_NAMES)}),
    "show_player_block": lambda: console.show_player_block(char, "Trading Square", "Day 3, dusk",
                                                           [("Health", 40, 52), ("Mana", 0, 0), ("Stamina", 11, 40)]),
    "show_inventory": lambda: console.show_inventory(char),
    "legendary_reveal": lambda: console.legendary_reveal(blade),
}

now = {"data": statehash.data_hash(), "plain": {k: shown(f) for k, f in PLAIN.items()}, "sheet": {k: shown(f) for k, f in SHEET.items()}}
again = {"plain": {k: shown(f) for k, f in PLAIN.items()}, "sheet": {k: shown(f) for k, f in SHEET.items()}}
check("(the same call writes the same text twice in one run)", again["plain"] == now["plain"] and again["sheet"] == now["sheet"],
      [k for g in ("plain", "sheet") for k in now[g] if now[g][k] != again[g][k]])

if "--write" in sys.argv:
    KEPT.write_text(json.dumps(now, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"kept {len(now['plain']) + len(now['sheet'])} texts in {KEPT}")
    sys.exit(0)

kept = json.loads(KEPT.read_text(encoding="utf-8"))
for name, text in now["plain"].items():
    check(f"{name}: stdout is the kept text", kept["plain"].get(name) == text, (kept["plain"].get(name), text))
check("no kept text is of a call the test no longer makes", set(kept["plain"]) == set(now["plain"]) and set(kept["sheet"]) == set(now["sheet"]),
      (set(kept["plain"]) ^ set(now["plain"]), set(kept["sheet"]) ^ set(now["sheet"])))
if kept["data"] == now["data"]:
    for name, text in now["sheet"].items():
        check(f"{name}: stdout is the kept text", kept["sheet"].get(name) == text, (kept["sheet"].get(name), text))
else:
    print(f"note: the data changed since the copy was taken ({kept['data']} then, {now['data']} now): the {len(now['sheet'])} sheet texts "
          "are not compared; take a new copy with --write")

# ---- whatever the data: each function writes what the built-in print writes for the calls it makes
import builtins
MISSING = object()


def as_print(fn) -> str:
    """The function's print calls, taken in the console's own name and written by the built-in print."""
    calls, had = [], console.__dict__.get("print", MISSING)
    console.print = lambda *a, **k: calls.append((a, k))
    try:
        shown(fn)
    finally:
        if had is MISSING:
            del console.print
        else:
            console.print = had
    buf = io.StringIO()
    for a, k in calls:
        builtins.print(*a, **{x: v for x, v in k.items() if x != "flush"}, file=buf)
    return buf.getvalue()


off = [k for group in (PLAIN, SHEET) for k, f in group.items() if as_print(f) != shown(f)]
check("every function writes exactly what the built-in print writes for its calls (the sheets too, whatever the data)", not off, off)

check("the one print that ends without a newline is the load bar's", now["plain"]["setup_progress, part"].startswith("\r")
      and not now["plain"]["setup_progress, part"].endswith("\n") and now["plain"]["setup_progress, done"].endswith("\n"))
check("a function that draws nothing in the terminal writes nothing", now["plain"]["busy_text"] == "" and now["plain"]["debug, off"] == ""
      and now["plain"]["combat_numbers, none"] == "")

# ---- every function that prints is one of the calls above
tree = ast.parse(Path(console.__file__).read_text(encoding="utf-8"))
prints = {f.name for f in ast.walk(tree) if isinstance(f, ast.FunctionDef)
          for c in ast.walk(f) if isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == "print"}
called = {k.split(",")[0] for k in list(PLAIN) + list(SHEET)}
check("every function of the console that prints is called here", prints <= called, sorted(prints - called))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
