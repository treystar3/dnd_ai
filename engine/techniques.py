"""(f396) What a hire can do besides a plain blow (party.yaml kits), and a priest's care outside a fight (party.yaml tending).

Why: a hired fighter, archer, rogue or mage fought with one plain blow, and a priest healed a twelfth of a wound every fourth round once
someone was badly hurt: a player who hired a priest never saw them heal. Now each role has two techniques, used on the hire's own
judgement: the engine decides when, the numbers are data, and the narrator is told the technique by name. Support (heal, bless, guard)
is weighed before the hire looks for a foe; offence (strike, hinder, burst) once they have one in reach."""
from __future__ import annotations

import random

from engine import combat as C
from engine.party import P

SUPPORT = ("heal", "bless", "guard")
OFFENCE = ("strike", "hinder", "burst")


def kit(role: str) -> list[dict]:
    return list((P.get("kits") or {}).get(role or "") or [])


def healing(role: str) -> dict | None:
    """A role's heal, if it has one: what an order to heal and a priest's care outside a fight are measured by."""
    return next((t for t in kit(role) if t["does"] == "heal"), None)


WHAT = {"heal": "heals the hurt", "bless": "the party strikes harder", "guard": "shields you when you are hurt",
        "strike": "a heavier blow", "hinder": "slows a foe", "burst": "hits every foe bunched together"}


def describe(role: str) -> str:
    """'Healing Word (heals the hurt), Blessing (the party strikes harder)': what a hire of this role can do, for the panes."""
    return ", ".join(f"{t['name']} ({'a heavy blow at a foe busy with someone else' if t.get('engaged') else WHAT.get(t['does'], t['does'])})"
                     for t in kit(role))


def ready(a: C.Fighter, t: dict) -> bool:
    return a.cooldowns.get(t["id"], 0) <= 0


def spend(a: C.Fighter, t: dict) -> None:
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
    return f.max_hp * float(t.get("pct", 0)) / 100


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
    heal_on(combat, a, who_, heal_amount(who_, t), t["name"])
    return True


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
    combat.log.append(f"{a.name} uses {t['name']}: the party strikes {pct}% harder until round {until}")
    C.tell(combat, f"{C.who(a)} {C.vb(a, 'raise', 'raises')} a hand and {C.vb(a, 'speak', 'speaks')} a blessing over you all, and every arm "
                   f"feels surer for it ({t['name']})")
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


DOES = {"heal": _heal, "bless": _bless, "guard": _guard, "strike": _strike, "hinder": _hinder, "burst": _burst}


# ---------- a priest's care outside a fight

def tender(party: list[dict]) -> dict | None:
    """The hire who can tend wounds: a role with a heal, on their feet (not carried out of the last fight)."""
    return next((m for m in party if healing(m.get("role", "")) and not m.get("npc") and m.get("hp_frac", 1.0) > 0.05), None)


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
            if not t.get("name") or not t.get("id"):
                bad.append(f"party.yaml kits {role}: every technique needs an id and a name")
    for role in roles:
        if role not in (P.get("kits") or {}):
            bad.append(f"party.yaml kits: the role '{role}' has no techniques")
    for k in ("after_fight_pct", "hires_pct", "asked_pct", "asked_every", "minutes"):
        if k not in (P.get("tending") or {}):
            bad.append(f"party.yaml tending: needs {k}")
    return bad
