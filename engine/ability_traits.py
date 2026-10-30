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


def shape_label(sid: str, reach="") -> str:
    """A shape's name on the card: a volley swung at arm's length is a flurry (f254)."""
    s = SHAPES[sid]
    return s.get("close_label", s["label"]) if tier_of(reach) in ("melee", "extended") else s["label"]


def command_text(cid: str, tier) -> str:
    c = COMMANDS[cid]
    nums = {k: value(v, tier) for k, v in c.items() if isinstance(v, dict) and tier_of(tier) in v}
    if "strike" in nums:
        nums["strike_pct"] = round(nums["strike"] * 100)
    return c["text"].format(**nums)


def buff_stat_word(stat: str) -> str:
    return {"armor": "armor", "ward": "ward", "both": "armor and ward"}.get(stat, "armor")


def buff_text(bid: str, tier=None, stat: str = "") -> str:
    """What a buff does, in the card's words. Buffs have one strength (f235): the tier is ignored."""
    b = BUFFS.get(bid)
    if not b:
        return ""
    return b["text"].format(**{k: v for k, v in b.items() if isinstance(v, (int, float)) and not isinstance(v, bool)})


def imbue_text(element: str, expressions=(), tier="light") -> str:
    """Imbue as it is for this ability: its own element, and what that element does on each hit (f250)."""
    from engine import spellcraft
    b = BUFFS["imbue"]
    el = element or "fire"
    out = f"for {b['rounds']} rounds, every weapon hit deals {b['pct']}% of the hit again as {el}"
    does = [spellcraft.expression_text(e, tier) for e in (expressions or []) if e in spellcraft.EXPR]
    if does:
        out += ", and each one " + " It also ".join(does)
    return out


ARCHON = {     # what an archon of each element does better with it (engine/combat.py ATTUNE, engine/afflictions.py) - f261
    "fire": "their burns are half again as strong",
    "cold": "their slows last a round longer",
    "lightning": "their lightning leaps on to other enemies half again as hard",
    "poison": "their poison lands two stacks at a time",
    "acid": "their acid eats half again as much armor",
    "necrotic": "their withering lasts a round longer and their drains heal half again as much",
    "radiant": "the enemies they light up or blind stay that way a round longer",
    "nature": "their bark barriers grow half again as thick",
}
WARD = {"fire": "cannot be set burning", "cold": "cannot be slowed by cold", "lightning": "cannot be slowed or blinded by lightning",
        "poison": "cannot be poisoned", "acid": "cannot be slowed or blinded by acid", "necrotic": "cannot be withered or unraveled",
        "radiant": "cannot be lit up or blinded by radiance", "nature": "cannot be bled, knocked down or petrified by nature"}


def attunement_text(element: str) -> str:
    """Attunement as it is for this ability: its own element, said plainly (f261)."""
    b = BUFFS["attunement"]
    el = element or "fire"
    return (f"for {b['rounds']} rounds, the one it is cast on becomes an archon of {el}: they take {b['pct']}% less {el} damage, "
            f"{WARD.get(el, 'shrug off its effects')}, and {ARCHON.get(el, 'their own ' + el + ' is stronger')}")


def ability_buff_text(a) -> str:
    """What this ability's buff does, as its card shows it."""
    if getattr(a, "buff", "") == "imbue":
        return imbue_text(getattr(a, "element", ""), getattr(a, "expressions", None) or [], imbue_strength())
    if getattr(a, "buff", "") == "attunement":
        return attunement_text(getattr(a, "element", ""))
    return buff_text(a.buff)


