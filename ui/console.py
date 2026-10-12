"""Plain-text console output. The game shows mechanics here; characters speak through say()."""

import contextlib
import textwrap

import config
from engine import items, money, stats

WIDTH = 92
CONTEXT_LABEL = {"combat": "C", "out_of_combat": "O", "both": "B"}


def say(text: str, speaker: str = "") -> None:
    with kind("speech"):
        print()
        if speaker:
            print(f"  {speaker}:")
        for para in text.strip().split("\n"):
            if para.strip():
                print(textwrap.fill(para.strip(), WIDTH, initial_indent="    ", subsequent_indent="    "))
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


def ask(main: bool = False) -> str:
    """The player's next line. main=True marks the top-level game loop (the GUI uses that to refresh its pinned view)."""
    return input("> ").strip()


def out(text: str = "") -> None:
    """A plain line that is not part of the game (start-up and shutdown messages)."""
    print(text)


damage_tags = False        # the window sets this: it draws blow figures as hoverable tokens and keeps its own combat log


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


def show_class(interp) -> None:
    constraints = "; ".join(interp.constraints) or "none"
    print(f"\n[ {interp.custom_class} | {interp.archetype.value} | focus: {interp.focus} ]")
    print(f"[ {interp.combat_identity} | themes: {', '.join(interp.themes)} ]")
    print(f"[ constraints: {constraints} | companions: {'yes' if interp.uses_companions else 'no'} ]")


CONTEXT_WORD = {"combat": "combat only", "out_of_combat": "outside combat", "both": "combat and outside"}
RULE = "─" * WIDTH


def ability_lines(a, level: int = 1, index: int | None = None, indent: int = 2) -> list[str]:
    """One ability as a small card: name, what it is and costs, what it looks like, what makes it special, what it does outside a fight."""
    from engine import ability_traits as at, field, pools
    from engine.combat import RULES as COMBAT
    pad = " " * indent
    body = pad + " " * (5 if index is not None else 2)
    table = "ability_cost_percent" if a.resource.value == "mana" else "stamina_cost_percent"
    price = max(1, round(pools.reference_pool(a.resource.value, level) * COMBAT[table][a.tier.value] / 100))
    if a.effect.value == "buff":
        price = max(1, round(price * at.T["buff_cost"]))
    if a.shape == "overcharge":
        price = round(price * at.SHAPES["overcharge"]["cost"])
    head = f"{pad}{index:>2}.  " if index is not None else f"{pad}◆ "
    lines = [f"{head}{a.name}"]
    facts = [f"{a.tier.value} {a.effect.value}", ("on you or allies" if a.effect.value == "buff" else "on yourself") if a.reach.value == "self" else f"{a.reach.value} reach", f"{price} {a.resource.value}"]
    if a.resource.value == "mana":
        facts[-1] += f" ({(a.attribute or 'casting')[:3].upper()})" if a.attribute else ""
    if a.cooldown:
        facts.append(f"cooldown {a.cooldown}")
    facts.append(CONTEXT_WORD[a.context.value])
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
    if a.companion:
        c = a.companion
        sp = COMBAT["creatures"]["spirit"]
        r = sp["role"].get(c.role.value, {"health": 1, "damage": 1})
        article = "an" if c.kind.value[:1] in "aeiou" else "a"
        feel = {"striker": "hits hard", "guardian": "sturdy, hits softly", "rogue": "quick, bleeds what it hits", "healer": "mends you and your allies", "support": "bolsters your allies' strikes"}.get(c.role.value, "")
        lines += textwrap.wrap(f"⚑ Calls {c.name}, {article} {c.kind.value} {c.role.value} - {c.description}", WIDTH - len(body),
                               initial_indent=body, subsequent_indent=body + "  ")
        lines += textwrap.wrap(f"  {sp['size'][a.tier.value]} size ({a.tier.value} tier) · {c.role.value}: {feel} "
                               f"({r['health']:g}× health, {r['damage']:g}× damage) · grows with your level",
                               WIDTH - len(body), initial_indent=body, subsequent_indent=body + "    ")
    return lines


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
            print(body + f"{o.tier.value} passive trait · {o.effect_text()}")
            print("\n".join(textwrap.wrap(o.description, WIDTH - len(body), initial_indent=body, subsequent_indent=body)))
        else:
            print("\n".join(ability_lines(o, level, i)))
        print()


def show_passives(passives) -> None:
    print("\nPASSIVE TRAITS   (◆ = changes how something works)")
    for i, p in enumerate(passives, 1):
        mark = "◆" if p.mechanic else " "
        print(f"{i:>2}. {mark} {p.name:<28} {p.effect_text()}")
        print(f"      {p.description}")


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
    return "█" * filled + "░" * (width - filled)


ATTR_MARK = "@@ATTRIBUTES@@"


