"""(f418) One price, and the world's own answers. A hungry town's innkeeper quoted a bowl at its list price and the player was charged a
third more; the narrator, told '45 copper', wrote 'four copper coins'; 'I head up to our rooms' got 'There's no such place.', read as the
keeper's answer; and 'the clerk heads off for the day' was printed above the hour spent helping that same clerk."""
import random, re, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 8))
import ui.console as uc
ORDER = []
uc.note = lambda m, *a, **k: ORDER.append(("note", str(m)))
uc.narrate = lambda t, *a, **k: ORDER.append(("narrate", str(t)))
for fn in ("say", "npc_says", "dialogue", "ledger"):
    setattr(uc, fn, lambda *a, **k: None)
uc.panel = lambda name, data: False
sys.path.insert(0, "tools")
import page_measures
from engine import ledger, money, needs, pulse
from llm.contracts import ActionIntent as A, Narration
from npc.traits import load_traits
import scenes.world as W
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/one_price_418_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("one_price_418_test")
store.meta.seed = 8; store.meta.turn = 1; store.meta.minutes = 600; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(8))
char.coins = 10 ** 6
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.player.mentor["never"] = True
ws.enter("tilted_plough")

# ---- a town with prices up a third: the quote, the list, what the keeper says and the charge are one figure
real_factor = pulse.price_factor
pulse.price_factor = lambda store, world, place, now: 1.32
keeper = next(n for n in ws.present if n.role == "innkeeper")
meal = next(w for w in world.roles["innkeeper"].sells if w.kind == "meal")
quoted = ws.quote_ware(keeper, meal).price
said = next((l for l in ws.wares_said(keeper) if l.startswith(meal.name)), "")
check("the price the game quotes has the town's dear prices in it", quoted == ws.price_of(meal.price, keeper, "meal") and quoted > meal.price,
      (quoted, meal.price))
check("...and the keeper is told to say that figure, not the list's", said.endswith(money.words(quoted)), (said, money.words(quoted)))
heard = []
real_converse = W.converse
W.converse = lambda *a, **k: (heard.append(k.get("wares")), real_converse(*a, **k))[1]
ws.on_talk(A(kind="talk", target=keeper.id, speech="What's a hot meal cost?"), "What's a hot meal cost?")
W.converse = real_converse
check("...which is what reaches them when they answer", heard and any(l.startswith(meal.name) and l.endswith(money.words(quoted)) for l in heard[-1] or []),
      heard[-1:] if heard else "not asked")
told = []
real_narrate = ws.narrate
ws.narrate = lambda event, text="", *a, **k: told.append(event)
before = ws.player.character.coins
ledger.begin()
ws.buy_ware(keeper, meal, "I buy a hot meal")
check("...and the charge is the same figure", before - ws.player.character.coins == quoted, (before - ws.player.character.coins, quoted))
FIG = re.compile(r"\b\d+\b|\b(copper|silver|gold)\b", re.I)
check("the passage of a payment is not handed a sum to restate", told and not FIG.search(told[-1]), told[-1:])
check("...nor is the turn's record of it", any(r["kind"] == "paid" for r in ledger.ROWS) and not any(FIG.search(r["say"]) for r in ledger.ROWS
                                                                                                   if r["kind"] == "paid"), ledger.ROWS)
ws.narrate = real_narrate
stock = ws.stock_here()
check("every piece of stock is priced by the same sum", all(p == ws.price_of(__import__("engine.items", fromlist=["price"]).price(i)
                                                                          * ws.stock_multiplier(n, i), n) for n, i, p in stock if not i.uid.startswith("relic_")))
pulse.price_factor = real_factor

# ---- a walk to somewhere the game does not know is answered in the world
line = ws.no_such_place("our_rooms")
check("a walk to nowhere is answered in the world's words, with the ways that are real", line.startswith("You look about for our rooms, but nothing here goes by that name")
      and "There's no such place" not in line, line)
check("...and the night's measures still count it as a refusal", page_measures.REFUSALS.search(line))

# ---- a note time raised mid-line comes after the passage
real_fresh = W.fresh
W.fresh = lambda task, system, request, *a, **k: Narration(text="You sit by the fire a while.") if task == "narrate" else real_fresh(task, system, request, *a, **k)
ws.audit_plan = lambda text, plan, raw=None: plan
ws.interpret = lambda text, hint="": [A(kind="wait", wait_minutes=60, summary="wait an hour"), A(kind="look", summary="look round the room")]
real_voice = needs.voice
needs.voice = lambda was, now: ["Your stomach growls; you could do with a meal."]
ORDER.clear()
ws.turn("I wait an hour and look round the room")
needs.voice = real_voice
W.fresh = real_fresh
first_passage = next((i for i, (k, _) in enumerate(ORDER) if k == "narrate"), None)
hunger = next((i for i, (k, t) in enumerate(ORDER) if k == "note" and "stomach growls" in t), None)
check("a note that time raised in the middle of the line is printed after its passage", first_passage is not None and hunger is not None
      and hunger > first_passage, ORDER[:8])
ws.step, ws.buffering = None, False
ORDER.clear()
ws.time_note("The clerk heads off for the day.")
check("...and straight away when no line is being told", ORDER == [("note", "The clerk heads off for the day.")], ORDER)

store.close()
shutil.rmtree("saves/one_price_418_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
