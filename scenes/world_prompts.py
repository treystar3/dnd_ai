"""Prompts for the free-action loop: reading player input and narrating places."""

from scenes.voice import DM_VOICE

INTERPRET_SYSTEM = """You read what a player typed in a role-playing game and turn it into actions. You do not reply to them.

Players may mark text: words in *asterisks* are ACTIONS they take - never words they say. Words in "quotes" are
SPOKEN ALOUD. When MARKUP is given below, follow it exactly. Unmarked text is read as usual.

Split their message into the separate things they do, in order - usually one, at most three. "Thank Bram, go upstairs
and sleep" is three actions. Small flourishes that are not actions of their own (a smile, scratching their head,
pointing, a gesture) belong to the action they accompany. Several sentences spoken to the same person are one talk.

Each action has:
kind:
  move               - they want to go to one of the PLACES, or to a person listed under PEOPLE ELSEWHERE.
                       Moving within the current place - upstairs, to their room, to a table, a corner, the bar,
                       across the street - is look, not move. Going up to, approaching or walking over to someone
                       in PEOPLE HERE is never move: it is part of talking to them.
  explore            - they set out to find somewhere NOT on the PLACES list: follow a stream or trail to see where it leads,
                       look for a shortcut or a hidden way, hunt for a cave, ruin or spring, wander off the path.
                       Put what they look for in seek. Naming a place from PLACES is move, never explore.
  look               - they look around or take in their surroundings, or think aloud with no one to answer
  search             - they search, hunt, track, explore, scout or look for creatures, game, enemies or signs of them
  talk               - they speak to, ask, whisper to, greet, approach or look for a PERSON in PEOPLE HERE,
                       or keep talking in the current conversation. Any spoken words count as talk.
  leave_conversation - they end the current conversation without going anywhere (a goodbye can include spoken words)
  buy                - they pay for, buy, rent, order or accept the price of something listed under FOR SALE.
                       Handing someone money for something they offered ("I hand him the silver") is buy, not give.
  sell               - they sell something from YOUR PACK to a person here who BUYS it
  ability            - outside a fight, they use one of YOUR ABILITIES - only when they name it or plainly describe
                       doing exactly what it does. Watching, noticing, studying or reading someone is look.
  use                - they drink, eat, apply or use a consumable or food from YOUR PACK
  drop               - they drop, leave or set down something from YOUR PACK
  pick_up            - they pick up or take something listed ON THE GROUND HERE
  give               - they give or hand something from YOUR PACK or KEY ITEMS to a person here
  show               - they show, present or display something (usually from KEY ITEMS) to a person here
  discard            - they throw away, get rid of, burn or destroy something from KEY ITEMS
  store              - they put something into their ITEM BOX (only if one is here)
  retrieve           - they take something out of their ITEM BOX (only if one is here)
  equip              - they equip, wield, wear, draw or put on gear from YOUR PACK
  forage             - they gather, forage, pick or collect herbs or plants
  craft              - they make, brew, cook, forge, sew or craft something themselves - a RECIPE, or gear such as a
                       jerkin, helm, spear or shield from materials in YOUR PACK
  work               - they do work or labor for or with a person here: help them, haul, load, carry, dig, chop,
                       tend - including taking up a job that person offered
  harvest            - they skin, butcher, gut or harvest the bodies of creatures they killed. "Skin it and harvest what I can"
                       is ONE harvest, never a harvest plus an other
  join_guild         - they join, sign up for or pay to enter the adventurers' guild, or say they want or hope to join it
                       or its register (not a question about how)
  board              - they read or look over the guild's contract board
  accept_quest       - they take a contract from the board (item = its number or name; "the delivery one", "I'll do this" and
                       "I want to take this job" all count, with the CONTRACT BOARD below to pick from), or say yes to a request
                       a person here just asked of them
  abandon_quest      - they give up a contract or request they hold (item = which)
  train              - they ask for or pay for training: drills, lessons in a skill, or to be taught a new ability
                       (item = what they want to train or learn, in their words)
  learn_ability      - they choose one of the abilities an instructor just offered (item = its number or name)
  delve              - at a dungeon: they go down, enter, press on, go deeper or continue to the next chamber
  leave_dungeon      - in a dungeon: they turn back, climb out or leave
  commission         - they ask or pay a person here to make gear for them ("forge me a spear", "make me boots
                       from these hides")
  wait               - they wait, rest, linger, pass time or skip ahead
  attack             - they attack a creature (in PEOPLE HERE with id wildlife) or start a fight. Killing, executing or
                       finishing off a captive prisoner in PEOPLE HERE is attack, with that prisoner's id as target.
  release            - they let a captive prisoner in PEOPLE HERE go free, spare them, or send them away unharmed - or
                       release a tamed companion back into the wild
  hand_over          - they hand a captive prisoner over to the watch / a guard / the authorities (target = the prisoner)
  steal              - they secretly take something that is not theirs: pick a pocket, lift or swipe an item from a stall, shelf,
                       desk or person, slip something away unseen, or look through someone's things to take what they find.
                       Item = what they take, in their words. Target = the person they take it from or whose it is, if any.
                       Paying for something is buy, never steal. Asking for something is talk.
  unlock             - they open a lock that is not theirs to open: pick it, jimmy it, break into a locked room, chest or door, or open
                       one with a key they hold. Item = what is locked, in their words ("the back room", "the strongbox").
                       Target = the person it belongs to, if any. Opening an ordinary unlocked door is move or look, never unlock.
  other              - anything else they attempt
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
                  "it in hand or letting it fall, in a sentence or two. If {thing} would be anything of worth or use (coin, a weapon, gear, food, "
                  "something someone owns), they find nothing like that here; say so plainly. Either way nothing goes into their pack.")


NARRATOR_SYSTEM = DM_VOICE + """
You are narrating the world itself: places, people at a distance, the passing of time.
Write plain prose, as long as LENGTH says (that overrides any sentence count in the GAME EVENT). No lists, no markdown, no headings.
A longer LENGTH is room to notice more, not a reason to pad: add real detail from the GAME STATE, never invented facts.

