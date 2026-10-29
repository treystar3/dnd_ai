"""(f347) Farewells in two words. A plain goodbye is recognised before the model reads the line (scenes/world.py farewell_intercept), and the
person it is said to answers with one short parting line through a small call: no frame, a written line if the model fails. An hour's
transcript had a goodbye read as talk a third of the time and answered with a full reply and a frame, and eight farewells wishing safe
travels; this is the moment for two words, and the engine marks it as one.

is_goodbye() takes only a line that is nothing but a goodbye (with its thanks and its filler): a goodbye that carries one more question
("thanks, but first: where is the mill?") is for the interpreter, as before."""
from __future__ import annotations

import re
import config

_FILLER = (r"(?:ok(?:ay)?|alright|all right|right|well|then|thanks|thank you|many thanks|much obliged|cheers|good|very well|i see|"
           r"i understand|understood|fair enough|fine|good to know|noted|anyway|and|so|now|again|friend|sir|ma'am|madam|miss|master|"
           r"mistress|my friend|to you|too|as well|for now|for your (?:help|time|trouble|kindness)|"
           r"thank (?:him|her|them)(?: for (?:his|her|their) (?:time|help|trouble))?|"
           r"for the (?:help|time|trouble|information|news|warning|directions|advice|drink|meal|work))")
_GOODBYE = (r"(?:good ?bye|bye|farewell|fare ?well|fare thee well|good (?:day|night|evening|morning)(?: to you)?|take care|be well|"
            r"keep well|stay safe|safe travels|see you(?: around| later| again| soon)?|until next time|till next time|so long|"
            r"i(?:'ll| will| must| should| had better|'d better| had best|'d best| best| have to| need to| ought to| shall)(?: be)? "
            r"(?:go|going|get going|be off|be going|off|leave|head off|head out|move on|moving on|move along|moving along|get on|be on my way|"
            r"on my way|let you (?:get on|work|be|get back to (?:it|work|your work))|leave you to (?:it|your work|work)|take my leave|be away)(?: now)?|"
            r"i(?:'m| am) (?:off|going|leaving|done(?: here)?|away)(?: now)?|that(?:'s| is| will be|'ll be) (?:all|everything|enough)"
            r"(?: i (?:needed|wanted|need|want)(?: to know| to ask| to hear)?)?(?: then)?|nothing (?:else|more)(?: then| from me)?|"
            r"i(?:'ll| will) (?:let you (?:get on|work|be|get back to (?:it|work|your work))|leave you to (?:it|your work|work)|be (?:on my way|going|off)|"
            r"take my leave|go now)|time i was (?:off|going|gone|on my way)|i(?:'ve| have) (?:kept|taken) (?:enough of )?your time|"
            r"i won'?t keep you(?: any longer| longer)?|i(?:'ll| will) not keep you(?: any longer| longer)?)")
_LEAD = re.compile(r"^(?:i (?:say|tell (?:him|her|them)|bid (?:him|her|them)|nod and say|thank (?:him|her|them) and say)\s*,?\s*)", re.I)
_LINE = re.compile(rf"^(?:{_FILLER}[ ,.!]*)*(?:{_GOODBYE})(?:[ ,.!]*(?:{_FILLER}|{_GOODBYE}))*[ .!]*$", re.I)


def is_goodbye(text: str, names=()) -> bool:
    """Is this line nothing but a goodbye to the person named (or to no one in particular)? A question, or anything the goodbye carries
    beyond thanks and filler, is not."""
    low = " ".join((text or "").lower().replace("’", "'").split()).strip().strip("\"'")
    if not low or "?" in low:
        return False
    for n in sorted({x for nm in names for x in ((nm or "").lower(), *((nm or "").lower().split()))} - {"", "the", "a", "an"}, key=len, reverse=True):
        low = re.sub(rf"(?<![\w']){re.escape(n)}(?![\w'])", " ", low)
    low = _LEAD.sub("", low.strip())
    low = re.sub(r"[\"“”]", "", low)
    low = " ".join(low.split()).strip(" ,.!")
    return bool(low) and bool(_LINE.match(low))


