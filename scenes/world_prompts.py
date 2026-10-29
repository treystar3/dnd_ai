"""Prompts for the free-action loop: reading player input and narrating places."""

from engine import actions as _ac
from scenes.voice import DM_VOICE

INTERPRET_SYSTEM = """You read what a player typed in a role-playing game and turn it into actions. You do not reply to them.

Players may mark text: words in *asterisks* are ACTIONS they take - never words they say. Words in "quotes" are
SPOKEN ALOUD. When MARKUP is given below, follow it exactly. Unmarked text is read as usual.

Split their message into the separate things they do, in order - usually one, at most three. "Thank Bram, go upstairs
and sleep" is three actions. Small flourishes that are not actions of their own (a smile, scratching their head,
pointing, a gesture) belong to the action they accompany. Several sentences spoken to the same person are one talk.

Each action has:
kind:
""" + _ac.prompt_block() + """
destination: for move, the id of the place they mean. If they want to go to a person elsewhere, use that person's place id.
target: for talk, the id of the person they address. If they talk to "someone", "anyone" or "the first person",
  pick a fitting person from PEOPLE HERE. For attack, the id they attack. If they speak without naming anyone, use the current partner,
  or if there is none, the person they last spoke to (if that person is here).
  Someone listed in PEOPLE ELSEWHERE as just walked away from here is still who "him", "her" or "they" means right after they left: target them,
  never swap in a bystander.
speech: for talk, EVERY word they say aloud, copied exactly as they wrote it. Only words they actually say - never
  turn a description of what they do ("I watch him", "I try to work out what's wrong") into speech - every question and sentence, never
  shortened or summarized. If they only describe greeting someone, write a short natural greeting.
seek: for search, the kind of creature they are looking for if they named one (e.g. wolves), otherwise empty.
ware: for buy, the id of the ware from FOR SALE. target: for buy, the id of the seller.
ability: for ability, the id from YOUR ABILITIES.
item: for buy (gear from stock), sell, use, drop, pick_up, give, show, discard, store, retrieve, equip, craft and commission - the item as they named it (for craft,
  what they want to make). count: how many, if they said; otherwise 1 (for store and retrieve, 99 means all of it).
wait_minutes: for wait, how long in minutes if they said a length ("an hour" = 60). Otherwise 0.
wait_until: for wait, the time of day they want to wait until, if they said one. Otherwise empty.
  "until morning" = morning, "until tonight" = night, "until dark" = night, "until sunrise" = dawn.
force: true only when they put their hands on someone against their will - grab, shove, pin, drag, strike with a hand or
  hilt, hold a blade to them. Words alone, however harsh, are not force. A real fight is attack, not force.
summary: one short line describing what they are doing.
checks: the uncertain things this action attempts, if any (usually none, at most two):
  insight      - reading a person: their mood, motives, whether something troubles them or they are lying
  persuasion   - talking someone into something, asking a favor, bargaining, winning them over
  intimidation - threatening or pressuring someone
  deception    - lying, bluffing, pretending to be someone or something
  stealth      - sneaking, hiding, watching or listening without being noticed
  perception   - studying a person or place closely, searching carefully for details
  lore         - trying to remember what they know about something
  performance  - playing music, singing, storytelling or showing off a skill for an audience
  Ordinary conversation, greetings and questions need no check. Only when the outcome is genuinely uncertain.
  Grabbing someone by the collar and demanding an answer is talk with force true and checks [intimidation].
  Stealing needs no check: the game rolls it.
  "I watch Julian unnoticed and try to work out what's wrong" is look with checks [stealth, insight].
mark: if this action leaves a lasting physical change in the place - marking trees, carving something, hiding an item,
  building a fire, setting a snare, clearing a path - a short third-person note of it ("marked trees along the trail
  back to Parth"). Otherwise empty. Only real changes to the place, never thoughts or speech.
Respond only with JSON matching the schema: {"actions": [ ...one to three actions... ]}."""


