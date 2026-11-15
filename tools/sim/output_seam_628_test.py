"""(f628) What the window is sent that is not story text, pinned before phase 3 puts the whole output seam under the channel
(docs/design/20_phase3_plan.md f635). The channel of f580 carries text only: the line asked for, the side pane's scope, the status
block, the busy light's words, a pane's data, the load bar, the home page, creation and the fight's pane reach the page another way.
Here a window's bridge is up, each of them is called through the console the way the game calls it, and the events the page would
be sent are compared with a kept copy (tools/sim/fixtures/output_seam_628.json). Then the same through an operation: its lines
reach the page when it stands, in the order they were said, and never when it does not.
This holds what the page is sent, not how it gets there, so it must pass unchanged while the seam moves; the names in SEAM are
held to the code that carries them today by tools/sim/moving_parts_628_test.py.
A new copy is taken only after a change that is meant to alter what the page is sent, and the commit says which event moved and
why: python tools/sim/output_seam_628_test.py --write
Run: python tools/sim/output_seam_628_test.py"""
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
import ui.console as console
from llm.gateway import LLMError
from ui.gui import bridge as bridge_mod

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

KEPT = Path(__file__).resolve().parent / "fixtures" / "output_seam_628.json"
SEAM = {"ask", "scope", "status_block", "kind", "busy_text", "panel", "setup_progress", "home", "home_done", "creation", "creation_done",
        "combat_state", "damage_tags", "WIDTH"}

# ---- each of them, called through the console with a window up
was_debug, config.DEBUG = config.DEBUG, False
b = bridge_mod.Bridge()
b.install()
try:
    used = set()

    def call(name, *a, **k):
        used.add(name)
        return getattr(console, name)(*a, **k)

    returned = {}
    console.out("A line before anything is asked.")
    returned["ask, main, the pinned view first"] = call("ask", main=True)
    b.inbox.put("  look around  ")
    returned["ask, main"] = call("ask", main=True)
    returned["ask, main, the pinned view again after a line"] = call("ask", main=True)
    b.inbox.put("#journal")
    returned["ask, main, a view"] = call("ask", main=True)
    b.inbox.put("yes")
    returned["ask, a question"] = call("ask")
    b.inbox.put("no")
    returned["ask, a question the main menu may leave"] = call("ask", menu=True)
    with call("scope", "#journal"):
        console.out("What the journal holds.")
        returned["panel, in the side pane"] = call("panel", "shop", {"wares": [{"name": "a coil of rope", "price": 12}]})
    with call("scope", "look around"):
        console.out("What is seen.")
    returned["panel, outside the side pane"] = console.panel("shop", {"wares": []})
    with call("kind", "speech"):
        console.out("Mind the mud.")
    call("status_block", "Day 3, dusk", "light rain", "Trading Square, Parth", "a quiet corner by the well",
         {"health": (40.4, 52), "mana": (0, 0), "stamina": (11.0, 40)}, 3, 2, 12345, (120, 400), {"hunger": 2})
    call("busy_text", "People go about their day.")
    b.busy(True)
    b.busy(False)
    b.busy(True)
    b.busy(False)
    call("setup_progress", 0.25, "Waking the model")
    call("setup_progress", 0.5, "Waking the model")
    returned["home"] = call("home", {"saves": [{"name": "Vessa", "level": 3}]})
    call("home_done")
    returned["creation"] = call("creation", {"step": "name", "ask": "What are you called?"})
    call("creation_done")
    returned["combat_state"] = call("combat_state", {"round": 1, "foes": [{"name": "grey wolf", "hp": 9}]})
    returned["combat_state, over"] = call("combat_state", None)
    used |= {"damage_tags", "WIDTH"}
    returned["damage_tags"] = console.damage_tags
    returned["WIDTH"] = console.WIDTH
    b.flush_text()
    events = [ev for _, ev in b.log]
finally:
    b.uninstall()
    config.DEBUG = was_debug

now = {"events": events, "returned": returned}
check("every name of the seam is called here", used == SEAM, sorted(SEAM ^ used))

if "--write" in sys.argv:
    KEPT.write_text(json.dumps(now, indent=1, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(f"kept {len(events)} events and {len(returned)} answers in {KEPT}")
    sys.exit(0)

kept = json.loads(KEPT.read_text(encoding="utf-8"))
now = json.loads(json.dumps(now, ensure_ascii=False))            # as the copy holds them: tuples are lists there
check("the page is sent the kept events, in the kept order", now["events"] == kept["events"],
      next(((i, a, c) for i, (a, c) in enumerate(zip(now["events"], kept["events"])) if a != c), (len(now["events"]), len(kept["events"]))))
check("...and the game is answered as kept", now["returned"] == kept["returned"],
      {k: (now["returned"].get(k), kept["returned"].get(k)) for k in set(now["returned"]) | set(kept["returned"])
       if now["returned"].get(k) != kept["returned"].get(k)})
kinds = [ev["k"] for ev in now["events"]]
check("(the kept events hold every kind the window can be sent by these names)",
      {"text", "prompt", "echo", "side_begin", "side_end", "panel", "status", "busy", "setup_progress", "home", "home_end", "creation",
       "creation_end", "combat", "combat_end"} <= set(kinds), sorted(set(kinds)))
check("...the load bar keeps only its latest figure", kinds.count("setup_progress") == 1)
check("...the busy light carries the words given for the wait once, and none after", [ev["text"] for ev in now["events"] if ev["k"] == "busy"]
      == ["People go about their day.", "", "", ""], [ev for ev in now["events"] if ev["k"] == "busy"])

# ---- through an operation: what it says reaches the page when it stands, and not at all when it does not
g = simlib.campaign("output_seam_628", cls="warrior", seed=3, location="parth")
ws = g.scene
config.TURN_LOG_PATH = "saves/output_seam_628/turns.jsonl"
ws.enter("parth")
b = bridge_mod.Bridge()
b.install()
try:
    texts = lambda: "".join(ev["text"] for _, ev in b.log if ev["k"] == "text")
    with ws.operation("test", "a step that stands") as stands:
        console.note("The first thing said inside.")
        console.note("The second thing said inside.")
        b.flush_text()
        inside = texts()
    b.flush_text()
    after = texts()
    with ws.operation("test", "a step that fails") as fails:
        console.note("Said inside a step that will not stand.")
        raise LLMError("the model failed")
    b.flush_text()
    failed = texts()
finally:
    b.uninstall()
check("what an operation says is not on the page while it is open", stands.state == "committed" and "said inside" not in inside, inside)
check("...it is there once the operation stands, in the order it was said", "The first thing said inside." in after
      and after.index("The first thing said inside.") < after.index("The second thing said inside."), after)
check("what an operation that did not stand said never reaches the page", fails.state == "rolled_back"
      and "will not stand" not in failed, failed[len(after):])
g.session.close()
shutil.rmtree("saves/output_seam_628", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
