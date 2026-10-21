"""Movement abilities (f223): the ways a character overcomes the limits of ordinary movement (data/rules/movement.yaml).

THE MOVEMENT LAW. Ordinary movement - the move action, the free step that rides along with an action, interposing, falling back -
is baseline positioning, limited on purpose (engine/battlefield.py, engine/combat.py retreat/advance_step). A movement ability is used
ALONGSIDE your action, at most one a turn, and buys past one of those limits; the rare extreme relocation takes the whole turn. It
only moves - you, your allies, or who is fighting whom. It deals no damage and adds no effect.

Every check that can fail happens in refuse(), before anything is spent: a movement ability that cannot do its job costs nothing,
and the turn's action still happens."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
M = yaml.safe_load((ROOT / "data" / "rules" / "movement.yaml").read_text(encoding="utf-8"))
KINDS: dict = M["kinds"]
EVERYDAY = [k for k, v in KINDS.items() if v["group"] == "everyday"]
SIGNATURES = [k for k, v in KINDS.items() if v["group"] == "signature"]


def spec(move) -> dict:
    return KINDS.get(getattr(move, "movement", "") or "", {})


def whole_turn(move) -> bool:
    return bool(spec(move).get("whole_turn"))


def card_text(kind: str) -> str:
    """What the ability card says: what it does - no advice on when to use it (f250); its cooldown is on the card's first line."""
    k = KINDS.get(kind)
    if not k:
        return ""
    return k["does"] + (" It takes your whole turn." if k.get("whole_turn") and "whole turn" not in k["does"] else "")


def signatures_for(families, summoner: bool = False) -> list[str]:
    """The signature movement abilities a class with these families could be offered."""
    fams = set(families or [])
    return [k for k in SIGNATURES if fams & set(KINDS[k].get("fits", []))
            and (KINDS[k].get("needs") != "summoner" or summoner)]


# ---------- in a fight ----------

def _arrive(combat, att, dest) -> None:
    """Land beside an enemy wherever it is - past whatever guards it - and be fighting it."""
    from engine import battlefield as bf
    bf.release(combat, att)
    if combat.battlefield is not None and att.zone_id != dest.zone_id:
        bf.enter_zone(combat, att, dest.zone_id)
    bf.to_row(combat, att, "loose")
    bf.engage(combat, att, dest)


def _cursed_by(combat, att) -> list:
    return [e for e in combat.enemies() if any(e.status_from.get(s) == att.id for s in e.statuses)
            or any(c.get("by") == att.id for c in e.curses)]


def _corpses(combat) -> list:
    return [f for f in combat.fighters if not f.alive and not f.fled and f.zone_id]


def _ally_for(combat, att, give):
    from engine import battlefield as bf
    near = [a for a in combat.allies() if a.alive and a is not att and (combat.battlefield is None or
            bf.steps_between(combat, att, a) <= 1)]
    named = next((a for a in (give or []) if a in near), None)
    if named is not None:
        return named
    pressed = [a for a in near if bf.engaged(combat, a)]
    return min(pressed or near, key=lambda a: a.hp / max(1, a.max_hp), default=None)


def refuse(combat, att, move, target, give=None) -> str | None:
    """Why this movement ability cannot be used right now (nothing is spent), or None."""
    from engine import battlefield as bf
    from engine import summons
    kind = getattr(move, "movement", "")
    if any(b.get("kind") == "stoneform" for b in (att.buffs or {}).values()):
        return "You are stone: you cannot use a movement ability until Stoneform ends."
    if att.counters.get("moved_round") == combat.round and not (kind == "shadowmark" and att.shadow):
        return "You have already used a movement ability this turn."
    if kind == "breach":
        if target is None or target.side != "enemy":
            return f"{move.name} needs an enemy to reach."
        if combat.battlefield is not None and bf.steps_between(combat, att, target) > 1:
            return f"{target.name} is too far away for {move.name}."
        if not bf.protected(combat, target):
            return f"{target.name} is not behind any guard - you can reach it without {move.name}."
    elif kind == "shift":
        if not bf.engaged(combat, att):
            return "Nothing is fighting you - there is nothing to pull free of."
    elif kind == "shield_ally":
        if _ally_for(combat, att, give) is None:
            return "No ally is near enough to shield."
    elif kind == "relentless_advance":
        if "grappled" in att.statuses:
            return "You are held fast - nothing breaks a grapple but getting free of it."
        if target is None or target.side != "enemy":
            return f"{move.name} needs an enemy to close on."
        if bf.attack_access(combat, att, target).ok:
            return f"{target.name} is already within your reach."
        if combat.battlefield is not None and bf.steps_between(combat, att, target) > int(M["reach_zones"]):
            return f"{target.name} is too far away for {move.name}."
    elif kind == "shadowmark":
        return None                                         # the vanish, or the return: both always work
    elif kind == "malefic_step":
        if not _cursed_by(combat, att):
            return "No enemy is suffering from one of your curses."
    elif kind == "grave_step":
        if not _corpses(combat):
            return "No one has fallen in this fight yet - there is no body to step out of."
    elif kind == "soul_swap":
        if summons.yours(combat) is None:
            return "You have no summon standing to trade places with."
    elif kind == "bloodscent":
        if not [e for e in combat.enemies() if e.hp < e.max_hp * 0.5]:
            return "No enemy is below half health - there is no blood to follow."
    elif kind == "vengeance_leap":
        hurt = combat.get(att.last_hurt_by) if att.last_hurt_by else None
        if hurt is None or not hurt.alive or hurt.fled or hurt.side == att.side:
            return "Whoever last hurt you is no longer in the fight."
    elif kind == "rally_to_me":
        if not [a for a in combat.allies() if a.alive and not _still(a)]:
            return "You have no allies to call to your side."
    return None


