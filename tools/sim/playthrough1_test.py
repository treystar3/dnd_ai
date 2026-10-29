"""(f373) What the first logged playthrough (a dragoon, the tutorial and back to the hall) showed, each fixed: Maren said goodbye and was
standing in the hall a minute later, telling the player off for 'their' late companions, who were hers; hiring narrated the party walking
out of the hall; 'sure go for it' to a hire's question went to the clerk; her four-line beats were refused for four paragraphs; wolves
were told as wearing plate mail; Lance Volley was told as a thrown volley with magic humming; Beast Command used on a wolf was answered
as idle chat; 'uhh okay then, I head to the clerk' made the clerk answer 'uhh okay then' before the player reached her."""
import random, re, shutil, sys, types
sys.path.insert(0, ".")
import simlib
STUB = simlib.Stub("warrior", 5)
simlib.install(STUB)
import ui.console as uc
NOTES, SAID = [], []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from core.models import UseContext
from engine import combat, martial as MA, mentor
from llm.contracts import ActionIntent as A
from npc.models import NPC
from npc.traits import load_traits
from scenes import combat_prompts as cp
from scenes.combat_scene import CombatScene
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- Maren: her goodbye says she is going on her way (f382: she leaves Parth on the capital's work), and her party is hers
ret = mentor.M["return"]
check("her farewell says she is leaving Parth on her own work", "capital" in ret["speech"][1] and "on the road" in ret["speech"][1]
      and "road out of town" in ret["leave"] and any("you leave Parth today" in i for i in ret["info"]), ret["speech"][1])
char, _ = simlib.make_character("warrior", random.Random(1))
pl = PlayerState(character=char, location="parth")
npc = mentor.make_npc(pl, 600, 3, "guild_house")
check("as a person of the world her party is her own, and she knows the stranger came alone", "capital" in npc.concern
      and any("not the stranger's" in m.text and "came alone" in m.text and "My own party" in m.text for m in npc.memories) and npc.gone,
      (npc.concern, [m.text for m in npc.memories][-1:]))

# ---- a scene at the hall
world = load_world()
shutil.rmtree("saves/playthrough1_test", ignore_errors=True)
store = CampaignStore.open_or_create("playthrough1_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 120; store.save_meta()
char.level = 10
store.save_player(PlayerState(character=char, location="guild_house", guild_rank="F"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
clerk = NPC(id="clerk_t", name="Emette Thorpham", people="human", role="guild_clerk", location="guild_house", name_known_to_player=True, met_player=True)
ws.present = [clerk]

# ---- 'uhh okay then, I head to the clerk at the desk'
plan = [A(kind="talk", target="clerk_t", speech="uhh okay then"), A(kind="move", destination="clerk_t")]
got = ws.walk_after_word("uhh okay then, I head to the clerk at the desk", plan)
check("an acknowledgement then a walk to the clerk: the walk is the step, the words go", got is not None and [a.kind for a in got] == ["move"], got)
plan = [A(kind="talk", target="clerk_t", speech="Any work going for my rank?"), A(kind="move", destination="clerk_t")]
got = ws.walk_after_word("I ask the clerk about work and head over", plan)
check("...real words then a walk to the one spoken to: the words stand, the walk goes", got is not None and [a.kind for a in got] == ["talk"], got)
check("...and a plan with no such pair is left alone", ws.walk_after_word("x", [A(kind="look")]) is None)

# ---- a hire's question answered 'sure go for it'
ram = {"id": "0-4", "name": "Ram Moll", "role": "priest", "level": 8, "rank": "F", "blurb": "x", "permanent": True, "base_level": 8,
       "hired_at": 10, "bond": 20, "quirks": {}, "motive": "coin"}
ws.player.party = [ram]
for line, want in (("sure go for it", True), ("yes, go ahead", True), ("sounds good", True), ("sure, let's go to the inn", False), ("I go to the inn", False)):
    ws._hire_last = ("Ram Moll", ws.store.meta.turn - 1)
    check(f"after Ram asked, '{line}' is {'an answer to him' if want else 'a step of its own'}", (ws.hire_followup(line) is not None) == want)

# ---- hiring: they join here, nobody goes anywhere
told = []
ws.narrate = lambda req, text="", **k: told.append(req)
ws.relations_seed = lambda: None
offered = ws.party_roster()
pick = next((m for m in offered if m["fee"] <= 10 ** 6), None)
ws.player.character.coins = 10 ** 6
if pick:
    ws.party_hire(pick["name"], f"hire {pick['name']}", offered, exact=pick)
check("a hire is narrated as joining the player here, not as the party setting out", told and "setting out" not in told[-1] and "Nobody leaves or goes anywhere" in told[-1], told[-1:] if told else "no narration")

# ---- her beats: her script comes back in as many paragraphs, as long, as she needs (f375: no count, no word cap)
spoke = []
ws.mentor_speak = lambda lines, beat, **k: spoke.append(k) or True
long_line = "One more thing. " + "word " * 72
ws.mentor_say(["A short line of hers here.", "Another line, with a bit more in it.", "A third one for the board.", long_line], beat="beat")
check("her beat is given no paragraph count and no word cap", spoke and "paragraphs" not in spoke[-1] and "max_words" not in spoke[-1], spoke[-1:])

# ---- a wolf has hide, a soldier armor
def fighter(fid, side, category=""):
    return combat.Fighter(id=fid, name=fid, side=side, level=5, attrs={a: 10 for a in combat.ATTRIBUTES}, hp=10 ** 5, max_hp=10 ** 5,
                          stamina=10 ** 5, max_stamina=10 ** 5, mana=100, max_mana=100, weapon_damage=10, weapon_attrs=["strength"], armor=50,
                          category=category, zone_id="z1", row="front")
wolf, guard, you = fighter("wolf", "enemy", "beast"), fighter("guard", "enemy", "hostile people"), fighter("you", "player")
check("what turns a blow is named for what the fighter is: hide, scales, armor", combat.cover(wolf) == "hide" and combat.cover(you) == "armor"
      and combat.cover(guard) == "armor" and combat.cover(fighter("d", "enemy", "dragon")) == "scales")
f = combat.Combat(fighters=[you, wolf], record=True)
MA.maneuver(f, you, wolf, combat.Move(id="v", name="Lance Volley", effect="damage", maneuver="sunder", tier="light", reach="melee", resource="stamina"), random.Random(1))
check("a sundering blow on a wolf cracks its hide, not its armor", any("hide cracks and splits" in s for s in f.story) and not any("armor" in s for s in f.story), f.story)

# ---- the narrator is told what an ability looks like; a power for outside a fight says so
c = ws.player.character
lance = c.actives[0].model_copy(update={"id": "lance_volley", "name": "Lance Volley", "description": "You deliver a rapid series of three precise strikes."})
calm = c.actives[0].model_copy(update={"id": "beast_command", "name": "Beast Command", "description": "You speak with animals and calm the wild.",
                                        "context": UseContext.OUT_OF_COMBAT})
c.actives = [lance, calm]
you.moves = [combat.Move(id="lance_volley", name="Lance Volley", effect="damage", tier="light", reach="melee", resource="stamina")]
cs = CombatScene.__new__(CombatScene)
cs.ws, cs.fight = ws, f
f.story = ["You use Lance Volley on the wolf, three strikes in one motion: every one lands [h1]"]
looks = cs.ability_looks()
check("the narrator is given the used ability's own description", looks == ["Lance Volley: You deliver a rapid series of three precise strikes."], looks)
req = cp.narrate_request("the Greywood", "morning", "I use Lance Volley", f.story, "copper lance", "hurt", ["the wolf, wounded"], 2, looks=looks)
check("...in the request, as what it looks like, never something thrown unless it says so", "WHAT THE PLAYER'S ABILITIES LOOK LIKE" in req and "three precise strikes" in req and "never as something thrown" in req)
away = cs.outside_ability(types.SimpleNamespace(kind="talk", ability="beast_command"), "I use beast command and tell the wolf to yield")
check("Beast Command in a fight is said to be for outside one, with what it does", "Beast Command works outside a fight" in away and "speak with animals" in away, away)
check("...and a fighting ability is not stopped", cs.outside_ability(types.SimpleNamespace(kind="ability", ability="lance_volley"), "I use lance volley") == "")

store.close()
shutil.rmtree("saves/playthrough1_test", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
