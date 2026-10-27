"""The party: adventurers the guild sends with you. Pure rules - who is for hire, what they cost, what they fight like.

Rules live in data/rules/party.yaml. The engine decides everything here; the model only voices the scene.
"""

import random
import re
from pathlib import Path

import yaml

from engine import combat

ROOT = Path(__file__).resolve().parent.parent
P = yaml.safe_load((ROOT / "data" / "rules" / "party.yaml").read_text(encoding="utf-8"))


def rank_of(level: int) -> str:
    """The guild rank a character of this level holds (the same level bands as the guild's ranks)."""
    from engine import quests
    for letter, v in quests.G["ranks"].items():
        if v["levels"][0] <= level < v["levels"][1]:
            return letter
    return list(quests.G["ranks"])[-1]


class Shape:
    """A creature-like stand-in so a hireling can be built with the same code as a monster."""
    def __init__(self, member: dict):
        role = P["roles"][member["role"]]
        self.id = member["id"]
        self.name = member["name"]
        self.size, self.category, self.temperament = "Medium", "humanoid", "aggressive"
        self.profile = dict(P["profiles"][role["profile"]])
        self.attacks = list(role["attacks"])
        self.group = (1, 1)


def roster(seed, hall: str, day: int, player_level: int, rank_coins: int, used: list[str]) -> list[dict]:
    """The adventurers free at a hall this week. Same list for the same week; hired ones drop off it."""
    week = day // P["roster_days"]
    rng = random.Random(f"{seed}:party:{hall}:{week}")
    out = []
    roles = list(P["roles"])
    for i in range(P["roster_size"]):
        role = roles[i % len(roles)] if i < len(roles) else rng.choice(roles)
        lo, hi = P["veteran_share"] if rng.random() < P["veteran_chance"] else P["level_share"]
        level = max(1, round(player_level * rng.uniform(lo, hi)))
        from engine import voice_profile
        people = voice_profile.roll_people(rng)
        name = hire_name(people, rng)
        speech = voice_profile.roll(rng, people)
        from engine import voices
        voices.ensure(speech, rng, [o["speech"]["kit"] for o in out])      # (f350) no two on one list sound alike
        out.append({"id": f"{week}-{i}", "name": name, "role": role, "level": level, "rank": rank_of(level),
                    "blurb": rng.choice(P["roles"][role]["blurb"]), "fee": 0, "hall": hall, "people": people, "speech": speech,
                    **roll_personality(rng)})
    rng.shuffle(out)
    for m in out:
        m["fee"] = fee(m, player_level, rank_coins)
    return [m for m in out if f"{m['hall']}:{m['id']}" not in used]


def hire_name(people: str, rng: random.Random, gender: str = "") -> str:
    """A name built from their people's sounds (npc/names.py), the way every resident's is: a first name of the gender rolled here and a
    family name. Never a name from a list."""
    from npc import names
    gender = gender or rng.choice(["male", "female"])
    return f"{names.build(people, gender, rng)} {names.build(people, 'family', rng)}".strip()


def roll_personality(rng: random.Random) -> dict:
    """What a hire is like, rolled once when they appear on the list: one or two temperaments, one want, one line they will not cross."""
    temps = rng.sample(list(P["temperaments"]), rng.choice([1, 2]))
    return {"temper": temps, "motive": rng.choice(list(P["motives"])), "line": rng.choice(P["lines"])}


def rank_fee(rank: str, role: str) -> int:
    """What a hire of this rank and role costs: the same at any level inside the band, rank_step times more for each rank up."""
    from engine import quests
    idx = list(quests.G["ranks"]).index(rank)
    return max(1, round(P["hire_base"] * P["rank_step"] ** idx * P["roles"][role]["fee"]))


def fee(member: dict, player_level: int = 0, rank_coins: int = 0) -> int:
    return rank_fee(member.get("rank") or rank_of(member["level"]), member["role"])


def level_cap(rank: str) -> int | None:
    """The highest level a hire of this rank reaches on their own (None for the top rank)."""
    from engine import quests
    letters = list(quests.G["ranks"])
    if letters.index(rank) == len(letters) - 1:
        return None
    return quests.G["ranks"][rank]["levels"][1] - 1


