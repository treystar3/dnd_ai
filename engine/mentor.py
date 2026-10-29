"""The mentor: a travelling adventurer who meets the new player in Parth, sends them into the guild, and takes them on a first
contract, a scripted wolf hunt in the Greywood that a troll interrupts.

The engine owns every part of it: when she appears, the order of the steps, the fight and its safety net, and the figures of the
troll's death (worked out with the same damage code as any fight). The words the player reads are fixed in data/world/mentor.yaml.
Nothing the model says can add a step or change what is true.

Stages, in order: "" -> invite (waiting for the player to join the guild) -> board (waiting for them to take the hunt from the board)
-> hunt -> done."""
from __future__ import annotations

import functools
import random
import re
import zlib
from pathlib import Path

import yaml

import config

from engine import combat, money, quests

M = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "world" / "mentor.yaml").read_text(encoding="utf-8"))
NAME = M["name"]
G = quests.G


def state(player) -> dict:
    return player.mentor


def stage(player) -> str:
    return player.mentor.get("stage", "")


def set_stage(player, name: str) -> None:
    player.mentor["stage"] = name


def may_appear(player, minutes: int, location: str, parent: str | None) -> bool:
    """Is it time for her to come over? Only in Parth, only for someone still new, only once."""
    if stage(player) or player.mentor.get("never"):
        return False
    if player.character.level > M["gate"]["max_level"] or player.guild_done:
        return False
    if M["gate"]["place"] not in (location, parent):
        return False
    since = player.mentor.setdefault("since", minutes)
    return minutes >= since + M["gate"]["wait_minutes"]


def rank_lines() -> list[str]:
    """What it takes to climb the ranks, straight from the guild's rules so it can never drift."""
    out = []
    for letter, r in G["ranks"].items():
        req = r.get("requires")
        if req:
            out.append(f"{letter}: level {req['level']} and {req['completed']} contracts")
    return out


def rank_table() -> list[tuple[str, int, int]]:
    """(letter, level, contracts) for every rank that must be earned, from the guild's rules."""
    return [(letter, int(r["requires"]["level"]), int(r["requires"]["completed"])) for letter, r in G["ranks"].items() if r.get("requires")]


def check_ranks(text: str, table: list[tuple[str, int, int]]) -> str:
    """Why a speech about the ranks has them wrong, or '': every rank is named, and the level and contract count that follow its letter
    (within a few words) are the guild's own. Said her own way, but never wrong."""
    words = re.findall(r"[A-Za-z0-9#']+", text)
    for letter, level, contracts in table:
        spots = [i for i, w in enumerate(words) if w == letter]
        if not spots:
            return f"you left out rank {letter}: it needs level {level} and {contracts} contracts"
        ok = False
        for i in spots:
            window = {w.lower() for w in words[i + 1:i + 14]}
            nums = {str(WORD_NUM[w]) if w in WORD_NUM else w for w in window}
            if str(level) in nums and str(contracts) in nums:
                ok = True
                break
        if not ok:
            return f"rank {letter} is wrong or unclear: it needs level {level} and {contracts} contracts, said together right after the letter"
    return ""


def topic_text(topic: str) -> list[str]:
    if topic == "ranks":
        return [f"{M['approach']['topic_ranks_intro']}\n" + "; ".join(rank_lines()) + ".", M["approach"]["topic_ranks_outro"]]
    if topic == "board":
        return [M["approach"]["topic_board"].format(active=G["base_active"])]
    if topic == "joining":
        return [M["approach"]["topic_joining"].format(fee=money.words(G["joining_fee"]))]
    return []


def pick_topic(text: str) -> str:
    """Which of the three guild subjects a line asks about, so the exact answer is given; '' when it is about something else."""
    from llm import embed
    if len((text or "").split()) >= 2:
        sims = embed.whole(text, [TOPIC_ABOUT[t] for t in ("ranks", "board", "joining")])
        if sims is not None:
            best = max(range(3), key=lambda i: sims[i])
            return ("ranks", "board", "joining")[best] if sims[best] >= config.SIM_TOPIC + 0.05 else ""
    words = set(w.strip(".,!?'\"").lower() for w in (text or "").split())
    for topic, keys in M["approach"]["topic_words"].items():
        if words & set(keys):
            return topic
    return ""


def is_question(text: str) -> bool:
    """Is this line asking her something, rather than nodding along or saying what they do next?"""
    low = (text or "").strip().lower()
    return "?" in low or low.startswith(("how", "what", "where", "why", "when", "who", "which", "can ", "could ", "do ", "does ", "did ", "is ", "are ",
                                         "will ", "would ", "should ", "tell me", "explain"))


def wants_to_go_on(text: str) -> bool:
    """Plainly done: nothing said, 'go on', or a word or two of assent. Anything longer is read by the model (MentorReply.moves_on)."""
    low = (text or "").strip().lower()
    words = set(w.strip(".,!?'\"") for w in low.split())
    return not low or "go on" in low or (len(words) <= 3 and bool(words & {"continue", "next", "done", "ready", "enough", "no", "nothing", "thanks", "ok", "okay", "skip", "go"}))