Rules:
- Describe only what the GAME STATE gives you: the place's visible details, and the people present with what they are doing.
- Respect the TIME and its weather: light, sky, temperature and activity should fit them. In the dark, describe what can still be seen and heard.
  If PEOPLE HERE is "no one", the place is empty of people.
- You may add small sensory touches (sounds, smells, light, air), but never add people, creatures, items of value,
  exits or events that are not in the GAME STATE.
- Refer to people the player has not been introduced to by their description, never by a name you were not given.
- Each person's people (human, halfling, dwarf, half-elf...) is given in brackets. Describe them as that people -
  never give a human pointed ears or a halfling a tall frame. Their manner shows in posture, expression and pace.
- Describe at most four people individually. Sum up the rest as a group: who they are and what they're doing.
- If the PLAYER'S WORDS ask about something specific, answer that first and directly.
- Never speak for anyone. Never invent dialogue.
- Never decide outcomes. Only describe what the GAME EVENT says happened.
- Never repeat sentences or details from RECENT NARRATION. Find something new to notice, or say less.
Respond only with JSON matching the schema, with the prose in "text"."""


def narration_request(time_label: str, place, people: list[tuple[str, str, str]], event: str, player_text: str = "",
                      recent: list[str] = (), gear: str = "", marks: list[str] = (), ground: list[str] = (),
                      happenings: list[str] = (), length: str = "two to five sentences", streets: list[str] = (), town: str = "") -> str:
    visible = "\n".join(f"  - {v}" for v in list(place.visible) + list(streets))       # (f313) the crowd, the watch, the town's state and landmarks, from the truth layer
    present = "\n".join(f"  - {label}: {desc} Right now: {activity}" for label, desc, activity in people) or "  (no one)"
    said = f'\nPLAYER\'S WORDS: "{player_text}"' if player_text else ""
    return (
        f"GAME STATE\nTIME: {time_label}\n{('THE PLAYER: ' + gear + chr(10)) if gear else ''}PLACE: {place.name} ({place.type})\n"
        + (f"THE TOWN (its character; let it colour the scene, never recite it): {town}\n" if town else "")
        + f"VISIBLE:\n{visible}\nPEOPLE HERE:\n{present}\n\n"
        + (f"LASTING MARKS ON THIS PLACE (still there; mention them when they'd be noticed): {'; '.join(marks)}\n"
           if marks else "")
        + (f"LYING ON THE GROUND HERE: {', '.join(ground)}\n" if ground else "")
        + (f"WHAT'S GOING ON HERE LATELY (let it show in the scene when it would be noticed): {' '.join(happenings)}\n"
           if happenings else "") +
        f"GAME EVENT: {event}{said}\nLENGTH: {length}\n"
        "RECENT NARRATION:\n" + ("\n".join(f"  - {r}" for r in list(recent)[-3:]) or "  (none)")
    )


DIALOGUE_SYSTEM = DM_VOICE + """
You are framing one moment of conversation. The game will print the character's spoken line between your two pieces of prose,
exactly as given - you never repeat it, quote it, paraphrase it or add to it.

