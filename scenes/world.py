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
from contextlib import contextmanager

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
from engine import regard                                   # (f480) what each person makes of each character
from core.interrupts import Interrupt                      # (f449) stopped on purpose: let through, never rolled back as a fault


class _Void(Exception):
    """(f470) Raised inside an operation that took nothing (op.void): its transaction is rolled back with nothing in it, no record is
    written, nothing it held is shown; it is neither a failure nor a commit."""
from engine.combat import RULES as COMBAT_RULES
from scenes import combat_prompts as cp
from scenes.combat_scene import CombatScene
from scenes.voice import fresh
from scenes.inventory_actions import InventoryActions
from scenes.shop_actions import ShopActions
from scenes.gear_actions import GearActions
from scenes.check_actions import CheckActions
from scenes.work_actions import WorkActions, offer_open
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
from scenes.pastime_actions import PastimeActions
from scenes import plan_repairs
from scenes.plan_repairs import PlanRepairs
from scenes.part_actions import PartActions
from scenes.listening import Listening
from scenes.spell_actions import SpellActions
from scenes import markup
from engine import entities, failures, features, hygiene, ledger, mapview, mentor, needs, pulse, pulselog, questions, quests, roads, turnlog
from engine import inventory as inv
from engine.names import cap_first                      # (f422) a capital first letter, the rest as written
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
UNPAID = re.compile(r"\b(without pay(ing)?|for free|no fee|steal|snatch|forge|by force|force my|swipe)\b")      # (f384) taking it, not joining
PAST = re.compile(r"\b(paid|gave|yesterday|last (week|night|time)|already|before)\b")                        # "the 2 silver I paid you" is no offer
from engine.actions import TIME_COST                 # how long each kind of action takes: declared with the action (engine/actions.py)
from engine import streams
SEARCH = encounters.E


