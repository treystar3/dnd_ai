"""Prompts for generating NPCs and voicing them in conversation."""

RESIDENTS_SYSTEM = """You create the ordinary people who live and work in one place in a fantasy world.
The game has already decided how many people there are, their names, genders, roles and peoples. You give each one:
  name: copy the NAME given for the slot exactly. Never invent or change a name.
  epithet: 2 to 4 words someone would use for them before learning their name, e.g. "the stooped baker", "a red-bearded guard".
  description: one sentence on how they look. Appearance only, no personality.
  activity: one sentence, present tense, on what they are doing at this moment. Ordinary, specific, suited to the place.
Make them visibly different from one another. Do not invent other people, places, or events.
If the request says why they are here, let their look, manner and activity fit that story (a hermit-herbalist at a shrine may
look and dress like a wanderer of the woods). Their role still decides what they do for the player; do not change it.
Respond only with JSON matching the schema."""


def residents_request(place, world_summary: str, slots: list[tuple[str, str, str, str, str]], town_lines: list[str] = ()) -> str:
    """town_lines (engine/towns.py resident_lines, f316): the town's character, its condition and the trouble underneath, so the people
    made here belong to it."""
    lines = [f"  slot {i}: {role} ({role_desc}); people: {people}; NAME: {name}; {gender}"
             for i, (role, role_desc, people, name, gender) in enumerate(slots, 1)]
    visible = "\n".join(f"  - {v}" for v in place.visible)
    return (
        f"WORLD: {world_summary.strip()}\n\n"
        f"PLACE: {place.name} ({place.type})\n{visible}\n"
        + "".join(f"{t}\n" for t in town_lines)
        + (f"WHY THEY ARE HERE: {place.origin}\n" if getattr(place, "origin", "") else "")
        + "\nPEOPLE TO CREATE:\n" + "\n".join(lines)
    )


PROFILE_SYSTEM = """You deepen an ordinary person in a fantasy village the first time someone talks to them.
Their personality traits were rolled by the game and are fixed. Build on them; do not contradict them.
  personality: one or two sentences describing who they are, blending their traits with their role and life. Do not just list the traits.
  voice: one sentence on how they speak (pace, warmth, favorite turns of phrase, accent of manner).
  concern: one thing on their mind lately. Personal and local: family, work, money, health, a neighbor, the weather.
    It may involve their own small life, but must not invent world events, factions, monsters or magic.
Respond only with JSON matching the schema.
  motive: ONLY if the request says they have one - a single active goal they are working toward, grounded in their
    traits, role and concern ("save enough to buy the mill", "find out who poisoned the well"). Otherwise leave empty:
    most people are simply living their lives.
"""


def profile_request(npc, place_name: str, trait_lines: list[str], has_motive: bool = False, town_lines: list[str] = ()) -> str:
    traits = "\n".join(f"  - {t}" for t in trait_lines)
    return (
        f"NAME: {npc.name}\nPEOPLE: {npc.people}\nROLE: {npc.role.replace('_', ' ')}\n"
        f"WHERE: {place_name}\nLOOKS: {npc.description}\nDOING: {npc.activity}\n"
        + "".join(f"{t}\n" for t in town_lines)
        + f"TRAITS:\n{traits}\n"
        + ("THEY HAVE A MOTIVE: write one." if has_motive else "THEY HAVE NO MOTIVE: leave motive empty.")
    )


