"""The combat engine. Pure rules: no model calls, no printing.

Everything here is deterministic given a random generator, so the same code runs real fights,
the danger estimate shown to the player, and the balance simulator (tools/balance.py).
"""

import copy
import math
import random
from pathlib import Path

import yaml
from pydantic import BaseModel

from core.models import Character
from core.rules import ATTRIBUTES
from engine import ability_traits as AT
from engine import elements, items, pools, stats as _stats

RULES = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "combat.yaml").read_text(encoding="utf-8"))
BANDS = ["engaged", "near", "far"]
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
    uses: int = 0                  # a relic power: how many times a fight (0 = no limit)
    text: str = ""                 # a relic power: what it does, in words (for the ability list)
    relic: dict = {}               # a relic power: its kind and numbers (engine/relics.py)


class Fighter(BaseModel):
    id: str
    name: str
    side: str                      # player | ally | enemy
    level: int
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
    band: str = "near"
    elevated: bool = False
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
    magic_power: float = 0
    adaptive: bool = False
    legendary: dict[str, float] = {}     # legendary effect id -> value
    slays: dict[str, float] = {}         # creature category -> bonus % (dragonslayer etc.)
    ally_role: str = ""                   # a hired party member's role (priests heal)
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
    counters: dict[str, int] = {}        # small per-fight tallies for gear effects (hits in a row, attunement, shrugged-off afflictions...)
    buffs: dict[str, dict] = {}          # timed effects from relic powers: {id: {rounds, mech, drain, collapse}}
    relic_uses: dict[str, int] = {}      # how many times each relic power has been used this fight
    boss: dict = {}                      # set-piece boss state: legendary actions and resistance, phases (engine/bosses.py)

    @property
    def alive(self) -> bool:
        return self.hp > 0

    def best_attr(self, names: list[str]) -> int:
        return max((self.attrs.get(a, 10) for a in names), default=10)


class Combat(BaseModel):
    round: int = 1
    gentle: bool = False           # Gentle Approach: timid animals don't flee
    fighters: list[Fighter]
    log: list[str] = []
    over: str = ""                 # "" | victory | defeat | fled
    place: str = ""
    conditions: list[str] = []     # triggers true for the whole fight: at_night, in_bad_weather, in_swamp...
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
    record: bool = False           # keep a breakdown of every blow (the window's combat log); off while the odds are simulated
    serial: str = ""               # tells this fight's blows apart from another fight's
    hits: list[dict] = []          # this turn's blows: who, how the roll and the damage were worked out, what was dealt

    def get(self, fid: str) -> Fighter | None:
        return next((f for f in self.fighters if f.id == fid), None)

    @property
    def player(self) -> Fighter:
        return next(f for f in self.fighters if f.side == "player")

    def enemies(self) -> list[Fighter]:
        return [f for f in self.fighters if f.side == "enemy" and f.alive and not f.fled]

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


def weapon_phrase(f: Fighter) -> str:
    return f"with {'your' if f.side == 'player' else 'its'} {f.weapon_name}"


def tell(combat: Combat, text: str, rec: dict | None = None) -> None:
    """Add an event to this round's story. A blow's event carries its tag ([h2]) so the narrator can place the figure."""
    if rec is not None:
        text += f" [{rec['tag']}]"
    combat.story.append(text[0].upper() + text[1:])


def new_hit(combat: Combat, att: Fighter, dfn: Fighter, label: str) -> dict | None:
    """Start the record of one blow, or None when blows are not being recorded."""
    if not combat.record:
        return None
    if not combat.serial:
        combat.serial = f"{random.randrange(16 ** 4):04x}"
    n = len(combat.hits) + 1
    rec = {"id": f"{combat.serial}-{combat.round}-{n}", "tag": f"h{n}", "round": combat.round, "att": att.name, "dfn": dfn.name,
           "att_side": att.side, "dfn_side": dfn.side, "label": label, "outcome": "", "chance": 0.0, "roll": 0.0,
           "note": "", "base": {}, "steps": [], "defence": {}, "extras": [], "final": 0, "figure": ""}
    combat.hits.append(rec)
    return rec


def hit_step(rec: dict | None, mult: float, label: str, factor: float) -> float:
    """One multiplier in the damage chain, written into the record as it is applied."""
    if rec is not None and label and abs(factor - 1) > 1e-9:
        rec["steps"].append([label, round(factor, 3)])
    return mult * factor


def figure(rec: dict) -> str:
    out = rec["outcome"]
    if out == "miss":
        return "(miss)"
    if out == "phase":
        return "(passes through)"
    word = {"crit": "critical, ", "graze": "graze, "}.get(out, "")
    return f"({word}{rec['final']} damage)"


# ---------- building fighters ----------

