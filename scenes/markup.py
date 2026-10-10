"""Player markup: *asterisks* mark actions, "quotes" mark speech. Plain text is read as usual."""

import re

PATTERN = re.compile(r'\*([^*]+)\*|"([^"]+)"|“([^”]+)”')


def segments(text: str) -> list[tuple[str, str]]:
    """[('action', ...), ('speech', ...), ('plain', ...)] in order."""
    out, pos = [], 0
    for m in PATTERN.finditer(text):
        before = text[pos:m.start()].strip(" .,;")
        if before:
            out.append(("plain", before))
        if m.group(1):
            out.append(("action", m.group(1).strip()))
        else:
            out.append(("speech", (m.group(2) or m.group(3)).strip()))
        pos = m.end()
    rest = text[pos:].strip(" .,;")
    if rest:
        out.append(("plain", rest))
    return out


def has_markup(text: str) -> bool:
    return bool(PATTERN.search(text))


def describe(text: str) -> str:
    """A line for the reader spelling out what is action and what is speech."""
    parts = []
    for kind, part in segments(text):
        label = {"action": "ACTION (do it, never say it)", "speech": "SPOKEN ALOUD", "plain": "PLAIN"}[kind]
        parts.append(f"  {label}: {part}")
    return "\n".join(parts)


def actions_in(text: str) -> list[str]:
    return [p for k, p in segments(text) if k == "action"]


def scrub_speech(speech: str, text: str) -> str:
    """Remove anything the player marked as an action from words someone will hear."""
    for act in actions_in(text):
        speech = speech.replace(f"*{act}*", "").replace(act, "")
    return re.sub(r"\s{2,}", " ", speech).strip(" .,;") or ""


_NAME_SKIP = {"the", "of", "von", "van", "de", "del", "la", "le", "and"}


def hide_names(text: str, npcs) -> str:
    """Swap the real name of anyone the player has not been told for how the player knows them, so narration never gives it away."""
    if not text:
        return text
    for n in npcs:
        if getattr(n, "name_known_to_player", True) or not n.name:
            continue
        label = n.label()
        parts = [p for p in re.split(r"\s+", n.name.strip()) if len(p) >= 3 and p.lower() not in _NAME_SKIP]
        for token in sorted({n.name.strip(), *parts}, key=len, reverse=True):
            pattern = r"(?<![\w'])" + re.escape(token) + r"(?![\w])"

            def swap(m, label=label):
                start = m.start()
                lead = text_before(m.string, start)
                return label[:1].upper() + label[1:] if lead in ("", ".", "!", "?", '"', "\n") else label
            text = re.sub(pattern, swap, text)
    return text


def text_before(s: str, i: int) -> str:
    """The last non-space character before position i ('' at the start)."""
    j = i - 1
    while j >= 0 and s[j] in " \t":
        j -= 1
    return s[j] if j >= 0 else ""