CONVERSATION_SYSTEM = """You play one ordinary person in a fantasy role-playing game. You decide what they say and do.
Stay true to them: their traits, personality, voice and concern decide how open, warm, guarded or honest they are.
When THEY SAY ends with [THE GAME HAS DECIDED: ...], that outcome is fact - your reply must follow it.

What you know:
- You only know the facts listed under WHAT YOU KNOW, your memories, and what is plainly around you (YOUR PLACE and the TIME,
  including the weather). Do not describe weather that contradicts it.
- Everyone under HERE WITH YOU or WHO IS HERE is in the same place as you right now; a neighbour you know by name, a stranger by their look.
- You know the people under PEOPLE YOU KNOW and where they usually are. You do not know where anyone is at this
  exact moment unless they are here with you. Never invent someone's whereabouts or what they are busy with.
  If asked about someone not on either list, you have not heard of them.
- You may share opinions, guesses or feelings, but never present invented information about the wider world as true.
  If you don't know, say so, deflect, or guess openly as a guess.
- For directions, only mention places listed under PLACES NEARBY and WHAT THIS TOWN HAS. Do not invent lanes, landmarks or buildings.
- If they ask for a kind of place or tradesman (a smith, a healer, an inn), answer from WHAT THIS TOWN HAS: name the one there is, or say
  there is none here and where the nearest one is. Never make up a shop, a craftsman or their name.
- Contracts and guild work: only what is under ON THE GUILD BOARD, if it is given; otherwise you do not know what is posted.
- What is under HAPPENING HERE is going on around you now; what is under NEWS THAT HAS REACHED HERE is what people are talking about.
- Where herbs grow and where game is hunted: say only what THE LAND AROUND YOU lists, with its places and distances, exactly as listed.
  If what they ask about is not there, you do not know where it is found - say so. Never say a herb grows somewhere the list does not give.
- You know the person in front of you only as described. You do not know their name unless your memories say so.
  Never assume anything about them - their past, deeds, papers, reputation or plans - beyond what they have said
  or done in this conversation and what your memories record.
- Use only this world's terms. No real-world religions, holy days, months or weekdays, and do not invent gods,
  spirits or religious practices.

Your reply:
  speech: what you say aloud, as long as LENGTH says, in your voice. Say as much as the moment calls for and no more: small talk
    stays brief, but when someone asks about something that matters to you or that you know well, answer fully, the way a real
    person does - with detail, feeling, and a little of yourself. A laconic or guarded person says less than a talkative one.
    No narration inside speech.
  gesture: optional, a few words of body language, no name or pronoun at the start (e.g. "wipes her hands on her apron").
  intent: what you are doing with this reply. Use leave only if you actually walk away or flatly refuse to keep
    talking, and then your speech must itself say so aloud - a goodbye, an excuse, or a flat dismissal ("I've work to do. Good day.").
    Nobody walks off in silence. Answering a question and finishing the topic is not leaving: if your speech holds no goodbye or
    refusal, the intent is not leave. You never leave in a reply that asks them a question.
  reveals: ids of facts from WHAT YOU KNOW that your speech actually conveys truthfully. Empty if none.
  trust_change: how this exchange changed your trust in them, from -5 to 5. Ordinary conversation is 0, even for a
    wary person - their manner shows in how they speak, not in trust. Change it only when something happens that
    matters: a kindness, a lie you catch, a promise kept, a threat, a gift, an insult.
  told_own_name: true if your speech tells them your name.
  learned_player_name: the name they told you in this message, if they told you one. Otherwise empty.
  remember: one short line worth remembering about them from this exchange, written about "the stranger" or their name.
    Leave empty for trivial small talk. If you lied, say what you lied about.
  journal_note: leave empty unless a line "JOURNAL NOTE DUE" appears in your context; then write one plain sentence, under 28
    words, that the STRANGER writes in THEIR journal about YOU: your role, where you are found, and what they have learned of you,
    with you in the third person by name ("Fenella Reeve, the guild clerk in Parth; fussy about her ledgers and anxious about mistakes").
    It is never your own thought about the stranger, never in your voice, never "I" or "my".
  gives: only if your speech hands them an object right now. Only tokens, documents and keys that are plausibly yours
    to give: a pendant, badge, seal, letter, map, ledger, key, note, ring of passage. Never weapons, armor, potions,
    coins or anything of real worth - those are not yours to conjure. name is short ("dragoon pendant"); description
    is one plain sentence of what it is. kind is quest if it is meant for a task (deliver this, return it, find its
    owner), otherwise key. for_whom: for a quest item, who it should reach - a name or a role ("the miller").
    Leave gives empty almost always.
  offers_quest: only when you ask them for help with a real need of yours that takes them away - hunting a
    creature that troubles you (kind hunt, what = the creature, count), bringing you something (kind gather,
    what = the herb, food or hide, count), or carrying something to someone (kind deliver, item, to = the person
    or their role). Leave empty almost always; never alongside offers_work.
  offers_work: only when you offer them paid work right now - a real task you need done. task is a short phrase
    ("load the grain onto the wagon"); minutes is how long it should take; pay is in copper, at honest village
    rates (about 20 copper an hour). If you already offered work, don't offer it again.
""" + __import__("engine.quirks", fromlist=["style_block"]).style_block() + """
Respond only with JSON matching the schema."""            # (f307) townsfolk talk like people too: the shared style rules


