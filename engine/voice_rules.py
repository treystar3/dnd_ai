"""The rules of the voices: stances, frames, refusals, partings, the exemplars. (f375) No length: nobody is told how long to speak."""

import re
from pathlib import Path

import yaml

V = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "voice.yaml").read_text(encoding="utf-8"))


_REFUSAL = re.compile(r"\b(no\.|i won'?t|i will not|i'?ll not|not (?:for|to) (?:you|strangers|the likes)|nothing (?:for|to) (?:you|say)|get out|"
                      r"leave me|none of your|mind your own|not your (?:business|concern|affair)|i(?:'m| am) not (?:telling|saying|giving)|"
                      r"ask (?:someone|somebody) else|go (?:away|elsewhere)|not (?:another|one more) word|keep (?:it|that) to myself)\b", re.I)


def refuses(speech: str) -> bool:
    """(f347) Do the words refuse: a no, a won't, a mind-your-own? The model's intent says 'refuse' on most ordinary answers."""
    return bool(_REFUSAL.search(speech or ""))


def short_gesture(gesture: str) -> str:
    """(f347) The gesture printed beside bare speech. (f375) Whole, however long: it was cut at its first clause past six words."""
    return " ".join((gesture or "").split()).strip().rstrip(".")


def roll_stance(npc, minutes: int, rng) -> str:
    """(f347) How this person is for the conversation that is starting, as a plain line for RIGHT NOW YOU ARE, or '' (most talks: they are
    simply themselves). Weights in data/rules/voice.yaml stances; wary needs trust under 50, grievance a concern, after a motive, and
    tired is twice as likely after dark."""
    from engine import clock
    if (getattr(npc, "speech", None) or {}).get("own_voice"):         # (f374) a person written by hand is themselves: their mood is their stance
        return ""
    S = V.get("stances", {})
    opts = {}
    for k, spec in S.items():
        w = spec.get("weight", 0)
        if k == "wary" and getattr(npc, "trust", 50) >= 50:
            continue
        if k == "grievance" and not getattr(npc, "concern", ""):
            continue
        if k == "after" and not getattr(npc, "motive", ""):
            continue
        if k == "busy" and not getattr(npc, "activity", ""):
            continue
        if k == "tired" and clock.is_dark(minutes):
            w *= 2
        if w > 0:
            opts[k] = w
    if not opts:
        return ""
    k = rng.choices(list(opts), weights=list(opts.values()))[0]
    return S[k]["text"].format(activity=(getattr(npc, "activity", "") or "").rstrip("."), concern=getattr(npc, "concern", ""),
                               motive=getattr(npc, "motive", ""))


def written_parting(npc, rng, said=()) -> str:
    """(f347) A parting line from the table, by how they are with the player, not one they said lately."""
    trust = getattr(npc, "trust", 50)
    band = "warm" if trust >= 65 else "plain" if trust >= 45 else "wary"
    opts = [l for l in V.get("partings", {}).get(band, ["Aye."]) if l.lower() not in {s.lower() for s in said}]
    return rng.choice(opts or V.get("partings", {}).get(band, ["Aye."]))


# (f349) A person stopping what they were doing, on the page: the frame's favourite opening, allowed once per person per visit.
PAUSE = re.compile(r"\b(pauses?|pausing|stops?|stopping|halts?|looks? up|glances? up|lifts? (his|her|their) (head|eyes|gaze)|"
                   r"sets? (it|the \w+|down)|straightens?|lowers? the|turns? from)\b")


def exemplar_block(kind: str) -> str:
    """(f347) The voice shown rather than described: a few passages (kind 'passages', for the narrator) or replies (kind 'speech', for
    everyone who speaks) from data/rules/voice.yaml, as the register of this game. Never lines to reuse."""
    ex = V.get("exemplars", {}).get(kind, [])
    if not ex:
        return ""
    head = ("HOW NARRATION SOUNDS HERE (the register of this game; never lines to reuse, and nothing in them is a fact of this moment):"
            if kind == "passages" else
            "HOW A FIGHT SOUNDS HERE (the register of this game; never lines to reuse, and nothing in them is a fact of this fight):"
            if kind == "fight" else
            "HOW PEOPLE SOUND HERE (the register of this game; never lines to reuse, and nothing in them is about you or this moment):")
    return head + "\n" + "\n".join(f"  - {e}" for e in ex)


def mention_once(text: str, words: tuple[str, ...]) -> str:
    """Keep the first sentence that uses any of these words and drop later sentences that use them again
    (a narrator told to open with one breath tends to describe the same breath twice)."""
    import re
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    seen, kept = False, []
    for sentence in parts:
        low = sentence.lower()
        hit = any(w in low for w in words)
        if hit and seen:
            continue
        seen = seen or hit
        kept.append(sentence)
    return " ".join(kept) if kept else text


NOTHING = ("RESULT: nothing was gained, found, changed or finished - the purse, pack and skills are exactly as they were. "
           "Narrate only the attempt, and mention no object, amount or outcome beyond what is stated here.")
ATTEMPT_ONLY = "You make the attempt, but nothing comes of it."
_MONEY = re.compile(r"\b(coins?|gold|silver|copper|purse|pouch|fortune|riches|wealth)\b", re.I)
_GAIN = re.compile(r"\b(heav\w*|weigh\w*|fill\w*|swell\w*|clink\w*|jingl\w*|bulg\w*|spill\w*|pour\w*|appear\w*|materiali[sz]\w*|conjur\w*|"
                   r"blessing|settles? (?:into|in)|lands? in)\b", re.I)
_DONE = re.compile(r"\b(finished|completed|all done|in a blur|in a single (?:heartbeat|instant|moment|breath)|vanished|"
                   r"hundred (?:tasks|jobs)|every (?:task|job))\b", re.I)
_MADE = re.compile(r"\b(torch(?:es)? (?:burn|flare|appear|spring|blaze)|twist\w* (?:\w+ ){0,3}into|conjur\w*|summon\w*)\b", re.I)


def contradicts_nothing(text: str) -> bool:
    """Narration for an attempt that gained nothing should not describe money arriving, work finished or something made."""
    return bool((_MONEY.search(text) and _GAIN.search(text)) or _DONE.search(text) or _MADE.search(text))
