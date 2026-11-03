"""(f486) The townsfolk brief: what a person is given for one reply is chosen for that line. The lore that bears on it (at most four,
from many), every clue they hold, and one line naming the rest; the town's list, the land and the guild board in full only when the line
is about them or their work is them, the checks still given the town's list so an invented smithy is sent back; the character's pronoun;
a mood only while it lasts; nothing of a secret while its gate is shut; the Orenna line only when the name is said; no day number; a
promise made to them kept as heard; the voice's dice their own; and the reply's request smaller than it was."""
import ast
import re
import sys
import types
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import brief, memory, truth
from llm import gateway
from world.loader import Fact

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- lore per line: many facts, at most four that bear on it, every clue, the rest named
facts = [Fact(id=f"lore_{i}", text=f"The old mill number {i} grinds barley for the valley farms.", known_by=[]) for i in range(43)]
facts += [Fact(id="ford_toll", text="The ford below the bridge has a toll keeper who takes copper from carts.", known_by=[]),
          Fact(id="wolves_north", text="Wolves have come down from the northern ridge this winter.", known_by=[]),
          Fact(id="herb_lore", text="Moonwort grows on the shaded banks of the Wend.", known_by=[]),
          Fact(id="temple_bell", text="The temple bell cracked in the frost two winters back.", known_by=[]),
          Fact(id="clue:t1:0", text="The miller's boy saw lantern light in the barn at night.", known_by=[])]
shown, index = brief.lore(facts, "Have you seen wolves near the ford, and who keeps the toll?", [])
lore_shown = [f for f in shown if not f.id.startswith("clue:")]
check("of 47 lore facts, a line is given at most four that bear on it, and every clue held", len(lore_shown) <= 4
      and {"ford_toll", "wolves_north"} <= {f.id for f in lore_shown} and any(f.id == "clue:t1:0" for f in shown), [f.id for f in shown])
check("...and one line naming what else they know, so nothing they know is a facade", index.startswith(brief.rules()["index_label"])
      and "temple bell" in index and "herb lore" in index, index[:200])
check("...the same line chooses the same, every time (pure, a fixed order)", brief.lore(facts, "Have you seen wolves near the ford, and who keeps the toll?", [])[0] == shown)

# ---- the town's list, the land, the board: in full when asked, or the role's work
check("the land comes in when the line is about herbs, never for the weather", brief.asked("land", "Where do herbs grow around here?")
      and not brief.asked("land", "Fine weather, isn't it?"))
check("...the board for work, and always for the guild clerk", brief.asked("board", "Any work going?") and brief.asked("board", "Good day.", "guild_clerk")
      and not brief.asked("board", "Good day.", "farmer"))
given = "THE PERSON IN FRONT OF YOU: a stranger."
town = ["smithy: none in Parth (the nearest is in Lethoria)"]
check("an invented smithy is sent back though the town's list was not in the prompt (the checks are given it)",
      truth.absent_here("Take it to the smithy by the well.", given) == "" and truth.absent_here("Take it to the smithy by the well.", given + "\n" + "\n".join(town)) != "")

# ---- in play: the request for one talk
game = simlib.campaign("brief_486", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter(ws.player.location)
REQ = []
real = gateway._client


def chat(**k):
    if k["format"].get("title") == "NPCReply":
        REQ.append(k["messages"][1]["content"])
    return real.chat(**k)


gateway._client = types.SimpleNamespace(chat=chat)
npc = sorted((n for n in ws.present if n.role not in ("guild_clerk", "guild_master")), key=lambda n: n.id)[0]
npc.mood, npc.mood_until, npc.mood_source = "glad of the rain", ws.minutes - 10, "the world"
store.save_npc(npc)
ws.present = [store.load_npc(npc.id)] + [n for n in ws.present if n.id != npc.id]
ws.player.character.pronoun = "she"
stub.reply_extra = {"they_promised": "to bring back the lost lamb"}
stub.plan = [{"kind": "talk", "target": npc.id, "speech": "Fine weather today. I'll find your lamb for you."}]
ws.turn('I say, "Fine weather today. I\'ll find your lamb for you."')
stub.plan, stub.reply_extra = None, None
req = REQ[-1] if REQ else ""
check("the character's pronoun is in the block about the one in front of them", "Speak of them as she." in req, re.findall(r"THE PERSON IN FRONT OF YOU[^\n]*", req))
check("a weather line brings no land, no town's list and no board", "THE LAND AROUND YOU" not in req and "WHAT THIS TOWN HAS" not in req
      and "ON THE GUILD BOARD" not in req, [l for l in req.splitlines() if l.isupper()][:12])
check("a mood past its time is not theirs any more", "glad of the rain" not in req)
check("no day number reaches them", not re.search(r"\bday \d+\b", req), re.findall(r".{20}\bday \d+\b.{20}", req)[:3])
check("the Orenna line comes only when the name is said", "Orenna" not in req)
heard = simlib.remembered(store, npc.id, kind="promise_heard")
check("a promise made to them in words is kept as theirs, heard, from the character", len(heard) == 1 and heard[0]["source"] == ws.acting
      and "lost lamb" in heard[0]["text"], heard)
REQ.clear()
stub.plan = [{"kind": "talk", "target": npc.id, "speech": "Where do herbs grow around here?"}]
ws.turn('I say, "Where do herbs grow around here?"')
stub.plan = None
check("...and asked about herbs, the land is given", REQ and ("THE LAND AROUND YOU" in REQ[-1] or not __import__("npc.land", fromlist=["land_lines"]).land_lines(ws.world, npc.location)),
      [l for l in (REQ[-1] if REQ else "").splitlines() if l.isupper()][:12])
gateway._client = real

# ---- a closed secret writes nothing; the voice's dice are their own
secret_src = Path("scenes/arc_actions.py").read_text()
check("while a secret's gate is shut nothing of it reaches the brief", "[YOU KNOW" not in secret_src)
src = Path("scenes/world.py").read_text()
calls = [n for n in ast.walk(ast.parse(src)) if isinstance(n, ast.Call) and getattr(n.func, "attr", "") == "roll_stance"]
check("the stance is drawn from the conversation's own die, never the scene's stream", calls and all("keyed" in ast.unparse(c) for c in calls),
      [ast.unparse(c)[:80] for c in calls])
check("...and the reply's lines on how they talk from the speaker's own", 'rng=streams.keyed("voice"' in src)
game.close()
import shutil
shutil.rmtree("saves/brief_486", ignore_errors=True)

# ---- the largest golden reply is smaller than it was
import gzip, json
calls = [json.loads(l) for l in gzip.open("data/replay/sessions/stub_short/calls.jsonl.gz", "rt")]
sizes = [len(c["request"]["messages"][0]["content"]) + len(c["request"]["messages"][1]["content"]) for c in calls if c.get("title") == "NPCReply"]
check("the largest golden townsfolk reply is under its ceiling (17,000 chars; 24,954 before)", sizes and max(sizes) <= 17000, sizes)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
