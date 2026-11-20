"""(f504) One damage calculation, declared stage by stage. data/rules/stages.yaml names the stages of each damage path in order (the
blow, a poison's or a burn's tick, a wound torn, a force turned back, a kill outright); STAGES here names the function behind each id, and
engine/data_check.py holds the two to each other: a stage the data names must have a function, and a function here must be named by a
path. Each stage reads and writes one Blow (the shared locals of engine/combat.py take_damage, so nothing is stale), keeps take_damage's
labels and its 0.5 threshold for the record (step), and returns False to end the path (a floor that held, a petrified target, nothing
left to land). The retribution and spellmirror rebound runs the rebound path, which has no rebound stage: that is the loop guard.

(f768) Every path that writes health names `fall` straight after it (engine/data_check.py holds it): the one fall step, fall_step, that
every death ends in, whatever killed.

(f772) The floors under the health bar are one table (stages.yaml floors), every path held to it: the same floor stages run on every
path, reading what is about to land through one accessor (Blow.landing). A floor that holds notes its fighter on the blow in progress
(engine/combat.py hold_in_blow), and the rest of that blow takes nothing from it (reaches): a floor that holds a blow holds all of it.

(f505) take_damage is resolve("blow"), the tick in start_turn resolve("dot_tick"), afflictions.tear resolve("tear") and the rebound
stage resolve("rebound"): one calculation, its value and its explanation from the declared recipe; the fight fixtures (93 cases, none
moved) are the proof that no number moved. (f773) engine/combat.py kill_outright is resolve("outright").
The health bar is written here and in engine/combat.py restore, and in the named exemptions tools/purity.py HP_EXEMPT lists (construction,
unmaking, floors outside a blow, heals outside restore, costs and drains); nowhere else (hp_writes, tools/sim/hp_writes_505_test.py)."""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml
from core import yamlio

from engine import combat as C
from engine import effects as E
from engine import items

_ST = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "stages.yaml").read_text(encoding="utf-8"))
PATHS: dict[str, list[str]] = _ST["damage"]
FLOORS: tuple[str, ...] = tuple(_ST.get("floors") or ())    # (f772) the floor stages, declared once; each writes health only to hold one up

NAMED = {"blood_pact": "Blood Pact", "hardening": "Hardening", "aegis": "Aegis", "last_stand": "Last Stand", "stoneskin": "Stoneskin",
         "plating": "Plating", "spellward": "Spellward", "unbroken": "Unbroken", "guardian": "Guardian", "mana_shield": "Mana shield"}


@dataclass
class Blow:
    """The shared locals of one damage path: the fight, the one struck, what is coming (amount, a float until it is rounded to what is
    dealt), who struck, the die, the kind of damage, the blow's record (None when blows are not being recorded), the struck one's active
    mechanics (L), and for a tick the affliction."""
    combat: C.Combat
    dfn: C.Fighter
    amount: float
    source: C.Fighter | None
    rng: random.Random
    damage_type: str = "physical"
    rec: dict | None = None
    dealt: int = 0
    L: dict = field(default_factory=dict)
    dot: str = ""
    deep: float = 1.0
    by: str = ""
    path: str = "blow"
    cause: C.Fighter | None = None      # (f768) whose kill a death here is: the source, unless the path was handed another
    up: bool = False                    # (f768) standing just before the health stage wrote
    whole: bool = False                 # (f772) the figure has been rounded to what is dealt (the blow's `rounded`)
    harm: str = "blow"                  # (f772) what a floor's line calls this harm: a key of combat.yaml harms

    @property
    def landing(self) -> float:
        """(f772) What is about to land: the rounded figure once the path has rounded it (a blow), else the amount (a tick, a torn
        wound, a rebound). Every floor reads it, so the same floors run on every path."""
        return self.dealt if self.whole else self.amount

    @landing.setter
    def landing(self, value: float) -> None:
        if self.whole:
            self.dealt = int(value)
        else:
            self.amount = value

    def label(self, mid: str) -> str:
        le = items.LEGENDARY.get(mid)
        return self.dfn.mech_names.get(mid) or (le.name if le else NAMED.get(mid, mid.replace("_", " ").title()))

    def step(self, before: float, mid_or_name: str, named_by_id: bool = True) -> None:
        """What changed the figure, written into the record by the name of the passive or gear that caused it (a change under half a
        point is not worth a line)."""
        if self.rec is not None and abs(before - self.amount) >= 0.5:
            self.rec["extras"].append([self.label(mid_or_name) if named_by_id else mid_or_name, f"{round(self.amount - before):+d}"])
            self.rec["named_total"] = self.rec.get("named_total", 0) + (round(self.amount) - round(before))


