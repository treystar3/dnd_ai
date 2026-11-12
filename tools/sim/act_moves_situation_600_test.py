"""(f600) An act moves a situation, in one call (docs/design/02 section 7). With the act path on, a situation whose trouble is here is in
the act's targets; the act's one ruling (act_ruling) may change its parts, checked by the situation's own rules (a change resting on force
is force to them only when the act was rolled on body or arms, act.yaml force_checks; skill is the work of a hand; a kept force change counts for its own
target alone; the owner, 2026-11-11), written by its own writer, and read for its end at once
(f598). The act's deed names the situations its ruling weighed, so the gate (f597) never asks a second ruling for them. Barring the
granary against the looters moves the situation at every tier, and ends it when the world says so.
Run: python tools/sim/act_moves_situation_600_test.py"""
import random
import sys
import types
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 7)
simlib.install(stub)
simlib.quiet_console()
import config
from engine import act as act_mod, checks, pulse, retrieval, situation_parts, situations, targets
from llm.contracts import SituationParts

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


calls = {"ActRuling": 0, "JudgeVerdict": 0}
for name in calls:
    real = getattr(stub, f"a_{name}")
    setattr(stub, f"a_{name}", (lambda real, name: lambda u, k: calls.__setitem__(name, calls[name] + 1) or real(u, k))(real, name))

g = simlib.campaign("act_moves_600", seed=7, location="trading_square")
ws, store = g.scene, g.store
ws.enter("trading_square")
world = ws.world
town = pulse.town_of(world, "trading_square")
folk = retrieval.people_in_town(store, world, town)
HERE = list(ws.present) or list(ws.residents[:2])
checks.roll = lambda odds, rng=None, c=None: ("success", 1)              # the dice are not what is under test


def looting(tid, tier):
    """Looters in the square: a danger the looting band lays on it, and a stallholder it harms."""
    with ws.operation("test", "looters") as op:
        st = store.load_world_state() or {}
        for k_, v_ in pulse.empty_state(ws.minutes).items():
            st.setdefault(k_, v_)
        th = {"id": tid, "title": f"Looting ({tier})", "tier": tier, "place": "trading_square", "times": [ws.minutes, ws.minutes + 9 * 1440],
              "status": "active", "made": ws.minutes, "clues": [], "paths": [], "stage": 0, "stages": [{"description": "Looters.", "effects": []}],
              "kind": "unrest", "groups": ["everyone"], "fallout": {"description": "The square is stripped.", "effects": []}}
        st.setdefault("threads", []).append(th)
        prop = {"people": [{"who": folk[1].id, "stake": "harmed", "want": "safety"}],
                "conditions": [{"on": "trading_square", "kind": "danger", "label": "looters in the square", "by": "the looting band", "by_kind": "group"}]}
        acc, _ = situations.check(SituationParts.model_validate(prop), store, world, tier, random.Random(7), town=town, ways=False,
                                  now=ws.minutes, players=(ws.acting,))
        situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
        store.save_world_state(st)
    assert op.state == "committed", op.state


def codes(tid):
    ws.present = list(HERE)
    T = targets.targets_for(ws, ws.acting)
    sit = next(t for t in T.rows if t.kind == "situation" and t.ref == tid)
    danger = next(t.code for t in T.rows if t.code.startswith(sit.code + ".") and t.kind == "condition")
    harmed = next(t.code for t in T.rows if t.code.startswith(sit.code + ".") and t.kind == "person")
    return danger, harmed


def part(tid, code):
    return pulse.thread_of(store.load_world_state(), tid)["parts"][int(code.split(".")[1]) - 1]


def act(text):
    ws.present = list(HERE)
    with ws.operation("action:other", text) as op:
        ws.on_other(types.SimpleNamespace(kind="other", summary=text), text)
    return op


check("the data: force is tested on body or arms, never talk or a performance",
      set(act_mod.A["force_checks"]) == {"strength", "dexterity", "constitution", "intimidation"} and not act_mod.problems())

for tier in ("normal", "uncommon", "rare"):
    tid = f"th600_{tier}"
    looting(tid, tier)
    danger, harmed = codes(tid)
    with ws.operation("test", "the others are not here") as op_:       # each tier stands alone: no other looting's parts are in reach
        st = store.load_world_state()
        for x in st["threads"]:
            if x["id"].startswith("th600_") and x["id"] != tid and x["status"] == "active":
                x["status"] = "resolved"
        store.save_world_state(st)
    stub.act_ruling = {"sense": "cost", "why": "a barred door and a show of steel", "stakes": {"check": "intimidation", "hard": "fair"},
                       "changes": [{"n": 1, "target": danger, "becomes": "lifted", "because": "force"},
                                   {"n": 2, "target": harmed, "becomes": "safe", "because": "earlier", "needs": [1]}]}
    calls.update(ActRuling=0, JudgeVerdict=0)
    op = act("I bar the granary door against the looters and drive them off with my sword.")
    th = pulse.thread_of(store.load_world_state(), tid)
    k_danger = int(danger.split(".")[1]) - 1
    k_harmed = int(harmed.split(".")[1]) - 1
    check(f"[{tier}] the act's one ruling lifted the danger the looters laid (force, by its own rules) and made the stallholder safe",
          op.state == "committed" and th["parts"][k_danger].get("now") == "lifted" and th["parts"][k_harmed].get("now") == "safe",
          (op.state, th["parts"][k_danger].get("now"), th["parts"][k_harmed].get("now")))
    check(f"[{tier}] ...and the world read it over: achieved, the player's doing", th["status"] == "resolved" and th.get("ending_kind") == "achieved"
          and th.get("result") == "player", (th["status"], th.get("ending_kind")))
    check(f"[{tier}] ...in one call: the act's ruling, never a second ruling on the situation", calls == {"ActRuling": 1, "JudgeVerdict": 0}, calls)

