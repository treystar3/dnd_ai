"""(f374) Why the first logged playthrough felt less human than the ones before, each fixed: Maren, a person of the world after the lesson,
had been drawn a townsperson's voice kit and a rolled grievance, so she answered in six-word lines, called herself rank F and harped on
'those boys of yours'; every person carried six or seven speech habits at once, and a hire repeated each question back before answering;
every line of hers was framed by the narrator, her weight shifting in a third of them; half the frames were rewritten for trailing
participles at a second call; a return visit was told as 'Since your last visit, Maren Holt now scrapes mud from a cloak'."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
STUB = simlib.Stub("warrior", 5)
simlib.install(STUB)
import ui.console as uc
NOTES, SAID, FRAMED = [], [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.narrate = lambda *a, **k: None
uc.npc_says = lambda label, speech, gesture="": SAID.append((label, speech, gesture))
uc.dialogue = lambda before, label, speech, after: FRAMED.append((label, speech))
uc.say = lambda text, speaker="": SAID.append((speaker, text, ""))
from engine import doings, mentor, voice_rules, voices
from llm.contracts import DialogueFrame
from npc import prompts as npr
from npc.models import NPC
from npc.traits import load_traits
from scenes import voice, world_prompts as wp
from scenes.world import WorldScene
from storage import migrations
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- Maren after the lesson keeps the voice she was written with
char, _ = simlib.make_character("warrior", random.Random(1))
pl = PlayerState(character=char, location="parth")
pl.mentor["chat"] = [["Player", "that was amazing how did you learn to fight like that"],
                     ["Maren", "Practice and some hard lessons from people who knew more than I did. Most of it comes down to knowing where the gaps are."],
                     ["Maren", "Ugh. That one got me. Say 'give Maren a healing draught', with my name in it so it comes to me."],
                     ["Maren", "Type #board and take the hunt."],
                     ["Maren", "Fine."]]
npc = mentor.make_npc(pl, 600, 3, "guild_house")
check("her personality is told of her, with no lesson still to run", npc.personality.startswith("A broad-shouldered") and "You are" not in npc.personality
      and "first guild contract" not in npc.personality, npc.personality[:120])
check("...her rank is A", npc.rank == "A")
check("...she has no habits drawn for her, and is marked as written by hand", npc.speech.get("own_voice") and voices.lines(voices.kit_of(npc.speech)) == [])
check("...her samples are what she said to this player, never a command she taught or a word, then lines written in her voice",
      npc.speech["samples"][0].startswith("Practice and some hard lessons") and not any("#" in s or "give Maren" in s or s == "Fine." for s in npc.speech["samples"])
      and len(npc.speech["samples"]) == 5 and npc.speech["samples"][1] == mentor.M["npc"]["samples"][0], npc.speech["samples"])
check("...and no doing yet, so the hall giving her one is no change to tell", npc.activity == "")
check("a person written by hand rolls no stance: her mood is how she is", all(voice_rules.roll_stance(npc, 600, random.Random(k)) == "" for k in range(30)))
from engine import voice_profile
check("...and gets no HOW YOU TALK lines from a people or a culture", voice_profile.resident_lines(npc, random.Random(1)) == ("", [], []))
npc.activity = "picking mud off a cloak with a knife"
text = npr.conversation_prompt(npc, types.SimpleNamespace(name="the adventurers' guild house", visible=[]), [], [], [], "Maren, you're still here?", [], [], []).render()
check("her prompt shows her voice and how she sounds, and no townsperson's habits", "VOICE: Talks like a person across a table" in text and "HOW YOU SOUND" in text
      and "Practice and some hard lessons" in text and "HOW YOU TALK" not in text and "short sentences, one thing in each" not in text, text[:600])
old = NPC(id="t1", name="Tamsin", people="human", role="farmer", location="parth", voice="slow and gravelly",
          speech={"kit": {"length": "terse", "sentences": "short", "questions": "never", "opening": "matter", "contractions": "full", "address": "formal", "refusing": "excuse", "words": "exact"}})
text = npr.conversation_prompt(old, types.SimpleNamespace(name="Parth", visible=[]), [], [], [], "hi", [], [], []).render()
check("a townsperson with a kit still has no written VOICE line", "VOICE:" not in text)

# ---- in a scene: her rank, her frames
world = load_world()
shutil.rmtree("saves/playthrough2_test", ignore_errors=True)
store = CampaignStore.open_or_create("playthrough2_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
store.save_player(PlayerState(character=char, location="guild_house", guild_rank="F"))
ws = WorldScene(store, world, load_traits(), store.load_player())
check("as a guild contractor she knows herself as rank A, not a drawn F", any("You are a rank-A member" in l for l in ws.npc_context(npc)), ws.npc_context(npc)[:2])
other = NPC(id="gc_x", name="Bors", people="human", role="guild_contractor", location="guild_house")
check("...while another contractor's rank is still drawn from their id", any("member of the adventurers' guild" in l and "rank-A" not in l for l in ws.npc_context(other)))

asked = []
def fake(task, system, request, schema, **k):
    asked.append((task, request))
    if schema is DialogueFrame:
        return DialogueFrame(before="She sets the cup down, her eyes returning to the door. The dog stirs, its tail thumping the boards.", after="")
    return schema.model_validate({"text": "x"})
real = voice.generate
voice.generate = fake
ws.player.mentor["introduced"] = True
ws.player.mentor["stage"] = "board"
ws.present = []
FRAMED.clear(); SAID.clear(); asked.clear()
ws.mentor_show("Good. Then let's get you on the board.", reply_to="i'm no bandit")
ws.mentor_show("Take the wolf hunt; it's the only one up for you.", reply_to="ok")
ws.mentor_show("Go on, then.", reply_to="ok", gesture="nods at the board")
check("her first line in this stage here is framed, the next ones are her words alone with her own gesture",
      len(FRAMED) == 1 and [s for _, s, _ in SAID] == ["Take the wolf hunt; it's the only one up for you.", "Go on, then."] and SAID[-1][2] == "nods at the board", (FRAMED, SAID))
check("...and the frame is not rewritten for its trailing participles: one call, not two", len(asked) == 1, [t for t, _ in asked])
ws.player.mentor["stage"] = "hunt"
ws.mentor_show("Right. The Greywood, then.", reply_to="let's go")
check("a new stage of the lesson is a moment: framed again", len(FRAMED) == 2)
ws._framed_here = set()
ws.mentor_show("Right. The Greywood, then.", reply_to="let's go")
check("...and so is a new place", len(FRAMED) == 3)
asked.clear()
voice.fresh("narrate", "s", "r", DialogueFrame, [], fields=("before", "after"))
check("a narration passage that ends sentences on a trailing participle is still rewritten once", len(asked) == 2 and "TRAILING PARTICIPLE" in asked[-1][1])
voice.generate = real

# ---- a return visit: shown, not reported, and sentences that do not run together
n = types.SimpleNamespace(label=lambda: "the sharp-eyed scout")
lines = doings.changed_lines([(n, "picking mud off a cloak with a knife", "counting arrows back into a quiver")])
check("a person doing something else is told as what they do now, to be shown", lines == ["the sharp-eyed scout is counting arrows back into a quiver now, not picking mud off a cloak "
                                                                                          "with a knife as when the player was last here; show it, never report it as a change."], lines)
check("...and someone with no doing before (Maren, new to the hall) is no change at all", doings.changed_lines([(n, "", "picking mud off a cloak")]) == [])
req = wp.narration_request("day 1", types.SimpleNamespace(name="the hall", type="guild", visible=[]), [], "arrive", "",
                           happenings=["the smith is shoeing a horse now", "Planting time: the fields are full."])
check("lines handed to the narrator end as sentences, one after another", "the smith is shoeing a horse now. Planting time: the fields are full." in req, req[req.find("LATELY"):][:200])

# ---- an older save: her record is brought up to her own voice
before = NPC(id="maren", name="Maren Holt", people="human", role="guild_contractor", location="guild_house", tier="significant",
             personality="You are Maren Holt... You are looking after a new adventurer through their first guild contract.", activity="between jobs",
             speech={"kit": dict(old.speech["kit"])})
store.save_npc(before)
store.set_version(5)
store.close()
store = CampaignStore.open_or_create("playthrough2_test")
after = store.load_npc("maren")
check("an older save's Maren is brought to the voice she was written with", store.version == migrations.CURRENT and after.speech.get("own_voice")
      and after.rank == "A" and "You are" not in after.personality and voices.lines(voices.kit_of(after.speech)) == [], (store.version, after.speech, after.personality[:60]))
store.close()
shutil.rmtree("saves/playthrough2_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
