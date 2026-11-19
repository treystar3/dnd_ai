"""(f740) An enchantment spends one of its reagent, and a thing that stacks leaves the pack only through a writer that counts.

The question the player answers says a fee "and a raw" material: one. enchant() took the reagent's whole Item out of the pack, and a
stack of five raw bear hide went for one binding. It now spends one through the writer crafting already uses (crafting.use_material:
a count off the stack, the Item gone only at zero), for a binding that takes and one that fails alike. The case that found it: five
bear hide picked up one at a time (inventory.add, one stack), one enchantment, nothing left. Second cases: a failed binding leaves
four; twelve held as a stack of ten and a stack of two leave eleven; a general enchantment touches no stack; the last one held goes
with its Item; and the same through the scene's #enchant and its yes, the saved pack read back.

The fence for the kind: every place in engine/, scenes/ and services/ that takes an Item out of a list held under a pack's name
(pack, inventory, bag, stash) by identity (.remove, .pop, .clear, del, or the list rebuilt from itself through a filter) is named in a
table with why it is right; a new one fails until it is named, and a named one that is gone is taken out. It knows a pack only by
those names: a pack held under another local name, or rebuilt through a filtered local and then assigned back, is not seen (none is
today), so whoever adds such a shape extends the walk. And the startup check: a
good whose Item carries its own state (a codex its spell) is one to a slot, since the place that spends it takes the Item whole."""
import ast
import random
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
from ui import console
from engine import data_check, enchanting, inventory, items
bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok:
        bad.append(n)


class Roll:
    """A die that always shows the same face: 0 binds (under any chance), 100 fails (at or over every chance)."""
    def __init__(self, face):
        self.face = face

    def uniform(self, a, b):
        return self.face


def stacks(c) -> list[int]:
    return [i.quantity for i in c.inventory if i.base == "raw_material" and i.material == "bear_hide"]


def holding(n: int):
    """A warrior with a rare blade to enchant and n raw bear hide, picked up one at a time as loot gives them."""
    c, spec = simlib.make_character("warrior", random.Random(1))
    c.coins = 10 ** 7
    blade = items.make(spec["weapon"], "rare", 5)
    c.inventory.append(blade)
    for _ in range(n):
        assert inventory.add(c.inventory, items.make_raw("bear_hide"), 40) is None
    return c, blade


ESSENCE = enchanting.OPTIONS["bear_hide_weapon"]

# ---- the case that found it: five in one stack, one enchantment
c, blade = holding(5)
check("five bear hide picked up one at a time are one stack of five", stacks(c) == [5], stacks(c))
coins, fee = c.coins, enchanting.fee(blade, ESSENCE)
ok, msg = enchanting.enchant(c, blade, ESSENCE, Roll(0))
check("one enchantment binds and spends one: four are left, in the same stack", ok and stacks(c) == [4], (ok, msg, stacks(c)))
check("...and the fee is taken once", coins - c.coins == fee > 0, (coins - c.coins, fee))

# ---- second cases
c, blade = holding(5)
ok, msg = enchanting.enchant(c, blade, ESSENCE, Roll(100))
check("a binding that fails spends one too: four are left", not ok and "binding fails" in msg and stacks(c) == [4], (ok, msg, stacks(c)))

c, blade = holding(12)
check("twelve are held as a stack of ten and a stack of two", sorted(stacks(c)) == [2, 10], stacks(c))
enchanting.enchant(c, blade, ESSENCE, Roll(0))
check("...and one enchantment leaves eleven", sum(stacks(c)) == 11 and len(stacks(c)) == 2, stacks(c))

c, blade = holding(5)
c.inventory.append(inventory.make_good("healing_draught", 3))
before = [(i.uid, i.quantity) for i in c.inventory]
keen = enchanting.OPTIONS["keen"]
ok, msg = enchanting.enchant(c, blade, keen, Roll(0))
check("a general enchantment with no reagent leaves every stack alone", ok and not keen.reagent and [(i.uid, i.quantity) for i in c.inventory if i is not blade]
      == [(u, q) for u, q in before if u != blade.uid], (ok, msg, before, [(i.uid, i.quantity) for i in c.inventory]))

