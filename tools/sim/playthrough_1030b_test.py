"""(f406) What a second evening's play showed. In a fight: 'Jorn, heal yourself. I use spark bolt' gave the order and dropped the spell,
and 'heal yourself' was read as heal me; 'get behind me' moved the player instead of the hire. On the road: a find told of a dropped
clerk's ledger and the player took wool slippers, and the arrival told the ledger again, lying at the hollow. And: Maren's '"Good hunting."'
shown as narration; a contract's lead reading 'Word of Four pieces...'; a hire who is he framed as 'they'."""
import io, contextlib, shutil, sys, random, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
NOTES, SAID = [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.panel = lambda name, data: False
from engine import combat, party
from npc.traits import load_traits
from scenes.world import WorldScene
from scenes.combat_scene import CombatScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
from engine.hygiene import clean as hygiene_clean

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/playthrough_1030b_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("playthrough_1030b_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
store.save_player(PlayerState(character=char, location="greyhollow_foothills" if "greyhollow_foothills" in world.places else "parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
jorn = {"id": "0-2", "name": "Jorn Elliston", "role": "priest", "level": 1, "permanent": True, "rank": "F", "bond": 10, "pronoun": "he",
        "hp_frac": 1.0, "hp_at": 0}
ws.player.party = [jorn]
ws.player.party_mode = "with"

# ---- orders in a fight
creature = world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", name="wolf 1")
foe.hp = foe.max_hp = 10 ** 6
ws.narrate_with = lambda *a, **k: None
sc = CombatScene.begin(ws, creature, [foe], "It is on you:")
ws.combat = sc
f = sc.fight
ally = next(a for a in f.allies() if a.name.startswith("Jorn"))
who, kind, target = sc.order_of("Jorn, heal yourself. I use spark bolt")
check("'heal yourself' is a heal order for the healer's own wounds", kind == "heal" and target == "self", (kind, target))
acted = []
sc.interpret = lambda text: types.SimpleNamespace(kind="ability", text=text)
real_act = sc.act
sc.act = lambda intent, text: acted.append(text)
NOTES.clear()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    sc.turn("Jorn, heal yourself. I use spark bolt")
check("...the order is given", ally.order == "heal" and ally.order_target == "self" and "their own wounds" in buf.getvalue(), (ally.order, buf.getvalue()))
check("...and the spell in the same line is cast, not dropped", acted == ["I use spark bolt"], acted)
ally.hp = ally.max_hp * 0.4
f.player.hp = f.player.max_hp * 0.5
before_me, before_him = f.player.hp, ally.hp
combat.ally_turn(f, ally, random.Random(1))
check("...and on his turn he heals himself, not the player", ally.hp > before_him and f.player.hp == before_me, (before_him, ally.hp, before_me, f.player.hp))
f.round += 1
acted.clear()
who, kind, target = sc.order_of("Jorn I need you to get behind me")
check("'get behind me' is an order to the hire, not a step back by the player", kind == "back" and who[0] is ally, kind)
from engine import battlefield as bf
bf.engage(f, ally, foe)
with contextlib.redirect_stdout(io.StringIO()):
    sc.turn('"Jorn, stand behind me". I cast spark bolt')
check("...he goes to the back row, out of the press", ally.order == "back" and ally.row == "back" and not ally.engaged_with, (ally.order, ally.row, ally.engaged_with))
check("...and the player's own spell in the line is cast", acted == ["I cast spark bolt"], acted)
ally.hp = ally.max_hp
f.player.hp = f.player.max_hp
f.round = 6                                              # past the opening blessing: nothing to heal, nothing to bless
f.log.clear()
combat.ally_turn(f, ally, random.Random(2))
check("...from there he goes to no one", any("keeps behind" in l for l in f.log) and not ally.engaged_with, f.log[-3:])
check("a line that is only an order acts on nothing else", sc.own_part("Jorn attack the wolf", [ally]) == "")
sc.act = real_act
ws.combat = None
store.save_combat(None)

# ---- a find on the road shows the thing taken
import scenes.road_actions as ra
from llm.contracts import RoadEvent
seen = {}
def fake_generate(task, system, user, schema, **k):
    seen["user"] = user
    return RoadEvent(title="The Dropped Ledger", scene="A ledger lies in a rut.", kind="find", detail="a ledger")
real_gen, ra.generate = ra.generate, fake_generate
road = next(iter(world.roads.values()))
a, b = road.from_, road.to
before = {id(i) for i in ws.pack}
hostile_was, kinds_was = ra.R["hostile"], ra.R.get("kinds")
ra.R["hostile"] = 0
ra.R["kinds"] = {"find": 1}                              # (f411) the engine picks the kind; a find here
road_out = io.StringIO()
with contextlib.redirect_stdout(road_out):
    ws.road_event([a, b], a, b, 60, 0.3, "I walk on", [], walked=40)
told = road_out.getvalue()
check("(f408) a road's happening comes in the middle of a journey: where from, where to, how long, before it",
      f"You set out from {world.places[a].name}" in told and told.index("set out") < told.index("A ledger lies"), told[:400])
check("...and the model is told the journey and who walks with the player", "THE JOURNEY: set out from" in seen.get("user", "")
      and "WHO IS WITH THEM" in seen.get("user", "") and "Jorn Elliston" in seen.get("user", ""), seen.get("user", "")[:600])
def fake_generate2(task, system, user, schema, **k):
    return RoadEvent(title="The Ford", journey="The road runs on under a grey sky, Jorn a step behind you.", scene="A ford, swollen.",
                     kind="sight")
ra.generate = fake_generate2
road_out = io.StringIO()
with contextlib.redirect_stdout(road_out):
    ws.road_event([a, b], a, b, 60, 0.3, "I walk on", [], walked=40)
check("...the model's own telling of the walk when it gives one", "grey sky, Jorn a step behind you" in road_out.getvalue(), road_out.getvalue()[:300])
# ---- (f411) what the examples showed: every happening a find, the walk left out, an odd fallback line, a stray backslash
ra.R["kinds"] = {"meeting": 1}
ra.generate = fake_generate
found_user, pack_was = seen.get("user", ""), list(ws.pack)
with contextlib.redirect_stdout(io.StringIO()):
    ws.road_event([a, b], a, b, 60, 0.3, "I walk on", [], walked=40)
check("the engine picks what kind of happening it is, and the model is told it", "KIND: meeting" in seen.get("user", "")
      and "finds and takes" not in seen.get("user", ""), seen.get("user", "")[-400:])
seen["user"] = found_user
ws.pack[:] = pack_was
ra.R["kinds"] = kinds_was
check("...the kinds are weighted in the rules, finds not the only one", len(kinds_was or {}) >= 4 and kinds_was.get("find", 0) < sum(kinds_was.values()) / 2,
      kinds_was)
import json as _json
from pydantic import ValidationError
ctx = {"hostile": False, "checks": ["perception"], "kind": "meeting", "want_journey": True}
def road_ok(**kw):
    body = dict(title="T", journey="You walk an hour.", scene="A carter waves.", kind="meeting")
    body.update(kw)
    try:
        RoadEvent.model_validate_json(_json.dumps(body), context=ctx)
        return True
    except ValidationError:
        return False
check("...and a happening of another kind is sent back", road_ok() and not road_ok(kind="find"))
check("the walk before a happening is required: left out, it is sent back", not road_ok(journey="  ")
      and "journey" in RoadEvent.model_json_schema().get("required", []))
unnamed = next(((x, y) for x in world.places for y in world.places if x != y and world.road_between(x, y) is None), None)
if unnamed:
    line = ws.journey_line([unnamed[0], unnamed[1]], unnamed[0], unnamed[1], 90)
    check("...the fallback on a way with no named road says no 'by the way toward'", "way toward" not in line
          and f"bound for {world.places[unnamed[1]].name}" in line, line)
check("a stray backslash before punctuation is taken out", hygiene_clean("the iron shears.\\, nearby") == "the iron shears., nearby"
      and hygiene_clean("a path\\ winds") == "a path winds")
from engine import hygiene as _hy
check("...and the walk is prose the gateway checks, like the scene", "journey" in _hy.PROSE and "scene" in _hy.PROSE)
ra.R["hostile"] = hostile_was
ra.generate = real_gen
new = [i for i in ws.pack if id(i) not in before]
from engine import inventory as inv
check("a road find is rolled first and the scene is told what it is", new and inv.label(new[0]) in seen.get("user", ""), (seen.get("user", "")[-300:], [inv.label(i) for i in new]))
asked = []
ws.narrate = lambda req, text="", *a, **k: asked.append(req)
ws.quiet_return = lambda *a, **k: False
ws.finish_journey([a, b], 60, "I walk on", ["The Dropped Ledger: A ledger lies in a rut."])
check("the arrival is told the road's happening is read already, and not to tell it again", asked and "do not tell it again" in asked[-1], asked[-1:])
ws.finish_journey([a, b], 90, "I walk on", [])
check("(f408) a long walk with nothing on the way is felt on arrival", "sentences of the walk itself" in asked[-1], asked[-1:])
ws.finish_journey([a, b], 20, "I walk on", [])
check("...a short one is not", "Say little of the road" in asked[-1], asked[-1:])

# ---- Maren's farewell, a lead's name, a hire's pronoun
said = []
uc.say = lambda text, speaker="": said.append((speaker, text))
ws.mentor_narrate('Whatever doubt she had about you seems to have passed. She gives you a small nod.\n\n"Good hunting."')
check("a quoted line in her scene text is her speaking, under her name", said and said[-1][1] == "Good hunting.", said)
check("a thing's name inside a sentence is not capitalised mid-sentence", ws.mid_sentence("Four pieces of a map to a dragon's hoard")
      == "four pieces of a map to a dragon's hoard" and ws.mid_sentence("Old Brannoch's ring") == "Old Brannoch's ring")
check("a hire who is he is framed as he, never they", "Jorn is he" in ws.frame_for(jorn, "how they listen") and "never they" in ws.frame_for(jorn, "x"))
# ---- (f409) dialogue that sounds like people
from engine import quirks, voice_rules, hygiene
from npc import prompts as npc_prompts
from scenes import party_prompts
block = quirks.style_block()
check("every speaker is told to answer what was said first, and to keep a short exchange short",
      "a greeting gets a greeting back" in block and "a few words get a few words back" in block, block[:300])
check("...and to leave the weather out of what they say", "Leave the weather" in block)
check("...townsfolk alike", "a greeting gets a greeting back" in npc_prompts.CONVERSATION_SYSTEM)
from engine import voice_profile
import yaml
SP = yaml.safe_load(open("data/rules/speech.yaml", encoding="utf-8"))
member = {"id": "brokur", "name": "Brokur Durdal", "people": "dwarf", "said": [],
          "speech": {"culture": next(c for c, s in voice_profile.S["cultures"].items() if s.get("tongue") == "ironvein"), "fluency": "learner",
                     "strength": "light"}}
acc = voice_profile.accent(member)
check("(f410) a speaker with an accent has it in every reply, not on a roll", "verb at the end" in acc and "in every line" in acc, acc)
rolled = [voice_profile.culture_feature(member, random.Random(i))[0] for i in range(200)]
check("...and it is no longer one of the touches rolled per reply", "transfer" not in rolled, set(rolled))
member["speech"]["fluency"] = "native"
check("...someone raised on Common has none", voice_profile.accent(member) == "")
from engine import mentor as _mentor
check("Maren is told to say each point once, briefly", any("Use no more words than the points need" in r for r in _mentor.M["voice"]["speech_rules"]))
check("a name run into a word with an underscore is written as words", hygiene.clean("Right_Nickkelly.") == "Right Nickkelly.")
store.close()
shutil.rmtree("saves/playthrough_1030b_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