def sync_levels(party: list[dict], player_level: int) -> list[str]:
    """Bring each hire's level up to where their time with you puts them, no higher than the top of their rank. Returns notes."""
    notes = []
    for m in party:
        if m.get("tutorial") or m.get("npc") or "hired_at" not in m:
            continue
        rank = m.get("rank") or rank_of(m["level"])
        cap = level_cap(rank)
        want = m["base_level"] + int(max(0, player_level - m["hired_at"]) * P["level_pace"])
        want = want if cap is None else min(want, cap)
        if want > m["level"]:
            m["level"] = want
            notes.append(f"{m['name']} has grown stronger: level {want}.")
        was = m.get("capped", False)
        m["capped"] = cap is not None and m["level"] >= cap
        if m["capped"] and not was:
            notes.append(f"{m['name']} has gone as far as {'an' if rank in 'AEFS' else 'a'} {rank}-rank can on their own; they would need to be promoted.")
    return notes


def next_rank(rank: str) -> str | None:
    from engine import quests
    letters = list(quests.G["ranks"])
    i = letters.index(rank)
    return letters[i + 1] if i + 1 < len(letters) else None


def promotion_fee(member: dict) -> int:
    rank = member.get("rank") or rank_of(member["level"])
    nxt = next_rank(rank)
    return max(1, rank_fee(nxt, member["role"]) - rank_fee(rank, member["role"])) if nxt else 0


def promotion_block(member: dict) -> str:
    """Why a hire cannot be promoted yet, or '' if they can."""
    rank = member.get("rank") or rank_of(member["level"])
    if not next_rank(rank):
        return f"{member['name']} already holds the highest rank."
    if not member.get("capped"):
        return f"{member['name']} still has room to grow as a {rank}-rank."
    B = P["bond"]
    names = [t[1] for t in B["tiers"]]
    if names.index(bond_tier(member)) < names.index(B["promote_needs"]):
        return f"{member['name']} does not trust you enough yet to put their name forward."
    if member.get("fights_since", 0) < B["promote_fights"]:
        return f"{member['name']} wants more fights beside you first ({member.get('fights_since', 0)} of {B['promote_fights']})."
    return ""


def promote(member: dict, player_level: int) -> None:
    nxt = next_rank(member.get("rank") or rank_of(member["level"]))
    from engine import quests
    member["rank"] = nxt
    member["level"] = member["base_level"] = max(member["level"] + 1, quests.G["ranks"][nxt]["levels"][0])
    member["hired_at"] = player_level
    member["capped"] = False
    member["fights_since"] = 0
    member["bond"] = member.get("bond", 0) + P["bond"]["promote"]


def bond_tier(member: dict) -> str:
    tier = P["bond"]["tiers"][0][1]
    for floor, name in P["bond"]["tiers"]:
        if member.get("bond", 0) >= floor:
            tier = name
    return tier


# Everything kept on a hire, by what it is. Tools that copy, swap or reset a hire (tools/live_check.py) take their lists from here, and
# party_perm_test fails on any field not in one of them, so a new field is decided about once, where it is made.
WHO = ("temper", "motive", "line", "quirks", "details", "secrets", "detail_kinds", "detail_weights", "people", "speech")   # who they are: rolled or written once
TALK = ("said", "talk", "memories", "impression", "gestured", "talked_day", "convo", "topics_used", "raised", "mood", "mood_at", "since_gesture", "heavy_at",
        "_culture_key", "_culture", "banter_at", "started_at", "mood_for", "hit_by")  # what play has given them
STANDING = ("id", "name", "pronoun", "blurb", "role", "level", "rank", "permanent", "base_level", "hired_at", "hired_day", "bond", "fights_since", "fights_total",
            "warned", "hp_frac", "hp_at", "capped", "hungover_until", "pocketed", "bragged_day", "down_fate")   # from the roster, and the engine's own numbers


def lived_keys() -> tuple:
    """What a hire has accumulated in play: what they said and heard, and every lasting fact they have stated (engine/canon.py)."""
    from engine import canon
    return TALK + tuple(canon.HELD)


def unclassified(member: dict) -> list[str]:
    return sorted(k for k in member if k not in WHO + STANDING + lived_keys())


