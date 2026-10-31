"""The combat engine. Pure rules: no model calls, no printing.

Everything here is deterministic given a random generator, so the same code runs real fights,
the danger estimate shown to the player, and the balance simulator (tools/balance.py).
"""

import copy
import math
import random
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from core.models import Character
from core.rules import ATTRIBUTES
from engine import ability_traits as AT
from engine import elements, items, pools, stats as _stats
from engine.battlefield import Battlefield


RULES = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "combat.yaml").read_text(encoding="utf-8"))
# Who can reach whom lives in engine/battlefield.py since B2: zones, rows, engagement and containment, not range bands.
LARGE = {"Large", "Huge", "Gargantuan"}


def growth(level: int) -> float:
    return 1 + items.RULES["item_level_growth"] * (max(1, level) - 1)


class Bonus(BaseModel):
    modifies: str
    trigger: str
    magnitude: int
    flat: bool = False


class Move(BaseModel):
    """An ability as combat sees it."""
    id: str
    name: str
    effect: str
    tier: str
    reach: str
    resource: str
    cooldown: int = 0
    attribute: str = ""
    element: str = ""              # fire, cold... read from the ability's name and description (engine/elements.py)
    rider: str = ""                # an extra effect when it lands (engine/ability_traits.py)
    shape: str = ""                # how a damage ability delivers its damage
    buff: str = ""                 # bulwark, thorns or mend (effect buff)
    buff_stat: str = ""
    command: str = ""
    channel: bool = False          # a mana strike through the wielded weapon
    movement: str = ""             # for mobility: the engine-owned movement kind (data/rules/movement.yaml, engine/movement.py)
    expressions: list[str] = []    # what its element does (data/rules/spellcraft.yaml): each rides on every hit, or is part of the control spell
    power: float = 0               # its own damage multiplier, in place of its tier's (0 = the tier's)
    cost_percent: float = 0        # its own cost, a percent of the pool, in place of its tier's (0 = the tier's)
    cast_turns: int = 0            # turns it takes, the first included; 0 = one, or two for a charged spell (engine/spellcraft.py)
    martial_form: str = ""         # a technique: strike, sweep, flurry, windup or counter (engine/martial.py)
    hits: int = 0                  # a flurry: how many hits
    maneuver: str = ""             # a technique's maneuver: trip, hamstring, rend, disarm, stagger, pin, shove, hook, sunder, feint
    spell_form: str = ""           # a mana damage spell: bolt, blast, burst, curse or charged (engine/spellcraft.py)
    heal_form: str = ""            # for healing: mend, renew, ward, cleanse, transfer or rescue (engine/healing.py)
    summon_form: str = ""          # for a summon: the form it makes (engine/summons.py)
    summon_name: str = ""          # for a summon: what the summoned being is called
    uses: int = 0                  # a relic power: how many times a fight (0 = no limit)
    text: str = ""                 # a relic power: what it does, in words (for the ability list)
    relic: dict = {}               # a relic power: its kind and numbers (engine/relics.py)
    rank: int = 0                  # (f397) a spell's rank (engine/spells.py): it and its form set its numbers
    line: str = ""
    named: bool = False            # (f397) a named spell: stronger, once a fight
    cooldown_days: int = 0         # ...and then not again for this many days (the scene keeps the day on the character)


class Fighter(BaseModel):
    id: str
    name: str
    side: str                      # player | ally | enemy
    level: int
    flaw: str = ""                 # a hired ally's weakness that shows in a fight (engine/quirks.py)
    flaw_used: bool = False
    size: str = "Medium"
    category: str = ""
    creature: str = ""
    spawn: str = ""                # the id of the big-event creature this fighter is (engine/events.py), if any
    rank: str = "normal"
    attrs: dict[str, int]
    hp: float
    max_hp: int
    stamina: float = 0
    max_stamina: int = 0
    mana: float = 0
    max_mana: int = 0
    weapon_name: str = "fists"
    weapon_damage: float = 2
    weapon_attrs: list[str] = ["strength"]
    reach: str = "melee"
    damage_type: str = "physical"
    element: str = ""              # what this fighter's attacks are made of, if anything (a fire elemental, a red dragon)
    hit_element: str = ""          # the element of the move being used right now
    armor: float = 0
    ward: float = 0
    evasion_penalty: int = 0
    zone_id: str = ""              # where they stand on the battlefield (engine/battlefield.py), the only range model since B2
    row: str = "loose"             # their place in their side's local formation there: front, back or loose
    position_tags: list[str] = []  # temporary personal facts of position: elevated, covered, concealed, exposed
    engaged_with: list[str] = []   # who they are tied up with in close combat: explicit, symmetric, same zone (battlefield.engage)
    hold: int = 0                  # how many enemies they contain while holding a front row (0: they hold nobody)
    pace: str = "normal"           # slow, normal or fast (battlefield.pace_of): how fast they cover ground
    winding: dict = {}             # a telegraphed blow being wound up: {"target": fid, "round": n}; lands on their next turn
    covering: str = ""             # the ally this fighter has put themselves in front of, until their own next turn
    starts_far: bool = False       # spotted at a distance: they begin loose in a side zone when the field has one
    defending: float = 0
    statuses: dict[str, int] = {}
    cooldowns: dict[str, int] = {}
    moves: list[Move] = []
    bonuses: list[Bonus] = []
    move_round: int = -9
    kill_round: int = -9
    attacked_since_turn: bool = False
    temperament: str = "aggressive"
    armor_pierce: float = 0
    crit_resist: float = 0
    offhand_spell: float = 0              # an off-hand focus's spell power
    spell_mult: float = 1.0               # while a spell is cast: 1 + its casting attribute / spell_attribute
    spell_share: float = 1.0              # (f400) a hire's spells: the share of a player's spell of the same rank they hit and heal for
    adaptive: bool = False
    legendary: dict[str, float] = {}     # legendary effect id -> value
    slays: dict[str, float] = {}         # creature category -> bonus % (dragonslayer etc.)
    ally_role: str = ""                   # a hired party member's role (priests heal)
    mech_names: dict[str, str] = {}        # mechanic id -> what the passive or gear that gives it is called, for the damage breakdown
    can_heal: bool = False                # a story companion who can tend wounds
    order: str = ""                       # what the player told this ally to do: focus | guard | hold | heal ("" = fight on their own)
    order_target: str = ""                # the enemy a focus order names; (f406) for a heal order, who to heal ("self", or an ally's id)
    story_id: str = ""                    # the party member this fighter is, when their wounds carry between fights
    always_miss: bool = False            # the first fight's troll: its blows go wide until the mentor steps in
    spell_parts: list = []                # while a spell is cast: [[label, value]] making up its weapon_damage, for the hit breakdown
    spell_kind: str = ""                  # "spell" or "channel" while one is cast
    weary: float = 0                      # hunger and fatigue: percent change to all damage dealt (negative)
    tether: int = 0                       # Soul Tether: a killing blow is survived once, at this percent of max health
    summon_form: str = ""                 # a summon (engine/summons.py): its form - bound, sentinel, striker, swarm, totem, decoy, volatile
    summon_owner: str = ""                # who made it
    summon_of: str = ""                   # the summon ability that made it
    summon_until: int = 0                 # the round it fades (0: it lasts - a Bound summon)
    summon_tier: str = ""
    summon_cast: int = 0                  # tells one casting's bodies from another's
    wards: dict[str, float] = {}         # creature category -> damage reduction % (dragonward etc.)
    hardening_stacks: int = 0
    windwalker_ready: bool = False
    deathward_used: bool = False
    breath: bool = False                 # Orenna's Last Breath, unspent: one killing blow restores health and mana in full
    yields_at: float = 0.0               # a foe that gives up the fight, unhurt past this, at this share of its health (never dies)
    yield_text: str = ""
    bound: bool = False                  # held to its master by a sworn seal (the Bound Executioner)
    second_wind_used: bool = False
    conditional: list[dict] = []         # passive mechanics active only when a trigger is true
    shield: float = 0                    # barrier that absorbs damage before health
    fled: bool = False                   # left the fight alive
    first_blood_used: bool = False
    relentless: int = 0
    aegis_round: int = -1
    archmage_used: bool = False
    spells_cast: int = 0
    counters: dict[str, Any] = {}        # small per-fight tallies for gear and element effects: counts, ids, [who, how much, until round] lists
    buffs: dict[str, dict] = {}          # timed effects from relic powers: {id: {rounds, mech, drain, collapse}}
    relic_uses: dict[str, int] = {}      # how many times each relic power has been used this fight
    boss: dict = {}                      # set-piece boss state: legendary actions and resistance, phases (engine/bosses.py)
    family: str = ""                      # a creature's family (data/world/families.yaml): how it fights
    behaviors: dict[str, float] = {}     # that family's behaviours (engine/behaviors.py)
    surrendered: bool = False            # yielded rather than fled: it can be taken prisoner
    talked: bool = False                 # spoken to once this fight, for good or ill (engine/parley.py)
    recent_casts: list[str] = []         # the last few spells cast, in order, for the perks that count them (engine/combat_perks.py)
    last_mobility: str = ""              # the mobility ability used last, for the perks that reset it
    shadow: dict = {}                    # Shadowmark: where the shadow waits {zone, row, until, move}; empty when none
    status_from: dict[str, str] = {}     # who put each status on this fighter (Malefic Step finds your curses by it)
    last_hurt_by: str = ""               # the last hostile fighter whose blow landed on this one (Vengeance Leap)
    ignite: float = 0                    # burning: damage each round, from the strongest ignite on it (engine/afflictions.py)
    poison: list[float] = []             # poisoned: each stack's damage each round (engine/afflictions.py)
    poison_fixed: list[float] = []       # poison stacks that never fade while it lives (Persistent Toxin, f268)
    bleed: float = 0                     # bleeding: the open wound's tick (engine/afflictions.py)
    curses: list[dict] = []              # curses laid on this fighter, dealing their damage over its turns (engine/spellcraft.py)
    charging: dict = {}                  # a charged spell this fighter is winding up, released at the start of its next turn
    sundered: float = 0                  # the share of armor broken by Sunder this fight (engine/martial.py)
    counter_move: dict = {}              # a readied counter (engine/martial.py), until this fighter's next turn
    corroded: float = 0                  # acid: the share of armor and ward eaten away this fight (engine/spellcraft.py)
    armor_weight: str = ""               # the heaviest armor actually worn (fitted or not), for the perks that care what you carry
    wears_metal: bool = False            # any metal armor worn (Curse of Rust)
    attuned: str = ""                    # the element of the last spell cast, carried on the weapon (Attuned Edge)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def best_attr(self, names: list[str]) -> int:
        return max((self.attrs.get(a, 10) for a in names), default=10)


class Combat(BaseModel):
    round: int = 1
    battlefield: Battlefield | None = None   # the ground this fight is on (engine/battlefield.py); None in bare simulations and old saves
    gentle: bool = False           # Gentle Approach: timid animals don't flee
    fighters: list[Fighter]
    log: list[str] = []
    over: str = ""                 # "" | victory | defeat | fled
    place: str = ""
    conditions: list[str] = []     # triggers true for the whole fight: at_night, in_bad_weather, in_swamp...
    zone_effects: dict[str, dict] = {}   # ground a perk has changed for a while: {zone_id: {"frozen_until": round, "by": fighter id}}
    story: list[str] = []          # this round's events in words, for the narrator
    opened: bool = False
    focus: str = ""                # the enemy the player last went after; companions follow it
    player_acted: bool = False     # the player has done something other than run
    reserves: list[Fighter] = []   # the rest of a big camp: they join the fight in waves
    reinforce_every: int = 2       # a wave arrives every this many rounds (and at once if the field is clear)
    reinforce_count: int = 2       # how many come at a time
    reinforce_from: int = 1        # no wave comes before this round (a quiet start gives the player time)
    thrall_used: bool = False      # the first foe slain has already risen to fight for the player
    ally_reserves: list[Fighter] = []   # a party told to hold back: they reach the fight on ally_arrive
    ally_arrive: int = 3
    order_round: int = 0           # the round the player last gave an order (one a turn, and it does not use the action)
    ordered: list[str] = []        # (f383) the allies that order went to: telling the same ones again this turn corrects it
    record: bool = False           # keep a breakdown of every blow (the window's combat log); off while the odds are simulated
    serial: str = ""               # tells this fight's blows apart from another fight's
    hits: list[dict] = []          # this turn's blows: who, how the roll and the damage were worked out, what was dealt
    duel: bool = False             # a trial of rank: nobody can die, the blow that would kill ends it and decides it
    mentor: bool = False           # the scripted first hunt: no running, and the player cannot die (a killing blow leaves them on 1)
    mentor_troll: bool = False     # the scripted troll: one round of its blows going wide, then the mentor steps in and ends it
    mentor_ally: Fighter | None = None    # the mentor, waiting to step in
    mentor_in: bool = False        # she has stepped in
    mentor_line: str = ""          # how she steps in, told to the narrator
    mentor_strike_line: str = ""   # how she ends it, told to the narrator the round after she steps in
    mentor_struck: bool = False    # she has struck
    item_round: int = 0            # the round the player last used an item (one a turn, and it does not use up the action)
    heals: int = 0                 # how many restorations this fight has recorded, to tell their figures apart
    no_rewards: bool = False       # no experience, coin or loot for this fight (the player did not earn it)
    mentor_phase: int = 0          # the troll script: 0 it strikes her, 1 she guards you, 2 she waits for your order and ends it
    mentor_stalls: int = 0         # rounds she has waited for the order to attack
    bound_id: str = ""             # the summon ability that holds the player's Bound summon (engine/summons.py)
    bound_fell: bool = False       # the Bound summon was destroyed in this fight: it cannot be made again until the fight is over
    mentor_hurt_line: str = ""     # the blow that lands on her, told to the narrator
    mentor_guard_line: str = ""    # how she guards the player, told to the narrator
    mentor_saved: int = 0          # how many times the floor has held
    mentor_beats: list[str] = []   # lessons already given
    burn_told: bool = False        # (f349) the element on the player's blade has been told to the narrator once; after that it is a figure, not a sentence
    felled_by: dict[str, str] = {}  # (f412) who struck each fallen fighter down, as the story names them: a night's narration gave a
                                    # pirate's killing blow on a companion to the player's own blade

    def get(self, fid: str) -> Fighter | None:
        return next((f for f in self.fighters if f.id == fid), None)

    @property
    def player(self) -> Fighter:
        return next(f for f in self.fighters if f.side == "player")

    def enemies(self) -> list[Fighter]:
        return [f for f in self.fighters if f.side == "enemy" and f.alive and not f.fled and not f.counters.get("turned")]

    def allies(self) -> list[Fighter]:
        return [f for f in self.fighters if f.side == "ally" and f.alive]


# ---------- telling the story ----------
# Every mechanical event is also described in words, so the narrator can dramatize what really happened.

ORDINALS = ["first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth", "ninth", "tenth"]


def who(f: Fighter) -> str:
    if f.side == "player":
        return "you"
    if f.side == "ally":
        return f.name
    name = f.name.replace(" (elite)", "")
    if name.lower().startswith(("the ", "a ", "an ", "one of ")) or (f.boss and name[:1].isupper()):
        return name                                   # already says what it is, or is a person with a name of their own
    prefix = "the hulking " if "(elite)" in f.name else "the "
    parts = name.rsplit(" ", 1)
    if len(parts) == 2 and parts[1].isdigit() and 1 <= int(parts[1]) <= 10:
        return f"{prefix}{ORDINALS[int(parts[1]) - 1]} {parts[0]}"
    return prefix + name


def whose(f: Fighter) -> str:
    return "your" if f.side == "player" else f"{who(f)}'s"


def vb(f: Fighter, you_form: str, other_form: str) -> str:
    return you_form if f.side == "player" else other_form


def condition(f: Fighter) -> str:
    frac = f.hp / f.max_hp if f.max_hp else 0
    if frac <= 0:
        return "down"
    if frac > 0.75:
        return "barely touched"
    if frac > 0.5:
        return "wounded"
    if frac > 0.25:
        return "badly wounded"
    return "barely standing"


def severity(dealt: float, max_hp: int) -> str:
    frac = dealt / max_hp if max_hp else 0
    if frac < 0.06:
        return "barely a scratch"
    if frac < 0.15:
        return "a solid hit"
    if frac < 0.3:
        return "a heavy blow"
    return "a devastating blow"


def possessive(f: Fighter) -> str:
    """(f419) Whose weapon, said rightly: 'your' for the player, a companion's own his or her (engine/names.py CAST, Maren hers), 'their'
    for any other person, 'its' for a beast or a thing. Every ally was 'its' before: 'Odly strikes with its sword'."""
    if f.side == "player":
        return "your"
    from engine import names
    pron = names.CAST.get(f.name.split()[0]) if f.side == "ally" and f.name else None
    if pron is None and f.side == "ally" and f.name == "Maren Holt":
        pron = "she"
    if pron in names.POSSESSIVE:
        return names.POSSESSIVE[pron]
    from engine.arcs import A as ARCS
    return "their" if f.ally_role or f.category in ARCS["people_categories"] else "its"


def weapon_phrase(f: Fighter) -> str:
    return f"with {possessive(f)} {f.weapon_name}"


def tell(combat: Combat, text: str, rec: dict | None = None) -> None:
    """Add an event to this round's story. A blow's event carries its tag ([h2]) so the narrator can place the figure."""
    from engine import hygiene
    text = hygiene.undash(text)                     # (f413) the story the narrator is handed has no dashes to copy (f403)
    if rec is not None:
        text += f" [{rec['tag']}]"
    combat.story.append(text[0].upper() + text[1:])


def new_hit(combat: Combat, att: Fighter, dfn: Fighter, label: str) -> dict | None:
    """Start the record of one blow, or None when blows are not being recorded."""
    if not combat.record:
        return None
    if not combat.serial:
        combat.serial = f"{random.randrange(16 ** 4):04x}"
    n = 1 + max((int(h["tag"][1:]) for h in combat.hits if str(h.get("tag", "")).startswith("h")), default=0)   # (f371) not the count: merged records leave gaps
    rec = {"id": f"{combat.serial}-{combat.round}-{n}", "tag": f"h{n}", "round": combat.round, "att": att.name, "dfn": dfn.name,
           "att_side": att.side, "dfn_side": dfn.side, "label": label, "outcome": "", "chance": 0.0, "roll": 0.0,
           "note": "", "base": {}, "steps": [], "defence": {}, "extras": [], "final": 0, "figure": ""}
    combat.hits.append(rec)
    return rec


def new_heal(combat: Combat, who: Fighter, label: str, pool: str, amount: int, extras: list) -> dict | None:
    """The record of a restoration (a draught drunk), shown like a blow's: a figure in the story, and the working on hover."""
    if not combat.record:
        return None
    if not combat.serial:
        combat.serial = f"{random.randrange(16 ** 4):04x}"
    combat.heals += 1
    rec = {"id": f"{combat.serial}-{combat.round}-i{combat.heals}", "tag": "", "round": combat.round, "att": who.name, "dfn": who.name,
           "att_side": who.side, "dfn_side": who.side, "label": label, "outcome": "heal", "chance": 0.0, "roll": 0.0, "note": "",
           "base": {}, "steps": [], "defence": {}, "extras": extras, "final": amount, "figure": f"(+{amount} {pool})"}
    combat.hits.append(rec)
    return rec


def hit_step(rec: dict | None, mult: float, label: str, factor: float) -> float:
    """One multiplier in the damage chain, written into the record as it is applied."""
    if rec is not None and label and abs(factor - 1) > 1e-9:
        rec["steps"].append([label, round(factor, 3)])
    return mult * factor


COVER = {"dragon": "scales", "plant": "bark", "construct": "plating", "beast": "hide", "monstrosity": "hide", "lycanthrope": "hide",
         "aberration": "hide", "swarm": "mass", "ooze": "body", "elemental": "outer shell"}


def cover(f: Fighter) -> str:
    """(f373) What turns a blow on this fighter, in words: a wolf's hide, a dragon's scales, a soldier's armor. A wolf told as wearing
    'armor' came out of the narrator as plate mail."""
    if f.side in ("player", "ally") or not f.category:
        return "armor"
    return COVER.get(f.category, "armor")


def figure(rec: dict) -> str:
    out = rec["outcome"]
    if out == "miss":
        return "(miss)"
    if out == "phase":
        return "(passes through)"
    word = {"crit": "critical, ", "graze": "graze, "}.get(out, "")
    more = (f" +{rec['bleed']} from the open wound" if rec.get("bleed") else "") + "".join(f", {s}" for s in rec.get("inflicted", []))
    return f"({word}{rec['final']} damage{more})"


# ---------- building fighters ----------

