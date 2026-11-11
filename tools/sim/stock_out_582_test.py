"""(f582) What to avoid is checked, not shown (docs/design/09 A2). The narrator's voice no longer names the stock phrases it once told the
model to avoid, and no prompt hands over the words recent writing has worn out: a list of what to avoid puts it in front of the model.
The aim is said instead (one exact detail), and the checkers catch the slips: a draft with a stock phrase or two worn words is written
again once (scenes/voice.py fresh), a townsperson's or a hire's reply that leans on two worn words is sent back (llm/contracts.py), each
naming only what that draft used.
Run: python tools/sim/stock_out_582_test.py"""
import ast
import inspect
import sys
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

# ---- the voice says the aim, and names no stock phrase
low = voice.DM_VOICE.lower()
check("the narrator's voice names none of the stock phrases the checker catches", not [s for s in voice.STALE if s in low],
      [s for s in voice.STALE if s in low])
check("...and says the aim instead: one exact detail", "one exact detail" in low and "stock phrase" not in low, voice.DM_VOICE[:900])
check("the checker still holds every phrase the voice once listed", all(s in voice.STALE for s in
      ("the air hangs heavy", "scent of damp earth", "a sense of", "can't help but", "little do you know")))

# ---- no prompt hands over a list of what to avoid
SYSTEMS = {"narrator": wp.NARRATOR_SYSTEM, "dialogue frame": wp.DIALOGUE_SYSTEM, "exchange frame": wp.EXCHANGE_SYSTEM,
           "fight": cp.NARRATE_SYSTEM, "fight opening": cp.START_SYSTEM, "fight aftermath": cp.AFTERMATH_SYSTEM, "hire": ppr.TALK_SYSTEM,
           "townsperson": npp.CONVERSATION_SYSTEM}
for name, text in SYSTEMS.items():
    check(f"the {name}'s system prompt names no stock phrase and no worn words", not [s for s in voice.STALE if s in text.lower()]
          and "WORN OUT" not in text.upper(), [s for s in voice.STALE if s in text.lower()])
import npc.life as life
BUILDERS = {"narration request": wp.narration_request, "frame request": wp.dialogue_request, "fight request": cp.narrate_request,
            "hire's prompt": ppr.talk_prompt, "townsperson's prompt": npp.conversation_prompt, "townsperson's request": npp.conversation_request,
            "townsperson's request, whichever contract": life._request}
for name, fn in BUILDERS.items():
    check(f"the {name} takes no worn words to show", "worn" not in inspect.signature(fn).parameters, list(inspect.signature(fn).parameters))

found = []
for d in ("scenes", "npc", "engine", "llm", "services"):
    for path in sorted(Path(d).rglob("*.py")):
        if path.as_posix() in ("scenes/voice.py", "llm/contracts.py"):      # the checkers: they name what a draft used, after it was written
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and "WORN OUT" in node.value.upper():
                found.append(f"{path.as_posix()}:{node.lineno}")
check("no text outside the checkers tells the model what it has worn out", not found, found)

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
