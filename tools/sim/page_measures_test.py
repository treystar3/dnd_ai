"""(f414) A night's page, counted from the page (tools/page_measures.py): a fixture night with one of each thing a reader met on the f395
night counts each once, and a clean one counts nothing. Also the split of 'made room for' by how it was made, a 'said no' that was about
someone in the party, and the bot's road count (once per happening)."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import page_measures as pm
import latency
from engine import clock
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

world = load_world()
wild = next(p.id for p in world.places.values() if p.danger)
inn = next(p.id for p in world.places.values() if p.type == "inn")
town = "parth"
summer = next(m for m in range(0, 400 * 1440, 1440) if clock.season(m) == "summer")
spring = next(m for m in range(0, 400 * 1440, 1440) if clock.season(m) == "spring")
info = {"cast": {"Odly Garth": {"kind": "hire", "pronoun": "she", "people": "human"}}, "_refusals": []}


def turn(n, text, place, shown, minutes=spring, level=10, foes=()):
    return ({"turn": n, "text": text, "place": place, "shown": [{"kind": k, "text": t} for k, t in shown]},
            {"turn": n, "level": level, "state": {"place": place, "minutes": minutes, "party": ["Odly Garth"], "foes": list(foes)}, "outcomes": []})


night = [
    turn(1, "I use the whetstone on my spear", town, [("note", "You have nothing like that you can use."),
                                                      ("narration", "The whetstone rasps along your spear while you sit.")]),
    turn(2, "I look around", town, [("narration", "The gate creaks.} {The mud is deep."), ("narration", "It falls (12 damage) (30 damage)."),
                                    ("speech", "Bram Voss: None.")]),
    turn(3, "I walk on", wild, [("narration", "An alley mouth opens beside the path.")]),
    turn(4, "I sit by the fire", inn, [("narration", "Rain lashes the bar while the keeper wipes it down.")]),
    turn(5, "I look at the field", town, [("narration", "Frost silvers the grass at the field's edge.")], minutes=summer),
    turn(6, "I watch the fight", wild, [("narration", "Odly raises his shield against the blow.")]),
    turn(7, "I attack the wolf", wild, [("note", "The Shipwreck Shoals across the road is ended - by way of 'Thin the giant crabs'.")]),
    turn(8, "I hunt the giant crabs at the shoals", wild, [("note", "Crabs on the Strand is ended - by way of 'Thin the giant crabs'.")]),
    turn(9, "I attack the bandits", wild, [("ledger", "Victory. +0 XP")], foes=[40]),
    turn(10, "I push off the wall", town, [("note", "Remembered here: broken: push off the wall")]),
    turn(11, "I rest", town, [("note", "The captured bandit worked his bonds loose and slipped away in the night.")]),
    turn(12, "I hand him over", town, [("note", "The watch captain takes the captured bandit into custody. Paid: 1 gold")]),
] + [turn(20 + i, "I wait", town, [("note", "People go about their day.")]) for i in range(5)]
game_turns = [g for g, _ in night]
turns = [t for _, t in night]
calls = [{"turn": 2, "task": "hire_chat", "attempt": 0, "messages": [{"role": "system", "content": ""},
                                                                    {"role": "user", "content": "ASKED BEFORE: where were you born"}]}]
m = pm.measure(game_turns, turns, calls, info, world)
check("a line shown five times word for word is counted, as the game's own", len(m["repeated"]) == 1 and m["repeated"][0][:2] == (5, True), m["repeated"])
check("a refusal followed by a passage that does it anyway: counted, and as never logged", m["refusals"] == 1 and len(m["refused_acted"]) == 1
      and m["refusals_unlogged"] == 1, (m["refusals"], m["refused_acted"], m["refusals_unlogged"]))
check("braces in a passage, a heap of figures, and empty speech: one each", len(m["machinery"]) == 1 and m["heaps"] == 1 and m["empty_speech"] == 1,
      (m["machinery"], m["heaps"], m["empty_speech"]))
check("an alley on a wild road, rain on the bar indoors, frost in summer: one each", len(m["urban_in_wilds"]) == 1 and len(m["rain_indoors"]) == 1
      and len(m["out_of_season"]) == 1, (m["urban_in_wilds"], m["rain_indoors"], m["out_of_season"]))
check("a she called his: one slip, by kind of person", m["pronoun_slips"].get("hire") == (1, 1), m["pronoun_slips"])
check("a matter ended by a kill of something else is by accident; one ended by hunting its creatures is pursued",
      len(m["ended_by_accident"]) == 1 and len(m["ended_pursued"]) == 1, (m["ended_by_accident"], m["ended_pursued"]))
check("a fight for +0 XP, against a foe thirty levels up", m["xp"] == [0] and m["level_gaps"] == [30], (m["xp"], m["level_gaps"]))
check("a mark left by an act, an escape and a hand-over: one each", m["marks_shown"] == 1 and m["captives_escaped"] == 1 and m["captives_settled"] == 1,
      (m["marks_shown"], m["captives_escaped"], m["captives_settled"]))
check("ASKED BEFORE handed to a speaker for a line that asked nothing", m["asked_before_not_a_question"] == 1)
rows = pm.table(game_turns, turns, calls, info, world)
check("the summary's table has a row for each", len(rows) == 13 and all(r.startswith("|") for r in rows), rows)

clean = [turn(1, "I walk into the square", town, [("narration", "You walk into the square. A carter calls out to a friend."),
                                                   ("speech", 'Bram Voss: "Morning."')])]
mc = pm.measure([g for g, _ in clean], [t for _, t in clean], [], info, world)
check("a clean night counts nothing", not mc["repeated"] and not mc["refusals"] and not mc["machinery"] and not mc["heaps"]
      and not mc["empty_speech"] and not mc["urban_in_wilds"] and not mc["rain_indoors"] and not mc["out_of_season"]
      and not any(a for a, _ in mc["pronoun_slips"].values()) and not mc["ended_by_accident"] and not mc["xp"], mc)

# ---- 'made room for', by how; and a 'said no' about someone in the party
rows_ = [{"state": {"party": ["Gallen Thorpden"]}, "outcomes": [{"kind": "made", "how": "narrated"}, {"kind": "made", "how": "ruled"},
                                                                {"kind": "made", "how": "narrated"}]}]
gl = latency.goal_lines(rows_, {"hours": 1, "_refusals": [{"kind": "refused", "text": "Gallen: let's go", "why": "nothing there"}]})
check("'made room for' is split by how it was made", any("narrated 2, ruled 1" in l for l in gl), gl)
check("...and a 'said no' about someone in the party is flagged", any("about someone in the party" in l and l.endswith("| 1 |") for l in gl), gl)

# ---- the bot's road counter: under the stub a ledger line is a note (simlib), so a road happening is counted once
sys.argv = ["x", "warrior", "2", "1", "1", "1"]
import simbot
import ui.console as uc
simbot.ROAD.clear()
uc.ledger("On the road - The Ford")
check("a road happening on the ledger is counted once by the bot", simbot.ROAD["events"] == 1, dict(simbot.ROAD))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
