"""(f474) Continuity, counted from the page (tools/page_measures.py continuity): a fixture night with one slip of each of the eight kinds
counts each once, and a clean night, the same people and matters told rightly, counts none. Also: the rows in summary.md under their
own heading (tools/latency.py), and a night with no talk state says it was not recorded rather than counting nothing."""
import json
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 2))
import page_measures as pm
import latency

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

D0 = 10 * 1440 + 600
T2 = D0 + 3 * 1440
MIN = {1: D0, 2: T2, 3: T2 + 60, 4: T2 + 300, 5: T2 + 400, 6: T2 + 500, 7: T2 + 600, 8: T2 + 700, 9: T2 + 800, 10: T2 + 900}
LABELS = {"bram": "Bram Voss", "wenna": "Wenna Holt", "ilsa": "Ilsa Penn", "tomas": "Tomas Reed", "marta": "Marta Quill", "hild": "Hild Ashe"}
Q1 = {"id": "q1", "kind": "kill", "holder": "tomas", "title": "Clear the rats from the cellar", "state": "taken"}
Q2 = {"id": "q2", "kind": "fetch", "holder": "marta", "title": "Recover the silver locket", "state": "taken"}
Q3 = {"id": "q3", "kind": "escort", "holder": "guild", "title": "Escort the wagon north", "state": "taken"}
DEED = {"kind": "brawl", "minute": T2 + 60, "place": "parth", "target": "carl", "witnesses": ["wenna"],
        "text": "You struck the drunk tanner at the market well"}


def state(n, work_lapses):
    talk = {}
    for nid, lab in LABELS.items():
        if nid == "hild" and n not in (2, 3):
            continue                                                   # Hild is only about on turns 2 and 3
        talk[nid] = {"label": lab, "met": nid != "ilsa" or n >= 4, "last_talk_at": D0 if nid == "bram" else -1, "known_as": "", "trust": 0}
    owed = [q for q, live in ((Q1, 3 <= n <= 5), (Q2, 3 <= n <= 6), (Q3, 3 <= n <= 7)) if live]
    if n in (2, 3):
        owed.append({"id": "work:hild", "kind": "work", "holder": "hild", "title": "Mend the fence by the barn",
                     "state": "lapsed" if n == 3 and work_lapses else "open"})
    return {"place": "parth", "minutes": MIN[n], "party": ["Odly Garth"] if n <= 6 else [], "talk": talk, "owed": owed, "partner": "",
            "commitments": 0, "deeds": [DEED] if n == 3 else []}


def night(said: dict, work_lapses: bool):
    game, turns = [], []
    for n in range(1, 11):
        game.append({"turn": n, "text": "I talk", "place": "parth", "shown": [{"kind": k, "text": t} for k, t in said.get(n, [])]})
        turns.append({"turn": n, "level": 5, "state": state(n, work_lapses), "outcomes": []})
    return game, turns


def sp(who, words):
    return ("speech", f'{LABELS[who]}: "{words}"')


SLIPS = {
    1: [sp("bram", "Morning.")],
    2: [sp("bram", "It's been months since we last spoke.")],                                   # C1: three days, said as months
    4: [sp("wenna", "Who are you, then? Never seen you before."),                               # C2: met, greeted as a stranger
        sp("ilsa", "Good to see you again, friend.")],                                          # C2: never met, greeted as known
    5: [sp("tomas", "Thank you for clearing the cellar rats."),                                 # C3: open, spoken of as done
        sp("bram", "Good day, Vosk."),                                                          # C6: kept by the one told
        sp("ilsa", "They say you struck the tanner by the market.")],                           # C8: a deed she did not see
    6: [("ledger", "Completed: [C] Clear the rats from the cellar. Tomas Reed pays you 5 silver."),
        sp("wenna", "Vosk, is it? I saw you strike that drunk tanner."),                        # C6 spread; C8 a witness
        ("narration", "Vosk walks to the door and looks out.")],                                # C6 in narration
    7: [("ledger", "Abandoned: Recover the silver locket.")],
    8: [("narration", "Odly sharpens her blade by the fire."),                                  # C7: gone, narrated as here; C5: q3 gone unsaid
        sp("tomas", "Any luck with the cellar yet?")],                                          # C3: closed, as still open; C4 raised
    9: [sp("marta", "Lovely weather. Where did Odly go?")],                                     # C4 not raised; C7 in speech
    10: [sp("bram", "Farewell, Vosk.")],                                                        # C6: after it was set straight
}
LOG = {"plants": [{"turn": 2, "npc": "bram", "name": "Bram Voss", "token": "Vosk Hallarin", "kind": "name"}],
       "corrections": [{"turn": 9, "npc": "bram", "token": "Vosk Hallarin", "gap": 2000}], "promises": [], "revisits": [],
       "accepted": [], "abandoned": [], "issuer_visits": []}
info = {"bot": {"continuity_log": LOG}}

game, turns = night(SLIPS, work_lapses=True)
m = pm.continuity(game, turns, info)
check("C1: three days since the last talk, said as months, is one slip of one time spoken", len(m["c1_time_slips"]) == 1
      and m["c1_time_spoken"] == 1 and m["c1_time_slips"][0][3:] == (5, 2), (m["c1_time_slips"], m["c1_time_spoken"]))