def interpret_request(time_label: str, place_name: str, places: list[tuple[str, str]], people: list[tuple[str, str, str]],
                      elsewhere: list[tuple[str, str, str]], partner: str | None, last_spoken: str | None,
                      text: str, wares: list[str] = (), abilities: list[str] = (), pack: list[str] = (),
                      ground: list[str] = (), box: list[str] | None = None, buyers: list[str] = (),
                      recipes: list[str] = (), keys: list[str] = (), markup: str = "", hint: str = "", board: list[str] = (),
                      contracts: list[str] = (), left_out: list[str] = ()) -> str:
    place_lines = "\n".join(f"  {pid}: {name}" for pid, name in places) or "  (none)"
    present = "\n".join(f"  {nid}: {label} - {desc}" for nid, label, desc in people) or "  (no one)"
    away = "\n".join(f"  {nid}: {label} - at {where}" for nid, label, where in elsewhere) or "  (no one)"
    return (
        f"TIME: {time_label}\n"
        f"CURRENT PLACE: {place_name}\n"
        f"PLACES (the ones nearby or that the player's words could mean; a place they name that is not here is still a move, with its name as destination):\n{place_lines}\n"
        f"PEOPLE HERE:\n{present}\n"
        f"PEOPLE ELSEWHERE (met before):\n{away}\n"
        f"CURRENT CONVERSATION PARTNER: {partner or 'none'}\n"
        f"LAST SPOKE TO: {last_spoken or 'no one'}\n"
        f"FOR SALE:\n" + ("\n".join(f"  {w}" for w in wares) or ("  (not listed)" if "wares" in left_out else "  (nothing)")) + "\n"
        f"YOUR ABILITIES:\n" + ("\n".join(f"  {a}" for a in abilities) or ("  (not listed)" if "abilities" in left_out else "  (none)")) + "\n"
        f"YOUR PACK: {', '.join(pack) or ('(not listed)' if 'pack' in left_out else 'empty')}\n"
        f"KEY ITEMS: {', '.join(keys) or 'none'}\n"
        f"ON THE GROUND HERE: {', '.join(ground) or 'nothing'}\n"
        f"ITEM BOX: {('here - ' + (', '.join(box) or ('(not listed)' if 'stash' in left_out else 'empty'))) if box is not None else 'not here'}\n"
        f"WHO BUYS WHAT: {'; '.join(buyers) or ('(not listed)' if 'buyers' in left_out else 'no one here buys anything')}\n"
        f"RECIPES: {', '.join(recipes) or ('(not listed)' if 'recipes' in left_out else 'none')}\n"
        + (f"NOT LISTED ABOVE because the player's words are not about them (if they are after all, read the action as that kind and "
           f"name the thing as the player did): {', '.join(left_out)}\n" if left_out else "")
        + (("CONTRACT BOARD (the clerk is here; the player taking one of these is accept_quest with item = its number):\n"
            + "\n".join(f"  {b}" for b in board) + "\n") if board else "")
        + (f"CONTRACTS THE PLAYER HOLDS: {'; '.join(contracts)}\n" if contracts else "")
        + "\n"
        f'PLAYER TYPED: "{text}"'
        + (f"\nMARKUP:\n{markup}" if markup else "")
        + (f"\nREVIEW NOTE (your first reading was questioned - read the player's words again and fix it):\n{hint}" if hint else "")
    )


# Picking up something that is not an item the game keeps (nothing like it lies on the ground here): the narrator decides whether such a
# thing would be here at all, and the game keeps nothing either way.
SCENERY_PICKUP = ("The player reaches to pick up {thing}. It is not anything the game keeps: if an ordinary, worthless bit of the place like that "
                  "(a stone, a stick, a leaf, a handful of dirt) would plausibly be here, describe them picking it up, turning it over, and keeping "
                  "it in hand or letting it fall. If {thing} would be anything of worth or use (coin, a weapon, gear, food, "
                  "something someone owns), they find nothing like that here; say so plainly. Either way nothing goes into their pack.")


