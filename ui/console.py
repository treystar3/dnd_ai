"""Plain-text console output. The game shows mechanics here; characters speak through say()."""

import contextlib
import textwrap

import config
from engine import items, money, stats

WIDTH = 92
CONTEXT_LABEL = {"combat": "C", "out_of_combat": "O", "both": "B"}


def say(text: str, speaker: str = "") -> None:
    """Speech under the speaker's name. A paragraph wrapped in parentheses is what they do, not what they say: it is shown as narration,
    between the spoken parts (f277)."""
    paras = [p.strip() for p in text.strip().split("\n") if p.strip()]
    with kind("speech"):
        print()
        if speaker:
            print(f"  {speaker}:")
    for para in paras:
        if para.startswith("(") and para.endswith(")") and para.count("(") == 1:
            with kind("narration"):
                print(textwrap.fill(para[1:-1].strip(), WIDTH, initial_indent="    ", subsequent_indent="    "))
        else:
            with kind("speech"):
                print(textwrap.fill(para, WIDTH, initial_indent="    ", subsequent_indent="    "))
    with kind("speech"):
        print()


def narrate(text: str) -> None:
    with kind("narration"):
        print()
        for para in text.strip().split("\n"):
            if para.strip():
                print(textwrap.fill(para.strip(), WIDTH))


def npc_says(label: str, speech: str, gesture: str = "") -> None:
    with kind("speech"):
        print()
        if gesture:
            print(textwrap.fill(f"({label} {gesture.strip().rstrip('.')}.)", WIDTH))
        print(textwrap.fill(f'{label}: "{speech.strip()}"', WIDTH, subsequent_indent="    "))


def dialogue(before: str, speaker: str, speech: str, after: str) -> None:
    if before.strip():
        narrate(before)
    with kind("speech"):
        print()
        print(textwrap.fill(f'{speaker}: "{speech.strip()}"', WIDTH, initial_indent="    ", subsequent_indent="      "))
    if after.strip():
        narrate(after)


def debug(message: str) -> None:
    if config.DEBUG:
        with kind("debug"):
            print(f"  [debug] {message}")


def ask(main: bool = False, menu: bool = False) -> str:
    """The player's next line. main=True marks the top-level game loop (the GUI uses that to refresh its pinned view); menu=True a
    prompt that is not the game loop but may still be left for the main menu (#menu), such as character creation's."""
    return input("> ").strip()


def out(text: str = "") -> None:
    """A plain line that is not part of the game (start-up and shutdown messages)."""
    print(text)


damage_tags = False        # the window sets this: it draws blow figures as hoverable tokens and keeps its own combat log


def windowed() -> bool:
    """Whether a window is drawing the game (the bridge sets damage_tags when it installs)."""
    return damage_tags


def combat_state(data: dict | None) -> bool:
    """The fight as data for a window's combat pane (None when it ends). The terminal returns False and prints text."""
    return False


def panel(name: str, data: dict) -> bool:
    """Hands structured data to a window that can draw it better than text. The terminal returns False and the caller prints text."""
    return False


def setup(data: dict) -> None:
    """A start-up screen (install Ollama, download the model). The window draws it as a page with buttons; here it is text."""
    print("\n" + "═" * 60)
    print("  " + data["title"])
    print("═" * 60)
    for line in data["lines"]:
        print(textwrap.fill(line, 70, initial_indent="  ", subsequent_indent="  "))
    if data["buttons"]:
        print("\n  Type one of: " + ", ".join(key for _, key in data["buttons"]))


def home(data: dict) -> bool:
    """(f345) The home page: True when something drew it (the window); the terminal returns False and scenes/home.py prints a menu."""
    return False


def home_done() -> None:
    """The home page is finished and a game is opening."""


def creation(data: dict) -> bool:
    """(f388) One step of character creation as a page (scenes/goddess.py show): True when a window drew it; the terminal returns False
    and the scene prints the step as text."""
    return False


def creation_done() -> None:
    """(f388) Creation is over: a window closes its pages."""