def fighter_from_character(c: Character) -> Fighter:
    from engine import loadout as _loadout
    weapon = c.equipment.get("main_hand")
    _gear = _stats.gear_attributes(c)
    attrs = {a: _stats.effective(c, a, _gear) for a in ATTRIBUTES}
    armor = ward = 0.0
    penalty = 0
    heaviest = raw_heaviest = "light"
    wears_metal = False
    weights = items.RULES["weight_classes"]
    flags = {"armor_pierce": 0.0, "crit_resist": 0.0, "adaptive": False}
    offhand_spell = 0.0
    for item in c.equipment.values():
        b = items.base_of(item)
        f = items.flags(item)
        flags["armor_pierce"] += f.get("armor_pierce", 0)
        flags["crit_resist"] += f.get("crit_resist", 0)
        flags["adaptive"] = flags["adaptive"] or bool(f.get("adaptive"))
        if b.is_offhand_focus:
            offhand_spell += items.value(item)
            continue
        if b.is_weapon:
            continue
        v = items.value(item)
        if b.ward:
            ward += v
        else:
            armor += v
            ward += v * f.get("ward_fraction", 0) / 100
        from engine import world_perks
        raw = items.weight(item)
        if raw and ["light", "medium", "heavy"].index(raw) > ["light", "medium", "heavy"].index(raw_heaviest):
            raw_heaviest = raw
        if getattr(b, "family", None) == "metal":
            wears_metal = True
        w = "" if world_perks.fitted(c, item) else raw
        if w:
            penalty = min(penalty, weights[w]["evasion"])
            if ["light", "medium", "heavy"].index(w) > ["light", "medium", "heavy"].index(heaviest):
                heaviest = w
    bonuses = [Bonus(modifies=p.modifies.value, trigger=p.trigger.value, magnitude=p.magnitude)
               for p in c.passives if not p.mechanic]
    for item in c.equipment.values():
        bonuses += [Bonus(modifies=e.modifies, trigger=e.trigger, magnitude=e.magnitude, flat=e.flat) for e in items.effects(item)]
    from engine import sets
    bonuses += [Bonus(modifies=e.modifies, trigger=e.trigger, magnitude=e.magnitude, flat=e.flat) for e in sets.effects(c.equipment)]
    legendary, slays, wards = dict(sets.fight(c.equipment)), {}, {}
    for p_ in c.passives:
        if p_.mechanic == "sworn_enemy" and p_.subject:
            slays[p_.subject] = slays.get(p_.subject, 0) + (p_.value or 20)
    from engine import world_perks
    for mid, v in world_perks.gift_mechanics(c).items():          # Symbiosis: the beast's gift, until the character sleeps
        legendary[mid] = legendary.get(mid, 0) + v
    for item in c.equipment.values():
        le = items.LEGENDARY.get(item.legendary_effect)
        if le:
            if le.category and le.applies == "armor":
                wards[le.category] = wards.get(le.category, 0) + le.value
            elif le.category:
                slays[le.category] = slays.get(le.category, 0) + le.value
            else:
                legendary[le.id] = legendary.get(le.id, 0) + (le.value or 1)
    if "still_water" in legendary and "body" not in c.equipment:        # monk wraps: the bare-skinned are hard to hurt
        legendary["stoneskin"] = legendary.get("stoneskin", 0) + legendary["still_water"]
    relics = []
    for slot, item in c.equipment.items():
        for k, v in (item.trait or {}).get("fight", {}).items():
            legendary[k] = legendary.get(k, 0) + (v or 1)
        if item.relic:
            r = item.relic
            relics.append(Move(id=f"relic_{slot}", name=r["name"], effect="relic", tier="moderate", reach="ranged", resource="stamina",
                               uses=r["uses"], text=r["text"], relic=r))
    from core.rules import MECHANICS
    conditional = []
    mech_names: dict[str, str] = {}
    for p in c.passives:
        m = MECHANICS.get(p.mechanic)
        if not m or m.kind != "combat":
            continue
        mech_names[p.mechanic] = p.name
        if p.when:
            conditional.append({"mechanic": p.mechanic, "when": p.when, "value": p.value})
            continue
        le = items.LEGENDARY.get(p.mechanic)
        if le and le.category and le.applies == "armor":
            wards[le.category] = wards.get(le.category, 0) + p.value
        elif le and le.category:
            slays[le.category] = slays.get(le.category, 0) + p.value
        else:
            legendary[p.mechanic] = legendary.get(p.mechanic, 0) + (p.value or 1)
    legacy = c.casting_attribute or next((x for x in c.primary_attributes if x in ("intelligence", "wisdom", "charisma")),
                                         "intelligence")
    moves = [Move(id=a.id, name=a.name, effect=a.effect.value, tier=a.tier.value, reach=a.reach.value,
                  resource=a.resource.value, cooldown=a.cooldown, movement=getattr(a, "movement", ""), heal_form=getattr(a, "heal_form", ""),
                  rider=a.rider, shape=a.shape, buff=a.buff, buff_stat=a.buff_stat, command=a.command, channel=a.channel,
                  attribute=a.attribute or (legacy if a.resource.value == "mana" else ""),
                  summon_form=a.summon_form, summon_name=a.summoned.name if a.summoned else "",
                  element=a.element, expressions=list(getattr(a, "expressions", []) or []), power=getattr(a, "power", 0),
                  cost_percent=getattr(a, "cost_percent", 0), cast_turns=getattr(a, "cast_turns", 0),
                  martial_form=getattr(a, "martial_form", ""), hits=getattr(a, "hits", 0), maneuver=getattr(a, "maneuver", ""),
                  spell_form=getattr(a, "spell_form", ""), rank=getattr(a, "rank", 0), line=getattr(a, "line", ""),
                  named=getattr(a, "named", False), cooldown_days=getattr(a, "cooldown_days", 0))
             for a in _loadout.prepared(c)] + relics      # only what is brought (engine/loadout.py)      # the planned element, never read from the words
    if weapon:
        b = items.base_of(weapon)
        wname, wdmg, wattrs, reach, dtype = weapon.name, items.value(weapon), b.attributes, b.reach, b.damage
        if weapon.legendary_effect == "longreach" and reach == "melee":
            reach = "extended"
    else:
        wname, wdmg, wattrs, reach, dtype = "fists", RULES["damage"]["unarmed"], ["strength"], "melee", "physical"
    from engine import needs
    return Fighter(
        id="player", name=c.name, side="player", level=c.level, attrs=attrs,
        hp=pools.current(c, "health"), max_hp=pools.maximum(c, "health"),
        stamina=pools.current(c, "stamina"), max_stamina=pools.maximum(c, "stamina"),
        mana=pools.current(c, "mana"), max_mana=pools.maximum(c, "mana"),
        weapon_name=wname, weapon_damage=wdmg, weapon_attrs=wattrs, reach=reach, damage_type=dtype,
        armor=armor, ward=ward + attrs["wisdom"] * RULES["mitigation"]["wisdom_ward"],
        evasion_penalty=penalty, bonuses=bonuses, moves=moves,
        armor_pierce=min(90, flags["armor_pierce"]), crit_resist=min(90, flags["crit_resist"]),
        offhand_spell=offhand_spell, adaptive=flags["adaptive"],
        legendary=legendary, slays=slays, wards=wards, conditional=conditional, mech_names=mech_names, breath=bool(getattr(c, 'orenna_breath', False)),
        weary=needs.penalties(c)["damage"],
        hold=(int((RULES.get("hold", {}).get("player") or {}).get(c.archetype.value, 1)) + int(legendary.get("shield_bearer", 0)))
        if reach != "ranged" else 0,
        pace=__import__("engine.battlefield", fromlist=["pace_of"]).pace_of(armor_weight=heaviest),
        armor_weight=raw_heaviest, wears_metal=wears_metal,
    )


def creature_attrs(profile: dict[str, int], level: int) -> dict[str, int]:
    budget = 100 + 5 * (max(1, level) - 1)
    total = sum(profile.values()) or 1
    return {a: max(1, round(budget * profile.get(a, 10) / total)) for a in ATTRIBUTES}


def calibration(level: int, key: str = "calibration") -> tuple[float, float]:
    """(health, damage) multipliers that keep a wild creature's strength in step with what gear gives a character at this level.
    Anchors are in data/rules/combat.yaml (creatures.calibration), measured with tools/tune.py; levels in between blend smoothly."""
    pts = RULES["creatures"].get(key)
    if not pts:
        return 1.0, 1.0
    if level <= pts[0][0]:
        return pts[0][1], pts[0][2]
    for (l0, h0, d0), (l1, h1, d1) in zip(pts, pts[1:]):
        if level <= l1:
            t = (level - l0) / (l1 - l0)
            return h0 + (h1 - h0) * t, d0 + (d1 - d0) * t
    return pts[-1][1], pts[-1][2]


_LIFT_CACHE: dict = {}


def _raw_power(creature, level: int, late) -> float:
    """Health times damage for a creature at a level before rank, pack and calibration: what it costs a character to beat it."""
    cr = RULES["creatures"]
    attrs = creature_attrs(creature.profile or {a: 10 for a in ATTRIBUTES}, level)
    hp = (10 + 5 * (level - 1) + 3 * attrs["constitution"] + 0.5 * attrs["strength"]) * cr["health_factor"] * cr["size_health"].get(creature.size, 1)
    over = max(0, level - late["start_level"]) * late.get("size_factor", {}).get(creature.size, 1.0) if late else 0
    hp *= 1 + (late["health"] * over if late else 0)
    dmg = cr["size_damage"].get(creature.size, 3) * growth(level) * (1 + (late["damage"] * over if late else 0))
    natural = cr["natural_armor"].get(getattr(creature, "category", ""), 1) * (1 + (late["armor"] * over if late else 0))
    hp *= 1 + natural / RULES["mitigation"]["armor_k"]       # armor makes every point of health take longer to chew through
    return hp * dmg


def power_lift(creature, level: int, late) -> tuple[float, float]:
    """(health, damage) multipliers that lift a creature weaker than the benchmark build of its level toward it. Stronger creatures are
    left as they are, so a dragon still outclasses a wolf of the same level. Rules: creatures.lift in combat.yaml."""
    lf = RULES["creatures"].get("lift")
    if not lf:
        return 1.0, 1.0
    key = (level, creature.id)
    if key not in _LIFT_CACHE:
        from types import SimpleNamespace
        ref = SimpleNamespace(profile={a: lf["benchmark_score"] for a in ATTRIBUTES}, size=lf["benchmark_size"], category=lf["benchmark_category"], id="ref")
        ratio = _raw_power(ref, level, late) / max(1.0, _raw_power(creature, level, late))
        s = min(lf["max"], max(1.0, ratio ** (lf["strength"] / 2)))
        t = min(1.0, max(0.0, (level - lf["from_level"]) / max(1, lf["full_level"] - lf["from_level"])))   # phased in with level
        s = 1 + (s - 1) * t
        _LIFT_CACHE[key] = (s, s)
    return _LIFT_CACHE[key]


def hold_of(reach: str, rank: str = "normal", size: str = "Medium", role: str = "") -> int:
    """How many enemies this fighter contains while holding a front row (data/rules/combat.yaml hold). The same law for everyone:
    ranged fighters hold nobody; rank and bulk hold more; a hired ally holds what their role says."""
    H = RULES.get("hold") or {}
    if reach == "ranged":
        return 0
    if role:
        return int((H.get("ally") or {}).get(role, 1))
    if rank == "boss":
        return int(H.get("boss", 3))
    if rank == "elite" or size in ("Huge", "Gargantuan"):
        return int(H.get("elite", 2))
    return int(H.get("normal", 1))


def fighter_from_creature(creature, level: int, rank: str, fid: str, name: str = "", start: str = "near", late: bool = True) -> Fighter:
    late_flag = late
    cr = RULES["creatures"]
    attrs = creature_attrs(creature.profile or {a: 10 for a in ATTRIBUTES}, level)
    rank_rule = cr["rank"][rank]
    es = cr.get("elite_scaling")
    if es and rank == "elite" and late_flag:         # elites keep getting stronger past a level, so they stay a threat to a strong character
        t = min(1.0, max(0.0, (level - es["from_level"]) / max(1, es["full_level"] - es["from_level"])))
        rank_rule = {"health": rank_rule["health"] * (1 + (es["health"] - 1) * t), "damage": rank_rule["damage"] * (1 + (es["damage"] - 1) * t)}
    raw_hp = 10 + 5 * (level - 1) + 3 * attrs["constitution"] + 0.5 * attrs["strength"]
    late = cr.get("late_growth") if late_flag else None
    over = max(0, level - late["start_level"]) * late.get("size_factor", {}).get(creature.size, 1.0) if late else 0
    raw_hp *= 1 + (late["health"] * over if late else 0)
    pack = cr["pack"]["health"] if creature.group[0] >= 2 and cr.get("pack") else 1.0
    cal_health, cal_damage = calibration(level) if late_flag else (1.0, 1.0)
    if late_flag and creature.group[0] >= 2:
        ph, pd = calibration(level, "pack_calibration")
        cal_health, cal_damage = cal_health * ph, cal_damage * pd
    even_h, even_d = (power_lift(creature, level, late) if late_flag else (1.0, 1.0))
    max_hp = max(1, round(raw_hp * cr["health_factor"] * cr["size_health"].get(creature.size, 1) * rank_rule["health"] * pack * cal_health * even_h))
    words = " ".join(creature.attacks).lower()
    ranged = any(w in words for w in cr["ranged_attack_words"])
    magical = creature.category in cr["magical_categories"]
    dmg = cr["size_damage"].get(creature.size, 3) * growth(level) * rank_rule["damage"] * (1 + (late["damage"] * over if late else 0))
    dmg *= cal_damage * even_d
    if creature.group[0] >= 2 and cr.get("pack"):
        dmg *= cr["pack"]["damage"]
    soft = cr.get("low_level_damage")
    if soft and level < soft["full_by_level"]:
        eased = 1.0 if level <= soft["soft_until_level"] else \
            (soft["full_by_level"] - level) / (soft["full_by_level"] - soft["soft_until_level"])
        dmg *= 1 - (1 - soft["factor"]) * eased
    attack = re.sub(r"\s*\([^)]*\)", "", next((a for a in creature.attacks), "strike")).strip() or "strike"   # (f419) no '(Fiend Form Only)
    fighter = Fighter(
        id=fid, name=name or creature.name.lower(), side="enemy", level=level, size=creature.size,
        category=creature.category, creature=creature.id, rank=rank, attrs=attrs, hp=max_hp, max_hp=max_hp,
        weapon_name=attack.lower(), weapon_damage=dmg, element=elements.of_creature(creature),
        weapon_attrs=["strength", "dexterity"], reach="ranged" if ranged else "melee",
        damage_type="magical" if magical and ranged else "physical",
        armor=cr["natural_armor"].get(creature.category, 1) * growth(level) * (1 + (late["armor"] * over if late else 0)),
        ward=(2 if magical else 0) * growth(level) + attrs["wisdom"] * RULES["mitigation"]["wisdom_ward"],
        starts_far=start == "far", hold=hold_of("ranged" if ranged else "melee", rank, creature.size),
        pace=__import__("engine.battlefield", fromlist=["pace_of"]).pace_of(creature.size, creature.category), temperament=creature.temperament,
    )
    if late_flag:
        from engine import behaviors
        behaviors.apply(fighter, creature)
    return fighter


def companion_fighter(shape, level: int, fid: str, name: str, gift: bool = False) -> Fighter:
    """A companion: a living creature, tamed - its kind's stats, strengthened by the companion rule as the player grows.
    (A summon is not a companion: engine/summons.py builds those from their caster.)"""
    f = fighter_from_creature(shape, level, "normal", fid, name, "near", late=False)
    g = RULES["creatures"].get("companion_gift")
    c = RULES["creatures"].get("companion")
    if gift and g:                          # an animal given as a reward: a helper, not a partner
        f.max_hp = f.hp = round(f.max_hp * g["health"])
        f.weapon_damage *= g["damage"]
    elif c:
        over = max(0, level - c["start_level"])
        f.max_hp = f.hp = round(f.max_hp * (c["health"] + c["late_health"] * over))
        f.weapon_damage *= c["damage"] + c["late_damage"] * over
    f.side = "ally"
    return f


# ---------- rules ----------

CATEGORY_TRIGGERS = {"undead": "against_undead", "fiend": "against_fiends", "fey": "against_fey", "beast": "against_beasts",
                     "swarm": "against_beasts", "celestial": "against_celestials", "lycanthrope": "against_lycanthropes"}


def active_triggers(f: Fighter, combat: Combat, target: Fighter | None = None, incoming_magic: bool = False) -> set[str]:
    t = {"always"} | set(combat.conditions)
    if target and target.category in CATEGORY_TRIGGERS:
        t.add(CATEGORY_TRIGGERS[target.category])
    if combat.round - f.move_round <= 1:
        t.add("after_moving")
    if f.attacked_since_turn:
        t.add("when_attacked")
    if f.defending:
        t.add("while_defending")
    if f.hp < f.max_hp / 3:
        t.add("at_low_health")
    if "elevated" in f.position_tags:
        t.add("while_elevated")
    if target and target.size in LARGE:
        t.add("against_large_foes")
    if incoming_magic:
        t.add("against_magic")
    if combat.round == 1:
        t.add("first_round_of_combat")
    if combat.round - f.kill_round <= 1:
        t.add("after_defeating_foe")
    if f.side == "player" and combat.allies():
        t.add("with_companion_present")
    return t


def bonus(f: Fighter, stat: str, triggers: set[str]) -> float:
    """Percentage (or chance points) from passives and percentage gear; flat gear amounts are in flat_bonus."""
    return sum(b.magnitude for b in f.bonuses if b.modifies == stat and b.trigger in triggers and not b.flat)


def flat_bonus(f: Fighter, stat: str, triggers: set[str]) -> float:
    return sum(b.magnitude for b in f.bonuses if b.modifies == stat and b.trigger in triggers and b.flat)


def is_companion(f: Fighter) -> bool:
    """A companion: a tamed, living creature (not a summon, a hired party member or a risen thrall)."""
    return f.side == "ally" and not f.ally_role and not f.id.startswith("thrall") and not f.summon_form


def _still(f: Fighter) -> bool:
    """A summon that neither moves nor strikes (a totem, a decoy)."""
    if not f.summon_form:
        return False
    from engine import summons
    return bool(summons.FORMS.get(f.summon_form, {}).get("still"))


def fights_for_you(f: Fighter) -> bool:
    """One of the player's own: a companion or a summon (the things 'your companions' perks and commands reach) - not a hired party
    member or a risen thrall."""
    return f.side == "ally" and not f.ally_role and not f.id.startswith("thrall")


def companion_boost(combat: Combat, stat: str) -> float:
    """Percentage points the player's gear and passives add to their companions' damage or durability."""
    p = combat.player
    return bonus(p, stat, active_triggers(p, combat)) if p else 0


def mechanics(f: Fighter, combat: Combat | None, other: Fighter | None = None) -> dict[str, float]:
    """Every mechanic active for this fighter right now: legendary gear, passives, and conditional passives."""
    out = dict(f.legendary)
    if f.buffs:
        from engine import relics
        for k, v in relics.buff_mechanics(f).items():
            out[k] = out.get(k, 0) + v
    if f.conditional and combat is not None:
        active = active_triggers(f, combat, other)
        for c in f.conditional:
            if c["when"] in active:
                out[c["mechanic"]] = out.get(c["mechanic"], 0) + (c["value"] or 1)
    return out


def category_bonus(f: Fighter, active: dict[str, float], target: Fighter | None, kind: str) -> float:
    """Slayer (kind='slay') or ward (kind='ward') percentage against the target's creature category."""
    if not target:
        return 0
    total = (f.slays if kind == "slay" else f.wards).get(target.category, 0)
    for mid, v in active.items():
        le = items.LEGENDARY.get(mid)
        if le and le.category and le.category == target.category and (le.applies == "armor") == (kind == "ward"):
            total += v
    return total


def status_mod(f: Fighter, key: str) -> float:
    return sum(RULES["statuses"].get(s, {}).get(key, 0) for s in f.statuses)


def hit_parts(att: Fighter, dfn: Fighter, combat: Combat) -> tuple[float, list[list]]:
    """The chance to hit and every step that makes it: [label, points] pairs, starting from the base for an equal match-up."""
    h = RULES["hit"]
    a = att.best_attr(att.weapon_attrs)
    d = dfn.attrs.get("dexterity", 10)
    steps = [["equal match-up", h["base"]], [f"{'accuracy' if a >= d else 'evasion'} edge ({a} against {d})", h["spread"] * (a - d) / max(1, a + d)]]
    acc = bonus(att, "accuracy", active_triggers(att, combat, dfn))
    if acc:
        steps.append(["accuracy from passives and gear", acc])
    ev = bonus(dfn, "evasion", active_triggers(dfn, combat, att))
    if ev:
        steps.append(["their evasion", -ev])
    slip = mechanics(dfn, combat, att).get("evasion", 0)
    if slip:
        steps.append(["slipping away", -slip])
    if dfn.evasion_penalty:
        steps.append(["their footing", -dfn.evasion_penalty])
    st = status_mod(att, "accuracy") - status_mod(dfn, "evasion")
    if st:
        steps.append(["conditions", st])
    if "elevated" in att.position_tags and "elevated" not in dfn.position_tags:
        steps.append(["high ground", RULES["elevated_accuracy"]])
    if att.reach == "ranged" and att.damage_type == "physical" and att.engaged_with:
        steps.append(["point-blank (a ranged weapon with a foe on top of you)", -h.get("point_blank", 0)])
    if combat is not None:
        from engine import battlefield as bfm
        steps += [st for st in bfm.hit_modifiers(combat, att, dfn) if st[0] != "high ground"]
    chance = sum(v for _, v in steps)
    return max(h["min"], min(h["max"], chance)), [[n, round(v, 1)] for n, v in steps if abs(v) >= 0.05]


def hit_chance(att: Fighter, dfn: Fighter, combat: Combat) -> float:
    return hit_parts(att, dfn, combat)[0]


def roll_attack(att: Fighter, dfn: Fighter, combat: Combat, rng: random.Random, trace: dict | None = None) -> tuple[str, float]:
    """Returns (outcome, chance). outcome: miss | graze | hit | crit."""
    chance, hit_steps = hit_parts(att, dfn, combat)
    if is_open(dfn, combat.round):
        chance = min(RULES["hit"]["max"], chance + RULES["opening"]["accuracy"])
        hit_steps = hit_steps + [["they are open", RULES["opening"]["accuracy"]]]
    r = rng.uniform(0, 100)                         # high is good: a hit needs a roll of (100 - chance) or more, a crit lands in the top of the range
    dm = mechanics(dfn, combat, att)
    if "blur" in dm:
        r = min(r, rng.uniform(0, 100))             # Blur: the attack is rolled twice and the worse roll is kept (f244)
        hit_steps = hit_steps + [["rolled twice, the worse kept (Blur)", 0]]
    c = RULES["crit"]
    dex_a, dex_d = att.attrs.get("dexterity", 10), dfn.attrs.get("dexterity", 10)
    crit = c["base"] + c["dexterity_spread"] * max(0, dex_a - dex_d) / max(1, dex_a + dex_d)
    crit += mechanics(att, combat, dfn).get("killer_instinct", 0)
    crit += mechanics(att, combat, dfn).get("precision", 0)             # Precision (f235)
    crit += bonus(att, "crit_chance", {"always"})
    if is_open(dfn, combat.round):
        crit += RULES["opening"]["crit"]
    if "elevated" in att.position_tags:
        crit += mechanics(att, combat, dfn).get("vantage_fighter", 0)
    from engine import combat_perks
    crit = combat_perks.crit_chance(combat, att, crit)
    crit = min(c.get("max", 50) * (combat_perks.crit_cap_mult(combat, att)), crit)
    crit *= 1 - dfn.crit_resist / 100
    if "brittle" in dfn.statuses:
        crit *= 2                                       # Brittle (f268): twice as likely to be struck critically
    if "humbled" in att.statuses or att.counters.get("tarnished", 0) > 0:
        crit = 0                                        # Humbled, Tarnish (f268): no critical hits
    if trace is not None:
        trace.update(hit_steps=hit_steps, chance=round(chance, 1), roll=round(r, 1), need=round(100 - chance, 1), crit=round(crit, 1), crit_need=round(100 - crit, 1))
    if r < 100 - chance:
        return "miss", chance
    if r >= 100 - crit:
        return "crit", chance
    if r < 100 - chance + RULES["hit"]["graze_band"]:
        return "graze", chance
    return "hit", chance


