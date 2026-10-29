"""(f388) Character creation as pages, and who the player was.
- Before the goddess speaks the player chooses a people, he, she or they, and a look; the engine makes one sentence of it that every
  speaker and the narrator are given from then on (engine/look.py, data/rules/look.yaml).
- In the window each step is a page (console.creation): cards for the abilities and the traits with filters, the attributes shaped with
  buttons and the numbers they give, her last words over it all. The page answers with hidden lines read without the model.
- The page's own sums (the sentence, the pools) are the engine's: run here with node against the Python, so they cannot drift apart."""
import json, random, re, shutil, subprocess, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
import ui.console as uc
NOTES, PAGES = [], []
for f in ("narrate", "say", "npc_says", "dialogue", "ledger", "wait"):
    setattr(uc, f, lambda *a, **k: None)
uc.note = lambda m, *a, **k: NOTES.append(str(m))
from pathlib import Path
import character.creation as cc
from core.models import Archetype, Attributes
from engine import look, pools, truth
from llm.contracts import ClassInterpretation
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()

# ---- the sentence
check("every people of the world has a look, and the table names no other", look.problems(world) == [], look.problems(world))
dwarf = {"people": "dwarf", "pronoun": "she", "look": {"build": "stocky", "age": "grown", "hair": "copper"}, "flags": ["braided"],
         "extra": "a burn scar along the jaw, soot never quite washes from her hands"}
check("the mock-up's dwarf, as the world sees her", look.describe(dwarf) ==
      "A stocky dwarf woman with braided copper hair and a burn scar along the jaw; soot never quite washes from her hands.", look.describe(dwarf))
check("a human is the plain word, and no hair is a shaved head", look.describe({"people": "human", "pronoun": "he", "look": {"build": "towering", "age": "old", "hair": "none"}})
      == "A towering old man with a shaved head.")
check("they, among a people, needs no noun; a dragonborn has scales, not hair",
      look.describe({"people": "dragonborn", "pronoun": "they", "look": {"build": "broad", "age": "young", "scales": "red"}}) == "A broad young dragonborn with red scales.")
check("a genasi carries an element as well", "water-touched genasi" in look.describe({"people": "genasi", "pronoun": "she", "look": {"element": "water"}}))
odd = look.clean({"people": "vampire", "pronoun": "it", "look": {"build": "enormous", "hair": "<script>"}, "flags": ["braided", "winged"], "extra": "x" * 400})
check("anything unknown falls back to what is there, and 'anything else' is kept short", odd["people"] == "human" and odd["pronoun"] == "they"
      and odd["look"]["build"] == look.L["axes"]["build"]["default"] and odd["flags"] == ["braided"] and len(odd["extra"]) <= look.L["extra_most"], odd)
typed = look.from_text("Half-elf woman, young, blond braided hair, a lute on her back always")
check("a typed answer is read for its choices, and the rest is 'anything else'", typed["people"] == "half_elf" and typed["pronoun"] == "she"
      and typed["look"]["hair"] == "blond" and typed["flags"] == ["braided"] and typed["extra"] == "a lute on her back always", typed)

# ---- the page's own sums are the engine's
JS = Path("ui/gui/web/app.js").read_text()
sentence_js = JS[JS.index("// LOOK-SENTENCE-BEGIN"):JS.index("// LOOK-SENTENCE-END")]
pools_js = re.search(r"function crPools\(b, v\) \{.*?\n\}\n", JS, re.S).group(0)
page = look.page()
samples = [look.surprise(random.Random(k)) for k in range(40)] + [look.clean(dwarf), typed]
for s_, k in zip(samples, range(len(samples))):
    if k % 3 == 0:
        s_["extra"] = random.Random(k).choice(["a burn scar along the jaw, soot on her hands", "eyes like river glass", "one ear torn", "an old oath tattooed, faded"])
def node(code: str):
    r = subprocess.run(["node", "-e", code], capture_output=True, text=True, timeout=60)
    return r.stdout.strip() or r.stderr.strip()
have_node = shutil.which("node") is not None
if have_node:
    out = node(sentence_js + f"\nconst page = {json.dumps(page)};\nconst xs = {json.dumps(samples)};\nconsole.log(JSON.stringify(xs.map((c) => lookSentence(page, c))));")
    got = json.loads(out) if out.startswith("[") else out
    want = [look.describe(s_) for s_ in samples]
    check("the page's 'how the world sees you' is the engine's sentence, every time", got == want,
          next(((a, b) for a, b in zip(got, want) if a != b), got) if isinstance(got, list) else got)

# ---- the creation scene, as pages
interp = ClassInterpretation(archetype=Archetype.WARRIOR, custom_class="Ironbound Bulwark", combat_identity="Heavy hammer and shield", themes=["Smithing"],
                             summary="A smith who stands in front of her friends.", primary_attributes=["strength", "constitution"], families=["guardian", "warrior"])
