"""Healing in a fight (f219): one path for every heal, so withering, perks and attention apply to all of them alike.

A healing ability is single-target - the caster or one ally (Rescue: one fallen ally) - and restores in one of six forms the engine
planned for it (data/rules/healing.yaml): mend, renew, ward, cleanse, transfer, rescue. Its size is a share of the TARGET's maximum
health times the caster's power, so a heal lands in proportion on anyone. Healing draws the eye: enemies that saw it go for the
healer. Necrotic harm withers: healing on the withered, and their own regeneration, is halved."""
from __future__ import annotations

import random
from pathlib import Path

import yaml

from engine import combat as C

ROOT = Path(__file__).resolve().parent.parent
H = yaml.safe_load((ROOT / "data" / "rules" / "healing.yaml").read_text(encoding="utf-8"))
FORMS = H["forms"]
LAST: dict[int, tuple[str, float]] = {}     # fight -> (who was healed, how much the heal was), for the perks that follow a heal


def form_of(move) -> str:
    """The form a healing ability restores in; abilities from before f219 (no form) mend."""
    return getattr(move, "heal_form", "") or "mend"


def card_text(move) -> str:
    """What a healing ability does in a fight, in plain words with its numbers (f250)."""
    form = form_of(move)
    spec = FORMS.get(form, FORMS["mend"])
    tier = getattr(move.tier, "value", move.tier)
    pct = H["percent"][tier]
    mana = getattr(getattr(move, "resource", ""), "value", getattr(move, "resource", "")) == "mana"
    attr = (getattr(move, "attribute", "") or "casting attribute").capitalize() if mana else "Constitution"
    grow = f" (more with a higher {attr})"
    if form == "renew":
        return f"heals you or one ally for {round(pct * spec['share'])}% of their health{grow}, spread over their next {spec['rounds']} turns"
    if form == "ward":
        return (f"puts a barrier on you or one ally that absorbs the next {round(pct * spec['share'])}% of their health in damage{grow};"
                f" a barrier never grows past {round(spec['cap'] * 100)}% of their health")
    if form == "cleanse":
        return f"lifts up to {spec['lifts']} afflictions (poison, burning, fear and the like) from you or one ally and heals {round(pct * spec['share'])}% of their health{grow}"
    if form == "transfer":
        return (f"heals one ally for {round(pct * spec['share'])}% of their health{grow}, and you lose health equal to "
                f"{round(spec['price'] * 100)}% of what it heals")
    if form == "rescue":
        return f"raises a fallen ally back to their feet at {round(spec['revive'] * 100)}% of their health (once per ally each fight), or heals one ally or you for {pct}%{grow}"
    return f"heals you or one ally for {round(pct * spec['share'])}% of their health at once{grow}"


def outside_text(move) -> str:
    tier = getattr(move.tier, "value", move.tier)
    return f"heals you for {H['outside'][tier]}% of your health"


def power(att: C.Fighter, move) -> float:
    """The caster's healing power: their casting attribute for a mana heal, constitution for a stamina one."""
    if move.resource == "mana":
        attr = att.attrs.get(move.attribute, 0) if move.attribute else max(att.attrs.get(a, 10) for a in ("intelligence", "wisdom", "charisma"))
    else:
        attr = att.attrs.get("constitution", 10)
    return max(0.6, 1 + (attr - H["attribute_center"]) * H["per_point"])


def base(att: C.Fighter, move, target: C.Fighter) -> float:
    return target.max_hp * H["percent"].get(move.tier, H["percent"]["light"]) / 100 * power(att, move)


def wither_factor(target: C.Fighter) -> float:
    return H["wither"]["factor"] if "withered" in target.statuses else 1.0


def fallen_ally(combat: C.Combat, target: C.Fighter | None) -> bool:
    """A fallen ally Rescue can still raise: on the caster's side, down this fight, not dead for good, not raised before."""
    return (target is not None and target.side == "ally" and not target.alive and not target.fled
            and not target.counters.get("dead") and not target.counters.get("rescued"))


