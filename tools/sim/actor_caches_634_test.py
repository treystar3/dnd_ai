"""(f634) The actor's caches (docs/design/20_phase3_plan.md; engine/actor.py Caches).
What a scene keeps for the character it plays, between lines, was held by five modules under names of their own: the journal
the canon writes to, the ids behind names, what became of each claim and the drafts under review (engine/canon.py), the
companions' pronouns (engine/names.py), the stand-in line said last of each kind (engine/failures.py), the dropped-question
line said last (engine/questions.py) and the enchanter's discount (engine/enchanting.py). They are one object the actor points
at, every actor's the process's one while a scene has one character. Held here:
- every cache written through its module's functions is named by the session's residue and gone after its reset;
- each module's functions read what was set through them: an id behind a name, a fact journaled, a pronoun mended, a line not
  said twice running, a fee discounted (a draft under review is stood in for here: what reads it is not this test's);
- a scene fills them for its character (the party's ids, the mentor's and the character's own; the journal; the cast);
- two actors given caches of their own keep their names, their journals, their pronouns and their discounts apart;
- closing the campaign leaves nothing in them.
The old names are gone, for a reader and a writer, in every file of the repository: tools/sim/registers_633_test.py holds
that fence for these names with f633's, and tools/sim/owned_state_633_test.py holds the table's rows.
Run: python tools/sim/actor_caches_634_test.py"""
import random
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
restore = simlib.install(stub)
from core.models import Item
from engine import actor, canon, enchanting, failures, mentor, names, questions, session

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

simlib.quiet_console()


def held():
    """The caches the session's residue names."""
    return sorted(k for k in session.residue() if k.startswith("caches."))


# ---- one object, the process's while no actor has its own
C = actor.caches()
session.reset()
check("with no actor bound the caches are the process's one, and a scene's actor shares it", C is actor.PROCESS.caches and actor.ActorContext().caches is C)
check("a set just put back holds nothing", C.held() == {} and held() == [], (C.held(), held()))

# ---- every cache, written through its module's functions, is the session's to put back
during = []
real_keep = canon._keep_into


def keeping(*a, **k):                                      # a draft under review: its events wait in the sink meanwhile
    during.extend(held())
    canon._event("Bram Voss", "a draft's claim", "kept")
    return []


def review():
    canon._keep_into = keeping
    try:
        return canon.review({"name": "Bram Voss"}, [], [], day=1)
    finally:
        canon._keep_into = real_keep


WRITERS = {
    "journal": lambda: canon.bind_journal(lambda *a: None),
    "ids": lambda: canon.set_ids({"Bram Voss": "h1"}),
    "events": lambda: canon._event("Bram Voss", "I was a smith once", "kept"),
    "sink": lambda: (review(), list(during))[1],
    "cast": lambda: names.set_cast({"Odly": "she"}),
    "said_failure": lambda: failures.not_taken(random.Random(1)),
    "said_question": lambda: questions.dropped(random.Random(1)),
    "discount": lambda: enchanting.set_discount(10),
}
check("every cache has a writer here", set(WRITERS) == set(actor.Caches.FRESH), set(WRITERS) ^ set(actor.Caches.FRESH))
for name, write in WRITERS.items():
    session.reset()
    try:
        got = write()
        named = got if name == "sink" else held()
    except Exception as e:
        named = [repr(e)]
    session.reset()
    check(f"{name}: written through its module it is named by the session's residue, and gone after the reset",
          f"caches.{name}" in named and held() == [] and C.held() == {}, (named, held()))
check("a draft's sink is empty again once its review is over", C.sink == [], C.sink)

# ---- each module's functions read what was set through them
session.reset()
given = {"Bram Voss": "h1", "Isel Quill": "h2"}
canon.set_ids(given)
given["Tam"] = "h3"
check("the ids set are a copy of what was given: adding to that afterwards names nobody", canon.about_id("Tam") == "Tam", canon.ids())
check("the id behind a name is the one set, by the whole name or the first, and a stranger is their own name",
      (canon.about_id("Bram Voss"), canon.about_id("isel"), canon.about_id("Tam"), canon.about_id("the player")) == ("h1", "h2", "Tam", "player"),
      (canon.about_id("Bram Voss"), canon.about_id("isel"), canon.about_id("Tam")))
