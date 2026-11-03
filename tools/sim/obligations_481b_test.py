"""(f481, part 2 of 2) A hire's commitments, a bribe and a companion's errand, each ending for a reason (GOALS.md S2: nothing ends by age;
the owner's answer of 2026-11-03 to Bundle D's question 3). A hire holds six promises with no clock on them, a seventh is kept as their
word and none of the six is let go for it; the fact reader's one call now also hears a promise said settled, and the held one it names is
kept, with a reason, while a settling that names none ends nothing; a hire who dies or leaves lets go of what they had promised; a bribe is
kept once the time bought has passed; an errand's ask ends with its answer (taken, said no to, let lie); and the night counts only the
promises still held."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 6)
simlib.install(stub)
shown = simlib.quiet_console()
from engine import canon, domain_events as de, obligations

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok: bad.append(n)

PROMISES = ["I owe my brother forty silver from the spring fair.", "I swore to the abbess I would bring her nephew home.",
            "I promised Fenna I would be back by the harvest moon.", "I owe the smith in Parth for a mended buckle.",
            "I told the ferryman I would carry his letter to the coast.", "I gave my word to the widow Marl to mend her roof.",
            "I promised the miller's boy a lesson with the sling."]
m = {"id": "h1", "name": "Ghak Skurz", "memories": [], "commitments": []}
for i, p in enumerate(PROMISES):
    canon.review(m, [], [], 10 + i, who=m["name"], buckets={"commitment": [p]}).commit()
held = [x["text"] for x in m["commitments"] if x.get("state", "active") == "active"]
check("six promises are held, and the seventh is kept as their word without letting any of the six go",
      held == PROMISES[:6] and [x["text"] for x in m.get("commitments_said", [])] == PROMISES[6:], (held, m.get("commitments_said")))
check("...and no clock ends them: four months on, all six are still offered back to the hire",
      sum(1 for r in canon.records(m, day=10 + 120) if r["text"].startswith("Something you have promised")) == 6)

canon.review(m, [], [], 140, who=m["name"], buckets={"kept": ["I finally paid my brother back the forty silver."]}).commit()
done = next(x for x in m["commitments"] if x["text"] == PROMISES[0])
check("a promise said settled is kept, with a reason from data, and no longer offered back", done["state"] == "fulfilled"
      and done["why"] in obligations.family("commitment")["reasons"]["fulfilled"]["kept"]
      and not any(PROMISES[0] in r["text"] for r in canon.records(m, day=140)), done)
canon.review(m, [], [], 141, who=m["name"], buckets={"kept": ["That business with the wolves is behind us now."]}).commit()
check("...a settling that names no promise held ends nothing", sum(1 for x in m["commitments"] if x.get("state", "active") == "active") == 5)
check("...and a draft never said keeps nothing: the review alone changes no promise",
      canon.review(m, [], [], 142, who=m["name"], buckets={"kept": [PROMISES[1]]}) is not None
      and next(x for x in m["commitments"] if x["text"] == PROMISES[1])["state"] == "active")

# ---- the fact reader's one call hears it: the schema takes a 'kept' fact, and the router keeps it however long it lasted
from llm.contracts import Extracted
got = Extracted.model_validate({"facts": [{"speaker": "Ghak Skurz", "subject": "self", "kind": "paid", "text": "I paid the smith for the buckle.",
                                           "lasts": "now"}]})
check("the fact reader's answer can say a promise is settled (an older word for it is read as kept)", got.facts[0].kind == "kept")
check("...and it is kept as kept, not as today's passing state", canon.route(got.facts[0], []) == ("self", "kept"))
check("...in the same call: the reader is told what kept means", "kept: a promise or debt of theirs" in canon.EXTRACT_SYSTEM)

# ---- a hire who dies lets go of what they promised, each for that reason
game = simlib.campaign("obligations_481b", minutes=600)
ws, store = game.scene, game.store
ws.enter(ws.player.location)
from tools import nightrun
nightrun.hire_party(ws, 2)
a, b = ws.player.party[0], ws.player.party[1]
for mem in (a, b):
    mem["commitments"] = [{"text": f"I owe {mem['name'].split()[0]}'s cousin a favour.", "day": 1, "state": "active"},
                          {"text": "I swore to see the bridge rebuilt.", "day": 1, "state": "active"}]
ws.notice(de.MemberDied(minute=ws.minutes, member_id=a["id"], name=a["name"]))
check("a hire who dies lets go of every promise held, each with the reason", all(x["state"] == "released"
      and x["why"] in obligations.family("commitment")["reasons"]["released"]["hire_died"] for x in a["commitments"]), a["commitments"])
run = type("R", (), {})()
state = nightrun.Run.continuity_state(run, ws)
check("the night counts only the promises still held", state["commitments"] == 2, state["commitments"])

# ---- a bribe is kept once the time bought has passed
from npc.models import NPC
g = NPC(id="g1", name="Orm Vell", people="human", role="guard", location=ws.player.location)
store.save_npc(g)
obligations.open_(store, "bribe", "g1", ws.acting, "look the other way at the gate", ws.minutes, terms={"until": ws.minutes + 120, "amount": 50})
obligations.lapse(ws)
check("a bribe stands while the time bought runs", obligations.current(store, "bribe", "g1", ws.acting) is not None)
store.meta.minutes += 121; store.save_meta()
obligations.lapse(ws)
kept = [e for e in store.find_entities(kind="obligation") if e.data.get("family") == "bribe"]
check("...and is kept once it has passed, with that reason", kept and kept[0].state == "fulfilled"
      and kept[0].history[-1][3] in obligations.family("bribe")["reasons"]["fulfilled"]["term_kept"], [e.history for e in kept])

# ---- an errand's ask ends with its answer
E = {"kind": "letter", "where": "here"}
def ask():
    ws._errand = (b, E)
    return obligations.open_(store, "errand", f"hire:{b['id']}", ws.acting, "carry my letter to the temple", ws.minutes, terms={"errand": "letter"})
ask()
check("an errand asked is an offer from the hire", obligations.current(store, "errand", f"hire:{b['id']}", ws.acting) is not None
      and obligations.current(store, "errand", f"hire:{b['id']}", ws.acting).links == {"hire": b["id"]})
ws.errand_intercept("no, not today")
asked = [e for e in store.find_entities(kind="offer") if e.data.get("family") == "errand"]
check("...said no to, it is let go with that reason", asked and asked[-1].state == "released" and asked[-1].data.get("cause") == "refused", [e.history for e in asked])
ask()
ws.errand_intercept("what was that noise")
asked = [e for e in store.find_entities(kind="offer") if e.data.get("family") == "errand"]
check("...answered with something else, it is let lie, with that reason", asked[-1].state == "released" and asked[-1].data.get("cause") == "no_answer",
      [e.data.get("cause") for e in asked])
game.close()
import shutil
shutil.rmtree("saves/obligations_481b", ignore_errors=True)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
