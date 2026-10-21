"""The stats window: the numbers are the ones combat uses, the pane data reaches the window, and a hired adventurer's hover sheet is there."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import config
import ui.console as uc
PANELS, SAID = [], []
uc.panel = lambda name, data: (PANELS.append((name, data)) or True)
uc.note = lambda m, *a, **k: SAID.append(str(m))
from engine import combat, party as P, statsheet
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/stats_test", ignore_errors=True)
st = CampaignStore.open_or_create("stats_test")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 600; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
ws = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/stats_test/turns.jsonl"

s = ws.player_sheet()
rows = {r[0]: r for sec in s["sections"] for r in sec["rows"]}
f = combat.fighter_from_character(ws.player.character)
check("the sections are offense, defense, pools and attributes", [x["title"] for x in s["sections"]][:4] == ["Offense", "Defense", "Pools", "Attributes"])
check("armor and ward are the fighter's own", rows["Armor"][1] == round(f.armor, 1) or rows["Armor"][1] == int(round(f.armor, 1)))
check("health is the maximum combat uses", rows["Health"][1] == round(f.max_hp, 1) or rows["Health"][1] == int(round(f.max_hp, 1)))
check("crit chance is the profile's", rows["Crit chance"][1] == f"{statsheet._n(combat.crit_profile(f)['chance'])}%")
foe = combat.Fighter(id="x", name="x", side="enemy", level=f.level, attrs={a: f.best_attr(f.weapon_attrs) for a in combat.ATTRIBUTES}, hp=1, max_hp=1)
check("hit chance is the one against an equal foe", rows["Hit chance"][1] == f"{statsheet._n(combat.hit_chance(f, foe, combat.Combat(fighters=[f, foe])))}%")
check("attack power sits between the damage range ends", float(rows["Damage range"][1].split(" to ")[0]) < float(rows["Attack power"][1]) < float(rows["Damage range"][1].split(" to ")[1]))
check("the armor note gives the share of damage turned away", "of physical damage" in rows["Armor"][2])

check("a caster's offense lists spell power and spell damage", all(k in rows for k in ("Spell power", "Spell damage")) or not f.moves)
ws.command("#stats")
check("#stats hands the window a stats panel", PANELS and PANELS[-1][0] == "stats" and PANELS[-1][1]["sections"][0]["title"] == "Offense", PANELS[-1:])

PANELS.clear()
ws.command("#character")
cp = next((d for n, d in PANELS if n == "character"), {})
check("the character pane hands the window each ability and passive by name with its hover lines",
      cp.get("abilities") and all(x["name"] and x["tip"][0] == ["h", x["name"]] and len(x["tip"]) >= 3 for x in cp["abilities"]) and
      all(x["tip"][0] == ["h", x["name"]] for x in cp.get("passives", [])), cp.get("abilities", [])[:1])
check("a hover line is [class, text]", all(len(l) == 2 for x in cp["abilities"] for l in x["tip"]))

offer = {"id": "1-0", "name": "Test Hire", "role": "archer" if "archer" in P.P["roles"] else "fighter", "level": 5, "rank": "F", "blurb": "x", "temper": ["blunt"], "motive": "coin", "line": "x"}
m = P.new_hire(offer, 10, 3)
ws.player.party.append(m)
PANELS.clear()
ws.show_party()
data = PANELS[-1][1]
adv = data["adventurers"][0]
check("a hired adventurer has a hover sheet with their name, offense and defense", adv["tip"] and adv["tip"][0][1].startswith("Test Hire") and any("Armor" in l[1] for l in adv["tip"]) and any("Crit chance" in l[1] for l in adv["tip"]), adv["tip"][:3])
check("the hover sheet is plain lines of [class, text]", all(len(l) == 2 for l in adv["tip"]))
theirs = P.fighter(m)
check("their sheet is the fighter combat builds for them", f"Health: {statsheet._n(theirs.max_hp)}" in [l[1] for l in adv["tip"]])
ws.player.party_mode = "with"
check("a hire travelling with you is one of the people here for the narrator", any(v[0] == "Test Hire" and "hired" in v[1] for v in ws.people_view()), ws.people_view())
TALK = []
ws.hire_talk = lambda mm, t: TALK.append((mm["name"], t))
from llm.contracts import ActionIntent
ws.on_talk(ActionIntent(kind="talk", target="hire:" + m["id"], speech="how are you holding up?"), "how are you holding up?")
check("talk the reader aims at a hire goes to them, by id and without their name", TALK == [("Test Hire", "how are you holding up?")], TALK)
ws.player.party_mode = "hold"
check("a hire holding back is not listed as here", not any(v[0] == "Test Hire" for v in ws.people_view()))
ws.player.party.clear()
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
