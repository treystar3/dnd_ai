"""(f483, part 1 of 2) How a person is and what is on their mind, each with where it came from and how it ends (Bundle D G5): every mood
is set with its cause and its clock; a matter's worry is released when the matter ends, settled or let go, leaving a line of their own
life, and a goal's when the goal ends; a person changes through identity.revise alone, which keeps how they first looked, caps the
record of changes and leaves one revision row; and a hire's identity is never evicted at its cap: a claim past it waits unsettled."""
import ast
import random
import sys
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 9)
simlib.install(stub)
shown = simlib.quiet_console()
from engine import canon, circumstance, drift, identity, matters, pulse
from npc.models import NPC

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

# ---- every mood is set with its cause and its clock (a fence over the code, and the one writer)
n = NPC(id="m1", name="Ada Kell", people="human", role="farmer", location="parth")
circumstance.set_mood(n, "proud, after the harvest", 1000, "thread:t1")
check("a mood is set with its cause and a clock from data", n.mood_source == "thread:t1" and n.mood_until == 1000 + pulse.P["drift"]["moods"]["days"] * 1440)
loose = []
for d in ("engine", "scenes", "npc", "services"):
    for p in Path(d).rglob("*.py"):
        if str(p) == "engine/circumstance.py":
            continue
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Assign):
                names = [t for t in node.targets] + [e for t in node.targets if isinstance(t, ast.Tuple) for e in t.elts]
                attrs = {t.attr for t in names if isinstance(t, ast.Attribute)}
                if "mood" in attrs and "mood_source" not in attrs:
                    loose.append(f"{p}:{node.lineno}")
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "NPC":
                kws = {k.arg for k in node.keywords}
                if "mood" in kws and "mood_source" not in kws:
                    loose.append(f"{p}:{node.lineno} NPC(mood=)")
check("every mood set or cleared anywhere says what gave it, or lets it go with the mood", loose == [], loose)
circumstance.clear_mood(n)
check("...a faded mood takes what gave it along", (n.mood, n.mood_source, n.mood_until) == ("", "", 0))

# ---- a matter's worry goes with the matter
game = simlib.campaign("circumstances_483", minutes=2000)
store, world = game.store, game.world
holder = NPC(id="h1", name="Bram Coyle", people="human", role="farmer", location="parth")
store.save_npc(holder)
h = store.load_npc("h1")
circumstance.set_concern(h, "The ewes keep going missing.", "th1")
store.save_npc(h)
state = pulse.empty_state(2000)
th = {"id": "th1", "title": "The Missing Ewes", "place": "parth", "groups": ["everyone"], "status": "active", "clues": [{"npc": "h1"}], "sender": ""}
state["threads"] = [th]
state.setdefault("history", [])
pulse.end_thread(store, state, th, "resolved", "The Missing Ewes - settled.", 2100)
after = store.load_npc("h1")
check("a settled matter clears the worry it gave, and says it was settled", after.concern == "" and after.concern_state == "settled", (after.concern, after.concern_state))
check("...leaving a line of their own life", any(m.kind == "own_life" and "Missing Ewes" in m.text for m in after.memories), [m.text for m in after.memories])
other = store.load_npc("h1")
circumstance.set_concern(other, "My brother owes me.", "profile")
check("a worry from something else is not released by the matter", not circumstance.release_concern(other, "th1", "settled", 2200) and other.concern)

# ---- a goal's worry goes with the goal
g = NPC(id="g1", name="Cass Wyn", people="human", role="farmer", location="parth", motive="buy the mill")
circumstance.set_concern(g, "Saving for the mill.", "motive")
drift.motive_ends(g, store, world, {"made_chance": 1.0, "outcomes": {"made": ["{name} bought it."], "mood_made": ["pleased"]}}, {"days": 6}, 3000,
                  random.Random(1))
check("a goal's end releases the worry it gave, settled when it was made, and the mood says what gave it", g.concern == "" and g.concern_state == "settled"
      and g.mood_source == "motive" and g.mood == "pleased", (g.concern, g.concern_state, g.mood_source))