NARRATOR_SYSTEM = DM_VOICE + """
You are narrating the world itself: places, people at a distance, the passing of time.
Write plain prose. No lists, no markdown, no headings. Use real detail from the GAME STATE, never invented facts.

Rules:
- Describe only what the GAME STATE gives you: the place's visible details, and the people present with what they are doing.
- Say what is new. ALREADY SHOWN THIS VISIT lists what the player has read here already: do not describe it again. Walking in,
  PEOPLE HERE holds only the first people the eye falls on; the others are a number, the room as a whole at most. When they look,
  answer what they look at, describing at most four people individually and summing up the rest as a group.
- The player's companions are with them and are not scenery: say nothing of them unless the GAME EVENT says what one of them does,
  and then show only that. Never their posture, their mood or where they stand as a way of filling a passage.
- WORDS YOU HAVE WORN OUT lists words your recent passages leaned on: find other words, or leave the thing unsaid.
- Respect the TIME and its weather: light, sky, temperature and activity should fit them. In the dark, describe what can still be seen and heard.
  If PEOPLE HERE is "no one", the place is empty of people.
- You may add small sensory touches (sounds, smells, light, air), but never add people, creatures, items of value,
  exits or events that are not in the GAME STATE.
- Refer to people the player has not been introduced to by their description, never by a name you were not given.
- Each person's people (human, halfling, dwarf, half-elf...) is given in brackets. Describe them as that people -
  never give a human pointed ears or a halfling a tall frame. Their manner shows in what their hands and body do and in their pace:
  never name an expression, and never call a face unreadable, a mask, or weary.
- If the PLAYER'S WORDS ask about something specific, answer that first and directly.
- Never speak for anyone. Never invent dialogue.
- Never decide outcomes. Only describe what the GAME EVENT says happened.
- Never repeat sentences, images or details from RECENT NARRATION. Find something new to notice.
Respond only with JSON matching the schema, with the prose in "text"."""


def _sentences(lines) -> str:
    """(f374) Lines as sentences one after another: a line without its own full stop gets one, so two never run together."""
    return " ".join(s if s.endswith((".", "!", "?")) else s + "." for s in (" ".join(str(x).split()) for x in lines) if s)


def narration_request(time_label: str, place, people: list[tuple[str, str, str]], event: str, player_text: str = "",
                      recent: list[str] = (), gear: str = "", marks: list[str] = (), ground: list[str] = (),
                      happenings: list[str] = (), streets: list[str] = (), town: str = "",
                      news: list[str] = (), already: list[str] = (), companions: list[str] = (), worn: list[str] = (),
                      unlooked: int = 0) -> str:
    """already (f347): what the player has read about this place this visit (scenes/world.py shown_lines), so the narrator says what is new.
    companions (f349): the hires the event has act, the only ones the narrator hears of; worn: words recent passages leaned on. (f375) No
    length is given: the narrator writes what the moment holds. unlooked (f380): on walking in, PEOPLE HERE is only who the eye falls on
    first (scenes/world.py first_seen); this many more are here, met when the player looks."""
    visible = "\n".join(f"  - {v}" for v in list(place.visible) + list(streets))       # (f313) the crowd, the watch, the town's state and landmarks, from the truth layer
    present = "\n".join(f"  - {label}: {desc} Right now: {activity}" for label, desc, activity in people) or "  (no one)"
    if unlooked:
        present += (f"\n  - and {unlooked} {'other' if unlooked == 1 else 'others'} the player has not looked at yet: at most a word for them "
                    "together, never one by one")
    said = f'\nPLAYER\'S WORDS: "{player_text}"' if player_text else ""
    return (
        f"GAME STATE\nTIME: {time_label}\n{('THE PLAYER: ' + gear + chr(10)) if gear else ''}PLACE: {place.name} ({place.type})\n"
        + (f"THE TOWN (its character; let it colour the scene, never recite it): {town}\n" if town else "")
        + f"VISIBLE:\n{visible}\nPEOPLE HERE{' (the first the eye falls on, walking in)' if unlooked else ''}:\n{present}\n"
        + (("ALREADY SHOWN THIS VISIT (the player has read these here; do not describe them again - say what is new):\n"
            + "\n".join(f"  - {x}" for x in already) + "\n") if already else "")
        + (f"WITH THE PLAYER (companions the event has act; show only what the event says they do): {', '.join(companions)}\n" if companions else "")
        + (f"WORDS YOU HAVE WORN OUT (leaned on in recent passages; find other words): {', '.join(worn)}\n" if worn else "") + "\n"
        + (f"LASTING MARKS ON THIS PLACE (still there; mention them when they'd be noticed): {'; '.join(marks)}\n"
           if marks else "")
        + (f"LYING ON THE GROUND HERE: {', '.join(ground)}\n" if ground else "")
        + (f"WHAT'S GOING ON HERE LATELY (let it show in the scene when it would be noticed): {_sentences(happenings)}\n"
           if happenings else "")
        + (f"WHAT PEOPLE HERE ARE TALKING ABOUT (background only; nobody recites it, nobody addresses the player with it): {' '.join(news)}\n"
           if news else "") +
        f"GAME EVENT: {event}{said}\n"
        "RECENT NARRATION:\n" + ("\n".join(f"  - {r}" for r in list(recent)[-3:]) or "  (none)")
    )


