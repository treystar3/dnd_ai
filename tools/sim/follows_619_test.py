"""(f619) What follows from a change is the engine's to say, never a ruling's to remember. On the pod the model drove the looters off the
granary (the danger lifted) and never said the stallholder was safe, in both passes, and the case counted its moves wrong (the audit
of 2026-11-13, docs/design/18 part C). A consequence is not a judgement: one the situation's heart says is harmed is safe when the heart
names a threat and every one is resolved, whoever resolved it and however (an act, a way met, time). One step says so
(engine/situation_parts.py follow, from the table in data/rules/situations.yaml `follows`), run wherever a situation is read
(engine/events.py read_end, read_ends): it gives the word and takes it back when the condition no longer holds, and never touches a
word a ruling gave. A ruling may still make someone safe by an act of its own (led out while the danger stands). The measure judges a
case's `moves` on what the engine would leave, kept and followed (tools/ruling_eval.py), by a dry run of the engine's own writers.
Run: python tools/sim/follows_619_test.py"""
import copy
import os
import sys
import types
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("MERAVIA_NO_SERVER", "1")
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


from tools import ruling_eval as R
from engine import act, checks, events, pulse, situation_parts as SP

HARMED = {"here": True, "stake": "harmed", "want": "safety"}
BLOCKS = {"here": True, "stake": "blocks", "want": "coin", "against": "committed"}
LOOT = {"kind": "danger", "label": "looters in the square", "by": "the looting band", "by_kind": "group"}
SHUT = {"kind": "closed", "label": "the mill shut by the quarrel", "by": "the millers", "by_kind": "group"}
FEVER = {"kind": "danger", "label": "fever in the well water", "by": "the fouled well", "by_kind": "group"}

