"""Quirks: what makes a hired companion somebody. Rolled once at hire from data/rules/quirks.yaml and kept on the member record:
  habit    - shown by the engine at its moment (rest, arrival, a fight starting or ending), so it is always there
  voice    - a pattern in how they talk, held in the prompt and checked where it can be
  likes / dislikes - a deed of the player's they approve of and one they cannot stand; the engine sees the deed and they react
  flaw     - rare, mechanical, visible
  errand   - once they trust you, their want asks something small of you
  secrets  - once they trust you, and once they are devoted, something they tell you
  growth   - how they have changed with you, by tier
The engine supplies the specifics; the model supplies the delivery."""
from __future__ import annotations

import random
import re
from pathlib import Path

import yaml

from engine import party as rules

Q = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "quirks.yaml").read_text(encoding="utf-8"))

PRONOUNS = {"she": ("her", "her", "she", "hands"), "he": ("his", "him", "he", "hands"), "they": ("their", "them", "they", "hand")}


def pronouns(member: dict) -> dict:
    """{their, them, they, they_cap, hand}: a hire's pronouns are theirs if set, else 'they'."""
    p = member.get("pronoun") or "they"
    their, them, they, hand = PRONOUNS.get(p, PRONOUNS["they"])
    return {"their": their, "them": them, "they": they, "they_cap": they.capitalize(), "hand": hand}


# ---------- rolling ----------

def roll_voice(q: dict, rng: random.Random) -> None:
    for k in ("oath", "trade", "nick", "tongue", "curses"):
        q.pop(k, None)
    keys = [k for k, spec in Q["voices"].items() if spec.get("weight", 1) > 0]
    v = rng.choices(keys, weights=[Q["voices"][k].get("weight", 1) for k in keys])[0]
    q["voice"] = v
    spec = Q["voices"][v]
    if "oaths" in spec:
        q["oath"] = rng.choice(spec["oaths"])
    if "trades" in spec:
        q["trade"] = rng.choice(spec["trades"])
    if "nicks" in spec:
        q["nick"] = rng.choice(spec["nicks"])
    if v == "second_tongue":
        q["tongue"] = rng.choice(list(Q["tongues"]))
    if v == "curses":
        q["curses"] = rng.sample(Q["curses"]["world"], 2) + rng.sample(Q["curses"]["mild"], 1) + rng.sample(Q["curses"]["strong"], 1)


def roll(member: dict, rng: random.Random) -> None:
    """Give a new hire their quirks. Idempotent: a member who has them keeps them, except a voice that is no longer in the data, which is
    rolled again."""
    if member.get("quirks"):
        if member["quirks"].get("voice") not in Q["voices"]:
            roll_voice(member["quirks"], rng)
        return
    q: dict = {}
    q["habit"] = rng.choice(list(Q["habits"]))
    roll_voice(q, rng)
    v = q["voice"]
    spec = Q["voices"][v]
    deeds = list(Q["deeds"])
    q["likes"] = rng.choice(deeds)
    q["dislikes"] = rng.choice([d for d in deeds if d != q["likes"]])
    q["flaw"] = rng.choice(list(Q["flaws"])) if rng.randrange(100) < Q["flaw_chance"] else ""
    E = Q["errands"].get(member.get("motive", ""), {})
    if E.get("targets"):
        q["target"] = rng.choice(E["targets"])
    q["habit_shown"] = 0
    q["reacted"] = {}          # deed -> day last reacted
    q["told"] = 0              # secrets told so far
    q["errand"] = ""           # "" | "asked" | "yes" | "no"
    member["quirks"] = q
    member.setdefault("fights_total", 0)


# ---------- the prompt ----------

