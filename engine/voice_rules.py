"""The rules of the voices: stances, frames, refusals, partings, the exemplars. (f375) No length: nobody is told how long to speak."""

import re
from pathlib import Path

import yaml
from core import yamlio

V = yamlio.safe_load((Path(__file__).resolve().parent.parent / "data" / "rules" / "voice.yaml").read_text(encoding="utf-8"))


_REFUSAL = re.compile(r"\b(no\.|i won'?t|i will not|i'?ll not|not (?:for|to) (?:you|strangers|the likes)|nothing (?:for|to) (?:you|say)|get out|"
                      r"leave me|none of your|mind your own|not your (?:business|concern|affair)|i(?:'m| am) not (?:telling|saying|giving)|"
                      r"ask (?:someone|somebody) else|go (?:away|elsewhere)|not (?:another|one more) word|keep (?:it|that) to myself)\b", re.I)


def refuses(speech: str) -> bool:
    """(f347) Do the words refuse: a no, a won't, a mind-your-own? The model's intent says 'refuse' on most ordinary answers."""
    return bool(_REFUSAL.search(speech or ""))


def short_gesture(gesture: str) -> str:
    """(f347) The gesture printed beside bare speech. (f375) Whole, however long: it was cut at its first clause past six words."""
    return " ".join((gesture or "").split()).strip().rstrip(".")


def roll_stance(npc, minutes: int, rng, *, who: str) -> str:
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
        if k == "wary" and _trust(npc, who) >= 50:                   # (f480) wary of this character
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


def _head(spec: dict) -> str:
    return (spec.get("text") or "").split(":")[0].split("{")[0].strip()


def stance_kind(text: str) -> str:
    """(f724) Which stance a talk's line is (voice.yaml stances, by its key; 'none' for no stance): read from the line as it was
    told, by the words before its colon, so a talk kept in a save needs nothing new and a line reworded after the colon is still
    its stance."""
    for k, spec in V.get("stances", {}).items():
        if _head(spec) and (text or "").startswith(_head(spec)):
            return k
    return "none"


def stance_problems(stances: dict | None = None) -> list[str]:
    """(f724) A stance is known again by how its line begins: no two begin alike."""
    S = V.get("stances", {}) if stances is None else stances
    heads = {k: _head(spec) for k, spec in S.items() if _head(spec)}
    return [f"voice.yaml stances.{a}: begins as {b} does, so the two cannot be told apart" for a in heads for b in heads
            if a != b and heads[a].startswith(heads[b])]


def _trust(npc, who: str) -> int:
    from engine import regard
    return regard.of(npc, who).trust


def written_parting(npc, rng, said=(), *, who: str) -> str:
    """(f347) A parting line from the table, by how they are with the character `who` (f480), not one they said lately."""
    trust = _trust(npc, who)
    band = "warm" if trust >= 65 else "plain" if trust >= 45 else "wary"
    opts = [l for l in V.get("partings", {}).get(band, ["Aye."]) if l.lower() not in {s.lower() for s in said}]
    return rng.choice(opts or V.get("partings", {}).get(band, ["Aye."]))


# (f349) A person stopping what they were doing, on the page: the frame's favourite opening, allowed once per person per visit.
PAUSE = re.compile(r"\b(pauses?|pausing|stops?|stopping|halts?|looks? up|glances? up|lifts? (his|her|their) (head|eyes|gaze)|"
                   r"sets? (it|the \w+|down)|straightens?|lowers? the|turns? from)\b")


NARRATION_POOLS = ("grief", "arrival", "night", "interior", "general")    # (f583) the engine's order of preference
SPEECH_POOLS = ("refusal", "gossip", "small_talk")


def pool(kind: str, name: str = "") -> list[str]:
    """(f583) The lines of one pool: kind 'narration' or 'speech' with a pool's name, or 'fight'."""
    ex = V["exemplars"]
    return list(ex["fight"]) if kind == "fight" else list(ex[kind][name])


def draw(lines: list[str], rng, last=(), n: int | None = None) -> list[str]:
    """(f583) n lines of a pool (voice.yaml exemplars draw), in the pool's order, never the same set as the last draw."""
    n = min(n or int(V["exemplars"]["draw"]), len(lines))
    for _ in range(8):
        got = sorted(rng.sample(range(len(lines)), n))
        if {lines[i] for i in got} != set(last) or len(lines) == n:
            return [lines[i] for i in got]
    keep = [i for i, l in enumerate(lines) if l not in set(last)][:1]      # dice that keep landing on it: one new line in, at least
    rest = [i for i in got if i not in keep][:n - len(keep)]
    return [lines[i] for i in sorted(keep + rest)]


def exemplar_block(kind: str, lines: list[str]) -> str:
    """(f347) The voice shown rather than described, as the register of this game; never lines to reuse. (f583) The lines drawn for one
    call, for the end of its request: kind 'narration', 'fight' or 'speech'."""
    if not lines:
        return ""
    head = ("HOW NARRATION SOUNDS HERE (the register of this game; never lines to reuse, and nothing in them is a fact of this moment):"
            if kind == "narration" else
            "HOW A FIGHT SOUNDS HERE (the register of this game; never lines to reuse, and nothing in them is a fact of this fight):"
            if kind == "fight" else
            "HOW PEOPLE SOUND HERE (the register of this game; never lines to reuse, and nothing in them is about you or this moment):")
    return head + "\n" + "\n".join(f"  - {e}" for e in lines)


def pool_problems(ex: dict | None = None) -> list[str]:
    """(f583) The pools, checked at startup: each pool there, with more lines than are drawn (so no two draws in a row are the same),
    and each line in the draft's rules: no dash, no figure, none of the worn seed words or stock phrases."""
    ex = ex if ex is not None else V.get("exemplars", {})
    bad = []
    n = ex.get("draw")
    if not isinstance(n, int) or n < 1:
        return ["voice.yaml exemplars: draw is a whole number of lines, one or more"]
    if not isinstance(ex.get("refusal_trust"), int):
        bad.append("voice.yaml exemplars: refusal_trust is a whole number")
    named = [("narration", p, (ex.get("narration") or {}).get(p)) for p in NARRATION_POOLS] + [("fight", "", ex.get("fight"))] \
        + [("speech", p, (ex.get("speech") or {}).get(p)) for p in SPEECH_POOLS]
    from engine import worn
    from scenes.voice import STALE
    seeds = set(worn.W.get("seed") or [])
    for kind, name, lines in named:
        where = f"voice.yaml exemplars {kind}{(' ' + name) if name else ''}"
        if not isinstance(lines, list) or not all(isinstance(l, str) and l.strip() for l in lines):
            bad.append(f"{where}: a list of lines")
            continue
        if len(lines) <= n:
            bad.append(f"{where}: {len(lines)} lines, more than the {n} drawn are needed so no two draws in a row are the same")
        for l in lines:
            low = l.lower()
            if re.search(r"[\u2013\u2014]| - ", l):
                bad.append(f"{where}: a dash in '{l[:40]}'")
            if re.search(r"\d", l):
                bad.append(f"{where}: a figure in '{l[:40]}'")
            hit = [w for w in re.findall(r"[a-z']+", low) if w in seeds] + [s for s in STALE if s in low]
            if hit:
                bad.append(f"{where}: '{hit[0]}' (worn or stock) in '{l[:40]}'")
    return bad


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
