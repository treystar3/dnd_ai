"""(f646) What the reading of a line was told to fill is read, and a count asked of a purchase is kept or refused
(docs/design/21_play_faults_plan.md, A4; found in play: docs/play/2026-11-15_play_findings.md 6.1). 'I buy three bandages' bought
one and said nothing: buying never read the count. The class is a handler that ignores part of the reading it was handed. Held here:
- the fence: for every kind, each field the interpreter is told to fill for it (engine/actions.py `fills`, and the target of a kind
  aimed at someone) is read by that kind's handler, by its source, or is declared there as not read (`unread`); what is declared
  is what is found, no more and no less, and the count of them only falls;
- the table and the interpreter's instructions agree on which kind is told which field, both ways, apart from the words listed
  here that are not an instruction ("use that person's place id");
- buying takes the count: that many are paid for and carried, eaten or drunk, and the line of the purchase says how many and
  for how much in all; a count the purse cannot meet, and a count the seller does not hold, are refused in a line that says so
  and nothing is paid; a count of one is as it was; what a seller holds is sold first and the rest from their trade's own list,
  each at its own price; a number in a thing's name is never a count ("a meal for the two of us", "Blade of Seven Stars");
- what is sold singly (a room, a piece of gear, a mount, a house) asked for in a number is refused in a line, and nothing is
  paid; a room that would be free is not said to be theirs and then refused.
The fields every kind has (summary, checks, mark, force) are the turn's, not a handler's, and are outside this fence.
Run: python tools/sim/intent_fields_646_test.py"""
import ast
import dataclasses
import inspect
import re
import shutil
import sys
import textwrap
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 10)
simlib.install(stub)
SHOWN = simlib.quiet_console()
from engine import actions, inventory as inv, items, money, mounts, pools, situation_parts
from llm.contracts import ActionIntent as A
from scenes import world_prompts
from scenes.world import WorldScene

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


FIELDS = set(A.model_fields) - {"kind"}
BY = {a.kind: a for a in actions.ACTIONS}
GENERAL = {"summary", "checks", "mark", "force"}                       # every kind's; read by the turn


def reads(cls, name: str, index: int = 0, seen: set | None = None) -> set:
    """The fields of the reading a method reads, by its source: its own, and those of the scene's methods it hands the reading to."""
    seen = set() if seen is None else seen
    fn = inspect.getattr_static(cls, name, None)
    static = isinstance(fn, staticmethod)
    fn = getattr(fn, "__func__", fn)
    fn = getattr(fn, "__wrapped__", fn)
    if fn is None or not inspect.isfunction(fn) or (name, index) in seen:
        return set()
    seen.add((name, index))
    tree = ast.parse(textwrap.dedent(inspect.getsource(fn))).body[0]
    params = [a.arg for a in tree.args.args][0 if static else 1:]
    if index >= len(params):
        return set()
    p, out = params[index], set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Load) and isinstance(node.value, ast.Name) and node.value.id == p \
                and node.attr in FIELDS:
            out.add(node.attr)
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == "getattr" and len(node.args) >= 2 and isinstance(node.args[0], ast.Name) \
                    and node.args[0].id == p and isinstance(node.args[1], ast.Constant) and node.args[1].value in FIELDS:
                out.add(node.args[1].value)
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) and node.func.value.id == "self":
                for i, a in enumerate(node.args):
                    if isinstance(a, ast.Name) and a.id == p:
                        out |= reads(cls, node.func.attr, i, seen)
    return out


def told(a) -> set:
    """What the interpreter is told to fill for a kind: the table's own list, and whom it is aimed at when it is aimed."""
    return set(getattr(a, "fills", ())) | ({"target"} if a.targeted else set())


# ---- the reader of sources reads what is read and nothing else
class Fake:
    def on_a(self, intent, text):
        return self.helper(text, intent)

    def helper(self, text, it):
        return it.item, self.how(it), text.count("x")

    @staticmethod
    def how(reading):
        return getattr(reading, "count", 1)

    def on_b(self, intent, text):
        other = text
        return other.count, intent

    def on_c(self, intent, text):
        intent.target = text
        return intent