def voice_prompt(member: dict, rng: random.Random | None = None) -> str:
    """Their marked way of talking, for one reply. With rng, a conditional voice (one that shows when the moment invites it) is in only some
    replies (voice_show); without, always - for writing about them."""
    q = member.get("quirks") or {}
    spec = Q["voices"].get(q.get("voice", ""))
    if not spec:
        return ""
    if rng is not None and spec.get("kind") == "conditional" and rng.random() >= Q["voice_show"]["conditional"]:
        return ""
    return spec["prompt"].format(oath=q.get("oath", ""), trade=q.get("trade", ""), nick=q.get("nick", ""), first=member["name"].split()[0],
                                 curses=", ".join(f"'{c}'" for c in my_curses(member)), tongue_prompt=tongue_prompt(member))


def material(member: dict, rng: random.Random, recent: list[str] | None = None, feature: tuple = ("", None)) -> list[str]:
    """Words that may be said as they are, offered for this one reply: what they call the player (always), and now and then one curse, their
    oath, a word of their home tongue or a saying from home - never one used in what they said lately. The engine owns how often; the model
    sees only what is offered, so it cannot lean on one phrase."""
    q = member.get("quirks") or {}
    v = q.get("voice", "")
    M = Q.get("material", {})
    lately = " ".join((recent or [])[-4:]).lower()
    fresh = lambda w: w.lower()[:24] not in lately
    out = []
    if v == "nickname" and q.get("nick"):
        out.append(f"what they call the player, always: '{q['nick']}'")
    if v == "curses":
        mine = [c for c in my_curses(member) if fresh(c)]
        if mine and rng.random() < M.get("curse", 0.35):
            out.append(f"a curse of theirs, if something here gets to them: '{rng.choice(mine)}'")
    if v == "swears_by" and q.get("oath") and fresh(q["oath"]) and rng.random() < M.get("oath", 0.3):
        out.append(f"their oath, if something moves them: 'by {q['oath']}'")
    from engine import voice_profile                     # the culture budget decides whether a saying or a home word is offered at all
    out += voice_profile.material_for_feature(member, feature)
    return out


def material_block(offers: list[str]) -> str:
    return "\n".join(f"  - {x}" for x in offers)


def my_curses(member: dict) -> list[str]:
    """The curses this hire uses, as far as the game's setting allows: their world curses always, real ones only at mild or strong."""
    import config
    level = getattr(config, "PROFANITY", "mild")
    q = member.get("quirks") or {}
    out = []
    for c in q.get("curses", []):
        if c in Q["curses"]["world"] or (c in Q["curses"]["mild"] and level in ("mild", "strong")) or (c in Q["curses"]["strong"] and level == "strong"):
            out.append(c)
    return out


def tongue(member: dict) -> dict:
    """Their first tongue if it is not Common (engine/voice_profile.py): home, habits, words, and their culture's sayings."""
    from engine import voice_profile
    return voice_profile.tongue_of(member)


def tongue_prompt(member: dict) -> str:
    t = tongue(member)
    if not t:
        return ""
    words = "; ".join(f"'{w}' ({m})" for w, m in t["words"].items())
    return Q["tongue_prompt"].format(home=t["home"], habits=t["habits"], words=words)


def habit_prompt(member: dict) -> str:
    q = member.get("quirks") or {}
    spec = Q["habits"].get(q.get("habit", ""))
    return spec["prompt"] if spec else ""


def flaw_prompt(member: dict) -> str:
    q = member.get("quirks") or {}
    spec = Q["flaws"].get(q.get("flaw", ""))
    return spec["prompt"] if spec else ""


def leanings(member: dict) -> str:
    q = member.get("quirks") or {}
    if not q.get("likes"):
        return ""
    return f"Approves of {Q['deeds'][q['likes']]}; cannot stand {Q['deeds'][q['dislikes']]}."


def growth(member: dict) -> str:
    tier = rules.bond_tier(member)
    table = Q["growth"].get(tier)
    if not table:
        return ""
    temper = (member.get("temper") or [""])[0]
    return table.get(temper) or table.get("default", "")


def nickname(member: dict) -> str:
    q = member.get("quirks") or {}
    return q.get("nick", "") if q.get("voice") == "nickname" else ""


