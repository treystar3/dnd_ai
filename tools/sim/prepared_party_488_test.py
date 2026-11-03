"""(f488) The hires and Maren: their talk is asked with no operation open (hire_chat, Maren's, and the canon check and extract a hire's
reply makes); a promise made to a hire is theirs to hold; a hire's memories are told from now in words, never a day number; a deed reaches
only the hires here and awake (one fallen, or held behind elsewhere, has no view of it); the fallen are remembered by state, never by
age, by the hires who travelled with them and not by one hired later (the narrator's as before); and Maren reads "shall we go?" from the
words alone, never by a second whole call."""
import sys
import types
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 6)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import operation, party as rules, truth
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

game = simlib.campaign("party_488", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter("guild_house")
LOG = []
real = gateway._client


def chat(**k):
    LOG.append((k["format"].get("title"), operation.current().kind if operation.current() else None))
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
h1 = {"id": "h1", "name": "Bram Hollin", "role": "fighter", "level": 3, "permanent": True, "temper": ["blunt"], "blurb": "a scarred sellsword",
      "active": True}
h2 = {"id": "h2", "name": "Isel Varn", "role": "healer", "level": 3, "permanent": True, "temper": ["gentle"], "blurb": "a quiet healer", "active": True}
ws.player.party = [h1, h2]
ws.player.party_mode = "with"
store.save_player(ws.player)

# ---- a hire's talk, asked with no operation open; a promise made to them kept
stub.plan = [{"kind": "talk", "target": "hire:h1", "speech": "I'll pay you double at the next town."}]
stub.a_CompanionReply = lambda u, k: {"speech": "I'll hold you to that.", "they_promised": "to pay double at the next town"}
LOG.clear()
ws.turn('I say to Bram, "I\'ll pay you double at the next town."')
stub.plan = None
del stub.a_CompanionReply
asked = [c for c in LOG if c[0] in ("CompanionReply", "Extracted", "CanonCheck")]
check("a hire's reply (and the canon calls it makes) are asked with no operation open", asked and all(op is None for _, op in asked), LOG)
check("...and none is in the ratchet's residue", not ({"hire_chat", "canon_extract", "canon_check"} & set(operation.LEGACY)), operation.LEGACY)
held = ws.store.load_player().party[0]
check("a promise made to a hire is theirs to hold", any("pay double" in m.get("text", "") for m in held.get("memories", [])), held.get("memories"))
picked = rules.pick_memories(held, "double pay", 3, day=ws.minutes // 1440 + 3)
check("a hire's memories are told from now in words, never a day number", picked and not any(p.startswith("day ") for p in picked), picked)

# ---- a deed reaches only the hires here and awake
ws.player.party = [dict(h1), dict(h2, fallen=True)]
crew = [m["id"] for m in ws.quirk_crew()]
check("a deed reaches the hires here and awake, never a fallen one", crew == ["h1"], crew)
ws.player.party_mode, ws.player.party_hold_at = "hold", "parth"
check("...and none held behind elsewhere", ws.quirk_crew() == [])
ws.player.party_mode, ws.player.party = "with", [dict(h1), dict(h2)]

# ---- the fallen: by state, for those who knew them
from engine import entities
ent = entities.begin(store, "hire", "hire:h0", "Ula Brand", ws.minutes - 90 * 1440, pronoun="she", people="human", owner="player",
                     data={"role": "archer", "knew": ["h1"], "place_name": "the Greywood"})
entities.move(store, ent, "dead", ws.minutes - 90 * 1440, "fell to the wolves")
scene = truth.scene_of(ws)
lines = lambda viewer: [f.text for f in scene.facts("fallen") if viewer.sees(f)]
check("ninety days on, the hire who travelled with her still has her among the fallen", any("Ula Brand" in t for t in lines(truth.viewer_for_hire("hire:h1"))),
      lines(truth.viewer_for_hire("hire:h1")))
check("...one hired after does not", not any("Ula Brand" in t for t in lines(truth.viewer_for_hire("hire:h2"))))
narrator = truth.Viewer(id="narrator", kind="narrator", groups=frozenset({"everyone"}))
check("...and the narrator's sixty days are as they were", not any("Ula Brand" in t for t in lines(narrator)))

# ---- Maren reads "shall we go?" from the words alone
n0 = len(LOG)
went = ws.mentor_talk_means_go("I think I understand most of it now, thank you kindly.")
check("Maren never makes a second whole call to read whether they mean to go", not went and len(LOG) == n0, LOG[n0:])
check("...plain going words still settle it", ws.mentor_talk_means_go("Let's go to the hall then."))

gateway._client = real
game.close()
import shutil
shutil.rmtree("saves/party_488", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
