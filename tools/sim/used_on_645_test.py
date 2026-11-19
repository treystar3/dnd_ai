"""(f645) An item used on someone goes to them (docs/design/21_play_faults_plan.md, A3; found in play:
docs/play/2026-11-15_play_findings.md 2.1). 'I use a healing draught on Raerei' healed the player while the story had her drink:
using an item never read whom it was for. Held here, outside a fight (in one, scenes/combat_scene.py ally_for_item reads it):
- the engine acts for someone else only when the reading of the line and the line's own words agree on who: then a companion who
  is hurt takes what restores health (a draught, a bandage, food, by what the data says), their health rises, the player's does
  not, it leaves the pack and they remember it; and someone of the town who is here is handed it, as giving does;
- what cannot be used on them is refused in a line and kept: one not hurt, a thing that would do nothing for them, one not with
  the player, someone known who is elsewhere;
- a line that names someone the reading does not, a reading that names someone the line does not ("her", "my companion"),
  and a line that says both (it is theirs, and the player takes it), are asked about, and the thing is kept: it is never used
  on the player in their place, and never handed to someone only named;
- a line that names nobody when the reading names nobody here, and a line that says in the first person that the player takes
  it, are the player's own.
Run: python tools/sim/used_on_645_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 10)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import actions, inventory as inv, pools

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


NAME = "used_on_645"
g = simlib.campaign(NAME, cls="warrior", seed=10, location="guild_house")
ws, store = g.scene, g.store
odly = {"id": "h1", "name": "Odly Garth", "role": "fighter", "level": 2, "permanent": True, "rank": "F", "bond": 12, "pronoun": "she",
        "hp_frac": 0.4, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "a sellsword"}
thav = {"id": "h2", "name": "Thavathiel Liaralor", "role": "mage", "level": 2, "permanent": True, "rank": "F", "bond": 12, "pronoun": "he",
        "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "a hedge mage"}
ws.player.party, ws.player.party_mode = [odly, thav], "with"
ws.enter("guild_house")
stub.plan = [{"kind": "look"}]
ws.turn("I look around.")
stub.plan = None
ODLY, THAV = "hire:h1", "hire:h2"


def hire(hid: str) -> dict:
    """The companion as the scene has them now (a turn may have put the save's own copy in the place of the one made above)."""
    return next(m for m in ws.player.party if m["id"] == hid)


def carrying(good: str) -> int:
    return sum(i.quantity for i in ws.pack if i.good == good)


def use(good: str, text: str, target: str = "", then=(), hurt: bool = True):
    """One use of a thing from the pack, as a step of a typed line (`then`: the line's later steps): what the player read, and
    what moved. Odly is hurt and the player is at half health before it, so either could take it."""
    while carrying(good):
        inv.take(ws.pack, inv.GOODS[good].name, 1)
    ws.to_pack(inv.make_good(good, 1))
    ws.player.character.health = pools.maximum(ws.player.character, "health") // 2
    hire("h1")["hp_frac"] = 0.4 if hurt else 1.0
    store.save_player(ws.player)
    before = {"player": ws.player.character.health, "odly": hire("h1")["hp_frac"], "thav": hire("h2")["hp_frac"]}
    n = len(SHOWN)
    stub.plan = [{"kind": "use", "item": inv.GOODS[good].name, "target": target, "summary": "a thing from the pack, used"}, *then]
    stood = ws.turn(text)
    stub.plan = None
    return {"stood": stood, "read": [t for k, t in SHOWN[n:]], "player": ws.player.character.health - before["player"],
            "odly": round(hire("h1")["hp_frac"] - before["odly"], 3), "thav": round(hire("h2")["hp_frac"] - before["thav"], 3), "spent": 1 - carrying(good)}


def hers(got):
    return got["odly"] > 0 and got["player"] == 0 and got["thav"] == 0 and got["spent"] == 1


def own(got):
    return got["player"] > 0 and got["odly"] == 0 and got["thav"] == 0 and got["spent"] == 1


def kept(got, *words):
    """Refused or asked in a line with these words: the thing still carried, and nobody's health moved."""
    return got["spent"] == 0 and got["player"] == 0 and got["odly"] == 0 and got["thav"] == 0 and any(all(w in t for w in words) for t in got["read"])


ASKED = ("for you or for someone else",)

# ---- 2.1: the reading and the line agree on a companion who is hurt
for label, text in (("used on her", "I use a healing draught on Odly."), ("poured", "I pour a healing draught between Odly's lips."),
                    ("she is made to drink", "I make Odly drink a healing draught.")):
    hire("h1")["memories"] = []
    got = use("healing_draught", text, ODLY)
    check(f"a draught for a hurt companion ({label}), the reading and the line agreeing: her health up, the player's not, the draught spent, and she remembers",
          hers(got) and any("when I was hurt" in str(m) for m in hire("h1").get("memories", [])), (got, hire("h1").get("memories")))
check("a bandage is hers too, by what the data says it restores", hers(use("bandage", "I bind Odly's arm with a bandage.", ODLY)))
check("...and food that restores health", hers(use("trail_ration", "I feed Odly a trail ration.", ODLY)))
check("a line naming two companions, the reading naming one of them: it is that one's",
      hers(use("healing_draught", "I use a healing draught on Odly while Thavathiel keeps watch.", ODLY)))

# ---- what it cannot do for them is refused in a line, and kept
got = use("healing_draught", "I use a healing draught on Thavathiel.", THAV)
check("a companion who is not hurt: refused in a line that says so, and kept", kept(got, "Thavathiel", "not hurt"), got)
got = use("mana_tonic", "I use a mana tonic on Odly.", ODLY)
check("a thing that would do nothing for her: refused in a line that says so, and kept", kept(got, "Odly", "nothing"), got)
ws.player.party_mode = "apart"
got = use("healing_draught", "I use a healing draught on Odly.", ODLY)
ws.player.party_mode = "with"
check("a companion who is not with the player: refused in a line that says so, and kept", kept(got, "Odly", "not with you"), got)

# ---- someone known who is elsewhere
away = sorted(ws.present, key=lambda n: n.id)[-1]
first = away.name.split()[0]


def gone_to_the_temple(known: bool = True):
    """Someone of this town, known by name or not, who is not here now (a turn's end may bring them back)."""
    npc = store.load_npc(away.id)
    simlib.view(npc).name_known = known
    npc.location, npc.away_until = "parth_temple", 0
    store.save_npc(npc)
    ws.present = [n for n in ws.present if n.id != away.id]
    ws.residents = [n for n in ws.residents if n.id != away.id]


gone_to_the_temple()
got = use("healing_draught", f"I use a healing draught on {first}.", away.id)
check("someone known who is not here, the reading and the line agreeing on them: refused in a line that says so, and kept", kept(got, first, "not here"), got)
for label, text in (("used on them, the reading silent", f"I use a healing draught on {first}."), ("only named", f"I use the healing draught {first} gave me.")):
    gone_to_the_temple()
    got = use("healing_draught", text, "")
    check(f"someone known who is not here ({label}): asked whom it is for, never told they are not here, and kept",
          kept(got, "for you or for someone else") and not any("not here" in t for t in got["read"]), got)
gone_to_the_temple(known=False)
got = use("healing_draught", f"I use a healing draught on {first}.", "")
check("a name the character does not know is nobody's: no refusal on it, and the draught is the player's", own(got) and not any("not here" in t for t in got["read"]), got)
ws.enter("guild_house")
gone_to_the_temple()
got = use("healing_draught", f"I use my healing draught, then go and find {first}.", "", then=[{"kind": "move", "destination": "parth_temple"}])
check("a draught used, then a walk to someone named who is elsewhere: no refusal, and the draught is the player's", own(got) and not any("not here" in t for t in got["read"]), got)
ws.enter("guild_house")

# ---- someone of the town who is here
person = sorted(ws.present, key=lambda n: n.id)[0]
simlib.view(person).name_known = True
store.save_npc(person)
theirs = person.name.split()[0]
got = use("healing_draught", f"I use a healing draught on {theirs}.", person.id)
check("someone of the town who is here, the reading and the line agreeing: it is handed to them, the ledger says to whom, and the player does not drink it",
      got["spent"] == 1 and got["player"] == 0 and got["odly"] == 0 and any("Gave healing draught" in t for t in got["read"]), (person.id, got))

# ---- the line names someone the reading does not: asked, and kept
for label, text, target, then in (
        ("the bug's own line, the reading silent", "I use a healing draught on Odly.", "", ()),
        ("poured, the reading silent", "I pour a healing draught between Odly's lips.", "", ()),
        ("she is to drink it, the reading silent", "I have Odly drink a healing draught.", "", ()),
        ("someone of the town only named", f"I use a healing draught on my cut while {theirs} watches.", "", ()),
        ("someone of the town, the reading silent", f"I use a healing draught on {theirs}.", "", ()),
        ("two companions, the reading naming neither", "I use a healing draught on Odly while Thavathiel keeps watch.", "", ()),
        ("the reading naming someone the line does not", "I use a healing draught on Odly.", person.id, ()),
        ("'her', the reading naming a companion", "I pour the healing draught down her throat.", ODLY, ()),
        ("'my companion', the reading naming her", "I tip the healing draught to my companion's lips.", ODLY, ()),
        ("by her trade, the reading naming her", "I use a healing draught on the fighter.", ODLY, ()),
        ("the line naming nobody, the reading naming a companion", "I use a healing draught.", ODLY, ()),
        ("the line naming nobody, the reading naming someone of the town", "I use a healing draught on them.", person.id, ()),
        ("then a word with her, the reading silent on the draught", "I use a healing draught on Odly, then ask how she feels.", "",
         [{"kind": "talk", "target": ODLY, "speech": "How do you feel?"}]),
        ("then a look around", "I use a healing draught on Odly, then look around.", "", [{"kind": "look"}])):
    got = use("healing_draught", text, target, then)
    check(f"a name the reading does not confirm ({label}): the player is asked whom it is for, the draught is kept, and nobody's health moves", kept(got, *ASKED), got)
for label, text, good in (("they drink, and the reading is aimed at the one they nod to", "I drink a healing draught and nod to Odly.", "healing_draught"),
                          ("'myself' said of something else", "I tend to Odly's wound myself with a bandage.", "bandage"),
                          ("'myself' in another clause", "I use a healing draught on Odly; I'll keep watch myself.", "healing_draught"),
                          ("eating said beside it", "I use a bandage on Odly while I eat.", "bandage"),
                          ("steadying her", "I pour a healing draught into Odly, steadying her myself.", "healing_draught")):
    got = use(good, text, ODLY)
    check(f"the reading and a name agree and the words also say the player takes it ({label}): asked, kept, and nobody's health moves", kept(got, *ASKED), got)
got = use("healing_draught", "I use a healing draught on Odly and I eat a trail ration.", "", [{"kind": "use", "item": "trail ration"}])
check("two things used in one line, one on a name the reading does not confirm: 'eat' is not taken for the draught's, and it is asked about",
      got["spent"] == 0 and got["odly"] == 0 and any(ASKED[0] in t for t in got["read"]), got)

# ---- the player's own
for label, text, target, then in (
        ("they drink it", "I drink a healing draught.", "", ()),
        ("they drink it, and the line names someone for something else", "I drink a healing draught and nod to Odly.", "", ()),
        ("they use it on themself, someone else named", "I use a healing draught on myself while Odly keeps watch.", "player", ()),
        ("the line names nobody and the reading names nobody", "I use a healing draught.", "", ()),
        ("the reading names the player", "I use a healing draught.", "player", ()),
        ("the reading names someone who is not here and whom the line does not name", "I use a healing draught.", "nobody_of_that_name", ()),
        ("they drink it, whatever the reading says", "I drink a healing draught.", ODLY, ()),
        ("they drink it, then a word with someone the line names", "I drink my healing draught, then ask the guild clerk about work.", "",
         [{"kind": "talk", "target": (ws.clerk_here() or person).id, "speech": "Is there work?"}]),
        ("they drink it, then a word with a companion", "I'll drink my healing draught, then tell Odly to rest.", "",
         [{"kind": "talk", "target": ODLY, "speech": "Rest."}])):
    got = use("healing_draught", text, target, then)
    check(f"a draught the player takes themself is theirs ({label})", own(got), got)
got = use("healing_draught", "I use a healing draught on Odly, then tell Odly to rest.", ODLY, [{"kind": "talk", "target": ODLY, "speech": "Rest."}])
check("a name two steps are aimed at, the reading saying so of the draught: it is hers", hers(got), got)
ws.to_pack(inv.make_good("healing_draught", 1))
ws.player.character.health = pools.maximum(ws.player.character, "health") // 2
had, was = carrying("healing_draught"), ws.player.character.health
ws.command("#useitem healing draught")
check("the pack's Use button is the player's own", carrying("healing_draught") == had - 1 and ws.player.character.health > was, (had, carrying("healing_draught")))

# ---- what counts as the player saying they take it themself
yes = ("I drink it.", "I quickly eat the ration.", "I'll drink the draught.", "I'd drink the draught now.", "I down the draught.", "I use it on myself.")
no = ("I have Odly drink the draught.", "I make her eat.", "Odly drinks it.", "I use the draught on Odly.", "I let Thavathiel sip it.")
check("the first person taking it is read as that, and someone else being made to is not",
      all(actions.takes_oneself(t) for t in yes) and not any(actions.takes_oneself(t) for t in no),
      ([t for t in yes if not actions.takes_oneself(t)], [t for t in no if actions.takes_oneself(t)]))

g.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
