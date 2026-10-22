"""Measure how the game reads what the player types: a corpus of lines, each with the scene it was typed in and what should happen, run
through the real intercepts and plan rewrites (scenes/world.py handle()) on a real scene with the model stubbed, or with the model live.

    python tools/interp_eval.py                       offline: the model's reading is the case's own `plan`; what is measured is everything
                                                      around the model - which intercept takes the line, what the rewrites make of the plan
    python tools/interp_eval.py --live                the real model reads every line (needs Ollama); its reading is measured too
    python tools/interp_eval.py --only road,bram      only the cases whose name contains one of these
    python tools/interp_eval.py --promote logs/turns.jsonl -1     a case stub from a logged turn (engine/turnlog.py rows; edit `expect`)

Cases live in data/replay/interp_cases.yaml:
    name, text          the line as typed
    scene               place (id), minutes, rank, guild_done, mentor_stage, level, present [{id, name, role}], party [{name, role}],
                        hire_last (a hire who spoke last turn), errand (the first hire has asked something), clarify (a question is pending),
                        partner / last_spoken (an id from present), pack [good id | gear base id | raw:<material>], key_items [names],
                        stash [good ids], ground [good ids], abilities [{id, name, effect, context}], wildlife (a creature id),
                        quests [{kind, title, creature, place}], board (true: the hall's board is laid out), prisoners [{id, name}],
                        dungeon (a wild place id: the player stands at the dungeon beneath it), delve (true: and is inside it)
    plan                what the model is taken to have read, offline: a list of intents ({kind, target, item...})
    expect              handled_by (the intercept's name, or interpret), kinds (the kinds that ran, in order), first (fields of the first),
                        steps [{field: value} per step, in order], most (no more than this many steps ran), moves (destinations, in order)
The suite runs the offline mode (tools/sim/interp_eval_test.py); the offline run is deterministic and needs no model. --live is the real
measure: the whole corpus takes the model a good while, and that is the point - one thorough run rather than many quick ones. It ends
with the count right and a table by kind."""
from __future__ import annotations

import argparse
import json
import random
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml

CASES = ROOT / "data" / "replay" / "interp_cases.yaml"
SAVE = "interp_eval"


def load_cases(path=CASES) -> list[dict]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or []


