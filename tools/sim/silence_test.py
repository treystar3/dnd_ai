"""The director decides who MAY react; how hard the moment hit each one decides who MUST speak (severity.yaml may_be_silent_from). Someone
shaken or devastated may answer with one word, or with nothing but a gesture, or not at all, and that is not a reason to write the exchange
again. Everyone below that level still says something. A silent answer is shown but not remembered as something said. The stub stands in
for the model."""
import random, shutil, sys
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
from engine import banter, party_director as director, quirks, severity
from llm.contracts import CompanionReply, Exchange
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def why(ls, **ctx):
    base = {"speakers": ["Bram Voss", "Isel Quill"], "lines": (1, 2), "all_speak": True, "material": [], "recent": {}, "members": {}, "gesture_states": {}}
    base.update(ctx)
    try:
        Exchange.model_validate({"lines": ls}, context=base)
        return ""
    except Exception as e:
        return str(e)

# ---- the contract
check("the level: shaken and devastated may be silent; sobered and composed may not",
      severity.may_be_silent("shaken") and severity.may_be_silent("devastated") and not severity.may_be_silent("sobered") and not severity.may_be_silent("composed"))
both = ("Bram Voss", "Isel Quill")
check("one devastated word from one of two, both allowed silence: accepted", why([{"speaker": "Bram Voss", "text": "Tamsin."}], silent_ok=both) == "",
      why([{"speaker": "Bram Voss", "text": "Tamsin."}], silent_ok=both))
check("...the same with nobody allowed silence is refused, as before", why([{"speaker": "Bram Voss", "text": "Tamsin."}], lines=(2, 2)) != "")
check("a line with no words and only a gesture, from someone allowed silence: accepted",
      why([{"speaker": "Bram Voss", "text": "Tamsin!"}, {"speaker": "Isel Quill", "text": "", "gesture": "goes very still"}], silent_ok=both) == "")
check("...from someone not allowed silence: refused, and told who must speak",
      "Isel Quill must say something" in why([{"speaker": "Bram Voss", "text": "Tamsin!"}, {"speaker": "Isel Quill", "text": ""}], silent_ok=("Bram Voss",)),
      why([{"speaker": "Bram Voss", "text": "Tamsin!"}, {"speaker": "Isel Quill", "text": ""}], silent_ok=("Bram Voss",)))
check("...one allowed silence, one not, and only the silent one wrote: the other must speak",
      "Isel Quill must say something" in why([{"speaker": "Bram Voss", "text": "Tamsin."}], silent_ok=("Bram Voss",)))
check("...one allowed silence stays out of it entirely while the other speaks: accepted",
      why([{"speaker": "Isel Quill", "text": "Gods. Bram, I am so sorry."}], silent_ok=("Bram Voss",)) == "")
check("a wholly silent exchange, when everyone in it is allowed silence: accepted",
      why([{"speaker": "Bram Voss", "text": "", "gesture": "sinks to his knees"}, {"speaker": "Isel Quill", "text": "(silence)"}], silent_ok=both) == "")
check("...not when someone in it must speak", why([{"speaker": "Bram Voss", "text": "...", "gesture": "sinks to his knees"}], silent_ok=()) != "")
ex = Exchange.model_validate({"lines": [{"speaker": "Bram Voss", "text": "no verbal response"}, {"speaker": "Isel Quill", "text": "...", "gesture": "turns away"}]},
                             context={"speakers": list(both), "lines": (1, 2), "all_speak": True, "silent_ok": both, "material": [], "recent": {}, "members": {}, "gesture_states": {}})
check("'no verbal response' and '...' are read as silence, and a silent line's gesture is kept",
      [l.text for l in ex.lines] == ["", ""] and ex.lines[1].gesture == "turns away", [(l.text, l.gesture) for l in ex.lines])
st_ = {"gestures": [], "gesture_now": False}            # a gesture just made: an ordinary line would lose it
ex = Exchange.model_validate({"lines": [{"speaker": "Bram Voss", "text": "", "gesture": "covers his face with both hands"}]},
                             context={"speakers": list(both), "lines": (1, 2), "all_speak": True, "silent_ok": both, "material": [], "recent": {}, "members": {},
                                      "gesture_states": {"Bram Voss": st_}})
check("...even right after another gesture: for a silent line the gesture is the reaction", ex.lines[0].gesture == "covers his face with both hands")

def reply(d, **ctx):
    try:
        return CompanionReply.model_validate(d, context=ctx), ""
    except Exception as e:
        return None, str(e)
