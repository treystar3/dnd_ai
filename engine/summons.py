"""Summons (f222): beings a magic user creates. Never companions - a companion is a living creature, tamed, that grows with you; a
summon is made out of its caster's power by a summon ability, in a form the engine planned (data/rules/summons.yaml).

Every summon is sized by its caster: health a share of theirs, blows a share of their spell, their element in it. A summon class
keeps exactly one BOUND summon - a lasting creation that walks with it between fights. It may know several Bound spells, but only one
Bound summon exists at a time and it is only switched out of a fight; destroyed in a fight, it stays unmade until the fight is over.
The other forms are made in the fight and last a few rounds: a sentinel that takes your blows, a striker, a swarm, a totem that
pulses, a decoy, a volatile thing that bursts. At most `standing` of them at once."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine import combat as C

ROOT = Path(__file__).resolve().parent.parent
S = yaml.safe_load((ROOT / "data" / "rules" / "summons.yaml").read_text(encoding="utf-8"))
FORMS = S["forms"]


def is_summon(f) -> bool:
    return bool(getattr(f, "summon_form", ""))


def form_of(move) -> str:
    return getattr(move, "summon_form", "") or "striker"


def mine(combat: C.Combat, owner: C.Fighter | None = None) -> list[C.Fighter]:
    """The summons standing for this caster (the player when none is named), oldest first."""
    oid = (owner or combat.player).id
    return [f for f in combat.fighters if is_summon(f) and f.summon_owner == oid and f.alive]


def bound_of(combat: C.Combat, owner: C.Fighter | None = None) -> C.Fighter | None:
    return next((f for f in mine(combat, owner) if f.summon_form == "bound"), None)


def made(combat: C.Combat, owner: C.Fighter | None = None) -> list[C.Fighter]:
    """The fight-made summons standing (not the Bound one), oldest first."""
    return [f for f in mine(combat, owner) if f.summon_form != "bound"]


def yours(combat: C.Combat) -> C.Fighter | None:
    """'Your summon', for the perks: the Bound summon first, else the newest one made in this fight."""
    b = bound_of(combat)
    if b is not None:
        return b
    m = made(combat)
    return m[-1] if m else None


def spell_of(att: C.Fighter, move) -> float:
    """The caster's spell before the attribute: base power for their level plus their spell power."""
    focus = (att.weapon_damage if att.damage_type == "magical" else 0) + att.offhand_spell + C.flat_bonus(att, "spell_power", {"always"})
    return C.RULES["spell_base_damage"] * C.growth(att.level) + focus


def make(combat: C.Combat, att: C.Fighter, move, form: str | None = None, tier: str | None = None, until: int | None = None,
         name: str = "") -> list[C.Fighter]:
    """Build a summon's body (or bodies) from its caster. `until` is the round it fades (0: never)."""
    form = form or form_of(move)
    spec = FORMS.get(form, FORMS["striker"])
    tier = tier or move.tier
    bodies = int(spec.get("bodies", 1))
    hp = att.max_hp * S["health"].get(tier, 30) / 100 * spec["health"] / bodies
    dmg = spell_of(att, move) * S["damage"].get(tier, 60) / 100 * spec["damage"] / bodies
    if until is None:
        until = 0 if form == "bound" else combat.round + S["rounds"].get(tier, 3)
    cast_attr = getattr(move, "attribute", "") or "intelligence"
    base = name or getattr(move, "summon_name", "") or move.name
    out, serial = [], len(combat.fighters)
    for i in range(bodies):
        f = C.Fighter(id=f"summon_{move.id}_{combat.round}_{i}_{len(combat.fighters)}", name=base if bodies == 1 else f"{base} ({i + 1})",
                      side="ally", level=att.level, attrs=dict(att.attrs), hp=max(1.0, hp), max_hp=max(1, round(hp)),
                      weapon_name="strike", weapon_damage=dmg, weapon_attrs=[cast_attr], damage_type="magical",
                      element=getattr(move, "element", "") or "", armor=att.armor * S["defense"], ward=att.ward * S["defense"],
                      reach="ranged" if spec.get("pulse") is not None else "melee", behaviors={"fearless": 1}, hold=1 if spec.get("intercept") else 0)
        f.summon_form, f.summon_owner, f.summon_of, f.summon_until, f.summon_tier = form, att.id, move.id, until, tier
        f.summon_cast = serial                                  # the bodies of one casting share it
        out.append(f)
    return out


