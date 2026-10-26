"""The home page (f345): what the game shows when it starts, and when the player asks for the main menu.

Continue opens the game played last. Below it: Load lists every game, to load or to delete (storage/saves.py moves a deleted game
aside rather than erasing it); New game starts a character in a folder of its own; Settings is the window's own; Quit is asked
first. The window draws the page with buttons and sends back a key ("home:continue", "home:load:<save>", ...); the terminal prints
a menu and reads what is typed. Both come back through console.ask(), and both are read by choose() here, so the two can never
disagree about what a choice means."""
from __future__ import annotations

from datetime import datetime

import config
from core.version import VERSION
from storage import saves
from ui import console

PREFIX = "home:"


def _played(stamp: str) -> str:
    """'today at 14:05', 'yesterday at 09:30', or '12 Oct 2026'."""
    try:
        t = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return ""
    days = (datetime.now().date() - t.date()).days
    if days == 0:
        return f"today at {t:%H:%M}"
    if days == 1:
        return f"yesterday at {t:%H:%M}"
    return f"{t.day} {t:%b %Y}"


def describe(s: dict, world) -> dict:
    """A save's summary with the words the page shows: where the character is, the in-game day and season, when it was played."""
    from engine import clock, mapview
    out = dict(s)
    place = world.places.get(s.get("place", "")) if world else None
    if place is not None:
        top = world.places.get(mapview.top_of(world, place.id))
        out["where"] = place.name if top is None or top.id == place.id else f"{place.name}, {top.name}"
    else:
        out["where"] = "on the road" if s.get("place", "").startswith("road") else ""
    m = int(s.get("minutes") or 0)
    out["when"] = f"day {clock.day(m)}, {clock.season(m)}" if s.get("ready") else ""
    out["played_label"] = _played(s.get("played", ""))
    out["line"] = (f"{s['character']}, {s['class']}, level {s['level']}" if s.get("ready") else s.get("why", ""))
    return out


def page(world) -> dict:
    """Everything the home page shows."""
    listed = [describe(s, world) for s in saves.list_saves()]
    cont = saves.last()
    return {"title": config.GAME_TITLE, "subtitle": getattr(config, "GAME_SUBTITLE", ""), "version": VERSION,
            "continue": next((s for s in listed if cont and s["name"] == cont["name"]), None), "saves": listed}


def _terminal_menu(data: dict) -> None:
    """The home page as text (the window replaces this with its own page): Continue, then Load, New game and Quit."""
    console.out("\n" + "═" * 60)
    console.out(f"  {data['title']}" + (f"  -  {data['subtitle']}" if data.get("subtitle") else ""))
    console.out("═" * 60)
    c = data.get("continue")
    if c:
        console.out(f"  [Enter] Continue as {c['line']}" + (f", in {c['where']}" if c.get("where") else "") + (f" ({c['when']})" if c.get("when") else ""))
    if data["saves"]:
        console.out(f"  [l] Load a game ({len(data['saves'])} saved)")
    console.out("  [n] New game" if c else "  [Enter] New game")
    console.out("  [q] Quit")


def _terminal_games(data: dict) -> None:
    """Load: every game, numbered."""
    console.out("\n  Your games:")
    for i, s in enumerate(data["saves"], 1):
        bits = [s["line"]] + [x for x in (s.get("where"), s.get("when")) if x] + ([f"played {s['played_label']}"] if s.get("played_label") else [])
        console.out(f"   {i:>2}. " + " - ".join(bits))
    console.out("\n  Type a number to load that game, d and a number to delete one (it is moved aside, not erased), or Enter to go back.")


def parse(answer: str, data: dict, view: str = "menu") -> tuple[str, str]:
    """(kind, save name) for what came back: continue, new, load, delete (confirmed in the window), ask_delete (to confirm here),
    list (the terminal's Load), menu (back from it), quit (confirmed in the window), ask_quit (to confirm here), or bad."""
    a = (answer or "").strip()
    low = a.lower()
    listed = data["saves"]
    names = {s["name"] for s in listed}
    if low.startswith(PREFIX):
        rest = a[len(PREFIX):]
        kind, _, name = rest.partition(":")
        kind = kind.lower()
        if kind == "continue":
            return ("load", data["continue"]["name"]) if data.get("continue") else ("new", "")
        if kind in ("new", "quit"):
            return kind, ""
        if kind in ("load", "delete") and name in names:
            return kind, name
        return "bad", ""
    num = low[1:].strip() if low.startswith("d") else low
    if num.isdigit() and 1 <= int(num) <= len(listed):
        return ("ask_delete" if low.startswith("d") else "load"), listed[int(num) - 1]["name"]
    if view == "list":
        return ("menu", "") if low in ("", "b", "back") else ("bad", "")
    if low in ("", "c", "continue"):
        if data.get("continue"):
            return "load", data["continue"]["name"]
        return ("new", "") if not low else ("bad", "")     # nothing to continue: Enter begins the first game
    if low in ("l", "load"):
        return ("list", "") if listed else ("bad", "")
    if low in ("n", "new", "new game"):
        return "new", ""
    if low in ("q", "quit", "exit"):
        return "ask_quit", ""
    return "bad", ""


def choose(world) -> tuple[str, str]:
    """Show the home page until the player picks a game, a new one, or to quit. Deleting happens here and shows the page again."""
    view = "menu"                                   # the terminal's page: the menu, or Load's list (the window keeps its own)
    while True:
        data = page(world)
        if not console.home(data):                  # the window draws its own page; the terminal gets it as text
            (_terminal_games if view == "list" and data["saves"] else _terminal_menu)(data)
        kind, name = parse(console.ask(), data, view)
        listed = {s["name"]: s for s in data["saves"]}
        if kind in ("menu", "list"):
            view = kind
            continue
        if kind == "ask_quit":
            console.note("Quit the game? (y/n)")
            if console.ask().strip().lower() in ("y", "yes"):
                return "quit", ""
            continue
        if kind == "load" and not listed.get(name, {}).get("ready"):
            console.note(f"That game can't be opened: {listed.get(name, {}).get('why') or 'it could not be read'}.")
            continue
        if kind == "ask_delete":
            view = "list"
            console.note(f"Delete {listed[name]['line'] or name}? It is moved to the deleted folder inside saves, not erased. (y/n)")
            if console.ask().strip().lower() not in ("y", "yes"):
                continue
            kind = "delete"
        if kind == "delete":
            where = saves.delete(name)
            console.note(f"Deleted. The game was moved to {where}." if where else "That game was already gone.")
            continue
        if kind == "bad":
            console.note("Choose Continue, Load, New game, or Quit." if view == "menu" else "Type a number, d and a number, or Enter to go back.")
            continue
        return kind, name