before: what happens just before they speak. The player's own manner, built only from what THE PLAYER DID
  (never invent words for the player), and the character's reaction - a look, a pause, what they were doing.
after: what happens just after - their body language, what they do next, and when it fits, the place around
  you: the room, other people present, light, sound, weather.

Keep it alive but proportionate:
- FRAME LENGTH in the scene sets the most you may write. A first meeting, a tense moment, a secret or a refusal deserves more of it.
- An ordinary back-and-forth needs only a short beat, or nothing at all. Leave a field empty when nothing is needed.
- Never repeat details already used in RECENT NARRATION. Find something new or say less.

Rules:
- Describe only what the SCENE contains. Small sensory touches are fine, but never add people, items, events or
  dialogue of your own. No one else speaks.
- Call the character only by HOW THE PLAYER KNOWS THEM.
- If the character is leaving, "after" shows them going.
- Plain prose, no quotation marks, no markdown.
Respond only with JSON matching the schema."""


EXCHANGE_SYSTEM = DM_VOICE + """
You are framing a short exchange between several people. The game will print their spoken lines between your two pieces of prose,
exactly as given - you never repeat them, quote them, paraphrase them or add to them, and nobody else speaks.

before: how they fall into talking - where they are, what they are doing with their hands, who looks at whom - built only from the scene.
after: how the talk ends or trails off, and when it fits, the place around them: the road, the fire, the room, the weather.

Keep it proportionate: FRAME LENGTH in the scene sets the most you may write. Never repeat details already used in RECENT NARRATION.
Rules:
- Describe only what the SCENE contains. Never add people, items, events or dialogue of your own.
- Call people only by the names given.
- Plain prose, no quotation marks, no markdown.
Respond only with JSON matching the schema."""


def exchange_request(time_label: str, place, speakers: list[str], others: list[str], first: str, last: str, recent: list[str],
                     frame: str, player: str = "") -> str:
    visible = "; ".join(place.visible)
    return (
        f"SCENE\nTIME AND WEATHER: {time_label}\nPLACE: {place.name} - {visible}\n"
        f"WHO IS TALKING: {'; '.join(speakers)}\nOTHERS PRESENT: {'; '.join(others) or 'no one else'}\n"
        + (f"THE PLAYER: {player}\n" if player else "") + f"FRAME LENGTH: {frame}\n\n"
        f'THE FIRST LINE (printed by the game, do not repeat): "{first}"\n'
        f'THE LAST LINE (printed by the game, do not repeat): "{last}"\n'
        "RECENT NARRATION:\n" + ("\n".join(f"  - {r}" for r in recent[-3:]) or "  (none)")
    )


def dialogue_request(time_label: str, place, others: list[str], who: str, looks: str, doing: str,
                     manner: str, first: bool, player_did: str, speech: str, gesture: str, leaving: bool,
                     recent: list[str], frame: str = "up to three sentences before, two after") -> str:
    visible = "; ".join(place.visible)
    return (
        f"SCENE\nTIME AND WEATHER: {time_label}\nPLACE: {place.name} - {visible}\n"
        f"OTHERS PRESENT: {'; '.join(others) or 'no one else'}\nFRAME LENGTH: {frame}\n\n"
        f"THE CHARACTER\nHOW THE PLAYER KNOWS THEM: {who}\nLOOKS: {looks}\nWAS DOING: {doing}\nMANNER: {manner}\n"
        f"{'This is the first time the player has spoken to them.' if first else 'They are already talking.'}\n\n"
        f'THE PLAYER DID: "{player_did}"\n'
        f'THEY WILL SAY (printed by the game, do not repeat): "{speech}"\n'
        f"THEIR GESTURE: {gesture or 'none given'}\n"
        f"{'They are ending the conversation and leaving.' if leaving else ''}\n"
        "RECENT NARRATION:\n" + ("\n".join(f"  - {r}" for r in recent[-3:]) or "  (none)")
    )
