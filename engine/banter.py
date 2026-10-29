"""People of the world talking to each other. The engine says who, where and why; the model writes the lines; this module checks them
and supplies the written lines when the model fails."""
from __future__ import annotations

import re
from pathlib import Path

import yaml

from engine import mentor

B = yaml.safe_load((Path(__file__).resolve().parent.parent / "data" / "world" / "banter.yaml").read_text(encoding="utf-8"))

_COLD = re.compile(r"\b(cold|rude|curt|surly|sour|brusque|gruff|snappish|sullen|dismissive|abrasive|hostile|bitter|haughty|short-tempered|irritable|contemptuous|bored|unfriendly|impatient|grumpy)\b")
_WARM = re.compile(r"\b(warm|kind|friendly|cheerful|gentle|welcoming|generous|genial|affable|patient|helpful|cordial|gracious|jovial|sunny|caring)\b")


MANNER_ABOUT = {"warm": "a warm, kind, friendly and welcoming person who is glad to help",
                "cold": "a cold, rude, curt and dismissive person who is impatient with others"}


def manner(npc) -> str:
    """How the clerk (or anyone) comes across, read from what the world wrote about them: 'warm', 'cold' or 'neutral'. By meaning when the
    helper model is there, else by words."""
    text = " ".join([getattr(npc, "personality", ""), getattr(npc, "voice", ""), getattr(npc, "mood", ""), " ".join(getattr(npc, "traits", []) or [])]).lower()
    from llm import embed
    sims = embed.whole(text, [MANNER_ABOUT["warm"], MANNER_ABOUT["cold"]]) if text.strip() else None
    if sims:
        warm, cold = sims
        if abs(warm - cold) < 0.03:
            return "neutral"
        return "warm" if warm > cold else "cold"
    cold, warm = len(_COLD.findall(text)), len(_WARM.findall(text))
    if cold > warm:
        return "cold"
    if warm > cold:
        return "warm"
    return "neutral"


def near_speaker(name: str, speakers: dict[str, str]) -> str:
    """(f382) The allowed speaker a misspelt or shortened name means ('Thavathiel Liaror', 'Deth'), or ''. Sending it back cost a second
    call, and the second answer was the worse one: the f375 night's companions spoke a broken line on exactly such a retry."""
    import difflib
    key = " ".join(name.strip().lower().rstrip(":").split())
    if not key:
        return ""
    firsts = {}
    for low, full in speakers.items():
        firsts.setdefault(low.split()[0], []).append(full)
    if len(firsts.get(key.split()[0], [])) == 1 and (len(key.split()) == 1 or difflib.SequenceMatcher(None, key, firsts[key.split()[0]][0].lower()).ratio() >= 0.75):
        return firsts[key.split()[0]][0]
    close = difflib.get_close_matches(key, list(speakers), n=2, cutoff=0.85)
    return speakers[close[0]] if len(close) == 1 else ""


def echoes(text: str, heard: list[str]) -> str:
    """(f382) A line someone else said just now that this one says again, or '': two companions greeted the player, and both said 'Morning.'"""
    norm = lambda s: " ".join(re.findall(r"[a-z']+", (s or "").lower()))
    t = norm(text)
    for h in [h for h in heard if h and h.strip()][-4:]:
        if t and t == norm(h):
            return h[:60]
    return repeats(text, heard)


HOLDING = re.compile(r"\bI(?:'m| am|'ve| have)?\s+(?:got |have |hold |holding |grip |gripping |clutch |clutching )"
                     r"(?:[a-z']+\s+){0,3}?(?:my|this|the|a|our)\s+(?:[a-z]+\s+)?(staff|bow|sword|mace|dagger|daggers|satchel|shield|blade|axe|spear|"
                     r"quiver|pack|holy symbol|symbol|crossbow|hammer|lute|knife|cloak|wand)\b", re.I)


def holding_talk(text: str, said: str = "") -> str:
    """(f386) A line that tells what the speaker is holding ('I have my staff gripped tight', 'I am holding this shield steady'), when
    nobody asked about it: the thing held, else ''. One companion said it five turns running; what is held shows in a gesture or not at
    all."""
    m = HOLDING.search(text or "")
    if not m or re.search(rf"\b{re.escape(m.group(1))}\b", said or "", re.I):
        return ""
    return m.group(1)


