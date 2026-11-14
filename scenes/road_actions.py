"""Road events: the journey is walked in legs, and some legs bring something the model invents.
(f427, the owner's review Q2) Whatever the player could act on stops the walk there: a fight, a person met, someone in need, a hazard
in the way, a find. A passing sight is told inside the walk, which goes on. Nothing at a stop is settled for the player: a find lies
there until they pick it up, a hazard waits for how they mean to get past it, and someone in need is helped only if the player helps
(walking past is seen by the party, who say what they think of it). After a won fight the walk carries on by itself."""


import re

from engine import checks, clock, encounters, inventory as inv, loot, money, pools, pulse, roads, weather
from engine import effects, worldstate
from engine.road_prompts import SYSTEM, user
from engine.roads import R
from llm.contracts import ActionIntent, RoadEvent
from llm.gateway import LLMError, generate
from ui import console
from world.loader import Place

RARITY = ["crude", "common", "uncommon", "rare", "epic", "legendary"]

# (f427) What the road writer is told of a happening that stops the walk: the scene ends before the player does anything.
STOP_MUST = {
    "hazard": ". The scene shows what is in the way and ends before anyone tries to get past it: how is the player's to decide",
    "aid": ". Someone here needs help (meets_role is who they are): the scene shows them and what they need, and ends before the player "
           "does or says anything: whether to help is the player's",
    "meeting": ". Someone is here (meets_role is who they are): the scene shows them, and ends before the player answers",
}