def setup_progress(frac: float, text: str) -> None:
    print(f"\r  {text}  {int(frac * 100):>3}%   ", end="", flush=True)
    if frac >= 1:
        print()


def setup_done() -> None:
    """The start-up screen is finished."""


@contextlib.contextmanager
def kind(name: str):
    """Marks what the text printed inside is (narration, speech, note, wait, combat, debug). The terminal ignores it; the GUI colours by it."""
    yield


@contextlib.contextmanager
def scope(command: str):
    """Wraps the running of a # command. The terminal does nothing with it; the GUI sends view commands to its side pane."""
    yield


def wait(message: str) -> None:
    with kind("wait"):
        print(f"\n  ({message})")


def note(message: str) -> None:
    with kind("note"):
        print(f"\n[{message}]")


def ledger(message: str) -> None:
    """(f325) A mechanical fact - coins, a contract's state, a thing taken, a check's result - kept out of the story's column. The terminal
    shows it small; the GUI folds it into the ticker under the status strip, where it stays until the next line is typed."""
    with kind("ledger"):
        print(f"  · {message}")


def show_class(interp) -> None:
    constraints = "; ".join(interp.constraints) or "none"
    print(f"\n[ {interp.custom_class} | {interp.archetype.value} | focus: {interp.focus} ]")
    print(f"[ {interp.combat_identity} | themes: {', '.join(interp.themes)} ]")
    print(f"[ constraints: {constraints} | companions: {'yes' if interp.uses_companions else 'no'} | summons: {'yes' if getattr(interp, 'summoner', False) else 'no'} ]")
    if getattr(interp, "adapted", ""):
        debug(f"adapted to this world: {interp.adapted}")         # (f264) shown only in debug mode


CONTEXT_WORD = {"combat": "combat only", "out_of_combat": "outside combat", "both": "combat and outside"}
RULE = "─" * min(WIDTH, 92)


KIND_WORD = {"damage": "", "control": "Control", "healing": "Healing", "buff": "Buff", "mobility": "Movement", "summon": "Summon",
             "command": "Command", "utility": "Utility", "influence": "Influence", "crafting": "Crafting"}


def damage_kind(a) -> str:
    """What an attack's damage is (f265): its element if it has one, else physical for a weapon blow, magic for a spell, and
    a channeled strike whichever the target resists less."""
    if getattr(a, "element", ""):
        return a.element
    if a.channel:
        return "physical or magic"
    return "magic" if a.resource.value == "mana" else "physical"


def ability_kind(a) -> str:
    """What kind of ability it is, in a word or two (f262): a Spell or a Technique for an attack, a Channeled strike for both at once,
    and the effect's own name for the rest."""
    mana = a.resource.value == "mana"
    if a.effect.value == "damage":
        return "Channeled strike" if a.channel else ("Spell" if mana else "Technique")
    if a.effect.value in ("control", "healing"):
        return f"{KIND_WORD[a.effect.value]} {'spell' if mana else 'technique'}"
    return KIND_WORD.get(a.effect.value, a.effect.value.capitalize())


