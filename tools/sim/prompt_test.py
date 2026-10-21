"""Typed prompts and the copy guard (engine/prompt.py, llm/gateway.py), engine-owned material, the conversation log (engine/convo.py), the
fallback ladder every speaker shares, and Maren on the same pipeline as the hires."""
import sys, random, shutil, re
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
SAID = []
uc.say = lambda t, s="": SAID.append((s, t))
uc.narrate = lambda t: None
uc.note = lambda m, *a, **k: None
import llm.gateway as gw
from engine import convo, mentor, quirks
from engine.prompt import Prompt, copied, grams
from llm.contracts import CompanionReply
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the copy guard reads types from the prompt
p = Prompt().instruction("Understates: describes big trouble as if it were small.", "HOW YOU SPEAK").fact("Your father was a farmer on the river flats.", "WHO YOU ARE")
check("saying a fact you were given is fine", copied("My father was a farmer on the river flats.", "", p) == "")
check("lifting the instruction's own words is caught", copied("Well, I describe big trouble as if it were nothing.", "", p) != "")
check("the system prompt counts as instruction", copied("I never invent furniture, walls, weather, scenery or held objects.", "Never invent furniture, walls, weather, scenery, or held objects.", Prompt()) != "")
check("a short shared phrase is not a copy: six words running are", copied("May I look at the wound for you?", "", Prompt().instruction("Asks before they look at the wound of a friend.")) == "")
check("ordinary small-word runs are not a copy", not grams("and it is the one that I do not") and copied("It is not that I do not care.", "It is not for you; do not do that.", Prompt()) == "")
p2 = Prompt().instruction("Says the hard thing about the guild hall plainly.").fact("The guild hall is by the river.")
check("words in both an instruction and a fact are allowed", copied("The guild hall is by the river, if you want it.", "", p2) == "")
check("material may be said as it is", copied("A cold hearth makes a short night.", "", Prompt().material("a saying from home: 'A cold hearth makes a short night.'")) == "")

# ---- the gateway refuses a copied line and retries, with the reason
calls = []
def comp(u):
    calls.append(u)
    return {"speech": "I describe big trouble as if it were small." if len(calls) == 1 else "It is a scratch."}
stub.companion = comp
r = gw.generate("hire_chat", "You are a hire.", p, CompanionReply, retries=1)
check("a reply that lifts the instructions is sent back, and the second try is kept", r.speech == "It is a scratch." and len(calls) == 2, (r.speech, len(calls)))
log = [l for l in open(config.LOG_PATH, encoding="utf-8").read().splitlines() if "instructions' own wording" in l]
check("...and the reason given names it as the instructions' wording", bool(log))
calls.clear()
r = gw.generate("hire_chat", "You are a hire.", "a plain string request", CompanionReply, retries=1)
check("a plain string request is not checked (only typed prompts know their parts)", r.speech == "I describe big trouble as if it were small.")
stub.companion = None

# ---- the fallback ladder: a looser last try, then the fallback is recorded centrally
gw.FALLBACKS.clear()
tries = []
def stubborn(u):
    tries.append(u)
    return {"speech": "I will say the same thing again and again."}
stub.companion = stubborn
try:
    gw.generate("hire_chat", "sys", "req", CompanionReply, retries=1, validation_context={"recent": ["I will say the same thing again and again."]},
                relaxed_context={"recent": []})
    ladder_ok = True
except gw.LLMError:
    ladder_ok = False
check("when the guarded tries all fail, the looser try is made before giving up", ladder_ok and len(tries) == 3, len(tries))
tries.clear()
try:
    gw.generate("hire_chat", "sys", "req", CompanionReply, retries=1, validation_context={"recent": ["I will say the same thing again and again."]},
                relaxed_context={"recent": ["I will say the same thing again and again."]})
except gw.LLMError:
    pass
check("a call that gives up is recorded where anyone can count it", gw.FALLBACKS[-1:] == ["hire_chat"], gw.FALLBACKS)
stub.companion = None

# ---- instructions carry nothing quotable
Q = quirks.Q
texts = [v["prompt"] for v in Q["voices"].values()] + [t["habits"] for t in Q["tongues"].values()] + [Q["tongue_prompt"]] + \
        [b["say"] for bs in Q["blueprints"].values() for b in bs] + list(Q["maren"]["blueprint"])
