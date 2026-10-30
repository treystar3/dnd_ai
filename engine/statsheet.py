"""The stats window: every number combat uses for one fighter, laid out the way the player reads it. It reads the fighter the fight itself would
build, so a figure here is the figure combat uses. Figures that depend on an opponent are shown against a foe of the same level."""
from __future__ import annotations

from engine import combat

RULES = combat.RULES


def _n(x: float, places: int = 1):
    x = round(x, places)
    return int(x) if x == int(x) else x


def _pct(x: float) -> str:
    return f"{_n(x)}%"


def sheet(f: combat.Fighter) -> dict:
    """{"name", "title", "sections": [{"title", "rows": [[label, value, note]]}]} for one fighter."""
    always = {"always"}
    d, m = RULES["damage"], RULES["mitigation"]
    attr = f.best_attr(f.weapon_attrs)
    flat = combat.flat_bonus(f, "damage", always)
    pct = combat.bonus(f, "damage", always)
    base = f.weapon_damage + attr * d["attribute_bonus"] + flat
    avg = base * (1 + pct / 100)
    var = d["variance"]
    foe = combat.Fighter(id="equal", name="an equal foe", side="enemy", level=f.level, attrs={a: attr for a in combat.ATTRIBUTES}, hp=1, max_hp=1)
    chance, steps = combat.hit_parts(f, foe, combat.Combat(fighters=[f, foe]))
    crit = combat.crit_profile(f)
    acc = combat.bonus(f, "accuracy", always)
    growth = combat.growth(f.level)

    def cut(protection: float) -> float:
        return min(m["cap"], 100 * protection / max(0.01, protection + m["armor_k"] * growth))

    weapon_note = max(f.weapon_attrs, key=lambda a: f.attrs.get(a, 10)).capitalize() if f.weapon_attrs else "Strength"
    offense = [
        ["Weapon damage", _n(f.weapon_damage), f"{f.reach} {f.damage_type} attacks"],
        ["Attack power", _n(avg), f"an average blow before armor: weapon + {_n(d['attribute_bonus'] * 100)}% of {weapon_note}"
                                   + (f", +{_n(flat)} flat" if flat else "") + (f", {pct:+g}% from passives and gear" if pct else "")],
        ["Damage range", f"{_n(avg * (1 - var))} to {_n(avg * (1 + var))}", f"damage varies {_n(var * 100)}% either way on each blow"],
        ["Accuracy", f"{acc:+g}" if acc else "0", "points from passives and gear" if acc else "nothing from passives or gear"],
        ["Hit chance", _pct(chance), f"against a foe of the same level and Dexterity; never below {RULES['hit']['min']}% or above {RULES['hit']['max']}%"],
        ["Crit chance", _pct(crit["chance"]), f"against an equal-Dexterity foe; up to {_n(crit['most'])}% with a Dexterity edge (cap {crit['cap']}%)"],
        ["Crit damage", f"x{_n(crit['multiplier'], 2)}", "damage on a critical hit"],
    ]
    casts = [mv for mv in f.moves if mv.resource == "mana"]
    if casts or f.max_mana:
        attr_name = next((mv.attribute for mv in casts if mv.attribute), "intelligence")
        power = f.offhand_spell + combat.flat_bonus(f, "spell_power", always) + (f.weapon_damage if f.damage_type == "magical" else 0)
        base = RULES["spell_base_damage"] * growth
        mult = 1 + f.attrs.get(attr_name, 10) / RULES["spell_attribute"]
        offense.append(["Spell power", _n(power), "added to a spell's base power from a magical weapon, a focus or gear; "
                                                  + ("none of those yet" if not power else "before your casting attribute multiplies it")])
        ranks = [mv.rank for mv in casts if mv.rank and mv.effect == "damage" and not mv.named]
        if ranks:                                           # (f400) the spellbook: a bolt of the highest rank they cast
            from engine import spells
            r, coef, share = max(ranks), float(spells.S["coefficient"]), f.spell_share
            offense.append(["Spell damage", _n((spells.base(r) + coef * power) * mult * share),
                            f"a rank {spells.numeral(r)} bolt before armor or ward: (base {_n(spells.base(r))} + {_n(coef, 2)} x spell power) x "
                            f"{_n(mult, 2)} from {attr_name.capitalize()}" + (f", at {round(share * 100)}% for a hire" if share != 1 else "")
                            + "; other forms are multiples of it"])
        elif f.side != "ally":                              # a hire with no damage spell (a priest) has no spell damage to show
            offense.append(["Spell damage", _n((base + power) * mult), f"an average spell before its ability's own power and armor or ward: (base {_n(base)} + spell power) x {_n(mult, 2)} from {attr_name.capitalize()}"])
    if f.armor_pierce:
        offense.append(["Armor pierce", _pct(f.armor_pierce), "of a foe's armor ignored"])
    ev = combat.bonus(f, "evasion", always)
    defense = [
        ["Armor", _n(f.armor), f"turns away {_pct(cut(f.armor))} of physical damage from a foe of your level"],
        ["Ward", _n(f.ward), f"turns away {_pct(cut(f.ward))} of magical damage from a foe of your level"],
        ["Evasion", f"{ev:+g}" if ev else "0", "points off an attacker's hit chance" + (f"; your gear costs {f.evasion_penalty} of it" if f.evasion_penalty else "")],
    ]
    dp = combat.bonus(f, "defense", always)
    if dp or combat.flat_bonus(f, "defense", always):
        defense.append(["Defense", (f"{dp:+g}%" if dp else "") + (f" {combat.flat_bonus(f, 'defense', always):+g} flat" if combat.flat_bonus(f, "defense", always) else ""),
                        "taken off every blow after armor"])
    if f.crit_resist:
        defense.append(["Crit resistance", _pct(f.crit_resist), "cuts the chance of being critically hit"])
    pools = [["Health", _n(f.max_hp), ""]]
    if f.max_stamina:
        pools.append(["Stamina", _n(f.max_stamina), ""])
    if f.max_mana:
        pools.append(["Mana", _n(f.max_mana), ""])
    attrs = [[a.capitalize(), f.attrs.get(a, 10), ""] for a in combat.ATTRIBUTES]
    out = [{"title": "Offense", "rows": offense}, {"title": "Defense", "rows": defense}, {"title": "Pools", "rows": pools}, {"title": "Attributes", "rows": attrs}]
    effects = []
    for mid, val in sorted(combat.mechanics(f, None, None).items()):
        label = f.mech_names.get(mid) or mid.replace("_", " ").title()
        effects.append([label, f"{_n(val)}" if val else "", ""])
    if effects:
        out.append({"title": "Effects from gear and passives", "rows": effects})
    return {"name": f.name, "title": f"{f.name} - level {f.level}", "sections": out}


def lines(s: dict, notes: bool = False) -> list[list[str]]:
    """The sheet as [class, text] lines for a hover: 'h' for a heading, '' for a row."""
    out = [["h", s["title"]]]
    for sec in s["sections"]:
        out.append(["dim", sec["title"].upper()])
        if sec["title"] == "Attributes":
            out.append(["", "   ".join(f"{r[0][:3].upper()} {r[1]}" for r in sec["rows"])])
            continue
        for label, value, note in sec["rows"]:
            out.append(["", f"{label}: {value}" + (f"  ({note})" if notes and note else "")])
    return out