mine = canon.ids()
mine["Tam"] = "h3"
check("the ids are read as a copy: changing it changes nothing", canon.about_id("Tam") == "Tam" and "Tam" not in canon.ids(), canon.ids())
rows = []
check("with no journal bound a fact goes nowhere, and says so", canon.journal_bound() is None and canon.journal("deed", "player", "h1", "a deed") is None)
sink = lambda kind, who, target, text, data: rows.append((kind, who, target, text, data))
canon.bind_journal(sink)
canon.journal("deed", "player", "h1", "a deed done", weight=2)
check("a fact is journaled through the journal bound", canon.journal_bound() is sink and rows == [("deed", "player", "h1", "a deed done", {"weight": 2})], rows)
canon._event("Bram Voss", "I was a smith once", "kept")
check("what became of a claim is read as it was kept, and cleared when asked", canon.events() == [{"who": "Bram Voss", "claim": "I was a smith once",
      "verdict": "kept", "against": ""}] and (canon.clear_events(), canon.events())[1] == [], canon.events())
for i in range(260):
    canon._event("Bram Voss", f"claim {i}", "kept")
check("...and only the last two hundred are kept", len(canon.events()) == 200 and canon.events()[-1]["claim"] == "claim 259", len(canon.events()))
canon.clear_events()
draft = review()
check("a draft's claims wait while it is under review: none is kept until it is committed, and then they are",
      canon.events() == [] and [e["claim"] for e in draft.events] == ["a draft's claim"]
      and (draft.commit(), [e["claim"] for e in canon.events()])[1] == ["a draft's claim"], (draft.events, canon.events()))
canon.Pending({"name": "Bram Voss"}, {}, [], [{"who": "Bram Voss", "claim": f"c{i}", "verdict": "kept", "against": ""} for i in range(260)]).commit()
check("...and a committed draft's are capped with the rest", len(canon.events()) == canon.EVENTS_KEEP == 200, len(canon.events()))
names.set_cast({"Odly": "she", "Bram": "he", "Wisp": "they", "": "she"})
check("the cast is the companions who are he or she", names.cast() == {"Odly": "she", "Bram": "he"}, names.cast())
check("...and a line that calls her him is mended on the way to the screen", names.mend_pronouns("Odly lowers his blade.") == "Odly lowers her blade.",
      names.mend_pronouns("Odly lowers his blade."))
names.set_cast({})
check("...and left alone with no cast", names.mend_pronouns("Odly lowers his blade.") == "Odly lowers his blade.")
rng = random.Random(7)
said = [failures.not_taken(rng) for _ in range(40)]
check("a stand-in line is never the one said last of its kind", len(failures.F["turn_not_taken"]) > 1 and all(a != b for a, b in zip(said, said[1:])), said[:4])
asked = [questions.dropped(rng) for _ in range(40)]
check("...nor is the line for a dropped question", len(questions.Q["dropped"]) > 1 and all(a != b for a, b in zip(asked, asked[1:])), asked[:4])
ring = Item(uid="ring_634", base="ring", name="a plain ring", rarity="rare", item_level=10)
option = next(iter(enchanting.OPTIONS.values()))
full = enchanting.fee(ring, option)
enchanting.set_discount(50)
half = enchanting.fee(ring, option)
enchanting.set_discount(100)
check("the enchanter's fee is discounted by what was set: half at fifty, nothing at a hundred", full > 0 and abs(half - full / 2) <= 1
      and enchanting.fee(ring, option) == 0 and enchanting.discount() == 100, (full, half, enchanting.fee(ring, option)))
enchanting.set_discount(12.5)
check("...and a discount that is not a whole number is taken as it is", enchanting.discount() == 12.5 and enchanting.fee(ring, option) < full, enchanting.discount())
session.reset()
check("...and whole again once the session has put it back", enchanting.fee(ring, option) == full and enchanting.discount() == 0)

