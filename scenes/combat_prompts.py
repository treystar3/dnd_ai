"""Prompts for fights: reading the player's combat action and narrating each round."""

from scenes.voice import DM_VOICE

INTERPRET_SYSTEM = """You read what a player typed during a fight in a role-playing game and classify it. You do not reply.

kind:
  attack  - a plain attack with their weapon
  ability - they use one of YOUR ABILITIES (match by name or by what it does)
  item    - they drink, apply or use something from YOUR ITEMS (a draught, a tonic, a bandage)
  move    - they reposition: closer, back (retreat a step), or high_ground (climb or leap to a higher spot)
  defend  - they guard, brace, block or take cover
  interpose - they put themselves between an enemy and an ALLY to shield them ("cover Isel", "get between it and Bram";
            target = that ally's id from ALLIES)
  flee    - they try to run away or escape the fight
  tame    - they try to tame, bind, calm, befriend or take in a wounded wild creature as a companion (target = that creature)
  talk    - the player's main act is to SPEAK to an enemy: threaten it, demand its surrender, plead, reason, bargain, or lie to it.
            If they speak while also swinging or casting, choose the attack or ability instead; talk is for when words are the act.
  other   - anything else: an improvised use of the fight's surroundings (kicking something over, throwing sand, climbing,
            putting the fire between you). The engine decides whether it works; still name the enemy it concerns as target.
approach: only for talk - intimidate (threaten, demand surrender, show strength), persuade (plead, reason, offer terms, call it off),
  or deceive (lie, bluff, trick, distract).
target: the id of the enemy they mean, from ENEMIES. If unclear, the nearest one.
ability: for ability, the id from YOUR ABILITIES.
item: for item, the item as they named it.
move: for move, closer / back / high_ground.
buff_for: only for a buff or healing ability. "self" (the default) when they cast it on themselves; the id from ALLIES when they cast
  it on one companion or ally (a fallen one too, when they try to raise them). Blessings and heals go on one creature at a time.
movement: a MOVEMENT ability from YOUR ABILITIES (marked [movement]) that they use on the way while also doing something else -
  "breach past their fighters and stab the archer" is movement = that ability's id, kind attack, target the archer. When the movement
  ability is ALL they do, choose kind ability with that id instead. A movement ability marked "whole turn" is always kind ability.
step: only when their words MOVE them while also doing something else: advance ("charge in and strike", "step up and swing") or
  withdraw ("fall back and shoot", "back off while casting"). The move kind is for when moving is the whole act; step rides along.
summary: one short line describing what they do.
Companions fight on their own and follow the player's lead. If the player tells a companion to attack something
and has no command ability, that is kind attack on that target. Never choose a summon ability just because a
companion is mentioned - only when the player clearly calls or summons one.
Respond only with JSON matching the schema."""


def interpret_request(abilities: list[str], enemies: list[str], text: str, usable: list[str] = (), allies: list[str] = ()) -> str:
    return (
        "YOUR ABILITIES:\n" + ("\n".join(f"  {a}" for a in abilities) or "  (none)") + "\n"
        "YOUR ITEMS: " + (", ".join(usable) or "none") + "\n"
        "ENEMIES:\n" + "\n".join(f"  {e}" for e in enemies) + "\n"
        "ALLIES:\n" + ("\n".join(f"  {a}" for a in allies) or "  (none)") + "\n\n"
        f'PLAYER TYPED: "{text}"'
    )


NARRATE_SYSTEM = DM_VOICE + """
You are narrating one exchange of a fight, like a DM describing what the dice just decided.

Make it feel dangerous and alive: momentum, breath, sound, the weight of weapons, the ground underfoot. One sentence tells one blow,
never two.
Build the player's part around what THE PLAYER SAID they do, but the outcome is only what the EVENTS say.

Rules:
- Every event in EVENTS happens, in that order. Never add hits, misses, wounds, kills or new enemies,
  and never skip an event.
- Several foes doing the same thing (closing in, swinging) can be told together. Lead with what matters most:
  a kill, a wound that changes the fight, a near miss on the player.
- ALREADY SHOWN IN THIS FIGHT lists what the player has read in this fight: the ground, the light, the look of a foe, the gleam of a
  blade. Do not describe them again; the fight has moved on, and so do you. WORDS YOU HAVE WORN OUT are words recent passages leaned
  on: find other words.
- Describe only the armor and gear given under THE PLAYER. If they wear no armor, blows land on cloth and skin.
- How hard a blow lands and how hurt someone is come from the EVENTS: honor "barely a scratch" versus
  "a devastating blow", "barely touched" versus "barely standing".
- Powers in brackets, like (Vampiric) or (Riposte), are the magic of the player's gear or the creature.
  Show them as something seen and felt, never as a name in brackets.
- BOSS fights are the climax of a story. Events that begin "BOSS ENTRANCE", "BOSS TURNING POINT", "BOSS LAST STAND",
  "BOSS FALLS", "BOSS SIGNATURE MOVE" or "BOSS ACTS BETWEEN TURNS" are set-pieces: give each its own vivid beat, and
  if the event says what the boss says, quote it as spoken aloud (you may trim it, never change its meaning or invent new
  threats). A boss acting between turns is acting in the gap, before anyone can answer. A last stand must feel like the
  fight starting over: the boss was dead on its feet and is not. A fall is an ending - slow down for it, let it land.
  Use these beats to make the fight feel like the end of a story, but add nothing the events do not say.
- If the player falls, it is final and terrible. Do not soften it.
- (f412) A companion on the player's side who falls, falls to the blow the EVENTS name, never to the player's or another companion's:
  the player never strikes a companion. One who goes down alive lies where they fell; they do not stand, walk or speak again this fight.
- A foe that falls leaves its body where it fell: fire chars it and blades cut it, but nothing turns a body to ash or dust or makes it
  vanish unless an event says so. (Bodies are skinned, searched and buried after a fight.)
- An event that tells several strikes "in one motion" is ONE attack (a volley, a flurry, a combination): tell it as one action and say
  how many struck home, never as separate attacks one after another, and give its one marker once, at the end of that telling.
- Some events end with a marker such as [h2]. It stands for that blow's damage figure, which the game fills in. Copy each marker
  exactly once, in the same form ([h2]), as the last thing in the sentence that tells that blow, just before its full stop: never in
  the middle of a sentence, and never two markers in one sentence. Never explain it and write no numbers yourself.
- No numbers, no game words (damage, health, round, critical, status, ability, legendary, phase). No lists or markdown.
""" + __import__("engine.voice_rules", fromlist=["exemplar_block"]).exemplar_block("fight") + """
Respond only with JSON matching the schema, with the prose in "text"."""