check("C2: someone met greeting the player as a stranger, and someone never met greeting them as known: one each",
      len(m["c2_met_as_stranger"]) == 1 and m["c2_met_as_stranger"][0][1] == "Wenna Holt"
      and len(m["c2_stranger_as_met"]) == 1 and m["c2_stranger_as_met"][0][1] == "Ilsa Penn", (m["c2_met_as_stranger"], m["c2_stranger_as_met"]))
check("C3: a contract thanked for while open, and asked after once it was done: one each, by its holder",
      len(m["c3_open_as_done"]) == 1 and len(m["c3_closed_as_open"]) == 1 and m["c3_closed_as_open"][0][3] == "kept",
      (m["c3_open_as_done"], m["c3_closed_as_open"]))
check("C4: the kept one raised by its holder next time, the given-up one not", m["c4_raised"] == {"kept": (1, 1), "given up": (0, 1)}, m["c4_raised"])
check("C5: a contract gone with no line saying so, and a work offer left to lapse: one each (an offer out of sight is not gone)",
      [v[2] for v in m["c5_vanished"]] == ["Escort the wagon north"] and m["c5_lapsed"] == 1, (m["c5_vanished"], m["c5_lapsed"]))
c6 = m["c6_false_name"]
check("C6: the false name kept by the one told, spread to one other, said after it was set straight, and in narration: one each",
      (c6["planted"], c6["kept"], c6["spread"], c6["after"], c6["narrated"], c6.get("corrected")) == (1, 1, 1, 1, 1, 1), c6)
check("C7: a companion gone, then in narration once and in speech once", m["c7_left_named"] == [("Odly Garth", 7, 1, 1)], m["c7_left_named"])
check("C8: a deed spoken of by one who did not see it, and by its witness, counted apart",
      len(m["c8_unseen_spoken_of"]) == 1 and m["c8_unseen_spoken_of"][0][1] == "Ilsa Penn" and m["c8_witnesses_spoke"] == 1,
      (m["c8_unseen_spoken_of"], m["c8_witnesses_spoke"]))
rows = pm.continuity_table(game, turns, info)
check("the table has a row for each of the eight", len(rows) == 10 and [r.split()[1] for r in rows[2:]] == [f"C{i}" for i in range(1, 9)], rows)

CLEAN = {
    1: [sp("bram", "Morning.")],
    2: [sp("bram", "Three days since we last spoke, and here you are.")],                       # bucket 2 against bucket 2
    4: [sp("wenna", "Good to see you again."), sp("ilsa", "Well met. What brings you to Parth?")],
    5: [sp("tomas", "How goes the cellar?"), sp("bram", "Good day, Vosk.")],                   # still open, asked after; the name kept
    6: [("ledger", "Completed: [C] Clear the rats from the cellar. Tomas Reed pays you 5 silver."),
        sp("wenna", "I saw you strike that drunk tanner."), ("narration", "You walk to the door and look out.")],
    7: [("ledger", "Abandoned: Recover the silver locket.")],
    8: [("note", "Completed: [D] Escort the wagon north. The guild pays you."), ("narration", "The fire burns low."),
        sp("tomas", "Thank you for clearing the cellar.")],
    9: [sp("marta", "So you gave up on my silver locket.")],
    10: [sp("bram", "Farewell, Edrin.")],
}
game_c, turns_c = night(CLEAN, work_lapses=False)
mc = pm.continuity(game_c, turns_c, info)
c6c = mc["c6_false_name"]
check("a clean night counts no slip of any kind", not mc["c1_time_slips"] and mc["c1_time_spoken"] == 1 and not mc["c2_met_as_stranger"]
      and not mc["c2_stranger_as_met"] and not mc["c3_open_as_done"] and not mc["c3_closed_as_open"] and not mc["c5_vanished"]
      and not mc["c5_lapsed"] and (c6c["spread"], c6c["after"], c6c["narrated"]) == (0, 0, 0) and mc["c7_left_named"] == [("Odly Garth", 7, 0, 0)]
      and not mc["c8_unseen_spoken_of"], mc)
check("...and counts what went right: both closed matters raised next time, the false name kept by the one told, the witness speaking",
      mc["c4_raised"] == {"kept": (1, 1), "given up": (1, 1)} and c6c["kept"] == 1 and mc["c8_witnesses_spoke"] == 1, (mc["c4_raised"], c6c))

# ---- the night's summary.md has the rows under their own heading; a night with no talk state says so
run = Path("saves/continuity_474_test")
shutil.rmtree(run, ignore_errors=True)
run.mkdir(parents=True)
(run / "run.json").write_text(json.dumps({"character": "Edrin", "bot": {"continuity_log": LOG}}), encoding="utf-8")
(run / "turns.jsonl").write_text("\n".join(json.dumps(t) for t in turns) + "\n", encoding="utf-8")
(run / "turns_game.jsonl").write_text("\n".join(json.dumps(g) for g in game) + "\n", encoding="utf-8")
text = latency.summarise(run)
part = text[text.find("## Continuity (from the page)"):]
check("summary.md has the continuity rows under their own heading, after the page's", "## The page" in text and "## Continuity (from the page)" in text
      and text.find("## The page") < text.find("## Continuity (from the page)") and "| C6 The false name given" in part
      and "1 / 1 / 1 / 1 (planted 1, set straight 1)" in part, part[:900])
old = [{**t, "state": {k: v for k, v in t["state"].items() if k not in ("talk", "owed", "deeds")}} for t in turns]
none = pm.continuity_table(game, old, {})
check("a night with no talk state is said not to be recorded, not counted as clean", len(none) == 1 and none[0].startswith("Not recorded"), none)
shutil.rmtree(run, ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