def make_contract(now: int) -> dict:
    """The first contract: three wolves in the Greywood, no time limit, so it is still there if the player has to try again."""
    H = M["hunt"]
    title = H["title"].format(name=NAME)
    q = quests._quest("hunt", "F", title, now, place=H["place"], creature=H["creature"], count=H["count"])
    q["deadline"] = None
    q["mentor"] = True
    return q


def has_contract(player) -> bool:
    return any(q.get("mentor") for q in player.quests)


TUTORIAL_STAGES = ("invite", "sign", "board", "hunt")


def tutorial_on(player) -> bool:
    """While she is teaching, the guild's board shows only her hunt, and the hunt cannot be put down."""
    return stage(player) in TUTORIAL_STAGES


def tutorial_board(player, minutes: int) -> list[dict]:
    """The only posting on the board during the lesson: the wolf hunt, until the player has taken it."""
    if has_contract(player):
        return []
    post = player.mentor.get("posting")
    if not post:
        post = player.mentor["posting"] = make_contract(minutes)
    return [post]


def at(section: dict, key: str, ptype: str) -> str:
    """A line of narration that depends on where the player stands: at a table (an inn), in the guild hall, in a temple, or out in the open."""
    for suffix in ({"inn": "", "guild": "_guild", "temple": "_temple"}.get(ptype, "_open"), "_open", ""):
        if section.get(key + suffix):
            return section[key + suffix]
    return section[key]


def combat_facts() -> str:
    """How hitting works, from the combat rules themselves, so she can teach it without ever inventing a number."""
    r = combat.RULES
    h = r["hit"]
    st = r["statuses"]
    return (f"HIT CHANCE: against an enemy of equal footing an attack lands about {h['base']} times in 100. It rises with the attribute your weapon "
            f"draws on (it is listed on your character sheet) and falls with the enemy's Dexterity. Gear and passives that add accuracy raise it; "
            f"anything that adds evasion to the enemy lowers it. Being blinded costs {-st['blinded']['accuracy']} points of accuracy, being "
            f"frightened or slowed {-st['frightened']['accuracy']}. Fighting from higher ground than the enemy adds {r['elevated_accuracy']}. A bow "
            f"loses {h['point_blank']} points against an enemy already on top of you, so step back first. It is never below {h['min']} or above "
            f"{h['max']}. The last {h['graze_band']} points under it are grazes, which only do half damage. To land more: raise the weapon's "
            f"attribute when you level, wear gear that adds accuracy, choose passives that add it, and fight from the high ground.")


def status_facts() -> str:
    """What each condition in a fight does, from the combat rules, so she can explain 'burning' or 'befuddled' without inventing anything."""
    st = combat.RULES["statuses"]
    pct = lambda k, f: st[k][f]
    return ("CONDITIONS IN A FIGHT (each lasts only a few rounds): "
            f"burning: an ignite - half the blow that set it, burned over {combat.RULES['ignite']['rounds']} turns; only the strongest burn counts. "
            f"bleeding: an open wound, sized by the blow that made it; it does nothing by itself, but every weapon blow it takes after that, from anyone, makes it bleed again, armor or not. Only the biggest wound counts. It closes after {combat.RULES['bleed']['rounds']} turns, or when healed or bandaged; the dead and the bloodless cannot bleed. "
            f"poisoned: every dose is a stack that hurts each turn, and each new dose keeps all of them going for {combat.RULES['poison']['rounds']} more turns. "
            f"slowed: {-pct('slowed', 'evasion')} points harder to dodge with and {-pct('slowed', 'accuracy')} points worse at hitting. "
            f"prone: knocked down, it loses its next turn getting up, and is {-pct('prone', 'evasion')} points easier to hit. "
            f"stunned: it loses its next turn. frightened: {-pct('frightened', 'accuracy')} points worse at hitting, and an afraid enemy hangs back instead of closing in. "
            f"blinded: {-pct('blinded', 'accuracy')} points worse at hitting. weakened: it hits {-pct('weakened', 'power')}% softer. "
            f"exposed: its protection is {-pct('exposed', 'protection')}% lower. marked: it takes {pct('marked', 'taken')}% more damage. "
            f"befuddled: its next attack goes at a random fighter, friend or foe. grappled: held fast, {-pct('grappled', 'evasion')} points easier to hit.")


@functools.lru_cache(maxsize=1)
def _world():
    from world.loader import load_world
    return load_world()


BUILDS = ("melee", "ranged", "caster", "support")


def build_of(character) -> str:
    """How this player fights, for the wording of her lessons: melee, ranged, caster or support."""
    from core.models import Archetype
    from engine import items
    arch = getattr(character, "archetype", None)
    if arch == Archetype.MAGE:
        return "caster"
    if arch == Archetype.SUPPORT:
        return "support"
    weapon = (character.equipment or {}).get("main_hand")
    try:
        if weapon and items.base_of(weapon).reach == "ranged":
            return "ranged"
    except Exception:
        pass
    return "melee"