READ = []
cc.interpret_concept = lambda concept, who="": (READ.append(who), interp)[1]
pool = []
for k in ("warrior", "priest", "ranger", "mage", "bard"):
    pool += simlib.make_character(k, random.Random(1))[0].actives
seen_names = set()
offered = [a for a in pool if not (a.name in seen_names or seen_names.add(a.name))][:15]
cc.generate_actives = lambda i: offered
_gp = cc.generate_passives
cc.generate_passives = lambda i, actives, rng=None: _gp(i, actives, random.Random(2))
SAVED = []
cc.save_character = lambda c, path=None: (SAVED.append(c), Path("/tmp/creation_page_test.json"))[1]
uc.creation = lambda d: (PAGES.append(d), True)[1]
uc.creation_done = lambda: PAGES.append("done")
answers = ["create:who " + json.dumps(dwarf), "create:name Brenna Ashforge", "create:calling a smith who fights with a hammer", "create:confirm",
           "create:picks 1 4 6", "create:picks 1 2 3"]
def ask(main=False, menu=False):
    if answers:
        return answers.pop(0)
    body = next((p["body"] for p in reversed(PAGES) if isinstance(p, dict) and p.get("body")), None)
    return "create:stats " + json.dumps(body["suggested"]) if body else "#menu"
uc.ask = ask
from scenes.goddess import ThresholdScene, Step
scene = ThresholdScene()
made = scene.run()
steps = [p["step"] if isinstance(p, dict) else p for p in PAGES]
check("each step is a page, in order, and the pages close at the end",
      [s_ for i, s_ in enumerate(steps) if i == 0 or steps[i - 1] != s_] == ["who", "name", "concept", "confirm_class", "actives", "passives", "stats", "done"], steps)
first = PAGES[0]
check("the first page has every people, he, she and they, and the look's rows", len(first["who"]["peoples"]) == len(world.peoples)
      and first["who"]["pronouns"] == ["he", "she", "they"] and first["tab"] == "who" and first["tabs"][0][1] == "Who you were", first["who"]["pronouns"])
check("...and is shown before the goddess has said anything", not first["goddess"])
acts = next(p for p in PAGES if isinstance(p, dict) and p.get("cards") and p["step"] == "actives")
check("the abilities are cards with what they cost, what kind they are and what they do, and the full detail on hover",
      len(acts["cards"]) == 15 and all(c["name"] and c["text"] and c["tip"] for c in acts["cards"]) and any(re.match(r"\d+ (stamina|mana)$", c["cost"]) for c in acts["cards"]),
      acts["cards"][:2])
check("...with filters that count them", acts["groups"][0] == ["all", "All", 15] and sum(n for g, _, n in acts["groups"][1:]) == 15, acts["groups"])
check("...and her last words over it all", all(isinstance(p, str) or p["step"] in ("who", "name") or p["goddess"] for p in PAGES))
body = next(p["body"] for p in PAGES if isinstance(p, dict) and p.get("body"))
check("the attributes page marks the class's main attributes and suggests a shape", [r["id"] for r in body["rows"] if r["main"]] == ["strength", "constitution"]
      and "Ironbound Bulwark" in body["suggest_label"] and sum(body["suggested"].values()) == body["total"])
check("a character was made, as the page shaped it", made is not None and made.attributes.model_dump() == body["suggested"], made and made.attributes)
check("...with the abilities and traits picked on the cards", made and [a.name for a in made.actives] == [offered[0].name, offered[3].name, offered[5].name])
check("...and who she was: her people, she, and the sentence the world sees", made and made.people == "dwarf" and made.pronoun == "she"
      and made.look_text == look.describe(dwarf) and made.look["flags"] == ["braided"], made and (made.people, made.pronoun, made.look_text))
check("the goddess was told who stood before her, and so was the reading of the calling", "stocky dwarf woman" in scene.system and READ and "stocky dwarf woman" in READ[0])
if have_node:
    c = made.model_copy(deep=True)
    out = node(pools_js + f"\nconsole.log(JSON.stringify(crPools({json.dumps(body)}, {json.dumps(made.attributes.model_dump())})));")
    got = json.loads(out) if out.startswith("{") else out
    want = {p: pools.maximum(c, p) for p in pools.POOLS}
    check("the page's health, stamina and mana are the engine's for the character made", got == want, (got, want))

# ---- (f389) the weapon they will wake with, on the attributes page
from character import kit
from engine import combat, items, mentor
check("the weapon is chosen as the attributes page opens: her words name a hammer, so a warhammer", scene.weapon == "warhammer" and made.start_weapon == "warhammer",
      (scene.weapon, made.start_weapon))