class WorldScene(ExitActions, InventoryActions, ShopActions, GearActions, CheckActions, WorkActions, GuildActions, TrainingActions, DungeonActions,
                 RoadActions, ExploreActions, PropertyActions, MountActions, ArcActions, CampActions, PartyActions, TrialActions, PassiveHooks, FieldActions, AuditActions, LawActions, StandingActions, OrennaActions, MentorActions, StatsActions, BanterActions, QuirkActions,
                 PastimeActions, PlanRepairs, PartActions, Listening, SpellActions):
    def __init__(self, store: CampaignStore, world, catalog: TraitCatalog, player: PlayerState, session=None):
        from engine.session import CampaignSession
        self.session = session or CampaignSession.adopt(store, world)   # (f453) built the old way (a test, a harness): a session of its own over
        self.store = self.session.store                                  # what it was given; (f451) a bare World is wrapped there: one writer
        self.world = self.session.world
        self.catalog = catalog
        self.player = player
        self.residents: list[NPC] = []
        self.present: list[NPC] = []
        self.partner: NPC | None = None
        self.last_spoken: str | None = None
        self.convo: list[tuple[str, str]] = []
        self._talk_saved = store.load_talk()  # (f485) a save opened mid-talk: put back once the one spoken with is here (restore_talk)
        self.to_menu = False          # (f345) #menu: the run loop ends and main.py shows the home page
        self.last_crash = False       # (f449) the last turn rolled back on the game's own fault (logs/crash.log), not the model's
        self.broken: dict[str, int] = {}     # (f449) lines that failed that way, and how often: the second time, the player is told to leave it
        self.recent_narration: list[str] = []
        self.last_text = ""
        self.buffering = False        # several actions in one message: narrate them together
        self.pending: list[str] = []
        self.halted = False           # an action failed or the situation changed: stop the chain
        self.line_ops: list = []      # (f463) the operations of the line being played that committed, in order
        self.line_failed: list = []   # (f463) ...and the one that did not, if any
        self.line_world_failed: list = []   # (f466) the world's own operations of the line that did not stand: rolled back alone, the player told nothing
        self.line_done: list[str] = []   # (f463) what the committed actions did, for the part_stood line
        self.passages: list = []      # (f464) the passages the line's operations queued: [kind, fn, standin, the lines held after their marker, the operation's id]
        self.line_untold: list = []   # (f464) the passage operations of the line that did not stand and were told by a stand-in
        self.unshown_ops: dict = {}   # (f464) operations whose later lines wait on a passage: id -> segments still to release
        self.collecting = False       # (f464) the line's actions are running: a narration is a passage operation of its own, after them
        self.crash_after_commit = ""  # (f467) the suite's injection (simlib.Game.crash_after_commit): the game stops right after this kind's commit
        self.last_budget: dict = {}   # (f468) the last input's budget, closed: what it estimated, deferred, dropped, stood in for (the turn log's)
        self.recovered_at_load = 0    # (f471) outcomes told at this load (recover_unshown): the first row after it says so, the night tool too
        self.combat: CombatScene | None = None
        self.resume_pending = None
        self.wildlife = None
        self.sneaking, self.queued_buffs, self.fight_text = False, [], ""     # a fight the player starts this turn (f248)
        self.recently_fled = False
        self.rng = streams.get("scene")  # (f439) reseeded at every input
        self.last_failure = ""        # (f437) why the last turn the game could not take was rolled back, for the turn log
        pools.fill_missing(self.player.character)
        self.session.bus.journal_everything()   # (f454) every event a row in this campaign's event log, on this campaign's bus
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

    def lying_here(self) -> list[str]:
        """(f592) The things lying where the player stands that the place's marks do not tell (one set down here), for the narrator."""
        from engine import objects
        return objects.lying_unmarked(self.store, self.player.location, self.minutes)

    def carried_things(self) -> list:
        """(f592) The things in the world the acting character carries in hand (engine/objects.py), for the inventory."""
        from engine import objects
        return objects.carried(self.store, self.acting)

    @property
    def acting(self) -> str:
        """(f480) The id of the character whose line is being played. What a person makes of "the player" is what they make of this
        character (engine/regard.py): the one place the scene says which character that is (one today; tools/sim/regard_480_test.py
        names the call sites that read it)."""
        return self.player.character.id

    def notice(self, event, *people) -> None:
        """The world notices a deed of the player's (engine/reactions.py). `people` are the records this code holds for anyone in it, so
        that the reactions change the very objects it will save, whether or not they stand in `present` right now."""
        self._live = {n.id: n for n in people if n is not None}
        from engine import domain_events as _de
        if isinstance(event, _de.Deed) and not event.by:
            import dataclasses
            event = dataclasses.replace(event, by=self.acting)   # (f480) the deed is the acting character's: whom the world remembers it of
        try:
            self.session.bus.publish(event)                 # (f454) this campaign's bus, whichever is current
        finally:
            self._live = {}

    @property
    def party_service(self):
        """The party's mechanics (services/party.py), always over the player's current record (which a rollback reloads)."""
        from services.party import PartyService
        return PartyService(self.player, lambda: self.minutes, self.store.meta.seed, bus=self.session.bus)   # (f454)

    @property
    def place(self):
        return self.world.places[self.player.location]

    @property
    def minutes(self) -> int:
        return self.store.meta.minutes

    def time_label(self) -> str:
        light = " (dark)" if clock.is_dark(self.minutes) else ""
        _, sky = weather.describe(self.store.meta.seed, self.minutes)
        return f"{clock.period(self.minutes)}{light}, weather: {sky.lower()}"           # (f423) no "day N": a passage wrote "on day 42"

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
        if (things := self.carried_things()):                # (f592) things in the world carried in hand
            parts.append(f"holding {', '.join(o.name for o in things)}")
        if getattr(c, "look_text", ""):                    # (f388) how they look, as they chose at the Threshold
            parts.insert(0, c.look_text.rstrip("."))
        return "; ".join(parts)

    def remember_narration(self, text: str, shown: dict | None = None) -> None:
        """Keep what the model should remember, and what the player saw (as pieces, so a reload draws it the same way)."""
        from engine import hygiene
        text = hygiene.undash(hygiene.unstage(hygiene.unnote(text)))   # (f396) what the narrator is shown of itself carries no dashes to copy; (f404) no notes; (f449) no stage directions
        if shown:
            shown = {k: hygiene.undash(hygiene.unstage(hygiene.unnote(v))) if k in ("text", "before", "after") and isinstance(v, str) else v for k, v in shown.items()}
        if text.strip():
            self.recent_narration = (self.recent_narration + [text])[-6:]
            self.store.save_story(self.recent_narration, shown or {"type": "narration", "text": text})
        self.note_worn(text, shown)

    # ---- (f349) the worn-word watch: which words the writing has leaned on lately (engine/worn.py)

    def note_worn(self, text: str, shown: dict | None = None) -> None:
        """Every passage feeds the prose watch; every line of speech feeds the speech watch; a frame feeds both."""
        from engine import worn
        w = self.__dict__.setdefault("_worn", {"prose": worn.Watch(), "speech": worn.Watch()})
        if shown and shown.get("speech"):
            w["speech"].add(shown["speech"])
            w["prose"].add(" ".join(x for x in (shown.get("before", ""), shown.get("after", "")) if x))
        else:
            w["prose"].add(text)

    def worn_words(self, kind: str = "prose") -> list[str]:
        """The words to hand over as WORDS YOU HAVE WORN OUT, less the nouns of this scene (names, labels, the place)."""
        w = self.__dict__.get("_worn")
        if not w:
            return []
        keep = [self.place.name] + [l for l, _, _ in self.people_view()] + [m.get("name", "") for m in self.player.party]
        return w[kind].worn(keep)

    def narrate_with(self, system: str, event: str) -> None:
        event = hygiene.undash(event)                                    # (f413) no dashes to copy (f403)
        self.flush(self.last_text)
        result = fresh("narrate", system,
                       wp.narration_request(self.time_label(), self.place, self.people_view(), event, self.last_text,
                                            self.recent_narration, self.gear_line(),
                                            self.store.load_place(self.player.location).marks, ground=self.lying_here(),
                                            told=ledger.told()),                       # (f416) what the turn did: a fight's opening, a sighting
                       Narration, self.recent_narration)
        console.narrate(result.text)
        self.remember_narration(result.text)
        self._wrote_turn = True                                                                  # (f351) the narrator wrote this turn

    def opening_telling(self, event: str, scene):
        """(f498) The fight's opening as a telling of its own (scenes/combat_scene.py begin marks it a passage): the request is built now,
        as narrate_with built it where the fight began (the hour, the place, who is here, the recent passages, the turn's rows as the
        narrator is given them, ledger.told), so the operation that tells it, run once the fight's commit stands and again when it stands
        down to ask (combat_opening is asked outside, data/rules/budget.yaml), asks in the same words. What is read of the opening is noted
        on the fight as it stands when it is told (note_fight_shown finds the live scene). Returns what mark_passage runs."""
        event = hygiene.undash(event)                                    # (f413) no dashes to copy (f403)
        self.flush(self.last_text)
        request = wp.narration_request(self.time_label(), self.place, self.people_view(), event, self.last_text,
                                       self.recent_narration, self.gear_line(),
                                       self.store.load_place(self.player.location).marks, ground=self.lying_here(),
                                       told=ledger.told())                       # (f416) what the turn did: a fight's opening, a sighting
        recent = list(self.recent_narration)

        def tell():
            result = fresh("combat_opening", cp.START_SYSTEM, request, Narration, recent)
            console.narrate(result.text)
            self.remember_narration(result.text)
            self._wrote_turn = True                                                              # (f351) the narrator wrote this turn
            scene.note_fight_shown(result.text)                                                  # (f349) the opening passage is read
            scene.note_ground_told(opening=True)                                                         # (f571) and the ground it was given is told
        return tell

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
            self.time_note(line)
        rest = needs.N["rest_heal_per_hour"]["safe" if self.safe_to_rest() else "rough"] if wait else 0.0
        pools.recover(c, minutes, conditions=self.conditions(), rest=rest)
        self.store.meta.day = clock.day(self.minutes)
        self.refresh_present()
        if self.partner and self.partner not in self.present:
            self.time_note(f"{self.partner.label(self.acting)} heads off for the day.")
            self.end_conversation()
        if clock.period(self.minutes) != before:
            console.debug(f"time of day is now {clock.period(self.minutes)}")

    def time_note(self, line: str) -> None:
        """(f418) A note that time raised in the middle of a line (someone gone for the day, hunger, weariness) is printed after the
        line's passage, not above it: 'the clerk heads off for the day' was printed before an hour of helping that same clerk with his
        ledger. The owner's decision (GOALS.md, review Q36)."""
        if self.step is not None or self.buffering:
            self.__dict__.setdefault("_time_notes", []).append(line)
        else:
            console.note(line)

    def release_time_notes(self) -> None:
        for line in self.__dict__.pop("_time_notes", []):
            console.note(line)

    def assault_fight_over(self, outcome: str) -> None:
        """(f324) A fight at the gate of a town a cataclysm reached: the outcome decides whether the town holds."""
        from engine import events
        events.assault_over(self, outcome)

    def visit(self, npc, until: int) -> None:
        """(f317) Someone from elsewhere in town is here for a while - they came looking for the player."""
        self.visitors = [v for v in getattr(self, "visitors", []) if v[0] != npc.id] + [(npc.id, until, self.player.location)]
        self.refresh_present()

    def streets_now(self) -> tuple[dict | None, dict]:
        """(f357) What the running situations have the streets doing here, and where they have placed their cast; read once a minute."""
        from engine import threads
        key = (self.player.location, self.minutes)
        cache = self.__dict__.get("_streets_cache")
        if not cache or cache[0] != key:
            state = self.store.load_world_state() or {}
            cache = (key, threads.street_now(state, self.world, self.player.location, self.minutes))
            self.__dict__["_streets_cache"] = cache
        return cache[1]

    def refresh_present(self, assign: bool = True) -> None:
        """Who is here now, from the rows. (f497) assign=False reads and never writes: a give-back (give_back) reloads the present as the
        operation found them and leaves their doings to the next operation, since assigning them saves the row (engine/doings.py), a write
        outside any operation with the fence armed, and a doing changed between the attempt that stood down and its re-run is a drift."""
        from engine import court, routines
        seed = self.store.meta.seed
        street, cast = self.streets_now()                                                               # (f357)
        on_stop = (self.player.road or {}).get("id") == self.player.location         # (f427) whoever the road stopped the player beside is
        self.present = [n for n in self.residents                                     # there, whatever the hour: no shift or routine on a road
                        if not n.gone                                                                     # (f422) the dead and departed are not here
                        and (on_stop or clock.in_hours(self.minutes, self.world.roles[n.role].hours) and n.away_until <= self.minutes
                             and court.visible(self, n) and not routines.away(self.world, seed, n, self.minutes, cast))]   # (f352)
        if self.__dict__.get("_talk_saved") and self.present:
            self.restore_talk()
        bound = self.escorted()                                             # (f392) the registry says who walks bound at the player's side
        for n in self.residents:                                            # a prisoner bound at the player's side is here whatever the hour or the door
            if n.id in bound and not n.gone and all(p.id != n.id for p in self.present):
                self.present.append(n)
        for pid in bound:                                                   # (f386) ...and wherever the player has walked them to: one taken
            if all(p.id != pid for p in self.present) and self.store.npc_exists(pid):     # elsewhere was 'not here'
                n = self.store.load_npc(pid)
                if not n.gone:
                    self.present.append(n)
        here = {n.id for n in self.present}
        self.visitors = [v for v in getattr(self, "visitors", []) if v[1] > self.minutes and v[2] == self.player.location and self.store.npc_exists(v[0])]
        for vid, _, _ in self.visitors:
            if vid not in here:
                v = self.store.load_npc(vid)
                if not v.gone:
                    self.present.append(v)
        here = {n.id for n in self.present}
        self._routine_here = set()                                                                     # (f352) the town's people here on their routine
        key = (self.player.location, clock.day(self.minutes), clock.period(self.minutes))
        cache = self.__dict__.setdefault("_routine_cache", {})
        if key not in cache or cache.get("_cast") != cast:
            cache.clear()
            cache["_cast"] = cast
            cache[key] = routines.visitor_ids(self.store, self.world, seed, self.player.location, self.minutes, cast)
        for vid in cache[key]:
            if vid not in here and self.store.npc_exists(vid):
                v = self.store.load_npc(vid)
                if not v.gone and v.away_until <= self.minutes and court.visible(self, v):
                    self.present.append(v)
                    self._routine_here.add(v.id)
        if self._routine_here and self.__dict__.get("_routine_marked") != key:
            self.__dict__["_routine_marked"] = key
            pulselog.mark("routine", f"{len(self._routine_here)} here on their routine", self.minutes, place=self.player.location)   # (f355)
        if getattr(self, "partner", None):          # residents are reloaded from disk each turn: keep pointing at the same person's fresh copy
            fresh_copy = next((n for n in self.present if n.id == self.partner.id), None)
            if fresh_copy:
                self.partner = fresh_copy
        if not assign:
            return
        from engine import doings, moments                                                    # (f348) what each of them is doing now: the engine's
        self._doing_changes = doings.assign(self.store, self.present, self.minutes, moments.active(self.store, self.player.location, self.minutes) or street,
                                            visiting=self._routine_here, place_type=self.place.type if self.player.location in self.world.places else "")

    def take_up_acts(self, text: str) -> None:
        """(f596) The oldest act this character left waiting for its ruling, ruled on before the new line is read, in an operation of its
        own whose call is asked outside the transaction (engine/act.py take_up); told, then the line plays. Nothing when none waits, or
        when the act path is off."""
        from engine import act
        if not act.on() or self.combat or not act.waiting(self, self.acting):
            return                                         # never in a fight: an act outside combat waits for the fight to end
        said = act.waiting(self, self.acting)[0]["text"]
        op, _ = self.asked_operation("act:waiting", said, lambda op: act.take_up(self, self.acting, text), world=True)
        if op.state != "committed":                        # its operation failed for any reason: one of its tries spent, apart
            with self.operation("act:waiting:missed", said, world=True):
                act.missed(self, self.acting)
        self.run_passages()

    def situation_births(self, text: str) -> None:
        """(f546) After the tail, apart from it, and only when something waits (so an input with nothing born commits what it always did):
        the oldest birth due asks for its parts outside any transaction (engine/situation_parts.py birth), the people here read again
        inside it (f546's second review: every write within an operation); a birth that took none, or whose operation failed for any
        reason, spends one of its tries in an operation of its own (f546's review), so none is asked forever; then the situations with
        no parts to adopt (one past its tries among them) take the engine's own, in an operation with no call."""
        from engine import situation_parts
        th = situation_parts.due(self.store.load_world_state() or {})
        if th is not None:
            tid, why = th["id"], {}

            def _born(op):
                try:
                    if situation_parts.birth(self, tid):
                        self.reread_here()
                except LLMError as e:
                    why["it"] = str(e) or "the model gave nothing usable"
                    raise
            op, _ = self.asked_operation("parts", text, _born, world=True)
            if op.state != "committed":
                with self.operation("parts:missed", text, world=True):
                    situation_parts.missed(self, tid, why.get("it") or "its operation did not stand")
        if situation_parts.adoptable(self.store.load_world_state() or {}):
            with self.operation("parts:adopt", text, world=True):
                situation_parts.adopt_all(self)

    def reread_here(self) -> None:
        """(f546) The people here read again from the save, as after the pulse: within an operation, since placing them may save one."""
        here = self.store.load_place(self.player.location)
        if here.populated:
            self.residents = [n for n in (self.store.load_npc(i) for i in here.residents) if not n.gone]
            self.refresh_present()

    def run_pulse(self) -> None:
        """Let the world move on, then see who is still here. (f466) The pulse may write the player through the save (engine/pulse.py
        remove_npc ties off the quests and commissions of someone gone); when it has, the scene takes the saved player before the drift is
        applied, so the operation's commit of the scene's copy keeps what the pulse did instead of writing over it."""
        from engine import drift, events
        before = self.store._kv_text("player")
        deltas = pulse.catch_up(self.store, self.world, self.catalog, self.minutes) or {}
        if self.store._kv_text("player") != before:
            self.player = self.store.load_player()
            pools.fill_missing(self.player.character)
        drift.apply_player(self.player, deltas)                                                 # (f331) what the drift owes the record this scene holds
        from engine import town_memory
        town_memory.sweep(self.store, self.world, self.player.location, self.minutes)        # (f484) past their term; a settled matter leaves its mark
        self.__dict__.pop("_streets_cache", None)                                           # (f357) the world may have moved: read the streets afresh
        events.apply_player_events(self)
        self.arc_tick()
        here = self.store.load_place(self.player.location)
        if here.populated:
            self.residents = [n for n in (self.store.load_npc(i) for i in here.residents) if not n.gone]
            self.refresh_present()
        from engine import moments
        moments.tick(self)                                                                    # (f348) a moment that has run its minutes ends

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
        threads = [f"[{t['tier']}{', engine-built' + (', re-told' if t.get('told') else '') if t.get('made_by') == 'engine' else ''}] {t['title']} - stage {t['stage'] + 1}/{len(t['stages'])} at {self.where_name(t['place'])}, ends day {clock.day(t['times'][-1])}"
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

    def end_contexts(self, place_id: str) -> None:
        """(f392) What the game believes about where the player is belongs to that place, and ends when they leave it: a delve is its
        dungeon's, the party holding back is the approach's. A night's run walked out of a dungeon with its delve still set; from then on
        every 'move out' was refused as 'You're not down in a dungeon' (46 times), and no companion spoke again, because talk waits
        while a delve is on. Another held its party back at a camp and never called them, so they fought but never spoke."""
        if self.player.delve:
            d = next((x for x in self.store.load_dungeons() if x["id"] == self.player.delve.get("dungeon")), None)
            if d is None or place_id != d["entrance"]:
                self.player.delve = None
        if self.player.party_mode == "hold" and place_id != self.player.party_hold_at:
            self.party_service.set_mode("with")
            if self.player.party:
                console.note("Your party falls in beside you again.")

    def enter(self, place_id: str) -> None:
        self.wildlife = None
        new_town, old_town = pulse.town_of(self.world, place_id), pulse.town_of(self.world, self.player.location)
        if new_town != old_town:
            self.__dict__.setdefault("_happenings_seen", set()).clear()           # (f323) a new town: its happenings are new to the eye
            self.__dict__.pop("_crowd_told", None)                                # (f385) ...and its crowd
            self._framed_hires = set()                                            # (f347) a hire's first words in a new town earn a frame; each shop in it does not
            from engine import ambient
            if self.world.peoples_at(old_town) and old_town in self.world.places and not self.world.places[old_town].danger:
                self.player.last_in[old_town] = self.minutes                       # (f331) when the player last left a town
            self._arrival_lines = ambient.since(self.store, self.world, new_town, self.player.last_in.get(new_town), self.minutes)
        self.leave_road(place_id)
        self.__dict__.pop("_streets_cache", None)                                           # (f357) a new place: read the streets afresh
        self.end_contexts(place_id)
        same_place = place_id == self.player.location
        self.revisit = self.store.load_place(place_id).populated
        self.player.location = place_id
        self.note_town(place_id)
        self.standing_arrive()
        self.first_arrival = place_id not in self.player.visited
        self._framed_here, self._shown_here = set(), {}                    # (f347) a new place: nothing read about it yet, nobody framed
        if self.first_arrival:
            self.player.visited.append(place_id)
            p = self.world.places[place_id]
            if p.type in ("city", "town", "village") or not p.parent:    # (f347) a town or the open country earns a first sight; a shop inside a town does not
                self.weight_hint = "major" if p.type == "city" else "rich"
        elif self.revisit:
            self.weight_hint = "brief"                                   # (f347) seen before: what has changed
        try:
            self.residents = populate_place(self.store, self.world, place_id, self.catalog, first_batch=life.FIRST_BATCH)
        except LLMError:
            from engine import operation as _op
            if _op.current() is not None:
                raise                                    # inside a line: the operation rolls back, as before
            self.residents = [n for n in self.store.load_npcs(list(self.store.load_place(place_id).residents or [])) if not n.gone]
            self._people_missing = place_id              # (f525's review) asked again at the next input's edge while the player is here
            console.debug(f"(f525) the people of {place_id} could not be written; the next input asks again")
        self.refresh_present()
        if self.revisit:                                                                      # (f348) who has moved on to something else since: true change for the narrator
            from engine import doings
            self.__dict__.setdefault("_arrival_lines", []).extend(doings.changed_lines(getattr(self, "_doing_changes", []), who=self.acting))
        from engine import moments
        moments.on_enter(self)                                                                # (f348) a possibility: something going on as they walk in
        self.home_arrival()
        self.arc_enter(place_id)
        self.arrive_parts(place_id, same_place)                             # (f394) its parts, and where in it the player stands
        self.bring_prisoners(place_id)
        self.party_notice()
        self.trial_notice(on_arrival=True)
        from engine import stay
        stay.reset(self)                                                                      # (f351) the stay starts here

    def repopulate(self) -> None:
        """(f525's review) A place whose people could not be written at an entry made outside a line is asked again at each input's edge
        while the player is still there, never left empty for the whole visit; still failing, it is asked at the next edge."""
        place_id = self.__dict__.pop("_people_missing", None)
        if place_id is None or place_id != self.player.location:
            return
        try:
            self.residents = populate_place(self.store, self.world, place_id, self.catalog, first_batch=life.FIRST_BATCH)
        except LLMError:
            self._people_missing = place_id
            return
        self.refresh_present()

    def start_backfill(self) -> None:
        """The scene is on screen and the player is reading: make the rest of this place's people in the background."""
        if life.FIRST_BATCH and not self.combat:
            backfill.start(self.store, self.world, self.catalog, self.player.location)

    def apply_backfill(self) -> None:
        """Add any people the background job has finished to the scene."""
        if not backfill.pending(store=self.store):
            return
        if self.player.location in backfill.collect(self.store, self.world, self.catalog, wait_all=streams.STRICT):   # (f439)
            here = self.store.load_place(self.player.location)
            self.residents = [n for n in (self.store.load_npc(i) for i in here.residents) if not n.gone]
            self.refresh_present()

    def quiet_return(self, log=(), text: str = "") -> bool:
        """(f349) Back somewhere already peopled with nothing new to tell: nobody has moved on to something else, nothing is happening here
        the player has not read, no news has come, nothing was met on the way and the player asked nothing. Then the engine says so in a
        line and the narrator is not called: a passage that says nothing has changed is worse than none."""
        if not getattr(self, "revisit", False) or getattr(self, "first_arrival", False) or log or "?" in (text or ""):
            return False
        if self.__dict__.get("_arrival_lines"):
            return False
        from engine import truth
        here = truth.scene_of(self).view(truth.NARRATOR, "narrator")
        seen = self.__dict__.setdefault("_happenings_seen", set())
        if any((self.player.location, h) not in seen for h in here.lines("happenings")):
            return False
        news_seen = self.__dict__.setdefault("_news_seen", set())
        return not any(h not in news_seen for h in here.lines("news")[:3])

    def stay_tick(self) -> None:
        """(f351) The room changes while the player is in it: one line for the one change worth telling (engine/stay.py)."""
        from engine import stay
        line = stay.tick(self, narrated=getattr(self, "_wrote_turn", False), rng=self.rng)
        if line:
            console.narrate(line)
            self.remember_narration(line)
            pulselog.mark("stay", line, self.minutes, place=self.player.location)                      # (f355)

    def brevity(self) -> str:
        if getattr(self, "revisit", False):
            return (" The player has been here before: the place and its people have been seen. Say what the "
                    "GAME STATE shows has changed since; if nothing has, say only that they are back, and never invent a change.")
        return ""

    # ---- (f347) what the player has read about this place this visit, so the narrator and the frames say what is new

    def note_shown(self, text: str) -> None:
        """Record what a passage printed here gave the player: the place itself, the weather, each present person it described."""
        if not (text or "").strip():
            return
        s = self.__dict__.setdefault("_shown_here", {})
        s.setdefault("people", set())
        s["place"] = True
        low = text.lower()
        if any(re.search(rf"\b{w}\w*", low) for w in voice_rules.V.get("weather_words", [])):
            s["weather"] = True
        paused = bool(voice_rules.PAUSE.search(low))
        for label, _desc, doing in self.people_view():
            key = re.sub(r"^(the|a|an) ", "", label.lower()).strip()
            head = key.split()[-1] if key else ""
            work = [w for w in re.findall(r"[a-z]{7,}", (doing or "").lower())]
            if key and (key in low or (len(head) >= 4 and re.search(rf"\b{re.escape(head)}s?\b", low)) or any(w in low for w in work)):
                s["people"].add(label)                   # the narrator paraphrases an epithet ('a muscular guard'): the noun or their work is enough
                if paused:
                    s.setdefault("paused", set()).add(label)     # (f349) they stopped what they were doing on the page: that is shown once a visit

    def shown_lines(self) -> list[str]:
        """The ALREADY SHOWN THIS VISIT list for the prompts, as plain lines."""
        s = self.__dict__.get("_shown_here") or {}
        out = []
        if s.get("place"):
            out.append(f"the place itself: {self.place.name} has been described; name only what changes")
        if s.get("weather"):
            out.append("the weather and the light")
        out += [f"{p}, and what they are doing" for p in sorted(s.get("people", ()))]
        out += [f"{p} pausing their work to speak: shown once already; from now on the words come while the hands keep at it"
                for p in sorted(s.get("paused", ()))]
        return out

    def open_world(self) -> None:
        """(f466) What the world owes the save as the game opens (the discoveries, homes, the road's place, the dungeons and the field's
        uses kept whole, and the pulse up to now), as one world operation, world:open, under the "#start" dice (f439). Its id is drawn
        before it opens and repeats at the same count of inputs: an open stopped in the middle of it finds nothing committed and runs it
        again; an open after a stood one finds its record and runs nothing, so the load-time pulse never runs twice (survey 12.1). Its
        failure is the world's: rolled back alone, written to logs/crash.log, the player told nothing."""
        from engine import operation as _op
        streams.begin(self.store.meta.seed, self.store.meta.steps, "#start")    # (f439) what happens as the game opens is decided too
        op_id = streams.new_id(_op.ID_DIGITS, stream="ops")
        if self.store.find_operation(op_id) is not None:
            console.debug("the world's opening stands from the last open: not run again")
            return
        self.begin_line()
        try:
            with questions.fence(), self.operation("world:open", "#start", world=True, op_id=op_id):
                self.ensure_discoveries()
                self.ensure_homes()
                self.ensure_road_place()
                self.ensure_dungeons()
                self.ensure_field_uses()
                self.run_pulse()
        finally:
            self.store.arm(False)

    def recover_unshown(self) -> bool:
        """(f467) What stood before the game last closed and was never shown (the operations whose presentation entries are still in the
        save: committed, then the game died before their telling, Bundle C decision 8): shown once, now, oldest first, through the
        installed bindings (the recorder, the turn log and the gate see it as they see any line), after one line that says it is of
        before (engine/failures.py shown_later). Each entry's held calls are made again, mended under this load's cast (engine/names.py
        mend_pronouns); an entry with no held lines, or whose passage was never written (a marker), is followed by plain lines of what
        its rows record, filled from their facts (failures.stood_lines). Then its entry goes (mark_shown): nothing waits past one load.
        No model call is made. True when something was recovered."""
        from engine import names, operation as _op
        pending = self.store.unshown()
        if not pending:
            return False
        order = {o["id"]: i for i, o in enumerate(self.store.load_operations()["ops"])}
        ids = sorted(pending, key=lambda i: (pending[i].get("steps", 0), order.get(i, -1)))

        def mended(x):
            return names.mend_pronouns(x) if isinstance(x, str) else x

        console.narrate(failures.shown_later(self.rng))
        for op_id in ids:
            entry = pending[op_id]
            calls = entry.get("calls")
            if calls is None:                                          # an entry from before the calls were kept: its lines, as narration
                calls = [["narrate", [line], {}] for line in entry.get("lines", [])]
            untold = not calls or any(c[0] == "marker" for c in calls)
            for name, a, k in calls:
                fn = getattr(console, name, None) if name != "marker" else None
                if fn is not None:
                    fn(*[mended(x) for x in a], **{kk: mended(v) for kk, v in k.items()})
            if untold:
                rec = self.store.find_operation(op_id) or {}
                rows = [r for r in rec.get("rows", []) if r.get("facts")]
                for line in failures.stood_lines(rows, self.rng) if rows else []:
                    console.narrate(mended(line))
            self.store.mark_shown(op_id)
            _op.present(op_id, "recovered")
        self.recovered_at_load = len(ids)
        self.__dict__["_recovered_unreported"] = len(ids)
        return True

    def run(self) -> None:
        self.open_world()
        recovered = self.recover_unshown()                                  # (f467) first: what stood before the game last closed, never shown
        first_time = self.store.meta.turn == 0
        self.enter(self.player.location)
        self.weight_hint = "major" if first_time else None                 # a reload narrates nothing on entering; the next passage is weighed on its own
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
            self.opening_passage(
                "The player has just woken here, lying on the ground, returned from death. "
                f"They remember the Threshold only faintly. {kit_text} Their first breath tears in. "
                "Open with that single breath, described once (mention the gasp only once in the whole passage), "
                "then describe what they see."
            )
        else:
            saved, shown = self.store.load_story()
            if shown:
                self.recent_narration = saved[-6:]
                if recovered:
                    pass                                                   # (f467) the remembered passage is of before what was just told: not shown again (owner question 12)
                elif shown.get("type") == "dialogue":
                    console.dialogue(shown.get("before", ""), shown.get("speaker", ""), shown.get("speech", ""), shown.get("after", ""))
                elif shown.get("type") == "says":
                    console.npc_says(shown.get("speaker", ""), shown.get("speech", ""), shown.get("gesture", ""))
                else:
                    console.narrate(shown.get("text", ""))
            elif not recovered:
                self.opening_passage("The player is here, picking up where they left off. Describe the scene, mentioning at most two "
                                     "of the people present.")            # (f413) no length (f375)
            if kit_text:
                c = self.player.character
                held = [i.name for i in c.equipment.values()] + [f"{m.name} ({m.description})" for m in c.companions]
                console.note(f"Checking your belongings, you find: {', '.join(held + [money.fmt(c.coins)])}.")
        self.show_exits()
        let_go = self.store.take_notice("fight_let_go")                     # (f507) a migration let a saved fight go: told once, here
        saved_fight = self.store.load_combat()
        if saved_fight:
            self.combat = CombatScene.resume(self, saved_fight)     # (f503) None for a row that cannot be read: the fight is let go, not the game
            if self.combat is not None:
                console.note("You are still in the middle of a fight!")
                self.combat.show()
            else:
                self.store.save_combat(None)                        # (f507) the row goes with the fight, and the player hears of it once
                let_go = True
        if let_go:
            console.narrate(failures.fight_let_go(self.rng))
        self.show_header()
        asked = self.store.load_question()
        if asked and asked.get("question"):                                 # (f460) the world was waiting on an answer when the save closed: ask again, once
            if asked.get("speaker"):
                console.say(asked["question"], asked["speaker"])             # (f461) in the voice it was asked in
            else:
                console.note(asked["question"])

        while True:
            self.start_backfill()
            text = console.ask(main=True)
            self.apply_backfill()
            self.repopulate()                                               # (f525's review) people an entry could not write, asked again
            if not text:
                continue
            if text.lower() in QUIT_WORDS:
                self.store.save_player(self.player)
                console.note("Saved. Run main.py again to continue.")
                return
            if text.startswith("#"):
                before = self.player.location
                bar = self.header_key()                                     # (f372) what the top bar shows, to redraw it when a button changed it
                turnlog.begin(console)                                      # (f385) a button that does something is a row too
                name = (text[1:].strip().lower().split() or ["command"])[0]
                self.begin_line()
                op = None
                try:
                    with console.scope(text), questions.fence():             # a pane button is a whole operation too: all of it, or none of it (f463)
                        self.new_input(text)                                # (f439) the dice of this input
                        self.collecting = True                              # (f498) a telling it asks for (a fight begun from the pack's button,
                        op, _ = self.asked_operation(f"command:{name}", text, lambda op: self.command(text), where="command")   # a draught's
                        self.run_passages()                                 # passage) is a passage operation after it, told once it stands
                except Interrupt:
                    raise                                                   # (f449) stopped on purpose, never a rolled-back fault
                finally:
                    self.collecting = False
                    self.store.arm(False)
                    from engine import budget
                    self.last_budget = budget.close(stand_ins=[o.kind for o in self.line_untold])   # (f468)
                rolled = op is None or op.state != "committed"
                crashed = rolled and self.last_crash
                if rolled:
                    console.note(self.failed_line(text) if crashed else failures.not_taken(self.rng))    # (f437) in the narrator's words, never the machinery
                failed = self.last_failure if rolled and not crashed else ""
                crash = self.last_failure if crashed else ""
                if self.to_menu:
                    turnlog.end(rolled, command=self.command_row(text, before, bar), failure=failed, crash=crash)
                    self.store.save_player(self.player)
                    return
                self.pane_arrival(before)
                turnlog.end(rolled, command=self.command_row(text, before, bar), failure=failed, crash=crash, world_failed=self.world_failures(),
                            budget=self.last_budget, ops=self.line_record(), recovered=self.take_recovered())
                if self.header_key() != bar:
                    self.show_header()                                      # (f372) a hire, a sale or a walk from a pane moves the coin, the clock or the place
                continue
            turnlog.begin(console)                                          # (f385) the row waits for what the turn shows
            stood = self.turn(text)
            if stood is False:
                console.note(self.failed_line(text))                     # (f437, f449) in the narrator's words, never the machinery
            elif stood == "part":                                           # (f463) what stood stands; the player reads which part, and that the rest did not
                console.note(failures.part_stood("; ".join(self.line_done) or "the first of it", self.rng))
            turnlog.end(stood is False, failure="" if stood is True or self.last_crash else self.last_failure,
                        crash=self.last_failure if stood is not True and self.last_crash else "",
                        stood={True: "all", False: "none"}.get(stood, "part"), stand_in=bool(self.line_untold), world_failed=self.world_failures(),
                        budget=self.last_budget, ops=self.line_record(), recovered=self.take_recovered())
            self.show_header()

    def failed_line(self, text: str) -> str:
        """(f437) What the player reads when the turn could not be taken. (f449) A line that has now failed twice running on the game's own
        fault (logs/crash.log has it) is told to be left: saying it a third time will not help. The count is by the line's words, kept
        small."""
        if not self.last_crash:
            return failures.not_taken(self.rng)
        key = " ".join(text.lower().split())[:120]
        n = self.broken.get(key, 0) + 1
        self.broken[key] = n
        while len(self.broken) > 50:
            self.broken.pop(next(iter(self.broken)))
        return failures.not_possible(self.rng) if n >= 2 else failures.not_taken(self.rng)

    def command_row(self, text: str, before: str, bar) -> dict:
        """(f385) A # command's row: what it changed (the place, the clock, the coin: the top bar), and whether it is only a view."""
        from ui.gui.bridge import VIEWS
        changed = (["place"] if self.player.location != before else []) + (["clock or coin"] if self.header_key() != bar else [])
        name = (text[1:].strip().lower().split() or [""])[0]
        return {"text": text, "turn": self.store.meta.turn, "changed": changed, "view": name in VIEWS}

    def name_ids(self) -> None:
        """Who is who, for anything kept under a stable id instead of a name (engine/canon.py opinions): the hires, Maren, the player."""
        from engine import canon, mentor
        canon.IDS = {m["name"]: m["id"] for m in self.player.party if m.get("name") and m.get("id")}
        canon.IDS[mentor.NAME] = "maren"
        canon.IDS[self.player.character.name] = self.player.character.id      # (f480) the character by their id ("player" with one)
        canon.JOURNAL = lambda kind, actor, target, text, data: self.store.journal(self.minutes, kind, actor, target, text, data, self.last_text[:80])
        from engine import names, party as rules                # (f412) each companion's pronoun, for what reaches the screen
        names.set_cast({m["name"].split()[0]: rules.pronoun_of(m) for m in self.player.party if m.get("name") and m.get("permanent")})

    def new_input(self, text: str) -> None:
        """(f439) A new input, a typed line or a pane's command: the campaign counts it, inside the turn's transaction (a turn rolled back
        takes its count back with it, so the line tried again meets the same dice), and every stream of dice starts again from the seed,
        that count and the line (engine/streams.py). (A session that must replay exactly, streams.STRICT, takes in the residents made in
        the background at the input's edge before this, outside the transaction: apply_backfill in run().)"""
        self.store.meta.steps += 1                                  # (f463) saved by the first operation that stands (commit_operation first_of_line)
        streams.begin(self.store.meta.seed, self.store.meta.steps, text)
        from engine import budget
        budget.open()                                               # (f468) the input's minute of model time begins; closed when the line is done

    HELD = ("narrate", "say", "npc_says", "dialogue", "note", "wait", "ledger", "combat_numbers", "legendary_reveal",   # (f463) the story bindings an operation holds
            "combat_state", "combat_panel")     # (f497) the fight's pane and its text panel: pushed at the commit, not for an attempt that stood down
    PANE = ("combat_state", "combat_panel")     # (f497) held, but no lines of the page: load re-shows the pane from the row (enter), so they are
    #                                             kept off the record's presentation entry and the turn log's lines
    ROLLED = ("recent_narration", "convo", "last_spoken", "wildlife", "recently_fled", "resume_pending", "held_yield", "orenna_fight", "camp_fight",
              "last_social", "weight_hint", "exits_due", "last_plan", "journey_event_factor", "haggle_factor", "craft_boost", "camp_bonus",
              "dungeon_fight", "rank_options", "learn_options", "step", "interpret_calls", "ran",
              "partner", "stance", "pending_check", "pending_beats", "buffering", "line_done",
              "last_hits",                            # (f489) how a beat hit each of the party goes back with the banter that measured it
              "sneaking", "queued_buffs", "fight_text", "surrender_took")   # (f496) what a fight the player starts this turn opens with (f248:
    # the creeping up, the buffs readied by name, the line's words), and whether a survivor was taken captive: set by one operation's
    # attempt and consumed by it, they go back to what the attempt found, so an attempt run again for its answer creeps up again
    # (f485) the conversation goes back whole: who is being spoken with and how they are this talk, with its lines (convo, last_spoken
    # above), so a first talk that did not stand opens a new conversation when it is tried again, with the stance it had; and the step's
    # own state, so an operation run again to be given its answer (engine/asked.py) starts where the first attempt did.
    # (f465) The scene's own state a line writes outside the save: snapshotted by the session at every operation's start and put back by a
    # rollback beside the `_` caches (engine/session.py begin_turn, rollback), so a rolled-back operation leaves no trace of itself in what
    # the narrator remembers, who was last spoken to, what was in view, the plan, the road, the fight that is coming. Declared, not guessed:
    # an attribute a turn writes and a rollback should take back is added here, or the next failing operation shows it.

    def begin_line(self) -> None:
        """(f463) A line begins: nothing of the last one's operations is kept, and the write fence is armed for its life."""
        self.last_crash = False
        self.line_ops, self.line_failed, self.line_done, self.line_world_failed = [], [], [], []
        self.passages, self.line_untold, self.unshown_ops, self.collecting = [], [], {}, False
        self.store.arm(True)

    @contextmanager
    def operation(self, kind: str, text: str = "", where: str = "turn", world: bool = False, op_id: str = ""):
        """(f463) One operation of the line: all of it stands or none of it does, with its record in the save (engine/operation.py,
        storage/campaign.py commit_operation). Inside: the store counts an operation open (the write fence lets its writes through), one
        transaction, the session's snapshot of what the database does not hold (f455), and the hold over the story bindings: what the body
        would show is kept on the operation and released, in order, once it has committed, so nothing the player reads is ever of an
        operation that did not stand; the record's presentation entry keeps the lines until they are shown (mark_shown), for a game
        closed in between (f467). On the model's failure (LLMError) or the game's own fault (any other exception, written to logs/crash.log
        as f449 did for the turn) the operation is rolled back through the session, the store is reloaded, the held lines are dropped,
        and the line goes on or stops as turn() decides; an Interrupt passes out untouched. Nothing is caught for the caller to see but
        `op.state`: committed or rolled_back.
        (f466) `world`: one of the world's own operations (the pulse, the arrival, the law, the tail, the game's opening), apart from the
        player's: its failure is rolled back alone and written to logs/crash.log, it halts nothing, and the player is told nothing of it
        (Bundle C, owner question 4); the line's outcome is of the player's operations alone (line_failed), the world's failures kept
        beside it (line_world_failed) for the turn log. `op_id`: an id drawn beforehand, when the caller looked for its record first."""
        from engine import asked as _asked, operation as _op
        index = len(self.line_ops) + len(self.line_failed) + len(self.line_world_failed)
        pending0 = list(self.pending)                # (f493) the line's held narration as this operation found it, to put back whole
        fight0 = self.fight_memory()                 # (f496) what the player has read of the fight, and who was tamed, as it found them
        if world and where == "turn":
            where = "world"
        op = None
        real: dict = {}
        writes0 = self.store._writes
        try:
            with self.store.in_operation(), self.store.transaction():
                self.session.begin_turn(self)                  # (f455) the map's additions and the scene's caches, to give back on a rollback
                if _op.current() is not None:
                    _op.end("rolled_back")                      # one left open by an Interrupt that passed through: closed, never joined
                op = _op.begin(kind, self.store.meta.steps, index, self.store.revision(), text, op_id=op_id)
                self.store.flush_later()                       # (f470) what a read filled in outside any operation is saved first
                real = self.hold(op)
                try:
                    yield op
                finally:
                    self.unhold(real)                          # symmetric: the real bindings are back before anything is shown or dropped
                if op.void and self.store._writes == writes0:
                    raise _Void()                              # (f470) nothing took the line and nothing was written: no record, nothing kept
                self.save_talk()                               # (f485) the conversation, with the operation that moved it
                self.store.save_player(self.player)            # (f464) what the operation changed of the player is its to keep: a later
                self.store.commit_operation(op, first_of_line=(index == 0))   # operation's rollback reloads the player from the save
            _op.end("committed")
            if self.crash_after_commit == kind:                   # (f467) the game dies between the commit and its telling: the next load tells it
                self.crash_after_commit = ""
                raise Interrupt(f"stopped after the commit of {kind}, before it was shown")
            self.line_ops.append(op)
            waiting = self.release(op)
            _op.present(op.id, "shown")                           # (f467) what it held reached the page (its later lines after their passages)
            if waiting:
                self.unshown_ops[op.id] = waiting              # (f464) marked shown once the passages its later lines wait on have run
            else:
                self.store.mark_shown(op.id)
        except _asked.NeedAnswer as e:
            self.give_back(op, pending0, fight0)                  # (f485) stood down to ask the model outside: nothing kept, nothing
            op.need = e                                           # counted as failed, nothing halted; asked_operation asks and runs it again
        except _Void:
            _op.end("void")                                       # (f470) ended without a record and not counted; what the scene changed in
            self.passages = [p for p in self.passages if p[4] != op.id]    # memory (a yielded foe let go) stands, nothing was written, and
            self.release(op)                                      # what it said reaches the page
        except Interrupt:
            raise                                                 # (f449) stopped on purpose (a replay parted): never a rolled-back fault
        except LLMError as e:
            self.abandon(op, pending0, world=world, fight0=fight0)
            console.debug(f"operation {kind} rolled back: {e}")
            self.last_failure = str(e) or type(e).__name__       # (f437) the turn log keeps why, as a model failure
            if op is not None:
                op.failure = self.last_failure
        except (Exception, _asked.Drift) as e:
            # (f449) The game's own fault, not the model's: the operation is rolled back, the fault goes to logs/crash.log with the line and
            # the place, and the player reads a line in the narrator's words (run()). What stood before it stands. (f466) A world
            # operation's fault is written there as the world's, and the player reads nothing of it.
            self.abandon(op, pending0, world=world, fight0=fight0)
            from engine import crashlog
            crashlog.record(e, where, text=text, place=self.player.location, turn=self.store.meta.turn, operation=kind)
            console.debug(f"operation {kind} crashed and rolled back: {type(e).__name__}: {e}")
            self.last_failure = f"{type(e).__name__}: {e}"[:200]
            self.last_crash = True
            if op is not None:
                op.failure, op.crashed = self.last_failure, True
        finally:
            if op is not None and op.state == "open":              # an Interrupt passed through: the operation is rolled back all the same
                self.abandon(op, pending0, world=world, fight0=fight0)

    def hold(self, op) -> dict:
        """(f463) The story bindings replaced by ones that keep each call on the operation, for release at its commit; what the console
        held is returned, to be put back by unhold whatever happens."""
        real = {}
        for name in self.HELD:
            fn = getattr(console, name, None)
            if fn is None:
                continue
            real[name] = fn

            def held(*a, _name=name, **k):
                op.held.append((_name, a, k))
                if _name in self.PANE:                             # (f497) the pane's data is no line of the page; and show() takes the
                    return console.damage_tags if _name == "combat_state" else None     # same branch held as live (the window's binding
                op.lines.append(turnlog._shown_text(_name, a, k) if _name in turnlog.SHOWN_KINDS else " ".join(str(x) for x in a))   # says True)
            setattr(console, name, held)
        return real

    @staticmethod
    def unhold(real: dict) -> None:
        for name, fn in real.items():
            setattr(console, name, fn)

    def release(self, op) -> int:
        """(f463) The operation committed: what it held reaches the page, in the order it was said, through the real bindings. (f464) Up to
        its first marker: what follows a marker waits behind that passage and is shown after it (run_passages), so the page reads as it did
        when the passage was written in the middle of the action. How many segments wait."""
        segments, current = 0, None
        for name, a, k in op.held:
            if name == "marker":
                current = a[0][3]
                segments += 1
            elif current is not None:
                current.append((name, a, k))
            else:
                getattr(console, name)(*a, **k)
        op.held = []
        return segments

    def mark_passage(self, kind: str, fn, standin=None) -> None:
        """(f464) Here goes a passage: a narration, a fight round's telling, the aftermath of a win, the goddess's words. Inside an
        operation of a line it is queued to run as an operation of its own once this one has committed (run_passages), at this place in
        what the player reads: what this operation says after this point waits to be shown after it. Its failure shows `standin` (a line or
        lines in the narrator's words, from engine/failures.py) and undoes nothing: what it would have told stands (Bundle C decision 1,
        the rebuild's rule 3). With no operation open, or outside a line, it runs now."""
        from engine import operation as _op
        op = _op.current()
        if op is None or not self.collecting:
            fn()
            return
        entry = [kind, fn, standin, [], op.id]
        op.held.append(("marker", (entry,), {}))
        self.passages.append(entry)

    def run_passages(self) -> None:
        """(f464) The passages the last operation queued, in order, each an operation of its own: told, or told by its stand-in when its
        telling could not be written; then the lines that waited behind it; and the operation whose lines they were is marked shown once
        the last of them has reached the page."""
        from engine import operation as _op
        while self.passages:
            kind, fn, standin, after, owner = self.passages.pop(0)
            halted = self.halted
            told_before = {id(r) for r in ledger.ROWS if r.get("told")}
            op, _ = self.asked_operation(kind, self.last_text, lambda op: fn())    # (f498) restartable: the telling's own call is asked
            self.halted = halted                                   # outside it; a telling that did not stand halts nothing: the facts stand
            if op.state != "committed":
                if op in self.line_failed:
                    self.line_failed.remove(op)
                self.line_untold.append(op)
                self.untell(told_before)                           # it told nothing: the rows it took to tell are untold again
                lines = standin(self.rng) if standin else []
                for line in ([lines] if isinstance(lines, str) else lines):
                    if line:
                        console.narrate(line)
                _op.present(op.id, "stand_in")                     # (f467) told by a stand-in
            for name, a, k in after:
                getattr(console, name)(*a, **k)
            if owner in self.unshown_ops:
                self.unshown_ops[owner] -= 1
                if self.unshown_ops[owner] <= 0:
                    del self.unshown_ops[owner]
                    self.store.mark_shown(owner)

    @staticmethod
    def untell(told_before: set) -> None:
        """(f464) A passage that did not stand told nothing: the rows it marked told (ledger.told, when its request was built) are untold
        again, so the stand-in and the next passage can tell them."""
        for r in ledger.ROWS:
            if r.get("told") and id(r) not in told_before:
                r.pop("told", None)

    def stood_standin(self, rng) -> list[str]:
        """(f464) What the player reads when the line's passage could not be written: one plain line for each row of the line not yet
        told that has facts to fill it from (engine/failures.py stood_lines); with none, one line that the deed stands."""
        rows = [r for r in ledger.ROWS if r.get("facts") and not r.get("told")]
        return failures.stood_lines(rows, rng) if rows else [failures.stood_any(rng)]

    def abandon(self, op, pending0: list, world: bool = False, fight0=None) -> None:
        """(f463) An operation did not stand: its rows go (the rest of the line's stay), the session gives back what the database never
        held, the store is reloaded, the narration it queued for the passage is dropped, its held lines with it, and the line is halted:
        what came before it stands, nothing after it is done. (f466) A world operation's failure halts nothing: the world's operations
        after it run all the same, each apart."""
        if op is not None:
            (self.line_world_failed if world else self.line_failed).append(op)
        self.give_back(op, pending0, fight0)
        if not world:
            self.halted = True


    def asked_operation(self, kind: str, text: str, body, world: bool = False, keep=None, where: str = "turn"):
        """(f485, engine/asked.py) An operation that may need the model: run as a restartable attempt. When its body reaches a call asked
        outside, the operation stands down (give_back), the call is made with no operation open, and the operation runs again from its
        start, the dice, the plan's steps and what reads had filled in put back as they were, the answer (or its failure) given at the same
        point. Returns (op, what the body returned) for the attempt that ended, committed or not. (f498) `where`: the pane command's,
        for logs/crash.log. The ledger rows an attempt took to tell (ledger.told) are untold again when it stands down: the attempt that
        stands tells them, in the same words (the aftermath's request names them)."""
        import copy
        from engine import asked, pulselog, refusals
        serve = asked._Serving()
        plan0 = [copy.deepcopy(x) for x in keep] if keep is not None else None
        later0 = list(self.store._later)
        marks0 = (len(refusals.SESSION), len(pulselog.LOG))
        cap = asked.most()                               # (f489) budget.yaml asked_max
        for _ in range(cap):
            snap = streams.snapshot()
            held = {id(x): x for x in [*self.residents, *self.present, self.partner, self.player] if x is not None}
            states = {k: x.model_copy(deep=True) for k, x in held.items()}       # who is here and who acts, as found: put back in place,
            lists = (list(self.residents), list(self.present), self.partner, self.player)   # the same objects, so a holder sees the re-run
            meta = self.store.meta.model_copy()          # the clock and the input's count as they stand in memory (a give-back reloads the save's)
            told0 = {id(r) for r in ledger.ROWS if r.get("told")}        # (f498) what was told before this attempt
            asked.begin(serve)
            result = None
            try:
                with self.operation(kind, text, where=where, world=world) as op:
                    result = body(op)
            finally:
                asked.end()
            need = op.__dict__.pop("need", None)
            if need is None:
                return op, result
            streams.restore(snap)                        # the attempt that stood down drew nothing that counts
            self.untell(told0)                           # (f498) ...and told nothing: the rows it took to tell wait for the attempt that stands
            for k, x in held.items():
                x.__dict__.update(states[k].__dict__)
            self.residents, self.present, self.partner, self.player = list(lists[0]), list(lists[1]), lists[2], lists[3]
            self.store.meta = meta
            if keep is not None:
                keep[:] = [copy.deepcopy(x) for x in plan0]
            self.store._later = list(later0)
            for log, n in ((refusals.SESSION, marks0[0]), (pulselog.LOG, marks0[1])):     # what the attempt noted goes with it
                while len(log) > n:
                    log.pop()
            try:
                serve.answers.append((need.key, need.ask(), None))
            except Interrupt:
                raise
            except Exception as e:                       # the model's failure, or the game's own in the call: the body is given it
                serve.answers.append((need.key, None, e))
        raise RuntimeError(f"{kind}: more than {cap} model calls asked for one operation")

    def prepare_step(self, i: int, plan: list, text: str) -> bool:
        """(f485) Before a step's operation, its prepare if its kind has one (prepare_<kind>): what the step would do first that is its own
        thing (a walk, a hand-in), each an operation of its own. False when one of those did not stand: the step is not done."""
        fn = getattr(self, f"prepare_{plan[i].kind}", None)
        if fn is None:
            return True
        failed = len(self.line_failed)
        try:
            fn(plan[i], text)                            # reads only, outside any operation: the write fence is armed
        except Interrupt:
            raise
        except Exception as e:                           # a write there, or any fault: the game's own (logs/crash.log), the step not done
            from engine import crashlog
            crashlog.record(e, "turn", text=text, place=self.player.location, turn=self.store.meta.turn, operation=f"prepare_{plan[i].kind}")
            self.last_failure, self.last_crash = f"{type(e).__name__}: {e}"[:200], True
            return False
        return len(self.line_failed) == failed and not self.halted

    def prepare_talk(self, intent, text: str) -> None:
        """(f485) Before the talk's own operation: the walk to someone of this town who is elsewhere (action:go) and the work handed in by
        speaking to who pays it (action:handin), each its own operation, so a reply that fails leaves them standing. The talk itself then
        finds them here, with what was handed in (on_talk)."""
        if (self.hire_by_id(intent.target) and not self.mentor_with_you()) or self.mentor_wants_talk(intent, text):
            return
        target_id = intent.target if intent.target not in ("", "none", "null") else ""
        if target_id and not any(n.id == target_id for n in self.present) and not self.store.npc_exists(target_id):
            target_id = ""
        target_id = target_id or (self.partner.id if self.partner else "") or (self.last_spoken or "")
        if not target_id:
            return
        if not any(n.id == target_id for n in self.present) and not any(n.id == target_id for n in self.residents) and self.store.npc_exists(target_id):
            away = self.store.load_npc(target_id)
            from engine import mapview
            if (away.location in self.world.places and away.location != self.player.location
                    and mapview.top_of(self.world, away.location) == mapview.top_of(self.world, self.player.location)
                    and not self.world.places[away.location].danger and away.away_until <= self.minutes):
                self.asked_operation("action:go", text, lambda op: self.travel_route(away.location, text))
                if self.halted:
                    return
        npc = next((n for n in self.present if n.id == target_id), None)
        if npc is None or not self.player.quests:
            return

        def _handin(op):
            was, self.buffering = self.buffering, True                  # (f384) two jobs handed in are told in one passage
            handed = self.turn_in(npc.id)
            self.buffering = was
            self._handed_in = (npc.id, handed)
            op.void = not handed
        self.asked_operation("action:handin", text, _handin)

    def characters(self) -> list:
        """(f485) The characters in this scene: the one player's today (engine/presence.py reads it)."""
        return [self.player.character]

    def talk_record(self) -> dict:
        """(f485) The conversation as the save keeps it (kv talk): who is spoken with, how they are this talk, its lines, who spoke last.
        Written with each operation's commit, so it rolls back with the operation and is there when the save is opened again."""
        from engine import presence
        lines = [list(x) for x in (self.convo or [])][-presence.lines_cap():]
        return {"speaker": self.partner.id if self.partner else "", "stance": getattr(self, "stance", "") or "", "lines": lines,
                "last_spoken": self.last_spoken or ""}

    def save_talk(self) -> None:
        rec = self.talk_record()
        if not rec["speaker"] and not rec["lines"] and not rec["last_spoken"]:
            if self.store.load_talk() is not None:
                self.store.clear_talk()
            return
        if self.store.load_talk() != rec:
            self.store.save_talk(rec)

    def restore_talk(self) -> None:
        """(f485) A save opened mid-talk: the conversation as it was, once the one spoken with is here."""
        rec = self.__dict__.pop("_talk_saved", None)
        if not rec:
            return
        self.last_spoken = rec.get("last_spoken") or None
        who = next((n for n in self.present if n.id == rec.get("speaker")), None)
        if who is not None:
            self.partner, self.stance = who, rec.get("stance", "")
            self.convo = [tuple(x) for x in rec.get("lines") or []]

    def fight_memory(self):
        """(f496) What the fight's scene keeps outside the save (what the player has read of this fight, who was tamed) and which fight it is
        (the serial, "" until its first blow): taken as an operation opens, put back on the resumed scene by give_back. None with no fight."""
        if self.combat is None:
            return None
        return (list(self.combat.fight.shown), list(self.combat.fight.tamed), self.combat.fight.serial,     # (f499) the fight's own
                dict(self.combat.fight.ground_told))                                                      # (f571) and the ground it was told

    def give_back(self, op, pending0: list, fight0=None) -> None:
        """(f463) What an operation that did not stand gives back: its record, the session's snapshot of what the database never held, the
        store reloaded, the narration it queued and its held lines. (f485) Alone, for an operation that stood down to ask the model
        outside its transaction: nothing of it is counted, nothing halted."""
        from engine import operation as _op
        _op.end("rolled_back")
        if op is not None:
            op.held = []
            self.passages = [p for p in self.passages if p[4] != op.id]      # (f464) the passages it queued go with it
        self.session.rollback(self, op.id if op is not None else "")
        self.store.reload_meta()                           # the clock the operation advanced goes back with it
        self.player = self.store.load_player()
        pools.fill_missing(self.player.character)
        saved_fight = self.store.load_combat()
        self.combat = CombatScene.resume(self, saved_fight) if saved_fight else None
        if fight0 is not None and self.combat is not None and self.combat.fight.serial == fight0[2]:
            self.combat.fight.ground_told = dict(fight0[3]) if len(fight0) > 3 else {}             # (f571) the same way
            self.combat.fight.shown, self.combat.fight.tamed = list(fight0[0]), list(fight0[1])     # (f496) the resumed fight remembers what the
            # player has read of it and who was tamed, as the operation found them: shown-memory, not state (Bundle C), kept on the scene
            # and lost with it when the row was resumed, so a round run again for its answer told the ground and the light a second time
        here = self.store.load_place(self.player.location)
        if here.populated:
            self.residents = [n for n in (self.store.load_npc(i) for i in here.residents) if not n.gone]
        self.refresh_present(assign=False)                # (f497) read, never written: their doings wait for an operation (the fence is armed)
        self.partner = next((n for n in self.present if self.partner and n.id == self.partner.id), None)
        self.pending = list(pending0)                     # (f493) as the operation found it: what it added goes, and what it flushed of an
                                                          # earlier operation's comes back (a hand-in's passage, flushed by the talk
                                                          # that stood down, was missing from its re-run: the post-D night's Drift)
        self.step = None

    def defer(self, kind: str, data: dict) -> None:
        """(f469) An optional call the budget deferred (engine/budget.py Deferred, the table's `later: deferred`): queued in the save,
        with the input it came from, for a later turn's tail (run_deferred). Called inside the operation whose call it was, so a rollback
        takes the entry with it; one deferred again from the queue keeps its first input's age."""
        rows = self.store.load_deferred()
        rows.append({"kind": kind, "data": data, "from_steps": int(self.__dict__.get("_deferred_from", self.store.meta.steps))})
        self.store.save_deferred(rows)

    def run_deferred(self) -> None:
        """(f469) The tail's turn for what earlier inputs deferred (decisions 4 and 10): each entry runs once as this input's optional
        work, under this input's dice and allowed by its budget again (deferred again, it waits on with its first age; dropped, it is
        gone); an entry older than retention.deferred_turns (data/rules/budget.yaml) goes untried; while a fight is on the queue waits,
        and ages. The queue is taken up whole before anything runs, so what defers itself again queues anew."""
        rows = self.store.load_deferred()
        if not rows:
            return
        from engine import operation as _op
        keep = int(_op.RETENTION.get("deferred_turns") or 3)
        steps = self.store.meta.steps
        live = [r for r in rows if steps - int(r.get("from_steps", steps)) <= keep]
        if self.combat:
            if live != rows:
                self.store.save_deferred(live)
            return
        self.store.save_deferred([])
        for r in live:
            self.__dict__["_deferred_from"] = int(r.get("from_steps", steps))
            try:
                self.run_deferred_one(r.get("kind", ""), r.get("data") or {})
            finally:
                self.__dict__.pop("_deferred_from", None)

    def run_deferred_one(self, kind: str, data: dict) -> None:
        """(f469) One deferred entry, by kind: the party's exchange (party_banter, without the roll that first brought it up), a hire's
        personal details (persona_details), an arc's dressing (redress_arc). A kind nobody knows is dropped."""
        if kind == "banter":
            wanted = set(data.get("crew") or [])
            crew = [m for m in self.banter_crew() if m.get("id") in wanted]
            if crew:
                self.party_banter(crew, data.get("why") or "travel")
        elif kind == "persona":
            m = next((x for x in self.player.party if x.get("id") == data.get("member")), None)
            if m is not None and not m.get("details"):
                m["details"] = self.persona_details(m)
        elif kind == "arc":
            self.redress_arc(data.get("arc", ""))

    def understood(self, text: str):
        """(f470) understand(), its failures taken as the line's own, as operation() takes an operation's: the model's (the line is not
        taken) or the game's (logs/crash.log, the player told so). False then; else the plan, or None when the world asked instead."""
        try:
            plan = self.understand(text)
        except Interrupt:
            raise
        except LLMError as e:
            console.debug(f"the understanding failed: {e}")
            self.last_failure = str(e) or type(e).__name__
            plan = False
        except Exception as e:
            from engine import crashlog
            crashlog.record(e, "turn", text=text, place=self.player.location, turn=self.store.meta.turn, operation="understanding")
            console.debug(f"the understanding crashed: {type(e).__name__}: {e}")
            self.last_failure = f"{type(e).__name__}: {e}"[:200]
            self.last_crash = True
            plan = False
        if not plan and not self.line_ops:
            self.store.reload_meta()                           # nothing of the line committed: the input's count is given back (f463)
        return plan

    def line_record(self) -> list:
        """(f471) The line's operations for the turn log: id, kind, index and how each ended (stood; rolled_back, the player's or the
        world's; stand_in, a telling stood in for), in the order they ran: the key that joins the row to the save's record (kv
        operations) and to the audit log's blocks."""
        rows = [{"id": o.id, "kind": o.kind, "index": o.index, "state": "stood"} for o in self.line_ops]
        rows += [{"id": o.id, "kind": o.kind, "index": o.index, "state": "rolled_back"} for o in self.line_failed + self.line_world_failed]
        rows += [{"id": o.id, "kind": o.kind, "index": o.index, "state": "stand_in"} for o in self.line_untold]
        return sorted(rows, key=lambda r: (r["index"], r["state"] != "stood"))

    def take_recovered(self) -> int:
        """(f471) The outcomes told at the last load, reported once, on the first row after it."""
        return int(self.__dict__.pop("_recovered_unreported", 0) or 0)

    def world_failures(self) -> list:
        """(f466) The world's own operations of the line that did not stand, for the turn log and the night's counts: which, why, and
        whether it was the game's own fault (logs/crash.log) or the model's."""
        return [{"kind": o.kind, "error": o.failure, "crash": o.crashed} for o in self.line_world_failed]

    def turn(self, text: str):
        """(f463) One typed line, as operations: the understanding and the first action (or the whole of an intercepted line, an answer, a
        fight's round) first, then each later step of the plan, then its passage (f464), then (f466) the world's own operations, apart:
        the world (the pulse), the arrival (a moment walked into, someone come looking), the law, and the tail, each all-or-nothing with
        its record, each failing alone and silently (world_failures). True when every operation of the player's stood; False when the
        first did not (the line is not taken: nothing happened, nothing is lost, as before); "part" when some stood and a later one did
        not: what stood stands, nothing after it is done, and the player reads which part (run()). The write fence is armed for the life
        of the line; no question is read inside it (f461)."""
        self.name_ids()
        turnlog.tap(console)
        shown = turnlog.SHOWN
        self.begin_line()
        try:
            with questions.fence():
                self.new_input(text)                       # (f439) the dice of this input
                ledger.begin()                             # (f394) the turn's record
                self.ran = []
                plan = None
                self.collecting = True                     # (f464) a narration asked for by an action is a passage operation after it
                self.take_up_acts(text)                    # (f596) an act left waiting for its ruling, before this line is read
                def _line(op):                             # (f470) the line taken whole (an answer, a fight's round, an intercept), or void
                    self._wrote_turn = False               # (f351) the narrator's mark is a flag, not a turn number; set inside the operation, so a rollback takes it back
                    got = self.take_line(text)
                    if got is None:
                        op.void = True
                    return got
                op, taken = self.asked_operation("line", text, _line)
                if op.state == "rolled_back":
                    return False
                if not taken:                              # (f470) the understanding outside any transaction: the interpreter and the audit read
                    plan = self.understood(text)           # committed state; a question asked, or a board refresh due, is an operation of its own
                    if plan is False:
                        return False
                    if plan is not None:
                        def _first(op):
                            self._wrote_turn = False
                            self.pending_clarify = None    # (f470) a question this line answered is spent inside the first action's commit
                            self.run_step(0, plan, text)
                        before = len(self.line_ops)
                        stood = self.prepare_step(0, plan, text) and self.asked_operation(f"action:{plan[0].kind}", text, _first,
                                                                                            keep=plan)[0].state == "committed"
                        prepared = any(o.kind in ("action:go", "action:handin") for o in self.line_ops[before:])
                        if not stood and not prepared:
                            return False                   # the first action did not stand: the line is not taken (a board refresh aside)
                        if not stood:                      # (f485) its prepare's own operation stood (the walk, the hand-in): what stood stands
                            plan = plan[:1]
                self.run_passages()
                if plan is not None:
                    for i in range(1, len(plan)):
                        if self.combat or self.halted:
                            console.debug(f"stopping after {i} of {len(plan)} actions")
                            break
                        if not self.prepare_step(i, plan, text):     # (f485) the step's own prepare (a walk, a hand-in) did not stand
                            self.run_passages()
                            break
                        op, _ = self.asked_operation(f"action:{plan[i].kind}", text, lambda op, i=i: self.run_step(i, plan, text), keep=plan)
                        self.run_passages()
                        if op.state != "committed":
                            break                              # what stood stands; the rest of the line is not done
                    if self.pending:                           # (f464) several actions: their one passage, an operation after them all and before the pulse
                        told_before = {id(r) for r in ledger.ROWS if r.get("told")}
                        with self.operation("passage", text) as op:
                            self.passage(text)
                        if op.state != "committed":
                            self.line_failed.remove(op)
                            self.line_untold.append(op)
                            self.untell(told_before)
                            for line in self.stood_standin(self.rng):
                                console.narrate(line)
                            self.pending = []
                            from engine import operation as _op
                            _op.present(op.id, "stand_in")         # (f467)
                    from engine import budget
                    budget.passage_shown()                     # (f468) the required path is told: the optional calls after it keep no reserve
                    self.after_steps(text)                     # (f466) outside any operation: the step is over, and what the line did not do is said
                    with self.operation("world", text, world=True):      # (f466) the world's own operations, apart: each stands or falls alone
                        self.world_tick()
                    self.run_passages()
                    with self.operation("arrival", text, world=True):
                        self.arrival()
                    self.run_passages()
                    with self.operation("law", text, world=True):
                        self.law_check()
                    self.run_passages()
                from engine import budget
                budget.passage_shown()                         # (f468) a fight's round or an answer: told; the tail's calls keep no reserve
                def _tail(op):                             # (f489) restartable: the party's talk it asks for is asked outside it
                    if plan is not None:
                        self.store.meta.turn += 1              # (f466) the line counted, with its tail
                    self.turn_ticks(text, shown)
                self.asked_operation("tail", text, _tail, world=True)
                self.run_passages()                            # (f498) the tail collects too: a road fight walked into as it resumes the
                if not self.combat:
                    self.situation_births(text)                # (f546) a situation born given its parts, each in operations of its own
                self.collecting = False                        # road (resume_road) begins committed, its opening a passage told after it
                ledger.LAST = ledger.end()
                return True if not self.line_failed else "part"
        except Interrupt:
            raise
        finally:
            self.store.arm(False)
            from engine import budget
            self.last_budget = budget.close(stand_ins=[o.kind for o in self.line_untold])   # (f468) the input's budget closes with the line

    def turn_ticks(self, text: str, shown: int) -> None:
        """(f463) What follows every line, however it was read: the road walked on, the hires' words marked, the quest and the mentor and
        the companions given their turn, the day's wear, what was heard of, and the save."""
        self.release_time_notes()                  # (f418) whatever way the line ended
        if self.resume_pending and not self.combat and not getattr(self, "held_yield", None):
            self.resume_road()                     # (f417) a won road fight walks on once the player has said what becomes of who yielded
        heard = self.hire_said_marks()
        self.sync_heard()
        self.orenna_tick()
        self.mentor_tick()
        self.quirk_tick()
        self.run_deferred()                        # (f469) what earlier turns deferred, before the party's own talk of this one
        self.banter_tick()
        self.note_hire_spoke(heard)
        self.collapse_check()
        self.stay_tick()                           # (f351) one change in the room since last turn, if the narrator did not write
        self.heard_flush()                         # the places first heard of this turn, in one quiet line
        from engine import operation as _op
        held_now = (len(_op.current().lines) + sum(1 for h in _op.current().held if h[0] == "marker")
                    if _op.current() is not None else 0)     # (f463) what this operation holds, not yet released; (f498) a passage it queued
        if turnlog.SHOWN + held_now == shown and not self.to_menu:
            self.said_nothing(text)
        self.store.save_player(self.player)

    def said_nothing(self, text: str) -> None:
        """(f385) The turn showed the player nothing at all: no passage, no line, no note. That is never the answer to something typed.
        (f416) When the engine did something all the same (a contract taken from the board, and the clerk's words never came), that is
        told, in the world; only a turn that did nothing says so, and the refusal log keeps what ran, so the handler that went quiet can
        be found and given its own reason."""
        from engine import refusals
        if ledger.untold():
            self._narrate_now("Tell what the game did this turn, as the player would see it, and nothing more.", text)
            return
        ran = ", ".join(getattr(self, "ran", []) or []) or "nothing"
        console.note("Nothing comes of that here. Try it another way, or say plainly what you want to happen.")   # (f391) in the world's words
        refusals.note("silent", text, f"the turn showed nothing; actions run: {ran}", self.player.location, self.store.meta.turn)

    step = None                                      # (f416) the plan's step being done, while one is

    def refuse(self, say: str, needed_by_rest: bool | None = None) -> None:
        """(f416) The game says no to a step. The player reads why; the turn's record keeps what did not happen, so the passage that tells
        the rest of the line never shows it done (a whetstone the player did not have rasped along their blade, a dungeon they were not
        at was walked into); the refusal log keeps it, so the night's count of refusals is every one the page shows; and the steps after
        it are not done only when they rest on this one (engine/actions.py needed_by_rest), unless the handler says otherwise."""
        from engine import actions, refusals
        console.note(say)
        st = self.step
        kind = st.kind if st is not None else ""
        what = (getattr(st, "summary", "") or "").strip() if st is not None else ""
        reason = hygiene.undash(" ".join(say.split())).rstrip(".")
        ledger.add("refused", step=kind, what=what, why=reason,
                   say=(f"NOT DONE, never show it done: {what} ({reason})." if what else f"NOT DONE, never show it done: {reason}."))
        refusals.note("refused", self.last_text or "", f"{kind or 'outside a plan'}: {reason}", self.player.location, self.store.meta.turn)
        if needed_by_rest is None:
            needed_by_rest = actions.BY_KIND[kind].needed_by_rest if kind in actions.BY_KIND else True
        if needed_by_rest:
            self.halted = True

    def reload_after_rollback(self) -> None:
        """The database was rolled back to before the turn; what the scene holds in memory must match it again. (f455) First the session
        gives back what the database never held: the map's additions, the scene's caches, the ledger's rows, the casting cache."""
        self.session.rollback(self)
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
        self.pending, self.buffering, self.halted, self.step = [], False, False, None

    def pane_arrival(self, before: str) -> None:
        """Arriving by a pane button (the map, the places list) counts like arriving by a typed line: what is due on arrival happens now,
        as the world's tail operation (f466): rolled back alone and silently when a call fails."""
        if self.player.location == before or self.combat:
            return
        self.store.arm(True)
        try:
            with questions.fence(), self.operation("tail", f"arrival at {self.player.location}", world=True):   # (f463) rolled back on its own when a call fails
                self.sync_heard()
                self.orenna_tick()
                self.mentor_tick()
                self.quirk_tick()
                self.banter_tick()
                self.heard_flush()
                self.store.save_player(self.player)
        finally:
            self.store.arm(False)

    def collapse_check(self) -> None:
        """Past the limit of fatigue you fall asleep where you stand: eight hours, with the dangers of the place."""
        c = self.player.character
        if not needs.collapsing(c) or self.combat:
            return
        console.note("You can't stay on your feet. Your legs give out and you sleep where you fall.")
        self.on_wait(ActionIntent(kind="wait", wait_minutes=needs.N["collapse_hours"] * 60), "I collapse from exhaustion")
        if needs.collapsing(c):                       # nowhere safe to fall: you wake at once, barely upright
            c.fatigue = needs.N["collapse_unslept"]

    def enchant_command(self, args: str, confirmed: bool = False) -> None:
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
        if not confirmed:                                               # (f460) the question ends the turn; the next line answers it (on_answer_enchant)
            self.ask_next("enchant", f"Bind {option.name} into {target} for {money.fmt(enchanting.fee(item, option))}"
                          f"{' and a raw ' + items.MATERIALS[option.reagent].name if option.reagent else ''}? "
                          f"{enchanting.success_chance(item)}% chance of success. (y/n)", args=args)
            return
        ok, message = enchanting.enchant(c, item, option, self.rng)
        console.note(message)
        self.store.save_player(self.player)

    def on_answer_enchant(self, asked: dict, text: str):
        """(f460) The answer to #enchant's question: yes binds it (the command runs again, confirmed, so what it checked is checked
        again), no cancels, anything else lets the question go."""
        yes = questions.yes_no(text)
        if yes is None:
            return None
        if not yes:
            console.note("Cancelled.")
            return True
        self.enchant_command(asked["data"]["args"], confirmed=True)
        return True

    def equip_command(self, query: str) -> None:
        c = self.player.character
        if not query:
            console.note("Equip what? Use #inventory to see your items, then e.g. #equip 1 or #equip spear")
            return
        item = equipment.find(c, query, "inventory")
        if not item:
            worn = equipment.find(c, query, "equipment") or next((i for i in c.equipment.values() if query.strip().lower()
                                                                  in (items.base_of(i).name.lower(), items.base_of(i).slot.replace("_", " "))), None)
            if worn is None and re.search(r"\b(blade|weapon|steel|arms|sword)\b", query.lower()):
                worn = c.equipment.get("main_hand")                   # (f429) "I draw my blade" with a mace in hand: the mace
            if worn:                                                  # (f420) already in hand: that is a yes, quietly, never "not carrying"
                console.note(f"{cap_first(items.display_name(worn))} is already {'in hand' if items.base_of(worn).slot in ('main_hand', 'off_hand') else 'on'}.")
                return
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
        seen = regard.of(npc, self.acting)                   # (f480) the note is the acting character's, about this person
        if not seen.name_known:
            return False
        if not seen.journal_note:
            return True
        return abs(seen.trust - seen.note_trust) >= self.NOTE_TRUST_SHIFT or npc.memory_total - seen.note_mem >= self.NOTE_NEW_MEMORIES

    def journal_line(self, n, town: str) -> str:
        """One sentence about a person you know by name: their own note when they have written one, a plain line from what is known until then."""
        import re as _re
        note = regard.of(n, self.acting).journal_note        # (f480)
        if note and not ("[" in note or _re.search(r"\b(I|I'm|I've|my|me)\b", note)):
            return note                                      # (f299) a note written in their own voice, from an older save, is passed over
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
            if not (regard.of(n, self.acting).met and regard.of(n, self.acting).name_known):
                continue                                     # (f480) known by name to another character, not to this one
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
        heard = [{"name": n.name, "by": seen.heard_of["by"], "line": seen.heard_of["line"]}       # (f480) what this character heard
                 for n in sorted(self.store.load_npcs([r.id for r in self.store.npc_rows(heard_of=True)]), key=lambda x: x.name.lower())
                 for seen in [regard.of(n, self.acting)] if seen.heard_of and not (seen.met and seen.name_known)]
        known = self.player.character.knowledge
        from engine import matters
        found = [f"{cap_first(e.name)}, {self.where_name(e.place)}: {e.data['clue'].replace('{low_tide}', features.low_tide_text(self.minutes))}"
                 for e in self.store.find_entities(kind="feature") if e.data.get("read") and e.data.get("clue")]          # (f394)
        return {"groups": out, "heard": heard, "facts": [self.world.lore[f].text for f in known if f in self.world.lore] + found,
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

    def allocate(self, args: str, confirmed: bool = False) -> None:
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
        if not confirmed:                                               # (f460) the question ends the turn; the next line answers it (on_answer_allocate)
            self.ask_next("allocate", f"{changes}. This is permanent. Confirm? (y/n)", args=args)
            return
        leveling.allocate(c, spend)
        if self.combat:
            self.combat.refresh_player()
        self.store.save_player(self.player)
        console.note(f"Done. {c.unspent_points} points left.")
        self.show_header()

    def on_answer_allocate(self, asked: dict, text: str):
        """(f460) The answer to #allocate's question: yes spends the points (the command runs again, confirmed), no cancels, anything
        else lets the question go."""
        yes = questions.yes_no(text)
        if yes is None:
            return None
        if not yes:
            console.note("Cancelled.")
            return True
        self.allocate(asked["data"]["args"], confirmed=True)
        return True

    def header_key(self) -> tuple:
        """(f372) Everything the top bar shows, so a pane button that changed any of it redraws the bar."""
        c = self.player.character
        return (self.player.location, self.minutes, c.coins, c.xp, c.level, c.unspent_points,
                tuple(round(pools.current(c, p)) for p in pools.POOLS), tuple(pools.maximum(c, p) for p in pools.POOLS))

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

    def ask_next(self, kind: str, question: str, show: bool = True, speaker: str = "", data: dict | None = None, **more) -> None:
        """(f460) The world asks the player something, and the question ends the line: nothing more of the line is done (halted), the
        question is kept in the save (storage/campaign.py save_question: a rollback takes it back, a save closed on it asks again when it
        opens, a #command typed meanwhile runs and leaves it standing), and the next line typed answers it: handle() hands that line to
        on_answer_<kind>(asked, text) before anything else reads it. A handler returns True when the line was the answer (the turn is
        spent on it), False when it was not and the handler has said so in the world's words, None when it was not and nothing was said
        (handle() lets the question go with a line from data/rules/questions.yaml); either way the line is then read as new. `data` is
        what the handler needs to finish, JSON only: ids and names, never objects. `show` False when the site has spoken the question
        itself (in someone's voice); the question is kept for the re-ask at open either way. engine/questions.py has the whole of it."""
        if show:
            console.note(question)
        self.store.save_question({"kind": kind, "question": question, "speaker": speaker, "turn": self.store.meta.turn,     # (f461) speaker: whose voice it is re-asked in
                                  "data": {**(data or {}), **more}})
        self.halted = True

    @property
    def pending_clarify(self) -> dict | None:
        """(f321) The question the world asked about a line it could not read, with that line (and (f428) the far place it named).
        (f460) Kept in the save with the other questions, under the kind "clarify"; handle() reads it as before, after the intercepts."""
        asked = self.store.load_question()
        return asked["data"] if asked and asked.get("kind") == "clarify" else None

    @pending_clarify.setter
    def pending_clarify(self, value) -> None:
        if value:
            self.ask_next("clarify", value.get("question", ""), show=False, data=dict(value))
        elif self.pending_clarify is not None:
            self.store.clear_question()

    def handle(self, text: str) -> None:
        """The whole of a line, in one piece and with no operation around it (the tests' way in; the game's is turn(), f463)."""
        plan = self.read_line(text)
        if plan is None:
            return
        for i in range(len(plan)):
            if i and (self.combat or self.halted):
                console.debug(f"stopping after {i} of {len(plan)} actions")
                break
            self.run_step(i, plan, text)
        self.passage(text)
        self.after_steps(text)
        self.world_tick()
        self.settle_line()

    def read_line(self, text: str):
        """(f463) The line read: an answer to the world's question, a fight's round, an intercept, or the interpreter's plan after repair
        and audit. None when the line was taken whole here (or the world asked a question instead); else the plan to run, step by step.
        (f470) Two halves: take_line (the line taken whole, inside the line's operation) and understand (the interpreter and the audit,
        outside any transaction); this is their composition for handle() and the tests. turn() runs them apart."""
        if self.take_line(text):
            return None
        plan = self.understand(text)
        if plan is not None:
            self.pending_clarify = None                 # (f321) read, whether first time or as the answer to a question
        return plan

    def take_line(self, text: str):
        """(f470) The line taken whole, inside the line's operation: an answer to the world's question, a fight's round, or an intercept.
        True when it was; None when nothing here touched it (the operation is void) and False when something was said or written of it
        (a question let go) but the interpreter must still read it (understand)."""
        touched = False
        self.last_text = text
        self.interpret_calls = []                           # every interpreter call made for this line, kept for the turn log
        from llm import audit
        audit.note_turn(self.store.meta.turn, text)         # the model calls that follow are filed under this turn (f314)
        asked = self.store.load_question()
        if asked and asked.get("kind") != "clarify":                   # (f460) the world asked something last turn: this line answers it, before anything else reads it
            self.store.clear_question()
            handler = getattr(self, f"on_answer_{asked.get('kind', '')}", None)
            taken = handler(asked, text) if handler else None
            if taken is None:
                console.note(questions.dropped(self.rng))              # not an answer: the question is let go, said so, and the line read as new
            if taken:
                self.took(text, f"answer:{asked['kind']}")
                return True
            touched = True                                             # (f470) the question cleared, or let go: the operation commits that
        if self.combat:
            self.combat.turn(text)
            self.seal_ask()                                 # (f460) the High Keeper bloodied this round: the seal's question ends the turn
            self.took(text, "combat")
            if not self.combat and self.resume_pending and not getattr(self, "held_yield", None):
                self.resume_road()
            return True
        for ic in self.INTERCEPT_TABLE:                     # the intercepts, in their declared order (scenes/intercepts.py)
            if getattr(self, ic.method)(text):
                if ic.after:
                    getattr(self, ic.after)()
                console.debug(f"intercept: {ic.name} took the line")
                self.took(text, ic.name)
                return True
        return False if touched else None

    def understand(self, text: str):
        """(f470) The interpreter and the audit: model calls that read committed state and write nothing (the write fence says so),
        outside any transaction when turn() runs them. The plan to run, or None when the world asked a question instead (a `clarify`
        operation of its own, ask_back); a board refresh the interpreter's read brings due is a `board` operation of its own
        (scenes/guild_actions.py ensure_board)."""
        asked = getattr(self, "pending_clarify", None)
        if asked:                                                     # (f321) they were asked a question: this line answers it
            hint = (f"The game asked the player a question about their earlier line \"{asked['text']}\": \"{asked['question']}\". "
                    f"What they have typed now answers it. Read the earlier line and this answer together as one intention, and plan that.")
            plan = self.interpret(text, hint)
            text = f"{asked['text']} - {text}"
            self._asked_place = asked.get("place", "")         # (f428) a far place the question named: the answer may go there
        else:
            plan = self.interpret(text)
            self._asked_place = ""
        raw_plan = [a.model_dump(exclude_defaults=True) for a in plan]
        self.pending, self.halted = [], False
        plan = self.repair(text, plan)              # (f333) every repair the scene declares, in its declared order (scenes/plan_repairs.py)
        self.buffering = len(plan) > 1
        plan = self.audit_plan(text, plan, raw_plan)
        if plan is None:                            # the audit could not make sense of it: nothing happens, no time passes; the world has asked (f321)
            self.buffering = False
            return None
        self.sneaking, self.queued_buffs, self.fight_text = False, [], text      # what a fight the player starts this turn opens with (f248)
        self.line_text = text                       # (f463) the line as the steps read it (an answer joined to its question)
        return plan

    def run_step(self, i: int, plan: list, text: str) -> None:
        """(f463) One step of the plan: its checks, its action, what follows it (a stop on the road, a forced hand, its beats, its mark, the
        commissions and quests it touched, its time)."""
        intent = plan[i]
        text = getattr(self, "line_text", text) or text
        console.debug(f"intent {i + 1}/{len(plan)}: {intent.model_dump(exclude_defaults=True)}")
        self.pending_check, self.pending_beats = "", []
        self.step = intent                                 # (f416) what a refusal says did not happen
        if not self.run_checks(intent, text):
            from engine import actions
            if intent.kind not in actions.BY_KIND:
                console.debug(f"no such action kind: {intent.kind}")
                self.halted = True
                return
            self.__dict__.setdefault("ran", []).append(intent.kind)
            refused_before = sum(1 for r in ledger.ROWS if r.get("kind") == "refused")
            getattr(self, f"on_{intent.kind}")(intent, text)
            if self.player.road:                       # (f427) a hand for someone in need at a stop, or a way past what blocks it
                self.stop_step(intent, sum(1 for r in ledger.ROWS if r.get("kind") == "refused") > refused_before)
            if intent.force and intent.kind != "attack":
                self.after_force(intent, text)
            if self.pending_beats:
                self.narrate(" ".join(self.pending_beats), text)
        if intent.mark.strip():
            self.add_mark(intent.mark.strip())
        if self.player.commissions:
            self.collect_commissions()
        if self.player.quests:                                           # (f491) nothing expires: a contract is never forfeit by the clock
            if intent.kind in ("give", "show") and intent.target:        # (f378) handing the work over is handing it in; talk does it in on_talk
                self.turn_in(intent.target)
        if intent.kind in TIME_COST:
            self.advance(TIME_COST[intent.kind])
        self.line_done.append((getattr(intent, "summary", "") or "").strip() or intent.kind)   # (f463) for the part_stood line

    def after_steps(self, text: str) -> None:
        """(f463) After the plan's steps, (f466) outside any operation: the step is over and the line's buffering with it, the notes time
        raised in the middle of the line are shown (f418: after the passage), and what was not done is said. These are the line's own,
        not any one operation's to hold or roll back, and nothing is written."""
        text = getattr(self, "line_text", text) or text
        self.step = None
        undone = self.__dict__.pop("dropped_steps", [])
        if undone:                                             # (f332) the game does at most three things a line: say what it did not do
            from engine import refusals
            console.note("Three things at a time: not done - " + "; ".join(undone) + ". Say it again when you are ready.")
            refusals.note("undone", text, "more than three actions in one line: " + "; ".join(undone), self.player.location, self.store.meta.turn)
            ledger.add("not_done", steps=undone, say="NOT DONE this turn, never show them done: " + "; ".join(undone) + ".")   # (f416)
        self.release_time_notes()                               # (f418) after the passage
        if self.buffering and self.exits_due and not self.combat:
            self.show_exits(force=True)
        self.buffering = False

    def world_tick(self) -> None:
        """(f466) The world operation's body, after the line's actions and their passage: the dungeons kept whole and the pulse (the world
        moving on, the drift, the notices owed the player: its lines are this operation's, shown at its commit, after the passage, GOALS.md
        review Q36; a narration it asks for is a passage operation after it). It fails apart: a fault in the pulse rolls back the pulse
        alone, and what the player did stands."""
        self.ensure_dungeons()
        self.run_pulse()
        from engine import obligations
        obligations.lapse(self)                                  # (f481) work offers that no longer stand, withdrawn for their reason

    def passage(self, text: str) -> None:
        """(f463) The passage of a line of several actions, held back until here (flush). (f464) An operation of its own, before the pulse:
        the line's required call before the world's optional ones."""
        text = getattr(self, "line_text", text) or text
        self.flush(text)

    def arrival(self) -> None:
        """(f466) The arrival operation's body: a moment walked into, or someone come looking (engine/matters.py on_arrival, f317, after the
        line's own passage). What it stamps on the world (a situation told in the world's words, told_at) commits with it; the narrations
        it asks for are passage operations after its commit, so a telling that cannot be written undoes nothing of what was walked into."""
        from engine import matters
        matters.on_arrival(self)

    def settle_line(self) -> None:
        """(f463) The end of an interpreted line, in one piece (handle(), the tests' way in): the arrival, the law, and the turn counted.
        The game's turn() runs each as a world operation of its own (f466)."""
        self.arrival()
        self.law_check()
        self.store.meta.turn += 1

    REPAIRS = (
        plan_repairs.Repair("settle_targets", 12, "settle_targets", "a target written near enough to someone here is them: a tag like (elite), a stray space, a slip of the pen (f386)"),
        plan_repairs.Repair("scrub_markup", 10, "scrub_markup", "words in *asterisks* are never speech; a talk left wordless by that goes"),
        plan_repairs.Repair("wordless_talk", 20, "wordless_talk", "a second, wordless talk to the one the line already spoke to adds nothing (f299)"),
        plan_repairs.Repair("walk_after_word", 25, "walk_after_word", "a word, then a walk to the one it was said to: an acknowledgement on the way goes, else the walk does (f373)"),
        plan_repairs.Repair("move_to_present", 30, "move_to_present", "a move before a word or a deal with someone already here is no journey - unless the line names the place"),
        plan_repairs.Repair("party_word", 35, "party_word", "the same words to each of the party are one talk; a proposal to go or search, read as talk to them, is doing it (f386)"),
        plan_repairs.Repair("narrated_talk", 40, "drop_narrated_talk", "a talk whose words narrate another step is not speech; the one it named gets the deed (f333)"),
        plan_repairs.Repair("local_building", 50, "local_building", "'the inn' with no town named is this town's inn, not a far one (f333)"),
        plan_repairs.Repair("join_guild", 150, "join_guild_rewrite", "paying or asking to join, said to the clerk, is joining - once (f271, f282)"),
        plan_repairs.Repair("coin_offered", 160, "coin_offered", "coin offered to someone here is a give, whatever it was read as; coin to nobody goes to the one named"),
        plan_repairs.Repair("one_harvest", 170, "one_harvest", "skinning and harvesting is one action: a second step restating it goes"),
    )

    def scrub_markup(self, text: str, plan: list) -> list | None:
        if not markup.has_markup(text):
            return None
        for a in plan:
            if a.speech:
                a.speech = markup.scrub_speech(a.speech, text)
        return [a for a in plan if not (a.kind == "talk" and not a.speech)] or plan

    @staticmethod
    def wordless_talk(text: str, plan: list) -> list:
        """(f299) "...and I talk to the clerk": a wordless talk to whoever the line already spoke to adds nothing; and a wordless talk
        beside a deed, saying the deed's summary over again or aimed at the one the deed is for, is the deed's own narration."""
        def norm(s): return re.sub(r"\W+", " ", (s or "").lower()).strip()
        kept = []
        for k, a in enumerate(plan):
            if a.kind == "talk" and not (a.speech or "").strip() and len(plan) > 1:
                if any(b.kind == "talk" and b.target == a.target for b in plan[:k]):
                    continue
                others = [b for b in plan if b is not a and b.kind != "talk"]
                if others and any(norm(b.summary) == norm(a.summary) and a.summary.strip() or (a.target and b.target == a.target) for b in others):
                    continue
            kept.append(a)
        return kept or plan

    FILLER = re.compile(r"^\W*(?:u+h+|u+m+|h+m+|a+h+|o+h+|okay|ok|right|alright|all right|fine|sure|yeah|yes|well|so|i see)"
                        r"(?:[\s,.!]+(?:okay|ok|then|so|right|sure|fine|well|i see))*[\s.!]*$")

    def walk_after_word(self, text: str, plan: list) -> list | None:
        """(f373) 'uhh okay then, I head to the clerk at the desk' was read as words to the clerk, then a walk to her: she answered 'uhh okay
        then' with a recital of the rank rules before the player had reached her desk. When the words are only an acknowledgement (said to
        whoever spoke last), the walk is the step and the words go; when they are real words, the player is already speaking to them and
        the walk goes."""
        here = {n.id for n in self.present}
        out = list(plan)
        for k, a in enumerate(plan):
            if a.kind != "talk" or a.target not in here:
                continue
            walk = next((b for b in plan[k + 1:] if b.kind == "move" and b.destination == a.target), None)
            if walk is None:
                continue
            gone = a if self.FILLER.match(a.speech or "") else walk
            if gone in out:
                out.remove(gone)
        return out if len(out) != len(plan) and out else None

    def move_to_present(self, text: str, plan: list) -> list:
        here_ids = {n.id for n in self.present}
        said = {w for w in re.findall(r"[a-z]+", text.lower()) if len(w) > 3}
        norm = lambda s: " ".join(re.findall(r"[a-z]+", (s or "").lower()))
        echo = lambda b: b.kind == "talk" and norm(b.speech) and norm(b.speech) in norm(text) \
            and len(norm(b.speech).split()) >= 0.8 * len(norm(text).split())              # the whole line, not words quoted in it
        if re.match(r"^\s*(?:i\s+)?(?:go|head|walk|run|hurry|travel|make my way|set off|take me)\b", text.lower()) and any(echo(b) for b in plan):
            return [a for a in plan if not echo(a)] or plan          # (f384) "go to smith": a journey; the talk was the line itself, put in a mouth

        def named(dest: str) -> bool:                              # (f342) "to the trading square": the player named where; the move stands
            pl = self.world.places.get(dest)
            return bool(pl) and bool({w for w in re.findall(r"[a-z]+", pl.name.lower()) if len(w) > 3 and w not in ("the", "and")} & said)
        return [a for k, a in enumerate(plan)
                if not (a.kind == "move" and not named(a.destination)
                        and any(b.kind in ("talk", "give", "show", "buy", "sell", "commission") and b.target in here_ids for b in plan[k + 1:]))] or plan

    def join_guild_rewrite(self, text: str, plan: list) -> list | None:
        """Paying or asking to join the guild, said to the clerk, is joining - and only once."""
        if self.rank or not self.clerk_here() or NEGATED.search(text.lower()) or UNPAID.search(text.lower()):
            return None
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
        return kept

    def coin_offered(self, text: str, plan: list) -> None:
        """"I offer the guard 5 silver to look the other way" is giving coin, whatever it was read as; coin handed to nobody in
        particular goes to the one the line names (f333)."""
        here_ids = {n.id for n in self.present}
        coin_given = any(b.kind == "give" and self.coin_amount(b.item or "") for b in plan)
        for a in plan:
            if a.kind in ("talk", "other") and a.target in here_ids and self.coin_amount(text) and not coin_given \
                    and not NEGATED.search(text.lower()) and not PAST.search(text.lower()) \
                    and any(w in f"{text} {a.summary}".lower() for w in self.BRIBE_WORDS):
                m = re.search(r"(?:\d+|[a-z]+)\s+(?:gold|silver|copper)(?:\s+(?:and\s+)?(?:\d+|[a-z]+)\s+(?:gold|silver|copper))*", text.lower())
                a.kind, a.item = "give", (m.group(0) if m else "coins")
                coin_given = True
            if a.kind == "give" and not a.target and self.coin_amount(a.item or ""):
                a.target = self.named_here(text) or (self.partner.id if self.partner else "") or (self.present[0].id if len(self.present) == 1 else "")

    HARVEST_WORDS = ("harvest", "skin", "butcher", "gut", "carcass", "hide", "meat", "parts", "gather")

    def one_harvest(self, text: str, plan: list) -> list:
        return [a for k, a in enumerate(plan)       # skinning and harvesting is one action: a second "other" restating it is dropped
                if not (a.kind in ("other", "harvest") and k and any(b.kind == "harvest" for b in plan[:k])
                        and any(w in f"{a.summary} {a.item}".lower() for w in self.HARVEST_WORDS))] or plan

    def settle_targets(self, text: str, plan: list) -> list:
        """(f386) The plan repair that puts a step on the one it means. A night's runs had 'wildlife:hippogriff (elite)', 'wildlife: raven',
        'bixdie_wigglewick' and a prisoner at the player's side all ruled 'not here', and the questions asked back made it worse."""
        from engine.actions import TARGETED
        for a in plan:
            if a.kind in TARGETED and a.target:
                a.target = self.settle_target(a.target)
        return plan

    def settle_target(self, target: str) -> str:
        """The id of the one here a written target means: the id itself; without a tag in brackets or a stray space; 'wildlife:...' when
        a creature is about; by name or by how the player knows them; or by a near spelling of any of those. Else as it was written."""
        import difflib
        from engine import truth
        present = truth.scene_of(self).present_people()
        ids = {p.id.lower(): p.id for p in present}
        t = re.sub(r"\s*:\s*", ":", (target or "").strip().lower())
        t = re.sub(r"\s*\([^)]*\)", "", t).strip()
        if t in ids:
            return ids[t]
        if t.split(":", 1)[0] == "wildlife" and "wildlife" in ids:
            return ids["wildlife"]
        plain = lambda s: re.sub(r"^the\s+", "", re.sub(r"\s*\([^)]*\)", "", (s or "").strip().lower().replace("_", " ")))
        bare = plain(t.split(":", 1)[-1])
        pool = {}
        for p in present:
            for k in (p.id.lower(), plain(p.name), plain(p.label)):
                if k:
                    pool.setdefault(k, p.id)
        if bare in pool:
            return pool[bare]
        near = difflib.get_close_matches(t, list(pool), n=1, cutoff=0.85) or difflib.get_close_matches(bare, list(pool), n=1, cutoff=0.85)
        return pool[near[0]] if near else target

    def drop_narrated_talk(self, text: str, plan: list) -> list:
        """(f333) A talk step whose 'speech' is the player describing an action the plan already has ("I give Bram a healing draught" beside
        a give) is not words said: it is dropped, and the person it named is given to the deed when that lacks one. Spoken words in quotes
        are never touched, and a talk that is the only step stays. When every step was handed the whole line as its speech and the line
        has as many clauses as the plan has steps, each step's words are its own clause ("I buy a meal, then ask Hollis about the roads")."""
        from engine import actions
        if len(plan) < 2 or markup.has_markup(text) or '"' in text:
            return plan
        whole = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", text.lower())).strip()
        clauses = [c.strip() for c in re.split(r",?\s+(?:and then|then|and)\s+|;\s*", text.strip()) if c.strip()]
        kept, lost = [], []
        for k, a in enumerate(plan):
            if a.kind == "talk" and a.speech.strip():
                speech = a.speech.strip()
                same = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]+", " ", speech.lower())).strip() == whole
                if same and len(clauses) == len(plan) > 1:
                    speech = a.speech = clauses[k]
                    same = False
                said = re.sub(r"^\W*(?:i|we)\s+(?:try to |go to |will |'ll )?", "", speech.lower())
                verbs = {w for b in plan if b is not a and b.kind != "talk" for w in actions.BY_KIND[b.kind].verbs + actions.BY_KIND[b.kind].words}
                lead = re.findall(r"[a-z']+", said)[:2]                  # "give bram", "throw dice", "offer the": the action is in the first two words
                narrated = any(w in verbs for w in lead) or any(" ".join(lead).startswith(v + " ") for v in verbs if " " in v)
                here = any(n.id == a.target for n in self.present)
                first_person = actions.first_person_action(speech, here) and any(b.kind != "talk" for b in plan)   # (f420) the one definition
                to_someone = re.search(r"\b(you|your|yours|you're|you've|you'll|please|thanks|thank you)\b", speech.lower()) is not None
                if narrated or (same and first_person and not to_someone):   # the whole line, told in the first person to nobody, is the player narrating
                    console.debug(f"dropped a talk narrating the {[b.kind for b in plan if b is not a]} step: {a.speech[:60]!r}")
                    lost.append(a.target)
                    continue
            kept.append(a)
        for t in [t for t in lost if t]:                                 # the one the talk named is who the deed is for
            for b in kept:
                if b.kind in actions.TARGETED and not b.target:
                    b.target = t
        return kept or plan

    def named_here(self, text: str) -> str:
        """The id of the one person here the line names, by name or by trade ("the guard", "Bram"); '' when none or several. A hire in
        the party counts as here."""
        low = text.lower()
        hits = []
        for n in self.present:
            words = {n.role.replace("_", " ")} | ({n.name.split()[0].lower()} if regard.of(n, self.acting).name_known and n.name else set())
            if any(re.search(rf"\b{re.escape(w.lower())}\b", low) for w in words if w):
                hits.append(n.id)
        for m in self.player.party:
            if m.get("permanent") and m.get("name") and re.search(rf"\b{re.escape(m['name'].split()[0].lower())}\b", low):
                hits.append(f"hire:{m['id']}")
        return hits[0] if len(hits) == 1 else ""

    def local_building(self, text: str, plan: list) -> None:
        """(f333) "Let's head to the inn": a building named by its kind, with no town named, is this town's when it has one; the model is
        shown the nearest of that kind in other towns too, and sometimes picks one of those."""
        from engine import mapview, truth
        low = text.lower()
        here_top = mapview.top_of(self.world, self.player.location)
        kinds = {kind for kind, words in truth.T["building_words"].items() if any(re.search(rf"\b{re.escape(w)}\b", low) for w in words)}
        if not kinds:
            return
        for a in plan:
            if a.kind != "move" or a.destination not in self.world.places:
                continue
            dest = self.world.places[a.destination]
            if dest.type not in kinds or mapview.top_of(self.world, a.destination) == here_top:
                continue
            far_town = self.world.places.get(mapview.top_of(self.world, a.destination))
            if far_town is not None and re.search(rf"\b{re.escape(far_town.name.lower().removeprefix('the '))}\b", low):
                continue                                              # they named that town: they mean its inn
            local = next((pid for pid, p in self.world.places.items() if p.type == dest.type and mapview.top_of(self.world, pid) == here_top and pid != self.player.location), None)
            if local:
                console.debug(f"destination {a.destination} ({dest.type}) read as this town's: {local}")
                a.destination = local

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
        elif name.split()[0] == "pronoun":                  # (f386) how the people of the world see the player: '#pronoun she|he|they'
            from engine import truth
            want = (name.split() + [""])[1]
            if want in truth.SEEN_AS:
                self.player.character.pronoun = want
                self.store.save_player(self.player)
            console.note(f"People see you as {'someone they cannot place' if truth.player_pronoun(self.player.character) == 'they' else truth.SEEN_AS[truth.player_pronoun(self.player.character)][3:]}"
                         " (#pronoun she, #pronoun he or #pronoun they to change it).")
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
                    console.show_inventory(self.player.character, self.carried_things())
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
        elif name in ("menu", "mainmenu", "saves"):
            if self.combat:                                         # (f345) a fight is saved every round, but it is not left mid-blow
                console.note("Not in the middle of a fight. Finish it, or flee, first.")
            else:
                console.note("Saved.")
                self.to_menu = True
        elif name.split()[0] == "attradd":
            self.attribute_click(name.split()[1] if len(name.split()) > 1 else "")
        elif name.split()[0] in ("allocate", "alloc", "assign"):
            self.allocate(name.split(maxsplit=1)[1] if " " in name else "")
        elif name.split()[0] in ("inventory", "inv", "i"):
            c = self.player.character
            console.show_inventory(c, self.carried_things())
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
        elif name == "report" or name.startswith("report "):
            self.report_content(text.split(" ", 1)[1].strip() if " " in text else "")      # (f364) what the player just saw, kept with the calls behind it
        elif name == "credits":
            from core import credits
            console.out(credits.text())
        elif name in ("help", "h", "?"):
            console.show_help()
        else:
            console.note(f"Unknown command '{text}'. Type #help for the list.")

    def save(self) -> None:
        self.store.save_player(self.player)
        self.store.save_meta()

    def people_view(self) -> list[tuple[str, str, str]]:
        """Who is here, as the player knows them, for the narrator (engine/truth.py, f313). The hires travelling with the player are not
        scenery (f349): they are left out, and the narrator hears of one only when the GAME EVENT has them act (companions_in)."""
        from engine import truth
        from engine import recognition
        by_id = {n.id: n for n in self.present}
        return [(p.label, (f"{work}. " if (work := truth.their_work(p.label, p.role)) else "") + p.desc
                 + ((" " + knows) if (knows := recognition.seen(by_id[p.id], self.minutes, self.acting) if p.id in by_id else "") else ""), p.doing)   # (f378) work; (f382) knows you
                for p in truth.scene_of(self).present_people() if p.kind not in ("wildlife", "hire", "companion")]

    FIRST_SEEN = 2

    def first_seen(self, people: list[tuple[str, str, str]]) -> tuple[list[tuple[str, str, str]], int]:
        """(f380) Walking in, the people the eye falls on first, and how many more there are. With no length to hold it (f375) an arrival
        walked the room one person at a time: ten at the guild hall, each with a look and a doing, though the narrator was told 'the place
        and one person'. So the engine chooses: those the player knows by name, then whoever the place is kept by (its first role: the
        clerk at the hall, the keeper of an inn), then by chance; the rest are a number until the player looks."""
        from engine import truth
        ps = [p for p in truth.scene_of(self).present_people() if p.kind not in ("wildlife", "hire", "companion")]
        if len(people) <= self.FIRST_SEEN:
            return people, 0
        kept_by = next(iter(self.place.residents or {}), "")
        rng = random.Random(f"{self.store.meta.seed}:first_seen:{self.player.location}:{self.minutes // 60}")
        order = sorted(ps, key=lambda p: (0 if p.kind == "maren" or (p.name and p.label == p.name) else 1 if p.role and p.role == kept_by else 2,
                                          rng.random()))
        first = {p.label for p in order[:self.FIRST_SEEN]}
        shown = [t for t in people if t[0] in first]
        return shown, len(people) - len(shown)

    def seen_as(self, n) -> str:
        """(f378) A townsperson as the narrator's frames list them: how the player knows them, and their work when that does not say it."""
        from engine import truth
        work = truth.their_work(n.label(self.acting), n.role)
        return f"{n.label(self.acting)}, {work}" if work else n.label(self.acting)

    def companions_in(self, event: str) -> list[str]:
        """(f349) The hires the GAME EVENT names, so the narrator may show what one of them does; the rest go unmentioned."""
        low = (event or "").lower()
        return [m["name"] for m in self.player.party if m.get("permanent") and not m.get("story") and m.get("name")
                and re.search(rf"\b{re.escape(m['name'].split()[0].lower())}\b", low)]

    def opening_passage(self, event: str) -> None:
        """(f525) The game's opening passage (the first waking, or where a loaded game left off). When it cannot be written the narrator's
        plain line stands in, picked from the scene's stream so the seed decides it, and the game reaches its first line all the same;
        until the owner's lines are in, the failure goes on up as before."""
        import copy
        told = ("_arrival_lines", "_happenings_seen", "_news_seen", "_crowd_told")    # (f525's review) what the passage tells once
        kept = {k: copy.deepcopy(self.__dict__[k]) for k in told if k in self.__dict__}
        try:
            self.narrate(event)
        except LLMError as e:
            for k in told:                               # the passage was never written: what it would have told is still to tell
                if k in kept:
                    self.__dict__[k] = kept[k]
                else:
                    self.__dict__.pop(k, None)
            line = failures.opening_untold(self.rng)
            if line is None:
                raise
            console.debug(str(e))
            console.narrate(line)

    def narrate(self, event: str, player_text: str = "") -> None:
        """A passage the narrator is asked for. Several actions in one line: held back and told together at the end (flush, the passage
        operation). (f464) Inside an operation of a line: a passage operation of its own, run once this one has committed, shown at this
        place in what the player reads (mark_passage); its failure shows what stood in the narrator's plain words and undoes nothing.
        Outside a line (the game opening, a test's handle()): now."""
        if self.buffering:
            self.pending.append(event)
            return
        from engine import operation as _op
        if self.collecting and _op.current() is not None:
            self.mark_passage("passage", lambda: self._narrate_now(event, player_text), self.stood_standin)
            return
        self._narrate_now(event, player_text)

    weight_hint = None
    camp_fight = None
    last_social = None

    def _narrate_now(self, event: str, player_text: str = "") -> None:
        event = hygiene.undash(event)                                    # (f413) what the narrator is told happened has no dashes to copy (f403)
        marks = self.store.load_place(self.player.location).marks
        self.weight_hint = None                                          # (f375) a moment's weight no longer sets a length
        strict = voice_rules.NOTHING in event
        from engine import truth
        here = truth.scene_of(self).view(truth.NARRATOR, "narrator")
        prof = self.world.town(self.player.location)
        seen = self.__dict__.setdefault("_happenings_seen", set())
        unseen = [h for h in here.lines("happenings") if (self.player.location, h) not in seen]    # (f323) told once, and again when it changes
        seen.update((self.player.location, h) for h in unseen)
        unseen = self.__dict__.pop("_arrival_lines", []) + unseen                                  # (f331) what changed here while the player was away, once
        self.__dict__.setdefault("_news_seen", set()).update(here.lines("news")[:3])              # (f349) news the narrator has been handed once
        streets = here.streets()
        crowd = [f.text for f in here.scene.facts("here") if f.id == "crowd" and f.text in streets]
        told = self.__dict__.setdefault("_crowd_told", {})                                         # (f385) the crowd once a visit to the town,
        town = pulse.town_of(self.world, self.player.location)                                      # and again only when it changes: "cart drivers
        streets = [s for s in streets if not (s in crowd and told.get(town) == s)]                 # eating in the inn" came back as drivers in
        for s in crowd:                                                                             # passage after passage
            told[town] = s
        people, unlooked = self.people_view(), 0
        if not self.__dict__.pop("_looking", False) and not (self.__dict__.get("_shown_here") or {}).get("place"):
            people, unlooked = self.first_seen(people)                                       # (f380) walking in: who the eye falls on first
        request = wp.narration_request(self.time_label(), self.place, people, event, player_text,
                                       self.recent_narration, self.gear_line(), marks,
                                       [inv.label(i) for i in self.ground_here()] + self.lying_here(),
                                       unseen, streets=streets,
                                       town=" ".join(prof.character.split()) if prof and not self.place.danger else "",
                                       news=here.lines("news")[:3],                                 # (f331) the narrator hears what the town is talking about
                                       already=self.shown_lines(),                                  # (f347) ...and what the player has read here already
                                       companions=self.companions_in(event),                        # (f349) ...and of a companion only when the event has them act
                                       worn=self.worn_words("prose"),                               # (f349) ...and which words it has worn out lately
                                       unlooked=unlooked,
                                       who=entities.who_is_who(self),                               # (f392) who is who, never guessed at
                                       fallen=here.lines("fallen"),                                 # ...and who fell, never seen alive again
                                       parts=features.lines(self),                                  # (f394) the parts of this place, real
                                       told=ledger.told(),                                          # ...and what the engine did this turn
                                       habits=self.arrival_habits() + self.habits_due("rest"))      # (f412) ...and the companions' habits, to fold in
        result = fresh("narrate", wp.NARRATOR_SYSTEM, request, Narration, self.recent_narration, max_tokens=config.PROSE_MAX_TOKENS,
                       temperature=0.4 if strict else 0.9, worn=self.worn_words("prose"), said=player_text or "")         # (f384) no invented speech
        shown = self.unnamed(result.text)
        if strict and voice_rules.contradicts_nothing(shown):
            console.debug("narration claimed a gain the engine did not give - rewriting once")
            retry = generate("narrate", wp.NARRATOR_SYSTEM,
                             request + "\n\nYOUR DRAFT CLAIMED SOMETHING WAS GAINED, MADE OR FINISHED. Nothing was. Rewrite it so the player only "
                                       "tries: no coins, no objects appearing, no work completed, no change to their purse or pack.",
                             Narration, temperature=0.2, max_tokens=config.PROSE_MAX_TOKENS)
            shown = self.unnamed(retry.text)
            if voice_rules.contradicts_nothing(shown):
                shown = voice_rules.ATTEMPT_ONLY
        if "gasp" in event or "breath" in event:
            shown = voice_rules.mention_once(shown, ("gasp", "gasped", "gasping"))
        console.narrate(shown)
        self.note_shown(shown)
        self.remember_narration(shown)
        self.adopt_from_passage(shown)                                                           # (f394) what it named is real now
        self._wrote_turn = True                                                                  # (f351) the narrator wrote this turn: its passage is the room's update

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

        shut = self.shut_roads()

        def row(pid: str, state: str) -> dict | None:
            found = w.path(here, pid)
            if not found:
                return None
            pl = w.places[pid]
            away = clock.describe_duration(found[1])
            if shut and self.shut_on(found[0]):                                 # (f541's review) the walk that can be made, not the shut one
                around = self.route_round(here, pid)
                found, away = (around, f"{clock.describe_duration(around[1])}, the long way round") if around else \
                    (found, f"{away}, but the road is shut")
            return {"id": pid, "name": pl.name, "type": pl.type, "minutes": found[1], "away": away, "state": state}
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
        r = self.world.roads.get(place_id) if p is None else None             # (f540) a road a situation lies on, by its name
        return p.name if p else r.name if r else "somewhere on the road"

    def people_elsewhere(self) -> list:
        """Everyone the player has met who is not here: from the index, not the records (storage.campaign.NPCRow)."""
        from engine import retrieval
        return retrieval.met_elsewhere(self.store, [n.id for n in self.present])

    def interpret(self, text: str, hint: str = "") -> list[ActionIntent]:
        """What the player typed, read into actions. The interpreter is shown only what the words could be about (engine/candidates.py):
        this town and its ways out plus any place named or close in meaning, the people met who are named, and a catalogue (wares, the
        pack, abilities...) only when the words are about that kind of thing."""
        from engine import candidates as cand
        places = features.candidates(self) + cand.places(self.world, self.player.location, text)   # (f394) the parts of this place first
        from engine import truth
        _sc = truth.scene_of(self)
        people = [(p.id, p.label, f"{p.role}. {p.plain} {p.doing}" + (f" {p.note}" if p.note else "")) for p in _sc.present_people() if p.kind == "npc"]
        away_rows = self.people_elsewhere()
        away_rows = away_rows + self.town_people_named(text, {n.id for n in away_rows} | {n.id for n in self.present})   # (f342)
        shown_away = cand.people_elsewhere(away_rows, text)
        left = next((n for n in away_rows if n.id == self.last_spoken and n.location == self.player.location and n.away_until > self.minutes), None)
        if left is not None and all(n.id != left.id for n in shown_away):
            shown_away.append(left)                       # the one who just walked off is always listed: "wait for them" must resolve
        elsewhere = [(n.id, f"{n.label(self.acting)} ({n.role.replace('_', ' ')})",
                      "just walked away from here and can't be spoken to for a short while"
                      if n.location == self.player.location and n.away_until > self.minutes else self.where_name(n.location))
                     for n in shown_away]
        last = self.last_spoken if left or any(n.id == self.last_spoken for n in self.present) else None
        people = people + [(p.id, f"{p.label} ({p.note})", f"{p.desc} {p.doing}.") for p in _sc.present_people() if p.kind in ("maren", "hire", "companion")]
        people = people + [(p.id, p.label, p.desc) for p in _sc.present_people() if p.kind == "wildlife"]
        short = cand.I["always_if_short"]
        wares_all = [f"{w.id}: {w.name} - {money.words(self.quote_ware(n, w).price)} (sold by {n.label(self.acting)}, id {n.id})"   # (f333) the id alone first: the model copies
                     for n in self.present for w in self.wares_of(n)] \
            + [f"{i.name}: {i.rarity}, level {i.item_level} - {money.words(p)} (stock of {n.label(self.acting)}, id {n.id})" for n, i, p in self.stock_here()]
        from engine import loadout
        abilities_all = [f"{a.id}: {a.name} ({a.field_use or a.effect.value}{', in a fight' if a.context.value == 'combat' else ''})"
                         for a in loadout.prepared(self.player.character)]
        pack_all = [inv.label(i) for i in self.pack]
        recipes_all = [inv.GOODS[next(iter(r.makes))].name for r in inv.RECIPES.values()]
        buyers_all = [f"{n.id} ({n.label(self.acting)}) buys {', '.join(self.world.roles[n.role].buys)}" for n in self.present if self.world.roles[n.role].buys]
        stash_all = [inv.label(i) for i in self.player.stash] if self.can_store() else None
        shown = {"wares": cand.catalogue(text, "wares", wares_all, short), "abilities": cand.catalogue(text, "abilities", abilities_all, short),
                 "pack": cand.catalogue(text, "pack", pack_all, short), "recipes": cand.catalogue(text, "recipes", recipes_all, short),
                 "buyers": cand.catalogue(text, "buyers", buyers_all, short),
                 "stash": cand.catalogue(text, "stash", stash_all, short) if stash_all is not None else None}
        left_out = [k for k, full in (("wares", wares_all), ("abilities", abilities_all), ("pack", pack_all), ("recipes", recipes_all),
                                      ("buyers", buyers_all), ("stash", stash_all or [])) if full and not shown[k]]
        from engine import mapview as _mv
        here_top = _mv.top_of(self.world, self.player.location)
        shown_places = []
        for pid, name in places:                                      # (f333) the kind of place, and whose town when it is not this one
            if pid not in self.world.places:                          # (f394) a part of this place: already said as one
                shown_places.append((pid, name))
                continue
            p_ = self.world.places[pid]
            top_ = _mv.top_of(self.world, pid)
            tag = p_.type if p_.type not in ("town", "city", "village") else ""
            if top_ != here_top and top_ != pid and top_ in self.world.places:
                tag = (tag + ", " if tag else "") + f"in {self.world.places[top_].name}"
            shown_places.append((pid, f"{name} ({tag})" if tag else name))
        req = wp.interpret_request(self.time_label(), self.place.name, shown_places, people, elsewhere,
                                   self.partner.id if self.partner else None, last, text,
                                   shown["wares"], shown["abilities"], shown["pack"], [inv.label(i) for i in self.ground_here()] + self.lying_here(),
                                   shown["stash"] if stash_all is not None else None, shown["buyers"], shown["recipes"],
                                   [k.name for k in self.player.character.key_items],
                                   markup.describe(text) if markup.has_markup(text) else "", hint,
                                   [f"{b['n']}. [{b['letter']}] {b['title']}" for b in self.board_data()["postings"]]
                                   if self.clerk_here() else (),
                                   [f"[{q['letter']}] {q['title']}" for q in self.player.quests], left_out=left_out)
        self.last_interpret = {"chars": len(wp.INTERPRET_SYSTEM) + len(req), "places": len(places), "people_away": len(elsewhere),
                               "of_places": len(self.world.places) - 1, "of_people_away": len(away_rows), "left_out": left_out}
        read = generate("interpret_action", wp.INTERPRET_SYSTEM, req, ActionPlan, temperature=0.2, max_tokens=700)
        actions = read.actions
        self.dropped_steps = [(a.summary or a.kind).strip() for a in read.dropped]        # (f332) a fourth thing and beyond: told to the player, not lost
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
        self.stance = ""

    @staticmethod
    def looks_like_exploring(dest: str, text: str) -> bool:
        t = f"{dest} {text}".lower()
        return any(w in t for w in ("follow", "shortcut", "short cut", "trail", "track", "path", "explore", "find a way",
                                    "see where", "wander", "look for a way", "cut through", "hidden"))

    GENERIC_WORDS = __import__("engine.candidates", fromlist=["GENERIC"]).GENERIC     # (f420) the one list, in interpret.yaml generic_words

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
            if n.id == dest or n.role == d or d in n.label(self.acting).lower().replace(" ", "_"):
                return n
        for role in self.ROLES_OF.get(kind, ()):
            for n in self.present:
                if n.role == role:
                    return n
        return None

    def no_such_place(self, dest: str) -> str:
        """(f418) The answer to a walk somewhere the game does not know, in the world's words and with the ways that are real: 'There's
        no such place.' read as the innkeeper's answer to 'I head up to our rooms', four times a night. (Rooms, doors and the party as
        places to go come with the work on places within places.)"""
        known = self.known_places()
        near = [self.world.places[p].name for p in self.world.neighbors(self.player.location) if p in known and p in self.world.places][:4]
        words = " ".join(dest.replace("_", " ").split()) or "that"
        return (f"You look about for {words}, but nothing here goes by that name."
                + (f" From here the ways you know lead to {', '.join(near[:-1]) + ' and ' + near[-1] if len(near) > 1 else near[0]}." if near else ""))

    def walk_over(self, npc) -> None:
        self.end_conversation()
        self.last_spoken = npc.id
        console.note(f"You walk over to {npc.label(self.acting)}.")
        self.halted = False

    @staticmethod
    def names_person(text: str, row) -> bool:
        """Do the words name this person: their name, their epithet, or their trade ('the smith', 'the blacksmith', 'smithy')?"""
        said = {w for w in re.findall(r"[a-z]+", (text or "").lower()) if len(w) >= 4}
        role = row.role.replace("_", " ")
        theirs = {w for w in re.findall(r"[a-z]+", f"{row.name} {row.epithet or ''} {role}".lower()) if len(w) >= 4}
        return any(w == v or w.endswith(v) or (w.startswith(v) and len(w) - len(v) <= 2) or (v.endswith(w) and len(w) >= 5)
                   for w in said for v in theirs) or row.id in (text or "").lower().split()             # blacksmith, smithy, smiths

    def town_people_named(self, text: str, exclude: set) -> list:
        """(f342) People of this town, wherever in it they work, whom the words name - met or not. The smith of Parth works in the
        streets, not in the square; a player who saw her at the gate and asks for 'the smith' from the square means her."""
        from engine import mapview, retrieval
        top = mapview.top_of(self.world, self.player.location)
        if not top or self.world.places[top].danger:
            return []
        rows = retrieval.people_in_town(self.store, self.world, top)
        return [r for r in rows if r.id not in exclude and r.location != self.player.location and self.names_person(text, r)]

    def town_person(self, dest: str = "", kind: str = ""):
        """(f342) Someone of this town, not here, who is what the player means: a trade word ('the smith'), or whoever works in that
        kind of building ('the smithy' in a town that has a smith but no smithy). The nearest first."""
        from engine import mapview, retrieval
        top = mapview.top_of(self.world, self.player.location)
        if not top or self.world.places[top].danger:
            return None
        here = {n.id for n in self.present}
        rows = [r for r in retrieval.people_in_town(self.store, self.world, top) if r.id not in here and r.location != self.player.location]
        wanted = [r for r in rows if dest and self.names_person(dest, r)] or [r for r in rows if kind and r.role in self.ROLES_OF.get(kind, ())]
        if not wanted:
            return None
        def walk(r):
            found = self.world.path(self.player.location, r.location)
            return found[1] if found else 10 ** 9
        return min(wanted, key=walk)

    def go_to_person(self, row, text: str) -> None:
        """(f342) Walk to where someone of this town is (their work, or their routine place at this hour, f352) and over to them; when they
        are not about at this hour, say so, and where they usually are."""
        from engine import routines
        dest = routines.where_now(self.world, self.store.meta.seed, row, self.minutes, self.streets_now()[1])
        if dest != self.player.location:
            self.travel_route(dest, text)
            if self.halted:
                return
        npc = next((n for n in self.present if n.id == row.id), None)
        if npc:
            self.walk_over(npc)
        else:
            usual = routines.usual_line(self.world, self.store.meta.seed, row)
            self.refuse(f"{row.label(self.acting)} works here, but is not about at this hour." + (f" You might find them {usual}." if usual else ""))

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
            on_trail = self.fresh_trail() and self.toward_trail(dest, text)
            if self.part_move(dest, text):                                             # (f394) a part of this place, or further in
                if on_trail and not self.halted:                                       # ...where the signs led: follow them on there
                    self._following = True
                    intent.seek = ""
                    self.on_search(intent, text)
                return
        if dest.startswith("feature:"):
            dest = dest.split(":")[-1].replace("_", " ")
        if dest not in self.world.places:
            person = self.local_person(dest)
            if person:
                self.walk_over(person)
                return
            row = self.town_person(dest)                                # (f342) 'the smith', who works across town
            if row:
                self.go_to_person(row, text)
                return
            if not any(dest.lower() in pl.name.lower() or dest == pl.id for pl in self.world.places.values()):
                if self.fresh_trail() and self.toward_trail(dest, text):                 # (f381) going where the signs led
                    self._following = True
                    intent.seek = ""
                    self.on_search(intent, text)
                    return
                if self.part_move(dest, text, adopt=True):                              # (f394) a part a place like this would have
                    return
                if self.part_of_here(dest):                                             # (f381) a spot inside this place
                    self.within_place(dest, text)
                    return
                if self.place.danger or self.place.type in ("hut", "camp", "grove", "spring", "shrine", "ford", "cabin", "cave",
                                                            "ruin", "hollow", "overlook") or self.looks_like_exploring(dest, text):
                    intent.seek = intent.seek or dest
                    self.on_explore(intent, text)
                    return
                console.debug(f"'{dest}' is not a place - stopping the action chain")
                self.refuse(self.no_such_place(dest))
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
                row = self.town_person(dest, self.world.places[dest].type)      # (f342) ...or has them somewhere else in town
                if row:
                    self.go_to_person(row, text)
                    return
                tgt = self.world.places[dest]
                found = self.world.path(self.player.location, dest)
                away = f", {clock.describe_duration(found[1])} away" if found else ""
                self.refuse(f"There is no {tgt.type} in {here_town}. The nearest is {tgt.name} in "
                             f"{self.world.places[mapview.top_of(self.world, dest)].name}{away}. Say where you want to go to head there.")
                return
            if self.far_unnamed(dest, text):
                return
        self.travel_route(dest, text)

    def far_unnamed(self, dest: str, text: str) -> bool:
        """(f428, the owner's review Q17) A far place the player's words do not name is never walked to on a guess: "For major cities
        they need to say it exactly but for places off a road or locations it can ask." A city or town not named is no move, and the
        ways from here are said; any other far place is asked about. The f425 night: "along the shoreline" walked a party 85 hours to
        the drowned shore, "along the ridge" toward Windbreak Ridge, "toward the stone steps" to another crypt, "the exit" to the next
        town - three of four runs, two deaths. True when it answered instead of walking."""
        I = __import__("engine.candidates", fromlist=["I"]).I
        if not text.strip() or dest == getattr(self, "_asked_place", ""):
            return False
        road = self.player.road or {}
        if dest in (road.get("bound"), road.get("resume")) or (road.get("id") == self.player.location
                                                               and dest in self.world.places[road["id"]].connects):
            return False                                    # walking on from a stop: the way the journey was going
        found = self.world.path(self.player.location, dest)
        if not found or found[1] <= I["far_walk_minutes"] or self.names_place(dest, text):
            return False
        tgt = self.world.places[dest]
        away = clock.describe_duration(found[1])
        if tgt.type in I["say_exactly_types"]:
            self.refuse(f"Where to? {tgt.name} is {away} from here: name it to set out for it.")
            return True
        self.ask_back("far_place", text, f"the words do not name a place; the nearest that might be meant is {tgt.name}, {away} away",
                      place=dest)
        return True

    def names_place(self, dest: str, text: str) -> bool:
        """(f428) Do the player's words name this place by a word of its own: not a word for what kind of place it is ('the shore', 'the
        ridge', 'the crypt'), which names any of them."""
        from engine import mapview
        I = __import__("engine.candidates", fromlist=["I"]).I
        w = self.world
        said = set(re.findall(r"[a-z]+", text.lower()))
        top = w.places.get(mapview.top_of(w, dest))
        common = set(self.GENERIC_WORDS) | set(I["landform_words"])
        names = [w.places[dest].name] + ([top.name] if top is not None and top.id != dest else [])
        own = {t for n in names for t in re.findall(r"[a-z]+", n.lower()) if len(t) > 3 and t not in common}
        if not own:                                         # a name made only of common words names itself whole
            own = {t for n in names for t in re.findall(r"[a-z]+", n.lower()) if len(t) > 3}
        return bool(own & said)

    def travel_route(self, dest: str, text: str, already: int = 0, events: int = 0) -> None:
        """Walk the quickest way to dest. `already` is time already spent on the way (a fork's shared stretch), taken off the walk."""
        found = self.world.path(self.player.location, dest) if dest in self.world.places else None
        if not found:
            self.refuse("You don't know a way there from here.")
            self.show_exits()
            return
        route, walk = found
        barrier = self.shut_on(route)                                           # (f541) a road a situation has shut, on the way
        if barrier:
            B = roads.R["barrier"]
            r_ = self.world.roads[barrier[1]]
            say = {"road": r_.name[:1].upper() + r_.name[1:], "why": barrier[2].rstrip("."), "dest": self.world.places[dest].name}
            if (self.here_stop() or {}).get("barrier") == barrier[1] and not self.met_closure(barrier[1]):
                self.meet_closure(barrier[1])                                    # (f541's review) met where they stand: never a barrier further on
            if self.has("wayfinder") is not None:
                console.note(B["wayfinder"].format(**say))
                barrier = None
            elif self.met_closure(barrier[1]):                                   # met already: the long way round, or not at all
                around = self.route_round(self.player.location, dest)
                if around is None:
                    self.refuse(B["refused"].format(**say))
                    return
                if around[1] > B["ask_ratio"] * max(1, walk) and not re.search(roads.R["hazard"]["around_words"], (text or "").lower()):
                    self.refuse(B["ask"].format(**say, time=clock.walk_words(around[1])))     # (f541's review) a long detour is asked for
                    return
                console.note(B["around"].format(**say))
                (route, walk), barrier, already = around, None, 0       # the walk out to a fork is not part of the way round
        free = pulse.way_out(self.world, self.player.location)                 # (f390) a closure never shuts in whoever is already there
        near = self.near_end(self.here_stop()) if self.here_stop() else ""
        if near:
            free |= pulse.way_out(self.world, near)                             # (f541's review) nor on a road whose barrier is ahead of them
        passed = [p for p in route[1:] if p in free and pulse.closed_reason(self.store, p, self.minutes)]
        blocked = next(((p, pulse.closed_reason(self.store, p, self.minutes)) for p in route[1:]
                        if p not in free and pulse.closed_reason(self.store, p, self.minutes)), None)
        if blocked and self.has("wayfinder") is not None:
            console.note(f"The way through {self.world.places[blocked[0]].name} is closed ({blocked[1]}), "
                         "but you know a way around.")
            blocked = None
        if blocked:
            left = pulse.closed_until(self.store, blocked[0], self.minutes) - self.minutes
            days, hours = round(left / 1440), max(1, round(left / 60))
            when = (" Nobody can say when it will open again." if not 0 < left <= 30 * 1440 else
                    f" It should open again in about {days} day{'s' if days != 1 else ''}." if days else
                    f" It should open again in about {hours} hour{'s' if hours != 1 else ''}.")
            self.refuse(f"The way through {self.world.places[blocked[0]].name} is closed: {blocked[1].rstrip('.')}.{when}")
            return
        if passed:
            console.note(f"The way through {self.world.places[passed[0]].name} is closed to anyone going in, but you are already "
                         "here, and nothing stops you leaving.")
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
        if barrier:                                                             # (f541's review) haste spent on the walk to the barrier
            upto = self.barrier_minutes(roads.edges(self.world, route, walk), barrier)
            hasted, fatigue_factor = self.take_haste(upto)
            walk = max(1, round(walk * hasted / upto)) if hasted != upto else walk
        else:
            walk, fatigue_factor = self.take_haste(walk)
        fatigue_factor *= self.take_swift(walk)
        self.travel_fatigue(self.barrier_minutes(roads.edges(self.world, route, walk), barrier) if barrier else walk, fatigue_factor)
        self.leaving_stop(route, text)                      # (f427) the hazard ahead got past, and anyone in need walked past, seen
        self.end_conversation()
        self.last_spoken = None
        console.debug(f"walking {walk} minutes: {' -> '.join(route)}" + (f" (to the barrier on {barrier[1]})" if barrier else ""))
        self.run_journey(route, walk, text, events, barrier=barrier)

    def on_look(self, intent: ActionIntent, text: str) -> None:
        from engine import matters
        if intent.seek and matters.try_find(self, text):          # (f317) looking for something, where a matter's find path points
            return
        self._looking = True                                                     # (f380) a look sees the whole room, an arrival or not
        room = (" The player has rented a small room upstairs here; if their words take them to it, describe the "
                "room - simple, private, theirs for the night. " if self.has_room() else "")
        self.narrate(
            room + "The player looks closely, focusing on what their words ask about. Answer that directly first, from what "
            "can actually be seen: if they ask about the people, describe their peoples, looks and manner. Mention only "
            "the people relevant to what they are looking at.", text)
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
                self.refuse(court.absent_line(self, resident))                  # (f320) behind a door that has not opened to them
            elif resident.away_until > self.minutes:
                self.refuse(f"{resident.label(self.acting)} has stepped away. Give it a little while.")
            else:
                self.refuse(f"{resident.label(self.acting)} isn't here at this hour.")
            return
        if not npc and self.store.npc_exists(target_id):
            away = self.store.load_npc(target_id)
            from engine import mapview
            same_town = (away.location in self.world.places and away.location != self.player.location
                         and mapview.top_of(self.world, away.location) == mapview.top_of(self.world, self.player.location)
                         and not self.world.places[away.location].danger and away.away_until <= self.minutes)
            if not same_town:
                console.note(f"{away.label(self.acting)} isn't here. You last saw them at {self.where_name(away.location)}.")
                return
            self.travel_route(away.location, text)                 # (f342) someone of this town: walk to where they work
            if self.halted:
                return
            npc = next((n for n in self.present if n.id == target_id), None)
            if not npc:
                self.refuse(f"{away.label(self.acting)} is not about at this hour.")
                return
        if not npc and not self.present:
            self.narrate("The player says or thinks this aloud, but no one is here to answer. Reflect the silence "
                         "of the place back at them.", text)
            return
        if not npc:
            here = ", ".join(n.label(self.acting) for n in self.present)
            self.ask_back("talk_whom", text, f"said to no one in particular; here: {here}")          # (f321) the world asks who they mean
            self.halted = True
            return
        if not self.partner or self.partner.id != npc.id:
            self.end_conversation()
            self.partner = npc
            self.stance = voice_rules.roll_stance(npc, self.minutes, streams.keyed("stance", npc.id, f"{npc.id}:{self.minutes}"),
                                                  who=self.acting)        # (f347) how they are for this conversation; (f486) its own die
            if self.stance:
                console.debug(f"{npc.name} is, this talk: {self.stance}")
        self.last_spoken = npc.id
        self.player.mentor["last_voice"] = False
        promote(npc, self.store, self.world, self.catalog)

        speech = intent.speech or text
        label_before = npc.label(self.acting)
        first_time = not regard.of(npc, self.acting).met         # (f480) the first meeting is this character's
        if not self.convo:                                       # (f481) a new conversation: a request left without a yes in the last is let go
            from engine import obligations
            asked = obligations.current(self.store, "request", npc.id, self.acting)
            if asked is not None and asked.since < self.minutes:       # (the owner, 2026-11-03) a situation's request as any other:
                obligations.close(self.store, asked, "released", "no_answer", self.minutes, npc=npc)   # and not asked again (ask)
                if (asked.data.get("terms") or {}).get("part"):
                    from engine import situation_parts
                    situation_parts.decline(self.store, asked.data["terms"]["part"], self.acting)
        from engine import recognition
        back = "" if first_time or self.convo else recognition.line(npc, self.minutes, self.acting)       # (f382) they know the player again
        self._back = npc.id if back else None
        if first_time:                                       # (f480) seeded from this character's standing: their name, their deeds
            rep = self.player.reputation.get(pulse.town_of(self.world, npc.location), 0)
            regard.step(npc, self.acting, round(rep * pulse.P["reputation"]["trust_per_point"]) + self.first_meeting_trust(npc)
                        + self.heat_trust() + self.standing_trust(npc), cause="first meeting", minute=self.minutes)
        else:
            self.easy_company(npc)
        if first_time and self.has("oathbound") and set(self.world.roles[npc.role].knowledge_groups) & {"guards", "temple"}:
            regard.step(npc, self.acting, round(self.has("oathbound")), cause="oathbound", minute=self.minutes)
        if first_time and self.has("trusted_face"):
            regard.step(npc, self.acting, round(self.has("trusted_face")), cause="trusted face", minute=self.minutes)
            console.debug(f"trusted face: {npc.name} starts at trust {regard.of(npc, self.acting).trust}")
        check_note = getattr(self, "pending_check", "")
        self.pending_check = ""
        pre = self.__dict__.pop("_handed_in", None)                           # (f485) handed in by the prepare, its own operation
        if pre is not None and pre[0] == npc.id:
            handed = pre[1]
        else:
            was, self.buffering = self.buffering, True                          # (f384) two jobs handed in are told in one passage
            handed = self.turn_in(npc.id) if self.player.quests else []         # (f378) finished work is handed in by speaking to who pays
            self.buffering = was
        if handed:
            check_note = (check_note + " [THE GAME HAS DECIDED: the stranger has handed in " + "; ".join(handed)
                          + ". It is done, recorded and paid; you may say so in your own way, without the figures.]").strip()
        from engine import matters, court, stakes
        matters.bind_for(self.store, self.world, npc)                    # (f317) a clue written for their role settles on them
        from engine import situation_parts
        situation_parts.ask(self, npc)                                   # (f545) what they need of their situation, asked of this character
        ctx = (self.npc_context(npc) + self.local_knowledge(npc) + matters.talk_lines(self, npc)
               + court.keeper_lines(self, npc, speech) + court.gated_lines(self, npc)    # (f320) the door, and what is behind it
               + stakes.talk_lines(self, npc))                                          # (f322) the job they put on the board
        note_due = self.note_due(npc)
        if note_due:
            old_note = regard.of(npc, self.acting).journal_note
            ctx = ctx + [("JOURNAL NOTE DUE: write journal_note now: one plain sentence, under 28 words, that the STRANGER writes in THEIR journal "
                          "about YOU: your role, where you are found, and what they have learned of you, with you in the third person by name "
                          '("Fenella Reeve, the guild clerk in Parth; fussy about her ledgers and anxious about mistakes"). Never your own '
                          'thought about the stranger, never in your voice, never "I" or "my".'      # (f486) the rule where it is used
                          + (f" The old note was: {old_note} - bring it up to date with what has happened since." if old_note else ""))]
        secret_lines, pending_secret = self.secret_lines(npc, speech)
        ctx = ([back] if back else []) + ctx + secret_lines
        if decided := ledger.decided():                                  # (f416) what the turn has settled so far: never answered against
            ctx = ctx + ["WHAT THE GAME HAS DECIDED THIS TURN (true; say nothing against it): " + " ".join(decided)]
        if npc.id in self.player.prisoners:
            self.player.prisoners[npc.id]["asked"] = self.player.prisoners[npc.id].get("asked", 0) + 1
        from engine import voices
        town = pulse.town_of(self.world, self.player.location)
        from engine import truth
        view = truth.scene_of(self).view(truth.viewer_for_npc(npc, self.world), "townsfolk").asking(speech)      # (f375) the streets when asked
        from engine import brief                                        # (f486) the town's list and the board in full only when the line is
        town_lines = view.lines("town")                                 # about them, or the role's work is them; the checks read the list always
        view.drop |= {f for f in ("town", "board") if not brief.asked(f, speech, npc.role)}
        console.debug(f"truth view for {npc.name}: " + ", ".join(f"{h.split(' (')[0].lower()} {len(l)}" for h, l in view.sections()))
        reply, revealed = converse(npc, self.store, self.world, self.catalog, self.convo,
                                   f"{speech} {check_note}".strip(), ctx, truth_text=view.text(), known=view.scene.known_words(),
                                   stance=getattr(self, "stance", ""), rng=streams.keyed("voice", npc.id, f"{npc.id}", len(self.convo)),   # (f486)
                                   worn=self.worn_words("speech"), pronoun=brief.pronoun(self, self.acting), given_also=town_lines,
                                   house=voices.house_phrases(self, town, npc.id),          # (f350) what everyone else here has been saying
                                   wares=self.wares_said(npc), who=self.acting)             # (f418) at the prices the game charges; (f480) to whom
        voices.heard(self, town, npc.id, reply.speech)
        from engine import presence                                            # (f485) what was said aloud reaches those standing by
        claimed = (getattr(reply, "learned_player_name", "") or "").strip()
        if claimed and claimed.lower() in speech.lower():
            presence.overheard_name(self, npc, self.acting, claimed)
        told = [f for f in (self.world.lore.get(r) for r in revealed if not str(r).startswith("clue:")) if f is not None]
        if told:
            presence.overheard_facts(self, npc, told)
        if reply.intent == "leave" and not has_parting(reply.speech):
            reply.intent = "small_talk"            # nobody walks off without a word: no goodbye or dismissal in the speech, no leaving
        self.convo += [("Stranger", speech), (npc.name, reply.speech)]
        if note_due and reply.journal_note.strip():
            seen = regard.own(npc, self.acting)
            seen.journal_note = " ".join(reply.journal_note.split())[:240]
            seen.note_trust, seen.note_mem = seen.trust, npc.memory_total + sum(1 for m in npc.memories if m.id is None)
        self.orenna_named(speech)
        self.hear_names(reply.speech)
        if reply.offers_work and reply.offers_work.task.strip():
            self.record_work_offer(reply.offers_work, npc)
        elif reply.offers_quest and reply.offers_quest.what.strip() and not self.request_of(npc):
            self.record_quest_offer(reply.offers_quest, npc)
        elif not offer_open(self.store, npc, self.acting) and not (reply.offers_quest and reply.offers_quest.what.strip()) and self.promises_pay(reply.speech):
            if (offer := self.inferred_offer(npc, reply.speech)) is not None:       # pay was promised in words: make it a real, payable offer
                self.record_work_offer(offer, npc)
        if reply.gives and reply.gives.name.strip() and reply.intent != "bargain" and self.story_object(reply.gives.name):
            self.receive_key_item(reply.gives, npc)
        elif reply.gives:
            console.debug(f"ignored gift '{reply.gives.name}' - not a story object, or offered for sale")
        speaker = npc.label(self.acting) if reply.told_own_name else label_before
        self.flush(text)
        if config.NARRATED_DIALOGUE:
            self.narrate_dialogue(npc, label_before, speaker, text, reply, first_time,
                                  reasons=self.frame_reasons(npc, reply, revealed, check_note))     # (f347) the engine decides if there is a frame
        else:
            self.show_speech(speaker, reply, npc)

        if reply.intent == "lie" and self.has("lie_sense") is not None:
            gift = next((i for i in self.player.character.equipment.values() if "lie_sense" in (i.trait or {}).get("world", {})), None)
            console.note(f"{gift.name if gift else 'Your relic'} turns cold against your skin. {npc.label(self.acting)} just lied to you.")
        known = self.player.character.knowledge
        for fact_id in revealed:
            if fact_id not in known and not fact_id.startswith("clue:"):
                known.append(fact_id)
                console.debug(f"player learned: {fact_id}")
        for clue in matters.mark_found(self, npc, revealed):              # (f317) a clue carried by their words is found: the matter is in the journal
            console.ledger(f"Noted: {clue}")
        matters.spoke(self, npc)
        from engine import situation_parts
        situation_parts.heard(self, npc, speech)                         # (f545) a clue told them, or their trust earned, may meet their terms
        self.secret_after(npc, pending_secret)
        if reply.intent == "leave" and reply.speech.rstrip().rstrip('"\'').endswith("?"):
            reply.intent = "small_talk"            # someone who has just asked a question has not walked away
        if reply.intent == "leave" and npc.role in ("guild_clerk",):
            reply.intent = "small_talk"            # the clerk stays at the desk: the guild must stay reachable
        if reply.intent == "leave" and npc.id not in self.player.prisoners:
            console.narrate(f"{cap_first(npc.label(self.acting))} lets the talk end there and steps away.")        # (f325) fiction, not a system note
            npc.away_until = self.minutes + 30
            self.store.save_npc(npc)
            self.end_conversation()
            self.refresh_present()

    def unnamed(self, text: str, *extra) -> str:
        """The text with the real name of anyone the player has not been told hidden behind how the player knows them."""
        people = list(self.present) + ([self.partner] if getattr(self, "partner", None) else []) + [x for x in extra if x]
        return markup.hide_names(text, people, self.acting)

    def reach_of(self, npc) -> tuple[list[str], str]:
        """(f344) What this townsperson can lay hands on now, and how tense the moment is (engine/reach.py)."""
        from engine import law, reach
        role = self.world.roles.get(npc.role)
        wares = [w.name for w in self.wares_of(npc)] if role else []
        wares += [i.name for n, i, _ in self.stock_here() if n.id == npc.id]
        try:
            ground = [inv.label(i) for i in self.ground_here()]
        except Exception:
            ground = []
        try:
            heat = law.tier(self.heat_here())
        except Exception:
            heat = ""
        return (reach.within(npc.role, self.place.type, wares=wares, ground=ground),
                reach.moment(npc.role, regard.of(npc, self.acting).trust, heat, fight=bool(self.combat)))    # (f480)

    def frame_reasons(self, npc, reply, revealed=(), note: str = "") -> list[str]:
        """(f347) Why this line of speech earns the narrator's frame, as the engine sees it: the first words between them this visit, trust
        that moved by two or more, a clue given, a refusal or threat, a gift, a leaving, an attempt the game has judged. Empty for an
        ordinary line (most of them), which is then printed as the words alone. data/rules/voice.yaml frame_when holds the wording the
        frame is given."""
        W = voice_rules.V["frame_when"]
        out = []
        if npc.id not in self.__dict__.setdefault("_framed_here", set()):
            out.append(W["first"])
        if abs(getattr(reply, "trust_change", 0) or 0) >= 2:                  # a nudge of one is the model being polite, not a moment
            out.append(W["trust"])
        if any(str(r).startswith("clue:") for r in revealed):                   # a clue to a matter; an ordinary fact of the town is not a moment
            out.append(W["reveal"])
        intent = getattr(reply, "intent", "")
        if intent == "threaten" or (intent == "refuse" and voice_rules.refuses(getattr(reply, "speech", ""))):
            out.append(W["refuse"])                                              # the model marks 'refuse' on most answers; the words decide
        gift = getattr(reply, "gives", None)
        if gift is not None and getattr(gift, "name", "").strip():
            out.append(W["gift"])
        if intent == "leave":
            out.append(W["leave"])
        if note:
            out.append(W["decided"])
        if self.__dict__.pop("_back", None) == npc.id:                          # (f382) someone who knows them, after a while
            out.append(W["back"])
        return out

    def other_names(self, who=None) -> list[str]:
        """(f347) Everyone present but `who` (an NPC record or a hire's name), by name and as the player knows them: a frame must not open
        on one of them."""
        skip = {getattr(who, "id", None), who if isinstance(who, str) else None}
        out = [x for n in self.present if n.id not in skip for x in (n.name, n.label(self.acting))]
        out += [m["name"] for m in self.player.party if m.get("name") and m["name"] not in skip]
        if getattr(self, "partner", None) and self.partner.id not in skip:
            out += [self.partner.name, self.partner.label(self.acting)]
        from engine import mentor
        if self.mentor_with_you() and who is not mentor.NAME:
            out.append(mentor.NAME)
        return out

    def show_speech(self, speaker: str, reply, npc, stood_in: bool = False) -> None:
        """(f347) The words alone, with the person's own gesture when it is short enough to read as one (voice_rules.short_gesture).
        (f485) `stood_in`: the narrator's frame was dropped or failed: with no gesture of their own, one from data (voice.yaml
        frame_stand_in), drawn for this speaker; never the same machinery line twice running."""
        from engine import quirks
        gesture = voice_rules.short_gesture(quirks.bare_gesture(self.unnamed(getattr(reply, "gesture", "") or "", npc), npc.name))   # no 'Rossy gives...': the label is printed
        if stood_in and not gesture:
            gesture = streams.keyed("frame_stand_in", npc.id, "", self.store.meta.steps).choice(voice_rules.V["frame_stand_in"])
        from llm.contracts import NO_WORDS
        if NO_WORDS.fullmatch(reply.speech or ""):                     # (f422) no words: what they do, and no name over an empty line
            done = self.unnamed(getattr(reply, "gesture", "") or "", npc).strip()
            silent = streams.keyed("no_words", npc.id, "", self.store.meta.steps).choice(voice_rules.V["no_words"]).format(speaker=speaker)
            line = f"{speaker} {done}" if done and not done.lower().startswith(speaker.lower()) else (done or silent)
            console.narrate(cap_first(line.rstrip(".") + "."))
            self.remember_narration(line)
            return
        console.npc_says(speaker, reply.speech, gesture)
        self.remember_narration(f'{speaker}: "{reply.speech}"', {"type": "says", "speaker": speaker, "speech": reply.speech, "gesture": gesture})

    def narrate_dialogue(self, npc, known_as: str, speaker: str, player_did: str, reply, first: bool, reasons: list[str] | None = None) -> None:
        """(f347) The words on the page. The narrator frames them only when the engine has a reason to (frame_reasons); every other line
        is the words alone with the person's own short gesture. A frame is told why it is there and what the player has already read here,
        so it writes to the moment rather than re-placing the whetstone."""
        if reasons is None:
            reasons = self.frame_reasons(npc, reply)
        self.__dict__.setdefault("_framed_here", set()).add(npc.id)
        if not reasons:
            self.show_speech(speaker, reply, npc)
            return
        others = [self.unnamed(f"{self.seen_as(n)}: {n.activity}", npc) for n in self.present if n.id != npc.id][:5]
        manner = self.unnamed(f"{npc.personality} {npc.voice}".strip(), npc) or "unknown yet"
        within, moment = self.reach_of(npc)
        try:
            frame = fresh(
                "dialogue_frame", wp.DIALOGUE_SYSTEM,
                wp.dialogue_request(self.time_label(), self.place, others, known_as, self.unnamed(npc.description, npc), self.unnamed(npc.activity, npc),
                                    manner, first, player_did, reply.speech, self.unnamed(reply.gesture, npc),
                                    getattr(reply, "intent", "") == "leave", self.recent_narration,
                                    reach=within, moment=moment,
                                    why=reasons, already=self.shown_lines(), worn=self.worn_words("prose"),
                                    who_is=entities.who_is_who(self, also=[npc.id])),                 # (f392)
                DialogueFrame, self.recent_narration, fields=("before", "after"), max_tokens=config.PROSE_MAX_TOKENS,
                context={"speaker": [npc.name, known_as, speaker], "others": self.other_names(npc), "speech": reply.speech}, worn=self.worn_words("prose"),
            )
        except LLMError:
            self.show_speech(speaker, reply, npc, stood_in=True)     # (f485) dropped or failed: the words, with a gesture from data if none
            return
        before, after = self.unnamed(frame.before, npc), self.unnamed(frame.after, npc)
        console.dialogue(before, speaker, reply.speech, after)
        self.note_shown(f"{before} {after}")
        self.remember_narration(" ".join(t for t in (before, after) if t.strip()),
                                {"type": "dialogue", "before": before, "speaker": speaker, "speech": reply.speech, "after": after})

    from scenes.intercepts import Intercept as _I
    INTERCEPTS = (_I("farewell", 85, "farewell_intercept", "a plain goodbye to the person they are talking with: one short parting line, no frame"),)

    def farewell_intercept(self, text: str) -> bool:
        """(f347) A line that is nothing but a goodbye to the person they are talking with is answered with one short parting line through a
        small call (engine/partings.py), with no frame, and the talk ends; the interpreter never sees it."""
        from engine import partings
        npc = self.partner
        if not npc or not partings.is_goodbye(text, (npc.name, npc.label(self.acting))):
            return False
        self.part_from(npc, text)
        return True

    def part_from(self, npc, text: str) -> None:
        """(f347) The player's goodbye: a word's worth of time passes, the person answers with one short parting line (a written one if
        the model fails), the words are printed alone, and the talk ends."""
        from engine import partings
        self.advance(clock.TALK_MINUTES)
        self.last_spoken = npc.id
        speech, gesture = partings.line(self, npc, text)
        self.convo += [("Stranger", text), (npc.name, speech)]
        partings.remember(npc, text, speech)
        self.store.save_npc(npc)
        self.hear_names(speech)
        speaker = npc.label(self.acting)
        import types
        self.show_speech(speaker, types.SimpleNamespace(speech=speech, gesture=gesture), npc)
        console.narrate(f"You step away from {speaker}.")
        self.end_conversation()

    def on_leave_conversation(self, intent: ActionIntent, text: str) -> None:
        from engine import partings
        if self.partner and intent.speech.strip() and partings.is_goodbye(intent.speech, (self.partner.name, self.partner.label(self.acting))):
            self.part_from(self.partner, intent.speech.strip())            # (f347) a goodbye read by the interpreter is still a goodbye: two words back
            return
        if self.partner and intent.speech.strip():
            partner = self.partner
            intent.target = partner.id
            intent.speech = f"{intent.speech.strip()} (said in parting - they are about to leave)"
            self.on_talk(intent, text)
            if self.partner:
                console.narrate(f"You step away from {partner.label(self.acting)}.")
            self.end_conversation()
            return
        if self.partner:
            console.note(f"You step away from {self.partner.label(self.acting)}.")
        self.end_conversation()

    def has_room(self) -> bool:
        return (self.player.room == self.player.location and self.player.room_until > self.minutes) or \
            (self.place.type == "home" and not self.home_ruined())

    def on_buy(self, intent: ActionIntent, text: str) -> None:
        if self.mount_buy(intent, text):
            return
        if self.property_buy(intent, text):
            return
        sellers = [n for n in self.present if self.wares_of(n)]
        listed = any(w.id == intent.ware.lower().strip() or (intent.ware and intent.ware.lower() in w.name.lower())
                     for n in sellers for w in self.wares_of(n))
        if not listed and self.buy_from_stock(intent, text):
            return
        wanted = intent.ware.lower().strip()
        seller = next((n for n in sellers if n.id == intent.target), None) or \
            next((n for n in sellers if self.ware_asked(self.wares_of(n), wanted)), None) or (sellers[0] if sellers else None)   # (f545's review)
        if not seller:
            self.refuse("No one here is selling anything.")
            return
        wares = self.wares_of(seller)
        ware = self.ware_asked(wares, wanted)
        if not ware:
            self.refuse(f"{seller.label(self.acting)} sells: " + ", ".join(f"{w.name} ({money.words(self.quote_ware(seller, w).price)})" for w in wares))
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
            self.refuse(f"{left.name} is in your book, but you did not bring it. (#book to see what you bring; #prepare to change it, out of a fight, once a day.)")
            return
        if not ability:
            named = (intent.ability or "").strip()
            if named and not any(named.lower() in (a.name.lower(), a.id.lower()) for a in c.actives):
                self.refuse(f"You don't have an ability called '{named}'.")
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
            self.refuse(f"{ability.name} is a fighting technique - save it for a fight"
                         + (" (name it as you start one, or set it with #prebuff)." if ability.effect.value == "buff" else "."))
            return
        self.ensure_field_uses()
        if ability.field_use:
            refusal = self.field_precheck(ability, intent, text)
            if refusal:
                self.refuse(refusal)
                return
        pool = ability.resource.value
        table = "ability_cost_percent" if pool == "mana" else "stamina_cost_percent"
        cost = pools.reference_pool(pool, c.level) * COMBAT_RULES[table][ability.tier.value] / 100
        if getattr(ability, "rank", 0):
            from engine import spells
            cost = spells.mana(ability)                 # (f397) a ranked spell's flat cost
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
            gain = top * _heal.pct_of(ability, outside=True) / 100        # (f399) a ranked heal's share by rank
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
            letter = getattr(npc, "rank", "") or "FFFEED"[zlib.crc32(npc.id.encode()) % 6]        # (f374) Maren is A rank, not a drawn F
            lines.append(f"You are a rank-{letter} member of the adventurers' guild, between contracts. You know the "
                         "Greywood and its dangers from your own jobs, and you size up newcomers.")
        if (asked := self.request_of(npc)):                                     # (f481) from the registry
            lines.append(f"You have asked them to: {asked['title']}, and are waiting for their answer.")
        if npc.mood and (npc.mood_until <= 0 or npc.mood_until > self.minutes):     # (f486) a mood past its time is no longer theirs
            lines.append(f"How you've been lately: {npc.mood}")
        if npc.motive:
            lines.append(f"What you're working toward (private - share it only if it comes up naturally): {npc.motive}")
        feelings = pulse.relations_text(self.store, npc)
        if feelings:
            lines.append(f"How you feel about people you know: {feelings}")
        if self.owns("gossips_ear"):                        # (f313) the news itself is in the truth view (NEWS THAT HAS REACHED HERE)
            lines.append("You like passing on news to the stranger - tell them what you've heard without being asked.")
        own = [m.text for m in npc.memories if m.kind == "own_life"][-2:]          # (f478) their own life, by kind
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
        if "orenna_name" in self.player.character.knowledge and "orenna" in (self.last_text or "").lower():   # (f486) only when it is said
            lines.append("No one living has ever heard the name Orenna. If the stranger says it, it means nothing to you; you do not "
                         "recognise it, and you do not pretend to.")
        lines += self.guild_knowledge(npc)
        lines.append(f"The season is {clock.season(self.minutes)}.")
        return lines

    def seek_person(self, seek: str, text: str) -> bool:
        """(f404) 'I look for Brokur Durdal': someone the player names is found, or said to be elsewhere. A night's play had the player
        look for the smith they had been told of, standing ten paces off as 'the soot-stained smith', and get a search for wild game
        instead: the narrator, told there was none, described a woman scraping mud from a boot, and the player went to ask her."""
        from engine import retrieval
        rows = retrieval.named_in(self.store, seek)
        if len(rows) != 1:
            return False
        here = next((n for n in self.present if n.id == rows[0].id), None)
        if here is not None:
            look = here.label(self.acting)
            if not regard.of(here, self.acting).name_known:
                regard.own(here, self.acting).name_known = True   # asked after by name and pointed out: they are known by it now
                self.store.save_npc(here)
            self.advance(2)
            self.narrate(f"The player looks for {here.name} and finds them here: {look}"
                         + (f", {here.activity}" if here.activity else "") + f". That is {here.name}. Show the player picking "
                         f"{here.name} out (someone points, or a name called and answered); add no one else.", text)
            return True
        o = self.store.load_npc(rows[0].id)
        seen = regard.of(o, self.acting)
        if not (seen.met or seen.heard_of or seen.name_known):
            return False                                          # a name the player has no way to know: an ordinary search
        if o.location == self.player.location:
            console.note(f"{o.name} isn't about just now. Try again later in the day.")
        else:
            console.note(f"{o.name} isn't here. " + (f"You can find {o.name.split()[0]} at {self.where_name(o.location)}." if o.location
                                                      else "Nobody here knows where to find them."))
        self.halted = True
        return True

    def on_search(self, intent: ActionIntent, text: str) -> None:
        if self.mentor_search():
            return
        if self.place.type == "dungeon" and self.player.delve:
            self.dungeon_search(text)
            return
        if self.search_part(intent, text):                       # (f394) what the part the player stands at holds
            return
        from engine import matters
        if matters.try_find(self, text):                          # (f317) a matter's find path points here
            return
        if self.plant_sought(intent.seek):                        # (f381) looking for silverleaf is foraging, not hunting
            self.on_forage(intent, text)
            return
        if intent.seek and self.seek_person(intent.seek, text):  # (f404) looking for someone by name
            return
        if not self.place.danger:
            self.narrate("The player searches the area. There is no wild game or danger here. Describe the search "
                         "and what ordinary things they notice instead.", text)
            return
        if self.wildlife:
            seen = self.wildlife[0]
            if intent.seek and encounters.matching(self.world, [seen.id], intent.seek):
                self.narrate(f"The {seen.name.lower()} they are looking for is right here, keeping its distance. "
                             "Remind them.", text)
                return
            self.wildlife = None
            console.debug(f"moving on from the {seen.name.lower()} in view")
        self.advance(SEARCH["search_minutes"])
        if self.bounty_encounter():
            return
        chance = SEARCH["chance_on_search"] + (SEARCH["tracker_bonus"] if self.has("tracker") is not None else 0)
        chance += (self.mech("patient_watch") + (self.mech("sniffer") if self.companion_here() else 0)) / 100
        trail = self.fresh_trail()
        following = self.__dict__.pop("_following", False)
        if trail and (following or not intent.seek or self.TRAIL_WORDS.search(intent.seek)
                      or encounters.matching(self.world, [trail["creature"]], intent.seek)):           # (f381) on the trail just found
            intent.seek = self.world.bestiary[trail["creature"]].name
            chance += SEARCH.get("trail", {}).get("bonus", 0)
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
        if self.maybe_encounter(min(0.95, chance), "You follow the signs:" if trail and intent.seek else "Your search pays off:",
                                intent.seek or text):
            self._trail = None
            return
        if self.wildlife:
            return
        roster = encounters.ensure_roster(self.store, self.world, self.player.location)
        wanted = encounters.matching(self.world, roster, intent.seek) if intent.seek else []
        pick = self.rng.choice(wanted or roster) if roster else ""
        clue = self.world.bestiary[pick].name.lower() if pick else ""
        if pick:
            self._trail = {"place": self.player.location, "creature": pick, "minutes": self.minutes}     # (f381) signs to follow
        self.narrate(f"The player spends {clue and 'a while '}searching but finds no creature this time. They do find "
                     f"fresh signs of {clue or 'nothing'}: tracks, droppings, or marks. Describe the search and the sign."
                     f"{' The creature they were looking for is not known to live here.' if intent.seek and not wanted else ''}",
                     text)

    TRAIL_WORDS = re.compile(r"\b(tracks?|trail|signs?|prints?|spoor|droppings|marks|it|them|the beast|the creature)\b", re.I)

    def fresh_trail(self) -> dict | None:
        """(f381) The signs the last search here turned up, while they are fresh: {place, creature, minutes} or None."""
        t = self.__dict__.get("_trail")
        if t and t["place"] == self.player.location and self.minutes - t["minutes"] <= SEARCH.get("trail", {}).get("fresh_minutes", 120):
            return t
        return None

    def toward_trail(self, dest: str, text: str) -> bool:
        """(f381) Going where the signs lead: the place named is in the passage that told of them, or the line says to follow them."""
        last = (self.recent_narration[-1] if self.recent_narration else "").lower()
        words = [w for w in re.findall(r"[a-z]+", dest.lower()) if len(w) >= 4]
        return any(re.search(rf"\b{re.escape(w)}", last) for w in words) or bool(re.search(r"\bfollow", text.lower())
                                                                                   and self.TRAIL_WORDS.search(f"{dest} {text}"))

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
        if self.hunt_named(intent, text):                         # (f449) a creature of this place, named but not in view: go looking for it
            return
        if self.present:
            console.note("Attacking people isn't supported yet.")
        else:
            console.note("There's nothing here to fight.")

    def hunt_named(self, intent: ActionIntent, text: str) -> bool:
        """(f449) "attack swarm of ravens" with none in view, where ravens live: the owner's log read "There's nothing here to fight" a turn
        after Beast-Breaker's Eye had listed them among the things that live here (pillar 1: what is shown can be acted on). A creature of
        this place's roster that the player names is sought the way a search seeks it, the same roll and the same minutes, and the fight
        begins if it is found; the player is told first that none is at hand. Nothing named, or a place with nothing dangerous: False."""
        words = (intent.target or intent.seek or "").strip() or text
        if not words or not self.place.danger:
            return False
        roster = encounters.ensure_roster(self.store, self.world, self.player.location)
        found = encounters.matching(self.world, roster, words) if roster else []
        if not found:
            return False
        name = self.world.bestiary[found[0]].name
        console.note(f"No {name.lower()} is within reach just now, though they are about these parts. You go looking.")
        self.on_search(ActionIntent(kind="search", seek=name, summary=f"hunting {name}"), text)
        return True

    def on_wait(self, intent: ActionIntent, text: str) -> None:
        barrow = (self.dungeon_here() or {}).get("theme") == "barrow"
        camped = self.camp_active()
        if self.place.type == "dungeon" and self.player.delve and not self.player.delve.get("rest") and not camped \
                and self.has("safe_camp") is None and not (barrow and self.owns("tomb_sleeper")):
            self.refuse("It's too dangerous to rest here. Find a quiet chamber, or climb back out.")
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
        arrived = [n.label(self.acting) for n in self.present if n.id not in before]
        left = [n.label(self.acting) for n in self.residents if n.id in before and n not in self.present]
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
        if not hit:
            self.habits("rest")                                # (f412) told in the rest's passage, not after it
            self.mentor_rest_habit()                           # (f413) and Maren's with them
        self.narrate(f"The player {how} at {self.place.name} for {clock.describe_duration(minutes)}. It is now {clock.period(self.minutes)}."
                     f"{changes}{interrupted}{feel} Describe the player resting and the passing of time, then the scene now, "
                     "mentioning at most two of the people present.", text)
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
        if world_improv.is_rest(text) and len(re.findall(r"[a-z']+", text.lower())) <= 12:
            late = clock.period(self.minutes) in ("evening", "night", "deep night")
            self.on_wait(ActionIntent(kind="wait", wait_until="morning" if late else "", wait_minutes=0 if late else 60), text)
            return                                          # (f386) a line that only goes to sleep is a rest, not a gamble rolled as hiding
        spot = features.spot_of(self)
        if spot is not None and spot.data.get("clue") and not spot.data.get("read") and \
                any(w in f"{intent.summary} {text}".lower().split() for w in self.CLUE_WORDS) and self.search_part(intent, text):
            return                                          # (f395) reading the marks where the player stands: what the part holds
        from engine import act, ruling
        if act.on():                                        # (f595) the one ruling outside combat, behind its switch
            act.act(self, self.acting, intent.summary or text, text)
            return
        ruling.run(self, intent.summary or text, text)      # (f395) the dungeon master's ruling: make room, set the stakes, or say no


from scenes import intercepts as _intercepts                                     # noqa: E402
WorldScene.INTERCEPT_TABLE = _intercepts.gather(WorldScene)                     # declared by the mixins, run in order by handle()
WorldScene.REPAIR_TABLE = plan_repairs.gather(WorldScene)                        # the plan repairs, declared the same way, run in order by repair()
