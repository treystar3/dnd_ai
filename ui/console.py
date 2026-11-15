"""Plain-text console output. The game shows mechanics here; characters speak through say().

(f635) Everything the game shows or asks goes to a channel: the one in use on this thread (use), or the process's (install: the
terminal's, or the page of the window that is up). The functions here are how the game calls it. Each is answered on the channel by
what was put in its place there (put), or the channel's own method, or the function as it is written here. No output is set on the
module after import: setting a name on it raises."""

import builtins
import contextlib
import contextvars
import functools
import sys
import textwrap
import types

import config
from engine import actor, items, money, stats

WIDTH = 92                 # the terminal's; what the game wraps to is the channel's (width())
CONTEXT_LABEL = {"combat": "C", "out_of_combat": "O", "both": "B"}
SEAM = ("ask", "scope", "kind", "status_block", "busy_text", "panel", "setup_progress", "home", "home_done", "creation", "creation_done",
        "combat_state")     # (f635) what is the channel's own to answer: a window draws these, the terminal answers as below
_PLAIN: dict = {}           # (f635) the outputs as written in this module, by name: what answers where nothing else does


class Channel:
    """(f580) Where the console's text goes. (f635) And everything else the game shows or asks for: the methods below are the terminal's
    answers, and a window's page has its own (ui/gui/bridge.py Page). What stands in for an output (a test's capture, an operation's
    hold, the turn log's tap, the recorder, the question fence) is set on the channel, and answers on that channel only."""

    width = WIDTH              # what the story's lines are wrapped to
    windowed = False           # whether a window draws the game: blow figures as hoverable tokens, a combat log of its own

    def write(self, text: str, end: str = "\n") -> None:
        raise NotImplementedError

    def emit(self, args: tuple, sep: str, end: str, flush: bool) -> None:
        self.write(sep.join(str(a) for a in args), end)

    def get(self, name: str):
        """(f635) What answers this output here now: what was put in its place, the channel's own method, or the console's function."""
        standing = self.__dict__.get("_standing")
        if standing and name in standing:
            return standing[name]
        own = getattr(self, name, None)
        return own if callable(own) else _PLAIN[name]

    def set(self, name: str, fn) -> None:
        """(f635) This answers the output here from now on. A wrapper reads what answered before it (get) and puts that back when it is
        done. The console's own function is refused: it asks the channel, so it would only call itself."""
        if getattr(fn, "routed", None):
            raise TypeError(f"console.{fn.routed} asks the channel and cannot stand in on it: console.now({name!r}) reads what answers")
        if name not in SEAM and name not in _PLAIN:
            raise KeyError(f"console.{name} is not an output a channel answers (ui/console.py NAMES)")
        self.__dict__.setdefault("_standing", {})[name] = fn

    def ask(self, main: bool = False, menu: bool = False) -> str:
        """The player's next line. main=True marks the top-level game loop (the GUI uses that to refresh its pinned view); menu=True a
        prompt that is not the game loop but may still be left for the main menu (#menu), such as character creation's."""
        return input("> ").strip()

    @contextlib.contextmanager
    def kind(self, name: str):
        """Marks what the text printed inside is (narration, speech, note, wait, combat, debug). The terminal ignores it; the GUI colours by it."""
        yield

    @contextlib.contextmanager
    def scope(self, command: str):
        """Wraps the running of a # command. The terminal does nothing with it; the GUI sends view commands to its side pane."""
        yield

    def status_block(self, when: str, weather: str, place_line: str, spot_line: str,
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

    def busy_text(self, message: str) -> None:
        """(f423) What the waiting indicator says while the world is busy ("People go about their day." while a place's people are made). It is
        never a line of the story: in the window it is the indicator's own words, until the wait is over; the terminal shows nothing."""

    def panel(self, name: str, data: dict) -> bool:
        """Hands structured data to a window that can draw it better than text. The terminal returns False and the caller prints text."""
        return False

    def setup_progress(self, frac: float, text: str) -> None:
        """(f526, f532) The model load's progress while Continue waits on it (main.py; llm/launch.py Screen calls it only while the wait is on
        screen). The installer's start-up screen that once shared this place is gone with it (f532)."""
        print(f"\r  {text}  {int(frac * 100):>3}%   ", end="", flush=True)
        if frac >= 1:
            print()

    def home(self, data: dict) -> bool:
        """(f345) The home page: True when something drew it (the window); the terminal returns False and scenes/home.py prints a menu."""
        return False

    def home_done(self) -> None:
        """The home page is finished and a game is opening."""

    def creation(self, data: dict) -> bool:
        """(f388) One step of character creation as a page (scenes/goddess.py show): True when a window drew it; the terminal returns False
        and the scene prints the step as text."""
        return False

    def creation_done(self) -> None:
        """(f388) Creation is over: a window closes its pages."""

    def combat_state(self, data: dict | None) -> bool:
        """The fight as data for a window's combat pane (None when it ends). The terminal returns False and prints text."""
        return False


class Stdout(Channel):
    """Whatever sys.stdout is when the line is written (the window swaps it in), in the built-in print's own pieces."""

    def write(self, text: str, end: str = "\n") -> None:
        self.emit((text,), " ", end, False)

    def emit(self, args: tuple, sep: str, end: str, flush: bool) -> None:
        builtins.print(*args, sep=sep, end=end, flush=flush)


STDOUT = Stdout()
_process: Channel = STDOUT                     # the process's channel: the terminal's, or the page of the window that is up (install)
_bound: contextvars.ContextVar = contextvars.ContextVar("console_channel", default=None)     # (f635) the one in use on this thread


def channel() -> Channel:
    """The channel in use on this thread; the process's where none is."""
    mine = _bound.get()
    return _process if mine is None else mine


@contextlib.contextmanager
def use(ch: Channel):
    """(f580) This channel is the console's until the block ends; the one before it is back after, a fault or not. (f635) On this
    thread: another thread's turn has its own, or the process's."""
    token = _bound.set(ch)
    try:
        yield ch
    finally:
        _bound.reset(token)


def install(ch: Channel) -> Channel:
    """(f635) This channel is the process's from now on: a window's page while it is up, the one it found when it goes. The one
    before is returned, for whoever installed to put back."""
    global _process
    was, _process = _process, ch
    return was


def now(name: str):
    """(f635) What answers this output on the channel in use (Channel.get): read by a wrapper before it stands in, to call and to put back."""
    return channel().get(name)


def put(name: str, fn) -> None:
    """(f635) This answers the output on the channel in use from now on (Channel.set)."""
    channel().set(name, fn)


def width() -> int:
    """What the channel in use wraps the story's lines to (a window's page wraps for itself, so the game must not wrap first)."""
    return channel().width


def windowed() -> bool:
    """Whether a window is drawing the game."""
    return channel().windowed


def _seam(name: str):
    """(f635) A name of the seam as the game calls it on the console: answered by the channel in use."""
    def through(*a, **k):
        return channel().get(name)(*a, **k)
    through.__name__ = through.__qualname__ = name
    through.__doc__ = getattr(Channel, name).__doc__
    through.routed = name
    return through


def _out(fn):
    """(f635) An output written here, as the game calls it: answered by the channel in use, with this function where nothing stands in."""
    name = fn.__name__
    _PLAIN[name] = fn

    @functools.wraps(fn)
    def through(*a, **k):
        return channel().get(name)(*a, **k)
    through.routed = name
    return through


ask, scope, kind, status_block = _seam("ask"), _seam("scope"), _seam("kind"), _seam("status_block")
busy_text, panel, setup_progress = _seam("busy_text"), _seam("panel"), _seam("setup_progress")
home, home_done, creation, creation_done = _seam("home"), _seam("home_done"), _seam("creation"), _seam("creation_done")
combat_state = _seam("combat_state")


@_out
def print(*args, sep: str = " ", end: str = "\n", flush: bool = False) -> None:
    """(f580) The console's one way out: every print below is this one, to the channel in use."""
    channel().emit(args, sep, end, flush)


@_out
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
                print(textwrap.fill(para[1:-1].strip(), width(), initial_indent="    ", subsequent_indent="    "))
        else:
            with kind("speech"):
                print(textwrap.fill(para, width(), initial_indent="    ", subsequent_indent="    "))
    with kind("speech"):
        print()


@_out
def narrate(text: str) -> None:
    with kind("narration"):
        print()
        for para in text.strip().split("\n"):
            if para.strip():
                print(textwrap.fill(para.strip(), width()))


@_out
def npc_says(label: str, speech: str, gesture: str = "") -> None:
    with kind("speech"):
        print()
        if gesture:
            print(textwrap.fill(f"({label} {gesture.strip().rstrip('.')}.)", width()))
        print(textwrap.fill(f'{label}: "{speech.strip()}"', width(), subsequent_indent="    "))


@_out
def dialogue(before: str, speaker: str, speech: str, after: str) -> None:
    if before.strip():
        narrate(before)
    with kind("speech"):
        print()
        print(textwrap.fill(f'{speaker}: "{speech.strip()}"', width(), initial_indent="    ", subsequent_indent="      "))
    if after.strip():
        narrate(after)


@_out
def debug(message: str) -> None:
    if actor.prefs().debug:
        with kind("debug"):
            print(f"  [debug] {message}")


@_out
def out(text: str = "") -> None:
    """A plain line that is not part of the game (start-up and shutdown messages)."""
    print(text)


@_out
def wait(message: str) -> None:
    with kind("wait"):
        print(f"\n  ({message})")


@_out
def note(message: str) -> None:
    with kind("note"):
        print(f"\n[{message}]")


@_out
def ledger(message: str) -> None:
    """(f325) A mechanical fact - coins, a contract's state, a thing taken, a check's result - kept out of the story's column. The terminal
    shows it small; the GUI folds it into the ticker under the status strip, where it stays until the next line is typed."""
    with kind("ledger"):
        print(f"  · {message}")


@_out
def show_class(interp) -> None:
    constraints = "; ".join(interp.constraints) or "none"
    print(f"\n[ {interp.custom_class} | {interp.archetype.value} | focus: {interp.focus} ]")
    print(f"[ {interp.combat_identity} | themes: {', '.join(interp.themes)} ]")
    print(f"[ constraints: {constraints} | companions: {'yes' if interp.uses_companions else 'no'} | summons: {'yes' if getattr(interp, 'summoner', False) else 'no'} ]")
    if getattr(interp, "adapted", ""):
        debug(f"adapted to this world: {interp.adapted}")         # (f264) shown only in debug mode


CONTEXT_WORD = {"combat": "combat only", "out_of_combat": "outside combat", "both": "combat and outside"}
RULE = "─" * 92


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


def _ability_facts(a, level: int, rank: bool = True) -> list[str]:
    """What an ability is and costs, as the short facts that head its card. rank=False leaves a spell's rank unsaid: at character creation
    every spell is rank I, so it says nothing (f401)."""
    from engine import ability_traits as at, pools
    from engine.combat import RULES as COMBAT
    table = "ability_cost_percent" if a.resource.value == "mana" else "stamina_cost_percent"
    price = max(1, round(pools.reference_pool(a.resource.value, level) * COMBAT[table][a.tier.value] / 100))
    if getattr(a, "rank", 0):
        from engine import spells
        price = spells.mana(a)                         # (f397) a ranked spell's flat cost
    if a.effect.value == "buff":
        from engine import spells
        price = spells.buff_mana(level)               # (f400) a buff: no tier, a flat cost by the rank the level allows
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
        facts.append((f"rank {spells.numeral(a.rank)}, " if rank else "") + f"{spells.FORMS[spells.form_of(a)]['label'].lower()}: "
                     f"{round(spells.power(a) * 100)}% of a bolt's {damage_kind(a)} damage")
    elif getattr(a, "rank", 0):                       # (f399) a ranked heal or control spell
        from engine import spells
        facts.append(f"rank {spells.numeral(a.rank)} {spells.form_label(a)}" if rank else spells.form_label(a))
    elif a.effect.value == "damage":                  # (f262) how hard it hits, against what it scales from
        pct = round((a.power or COMBAT["damage"]["multiplier"][a.tier.value]) * 100)
        facts.append(f"deals {pct}% of {'spell' if a.resource.value == 'mana' and not a.channel else 'weapon'} damage as {damage_kind(a)} damage")
    facts.append(CONTEXT_WORD[a.context.value])
    return facts


def ability_tip(a, level: int = 1, rank: bool = True) -> list[list[str]]:
    """An ability as hover lines [class, text]: its name, what it is and costs, what it looks like, what makes it special, and what it does."""
    from engine import ability_traits as at, field
    out = [["h", a.name], ["dim", " · ".join(_ability_facts(a, level, rank))], ["", a.description]]
    out += [["", f"✦ {label}: {text}"] for label, text in at.parts(a, rank)]
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


def ability_lines(a, level: int = 1, index: int | None = None, indent: int = 2, rank: bool = True) -> list[str]:
    """One ability as a small card: name, what it is and costs, what it looks like, what makes it special, what it does outside a fight."""
    from engine import ability_traits as at, field, pools
    from engine.combat import RULES as COMBAT
    pad = " " * indent
    body = pad + " " * (5 if index is not None else 2)
    head = f"{pad}{index:>2}.  " if index is not None else f"{pad}◆ "
    lines = [f"{head}{a.name}"]
    facts = _ability_facts(a, level, rank)
    lines.append(body + " · ".join(facts))
    lines += textwrap.wrap(a.description, width() - len(body), initial_indent=body, subsequent_indent=body)
    for label, text in at.parts(a, rank):
        lines += textwrap.wrap(f"✦ {label}: {text}", width() - len(body), initial_indent=body, subsequent_indent=body + "  ")
    fight = field.fight_text(a)
    if fight:
        lines += textwrap.wrap(f"⚔ In a fight: {fight}", width() - len(body), initial_indent=body, subsequent_indent=body + "  ")
    out = field.outside_text(a)
    if out:
        lines += textwrap.wrap(f"☼ Outside combat: {out}", width() - len(body), initial_indent=body, subsequent_indent=body + "  ")
    if a.summon_form:
        lines += textwrap.wrap(f"⚑ {summon_text(a)}", width() - len(body), initial_indent=body, subsequent_indent=body + "  ")
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


@_out
def show_actives(abilities, level: int = 1) -> None:
    """The abilities offered at character creation, where every spell is rank I: the rank goes unsaid (f401)."""
    print(f"\n{RULE}\n ACTIVE ABILITIES   ✦ special effect   ☼ what it does outside combat\n{RULE}")
    for i, a in enumerate(abilities, 1):
        print("\n".join(ability_lines(a, level, i, rank=False)))
        print()


@_out
def show_lessons(options, level: int = 1) -> None:
    """Lessons on offer: abilities as their usual cards, passive traits as small ones marked ◇."""
    from core.models import Passive
    print(f"\n{RULE}\n LESSONS   ✦ special effect   ☼ outside combat   ◇ a lasting trait\n{RULE}")
    for i, o in enumerate(options, 1):
        if isinstance(o, Passive):
            body = " " * 7
            print(f"  {i:>2}.  ◇ {o.name}")
            print(body + f"passive trait · {o.effect_text()}")
            print("\n".join(textwrap.wrap(o.description, width() - len(body), initial_indent=body, subsequent_indent=body)))
        else:
            print("\n".join(ability_lines(o, level, i)))
        print()


def passive_lines(p, index: int, indent: int = 2) -> list[str]:
    """One passive trait as a small card, laid out like an ability's: name, what kind it is, what it looks like, what it does (f250)."""
    pad = " " * indent
    body = pad + " " * 5
    lines = [f"{pad}{index:>2}.  {p.name}"]
    lines += textwrap.wrap(p.description, width() - len(body), initial_indent=body, subsequent_indent=body)
    lines += textwrap.wrap(f"✦ {p.effect_text()}", width() - len(body), initial_indent=body, subsequent_indent=body + "  ")
    return lines


@_out
def show_passives(passives) -> None:
    print(f"\n{RULE}\n PASSIVE TRAITS\n{RULE}")
    for i, p in enumerate(passives, 1):
        print("\n".join(passive_lines(p, i)))
        print()


@_out
def show_stat_rules(guidance: list[str] = ()) -> None:
    print(f"\nATTRIBUTES: {', '.join(stats.STAT_NAMES)}")
    print(f"{stats.rules_text()}")
    for line in guidance:
        print(textwrap.fill(f"» {line}", width(), subsequent_indent="  "))
    print("Give exact numbers, or just say what matters most to you (e.g. 'quick and perceptive, a little charming').")


@_out
def show_sheet(values: dict[str, int]) -> None:
    print("\n" + "  ".join(f"{k[:3].upper()} {values[k]}" for k in stats.STAT_NAMES))


@_out
def header(text: str) -> None:
    print(f"\n── {text} " + "─" * max(4, width() - len(text) - 4))


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


@_out
def show_player_block(character, location_name: str, time_label: str, vitals: list[tuple[str, int, int]]) -> None:
    c = character
    print("\n" + "═" * min(width(), 92))
    print(f"  {c.name.upper()} · {c.custom_class} ({c.archetype.value}) · Level {c.level}")
    print(f"  {time_label} · {location_name}")
    print("═" * min(width(), 92))

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
            print(textwrap.fill(p.description, width(), initial_indent="    ", subsequent_indent="    "))

    print("═" * min(width(), 92))


PACK_GROUPS = (("Gear", ("weapon", "armor", "jewelry")), ("Consumables", ("consumable",)), ("Food & herbs", ("food", "herb")),
               ("Trade goods", ("trade",)))                                   # (f545's review) salt and cloth are no materials


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
                     "use": good.name if usable and good and good.kind not in ("herb", "trade") else ""})   # (f545's review) carried, never used
    return rows


