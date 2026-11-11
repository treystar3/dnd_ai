"""(f592) Things in the world are saved entities (docs/design/05 section 5.2). A thing a ruling makes for an attempt ("a rope ladder")
is an object lying where it was made, tagged by what it is, its words kept on the place; it can be picked up and carried (in hand, no
pack slot, shown in the inventory), set down elsewhere, picked up again, and is still there after the save is opened again. A heavy
thing is never carried off, and a character's hands hold only so many. A thing that names a good becomes that good in the pack. When a
thing leaves where it was made, the place no longer tells it lying there; set down elsewhere, the narrator is told it lies there.
Unowned things are capped per place and fade when nobody touches them. Two characters carry their own.
Run: python tools/sim/objects_592_test.py"""
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
simlib.quiet_console()
from engine import features, inventory as inv, ledger, objects, ruling
from llm.contracts import Ruling
from scenes import world_prompts as wp
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def rule(**k):
    return Ruling.model_validate({"answer": "", **k}, context={"capabilities": list(ruling.C), "becomes": list(features.F["becomes"])})


g = simlib.campaign("objects_592", location="parth")
ws, store = g.scene, g.store
here = ws.player.location
told = []
ws.narrate = lambda event, text="": told.append(event)
with ws.operation("test", "make room"):
    ledger.begin()
    made = ruling.make_room(ws, rule(sense="yes", needs=[{"kind": "thing", "name": "a rope ladder", "what": "left by a carter, frayed at one end"}]))
rope = objects.find(objects.here(store, here), "the rope ladder")
check("a ruled thing is an object lying where it was made", rope is not None and rope.state == "here" and rope.place == here
      and rope.ref.startswith(f"object:{here}:"), rope)
check("...tagged by what it is (a rope ladder climbs and burns)", rope is not None and {"climbable", "flammable"} <= set(rope.data["tags"]), rope and rope.data)
check("...its words kept on the place, and the turn's record names the thing", any("rope ladder" in m for m in store.load_place(here).marks)
      and any(r.get("ref") == rope.ref for r in ledger.ROWS if r["kind"] == "made"), (store.load_place(here).marks, ledger.ROWS))
check("...and nothing a mark already tells is told again on the ground", ws.lying_here() == [], ws.lying_here())


def act(handler, item, text):
    with ws.operation("action", text):
        handler(types.SimpleNamespace(item=item, count=1), text)


told.clear()
pack = len(ws.player.character.inventory)
act(ws.on_pick_up, "the rope ladder", "I pick up the rope ladder")
rope = store.load_entity(rope.ref)
check("picking it up carries it, the character its owner", rope.state == "carried" and rope.owner == ws.acting, (rope.state, rope.owner))
check("...in hand, no pack slot", len(ws.player.character.inventory) == pack and [o.ref for o in ws.carried_things()] == [rope.ref])
check("...the place no longer tells it lying there", not any("rope ladder" in m for m in store.load_place(here).marks), store.load_place(here).marks)
check("...and the narrator is told the character carries it", told and "rope ladder" in told[-1] and "carries" in told[-1], told)
shown = {}
was_panel = console.panel
console.panel = lambda kind, data: shown.update({kind: data}) or True
console.show_inventory(ws.player.character, ws.carried_things())
console.panel = was_panel
check("the inventory shows what is carried in hand, in the window and the console", [c["name"] for c in shown["inventory"]["carried"]]
      == [rope.name] and "CARRIED IN HAND" in open("ui/console.py", encoding="utf-8").read()
      and "CARRIED IN HAND" in open("ui/gui/web/app.js", encoding="utf-8").read(), shown.get("inventory", {}).get("carried"))

g2 = simlib.campaign("objects_592", fresh=False)
check("it is still carried when the save is opened again", [o.ref for o in objects.carried(g2.store, g2.player.character.id)] == [rope.ref])

elsewhere = next(p for p in ws.world.places if p != here and ws.world.places[p].type not in ("road",))
ws.player.location = elsewhere
told.clear()
act(ws.on_drop, "the ladder", "I drop the ladder")
rope = store.load_entity(rope.ref)
check("setting it down elsewhere leaves it lying there, nobody's", rope.state == "here" and rope.place == elsewhere and rope.owner == ""
      and ws.carried_things() == [], (rope.state, rope.place, rope.owner))
asked = []
real_request = wp.narration_request


