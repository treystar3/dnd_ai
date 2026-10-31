"""The bridge between the game and the window.

The game keeps printing and asking exactly as it does in the terminal. In GUI mode this module swaps the few console hooks
(ask, scope, status_block) and sys.stdout for versions that turn everything into small events, kept in a log the page reads
over a one-way stream. Typed lines come back through a queue that console.ask() waits on, so the engine never knows the difference.

Events (all dicts with "k"):  text{pane,kind,text}  echo{text}  side_begin{cmd}  side_end  status{...}  prompt{main}  busy{on,text}  panel{name,data}  combat{data}  combat_end
                              ended  fatal{text}
"""

import contextlib
import queue
import sys
import threading

from ui import console

LOG_CAP = 6000
VIEWS = {"system", "sys", "stats", "character", "exits", "where", "places", "map", "party", "journal", "j", "inventory", "inv", "i",
         "board", "contracts", "standing", "rumors", "dungeon", "floors", "quests", "quest", "jobs", "arc", "story",
         "trail", "clues", "home", "house", "property", "homes", "shop", "store", "wares", "buy", "stash", "box",
         "itembox", "gear", "equipment", "worn", "help", "h", "?", "world", "pulse", "book", "spellbook", "loadout"}
DEFAULT_PIN = "#character"
PINNABLE = {"#character", "#stats", "#inventory", "#gear", "#journal", "#quests", "#map", "#places", "#exits", "#party", "#standing", "#arc",
            "#dungeon", "#home", "#shop", "#stash", "#board", "#help", "#pulse", "#book"}     # read-only views: a pin runs again after every turn
HIDDEN = ("#shopbuy", "#shopsell", "#gearequip", "#gearunequip", "#attradd", "#compname", "#boardaccept", "#boardabandon", "#boardrequest", "#boardjoin", "#boardhire", "#goto", "#mapgo",
          "#useitem", "#correct", "#questabandon", "home:")      # the panes' buttons and the home page's: run like commands, never echoed
MENU = ("#menu", "#mainmenu", "#saves")     # back to the main menu: taken at the game loop, and at a prompt that allows it (ask(menu=True))
WRAP_WIDTH = 2000


def is_view(text: str) -> bool:
    return text.startswith("#") and text[1:].strip().lower() in VIEWS


class Closed(SystemExit):
    """Raised inside the game when the window is gone and a sub-prompt would otherwise wait forever."""


class _Out:
    encoding = "utf-8"
    errors = "replace"

    def __init__(self, bridge):
        self.b = bridge

    def write(self, s):
        self.b.write(str(s))
        return len(s)

    def flush(self):
        self.b.flush_text()

    def isatty(self):
        return False


