"""The free-action loop: the player lives in the world.

Each input:
  1. interpret - the LLM reads it into an ActionIntent
  2. engine    - this class decides what actually happens and updates saved state
  3. voice     - the narrator describes places; NPCs speak for themselves

The engine fully understands move, look and talk. Anything else is narrated as an
attempt with no consequences, until the systems that can resolve it exist.
"""

import re
import config
import json
import random

from character.kit import give_starting_kit
from core.models import Companion
from engine import faith as faith_mod
from scenes.orenna_actions import OrennaActions
from engine import encounters
from engine.combat import RULES as COMBAT_RULES
from scenes import combat_prompts as cp
from scenes.combat_scene import CombatScene
from scenes.voice import fresh
from scenes.inventory_actions import InventoryActions
from scenes.shop_actions import ShopActions
from scenes.gear_actions import GearActions
from scenes.check_actions import CheckActions
from scenes.work_actions import WorkActions
from scenes.guild_actions import GuildActions
from scenes.training_actions import TrainingActions
from scenes.dungeon_actions import DungeonActions
from scenes.road_actions import RoadActions
from scenes.explore_actions import ExploreActions
from scenes.property_actions import PropertyActions
from scenes.mount_actions import MountActions
from scenes.arc_actions import ArcActions
from scenes.camp_actions import CampActions
from scenes.party_actions import PartyActions
from scenes.passive_hooks import PassiveHooks
from scenes.field_actions import FieldActions
from scenes.audit_actions import AuditActions
from scenes.standing_actions import StandingActions
from scenes.law_actions import LawActions
from scenes import markup
from engine import mapview, needs, pulse, pulselog, quests
from engine import inventory as inv
from engine import crafting
from engine import clock, equipment, items, leveling, money, pools, voice_rules, weather
from llm.contracts import ActionIntent, ActionPlan, DialogueFrame, Narration
from llm.gateway import LLMError, generate
from npc.life import converse, has_parting, manner, populate_place, promote
from npc.models import Memory, NPC
from npc.traits import TraitCatalog
from scenes import world_prompts as wp
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import World

QUIT_WORDS = {"quit", "exit", "/quit", "/exit"}
TIME_COST = {"look": clock.LOOK_MINUTES, "talk": clock.TALK_MINUTES, "other": clock.OTHER_MINUTES,
             "leave_conversation": 0, "steal": 5}
SEARCH = encounters.E


