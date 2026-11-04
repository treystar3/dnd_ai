"""(f503) The fight's mechanics in one place: who takes the field, the serial, the opening blows and the odds; a round (the player's
action and everyone else's, hires going down through the party service); orders, a draught drunk, the one Character -> Fighter path
(refresh) and the one Fighter -> Character path (sync); the end (the row dropped, the minutes passed, who fell, the companions, the
survivor who yields, the rewards under the engine's own names, the captives chosen, a death, a Phoenix). Every method returns facts;
the service writes nothing to the console, asks the model nothing and imports none of scenes, ui, llm.gateway or llm.embed (the
fence: tools/purity.py check_fight). The scene (scenes/combat_scene.py, the name CombatScene kept) reads the player's words and the
model's proposals, calls these steps in the order the page needs them, and tells the story of what came back: its lines fall between
the steps where they fell before, so a recorded session replays exactly (Bundle E decision 10: no number moves).

What it may change: the fight row (store.save_combat), the player's record (pools, coins, xp, spell_days, orenna_breath, party dicts,
companions, the bound summon, the field cooldowns), the place's bodies and carcasses (store.save_place), the taken legendary names;
entities through the party service. Its dice: the stream it is handed (the scene's streams.get("combat")), streams.keyed for the dice
that must hold across inputs (f501). `player` and `world` are the records and data it is handed, not dependencies it reaches for.

The precedent is services/party.py: the service holds no state of its own beyond the fight it is handed; what joining or dying means
is decided in one place, and whoever needs to know (the journal, the tests, later the director) subscribes to the typed events it
publishes (FightBegun, RoundFought, FightEnded, PlayerFell)."""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from typing import Callable

from core.models import Item
from engine import accessories, bosses, clock, combat, death, entities, inventory, items, leveling, loot, needs, pools, spells, streams, summons, taming
from engine import asked, battlefield, combat_improv, combat_perks, parley
from engine import effects
from engine import field as field_rules
from engine import mentor as mentor_rules
from engine import party as party_rules
from engine.domain_events import FightBegun, FightEnded, PlayerFell, RoundFought, current

DEPENDS = ("store", "bus", "party", "streams")


def whose_blow(by: str) -> str:
    """(f412) 'the third pirate's blow', 'your blow': the blow that put someone down, from who struck it."""
    return "your blow" if by == "you" else f"{by}'s blow"


ROLE_PROFILES = {
    "striker": {"strength": 14, "dexterity": 15, "constitution": 11, "intelligence": 6, "wisdom": 10, "charisma": 6},
    "guardian": {"strength": 15, "dexterity": 9, "constitution": 16, "intelligence": 6, "wisdom": 10, "charisma": 6},
    "rogue": {"strength": 10, "dexterity": 16, "constitution": 10, "intelligence": 8, "wisdom": 12, "charisma": 6},
    "healer": {"strength": 8, "dexterity": 11, "constitution": 12, "intelligence": 10, "wisdom": 16, "charisma": 10},
    "support": {"strength": 8, "dexterity": 12, "constitution": 11, "intelligence": 12, "wisdom": 14, "charisma": 12},
}


class _Shape:
    """A minimal creature-like stand-in for a companion whose kind is missing from the bestiary."""
    def __init__(self, comp):
        sizes = combat.RULES["creatures"].get("spirit", {}).get("size", {})
        self.id, self.name, self.size, self.category = comp.id, comp.name, sizes.get(getattr(comp, "tier", "light"), "Medium"), comp.kind or "spirit"
        self.profile = ROLE_PROFILES.get(comp.role, ROLE_PROFILES["striker"])
        self.attacks, self.temperament, self.group = ["strike"], "aggressive", (1, 1)


# ---------- the facts the methods take and return

@dataclass
class FightSpec:
    """A fight starting now, as the scene resolved it: the foes, the allies it mustered (allies()), the ground it built, the buffs the
    player readied and the stealth degree it rolled (an initiated fight), the camp's reserves and waves, a scripted setup."""
    creature: object
    enemies: list
    allies: list = field(default_factory=list)       # who starts beside the player
    later: list = field(default_factory=list)        # a party told to hold: it arrives on hold_arrival_round
    battlefield: object = None
    place: str = ""
    conditions: list = field(default_factory=list)
    reserves: list = field(default_factory=list)
    wave: tuple = (2, 2, 1)
    duel: bool = False
    prebuffs: list = field(default_factory=list)     # the combat buffs cast before the first blow (the player picked the moment)
    stealth: str = ""                                # the degree of the stealth check, when the player crept up; "" when they did not
    initiated: bool = False
    prepare: Callable | None = None                  # a scripted fight sets itself up after the estimate


@dataclass
class Opening:
    """What the telling of a fight's start may tell: the odds (label and the rate behind it), the opening events (the story lines, their
    blow tags on), and the notes for the player (the buffs cast before the first blow)."""
    label: str
    rate: float
    events: list
    notes: list


@dataclass
class RoundIntent:
    """The validated form of the model's CombatIntent proposal (llm/contracts.py): the kind, a target id looked up in the fight (the
    closest foe when it names none that stands), an ability id looked up in the kit, the line's words, and an improvisation's effect as
    the scene read it. The actor is a fighter id; the player fighter when empty."""
    kind: str
    target: str = ""
    ability: str = ""
    move: str = ""
    step: str = ""
    movement: str = ""
    buff_for: str = ""
    summary: str = ""
    approach: str = ""
    words: str = ""
    effect: str = ""
    actor: str = ""

    @classmethod
    def of(cls, intent, words: str, effect: str = "") -> "RoundIntent":
        """From the model's proposal and the line it answered."""
        return cls(kind=intent.kind, target=intent.target or "", ability=intent.ability or "", move=intent.move or "",
                   step=intent.step or "", movement=intent.movement or "", buff_for=intent.buff_for or "",
                   summary=intent.summary or "", approach=intent.approach or "", words=words, effect=effect)