def empty_handed(character) -> bool:
    """(f385) Nothing in their hands to draw: no weapon, or wraps on their fists."""
    from engine import items
    weapon = (character.equipment or {}).get("main_hand")
    try:
        return weapon is None or "unarmed" in (items.base_of(weapon).tags or [])
    except Exception:
        return weapon is None


def line(player, key: str, seed=0) -> str:
    """One of the phrasings of a lesson, for this build. The same advice each time, said a little differently on a retry."""
    L = M["lessons"][key]
    build = build_of(player.character)
    if build == "melee" and isinstance(L, dict) and L.get("unarmed") and empty_handed(player.character):
        build = "unarmed"                                   # (f385) "Draw. Now." to someone with nothing to draw
    options = L[build] if isinstance(L, dict) else L
    said = player.mentor.setdefault("said", {})
    n = said.get(key, 0)
    said[key] = n + 1
    return options[(n + zlib.crc32(f"{seed}:{key}".encode())) % len(options)]


def text(x) -> str:
    """A string, or the first of a list of them (for one-line entries written as a list)."""
    return x if isinstance(x, str) else x[0]


def line_from(player, options: list[str]) -> str:
    """One of a few phrasings, rotating so a repeat is not word for word."""
    said = player.mentor.setdefault("said", {})
    n = said.get("_from", 0)
    said["_from"] = n + 1
    return options[n % len(options)]


YES_WORDS = {"yes", "yeah", "yep", "yup", "sure", "certain", "understand", "know", "do", "ok", "okay", "aye", "absolutely", "definitely", "totally"}
NO_WORDS = {"no", "nope", "nah", "not", "dont", "don't", "unsure", "explain", "teach", "show", "tell", "learn", "little", "bit", "help", "maybe", "unclear"}


def says_yes(text: str) -> bool:
    """Is this a yes? Any doubt at all ('not really', 'sort of', 'I don't know') counts as no, so the walkthrough is the safe default."""
    low = (text or "").lower().replace("n't", " not")
    words = {w.strip(".,!?'\"*") for w in low.split()}
    return bool(words & YES_WORDS) and not (words & NO_WORDS) and "sort of" not in low and "kind of" not in low


_STOP = {"the", "and", "his", "her", "with", "small", "tall", "old", "young", "big", "little"}


def addresses(text: str, npc) -> bool:
    """Does the player's line name this person - their name, their role or a word of how they are described?"""
    low = (text or "").lower()
    words = set()
    for src in (npc.name, npc.epithet or "", npc.role.replace("_", " ")):
        words |= {w for w in src.lower().replace("-", " ").replace("'", " ").split() if len(w) > 2 and w not in _STOP}
    return any(w in low for w in words)


def named(text: str) -> bool:
    """Does the player's line call her by name?"""
    return NAME.split()[0].lower() in (text or "").lower()


TOPIC_WORDS = {
    "ranks": ["rank", "ranks", "promote", "promotion", "promoted", "letter", "letters", "climb", "rise"],
    "board": ["board", "contract", "contracts", "quest", "quests", "job", "jobs", "bounty", "posting"],
    "joining": ["join", "joining", "sign", "signed", "fee", "register", "clerk", "badge", "member"],
    "combat": ["hit", "miss", "missed", "chance", "accuracy", "aim", "crit", "critical", "dodge", "evasion", "armor", "armour", "ward", "damage", "attack", "fight", "fighting", "strike"],
    "status": ["burning", "burn", "bleeding", "bleed", "stunned", "stun", "slowed", "poisoned", "poison", "befuddled", "frozen", "chilled", "weakened", "condition", "conditions", "effect", "effects"],
    "commands": ["type", "command", "commands", "button", "pane", "how do i", "what do i", "how to", "#"],
}


TOPIC_ABOUT = {
    "ranks": "a question about the adventurers' guild ranks, what each rank needs, and how to be promoted to a higher rank",
    "board": "a question about the guild's contract board, taking contracts and jobs, and how many contracts one may hold",
    "joining": "a question about joining the guild, signing the register with the clerk, the joining fee and the guild badge",
    "combat": "a question about fighting: hitting and missing, hit chance, aiming, critical hits, dodging, armour, ward and damage",
    "status": "a question about conditions in a fight, such as burning, bleeding, poison, being stunned, slowed or frozen",
    "commands": "a question about how to do something: what to type or say, which command or button to use",
}


def topics_in(text: str) -> set[str]:
    """Which of her subjects a line touches, so only those are given in full: by meaning when the helper model is there, else by words."""
    from llm import embed
    if text and len(text.split()) >= 2:
        names = list(TOPIC_ABOUT)
        sims = embed.whole(text, [TOPIC_ABOUT[t] for t in names])
        if sims is not None:
            top = max(sims)
            return {n for n, v in zip(names, sims) if v >= config.SIM_TOPIC and v >= top - 0.05}
    low = (text or "").lower()
    words = set(re.findall(r"[a-z#]+", low))
    out = set()
    for topic, keys in TOPIC_WORDS.items():
        if any((" " in k and k in low) or (k in words) for k in keys):
            out.add(topic)
    return out