def spy(*a, **k):
    asked.append(k.get("ground") if "ground" in k else (a[8] if len(a) > 8 else None))
    return real_request(*a, **k)


wp.narration_request = spy
narrate = ws.narrate
del ws.narrate                                         # the scene's own narration, as play tells a passage
with ws.operation("look", "I look around"):
    ws.narrate("The player looks around.", "I look around")
ws.narrate = narrate
wp.narration_request = real_request
check("...and the narrator, telling the place, is told it lies on the ground there", any(any("rope ladder" in x for x in (g or [])) for g in asked),
      asked)
act(ws.on_pick_up, "rope ladder", "I take the rope ladder again")
check("it can be picked up again", store.load_entity(rope.ref).state == "carried")
check("...and the narrator is told the character holds it, with what they wear and wield", "holding the rope ladder" in ws.gear_line(),
      ws.gear_line())

# ---- a heavy thing, full hands
with ws.operation("test", "more things"):
    rock = objects.make(store, elsewhere, "the boulder", "a grey boulder sunk in the mud", minute=ws.minutes)
    small = [objects.make(store, elsewhere, f"the {n}", "", minute=ws.minutes) for n in ("lantern", "sack", "knife", "jar")]
told.clear()
act(ws.on_pick_up, "the boulder", "I lift the boulder")
check("a heavy thing is never carried off: it stays where it lies, and the narrator is told why", store.load_entity(rock.ref).state == "here"
      and told and "too heavy" in told[-1], told)
for o in small:
    act(ws.on_pick_up, o.name, f"I pick up {o.name}")
held = [o.ref for o in ws.carried_things()]
check("a character's hands hold only so many", len(held) == objects.O["carried_most"] and small[-1].ref not in held
      and store.load_entity(small[-1].ref).state == "here", held)

# ---- a thing that names a good is that good
good = next(iter(inv.GOODS.values()))
with ws.operation("test", "a good"):
    sack = objects.make(store, elsewhere, f"some {good.name}", "", minute=ws.minutes)
    for o in ws.carried_things():                       # hands emptied, so only the good is in question
        objects.drop(store, o, elsewhere, ws.minutes)
count = sum(i.quantity for i in ws.player.character.inventory if i.good == good.id)
act(ws.on_pick_up, good.name, f"I pick up the {good.name}")
check("a thing that names a good goes into the pack as that good, and is no longer a thing lying there (its row gone)",
      sum(i.quantity for i in ws.player.character.inventory if i.good == good.id) == count + 1 and store.load_entity(sack.ref) is None)
check("...named as what it is, never 'the some'", sack.name == f"the {good.name}" and objects.name_of("two coils of rope") == "the coils of rope",
      sack.name)

# ---- the caps: per place, and fading
with ws.operation("test", "caps"):
    spot = "objects_592_field"
    first = [objects.make(store, spot, f"the stone {i}", "", minute=1000 + i) for i in range(objects.O["per_place"] + 2)]
lying = [e.ref for e in objects.here(store, spot)]
check("unowned things past the place's cap go, the oldest untouched first, and their rows with them", len(lying) == objects.O["per_place"]
      and first[0].ref not in lying and first[1].ref not in lying and first[-1].ref in lying and store.load_entity(first[0].ref) is None, lying)
later = 1000 + objects.O["fade_days"] * 1440 + 10
check("...those nobody touched for fade_days are no longer seen, even before anything is written there",
      objects.here(store, spot, later) == [] and objects.lying_unmarked(store, spot, later) == [])
with ws.operation("test", "fade"):
    fresh = objects.make(store, spot, "the new stone", "", minute=later)
check("...and their rows go the next time the place is written", [e.ref for e in objects.here(store, spot)] == [fresh.ref])
with ws.operation("test", "authored"):
    old = objects.make(store, "objects_592_hall", "the old shield", "", made_by="authored", minute=0)
    objects.trim(store, "objects_592_hall", later * 3)
check("...but an authored thing never fades", store.load_entity(old.ref).state == "here")

# ---- two characters, and the lifecycle
with ws.operation("test", "two"):
    a = objects.make(store, "objects_592_two", "the lamp", "", minute=1)
    b = objects.make(store, "objects_592_two", "the lamp", "", minute=1)
    objects.take(store, a, "other_character", 2)
check("two things of one name at one place are two", a.ref != b.ref and b.ref.endswith(":2"))
check("two characters carry their own", [o.ref for o in objects.carried(store, "other_character")] == [a.ref]
      and a.ref not in [o.ref for o in ws.carried_things()])
