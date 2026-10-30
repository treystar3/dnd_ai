"""(f397) The spellbook: spells on ranks and forms (data/rules/spells.yaml).

A damage spell is a RANK (learned from spell books and teachers: its base damage and mana), cast in a FORM (the dial: how strong, how
costly, how slow, how often), of an ELEMENT (what it does besides damage). Each rank of a spell is a spell of its own in the book: a line
of spells (its `line`, the id of its first rank) grows a new member each time a rank is learned, the lower ranks stay (cheap, and
weaker), and the model names each new rank, told what rank it is. Light, moderate and heavy stay with weapon techniques.

Everything here is rules and lookups; no model calls, no printing. The scene (scenes/spell_actions.py) names new ranks and tells the
player. Extending it: a new form is a row in spells.yaml with one of the deliveries below; a new rank is a row in `ranks`; heals, buffs
and control join by getting rank tables of their own (until then they keep their tiers, and `tier_for` is what a rank counts as where
tiers are still read)."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
S = yaml.safe_load((ROOT / "data" / "rules" / "spells.yaml").read_text(encoding="utf-8"))
RANKS = {int(r["rank"]): r for r in S["ranks"]}
TOP = max(RANKS)
FORMS = S["forms"]
NUMERALS = {1: "I", 2: "II", 3: "III", 4: "IV", 5: "V", 6: "VI", 7: "VII", 8: "VIII", 9: "IX", 10: "X"}
DELIVERY = {"single": "bolt", "area": "blast", "around": "burst", "over_time": "curse", "gathered": "charged"}   # the spellcraft form that casts it
TIERS = ("light", "moderate", "heavy")


# ---------- what a spell is

def numeral(rank: int) -> str:
    return NUMERALS.get(int(rank), str(rank))


KINDS = ("damage", "healing", "control")             # the kinds of spell on ranks; buffs and summons keep their tiers for now


def is_ranked(x) -> bool:
    """A spell on ranks (an Ability or a combat Move): rank 1 and up. Everything else (techniques, buffs, summons) is tiered."""
    return int(getattr(x, "rank", 0) or 0) > 0


def kind_of(x) -> str:
    return str(getattr(getattr(x, "effect", ""), "value", getattr(x, "effect", "")))


def is_ranked_damage(x) -> bool:
    """A ranked damage spell: its rank and form set its damage (the others keep their own numbers, by rank)."""
    return is_ranked(x) and kind_of(x) == "damage"


def takes_rank(effect, resource, channel: bool = False) -> bool:
    """Whether a new ability of this kind is a ranked spell: a mana damage, healing or control spell, not a strike channelled through a
    weapon."""
    ev = getattr(effect, "value", effect)
    rv = getattr(resource, "value", resource)
    return ev in KINDS and rv == "mana" and not channel


def form_of(x) -> str:
    f = getattr(x, "spell_form", "") or ""
    return f if f in FORMS else "bolt"


def delivery(x) -> str:
    """The spellcraft form the engine casts this spell as: bolt, blast, burst, curse or charged."""
    return DELIVERY[FORMS[form_of(x)]["delivery"]]


def highest_rank(level: int) -> int:
    return max((r for r, spec in RANKS.items() if spec["learn"] <= max(1, int(level))), default=1)


def learn_level(rank: int) -> int:
    return int(RANKS[int(rank)]["learn"]) if int(rank) in RANKS else 10 ** 6


def base(rank: int) -> float:
    return float(RANKS[int(rank)]["base"])


def power(x) -> float:
    p = float(FORMS[form_of(x)]["power"])
    return p * float(S["named"]["power"]) if getattr(x, "named", False) else p


def coefficient(x) -> float:
    return float(S["coefficient"]) * float(FORMS[form_of(x)].get("coefficient", 1.0))


def mana(x) -> int:
    """A flat cost: the rank's mana times the form's (for a heal, its heal form's; for a control spell, the control table's)."""
    r = int(x.rank)
    kind = kind_of(x)
    if kind == "healing":
        hf = getattr(x, "heal_form", "") or "mend"
        return max(1, round(float(S["healing"]["mana"][r - 1]) * float(S["healing"]["forms"].get(hf, {}).get("mana", 1.0))))
    if kind == "control":
        return max(1, round(float(S["control"]["mana"][r - 1])))
    m = float(RANKS[r]["mana"]) * float(FORMS[form_of(x)]["mana"])
    return max(1, round(m * (float(S["named"]["mana"]) if getattr(x, "named", False) else 1.0)))


def heal_percent(x, outside: bool = False) -> float:
    """A ranked heal's share of its target's health, by rank (out of a fight: of the caster's own)."""
    return float(S["healing"]["outside" if outside else "percent"][int(x.rank) - 1])


def cooldown(form: str) -> int:
    return int(FORMS.get(form, FORMS["bolt"]).get("cooldown", 0))


def cast_turns(form: str) -> int:
    return int(FORMS.get(form, FORMS["bolt"]).get("cast_turns", 0))


def lone(x) -> float:
    """An area form's power on a lone foe, as a share of its power (1.0 for a form that is not an area form)."""
    return float(FORMS[form_of(x)].get("lone", 1.0))


def tier_for(rank: int) -> str:
    """What a rank counts as where tiers are still read (riders, element expressions, field uses)."""
    return str(RANKS.get(int(rank), RANKS[1]).get("tier", "light"))


def form_text(form: str) -> str:
    F = FORMS.get(form, FORMS["bolt"])
    return F["text"].format(cooldown=F.get("cooldown", 0), turns=F.get("turns", 3))


def form_label(x) -> str:
    """The form a ranked spell is cast in, as one word: lance, blast; mend, renew (a heal's); control."""
    kind = kind_of(x)
    if kind == "healing":
        return getattr(x, "heal_form", "") or "mend"
    if kind == "control":
        return "control"
    return FORMS[form_of(x)]["label"].lower()


def form_description(x) -> str:
    """What the form does, for the model naming a new rank."""
    kind = kind_of(x)
    if kind == "healing":
        from engine import healing
        return healing.FORMS.get(getattr(x, "heal_form", "") or "mend", {}).get("depict", "a heal")
    if kind == "control":
        return "a control spell: it hinders a foe rather than harming it"
    return form_text(form_of(x))


def card(x) -> str:
    """'Rank III lance': how a ranked spell is named in the book and the panes ('Named blast' for a codex's spell)."""
    if getattr(x, "named", False):
        return f"Named {form_label(x)}"
    return f"Rank {numeral(x.rank)} {form_label(x)}"


# ---------- making and growing a spell

def make_ranked(a, rank: int, form: str = "") -> None:
    """Put an ability on ranks: its rank and form set every number it has (cooldown, cast turns, cost); the tier is only what it counts
    as where tiers are read."""
    from core.models import PowerTier
    a.rank = int(rank)
    a.line = a.line or a.id
    a.tier = PowerTier(tier_for(rank))
    kind = kind_of(a)
    if kind == "healing":                         # (f399) a heal: its form's cooldown; its size by rank (engine/healing.py)
        a.cooldown = int(S["healing"]["forms"].get(getattr(a, "heal_form", "") or "mend", {}).get("cooldown", 1))
    elif kind == "control":                       # (f399) a control spell: its strength by the tier its rank counts as
        a.cooldown = int(S["control"]["cooldown"])
    else:
        a.spell_form = form or form_of(a)
        a.cooldown = cooldown(a.spell_form)
        a.cast_turns = cast_turns(a.spell_form)
        a.power = 0
    a.cost_percent = 0
    a.cost = mana(a)


def lines(c) -> dict[str, list]:
    """The character's spell lines: line -> its ranks they know, lowest first."""
    out: dict[str, list] = {}
    for a in c.actives:
        if is_ranked(a) and not getattr(a, "named", False):          # a named spell never ranks up
            out.setdefault(a.line or a.id, []).append(a)
    return {k: sorted(v, key=lambda a: a.rank) for k, v in out.items()}


def top(c, line: str):
    ranks = lines(c).get(line) or []
    return ranks[-1] if ranks else None


def next_rank(c, line: str) -> int | None:
    t = top(c, line)
    if t is None or t.rank >= TOP:
        return None
    return t.rank + 1


def learnable(c, rank: int | None = None) -> list[tuple[str, object, int]]:
    """(line, its highest rank known, the next rank) for every line whose next rank the character's level allows (and is `rank`, if
    given)."""
    out = []
    for line in lines(c):
        r = next_rank(c, line)
        if r and learn_level(r) <= c.level and (rank is None or r == rank):
            out.append((line, top(c, line), r))
    return out


def waiting(c) -> list[tuple[str, object, int]]:
    """(line, highest known, next rank) for lines whose next rank needs a higher level: what the player is working toward."""
    out = []
    for line in lines(c):
        r = next_rank(c, line)
        if r and learn_level(r) > c.level:
            out.append((line, top(c, line), r))
    return out


def distinct(actives: list) -> int:
    """How many abilities the character holds, counting a spell line once: a new rank is not a new ability."""
    return sum(1 for a in actives if not is_ranked(a)) + len({a.line or a.id for a in actives if is_ranked(a) and not getattr(a, "named", False)})


def plain_name(name: str) -> str:
    return re.sub(r"\s+(?:[IVX]+)$", "", (name or "").strip())


def fallback_name(t, rank: int) -> str:
    return f"{plain_name(t.name)} {numeral(rank)}"


def learn(c, line: str, name: str = "", description: str = ""):
    """The next rank of a line, learned: a new spell in the book, of the same element and form, a rank higher, under its own name. It
    takes the place of the rank below in the spells the character has ready. Returns the new ability, or None when there is no next rank
    the character's level allows."""
    t = top(c, line)
    r = next_rank(c, line)
    if t is None or r is None or learn_level(r) > c.level:
        return None
    new = t.model_copy(deep=True)
    new.id = f"{line}_{numeral(r).lower()}"
    new.name = (name or "").strip() or fallback_name(t, r)
    new.description = (description or "").strip() or t.description
    new.line = line
    make_ranked(new, r, form_of(t))
    c.actives.append(new)
    if t.id in c.prepared:
        c.prepared = [new.id if i == t.id else i for i in c.prepared]
    return new


def catch_up(c) -> list:
    """Every line raised to the rank the character's level allows, under plain names: for a character made at a level above the first
    (a night run's starting point, the balance bots), who would have learned them along the way."""
    out = []
    for line in list(lines(c)):
        while True:
            a = learn(c, line)
            if a is None:
                break
            out.append(a)
    return out


# ---------- where ranks come from

def book_for(rank: int) -> str:
    return str((S.get("books") or {}).get(int(rank), ""))


def book_rank(item) -> int:
    """The rank a spell book teaches, or 0 for anything that is not one."""
    from engine import inventory as inv
    g = inv.GOODS.get(getattr(item, "good", "") or "")
    return int(g.rank) if g is not None and g.kind == "book" else 0


def book_drop(level: int, rank_kind: str, rng: random.Random):
    """A spell book a fallen foe leaves, sometimes: of the highest rank its level allows (never the first, which everyone has)."""
    from engine import inventory as inv
    chance = float((S.get("book_drops") or {}).get(rank_kind, 0))
    r = highest_rank(level)
    if r < 2 or rng.random() >= chance or not book_for(r):
        return None
    return inv.make_good(book_for(r), 1)


def teacher_fee(rank: int) -> int:
    fees = S["teach"]["fee_per_rank"]
    return int(fees[min(len(fees), int(rank)) - 1])


def teaches(npc) -> bool:
    return getattr(npc, "role", "") in (S["teach"].get("roles") or [])


# ---------- named spells (codices)

N = S["named"]


def is_codex(item) -> bool:
    from engine import inventory as inv
    g = inv.GOODS.get(getattr(item, "good", "") or "")
    return g is not None and g.kind == "codex" and bool(getattr(item, "spell", None))


def make_codex(level: int, rng: random.Random, element: str = ""):
    """A codex holding one named spell, unnamed yet (the scene has the model name it when it is found): its form drawn, its element
    the one given (a boss's own) or drawn, its rank the one its level allows."""
    from engine import elements as EL, inventory as inv
    forms = N["forms"]
    form = rng.choices(list(forms), weights=list(forms.values()))[0]
    element = element if element in EL.ELEMENTS else rng.choice(sorted(EL.ELEMENTS))
    item = inv.make_good("codex", 1)
    item.spell = {"name": "", "description": "", "element": element, "form": form, "rank": highest_rank(level), "level": int(level)}
    return item


def codex_drop(level: int, rng: random.Random, element: str = ""):
    """A boss's codex, now and then, once the world is deep enough for one."""
    if level < N["min_level"] or rng.random() >= float(N["boss_chance"]):
        return None
    return make_codex(level, rng, element)


def contract_codex(letter: str, level: int, rng: random.Random):
    """A codex paid with a finished guild contract of the highest ranks, now and then."""
    chance = float((N.get("contract_chance") or {}).get(letter, 0))
    if level < N["min_level"] or rng.random() >= chance:
        return None
    return make_codex(level, rng)


def codex_name(item) -> str:
    sp = getattr(item, "spell", None) or {}
    return f"codex of {sp['name']}" if sp.get("name") else "sealed codex"


def can_read(c, item) -> str:
    """'' if the character can learn the codex's spell; else why not."""
    sp = item.spell
    if c.level < int(sp.get("level", 0)) - int(N["read_below"]):
        return f"The working in the {codex_name(item)} is beyond you until level {int(sp['level']) - int(N['read_below'])}."
    if any(getattr(a, "named", False) and a.name == sp.get("name") for a in c.actives):
        return f"You already know {sp['name']}."
    return ""


def learn_named(c, item):
    """The codex's spell, learned: a named spell of its own, brought at once when there is room."""
    from core.models import Ability, Effect, PowerTier, Reach, Resource, UseContext
    from engine.abilities import slugify
    sp = item.spell
    form = sp.get("form") or "blast"
    ids = {a.id for a in c.actives}
    aid = slugify(sp.get("name") or "named spell")
    while aid in ids:
        aid += "_"
    a = Ability(id=aid, name=sp.get("name") or "Named Working", description=sp.get("description") or "", effect=Effect.DAMAGE,
                tier=PowerTier(tier_for(int(sp.get("rank") or 1))), reach=Reach("area" if FORMS[form]["delivery"] in ("area", "around") else "ranged"),
                resource=Resource.MANA, context=UseContext.COMBAT, cost=0, cooldown=0, element=sp.get("element", ""),
                attribute=c.casting_attribute or "intelligence", spell_form=form, rank=int(sp.get("rank") or 1), line=aid, named=True,
                cooldown_days=int(N["cooldown_days"]))
    a.cost = mana(a)
    c.actives.append(a)
    return a


def day_locked(c, a, minutes: int) -> int:
    """Minutes before a named spell can be cast again (0 when it can)."""
    days = int(getattr(a, "cooldown_days", 0) or 0)
    last = (getattr(c, "spell_days", None) or {}).get(a.id)
    if not days or last is None:
        return 0
    return max(0, int(last) + days * 1440 - int(minutes))


RANK_WORDS = re.compile(r"\b(rank|ranks|circle|stronger version|greater version|next level of|deepen|improve my|strengthen my|upgrade|"
                        r"higher form|more powerful version|advanced version)\b", re.I)


# ---------- the data's own checks

def problems() -> list[str]:
    from engine import inventory as inv
    bad = []
    prev_learn = prev_base = prev_mana = 0
    for r in sorted(RANKS):
        spec = RANKS[r]
        if spec.get("tier") not in TIERS:
            bad.append(f"spells.yaml rank {r}: tier '{spec.get('tier')}' is not one of {', '.join(TIERS)}")
        if not (spec["learn"] > prev_learn or r == 1) or spec["base"] <= prev_base or spec["mana"] <= prev_mana:
            bad.append(f"spells.yaml rank {r}: each rank is learned later, hits harder and costs more than the one below")
        prev_learn, prev_base, prev_mana = spec["learn"], spec["base"], spec["mana"]
    if sorted(RANKS) != list(range(1, TOP + 1)):
        bad.append("spells.yaml ranks: they run from 1 with no gaps")
    for f, F in FORMS.items():
        if F.get("delivery") not in DELIVERY:
            bad.append(f"spells.yaml form {f}: delivery '{F.get('delivery')}' is not one the engine knows ({', '.join(DELIVERY)})")
        for k in ("power", "mana", "label", "text"):
            if k not in F:
                bad.append(f"spells.yaml form {f}: needs {k}")
    for reach, by_tier in (S.get("plan") or {}).items():
        for tier, weights in by_tier.items():
            for f in weights:
                if f not in FORMS:
                    bad.append(f"spells.yaml plan {reach} {tier}: '{f}' is not a form")
    for k in ("percent", "outside", "mana"):
        if len(S["healing"][k]) < TOP:
            bad.append(f"spells.yaml healing {k}: a value for every rank")
    if len(S["control"]["mana"]) < TOP:
        bad.append("spells.yaml control mana: a value for every rank")
    from engine import healing as _h
    for hf in _h.FORMS:
        if hf not in S["healing"]["forms"]:
            bad.append(f"spells.yaml healing forms: '{hf}' (a healing.yaml form) has no mana and cooldown")
    for r, good in (S.get("books") or {}).items():
        g = inv.GOODS.get(good)
        if g is None or g.kind != "book" or g.rank != int(r):
            bad.append(f"spells.yaml books {r}: '{good}' is not a goods.yaml book of rank {r}")
    if len(S["teach"]["fee_per_rank"]) < TOP:
        bad.append("spells.yaml teach: a fee for every rank")
    for f in N.get("forms") or {}:
        if f not in FORMS:
            bad.append(f"spells.yaml named forms: '{f}' is not a form")
    g = inv.GOODS.get("codex")
    if g is None or g.kind != "codex":
        bad.append("goods.yaml: a codex good (kind codex) for the named spells")
    return bad