def facts(player, where: str, about: str = "", objective: bool = False) -> str:
    """The fact sheet for her replies: who she is, where things stand, how she feels about the player, and a compact index of what she knows.
    Only the subjects `about` touches (what the player said, or the lines she is about to say) are given in full, so a personal question is
    not buried under the hit-chance table."""
    A = M["approach"]
    st = stage(player)
    S_ = M["chat"]["stages"].get(st)
    if S_:                                              # what she is waiting for comes in only when the talk is about it, or in a beat of hers
        wanted = objective or wants_objective(about)
        now = S_["state"] + (" " + S_["objective"] if wanted else "")
    else:
        now = {"hunt": "You are travelling with the player on their first contract: three wolves in the Greywood, no time limit.",
               "harvest": M["chat"]["harvest_state"] if player.mentor.get("troll_done") else M["chat"]["skin_state"]}.get(st, "")
    if st in ("hunt", "harvest") and player.mentor.get("troll"):
        now = M["chat"]["troll_state"]
    elif st == "hunt" and player.mentor.get("found"):
        now = "You are in the Greywood fighting the wolves alongside the player. Wolves cannot be run from or talked to."
    elif st == "hunt" and player.mentor.get("briefed"):
        now = "You are in the Greywood with the player. You have just told them to search for the wolves."
    elif st == "hunt" and where == M["hunt"]["place"]:
        now = "You have just reached the Greywood with the player."
    c = player.character
    weapon = (c.equipment or {}).get("main_hand")
    safe = "" if st in ("hunt", "harvest") else "HOW THINGS STAND: Parth is a guarded town and nothing threatens here right now; you have no reason to put the player on guard unless something happens.\n"
    want = topics_in(about) if about else set()
    full = {
        "ranks": f"GUILD RANKS: F at the bottom to S at the top; everyone starts at F. To rise you need a character level and a number of finished contracts: {'; '.join(rank_lines())}.\nGUILD: {A['topic_ranks_outro']}",
        "board": f"BOARD: {A['topic_board'].format(active=G['base_active'])}",
        "joining": f"JOINING: {A['topic_joining'].format(fee=money.words(G['joining_fee']))}",
        "combat": combat_facts(),
        "status": status_facts(),
        "commands": "COMMANDS:\n" + "\n".join(f"  - {x}" for x in M["chat"]["commands"]),
    }
    index = ("YOU KNOW EXACTLY, and are given in full only when asked: the ranks, the board, joining, how a fight's hits work, the conditions, "
             "the commands. Asked about one not given here, say you will explain it properly if they ask plainly; never guess a figure.")
    told_you = [t for who, t in player.mentor.get("chat", []) if who == "Player" and len(t.split()) >= 5][-3:]
    lines = [f"STATE: {now}",                                   # (f315) where she is comes with her truth view, like everyone's
             f"ATTITUDE: {M['chat']['attitude'].get(st if st in M['chat']['attitude'] else 'default')}",
             f"THE PLAYER: level {c.level}, fights as {build_of(c)}" + (f", carrying a {weapon.name}" if weapon else ", unarmed"),
             "YOU: you hold the A rank, the second highest the guild gives.",
             index]
    from engine import relevance
    if about and relevance.pick(about, [M["chat"]["motivation_about"]], 1):      # why she helps: when that is what the talk is about
        lines.append("MOTIVATION (yours, private): you have seen too many newcomers hurt or killed over things nobody bothered to show them, and "
                     "helping the capable ones has become a habit you do not make a sentimental thing of. If asked why you help, put it your own way, "
                     "and wave off thanks.")
    if about:
        mine = about_her(player, about)
        if mine:
            lines.append("ABOUT YOU (true; tell it only if the player asks about it or about you, never unprompted): " + " ".join(mine))
    if told_you:
        lines.append("THINGS THEY HAVE TOLD YOU (you remember details; bring one back when it fits, unprompted): " + " | ".join(told_you))
    lines += [full[t] for t in ("ranks", "board", "joining", "combat", "status", "commands") if t in want]
    return safe + "\n".join(lines)


def her_records(player) -> list[dict]:
    """What is true of her, tagged for the scene builder (engine/context.py): her authored details and what she has said in play."""
    from engine import canon, quirks
    return [{"kind": "detail", "text": d} for d in quirks.Q["maren"]["details"]] + canon.records(player.mentor)


GIVEN = ["I am an A-rank adventurer of the guild.", "I am helping a newcomer through their first contract."]


def about_her(player, about: str) -> list[str]:
    """The records this conversation carries, chosen the same way as for every other speaker."""
    import random as _r
    from engine import context
    chosen, _ = context.select(player.mentor, her_records(player), "talk", about, 0, _r.Random(about))
    return chosen[:2]


def read_claims(player, said: str, asked: str, day: int):
    """What her draft would add to what is true of her, like anyone else's (engine/canon.py), not yet kept."""
    from engine import canon, quirks
    return canon.read(player.mentor, NAME, said, asked, day, details=quirks.Q["maren"]["details"], given_facts=GIVEN)