b = R.Bench(save="follows_619")
ws, store = b.ws, b.store
try:
    def sit(people, conditions, title="Trouble"):
        b.put({"line": "x", "at": "trading_square", "expect": "cost", "situation": {"tier": "rare", "title": title, "people": people,
                                                                                   "conditions": conditions}})
        state = store.load_world_state()
        return state, pulse.thread_of(state, b.sit)
    def change(state, th, part, word, because="force"):
        SP.keep_changes(ws, state, th, {"kind": "acted", "by": ws.acting, "npc": "", "witnesses": [], "place": "trading_square"},
                        [{"n": 1, "part": part, "who": 0, "becomes": word, "because": because, "needs": []}])
    def now(th, part):
        return th["parts"][part - 1].get("now", "")
    def standing(state, th):
        return [s for x, s in SP.reading(store, ws.world, state, th, ws.minutes).stakes if x["kind"] == "person"]

    # ---- the data
    F = SP.S.get("follows") or {}
    check("the table says what follows: safe, for a person at stake, when every threat is resolved", F.get("safe") == {"stake": "person",
          "when": "threats_resolved"}, F)
    check("...and it checks clean", SP.problems() == [], SP.problems())
    real = copy.deepcopy(F)
    for wrong in ({"safe": {"stake": "person", "when": "whenever"}}, {"safe": {"stake": "horse", "when": "threats_resolved"}},
                  {"happy": {"stake": "person", "when": "threats_resolved"}}, {"safe": {"stake": "resource", "when": "threats_resolved"}}):
        SP.S["follows"] = wrong
        check(f"...a row that names no real word, stake or test, or a word its kind of stake cannot take, is named at startup ({wrong})", any("follows" in p for p in SP.problems()), SP.problems())
    SP.S["follows"] = real

    # ---- the step, on situations of several shapes
    state, th = sit([HARMED], [LOOT], "Looting")
    check("while the danger stands, nothing follows", SP.follow(store, state, th, ws.minutes) == [] and now(th, 1) == "" and standing(state, th) == ["at_risk"])
    change(state, th, 2, "lifted")
    got = SP.follow(store, state, th, ws.minutes)
    check("the danger lifted, the one it harmed is safe, said by the engine with no ruling asking", got == [(0, "safe")] and now(th, 1) == "safe"
          and standing(state, th) == ["secured"], (got, th["parts"][0]))
    check("...said once: nothing more follows from the same world", SP.follow(store, state, th, ws.minutes) == [])
    check("...and nobody is credited for what followed (the record holds the act alone)", [c["becomes"] for c in th["changes"]] == ["lifted"], th["changes"])

    state, th = sit([HARMED, HARMED], [SHUT, FEVER], "The mill")
    change(state, th, 3, "lifted")
    first = SP.follow(store, state, th, ws.minutes)
    change(state, th, 4, "lifted")
    second = SP.follow(store, state, th, ws.minutes)
    check("two threats, another kind of trouble: one resolved leaves everyone at stake as they were; both, and each of them is safe",
          first == [] and second == [(0, "safe"), (1, "safe")] and standing(state, th) == ["secured", "secured"], (first, second))

    state, th = sit([HARMED, BLOCKS], [LOOT], "The hoard")
    change(state, th, 3, "lifted")
    first = SP.follow(store, state, th, ws.minutes)
    th["parts"][1]["willing"][ws.acting] = "open"
    second = SP.follow(store, state, th, ws.minutes)
    th["parts"][1]["willing"][ws.acting] = "hostile"
    third = SP.follow(store, state, th, ws.minutes)
    check("one who blocks an end to it is a threat too: safe only once they stand down, and no longer when they stand against it again",
          first == [] and second == [(0, "safe")] and third == [(0, "")] and now(th, 1) == "" and "follows" not in th["parts"][0],
          (first, second, third, th["parts"][0]))

    state, th = sit([{"here": False, "stake": "harmed", "want": "safety"}], [LOOT], "The kidnapping")
    change(state, th, 1, "safe")
    got = SP.follow(store, state, th, ws.minutes)
    check("a ruling may still make someone safe by an act of its own, the danger standing: that word is the ruling's, and is never taken back",
          got == [] and now(th, 1) == "safe" and "follows" not in th["parts"][0], (got, th["parts"][0]))

    # ---- a word that followed is the engine's until someone earns it: a later act that does it is kept, credited, and then theirs
    state, th = sit([{"here": False, "stake": "harmed", "want": "safety"}, BLOCKS], [LOOT], "The kidnapping")
    change(state, th, 3, "lifted")
    th["parts"][1]["willing"][ws.acting] = "open"
    SP.follow(store, state, th, ws.minutes)
    doing = {**act.acted(ws, ws.acting), "witnesses": [th["parts"][1]["who"]]}
    kept, dropped = SP.ruled(store, th, doing, [{"n": 1, "part": 1, "who": 0, "becomes": "safe", "because": "force", "needs": []}], world=ws.world)
    check("one the engine left safe may still be led out by an act: the act's change is kept, not refused as done already",
          now(th, 1) == "safe" and [c["becomes"] for c in kept] == ["safe"] and not dropped, (th["parts"][0], kept, dropped))
    SP.keep_changes(ws, state, th, doing, kept)
    th["parts"][1]["willing"][ws.acting] = "hostile"
    got = SP.follow(store, state, th, ws.minutes)
    check("...and from then the word is the act's: on its record, and not taken back when a threat stands again",
          got == [] and now(th, 1) == "safe" and "follows" not in th["parts"][0] and th["changes"][-1]["becomes"] == "safe"
          and ws.acting in SP.contributors(th), (got, th["parts"][0], th["changes"][-1]))

    state, th = sit([HARMED], [LOOT], "Looting")
    change(state, th, 2, "lifted")
    th["status"] = "resolved"
    check("a situation that is over is left as it ended: nothing follows", SP.follow(store, state, th, ws.minutes) == [] and now(th, 1) == "")

    state, th = sit([HARMED], [], "A fright")
    check("a heart that names no threat: its objective is its stakes, and nothing follows of itself",
          SP.follow(store, state, th, ws.minutes) == [] and now(th, 1) == "")

    state, th = sit([HARMED], [LOOT], "Looting")
    change(state, th, 2, "lifted")
    gone = types.SimpleNamespace(npc_exists=lambda nid: False, load_npc=store.load_npc)
    check("one who is gone is not made safe", SP.follow(gone, state, th, ws.minutes) == [] and now(th, 1) == "")

    # ---- wherever a situation is read: time alone (the pulse), nobody having touched it
    state, th = sit([HARMED], [FEVER], "The well")
    for e in state["effects"]:
        if e.get("thread") == th["id"]:
            e["until"] = ws.minutes - 1
    with ws.operation("follows_619", "the fever runs its course"):
        store.save_world_state(state)
        events.read_ends(ws)
    state = store.load_world_state()
    th = pulse.thread_of(state, b.sit)
    check("a danger that ran out with nobody's hand in it: the one it harmed is safe on the saved world, and the situation keeps its own end",
          now(th, 1) == "safe" and th["status"] == "active", (th["parts"][0], th["status"]))

    # ---- a way met: the one who imposed it won over, with no ruling at all
    state, th = sit([HARMED, BLOCKS], [SHUT], "The toll")
    boss = th["parts"][1]["who"]
    th["parts"][2].update(by=boss, by_kind="person")
    for x in th["heart"]["threats"]:
        if x.get("part") == 2:
            x.update(by=boss, by_kind="person")
    with ws.operation("follows_619", "the toll keeper is won over"):
        SP.met_way(ws, state, th, {"target": boss, "kind": "persuade"}, ws.acting)
        ended = events.read_end(ws, state, th, "by way of 'Win them over'")
        store.save_world_state(state)
    th = pulse.thread_of(store.load_world_state(), b.sit)
    check("a way met (the one who shut it won over, what they imposed lifted with them): the one it harmed is safe, and it ends achieved",
          ended and now(th, 3) == "lifted" and now(th, 1) == "safe" and th.get("ending_kind") == "achieved",
          (ended, th["parts"][0], th["parts"][2].get("now"), th.get("ending_kind")))

    # ---- in play: an act lifts the danger and its ruling never mentions the one it harmed
    state, th = sit([HARMED], [SHUT], "The mill")
    T = b.targets()
    scode = next(t.code for t in T.rows if t.kind == "situation" and t.ref == b.sit)
    told = []
    real_narrate, real_roll = ws.narrate, checks.roll
    ws.narrate = lambda event, text="": told.append(event)
    checks.roll = lambda odds, rng=None, c=None: ("success", 1)
    b.stub.act_ruling = {"sense": "cost", "why": "x", "works": "The millers stand aside and the wheel turns.", "stakes": {"check": "strength", "hard": "fair"},
                         "fail": next(iter(act.A["fails"])), "changes": [{"n": 1, "target": f"{scode}.2", "becomes": "lifted", "because": "force"}]}
    try:
        with ws.operation("action:other", "I drag the millers apart and set the wheel turning."):
            ws.on_other(types.SimpleNamespace(kind="other", summary="drag the millers apart and set the wheel turning"),
                        "I drag the millers apart and set the wheel turning.")
    finally:
        ws.narrate, checks.roll = real_narrate, real_roll
    state = store.load_world_state()
    th = pulse.thread_of(state, b.sit)
    said = told[-1] if told else ""
    name = b.names[0]
    check("the act's ruling lifts the trouble and says nothing of the miller: the engine leaves them safe, and the narrator is told so",
          now(th, 2) == "lifted" and now(th, 1) == "safe" and "(safe)" in said and "(lifted)" in said, (th["parts"][0], said[-400:]))
    check("...and the situation ends achieved, by the one who acted", th["status"] != "active" and th.get("ending_kind") == "achieved",
          (th["status"], th.get("ending_kind")))

    # ---- the measure: a case's moves judged on what the engine would leave, and nothing written to do it
    GRAN = {"line": "I bar the granary door and drive the looters off with my sword.", "at": "trading_square", "expect": "cost",
            "situation": {"tier": "rare", "title": "Looting", "people": [HARMED], "conditions": [LOOT]},
            "model": {"sense": "cost", "stakes": {"check": "intimidation", "hard": "fair"},
                      "changes": [{"n": 1, "target": "@condition", "becomes": "lifted", "because": "force"}]},
            "moves": {"@condition": "lifted", "@person:1": "safe"}}
    got = b.offline(GRAN, "new")
    state = store.load_world_state()
    th = pulse.thread_of(state, b.sit)
    check("the granary as the pod's model ruled it (lifted, the stallholder never named): its moves are right",
          got == ("yes", True), got)
    check("...and the dry run wrote nothing: the case's own world is as it was put", now(th, 1) == "" and now(th, 2) == "" and not th.get("changes"),
          (th["parts"][0], th.get("changes")))
    got = b.offline({**GRAN, "situation": {**GRAN["situation"], "people": [HARMED, BLOCKS]}}, "new")
    check("...with one who blocks still standing, the same ruling leaves the stallholder as they were: moves wrong", got == ("yes", False), got)
    got = b.offline({**GRAN, "line": "I drive the looters off.", "moves": {"@condition": "lifted", "@person:1": False}}, "new")
    check("...and a case that says the act leaves someone alone is wrong when safety follows", got == ("yes", False), got)
    got = b.offline({**GRAN, "model": {**GRAN["model"], "changes": [{"n": 1, "target": "@condition", "becomes": "lifted", "because": "words"}]},
                     "moves": {"@condition": False, "@person:1": False}}, "new")
    check("...a change the engine refuses moves nothing, and nothing follows from it", got == ("yes", True), got)
    refused = None
    try:
        R.Dry(ws).store.delete_entity("x")
    except AttributeError as e:
        refused = str(e)
    check("...the dry run's store reads, drops the writes the writers make, and stops at any call it does not know",
          refused is not None and R.Dry(ws).store.npc_exists(th["parts"][0]["who"]) and R.Dry(ws).store.save_npc(None) is None, refused)

    cases = yaml.safe_load((ROOT / "data/replay/ruling_cases_act.yaml").read_text(encoding="utf-8"))
    gran = next(c for c in cases if c["line"].startswith("I bar the granary door"))
    check("the corpus's granary case, whose ruling names the stallholder safe itself, is right as it was: no corpus line changed for this",
          [ch["becomes"] for ch in gran["model"]["changes"]] == ["lifted", "safe"] and gran["moves"] == {"@condition": "lifted", "@person:1": "safe"}
          and b.offline(gran, "new") == ("yes", True), gran)
    wrong = []
    for c in cases:
        out = b.offline(c, "new")
        if out is not None and "moves" in c and out[1] is not True and not c.get("known"):
            wrong.append((c["line"], out))
    check("every case of the act corpus that says its moves has them right offline", not wrong, wrong)
finally:
    b.clear()
    b.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