with ws.operation("test", "broken"):
    objects.change(store, b, "broken", 3, "smashed")
check("a broken thing still lies there, told as broken", any("lamp (broken)" in x for x in objects.lying_unmarked(store, "objects_592_two")))
refused = []
for e, to in ((store.load_entity(b.ref), "hidden"), (store.load_entity(a.ref), "broken"), (store.load_entity(b.ref), "carried")):
    try:
        objects.change(store, e, to, 4)                 # refused before anything is written
    except ValueError:
        refused.append(to)
check("...and a move its lifecycle does not allow is refused: broken things hidden, a thing broken in hand, carried without a carrier",
      refused == ["hidden", "broken", "carried"], refused)

# ---- the place's words and the things: two of a kind, a mark scrolled off, a mark in other letters
with ws.operation("test", "marks"):
    st = store.load_place("objects_592_marks")
    st.marks = ["a lamp: brass"]
    store.save_place(st)
    l1 = objects.make(store, "objects_592_marks", "a lamp", "brass", mark="a lamp: brass", minute=5)
    l2 = objects.make(store, "objects_592_marks", "a lamp", "brass", mark="A lamp: brass", minute=5)
    objects.take(store, l1, ws.acting, 6)
check("two things sharing one mark: taking one leaves the words for the other", store.load_place("objects_592_marks").marks == ["a lamp: brass"]
      and objects.lying_unmarked(store, "objects_592_marks") == [], store.load_place("objects_592_marks").marks)
with ws.operation("test", "marks 2"):
    objects.take(store, store.load_entity(l2.ref), "third_character", 7)
check("...taking the last takes the words off, whatever their letters", store.load_place("objects_592_marks").marks == [])
with ws.operation("test", "scrolled"):
    br = objects.make(store, "objects_592_marks", "the brazier", "cold iron", mark="the brazier: cold iron", minute=8)
check("a thing whose words the place no longer keeps (scrolled off its marks) is told on the ground",
      any("the brazier" in x for x in objects.lying_unmarked(store, "objects_592_marks")), objects.lying_unmarked(store, "objects_592_marks"))
check("fixed and heavy things are never carried off: a wall, a door, an altar", all("heavy" in objects.tags_for(n) for n in ("the wall", "a door", "the altar")))
with ws.operation("test", "full name"):
    for o in ws.carried_things():
        objects.drop(store, o, ws.player.location, ws.minutes)
    lad = objects.make(store, ws.player.location, "a rope ladder", "", minute=ws.minutes)
rope_good = next((gd for gd in inv.GOODS.values() if "rope" in gd.name.lower()), None)
if rope_good is not None:
    ws.player.character.inventory.append(inv.make_good(rope_good.id))
act(ws.on_pick_up, "the rope ladder", "I pick up the rope ladder")
pack_ropes = sum(1 for i in ws.player.character.inventory if rope_good is not None and i.good == rope_good.id)
act(ws.on_drop, "the rope ladder", "I drop the rope ladder")
check("'drop the rope ladder' sets down the ladder in hand, not the pack's rope", store.load_entity(lad.ref).state == "here"
      and sum(1 for i in ws.player.character.inventory if rope_good is not None and i.good == rope_good.id) == pack_ropes)
act(ws.on_pick_up, "the rope ladder", "I pick up the rope ladder")
act(ws.on_discard, "the rope ladder", "I discard the rope ladder")
check("discarding a thing in hand sets it down too", store.load_entity(lad.ref).state == "here")
check("picking one up is recorded as carried in hand, with what it is for a line if its telling fails",
      any(r["kind"] == "carried" and (r.get("facts") or {}).get("what") == "the rope ladder" for r in ledger.ROWS + ledger.LAST), ledger.ROWS[-3:])
check("objects.yaml and the lifecycle pass their startup checks", objects.problems() == [])
was = dict(objects.O)
objects.O.update(per_place=0, tags={k: v for k, v in was["tags"].items() if k != "heavy"})
check("...and a cap of 0 or no 'heavy' fails them", len(objects.problems()) == 2, objects.problems())
objects.O.clear(); objects.O.update(was)

# ---- scenery with nothing behind it is narrated as before
told.clear()
act(ws.on_pick_up, "a smooth grey pebble", "I pick up a smooth grey pebble")
check("scenery that is no thing in the world is narrated, as before", told and "nothing goes into their pack" in told[-1], told)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