def crit_profile(f: Fighter) -> dict:
    """The fighter's crit numbers for display: chance against an equal-Dexterity target, the most Dexterity can add, and the damage multiplier."""
    c = RULES["crit"]
    plain = c["base"] + mechanics(f, None, None).get("killer_instinct", 0) + bonus(f, "crit_chance", {"always"})
    top = c.get("max", 50)
    return {"chance": min(top, plain), "most": min(top, plain + c["dexterity_spread"]), "multiplier": crit_multiplier(f), "cap": top}


def crit_multiplier(att: Fighter) -> float:
    """What a critical hit multiplies damage by: the base, plus the flat percentage points gear adds."""
    return RULES["crit"]["multiplier"] + bonus(att, "crit_damage", {"always"}) / 100


def raw_damage(att: Fighter, multiplier: float, triggers: set[str], rng: random.Random, steady: bool = False,
               trace: dict | None = None) -> float:
    d = RULES["damage"]
    spell = att.spell_kind == "spell"                    # a spell: (spell base + spell power) x its casting attribute, no flat attribute bonus
    flat = 0.0 if spell else flat_bonus(att, "damage", triggers)
    attr_bonus = 0.0 if spell else att.best_attr(att.weapon_attrs) * d["attribute_bonus"]
    base = att.weapon_damage + attr_bonus + flat
    variance = 1.0 if steady else rng.uniform(1 - d["variance"], 1 + d["variance"])
    magic = att.spell_mult if spell else 1.0
    pct = bonus(att, "damage", triggers)
    if trace is not None:
        if att.spell_kind:
            trace.update(kind=att.spell_kind, parts=[[n, round(v, 1)] for n, v in att.spell_parts])
        trace.update(weapon=round(att.weapon_damage, 1), attr=att.best_attr(att.weapon_attrs), attr_bonus=round(attr_bonus, 1), spell_mult=round(att.spell_mult, 3),
                     flat=round(flat, 1), base=round(base, 1), pct=round(pct, 1), variance=round(variance, 3), magic=round(magic, 3),
                     multiplier=round(multiplier, 3), total=round(base * multiplier * (1 + pct / 100) * variance * magic, 2))
    return base * multiplier * (1 + pct / 100) * variance * magic


def mitigate(dfn: Fighter, amount: float, damage_type: str, attacker_level: int, combat: Combat,
             attacker: Fighter | None = None, trace: dict | None = None) -> tuple[float, float]:
    """Returns (damage taken, damage absorbed)."""
    m = RULES["mitigation"]
    if attacker and attacker.adaptive:
        damage_type = "magical" if dfn.ward < dfn.armor else "physical"
    protection = dfn.ward if damage_type == "magical" else dfn.armor
    base_prot, prot_steps = protection, []
    if dfn.buffs:
        bw = mechanics(dfn, combat).get("bulwark_ward" if damage_type == "magical" else "bulwark_armor", 0)
        if bw:
            floor = AT.T["bulwark_floor"] * m["armor_k"] * growth(attacker_level)
            protection = max(protection, floor) * (1 + bw / 100)
            prot_steps.append(["Bulwark stance", f"+{bw:g}%"])
    if status_mod(dfn, "protection"):
        prot_steps.append(["Exposed", f"{status_mod(dfn, 'protection'):+g}%"])
    protection *= max(0.1, 1 + status_mod(dfn, "protection") / 100)        # Exposing
    if dfn.sundered and damage_type != "magical":
        prot_steps.append(["Sundered", f"-{dfn.sundered:g}%"])
        protection *= 1 - dfn.sundered / 100                                # armor broken by Sunder (engine/martial.py)
    if dfn.corroded:
        prot_steps.append(["Corroded", f"-{dfn.corroded:g}%"])
        protection *= 1 - dfn.corroded / 100                                # acid has eaten into armor and ward (engine/spellcraft.py)
    am = mechanics(attacker, combat, dfn) if attacker else {}
    if attacker is not None:
        from engine import spellcraft as _sc
        if damage_type == "magical" and _sc.scorching(attacker):      # Scorch (f266): straight through the ward
            prot_steps.append(["Scorch", "-100%"])
            protection = 0.0
        if _sc.etching(attacker):                          # Etch (f268): half of it eaten through
            prot_steps.append(["Etch", "-50%"])
            protection *= 0.5
    if damage_type == "magical" and "wardbreaker" in am:
        prot_steps.append(["Wardbreaking", f"-{min(90, am['wardbreaker']):g}%"])
        protection *= 1 - min(90, am["wardbreaker"]) / 100
    pierce = (attacker.armor_pierce if attacker else 0) + am.get("piercing", 0)
    if pierce and damage_type != "magical":
        prot_steps.append(["Piercing / Sundering", f"-{min(90, pierce):g}%"])
        protection *= 1 - min(90, pierce) / 100
    reduction = min(m["cap"], 100 * protection / max(0.01, protection + m["armor_k"] * growth(attacker_level)))
    after = amount * (1 - reduction / 100)
    triggers = active_triggers(dfn, combat, incoming_magic=damage_type == "magical")
    before = after
    cuts = [["armour" if damage_type != "magical" else "ward", amount - after]]
    def_pct, def_flat = bonus(dfn, "defense", triggers), flat_bonus(dfn, "defense", triggers)
    after *= max(0.05, 1 - def_pct / 100)
    cuts.append(["gear defence", before - after])
    step = after
    after = max(before * 0.1, after - def_flat)
    cuts.append(["flat defence", step - after])
    step = after
    from engine import spellcraft as _scb
    guarded = not (attacker is not None and _scb.burning_through(attacker))      # Burn Through (f268): the guard counts for nothing
    if dfn.defending and guarded:
        after *= 1 - dfn.defending / 100
    stance = mechanics(dfn, combat, attacker).get("stance", 0)
    if stance and guarded:
        after *= 1 - min(60, stance) / 100
    cuts.append(["guarding", step - after])
    if trace is not None:
        trace.update(kind=damage_type, protection=round(protection, 1), base_protection=round(base_prot, 1), prot_steps=prot_steps,
                     k=round(m["armor_k"] * growth(attacker_level), 1), who=dfn.name, reduction=round(reduction, 1),
                     raw_reduction=round(100 * protection / max(0.01, protection + m["armor_k"] * growth(attacker_level)), 1), defense_pct=round(def_pct, 1),
                     defense_flat=round(def_flat, 1), defending=round(dfn.defending, 1), before=round(amount, 2), after=round(after, 2),
                     cuts=[[n, round(v, 1)] for n, v in cuts if v >= 0.05])
    return after, amount - after


def is_open(f: Fighter, round_now: int) -> bool:
    """Left open (a whiffed or interrupted big blow): attacks against them land easier for a round."""
    return f.counters.get("open_until", -9) >= round_now


def leave_open(combat: Combat, f: Fighter) -> None:
    f.counters["open_until"] = combat.round + int(RULES["opening"].get("rounds", 1))


def add_status(combat: Combat, f: Fighter, status: str, rounds: int, source: Fighter | None = None) -> bool:
    """Apply a status unless a legendary effect prevents it. Returns True if it took hold. The source, when the caller knows it, is
    whoever did it: the perks that change how an affliction lands (engine/combat_perks.py) belong to one side or the other."""
    fm = mechanics(f, combat)
    if "unyielding" in fm and status in ("stunned", "prone"):
        combat.log.append(f"{f.name} stands firm (Unyielding)")
        tell(combat, f"{who(f)} {vb(f, 'stand', 'stands')} firm, unshaken (Unyielding)")
        return False
    if "earthshaker" in fm and status == "prone":
        return False
    if "stoneform" in fm and status in ("stunned", "prone", "grappled"):
        tell(combat, f"{who(f)} {vb(f, 'stand', 'stands')} like stone, unmoved (Stoneform)")
        return False
    if "iron_will" in fm and status in ("stunned", "prone", "slowed", "frightened", "blinded") \
            and f.counters.get("shrugged", 0) < fm["iron_will"]:
        f.counters["shrugged"] = f.counters.get("shrugged", 0) + 1
        combat.log.append(f"{f.name} shrugs it off (Iron Will)")
        tell(combat, f"{who(f)} {vb(f, 'shrug', 'shrugs')} it off as if it were nothing, and the effort sharpens {whose(f)} resolve (Iron Will)")
        return False
    element = ELEMENT_STATUS.get(status) or ((source.hit_element or source.element) if source is not None
                                             and status in ("slowed", "blinded", "bleeding", "prone", "petrified") else "")
    if element and warded(f, element):
        tell(combat, f"{who(f)}, an archon of {element}, {vb(f, 'shrug', 'shrugs')} it off (Attunement)")
        return False
    if element and attuned(source, element) and status in ("slowed", "withered", "unraveled", "illuminated", "blinded"):
        rounds += 1                                         # an archon's chills, witherings and lights last longer (f246)
    if "sanctified" in fm and status in ("bleeding", "frightened"):
        combat.log.append(f"{f.name} is untouched by it (Sanctified)")
        tell(combat, f"a holy calm keeps {who(f)} untouched (Sanctified)")
        return False
    if f.boss:
        from engine import bosses
        if bosses.resisted(combat, f, status):
            return False
    from engine import combat_perks
    landed = combat_perks.on_status(combat, f, status, rounds, source)
    if landed is None:
        return False
    status, rounds = landed
    if status == "bleeding":
        from engine import afflictions
        if afflictions.bloodless(f):
            return False                                  # nothing to bleed
    if status in ("burning", "poisoned", "bleeding"):
        from engine import afflictions
        rounds = afflictions.apply(combat, f, status, rounds, source)    # ignite, poison and bleeding: one law for every source
    f.statuses[status] = rounds
    if source is not None:
        f.status_from[status] = source.id
    if status == "bleeding" and source is not None and source.side != f.side and "crippling_wounds" in mechanics(source, combat) \
            and f.alive and add_status(combat, f, "slowed", rounds, source):
        f.counters["crippled"] = 1                          # Crippling Wounds (f312): slowed for as long as your wound stays open
        tell(combat, f"the wound drags at {who(f)}, and {vb(f, 'you slow', 'it slows')} (Crippling Wounds)")
    if status in ("stunned", "prone") and f.winding:
        f.winding = {}
        leave_open(combat, f)
        combat.log.append(f"{f.name}'s wound-up blow is interrupted")
        tell(combat, f"the blow {who(f)} was winding up never falls - {who(f)} {vb(f, 'are', 'is')} left open")
    return True


def element_factor(dfn: Fighter, element: str) -> float:
    """How much of an element gets through the target's resistance to it alone (gear, nature, kind); above 1 is a weakness. This is
    all a burn or a poisoning has to get through (engine/afflictions.py)."""
    if not element:
        return 1.0
    pct = sum(b.magnitude for b in dfn.bonuses if b.trigger == "always" and b.modifies in (f"{element}_resistance", "all_elemental_resistance"))
    if dfn.element == element:
        pct += elements.R.get("native_resist", 0)
    pct += (elements.R.get("category_resist") or {}).get(dfn.category, {}).get(element, 0)
    pct += warded(dfn, element)                             # Attunement (f246)
    factor = 1 - max(-100, min(elements.CAP, pct)) / 100
    if element == "lightning" and "conductive" in dfn.statuses:
        from engine import spellcraft as _sc
        factor *= 1 + _sc.num(_sc.EXPR["conductor"], "light", "pct", 25) / 100      # Conductor (f268)
    return factor


ELEMENT_STATUS = {"burning": "fire", "poisoned": "poison", "withered": "necrotic", "unraveled": "necrotic", "illuminated": "radiant"}


def warded(f: Fighter, element: str) -> float:
    """How much an Attunement on this fighter resists this element (0 if it is not that element's archon)."""
    if not element:
        return 0
    for b in (f.buffs or {}).values():
        if b.get("kind") == "attunement" and b.get("element") == element:
            return float(b.get("mech", {}).get("element_ward", 0))
    return 0


def attuned(f: Fighter | None, element: str) -> bool:
    """Whether this fighter is an archon of this element right now (Attunement, f246): its own effects of it are stronger."""
    return f is not None and bool(element) and any(b.get("kind") == "attunement" and b.get("element") == element
                                                   for b in (f.buffs or {}).values())


ATTUNE = {"fire": 1.5, "lightning": 1.5, "acid": 1.5, "drain": 1.5, "nature": 1.5}     # how much stronger an archon's own effects are, where it is a size      # below zero is a weakness: plants to fire, the undead to radiant


def resist_factor(dfn: Fighter, damage_type: str, element: str) -> float:
    """How much of an attack gets through the target's resistances: physical or magical, then the element it carries."""
    kind = "physical" if damage_type == "physical" else "magical"
    pct = sum(b.magnitude for b in dfn.bonuses if b.modifies == f"{kind}_resistance" and b.trigger == "always")
    return (1 - max(0, min(elements.CAP, pct)) / 100) * element_factor(dfn, element)


def restore(combat: Combat | None, f: Fighter, amount: float, source: Fighter | None = None, rng: random.Random | None = None) -> float:
    """Every bit of health a fighter gets back in a fight comes through here (f263). Unraveled (necrotic), healing turns on its
    owner: it deals that much damage instead. Returns the health actually gained (negative when it hurt)."""
    if amount <= 0 or not f.alive:
        return 0.0
    thief = combat.get(f.counters.get("life_theft", "")) if combat is not None and f.counters.get("life_theft") else None
    if thief is not None and thief.alive and thief is not f:
        f.counters.pop("life_theft", None)                 # Life Theft (f268): this healing goes to the thief instead
        tell(combat, f"the healing meant for {who(f)} is drawn away into {who(thief)} (Life Theft)")
        return restore(combat, thief, amount, source, rng)
    if "unraveled" in f.statuses and combat is not None:
        dealt = take_damage(combat, f, amount, source, rng or random.Random(), "magical")
        combat.log.append(f"{f.name}'s healing turns on it: {dealt} damage (Unraveled)")
        tell(combat, f"the healing curdles in {who(f)} and tears at {vb(f, 'you', 'it')} instead ({dealt})")
        return -float(dealt)
    before = f.hp
    f.hp = min(f.max_hp, f.hp + amount)
    return f.hp - before


def take_damage(combat: Combat, dfn: Fighter, amount: float, source: Fighter | None, rng: random.Random,
                damage_type: str = "physical", rec: dict | None = None) -> int:
    """Apply final damage to a fighter, with defensive legendary effects. Returns damage actually dealt. With a record, every effect that
    changed the figure is written into it by the name of the passive or gear that caused it."""
    if "petrified" in dfn.statuses:                     # Petrify (f266): stone cannot be hurt
        return 0
    L = mechanics(dfn, combat, source)
    named = {"blood_pact": "Blood Pact", "hardening": "Hardening", "aegis": "Aegis", "last_stand": "Last Stand", "stoneskin": "Stoneskin",
             "plating": "Plating", "spellward": "Spellward", "unbroken": "Unbroken", "guardian": "Guardian", "mana_shield": "Mana shield"}

    def label(mid: str) -> str:
        le = items.LEGENDARY.get(mid)
        return dfn.mech_names.get(mid) or (le.name if le else named.get(mid, mid.replace("_", " ").title()))

    def step(before: float, mid_or_name: str, named_by_id: bool = True) -> None:
        if rec is not None and abs(before - amount) >= 0.5:
            rec["extras"].append([label(mid_or_name) if named_by_id else mid_or_name, f"{round(amount - before):+d}"])
            rec["named_total"] = rec.get("named_total", 0) + (round(amount) - round(before))
    from engine import combat_perks
    was = amount
    amount = combat_perks.before_damage(combat, dfn, amount, source, rng, damage_type)
    step(was, "Shared or capped by a perk", False)
    if not (source and source.legendary.get("penetrating")):               # Penetrating ignores resistances
        was = amount
        amount *= resist_factor(dfn, damage_type, (source.hit_element or source.element) if source else "")
        step(was, "Resistance", False)
    if "blood_pact" in L:
        was = amount
        amount *= 1 + L["blood_pact"] / 200
        step(was, "blood_pact")
    ward = category_bonus(dfn, L, source, "ward")
    if ward:
        was = amount
        amount *= 1 - min(90, ward) / 100
        step(was, f"Ward against {source.category}" if source and source.category else "Ward", False)
    if "hardening" in L:
        was = amount
        amount *= 1 - L["hardening"] * min(5, dfn.hardening_stacks) / 100
        dfn.hardening_stacks += 1
        step(was, "hardening")
    if "aegis" in L and dfn.aegis_round != combat.round:
        dfn.aegis_round = combat.round
        was = amount
        amount *= 1 - L["aegis"] / 100
        step(was, "aegis")
    if "last_stand" in L and dfn.hp < dfn.max_hp / 4:
        was = amount
        amount *= 0.8
        step(was, "last_stand")
    if "stoneskin" in L:
        was = amount
        amount *= 1 - min(90, L["stoneskin"]) / 100
        step(was, "stoneskin")
    if "plating" in L and damage_type == "physical":
        was = amount
        amount *= 1 - min(90, L["plating"]) / 100
        step(was, "plating")
    if "spellward" in L and damage_type == "magical":
        was = amount
        amount *= 1 - min(90, L["spellward"]) / 100
        step(was, "spellward")
    if "unbroken" in L:
        was = amount
        amount = min(amount, dfn.max_hp * L["unbroken"] / 100)
        step(was, "unbroken")
    if dfn.side == "ally":
        guard = mechanics(combat.player, combat).get("guardian", 0)
        was = amount
        amount *= 1 - min(90, guard) / 100
        step(was, "guardian")
        if fights_for_you(dfn):
            was = amount
            amount /= 1 + max(0, companion_boost(combat, "companion_durability")) / 100
            step(was, "Companion durability", False)
    from engine import spellcraft as _scs
    if dfn.shield > 0 and amount > 0 and source is not None and _scs.seeping(source):
        step(amount, "Seep: under the barrier", False)     # Seep (f268): straight past it
    elif dfn.shield > 0 and amount > 0:
        soaked = min(dfn.shield, amount)
        dfn.shield -= soaked
        was = amount
        amount -= soaked
        step(was, "Barrier", False)
        tell(combat, f"{whose(dfn)} barrier takes the blow" + (" and shatters" if dfn.shield <= 0 else ""))
    if "stoneform" in L and amount > 0 and damage_type == "physical":
        was = amount
        amount *= 1 - min(90, L["stoneform"]) / 100          # Stoneform: blows that would cut or crush meet stone
        step(was, "Stoneform", False)
    if "mana_veil" in L and amount > 0 and dfn.mana > 0:
        absorbed = min(dfn.mana, amount * min(90, L["mana_veil"]) / 100)    # Mana Shield (f235): point for point, until the mana is gone
        dfn.mana -= absorbed
        was = amount
        amount -= absorbed
        step(was, "Mana Shield", False)
        if dfn.mana <= 0:
            for k, b in list(dfn.buffs.items()):
                if b.get("kind") == "manashield":
                    dfn.buffs.pop(k)
            tell(combat, f"{whose(dfn)} mana runs dry and the shield breaks")
    if "mana_shield" in L and amount > 0 and dfn.mana > 1:
        absorbed = min(dfn.mana / 2, amount * min(90, L["mana_shield"]) / 100)
        dfn.mana -= absorbed * 2
        was = amount
        amount -= absorbed
        step(was, "mana_shield")
    if amount <= 0:
        return 0
    if "ward_conversion" in L and damage_type == "magical" and dfn.max_mana:
        dfn.mana = min(dfn.max_mana, dfn.mana + amount * L["ward_conversion"] / 100)
    dealt = max(1, round(amount))
    if combat.duel and dealt >= dfn.hp:
        dfn.hp = 1
        combat.over = "defeat" if dfn.side == "player" else "victory"
        combat.log.append(f"{dfn.name} is beaten")
        tell(combat, f"the blow that would have ended {who(dfn)} is pulled short, and the duel is decided" if dfn.side != "player" else
             "the blow that would have ended you is pulled short, and the duel is decided")
        return dealt
    if dealt >= dfn.hp and fights_for_you(dfn) and "lifeline" in mechanics(combat.player, combat) and not dfn.counters.get("lifeline"):
        dfn.counters["lifeline"] = 1
        dfn.hp = 1
        combat.log.append(f"{dfn.name} should have fallen - the bond holds it to life (Lifeline)")
        tell(combat, f"the blow should have ended {who(dfn)}, but the bond with its master will not let it fall (Lifeline)")
        return dealt
    if dealt >= dfn.hp and dfn.tether:
        dfn.hp = max(1, round(dfn.max_hp * dfn.tether / 100))
        dfn.tether = 0
        combat.log.append(f"{dfn.name} should have fallen - the Soul Tether holds it to life")
        tell(combat, f"the blow should have ended {who(dfn)}, but a thread of the master's will draws it back from the brink (Soul Tether)")
        return dealt
    if dfn.boss and dealt >= dfn.hp:
        from engine import bosses
        if bosses.last_stand(combat, dfn):
            return dealt
    if dealt >= dfn.hp and dfn.breath:
        dfn.breath = False
        dfn.hp, dfn.mana = dfn.max_hp, dfn.max_mana
        combat.log.append(f"{dfn.name} should have fallen - Orenna's Last Breath restores them in full")
        tell(combat, f"the blow should have killed {who(dfn)} - but a thin, tired warmth catches them, and {vb(dfn, 'you rise', 'they rise')} whole, health and strength restored (Orenna's Last Breath, now spent)")
        return dealt
    if dealt >= dfn.hp and dfn.side == "player" and combat.mentor:
        combat.mentor_saved += 1
        dfn.hp = 1
        tell(combat, "the blow should have ended you, but a hand pulls you aside at the last instant")
        return dealt
    if dealt >= dfn.hp and "deathless" in L:
        dfn.hp = 1
        tell(combat, f"the blow should have ended {who(dfn)}, but {vb(dfn, 'you are', 'it is')} held on the threshold and will not fall")
        return dealt
    if dealt >= dfn.hp and "deathward" in L and not dfn.deathward_used:
        dfn.deathward_used = True
        dfn.hp = 1 + round(dfn.max_hp * L["deathward"] / 100)
        combat.log.append(f"{dfn.name} should have fallen - Deathward holds them to life")
        tell(combat, f"the blow should have killed {who(dfn)} - but a power older than death refuses to let go (Deathward)")
        return dealt
    if dfn.yields_at and dealt >= dfn.hp:
        dealt = max(0, round(dfn.hp) - 1)
    dfn.hp = max(0, dfn.hp - dealt)
    if dealt > 0 and source is not None and source.side != dfn.side and source is not dfn:
        dfn.last_hurt_by = source.id
    if dfn.summon_form and not dfn.alive:
        from engine import summons
        summons.on_fall(combat, dfn, rng)              # unmade: the volatile kind bursts; a Bound summon is gone until the fight ends
    combat_perks.after_damage(combat, dfn, dealt, source)
    from engine import healing as _heal
    _heal.after_damage(combat, dfn, dealt, source)
    from engine import battlefield as bf
    if not dfn.alive:
        bf.release(combat, dfn)                       # the fallen hold nobody, and nobody is tied up with them
        if dfn.side == "enemy":
            from engine import behaviors as _bh
            _bh.morale_on_death(combat, dfn, rng)
        elif dfn.side == "ally":
            p_ = combat.player
            av = mechanics(p_, combat).get("avenger", 0)
            if av and not p_.counters.get("avenger_used"):
                p_.counters["avenger_used"] = 1
                p_.counters["avenging"] = 1
                tell(combat, f"something goes cold and certain in {who(p_)}: the next blow will not miss (Avenger)")
    if dfn.yields_at and dfn.alive and not dfn.fled and dfn.hp <= dfn.max_hp * dfn.yields_at:
        dfn.fled = True
        bf.release(combat, dfn)
        tell(combat, dfn.yield_text or f"{who(dfn)} breaks off and is gone")
    if dfn.boss:
        from engine import bosses
        bosses.after_damage(combat, dfn)
    if "second_wind" in L and not dfn.second_wind_used and 0 < dfn.hp < dfn.max_hp / 4:
        dfn.second_wind_used = True
        heal = round(dfn.max_hp * L["second_wind"] / 100)
        restore(combat, dfn, heal)
        combat.log.append(f"{dfn.name} finds a second wind: +{heal}")
        tell(combat, f"with the end close, {who(dfn)} {vb(dfn, 'find', 'finds')} a second wind and {vb(dfn, 'rise', 'rises')} again")
    for effect, applies in (("retribution", True), ("spellmirror", damage_type == "magical")):
        if source and effect in L and applies and source.alive:
            back = max(1, round(dealt * L[effect] / 100))
            source.hp = max(0, source.hp - back)
            combat.log.append(f"{effect.capitalize()} returns {back} damage to {source.name}")
            tell(combat, f"the force rebounds into {who(source)} ({effect.capitalize()})")
            if not source.alive:
                combat.log.append(f"{source.name} falls")
                tell(combat, f"{who(source)} {vb(source, 'collapse', 'collapses')}, undone by {vb(source, 'your', 'its')} own violence")
    return dealt