# ---------- the blow: what a landed hit meets on its way to the health bar

def petrified(b: Blow) -> bool:
    """Petrify (f266): stone cannot be hurt."""
    return "petrified" not in b.dfn.statuses


def before_damage(b: Blow) -> bool:
    from engine import combat_perks
    was = b.amount
    b.amount = combat_perks.before_damage(b.combat, b.dfn, b.amount, b.source, b.rng, b.damage_type)
    b.step(was, "Shared or capped by a perk", False)
    return True


def resistance(b: Blow) -> bool:
    if not (b.source and b.source.legendary.get("penetrating")):               # Penetrating ignores resistances
        was = b.amount
        b.amount *= C.resist_factor(b.dfn, b.damage_type, (b.source.hit_element or b.source.element) if b.source else "")
        b.step(was, "Resistance", False)
    return True


def blood_pact(b: Blow) -> bool:
    if "blood_pact" in b.L:
        was = b.amount
        b.amount *= 1 + b.L["blood_pact"] / 200
        b.step(was, "blood_pact")
    return True


def category_ward(b: Blow) -> bool:
    ward = C.category_bonus(b.dfn, b.L, b.source, "ward")
    if ward:
        was = b.amount
        b.amount *= 1 - min(90, ward) / 100
        b.step(was, f"Ward against {b.source.category}" if b.source and b.source.category else "Ward", False)
    return True


def hardening(b: Blow) -> bool:
    if "hardening" in b.L:
        was = b.amount
        b.amount *= 1 - b.L["hardening"] * min(5, b.dfn.hardening_stacks) / 100
        b.dfn.hardening_stacks += 1
        b.step(was, "hardening")
    return True


def aegis(b: Blow) -> bool:
    if "aegis" in b.L and b.dfn.aegis_round != b.combat.round:
        b.dfn.aegis_round = b.combat.round
        was = b.amount
        b.amount *= 1 - b.L["aegis"] / 100
        b.step(was, "aegis")
    return True


def last_stand(b: Blow) -> bool:
    if "last_stand" in b.L and b.dfn.hp < b.dfn.max_hp / 4:
        was = b.amount
        b.amount *= 0.8
        b.step(was, "last_stand")
    return True


def stoneskin(b: Blow) -> bool:
    if "stoneskin" in b.L:
        was = b.amount
        b.amount *= 1 - min(90, b.L["stoneskin"]) / 100
        b.step(was, "stoneskin")
    return True


def plating(b: Blow) -> bool:
    if "plating" in b.L and b.damage_type == "physical":
        was = b.amount
        b.amount *= 1 - min(90, b.L["plating"]) / 100
        b.step(was, "plating")
    return True


def spellward(b: Blow) -> bool:
    if "spellward" in b.L and b.damage_type == "magical":
        was = b.amount
        b.amount *= 1 - min(90, b.L["spellward"]) / 100
        b.step(was, "spellward")
    return True


def unbroken(b: Blow) -> bool:
    if "unbroken" in b.L:
        was = b.amount
        b.amount = min(b.amount, b.dfn.max_hp * b.L["unbroken"] / 100)
        b.step(was, "unbroken")
    return True


def guardian(b: Blow) -> bool:
    if b.dfn.side == "ally":
        guard = C.mechanics(b.combat.player, b.combat).get("guardian", 0)
        was = b.amount
        b.amount *= 1 - min(90, guard) / 100
        b.step(was, "guardian")
    return True


