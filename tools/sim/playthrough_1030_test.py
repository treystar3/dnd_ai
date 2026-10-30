"""(f404) What a fire mage's first hour showed: a search for someone by name finds them (it was a search for wild game, and the narrator
made up a woman to ask); a model's note to itself in brackets never reaches the page or the narration it remembers; the after-fight
passage keeps the bodies whole (wolves burnt to ash were then skinned for three hides) and lets the fight's echoes fade; a fight whose
foe a scripted passage already brought on is not narrated arriving a second time (Maren's troll came out of the trees twice)."""
import io, contextlib, shutil, sys, random
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("mage", 5))
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.panel = lambda name, data: False
from engine import hygiene
from npc.life import populate_place
from npc.traits import load_traits
from scenes.world import WorldScene
from scenes import combat_prompts as cp
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
from llm.contracts import ActionIntent

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- a note in brackets
leak = "crimson sprays from the meat [h4_damage_implied/hidden_by_rules_but_noted_in_events? No wait, use events only.]. One snaps [h2]."
from llm.contracts import Narration
check("a note to itself in brackets is found in an answer, so the model is asked again", hygiene.problem("combat_narrate", Narration(text=leak))[0] == "note")
check("...a blow's tag is not a note", hygiene.problem("combat_narrate", Narration(text="One snaps [h2]. Another (h3).")) == ("", ""))
check("...and one that slips through is cut from the story, the tags kept", hygiene.unnote(leak) == "crimson sprays from the meat. One snaps [h2].",
      hygiene.unnote(leak))
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    uc.narrate("The wolf falls [h4_damage_implied? No wait.] and lies still.")
check("...never on the screen", "No wait" not in buf.getvalue() and "lies still" in buf.getvalue(), buf.getvalue())

# ---- the narrators' rules
check("a round's narrator keeps a fallen foe's body", "nothing turns a body to ash or dust" in cp.NARRATE_SYSTEM)
check("the after-fight narrator keeps to the bodies and what the fight called up", "THE BODIES" in cp.AFTERMATH_SYSTEM
      and "WHAT THE FIGHT CALLED UP" in cp.AFTERMATH_SYSTEM)

# ---- a scene
shutil.rmtree("saves/playthrough_1030_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("playthrough_1030_test")
store.meta.seed = 5; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, spec = simlib.make_character("mage", random.Random(2))
store.save_player(PlayerState(character=char, location="trading_square"))
cat = load_traits()
for pid in ("trading_square", "parth", "guild_house"):
    try: populate_place(store, world, pid, cat)
    except Exception: pass
ws = WorldScene(store, world, cat, store.load_player())
ws.player.mentor["never"] = True
asked = []
ws.narrate = lambda req, text="", *a, **k: asked.append(req)
who = None
for pid in ("parth", "trading_square", "guild_house"):
    ws.enter(pid)
    who = next((n for n in ws.present if not n.name_known_to_player and len(n.name.split()) >= 2), None)
    if who is not None:
        break
check("(the square has someone the player does not know by name)", who is not None, [n.name for n in ws.present])
if who is not None:
    who.heard_of = {"by": "Belney", "day": 0, "line": f"{who.name} works here."}
    store.save_npc(who)
    asked.clear()
    ws.on_search(ActionIntent(kind="search", seek=who.name), f"I look for {who.name}")
    check("looking for someone by name who is here finds them", asked and who.name in asked[-1] and "picking" in asked[-1], asked[-1:])
    check("...and they are known by that name now", store.load_npc(who.id).name_known_to_player and who.name_known_to_player)
    check("...not a search for wild game", not any("no wild game" in a for a in asked))
away = next((store.load_npc(i) for i in store.list_npcs() if store.load_npc(i).location not in (ws.player.location, "")
             and store.load_npc(i).id not in {n.id for n in ws.present}), None)
if away is not None:
    away.heard_of = {"by": "Belney", "day": 0, "line": f"{away.name} works elsewhere."}
    store.save_npc(away)
    NOTES.clear(); asked.clear(); ws.halted = False
    ws.on_search(ActionIntent(kind="search", seek=away.name), f"I look for {away.name}")
    check("someone known to be elsewhere: the player is told where", any(f"{away.name} isn't here" in n and ws.where_name(away.location) in n
                                                                      for n in NOTES) and not asked, (NOTES, asked))

# ---- the after-fight facts
from scenes.combat_scene import CombatScene
from engine import combat
sc = CombatScene.__new__(CombatScene)
me = combat.fighter_from_character(char)
me.counters["echoes"] = 2
sc.fight = combat.Combat(fighters=[me], place="x", conditions=[])
facts = sc.aftermath_facts([object()], 3)
check("the after-fight passage is told the bodies lie whole, and can be skinned", "THE BODIES" in facts and "skinned" in facts, facts)
check("...and that the kills' echoes fade with the fight", "echoes the kills left fade" in facts and not me.counters.get("echoes"), facts)
check("...no echoes, nothing said of them; no skinning where none can be done", "CALLED UP" not in sc.aftermath_facts([object()], 0)
      and "skinned" not in sc.aftermath_facts([object()], 0))

# ---- a scripted entrance is not narrated twice
starts = []
ws.narrate_with = lambda system, *a, **k: starts.append(system)
creature = world.bestiary["wolf"]
foe = combat.fighter_from_creature(creature, 1, "normal", "e0", name="wolf 1")
told = "Something comes out of the treeline, taller than the lowest branches."
scene = CombatScene.begin(ws, creature, [foe], "It is on you:", told=told)
check("a fight a scripted passage brought on is not narrated arriving again", cp.START_SYSTEM not in starts, len(starts))
check("...the scripted passage is what the fight remembers as its opening", ws.recent_narration and ws.recent_narration[-1] == told)
ws.combat = None
store.close()
shutil.rmtree("saves/playthrough_1030_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