c, blade = holding(1)
ok, msg = enchanting.enchant(c, blade, ESSENCE, Roll(0))
check("the last one held goes with its Item: no empty stack is left behind", ok and stacks(c) == [] and not any(i.quantity <= 0 for i in c.inventory),
      (ok, stacks(c)))
check("...and a second binding of the essence is refused for want of one", enchanting.check(c, blade, ESSENCE) == "You need a raw bear hide.",
      enchanting.check(c, blade, ESSENCE))

# ---- the same through the scene: #enchant, its question, and the yes; the saved pack read back
g = simlib.campaign("reagent_stack_740", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
shown = simlib.quiet_console()
ws.enter("parth")
c = ws.player.character
c.coins = 10 ** 7
for _ in range(5):
    inventory.add(c.inventory, items.make_raw("bear_hide"), 40)
worn = c.equipment["main_hand"]
pick = [o.id for o in enchanting.available(c, worn)].index("bear_hide_weapon") + 1
enchanter = ws.residents[0]
enchanter.role = "enchanter"                                      # someone here binds for a fee
store.save_npc(enchanter)
ws.present = [enchanter]
store.save_player(ws.player)
coins, fee = c.coins, enchanting.fee(worn, ESSENCE)
shown.clear()
script = [f"#enchant 1 {pick}", "yes", "quit"]
console.put("ask", lambda *a, **k: script.pop(0) if script else "quit")
ws.run()
texts = [t for k, t in shown]
saved = store.load_player().character
check("the scene asks for the fee and one raw bear hide", any("and a raw bear hide?" in t for t in texts), texts[:4])
check("...the yes binds it (or fails it) and the saved pack holds four", any(t.startswith(("The enchantment takes", "The binding fails")) for t in texts)
      and stacks(saved) == [4], (texts[:4], stacks(saved)))
check("...and the fee was taken once", coins - saved.coins == fee > 0, (coins - saved.coins, fee))
g.close()
shutil.rmtree("saves/reagent_stack_740", ignore_errors=True)

# ---- the fence: a thing leaves a pack's list by identity only where the table says why that is right
ROOT = Path(__file__).resolve().parent.parent.parent
PACKS = {"pack", "inventory", "bag", "stash"}
NAMED = {
    ("engine/inventory.py", "take", "bag.remove(first)"): "the counted writer: a thing that does not stack is the whole of itself",
    ("engine/inventory.py", "take", "bag.remove(have)"): "the counted writer: a stack leaves once it is down to nothing",
    ("engine/inventory.py", "remove_goods", "bag.remove(have)"): "the counted writer: a stack leaves once it is down to nothing",
    ("engine/crafting.py", "use_material", "bag.remove(i)"): "the counted writer: a stack leaves once it is down to nothing",
    ("scenes/field_actions.py", "field_salvage", "self.pack.remove(item)"): "gear picked for salvage: one piece, and gear never stacks",
    ("scenes/shop_actions.py", "take_stack", "self.pack.remove(first)"): "a whole stack sold on purpose (the pane's sell): a thing that does not stack",
    ("scenes/shop_actions.py", "take_stack", "self.pack.remove(have)"): "a whole stack sold on purpose (the pane's sell): every stack of it",
    ("scenes/spell_actions.py", "read_codex", "self.pack.remove(item)"): "a codex: its Item holds its own spell and is one to a slot (goods_problems)",
    ("engine/equipment.py", "equip", "c.inventory rebuilt"): "gear being worn: the piece moves from the pack to its slot",
}


def held_as(node) -> str:
    """The name a list is held under: bag, self.pack, c.inventory, self.player.stash."""
    return node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute) else ""


def rebuilt_from_a_pack(value) -> bool:
    """A value made from a pack's list through a filter: a comprehension over it with an `if`, or filter() over it."""
    for n in ast.walk(value):
        if isinstance(n, (ast.ListComp, ast.GeneratorExp)) and any(held_as(gen.iter) in PACKS and gen.ifs for gen in n.generators):
            return True
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "filter" and len(n.args) == 2 and held_as(n.args[1]) in PACKS:
            return True
    return False