def _ability_facts(a, level: int) -> list[str]:
    """What an ability is and costs, as the short facts that head its card."""
    from engine import ability_traits as at, pools
    from engine.combat import RULES as COMBAT
    table = "ability_cost_percent" if a.resource.value == "mana" else "stamina_cost_percent"
    price = max(1, round(pools.reference_pool(a.resource.value, level) * COMBAT[table][a.tier.value] / 100))
    if getattr(a, "rank", 0):
        from engine import spells
        price = spells.mana(a)                         # (f397) a ranked spell's flat cost
    if a.effect.value == "buff":
        price = max(1, round(price * at.T["buff_cost"]))
    if a.shape == "overcharge":
        price = round(price * at.SHAPES["overcharge"]["cost"])
    body = 0
    if a.channel:                                     # (f260) a technique's stamina plus half a spell's mana
        price = max(1, round(price * COMBAT["channel"]["cost"]))
        body = max(1, round(pools.reference_pool("stamina", level) * COMBAT["stamina_cost_percent"][a.tier.value] / 100 * COMBAT["channel"]["stamina"]))
    if a.reach.value != "self":
        where = f"{a.reach.value.capitalize()} reach"
    elif a.effect.value == "buff":                    # (f253) Mana Shield is your own; the rest can go on an ally
        where = "On you or allies" if at.BUFFS.get(a.buff, {}).get("allies", True) else "On yourself"
    else:
        where = ""                                    # a movement, summon, command or world ability: "on yourself" says nothing
    facts = [ability_kind(a)] + ([where] if where else []) + [f"{price} {a.resource.value}"]
    if a.resource.value == "mana":
        facts[-1] += f" ({(a.attribute or 'casting')[:3].upper()})" if a.attribute else ""
    if body:
        facts[-1] = f"{body} stamina + {facts[-1]}"
    if a.cooldown:
        facts.append(f"cooldown {a.cooldown}")
    if getattr(a, "named", False):                    # (f397) a named spell from a codex
        from engine import spells
        facts.append(f"named {spells.FORMS[spells.form_of(a)]['label'].lower()}: {round(spells.power(a) * 100)}% of a bolt's {damage_kind(a)} "
                     f"damage; once a fight, then {a.cooldown_days} day{'s' if a.cooldown_days != 1 else ''} before it can be cast again")
    elif getattr(a, "rank", 0) and a.effect.value == "damage":   # (f397) a ranked spell: its rank and form say how hard it hits
        from engine import spells
        facts.append(f"rank {spells.numeral(a.rank)}, {spells.FORMS[spells.form_of(a)]['label'].lower()}: "
                     f"{round(spells.power(a) * 100)}% of a bolt's {damage_kind(a)} damage")
    elif getattr(a, "rank", 0):                       # (f399) a ranked heal or control spell
        from engine import spells
        facts.append(f"rank {spells.numeral(a.rank)} {spells.form_label(a)}")
    elif a.effect.value == "damage":                  # (f262) how hard it hits, against what it scales from
        pct = round((a.power or COMBAT["damage"]["multiplier"][a.tier.value]) * 100)
        facts.append(f"deals {pct}% of {'spell' if a.resource.value == 'mana' and not a.channel else 'weapon'} damage as {damage_kind(a)} damage")
    facts.append(CONTEXT_WORD[a.context.value])
    return facts


def ability_tip(a, level: int = 1) -> list[list[str]]:
    """An ability as hover lines [class, text]: its name, what it is and costs, what it looks like, what makes it special, and what it does."""
    from engine import ability_traits as at, field
    out = [["h", a.name], ["dim", " · ".join(_ability_facts(a, level))], ["", a.description]]
    out += [["", f"✦ {label}: {text}"] for label, text in at.parts(a)]
    fight = field.fight_text(a)
    if fight:
        out.append(["", f"⚔ In a fight: {fight}"])
    outside = field.outside_text(a)
    if outside:
        out.append(["", f"☼ Outside combat: {outside}"])
    if a.summon_form:
        out.append(["", f"⚑ {summon_text(a)}"])
    return out


def passive_tip(p) -> list[list[str]]:
    return [["h", p.name], ["", p.effect_text()], ["dim", p.description]]


def ability_lines(a, level: int = 1, index: int | None = None, indent: int = 2) -> list[str]:
    """One ability as a small card: name, what it is and costs, what it looks like, what makes it special, what it does outside a fight."""
    from engine import ability_traits as at, field, pools
    from engine.combat import RULES as COMBAT
    pad = " " * indent
    body = pad + " " * (5 if index is not None else 2)
    head = f"{pad}{index:>2}.  " if index is not None else f"{pad}◆ "
    lines = [f"{head}{a.name}"]
    facts = _ability_facts(a, level)
    lines.append(body + " · ".join(facts))
    lines += textwrap.wrap(a.description, WIDTH - len(body), initial_indent=body, subsequent_indent=body)
    for label, text in at.parts(a):
        lines += textwrap.wrap(f"✦ {label}: {text}", WIDTH - len(body), initial_indent=body, subsequent_indent=body + "  ")
    fight = field.fight_text(a)
    if fight:
        lines += textwrap.wrap(f"⚔ In a fight: {fight}", WIDTH - len(body), initial_indent=body, subsequent_indent=body + "  ")
    out = field.outside_text(a)
    if out:
        lines += textwrap.wrap(f"☼ Outside combat: {out}", WIDTH - len(body), initial_indent=body, subsequent_indent=body + "  ")
    if a.summon_form:
        lines += textwrap.wrap(f"⚑ {summon_text(a)}", WIDTH - len(body), initial_indent=body, subsequent_indent=body + "  ")
    return lines