def narrate_request(place: str, time_label: str, player_words: str, events: list[str], weapon: str,
                    you: str, foes: list[str], round_number: int, gear: str = "", recent: list[str] = (), ground: str = "",
                    shown: list[str] = (), worn: list[str] = (), looks: list[str] = (), allies: list[str] = (), gone: list[str] = ()) -> str:
    """shown: what the player has read in this fight already (scenes/combat_scene.py fight_shown); worn: words recent passages leaned on.
    (f375) No length is given. (f385) allies: everyone on the player's side, with she, he or it and what they fight with. (f415) gone: foes
    alive but out of the fight (yielded or fled); each ally's line ends with how hurt they are now."""
    return (
        f"PLACE: {place}\nTIME AND WEATHER: {time_label}\nTHE PLAYER FIGHTS WITH: {weapon}\n"
        f"THE PLAYER: {gear}\n"
        + (f"THE GROUND NOW (who stands where; never move anyone elsewhere):\n{ground}\n" if ground else "")
        + (("ALREADY SHOWN IN THIS FIGHT (do not describe these again):\n" + "\n".join(f"  - {s}" for s in shown) + "\n") if shown else "")
        + (f"WORDS YOU HAVE WORN OUT (find other words): {', '.join(worn)}\n" if worn else "")
        + "RECENT NARRATION:\n" + ("\n".join(f"  - {r}" for r in list(recent)[-3:]) or "  (none)") + "\n"
        f"MOMENT: {'the opening clash' if round_number <= 1 else f'the fight goes on (exchange {round_number})'}\n"
        f"THE PLAYER IS: {you}\nFOES NOW: {'; '.join(foes) or 'none left standing'}\n"
        + (f"OUT OF THE FIGHT (alive, but they do not strike, block or come back): {'; '.join(gone)}\n" if gone else "")
        + (("ON THE PLAYER'S SIDE (keep who each is as written here, every time: the same she, he or it, and only what they fight with; "
            "how hurt each is NOW is a fact):\n"
            + "\n".join(f"  - {a}" for a in allies) + "\n") if allies else "")
        + f'THE PLAYER SAID: "{player_words}"\n'
        + (("WHAT THE PLAYER'S ABILITIES LOOK LIKE (show each as this, with the weapon they carry; never as something thrown, cast or "
            "magical unless this says so):\n" + "\n".join(f"  - {x}" for x in looks) + "\n") if looks else "")
        + "EVENTS:\n" + "\n".join(f"  - {e}" for e in events)
    )


AFTERMATH_SYSTEM = DM_VOICE + """
You narrate the moment just after a fight ends. The last foe is down. Begin where OPEN ON says, and not the way the passages under DO NOT
BEGIN LIKE THESE began; a returning silence, a held breath or a heaving chest open it only if OPEN ON asks for that. Then what this fight
leaves that is its own: the fallen, a wound that matters, the place, anything found. The player's companions come in only for what is
given about them (who died, who is down, what they do now); never go round them one pose each. If the player finds anything, describe
them noticing it and taking it: it is already in their pack or purse, never left lying. THE BODIES and WHAT THE FIGHT CALLED UP are facts:
keep to them, whatever the narration before said.
No numbers, no game words. Respond only with JSON matching the schema, with the prose in "text"."""


START_SYSTEM = DM_VOICE + """
You narrate the moment a fight begins, or a creature is sighted. First acknowledge what the
player was doing, then reveal what they've run into. Describe only the creatures in the EVENT, their manner and how
far off they are - far means they are still at a distance, not lunging. Make THE ODDS felt through the scene.
If the event says "BOSS ENTRANCE" the creature is the climax of a story: let it make an entrance and,
if it says what the boss says, quote that speech as spoken aloud. Add no new threats or facts.
No numbers, no outcome. Respond only with JSON matching the schema, with the prose in "text"."""

THRESHOLD_EVENT = """The player has died again and stands once more at the Threshold. This is death number {deaths}.
You are Orenna, and sending them back costs you: you are weaker every time. Never colder, never angry, never blaming them.
The first time you are tired but steady and glad they came back, and worried it was so soon. By the fourth or fifth your voice is thin, your sentences short, and you sometimes trail off. After that you must rest between words, and the light around you is dim.
It has cost them: {losses}. Their strength and gear were left to them.
Have her speak to them before they are sent back. Her last words may be "my child"; on later returns the words can catch or crack."""