def core_lines(member: dict) -> str:
    """The quirk part of WHO YOU ARE: voice, habit, leanings, flaw (as a weakness they know), growth. One compact run of clauses."""
    bits = []
    v = voice_prompt(member)
    if v:
        bits.append(f"In speech, {v}.")
    h = habit_prompt(member)
    if h:
        bits.append(f"A habit: {h}.")
    l = leanings(member)
    if l:
        bits.append(l)
    f = flaw_prompt(member)
    if f:
        bits.append(f"A weakness they know of: {f}.")
    g = growth(member)
    if g:
        bits.append(f"With the player, they have changed: {g}.")
    return " ".join(bits)


# ---------- checks on a line ----------

CONTRACTION = re.compile(r"\b\w+n't\b|\b(i'm|you're|we're|they're|he's|she's|it's|that's|there's|what's|who's|let's|i've|you've|we've|they've|i'll|you'll|we'll|he'll|she'll|they'll|it'll|i'd|you'd|we'd|he'd|she'd|they'd|can't|won't|don't|isn't|aren't|wasn't|weren't|didn't|doesn't|hasn't|haven't|wouldn't|couldn't|shouldn't)\b", re.I)


def voice_check(member: dict, speech: str, player_name: str = "", recent: list[str] | None = None) -> str:
    """Why a line breaks this hire's way of talking, or ''."""
    q = member.get("quirks") or {}
    spec = Q["voices"].get(q.get("voice", ""))
    if not spec or not speech:
        return ""
    check = spec.get("check", "")
    if check == "no_contractions" and CONTRACTION.search(speech):
        return "this person never uses contractions: write 'do not', 'I am', 'it is'"
    if check == "no_thanks" and re.search(r"\bthank", speech, re.I):
        return "this person never says thank you: show it some other way"
    if check == "oath" and q.get("oath") and q["oath"].lower() in speech.lower() and any(q["oath"].lower() in r.lower() for r in (recent or [])[-2:]):
        return f"they swore by {q['oath']} only just now: not in every breath"
    if check == "curses":
        import config
        low = speech.lower()
        mine = [c for c in my_curses(member) if re.search(rf"\b{re.escape(c.lower())}", low)]
        if mine and any(re.search(rf"\b{re.escape(c.lower())}", r.lower()) for c in my_curses(member) for r in (recent or [])[-2:]):
            return "they cursed only just now: not in two breaths running"
        level = getattr(config, "PROFANITY", "mild")
        banned = (Q["curses"]["mild"] + Q["curses"]["strong"]) if level == "off" else (Q["curses"]["strong"] if level == "mild" else [])
        bad = [b for b in banned if re.search(rf"\b{re.escape(b)}", low)]
        if bad:
            return f"too coarse for this game: no '{bad[0]}'"
    if tongue(member).get("words"):
        t = tongue(member)
        known = set(t.get("words", {}))
        from engine import voice_profile
        others = {w for o in list(Q["tongues"].values()) + list(voice_profile.S["tongues"].values()) for w in o["words"]} - known
        used = [w for w in re.findall(r"[a-z]+", speech.lower()) if w in others]
        if used:
            return f"'{used[0]}' is not a word of their tongue; their own words are {', '.join(sorted(known))}"
        if sum(1 for w in re.findall(r"[a-z]+", speech.lower()) if w in known) > 2:
            return "a word or two of their own tongue at most, not a stream of them"
    if check == "nickname" and player_name:
        first = player_name.split()[0]
        if len(first) > 2 and re.search(rf"\b{re.escape(first)}\b", speech, re.I):
            return f"this person never uses the player's name; they call them '{q.get('nick', '')}'"
    return ""


# ---------- habits ----------

def habit_fits(spec: dict, place_type: str) -> bool:
    """(f379) Can this habit happen in this kind of place: a door for the doorframe, a sky for reading the sky. No place type: anywhere."""
    where = spec.get("where", "")
    if not where or not place_type:
        return True
    building = place_type in Q.get("buildings", [])
    if where == "building":
        return building
    if where == "open_air":
        return not building and place_type not in Q.get("under_ground", [])
    return True


