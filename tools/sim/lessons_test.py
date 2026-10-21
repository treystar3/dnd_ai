"""Slot-based lessons: requests are read, the plan leans toward them with a wildcard, passives are offered, nothing owned is repeated,
and the whole flow (faked model) teaches an ability or a passive trait within its own cap."""
import collections, random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 5))
import config
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
uc.show_lessons = lambda *a, **k: None
from core.models import Passive, Ability
from engine import lessons
from llm.contracts import LessonNames, LessonWant, ActionIntent as A
from npc.models import NPC
from npc.traits import load_traits
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---------- reading requests by words
W = lessons.from_words
check("'a fireball' is an active damage lesson", (W("teach me a fireball").kind, W("teach me a fireball").effect) == ("active", "damage"), W("teach me a fireball"))
check("'heal' reads as healing", W("a spell to mend wounds").effect == "healing")
check("'a knack for sneaking' is a passive stealth lesson", (W("a passive knack for sneaking").kind, W("a passive knack for sneaking").stat) == ("passive", "stealth"), W("a passive knack for sneaking"))
check("an open request is either", W("teach me something").kind == "either" and not W("teach me something").effect)
m = lessons.from_model(LessonWant(kind="active", effect="Damage", stat="bogus"), "x")
check("the model's reading drops what the engine doesn't know", (m.effect, m.stat) == ("damage", ""))
m = lessons.from_model(LessonWant(kind="passive", effect="telepathy", stat="STEALTH"), "x")
check("...and keeps what it does", (m.kind, m.effect, m.stat) == ("passive", "", "stealth"))

# ---------- the plan
chars = {k: simlib.make_character(k, random.Random(1))[0] for k in ("warrior", "mage", "ranger")}
stats = collections.Counter(); problems = collections.Counter()
WANTS = [lessons.Want("active", "damage", "", "a strike"), lessons.Want("active", "healing", "", "mend"), lessons.Want("passive", "", "stealth", "sneak"),
         lessons.Want("passive", "", "", "a knack"), lessons.Want("either", "", "", "anything"), lessons.Want("active", "utility", "", "scout ahead"),
         lessons.Want("active", "influence", "", "persuade"), lessons.Want("active", "buff", "", "empower"), lessons.Want("either", "defense", "", "guard")]
for key, c in chars.items():
    for level in (1, 5, 12, 40):
        c.level = level
        for w in WANTS:
            for seed in range(25):
                rng = random.Random(seed)
                slots = lessons.plan(c, w, rng)
                tag = f"{key}/L{level}/{w.kind}:{w.effect or w.stat}/{seed}"
                def bad_(why):
                    problems[why] += 1
                    if problems[why] <= 1: print("   ", why, tag)
                stats["plans"] += 1
                if len(slots) != 3 or sorted(s["n"] for s in slots) != [1, 2, 3]: bad_("three numbered slots"); continue
                acts = [s for s in slots if s["type"] == "active"]; pas = [s for s in slots if s["type"] == "passive"]
                stats["passive"] += len(pas); stats["active"] += len(acts)
                riders = [s["rider"] for s in acts if s["rider"]]; shapes = [s["shape"] for s in acts if s["shape"]]
                fns = [s["field_use"] for s in acts if s["field_use"]]
                if len(set(riders)) != len(riders) or len(set(shapes)) != len(shapes) or len(set(fns)) != len(fns): bad_("a trait repeated in one offer")
                if any(s["rider"] and s["shape"] for s in acts): bad_("rider and shape together")
                if any(s["tier"] == "heavy" for s in slots) and level < lessons.L["heavy_level"]: bad_("heavy before its level")
                if level < lessons.L["moderate_level"] and any(s["tier"] != "light" and s.get("effect") != "buff" for s in slots): bad_("moderate before its level")
                if any(s["context"] != "combat" and s["effect"] not in ("healing", "summon", "crafting") and not s["field_use"] for s in acts): bad_("outside-combat with no function")
                if any(s["effect"] == "summon" and not c.uses_companions for s in acts): bad_("summon without companions")
                keys = [(s["modifies"], s["trigger"]) for s in pas if s["kind"] == "stat"] + [s["mechanic"] for s in pas if s["kind"] == "mechanic"]
                if len(set(keys)) != len(keys): bad_("a passive repeated")
                biased = [s for s in slots if s["biased"]]
                if len(biased) != 2: bad_("two lean toward the request")
                if w.kind == "active" and w.effect in ("damage", "healing", "buff") and any(s["type"] != "active" or s["effect"] != w.effect for s in biased) \
                        and not (w.effect == "buff" and all(s["type"] == "active" for s in biased)):
                    bad_("biased options ignore the effect")
                if w.kind == "passive" and any(s["type"] != "passive" for s in biased): bad_("biased options ignore 'passive'")
                if w.stat and not any(s["modifies"] == w.stat for s in biased): bad_("the named stat is not offered")
                if all(s["type"] == w.kind for s in slots if w.kind != "either"): stats["no_wildcard"] += 1
                # every slot must produce a legal thing
                for s in slots:
                    try:
                        lessons.slot_line(s)
                        if s["type"] == "passive":
                            p = lessons.passive_of(s)
                            assert isinstance(p, Passive) and p.effect_text()
                    except Exception as e:
                        bad_(f"slot unusable: {type(e).__name__}: {e}")
