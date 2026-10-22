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
from scenes.exit_actions import ExitActions
from scenes.mentor_actions import MentorActions
from scenes.stats_actions import StatsActions
from scenes.banter_actions import BanterActions
from scenes.quirk_actions import QuirkActions
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
from scenes.trial_actions import TrialActions
from scenes.passive_hooks import PassiveHooks
from scenes.field_actions import FieldActions
from scenes.audit_actions import AuditActions
from scenes.standing_actions import StandingActions
from scenes.law_actions import LawActions
from scenes import markup
from engine import mapview, mentor, needs, pulse, pulselog, quests
from engine import inventory as inv
from engine import crafting
from engine import clock, equipment, items, leveling, money, pools, voice_rules, weather
from llm.contracts import ActionIntent, ActionPlan, DialogueFrame, Narration
from llm.gateway import LLMError, generate
from npc import backfill, life
from npc.life import converse, has_parting, manner, populate_place, promote
from npc.models import Memory, NPC
from npc.traits import TraitCatalog
from scenes import world_prompts as wp
from storage.campaign import CampaignStore, PlayerState
from ui import console
from world.loader import World

QUIT_WORDS = {"quit", "exit", "/quit", "/exit"}
NEGATED = re.compile(r"\b(don'?t|do not|won'?t|will not|can'?t|cannot|not|never|refuse|decline|later)\b")     # "I don't want to join" is not joining
PAST = re.compile(r"\b(paid|gave|yesterday|last (week|night|time)|already|before)\b")                        # "the 2 silver I paid you" is no offer
from engine.actions import TIME_COST                 # how long each kind of action takes: declared with the action (engine/actions.py)
SEARCH = encounters.E


