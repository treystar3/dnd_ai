"""The game master's voice, shared by every narrator, and a guard against repetition.

Narration should feel like a live DM at the table: specific, responsive, varied, and never on autopilot.
"""

import re

from llm.gateway import generate
from llm.prompts import WORLD_RULES

DM_VOICE = """You are the game master, running this world live for one player at the table. Speak to them the way a
great DM does: present tense, second person, vivid and specific.
- React to what the player actually said and did, including small touches (marking a tree, a joke, a hesitation).
  Show that it registered.
- Keep it fresh. Never open the way RECENT NARRATION opened, and never reuse its images, phrases or sentence shapes.
  Weather, air and smells are seasoning, not a refrain: mention them only when they change or matter.
- One sharp, concrete detail beats three generic ones. Avoid stock phrases like "the air hangs heavy", "the scent of
  damp earth", "a sense of", "you can't help but", "little do you know".
- Group what happens in parallel ("the rest of them close in around you") instead of walking through each person.
- Let the sentences move with the moment: a short one lands a blow, a turn or a silence; a longer one carries movement. Plain
  words, exact nouns, verbs that act: "the hammer rang", not "his hammer ringing out in a steady cadence". One adjective is
  usually one too many, and two before a noun always are. Never end a sentence on a trailing participle ("..., his gaze
  returning to the road").
- Narrate what changes, not what stands. The room, the weather and what people were doing, once given, are given: after that,
  say what is new.
- Let danger be felt before it lands. When the odds are bad, the world itself should warn the player - numbers,
  movement, the look in a foe's eyes - without you saying "this is dangerous".
- Now and then, not every time, end on a beat that invites the player to act: a sound, an opening, a choice.
- Never contradict the facts you are given, and never add facts that change the situation. The player's gear is exactly what
  you are told they carry: never add a piece, and never name something they lack.

""" + WORLD_RULES + "\n\n" + __import__("engine.voice_rules", fromlist=["exemplar_block"]).exemplar_block("passages") + "\n"

STALE = ["the air hangs heavy", "hangs heavy", "scent of damp earth", "smell of damp earth", "cool morning air",
         "a sense of", "can't help but", "little do you know", "send shivers down", "sends a shiver",
         "nothing has changed", "nothing had changed", "unchanged since", "exactly as it was"]     # a revisit passage that says so after describing a change


def _shingles(text: str, n: int = 5) -> set[str]:
    words = re.findall(r"[a-z']+", text.lower())
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


def stale_phrases(text: str, recent: list[str]) -> list[str]:
    """Phrases of five or more words reused from recent narration, plus known stock phrases."""
    mine = _shingles(text)
    seen = set()
    for r in recent[-4:]:
        seen |= _shingles(r)
    repeats = sorted(mine & seen)
    lower = text.lower()
    return repeats[:6] + [s for s in STALE if s in lower]


_ING_NOUNS = {"nothing", "something", "anything", "everything", "morning", "evening", "thing", "king", "ring", "string", "spring", "wing",
              "sling", "sting", "bring", "ceiling", "building", "during", "sibling", "clothing", "lightning", "wedding", "shilling", "darling",
              "mooring", "bedding", "landing", "footing", "opening", "meaning", "feeling", "being", "living", "dwelling", "lodging", "railing",
              "stocking", "blessing", "warning", "offering", "fling", "cling", "swing", "thing"}
_TAIL = re.compile(r",\s*(?:(?:his|her|their|its|the|a|an|one|each|every|both|all|my|your|our|that|this|those|these)\s+)?(?:[a-z'-]+\s+){0,2}([a-z]+ing)\b[^,]*$")


def participle_tails(text: str) -> list[str]:
    """(f349) The sentences that end on a trailing participle clause (', his gaze returning to the road'): the five-hour run ended one
    sentence in six that way. The DM voice names the habit; this finds it in a draft so the rewrite can be asked to undo it."""
    out = []
    for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()):
        core = s.rstrip(".!?\"'\u201d ").lower()
        m = _TAIL.search(core)
        if m and m.group(1) not in _ING_NOUNS and len(m.group(1)) > 5:
            out.append(s.strip())
    return out