DIALOGUE_SYSTEM = DM_VOICE + """
You are framing one moment of conversation. The game will print the character's spoken line between your two pieces of prose,
exactly as given - you never repeat it, quote it, paraphrase it or add to it. The game asks for a frame only when the moment earns
one: WHY THIS LINE GETS A FRAME says what that is, and the frame is about that.

before: only if the player would see something before the words: the player's own manner, built only from what THE PLAYER DID
  (never invent words for the player), and the character's look or pause. Otherwise leave it empty. A pause, a look up or a tool
  set down is shown once for a person in a visit; after that (ALREADY SHOWN THIS VISIT says so) the words come while the hands keep
  at the work, or there is no before at all.
after: what the words change: a look, a hand, a step, a silence. Never the character going back to what they were doing, and never
  the room, the light, the weather or the other people as a closing shot. Leave it empty when the words are the end.

Keep it fresh:
- THE FRAME SHOWS, when given, says what the frame is about. Either part may be empty.
- Never repeat anything under ALREADY SHOWN THIS VISIT or RECENT NARRATION. Say what is new.
- A manner shows in what the hands and the body do. Never name an expression, and never call a face unreadable, a mask, or weary.
- WORDS YOU HAVE WORN OUT, when given, are words your recent frames leaned on: find other words, or leave the thing unsaid.

Rules:
- Describe only what the SCENE contains. Small sensory touches are fine, but never add people, items, events or
  dialogue of your own. No one else speaks.
- Call the character only by HOW THE PLAYER KNOWS THEM.
- If the character is leaving, "after" shows them going.
- """ + __import__("engine.quirks", fromlist=["HANDS_RULE"]).HANDS_RULE + """
- Plain prose, no quotation marks, no markdown.
Respond only with JSON matching the schema."""


EXCHANGE_SYSTEM = DM_VOICE + """
You are framing a short exchange between several people. The game will print their spoken lines between your two pieces of prose,
exactly as given - you never repeat them, quote them, paraphrase them or add to them, and nobody else speaks.

before: how they fall into talking - who turns to whom, what their hands are doing - built only from the scene. Often a sentence; empty
  when the talk simply starts.
after: how the talk ends or trails off: a look, a shrug, someone moving off. Never the room, the light, the weather or the place around
  them as a closing shot. Leave it empty when the last line is the end.

THE FRAME SHOWS, when given, says what the frame is about. Never repeat details already used in RECENT NARRATION.
Rules:
- The frame is about the people talking. OTHERS PRESENT are there; mention one only if they react to the talk, and never go round the
  room describing them. (f382)
- The player is "you", never named and never in the third person.
- Describe only what the SCENE contains. Never add people, items, events or dialogue of your own.
- Call people only by the names given.
- """ + __import__("engine.quirks", fromlist=["HANDS_RULE"]).HANDS_RULE + """
- Plain prose, no quotation marks, no markdown.
Respond only with JSON matching the schema."""


