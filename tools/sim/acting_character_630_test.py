"""(f630) One helper for a character's record by id, and no literal "player" where the character's id is meant
(docs/design/20_phase3_plan.md; docs/design/17 M0). Code that is handed a character's id reads that character's place and sheet
through the scene's player_of(id), never the scene's one player: with a second record stood behind the helper, the act's means, its
targets, its body and its deed are that record's, and an id the scene does not hold is refused, not answered with someone else's.
Where the game wrote the id as the word "player" (the journal's "lately", a hire's memory, a companion's reaction to a deed, a
memory's default subject) it writes the character's own id: shown with a character whose id is not that word.
Then the fences. No function that takes a character's id reads the scene's player, its place or its acting id; the three modules
of the act read the player nowhere;
the reads left in the engine and the literal "player" strings left in the game's code (a fight's side apart) are counted per file,
and a count only falls.
Run: python tools/sim/acting_character_630_test.py"""
import ast
import shutil
import sys
from pathlib import Path
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
import config
from engine import act, body, brief, canon, memory, objects, quirks, ruling, targets, truth
from llm.gateway import LLMError

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def refused(fn) -> bool:
    try:
        fn()
        return False
    except ValueError:
        return True


g = simlib.campaign("acting_character_630", cls="warrior", seed=3, location="trading_square")
ws, store = g.scene, g.store
config.TURN_LOG_PATH = "saves/acting_character_630/turns.jsonl"
ws.enter("trading_square")

# ---- the helper, with the scene's one character
check("the record of the acting character is the scene's player", ws.player_of(ws.acting) is ws.player)
check("an id the scene holds no character for is refused", refused(lambda: ws.player_of("nobody")))
was = ws.player
with ws.operation("test", "a failing step") as op:
    raise LLMError("the model failed")
check("after a failed operation reloads the player, the helper gives the new record", op.state == "rolled_back" and ws.player is not was
      and ws.player_of(ws.acting) is ws.player)

# ---- a second record stood behind the helper: id-taking code reads that record, not the scene's
elsewhere = next(p for p in sorted(ws.world.places) if p != ws.player.location and not ws.world.places[p].danger)
other = simlib.stood_beside(ws, "another", location=elsewhere, party=[{"id": "h9", "name": "Dara Holt", "role": "scout"}])
other.character.capabilities = ["flight"]
other.character.attributes.strength = ws.player.character.attributes.strength + 6
with ws.operation("test", "a thing lying elsewhere") as op:
    lying = objects.make(store, elsewhere, "a dented kettle", "left by the road", minute=ws.minutes)
try:
    check("an act's means are those of the character named", "flight" in act.means(ws, "another") and "flight" not in act.means(ws, ws.acting),
          (act.means(ws, "another"), act.means(ws, ws.acting)))
    check("...and so are the road ruling's", "flight" in ruling.means_of(ws, "another") and "flight" not in ruling.means_of(ws, ws.acting))
    theirs, mine = targets.targets_for(ws, "another"), targets.targets_for(ws, ws.acting)
    check("what an act can name is what lies where that character stands, and their own companions",
          any(t.ref == lying.ref for t in theirs.rows) and not any(t.ref == lying.ref for t in mine.rows)
          and any(t.ref == "h9" for t in theirs.rows) and not any(t.ref == "h9" for t in mine.rows), (theirs.lines()[:8], mine.lines()[:8]))
    check("the body an act is judged by is that character's", act.own_body(ws, "another") == body.of_character(other.character)
          and act.own_body(ws, "another") != act.own_body(ws, ws.acting))
    check("the deed an act leaves is done where that character stands", act.acted(ws, "another")["place"] == elsewhere
          and act.acted(ws, ws.acting)["place"] == ws.player.location, act.acted(ws, "another"))
    asked = {"the act's": act.request(ws, "another", theirs, "leap", "I leap."), "the road's": ruling.request(ws, "another", "leap", "I leap.")}
    check("the request for a ruling describes that character's sheet, on either path",
          all("flight" in a.split("WHAT THEY CAN DO BEYOND THE ORDINARY:")[1].splitlines()[0] for a in asked.values()))
    check("...and the place where that character stands", all(a.startswith(f"PLACE: {ws.world.places[elsewhere].name} ") for a in asked.values())
          and ws.place.name != ws.world.places[elsewhere].name, [a.splitlines()[0] for a in asked.values()])
finally:
    del ws.player_of
STRANGER = {"act.means": lambda: act.means(ws, "nobody"), "targets_for": lambda: targets.targets_for(ws, "nobody"),
            "act.own_body": lambda: act.own_body(ws, "nobody"), "ruling.means_of": lambda: ruling.means_of(ws, "nobody"),
            "act.acted": lambda: act.acted(ws, "nobody"), "act.take_up": lambda: act.take_up(ws, "nobody", "x") or act.act(ws, "nobody", "x", "x"),
            "ruling.odds": lambda: ruling.odds(ws, "nobody", "attempt", {}), "brief.pronoun": lambda: brief.pronoun(ws, "nobody"),
            "ws.dies": lambda: ws.dies("nobody")}