def habit_line(member: dict, when: str, rng: random.Random, weapon: str = "", danger: bool = False, day: int | None = None,
               place_type: str = "") -> str:
    """The habit shown at its moment, or ''. Always the first time; then most of the time, and never twice in one day (a night run saw
    'takes the first watch' on every hour's wait). (f379) Never where it cannot happen (habit_fits)."""
    q = member.get("quirks") or {}
    spec = Q["habits"].get(q.get("habit", ""))
    if not spec or not habit_fits(spec, place_type):
        return ""
    if day is not None and q.get("habit_day") == day:
        return ""
    want = spec["when"]
    if want == "arrival_danger":
        if when != "arrival" or not danger:
            return ""
    elif want != when:
        return ""
    if q.get("habit_shown", 0) and rng.randrange(100) >= Q["habit_chance"]:
        return ""
    q["habit_shown"] = q.get("habit_shown", 0) + 1
    if day is not None:
        q["habit_day"] = day
    p = pronouns(member)
    return spec["line"].format(name=member["name"].split()[0], weapon=weapon or "blade", count=member.get("fights_total", 0), **p)


# ---------- deeds ----------

def _worn(table: list, n: int) -> float:
    return float(table[min(n, len(table) - 1)]) if table else 1.0


def reaction(member: dict, deed: str, day: int, rng=None) -> str:
    """'approve', 'disapprove' or '' for this deed: not if they have already reacted to it today, and - the more often they have reacted
    to it before - less and less likely at all (habituation.react_chance; with no rng, as if the dice allowed it)."""
    q = member.get("quirks") or {}
    if deed not in Q["deeds"]:
        return ""
    if Q.get("reaction_once_per_day") and q.get("reacted", {}).get(deed) == day:
        return ""
    seen = (q.get("deeds_seen") or {}).get(deed, 0)
    if rng is not None and rng.random() >= _worn(Q["habituation"]["react_chance"], seen):
        return ""
    if q.get("likes") == deed:
        return "approve"
    if q.get("dislikes") == deed:
        return "disapprove"
    return ""


def react(member: dict, deed: str, how: str, day: int, spoke: bool = True) -> int:
    """Apply a reaction: bond moves, a memory is kept, the day is noted. Returns the bond change. Whether they said so is part of the memory:
    one who kept it to themselves remembers that, not a word they never said."""
    q = member.setdefault("quirks", {})
    q.setdefault("reacted", {})[deed] = day
    seen = q.setdefault("deeds_seen", {})
    base = Q["approve_bond"] if how == "approve" else Q["disapprove_bond"]
    delta = int(round(base * _worn(Q["habituation"]["bond_share"], seen.get(deed, 0))))      # less each time: they come to terms with it
    member["bond"] = member.get("bond", 0) + delta
    from engine import canon
    canon.journal("deed_reaction", "player", member.get("id", ""), f"{member.get('name', '')} {'approved of' if how == 'approve' else 'minded'} {Q['deeds'].get(deed, deed)}",
                  deed=deed, how=how, bond=delta, spoke=spoke)
    seen[deed] = seen.get(deed, 0) + 1
    n = seen[deed]
    times = "once" if n == 1 else ("twice" if n == 2 else f"{n} times")
    if spoke:
        feel = "I liked it and told them so" if how == "approve" else "I do not hold with it, and I told them so"
    else:
        feel = "I liked it, and kept that to myself" if how == "approve" else "I do not hold with it, and kept that to myself"
    rules.remember(member, day, f"I have seen them {DEED_ACT.get(deed, Q['deeds'][deed])} {times} now; {feel}.", 2 + (n >= 3), key=f"deed:{deed}")
    return delta


DEED_ACT = {"loot_dead": "pick over the dead", "spare": "spare a foe who yielded", "flee": "run from a fight", "bribe": "pay someone to look away",
            "sleep_late": "sleep past midday", "charity": "give coin away", "harvest": "skin and butcher what they kill",
            "shrine": "stop at a shrine", "inn": "take a bed at an inn"}