def key_item_rows(c) -> list[dict]:
    out = []
    for k in getattr(c, "key_items", None) or []:
        src = (f"from {k.source}, day {k.day}" if k.source else "") + (f" · for {k.for_whom}" if k.for_whom else "")
        out.append({"name": k.name, "detail": k.description, "kind": "quest" if k.kind == "quest" else "key", "source": src.strip(" ·")})
    return out


@_out
def show_inventory(c, carried=()) -> None:
    """The pack and what is worn; (f592) `carried`: the things in the world the character carries in hand (engine/objects.py)."""
    from engine import inventory as inv
    held = [{"name": o.name, "detail": o.data.get("what", "")} for o in carried]
    if panel("inventory", {"purse": money.fmt(c.coins), "count": len(c.inventory), "cap": inv.RULES["pack_slots"],
                           "items": item_rows(c.inventory, usable=True), "keys": key_item_rows(c), "carried": held,
                           "groups": [g for g, _ in PACK_GROUPS] + ["Materials"]}):
        return                                        # (f327) the window draws the pack itself; worn gear has its own pane
    print("\n" + "═" * min(width(), 92))
    print(f"  INVENTORY · {money.fmt(c.coins)}")
    print("═" * min(width(), 92))
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
            print(textwrap.fill(f'"{item.description}"', width(), initial_indent="      ", subsequent_indent="       "))
    if not c.inventory:
        print("  nothing")
    if getattr(c, "key_items", None):
        _section("KEY ITEMS  (no slots · can't be sold or dropped · kept through death · say 'discard' to let one go)")
        for k in c.key_items:
            tag = "! quest" if k.kind == "quest" else "✧ key  "
            src = f" · from {k.source}, day {k.day}" if k.source else ""
            src += f" · for {k.for_whom}" if k.for_whom else ""
            print(textwrap.fill(f"  {tag}  {k.name} - {k.description}{src}", width(), subsequent_indent="           "))
    if held:
        _section("CARRIED IN HAND  (no pack slots · set down with 'drop')")
        for h in held:
            print(textwrap.fill(f"  {h['name']}" + (f" - {h['detail']}" if h["detail"] else ""), width(), subsequent_indent="      "))
    print("\n  #equip <number or name>   #unequip <slot or name>   #stash to see your item box")
    print("  Or just say it: drink a draught, drop the hides, sell the pelts to the hunter, brew a tonic...")
    print("═" * min(width(), 92))


