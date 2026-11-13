"""(f609) A success never goes past what was ruled. The act's ruling says, for a yes or a cost, what the act comes to if it works (`works`,
as it would be seen, only what someone with what they have could bring about here), and the narrator is told that success, never "what
the player attempts WORKS: show it done", which let a proclamation that rolled well be shown as a crown (the pod rerun of 2026-11-12,
docs/measure/2026-11-12_phase2_pod.md section 7: "I declare myself king of Parth" ruled a cost with nothing to change).
Run: python tools/sim/act_bounded_609_test.py"""
import json
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()
from engine import act, checks, pulse, targets
from llm.contracts import ActRuling

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("act_bounded_609", seed=3, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
store.save_world_state({**pulse.empty_state(ws.minutes), **(store.load_world_state() or {})})

# ---- the grammar: a yes or a cost says what it comes to; a no says what happens instead
T = targets.targets_for(ws, ws.acting)
schema = act.shape(ws, T).model_json_schema()
yes, no = schema["anyOf"]
check("a yes or a cost must say what it comes to if it works, and carries no `answer` (a no's alone)",
      "works" in yes["required"] and yes["properties"]["works"].get("minLength") == 1 and "answer" not in yes["properties"]
      and yes["properties"]["works"]["maxLength"] == act.A["grammar"]["works"], json.dumps(yes)[:400])
check("...a no says what happens instead, and nothing of what it would come to", "answer" in no["required"] and "works" not in no["properties"])
check("...and the prompt tells the model what it is", "works:" in act.SYSTEM and "answer:   for a no only" in act.SYSTEM)
check("the act's data checks clean", act.problems() == [], act.problems())

# ---- the king, as the model ruled it on the pod (a cost, nothing to change), with what it comes to
KING = {"sense": "cost", "why": "A bold claim in a public square requires a commanding presence and a crowd's attention.", "uses": [],
        "requires": [], "stakes": {"check": "charisma", "hard": "hard"}, "changes": [], "fail": "noticed",
        "works": "Heads turn across the square and the crowd hears you out; a few laugh, the guards watch you closely, and no one takes you for king."}
r = ActRuling.model_validate(KING, context=act.context(ws, T))
check("the contract keeps what an act comes to", r.works == KING["works"], r)

told = []
real_narrate = ws.narrate
ws.narrate = lambda event, text="": told.append(event)


def attempt(text, ruled, roll):
    stub.act_ruling = ruled
    real_roll = checks.roll
    checks.roll = lambda odds, rng=None, c=None: (roll, 1)
    try:
        with ws.operation("action:other", text):
            ws.on_other(types.SimpleNamespace(kind="other", summary=text.rstrip(".")), text)
    finally:
        checks.roll = real_roll
    return told[-1] if told else ""


said = attempt("I declare myself king of Parth.", KING, "success")
check("a success is told as what the ruling says it comes to, and nothing beyond it, never 'show it done'",
      "WORKS" in said and KING["works"] in said and "nothing beyond it" in said and "Show it done" not in said, said[-500:])
said = attempt("I declare myself king of Parth, again.", KING, "partial")
check("...a partial success as falling short of it", KING["works"] in said and "half works" in said, said[-500:])
said = attempt("I declare myself king of Parth, once more.", KING, "failure")
check("...and a failure as before: what was meant does not happen", "FAILS" in said and KING["works"] not in said, said[-300:])

# ---- the reuse rule: a kept ruling is played back with what it comes to
told.clear()
attempt("I declare myself king of Parth.", {"sense": "no", "answer": "unused: the kept ruling stands"}, "success")
check("a kept ruling, played back with no call, is held to what it came to", told and KING["works"] in told[-1],
      told[-1][-400:] if told else "")

# ---- the dragon's hoard (the complex set), as ruled on the pod: four rumours used, nothing changed
HOARD = {"sense": "cost", "why": "Convincing a crowd to abandon their livelihoods for a myth requires significant charisma and effort.",
         "uses": [], "requires": [], "stakes": {"check": "persuasion", "hard": "hard"}, "changes": [], "fail": "noticed",
         "works": "A handful of idlers listen and argue about it among themselves; the stallholders go back to their trade."}
said = attempt("I stand on a crate, tell the whole market of a dragon's hoard in the caves, and lead them all down there to share it.",
               HOARD, "strong success")
check("a strong success is still only what it comes to", HOARD["works"] in said and "nothing beyond it" in said, said[-500:])

# ---- what it comes to never carries a change the engine refused
road = next(t for t in targets.targets_for(ws, ws.acting).rows if t.ref in ws.world.roads)
said = attempt("I bar the north gate with a cart.", {"sense": "cost", "why": "a cart is to hand", "stakes": {"check": "strength", "hard": "fair"},
                                                     "fail": "time_lost", "works": "The north gate is barred and no one gets through.",
                                                     "changes": [{"n": 1, "target": road.code, "becomes": "access", "state": "closed"}]}, "success")
check("a success whose ruling asked for a change the engine refused is told as what it comes to short of what did not happen",
      "short of what did not happen" in said and "WHAT DID NOT HAPPEN" in said, said[-500:])

# ---- a ruling kept from before, or a stand-in's, with no `works`: told as it always was
said = attempt("I whistle a tune.", {"sense": "yes", "why": "anyone can"}, "success")
check("a ruling with nothing said of what it comes to is told as before", "Show it done" in said, said[-300:])
ws.narrate = real_narrate

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
