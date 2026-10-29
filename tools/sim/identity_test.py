"""(f392) Who someone is, from one place, given to every writer; and the registry with its lifecycles.
Two nights found a companion "she" in her fights and "he" in the frames around her words (Deth: 77 frames), an elf turned "the dwarf
with the ginger beard", and growth lines written "turns their back on the player" shown as they were. Four places kept gender and the
narrator was given none of them."""
import random, shutil, sqlite3, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import llm.gateway as gw
SENT = []
_chat = gw._client.chat
def chat(*a, **k):
    SENT.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
for f in ("narrate", "say", "npc_says", "dialogue", "ledger", "note"):
    setattr(uc, f, lambda *a, **k: None)
from engine import domain_events, entities, party, quirks, truth
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/identity_test", ignore_errors=True)
store = CampaignStore.open_or_create("identity_test")
store.meta.seed = 3; store.meta.minutes = 600; store.meta.turn = 1; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.pronoun, char.people = "she", "dwarf"
store.save_player(PlayerState(character=char, location="trading_square", guild_rank="E"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("trading_square")
offers = party.roster(3, "guild_house", 0, 5, 100, [])[:3]
ws.player.party = [party.new_hire(o, 5, 0) for o in offers]
ws.player.party_mode = "with"
m0 = ws.player.party[0]

# ---- one answer to "who is this"
who = entities.identity(ws, f"hire:{m0['id']}")
check("a hire's identity is their kept pronoun and their people", who and who.pronoun == m0["pronoun"] and who.people == entities.people_word(world, m0["people"]),
      who)
me = entities.identity(ws, "player")
check("the player's is what they chose at the Threshold", me.pronoun == "she" and me.people == "dwarf", me)
from npc.models import NPC
npc = NPC(id="ivy_test", name="Ivy Marrow", gender="female", people="elf", role="merchant", location="trading_square", description="A tall trader.",
          activity="weighing spice")
store.save_npc(npc)
ws.residents = ws.residents + [npc]
ws.present = ws.present + [npc]
if npc is not None:
    nid = entities.identity(ws, npc.id)
    check("a townsperson's is their record's gender and people", nid.pronoun == {"male": "he", "female": "she"}.get(npc.gender, "they")
          and nid.people == entities.people_word(world, npc.people), (nid, npc.gender, npc.people))
    p = next(x for x in truth.scene_of(ws).present_people() if x.id == npc.id)
    check("...and the truth layer every speaker reads says it", f"({nid.pronoun}, {nid.people})" in p.desc, p.desc)
check("Maren is she, human", entities.identity(ws, "maren").tag() == "she, human")
lines = entities.cast_lines(ws)
check("everyone travelling with the player is in the cast, each with pronoun and people",
      all(any(l.startswith(f"{m['name']}: {m['pronoun']}, {entities.people_word(world, m['people'])}") for l in lines) for m in ws.player.party), lines)

# ---- every writer is told
SENT.clear()
ws.narrate("The player looks around the square.", "I look around.")
narr = [msgs for t, msgs in SENT if t == "Narration"]
check("the narrator is told who is who", narr and entities.WHO_HEAD in narr[-1][-1]["content"] and m0["name"] in narr[-1][-1]["content"],
      narr[-1][-1]["content"][-900:] if narr else "no call")
SENT.clear()
ws.companion_show(m0, "Hold on a moment.", reply_to="I ask them to wait.", why=["the player spoke to them"])
frames = [msgs for t, msgs in SENT if t == "DialogueFrame"]
check("a companion's frame is told who they are", frames and f"{m0['pronoun']}, {entities.people_word(world, m0['people'])}" in frames[-1][-1]["content"]
      and entities.WHO_HEAD in frames[-1][-1]["content"], frames[-1][-1]["content"][:700] if frames else "no frame")

# ---- the engine's own lines about one person
m = dict(m0); m.pop("pronoun", None)
check("a hire with no pronoun read yet gets theirs drawn, not 'they'", quirks.pronouns(m)["they"] in ("she", "he"), quirks.pronouns(m))
check("a line written about 'they' is said with their pronoun and the verbs to match",
      entities.gendered("turns their back on the player without thinking about it, which they do with no one", "she")
      == "turns her back on the player without thinking about it, which she does with no one")
check("...and adverbs and contractions are minded", entities.gendered("They always keep their blade clean; they're proud of it.", "he")
      == "He always keeps his blade clean; he's proud of it.")
check("...and 'they' is left as written for them", entities.gendered("they keep their word", "they") == "they keep their word")

# ---- the registry and its lifecycles
domain_events.RECENT.clear()
e = entities.begin(store, "captive", "captive:x1", "Skarn", ws.minutes, pronoun="he", people="orc", owner="player", links={"npc": "x1"})
check("a captive starts escorted, kept in the save", store.load_entity("captive:x1").state == "escorted" and store.find_entities(kind="captive", state="escorted"))
entities.move(store, e, "released", ws.minutes + 5, "let go")
check("a move is kept with its history, and the player no longer holds them", store.load_entity("captive:x1").state == "released"
      and store.load_entity("captive:x1").owner == "" and store.load_entity("captive:x1").history[-1][1:] == ["escorted", "released", "let go"])
check("...and published on the event bus", any(getattr(ev, "kind", "") == "state_changed" and ev.ref == "captive:x1" and ev.now == "released"
                                               for ev in domain_events.RECENT), list(domain_events.RECENT)[-2:])
try:
    entities.move(store, store.load_entity("captive:x1"), "escorted", ws.minutes + 6)
    check("a move the lifecycle does not allow is refused", False)
except ValueError:
    check("a move the lifecycle does not allow is refused", True)
check("the lifecycles are well formed", entities.problems() == [], entities.problems())

# ---- an older save gains the registry
store.close()
db = sqlite3.connect("saves/identity_test/campaign.db")
db.execute("DROP TABLE entities"); db.execute("PRAGMA user_version = 8"); db.commit(); db.close()
store = CampaignStore.open_or_create("identity_test")
check("an older save opens with the registry in place", store.version >= 9 and store.find_entities() == [])
store.close()
shutil.rmtree("saves/identity_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
