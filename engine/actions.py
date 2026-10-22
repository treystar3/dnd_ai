"""Every kind of action the interpreter may read a line into, declared once. The typed contract (llm/contracts.ActionIntent), the
dispatch in scenes/world.py (on_<kind>), the audit's list of targeted kinds (engine/intent_audit.py) and how long each takes are all
derived from this table, and data_check verifies at start-up that every kind here has a handler on the scene, that the interpreter's
instructions describe every kind and no other, and that nothing is declared twice. Adding an action is one line here, one on_<kind>
method, and one line of description in the interpreter's instructions; forgetting any of the three is caught before play.

Fields:
  minutes   how long the action takes when it does not say itself (None: the handler decides, or it takes no time)
  targeted  the action is aimed at a person who must be here (the audit checks the target against the scene)
  verbs     the player's words that mean this kind surely enough that a plan without it is suspect: the audit
            (engine/intent_audit.py) flags a line with such a verb and no step of its kind. A verb may belong to several kinds
            ("give" is give, show or sell), and a kind may claim a verb that usually means another ("sleep" is wait, or buying a room)
  words     looser words that still mark a line as an action rather than talk ("go", "look", "drink"). With the verbs they are the one
            list that tells the mentor's and a hire's intercepts (scenes/world.py, scenes/party_actions.py) that a line naming someone
            is not said to them. Too loose to audit: "go" is in half of what a player types
  note      what it is, for anyone reading this table"""
from __future__ import annotations

import re
from dataclasses import dataclass

from engine import clock


@dataclass(frozen=True)
class Action:
    kind: str
    note: str
    minutes: int | None = None
    targeted: bool = False
    verbs: tuple[str, ...] = ()
    words: tuple[str, ...] = ()


ACTIONS: tuple[Action, ...] = (
    Action("move", "go to a place, or to a person elsewhere", words=("go", "walk", "head", "travel", "ride", "set out", "set off")),
    Action("look", "look around, or at something here", clock.LOOK_MINUTES, words=("look", "examine", "inspect")),
    Action("search", "search this place", words=("search",)),
    Action("explore", "set out to find somewhere not on the map", words=("explore",)),
    Action("talk", "speak to someone here", clock.TALK_MINUTES, targeted=True),
    Action("leave_conversation", "end the conversation", 0),
    Action("buy", "buy a ware from someone here", targeted=True, verbs=("buy", "purchase", "sleep", "rest")),       # sleep, rest: a room
    Action("sell", "sell something to someone here", targeted=True, verbs=("sell", "give", "hand")),
    Action("ability", "use one of the character's abilities", verbs=("attack", "stab", "shoot", "kill", "cast", "heal")),
    Action("use", "use an item they carry", words=("use", "drink", "eat", "quaff")),
    Action("drop", "drop an item here", verbs=("drop", "discard")),
    Action("pick_up", "pick something up from the ground", words=("pick up", "loot")),
    Action("give", "give an item or coin to someone here", targeted=True, verbs=("give", "hand", "bribe")),
    Action("show", "show someone an item or key item", targeted=True, verbs=("give", "hand", "show")),
    Action("discard", "throw an item away for good", verbs=("discard", "drop")),
    Action("store", "put an item in the item box", words=("stow",)),
    Action("retrieve", "take an item out of the item box"),
    Action("equip", "wear or wield an item", verbs=("equip", "wield", "wear")),
    Action("forage", "forage for herbs and materials", verbs=("harvest", "forage")),
    Action("craft", "make something from materials", verbs=("craft", "forge")),
    Action("commission", "order gear from a crafter", targeted=True, verbs=("buy", "purchase", "craft", "forge")),
    Action("work", "take, do or finish paid work for someone", targeted=True),
    Action("harvest", "skin or butcher a carcass", verbs=("harvest", "skin", "butcher")),
    Action("join_guild", "pay the fee and sign the register", verbs=("buy", "purchase", "join", "register")),
    Action("board", "read or ask about the contract board", targeted=True, verbs=("buy", "join", "board")),
    Action("accept_quest", "take a contract or request", verbs=("join",)),
    Action("abandon_quest", "give a contract or request up", verbs=("abandon",)),
    Action("train", "train with a teacher", targeted=True, verbs=("train", "learn")),
    Action("learn_ability", "learn a taught ability", verbs=("train", "learn")),
    Action("delve", "go down into a dungeon", words=("delve", "descend")),
    Action("leave_dungeon", "leave the dungeon"),
    Action("wait", "wait, rest or sleep", verbs=("sleep", "rest", "wait")),
    Action("attack", "attack someone or something", targeted=True, verbs=("attack", "stab", "shoot", "kill"), words=("hit", "fight")),
    Action("release", "release a captive", verbs=("release",)),
    Action("hand_over", "hand a captive over", verbs=("arrest", "surrender")),
    Action("steal", "steal from someone here", 5, targeted=True, words=("steal", "rob")),      # the audit's theft words come from law.yaml
    Action("unlock", "pick or force a lock", targeted=True),
    Action("other", "anything else: narrated as an attempt", clock.OTHER_MINUTES, verbs=("bribe",)),
)

BY_KIND: dict[str, Action] = {a.kind: a for a in ACTIONS}
KINDS: tuple[str, ...] = tuple(a.kind for a in ACTIONS)
TARGETED: tuple[str, ...] = tuple(a.kind for a in ACTIONS if a.targeted)
TIME_COST: dict[str, int] = {a.kind: a.minutes for a in ACTIONS if a.minutes is not None}

VERB_KINDS: dict[str, tuple[str, ...]] = {}          # verb -> the kinds it may mean, from the rows above
for _a in ACTIONS:
    for _v in _a.verbs:
        VERB_KINDS[_v] = VERB_KINDS.get(_v, ()) + (_a.kind,)
ACTION_WORDS: frozenset[str] = frozenset(w for _a in ACTIONS for w in _a.verbs + _a.words)


def action_re(extra: tuple[str, ...] = ()) -> re.Pattern:
    """A pattern that matches any action word as a whole word (longest first, so "set out" wins over "out"). `extra` adds a caller's own
    words: the party's hire and dismiss, which scenes/party_actions.py reads itself and which are not action kinds."""
    words = sorted(set(ACTION_WORDS) | set(extra), key=len, reverse=True)
    return re.compile(r"\b(" + "|".join(re.escape(w) for w in words) + r")\b")


ACTION_RE: re.Pattern = action_re()


def problems(scene_class, interpreter_text: str) -> list[str]:
    """What does not agree: a kind with no on_<kind> on the scene, a kind the interpreter's instructions do not describe (or describe
    without declaring here), a kind declared twice."""
    out = []
    seen = set()
    for a in ACTIONS:
        if a.kind in seen:
            out.append(f"action '{a.kind}' is declared twice")
        seen.add(a.kind)
        if not hasattr(scene_class, f"on_{a.kind}"):
            out.append(f"action '{a.kind}' has no on_{a.kind} handler on the scene")
    import re
    block = interpreter_text.split("\nkind:\n", 1)[-1].split("\nchecks:", 1)[0]          # the kinds, not the checks listed after them
    described = set(re.findall(r"^  ([a-z_]+) +- ", block, re.M))
    for k in KINDS:
        if k not in described:
            out.append(f"action '{k}' is not described in the interpreter's instructions")
    for k in described - set(KINDS):
        out.append(f"the interpreter's instructions describe '{k}', which is not a declared action")
    return out