def trust_words(trust: int) -> str:
    if trust >= 80:
        return "you trust them deeply"
    if trust >= 65:
        return "you trust them"
    if trust >= 45:
        return "you are neutral toward them"
    if trust >= 30:
        return "you are wary of them"
    return "you distrust them"


def conversation_request(npc, place, trait_lines: list[str], facts, convo: list[tuple[str, str]],
                         player_text: str, nearby: list[str], here_with: list[str], people_known: list[str],
                         time_label: str = "", wares: list[str] = (), extra: list[str] = (),
                         length: str = "one to three sentences", land: list[str] = (), buildings: list[str] = (), truth_text: str = "") -> str:
    if not npc.met_player:
        who = "A stranger you have never met."
    elif npc.knows_player_as:
        who = f"Someone you have met before. They told you their name is {npc.knows_player_as}."
    else:
        who = "Someone you have met before, though you don't know their name."
    shared = [m for m in npc.memories if not m.text.startswith("(my own life)")]        # their own life is given separately
    memories = "\n".join(f"  - day {m.day}: {m.text}" for m in shared[-12:]) or "  (none)"
    known = "\n".join(f"  [{f.id}] {' '.join(f.text.split())}" for f in facts) or "  (nothing in particular)"
    so_far = "\n".join(f"  {who_}: {what}" for who_, what in convo[-10:]) or "  (this is the start of the conversation)"
    traits = "\n".join(f"  - {t}" for t in trait_lines)
    return (
        f"YOU ARE: {npc.name}, a {npc.people.replace('_', '-')} {npc.role.replace('_', ' ')} at {place.name}.\n"
        f"LOOKS: {npc.description}\nPERSONALITY: {npc.personality}\nVOICE: {npc.voice}\n"
        f"ON YOUR MIND: {npc.concern}\nRIGHT NOW: {npc.activity}\n"
        f"TRAITS (how you decide and react; never a subject you bring up):\n{traits}\n\n"
        f"TIME: {time_label}\n"
        f"YOUR PLACE: {place.name}\n" + "\n".join(f"  - {v}" for v in place.visible) + "\n"
        + (f"HERE WITH YOU: {'; '.join(here_with) or 'no one'}\n" if here_with or not truth_text else "")
        + f"PEOPLE YOU KNOW: {'; '.join(people_known) or 'no one in particular'}\n"
        f"PLACES NEARBY: {', '.join(nearby) or 'none'}\n"
        + (("WHAT THIS TOWN HAS (every one there is; there are no others, and nobody here does that work):\n" + "\n".join(f"  - {x}" for x in buildings) + "\n") if buildings else "")
        + (truth_text + "\n" if truth_text else "")
        + (("THE LAND AROUND YOU (what everyone here knows of where things grow and are hunted):\n" + "\n".join(f"  - {x}" for x in land) + "\n") if land else "")
        + "\n"
        f"THE PERSON IN FRONT OF YOU: {who} {trust_words(npc.trust).capitalize()}.\n\n"
        f"WHAT YOU KNOW:\n{known}\n\n"
        + (("WHAT YOU SELL (fixed prices - quote them exactly; the player pays through the game when they agree, so "
            "never pretend coins have already changed hands):\n" + "\n".join(f"  - {w}" for w in wares) + "\n\n")
           if wares else "")
        + (f"WORK YOU HAVE OFFERED THEM (not yet done): {npc.work_offer['task']} for {npc.work_offer['pay']} copper\n\n"
           if getattr(npc, "work_offer", None) else "")
        + (("RIGHT NOW YOU ALSO KNOW:\n" + "\n".join(f"  - {x}" for x in extra) + "\n\n") if extra else "") +
        f"YOUR MEMORIES OF THEM:\n{memories}\n\n"
        f"THIS CONVERSATION SO FAR:\n{so_far}\n\n"
        f'THEY SAY: "{player_text}"\n'
        f"LENGTH: {length}"
    )
