"""(f504) One damage calculation, declared stage by stage. data/rules/stages.yaml names the stages of each damage path in order (the
blow, a poison's or a burn's tick, a wound torn); STAGES here names the function behind each id, and engine/data_check.py holds the two
to each other: a stage the data names must have a function, and a function here must be named by a path. Each stage reads and writes
one Blow (the shared locals of engine/combat.py take_damage, so nothing is stale), keeps take_damage's labels and its 0.5 threshold for
the record (step), and returns False to end the path (a floor that held, a petrified target, nothing left to land). The retribution
and spellmirror rebound writes the striker's health directly, as take_damage does: that write is the loop guard.

Not yet wired (f504): take_damage, the tick in start_turn and afflictions.tear still run their own lines; resolve("blow") is held equal
to take_damage on a battery of random blows (tools/sim/tables_504_test.py). f505 makes them call resolve, the fixtures the proof."""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import yaml

from engine import combat as C
from engine import items

PATHS: dict[str, list[str]] = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "stages.yaml")
                                             .read_text(encoding="utf-8"))["damage"]

NAMED = {"blood_pact": "Blood Pact", "hardening": "Hardening", "aegis": "Aegis", "last_stand": "Last Stand", "stoneskin": "Stoneskin",
         "plating": "Plating", "spellward": "Spellward", "unbroken": "Unbroken", "guardian": "Guardian", "mana_shield": "Mana shield"}


@dataclass
class Blow:
    """The shared locals of one damage path: the fight, the one struck, what is coming (amount, a float until it is rounded to what is
    dealt), who struck, the die, the kind of damage, the blow's record (None when blows are not being recorded), the struck one's active
    mechanics (L), and for a tick the affliction and the floor under the health bar."""
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
    floor: int = 0
    deep: float = 1.0
    by: str = ""

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
                    d.buffs.pop(k)
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
    return True


# ---------- the floors: a blow that would end someone, pulled short