def apply_damage(combat: Combat, att: Fighter, dfn: Fighter, multiplier: float, label: str, rng: random.Random,
                 can_cleave: bool = True, can_riposte: bool = True, how: str = "", can_flurry: bool = True,
                 reliable: bool = False) -> bool:
    """Attack roll, damage and mitigation. Returns True if it landed. A defender with a readied counter meets the first engaged blow:
    it lands weakened, and the defender strikes back (engine/martial.py)."""
    from engine import martial
    meet = martial.countering(att, dfn)
    if meet:
        multiplier *= martial.FORMS["counter"]["weaken"]
    landed = _apply_damage(combat, att, dfn, multiplier, label, rng, can_cleave, can_riposte, how, can_flurry, reliable)
    if meet:
        martial.strike_back(combat, dfn, att, rng)
    return landed


def _apply_damage(combat: Combat, att: Fighter, dfn: Fighter, multiplier: float, label: str, rng: random.Random,
                  can_cleave: bool = True, can_riposte: bool = True, how: str = "", can_flurry: bool = True,
                  reliable: bool = False) -> bool:
    how = how or weapon_phrase(att)
    from engine import spellcraft as _sc
    if can_cleave and att.alive:
        _sc.on_attack(combat, att)                          # Caustic Drip (f268): the acid bites as the arm swings
        if not att.alive:
            return False                                    # ...and the swing never lands: the acid finished them first
    rec = new_hit(combat, att, dfn, label)
    open_wound = "bleeding" in dfn.statuses             # a wound opened by this very blow is not torn by it (engine/afflictions.py)
    if "concealed" in att.position_tags:
        att.counters["struck_hidden"] = 1               # striking from hiding gives you away, once the action is done
    A, D = mechanics(att, combat, dfn), mechanics(dfn, combat, att)
    if att.counters.get("blessed"):
        from engine import techniques
        multiplier *= techniques.blessed(att, combat)              # (f396) a hired priest's Blessing
    if fights_for_you(att):
        multiplier *= 1 + max(0, companion_boost(combat, "companion_damage")) / 100
        if "press" in A:
            multiplier *= 1 + A["press"] / 100
    dfn.attacked_since_turn = True
    if att.weary:
        multiplier *= 1 + att.weary / 100
    if "phantom" in D and not dfn.counters.get("phantom_used") and att.side != dfn.side:
        dfn.counters["phantom_used"] = 1
        combat.log.append(f"{att.name} {label} {dfn.name}: passes through them like smoke (Phantom)")
        if rec is not None:
            rec.update(outcome="phase", note="Phantom: the blow passes through")
            rec["figure"] = figure(rec)
        tell(combat, f"{who(att)} {vb(att, 'strike', 'strikes')} at {who(dfn)} {how}, but the blow passes through {vb(dfn, 'you', 'them')} like smoke (Phantom)", rec)
        dfn.windwalker_ready = "windwalker" in D
        if "flowing_step" in D:
            dfn.counters["flow"] = min(3, dfn.counters.get("flow", 0) + 1)
        return False
    roll_info: dict = {}
    outcome, chance = roll_attack(att, dfn, combat, rng, trace=roll_info)
    if rec is not None:
        rec.update(chance=roll_info.get("chance", round(chance, 1)), roll=roll_info.get("roll", 0.0), need=roll_info.get("need", 0.0),
                   crit=roll_info.get("crit", 0.0), crit_need=roll_info.get("crit_need", 100.0))
    from engine import combat_perks
    outcome = combat_perks.on_outcome(combat, att, dfn, outcome, rec)
    if "first_blood" in A and not att.first_blood_used:
        att.first_blood_used = True
        outcome = "crit"
        if rec is not None:
            rec["note"] = "First Blood: the first strike is always critical"
    if att.counters.get("avenging") and att.side == "player" and att.side != dfn.side:
        att.counters.pop("avenging", None)
        outcome = "crit" if outcome == "crit" else "hit"
        multiplier *= 1 + mechanics(att, combat).get("avenger", 50) / 100
        if rec is not None:
            rec["note"] = "Avenger: this one cannot miss"
    if "bladeward" in D and outcome != "miss" and att.reach in ("melee", "extended") and att.side != dfn.side \
            and dfn.counters.get("bladeward_round") != combat.round:
        dfn.counters["bladeward_round"] = combat.round
        multiplier *= 1 - D["bladeward"] / 100                  # Bladeward: the first blade each round is turned (f244)
        tell(combat, f"the ward around {who(dfn)} turns the worst of the blade (Bladeward)")
    if outcome == "miss" and "enlarged" in D and att.side != dfn.side:
        outcome = "hit"                                # Enlarge: too big to miss
    if outcome == "graze" and "precision" in A:
        outcome = "hit"                                # Precision: no glancing blows (f235)
    if outcome == "graze" and "vantage_fighter" in A and "elevated" in att.position_tags:
        outcome = "hit"                                # Vantage: no glancing blows from high ground
    if reliable:
        outcome = "hit"                            # Reliable: never misses, never crits
        if rec is not None:
            rec["note"] = "Reliable: never misses, never crits"
    guide = dfn.counters.get("guided")
    if outcome == "miss" and guide and guide != att.id and att.side != dfn.side:
        dfn.counters.pop("guided", None)
        outcome = "hit"                            # Guiding Light (f268): an ally's next blow cannot miss
        if rec is not None:
            rec["note"] = "Guiding Light: the blow cannot miss"
    if att.counters.get("tarnished", 0) > 0 and outcome != "miss":
        att.counters["tarnished"] -= 1
    att.counters["last_outcome"] = outcome
    if att.always_miss:
        outcome = "miss"
        if rec is not None:
            rec["note"] = "Its blow goes wide"
    if rec is not None:
        rec["outcome"] = outcome
    if outcome == "miss":
        att.relentless = 0
        att.counters.pop("stoke", None)                 # Stoke (f268): a miss lets the fire die back
        combat.log.append(f"{att.name} {label} {dfn.name}: miss")
        if rec is not None:
            rec["figure"] = figure(rec)
        tell(combat, f"{who(att)} {vb(att, 'go', 'goes')} for {who(dfn)} {how} - and {vb(att, 'miss', 'misses')}", rec)
        if "windwalker" in D:
            dfn.windwalker_ready = True
        if "flowing_step" in D:
            dfn.counters["flow"] = min(3, dfn.counters.get("flow", 0) + 1)
        if can_riposte and "riposte" in D and att.reach in ("melee", "extended") and att.alive and dfn.alive \
                and att.side != dfn.side and dfn.counters.get("riposte_round") != combat.round:
            dfn.counters["riposte_round"] = combat.round               # the first blade that misses you each round is answered
            apply_damage(combat, dfn, att, 1.0, "ripostes against", rng, can_cleave=False, can_riposte=False,
                         how=f"answering the miss in a lightning riposte {weapon_phrase(dfn)}")
        return False
    mult = hit_step(rec, 1.0, "Move power", multiplier)
    mult = hit_step(rec, mult, {"graze": "Glancing blow", "hit": "", "crit": "Critical hit"}[outcome], {"graze": 0.5, "hit": 1.0, "crit": crit_multiplier(att)}[outcome])
    mult = hit_step(rec, mult, "Weakened or strengthened", max(0.2, 1 + status_mod(att, "power") / 100))                  # poisoned or weakened attackers hit softer
    if att.side != dfn.side:
        mult = hit_step(rec, mult, "Target marked", 1 + status_mod(dfn, "taken") / 100)                       # a marked target takes more
    if "empowered" in A:
        mult = hit_step(rec, mult, "Empowered", 1 + A["empowered"] / 100)
    rally = att.counters.pop("rallied", 0)
    if rally and att.side != dfn.side:
        mult = hit_step(rec, mult, "Rallying Light", 1 + rally / 100)
    if "scented" in dfn.statuses and (fights_for_you(att) or att.summon_form) and att.side != dfn.side:
        from engine import spellcraft as _sc2
        mult = hit_step(rec, mult, "Pack Scent", 1 + _sc2.num(_sc2.EXPR["pack_scent"], "light", "pct", 30) / 100)
    if "enlarged" in A and att.reach in ("melee", "extended"):
        mult = hit_step(rec, mult, "Enlarged", 1 + A["enlarged"] / 100)        # a bigger body behind every melee blow
    if "executioner" in A and dfn.hp < dfn.max_hp * 0.3:
        mult = hit_step(rec, mult, "Executioner", 1 + A["executioner"] / 100)
    if "relentless" in A:
        mult = hit_step(rec, mult, "Relentless", 1 + A["relentless"] * min(5, att.relentless) / 100)
        att.relentless += 1
    if "last_stand" in A and att.hp < att.max_hp / 4:
        mult = hit_step(rec, mult, "Last Stand", 1 + A["last_stand"] / 100)
    slay = category_bonus(att, A, dfn, "slay")
    if slay:
        mult = hit_step(rec, mult, "Slayer", 1 + slay / 100)
    if "opportunist" in A and set(dfn.statuses) & {"slowed", "prone", "stunned", "bleeding", "frightened"}:
        mult = hit_step(rec, mult, "Opportunist", 1 + A["opportunist"] / 100)
    if "press_the_opening" in A and (is_open(dfn, combat.round) or "exposed" in dfn.position_tags):
        mult = hit_step(rec, mult, "Press the Opening", 1 + A["press_the_opening"] / 100)
    if "hex" in A and "hexed" in dfn.statuses:
        mult = hit_step(rec, mult, "Hex", 1 + A["hex"] / 100)
    if "blood_pact" in A:
        mult = hit_step(rec, mult, "Blood Pact", 1 + A["blood_pact"] / 100)
    if "attunement" in A and att.counters.get("attune"):
        mult = hit_step(rec, mult, "Attunement", 1 + A["attunement"] * att.counters["attune"] / 100)
    if "iron_will" in A and att.counters.get("shrugged"):
        mult = hit_step(rec, mult, "Iron Will", 1 + 0.10 * att.counters["shrugged"])
    from engine import spellcraft as _sc
    mult = _sc.hit_mult(combat, att, dfn, mult, rec)   # Shatter, Blister, Smite (f266)
    if "unaware" in dfn.statuses:                  # a sneak attack on someone who never saw it coming (less spread over an area)
        mult = hit_step(rec, mult, "Unaware target", RULES["unaware_area_damage" if att.counters.get("area_hit") else "unaware_damage"])
    if att.windwalker_ready:
        att.windwalker_ready = False
        mult = hit_step(rec, mult, "Windwalker", 1 + A.get("windwalker", 0) / 100)
    if "flowing_step" in A and att.counters.get("flow"):
        mult = hit_step(rec, mult, "Flowing Step", 1 + A["flowing_step"] * att.counters["flow"] / 100)
        tell(combat, f"{who(att)} {vb(att, 'flow', 'flows')} out of the dodge and into the blow (Flowing Step)")
        att.counters["flow"] = 0
    mult = combat_perks.damage_mult(combat, att, dfn, mult, rec)
    base_info: dict = {}
    dmg = raw_damage(att, mult, active_triggers(att, combat, dfn), rng, steady=reliable, trace=base_info)
    def_info: dict = {}
    taken, absorbed = mitigate(dfn, dmg, att.damage_type, att.level, combat, att, trace=def_info)
    if rec is not None:
        rec["base"], rec["defence"] = base_info, def_info
    if "spellblade" in A:
        extra, _ = mitigate(dfn, dmg * A["spellblade"] / 100, "magical", att.level, combat, att)
        taken += extra
        if rec is not None:
            rec["extras"].append(["Spellblade (magic, after defence)", f"+{round(extra)}"])
    if "deflect" in D and rng.uniform(0, 100) < D["deflect"]:
        taken *= 0.5
        if rec is not None:
            rec["extras"].append(["Deflect: half turned aside", "×0.5"])
        tell(combat, f"{who(dfn)} {vb(dfn, 'turn', 'turns')} the worst of it aside (Deflect)")
    if "guarded" in D and dfn.side == "player":
        guard = next((a for a in combat.allies() if fights_for_you(a)), None)
        if guard:
            moved = taken * min(90, D["guarded"]) / 100
            taken -= moved
            if rec is not None:
                rec["extras"].append(["Guardian takes a share", f"-{round(moved)}"])
            take_damage(combat, guard, moved, att, rng, att.damage_type)
            tell(combat, f"{who(guard)} throws itself in the way and takes {round(moved)} of it")
    pre_shield = taken
    taken = take_damage(combat, dfn, taken, att, rng, att.damage_type, rec=rec)
    att.counters["last_hit"] = int(taken)               # what this blow dealt, for an ignite it sets (engine/afflictions.py)
    from engine import spellcraft
    spellcraft.on_hit(combat, att, dfn, taken, rng)      # the element of the ability being used does its work (engine/spellcraft.py)
    spellcraft.on_any_hit(combat, att, dfn, taken, rng)  # and the marks already on the two of them (f268)
    if open_wound and att.damage_type == "physical" and "bleeding" in dfn.statuses:
        from engine import afflictions
        deep = combat_perks.P["open_wound"]["deep"] if "open_wound" in A else 1.0     # Open Wound (f311): your blows tear it twice as deep
        lost = afflictions.tear(combat, dfn, deep, "(Open Wound)" if deep > 1 else "")   # any physical blow on an open wound tears it again
        if rec is not None and lost:
            rec["bleed"] = lost                          # shown on the blow's line and in its working (f286)
            rec["extras"].append(["Open wound tears" + (" twice as deep (Open Wound)" if deep > 1 else "") + " (after defence, not in the figure above)", f"+{lost}"])
    if rec is not None:
        rec["final"] = round(taken)
        rest = (round(taken) - round(pre_shield)) - rec.pop("named_total", 0)
        if rest:
            rec["extras"].append(["Other last-moment effects", f"{rest:+d}"])
        rec["figure"] = figure(rec)
    if att.side == "ally" and dfn.side == "enemy":
        dfn.counters["flanked"] = combat.round                             # an ally has struck it (Flanking)
    if "frost_armor" in D and att.reach in ("melee", "extended") and att.alive and att.side != dfn.side:
        if add_status(combat, att, "slowed", 2, dfn):     # 2: it holds through the attacker's next turn
            tell(combat, f"{who(att)} {vb(att, 'strike', 'strikes')} the ice around {who(dfn)} and the cold bites deep - {vb(att, 'you are', 'it is')} slowed (Frost Armor)")
    if "thorn_pct" in D and att.reach in ("melee", "extended") and att.alive and att.side != dfn.side:
        back = D.get("thorn_flat", 0) + dfn.armor * D["thorn_pct"] / 100          # Thorns (buff): a little for anyone, a lot for the armored
        back = take_damage(combat, att, back, dfn, rng, "physical")
        combat.log.append(f"{att.name} is hurt by {dfn.name}'s thorns: {back}")
        tell(combat, f"{who(att)} {vb(att, 'are', 'is')} torn for {back} by the thorns around {who(dfn)} (Thorns)")
    if "thorns" in D and att.reach == "melee" and att.alive and att.side != dfn.side:
        floor = AT.T["thorns_floor"] * RULES["mitigation"]["armor_k"] * growth(att.level)
        back = max(dfn.armor, floor) * D["thorns"] / 100
        back = take_damage(combat, att, back, dfn, rng, "physical")
        combat.log.append(f"{att.name} is hurt by {dfn.name}'s thorns: {back}")
        tell(combat, f"{who(att)} {vb(att, 'are', 'is')} hurt for {back} as the blow rebounds (Thorns)")
    note = {"graze": " (graze)", "crit": " (critical)"}.get(outcome, "")
    soak = f", {round(absorbed)} absorbed" if absorbed >= 1 else ""
    combat.log.append(f"{att.name} {label} {dfn.name}: {taken} damage{note}{soak}")
    quality = {"graze": "only a glancing blow", "crit": "a perfect strike, " + severity(taken, dfn.max_hp)}.get(outcome, severity(taken, dfn.max_hp))
    turned = f"; {whose(dfn)} {cover(dfn)} turns part of it" if absorbed > taken * 0.4 else ""
    after = f" - {who(dfn)} {vb(dfn, 'are', 'is')} {condition(dfn)}" if dfn.alive else ""
    tell(combat, f"{who(att)} {vb(att, 'hit', 'hits')} {who(dfn)} {how}: {quality}{turned}{after}", rec)
    emult = multiplier * {"graze": 0.5, "hit": 1.0, "crit": crit_multiplier(att)}[outcome]
    for el in elements.ELEMENTS:
        flat = flat_bonus(att, f"{el}_damage", {"always"})
        if flat > 0 and dfn.alive:
            part, _ = mitigate(dfn, flat * emult, "magical", att.level, combat, att)
            held, att.hit_element = att.hit_element, el
            dealt = take_damage(combat, dfn, part, att, rng, "magical")
            att.hit_element = held
            taken += dealt
            combat.log.append(f"{att.name}'s {el} damage from gear hits {dfn.name}: {dealt}")       # (f419) lightning does not burn
            if rec is not None:
                rec["extras"].append([f"{el.capitalize()} damage from gear", f"+{round(dealt)}"])
            if not combat.burn_told or not dfn.alive:           # (f349) told once a fight (lightning was narrated 56 rounds running); a kill by it is always told
                tell(combat, f"{el} damage follows the {'spell' if att.spell_kind == 'spell' else 'blow'} into {who(dfn)}"
                     + (f" - {who(dfn)} {vb(dfn, 'are', 'is')} {condition(dfn)}" if dfn.alive else ""))
                combat.burn_told = True
    if "acid_weapon" in A and dfn.alive and taken > 0 and att.spell_kind != "spell" and not warded(dfn, "acid"):
        cap = AT.BUFFS.get("acidcoat", {}).get("cap", 75)
        cut = min(cap, dfn.corroded + A["acid_weapon"] * (ATTUNE["acid"] if attuned(att, "acid") else 1))   # Acid Coating
        if cut > dfn.corroded:
            dfn.corroded = cut
            tell(combat, f"the acid eats into {whose(dfn)} armor ({cut:g}% gone)")
    if "envenom_weapon" in A and dfn.alive and taken > 0 and att.spell_kind != "spell":
        add_status(combat, dfn, "poisoned", 3, att)        # Envenom Weapon: every weapon hit adds a stack, and nothing more
    if "elemental_weapon" in A and dfn.alive and taken > 0 and att.spell_kind != "spell":     # Imbue: weapon hits only, never spells
        buff = next((b for b in att.buffs.values() if b.get("kind") == "imbue"), {})
        el = buff.get("element") or "fire"
        part, _ = mitigate(dfn, dmg * A["elemental_weapon"] / 100, "magical", att.level, combat, att)
        held, att.hit_element = att.hit_element, el
        extra = take_damage(combat, dfn, part, att, rng, "magical")
        att.hit_element = held
        combat.log.append(f"{att.name}'s {el} weapon hits {dfn.name}: {extra}")
        if rec is not None:
            rec["extras"].append([f"{el.capitalize()} weapon", f"+{round(extra)}"])
        tell(combat, f"{el} flares along the blow and bites into {who(dfn)} ({buff.get('name') or 'Elemental Weapon'})")
        if buff.get("exprs"):
            from engine import spellcraft
            spellcraft.carried(combat, att, dfn, buff["exprs"], buff.get("etier", "light"), buff.get("name", ""), taken, rng)
    att.counters["storm"] = att.counters.get("storm", 0) + 1 if "stormcaller" in A else 0
    if "stormcaller" in A and dfn.alive and att.counters["storm"] % 3 == 0:
        bolt, _ = mitigate(dfn, dmg * 0.5, "magical", att.level, combat, att)
        combat.log.append(f"lightning strikes {dfn.name}: {take_damage(combat, dfn, bolt, att, rng, 'magical')} damage (Stormcaller)")
        tell(combat, f"lightning answers {whose(att)} weapon and cracks down onto {who(dfn)} (Stormcaller)")
    if outcome == "crit" and "bloodlust" in A:
        gain = round(att.max_hp * A["bloodlust"] / 100)
        restore(combat, att, gain)
        tell(combat, f"the perfect strike sets {whose(att)} blood singing (Bloodlust)")
    if att.side == "player" and att.max_stamina and label.startswith("attacks") and outcome != "graze":
        m = RULES["momentum"]["crit" if outcome == "crit" else "hit"]
        att.stamina = min(att.max_stamina, att.stamina + pools.reference_pool("stamina", att.level) * m / 100)
    if "ki_strike" in A and att.max_stamina and outcome != "graze":
        att.stamina = min(att.max_stamina, att.stamina + att.max_stamina * A["ki_strike"] * (2 if outcome == "crit" else 1) / 100)
    if "battle_rhythm" in A and att.max_stamina:
        att.stamina = min(att.max_stamina, att.stamina + att.max_stamina * A["battle_rhythm"] / 100)
    if "vampiric" in A:
        heal = round(taken * A["vampiric"] / 100)
        if heal:
            restore(combat, att, heal)
            combat.log.append(f"{att.name} drinks {heal} health from the wound (Vampiric)")
            tell(combat, f"{whose(att)} weapon drinks from the wound, and strength flows back into {who(att)} (Vampiric)")
    if att.side == "player" and taken > 0:                                  # on-hit properties rolled on the weapon
        always = {"always"}
        leech = bonus(att, "vampiric", always)
        if leech and att.alive:
            heal = round(taken * leech / 100)
            if heal:
                restore(combat, att, heal)
                tell(combat, f"the weapon drinks from the wound, and strength flows back into {who(att)}")        # (f419) no figure, no game word
        if att.max_mana:
            att.mana = min(att.max_mana, att.mana + att.max_mana * bonus(att, "siphon_mana", always) / 100)
        if att.max_stamina:
            att.stamina = min(att.max_stamina, att.stamina + att.max_stamina * bonus(att, "siphon_stamina", always) / 100)
        for stat, status, rounds, word in (("envenom_chance", "poisoned", 3, "envenomed"), ("ignite_chance", "burning", 3, "ignited"),
                                           ("jolt_chance", "stunned", 1, "jolted")):
            chance = bonus(att, stat, always)
            if chance and dfn.alive and rng.uniform(0, 100) < chance and add_status(combat, dfn, status, rounds, att):
                combat.log.append(f"{dfn.name} is {status} (weapon)")
                tell(combat, f"{who(dfn)} {STATUS_WORDS[status][0 if dfn.side == 'player' else 1]} (the weapon {word} it)")
    if att.side == "player" and "lifebinder" in A:
        for ally in (a for a in combat.allies() if fights_for_you(a)):
            restore(combat, ally, round(taken * A["lifebinder"] / 100))
    if can_cleave and att.side == "player" and "packbond" in A and dfn.alive:
        for ally in [a for a in combat.allies() if fights_for_you(a)]:
            if dfn.alive and rng.uniform(0, 100) < A["packbond"]:
                apply_damage(combat, ally, dfn, 1.0, "strikes alongside", rng, can_cleave=False, can_riposte=False,
                             can_flurry=False, how="as the bond answers the blow (Packbond)")
    if "hex" in A and dfn.alive and "hexed" not in dfn.statuses:
        dfn.statuses["hexed"] = 99
        combat.log.append(f"{dfn.name} is hexed")
        tell(combat, f"a curse settles on {who(dfn)} like cold ash (Hex)")
    if dfn.alive:
        for effect, status, rounds in (("frostbite", "slowed", 2), ("rending", "bleeding", 3), ("thunderous", "stunned", 1),
                                       ("blinding", "blinded", 1), ("terrify", "frightened", 2)):
            if effect in A and rng.uniform(0, 100) < A[effect] and add_status(combat, dfn, status, rounds, att):
                if rec is not None:
                    rec.setdefault("inflicted", []).append(status)       # on the blow's line in the combat log (f286)
                    rec["figure"] = figure(rec)
                combat.log.append(f"{dfn.name} is {status}")
                tell(combat, f"{who(dfn)} {STATUS_WORDS[status][0 if dfn.side == 'player' else 1]} ({effect.capitalize()})")
    if "earthshaker" in A and dfn.alive and (outcome == "crit" or (outcome == "hit" and rng.uniform(0, 100) < A["earthshaker"])):
        if add_status(combat, dfn, "prone", 1, att):
            combat.log.append(f"{dfn.name} is knocked flat")
            tell(combat, f"the blow lands like a falling wall and {who(dfn)} {STATUS_WORDS['prone'][0 if dfn.side == 'player' else 1]} (Earthshaker)")
    if "open_palm" in A and dfn.alive and (outcome == "crit" or (outcome == "hit" and rng.uniform(0, 100) < A["open_palm"])):
        if add_status(combat, dfn, "prone", 1, att):
            combat.log.append(f"{dfn.name} is swept off their feet")
            tell(combat, f"the open palm turns {whose(dfn)} balance against {who(dfn)} and {who(dfn)} {STATUS_WORDS['prone'][0 if dfn.side == 'player' else 1]} (Open Palm)")
    combat_perks.after_hit(combat, att, dfn, outcome, taken, rng)
    if not dfn.alive:
        combat.log.append(f"{dfn.name} falls")
        if att is not dfn:
            combat.felled_by[dfn.id] = who(att)
        by = f" to {whose(att)} blow" if att is not dfn and dfn.side != "enemy" else ""     # (f412) on the player's side, whose blow it was
        tell(combat, f"{who(dfn)} {vb(dfn, 'fall', 'falls')}{by}" + (" - and the world goes dark" if dfn.side == "player" else " and does not rise"))
        att.kill_round = combat.round
        combat_perks.on_kill(combat, att, dfn, rng, echo=bool(att.counters.get("echo_cast")))
        if "thrall" in A and att.side == "player" and dfn.side == "enemy" and not combat.thrall_used:
            raise_thrall(combat, dfn)
        else:
            _sc.on_death(combat, dfn, att)                 # Reap, Pyre, Contagion: the marks that wait for death (f266, f268)
        if "soul_harvest" in A and att.max_mana:
            att.mana = min(att.max_mana, att.mana + att.max_mana * A["soul_harvest"] / 100)
            tell(combat, f"something passes from the fallen into {who(att)} (Soul Harvest)")
        if "triumph" in A:
            heal = round(att.max_hp * A["triumph"] / 100)
            restore(combat, att, heal)
            combat.log.append(f"{att.name} is renewed by the kill: +{heal} health (Triumph)")
            tell(combat, f"the kill fills {who(att)} with fresh strength (Triumph)")
    if can_flurry and "flurry" in A and dfn.alive and att.alive and rng.uniform(0, 100) < A["flurry"]:
        apply_damage(combat, att, dfn, multiplier * 0.6, "strikes again at", rng, can_cleave=False, can_riposte=False,
                     how="in a blur of follow-up blows (Flurry)", can_flurry=False)
    if can_cleave and "many_heads" in A and att.side == "player" and att.counters.get("heads_round") != combat.round and att.alive:
        others = [e for e in combat.enemies() if e is not dfn]
        if others:
            att.counters["heads_round"] = combat.round
            apply_damage(combat, att, min(others, key=lambda e: e.hp), A["many_heads"] / 100, "is struck by another head against", rng,
                         can_cleave=False, can_riposte=False, can_flurry=False, how="from the side, with another head of the beast (Many Heads)")
    if can_cleave and "follow_through" in A and not dfn.alive:
        others = [e for e in (combat.enemies() if att.side != "enemy" else []) if e is not dfn and e.zone_id == att.zone_id]
        if others:
            from engine import battlefield as _bfc
            nxt = _bfc.closest(combat, att, others) or others[0]
            tell(combat, f"the blow that fells {who(dfn)} does not stop (Follow Through)")
            apply_damage(combat, att, nxt, multiplier * A["follow_through"] / 100, "carries on into", rng, can_cleave=False,
                         can_riposte=False)
    if can_cleave and "cleave" in A and att.reach in ("melee", "extended") and att.spell_kind != "spell":
        nxt = cleave_target(combat, att, dfn)             # Cleave (a weapon's power, f250): every melee blow carries into one more
        if nxt is not None:
            tell(combat, f"the blow carries through into {who(nxt)} (Cleave)")
            apply_damage(combat, att, nxt, multiplier * A["cleave"] / 100, "cleaves into", rng, can_cleave=False, can_riposte=False)
    return True


