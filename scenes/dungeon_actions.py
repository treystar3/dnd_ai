"""Dungeons in play: pressing on through chambers, traps, caches, quiet rooms, bosses, leaving and respawning."""

import random

from engine import combat, dungeons, items, loot, money
from engine import field as _field
from ui import console

D = dungeons.D


class DungeonActions:

    # ---------- the dungeons of this campaign ----------

    def ensure_dungeons(self) -> None:
        """Make a dungeon beneath each dangerous wild place, remake any that are due, and put entrances on the map."""
        known = {d["place"]: d for d in self.store.load_dungeons()}
        changed = False
        for place in [p for p in self.world.places.values() if p.danger and p.type != "dungeon"]:
            if place.danger[1] < D["min_zone_level"] or place.id in dungeons.FIXED_PLACES:
                continue
            d = known.get(place.id)
            if d is not None and dungeons.due_for_respawn(d, self.minutes) and \
                    (self.combat or (self.player.delve and self.player.delve.get("dungeon") == d["id"])):
                continue  # never remake a dungeon while the player is inside it or fighting
            if d is None or dungeons.due_for_respawn(d, self.minutes):
                fresh = dungeons.generate(place, self.world, f"{self.store.meta.seed}:{place.id}:{self.minutes}", self.minutes)
                if not fresh:
                    continue
                if d is not None:
                    if self.player.delve and self.player.delve.get("dungeon") == d["id"]:
                        self.player.delve = None
                        console.note(f"{d['name'].capitalize()} has shifted and been remade - your progress there is lost.")
                    fresh["entrance"] = d["entrance"]
                    self.void_dungeon_contracts(d["id"], fresh)
                known[place.id] = fresh
                changed = True
        if changed:
            self.store.save_dungeons(list(known.values()))
        for d in known.values():
            if d["entrance"] not in self.world.places:
                self.world.places[d["entrance"]] = dungeons.entrance_place(d, self.world)
            self.world.places[d["place"]].connects.setdefault(d["entrance"], 10)

    def dungeon_here(self) -> dict | None:
        return next((d for d in self.store.load_dungeons() if d["entrance"] == self.player.location), None)

    def save_dungeon(self, d: dict) -> None:
        all_d = [x if x["id"] != d["id"] else d for x in self.store.load_dungeons()]
        self.store.save_dungeons(all_d)

    def show_dungeon(self) -> None:
        d = self.dungeon_here() or next((x for x in self.store.load_dungeons() if x["place"] == self.player.location), None)
        if not d:
            console.note("There's no dungeon here.")
            return
        days = max(0, (d["made"] + D["respawn_days"] * 1440 - self.minutes) // 1440)
        cf, cc = d["cleared"]
        sense = self.owns("arcane_echoes") or (self.owns("spirit_guide") and self.companion_here())
        floors = []
        for i, fl in enumerate(d["floors"]):
            n = len(fl["chambers"])
            done = n if i < cf else (cc + 1 if i == cf else 0)
            row = {"n": i + 1, "letter": fl["letter"], "done": done, "total": n, "boss": i == len(d["floors"]) - 1}
            if sense:
                kinds = sorted({self.world.bestiary[ch["creature"]].name.lower() for ch in fl["chambers"] if ch["kind"] == "fight"})
                traps = sum(ch["kind"] == "trap" for ch in fl["chambers"])
                row["sense"] = (", ".join(kinds) or "nothing living") + (f"; {traps} trap(s)" if traps else "")
            floors.append(row)
        delve = self.player.delve if self.player.delve and self.player.delve.get("dungeon") == d["id"] else None
        if console.panel("dungeon", {"name": d["name"], "theme": d["theme"], "beneath": self.world.places[d["place"]].name, "remade_days": days,
                                     "floors": floors, "on_floor": (delve["floor"] + 1) if delve else 0}):
            return
        console.note(f"{d['name'].upper()} - a {d['theme']} beneath {self.world.places[d['place']].name}. "
                     f"Remade in {days} days.")
        for i, fl in enumerate(d["floors"]):
            n = len(fl["chambers"])
            done = n if i < cf else (cc + 1 if i == cf else 0)
            boss = " · boss" if i == len(d["floors"]) - 1 else ""
            console.note(f"  floor {i + 1} [{fl['letter']}] - {done}/{n} chambers cleared{boss}")
            if self.owns("arcane_echoes") or (self.owns("spirit_guide") and self.companion_here()):
                kinds = sorted({self.world.bestiary[ch["creature"]].name.lower() for ch in fl["chambers"] if ch["kind"] == "fight"})
                traps = sum(ch["kind"] == "trap" for ch in fl["chambers"])
                console.note(f"      you sense: {', '.join(kinds) or 'nothing living'}" + (f"; {traps} trap(s)" if traps else ""))

    # ---------- moving through ----------

    def on_delve(self, intent, text: str) -> None:
        d = self.dungeon_here()
        if not d:
            self.refuse("You need to be at a dungeon's entrance to go down.")
            return
        nxt = dungeons.next_chamber(d)
        if nxt is None:
            days = max(0, (d["made"] + D["respawn_days"] * 1440 - self.minutes) // 1440)
            self.refuse(f"{d['name'].capitalize()} is cleared to the bottom. It will be remade in {days} days.")
            return
        f, c = nxt
        floor = d["floors"][f]
        chamber = floor["chambers"][c]
        if not self.player.delve:
            where = "the first chamber" if (f, c) == (0, 0) else f"floor {f + 1}, where you left off"
            console.note(f"You descend into {d['name']} and make your way to {where}.")
        self.player.delve = {"dungeon": d["id"], "floor": f, "chamber": c, "rest": False}
        self.ensure_light(d)
        self.advance(10, exert=True)
        label = f"Floor {f + 1} [{floor['letter']}], chamber {c + 1} of {len(floor['chambers'])}"
        kind = chamber["kind"]
        if kind == "fight" and not chamber.get("boss") and self.shadow_active():
            self.use_shadow()
            creature = self.world.bestiary[chamber["creature"]]
            console.note(label)
            console.note(f"You slip past the {creature.name.lower()} unseen. There's no fight, and no spoils.")
            self.narrate(f"The player, unseen, slips past the {creature.name.lower()} in a chamber of {d['name']} and goes on. "
                         f"Describe how they pass them without being noticed, fitting a {d['theme']}.", text)
            self.chamber_cleared(d, f, c)
            return
        if kind == "fight":
            creature = self.world.bestiary[chamber["creature"]]
            rank = "boss" if chamber.get("boss") else "normal"
            foes = []
            for i in range(chamber["count"]):
                name = chamber.get("name") or (d["boss_name"] if rank == "boss" else creature.name.lower() + (f" {i + 1}" if chamber["count"] > 1 else ""))
                foes.append(combat.fighter_from_creature(creature, chamber["level"], rank, f"e{i + 1}", name, "near"))
            self.dungeon_fight = (d["id"], f, c, d["made"])
            from scenes.combat_scene import CombatScene
            console.note(label + (" - the master of this place waits here." if rank == "boss" else ""))
            self.combat = CombatScene.begin(self, creature, foes, f"In the {d['theme']}'s depths ({label.lower()}),",
                                            big="lair" if rank == "boss" else "")
            return
        console.note(label)
        if kind == "trap":
            degree = "success" if (self.has("trap_sense") is not None or self.scouted_here(d, f, c) or chamber.get("disarmed")) \
                else self.resolve("perception")
            pct = {"strong success": 0, "success": 0, "partial": D["trap"]["damage_partial"]}.get(degree, D["trap"]["damage_failure"])
            c_ = self.player.character
            from engine import pools
            hurt = round(pools.maximum(c_, "health") * pct / 100 * (1 - (self.has("warded") or 0) / 100))
            c_.health = max(1, pools.current(c_, "health") - hurt)
            what = "spots the trap and steps around it" if not pct else f"springs a trap and is hurt ({hurt} damage)"
            self.narrate(f"The player enters a chamber of {d['name']} and {what}. Describe the trap, fitting a {d['theme']}.", text)
        elif kind == "cache":
            lo, hi = D["cache"]["coins_per_level"]
            picked = bool(chamber.get("picked"))
            coins = round(random.randint(lo, hi) * floor["level"] * (1 + (self.has("cache_hunter") or 0) / 100)
                          * (1 + (_field.F["picklock"]["coin_bonus"] if picked else 0)))
            self.player.character.coins += coins
            found = [money.words(coins)]
            if random.random() < D["cache"]["item_chance"] + (self.has("grave_robber") or 0) / 100 \
                    + (_field.F["picklock"]["item_bonus"] if picked else 0):
                item = self.cache_item(floor["level"])
                self.to_pack(item)
                found.append(item.name)
            console.ledger(f"Found: {', '.join(found)}.")
            self.narrate(f"The player finds a cache in a chamber of {d['name']}: {', '.join(found)}. Describe where it was "
                         f"hidden, fitting a {d['theme']}.", text)
        elif kind == "rest":
            self.player.delve["rest"] = True
            self.narrate(f"The player reaches a quiet chamber in {d['name']} - nothing lives here, and it would be a "
                         "safe place to rest.", text)
        self.chamber_cleared(d, f, c)

    def cache_item(self, level: int):
        rng = random.Random()
        bases = [b for b in items.CATALOG.values() if b.slot not in ("none", "neck", "ring") and b.min_level <= level]
        base = rng.choice(bases)
        rarity = loot.roll_rarity(rng)
        rarity = {"common": "uncommon", "crude": "common", "legendary": "epic"}.get(rarity, rarity)
        item = items.make(base.id, rarity, level, rng=rng)
        material = items.material_of(item)
        item.properties = loot.roll_properties(rarity, rng, material.extra_properties if material else 0)
        return item

    def void_dungeon_contracts(self, dungeon_id: str, fresh: dict) -> None:
        """A remade dungeon invalidates postings and delve quests that point at floors it no longer has."""
        def stale(q):
            return q.get("kind") == "delve" and q.get("dungeon") == dungeon_id and q.get("floor", 0) >= len(fresh["floors"])
        self.player.quests = [q for q in self.player.quests if not stale(q)]
        for pid in {self.player.location}:
            try:
                ps = self.store.load_place(pid)
                ps.board = [q for q in ps.board if not stale(q)]
                self.store.save_place(ps)
            except Exception:
                pass

    def chamber_cleared(self, d: dict, f: int, c: int) -> None:
        if f >= len(d["floors"]) or c >= len(d["floors"][f]["chambers"]):
            return
        if [f, c] > d["cleared"]:
            d["cleared"] = [f, c]
            self.save_dungeon(d)
        floor = d["floors"][f]
        if c == len(floor["chambers"]) - 1 and d.get("fixed") == "orenna":
            self.orenna_floor_done(d, f)
            self.store.save_player(self.player)
            return
        if c == len(floor["chambers"]) - 1:
            last = f == len(d["floors"]) - 1
            console.ledger(f"Floor {f + 1} cleared." + ("" if last else
                         f" Stairs lead down to floor {f + 2} [{d['floors'][f + 1]['letter']}]."))
            for q in self.player.quests:
                if q["kind"] == "delve" and q.get("dungeon") == d["id"] and q.get("floor") == f:
                    q["progress"] = 1
                    console.note(f"{q['title']}: done")
                if last and q["kind"] == "dungeon_boss" and q.get("dungeon") == d["id"]:
                    q["progress"] = 1
                    console.note(f"{q['title']}: done")
            if last:
                from engine import pulse
                from engine.domain_events import DungeonCleared
                self.notice(DungeonCleared(minute=self.minutes, place=d["place"], dungeon=d["id"], boss=d.get("boss_name", "")))
                state = self.store.load_world_state() or pulse.empty_state(self.minutes)
                pulse.add_news(state, f"A newcomer went down into {d['name']} and killed {d['boss_name']}.",
                               d["place"], self.minutes, ["guild", "hunters", "merchants",
                                                          self.world.locals_group(pulse.town_of(self.world, d['place'])) or "everyone"])
                self.store.save_world_state(state)
        self.store.save_player(self.player)

    def dungeon_fight_over(self, outcome: str) -> None:
        """Called when a fight that started in a dungeon ends."""
        info = getattr(self, "dungeon_fight", None)
        self.dungeon_fight = None
        if not info:
            return
        d = next((x for x in self.store.load_dungeons() if x["id"] == info[0]), None)
        if d is not None and d["made"] != info[3]:
            return  # the dungeon was remade mid-fight
        if outcome == "victory" and d:
            self.chamber_cleared(d, info[1], info[2])
        elif outcome == "fled":
            console.note("You fall back to the chamber you came from. The way ahead is still held.")
        elif outcome == "defeat":
            self.player.delve = None

    def on_leave_dungeon(self, intent, text: str) -> None:
        d = self.dungeon_here()
        if not d or not self.player.delve:
            console.note("You're not down in a dungeon.")
            return
        self.player.delve = None
        self.advance(15, exert=True)
        self.store.save_player(self.player)
        console.note(f"You climb back out of {d['name']}. Your progress is kept until it is remade.")
        self.narrate(f"The player climbs back up out of {d['name']} into the open air.", text)

    def dungeon_search(self, text: str) -> None:
        d = self.dungeon_here()
        degree = self.resolve("perception")
        self.advance(15)
        if self.owns("second_look") and degree not in ("strong success", "success"):
            degree = "success"
        if degree in ("strong success", "success"):
            coins = random.randint(1, 4) * max(1, d["floors"][self.player.delve["floor"]]["level"])
            self.player.character.coins += coins
            self.store.save_player(self.player)
            console.ledger(f"Found: {money.words(coins)}.")
            self.narrate(f"The player searches the chamber carefully and turns up {money.words(coins)} that others missed.", text)
        else:
            self.narrate(f"The player searches the chamber in {d['name']} but finds nothing more of use.", text)
