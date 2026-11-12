"""(f604) One held out of the scene is freed by a hand's work where the trouble is, as by force (the owner, 2026-11-11, GOALS.md row
f601): picking the lock of the cellar a captive is kept in and leading them out frees them. Words still free no one held away, and a
hand's work away from the trouble frees no one. The old judge's rulings carry no work, so their rule is as it was. The ruling corpus's
lock-picking case (data/replay/ruling_cases_act.yaml) is no longer shown apart as known. A change on an act rolled on talk rests on
words, whatever the ruling says (act.yaml talk_checks), so talk frees no one held away; and a hand's work frees one held away only
on a roll of the hand (act.yaml hand_checks: strength, dexterity, constitution, stealth), never on a plain yes or another roll (the
owner, 2026-11-12).
Run: python tools/sim/captive_work_604_test.py"""
import random
import subprocess
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 9)
simlib.install(stub)
simlib.quiet_console()
import config
from engine import act as act_mod, checks, pulse, retrieval, situation_parts, situations, targets
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


g = simlib.campaign("captive_work_604", seed=9, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
world = ws.world
town = pulse.town_of(world, "trading_square")
HERE = list(ws.present) or list(ws.residents[:2])
away = next(p for p in retrieval.people_in_town(store, world, town) if p.id not in {n.id for n in HERE})
config.ACT = True
checks.roll = lambda odds, rng=None, c=None: ("success", 1)              # the dice are not what is under test


def kidnapping(tid):
    """A trader held in a cellar in the square, away from the scene, by a band of kidnappers."""
    with ws.operation("test", "a kidnapping") as op:
        st = store.load_world_state() or {}
        for k_, v_ in pulse.empty_state(ws.minutes).items():
            st.setdefault(k_, v_)
        for x in st.get("threads", []):
            if x["id"].startswith("th604_") and x["status"] == "active":
                x["status"] = "resolved"
        th = {"id": tid, "title": "The kidnapping", "tier": "rare", "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
              "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Held.", "effects": []}],
              "kind": "unrest", "groups": ["everyone"], "fallout": {"description": "The trader is lost.", "effects": []}}
        st.setdefault("threads", []).append(th)
        prop = {"people": [{"who": away.id, "stake": "harmed", "want": "safety"}],
                "conditions": [{"on": "trading_square", "kind": "danger", "label": "the kidnappers in the square", "by": "the kidnappers",
                                "by_kind": "group"}]}
        acc, _ = situations.check(SituationParts.model_validate(prop), store, world, "rare", random.Random(9), town=town, ways=False,
                                  now=ws.minutes, players=(ws.acting,))
        situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
        store.save_world_state(st)
    assert op.state == "committed", op.state
    ws.present = list(HERE)
    held = next(t.code for t in targets.targets_for(ws, ws.acting).rows if t.kind == "person" and t.ref.startswith(tid + "#"))
    return held


def freed(tid):
    th = pulse.thread_of(store.load_world_state(), tid)
    return next(a for a in th["parts"] if a.get("kind") == "person" and a.get("who") == away.id).get("now") == "safe"


def act(text):
    ws.present = list(HERE)
    with ws.operation("action:other", text) as op:
        ws.on_other(types.SimpleNamespace(kind="other", summary=text), text)
    return op


held = kidnapping("th604_lock")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "dexterity", "hard": "fair"},
                   "changes": [{"n": 1, "target": held, "becomes": "safe", "because": "skill"}]}
op = act("I pick the lock of the cellar where they keep the trader and lead them out quietly.")
check("a hand's work where the trouble is frees one held out of the scene: the lock picked, the trader led out",
      op.state == "committed" and freed("th604_lock"), op.state)

held = kidnapping("th604_door")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "strength", "hard": "fair"},
                   "changes": [{"n": 1, "target": held, "becomes": "safe", "because": "force"}]}
act("I break down the cellar door and pull the trader out.")
check("...as force there always did", freed("th604_door"))

held = kidnapping("th604_words")
stub.act_ruling = {"sense": "yes", "changes": [{"n": 1, "target": held, "becomes": "safe", "because": "words"}]}
act("I shout down to the trader in the cellar that they are free now.")
check("words free no one held away", not freed("th604_words"))

held = kidnapping("th604_talk")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "persuasion", "hard": "hard"},
                   "changes": [{"n": 1, "target": held, "becomes": "safe"}]}          # its because left to the default, skill
act("I talk the kidnappers' lookout into fetching the trader up for me.")
check("talk is words (the owner, 2026-11-12): a change on an act rolled on persuasion frees no one held away, whatever it rests on",
      not freed("th604_talk"))
held = kidnapping("th604_song")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "performance", "hard": "fair"},
                   "changes": [{"n": 1, "target": held, "becomes": "safe", "because": "force"}]}
