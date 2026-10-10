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


def outside_label(a) -> str:
    """What the ability does outside combat, in a word - empty for combat-only abilities."""
    if a.context.value == "combat":
        return ""
    if a.field_use in F["functions"]:
        return F["functions"][a.field_use]["label"]
    return {"healing": "heal", "crafting": "craft", "summon": "summon"}.get(a.effect.value, "")


def outside_text(a) -> str:
    """What the ability does outside combat, as a short sentence - empty for combat-only abilities."""
    if a.context.value == "combat":
        return ""
    if a.field_use in F["functions"]:
        return f"{F['functions'][a.field_use]['label'].capitalize()} - {F['functions'][a.field_use]['blurb']}"
    return {"healing": "Heal - closes your wounds between fights", "crafting": "Craft - improves the next thing you make",
            "summon": "Summon - calls your companion to your side"}.get(a.effect.value, "")


# ---------- the per-character draw ----------

def draw(interp, rng=None, minimum: int = 0, count: int | None = None, skip=()) -> list[str]:
    """The functions one new character (or one lesson) is offered: a handful, weighted toward what suits the class but
    always varied. A character must have at least `minimum` of them, so a social class is offered more."""
    import random
    from engine import ability_traits as AT
    rng = rng or random.SystemRandom()
    lo, hi = F["offer"]["size"]
    n = count if count is not None else max(rng.randint(lo, hi), minimum)
    keep_companions = bool(getattr(interp, "uses_companions", False))
    table = {fn: spec for fn, spec in F["functions"].items() if keep_companions or spec.get("needs") != "companions"}
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