def check_exchange(ex, ctx: dict) -> str:
    """Why an exchange can't be used, or ''. Names are fixed to the allowed ones as written, and nothing new is added."""
    speakers = {s.lower(): s for s in ctx.get("speakers", [])}
    silent_ok = set(ctx.get("silent_ok", ()))            # those this moment hit hard enough that a word, or nothing, is their answer
    lo, hi = ctx.get("lines", (2, 6))
    if not lo <= len(ex.lines) <= hi:
        return f"write {lo} to {hi} lines of dialogue (you wrote {len(ex.lines)})"
    for ln in ex.lines:
        who = speakers.get(ln.speaker.strip().lower().rstrip(":")) or near_speaker(ln.speaker, speakers)
        if not who:
            return f"speaker must be one of: {', '.join(speakers.values())}"
        ln.speaker = who
        ln.text = " ".join(ln.text.split()).strip('"“”')
        if not re.search(r"[A-Za-z]", ln.text) or re.fullmatch(r"[(\[]?\s*(silence|silent|says nothing|nothing|no (verbal )?(response|reply|answer))\s*[)\]]?\.?", ln.text, re.I):
            ln.text = ""                                  # '...', '(silence)', 'no verbal response': they say nothing
        if not ln.text:
            if who in silent_ok:
                continue
            return f"{who} must say something" if silent_ok else "a line was empty"
        if "*" in ln.text or '"' in ln.text:
            return "plain speech only: no asterisks and no quotation marks"
        if ln.text.lower().lstrip().startswith(ln.speaker.lower().split()[0] + ":"):
            return "do not begin a line with the speaker's name"
    if not any(l.text for l in ex.lines) and not (silent_ok and all(l.speaker in silent_ok for l in ex.lines)):
        return "someone must say something"
    appearing = {l.speaker for l in ex.lines}
    if ctx.get("all_speak"):                                # everyone chosen reacts; those allowed silence may also stay out of it
        missing = [s for s in speakers.values() if s not in appearing and s not in silent_ok]
        if missing:
            return ("everyone named must speak at least once" if not silent_ok else f"{', '.join(missing)} must say something")
    elif len(appearing) < min(2, len(speakers)) and not silent_ok:
        return "everyone named must speak at least once"
    first = ctx.get("first_speaker")
    if first and ex.lines and ex.lines[0].speaker != first and first not in silent_ok:    # someone struck hard need not open
        return f"{first} speaks first"
    for ln in ex.lines:
        held = holding_talk(ln.text)
        if held:
            return f"{ln.speaker} tells what they are holding ('{held}'): nobody asked; say something else, and let a gesture show it if it matters"
    dead = (ctx.get("must_name") or "").split(",")[0].split()
    if dead and not any(re.search(rf"\b{re.escape(dead[0])}\b", l.text, re.I) for l in ex.lines):
        return (f"this is about {dead[0]}, who died: someone says {dead[0]}'s name. 'They won't be coming back' about no one in "
                "particular could be about anyone")                                  # (f385) a death talked over without the name
    from engine import quirks
    states = {k: dict(v) for k, v in ctx.get("gesture_states", {}).items()}
    kept = 0
    for ln in ex.lines:
        st = states.setdefault(ln.speaker, {"gestures": [], "gesture_now": True})
        silent = not ln.text                                 # a silent line's gesture is the reaction itself: kept past the cap, not counted
        g = quirks.keep_gesture(ln.gesture, dict(st, gesture_now=True) if silent else st, ln.speaker) if (kept < 2 or silent) else ""
        ln.gesture = g
        if g:
            kept += 0 if silent else 1
            st["gestures"] = st.get("gestures", []) + [g]
            st["gesture_now"] = False
    recent = ctx.get("recent", {})
    members = ctx.get("members", {})
    for i, ln in enumerate(ex.lines):
        if not ln.text:
            continue
        said = echoes(ln.text, [l.text for l in ex.lines[:i] if l.speaker != ln.speaker]) if len(ln.text.split()) <= 6 else ""
        if said:                                             # (f382) one person's line said again by the next
            return f"{ln.speaker} says again what was just said ('{said}'): give them their own words"
        hit = repeats(ln.text, recent.get(ln.speaker, []))
        if hit:
            return f"{ln.speaker} has said something very like '{hit}' lately: give them something new to say"
        if ln.speaker in members:
            from engine import quirks
            before = recent.get(ln.speaker, [])[-2:] + [l.text for l in ex.lines[:i] if l.speaker == ln.speaker]
            why = quirks.voice_check(members[ln.speaker], ln.text, ctx.get("player", ""), before) or \
                quirks.borrowed(members[ln.speaker], ln.text, [m for n, m in members.items() if n != ln.speaker])
            if why:
                return f"{ln.speaker}: {why}"
    whole = " ".join(l.text for l in ex.lines).lower()
    material = " ".join(ctx.get("material", [])).lower()
    if set(re.findall(r"\d+", whole)) - (set(re.findall(r"\d+", material)) | mentor.same_figures(material)):
        return "you used a number that is not in the material: use only the figures given"
    if (set(re.findall(r"[a-z]+", whole)) & mentor.NUMBER_WORDS) - (set(re.findall(r"[a-z]+", material)) | mentor.same_figures(material)):
        return "you gave an amount that is not in the material: use only the figures and amounts given"
    if (set(re.findall(r"[a-z]+", whole)) & mentor.BANNED_WORDS) - set(re.findall(r"[a-z]+", material)):
        return "do not talk about a game or its parts"
    return ""


