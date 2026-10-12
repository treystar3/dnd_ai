"""Prompts for fights: reading the player's combat action and narrating each round."""

from scenes.voice import DM_VOICE

INTERPRET_SYSTEM = """You read what a player typed during a fight in a role-playing game and classify it. You do not reply.

kind:
  attack  - a plain attack with their weapon
  ability - they use one of YOUR ABILITIES (match by name or by what it does)
  item    - they drink, apply or use something from YOUR ITEMS (a draught, a tonic, a bandage)
  move    - they reposition: closer, back (retreat a step), or high_ground (climb or leap to a higher spot)
  defend  - they guard, brace, block or take cover
  flee    - they try to run away or escape the fight
  tame    - they try to tame, bind, calm, befriend or take in a wounded wild creature as a companion (target = that creature)
  other   - anything else
target: the id of the enemy they mean, from ENEMIES. If unclear, the nearest one.
ability: for ability, the id from YOUR ABILITIES.
item: for item, the item as they named it.
move: for move, closer / back / high_ground.
buff_for: only for a buff ability. "self" (the default) when they cast it on themselves; the id from ALLIES when they cast it on one
  companion or ally; "all" when they cast it on all their allies / everyone / the whole party.
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
You are narrating one exchange of a fight, like a DM describing what the dice just decided. Three to six sentences.

Make it feel dangerous and alive: momentum, breath, sound, the weight of weapons, the ground underfoot, the
weather and the place. Vary the rhythm - short hard sentences for impacts, longer ones for movement.
Build the player's part around what THE PLAYER SAID they do, but the outcome is only what the EVENTS say.

Rules:
- Every event in EVENTS happens, in that order. Never add hits, misses, wounds, kills or new enemies,
  and never skip an event.
- Several foes doing the same thing (closing in, swinging) can be told together. Lead with what matters most:
  a kill, a wound that changes the fight, a near miss on the player.
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
- Some events end with a marker such as [h2]. It stands for that blow's damage figure, which the game fills in. Copy each marker
  exactly once, right after the sentence that tells that event, in the same form ([h2]). Never explain it and write no numbers yourself.
- No numbers, no game words (damage, health, round, critical, status, ability, legendary, phase). No lists or markdown.
For a boss fight you may write up to eight sentences.
Respond only with JSON matching the schema, with the prose in "text"."""


def narrate_request(place: str, time_label: str, player_words: str, events: list[str], weapon: str,
                    you: str, foes: list[str], round_number: int, gear: str = "", recent: list[str] = ()) -> str:
    return (
        f"PLACE: {place}\nTIME AND WEATHER: {time_label}\nTHE PLAYER FIGHTS WITH: {weapon}\n"
        f"THE PLAYER: {gear}\n"
        "RECENT NARRATION:\n" + ("\n".join(f"  - {r}" for r in list(recent)[-3:]) or "  (none)") + "\n"
        f"MOMENT: {'the opening clash' if round_number <= 1 else f'the fight goes on (exchange {round_number})'}\n"
        f"THE PLAYER IS: {you}\nFOES NOW: {'; '.join(foes) or 'none left standing'}\n"
        f'THE PLAYER SAID: "{player_words}"\n'
        "EVENTS:\n" + "\n".join(f"  - {e}" for e in events)
    )


AFTERMATH_SYSTEM = DM_VOICE + """
You narrate the moment just after a fight ends. Three to five sentences. The last foe is down. Describe the silence returning,
the player's breathing and wounds, the fallen, the place. If the player finds anything, describe them noticing it.
No numbers, no game words. Respond only with JSON matching the schema, with the prose in "text"."""


START_SYSTEM = DM_VOICE + """
You narrate the moment a fight begins, or a creature is sighted. Two to four sentences. First acknowledge what the
player was doing, then reveal what they've run into. Describe only the creatures in the EVENT, their manner and how
far off they are - far means they are still at a distance, not lunging. Make THE ODDS felt through the scene.
If the event says "BOSS ENTRANCE" the creature is the climax of a story: let it make an entrance (up to five sentences) and,
if it says what the boss says, quote that speech as spoken aloud. Add no new threats or facts.
No numbers, no outcome. Respond only with JSON matching the schema, with the prose in "text"."""

THRESHOLD_EVENT = """The player has died again and stands once more at the Threshold. This is death number {deaths}.
You are Orenna, and sending them back costs you: you are weaker every time. Never colder, never angry, never blaming them.
The first time you are tired but steady and glad they came back, and worried it was so soon. By the fourth or fifth your voice is thin, your sentences short, and you sometimes trail off. After that you must rest between words, and the light around you is dim.
It has cost them: {losses}. Their strength and gear were left to them.
In two to four sentences, have her speak to them before they are sent back. Her last words may be "my child"; on later returns the words can catch or crack."""
