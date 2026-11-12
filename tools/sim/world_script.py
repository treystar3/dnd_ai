"""(f579) A seeded world, played the same way every time: the gate for moving world state out of its one row.

The kept recordings change the world's state in 6 of their 83 inputs and start with no matters, deeds, news or effects, so "the
recordings replay" proves little about where that state is kept. This script plays one stub campaign through the writers the game
uses (typed lines, the pulse over many days, deeds, endings, news, effects) and takes the loaded world after every step, as text. Its
coverage is counted, not assumed: a matter ended by the player with its settled deed, a rare matter ruled on through its parts (f597:
the old judge's ending is gone) and ended by the reading of the world (f598), (f605) an act on the act path that moves a matter in
one ruling, a rule of the town's answered, news told twice
folded into one row, news past its cap with a deed's tale kept, an effect lifted with its matter and later dropped, finished matters
past what is kept, deeds past their cap, the history at its cap, and an operation that wrote the world and was rolled back.

    python tools/sim/world_script.py NAME --out FILE     one play in a process of its own: {"steps": [[label, the world as text]],
                                                         "cover": {what: bool}, "other": the digest of every table of the save,
                                                         "calls": the model's calls over the play, by kind (f605)}
    world_script.run_apart("name")                       the same from a test: the play's dict (the stand-in model numbers what it
                                                         invents by a count the process keeps, so two plays compared share none)
    play(name, stub, prepare=fn)                         in this process; fn(game) before anything is written: where a storage
                                                         under test is put in place

Used by world_script_579_test (two plays agree step by step) and by the storage features after it (old storage against new)."""
from __future__ import annotations

import json
import sys

sys.path.insert(0, ".")
import simlib

SEED = 11
PLACE = "trading_square"


class Run:
    def __init__(self, game):
        self.game, self.steps, self.cover, self.other, self.calls = game, [], {}, {}, {}


def world_text(store) -> str:
    """The loaded world as text, keys in the order they are held (a storage that reorders them is caught)."""
    return json.dumps(store.load_world_state(), ensure_ascii=False)