@_out
def legendary_reveal(item) -> None:
    print("\n  " + "✦" * 30)
    print(f"  ★ LEGENDARY ★  {items.display_name(item)}")
    for part in items.summary(item).split("; "):
        print(textwrap.fill(part, width(), initial_indent="  ", subsequent_indent="    "))
    if item.description:
        print(textwrap.fill(f'"{item.description}"', width(), initial_indent="  ", subsequent_indent="   "))
    print("  " + "✦" * 30)


@_out
def show_journal(facts: list[str], people: list[str], history: list[str] = ()) -> None:
    print("\n" + "═" * min(width(), 92))
    print("  JOURNAL")
    print("═" * min(width(), 92))
    _section("PEOPLE YOU'VE MET")
    for line in people or ["no one yet"]:
        print(f"  {line}")
    _section("THINGS YOU'VE LEARNED")
    for text in facts or ["nothing yet"]:
        print(textwrap.fill(" ".join(text.split()), width(), initial_indent="  - ", subsequent_indent="    "))
    if history:
        _section("ITEMS DELIVERED OR LET GO")
        for text in history:
            print(textwrap.fill(text, width(), initial_indent="  - ", subsequent_indent="    "))
    print("═" * min(width(), 92))


@_out
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
    print("  #quests   your contracts and requests, progress and guild rank")
    print("  #party    your companions and the adventurers travelling with you (#name <companion> = <new name> renames one)")
    print("  #standing how the groups of this town regard you; #rumors what is said of you; #correct <n> sets a false tale straight")
    print("  #dungeon  the floors of the dungeon here, what you've cleared, and when it will be remade")
    print("  #dialogue switch conversations between narrated and plain dialogue")
    print("  #numbers  show or hide the numbers under each round of combat")
    print("  #menu     save and go back to the main menu: continue, load another game, or start a new one")
    print("  #debug    toggle debug mode (shows what the engine decides)")
    if actor.prefs().debug:
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


