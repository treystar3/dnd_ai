"""(f701) A passage may not show a creature of this place that the game does not have (found in the second blind play:
docs/play/2026-11-16_blind_play_journal.md). A search found signs and the passage showed "the awakened tree" itself; passages showed
wisps the game never had. The narrator is told "never add creatures", and nothing held it to that.
Held here: a narrator's passage that names a creature this place can hold (its roster), when the request it was written from names
none of that kind (in view, the event, the fight), is sent back once with the reason; a second such passage is taken rather than the
telling lost. Names are read whole ("awakened tree", "will-o'-wisps"), never by a common word alone ("trees", "wisps of mist"); a
one-word name counts as a creature only as one ("two wolves", "the bear", never "bear the weight"). A creature the request names
passes; a place that holds no creatures (a town) is never checked; a speaker's line is not the narrator's.
Run: python tools/sim/phantoms_701_test.py"""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from pydantic import BaseModel
from engine import phantoms
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


ROSTER = ["awakened_tree", "will_o_wisp", "wolf", "brown_bear", "bat"]
phantoms.use(lambda: ROSTER)
REQ = "GAME STATE\nPLACE: the Greywood\nGAME EVENT: The player searches and finds fresh signs of wolf.\nRECENT NARRATION:\n  - an awakened tree"


def found(text, request=REQ, task="narrate"):
    return phantoms.found(task, text, request)


check("a creature of this place the request never named is a phantom", "awakened tree" in str.lower(found("The awakened tree itself sways ahead.")))
check("...and wisps by their whole name", "will-o'-wisp" in found("Two will-o'-wisps drift over the pools.").lower())
check("trees and wisps of mist are no creatures", found("Trees crowd the path and wisps of mist curl over the pools.") == "")
check("a creature the request names passes (the wolf's signs)", found("Wolf tracks cross the mud; the wolf is long gone.") == "")
check("what was said before (recent narration) is no leave to show it again", "awakened tree" in found("An awakened tree creaks.").lower())
check("a one-word name counts only as a creature: 'the bat' is one", "bat" in found("The bat swoops low over you.", request="GAME EVENT: x").lower())
check("...and 'two bats'", "bat" in found("Two bats flit past.", request="GAME EVENT: x").lower())
check("...'did not bat an eye' is none", found("Pae did not bat an eye.", request="GAME EVENT: x") == "")
check("a two-word name is read whole: 'the brown bear' is one", "brown bear" in found("The brown bear rises.", request="GAME EVENT: x").lower())
check("a speaker's line is not the narrator's", found("The awakened tree!", task="npc_conversation") == "")
phantoms.use(lambda: [])
check("a place that holds no creatures is never checked", found("The awakened tree sways.") == "")
phantoms.use(lambda: ROSTER)


from scenes import combat_prompts as cp, world_prompts as wp
fight = cp.narrate_request("the Greywood", "noon", "I strike", ["The wolf bites you [h1]"], "staff", "you", ["wolf (hurt)"], 2,
                           recent=["An awakened tree creaks."])
check("a fight round names its foe: the foe, told after the recent passages, is no phantom", found("The wolf lunges at your arm.", fight) == "")
check("...while the recent passages there are still no leave", "awakened tree" in found("An awakened tree creaks.", fight).lower())
place = type("P", (), {"name": "the Greywood", "type": "forest", "visible": ["old oaks"]})()
told = wp.narration_request("noon", place, [], "The player walks on.", "I walk on.", recent=["A wolf howls."],
                            already=["a wolf by the stream"], in_view=["bat"])
check("the world's passage: what is in view passes", found("The bat circles once.", told) == "")
check("...what was shown earlier this visit is no leave", "wolf" in found("The wolf pads closer.", told).lower())
ROSTER.extend(["shadow", "ghost", "skeleton"])
for line in ("Shadows pool under the old oaks.", "The shadow of the ridge falls across you.", "A ghost of a smile crosses her face.",
             "Mist hangs like a ghost over the water.", "The skeleton of a burnt barn leans by the road.", "A wolf pelt hangs drying.",
             "You pass the Wolf's Head inn.", "He wolfs down the bread.", "Wolf tracks cross the mud."):
    check(f"an ordinary word is no creature: '{line}'", found(line, "GAME EVENT: you walk on.") == "", found(line, "GAME EVENT: you walk on."))


class Reply(BaseModel):
    text: str


class Resp:
    def __init__(self, text):
        self.message = type("M", (), {"content": text})()
        self.done_reason = "stop"


def run(answers):
    it = iter(answers)
    seen = []
    def chat(**kw):
        seen.append(kw["messages"][-1]["content"])
        return Resp(next(it))
    held = simlib.stand_in(chat=chat, embed=None, name="phantoms_701")
    try:
        r = gateway.generate("narrate", "You are the narrator.", REQ, Reply, retries=2)
    finally:
        held()
    return r.text, seen


text, seen = run(['{"text": "The awakened tree itself sways ahead."}', '{"text": "Wolf tracks cross the mud."}'])
check("the passage with a phantom is sent back with its reason, and the rewrite is taken",
      text == "Wolf tracks cross the mud." and len(seen) == 2 and "awakened tree" in seen[-1].lower(), (text, seen[-1:]))
text, seen = run(['{"text": "The awakened tree sways."}', '{"text": "An awakened tree creaks."}'])
check("a second phantom in a row is taken: the telling is never lost to it", text == "An awakened tree creaks." and len(seen) == 2, (text, len(seen)))
text, seen = run(['not json', '{"other": "x"}', '{"text": "The awakened tree sways."}'])
check("a phantom on the last try is taken: the telling is never lost to it", text == "The awakened tree sways." and len(seen) == 3, (text, len(seen)))
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