def summon_text(a) -> str:
    """What a summon ability makes, in the engine's terms (engine/summons.py)."""
    from engine import summons
    spec = summons.FORMS.get(a.summon_form, {})
    tier = a.tier.value
    hp = summons.S["health"][tier] * spec.get("health", 1)
    who = a.summoned.name if a.summoned else "a summon"
    last = "stays with you between fights (your Bound summon - one at a time)" if a.summon_form == "bound" else \
        f"lasts {summons.S['rounds'][tier]} rounds"
    el = f" · {a.element}" if getattr(a, "element", "") else ""
    return f"Makes {who} - {a.summon_form}: {spec.get('depict', '')} · {hp:g}% of your health · {last}{el}"


def show_actives(abilities, level: int = 1) -> None:
    print(f"\n{RULE}\n ACTIVE ABILITIES   ✦ special effect   ☼ what it does outside combat\n{RULE}")
    for i, a in enumerate(abilities, 1):
        print("\n".join(ability_lines(a, level, i)))
        print()


def show_lessons(options, level: int = 1) -> None:
    """Lessons on offer: abilities as their usual cards, passive traits as small ones marked ◇."""
    from core.models import Passive
    print(f"\n{RULE}\n LESSONS   ✦ special effect   ☼ outside combat   ◇ a lasting trait\n{RULE}")
    for i, o in enumerate(options, 1):
        if isinstance(o, Passive):
            body = " " * 7
            print(f"  {i:>2}.  ◇ {o.name}")
            print(body + f"passive trait · {o.effect_text()}")
            print("\n".join(textwrap.wrap(o.description, WIDTH - len(body), initial_indent=body, subsequent_indent=body)))
        else:
            print("\n".join(ability_lines(o, level, i)))
        print()


def passive_lines(p, index: int, indent: int = 2) -> list[str]:
    """One passive trait as a small card, laid out like an ability's: name, what kind it is, what it looks like, what it does (f250)."""
    pad = " " * indent
    body = pad + " " * 5
    lines = [f"{pad}{index:>2}.  {p.name}"]
    lines += textwrap.wrap(p.description, WIDTH - len(body), initial_indent=body, subsequent_indent=body)
    lines += textwrap.wrap(f"✦ {p.effect_text()}", WIDTH - len(body), initial_indent=body, subsequent_indent=body + "  ")
    return lines


def show_passives(passives) -> None:
    print(f"\n{RULE}\n PASSIVE TRAITS\n{RULE}")
    for i, p in enumerate(passives, 1):
        print("\n".join(passive_lines(p, i)))
        print()


def show_stat_rules(guidance: list[str] = ()) -> None:
    print(f"\nATTRIBUTES: {', '.join(stats.STAT_NAMES)}")
    print(f"{stats.rules_text()}")
    for line in guidance:
        print(textwrap.fill(f"» {line}", WIDTH, subsequent_indent="  "))
    print("Give exact numbers, or just say what matters most to you (e.g. 'quick and perceptive, a little charming').")


def show_sheet(values: dict[str, int]) -> None:
    print("\n" + "  ".join(f"{k[:3].upper()} {values[k]}" for k in stats.STAT_NAMES))


def header(text: str) -> None:
    print(f"\n── {text} " + "─" * max(4, WIDTH - len(text) - 4))


def _section(title: str) -> None:
    print(f"\n{title}")