@_out
def combat_panel(lines: list[str]) -> None:
    with kind("combat"):
        print()
        for line in lines:
            print(f"  {line}")


@_out
def combat_numbers(lines: list[str]) -> None:
    if lines:
        with kind("combat"):
            print()
            print(textwrap.fill("⚔ " + " · ".join(lines), width(), initial_indent="  ", subsequent_indent="    "))


OUTPUTS = ("say", "narrate", "npc_says", "dialogue", "note", "wait", "ledger")
STORY = ("say", "narrate", "npc_says", "dialogue")      # (f403) the story's own lines, narration and speech: no dashes (the game's notes keep theirs)


def _gate(name: str, fn):
    """(f391) The output behind the gate (engine/hygiene.py): no JSON tail, code, placeholder, escape or 'the player' reaches the page."""
    from engine import hygiene
    mend = (lambda s: hygiene.undash(hygiene.unstage(hygiene.unnote(hygiene.clean(s))))) if name in STORY else hygiene.clean   # (f396, f403) no dashes in the story; (f404) no notes; (f449) no stage directions

    def gated(*args, _fn=fn, _mend=mend, **kwargs):
        return _fn(*(_mend(a) if isinstance(a, str) else a for a in args),
                   **{k: _mend(v) if isinstance(v, str) else v for k, v in kwargs.items()})
    gated.gated, gated.inner = True, fn
    return gated


