"""(f382) From the dig into the second playthrough and the f375 night.
- People know the player again: nobody once greeted the player as someone they knew. A person met before, spoken to after a while, is
  told it is a return (when they last spoke, the last thing between them), the frame shows them knowing who it is, and the narrator is
  told who in a room knows the player.
- Companion small talk: two companions greeted the player with the same 'Morning.'; a misspelt speaker name sent an exchange back and the
  retry spoke a broken line; the frame around an exchange toured the room and named the player in the third person; the talk began on a
  childhood detail out of nowhere. A name near enough is that name; one line said again by the next is sent back; the frame stays on the
  people; a thing of their own comes up most when something here touches it; the job they are on is something to talk about.
- Maren leaves Parth once the lesson is over: an older save that has her waiting at the hall is moved on."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 2)
simlib.install(stub)
import llm.gateway as gw
CALLS = []
_chat = gw._client.chat
def chat(*a, **k):
    CALLS.append((k.get("format", {}).get("title", "?"), k.get("messages") or []))
    return _chat(*a, **k)
gw._client = types.SimpleNamespace(chat=chat)
import ui.console as uc
for f in ("narrate", "note", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, f, lambda *a, **k: None)
from pydantic import ValidationError
from engine import banter, mentor, quests, recognition
from llm.contracts import CompanionReply, Exchange
from npc.traits import load_traits
from scenes import world_prompts as wp
from scenes.world import WorldScene
from storage import migrations
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
shutil.rmtree("saves/know_again_test", ignore_errors=True)
store = CampaignStore.open_or_create("know_again_test")
store.meta.seed = 3; store.meta.minutes = 120; store.meta.turn = 1; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="guild_house", guild_rank="F"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("guild_house")
clerk = ws.clerk_here()

def asked_npc():
    return next((m[-1]["content"] for t, m in CALLS if t == "NPCReply"), "")

# ---- the first talk is no return; talk again the same hour is the same visit
CALLS.clear()
stub.plan = [{"kind": "talk", "target": clerk.id, "speech": "Any work going?"}]
ws.turn("Any work going?")
check("a first meeting is no return", "THEY ARE BACK" not in asked_npc(), asked_npc()[-400:])
check("...and when they last spoke is kept, to the minute", store.load_npc(clerk.id).last_talk_at >= 120, store.load_npc(clerk.id).last_talk_at)
ws.end_conversation()
CALLS.clear()
stub.plan = [{"kind": "talk", "target": clerk.id, "speech": "One more thing."}]
ws.turn("One more thing.")
check("talking again within the hour is no return", "THEY ARE BACK" not in asked_npc())

# ---- two days later
ws.end_conversation()
ws.enter("trading_square")
store.meta.minutes += 2 * 1440; store.save_meta()
ws.enter("guild_house")
seen = {l: d for l, d, _ in ws.people_view()}
clerk = ws.clerk_here()
check("the narrator is told who in the room knows the player", "Knows the player; last spoke with them two days ago" in seen.get(clerk.label(), ""), seen.get(clerk.label()))
CALLS.clear()
REASONS = []
_frame = ws.frame_reasons
ws.frame_reasons = lambda *a, **k: (REASONS.append(_frame(*a, **k)), REASONS[-1])[1]
stub.plan = [{"kind": "talk", "target": clerk.id, "speech": "Morning."}]
ws.turn("Morning.")
said = asked_npc()
check("back after two days, the person is told it is a return, and when", "THEY ARE BACK: you last spoke with them two days ago" in said, said[-600:])
check("...the frame shows them knowing who it is", REASONS and any("know the player" in r for r in REASONS[-1]), REASONS)
CALLS.clear()
stub.plan = [{"kind": "talk", "target": clerk.id, "speech": "And the board?"}]
ws.turn("And the board?")
check("...once, at the start of the talk", "THEY ARE BACK" not in asked_npc())
check("the way it is put", recognition.ago(1440 * 10 + 60, 1440 * 9) == "yesterday" and recognition.ago(1440 * 20, 1440 * 10) == "about a week ago"
      and recognition.ago(1440 * 90, 0) == "months ago")

# ---- companions: no second 'Morning.'
def comp(speech, heard):
    try:
        CompanionReply.model_validate({"speech": speech, "gesture": ""}, context={"heard": heard}); return ""
    except ValidationError as e:
        return str(e)
check("a companion does not say back what another just said", "someone else has just said" in comp("Morning.", ["Morning."]))
check("...but answers in their own words freely", comp("Aye. Early, though.", ["Morning."]) == "")

# ---- exchanges among the party
ctx = {"speakers": ["Thavathiel Liaralor", "Deth Stone"], "lines": (2, 4), "material": []}
def ex(*pairs):
    try:
        return Exchange.model_validate({"lines": [{"speaker": a, "text": b} for a, b in pairs]}, context=ctx), ""
    except ValidationError as e:
        return None, str(e)
got, why = ex(("Thavathiel Liaror", "The crates never matched their labels."), ("Deth", "Then someone was skimming."))
check("a speaker name near enough is that name, without a second call", got is not None and [l.speaker for l in got.lines] == ["Thavathiel Liaralor", "Deth Stone"], why)
got, why = ex(("Maren Holt", "Well."), ("Deth Stone", "Hm."))
check("...while someone not in the talk is still sent back", got is None and "speaker must be one of" in why, why)
got, why = ex(("Thavathiel Liaralor", "Morning."), ("Deth Stone", "Morning."))
check("one line said again by the next is sent back", got is None and "says again what was just said" in why, why)
check("the frame around an exchange stays on the people and never closes on the room", "Never the room" in wp.EXCHANGE_SYSTEM
      and "the road, the fire, the room, the weather" not in wp.EXCHANGE_SYSTEM and "never go round the" in wp.EXCHANGE_SYSTEM)
check("...and the player in it is you", "always 'you'" in wp.exchange_request("day 1", world.places["parth"], ["A"], [], "x", "y", [], "", "Ironbound Vanguard"))

# ---- what the party talks about
ws.enter("trading_square")
h1 = {"id": "h1", "name": "Thavathiel Liaralor", "role": "mage", "level": 3, "permanent": True, "temper": ["sullen"], "blurb": "a sullen mage",
      "details": ["Their family were merchants with a fleet of spice ships.", "They once fell through the ice on a frozen pond."]}
h2 = {"id": "h2", "name": "Deth Stone", "role": "priest", "level": 3, "permanent": True, "temper": ["grim"], "blurb": "a grim priest", "details": []}
from engine import relevance
_pick = relevance.pick
relevance.pick = lambda q, items, k=2, floor=None: [i for i in items if "spice" in q and "stalls" in i][:k]       # the helper model's call
ws.place.visible.append("A few permanent stalls; on market day, carts and traveling merchants fill the rest.")
got = ws.personal_topic(h1, random.Random(1), "ease", scene=ws.banter_scene())
check("a thing of their own that something here touches comes first, with what touched it", got and "spice" in got[0] and "stalls" in got[2], got)
relevance.pick = _pick
ws.place.visible.pop()
q = quests._quest("hunt", "E", "Hunt 4 griffons in the Greyhollow foothills", ws.minutes, place="greyhollow_foothills", creature="griffon", count=4)
ws.player.quests = [q]
kinds = {}
for i in range(60):
    k, text, _ = ws.banter_hook([h1, h2], "travel", random.Random(i))
    kinds.setdefault(k, text)
check("the job the party is on is something to talk about", "errand" in kinds and "Hunt 4 griffons" in kinds["errand"], list(kinds))

# ---- Maren, on an older save, is moved on
store.save_npc(mentor.make_npc(ws.player, ws.minutes, 1, "guild_house").model_copy(update={"gone": ""}))
hall = store.load_place("guild_house"); hall.residents.append("maren"); store.save_place(hall)
migrations._v7_maren_moves_on(store)
check("an older save's Maren, waiting at the hall, has left Parth", store.load_npc("maren").gone and "maren" not in store.load_place("guild_house").residents)
check("...and Parth heard it", any("Maren Holt" in n["text"] for n in store.load_world_state().get("news", [])))
check("the save version moves on with it", migrations.CURRENT >= 7)

store.close()
shutil.rmtree("saves/know_again_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