def refuse(combat: C.Combat, att: C.Fighter, move) -> str | None:
    """Why this summon ability cannot be cast in this fight right now, before anything is spent - or None."""
    if form_of(move) != "bound" or att.side != "player":
        return None
    standing = bound_of(combat, att)
    if standing is not None and standing.summon_of != move.id:
        return f"{standing.name} is your Bound summon, and a Bound summon cannot be changed in the middle of a fight."
    if standing is None and combat.bound_fell:
        return "Your Bound summon was destroyed in this fight; it cannot be made again until the fight is over."
    if standing is None and combat.bound_id and combat.bound_id != move.id:
        return "Another Bound spell holds your bond; a Bound summon can only be changed outside a fight."
    return None


def cast(combat: C.Combat, att: C.Fighter, move, rng: random.Random) -> None:
    """A summon ability, cast in a fight (refuse() has already been asked)."""
    from engine import combat_perks
    form = form_of(move)
    if form == "bound":
        standing = bound_of(combat, att)
        if standing is not None:
            healed, _ = combat_perks.mend(combat, att, standing, standing.max_hp * S["bound_restore"])
            combat.log.append(f"{att.name} uses {move.name}: {standing.name} restored ({healed})")
            C.tell(combat, f"{C.who(att)} {C.vb(att, 'pour', 'pours')} power into {move.name}, and {standing.name} knits back together ({healed})")
            return
        for f in make(combat, att, move):
            C.enters(combat, f)
        combat.bound_id = move.id
        combat.log.append(f"{att.name} uses {move.name}: the Bound summon takes shape")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'call', 'calls')} on {move.name}, and {C.whose(att)} Bound summon takes shape beside {C.who(att)}")
        return
    if combat_perks.unmaking(combat, att, move, rng):
        return                                               # the standing one came apart in a burst instead
    standing = made(combat, att)
    bodies = make(combat, att, move)
    room = S["standing"]
    groups = []                                               # the made summons, grouped by the casting that made them
    for f in standing:
        key = f.summon_cast
        if not groups or groups[-1][0] != key:
            groups.append((key, []))
        groups[-1][1].append(f)
    while len(groups) >= room:
        _, old = groups.pop(0)
        for f in old:
            disperse(combat, f, rng, "lets go of it to make room")
    for f in bodies:
        C.enters(combat, f)
    spec = FORMS.get(form, {})
    combat.log.append(f"{att.name} uses {move.name}: {len(bodies)} {form} summon(s) for {S['rounds'].get(move.tier, 3)} rounds")
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'call', 'calls')} up {move.name} - {spec.get('depict', 'a summoned thing')}")


def disperse(combat: C.Combat, f: C.Fighter, rng: random.Random, why: str = "fades") -> None:
    """A fight-made summon's time is up (or its caster lets it go): it is gone, bursting first if it is the volatile kind."""
    if not f.alive:
        return
    burst(combat, f, rng)
    f.hp = 0
    f.counters["dead"] = 1
    from engine import battlefield as bf
    bf.release(combat, f)
    combat.log.append(f"{f.name} {why}")
    C.tell(combat, f"{f.name} {why}")


def burst(combat: C.Combat, f: C.Fighter, rng: random.Random) -> None:
    spec = FORMS.get(f.summon_form, {})
    if not spec.get("burst") or f.counters.get("burst"):
        return
    f.counters["burst"] = 1
    from engine import battlefield as bf
    victims = [e for e in bf.standing(combat, f.zone_id) if e.alive and bf.hostile(f, e)] if combat.battlefield else combat.enemies()
    held, f.hit_element = f.hit_element, f.element
    for e in victims:
        hit, _ = C.mitigate(e, f.weapon_damage * spec["burst"], "magical", f.level, combat, f)
        combat.log.append(f"{f.name} bursts over {e.name}: {C.take_damage(combat, e, hit, f, rng, 'magical')}")
    f.hit_element = held
    if victims:
        C.tell(combat, f"{f.name} bursts apart" + (f" in {f.element}" if f.element else "") + f", and the blast takes {', '.join(C.who(e) for e in victims)}")


def on_fall(combat: C.Combat, f: C.Fighter, rng: random.Random) -> None:
    """A summon destroyed: the volatile kind bursts; a Bound summon stays unmade until the fight is over."""
    if f.counters.get("fell"):
        return
    f.counters["fell"] = 1
    f.counters["dead"] = 1                                    # a summon is unmade, not hurt: nothing raises it in the fight
    burst(combat, f, rng)
    if f.summon_form == "bound" and f.summon_owner == combat.player.id:
        combat.bound_fell = True