def companion_durability(b: Blow) -> bool:
    if b.dfn.side == "ally" and C.fights_for_you(b.dfn):
        was = b.amount
        b.amount /= 1 + max(0, C.companion_boost(b.combat, "companion_durability")) / 100
        b.step(was, "Companion durability", False)
    return True


def barrier(b: Blow) -> bool:
    from engine import spellcraft as _scs
    d = b.dfn
    if d.shield > 0 and b.amount > 0 and b.source is not None and _scs.seeping(b.source):
        b.step(b.amount, "Seep: under the barrier", False)     # Seep (f268): straight past it
    elif d.shield > 0 and b.amount > 0:
        soaked = min(d.shield, b.amount)
        d.shield -= soaked
        was = b.amount
        b.amount -= soaked
        b.step(was, "Barrier", False)
        C.tell(b.combat, f"{C.whose(d)} barrier takes the blow" + (" and shatters" if d.shield <= 0 else ""))
    return True


def stoneform(b: Blow) -> bool:
    if "stoneform" in b.L and b.amount > 0 and b.damage_type == "physical":
        was = b.amount
        b.amount *= 1 - min(90, b.L["stoneform"]) / 100          # Stoneform: blows that would cut or crush meet stone
        b.step(was, "Stoneform", False)
    return True


def mana_veil(b: Blow) -> bool:
    d = b.dfn
    if "mana_veil" in b.L and b.amount > 0 and d.mana > 0:
        absorbed = min(d.mana, b.amount * min(90, b.L["mana_veil"]) / 100)    # Mana Shield (f235): point for point, until the mana is gone
        d.mana -= absorbed
        was = b.amount
        b.amount -= absorbed
        b.step(was, "Mana Shield", False)
        if d.mana <= 0:
            for k, bf_ in list(d.buffs.items()):
                if bf_.get("kind") == "manashield":
                    E.end_buff(d, k)
            C.tell(b.combat, f"{C.whose(d)} mana runs dry and the shield breaks")
    return True


def mana_shield(b: Blow) -> bool:
    d = b.dfn
    if "mana_shield" in b.L and b.amount > 0 and d.mana > 1:
        absorbed = min(d.mana / 2, b.amount * min(90, b.L["mana_shield"]) / 100)
        d.mana -= absorbed * 2
        was = b.amount
        b.amount -= absorbed
        b.step(was, "mana_shield")
    return True


def nothing_through(b: Blow) -> bool:
    """Nothing left to land: the path ends with nothing dealt."""
    return b.amount > 0


def ward_conversion(b: Blow) -> bool:
    d = b.dfn
    if "ward_conversion" in b.L and b.damage_type == "magical" and d.max_mana:
        d.mana = min(d.max_mana, d.mana + b.amount * b.L["ward_conversion"] / 100)
    return True


def rounded(b: Blow) -> bool:
    """What is dealt: a whole number, never less than one once something got through."""
    b.dealt = max(1, round(b.amount))
    b.whole = True
    return True


# ---------- the floors: a harm that would end someone, pulled short (stages.yaml floors: every path meets the same ones)

PATH_HARM = {"blow": "blow", "tear": "blow", "rebound": "rebound",   # (f772) a torn wound is its blow's; a tick's harm is its status
             "outright": "outright"}
CARRIED = {"blow": "unnamed", "outright": "outright"}   # (f773) paths a blow may carry, and the word when no carrier is named


def harm(b: Blow) -> str:
    """(f772) What a floor's line calls the harm it held (combat.yaml harms): "the blow", "the poison", "the thorns", or "that" for a
    harm with no word of its own."""
    return C.RULES["harms"][b.harm]


def _held(b: Blow) -> bool:
    """(f772) A floor has held this fighter: noted on the blow in progress, so the rest of that blow takes nothing from it. Ends the
    path."""
    C.hold_in_blow(b.combat, b.dfn)
    return False


def duel_holds(combat: C.Combat | None, d: C.Fighter) -> bool:
    """(f771) A trial of rank holds this fighter above death: one of its duellists (engine/combat.py duellist). Anyone else in it falls
    as in any fight, and decides nothing. The duel's floor asks it on every path (stages.yaml floors)."""
    return combat is not None and combat.duel and C.duellist(combat, d)


