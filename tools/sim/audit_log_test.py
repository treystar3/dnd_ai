"""The audit log (f314): every attempt of every model call is written, readable, under the turn it served; a rejected answer shows why;
the system prompt is written once in full and then by reference; typed prompts show their parts."""
import sys, json, shutil
sys.path.insert(0, ".")
from pathlib import Path
import config
from llm import audit, gateway
from engine.prompt import Prompt
from pydantic import BaseModel, field_validator

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# a session file of our own, in a scratch folder
audit.A["folder"] = "logs/audit_test"
shutil.rmtree("logs/audit_test", ignore_errors=True)
audit._path = None; audit._count = 0; audit._system_seen.clear(); audit._first_attempt.clear(); audit._full = False
config.AUDIT_LOG = True


class Reply(BaseModel):
    speech: str

    def spoken(self):
        return [("", self.speech)]

    @field_validator("speech")
    @classmethod
    def no_dragons(cls, v):
        if "dragon" in v:
            raise ValueError("no dragons here")
        return v


class FakeResponse:
    def __init__(self, text):
        self.message = type("M", (), {"content": text})()
        self.done_reason = "stop"


answers = iter(['{"speech": "a dragon lands"}', '{"speech": "a cart rolls by"}', '{"speech": "fine weather"}'])


class FakeClient:
    def chat(self, **kw):
        return FakeResponse(next(answers))


gateway._client = FakeClient()
audit.note_turn(7, "I look around")
p = Prompt().instruction("be brief", "HOW TO SPEAK").fact("it is raining", "WEATHER")
r = gateway.generate("narrate", "You are the narrator.", p, Reply, retries=2)
check("the call came back once the answer was acceptable", r.speech == "a cart rolls by")
audit.note_turn(8, "I ask the baker the way")
gateway.generate("narrate", "You are the narrator.", "plain user text", Reply, retries=0)

# (f315) the gateway sends back a line that names someone the speaker was not told of, with the complaint, and takes the redraft
answers = iter(['{"speech": "Go and see Oswin Lovell, he will sort you out."}', '{"speech": "Go and see Fenella Reeve at the desk."}'])
audit.note_turn(9, "who should i see?")
q = Prompt().fact("Fenella Reeve: the guild clerk, at her desk", "WHO IS HERE")
r = gateway.generate("npc_conversation", "You are a townsperson.", q, Reply, retries=1, validation_context={"known": {"maren", "holt"}})
check("a line naming someone the speaker was not told of is sent back, and the redraft taken", r.speech.startswith("Go and see Fenella"), r.speech)

text = Path(audit.path()).read_text(encoding="utf-8")
check("...and the log shows why", "'Oswin Lovell' is no one and nowhere you were told of" in text)
check("the file names the turn and what the player typed", '# Turn 7: "I look around"' in text and '# Turn 8: "I ask the baker the way"' in text)
check("why the call was made is in plain words", "the narrator describing what just happened" in text)
check("the rejected attempt is recorded with its reason", "attempt 1" in text and "rejected - speech: no dragons here" in text)
check("...and the accepted one after it", "attempt 2" in text and "**Verdict:** accepted" in text)
check("the system prompt is written in full once, then by reference", text.count("You are the narrator.") == 1 and "unchanged since #1" in text)
check("a typed prompt shows its parts", "[instruction · HOW TO SPEAK]" in text and "[fact · WEATHER]" in text)
check("the complaint sent back is shown", "Sent back with:" in text and "no dragons here" in text)
check("a retry does not repeat the prompt in full", "the same as #1" in text and text.count("[fact · WEATHER]") == 1)
check("answers are shown as formatted JSON", '"speech": "a cart rolls by"' in text)
check("#audit can say where it is", "calls recorded" in audit.summary())

shutil.rmtree("logs/audit_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
