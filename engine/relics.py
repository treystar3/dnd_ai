"""A ring's or amulet's power in a fight (see data/rules/accessories.yaml). It takes the wearer's action, costs nothing, and is limited per fight.

use() runs one power. Timed effects live in Fighter.buffs and are folded into the wearer's mechanics (combat.mechanics), ticked in
combat.start_turn through tick().
"""

import random

from engine import combat as C


def _foes(combat, target):
    en = combat.enemies()
    t = target if target and target.alive and target.side == "enemy" else (min(en, key=lambda e: C.BANDS.index(e.band)) if en else None)
    return t, en


def use(combat, att, move, target, rng: random.Random) -> str | None:
    """Fire the power on `move` for `att`. Returns a problem string if it cannot be used."""
    r = move.relic
    P, kind, name = r["params"], r["kind"], r["name"]
    t, enemies = _foes(combat, target)
    if kind in ("smite", "mark", "dazzle", "nova", "rally") and not enemies and kind != "rally":
        return "There is nothing to use it on."
    att.relic_uses[move.id] = att.relic_uses.get(move.id, 0) + 1
    if att.side == "player" and t:
        combat.focus = t.id
    C.tell(combat, f"{C.who(att)} {C.vb(att, 'call', 'calls')} on {name}")
    combat.log.append(f"{att.name} uses {name}")
    if kind == "smite":
        C.apply_damage(combat, att, t, P["mult"] / 100, f"unleashes {name} on", rng, how=f"with {name}", can_cleave=False)
    elif kind == "mend":
        amount = round(att.max_hp * P["pct"] / 100)
        att.hp = min(att.max_hp, att.hp + amount)
        att.statuses.pop("bleeding", None)
        C.tell(combat, f"wounds close on their own and the bleeding stops (+{amount} health)")
    elif kind == "barrier":
        att.shield += att.max_hp * P["pct"] / 100
        C.tell(combat, f"a barrier closes around {C.who(att)}")
    elif kind == "buff":
        att.buffs[move.id] = {"rounds": P["rounds"], "mech": dict(P["mech"]), "drain": P.get("drain", 0),
                              "collapse": P.get("collapse", ""), "name": name}
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'are', 'is')} changed for {P['rounds']} rounds: {r['text']}")
    elif kind == "mark":
        if t:
            t.statuses["hexed"] = 99
            if C.add_status(combat, t, "bleeding", P["rounds"]):
                C.tell(combat, f"{C.who(t)} is cut open and cursed, marked for ruin")
            else:
                C.tell(combat, f"{C.who(t)} is cursed, marked for ruin, though the wound will not open")
    elif kind == "dazzle":
        targets = enemies if P.get("wide") else ([t] if t else [])
        for e in targets:
            hit = C.add_status(combat, e, "blinded", P["rounds"])
            C.add_status(combat, e, "slowed", P["rounds"])
            if hit:
                C.tell(combat, f"{C.who(e)} {C.STATUS_WORDS['blinded'][1]}")
    elif kind == "font":
        att.mana = min(att.max_mana, att.mana + att.max_mana * P["mana"] / 100)
        for k in list(att.cooldowns):
            att.cooldowns[k] = max(0, att.cooldowns[k] - int(P["cooldown"]))
            if not att.cooldowns[k]:
                att.cooldowns.pop(k)
        C.tell(combat, f"power wells up in {C.who(att)}, and everything {C.vb(att, 'you know', 'it knows')} comes closer to ready")
    elif kind == "nova":
        base = C.RULES["spell_base_damage"] * C.growth(att.level) * P["mult"] / 100
        for e in enemies:
            dealt, _ = C.mitigate(e, base, "magical", att.level, combat, att)
            taken = C.take_damage(combat, e, dealt, att, rng, "magical")
            combat.log.append(f"{name} hits {e.name}: {taken} damage")
            if P.get("status") and e.alive and not C.resist(att, e, ["wisdom", "charisma"], rng):
                C.add_status(combat, e, P["status"], 2)
        C.tell(combat, "it rolls out over the field and strikes every enemy: " + ", ".join(f"{C.who(e)} is {C.condition(e)}" for e in enemies))
    elif kind == "rally":
        for a in combat.allies():
            a.hp = min(a.max_hp, a.hp + a.max_hp * P["pct"] / 100)
            if combat.enemies():
                C.apply_damage(combat, a, min(combat.enemies(), key=lambda e: e.hp), 1.0, "strikes at the rally", rng, how="at the rallying cry")
        att.shield += att.max_hp * P["pct"] / 100
        C.tell(combat, f"{C.who(att)} {C.vb(att, 'raise', 'raises')} a cry that no one can ignore")
    elif kind == "reset":
        att.cooldowns.clear()
        att.stamina = min(att.max_stamina, att.stamina + att.max_stamina * P["stamina"] / 100)
        C.tell(combat, "time gives a little, and everything is ready again")
    return None


def tick(combat, f) -> None:
    """Called at the start of a fighter's turn: timed effects run down, cost, and end."""
    for bid in list(f.buffs):
        b = f.buffs[bid]
        if b.get("drain") and f.alive:
            loss = max(1, round(f.max_hp * b["drain"] / 100))
            f.hp = max(1, f.hp - loss)
            C.tell(combat, f"{b['name']} takes its price from {C.who(f)}")
        b["rounds"] -= 1
        if b["rounds"] <= 0:
            f.buffs.pop(bid)
            end = b.get("collapse")
            C.tell(combat, f"{b['name']} fades from {C.who(f)}")
            if end == "weary":
                C.add_status(combat, f, "slowed", 2)
            elif end == "spent":
                f.stamina = 0
                f.mana = 0


def buff_mechanics(f) -> dict[str, float]:
    out: dict[str, float] = {}
    for b in f.buffs.values():
        for k, v in b["mech"].items():
            out[k] = out.get(k, 0) + (v or 1)
    return out