def _bar(now: int, top: int, width: int = 20) -> str:
    filled = round(width * now / top) if top else 0
    if top and now > 0:
        filled = max(1, filled)                    # a sliver of health still shows as a sliver
    return "█" * filled + "░" * (width - filled)


SLOT_ORDER = ("main_hand", "off_hand", "head", "body", "hands", "feet", "neck", "ring")


def _slot_rank(slot: str) -> tuple:
    base = slot.rstrip("_0123456789")
    return (SLOT_ORDER.index(base) if base in SLOT_ORDER else len(SLOT_ORDER), slot)


ATTR_MARK = "@@ATTRIBUTES@@"
ABIL_MARK = "@@ABILITIES@@"
EQUIP_MARK = "@@EQUIPMENT@@"


def show_player_block(character, location_name: str, time_label: str, vitals: list[tuple[str, int, int]]) -> None:
    c = character
    print("\n" + "═" * min(WIDTH, 92))
    print(f"  {c.name.upper()} · {c.custom_class} ({c.archetype.value}) · Level {c.level}")
    print(f"  {time_label} · {location_name}")
    print("═" * min(WIDTH, 92))

    _section("CONDITION")
    for name, now, top in vitals:
        print(f"  {name.capitalize():<8} {_bar(now, top)} {now}/{top}")

    from engine import needs as _needs
    cost = _needs.penalties(c)
    if cost["checks"] or cost["stamina"] or cost["health"] or cost["damage"]:
        print(f"  Worn down: {cost['checks']:+.0f} to checks, {cost['stamina']:+.0f}% stamina, {cost['health']:+.0f}% health, {cost['damage']:+.0f}% damage")

    _section("ATTRIBUTES")
    gear = stats.gear_attributes(c)
    extra = [f"crafting skill {getattr(c, 'crafting_skill', 0):.0f}"]
    if getattr(c, "primary_attributes", None):
        extra.append(f"main attributes for your class: {', '.join(a[:3].upper() for a in c.primary_attributes)}")
    attrs = [{"key": k, "label": k[:3].upper(), "value": stats.effective(c, k, gear), "bonus": gear.get(k) or 0} for k in stats.STAT_NAMES]
    from engine import loadout
    brought = {a.id for a in loadout.prepared(c)}
    windowed = panel("character", {"attrs": attrs, "points": c.unspent_points, "extra": extra,
                                   "abilities": [{"name": a.name + ("" if a.id in brought else " (in book)"), "tip": ability_tip(a, c.level),
                                                  "brought": a.id in brought} for a in c.actives],
                                   "passives": [{"name": p.name, "tip": passive_tip(p)} for p in c.passives],
                                   "worn": [{"slot": slot.replace("_", " "), "name": items.display_name(item), "detail": items.summary(item),
                                             "rarity": item.rarity, "legendary": item.rarity == "legendary"}
                                            for slot, item in sorted(c.equipment.items(), key=lambda kv: _slot_rank(kv[0]))]})
    if windowed:
        print(ATTR_MARK)
    else:
        print("  " + "   ".join(f"{k[:3].upper()} {stats.effective(c, k, gear)}" + (f" (+{gear[k]})" if gear.get(k) else "") for k in stats.STAT_NAMES))
        for line in extra:
            print("  " + line)
        if c.unspent_points:
            print(f"  {c.unspent_points} points to spend - use #allocate, e.g. #allocate str 3 dex 2")

    _section("WEALTH")
    print(f"  {money.fmt(c.coins)}")

    _section("EQUIPMENT")
    if windowed:
        print(EQUIP_MARK)                 # (f327) the window draws the worn pieces as rows
    elif c.equipment:
        for slot, item in c.equipment.items():
            star = "★ " if item.rarity == "legendary" else ""
            print(f"  {slot.replace('_', ' '):<10} {star}{items.display_name(item)} - {items.summary(item)}")
    else:
        print("  nothing equipped")
    from engine import sets
    for line in sets.summary(c.equipment):
        print(("  " if not line.startswith(" ") else "") + line)
    if c.inventory:
        print(f"  carrying {len(c.inventory)} other item{'s' if len(c.inventory) != 1 else ''} - see #inventory")

    if c.companions:
        _section("COMPANIONS")
        for comp in c.companions:
            state = " [dead]" if comp.dead else " [fallen, recovering]" if comp.fallen else ""
            print(f"  {comp.name}{state} - {comp.description} ({comp.source})")
            if comp.perks:
                from engine import arcs as _arcs
                print(f"      {_arcs.perk_text(comp)}")

    if windowed:
        print(ABIL_MARK)                  # the window lists these by name and shows each on hover
    else:
        _section("ACTIVE ABILITIES")
        for a in c.actives:
            print("\n".join(ability_lines(a, c.level)) + ("" if a.id in brought else "\n    (in your book, not brought - #book)"))
            print()

        _section("PASSIVES")
        for p in c.passives:
            print(f"  ◆ {p.name} - {p.effect_text()}")
            print(textwrap.fill(p.description, WIDTH, initial_indent="    ", subsequent_indent="    "))

    print("═" * min(WIDTH, 92))