class RoadActions:

    # ---------- the stop on the road ----------

    def ensure_road_place(self) -> None:
        road = self.player.road
        if road and road["id"] not in self.world.places:
            self.world.add_place(Place(**road["place"]))             # (f451) through the campaign's world

    def leave_road(self, new_place: str) -> None:
        """Called when the player stands anywhere but the stop: tidy it away."""
        road = self.player.road
        if not road or new_place == road["id"]:
            return
        for nid in self.store.load_place(road["id"]).residents:
            npc = self.store.load_npc(nid)
            if not npc.gone:
                pulse.remove_npc(self.store, self.world, npc, "moved on along the road", self.minutes, dead=False)
        self.player.road = None
        self.world.remove_place(road["id"])                         # (f451) the only place ever taken off the map, with its ways
        self.end_conversation()
        self.last_spoken = None
        self.present = []

    # ---------- walking ----------

    def run_journey(self, route: list[str], walk: int, text: str, events: int = 0, barrier: tuple | None = None) -> None:
        """`barrier` (f541): (stretch index, road id, why) of a road a situation has shut, met on this walk for the first time: the walk
        goes as far as the barrier and stops there, and nothing on the road happens on the shut stretch itself."""
        stretches = roads.edges(self.world, route, walk)
        upto = self.barrier_minutes(stretches, barrier) if barrier else walk
        legs = roads.plan_legs(upto)
        quiet = getattr(self, "journey_event_factor", 1.0)        # Swift Step thins out the troubles on this trip
        self.journey_event_factor = 1.0
        log = list((self.player.road or {}).get("log", []))
        done = 0
        for k, leg in enumerate(legs):
            self.advance(leg, exert=True)
            done += leg
            if k == len(legs) - 1 or events >= R["max_per_trip"]:
                continue
            i, frac = roads.position(stretches, done)
            a, b, m = stretches[i]
            if barrier and i >= barrier[0]:
                continue                                          # (f541) the shut stretch is the barrier's
            if m < R["min_edge_minutes"] or self.rng.random() >= R["chance_per_leg"] * quiet:
                continue
            outcome = self.road_event(route, a, b, m, frac, text, log, walked=done)
            if outcome:
                events += 1
            if outcome in ("stopped", "fight"):
                return
        if barrier:
            self.meet_barrier(route, stretches, barrier, text, log, upto)
            return
        self.finish_journey(route, walk, text, log)

    # ---------- (f541) a road a situation has shut, met at the barrier (the owner, 2026-11-07) ----------

    def here_stop(self) -> dict | None:
        """The stop on the road the player stands at, or None."""
        road = self.player.road
        return road if road and self.player.location == road.get("id") else None

    def shut_roads(self) -> dict[str, str]:
        """The named roads shut to the player now, by id, with why (a closure the player made themselves is theirs to undo)."""
        state = self.store.load_world_state() or {}
        out = {}
        for e in state.get("effects", []):
            if e["kind"] == "closed" and e["until"] > self.minutes and e["place"] in self.world.roads and e.get("cause") != "improvised":
                out.setdefault(e["place"], e.get("text") or "")
        return out

    def near_end(self, stop: dict) -> str:
        """(f541's review) The end of a shut road on the player's side of its barrier, for a stop they stand at on it ('' off one)."""
        if stop.get("barrier"):
            return stop.get("behind") or ""
        key = next((k for k in self.shut_roads() if roads.on_road(self.world, stop["id"], k)), "")
        if not key:
            return ""
        far = roads.far_side(self.world, stop["id"], key, R["barrier"]["at"], stop.get("from", ""))
        return next((e for e in self.world.places[stop["id"]].connects if e != far), "")

    def shut_stretch(self, x: str, y: str, shut: dict[str, str]) -> str:
        """The road a stretch from x to y runs on, when it is shut to the player now; '' when open. The barrier is one fixed point on
        the road (roads.far_side): from a stop on the road, the end on the player's side of it is open and the end across it is not,
        whatever made the stop (the barrier itself, a happening on the walk back, a fight)."""
        key = roads.way_key(self.world, x, y)
        if key not in shut:
            return ""
        stop = self.here_stop()
        if stop and x == stop["id"]:
            if stop.get("barrier") == key:
                return "" if y == stop.get("behind") else key
            if roads.on_road(self.world, x, key):
                return key if y == roads.far_side(self.world, x, key, R["barrier"]["at"], stop.get("from", "")) else ""
        return key

    def shut_on(self, route: list[str]) -> tuple[int, str, str] | None:
        """The first stretch of a route over a road shut to the player: (its index, the road's id, why), or None."""
        shut = self.shut_roads()
        if not shut:
            return None
        for i, (x, y) in enumerate(zip(route, route[1:])):
            key = self.shut_stretch(x, y, shut)
            if key:
                return i, key, shut[key]
        return None

    def route_round(self, start: str, dest: str) -> tuple[list[str], int] | None:
        """The quickest walk from start to dest that sets foot on no road shut to the player now, or None when there is none."""
        import heapq
        shut = self.shut_roads()
        best, came, queue = {start: 0}, {start: None}, [(0, start)]
        while queue:
            cost, here = heapq.heappop(queue)
            if here == dest:
                route = []
                while here is not None:
                    route.append(here)
                    here = came[here]
                return route[::-1], cost
            if cost > best[here]:
                continue
            for nxt in self.world.neighbors(here):
                if self.shut_stretch(here, nxt, shut):
                    continue
                c = cost + self.world.travel_minutes(here, nxt)
                if c < best.get(nxt, float("inf")):
                    best[nxt], came[nxt] = c, here
                    heapq.heappush(queue, (c, nxt))
        return None

    def barrier_minutes(self, stretches: list[tuple[str, str, int]], barrier: tuple) -> int:
        """How long the walk to the barrier takes: the stretches before the shut one, and the part of it walked before the barrier."""
        i, key = barrier[0], barrier[1]
        a, b, m = stretches[i]
        return max(1, sum(m_ for _, _, m_ in stretches[:i]) + max(1, round(roads.barrier_frac(self.world, a, b, key, R["barrier"]["at"]) * m)))

    def met_closure(self, key: str) -> bool:
        """Has the acting character met this closure at its barrier (so their walks go round it, or are refused before setting out)?"""
        state = self.store.load_world_state() or {}
        return any(e["kind"] == "closed" and e["place"] == key and e["until"] > self.minutes and self.acting in (e.get("met_by") or [])
                   for e in state.get("effects", []))

    def meet_closure(self, key: str) -> None:
        state = self.store.load_world_state() or {}
        for e in state.get("effects", []):
            if e["kind"] == "closed" and e["place"] == key and e["until"] > self.minutes and self.acting not in (e.get("met_by") or []):
                e["met_by"] = list(e.get("met_by") or []) + [self.acting]
        self.store.save_world_state(state)

    def meet_barrier(self, route: list[str], stretches: list, barrier: tuple, text: str, log: list[str], walked: int) -> None:
        """The walk comes to where a situation has shut the road: a stop on the road at the barrier, told; the way back open, the way
        on shut until the situation lifts it (no pushing through, as a hazard may be got past), the long way round named when there is
        one."""
        i, key, why = barrier
        a, b, m = stretches[i]
        r = self.world.roads[key]
        B = R["barrier"]
        name = r.name[:1].upper() + r.name[1:]
        stop = roads.make_stop(self.world, a, b, roads.barrier_frac(self.world, a, b, key, B["at"]), m, why, "", f"{name} shut", why)
        ends = list(stop["place"]["connects"])
        stop.update(log=log[-6:], text=text, resume="", bound=route[-1], kind="barrier", tier="normal", barrier=key, behind=ends[0])
        if (self.player.road or {}).get("id") not in stop["place"]["connects"]:
            self.leave_road(stop["id"])                     # the stop they set out from is tidied away, as a road event's is
        self.player.road = stop
        self.ensure_road_place()
        self.enter(stop["id"])
        self.meet_closure(key)
        back, onward = self.world.places[ends[0]].name, self.world.places[ends[-1]].name
        happened = (f" On the way (the player has read this already: do not tell it again): {' '.join(log[-4:])}") if log else ""
        self.narrate(f"After {clock.describe_duration(walked)} on foot, the player comes to where {r.name} is shut: {why.rstrip('.')}."
                     f"{happened} Tell the road, then what bars the way, as it is seen. The way on cannot be passed here while it is "
                     "shut. The scene ends before the player does anything: whether to turn back or go round is theirs.", text)
        around = self.route_round(stop["id"], route[-1])
        dest = self.world.places[route[-1]].name
        rnd = B["round"].format(dest=dest, time=clock.walk_words(around[1])) if around else B["none"].format(dest=dest)
        console.note(B["meet"].format(onward=onward, back=back, round=rnd))
        self.show_exits()
        self.store.save_player(self.player)

    def finish_journey(self, route: list[str], walk: int, text: str, log: list[str]) -> None:
        dest = route[-1]
        self.enter(dest)
        via = [self.world.places[p].name for p in route[1:-1] if p in self.world.places]
        passing = f" They pass through {', '.join(via)} on the way." if via else ""
        named = [r for r in (self.world.road_between(a, b) for a, b in zip(route, route[1:])) if r]
        if named:
            state = self.store.load_world_state() or {}
            marks = [f"On {r.name}: {'; '.join(pulse.road_marks(state, r.id)[-2:])}." for r in named[:2] if pulse.road_marks(state, r.id)]
            passing = f" They travel by {', then '.join(r.name for r in named)}: " + \
                " ".join(r.description for r in named[:2]) + (" " + " ".join(marks) if marks else "") + (passing or "")   # (f540)
        happened = (f" On the way (the player has read this already, back where it happened on the road: do not tell it again or put it "
                    f"here): {' '.join(log[-4:])}") if log else ""      # (f406) a dropped ledger on the road was told again, lying at the hollow
        if walk < 45 and self.quiet_return(log, text):                     # (f349) back somewhere seen, nothing new: a line, and no narrator;
                                                                            # (f413) never after a long walk, which is always told (f408)
            self.weight_hint = None
            line = f"You are back at {self.place.name}." if walk < 15 else f"After {clock.walk_words(walk)}, you are back at {self.place.name}."
            self.flush(text)                                                # anything held back from earlier actions goes first, in order
            console.narrate(line)
            self.remember_narration(line)
        else:
            road = ("Tell the walk itself first (the road, the country it crosses, the light changing over the hours, anyone walking with "
                    "them), so the player feels the journey; then the arrival. " if walk >= 45
                    else "Say little of the road. ")               # (f408) a long walk is felt, a short one is not; (f413) a walk with a
                                                                    # happening on it too (only the happening is not told again), and no length
            self.narrate(f"After {clock.describe_duration(walk)} on foot, the player arrives at {self.place.name}.{passing}{happened} "
                         f"{road}Give the place and one person doing one thing; the rest waits until they look.{self.brevity()}", text)
        self.show_exits()
        if self.arc_arrival():
            return
        if self.has("tracker") is not None and self.place.danger:
            roster = encounters.ensure_roster(self.store, self.world, self.player.location)
            if roster:
                names = ", ".join(self.world.bestiary[r].name.lower() for r in roster)
                console.note(f"You read the signs: tracks, spoor and markings of {names}.")
        self.maybe_encounter(encounters.E["chance_on_arrival"], "As you arrive,")

    # ---------- one event ----------

    def road_company(self) -> list[str]:
        """(f408) Who walks the road with the player, as they must be written."""
        from engine import entities
        try:
            return entities.who_is_who(self)
        except Exception:
            return []

    def bandit_road(self, a: str, b: str) -> bool:
        """Is something about outlaws acting on this road right now - a world event the pulse or a road event made?"""
        state = self.store.load_world_state() or {}
        key = roads.edge_key(self.world, a, b)
        words = R["bandits"]["words"]
        rid = next((r.id for r in self.world.roads.values() if roads.edge_key(self.world, r.from_, r.to) == key), None)
        for e in state.get("effects", []):
            if e.get("kind") == "danger" and e.get("until", 0) > self.minutes and e.get("value", 0) > 0 \
                    and e.get("place") in (key, rid, a, b) and any(w in str(e.get("cause", "")).lower() for w in words):
                return True
        return False

    def road_danger(self, a: str, b: str) -> float:
        key = roads.edge_key(self.world, a, b)
        f = pulse.danger_factor(self.store, key, self.minutes)
        ends = [pulse.danger_factor(self.store, pulse.town_of(self.world, p), self.minutes) for p in (a, b)]
        return f * (sum(ends) / 2) * self.danger_multiplier(b, True)

    def journey_facts(self, route, a, b, walked: int) -> str:
        """(f408) Where the player set out from, where they are bound, the road they are on and how long they have walked."""
        r = self.world.road_between(a, b) or self.world.roads.get(roads.way_key(self.world, a, b))   # (f540's review) from a stop too
        way = r.name if r else f"the way toward {self.world.places[b].name}"
        marks = pulse.road_marks(self.store.load_world_state() or {}, r.id) if r else []      # (f540) what the road carries now
        return (f"set out from {self.world.places[route[0]].name}, bound for {self.world.places[route[-1]].name}; now on {way}, "
                f"{clock.describe_duration(max(5, walked))} into the walk" + (f"; on this road: {'; '.join(marks[-3:])}" if marks else ""))

    def journey_line(self, route, a, b, walked: int) -> str:
        """(f408) The walk before a happening, when the model gave none: where from, where to, by what road, how long."""
        r = self.world.road_between(a, b)
        by = f" by {r.name}" if r else ""                 # (f411) no named road: no "by the way toward Elmshade, bound for Elmshade"
        return (f"You set out from {self.world.places[route[0]].name}{by}, bound for {self.world.places[route[-1]].name}. "
                f"You have been walking {clock.describe_duration(max(5, walked))}.")

    def road_event(self, route, a, b, minutes, frac, text, log, resume: str | None = None, stop_name: str = "", walked: int = 0):
        """`resume` is where a won fight carries on to (default: the end of the route); `stop_name` names a stop on the road."""
        tier = roads.roll_tier(self.rng)
        wilds = roads.nearby_wilds(self.world, a, b)
        hostile = bool(wilds) and self.rng.random() < min(R["hostile_max"], R["hostile"] * self.road_danger(a, b))
        hit = None
        deterred = camp = False
        BR = R["bandits"]
        from engine import matters
        matter = matters.road_matter(self, a, b, self.rng)                # (f317) the road's happening may be part of a matter nearby
        if hostile:
            wild = self.rng.choice(wilds)
            themed = self.bandit_road(a, b)
            force = "bandit" if self.rng.random() < (BR["themed"] if themed else BR["base"]) else ""
            if matter and matter[2]:
                force = matter[2]                                          # the matter's own creature comes at them
            hit = encounters.roll(self.store, self.world, wild, 1.0, self.rng, force=force)
            high = self.world.places[wild].danger[1]
            if hit and self.deterred(hit[0], high):
                deterred, hostile, hit = True, False, None
            elif not hit or self.temperament(hit[0], high) == "passive":
                hostile, hit = False, None
            elif hit[0].id == "bandit" and tier == "rare" and self.rng.random() < BR["camp_chance"]:
                camp = True
                hit[1].append(encounters.add_member(self.world, wild, "bandit_captain", self.rng, "elite",
                                                    f"e{len(hit[1]) + 1}", "bandit captain"))
        state = self.store.load_world_state()
        near = a if frac < 0.5 else b
        threads = [f"{t['title']} ({self.where_name(t['place']) if t.get('place') in self.world.places else t.get('place', '')})"   # (f423) a name,
                   for t in state.get("threads", []) if t["status"] == "active"][-8:]                                                       # not an id
        group = self.world.locals_group(near)
        lore = " ".join(f.text for f in self.world.lore.values() if group in f.known_by)[:600]
        rkeys = {roads.edge_key(self.world, x.from_, x.to): f"{x.id} ({x.name})" for x in self.world.roads.values()}
        if hostile:
            names = ", ".join(sorted({e.name for e in hit[1]}))
            must = f"an ambush by {len(hit[1])} x {hit[0].name.lower()} ({names})"
            if camp:
                must = (f"an ambush at an outlaw camp by the roadside: {len(hit[1])} fighters ({names}) with a captain, "
                        "defending a camp full of stolen goods")
        elif deterred:
            must = ("outlaws watching from cover: the player looks far too dangerous, so they hold back and let them pass. "
                    "Not a fight; kind sight. Describe the unseen watchers and the tension, as the player senses it")
        else:
            must = "a happening that is not a fight"
        prize, kind = None, ("ambush" if hostile else "sight" if deterred else "")
        if not hostile and not deterred:                     # (f411) the engine picks the kind, so they vary
            kinds = R.get("kinds") or {"find": 1, "meeting": 1, "sight": 1, "hazard": 1, "aid": 1}
            kind = self.rng.choices(list(kinds), weights=list(kinds.values()))[0]
            must += f". KIND: {kind}"
            if kind == "find":                               # (f406) what a find gives is rolled first, and the scene shows that thing
                prize = self.road_prize(tier, a, b)          # (f427) lying there: whether to take it is the player's
                must += (f". What lies here is exactly this: {inv.label(prize)} ({prize.rarity}). The scene shows it where it lies, "
                         "untouched: the player has not picked it up, and nothing there is taken")
            must += STOP_MUST.get(kind, "")
        stops = hostile or kind in R["stops"]                # (f427, review Q2) what the player could act on stops the walk; a sight does not
        if matter and (hostile or not deterred):
            must += matters.road_lines(matter[0], matter[1], hostile)
        _, sky = weather.describe(self.store.meta.seed, self.minutes)
        try:
            ev = generate(
                "road_event", SYSTEM,
                user(roads.road_text(self.world, a, b), tier, clock.season(self.minutes), clock.period(self.minutes), sky,
                     "; ".join(threads + [h["text"] for h in state.get("history", [])[-3:]]), lore, must,
                     sorted(self.world.roles), ", ".join(rkeys.values()), stops,
                     self.journey_facts(route, a, b, walked), self.road_company()),
                RoadEvent, temperature=0.95, max_tokens=900,
                validation_context={"hostile": hostile, "kind": kind, "want_journey": True,
                                    "stops": stops, "roles": sorted(self.world.roles)})
        except LLMError as e:
            console.debug(f"road: nothing happened this time ({e})")
            return None
        console.narrate(ev.journey.strip() or self.journey_line(route, a, b, walked))      # (f408) the road goes by before it happens
        console.ledger(f"On the road - {ev.title}")
        console.narrate(ev.scene)
        log.append(f"{ev.title}: {ev.scene}")
        self.road_effects(ev, tier, a, b, state)
        if matter and (hostile or not deterred):
            matters.road_shown(self, matter[0]["id"], carried=not hostile)
        if stops:
            role = "" if hostile else ev.meets_role if ev.meets_role in self.world.roles else \
                R["stop_roles"].get(kind, "") if kind in ("aid", "meeting") else ""      # (f427) someone in need is someone there
            stop = roads.make_stop(self.world, a, b, frac, minutes, ev.scene, role, ev.title, ev.detail, stop_name)
            stop.update(log=log[-6:], text=text, resume=(route[-1] if resume is None else resume) if hostile else "",
                        bound=route[-1], kind=kind, tier=tier)
            back, onward = list(stop["place"]["connects"])[0], list(stop["place"]["connects"])[-1]   # (f492) the stop's own ends, real places:
            back, onward = self.world.places[back].name, self.world.places[onward].name               # `a` may be the stop left behind, tidied next
            if camp:
                stop["camp"] = max(1, round(sum(self.world.places[wild].danger) / 2))
            if (self.player.road or {}).get("id") not in stop["place"]["connects"]:      # (f426) never one the new stop is joined to
                self.leave_road(stop["id"])                 # (f423) the stop they stood at is tidied away before the new one: its people too
            self.player.road = stop
            self.ensure_road_place()
            self.enter(stop["id"])
            if hostile:
                creature, enemies = hit
                if creature.temperament == "territorial" or self.sees_far():
                    for e in enemies:
                        e.starts_far = True
                self.wildlife = None
                if self.owns("scout_ahead"):
                    for e in enemies:
                        effects.put_status(e, "unaware", 1)     # Scout Ahead: you saw them first, and they have not seen you (raw, on purpose)
                from scenes.combat_scene import CombatScene
                self.combat = CombatScene.begin(self, creature, enemies, f"On the road,")
                if self.owns("scout_ahead") and self.combat is not None:
                    from engine import battlefield as bf
                    bf.gain(self.combat.fight.player, "concealed")
                    console.note("You saw them before they saw you (Scout Ahead).")
                return "fight"
            self.stop_waits(ev, kind, tier, b, prize)
            console.note(f"You stop here, on the road. Onward to {onward}, or back to {back}.")
            self.show_exits()
            return "stopped"
        return "go"

    # ---------- (f427) what waits at a stop, for the player to do something about ----------

    def stop_waits(self, ev, kind: str, tier: str, ahead: str, prize=None) -> None:
        """Nothing at a stop is settled for the player (the owner, review Q2): a find lies where it is until they pick it up, a hazard
        stands in the way until they decide how to get past it, and someone in need is helped only if the player helps them."""
        from engine import ledger
        road = self.player.road
        if kind == "find" and prize is not None:
            state = self.store.load_place(self.player.location)
            inv.leave_on_ground(state, prize, self.minutes)
            self.store.save_place(state)
            console.ledger(f"Lying here: {inv.label(prize)}.")
            ledger.add("found", item=prize.uid, say=f"{inv.label(prize)} lies here on the road, untouched: the player has not picked it up. "
                                                    "Never show it taken unless they do.")
        elif kind == "hazard":
            ends = list(self.world.places[road["id"]].connects)
            behind = road["from"] if road["from"] in ends else next((k for k in ends if k != ahead), "")
            road["hazard"] = {"tier": tier,                         # (f447) what it is and how hard; how to get past is the player's
                              "what": (ev.detail or ev.title).strip(), "behind": behind}       # going back the way they came passes nothing
        elif kind == "aid":
            role = (self.world.places[road["id"]].residents or {})
            who = next((n for n in self.present if n.role in role), None)
            if who is not None:
                road["aid"] = {"who": who.id, "name": who.label(self.acting), "need": (ev.detail or ev.title).strip(), "tier": tier}
        self.store.save_player(self.player)

    def stop_step(self, intent, refused: bool) -> None:
        """After each thing the player does at a stop: was it help for the one in need there, or their own way past the hazard?"""
        road = self.player.road
        if not road or self.player.location != road.get("id") or refused:
            return
        aid = road.get("aid")
        if aid and not aid.get("helped") and self.helps(intent, aid):
            aid["helped"] = True
            self.road_outcome(type("Aid", (), {"kind": "aid", "check": ""})(), aid.get("tier", "normal"), road["from"], road["to"],
                              road["from"])
            self.need_deed("road_help")
        hz = road.get("hazard")
        if hz and not hz.get("dealt") and intent.kind == "other":       # their own way past it, ruled as any attempt is (engine/ruling.py)
            hz["dealt"] = True
        self.store.save_player(self.player)

    def helps(self, intent, aid: dict) -> bool:
        """Is this a hand for the one in need: something given or done for them, never only a word or a question."""
        if intent.kind not in ("give", "use", "ability", "other"):
            return False
        if intent.target == aid["who"]:
            return True
        words = f"{intent.summary} {intent.speech}".lower()
        return intent.kind in ("other", "use") and bool(re.search(R["aid"]["help_words"], words))

    def leaving_stop(self, route: list[str], text: str) -> None:
        """Setting off from a stop: the hazard ahead is got past (or gone around), and walking past someone in need is seen by the party."""
        road = self.player.road
        if not road or self.player.location != road.get("id") or len(route) < 2:
            return
        hz = road.pop("hazard", None)
        if hz and not hz.get("dealt") and route[1] != hz.get("behind"):
            self.get_past(hz, text)
        aid = road.pop("aid", None)
        if aid and not aid.get("helped"):
            from engine import ledger
            ledger.add("departed", name=aid["name"], say=f"The player walked on past {aid['name']}, who needed help ({aid['need']}), "
                                                        "and did not help.")
            self.need_deed("pass_by")
        self.store.save_player(self.player)

    def get_past(self, hz: dict, text: str) -> None:
        """A hazard in the way: gone around (time, no risk) when the player's words say so. (f447) Otherwise they press straight on, and
        that is ruled in the moment like any attempt (engine/ruling.py): what it takes, a skill or an attribute, and how hard, from what
        the hazard is. Nothing about how to get past was named in advance (the owner: "let's have the model stop naming checks"). A
        ruling that there is no pushing through it sends them the long way round; no ruling to be had, the attempt is the act's own."""
        from engine import ruling
        hi = R["hazard"]["delay_minutes"][hz.get("tier", "normal")][1]
        what = hz["what"].rstrip(".")
        r = None
        if not re.search(R["hazard"]["around_words"], (text or "").lower()):
            r = ruling.ask(self, f"pressing straight on past {what}", text or "I keep going")
            if r is not None:                        # (f618, f623) what lacking a power means, and what a body can do, are the engine's
                r = ruling.settled(self, self.acting, r)
            if r is None or r.sense != "no":
                self.push_past(hz, r)
                return
        self.advance(hi, exert=True)
        console.ledger(f"There is no pushing straight through {what}: going around costs you {clock.describe_duration(hi)}." if r is not None
                       else f"Going around {what} costs you {clock.describe_duration(hi)}.")

    def push_past(self, hz: dict, r) -> None:
        """(f447) Pressing on past a hazard, as the ruling has it: a plain yes walks on; else the roll its check (or the act's own
        attribute) and how hard decide what it costs."""
        from engine import ruling
        c, rng, tier = self.player.character, self.rng, hz.get("tier", "normal")
        lo, hi = R["hazard"]["delay_minutes"][tier]
        ruled = {"check": r.stakes.check, "hard": r.stakes.hard} if r is not None else {}
        if r is not None and r.sense == "yes" and not ruled["check"]:
            return
        degree, _ = checks.roll(ruling.odds(self, "attempt", ruled), rng, c=c)
        console.note(checks.label(ruled.get("check") or "getting past", degree.replace("_", " ")))
        if degree in ("failure", "partial"):
            delay = rng.randint(lo, hi) // (2 if degree == "partial" else 1)
            self.advance(delay, exert=True)
            lost = ""
            if degree == "failure":
                top = pools.maximum(c, "health")
                c.health = max(1.0, pools.current(c, "health") - top * R["hazard"]["health_loss_pct"][tier] / 100)
                lost = " and you come away bruised"
            console.ledger(f"Getting past costs you {clock.describe_duration(delay)}{lost}.")

    # ---------- what an event does ----------

    def road_effects(self, ev, tier, a, b, state) -> None:
        t = self.minutes
        near = a if self.rng.random() < 0.5 else b
        if ev.news.strip():
            pulse.add_news(state, ev.news, near, t, ["everyone"], certainty="they say")
        lim_v, lim_d = R["danger_effect"]["max_value"][tier], R["danger_effect"]["max_days"][tier]
        for e in ev.effects:
            if e.kind == "fact" and e.text:
                pulse.add_news(state, e.text, near, t, [g for g in e.groups if g in self.world.knowledge_groups] or ["everyone"], certainty="they say")
            elif e.kind == "mark" and e.place in self.world.places and e.text and not self.world.places[e.place].danger:
                ps = self.store.load_place(e.place)
                ps.marks = (ps.marks + [e.text])[-12:]
                self.store.save_place(ps)
            elif e.kind == "lead" and e.text:
                from engine import discovery
                spot = e.place if pulse.known(self.world, e.place) else near
                data = self.store.load_discoveries()
                if discovery.add_lead(data, spot, e.text, t, self.rng):
                    self.store.save_discoveries(data)
                    pulse.add_news(state, e.text, spot, t, ["everyone"], certainty="they say")
            elif e.kind == "danger" and e.value:
                key = e.place if e.place in self.world.roads else roads.edge_key(self.world, a, b)
                worldstate.add_effect(state, {"kind": "danger", "place": key, "value": max(-lim_v, min(lim_v, e.value)),
                                         "until": t + max(1, min(lim_d, e.days or 3)) * 1440, "cause": ev.title})
        self.store.save_world_state(state)

    def road_prize(self, tier, a, b):
        """What a find on this road gives: rolled before the scene is written, so the scene shows the thing taken (f406: a road's find
        told of a dropped clerk's ledger, and the player took wool slippers)."""
        c = self.player.character
        rng = self.rng
        wilds = roads.nearby_wilds(self.world, a, b)
        level = max(1, round(sum(self.world.places[wilds[0]].danger) / 2)) if wilds else max(1, c.level // 2)
        level = min(level, max(1, c.level))
        rolls = R["find"]["rarity_rolls"][tier]
        best = max((loot.roll_rarity(rng) for _ in range(rolls)), key=RARITY.index)
        floor = R["find"]["rare_min"] if tier == "rare" else "common"
        return loot.make_drop(level, max(best, floor, key=RARITY.index), rng, loot.keeps_companions(c))

    def road_outcome(self, ev, tier, a, b, near, prize=None) -> None:
        """(f427) What helping someone in need on the road brings: coin pressed on them for their trouble, and the nearest town hears.
        Only when the player has helped (stop_step); a find and a hazard are never settled here any more, they wait for the player."""
        c = self.player.character
        if ev.kind != "aid":
            return
        lo, hi = R["aid"]["coins"][tier]
        wilds = roads.nearby_wilds(self.world, a, b)              # (f426) the land's level, as the find's prize reckons it (road_prize)
        level = min(max(1, round(sum(self.world.places[wilds[0]].danger) / 2)) if wilds else max(1, c.level // 2), max(1, c.level))
        pay = self.rng.randint(lo, hi) * max(1, level // 4)
        c.coins += pay
        town = pulse.town_of(self.world, near)
        if not self.world.places[town].danger:
            self.player.reputation[town] = max(-100, min(100, self.player.reputation.get(town, 0) + R["aid"]["reputation"][tier]))
        console.ledger("Your help is remembered, and repaid.")
        self.store.save_player(self.player)

    # ---------- after a fight on the road ----------

    def road_fight_over(self, outcome: str) -> None:
        road = self.player.road
        if not road:
            return
        if outcome == "victory" and road.get("camp"):
            self.loot_camp(road.pop("camp"))
        if outcome == "victory" and road.get("resume"):
            road["log"] = (road.get("log", []) + [f"{road.get('title') or 'On the road'}: the player fought it out there, won, and went on."])[-6:]
            self.resume_pending = (road["resume"], road.get("text", ""))     # (f417) the arrival is told the fight; the walk waits on any yield
        elif outcome == "defeat":
            self.player.road = None
        road["resume"] = ""

    def loot_camp(self, level: int) -> None:
        """The spoils of a bandit camp: coin and good gear, left behind when the outlaws fall."""
        B = R["bandits"]
        rng, c = self.rng, self.player.character
        coins = rng.randint(*B["camp_coins_per_level"]) * level
        c.coins += coins
        best = max((loot.roll_rarity(rng) for _ in range(B["camp_rarity_rolls"])), key=RARITY.index)
        item = loot.make_drop(level, max(best, "uncommon", key=RARITY.index), rng, loot.keeps_companions(c))
        left = inv.add(self.pack, item, self.pack_slots())
        console.note(f"You search the camp. Stolen coin: {money.fmt(coins)}. " +
                     (f"And {inv.label(item)}." if left is None else f"There is {inv.label(item)} too, but your pack is full."))
        from engine import ledger                                           # (f417)
        ledger.add("gained" if left is None else "left", item=item.uid,
                   say=f"In the outlaws' camp the player finds stolen coin and {inv.label(item)}" + (", and takes both." if left is None
                       else "; the coin is taken, the rest left: their pack is full. Never show it carried."))
        self.store.save_player(self.player)

    def resume_road(self) -> None:
        dest, text = self.resume_pending
        self.resume_pending = None
        console.note("You get your breath back and carry on.")
        self.on_move(ActionIntent(kind="move", destination=dest), text)