def chat_system() -> str:
    C = M["chat"]
    from engine import quirks
    return (chat_system_persona() + "\n\nHOW YOU SPEAK:\n" + "\n".join(f"- {b}" for b in quirks.Q["maren"]["blueprint"]) +
            "\n\n" + quirks.style_block() +
            "\n\nRULES:\n" + "\n".join(f"- {r}" for r in C["rules"]) +
            "\n\nGESTURE: " + __import__("engine.quirks", fromlist=["GESTURE_RULE"]).GESTURE_RULE +
            "\n\nAlso say whether the player is moving on: moves_on is true only when what they said means they are ready to go on or get "
            "moving (go to the hall, sign up, set out, carry on), not when they ask or tell you something."
            "\n\nWhatever specific thing you say about yourself becomes true of you for good, so choose it with care, and never contradict "
            "anything given as true of you."
            "\n\nRespond only with JSON matching the schema: {\"speech\": \"what you say\", \"gesture\": \"\", \"moves_on\": false}.")


def rules_for(about: str) -> str:
    """The rules for this kind of question only (mentor.yaml chat.rules_when): how to tell them what to type when it is about what to do or
    the commands; how to explain a fight when it is about fighting. Nothing for a question about her."""
    want = topics_in(about) if about else set()
    R = M["chat"]["rules_when"]
    out = []
    if want & {"commands", "board", "joining"} or (about and wants_objective(about)):
        out.append(R["commands"])
    if want & {"combat", "status"}:
        out.append(R["combat"])
    return "\n".join(f"- {r}" for r in out)


def wants_objective(about: str) -> bool:
    """Is the talk about what to do next (by meaning, mentor.yaml chat.objective_about)?"""
    from engine import relevance
    return bool(about and relevance.pick(about, [M["chat"]["objective_about"]], 1))


def chat_prompt(player, where: str, text: str, scene: str = "", unsaid: str = "", props: str = "", leaned: str = "", again: str = "",
                again_how: str = "", fix: str = "", truth_text: str = ""):
    """Her request in typed parts (engine/prompt.py), like every other speaker's. truth_text is her view of the moment from the truth layer
    (engine/truth.py, f315): where she is, who is here, what the town has, the board as it really is."""
    from engine.prompt import Prompt
    recent = player.mentor.get("chat", [])[-8:]
    talk = "\n".join(f"  {who}: {said}" for who, said in recent) or "  (nothing yet)"
    p = Prompt()
    p.fact(facts(player, where, text + " " + scene), "FACTS")
    p.fact(truth_text)
    p.instruction(rules_for(text + " " + scene), "FOR THIS QUESTION")
    p.fact(scene, "RIGHT NOW IN THE FIGHT")
    p.fact(fix)
    p.fact(again, "ASKED BEFORE")
    p.instruction(again_how)
    p.history(unsaid)
    p.fact(props)
    p.history(leaned)
    p.history(talk, "WHAT WAS SAID LATELY")
    p.fact(text, "THE PLAYER SAYS TO YOU")
    return p


def chat_request(player, where: str, text: str, scene: str = "", unsaid: str = "") -> str:
    recent = player.mentor.get("chat", [])[-8:]
    talk = "\n".join(f"  {who}: {said}" for who, said in recent) or "  (nothing yet)"
    now = f"\n\nRIGHT NOW IN THE FIGHT: {scene}" if scene else ""
    more = f"\n\n{unsaid}" if unsaid else ""
    return f"FACTS:\n{facts(player, where, text + ' ' + scene)}{now}{more}\n\nWHAT WAS SAID LATELY:\n{talk}\n\nTHE PLAYER SAYS TO YOU: {text}"


def remember_chat(player, text: str, reply: str) -> None:
    log = player.mentor.setdefault("chat", [])
    log += [["Player", text[:300]]] + ([[NAME.split()[0], reply[:400]]] if reply else [])
    del log[:-12]
    if reply:
        player.mentor["last_voice"] = True


def make_npc(player, minutes: int, turn: int, place_id: str):
    """Her record as a person of the world once the tutorial is over: what she remembers of the player, how she feels, where she is."""
    from npc.models import NPC, Memory
    from engine import clock
    said = [t for who, t in player.mentor.get("chat", []) if who == "Player" and t.strip()]
    day = clock.day(minutes)
    mem = [Memory(day=day, turn=turn, text="Met a stranger in Parth, armed and with no guild badge. At first I took them for a bandit.")]
    for t in said[:4]:
        mem.append(Memory(day=day, turn=turn, text=f"They told me: {t[:160]}"))
    mem += [Memory(day=day, turn=turn, text=f"Walked {player.character.name} to the guild hall and watched them sign in."),
            Memory(day=day, turn=turn, text="Let them hire me as practice. Fought a troll beside them in the Greywood, where no troll should be."),
            Memory(day=day, turn=turn, text="They did well."),
            Memory(day=day, turn=turn, text="Left Parth after, on the work the capital sent me south to do. My own party is to catch me up on the road. They are my companions, not the stranger's: the stranger came alone.")]
    npc = NPC(id="maren", name=NAME, people="human", role="guild_contractor", location=place_id, gender="female", tier="significant",
              epithet="the A-rank adventurer", description="A broad-shouldered woman in her middle years in dark plate with gold detailing and a greatsword on her back.",
              concern="Things where they do not belong, and the work the capital sent her south to do.",
              trust=65, mood="fond of the player, though she would not say so", name_known_to_player=True, met_player=True,
              knows_player_as=player.character.name, protected=True, memories=mem,
              gone=M["npc"]["gone"])                                 # (f382) she goes on her way: a record, in no place
    return own_voice(npc, player)


