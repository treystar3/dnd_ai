"""(f396) What a hire can do besides a plain blow (party.yaml kits), and a priest's care outside a fight (party.yaml tending).

Why: a hired fighter, archer, rogue or mage fought with one plain blow, and a priest healed a twelfth of a wound every fourth round once
someone was badly hurt: a player who hired a priest never saw them heal. Now each role has two techniques, used on the hire's own
judgement: the engine decides when, the numbers are data, and the narrator is told the technique by name. Support (heal, bless, guard)
is weighed before the hire looks for a foe; offence (strike, hinder, burst, spell) once they have one in reach.

(f400) A hire who casts (party.yaml casting: a mage, a priest) casts the player's spells (engine/spells.py) at the highest rank their
level allows, through the same engine a player's spell goes through: its rank and form set its damage or its heal, its flat mana cost
comes out of a pool like a player's, its form sets its cooldown. Each rank has a name of its own in the kit, so a rank shows in play."""
from __future__ import annotations

import random

from engine import combat as C, spells
from engine.party import P

SUPPORT = ("heal", "bless", "guard")
OFFENCE = ("strike", "hinder", "burst", "spell")
SPELLS = ("heal", "spell")                                        # (f400) what a hire casts as a ranked spell


def kit(role: str) -> list[dict]:
    return list((P.get("kits") or {}).get(role or "") or [])


def healing(role: str) -> dict | None:
    """A role's heal, if it has one: what an order to heal and a priest's care outside a fight are measured by."""
    return next((t for t in kit(role) if t["does"] == "heal"), None)


def casts(role: str) -> str:
    """(f400) The attribute a role casts with, or '' for a role that does not cast."""
    return str(((P.get("casting") or {}).get("roles") or {}).get(role or "", ""))


def name_of(t: dict, level: int = 1) -> str:
    """A technique's name; a spell's, by the rank the hire's level allows (party.yaml kits names, one per rank)."""
    names = t.get("names") or []
    if names:
        return names[min(len(names), spells.highest_rank(level)) - 1]
    return t.get("name") or t["id"]


def move_of(t: dict, level: int, role: str) -> C.Move:
    """(f400) A hire's spell, as the engine casts it: the player's spell of the same rank and form, cast with the role's attribute."""
    r = spells.highest_rank(level)
    common = dict(id=f"kit_{t['id']}", name=name_of(t, level), tier=spells.tier_for(r), resource="mana", attribute=casts(role) or "wisdom",
                  rank=r, line=t["id"])
    if t["does"] == "heal":
        form = t.get("form", "mend")
        return C.Move(effect="healing", reach="extended", heal_form=form,
                      cooldown=int(spells.S["healing"]["forms"].get(form, {}).get("cooldown", 1)), **common)
    form = t.get("form", "bolt")
    area = spells.FORMS[form]["delivery"] in ("area", "around")
    return C.Move(effect="damage", reach="area" if area else "ranged", spell_form=form, cooldown=spells.cooldown(form),
                  cast_turns=spells.cast_turns(form), **common)


def equip(f: C.Fighter, member: dict, minutes: int | None = None) -> None:
    """(f400) A hire who casts: mana as a player of their level and casting attribute has (what is left of it since the last fight), the
    share of a spell they cast for, and their spells as moves."""
    from engine import party, pools
    attr = casts(member.get("role", ""))
    if not attr:
        return
    f.max_mana = pools.mana_of(f.level, f.attrs, attr)
    f.mana = f.max_mana * (party.mana_now(member, minutes) if member.get("permanent") else 1.0)
    f.spell_share = float((P.get("casting") or {}).get("power", 1.0))
    f.moves = [move_of(t, f.level, member.get("role", "")) for t in kit(member.get("role", "")) if t["does"] in SPELLS]


