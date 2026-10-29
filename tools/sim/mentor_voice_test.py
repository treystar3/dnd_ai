"""Maren's words come from the model inside limits: every figure, command and quoted phrase survives, nothing new is added, fixed rules are
said exactly as written, and a bad or failed answer means the written line is said instead. Also the model warm-up."""
import sys, random, shutil, time
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
config.FREE_MENTOR = False            # these tests are about the line-by-line path; the free path has its own at the end
import ui.console as uc
SAID = []
uc.say = lambda t, s="": SAID.append((s, t))
uc.dialogue = lambda b, s, t, a: SAID.append((s, t))
uc.npc_says = lambda s, t, g="": SAID.append((s, t))        # her words alone, once the moment has had its frame (f374)
uc.narrate = lambda t: None
uc.note = lambda m, *a, **k: None
from engine import mentor
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
import llm.gateway as gw
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

cv = mentor.check_voice
src = ["Type #board to read it and #quests to see what you hold. You can hold 2 at a time.", "Say 'search for wolves' and give it a little time.", "How new are you?"]
good = ["Type #board and read it, and #quests shows what you hold. Two at a time, no more? No: you can hold 2 at a time.", "Say 'search for wolves' and give it a moment.", "How new are you, exactly?"]
check("a fair rewording passes", cv(src, good) == "" or "changes how many" in cv(src, good), cv(src, good))
ok = ["Type #board to read it; #quests shows what you hold. You can hold 2 at a time.", "Say 'search for wolves' and give it a moment.", "How new are you, exactly?"]
check("a clean rewording passes", cv(src, ok) == "", cv(src, ok))
check("a missing line is refused", "exactly 3" in cv(src, ok[:2]))
check("a dropped figure is refused", "figure 2" in cv(src, [ok[0].replace("2 at a time", "a couple at a time")] + ok[1:]))
check("a dropped command is refused", "#board" in cv(src, [ok[0].replace("#board", "the board")] + ok[1:]))
check("quoted words must be exact", "search for wolves" in cv(src, [ok[0], "Say 'look for wolves' and wait.", ok[2]]))
check("a new number is refused", "adds a number" in cv(src, [ok[0] + " Three of them.", *ok[1:]]) or "how many" in cv(src, [ok[0] + " Three of them.", *ok[1:]]))
check("a changed amount in words is refused", "how many" in cv(src, [ok[0], "Say 'search for wolves' and give it five minutes.", ok[2]]))
check("talk of a game is refused", "game" in cv(src, [ok[0], "Say 'search for wolves' - it is how the game works.", ok[2]]))
check("a question stays a question", "question" in cv(src, [ok[0], ok[1], "You are new, then."]))
check("it cannot run on", "too long" in cv(src, [ok[0], ok[1], "How new are you " + "really " * 40 + "?"]))
check("a contraction is not a quoted phrase", mentor._facts_of("Don't look so worried. You can't know, isn't it?")[2] == set())

shutil.rmtree("saves/mv", ignore_errors=True)
st = CampaignStore.open_or_create("mv")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/mv/turns.jsonl"
W = "Hand the contract in at the guild hall. The clerk will have your coin. Go on."
FIX = "There are seven ranks, F at the bottom to S at the top."

stub.voice = lambda lines: [l.replace("Hand", "Take").replace("clerk", "clerk, patient as ever,") for l in lines]
SAID.clear()
w.mentor_say(W, mentor.Fixed([FIX]), "Short one.", beat="test")
t = SAID[-1][1].split("\n")
check("her lines are put in her words", t[0].startswith("Take the contract in") and "patient as ever" in t[0], t)
check("fixed rules are said exactly as written", t[1] == FIX)
check("a very short line is said as written", t[2] == "Short one.")
check("said under her, once", len(SAID) == 1 and SAID[0][0] in (mentor.NAME, mentor.M["unnamed"]), SAID)
check("what she said is remembered for the next line", w.player.mentor["chat"][-1][0] == "Maren" and "Take the contract" in w.player.mentor["chat"][-1][1])

calls0 = stub.calls.get("MentorLines", 0)
stub.voice = lambda lines: [l.replace("guild hall", "hall").replace("30", "") + " Fifty coins." for l in lines]
SAID.clear()
w.mentor_say(W, beat="test")
check("a rejected answer is retried once, then the written line is said", SAID[-1][1] == W and stub.calls["MentorLines"] - calls0 == 2, (SAID, stub.calls["MentorLines"] - calls0))

stub.voice = lambda lines: lines + ["An extra line."]
SAID.clear()
w.mentor_say(W, beat="test")
check("a wrong number of lines is refused", SAID and SAID[-1][1] == W, SAID)

stub.voice = lambda lines: ["Take it in."]
config.VOICED_MENTOR = False
calls0 = stub.calls.get("MentorLines", 0)
SAID.clear()
w.mentor_say(W, beat="test")
check("with the model turned off she says it as written, with no call", SAID[-1][1] == W and stub.calls.get("MentorLines", 0) == calls0)
config.VOICED_MENTOR = True

stub.voice = None
w.mentor_say(mentor.Fixed([FIX]), beat="test")
check("a block of only fixed lines never calls the model", SAID[-1][1] == FIX)