def fighter_from_character(c: Character) -> Fighter:
    weapon = c.equipment.get("main_hand")
    _gear = _stats.gear_attributes(c)
    attrs = {a: _stats.effective(c, a, _gear) for a in ATTRIBUTES}
    armor = ward = 0.0
    penalty = 0
    weights = items.RULES["weight_classes"]
    flags = {"armor_pierce": 0.0, "crit_resist": 0.0, "magic_power": 0.0, "adaptive": False}
    for item in c.equipment.values():
        b = items.base_of(item)
        f = items.flags(item)
        flags["armor_pierce"] += f.get("armor_pierce", 0)
        flags["crit_resist"] += f.get("crit_resist", 0)
        flags["magic_power"] += f.get("magic_power", 0)
        flags["adaptive"] = flags["adaptive"] or bool(f.get("adaptive"))
        if b.is_weapon:
            continue
        v = items.value(item)
        if b.ward:
            ward += v
        else:
            armor += v
            ward += v * f.get("ward_fraction", 0) / 100
        w = items.weight(item)
        if w:
            penalty = min(penalty, weights[w]["evasion"])
    bonuses = [Bonus(modifies=p.modifies.value, trigger=p.trigger.value, magnitude=p.magnitude)
               for p in c.passives if not p.mechanic]
    for item in c.equipment.values():
        bonuses += [Bonus(modifies=e.modifies, trigger=e.trigger, magnitude=e.magnitude, flat=e.flat) for e in items.effects(item)]
    from engine import sets
    bonuses += [Bonus(modifies=e.modifies, trigger=e.trigger, magnitude=e.magnitude, flat=e.flat) for e in sets.effects(c.equipment)]
    legendary, slays, wards = dict(sets.fight(c.equipment)), {}, {}
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
    for p in c.passives:
        m = MECHANICS.get(p.mechanic)
        if not m or m.kind != "combat":
            continue
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
                  resource=a.resource.value, cooldown=a.cooldown,
                  rider=a.rider, shape=a.shape, buff=a.buff, buff_stat=a.buff_stat, command=a.command,
                  attribute=a.attribute or (legacy if a.resource.value == "mana" else ""),
                  element=elements.of_text(f"{a.name} {a.description}")) for a in c.actives] + relics
    if weapon:
        b = items.base_of(weapon)
        wname, wdmg, wattrs, reach, dtype = weapon.name, items.value(weapon), b.attributes, b.reach, b.damage
        if weapon.legendary_effect == "longreach" and reach == "melee":
            reach = "extended"
    else:
        wname, wdmg, wattrs, reach, dtype = "fists", RULES["damage"]["unarmed"], ["strength"], "melee", "physical"
    return Fighter(
        id="player", name=c.name, side="player", level=c.level, attrs=attrs,
        hp=pools.current(c, "health"), max_hp=pools.maximum(c, "health"),
        stamina=pools.current(c, "stamina"), max_stamina=pools.maximum(c, "stamina"),
        mana=pools.current(c, "mana"), max_mana=pools.maximum(c, "mana"),
        weapon_name=wname, weapon_damage=wdmg, weapon_attrs=wattrs, reach=reach, damage_type=dtype,
        armor=armor, ward=ward + attrs["wisdom"] * RULES["mitigation"]["wisdom_ward"],
        evasion_penalty=penalty, bonuses=bonuses, moves=moves,
        armor_pierce=min(90, flags["armor_pierce"]), crit_resist=min(90, flags["crit_resist"]),
        magic_power=flags["magic_power"], adaptive=flags["adaptive"],
        legendary=legendary, slays=slays, wards=wards, conditional=conditional, breath=bool(getattr(c, 'orenna_breath', False)),
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


def fighter_from_creature(creature, level: int, rank: str, fid: str, name: str = "", band: str = "near", late: bool = True) -> Fighter:
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
    attack = next((a for a in creature.attacks), "strike")
    return Fighter(
        id=fid, name=name or creature.name.lower(), side="enemy", level=level, size=creature.size,
        category=creature.category, creature=creature.id, rank=rank, attrs=attrs, hp=max_hp, max_hp=max_hp,
        weapon_name=attack.lower(), weapon_damage=dmg, element=elements.of_creature(creature),
        weapon_attrs=["strength", "dexterity"], reach="ranged" if ranged else "melee",
        damage_type="magical" if magical and ranged else "physical",
        armor=cr["natural_armor"].get(creature.category, 1) * growth(level) * (1 + (late["armor"] * over if late else 0)),
        ward=(2 if magical else 0) * growth(level) + attrs["wisdom"] * RULES["mitigation"]["wisdom_ward"],
        band=band, temperament=creature.temperament,
    )


def companion_fighter(shape, level: int, fid: str, name: str, spirit: tuple[str, str] | None = None, gift: bool = False) -> Fighter:
    """A bonded companion: the creature's stats, strengthened by the companion rule. A summoned spirit passes (tier, role)
    and gets the size of its ability's tier and the build of its role."""
    f = fighter_from_creature(shape, level, "normal", fid, name, "near", late=False)
    sp = RULES["creatures"].get("spirit")
    if spirit and sp:
        tier, role = spirit
        r = sp["role"].get(role, {"health": 1, "damage": 1})
        f.max_hp = f.hp = round(f.max_hp * r["health"])
        f.weapon_damage *= r["damage"]
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
    if f.elevated:
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
    """A bonded companion or summoned spirit (not a hired party member or a risen thrall)."""
    return f.side == "ally" and not f.ally_role and f.id != "thrall"


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
        if le and le.category == target.category and (le.applies == "armor") == (kind == "ward"):
            total += v
    return total


def status_mod(f: Fighter, key: str) -> float:
    return sum(RULES["statuses"].get(s, {}).get(key, 0) for s in f.statuses)


def hit_chance(att: Fighter, dfn: Fighter, combat: Combat) -> float:
    h = RULES["hit"]
    a = att.best_attr(att.weapon_attrs)
    d = dfn.attrs.get("dexterity", 10)
    chance = h["base"] + h["spread"] * (a - d) / max(1, a + d)
    chance += bonus(att, "accuracy", active_triggers(att, combat, dfn))
    chance -= bonus(dfn, "evasion", active_triggers(dfn, combat, att))
    chance -= dfn.evasion_penalty
    chance += status_mod(att, "accuracy") - status_mod(dfn, "evasion")
    if att.elevated and not dfn.elevated:
        chance += RULES["elevated_accuracy"]
    if att.side != "enemy" and att.reach == "ranged" and att.damage_type == "physical" and dfn.band == "engaged":
        chance -= h.get("point_blank", 0)             # a bow is awkward with something already on top of you
    return max(h["min"], min(h["max"], chance))


def roll_attack(att: Fighter, dfn: Fighter, combat: Combat, rng: random.Random, trace: dict | None = None) -> tuple[str, float]:
    """Returns (outcome, chance). outcome: miss | graze | hit | crit."""
    chance = hit_chance(att, dfn, combat)
    r = rng.uniform(0, 100)
    if trace is not None:
        trace["chance"], trace["roll"] = round(chance, 1), round(r, 1)
    if r >= chance:
        return "miss", chance
    c = RULES["crit"]
    dex_a, dex_d = att.attrs.get("dexterity", 10), dfn.attrs.get("dexterity", 10)
    crit = c["base"] + c["dexterity_spread"] * max(0, dex_a - dex_d) / max(1, dex_a + dex_d)
    crit += mechanics(att, combat, dfn).get("killer_instinct", 0)
    crit += bonus(att, "crit_chance", {"always"})
    crit = min(c.get("max", 50), crit)
    crit *= 1 - dfn.crit_resist / 100
    if r < crit:
        return "crit", chance
    if r >= chance - RULES["hit"]["graze_band"]:
        return "graze", chance
    return "hit", chance


def crit_multiplier(att: Fighter) -> float:
    """What a critical hit multiplies damage by: the base, plus the flat percentage points gear adds."""
    return RULES["crit"]["multiplier"] + bonus(att, "crit_damage", {"always"}) / 100


def raw_damage(att: Fighter, multiplier: float, triggers: set[str], rng: random.Random, steady: bool = False,
               trace: dict | None = None) -> float:
    d = RULES["damage"]
    flat = flat_bonus(att, "damage", triggers)
    base = att.weapon_damage + att.best_attr(att.weapon_attrs) * d["attribute_bonus"] + flat
    variance = 1.0 if steady else rng.uniform(1 - d["variance"], 1 + d["variance"])
    magic = 1 + att.magic_power / 100 if att.damage_type == "magical" or att.adaptive else 1
    pct = bonus(att, "damage", triggers)
    if trace is not None:
        trace.update(weapon=round(att.weapon_damage, 1), attr=att.best_attr(att.weapon_attrs), attr_bonus=round(att.best_attr(att.weapon_attrs) * d["attribute_bonus"], 1),
                     flat=round(flat, 1), base=round(base, 1), pct=round(pct, 1), variance=round(variance, 3), magic=round(magic, 3),
                     multiplier=round(multiplier, 3), total=round(base * multiplier * (1 + pct / 100) * variance * magic, 1))
    return base * multiplier * (1 + pct / 100) * variance * magic


def mitigate(dfn: Fighter, amount: float, damage_type: str, attacker_level: int, combat: Combat,
             attacker: Fighter | None = None, trace: dict | None = None) -> tuple[float, float]:
    """Returns (damage taken, damage absorbed)."""
    m = RULES["mitigation"]
    if attacker and attacker.adaptive:
        damage_type = "magical" if dfn.ward < dfn.armor else "physical"
    protection = dfn.ward if damage_type == "magical" else dfn.armor
    if dfn.buffs:
        bw = mechanics(dfn, combat).get("bulwark_ward" if damage_type == "magical" else "bulwark_armor", 0)
        if bw:
            floor = AT.T["bulwark_floor"] * m["armor_k"] * growth(attacker_level)
            protection = max(protection, floor) * (1 + bw / 100)
    protection *= max(0.1, 1 + status_mod(dfn, "protection") / 100)        # Exposing
    am = mechanics(attacker, combat, dfn) if attacker else {}
    if damage_type == "magical" and "wardbreaker" in am:
        protection *= 1 - min(90, am["wardbreaker"]) / 100
    pierce = (attacker.armor_pierce if attacker else 0) + am.get("piercing", 0)
    if pierce and damage_type != "magical":
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
    if dfn.defending:
        after *= 1 - dfn.defending / 100
    cuts.append(["guarding", step - after])
    if trace is not None:
        trace.update(kind=damage_type, protection=round(protection, 1), reduction=round(reduction, 1), defense_pct=round(def_pct, 1),
                     defense_flat=round(def_flat, 1), defending=round(dfn.defending, 1), before=round(amount, 1), after=round(after, 1),
                     cuts=[[n, round(v, 1)] for n, v in cuts if v >= 0.05])
    return after, amount - after


def add_status(combat: Combat, f: Fighter, status: str, rounds: int) -> bool:
    """Apply a status unless a legendary effect prevents it. Returns True if it took hold."""
    fm = mechanics(f, combat)
    if "unyielding" in fm and status in ("stunned", "prone"):
        combat.log.append(f"{f.name} stands firm (Unyielding)")
        tell(combat, f"{who(f)} {vb(f, 'stand', 'stands')} firm, unshaken (Unyielding)")
        return False
    if "earthshaker" in fm and status == "prone":
        return False
    if "iron_will" in fm and status in ("stunned", "prone", "slowed", "frightened", "blinded") \
            and f.counters.get("shrugged", 0) < fm["iron_will"]:
        f.counters["shrugged"] = f.counters.get("shrugged", 0) + 1
        combat.log.append(f"{f.name} shrugs it off (Iron Will)")
        tell(combat, f"{who(f)} {vb(f, 'shrug', 'shrugs')} it off as if it were nothing, and the effort sharpens {whose(f)} resolve (Iron Will)")
        return False
    if "sanctified" in fm and status in ("bleeding", "frightened"):
        combat.log.append(f"{f.name} is untouched by it (Sanctified)")
        tell(combat, f"a holy calm keeps {who(f)} untouched (Sanctified)")
        return False
    if f.boss:
        from engine import bosses
        if bosses.resisted(combat, f, status):
            return False
    f.statuses[status] = rounds
    return True


def resist_factor(dfn: Fighter, damage_type: str, element: str) -> float:
    """How much of an attack gets through the target's resistances: physical or magical, then the element it carries."""
    cap = elements.CAP
    f = 1.0
    for kind in (("physical" if damage_type == "physical" else "magical"), element):
        if kind:
            pct = sum(b.magnitude for b in dfn.bonuses if b.modifies == f"{kind}_resistance" and b.trigger == "always")
            if kind == element:
                pct += sum(b.magnitude for b in dfn.bonuses if b.modifies == "all_elemental_resistance" and b.trigger == "always")
                if dfn.element == element:
                    pct += elements.R.get("native_resist", 0)
            f *= 1 - max(0, min(cap, pct)) / 100
    return f


def take_damage(combat: Combat, dfn: Fighter, amount: float, source: Fighter | None, rng: random.Random,
                damage_type: str = "physical") -> int:
    """Apply final damage to a fighter, with defensive legendary effects. Returns damage actually dealt."""
    L = mechanics(dfn, combat, source)
    if not (source and source.legendary.get("penetrating")):               # Penetrating ignores resistances
        amount *= resist_factor(dfn, damage_type, (source.hit_element or source.element) if source else "")
    if "blood_pact" in L:
        amount *= 1 + L["blood_pact"] / 200
    ward = category_bonus(dfn, L, source, "ward")
    if ward:
        amount *= 1 - min(90, ward) / 100
    if "hardening" in L:
        amount *= 1 - L["hardening"] * min(5, dfn.hardening_stacks) / 100
        dfn.hardening_stacks += 1
    if "aegis" in L and dfn.aegis_round != combat.round:
        dfn.aegis_round = combat.round
        amount *= 1 - L["aegis"] / 100
    if "last_stand" in L and dfn.hp < dfn.max_hp / 4:
        amount *= 0.8
    if "stoneskin" in L:
        amount *= 1 - min(90, L["stoneskin"]) / 100
    if "plating" in L and damage_type == "physical":
        amount *= 1 - min(90, L["plating"]) / 100
    if "spellward" in L and damage_type == "magical":
        amount *= 1 - min(90, L["spellward"]) / 100
    if "unbroken" in L:
        amount = min(amount, dfn.max_hp * L["unbroken"] / 100)
    if dfn.side == "ally":
        guard = mechanics(combat.player, combat).get("guardian", 0)
        amount *= 1 - min(90, guard) / 100
        if is_companion(dfn):
            amount /= 1 + max(0, companion_boost(combat, "companion_durability")) / 100
    if dfn.shield > 0 and amount > 0:
        soaked = min(dfn.shield, amount)
        dfn.shield -= soaked
        amount -= soaked
        tell(combat, f"{whose(dfn)} barrier takes the blow" + (" and shatters" if dfn.shield <= 0 else ""))
    if "mana_shield" in L and amount > 0 and dfn.mana > 1:
        absorbed = min(dfn.mana / 2, amount * min(90, L["mana_shield"]) / 100)
        dfn.mana -= absorbed * 2
        amount -= absorbed
    if amount <= 0:
        return 0
    if "ward_conversion" in L and damage_type == "magical" and dfn.max_mana:
        dfn.mana = min(dfn.max_mana, dfn.mana + amount * L["ward_conversion"] / 100)
    dealt = max(1, round(amount))
    if dealt >= dfn.hp and is_companion(dfn) and "lifeline" in mechanics(combat.player, combat) and not dfn.counters.get("lifeline"):
        dfn.counters["lifeline"] = 1
        dfn.hp = 1
        combat.log.append(f"{dfn.name} should have fallen - the bond holds it to life (Lifeline)")
        tell(combat, f"the blow should have ended {who(dfn)}, but the bond with its master will not let it fall (Lifeline)")
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
    if dfn.yields_at and dfn.alive and not dfn.fled and dfn.hp <= dfn.max_hp * dfn.yields_at:
        dfn.fled = True
        tell(combat, dfn.yield_text or f"{who(dfn)} breaks off and is gone")
    if dfn.boss:
        from engine import bosses
        bosses.after_damage(combat, dfn)
    if "second_wind" in L and not dfn.second_wind_used and 0 < dfn.hp < dfn.max_hp / 4:
        dfn.second_wind_used = True
        heal = round(dfn.max_hp * L["second_wind"] / 100)
        dfn.hp = min(dfn.max_hp, dfn.hp + heal)
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
    """Attack roll, damage and mitigation. Returns True if it landed."""
    how = how or weapon_phrase(att)
    rec = new_hit(combat, att, dfn, label)
    A, D = mechanics(att, combat, dfn), mechanics(dfn, combat, att)
    if is_companion(att):
        multiplier *= 1 + max(0, companion_boost(combat, "companion_damage")) / 100
        if "press" in A:
            multiplier *= 1 + A["press"] / 100
    dfn.attacked_since_turn = True
    if "phantom" in D and rng.uniform(0, 100) < D["phantom"]:
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
        rec.update(chance=roll_info.get("chance", round(chance, 1)), roll=roll_info.get("roll", 0.0))
    if "first_blood" in A and not att.first_blood_used:
        att.first_blood_used = True
        outcome = "crit"
        if rec is not None:
            rec["note"] = "First Blood: the first strike is always critical"
    if reliable:
        outcome = "hit"                            # Reliable: never misses, never crits
        if rec is not None:
            rec["note"] = "Reliable: never misses, never crits"
    if rec is not None:
        rec["outcome"] = outcome
    if outcome == "miss":
        att.relentless = 0
        combat.log.append(f"{att.name} {label} {dfn.name}: miss")
        if rec is not None:
            rec["figure"] = figure(rec)
        tell(combat, f"{who(att)} {vb(att, 'go', 'goes')} for {who(dfn)} {how} - and {vb(att, 'miss', 'misses')}", rec)
        if "windwalker" in D:
            dfn.windwalker_ready = True
        if "flowing_step" in D:
            dfn.counters["flow"] = min(3, dfn.counters.get("flow", 0) + 1)
        return False
    mult = hit_step(rec, 1.0, "Move power", multiplier)
    mult = hit_step(rec, mult, {"graze": "Glancing blow", "hit": "", "crit": "Critical hit"}[outcome], {"graze": 0.5, "hit": 1.0, "crit": crit_multiplier(att)}[outcome])
    mult = hit_step(rec, mult, "Weakened or strengthened", max(0.2, 1 + status_mod(att, "power") / 100))                  # poisoned or weakened attackers hit softer
    if att.side != dfn.side:
        mult = hit_step(rec, mult, "Target marked", 1 + status_mod(dfn, "taken") / 100)                       # a marked target takes more
    if "empowered" in A:
        mult = hit_step(rec, mult, "Empowered", 1 + A["empowered"] / 100)
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
    if "hex" in A and "hexed" in dfn.statuses:
        mult = hit_step(rec, mult, "Hex", 1 + A["hex"] / 100)
    if "blood_pact" in A:
        mult = hit_step(rec, mult, "Blood Pact", 1 + A["blood_pact"] / 100)
    if "attunement" in A and att.counters.get("attune"):
        mult = hit_step(rec, mult, "Attunement", 1 + A["attunement"] * att.counters["attune"] / 100)
    if "iron_will" in A and att.counters.get("shrugged"):
        mult = hit_step(rec, mult, "Iron Will", 1 + 0.10 * att.counters["shrugged"])
    if "unaware" in dfn.statuses:                  # a sneak attack on someone who never saw it coming
        mult = hit_step(rec, mult, "Unaware target", RULES["unaware_damage"])
    if att.windwalker_ready:
        att.windwalker_ready = False
        mult = hit_step(rec, mult, "Windwalker", 1 + A.get("windwalker", 0) / 100)
    if "flowing_step" in A and att.counters.get("flow"):
        mult = hit_step(rec, mult, "Flowing Step", 1 + A["flowing_step"] * att.counters["flow"] / 100)
        tell(combat, f"{who(att)} {vb(att, 'flow', 'flows')} out of the dodge and into the blow (Flowing Step)")
        att.counters["flow"] = 0
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
        guard = next((a for a in combat.allies() if is_companion(a)), None)
        if guard:
            moved = taken * min(90, D["guarded"]) / 100
            taken -= moved
            if rec is not None:
                rec["extras"].append(["Guardian takes a share", f"-{round(moved)}"])
            take_damage(combat, guard, moved, att, rng, att.damage_type)
            tell(combat, f"{who(guard)} throws itself in the way and takes {round(moved)} of it")
    pre_shield = taken
    taken = take_damage(combat, dfn, taken, att, rng, att.damage_type)
    if rec is not None:
        rec["final"] = round(taken)
        if round(pre_shield) != round(taken):
            rec["extras"].append(["Shield, ward or last-moment effects", f"{round(taken) - round(pre_shield):+d}"])
        rec["figure"] = figure(rec)
    if att.side == "ally" and dfn.side == "enemy":
        dfn.counters["flanked"] = combat.round                             # an ally has struck it (Flanking)
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
    turned = f"; {whose(dfn)} {'armor' if dfn.side == 'player' else 'hide or armor'} turns part of it" if absorbed > taken * 0.4 else ""
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
            combat.log.append(f"{att.name}'s {el} damage burns {dfn.name}: {dealt}")
            if rec is not None:
                rec["extras"].append([f"{el.capitalize()} damage from gear", f"+{round(dealt)}"])
            tell(combat, f"{el} damage follows the blow into {who(dfn)}" + (f" - {who(dfn)} {vb(dfn, 'are', 'is')} {condition(dfn)}" if dfn.alive else ""))
    if "elemental_weapon" in A and dfn.alive and taken > 0:
        buff = next((b for b in att.buffs.values() if b.get("kind") == "elemental"), {})
        el = buff.get("element") or "fire"
        part, _ = mitigate(dfn, dmg * A["elemental_weapon"] / 100, "magical", att.level, combat, att)
        held, att.hit_element = att.hit_element, el
        extra = take_damage(combat, dfn, part, att, rng, "magical")
        att.hit_element = held
        combat.log.append(f"{att.name}'s {el} weapon burns {dfn.name}: {extra}")
        if rec is not None:
            rec["extras"].append([f"{el.capitalize()} weapon", f"+{round(extra)}"])
        tell(combat, f"{el} flares along the blow and bites into {who(dfn)} (Elemental Weapon)")
    if "stormcaller" in A and dfn.alive and rng.uniform(0, 100) < A["stormcaller"]:
        bolt, _ = mitigate(dfn, dmg * 0.5, "magical", att.level, combat, att)
        combat.log.append(f"lightning strikes {dfn.name}: {take_damage(combat, dfn, bolt, att, rng, 'magical')} damage (Stormcaller)")
        tell(combat, f"lightning answers {whose(att)} weapon and cracks down onto {who(dfn)} (Stormcaller)")
    if outcome == "crit" and "bloodlust" in A:
        gain = round(att.max_hp * A["bloodlust"] / 100)
        att.hp = min(att.max_hp, att.hp + gain)
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
            att.hp = min(att.max_hp, att.hp + heal)
            combat.log.append(f"{att.name} drinks {heal} health from the wound (Vampiric)")
            tell(combat, f"{whose(att)} weapon drinks from the wound, and strength flows back into {who(att)} (Vampiric)")
    if att.side == "player" and taken > 0:                                  # on-hit properties rolled on the weapon
        always = {"always"}
        leech = bonus(att, "vampiric", always)
        if leech and att.alive:
            heal = round(taken * leech / 100)
            if heal:
                att.hp = min(att.max_hp, att.hp + heal)
                tell(combat, f"the weapon drinks from the wound, and {heal} health flows back into {who(att)}")
        if att.max_mana:
            att.mana = min(att.max_mana, att.mana + att.max_mana * bonus(att, "siphon_mana", always) / 100)
        if att.max_stamina:
            att.stamina = min(att.max_stamina, att.stamina + att.max_stamina * bonus(att, "siphon_stamina", always) / 100)
        for stat, status, rounds, word in (("envenom_chance", "poisoned", 3, "envenomed"), ("ignite_chance", "burning", 3, "ignited"),
                                           ("jolt_chance", "stunned", 1, "jolted")):
            chance = bonus(att, stat, always)
            if chance and dfn.alive and rng.uniform(0, 100) < chance and add_status(combat, dfn, status, rounds):
                combat.log.append(f"{dfn.name} is {status} (weapon)")
                tell(combat, f"{who(dfn)} {STATUS_WORDS[status][0 if dfn.side == 'player' else 1]} (the weapon {word} it)")
    if att.side == "player" and "lifebinder" in A:
        for ally in (a for a in combat.allies() if is_companion(a)):
            ally.hp = min(ally.max_hp, ally.hp + round(taken * A["lifebinder"] / 100))
    if can_cleave and att.side == "player" and "packbond" in A and dfn.alive:
        for ally in [a for a in combat.allies() if is_companion(a)]:
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
            if effect in A and rng.uniform(0, 100) < A[effect] and add_status(combat, dfn, status, rounds):
                combat.log.append(f"{dfn.name} is {status}")
                tell(combat, f"{who(dfn)} {STATUS_WORDS[status][0 if dfn.side == 'player' else 1]} ({effect.capitalize()})")
    if "earthshaker" in A and dfn.alive and (outcome == "crit" or (outcome == "hit" and rng.uniform(0, 100) < A["earthshaker"])):
        if add_status(combat, dfn, "prone", 1):
            combat.log.append(f"{dfn.name} is knocked flat")
            tell(combat, f"the blow lands like a falling wall and {who(dfn)} {STATUS_WORDS['prone'][0 if dfn.side == 'player' else 1]} (Earthshaker)")
    if "open_palm" in A and dfn.alive and (outcome == "crit" or (outcome == "hit" and rng.uniform(0, 100) < A["open_palm"])):
        if add_status(combat, dfn, "prone", 1):
            combat.log.append(f"{dfn.name} is swept off their feet")
            tell(combat, f"the open palm turns {whose(dfn)} balance against {who(dfn)} and {who(dfn)} {STATUS_WORDS['prone'][0 if dfn.side == 'player' else 1]} (Open Palm)")
    if not dfn.alive:
        combat.log.append(f"{dfn.name} falls")
        tell(combat, f"{who(dfn)} {vb(dfn, 'fall', 'falls')}" + (" - and the world goes dark" if dfn.side == "player" else " and does not rise"))
        att.kill_round = combat.round
        if "thrall" in A and att.side == "player" and dfn.side == "enemy" and not combat.thrall_used:
            raise_thrall(combat, dfn)
        if "soul_harvest" in A and att.max_mana:
            att.mana = min(att.max_mana, att.mana + att.max_mana * A["soul_harvest"] / 100)
            tell(combat, f"something passes from the fallen into {who(att)} (Soul Harvest)")
        if "triumph" in A:
            heal = round(att.max_hp * A["triumph"] / 100)
            att.hp = min(att.max_hp, att.hp + heal)
            combat.log.append(f"{att.name} is renewed by the kill: +{heal} health (Triumph)")
            tell(combat, f"the kill fills {who(att)} with fresh strength (Triumph)")
    elif can_riposte and "riposte" in D and att.reach == "melee" and dfn.alive and att.alive \
            and rng.uniform(0, 100) < D["riposte"]:
        apply_damage(combat, dfn, att, 1.0, "ripostes against", rng, can_cleave=False, can_riposte=False,
                     how=f"in a lightning riposte {weapon_phrase(dfn)}")
    if can_flurry and "flurry" in A and dfn.alive and att.alive and rng.uniform(0, 100) < A["flurry"]:
        apply_damage(combat, att, dfn, multiplier * 0.6, "strikes again at", rng, can_cleave=False, can_riposte=False,
                     how="in a blur of follow-up blows (Flurry)", can_flurry=False)
    if can_cleave and "many_heads" in A and att.side == "player" and att.counters.get("heads_round") != combat.round and att.alive:
        others = [e for e in combat.enemies() if e is not dfn]
        if others:
            att.counters["heads_round"] = combat.round
            apply_damage(combat, att, min(others, key=lambda e: e.hp), A["many_heads"] / 100, "is struck by another head against", rng,
                         can_cleave=False, can_riposte=False, can_flurry=False, how="from the side, with another head of the beast (Many Heads)")
    if can_cleave and "cleave" in A:
        others = [e for e in (combat.enemies() if att.side != "enemy" else []) if e is not dfn and e.band == "engaged"]
        if others:
            apply_damage(combat, att, others[0], multiplier * A["cleave"] / 100, "cleaves into", rng, can_cleave=False,
                         can_riposte=False, how="as the same swing carries on (Cleave)")
    return True


def raise_thrall(combat: Combat, dead: Fighter) -> None:
    """The first enemy the wearer slays rises as it was in life and fights for them until the fight ends (or it falls again)."""
    combat.thrall_used = True
    t = dead.model_copy(deep=True)
    base = dead.name.replace(" (elite)", "")
    for article in ("the ", "a ", "an ", "one of "):
        if base.lower().startswith(article):
            base = base[len(article):]
    t.id, t.side, t.name = "thrall", "ally", f"the risen {base}"
    strength = 0.6 if dead.boss else 1.0
    t.max_hp = max(1, round(dead.max_hp * strength))
    t.hp, t.shield, t.fled = float(t.max_hp), 0.0, False
    t.statuses, t.cooldowns, t.buffs, t.boss, t.band = {}, {}, {}, {}, "engaged"
    t.rank, t.temperament, t.spawn = "normal", "aggressive", ""
    combat.fighters.append(t)
    combat.log.append(f"{dead.name} rises to fight for you")
    tell(combat, f"{who(dead)} does not stay down: it rises again, as it was in life, and turns on its own side - {t.name} fights for you now, until this fight is over (Risen Thrall)")


STATUS_WORDS = {
    "slowed": ("stagger, your limbs suddenly heavy", "staggers, suddenly sluggish"),
    "bleeding": ("are bleeding freely", "is bleeding freely"),
    "stunned": ("reel, stunned", "reels, stunned"),
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
}


def in_reach(att: Fighter, dfn: Fighter, reach: str | None = None) -> bool:
    reach = reach or att.reach
    band = dfn.band if att.side != "enemy" else att.band
    if reach in ("ranged", "area", "self"):
        return True
    if reach == "extended":
        return band in ("engaged", "near")
    return band == "engaged"


def step_closer(f: Fighter) -> None:
    f.band = BANDS[max(0, BANDS.index(f.band) - 1)]


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
    if move.resource == "stamina":
        # Stamina is a rhythm: smaller flat costs (a share of a typical pool at your level), refilled by fighting
        pool = pools.reference_pool("stamina", f.level) if f.side == "player" else f.max_stamina
        cost = pool * RULES["stamina_cost_percent"][move.tier] / 100
    else:
        pool = pools.reference_mana(f.level) if f.side == "player" else f.max_mana     # a share of what a dedicated caster has
        cost = pool * RULES["ability_cost_percent"][move.tier] / 100
    unburdened = mechanics(f, combat).get("unburdened", 0)
    if unburdened:
        cost *= 1 - min(90, unburdened) / 100
    if move.shape == "overcharge":
        cost *= AT.SHAPES["overcharge"]["cost"]
    if move.effect == "buff":
        cost *= AT.T["buff_cost"]
    return max(1, math.ceil(cost))


def can_use(f: Fighter, move: Move, combat: Combat | None = None) -> str | None:
    if move.effect == "relic" and move.uses and f.relic_uses.get(move.id, 0) >= move.uses:
        return f"{move.name} has given all it has this fight."
    if f.cooldowns.get(move.id, 0) > 0:
        return f"{move.name} isn't ready yet ({f.cooldowns[move.id]} more rounds)."
    have = f.stamina if move.resource == "stamina" else f.mana
    if move.resource == "mana":
        blood = mechanics(f, combat).get("overchannel", 0)
        if blood:
            have += max(0.0, f.hp - f.max_hp * 0.1) / blood
    if have < cost_of(f, move, combat):
        return f"Not enough {move.resource} for {move.name}."
    return None


def act_attack(combat: Combat, att: Fighter, target: Fighter, rng: random.Random) -> None:
    if att.side == "player" and target:
        combat.focus = target.id
    if not in_reach(att, target):
        if att.side == "enemy":
            step_closer(att)
        else:
            step_closer(target)
        att.move_round = combat.round
        combat.log.append(f"{att.name} closes in on {target.name}")
        tell(combat, f"{who(att)} {vb(att, 'close', 'closes')} the distance to {who(target)}")
        return
    apply_damage(combat, att, target, RULES["damage"]["multiplier"]["basic"], f"attacks ({att.weapon_name})", rng)


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
        victims = [t] + [e for e in combat.enemies() if e is not t and e.alive and e.band == "engaged"]
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
    elif kind == "lunge":
        if t.band != "engaged":
            mult *= sh["bonus"]
            t.band = "engaged"
            tell(combat, f"{who(att)} {vb(att, 'close', 'closes')} the gap in a single bound")
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
            o = min(others, key=lambda e: BANDS.index(e.band))
            apply_damage(combat, att, o, mult * sh["side"], "arcs on to", rng, how=f"from {move.name}", can_cleave=False, can_riposte=False)
    elif kind == "ricochet" and landed:
        last = t
        for share in sh["bounces"]:
            others = [e for e in combat.enemies() if e is not last and e.alive]
            if not others:
                break
            last = rng.choice(others)
            apply_damage(combat, att, last, mult * share, "ricochets into", rng, how=f"from {move.name}", can_cleave=False, can_riposte=False)
    elif kind == "packhunt" and landed and t.alive:
        for a in [a for a in combat.allies() if is_companion(a)]:
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
        pack = [a for a in combat.allies() if is_companion(a)]
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
        if rng.uniform(0, 100) < AT.value(r["chance"], move.tier) and add_status(combat, t, r["status"], r["rounds"]):
            combat.log.append(f"{t.name} is {r['status']} ({r['label']})")
            tell(combat, f"{who(t)} {STATUS_WORDS[r['status']][0 if t.side == 'player' else 1]} ({r['label']})")
            if r["status"] == "grappled":
                t.band = "engaged"
    elif move.rider == "shove" and t.band != "far" and "grappled" not in t.statuses:
        t.band = BANDS[min(2, BANDS.index(t.band) + 1)]
        combat.log.append(f"{t.name} is driven back")
        tell(combat, f"{who(t)} {vb(t, 'are', 'is')} driven back by the force of it ({r['label']})")
    elif move.rider == "hook" and t.band != "engaged":
        step_closer(t)
        combat.log.append(f"{t.name} is hauled closer")
        tell(combat, f"{who(t)} {vb(t, 'are', 'is')} hauled a step closer ({r['label']})")


def act_ability(combat: Combat, att: Fighter, move: Move, target: Fighter | None, rng: random.Random) -> str | None:
    problem = can_use(att, move, combat)
    if problem:
        return problem
    if att.side == "player" and target and target.side == "enemy":
        combat.focus = target.id
    if move.effect == "relic":
        from engine import relics
        return relics.use(combat, att, move, target, rng)
    cost = cost_of(att, move, combat)
    am = mechanics(att, combat)
    free_cast = move.resource == "mana" and not att.archmage_used and "archmage" in am
    if move.resource == "stamina":
        att.stamina -= cost
    elif cost > att.mana and "overchannel" in am:
        owed = cost - att.mana
        att.mana = 0
        att.hp = max(1, att.hp - owed * am["overchannel"])
        combat.log.append(f"{att.name} pays {owed:.0f} mana in blood (Overchannel)")
        tell(combat, f"{who(att)} {vb(att, 'have', 'has')} nothing left to give, so {vb(att, 'pay', 'pays')} in blood (Overchannel)")
    else:
        att.mana -= cost
    if move.rider == "thrift":
        back = cost * AT.value(AT.RIDERS["thrift"]["refund"], move.tier) / 100
        if move.resource == "stamina":
            att.stamina = min(att.max_stamina, att.stamina + back)
        else:
            att.mana = min(att.max_mana, att.mana + back)
    if move.resource == "mana":
        att.spells_cast += 1
        if "arcane_recall" in am:
            for k in list(att.cooldowns):
                if k != move.id and att.cooldowns[k] > 0:
                    att.cooldowns[k] = max(0, att.cooldowns[k] - int(am["arcane_recall"]))
    echo = mechanics(att, combat).get("echoing", 0)
    if move.cooldown and not (echo and rng.uniform(0, 100) < echo):
        att.cooldowns[move.id] = move.cooldown + 1
    mult = RULES["damage"]["multiplier"][move.tier]
    if move.effect == "damage" and not move.rider and not move.shape:
        mult *= 1 + AT.T["plain_damage"]                  # Honed: a plain damage ability is never strictly worse than a decorated one
    if free_cast:
        att.archmage_used = True
        mult *= 1 + am["archmage"] / 100
        tell(combat, f"{who(att)} {vb(att, 'let', 'lets')} the first spell go without a breath of effort (Archmage's Focus)")
    enemies = combat.enemies()

    if move.effect == "damage":
        spell = move.resource == "mana"
        saved = (att.weapon_attrs, att.damage_type, att.weapon_damage)
        att.hit_element = move.element
        if spell:
            att.weapon_attrs = [move.attribute or "intelligence"]
            focus = att.weapon_damage if att.damage_type == "magical" else 0
            att.damage_type = "magical"
            att.weapon_damage = max(focus, RULES["spell_base_damage"] * growth(att.level))
        targets = enemies if move.reach == "area" else [target] if target else enemies[:1]
        if move.rider == "seeker" and move.reach != "area" and enemies:
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
        for t in targets:
            if move.reach != "area" and move.shape != "lunge" and not in_reach(att, t, move.reach):
                step_closer(t)
                combat.log.append(f"{att.name} closes in on {t.name}")
                tell(combat, f"{who(att)} {vb(att, 'close', 'closes')} the distance to {who(t)}")
                continue
            before = t.hp
            if move.reach == "area":
                landed |= apply_damage(combat, att, t, mult * 0.6, f"uses {move.name} on", rng, how=f"with {move.name}")
            else:
                landed |= shaped_strike(combat, att, t, move, mult, rng)
            if move.rider:
                if move.rider == "siphon" and att.alive:
                    gain = round(max(0.0, before - t.hp) * AT.value(AT.RIDERS["siphon"]["heal"], move.tier) / 100)
                    if gain:
                        att.hp = min(att.max_hp, att.hp + gain)
                        tell(combat, f"{move.name} draws {gain} health back into {who(att)} ({AT.RIDERS['siphon']['label']})")
                if move.rider not in ("drain", "rouse") or before > t.hp:
                    apply_rider(combat, att, t, move, rng)
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
        att.weapon_attrs, att.damage_type, att.weapon_damage = saved
        att.hit_element = ""
    elif move.effect in ("control", "influence"):
        t = target or (enemies[0] if enemies else None)
        if t:
            power = [move.attribute] if move.resource == "mana" and move.attribute else \
                (["charisma", "strength"] if move.effect == "influence" else att.weapon_attrs)
            if resist(att, t, power, rng):
                combat.log.append(f"{att.name} uses {move.name} on {t.name}: resisted")
                tell(combat, f"{who(att)} {vb(att, 'turn', 'turns')} {move.name} on {who(t)}, but {vb(t, 'you shake', 'it shakes')} it off")
            else:
                status = ("frightened" if move.effect == "influence" else
                          {"light": "slowed", "moderate": "prone", "heavy": "stunned"}[move.tier])
                if add_status(combat, t, status, 2 if move.tier != "heavy" else 1):
                    combat.log.append(f"{att.name} uses {move.name} on {t.name}: {status}")
                    tell(combat, f"{who(att)} {vb(att, 'unleash', 'unleashes')} {move.name} on {who(t)}, and {who(t)} "
                                 f"{STATUS_WORDS[status][0 if t.side == 'player' else 1]}")
                if move.rider:
                    apply_rider(combat, att, t, move, rng)
    elif move.effect == "buff":
        mech = AT.buff_mech(move.buff, move.tier, move.buff_stat, magical=move.resource == "mana")
        rounds = AT.value(AT.BUFFS[move.buff]["rounds"], move.tier)
        for k, b in list(att.buffs.items()):
            if b.get("kind") == move.buff:
                att.buffs.pop(k)                      # one of each kind: a new casting replaces the old
        att.buffs[move.id] = {"rounds": rounds, "mech": mech, "drain": 0, "collapse": "", "name": move.name, "kind": move.buff,
                              "element": move.element or "fire"}
        combat.log.append(f"{att.name} uses {move.name}: {AT.buff_text(move.buff, move.tier, move.buff_stat)}")
        tell(combat, f"{who(att)} {vb(att, 'wrap', 'wraps')} {'yourself' if att.side == 'player' else 'itself'} in {move.name}: "
                     f"{AT.buff_text(move.buff, move.tier, move.buff_stat)}")
    elif move.effect == "defense":
        att.defending = RULES["defend_percent"][move.tier]
        combat.log.append(f"{att.name} uses {move.name}: braced ({att.defending:.0f}% less damage)")
        tell(combat, f"{who(att)} {vb(att, 'brace', 'braces')} with {move.name}, ready for what comes")
    elif move.effect == "mobility":
        att.elevated = True
        att.move_round = combat.round
        if target:
            target.band = "engaged"
        combat.log.append(f"{att.name} uses {move.name}: gains height" + (f" and closes on {target.name}" if target else ""))
        tell(combat, f"{who(att)} {vb(att, 'launch', 'launches')} upward with {move.name}" + (f", coming down right beside {who(target)}" if target else ""))
    elif move.effect == "healing":
        amount = round(att.max_hp * RULES["healing_percent"][move.tier] / 100)
        att.hp = min(att.max_hp, att.hp + amount)
        combat.log.append(f"{att.name} uses {move.name}: heals {amount}")
        tell(combat, f"{who(att)} {vb(att, 'call', 'calls')} on {move.name}, and wounds begin to close")
    elif move.effect == "summon":
        allies = [f for f in combat.fighters if f.side == "ally"]
        if allies:
            for a in allies:
                a.hp = min(a.max_hp, max(a.hp, 0) + a.max_hp * 0.4)
            combat.log.append(f"{att.name} uses {move.name}: companions restored")
            tell(combat, f"{who(att)} {vb(att, 'pour', 'pours')} power into {move.name}, and "
                         f"{', '.join(a.name for a in allies)} {'surges' if len(allies) == 1 else 'surge'} back to strength")
        else:
            combat.log.append(f"{att.name} uses {move.name}: nothing answers here")
            tell(combat, f"{who(att)} {vb(att, 'call', 'calls')} with {move.name}, but nothing answers in the heat of the fight")
    elif move.effect == "command":
        if target:
            combat.focus = target.id
        allies = combat.allies()
        pack = [a for a in allies if is_companion(a)]
        kind = move.command or "focus"
        spec = AT.COMMANDS[kind]
        if not allies:
            tell(combat, f"{who(att)} {vb(att, 'give', 'gives')} the command, but no companion is there to obey")
        elif kind == "focus":
            for a in allies:
                if combat.enemies():
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
    if "attunement" in am:
        att.counters["attune"] = min(5, att.counters.get("attune", 0) + 1)
    if move.resource == "mana" and "starfall" in am and att.spells_cast % 4 == 0 and att.alive:
        base = RULES["spell_base_damage"] * growth(att.level) * am["starfall"] / 100
        tell(combat, "the sky answers the fourth spell, and stars fall (Starfall)")
        for e in combat.enemies():
            dealt, _ = mitigate(e, base, "magical", att.level, combat, att)
            combat.log.append(f"starfall hits {e.name}: {take_damage(combat, e, dealt, att, rng, 'magical')} damage")
    return None


def act_defend(combat: Combat, f: Fighter) -> None:
    f.defending = RULES["defend_percent"]["basic"]
    combat.log.append(f"{f.name} defends")
    tell(combat, f"{who(f)} {vb(f, 'set', 'sets')} {whose(f)} guard and {vb(f, 'wait', 'waits')}")


def act_move(combat: Combat, f: Fighter, how: str, target: Fighter | None) -> None:
    f.move_round = combat.round
    if how == "high_ground":
        f.elevated = True
        combat.log.append(f"{f.name} takes the high ground")
        tell(combat, f"{who(f)} {vb(f, 'scramble', 'scrambles')} up to higher ground")
    elif how == "back":
        f.elevated = False
        for e in combat.enemies():
            e.band = BANDS[min(2, BANDS.index(e.band) + 1)]
        combat.log.append(f"{f.name} falls back")
        tell(combat, f"{who(f)} {vb(f, 'fall', 'falls')} back, opening distance")
    else:
        for e in ([target] if target else combat.enemies()[:1]):
            step_closer(e)
        combat.log.append(f"{f.name} closes in")
        tell(combat, f"{who(f)} {vb(f, 'press', 'presses')} in")


def flee_chance(combat: Combat) -> float:
    fr = RULES["flee"]
    p = combat.player
    enemies = combat.enemies()
    if not enemies:
        return 100
    nearest = min(enemies, key=lambda e: BANDS.index(e.band))
    their_dex = sum(e.attrs.get("dexterity", 10) for e in enemies) / len(enemies)
    mine = p.attrs.get("dexterity", 10)
    chance = fr["base"] + fr["band"][nearest.band] + fr["dexterity_spread"] * (mine - their_dex) / max(1, mine + their_dex)
    if not combat.player_acted:
        first = fr.get("first_action_engaged" if nearest.band == "engaged" else "first_action", chance)
        chance = max(chance, first)
    pm = mechanics(p, combat)
    if "lightfoot" in pm:
        chance += 30
    if "shadowmantle" in pm:
        if all(e.band != "engaged" for e in enemies):
            return 95
        chance += pm["shadowmantle"]
    return max(5, min(95, chance))


def act_flee(combat: Combat, rng: random.Random) -> bool:
    chance = flee_chance(combat)
    if rng.uniform(0, 100) < chance:
        combat.log.append(f"{combat.player.name} breaks away and escapes")
        tell(combat, "you break away and run, and this time nothing catches you")
        combat.over = "fled"
        return True
    combat.log.append(f"{combat.player.name} tries to flee but is cut off")
    tell(combat, "you try to break away, but you are cut off")
    return False


def bring_allies(combat: Combat) -> None:
    """A party that held back reaches the fight."""
    if not combat.ally_reserves or combat.round < combat.ally_arrive:
        return
    came = combat.ally_reserves
    combat.ally_reserves = []
    for a in came:
        a.band = "near"
        combat.fighters.append(a)
    names = ", ".join(a.name for a in came)
    combat.log.append(f"the party arrives: {names}")
    tell(combat, f"{names} burst{'s' if len(came) == 1 else ''} in from outside, answering the alarm")


def muster(combat: Combat) -> bool:
    """Bring up the next wave from the reserves, at a distance. Returns True if anyone came."""
    if not combat.reserves:
        return False
    wave = [combat.reserves.pop(0) for _ in range(min(combat.reinforce_count, len(combat.reserves)))]
    for f in wave:
        f.band = "far"
        combat.fighters.append(f)
    names = ", ".join(f.name for f in wave)
    combat.log.append(f"reinforcements: {names}")
    tell(combat, f"{len(wave)} more come running from the rest of the camp, drawn by the noise ({names})"
         + (f"; {len(combat.reserves)} still to come" if combat.reserves else ""))
    return True


# ---------- turn order and AI ----------

def start_turn(f: Fighter, combat: Combat | None = None) -> bool:
    """Tick statuses at the start of a fighter's turn. Returns False if they lose the turn."""
    fm = mechanics(f, combat)
    f.attacked_since_turn = False
    f.defending = 0
    if f.side == "player" and f.alive and f.max_stamina and combat is not None and combat.round > 1:
        f.stamina = min(f.max_stamina, f.stamina + pools.reference_pool("stamina", f.level) * RULES["momentum"]["round"] / 100)
    if f.buffs and combat is not None:
        from engine import relics
        relics.tick(combat, f)
    if "unyielding" in fm:
        f.statuses.pop("stunned", None)
        f.statuses.pop("prone", None)
    if "regeneration" in fm and f.alive:
        f.hp = min(f.max_hp, f.hp + max(1, round(f.max_hp * fm["regeneration"] / 100)))
    for dot in ("bleeding", "poisoned", "burning"):
        if dot in f.statuses:
            f.hp = max(0, f.hp - max(1, round(f.max_hp * RULES["statuses"][dot]["damage_percent"] / 100)))
    skip = "stunned" in f.statuses
    if "prone" in f.statuses and not skip:
        f.statuses.pop("prone")
        skip = True
    for s in list(f.statuses):
        f.statuses[s] -= 1
        if f.statuses[s] <= 0:
            f.statuses.pop(s)
    for k in list(f.cooldowns):
        f.cooldowns[k] -= 1
        if f.cooldowns[k] <= 0:
            f.cooldowns.pop(k)
    return f.alive and not skip


FLEE_CHANCE_PASSIVE = {"engaged": 0.2, "near": 0.4, "far": 0.6}   # startled animals don't run in the first round


def enemy_turn(combat: Combat, e: Fighter, rng: random.Random) -> None:
    if "unaware" in e.statuses:                      # caught by surprise: the first round is the player's alone
        e.statuses.pop("unaware")
        combat.log.append(f"{e.name} is caught unaware")
        tell(combat, f"{who(e)} has not yet understood what is happening")
        return
    if e.boss:
        from engine import bosses
        bosses.refresh(e)
    if not start_turn(e, combat):
        if e.alive:
            combat.log.append(f"{e.name} loses its turn")
            tell(combat, f"{who(e)} reels, unable to act")
        return
    pinned = {"slowed", "stunned", "prone", "grappled"} & set(e.statuses)
    if e.temperament == "passive" and combat.round > 1 and not pinned and not combat.gentle and \
            rng.random() < FLEE_CHANCE_PASSIVE.get(e.band, 0.4):
        e.fled = True
        combat.log.append(f"{e.name} bolts and escapes")
        tell(combat, f"{who(e)} bolts for the trees and is gone")
        return
    targets = [combat.player] + combat.allies()
    targets = [t for t in targets if t.alive]
    if not targets:
        return
    held = mechanics(combat.player, combat)
    bulwark = ("bulwark" in held or "taunt" in held) and combat.player.alive      # taunt: Distract draws every enemy onto you
    target = combat.player if bulwark or rng.random() < 0.7 or len(targets) == 1 else rng.choice(targets[1:])
    if "befuddled" in e.statuses:                    # its attack goes wide: at a random fighter, friend or foe
        e.statuses.pop("befuddled")
        mix = [f for f in combat.fighters if f.alive and f is not e and not f.fled]
        if mix:
            target = rng.choice(mix)
            combat.log.append(f"{e.name} is befuddled and turns on {target.name}")
            tell(combat, f"{who(e)} lashes out blindly at {who(target)}")
            if target.side == e.side:
                e_band, e.band = e.band, "engaged"
                apply_damage(combat, e, target, 1.0, f"{e.weapon_name}s" if not e.weapon_name.endswith("s") else e.weapon_name, rng)
                e.band = e_band
                return
    if "frightened" in e.statuses and e.band != "engaged" and "grappled" not in e.statuses:
        combat.log.append(f"{e.name} hangs back, afraid")
        tell(combat, f"{who(e)} hangs back, afraid to come closer")
        return
    if not in_reach(e, target):
        step_closer(e)
        combat.log.append(f"{e.name} closes in")
        tell(combat, f"{who(e)} closes in")
        return
    apply_damage(combat, e, target, 1.0, f"{e.weapon_name}s" if not e.weapon_name.endswith("s") else e.weapon_name, rng)
    if e.boss and e.alive and combat.player.alive:
        from engine import bosses
        bosses.own_turn(combat, e, target if target.alive else combat.player, rng)


def ally_turn(combat: Combat, a: Fighter, rng: random.Random) -> None:
    if not start_turn(a, combat):
        return
    if a.ally_role == "priest" and "heal" not in a.cooldowns:
        hurt = [f for f in [combat.player] + combat.allies() if f.alive and f.hp < f.max_hp * RULES["ally_heal"]["below"]]
        if hurt:
            t = min(hurt, key=lambda f: f.hp / f.max_hp)
            amount = t.max_hp * RULES["ally_heal"]["pct"] / 100
            t.hp = min(t.max_hp, t.hp + amount)
            a.cooldowns["heal"] = RULES["ally_heal"]["cooldown"] + 1
            combat.log.append(f"{a.name} heals {t.name} for {round(amount)}")
            tell(combat, f"{who(a)} {vb(a, 'lay', 'lays')} hands on {who(t)}, and the wounds close a little")
            return
    enemies = combat.enemies()
    if enemies:
        target = next((e for e in enemies if e.id == combat.focus), None) or min(enemies, key=lambda e: e.hp)
        if target.band != "engaged":
            target.band = "near" if target.band == "far" else "engaged"
        inspire = mechanics(combat.player, combat).get("inspire", 0)
        apply_damage(combat, a, target, 1.0 + inspire / 100, "attacks", rng)


def _legendary(combat: Combat, rng: random.Random) -> None:
    if combat.player.alive and any(e.boss for e in combat.enemies()):
        from engine import bosses
        bosses.legendary(combat, rng)


def finish_round(combat: Combat, rng: random.Random) -> None:
    """Everyone except the player acts, then the round advances."""
    _legendary(combat, rng)                    # a boss acts at the end of the player's turn
    for a in combat.allies():
        ally_turn(combat, a, rng)
        _legendary(combat, rng)
    for e in sorted(combat.enemies(), key=lambda x: -x.attrs.get("dexterity", 10)):
        if combat.player.alive:
            enemy_turn(combat, e, rng)
            _legendary(combat, rng)
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
    if not start_turn(p, combat):
        return
    enemies = combat.enemies()
    target = min(enemies, key=lambda e: (BANDS.index(e.band), e.hp))
    usable = [m for m in p.moves if m.effect == "damage" and not can_use(p, m, combat)]
    usable.sort(key=lambda m: -RULES["damage"]["multiplier"][m.tier])
    if usable and (in_reach(p, target, usable[0].reach) or usable[0].reach == "area"):
        act_ability(combat, p, usable[0], target, rng)
    else:
        act_attack(combat, p, target, rng)
    if not combat.enemies() and not muster(combat):
        combat.over = "victory"


def simulate(combat: Combat, rng: random.Random, max_rounds: int = 60) -> Combat:
    c = copy.deepcopy(combat)
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


def opening(combat: Combat, rng: random.Random) -> None:
    """Everything that happens as a fight begins: barriers, rallies, war cries, dread."""
    combat.opened = True
    p = combat.player
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

