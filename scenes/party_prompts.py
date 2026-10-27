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
You are given WHO YOU ARE, HOW YOU ARE WITH THEM, RIGHT NOW, and WHAT YOU REMEMBER. Your temperament shapes how you answer; it is never the subject.
What you talk about comes from what they said, what is happening right now, and what you remember. """ + " ".join(_Q["answer_first"].split()) + """
GESTURE: """ + GESTURE_RULE + """ You may also say nothing and only make a gesture, when that is truer to you; then leave speech empty.
A reply is one to four short sentences; two short paragraphs at most when there is a lot to say.
Rules: no game words (level, rank is fine as a guild word; never stats, bond, trust points, percent); speech has no asterisks or quotation marks.
""" + _style() + "\n" + _exemplars("speech") + """
If the player asks something you cannot know, say so in character.
Also return:
  remember: only if this exchange holds something you would genuinely keep (a fact about their life, a promise, a wrong, a kindness), one short
    sentence in your own words, in the first person ("They told me their brother was killed by bandits."). Keep what was said, never that a
    question was asked. Empty for small talk, and empty if you already remember it.
  impression: only if what you think of the player has just changed, one short line of what you think of them now. Otherwise empty.
Whatever specific thing you say about yourself becomes true of you for good, so choose it with care, and never contradict anything given
as true of you.
""" + __import__("llm.prompts", fromlist=["WORLD_RULES"]).WORLD_RULES + """
Respond only with JSON matching the schema: {"speech": "...", "gesture": "", "remember": "", "impression": ""}.""")


def talk_request(core: str, relation: str, now: list[str], memories: list[str], recent: list, player: str, text: str, unsaid: str = "",
                 props: str = "", subtext: str = "") -> str:
    talk = "\n".join(f"  {who}: {said}" for who, said in recent) or "  (nothing yet)"
    mem = "\n".join(f"  - {m}" for m in memories) or "  (nothing in particular)"
    right_now = "\n".join(f"  - {x}" for x in now) or "  - nothing presses"
    return (f"WHO YOU ARE: {core}\n\nHOW YOU ARE WITH {player.upper()}: {relation}\n\nRIGHT NOW:\n{right_now}\n\n"
            f"WHAT YOU REMEMBER:\n{mem}\n\n" + (f"{subtext}\n\n" if subtext else "") + (f"{unsaid}\n\n" if unsaid else "") + (f"{props}\n\n" if props else "") +
            f"WHAT WAS SAID LATELY:\n{talk}\n\n{player.upper()} SAYS TO YOU: {text}")


def talk_prompt(how: str, core: str, relation: str, now: list[str], memories: list[str], recent: list, player: str, text: str, unsaid: str = "",
                notes: str = "", props: str = "", leaned: str = "", subtext: str = "", offers: list[str] | None = None, again: str = "",
                again_how: str = "", fix: str = "", truth_text: str = "", worn: list[str] = ()):
    """The same request as talk_request, built from typed parts (engine/prompt.py) so the gateway knows instruction from fact. truth_text is
    their view of the moment from the truth layer (engine/truth.py, f315): where they are, who is here, what the town has, the board."""
    from engine.prompt import Prompt
    talk = "\n".join(f"  {who}: {said}" for who, said in recent) or "  (nothing yet)"
    mem = "\n".join(f"  - {m}" for m in memories) or "  (nothing in particular)"
    right_now = "\n".join(f"  - {x}" for x in now) or "  - nothing presses"
    p = Prompt()
    p.fact(core, "WHO YOU ARE")
    p.instruction(how, "HOW YOU SPEAK")
    p.fact(relation, f"HOW YOU ARE WITH {player.upper()}")
    p.fact(right_now, "RIGHT NOW")
    p.fact(truth_text)
    p.fact(fix)
    p.fact(again, "ASKED BEFORE")
    p.instruction(again_how)
    p.fact(mem, "WHAT YOU REMEMBER")
    p.instruction(subtext)
    p.history(unsaid)
    p.instruction(notes)
    p.fact(props)
    p.history(leaned)
    if offers:
        from engine import quirks
        p.material(quirks.material_block(offers), "WORDS YOU MAY USE THIS TIME, AS THEY ARE (only if they fit)")
    p.history(talk, "WHAT WAS SAID LATELY")
    if worn:
        p.instruction(", ".join(worn), "WORDS EVERYONE HAS WORN OUT LATELY (find other words)")       # (f349)
    p.fact(text, f"{player.upper()} SAYS TO YOU")
    return p
