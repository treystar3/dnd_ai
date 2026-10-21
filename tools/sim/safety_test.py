"""The safety net (f189): one transaction per turn, rolled back whole when the model fails partway; a save from a newer build is refused;
a backup is taken before any migration; a new database starts at the baseline schema; the campaign invariant checker finds broken
references and repairs nothing; opinions and the last fight's hurt and carried lists are kept by stable id."""
import random, shutil, sys, sqlite3
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
uc.note = lambda m, *a, **k: None; uc.narrate = lambda t: None; uc.say = lambda *a, **k: None
from storage import migrations, invariants
from storage.campaign import CampaignStore, PlayerState, PlaceState, SaveTooNew
from llm.gateway import LLMError
from scenes.world import WorldScene
from npc.traits import load_traits
from world.loader import load_world
from npc.models import NPC
from engine import canon
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

root = Path("saves/safety"); shutil.rmtree(root, ignore_errors=True)
st = CampaignStore.open_or_create("safety")
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
world = load_world()
w = WorldScene(st, world, load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/safety/turns.jsonl"

# ---- one transaction per turn: a model failure partway rolls the whole turn back, memory and all
coins0 = w.player.character.coins
turn0 = st.meta.turn
def _boom(self_, text):
    w.player.character.coins -= 7                    # the action changed something and saved it...
    st.save_player(w.player)
    st.meta.turn += 1
    raise LLMError("the model failed after the save")
_h = WorldScene.handle
WorldScene.handle = _boom
ok = w.turn("I pick up a rock")
WorldScene.handle = _h
check("a turn in which the model fails after a save is rolled back: nothing kept", ok is False and st.load_player().character.coins == coins0
      and CampaignStore.open_or_create("safety").meta.turn == turn0, (ok, st.load_player().character.coins, coins0))
check("...and what the scene holds in memory is put back too", w.player.character.coins == coins0, w.player.character.coins)
w.mentor_intercept = lambda t: False                  # a new game in Parth: Maren's first meeting would wait on the keyboard
ok = w.turn("look around")
check("an ordinary turn commits", ok and CampaignStore.open_or_create("safety").meta.turn > turn0, (ok, st.meta.turn))

# ---- a save from a newer build is refused
st.set_version(migrations.CURRENT + 5)
st.close()
try:
    CampaignStore.open_or_create("safety"); refused = False
except SaveTooNew as e:
    refused = True; msg = str(e)
check("a save made by a newer build is refused with a plain message", refused and "newer version" in msg, msg if refused else "opened")
db = sqlite3.connect(root / "campaign.db"); db.execute(f"PRAGMA user_version = {migrations.CURRENT}"); db.commit(); db.close()

# ---- a migration takes a backup first; a fresh database starts at the baseline and needs none
st = CampaignStore.open_or_create("safety")
check("no backup is taken when nothing needs migrating", not (root / "backups").exists() or not list((root / "backups").glob("*.db")))
migrations.MIGRATIONS.append((migrations.CURRENT + 1, "test step", lambda s: s.execute("CREATE TABLE IF NOT EXISTS t_test (x INTEGER)")))
migrations.run(st)
backs = list((root / "backups").glob("campaign_v*.db"))
check("a migration first backs the database up, as it was", len(backs) == 1 and f"v{migrations.CURRENT}" in backs[0].name, [b.name for b in backs])
check("...and the step's own DDL ran through the store", st._db.execute("SELECT name FROM sqlite_master WHERE name='t_test'").fetchone() is not None)
old = sqlite3.connect(backs[0]); check("...the backup opens and has no such table (it is from before)", old.execute("SELECT name FROM sqlite_master WHERE name='t_test'").fetchone() is None); old.close()
migrations.MIGRATIONS.pop(); st.set_version(migrations.CURRENT)
for k in range(4):
    st.backup("extra")
check("only the last few backups are kept", len(list((root / "backups").glob("campaign_*.db"))) <= 3)

# ---- the invariant checker
check("a sound campaign has no problems", invariants.validate_campaign(st, world) == [], invariants.validate_campaign(st, world))
ps = st.load_place("parth"); ps.populated = True; ps.residents = ["ghost_1"]; st.save_place(ps)
n = NPC(id="n_far", name="Far Away", people="human", role="farmer", location="nowhere_land"); st.save_npc(n)
p = st.load_player(); p.party.append({"id": "h9", "name": "Nobody Real", "npc": "missing_npc", "role": "fighter"}); p.party_relations["h1|h9"] = {"score": 0}; st.save_player(p)
probs = [str(x) for x in invariants.validate_campaign(st, world)]
check("...a resident who is not a person is found", any("ghost_1" in x for x in probs), probs)
check("...a person standing in no place of the world is found", any("nowhere_land" in x for x in probs), probs)
check("...a party member standing in for a missing npc is found", any("missing_npc" in x for x in probs), probs)
check("...a relation naming someone never in the party is found", any("h1" in x and "party_relations" in x for x in probs), probs)
check("...and nothing was repaired", st.load_place("parth").residents == ["ghost_1"])

# ---- stable ids: opinions by id, the last fight's hurt and carried by id
canon.IDS = {"Isel Quill": "h2", "Tamsin Reed": "h3"}
m = {"id": "h3", "name": "Tamsin Reed"}
canon.keep_opinions(m, [("Isel", "I would trust Isel's hands over anyone's."), ("the player", "You fight like a mule."), ("Odo", "Odo is a liar.")], 1)
check("an opinion of a known person is kept under their id, the name only for display", m["opinions"][0]["about_id"] == "h2" and m["opinions"][0]["about"] == "Isel", m["opinions"])
check("...of the player under 'player'; of someone known only by name, under the name", m["opinions"][1]["about_id"] == "player" and m["opinions"][2]["about_id"] == "Odo")
check("...and found by id, by full name or by first name", canon.opinions_of(m, "h2") == canon.opinions_of(m, "Isel Quill") == canon.opinions_of(m, "Isel") == ["I would trust Isel's hands over anyone's."])
import types
w2 = WorldScene(st, world, load_traits(), st.load_player())
w2.player.party = [{"id": "h1", "name": "Bram Voss", "permanent": True, "role": "fighter", "level": 3, "bond": 20, "memories": [], "said": [], "talk": []}]
ally = types.SimpleNamespace(id="ally_h1", name="Bram Voss", alive=True, hp=1, max_hp=100)
w2.party_after_fight([], [ally], won=True, hard=True)
lf = w2.player.party_last_fight
check("the last fight keeps who was hurt and carried by id as well as by name", lf.get("hurt_ids") == ["h1"] and lf.get("carried_ids") == ["h1"] and lf.get("hurt") == ["Bram Voss"], lf)

st.close(); shutil.rmtree(root, ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
