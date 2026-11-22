"""(f647) The danger label is for testing, not for the player (the owner, 2026-11-15: "something I think should only be left for
internal testing and not a player viewable thing"; docs/design/21_play_faults_plan.md section 11.3, G1; found in play:
docs/play/2026-11-15_play_findings.md 5.1, a fight that killed every companion read "trivial"). Held here:
- a fight's start shows the player no label: not in the pane's data, not in the printed header, not in a note;
- the debug view keeps it, the word and the rate, and the estimate itself is what it was (danger_500_test holds its dice);
- a character whose ability promises a reading of the fight still gets what the data promises, in figures and never by the
  label's word: the odds for Keen Judge (and the Oracle's effect), the odds and the foe's pace for a sworn enemy;
- a camp scouted well tells its guards, its leader and its flaw, and no label; the advice to hire help for a garrison stays.
What the narrator is told of the odds (the opening's own sentence) is not the label and is not changed here.
Run: python tools/sim/danger_hidden_647_test.py"""
import re
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import arcs, combat
from core.models import Passive, PowerTier
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


LABELS = ("trivial", "favorable", "even", "dangerous", "deadly")
WORD = re.compile(r"\b(" + "|".join(LABELS) + r")\b", re.I)
PANES, HEADS, DEBUG = [], [], []
console.put("combat_state", lambda data: (PANES.append(data), False)[1])
console.put("combat_panel", lambda lines: HEADS.append(list(lines)))
console.put("debug", lambda t, *a, **k: DEBUG.append(str(t)))

NAME = "danger_hidden_647"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")
creature = ws.world.bestiary["awakened_shrub"]


def begin(passives=()):
    """A fight begun by a typed line, as a player begins one: what the pane was handed, what was printed, and the estimate."""
    ws.combat = None
    store.save_combat(None)
    c = ws.player.character
    c.passives = [p for p in c.passives if p.mechanic not in ("keen_judge", "sworn_enemy")] + list(passives)
    store.save_player(ws.player)
    foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "awakened shrub", "near")
    foe.hp = foe.max_hp = 600
    ws.wildlife = (creature, [foe])
    del PANES[:], HEADS[:], DEBUG[:]
    n = len(SHOWN)
    stub.plan = [{"kind": "attack", "target": "awakened shrub"}]
    ws.turn("I attack the shrub.")
    stub.plan = None
    label, rate = combat.danger(ws.combat.fight)
    first = PANES[0] if PANES else {}
    head = [l for lines in HEADS[:1] for l in lines]
    return {"label": label, "rate": rate, "pane": str(first.get("danger", "")), "head": head, "notes": [t for k, t in SHOWN[n:] if k == "note"],
            "debug": list(DEBUG)}


got = begin()
check("a fight has begun, and the estimate is what it was: one of the five words and a rate",
      ws.combat is not None and got["label"] in LABELS and 0.0 <= got["rate"] <= 1.0, got)
check("5.1: the pane is handed no label at a fight's start", got["pane"] == "", got["pane"])
check("...the printed header has none", bool(got["head"]) and not any("Danger" in l or WORD.search(l) for l in got["head"]), got["head"])
check("...and no note says it", not any("Danger" in t or WORD.search(t) for t in got["notes"]), got["notes"])
check("the debug view keeps it: the word and the rate", any(got["label"] in t and "%" in t for t in got["debug"]), got["debug"])

keen = Passive(id="kj", name="Keen Judge", description="d", tier=PowerTier.LIGHT, mechanic="keen_judge", value=1)
got = begin([keen])
PCT = re.compile(r"\d+%")
check("Keen Judge still reads the odds, as the data promises: the figure, in the pane and in the header",
      "judge your odds at" in got["pane"] and PCT.search(got["pane"]) and any(PCT.search(l) for l in got["head"]), (got["pane"], got["head"]))
check("...and never by the label's word", not WORD.search(got["pane"]) and not any("Danger" in l or WORD.search(l) for l in got["head"]), (got["pane"], got["head"]))

sworn = Passive(id="se", name="Sworn Enemy", description="d", tier=PowerTier.LIGHT, mechanic="sworn_enemy", value=20, subject=getattr(creature, "category", ""))
got = begin([sworn])
check("a sworn enemy is still read at a glance: the odds and its pace",
      PCT.search(got["pane"]) and re.search(r"slow|fast|no quicker", got["pane"]) is not None and any(PCT.search(l) for l in got["head"]), (got["pane"], got["head"]))
check("...and never by the label's word", not WORD.search(got["pane"]) and not any("Danger" in l for l in got["head"]), (got["pane"], got["head"]))
got = begin([keen, sworn])
check("both abilities: each reading is there once, and no label",
      got["pane"].count("judge your odds") == 1 and got["pane"].count("sworn foe") == 1 and not WORD.search(got["pane"]), got["pane"])
check("a reading shown never opens with the label's old heading", not any("Danger" in l for l in got["head"]), got["head"])

# ---- a camp scouted well
ws.combat = None
store.save_combat(None)
tpl = arcs.TEMPLATES["smuggling_ring"]
arc = {"id": "arc647", "nodes": []}
node = {"id": "n1", "kind": "lair"}
ws.story_node = lambda a, nid: {}
ws.camp_roll = lambda *a, **k: "success"
camp = ws.camp_build(arc, node, tpl)
node["camp"] = camp
ws.advance_quiet = lambda minutes: None
told = []
real_narrate = ws.narrate
ws.narrate = lambda event, text="", *a, **k: told.append(event)
n = len(SHOWN)
for size in ("as built", "a garrison"):
    camp["scouted"] = False
    if size == "a garrison":
        camp["guards"] = [dict(camp["guards"][0], name=f"guard {i}", level=camp["guards"][0]["level"] * 6) for i in range(12)]
    n = len(SHOWN)
    ws.camp_scout({}, arc, node, tpl, camp, "I scout the camp.")
    notes = [t for k, t in SHOWN[n:] if k == "note"]
    check(f"a camp scouted well ({size}): its guards, its leader and its flaw are told", any("Guards:" in t and "Leader:" in t for t in notes) and any("You spot" in t for t in notes), notes)
    check(f"...and no label ({size})", not any("looks:" in t or WORD.search(t) for t in notes), notes)
check("a garrison is still told as one, with the advice to hire help", any("garrison" in t for t in notes), notes)
ws.narrate = real_narrate

# ---- the fence: who asks for the estimate, and who reads its label, in the game's own code
from game_files import game_files                                     # (f788) the game's own code, one definition for every fence
SHOWING = game_files()
asks = sorted(p.as_posix() for p in SHOWING if re.search(r"(?<![\w])danger\(", p.read_text(encoding="utf-8")))
reads_label = sorted(p.as_posix() for p in SHOWING if re.search(r"\bopening\.label\b", p.read_text(encoding="utf-8")))
check("the estimate is made in one place and asked for where it was: a fight's making and a camp's scouting, and nowhere new",
      asks == ["engine/combat.py", "scenes/camp_actions.py", "services/fight.py"], asks)
check("...and a fight's label is read in one place, the scene that opens it", reads_label == ["scenes/combat_scene.py"], reads_label)
check("no line the game prints is headed by the label", not any("Danger:" in p.read_text(encoding="utf-8") or "Charging in looks" in p.read_text(encoding="utf-8")
                                                              for p in SHOWING), [p.as_posix() for p in SHOWING if "Danger:" in p.read_text(encoding="utf-8")])

game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