def spell(a: C.Fighter, t: dict) -> C.Move | None:
    m = next((m for m in a.moves if m.id == f"kit_{t['id']}"), None)
    if m is None and casts(a.ally_role) and not any(x.id.startswith("kit_") for x in a.moves):
        equip(a, {"role": a.ally_role})          # a hire made before spells had ranks (a fight saved then): their spells now, mana full
        m = next((m for m in a.moves if m.id == f"kit_{t['id']}"), None)
    return m


WHAT = {"heal": "heals the hurt", "bless": "the party strikes harder", "guard": "shields you when you are hurt",
        "strike": "a heavier blow", "hinder": "slows a foe", "burst": "hits every foe bunched together"}


def describe(role: str, level: int = 1) -> str:
    """'Healing Word (heals the hurt), Blessing (the party strikes harder)': what a hire of this role can do, for the panes. (f400) A spell
    says its rank and form: 'Shattering Ring (rank III blast: strikes every foe in the target's area...)'."""
    out = []
    for t in kit(role):
        if t["does"] == "spell":
            what = f"rank {spells.numeral(spells.highest_rank(level))} {spells.FORMS[t['form']]['label'].lower()}: " \
                   + spells.form_text(t["form"]).rstrip(".")
        elif t["does"] == "heal" and t.get("form"):
            what = f"rank {spells.numeral(spells.highest_rank(level))} heal"
        else:
            what = "a heavy blow at a foe busy with someone else" if t.get("engaged") else WHAT.get(t["does"], t["does"])
        out.append(f"{name_of(t, level)} ({what})")
    return ", ".join(out)


def ready(a: C.Fighter, t: dict) -> bool:
    if t["does"] in SPELLS:
        m = spell(a, t)
        return m is not None and C.can_use(a, m) is None          # its cooldown, and the mana for it
    if t["does"] == "bless" and a.max_mana and a.mana < spells.buff_mana(a.level):
        return False                                              # a blessing is a buff: a buff's mana
    return a.cooldowns.get(t["id"], 0) <= 0


def spend(a: C.Fighter, t: dict) -> None:
    if t["does"] in SPELLS:
        return                                                    # the engine paid for the spell and set its cooldown
    if t["does"] == "bless" and a.max_mana:
        a.mana = max(0.0, a.mana - spells.buff_mana(a.level))
    a.cooldowns[t["id"]] = int(t.get("cooldown", 0)) + 1           # the round it is used counts, as for every ability


def support(combat: C.Combat, a: C.Fighter, rng: random.Random) -> bool:
    """A heal, a blessing or a shield, when one is ready and called for. True if it took the hire's turn."""
    for t in kit(a.ally_role):
        if t["does"] in SUPPORT and ready(a, t) and DOES[t["does"]](combat, a, t, rng):
            spend(a, t)
            return True
    return False


def offence(combat: C.Combat, a: C.Fighter, target: C.Fighter, mult: float, rng: random.Random) -> bool:
    """A technique at the foe in reach, when one is ready and fits. True if it took the hire's turn."""
    for t in kit(a.ally_role):
        if t["does"] in OFFENCE and ready(a, t) and DOES[t["does"]](combat, a, t, rng, target=target, mult=mult):
            spend(a, t)
            return True
    return False


def heal_amount(f: C.Fighter, t: dict) -> float:
    """A heal technique without a rank: its share of the target's health (party.yaml pct)."""
    return f.max_hp * float(t.get("pct", 0)) / 100


def cast_heal(combat: C.Combat, a: C.Fighter, t: dict, target: C.Fighter, rng: random.Random) -> bool:
    """(f400) A hire's heal on someone: a ranked heal cast as the player's is, paid from their mana. True if it was cast."""
    m = spell(a, t)
    if m is None:
        if not t.get("pct"):
            return False
        heal_on(combat, a, target, heal_amount(target, t), name_of(t, a.level))
        return True
    return C.act_ability(combat, a, m, None, rng, give=[target]) is None


def _heal(combat, a, t, rng, **_) -> bool:
    p = combat.player
    below = float(t.get("below", 1.0))
    if p.alive and p.hp < p.max_hp * below:
        who_ = p
    else:
        hurt = [f for f in combat.allies() if f.alive and f is not a and f.hp < f.max_hp * below]
        if not hurt:
            return False
        who_ = min(hurt, key=lambda f: f.hp / max(1, f.max_hp))
    return cast_heal(combat, a, t, who_, rng)


