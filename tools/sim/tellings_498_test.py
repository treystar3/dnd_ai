"""(f498) The tellings are restartable operations and the fight's opening is a telling of its own. An attack from a line commits the
action, then an `opening` operation whose Narration call (combat_opening) is made with no operation open; the opening ran twice (stood
down at its call, then again with the answer) and committed once under its first id, asking in the same words; the page reads the
opening, then the notes and the pane. The round's telling (combat_narrate) is asked outside too, and one whose call fails every try is
round_stood while the round stands. An opening whose call fails leaves the fight begun (its row saved, its pane shown) with a fight_begun
line in the narrator's words and no machinery. The goddess line is asked outside and the death stands either way. A cataclysm's fight
begun inside the world operation commits before its opening is told (the opening a passage after the world's commit). A pane command
(#useitem in a fight) is a restartable operation too: what it shows reaches the page at its commit, the pane once. The ratchet holds none
of the four tellings. Nothing stays in the process."""
import shutil
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
SHOWN = simlib.quiet_console()
import ui.console as uc
from engine import combat, events, failures, operation
from ui import console

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

NAME = "tellings_498"
game = simlib.campaign(NAME, cls="warrior", seed=3, location="south_fields")
ws, store = game.scene, game.store
ws.enter("south_fields")

LOG, FAIL, BEGUN, REQ = [], {"titles": set()}, [], []
real = simlib.below()                       # (f518) the stub answering now, taken before the spy goes in over it


def chat(**k):
    title = k["format"].get("title")
    op = operation.current()
    LOG.append((title, op.kind if op else None))
    if title == "Narration":
        REQ.append(k["messages"][1]["content"])
    if title in FAIL["titles"]:
        raise ConnectionError("the model server cannot be reached")
    return real.chat(**k)


spy = simlib.stand_in(chat=chat, embed=None, name="tellings_498_spy")
real_begin = operation.begin


def begin(*a, **k):
    op = real_begin(*a, **k)
    BEGUN.append((op.kind, op.id))
    return op


operation.begin = begin
real_commit = store.commit_operation
store.commit_operation = lambda op, *a, **k: (SHOWN.append(("commit", op.kind)), real_commit(op, *a, **k))[1]
console.combat_state = lambda data: (SHOWN.append(("pane", "")), False)[1]          # the terminal's: no pane, so the text panel follows
console.combat_panel = lambda lines: SHOWN.append(("panel", ""))


def ops_of_input():
    return [o for o in store.load_operations()["ops"] if o["steps"] == store.meta.steps]


def kinds():
    return [o["kind"] for o in ops_of_input()]


def reset():
    del SHOWN[:], LOG[:], BEGUN[:], REQ[:]


def fight_begun_fills(foe: str, n: int) -> set:
    facts = {"foe": foe, "count": failures.count_phrase(n)}
    return {l.format_map(facts) for l in failures.F["fight_begun"]}


# ---- 1. an attack from a line: the action commits, then the opening, a telling of its own asked with no operation open
creature = ws.world.bestiary["awakened_shrub"]                   # fearless (families.yaml plant): it never bolts or yields, so the fight lasts
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "awakened shrub", "near")
foe.hp = foe.max_hp = 600                                        # a weak thing with a long life: never deadly
ws.wildlife = (creature, [foe])
stub.plan = [{"kind": "attack", "target": "awakened shrub"}]
reset()
stood = ws.turn("I attack the shrub.")
stub.plan = None
k = kinds()
check("an attack from a line: the action commits, then the opening is an operation of its own, then the world's operations",
      stood is True and ws.combat is not None and k[:2] == ["action:attack", "opening"] and k[2:] == ["world", "arrival", "law", "tail"], (stood, k))
opens = [(t, o) for t, o in LOG if t == "Narration"]
check("...its Narration call (combat_opening) is made with no operation open", len(opens) == 1 and opens[0][1] is None, opens)
ids = [i for kk, i in BEGUN if kk == "opening"]
recorded = [o["id"] for o in ops_of_input() if o["kind"] == "opening"]
check("...the opening ran twice (stood down at its call, then again with the answer) and committed once, under its first id",
      len(ids) == 2 and ids[0] == ids[1] and recorded == [ids[0]], (ids, recorded))
check("...asking in the same words: one request, naming the foe and the odds", len(REQ) == 1 and "awakened shrub" in REQ[0] and "THE ODDS" in REQ[0],
      (len(REQ), REQ[-1][-300:] if REQ else REQ))
