"""World passives: the small rules each one adds, gathered in one place. Call sites stay short."""

import random
from pathlib import Path

import yaml

from engine import clock, items, pools
from ui import console

ROOT = Path(__file__).resolve().parent.parent
TRAVEL = yaml.safe_load((ROOT / "data" / "rules" / "travel.yaml").read_text(encoding="utf-8"))

ARMED_ROLES = {"guard", "watch_captain", "royal_guard", "hunter", "guild_contractor", "elven_warden", "scout",
               "trapper", "guild_instructor"}
WILD_FOLK = {"farmer", "shepherd", "hunter", "herbalist", "trapper", "fisher", "lumberjack", "orchard_keeper"}
GIFTED_ROLES = {"noble", "courtier", "enchanter", "loremaster", "water_priest"}
HISTORY_WORDS = ("history", "legend", "old", "ancient", "story", "song", "ballad", "ruin", "war", "king", "founded",
                 "place", "road", "city", "town")
DARK_WORDS = ("dead", "undead", "death", "grave", "ghost", "spirit", "fiend", "demon", "devil", "curse", "hex",
              "hollow", "necro", "lich", "vampire", "shadow")
FOOD = {"food"}


class PassiveHooks:

    def mech(self, mid: str) -> float:
        return self.has(mid) or 0

    def owns(self, mid: str) -> bool:
        return self.has(mid) is not None

    def companion_here(self) -> bool:
        return any(m.active for m in self.player.character.companions)

    # ---------- checks ----------

    def check_bonuses(self, check: str, npc=None, talking: bool = False, text: str = "") -> list[tuple[str, float]]:
        out, night = [], clock.is_dark(self.minutes)
        words = text.lower()

        def add(mid, label=None, when=True, sign=1):
            if when and self.owns(mid):
                out.append((label or mid.replace("_", " "), sign * self.mech(mid)))
        shadow = self.fld.get("shadow")
        if check == "stealth" and shadow and shadow["until"] > self.minutes:
            from engine.field import F as FIELD, tier_value
            out.append(("shadowing", tier_value(FIELD["shadow"]["stealth_bonus"], shadow["tier"])))
        if self.blessed_bonus():
            out.append(("blessed", self.blessed_bonus()))
        edge = self.fld.get("edge")
        if npc is not None and edge and edge["npc"] == npc.id and edge["until"] > self.minutes \
                and check in edge.get("only", ("persuasion", "intimidation", "deception")):
            out.append(("cowed" if edge.get("only") else "won over", edge["bonus"]))
        if check == "perception" and self.darkness_penalty():
            out.append(("darkness", self.darkness_penalty()))
        if check == "intimidation":
            add("wild_presence")
            add("soldiers_bearing", when=bool(npc and npc.role in ARMED_ROLES))
            add("unsettling_presence", when=night)
        elif check == "stealth":
            worn = [items.weight(i) for i in self.player.character.equipment.values() if not items.base_of(i).is_weapon]
            heavy = min((items.RULES["weight_classes"].get(w, {}).get("stealth", 0) for w in worn if w), default=0)
            if heavy:
                out.append(("armor", heavy))
            add("night_prowler", when=night)
            add("quiet_step")
        elif check == "insight":
            add("still_mind")
            add("bedside_manner", when=bool(npc) or talking)
            add("mood_reader", when=self.companion_here())
        elif check == "perception":
            add("second_eyes", when=self.companion_here())
        elif check == "lore":
            add("bookish")
            add("old_ballads", when=any(w in words for w in HISTORY_WORDS)
                or any(p.name.lower().replace("the ", "") in words for p in self.world.places.values()))
            add("forbidden_lore", when=any(w in words for w in DARK_WORDS))
        elif check == "performance":
            add("stage_presence")
        elif check == "persuasion":
            add("honest_face")
        elif check == "deception":
            add("silver_tongue")
            if self.owns("honest_face"):
                out.append(("honest face", -15))
        return out

    # ---------- people ----------

    def in_kingdom(self, place_id: str) -> bool:
        from engine import pulse
        town = self.world.places[pulse.town_of(self.world, place_id)]
        return "crown" in (self.world.regions[town.region].ruled_by or "")

    def first_meeting_trust(self, npc) -> int:
        bonus = 0
        if self.owns("marked_by_gift") and self.in_kingdom(npc.location):
            bonus += round(self.mech("marked_by_gift")) if npc.role in GIFTED_ROLES else -5
        if npc.role in WILD_FOLK:
            bonus += round(self.mech("speaker_for_wild"))
        if npc.role == "guild_contractor":
            bonus += round(self.mech("recruiter"))
        return bonus

    def easy_company(self, npc) -> None:
        if self.owns("easy_company") and npc.met_player and npc.easy_bonus < 10 \
                and npc.easy_day != clock.day(self.minutes):
            npc.trust = min(100, npc.trust + 1)
            npc.easy_bonus += 1
            npc.easy_day = clock.day(self.minutes)

    # ---------- reputation ----------

    def town_rep(self, place_id: str | None = None) -> int:
        from engine import pulse
        return self.player.reputation.get(pulse.town_of(self.world, place_id or self.player.location), 0)

    def reputation_add(self, town: str, amount: int) -> None:
        if town and not self.world.places[town].danger:
            self.player.reputation[town] = max(-100, min(100, self.player.reputation.get(town, 0) + amount))

    def neighbor_towns(self, place_id: str) -> list[str]:
        """Settlements one step along the map from this place's town."""
        from engine import pulse
        here = pulse.town_of(self.world, place_id)
        out = []
        for pid in self.world.neighbors(here) if hasattr(self.world, "neighbors") else []:
            town = pulse.town_of(self.world, pid)
            if town != here and not self.world.places[town].danger and town not in out:
                out.append(town)
        if not out:
            for p in self.world.places.values():
                if here in p.connects or p.id in self.world.places[here].connects:
                    town = pulse.town_of(self.world, p.id)
                    if town != here and not self.world.places[town].danger and town not in out:
                        out.append(town)
        return out

    def mercy_spreads(self) -> None:
        """Mercy Remembered: kindness is talked about in the next town down the road."""
        if self.owns("mercy_remembered"):
            for town in self.neighbor_towns(self.player.location)[:1]:
                self.reputation_add(town, 1)

    def nearest_town(self, place_id: str) -> str | None:
        place = self.world.places[place_id]
        options = [(m, pid) for pid, m in place.connects.items() if not self.world.places[pid].danger]
        options += [(p.connects[place_id], p.id) for p in self.world.places.values()
                    if place_id in p.connects and not p.danger]
        if not options:
            return None
        from engine import pulse
        return pulse.town_of(self.world, min(options)[1])

    # ---------- carrying ----------

    def pack_slots(self) -> int:
        from scenes.inventory_actions import R
        extra = self.mech("light_pack") + (self.mech("pack_beast") if self.companion_here() else 0)
        return R["pack_slots"] + round(extra)

    # ---------- travel ----------

    def travel_minutes(self, route: list[str], walk: int) -> int:
        from engine import weather
        if self.owns("pilgrims_pace"):
            on_roads = sum(self.edge_minutes(a, b) for a, b in zip(route, route[1:]) if self.world.road_between(a, b))
            walk -= round(on_roads * self.mech("pilgrims_pace") / 100)
        stormy = weather.condition(self.store.meta.seed, self.minutes)["id"] in ("rain", "storm")
        if stormy and not (self.owns("weather_wise") or self.owns("blood_warm")):
            walk = round(walk * (1 + TRAVEL["bad_weather_slow"] / 100))
        if any(self.world.places[p].biome == "arctic" for p in route[1:]) and not self.owns("blood_warm"):
            walk = round(walk * (1 + TRAVEL["arctic_slow"] / 100))
        return max(1, walk)

    def edge_minutes(self, a: str, b: str) -> int:
        return self.world.places[a].connects.get(b) or self.world.places[b].connects.get(a) or 0

    def mount_info(self) -> dict | None:
        """The mount the player rides, if any (see data/rules/events.yaml, grand.mounts)."""
        return next((m for m in self.player.mounts if m["id"] == self.player.mount), None)

    def travel_fatigue(self, walk: int, factor: float = 1.0) -> None:
        if self.owns("long_road_walker") or walk < 60:
            return
        c = self.player.character
        cost = min(TRAVEL["fatigue_max"], TRAVEL["fatigue_per_hour"] * walk / 60) * factor
        mount = self.mount_info()
        if mount:
            cost *= 1 - mount["stamina"]
        c.stamina = max(0, pools.current(c, "stamina") - pools.maximum(c, "stamina") * cost / 100)

    def danger_multiplier(self, place_id: str, visited_before: bool) -> float:
        mult = 1.0
        if visited_before and self.owns("old_haunts"):
            mult *= 1 - self.mech("old_haunts") / 100
        if self.companion_here() and self.owns("pack_instinct"):
            mult *= 1 - self.mech("pack_instinct") / 100
        return mult

    # ---------- money ----------

    def contract_multiplier(self, q: dict) -> float:
        m = 1.0
        if q["kind"] in ("delve", "dungeon_boss"):
            m += self.mech("delvers_wage") / 100
        if q["kind"] == "deliver" and q["guild"]:
            m += self.mech("road_warden") / 100
        if not q["guild"]:
            m += self.mech("keeper_of_oaths") / 100
        creature = q.get("creature")
        if not creature and q.get("dungeon"):
            d = next((x for x in self.store.load_dungeons() if x["id"] == q["dungeon"]), None)
            creature = d["floors"][-1]["chambers"][-1]["creature"] if d else None
        if creature and creature in self.world.bestiary and \
                self.world.bestiary[creature].category in ("undead", "fiend") and q["kind"] != "delve":
            m += self.mech("righteous_hunt") / 100
        return m

    def sell_multiplier(self, item) -> float:
        m = 1.0
        base = item.base or ""
        if not item.good and base != "raw_material":
            from engine import items
            slot = items.CATALOG[base].slot if base in items.CATALOG else ""
            if slot in ("neck", "ring"):
                m += self.mech("fence_friend") / 100
            if item.source == "your own work":
                m += self.mech("signature_work") / 100
        if base == "raw_material":
            m += self.mech("material_eye") / 100
        if item.good in ("healing_draught", "mana_tonic"):
            m += self.mech("apothecary") / 100
        return m

    def stock_multiplier(self, npc, item) -> float:
        from engine import items
        m = 1.0
        slot = items.CATALOG[item.base].slot if item.base in items.CATALOG else ""
        if slot in ("main_hand", "off_hand") and npc.role in ("smith", "quartermaster"):
            m -= self.mech("weapon_wise") / 100
        if npc.role == "quartermaster":
            m -= self.mech("quartermasters_friend") / 100
        return max(0.1, m)

    def salvage(self, item) -> None:
        """Salvager: gear sold or dropped gives back one unit of its material."""
        if not self.owns("salvager") or item.good or item.base == "raw_material" or not item.material:
            return
        from engine import items
        self.to_pack(items.make_raw(item.material))
        console.note(f"Salvaged: 1 {items.MATERIALS[item.material].name}.")

    def known_work_sold(self, item) -> None:
        if self.owns("known_craftsman") and item.source == "your own work":
            from engine import pulse
            self.reputation_add(pulse.town_of(self.world, self.player.location), 1)

    # ---------- sleeping ----------

    def after_sleep(self) -> None:
        """Things that come to you in the night."""
        c = self.player.character
        day = clock.day(self.minutes)
        if self.owns("patrons_gift") and day - c.patron_gift_day >= 7:
            from engine import loot
            rng = random.Random()
            item = loot.make_drop(max(1, c.level), rng.choice(["uncommon", "uncommon", "rare"]), rng, loot.keeps_companions(c))
            c.patron_gift_day = day
            self.to_pack(item)
            console.note(f"Beside you when you wake: {item.name}. You don't remember it being there.")
        if self.owns("patron_dreams"):
            st = self.store.load_world_state()
            big = next((t for t in st.get("threads", []) if t["id"] == st.get("campaign")), None)
            if big:
                stage = big["stages"][big["stage"]]["description"]
                self.narrate(f"In the night, the player's patron shows them a dream - a glimpse of something vast "
                             f"unfolding far away: {stage} Tell it as a fragment of dream, vivid but unclear, "
                             f"without naming places outright.")