def enters(combat: Combat, f: Fighter) -> None:
    """A fighter joining mid-fight (a thrall raised, a wave arriving, a summon, a boss's guard) steps onto the field now: tied to
    nobody, placed fresh - in a side zone when they come from afar (starts_far), else with their side."""
    combat.fighters.append(f)
    from engine import battlefield as _bf
    _bf.place_joiner(combat, f)


def raise_thrall(combat: Combat, dead: Fighter, reason: str = "") -> None:
    """The first enemy the wearer slays rises as it was in life and fights for them until the fight ends (or it falls again). Reap
    (f266) raises others the same way."""
    if not reason:
        combat.thrall_used = True
    t = dead.model_copy(deep=True)
    base = dead.name.replace(" (elite)", "")
    for article in ("the ", "a ", "an ", "one of "):
        if base.lower().startswith(article):
            base = base[len(article):]
    taken = {f.id for f in combat.fighters}
    t.id = "thrall" if "thrall" not in taken else next(f"thrall{n}" for n in range(2, 99) if f"thrall{n}" not in taken)
    t.side, t.name = "ally", f"the risen {base}"
    strength = 0.6 if dead.boss else 1.0
    t.max_hp = max(1, round(dead.max_hp * strength))
    t.hp, t.shield, t.fled = float(t.max_hp), 0.0, False
    t.statuses, t.cooldowns, t.buffs, t.boss = {}, {}, {}, {}
    t.rank, t.temperament, t.spawn = "normal", "aggressive", ""
    enters(combat, t)
    combat.log.append(f"{dead.name} rises to fight for you")
    tell(combat, f"{who(dead)} does not stay down: it rises again, as it was in life, and turns on its own side - {t.name} fights for you now, until this fight is over ({reason or 'Risen Thrall'})")


STATUS_WORDS = {
    "slowed": ("stagger, your limbs suddenly heavy", "staggers, suddenly sluggish"),
    "withered": ("feel something sour in your blood - wounds will not knit well", "is withered, its wounds souring"),
    "bleeding": ("are bleeding freely", "is bleeding freely"),
    "stunned": ("reel, stunned", "reels, stunned"),
    "brittle": ("feel the cold make you brittle", "is brittle with cold"),
    "shaky": ("feel your hands begin to shake", "is shaking, its aim gone"),
    "jittered": ("twitch with current", "is twitching with current"),
    "wasting": ("feel the sickness take hold", "is wasting"),
    "conductive": ("feel charge cling to you", "crackles with charge"),
    "superconductive": ("feel the ice hum with charge", "is sheathed in humming ice"),
    "frostwelded": ("find your feet frozen to the ground", "is frozen to the ground"),
    "numb_hands": ("lose all feeling in your hands", "cannot feel its hands"),
    "tangled": ("have your arms tangled in vines", "has its arms tangled in vines"),
    "humbled": ("feel the edge go out of your blows", "is humbled, the edge gone from its blows"),
    "scented": ("are marked by a scent every hunter can follow", "is marked by its scent"),
    "petrified": ("turn to stone", "turns to stone"),
    "prone": ("are knocked off your feet", "is knocked off its feet"),
    "frightened": ("falter, fear gripping you", "falters, gripped by fear"),
    "blinded": ("are blinded, the world gone to white", "is blinded and flails"),
    "poisoned": ("feel poison burning through your veins", "convulses as poison takes hold"),
    "burning": ("are set alight", "is set alight"),
    "weakened": ("feel your strength drain away", "wilts, its strength sapped"),
    "exposed": ("are left open, your guard stripped away", "is left open, its guard stripped away"),
    "marked": ("are marked out for destruction", "is marked out for destruction"),
    "befuddled": ("reel, your thoughts scattered", "reels, its thoughts scattered"),
    "grappled": ("are seized and held fast", "is seized and held fast"),
    "illuminated": ("are lit up in a hard glare - there is nowhere to hide", "is lit up in a hard glare, with nowhere to hide"),
    "unraveled": ("feel your body turn against its own mending", "is unraveled - any healing it gets will hurt it instead"),
}


def in_reach(att: Fighter, dfn: Fighter, reach: str | None = None) -> bool:
    """Pure reach, with no word on protection (battlefield.attack_access has that): melee reaches who it is tied up with, extended
    reaches its whole zone, ranged and area reach everywhere."""
    reach = reach or att.reach
    if reach in ("ranged", "area", "self"):
        return True
    if att.zone_id != dfn.zone_id:
        return False
    if reach == "extended":
        return True
    return dfn.id in att.engaged_with


def contest(att: Fighter, dfn: Fighter, att_attrs: list[str], rng: random.Random) -> str:
    """A control's graded contest: 'full', 'partial' (it would just have been resisted - it half-takes instead) or 'none'. Diminishing
    returns downgrade the result one step per time this target has already been controlled this fight (a boss counts as once already)."""
    a = att.best_attr(att_attrs)
    w = dfn.attrs.get("wisdom", 10)
    chance = 25 + 40 * (w - a) / max(1, w + a)
    chance += bonus(dfn, "resolve", {"always"})
    chance = max(5, min(90, chance))
    r = rng.uniform(0, 100)
    grade = "full" if r >= chance else ("partial" if r >= chance * RULES["control"]["resist_share"] else "none")
    prior = dfn.counters.get("controlled", 0) + (RULES["control"]["boss_prior"] if dfn.boss else 0)
    for _ in range(prior):
        grade = {"full": "partial", "partial": "none", "none": "none"}[grade]
    return grade


def resist(att: Fighter, dfn: Fighter, att_attrs: list[str], rng: random.Random) -> bool:
    """True if the defender resists a control or influence effect (resolve vs the attacker)."""
    a = att.best_attr(att_attrs)
    w = dfn.attrs.get("wisdom", 10)
    chance = 25 + 40 * (w - a) / max(1, w + a)
    chance += bonus(dfn, "resolve", {"always"})            # gear and passives that add resolve (points of chance)
    return rng.uniform(0, 100) < max(5, min(90, chance))


# ---------- actions ----------

def cost_of(f: Fighter, move: Move, combat: Combat | None = None) -> int:
    if move.effect == "relic":
        return 0
    if move.resource == "mana" and not f.archmage_used and "archmage" in mechanics(f, combat):
        return 0
    if f.counters.get("free_fire") and getattr(move, "element", "") == "fire":
        return 0                                        # Phoenix Spark (f268): the next fire costs nothing
    if move.effect == "buff":
        from engine import spells
        cost = spells.buff_mana(f.level)                 # (f400) a buff: no tier, a flat cost by the rank the caster's level allows
    elif move.resource == "stamina":
        # Stamina is a rhythm: smaller flat costs (a share of a typical pool at your level), refilled by fighting
        pool = pools.reference_pool("stamina", f.level) if f.side == "player" else f.max_stamina
        cost = pool * (move.cost_percent or RULES["stamina_cost_percent"][move.tier]) / 100
    elif getattr(move, "rank", 0):
        from engine import spells
        cost = spells.mana(move)                         # (f397) a ranked spell: a flat cost, by its rank and form
    else:
        pool = pools.reference_mana(f.level) if f.side == "player" else f.max_mana     # a share of what a dedicated caster has
        cost = pool * (move.cost_percent or RULES["ability_cost_percent"][move.tier]) / 100
    unburdened = mechanics(f, combat).get("unburdened", 0)
    if unburdened:
        cost *= 1 - min(90, unburdened) / 100
    if move.shape == "overcharge":
        cost *= AT.SHAPES["overcharge"]["cost"]
    if move.channel:
        cost *= RULES["channel"]["cost"]                 # the mana half of a channeled strike (its stamina is stamina_part)
    from engine import combat_perks
    cost = combat_perks.cost(combat, f, move, cost)
    return max(1, math.ceil(cost)) if cost > 0 else 0


def stamina_part(f: Fighter, move: Move, combat: Combat | None = None) -> int:
    """The stamina a channeled strike costs on top of its mana (f260): a technique's full cost for its tier."""
    if not getattr(move, "channel", False) or move.resource != "mana":
        return 0
    pool = pools.reference_pool("stamina", f.level) if f.side == "player" else f.max_stamina
    cost = pool * RULES["stamina_cost_percent"][move.tier] / 100 * RULES["channel"]["stamina"]
    unburdened = mechanics(f, combat).get("unburdened", 0)
    if unburdened:
        cost *= 1 - min(90, unburdened) / 100
    return max(1, math.ceil(cost)) if cost > 0 else 0


def can_use(f: Fighter, move: Move, combat: Combat | None = None) -> str | None:
    if move.effect == "damage" and move.reach in ("melee", "extended") and not getattr(move, "martial_form", "") == "counter" \
            and "bladeward" in mechanics(f, combat):
        return f"{move.name} is a melee attack, and Bladeward will not let a blade pass outward until it ends."
    from engine import spellcraft as _scu
    why_not = _scu.blocked_attack(f, move.reach) if move.effect == "damage" else ""
    if why_not:
        return f"{move.name} cannot be used right now: {why_not}."
    if getattr(move, "channel", False) and not (f.damage_type == "physical" and f.reach in ("melee", "extended")):
        return f"{move.name} is struck through a melee weapon, and you have none in hand."      # (f250: no longer cast bare)
    if move.effect == "relic" and move.uses and f.relic_uses.get(move.id, 0) >= move.uses:
        return f"{move.name} has given all it has this fight."
    from engine import combat_perks
    if f.cooldowns.get(move.id, 0) > 0 and not combat_perks.may_overcast(combat, f, move):
        return f"{move.name} isn't ready yet ({f.cooldowns[move.id]} more rounds)."
    have = f.stamina if move.resource == "stamina" else f.mana
    if move.resource == "mana":
        blood = mechanics(f, combat).get("overchannel", 0)
        if blood:
            have += max(0.0, f.hp - f.max_hp * 0.1) / blood
    if have < cost_of(f, move, combat):
        return f"Not enough {move.resource} for {move.name}."
    if f.stamina < stamina_part(f, move, combat):
        return f"Not enough stamina for {move.name}."
    return None


def act_attack(combat: Combat, att: Fighter, target: Fighter, rng: random.Random) -> None:
    from engine import battlefield as bf
    if att.side == "player" and target:
        combat.focus = target.id
    from engine import spellcraft as _sca
    why_not = _sca.blocked_attack(att, att.reach)
    if why_not:
        combat.log.append(f"{att.name} cannot attack: {why_not}")
        tell(combat, f"{who(att)} {vb(att, 'cannot', 'cannot')} attack - {why_not}")
        return
    if att.reach in ("melee", "extended") and "bladeward" in mechanics(att, combat):
        combat.log.append(f"{att.name} cannot strike in melee under Bladeward")
        tell(combat, f"the ward around {who(att)} will not let a blade pass outward - {who(att)} cannot strike in melee while Bladeward holds")
        return
    access = bf.attack_access(combat, att, target)
    if access.ok and att.reach not in ("ranged", "area") and att.zone_id == target.zone_id and not bf.engaged_pair(att, target):
        bf.engage(combat, att, target)                   # moving into the fight is easy: step in and strike in the same action
    if not access.ok:
        story = bf.approach(combat, att, target) if access.can_approach else ""
        combat.log.append(f"{att.name}: {access.why}" + (f"; {story}" if story else ""))
        tell(combat, f"{who(att)} {vb(att, 'are', 'is')} {access.why}" + (f" - {who(att)} {story}" if story else ""))
        return                                           # getting there was the action: the blow comes next round
    att.counters.pop("tier_now", None)                   # a plain blow has no tier
    from engine import combat_perks
    held = (att.hit_element, att.weapon_damage, att.adaptive)
    if att.attuned and combat_perks.has(att, "attuned_edge", combat):
        att.hit_element = att.attuned                     # Attuned Edge: the weapon strikes as the last spell's element
    extra = combat_perks.feral(att, combat)
    if extra:
        att.weapon_damage += extra                        # Feral Form: the blessing's spell power rides the blow
        att.adaptive = True
        tell(combat, f"{whose(att)} blow carries the blessing's power with it {combat_perks.tag(att, 'feral_form')}")
    try:
        apply_damage(combat, att, target, RULES["damage"]["multiplier"]["basic"], f"attacks ({att.weapon_name})", rng)
    finally:
        att.hit_element, att.weapon_damage, att.adaptive = held
        from engine import movement as _mv
        _mv.reveal_after(att)


def cleave_target(combat: Combat, att: Fighter, t: Fighter):
    """The one other enemy a cleaving blow carries into: someone else engaged with the attacker, else someone engaged with the target
    in the same place - the closest. None if there is no one."""
    foes = [e for e in combat.fighters if e.alive and not e.fled and e is not t and (e.side == "enemy") != (att.side == "enemy")]
    near = [e for e in foes if e.id in att.engaged_with] or [e for e in foes if e.zone_id == att.zone_id and e.id in t.engaged_with]
    if not near:
        return None
    from engine import battlefield as bf
    return bf.closest(combat, att, near) or near[0]