def guard_outputs() -> None:
    """(f391) Every line the player sees passes the output gate on its way out, whoever drew the line. The outputs written here are
    gated as this module loads, for every channel. A night's harness, which puts its own in their place on its channel, calls this to
    gate those. Gating twice is a no-op."""
    ch = channel()
    for name in OUTPUTS:
        fn = ch.get(name)
        if not getattr(fn, "gated", False):
            ch.set(name, _gate(name, fn))


for _name in OUTPUTS:
    _PLAIN[_name] = _gate(_name, _PLAIN[_name])
NAMES = SEAM + tuple(_PLAIN)        # (f635) every output a channel answers


class _Sealed(types.ModuleType):
    """(f635) No output is set on the console module after import: one is replaced on a channel, never here, or a second player's
    turn would be shown on the first one's screen. The two names a window used to set are read from the channel in use."""

    WIDTH = property(lambda self: channel().width)
    damage_tags = property(lambda self: channel().windowed)

    def __setattr__(self, name, value):
        raise AttributeError(f"ui.console.{name} is not set on the module: console.put({name!r}, fn) puts a stand-in on the channel in use")

    def __delattr__(self, name):
        raise AttributeError(f"ui.console.{name} is not deleted from the module: console.put({name!r}, fn) puts a stand-in on the channel in use")


sys.modules[__name__].__class__ = _Sealed