order = [kk for kk, t in SHOWN if kk in ("commit", "narrate", "pane", "panel", "note")]
i_open = next((i for i, (kk, t) in enumerate(SHOWN) if kk == "narrate" and t.startswith("[scene")), None)
i_pane = next((i for i, (kk, t) in enumerate(SHOWN) if kk == "pane"), None)
i_commit = next((i for i, (kk, t) in enumerate(SHOWN) if kk == "commit" and t == "opening"), None)
check("...and the page reads the opening after its commit, then the pane (what followed the marker waited behind the telling)",
      None not in (i_open, i_pane, i_commit) and i_commit < i_open < i_pane, (i_commit, i_open, i_pane, order[:12]))
check("the opening left what the player read of it on the fight's scene", bool(ws.combat.fight_shown), ws.combat.fight_shown)

# ---- the round's telling, asked outside; a telling that fails every try is round_stood and the round stands
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e1"}
reset()
round0 = ws.combat.fight.round
stood = ws.turn("I strike at the shrub.")
k = kinds()
told = [(t, o) for t, o in LOG if t == "Narration"]
ids = [i for kk, i in BEGUN if kk == "round"]
check("a round: its line commits, then its telling is an operation of its own, asked with no operation open, run twice and committed once",
      stood is True and k[:2] == ["line", "round"] and len(told) == 1 and told[0][1] is None and len(ids) == 2 and ids[0] == ids[1]
      and [o["id"] for o in ops_of_input() if o["kind"] == "round"] == [ids[0]], (stood, k, told, ids))
check("...and the fight's reading of the line (combat_interpret) is asked outside too, before it",
      [t for t, o in LOG if t in ("CombatIntent", "Narration")] == ["CombatIntent", "Narration"] and all(o is None for t, o in LOG if t == "CombatIntent"), LOG)
FAIL["titles"] = {"Narration"}
reset()
round1 = ws.combat.fight.round
stood = ws.turn("I strike at the shrub.")
FAIL["titles"] = set()
lines = [t for kk, t in SHOWN if kk == "narrate"]
check("a round whose telling fails every try stands: the round passed, a blow is recorded, round_stood in the telling's place",
      stood is True and ws.combat is not None and ws.combat.fight.round == round1 + 1 and ws.combat.fight.hits
      and [o.kind for o in ws.line_untold] == ["round"] and any(t in failures.F["round_stood"] for t in lines)
      and not any(failures.MACHINERY.search(t) for t in lines), (stood, ws.combat.fight.round if ws.combat else None, round1, lines))

# ---- 2. an opening whose call fails: the fight begun, its row saved and its pane shown, fight_begun in the narrator's words
ws.combat = None
store.save_combat(None)                                          # the shrub let go: another fight, whose opening cannot be written
foe = combat.fighter_from_creature(creature, 1, "normal", "e1", "awakened shrub", "near")
foe.hp = foe.max_hp = 600
ws.wildlife = (creature, [foe])
stub.plan = [{"kind": "attack", "target": "awakened shrub"}]
FAIL["titles"] = {"Narration"}
reset()
stood = ws.turn("I attack the shrub.")
FAIL["titles"] = set()
stub.plan = None
lines = [t for kk, t in SHOWN if kk == "narrate"]
fills = fight_begun_fills("awakened shrub", 1)
check("an opening whose call fails every try leaves the fight begun: the action stood, the row saved, the pane shown",
      stood is True and ws.combat is not None and store.load_combat() is not None and any(kk == "pane" for kk, t in SHOWN)
      and "opening" in [o.kind for o in ws.line_untold] and "action:attack" in kinds(), (stood, ws.combat is not None, [o.kind for o in ws.line_untold], kinds()))
check("...and the player reads that the fight is on, in the narrator's words (fight_begun, filled with who came and how many), never machinery",
      any(t in fills for t in lines) and not any(failures.MACHINERY.search(t) for t in lines), lines)
check("...the stand-in comes after the action's commit and before the pane",
      (lambda s: s.index(("commit", "action:attack")) < next(i for i, e in enumerate(s) if e[0] == "narrate" and e[1] in fills) < next(i for i, e in enumerate(s) if e[0] == "pane"))(list(SHOWN)),
      [(kk, t[:30]) for kk, t in SHOWN][:10])
check("the fight so begun is fought: the next line's round stands", (ws.turn("I strike at the shrub.") is True) and ws.combat is not None and ws.combat.fight.hits, ws.combat)

# ---- the goddess line asked outside; the death stands either way
ws.combat = None
store.save_combat(None)
c = ws.player.character
c.health = 1
deaths0 = c.deaths
bandit = ws.world.bestiary["bandit"]
strong = combat.fighter_from_creature(bandit, 40, "elite", "e2", name="bandit captain")
strong.hp = strong.max_hp = 10 ** 6
strong.weapon_damage = 10 ** 4
ws.wildlife = (bandit, [strong])
stub.plan = [{"kind": "attack", "target": "bandit captain"}]
stub.a_CombatIntent = lambda u, k: {"kind": "attack", "target": "e2"}
ws.turn("I attack the bandit captain.")
stub.plan = None
reset()
for _ in range(6):                                               # the captain winds up, may miss, then lands: a few rounds
    stood = ws.turn("I attack the bandit captain.")
    if ws.combat is None or stood is not True:
        break