def turn(combat: C.Combat, a: C.Fighter, rng: random.Random) -> bool:
    """A summon's own turn, where its form decides it. True when the form took the turn (else it strikes like any ally)."""
    if a.summon_until and combat.round >= a.summon_until:
        disperse(combat, a, rng)
        return True
    spec = FORMS.get(a.summon_form, {})
    if spec.get("pulse") is not None and spec.get("still"):
        from engine import battlefield as bf
        if a.element:
            victims = [e for e in bf.standing(combat, a.zone_id) if e.alive and bf.hostile(a, e)] if combat.battlefield else combat.enemies()
            held, a.hit_element = a.hit_element, a.element
            for e in victims:
                hit, _ = C.mitigate(e, a.weapon_damage * spec["pulse"], "magical", a.level, combat, a)
                combat.log.append(f"{a.name} pulses {a.element} into {e.name}: {C.take_damage(combat, e, hit, a, rng, 'magical')}")
            a.hit_element = held
            C.tell(combat, f"{a.name} pulses, and {a.element} washes over " + (", ".join(C.who(e) for e in victims) if victims else "empty ground"))
        else:
            pct = spec["empower"].get(a.summon_tier, 10)
            near = [f for f in [combat.player] + combat.allies() if f.alive and f is not a and (not combat.battlefield or f.zone_id == a.zone_id)]
            for f in near:
                f.buffs["totem_urge"] = {"rounds": 2, "mech": {"empowered": pct}, "drain": 0, "collapse": "", "name": a.name, "kind": "bolster"}
            combat.log.append(f"{a.name} urges its allies on: +{pct}%")
            C.tell(combat, f"{a.name} pulses, and the fighters around it strike harder (+{pct}%)")
        return True
    if spec.get("still"):
        return True                                           # a decoy only stands there being looked at
    return False


def redirect(combat: C.Combat, e: C.Fighter, target: C.Fighter, rng: random.Random) -> C.Fighter:
    """Summons that pull blows: a decoy draws an enemy's attack some of the time; a sentinel takes the blows meant for its caster."""
    from engine import battlefield as bf
    standing = [f for f in combat.allies() if is_summon(f)]
    decoys = [f for f in standing if FORMS.get(f.summon_form, {}).get("draw") and f is not target
              and (not combat.battlefield or bf.attack_access(combat, e, f).ok or bf.attack_access(combat, e, f).can_approach)]
    if decoys and rng.random() < FORMS[decoys[0].summon_form]["draw"]:
        d = rng.choice(decoys)
        combat.log.append(f"{e.name} is drawn to {d.name}")
        C.tell(combat, f"{C.who(e)} turns on {d.name} instead")
        return d
    if target.side == "player":
        guards = [f for f in standing if FORMS.get(f.summon_form, {}).get("intercept") and f.summon_owner == target.id
                  and (not combat.battlefield or f.zone_id == target.zone_id)]
        if guards:
            g = guards[0]
            combat.log.append(f"{g.name} intercepts the blow meant for {target.name}")
            C.tell(combat, f"{g.name} steps into the blow meant for {C.who(target)}")
            return g
    return target


# ---------- around the fight ----------

def join_bound(fight: C.Combat, character) -> None:
    """The player's Bound summon walks into the fight with them, whole - unless it was destroyed and not yet made again."""
    fight.bound_id = getattr(character, "bound_summon", "") or ""
    if not fight.bound_id or getattr(character, "bound_broken", False):
        return
    p = fight.player
    move = next((m for m in p.moves if m.id == fight.bound_id and form_of(m) == "bound"), None)
    if move is None:
        return
    fight.fighters += make(fight, p, move, until=0)


def after_fight(character, fight: C.Combat) -> str:
    """A Bound summon destroyed in the fight stays unmade until its spell is cast again. Returns a note, or ''."""
    if fight.bound_fell and getattr(character, "bound_summon", ""):
        character.bound_broken = True
        return "Your Bound summon was unmade in the fight. Cast its spell again to make it anew."
    return ""


def form_outside(character, ability) -> str:
    """A Bound spell cast outside a fight: it makes the Bound summon anew, or switches the bond to this spell's creation."""
    old = next((a for a in character.actives if a.id == character.bound_summon), None)
    name = getattr(ability, "summon_name", "") or ability.name
    if old is not None and old.id == ability.id:
        if character.bound_broken:
            character.bound_broken = False
            return f"{name} takes shape again, whole, and stands with them."
        return f"{name} is already with them; the casting only steadies it."
    character.bound_summon, character.bound_broken = ability.id, False
    if old is not None:
        return f"{getattr(old, 'summon_name', '') or old.name} comes apart, and {name} takes its place - their Bound summon now."
    return f"{name} takes shape for the first time and is bound to them."
