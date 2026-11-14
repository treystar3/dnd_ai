"""(f584) What to avoid is shown and checked. A2 (f582) took the stock-phrase list out of the narrator's voice and the worn words out of
every prompt, leaving only the checkers; measured on the live model it did not hold (docs/measure/prose_a2: the writing leaned on the
worn words and stock phrases more, and nearly three times as many narrations were sent back). So the lists are shown again, as before
f582, and the two checks A2 added are kept: a hire's reply and a townsperson's answer to several characters are held to the worn words
too, as one townsperson's reply was. Each check names only what that draft used.
Run: python tools/sim/lists_back_584_test.py"""
import ast
import inspect
import sys
import types
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from pydantic import ValidationError
from llm.contracts import CompanionReply, Narration, NPCReply
from scenes import combat_prompts as cp, party_prompts as ppr, voice, world_prompts as wp
import npc.prompts as npp

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- the lists are shown again
low = voice.DM_VOICE.lower()
check("the narrator's voice lists the stock phrases again", all(s in low for s in
      ("the air hangs heavy", "the scent of", "damp earth", "a sense of", "can't help but", "little do you know")), voice.DM_VOICE[:900])
check("...each of them one the checker catches", all(s in voice.STALE for s in
      ("the air hangs heavy", "scent of damp earth", "a sense of", "can't help but", "little do you know")))
WORN = ["steadfast", "weariness"]
place = types.SimpleNamespace(name="P", type="town", visible=[])
shown = {"narration request": wp.narration_request("t", place, [], "x", worn=WORN),
         "frame request": wp.dialogue_request("t", place, [], "w", "l", "d", "m", True, "p", "s", "", False, [], worn=WORN),
         "fight request": cp.narrate_request("P", "t", "swing", ["x [h1]"], "sword", "fine", ["a wolf"], 2, worn=WORN),
         "hire's prompt": ppr.talk_prompt("how", "core", "rel", [], [], [], "P", "Hello.", worn=WORN).render()}
for name, text in shown.items():
    check(f"the {name} shows the worn words again", "WORN OUT" in text and all(w in text for w in WORN), text[-300:])
check("the narrator and the frames are told what the list is", "WORDS YOU HAVE WORN OUT lists" in wp.NARRATOR_SYSTEM
      and "WORDS YOU HAVE WORN OUT, when given" in wp.DIALOGUE_SYSTEM and "WORDS YOU HAVE WORN OUT are words" in cp.NARRATE_SYSTEM)
import npc.life as life
for name, fn in {"townsperson's prompt": npp.conversation_prompt, "townsperson's request": npp.conversation_request,
                 "townsperson's request, whichever contract": life._request}.items():
    check(f"the {name} takes the worn words to show", "worn" in inspect.signature(fn).parameters)
check("the townsperson's prompt shows them", "WORDS PEOPLE HERE HAVE WORN OUT" in inspect.getsource(npp.conversation_prompt))
src_calls = Path("scenes/world.py").read_text(encoding="utf-8") + Path("scenes/combat_scene.py").read_text(encoding="utf-8")     + Path("scenes/party_actions.py").read_text(encoding="utf-8")
check("the call sites hand them over again (narration, frames, the fight, the hire)",
      src_calls.count('worn=self.worn_words("prose"),') >= 5 and 'shown=self.fight_shown, worn=self.ws.worn_words("prose")' in src_calls
      and 'worn=self.worn_words("speech"), others=self.fellow_names(m)' in src_calls)

# ---- the checkers still catch the slips
calls = []
answers = iter(["The air hangs heavy over the square.", "A cart turns in at the gate.", "Steady hands, a weary face, a quiet square.", "Clean."])


def fake(task, system, request, schema, **k):
    calls.append(request)
    return Narration(text=next(answers))


voice.generate = fake
r = voice.fresh("narrate", "sys", "req", Narration, [])
check("a draft with a stock phrase is written again once, told the phrase it used", len(calls) == 2 and "the air hangs heavy" in calls[1]
      and r.text == "A cart turns in at the gate.", calls)
calls.clear()
r = voice.fresh("narrate", "sys", "req", Narration, [], worn=["steady", "weary", "quiet"])
check("a draft that leans on worn words is written again once, told which", len(calls) == 2 and "WORN OUT" in calls[1]
      and "steady" in calls[1] and r.text == "Clean.", calls)


def reply(model, speech, worn, **more):
    try:
        model.model_validate({"speech": speech, **more}, context={"worn": worn}); return ""
    except ValidationError as e:
        return str(e)


LEAN = "The road is steady enough past the bridge, though you look weary to me, and the mill is not far now."
check("a townsperson's reply that leans on two worn words is sent back", "worn out" in reply(NPCReply, LEAN, ["steady", "weary"], intent="small_talk"))
check("a hire's reply that leans on two worn words is sent back, naming them",
      "'steady' and 'weary'" in reply(CompanionReply, LEAN, ["steady", "weary", "glance"]), reply(CompanionReply, LEAN, ["steady", "weary"]))
check("...one worn word, a short line, or no worn words given, passes",
      reply(CompanionReply, "The road is steady enough past the bridge, though the mill is not far from it now.", ["steady", "weary"]) == ""
      and reply(CompanionReply, "Steady on, weary one.", ["steady", "weary"]) == "" and reply(CompanionReply, LEAN, []) == "")
from llm.contracts import many_reply
Many = many_reply(["a", "b"])
block = [{"to": "a"}, {"to": "b"}]


def many(speech, worn):
    try:
        Many.model_validate({"speech": speech, "intent": "small_talk", "answers": block}, context={"to": ["a", "b"], "worn": worn}); return ""
    except ValidationError as e:
        return str(e)


check("a townsperson answering several characters at once is held to the worn words too", "worn out" in many(LEAN, ["steady", "weary"])
      and many(LEAN, []) == "", (many(LEAN, ["steady", "weary"]), many(LEAN, [])))
src = Path("scenes/party_actions.py").read_text(encoding="utf-8")
check("the hire's reply is checked against the words worn in speech", '"worn": self.worn_words("speech")' in src)
check("...and its relaxed last try lets them go, as a townsperson's does (no fixed quip for a hire who leans on them every try)",
      "kit=False, worn=[])" in src)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