PACK_GROUPS = (("Gear", ("weapon", "armor", "jewelry")), ("Consumables", ("consumable",)), ("Food & herbs", ("food", "herb")))


def item_rows(bag: list, usable: bool = False) -> list[dict]:
    """(f327) The things in a bag as rows for a window's pane: what it is, what it does, what it is worth; grouped like the pack."""
    from engine import inventory as inv
    rows = []
    for n, item in enumerate(bag, 1):
        cat = inv.category(item)
        group = next((g for g, kinds in PACK_GROUPS if cat in kinds), "Materials")
        good = inv.GOODS[item.good] if item.good else None
        rows.append({"n": n, "uid": item.uid, "name": items.display_name(item), "qty": item.quantity, "detail": items.summary(item),
                     "value": money.short(inv.unit_value(item)), "rarity": item.rarity, "legendary": item.rarity == "legendary", "group": group,
                     "flavour": item.description if item.rarity == "legendary" and item.description else "",
                     "use": good.name if usable and good and good.kind != "herb" else ""})
    return rows


def key_item_rows(c) -> list[dict]:
    out = []
    for k in getattr(c, "key_items", None) or []:
        src = (f"from {k.source}, day {k.day}" if k.source else "") + (f" · for {k.for_whom}" if k.for_whom else "")
        out.append({"name": k.name, "detail": k.description, "kind": "quest" if k.kind == "quest" else "key", "source": src.strip(" ·")})
    return out


def show_inventory(c) -> None:
    from engine import inventory as inv
    if panel("inventory", {"purse": money.fmt(c.coins), "count": len(c.inventory), "cap": inv.RULES["pack_slots"],
                           "items": item_rows(c.inventory, usable=True), "keys": key_item_rows(c), "groups": [g for g, _ in PACK_GROUPS] + ["Materials"]}):
        return                                        # (f327) the window draws the pack itself; worn gear has its own pane
    print("\n" + "═" * min(WIDTH, 92))
    print(f"  INVENTORY · {money.fmt(c.coins)}")
    print("═" * min(WIDTH, 92))
    _section("EQUIPPED")
    for slot, item in c.equipment.items() or []:
        star = "★ " if item.rarity == "legendary" else ""
        print(f"  {slot.replace('_', ' '):<10} {star}{items.display_name(item)} - {items.summary(item)}")
    if not c.equipment:
        print("  nothing")
    from engine import sets
    for line in sets.summary(c.equipment):
        print(("  " if not line.startswith(" ") else "") + line)
    _section(f"PACK  {len(c.inventory)}/{inv.RULES['pack_slots']} slots")
    for n, item in enumerate(c.inventory, 1):
        star = "★ " if item.rarity == "legendary" else ""
        each = " each" if item.quantity > 1 else ""
        print(f"  {n:>2}. {star}{inv.label(item)} - {items.summary(item)} · worth {money.fmt(inv.unit_value(item))}{each}")
        if item.rarity == "legendary" and item.description:
            print(textwrap.fill(f'"{item.description}"', WIDTH, initial_indent="      ", subsequent_indent="       "))
    if not c.inventory:
        print("  nothing")
    if getattr(c, "key_items", None):
        _section("KEY ITEMS  (no slots · can't be sold or dropped · kept through death · say 'discard' to let one go)")
        for k in c.key_items:
            tag = "! quest" if k.kind == "quest" else "✧ key  "
            src = f" · from {k.source}, day {k.day}" if k.source else ""
            src += f" · for {k.for_whom}" if k.for_whom else ""
            print(textwrap.fill(f"  {tag}  {k.name} - {k.description}{src}", WIDTH, subsequent_indent="           "))
    print("\n  #equip <number or name>   #unequip <slot or name>   #stash to see your item box")
    print("  Or just say it: drink a draught, drop the hides, sell the pelts to the hunter, brew a tonic...")
    print("═" * min(WIDTH, 92))


