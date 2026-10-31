"""(f420) Words and plans the f395 night read wrong. 'I'll check these woods' went to a companion as chat; 'I'll take the contract' to the
clerk lost its words; the audit threw away its own corrected reading of an improvised act, and merged two into one; a word to a companion
and the walk it proposed were flagged and asked again; 'I hand Odly the silver' found no one to give to; equipping the sword in hand
said it was not carried; 'silverleaf' was coin; an empty reading of a line made up an offer of odd jobs; 'the guild hall' named the
clerk; and the plan readings ('our rooms', the generic words) are pinned in data/replay/interp_cases.yaml."""
import random, shutil, sys, types
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 10))
import ui.console as uc
NOTES = []
uc.note = lambda m, *a, **k: NOTES.append(str(m))
for fn in ("narrate", "say", "npc_says", "dialogue", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
from engine import actions, candidates, intent_audit as ia, inventory as inv, mentor
from llm.contracts import ActionIntent as A, WorkOffer
from npc.traits import load_traits
import scenes.work_actions as wa
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# ---- one first-person definition
for line in ("I'll check these woods for any more Black Bears", "I am going to scan the trees", "I'm taking the bounty", "We're heading out"):
    check(f"{line!r} is the player about to do something", actions.first_person_action(line))
for line in ("I'll take the contract to hunt three merrows", "I'm taking the bounty on the bandit captain"):
    check(f"...but {line!r}, said to someone here, is words to them", not actions.first_person_action(line, addressee_present=True))
for line in ("I'm fine", "I think so", "I'll be fine", "I will think about it", "Will you come?"):
    check(f"{line!r} is an answer, as before", not actions.first_person_action(line))

# ---- the audit keeps what an improvised act is
a, b = A(kind="other", summary="makes a joke about wings"), A(kind="other", summary="attempts to grow wings and fly away")
check("an improvised act read again is a different step", ia._key(a) != ia._key(b))
two = [A(kind="other", summary="wedge the door shut with the bench"), A(kind="other", summary="climb out through the window")]
check("...and two improvised acts in one line are not merged", ia._key(two[0]) != ia._key(two[1]))
prop = [A(kind="talk", target="hire:h1", speech="Gallen, let's head toward the Riverhaven guild hall"), A(kind="move", destination="riverhaven_guild")]
check("a word to a companion and the walk it proposes is not two intents to check", "multi_intent" not in ia.risk_flags("x", prop, ia.Situation()))
check("...while two unrelated deeds still are", "multi_intent" in ia.risk_flags("x", [A(kind="look"), A(kind="wait")], ia.Situation()))

# ---- a scene
shutil.rmtree("saves/words_plans_420_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("words_plans_420_test")
store.meta.seed = 10; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(10))
char.coins = 10_000
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
odly = {"id": "h1", "name": "Odly Garth", "role": "fighter", "level": 2, "permanent": True, "rank": "F", "bond": 12, "pronoun": "she",
        "hp_frac": 0.4, "hp_at": 0, "memories": [], "said": [], "talk": [], "blurb": "a sellsword"}
ws.player.party, ws.player.party_mode = [odly], "with"
ws.enter("parth")

# ---- giving to a companion
NOTES.clear()
c0 = ws.player.character.coins
ws.on_give(A(kind="give", target="hire:h1", item="2 silver"), "I hand Odly 2 silver")
check("coin handed to a companion is given, not refused", ws.player.character.coins == c0 - 200 and not any("no one here" in n for n in NOTES), NOTES)
ws.pack.append(inv.make_good("healing_draught", 1))
ws.on_give(A(kind="give", item="healing draught"), "I give Odly a healing draught")
check("...and a draught given to one who is hurt is drunk", odly["hp_frac"] > 0.4 and not inv.find(ws.pack, "healing draught"), odly["hp_frac"])
check("...and remembered", any("gave me" in (m.get("text") if isinstance(m, dict) else str(m)) for m in odly.get("memories", [])), odly.get("memories"))

# ---- equipping what is already in hand
held = next(iter(ws.player.character.equipment.values()), None)
NOTES.clear()
if held is not None:
    ws.equip_command(held.name)
check("equipping what is already in hand is a quiet yes", held is not None and NOTES and "already" in NOTES[-1] and "aren't carrying" not in NOTES[-1], NOTES)

# ---- coin, as a whole word
for words, want in (("2 silver", True), ("the coins", True), ("some silver to the guard", True), ("gold", True), ("silverleaf", False),
                    ("a silver signet ring", False), ("golden apple", False), ("my feet", False), ("the fee", True)):
    check(f"{words!r} {'is' if want else 'is not'} coin", ws.coin_word(words) == want)

# ---- no made-up offer
real_gen = wa.generate
for task in ("", "none", "0", "N/A"):
    wa.generate = lambda *a, task=task, **k: WorkOffer(task=task, pay=0, minutes=60)
    check(f"a reading of {task!r} is no offer of work", ws.inferred_offer(types.SimpleNamespace(label=lambda: "the smith"), "x") is None)
wa.generate = lambda *a, **k: WorkOffer(task="load the grain onto the wagon", pay=20, minutes=60)
check("...while a real task is kept", ws.inferred_offer(types.SimpleNamespace(label=lambda: "the smith"), "x").task.startswith("load"))
wa.generate = real_gen

# ---- one generic-word list; whole-word naming
check("the far-place words come from interpret.yaml, the one list", ws.GENERIC_WORDS is candidates.GENERIC)
clerk = types.SimpleNamespace(name="Wren Hollis", epithet="the clerk with ink-stained cuffs", role="guild_clerk")
check("'the guild hall' does not name the clerk", not mentor.addresses("Let's go to the guild hall", clerk))
check("...'the clerk' does, and 'the guild clerk'", mentor.addresses("I ask the clerk", clerk) and mentor.addresses("the guild clerk", clerk))
check("...and a name is a whole word ('wrench' is not Wren)", not mentor.addresses("I pick up the wrench", clerk) and mentor.addresses("Wren, hello", clerk))

store.close()
shutil.rmtree("saves/words_plans_420_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