def shaped_strike(combat: Combat, att: Fighter, t: Fighter, move: Move, mult: float, rng: random.Random) -> bool:
    """One single-target damage ability, delivered the way its shape says."""
    label, how = f"uses {move.name} on", f"with {move.name}"
    sh = AT.SHAPES.get(move.shape)
    if not sh:
        return apply_damage(combat, att, t, mult, label, rng, how=how)
    kind, frac = move.shape, t.hp / max(1, t.max_hp)
    if "parts" in sh:                                  # volley, double strike, barrage: several smaller hits
        landed = False
        for i in range(sh["parts"]):
            if not t.alive:
                break
            landed |= apply_damage(combat, att, t, mult * sh["each"], label if i == 0 else "strikes again at", rng,
                                   how=how if i == 0 else f"as {move.name} keeps coming", can_cleave=(i == 0), can_flurry=(i == 0))
        return landed
    if kind == "sweeping":
        victims = [t] + [e for e in combat.enemies() if e is not t and e.alive and (e.id in att.engaged_with or
                         (e.zone_id == att.zone_id and e.id in t.engaged_with))]
        landed = False
        for i, v in enumerate(victims):
            if v.alive:
                landed |= apply_damage(combat, att, v, mult * sh["share"], label if i == 0 else "sweeps on into", rng,
                                       how=how if i == 0 else f"as {move.name} carries round", can_cleave=False, can_riposte=(i == 0))
        return landed
    steady = False
    if kind == "finisher":
        mult *= sh["low"] + (sh["high"] - sh["low"]) * (1 - frac)
    elif kind == "opener":
        mult *= sh["fresh"] if frac >= 0.9 else sh["worn"]
    elif kind == "overcharge":
        mult *= sh["damage"]
    elif kind == "desperate":
        mine = att.hp / max(1, att.max_hp)
        mult *= sh["low"] + (sh["high"] - sh["low"]) * (1 - mine)
    elif kind == "exploiting":
        mult *= sh["afflicted"] if t.statuses else sh["plain"]
    elif kind == "flank":
        if combat.round - t.counters.get("flanked", -9) <= 1 and t.counters.get("flanked") is not None:
            mult *= sh["bonus"]
            tell(combat, f"{who(t)} is caught between {whose(att)} blow and the others")
    elif kind == "combo":
        key = f"combo:{t.id}"
        n = att.counters.get(key, 0)
        for k in [k for k in att.counters if k.startswith("combo:") and k != key]:
            att.counters.pop(k)
        mult *= 1 + sh["step"] * min(sh["cap"], n)
    elif kind == "reliable":
        steady = True
    landed = apply_damage(combat, att, t, mult, label, rng, how=how, reliable=steady)
    if kind == "combo":
        if landed:
            att.counters[f"combo:{t.id}"] = att.counters.get(f"combo:{t.id}", 0) + 1
        else:
            att.counters.pop(f"combo:{t.id}", None)
    if kind == "chain" and landed:
        others = [e for e in combat.enemies() if e is not t and e.alive]
        if others:
            from engine import battlefield as bf
            o = bf.closest(combat, att, others) or others[0]
            apply_damage(combat, att, o, mult * sh["side"], "arcs on to", rng, how=f"from {move.name}", can_cleave=False, can_riposte=False)
    elif kind == "cleave" and landed:                 # the blow carries through into one other enemy engaged with you (f250)
        o = cleave_target(combat, att, t)
        if o is not None:
            apply_damage(combat, att, o, mult * sh["share"], "cleaves on into", rng, how=f"from {move.name}", can_cleave=False, can_riposte=False)
    elif kind == "ricochet" and landed:
        last = t
        for share in sh["bounces"]:
            others = [e for e in combat.enemies() if e is not last and e.alive]
            if not others:
                break
            last = rng.choice(others)
            apply_damage(combat, att, last, mult * share, "ricochets into", rng, how=f"from {move.name}", can_cleave=False, can_riposte=False)
    elif kind == "packhunt" and landed and t.alive:
        for a in [a for a in combat.allies() if fights_for_you(a) and not _still(a)]:
            if t.alive:
                apply_damage(combat, a, t, sh["share"], "pounces on", rng, can_cleave=False, can_riposte=False, can_flurry=False,
                             how=f"as {whose(att)} {move.name} brings the pack in")
    return landed


def apply_rider(combat: Combat, att: Fighter, t: Fighter, move: Move, rng: random.Random) -> None:
    """What a rider adds after the ability lands (or takes hold): a status, a push or pull, a buff for companions. Siphon, thrift, seeker,
    sunder and penetrate act elsewhere."""
    r = AT.RIDERS.get(move.rider)
    if not r:
        return
    if move.rider == "rouse":                          # companions, not the target
        pack = [a for a in combat.allies() if fights_for_you(a)]
        for a in pack:
            a.buffs[move.id] = {"rounds": r["rounds"], "mech": {"press": AT.value(r["pct"], move.tier)}, "drain": 0,
                                "collapse": "", "name": move.name, "kind": "rouse"}
        if pack:
            tell(combat, f"{who(att)} {vb(att, 'rouse', 'rouses')} {', '.join(a.name for a in pack)} to fight harder ({r['label']})")
        return
    if move.rider == "drain":
        if att.max_mana and att.alive:
            back = att.max_mana * AT.value(r["mana"], move.tier) / 100
            att.mana = min(att.max_mana, att.mana + back)
            tell(combat, f"{move.name} pulls {round(back)} mana back into {who(att)} ({r['label']})")
        return
    if not t or not t.alive:
        return
    if "status" in r:
        if rng.uniform(0, 100) < AT.value(r["chance"], move.tier) and add_status(combat, t, r["status"], r["rounds"], att):
            combat.log.append(f"{t.name} is {r['status']} ({r['label']})")
            tell(combat, f"{who(t)} {STATUS_WORDS[r['status']][0 if t.side == 'player' else 1]} ({r['label']})")
            if r["status"] == "grappled":
                from engine import battlefield as bf
                bf.engage(combat, att, t)
    elif move.rider == "shove" and "grappled" not in t.statuses and not __import__("engine.combat_perks", fromlist=["unmovable"]).unmovable(combat, t):
        from engine import battlefield as bf
        bf.slip_away(combat, t)
        bf.gain(t, "exposed")
        combat.log.append(f"{t.name} is driven back")
        tell(combat, f"{who(t)} {vb(t, 'are', 'is')} driven back by the force of it, out of the press ({r['label']})")
    elif move.rider == "hook":
        from engine import battlefield as bf
        if not bf.engaged_pair(att, t):
            if t.zone_id != att.zone_id:
                bf.enter_zone(combat, t, att.zone_id)
            elif t.row == "back":
                bf.to_row(combat, t, "loose")
            bf.engage(combat, att, t)
            combat.log.append(f"{t.name} is hauled closer")
            tell(combat, f"{who(t)} {vb(t, 'are', 'is')} hauled out of {'the back' if t.row != 'front' else 'position'} and into the fight ({r['label']})")


def act_ability(combat: Combat, att: Fighter, move: Move, target: Fighter | None, rng: random.Random,
                give: list[Fighter] | None = None, echo: bool = False) -> str | None:
    """One ability, resolved. An echo (engine/combat_perks.py) is the same ability happening again on a perk's account: nothing is
    paid or counted for it, and what it kills raises no further echoes."""
    from engine import combat_perks
    problem = None if echo else can_use(att, move, combat)
    if problem:
        return problem
    if move.effect == "buff" and move.buff != "manashield" and combat_perks.has(att, "selfless", combat) \
            and not [r for r in (give or []) if r is not att]:
        return f"{move.name} is for others: your blessings are not yours to keep (Selfless). Name who it is for."
    if move.effect == "summon" and not echo:
        from engine import summons
        why = summons.refuse(combat, att, move)
        if why:
            return why
    if move.effect == "mobility" and not echo:
        from engine import movement
        if move.movement == "shadowmark" and att.shadow:
            movement.shadow_return(combat, att, move, "called back")   # the return is free: the price was paid going in
            return None
        why = movement.refuse(combat, att, move, target, give)
        if why:
            return why
    if echo:
        att.counters["echo_cast"] = 1
    att.counters["tier_now"] = 0 if move.effect == "buff" else combat_perks.TIER_CODE.get(move.tier, 0)    # (f400) a buff has no tier
    att.counters["reach_now"] = {"ranged": 1, "melee": 2, "extended": 2, "area": 3}.get(move.reach, 0)
    try:
        return _act_ability(combat, att, move, target, rng, give, echo)
    finally:
        from engine import movement as _mv
        _mv.reveal_after(att)
        att.counters.pop("tier_now", None)
        att.counters.pop("reach_now", None)
        att.counters.pop("blood_cast", None)
        if echo:
            att.counters.pop("echo_cast", None)


def _act_ability(combat: Combat, att: Fighter, move: Move, target: Fighter | None, rng: random.Random,
                 give: list[Fighter] | None, echo: bool) -> str | None:
    from engine import combat_perks
    if (move.effect != "buff" and move.effect != "healing") or (move.effect == "buff" and not AT.BUFFS.get(move.buff, {}).get("allies", True)):
        give = None                                    # only a blessing or a heal can go on someone else; a mana shield is your own
    if give:
        give = give[:1]                                # a blessing falls on one at a time (f217)
    if att.side == "player" and target and target.side == "enemy":
        combat.focus = target.id
    if move.effect == "relic":
        from engine import relics
        return relics.use(combat, att, move, target, rng)
    if move.effect == "damage" and move.reach != "area" and getattr(move, "spell_form", "") not in ("blast", "burst") \
            and move.martial_form != "counter":
        aim = target or (combat.enemies()[0] if att.side != "enemy" and combat.enemies() else None)
        if move.rider == "seeker" and att.side != "enemy" and combat.enemies():
            aim = min(combat.enemies(), key=lambda e: e.hp / max(1, e.max_hp))
        from engine import battlefield as bf
        access = bf.attack_access(combat, att, aim, move.reach) if aim else None
        if aim and not access.ok and move.resource == "mana":
            from engine import combat_perks as _cp
            eyes = _cp.familiar_access(combat, att, aim, move)
            if eyes is not None:
                access = eyes                              # Familiar's Eyes: cast from where the summon stands
        if aim and not access.ok and aim.alive and "lightning_step" in (getattr(move, "expressions", None) or []):
            if aim.zone_id != att.zone_id:
                bf.enter_zone(combat, att, aim.zone_id)   # Lightning Step (f268): there in a flash, then the blow
            if move.reach in ("melee", "extended"):
                bf.engage(combat, att, aim)
            tell(combat, f"{who(att)} {vb(att, 'are', 'is')} across the field in a streak of light, on {who(aim)} before {vb(aim, 'you', 'it')} can move (Lightning Step)")
            access = bf.attack_access(combat, att, aim, move.reach)
        if aim and access.ok and move.reach not in ("ranged", "area") and att.zone_id == aim.zone_id:
            bf.engage(combat, att, aim)                   # stepping into the fight comes free with the strike
        if aim and not access.ok:                         # the action is spent getting there, and the ability is kept
            story = bf.approach(combat, att, aim) if access.can_approach else ""
            combat.log.append(f"{att.name}: {access.why} ({move.name} is kept)")
            tell(combat, f"{who(att)} {vb(att, 'are', 'is')} {access.why}" + (f" - {who(att)} {story}" if story else ""))   # (f419) what is kept is the log's
            return None
    cost = cost_of(att, move, combat) if not echo else 0
    body = stamina_part(att, move, combat) if not echo else 0   # a channeled strike's stamina (f260)
    att.stamina -= body
    am = mechanics(att, combat)
    free_cast = move.resource == "mana" and not att.archmage_used and "archmage" in am and not echo
    if att.cooldowns.get(move.id, 0) > 0 and not echo:
        att.counters["overcasting"] = 1                  # Overcast: the cooldown is bought through (cost_of doubled it)
    if move.resource == "stamina":
        att.stamina -= cost
    elif cost > att.mana and "overchannel" in am:
        owed = cost - att.mana
        att.mana = 0
        att.hp = max(1, att.hp - owed * am["overchannel"])
        att.counters["blood_cast"] = 1
        combat.log.append(f"{att.name} pays {owed:.0f} mana in blood (Overchannel)")
        tell(combat, f"{who(att)} {vb(att, 'have', 'has')} nothing left to give, so {vb(att, 'pay', 'pays')} in blood"
             + (", and the spell burns the hotter for it" if "overchannel" in att.mech_names else "") + " (Overchannel)")
    else:
        att.mana -= cost
    if att.counters.get("free_fire") and getattr(move, "element", "") == "fire" and not echo:
        att.counters.pop("free_fire", None)
    combat_perks.on_cast(combat, att, move, echo, cost)
    if move.rider == "thrift":
        back = cost * AT.value(AT.RIDERS["thrift"]["refund"], move.tier) / 100
        if move.resource == "stamina":
            att.stamina = min(att.max_stamina, att.stamina + back)
        else:
            att.mana = min(att.max_mana, att.mana + back)
    if move.resource == "mana" and not echo:
        att.spells_cast += 1
        if "arcane_recall" in am:
            for k in list(att.cooldowns):
                if k != move.id and att.cooldowns[k] > 0:
                    att.cooldowns[k] = max(0, att.cooldowns[k] - int(am["arcane_recall"]))
    if "echoing" in am and not att.counters.get("echoed") and not echo:
        att.counters["echoed"] = 1
        att.stamina = min(att.max_stamina, att.stamina + body)
        if move.resource == "stamina":
            att.stamina = min(att.max_stamina, att.stamina + cost)
        else:
            att.mana = min(att.max_mana, att.mana + cost)
        tell(combat, f"the first working costs {who(att)} nothing - the effort echoes back (Echoing)")
    if move.cooldown and not echo:
        att.cooldowns[move.id] = move.cooldown + 1
    if getattr(move, "cooldown_days", 0) and not echo:
        att.cooldowns[move.id] = 10 ** 6                     # (f397) a named spell: once this fight, and the day is kept (spells.day_cast)
        att.counters["day_cast"] = list(att.counters.get("day_cast", [])) + [move.id]
    ranked = bool(getattr(move, "rank", 0)) and move.effect == "damage"
    if ranked:
        from engine import spells
        mult = spells.power(move) * att.spell_share                         # (f397) a ranked spell: its form's power (f400: a hire's share)
    else:
        mult = move.power or RULES["damage"]["multiplier"][move.tier]          # an ability's own power, or its tier's
    if move.effect == "damage" and not move.rider and not move.shape and not move.expressions and not move.maneuver \
            and move.martial_form in ("", "strike"):
        mult *= 1 + AT.T["plain_damage"]                  # Honed: a plain damage ability is never strictly worse than a decorated one
    if free_cast:
        att.archmage_used = True
        mult *= 1 + am["archmage"] / 100
        tell(combat, f"{who(att)} {vb(att, 'let', 'lets')} the first spell go without a breath of effort (Archmage's Focus)")
    enemies = combat.enemies()
    from engine import spellcraft as _sc

    if move.effect != "damage" and _sc.cast_turns(move) > 1 and not att.counters.get("charged_release"):
        _sc.wind_up(combat, att, move, target or (enemies[0] if enemies else None))    # gathered over turns, whatever it does
    elif move.effect == "damage":
        spell = move.resource == "mana"
        saved = (att.weapon_attrs, att.damage_type, att.weapon_damage, att.adaptive)
        att.hit_element = move.element
        if spell:
            cast_attr = move.attribute or "intelligence"
            att.spell_mult = 1 + att.attrs.get(cast_attr, 10) / RULES["spell_attribute"]
            gear_power = att.offhand_spell + flat_bonus(att, "spell_power", {"always"})
        if spell and move.channel and att.damage_type == "physical" and att.reach in ("melee", "extended"):
            bonus_part = RULES["channel"]["bonus"] * (RULES["spell_base_damage"] * growth(att.level) + gear_power) * att.spell_mult
            att.spell_kind, att.spell_parts = "channel", [["weapon", att.weapon_damage], ["spell", bonus_part]]
            att.weapon_damage += bonus_part
            att.adaptive = True                              # struck as physical or magic, whichever the target resists less
        elif spell:
            att.weapon_attrs = [cast_attr]
            focus = (att.weapon_damage if att.damage_type == "magical" else 0) + gear_power
            att.damage_type = "magical"
            if ranked:                                   # (f397) the rank's base, and the form's share of the caster's spell power
                base_part, focus = spells.base(move.rank), focus * spells.coefficient(move)
                att.spell_kind, att.spell_parts = "spell", [[f"rank {spells.numeral(move.rank)}", base_part]] + ([["spell power", focus]] if focus else [])
            else:
                base_part = RULES["spell_base_damage"] * growth(att.level)
                att.spell_kind, att.spell_parts = "spell", [["spell base", base_part]] + ([["spell power", focus]] if focus else [])
            att.weapon_damage = focus + base_part
        from engine import spellcraft
        form = spellcraft.form_of(move)
        area = form in ("blast", "burst")
        targets, share = spellcraft.targets(combat, att, move, target, enemies)
        from engine import martial
        mform = "" if spell else move.martial_form                   # a technique's form (engine/martial.py)
        if mform == "sweep":
            targets = martial.sweep_targets(combat, att, target or (enemies[0] if enemies else None))
            share, area = martial.FORMS["sweep"]["share"], True
        if spellcraft.cast_turns(move) > 1 and not att.counters.get("charged_release"):
            spellcraft.wind_up(combat, att, move, targets[0] if targets else None)
            targets = []
        elif form == "charged" and not ranked:
            mult *= spellcraft.FORMS["charged"]["mult"]       # a ranked spell's power is all in its form
        elif mform == "windup":
            mult *= martial.FORMS["windup"]["mult"]
        if mform == "counter":
            martial.ready_counter(combat, att, move)
            targets = []
        if move.rider == "seeker" and not area and enemies:
            targets = [min(enemies, key=lambda e: e.hp / max(1, e.max_hp))]
            combat.focus = targets[0].id
        held_pierce, held_wb = att.armor_pierce, att.legendary.get("wardbreaker", 0)
        held_pen = att.legendary.get("penetrating")
        if move.rider == "penetrate":
            att.legendary["penetrating"] = 1
        if move.rider == "sunder":
            cut = AT.value(AT.RIDERS["sunder"]["pierce"], move.tier)
            att.armor_pierce += cut
            att.legendary["wardbreaker"] = held_wb + cut
        landed = False
        spellcraft.begin(att, move)
        for t in targets:
            if not area and not in_reach(att, t, move.reach) \
                    and not (spell and combat_perks.familiar_access(combat, att, t, move, quiet=True) is not None):
                from engine import battlefield as bf
                bf.approach(combat, att, t)
                combat.log.append(f"{att.name} closes in on {t.name}")
                tell(combat, f"{who(att)} {vb(att, 'close', 'closes')} the distance to {who(t)}")
                continue
            before = t.hp
            if form == "curse":
                spellcraft.lay_curse(combat, att, t, move, mult, rng)
                landed = True
                continue
            if area:
                att.counters["area_hit"] = 1
                try:
                    hit = apply_damage(combat, att, t, mult * share, f"uses {move.name} on", rng, how=f"with {move.name}")
                finally:
                    att.counters.pop("area_hit", None)
            elif mform == "flurry":
                hit = martial.flurry(combat, att, t, move, mult, rng)
            else:
                hit = shaped_strike(combat, att, t, move, mult, rng)
            landed |= hit
            if hit and move.maneuver:
                martial.maneuver(combat, att, t, move, rng)          # what the technique does besides damage, by size
            if move.rider:
                if move.rider == "siphon" and att.alive:
                    gain = round(max(0.0, before - t.hp) * AT.value(AT.RIDERS["siphon"]["heal"], move.tier) / 100)
                    if gain:
                        restore(combat, att, gain)
                        tell(combat, f"{move.name} draws {gain} health back into {who(att)} ({AT.RIDERS['siphon']['label']})")
                if move.rider not in ("drain", "rouse") or before > t.hp:
                    apply_rider(combat, att, t, move, rng)
        spellcraft.end(att)
        att.armor_pierce = held_pierce
        if held_pen:
            att.legendary["penetrating"] = held_pen
        else:
            att.legendary.pop("penetrating", None)
        if move.rider == "sunder":
            if held_wb:
                att.legendary["wardbreaker"] = held_wb
            else:
                att.legendary.pop("wardbreaker", None)
        att.weapon_attrs, att.damage_type, att.weapon_damage, att.adaptive = saved
        att.spell_kind, att.spell_parts, att.spell_mult = "", [], 1.0
        att.hit_element = ""
    elif move.effect == "control" and move.maneuver:
        from engine import martial
        martial.control(combat, att, move, target, rng)              # a maneuver, contested (engine/martial.py)
    elif move.effect == "control" and move.expressions:
        from engine import spellcraft
        spellcraft.control(combat, att, move, target, rng)          # what the element does, and no damage (engine/spellcraft.py)
    elif move.effect in ("control", "influence"):
        t = target or (enemies[0] if enemies else None)
        if t:
            power = [move.attribute] if move.resource == "mana" and move.attribute else \
                (["charisma", "strength"] if move.effect == "influence" else att.weapon_attrs)
            grade = contest(att, t, power, rng)
            if grade == "none":
                combat.log.append(f"{att.name} uses {move.name} on {t.name}: resisted")
                tell(combat, f"{who(att)} {vb(att, 'turn', 'turns')} {move.name} on {who(t)}, but {vb(t, 'you shake', 'it shakes')} it off"
                     + (" - it has been worn down against them" if t.counters.get("controlled") or t.boss else ""))
            else:
                status = ("frightened" if move.effect == "influence" else
                          {"light": "slowed", "moderate": "prone", "heavy": "stunned"}[move.tier])
                rounds = 2 if move.tier != "heavy" else 1
                if grade == "partial":
                    status = {"stunned": "slowed", "prone": "slowed"}.get(status, status)
                    rounds = 1
                if add_status(combat, t, status, rounds, att):
                    t.counters["controlled"] = t.counters.get("controlled", 0) + 1
                    combat.log.append(f"{att.name} uses {move.name} on {t.name}: {status}" + (" (partial)" if grade == "partial" else ""))
                    tell(combat, f"{who(att)} {vb(att, 'unleash', 'unleashes')} {move.name} on {who(t)}, and "
                         + (f"{who(t)} half shakes it off, but " if grade == "partial" else "") + f"{who(t)} "
                         f"{STATUS_WORDS[status][0 if t.side == 'player' else 1]}")
                if move.rider:
                    apply_rider(combat, att, t, move, rng)
    elif move.effect == "buff":
        on = list(give or [att])
        if combat_perks.has(att, "twin_benediction", combat) and any(r is not att for r in on) and att not in on:
            on.append(att)                            # Twin Benediction: a blessing on an ally falls on you as well
            tell(combat, f"the blessing falls on {who(att)} too {combat_perks.tag(att, 'twin_benediction')}")
        if not AT.BUFFS.get(move.buff, {}).get("allies", True):
            on = [att]                                # a buff that is only ever your own
        for r in on:
            mech = AT.buff_mech(move.buff)            # one strength (f235)
            rounds = AT.buff_rounds(move.buff)
            if r is not att and combat_perks.has(att, "selfless", combat):
                rounds += 2                           # Selfless: what you give away lasts longer
            for k, b in list(r.buffs.items()):
                if b.get("kind") == move.buff:
                    r.buffs.pop(k)                    # one of each kind: a new casting replaces the old
            r.buffs[move.id] = {"rounds": rounds + (1 if r is not att else 0), "mech": dict(mech), "drain": 0, "collapse": "",
                                "name": move.name, "kind": move.buff, "element": move.element or "fire", "from": att.id,
                                "exprs": list(move.expressions) if move.buff == "imbue" else [], "etier": AT.imbue_strength()}
            if move.buff == "stoneform":
                r.statuses["slowed"] = max(r.statuses.get("slowed", 0), rounds + (1 if r is not att else 0))   # the price of stone
        text = AT.ability_buff_text(move)
        others = [r for r in (give or []) if r is not att]
        if not others:
            combat.log.append(f"{att.name} uses {move.name}: {text}")
            tell(combat, f"{who(att)} {vb(att, 'wrap', 'wraps')} {'yourself' if att.side == 'player' else 'itself'} in {move.name}: {text}")
        else:
            names = " and ".join(who(r) for r in others) if len(others) <= 2 else f"{who(others[0])} and {len(others) - 1} more"
            combat.log.append(f"{att.name} uses {move.name} on {', '.join(r.name for r in (give or []))}: {text}")
            tell(combat, f"{who(att)} {vb(att, 'wrap', 'wraps')} {names}{' and yourself' if att in (give or []) and att.side == 'player' else ''} in "
                         f"{move.name}: {text}")
    elif move.effect == "defense":
        S_ = RULES["stance"]
        for k, b in list(att.buffs.items()):
            if b.get("kind") == "stance":
                att.buffs.pop(k)                           # one stance at a time
        mech = {"stance": S_["percent"][move.tier]}
        if S_.get("counter", {}).get(move.tier):
            mech["riposte"] = S_["counter"][move.tier]
        att.buffs[move.id] = {"rounds": S_["rounds"][move.tier], "mech": mech, "drain": 0, "collapse": "",
                              "name": move.name, "kind": "stance"}
        combat.log.append(f"{att.name} takes the {move.name} stance ({mech['stance']:.0f}% less damage, {S_['rounds'][move.tier]} rounds)")
        tell(combat, f"{who(att)} {vb(att, 'settle', 'settles')} into {move.name}: a guard {who(att)} {vb(att, 'can fight', 'can fight')} from"
             + (", answering any blow that misses" if "riposte" in mech else ""))
    elif move.effect == "mobility":
        from engine import movement
        movement.resolve(combat, att, move, target, rng, give)        # only movement: no blow, no effect (engine/movement.py)
    elif move.effect == "healing":
        from engine import healing
        healing.cast(combat, att, move, (give or [None])[0], rng)
    elif move.effect == "summon":
        from engine import summons
        if summons.form_of(move) != "bound" and not summons.mine(combat, att) and combat_perks.blood_summon(combat, att, move, rng):
            pass                                        # called in blood: a striker a tier stronger, for this whole fight
        else:
            summons.cast(combat, att, move, rng)
    elif move.effect == "command":
        if target:
            combat.focus = target.id
        allies = combat.allies()
        pack = [a for a in allies if fights_for_you(a)]
        kind = move.command or "focus"
        spec = AT.COMMANDS[kind]
        if not allies:
            tell(combat, f"{who(att)} {vb(att, 'give', 'gives')} the command, but no companion is there to obey")
        elif kind == "focus":
            for a in allies:
                if combat.enemies() and not _still(a):
                    tgt = next((e for e in combat.enemies() if e.id == combat.focus), combat.enemies()[0])
                    apply_damage(combat, a, tgt, AT.value(spec["strike"], move.tier), "strikes on command at", rng,
                                 how=f"at {whose(att)} command")
        elif kind == "distract":
            att.buffs[move.id] = {"rounds": AT.value(spec["rounds"], move.tier), "mech": {"taunt": 1}, "drain": 0,
                                  "collapse": "", "name": move.name, "kind": "distract"}
            tell(combat, f"{who(att)} {vb(att, 'draw', 'draws')} every eye in the fight - {AT.command_text(kind, move.tier)}")
        elif not pack:
            tell(combat, f"{who(att)} {vb(att, 'give', 'gives')} the command, but no companion answers it")
        else:
            rounds = AT.value(spec["rounds"], move.tier)
            if kind == "guard":
                att.buffs[move.id] = {"rounds": rounds, "mech": {"guarded": AT.value(spec["share"], move.tier)}, "drain": 0,
                                      "collapse": "", "name": move.name, "kind": "guard"}
            else:
                mech = {"press": AT.value(spec["pct"], move.tier)} if kind == "press" else {"stoneskin": AT.value(spec["pct"], move.tier)}
                for a in pack:
                    a.buffs[move.id] = {"rounds": rounds, "mech": mech, "drain": 0, "collapse": "", "name": move.name, "kind": kind}
            tell(combat, f"{who(att)} {vb(att, 'give', 'gives')} the order - {AT.command_text(kind, move.tier)}")
        combat.log.append(f"{att.name} uses {move.name}: {spec['label'].lower()}")
    else:
        combat.log.append(f"{att.name} uses {move.name}: no clear effect in the fight")
        tell(combat, f"{who(att)} {vb(att, 'try', 'tries')} {move.name}, but it changes little in the heat of the fight")
    if "attunement" in am and not echo:
        att.counters["attune"] = min(5, att.counters.get("attune", 0) + 1)
    if move.resource == "mana" and "starfall" in am and att.spells_cast % 4 == 0 and att.alive and not echo:
        base = RULES["spell_base_damage"] * growth(att.level) * am["starfall"] / 100
        tell(combat, "the sky answers the fourth spell, and stars fall (Starfall)")
        for e in combat.enemies():
            dealt, _ = mitigate(e, base, "magical", att.level, combat, att)
            combat.log.append(f"starfall hits {e.name}: {take_damage(combat, e, dealt, att, rng, 'magical')} damage")
    if att.alive:
        combat_perks.after_cast(combat, att, move, target, rng, give, echo, cost)
    return None