PARTING_SYSTEM = """You play one person in a fantasy world, in a role-playing game; the game has you answer in your own voice.
The one you were talking with is leaving: their words are their goodbye. Answer with your parting, as this person would at the end
of an ordinary talk - the last practical thing, something of your own, or nothing warm at all if you are not warm. Never a blessing
for the road unless that is who you are. No narration inside the speech.
gesture is optional: what they do, or empty. Use only this world's terms, and never a line you have said lately.
Respond only with JSON matching the schema."""


def request(ws, npc, text: str):
    """The small request: who they are, how they are with the player, how they talk, the last few lines, what they have said lately."""
    from engine import voice_profile, voice_rules
    from engine.prompt import Prompt
    from npc.prompts import trust_words
    p = Prompt()
    who = (f"someone you have met before, who told you their name is {npc.knows_player_as}" if npc.knows_player_as
           else "someone you have met before" if npc.met_player else "a stranger")
    p.fact(f"YOU ARE: {npc.name}, a {npc.people.replace('_', '-')} {npc.role.replace('_', ' ')} at {ws.world.places[npc.location].name}.\n"
           f"PERSONALITY: {npc.personality or 'not yet known'}\nVOICE: {npc.voice or 'plain'}\nON YOUR MIND: {npc.concern or 'nothing in particular'}\n"
           f"THE ONE LEAVING: {who}; {trust_words(npc.trust)}.")
    stance = getattr(ws, "stance", "")
    if stance:
        p.instruction(stance, "RIGHT NOW YOU ARE")
    if npc.speech:
        fact, lines, material = voice_profile.resident_lines(npc, ws.rng)
        p.fact(fact, "YOUR PEOPLE")
        if lines:
            p.instruction("\n".join(f"- {l}" for l in lines), "HOW YOU TALK")
        if material:
            p.material("\n".join(f"- {m}" for m in material), "WORDS YOU MAY USE, AS THEY ARE (only if they fit)")
    so_far = "\n".join(f"  {w}: {s}" for w, s in ws.convo[-4:])
    if so_far:
        p.history(so_far, "THIS CONVERSATION, LATELY")
    from engine import banter
    p.history(banter.unsaid_rule(list(npc.said)))
    heard = getattr(ws, "_partings_heard", [])
    if heard:
        p.history("\n".join(f"  - {h}" for h in heard[-6:]), "WHAT OTHERS HERE SAID LATELY WHEN THE PLAYER LEFT (not these, nor the like of them)")
    p.fact(f'"{text}"', "THEY SAY, LEAVING")
    return p


def line(ws, npc, text: str) -> tuple[str, str]:
    """(speech, gesture): the model's parting line, checked like any speech (nothing named they were not told, nothing said again
    lately), or the written line when it fails."""
    from engine import truth, voice_rules
    from llm.contracts import Parting
    from llm.gateway import LLMError, generate
    view = truth.scene_of(ws).view(truth.viewer_for_npc(npc, ws.world), "townsfolk")
    known = view.scene.known_words()
    heard = list(getattr(ws, "_partings_heard", []))
    try:
        r = generate("npc_parting", PARTING_SYSTEM, request(ws, npc, text), Parting, temperature=0.9, max_tokens=config.PROSE_MAX_TOKENS, retries=2,
                     validation_context={"known": known, "recent": list(npc.said[-6:]), "heard": heard}, relaxed_context={"known": known})
        speech, gesture = r.speech.strip(), (r.gesture or "").strip()
    except LLMError:
        speech, gesture = voice_rules.written_parting(npc, ws.rng, list(npc.said) + heard), ""
    ws._partings_heard = (heard + [speech])[-10:]                   # (f347) the town's partings lately: no chorus across people
    return speech, gesture


def remember(npc, heard: str, said: str, keep: int = 8) -> None:
    """(f347) What they said and what drew it, kept short on the record for the repeat guard and the written fallback."""
    npc.said = (list(npc.said) + [said])[-keep:]
    npc.heard = (list(npc.heard) + [heard])[-keep:]