def duel_floor(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if combat.duel and b.dealt >= d.hp:
        d.hp = 1
        combat.over = "defeat" if d.side == "player" else "victory"
        combat.log.append(f"{d.name} is beaten")
        C.tell(combat, f"the blow that would have ended {C.who(d)} is pulled short, and the duel is decided" if d.side != "player" else
               "the blow that would have ended you is pulled short, and the duel is decided")
        return False
    return True


def lifeline(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.dealt >= d.hp and C.fights_for_you(d) and "lifeline" in C.mechanics(combat.player, combat) and not d.counters.get("lifeline"):
        d.counters["lifeline"] = 1
        d.hp = 1
        combat.log.append(f"{d.name} should have fallen - the bond holds it to life (Lifeline)")
        C.tell(combat, f"the blow should have ended {C.who(d)}, but the bond with its master will not let it fall (Lifeline)")
        return False
    return True


def tether(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.dealt >= d.hp and d.tether:
        d.hp = max(1, round(d.max_hp * d.tether / 100))
        d.tether = 0
        combat.log.append(f"{d.name} should have fallen - the Soul Tether holds it to life")
        C.tell(combat, f"the blow should have ended {C.who(d)}, but a thread of the master's will draws it back from the brink (Soul Tether)")
        return False
    return True


def boss_last_stand(b: Blow) -> bool:
    if b.dfn.boss and b.dealt >= b.dfn.hp:
        from engine import bosses
        if bosses.last_stand(b.combat, b.dfn):
            return False
    return True


def breath(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.dealt >= d.hp and d.breath:
        d.breath = False
        d.hp, d.mana = d.max_hp, d.max_mana
        combat.log.append(f"{d.name} should have fallen - Orenna's Last Breath restores them in full")
        C.tell(combat, f"the blow should have killed {C.who(d)} - but a thin, tired warmth catches them, and {C.vb(d, 'you rise', 'they rise')} whole, health and strength restored (Orenna's Last Breath, now spent)")
        return False
    return True


def mentor_floor(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.dealt >= d.hp and d.side == "player" and combat.mentor:
        combat.mentor_saved += 1
        d.hp = 1
        C.tell(combat, "the blow should have ended you, but a hand pulls you aside at the last instant")
        return False
    return True


def deathless(b: Blow) -> bool:
    d = b.dfn
    if b.dealt >= d.hp and "deathless" in b.L:
        d.hp = 1
        C.tell(b.combat, f"the blow should have ended {C.who(d)}, but {C.vb(d, 'you are', 'it is')} held on the threshold and will not fall")
        return False
    return True


def deathward(b: Blow) -> bool:
    d, combat = b.dfn, b.combat
    if b.dealt >= d.hp and "deathward" in b.L and not d.deathward_used:
        d.deathward_used = True
        d.hp = 1 + round(d.max_hp * b.L["deathward"] / 100)
        combat.log.append(f"{d.name} should have fallen - Deathward holds them to life")
        C.tell(combat, f"the blow should have killed {C.who(d)} - but a power older than death refuses to let go (Deathward)")
        return False
    return True


def yields_floor(b: Blow) -> bool:
    d = b.dfn
    if d.yields_at and b.dealt >= d.hp:
        b.dealt = max(0, round(d.hp) - 1)
    return True


# ---------- the landing, and what it sets off

def health(b: Blow) -> bool:
    d = b.dfn
    d.hp = max(0, d.hp - b.dealt)
    if b.dealt > 0 and b.source is not None and b.source.side != d.side and b.source is not d:
        d.last_hurt_by = b.source.id
    return True


def on_fall(b: Blow) -> bool:
    if b.dfn.summon_form and not b.dfn.alive:
        from engine import summons
        summons.on_fall(b.combat, b.dfn, b.rng)              # unmade: the volatile kind bursts; a Bound summon is gone until the fight ends
    return True


def after_damage(b: Blow) -> bool:
    from engine import combat_perks
    combat_perks.after_damage(b.combat, b.dfn, b.dealt, b.source)
    return True


def healing_after_damage(b: Blow) -> bool:
    from engine import healing as _heal
    _heal.after_damage(b.combat, b.dfn, b.dealt, b.source)
    return True


def release(b: Blow) -> bool:
    if not b.dfn.alive:
        from engine import battlefield as bf
        bf.release(b.combat, b.dfn)                          # the fallen hold nobody, and nobody is tied up with them
    return True


def morale(b: Blow) -> bool:
    if not b.dfn.alive and b.dfn.side == "enemy":
        from engine import behaviors as _bh
        _bh.morale_on_death(b.combat, b.dfn, b.rng)
    return True


def avenger(b: Blow) -> bool:
    if not b.dfn.alive and b.dfn.side == "ally":
        p_ = b.combat.player
        av = C.mechanics(p_, b.combat).get("avenger", 0)
        if av and not p_.counters.get("avenger_used"):
            p_.counters["avenger_used"] = 1
            p_.counters["avenging"] = 1
            C.tell(b.combat, f"something goes cold and certain in {C.who(p_)}: the next blow will not miss (Avenger)")
    return True


def yields_break(b: Blow) -> bool:
    d = b.dfn
    if d.yields_at and d.alive and not d.fled and d.hp <= d.max_hp * d.yields_at:
        from engine import battlefield as bf
        d.fled = True
        bf.release(b.combat, d)
        C.tell(b.combat, d.yield_text or f"{C.who(d)} breaks off and is gone")
    return True


def boss_after_damage(b: Blow) -> bool:
    if b.dfn.boss:
        from engine import bosses
        bosses.after_damage(b.combat, b.dfn)
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
    """Retribution and Spellmirror: the striker's health written directly, the loop guard (a rebound never rebounds)."""
    combat, source = b.combat, b.source
    for effect, applies in (("retribution", True), ("spellmirror", b.damage_type == "magical")):
        if source and effect in b.L and applies and source.alive:
            back = max(1, round(b.dealt * b.L[effect] / 100))
            source.hp = max(0, source.hp - back)
            combat.log.append(f"{effect.capitalize()} returns {back} damage to {source.name}")
            C.tell(combat, f"the force rebounds into {C.who(source)} ({effect.capitalize()})")
            if not source.alive:
                combat.log.append(f"{source.name} falls")
                C.tell(combat, f"{C.who(source)} {C.vb(source, 'collapse', 'collapses')}, undone by {C.vb(source, 'your', 'its')} own violence")
    return True


# ---------- the bypasses: a tick at the start of the turn, a wound torn

def tick_floor(b: Blow) -> bool:
    """The first hunt cannot kill the player; a duel kills no one."""
    combat, d = b.combat, b.dfn
    b.floor = 1 if (combat is not None and ((combat.mentor and d.side == "player") or combat.duel)) else 0
    return True


def tick_health(b: Blow) -> bool:
    """A poison's or a burn's tick (engine/combat.py start_turn): the amount the perks and the element's expressions set, straight
    through armour and shields, never below the floor."""
    b.dfn.hp = max(b.floor, b.dfn.hp - b.amount)
    return True


def tick_on_tick(b: Blow) -> bool:
    if b.combat is not None:
        from engine import spellcraft as _sck
        _sck.on_tick(b.combat, b.dfn, b.dot)
    return True


def tick_duel_end(b: Blow) -> bool:
    combat, d = b.combat, b.dfn
    if combat is not None and combat.duel and d.hp <= 1 and not combat.over:
        combat.over = "defeat" if d.side == "player" else "victory"
    return True


def tear_health(b: Blow) -> bool:
    """A physical hit lands on an open wound (engine/afflictions.py tear): it bleeds its size times deep, through armour and shields.
    What it took is dealt."""
    d = b.dfn
    before = d.hp
    d.hp = max(b.floor, d.hp - b.amount)
    b.dealt = round(before - d.hp)
    if b.dealt:
        b.combat.log.append(f"{d.name}'s wound tears: {b.dealt}")
        C.tell(b.combat, f"the blow tears {C.whose(d)} wound open again - {b.dealt} more blood lost" + (f" {b.by}" if b.by else ""))
    return True


STAGES: dict[str, Callable[[Blow], bool]] = {
    "petrified": petrified, "before_damage": before_damage, "resistance": resistance, "blood_pact": blood_pact,
    "category_ward": category_ward, "hardening": hardening, "aegis": aegis, "last_stand": last_stand, "stoneskin": stoneskin,
    "plating": plating, "spellward": spellward, "unbroken": unbroken, "guardian": guardian, "companion_durability": companion_durability,
    "barrier": barrier, "stoneform": stoneform, "mana_veil": mana_veil, "mana_shield": mana_shield, "nothing_through": nothing_through,
    "ward_conversion": ward_conversion, "rounded": rounded, "duel_floor": duel_floor, "lifeline": lifeline, "tether": tether,
    "boss_last_stand": boss_last_stand, "breath": breath, "mentor_floor": mentor_floor, "deathless": deathless, "deathward": deathward,
    "yields_floor": yields_floor, "health": health, "on_fall": on_fall, "after_damage": after_damage,
    "healing_after_damage": healing_after_damage, "release": release, "morale": morale, "avenger": avenger, "yields_break": yields_break,
    "boss_after_damage": boss_after_damage, "second_wind": second_wind, "rebound": rebound,
    "tick_floor": tick_floor, "tick_health": tick_health, "tick_on_tick": tick_on_tick, "tick_duel_end": tick_duel_end,
    "tear_health": tear_health,
}


def resolve(path: str, combat: C.Combat, dfn: C.Fighter, amount: float, source: C.Fighter | None, rng: random.Random,
            damage_type: str = "physical", rec: dict | None = None, dot: str = "", deep: float = 1.0, by: str = "") -> int:
    """Run one damage path (data/rules/stages.yaml damage) on this fighter, stage by stage, in the order declared. Returns what was
    dealt. `rec` is the blow's record (every stage that changed the figure writes its name into it); `dot` the affliction of a tick;
    `deep` and `by` a torn wound's depth and the perk that deepened it."""
    b = Blow(combat, dfn, amount, source, rng, damage_type, rec, dot=dot, deep=deep, by=by)
    b.L = C.mechanics(dfn, combat, source)
    for stage in PATHS[path]:
        if STAGES[stage](b) is False:
            break
    return b.dealt