# ---- what is not force: words, a hand's skill, force claimed on a song; and force is the change's own, never the whole act's
REFUSED = [("words", "performance", "I sing to the looters until they lose heart."),
           ("skill", "intimidation", "I jam the looters' cart wheel with a stake."),
           ("force", "performance", "I sing so fiercely the looters flee.")]
for i, (because, chk, text) in enumerate(REFUSED):
    tid = f"th600_not_{i}"
    looting(tid, "rare")
    danger, harmed = codes(tid)
    stub.act_ruling = {"sense": "cost", "stakes": {"check": chk, "hard": "fair"},
                       "changes": [{"n": 1, "target": danger, "becomes": "lifted", "because": because}]}
    op = act(text)
    th = pulse.thread_of(store.load_world_state(), tid)
    check(f"a danger a band holds is not lifted by {because} on {chk}: the situation's own rules still hold for an act",
          op.state == "committed" and part(tid, danger).get("now") != "lifted" and th["status"] == "active",
          (op.state, part(tid, danger).get("now"), th["status"]))
    with ws.operation("test", "done with it"):
        st = store.load_world_state()
        pulse.thread_of(st, tid)["status"] = "resolved"
        store.save_world_state(st)

tid = "th600_dropped"
looting(tid, "rare")
danger, harmed = codes(tid)
stub.act_ruling = {"sense": "cost", "stakes": {"check": "performance", "hard": "fair"},
                   "changes": [{"n": 1, "target": danger, "becomes": "lifted", "because": "force"},
                               {"n": 2, "target": harmed, "becomes": "safe", "because": "skill"}]}
act("I sing the looters off and lead the stallholder out the back.")
check("a force change the rules refused never makes the rest of the act force: the danger stands",
      part(tid, danger).get("now") != "lifted", part(tid, danger).get("now"))
tid = "th600_kept"
with ws.operation("test", "done with it"):
    st = store.load_world_state()
    pulse.thread_of(st, "th600_dropped")["status"] = "resolved"
    store.save_world_state(st)
looting(tid, "rare")
with ws.operation("test", "a second band"):                           # two dangers, both held by the band
    st = store.load_world_state()
    th = pulse.thread_of(st, tid)
    th["parts"].append(dict(next(a for a in th["parts"] if a.get("kind") == "condition"), label="looters at the well"))
    store.save_world_state(st)
ws.present = list(HERE)
T = targets.targets_for(ws, ws.acting)
sit = next(t for t in T.rows if t.kind == "situation" and t.ref == tid)
d1, d2 = [t.code for t in T.rows if t.code.startswith(sit.code + ".") and t.kind == "condition"][:2]
stub.act_ruling = {"sense": "cost", "stakes": {"check": "strength", "hard": "fair"},
                   "changes": [{"n": 1, "target": d1, "becomes": "lifted", "because": "force"},
                               {"n": 2, "target": d2, "becomes": "lifted", "because": "skill"}]}
op = act("I throw the looters out of the granary and pick the lock on the well's chain.")
check("on strength, the force change is kept: the danger it was done to is lifted", op.state == "committed"
      and part(tid, d1).get("now") == "lifted", (op.state, part(tid, d1).get("now")))
check("...and never spreads to its neighbour: the one done by skill, against a band, is refused", part(tid, d2).get("now") != "lifted",
      part(tid, d2).get("now"))
