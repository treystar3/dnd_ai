"""Plays a campaign or a cataclysm with the real model from its start to its end, and writes down everything the model wrote and
how the chain went: for judging how the model handles the biggest things the world does.

    python tools/eventrun.py campaign [--level 60] [--pressure ID] [--hours 4] [--turns 400] [--days 120]
    python tools/eventrun.py cataclysm [--kind war|awakening|invasion|plague] [--level 100]
    eventrun.bat cataclysm --kind war            (Windows: the same, through the game's own Python environment)

The event is forced at the start, the way tools/event_trial.py forces one, and a bot then plays it the way a player would, typing
lines the real model reads: it goes where the matter is, asks the people who hold its clues, lets the stages turn (time passes in
8-hour steps between lines, so the waiting costs no model calls), hunts the boss where it is abroad, tries to win over the people a
treaty needs, stands in the town a cataclysm is about to reach and fights at its gate, takes the guild's job, and so on until the
event is resolved, ends on its own, or the run's limits are reached.

logs/eventrun/<when>/report.md is the piece to read: the event as the model wrote it (title, stages, paths, clues, truth, the boss's
lines), a timeline of what the engine did and what the bot typed, every judge verdict with its reason, and an outcome checklist.
transcript.md holds every word the model narrated along the way; the rest is as tools/nightrun.py keeps it (turns.jsonl, the call
log, summary.md from tools/latency.py). --stub plays with the stand-in model (the test suite): it shows the chain's mechanics, not
the model's writing.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import shutil
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import nightrun                                      # sets the working directory and the import path
from nightrun import Bot, Run, die, outfit, spend_points

DAY = 24 * 60
STEP = 8 * 60                                        # the pulse's own interval: time passes in these steps between lines
PATH_ORDER = ("boss", "kill", "horde", "fight", "treaty", "persuade", "contract", "clear", "find")


def force_event(store, world, catalog, state, t, rng, tier: str, kind: str, pressure: str) -> dict | None:
    """Begin the event now, as the pulse's big-event slot would. The thread record, or None when the model gave nothing usable."""
    from engine import events, pulse
    if tier == "campaign":
        ok = pulse.start_thread(store, world, catalog, state, t, rng, tier="campaign", pressure_id=pressure or "")
        th = next((x for x in state["threads"] if x["tier"] == "campaign"), None)
    else:
        weights = {k: v["weight"] for k, v in events.C["kinds"].items()}
        try:
            if kind:
                for k in events.C["kinds"]:
                    events.C["kinds"][k]["weight"] = 1000 if k == kind else 0
            ok = events.start_cataclysm(store, world, catalog, state, t, rng)
        finally:
            for k, w in weights.items():
                events.C["kinds"][k]["weight"] = w
        th = next((x for x in state["threads"] if x["tier"] == "cataclysm"), None)
    store.save_world_state(state)
    return th if ok and th else None