def reaction_fallback(deed: str, how: str, rng: random.Random) -> str:
    return rng.choice(Q["reactions"][how]).format(deed=Q["deeds"][deed])


# ---------- flaws ----------

def flaw(member: dict) -> str:
    return (member.get("quirks") or {}).get("flaw", "")


def hungover(member: dict, minutes: int) -> bool:
    return flaw(member) == "drinker" and minutes < member.get("hungover_until", -1)


# ---------- errands and secrets ----------

def errand(member: dict) -> dict | None:
    """The errand this hire's want would ask, if they trust the player and have not asked yet."""
    q = member.get("quirks") or {}
    E = Q["errands"].get(member.get("motive", ""))
    if not E or E.get("where") == "none" or q.get("errand"):
        return None
    names = [t[1] for t in rules.P["bond"]["tiers"]]
    if names.index(rules.bond_tier(member)) < names.index("trusted"):
        return None
    return E


def errand_text(member: dict, key: str, **extra) -> str:
    E = Q["errands"].get(member.get("motive", ""), {})
    q = member.get("quirks") or {}
    return E.get(key, "").format(name=member["name"].split()[0], target=q.get("target", "someone"), **pronouns(member), **extra)


def secret_due(member: dict) -> str:
    """The next thing they would tell the player, if trust has reached it, or ''."""
    q = member.get("quirks") or {}
    told = q.get("told", 0)
    S = member.get("secrets") or Q["secret_fallback"].get(member.get("motive", ""), [])     # their own, written with their life
    names = [t[1] for t in rules.P["bond"]["tiers"]]
    tier = names.index(rules.bond_tier(member))
    if told == 0 and tier >= names.index("trusted") and len(S) > 0:
        return S[0]
    if told == 1 and tier >= names.index("devoted") and len(S) > 1:
        return S[1]
    return ""


def told(member: dict, day: int, secret: str) -> None:
    q = member.setdefault("quirks", {})
    q["told"] = q.get("told", 0) + 1
    rules.remember(member, day, f"I told them something I tell nobody: {secret}", 3)


COMMON = {"because", "someone", "something", "anyone", "nobody", "which", "there", "their", "would", "could", "should", "never", "still", "whole",
          "thinks", "think", "about", "being", "every", "other", "these", "those", "where", "while", "really", "always", "before", "after", "again",
          "people", "things", "little", "right", "first", "years", "today", "going", "doing", "since", "though", "through", "without", "nothing"}


def must_words(secret: str, n: int = 2) -> list[str]:
    """The secret's rarest words, which its retelling must keep, so it is the same secret: the longest uncommon ones."""
    words = [w for w in dict.fromkeys(re.findall(r"[A-Za-z]{5,}", secret)) if w.lower() not in COMMON]
    return sorted(words, key=lambda w: -len(w))[:n]


# ---------- what belongs to one speaker's way of talking ----------

def markers(member: dict) -> set[str]:
    """The words that are this person's own, by the voice they have now: their oath, their curses, their name for the player. A field left
    over from a voice they no longer have (an oath kept after the voice changed) is not theirs."""
    q = member.get("quirks") or {}
    v = q.get("voice", "")
    out = set()
    if v == "swears_by" and q.get("oath"):
        out.add(q["oath"].lower())
    if v == "curses":
        out |= {c.lower() for c in q.get("curses", [])}
    if v == "nickname" and q.get("nick"):
        out.add(q["nick"].lower())
    return out


def borrowed(speaker: dict, text: str, others: list[dict]) -> str:
    """A word in this line that belongs to someone else's way of talking and not to the speaker's, or ''."""
    low = text.lower()
    mine = markers(speaker)
    for o in others:
        for w in markers(o) - mine:
            if re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", low):
                return f"'{w}' is how {o['name'].split()[0]} talks, not {speaker['name'].split()[0]}"
    return ""