def _still(f) -> bool:
    from engine import combat as C
    return C._still(f)


def resolve(combat, att, move, target, rng: random.Random, give=None) -> None:
    """The movement itself (refuse() has already passed and the cost is paid)."""
    from engine import battlefield as bf
    from engine import combat as C
    from engine import summons
    kind = move.movement
    att.counters["moved_round"] = combat.round
    att.move_round = combat.round
    name = move.name
    if kind == "breach":
        _arrive(combat, att, target)
        combat.log.append(f"{att.name} uses {name}: past the guards to {target.name}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'slip', 'slips')} past the guarding line with {name} and {C.vb(att, 'are', 'is')} on {C.who(target)}")
    elif kind == "shift":
        was = bf.engaged(combat, att)
        old = [o.name for o in was]
        bf.release(combat, att)
        back = att.counters.pop("shift_back", 0)
        if not back and target is not None and target.alive and target.side == "enemy" and target.zone_id == att.zone_id \
                and target not in was and bf.attack_access(combat, att, target).ok:
            bf.engage(combat, att, target)
            C.tell(combat, f"{C.who(att)} {C.vb(att, 'pull', 'pulls')} free of {', '.join(old)} with {name} and {C.vb(att, 'turn', 'turns')} on {C.who(target)} instead")
        else:
            story = bf.withdraw(combat, att)
            C.tell(combat, f"{C.who(att)} {C.vb(att, 'pull', 'pulls')} cleanly free of {', '.join(old)} with {name} and {story}")
        combat.log.append(f"{att.name} uses {name}: free of {', '.join(old)}")
    elif kind == "shield_ally":
        ally = _ally_for(combat, att, give)
        bf.release(combat, att)
        if combat.battlefield is not None and att.zone_id != ally.zone_id:
            bf.enter_zone(combat, att, ally.zone_id)
        bf.to_row(combat, att, "front")
        att.covering = ally.id
        took = []
        for e in bf.engaged(combat, ally)[:max(1, int(bf.hold_of(att)))]:
            bf.disengage(combat, ally, e)
            bf.engage(combat, att, e)
            took.append(e.name)
        combat.log.append(f"{att.name} uses {name}: shields {ally.name}" + (f", taking on {', '.join(took)}" if took else ""))
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'reach', 'reaches')} {ally.name} with {name}"
               + (f" and {', '.join(took)} {'turns' if len(took) == 1 else 'turn'} on {C.who(att)} instead" if took else "")
               + " - blows meant for them will land on " + ("you" if att.side == "player" else C.who(att)))
    elif kind == "relentless_advance":
        crossed = 0
        while att.zone_id != target.zone_id and crossed < int(M["reach_zones"]):
            if not bf.approach(combat, att, target, hard_ok=True):
                break
            crossed += 1
        if att.zone_id == target.zone_id and bf.attack_access(combat, att, target).ok:
            bf.engage(combat, att, target)
        combat.log.append(f"{att.name} uses {name}: closes on {target.name}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'drive', 'drives')} on with {name} - nothing slows {C.who(att)} - and {C.vb(att, 'reach', 'reaches')} {C.who(target)}")
    elif kind == "shadowmark":
        if att.shadow:
            shadow_return(combat, att, move, "called back")
            return
        att.shadow = {"zone": att.zone_id, "row": att.row, "until": combat.round + int(M["shadow_turns"]), "move": move.id,
                      "cooldown": int(move.cooldown or KINDS["shadowmark"]["cooldown"])}
        bf.release(combat, att)
        bf.gain(att, "concealed")
        att.counters["vanished_round"] = combat.round       # alone, nobody can find you until your next turn
        att.cooldowns.pop(move.id, None)                    # the cooldown starts only on the return
        combat.log.append(f"{att.name} uses {name}: vanishes, leaving a shadow")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'melt', 'melts')} out of the fight with {name}, and only {C.whose(att)} shadow stays where {C.who(att)} stood")
    elif kind == "malefic_step":
        cursed = _cursed_by(combat, att)
        dest = target if target in cursed else bf.closest(combat, att, cursed)
        _arrive(combat, att, dest)
        combat.log.append(f"{att.name} uses {name}: steps to the cursed {dest.name}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'follow', 'follows')} {C.whose(att)} own curse with {name} and {C.vb(att, 'stand', 'stands')} at {C.whose(dest)} side")
    elif kind == "grave_step":
        bodies = _corpses(combat)
        aim = target if target is not None and target.alive else None
        body = min(bodies, key=lambda b: (0 if aim and b.zone_id == aim.zone_id else 1,
                                          bf.steps_between(combat, b, aim) if aim and combat.battlefield else 0))
        bf.release(combat, att)
        if combat.battlefield is not None and att.zone_id != body.zone_id:
            bf.enter_zone(combat, att, body.zone_id)
        bf.to_row(combat, att, "loose")
        if aim is not None and aim.zone_id == att.zone_id:
            bf.engage(combat, att, aim)
        combat.log.append(f"{att.name} uses {name}: steps out of {body.name}'s body")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'sink', 'sinks')} into death with {name} and {C.vb(att, 'step', 'steps')} out of the fallen {body.name}"
               + (f", right beside {C.who(aim)}" if aim is not None and aim.zone_id == att.zone_id else ""))
    elif kind == "soul_swap":
        s = summons.yours(combat)
        mine, its = bf.engaged(combat, att), bf.engaged(combat, s)
        bf.release(combat, att)
        bf.release(combat, s)
        (a_zone, a_row), (s_zone, s_row) = (att.zone_id, att.row), (s.zone_id, s.row)
        if combat.battlefield is not None and a_zone != s_zone:
            bf.enter_zone(combat, att, s_zone)
            bf.enter_zone(combat, s, a_zone)
        bf.to_row(combat, att, s_row)
        bf.to_row(combat, s, a_row)
        for e in mine:
            bf.engage(combat, s, e)
        for e in its:
            bf.engage(combat, att, e)
        combat.log.append(f"{att.name} uses {name}: trades places with {s.name}")
        C.tell(combat, f"{C.who(att)} and {s.name} trade places in an instant with {name}")
    elif kind == "bloodscent":
        hurt = [e for e in combat.enemies() if e.hp < e.max_hp * 0.5]
        prey = min(hurt, key=lambda e: e.hp / max(1, e.max_hp))
        _arrive(combat, att, prey)
        combat.log.append(f"{att.name} uses {name}: leaps to the wounded {prey.name}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'scent', 'scents')} blood and {C.vb(att, 'leap', 'leaps')} across the field with {name}, landing on {C.who(prey)}")
    elif kind == "vengeance_leap":
        foe = combat.get(att.last_hurt_by)
        _arrive(combat, att, foe)
        combat.log.append(f"{att.name} uses {name}: leaps at {foe.name}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'leap', 'leaps')} straight at {C.who(foe)} with {name} - the one who hurt {C.who(att)}")
    elif kind == "rally_to_me":
        came = []
        for a in [a for a in combat.allies() if a.alive and not _still(a)]:
            bf.release(combat, a)
            if combat.battlefield is not None and a.zone_id != att.zone_id:
                bf.enter_zone(combat, a, att.zone_id)
            bf.to_row(combat, a, "back" if a.reach == "ranged" else "front")
            came.append(a.name)
        combat.log.append(f"{att.name} uses {name}: {', '.join(came)} rally to them")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'call', 'calls')} with {name}, and {', '.join(came)} {'comes' if len(came) == 1 else 'come'} free of the fight to {C.whose(att)} side")


