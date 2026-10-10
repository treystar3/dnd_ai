"""Riders, shapes and buffs on abilities (data/rules/ability_traits.yaml): their text, numbers and the per-character draw."""

import random
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
T = yaml.safe_load((ROOT / "data" / "rules" / "ability_traits.yaml").read_text(encoding="utf-8"))
RIDERS, SHAPES, BUFFS, COMMANDS = T["riders"], T["shapes"], T["buffs"], T["commands"]


PLAIN_LABEL = "Honed"


def tier_of(x) -> str:
    return getattr(x, "value", x)


def value(table: dict, tier) -> float:
    return table[tier_of(tier)]


def rider_text(rid: str, tier) -> str:
    r = RIDERS[rid]
    nums = {k: value(v, tier) for k, v in r.items() if isinstance(v, dict) and tier_of(tier) in v}
    return r["text"].format(**nums)


def shape_text(sid: str) -> str:
    return SHAPES[sid]["text"]


def command_text(cid: str, tier) -> str:
    c = COMMANDS[cid]
    nums = {k: value(v, tier) for k, v in c.items() if isinstance(v, dict) and tier_of(tier) in v}
    if "strike" in nums:
        nums["strike_pct"] = round(nums["strike"] * 100)
    return c["text"].format(**nums)


def buff_stat_word(stat: str) -> str:
    return {"armor": "armor", "ward": "ward", "both": "armor and ward"}.get(stat, "armor")


def buff_text(bid: str, tier, stat: str = "") -> str:
    b = BUFFS[bid]
    pct = value(b["pct"], tier)
    if bid == "bulwark" and stat == "both":
        pct = round(pct * b["both_share"])
    return b["text"].format(rounds=value(b["rounds"], tier), pct=pct, half=round(pct / 2), stat=buff_stat_word(stat))


def parts(a) -> list[tuple[str, str]]:
    """(label, text) for each trait an ability carries beyond its tier."""
    out = []
    if getattr(a, "command", "") and tier_of(a.effect) == "command":
        out.append((COMMANDS[a.command]["label"], command_text(a.command, a.tier)))
    if getattr(a, "buff", ""):
        out.append((BUFFS[a.buff]["label"], buff_text(a.buff, a.tier, a.buff_stat)))
    if tier_of(a.effect) == "damage" and not getattr(a, "shape", "") and not getattr(a, "rider", ""):
        out.append((PLAIN_LABEL, f"deals {round(T['plain_damage'] * 100)}% more damage, having no rider or shape"))
    if getattr(a, "shape", ""):
        out.append((SHAPES[a.shape]["label"], shape_text(a.shape)))
    if getattr(a, "rider", ""):
        out.append((RIDERS[a.rider]["label"], rider_text(a.rider, a.tier)))
    return out


def describe(a) -> str:
    """One line for the ability list: what it does beyond its tier."""
    return "; ".join(f"{label.lower()}: {text}" for label, text in parts(a))


def buff_mech(buff: str, tier, stat: str = "", magical: bool = False) -> dict:
    """The combat mechanics a buff grants while it lasts."""
    b = BUFFS[buff]
    pct = value(b["pct"], tier)
    if buff == "bulwark":
        stat = stat or ("ward" if magical else "armor")
        if stat == "both":
            share = round(pct * b["both_share"])
            return {"bulwark_armor": share, "bulwark_ward": share}
        return {f"bulwark_{stat}": pct}
    if buff == "thorns":
        return {"thorns": pct}
    special = {"manashield": "mana_shield", "empower": "empowered", "frenzy": "blood_pact", "vampiric": "vampiric", "elemental": "elemental_weapon"}
    if buff in special:
        return {special[buff]: pct}
    return {"regeneration": pct}


def _score(entry: dict, interp) -> float:
    text = " ".join([interp.custom_class, interp.combat_identity, interp.summary, *interp.themes]).lower()
    s = 1.0
    fams = interp.families or [{"support": "healer"}.get(interp.archetype.value, interp.archetype.value)]
    s += 1.5 * sum(1 for fam in fams if fam in entry.get("fits", []))
    s += 1.5 * min(2, sum(1 for w in entry.get("words", []) if w in text))
    return s


def _draw(table: dict, n: int, interp, rng: random.Random, skip=(), max_multi: int | None = None) -> list[str]:
    """Weighted draw without repeats. Companion-only entries need a class that has companions; multi-hit shapes are capped."""
    pack = getattr(interp, "uses_companions", False)
    ids = [k for k in table if k not in skip and (pack or not table[k].get("companion"))]
    out, multi = [], 0
    while ids and len(out) < n:
        pick = rng.choices(ids, weights=[_score(table[i], interp) ** 1.2 for i in ids])[0]
        out.append(pick)
        ids.remove(pick)
        if table[pick].get("multi"):
            multi += 1
            if max_multi is not None and multi >= max_multi:
                ids = [i for i in ids if not table[i].get("multi")]
    return out


def draw_offers(interp, rng: random.Random | None = None, sizes: dict | None = None, skip=(), min_functions: int = 0,
                owned_functions=()) -> dict:
    """A fresh selection for one new character (or one lesson). Weighted toward what suits the class, but always varied."""
    from engine import field
    rng = rng or random.SystemRandom()
    n = sizes or T["offer"]
    return {
        "functions": field.draw(interp, rng, minimum=min_functions, count=(sizes or {}).get("functions"), skip=owned_functions),
        "commands": list(COMMANDS) if getattr(interp, "uses_companions", False) else [],
        "riders": _draw(RIDERS, n["riders"], interp, rng, skip),
        "shapes": _draw(SHAPES, n["shapes"], interp, rng, skip, max_multi=T["max_multi"]),
        "buffs": _draw(BUFFS, n["buffs"], interp, rng),
    }