check("the reader of sources finds a field read directly, through a method handed the reading, and by getattr",
      reads(Fake, "on_a") == {"item", "count"}, reads(Fake, "on_a"))
check("...and credits nothing to a handler that reads none, whatever else has an attribute of that name", reads(Fake, "on_b") == set(), reads(Fake, "on_b"))
check("...nor to one that only writes a field", reads(Fake, "on_c") == set(), reads(Fake, "on_c"))

# ---- the fence: told and not read is declared, and nothing else is
found = {a.kind: told(a) - reads(WorldScene, f"on_{a.kind}") for a in actions.ACTIONS}
declared = {a.kind: set(getattr(a, "unread", ())) for a in actions.ACTIONS}
check("every field a kind is told to fill is read by its handler, or declared as not read; and nothing declared is in fact read",
      found == declared, {k: (sorted(found[k]), sorted(declared[k])) for k in found if found[k] != declared[k]})
check("the table tells every kind something only of the reading's own fields",
      all(told(a) <= FIELDS - GENERAL and set(getattr(a, "unread", ())) <= told(a) for a in actions.ACTIONS),
      [a.kind for a in actions.ACTIONS if not told(a) <= FIELDS - GENERAL])
check("the fields told and not read only fall in number (8 when the fence was built)", sum(len(v) for v in declared.values()) <= 8, declared)
check("buying reads the count", "count" in told(BY["buy"]) and "count" not in declared["buy"], (told(BY["buy"]), declared["buy"]))
check("no kind that moves goods or coin by a count leaves it unread",
      not any("count" in declared[k] for k in ("buy", "sell", "use", "give", "drop", "discard", "store", "retrieve")), declared)
check("the table is told of at least the kinds the instructions list for an item", sum("item" in told(a) for a in actions.ACTIONS) >= 13)

# ---- the table and the interpreter's instructions agree
text = world_prompts.INTERPRET_SYSTEM
body = text[text.index("\ndestination:"):text.index("Respond only")]
names = "|".join(sorted(FIELDS))
marks = sorted((m.start(), m.group(1)) for m in re.finditer(r"(?:^|(?<=\. )|(?<=\)\. ))(" + names + r"): ", body, re.M))
said: dict = {}
for i, (at, f) in enumerate(marks):
    said[f] = said.get(f, "") + body[at:marks[i + 1][0] if i + 1 < len(marks) else len(body)]
check("the instructions describe every field of the reading", set(said) == FIELDS, sorted(FIELDS - set(said)))