def _spell(combat, a, t, rng, target=None, **_) -> bool:
    """(f400) A hire's damage spell at the foe in reach: an area form only when foes are bunched in the target's area (`foes`)."""
    m = spell(a, t)
    if m is None or target is None or not target.alive:
        return False
    if m.reach == "area" and sum(1 for e in combat.enemies() if e.alive and e.zone_id == target.zone_id) < int(t.get("foes", 2)):
        return False
    return C.act_ability(combat, a, m, target, rng) is None


def heal_on(combat: C.Combat, a: C.Fighter, target: C.Fighter, amount: float, name: str) -> None:
    from engine import combat_perks
    landed, _ = combat_perks.mend(combat, a, target, amount)       # one path for every heal: withering and perks apply
    a.counters["healed_round"] = combat.round                      # healing draws the eye
    combat.log.append(f"{a.name} uses {name} on {target.name}: +{round(landed)}")
    rec = C.new_heal(combat, target, f"uses {name} on", "health", round(landed), [[name, f"+{round(landed)} health"]])
    if rec:
        rec["att"], rec["att_side"] = a.name, a.side
    C.tell(combat, f"{C.who(a)} {C.vb(a, 'speak', 'speaks')} a {name.lower()} over {C.who(target)}, and the wounds close ({name})", rec)


def _bless(combat, a, t, rng, **_) -> bool:
    if combat.round > 2 or not combat.enemies():
        return False
    until, pct = combat.round + int(t.get("rounds", 3)), int(t.get("pct", 0))
    for f in [combat.player] + combat.allies():
        if f.alive:
            f.counters["blessed"] = [until, pct]
    combat.log.append(f"{a.name} uses {name_of(t, a.level)}: the party strikes {pct}% harder until round {until}")
    C.tell(combat, f"{C.who(a)} {C.vb(a, 'raise', 'raises')} a hand and {C.vb(a, 'speak', 'speaks')} a blessing over you all, and every arm "
                   f"feels surer for it ({name_of(t, a.level)})")
    return True


def blessed(f: C.Fighter, combat: C.Combat) -> float:
    """The multiplier a blessing gives this fighter's blows now (1.0 when none)."""
    b = f.counters.get("blessed")
    return 1 + b[1] / 100 if b and b[0] >= combat.round else 1.0


def _guard(combat, a, t, rng, **_) -> bool:
    p = combat.player
    if not p.alive or p.hp >= p.max_hp * float(t.get("below", 1.0)) or a.zone_id != p.zone_id or a.covering:
        return False
    if not any(e.alive and not e.fled for e in combat.enemies()):
        return False
    a.covering = p.id
    combat.log.append(f"{a.name} uses {t['name']}: blows meant for {p.name} land on them")
    C.tell(combat, f"{C.who(a)} {C.vb(a, 'plant', 'plants')} a shield in front of you, and whatever comes for you will have to go through "
                   f"{'you' if a.side == 'player' else 'them'} first ({t['name']})")
    return True


def _strike(combat, a, t, rng, target=None, mult=1.0, **_) -> bool:
    if target is None or not target.alive:
        return False
    if t.get("engaged") and not any(x != a.id for x in target.engaged_with):
        return False                                              # a backstab wants a foe already busy with someone else
    C.apply_damage(combat, a, target, mult * float(t.get("power", 1.0)), f"uses {t['name']} on", rng, how=f"with {t['name']}")
    return True


def _hinder(combat, a, t, rng, target=None, mult=1.0, **_) -> bool:
    status = t.get("status", "slowed")
    if target is None or not target.alive or status in target.statuses:
        return False
    if C.apply_damage(combat, a, target, mult * float(t.get("power", 1.0)), f"uses {t['name']} on", rng, how=f"with {t['name']}") and target.alive:
        C.add_status(combat, target, status, int(t.get("rounds", 1)), a)
    return True


