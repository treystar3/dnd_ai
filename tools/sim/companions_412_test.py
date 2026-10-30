"""(f412) What the f395 night's blind readers tripped over most, among the companions. A companion killed by a pirate was narrated as
killed by the player's own blade; the dead were never named again; Zurra was written Zorra, Zumra and Zerra; a woman who fought beside
the player 'grips their sword hilt' and 'lowers his blade'; and 'Zurra counts her coin on arriving, as if the road might have taken
some.' stood alone on its line 24 times, while some 200 passages after a fight opened on the silence rushing back."""
import io, contextlib, json, random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 4))
import ui.console as uc
NARR = []
uc.narrate = lambda t, *a, **k: NARR.append(str(t))
uc.panel = lambda name, data: False
from engine import combat, context, hygiene, names, quirks
from llm.contracts import Narration
from npc.traits import load_traits
from scenes.world import WorldScene
from scenes.combat_scene import CombatScene
from scenes import combat_prompts as cp, world_prompts as wp
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/companions_412_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("companions_412_test")
store.meta.seed = 7; store.meta.turn = 1; store.meta.minutes = 900; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(3))
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
odly = {"id": "h1", "name": "Odly Garth", "role": "fighter", "level": 2, "permanent": True, "rank": "F", "bond": 12, "pronoun": "she",
        "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "a sellsword with a dented shield"}
thav = {"id": "h2", "name": "Thavathiel Liaralor", "role": "mage", "level": 2, "permanent": True, "rank": "F", "bond": 12, "pronoun": "he",
        "hp_frac": 1.0, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "an elf who talks of ley lines"}
for i, m in enumerate((odly, thav)):
    quirks.roll(m, random.Random(i))
ws.player.party = [odly, thav]
ws.player.party_mode = "with"
ws.enter("parth")

# ---- 1. a companion's death is the foe's, and the dead are remembered
creature = world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 3, "normal", "e1", name="wolf 1")
foe.hp = foe.max_hp = 10 ** 6
ws.narrate_with = lambda *a, **k: None
sc = CombatScene.begin(ws, creature, [foe], "It is on you:")
ws.combat = sc
f = sc.fight
ally = next(a for a in f.fighters if a.side == "ally" and a.name.startswith("Thavathiel"))
ally.hp = 1
f.story.clear()
for _ in range(80):
    combat.apply_damage(f, foe, ally, 1.0, "bites", random.Random(_))
    if not ally.alive:
        break
check("a companion struck down: the fight keeps whose blow it was", f.felled_by.get(ally.id) == combat.who(foe), f.felled_by)
check("...and the story's fall line says so", any("falls to" in s and combat.who(foe) in s for s in f.story), f.story[-3:])
svc_cls = type(ws.party_service)                           # the dice say dead this time
real_decide = svc_cls.decide_down
svc_cls.decide_down = lambda self, m, rng, in_fight=True: (m.__setitem__("down_fate", "dead"), "dead")[1]
f.story.clear()
killed = sc.hires_down()
svc_cls.decide_down = real_decide
check("his death is told as the foe's, and never the player's", killed and any(f"from {combat.who(foe)}" in s and "not by you" in s for s in f.story), f.story)
check("the narrator is told a companion never falls to the player's blow", "never to the player's or another companion's" in cp.NARRATE_SYSTEM
      if hasattr(cp, "NARRATE_SYSTEM") else any("never to the player's or another companion's" in getattr(cp, n) for n in dir(cp)
                                                  if isinstance(getattr(cp, n), str)))
check("everyone who travelled with him keeps who fell, where, and by whose hand",
      odly.get("mourns") and odly["mourns"][0]["name"] == "Thavathiel Liaralor" and combat.who(foe) in odly["mourns"][0]["how"], odly.get("mourns"))
check("...and not himself", not thav.get("mourns"))
ws.combat = None
store.save_combat(None)
ws.player.party = [odly]

# days later, at rest: the dead come up in the companions' talk
ws.store.meta.minutes += 3 * 1440
picked = None
for seed in range(120):
    kind, text, about = ws.banter_hook([odly], "rest", random.Random(seed))
    if kind == "remembered":
        picked = text
        break
check("days later, the one who fell comes up in what they talk about", picked and "Thavathiel Liaralor" in picked and "3 days ago" in picked, picked)
check("...and when it has, not again by her that day", not context.due(odly, f"mourn:{thav['id']}", ws.minutes))
check("...and the talk is told to name him", ws.__dict__.get("_remembered") == "Thavathiel Liaralor")
ws.store.meta.minutes += 2 * 1440
odly["raised"] = {}
where = [ws.banter_hook([odly], "travel", random.Random(s))[0] for s in range(200)]
ws.player.location, was = odly["mourns"][0]["place"], ws.player.location
odly["raised"] = {}
there = []
for s in range(200):
    odly["raised"] = {}
    there.append(ws.banter_hook([odly], "travel", random.Random(s))[0])