def sites(tree) -> list[tuple[str, int, str]]:
    """(function, line, what) for every place an Item leaves a pack's list by identity."""
    parents = {ch: p for p in ast.walk(tree) for ch in ast.iter_child_nodes(p)}

    def within(node) -> str:
        p = parents.get(node)
        while p is not None and not isinstance(p, (ast.FunctionDef, ast.AsyncFunctionDef)):
            p = parents.get(p)
        return p.name if p is not None else "<module>"

    out = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr in ("remove", "pop", "clear") \
                and held_as(n.func.value) in PACKS:
            out.append((within(n), n.lineno, ast.unparse(n)))
        elif isinstance(n, ast.Delete):
            for t in n.targets:
                if isinstance(t, ast.Subscript) and held_as(t.value) in PACKS:
                    out.append((within(n), n.lineno, f"del {ast.unparse(t)}"))
        elif isinstance(n, (ast.Assign, ast.AnnAssign)) and n.value is not None:
            for t in (n.targets if isinstance(n, ast.Assign) else [n.target]):
                held = t.value if isinstance(t, ast.Subscript) else t           # bag[:] = ... is the bag rebuilt in place
                if (isinstance(held, ast.Attribute) or isinstance(t, ast.Subscript)) and held_as(held) in PACKS and rebuilt_from_a_pack(n.value):
                    out.append((within(n), n.lineno, f"{ast.unparse(held)} rebuilt"))       # a local rebound is a copy, not the pack
    return sorted(out, key=lambda s: s[1])


found = {}
for folder in ("engine", "scenes", "services"):
    for path in sorted((ROOT / folder).rglob("*.py")):
        name = path.relative_to(ROOT).as_posix()
        for fn, line, what in sites(ast.parse(path.read_text(encoding="utf-8"))):
            found.setdefault((name, fn, what), []).append(line)
new = {f"{k[0]}:{v[0]} {k[1]}: {k[2]}": v for k, v in found.items() if k not in NAMED}
check("every place a thing leaves a pack by identity is named with why it is right (a new one: spend through a counted writer, or name it)",
      not new, new)
gone = [k for k in NAMED if k not in found]
check("...and every named place is still there (one that is gone is taken out of the table)", not gone, gone)
check("enchanting.py takes nothing out of a pack by identity", not any(k[0] == "engine/enchanting.py" for k in found),
      [k for k in found if k[0] == "engine/enchanting.py"])
probe = ast.parse("def f(c, x):\n    c.inventory = [i for i in c.inventory if i.uid != x.uid]\n    c.stash.pop(0)\n    del self.pack[0]\n"
                  "    bag.remove(x)\n    keys.remove(x)\n    bag = [i for i in c.inventory if i.good]\n")
check("the walk sees a rebuild by uid, a pop, a del and a remove on a pack, and not a key list or a filtered copy into a local",
      [w for _, _, w in sites(probe)] == ["c.inventory rebuilt", "c.stash.pop(0)", "del self.pack[0]", "bag.remove(x)"], sites(probe))

# ---- the startup check: a good whose Item carries its own state is one to a slot
gp = getattr(data_check, "goods_problems", None)
check("goods.yaml holds every good that carries its own state at one to a slot", gp is not None and gp() == [], gp() if gp else "no goods_problems")
broken = [{"id": "codex", "name": "sealed codex", "kind": "codex", "price": 50000, "stack": 5},
          {"id": "tome_x", "name": "tome", "kind": "book", "price": 1, "stack": 5},
          {"id": "codex_two", "name": "another codex", "kind": "codex", "price": 1}]
p = gp(broken) if gp else []
check("...and a codex that stacks is named, with one left at the default stack, and a book that stacks is not",
      len(p) == 2 and any("codex:" in x for x in p) and any("codex_two" in x for x in p) and not any("tome_x" in x for x in p), p)
dc = ast.parse((ROOT / "engine/data_check.py").read_text(encoding="utf-8"))
runs = [n for f in dc.body if isinstance(f, ast.FunctionDef) and f.name == "check" for n in ast.walk(f)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "goods_problems"]
check("the startup check runs it: check() calls goods_problems()", bool(runs))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