def new_hire(offer: dict, player_level: int, day: int) -> dict:
    """A roster entry turned into a permanent member of the party."""
    start = P["bond"]["start"] + sum(P["temperaments"][t]["start"] for t in offer.get("temper", []))
    return {"id": offer["id"], "name": offer["name"], "role": offer["role"], "level": offer["level"], "rank": offer["rank"],
            "blurb": offer["blurb"], "temper": list(offer.get("temper", [])), "motive": offer.get("motive", ""), "line": offer.get("line", ""),
            "people": offer.get("people", "human"), **({"speech": dict(offer["speech"])} if offer.get("speech") else {}),
            "permanent": True, "base_level": offer["level"], "hired_at": player_level, "hired_day": day, "bond": start,
            "fights_since": 0, "warned": False, "hp_frac": 1.0, "hp_at": 0,
            "capped": level_cap(offer["rank"]) is not None and offer["level"] >= level_cap(offer["rank"]),
            "memories": [{"day": day, "text": "I took their coin at the guild hall and signed on.", "weight": 2, "count": 1}],
            "impression": "Has only just met the player and is reserving judgment.", "mood": "", "mood_at": 0, "said": []}


def health_now(member: dict, minutes: int) -> float:
    """How much of their health a hire has: wounds mend with time."""
    return min(1.0, member.get("hp_frac", 1.0) + max(0, minutes - member.get("hp_at", 0)) / P["heal_minutes"])


def after_fight(party_survivors: list[tuple[dict, float]], won: bool, hard: bool, minutes: int) -> list[str]:
    """Fight over. Each (member, health fraction left): remember the wounds, and move their trust. Returns notes."""
    B, notes = P["bond"], []
    day = minutes // 1440
    for m, frac in party_survivors:
        m["hp_frac"], m["hp_at"] = max(0.05, frac), minutes
        if frac < B["battered_below"]:
            m["bond"] = m.get("bond", 0) + B["battered"]
            set_mood(m, "sore, and quieter than usual, after coming out of the last fight badly hurt", minutes)
            remember(m, day, "I came out of a fight badly hurt" + (" and had to be carried out of it" if frac <= 0.05 else "") + ".", 3)
        elif won:
            m["bond"] = m.get("bond", 0) + B["win"] + (B["hard_win"] if hard else 0)
            if hard:
                set_mood(m, "flush and a little loud after a hard fight won", minutes)
                remember(m, day, "We won a hard fight together, against something as strong as they are or stronger.", 2, key="hard_win")
        if won:
            m["fights_since"] = m.get("fights_since", 0) + 1
        if m.get("bond", 0) <= B["warn_at"] and not m.get("warned"):
            m["warned"] = True
            notes.append(f"{m['name']} says it plainly: they are not sure this is worth it, and you should look to them more.")
            m["impression"] = "Thinks the player leaves them to take the hits, and has said so."
            remember(m, day, "I told them plainly that this might not be worth it.", 3)
        elif m.get("bond", 0) > B["warn_at"] + 8:
            m["warned"] = False
    return notes


def fighter(member: dict, fid: str | None = None, minutes: int | None = None) -> combat.Fighter:
    if member.get("sheet") == "maren":                  # a named companion with a sheet of her own
        from engine import mentor
        f = mentor.maren_fighter()
        f.id = fid or f"ally_{member['id']}"
        return f
    f = combat.fighter_from_creature(Shape(member), member["level"], "normal", fid or f"ally_{member['id']}", member["name"], "near")
    f.side = "ally"
    f.ally_role = member["role"]
    f.hold = combat.hold_of(f.reach, role=member["role"])
    q = member.get("quirks") or {}
    f.flaw = q.get("flaw", "")
    if f.flaw == "drinker" and minutes is not None and minutes < member.get("hungover_until", -1):
        from engine import quirks
        f.weapon_damage *= quirks.Q["flaws"]["drinker"]["damage_mult"]
    if minutes is not None and member.get("permanent"):
        f.hp = max(1.0, f.max_hp * health_now(member, minutes))
    return f


def is_scout(member: dict) -> bool:
    return bool(P["roles"][member["role"]].get("scout"))


def sneak_penalty(party: list[dict]) -> int:
    return P["stealth"]["sneak_each"] * sum(1 for m in party if not is_scout(m))


def scout_bonus(party: list[dict]) -> int:
    return min(P["stealth"]["scout_cap"], P["stealth"]["scout_each"] * sum(1 for m in party if is_scout(m)))


# ---------- a hire's social life: what they remember, how they feel, what they think of you, what they have said lately ----------

MEMORY_KEEP = 8
MOOD_MINUTES = 1440