class EventBot(Bot):
    """Plays toward the event's end: learns what it can where the matter is, then takes its paths as they open."""

    def __init__(self, ws, world, rng, stub, run, thread_id: str):
        super().__init__(ws, world, rng, stub)
        self.run_, self.thread_id = run, thread_id
        self.timeline: list[str] = []                # what the engine did and what the bot typed, day by day
        self.start_minutes = ws.minutes
        self.searches: collections.Counter = collections.Counter()   # place -> searches there without the quarry
        self.tries: collections.Counter = collections.Counter()      # npc -> persuasion attempts
        self.asked: collections.Counter = collections.Counter()      # npc -> questions asked about the matter
        self.given_up: set[str] = set()              # path ids the bot stopped trying
        self.stuck: collections.Counter = collections.Counter()      # (goal, place) -> lines typed toward it with no change of place
        self.waits = 0                               # 8-hour steps passed without a line
        self.waits_here = 0
        self.avoid_until: dict[str, int] = {}        # spawn id -> the minute a hunt that killed the character twice may resume
        self.deaths_on: collections.Counter = collections.Counter()
        self.deaths_seen = self.c.deaths
        self.learn_left = 3                          # questions to ask where the matter is before going after its paths; more when a stage turns
        self.zones: dict[str, str | None] = {}       # path id -> the zone where its quarry lives, once looked up
        self.snapshot = self.take()

    # ---- the event's state
    def state(self) -> dict:
        return self.ws.store.load_world_state() or {}

    def thread(self) -> dict | None:
        th = next((x for x in self.state().get("threads", []) if x["id"] == self.thread_id), None)
        if th is not None:
            self.last_th = dict(th)
        return th if th is not None else getattr(self, "last_th", None)

    def day(self) -> int:
        return (self.ws.minutes - self.start_minutes) // DAY + 1

    def note(self, text: str) -> None:
        self.timeline.append(f"day {self.day()}: {text}")

    def take(self) -> dict:
        st = self.state()
        th = next((x for x in st.get("threads", []) if x["id"] == self.thread_id), None) or {}
        return {"stage": th.get("stage", 0), "status": th.get("status", ""), "judge": th.get("judge_calls", 0),
                "spawns": {s["id"]: (s["defeated"], s["from"] <= self.ws.minutes) for s in st.get("spawns", []) if s.get("thread") == self.thread_id},
                "paths": {p["id"]: p["done"] for p in th.get("paths", [])}, "clues": [bool(c.get("found")) for c in th.get("clues", [])],
                "moment": th.get("moment", ""), "summons": th.get("summons", ""), "fallen": set((st.get("fallen") or {}).keys()),
                "held": list(th.get("held", [])), "partial": th.get("partial", 0)}

    def watch(self) -> None:
        """Write down what changed in the event since the last look."""
        st = self.state()
        now, was = self.take(), self.snapshot
        th = self.thread() or {}
        names = self.world.places
        if now["stage"] != was["stage"] and th.get("stages"):
            self.learn_left = max(self.learn_left, 2)
            s = th["stages"][now["stage"]]
            self.note(f"STAGE {now['stage'] + 1}/{len(th['stages'])} - {s.get('name', '')}{': ' if s.get('name') else ''}{s.get('description', '')[:220]}")
        for sid, (dead, live) in now["spawns"].items():
            s = next((x for x in st["spawns"] if x["id"] == sid), None)
            if not s:
                continue
            before = was["spawns"].get(sid)
            if before is None:
                self.note(f"{'the boss ' if s.get('boss') else ''}{s['name']} (level {s.get('level', '?')}) is put into {names[s['place']].name}" + ("" if live else ", not abroad yet"))
            elif live and not before[1]:
                self.note(f"{s['name']} is abroad in {names[s['place']].name}")
            if dead and before and not before[0]:
                self.note(f"{s['name']} is DEFEATED")
        for pid, done in now["paths"].items():
            if done and not was["paths"].get(pid):
                self.note(f"PATH MET - {pid}")
        for i, found in enumerate(now["clues"]):
            if found and not (i < len(was["clues"]) and was["clues"][i]):
                self.note(f"CLUE FOUND - \"{th['clues'][i].get('text', '')[:160]}\"")
        if now["judge"] != was["judge"]:
            self.note(f"the judge was asked (call {now['judge']})" + (f"; the event is pushed back (partial {now['partial']})" if now["partial"] != was["partial"] else ""))
        if now["moment"] != was["moment"]:
            self.note(f"moment: {was['moment'] or '-'} -> {now['moment'] or '-'}")
        if now["summons"] != was["summons"]:
            self.note(f"summons: {was['summons'] or '-'} -> {now['summons'] or '-'}")
        for fell in sorted(now["fallen"] - was["fallen"]):
            self.note(f"{names[fell].name} FALLS")
        for held in now["held"][len(was["held"]):]:
            self.note(f"{names[held].name if held in names else held} HOLDS")
        if now["status"] != was["status"] and now["status"]:
            self.note(f"the event is {now['status'].upper()} ({th.get('result', '?')}){' - ' + th['ending'] if th.get('ending') else ''}")
        self.snapshot = now

    # ---- time passing without a line
    def pass_time(self) -> None:
        """Eight hours go by: needs, the pulse, the drift, the event's own clock, and whatever reaches the player where they stand."""
        ws = self.ws
        ws.advance(STEP, wait="rest")
        ws.run_pulse()
        if ws.combat is None:
            from engine import matters
            try:
                matters.on_arrival(ws)
            except Exception as e:
                self.run_.errors.write(f"on_arrival after a wait: {type(e).__name__}: {e}\n{traceback.format_exc()}\n")
        ws.store.save_player(ws.player)
        self.waits += 1
        self.watch()

    # ---- deciding
    def decide(self) -> tuple[str, str]:
        self.watch()
        if self.c.deaths > self.deaths_seen:         # died since the last line: the hunt that did it is left alone for a while
            self.deaths_seen = self.c.deaths
            goal = getattr(self, "current_goal", None)
            if goal and goal[0] == "hunt":
                sid = goal[1]["id"]
                self.deaths_on[sid] += 1
                if self.deaths_on[sid] >= 2:
                    self.avoid_until[sid] = self.ws.minutes + 12 * DAY
                    self.note(f"{goal[1]['name']} has killed the character twice: that hunt rests for twelve days")
        text, kind = super().decide()
        self.note(f"at {self.where()} > {text}")
        return text, kind

    def choose(self) -> tuple[str, dict, str]:
        ws, rng, world = self.ws, self.rng, self.world
        if ws.combat:
            return self.fight_line()
        if getattr(ws, "pending_clarify", None):
            return "I look around.", self.intend("look"), "look"
        th = self.thread()
        if ws.partner is not None:
            goal = getattr(self, "current_goal", None)
            if goal and goal[0] == "persuade" and ws.partner.id == goal[1] and self.tries[goal[1]] < 6:
                return self.persuade_line(ws.partner, goal[2], th)       # keep at it while they are listening
            self.talks += 1
            if self.talks <= 1 and th:
                q = rng.choice([f"What do you know about {th['title']}?", f"What have you heard of {th['title']}?",
                                "Is there anything you can tell me that would help with it?"])
                return f'"{q}"', self.intend("talk", target=ws.partner.id, speech=q), "talk"
            self.talks = 0
            return rng.choice(self.LEAVE), self.intend("leave_conversation"), "leave"
        c = self.c
        if self.hp() < 0.5 or c.fatigue >= 70 or c.hunger >= 70:
            return self.rest_line(world.places[ws.player.location])
        for _ in range(9):                            # up to three days may pass before a line is worth typing
            th = self.thread()
            if not th or th["status"] != "active":
                return "I look around.", self.intend("look"), "look"
            goal = self.goal(th)
            self.current_goal = goal
            if goal[0] == "wait":
                self.pass_time()
                if ws.combat:
                    return self.fight_line()
                continue
            line = self.act_on(goal, th)
            if line is not None:
                return line
            self.pass_time()
            if ws.combat:
                return self.fight_line()
        return "I look around.", self.intend("look"), "look"

    def goal(self, th: dict) -> tuple:
        """What to go after now: a live path first, else where the matter can be learned or met, else waiting."""
        from engine import events, pulse
        st = self.state()
        now = self.ws.minutes
        town = pulse.town_of(self.world, th.get("place") or self.ws.player.location)
        if th["tier"] == "cataclysm":                 # its place is the monster's ground: the word is in the towns it will reach
            towns = [t for stage in (th.get("hits") or []) for t in stage if t in self.world.places]
            town = towns[0] if towns else town
        if self.learn_left > 0:                       # first, and after every stage, a word with the people where the matter is
            if self.ws.player.location != town:
                return ("learn", town)
            if any(self.asked[n.id] < 2 for n in self.ws.present):
                return ("learn", town)
            if self.waits_here < 3:                   # nobody about at this hour: wait a little before giving up on it
                self.waits_here += 1
                return ("wait",)
            self.learn_left = 0
        live = [s for s in events.live_spawns(st, now, th["id"]) if self.avoid_until.get(s["id"], 0) <= now]
        undone = [p for p in th.get("paths", []) if not p["done"] and p["id"] not in self.given_up]
        boss = [s for s in live if s.get("boss")]
        if boss:
            return ("hunt", boss[0])
        if live and any(p["kind"] in ("kill", "horde", "fight") for p in undone):
            return ("hunt", live[0])
        for p in undone:
            if p["kind"] in ("persuade", "treaty"):
                for nid in [i for i in str(p.get("target", "")).split(",") if i]:
                    if self.tries[nid] < 6 and self.ws.store.npc_exists(nid) and not events._won_over(st, th.get("made", 0), nid):
                        return ("persuade", nid, p)
        for p in undone:
            if p["kind"] == "contract" and not any(q.get("thread") == th["id"] for q in self.ws.player.quests):
                hall = next((x for x in self.world.places.values() if x.type == "guild"), None)
                if hall:
                    return ("contract", hall.id, p)
        for p in undone:
            if p["kind"] == "kill" and not p.get("spawn") and self.searches[("species", p["id"])] < 30:
                zone = self.zone_for(p, th)
                if zone:
                    return ("species", zone, p)
                self.given_up.add(p["id"])
                self.note(f"no reachable ground where a {p.get('target', '?')} is found: giving up on {p['id']}")
        for p in undone:
            if p["kind"] == "clear" and p.get("target") in self.world.places and self.searches[("clear", p["id"])] < 40:
                return ("clear", p["target"], p)
        for p in undone:
            if p["kind"] == "find" and p.get("target") in self.world.places and self.searches[("find", p["id"])] < 5:
                return ("find", p["target"], p)
        if th["tier"] == "cataclysm":
            hits = th.get("hits") or []
            stage = th.get("stage", 0)
            fallen = set((st.get("fallen") or {}).keys())
            ahead = [t for i in range(stage + 1, len(hits)) for t in hits[i] if t not in fallen]
            if ahead:
                return ("stand", ahead[0])
        from engine import pulse
        town = pulse.town_of(self.world, th.get("place") or self.ws.player.location)
        return ("learn", town)

    def zone_for(self, p: dict, th: dict) -> str | None:
        """The nearest wild place within the character's reach whose creatures include the path's quarry, looked up once."""
        if p["id"] in self.zones:
            return self.zones[p["id"]]
        from engine import encounters
        world, store = self.world, self.ws.store
        start = th.get("place") if th.get("place") in world.places else self.ws.player.location
        found = None
        wild = [x for x in world.places.values() if x.danger and x.type != "dungeon" and x.danger[0] <= self.c.level + 5]
        wild.sort(key=lambda x: (world.path(start, x.id) or ([], 10 ** 9))[1])
        for x in wild[:12]:
            try:
                roster = encounters.ensure_roster(store, world, x.id)
            except Exception:
                continue
            if p.get("target") in roster:
                found = x.id
                break
        self.zones[p["id"]] = found
        return found

    def act_on(self, goal: tuple, th: dict) -> tuple | None:
        """The line for a goal, or None when the thing to do is wait where we stand."""
        ws, rng, world = self.ws, self.rng, self.world
        loc = ws.player.location
        kind = goal[0]
        if kind == "hunt":
            s = goal[1]
            line = self.travel_line(s["place"], ("hunt", s["id"]))
            if line:
                return line
            key = ("hunt", s["id"])
            self.searches[key] += 1
            if self.searches[key] % 12 == 0:
                return None                            # a day's rest from the search, then back to it
            text = rng.choice([f"I search the area for {s['name']}.", f"I hunt for {s['name']} here.", f"I go looking for {s['name']}."])
            return text, self.intend("search"), "hunt"
        if kind == "persuade":
            nid, p = goal[1], goal[2]
            n = ws.store.load_npc(nid)
            if n.gone:
                self.tries[nid] = 99
                return None
            line = self.travel_line(n.location, ("persuade", nid))
            if line:
                return line
            if nid not in {x.id for x in ws.present}:
                return None                            # not here at this hour: wait
            return self.persuade_line(n, p, th)
        if kind == "contract":
            hall, p = goal[1], goal[2]
            line = self.travel_line(hall, ("contract", hall))
            if line:
                return line
            self.searches[("contract", p["id"])] += 1
            if self.searches[("contract", p["id"])] > 3:
                self.given_up.add(p["id"])
            return f"I take the contract about {th['title']} from the board.", self.intend("accept_quest", target=th["title"]), "contract"
        if kind == "species":
            zone, p = goal[1], goal[2]
            line = self.travel_line(zone, ("species", p["id"]))
            if line:
                return line
            self.searches[("species", p["id"])] += 1
            return f"I search the area for a {p.get('target', 'quarry').replace('_', ' ')}.", self.intend("search"), "hunt"
        if kind == "clear":
            place, p = goal[1], goal[2]
            line = self.travel_line(place, ("clear", p["id"]))
            if line:
                return line
            self.searches[("clear", p["id"])] += 1
            if ws.player.delve:
                return rng.choice(["I press on to the next chamber.", "I go deeper."]), self.intend("delve"), "clear"
            return f"I go down into {world.places[place].name} to clear it.", self.intend("delve"), "clear"
        if kind == "find":
            place, p = goal[1], goal[2]
            line = self.travel_line(place, ("find", p["id"]))
            if line:
                return line
            self.searches[("find", p["id"])] += 1
            return f"I search carefully for what {th['title']} has hidden here.", self.intend("search", seek=th["title"]), "find"
        if kind in ("stand", "learn"):
            town = goal[1]
            line = self.travel_line(town, (kind, town))
            if line:
                return line
            holders = {c.get("npc") for c in th.get("clues", []) if c.get("npc") and not c.get("found")}
            here = [n for n in ws.present if self.asked[n.id] < 2]
            first = [n for n in here if n.id in holders] or here
            if first and (holders & {n.id for n in here} or self.learn_left > 0):
                n = rng.choice(first)
                self.asked[n.id] += 1
                self.learn_left = max(0, self.learn_left - 1)
                self.talks = 0                         # one follow-up question, then leave
                text = rng.choice([f"I ask {n.label()} what they know about {th['title']}.", f"I go over to {n.label()} and ask about {th['title']}."])
                return text, self.intend("talk", target=n.id, speech=f"What do you know about {th['title']}?"), "talk"
            return None                                # nothing more to learn here now: let time pass
        return None

    def persuade_line(self, n, p: dict, th: dict) -> tuple:
        self.tries[n.id] += 1
        ask = "make peace" if p["kind"] == "treaty" else f"help end {th['title']}"
        text = self.rng.choice([f"I try to persuade {n.label()} to {ask}.", f"I do my best to convince {n.label()} to {ask}.",
                                f"I try to talk {n.label()} round: they should {ask}, for everyone's sake."])
        return text, self.intend("talk", target=n.id, speech=text, checks=["persuasion"]), "persuade"

    def travel_line(self, dest: str, key: tuple) -> tuple | None:
        """One hop toward dest, or None when already there. A hop that leads nowhere three times is given up for this goal."""
        ws, world = self.ws, self.world
        loc = ws.player.location
        if loc == dest:
            self.stuck[key] = 0
            return None
        self.stuck[key] += 1
        if self.stuck[key] > 12:
            self.given_up.add(key[1] if isinstance(key[1], str) else "")
            self.note(f"cannot reach {world.places[dest].name}: giving up on {key[0]}")
            self.stuck[key] = 0
            return None
        route = world.path(loc, dest)
        hop = route[0][1] if route and len(route[0]) > 1 else dest
        from engine import pulse
        local = pulse.town_of(world, hop) == pulse.town_of(world, loc) and world.places[hop].danger is None
        text = f"I walk over to {world.places[hop].name}." if local else self.rng.choice([f"I set out for {world.places[hop].name}.", f"I take the road to {world.places[hop].name}."])
        return text, self.intend("move", destination=hop), "move"