def word(w: str, where: str, flags=0) -> bool:
    return bool(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", where, flags))


def backed(a, f: str) -> bool:
    """The instructions tell this kind this field: the field's entry names the kind, the kind's own entry names the field, the kind
    is aimed at someone, or (a count) the kind is one the item's entry lists, the count being told in that entry."""
    return word(a.kind, said.get(f, "")) or word(f, a.prompt, re.I) or (f == "target" and a.targeted) \
        or (f == "count" and word(a.kind, said.get("item", "")))


NOT_AN_INSTRUCTION = {("use", "destination"), ("use", "target"), ("work", "speech"), ("talk", "count"), ("accept_quest", "count"),
                      ("train", "ability")}                            # "use that person's place id", "all count", "a new ability"
SPECIFIC = sorted(FIELDS - GENERAL)
loose = [(a.kind, f) for a in actions.ACTIONS for f in sorted(told(a)) if not backed(a, f)]
check("the table tells a kind no field the instructions do not", not loose, loose)
missing = [(a.kind, f) for a in actions.ACTIONS for f in SPECIFIC if backed(a, f) and f not in told(a) and (a.kind, f) not in NOT_AN_INSTRUCTION]
check("the instructions tell a kind no field the table does not", not missing, missing)
check("the words set aside as not an instruction are all words the instructions hold",
      all(backed(BY[k], f) for k, f in NOT_AN_INSTRUCTION), [x for x in NOT_AN_INSTRUCTION if not backed(BY[x[0]], x[1])])

# ---- the table checks itself at start-up
kept_table = actions.ACTIONS
last = kept_table[-1]
try:
    actions.ACTIONS = (*kept_table[:-1], dataclasses.replace(last, fills=("no_such_field",)))
    p1 = actions.problems(WorldScene, text)
    actions.ACTIONS = (*kept_table[:-1], dataclasses.replace(last, fills=("item",), unread=("count",)))
    p2 = actions.problems(WorldScene, text)
except TypeError as e:
    p1 = p2 = [f"the table has no such part: {e}"]
finally:
    actions.ACTIONS = kept_table
check("a field the reading does not have, told to a kind, is a problem at start-up", any("no_such_field" in p for p in p1), p1)
check("...and so is a field declared as not read that the kind is not told", any("count" in p and last.kind in p for p in p2), p2)
check("the table as it stands has no problems", actions.problems(WorldScene, text) == [], actions.problems(WorldScene, text))

# ---- buying: the count is kept or refused
NAME = "intent_fields_646"
g = simlib.campaign(NAME, cls="warrior", seed=10, location="tilted_plough")
ws, store = g.scene, g.store
ws.enter("tilted_plough")
stub.plan = [{"kind": "look"}]
ws.turn("I look around.")
stub.plan = None
keeper = next(n for n in ws.present if n.role == "innkeeper")


def carrying(good: str) -> int:
    return sum(i.quantity for i in ws.pack if i.good == good)


def unit(ware_id: str) -> int:
    return ws.quote_ware(keeper, next(w for w in ws.wares_of(keeper) if w.id == ware_id)).price


def buy(ware: str, text: str, count: int = 1, coins: int = 5000, item: str = "", good: str = "wine"):
    """One purchase as a step of a typed line: what was paid, what is carried more than before, and what the player read."""
    c = ws.player.character
    c.coins = coins
    c.stamina = pools.maximum(c, "stamina") * 0.1
    store.save_player(ws.player)
    had, n, stamina = carrying(good), len(SHOWN), pools.current(c, "stamina")
    stub.plan = [{"kind": "buy", "ware": ware, "target": keeper.id, "count": count, "item": item, "summary": "a purchase"}]
    stood = ws.turn(text)
    stub.plan = None
    c = ws.player.character
    return {"stood": stood, "paid": coins - c.coins, "got": carrying(good) - had, "read": [t for k, t in SHOWN[n:]],
            "ledger": [t for k, t in SHOWN[n:] if k == "ledger"], "stamina": round((pools.current(c, "stamina") - stamina) / pools.maximum(c, "stamina"), 2)}


def refused(got, *words):
    """Nothing paid and nothing carried, and a line read that holds these words."""
    return got["paid"] == 0 and got["got"] == 0 and any(all(w.lower() in t.lower() for w in words) for t in got["read"])


wine = unit("wine")
got = buy("wine", "I buy a jar of wine.")
check("a count of one: one is paid for and carried, as it was", got["paid"] == wine and got["got"] == 1 and any("a jar of wine" in t for t in got["ledger"]), got)
got = buy("wine", "I buy three jars of wine.", count=3)
check("6.1, a count of three: three are paid for and three are carried", got["paid"] == 3 * wine and got["got"] == 3, got)
check("...and the line of the purchase says how many and for how much in all",
      any("three jars of wine" in t and money.fmt(3 * wine) in t for t in got["ledger"]), got["ledger"])
got = buy("wine", "I buy a jar of wine for the two of us.", item="a jar of wine for the two of us")
check("a number in the item's own words, the count left at one, is not a count: one is bought", got["paid"] == wine and got["got"] == 1, got)
got = buy("wine", "I buy three jars of wine.", count=3, coins=3 * wine - 1)
check("a count the purse cannot meet: refused in a line that says what it comes to and what is held, and nothing is paid",
      refused(got, "three jars of wine", money.words(3 * wine), money.words(3 * wine - 1)), got)
got = buy("wine", "I buy two jars of wine.", count=2, coins=3 * wine - 1)
check("...and a count it can meet is then bought", got["paid"] == 2 * wine and got["got"] == 2, got)

got = buy("wine", "I buy two hundred jars of wine.", count=200, coins=10 ** 6)
check("a count over the most sold at once: refused in a line that says the most, never cut to it and charged", refused(got, "no more than 99"), got)
got = buy("wine", "I buy ninety-nine jars of wine.", count=99, coins=10 ** 6)
check("...and the most itself is sold whole", got["paid"] == 99 * wine and any("99 jars of wine" in t for t in got["ledger"]), got)
for none in (0, -3):
    got = buy("wine", "I buy a jar of wine.", count=none)
    check(f"a count of {none} is one", got["paid"] == wine and got["got"] == 1, got)

# what the seller holds: a shelf
situation_parts.give_stock(store, keeper, "bandage", 2, "th646", ws.minutes)
held = lambda: sum(int(e.data.get("count", 0)) for e in situation_parts.held(store, keeper.id, "bandage"))
bandage = unit("stock:bandage")
got = buy("stock:bandage", "I buy three bandages.", count=3, good="bandage")
check("a count the seller does not hold: refused in a line that says how many they have, nothing is paid, and they hold what they held",
      refused(got, "only two bandages") and held() == 2, (got, held()))
check("...a line that begins with a capital, whoever the seller is to the player", all(t[:1].isupper() for t in got["read"] if "has only" in t), got["read"])
got = buy("stock:bandage", "I buy two bandages.", count=2, good="bandage")
check("a count the seller holds: all of it is bought, and it is gone from what they hold",
      got["paid"] == 2 * bandage and got["got"] == 2 and held() == 0, (got, held()))
situation_parts.give_stock(store, keeper, "torch", 1, "th646", ws.minutes)
got = buy("stock:torch", "I buy two torches.", count=2, good="torch")
check("one held and two asked: refused in a line that says there is the one", refused(got, "only the one"), got)

# what they hold of a good their own trade sells too: the held first, the rest from the trade's list, each at its own price
situation_parts.give_stock(store, keeper, "wine", 1, "th646", ws.minutes)
held_wine = lambda: sum(int(e.data.get("count", 0)) for e in situation_parts.held(store, keeper.id, "wine"))
from_stock = unit("stock:wine")
listed_wine = next(w for w in ws.world.roles["innkeeper"].sells if w.id == "wine")
listed_wine.price += 6                                                 # the two prices differ, so each part is seen to be charged at its own
from_list = ws.quote_ware(keeper, listed_wine).price
got = buy("stock:wine", "I buy three jars of wine.", count=3)
check("one held of a good the trade sells too, three asked: three are bought, the held one first and two from the trade's list at its price",
      from_stock != from_list and got["paid"] == from_stock + 2 * from_list and got["got"] == 3 and held_wine() == 0
      and any("three jars of wine" in t for t in got["ledger"]), (got, from_stock, from_list, held_wine()))
listed_wine.price -= 6

# what they hold goes by the good's bare name: said as the trades sell it, or by measure when none does
situation_parts.give_stock(store, keeper, "salt", 2, "th646", ws.minutes)
salt = unit("stock:salt")
got = buy("stock:salt", "I buy three sacks of salt.", count=3, good="salt")
check("held salt, more asked than held: counted as the trades sell it", refused(got, "only two sacks of salt"), got)
got = buy("stock:salt", "I buy two sacks of salt.", count=2, good="salt")
check("...and its purchase too", got["paid"] == 2 * salt and got["got"] == 2 and any("two sacks of salt" in t for t in got["ledger"]), got)
situation_parts.give_stock(store, keeper, "yarrow", 2, "th646", ws.minutes)
got = buy("stock:yarrow", "I buy three bundles of yarrow.", count=3, good="yarrow")
check("a good by measure that no trade sells: counted in measures", refused(got, "only two measures of yarrow"), got)

# a material, and a pack with no room: what the passage is told
from scenes.shop_actions import ShopActions
from world.loader import Ware
told = []
real_narrate = ws.narrate
ws.narrate = lambda event, text="", *a, **k: told.append(event)
c = ws.player.character
c.coins = 5000
iron = ws.quote_ware(keeper, Ware(id="iron", name="an iron bar", price=90, kind="material", item="iron")).price
ok = ws.buy_ware(keeper, Ware(id="iron", name="an iron bar", price=90, kind="material", item="iron"), "I buy three iron bars.", count=3)
check("a material: three are paid for and carried, and the passage is told three",
      ok and c.coins == 5000 - 3 * iron and sum(i.quantity for i in ws.pack if i.material == "iron" and i.base == "raw_material") == 3
      and "three iron bars" in told[-1], (c.coins, iron, told[-1:]))
while carrying("wine"):
    inv.take(ws.pack, inv.GOODS["wine"].name, 1)
ws.to_pack(inv.make_good("wine", inv.GOODS["wine"].stack - 1))        # one more jar fits the stack, and no more
real_slots = ws.pack_slots
ws.pack_slots = lambda: 0
c.coins = 5000
on_ground = lambda: sum(i.quantity for i in ws.ground_here() if i.good == "wine")
lay, had = on_ground(), carrying("wine")
ok = ws.buy_ware(keeper, next(w for w in ws.wares_of(keeper) if w.id == "wine"), "I buy three jars of wine.", count=3)
fit = carrying("wine") - had
check("a pack with room for only some: the three are paid for, some are carried, the rest lie here, and the passage is told so",
      ok and c.coins == 5000 - 3 * wine and 0 < fit < 3 and on_ground() == lay + 3 - fit and "the rest is set down here" in told[-1]
      and "in their pack." not in told[-1], (c.coins, fit, on_ground(), told[-1:]))
while carrying("wine"):
    inv.take(ws.pack, inv.GOODS["wine"].name, 1)
c.coins = 5000
lay = on_ground()
ok = ws.buy_ware(keeper, next(w for w in ws.wares_of(keeper) if w.id == "wine"), "I buy three jars of wine.", count=3)
check("a pack with no room: the three are paid for, lie here, and the passage is told they were set down, never pocketed",
      ok and c.coins == 5000 - 3 * wine and carrying("wine") == 0 and on_ground() == lay + 3 and "they are set down here" in told[-1]
      and "in their pack." not in told[-1], (c.coins, carrying("wine"), on_ground(), told[-1:]))
ws.pack_slots, ws.narrate = real_slots, real_narrate

# how a number of a ware is said
said_so = {("a jar of wine", 3): "three jars of wine", ("an iron bar", 2): "two iron bars", ("bandage", 2): "two bandages", ("a torch", 4): "four torches",
           ("a bundle of candles", 2): "two bundles of candles", ("a hot meal", 1): "a hot meal", ("a mug of ale", 13): "13 mugs of ale",
           ("a tome of the second circle", 2): "two tomes of the second circle", ("silverleaf", 2): "two silverleaves"}
check("a number of a ware is said as a person would", all(ShopActions.several(n, k) == v for (n, k), v in said_so.items()),
      {k: ShopActions.several(*k) for k, v in said_so.items() if ShopActions.several(*k) != v})
every = sorted({w.name for r in ws.world.roles.values() for w in r.sells if w.kind != "room"})
check("...for every ware a trade sells: no article left in it, and its thing in the plural",
      all(re.fullmatch(r"two (?!a |an |the )[a-z ]+s( of [a-z ]+)?", ShopActions.several(n, 2)) for n in every),
      [ShopActions.several(n, 2) for n in every if not re.fullmatch(r"two (?!a |an |the )[a-z ]+s( of [a-z ]+)?", ShopActions.several(n, 2))])

# eaten and drunk at once: as many as were paid for
meal = unit("meal")
one = buy("meal", "I buy a hot meal.")
two = buy("meal", "I buy two hot meals.", count=2)
check("two meals: two are paid for, and both are eaten (what one restores, twice)",
      two["paid"] == 2 * meal and one["paid"] == meal and one["stamina"] > 0 and abs(two["stamina"] - 2 * one["stamina"]) <= 0.01, (one, two))
check("...and its line says two", any("two hot meals" in t for t in two["ledger"]), two["ledger"])

# sold singly
SINGLY = ("one at a time",)
got = buy("room", "I take two rooms for the night.", count=2)
check("a room asked for twice: refused in a line, nothing is paid, and no room is theirs",
      refused(got, *SINGLY) and ws.player.room != "tilted_plough", (got, ws.player.room))
from engine import clock
ws.player.free_room_day = clock.day(ws.minutes)
store.save_player(ws.player)
got = buy("room", "I take two rooms for the night.", count=2)
check("a room that would be free, asked for twice: refused, and never said to be theirs",
      refused(got, *SINGLY) and not any("is yours" in t for t in got["read"]) and ws.player.room != "tilted_plough", got)
ws.player.free_room_day = -1
store.save_player(ws.player)
got = buy("room", "I take a room for two nights.", item="a room for two nights")
check("a number in the words for a room, the count left at one: the room is theirs", got["paid"] == unit("room") and ws.player.room == "tilted_plough", (got, ws.player.room))
ws.player.room, ws.player.room_until = "", 0
store.save_player(ws.player)
got = buy("room", "I take a room for the night.")
check("...and a room asked for once is theirs", got["paid"] == unit("room") and ws.player.room == "tilted_plough", (got, ws.player.room))

blade = items.make(next(iter(items.CATALOG))).model_copy(update={"name": "blade of seven stars"})
sold = []
ws.stock_here = lambda: [(keeper, blade, 100)]
ws.buy_stock_item = lambda npc, item, price, text="", quiet=False: (sold.append(item.uid), True)[1]
got = buy(blade.name, f"I buy two of the {blade.name}.", count=2)
check("a piece of gear asked for twice: refused in a line, and none is sold", refused(got, *SINGLY) and not sold, (got, sold))
got = buy(blade.name, f"I buy the {blade.name}.", item=blade.name)
check("...and asked for once, it is sold, a number in its name being no count", sold == [blade.uid], (got, sold))
del ws.stock_here, ws.buy_stock_item

# a mount, and a house: the same refusal, where each is paid for
g2 = simlib.campaign(NAME + "_b", cls="warrior", seed=5, location="eldervale")
w2 = g2.scene
c2 = w2.player.character
c2.level, c2.coins = 10, money.to_smallest(gold=5000)
pick, price = next(iter(w2.stable_stock()))
n, coins0 = len(SHOWN), c2.coins
w2.halted = False
w2.on_buy(A(kind="buy", ware=pick["name"], count=2), f"buy two of {pick['name']}")
check("a mount asked for twice: refused in a line, nothing is paid, and none is theirs",
      c2.coins == coins0 and not w2.player.mounts and any(SINGLY[0] in t for k, t in SHOWN[n:]), (c2.coins, coins0, w2.player.mounts, SHOWN[n:]))
w2.halted = False
w2.on_buy(A(kind="buy", ware=pick["name"]), f"buy {pick['name']}")
check("...and asked for once, it is theirs", [m["id"] for m in w2.player.mounts] == [pick["id"]] and c2.coins == coins0 - price, (c2.coins, w2.player.mounts))
from engine import property as prop
town = next(t for t in prop.P["homes"] if prop.for_sale(t))
w2.player.location = town
w2.enter(town)
agent = next((n for n in w2.present if n.role == prop.P["agent_role"]), None)
if agent is None:                                                      # the agent keeps hours; the refusal is about the count, not the hour
    agent = next(n for n in w2.present) if w2.present else keeper
    agent = agent.model_copy(update={"role": prop.P["agent_role"]})
    w2.present = [*w2.present, agent]
c2.coins = prop.P["homes"][town]["price"] * 3
n, coins0 = len(SHOWN), c2.coins
w2.halted = False
w2.property_buy(A(kind="buy", ware="a house", count=2), "buy two houses")
check("a house asked for twice: refused in a line, nothing is paid, and none is theirs",
      c2.coins == coins0 and town not in w2.player.homes and any(SINGLY[0] in t for k, t in SHOWN[n:]), (c2.coins, coins0, SHOWN[n:]))
w2.halted = False
w2.property_buy(A(kind="buy", ware="a house"), "buy a house")
check("...and asked for once, it is theirs", town in w2.player.homes and c2.coins < coins0, (c2.coins, coins0, SHOWN[n:]))

g.close()
g2.close()
for name in (NAME, NAME + "_b"):
    shutil.rmtree(f"saves/{name}", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