class Bridge:
    def __init__(self):
        self.cv = threading.Condition()
        self.log: list[tuple[int, dict]] = []
        self.next_id = 1
        self.inbox: queue.Queue = queue.Queue()
        self.route = "main"
        self.cur_kind = "plain"
        self.buf = ""
        self.update_info: dict | None = None
        self.pinned: str | None = DEFAULT_PIN
        self.dirty = True            # a turn has passed since the pinned view was last refreshed
        self.in_combat = False       # the combat pane owns the side pane until the fight ends
        self.waiting = False
        self.at_main = False
        self.at_menu = False         # the prompt waiting now may be left for the main menu though it is not the game loop
        self.closed = False
        self.failed = False
        self.finished = threading.Event()
        self.saved = {}
        self.depth = 0
        self.lock = threading.RLock()

    # ---------- events ----------
    def emit(self, **ev) -> None:
        with self.cv:
            self.log.append((self.next_id, ev))
            self.next_id += 1
            if len(self.log) > LOG_CAP:
                del self.log[:len(self.log) - LOG_CAP]
            self.cv.notify_all()

    def since(self, last: int, timeout: float = 15.0) -> list[tuple[int, dict]]:
        with self.cv:
            if not any(i > last for i, _ in self.log[-1:]) and not self.closed:
                self.cv.wait(timeout)
            if not self.log or self.log[-1][0] <= last:
                return []
            first = self.log[0][0]
            return self.log[max(0, last + 1 - first):]

    # ---------- output ----------
    def write(self, s: str) -> None:
        with self.lock:
            self.buf += s
            if "\n" in self.buf:
                head, _, tail = self.buf.rpartition("\n")
                self.buf = tail
                self.emit(k="text", pane=self.route, kind=self.cur_kind, text=head + "\n")

    def flush_text(self) -> None:
        with self.lock:
            if self.buf:
                text, self.buf = self.buf, ""
                self.emit(k="text", pane=self.route, kind=self.cur_kind, text=text)

    @contextlib.contextmanager
    def kind(self, name: str):
        self.flush_text()
        before, self.cur_kind = self.cur_kind, name
        try:
            yield
        finally:
            self.flush_text()
            self.cur_kind = before

    def combat_state(self, data) -> bool:
        """The fight as data for the combat pane; None says the fight is over."""
        self.in_combat = data is not None
        if data is None:
            self.emit(k="combat_end")
        else:
            self.emit(k="combat", data=data)
        return True

    def update_found(self, info: dict) -> None:
        self.update_info = info
        self.emit(k="update", data=info)

    def setup(self, data: dict) -> None:
        self.emit(k="setup", data=data)

    def setup_progress(self, frac: float, text: str) -> None:
        with self.cv:
            if self.log and self.log[-1][1].get("k") == "setup_progress":
                self.log.pop()                       # only the latest figure matters: do not fill the log with them
        self.emit(k="setup_progress", frac=round(frac, 3), text=text)

    def setup_done(self) -> None:
        self.emit(k="setup_end")

    def home(self, data: dict) -> bool:
        """(f345) The home page, drawn by the page itself (web/app.js showHome)."""
        self.emit(k="home", data=data)
        return True

    def creation(self, data: dict) -> bool:
        """(f388) A step of character creation, drawn by the page itself (web/app.js showCreation)."""
        self.flush_text()
        self.emit(k="creation", data=data)
        return True

    def creation_done(self) -> None:
        self.flush_text()
        self.emit(k="creation_end")

    def home_done(self) -> None:
        """A game is opening: the page hides the home page and clears the story of whatever was played before; the pinned view runs
        again at the first prompt, for the new character."""
        self.emit(k="home_end")
        self.dirty = True

    def panel(self, name: str, data: dict) -> bool:
        """Structured data for the side pane (the shop). Only meaningful while a view is routed to the side."""
        if self.route != "side":
            return False
        self.emit(k="panel", name=name, data=data)
        return True

    @contextlib.contextmanager
    def scope(self, command: str):
        if not is_view(command):
            yield
            return
        self.flush_text()
        self.route = "side"
        self.emit(k="side_begin", cmd="#" + command[1:].strip().lower())
        try:
            yield
        finally:
            self.flush_text()
            self.route = "main"
            self.emit(k="side_end")

    def status_block(self, when, weather, place_line, spot_line, vitals, level, points, coins, xp=(0, 0), needs=None) -> None:
        from engine import money
        import config
        self.emit(k="status", debug=bool(config.DEBUG), when=when, weather=weather, place=place_line, spot=spot_line,
                  vitals={k: [round(v[0]), v[1]] for k, v in vitals.items()}, level=level, points=points,
                  coins=money.fmt(coins), xp=list(xp), needs=needs or {})

    # ---------- input ----------
    def ask(self, main: bool = False, menu: bool = False) -> str:
        self.flush_text()
        if main and self.pinned in PINNABLE and self.dirty and not self.closed and not self.in_combat:
            self.dirty = False
            return self.pinned           # the game's own loop runs it; scope() sends it to the side pane
        if self.closed:
            if main:
                return "quit"
            raise Closed()
        self.waiting, self.at_main, self.at_menu = True, main, menu
        self.emit(k="prompt", main=main, menu=menu)      # menu: the Main menu button works here though the others wait
        text = self.inbox.get()
        self.waiting = False
        if text is None:
            if main:
                return "quit"
            raise Closed()
        text = text.strip()
        if not is_view(text) and not text.lower().startswith(HIDDEN):
            self.emit(k="echo", text=text)
        if not text.startswith("#"):
            self.dirty = True
        return text

    def submit(self, text: str) -> bool:
        if not self.waiting:
            return False
        self.waiting = False
        self.inbox.put(text)
        return True

    def close(self) -> None:
        self.closed = True
        self.inbox.put(None)
        with self.cv:
            self.cv.notify_all()

    # ---------- wiring ----------
    def busy(self, on: bool) -> None:
        self.emit(k="busy", on=on, text=getattr(self, "busy_label", "") if on else "")
        if not on:
            self.busy_label = ""

    def busy_text(self, message: str) -> None:
        """(f423) The waiting indicator's words for the wait that follows."""
        self.busy_label = message

    def install(self) -> None:
        from llm import gateway
        self.saved = {"stdout": sys.stdout, "ask": console.ask, "scope": console.scope,
                      "status_block": console.status_block, "kind": console.kind, "panel": console.panel, "busy_text": console.busy_text, "combat_state": console.combat_state, "setup": console.setup, "setup_progress": console.setup_progress, "setup_done": console.setup_done, "home": console.home, "home_done": console.home_done, "creation": console.creation, "creation_done": console.creation_done, "damage_tags": console.damage_tags, "width": console.WIDTH, "chat": gateway._client.chat}
        real_chat = gateway._client.chat

        def chat(*a, **kw):
            with self.lock:
                self.depth += 1
                if self.depth == 1:
                    self.busy(True)
            try:
                return real_chat(*a, **kw)
            finally:
                with self.lock:
                    self.depth -= 1
                    if self.depth == 0:
                        self.busy(False)

        gateway._client.chat = chat
        sys.stdout = _Out(self)
        console.ask, console.scope, console.status_block, console.kind = self.ask, self.scope, self.status_block, self.kind
        console.busy_text = self.busy_text
        console.panel = self.panel
        console.setup, console.setup_progress, console.setup_done = self.setup, self.setup_progress, self.setup_done
        console.home, console.home_done = self.home, self.home_done
        console.creation, console.creation_done = self.creation, self.creation_done
        console.combat_state, console.damage_tags = self.combat_state, True
        console.WIDTH = WRAP_WIDTH      # the page wraps text to its own width, so the game must not wrap it first

    def uninstall(self) -> None:
        from llm import gateway
        s = self.saved
        if not s:
            return
        self.flush_text()
        sys.stdout = s["stdout"]
        console.ask, console.scope, console.status_block, console.kind = s["ask"], s["scope"], s["status_block"], s["kind"]
        console.busy_text = s["busy_text"]
        console.panel = s["panel"]
        console.setup, console.setup_progress, console.setup_done = s["setup"], s["setup_progress"], s["setup_done"]
        console.home, console.home_done = s["home"], s["home_done"]
        console.creation, console.creation_done = s["creation"], s["creation_done"]
        console.combat_state, console.damage_tags = s["combat_state"], s["damage_tags"]
        console.WIDTH = s["width"]
        gateway._client.chat = s["chat"]
        self.saved = {}