class WorldScene(InventoryActions, ShopActions, GearActions, CheckActions, WorkActions, GuildActions, TrainingActions, DungeonActions,
                 RoadActions, ExploreActions, PropertyActions, MountActions, ArcActions, CampActions, PartyActions, PassiveHooks, FieldActions, AuditActions, LawActions, StandingActions, OrennaActions):
    def __init__(self, store: CampaignStore, world: World, catalog: TraitCatalog, player: PlayerState):
        self.store = store
        self.world = world
        self.catalog = catalog
        self.player = player
        self.residents: list[NPC] = []
        self.present: list[NPC] = []
        self.partner: NPC | None = None
        self.last_spoken: str | None = None
        self.convo: list[tuple[str, str]] = []
        self.restart = False          # #newgame: the run loop ends and main.py starts character creation again
        self.recent_narration: list[str] = []
        self.last_text = ""
        self.buffering = False        # several actions in one message: narrate them together
        self.pending: list[str] = []
        self.halted = False           # an action failed or the situation changed: stop the chain
        self.combat: CombatScene | None = None
        self.resume_pending = None
        self.wildlife = None
        self.recently_fled = False
        self.rng = random.Random()
        pools.fill_missing(self.player.character)

    @property
    def place(self):
        return self.world.places[self.player.location]

    @property
    def minutes(self) -> int:
        return self.store.meta.minutes

    def time_label(self) -> str:
        light = " (dark)" if clock.is_dark(self.minutes) else ""
        _, sky = weather.describe(self.store.meta.seed, self.minutes)
        return f"day {clock.day(self.minutes)}, {clock.period(self.minutes)}{light}, weather: {sky.lower()}"

    def place_lines(self) -> tuple[str, str]:
        here = self.place
        parent = self.world.places.get(here.parent) if here.parent else None
        outer = parent.name if parent else self.world.regions[here.region].name
        return here.name, f"{outer} — {here.name}"

    def conditions(self) -> set[str]:
        """Triggers that are true because of where and when the player is."""
        from core.rules import TRIGGERS
        found = {"at_night" if clock.is_dark(self.minutes) else "in_daylight"}
        if weather.condition(self.store.meta.seed, self.minutes)["id"] in ("rain", "storm"):
            found.add("in_bad_weather")
        parent = self.world.places.get(self.place.parent) if self.place.parent else None
        biome = self.place.biome or (parent.biome if parent else None)
        found.add("in_settlements" if biome == "urban" or (not biome and not self.place.danger) else "in_wilderness")
        if biome and f"in_{biome}" in TRIGGERS:
            found.add(f"in_{biome}")
        if self.player.character.companions:
            found.add("with_companion_present")
        return found

    def advance_quiet(self, minutes: int) -> None:
        self.advance(minutes)

    def goddess_knowledge(self) -> dict:
        return json.loads((__import__("core.paths", fromlist=["BUNDLE"]).BUNDLE / "data" / "goddess_knowledge.json").read_text(encoding="utf-8"))

    def gear_line(self) -> str:
        c = self.player.character
        worn = [i.name for s, i in c.equipment.items() if s != "main_hand"]
        held = c.equipment.get("main_hand")
        parts = [f"wearing {', '.join(worn)}" if worn else "no armor, only plain clothes"]
        parts.append(f"carrying {held.name}" if held else "empty-handed")
        return "; ".join(parts)

    def remember_narration(self, text: str, shown: dict | None = None) -> None:
        """Keep what the model should remember, and what the player saw (as pieces, so a reload draws it the same way)."""
        if text.strip():
            self.recent_narration = (self.recent_narration + [text])[-6:]
            self.store.save_story(self.recent_narration, shown or {"type": "narration", "text": text})

    def narrate_with(self, system: str, event: str) -> None:
        self.flush(self.last_text)
        result = fresh("narrate", system,
                       wp.narration_request(self.time_label(), self.place, self.people_view(), event, self.last_text,
                                            self.recent_narration, self.gear_line(),
                                            self.store.load_place(self.player.location).marks),
                       Narration, self.recent_narration)
        console.narrate(result.text)
        self.remember_narration(result.text)

    def has(self, mechanic: str) -> float | None:
        return pools.mechanic(self.player.character, mechanic)

    def deterred(self, creature, high: int | None = None) -> bool:
        """Outlaws leave anyone who far outlevels the land alone: they weigh the odds and let you pass."""
        if creature.category != "hostile people":
            return False
        if high is None:
            high = self.place.danger[1] if self.place.danger else None
        if not high:
            return False
        from engine import roads
        d = roads.R["bandits"]["deterrence"]
        return self.player.character.level >= max(high * d["ratio"], high + d["margin"])

    def temperament(self, creature, high: int | None = None) -> str:
        if self.has("beast_friend") is not None and creature.category in ("beast", "swarm"):
            return "passive"
        if self.deterred(creature, high):
            return "passive"
        return creature.temperament

    def maybe_encounter(self, chance: float, how: str, seek: str = "") -> bool:
        if self.combat or self.recently_fled:
            self.recently_fled = False
            return False
        if self.shadow_active() and not self.dungeon_here() and self.place.danger and not self.player.delve:
            self.use_shadow()
            console.note("Something stirs nearby, but you are not noticed and it passes you by.")
            return False
        chance = min(0.95, chance * pulse.danger_factor(self.store, self.player.location, self.minutes)
                     * self.danger_multiplier(self.player.location, not getattr(self, "first_arrival", True)))
        hit = encounters.roll(self.store, self.world, self.player.location, chance, self.rng, seek, contracts=self.player.quests)
        if not hit:
            return False
        creature, enemies = hit
        console.debug(f"encounter: {len(enemies)} x {creature.id} (levels {[e.level for e in enemies]})")
        if self.beasts_calm(creature):
            console.note(f"A {creature.name.lower()} stirs nearby, but the animals have spoken for you and it passes by.")
            return False
        if self.temperament(creature) == "passive":
            self.wildlife = (creature, enemies)
            names = ", ".join(e.name for e in enemies)
            self.narrate_with(cp.START_SYSTEM, f"{how} the player spots {names}, keeping its distance. It is not hostile.")
            return False
        if creature.temperament == "territorial" or self.has("danger_sense") is not None:
            for e in enemies:
                e.band = "far"
        self.wildlife = None
        self.combat = CombatScene.begin(self, creature, enemies, how)
        return True

    def safe_to_rest(self) -> bool:
        return bool(self.camp_active() or not self.place.danger)

    def advance(self, minutes: int, exert: bool = False, wait: str = "") -> None:
        """Time passes. exert: travelling, working or fighting. wait: 'rest' or 'sleep' - health comes back, and a sleep clears fatigue."""
        before = clock.period(self.minutes)
        self.store.meta.minutes += minutes
        c = self.player.character
        was = needs.marks(c)
        needs.tick(c, minutes, exertion=exert, sleeping=wait == "sleep", resting=wait == "rest")
        for line in needs.voice(was, needs.marks(c)):
            console.note(line)
        rest = needs.N["rest_heal_per_hour"]["safe" if self.safe_to_rest() else "rough"] if wait else 0.0
        pools.recover(c, minutes, conditions=self.conditions(), rest=rest)
        self.store.meta.day = clock.day(self.minutes)
        self.refresh_present()
        if self.partner and self.partner not in self.present:
            console.note(f"{self.partner.label()} heads off for the day.")
            self.end_conversation()
        if clock.period(self.minutes) != before:
            console.debug(f"time of day is now {clock.period(self.minutes)}")

    def refresh_present(self) -> None:
        self.present = [n for n in self.residents
                        if clock.in_hours(self.minutes, self.world.roles[n.role].hours) and n.away_until <= self.minutes]
        if getattr(self, "partner", None):          # residents are reloaded from disk each turn: keep pointing at the same person's fresh copy
            fresh_copy = next((n for n in self.present if n.id == self.partner.id), None)
            if fresh_copy:
                self.partner = fresh_copy

    def run_pulse(self) -> None:
        """Let the world move on, then see who is still here."""
        pulse.catch_up(self.store, self.world, self.catalog, self.minutes)
        from engine import events
        events.apply_player_events(self)
        self.arc_tick()
        here = self.store.load_place(self.player.location)
        if here.populated:
            self.residents = [n for n in (self.store.load_npc(i) for i in here.residents) if not n.gone]
            self.refresh_present()

    def pulse_data(self) -> dict:
        """The debug pane: the pulse log of this session, newest first, and what is live now."""
        st = self.store.load_world_state() or {}
        last = st.get("last", 0)
        rows = []
        for r in reversed(pulselog.LOG):
            when = lambda t: f"day {clock.day(t)} {clock.clock_time(t)}"
            if r["kind"] == "quiet":
                text = f"{r['count']} quiet pulse{'s' if r['count'] != 1 else ''}, nothing happened"
                rows.append({"when": when(r["t"]) + ("" if r["count"] == 1 else f" - {when(r['to'])}"), "kind": "quiet", "text": text, "effects": []})
            else:
                rows.append({"when": when(r["t"]), "kind": r["kind"], "text": r["text"], "effects": list(r["effects"])})
        threads = [f"[{t['tier']}] {t['title']} - stage {t['stage'] + 1}/{len(t['stages'])} at {self.where_name(t['place'])}, ends day {clock.day(t['times'][-1])}"
                   for t in st.get("threads", []) if t["status"] == "active"]
        live = [f"{e['kind']} {e.get('value', '')} at {self.where_name(e['place'])} until day {clock.day(e['until'])}"
                for e in st.get("effects", []) if e["until"] > self.minutes]
        return {"rows": rows, "now": f"day {clock.day(self.minutes)} {clock.clock_time(self.minutes)}",
                "last": f"day {clock.day(last)} {clock.clock_time(last)}" if last else "never",
                "next_in": max(0, last + pulse.INTERVAL - self.minutes) if last else 0, "interval": pulse.INTERVAL,
                "threads": threads, "effects": live}

    def show_pulse(self) -> None:
        if not config.DEBUG:
            console.note("#pulse is a debug pane (run the game with --debug).")
            return
        data = self.pulse_data()
        if console.panel("pulse", data):
            return
        console.note(f"PULSE - now {data['now']}, last {data['last']}, next in {data['next_in']} min")
        for r in data["rows"][:25]:
            console.note(f"  {r['when']}  {r['kind']}: {r['text']}")
            for e in r["effects"]:
                console.note(f"      {e['result']}: {e['text']}")

    def show_world_state(self) -> None:
        st = self.store.load_world_state()
        console.note(f"WORLD - {clock.season(self.minutes)}, day {clock.day(self.minutes)}. Last pulse: day "
                     f"{clock.day(st.get('last', 0))}. Campaign event: "
                     f"{next((t['title'] for t in st.get('threads', []) if t['id'] == st.get('campaign')), 'none')}")
        for t in [x for x in st.get("threads", []) if x["status"] == "active"]:
            console.note(f"  [{t['tier']}] {t['title']} @ {t['place']} - stage {t['stage'] + 1}/{len(t['stages'])}, "
                         f"ends day {clock.day(t['times'][-1])}")
        movers = [n for n in (self.store.load_npc(i) for i in self.store.list_npcs()) if n.motive and not n.gone]
        for n in movers:
            console.note(f"  motive: {n.name} - {n.motive}" + (f" (mood: {n.mood})" if n.mood else ""))
        for e in [x for x in st.get("effects", []) if x["until"] > self.minutes]:
            console.note(f"  effect: {e['kind']} {e.get('value', '')} @ {e['place']} until day {clock.day(e['until'])}")
        for h in st.get("history", [])[-5:]:
            console.note(f"  history: day {clock.day(h['minute'])} - {h['text']}")
        console.note(f"  news items: {len(st.get('news', []))} | reputation: {self.player.reputation or 'none yet'}")

    def reputation_change(self, key: str, place_id: str | None = None) -> None:
        town = pulse.town_of(self.world, place_id or self.player.location)
        if self.world.places[town].danger:
            return
        amount = pulse.P["reputation"][key]
        if key == "threat" and self.has("dread_name") is not None:
            return
        if key == "gift" and self.has("almsgiver") is not None:
            amount *= 3
        if amount > 0 and self.has("town_defender"):
            amount = round(amount * (1 + self.has("town_defender") / 100))
        self.player.reputation[town] = max(-100, min(100, self.player.reputation.get(town, 0) + amount))

    def reputation_words(self, town: str) -> str:
        r = self.player.reputation.get(town, 0)
        return ("unknown - just a stranger" if -5 < r < 5 else "well liked" if r >= 30 else "liked" if r >= 10
                else "known, and thought decent" if r > 0 else "distrusted" if r <= -30 else "viewed warily")

    def enter(self, place_id: str) -> None:
        self.wildlife = None
        self.leave_road(place_id)
        self.revisit = self.store.load_place(place_id).populated
        self.player.location = place_id
        self.note_town(place_id)
        self.standing_arrive()
        self.first_arrival = place_id not in self.player.visited
        if self.first_arrival:
            self.player.visited.append(place_id)
            self.weight_hint = "major" if self.world.places[place_id].type == "city" else "rich"
        self.residents = populate_place(self.store, self.world, place_id, self.catalog)
        self.refresh_present()
        self.home_arrival()
        self.arc_enter(place_id)
        self.bring_prisoners(place_id)
        self.party_notice()

    def brevity(self) -> str:
        if getattr(self, "revisit", False):
            return (" The player has been here before: keep it to two or three sentences, "
                    "and mention at most two of the people present.")
        return ""

    def run(self) -> None:
        self.ensure_discoveries()
        self.ensure_homes()
        self.ensure_road_place()
        self.ensure_dungeons()
        self.ensure_field_uses()
        self.run_pulse()
        first_time = self.store.meta.turn == 0
        self.enter(self.player.location)
        if first_time:
            self.weight_hint = "major"
        kit_text = ""
        c = self.player.character
        if not c.kit_given:
            kit_text = give_starting_kit(c, f"{c.custom_class} ({c.archetype.value}): {c.class_summary}",
                                         c.uses_companions, self.world)
            self.store.save_player(self.player)
            console.debug(f"starting kit: {kit_text}")
        if not self.present and self.residents:
            console.debug("residents are home at this hour")
        if first_time:
            self.narrate(
                "The player has just woken here, lying on the ground, returned from death. "
                f"They remember the Threshold only faintly. {kit_text} Their first breath tears in. "
                "Open with that single breath, described once in one sentence (mention the gasp only once in the whole passage), "
                "then describe what they see."
            )
        else:
            saved, shown = self.store.load_story()
            if shown:
                self.recent_narration = saved[-6:]
                if shown.get("type") == "dialogue":
                    console.dialogue(shown.get("before", ""), shown.get("speaker", ""), shown.get("speech", ""), shown.get("after", ""))
                elif shown.get("type") == "says":
                    console.npc_says(shown.get("speaker", ""), shown.get("speech", ""), shown.get("gesture", ""))
                else:
                    console.narrate(shown.get("text", ""))
            else:
                self.narrate("The player is here, picking up where they left off. Describe the scene in two or three "
                             "sentences, mentioning at most two of the people present.")
            if kit_text:
                c = self.player.character
                held = [i.name for i in c.equipment.values()] + [f"{m.name} ({m.description})" for m in c.companions]
                console.note(f"Checking your belongings, you find: {', '.join(held + [money.fmt(c.coins)])}.")
        self.show_exits()
        saved_fight = self.store.load_combat()
        if saved_fight:
            self.combat = CombatScene.resume(self, saved_fight)
            console.note("You are still in the middle of a fight!")
            self.combat.show()
        self.show_header()

        while True:
            text = console.ask(main=True)
            if not text:
                continue
            if text.lower() in QUIT_WORDS:
                self.store.save_player(self.player)
                console.note("Saved. Run main.py again to continue.")
                return
            if text.startswith("#"):
                with console.scope(text):
                    self.command(text)
                if self.restart:
                    self.store.save_player(self.player)
                    return
                continue
            try:
                self.handle(text)
                self.orenna_tick()
                self.collapse_check()
            except LLMError as e:
                console.note("The world seems to hesitate - the model couldn't produce a usable answer. "
                             "Nothing has been lost; try again, perhaps worded differently.")
                console.debug(str(e))
            self.store.save_player(self.player)
            self.show_header()

    def collapse_check(self) -> None:
        """Past the limit of fatigue you fall asleep where you stand: eight hours, with the dangers of the place."""
        c = self.player.character
        if not needs.collapsing(c) or self.combat:
            return
        console.note("You can't stay on your feet. Your legs give out and you sleep where you fall.")
        self.on_wait(ActionIntent(kind="wait", wait_minutes=needs.N["collapse_hours"] * 60), "I collapse from exhaustion")
        if needs.collapsing(c):                       # nowhere safe to fall: you wake at once, barely upright
            c.fatigue = needs.N["collapse_unslept"]

    def enchant_command(self, args: str) -> None:
        from engine import enchanting
        c = self.player.character
        enchanting.DISCOUNT["percent"] = self.has("arcane_appraiser") or 0
        enchanter = next((n for n in self.present if n.role == "enchanter"), None)
        if not enchanter and not config.DEBUG:
            console.note("There's no enchanter here. You'll need to find one - perhaps somewhere magic is welcome.")
            return
        gear = list(c.equipment.values()) + [i for i in c.inventory if items.base_of(i).slot != "none"]
        if not args:
            console.note("Your gear and its enchantment slots:")
            for n, it in enumerate(gear, 1):
                used, total = len(it.enchantments), enchanting.slots(it)
                console.note(f"  {n}. {items.display_name(it)} - {used}/{total} enchantments")
            console.note("Pick one: #enchant <number>")
            return
        parts = args.split()
        if not parts[0].isdigit() or not 1 <= int(parts[0]) <= len(gear):
            console.note("Choose an item by number. Type #enchant to see the list.")
            return
        item = gear[int(parts[0]) - 1]
        options = enchanting.available(c, item)
        if len(parts) == 1:
            console.note(f"{items.display_name(item)}: {len(item.enchantments)}/{enchanting.slots(item)} enchantments, "
                         f"{enchanting.success_chance(item)}% chance of success.")
            for n, o in enumerate(options, 1):
                from engine import accessories
                fx = [items._describe_effect(e) for e in items.to_flat(
                    [items.Effect(modifies=e.modifies, trigger=e.trigger, magnitude=e.magnitude)
                                       for e in enchanting.usable_effects(c, item, o)], item.item_level)]
                if not accessories.is_accessory(item):
                    fx += [items.FLAG_TEXT[k].format(v=v) for k, v in o.flags.items()]
                fx = "; ".join(fx)
                need = f" + raw {items.MATERIALS[o.reagent].name}" if o.reagent else ""
                console.note(f"  {n:>2}. {o.name} ({o.suffix}) - {fx} · {money.fmt(enchanting.fee(item, o))}{need}")
            if not options:
                console.note("Nothing you can afford or have the materials for. Creature materials unlock more.")
            else:
                console.note(f"Enchant with: #enchant {parts[0]} <option number>")
            return
        if not parts[1].isdigit() or not 1 <= int(parts[1]) <= len(options):
            console.note("Choose an enchantment by number.")
            return
        option = options[int(parts[1]) - 1]
        problem = enchanting.check(c, item, option)
        if problem:
            console.note(problem)
            return
        target = items.display_name(item) if item.title else f"the {items.display_name(item)}"
        console.note(f"Bind {option.name} into {target} for {money.fmt(enchanting.fee(item, option))}"
                     f"{' and a raw ' + items.MATERIALS[option.reagent].name if option.reagent else ''}? "
                     f"{enchanting.success_chance(item)}% chance of success. (y/n)")
        if console.ask().lower() not in ("y", "yes"):
            console.note("Cancelled.")
            return
        ok, message = enchanting.enchant(c, item, option, self.rng)
        console.note(message)
        self.store.save_player(self.player)

    def equip_command(self, query: str) -> None:
        c = self.player.character
        if not query:
            console.note("Equip what? Use #inventory to see your items, then e.g. #equip 1 or #equip spear")
            return
        item = equipment.find(c, query, "inventory")
        if not item:
            console.note(f"You aren't carrying anything matching '{query}'.")
            return
        console.note(equipment.equip(c, item))
        self.store.save_player(self.player)

    def unequip_command(self, query: str) -> None:
        c = self.player.character
        slot = query.strip().lower().replace(" ", "_")
        if slot not in c.equipment:
            item = equipment.find(c, query, "equipped")
            slot = equipment.slot_of(c, item) if item else slot
        console.note(equipment.unequip(c, slot))
        self.store.save_player(self.player)

    def attribute_click(self, attr: str) -> None:
        """The Character pane's + button: one point into one attribute, then the pane is drawn again."""
        c = self.player.character
        spend = {attr: 1}
        error = None if attr in leveling.ATTRIBUTES else "That is not an attribute."
        error = error or leveling.check_allocation(c, spend)
        if error:
            console.note(error)
        else:
            leveling.allocate(c, spend)
            if self.combat:
                self.combat.refresh_player()
            self.store.save_player(self.player)
            self.show_header()
        with console.scope("#character"):
            self.command("#character")

    NOTE_TRUST_SHIFT = 15           # a note is rewritten after trust moves this far, or after two or more new memories
    NOTE_NEW_MEMORIES = 2

    def note_due(self, npc) -> bool:
        if not npc.name_known_to_player:
            return False
        if not npc.journal_note:
            return True
        return abs(npc.trust - npc.note_trust) >= self.NOTE_TRUST_SHIFT or len(npc.memories) - npc.note_mem >= self.NOTE_NEW_MEMORIES

    def journal_line(self, n, town: str) -> str:
        """One sentence about a person you know by name: their own note when they have written one, a plain line from what is known until then."""
        if n.journal_note:
            return n.journal_note
        role = n.role.replace("_", " ")
        first = (n.description or "").split(". ")[0].strip().rstrip(".")
        return f"{role.capitalize()} of {town or 'the road'}" + (f" - {first[0].lower() + first[1:]}." if len(first) > 12 else ".")

    def journal_data(self) -> dict:
        """People you know by name, by town (this town first, then the last one you stood in), what you have learned, what you have let go."""
        here = pulse.town_of(self.world, self.player.location)
        last = next((t for t in reversed(self.fld.get("towns", [])) if t != here), "")
        groups: dict[str, list] = {}
        for n in (self.store.load_npc(i) for i in self.store.list_npcs()):
            if not n.met_player or not n.name_known_to_player:
                continue
            town = pulse.town_of(self.world, n.location) if n.location in self.world.places else ""
            groups.setdefault(town, []).append(n)
        def rank(t):
            return (0 if t == here else 1 if t == last else 3 if not t else 2, self.where_name(t).lower())
        out = []
        for t in sorted(groups, key=rank):
            tag = "here" if t == here else "last visited" if t == last else ""
            people = []
            for n in sorted(groups[t], key=lambda x: x.name.lower()):
                people.append({"name": n.name, "role": n.role.replace("_", " "), "place": self.where_name(n.location),
                               "line": self.journal_line(n, self.where_name(t) if t else "")})
            out.append({"town": self.where_name(t) if t else "On the road", "tag": tag, "people": people})
        heard = [{"name": n.name, "by": n.heard_of["by"], "line": n.heard_of["line"]}
                 for n in sorted((self.store.load_npc(i) for i in self.store.list_npcs()), key=lambda x: x.name.lower())
                 if n.heard_of and not (n.met_player and n.name_known_to_player)]
        known = self.player.character.knowledge
        return {"groups": out, "heard": heard, "facts": [self.world.lore[f].text for f in known if f in self.world.lore],
                "history": list(self.player.character.item_history)}

    def show_journal(self) -> None:
        data = self.journal_data()
        if console.panel("journal", data):
            return
        people = [f"{x['name']} - {x['line']}" for g in data["groups"] for x in g["people"]]
        people += [f"{x['name']} (heard of) - {x['by']}: \"{x['line']}\"" for x in data["heard"]]
        console.show_journal(data["facts"], people, data["history"])

    def allocate(self, args: str) -> None:
        c = self.player.character
        if not args:
            sheet = "  ".join(f"{a[:3].upper()} {getattr(c.attributes, a)}" for a in leveling.ATTRIBUTES)
            console.note(f"{c.unspent_points} points to spend. Now: {sheet}")
            if c.primary_attributes:
                console.note(f"Main attributes for your class: {', '.join(c.primary_attributes)}")
            if c.unspent_points:
                console.note("Example: #allocate str 3 dex 2")
            return
        spend, error = leveling.parse_allocation(args)
        error = error or leveling.check_allocation(c, spend)
        if error:
            console.note(error)
            return
        changes = ", ".join(f"{a[:3].upper()} {getattr(c.attributes, a)} -> {getattr(c.attributes, a) + n}"
                            for a, n in spend.items())
        console.note(f"{changes}. This is permanent. Confirm? (y/n)")
        if console.ask().lower() not in ("y", "yes"):
            console.note("Cancelled.")
            return
        leveling.allocate(c, spend)
        if self.combat:
            self.combat.refresh_player()
        self.store.save_player(self.player)
        console.note(f"Done. {c.unspent_points} points left.")
        self.show_header()

    def show_header(self) -> None:
        c = self.player.character
        m = self.minutes
        when = f"{clock.ordinal(clock.day(m))} Day {clock.clock_time(m)} ({clock.period(m).capitalize()})"
        emoji, sky = weather.describe(self.store.meta.seed, m)
        place_line, spot_line = self.place_lines()
        vitals = {p: (pools.current(c, p), pools.maximum(c, p)) for p in pools.POOLS}
        console.status_block(when, f"{emoji} {sky}", place_line, spot_line, vitals,
                             c.level, c.unspent_points, c.coins, (c.xp, leveling.xp_to_next(c.level)))

    def handle(self, text: str) -> None:
        self.last_text = text
        if self.combat:
            self.combat.turn(text)
            self.store.meta.turn += 1
            if not self.combat and self.resume_pending:
                self.resume_road()
            return
        if self.party_turn(text):
            self.store.meta.turn += 1
            return
        if self.camp_turn(text):
            self.ensure_dungeons()
            self.run_pulse()
            self.store.meta.turn += 1
            return
        plan = self.interpret(text)
        raw_plan = [a.model_dump(exclude_defaults=True) for a in plan]
        if markup.has_markup(text):
            for a in plan:
                if a.speech:
                    a.speech = markup.scrub_speech(a.speech, text)
            plan = [a for a in plan if not (a.kind == "talk" and not a.speech)] or plan
        self.buffering, self.pending, self.halted = len(plan) > 1, [], False
        here_ids = {n.id for n in self.present}
        plan = [a for k, a in enumerate(plan)
                if not (a.kind == "move" and any(b.kind in ("talk", "give", "show", "buy", "sell", "commission")
                                                 and b.target in here_ids for b in plan[k + 1:]))] or plan
        if not self.rank and self.clerk_here():     # paying or asking to join the guild, said to the clerk, is joining - and only once
            asking = text.strip().lower().startswith(("how", "what", "where", "can ", "could ", "do ", "does ", "is ", "are ")) or "?" in text
            for a in plan:
                low = f"{text} {a.summary}".lower()
                about_guild = any(w in low for w in ("guild", "registry", "register", "registration", "membership"))
                if about_guild and a.kind in ("talk", "buy", "give", "other") and not asking \
                        and any(w in low for w in ("join", "fee", "pay", "sign", "enrol", "enroll", "register")):
                    a.kind, a.target, a.ware, a.item = "join_guild", "", "", ""
            seen_join = False
            kept = []
            for a in plan:
                if a.kind == "join_guild":
                    if seen_join:
                        continue
                    seen_join = True
                kept.append(a)
            plan = kept
        for a in plan:                              # "I offer the guard 5 silver to look the other way" is giving coin, whatever it was read as
            if a.kind in ("talk", "other") and a.target in here_ids and self.coin_amount(text) \
                    and any(w in f"{text} {a.summary}".lower() for w in self.BRIBE_WORDS):
                m = re.search(r"(?:\d+|[a-z]+)\s+(?:gold|silver|copper)(?:\s+(?:and\s+)?(?:\d+|[a-z]+)\s+(?:gold|silver|copper))*", text.lower())
                a.kind, a.item = "give", (m.group(0) if m else "coins")
        HARVEST_WORDS = ("harvest", "skin", "butcher", "gut", "carcass", "hide", "meat", "parts", "gather")
        plan = [a for k, a in enumerate(plan)       # skinning and harvesting is one action: a second "other" restating it is dropped
                if not (a.kind in ("other", "harvest") and k and any(b.kind == "harvest" for b in plan[:k])
                        and any(w in f"{a.summary} {a.item}".lower() for w in HARVEST_WORDS))] or plan
        plan = self.audit_plan(text, plan, raw_plan)
        if plan is None:                            # the audit could not make sense of it: nothing happens, no time passes, the player rewords
            self.buffering = False
            return
        for i, intent in enumerate(plan):
            if i and (self.combat or self.halted):
                console.debug(f"stopping after {i} of {len(plan)} actions")
                break
            console.debug(f"intent {i + 1}/{len(plan)}: {intent.model_dump(exclude_defaults=True)}")
            self.pending_check, self.pending_beats = "", []
            if not self.run_checks(intent, text):
                getattr(self, f"on_{intent.kind}")(intent, text)
                if intent.force and intent.kind != "attack":
                    self.after_force(intent, text)
                if self.pending_beats:
                    self.narrate(" ".join(self.pending_beats), text)
            if intent.mark.strip():
                self.add_mark(intent.mark.strip())
            if self.player.commissions:
                self.collect_commissions()
            if self.player.quests:
                self.expire_quests()
                self.turn_in()
            if intent.kind in TIME_COST:
                self.advance(TIME_COST[intent.kind])
        self.ensure_dungeons()
        self.run_pulse()
        self.flush(text)
        if self.buffering and self.exits_due and not self.combat:
            self.show_exits(force=True)
        self.buffering = False
        self.law_check()
        self.store.meta.turn += 1

    def flush(self, player_text: str = "") -> None:
        """Narrate everything held back so far, as one passage."""
        if not self.pending:
            return
        events, self.pending = self.pending, []
        if len(events) == 1:
            event = events[0]
        else:
            event = ("The player does several things in order. Narrate them as one flowing passage, in that order, "
                     "giving each its due but no more: " + " THEN: ".join(f"({n}) {e}" for n, e in enumerate(events, 1)))
        self._narrate_now(event, player_text)

    def add_mark(self, mark: str) -> None:
        state = self.store.load_place(self.player.location)
        if mark.lower() not in (m.lower() for m in state.marks):
            state.marks = (state.marks + [mark])[-12:]
            self.store.save_place(state)
            console.note(f"Remembered here: {mark}")

    def command(self, text: str) -> None:
        name = text[1:].strip().lower()
        if name in ("system", "sys", "stats", "character"):
            c = self.player.character
            vitals = [(p, round(pools.current(c, p)), pools.maximum(c, p)) for p in pools.POOLS]
            console.show_player_block(c, self.place.name,
                                      clock.header(self.minutes, self.place.name).rsplit(" · ", 1)[0], vitals)
        elif name in ("exits", "where", "places"):
            self.show_exits(asked=True)
        elif name == "map":
            self.show_map()
        elif name == "party":
            self.show_party()
        elif name.split()[0] in ("compname", "name"):
            self.rename_companion(text)
        elif name in ("journal", "j"):
            self.show_journal()
        elif name == "newgame":
            console.note("Start a new character? Your current game is not deleted: it is set aside as a backup in the saves folder. (y/n)")
            if console.ask().lower() in ("y", "yes"):
                self.restart = True
            else:
                console.note("Cancelled.")
        elif name.split()[0] == "attradd":
            self.attribute_click(name.split()[1] if len(name.split()) > 1 else "")
        elif name.split()[0] in ("allocate", "alloc", "assign"):
            self.allocate(name.split(maxsplit=1)[1] if " " in name else "")
        elif name.split()[0] in ("inventory", "inv", "i"):
            c = self.player.character
            console.show_inventory(c)
        elif name.split()[0] in ("equip", "wield", "wear"):
            self.equip_command(name.split(maxsplit=1)[1] if " " in name else "")
        elif name.split()[0] in ("unequip", "remove"):
            self.unequip_command(name.split(maxsplit=1)[1] if " " in name else "")
        elif name.split()[0] == "enchant":
            self.enchant_command(name.split(maxsplit=1)[1] if " " in name else "")
        elif name in ("board", "contracts"):
            if self.place.type == "guild" or self.rank:
                self.show_board()
            else:
                console.note("The contract board is at the guild house.")
        elif name == "standing":
            self.show_standing()
        elif name == "rumors":
            self.show_rumors()
        elif name.split()[0] == "correct":
            self.correct_rumor(name.split(maxsplit=1)[1] if " " in name else "")
        elif name == "pulse":
            self.show_pulse()
        elif name == "world":
            if not config.DEBUG:
                console.note("#world is a debug command (run with --debug).")
            else:
                self.show_world_state()
        elif name in ("dungeon", "map", "floors"):
            self.show_dungeon()
        elif name in ("quests", "quest", "jobs"):
            self.show_quests()
        elif name in ("arc", "story", "trail", "clues"):
            self.show_arc()
        elif name in ("home", "house", "property", "homes"):
            self.show_home()
        elif name.split()[0] in ("mount", "mounts", "ride", "stable", "stables"):
            self.mount_command(name.split(maxsplit=1)[1] if " " in name else "")
        elif name.split()[0] in ("shopbuy", "shopsell"):
            self.shop_click(text)
        elif name.split()[0] == "goto":
            self.places_click(text)
        elif name.split()[0] in ("boardaccept", "boardabandon", "boardrequest", "boardjoin"):
            self.board_click(text)
        elif name.split()[0] in ("gearequip", "gearunequip"):
            self.gear_click(text)
        elif name in ("gear", "equipment", "worn"):
            self.show_gear()
        elif name in ("shop", "store", "wares", "buy"):
            self.show_shop()
        elif name in ("stash", "box", "itembox"):
            here = "here" if self.can_store() else "not reachable here - find an inn with storage"
            console.note(f"Item box ({here}): {len(self.player.stash)}/{self.stash_cap()} slots")
            for i in self.player.stash:
                console.note(f"  {inv.label(i)}")
        elif name == "dialogue":
            config.NARRATED_DIALOGUE = not config.NARRATED_DIALOGUE
            console.note(f"Conversations {'narrated' if config.NARRATED_DIALOGUE else 'shown as plain dialogue'}.")
        elif name == "numbers":
            config.COMBAT_NUMBERS = not config.COMBAT_NUMBERS
            console.note(f"Combat numbers {'shown' if config.COMBAT_NUMBERS else 'hidden'}.")
        elif name == "debug":
            config.DEBUG = not config.DEBUG
            console.note(f"Debug mode {'on' if config.DEBUG else 'off'}.")
        elif name.split()[0] == "levelup" and config.DEBUG:
            c = self.player.character
            count = int(name.split()[1]) if len(name.split()) > 1 and name.split()[1].isdigit() else 1
            leveling.level_up(c, count)
            self.store.save_player(self.player)
            console.note(f"[debug] Now level {c.level}. {c.unspent_points} points to spend.")
        elif name in ("help", "h", "?"):
            console.show_help()
        else:
            console.note(f"Unknown command '{text}'. Type #help for the list.")

    def save(self) -> None:
        self.store.save_player(self.player)
        self.store.save_meta()

    def people_view(self) -> list[tuple[str, str, str]]:
        view = []
        for n in self.present:
            people = self.world.peoples[n.people].name if n.people in self.world.peoples else n.people
            desc = f"({people}) {n.description} Manner: {manner(n, self.catalog, self.store)}."
            view.append((n.label(), desc, n.activity))
        return view

    def narrate(self, event: str, player_text: str = "") -> None:
        if self.buffering:
            self.pending.append(event)
            return
        self._narrate_now(event, player_text)

    weight_hint = None
    camp_fight = None
    last_social = None

    def _narrate_now(self, event: str, player_text: str = "") -> None:
        marks = self.store.load_place(self.player.location).marks
        rule = voice_rules.narration(self.weight_hint)
        self.weight_hint = None
        result = fresh(
            "narrate", wp.NARRATOR_SYSTEM,
            wp.narration_request(self.time_label(), self.place, self.people_view(), event, player_text,
                                 self.recent_narration, self.gear_line(), marks,
                                 [inv.label(i) for i in self.ground_here()],
                                 pulse.happenings_at(self.store, self.world, self.player.location, self.minutes),
                                 rule["length"]),
            Narration, self.recent_narration, max_tokens=rule["tokens"],
        )
        shown = self.unnamed(result.text)
        console.narrate(shown)
        self.remember_narration(shown)

    exits_due = False

    def show_exits(self, force: bool = False, asked: bool = False) -> None:
        """The list of places reachable from here, shown only when the player asks for it (#exits)."""
        self.exits_due = False
        if not asked:
            return
        self.show_places()

    def places_data(self) -> dict:
        """Where the player can go from here, as plain data: the places in this town with their walking times, then the
        towns and roads they know of, nearest first."""
        from engine import mapview
        w = self.world
        here = self.player.location if self.player.location in w.places else next(
            (v for v in reversed(self.player.visited) if v in w.places), "")
        if not here:
            return {"here": "", "town": "", "local": [], "far": []}
        top = mapview.top_of(w, here)

        def row(pid: str, state: str) -> dict | None:
            found = w.path(here, pid)
            if not found:
                return None
            pl = w.places[pid]
            return {"id": pid, "name": pl.name, "type": pl.type, "minutes": found[1], "away": clock.describe_duration(found[1]), "state": state}
        local = [r for pid, pl in w.places.items() if pid != here and mapview.top_of(w, pid) == top and pl.id != top
                 for r in [row(pid, "here")] if r]
        if here != top and top != here:
            r = row(top, "here")
            if r:
                local.append(r)
        been, heard = mapview.known(w, self.player.visited, here)
        far = [r for pid in (been | heard) if pid != top for r in [row(pid, "visited" if pid in been else "heard")] if r]
        key = lambda r: (r["minutes"], r["name"])
        return {"here": here, "town": w.places[top].name, "here_name": w.places[here].name,
                "local": sorted(local, key=key), "far": sorted(far, key=key)}

    def show_places(self) -> None:
        data = self.places_data()
        if console.panel("places", data):                  # the window draws this one with Go buttons
            return
        if not data["here"]:
            console.note("You are not anywhere you know the way from.")
            return
        console.note(f"From {data['here_name']} in {data['town']}:")
        for r in data["local"]:
            console.note(f"  {r['name']} - {r['away']}")
        for r in data["far"]:
            console.note(f"  {r['name']}{'' if r['state'] == 'visited' else ' (heard of)'} - {r['away']}")

    def places_click(self, text: str) -> None:
        """The pane's hidden command:  #goto <place id>."""
        from llm.contracts import ActionIntent
        parts = text.split()
        dest = parts[1] if len(parts) > 1 else ""
        if dest not in self.world.places:
            console.note("You don't know a way there.")
        elif not any(r["id"] == dest for r in self.places_data()["local"] + self.places_data()["far"]):
            console.note("You don't know a way there from here.")
        else:
            self.on_move(ActionIntent(kind="move", destination=dest, summary=f"I go to {self.world.places[dest].name}."), "")
            self.halted = False
        if not self.combat:
            with console.scope("#exits"):
                self.show_places()

    def show_map(self) -> None:
        """The map pane: the places you have been and the ones they lead to, and how far each is from here."""
        data = mapview.view(self.world, self.player.visited, self.player.location, clock.describe_duration)
        if console.panel("map", data):
            return
        here = self.world.places[data["here"]]
        console.note(f"You are {'on the road, last in' if data.get('on_road') else 'in'} {here.name} ({self.world.regions[here.region].name if here.region in self.world.regions else here.region}).")
        for n in sorted(data["nodes"], key=lambda n: n["away"] == "", reverse=True):
            if n["state"] != "here":
                console.note(f"  {n['name']}{'' if n['state'] == 'visited' else ' (heard of)'} - {n['away']} away")

    def where_name(self, place_id: str) -> str:
        p = self.world.places.get(place_id)
        return p.name if p else "somewhere on the road"

    def people_elsewhere(self) -> list[NPC]:
        present = {n.id for n in self.present}
        others = (self.store.load_npc(i) for i in self.store.list_npcs() if i not in present)
        return [n for n in others if n.met_player]

    def interpret(self, text: str, hint: str = "") -> list[ActionIntent]:
        places = [(p.id, p.name) for p in self.world.places.values() if p.id != self.player.location]
        people = [(n.id, n.label(), f"{n.role.replace('_', ' ')}. {n.description} {n.activity}"
                   + (f" Has offered the player paid work ({n.work_offer['task']}): the player agreeing to it, doing it or finishing it is a work action, "
                      "and 'taking the pay' once it is done is part of that work." if n.work_offer else "")) for n in self.present]
        elsewhere = [(n.id, f"{n.label()} ({n.role.replace('_', ' ')})",
                      "just walked away from here and can't be spoken to for a short while"
                      if n.location == self.player.location and n.away_until > self.minutes else self.where_name(n.location))
                     for n in self.people_elsewhere()]
        left = next((n for n in self.people_elsewhere() if n.id == self.last_spoken and n.location == self.player.location
                     and n.away_until > self.minutes), None)
        last = self.last_spoken if left or any(n.id == self.last_spoken for n in self.present) else None
        if self.wildlife:
            people = people + [("wildlife", ", ".join(e.name for e in self.wildlife[1]), "a creature, keeping its distance")]
        return generate(
            "interpret_action", wp.INTERPRET_SYSTEM,
            wp.interpret_request(self.time_label(), self.place.name, places, people, elsewhere,
                                 self.partner.id if self.partner else None, last, text,
                                 [f"{w.id} from {n.id}: {w.name} - {money.words(w.price)} (sold by {n.label()})"
                                  for n in self.present for w in self.world.roles[n.role].sells]
                                 + [f"{i.name} from {n.id}: {i.rarity}, level {i.item_level} - {money.words(p)} (stock)"
                                    for n, i, p in self.stock_here()],
                                 [f"{a.id}: {a.name} ({a.field_use or a.effect.value})" for a in self.player.character.actives if a.context.value != "combat"],
                                 [inv.label(i) for i in self.pack], [inv.label(i) for i in self.ground_here()],
                                 [inv.label(i) for i in self.player.stash] if self.can_store() else None,
                                 [f"{n.id} ({n.label()}) buys {', '.join(self.world.roles[n.role].buys)}"
                                  for n in self.present if self.world.roles[n.role].buys],
                                 [inv.GOODS[next(iter(r.makes))].name for r in inv.RECIPES.values()],
                                 [k.name for k in self.player.character.key_items],
                                 markup.describe(text) if markup.has_markup(text) else "", hint,
                                 [f"{b['n']}. [{b['letter']}] {b['title']}" for b in self.board_data()["postings"]]
                                 if self.clerk_here() else (),
                                 [f"[{q['letter']}] {q['title']}" for q in self.player.quests]),
            ActionPlan, temperature=0.2, max_tokens=700,
        ).actions

    def end_conversation(self) -> None:
        self.partner = None
        self.convo = []

    @staticmethod
    def looks_like_exploring(dest: str, text: str) -> bool:
        t = f"{dest} {text}".lower()
        return any(w in t for w in ("follow", "shortcut", "short cut", "trail", "track", "path", "explore", "find a way",
                                    "see where", "wander", "look for a way", "cut through", "hidden"))

    GENERIC_WORDS = {"the", "of", "and", "hall", "house", "guild", "guildhall", "inn", "shop", "temple", "forge", "smithy", "market",
                     "square", "tavern", "workshop", "yard", "trading", "village", "town"}

    BUILDING_TYPES = ("shop", "inn", "temple", "guild", "workshop", "smithy", "yard", "guardpost")

    def nearest_alike(self, dest: str, text: str) -> str:
        """A bare "the guildhall" means the nearest one. The place the interpreter picked stands only if the player's words name it
        (its own name or its town); otherwise the nearest place of the same kind, in this town first, is used instead."""
        from engine import mapview
        w = self.world
        target = w.places[dest]
        if not text.strip():                                    # a pane button names its place exactly
            return dest
        said = set(re.findall(r"[a-z]+", text.lower()))
        own = {t for t in re.findall(r"[a-z]+", target.name.lower()) if len(t) > 3 and t not in self.GENERIC_WORDS}
        if target.type not in self.BUILDING_TYPES:
            return dest
        town = w.places.get(mapview.top_of(w, dest))
        own |= {t for t in re.findall(r"[a-z]+", town.name.lower()) if town and len(t) > 3 and t not in self.GENERIC_WORDS}
        if own & said or dest == self.player.location:
            return dest
        here_top = mapview.top_of(w, self.player.location)
        best, cost = dest, None
        for pid, pl in w.places.items():
            if pl.type != target.type or pid == self.player.location:
                continue
            found = w.path(self.player.location, pid)
            if not found:
                continue
            walk = found[1] - (1 if mapview.top_of(w, pid) == here_top else 0) * 100000    # this town's own place beats anything on the road
            if cost is None or walk < cost:
                best, cost = pid, walk
        if best != dest:
            console.debug(f"'{target.name}' read as the nearest {target.type}: {w.places[best].name}")
        return best

    def on_move(self, intent: ActionIntent, text: str) -> None:
        dest = intent.destination.strip()
        here_names = {self.player.location, self.place.name.lower(), self.place.name.lower().replace("the ", "")}
        if dest in self.world.places and dest == self.player.location or dest.lower() in here_names:
            console.debug("move within the current place - nothing to travel")
            return
        if dest not in self.world.places:
            if any(n.id == dest for n in self.present):
                return
            if not any(dest.lower() in pl.name.lower() or dest == pl.id for pl in self.world.places.values()):
                if self.place.danger or self.place.type in ("hut", "camp", "grove", "spring", "shrine", "ford", "cabin", "cave",
                                                            "ruin", "hollow", "overlook") or self.looks_like_exploring(dest, text):
                    intent.seek = intent.seek or dest
                    self.on_explore(intent, text)
                    return
                console.debug(f"'{dest}' is not a place - treating it as moving within {self.place.name}")
                return
        if dest in self.world.places:
            dest = self.nearest_alike(dest, text)
        found = self.world.path(self.player.location, dest) if dest in self.world.places else None
        if not found:
            console.note("You don't know a way there from here.")
            self.halted = True
            self.show_exits()
            return
        route, walk = found
        blocked = next(((p, pulse.closed_reason(self.store, p, self.minutes)) for p in route[1:]
                        if pulse.closed_reason(self.store, p, self.minutes)), None)
        if blocked and self.has("wayfinder") is not None:
            console.note(f"The way through {self.world.places[blocked[0]].name} is closed ({blocked[1]}), "
                         "but you know a way around.")
            blocked = None
        if blocked:
            console.note(f"The way through {self.world.places[blocked[0]].name} is closed: {blocked[1]}")
            self.halted = True
            return
        if any(i.legendary_effect == "lightfoot" for i in self.player.character.equipment.values()):
            walk = max(1, round(walk * (1 - items.LEGENDARY["lightfoot"].value / 100)))
        if self.has("trailblazer"):
            walk = max(1, round(walk * (1 - self.has("trailblazer") / 100)))
        walk = self.travel_minutes(route, walk)
        mount = self.mount_info()
        if mount and walk >= 20:
            walk = max(1, round(walk * (1 - mount["speed"])))
            console.note(f"You ride {mount['name']}.")
        walk, fatigue_factor = self.take_haste(walk)
        fatigue_factor *= self.take_swift(walk)
        self.travel_fatigue(walk, fatigue_factor)
        self.end_conversation()
        self.last_spoken = None
        console.debug(f"walking {walk} minutes: {' -> '.join(route)}")
        self.run_journey(route, walk, text)

    def on_look(self, intent: ActionIntent, text: str) -> None:
        room = (" The player has rented a small room upstairs here; if their words take them to it, describe the "
                "room - simple, private, theirs for the night. " if self.has_room() else "")
        self.narrate(
            room + "The player looks closely, focusing on what their words ask about. Answer that directly first, from what "
            "can actually be seen: if they ask about the people, describe their peoples, looks and manner. Mention only "
            "the people relevant to what they are looking at. Three to five sentences.", text)
        self.show_exits()

    def on_talk(self, intent: ActionIntent, text: str) -> None:
        target_id = intent.target if intent.target not in ("", "none", "null") else ""
        if target_id and not any(n.id == target_id for n in self.present) and not self.store.npc_exists(target_id):
            console.debug(f"'{target_id}' isn't a person - choosing someone present")
            target_id = ""
        target_id = target_id or (self.partner.id if self.partner else "") or (self.last_spoken or "")
        if not target_id and self.present and not any(n.id == self.last_spoken for n in self.present):
            target_id = self.present[0].id
        npc = next((n for n in self.present if n.id == target_id), None)
        resident = next((n for n in self.residents if n.id == target_id), None)
        if not npc and resident:
            if resident.away_until > self.minutes:
                console.note(f"{resident.label()} has stepped away. Give it a little while.")
                self.halted = True
            else:
                console.note(f"{resident.label()} isn't here at this hour.")
                self.halted = True
            return
        if not npc and self.store.npc_exists(target_id):
            away = self.store.load_npc(target_id)
            console.note(f"{away.label()} isn't here. You last saw them at {self.where_name(away.location)}.")
            return
        if not npc and not self.present:
            self.narrate("The player says or thinks this aloud, but no one is here to answer. Reflect the silence "
                         "of the place back at them in a sentence or two.", text)
            return
        if not npc:
            here = ", ".join(n.label() for n in self.present)
            console.note(f"Talk to whom? Here: {here}")
            self.halted = True
            return
        if not self.partner or self.partner.id != npc.id:
            self.end_conversation()
            self.partner = npc
        self.last_spoken = npc.id
        promote(npc, self.store, self.world, self.catalog)

        speech = intent.speech or text
        label_before = npc.label()
        first_time = not npc.met_player
        if first_time:
            rep = self.player.reputation.get(pulse.town_of(self.world, npc.location), 0)
            npc.trust = max(0, min(100, npc.trust + round(rep * pulse.P["reputation"]["trust_per_point"])
                                   + self.first_meeting_trust(npc) + self.heat_trust() + self.standing_trust(npc)))
        else:
            self.easy_company(npc)
        if first_time and self.has("oathbound") and set(self.world.roles[npc.role].knowledge_groups) & {"guards", "temple"}:
            npc.trust = min(100, npc.trust + round(self.has("oathbound")))
        if first_time and self.has("trusted_face"):
            npc.trust = min(100, npc.trust + round(self.has("trusted_face")))
            console.debug(f"trusted face: {npc.name} starts at trust {npc.trust}")
        check_note = getattr(self, "pending_check", "")
        self.pending_check = ""
        ctx = self.npc_context(npc)
        note_due = self.note_due(npc)
        if note_due:
            ctx = ctx + [("JOURNAL NOTE DUE: write journal_note now." + (f" The old note was: {npc.journal_note} - bring it up to date with what has happened since."
                                                                         if npc.journal_note else ""))]
        secret_lines, pending_secret = self.secret_lines(npc, speech)
        ctx = ctx + secret_lines
        if npc.id in self.player.prisoners:
            self.player.prisoners[npc.id]["asked"] = self.player.prisoners[npc.id].get("asked", 0) + 1
        level = voice_rules.npc_level(npc, speech, self.convo, ctx, first_time)
        self.npc_level = level
        reply, revealed = converse(npc, self.store, self.world, self.catalog, self.convo,
                                   f"{speech} {check_note}".strip(), ctx, level)
        if reply.intent == "leave" and not has_parting(reply.speech):
            reply.intent = "small_talk"            # nobody walks off without a word: no goodbye or dismissal in the speech, no leaving
        self.convo += [("Stranger", speech), (npc.name, reply.speech)]
        if note_due and reply.journal_note.strip():
            npc.journal_note = " ".join(reply.journal_note.split())[:240]
            npc.note_trust, npc.note_mem = npc.trust, len(npc.memories)
        self.orenna_named(speech)
        if reply.offers_work and reply.offers_work.task.strip():
            self.record_work_offer(reply.offers_work, npc)
        elif reply.offers_quest and reply.offers_quest.what.strip() and not npc.quest_offer:
            self.record_quest_offer(reply.offers_quest, npc)
        elif not npc.work_offer and not (reply.offers_quest and reply.offers_quest.what.strip()) and self.promises_pay(reply.speech):
            self.record_work_offer(self.inferred_offer(npc, reply.speech), npc)      # pay was promised in words: make it a real, payable offer
        if reply.gives and reply.gives.name.strip() and reply.intent != "bargain" and self.story_object(reply.gives.name):
            self.receive_key_item(reply.gives, npc)
        elif reply.gives:
            console.debug(f"ignored gift '{reply.gives.name}' - not a story object, or offered for sale")
        speaker = npc.label() if reply.told_own_name else label_before
        self.flush(text)
        if config.NARRATED_DIALOGUE:
            self.narrate_dialogue(npc, label_before, speaker, text, reply, first_time)
        else:
            gesture = self.unnamed(reply.gesture, npc)
            console.npc_says(speaker, reply.speech, gesture)
            self.remember_narration(f'{speaker}: "{reply.speech}"', {"type": "says", "speaker": speaker, "speech": reply.speech, "gesture": gesture})

        if reply.intent == "lie" and self.has("lie_sense") is not None:
            gift = next((i for i in self.player.character.equipment.values() if "lie_sense" in (i.trait or {}).get("world", {})), None)
            console.note(f"{gift.name if gift else 'Your relic'} turns cold against your skin. {npc.label()} just lied to you.")
        known = self.player.character.knowledge
        for fact_id in revealed:
            if fact_id not in known:
                known.append(fact_id)
                console.debug(f"player learned: {fact_id}")
        self.secret_after(npc, pending_secret)
        if reply.intent == "leave" and reply.speech.rstrip().rstrip('"\'').endswith("?"):
            reply.intent = "small_talk"            # someone who has just asked a question has not walked away
        if reply.intent == "leave" and npc.role in ("guild_clerk",):
            reply.intent = "small_talk"            # the clerk stays at the desk: the guild must stay reachable
        if reply.intent == "leave" and npc.id not in self.player.prisoners:
            console.note(f"{npc.label()} ends the conversation and steps away.")
            self.halted = True
            npc.away_until = self.minutes + 30
            self.store.save_npc(npc)
            self.end_conversation()
            self.refresh_present()

    def unnamed(self, text: str, *extra) -> str:
        """The text with the real name of anyone the player has not been told hidden behind how the player knows them."""
        people = list(self.present) + ([self.partner] if getattr(self, "partner", None) else []) + [x for x in extra if x]
        return markup.hide_names(text, people)

    def narrate_dialogue(self, npc, known_as: str, speaker: str, player_did: str, reply, first: bool) -> None:
        others = [self.unnamed(f"{n.label()}: {n.activity}", npc) for n in self.present if n.id != npc.id][:5]
        manner = self.unnamed(f"{npc.personality} {npc.voice}".strip(), npc) or "unknown yet"
        try:
            frame = fresh(
                "dialogue_frame", wp.DIALOGUE_SYSTEM,
                wp.dialogue_request(self.time_label(), self.place, others, known_as, self.unnamed(npc.description, npc), self.unnamed(npc.activity, npc),
                                    manner, first, player_did, reply.speech, self.unnamed(reply.gesture, npc),
                                    reply.intent == "leave", self.recent_narration,
                                    voice_rules.npc(getattr(self, "npc_level", "short"))["frame"]),
                DialogueFrame, self.recent_narration, fields=("before", "after"), max_tokens=450 if getattr(self, "npc_level", "short") == "short" else 700,
            )
        except LLMError:
            gesture = self.unnamed(reply.gesture, npc)
            console.npc_says(speaker, reply.speech, gesture)
            self.remember_narration(f'{speaker}: "{reply.speech}"', {"type": "says", "speaker": speaker, "speech": reply.speech, "gesture": gesture})
            return
        before, after = self.unnamed(frame.before, npc), self.unnamed(frame.after, npc)
        console.dialogue(before, speaker, reply.speech, after)
        self.remember_narration(" ".join(t for t in (before, after) if t.strip()),
                                {"type": "dialogue", "before": before, "speaker": speaker, "speech": reply.speech, "after": after})

    def on_leave_conversation(self, intent: ActionIntent, text: str) -> None:
        if self.partner and intent.speech.strip():
            partner = self.partner
            intent.target = partner.id
            intent.speech = f"{intent.speech.strip()} (said in parting - they are about to leave)"
            self.on_talk(intent, text)
            if self.partner:
                console.note(f"You step away from {partner.label()}.")
            self.end_conversation()
            return
        if self.partner:
            console.note(f"You step away from {self.partner.label()}.")
        self.end_conversation()

    def has_room(self) -> bool:
        return (self.player.room == self.player.location and self.player.room_until > self.minutes) or \
            (self.place.type == "home" and not self.home_ruined())

    def on_buy(self, intent: ActionIntent, text: str) -> None:
        if self.mount_buy(intent, text):
            return
        if self.property_buy(intent, text):
            return
        sellers = [n for n in self.present if self.world.roles[n.role].sells]
        listed = any(w.id == intent.ware.lower().strip() or (intent.ware and intent.ware.lower() in w.name.lower())
                     for n in sellers for w in self.world.roles[n.role].sells)
        if not listed and self.buy_from_stock(intent, text):
            return
        seller = next((n for n in sellers if n.id == intent.target), None) or (sellers[0] if sellers else None)
        if not seller:
            console.note("No one here is selling anything.")
            self.halted = True
            return
        wares = self.world.roles[seller.role].sells
        wanted = intent.ware.lower().strip()
        ware = next((w for w in wares if w.id == wanted), None) or \
            next((w for w in wares if wanted and (wanted in w.name.lower() or w.id in wanted)), None)
        if not ware:
            console.note(f"{seller.label()} sells: " + ", ".join(f"{w.name} ({money.words(w.price)})" for w in wares))
            self.halted = True
            return
        self.buy_ware(seller, ware, text)

    def on_ability(self, intent: ActionIntent, text: str) -> None:
        c = self.player.character
        ability = next((a for a in c.actives if a.id == intent.ability), None) or \
            next((a for a in c.actives if a.name.lower() in text.lower()), None)
        if not ability:
            self.on_other(intent, text)
            return
        craft_words = ("craft", "forge", "smith", "make", "brew", "temper", "work the", "hammer", "sew", "tan", "cook")
        if ability.effect.value == "crafting" and ability.name.lower() not in text.lower() \
                and not any(w in text.lower() for w in craft_words):
            console.debug(f"{ability.name} is a crafting ability and they aren't crafting - looking instead")
            self.on_look(intent, text)
            return
        if ability.context.value == "combat":
            console.note(f"{ability.name} is a fighting technique - save it for a fight.")
            self.halted = True
            return
        self.ensure_field_uses()
        if ability.field_use:
            refusal = self.field_precheck(ability, intent, text)
            if refusal:
                console.note(refusal)
                self.halted = True
                return
        pool = ability.resource.value
        table = "ability_cost_percent" if pool == "mana" else "stamina_cost_percent"
        cost = pools.reference_pool(pool, c.level) * COMBAT_RULES[table][ability.tier.value] / 100
        if pools.current(c, pool) < cost:
            self.narrate(f"The player tries to use {ability.name}, but they are too drained - not enough {pool}. "
                         "Describe the attempt faltering.", text)
            self.halted = True
            return
        setattr(c, pool, pools.current(c, pool) - cost)
        self.advance(clock.OTHER_MINUTES)
        effect = ability.effect.value
        if effect == "summon" and ability.companion:
            bound = next((m for m in c.companions if m.source in (ability.name, ability.id)), None)
            if not bound:
                t = ability.companion
                bound = Companion(id=t.id, name=t.name, kind=getattr(t.kind, "value", t.kind),
                                  role=getattr(t.role, "value", t.role), level=c.level, description=t.description,
                                  source=ability.name, tier=getattr(t.tier, "value", t.tier), health=t.health, damage=t.damage)
                c.companions.append(bound)
                result = f"{bound.name} answers the call for the first time and is now bound to them."
            elif bound.dead:
                result = f"{bound.name} does not answer. It is gone, and only a revival could bring it back."
            elif bound.fallen:
                bound.fallen = False
                result = f"{bound.name} answers the call again and stands ready at their side."
            else:
                result = f"{bound.name} answers the call and stands ready at their side."
        elif effect == "crafting":
            self.craft_boost = {"light": 8, "moderate": 15, "heavy": 25}[ability.tier.value]
            result = "Their next piece of work will be better for it."
        elif effect == "healing":
            top = pools.maximum(c, "health")
            gain = top * {"light": 0.15, "moderate": 0.25, "heavy": 0.4}[ability.tier.value]
            c.health = min(top, pools.current(c, "health") + gain)
            result = "Their wounds close a little."
        elif ability.field_use:
            result = self.field_apply(ability, intent, text)
            if result is None:      # nothing came of it: no cost
                setattr(c, pool, pools.current(c, pool) + cost)
                self.halted = True
                return
        else:
            result = ("The ability works as described, but nothing in the world changes because of it yet - describe "
                      "what they experience without inventing discoveries, information or outcomes.")
        if effect in ("healing", "crafting"):
            self.field_cooldown_start(ability)
        self.store.save_player(self.player)
        self.narrate(f"Outside of any fight, the player uses {ability.name}: {ability.description} {result}", text)

    def npc_context(self, npc) -> list[str]:
        """What a person should know right now beyond their own life - the guild, offers they've made."""
        lines = []
        if npc.role == "guild_clerk":
            status = f"a guild member of rank {self.rank}" if self.rank else \
                f"not a guild member - joining costs {money.words(quests.G['joining_fee'])}, paid through the game"
            lines.append(f"The person in front of you is {status}.")
            board = self.ensure_board()
            if board:
                lines.append("Contracts on the board: " + "; ".join(f"[{q['letter']}] {q['title']}" for q in board))
            mine = [q["title"] for q in self.player.quests if q["guild"]]
            if mine:
                lines.append("Contracts they hold: " + "; ".join(mine))
            lines.append("Ranks run F (lowest) to S. Members take contracts of their letter and below; promotion needs "
                         "both a level and enough completed contracts.")
        if npc.role == "guild_contractor":
            import zlib
            letter = "FFFEED"[zlib.crc32(npc.id.encode()) % 6]
            lines.append(f"You are a rank-{letter} member of the adventurers' guild, between contracts. You know the "
                         "Greywood and its dangers from your own jobs, and you size up newcomers.")
        if npc.quest_offer:
            lines.append(f"You have asked them to: {npc.quest_offer['title']}, and are waiting for their answer.")
        if npc.mood:
            lines.append(f"How you've been lately: {npc.mood}")
        if npc.motive:
            lines.append(f"What you're working toward (private - share it only if it comes up naturally): {npc.motive}")
        feelings = pulse.relations_text(self.store, npc)
        if feelings:
            lines.append(f"How you feel about people you know: {feelings}")
        news = pulse.news_for(self.store, self.world, npc, self.minutes, 8 if self.owns("gossips_ear") else 5)
        if news and self.owns("gossips_ear"):
            lines.append("You like passing on news to the stranger - tell them what you've heard without being asked.")
        if news:
            lines.append("News and talk you've heard lately (mention it when it's natural - it's what people talk "
                         "about): " + " | ".join(news))
        own = [m.text.replace("(my own life) ", "") for m in npc.memories if m.text.startswith("(my own life)")][-2:]
        if own:
            lines.append("What has happened in your own life since you last saw the stranger: " + " ".join(own))
        town = pulse.town_of(self.world, npc.location)
        if not self.world.places[town].danger:
            lines.append(f"How people around here regard the stranger: {self.reputation_words(town)}.")
            group_line = self.standing_line(npc)
            if group_line:
                lines.append(group_line)
        faith = faith_mod.line(self.world, npc)
        if faith:
            lines.append(faith)
        if "orenna_name" in self.player.character.knowledge:
            lines.append("No one living has ever heard the name Orenna. If the stranger says it, it means nothing to you; you do not "
                         "recognise it, and you do not pretend to.")
        lines += self.guild_knowledge(npc)
        lines.append(f"The season is {clock.season(self.minutes)}.")
        return lines

    def on_search(self, intent: ActionIntent, text: str) -> None:
        if self.place.type == "dungeon" and self.player.delve:
            self.dungeon_search(text)
            return
        if not self.place.danger:
            self.narrate("The player searches the area. There is no wild game or danger here. Describe the search "
                         "briefly and what ordinary things they notice instead.", text)
            return
        if self.wildlife:
            seen = self.wildlife[0]
            if intent.seek and encounters.matching(self.world, [seen.id], intent.seek):
                self.narrate(f"The {seen.name.lower()} they are looking for is right here, keeping its distance. "
                             "Remind them briefly.", text)
                return
            self.wildlife = None
            console.debug(f"moving on from the {seen.name.lower()} in view")
        self.advance(SEARCH["search_minutes"])
        if self.bounty_encounter():
            return
        chance = SEARCH["chance_on_search"] + (SEARCH["tracker_bonus"] if self.has("tracker") is not None else 0)
        chance += (self.mech("patient_watch") + (self.mech("sniffer") if self.companion_here() else 0)) / 100
        quarry = next((q for q in self.player.quests if q["kind"] in ("hunt", "bounty") and q.get("place") ==
                       self.player.location and q["progress"] < q["count"]), None) if self.owns("game_warden") else None
        if quarry:
            name = self.world.bestiary[quarry["creature"]].name
            for _ in range(6):
                hit = encounters.roll(self.store, self.world, self.player.location, 1.0, self.rng, name, contracts=self.player.quests)
                if hit and hit[0].id == quarry["creature"]:
                    break
            else:
                hit = None
            if hit:
                creature, enemies = hit
                from scenes.combat_scene import CombatScene
                self.combat = CombatScene.begin(self, creature, enemies, "You find the trail of your quarry:")
                return
        if self.maybe_encounter(min(0.95, chance), "Your search pays off:", intent.seek or text):
            return
        if self.wildlife:
            return
        roster = encounters.ensure_roster(self.store, self.world, self.player.location)
        wanted = encounters.matching(self.world, roster, intent.seek) if intent.seek else []
        clue = self.world.bestiary[self.rng.choice(wanted or roster)].name.lower() if roster else ""
        self.narrate(f"The player spends {clue and 'a while '}searching but finds no creature this time. They do find "
                     f"fresh signs of {clue or 'nothing'}: tracks, droppings, or marks. Describe the search and the sign."
                     f"{' The creature they were looking for is not known to live here.' if intent.seek and not wanted else ''}",
                     text)

    def on_attack(self, intent: ActionIntent, text: str) -> None:
        if self.wildlife:
            creature, enemies = self.wildlife
            self.wildlife = None
            self.combat = CombatScene.begin(self, creature, enemies, "You attack")
            return
        prisoner = self.prisoner_here(intent)
        if prisoner:
            self.execute_prisoner(prisoner, text)
            return
        if self.present:
            console.note("Attacking people isn't supported yet.")
        else:
            console.note("There's nothing here to fight.")

    def on_wait(self, intent: ActionIntent, text: str) -> None:
        barrow = (self.dungeon_here() or {}).get("theme") == "barrow"
        camped = self.camp_active()
        if self.place.type == "dungeon" and self.player.delve and not self.player.delve.get("rest") and not camped \
                and self.has("safe_camp") is None and not (barrow and self.owns("tomb_sleeper")):
            console.note("It's too dangerous to rest here. Find a quiet chamber, or climb back out.")
            self.halted = True
            return
        if intent.wait_until:
            minutes = clock.minutes_until(self.minutes, intent.wait_until)
        else:
            minutes = intent.wait_minutes or clock.DEFAULT_WAIT_MINUTES
        minutes = max(1, min(minutes, clock.MAX_WAIT_MINUTES))
        sleeping = minutes >= 360
        if sleeping and self.owns("restless"):
            minutes = max(180, minutes // 2)
        self.end_conversation()
        before = {n.id for n in self.present}
        c0 = self.player.character
        hp0, hp_top0, fat0 = pools.current(c0, "health"), pools.maximum(c0, "health"), c0.fatigue
        waited, hit = 0, None
        while waited < minutes:
            step = min(60, minutes - waited)
            self.advance(step, wait="sleep" if sleeping else "rest")
            waited += step
            if self.place.danger and not self.owns("night_watch") and not camped:
                hit = encounters.roll(self.store, self.world, self.player.location,
                                      encounters.E["chance_per_hour"] * step / 60, self.rng)
                if hit and self.temperament(hit[0]) != "passive":
                    break
                hit = None
        minutes = waited
        if not hit and sleeping:
            c = self.player.character
            c.last_rest = self.player.location
            rough = self.place.danger and self.owns("campaigner")
            temple = self.place.type == "temple" and self.owns("sanctuary")
            if camped:
                for pool in ("health", "stamina", "mana"):
                    setattr(c, pool, pools.maximum(c, pool))
                console.note(f"You slept safely in your camp and woke fully rested. If you die, you will wake at {self.place.name}.")
            elif rough or temple:
                for pool in ("health", "stamina", "mana"):
                    setattr(c, pool, pools.maximum(c, pool))
                console.note("You slept well and woke fully rested" + (" in the temple's quiet." if temple else
                             ", as a soldier learns to on hard ground.") + f" If you die, you will wake at {self.place.name}.")
            elif self.has_room():
                for pool in ("health", "stamina", "mana"):
                    setattr(c, pool, pools.maximum(c, pool))
                console.note(f"You slept in your room and woke fully rested. If you die, you will wake at {self.place.name}.")
            else:
                console.note(f"You rested here. If you die, you will wake at {self.place.name}.")
        arrived = [n.label() for n in self.present if n.id not in before]
        left = [n.label() for n in self.residents if n.id in before and n not in self.present]
        changes = ""
        if arrived:
            changes += f" Arrived meanwhile: {', '.join(arrived)}."
        if left:
            changes += f" Gone home meanwhile: {', '.join(left)}."
        console.debug(f"waited {minutes} minutes")
        interrupted = " Their rest is cut short by danger." if hit else ""
        c1 = self.player.character
        healed = (pools.current(c1, "health") - hp0) / max(1.0, hp_top0)
        eased = fat0 - c1.fatigue
        how = "sleeps" if sleeping else "rests"
        body = []
        if healed >= 0.6:
            body.append("their wounds close and their strength returns almost completely")
        elif healed >= 0.15:
            body.append("their hurts ease and some of their strength returns")
        elif healed >= 0.03:
            body.append("they recover a little")
        if sleeping and (eased >= 20 or not needs.on()):
            body.append("they wake rested, their head clear")
        elif eased >= 5:
            body.append("their tiredness lifts a little")
        feel = f" While they rest, {' and '.join(body)} (say so in the story; no numbers)." if body and not hit else ""
        self.narrate(f"The player {how} at {self.place.name} for {clock.describe_duration(minutes)}. It is now {clock.period(self.minutes)}."
                     f"{changes}{interrupted}{feel} Describe the player resting and the passing of time, then the scene now. Keep it to "
                     "three or four sentences and mention at most two of the people present.", text)
        if not hit and sleeping:
            self.after_sleep()
        if hit:
            creature, enemies = hit
            if creature.temperament == "territorial" or self.has("danger_sense") is not None:
                for e in enemies:
                    e.band = "far"
            self.combat = CombatScene.begin(self, creature, enemies, "While you wait,")

    def on_other(self, intent: ActionIntent, text: str) -> None:
        console.debug("not yet resolvable by the engine; narrating the attempt only")
        self.narrate(
            "The player attempts something the game cannot resolve yet. Describe only them beginning it and "
            "the immediate moment. Do not say whether it succeeds, and give them nothing, injure no one, "
            "and have no one react beyond a glance.",
            text,
        )
