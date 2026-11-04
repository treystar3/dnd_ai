"""Reading what a player wants to do about their hired party. The model only reads the words."""

SYSTEM = """You read what a player wants to do about hiring or directing adventurers who travel with them. Choose one kind:
  list    - see who is available to hire, ask what adventurers the guild has.
  hire    - take one or more of the listed adventurers on. target is their name, number in the list, role (fighter, archer, priest, rogue, mage), or "all".
  promote - raise one of their hired adventurers to the next guild rank, train them, put their name forward. target is a name or role.
  dismiss - send one or more of their party away or disband it. target is a name, role, or "all".
  hold    - tell the party to wait outside, hang back, stay out of sight, or come in only if there is trouble.
  with    - tell the party to stay close, come along, move in together.
  status  - ask who is in the party.
  none    - it is not about the party (buying, talking to someone, taking a contract, anything else).
Respond only with JSON matching the schema."""


def user(text: str, offered: list[str], members: list[str]) -> str:
    return (f"AVAILABLE TO HIRE: {', '.join(offered) or 'nobody right now'}.\n"
            f"IN THE PLAYER'S PARTY: {', '.join(members) or 'nobody'}.\nTHE PLAYER SAYS: {text}")


from engine.quirks import GESTURE_RULE, Q as _Q, style_block as _style
from engine.voice_rules import exemplar_block as _exemplars
from engine import canon as _canon

TALK_SYSTEM = ("""You are one adventurer the player hired, now travelling with them. You speak only as yourself, in your own words.
You are given WHO YOU ARE, RIGHT NOW, HOW YOU ARE WITH THEM, WHAT YOU REMEMBER and HOW YOU SPEAK. Your temperament shapes how you answer; it is never the subject.
What you talk about comes from what they said, what is happening right now, and what you remember. """ + " ".join(_Q["answer_first"].split()) + """
GESTURE: """ + GESTURE_RULE + """ You may also say nothing and only make a gesture, when that is truer to you; then leave speech empty.
Rules: no game words (level, rank is fine as a guild word; never stats, bond, trust points, percent); speech has no asterisks or quotation marks.
""" + _style() + "\n" + _exemplars("speech") + """
If the player asks something you cannot know, say so in character.
Also return:
  remember: only if this exchange holds something you would genuinely keep (a fact about their life, a promise, a wrong, a kindness), one short
    sentence in your own words, in the first person ("They told me their brother was killed by bandits."). Keep what was said, never that a
    question was asked. Empty for small talk, and empty if you already remember it.
  impression: only if what you think of the player has just changed, one short line of what you think of them now. Otherwise empty.
  they_promised: only if the player promised you something in this message ("I'll pay you double at the next town"): what they promised, in
    a few words. Otherwise empty. It is their word, not yet done.
Whatever specific thing you say about yourself becomes true of you for good, so choose it with care, and never contradict anything given
as true of you.
""" + __import__("llm.prompts", fromlist=["WORLD_RULES"]).WORLD_RULES + """
Respond only with JSON matching the schema: {"speech": "...", "gesture": "", "remember": "", "impression": "", "they_promised": ""}.""")


def talk_prompt(how: str, core: str, relation: str, now: list[str], memories: list[str], recent: list, player: str, text: str, unsaid: str = "",
                notes: str = "", props: str = "", leaned: str = "", subtext: str = "", offers: list[str] | None = None, again: str = "",
                again_how: str = "", fix: str = "", truth_text: str = "", worn: list[str] = (), others: list[str] = (), recalled: str = "",
                open_: list[str] = (), pronoun: str = ""):
    """A hire's request, built from typed parts (engine/prompt.py) so the gateway knows instruction from fact. (f488) In the brief's order:
    first what holds through a talk (who they are, what presses on them, the moment as they know it from the truth layer, the one who hired
    them and what is open between them); then the talk so far; then this line's tail (what it brings to mind, the checks' notes, how they
    speak, last, and the words said to them)."""
    from engine.prompt import Prompt
    talk = "\n".join(f"  {who}: {said}" for who, said in recent) or "  (nothing yet)"
    mem = "\n".join(f"  - {m}" for m in memories) or "  (nothing in particular)"
    right_now = "\n".join(f"  - {x}" for x in now) or "  - nothing presses"
    p = Prompt()
    p.fact(core, "WHO YOU ARE")
    p.fact(right_now, "RIGHT NOW")
    p.fact(truth_text)
    p.fact(f"{player}, the one who hired you" + (f". Speak of them as {pronoun}" if pronoun else "")
           + (f". {', '.join(others)} {'is' if len(others) == 1 else 'are'} someone else: never call {player} by "
              f"{'that name' if len(others) == 1 else 'their names'}" if others else ""), "YOU ARE TALKING WITH")    # (f385) Merris called the player Salith
    p.fact(relation, f"HOW YOU ARE WITH {player.upper()}")
    if open_:                                                                           # (f488) what they hold, always: never by its age
        p.fact("\n".join(f"  - {x}" for x in open_), "WHAT IS OPEN BETWEEN YOU")
    p.history(talk, "WHAT WAS SAID LATELY")
    p.mark_tail()
    p.fact(fix)
    p.fact(again, "ASKED BEFORE")
    p.instruction(again_how)
    p.fact(mem, "WHAT YOU REMEMBER")
    p.fact(recalled, "WHAT THIS BRINGS TO MIND OF YOU")
    p.instruction(subtext)
    p.history(unsaid)
    p.fact(props)
    p.history(leaned)
    p.instruction(how, "HOW YOU SPEAK")
    p.instruction(notes)
    if offers:
        from engine import quirks
        p.material(quirks.material_block(offers), "WORDS YOU MAY USE THIS TIME, AS THEY ARE (only if they fit)")
    if worn:
        p.instruction(", ".join(worn), "WORDS EVERYONE HAS WORN OUT LATELY (find other words)")       # (f349)
    p.fact(text, f"{player.upper()} SAYS TO YOU")
    return p
