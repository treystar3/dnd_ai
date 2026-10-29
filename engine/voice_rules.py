"""How long the narrator and the people of the world should speak. The engine decides; the model fills the space."""

import re
from pathlib import Path

import yaml

V = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "voice.yaml").read_text(encoding="utf-8"))


def narration(weight: str | None) -> dict:
    return V["narration"].get(weight or "normal", V["narration"]["normal"])


def npc_level(npc, player_text: str, convo: list, extra: list, first: bool) -> str:
    """short / medium / long, from what the moment asks for."""
    P = V["points"]
    low = player_text.lower()
    score = 0
    score += len(player_text.split()) >= P["long_player_message_words"]
    score += any(w in low for w in P["open_question"])
    score += min(2, sum(w in low for w in P["weighty"]))
    score += first
    score += npc.trust >= P["trust"]
    score += len(convo) >= P["long_conversation_turns"] * 2
    score += bool(extra) and any("quest" in str(e).lower() or "work" in str(e).lower() for e in extra)
    quiet = any(t in V["quiet_traits"] for t in getattr(npc, "traits", []))
    level = "short" if score == 0 else "medium" if score <= 2 else "long"
    if quiet and level == "long":
        level = "medium"
    return level


def npc(level: str) -> dict:
    return V["npc"][level]


_REFUSAL = re.compile(r"\b(no\.|i won'?t|i will not|i'?ll not|not (?:for|to) (?:you|strangers|the likes)|nothing (?:for|to) (?:you|say)|get out|"
                      r"leave me|none of your|mind your own|not your (?:business|concern|affair)|i(?:'m| am) not (?:telling|saying|giving)|"
                      r"ask (?:someone|somebody) else|go (?:away|elsewhere)|not (?:another|one more) word|keep (?:it|that) to myself)\b", re.I)


def refuses(speech: str) -> bool:
    """(f347) Do the words refuse: a no, a won't, a mind-your-own? The model's intent says 'refuse' on most ordinary answers."""
    return bool(_REFUSAL.search(speech or ""))


def short_gesture(gesture: str) -> str:
    """(f347) A gesture short enough to print beside bare speech: kept whole when it is within gesture_words, cut at its first clause when
    that is, otherwise dropped. 'wipes her hands on her apron' stays; 'glances at the door, then back to the ledger with a sigh' becomes
    'glances at the door'; 'gives a slow, deliberate nod' is never cut inside its pair of adjectives."""
    g = " ".join((gesture or "").split()).strip().rstrip(".")
    if not g:
        return ""
    cap = V.get("gesture_words", 6)
    if len(g.split()) <= cap:
        return g
    head = re.split(r";|, then |, and |, before |, while |, as |,\s+(?=(?:turning|looking|glancing|leaning|resting|setting|wiping|nodding|"
                    r"shaking|pulling|returning|going|letting|watching|reaching|folding|crossing|rubbing|brushing|picking|putting|"
                    r"settling|straightening|dropping|lowering|raising|lifting|leaving|smiling|laughing|frowning|sighing|squinting|pausing|"
                    r"stepping|moving|tucking|tapping|giving|holding|keeping|casting|shifting|scratching|running|waving|pointing|"
                    r"sweeping|wrapping|tightening|loosening|closing|opening)\b)| and then | and | then | before | while | as ", g, maxsplit=1)[0].strip()
    return head if head and len(head.split()) <= cap else ""


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