mentor.set_stage(w.player, "")
check("at the first meeting she is sceptical", "highly sceptical" in mentor.facts(w.player, "Parth") and "armed stranger" in mentor.facts(w.player, "Parth"))
# she answers what the player says
stub.voice = None; stub.reply = "Woke up in a field, did you? That is a new one."
SAID.clear()
w.mentor_say(W, beat="test", reply_to="I'm not sure, I just woke up in the fields")
t = SAID[-1][1].split("\n")
check("her first paragraph answers what they said", t[0] == stub.reply and t[1] == W, t)
SAID.clear()
w.mentor_say(W, beat="test")
check("with nothing said to her there is no reply", SAID[-1][1] == W)
stub.reply = "You have 3 chances left."
SAID.clear()
w.mentor_say(W, beat="test", reply_to="hello")
check("a reply that states a number is refused and the written lines are said", SAID[-1][1] == W, SAID[-1])
stub.reply = None
check("the request shows what the player just said", "THE PLAYER JUST SAID: \"hello there\"" in mentor.voice_request(w.player, "Parth", "b", [W], "hello there"))
check("reply checks", mentor.check_reply("Fine.") == "" and mentor.check_reply("") != "" and mentor.check_reply("It is a game.") != "" and mentor.check_reply("x " * 60) != "")
# the request carries her manner, what was said, and the lines
req = mentor.voice_request(w.player, "Parth", "a beat", [W])
check("the request has the facts, the attitude, the talk and the lines", "ATTITUDE:" in req and "WHAT WAS SAID LATELY" in req and "1. " + W in req and "a beat" in req)
check("her persona and the rules are in the system prompt", "warm, wry personality" in mentor.voice_system(w.player) and "Return exactly one line" in mentor.voice_system(w.player))

# free speech: paragraphs, checked
cs = mentor.check_speech
ctxs = {"paragraphs": (2, 4), "must": ["#board"], "material": ["Type #board. You can hold 2."], "ends_question": True}
okp = ["Type #board and read it. You can hold 2.", "How well do you know the guild?"]
check("a clean speech passes", cs(okp, ctxs) == "", cs(okp, ctxs))
check("too few paragraphs refused", "paragraphs" in cs(okp[:1], ctxs))
check("a missing required phrase refused", "#board" in cs(["Read the board. You can hold 2.", okp[1]], ctxs))
check("a new number refused", "number" in cs([okp[0] + " Take 7.", okp[1]], ctxs))
check("a game mention refused", "game" in cs([okp[0] + " It is a game.", okp[1]], ctxs))
check("a long paragraph refused", "too long" in cs(["#board " + "word " * 80, okp[1]], ctxs))
check("must end on the question", "question" in cs([okp[0], "Fine then."], ctxs))
SAID.clear()
w.mentor_speak(["Type #board to read it.", "You can hold 2."], "test", must=["#board"], paragraphs=(1, 3))
check("free speech is said as one block under her", len(SAID) == 1 and SAID[0][0] in (mentor.NAME, mentor.M["unnamed"]), SAID)
old = config.VOICED_MENTOR
config.VOICED_MENTOR = False
check("off means not spoken", w.mentor_speak(["x y z a b c"], "t") is False)
config.VOICED_MENTOR = old
stub.speech = lambda pts, musts: ["No."]
SAID.clear()
check("a failing speech falls back (returns False)", w.mentor_speak(["Type #board to read it.", "You can hold 2."], "t", must=["#board"], paragraphs=(2, 3)) is False and not SAID)
stub.speech = None

# every plain speech is facts in, her words out
config.FREE_MENTOR = True
SAID.clear()
w.mentor_say("Type #board to read it and 'search for wolves' to hunt. The clerk will pay you at the guild hall.", beat="test")
check("mentor_say writes her speech freely from the facts", len(SAID) == 1 and "#board" in SAID[0][1] and "search for wolves" in SAID[0][1], SAID)
SAID.clear()
w.mentor_say("Behind me.", beat="test")
check("a very short line stays as written", SAID[-1][1] == "Behind me.")
SAID.clear()
w.mentor_say(mentor.Fixed(["Rank F may hold 2 contracts."]), "Take your time over it, there is no hurry at all.", beat="test")
check("fixed rules are never rewritten", "Rank F may hold 2 contracts." in SAID[-1][1].split("\n"))
config.FREE_MENTOR = False

# warm-up: the model is loaded in the background, same context size, and every call asks to keep it loaded
seen = []
real_chat = gw._client.chat
gw._client.chat = lambda **k: (seen.append(k), real_chat(**k))[1]
gw.warm()
t0 = time.time()
while not seen and time.time() - t0 < 3:
    time.sleep(0.02)
check("the warm-up asks for a tiny reply with the game's context size", seen and seen[0]["options"]["num_predict"] <= 8 and seen[0]["options"]["num_ctx"] == config.NUM_CTX, seen[:1])
check("...and keeps the model loaded", seen and seen[0]["keep_alive"] == config.KEEP_ALIVE)
seen.clear()
w.mentor_say(W, beat="test")
check("every real call keeps the model loaded too", seen and all(k["keep_alive"] == config.KEEP_ALIVE for k in seen), seen[:1])
gw._client.chat = lambda **k: (_ for _ in ()).throw(ConnectionError("no ollama"))
gw.warm(); time.sleep(0.1)
check("a missing Ollama does not break the warm-up", True)

# closing the game unloads the model
seen2 = []
real2 = gw._client.chat
gw._client.chat = lambda **k: (seen2.append(k), None)[1]
gw.unload()
check("closing the game asks Ollama to unload the model", seen2 and seen2[0]["keep_alive"] == 0 and seen2[0]["messages"] == [], seen2)
config.UNLOAD_ON_EXIT = False
seen2.clear(); gw.unload()
check("...unless switched off", not seen2)
config.UNLOAD_ON_EXIT = True
gw._client.chat = lambda **k: (_ for _ in ()).throw(ConnectionError("no ollama"))
gw.unload()
check("a missing Ollama does not break closing", True)
gw._client.chat = real2

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
