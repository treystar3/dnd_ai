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
  prompt    what the interpreter is told this kind is: the kinds block of its instructions (scenes/world_prompts.py INTERPRET_SYSTEM) is
            written from these, so it can never describe a kind nobody declared, or miss one
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
    prompt: str = ""


ACTIONS: tuple[Action, ...] = (
    Action("move", "go to a place, or to a person elsewhere", words=("go", "walk", "head", "travel", "ride", "set out", "set off"),
           prompt="""they want to go to one of the PLACES, or to a person listed under PEOPLE ELSEWHERE.
               Moving within the current place - upstairs, to their room, to a table, a corner, the bar,
               across the street - is look, not move. Going up to, approaching or walking over to someone
               in PEOPLE HERE is never move: it is part of talking to them."""),
    Action("explore", "set out to find somewhere not on the map", words=("explore",),
           prompt="""they set out to find somewhere NOT on the PLACES list: follow a stream or trail to see where it leads,
               look for a shortcut or a hidden way, hunt for a cave, ruin or spring, wander off the path.
               Put what they look for in seek. Naming a place from PLACES is move, never explore."""),
    Action("look", "look around, or at something here", clock.LOOK_MINUTES, words=("look", "examine", "inspect"),
           prompt="""they look around or take in their surroundings, or think aloud with no one to answer"""),
    Action("search", "search this place", words=("search",),
           prompt="""they search, hunt, track, explore, scout or look for creatures, game, enemies or signs of them"""),
    Action("talk", "speak to someone here", clock.TALK_MINUTES, targeted=True,
           prompt="""they speak to, ask, whisper to, greet, approach or look for a PERSON in PEOPLE HERE,
               or keep talking in the current conversation. Any spoken words count as talk."""),
    Action("leave_conversation", "end the conversation", 0,
           prompt="""they end the current conversation without going anywhere (a goodbye can include spoken words)"""),
    Action("buy", "buy a ware from someone here", targeted=True, verbs=("buy", "purchase", "sleep", "rest"),
           prompt="""they pay for, buy, rent, order or accept the price of something listed under FOR SALE.
               Handing someone money for something they offered ("I hand him the silver") is buy, not give."""),       # sleep, rest: a room
    Action("sell", "sell something to someone here", targeted=True, verbs=("sell", "give", "hand"),
           prompt="""they sell something from YOUR PACK to a person here who BUYS it"""),
    Action("ability", "use one of the character's abilities", verbs=("attack", "stab", "shoot", "kill", "cast", "heal"),
           prompt="""outside a fight, they use one of YOUR ABILITIES - only when they name it or plainly describe
               doing exactly what it does. Watching, noticing, studying or reading someone is look."""),
    Action("use", "use an item they carry", words=("use", "drink", "eat", "quaff"),
           prompt="""they drink, eat, apply or use a consumable or food from YOUR PACK"""),
    Action("drop", "drop an item here", verbs=("drop", "discard"),
           prompt="""they drop, leave or set down something from YOUR PACK"""),
    Action("pick_up", "pick something up from the ground", words=("pick up", "loot"),
           prompt="""they pick up or take something listed ON THE GROUND HERE"""),
    Action("give", "give an item or coin to someone here", targeted=True, verbs=("give", "hand", "bribe"),
           prompt="""they give or hand something from YOUR PACK or KEY ITEMS to a person here"""),
    Action("show", "show someone an item or key item", targeted=True, verbs=("give", "hand", "show"),
           prompt="""they show, present or display something (usually from KEY ITEMS) to a person here"""),
    Action("discard", "throw an item away for good", verbs=("discard", "drop"),
           prompt="""they throw away, get rid of, burn or destroy something from KEY ITEMS"""),
    Action("store", "put an item in the item box", words=("stow",),
           prompt="""they put something into their ITEM BOX (only if one is here)"""),
    Action("retrieve", "take an item out of the item box",
           prompt="""they take something out of their ITEM BOX (only if one is here)"""),
    Action("equip", "wear or wield an item", verbs=("equip", "wield", "wear"),
           prompt="""they equip, wield, wear, draw or put on gear from YOUR PACK"""),
    Action("forage", "forage for herbs and materials", verbs=("harvest", "forage"),
           prompt="""they gather, forage, pick or collect herbs or plants"""),
    Action("craft", "make something from materials", verbs=("craft", "forge"),
           prompt="""they make, brew, cook, forge, sew or craft something themselves - a RECIPE, or gear such as a
               jerkin, helm, spear or shield from materials in YOUR PACK"""),
    Action("work", "take, do or finish paid work for someone", targeted=True,
           prompt="""they do work or labor for or with a person here: help them, haul, load, carry, dig, chop,
               tend - including taking up a job that person offered"""),
    Action("harvest", "skin or butcher a carcass", verbs=("harvest", "skin", "butcher"),
           prompt="""they skin, butcher, gut or harvest the bodies of creatures they killed. "Skin it and harvest what I can"
               is ONE harvest, never a harvest plus an other"""),
    Action("join_guild", "pay the fee and sign the register", verbs=("buy", "purchase", "join", "register"),
           prompt="""they join, sign up for or pay to enter the adventurers' guild, or say they want or hope to join it
               or its register (not a question about how)"""),
    Action("board", "read or ask about the contract board", targeted=True, verbs=("buy", "join", "board"),
           prompt="""they read or look over the guild's contract board"""),
    Action("accept_quest", "take a contract or request", verbs=("join",),
           prompt="""they take a contract from the board (item = its number or name; "the delivery one", "I'll do this" and
               "I want to take this job" all count, with the CONTRACT BOARD below to pick from), or say yes to a request
               a person here just asked of them"""),
    Action("abandon_quest", "give a contract or request up", verbs=("abandon",),
           prompt="""they give up a contract or request they hold (item = which)"""),
    Action("train", "train with a teacher", targeted=True, verbs=("train", "learn"),
           prompt="""they ask for or pay for training: drills, lessons in a skill, or to be taught a new ability
               (item = what they want to train or learn, in their words)"""),
    Action("learn_ability", "learn a taught ability", verbs=("train", "learn"),
           prompt="""they choose one of the abilities an instructor just offered (item = its number or name)"""),
    Action("delve", "go down into a dungeon", words=("delve", "descend"),
           prompt="""at a dungeon: they go down, enter, press on, go deeper or continue to the next chamber"""),
    Action("leave_dungeon", "leave the dungeon",
           prompt="""in a dungeon: they turn back, climb out or leave"""),
    Action("commission", "order gear from a crafter", targeted=True, verbs=("buy", "purchase", "craft", "forge"),
           prompt="""they ask or pay a person here to make gear for them ("forge me a spear", "make me boots
               from these hides")"""),
    Action("wait", "wait, rest or sleep", verbs=("sleep", "rest", "wait"),
           prompt="""they wait, rest, linger, pass time or skip ahead"""),
    Action("attack", "attack someone or something", targeted=True, verbs=("attack", "stab", "shoot", "kill"), words=("hit", "fight"),
           prompt="""they attack a creature (in PEOPLE HERE with id wildlife) or start a fight. Killing, executing or
               finishing off a captive prisoner in PEOPLE HERE is attack, with that prisoner's id as target."""),
    Action("release", "release a captive", verbs=("release",),
           prompt="""they let a captive prisoner in PEOPLE HERE go free, spare them, or send them away unharmed - or
               release a tamed companion back into the wild"""),
    Action("hand_over", "hand a captive over", verbs=("arrest", "surrender"),
           prompt="""they hand a captive prisoner over to the watch / a guard / the authorities (target = the prisoner)"""),
    Action("steal", "steal from someone here", 5, targeted=True, words=("steal", "rob"),
           prompt="""they secretly take something that is not theirs: pick a pocket, lift or swipe an item from a stall, shelf,
               desk or person, slip something away unseen, or look through someone's things to take what they find.
               Item = what they take, in their words. Target = the person they take it from or whose it is, if any.
               Paying for something is buy, never steal. Asking for something is talk."""),      # the audit's theft words come from law.yaml
    Action("unlock", "pick or force a lock", targeted=True,
           prompt="""they open a lock that is not theirs to open: pick it, jimmy it, break into a locked room, chest or door, or open
               one with a key they hold. Item = what is locked, in their words ("the back room", "the strongbox").
               Target = the person it belongs to, if any. Opening an ordinary unlocked door is move or look, never unlock."""),
    Action("pray", "pray, or keep a small rite, at a temple or anywhere", words=("pray", "kneel", "worship"),
           prompt="""they pray, kneel, light a candle, give thanks or keep a small rite - at a temple or shrine, or anywhere.
               Coins into a tithe box are give, not pray."""),
    Action("gamble", "stake coin on dice or cards with someone here", targeted=True, verbs=("gamble", "wager", "bet"), words=("dice", "cards"),
           prompt="""they gamble: dice, cards or a wager with someone here. target: who they play with, if named. item: the stake
               as they named it ("2 silver"), else empty."""),
    Action("haggle", "bargain a price down before buying", targeted=True, verbs=("haggle", "bargain"),
           prompt="""they haggle, bargain or try to beat down the price of something listed under FOR SALE before buying it:
               ware and target as for buy. A plain purchase is buy."""),
    Action("other", "anything else: narrated as an attempt", clock.OTHER_MINUTES, verbs=("bribe",),
           prompt="""anything else they attempt"""),
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


def prompt_block() -> str:
    """The kinds block of the interpreter's instructions, one entry per action in this table, in the exact layout actions.problems
    reads back: two spaces, the kind in a 19-wide column, a dash, then the text; continuation lines under the text."""
    out = []
    for a in ACTIONS:
        lines = [l.strip() for l in a.prompt.strip().splitlines() if l.strip()] or [a.note]
        out.append(f"  {a.kind:<19}- {lines[0]}")
        out.extend(" " * 23 + l for l in lines[1:])
    return "\n".join(out)


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