class Bench:
    """One scene, re-dressed for each case: who is here, who travels with the player, where they stand, what the mentor is up to."""

    def __init__(self, live: bool = False):
        import simlib
        from llm import gateway as gw
        real = gw._client                                      # the real Ollama client, before the stand-in takes its place
        self.stub = simlib.Stub("warrior", 5)
        simlib.install(self.stub)
        if live:                                               # --live: the interpreter's own calls reach the model; the rest of the scene stays stubbed
            import types
            stub_chat = self.stub.chat

            def chat(**k):
                if (k.get("format") or {}).get("title") == "ActionPlan":
                    return real.chat(**k)
                return stub_chat(**k)
            gw._client = types.SimpleNamespace(chat=chat)
        import config
        from engine import actions
        from npc.traits import load_traits
        from scenes import quirk_actions
        from scenes.world import WorldScene
        from storage.campaign import CampaignStore, PlayerState
        from world.loader import load_world
        import ui.console as uc
        self.notes: list[str] = []
        uc.note = lambda m, *a, **k: self.notes.append(str(m))
        self.world = load_world()
        shutil.rmtree(f"saves/{SAVE}", ignore_errors=True)
        self.store = CampaignStore.open_or_create(SAVE)
        self.store.meta.seed = 3; self.store.meta.turn = 1; self.store.meta.minutes = 120; self.store.save_meta()
        char, _ = simlib.make_character("warrior", random.Random(1))
        self.store.save_player(PlayerState(character=char, location="trading_square"))
        self.ws = WorldScene(self.store, self.world, load_traits(), self.store.load_player())
        self.ws.player.mentor["never"] = True
        config.TURN_LOG_PATH = f"saves/{SAVE}/turns.jsonl"
        config.AUDIT_ENABLED = False
        self.live = live
        self.ran: list = []
        self.moves: list[str] = []
        self.talked: list[str] = []
        self.hire: list[tuple] = []
        ws = self.ws
        for k in actions.KINDS:
            setattr(ws, f"on_{k}", lambda intent, text, k=k: self.ran.append((k, intent)))
        ws.run_checks = lambda intent, text: False
        ws.on_move = lambda intent, text: (self.moves.append(intent.destination), self.ran.append(("move", intent)))
        ws.leave_by = lambda gp, text: self.moves.append(gp["members"][0]["to"])       # a way out is recorded as where it leads, not travelled
        uc.ask = lambda *a, **k: ""                                                     # nothing in a case may stop to ask the player
        ws.mentor_talk = lambda t: self.talked.append(t)
        ws.hire_talk = lambda m, t: self.hire.append((m["name"], t))
        quirk_actions.quirks.errand_text = lambda *a, **k: "x"
        quirk_actions.rules.remember = lambda *a, **k: None
        self.plan: list = []
        self.base_actives = list(ws.player.character.actives)
        if not live:
            from llm.contracts import ActionIntent, ActionPlan

            def read(text, hint=""):                      # offline: the case's plan, through the same contract the model's reading goes through
                plan = ActionPlan(actions=[ActionIntent(**dict(p)) for p in self.plan])
                ws.dropped_steps = [(a.summary or a.kind).strip() for a in plan.dropped]
                return plan.actions
            ws.interpret = read

    def dress(self, sc: dict) -> None:
        from engine import mentor
        from npc.models import NPC
        ws = self.ws
        ws.player.location = sc.get("place", "trading_square")
        self.store.meta.minutes = int(sc.get("minutes", 120))
        ws.player.guild_rank = sc.get("rank", "")
        ws.player.guild_done = dict(sc.get("guild_done", {}))
        ws.player.character.level = int(sc.get("level", 10))
        mentor.set_stage(ws.player, sc.get("mentor_stage", ""))
        people = []
        for p in sc.get("present", []):
            n = NPC(id=p["id"], name=p.get("name", p["id"]), people="human", role=p.get("role", "merchant"), location=ws.player.location, traits=[], trust=50)
            self.store.save_npc(n)
            people.append(n)
        for pr in sc.get("prisoners", []):                                    # a captive, bound and present
            n = NPC(id=pr["id"], name=pr.get("name", pr["id"]), people="human", role="prisoner", location=ws.player.location, traits=[], trust=30,
                    epithet="the captured outlaw", name_known_to_player=False, protected=True)
            self.store.save_npc(n)
            people.append(n)
        ws.player.prisoners = {pr["id"]: {"deal": False, "arc": "", "node": "", "tip": False, "asked": 0, "day": 0} for pr in sc.get("prisoners", [])}
        ws.residents = ws.present = people
        by_id = {n.id: n for n in people}
        ws.partner = by_id.get(sc.get("partner", ""))
        ws.last_spoken = sc.get("last_spoken") or (ws.partner.id if ws.partner else None)
        ws.convo = []
        ws.player.party = [{"id": f"h{i}", "name": m["name"], "role": m.get("role", "fighter"), "level": 8, "rank": "F", "blurb": "x", "permanent": True,
                            "base_level": 8, "hired_at": 10, "bond": 20, "quirks": {}, "motive": "coin"} for i, m in enumerate(sc.get("party", []))]
        ws._hire_last = (sc["hire_last"], self.store.meta.turn - 1) if sc.get("hire_last") else None
        ws._errand = (ws.player.party[0], {}) if sc.get("errand") and ws.player.party else None
        ws.pending_clarify = {"text": "x", "question": "y"} if sc.get("clarify") else None
        ws.combat = None
        self.dress_things(sc)

    def dress_things(self, sc: dict) -> None:
        """What the character carries, knows and faces: the catalogues the interpreter is shown come from these."""
        from core.models import Ability, KeyItem
        from engine import inventory as inv, items, quests
        ws = self.ws
        c = ws.player.character

        def thing(spec: str):
            if spec.startswith("raw:"):
                return items.make_raw(spec[4:])
            if spec in inv.GOODS:
                return inv.make_good(spec, 1)
            return items.make(spec, "common", 5)
        c.inventory = [thing(x) for x in sc.get("pack", [])]
        c.key_items = [KeyItem(id=k.lower().replace(" ", "_"), name=k, description="x") for k in sc.get("key_items", [])]
        ws.player.stash = [thing(x) for x in sc.get("stash", [])]
        base_ids = {a.id for a in self.base_actives}
        c.actives = [a for a in c.actives if a.id in base_ids]
        c.prepared = [a for a in c.prepared if a in base_ids]
        for ab in sc.get("abilities", []):
            combat_kind = ab.get("context", "combat")
            a = Ability(id=ab["id"], name=ab["name"], description="x", effect=ab.get("effect", "damage"), tier=ab.get("tier", "moderate"),
                        reach=ab.get("reach", "self" if ab.get("effect") in ("healing", "buff") else "ranged"),
                        resource=ab.get("resource", "mana"), context=combat_kind, cost=0, cooldown=0,
                        buff="mend" if ab.get("effect") == "buff" else "")
            c.actives.append(a)
            c.prepared.append(a.id)
        ps = self.store.load_place(ws.player.location)
        ps.ground = []
        for g in sc.get("ground", []):
            inv.leave_on_ground(ps, thing(g), self.store.meta.minutes)
        self.store.save_place(ps)
        ws.wildlife = None
        if sc.get("wildlife"):
            from engine import combat
            cr = self.world.bestiary[sc["wildlife"]]
            ws.wildlife = (cr, [combat.fighter_from_creature(cr, 3, "normal", "e1", cr.name, "near")])
        ws.player.quests = [quests._quest(q.get("kind", "hunt"), q.get("letter", "F"), q["title"], self.store.meta.minutes, place=q.get("place", "greywood"),
                                          creature=q.get("creature", "wolf"), count=q.get("count", 2)) for q in sc.get("quests", [])]
        ws.player.delve = None
        if sc.get("dungeon"):
            ws.ensure_dungeons()
            ds = self.store.load_dungeons()
            d = next((x for x in ds if x["place"] == sc["dungeon"]), None) or (ds[0] if ds else None)   # a place with no dungeon beneath it: any one will do
            if d:
                ws.player.location = d["entrance"]
                if sc.get("delve"):
                    ws.player.delve = {"dungeon": d["id"], "floor": 0, "chamber": 1, "rest": False}
        if sc.get("board") and ws.guild_place_id():
            ws.ensure_board()

    def run(self, case: dict) -> dict:
        import config
        self.dress(case.get("scene", {}))
        self.plan = [dict(p) for p in (case.get("plan") or [{"kind": "look"}])]
        self.ran.clear(); self.moves.clear(); self.talked.clear(); self.hire.clear(); self.notes.clear()
        text = case["text"]
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()):                 # the game's own printing stays off the report
            self.ws.handle(text)
        rows = [json.loads(l) for l in open(config.TURN_LOG_PATH, encoding="utf-8")] if Path(config.TURN_LOG_PATH).exists() else []
        last = rows[-1] if rows and rows[-1].get("text") == text else {}
        first = self.ran[0][1].model_dump(exclude_defaults=True) if self.ran else {}
        return {"handled_by": last.get("handled_by", "nothing"), "kinds": [k for k, _ in self.ran], "first": first,
                "steps": [i.model_dump(exclude_defaults=True) for _, i in self.ran],
                "moves": list(self.moves), "talked": list(self.talked), "hire": [n for n, _ in self.hire],
                "read": (last.get("interpreter") or [{}])[0].get("plan") if last else None}


