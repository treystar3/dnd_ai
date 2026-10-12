"""Field abilities: every ability usable outside combat has one function (see data/rules/field.yaml).

The model chooses the function when the character is made; older characters are classified once, lazily, with a
single model call (keywords are the fallback), and the answer is saved on the ability."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
F = yaml.safe_load((ROOT / "data" / "rules" / "field.yaml").read_text(encoding="utf-8"))
FUNCTIONS = list(F["functions"])
# abilities whose out-of-combat behavior is already defined by what they are
SELF_FUNCTIONED = {"healing": True, "crafting": True, "summon": True}
# classifier words: the old keyword lists, plus each function's own draw words
KEYWORDS = {fn: list(F["keywords"].get(fn, [])) + list(spec.get("words", [])) for fn, spec in F["functions"].items()}
NEEDS_MODEL = ("damage", "control", "command")     # these only get a function if the model gave one


def tier_value(table: dict, tier) -> int:
    return table[getattr(tier, "value", tier)]


def cooldown_minutes(ability) -> int:
    base = F["cooldown_minutes"][getattr(ability.tier, "value", ability.tier)]
    return max(base, F.get("min_cooldown", {}).get(getattr(ability, "field_use", ""), 0))


def label(fn: str) -> str:
    return F["functions"][fn]["label"] if fn in F["functions"] else ""


def blurb(fn: str) -> str:
    return F["functions"][fn]["blurb"] if fn in F["functions"] else ""


def keyword_function(name: str, description: str, tags, effect: str) -> str:
    """Best guess from the words alone. Empty when nothing fits."""
    text = " ".join([name, description, *tags]).lower()
    scores = {fn: sum(1 for w in words if w in text) for fn, words in KEYWORDS.items()}
    best = max(scores, key=lambda k: scores[k])
    if scores[best] > 0:
        return best
    return F["default_by_effect"].get(effect, "")


def function_for(a) -> str:
    """The function of a proposal or ability: the model's own choice if valid, else a fallback."""
    effect = getattr(a.effect, "value", a.effect)
    context = getattr(a.context, "value", a.context)
    if context == "combat" or SELF_FUNCTIONED.get(effect):
        return ""
    chosen = getattr(a, "field_use", "")
    if chosen in FUNCTIONS:
        return chosen
    if effect in NEEDS_MODEL:
        return ""
    return keyword_function(a.name, a.description, a.tags, effect)


def needs_function(a) -> bool:
    effect = a.effect.value
    return a.context.value != "combat" and not SELF_FUNCTIONED.get(effect) and a.field_use not in FUNCTIONS


def classify(character) -> bool:
    """Give every non-combat ability of an older character its function. One model call, falling back to keywords.
    Returns True if anything changed (so the caller can save)."""
    todo = [a for a in character.actives if needs_function(a)]
    if not todo:
        return False
    answers = {}
    try:
        from llm import prompts
        from llm.contracts import FieldAssignments
        from llm.gateway import generate
        result = generate("classify_field", prompts.FIELD_SYSTEM, prompts.field_user(todo), FieldAssignments,
                          max_tokens=1200, retries=1)
        answers = {r.name.strip().lower(): r.function for r in result.abilities}
    except Exception:
        answers = {}
    from core.models import UseContext
    for a in todo:
        fn = answers.get(a.name.lower())
        if fn not in FUNCTIONS:
            fn = function_for(a)
        if fn in FUNCTIONS:
            a.field_use = fn
        else:
            a.context = UseContext.COMBAT       # nothing it can do outside a fight
            a.field_use = ""
    return True


def in_combat_function(fn: str) -> bool:
    return bool(F["functions"].get(fn, {}).get("in_combat"))


def fight_text(a) -> str:
    """What an ability does in a fight beyond its tier, when its function is one of those (bind a beast) - else empty."""
    if a.field_use in F["functions"] and in_combat_function(a.field_use):
        return f"{F['functions'][a.field_use]['label'].capitalize()} - {F['functions'][a.field_use]['blurb']}"
    return ""


def outside_text(a) -> str:
    """What the ability does outside combat, as a short sentence - empty for combat-only abilities."""
    if a.context.value == "combat" or in_combat_function(a.field_use):
        return ""
    if a.field_use in F["functions"]:
        return f"{F['functions'][a.field_use]['label'].capitalize()} - {F['functions'][a.field_use]['blurb']}"
    return {"healing": "Heal - closes your wounds between fights", "crafting": "Craft - improves the next thing you make",
            "summon": "Summon - calls your companion to your side"}.get(a.effect.value, "")