def legendary_reveal(item) -> None:
    print("\n  " + "✦" * 30)
    print(f"  ★ LEGENDARY ★  {items.display_name(item)}")
    for part in items.summary(item).split("; "):
        print(textwrap.fill(part, WIDTH, initial_indent="  ", subsequent_indent="    "))
    if item.description:
        print(textwrap.fill(f'"{item.description}"', WIDTH, initial_indent="  ", subsequent_indent="   "))
    print("  " + "✦" * 30)


def show_journal(facts: list[str], people: list[str], history: list[str] = ()) -> None:
    print("\n" + "═" * min(WIDTH, 92))
    print("  JOURNAL")
    print("═" * min(WIDTH, 92))
    _section("PEOPLE YOU'VE MET")
    for line in people or ["no one yet"]:
        print(f"  {line}")
    _section("THINGS YOU'VE LEARNED")
    for text in facts or ["nothing yet"]:
        print(textwrap.fill(" ".join(text.split()), WIDTH, initial_indent="  - ", subsequent_indent="    "))
    if history:
        _section("ITEMS DELIVERED OR LET GO")
        for text in history:
            print(textwrap.fill(text, WIDTH, initial_indent="  - ", subsequent_indent="    "))
    print("═" * min(WIDTH, 92))


def show_help() -> None:
    print("\nCOMMANDS (these don't take any game time)")
    print("  #character your character: attributes, wealth, equipment, abilities, passives")
    print("  #stats     every combat number: attack power, hit and crit chance, armor, ward, evasion")
    print("  #journal  people you've met and things you've learned")
    print("  #events   what has happened, in order")
    print("  #audit    where this session's record of every model call is kept")
    print("  #refusals the lines the game could not act on this session, and what it asked")
    print("  #report [note]  flag what you just read: it is saved with the calls behind it under logs/reports, and sent nowhere")
    print("  #credits  who made what the game is built from")
    print("  #inventory  what you carry and wear (#equip / #unequip to change it)")
    print("  #book     your abilities: what you bring (5 spells and 5 techniques at first) and what stays in your book")
    print("  #prepare  change what you bring, out of a fight and once a day, e.g. #prepare 1 3 4 or #prepare Firebolt, Ice Wall")
    print("  #prebuff  the buffs you cast before the first blow of a fight you start, e.g. #prebuff Stoneskin, Frost Armor (#prebuff none clears)")
    print("  #allocate spend attribute points from leveling, e.g. #allocate str 3 dex 2")
    print("  #enchant  see enchantments an enchanter here can bind into your gear")
    print("  #pronoun  how people see you: #pronoun she, #pronoun he or #pronoun they")
    print("  #resetlayout  put the info pane's buttons back in their original order (drag a button to move it; game window only)")
    print("  #help     this list")
    print("  quit      save and exit")
    print("  *text*    in asterisks is something you do, never say:  \"I'll get to it.\" *I lift the sacks*")
    print("  \"text\"    in quotes is always said aloud. Plain text is read as usual.")
    print("  #stash    see what's in your item box (stored at inns with storage)")
    print("  #shop     see what the merchants here sell and buy, with prices")
    print("  #mount    your mounts and the stable here; #mount <name> to ride one, #mount none to walk")
    print("  #board    the adventurers' guild contract board (at the guild house)")
    print("  #quests   your contracts and requests, progress, deadlines and guild rank")
    print("  #party    your companions and the adventurers travelling with you (#name <companion> = <new name> renames one)")
    print("  #standing how the groups of this town regard you; #rumors what is said of you; #correct <n> sets a false tale straight")
    print("  #dungeon  the floors of the dungeon here, what you've cleared, and when it will be remade")
    print("  #dialogue switch conversations between narrated and plain dialogue")
    print("  #numbers  show or hide the numbers under each round of combat")
    print("  #menu     save and go back to the main menu: continue, load another game, or start a new one")
    print("  #debug    toggle debug mode (shows what the engine decides)")
    if config.DEBUG:
        print("  #levelup [n]  (debug) gain n levels")
    print("Anything else you type is something your character does or says.")