def judge(got: dict, expect: dict) -> list[str]:
    """What is wrong with the outcome, in words; empty when it is right."""
    bad = []
    if "handled_by" in expect and got["handled_by"] != expect["handled_by"]:
        bad.append(f"handled by {got['handled_by']}, not {expect['handled_by']}")
    if "kinds" in expect and got["kinds"] != list(expect["kinds"]):
        bad.append(f"ran {got['kinds']}, not {list(expect['kinds'])}")
    for k, v in (expect.get("first") or {}).items():
        if str(got["first"].get(k, "")).lower() != str(v).lower():
            bad.append(f"first.{k} = {got['first'].get(k, '')!r}, not {v!r}")
    if "moves" in expect and got["moves"] != list(expect["moves"]):
        bad.append(f"moved to {got['moves']}, not {list(expect['moves'])}")
    for i, want in enumerate(expect.get("steps") or []):
        step = got["steps"][i] if i < len(got["steps"]) else {}
        for k, v in (want or {}).items():
            if str(step.get(k, "")).lower() != str(v).lower():
                bad.append(f"step {i + 1}.{k} = {step.get(k, '')!r}, not {v!r}")
    if "most" in expect and len(got["kinds"]) > int(expect["most"]):
        bad.append(f"{len(got['kinds'])} steps ran; at most {expect['most']} should")
    return bad