# ---------- saying the same thing twice ----------

STOP = {"the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "for", "with", "is", "are", "was", "were", "be", "it", "that",
        "this", "you", "your", "we", "our", "they", "them", "their", "i", "my", "me", "he", "she", "his", "her", "do", "not", "no", "so",
        "if", "as", "by", "from", "have", "has", "had", "will", "would", "can", "could", "there", "here", "what", "who", "how", "then"}


def grams(text: str, n: int = 4) -> set[tuple[str, ...]]:
    """The distinctive n-word runs in a line: at least one word of four letters or more that is not filler, and not mostly filler."""
    words = re.findall(r"[a-z']+", text.lower())
    out = set()
    for i in range(len(words) - n + 1):
        g = tuple(words[i:i + n])
        if any(len(w) >= 4 and w not in STOP for w in g) and sum(w in STOP for w in g) < n - 1:
            out.add(g)
    return out


def asked_again(text: str, before: list[str]) -> bool:
    """Is the player asking much the same thing they asked lately? Then answering in much the same words is continuity, not repetition.
    By meaning when the helper model is there, else by shared words."""
    from llm import embed
    import config
    sims = embed.whole(text or "", [b for b in before[-4:] if b.strip()])
    if sims is not None:
        return bool(sims) and max(sims) >= config.SIM_ASKED
    norm = lambda t: set(w.split("'")[0] for w in re.findall(r"[a-z']{3,}", (t or "").lower())) - STOP - {"again", "tell", "please"}
    words = norm(text)
    if not words:
        return False
    for old in before[-4:]:
        o = norm(old)
        if o and len(words & o) / len(words | o) >= 0.5:
            return True
    return False


def repeats(text: str, recent: list[str], n: int = 5) -> str:
    """Something in this line that was said in the last few lines, or '': a sentence that means the same as one said lately (by meaning, when
    the helper model is there), else a shared run of n words."""
    recent = [r for r in recent[-4:] if r and r.strip()]
    from llm import embed
    import config
    hit = embed.closest(text, recent)
    if hit is not None:
        return hit[1][:60] if hit[0] >= config.SIM_REPEAT else ""
    mine = grams(text, n)
    if not mine:
        return ""
    for old in recent:
        hit = mine & grams(old, n)
        if hit:
            return " ".join(sorted(hit, key=lambda g: -len(" ".join(g)))[0])
    return ""


def unsaid_rule(recent: list[str], query: str | None = None, k: int = 3) -> str:
    """A line for the request: what they have said lately, so they say something new. With a query, only the lines about the same thing
    as this moment: an off-topic line in the prompt reads to the model as the topic, and the repetition guard still sees every line."""
    recent = [r for r in recent if r.strip()][-6:]
    if query is not None and recent:
        from engine import relevance
        keep = set(relevance.pick(query, recent, k=k))
        recent = [r for r in recent if r in keep]
    if not recent:
        return ""
    return "SAID LATELY BY YOU (say something new; do not reuse these turns of phrase):\n" + "\n".join(f"  - {r[:140]}" for r in recent)


def clerk_fallback(m: str, fee: str) -> list[tuple[str, str]]:
    return [(who, text.format(fee=fee)) for who, text in B["clerk"]["fallback"][m if m in B["clerk"]["fallback"] else "neutral"]]
