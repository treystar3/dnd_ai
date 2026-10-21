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
