"""Exploring: the player goes looking for somewhere that isn't on the map, or follows up a rumor. The engine rolls whether
anything is there; the model invents what; the engine checks it, keeps it, and puts it on the map."""

import random
import re

from engine import checks, clock, discovery, pulse
from engine.discovery import X
from engine.explore_prompts import SYSTEM, user
from llm.contracts import DiscoveryProposal
from llm.gateway import LLMError, generate
from ui import console


NOT_A_SPOT = {"north", "south", "east", "west", "back", "away", "road", "path", "trail", "track", "tracks", "area", "place", "side",
              "edge", "there", "here", "into", "toward", "towards", "deeper", "further", "beyond", "around", "near", "nearby", "other",
              "over", "from", "with", "that", "this", "where", "somewhere", "something", "anywhere", "hidden", "secret", "shortcut"}


class ExploreActions:

    def part_of_here(self, dest: str) -> bool:
        """(f381) Is `dest` a spot inside where the player is: named by this place's own description, or by the passage they just read?
        At the Tidepool Caves, 'the dry chamber' is in the place's description and 'the dry chamber's threshold' was where the tracks
        led; going there was read as setting out to find somewhere new, and the model was asked to invent it."""
        words = [w for w in re.findall(r"[a-z]+", (dest or "").lower()) if len(w) >= 4 and w not in NOT_A_SPOT]
        seen = " ".join(list(self.place.visible) + list(self.recent_narration[-1:])).lower()
        return bool(words) and any(re.search(rf"\b{re.escape(w)}", seen) for w in words)

    def within_place(self, dest: str, text: str) -> None:
        """(f381) A few steps to that spot: no hours, no invention, nobody added."""
        self.end_conversation()
        self.advance(X.get("within_minutes", 5))
        self.narrate(f"The player walks a short way, still within {self.place.name}, to {dest}. Describe getting there and what is "
                     "there, from what this place is known to hold; add no one and nothing of value.", text)

    def ensure_discoveries(self) -> None:
        discovery.apply_all(self.world, self.store.load_discoveries())

    def explore_chance(self, seek: str) -> float:
        c = self.player.character
        best = max(checks.chance(c, k, self.check_triggers(k, False))[0] for k in ("perception", "lore"))
        chance = X["base_chance"] + X["check_weight"] * best / 100
        for mech, bonus in X["passives"].items():
            if self.has(mech) is not None:
                chance += bonus
        return max(X["min_chance"], min(X["max_chance"], chance))

    def on_explore(self, intent, text: str) -> None:
        here = self.player.location
        place = self.world.places[here]
        if place.type in ("road", "dungeon") or self.combat:
            console.note("Not from here. Get to a proper place first.")
            self.halted = True
            return
        seek = (intent.seek or intent.destination or text).strip()
        data = self.store.load_discoveries()
        lead = discovery.match_lead(data, here, seek, self.minutes)
        chance = X["lead_chance"] if lead else self.explore_chance(seek)
        self.end_conversation()
        self.advance(self.rng.randint(*[h * 60 for h in X["hours"]]))
        if not discovery.room(data, here) or self.rng.random() >= chance:
            self.narrate(f"The player goes looking beyond what they already know, searching for: {seek}. They find nothing new "
                         f"- only more of {place.name}. Describe the search and its fruitlessness.", text)
            return
        found = self.invent_discovery(here, seek, lead, data)
        if not found:
            self.narrate(f"The player goes looking beyond what they already know, searching for: {seek}. A promising lead "
                         f"comes to nothing. Describe that.", text)
            return
        if lead:
            data = self.store.load_discoveries()
            data["leads"] = [l for l in data["leads"] if l["id"] != lead["id"]]
            self.store.save_discoveries(data)
        if found["kind"] == "place":
            p = self.world.places[found["id"]]
            console.note(f"You find somewhere new: {p.name}.")
            self.advance(found["minutes"])
            self.enter(found["id"])
            self.weight_hint = "rich"
            self.narrate(f"After searching for {seek}, the player has found {p.name}, a {p.type} off {place.name}. "
                         f"Describe arriving and what they see: {' '.join(p.visible)}", text)
        else:
            r = self.world.roads[found["id"]]
            console.note(f"You find a way: {r.name} - {r.description}")
            console.note(f"It runs from here to {self.world.places[r.to].name}, about "
                         f"{clock.describe_duration(found['minutes'])} on foot.")
            self.narrate(f"After searching for {seek}, the player finds {r.name}: {r.description} It leads to "
                         f"{self.world.places[r.to].name}. Describe the discovery.", text)
        self.show_exits()

    def invent_discovery(self, anchor: str, seek: str, lead: dict | None, data: dict) -> dict | None:
        """Ask the model, check what it says, keep it. Returns {'kind', 'id', 'minutes'} or None."""
        world = self.world
        state = self.store.load_world_state()
        a = world.places[anchor]
        safe, wild = discovery.allowed_types(world, anchor)
        reach = discovery.reachable(world, anchor)
        group = world.locals_group(anchor)
        lore = " ".join(f.text for f in world.lore.values() if group in f.known_by)[:600]
        threads = "; ".join(f"{t['title']} ({t['place']})" for t in state.get("threads", []) if t["status"] == "active")
        anchor_text = (f"{anchor} - {a.name} ({a.type}, {a.biome or 'settled'}, "
                       f"{'wild, danger ' + str(a.danger) if a.danger else 'safe'}); {' '.join(a.visible)[:400]}")
        try:
            prop = generate(
                "discovery", SYSTEM,
                user(anchor_text, seek, lead["text"] if lead else "", clock.season(self.minutes), lore, threads, safe, wild,
                     sorted(world.roles), "; ".join(f"{k}: {world.places[k].name}, {m} min" for k, m in reach.items()) or "none",
                     discovery.names(world, data)),
                DiscoveryProposal, temperature=0.9, max_tokens=700,
                validation_context={"types": safe + wild, "reachable": list(reach), "roles": sorted(world.roles)})
        except LLMError as e:
            console.debug(f"explore: the model found nothing ({e})")
            return None
        if not prop.found:
            return None
        rng = random.Random(f"{self.store.meta.seed}:explore:{self.minutes}")
        data = self.store.load_discoveries()
        if prop.kind == "place":
            made = discovery.make_place(world, anchor, prop, rng, self.minutes)
            if not made:
                return None
            data["places"].append(made)
            out = {"kind": "place", "id": made["place"]["id"], "minutes": made["minutes"]}
        else:
            made = discovery.make_track(world, anchor, prop, rng, self.minutes)
            if not made:
                return None
            data["tracks"].append(made)
            out = {"kind": "track", "id": made["id"], "minutes": made["minutes"]}
        self.store.save_discoveries(data)
        discovery.apply_all(world, data)
        from engine.domain_events import PlaceDiscovered
        self.notice(PlaceDiscovered(minute=self.minutes, place=self.player.location, found=out["id"], what=out["kind"], name=prop.name.strip()))
        if prop.news.strip():
            pulse.add_news(state, prop.news, anchor, self.minutes, ["everyone"])
            self.store.save_world_state(state)
        return out
