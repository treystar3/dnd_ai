"""Leaving a place by a road, a gate or a compass direction without knowing where it ends, and the places a player learns of.
The rules (which roads leave where, forks, matching the player's words) are in engine/exits.py; this is the play of it."""
import re

from engine import clock, exits, mapview, roads
from engine.roads import R
from llm.gateway import LLMError
from ui import console

SETTLEMENTS = ("city", "town", "village")
KNOWS = {"innkeeper": 5, "server": 4, "merchant": 5, "caravan_master": 6, "scout": 5, "guild_clerk": 4, "guild_contractor": 4, "guild_master": 4,
         "watch_captain": 4, "guard": 4, "royal_guard": 4, "quartermaster": 4, "bargeman": 5, "dockhand": 4, "fisher": 3, "hunter": 3,
         "trapper": 3, "elder": 4, "loremaster": 5, "relic_dealer": 4, "courtier": 3, "noble": 3}


class ExitActions:
    from scenes.intercepts import Intercept as _I
    INTERCEPTS = (_I("exit", 100, "exit_request", "a way out of town by road, gate or compass direction"),)

    def here_top(self) -> str:
        w = self.world
        here = self.player.location if self.player.location in w.places else next(
            (v for v in reversed(self.player.visited) if v in w.places), "")
        return mapview.top_of(w, here) if here else ""

    def known_places(self) -> set[str]:
        been, heard = mapview.known(self.world, self.player.visited, self.player.location, self.player.heard)
        return been | heard

    # ---------- the roads out ----------

    def road_rows(self) -> list[dict]:
        """The ways out of here that lead somewhere the player does not know yet (the ones to known places are listed as those places)."""
        top = self.here_top()
        if not top or self.player.delve:
            return []
        known = self.known_places()
        rows = []
        for gp in exits.groups(self.world, top):
            if all(m["to"] in known for m in gp["members"]):
                continue
            rows.append({"dir": gp["dir"], "name": gp["label"][0].upper() + gp["label"][1:], "named": gp["named"]})
        return rows

    def exit_request(self, text: str) -> bool:
        """'I head out the east gate', 'take the Red Road': leave that way. True if this line was a way out."""
        top = self.here_top()
        if not top or self.player.delve or self.combat:
            return False
        gp, why = exits.match(self.world, top, text)
        if gp:
            self.leave_by(gp, text)
            return True
        if why and self.world.places[top].type in SETTLEMENTS:
            rows = ", ".join(f"{r['dir']} ({r['name'].lower()})" for r in self.road_rows())
            console.note(why + (f" Roads out of here: {rows}." if rows else ""))
            self.halted = True
            return True
        return False

    def goroad_click(self, text: str, back_to: str = "places") -> None:
        """The pane's hidden command:  #goroad <direction>  (#maproad from the map pane, which redraws the map instead of the places list)"""
        parts = text.split()
        d = parts[1] if len(parts) > 1 else ""
        gp = next((g for g in exits.groups(self.world, self.here_top()) if g["dir"] == d), None)
        if not gp:
            console.note("There is no road that way.")
        else:
            self.leave_by(gp, f"I head {d}.")
            self.halted = False
        if not self.combat:
            if back_to == "map":
                with console.scope("#map"):
                    self.show_map()
            else:
                with console.scope("#exits"):
                    self.show_places()

    def fork_text(self, gp: dict, top: str) -> str:
        """What the model is asked to describe at a fork: the branches by their road names and terrain, never by where they go."""
        names = sorted(p.name for p in self.world.places.values() if not p.parent)

        def scrub(t: str) -> str:
            for n in sorted(names, key=len, reverse=True):
                t = re.sub(re.escape(n.replace("the ", "", 1)), "somewhere ahead", t, flags=re.I)
            return t
        lines = []
        for m in gp["members"]:
            desc = scrub(m["road"].description) if m["road"] else "an ordinary track"
            lines.append(f"  - {exits.option_label(m)}: {desc}")
        return ("The player has walked a while along the road leaving {town} to the {d}, and the road forks. "
                "Describe the fork in two or three sentences: how each branch looks from here (the ground, the traffic, the weather), "
                "using only the notes below. Do NOT name any town or place, and do not say where any branch ends.\n"
                "BRANCHES:\n{lines}").format(town=self.world.places[top].name, d=gp["dir"], lines="\n".join(lines))

    def fork_walk(self, gp: dict, top: str, fork: int, text: str) -> int | None:
        """Walk the shared stretch to the fork. It rolls road events like any other trip. Returns how many happened,
        or None if one stopped the player on the road (a fight, or a big event)."""
        found = self.world.path(top, gp["members"][0]["to"])
        route = found[0] if found else []
        legs = roads.plan_legs(fork)
        quiet = getattr(self, "journey_event_factor", 1.0)
        log: list[str] = []
        done = events = 0
        for leg in legs:
            self.advance(leg, exert=True)
            done += leg
            if len(route) < 2 or events >= R["max_per_trip"] or fork < R["min_edge_minutes"]:
                continue
            if self.rng.random() >= R["chance_per_leg"] * quiet:
                continue
            a, b = route[0], route[1]
            m = max(1, self.world.travel_minutes(a, b))
            outcome = self.road_event(route, a, b, m, min(0.95, done / m), text, log, resume="",
                                      stop_name=f"the road out of {self.world.places[top].name}")
            if outcome:
                events += 1
            if outcome in ("stopped", "fight"):
                return None
        return events

    def leave_by(self, gp: dict, text: str) -> None:
        top = self.here_top()
        members = gp["members"]
        if len(members) == 1:
            self.travel_route(members[0]["to"], text)
            return
        fork = gp["fork_minutes"]
        self.end_conversation()
        events = self.fork_walk(gp, top, fork, text)
        if events is None:
            return                                    # something on the road stopped the walk before the fork
        try:
            self.narrate(self.fork_text(gp, top), text)
        except LLMError:
            console.narrate(f"The road forks ahead: {', or '.join(exits.option_label(m) for m in members)}.")
        console.note("The road forks: " + "; ".join(exits.option_label(m) for m in members) + ". Which way?")
        chosen = None
        for _ in range(3):
            answer = console.ask()
            if exits.wants_back(answer):
                self.advance(fork, exert=True)
                console.note("You turn back and walk the road home.")
                self.halted = True
                return
            chosen = exits.pick(gp, answer)
            if chosen:
                break
            console.note("Which fork? " + "; ".join(exits.option_label(m) for m in members) + ", or turn back.")
        chosen = chosen or members[0]
        console.note(f"You take {exits.option_label(chosen)}.")
        self.travel_route(chosen["to"], text, already=fork, events=events)

    # ---------- what the player has heard of ----------

    def hear(self, place_id: str, how: str = "") -> bool:
        """The player has learned of a place. True if it is new to them."""
        top = mapview.top_of(self.world, place_id)
        if top not in self.world.places or top in self.known_places():
            return False
        self.player.heard.append(top)
        p = self.world.places[top]
        console.note(f"You have heard of {p.name}{how}.")
        return True

    def hear_names(self, text: str) -> None:
        """Whoever names a place aloud has told the player of it."""
        low = (text or "").lower()
        for p in self.world.places.values():
            if p.parent:
                continue
            n = p.name.lower().replace("the ", "", 1)
            if len(n) >= 4 and re.search(rf"\b{re.escape(n)}\b", low):
                self.hear(p.id)

    def sync_heard(self) -> None:
        """A contract or request that names a place is a place the player has heard of."""
        for q in self.player.quests:
            pid = q.get("place")
            if pid and pid in self.world.places:
                self.hear(pid)

    def local_knowledge(self, npc) -> list[str]:
        """The places near their town that this person would know, as a line for their conversation. A traveller knows more than a farmer."""
        g = mapview.graph(self.world)
        top = mapview.top_of(self.world, npc.location)
        near = sorted(g.get(top, {}).items(), key=lambda kv: (kv[1], kv[0]))[:KNOWS.get(npc.role, 2)]
        if not near:
            return []
        bits = []
        for pid, minutes in near:
            m = next((m for gp in exits.groups(self.world, top) for m in gp["members"] if m["to"] == pid), None)
            way = f"to the {exits.sector_of(m['bearing'])}, " if m else ""
            bits.append(f"{self.world.places[pid].name} ({way}{clock.walk_words(minutes)})")            # (f349) as a local says it
        return ["PLACES AROUND HERE THAT YOU KNOW OF (mention them only if the player asks about the area, the roads, or where to go; "
                "never add places that are not listed): " + "; ".join(bits)]