def offer_lines(offers: dict) -> str:
    from engine import field
    lines = [field.offer_lines(offers["functions"])] if offers.get("functions") else []
    lines += ["Riders on offer (put one on a damage or control ability; the extra thing it does when the ability lands):"]
    for r in offers["riders"]:
        lines.append(f"  {r}: {rider_text(r, 'moderate')}")
    lines.append("Shapes on offer (put one on a single-target damage ability; it changes how the damage arrives):")
    for sh in offers["shapes"]:
        lines.append(f"  {sh}: {SHAPES[sh]['text']}")
        if SHAPES[sh].get("hint"):
            lines.append(f"      (a multi-hit ability: name and describe it to suit the class - {SHAPES[sh]['hint']})")
    if offers.get("commands"):
        lines.append("Commands on offer (every command-effect ability gets a DIFFERENT one of these, in the command field):")
        for cm in offers["commands"]:
            lines.append(f"  {cm}: {command_text(cm, 'moderate')}")
    lines.append("Buffs on offer (give an ability the effect buff and this buff; it strengthens the caster for a few rounds of a fight):")
    for b in offers["buffs"]:
        lines.append(f"  {b}: " + ("raises armor, ward or both - set buff_stat to armor, ward or both" if b == "bulwark"
                                   else buff_text(b, "moderate")))
    return "\n".join(lines)


MULTI_WORDS = ("multiple", "volley", "barrage", "flurry", "rapid", "salvo", "hail", "rain of", "missiles", "series of", "sequence", "several",
               "twin", "two ", "pair of", "dual", "double", "triple", "fusillade", "succession", "bolts", "darts", "shards", "arrows", "fireballs")
_BY_COUNT = (("barrage", ("five", "flurry", "barrage", "fusillade", "rapid", "rain of", "hail", "salvo", "sequence", "succession")),
             ("double", ("two ", "twin", "pair of", "dual", "double")))


def sounds_multi(a) -> bool:
    """Does an ability's name and description describe several strikes?"""
    text = f"{a.name} {a.description}".lower()
    return any(w in text for w in MULTI_WORDS)


def fit_problem(a) -> str:
    """Why this ability's shape or rider does not suit what it is (its reach, or what its own description says). Empty if it fits."""
    text = f"{a.name} {a.description}".lower()
    reach = tier_of(a.reach)
    for kind, table, trait in (("shape", SHAPES, a.shape), ("rider", RIDERS, a.rider)):
        if not trait:
            continue
        t = table[trait]
        if t.get("reach") and reach not in t["reach"]:
            return f"{t['label']} ({kind}) needs a {'/'.join(t['reach'])}-reach ability, but '{a.name}' is {reach}"
        clash = next((w for w in t.get("clash", []) if w in text), "")
        if clash:
            return f"{t['label']} ({kind}) contradicts '{a.name}', which is described as \"{clash}\""
    return ""


def repair_shapes(skills, offered_shapes) -> None:
    """Keep each ability's shape and rider honest to what the ability is.
    1. An ability that describes several hits gets one of the offered multi-hit shapes in place of a shape that doesn't fit it.
    2. A shape or rider that contradicts the ability (a ricochet on 'a beam that strikes a single target', a lunge on a ranged spell)
       is dropped when the set can spare it, and otherwise refused with the reason so the model moves it to an ability it suits."""
    multi = [s for s in offered_shapes if SHAPES[s].get("multi")]
    for a in skills:
        if tier_of(a.effect) != "damage" or tier_of(a.reach) == "area":
            continue
        if not sounds_multi(a) or (a.shape and SHAPES[a.shape].get("multi")):
            continue
        if multi:
            text = f"{a.name} {a.description}".lower()
            pick = next((sid for sid, words in _BY_COUNT if sid in multi and any(w in text for w in words)), None)
            a.shape = pick or ("volley" if "volley" in multi else multi[0])
        elif a.shape and len({s.shape for s in skills if s.shape}) > T["need"]["shapes"]:
            a.shape = ""
    for a in skills:
        why = fit_problem(a)
        while why:
            kind = "shape" if "(shape)" in why else "rider"
            used = {getattr(s, kind) for s in skills if getattr(s, kind)}
            if len(used) <= T["need"][kind + "s"] and sum(getattr(s, kind) == getattr(a, kind) for s in skills) == 1:
                raise ValueError(why + f" - move that {kind} to an ability it suits, or use a different {kind} here")
            setattr(a, kind, "")
            why = fit_problem(a)
    dedupe_traits(skills)


def dedupe_traits(skills) -> None:
    """Each rider and each shape is used on one ability only. Where one is repeated, the ability it suits best keeps it (most of its
    words in the ability's name and description; the earlier one on a tie) and the others go plain. Never lowers the number of different traits."""
    for kind, table in (("rider", RIDERS), ("shape", SHAPES)):
        groups: dict[str, list] = {}
        for a in skills:
            if getattr(a, kind):
                groups.setdefault(getattr(a, kind), []).append(a)
        for trait, users in groups.items():
            if len(users) < 2:
                continue
            words = table[trait].get("words", [])
            def score(a):
                text = f"{a.name} {a.description}".lower()
                return sum(w in text for w in words) + (2 if kind == "shape" and table[trait].get("multi") and sounds_multi(a) else 0)
            keep = max(users, key=lambda a: (score(a), -users.index(a)))
            for a in users:
                if a is not keep:
                    setattr(a, kind, "")