# ---- the guild contractor who settled a matter off-screen is proud of it, and says what of
store.save_npc(NPC(id="gc1", name="Orla Venn", people="human", role="guild_contractor", location="parth"))
th2 = {"id": "th2", "title": "The Broken Weir", "place": "parth", "times": [2000, 2300]}
said = next((r for r in (pulse.resolver(store, world, th2, random.Random(i), 2300) for i in range(60)) if r.endswith("a guild contractor")), "")
gc = store.load_npc(store.npc_rows(role="guild_contractor", gone=False)[0].id) if said else None
check("a contractor's mood from a matter they settled says which matter, with its clock", gc is not None and gc.mood_source == "thread:th2"
      and gc.mood_until == 2300 + pulse.P["drift"]["moods"]["days"] * 1440, (said, gc and (gc.mood, gc.mood_source, gc.mood_until)))

# ---- a job's worry is settled when the job is done, and let go when the stranger drops it
j = store.load_npc("h1")
circumstance.set_concern(j, "Someone has to clear the well.", "quest:q9")
store.save_npc(j)
game.scene.contract_dropped({"id": "q9", "issuer": "h1", "title": "Clear the Well"}, "abandoned")
j = store.load_npc("h1")
check("a job the stranger dropped is let go from the issuer's mind, not settled", j.concern == "" and j.concern_state == "let_go", (j.concern, j.concern_state))
game.close()
import shutil
shutil.rmtree("saves/circumstances_483", ignore_errors=True)

# ---- a person changes through identity.revise alone: first look kept, one revision row, the record of changes capped
from npc.traits import load_traits
cat = load_traits()
r = NPC(id="r1", name="Dov Pell", people="human", role="smith", location="parth", description="A wiry smith with burnt forearms.",
        personality="Short-tempered and proud.", traits=[])
cat_traits = list(cat.traits)
r.traits = [cat_traits[0]]
add = next(t for t in cat_traits[1:] if cat.fits(t, []))
for i in range(12):
    remove = r.traits[0]
    nxt = next(t for t in cat_traits if t != remove and cat.fits(t, []))
    identity.revise(r, cat, remove, nxt if i % 2 == 0 else add if add != remove else nxt, f"what happened, number {i}", 5000 + i)
revs = [m for m in r.memories if m.kind == "revision"]
check("each change leaves one revision row, of how they changed and why", len(revs) == 12 and "number 11" in revs[-1].text, [m.text for m in revs][-1:])
w = NPC(id="r2", name="Esk Varr", people="human", role="smith", location="parth", traits=["set_in_ways"])
identity.revise(w, cat, "set_in_ways", next(t for t in cat_traits if t not in ("set_in_ways",) and cat.fits(t, [])), "the fire at the forge", 6000)
check("...told in their own words, never the trait's id", "set in my ways" in w.memories[-1].text and "_" not in w.memories[-1].text, w.memories[-1].text)
check("...the first look is kept and who they are otherwise stands", r.first_description == "A wiry smith with burnt forearms." and r.personality == "Short-tempered and proud.")
check("...and the record of changes is capped in data", len(r.trait_history) == identity._cap(), len(r.trait_history))
writes = []
for d in ("engine", "scenes", "npc", "services"):
    for p in Path(d).rglob("*.py"):
        if str(p) in ("npc/traits.py", "engine/identity.py"):
            continue
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", "")) == "change_trait":
                writes.append(f"{p}:{node.lineno}")
check("nothing changes a trait but identity.revise", writes == [], writes)

# ---- a hire's identity is never evicted at its cap: a claim past it waits unsettled
cap = canon.BUCKETS["backstory"]["cap"]
m = {"id": "h9", "name": "Ghak Skurz", "canon": [{"text": f"My {i}th memory of home is the river.", "day": 1} for i in range(cap)], "memories": []}
canon.review(m, ["My mother kept bees on the hill above the ford."], [], 9, who="Ghak Skurz").commit()
check("a hire's identity at its cap keeps every claim it held", len(m["canon"]) == cap and m["canon"][0]["text"].startswith("My 0th"), len(m["canon"]))
check("...and the new one waits unsettled, never dropped", any("bees" in x["text"] for x in m.get("unsettled", [])), m.get("unsettled"))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
