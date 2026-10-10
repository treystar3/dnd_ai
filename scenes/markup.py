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