_QUOTE = re.compile(r'["\u201c]([^"\u201d]{8,})["\u201d]')
_MARK = re.compile(r"\[h\d+\]")


def invented_speech(text: str, said: str) -> str:
    """(f384) Words the passage puts in someone's mouth, or '': a quoted line that is not the player's own. The narrator wrote two
    woodcutters' warnings and the player's question to them, and Maren saying Parth was 'just over that rise' while standing in it."""
    mine = set(re.findall(r"[a-z']+", (said or "").lower()))
    for m in _QUOTE.finditer(text or ""):
        q = set(re.findall(r"[a-z']+", m.group(1).lower()))
        if q and len(q & mine) / len(q) < 0.6:
            return m.group(1)[:60]
    return ""


def fresh(task: str, system: str, request: str, schema, recent: list[str], fields=("text",),
          temperature: float = 0.9, max_tokens: int | None = None, context: dict | None = None, worn: list[str] | None = None,
          said: str | None = None):
    """Generate narration; if it repeats recent phrasing or stock phrases, or leans on words the writing has worn out (f349, `worn` from
    the scene's watch), rewrite once with the habit called out. `context` is the schema's validation context (a frame's speaker and the
    others present, f347).

    (f382) No rewrite for sentences ending on a trailing participle, anywhere. It was dropped for frames (f374) and fights (f380) first;
    across the second playthrough and the f375 night warrior it rewrote three passages in four, the rewrites ended as many sentences that
    way as the drafts (a rate of 0.25 to 0.34 either way), and each was a second call before the player could read anything. The DM
    voice still names the habit; participle_tails stays for the LoRA tools, which keep such drafts out of what is learned.

    (f384) said: the player's words, for a passage that may put no words in anyone else's mouth (invented_speech): one that does is
    rewritten. A rewrite that loses a blow's [hN] marker the draft had, or piles them up together, is thrown away and the draft stands:
    its figures would otherwise be printed away from their blows."""
    from engine import worn as _worn
    import config
    max_tokens = max_tokens or config.PROSE_MAX_TOKENS                     # (f375) a ceiling against a runaway, never a length
    result = generate(task, system, request, schema, temperature=temperature, max_tokens=max_tokens, validation_context=context)
    text = " ".join(getattr(result, f, "") or "" for f in fields)
    parts = []
    hits = stale_phrases(text, recent)
    if hits:
        parts.append("REUSED STALE PHRASING. Do not use any of these again: " + "; ".join(f'"{h}"' for h in hits))
    lean = _worn.leaned_on(text, worn or [])
    if len(lean) >= 2:
        parts.append("LEANED ON WORDS YOU HAVE WORN OUT: " + ", ".join(lean) + ". Find other words, or leave the thing unsaid")
    spoken = invented_speech(text, said) if said is not None else ""
    if spoken:
        parts.append(f'PUT WORDS IN SOMEONE\'S MOUTH ("{spoken}"). Nobody speaks in a passage: show what people do, and leave the speaking '
                     "to the game")
    if not parts:
        return result
    nudge = "\n\nYOUR DRAFT " + ". YOUR DRAFT ALSO ".join(parts) + ". Write it fresh, with the same events."
    redo = generate(task, system, request + nudge, schema, temperature=min(1.1, temperature + 0.1), max_tokens=max_tokens, validation_context=context)
    now = " ".join(getattr(redo, f, "") or "" for f in fields)
    (rn, rs), (dn, ds) = _marked(now), _marked(text)
    if rn < dn or rs < ds:                                  # (f384) the draft kept every blow in its own sentence: it stands
        return result
    return redo


def _marked(text: str) -> tuple[int, int]:
    """(f384) How many blow markers a passage keeps, and how many sentences carry one: a rewrite that drops markers, or piles them up
    after its last sentence ('...without drawing blood. [h1] [h2] [h3] [h4]'), prints every figure away from its blow."""
    return (len(_MARK.findall(text or "")), sum(1 for s in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if _MARK.search(s)))
