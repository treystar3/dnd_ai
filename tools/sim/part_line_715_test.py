"""(f715) One honest line when a turn stands in part (the owner, 2026-11-16: "Yes, build all three"; docs/design/25_speech_parts_camp.md).
In Ironvein a hand-in was paid, then the turn's budget ran out before the clerk spoke, and two stand-ins printed: "You see it
through." and "You got as far as Go to the guild hall; the finished contract 'Bounty: ...', paid 27 silver and 50 copper. The rest
didn't happen." Step summaries pasted mid-sentence, and "the rest" for what was in fact only the clerk's words.
Held here: each step's operation keeps what it set out to do as a clause (failures.yaml missed, by kind: "speak with the clerk",
"go to the guild hall"); the part line names what did not happen, by those clauses, never "the rest" and never a pasted summary
(what did happen is already on the page: the ledger, the bar); and a passage lost on such a line stands in with nothing of its own,
so the part line is the one line.
Run: python tools/sim/part_line_715_test.py"""
import shutil
import sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 3))
simlib.quiet_console()
from llm.contracts import ActionIntent as A
from engine import failures
from engine.operation import Operation

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)


g = simlib.campaign("part_715", seed=4, location="trading_square")
ws = g.scene
ws.enter("trading_square")
from engine import retrieval
for place in ("guild_house", "tilted_plough", "trading_square"):
    ws.enter(place)
row = retrieval.people_in_town(g.store, ws.world, "parth")[0]
clerk = g.store.load_npc(row.id)
ws.present.append(clerk)
check("a talk sets out to speak with someone, by how the player knows them",
      ws.aim_of(A(kind="talk", target=clerk.id, speech="Here.")) == f"speak with {clerk.label(ws.acting)}", ws.aim_of(A(kind="talk", target=clerk.id)))
check("...a walk to go somewhere, by the place's name", ws.aim_of(A(kind="move", destination="trading_square")) == f"go to {ws.world.places['trading_square'].name}",
      ws.aim_of(A(kind="move", destination="trading_square")))
check("...a step whose facts are unknown has its kind's plainer clause", ws.aim_of(A(kind="buy")) == failures.F["missed"]["buy"][-1], ws.aim_of(A(kind="buy")))
check("...and a kind the table does not know has the default", failures.missed_clause("no_such_kind", {}) == failures.F["missed"]["default"][0]
      and failures.done_clause("no_such_kind", {}) == failures.F["done"]["default"][0], failures.missed_clause("no_such_kind", {}))
check("every kind of action has its clauses, each list ending in one that names nothing", failures.clause_problems() == [], failures.clause_problems())

op = Operation(id="x", kind="action:talk", steps=1, index=1, revision_seen=0, aim=f"speak with {clerk.label(ws.acting)}")
went = Operation(id="w", kind="action:go", steps=1, index=0, revision_seen=0, did=["walked to the guild hall",
                 "handed in the contract 'Bounty: the snake' and were paid 27 silver"])
ws.line_ops, ws.line_failed = [went], [op]
line = ws.part_line()
check("the part line names what stood, in clauses, then what did not; never 'the rest', a pasted summary or a semicolon",
      line.startswith("You walked to the guild hall, then handed in the contract 'Bounty: the snake' and were paid 27 silver")
      and clerk.label(ws.acting) in line and "the rest" not in line.lower() and ";" not in line and "Go to" not in line, line)
import re as _re
mid = [w for sent in _re.split(r"(?<=[.!?])\s+", line) for w in sent.split()[1:] if w[:1].isupper() and w.lower().strip(".,") not in clerk.label(ws.acting).lower()]
check("...never a summary pasted mid-sentence, never a capital in the middle of a sentence", not mid, (line, mid))
check("a lost passage on a line that stood in part stands in with nothing of its own: the part line is the one line", ws.line_standin(ws.rng) == [],
      ws.line_standin(ws.rng))
check("...while a world passage lost on that turn still says the deed stood", ws.stood_standin(ws.rng) and ws.stood_standin(ws.rng)[0] in failures.F["stood_any"])
ws.line_failed = []
check("...and on a whole line the line's own passage says the deed stood", ws.line_standin(ws.rng) and ws.line_standin(ws.rng)[0] in failures.F["stood_any"])
ws.line_ops, ws.line_failed = [went], []
ws.line_plan = [A(kind="talk", target=clerk.id, speech="Here."), A(kind="look")]
never = ws.part_line()
check("steps never begun are named too, joined with 'or'", f"speak with {clerk.label(ws.acting)} or look around" in never, never)
ws.plan_now = (A(kind="search"),)
ws.begin_line()
ws.line_ops, ws.line_failed = [went], [op]
fresh = ws.part_line()
check("...and only this line's steps: a new line starts its plan empty, whatever the last one's step left behind",
      ws.line_plan == [] and "search" not in fresh, (ws.line_plan, fresh))
ws.store.arm(False)
def act(summary):
    return ws.act_words(A(kind="other", summary=summary))
check("an act's summary is said back as a clause after 'to': a lead in dropped, the player's own words turned to 'you'",
      act("I try to cut a way through the brambles with my axe.") == "cut a way through the brambles with your axe"
      and act("Scramble up the crag") == "scramble up the crag", (act("I try to cut a way through the brambles with my axe."), act("Scramble up the crag")))
check("...never one that is no such clause: a gerund, a third person verb, or someone's name first",
      act("leaning against the wall and watching the shadows") == "" and act("Climbs the crag") == "" and act("The player climbs") == ""
      and act(f"{ws.player.character.name.split()[0]} climbs the crag") == "",
      [act(x) for x in ("leaning against the wall", "Climbs the crag", "The player climbs")])
check("...and such a step has its plainer clause", ws.aim_of(A(kind="other", summary="leaning on the wall")) == failures.F["missed"]["other"][-1])
seller = next((n for n in ws.present if ws.wares_of(n)), None)
if seller is not None:
    ware = ws.wares_of(seller)[0]
    check("a ware is named by its name, never its id", ws.aim_of(A(kind="buy", target=seller.id, ware=ware.id)) == f"buy {ware.name}",
          (ware.id, ws.aim_of(A(kind="buy", target=seller.id, ware=ware.id))))
check("...and a ware no one here sells by its words, never an id", ws.aim_of(A(kind="buy", ware="healing_draught")) == "buy healing draught",
      ws.aim_of(A(kind="buy", ware="healing_draught")))
check("every part line names what stood and then what was missed, and none speaks of 'the rest'",
      all(l.index("{done}") < l.index("{missed}") and "the rest" not in l.lower() for l in failures.F["part_stood"]) and failures.problems() == [],
      failures.problems())
check("what a step did is a finished clause by its kind ('spoke with ...'), never its summary",
      ws.done_of(A(kind="talk", target=clerk.id, summary="Hand in the bounty")) == f"spoke with {clerk.label(ws.acting)}"
      and ws.done_of(A(kind="look", summary="a look around the hall")) == "looked around")
g.close()
shutil.rmtree("saves/part_715", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