def cursed_lately(member: dict, recent: list[str]) -> bool:
    low = " ".join((recent or [])[-2:]).lower()
    return any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", low) for w in markers_curses(member))


def markers_curses(member: dict) -> set[str]:
    q = member.get("quirks") or {}
    v = q.get("voice", "")
    return ({q["oath"].lower()} if v == "swears_by" and q.get("oath") else set()) | ({c.lower() for c in my_curses(member)} if v == "curses" else set())


def voice_notes(member: dict, others: list[dict] | None = None, solo: bool = False) -> str:
    """Said before generating: whether this speaker has just cursed. Nobody's words are listed here - a list of words, even marked as someone
    else's, is a list the model reaches into; each speaker is offered only their own, under their own name, and a borrowed one is refused
    after (borrowed)."""
    first = member["name"].split()[0]
    out = []
    if cursed_lately(member, member.get("said", [])):
        out.append(f"{first} cursed only just now: no curse or oath from {first} this time.")
    return " ".join(out)


def repeat_manner(member: dict) -> str:
    temper = (member.get("temper") or [""])[0]
    R = Q["repeat_manner"]
    return R.get(temper) or R["default"]


# ---------- gestures ----------

# (f344) A tester's Maren had a hand on her sword hilt in half her lines: her only example gesture was the hilt, and the sword her only
# prop. The frames are now shown what is really within reach and how tense the moment is (engine/reach.py), and hands follow those.
HANDS_RULE = ("Hands: what a character does as they speak comes from WITHIN REACH and THE MOMENT, never from habit. Many lines need "
              "nothing, or only a look or a pause. When their hands do something, it is something within reach that fits what is said or "
              "what they were doing: their own work, the thing being talked about, what the place offers. In a tense moment a hand may "
              "rest on a weapon and stay there for as long as the tension lasts; in an easy one, the weapon is left alone.")

GESTURE_RULE = ("Gesture is optional and usually blank. It is written about them, as someone watching would put it ('looks away down the "
                "road'), never as they would say it ('I look away'). Use one only when body language adds meaning the words do not. Use only the "
                "character's body, known possessions, or objects explicitly present in the scene. Never invent furniture, walls, weather, scenery, "
                "or held objects for a gesture. They handle a possession only when the moment gives them a reason to, never as something to do.")
GESTURE_GAP = 3          # a speaker's gesture is shown at most once in this many of their lines
GESTURE_KEEP = 12        # the gestures remembered for each speaker, for the whole save

CARRY = {"fighter": "a sword, a shield, a pack", "archer": "a bow and a quiver, a pack", "priest": "a mace, a holy symbol, a pack",
         "rogue": "a pair of daggers, a pack", "mage": "a staff, a satchel of reagents"}


def carried(member: dict | None) -> str:
    if member is None:
        return "a greatsword on your back, plate armour, a pack"
    return CARRY.get(member.get("role", ""), "a weapon, a pack") + ", the clothes and armour they travel in"


def scene_props(member: dict | None, place) -> str:
    """What a gesture may use: the speaker's body, what they carry, and what the place is given as having. Nothing else exists for it."""
    here = list(getattr(place, "visible", []) or [])[:3]          # enough to lean on or look at; the whole place description is not for a gesture
    return (f"FOR A GESTURE ONLY - WHAT THEY CARRY: {carried(member)}. WHAT IS HERE: " + ("; ".join(here) if here else "nothing in particular") + ".")


GESTURE_SHARED = 4      # how many of each other person's latest gestures also count: three people adjusting the same strap is one gesture


def gesture_state(holder: dict, others: list[dict] | None = None) -> dict:
    """What a new gesture is checked against: this speaker's own, and the latest of everyone else present (by meaning, without the name)."""
    theirs = [bare_gesture(g, o.get("name", "")) for o in (others or []) if o is not holder for g in o.get("gestured", [])[-GESTURE_SHARED:] if g.strip()]
    return {"gestures": list(holder.get("gestured", [])) + theirs, "gesture_now": holder.get("since_gesture", GESTURE_GAP) >= GESTURE_GAP}


