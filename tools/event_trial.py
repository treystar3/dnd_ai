"""Walk a character through a campaign or a cataclysm, end to end, and write down what they would have met.

The big events (engine/events.py) are the largest things the world does, and until now only the unit tests and a bot that wanders into
them exercised them. This tool forces one for a character of a given level, lets it run a day at a time through the real pulse, acts on
its paths the way play would, and reports what the character saw: the stages, the news that reached their town, the creatures put into
the world, the towns hit and what became of them, the people lost, the ending and the reward.

  python tools/event_trial.py campaign --level 60                     a campaign near Parth, forced now, played to its end
  python tools/event_trial.py campaign --pressure ironvein_deeps       the campaign of one marked pressure
  python tools/event_trial.py cataclysm --kind war --level 100         a war; settled by treaty or by the sword (--path)
  python tools/event_trial.py cataclysm --kind awakening --ignore      nobody acts: watch it run its course
  python tools/event_trial.py campaign --live                          the real model writes it (Ollama)
  python tools/event_trial.py cataclysm --play --days 200              simbot plays the character instead of the ledger
  python tools/event_trial.py --list                                   the marked pressures and the cataclysm kinds

Modes:
  ledger (default)  no bot: time passes a day at a time; when a path can be met the deed is laid in the ledger as play would lay it (the
                    boss falls, the leader is won over, the gate holds), and the real machinery judges it: paths, the judge, finish, the
                    grand reward, the town's memory.
  --play            simbot plays the character from the event's start; its own big-event pursuit goes after the boss or the treaty.

Report: saves/event_trial/<name>.md; a one-line verdict on stdout. The stub stands in for the model unless --live."""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import shutil
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DAY = 1440
PATH_ORDER = ("boss", "horde", "treaty", "persuade", "kill", "clear", "find", "contract")


def install_model(live: bool) -> None:
    if live:
        return
    import simlib
    simlib.install(simlib.Stub("warrior", 3))


