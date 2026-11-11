"""(f583) How a moment sounds is drawn from a pool for that kind of moment (docs/design/09 A3). The exemplars are pools in
data/rules/voice.yaml (narration: general, arrival, night, interior, grief; the fight; speech: small talk, refusal, gossip); the
engine picks the pool from what it knows at the call (a death this line, a place newly reached, the dark, an indoor place; a wary or
busy person or a low trust, news in their brief), never the model; each call is given three lines of it, drawn from the input's own
dice and never the same three twice running, at the end of its request. The system prompts carry none, so the server's cached
prefix stays the same from call to call.
Run: python tools/sim/exemplar_pools_583_test.py"""
import random
import re
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import clock, streams, voice_rules as vr
from scenes import combat_prompts as cp, party_prompts as ppr, voice, world_prompts as wp
import npc.prompts as npp

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

EX = vr.V["exemplars"]
# ---- the pools, as data, held to the draft's rules at startup
check("the pools are in the data: five for narration, the fight, three for speech", set(EX["narration"]) == {"general", "arrival", "night", "interior", "grief"}
      and isinstance(EX["fight"], list) and set(EX["speech"]) == {"small_talk", "refusal", "gossip"}, sorted(EX))
every = [l for p in EX["narration"].values() for l in p] + list(EX["fight"]) + [l for p in EX["speech"].values() for l in p]
doc = open("docs/design/09a_exemplar_pools_draft.md", encoding="utf-8").read()
draft = [l[2:].replace("*(current)* ", "").strip() for l in doc[doc.index("## Narration"):].splitlines() if l.startswith("- ")]
check("...every approved line in its pool, and the general mix the four passages there were before", set(draft) <= set(every)
      and len(EX["narration"]["general"]) == 4 and all(l in every for l in EX["narration"]["general"]), sorted(set(draft) - set(every))[:3])
check("the startup checks pass on the game's pools", vr.pool_problems() == [], vr.pool_problems())
bent = {"draw": 3, "refusal_trust": 30, "narration": {**EX["narration"], "night": ["Too few.", "Lines."]}, "fight": EX["fight"],
        "speech": {**EX["speech"], "gossip": EX["speech"]["gossip"] + ["A line with a dash — in it."]}}
probs = vr.pool_problems(bent)
check("...and catch a pool too small to draw from without repeating, and a line with a dash", any("night" in p for p in probs)
      and any("dash" in p for p in probs), probs)

# ---- the draw
pool = EX["fight"]
a = vr.draw(pool, random.Random("x"), ())
b = vr.draw(pool, random.Random("x"), ())
check("a draw is three lines of the pool, the same for the same dice", len(a) == 3 and len(set(a)) == 3 and set(a) <= set(pool) and a == b, a)
seen = []
for i in range(200):
    seen.append(vr.draw(EX["narration"]["general"], random.Random(f"r{i % 3}"), seen[-1] if seen else ()))
check("...never the same three twice running, even from a pool of four drawn with the same few dice",
      all(set(x) != set(y) for x, y in zip(seen, seen[1:])), next(((x, y) for x, y in zip(seen, seen[1:]) if set(x) == set(y)), None))
block = vr.exemplar_block("narration", a)
check("the block heads the lines as the game's register, never lines to reuse or facts of the moment",
      block.startswith("HOW NARRATION SOUNDS HERE") and "never lines to reuse" in block and all(l in block for l in a), block)

# ---- no system prompt carries them: the cached prefix holds still
SYSTEMS = {"narrator": wp.NARRATOR_SYSTEM, "frame": wp.DIALOGUE_SYSTEM, "exchange frame": wp.EXCHANGE_SYSTEM, "fight": cp.NARRATE_SYSTEM,
           "fight opening": cp.START_SYSTEM, "aftermath": cp.AFTERMATH_SYSTEM, "hire": ppr.TALK_SYSTEM, "townsperson": npp.CONVERSATION_SYSTEM}
for name, text in SYSTEMS.items():
    check(f"the {name}'s system prompt carries no exemplar", not re.search(r"SOUNDS? HERE", text) and not any(l in text for l in every),
          [l for l in every if l in text][:2])