def write_report(out: Path, info: dict, th: dict | None, state: dict, bot: EventBot, world) -> str:
    import latency
    calls = latency.load(out / "llm_calls.jsonl")
    rows = latency.load(out / "turns.jsonl")
    th = th or {}
    names = world.places
    lines = [f"# {info['tier']} '{th.get('title', '(never started)')}'" + (f" ({th.get('kind')})" if th.get("kind") else "") + f" at level {info['level']}", ""]
    lines.append(f"**Outcome: {th.get('status', 'never started')}** ({th.get('result') or '-'}){' - ' + th['ending'] if th.get('ending') else ''}; "
                 f"stage {th.get('stage', 0) + 1}/{len(th.get('stages', []))} after {info.get('days', 0)} days and {info.get('turns', 0)} lines; "
                 f"stopped: {info.get('reason', '?')}; model {info.get('model', '?')}" + (" (stand-in)" if info.get("stub") else "") + ".")
    lines.append("")
    proposal = [r for r in calls if r.get("task") in ("pulse_thread", "pulse_cataclysm")]
    if proposal:
        rejected = [r for r in proposal if r.get("error")]
        lines.append(f"The proposal took {len(proposal)} attempt{'s' if len(proposal) != 1 else ''}" + (": " + "; ".join(f"attempt {r.get('attempt', 0) + 1} rejected - {str(r['error'])[:200]}" for r in rejected) if rejected else "") + ".")
        lines.append("")
    lines += ["## The event as the model wrote it", ""]
    if th:
        for key, label in (("news", "News"), ("truth", "Truth"), ("resolution", "Resolution"), ("reveal", "Reveal"), ("antagonist", "Antagonist"), ("keepsake", "Keepsake")):
            if th.get(key):
                lines.append(f"- **{label}:** {th[key]}")
        if th.get("place") in names:
            lines.append(f"- **Place:** {names[th['place']].name}; groups {', '.join(th.get('groups', [])) or '-'}; door {th.get('door', '-')}")
        lines += ["", "**Stages**", ""]
        for i, s in enumerate(th.get("stages", [])):
            eff = collections.Counter(e.get("kind", "?") for e in s.get("effects", []))
            desc = s.get("description", "")
            name = s.get("name", "") if not desc.startswith(s.get("name", "") + ":") else ""
            lines.append(f"{i + 1}. {name}{': ' if name else ''}{desc}" + (f" _(signs: {s['signs']})_" if s.get("signs") else "")
                         + (f" [{', '.join(f'{k} x{n}' for k, n in eff.items())}]" if eff else ""))
        for key, label in (("fallout", "Fallout"), ("triumph", "Triumph")):
            v = th.get(key)
            if isinstance(v, dict):
                v = v.get("description", "")
            if v:
                lines += ["", f"**{label}:** {v}"]
        lines += ["", "**Paths**", ""]
        for p in th.get("paths", []):
            lines.append(f"- {'[met] ' if p.get('done') else ''}**{p.get('name', p.get('id'))}** ({p.get('kind')}): {p.get('how', '')}")
        if th.get("clues"):
            lines += ["", "**Clues**", ""]
            for c_ in th["clues"]:
                holder = c_.get("npc", "") or c_.get("holder", "")
                lines.append(f"- {'[found] ' if c_.get('found') else ''}\"{c_.get('text', '')}\" - held by {holder or '?'}")
        bl = th.get("boss_lines") or {}
        if bl:
            lines += ["", "**The boss's lines**", ""] + [f"- {k}: {v}" for k, v in bl.items() if v]
        for side in th.get("side_lines", []) or []:
            lines += ["", "**A side's lines**", ""] + [f"- {k}: {v}" for k, v in side.items() if v]
    lines += ["", "## Timeline", ""] + [f"- {l}" for l in bot.timeline]
    judge = [r for r in calls if r.get("task") == "event_judge"]
    lines += ["", "## The judge", ""]
    if not judge:
        lines.append("Never asked.")
    for r in judge:
        try:
            v = json.loads(r.get("raw") or "{}")
        except ValueError:
            v = {}
        lines.append(f"- {r.get('time', '')[11:19]} attempt {r.get('attempt', 0) + 1}: verdict **{v.get('verdict', '?')}** ({v.get('ending', '-')}) - {v.get('reason', '')}"
                     + (f" _(rejected: {str(r['error'])[:160]})_" if r.get("error") else ""))
    by_task = collections.Counter(r.get("task") for r in calls if r.get("attempt", 0) == 0)
    retries = sum(1 for r in calls if r.get("attempt", 0) > 0)
    spawns = [s for s in state.get("spawns", []) if s.get("thread") == th.get("id")]
    boss = [s for s in spawns if s.get("boss")]
    lines += ["", "## Outcome checklist", "", "| What | Result |", "| --- | --- |",
              f"| Started | {'yes' if th else 'no'} ({len(proposal)} attempt{'s' if len(proposal) != 1 else ''}) |",
              f"| Door | {th.get('door', '-')}; moment {th.get('moment') or '-'}; summons {th.get('summons') or '-'}; opened {th.get('opened', '-')}; answered {th.get('answered', '-')} |",
              f"| Paths | {len(th.get('paths', []))} built, {sum(1 for p in th.get('paths', []) if p.get('done'))} met; won by {(th.get('won_path') or {}).get('name', '-')} |",
              f"| Clues | {len(th.get('clues', []))} written, {sum(1 for c_ in th.get('clues', []) if c_.get('npc'))} bound to a person, {sum(1 for c_ in th.get('clues', []) if c_.get('found'))} found in speech |",
              f"| Boss | {('appeared, ' + ('killed' if boss[0].get('kills', 0) >= boss[0].get('need', 1) else 'stood down at the end' if boss[0].get('defeated') else 'not killed')) if boss else 'none'}; other spawns {len(spawns) - len(boss)} |",
              f"| Towns | fallen {', '.join(names[t].name for t in (state.get('fallen') or {}) if t in names) or 'none'}; held {len(th.get('held', []))} |",
              f"| Judge | asked {th.get('judge_calls', 0)} time(s); pushed back {th.get('partial', 0)} |",
              f"| Ending | {th.get('status', '-')} / {th.get('result') or '-'} / {th.get('ending') or '-'} |",
              f"| Play | {info.get('turns', 0)} lines, {bot.waits} eight-hour waits, {info.get('days', 0)} days; deaths {info.get('deaths', 0)} |",
              f"| Model | {sum(by_task.values())} calls, {retries} retries; " + ", ".join(f"{t} {n}" for t, n in by_task.most_common(8)) + " |"]
    lines += ["", f"Every word the model narrated is in transcript.md; the calls and turns are summarised in summary.md.", ""]
    text = "\n".join(lines)
    (out / "report.md").write_text(text, encoding="utf-8")
    return text


