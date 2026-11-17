"""(f651) An order to the party out of a fight is to the members it names (docs/design/21_play_faults_plan.md, B1; found in play:
docs/play/2026-11-15_play_findings.md 1.6). '"Raerei, ... stay behind me from here on."' held the whole party back: the party could only
be held all together. Held here:
- holding back: the companions the line speaks to by name, clause by clause, or else the ones the reading's target names (by name or
  role), hold back where they are; the others stay with the player; the line printed names who; a line said to everyone, or naming
  no one, holds the whole party as before ("Kennard, hold back. Everyone else, with me" holds Kennard);
- one held alone is shown so in the Party pane, is left out of a camp's first rank and its noise (the estimate as the fight), falls in
  again when the player walks away, and comes when told to come along by a typed line;
- dismissing: those named go (by name or role), the rest stay; "the whole party" or "everyone" sends all; a target naming no one in
  the party sends no one, and says so (it sent everyone before).
Run: python tools/sim/party_members_651_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
SHOWN = simlib.quiet_console()
from llm.contracts import PartyIntent

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


NAME = "party_members_651"
g = simlib.campaign(NAME, cls="warrior", seed=3, location="trading_square")
ws, store = g.scene, g.store


def party():
    ws.player.party = [{"id": hid, "name": name, "role": role, "level": 5, "rank": "F", "permanent": True, "bond": 10, "base_level": 5,
                        "hired_at": 10, "quirks": {}, "motive": "coin", "blurb": "x"}
                       for hid, name, role in (("h0", "Raerei Wynn", "priest"), ("h1", "Kennard Holt", "fighter"), ("h2", "Almund Pell", "mage"))]
    ws.player.party_mode = "with"
    ws.player.party_hold_at = ""
    if ws.player.location != "trading_square":
        ws.enter("trading_square")
    store.save_player(ws.player)


def held():
    return sorted(m["name"].split()[0] for m in ws.player.party if m.get("held_at"))


def left():
    return sorted(m["name"].split()[0] for m in ws.player.party)


def notes(n):
    return [t for k, t in SHOWN[n:] if k == "note"]


# ---- holding back one
party()
n = len(SHOWN)
ws.party_hold("Raerei", '"Raerei, see to your own wounds and stay here." We go on.', [])
check("1.6: the companion spoken to is held back, the others stay with the player", held() == ["Raerei"] and ws.player.party_mode == "with", ws.player.party)
check("...and the line printed says who", any("Raerei" in t and "hold back" in t for t in notes(n)) and not any("Your party" in t for t in notes(n)), notes(n))
party()
ws.party_hold("", "Kennard, Almund, hold back here.", [])
check("two companions spoken to are held, the third is not", held() == ["Almund", "Kennard"], held())
party()
ws.party_hold("Kennard", "Hold back here, big man.", [])
check("the one the reading names is held, though the line names no one", held() == ["Kennard"], held())
party()
ws.party_hold("fighter", "You, the big one, wait here.", [])
check("...or the one the reading names by role", held() == ["Kennard"], held())
party()
ws.party_hold("Kennard", "Everyone, hold back here.", [])
check("a line said to everyone is the whole party's, whatever the reading names", ws.player.party_mode == "hold" and held() == [], (ws.player.party_mode, held()))
party()
ws.party_hold("Kennard", "Kennard, hold back here. Everyone else, with me.", [])
check("'Kennard, hold back. Everyone else, with me' holds Kennard alone", held() == ["Kennard"] and ws.player.party_mode == "with", (held(), ws.player.party_mode))
party()
ws.party_hold("Kennard", "Everyone else, with me. You wait here, big man.", [])
check("...and the reading's one is held when 'everyone else' is told to come", held() == ["Kennard"], held())
party()
n = len(SHOWN)
ws.party_hold("", "Hold back here, all of you.", [])
check("no one named: the whole party, as before", ws.player.party_mode == "hold" and any("Your party" in t for t in notes(n)), (ws.player.party_mode, notes(n)))

# ---- one held alone: the pane, a camp, walking away, being called
party()
ws.party_hold("Raerei", "Raerei, wait here.", [])
rows = {r["name"].split()[0]: r for r in ws.party_data()["adventurers"]}
check("the Party pane shows the one held back, and only them", "holding back" in rows["Raerei"].get("doing", "") and not rows["Kennard"].get("doing"), rows)
from scenes.combat_scene import service_of
near, later, _n, _f = service_of(ws).allies(True)
check("at a camp, the one held back arrives later and the others are in the first rank",
      [a.name.split()[0] for a in later] == ["Raerei"] and {"Kennard", "Almund"} <= {a.name.split()[0] for a in near}, ([a.name for a in near], [a.name for a in later]))
check("...a camp's noise counts only those with the player", [m["name"].split()[0] for m in ws.camp_members()] == ["Kennard", "Almund"])
n = len(SHOWN)
ws.enter("guild_house")
check("walking away from the place one holds: they fall in again, and the line says who",
      held() == [] and any("Raerei" in t and "falls in" in t for t in notes(n)), (held(), notes(n)))
party()
ws.party_hold("Raerei", "Raerei, wait here.", [])
ws.party_read = lambda text, offered: PartyIntent(kind="with", target="Raerei")
taken = ws.party_turn("Raerei, come with me now.")
check("a typed line calling the one held back brings them", taken and held() == [], (taken, held()))
del ws.party_read

# ---- dismissing
party()
ws.party_dismiss("Kennard", "I dismiss Kennard from the party", [])
check("dismissing one named sends that one only, though the line says 'party'", left() == ["Almund", "Raerei"], left())
party()
ws.party_dismiss("priest", "I send the priest away.", [])
check("...and one named by role", left() == ["Almund", "Kennard"], left())
party()
ws.party_dismiss("Kennard and Raerei", "Dismiss Kennard and Raerei.", [])
check("...and two named", left() == ["Almund"], left())
party()
n = len(SHOWN)
ws.party_dismiss("Bram", "Send Bram away.", [])
check("a name not in the party sends no one, and says so", left() == ["Almund", "Kennard", "Raerei"] and any("no one in your party" in t.lower() for t in notes(n)), (left(), notes(n)))
party()
ws.party_dismiss("", "I dismiss the whole party", [])
check("'the whole party' sends everyone", ws.player.party == [], ws.player.party)
party()
ws.party_dismiss("", "Everyone, you're dismissed", [])
check("...and so does 'everyone'", ws.player.party == [], ws.player.party)

g.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