check("...and the page shows it, the attribute it hits harder with, and marks that row", body["weapon"] and body["weapon"]["name"] == kit.starting_weapon("warhammer").name
      and body["weapon"]["attrs"] == ["strength"] and [r["id"] for r in body["rows"] if r["weapon"]] == ["strength"], body["weapon"])
check("...its blow and hit chance against a wolf grow as that attribute is raised", body["blow"][30] > body["blow"][10] and body["hit"][30] > body["hit"][10]
      and body["foe"] == "a wolf", (body["blow"][10], body["blow"][30], body["hit"][10], body["hit"][30]))
woke = made.model_copy(deep=True)
woke.equipment = {}
kit_text = kit.give_starting_kit(woke, "Ironbound Bulwark", False, world)
held = woke.equipment.get("main_hand")
check("...and it is the very weapon they wake with", held is not None and held.base == "warhammer" and held.name == body["weapon"]["name"], kit_text)
f = combat.fighter_from_character(woke)
wolf = combat.fighter_from_creature(world.bestiary[mentor.M["hunt"]["creature"]], 1, "normal", "e1")
best = max(woke.attributes.strength, 0)
check("...and the page's blow and hit chance are the fight's for the character made",
      body["hit"][best] == round(combat.hit_parts(f, wolf, combat.Combat(fighters=[f, wolf]))[0])
      and body["blow"][best] == round(combat.raw_damage(f, 1.0, {"always"}, random.Random(0), steady=True)), (body["hit"][best], body["blow"][best]))
check("...and the terminal is told it with the attribute advice", any(g.startswith("You will wake with a ") and "strength" in g for g in scene.guidance), scene.guidance)
if have_node:
    best_js = re.search(r"function crWeaponBest\(b, v\) \{.*?\n\}\n", JS, re.S).group(0)
    out = node(best_js + f"\nconsole.log(crWeaponBest({json.dumps(body)}, {json.dumps(made.attributes.model_dump())}));")
    check("...and the page looks them up by the same attribute", out == str(made.attributes.strength), out)

# ---- a note during creation is on the page, not behind it
PAGES.clear()
s2 = ThresholdScene()
s2.drawn = True
s2.step = Step.CONCEPT
s2.concept = "x"
def fail(*a, **k):
    from llm.gateway import LLMError
    raise LLMError("no")
cc.interpret_concept = fail
s2.read_class()
check("when her reading fails, the page says so (a note behind the page is a note nobody reads)",
      any(isinstance(p, dict) and "couldn't read that concept" in (p.get("note") or "") for p in PAGES), [p.get("note") for p in PAGES if isinstance(p, dict)])

# ---- the terminal, and the menu
uc.creation = lambda d: False
answers[:] = ["a towering orc man with black hair and a broken tusk", "#menu"]
t = ThresholdScene()
t.run()
check("in the terminal the same step is a line of words", t.who_choice and t.who_choice["people"] == "orc" and t.who_choice["pronoun"] == "he"
      and "broken tusk" in look.describe(t.who_choice), t.who_choice)
answers[:] = ["#menu"]
check("leaving for the menu before the goddess speaks makes nobody", ThresholdScene().run() is None)

# ---- the world sees them
shutil.rmtree("saves/creation_page_test", ignore_errors=True)
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from scenes.world import WorldScene
store = CampaignStore.open_or_create("creation_page_test")
store.meta.seed = 3; store.meta.minutes = 600; store.meta.turn = 1; store.save_meta()
store.save_player(PlayerState(character=made, location="trading_square", guild_rank="F"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("trading_square")
seen = truth.scene_of(ws).view(truth.viewer_for_npc(types.SimpleNamespace(knowledge_groups=["everyone"], id="x", location="parth", role="guard")), "townsfolk").text()
check("a townsperson sees a woman, and how she looks", "is a woman" in seen and "braided copper hair" in seen, seen[-400:])
check("the narrator is told how the player looks, with what they wear", ws.gear_line().startswith("A stocky dwarf woman with braided copper hair"), ws.gear_line())
store.close()
shutil.rmtree("saves/creation_page_test", ignore_errors=True)

# ---- the window
from ui.gui.bridge import Bridge
b = Bridge()
ev = []
b.emit = lambda **k: ev.append(k)
b.install()
uc.creation({"step": "who"}); uc.creation_done()
b.uninstall()
check("the window draws each step and closes the pages at the end", [e["k"] for e in ev if e["k"].startswith("creation")] == ["creation", "creation_end"], ev)
check("...and gives the console back as it was", uc.creation({"step": "x"}) is False)
html = Path("ui/gui/web/index.html").read_text()
check("the page has its tabs, her words, the card and its own box to type in", all(f'id="{i}"' in html for i in ("creation", "crtabs", "crvoice", "crcard", "crinput")))

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