def moved_on(store, world, npc, t: int) -> None:
    """(f382) She has left Parth: out of every place's residents, in the journal, and news in the town she left."""
    from engine import pulse
    if npc.location in world.places:
        ps = store.load_place(npc.location)
        if npc.id in ps.residents:
            ps.residents = [r for r in ps.residents if r != npc.id]
            store.save_place(ps)
    store.journal(t, "npc_gone", "", npc.id, f"{npc.name} is gone: {npc.gone}", {"how": npc.gone, "place": npc.location})
    state = store.load_world_state()
    pulse.add_news(state, M["npc"]["news"], pulse.town_of(world, M["gate"]["place"]), t, ["everyone"])
    store.save_world_state(state)


def own_voice(npc, player=None):
    """(f374) Her record keeps the voice she was written with (mentor.yaml npc): her personality told of her rather than to her, her voice,
    her rank, and a speech profile that marks her as written by hand (no kit habits, no rolled stance: engine/voices.py, voice_rules.py)
    with lines she has said to this player (the lesson's talk, the conversational ones) or, when there are few, lines written in her voice."""
    from engine import voices
    N = M["npc"]
    npc.personality = " ".join(N["personality"].split())
    npc.voice = N["voice"]
    npc.rank = N.get("rank", "")
    said = [t for who, t in (player.mentor.get("chat", []) if player is not None else []) if who == NAME.split()[0]]
    said = [" ".join(t.split()) for t in said if "#" not in t and not re.search(r"(?<![A-Za-z])'[^']{3,60}'(?![A-Za-z])", t)   # not a command taught
            and 8 <= len(t.split()) <= 45]
    samples = (said[-4:] + [s for s in N.get("samples", []) if s not in said])[:5]
    npc.speech = {"own_voice": True, "kit": {axis: voices.unmarked(axis) for axis in voices.AXES}, "samples": samples}
    return npc


def maren_fighter(level_mentor: int | None = None):
    """Her fighting sheet: a veteran far above the troll, with a greatsword worth several plain ones."""
    T = M["troll_sheet"]
    me = combat.fighter_from_creature(_world().bestiary[T["stand_in"]], level_mentor or T["level_mentor"], "normal", "maren", NAME, "near")
    me.side = "ally"
    me.ally_role = "mentor"                              # not a bonded companion: her gear and passives are her own
    me.weapon_name = T["weapon"]
    me.weapon_damage *= T.get("weapon_mult", 1.0)
    return me


def troll_fighter(band: str = "engaged"):
    T = M["troll_sheet"]
    return combat.fighter_from_creature(_world().bestiary[T["creature"]], T["level"], "normal", "e1", "troll", band)


def troll_fight(seed, level_mentor: int | None = None) -> dict:
    """Her blow against the troll worked out on its own (for the tests and the balance check): she does not miss the troll, so the
    first stroke that lands kills it. Returns {"max": troll health, "blows": [damage], "left": [troll health after each blow]}."""
    rng = random.Random(f"{seed}:mentor:troll")
    me = maren_fighter(level_mentor)
    me.side = "player"                                  # the fight engine needs someone on the player's side to act
    troll = troll_fighter("near")
    fight = combat.Combat(fighters=[me, troll], record=False)
    blows, left = [], []
    for _ in range(30):
        before = troll.hp
        combat.act_attack(fight, me, troll, rng)
        if troll.hp >= before:                          # she does not miss the troll: swing again
            continue
        blows.append(round(before - troll.hp))
        left.append(max(0, round(troll.hp)))
        if not troll.alive:
            break
    return {"max": troll.max_hp, "blows": blows, "left": left}


def remember_said(player, text: str) -> None:
    """What she has just said goes into the lately-said log, so the next thing she says follows from it."""
    log = player.mentor.setdefault("chat", [])
    log.append([NAME.split()[0], text[:400]])
    del log[:-24]
    player.mentor["last_voice"] = True


# ---------- her words, from the model, inside limits ----------

class Fixed(list):
    """Lines she says exactly as written: the guild's real rules and figures. Everything else she says is put in her own words."""


NUMBER_WORDS = {"two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "twenty", "thirty", "forty", "fifty",
                "sixty", "seventy", "eighty", "ninety", "hundred", "thousand", "dozen", "half", "twice", "double"}
WORD_NUM = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
            "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100, "thousand": 1000}