@dataclass
class RoundOutcome:
    """kind: 'round' (a round fought to its end), 'free' (a movement used on its own: the action is still the player's to take, no round
    passed), 'talk' (words, a free action; `problem` says why they could not be tried). `notes` are the lines for the player, in order;
    `killed` the hires who died this round, (member, by whose blow), their deaths decided and published already."""
    kind: str
    notes: list
    killed: list
    problem: str = ""
    over: str = ""


@dataclass
class Told:
    told: list
    problems: list
    stopped: bool = False           # an order already given this turn: nothing more is done with the line


@dataclass
class Ending:
    outcome: str
    minutes: int
    dead: list
    fallen: list                    # the allies down at the end (fighters)
    fallen_ids: list
    duel: bool = False
    notes: list = field(default_factory=list)


@dataclass
class Rewards:
    """A win's take, committed under the engine's own names (the naming operation after the win gives the model's, f502):
    to_name is (item, source, kind, boss) with kind '' | 'codex' | 'relic'."""
    xp: int
    coins: int
    found: list
    to_name: list
    skinnable: int


@dataclass
class Captive:
    """A foe who yielded and is taken: the record make_prisoner takes (scenes/arc_actions.py), not the Fighter."""
    name: str
    kind: str
    level: int
    creature: str
    id: str
    tip: bool