def main() -> None:
    ap = argparse.ArgumentParser(description="Play a campaign or a cataclysm with the real model, start to end, and report what the model wrote.")
    ap.add_argument("tier", nargs="?", choices=["campaign", "cataclysm"], default="campaign")
    ap.add_argument("--kind", default="", help="cataclysm kind: awakening, invasion, war, plague (default: the world's roll)")
    ap.add_argument("--pressure", default="", help="campaign: the marked pressure to force (tools/event_trial.py --list names them)")
    ap.add_argument("--level", type=int, default=0, help="the character's level (default 60 for a campaign, 100 for a cataclysm)")
    ap.add_argument("--class", dest="cls", default="warrior")
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--hours", type=float, default=4.0, help="stop after this many real hours (default 4)")
    ap.add_argument("--turns", type=int, default=400, help="stop after this many typed lines (default 400)")
    ap.add_argument("--days", type=int, default=160, help="stop after this many in-game days (default 160)")
    ap.add_argument("--out", default="", help="where the logs go (default logs/eventrun/<when>)")
    ap.add_argument("--save", default="", help="the save folder's name (default eventrun_<when>; never listed on the home page)")
    ap.add_argument("--stub", action="store_true", help="the stand-in model (the test suite): the mechanics, not the writing")
    args = ap.parse_args()
    level = args.level or (60 if args.tier == "campaign" else 100)

    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    out = Path(args.out or f"logs/eventrun/{stamp}")
    out.mkdir(parents=True, exist_ok=True)
    save = args.save or f"eventrun_{stamp}"

    import config
    config.LOG_PATH = str(out / "llm_calls.jsonl")
    config.TURN_LOG_PATH = str(out / "turns_game.jsonl")
    config.SESSION_STATS_PATH = str(out / "sessions.jsonl")
    config.REFUSALS_LOG_PATH = str(out / "refusals.jsonl")
    config.LOG_MAX_MB = 10 ** 6

    import simlib
    if args.cls not in simlib.CLASSES:
        die(f"--class must be one of: {', '.join(simlib.CLASSES)}")
    stub = None
    if args.stub:
        stub = simlib.Stub(args.cls, args.seed)
        stub.verdict = "no"
        simlib.install(stub)
    else:
        from llm import setup_check
        if not setup_check.server_up():
            die("Ollama is not running. Start the Ollama app, wait a few seconds, and run this again.")
        if not setup_check.model_present():
            die(f"The model {config.MODEL} is not downloaded: run  ollama pull {config.MODEL}  first.")
        from llm import embed
        embed.pull_in_background()
        from llm.gateway import warm
        warm()

    from engine import data_check, leveling, pulse
    problems = data_check.check()
    if problems:
        die("The game's data has problems:\n" + "\n".join(f"  - {p}" for p in problems))
    from world.loader import load_world
    from npc.traits import load_traits
    from npc import backfill
    from storage.campaign import CampaignStore, PlayerState
    from scenes.world import WorldScene
    from engine import turnlog

    world = load_world()
    catalog = load_traits()
    rng = random.Random(args.seed)
    shutil.rmtree(f"saves/{save}", ignore_errors=True)
    store = CampaignStore.open_or_create(save)
    store.meta.seed, store.meta.turn, store.meta.minutes = args.seed, 1, 400 * DAY + 8 * 60
    store.save_meta()
    char, spec = simlib.make_character(args.cls, rng, perks=True)
    if level > 1:
        leveling.level_up(char, level - 1)
        spend_points(char, spec)
        outfit(char, spec, level, rng)
    store.save_player(PlayerState(character=char, location="parth"))
    ws = WorldScene(store, world, catalog, store.load_player())
    ws.player.mentor["never"] = True

    run = Run(out, args.hours, args.turns, live=not args.stub)
    run.install_console()
    run.install_client()
    print(f"Event run: a {args.tier}" + (f" ({args.kind})" if args.kind else "") + f" for {char.name}, {spec['name']}, level {char.level}, seed {args.seed}; "
          f"logs in {out}; stops when the event ends, after {args.days} days, {args.turns} lines or {args.hours:g} h. Ctrl+C stops it early.", flush=True)

    # a character of this level is known in the towns: the doors that need a name (a summons, someone coming to find them) can open
    from engine import events as _events
    for p in _events.settlements(world):
        ws.reputation_add(p.id, 15)
    store.save_player(ws.player)

    # the event, forced now, as the big-event slot would start it; the model may give nothing usable, so up to three tries
    ws.enter(ws.player.location)
    th = None
    for n in range(3):
        state = store.load_world_state() or pulse.empty_state(ws.minutes)
        th = force_event(store, world, catalog, state, ws.minutes, random.Random(args.seed + 11 * n), args.tier, args.kind, args.pressure)
        if th:
            break
        print(f"the {args.tier} did not start (try {n + 1} of 3)", flush=True)
    if not th:
        run.finish({"tier": args.tier, "kind": args.kind, "level": level, "started": False, "days": 0, "deaths": char.deaths, "model": config.MODEL,
                    "stub": args.stub, "seed": args.seed, "save": save})
        write_report(out, json.loads((out / "run.json").read_text(encoding="utf-8")), None, store.load_world_state() or {}, EventBot(ws, world, rng, stub, run, ""), world)
        store.close()
        die(f"The {args.tier} never started: see {out / 'llm_calls.jsonl'} for what the model answered.")
    print(f"{args.tier} begun: '{th['title']}'" + (f" ({th.get('kind')})" if th.get("kind") else "") + f" at {world.places[th['place']].name if th.get('place') in world.places else '?'}, "
          f"{len(th.get('stages', []))} stages, {len(th.get('paths', []))} paths, {len(th.get('clues', []))} clues", flush=True)

    bot = EventBot(ws, world, random.Random(args.seed * 7 + 1), stub, run, th["id"])
    bot.note(f"begun: '{th['title']}' at {world.places[th['place']].name if th.get('place') in world.places else '?'}; paths " + ", ".join(p["id"] for p in th.get("paths", [])))
    run.bot = bot
    if stub is not None:
        stub.bot = bot

    def finished() -> str:
        t = bot.thread()
        if t and t["status"] != "active":
            return f"the event is {t['status']}"
        if bot.day() > args.days:
            return f"day limit ({args.days})"
        return ""
    run.stop_when = finished

    restarts = 0
    try:
        while True:
            try:
                ws.run()
                break
            except KeyboardInterrupt:
                run.reason = "stopped by hand"
                break
            except Exception as e:
                restarts += 1
                run.errors.write(f"--- line {len(run.rows) + 1}: {type(e).__name__}: {e}\n{traceback.format_exc()}\n")
                run.errors.flush()
                print(f"error: {type(e).__name__}: {str(e)[:100]} (restart {restarts})", flush=True)
                if run.current is not None:
                    run.current["error"] = f"{type(e).__name__}: {str(e)[:200]}"
                    run.close_turn()
                if restarts >= 20:
                    run.reason = "too many errors (20)"
                    break
                ws.combat = None
                try:
                    ws.reload_after_rollback()
                except Exception:
                    pass
    finally:
        bot.watch()
        final_th, final_state = bot.thread(), bot.state()
        try:
            store.save_player(ws.player)
        except Exception:
            pass
        store.close()
        backfill.drop(store)
        turnlog.write_session_stats()
        run.finish({"tier": args.tier, "kind": (final_th or {}).get("kind", args.kind), "title": (final_th or {}).get("title", ""), "level": level,
                    "started": True, "status": (final_th or {}).get("status", ""), "result": (final_th or {}).get("result", ""),
                    "ending": (final_th or {}).get("ending", ""), "days": bot.day(), "deaths": ws.player.character.deaths, "character": char.name,
                    "class": spec["name"], "seed": args.seed, "save": save, "restarts": restarts, "stub": args.stub, "model": config.MODEL})
        if not args.stub:
            from llm.gateway import unload
            unload()
    import latency
    latency.summarise(out)
    info = json.loads((out / "run.json").read_text(encoding="utf-8"))
    report = write_report(out, info, final_th, final_state, bot, world)
    print()
    print("\n".join(report.splitlines()[:4]))
    print(f"\nReport: {(out / 'report.md').resolve()}")


if __name__ == "__main__":
    main()