# ---- the engine picks the pool
g = simlib.campaign("pools_583", seed=5, location="trading_square")
ws = g.scene
ws.enter("trading_square")
ws.begin_line()
ws.store.arm(False)
base = (ws.minutes // 1440) * 1440
day = next(base + m for m in range(0, 1440, 30) if not clock.is_dark(base + m))
dark = next(base + m for m in range(0, 1440, 30) if clock.is_dark(base + m))
ws.store.meta.minutes = day
check("by day, out of doors, nothing else: the general pool", ws.narration_pool() == "general", ws.narration_pool())
ws.store.meta.minutes = dark
check("in the dark: the night pool", clock.is_dark(ws.minutes) and ws.narration_pool() == "night", ws.narration_pool())
ws.store.meta.minutes = day
ws.place.type, kind = "inn", ws.place.type
check("indoors: the interior pool", ws.narration_pool() == "interior", ws.narration_pool())
ws.place.type = kind
from engine import pulse
here_town = pulse.town_of(ws.world, ws.player.location)
same = next((pid for pid in ws.world.places if pid != ws.player.location and pulse.town_of(ws.world, pid) == here_town), None)
ws.line_from = same
check("a step within the same town is no arrival", same is not None and ws.narration_pool() == "general", (same, ws.narration_pool()))
far = next(pid for pid in ws.world.places if pulse.town_of(ws.world, pid) not in ("", here_town))
ws.line_from = far
check("a new town reached this line: the arrival pool, before the dark or a roof", ws.narration_pool() == "arrival", ws.narration_pool())
ws.line_losses = 1
check("a companion's death this line: the grief pool, before everything", ws.narration_pool() == "grief", ws.narration_pool())
ws.line_losses, ws.line_from = 0, ws.player.location
src_rx = open("engine/reactions.py", encoding="utf-8").read()
check("...counted when the party's death is published (engine/reactions.py fallen)", "self.ws.line_losses = getattr(self.ws, \"line_losses\", 0) + 1" in src_rx)
from engine import regard as _rg
people = [n for n in (ws.residents or ws.present)]
met_one, stranger = people[0], (people[1] if len(people) > 1 else None)
real_of = _rg.of
import types as _t
_rg.of = lambda n, who: _t.SimpleNamespace(met=(n.id == met_one.id), trust=50)


def gone(npc, place, dead=True):
    ws.store.journal(ws.minutes, "npc_gone", "", npc.id, f"{npc.name} is gone", {"how": "killed", "place": place, "dead": dead})


gone(met_one, far)
check("someone the acting character met, dying far away: news, not grief", ws.narration_pool() != "grief" and not ws.died_this_line())
if stranger is not None:
    gone(stranger, ws.player.location)
    check("a stranger dying here: no grief", not ws.died_this_line())
gone(met_one, ws.player.location, dead=False)
check("someone met leaving here alive: no grief", not ws.died_this_line())
gone(met_one, ws.player.location)
check("someone the acting character met, dying here this line: the grief pool", ws.died_this_line() and ws.narration_pool() == "grief")
_rg.of = real_of
ws.begin_line()
ws.store.arm(False)
ws.store.meta.minutes = day
check("a new line starts with no loss and from where the player stands", ws.line_losses == 0 and ws.line_from == ws.player.location
      and ws.narration_pool() == "general")
check("a loss is taken back with a failed operation", "line_losses" in ws.ROLLED)

npc = next(iter(ws.residents or ws.present), None)
check("(someone to talk to)", npc is not None)
from engine import regard
import types
real_of = regard.of
trust = real_of(npc, ws.acting).trust
check("a person at ease with nothing to pass on: small talk", ws.speech_pool(npc, "", []) == "small_talk" or trust < EX["refusal_trust"],
      (ws.speech_pool(npc, "", []), trust))
check("...wary or busy, in the stance's own words from the data: refusal", ws.speech_pool(npc, vr.V["stances"]["wary"]["text"], []) == "refusal"
      and ws.speech_pool(npc, vr.V["stances"]["busy"]["text"], []) == "refusal"
      and ws.speech_pool(npc, vr.V["stances"]["tired"]["text"], []) != "refusal" if trust >= EX["refusal_trust"] else True)
check("...news in their brief: gossip", ws.speech_pool(npc, "", ["The ferry is late again."]) in ("gossip", "refusal"))
regard.of = lambda *a, **k: types.SimpleNamespace(trust=EX["refusal_trust"] - 1)
check("...a trust under the mark: refusal, before gossip", ws.speech_pool(npc, "", ["The ferry is late again."]) == "refusal")
regard.of = lambda *a, **k: types.SimpleNamespace(trust=EX["refusal_trust"] + 20)
check("...and at ease with news: gossip", ws.speech_pool(npc, "", ["The ferry is late again."]) == "gossip"
      and ws.speech_pool(npc, "", []) == "small_talk")
regard.of = real_of

# ---- the draw on the scene: the input's dice, never the same three running, taken back with a failed operation
streams.begin(5, 9, "look")
first = ws.exemplars("narration")
second = ws.exemplars("narration")
streams.begin(5, 9, "look")
held = dict(ws.__dict__.get("_exemplars") or {})
ws.__dict__.pop("_exemplars", None)
again = ws.exemplars("narration")
check("the same input, from the same start, draws the same lines (a replay meets them)", again == first, (again[:80], first[:80]))
lines = lambda b: [l.strip()[2:] for l in b.splitlines()[1:]]
check("...and the next call of the input draws another three", set(lines(first)) != set(lines(second)))
ws.__dict__["_exemplars"] = held
from llm.gateway import LLMError
before = dict(ws.__dict__["_exemplars"])
with ws.operation("test", "a step that draws and fails") as op:
    ws.exemplars("narration")
    raise LLMError("the model failed")
check("a draw inside an operation that fails is taken back (the attempt run again draws the same)", ws.__dict__.get("_exemplars") == before,
      (ws.__dict__.get("_exemplars"), before))

# ---- at the end of each request
req = wp.narration_request("t", ws.place, [], "x", exemplars=vr.exemplar_block("narration", a))
check("the narration's request ends with them", req.rstrip().endswith(a[-1]), req[-200:])
fr = wp.dialogue_request("t", ws.place, [], "w", "l", "d", "m", True, "p", "s", "", False, [], exemplars=vr.exemplar_block("narration", a))
check("...a frame's", fr.rstrip().endswith(a[-1]), fr[-200:])
ex = wp.exchange_request("t", ws.place, ["a"], [], "x", "y", [], "", "P", exemplars=vr.exemplar_block("narration", a))
check("...an exchange frame's", ex.rstrip().endswith(a[-1]), ex[-200:])
fq = cp.narrate_request("P", "t", "swing", ["x [h1]"], "sword", "fine", ["a wolf"], 2, exemplars=vr.exemplar_block("fight", a))
check("...a fight's", fq.rstrip().endswith(a[-1]), fq[-200:])
src = open("scenes/combat_scene.py", encoding="utf-8").read() + open("scenes/world.py", encoding="utf-8").read()
check("the aftermath and the opening are given the fight's", src.count('exemplars("fight")') >= 3, src.count('exemplars("fight")'))
import ast, pathlib
TASKS = {"narrate", "combat_narrate", "combat_opening", "combat_aftermath", "dialogue_frame", "hire_chat"}
missing = []
for path in sorted(pathlib.Path("scenes").glob("*.py")):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    tops = [n for n in tree.body if isinstance(n, ast.FunctionDef)] + [m for c in tree.body if isinstance(c, ast.ClassDef)
                                                                       for m in c.body if isinstance(m, ast.FunctionDef)]
    for fn in tops:                                           # the method as a whole: a request built above a nested tell() counts
        body = ast.unparse(fn)                                # a request built a few lines above the call counts
        for node in ast.walk(fn):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("fresh", "generate") and node.args
                    and isinstance(node.args[0], ast.Constant) and node.args[0].value in TASKS and "exemplars" not in body):
                missing.append(f"{path.as_posix()}:{node.lineno} {node.args[0].value}")
check("every prose call and every hire's line in the scenes is given its lines", not missing, missing)
src_fr = open("scenes/party_actions.py", encoding="utf-8").read() + open("scenes/banter_actions.py", encoding="utf-8").read()
check("...a frame in a fight, the fight's", src_fr.count('exemplars("fight" if in_fight else "narration")') == 2)
hp = ppr.talk_prompt("how", "core", "rel", [], [], [], "P", "Hello there.", exemplars=vr.exemplar_block("speech", ["Line one.", "Line two."])).render()
check("...a hire's, after how they speak and just before what was said to them",
      hp.index("HOW YOU SPEAK") < hp.index("SOUND HERE") < hp.index("Line two.") < hp.index("Hello there."), hp[-400:])
tp = npp.conversation_prompt(npc, ws.place, [], [], [], "Good day.", [], [], [], who=ws.acting,
                             exemplars=vr.exemplar_block("speech", ["Line one.", "Line two."])).render()
check("...a townsperson's, just before what was said to them", tp.index("SOUND HERE") < tp.index("Line two.") < tp.index("Good day."), tp[-400:])
g.session.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