# ---------- the per-character draw ----------

def allowed(spec: dict, level: int, lesson: bool) -> bool:
    """Whether an instructor (lesson) or character creation may offer this function at this level. A taught-only function is never part
    of a new character; one with a minimum level waits for it."""
    if spec.get("taught_only") and not lesson:
        return False
    return level >= spec.get("min_level", 1)


def draw(interp, rng=None, minimum: int = 0, count: int | None = None, skip=(), level: int = 1, lesson: bool = False) -> list[str]:
    """The functions one new character (or one lesson) is offered: a handful, weighted toward what suits the class but
    always varied. A character must have at least `minimum` of them, so a social class is offered more."""
    import random
    from engine import ability_traits as AT
    rng = rng or random.SystemRandom()
    lo, hi = F["offer"]["size"]
    n = count if count is not None else max(rng.randint(lo, hi), minimum)
    keep_companions = bool(getattr(interp, "uses_companions", False))
    table = {fn: spec for fn, spec in F["functions"].items()
             if (keep_companions or spec.get("needs") != "companions") and allowed(spec, level, lesson)}
    return AT._draw(table, n, interp, rng, skip)


def offer_lines(functions: list[str]) -> str:
    lines = ["Outside-combat functions on offer (an ability usable outside combat takes ONE of these as its field_use; "
             "no two abilities may share one, and only these may be used):"]
    for fn in functions:
        lines.append(f"  {fn}: {F['functions'][fn]['blurb']}")
    return "\n".join(lines)


def repair(skills, offered: list[str]) -> None:
    """Make a model's abilities obey the offer: only offered functions, each used by one ability. An ability whose function was
    refused gets an unused offered one that suits it, or is left without (it then stays a combat ability)."""
    taken = set()
    for s in skills:
        fn = getattr(s, "field_use", "")
        if not fn:
            continue
        if fn not in offered or fn in taken:
            s.field_use = ""
        else:
            taken.add(fn)
    for s in skills:
        effect = getattr(s.effect, "value", s.effect)
        context = getattr(s.context, "value", s.context)
        if context == "combat" or SELF_FUNCTIONED.get(effect) or s.field_use:
            continue
        free = [fn for fn in offered if fn not in taken]
        text = " ".join([s.name, s.description, *s.tags]).lower()
        scored = sorted(free, key=lambda fn: -sum(1 for w in KEYWORDS[fn] if w in text))
        if scored and (effect == "utility" or sum(1 for w in KEYWORDS[scored[0]] if w in text) > 0):
            s.field_use = scored[0]
            taken.add(scored[0])



CONVERTIBLE = ("damage", "control", "mobility", "defense", "influence", "utility")
SELFISH = ("healing", "crafting", "summon")


def fill(skills, offered: list[str], required: int) -> None:
    """The model sometimes leaves too few abilities usable outside combat. Count what it has and, if short:
    1. an ability given a function but kept combat-only becomes usable in both;
    2. unused offered functions go to the abilities they suit best (utility and influence first, damage last);
    3. healing, crafting and summon abilities become usable in both."""
    def val(x):
        return getattr(x, "value", x)

    def usable(s):
        return val(s.context) != "combat" and (val(s.effect) in SELFISH or bool(s.field_use))

    def count():
        return sum(usable(s) for s in skills)

    for s in skills:
        if count() >= required:
            return
        if s.field_use and val(s.context) == "combat" and val(s.effect) in CONVERTIBLE:
            s.context = type(s.context)("both") if hasattr(s.context, "value") else "both"
    taken = {s.field_use for s in skills if s.field_use}
    while count() < required:
        free = [fn for fn in offered if fn not in taken]
        cands = [s for s in skills if not s.field_use and val(s.effect) in CONVERTIBLE]
        if not free or not cands:
            break
        weight = {"utility": 1.0, "influence": 1.0, "mobility": 0.5, "defense": 0.3, "control": 0.0, "damage": -0.5}
        best = max(((sum(w in " ".join([s.name, s.description]).lower() for w in KEYWORDS[fn]) + weight[val(s.effect)], fn, s)
                    for fn in free for s in cands), key=lambda t: t[0])
        _, fn, s = best
        s.field_use = fn
        taken.add(fn)
        s.context = type(s.context)("out_of_combat" if val(s.effect) in ("utility", "influence") else "both") if hasattr(s.context, "value") else "both"
    for s in skills:
        if count() >= required:
            break
        if val(s.effect) in SELFISH and val(s.context) == "combat":
            s.context = type(s.context)("both") if hasattr(s.context, "value") else "both"