def parts(a, rank: bool = True) -> list[tuple[str, str]]:
    """(label, text) for each trait an ability carries beyond its tier. rank=False leaves a spell's rank unsaid (at creation every spell
    is rank I, f401)."""
    out = []
    if getattr(a, "command", "") and tier_of(a.effect) == "command":
        out.append((COMMANDS[a.command]["label"], command_text(a.command, a.tier)))
    if getattr(a, "buff", "") in BUFFS:
        out.append((BUFFS[a.buff]["label"], ability_buff_text(a)))
    if tier_of(a.effect) == "healing":
        from engine import healing
        out.append(("In a fight", healing.card_text(a)))
    if tier_of(a.effect) == "damage" and not getattr(a, "shape", "") and not getattr(a, "rider", "") and not getattr(a, "expressions", None) \
            and not getattr(a, "maneuver", "") and getattr(a, "martial_form", "") in ("", "strike"):
        out.append((PLAIN_LABEL, f"deals {round(T['plain_damage'] * 100)}% more damage, having no rider or shape"))
    if getattr(a, "shape", ""):
        out.append((shape_label(a.shape, getattr(a, "reach", "")), shape_text(a.shape)))
    if getattr(a, "rider", ""):
        out.append((RIDERS[a.rider]["label"], rider_text(a.rider, a.tier)))
    if getattr(a, "rank", 0) and getattr(a.effect, "value", a.effect) == "damage":   # (f397) a ranked spell: its rank, and its form
        from engine import spells
        out.append((spells.card(a) if rank else spells.form_label(a), spells.form_text(spells.form_of(a))))
    elif getattr(a, "spell_form", "") and a.spell_form != "bolt":
        from engine import spellcraft
        out.append((spellcraft.FORMS[a.spell_form]["label"], spellcraft.form_text(a.spell_form)))
    from engine import spellcraft
    for eid in ([] if getattr(a, "buff", "") == "imbue" else spellcraft.exprs_of(a)):     # Imbue says its element's effect in its own line
        x = spellcraft.EXPR[eid]
        lead = "Deals no damage; instead it " if x["kind"] == "control" else ("While it lasts, your weapon's hits also " if
                                                                             getattr(a, "buff", "") == "imbue" else "Each hit ")
        out.append((x["label"], lead + spellcraft.expression_text(eid, a.tier)))
    turns = int(getattr(a, "cast_turns", 0) or 0)       # a cast time of its own (a charged spell's form already says its two turns)
    if turns > 1:
        out.append(("Cast time", f"takes {turns} turns: begun on the first, the rest go to finishing it. A stun or a fall breaks it."))
    if getattr(a, "martial_form", "") and a.martial_form != "strike":
        from engine import martial
        out.append((martial.FORMS[a.martial_form]["label"], martial.form_text(a.martial_form, getattr(a, "hits", 0))))
    if getattr(a, "maneuver", ""):
        from engine import martial
        lead = "Deals no damage; contested, it " if tier_of(a.effect) == "control" else "When it lands, it "
        out.append((martial.MANEUVERS[a.maneuver]["label"], lead + martial.maneuver_text(a.maneuver, a.tier)))
    if getattr(a, "movement", ""):
        from engine import movement
        txt = movement.card_text(a.movement)
        if txt:
            out.append(("Movement", txt))
    if getattr(a, "channel", False):
        out.append(("Channeled", "it hits with your weapon damage plus half of your spell power."))
    return out


def describe(a) -> str:
    """One line for the ability list: what it does beyond its tier."""
    return "; ".join(f"{label.lower()}: {text}" for label, text in parts(a))


def buff_mech(buff: str, tier=None, stat: str = "", magical: bool = False) -> dict:
    """The combat mechanics a buff grants while it lasts (f235: one strength each)."""
    b = BUFFS.get(buff)
    if not b:
        return {}
    return {"imbue": {"elemental_weapon": b.get("pct", 0)}, "precision": {"precision": b.get("crit", 0)},
            "blur": {"blur": 1}, "arcaneward": {"bulwark_ward": b.get("pct", 0)}, "attunement": {"element_ward": b.get("pct", 0)},
            "bladeward": {"bladeward": b.get("pct", 0)}, "manashield": {"mana_veil": b.get("pct", 0)},
            "enlarge": {"enlarged": b.get("pct", 0)},
            "frostarmor": {"bulwark_armor": b.get("pct", 0), "frost_armor": 1},
            "stoneform": {"stoneform": b.get("pct", 0)}, "envenom": {"envenom_weapon": 1},
            "acidcoat": {"acid_weapon": b.get("pct", 0)}, "thorns": {"thorn_flat": b.get("flat", 0), "thorn_pct": b.get("pct", 0)}}.get(buff, {})


def imbue_strength() -> str:
    """(f400) How strongly Imbue's element lands on each hit, on the element expressions' scale (data/rules/spellcraft.yaml): one strength,
    like every buff, whoever casts it."""
    return str(BUFFS["imbue"].get("expression", "moderate"))


def buff_rounds(buff: str) -> int:
    return int((BUFFS.get(buff) or {}).get("rounds", 3))


def _score(entry: dict, interp) -> float:
    text = " ".join([interp.custom_class, interp.combat_identity, interp.summary, *interp.themes]).lower()
    s = 1.0
    fams = interp.families or [{"support": "healer"}.get(interp.archetype.value, interp.archetype.value)]
    s += 1.5 * sum(1 for fam in fams if fam in entry.get("fits", []))
    s += 1.5 * min(2, sum(1 for w in entry.get("words", []) if w in text))
    return s