def cast(combat: C.Combat, att: C.Fighter, move, target: C.Fighter | None, rng: random.Random) -> float:
    """Resolve a healing ability on its target (the caster when none is named). Returns the heal's size before its form."""
    from engine import combat_perks as perks
    form = form_of(move)
    spec = FORMS.get(form, FORMS["mend"])
    t = target or att
    if not t.alive and not (form == "rescue" and fallen_ally(combat, t)):
        t = att                                          # only Rescue reaches the fallen, and only those it can still raise
    amount = base(att, move, t)
    who_t = "yourself" if (t is att and att.side == "player") else C.who(t)
    if form == "renew":
        per = amount * spec["share"] / spec["rounds"]
        for k, b in list(t.buffs.items()):
            if b.get("kind") == "renew" and b.get("from") == att.id:
                t.buffs.pop(k)
        t.buffs[f"renew_{move.id}"] = {"rounds": spec["rounds"], "mech": {}, "drain": 0, "collapse": "",
                                       "name": move.name, "kind": "renew", "per": per, "from": att.id}
        combat.log.append(f"{att.name} uses {move.name} on {t.name}: renewing {round(per)} a round for {spec['rounds']} rounds")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'lay', 'lays')} {move.name} on {who_t}: a healing that will keep working")
    elif form == "ward":
        cap = t.max_hp * spec["cap"]
        add = min(amount * spec["share"] * wither_factor(t), max(0.0, cap - t.shield))
        t.shield += add
        combat.log.append(f"{att.name} uses {move.name} on {t.name}: a ward of {round(add)}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'raise', 'raises')} {move.name} around {who_t} - a ward that will take the next blows ({round(add)})")
    elif form == "cleanse":
        lifted = [s for s in perks.AFFLICTIONS if s in t.statuses][:spec["lifts"]]
        for s in lifted:
            t.statuses.pop(s)
        healed, _ = perks.mend(combat, att, t, amount * spec["share"])
        combat.log.append(f"{att.name} uses {move.name} on {t.name}: lifts {', '.join(lifted) or 'nothing'}, heals {healed}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'cleanse', 'cleanses')} {who_t} with {move.name}"
               + (f", and the {' and '.join(lifted)} {'is' if len(lifted) == 1 else 'are'} gone" if lifted else ""))
    elif form == "transfer" and t is not att:
        price = min(att.hp - 1, amount * spec["price"])
        att.hp -= max(0.0, price)
        healed, _ = perks.mend(combat, att, t, amount * spec["share"])
        combat.log.append(f"{att.name} uses {move.name}: gives {round(price)} of their own life, {t.name} heals {healed}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'pour', 'pours')} {C.whose(att)} own life into {who_t} through {move.name} ({healed})")
    elif form == "rescue" and fallen_ally(combat, t):
        from engine import battlefield as bf
        t.hp = max(1.0, t.max_hp * spec["revive"] * wither_factor(t))
        t.counters["rescued"] = 1
        t.statuses = {}
        if t.zone_id and combat.battlefield is not None and t.zone_id in combat.battlefield.zones:
            bf.to_row(combat, t, "back" if t.reach == "ranged" else "front")
        combat.log.append(f"{att.name} uses {move.name}: {t.name} rises ({round(t.hp)})")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'call', 'calls')} {t.name} back with {move.name} - and {t.name} gets up, still in the fight")
    else:
        healed, _ = perks.mend(combat, att, t, amount * spec["share"] if form in ("mend", "rescue") else amount)
        combat.log.append(f"{att.name} uses {move.name} on {t.name}: heals {healed}")
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'call', 'calls')} on {move.name}, and {'your' if t is att and att.side == 'player' else C.whose(t)} wounds begin to close")
    att.counters["healed_round"] = combat.round
    LAST[id(combat)] = (t.id, amount)
    return amount


def on_turn_start(combat: C.Combat, f: C.Fighter) -> None:
    """Renewals at work: each one heals at the start of its bearer's turn (the countdown is relics.tick's)."""
    from engine import combat_perks as perks
    for b in list(f.buffs.values()):
        if b.get("kind") == "renew" and f.alive and b.get("per"):
            healer = combat.get(b.get("from", "")) or f
            healed, _ = perks.mend(combat, healer, f, b["per"])
            if healed:
                combat.log.append(f"{b['name']} renews {f.name}: +{healed}")


def attention_target(combat: C.Combat, e: C.Fighter, rng: random.Random) -> C.Fighter | None:
    """Healing draws the eye: an enemy that saw a heal this round or last goes for the healer, some of the time, when it can reach them."""
    if e.side != "enemy":
        return None
    from engine import battlefield as bf
    A = H["attention"]
    healers = [f for f in [combat.player] + combat.allies()
               if f.alive and f.counters.get("healed_round", -9) >= combat.round - A["rounds"]]
    reach = [h for h in healers if bf.attack_access(combat, e, h).ok or bf.attack_access(combat, e, h).can_approach]
    if reach and rng.random() < A["chance"]:
        return rng.choice(reach)
    return None


def after_damage(combat: C.Combat, dfn: C.Fighter, dealt: float, source: C.Fighter | None) -> None:
    """Necrotic harm withers whoever it lands on."""
    if dealt <= 0 or source is None or not dfn.alive:
        return
    if (source.hit_element or source.element) in H["wither"]["elements"]:
        C.add_status(combat, dfn, "withered", H["wither"]["rounds"], source)