def act_defend(combat: Combat, f: Fighter) -> None:
    f.defending = RULES["defend_percent"]["basic"]
    combat.log.append(f"{f.name} defends")
    tell(combat, f"{who(f)} {vb(f, 'set', 'sets')} {whose(f)} guard and {vb(f, 'wait', 'waits')}")


def retreat(combat: Combat, f: Fighter, rng: random.Random) -> str:
    """Backing away from the fight, priced (the movement law): free and clean behind your own working line; otherwise it costs the
    action, everyone on you gets a parting blow as you pull away, and the fast simply follow. Returns the story."""
    from engine import battlefield as bf
    on_me = bf.engaged(combat, f)
    covered = any(not bf.hostile(f, o) and bf.can_hold(o) and o is not f for o in bf.standing(combat, f.zone_id)) \
        or "sure_footed" in mechanics(f, combat)
    if on_me and not covered:
        for e in on_me:
            if f.alive:
                tell(combat, f"{who(e)} {vb(e, 'strike', 'strikes')} at {who(f)} as {vb(f, 'you pull', 'they pull')} away (a parting blow)")
                apply_damage(combat, e, f, RULES["damage"]["multiplier"]["basic"], "cuts at the retreating", rng,
                             can_cleave=False, can_riposte=False, can_flurry=False)
    followers = [e for e in on_me if e.pace == "fast" and e.alive]
    story = bf.withdraw(combat, f) or "can fall back no further"
    for e in followers:
        if f.alive and e.zone_id == f.zone_id:
            bf.engage(combat, e, f)
            tell(combat, f"{who(e)} follows {who(f)} step for step - there is no outrunning it")
        elif f.alive and combat.battlefield is not None and combat.battlefield.connected(e.zone_id, f.zone_id) \
                and not combat.battlefield.hard(e.zone_id, f.zone_id):
            bf.enter_zone(combat, e, f.zone_id)
            bf.engage(combat, e, f)
            tell(combat, f"{who(e)} comes after {who(f)}, fast and low")
    return story


def advance_step(combat: Combat, f: Fighter, target: Fighter | None) -> str:
    """The free step toward the fight that comes with an action (the movement law). The slow have no free step: for them, moving is
    the action (the caller checks). Returns the story, '' when there was nothing to close."""
    from engine import battlefield as bf
    from engine import combat_perks
    if target is None or f.pace == "slow" or combat_perks.pinned(combat, f):
        return ""
    before = f.zone_id
    story = bf.approach(combat, f, target, hard_ok=False)
    return story if (story or f.zone_id != before) else ""


def act_move(combat: Combat, f: Fighter, how: str, target: Fighter | None) -> None:
    from engine import battlefield as bf
    f.move_round = combat.round
    field = combat.battlefield
    if how == "high_ground":
        here = field.zones.get(f.zone_id) if field else None
        high = next((z for z in field.adjacent(f.zone_id) if field.zones[z].has("elevated")), None) if field else None
        if here is not None and here.has("elevated"):
            bf.gain(f, "elevated")
        elif high:
            bf.enter_zone(combat, f, high)
        else:
            combat.log.append(f"{f.name} looks for high ground, but there is none here")
            tell(combat, f"{who(f)} {vb(f, 'look', 'looks')} for higher ground, but this place offers none")
            return
        combat.log.append(f"{f.name} takes the high ground")
        tell(combat, f"{who(f)} {vb(f, 'scramble', 'scrambles')} up to higher ground")
    elif how == "back":
        story = retreat(combat, f, random.Random(combat.round * 7919 + len(combat.log)))
        combat.log.append(f"{f.name} falls back")
        tell(combat, f"{who(f)} {story}")
    else:
        tgt = target or (bf.closest(combat, f, combat.enemies()) if combat.enemies() else None)
        if tgt is not None:
            story = bf.approach(combat, f, tgt) or "presses in"
            combat.log.append(f"{f.name} closes in")
            tell(combat, f"{who(f)} {story}")


def flee_chance(combat: Combat) -> float:
    fr = RULES["flee"]
    p = combat.player
    enemies = combat.enemies()
    if not enemies:
        return 100
    from engine import battlefield as bf
    pressed = "engaged" if bf.engaged(combat, p) else ("near" if any(e.zone_id == p.zone_id for e in enemies) else "far")
    their_dex = sum(e.attrs.get("dexterity", 10) for e in enemies) / len(enemies)
    mine = p.attrs.get("dexterity", 10)
    chance = fr["base"] + fr["band"][pressed] + fr["dexterity_spread"] * (mine - their_dex) / max(1, mine + their_dex)
    if not combat.player_acted:
        first = fr.get("first_action_engaged" if pressed == "engaged" else "first_action", chance)
        chance = max(chance, first)
    pm = mechanics(p, combat)
    if "lightfoot" in pm:
        chance += 30
    if "shadowmantle" in pm:
        if not bf.engaged(combat, p):
            return 95
        chance += pm["shadowmantle"]
    return max(5, min(95, chance))


def act_flee_blocked(combat: Combat, why: str) -> None:
    """A flight that cannot work (the scripted troll): the attempt is made and costs the round, and fails."""
    combat.log.append(f"{combat.player.name} tries to flee but cannot get away")
    tell(combat, why)


def act_flee(combat: Combat, rng: random.Random) -> bool:
    if "frostwelded" in combat.player.statuses:
        combat.log.append(f"{combat.player.name} cannot flee: frozen to the ground")
        tell(combat, "your feet are frozen to the ground - there is no running")
        return False
    chance = flee_chance(combat)
    if rng.uniform(0, 100) < chance:
        from engine import battlefield as bf
        bf.release(combat, combat.player)
        combat.log.append(f"{combat.player.name} breaks away and escapes")
        tell(combat, "you break away and run, and this time nothing catches you")
        combat.over = "fled"
        return True
    combat.log.append(f"{combat.player.name} tries to flee but is cut off")
    tell(combat, "you try to break away, but you are cut off")
    return False


def mentor_script(combat: Combat, rng: random.Random) -> None:
    """The scripted troll, end of each round before she strikes. Round one: its blow lands on her, a recorded blow that takes about two
    fifths of her health (the player is told to give her a draught). Round two: she guards the player. After that she waits for the player's
    order to attack (see mentor_strikes); if she is ordered to guard she guards."""
    m = combat.mentor_ally
    if not combat.mentor_troll or m is None or combat.mentor_struck or not combat.player.alive or not m.alive:
        return
    troll = next(iter(combat.enemies()), None)
    if combat.mentor_phase == 0 and troll is not None:
        tell(combat, combat.mentor_hurt_line or f"the troll's blow lands on {m.name}, not on you")
        probe = raw_damage(troll, 1.0, active_triggers(troll, combat, m), random.Random(0), steady=True)
        one, _ = mitigate(m, probe, troll.damage_type, troll.level, combat, troll)
        held, troll.always_miss = troll.always_miss, False
        apply_damage(combat, troll, m, max(0.1, m.max_hp * 0.4 / max(1.0, one)), "smashes", rng, can_cleave=False, can_riposte=False, can_flurry=False, reliable=True)
        troll.always_miss = held
    elif combat.mentor_phase == 1:
        m.order = "guard"
        combat.log.append(f"{m.name} guards {combat.player.name}")
        tell(combat, combat.mentor_guard_line or f"{m.name} guards you")
    elif combat.mentor_phase >= 2:
        combat.mentor_stalls += 1
        if m.order == "guard":
            combat.log.append(f"{m.name} guards {combat.player.name}")
            tell(combat, f"{m.name} holds her guard in front of you, waiting on your word")
        return
    combat.mentor_phase += 1


def mentor_strikes(combat: Combat, rng: random.Random) -> None:
    """The round after she steps in, once the player has given their command: her blow, before the troll can act. A real blow, rolled and
    recorded like any other, that never misses; she swings again if the first somehow leaves it standing."""
    m = combat.mentor_ally
    if m is None or combat.mentor_phase < 2 or combat.mentor_struck or not combat.player.alive:
        return
    if m.order != "focus" and combat.mentor_stalls < 3:        # she strikes on the order to attack (or after three rounds of waiting, so it cannot stall)
        return
    combat.mentor_struck = True
    if combat.mentor_strike_line:
        tell(combat, combat.mentor_strike_line)
    for e in combat.enemies():
        e.always_miss = False
        for _ in range(8):
            apply_damage(combat, m, e, 1.0, "strikes", rng, reliable=True)
            if not e.alive:
                break


def bring_allies(combat: Combat) -> None:
    """A party that held back reaches the fight."""
    if not combat.ally_reserves or combat.round < combat.ally_arrive:
        return
    came = combat.ally_reserves
    combat.ally_reserves = []
    for a in came:
        enters(combat, a)
    names = ", ".join(a.name for a in came)
    combat.log.append(f"the party arrives: {names}")
    tell(combat, f"{names} burst{'s' if len(came) == 1 else ''} in from outside, answering the alarm")


def muster(combat: Combat) -> bool:
    """Bring up the next wave from the reserves, at a distance. Returns True if anyone came."""
    if not combat.reserves:
        return False
    wave = [combat.reserves.pop(0) for _ in range(min(combat.reinforce_count, len(combat.reserves)))]
    for f in wave:
        f.starts_far = True
        enters(combat, f)
    names = ", ".join(f.name for f in wave)
    combat.log.append(f"reinforcements: {names}")
    tell(combat, f"{len(wave)} more come running from the rest of the camp, drawn by the noise ({names})"
         + (f"; {len(combat.reserves)} still to come" if combat.reserves else ""))
    return True


# ---------- turn order and AI ----------

def start_turn(f: Fighter, combat: Combat | None = None, rng: random.Random | None = None) -> bool:
    """Tick statuses at the start of a fighter's turn. Returns False if they lose the turn."""
    fm = mechanics(f, combat)
    f.attacked_since_turn = False
    f.defending = 0
    f.counter_move = {}                                 # a readied counter lasts until your own next turn
    f.covering = ""
    if f.shadow and combat is not None:
        from engine import movement
        movement.on_turn_start(combat, f)               # Shadowmark: the shadow pulls its owner home when the time is up
    if combat is not None:
        from engine import combat_perks as _cp
        _cp.on_turn_start(combat, f)
    if "exposed" in f.position_tags:
        f.position_tags.remove("exposed")
    if f.side == "player" and f.alive and f.max_stamina and combat is not None and combat.round > 1:
        f.stamina = min(f.max_stamina, f.stamina + pools.reference_pool("stamina", f.level) * RULES["momentum"]["round"] / 100)
    if f.buffs and combat is not None:
        for bid, b in list(f.buffs.items()):
            if b.get("kind") != "stance":
                continue
            if "stancework" in fm:
                continue                                   # trained stancework: holding it costs nothing
            pool = pools.reference_pool("stamina", f.level) if f.side == "player" else max(1, f.max_stamina)
            keep = pool * RULES["stance"]["upkeep_percent"] / 100
            if f.stamina < keep:
                f.buffs.pop(bid)
                combat.log.append(f"{f.name}'s {b['name']} falters: no stamina left to hold it")
                tell(combat, f"{whose(f)} {b['name']} falters - there is nothing left to hold it with")
            else:
                f.stamina -= keep
        from engine import relics
        from engine import healing as _heal
        _heal.on_turn_start(combat, f)
        relics.tick(combat, f)
    if "unyielding" in fm:
        f.statuses.pop("stunned", None)
        f.statuses.pop("prone", None)
    if "regeneration" in fm and f.alive:                 # unraveled, it hurts instead (restore, f263)
        withered = 0.5 if "withered" in f.statuses else 1.0           # necrotic harm sours regeneration too (engine/healing.py)
        restore(combat, f, max(1, round(f.max_hp * fm["regeneration"] / 100 * withered)))
    from engine import combat_perks
    from engine import afflictions
    if combat is not None:
        from engine import spellcraft
        spellcraft.zone_turn(combat, f, rng)              # burning, charged or poisoned ground (engine/spellcraft.py)
        if f.curses:
            spellcraft.curse_turn(combat, f, rng)
        if f.charging and f.alive and spellcraft.release(combat, f, rng):
            f.counters["cast_turn"] = 1                   # the charged spell was this whole turn (released, or broken)
    if combat is not None and f.alive:
        from engine import spellcraft as _sct
        _sct.turn_effects(combat, f, rng)                 # frostbite, creeping corrosion, a seed about to burst (f268)
    for dot in ("poisoned", "burning"):                  # an open wound does nothing by itself: blows make it bleed (engine/afflictions.py)
        if dot in f.statuses:
            floor = 1 if (combat is not None and ((combat.mentor and f.side == "player") or combat.duel)) else 0       # the first hunt cannot kill the player; a duel kills no one
            from engine import spellcraft as _sck
            f.hp = max(floor, f.hp - combat_perks.dot_damage(f, dot, round(afflictions.tick(f, dot) * _sck.tick_mult(f, dot))))
            if combat is not None:
                _sck.on_tick(combat, f, dot)
            if combat is not None and combat.duel and f.hp <= 1 and not combat.over:
                combat.over = "defeat" if f.side == "player" else "victory"
    if not f.alive and combat is not None and f.side == "enemy":
        combat_perks.on_dot_death(combat, f)
        from engine import spellcraft as _scd
        _scd.on_death(combat, f, None)
        return False
    skip = "stunned" in f.statuses or "petrified" in f.statuses or bool(f.counters.get("cast_turn"))
    if "prone" in f.statuses and not skip:
        f.statuses.pop("prone")
        skip = True
    for s in list(f.statuses):
        if combat is not None and combat_perks.withering_holds(combat, f, s):
            continue                                     # Withering: it does not wear off while its maker stands near
        f.statuses[s] -= 1
        if f.statuses[s] <= 0:
            if s == "poisoned" and f.poison_fixed:        # Persistent Toxin (f268): the timed stacks fade, the fixed ones stay
                f.statuses[s], f.poison = 1, []
                continue
            f.statuses.pop(s)
            combat_perks.on_status_end(f, s)
    for k in list(f.cooldowns):
        f.cooldowns[k] -= 1
        if f.cooldowns[k] <= 0:
            f.cooldowns.pop(k)
    return f.alive and not skip


FLEE_CHANCE_PASSIVE = {"engaged": 0.2, "near": 0.4, "far": 0.6}   # startled animals don't run in the first round


def _pressed(combat: Combat, e: Fighter) -> str:
    """How hard this fighter is pressed: engaged, near (hostiles in their zone) or far."""
    from engine import battlefield as bf
    if bf.engaged(combat, e):
        return "engaged"
    return "near" if any(bf.hostile(e, o) for o in bf.standing(combat, e.zone_id)) else "far"