check("...more often where he fell", there.count("remembered") > where.count("remembered"), (there.count("remembered"), where.count("remembered")))
ws.player.location = was

# ---- 2. a name it was told, written wrong, is written right
n = Narration(text="Zorra laughs, and Liaror shrugs. Lanterns sway over the Wend.")
names.mend_answer(n, "WITH THE PLAYER: Zurra Barruk (she), Thavathiel Liaralor (he). The river Wend runs by.")
check("'Zorra' for Zurra and 'Liaror' for Liaralor are mended; ordinary words are not", n.text == "Zurra laughs, and Liaralor shrugs. Lanterns sway over the Wend.", n.text)
n = Narration(text="Wind tugs at the reeds. Store the rope, Odly says.")
names.mend_answer(n, "PLACE: the banks of the Wend. WITH THE PLAYER: Odly Garth, Deth Stone.")
check("...an ordinary word one letter off a name is left alone ('Wind' and the Wend, 'Store' and Stone)", n.text == "Wind tugs at the reeds. Store the rope, Odly says.", n.text)
from llm import gateway
real_chat = gateway._client.chat
gateway._client.chat = lambda **kw: types.SimpleNamespace(done_reason="stop", prompt_eval_count=0, eval_count=0,
                                                         message=types.SimpleNamespace(content=json.dumps({"text": "Oddy grins at you."})))
out = gateway.generate("narrate", "You narrate.", "WITH THE PLAYER: Odly Garth (she). THE PLAYER: you.", Narration)
gateway._client.chat = real_chat
check("...by the gateway, on every answer it passes", out.text == "Odly grins at you.", out.text)

# ---- 3. pronouns: a gesture's 'their', and 'his blade' for a she
check("a companion's gesture is said with her own pronoun", quirks.shown("Ready.", "grips their sword hilt", "Odly Garth", "she")
      == "(Odly grips her sword hilt.)\nReady.", quirks.shown("Ready.", "grips their sword hilt", "Odly Garth", "she"))
ws.player.party = [odly, dict(thav, id="h3")]
ws.name_ids()
check("'Odly lowers his blade' on the way to the screen is her blade", hygiene.clean("Odly lowers his blade and steps back.") == "Odly lowers her blade and steps back.")
check("...'steadies herself' for a he is himself", hygiene.clean("Thavathiel steadies herself.") == "Thavathiel steadies himself.")
check("...and someone else's is left alone", hygiene.clean("Odly was his sister.") == "Odly was his sister."
      and hygiene.clean("Thavathiel pushes her back.") == "Thavathiel pushes her back.")
ws.player.party = [odly]

# ---- 4. a habit is folded into the passage of its moment, never a line of its own
odly["quirks"]["habit"] = "counts_coin"
odly["quirks"].pop("habit_day", None)
asked = []
import scenes.world as W
real_fresh = W.fresh
W.fresh = lambda task, system, request, *a, **k: (asked.append(request), Narration(text="You come into the square."))[1]
ws._quirk_loc = "south_fields"
NARR.clear()
ws._narrate_now("You arrive.")
check("arriving: her habit is handed to the arrival's passage, to tell in its own words", asked and wp.HABITS_HEAD in asked[-1]
      and "counts her coin" in asked[-1], asked[-1][-600:] if asked else "")
ws.quirk_tick()
check("...and never shown as a line of its own", not any("counts her coin" in t for t in NARR), NARR)
asked.clear()
ws._narrate_now("You look around.")
check("...once: the next passage in the same place has none", asked and wp.HABITS_HEAD not in asked[-1])
odly["quirks"]["habit"] = "boots_off"
odly["quirks"].pop("habit_day", None)
ws.habits("rest")
asked.clear()
ws._narrate_now("The player rests.")
check("resting: the rest's passage tells it", asked and "boots off" in asked[-1])
W.fresh = real_fresh

# ---- 5. the passage after a fight begins somewhere new each time
check("the after-fight voice no longer asks for the silence and the breathing", "Describe the silence returning" not in cp.AFTERMATH_SYSTEM
      and "OPEN ON" in cp.AFTERMATH_SYSTEM)
sc2 = CombatScene.__new__(CombatScene)
sc2.ws, sc2.rng = ws, random.Random(5)
opens = [sc2.aftermath_opening().split("\n")[0] for _ in range(12)]
check("it opens where the engine says, never where one of the last two did",
      all(opens[i] not in opens[max(0, i - 2):i] for i in range(len(opens))), opens)
ws._after_starts = ["Silence rushes back into the", "The heavy thud of the"]
check("...and is told how the last ones began", "DO NOT BEGIN LIKE THESE" in sc2.aftermath_opening() and "Silence rushes back" in sc2.aftermath_opening())
ws.player.party = []
check("...an opening on a companion only with a party along", not any("companion" in sc2.aftermath_opening() for _ in range(30)))

store.close()
shutil.rmtree("saves/companions_412_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
