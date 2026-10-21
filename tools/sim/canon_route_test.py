"""Where a claim goes (engine/canon.py route): is it durable, what kind is it, how long does it live, is it worth keeping? Common
knowledge and facts of the scene are dropped; an opinion of a particular person is kept under that person's name (the player, a
companion, someone outside the party), never as a trait; a claim true for a while becomes an ongoing situation that expires; one true
only now lasts a day. A pair's relationship is written with what each has said of the other, and never another pair's opinions."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
from engine import canon, quirks
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def hire(i, name, role):
    m = {"id": f"c{i}", "name": name, "role": role, "level": 3, "permanent": True, "temper": ["blunt"], "motive": "coin", "line": "will not take from the poor",
         "bond": 20, "memories": [], "said": [], "talk": [], "blurb": "a hired hand"}
    quirks.roll(m, random.Random(i)); m["details"] = []
    return m
bram, isel, tam = hire(1, "Bram Voss", "fighter"), hire(2, "Isel Quill", "priest"), hire(3, "Tamsin Reed", "ranger")
F = lambda **k: dict({"subject": "self", "kind": "backstory", "weight": "personal", "lasts": "years", "common": False}, **k)
lines = [("Bram Voss", "We are still in Parth. The guild exists, as ever. My father ran a forge in the Great River country. I mean to see the coast before "
          "winter. I am nursing a cracked rib. I am hungry right now. You fight like a mule. Odo is a liar."),
         ("Tamsin Reed", "I'd rather have Isel's hands on my wounds than anyone else's.")]
stub.extract = lambda u: {"facts": [
    F(speaker="Bram Voss", subject="world", claim="We are still in Parth.", lasts="now"),
    F(speaker="Bram Voss", subject="world", claim="The guild exists.", common=True),
    F(speaker="Tamsin Reed", kind="trait", claim="I'd rather have Isel's hands on my wounds than anyone else's."),
    F(speaker="Bram Voss", claim="My father ran a forge in the Great River country."),
]}
got = canon.extract(lines, {"Bram Voss": [], "Tamsin Reed": [], "Isel Quill": []})
canon.EVENTS.clear()
verdicts = {}
check("'We are still in Parth' is a fact of the scene, not a belief: dropped", "world" not in got.get("Bram Voss", {}), got.get("Bram Voss"))
check("'The guild exists' is common knowledge: dropped", not any("guild exists" in t for t in sum((v for k, v in got.get("Bram Voss", {}).items() if k != "_weight" and isinstance(v, list) and v and isinstance(v[0], str)), [])))
check("a 'trait' that is really a feeling about Isel is kept as Tamsin's opinion of Isel, not a trait",
      got.get("Tamsin Reed", {}).get("opinion") == [("Isel Quill", "I'd rather have Isel's hands on my wounds than anyone else's.")] and "trait" not in got.get("Tamsin Reed", {}), got.get("Tamsin Reed"))
check("'My father ran a forge' is backstory, for good", got["Bram Voss"].get("backstory") == ["My father ran a forge in the Great River country."], got["Bram Voss"])

stub.extract = lambda u: {"facts": [
    F(speaker="Bram Voss", kind="intention", claim="I mean to see the coast before winter.", lasts="while"),
    F(speaker="Bram Voss", kind="trait", claim="I am nursing a cracked rib.", lasts="while"),
    F(speaker="Bram Voss", kind="trait", claim="I am hungry right now.", lasts="now"),
    F(speaker="Bram Voss", subject="player", claim="You fight like a mule.", weight="light"),
]}
got = canon.extract(lines[:1], {"Bram Voss": []})["Bram Voss"]
check("a plan stays an intention, with its own life", got.get("intention") == ["I mean to see the coast before winter."], got)
check("a trait true only for a while is an ongoing situation", got.get("situation") == ["I am nursing a cracked rib."], got)
check("one true only now is for today", got.get("moment") == ["I am hungry right now."], got)
check("what he thinks of the player is kept as his opinion of the player", got.get("opinion") == [("the player", "You fight like a mule.")], got)
stub.extract = lambda u: {"facts": [F(speaker="Bram Voss", subject="Odo", claim="Odo is a liar.", weight="light")]}
got_odo = canon.extract(lines[:1], {"Bram Voss": []})["Bram Voss"]
check("an opinion of someone outside the party (Odo) is kept too, under his name", got_odo.get("opinion") == [("Odo", "Odo is a liar.")], got_odo)

# kept, and offered back for as long as each stays true
day = 10
canon.review(bram, [], [], day, buckets=got).commit()
canon.review(bram, [], [], day, buckets=got_odo).commit()
recs = lambda d: [r["text"] for r in canon.records(bram, d)]
check("kept: the plan, the situation, today's state, the opinions", any("coast" in t for t in recs(day)) and any("cracked rib" in t for t in recs(day))
      and any("hungry" in t for t in recs(day)) and any("What you have said of the player: You fight like a mule." == t for t in recs(day))
      and any(t.startswith("What you have said of Odo") for t in recs(day)), recs(day))
check("a day later, today's state is gone", not any("hungry" in t for t in recs(day + 2)))
check("past two weeks, the cracked rib is no longer offered", not any("cracked rib" in t for t in recs(day + 15)) and any("coast" in t for t in recs(day + 15)))
check("past a month, the plan is gone too; opinions stay", not any("coast" in t for t in recs(day + 31)) and any("mule" in t for t in recs(day + 31)))
check("opinions_of finds what he said of someone by full or first name", canon.opinions_of(bram, "the player") == ["You fight like a mule."]
      and canon.opinions_of(bram, "Odo") == ["Odo is a liar."])

# a pair's relationship is written with what each said of the other, and never anyone else's
import shutil
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
shutil.rmtree("saves/canonroute", ignore_errors=True)
st = CampaignStore.open_or_create("canonroute")
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
tam["opinions"] = [{"about_id": "c2", "about": "Isel Quill", "text": "I'd rather have Isel's hands on my wounds than anyone else's.", "day": 1, "gravity": "light"}]
canon.IDS = {m["name"]: m["id"] for m in (bram, isel, tam)}
seen = []
import llm.gateway as gw
_g = gw._generate
def spy(task, system, user, schema, *a, **k):
    if task == "pair_dynamic":
        seen.append(user if isinstance(user, str) else user.render())
    return _g(task, system, user, schema, *a, **k)
gw._generate = spy
w.pair_dynamic(isel, tam)
w.pair_dynamic(bram, tam)
gw._generate = _g
check("Isel & Tamsin's relationship is written knowing what Tamsin said of Isel", seen and "WHAT EACH HAS SAID OF THE OTHER" in seen[0] and "Isel's hands" in seen[0], seen[:1])
check("...Bram & Tamsin's is not given Tamsin's opinion of Isel", len(seen) > 1 and "Isel's hands" not in seen[1], seen[1:])
st.close(); shutil.rmtree("saves/canonroute", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
