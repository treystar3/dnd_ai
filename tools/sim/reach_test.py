"""(f344) What a speaker can lay hands on, and how tense the moment is. A tester's Maren had a hand on her sword hilt in ten frames of
nineteen: her only example gesture was the hilt, and the sword her only prop. Instead of policing the habit, every dialogue frame is now
shown what is really within reach - the speaker's trade's own tools, the place, their wares and stock, the ground, what they carry - and
THE MOMENT: easy, or tense and why. In a tense moment a hand may stay on a weapon; in an easy one the weapon is left alone."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import yaml
from engine import quirks, reach
from scenes import voice
from scenes import world_prompts as wp
from llm.contracts import DialogueFrame

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- 1. the rules
roles = {r["id"] for r in yaml.safe_load(open("data/world/roles.yaml", encoding="utf-8"))}
types_ = {p.get("type", "") for p in yaml.safe_load(open("data/world/places.yaml", encoding="utf-8"))}
check("every trade has something to hand, and every place type named is real", reach.problems(roles, types_) == [], reach.problems(roles, types_))
check("a checker that sees a made-up trade says so", any("not a role" in x for x in reach.problems(roles - {"smith"}, types_)))

# ---- 2. what is within reach: the speaker's own first, then the place, the wares, the ground
smith = reach.within("smith", "town", wares=["a horseshoe"], ground=["a dropped glove"])
check("the smith has her hammer and tongs to hand before anything of the street's", smith[:2] == ["the hammer", "a pair of tongs"] and "a wall" in smith, smith)
check("...and what she sells is there to be handled", "a horseshoe" in smith)
check("...at most the length the rules set", len(smith) <= reach.R["most"])
maren = reach.within("", "guild", carries=["her greatsword", "the A crest on her shoulder"])
check("Maren at the guild: her own gear, then the board and the desk", maren == ["her greatsword", "the A crest on her shoulder", "the contract board", "the clerk's desk"], maren)

# ---- 3. the moment
check("an ordinary word with a baker is easy", reach.moment("baker", 60) == reach.EASY)
check("a guard facing someone the watch wants is tense", reach.moment("guard", 60, "confront").startswith("tense"))
check("...but the same guard on a quiet day is not", reach.moment("guard", 60, "cold") == reach.EASY)
check("someone who distrusts the stranger is tense", reach.moment("baker", 20).startswith("tense"))
check("a prisoner facing their captor is tense", reach.moment("prisoner", 60).startswith("tense"))
check("a fight is tense", reach.moment(fight=True).startswith("tense"))
check("a reason the caller knows is given as the reason", reach.moment(wary="terms are being made with the bandits") == "tense - terms are being made with the bandits")

# ---- 4. the frames are shown it, through the real paths
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
asked = []
def fake(task, system, request, schema, **kw):
    asked.append(request)
    return DialogueFrame(before="", after="")
real = voice.generate
shutil.rmtree("saves/reach_test", ignore_errors=True)
world = load_world(); store = CampaignStore.open_or_create("reach_test"); store.meta.seed = 3; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player()); ws.enter("parth")
reply = types.SimpleNamespace(speech="Horseshoes, a copper apiece.", gesture="", intent="talk")
smith_npc = next(n for n in ws.residents if n.role == "smith")
ws.present = [smith_npc] + [n for n in ws.present if n.id != smith_npc.id]
voice.generate = fake
ws.narrate_dialogue(smith_npc, smith_npc.label(), smith_npc.label(), "i ask what she makes", reply, False)
req = asked[-1]
check("a townsperson's frame is shown their trade's tools within reach", "WITHIN REACH: the hammer; a pair of tongs" in req, req[req.find("WITHIN"):][:160])
check("...and that the moment is easy", "THE MOMENT: easy" in req)
smith_npc.trust = 15
ws._framed_here = set()                     # (f347) an ordinary second line gets no frame; start the visit over so this one is framed
ws.narrate_dialogue(smith_npc, smith_npc.label(), smith_npc.label(), "i ask what she makes", reply, False)
check("...and tense when they distrust the stranger", "THE MOMENT: tense - they distrust the stranger" in asked[-1])
smith_npc.trust = 50

ws.player.mentor["introduced"] = False
ws.mentor_show("Where did you come by that weapon?", reply_to="hello")
check("Maren, still weighing a stranger: her greatsword within reach, and the moment tense with the reason",
      "WITHIN REACH: her greatsword" in asked[-1] and "THE MOMENT: tense - she does not yet know whether this armed stranger is a bandit" in asked[-1], asked[-1][-700:])
ws.player.mentor["introduced"] = True
ws.mentor_show("Good. Then let's get you on the board.", reply_to="i'm no bandit")
check("...and once the stranger has settled her, easy", "THE MOMENT: easy" in asked[-1])

hire = {"name": "Bram", "role": "fighter", "people": "human", "rank": "F", "blurb": "a scarred sellsword", "level": 3, "bond": 0}
ws.companion_show(hire, "We should move before dark.")
check("a hire's frame is shown what a fighter carries", "WITHIN REACH: a sword; a shield; a pack" in asked[-1], asked[-1][asked[-1].find("WITHIN"):][:120])
voice.generate = real

# ---- 5. the rule, and no habit policing
check("the frames carry the hands rule, which lets a hand stay on a weapon while a moment is tense",
      quirks.HANDS_RULE in wp.DIALOGUE_SYSTEM and quirks.HANDS_RULE in wp.EXCHANGE_SYSTEM and "stay there for as long as the tension lasts" in quirks.HANDS_RULE)
check("the exchange is shown what is within reach too", "WITHIN REACH:" in wp.exchange_request("t", world.places["parth"], ["Bram"], [], "a", "b", [], "short", reach=["a cart"]))
mentor_rule = yaml.safe_load(open("data/world/mentor.yaml", encoding="utf-8"))["frame"]["length"]
party_rule = yaml.safe_load(open("data/rules/party.yaml", encoding="utf-8"))["frame"]
check("no example gesture names a hilt or a strap any more", "hilt" not in mentor_rule and "strap" not in party_rule["talk"] and "with their hands" not in party_rule["exchange"])
check("there is no repetition guard on gestures: the world decides, not a rule against habits", not hasattr(voice, "reached_again"))

shutil.rmtree("saves/reach_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