def leaned_on(holder: dict) -> str:
    """The gestures this speaker has used lately, so the model does not reach for them again."""
    seen = list(dict.fromkeys(bare_gesture(g) for g in reversed(holder.get("gestured", [])) if g.strip()))[:5]
    return ("GESTURES ALREADY USED BY THEM (never repeat one of these): " + "; ".join(seen)) if seen else ""


def keep_gesture(gesture: str, state: dict, name: str = "") -> str:
    """The gesture if it may be shown now, else '': none too soon after the last, none too long or with speech in it, none like one they
    have already made. A bad gesture is dropped, never a reason to throw away the words."""
    g = " ".join((gesture or "").split()).strip().rstrip(".")
    if not g or not state.get("gesture_now", True):
        return ""
    if len(g.split()) > 15 or '"' in g or "*" in g or "\u201c" in g:
        return ""
    if not re.search(r"[A-Za-z]{3,}", g):                       # 'u.' is not a gesture; 'shrugs' is
        return ""
    if re.search(r"\bI\b|\b[Mm]y\b|\bme\b|\bmyself\b", g):               # written as 'I turn my head': it would read 'Isel i turn my head'
        return ""
    if gesture_ok(g, state.get("gestures", []), name):
        return ""
    return g


def note_line(holder: dict, gesture: str) -> None:
    """After a line: remember the gesture, or count a line without one."""
    if gesture and gesture.strip():
        log = holder.setdefault("gestured", [])
        log.append(" ".join(gesture.split())[:120])
        del log[:-GESTURE_KEEP]
        holder["since_gesture"] = 0
    else:
        holder["since_gesture"] = holder.get("since_gesture", GESTURE_GAP) + 1


def gesture_ok(gesture: str, recent: list[str], name: str = "") -> str:
    """Why a gesture repeats one they have made, or ''."""
    g = " ".join((gesture or "").split())
    if not g:
        return ""
    if '"' in g or "*" in g or "\u201c" in g:
        return "a gesture is what the body does: no speech, no asterisks"
    from llm import embed
    import config
    olds = [bare_gesture(o, name) for o in recent[-GESTURE_KEEP:] if o.strip()]
    sims = embed.whole(bare_gesture(g, name), olds)
    if sims is not None:
        return "they did that very thing before: a different gesture, or none" if sims and max(sims) >= config.SIM_GESTURE else ""
    words = lambda t: {w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in {"his", "her", "their", "the", "and", "with", "him"}}
    mine = words(bare_gesture(g, name))
    for old in olds:
        o = words(old)
        if mine and o and len(mine & o) / min(len(mine), len(o)) >= 0.75:
            return "they did that very thing before: a different gesture, or none"
    return ""


def bare_gesture(g: str, name: str = "") -> str:
    """A gesture without who does it: 'He leans on the wall.' and 'Bram leans on the wall' are the same gesture. Only a pronoun or the
    speaker's own name is taken off, never a word that happens to start with a capital ('Looks toward the sun' keeps its verb)."""
    g = " ".join((g or "").split()).strip().rstrip(".")
    names = [n for n in ([name, name.split()[0]] if name else []) if n]
    for n in sorted(names, key=len, reverse=True):
        if g.lower().startswith(n.lower() + " "):
            return g[len(n) + 1:]
    m = re.match(r"^(he|she|they|it)\s+", g, re.I)
    return g[m.end():] if m else g


def shown(speech: str, gesture: str, name: str) -> str:
    """Speech with its gesture before it, as one block under the speaker's name."""
    g = bare_gesture(" ".join((gesture or "").split()).rstrip("."), name)
    if not g:
        return speech
    first = name.split()[0]
    g = f"{first} {g[0].lower()}{g[1:]}"
    return f"({g}.)\n{speech}" if speech else f"({g}.)"


# ---------- how they speak, as behaviour ----------