def shadow_return(combat, att, move, how: str = "pulled back") -> None:
    """Back to the shadow: free of every fight, safe, standing where the shadow was. The cooldown starts now."""
    from engine import battlefield as bf
    from engine import combat as C
    sh = att.shadow
    att.shadow = {}
    bf.release(combat, att)
    if combat.battlefield is not None and sh.get("zone") in combat.battlefield.zones and att.zone_id != sh["zone"]:
        bf.enter_zone(combat, att, sh["zone"])
    bf.to_row(combat, att, sh.get("row") or "back")
    bf.lose(att, "concealed")
    mid = sh.get("move") or getattr(move, "id", "")
    if mid:
        att.cooldowns[mid] = int(sh.get("cooldown") or KINDS["shadowmark"]["cooldown"]) + 1
    att.counters["moved_round"] = combat.round
    combat.log.append(f"{att.name} returns to the shadow ({how})")
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'step', 'steps')} back into {C.whose(att)} shadow, out of every fight - "
           + ("called back" if how == "called back" else "the shadow pulls " + ("you" if att.side == "player" else C.who(att)) + " home"))


def on_turn_start(combat, f) -> None:
    """The shadow pulls its owner back at the start of the turn its time runs out."""
    if f.shadow and combat.round >= f.shadow.get("until", 0) and f.alive:
        shadow_return(combat, f, None, "pulled back")


def reveal_after(att) -> None:
    """Striking from hiding gives you away - unless the blow itself hid you again (Shadowstep)."""
    from engine import battlefield as bf
    if att.counters.pop("struck_hidden", None) and not att.counters.pop("rehid", None):
        bf.lose(att, "concealed")