class Trial:
    def __init__(self, tier: str, kind: str = "", level: int = 60, cls: str = "warrior", seed: int = 5, live: bool = False,
                 save: str = "event_trial", quiet: bool = True):
        install_model(live)
        import ui.console as uc
        from engine import leveling, events
        from npc.life import populate_place
        from npc.traits import load_traits
        from scenes.world import WorldScene
        from storage.campaign import CampaignStore, PlayerState
        from world.loader import load_world
        import simlib
        self.start_at = time.time()
        self.tier, self.kind, self.level, self.cls, self.seed, self.live = tier, kind, level, cls, seed, live
        self.notes: list[str] = []
        self.narrations: list[str] = []
        self.lines: list[str] = []
        if quiet:
            uc.note = lambda m, *a, **k: self.notes.append(str(m))
            uc.narrate = lambda t, *a, **k: None
            uc.say = lambda *a, **k: None
            uc.wait = lambda *a, **k: None
            uc.ledger = lambda m, *a, **k: self.notes.append(str(m))
        self.world = load_world()
        self.catalog = load_traits()
        shutil.rmtree(ROOT / "saves" / save, ignore_errors=True)
        self.store = CampaignStore.open_or_create(save)
        self.t = 400 * DAY
        self.store.meta.seed = seed
        self.store.meta.minutes = self.t
        self.store.save_meta()
        char, _ = simlib.make_character(cls, random.Random(seed))
        while char.level < level:
            leveling.gain_xp(char, leveling.xp_to_next(char.level))
        self.store.save_player(PlayerState(character=char, location="parth"))
        self.ws = WorldScene(self.store, self.world, self.catalog, self.store.load_player())
        self.ws.player.mentor["never"] = True
        self.ws.narrate = lambda text, *a, **k: self.narrations.append(str(text))
        for pid in [p.id for p in events.settlements(self.world)]:
            try:
                populate_place(self.store, self.world, pid, self.catalog)
            except Exception as e:
                self.lines.append(f"(could not populate {pid}: {e})")
        for p in self.world.places.values():
            if "guild_master" in (p.residents or {}):
                populate_place(self.store, self.world, p.id, self.catalog)
        from engine import pulse
        state = pulse.empty_state(self.t)
        self.store.save_world_state(state)
        self.rng = random.Random(seed + 1)
        self.thread_id = ""
        self.day = 0
        self.coins0 = self.ws.player.character.coins
        self.titles0 = list(self.ws.player.titles)
        self.acted: list[str] = []

    # ---------- the event

    def start(self, pressure: str = "") -> bool:
        from engine import events, pulse
        state = self.store.load_world_state()
        if self.tier == "campaign":
            ok = pulse.start_thread(self.store, self.world, self.catalog, state, self.t, self.rng, tier="campaign", pressure_id=pressure or "")
            th = next((x for x in state["threads"] if x["tier"] == "campaign"), None)
        else:
            weights = {k: v["weight"] for k, v in events.C["kinds"].items()}
            try:
                if self.kind:
                    for k in events.C["kinds"]:
                        events.C["kinds"][k]["weight"] = 1000 if k == self.kind else 0
                ok = events.start_cataclysm(self.store, self.world, self.catalog, state, self.t, self.rng)
            finally:
                for k, w in weights.items():
                    events.C["kinds"][k]["weight"] = w
            th = next((x for x in state["threads"] if x["tier"] == "cataclysm"), None)
        self.store.save_world_state(state)
        if not ok or th is None:
            return False
        self.thread_id = th["id"]
        self.snapshot = self.take()
        return True

    def thread(self) -> dict | None:
        """The event's record; once the world has dropped a finished record from its list, the last one seen."""
        st = self.store.load_world_state() or {}
        th = next((x for x in st.get("threads", []) if x["id"] == self.thread_id), None)
        if th is not None:
            self.last_th = dict(th)
        return th if th is not None else getattr(self, "last_th", None)

    # ---------- a day at a time

    def take(self) -> dict:
        st = self.store.load_world_state() or {}
        th = next((x for x in st.get("threads", []) if x["id"] == self.thread_id), None) or {}
        return {"stage": th.get("stage", 0), "status": th.get("status", ""), "news": len(st.get("news", [])),
                "spawns": {s["id"]: (s["defeated"], s["from"] <= self.t) for s in st.get("spawns", [])},
                "camps": len(st.get("camps", [])), "effects": len(st.get("effects", [])), "fallen": set((st.get("fallen") or {}).keys()),
                "history": len(st.get("history", [])), "gone": sum(1 for r in self.store.npc_rows() if r.gone),
                "paths": {p["id"]: p["done"] for p in th.get("paths", [])}, "ruined": [t for t, h in self.ws.player.homes.items() if h.get("ruined")]}

    def pass_day(self) -> None:
        from engine import events
        self.day += 1
        self.t += DAY
        self.store.meta.minutes = self.t
        self.store.save_meta()
        self.ws.run_pulse()                                         # the real pulse, drift and the player-facing notices
        if self.ws.combat is not None and getattr(self.ws, "assault", None):      # the host at the gate of the town they stand in: the ledger holds it
            a = self.ws.assault
            events.assault_over(self.ws, "victory")
            self.ws.combat = None
            self.store.save_combat(None)
            self.lines.append(f"day {self.day}: the host reaches {self.world.places[a['town']].name} while the character stands there; the gate holds")
        self.diff()

    def diff(self) -> None:
        from engine import pulse
        st = self.store.load_world_state() or {}
        now, was = self.take(), self.snapshot
        th = self.thread() or {}
        town = pulse.town_of(self.world, self.ws.player.location)
        if now["stage"] != was["stage"] and th.get("stages"):
            self.lines.append(f"day {self.day}: stage {now['stage'] + 1}/{len(th['stages'])} - {th['stages'][now['stage']]['description'][:160]}")
        for sid, (dead, live) in now["spawns"].items():
            s = next(x for x in st["spawns"] if x["id"] == sid)
            before = was["spawns"].get(sid)
            if before is None:
                self.lines.append(f"day {self.day}: {'the boss ' if s['boss'] else ''}{s['name']} (level {s.get('level') or '?'}) is put into {self.world.places[s['place']].name}" + ("" if live else f", abroad from day {max(0, (s['from'] - self.t) // DAY + self.day)}"))
            elif live and not before[1]:
                self.lines.append(f"day {self.day}: {s['name']} is abroad in {self.world.places[s['place']].name}")
            if dead and before and not before[0]:
                self.lines.append(f"day {self.day}: {s['name']} is defeated")
        if now["camps"] > was["camps"]:
            self.lines.append(f"day {self.day}: {now['camps'] - was['camps']} camp(s) set up")
        if now["effects"] > was["effects"]:
            kinds = collections.Counter(e["kind"] for e in st.get("effects", [])[was["effects"]:])
            self.lines.append(f"day {self.day}: effects laid - " + ", ".join(f"{k} x{n}" for k, n in kinds.items()))
        for fell in sorted(now["fallen"] - was["fallen"]):
            self.lines.append(f"day {self.day}: {self.world.places[fell].name} FALLS")
        if now["gone"] > was["gone"]:
            self.lines.append(f"day {self.day}: {now['gone'] - was['gone']} people lost (dead, fled or taken)")
        for pid, done in now["paths"].items():
            if done and not was["paths"].get(pid):
                self.lines.append(f"day {self.day}: path met - {pid}")
        for n in st.get("news", [])[was["news"]:]:
            if n["minute"] + pulse.travel_delay(self.world, n["origin"], town) <= self.t:
                self.lines.append(f"day {self.day}: news in {self.world.places[town].name} - {pulse.news_text(n)[:150]}")
        for h in st.get("history", [])[was["history"]:]:
            self.lines.append(f"day {self.day}: history - {h['text'][:150]}")
        for t_ in now["ruined"]:
            if t_ not in was["ruined"]:
                self.lines.append(f"day {self.day}: the character's house in {self.world.places[t_].name} is a ruin")
        if now["status"] != was["status"] and now["status"]:
            self.lines.append(f"day {self.day}: the event is {now['status']} ({th.get('result', '?')}){' - ' + th['ending'] if th.get('ending') else ''}")
        self.snapshot = now

    # ---------- acting: the ledger stands in for play

    def act(self, prefer: str = "") -> bool:
        """Lay one deed toward the event's end, the way play would, and let the real machinery judge it. True when something was done."""
        from engine import deeds, events
        st = self.store.load_world_state() or {}
        th = next((x for x in st.get("threads", []) if x["id"] == self.thread_id), None)
        if not th or th["status"] != "active":
            return False
        paths = [p for p in th.get("paths", []) if not p["done"]]
        if not paths:
            return False

        def rank(p):
            if p["kind"] == "kill" and p.get("spawn"):
                s = next((x for x in st["spawns"] if x["id"] == p["spawn"]), None)
                if not s or s["defeated"] or s["from"] > self.t:
                    return 99
                if any(x not in {y["id"] for y in st["spawns"] if y["defeated"]} for x in s.get("after", [])):
                    return 99
                key = "boss" if s["boss"] else "kill"
            else:
                key = p["kind"]
            order = list(PATH_ORDER)
            if prefer and prefer in order:
                order.remove(prefer); order.insert(0, prefer)
            return order.index(key) if key in order else 98
        paths.sort(key=rank)
        p = paths[0]
        if rank(p) >= 98:
            return False
        who = self.ws.player.character.name
        if p["kind"] == "kill" and p.get("spawn"):
            s = next(x for x in st["spawns"] if x["id"] == p["spawn"])
            self.go(s["place"])
            events.on_kills(self.store, [types.SimpleNamespace(spawn=s["id"])] * s["need"], self.t, self.world)
            deed = deeds.log(self.store, "kill", self.t, place=s["place"], creature=s["creature"], count=s["need"], rank="boss" if s["boss"] else "normal")
            self.acted.append(f"day {self.day}: {who} faces {s['name']} in {self.world.places[s['place']].name} and kills it")
        elif p["kind"] == "horde":
            ids = [i for i in p.get("spawn", "").split(",") if i]
            for sid in ids:
                s = next((x for x in st["spawns"] if x["id"] == sid), None)
                if s and not s["defeated"]:
                    events.on_kills(self.store, [types.SimpleNamespace(spawn=sid)] * s["need"], self.t, self.world)
            deed = deeds.log(self.store, "kill", self.t, place=th["place"], creature="horde", count=len(ids))
            self.acted.append(f"day {self.day}: {who} breaks the horde ({len(ids)} bands)")
        elif p["kind"] in ("persuade", "treaty"):
            ids = [i for i in p["target"].split(",") if i]
            deed = None
            for nid in ids:
                if not self.store.npc_exists(nid):
                    continue
                n = self.store.load_npc(nid)
                self.go(n.location)
                deed = deeds.log(self.store, "persuade", self.t, place=n.location, npc=nid, degree="strong success")
                self.acted.append(f"day {self.day}: {who} wins over {n.name}, the {n.role.replace('_', ' ')}, in {self.world.places[n.location].name}")
            if deed is None:
                return False
        elif p["kind"] == "kill":
            zone = events.nearest_zone(self.world, th["place"], self.level)
            self.go(zone.id)
            deed = deeds.log(self.store, "kill", self.t, place=zone.id, creature=p["target"], count=1)
            self.acted.append(f"day {self.day}: {who} hunts down a {p['target']} in {zone.name}")
        elif p["kind"] == "clear":
            self.go(p["target"])
            deed = deeds.log(self.store, "dungeon_cleared", self.t, place=p["target"])
            self.acted.append(f"day {self.day}: {who} clears {self.world.places[p['target']].name}")
        elif p["kind"] == "find":
            self.go(p["target"])
            deed = deeds.log(self.store, "found", self.t, place=p["target"], thread=th["id"])
            self.acted.append(f"day {self.day}: {who} finds what the matter hid at {self.world.places[p['target']].name}")
        elif p["kind"] == "contract":
            deed = deeds.log(self.store, "quest_done", self.t, place=th["place"], thread=th["id"])
            self.acted.append(f"day {self.day}: {who} finishes the contract the event posted")
        else:
            return False
        events.after_deed(self.ws, deed)
        self.store.save_player(self.ws.player)
        return True

    def go(self, place_id: str) -> None:
        if place_id in self.world.places and self.ws.player.location != place_id:
            self.ws.player.location = place_id
            self.store.save_player(self.ws.player)
            self.acted.append(f"day {self.day}: travels to {self.world.places[place_id].name}")

    # ---------- the whole run

    def run(self, days: int = 150, ignore: bool = False, prefer: str = "", act_from_stage: int = 2) -> dict:
        """A day at a time until the event ends or the days run out. The character acts from `act_from_stage` on (the second stage by
        default, so the event is seen to unfold before anyone moves against it)."""
        from storage import invariants
        for _ in range(days):
            th = self.thread()
            if not th or th["status"] != "active":
                break
            self.pass_day()
            th = self.thread()
            if th and th["status"] == "active" and not ignore and th["stage"] + 1 >= act_from_stage:
                if self.act(prefer):
                    self.diff()
        th = self.thread() or {}
        problems = invariants.validate_campaign(self.store, self.world)
        c = self.ws.player.character
        out = {"tier": self.tier, "kind": th.get("kind", self.kind), "title": th.get("title", ""), "level": self.level, "days": self.day,
               "started": bool(th), "status": th.get("status", ""), "result": th.get("result", ""), "ending": th.get("ending", ""),
               "won_path": (th.get("won_path") or {}).get("name", ""), "paths": [(p["id"], p["done"]) for p in th.get("paths", [])],
               "stages": len(th.get("stages", [])), "stage": th.get("stage", 0) + 1, "reward": [n for n in self.notes if n.startswith("The survivors give")],
               "coins_gained": c.coins - self.coins0, "titles": [t for t in self.ws.player.titles if t not in self.titles0],
               "fallen": sorted((self.store.load_world_state() or {}).get("fallen", {}).keys()),
               "problems": [str(p) for p in problems], "acted": list(self.acted), "lines": list(self.lines), "notes": list(self.notes),
               "seconds": round(time.time() - self.start_at, 1)}
        return out