def same_figures(text: str) -> set[str]:
    """The other way of writing each figure in this text: '3' also allows 'three', and 'three' also allows '3'. Said aloud, a figure may be
    spelt either way; only a different amount is a change."""
    low = text.lower()
    out = {w for w, n in WORD_NUM.items() if re.search(rf"(?<!\d){n}(?!\d)", low)}
    out |= {str(WORD_NUM[w]) for w in re.findall(r"[a-z]+", low) if w in WORD_NUM}
    return out
BANNED_WORDS = {"game", "player", "npc", "ai", "model", "prompt", "interface", "program", "engine", "stats"}


def _facts_of(line: str) -> tuple[set, set, set]:
    low = line.lower()
    digits = set(re.findall(r"\d+", low))
    commands = set(re.findall(r"#\w+", low))
    quoted = {q.strip().lower() for q in re.findall(r"(?<![A-Za-z])'([^']{3,40}?)'(?![A-Za-z])", line)}
    return digits, commands, quoted


def check_voice(source: list[str], out: list[str]) -> str:
    """Why her reworded lines can't be used, or '' if they can: the same number of lines, every figure, command and quoted phrase kept,
    nothing new in the way of numbers, no talk of a game, and a question stays a question. The reason is shown to the model on a retry."""
    if len(out) != len(source):
        return f"give exactly {len(source)} lines, one for each line given, in the same order (you gave {len(out)})"
    for n, (src, new) in enumerate(zip(source, out), 1):
        if not new.strip():
            return f"line {n} is empty"
        digits, commands, quoted = _facts_of(src)
        got_digits, got_commands, _ = _facts_of(new)
        low = new.lower()
        for d in sorted(digits):
            if d not in got_digits:
                return f"line {n} must keep the figure {d}"
        for c in sorted(commands):
            if c not in got_commands:
                return f"line {n} must keep the command {c}"
        for q in sorted(quoted):
            if q not in low:
                return f"line {n} must keep the words '{q}' exactly"
        if got_digits - digits:
            return f"line {n} adds a number that is not in the original"
        said = set(re.findall(r"[a-z]+", low))
        if (said & NUMBER_WORDS) - (set(re.findall(r"[a-z]+", src.lower())) | same_figures(src)):
            return f"line {n} changes how many or how much: use only the amounts in the original"
        if (said & BANNED_WORDS) - set(re.findall(r"[a-z]+", src.lower())):
            return f"line {n} must not talk about a game or its parts: say it as something that is simply so in the world"
        if "*" in new or '"' in new:
            return f"line {n} must be plain speech: no asterisks and no quotation marks"
        if src.rstrip().endswith("?") != new.rstrip().endswith("?"):
            return f"line {n} must {'be a question' if src.rstrip().endswith('?') else 'not be a question'}, as in the original"
    return ""


RULE_UNITS = r"(?:level|levels|contract|contracts|at a time|silver|gold|copper|coin|coins)"
_RULE_FIG = re.compile(rf"\b(?:level\s+(\d+|[a-z]+)|(\d+|[a-z]+)\s+(?:finished\s+|more\s+)?{RULE_UNITS})\b")


def rule_figures(text: str) -> set[str]:
    """The figures a line states in the guild's own units - a level, a count of contracts, how many at a time, a sum of coin - as digits.
    'Eleven years' is not one; 'level 30' and 'five contracts' are."""
    out = set()
    for a, b in _RULE_FIG.findall(text.lower()):
        w = a or b
        if w.isdigit():
            out.add(w)
        elif w in WORD_NUM:
            out.add(str(WORD_NUM[w]))
    return out


def check_figures(asked: str, reply: str) -> str:
    """A rules question answered in her own words may state levels, contract counts and sums only as the guild really has them: why the
    draft cannot be used, or '' if it can. Figures in any other unit (years, wolves, miles) are hers to invent."""
    want = topics_in(asked) & {"ranks", "board", "joining"}
    if not want:
        return ""
    allowed = {d for t in want for line in topic_text(t) for d in _facts_of(line)[0]}
    wrong = rule_figures(reply) - allowed
    if wrong:
        return f"the figure {sorted(wrong, key=int)[0]} is not one of the guild's: use only the real levels, contract counts and sums given in FACTS, or give none"
    return ""


def check_reply(reply: str) -> str:
    """Her answer to what the player just said, in plain speech, with no rules, figures or talk of a game."""
    low = reply.lower()
    if not reply.strip():
        return "give a 'reply' answering what the player just said"
    if re.search(r"\d", reply):
        return "the reply must not state any numbers"
    if set(re.findall(r"[a-z]+", low)) & BANNED_WORDS:
        return "the reply must not talk about a game or its parts"
    if "*" in reply or '"' in reply or "#" in reply:
        return "the reply must be plain speech: no asterisks, quotation marks or commands"
    return ""


def voice_system(player) -> str:
    V = M["voice"]
    return (chat_system_persona() + "\n\nYOUR JOB: you are given lines Maren is going to say next. Say them as Maren would, in your own words, "
            "keeping everything in them.\nRULES:\n" + "\n".join(f"- {r}" for r in V["rules"]) +
            "\n\nRespond only with JSON matching the schema: {\"reply\": \"your answer to what the player just said, or empty if they said nothing\", "
            "\"lines\": [\"first line\", \"second line\"]}.")