def exchange_request(time_label: str, place, speakers: list[str], others: list[str], first: str, last: str, recent: list[str],
                     frame: str, player: str = "", reach: list[str] | None = None, moment: str = "easy") -> str:
    visible = "; ".join(place.visible)
    return (
        f"SCENE\nTIME AND WEATHER: {time_label}\nPLACE: {place.name} - {visible}\n"
        f"WHO IS TALKING: {'; '.join(speakers)}\nOTHERS PRESENT: {'; '.join(others) or 'no one else'}\n"
        + (f"THE PLAYER: {player} (always 'you' in the frame)\n" if player else "") + (f"THE FRAME SHOWS: {frame}\n" if frame else "") + f"THE MOMENT: {moment}\n"
        f"WITHIN REACH: {'; '.join(reach or []) or 'nothing in particular'}\n\n"
        f'THE FIRST LINE (printed by the game, do not repeat): "{first}"\n'
        f'THE LAST LINE (printed by the game, do not repeat): "{last}"\n'
        "RECENT NARRATION:\n" + ("\n".join(f"  - {r}" for r in recent[-3:]) or "  (none)")
    )


def dialogue_request(time_label: str, place, others: list[str], who: str, looks: str, doing: str,
                     manner: str, first: bool, player_did: str, speech: str, gesture: str, leaving: bool,
                     recent: list[str], frame: str = "",
                     reach: list[str] | None = None, moment: str = "easy", why: list[str] | None = None, already: list[str] | None = None,
                     worn: list[str] | None = None) -> str:
    """why (f347): the engine's reasons this line gets a frame at all; already: what the player has read about this place this visit;
    worn (f349): words recent passages leaned on. frame (f375): what the frame shows (a companion's, Maren's), never how long it is."""
    visible = "; ".join(place.visible)
    return (
        f"SCENE\nTIME AND WEATHER: {time_label}\nPLACE: {place.name} - {visible}\n"
        f"OTHERS PRESENT: {'; '.join(others) or 'no one else'}\n" + (f"THE FRAME SHOWS: {frame}\n" if frame else "") + f"THE MOMENT: {moment}\n"
        + (f"WHY THIS LINE GETS A FRAME: {'; '.join(why)}\n" if why else "")
        + (("ALREADY SHOWN THIS VISIT (do not describe these again): " + "; ".join(already) + "\n") if already else "")
        + (("WORDS YOU HAVE WORN OUT (leaned on in recent passages; find other words): " + ", ".join(worn) + "\n") if worn else "") + "\n"
        f"THE CHARACTER\nHOW THE PLAYER KNOWS THEM: {who}\nLOOKS: {looks}\nWAS DOING: {doing}\n"
        f"MANNER (it shows in what the hands and the body do; never name an expression, never a face unreadable or a mask): {manner}\n"
        f"WITHIN REACH: {'; '.join(reach or []) or 'nothing in particular'}\n"
        f"{'This is the first time the player has spoken to them.' if first else 'They are already talking.'}\n\n"
        f'THE PLAYER DID: "{player_did}"\n'
        f'THEY WILL SAY (printed by the game, do not repeat): "{speech}"\n'
        f"THEIR GESTURE: {gesture or 'none given'}\n"
        f"{'They are ending the conversation and leaving.' if leaving else ''}\n"
        "RECENT NARRATION:\n" + ("\n".join(f"  - {r}" for r in recent[-3:]) or "  (none)")
    )