def meter(now: float, top: float, width: int = 10) -> str:
    filled = max(0, min(width, round(width * now / top))) if top else 0
    if top and now > 0:
        filled = max(1, filled)
    return "⸢" + "▰" * filled + "▱" * (width - filled) + "⸥"


def stamina_word(fraction: float) -> str:
    if fraction >= 0.9:
        return "Fresh"
    if fraction >= 0.6:
        return "Steady"
    if fraction >= 0.3:
        return "Tired"
    if fraction > 0:
        return "Exhausted"
    return "Spent"


def combat_panel(lines: list[str]) -> None:
    with kind("combat"):
        print()
        for line in lines:
            print(f"  {line}")


def combat_numbers(lines: list[str]) -> None:
    if lines:
        with kind("combat"):
            print()
            print(textwrap.fill("⚔ " + " · ".join(lines), WIDTH, initial_indent="  ", subsequent_indent="    "))


def status_block(when: str, weather: str, place_line: str, spot_line: str,
                 vitals: dict[str, tuple[float, int]], level: int, points: int, coins: int,
                 xp: tuple[int, int] = (0, 0), needs: dict | None = None) -> None:
    hp, mp, sp = vitals["health"], vitals["mana"], vitals["stamina"]
    lines = [
        f"[{when} | {weather} — {place_line}]",
        f"🔍 {spot_line}",
        f"HP {meter(*hp)} {round(hp[0])}/{hp[1]}",
        f"MP {meter(*mp)} {round(mp[0])}/{mp[1]}",
        f"SP {meter(*sp)} {round(sp[0])}/{sp[1]} ({stamina_word(sp[0] / sp[1] if sp[1] else 0)})",
        f"XP {meter(*xp)} {xp[0]}/{xp[1]} ({round(100 * xp[0] / xp[1]) if xp[1] else 0}%)",
        f"LV: {level} | PTS: {points}",
        f"$: {money.fmt(coins)}",
    ]
    print()
    for line in lines:
        print(f"  {line}")


OUTPUTS = ("say", "narrate", "npc_says", "dialogue", "note", "wait", "ledger")


def guard_outputs() -> None:
    """(f391) Every line the player sees passes the output gate (engine/hygiene.py) on its way out: no JSON tail, code, placeholder,
    escape or 'the player' reaches the page, whoever drew the line. The terminal's functions are gated as this module loads; the window
    keeps them (it only takes stdout); a night's harness, which puts its own in place, calls this again. Gating twice is a no-op."""
    import sys
    from engine import hygiene
    me = sys.modules[__name__]
    for name in OUTPUTS:
        fn = getattr(me, name)
        if getattr(fn, "gated", False):
            continue

        mend = (lambda s: hygiene.undash(hygiene.clean(s))) if name == "narrate" else hygiene.clean   # (f396) the narrator writes no dashes

        def gated(*args, _fn=fn, _mend=mend, **kwargs):
            return _fn(*(_mend(a) if isinstance(a, str) else a for a in args),
                       **{k: _mend(v) if isinstance(v, str) else v for k, v in kwargs.items()})
        gated.gated, gated.inner = True, fn
        setattr(me, name, gated)


guard_outputs()