def report(out: dict, path: Path) -> None:
    th_line = f"{out['tier']} '{out['title']}'" + (f" ({out['kind']})" if out["kind"] else "")
    md = [f"# {th_line} at level {out['level']}", "",
          f"- outcome: **{out['status'] or 'never started'}** ({out['result'] or '-'}){' - ' + out['ending'] if out['ending'] else ''}",
          f"- stages: {out['stage']}/{out['stages']} over {out['days']} days; path met: {out['won_path'] or '-'}",
          "- paths: " + (", ".join(f"{pid}{' (met)' if done else ''}" for pid, done in out["paths"]) or "-"),
          f"- towns fallen: {', '.join(out['fallen']) or 'none'}",
          f"- reward: {'; '.join(out['reward']) or 'none'}; coins gained {out['coins_gained']}; titles {', '.join(out['titles']) or 'none'}",
          f"- invariants: {len(out['problems'])} problem(s)" + (" - " + "; ".join(out["problems"][:5]) if out["problems"] else ""),
          "", "## What the character did", ""] + [f"- {a}" for a in out["acted"]] + ["", "## Day by day", ""] + [f"- {l}" for l in out["lines"]] \
         + ["", "## Notes the game printed", ""] + [f"- {n}" for n in out["notes"][-40:]]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(md) + "\n", encoding="utf-8")