check("an id the scene does not hold is refused by each of them, never answered with the scene's own character",
      all(refused(fn) for fn in STRANGER.values()), [k for k, fn in STRANGER.items() if not refused(fn)])

# ---- the character's id where the word "player" stood: a character whose id is not that word
ws.player.character.id = "vessa"
check("(the scene's character now goes by another id)", ws.acting == "vessa" and ws.player_of("vessa") is ws.player
      and refused(lambda: ws.player_of("player")))
here = ws.player.location
with store.transaction():
    store.journal(ws.minutes, "theft", "vessa", "m1", "took a silver cup from a stall", {"place": here, "witnesses": ["m1"]})
    store.journal(ws.minutes, "theft", "player", "m1", "took a brass bell from a stall", {"place": here, "witnesses": ["m1"]})
lately = [f.text for f in truth.Scene(ws).facts("lately")]
check("what was done here lately is what the scene's characters did, by their ids", any("silver cup" in t for t in lately), lately)
check("...a row whose actor is no character of the scene is no deed of theirs", not any("brass bell" in t for t in lately), lately)
lived = memory.hire_row({"day": 2, "text": "Stood the night watch with them.", "weight": 2, "count": 1, "kind": "event"}, "vessa")
told = memory.hire_row({"day": 2, "text": "They come from the coast.", "weight": 1, "count": 1, "kind": "fact"}, "vessa")
check("a hire's memory is about the character who hired them, and a thing told to them was told by that character",
      lived["subject"] == "vessa" and lived["source"] == "self" and told["subject"] == "vessa" and told["source"] == "vessa", (lived, told))
ws.player.party = [{"id": "h1", "name": "Bram Voss", "role": "guard", "bond": 20,
                    "memories": [{"day": 2, "text": "Stood the night watch with them.", "weight": 2, "count": 1, "kind": "event"}]}]
with ws.operation("test", "the player saved with a hire") as op:
    store.save_player(ws.player)
kept = memory.records(store, "hire:h1")
check("...and so it is written when the player is saved", op.state == "committed" and kept and all(r["subject"] == "vessa" for r in kept), kept)
townsman = ws.residents[0]
try:
    memory.keep(townsman, "Something happened.", day=1, turn=1)
    defaulted = True
except TypeError:
    defaulted = False
check("a memory has no default subject: whoever keeps one says whom it is about", not defaulted)
journal_was = canon.journal_bound()
rows = []
canon.bind_journal(lambda kind, actor, target, text, data: rows.append((kind, actor, target)))
try:
    m = {"id": "h1", "name": "Bram Voss", "bond": 20, "memories": [], "quirks": {"likes": "harvest", "dislikes": "flee", "reacted": {}, "deeds_seen": {}}}
    quirks.react(m, "flee", "disapprove", 3, by="vessa")
finally:
    canon.bind_journal(journal_was)
check("a companion's reaction to a deed is journaled against the character who did it", rows == [("deed_reaction", "vessa", "h1")], rows)
g.session.close()
shutil.rmtree("saves/acting_character_630", ignore_errors=True)

# ---- the fences
ROOT = Path(__file__).resolve().parent.parent.parent
FOLDERS = ("engine", "scenes", "services", "npc", "llm", "core", "storage", "ui", "world")
SCENE = ("ws", "scene", "self")
trees = {}
for folder in FOLDERS:
    for path in sorted((ROOT / folder).rglob("*.py")):
        trees[path.relative_to(ROOT).as_posix()] = ast.parse(path.read_text(encoding="utf-8"))
for path in sorted(ROOT.glob("*.py")):
    if path.name not in ("simlib.py", "simbot.py"):
        trees[path.name] = ast.parse(path.read_text(encoding="utf-8"))


def players_read(node, names=SCENE, also=()) -> list[int]:
    """The lines where a scene's player is read: ws.player, scene.player, self.player, x.ws.player, or getattr(ws, "player"). With
    `also`, the scene's other names for the one player's (ws.place, ws.acting)."""
    attrs = ("player",) + tuple(also)
    scene = lambda v: isinstance(v, ast.Name) and v.id in names or isinstance(v, ast.Attribute) and v.attr == "ws"
    return sorted([n.lineno for n in ast.walk(node) if isinstance(n, ast.Attribute) and n.attr in attrs and scene(n.value)]
                  + [n.lineno for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "getattr"
                     and len(n.args) >= 2 and scene(n.args[0]) and isinstance(n.args[1], ast.Constant) and n.args[1].value in attrs])


taking = {}
for name, tree in trees.items():
    for fn in ast.walk(tree):
        if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)) and fn.name != "player_of" \
                and any(a.arg in ("actor_id", "char_id", "character_id") for a in fn.args.args + fn.args.kwonlyargs) \
                and players_read(fn, also=("place", "acting")):
            taking[f"{name} {fn.name}"] = players_read(fn, also=("place", "acting"))
check("no function that takes a character's id reads the scene's player, its place or its acting id (it asks player_of for that id)",
      not taking, taking)
for name in ("engine/act.py", "engine/ruling.py", "engine/targets.py"):
    check(f"{name} reads the scene's player nowhere", not players_read(trees[name], ("ws", "scene")), players_read(trees[name], ("ws", "scene")))