def group_of(case: dict) -> str:
    """What a case is about, for the table by kind: the intercept it expects, else the first kind it expects."""
    e = case.get("expect") or {}
    if e.get("handled_by") and e["handled_by"] != "interpret":
        return f"intercept:{e['handled_by']}"
    kinds = e.get("kinds") or []
    return kinds[0] if kinds else ("move" if e.get("moves") else "other")


def evaluate(cases: list[dict], live: bool = False, quiet: bool = False) -> dict:
    bench = Bench(live=live)
    results, wrong = [], []
    taken_wrong = missed = 0
    for case in cases:
        got = bench.run(case)
        bad = judge(got, case.get("expect") or {})
        want = (case.get("expect") or {}).get("handled_by")
        if bad and want:
            if want == "interpret" and got["handled_by"] != "interpret":
                taken_wrong += 1
            elif want != "interpret" and got["handled_by"] == "interpret":
                missed += 1
        results.append((case["name"], got, bad))
        if bad:
            wrong.append(case["name"])
        if not quiet:
            print(("ok   " if not bad else "FAIL ") + f"{case['name']:<36} {got['handled_by']:<16} {got['kinds']}" + ("" if not bad else "  <- " + "; ".join(bad))
                  + (f"  (model read {got['read']})" if live and got.get("read") is not None else ""))
    n = len(cases)
    by_kind: dict[str, list[int]] = {}
    for case, (_, got, bad) in zip(cases, results):
        row = by_kind.setdefault(group_of(case), [0, 0])
        row[1] += 1
        row[0] += not bad
    summary = {"cases": n, "right": n - len(wrong), "wrong": wrong, "intercept_took_wrongly": taken_wrong, "intercept_missed": missed,
               "by_kind": {k: f"{r}/{t}" for k, (r, t) in sorted(by_kind.items())}}
    if not quiet:
        print(f"\n{summary['right']}/{n} right; intercepts took {taken_wrong} line(s) that were not theirs and missed {missed} that were"
              + (" (live: the model's reading counted)" if live else " (offline: the model's reading is the case's own)"))
        print("by kind: " + ", ".join(f"{k} {v}" for k, v in summary["by_kind"].items()))
        if wrong:
            print("wrong: " + ", ".join(wrong))
    return summary


def promote_case(row: dict) -> dict:
    """A case stub from a turn-log row: the scene as the interpreter saw it, the plan the model read; `expect` is for the reader to fill."""
    call = (row.get("interpreter") or [{}])[0]
    roles = call.get("roles") or {}
    present = [{"id": i, "name": lbl, "role": roles.get(i, "merchant")} for i, lbl in (row.get("present") or {}).items()]
    scene = {"place": row.get("place", "trading_square"), "present": present}
    return {"name": "promoted_line", "text": row["text"], "scene": scene, "plan": row.get("raw") or call.get("plan") or [{"kind": "look"}],
            "expect": {"handled_by": row.get("handled_by", "interpret"), "kinds": [s.get("kind") for s in (row.get("final") or [])]}}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--promote", nargs=2, metavar=("LOG", "INDEX"))
    a = ap.parse_args()
    if a.promote:
        lines = [l for l in Path(a.promote[0]).read_text(encoding="utf-8").splitlines() if l.strip()]
        print(yaml.safe_dump([promote_case(json.loads(lines[int(a.promote[1])]))], sort_keys=False, allow_unicode=True))
        sys.exit(0)
    cases = load_cases()
    if a.only:
        frags = [f.strip() for f in a.only.split(",") if f.strip()]
        cases = [c for c in cases if any(f in c["name"] for f in frags)]
    out = evaluate(cases, live=a.live)
    sys.exit(1 if out["wrong"] else 0)