def play(name: str, stub, seed: int = SEED, prepare=None) -> Run:
    import config
    from engine import deeds, pulse, standing
    from engine.domain_events import CreatureKilled
    from llm.gateway import LLMError
    from storage import statehash
    g = simlib.campaign(name, seed=seed, location=PLACE)
    if prepare:
        prepare(g)
    run = Run(g)
    ws, store = g.scene, g.store
    config.TURN_LOG_PATH = f"saves/{name}/turns.jsonl"     # its typed lines are logged in its own save, not the shared log
    ws.enter(PLACE)
    world = ws.world
    town = pulse.town_of(world, PLACE)
    n = [0]

    def snap(label: str) -> None:
        run.steps.append((label, world_text(store)))

    def state() -> dict:
        return store.load_world_state()

    def days(count: int) -> None:
        """Game days pass and the world moves on, as it does behind a line (scenes/world.py run_pulse)."""
        store.meta.minutes += count * 1440
        store.save_meta()
        ws.run_pulse()

    def born(tier: str = "normal", paths=(), stage: int = 0) -> str:
        n[0] += 1
        tid = f"thw{n[0]}"
        t = ws.minutes
        st = state() or pulse.empty_state(t)
        st.setdefault("threads", []).append({"id": tid, "title": f"Trouble {n[0]}", "tier": tier, "place": PLACE,
                                             "times": [t, t + 6 * 1440, t + 12 * 1440], "status": "active", "made": t, "clues": [],
                                             "paths": [dict(p) for p in paths], "stage": stage,
                                             "stages": [{"description": "Trouble.", "effects": []}, {"description": "Worse.", "effects": []}],
                                             "kind": "trouble", "groups": ["everyone"], "fallout": {"description": "", "effects": []},
                                             "resolution": "", "triumph": None})
        store.save_world_state(st)
        return tid

    def thread(tid: str) -> dict | None:
        return next((x for x in state().get("threads", []) if x["id"] == tid), None)

    def kill(creature: str) -> None:
        with ws.operation("action:attack", f"kill the {creature}"):
            ws.notice(CreatureKilled(minute=ws.minutes, place=PLACE, witnesses=(), creature=creature, level=1))

    def ruled_rare(conditions=()) -> str:
        """(f597) A rare matter with parts: a townsperson it harms; (f605) and the conditions given."""
        import random
        from engine import retrieval, situation_parts, situations
        from llm.contracts import SituationParts
        tid = born(tier="rare", stage=1)
        st = state()
        th = next(x for x in st["threads"] if x["id"] == tid)
        who = retrieval.people_in_town(store, world, town)[0]
        acc, _ = situations.check(SituationParts.model_validate({"people": [{"who": who.id, "stake": "harmed", "want": "safety"}],
                                                                 "conditions": list(conditions)}),
                                  store, world, "rare", random.Random(seed), town=town, ways=False, now=ws.minutes, players=(ws.acting,))
        with ws.operation("test", "a rare matter's parts"):
            situation_parts.register(store, world, st, th, acc, ws.minutes, catalog=ws.catalog, ways=False)
            store.save_world_state(st)
        return tid

    def gift(tid: str, item: str = "a loaf") -> None:
        """(f597) A gift to the matter's person, as the world notices one: the reaction logs the deed, then rules on it."""
        from engine.domain_events import Gift
        th = thread(tid)
        who = next(a["who"] for a in th["parts"] if a.get("kind") == "person")
        with ws.operation("action:give", "give a loaf"):
            ws.notice(Gift(minute=ws.minutes, place=PLACE, witnesses=(), npc=who, name=store.load_npc(who).name, item=item, count=1))

    def acted() -> None:
        """(f605) An act on the act path (f595, f600): looters lay a danger on the square and harm a townsperson there; the act's one
        ruling lifts the danger by force on a roll of the arms and makes them safe, and the world reads the matter over at once."""
        import types
        from engine import checks, targets
        looted = ruled_rare([{"on": PLACE, "kind": "danger", "label": "looters in the square", "by": "the looting band", "by_kind": "group"}])
        harmed = next(a["who"] for a in thread(looted)["parts"] if a.get("kind") == "person")
        present, roll, act_on, ruling = list(ws.present), checks.roll, config.ACT, getattr(stub, "act_ruling", None)
        ws.present = present + ([store.load_npc(harmed)] if harmed not in {n.id for n in present} else [])
        config.ACT, checks.roll = True, (lambda odds, rng=None, c=None: ("success", 1))   # the dice are not what the script covers
        try:
            rows = targets.targets_for(ws, ws.acting).rows
            sit = next(t.code for t in rows if t.kind == "situation" and t.ref == looted)
            danger = next(t.code for t in rows if t.code.startswith(sit + ".") and t.kind == "condition")
            person = next(t.code for t in rows if t.code.startswith(sit + ".") and t.kind == "person")
            stub.act_ruling = {"sense": "cost", "stakes": {"check": "intimidation", "hard": "fair"},
                               "changes": [{"n": 1, "target": danger, "becomes": "lifted", "because": "force"},
                                           {"n": 2, "target": person, "becomes": "safe", "because": "earlier", "needs": [1]}]}
            before = {k: stub.calls.get(k, 0) for k in ("ActRuling", "JudgeVerdict")}
            text = "I bar the granary door and drive the looters off."
            with ws.operation("action:other", text):
                ws.on_other(types.SimpleNamespace(kind="other", summary=text), text)
            spent = {k: stub.calls.get(k, 0) - v for k, v in before.items()}
        finally:
            stub.act_ruling, config.ACT, checks.roll, ws.present = ruling, act_on, roll, present
        snap("an act moves a matter, in one ruling")
        th = thread(looted) or {}
        made = {(c.get("becomes"), c.get("act")) for c in th.get("changes") or []}        # the act's own changes ended it
        run.cover["an act moved a matter, in one ruling"] = (th.get("status") == "resolved" and th.get("ending_kind") == "achieved"
                                                            and spent == {"ActRuling": 1, "JudgeVerdict": 0}
                                                            and {("lifted", "acted"), ("safe", "acted")} <= made)

    # ---- lines typed, and days passing
    ws.turn("look around")
    snap("a first line")
    for i in range(6):
        days(3)
        snap(f"three days pass ({i + 1})")
    run.cover["the pulse left matters, news or history of its own"] = any(state().get(k) for k in ("threads", "news", "history"))

    # ---- matters the player ends, and what the town makes of them
    way = {"kind": "kill", "target": "wolf", "name": "kill the wolves", "how": "the wolves are killed", "done": False}
    first = born(paths=[way])
    snap("a matter begins")
    kill("wolf")
    snap("the player ends it by one of its ways")
    second = born(paths=[dict(way, target="boar")])
    kill("boar")
    snap("and ends a second in the same region")
    st = state()
    run.cover["a matter ended by the player"] = all((thread(t) or {}).get("result") == "player" for t in (first, second))
    run.cover["its settled deed kept, numbered"] = (len([d for d in st.get("deeds", []) if d["kind"] == "settled"]) == 2
                                                    and st.get("seq") == max(d.get("seq", 0) for d in st["deeds"]))
    rare = ruled_rare()
    stub.changes = [{"n": 1, "part": 1, "who": 0, "becomes": "warmer", "because": "goods"}]
    gift(rare)
    stub.changes = None
    snap("a rare matter's person moved by a gift, ruled on through its parts")
    run.cover["a matter ruled on through its parts"] = any(c.get("becomes") == "warmer" for c in (thread(rare) or {}).get("changes") or [])
    stub.changes = [{"n": 1, "part": 1, "who": 0, "becomes": "safe", "because": "force"}]
    gift(rare, "a warm cloak")
    stub.changes = None
    snap("the one it harmed made safe: the world reads it over")
    run.cover["a matter ended by the reading"] = ((thread(rare) or {}).get("status") == "resolved"
                                                  and (thread(rare) or {}).get("ending_kind") == "achieved")
    acted()
    before = len(state().get("threads", []))
    for i in range(4):
        days(2)
        snap(f"two days pass after the endings ({i + 1})")
    run.cover["the world went on after them"] = state().get("last", 0) > st.get("last", 0) and len(state().get("threads", [])) >= before

    # ---- news: a tale told twice, a deed's tale, and the cap
    st = state()
    t = ws.minutes
    pulse.add_news(st, "The mill wheel is cracked.", PLACE, t, ["everyone"], certainty="they say")
    pulse.add_news(st, "The ferry is late again.", PLACE, t, ["everyone"])
    pulse.add_news(st, "The mill wheel is cracked.", PLACE, t + 60, ["merchants"], certainty="they say", source="npc:ost")
    store.save_world_state(st)
    snap("news told twice is one row")
    told = [x for x in state()["news"] if x["text"] == "The mill wheel is cracked."]
    run.cover["news folded and moved to the end"] = (len(told) == 1 and told[0].get("times") == 2 and state()["news"][-1] is not None
                                                     and state()["news"][-1]["text"] == "The mill wheel is cracked.")
    public = next(k for k, r in standing.DEEDS.items() if r.get("public"))
    tale = standing.report(store, world, ws.player, public, town, world.places[PLACE].name, ws.player.character.name, t + 90,
                           (t + 90) // 1440, seed=seed)
    snap("a deed becomes a tale")
    st = state()
    for i in range(pulse.NEWS_KEEP + 12):
        pulse.add_news(st, f"Talk of the day, number {i}.", PLACE, t + 120 + i, ["everyone"], certainty="they say")
    store.save_world_state(st)
    snap("news past its cap")
    news = state()["news"]
    run.cover["news at its cap, the oldest gossip gone and the deed's tale kept"] = (
        tale is not None and len(news) == pulse.NEWS_KEEP and any((x.get("deed") or {}).get("id") == tale["deed"]["id"] for x in news)
        and not any(x["text"] == "The ferry is late again." for x in news))

    # ---- an effect laid by a matter, lifted with it, dropped a day on
    priced = born(tier="uncommon")
    st = state()
    pulse.apply_effects(store, world, ws.catalog, st, [{"kind": "prices", "place": PLACE, "value": 1.3, "days": 9},
                                                       {"kind": "danger", "place": PLACE, "value": 1.2, "days": 9}],
                        "uncommon", ws.minutes, "Trouble", raw=True, thread_id=priced)
    store.save_world_state(st)
    snap("a matter lays its effects")
    laid = [e for e in state()["effects"] if e.get("thread") == priced]
    st = state()
    th = next(x for x in st["threads"] if x["id"] == priced)
    pulse.end_thread(store, st, th, "fallen", "Trouble came to nothing.", ws.minutes + 30)
    store.save_world_state(st)
    snap("the matter ends and its effects are lifted")
    lifted = [e for e in state()["effects"] if e.get("thread") == priced]
    run.cover["an effect lifted with its matter"] = (len(laid) == 2 and len(lifted) == 2
                                                    and all(e["until"] == ws.minutes + 30 for e in lifted)
                                                    and all(e["until"] > ws.minutes + 30 for e in laid))
    days(3)
    st = state()
    pulse.apply_effects(store, world, ws.catalog, st, [{"kind": "prices", "place": PLACE, "value": 0.9, "days": 2}],
                        "normal", ws.minutes, "A good harvest", raw=True)
    store.save_world_state(st)
    snap("a later effect drops the lifted ones")
    run.cover["a lifted effect dropped a day on"] = (not any(e.get("thread") == priced for e in state()["effects"])
                                                    and any(e.get("cause") == "A good harvest" for e in state()["effects"]))

    # ---- the caps: finished matters, deeds, history
    for i in range(pulse.FINISHED_KEPT + 6):
        tid = born()
        st = state()
        th = next(x for x in st["threads"] if x["id"] == tid)
        pulse.end_thread(store, st, th, "fallen", f"Trouble {n[0]} came to nothing.", ws.minutes + i)
        store.save_world_state(st)
    snap("finished matters past what is kept")
    done = [x for x in state()["threads"] if x["status"] != "active"]
    run.cover["finished matters trimmed to what is kept"] = len(done) == pulse.FINISHED_KEPT and thread(first) is None
    seq = state().get("seq", 0)
    for i in range(deeds.KEEP + 15):
        deeds.log(store, "found", ws.minutes + i, PLACE, thread=f"x{i}", by=ws.acting)
    snap("deeds past their cap")
    st = state()
    run.cover["deeds at their cap, the count still rising"] = (len(st["deeds"]) == deeds.KEEP and st["seq"] == seq + deeds.KEEP + 15
                                                              and st["deeds"][-1]["seq"] == st["seq"])
    keep = int(pulse.P.get("history_keep", 200))
    for i in range(keep + 9):
        pulse.add_history(st, f"Something happened, number {i}.", PLACE, ws.minutes + i)
    store.save_world_state(st)
    snap("the history past its cap")
    run.cover["history at its cap"] = (len(state()["history"]) == keep
                                       and state()["history"][-1]["text"] == f"Something happened, number {keep + 8}.")

    # ---- an operation that wrote the world and did not stand
    held = world_text(store)
    with ws.operation("test", "a step that writes the world and fails") as op:
        st = state()
        pulse.add_news(st, "A thing that never happened.", PLACE, ws.minutes, ["everyone"])
        deeds.add(st, "found", ws.minutes, PLACE, thread="never", by=ws.acting)
        st["threads"].append({"id": "never", "title": "Never", "tier": "normal", "place": PLACE, "status": "active", "made": ws.minutes})
        st["effects"].append({"kind": "prices", "place": town, "value": 2, "until": ws.minutes + 1440, "cause": "never", "thread": "never"})
        store.save_world_state(st)
        wrote = world_text(store) != held
        raise LLMError("the model failed")
    snap("a failed operation's writes are taken back")
    run.cover["an operation that wrote the world rolled back whole"] = wrote and op.state == "rolled_back" and world_text(store) == held

    # ---- and the world goes on
    days(2)
    snap("two more days")
    ws.turn("wait a while")
    snap("a last line")
    run.other = {k: v for k, v in statehash.digest(store).items()}
    run.calls = dict(sorted(stub.calls.items()))
    return run


def run_apart(name: str, seed: int = SEED, extra: tuple = ()) -> dict:
    """One play in a child process; what it wrote."""
    import os
    import subprocess
    from pathlib import Path
    out = Path("saves") / f"{name}.world_script.json"     # beside the play's save, written over by the next run
    done = subprocess.run([sys.executable, __file__, name, "--seed", str(seed), "--out", str(out), *extra], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env={**os.environ, "PYTHONUTF8": "1"})
    if done.returncode != 0 or not out.exists():
        raise RuntimeError(f"world_script {name} failed:\n{done.stdout[-1500:]}\n{done.stderr[-3000:]}")
    return json.loads(out.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    import argparse
    from pathlib import Path
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("name")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    stub = simlib.Stub("warrior", 3)
    simlib.install(stub)
    simlib.quiet_console()
    run = play(a.name, stub, seed=a.seed)
    run.game.session.close()
    Path(a.out).write_text(json.dumps({"steps": run.steps, "cover": run.cover, "other": run.other, "calls": run.calls}, ensure_ascii=False),
                           encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
