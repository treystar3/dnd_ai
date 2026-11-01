"""(f433) An answer cut off at its token ceiling was sent back with "the answer was cut off because it was far too long. Keep every field
short." (llm/gateway.py), the one length instruction left after the owner's "No length limits on the narrator or the speakers" (f375):
a narration that ran into the runaway ceiling was told to be short on its retry. Now the narrator and every speaker are told the answer
went round in circles, to say what the moment holds once and stop; only the engine's own structured calls are still asked to keep
fields short so their JSON closes."""
import re, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 33)
simlib.install(stub)
import config
from llm import gateway
from llm.contracts import ActionPlan, Narration, NPCReply

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

LENGTH = re.compile(r"\b(short|shorter|brief|briefly|concise|too long|fewer|sentences?)\b", re.I)

# ---- what each kind of call is told
told = {"narration at the runaway ceiling": gateway.cut_off_reason("narrate", Narration, config.PROSE_MAX_TOKENS),
        "a narrator's task under a lower ceiling": gateway.cut_off_reason("moment", Narration, config.MAX_TOKENS),
        "a speaker under a lower ceiling": gateway.cut_off_reason("npc_conversation", NPCReply, config.MAX_TOKENS)}
for name, reason in told.items():
    check(f"{name} is never told a length", not LENGTH.search(reason), reason)
    check(f"...and is told it went round in circles, to say it once", "once" in reason and "circles" in reason, reason)
read = gateway.cut_off_reason("interpret_action", ActionPlan, config.MAX_TOKENS)
check("the engine's own structured call is told its JSON did not close", "JSON" in read, read)

# ---- the retry a narration gets after a cut-off
sent = []
real = gateway._client
class CutOnce:
    n = 0
    def chat(self, **k):
        sent.append(k["messages"])
        CutOnce.n += 1
        if CutOnce.n == 1:
            return types.SimpleNamespace(done_reason="length", message=types.SimpleNamespace(content='{"text": "The rain the rain the rain'))
        return real.chat(**k)
gateway._client = CutOnce()
out = gateway.generate("narrate", "You narrate.", "The player looks around.", Narration, max_tokens=config.PROSE_MAX_TOKENS)
gateway._client = real
followup = sent[1][-1]["content"] if len(sent) > 1 else ""
check("a narration cut off at the ceiling is tried again and stands", isinstance(out, Narration) and len(sent) == 2, len(sent))
check("...and the retry carries no length", followup and not LENGTH.search(followup), followup)
check("...but says to say it once", "once" in followup, followup)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
