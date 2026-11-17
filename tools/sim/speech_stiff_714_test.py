"""(f714) Companions that sound like people (the owner, 2026-11-16: "pay attention to how npcs speak and if they come off as ai or human
like"; docs/design/25_speech_parts_camp.md). In the third blind play the party said "It is just a scratch. I can still hold my
shield.", "Another fight finished now.", "Moving forward next. Route remains hard."; the style rules ask for contractions and plain
talk, but the party's exchanges were shown no speech exemplars at all, and nothing checked what came back.
Held here: speech with two or more uncontracted pairs a person would contract (hygiene.yaml speech) is sent back once with its reason,
the rewrite taken, never on the last try and never the reply lost; a speaker whose own voice or tongue speaks without contractions
(voice no_contractions, a tongue marked contracts: false) is let be; one uncontracted pair is ordinary; and every party exchange is
given the speech exemplars, as single replies are.
Run: python tools/sim/speech_stiff_714_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from typing import ClassVar
from pydantic import BaseModel
from engine import hygiene, voice_profile
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


check("two uncontracted pairs a person would contract are stiff", hygiene.stiff_speech("It is just a scratch. I am fine.") != [])
check("...contracted, they are not", hygiene.stiff_speech("It's just a scratch. I'm fine.") == [])
check("...and one alone is ordinary speech", hygiene.stiff_speech("It is late. Let's go.") == [])
check("...nor do words that only look like a pair count ('It is' inside 'Spirit is')", hygiene.stiff_speech("The spirit is gone. The bit is lost.") == [])


class Said(BaseModel):
    REPLY: ClassVar[bool] = True
    speech: str

    def spoken(self):
        return [("", self.speech)]


class Told(BaseModel):                    # world prose, as a thread's telling: no one speaks it
    news: str

    def spoken(self):
        return [("", self.news)]


class Talk(BaseModel):                    # the party's exchange: several people
    SPEAKS: ClassVar[bool] = True
    lines: list[dict]

    def spoken(self):
        return [(l["speaker"], l["text"]) for l in self.lines]


class Resp:
    def __init__(self, text):
        self.message = type("M", (), {"content": text})()
        self.done_reason = "stop"


def run(answers, ctx=None, retries=2, schema=None, task="hire_chat"):
    it = iter(answers)
    seen = []
    def chat(**kw):
        seen.append(kw["messages"][-1]["content"])
        return Resp(next(it))
    held = simlib.stand_in(chat=chat, embed=None, name="speech_714")
    try:
        r = gateway.generate(task, "You speak as a companion.", "PLAYER SAID: how's the shoulder?", schema or Said, retries=retries,
                             validation_context=ctx or {})
    finally:
        held()
    return (r.speech if hasattr(r, "speech") else r.news if hasattr(r, "news") else r.lines), seen


text, seen = run(['{"speech": "It is just a scratch. I do not need help."}', '{"speech": "It\'s just a scratch. I don\'t need help."}'])
check("stiff speech is sent back once with its reason, and the rewrite is taken", text.startswith("It's just a scratch") and len(seen) == 2
      and "it's" in seen[-1].lower() and "don't" in seen[-1].lower(), (text, seen[-1:]))
text, seen = run(['{"speech": "It is just a scratch. I do not need help."}', '{"speech": "It is only a scratch. I do not need help."}'])
check("...a second stiff reply is taken: the reply is never lost to it", text.startswith("It is only") and len(seen) == 2, (text, len(seen)))
text, seen = run(['{"speech": "It is just a scratch. I do not need help."}'], ctx={"uncontracted_ok": [""]})
check("a speaker whose own way of talking has no contractions is let be", text.startswith("It is just") and len(seen) == 1, (text, len(seen)))
text, seen = run(['{"speech": "It is just a scratch. I do not need help."}'], retries=0)
check("...and the last try is never sent back", text.startswith("It is just") and len(seen) == 1, (text, len(seen)))

check("pairs that cannot be contracted do not count: 'Yes, I am.', 'who you are and where we are'",
      hygiene.stiff_speech("Yes, I am. That is all.") == [] and hygiene.stiff_speech("I know who you are and where we are.") == [])
text, seen = run(['{"news": "The coin is not lost, and a herbalist cannot pay what is owed. It is not over."}'], schema=Told, task="thread_telling")
check("the world's own prose (a thread's telling) is never sent back for reading stiff: no one speaks it", len(seen) == 1, (text, len(seen)))
stiff2 = '{"lines": [{"speaker": "Pae", "text": "It is just a scratch. I do not need help."}, {"speaker": "Morm", "text": "It is not nothing. I am worried."}]}'
easy2 = '{"lines": [{"speaker": "Pae", "text": "It is just a scratch. I do not need help."}, {"speaker": "Morm", "text": "It\'s not nothing. I\'m worried."}]}'
text, seen = run([stiff2, easy2], ctx={"uncontracted_ok": ["Pae"]}, schema=Talk, task="exchange")
check("an exchange: a stiff speaker is sent back, one whose own way of talking has no contractions is let be", len(seen) == 2
      and "Pae" not in seen[-1].split("rejected")[0] and text[1]["text"].startswith("It's"), (len(seen), text))
text, seen = run([easy2], ctx={"uncontracted_ok": ["Pae"]}, schema=Talk, task="exchange")
check("...and with only the exempt speaker stiff, nothing is sent back", len(seen) == 1, len(seen))
from engine import budget
b = budget.open(); b.spent = b.limit - b.margin - (b.floor + b.reserve / 2)     # the call may run; no room for a second
text, seen = run(['{"speech": "It is just a scratch. I do not need help."}'])
budget.close()
check("a turn with no room for another call keeps the stiff reply: the story's time is never spent on it", len(seen) == 1, len(seen))
with gateway.tagged(relaxed=True):
    text, seen = run(['{"speech": "It is just a scratch. I do not need help."}'])
check("...nor is the looser last pass sent back again", len(seen) == 1, len(seen))
check("a companion whose voice kit says 'never a contraction' does not contract", voice_profile.contracts({"speech": {"kit": {"contractions": "full"}}}) is False)
check("a companion with the no_contractions voice does not contract", voice_profile.contracts({"quirks": {"voice": "no_contractions"}}) is False)
check("...nor one of a tongue marked contracts: false (the Rimelands)", voice_profile.contracts({"quirks": {"tongue": "rime"}}) is False)
check("...while a plain speaker does", voice_profile.contracts({"quirks": {"voice": "questions"}}) is True)
src = open("scenes/banter_actions.py", encoding="utf-8").read()
check("every party exchange is given the speech exemplars, as single replies are", 'self.exemplars("speech"' in src[src.index("def exchange"):src.index("generate(\"exchange\"")])
from llm import contracts as C
check("the real speech answers are marked (Exchange SPEAKS; NPCReply, CompanionReply, Parting REPLY) and the world's prose is not",
      C.Exchange.SPEAKS and C.NPCReply.REPLY and C.CompanionReply.REPLY and C.Parting.REPLY and C.Exchange.__doc__
      and not any(getattr(getattr(C, k), m, False) for k in ("ThreadTelling", "ThreadProposal", "CataclysmProposal") for m in ("REPLY", "SPEAKS")))
check("the startup check holds the speech table", hygiene.problems() == [], hygiene.problems())
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