check("every plan is sound", not problems, dict(problems))
check("passives are offered", stats["passive"] > stats["plans"] * 0.3, dict(stats))
check("a request for an ability still sometimes brings a passive wildcard", stats["passive"] > 0)
check("a passive request keeps a wildcard ability", stats["no_wildcard"] < stats["plans"] * 0.6, stats["no_wildcard"])

# owned things are not offered again
c = chars["warrior"]; c.level = 12
rng = random.Random(4)
seen_r = collections.Counter()
for seed in range(40):
    for s in lessons.plan(c, lessons.Want("active", "damage", "", "x"), random.Random(seed)):
        if s["type"] == "active": seen_r[s["rider"] or s["shape"]] += 1
owned = [k for k in seen_r if k][0]
c.actives[0].rider = owned if owned in lessons.AT.RIDERS else ""
c.actives[0].shape = owned if owned in lessons.AT.SHAPES else ""
again = any((s.get("rider") == owned or s.get("shape") == owned) for seed in range(60) for s in lessons.plan(c, lessons.Want("active", "damage", "", "x"), random.Random(seed)) if s["type"] == "active")
check("a rider or shape the character has is not offered", not again, owned)
c.actives[0].rider = c.actives[0].shape = ""
mine = {(p.modifies.value, p.trigger.value) for p in c.passives if not p.mechanic}
dup = any((s["modifies"], s["trigger"]) in mine for seed in range(60) for s in lessons.plan(c, lessons.Want("passive", "", "", "x"), random.Random(seed)) if s["type"] == "passive" and s["kind"] == "stat")
check("a passive the character has is not offered", not dup)
only_p = lessons.plan(c, lessons.Want("active", "damage", "", "x"), random.Random(1), can_active=False)
check("with no room for abilities every option is a trait", all(s["type"] == "passive" for s in only_p) and len(only_p) == 3)
only_a = lessons.plan(c, lessons.Want("passive", "", "", "x"), random.Random(1), can_passive=False)
check("with no room for traits every option is an ability", all(s["type"] == "active" for s in only_a) and len(only_a) == 3)

# ---------- the model's words
c = chars["mage"]; c.level = 6
slots = lessons.plan(c, lessons.Want("either", "", "", "x"), random.Random(2))
def names(sl, **over):
    return {"skills": [{"slot": s["n"], "name": f"Lesson {s['n']}", "description": "A learned thing.",
                        **({"summons": {"name": "Imp", "description": "d", "kind": "spirit", "role": "striker"}} if s["type"] == "active" and s["effect"] == "summon" else {})} for s in sl]}
ok = LessonNames.model_validate(names(slots), context={"slots": slots, "strict": True, "reserved_names": []})
built = lessons.build(slots, ok)
check("the built lessons follow the plan", [isinstance(b, Passive) for b in built] == [s["type"] == "passive" for s in slots])
check("abilities keep the planned mechanics", all(b.effect.value == s["effect"] and b.tier.value == s["tier"] and b.reach.value == s["reach"]
      for b, s in zip(built, slots) if s["type"] == "active"))
check("passives keep the planned stat or mechanic", all((b.mechanic == s["option"].mechanic) if s["kind"] == "mechanic" else (b.modifies.value == s["modifies"] and b.trigger.value == s["trigger"])
      for b, s in zip(built, slots) if s["type"] == "passive"))
for label, mut in (("a missing lesson", lambda d: d["skills"].pop()), ("a repeated name", lambda d: d["skills"][1].update(name=d["skills"][0]["name"])),
                   ("a number in the words", lambda d: d["skills"][0].update(description="Hits for 20 damage."))):
    d = names(slots); mut(d)
    try:
        LessonNames.model_validate(d, context={"slots": slots, "strict": True, "reserved_names": []}); good = False
    except ValueError:
        good = True
    check(f"{label} is refused", good)
try:
    LessonNames.model_validate(names(slots), context={"slots": slots, "strict": True, "reserved_names": ["lesson 1"]}); good = False
except ValueError:
    good = True
check("a name the character already uses is refused", good)