READS = {                                                # ws.player read in the engine, per file: a count only falls
    "engine/court.py": 7, "engine/entities.py": 6, "engine/events.py": 28, "engine/features.py": 5,
    "engine/matters.py": 17, "engine/moment_prompts.py": 1, "engine/moments.py": 10, "engine/obligations.py": 2, "engine/presence.py": 1,
    "engine/reactions.py": 13, "engine/situation_parts.py": 4, "engine/stakes.py": 6, "engine/stay.py": 2, "engine/truth.py": 26,
    "engine/world_improv.py": 1,
}
found = {name: len(players_read(tree, ("ws", "scene"))) for name, tree in trees.items() if name.startswith("engine/") and players_read(tree, ("ws", "scene"))}
check("the engine reads the scene's player in the recorded places and no more (new code takes an id and asks player_of)",
      all(n <= READS.get(f, 0) for f, n in found.items()), {f: (n, READS.get(f, 0)) for f, n in found.items() if n > READS.get(f, 0)})
check("...and a count that fell is lowered here", all(found.get(f, 0) == n for f, n in READS.items()),
      {f: (found.get(f, 0), n) for f, n in READS.items() if found.get(f, 0) != n})


def a_side(node, parents) -> bool:
    """A fight's side: compared with something's .side, passed as side=, or assigned to a .side."""
    p = parents.get(node)
    while isinstance(p, (ast.Tuple, ast.Set, ast.List)):
        p = parents.get(p)
    if isinstance(p, ast.Compare):
        return any(isinstance(o, ast.Attribute) and o.attr == "side" for o in [p.left] + list(p.comparators))
    if isinstance(p, ast.keyword):
        return p.arg == "side"
    return isinstance(p, ast.Assign) and any(isinstance(t, ast.Attribute) and t.attr == "side" for t in p.targets)


LITERALS = {                                             # the string "player" outside a fight's side, per file: a count only falls
    # ---- a character's id written as the word: what multiplayer M1 has still to name by id
    "engine/canon.py": 3,                                # the subject of a fact about the character
    "engine/combat.py": 2,                               # the first player fighter's id; a key of the rules' hold table
    "engine/domain_events.py": 4,                        # the actor of a party's events
    "engine/events.py": 3, "engine/matters.py": 1, "engine/starts.py": 1,     # who ended a thread: "the player", whichever it was
    "engine/entities.py": 3,                             # the cast's one reference to a human
    "engine/party_director.py": 5,                       # whom a beat concerns or is said to
    "engine/reactions.py": 1,                            # a hire's owner
    "engine/severity.py": 1,                             # whom a thing concerns
    "engine/truth.py": 9,                                # the player's viewer, the facet of that name and its facts
    "scenes/arc_actions.py": 3,                          # a captive's owner
    "scenes/banter_actions.py": 5,                       # whom a memory concerns; a hook's name; a key of a speaker's context
    "services/fight.py": 3,                              # the first player fighter's id; a captive's owner
    "npc/models.py": 3,                                  # an older record's one character
    "storage/invariants.py": 3,                          # where a problem is; one id among a record's
    "core/models.py": 1,                                 # the saved id itself
    # ---- the saved row's key, which M1's migration re-keys (the owner, 2026-11-14)
    "storage/playerstable.py": 1, "storage/campaign.py": 2, "storage/saves.py": 2,     # (f638) named once; the export, the import, the save list
    # ---- a word, not an id: a key of a prompt's context, a word the model may write, a name in a table, an attribute's name
    "engine/banter.py": 1, "engine/battlefield_builder.py": 1, "engine/data_check.py": 1, "engine/hygiene.py": 4,
    "engine/mentor.py": 1, "engine/situation_parts.py": 1, "engine/situations.py": 4, "engine/worn.py": 1, "scenes/combat_scene.py": 1, "scenes/part_actions.py": 1, "scenes/party_actions.py": 1, "scenes/plan_repairs.py": 1,
    "scenes/quirk_actions.py": 1, "llm/contracts.py": 6,
}
words = {}
for name, tree in trees.items():
    if name == "storage/migrations.py":
        continue                                         # an old save's one character was "player": its steps say so for good
    parents = {c: p for p in ast.walk(tree) for c in ast.iter_child_nodes(p)}
    n = sum(1 for x in ast.walk(tree) if isinstance(x, ast.Constant) and x.value == "player" and not a_side(x, parents))
    if n:
        words[name] = n
check('the string "player" stands in the recorded places and no more (a character is named by its id)',
      all(n <= LITERALS.get(f, 0) for f, n in words.items()), {f: (n, LITERALS.get(f, 0)) for f, n in words.items() if n > LITERALS.get(f, 0)})
check("...and a count that fell is lowered here", all(words.get(f, 0) == n for f, n in LITERALS.items()),
      {f: (words.get(f, 0), n) for f, n in LITERALS.items() if words.get(f, 0) != n})
for name in ("engine/memory.py", "engine/quirks.py"):
    check(f"{name} holds none", name not in words, words.get(name))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