def chat_system_persona() -> str:
    from llm.prompts import WORLD_RULES
    return M["chat"]["persona"].strip() + "\n\n" + WORLD_RULES


def voice_request(player, where: str, beat: str, lines: list[str], reply_to: str = "") -> str:
    recent = player.mentor.get("chat", [])[-6:]
    talk = "\n".join(f"  {who}: {said}" for who, said in recent) or "  (nothing yet)"
    numbered = "\n".join(f"{n}. {x}" for n, x in enumerate(lines, 1))
    ask = ""
    if reply_to:
        ask = (f"\n\nTHE PLAYER JUST SAID: \"{reply_to[:300]}\"\n{M['voice']['reply_rule']}")
    return (f"FACTS:\n{facts(player, where, ' '.join(lines) + ' ' + reply_to, objective=True)}\n\nWHAT WAS SAID LATELY:\n{talk}\n\n"
            f"WHAT THIS IS: {beat or 'what Maren says next'}{ask}\n\nLINES TO SAY ({len(lines)}):\n{numbered}")


def check_speech(paragraphs: list[str], ctx: dict) -> str:
    """Why a speech she wrote freely can't be used, or '': something said, every required phrase word for word, no
    figure or amount that is not in the material, no talk of a game, no name as her first word, and the ending the beat asks for."""
    if not paragraphs:
        return "write what Maren says, in paragraphs of natural speech"
    whole = " ".join(paragraphs)
    low = " ".join(whole.lower().split())
    for n, p in enumerate(paragraphs, 1):
        if "*" in p or '"' in p:
            return f"paragraph {n} must be plain speech: no asterisks and no quotation marks"
    for phrase in ctx.get("must", []):
        if " ".join(phrase.lower().split()) not in low:
            return f"you must include the words '{phrase}' exactly as written"
    material = " ".join(ctx.get("material", []) + ctx.get("must", [])).lower()
    if set(re.findall(r"\d+", whole)) - (set(re.findall(r"\d+", material)) | same_figures(material)):
        return "you used a number that is not in the material: use only the figures given"
    mwords = set(re.findall(r"[a-z]+", material)) | same_figures(material)
    said = set(re.findall(r"[a-z]+", low))
    if (said & NUMBER_WORDS) - mwords:
        return "you gave an amount that is not in the material: use only the figures and amounts given"
    if (said & BANNED_WORDS) - mwords:
        return "do not talk about a game or its parts: say it as something simply true of the world and the guild"
    if re.match(r"\s*maren\b", paragraphs[0].lower()):
        return "do not begin by saying your own name"
    if ctx.get("ends_question") and not paragraphs[-1].rstrip().endswith("?"):
        return "end with the question"
    if ctx.get("ranks"):
        why = check_ranks(whole, ctx["ranks"])
        if why:
            return why
    return ""


def speech_system(player) -> str:
    V = M["voice"]
    from engine import quirks
    return (chat_system_persona() + "\n\nHOW YOU SPEAK:\n" + "\n".join(f"- {b}" for b in quirks.Q["maren"]["blueprint"]) +
            "\n\nSTYLE:\n" + "\n".join(f"- {r}" for r in quirks.Q["style_rules"]) +
            "\n\nYOUR JOB: write what Maren says next, as natural speech in paragraphs: group related sentences "
            "together instead of putting each sentence on its own line.\nRULES:\n" + "\n".join(f"- {r}" for r in V["speech_rules"]) +
            "\n\nRespond only with JSON matching the schema: {\"paragraphs\": [\"first paragraph\", \"second paragraph\"]}.")


def speech_request(player, where: str, beat: str, points: list[str], must: list[str], reply_to: str = "", ends: str = "") -> str:
    recent = player.mentor.get("chat", [])[-6:]
    talk = "\n".join(f"  {who}: {said}" for who, said in recent) or "  (nothing yet)"
    pts = "\n".join(f"{n}. {x}" for n, x in enumerate(points, 1))
    musts = "\n".join(f"  - {x}" for x in must) or "  (none)"
    heard = f"\n\nTHE PLAYER JUST SAID: \"{reply_to[:300]}\"\n{V_REPLY()}" if reply_to else ""
    end = f"\n\nHOW IT ENDS: {ends}" if ends else ""
    return (f"FACTS:\n{facts(player, where, ' '.join(points) + ' ' + ' '.join(must) + ' ' + reply_to, objective=True)}\n\nWHAT WAS SAID LATELY:\n{talk}\n\nWHAT THIS IS: {beat}{heard}\n\n"
            f"POINTS TO COVER, in this order. They are how Maren might put it; say it in your own words and your own order of sentences, "
            f"but cover every point:\n{pts}\n\nWORD FOR WORD: these must appear exactly as written, inside your own sentences:\n{musts}{end}")


def V_REPLY() -> str:
    return M["voice"]["speech_reply"]
