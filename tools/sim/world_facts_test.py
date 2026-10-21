"""Character creation knows what exists in Rivia: no firearms, a concept that needs them is translated, and the Goddess says so."""
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
check("no hard word filter was added to the interpretation", not any("gun" in str(v) for v in ClassInterpretation.model_fields.values()))

heard = []
s = ThresholdScene()
s.speak = lambda event: heard.append(event)
s.concept = "I want to be a hunter with a gun"
import character.creation as cr
cr.interpret_concept = lambda c: ClassInterpretation(archetype=Archetype.ROGUE, custom_class="Crossbow Hunter", combat_identity="crossbow marksman",
                                                    themes=["Marksmanship"], summary="A patient hunter.", adapted="Firearms do not exist here; I read this as a crossbow marksman.")
s.read_class()
check("the Goddess is told to say that the thing asked for has no place in Rivia", s.step == Step.CONFIRM_CLASS and "no place in Rivia" in heard[-1] and "Firearms do not exist" in heard[-1], heard[-1:])
heard.clear()
cr.interpret_concept = lambda c: ClassInterpretation(archetype=Archetype.ROGUE, custom_class="Shadow", combat_identity="daggers", themes=["Stealth"], summary="Quiet.")
s.read_class()
check("an ordinary concept gets no such note", "no place in Rivia" not in heard[-1])
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
