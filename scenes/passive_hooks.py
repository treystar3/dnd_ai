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
        c = self.player.character
        return any(m.active for m in c.companions) or bool(c.bound_summon and not c.bound_broken)   # a companion, or the Bound summon

    # ---------- checks ----------

    def check_bonuses(self, check: str, npc=None, talking: bool = False, text: str = "") -> list[tuple[str, float]]:
        out, night = [], clock.is_dark(self.minutes)
        words = text.lower()

        def add(mid, label=None, when=True, sign=1):
            if when and self.owns(mid):
                out.append((label or mid.replace("_", " "), sign * self.mech(mid)))
        from engine import world_perks
        who, lent = world_perks.best_hands(self.player.character, check, self.player.party)
        if lent > 0:
            out.append((f"borrowed hands ({who})", lent))
        shadow = self.fld.get("shadow")
        if check == "stealth" and shadow and shadow["until"] > self.minutes:
            from engine.field import F as FIELD, tier_value
            out.append(("shadowing", tier_value(FIELD["shadow"]["stealth_bonus"], shadow["tier"])))
        if check == "stealth" and hasattr(self, "traceless") and self.traceless():
            from engine.field import F as FIELD
            out.append(("passing without trace", FIELD["pass_without_trace"]["stealth_bonus"]))
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
            from engine import world_perks
            worn = [items.weight(i) for i in self.player.character.equipment.values()
                    if not items.base_of(i).is_weapon and not world_perks.fitted(self.player.character, i)]
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

    def reputation_add(self, town: str, amount: int, spread: bool = True) -> None:
        if not town or self.world.places[town].danger:
            return
        if amount < 0 and self.owns("nobody"):
            return                                       # Nobody: infamy never sticks to a face no one can place
        self.player.reputation[town] = max(-100, min(100, self.player.reputation.get(town, 0) + amount))
        if spread and amount and self.owns("famous") and not self.owns("nobody"):
            for other in self.neighbor_towns(town):     # Famous: every town a road connects hears it at once, in full
                self.reputation_add(other, amount, spread=False)

    def sees_far(self) -> bool:
        """Hostiles are always spotted at a distance: Danger Sense, or a spirit walking ahead (Spirit Guide)."""
        return self.has("danger_sense") is not None or (self.owns("spirit_guide") and self.companion_here())

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
        if self.owns("mercy_remembered") and not self.owns("nobody"):
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
        sky = weather.condition(self.store.meta.seed, self.minutes)["id"]
        stormy = sky in ("rain", "storm")
        if stormy and not (self.owns("weather_wise") or self.owns("blood_warm") or (sky == "storm" and self.owns("storm_chosen"))):
            walk = round(walk * (1 + TRAVEL["bad_weather_slow"] / 100))
        if any(self.world.places[p].biome == "arctic" for p in route[1:]) and not self.owns("blood_warm"):
            walk = round(walk * (1 + TRAVEL["arctic_slow"] / 100))
        if self.owns("well_trodden"):
            from engine import world_perks
            total = sum(self.edge_minutes(a, b) for a, b in zip(route, route[1:])) or 1
            known = sum(self.edge_minutes(a, b) for a, b in zip(route, route[1:]) if self.walked_before(a, b))
            if known:
                walk = round(walk * (1 - (1 - world_perks.P["well_trodden"]["share"]) * known / total))
        return max(1, walk)

    def walked_before(self, a: str, b: str) -> bool:
        """Well-Trodden: a way is known when the player has been at both ends of it before this trip."""
        seen = self.player.visited
        return a in seen and b in seen

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
        console.ledger(f"Salvaged: 1 {items.MATERIALS[item.material].name}.")

    def known_work_sold(self, item) -> None:
        if self.owns("known_craftsman") and item.source == "your own work":
            from engine import pulse
            self.reputation_add(pulse.town_of(self.world, self.player.location), 1)

    # ---------- sleeping ----------

    def after_sleep(self) -> None:
        """Things that come to you in the night."""
        c = self.player.character
        day = clock.day(self.minutes)
        if c.gift:
            console.note(f"The {c.gift.get('family', 'beast').replace('_', ' ')}'s gift leaves you in your sleep.")
            c.gift = {}
        if self.owns("visions"):
            self.vision()
        if self.owns("reverse_engineer"):
            self.study_overnight()
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

    # ---------- the world's news, as the perks hear it ----------

    def live_threads(self, exclude_here: bool = False) -> list[dict]:
        """The world's active situations (engine/pulse.py threads), each with the name of the place it unfolds in."""
        from engine import pulse
        st = self.store.load_world_state() or {}
        here = pulse.town_of(self.world, self.player.location)
        out = []
        for t in st.get("threads", []):
            if t.get("status") != "active" or t["place"] not in self.world.places:
                continue
            town = pulse.town_of(self.world, t["place"])
            if exclude_here and town == here:
                continue
            out.append({"title": t["title"], "place": t["place"], "town": town, "place_name": self.world.places[t["place"]].name,
                        "now": t["stages"][t["stage"]]["description"]})
        return out

    def vision(self) -> None:
        """Visions: sleep shows one situation unfolding somewhere else, and names the place."""
        far = self.live_threads(exclude_here=True)
        if not far:
            return
        t = random.Random(f"{self.store.meta.seed}:vision:{clock.day(self.minutes)}").choice(far)
        console.note(f"A vision in your sleep: something is unfolding at {t['place_name']}.")
        self.narrate(f"In sleep the player sees, clearly, something happening far away at {t['place_name']}: {t['now']} "
                     f"Tell it as a vision - vivid, certain of the place, uncertain of the meaning. Name the place.")

    def tavern_ear(self, npc) -> None:
        """Tavern Ear: a drink at an inn, and the town talks - its troubles, and who is hiring."""
        from engine import pulse
        if not self.owns("tavern_ear") or getattr(npc, "role", "") not in ("innkeeper", "server", "cook"):
            return
        here = pulse.town_of(self.world, self.player.location)
        troubles = [t["now"] for t in self.live_threads() if t["town"] == here]
        hiring = []
        try:
            for q in self.ensure_board():
                hiring.append(q.get("title") or q.get("kind", "work"))
        except Exception:
            pass
        asks = [n.name for n in self.present if getattr(n, "request", None)]
        if not (troubles or hiring or asks):
            console.note("The talk at the bar is only weather and old grudges tonight.")
            return
        lines = []
        if troubles:
            lines.append("the town's troubles: " + " ".join(troubles[:3]))
        if hiring:
            lines.append("who is hiring: the guild board has " + ", ".join(hiring[:4]))
        if asks:
            lines.append("people with something to ask: " + ", ".join(asks[:4]))
        console.note("Over the drink, the room talks (Tavern Ear): " + "; ".join(lines) + ".")
        self.narrate("Over a drink the player picks up the talk of the room - " + "; ".join(lines) + ". Give it as overheard "
                     "scraps from different voices, true to these facts.")

    def troubadour(self, degree: str) -> None:
        """Troubadour: a performance is news from everywhere - and the towns sung about remember the singer."""
        if not self.owns("troubadour"):
            return
        from engine import world_perks
        threads = self.live_threads()
        if not threads:
            console.note("Your songs are all old ones tonight - the realm is quiet.")
            return
        sung = threads[:4]
        towns = []
        for t in sung:
            if t["town"] not in towns:
                towns.append(t["town"])
        if degree in ("strong success", "success"):
            for town in towns:
                self.reputation_add(town, world_perks.P["troubadour"]["standing"])
        console.note("What the songs carry (Troubadour): " + "; ".join(f"at {t['place_name']}, {t['now']}" for t in sung))
        self.narrate("Between verses the player weaves in the news of the realm, true in every particular: "
                     + "; ".join(f"at {t['place_name']}: {t['now']}" for t in sung) + ". The room hears it as song.")

    def campfire_cook(self, made: dict[str, int]) -> None:
        """Campfire Cook: a meal cooked at camp feeds the party, and every companion who shares it trusts you a little more."""
        from engine import inventory as inv, needs, party as party_rules
        from engine import world_perks
        if not self.owns("campfire_cook") or not self.place.danger:
            return
        if not any(inv.GOODS[g].kind == "food" for g in made):
            return
        R = world_perks.P["campfire_cook"]
        c = self.player.character
        needs.eat(c, R["feeds"])
        fed = [m for m in self.player.party if m.get("active", True) and not m.get("fallen")]
        for m in fed:
            m["bond"] = m.get("bond", 0) + R["trust"]
            party_rules.set_mood(m, "warmed by a hot meal", self.minutes)
        who = ", ".join(m["name"].split()[0] for m in fed)
        console.note("Everyone eats" + (f" - {who} think{'s' if len(fed) == 1 else ''} a little better of you for it (Campfire Cook)." if fed else " (Campfire Cook)."))

    def pious_hospitality(self) -> None:
        """Pious Path: the temple feeds you and yours, and asks nothing."""
        from engine import needs, party as party_rules, world_perks
        c = self.player.character
        needs.eat(c, world_perks.P["pious_path"]["feeds"])
        for m in self.player.party:
            if m.get("active", True) and not m.get("fallen"):
                party_rules.set_mood(m, "fed and rested under a temple roof", self.minutes)
        console.note("The temple gives bread and a bed to you and yours, and asks nothing (Pious Path).")

    def study_overnight(self) -> None:
        """Reverse Engineer: a night spent with the finest piece of gear you carry that you could learn from. What you craft of that
        kind afterwards comes out at least as fine as it was."""
        from engine import crafting, items
        c = self.player.character
        order = crafting.RARITY_ORDER
        best = None
        for it in list(c.equipment.values()) + list(c.inventory):
            b = items.CATALOG.get(it.base)
            if b is None or it.good or getattr(b, "family", None) not in crafting.RULES["stations"]:
                continue
            known = c.studied.get(it.base)
            if known is not None and order.index(known) >= order.index(it.rarity if it.rarity in order else "common"):
                continue
            if it.rarity not in order:
                continue
            if best is None or order.index(it.rarity) > order.index(best.rarity):
                best = it
        if best is None:
            return
        c.studied[best.base] = best.rarity
        if best.base not in c.recipes_made:
            c.recipes_made.append(best.base)
        console.note(f"You spent the night taking {items.display_name(best)} apart in your head. You could make its like now - "
                     f"{best.rarity} work at the least (Reverse Engineer).")