def verdict(out: dict) -> str:
    return (f"{out['tier']} '{out['title']}'{' (' + out['kind'] + ')' if out['kind'] else ''} at level {out['level']}: "
            f"{out['status'] or 'never started'} ({out['result'] or '-'}) after {out['days']} days, stage {out['stage']}/{out['stages']}"
            + (f", by way of '{out['won_path']}'" if out["won_path"] else "") + f"; reward {'yes' if out['reward'] else 'no'}"
            + f"; towns fallen {len(out['fallen'])}; invariants {len(out['problems'])} problem(s); {out['seconds']}s")


def run(tier: str, kind: str = "", level: int = 60, cls: str = "warrior", seed: int = 5, pressure: str = "", days: int = 150, ignore: bool = False,
        prefer: str = "", live: bool = False, save: str = "event_trial", quiet: bool = True, act_from_stage: int = 2) -> dict:
    trial = Trial(tier, kind, level, cls, seed, live, save, quiet)
    if not trial.start(pressure):
        return {"tier": tier, "kind": kind, "title": "", "level": level, "days": 0, "started": False, "status": "", "result": "", "ending": "",
                "won_path": "", "paths": [], "stages": 0, "stage": 0, "reward": [], "coins_gained": 0, "titles": [], "fallen": [], "problems": [],
                "acted": [], "lines": trial.lines, "notes": trial.notes, "seconds": 0}
    return trial.run(days, ignore, prefer, act_from_stage)