def _burst(combat, a, t, rng, target=None, mult=1.0, **_) -> bool:
    if target is None or not target.alive:
        return False
    near = [e for e in combat.enemies() if e.alive and e.zone_id == target.zone_id]
    if len(near) < int(t.get("foes", 2)):
        return False
    C.tell(combat, f"{C.who(a)} {C.vb(a, 'loose', 'looses')} {t['name']} into the thick of them")
    for e in near:
        if e.alive:
            C.apply_damage(combat, a, e, mult * float(t.get("power", 1.0)), f"uses {t['name']} on", rng, can_cleave=False, how=f"with {t['name']}")
    return True


DOES = {"heal": _heal, "bless": _bless, "guard": _guard, "strike": _strike, "hinder": _hinder, "burst": _burst, "spell": _spell}


# ---------- a priest's care outside a fight

def tender(party: list[dict]) -> dict | None:
    """The hire who can tend wounds: a role with a heal, on their feet (not carried out of the last fight)."""
    return next((m for m in party if healing(m.get("role", "")) and not m.get("npc") and m.get("hp_frac", 1.0) > 0.05), None)


def tend_pct(member: dict, when: str) -> float:
    """(f400) How much of the player's health a hire's care gives back: their heal out of a fight, at the rank their level allows
    (spells.yaml healing outside), times party.yaml tending `after_fight` or `asked`."""
    r = spells.highest_rank(member.get("level", 1))
    return min(100.0, float(spells.S["healing"]["outside"][r - 1]) * float(P["tending"][when]))


def tend(character, party: list[dict], pct: float, minutes: int, healer: dict | None = None) -> tuple[int, list[str]]:
    """Health given back to the player (pct of their health), and the hires tended (to `hires_pct` more of theirs). Returns (health
    restored, the names of hires tended)."""
    from engine import party as rules, pools
    T = P["tending"]
    top = pools.maximum(character, "health")
    now = pools.current(character, "health")
    gained = int(min(top - now, top * pct / 100))
    if gained > 0:
        character.health = float(now + gained)
    tended = []
    for m in party:
        if m is healer or m.get("npc") or not m.get("permanent"):
            continue
        h = rules.health_now(m, minutes)
        if h < 0.95:
            m["hp_frac"], m["hp_at"] = min(1.0, h + T["hires_pct"] / 100), minutes
            tended.append(m["name"])
    return max(0, gained), tended


def problems() -> list[str]:
    bad = []
    roles = set(P.get("roles") or {})
    for role, ts in (P.get("kits") or {}).items():
        if role not in roles:
            bad.append(f"party.yaml kits: '{role}' is not a role")
        for t in ts:
            if t.get("does") not in DOES:
                bad.append(f"party.yaml kits {role}: '{t.get('id')}' does '{t.get('does')}', which the engine does not know")
            if not (t.get("name") or t.get("names")) or not t.get("id"):
                bad.append(f"party.yaml kits {role}: every technique needs an id and a name (or a name for each rank)")
            if t.get("names") and len(t["names"]) < spells.TOP:
                bad.append(f"party.yaml kits {role}: '{t['id']}' needs a name for each of the {spells.TOP} ranks")
            if t.get("does") == "spell" and t.get("form") not in spells.FORMS:
                bad.append(f"party.yaml kits {role}: '{t['id']}' casts form '{t.get('form')}', which spells.yaml does not have")
            if t.get("does") in SPELLS and t.get("names") and not casts(role):
                bad.append(f"party.yaml kits {role}: '{t['id']}' is a spell, and party.yaml casting gives the role no attribute to cast with")
    for role in roles:
        if role not in (P.get("kits") or {}):
            bad.append(f"party.yaml kits: the role '{role}' has no techniques")
    for k in ("after_fight", "hires_pct", "asked", "asked_every", "minutes"):
        if k not in (P.get("tending") or {}):
            bad.append(f"party.yaml tending: needs {k}")
    return bad
