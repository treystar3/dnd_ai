"""Character creation knows what exists in Meravia: no firearms, a concept that needs them is translated, and the Goddess says so."""
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("rogue", 3))
import ui.console as uc
uc.note = lambda *a, **k: None
uc.say = lambda *a, **k: None
uc.wait = lambda *a, **k: None
from llm import prompts
from character import kit
from llm.contracts import ClassInterpretation
from core.models import Archetype
from scenes.goddess import ThresholdScene, Step
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

for name in ("CLASSIFY_SYSTEM", "ACTIVES_SYSTEM", "SLOTS_SYSTEM", "PASSIVES_SYSTEM", "MECH_PASSIVES_SYSTEM", "STAT_PASSIVES_SYSTEM"):
    text = getattr(prompts, name)
    check(f"{name} is told what the world has and lacks", "no guns, firearms" in text and "Alchemy, clockwork" in text and "crossbow" in text)
check("the starting-weapon prompt is told too", "no guns, firearms" in kit.KIT_SYSTEM)
check("the class reading is asked to say what it changed", "adapted" in prompts.CLASSIFY_SYSTEM)
from llm.contracts import ClassInterpretation as _CI
_b = dict(archetype="warrior", custom_class="x", combat_identity="y", themes=["a"], summary="s")
check("'none' written for nothing adapted is empty, so the line stays hidden", all(_CI(**_b, adapted=v).adapted == "" for v in ("none", "None.", "N/A", "\"none\"", "none\",  ", " ,\"", "")))
check("a real adaptation is kept", _CI(**_b, adapted="asked for a gun; made a crossbow").adapted == "asked for a gun; made a crossbow")
check("clockwork and alchemy stay allowed", "do exist" in prompts.WORLD_FACTS)
# (f342) a tester's archer was told they had no arrows, then spent five turns trying to buy some: every speaker now knows bows need none
check("the world rules say bows need no arrows and nobody sells them", "need no arrows" in prompts.WORLD_RULES and "nobody sells arrows" in prompts.WORLD_RULES)
from scenes import world_prompts, combat_prompts, party_prompts
from npc import prompts as npc_prompts
from engine import mentor
for label, text in (("the narrator", world_prompts.NARRATOR_SYSTEM), ("the dialogue frame", world_prompts.DIALOGUE_SYSTEM), ("the fight narrator", combat_prompts.NARRATE_SYSTEM),
                    ("townsfolk", npc_prompts.CONVERSATION_SYSTEM), ("hires", party_prompts.TALK_SYSTEM), ("Maren chatting", mentor.chat_system()),
                    ("Maren's persona, under her scripted lines too", mentor.chat_system_persona())):
    check(f"{label} is told the world's rules", "need no arrows" in text and "no guns, firearms" in text)
check("the narrator is told the gear is exactly what it is given", "never name something they lack" in world_prompts.NARRATOR_SYSTEM)
check("creation still gets the concept rule on top", "translate it to the closest thing" in prompts.WORLD_FACTS and "translate it" not in prompts.WORLD_RULES)
check("no hard word filter was added to the interpretation", not any("gun" in str(v) for v in ClassInterpretation.model_fields.values()))

heard = []
s = ThresholdScene()
s.speak = lambda event: heard.append(event)
s.concept = "I want to be a hunter with a gun"
import character.creation as cr
cr.interpret_concept = lambda c: ClassInterpretation(archetype=Archetype.ROGUE, custom_class="Crossbow Hunter", combat_identity="crossbow marksman",
                                                    themes=["Marksmanship"], summary="A patient hunter.", adapted="Firearms do not exist here; I read this as a crossbow marksman.")
s.read_class()
check("the Goddess is told to say that the thing asked for has no place in Meravia", s.step == Step.CONFIRM_CLASS and "no place in Meravia" in heard[-1] and "Firearms do not exist" in heard[-1], heard[-1:])
heard.clear()
cr.interpret_concept = lambda c: ClassInterpretation(archetype=Archetype.ROGUE, custom_class="Shadow", combat_identity="daggers", themes=["Stealth"], summary="Quiet.")
s.read_class()
check("an ordinary concept gets no such note", "no place in Meravia" not in heard[-1])
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