def remember(member: dict, day: int, text: str, weight: int = 1, key: str = "", kind: str = "event") -> None:
    """One short thing worth keeping, in their own words. A memory with the same key is the same memory, updated; one that means the same as
    a memory they already hold makes that one stronger instead of sitting beside it. The newest are kept, and the heaviest survive."""
    text = " ".join(str(text).split())[:180]
    if not text:
        return
    mem = member.setdefault("memories", [])
    if key:
        for x in mem:
            if x.get("key") == key:
                x.update(text=text, day=day, weight=max(x.get("weight", 1), int(weight)))
                return
    same = _same_memory(text, [x["text"] for x in mem if not x.get("key")])
    if same is not None:
        x = [x for x in mem if not x.get("key")][same]
        if x.get("kind", "event") == "event" and kind == "event":
            x["count"] = x.get("count", 1) + 1              # a thing that happened again; a fact told again is still one fact
        x["day"] = day
        x["weight"] = max(x.get("weight", 1), int(weight))
        return
    mem.append({"day": day, "text": text, "weight": int(weight), "count": 1, "kind": kind, **({"key": key} if key else {})})
    while len(mem) > MEMORY_KEEP:
        old = mem[:len(mem) // 2]
        mem.remove(min(old, key=lambda x: (x["weight"], x["day"])))


def _same_memory(text: str, olds: list[str]) -> int | None:
    """The index of a memory that means the same as this text, or None: by meaning when the helper model is there, else by shared words."""
    if not olds:
        return None
    from llm import embed
    import config
    sims = embed.whole(text, olds)
    if sims is not None:
        best = max(range(len(sims)), key=lambda i: sims[i])
        return best if sims[best] >= config.SIM_ASKED else None
    norm = lambda t: set(w for w in re.findall(r"[a-z]{3,}", t.lower()) if w not in {"the", "and", "they", "them", "their", "that", "with"})
    mine = norm(text)
    for i, o in enumerate(olds):
        theirs = norm(o)
        if mine and theirs and len(mine & theirs) / len(mine | theirs) >= 0.6:
            return i
    return None


def pick_memories(member: dict, text: str = "", n: int = 3, day: int | None = None) -> list[str]:
    """The memories this moment is about: those close in meaning to what was said, closest first, up to n. With nothing relevant, only the
    newest, and only if it is from today (the conversation is still warm). Unrelated memories in a prompt become topics."""
    mem = member.get("memories", [])
    if not mem:
        return []
    picks = []
    if text:
        from engine import relevance
        for t in relevance.pick(text, [x["text"] for x in mem], k=n):
            picks.append(next(x for x in mem if x["text"] == t))
    if not picks and day is not None and mem[-1].get("day") == day:
        picks = [mem[-1]]
    picks.sort(key=lambda x: x["day"])
    return [f"day {x['day']}: {x['text']}" + (" (more than once)" if x.get("count", 1) > 1 and x.get("kind", "event") == "event" else "") for x in picks]


def set_mood(member: dict, text: str, minutes: int, lasts: int | None = None) -> None:
    """A mood, for a day unless it is given longer (lasts, in minutes: what a devastating moment leaves lasts days). A lighter mood never
    cuts a longer one short."""
    if lasts is None and member.get("mood_for") and mood_now(member, minutes):
        return
    member["mood"], member["mood_at"] = " ".join(str(text).split())[:120], minutes
    if lasts:
        member["mood_for"] = lasts
    else:
        member.pop("mood_for", None)


def mood_now(member: dict, minutes: int) -> str:
    """A mood fades after a day, or after however long it was given."""
    if member.get("mood") and minutes - member.get("mood_at", 0) <= member.get("mood_for", MOOD_MINUTES):
        return member["mood"]
    return ""


def said(member: dict, text: str) -> None:
    """What they have said lately, so they do not say it again."""
    log = member.setdefault("said", [])
    text = re.sub(r"^\(.*?\)\s*", "", str(text).strip())           # the gesture shown before it is not something said
    log.append(" ".join(text.split())[:300])
    del log[:-10]


def pair_key(a: str, b: str) -> str:
    return "|".join(sorted((str(a), str(b))))


def relation_words(score: int) -> str:
    if score >= 40:
        return "close as kin"
    if score >= 15:
        return "easy with each other"
    if score <= -15:
        return "grating on each other"
    return "still getting the measure of each other"


def gestured(member: dict, text: str) -> None:
    """What they did lately, so they do not do the same thing every time."""
    if text and text.strip():
        log = member.setdefault("gestured", [])
        log.append(" ".join(text.split())[:120])
        del log[:-6]