def play(tier: str, kind: str, level: int, cls: str, seed: int, pressure: str, days: int, live: bool) -> dict:
    """simbot plays it: the event is forced into the bot's world at its start, and the bot's own pursuit (big_pass) goes after it."""
    os.environ["SIMBOT_SAVE"] = "event_trial_play"
    os.environ["SIM_START_LEVEL"] = str(level)
    sys.argv = ["simbot.py", cls, str(seed), str(days)]
    import simbot
    simbot.TARGET = max(getattr(simbot, "TARGET", 150), level + 100)          # the bot stops at its level target: not before the event is done
    bot = simbot.Bot()
    from engine import events, pulse
    state = bot.store.load_world_state() or pulse.empty_state(bot.ws.minutes)
    if tier == "campaign":
        ok = pulse.start_thread(bot.store, bot.world, bot.ws.catalog, state, bot.ws.minutes, random.Random(seed), tier="campaign", pressure_id=pressure or "")
    else:
        weights = {k: v["weight"] for k, v in events.C["kinds"].items()}
        try:
            if kind:
                for k in events.C["kinds"]:
                    events.C["kinds"][k]["weight"] = 1000 if k == kind else 0
            ok = events.start_cataclysm(bot.store, bot.world, bot.ws.catalog, state, bot.ws.minutes, random.Random(seed))
        finally:
            for k, w in weights.items():
                events.C["kinds"][k]["weight"] = w
    bot.store.save_world_state(state)
    th = next((x for x in state["threads"] if x["tier"] == tier), None)
    bot.run()
    sys.stdout = sys.__stdout__
    st = bot.store.load_world_state() or {}
    th = next((x for x in st.get("threads", []) if th and x["id"] == th["id"]), th)
    from storage import invariants
    problems = invariants.validate_campaign(bot.store, bot.world)
    return {"tier": tier, "kind": (th or {}).get("kind", kind), "title": (th or {}).get("title", ""), "level": bot.c.level, "days": bot.day,
            "started": bool(ok and th), "status": (th or {}).get("status", ""), "result": (th or {}).get("result", ""), "ending": (th or {}).get("ending", ""),
            "won_path": ((th or {}).get("won_path") or {}).get("name", ""), "paths": [(p["id"], p["done"]) for p in (th or {}).get("paths", [])],
            "stages": len((th or {}).get("stages", [])), "stage": (th or {}).get("stage", 0) + 1, "reward": [], "coins_gained": 0,
            "titles": list(bot.ws.player.titles), "fallen": sorted(st.get("fallen", {}).keys()), "problems": [str(p) for p in problems],
            "acted": [json.dumps(b) for b in bot.big_log], "lines": [f"the bot stopped: {bot.aborted}"] + [json.dumps(x) for x in getattr(bot, "exc_log", [])[-5:]],
            "notes": [], "seconds": round(time.time() - bot.t0, 1)}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("tier", nargs="?", choices=["campaign", "cataclysm", "both"], default="campaign")
    ap.add_argument("--kind", default="", help="cataclysm kind: awakening, invasion, war, plague")
    ap.add_argument("--pressure", default="", help="campaign: the marked pressure to force")
    ap.add_argument("--level", type=int, default=0, help="the character's level (default 60 for a campaign, 100 for a cataclysm)")
    ap.add_argument("--cls", default="warrior")
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--days", type=int, default=150)
    ap.add_argument("--path", default="", help="which way to end it first: boss, treaty, persuade, kill, clear, find, contract")
    ap.add_argument("--ignore", action="store_true", help="never act: watch it run its course")
    ap.add_argument("--from-stage", type=int, default=2, help="act from this stage on (default 2: the event is seen to unfold first)")
    ap.add_argument("--play", action="store_true", help="simbot plays the character")
    ap.add_argument("--live", action="store_true", help="the real model (Ollama) instead of the stub")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        from world.loader import load_world
        from engine import events
        w = load_world()
        print("marked pressures (campaigns): " + ", ".join(sorted(p.id for p in w.pressures.values() if getattr(p, "campaign", False))))
        print("cataclysm kinds: " + ", ".join(events.C["kinds"]))
        return 0
    tiers = ["campaign", "cataclysm"] if a.tier == "both" else [a.tier]
    rc = 0
    for tier in tiers:
        level = a.level or (60 if tier == "campaign" else 100)
        if a.play:
            out = play(tier, a.kind, level, a.cls, a.seed, a.pressure, a.days, a.live)
        else:
            out = run(tier, a.kind, level, a.cls, a.seed, a.pressure, a.days, a.ignore, a.path, a.live, act_from_stage=a.from_stage)
        name = f"{tier}_{out['kind'] or 'any'}_{level}" + ("_play" if a.play else "") + ("_ignored" if a.ignore else "")
        path = ROOT / "saves" / "event_trial" / f"{name}.md"
        report(out, path)
        print(verdict(out))
        print(f"  report: {path.relative_to(ROOT)}")
        if not out["started"] or out["problems"]:
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