check("no voice, tongue or temperament line carries an example in brackets to copy", not [t for t in texts if re.search(r"\('|\(\"", t)], [t for t in texts if re.search(r"\('|\(\"", t)])
check("sayings live in the tongues as material", all(t.get("sayings") for t in Q["tongues"].values()))

# ---- a world to talk in
shutil.rmtree("saves/pt", ignore_errors=True)
st = CampaignStore.open_or_create("pt")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/pt/turns.jsonl"
m = {"id": "h0", "name": "Bram Voss", "role": "fighter", "level": 3, "rank": "F", "permanent": True, "temper": ["blunt", "dry"], "motive": "coin",
     "line": "will not take from the poor", "bond": 15, "memories": [], "said": [], "talk": [], "blurb": "a scarred sellsword"}
quirks.roll(m, random.Random(0))
m["quirks"].update({"voice": "curses", "curses": ["ashes and rot", "damn"]})
w.player.party = [m]; w.player.party_mode = "with"

reqs = []
def watch(u):
    reqs.append(u)
    return {"speech": ["I did it for the coin, and the coin was good.", "Coin. Same as I said. It has not changed since this morning."][min(len(reqs) - 1, 1)]}
stub.companion = watch
w.hire_talk(m, "Why did you become a sellsword?")
check("the talk request is typed: how they speak is apart from who they are", "HOW YOU SPEAK:" in reqs[-1] and "WHO YOU ARE:" in reqs[-1])
check("their curses are not listed in the instructions", "'damn'" not in reqs[-1].split("WORDS YOU MAY USE")[0], reqs[-1][:600])
w.hire_talk(m, "Why did you become a sellsword, again?")
check("asked again, the request says so and gives what they answered last time", "ASKED BEFORE" in reqs[-1] and "the coin was good" in reqs[-1], reqs[-1][-900:])
check("...and the answer in new words is said, not refused", SAID and "has not changed" in SAID[-1][1], SAID[-1:])
reqs.clear(); stub.companion = lambda u: (reqs.append(u), {"speech": "Coin. Same as I said. It has not changed since this morning."})[1]
w.hire_talk(m, "Why did you become a sellsword, one more time?")
check("asked a third time, the very same answer stands: it is not checked against the answer being asked for again", SAID and SAID[-1][1].endswith("since this morning.") and len(reqs) == 1, (SAID[-1:], len(reqs)))
check("...and the request asks for the same facts, not new words", "same facts" in reqs[-1] and "new words" not in reqs[-1])
stub.companion = watch
e = convo.find(m, "why did you become a sellsword")
check("the conversation log keeps the question, how often, and the latest answer", e and e["times"] == 3 and "has not changed" in e["answer"], e)
offered = 0
for k in range(40):
    st.meta.minutes = 2000 + k
    m["said"] = []
    if any("curse of theirs" in x for x in w.material_for(m)):
        offered += 1
check("a curse is offered now and then, not every time", 5 <= offered <= 25, offered)
stub.companion = None

# ---- Maren on the same pipeline
from engine import mentor as _m
mentor.set_stage(w.player, "board")
w.mentor_with_you = lambda: True
mreqs = []
_orig = stub.a_MentorReply if hasattr(stub, "a_MentorReply") else None
def mrep(u, k):
    mreqs.append(k["messages"][1]["content"])
    n = len(mreqs)
    return {"speech": ["An A rank, earned the slow way.", "I told you, A rank. It has not got any higher since."][min(n - 1, 1)], "gesture": "", "moves_on": False,
            }
stub.a_MentorReply = mrep
stub.extract = lambda u: {"facts": [{"speaker": "Maren Holt", "about": "self", "text": "I earned my A rank on river contracts."}]} if "slow way" in u else {"facts": []}
w.mentor_talk("How did you come by your rank, and where do you come from?")
w.mentor_talk("How did you come by your rank, and where do you come from, again?")
stub.extract = None
check("Maren's request is typed and she is told she was asked before, with her last answer", "ASKED BEFORE" in mreqs[-1] and "earned the slow way" in mreqs[-1], mreqs[-1][-700:])
check("what she says about herself becomes her canon", any("river contracts" in c["text"] for c in w.player.mentor.get("canon", [])), w.player.mentor.get("canon"))
check("...and comes back when she is asked about it", "river contracts" in _m.facts(w.player, "Parth", "how did you earn your rank?"))
if _orig:
    stub.a_MentorReply = _orig

shutil.rmtree("saves/pt", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