# ---- a scene fills them for its character
BASE = Path("saves/actor_caches_634")
shutil.rmtree(BASE, ignore_errors=True)
g = simlib.campaign("actor_caches_634", cls="warrior", seed=3, location="parth")
ws, store = g.scene, g.store
ws.player.party.append({"id": "h7", "name": "Odly Marsh", "pronoun": "she", "permanent": True, "kind": "hire"})
ws.player.character.id = "vessa"
ws.name_ids()
who = ws.player.character.name
check("a scene names who is who for its character: the party, the mentor, and the character by their own id",
      (canon.about_id("Odly Marsh"), canon.about_id(mentor.NAME), canon.about_id(who)) == ("h7", "maren", "vessa"), canon.ids())
before = store._db.execute("SELECT count(*) FROM event_log").fetchone()[0]
canon.journal("deed", "vessa", "h7", "a deed for the test")
last = store._db.execute("SELECT kind, actor, target, text FROM event_log ORDER BY seq DESC LIMIT 1").fetchone()
check("...binds the journal to its save", store._db.execute("SELECT count(*) FROM event_log").fetchone()[0] == before + 1
      and tuple(last) == ("deed", "vessa", "h7", "a deed for the test"), tuple(last))
check("...and keeps its permanent companions' pronouns", names.cast().get("Odly") == "she", names.cast())
ws.has = lambda key: 15 if key == "arcane_appraiser" else 0
ws.owns = lambda key: False
with actor.bind(ws.actor):
    ws.enchant_command("")
del ws.has, ws.owns
check("...and the discount its character's passives give, before any fee is shown", enchanting.discount() == 15, enchanting.discount())
check("while it plays the residue names them", {"caches.ids", "caches.journal", "caches.cast", "caches.discount"} <= set(held()), held())
g.close()
check("closing the campaign leaves nothing in the caches", C.held() == {} and simlib.residue() == {} and canon.about_id("Odly Marsh") == "Odly Marsh",
      (C.held(), simlib.residue()))

# ---- two actors with caches of their own
one, two = actor.ActorContext(caches=actor.Caches()), actor.ActorContext(caches=actor.Caches())
ones, twos = [], []
with actor.bind(one):
    canon.set_ids({"Bram Voss": "h1"})
    canon.bind_journal(lambda *a: ones.append(a[:3]))
    names.set_cast({"Odly": "she"})
    enchanting.set_discount(50)
    first = failures.not_taken(random.Random(1)), questions.dropped(random.Random(1))
    with actor.bind(two):
        apart = dict(id=canon.about_id("Bram Voss"), journal=canon.journal_bound(), cast=names.cast(), discount=enchanting.discount(), events=canon.events())
        canon.set_ids({"Bram Voss": "x9"})
        canon.bind_journal(lambda *a: twos.append(a[:3]))
        names.set_cast({"Odly": "he"})
        canon.journal("deed", "two", "x9")
        canon._event("Bram Voss", "two's claim", "kept")
        theirs = (canon.about_id("Bram Voss"), names.mend_pronouns("Odly draws herself up."), enchanting.fee(ring, option),
                  [e["claim"] for e in canon.events()], (failures.not_taken(random.Random(1)), questions.dropped(random.Random(1))))
    canon.journal("deed", "one", "h1")
    back = (canon.about_id("Bram Voss"), names.cast(), enchanting.fee(ring, option), canon.events())
    draft = review()
    drafted = ([e["claim"] for e in draft.events], canon.events())
check("two actors given caches of their own: the second finds no name, no journal, no cast, no discount and no claim of the first's",
      apart == dict(id="Bram Voss", journal=None, cast={}, discount=0, events=[]), apart)
check("...each keeps its own names, journal, pronouns, price and claims", theirs[0] == "x9" and "himself" in theirs[1] and theirs[2] == full
      and theirs[3] == ["two's claim"] and back == ("h1", {"Odly": "she"}, half, []) and ones == [("deed", "one", "h1")]
      and twos == [("deed", "two", "x9")], (theirs, back, ones, twos))
check("...the line said last is each one's own: the second, new to them, may say the very lines the first just said", theirs[4] == first, (first, theirs[4]))
check("...and a draft reviewed for one waits in that one's sink", drafted == (["a draft's claim"], []), drafted)
check("...and neither wrote the process's", C.held() == {}, C.held())

restore()
shutil.rmtree(BASE, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