def blueprint(member: dict, rng: random.Random | None = None) -> list[str]:
    """How this person speaks, as things they do: two lines from their first temperament, one from their second, minus any line their own
    voice quirk contradicts (the quirk always wins). With rng, which of a temperament's lines appear changes from reply to reply; without,
    the first ones (for writing about them)."""
    q = member.get("quirks") or {}
    voice = q.get("voice", "")
    out = []
    for n, t in zip((2, 1), (member.get("temper") or [])[:2]):
        lines = [b["say"] for b in Q["blueprints"].get(t, []) if voice not in b.get("not_with", []) and b["say"] not in out]
        out += (rng.sample(lines, min(n, len(lines))) if rng else lines[:n])
    return out


def style_block() -> str:
    return ("DIALOGUE STYLE:\n" + "\n".join(f"- {r}" for r in Q["style_rules"]) +
            "\nWHAT YOU MAY AND MAY NOT INVENT:\n" + "\n".join(f"- {r}" for r in Q["invention_rules"]))


# ---------- what they feel and do not say ----------

def subtext(member: dict, situation: str) -> str:
    table = Q["subtext"].get(situation)
    if not table:
        return ""
    temper = (member.get("temper") or [""])[0]
    return table.get(temper) or table.get("default", "")


# ---------- small personal details ----------

def detail_subjects(member: dict, rng: random.Random) -> list[str]:
    """The five subjects for a hire's details: their upbringing, then four rolled from the pool, kept so a rewrite asks the same."""
    if not member.get("detail_kinds"):
        member["detail_kinds"] = [Q["detail_first"]] + rng.sample(list(Q["detail_kinds"]), 4)
    return member["detail_kinds"]


def secret_themes(member: dict) -> list[str]:
    return list(Q.get("secret_themes", {}).get(member.get("motive", ""), []))


def details_request(member: dict, core: str | None = None, taken: list[str] | None = None) -> str:
    """The seed for writing who they are: a little to draw on, a little to stay consistent with, and nothing else. (The whole character
    sheet, habits and all, made every detail an echo of the rest.) `core` is ignored; kept so old callers still work."""
    from engine import party as rules, voice_profile
    sp = member.get("speech") or {}
    fam, home = voice_profile.family(member), voice_profile.culture(member).get("home", "")
    temper = [rules.P["temperaments"][t]["say"] for t in member.get("temper", []) if t in rules.P["temperaments"]]
    inspire = [f"a hired {member.get('role', 'adventurer')}, {member.get('blurb', '')}".rstrip(", ")]
    if sp.get("people"):
        inspire.append(f"{'an' if sp['people'][0] in 'aeiou' else 'a'} {sp['people'].replace('_', '-')}" + (f", raised in {home}" if home else ""))
    if fam:
        inspire.append(f"their family were {fam}")
    if temper:
        inspire.append("by temperament: " + "; ".join(temper))
    consistent = []
    mt = rules.P["motives"].get(member.get("motive", ""), "")
    if mt:
        consistent.append(f"underneath it all, they {mt.replace('wants', 'want')}")
    if member.get("line"):
        consistent.append(f"they {member['line']}")
    themes = secret_themes(member)
    subjects = member.get("detail_kinds") or [Q["detail_first"]] + list(Q["detail_kinds"])[:4]
    return ("WHO THEY ARE: " + member["name"] + "." +
            "\nINSPIRATION:\n" + "\n".join(f"  - {t}" for t in inspire) +
            ("\nFOR CONSISTENCY ONLY:\n" + "\n".join(f"  - {t}" for t in consistent) if consistent else "") +
            "\nSUBJECTS, one detail each, in this order:\n" + "\n".join(f"  {i + 1}. {k}" for i, k in enumerate(subjects)) +
            ("\nSECRET THEMES, one secret each:\n" + "\n".join(f"  {i + 1}. {k}" for i, k in enumerate(themes)) if themes else "") +
            ("\nALREADY TAKEN BY OTHERS (write nothing like these):\n" + "\n".join(f"  - {t}" for t in taken) if taken else ""))