def enemy_turn(combat: Combat, e: Fighter, rng: random.Random) -> None:
    if e.counters.get("turned") and e.counters.get("turned_until") is not None and e.counters["turned_until"] < combat.round:
        e.counters.pop("turned", None)                 # Dominate (f268) wears off
        e.counters.pop("turned_until", None)
        tell(combat, f"the will on {who(e)} lifts, and it remembers its own side")
    if "numb_hands" in e.statuses and e.reach == "ranged":
        held_reach = e.reach
        e.reach = "melee"                              # Numb Hands (f268): it cannot draw or throw, so it comes in swinging
        try:
            return enemy_turn(combat, e, rng)
        finally:
            e.reach = held_reach
    if e.counters.get("turned"):                     # Dread Regent: it fights its old side now
        from engine import combat_perks
        if start_turn(e, combat, rng):
            combat_perks.turned_turn(combat, e, rng)
        return
    if "unaware" in e.statuses:                      # caught by surprise: the first round is the player's alone
        e.statuses.pop("unaware")
        combat.log.append(f"{e.name} is caught unaware")
        tell(combat, f"{who(e)} has not yet understood what is happening")
        return
    if e.boss:
        from engine import bosses
        bosses.refresh(e)
    if not start_turn(e, combat, rng):
        if e.alive and not e.counters.pop("cast_turn", None):
            combat.log.append(f"{e.name} loses its turn")
            tell(combat, f"{who(e)} reels, unable to act")
        return
    pinned = {"slowed", "stunned", "prone", "grappled"} & set(e.statuses)
    if e.temperament == "passive" and combat.round > 1 and not pinned and not combat.gentle and \
            rng.random() < FLEE_CHANCE_PASSIVE.get(_pressed(combat, e), 0.4):
        e.fled = True
        from engine import battlefield as bf
        bf.release(combat, e)
        combat.log.append(f"{e.name} bolts and escapes")
        tell(combat, f"{who(e)} bolts for the trees and is gone")
        return
    if e.winding:
        resolve_telegraph(combat, e, rng)
        return
    targets = [combat.player] + combat.allies()
    targets = [t for t in targets if t.alive]
    if not targets:
        return
    held = mechanics(combat.player, combat)
    bulwark = ("bulwark" in held or "taunt" in held) and combat.player.alive      # taunt: Distract draws every enemy onto you
    target = combat.player if bulwark or rng.random() < 0.7 or len(targets) == 1 else rng.choice(targets[1:])
    from engine import combat_perks
    from engine import healing as _heal
    decided = combat_perks.pick_target(combat, e, targets, rng)             # a perk may decide it outright (Provoke, Pack Alpha)
    target = decided or _heal.attention_target(combat, e, rng) or target    # else healing draws the eye
    guards = [t for t in targets[1:] if t.order == "guard" and t.alive]
    if target is combat.player and guards and rng.random() < GUARD_CHANCE:
        target = rng.choice(guards)
        combat.log.append(f"{target.name} steps in front of {combat.player.name}")
        tell(combat, f"{who(target)} {vb(target, 'step', 'steps')} into the blow meant for you")
    from engine import summons as _sm
    if target is combat.player and "concealed" in target.position_tags:
        seen = [t for t in targets[1:] if t.alive]
        if seen:
            target = rng.choice(seen)                     # hidden: they go for someone they can see
        elif target.counters.get("vanished_round") == combat.round:
            combat.log.append(f"{e.name} searches but cannot find {target.name}")
            tell(combat, f"{who(e)} {vb(e, 'cast', 'casts')} about for you, but you are nowhere to be seen")   # the vanish buys one clean turn
            return
    target = _sm.redirect(combat, e, target, rng)          # a decoy draws the eye; a sentinel takes its caster's blows
    cover = coverer_for(combat, target)
    if cover is not None:
        tell(combat, f"{who(cover)} {vb(cover, 'take', 'takes')} the blow meant for {who(target)}")
        target = cover
    if "befuddled" in e.statuses:                    # its attack goes wide: at a random fighter, friend or foe
        e.statuses.pop("befuddled")
        mix = [f for f in combat.fighters if f.alive and f is not e and not f.fled]
        if mix:
            target = rng.choice(mix)
            combat.log.append(f"{e.name} is befuddled and turns on {target.name}")
            tell(combat, f"{who(e)} lashes out blindly at {who(target)}")
            if target.side == e.side:
                apply_damage(combat, e, target, 1.0, f"attacks ({e.weapon_name})", rng)
                return
    if "frightened" in e.statuses and _pressed(combat, e) != "engaged" and "grappled" not in e.statuses:
        combat.log.append(f"{e.name} hangs back, afraid")
        tell(combat, f"{who(e)} hangs back, afraid to come closer")
        return
    from engine import behaviors
    if behaviors.pre_turn(combat, e, target, rng):
        behaviors.after_turn(combat, e, rng)
        return
    from engine import battlefield as bfd
    mult, why = behaviors.attack_mult(combat, e, target)
    access = bfd.attack_access(combat, e, target)
    if access.ok and e.reach not in ("ranged", "area") and e.zone_id == target.zone_id:
        bfd.engage(combat, e, target)
    if not access.ok:
        if not access.can_approach:
            fallback = next((t for t in targets if bfd.attack_access(combat, e, t).ok), None)
            if fallback is None:
                combat.log.append(f"{e.name} is {access.why}")
                tell(combat, f"{who(e)} {vb(e, 'are', 'is')} {access.why}")
                return
            target = fallback                             # held at the line: it turns on whoever holds it
            if e.reach not in ("ranged", "area"):
                bfd.engage(combat, e, target)
        else:
            before = e.zone_id
            from engine import combat_perks as _cp
            story = ("" if _cp.pinned(combat, e) else bfd.approach(combat, e, target, hard_ok=False)) or ""   # the free step (none when pinned)
            crossed = e.zone_id != before
            if not story and not crossed:
                story = bfd.approach(combat, e, target) or "closes in"     # then the action itself goes to covering ground
                combat.log.append(f"{e.name} {story}")
                tell(combat, f"{who(e)} {story}")
                return
            combat.log.append(f"{e.name} {story}")
            tell(combat, f"{who(e)} {story}")
            if story == bfd.BREACH:                                        # slipping the line is the action: the blow waits
                return
            if not bfd.attack_access(combat, e, target).ok:
                if e.pace != "slow":
                    more = bfd.approach(combat, e, target)                 # the free step and the action both go to covering ground
                    if more:
                        combat.log.append(f"{e.name} keeps coming")
                        tell(combat, f"{who(e)} keeps coming" + (f" - {more}" if more != bfd.BREACH else ", and slips past the line"))
                return
            if e.pace == "slow" and crossed:                               # the slow arrive, and the blow waits for the next round
                return
            if e.reach not in ("ranged", "area"):
                bfd.engage(combat, e, target)
            if crossed and behaviors.closes_and_strikes(e):
                mult *= behaviors.charge_bonus(e)
                tell(combat, f"{who(e)} does not slow, and strikes as it arrives")
    if behaviors.sweeps(combat, e, rng):
        return
    if telegraphs(e) and bfd.attack_access(combat, e, target).ok and \
            rng.random() < (1.0 if behaviors.beh(e, "relentless") else RULES["telegraph"]["chance"]):
        e.winding = {"target": target.id, "round": combat.round}
        combat.log.append(f"{e.name} winds up a great blow at {target.name}")
        tell(combat, f"{who(e)} {vb(e, 'draw', 'draws')} back for a crushing blow at {who(target)} - it lands next round unless something answers it")
        return
    if why:
        tell(combat, f"{who(e)} " + ", ".join(why))
    from engine import spellcraft as _sce
    if _sce.blocked_attack(e, e.reach):
        act_defend(combat, e)                          # Tangled Arms (f268): it cannot swing, so it guards
        tell(combat, f"{who(e)} cannot bring its arms to bear, and guards instead")
        behaviors.after_turn(combat, e, rng)
        return
    landed = apply_damage(combat, e, target, mult, f"attacks ({e.weapon_name})", rng)
    behaviors.after_hit(combat, e, target, landed, rng)
    behaviors.after_turn(combat, e, rng)
    if e.boss and e.alive and combat.player.alive:
        from engine import bosses
        bosses.own_turn(combat, e, target if target.alive else combat.player, rng)


def telegraphs(e: Fighter) -> bool:
    """Heavy hitters wind up their big blow a round early: elites and anything Huge and up. Set-piece bosses have their own legendary
    actions and do not use this."""
    return not e.boss and (e.rank == "elite" or e.size in ("Huge", "Gargantuan"))


def coverer_for(combat: Combat, target: Fighter) -> Fighter | None:
    """Whoever has put themselves between this fighter and the blow (interpose), standing and in the same zone."""
    return next((x for x in [combat.player] + combat.allies()
                 if x.covering == target.id and x is not target and x.alive and x.zone_id == target.zone_id
                 and not ({"stunned", "prone"} & set(x.statuses))), None)


def resolve_telegraph(combat: Combat, e: Fighter, rng: random.Random) -> None:
    """The wound-up blow lands, or finds air: gone if the target is down or out of reach (they read it and were not there - the brute
    is left open), taken by whoever interposed, otherwise it falls at full weight."""
    from engine import battlefield as bf
    wound = e.winding
    e.winding = {}
    t = combat.get(wound.get("target", ""))
    if t is None or not t.alive or t.fled:
        leave_open(combat, e)
        combat.log.append(f"{e.name}'s great blow finds nothing")
        tell(combat, f"the blow {who(e)} wound up falls on empty ground - {who(e)} {vb(e, 'are', 'is')} left open")
        return
    cover = coverer_for(combat, t)
    if cover is not None:
        tell(combat, f"{who(cover)} {vb(cover, 'step', 'steps')} into the blow meant for {who(t)}")
        t = cover
    stepped_out = t.move_round >= wound.get("round", -9) and t.id not in e.engaged_with \
        and (t.pace != "slow" or "read_the_wind" in mechanics(t, combat))
    if stepped_out or not bf.attack_access(combat, e, t).ok:
        leave_open(combat, e)
        combat.log.append(f"{e.name}'s great blow finds air: {t.name} is not there")
        tell(combat, f"the great blow falls where {who(t)} stood a moment ago and finds air - {who(e)} {vb(e, 'are', 'is')} wide open")
        return
    if e.reach not in ("ranged", "area"):
        bf.engage(combat, e, t)
    tell(combat, f"the wound-up blow comes down on {who(t)} with everything behind it")
    apply_damage(combat, e, t, RULES["telegraph"]["multiplier"], "brings the great blow down on", rng, can_cleave=False)


def act_interpose(combat: Combat, f: Fighter, ally: Fighter | None) -> None:
    """Stand between a declared threat and an ally: until your next turn, blows aimed at them land on you, through your stance."""
    from engine import battlefield as bf
    if ally is None or ally is f or ally.zone_id != f.zone_id:
        combat.log.append(f"{f.name} looks to cover someone, but there is nobody there to cover")
        tell(combat, f"{who(f)} {vb(f, 'move', 'moves')} to shield an ally, but there is no one in reach to shield")
        return
    f.covering = ally.id
    combat.log.append(f"{f.name} interposes: blows meant for {ally.name} land on them")
    tell(combat, f"{who(f)} {vb(f, 'plant', 'plants')} {'yourself' if f.side == 'player' else 'itself'} between {who(ally)} and whatever comes")


ORDERS = ("focus", "guard", "hold", "heal", "back")     # (f406) back: behind the player, in the back row, acting from there
GUARD_CHANCE = 0.4          # an enemy that would strike the player strikes a guarding ally instead this often


def give_order(combat: Combat, ally: Fighter, kind: str, target_id: str = "", same_command: bool = False) -> str:
    """The player's one free order a turn to an ally. '' if given; else why not. (f383) The same allies told again this turn is a
    correction and replaces the order (a misread order could not be put right); another ally waits for the next turn. same_command: the
    rest of the party given one order together."""
    if kind not in ORDERS:
        return "That is not an order they know."
    if not ally.alive or ally.fled or ally not in combat.fighters:
        return f"{ally.name} is not in the fight."
    if combat.order_round != combat.round:
        combat.ordered = []
    if combat.order_round == combat.round and combat.round and ally.id not in combat.ordered and not same_command:
        return "You have already given an order this turn."
    if kind == "heal" and not (ally.ally_role == "priest" or ally.can_heal):
        return f"{ally.name} has no healing to give."
    if kind == "hold" and ally.ally_role == "mentor":
        return f"{ally.name} is not about to stand back from that."
    if kind == "focus":
        t = next((e for e in combat.enemies() if e.id == target_id), None)
        if not t:
            return "There is nothing there for them to take."
        ally.order_target = t.id
    elif kind == "heal":
        ally.order_target = target_id if target_id == "self" or any(x.id == target_id for x in combat.allies()) else ""
    elif kind == "back":                                 # (f406) "get behind me": out of the press, into the back row
        from engine import battlefield as bf
        bf.release(combat, ally)
        bf.to_row(combat, ally, "back")
    ally.order = kind
    combat.order_round = combat.round
    if ally.id not in combat.ordered:
        combat.ordered.append(ally.id)
    return ""


def ally_turn(combat: Combat, a: Fighter, rng: random.Random) -> None:
    from engine import combat_perks
    if a.ally_role == "mentor" and combat.mentor_troll and not combat.mentor_struck:
        return                                   # she is in the scripted fight and acts only as the script says
    if not start_turn(a, combat, rng):
        a.counters.pop("cast_turn", None)
        return
    if a.summon_form:
        from engine import summons
        if summons.turn(combat, a, rng):
            return                                        # its form took the turn (a totem's pulse, a decoy, its time running out)
    if a.order == "hold":
        combat.log.append(f"{a.name} holds back")
        tell(combat, f"{who(a)} {vb(a, 'hold', 'holds')} back, as told")
        return
    if a.flaw == "fair_weather" and not a.flaw_used and a.hp < a.max_hp * 0.5 and any(e.level >= combat.player.level for e in combat.enemies()):
        from engine import quirks
        F = quirks.Q["flaws"]["fair_weather"]
        if rng.randrange(100) < F["chance"]:
            a.flaw_used = True
            combat.log.append(f"{a.name} hangs back")
            tell(combat, F["line"].format(name=a.name.split()[0]))
            return
    from engine import techniques
    if a.order == "heal":
        whom = a if a.order_target == "self" else next((x for x in combat.allies() if x.id == a.order_target and x.alive), combat.player)
        hurt = whom if whom.alive and whom.hp < whom.max_hp else None          # (f406) "heal yourself", "heal Bryn": the one named
        kit_heal = techniques.healing(a.ally_role)
        if hurt and kit_heal:                                      # (f396) told to heal: their own heal, every turn they are told to
            m = techniques.spell(a, kit_heal)
            if m is not None:
                a.cooldowns.pop(m.id, None)                        # (f400) told to: every turn, for as long as their mana lasts
            if techniques.cast_heal(combat, a, kit_heal, hurt, rng):
                return
        if hurt and (a.ally_role == "priest" or a.can_heal):
            amount = hurt.max_hp * RULES["ally_heal"]["pct"] / 100 * 1.5
            amount, _ = combat_perks.mend(combat, a, hurt, amount)        # one path for every heal: withering and perks apply
            a.counters["healed_round"] = combat.round              # healing draws the eye
            combat.log.append(f"{a.name} heals {hurt.name} for {round(amount)}")
            tell(combat, f"{who(a)} {vb(a, 'tend', 'tends')} {who(hurt)}, and the wounds close")
            return
    if techniques.kit(a.ally_role) and a.order != "focus" and techniques.support(combat, a, rng):
        return                                                     # (f396) a heal, a blessing or a shield, on their own judgement
    if a.ally_role == "priest" and "heal" not in a.cooldowns and not techniques.healing(a.ally_role):
        hurt = [f for f in [combat.player] + combat.allies() if f.alive and f.hp < f.max_hp * RULES["ally_heal"]["below"]]
        if hurt:
            t = min(hurt, key=lambda f: f.hp / f.max_hp)
            amount = t.max_hp * RULES["ally_heal"]["pct"] / 100
            amount, _ = combat_perks.mend(combat, a, t, amount)        # one path for every heal: withering and perks apply
            a.counters["healed_round"] = combat.round              # healing draws the eye
            a.cooldowns["heal"] = RULES["ally_heal"]["cooldown"] + 1
            combat.log.append(f"{a.name} heals {t.name} for {round(amount)}")
            tell(combat, f"{who(a)} {vb(a, 'lay', 'lays')} hands on {who(t)}, and the wounds close a little")
            return
    enemies = combat.enemies()
    if enemies:
        ordered = next((e for e in enemies if e.id == a.order_target), None) if a.order == "focus" else None
        target = ordered or next((e for e in enemies if e.id == combat.focus), None) or min(enemies, key=lambda e: e.hp)
        from engine import battlefield as bf
        access = bf.attack_access(combat, a, target)
        if a.order == "back":                                      # (f406) told to keep behind the player: they go to no one
            near = [e for e in enemies if e.id in a.engaged_with] or [e for e in enemies if bf.attack_access(combat, a, e).ok
                                                                       and a.reach in ("ranged", "area")]
            if not near:
                combat.log.append(f"{a.name} keeps behind {combat.player.name}")
                tell(combat, f"{who(a)} {vb(a, 'keep', 'keeps')} behind {who(combat.player)}, as told")
                return
            target, access = near[0], bf.attack_access(combat, a, near[0])
        if not access.ok:
            reachable = next((e for e in enemies if bf.attack_access(combat, a, e).ok), None)
            if reachable is None and access.can_approach:
                story = bf.approach(combat, a, target) or "closes in"
                combat.log.append(f"{a.name} {story}")
                tell(combat, f"{who(a)} {story}")
                return
            target = reachable or target
        if a.reach not in ("ranged", "area") and a.zone_id == target.zone_id and a.order != "back":
            bf.engage(combat, a, target)
        inspire = mechanics(combat.player, combat).get("inspire", 0)
        if techniques.offence(combat, a, target, 1.0 + inspire / 100, rng):
            return                                                 # (f396) a technique of their own at the foe in reach
        apply_damage(combat, a, target, 1.0 + inspire / 100, "attacks", rng)


def _legendary(combat: Combat, rng: random.Random) -> None:
    if combat.player.alive and any(e.boss for e in combat.enemies()):
        from engine import bosses
        bosses.legendary(combat, rng)


def finish_round(combat: Combat, rng: random.Random) -> None:
    """Everyone except the player acts, then the round advances."""
    if combat.duel and combat.over:
        combat.round += 1
        return
    mentor_strikes(combat, rng)
    _legendary(combat, rng)                    # a boss acts at the end of the player's turn
    for a in combat.allies():
        ally_turn(combat, a, rng)
        _legendary(combat, rng)
    for e in sorted(combat.enemies(), key=lambda x: -x.attrs.get("dexterity", 10)):
        if combat.player.alive and not (combat.duel and combat.over):
            enemy_turn(combat, e, rng)
            _legendary(combat, rng)
    for e in [f for f in combat.fighters if f.side == "enemy" and f.alive and not f.fled and f.counters.get("turned")]:
        enemy_turn(combat, e, rng)                     # Dread Regent: the turned fight their old side
    mentor_script(combat, rng)
    bring_allies(combat)
    p = combat.player
    if p.alive and combat.reserves and combat.round >= combat.reinforce_from and combat.round % combat.reinforce_every == 0:
        muster(combat)
    if not p.alive:
        combat.over = "defeat"
    elif not combat.enemies() and not muster(combat):
        combat.over = "victory"
    combat.round += 1


def player_ai(combat: Combat, rng: random.Random) -> None:
    """A sensible automatic player, used by the danger estimate and the balance simulator."""
    p = combat.player
    if not start_turn(p, combat, rng):
        p.counters.pop("cast_turn", None)
        return
    enemies = combat.enemies()
    from engine import battlefield as bf
    target = min(enemies, key=lambda e: (0 if bf.attack_access(combat, p, e).ok else 1,
                                         combat.battlefield.steps(p.zone_id, e.zone_id) if combat.battlefield else 0, e.hp))
    usable = [m for m in p.moves if m.effect == "damage" and not can_use(p, m, combat)]
    usable.sort(key=lambda m: -RULES["damage"]["multiplier"][m.tier])
    if usable and (in_reach(p, target, usable[0].reach) or usable[0].reach == "area"):
        act_ability(combat, p, usable[0], target, rng)
    else:
        act_attack(combat, p, target, rng)
    if not combat.enemies() and not muster(combat):
        combat.over = "victory"


def ensure_field(fight: Combat) -> None:
    """A fight that was built bare (a danger estimate, a tool, a practice bout) gets plain ground, so the same spatial law runs
    everywhere and an estimate can never disagree with the fight it estimates."""
    if fight.battlefield is None:
        from engine import battlefield_builder
        from engine import battlefield as bf
        fight.battlefield = battlefield_builder.duel_ground()
        bf.place_fighters(fight)


def simulate(combat: Combat, rng: random.Random, max_rounds: int = 60) -> Combat:
    c = copy.deepcopy(combat)
    ensure_field(c)
    if not c.opened:
        opening(c, rng)
    while not c.over and c.round <= max_rounds:
        player_ai(c, rng)
        if not c.over:
            finish_round(c, rng)
    if not c.over:
        c.over = "stalemate"
    return c


def danger(combat: Combat, runs: int = 80, seed: int = 0) -> tuple[str, float]:
    """Estimate the fight by simulating it. Returns (label, win rate)."""
    rng = random.Random(seed)
    wins = sum(simulate(combat, rng).over == "victory" for _ in range(runs))
    rate = wins / runs
    if rate >= 0.97:
        label = "trivial"
    elif rate >= 0.8:
        label = "favorable"
    elif rate >= 0.55:
        label = "even"
    elif rate >= 0.25:
        label = "dangerous"
    else:
        label = "deadly"
    return label, rate


def prebuff(combat: Combat, ids: list[str], rng: random.Random) -> list[str]:
    """A fight the player starts themselves: the combat buffs they chose (#prebuff) go up before the first blow - paid for in full,
    on cooldown as usual, and one round shorter for the time it took. Returns the notes for the player."""
    p, notes = combat.player, []
    for mid in ids or []:
        move = next((m for m in p.moves if m.id == mid and m.effect == "buff"), None)
        if move is None:
            continue
        why = can_use(p, move, combat)
        if why:
            notes.append(f"No time for {move.name}: {why}")
            continue
        _act_ability(combat, p, move, None, rng, None, False)
        b = p.buffs.get(move.id)
        if b:
            b["rounds"] = max(1, b["rounds"] - 1)
        notes.append(f"Before the first blow you cast {move.name}.")
    return notes


def can_surprise(f) -> bool:
    """Whether this fighter can be caught unaware at all: a boss never is."""
    return not f.boss and f.rank != "boss"


def surprise(combat: Combat) -> list:
    """The player got close unseen: every enemy that can be surprised is caught unaware. Returns those caught."""
    caught = [e for e in combat.enemies() if can_surprise(e)]
    for e in caught:
        e.statuses["unaware"] = 1
    return caught


def opening(combat: Combat, rng: random.Random) -> None:
    """Everything that happens as a fight begins: barriers, rallies, war cries, dread."""
    combat.opened = True
    p = combat.player
    for e in combat.enemies():
        if "unaware" in e.statuses and not can_surprise(e):      # a boss is never caught off its guard (f248)
            e.statuses.pop("unaware")
            tell(combat, f"{who(e)} was never off its guard")
    pm = mechanics(p, combat)
    if "barrier" in pm:
        p.shield += p.max_hp * pm["barrier"] / 100
        tell(combat, "a barrier shimmers into being around you (Barrier)")
    if "rally" in pm:
        for f in [p] + combat.allies():
            f.shield += p.max_hp * pm["rally"] / 100
        tell(combat, "your voice steels you" + (" and your companions" if combat.allies() else "") + " for what comes (Rally)")
    if any(e.boss for e in combat.enemies()):
        from engine import bosses
        bosses.intro(combat, rng)
    for e in combat.enemies():
        if "fearsome" in pm and e.level < p.level and not resist(p, e, ["charisma", "strength"], rng):
            if add_status(combat, e, "frightened", 2):
                combat.log.append(f"{e.name} quails before you (Fearsome)")
                tell(combat, f"{who(e)} quails at the sight of you (Fearsome)")
        elif "battle_cry" in pm and rng.uniform(0, 100) < pm["battle_cry"]:
            if add_status(combat, e, "frightened", 2):
                combat.log.append(f"{e.name} is shaken by your war cry")
                tell(combat, f"your war cry rolls over {who(e)}, and it falters (Battle Cry)")

