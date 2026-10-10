"""Road events: the journey is walked in legs, and some legs bring something the model invents.
Big events (the rare tier) stop the player on the road; small ones happen and the walk goes on. Fights always stop it,
and afterwards a small one carries on to the destination by itself."""

import random

from engine import checks, clock, encounters, inventory as inv, loot, money, pools, pulse, roads, weather
from engine.road_prompts import SYSTEM, user
from engine.roads import R
from llm.contracts import ActionIntent, RoadEvent
from llm.gateway import LLMError, generate
from ui import console
from world.loader import Place

RARITY = ["crude", "common", "uncommon", "rare", "epic", "legendary"]


class RoadActions:

    # ---------- the stop on the road ----------

    def ensure_road_place(self) -> None:
        road = self.player.road
        if road and road["id"] not in self.world.places:
            self.world.places[road["id"]] = Place(**road["place"])

    def leave_road(self, new_place: str) -> None:
        """Called when the player stands anywhere but the stop: tidy it away."""
        road = self.player.road
        if not road or new_place == road["id"]:
            return
        for nid in self.store.load_place(road["id"]).residents:
            npc = self.store.load_npc(nid)
            if not npc.gone:
                pulse.remove_npc(self.store, self.world, npc, "moved on along the road", self.minutes)
        self.player.road = None
        self.world.places.pop(road["id"], None)
        self.end_conversation()
        self.last_spoken = None
        self.present = []

    # ---------- walking ----------

    def run_journey(self, route: list[str], walk: int, text: str) -> None:
        stretches = roads.edges(self.world, route, walk)
        legs = roads.plan_legs(walk)
        quiet = getattr(self, "journey_event_factor", 1.0)        # Swift Step thins out the troubles on this trip
        self.journey_event_factor = 1.0
        log = list((self.player.road or {}).get("log", []))
        done = events = 0
        for k, leg in enumerate(legs):
            self.advance(leg)
            done += leg
            if k == len(legs) - 1 or events >= R["max_per_trip"]:
                continue
            i, frac = roads.position(stretches, done)
            a, b, m = stretches[i]
            if m < R["min_edge_minutes"] or self.rng.random() >= R["chance_per_leg"] * quiet:
                continue
            outcome = self.road_event(route, a, b, m, frac, text, log)
            if outcome:
                events += 1
            if outcome in ("stopped", "fight"):
                return
        self.finish_journey(route, walk, text, log)

    def finish_journey(self, route: list[str], walk: int, text: str, log: list[str]) -> None:
        dest = route[-1]
        self.enter(dest)
        via = [self.world.places[p].name for p in route[1:-1] if p in self.world.places]
        passing = f" They pass through {', '.join(via)} on the way." if via else ""
        named = [r for r in (self.world.road_between(a, b) for a, b in zip(route, route[1:])) if r]
        if named:
            passing = f" They travel by {', then '.join(r.name for r in named)}: " + \
                " ".join(r.description for r in named[:2]) + (passing or "")
        happened = f" On the way: {' '.join(log[-4:])}" if log else ""
        self.narrate(f"After {clock.describe_duration(walk)} on foot, the player arrives at {self.place.name}.{passing}{happened} "
                     f"Describe what they find, mentioning the road only briefly.{self.brevity()}", text)
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

    def road_event(self, route, a, b, minutes, frac, text, log):
        tier = roads.roll_tier(self.rng)
        wilds = roads.nearby_wilds(self.world, a, b)
        hostile = bool(wilds) and self.rng.random() < min(R["hostile_max"], R["hostile"] * self.road_danger(a, b))
        hit = None
        deterred = camp = False
        BR = R["bandits"]
        if hostile:
            wild = self.rng.choice(wilds)
            themed = self.bandit_road(a, b)
            force = "bandit" if self.rng.random() < (BR["themed"] if themed else BR["base"]) else ""
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
        interrupts = tier in R["interrupt"]
        state = self.store.load_world_state()
        near = a if frac < 0.5 else b
        threads = [f"{t['title']} ({t['place']})" for t in state.get("threads", []) if t["status"] == "active"][-8:]
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
            must = ("outlaws watching from cover: the traveler looks far too dangerous, so they hold back and let them pass. "
                    "Not a fight; kind sight. Describe the unseen watchers and the tension, in the traveler's view")
        else:
            must = "a happening that is not a fight"
        _, sky = weather.describe(self.store.meta.seed, self.minutes)
        try:
            ev = generate(
                "road_event", SYSTEM,
                user(roads.road_text(self.world, a, b), tier, clock.season(self.minutes), clock.period(self.minutes), sky,
                     "; ".join(threads + [h["text"] for h in state.get("history", [])[-3:]]), lore, must, list(checks.CHECKS),
                     sorted(self.world.roles), ", ".join(rkeys.values()), interrupts or hostile),
                RoadEvent, temperature=0.95, max_tokens=900,
                validation_context={"hostile": hostile, "checks": list(checks.CHECKS)})
        except LLMError as e:
            console.debug(f"road: nothing happened this time ({e})")
            return None
        console.note(f"On the road - {ev.title}")
        console.narrate(ev.scene)
        log.append(f"{ev.title}: {ev.scene}")
        self.road_effects(ev, tier, a, b, state)
        if not hostile:
            self.road_outcome(ev, tier, a, b, near)
        if hostile or interrupts:
            role = ev.meets_role if ev.meets_role in self.world.roles and not hostile else ""
            stop = roads.make_stop(self.world, a, b, frac, minutes, ev.scene, role, ev.title, ev.detail)
            stop.update(log=log[-6:], text=text, resume=route[-1] if hostile and not interrupts else "")
            if camp:
                stop["camp"] = max(1, round(sum(self.world.places[wild].danger) / 2))
            self.player.road = stop
            self.ensure_road_place()
            self.enter(stop["id"])
            if hostile:
                creature, enemies = hit
                if creature.temperament == "territorial" or self.has("danger_sense") is not None:
                    for e in enemies:
                        e.band = "far"
                self.wildlife = None
                from scenes.combat_scene import CombatScene
                self.combat = CombatScene.begin(self, creature, enemies, f"On the road,")
                return "fight"
            console.note(f"You stop here, on the road. Onward to {self.world.places[b].name}, or back to {self.world.places[a].name}.")
            self.show_exits()
            return "stopped"
        return "go"

    # ---------- what an event does ----------

    def road_effects(self, ev, tier, a, b, state) -> None:
        t = self.minutes
        near = a if self.rng.random() < 0.5 else b
        if ev.news.strip():
            pulse.add_news(state, ev.news, near, t, ["everyone"])
        lim_v, lim_d = R["danger_effect"]["max_value"][tier], R["danger_effect"]["max_days"][tier]
        for e in ev.effects:
            if e.kind == "fact" and e.text:
                pulse.add_news(state, e.text, near, t, [g for g in e.groups if g in self.world.knowledge_groups] or ["everyone"])
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
                    pulse.add_news(state, e.text, spot, t, ["everyone"])
            elif e.kind == "danger" and e.value:
                key = e.place if e.place in self.world.roads else roads.edge_key(self.world, a, b)
                state["effects"].append({"kind": "danger", "place": key, "value": max(-lim_v, min(lim_v, e.value)),
                                         "until": t + max(1, min(lim_d, e.days or 3)) * 1440, "cause": ev.title})
        self.store.save_world_state(state)

    def road_outcome(self, ev, tier, a, b, near) -> None:
        c = self.player.character
        rng = self.rng
        wilds = roads.nearby_wilds(self.world, a, b)
        level = max(1, round(sum(self.world.places[wilds[0]].danger) / 2)) if wilds else max(1, c.level // 2)
        level = min(level, max(1, c.level))
        if ev.kind == "find":
            rolls = R["find"]["rarity_rolls"][tier]
            best = max((loot.roll_rarity(rng) for _ in range(rolls)), key=RARITY.index)
            floor = R["find"]["rare_min"] if tier == "rare" else "common"
            item = loot.make_drop(level, max(best, floor, key=RARITY.index), rng, loot.keeps_companions(c))
            left = inv.add(self.pack, item, self.pack_slots())
            console.note(f"You take: {inv.label(item)}." if left is None else
                         f"You find {inv.label(item)}, but your pack is full - you leave it.")
        elif ev.kind == "hazard":
            odds, _ = checks.chance(c, ev.check, self.check_triggers(ev.check, False))
            degree, _ = checks.roll(odds, rng)
            console.note(checks.label(ev.check, degree.replace("_", " ")))
            if degree in ("failure", "partial"):
                lo, hi = R["hazard"]["delay_minutes"][tier]
                delay = rng.randint(lo, hi) // (2 if degree == "partial" else 1)
                self.advance(delay)
                lost = ""
                if degree == "failure":
                    top = pools.maximum(c, "health")
                    c.health = max(1.0, pools.current(c, "health") - top * R["hazard"]["health_loss_pct"][tier] / 100)
                    lost = " and you come away bruised"
                console.note(f"It costs you {clock.describe_duration(delay)}{lost}.")
        elif ev.kind == "aid":
            lo, hi = R["aid"]["coins"][tier]
            pay = rng.randint(lo, hi) * max(1, level // 4)
            c.coins += pay
            town = pulse.town_of(self.world, near)
            if not self.world.places[town].danger:
                self.player.reputation[town] = max(-100, min(100, self.player.reputation.get(town, 0) + R["aid"]["reputation"][tier]))
            console.note("Your help is remembered, and repaid.")
        self.store.save_player(self.player)

    # ---------- after a fight on the road ----------

    def road_fight_over(self, outcome: str) -> None:
        road = self.player.road
        if not road:
            return
        if outcome == "victory" and road.get("camp"):
            self.loot_camp(road.pop("camp"))
        if outcome == "victory" and road.get("resume"):
            self.resume_pending = (road["resume"], road.get("text", ""))
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
        self.store.save_player(self.player)

    def resume_road(self) -> None:
        dest, text = self.resume_pending
        self.resume_pending = None
        console.note("You get your breath back and carry on.")
        self.on_move(ActionIntent(kind="move", destination=dest), text)