class FightService:
    def __init__(self, store, bus, party, dice, player, world, now: Callable[[], int]):
        self.store = store
        self._bus = bus                      # the session's bus; the current one when none is given
        self.party = party                   # PartyService: a hire going down is its decision (decide_down)
        self.dice = dice                     # the fight's stream (streams.get("combat")), reseeded at every input
        self.player = player
        self.world = world                   # read for the bestiary
        self.now = now                       # the game's minute

    def _publish(self, event):
        return (self._bus or current()).publish(event)

    # ---------- taking the field

    def allies(self, hold: bool = False) -> tuple[list, list, list, bool]:
        """(allies who start in the fight, allies who arrive later, the notes for the player, whether the party formed up). Companions
        always start; a party told to hold arrives late."""
        c = self.player.character
        near, notes = [], []
        now = self.now()
        for comp in c.companions:
            if comp.fallen and not comp.dead and now >= comp.recover_at:
                comp.fallen = False
                notes.append(f"{comp.name} is back on its feet.")
            if not comp.active:
                continue
            shape = self.world.bestiary.get(comp.creature) or _Shape(comp)
            ally = combat.companion_fighter(shape, c.level, f"ally_{comp.id}", comp.name, gift=comp.source == "gift")
            near.append(ally)
        near = taming.strongest(near, c.level)
        notes += party_rules.sync_levels(self.player.party, c.level)
        members = [party_rules.fighter(m, minutes=now) for m in self.player.party if not m.get("tutorial")]
        formed = bool(members) and not (hold and self.player.party_mode == "hold")
        if hold and self.player.party_mode == "hold":
            return near, members, notes, formed
        return near + members, [], notes, formed

    def begin(self, spec: FightSpec) -> tuple[combat.Combat, Opening]:
        """The fight built: the player's fighter from the character (a named spell cast within its days not ready), the allies and the
        foes, the serial drawn once (f500), the ground, the bound summon, everyone placed; the buffs readied before the first blow and
        the surprise a stealthy approach earns; the opening events; the odds (combat.danger, kept across a restart by asked.compute);
        a script's setup; the row saved. Returns the fight and the Opening the telling may tell."""
        c = self.player.character
        me = combat.fighter_from_character(c)
        now = self.now()
        for m in me.moves:                                # (f397) a named spell cast within its days is not ready this fight
            a = next((x for x in c.actives if x.id == m.id), None)
            if a is not None and spells.day_locked(c, a, now):
                me.cooldowns[m.id] = 10 ** 6
        fight = combat.Combat(fighters=[me] + list(spec.allies) + list(spec.enemies), place=spec.place, conditions=list(spec.conditions))
        fight.record = True                 # keep a breakdown of every blow for the window's combat log
        combat.fight_key(fight)             # (f500) the fight's serial, drawn once here from the ids stream: never by an estimate's copy, never
        #                                     by a mark read before the first blow, so the dice after it are the same whatever is estimated
        fight.battlefield = spec.battlefield
        if spec.duel:
            fight.duel, fight.no_rewards = True, True
        fight.ally_reserves = list(spec.later)
        fight.ally_arrive = party_rules.P["hold_arrival_round"]
        fight.gentle = pools.mechanic(c, "gentle_approach") is not None
        fight.reserves = list(spec.reserves or [])
        fight.reinforce_every, fight.reinforce_count, fight.reinforce_from = spec.wave
        if not spec.duel:
            summons.join_bound(fight, c)     # the Bound summon walks in with them, whole (unless it was unmade and not yet made again)
        battlefield.place_fighters(fight)
        notes = []
        if spec.initiated and not spec.duel:
            notes += combat.prebuff(fight, list(spec.prebuffs), self.dice)   # the player picked the moment: their buffs go up first (f247, f248)
            if spec.stealth:                 # they crept up on it: stealth decides surprise (a camp rolls its own)
                if spec.stealth in ("success", "strong success"):
                    caught = combat.surprise(fight)
                    if caught:
                        combat.tell(fight, ", ".join(combat.who(e) for e in caught) + (" never see" if len(caught) > 1 else " never sees")
                                    + " you coming - caught unaware")
                else:
                    combat.tell(fight, "they see you coming at the last moment - no surprise")
        combat.opening(fight, self.dice)
        events = list(fight.story)                        # the opening blows are logged, not narrated with figures
        fight.log, fight.story = [], []
        label, rate = asked.compute(f"danger:{fight.serial}", lambda: combat.danger(fight))   # (f500) eighty fights simulated once a line:
        if spec.prepare:                                                                       # an operation run again finds the estimate kept
            spec.prepare(fight)              # a scripted fight sets itself up after the estimate, so the estimate is of the fight as it looks
        self.save(fight, spec.creature.name)
        self._publish(FightBegun(minute=now, serial=fight.serial, place=self.player.location,
                                 foes=tuple(e.name for e in spec.enemies), count=len(spec.enemies)))
        return fight, Opening(label, rate, events, notes)

    @staticmethod
    def row(fight: combat.Combat, creature: str) -> str:
        return json.dumps({"creature": creature, "fight": fight.model_dump(mode="json")})     # (f497) by the fields' types:
        # a fighter's float left as the int it was given (bleed 0, armor 0) is written 0.0 live as it is resumed, so a round run again from
        # the resumed row saves the row its first attempt would have (the digests of a stood-down round and a straight one agree)

    def save(self, fight: combat.Combat, creature: str) -> None:
        self.store.save_combat(self.row(fight, creature))

    @staticmethod
    def resume(raw: str) -> tuple[combat.Combat | None, str, str]:
        """The fight from its saved row: (fight, the creature's name, ''), or (None, '', why) for a row that cannot be read, which the
        caller lets go of with its reason (the fight is lost, never the game)."""
        try:
            data = json.loads(raw)                         # (f499) what the fight remembers of itself (its marks, what was read, who was tamed) is in the row
            shape = data["fight"].get("version")
            if shape != combat.SHAPE:                      # (f507) an older or stranger shape is never read in part
                return None, "", f"a fight of another shape ({shape}; this game's is {combat.SHAPE})"
            return combat.Combat(**data["fight"]), data["creature"], ""
        except Exception as e:                             # a damaged row: a half-written save, a shape an older game wrote
            return None, "", f"{type(e).__name__}: {e}"

    # ---------- a round

    def orders(self, fight: combat.Combat, who: list, kind: str, target: str) -> Told:
        """An order to the party: one order a turn is one command, even to the whole party. Returns who was told and the problems, and
        whether the line stops there (an order already given this turn)."""
        told, problems = [], []
        for a in who:
            problem = combat.give_order(fight, a, kind, target, same_command=bool(told))
            if problem:
                problems.append(problem)
                if "already given" in problem:
                    return Told(told, problems, True)
                continue
            told.append(a)
        return Told(told, problems)

    def round(self, fight: combat.Combat, intent: RoundIntent) -> RoundOutcome:
        """One player turn, and everyone else's when it ends the round: the action the intent names (a step or a movement alongside it,
        an ability, a move, a defence, an interposing, a flight, a taming, an improvisation, a plain attack), the round finished, the
        hires who went down decided. Words are a free action (kind 'talk'); so is a movement used on its own (kind 'free')."""
        f = fight
        p = (f.get(intent.actor) if intent.actor else None) or f.player
        notes: list[str] = []
        f.log, f.story, f.hits = [], [], []
        target = f.get(intent.target) if intent.target else None
        if intent.kind != "interpose" and (not target or not target.alive or target.side != "enemy" or target.fled):
            target = battlefield.closest(f, p, f.enemies())
        if intent.kind == "talk":
            return self._talk(f, p, target, intent)

        again = p.counters.pop("acting_again", None)       # a movement used on its own: this is the same turn's action
        if not again and not combat.start_turn(p, f, self.dice):
            if not p.counters.pop("cast_turn", None):      # a charged spell going off (or breaking) is the whole turn
                f.log.append(f"{p.name} is unable to act")
                combat.tell(f, "you try to act, but your body will not answer")
        elif self.alongside(f, p, intent, target, notes):
            pass                                          # the movement was the whole of what they did: the action is still to come
        elif not p.counters.get("moved_now") and self.apply_step(f, p, intent, target):
            pass                                          # the step took the whole round (the movement law); the action waits
        elif intent.kind == "ability":
            move = next((m for m in p.moves if m.id == intent.ability), None)
            binder = self.binding_ability(move)
            problem = None
            if binder:
                self.try_bind(f, move, binder, target, notes)
            else:
                give = self.buff_recipients(f, move, intent.buff_for, notes) if move and move.effect != "mobility" else \
                    ([a for a in [self.movement_ally(f, intent)] if a] or None)
                problem = combat.act_ability(f, p, move, target, self.dice, give=give) if move else "You don't know that ability."
            if problem:
                notes.append(problem + " You attack instead.")
                combat.act_attack(f, p, target, self.dice)
        elif intent.kind == "move":
            combat.act_move(f, p, intent.move or "closer", target)
        elif intent.kind == "defend":
            combat.act_defend(f, p)
        elif intent.kind == "interpose":
            ward = next((a for a in f.allies() if a.id == intent.target), None) or \
                next((a for a in f.allies() if intent.target and intent.target.lower() in a.name.lower()), None) or \
                min(f.allies(), key=lambda a: a.hp / max(1, a.max_hp), default=None)
            combat.act_interpose(f, p, ward)
        elif intent.kind == "flee":
            if f.mentor_troll:                             # the scripted troll: the attempt is made, and it fails, in her words
                combat.act_flee_blocked(f, mentor_rules.line_from(self.player, mentor_rules.M["troll_combat"]["run_fail"]))
            else:
                combat.act_flee(f, self.dice)
        elif intent.kind == "tame":
            c = self.player.character
            binder = taming.binder(c) if not c.uses_companions else None
            move = next((m for m in p.moves if binder and m.id == binder.id), None)
            if move:
                self.try_bind(f, move, binder, target, notes)
            else:
                self.try_tame(f, target, notes)
        elif intent.kind == "other":
            combat_improv.resolve(f, p, target, intent.summary or intent.words, self.dice, intent.effect)
        else:
            combat.act_attack(f, p, target, self.dice)

        if intent.kind != "flee":
            f.player_acted = True
        if not f.over and not f.enemies() and not combat.muster(f):
            f.over = "victory"
        p.counters.pop("moved_now", None)
        if p.counters.pop("free_action", None) and not f.over:   # a movement on its own did not use the action - the player acts again
            return RoundOutcome("free", notes, [])
        if not f.over:
            combat.finish_round(f, self.dice)
        killed = self.hires_down(f)
        self._publish(RoundFought(minute=self.now(), serial=f.serial, round=f.round, over=f.over))
        return RoundOutcome("round", notes, killed, over=f.over)

    def _talk(self, f: combat.Combat, p, target, intent: RoundIntent) -> RoundOutcome:
        """Words are a free action: the fight waits for the player's real move afterwards. Challenger: the words were a call to single
        combat, and it was answered."""
        if combat_perks.challenge(f, intent.words, self.dice):
            return RoundOutcome("talk", [], [])
        problem = parley.attempt(f, target, intent.approach, self.player.character, self.dice)
        if problem:
            return RoundOutcome("talk", [], [], problem=problem)
        if not f.enemies() and not combat.muster(f):
            f.over = "victory"
        return RoundOutcome("talk", [], [], over=f.over)

    def hires_down(self, fight: combat.Combat) -> list:
        """Hired companions who have just gone down: whether each is dead is decided now (kept on them until the fight is over), so the
        narration shows it as it happens and those who saw it can react at once. Returns (member, by whose blow) for those killed; the
        survivors keep who fell, where and by whose hand (engine/party.py mourn)."""
        f = fight
        killed = []
        for m in self.player.party:
            if not m.get("permanent") or m.get("story") or m.get("tutorial") or m.get("npc"):
                continue
            a = f.get(f"ally_{m['id']}")
            if a is None:
                continue
            if a.alive:                                     # standing: any fate left from a fight that ended some other way is stale
                m.pop("down_fate", None)
                continue
            if m.get("down_fate"):                          # already decided when they went down
                continue
            by = f.felled_by.get(a.id, "")                  # (f412) the blow was the foe's: never the player's, never another companion's
            if self.party.decide_down(m, self.dice, in_fight=True) == "dead":
                a.counters["dead"] = 1                      # beyond any healing: a Rescue cannot raise the dead
                combat.tell(f, f"{a.name} takes a killing blow{' from ' + by if by else ''} and does not get up: {a.name} is dead"
                               + (f" (killed by {by}, not by you)" if by and by != "you" else ""))
                killed.append((m, by))
                place = getattr(f, "place", "")
                how = (f" by {by}" if by and by != "you" else "") + (f" at {place}" if place else "")
                party_rules.mourn(self.player.party, m, self.now(), self.player.location, how)
            else:
                combat.tell(f, entities.gendered(f"{a.name} goes down hard{' under ' + whose_blow(by) if by else ''} and lies still: alive, but "
                                                 "out of the fight, and they will have to be carried",            # (f422) in their own pronoun
                                                 party_rules.pronoun_of(m, self.store.meta.seed, self.player.party_used)))
        return killed

    def buff_recipients(self, f: combat.Combat, move, wish: str, notes: list) -> list | None:
        """Who a blessing or a heal goes on: the player (default) or one ally - single-target (f217, f219). A Rescue may name a fallen
        ally: they are the one creature a heal can reach on the ground."""
        if move.effect not in ("buff", "healing") or not wish or wish == "self":
            return None
        allies = f.allies()
        if move.effect == "healing" and getattr(move, "heal_form", "") == "rescue":
            allies = allies + [a for a in f.fighters if a.side == "ally" and not a.alive and not a.counters.get("dead")]
        if wish == "all":
            notes.append(f"{move.name} falls on one at a time - name who it is for. You cast it on yourself.")
            return None
        one = next((a for a in allies if a.id == wish or a.name.lower() == wish.lower()), None)
        return [one] if one else None

    def binding_ability(self, move):
        """The character's Bind a Beast ability if this move is it."""
        if not move:
            return None
        return next((a for a in self.player.character.actives if a.id == move.id and a.field_use == "bind_beast"), None)

    def try_bind(self, f: combat.Combat, move, ability, target, notes: list) -> None:
        """Bind a Beast: a taught ability, once a day, odds set by the creature and the ability's tier; the bond is permanent."""
        c = self.player.character
        p = f.player
        creature = self.world.bestiary.get(target.creature)
        wait = field_rules.ready_in(self.player.field, ability, self.now())
        problem = taming.bind_check(c, target, creature) or combat.can_use(p, move, f) or \
            (f"{ability.name} needs {clock.describe_duration(wait)} more before you can do it again." if wait else "")
        if problem:
            notes.append(problem + " You attack instead.")
            combat.act_attack(f, p, target, self.dice)
            return
        cost = combat.cost_of(p, move, f)
        if move.resource == "stamina":
            p.stamina -= cost
        else:
            p.mana -= cost
        field_rules.start_cooldown(self.player.field, ability, self.now())
        if self.dice.random() < taming.bind_chance(c, target, creature, ability.tier):
            comp = taming.bind(c, creature, target.name)
            f.fighters.remove(target)
            f.tamed.append(comp.name)
            f.log.append(f"{f.player.name} binds {target.name} with {ability.name}; it is now a companion")
            combat.tell(f, f"{target.name} stops fighting and settles beside you - it is yours now ({comp.name}, a new companion)")
            notes.append(f"{comp.name} is bound to you as a companion.")
        else:
            f.log.append(f"{f.player.name} tries to bind {target.name} with {ability.name}, but it will not yield")
            combat.tell(f, f"you reach for {target.name} with {ability.name}, but it breaks free and snaps at you")

    def try_tame(self, f: combat.Combat, target, notes: list) -> None:
        c = self.player.character
        creature = self.world.bestiary.get(target.creature)
        problem = taming.check(c, target, creature)
        if problem:
            notes.append(problem + " You attack instead.")
            combat.act_attack(f, f.player, target, self.dice)
            return
        if self.dice.random() < taming.chance(c, target, creature):
            comp = taming.bind(c, creature, target.name)
            f.fighters.remove(target)
            f.tamed.append(comp.name)
            f.log.append(f"{f.player.name} tames {target.name}; it is now a companion")
            combat.tell(f, f"{target.name} stops fighting and settles beside you - it is yours now ({comp.name}, a new companion)")
            notes.append(f"{comp.name} is bound to you as a companion.")
        else:
            f.log.append(f"{f.player.name} tries to tame {target.name}, but it will not yield")
            combat.tell(f, f"you reach for {target.name}, but it will not yield and snaps at you")

    def alongside(self, f: combat.Combat, p, intent: RoundIntent, target, notes: list) -> bool:
        """A movement ability used on the way (engine/movement.py): it resolves first, and the turn's action follows. Returns True when
        the movement was all the player did, so the action is still theirs to take (the round waits for it). A whole-turn movement
        is not handled here: it is the turn's ability."""
        from engine import movement
        mid = intent.movement or (intent.ability if intent.kind == "ability" else "")
        move = next((m for m in p.moves if m.id == mid and m.effect == "mobility"), None)
        if move is None or movement.whole_turn(move):
            return False
        alone = not intent.movement
        if move.movement == "shift":
            ranged = p.reach == "ranged" or (intent.kind == "ability" and any(m.id == intent.ability and m.reach in ("ranged", "area")
                                                                                for m in p.moves))
            if intent.step == "withdraw" or ranged:
                p.counters["shift_back"] = 1
        ally = self.movement_ally(f, intent)
        problem = combat.act_ability(f, p, move, target, self.dice, give=[ally] if ally else None)
        p.counters.pop("shift_back", None)
        if problem:
            notes.append(problem)
            return False if not alone else self.act_again(p)
        p.counters["moved_now"] = 1
        return self.act_again(p) if alone else False

    @staticmethod
    def act_again(p) -> bool:
        p.counters["free_action"] = 1
        p.counters["acting_again"] = 1
        return True

    @staticmethod
    def movement_ally(f: combat.Combat, intent: RoundIntent):
        for key in (intent.target, intent.buff_for):
            a = next((x for x in f.allies() if key and (x.id == key or key.lower() in x.name.lower())), None)
            if a is not None:
                return a
        return None

    def apply_step(self, f: combat.Combat, p, intent: RoundIntent, target) -> bool:
        """The step that rides along with an action, priced by the movement law: toward the fight is free; away costs the round
        (parting blows and all) unless your own line covers you; in heavy armor, moving is the round's work either way.
        Returns True when the step consumed the action."""
        bf = battlefield
        if not intent.step or intent.kind in ("move", "flee", "talk"):
            return False
        if intent.step == "advance":
            if p.pace == "slow":
                story = (bf.approach(f, p, target) if target else "") or "moves up"
                f.log.append(f"{p.name} {story}")
                combat.tell(f, f"in that armor, moving is the work of the round: you {story} and ready yourself")
                return True
            story = combat.advance_step(f, p, target)
            if story:
                f.log.append(f"{p.name} {story}")
                combat.tell(f, f"you {story}")
            return False
        covered = any(not bf.hostile(p, o) and bf.can_hold(o) for o in bf.standing(f, p.zone_id))
        threatened = bool(bf.engaged(f, p)) or any(bf.hostile(p, o) for o in bf.standing(f, p.zone_id))
        if (covered or not threatened) and p.pace != "slow":
            story = bf.withdraw(f, p)
            f.log.append(f"{p.name} {story}")
            combat.tell(f, f"you {story}")
            return False
        story = combat.retreat(f, p, self.dice)
        f.log.append(f"{p.name} {story}")
        combat.tell(f, f"backing away is the work of the round: you {story}")
        return True

    # ---------- a draught

    def item_for(self, fight: combat.Combat, name: str, target=None) -> tuple[Item | None, str]:
        """The consumable a line names, usable in a fight, or why not. 'give Maren a healing draught': the whole line is the name."""
        c = self.player.character
        item = inventory.find(c.inventory, name)
        if not item and target is not None:
            low = name.lower()
            usable = [i for i in c.inventory if i.good and inventory.GOODS[i.good].combat]
            item = next((i for i in usable if inventory.GOODS[i.good].name.lower() in low), None) or \
                next((i for i in usable if "health" in inventory.GOODS[i.good].restores), None)
        if not item or not item.good or not inventory.GOODS[item.good].combat:
            return None, "You have nothing like that to use in a fight."
        return item, ""

    def use_item(self, fight: combat.Combat, item: Item, target=None, frugal: bool = False) -> tuple[list, object]:
        """Use a consumable mid-fight, on yourself or on a party member; `frugal` keeps it (Frugal Hands, the scene's roll). Returns the
        figures of what it restored or cured (the records the window explains) and the good."""
        c, f = self.player.character, fight
        p = target or f.player
        g = inventory.GOODS[item.good]
        if not frugal:
            inventory.take(c.inventory, g.name, 1)
        pools_now = {"health": ("hp", "max_hp"), "mana": ("mana", "max_mana"), "stamina": ("stamina", "max_stamina")}
        figures = []
        for pool, pct in g.restores.items():
            cur, top = pools_now[pool]
            before, maximum = getattr(p, cur), getattr(p, top)
            shielded = 0
            if pool == "health":
                gained, shielded = combat_perks.mend(f, f.player, p, maximum * pct / 100)
            else:
                setattr(p, cur, min(maximum, before + maximum * pct / 100))
                gained = round(getattr(p, cur) - before)
            rec = combat.new_heal(f, p, f"uses {g.name} on", pool, gained, [
                [g.name, f"restores {pct:g}% of {'your' if p is f.player else p.name.split()[0] + chr(39) + 's'} maximum {pool} ({round(maximum)})"],
                [f"{pool} before and after", f"{round(before)} to {round(getattr(p, cur))}"]]
                + ([["barrier (Overabundance)", f"+{shielded}"]] if shielded else []))
            figures.append(rec or {"id": "", "figure": f"(+{gained} {pool})"})
        cured = [st for st in g.cures if st in p.statuses]
        for st in cured:
            effects.end_status(p, st)
        if cured:
            rec = combat.new_heal(f, p, f"uses {g.name} on", "", 0, [[g.name, f"cures {', '.join(cured)}"]])
            if rec:
                rec["figure"] = f"(cured {', '.join(cured)})"
            figures.append(rec or {"id": "", "figure": f"(cured {', '.join(cured)})"})
        f.log.append(f"{f.player.name} uses {g.name}" + ("" if p is f.player else f" on {p.name}"))
        return figures, g

    # ---------- the character and the fighter

    def refresh(self, fight: combat.Combat) -> str:
        """Attribute points spent in the middle of a fight: bring the fighter's maximums, attributes and defences in line with the character,
        and add what each maximum gained to the current value (the same rule as outside a fight), so the bars and spell costs agree.
        The one Character -> Fighter path. Returns sync's note."""
        c, p = self.player.character, fight.player
        fresh = combat.fighter_from_character(c)
        for cur, top in (("hp", "max_hp"), ("stamina", "max_stamina"), ("mana", "max_mana")):
            gained = getattr(fresh, top) - getattr(p, top)
            setattr(p, top, getattr(fresh, top))
            if gained > 0:
                setattr(p, cur, min(getattr(p, top), getattr(p, cur) + gained))
        p.attrs = fresh.attrs
        p.ward, p.armor = fresh.ward, fresh.armor
        return self.sync(fight)

    def sync(self, fight: combat.Combat) -> str:
        """The one Fighter -> Character path, at a round's commit: the pools, a named spell's day (f397), the blessing spent. Returns the
        note for the player ('' when there is none)."""
        c, p = self.player.character, fight.player
        c.health, c.stamina, c.mana = float(p.hp), float(p.stamina), float(p.mana)
        for mid in p.counters.pop("day_cast", []):      # (f397) a named spell cast: the day is kept, for its cooldown in days
            c.spell_days = {**c.spell_days, mid: self.now()}
        if c.orenna_breath and not p.breath:
            c.orenna_breath = False
            from engine import orenna
            return orenna.O["blessing"]["spent"]
        return ""

    # ---------- the end

    def close(self, fight: combat.Combat) -> Ending:
        """The fight is over: the row dropped, the minutes it took, who fell. A trial of rank (duel): nobody dies, the blades were pulled,
        the pools written back. FightEnded published."""
        f = fight
        c = self.player.character
        if f.duel:
            for x in f.fighters:
                if x.alive and x.hp < 1:
                    x.hp = 1
            note = self.sync(f)
            self.store.save_combat(None)
            minutes = max(1, math.ceil(f.round * combat.RULES["round_seconds"] / 60))
            self._publish(FightEnded(minute=self.now(), serial=f.serial, outcome=f.over, duel=True))
            return Ending(f.over, minutes, [], [], [], duel=True, notes=[note] if note else [])
        needs.fight(c)
        self.store.save_combat(None)                        # (f499) what the fight remembered of itself goes with its row
        minutes = max(1, math.ceil(f.round * combat.RULES["round_seconds"] / 60))
        dead = [e for e in f.fighters if e.side == "enemy" and not e.alive]
        fallen = [a for a in f.fighters if a.side == "ally" and a.id.startswith("ally_") and not a.alive]
        self._publish(FightEnded(minute=self.now(), serial=f.serial, outcome=f.over, dead=tuple(combat.who(e) for e in dead),
                                 fallen=tuple(a.id for a in fallen)))
        return Ending(f.over, minutes, dead, fallen, [a.id for a in fallen])

    def companions_after(self, fight: combat.Combat, fallen_ids: set) -> list:
        """A companion who went down is out for a day, and may not survive. A Bound summon unmade in the fight stays unmade until
        its spell is cast again. Returns the notes for the player."""
        c = self.player.character
        notes = []
        note = summons.after_fight(c, fight)
        if note:
            notes.append(note)
            self.store.save_player(self.player)
        rules = combat.RULES["creatures"]["companion_fall"]
        changed = False
        now = self.now()
        last = getattr(self.player, "party_last_fight", None)
        last = last if (last or {}).get("minute") == now else None
        for comp in c.companions:
            if f"ally_{comp.id}" not in fallen_ids or not comp.active:
                continue
            changed = True
            comp.fallen = True
            comp.recover_at = now + int(rules["recover_hours"] * 60)
            p = party_rules.companion_pronoun(comp)
            if self.dice.random() < rules["death_chance"]:
                comp.dead = True
                notes.append(f"{comp.name} is dead. {'It' if p == 'it' else p.capitalize()} fell protecting you.")
                if last is not None:                           # (f385) what the party will talk over: the player's own animal, by name
                    bestiary = self.world.bestiary
                    kind_of = bestiary[comp.creature].name.lower() if comp.creature in bestiary else (comp.kind or "animal")
                    last.setdefault("fallen_what", {})[comp.name] = f"the player's own {kind_of}"
            else:
                notes.append(f"{comp.name} is badly hurt and will need a day to recover.")
                if last is not None and comp.name in last.get("fallen", []):      # (f385) down, not dead: no wake is held for them
                    i = last["fallen"].index(comp.name)
                    last["fallen"].pop(i)
                    if i < len(last.get("fallen_ids", [])):
                        last["fallen_ids"].pop(i)
                    last.setdefault("hurt", []).append(comp.name)
        if changed:
            self.store.save_player(self.player)
        return notes

    def yields(self, fight: combat.Combat, allowed: bool = True) -> None:
        """(f392) A won fight against outlaws can leave one who lives and yields (arcs.yaml prisoner.chance): chosen here among the fallen,
        before the after-fight passage is written, so the story and the captive agree. It used to be rolled afterwards, among the dead:
        a night's run had an outlaw narrated dead and then throwing down his weapon. An arc's camp has its leader's own way, and a dungeon
        or the road none (`allowed` False)."""
        from engine.arcs import A as R
        f = fight
        if not allowed:
            return
        fallen = [e for e in f.fighters if e.side == "enemy" and not e.alive and e.category in R["people_categories"]]
        if not fallen or any(e.alive and e.surrendered for e in f.fighters if e.side == "enemy"):
            return
        PR = R["prisoner"]
        chance = max(PR["min_chance"], min(PR["max_chance"], PR["chance"] + self.player.outlaw_rep * PR["rep_chance_per_point"]))
        if streams.keyed("yield", f.serial).random() < chance:                                       # (f501) the fight's own die
            who = max(fallen, key=lambda e: e.level)
            who.hp, who.surrendered = 1, True

    def rewards(self, fight: combat.Combat, dead: list, yielded: list) -> Rewards:
        """A win's take: the experience the fallen and the yielded are worth, the coin and the drops (a boss's prizes, a codex, a relic;
        a spell book now and then), every piece committed under the engine's own name (fallback_name, spells.plain_codex: the naming
        operation after the win gives the model's, f502), the bodies and the carcasses written to the place. The coin is the raw take:
        what the player gets of it (a light-fingered hire) and the pack are the scene's; award() adds it and levels."""
        c = self.player.character
        pack = combat.RULES["creatures"].get("pack", {})
        pack_xp = (pack.get("health", 1) + pack.get("damage", 1)) / 2
        deaths_ledger = 1 + (pools.mechanic(c, "deaths_ledger") or 0) / 100
        bestiary = self.world.bestiary
        total_xp = round(sum(leveling.kill_xp(c.level, e.level, e.rank)
                             * (pack_xp if bestiary[e.creature].group[0] >= 2 else 1)
                             * (deaths_ledger if e.category == "undead" else 1) for e in dead))
        total_xp += round(sum(leveling.kill_xp(c.level, e.level, e.rank) for e in yielded) * combat.RULES["talk"]["surrender_reward"])
        coins, found, to_name = 0, [], []
        scavenger = pools.mechanic(c, "scavenger") or 0
        state = self.store.load_place(self.player.location)
        skinnable = 0
        now = self.now()
        bodies = {e.id: {"creature": e.creature, "name": e.name, "level": e.level, "category": e.category, "rank": e.rank,
                         "minute": now, "asked": False} for e in dead}
        for e in dead:
            if e.rank == "boss":
                gained, prizes = loot.boss_drops(e, self.dice, loot.keeps_companions(c))
                coins += gained
                for prize in prizes:
                    if prize.rarity in ("rare", "epic", "legendary"):
                        self.fallback_name(prize, e.name)                      # (f502) the engine's name now; the model's after the commit
                        to_name.append((prize, e.name, "", None))
                    found.append(prize)
                codex = spells.codex_drop(e.level, self.dice, e.element)          # (f397) now and then, a codex: a named spell
                if codex is not None:
                    spells.plain_codex(codex)                                      # (f502) likewise
                    to_name.append((codex, e.name, "codex", None))
                    found.append(codex)
                if prizes:
                    bodies[e.id]["carried"] = inventory.label(prizes[0])
                kit = (e.boss or {}).get("kit") or bosses.kit_for(e.category)
                tier = (e.boss or {}).get("tier") or "dungeon"
                if self.dice.random() < bosses.B["relic_chance"].get(tier, 0):
                    relic = accessories.boss_relic(kit, e.level, self.dice)
                    self.fallback_name(relic, e.name)                              # (f502) the story as the win found it: the naming asks in these words
                    to_name.append((relic, e.name, "relic", e.boss or {"kit": kit, "tier": tier}))
                    found.append(relic)
                if loot.has_remains(e):
                    state.carcasses.append({"creature": e.creature, "level": e.level, "minute": now})
                    skinnable += 1
                continue
            gained, item = loot.drops(e, self.dice, loot.keeps_companions(c))
            if loot.has_remains(e):
                state.carcasses.append({"creature": e.creature, "level": e.level, "minute": now})
                skinnable += 1
            plunder = (pools.mechanic(c, "last_possessions") or 0) if e.category in ("hostile people", "person template") else 0
            coins += round(gained * (1 + scavenger / 100) * (1 + plunder / 100))
            lucky = pools.mechanic(c, "lucky_find") or 0
            if not item and lucky and self.dice.random() < lucky / 100:
                item = loot.drops(e, self.dice, loot.keeps_companions(c))[1]
            if item:
                if item.rarity in ("rare", "epic", "legendary"):
                    self.fallback_name(item, e.name)                               # (f502)
                    to_name.append((item, e.name, "", None))
                found.append(item)
                bodies[e.id]["carried"] = inventory.label(item)
        for e in dead:
            book = spells.book_drop(e.level, e.rank, self.dice)               # (f397) now and then, a spell book of the rank its level allows
            if book is not None:
                found.append(book)
        state.bodies = field_rules.keep_bodies(state.bodies + list(bodies.values()), now)
        self.store.save_place(state)
        return Rewards(total_xp, coins, found, to_name, skinnable)

    def award(self, xp: int, coins: int) -> int:
        """The coin the player gets and the experience earned, once the finds are stowed. Returns the levels gained."""
        c = self.player.character
        c.coins += coins
        return leveling.gain_xp(c, xp)

    def captives(self, fight: combat.Combat, yielded: list, leader: str | None = None) -> list:
        """Foes who yielded and are taken: people can be bound and kept (questioned, let go, handed to the watch); the rest wait on the
        player (f385). (f392) No more than walk bound at once (lifecycles.yaml captive.most_escorted): the rest wait on the player's word
        like any foe who yields. An arc's camp leader is taken by the camp's own way (arc_actions.camp_fight_over). Returns the records,
        strongest first, each named apart from every name already in the save (f422)."""
        from engine.arcs import A as R
        present = tuple(entities.L["captive"]["present_with_player"])
        escorted = list(dict.fromkeys(e.links.get("npc", "") for e in self.store.find_entities(kind="captive", state=present, owner="player")))
        room = entities.L["captive"]["most_escorted"] - len(escorted)
        ppl = sorted([e for e in yielded if e.category in R["people_categories"] and e.name != leader], key=lambda e: -e.level)[:max(0, room)]
        if not ppl:
            return []
        rng = streams.keyed("surrender", fight.serial)                                               # (f501) the fight's own die
        taken = {n.split()[0].lower() for n in self.store.npc_names() if n}            # (f422) no two captives, or a captive and a
        out = []                                                                            # townsman, share a name in one save
        for e in ppl:
            free = [n for n in R["prisoner"]["names"] if n.split()[0].lower() not in taken] or R["prisoner"]["names"]
            name = rng.choice(free)
            taken.add(name.split()[0].lower())
            kind = re.sub(r" ?\d+$", "", re.sub(r"\s*\([^)]*\)", "", e.name)).strip()            # (f422) no "(bounty)" on what they are
            out.append(Captive(name, kind, e.level, e.creature, e.id, rng.random() < R["prisoner"]["tip_chance"]))
        return out

    FALLBACK_FIRST = ["Ashen", "Hollow", "Ember", "Gloam", "Thorn", "Dusk", "Varr", "Kestrel", "Wraith", "Sable", "Oath", "Rime"]
    FALLBACK_SECOND = ["fang", "bane", "ward", "song", "reach", "brand", "mourn", "keep", "bite", "light", "fall", "shard"]

    def fallback_name(self, item: Item, source: str) -> None:
        """The engine's own name for an item when the model cannot supply one. A failed naming must never cost the player the fight's rewards."""
        b = items.base_of(item)
        label = b.label or b.name
        if item.rarity != "legendary":
            item.name = f"{item.rarity.capitalize()} {label}"
            item.description = f"Taken from {source}."
            return
        taken = {t.lower() for t in self.store.legendary_names()}
        rng = streams.keyed("item_name", item.uid, len(taken))                                        # (f501) the find's own die
        for _ in range(200):
            name = rng.choice(self.FALLBACK_FIRST) + rng.choice(self.FALLBACK_SECOND)
            if name.lower() not in taken:
                break
        else:
            name = f"{label} {len(taken) + 1}"
        item.name = name
        item.title = f"the {label.title()} of {source}"
        item.description = f"A {label} of uncommon make, carried off from {source}. No song has been sung of it yet."
        self.store.add_legendary_name(item.name)

    def phoenix(self):
        """A Phoenix item turns one killing blow aside every few days: half health, nothing lost, the fight is over. Returns (the item,
        the days it waits) when it does, None when it cannot."""
        c = self.player.character
        item = next((i for i in c.equipment.values() if i.legendary_effect == "phoenix"), None)
        if not item:
            return None
        day = clock.day(self.now())
        wait = items.LEGENDARY["phoenix"].value
        if day - c.phoenix_day < wait:
            return None
        c.phoenix_day = day
        for pool in pools.POOLS:
            setattr(c, pool, float(pools.maximum(c, pool)) * (0.5 if pool == "health" else 1.0))
        return item, wait

    def fall(self, fight: combat.Combat) -> dict:
        """The player has died: the death's price (engine/death.py), PlayerFell published. Returns the summary the Threshold is told."""
        summary = death.die(self.player.character)
        self._publish(PlayerFell(minute=self.now(), serial=fight.serial, place=self.player.location, deaths=summary["deaths"]))
        return summary