c2 = store.load_player().character
goddess = [(t, o) for t, o in LOG if t == "GoddessLine"]
check("the goddess's words at a death are asked with no operation open, and the death stands: counted, the player awake elsewhere",
      stood is True and ws.combat is None and c2.deaths == deaths0 + 1 and goddess and all(o is None for t, o in goddess)
      and any(kk == "say" for kk, t in SHOWN) and "goddess" in kinds(), (stood, c2.deaths, deaths0, goddess, kinds()))

# ---- 3. a cataclysm's fight begun inside the world operation commits before its opening is told
ws.enter("trading_square")
from engine import pulse as _pulse
now = ws.minutes
st = store.load_world_state() or _pulse.empty_state(now)
th = {"id": "cat1", "title": "The Ash Tide", "tier": "cataclysm", "kind": "invasion", "place": "greywood", "antagonist": "the Ash Tide", "stage": 1, "status": "active",
      "stages": [{"description": "Omens.", "effects": [], "signs": "Dogs will not settle."}, {"description": "The host reaches the Wend.", "effects": [], "signs": "Smoke on the north road."}],
      "fallout": {"description": "", "effects": []}, "times": [now - 1440, now, now + 14 * 1440], "made": now - 1440, "groups": ["everyone"], "paths": [],
      "hit_towns": ["parth"], "hits": [[], ["parth"]], "fallen": [], "level": 1, "scope_places": ["parth"], "leaders": [], "boss": "", "door": "scene", "summons": "pending", "moment": "", "sender": "", "clues": [], "touched": False, "answered": False, "opened": now}
st["threads"] = [th]
events.add_spawn(store, ws.world, st, "cat1", "greywood", "wolf", False, now - 1440, days=30, level=1, need=3)
st["assaults"] = [{"thread": "cat1", "town": "parth", "stage": 1, "minute": now}]
store.save_world_state(st)
stub.plan = [{"kind": "look"}]
reset()
stood = ws.turn("I look around.")
stub.plan = None
k = kinds()
i_world = k.index("world") if "world" in k else None
check("a cataclysm reaching the town the player stands in: the fight begins inside the world operation, which commits before its opening is told",
      stood is True and ws.combat is not None and getattr(ws, "assault", None) and i_world is not None and "opening" in k[i_world + 1:]
      and k.index("opening") < k.index("tail"), (stood, ws.combat is not None, k))
opens = [(t, o) for t, o in LOG if t == "Narration"]                # the look's passage and the moment's are told inside their own
check("...its opening asked with no operation open, after the world's commit",   # operations (narrate is not asked outside); the opening, last, is
      opens and opens[-1][1] is None and (lambda s: s.index(("commit", "world")) < next(i for i, e in enumerate(s) if e[0] == "commit" and e[1] == "opening"))(list(SHOWN)),
      (opens, [(kk, t[:20]) for kk, t in SHOWN if kk == "commit"]))

# ---- 4. a pane command in a fight is a restartable operation: what it shows reaches the page at its commit, the pane once
from engine import inventory
inventory.add(ws.player.character.inventory, inventory.make_good("healing_draught", 2), 99)     # the player as the scene holds them now (reloaded since the death)
store.save_player(ws.player)
script = ["#useitem healing draught", "quit"]
uc.ask = lambda *a, **k: script.pop(0) if script else "quit"
reset()
ws.run()
k = kinds()
after = [(kk, t) for kk, t in SHOWN[SHOWN.index(("commit", "command:useitem")) + 1:]] if ("commit", "command:useitem") in SHOWN else []
check("a pane command in a fight (#useitem) is an operation of its own, restartable, and what it showed reaches the page at its commit: the draught's line, then the pane once",
      k == ["command:useitem"] and [kk for kk, t in after if kk in ("narrate", "pane")] == ["narrate", "pane"] and any("healing draught" in t for kk, t in after if kk == "narrate")
      and ("command:useitem", ) in {(kk,) for kk, i in BEGUN}, (k, after[:6], [kk for kk, i in BEGUN]))

check("the ratchet holds none of the four tellings: nothing of them is asked inside an operation",
      not ({"combat_opening", "combat_narrate", "combat_aftermath", "goddess_line"} & set(operation.LEGACY)), operation.LEGACY)

check("every telling was asked of the test's own stand-in", spy.live() and spy.src.calls["Narration"] >= 4, dict(spy.src.calls))
operation.begin, store.commit_operation = real_begin, real_commit
spy()
game.close()
shutil.rmtree(f"saves/{NAME}", ignore_errors=True)
check("nothing of it stays in the process", simlib.residue() == {}, simlib.residue())

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