class WorldScene(ExitActions, InventoryActions, ShopActions, GearActions, CheckActions, WorkActions, GuildActions, TrainingActions, DungeonActions,
                 RoadActions, ExploreActions, PropertyActions, MountActions, ArcActions, CampActions, PartyActions, TrialActions, PassiveHooks, FieldActions, AuditActions, LawActions, StandingActions, OrennaActions, MentorActions, StatsActions, BanterActions, QuirkActions):
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
        self.sneaking, self.queued_buffs, self.fight_text = False, [], ""     # a fight the player starts this turn (f248)
        self.recently_fled = False
        self.rng = random.Random()
        pools.fill_missing(self.player.character)
        from engine import domain_events
        domain_events.journal_everything()
        self.name_ids()               # the journal and the stable ids are bound from the start, not only from the first turn
        from engine import reactions
        reactions.register(self)      # the world's reactions to the player's deeds, bound to this scene (engine/reactions.py)

    def npc_by_id(self, nid: str):
        """The person with this id as this scene holds them (present or resident here): the same object the scene saves at the end of the
        turn, so a change made through it is not overwritten by that save. Anyone else is loaded from the store. None if there is no one."""
        if not nid:
            return None
        held = self.__dict__.get("_live") or {}
        if nid in held:
            return held[nid]
        for n in self.present + self.residents:
            if n.id == nid:
                return n
        return self.store.load_npc(nid) if self.store.npc_exists(nid) else None

    def notice(self, event, *people) -> None:
        """The world notices a deed of the player's (engine/reactions.py). `people` are the records this code holds for anyone in it, so
        that the reactions change the very objects it will save, whether or not they stand in `present` right now."""
        from engine.domain_events import publish
        self._live = {n.id: n for n in people if n is not None}
        try:
            publish(event)
        finally:
            self._live = {}

    @property
    def party_service(self):
        """The party's mechanics (services/party.py), always over the player's current record (which a rollback reloads)."""
        from services.party import PartyService
        return PartyService(self.player, lambda: self.minutes, self.store.meta.seed)

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
        sky = weather.condition(self.store.meta.seed, self.minutes)["id"]
        if sky in ("rain", "storm"):
            found.add("in_bad_weather")
        if sky == "storm":
            found.add("in_storm")                          # the storm itself, for those chosen by it (engine/combat_perks.py)
        parent = self.world.places.get(self.place.parent) if self.place.parent else None
        biome = self.place.biome or (parent.biome if parent else None)
        found.add("in_settlements" if biome == "urban" or (not biome and not self.place.danger) else "in_wilderness")
        if self.place.type == "dungeon":
            found.add("underground")                       # no open sky down here (Sunlit Growth, f268)
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
        if self.owns("pale_company") and creature.category in __import__("engine.world_perks", fromlist=["P"]).P["pale_company"]["categories"]:
            return "passive"
        if self.deterred(creature, high):
            return "passive"
        return creature.temperament

    def maybe_encounter(self, chance: float, how: str, seek: str = "") -> bool:
        if self.combat or self.recently_fled:
            self.recently_fled = False
            return False
        if mentor.stage(self.player) == "hunt" and self.player.location == mentor.M["hunt"]["place"] and not self.player.mentor.get("found"):
            return False                      # her lesson comes first: the wolves are found by searching, as she teaches
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
        if creature.temperament == "territorial" or self.sees_far():
            for e in enemies:
                e.starts_far = True
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

    def assault_fight_over(self, outcome: str) -> None:
        """(f324) A fight at the gate of a town a cataclysm reached: the outcome decides whether the town holds."""
        from engine import events
        events.assault_over(self, outcome)

    def visit(self, npc, until: int) -> None:
        """(f317) Someone from elsewhere in town is here for a while - they came looking for the player."""
        self.visitors = [v for v in getattr(self, "visitors", []) if v[0] != npc.id] + [(npc.id, until, self.player.location)]
        self.refresh_present()

    def refresh_present(self) -> None:
        from engine import court
        self.present = [n for n in self.residents
                        if clock.in_hours(self.minutes, self.world.roles[n.role].hours) and n.away_until <= self.minutes and court.visible(self, n)]
        here = {n.id for n in self.present}
        self.visitors = [v for v in getattr(self, "visitors", []) if v[1] > self.minutes and v[2] == self.player.location and self.store.npc_exists(v[0])]
        for vid, _, _ in self.visitors:
            if vid not in here:
                v = self.store.load_npc(vid)
                if not v.gone:
                    self.present.append(v)
        if getattr(self, "partner", None):          # residents are reloaded from disk each turn: keep pointing at the same person's fresh copy
            fresh_copy = next((n for n in self.present if n.id == self.partner.id), None)
            if fresh_copy:
                self.partner = fresh_copy

    def run_pulse(self) -> None:
        """Let the world move on, then see who is still here."""
        from engine import drift, events
        drift.apply_player(self.player, pulse.catch_up(self.store, self.world, self.catalog, self.minutes) or {})   # (f331) what the drift owes the record this scene holds
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
                   + (f"; door {t['door']}{' (hidden)' if t.get('hidden') else ''}, clues found {sum(1 for c in t.get('clues', []) if c['found'])}/{len(t.get('clues', []))}, paths {len(t.get('paths') or [])}" if t.get("door") else "")
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
        movers = self.store.npc_rows(motive=True, gone=False)
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
        if amount > 0 and self.has("town_defender"):
            amount = round(amount * (1 + self.has("town_defender") / 100))
        self.player.reputation[town] = max(-100, min(100, self.player.reputation.get(town, 0) + amount))

    def reputation_words(self, town: str) -> str:
        r = self.player.reputation.get(town, 0)
        return ("unknown - just a stranger" if -5 < r < 5 else "well liked" if r >= 30 else "liked" if r >= 10
                else "known, and thought decent" if r > 0 else "distrusted" if r <= -30 else "viewed warily")

    def enter(self, place_id: str) -> None:
        self.wildlife = None
        new_town, old_town = pulse.town_of(self.world, place_id), pulse.town_of(self.world, self.player.location)
        if new_town != old_town:
            self.__dict__.setdefault("_happenings_seen", set()).clear()           # (f323) a new town: its happenings are new to the eye
            from engine import ambient
            if self.world.peoples_at(old_town) and old_town in self.world.places and not self.world.places[old_town].danger:
                self.player.last_in[old_town] = self.minutes                       # (f331) when the player last left a town
            self._arrival_lines = ambient.since(self.store, self.world, new_town, self.player.last_in.get(new_town), self.minutes)
        self.leave_road(place_id)
        self.revisit = self.store.load_place(place_id).populated
        self.player.location = place_id
        self.note_town(place_id)
        self.standing_arrive()
        self.first_arrival = place_id not in self.player.visited
        if self.first_arrival:
            self.player.visited.append(place_id)
            self.weight_hint = "major" if self.world.places[place_id].type == "city" else "rich"
        self.residents = populate_place(self.store, self.world, place_id, self.catalog, first_batch=life.FIRST_BATCH)
        self.refresh_present()
        self.home_arrival()
        self.arc_enter(place_id)
        self.bring_prisoners(place_id)
        self.party_notice()
        self.trial_notice(on_arrival=True)

    def start_backfill(self) -> None:
        """The scene is on screen and the player is reading: make the rest of this place's people in the background."""
        if life.FIRST_BATCH and not self.combat:
            backfill.start(self.store, self.world, self.catalog, self.player.location)

    def apply_backfill(self) -> None:
        """Add any people the background job has finished to the scene."""
        if not backfill.pending():
            return
        if self.player.location in backfill.collect(self.store, self.world, self.catalog):
            here = self.store.load_place(self.player.location)
            self.residents = [n for n in (self.store.load_npc(i) for i in here.residents) if not n.gone]
            self.refresh_present()

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
            self.start_backfill()
            text = console.ask(main=True)
            self.apply_backfill()
            if not text:
                continue
            if text.lower() in QUIT_WORDS:
                self.store.save_player(self.player)
                console.note("Saved. Run main.py again to continue.")
                return
            if text.startswith("#"):
                before = self.player.location
                try:
                    with self.store.transaction(), console.scope(text):      # a pane button is a whole turn too: all of it, or none of it
                        self.command(text)
                except LLMError as e:
                    console.debug(f"command rolled back: {e}")
                    self.reload_after_rollback()
                    console.note("The world seems to hesitate - the model couldn't produce a usable answer. Nothing has changed; try again.")
                if self.restart:
                    self.store.save_player(self.player)
                    return
                self.pane_arrival(before)
                continue
            if not self.turn(text):
                console.note("The world seems to hesitate - the model couldn't produce a usable answer. "
                             "Nothing has changed; try again, perhaps worded differently.")
            self.show_header()

    def name_ids(self) -> None:
        """Who is who, for anything kept under a stable id instead of a name (engine/canon.py opinions): the hires, Maren, the player."""
        from engine import canon, mentor
        canon.IDS = {m["name"]: m["id"] for m in self.player.party if m.get("name") and m.get("id")}
        canon.IDS[mentor.NAME] = "maren"
        canon.IDS[self.player.character.name] = "player"
        canon.JOURNAL = lambda kind, actor, target, text, data: self.store.journal(self.minutes, kind, actor, target, text, data, self.last_text[:80])

    def turn(self, text: str) -> bool:
        """One whole turn as one unit: everything the action and what follows it write is committed together at the end, or, if the model
        fails partway, rolled back together and the game put back as it was before the line was typed. True if the turn stood."""
        self.name_ids()
        try:
            with self.store.transaction():
                self.handle(text)
                heard = self.hire_said_marks()
                self.sync_heard()
                self.orenna_tick()
                self.mentor_tick()
                self.quirk_tick()
                self.banter_tick()
                self.note_hire_spoke(heard)
                self.collapse_check()
                self.store.save_player(self.player)
            return True
        except LLMError as e:
            console.debug(f"turn rolled back: {e}")
            self.reload_after_rollback()
            return False

    def reload_after_rollback(self) -> None:
        """The database was rolled back to before the turn; what the scene holds in memory must match it again."""
        self.store.reload_meta()                           # the clock the turn advanced goes back with it
        self.player = self.store.load_player()
        pools.fill_missing(self.player.character)
        saved_fight = self.store.load_combat()
        self.combat = CombatScene.resume(self, saved_fight) if saved_fight else None
        here = self.store.load_place(self.player.location)
        if here.populated:
            self.residents = [n for n in (self.store.load_npc(i) for i in here.residents) if not n.gone]
        self.refresh_present()
        self.partner = next((n for n in self.present if self.partner and n.id == self.partner.id), None)
        self.pending, self.buffering, self.halted = [], False, False

    def pane_arrival(self, before: str) -> None:
        """Arriving by a pane button (the map, the places list) counts like arriving by a typed line: what is due on arrival happens now."""
        if self.player.location == before or self.combat:
            return
        try:
            self.sync_heard()
            self.orenna_tick()
            self.mentor_tick()
            self.quirk_tick()
            self.banter_tick()
        except LLMError:
            pass
        self.store.save_player(self.player)

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
        own_hands = self.owns("enchanter") and bool(self.place.stations)
        if not enchanter and not own_hands and not config.DEBUG:
            console.note("There's no enchanter here. You'll need to find one - perhaps somewhere magic is welcome."
                         + (" Or a workshop: you can do the work yourself." if self.owns("enchanter") else ""))
            return
        if not enchanter and own_hands:
            enchanting.DISCOUNT["percent"] = 100        # Enchanter: your own hands at a workshop, no fee
            console.note("No enchanter here, but a workshop and your own hands will do (Enchanter).")
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
        return abs(npc.trust - npc.note_trust) >= self.NOTE_TRUST_SHIFT or npc.memory_total - npc.note_mem >= self.NOTE_NEW_MEMORIES

    def journal_line(self, n, town: str) -> str:
        """One sentence about a person you know by name: their own note when they have written one, a plain line from what is known until then."""
        import re as _re
        if n.journal_note and not ("[" in n.journal_note or _re.search(r"\b(I|I'm|I've|my|me)\b", n.journal_note)):
            return n.journal_note                            # (f299) a note written in their own voice, from an older save, is passed over
        if n.id == "maren":
            return mentor.M["journal_after"]
        role = n.role.replace("_", " ")
        first = (n.description or "").split(". ")[0].strip().rstrip(".")
        return f"{role.capitalize()} of {town or 'the road'}" + (f" - {first[0].lower() + first[1:]}." if len(first) > 12 else ".")

    def journal_data(self) -> dict:
        """People you know by name, by town (this town first, then the last one you stood in), what you have learned, what you have let go."""
        here = pulse.town_of(self.world, self.player.location)
        last = next((t for t in reversed(self.fld.get("towns", [])) if t != here), "")
        groups: dict[str, list] = {}
        for n in self.store.load_npcs([r.id for r in self.store.npc_rows(met_player=True) if r.name_known_to_player]):
            town = pulse.town_of(self.world, n.location) if n.location in self.world.places else ""
            groups.setdefault(town, []).append(n)
        virtual = self.mentor_journal_entry()
        if virtual:
            groups.setdefault(virtual[0], []).append(virtual[1])

        def rank(t):
            return (0 if t == here else 1 if t == last else 3 if not t else 2, self.where_name(t).lower())
        out = []
        crew = [m for m in self.player.party if m.get("permanent") and not m.get("story")]
        if crew:                                             # (f299) the people travelling with you, first
            out.append({"town": "Travelling with you", "tag": "", "people": [
                {"name": m["name"], "role": f"hired {m.get('role', '')}", "place": "with you",
                 "line": f"{(m.get('people') or 'human').replace('_', '-').capitalize()} {m.get('role', '')}, rank {m.get('rank', 'F')}, level {m.get('level', 1)}: "
                         f"{m.get('blurb', '')}; {self.temper_text(m)}."} for m in sorted(crew, key=lambda x: x['name'].lower())]})
        for t in sorted(groups, key=rank):
            tag = "here" if t == here else "last visited" if t == last else ""
            people = []
            for n in sorted(groups[t], key=lambda x: (x["name"] if isinstance(x, dict) else x.name).lower()):
                if isinstance(n, dict):
                    people.append(n)
                    continue
                people.append({"name": n.name, "role": n.role.replace("_", " "), "place": self.where_name(n.location),
                               "line": self.journal_line(n, self.where_name(t) if t else "")})
            out.append({"town": self.where_name(t) if t else "On the road", "tag": tag, "people": people})
        heard = [{"name": n.name, "by": n.heard_of["by"], "line": n.heard_of["line"]}
                 for n in sorted(self.store.load_npcs([r.id for r in self.store.npc_rows(heard_of=True)]), key=lambda x: x.name.lower())
                 if n.heard_of and not (n.met_player and n.name_known_to_player)]
        known = self.player.character.knowledge
        from engine import matters
        return {"groups": out, "heard": heard, "facts": [self.world.lore[f].text for f in known if f in self.world.lore],
                "history": list(self.player.character.item_history), "matters": matters.journal(self)}

    def prebuff_command(self, rest: str) -> None:
        """#prebuff <names>: the combat buffs you cast as the opening of a fight you start yourself (f247). #prebuff alone shows them;
        #prebuff none clears them. Only buffs you bring (your loadout) can be chosen."""
        from engine import loadout
        c = self.player.character
        buffs = [a for a in loadout.prepared(c) if a.effect.value == "buff" and a.context.value != "out_of_combat"]
        if rest.strip().lower() in ("none", "clear", "off"):
            c.prebuffs = []
            self.store.save_player(self.player)
            console.note("You will start your fights without casting first.")
            return
        if rest.strip():
            want = [w.strip().lower() for w in rest.replace(";", ",").split(",") if w.strip()]
            picked = [a for a in buffs if any(w in a.name.lower() or w == a.id.lower() for w in want)]
            if not picked:
                console.note("None of those is a combat buff you bring. " + (f"You can choose from: {', '.join(a.name for a in buffs)}." if buffs
                                                                               else "You bring no combat buffs."))
                return
            c.prebuffs = [a.id for a in picked]
            self.store.save_player(self.player)
        chosen = [a.name for a in buffs if a.id in c.prebuffs]
        console.note(("When you start a fight yourself, you first cast: " + ", ".join(chosen) + ". Each costs its mana and starts a round shorter."
                      if chosen else "You start your fights without casting first.")
                     + (f" Your combat buffs: {', '.join(a.name for a in buffs)}. Choose with #prebuff <names, separated by commas>." if buffs else ""))

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

    def handled(self, text: str, by: str, **fields) -> None:
        """The typed line went to `by` (an intercept's name, 'combat', or 'interpret'): one row in the turn log (engine/turnlog.py)."""
        from engine import turnlog
        turnlog.record(self.store.meta.turn, text, by, place=self.player.location, **fields)

    def took(self, text: str, by: str) -> None:
        """An intercept took the line before the model saw it: logged under its name, and the turn passes. A question the world had
        asked (f321) is spent too: the next line is not glued to a question the player has moved past."""
        self.handled(text, by)
        self.pending_clarify = None
        self.store.meta.turn += 1

    def handle(self, text: str) -> None:
        self.last_text = text
        self.interpret_calls = []                           # every interpreter call made for this line, kept for the turn log
        from llm import audit
        audit.note_turn(self.store.meta.turn, text)         # the model calls that follow are filed under this turn (f314)
        if self.combat:
            self.combat.turn(text)
            self.took(text, "combat")
            if not self.combat and self.resume_pending:
                self.resume_road()
            return
        for ic in self.INTERCEPT_TABLE:                     # the intercepts, in their declared order (scenes/intercepts.py)
            if getattr(self, ic.method)(text):
                if ic.after:
                    getattr(self, ic.after)()
                console.debug(f"intercept: {ic.name} took the line")
                return self.took(text, ic.name)
        asked = getattr(self, "pending_clarify", None)
        if asked:                                                     # (f321) they were asked a question: this line answers it
            hint = (f"The game asked the player a question about their earlier line \"{asked['text']}\": \"{asked['question']}\". "
                    f"What they have typed now answers it. Read the earlier line and this answer together as one intention, and plan that.")
            plan = self.interpret(text, hint)
            text = f"{asked['text']} - {text}"
        else:
            plan = self.interpret(text)
        raw_plan = [a.model_dump(exclude_defaults=True) for a in plan]
        if markup.has_markup(text):
            for a in plan:
                if a.speech:
                    a.speech = markup.scrub_speech(a.speech, text)
            plan = [a for a in plan if not (a.kind == "talk" and not a.speech)] or plan
        plan = [a for k, a in enumerate(plan)              # (f299) "...and I talk to the clerk": a wordless talk to whoever the line already spoke to adds nothing
                if not (k and a.kind == "talk" and not (a.speech or "").strip() and any(b.kind == "talk" and b.target == a.target for b in plan[:k]))] or plan
        self.buffering, self.pending, self.halted = len(plan) > 1, [], False
        here_ids = {n.id for n in self.present}
        plan = [a for k, a in enumerate(plan)
                if not (a.kind == "move" and any(b.kind in ("talk", "give", "show", "buy", "sell", "commission")
                                                 and b.target in here_ids for b in plan[k + 1:]))] or plan
        if not self.rank and self.clerk_here() and not NEGATED.search(text.lower()):     # paying or asking to join the guild, said to the clerk, is joining - and only once
            asking = text.strip().lower().startswith(("how", "what", "where", "can ", "could ", "do ", "does ", "is ", "are ")) or "?" in text
            for a in plan:
                low = f"{text} {a.summary}".lower()
                at_desk = mentor.stage(self.player) == "sign"   # at the clerk's desk with Maren, 'I pay' can only mean one thing (f271)
                about_guild = at_desk or any(w in low for w in ("guild", "registry", "register", "registration", "membership"))
                if about_guild and (at_desk or a.kind in ("talk", "buy", "give", "other")) and not asking \
                        and (any(w in low for w in ("join", "fee", "pay", "sign", "enrol", "enroll", "register"))
                             or (at_desk and (a.kind == "give" or any(w in low for w in ("hand", "give", "silver", "coin"))))):   # at the desk, handing the coin over is paying (f282)
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
                    and not NEGATED.search(text.lower()) and not PAST.search(text.lower()) \
                    and any(w in f"{text} {a.summary}".lower() for w in self.BRIBE_WORDS):
                m = re.search(r"(?:\d+|[a-z]+)\s+(?:gold|silver|copper)(?:\s+(?:and\s+)?(?:\d+|[a-z]+)\s+(?:gold|silver|copper))*", text.lower())
                a.kind, a.item = "give", (m.group(0) if m else "coins")
        HARVEST_WORDS = ("harvest", "skin", "butcher", "gut", "carcass", "hide", "meat", "parts", "gather")
        plan = [a for k, a in enumerate(plan)       # skinning and harvesting is one action: a second "other" restating it is dropped
                if not (a.kind in ("other", "harvest") and k and any(b.kind == "harvest" for b in plan[:k])
                        and any(w in f"{a.summary} {a.item}".lower() for w in HARVEST_WORDS))] or plan
        plan = self.audit_plan(text, plan, raw_plan)
        if plan is None:                            # the audit could not make sense of it: nothing happens, no time passes; the world has asked (f321)
            self.buffering = False
            return
        self.pending_clarify = None                 # (f321) read, whether first time or as the answer to a question
        self.sneaking, self.queued_buffs, self.fight_text = False, [], text      # what a fight the player starts this turn opens with (f248)
        for i, intent in enumerate(plan):
            if i and (self.combat or self.halted):
                console.debug(f"stopping after {i} of {len(plan)} actions")
                break
            console.debug(f"intent {i + 1}/{len(plan)}: {intent.model_dump(exclude_defaults=True)}")
            self.pending_check, self.pending_beats = "", []
            if not self.run_checks(intent, text):
                from engine import actions
                if intent.kind not in actions.BY_KIND:
                    console.debug(f"no such action kind: {intent.kind}")
                    self.halted = True
                    break
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
        from engine import matters
        matters.on_arrival(self)                                 # (f317) after the turn's own passage: a moment walked into, or someone come looking
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
            console.ledger(f"Remembered here: {mark}")

    FIGHT_LOCKED = ("goto", "goroad", "maproad", "mapgo", "shopbuy", "shopsell", "boardaccept", "boardabandon", "boardrequest", "boardjoin", "boardhire")

    def command(self, text: str) -> None:
        name = text[1:].strip().lower()
        if self.combat and name.split()[0] in self.FIGHT_LOCKED:      # a pane button cannot walk, shop or sign up in the middle of a fight
            console.note("Not in the middle of a fight.")
            return
        if name == "stats":
            self.show_stats()
        elif name.split()[0] == "events":                   # the event log (storage event_log): what happened, in order; '#events <id>' for one person
            who = name[6:].strip()
            rows = self.store.journal_tail(25, actor=who) if who else self.store.journal_tail(25)
            console.note("Nothing has happened yet." if not rows else "\n".join(
                f"  day {clock.day(r['minute'])}: [{r['kind']}] {r['text']}" + (f"  ({r['actor']} -> {r['target']})" if r['actor'] or r['target'] else "") for r in rows))
        elif name == "check":                               # is the campaign consistent as a world (storage/invariants.py)? Repairs nothing.
            from storage import invariants
            problems = invariants.validate_campaign(self.store, self.world)
            console.note("The campaign checks out: nothing inconsistent found." if not problems else
                         f"{len(problems)} problem{'s' if len(problems) != 1 else ''} found:\n" + "\n".join(f"  - {p}" for p in problems[:40]))
        elif name == "resetlayout":
            console.note("#resetlayout puts the info pane's buttons back in their original order. It works in the game window, where you can drag the buttons.")
        elif name in ("system", "sys", "character"):
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
        elif name.split()[0] == "useitem":
            if not self.combat:                                  # (f327) the pack's Use button: the same as saying 'drink a draught'
                from types import SimpleNamespace
                what = text.strip().split(maxsplit=1)[1] if " " in text.strip() else ""
                self.on_use(SimpleNamespace(item=what), what)
                with console.scope("#inventory"):
                    console.show_inventory(self.player.character)
                self.show_header()
            else:
                from types import SimpleNamespace
                self.combat.free_item(SimpleNamespace(item=text[1:].strip().split(maxsplit=1)[1] if " " in text.strip() else ""), "")
        elif name.split()[0] in ("compname", "name"):
            self.rename_companion(text)
        elif name in ("journal", "j"):
            self.show_journal()
        elif name.split()[0] in ("prebuff", "opener"):
            self.prebuff_command(text.strip().split(maxsplit=1)[1] if " " in text.strip() else "")
        elif name.split()[0] in ("book", "spellbook", "loadout", "prepared"):
            from engine import loadout
            console.note("\n".join(loadout.lines(self.player.character, clock.day(self.minutes), bool(self.combat))))
        elif name.split()[0] in ("prepare", "bring"):
            from engine import loadout
            rest = text.strip().split(maxsplit=1)[1] if " " in text.strip() else ""
            tokens = [t for t in rest.replace(";", ",").split(",")] if "," in rest or ";" in rest else rest.split() if all(x.isdigit() for x in rest.split()) else [rest]
            c = self.player.character
            console.note(loadout.change(c, loadout.by_number(c, tokens), clock.day(self.minutes), bool(self.combat)))
            self.store.save_player(self.player)
            console.note("\n".join(loadout.lines(c, clock.day(self.minutes), bool(self.combat))))
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
            self.show_board()
        elif name == "standing":
            self.show_standing()
        elif name == "rumors":
            self.show_rumors()
        elif name.split()[0] == "correct":
            self.correct_rumor(name.split(maxsplit=1)[1] if " " in name else "")
        elif name == "pulse":
            self.show_pulse()
        elif name == "audit":                              # where this session's record of every model call is (f314)
            from llm import audit
            console.note(f"Audit log: {audit.summary()}")
        elif name == "refusals":                           # the lines the game could not act on this session (f321)
            from engine import refusals
            console.note(refusals.summary())
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
        elif name.split()[0] == "goroad":
            self.goroad_click(text)
        elif name.split()[0] == "maproad":
            self.goroad_click(text.replace("#maproad", "#goroad", 1), back_to="map")
        elif name.split()[0] == "goto":
            self.places_click(text)
        elif name.split()[0] == "mapgo":
            self.places_click(text.replace("#mapgo", "#goto", 1), back_to="map")
        elif name.split()[0] in ("boardaccept", "boardabandon", "questabandon", "boardrequest", "boardjoin", "boardhire"):
            self.board_click(text)
        elif name.split()[0] in ("gearequip", "gearunequip"):
            self.gear_click(text)
        elif name in ("gear", "equipment", "worn"):
            self.show_gear()
        elif name in ("shop", "store", "wares", "buy"):
            self.show_shop()
        elif name in ("stash", "box", "itembox"):
            here = "here" if self.can_store() else "not reachable here - find an inn with storage"
            if console.panel("stash", {"reachable": self.can_store(), "where": self.place.name, "count": len(self.player.stash), "cap": self.stash_cap(),
                                       "items": console.item_rows(self.player.stash)}):
                return
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
        """Who is here, as the player knows them: one list for the narrator, the interpreter and the audit (engine/truth.py, f313)."""
        from engine import truth
        return [(p.label, p.desc, p.doing) for p in truth.scene_of(self).present_people() if p.kind != "wildlife"]

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
        strict = voice_rules.NOTHING in event
        from engine import truth
        here = truth.scene_of(self).view(truth.NARRATOR, "narrator")
        prof = self.world.town(self.player.location)
        seen = self.__dict__.setdefault("_happenings_seen", set())
        unseen = [h for h in here.lines("happenings") if (self.player.location, h) not in seen]    # (f323) told once, and again when it changes
        seen.update((self.player.location, h) for h in unseen)
        unseen = self.__dict__.pop("_arrival_lines", []) + unseen                                  # (f331) what changed here while the player was away, once
        request = wp.narration_request(self.time_label(), self.place, self.people_view(), event, player_text,
                                       self.recent_narration, self.gear_line(), marks,
                                       [inv.label(i) for i in self.ground_here()],
                                       unseen, rule["length"], streets=here.streets(),
                                       town=" ".join(prof.character.split()) if prof and not self.place.danger else "",
                                       news=here.lines("news")[:3])                                 # (f331) the narrator hears what the town is talking about
        result = fresh("narrate", wp.NARRATOR_SYSTEM, request, Narration, self.recent_narration, max_tokens=rule["tokens"],
                       temperature=0.4 if strict else 0.9)
        shown = self.unnamed(result.text)
        if strict and voice_rules.contradicts_nothing(shown):
            console.debug("narration claimed a gain the engine did not give - rewriting once")
            retry = generate("narrate", wp.NARRATOR_SYSTEM,
                             request + "\n\nYOUR DRAFT CLAIMED SOMETHING WAS GAINED, MADE OR FINISHED. Nothing was. Rewrite it so the player only "
                                       "tries: no coins, no objects appearing, no work completed, no change to their purse or pack.",
                             Narration, temperature=0.2, max_tokens=rule["tokens"])
            shown = self.unnamed(retry.text)
            if voice_rules.contradicts_nothing(shown):
                shown = voice_rules.ATTEMPT_ONLY
        if "gasp" in event or "breath" in event:
            shown = voice_rules.mention_once(shown, ("gasp", "gasped", "gasping"))
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
        been, heard = mapview.known(w, self.player.visited, here, self.player.heard)
        far = [r for pid in (been | heard) if pid != top for r in [row(pid, "visited" if pid in been else "heard")] if r]
        key = lambda r: (r["minutes"], r["name"])
        return {"here": here, "town": w.places[top].name, "here_name": w.places[here].name,
                "local": sorted(local, key=key), "far": sorted(far, key=key), "roads": self.road_rows()}

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
        for r in data.get("roads", []):
            console.note(f"  Road {r['dir']}: {r['name'].lower()} - leads somewhere you have not been")

    def places_click(self, text: str, back_to: str = "places") -> None:
        """The pane's hidden command:  #goto <place id>  (#mapgo from the map pane, which redraws the map instead of the places list)."""
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
            if back_to == "map":
                with console.scope("#map"):
                    self.show_map()
            else:
                with console.scope("#exits"):
                    self.show_places()

    def show_map(self) -> None:
        """The map pane: the places you have been and the ones they lead to, and how far each is from here."""
        data = mapview.view(self.world, self.player.visited, self.player.location, clock.describe_duration, self.player.heard)
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

    def people_elsewhere(self) -> list:
        """Everyone the player has met who is not here: from the index, not the records (storage.campaign.NPCRow)."""
        from engine import retrieval
        return retrieval.met_elsewhere(self.store, [n.id for n in self.present])

    def interpret(self, text: str, hint: str = "") -> list[ActionIntent]:
        """What the player typed, read into actions. The interpreter is shown only what the words could be about (engine/candidates.py):
        this town and its ways out plus any place named or close in meaning, the people met who are named, and a catalogue (wares, the
        pack, abilities...) only when the words are about that kind of thing."""
        from engine import candidates as cand
        places = cand.places(self.world, self.player.location, text)
        from engine import truth
        _sc = truth.scene_of(self)
        people = [(p.id, p.label, f"{p.role}. {p.plain} {p.doing}" + (f" {p.note}" if p.note else "")) for p in _sc.present_people() if p.kind == "npc"]
        away_rows = self.people_elsewhere()
        shown_away = cand.people_elsewhere(away_rows, text)
        left = next((n for n in away_rows if n.id == self.last_spoken and n.location == self.player.location and n.away_until > self.minutes), None)
        if left is not None and all(n.id != left.id for n in shown_away):
            shown_away.append(left)                       # the one who just walked off is always listed: "wait for them" must resolve
        elsewhere = [(n.id, f"{n.label()} ({n.role.replace('_', ' ')})",
                      "just walked away from here and can't be spoken to for a short while"
                      if n.location == self.player.location and n.away_until > self.minutes else self.where_name(n.location))
                     for n in shown_away]
        last = self.last_spoken if left or any(n.id == self.last_spoken for n in self.present) else None
        people = people + [(p.id, f"{p.label} ({p.note})", f"{p.desc} {p.doing}.") for p in _sc.present_people() if p.kind in ("maren", "hire")]
        people = people + [(p.id, p.label, p.desc) for p in _sc.present_people() if p.kind == "wildlife"]
        short = cand.I["always_if_short"]
        wares_all = [f"{w.id} from {n.id}: {w.name} - {money.words(w.price)} (sold by {n.label()})"
                     for n in self.present for w in self.world.roles[n.role].sells] \
            + [f"{i.name} from {n.id}: {i.rarity}, level {i.item_level} - {money.words(p)} (stock)" for n, i, p in self.stock_here()]
        from engine import loadout
        abilities_all = [f"{a.id}: {a.name} ({a.field_use or a.effect.value}{', in a fight' if a.context.value == 'combat' else ''})"
                         for a in loadout.prepared(self.player.character)]
        pack_all = [inv.label(i) for i in self.pack]
        recipes_all = [inv.GOODS[next(iter(r.makes))].name for r in inv.RECIPES.values()]
        buyers_all = [f"{n.id} ({n.label()}) buys {', '.join(self.world.roles[n.role].buys)}" for n in self.present if self.world.roles[n.role].buys]
        stash_all = [inv.label(i) for i in self.player.stash] if self.can_store() else None
        shown = {"wares": cand.catalogue(text, "wares", wares_all, short), "abilities": cand.catalogue(text, "abilities", abilities_all, short),
                 "pack": cand.catalogue(text, "pack", pack_all, short), "recipes": cand.catalogue(text, "recipes", recipes_all, short),
                 "buyers": cand.catalogue(text, "buyers", buyers_all, short),
                 "stash": cand.catalogue(text, "stash", stash_all, short) if stash_all is not None else None}
        left_out = [k for k, full in (("wares", wares_all), ("abilities", abilities_all), ("pack", pack_all), ("recipes", recipes_all),
                                      ("buyers", buyers_all), ("stash", stash_all or [])) if full and not shown[k]]
        req = wp.interpret_request(self.time_label(), self.place.name, places, people, elsewhere,
                                   self.partner.id if self.partner else None, last, text,
                                   shown["wares"], shown["abilities"], shown["pack"], [inv.label(i) for i in self.ground_here()],
                                   shown["stash"] if stash_all is not None else None, shown["buyers"], shown["recipes"],
                                   [k.name for k in self.player.character.key_items],
                                   markup.describe(text) if markup.has_markup(text) else "", hint,
                                   [f"{b['n']}. [{b['letter']}] {b['title']}" for b in self.board_data()["postings"]]
                                   if self.clerk_here() else (),
                                   [f"[{q['letter']}] {q['title']}" for q in self.player.quests], left_out=left_out)
        self.last_interpret = {"chars": len(wp.INTERPRET_SYSTEM) + len(req), "places": len(places), "people_away": len(elsewhere),
                               "of_places": len(self.world.places) - 1, "of_people_away": len(away_rows), "left_out": left_out}
        actions = generate("interpret_action", wp.INTERPRET_SYSTEM, req, ActionPlan, temperature=0.2, max_tokens=700).actions
        self.__dict__.setdefault("interpret_calls", []).append({          # the call in full, for the turn log and a lossless replay case
            "hint": hint, "place": self.player.location, "place_name": self.place.name,
            "roles": {p.id: p.role for p in _sc.present_people() if p.kind == "npc"},
            "partner": self.partner.id if self.partner else "", "last_spoken": last or "",
            "places": [pid for pid, _ in places], "people": [p[0] for p in people], "elsewhere": [e[0] for e in elsewhere],
            "shown": {k: v for k, v in shown.items() if v}, "left_out": left_out, "chars": self.last_interpret["chars"],
            "request": req, "plan": [a.model_dump(exclude_defaults=True) for a in actions]})
        return actions

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
    # who works in a kind of building: in a town with no such building, "go to the smithy" means walk over to them
    ROLES_OF = {"smithy": ("smith",), "inn": ("innkeeper", "server", "cook"), "temple": ("priest", "acolyte"),
                "guild": ("guild_clerk", "guild_master", "guild_contractor"), "guardpost": ("watch_captain", "guard"),
                "shop": ("merchant", "chandler", "herbalist", "baker", "butcher", "quartermaster"),
                "workshop": ("tinker", "engineer", "enchanter"), "yard": ("caravan_master",)}

    def local_person(self, dest: str, kind: str = ""):
        """Someone here who is what the player means: a person's id, a role word ('the smith'), or whoever works in that kind of building."""
        d = dest.lower().strip().replace("the ", "", 1).replace(" ", "_")
        for n in self.present if d else ():
            if n.id == dest or n.role == d or d in n.label().lower().replace(" ", "_"):
                return n
        for role in self.ROLES_OF.get(kind, ()):
            for n in self.present:
                if n.role == role:
                    return n
        return None

    def walk_over(self, npc) -> None:
        self.end_conversation()
        self.last_spoken = npc.id
        console.note(f"You walk over to {npc.label()}.")
        self.halted = False

    def names_far_place(self, dest: str, text: str) -> bool:
        """Do the player's own words name this place (or its town)? A bare noun like 'the smithy' does not."""
        from engine import mapview
        w = self.world
        said = set(re.findall(r"[a-z]+", text.lower()))
        target = w.places[dest]
        town = w.places.get(mapview.top_of(w, dest))
        words = {t for t in re.findall(r"[a-z]+", f"{target.name} {town.name if town else ''}".lower()) if len(t) > 3 and t not in self.GENERIC_WORDS}
        return bool(words & said)

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
            person = self.local_person(dest)
            if person:
                self.walk_over(person)
                return
            if not any(dest.lower() in pl.name.lower() or dest == pl.id for pl in self.world.places.values()):
                if self.place.danger or self.place.type in ("hut", "camp", "grove", "spring", "shrine", "ford", "cabin", "cave",
                                                            "ruin", "hollow", "overlook") or self.looks_like_exploring(dest, text):
                    intent.seek = intent.seek or dest
                    self.on_explore(intent, text)
                    return
                console.debug(f"'{dest}' is not a place - stopping the action chain")
                console.note("There's no such place.")
                self.halted = True
                return
        if dest in self.world.places:
            from engine import mapview
            dest = self.nearest_alike(dest, text)
            far = mapview.top_of(self.world, dest) != mapview.top_of(self.world, self.player.location)
            if far and text.strip() and self.world.places[dest].type in self.BUILDING_TYPES and not self.names_far_place(dest, text):
                here_town = self.world.places[mapview.top_of(self.world, self.player.location)].name
                person = self.local_person("", self.world.places[dest].type)
                if person:                                         # this town has no such building, but it has the person who would work in one
                    self.walk_over(person)
                    return
                tgt = self.world.places[dest]
                found = self.world.path(self.player.location, dest)
                away = f", {clock.describe_duration(found[1])} away" if found else ""
                console.note(f"There is no {tgt.type} in {here_town}. The nearest is {tgt.name} in "
                             f"{self.world.places[mapview.top_of(self.world, dest)].name}{away}. Say where you want to go to head there.")
                self.halted = True
                return
        self.travel_route(dest, text)

    def travel_route(self, dest: str, text: str, already: int = 0, events: int = 0) -> None:
        """Walk the quickest way to dest. `already` is time already spent on the way (a fork's shared stretch), taken off the walk."""
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
        walk = max(1, walk - already)
        walk, fatigue_factor = self.take_haste(walk)
        fatigue_factor *= self.take_swift(walk)
        self.travel_fatigue(walk, fatigue_factor)
        self.end_conversation()
        self.last_spoken = None
        console.debug(f"walking {walk} minutes: {' -> '.join(route)}")
        self.run_journey(route, walk, text, events)

    def on_look(self, intent: ActionIntent, text: str) -> None:
        from engine import matters
        if intent.seek and matters.try_find(self, text):          # (f317) looking for something, where a matter's find path points
            return
        room = (" The player has rented a small room upstairs here; if their words take them to it, describe the "
                "room - simple, private, theirs for the night. " if self.has_room() else "")
        self.narrate(
            room + "The player looks closely, focusing on what their words ask about. Answer that directly first, from what "
            "can actually be seen: if they ask about the people, describe their peoples, looks and manner. Mention only "
            "the people relevant to what they are looking at. Three to five sentences.", text)
        self.show_exits()

    def on_talk(self, intent: ActionIntent, text: str) -> None:
        hire = self.hire_by_id(intent.target)
        if hire and not self.mentor_with_you():
            self.hire_talk(hire, intent.speech or text)
            return
        if self.mentor_wants_talk(intent, text):
            self.mentor_talk(intent.speech or text)
            return
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
            from engine import court
            if court.is_gated(self.world, resident) and not court.admitted(self, resident.location):
                console.note(court.absent_line(self, resident))                  # (f320) behind a door that has not opened to them
                self.halted = True
            elif resident.away_until > self.minutes:
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
            self.ask_back("talk_whom", text, f"said to no one in particular; here: {here}")          # (f321) the world asks who they mean
            self.halted = True
            return
        if not self.partner or self.partner.id != npc.id:
            self.end_conversation()
            self.partner = npc
        self.last_spoken = npc.id
        self.player.mentor["last_voice"] = False
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
        from engine import matters, court, stakes
        matters.bind_for(self.store, self.world, npc)                    # (f317) a clue written for their role settles on them
        ctx = (self.npc_context(npc) + self.local_knowledge(npc) + matters.talk_lines(self, npc)
               + court.keeper_lines(self, npc, speech) + court.gated_lines(self, npc)    # (f320) the door, and what is behind it
               + stakes.talk_lines(self, npc))                                          # (f322) the job they put on the board
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
        from engine import truth
        view = truth.scene_of(self).view(truth.viewer_for_npc(npc, self.world), "townsfolk")
        console.debug(f"truth view for {npc.name}: " + ", ".join(f"{h.split(' (')[0].lower()} {len(l)}" for h, l in view.sections()))
        reply, revealed = converse(npc, self.store, self.world, self.catalog, self.convo,
                                   f"{speech} {check_note}".strip(), ctx, level, truth_text=view.text(), known=view.scene.known_words())
        if reply.intent == "leave" and not has_parting(reply.speech):
            reply.intent = "small_talk"            # nobody walks off without a word: no goodbye or dismissal in the speech, no leaving
        self.convo += [("Stranger", speech), (npc.name, reply.speech)]
        if note_due and reply.journal_note.strip():
            npc.journal_note = " ".join(reply.journal_note.split())[:240]
            npc.note_trust, npc.note_mem = npc.trust, npc.memory_total + sum(1 for m in npc.memories if m.id is None)
        self.orenna_named(speech)
        self.hear_names(reply.speech)
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
            if fact_id not in known and not fact_id.startswith("clue:"):
                known.append(fact_id)
                console.debug(f"player learned: {fact_id}")
        for clue in matters.mark_found(self, npc, revealed):              # (f317) a clue carried by their words is found: the matter is in the journal
            console.ledger(f"Noted: {clue}")
        matters.spoke(self, npc)
        self.secret_after(npc, pending_secret)
        if reply.intent == "leave" and reply.speech.rstrip().rstrip('"\'').endswith("?"):
            reply.intent = "small_talk"            # someone who has just asked a question has not walked away
        if reply.intent == "leave" and npc.role in ("guild_clerk",):
            reply.intent = "small_talk"            # the clerk stays at the desk: the guild must stay reachable
        if reply.intent == "leave" and npc.id not in self.player.prisoners:
            console.narrate(f"{npc.label().capitalize()} lets the talk end there and steps away.")        # (f325) fiction, not a system note
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
                console.narrate(f"You step away from {partner.label()}.")
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
        from engine import loadout
        brought = loadout.prepared(c)
        ability = next((a for a in brought if a.id == intent.ability), None) or \
            next((a for a in brought if a.name.lower() in text.lower()), None)
        left = next((a for a in loadout.book(c) if a.id == intent.ability or a.name.lower() in text.lower()), None)
        if not ability and left is not None:
            console.note(f"{left.name} is in your book, but you did not bring it. (#book to see what you bring; #prepare to change it, out of a fight, once a day.)")
            self.halted = True
            return
        if not ability:
            named = (intent.ability or "").strip()
            if named and not any(named.lower() in (a.name.lower(), a.id.lower()) for a in c.actives):
                console.note(f"You don't have an ability called '{named}'.")
                self.halted = True
                return
            self.on_other(intent, text)
            return
        craft_words = ("craft", "forge", "smith", "make", "brew", "temper", "work the", "hammer", "sew", "tan", "cook")
        if ability.effect.value == "crafting" and ability.name.lower() not in text.lower() \
                and not any(w in text.lower() for w in craft_words):
            console.debug(f"{ability.name} is a crafting ability and they aren't crafting - looking instead")
            self.on_look(intent, text)
            return
        if ability.context.value == "combat":
            if self.wildlife and ability.effect.value == "buff":       # it goes up as the fight they start this turn begins (f248)
                if ability.id not in self.queued_buffs:
                    self.queued_buffs.append(ability.id)
                console.note(f"You ready {ability.name} - it goes up the moment you strike.")
                return
            if self.wildlife:                                        # a fighting ability turned on something hostile starts the fight with it
                self.on_attack(intent, text, opener=ability.id)
                return
            console.note(f"{ability.name} is a fighting technique - save it for a fight"
                         + (" (name it as you start one, or set it with #prebuff)." if ability.effect.value == "buff" else "."))
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
        if effect == "summon" and ability.summon_form == "bound":
            from engine import summons
            result = summons.form_outside(c, ability)        # makes the Bound summon anew, or switches the bond to this one
        elif effect == "summon":
            setattr(c, pool, pools.current(c, pool) + cost)
            result = "There is nothing to fight here; what it makes lasts only a few moments in a fight. Describe it flickering and fading."
        elif effect == "crafting":
            self.craft_boost = {"light": 8, "moderate": 15, "heavy": 25}[ability.tier.value]
            result = "Their next piece of work will be better for it."
        elif effect == "healing":
            top = pools.maximum(c, "health")
            from engine import healing as _heal
            gain = top * _heal.H["outside"][ability.tier.value] / 100
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
        if self.owns("gossips_ear"):                        # (f313) the news itself is in the truth view (NEWS THAT HAS REACHED HERE)
            lines.append("You like passing on news to the stranger - tell them what you've heard without being asked.")
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
        if self.mentor_search():
            return
        if self.place.type == "dungeon" and self.player.delve:
            self.dungeon_search(text)
            return
        from engine import matters
        if matters.try_find(self, text):                          # (f317) a matter's find path points here
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
                self.combat = CombatScene.begin(self, creature, enemies, "You find the trail of your quarry:", initiated=True)
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

    def fight_buffs(self) -> list[str]:
        """The combat buffs the player named as they started a fight this turn - readied by name, or named in what they wrote (f248)."""
        from engine import loadout
        text = (getattr(self, "fight_text", "") or "").lower()
        ids = list(getattr(self, "queued_buffs", None) or [])
        for a in loadout.prepared(self.player.character):
            if a.effect.value == "buff" and a.context.value == "combat" and a.name.lower() in text and a.id not in ids:
                ids.append(a.id)
        return ids

    def on_attack(self, intent: ActionIntent, text: str, opener: str = "") -> None:
        if self.wildlife:
            creature, enemies = self.wildlife
            self.wildlife = None
            self.combat = CombatScene.begin(self, creature, enemies, "You attack", initiated=True)
            if opener and self.combat is not None and not self.combat.fight.over:      # the ability they named is the first blow
                from llm.contracts import CombatIntent
                self.combat.turn(text, forced=CombatIntent(kind="ability", ability=opener))
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
            temple = self.place.type == "temple" and (self.owns("sanctuary") or self.owns("pious_path"))
            if self.place.type == "temple" and self.owns("pious_path"):
                self.pious_hospitality()
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
        if not hit:
            self.rest_quirks(sleeping)
        if not hit and self.player.party:
            self._banter_due = "rest"
        if hit:
            creature, enemies = hit
            if creature.temperament == "territorial" or self.sees_far():
                for e in enemies:
                    e.starts_far = True
            self.combat = CombatScene.begin(self, creature, enemies, "While you wait,")

    def on_other(self, intent: ActionIntent, text: str) -> None:
        """(f321) What the interpreter could not name is an improvisation: read for what it is after, rolled, and made true either way."""
        from engine import world_improv
        world_improv.resolve(self, intent.summary or text, text)


from scenes import intercepts as _intercepts                                     # noqa: E402
WorldScene.INTERCEPT_TABLE = _intercepts.gather(WorldScene)                     # declared by the mixins, run in order by handle()