act("I sing so fiercely the kidnappers flee and the trader walks out.")
check("...nor one on a performance, force claimed or not", not freed("th604_song"))
check("the talk checks are data, checked at startup, none of them a test of force",
      set(act_mod.A["talk_checks"]) == {"persuasion", "deception", "performance"}
      and not set(act_mod.A["talk_checks"]) & set(act_mod.A["force_checks"]))

for chk, text, tid in (("", "I walk down and let the trader out.", "th604_yes"),
                       ("insight", "I read the guards and slip the trader out when they look away.", "th604_insight"),
                       ("deception", "I trick the guards into opening the cellar and lead the trader out.", "th604_lie")):
    held = kidnapping(tid)
    stub.act_ruling = {"sense": "yes" if not chk else "cost", **({"stakes": {"check": chk, "hard": "fair"}} if chk else {}),
                       "changes": [{"n": 1, "target": held, "becomes": "safe"}]}             # because left to its default, skill
    act(text)
    check(f"a hand's work frees one held away only on a roll of the hand (the owner, 2026-11-12): {chk or 'a plain yes'} frees no one",
          not freed(tid))
from types import SimpleNamespace as NS
check("what a change rests on, by the roll: skill and force on talk are words; skill on any other roll is work; force only on body or arms",
      [act_mod._because(NS(because=b), c) for b, c in (("skill", "persuasion"), ("force", "deception"), ("skill", "stealth"),
                                                           ("force", "stealth"), ("force", "strength"), ("skill", ""))]
      == ["words", "words", "work", "work", "force", "work"])
check("the hand's checks are data, checked at startup, none of them talk", set(act_mod.A["hand_checks"]) == {"strength", "dexterity",
      "constitution", "stealth"} and not set(act_mod.A["hand_checks"]) & set(act_mod.A["talk_checks"]) and not act_mod.problems())

# ---- the rule itself: away from the trouble, without a roll of the hand, the old judge's rulings, and what talk still reaches
th = pulse.thread_of(store.load_world_state(), "th604_lie")
k = next(i + 1 for i, a in enumerate(th["parts"]) if a.get("kind") == "person" and a.get("who") == away.id)
row = {"n": 1, "part": k, "who": 0, "becomes": "safe", "about": 0, "needs": []}
on_act = {"kind": "acted", "by": ws.acting, "npc": "", "witnesses": sorted(n.id for n in HERE), "coin": 0, "item": "", "count": 1,
          "degree": "", "words_only": False, "force_by_change": True}
far = next(p for p in sorted(world.places) if world.places[p].type in ("town", "city", "village") and pulse.town_of(world, p) != town)
work = {**row, "because": "work", "hand": True}
kept, dropped = situation_parts.ruled(store, th, {**on_act, "place": far}, [work], world)
check("a hand's work away from the trouble frees no one held away", not kept and dropped, dropped)
kept, _ = situation_parts.ruled(store, th, {**on_act, "place": "trading_square"}, [work], world)
check("...the same work where the trouble is does", len(kept) == 1)
kept, _ = situation_parts.ruled(store, th, {**on_act, "place": "trading_square"}, [{**work, "hand": False}], world)
check("...and without a roll of the hand it does not", not kept)
judge = {k_: v for k_, v in on_act.items() if k_ != "force_by_change"}
kept, _ = situation_parts.ruled(store, th, {**judge, "kind": "persuade", "place": "trading_square"}, [work], world)
check("the old judge's rulings: work in an act that is no violence frees no one held away, as before", not kept)
kept, _ = situation_parts.ruled(store, th, {**judge, "kind": "assault", "place": "trading_square"}, [{**row, "because": "force"}], world)
check("...and an act of violence there still frees them", len(kept) == 1)
kept, _ = situation_parts.ruled(store, th, {**on_act, "place": "trading_square", "witnesses": sorted(n.id for n in HERE) + [away.id]},
                                [{**row, "becomes": "grateful", "because": "words"}], world)
check("talk still reaches what words reach: one who heard it is grateful", len(kept) == 1)
config.ACT = False

r = subprocess.run([sys.executable, "tools/ruling_eval.py", "--path", "new", "--cases", "data/replay/ruling_cases_act.yaml"],
                   capture_output=True, text=True, timeout=600, env={**__import__("os").environ, "MERAVIA_NO_SERVER": "1", "PYTHONUTF8": "1"})
check("the ruling corpus: the lock-picking case stands as the owner decided, no longer known apart",
      r.returncode == 0 and "known" not in r.stdout.splitlines()[-1] and "pick the lock" in r.stdout and "KNW" not in r.stdout,
      (r.returncode, r.stdout[-500:], r.stderr[-300:]))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
