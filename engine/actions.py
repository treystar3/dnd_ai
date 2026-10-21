"""Every kind of action the interpreter may read a line into, declared once. The typed contract (llm/contracts.ActionIntent), the
dispatch in scenes/world.py (on_<kind>), the audit's list of targeted kinds (engine/intent_audit.py) and how long each takes are all
derived from this table, and data_check verifies at start-up that every kind here has a handler on the scene, that the interpreter's
instructions describe every kind and no other, and that nothing is declared twice. Adding an action is one line here, one on_<kind>
method, and one line of description in the interpreter's instructions; forgetting any of the three is caught before play.

Fields:
  minutes   how long the action takes when it does not say itself (None: the handler decides, or it takes no time)
  targeted  the action is aimed at a person who must be here (the audit checks the target against the scene)
  note      what it is, for anyone reading this table"""
from __future__ import annotations

from dataclasses import dataclass

from engine import clock


@dataclass(frozen=True)
class Action:
    kind: str
    note: str
    minutes: int | None = None
    targeted: bool = False


ACTIONS: tuple[Action, ...] = (
    Action("move", "go to a place, or to a person elsewhere"),
    Action("look", "look around, or at something here", clock.LOOK_MINUTES),
    Action("search", "search this place"),
    Action("explore", "set out to find somewhere not on the map"),
    Action("talk", "speak to someone here", clock.TALK_MINUTES, targeted=True),
    Action("leave_conversation", "end the conversation", 0),
    Action("buy", "buy a ware from someone here", targeted=True),
    Action("sell", "sell something to someone here", targeted=True),
    Action("ability", "use one of the character's abilities"),
    Action("use", "use an item they carry"),
    Action("drop", "drop an item here"),
    Action("pick_up", "pick something up from the ground"),
    Action("give", "give an item or coin to someone here", targeted=True),
    Action("show", "show someone an item or key item", targeted=True),
    Action("discard", "throw an item away for good"),
    Action("store", "put an item in the item box"),
    Action("retrieve", "take an item out of the item box"),
    Action("equip", "wear or wield an item"),
    Action("forage", "forage for herbs and materials"),
    Action("craft", "make something from materials"),
    Action("commission", "order gear from a crafter", targeted=True),
    Action("work", "take, do or finish paid work for someone", targeted=True),
    Action("harvest", "skin or butcher a carcass"),
    Action("join_guild", "pay the fee and sign the register"),
    Action("board", "read or ask about the contract board", targeted=True),
    Action("accept_quest", "take a contract or request"),
    Action("abandon_quest", "give a contract or request up"),
    Action("train", "train with a teacher", targeted=True),
    Action("learn_ability", "learn a taught ability"),
    Action("delve", "go down into a dungeon"),
    Action("leave_dungeon", "leave the dungeon"),
    Action("wait", "wait, rest or sleep"),
    Action("attack", "attack someone or something", targeted=True),
    Action("release", "release a captive"),
    Action("hand_over", "hand a captive over"),
    Action("steal", "steal from someone here", 5, targeted=True),
    Action("unlock", "pick or force a lock", targeted=True),
    Action("other", "anything else: narrated as an attempt", clock.OTHER_MINUTES),
)

BY_KIND: dict[str, Action] = {a.kind: a for a in ACTIONS}
KINDS: tuple[str, ...] = tuple(a.kind for a in ACTIONS)
TARGETED: tuple[str, ...] = tuple(a.kind for a in ACTIONS if a.targeted)
TIME_COST: dict[str, int] = {a.kind: a.minutes for a in ACTIONS if a.minutes is not None}


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
