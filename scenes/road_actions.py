"""Road events: the journey is walked in legs, and some legs bring something the model invents.
Big events (the rare tier) stop the player on the road; small ones happen and the walk goes on. Fights always stop it,
and afterwards a small one carries on to the destination by itself."""


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

    def run_journey(self, route: list[str], walk: int, text: str, events: int = 0) -> None:
        stretches = roads.edges(self.world, route, walk)
        legs = roads.plan_legs(walk)
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
            if m < R["min_edge_minutes"] or self.rng.random() >= R["chance_per_leg"] * quiet:
                continue
            outcome = self.road_event(route, a, b, m, frac, text, log, walked=done)
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
        r = self.world.road_between(a, b)
        way = r.name if r else f"the way toward {self.world.places[b].name}"
        return (f"set out from {self.world.places[route[0]].name}, bound for {self.world.places[route[-1]].name}; now on {way}, "
                f"{clock.describe_duration(max(5, walked))} into the walk")

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
        interrupts = tier in R["interrupt"]
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
                prize = self.road_prize(tier, a, b)
                if inv.fits(self.pack, prize, self.pack_slots()):
                    must += (f". What the player finds and takes is exactly this: {inv.label(prize)} ({prize.rarity}). The scene shows "
                             f"that thing; nothing else there can be taken")
                else:                                        # (f417) room is checked first: a full pack leaves it where it lies
                    must += (f". What the player finds is exactly this: {inv.label(prize)} ({prize.rarity}), but their pack is full and "
                             f"they leave it where it lies. The scene shows that thing left behind; nothing there is taken")
        if matter and (hostile or not deterred):
            must += matters.road_lines(matter[0], matter[1], hostile)
        _, sky = weather.describe(self.store.meta.seed, self.minutes)
        try:
            ev = generate(
                "road_event", SYSTEM,
                user(roads.road_text(self.world, a, b), tier, clock.season(self.minutes), clock.period(self.minutes), sky,
                     "; ".join(threads + [h["text"] for h in state.get("history", [])[-3:]]), lore, must, list(checks.CHECKS),
                     sorted(self.world.roles), ", ".join(rkeys.values()), interrupts or hostile,
                     self.journey_facts(route, a, b, walked), self.road_company()),
                RoadEvent, temperature=0.95, max_tokens=900,
                validation_context={"hostile": hostile, "checks": list(checks.CHECKS), "kind": kind, "want_journey": True})
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
        if not hostile:
            self.road_outcome(ev, tier, a, b, near, prize)
        if hostile or interrupts:
            role = ev.meets_role if ev.meets_role in self.world.roles and not hostile else ""
            stop = roads.make_stop(self.world, a, b, frac, minutes, ev.scene, role, ev.title, ev.detail, stop_name)
            stop.update(log=log[-6:], text=text, resume=(route[-1] if resume is None else resume) if hostile and not interrupts else "")
            if camp:
                stop["camp"] = max(1, round(sum(self.world.places[wild].danger) / 2))
            self.leave_road(stop["id"])                     # (f423) the stop they stood at is tidied away before the new one: its people too
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
                        e.statuses["unaware"] = 1         # Scout Ahead: you saw them first, and they have not seen you
                from scenes.combat_scene import CombatScene
                self.combat = CombatScene.begin(self, creature, enemies, f"On the road,")
                if self.owns("scout_ahead") and self.combat is not None:
                    from engine import battlefield as bf
                    bf.gain(self.combat.fight.player, "concealed")
                    console.note("You saw them before they saw you (Scout Ahead).")
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
        c = self.player.character
        rng = self.rng
        if ev.kind == "find":
            item = prize or self.road_prize(tier, a, b)
            left = inv.add(self.pack, item, self.pack_slots())
            console.ledger(f"You take: {inv.label(item)}." if left is None else
                         f"You find {inv.label(item)}, but your pack is full - you leave it.")
            from engine import ledger                       # (f417) and the arrival is told which
            ledger.add("gained" if left is None else "left", item=item.uid,
                       say=f"On the road the player found {inv.label(item)}" + (" and took it." if left is None
                                                                               else ", and left it there: their pack was full. Never show it carried."))
        elif ev.kind == "hazard":
            odds, _ = checks.chance(c, ev.check, self.check_triggers(ev.check, False))
            degree, _ = checks.roll(odds, rng, c=c)
            console.note(checks.label(ev.check, degree.replace("_", " ")))
            if degree in ("failure", "partial"):
                lo, hi = R["hazard"]["delay_minutes"][tier]
                delay = rng.randint(lo, hi) // (2 if degree == "partial" else 1)
                self.advance(delay, exert=True)
                lost = ""
                if degree == "failure":
                    top = pools.maximum(c, "health")
                    c.health = max(1.0, pools.current(c, "health") - top * R["hazard"]["health_loss_pct"][tier] / 100)
                    lost = " and you come away bruised"
                console.ledger(f"It costs you {clock.describe_duration(delay)}{lost}.")
        elif ev.kind == "aid":
            lo, hi = R["aid"]["coins"][tier]
            pay = rng.randint(lo, hi) * max(1, level // 4)
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