def show_player_block(character, location_name: str, time_label: str, vitals: list[tuple[str, int, int]]) -> None:
    c = character
    print("\n" + "═" * WIDTH)
    print(f"  {c.name.upper()} · {c.custom_class} ({c.archetype.value}) · Level {c.level}")
    print(f"  {time_label} · {location_name}")
    print("═" * WIDTH)

    _section("CONDITION")
    for name, now, top in vitals:
        print(f"  {name.capitalize():<8} {_bar(now, top)} {now}/{top}")

    _section("ATTRIBUTES")
    gear = stats.gear_attributes(c)
    extra = [f"crafting skill {getattr(c, 'crafting_skill', 0):.0f}"]
    if getattr(c, "primary_attributes", None):
        extra.append(f"main attributes for your class: {', '.join(a[:3].upper() for a in c.primary_attributes)}")
    attrs = [{"key": k, "label": k[:3].upper(), "value": stats.effective(c, k, gear), "bonus": gear.get(k) or 0} for k in stats.STAT_NAMES]
    if panel("character", {"attrs": attrs, "points": c.unspent_points, "extra": extra}):
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
    if c.equipment:
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

    _section("ACTIVE ABILITIES")
    for a in c.actives:
        print("\n".join(ability_lines(a, c.level)))
        print()

    _section("PASSIVES")
    for p in c.passives:
        print(f"  ◆ {p.name} - {p.effect_text()}")
        print(textwrap.fill(p.description, WIDTH, initial_indent="    ", subsequent_indent="    "))

    print("═" * WIDTH)


def show_inventory(c) -> None:
    print("\n" + "═" * WIDTH)
    print(f"  INVENTORY · {money.fmt(c.coins)}")
    print("═" * WIDTH)
    windowed = panel("inventory", {})                 # the window has a Gear pane for what is worn
    if not windowed:
        _section("EQUIPPED")
        for slot, item in c.equipment.items() or []:
            star = "★ " if item.rarity == "legendary" else ""
            print(f"  {slot.replace('_', ' '):<10} {star}{items.display_name(item)} - {items.summary(item)}")
        if not c.equipment:
            print("  nothing")
        from engine import sets
        for line in sets.summary(c.equipment):
            print(("  " if not line.startswith(" ") else "") + line)
    from engine import inventory as inv
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
    print("\n  #stash to see your item box" if windowed else "\n  #equip <number or name>   #unequip <slot or name>   #stash to see your item box")
    print("  Or just say it: drink a draught, drop the hides, sell the pelts to the hunter, brew a tonic...")
    print("═" * WIDTH)


def legendary_reveal(item) -> None:
    print("\n  " + "✦" * 30)
    print(f"  ★ LEGENDARY ★  {items.display_name(item)}")
    for part in items.summary(item).split("; "):
        print(textwrap.fill(part, WIDTH, initial_indent="  ", subsequent_indent="    "))
    if item.description:
        print(textwrap.fill(f'"{item.description}"', WIDTH, initial_indent="  ", subsequent_indent="   "))
    print("  " + "✦" * 30)


def show_journal(facts: list[str], people: list[str], history: list[str] = ()) -> None:
    print("\n" + "═" * WIDTH)
    print("  JOURNAL")
    print("═" * WIDTH)
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
    print("═" * WIDTH)


def show_help() -> None:
    print("\nCOMMANDS (these don't take any game time)")
    print("  #character your character: attributes, wealth, equipment, abilities, passives")
    print("  #journal  people you've met and things you've learned")
    print("  #inventory  what you carry and wear (#equip / #unequip to change it)")
    print("  #allocate spend attribute points from leveling, e.g. #allocate str 3 dex 2")
    print("  #enchant  see enchantments an enchanter here can bind into your gear")
    print("  #help     this list")
    print("  quit      save and exit")
    print("  *text*    in asterisks is something you do, never say:  \"I'll get to it.\" *I lift the sacks*")
    print("  \"text\"    in quotes is always said aloud. Plain text is read as usual.")
    print("  #stash    see what's in your item box (stored at inns with storage)")
    print("  #shop     see what the merchants here sell and buy, with prices")
    print("  #mount    your mounts and the stable here; #mount <name> to ride one, #mount none to walk")
    print("  #board    the adventurers' guild contract board (at the guild house)")
    print("  #quests   your contracts and requests, progress, deadlines and guild rank")
    print("  #party    the adventurers travelling with you")
    print("  #standing how the groups of this town regard you; #rumors what is said of you; #correct <n> sets a false tale straight")
    print("  #dungeon  the floors of the dungeon here, what you've cleared, and when it will be remade")
    print("  #dialogue switch conversations between narrated and plain dialogue")
    print("  #numbers  show or hide the numbers under each round of combat")
    print("  #newgame  start a new character (this game is kept as a backup)")
    print("  #debug    toggle debug mode (shows what the engine decides)")
    if config.DEBUG:
        print("  #levelup [n]  (debug) gain n levels")
    print("Anything else you type is something your character does or says.")


def meter(now: float, top: float, width: int = 10) -> str:
    filled = max(0, min(width, round(width * now / top))) if top else 0
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
                 xp: tuple[int, int] = (0, 0)) -> None:
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
