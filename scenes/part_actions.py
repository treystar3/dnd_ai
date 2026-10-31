"""(f394) Going about inside a place: to its parts, deeper in, and searching where you stand (engine/features.py; GOAL.md).

Bumbo Claat's session at the Tidepool Caves: "go to the darkest pocket of the rear tunnel" and "go to the dry chamber's threshold"
were read as setting out to find somewhere new, and each ended in a wall the narrator made up. Now a part the place has is a walk of a
few minutes; going further in leads to the next part, made as it is needed; a part a place like this would have, named by the player or
the passage, is made real when they go to it; the tide closes what it covers and says when it opens; and a search where the player
stands finds what that part holds."""
from __future__ import annotations

import random

from engine import features, ledger
from ui import console
from engine.names import cap_first                      # (f422) a capital first letter, the rest as written


class PartActions:

    def arrive_parts(self, place_id: str, same_place: bool) -> None:
        """On entering a place: its parts are made if they are not yet, and the player stands at its entry (or where they stood, when
        they never left: the game opened again, say)."""
        features.ensure(self, place_id)
        at = features.spot_of(self)
        if same_place and at is not None:
            return
        entry = features.entry_of(self, place_id)
        self.player.spot = entry.ref if entry is not None else ""

    def part_move(self, dest: str, text: str, adopt: bool = False) -> bool:
        """A move to somewhere inside this place: a part it has, deeper in, or (adopt) a part a place like this would have, named by
        the player or the passage. True if it was one."""
        if not features.grows_here(self.place) or features.leaving(f"{dest} {text}", self.place):
            return False                                            # "a hidden grotto beyond the caves" is somewhere else
        if dest.startswith("feature:"):                            # the interpreter chose one of PLACES by its ref
            e = self.store.load_entity(dest)
            if e is not None and e.place == self.player.location and e.state != "gone":
                self.go_to_part(e, text)
                return True
            dest = dest.split(":")[-1].replace("_", " ")
        named = features.named_part(dest)
        if features.DEEPER.search(dest) and not features.find(self, dest) and not named:
            self.go_deeper(text)
            return True
        e = features.find(self, dest)
        if e is None and adopt and named and (named[1] in features.kinds_here(self.place) or self.part_of_here(dest)):
            e = features.adopt(self, self.player.location, named[0], named[1], "player")
        if e is None:
            return False
        self.go_to_part(e, text)
        return True

    def go_to_part(self, e, text: str) -> None:
        from engine import entities
        ok, why = features.open_now(e, self.minutes)
        if not ok:
            console.note(why)
            ledger.add("closed", ref=e.ref, say=why)
            self.halted = True
            return
        self.end_conversation()
        at = features.spot_of(self)
        self.advance(features.F["budget"]["step_minutes"] * (0 if at is not None and at.ref == e.ref else 1))
        self.player.spot = e.ref
        first = e.state in ("unseen", "known")
        if first:
            e = entities.move(self.store, e, "explored", self.minutes, "walked to")
        ledger.add("moved", ref=e.ref, name=e.name, say=f"The player is now at {e.name}, within {self.place.name}.")
        sign = self.part_sign(e, first)
        self.narrate(f"The player walks a short way within {self.place.name}, to {e.name}: {e.data.get('what', '')} {sign}"
                     "Describe getting there and what is there. Nothing else is there; nobody is there unless named here.", text)

    def part_sign(self, e, first: bool) -> str:
        """What can be seen of what a part holds, walking in; a hazard is met on the first walk in, by a check."""
        h = e.data.get("holds", "none")
        if h == "lair" and e.data.get("creature") in self.world.bestiary:
            return f"There are signs that {self.world.bestiary[e.data['creature']].name.lower()}s den here: tracks, bones, the smell. "
        if h == "resource" and e.data.get("good"):
            from engine import inventory
            g = inventory.GOODS.get(e.data["good"])
            return f"{cap_first(g.name)} grows here. " if g else ""
        if h == "hazard" and first and not e.data.get("met"):
            return self.meet_hazard(e)
        if h == "hazard":
            return f"Take care here: {e.data.get('hazard', '')}. "
        if e.data.get("clue") and not e.data.get("read"):
            return "Something here could be read or found by looking closely. "
        return ""

    def meet_hazard(self, e) -> str:
        from engine import checks, entities, pools
        c = self.player.character
        odds, _ = checks.chance(c, e.data.get("check", "perception"), self.check_triggers(e.data.get("check", "perception"), False))
        degree, _ = checks.roll(odds, self.rng, c=c)
        e.data["met"] = True
        self.store.save_entity(e)
        if degree in ("success", "strong success"):
            console.ledger(f"You see it in time: {e.data.get('hazard', '')} ({degree}).")
            return f"The player notices the danger in time and steps around it: {e.data.get('hazard', '')}. "
        lost = round(pools.maximum(c, "health") * e.data.get("cost", 6) / 100)
        c.health = max(1.0, pools.current(c, "health") - lost)
        console.ledger(f"{e.data.get('hazard', '').capitalize()}: -{lost} health ({degree}).")
        ledger.add("hurt", ref=e.ref, amount=lost, say=f"The player is caught by {e.data.get('hazard', '')} and hurt ({lost} health).")
        return f"The player does not see it in time and is hurt: {e.data.get('hazard', '')}. "

    def go_deeper(self, text: str) -> None:
        """Further in: the next part beyond where the player stands, a part they have not walked yet first, else one made now, a step
        deeper, of a kind this place has. When the place has grown all it may, the deepest part is where the way ends, and it is said
        so plainly: a real end, the same every time, never a wall made up on the spot."""
        loc = self.player.location
        at = features.spot_of(self) or features.entry_of(self, loc)
        parts = features.here(self.store, loc)
        on = [e for e in parts if at is not None and e.ref in at.data.get("links", []) and features.depth(e) > features.depth(at)]
        ahead = sorted(on, key=lambda e: (e.state != "unseen", e.state == "explored", features.depth(e)))
        nxt = next((e for e in ahead if features.open_now(e, self.minutes)[0]), None)
        if nxt is None or nxt.state == "explored":
            grown = features.grow(self, loc, at, random.Random(f"{self.store.meta.seed}:{loc}:{len(parts)}:{self.minutes // 60}"))
            nxt = grown or nxt
        if nxt is None:
            closed = next((e for e in ahead if not features.open_now(e, self.minutes)[0]), None)
            if closed is not None:
                self.go_to_part(closed, text)
                return
            self.end_conversation()
            self.advance(features.F["budget"]["step_minutes"])
            where = at.name if at is not None else self.place.name
            ledger.add("end", ref=at.ref if at else "", say=f"There is no way further in than {where}.")
            self.narrate(f"The player looks for a way further in from {where}, and there is none that anyone could take: the place ends here "
                         "(rock, water or growth too thick). Describe the end of the way, plainly and as the same every time.", text)
            return
        self.go_to_part(nxt, text)

    def explore_parts(self, intent, text: str) -> bool:
        """Exploring inside a place made of parts: further in, or to a part the words name. False to let exploring look for somewhere
        new beyond the place (engine/discovery.py)."""
        if not features.grows_here(self.place) or features.leaving(f"{intent.seek} {text}", self.place):
            return False
        seek = (intent.seek or intent.destination or "").strip()
        if not seek or features.DEEPER.search(seek) or features.DEEPER.search(text):
            if features.find(self, seek) is None and not features.named_part(seek):
                self.go_deeper(text)
                return True
        return self.part_move(seek, text, adopt=True)

    def search_part(self, intent, text: str) -> bool:
        """A search where the player stands finds what that part holds, once: the clue it keeps, the cache, a resource, or the creature
        that dens there. False when the part holds nothing yet unfound (the search goes on as before)."""
        e = features.spot_of(self)
        if e is None or e.data.get("found") or self.__dict__.get("_following"):
            return False
        if not self.about_spot(e, intent.seek or "", text):        # a hunt for a creature, or after tracks, goes on as a search
            return False
        h = e.data.get("holds", "none")
        if e.data.get("clue") and not e.data.get("read"):
            clue = e.data["clue"].replace("{low_tide}", features.low_tide_text(self.minutes))
            e.data["read"] = True
            self.store.save_entity(e)
            self.advance(10)
            ledger.add("found", ref=e.ref, what="clue", say=f"What the player finds at {e.name}: {clue}")
            console.ledger(f"Found at {e.name}: {clue}")
            self.narrate(f"The player looks closely at {e.name} and finds this: {clue} Describe them finding it and what it says, exactly "
                         "as given.", text)
            return True
        if h == "lair" and e.data.get("creature") in self.world.bestiary:
            e.data["found"] = True
            self.store.save_entity(e)
            intent.seek = self.world.bestiary[e.data["creature"]].name
            return self.maybe_encounter(0.95, f"At {e.name}, where they den:", intent.seek)
        if h == "cache":
            from engine import money
            e.data["found"] = True
            self.store.save_entity(e)
            coins = random.Random(f"{e.ref}:cache").randint(5, 20) * max(1, self.player.character.level)
            self.player.character.coins += coins
            self.advance(15)
            console.ledger(f"Found at {e.name}: {money.fmt(coins)}")
            ledger.add("found", ref=e.ref, what="cache", coins=coins, say=f"At {e.name} the player finds {e.data.get('sign', 'a cache')} "
                                                                             f"holding old coin.")
            self.narrate(f"The player searches {e.name} and finds {e.data.get('sign', 'a cache')}, with old coin "
                         "inside. Describe the find; nothing else is in it.", text)
            return True
        if h == "resource" and e.data.get("good"):
            from engine import inventory
            e.data["found"] = True
            self.store.save_entity(e)
            item = inventory.make_good(e.data["good"], 2)
            st = self.to_pack(item)
            self.advance(20)
            console.ledger(f"Gathered: {inventory.label(item)}.")              # (f424) a real find shows its line, like the clue and the cache
            ledger.add("found", ref=e.ref, what="resource", say=f"The player gathers {inventory.label(item)} at {e.name}.")
            self.narrate(f"The player gathers {inventory.label(item)} at {e.name}. Describe it."
                         + (" Their pack is full: what will not fit is left where it grew." if st.left is not None else ""), text)
            return True
        return False

    SPOT_WORDS = ("here", "around", "this spot", "this place", "closely", "carefully", "where i stand", "about")
    CLUE_WORDS = ("mark", "marks", "scratch", "scratches", "writing", "carving", "carvings", "notches", "wall", "clue", "read")

    def about_spot(self, e, seek: str, text: str) -> bool:
        """Whether a search is about the part the player stands at: nothing in particular, the part itself, or what it holds; not a
        hunt for a creature that does not den here, and not following tracks."""
        low = f"{seek} {text}".lower()
        if self.TRAIL_WORDS.search(seek) and self.fresh_trail():
            return False
        if e.data.get("holds") == "lair" and e.data.get("creature") in self.world.bestiary and \
                self.world.bestiary[e.data["creature"]].name.lower().split()[-1] in low:
            return True
        from engine import encounters
        if seek and encounters.matching(self.world, list(self.world.bestiary), seek):
            return False                                            # hunting something by name
        if not seek.strip() or any(w in low for w in self.SPOT_WORDS):
            return True
        own = set(e.name.lower().split()) - {"the"}
        return bool(own & set(low.split())) or (bool(e.data.get("clue")) and any(w in low.split() for w in self.CLUE_WORDS))

    def adopt_from_passage(self, shown: str) -> list:
        """(f394) The parts of this place a passage of the narrator named, made real, within the budget: what the narrator names becomes
        real (GOAL.md). The rear tunnel it wrote at the Tidepool Caves is now somewhere the player can go."""
        if not features.grows_here(self.place) or not shown:
            return []
        out = []
        import re
        for m in re.finditer(r"\b(the|a|an)\s+((?:[a-z'-]+\s+){1,2}[a-z'-]+)", shown.lower()):
            if len(out) >= features.F["budget"]["adopt_per_passage"]:
                break
            named = features.named_part(m.group(2))
            if not named or named[1] not in features.kinds_here(self.place):
                continue
            if features.find(self, named[0]) is not None:
                continue
            e = features.adopt(self, self.player.location, named[0], named[1], "narrated")
            if e is not None:
                out.append(e)
        return out