r, e = reply({"speech": "", "gesture": ""}, silent_ok=True)
check("one companion alone, allowed silence, says nothing and does nothing visible: accepted", r is not None and r.speech == "", e)
r, e = reply({"speech": "", "gesture": ""})
check("...not allowed silence: refused as before", r is None)

# ---- in play: a death mid-fight, Bram devastated, Isel only sobered
shutil.rmtree("saves/silence", ignore_errors=True)
st = CampaignStore.open_or_create("silence")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 3000; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/silence/turns.jsonl"

def hire(i, name, temper, role, bond=20):
    m = {"id": f"s{i}", "name": name, "role": role, "level": 3, "rank": "F", "permanent": True, "temper": temper, "motive": "coin",
         "line": "will not take from the poor", "bond": bond, "memories": [], "said": [], "talk": [], "blurb": "a hired hand"}
    quirks.roll(m, random.Random(i))
    m["details"] = []
    m["speech"] = {"tells": {}}
    return m
bram, isel, tam = hire(1, "Bram Voss", ["blunt"], "fighter"), hire(2, "Isel Quill", ["gentle"], "priest"), hire(3, "Tamsin Reed", ["wary"], "ranger")
crew = [bram, isel, tam]
w.player.party = crew; w.player.party_mode = "with"; w.player.party_relations = {}
w.relations_seed()
w.relation(bram, tam)["score"] = 40
w.relation(isel, tam)["score"] = -10
w.relation(bram, isel)["score"] = 10

calls = []
import llm.gateway as gw
WHY = []
_chat = gw._client.chat
def _spy(**k):
    msgs = k.get("messages", [])
    if len(msgs) > 2 and "rejected" in msgs[-1].get("content", ""):
        WHY.append(msgs[-1]["content"].split("\n")[0][:200])
    return _chat(**k)
gw._client.chat = _spy
def one_word(names, first):
    calls.append(first)
    return [{"speaker": "Isel Quill", "text": "Bram, get down!"}, {"speaker": "Bram Voss", "text": "Tamsin!"}]
stub.exchange = one_word
SAID.clear(); severity.REACTIONS.clear()
w.party_moment("Tamsin Reed has just been killed in front of them.", "heavy", "s3", "Tamsin Reed's death", in_fight=True)
check("killed mid-fight: one call, and Bram's single word is shown as it is", len(calls) == 1 and ("Bram Voss", "Tamsin!") in SAID, (len(calls), WHY, SAID))

calls.clear()
stub.exchange = lambda names, first: (calls.append(first), [{"speaker": "Bram Voss", "text": "Tamsin."}])[1]
SAID.clear()
w.party_moment("Tamsin Reed has just been killed in front of them.", "heavy", "s3", "Tamsin Reed's death (again)", in_fight=True)
check("...and at a death anyone may stay out of it (severity.yaml all_may_be_silent_at: heavy): Bram's word alone is accepted",
      len(calls) == 1, len(calls))

# both struck hard: a wholly silent moment is shown, and nothing is remembered as said
w.relation(isel, tam)["score"] = 30
calls.clear()
stub.exchange = lambda names, first: (calls.append(first), [{"speaker": "Bram Voss", "text": "", "gesture": "drops his sword"},
                                                            {"speaker": "Isel Quill", "text": ""}])[1]
SAID.clear(); severity.REACTIONS.clear()
said_before = (list(bram["said"]), list(isel["said"]))
w.party_moment("Tamsin Reed has just been killed in front of them.", "heavy", "s3", "Tamsin Reed's death (III)", in_fight=True)
shown = dict(SAID)
check("both devastated: a wholly silent moment is accepted first time and shown", len(calls) == 1 and shown.get("Bram Voss") == "(Bram drops his sword.)"
      and shown.get("Isel Quill") == "(Isel says nothing.)", (len(calls), SAID))
check("...silence is not remembered as something they said", (bram["said"], isel["said"]) == said_before, (bram["said"][-1:], isel["said"][-1:]))
check("...and the reactions are tallied as silent, at their level", sorted(severity.REACTIONS) == [("devastated", True), ("devastated", True)], severity.REACTIONS)
check("...the moment still leaves its mark on them", "devastated" in (bram.get("mood") or "") and "devastated" in (isel.get("mood") or ""), (bram.get("mood"), isel.get("mood")))

# ordinary talk never offers silence
calls.clear()
stub.exchange = lambda names, first: (calls.append(first), [{"speaker": n, "text": "Fine weather for it."} for n in names])[1]
w.party_banter([bram, isel], "travel")
check("idle talk never offers silence", calls and all("WHO MAY SAY NOTHING" not in c and "beyond words" not in c for c in calls), [c[-300:] for c in calls][:1])
stub.exchange = None

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