# ---- (the owner, 2026-11-11) a kept force change counts for its own target: one committed is moved by it, one held away is freed
away = next(p for p in folk if p.id not in {n.id for n in HERE} and p.id != folk[1].id)
guard = next(n.id for n in HERE if n.id != folk[1].id)                 # present, and not the stallholder already harmed
for chk, kept_ in (("strength", True), ("performance", False)):
    tid = f"th600_own_{chk}"
    with ws.operation("test", "done with it"):
        st = store.load_world_state()
        for x in st["threads"]:
            if x["id"].startswith("th600_") and x["status"] == "active":
                x["status"] = "resolved"
        store.save_world_state(st)
    looting(tid, "rare")
    with ws.operation("test", "a guard set against them, and one held away"):
        st = store.load_world_state()
        th = pulse.thread_of(st, tid)
        g_at = len(th["parts"])
        th["parts"].append({"kind": "person", "who": guard, "stake": "blocks", "want": "coin", "willing": {ws.acting: "committed"}})
        th["parts"].append({"kind": "person", "who": away.id, "stake": "harmed", "want": "safety"})
        store.save_world_state(st)
    ws.present = list(HERE)
    T = targets.targets_for(ws, ws.acting)
    mine = {t.ref: t.code for t in T.rows if t.kind == "person"}
    g_code, a_code = mine.get(f"{tid}#{g_at}"), mine.get(f"{tid}#{g_at + 1}")
    check(f"[{chk}] (the guard and the one held away are among the act's targets)", bool(g_code and a_code), sorted(mine))
    stub.act_ruling = {"sense": "cost", "stakes": {"check": chk, "hard": "fair"},
                       "changes": [{"n": 1, "target": g_code, "becomes": "terrified", "because": "force"},
                                   {"n": 2, "target": a_code, "becomes": "safe", "because": "force"}]}
    op = act("I wrestle the guard to the ground and break the lock on the cellar where they keep the trader.")
    th = pulse.thread_of(store.load_world_state(), tid)
    g, a = th["parts"][g_at], th["parts"][g_at + 1]
    check(f"[{chk}] a committed guard {'is' if kept_ else 'is not'} moved by the force done to them",
          op.state == "committed" and (g.get("willing", {}).get(ws.acting) == "terrified") == kept_, (op.state, g.get("willing")))
    check(f"[{chk}] one held out of earshot {'is' if kept_ else 'is not'} freed by force where the trouble is",
          (a.get("now") == "safe") == kept_, a.get("now"))

tid = "th600_own_only"
with ws.operation("test", "done with it"):
    st = store.load_world_state()
    for x in st["threads"]:
        if x["id"].startswith("th600_") and x["status"] == "active":
            x["status"] = "resolved"
    store.save_world_state(st)
looting(tid, "rare")
with ws.operation("test", "a guard set against them"):
    st = store.load_world_state()
    th = pulse.thread_of(st, tid)
    g_at = len(th["parts"])
    th["parts"].append({"kind": "person", "who": guard, "stake": "blocks", "want": "coin", "willing": {ws.acting: "committed"}})
    store.save_world_state(st)
danger, _ = codes(tid)
ws.present = list(HERE)
g_code = {t.ref: t.code for t in targets.targets_for(ws, ws.acting).rows if t.kind == "person"}.get(f"{tid}#{g_at}")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "strength", "hard": "fair"},
                   "changes": [{"n": 1, "target": danger, "becomes": "lifted", "because": "force"},
                               {"n": 2, "target": g_code, "becomes": "terrified", "because": "earlier", "needs": [1]}]}
act("I drive the looters out of the square while the guard watches.")
th = pulse.thread_of(store.load_world_state(), tid)
check("force done to the danger moves only the danger: the committed guard who saw it stands as they were",
      part(tid, danger).get("now") == "lifted" and th["parts"][g_at].get("willing", {}).get(ws.acting) == "committed",
      (part(tid, danger).get("now"), th["parts"][g_at].get("willing")))

tid = "th600_warned"
with ws.operation("test", "done with it"):
    st = store.load_world_state()
    pulse.thread_of(st, "th600_own_only")["status"] = "resolved"
    store.save_world_state(st)
looting(tid, "rare")
ws.present = list(HERE)
lookout = next(t.code for t in targets.targets_for(ws, ws.acting).rows if t.kind == "person" and t.ref == f"{tid}#0")
with ws.operation("test", "the guard is elsewhere"):
    st = store.load_world_state()
    pulse.thread_of(st, tid)["parts"].append({"kind": "person", "who": away.id, "stake": "blocks", "want": "coin",
                                              "willing": {ws.acting: "committed"}})
    w_at = len(pulse.thread_of(st, tid)["parts"]) - 1
    store.save_world_state(st)
ws.present = list(HERE)
w_code = {t.ref: t.code for t in targets.targets_for(ws, ws.acting).rows if t.kind == "person"}.get(f"{tid}#{w_at}")
stub.act_ruling = {"sense": "cost", "stakes": {"check": "strength", "hard": "fair"},
                   "changes": [{"n": 1, "target": lookout, "who": lookout, "becomes": "warns", "about": w_code, "because": "words"},
                               {"n": 2, "target": w_code, "becomes": "terrified", "because": "force", "needs": [1]}]}
act("I shove the stallholder toward the cellar to warn the other guard, and hope my fists carry.")
th = pulse.thread_of(store.load_world_state(), tid)
check("one only warned, never there, is not moved by force: force is done in person",
      th["parts"][w_at].get("willing", {}).get(ws.acting) == "committed", th["parts"][w_at].get("willing"))

check("...and the act itself is no violent act to the situation's rules", "acted_by_force" not in situation_parts.S["rulings"]["force_acts"]
      and "acted" not in situation_parts.S["rulings"]["force_acts"])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