def duel_decided(combat: C.Combat, d: C.Fighter) -> None:
    """(f771) Decides the trial for this duellist brought to the floor: a player fighter loses it, the foe loses it to the player; the
    first decision stands."""
    if not combat.over:
        combat.over = "defeat" if d.side == "player" else "victory"
        combat.log.append(f"{d.name} is beaten")


def duel_floor(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if duel_holds(combat, d) and b.landing >= d.hp:
        d.hp = 1
        duel_decided(combat, d)
        C.tell(combat, f"{harm(b)} that would have ended {C.who(d)} is pulled short, and the duel is decided" if b.harm == "blow" else
               f"the trial is called before {C.who(d)} can fall, and the duel is decided" if b.harm == "unnamed" else
               f"the trial is called before {harm(b)} can end {C.who(d)}, and the duel is decided")
        return _held(b)
    return True


def lifeline(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.landing >= d.hp and C.fights_for_you(d) and not d.counters.get("lifeline") \
            and any("lifeline" in C.mechanics(p, combat) for p in combat.player_fighters()):     # (f772) its master, by fighter
        d.counters["lifeline"] = 1
        d.hp = 1
        combat.log.append(f"{d.name} should have fallen - the bond holds it to life (Lifeline)")
        C.tell(combat, f"{harm(b)} should have ended {C.who(d)}, but the bond with its master will not let it fall (Lifeline)")
        return _held(b)
    return True


def tether(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.landing >= d.hp and d.tether:
        d.hp = max(1, round(d.max_hp * d.tether / 100))
        d.tether = 0
        combat.log.append(f"{d.name} should have fallen - the Soul Tether holds it to life")
        C.tell(combat, f"{harm(b)} should have ended {C.who(d)}, but a thread of the master's will draws it back from the brink (Soul Tether)")
        return _held(b)
    return True


def boss_last_stand(b: Blow) -> bool:
    if b.dfn.boss and b.landing >= b.dfn.hp:
        from engine import bosses
        if bosses.last_stand(b.combat, b.dfn):
            return _held(b)
    return True


def breath(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.landing >= d.hp and d.breath:
        d.breath = False
        d.hp, d.mana = d.max_hp, d.max_mana
        combat.log.append(f"{d.name} should have fallen - Orenna's Last Breath restores them in full")
        C.tell(combat, f"{harm(b)} should have killed {C.who(d)}, but a thin, tired warmth catches {C.vb(d, 'you', 'them')}, and "
                       f"{C.vb(d, 'you rise', 'they rise')} whole (Orenna's Last Breath, now spent)")
        return _held(b)
    return True


def mentor_floor(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.landing >= d.hp and d.side == "player" and combat.mentor:
        combat.mentor_saved += 1
        d.hp = 1
        C.tell(combat, f"{harm(b)} should have ended you, but a hand catches you before you fall")
        return _held(b)
    return True


def deathless(b: Blow) -> bool:
    d = b.dfn
    if b.landing >= d.hp and "deathless" in b.L:
        d.hp = 1
        C.tell(b.combat, f"{harm(b)} should have ended {C.who(d)}, but {C.vb(d, 'you are', 'it is')} held on the threshold and will not fall")
        return _held(b)
    return True


def deathward(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.landing >= d.hp and "deathward" in b.L and not d.deathward_used:
        d.deathward_used = True
        d.hp = 1 + round(d.max_hp * b.L["deathward"] / 100)
        combat.log.append(f"{d.name} should have fallen - Deathward holds them to life")
        C.tell(combat, f"{harm(b)} should have killed {C.who(d)}, but a power older than death refuses to let go (Deathward)")
        return _held(b)
    return True


def yields_floor(b: Blow) -> bool:
    """A foe that yields never dies: what would end it lands one short, and it yields (yields_break, after the fall)."""
    d = b.dfn
    if d.yields_at and b.landing >= d.hp:
        b.landing = max(0, round(d.hp) - 1)
        C.hold_in_blow(b.combat, d)
    return True


# ---------- the landing, and what it sets off

def health(b: Blow) -> bool:
    d = b.dfn
    b.up = d.alive
    d.hp = max(0, d.hp - b.dealt)
    from engine import battlefield as bf
    if b.dealt > 0 and b.source is not None and bf.hostile(b.source, d) and b.source is not d:
        d.last_hurt_by = b.source.id
    return True


HOW = {"dot_tick": "tick", "rebound": "rebound"}       # (f768) how a fall on each path is told; a blow's and a torn wound's by who struck


def fall(b: Blow) -> bool:
    """(f768) The health stage just before took this fighter from standing to zero: the fall step, once. The blow's path keeps its
    own die; a tick's, a torn wound's and a rebound's fall uses the death's keyed die."""
    if b.combat is not None and b.up and not b.dfn.alive:
        fall_step(b.combat, b.dfn, b.cause, b.rng if b.path == "blow" else None, HOW.get(b.path), b.dot)
    return True


def after_damage(b: Blow) -> bool:
    from engine import combat_perks
    combat_perks.after_damage(b.combat, b.dfn, b.dealt, b.source)
    return True


def healing_after_damage(b: Blow) -> bool:
    from engine import healing as _heal
    _heal.after_damage(b.combat, b.dfn, b.dealt, b.source)
    return True


def yields_break(b: Blow) -> bool:
    d = b.dfn
    if b.combat is not None and d.yields_at and d.alive and not d.fled and d.hp <= d.max_hp * d.yields_at:
        C.leave(b.combat, d, "fled")
        C.tell(b.combat, d.yield_text or f"{C.who(d)} breaks off and is gone")
    return True


def boss_after_damage(b: Blow) -> bool:
    if b.dfn.boss:
        from engine import bosses
        bosses.bloodied(b.combat, b.dfn)                     # (f768) its fall is the fall step's
    return True


def second_wind(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if "second_wind" in b.L and not d.second_wind_used and 0 < d.hp < d.max_hp / 4:
        d.second_wind_used = True
        heal = round(d.max_hp * b.L["second_wind"] / 100)
        C.restore(combat, d, heal)
        combat.log.append(f"{d.name} finds a second wind: +{heal}")
        C.tell(combat, f"with the end close, {C.who(d)} {C.vb(d, 'find', 'finds')} a second wind and {C.vb(d, 'rise', 'rises')} again")
    return True


def rebound(b: Blow) -> bool:
    """Retribution and Spellmirror: a share of what the blow dealt goes back into its striker, on the rebound's own path (stages.yaml
    rebound: the floors, its health, the fall), which holds no rebound of its own: the loop guard."""
    combat, source = b.combat, b.source
    for effect, applies in (("retribution", True), ("spellmirror", b.damage_type == "magical")):
        if source and effect in b.L and applies and C.reaches(combat, source):
            back = max(1, round(b.dealt * b.L[effect] / 100))
            combat.log.append(f"{effect.capitalize()} returns {back} damage to {source.name}")
            C.tell(combat, f"the force rebounds into {C.who(source)} ({effect.capitalize()})")
            resolve("rebound", combat, source, back, b.dfn, None, cause=b.dfn)     # (f768) a death by it is the wearer's kill
    return True


# ---------- the bypasses: a tick at the start of the turn, a wound torn, a force turned back

def tick_health(b: Blow) -> bool:
    """A poison's or a burn's tick (engine/combat.py start_turn): the amount the perks and the element's expressions set, straight
    through armour and shields."""
    b.up = b.dfn.alive
    b.dfn.hp = max(0, b.dfn.hp - b.amount)
    return True


def tick_on_tick(b: Blow) -> bool:
    if b.combat is not None:
        from engine import spellcraft as _sck
        _sck.on_tick(b.combat, b.dfn, b.dot)
    return True


def rebound_health(b: Blow) -> bool:
    """(f772) The force turned back (the rebound stage): straight to the striker's health, through armour and shields."""
    d = b.dfn
    b.up = d.alive
    d.hp = max(0, d.hp - b.amount)
    b.dealt = round(b.amount)
    return True


def whole_health(b: Blow) -> bool:
    """(f773) A kill outright: what is about to land is all the health the fighter has, whole, past any armour, ward or barrier
    (none stands before the floors on its path), so it ends them unless a floor holds. The health stage takes it."""
    b.amount = b.dfn.hp
    b.dealt = math.ceil(b.dfn.hp)
    b.whole = True
    return True


def tear_health(b: Blow) -> bool:
    """A physical hit lands on an open wound (engine/afflictions.py tear): it bleeds its size times deep, through armour and shields.
    What it took is dealt."""
    d = b.dfn
    before, b.up = d.hp, d.alive
    d.hp = max(0, d.hp - b.amount)
    b.dealt = round(before - d.hp)
    if b.dealt:
        b.combat.log.append(f"{d.name}'s wound tears: {b.dealt}")
        C.tell(b.combat, f"the blow tears {C.whose(d)} wound open again - {b.dealt} more blood lost" + (f" {b.by}" if b.by else ""))
    return True


# ---------- (f768) the fall: the one step every death ends in

HEALTH = ("health", "tick_health", "tear_health", "rebound_health")   # the stages that take health away: `fall` straight after each


def fall_step(combat: C.Combat, f: C.Fighter, cause: C.Fighter | None, rng: random.Random | None = None, how: str | None = None,
              dot: str = "") -> None:
    """(f768) A fighter has fallen: told by its cause and felled_by set, a summon unmade, every tie released, a boss's last words, the
    rout for a foe, Avenger for an ally, and the kill credited (engine/combat.py credit), at once or, for the target of a blow in
    progress, at that blow's tail. rng: the blow's die on its path, else the death's keyed die. how: blow, harm, rebound or tick;
    when not given, a blow if the blow in progress on the fallen is the cause's."""
    from engine import battlefield as bf
    from engine import behaviors, streams
    held = C.open_blow(combat, f)
    how = how or ("blow" if held is not None and cause is held.att else "harm")
    named = cause if cause is not None and cause is not f else None
    rng = rng or streams.keyed("morale", f.id, combat.serial, combat.round)
    if named is not None:
        combat.felled_by[f.id] = C.who(named)
    else:
        combat.felled_by.pop(f.id, None)                  # raised and felled again by no one named: the old killer is not this one
    if how == "blow":
        f.counters.pop("fell_to", None)
    else:
        f.counters["fell_to"] = how                       # read by the hire's lines (services/fight.py): no blow on them
    combat.log.append(f"{f.name} {'succumbs' if how == 'tick' else 'falls'}")
    C.tell(combat, fall_line(f, named, how, dot))         # told before what the fall sets off: a burst, a rout
    if f.summon_form:
        from engine import summons
        summons.on_fall(combat, f, rng)
    bf.release(combat, f)
    if f.boss:
        from engine import bosses
        bosses.fall(combat, f)
    if bf.is_foe(f):
        behaviors.morale_on_death(combat, f, rng)          # (f774) a turned foe's fall routs none of its old side
    if f.side == "ally":
        for p_ in combat.player_fighters():
            if C.mechanics(p_, combat).get("avenger", 0) and not p_.counters.get("avenger_used"):
                p_.counters["avenger_used"] = 1
                p_.counters["avenging"] = 1
                C.tell(combat, f"something goes cold and certain in {C.who(p_)}: the next blow will not miss (Avenger)")
    if held is not None:
        held.fell, held.by = True, cause
    else:
        C.credit(combat, cause, f, rng)


def fall_line(f: C.Fighter, cause: C.Fighter | None, how: str, dot: str = "") -> str:
    """(f768) A fall told by its cause: a blow on one of the player's side names whose blow it was; a rebound is the striker's own
    undoing; a tick says what did its work, and whose; anything else is a plain fall (the line before it says what struck)."""
    if how == "rebound":
        return f"{C.who(f)} {C.vb(f, 'collapse', 'collapses')}, undone by {C.vb(f, 'your', 'its')} own violence"
    if how == "tick" and f.side == "enemy":
        return f"{C.who(f)} succumbs to what was done to {C.vb(f, 'you', 'it')} and falls"
    if how == "tick":
        words = C.RULES["ticks"][dot]                     # combat.yaml ticks: every ticking status has its words (engine/data_check.py)
        what = (words["nobody"].format(fallen=C.who(f)) if cause is None else
                words["laid"].format(whose=C.whose(cause), who=C.who(cause), fallen=C.who(f)))
        return f"{what}. You fall, and the world goes dark" if f.side == "player" else f"{what}, and {C.who(f)} falls and does not rise"
    by = f" to {C.whose(cause)} blow" if how == "blow" and cause is not None and f.side != "enemy" else ""
    return f"{C.who(f)} {C.vb(f, 'fall', 'falls')}{by}" + (", and the world goes dark" if f.side == "player" else " and does not rise")


STAGES: dict[str, Callable[[Blow], bool]] = {
    "petrified": petrified, "before_damage": before_damage, "resistance": resistance, "blood_pact": blood_pact,
    "category_ward": category_ward, "hardening": hardening, "aegis": aegis, "last_stand": last_stand, "stoneskin": stoneskin,
    "plating": plating, "spellward": spellward, "unbroken": unbroken, "guardian": guardian, "companion_durability": companion_durability,
    "barrier": barrier, "stoneform": stoneform, "mana_veil": mana_veil, "mana_shield": mana_shield, "nothing_through": nothing_through,
    "ward_conversion": ward_conversion, "rounded": rounded, "duel_floor": duel_floor, "lifeline": lifeline, "tether": tether,
    "boss_last_stand": boss_last_stand, "breath": breath, "mentor_floor": mentor_floor, "deathless": deathless, "deathward": deathward,
    "yields_floor": yields_floor, "health": health, "fall": fall, "after_damage": after_damage,
    "healing_after_damage": healing_after_damage, "yields_break": yields_break,
    "boss_after_damage": boss_after_damage, "second_wind": second_wind, "rebound": rebound,
    "tick_health": tick_health, "tick_on_tick": tick_on_tick, "tear_health": tear_health, "rebound_health": rebound_health,
    "whole_health": whole_health,
}


def _harm_key(combat, path: str, dfn, source, dot: str, harm: str | None) -> str:
    """(f772) What this harm is called: a tick by its status, a torn wound and a rebound by their path; on a path a blow may carry (the
    blow's, a kill outright's) the blow's own when its striker's blow on its target is in progress, else what the caller named (its
    carrier: a curse), else the path's own word (CARRIED)."""
    if path == "dot_tick":
        return dot
    if path not in CARRIED:
        return PATH_HARM[path]
    blow = C.blow_now(combat)
    if blow is not None and blow.att is source and blow.dfn is dfn:
        return "blow"
    return harm or CARRIED[path]


def resolve(path: str, combat: C.Combat, dfn: C.Fighter, amount: float, source: C.Fighter | None, rng: random.Random,
            damage_type: str = "physical", rec: dict | None = None, dot: str = "", deep: float = 1.0, by: str = "",
            cause=C.AS_SOURCE, harm: str | None = None) -> int:
    """Run one damage path (data/rules/stages.yaml damage) on this fighter, stage by stage, in the order declared. Returns what was
    dealt. `rec` is the blow's record (every stage that changed the figure writes its name into it); `dot` the affliction of a tick;
    `deep` and `by` a torn wound's depth and the perk that deepened it. (f768) `cause`: whose kill a death on this path is, when not
    the source (a tick's layer, a torn wound's striker, Unraveled's layer); None names nobody. (f772) Nothing lands on one who has
    left the fight or whom a floor has held in the blow in progress (engine/combat.py reaches); with no fight, no floor stands.
    `harm`: what side harm on the blow's path is called (a key of combat.yaml harms; None, a harm with no word of its own); the blow's
    own harm, and everything it carries, is the blow."""
    if dfn.alive and not C.reaches(combat, dfn):
        return 0
    b = Blow(combat, dfn, amount, source, rng, damage_type, rec, dot=dot, deep=deep, by=by, path=path,
             cause=source if cause is C.AS_SOURCE else cause, harm=_harm_key(combat, path, dfn, source, dot, harm))
    b.L = C.mechanics(dfn, combat, source)
    for stage in PATHS[path]:
        if combat is None and stage in FLOORS:
            continue
        if STAGES[stage](b) is False:
            break
    return b.dealt