def _draw(table: dict, n: int, interp, rng: random.Random, skip=(), max_multi: int | None = None) -> list[str]:
    """Weighted draw without repeats. Companion-only entries need a class that has companions; multi-hit shapes are capped."""
    pack = getattr(interp, "uses_companions", False) or getattr(interp, "summoner", False)   # allies of its own, kept or made
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
                owned_functions=(), level: int = 1, lesson: bool = False) -> dict:
    """A fresh selection for one new character (or one lesson). Weighted toward what suits the class, but always varied."""
    from engine import field
    rng = rng or random.SystemRandom()
    n = sizes or T["offer"]
    return {
        "functions": field.draw(interp, rng, minimum=min_functions, count=(sizes or {}).get("functions"), skip=owned_functions,
                               level=level, lesson=lesson),
        "commands": list(COMMANDS) if (getattr(interp, "uses_companions", False) or getattr(interp, "summoner", False)) else [],
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
        lines.append(f"  {b}: {buff_text(b)}")
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
    2. A shape or rider that contradicts the ability (a ricochet on 'a beam that strikes a single target', a lunge on a ranged spell) is dropped.
    The caller then runs dedupe_traits and fill_traits."""
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
    for a in skills:                                       # a trait that contradicts the ability goes; the fill below finds it a better home
        while True:
            why = fit_problem(a)
            if not why:
                break
            setattr(a, "shape" if "(shape)" in why else "rider", "")
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


def infer_buff(a, candidates, used=()) -> str:
    """Which buff an unlabeled buff ability is: the candidate whose flavor words appear in its text, else the first candidate."""
    candidates = [c for c in candidates if c in BUFFS] or list(BUFFS)
    text = f"{a.name} {a.description}".lower()
    scored = [(2 * sum(w in text for w in BUFFS[c].get("words", [])) + (1 if c not in used else 0), -i, c) for i, c in enumerate(candidates)]
    return max(scored)[2]


def repair_buffs(skills, offered_buffs=None) -> None:
    """A buff ability with no buff, or one that is not on offer, gets the best-fitting offered buff instead of failing the whole set."""
    for a in skills:                                       # no defense stances (f250): a guard the model wrote is a buff
        if tier_of(a.effect) == "defense":
            a.effect = type(a.effect)("buff")
    for a in skills:
        if tier_of(a.effect) != "buff":
            continue
        if not a.buff or (offered_buffs and a.buff not in offered_buffs):
            a.buff = infer_buff(a, offered_buffs or list(BUFFS), {s.buff for s in skills if s.buff})
            a.buff_stat = ""
    extra = [a for a in skills if tier_of(a.effect) == "buff"][T["max_buffs"]:]
    for a in extra:                                        # too many buffs: the surplus become plain attacks
        a.effect = type(a.effect)("damage")
        if tier_of(a.reach) == "self":
            a.reach = type(a.reach)("melee")
        a.buff = a.buff_stat = ""


def fill_traits(skills, offers: dict) -> None:
    """The model sometimes ignores the minimums. Give each missing rider and shape to the ability it suits best: a plain ability of the right
    kind, no contradiction with its text or reach, preferring wording that matches the trait. Never exceeds the cap on decorated abilities."""
    for kind, table, key in (("rider", RIDERS, "riders"), ("shape", SHAPES, "shapes")):
        offered = [t for t in offers.get(key, []) if t in table]
        need = min(T["need"][key], len(offered))
        while True:
            used = {getattr(s, kind) for s in skills if getattr(s, kind)}
            if len(used) >= need or sum(1 for s in skills if s.rider or s.shape) >= T["max_decorated"]:
                break
            best = None
            for trait in offered:
                if trait in used:
                    continue
                spec = table[trait]
                for a in skills:
                    effect = tier_of(a.effect)
                    if getattr(a, kind) or (kind == "rider" and effect not in spec["applies"]) \
                            or (kind == "shape" and (effect != "damage" or tier_of(a.reach) == "area")):
                        continue
                    setattr(a, kind, trait)
                    problem = fit_problem(a)
                    setattr(a, kind, "")
                    text = f"{a.name} {a.description}".lower()
                    multi_text = sounds_multi(a)
                    if problem or (kind == "shape" and multi_text and not spec.get("multi")):
                        continue
                    other = a.shape if kind == "rider" else a.rider
                    score = 2 * sum(w in text for w in spec.get("words", [])) - (1.5 if other else 0) \
                        + (1 if spec.get("multi") and multi_text else 0) - (1 if spec.get("multi") and not multi_text else 0)
                    if best is None or score > best[0]:
                        best = (score, trait, a)
            if best is None:
                break
            setattr(best[2], kind, best[1])