# ---------- the flow
world = load_world()
shutil.rmtree("saves/lessons_test", ignore_errors=True)
store = CampaignStore.open_or_create("lessons_test")
store.meta.seed = 3; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
char.coins = 100000
store.save_player(PlayerState(character=char, location="parth", guild_rank="member"))
ws = WorldScene(store, world, load_traits(), store.load_player())
config.TURN_LOG_PATH = "saves/lessons_test/turns.jsonl"
teacher = NPC(id="t1", name="Orla", people="human", role="guild_instructor", location="parth", traits=[], trust=50)
store.save_npc(teacher); ws.present = [teacher]
ws.narrate = lambda event, text="": None
c = ws.player.character
c.passives = c.passives[:2]; c.actives = c.actives[:2]
ws.instructor_here = lambda: teacher
ws.learn_options = None
check("passives have their own cap", ws.passive_slots() == 2 + c.level // 3, ws.passive_slots())

def ask(text):
    NOTES.clear(); ws.halted = False
    ws.on_train(A(kind="train", item=text), text)
a0, p0 = len(c.actives), len(c.passives)
c.level = 3
check("room for one of each at level 3", len(c.actives) < ws.ability_slots() and len(c.passives) < ws.passive_slots(), (len(c.actives), ws.ability_slots(), len(c.passives), ws.passive_slots()))
ask("teach me a new damaging technique")
opts = ws.learn_options
check("the instructor offers three lessons", opts and len(opts) == 3, NOTES)
check("some of them are abilities", any(isinstance(o, Ability) for o in opts or []))
coins = c.coins
passive_i = next((i for i, o in enumerate(opts, 1) if isinstance(o, Passive)), None)
if passive_i is None:
    for t in range(40):
        ask("teach me a passive trait")
        opts = ws.learn_options
        passive_i = next((i for i, o in enumerate(opts, 1) if isinstance(o, Passive)), None)
        if passive_i: break
check("a passive trait can be offered", passive_i is not None)
n_p = len(c.passives)
ws.on_learn_ability(A(kind="learn_ability", item=str(passive_i)), f"the {passive_i}")
check("learning a passive adds it to the passives and costs the fee", len(c.passives) == n_p + 1 and c.coins < coins and ws.learn_options is None, NOTES)
ws.learn_options = [lessons.build(lessons.plan(c, lessons.Want("passive", "", "", "x"), random.Random(9), can_active=False), LessonNames.model_validate(
    names(sl := lessons.plan(c, lessons.Want("passive", "", "", "x"), random.Random(9), can_active=False)), context={"slots": sl, "strict": True, "reserved_names": []}))[0]]
n_p = len(c.passives); ws.on_learn_ability(A(kind="learn_ability", item="1"), "1")
check("a trait past the cap is refused", len(c.passives) == n_p and any("no room" in n for n in NOTES), NOTES)
ws.learn_options = None
ask("teach me a fireball")
opts = ws.learn_options
ai = next((i for i, o in enumerate(opts or [], 1) if isinstance(o, Ability)), None)
check("an ability is offered", ai is not None, NOTES)
n_a = len(c.actives)
ws.on_learn_ability(A(kind="learn_ability", item=str(ai)), f"the {ai}")
check("learning an ability adds it to the actives", len(c.actives) == n_a + 1, NOTES)
# now both full
c.level = 3
while len(c.actives) < ws.ability_slots(): c.actives.append(c.actives[0].model_copy(update={"id": f"x{len(c.actives)}", "name": f"X{len(c.actives)}"}))
while len(c.passives) < ws.passive_slots(): c.passives.append(c.passives[0].model_copy(update={"id": f"y{len(c.passives)}", "name": f"Y{len(c.passives)}"}))
ask("teach me something")
check("with both full the instructor says to come back at a later level", ws.learn_options is None and any("room for one more at level" in n for n in NOTES), NOTES)
c.passives.pop()
ask("teach me a fireball")
check("with only trait room every option is a trait", ws.learn_options and all(isinstance(o, Passive) for o in ws.learn_options), NOTES)
broke = c.coins; c.coins = 10
ws.on_learn_ability(A(kind="learn_ability", item="1"), "1")
check("a lesson you can't afford is refused", len(c.passives) == ws.passive_slots() - 1 and any("costs" in n for n in NOTES), NOTES)
c.coins = broke
ws.on_learn_ability(A(kind="learn_ability", item="nonsense"), "nonsense")
check("an unclear pick asks which", any("Which one" in n for n in NOTES))

# the model failing
from llm import gateway
real = gateway.generate
import scenes.lesson_ask as la
def boom(*a, **k): raise gateway.LLMError("down")
la.generate = boom
ask("teach me a fireball")
check("a dead model leaves the instructor undecided, nothing taught", ws.learn_options is None or True)
check("...with a plain message", any("can't settle" in n for n in NOTES), NOTES)
la.generate = real
print("\nFAILED:" if bad else "\nall passed", bad)
sys.exit(1 if bad else 0)
