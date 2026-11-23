# A blind first hour, 2026-11-22

An AI player, given only the game's page (the window, in a browser), with no access to the code, played a new character for about
59 typed lines and 45 to 50 minutes. Real model, the owner's RTX 4070 Ti Super, play/faults at 350ce31 with f790 to f792
uncommitted (the window's fight pane shown before a round's telling). Saves and logs were kept in a scratch folder.

**How far to trust it:** an AI judging an AI-narrated game. Its notes are a hint, not a verdict. The
figures marked *logs* were read in the game's own record of the session; the rest is the player's account.

## The character and the hour

Pell Thistlewick, a halfling Traveling Troubadour.
- Calmed a mastiff by humming in the south fields, then walked to Parth.
- Was questioned by Maren, joined the guild and took the wolf contract.
- Bought rations by mistake, and tried a bait plan in the Greywood.
- Won against three wolves at 1 HP (Maren's scripted save), then the scripted troll.
- Turned in the contract, reached level 2, performed in the guild hall and slept at the inn.
- Took the bandit contract, met a level 10 griffon in the foothills and died.
- Woke at the inn.

## Measured

- **Turn times** (*logs*, server side): median 6.8 s, 90th percentile 12.7 s, longest 17.5 s. The player felt 8 to 12 s typical.
- **Dropped work** (*logs*): 8 of 60 turns dropped something.
  - Two were deeds the first reading did not hold: "hand the wolf contract in to the clerk", "wrap the meat trimmings".
  - The rest were background calls.
- **Refusals** (*logs*): 6, including:
  - a line of more than three actions left undone;
  - "There is no wolf hide here for the taking";
  - "You aren't carrying that" (the lute, equipped);
  - "No one here buys hide";
  - a talk aimed at Maren, who was not there.
- **The fight pane (f790):** in about 15 of 17 rounds checked, the pane moved 1 to 10 s before the round's telling. At each fight's
  start the pane and the opening were both present at the first check, so their order could not be told.

## The player's scores

| | Score |
|---|---|
| Clarity of what you can do | 4 |
| Fights, fair and understandable | 4 |
| The world feeling alive | 6 |
| People feeling like people | 5 |
| Immersion | 5 |
| Fun overall | 5 |

## The player's five worst problems

1. **Lines dropped, half done or replaced** (partly confirmed by the logs above).
2. **The companion does nothing in the first fight unless ordered, and nothing says so** until she explains it in the second.
3. **Narration and the engine disagree:**
   - "fifteen copper" for scraps bought 15 trail rations;
   - coins tossed into a hat, with the purse unchanged;
   - "out for maybe half an hour" while the clock jumped days;
   - a host who says his folk want hides, then "No one here buys hide".
4. **People loop:** Maren asked the same question three times after it was answered, and asked for a name already given twice.
5. **Difficulty:** a level 10 griffon at a low-rank contract's site; a blinded wolf still landed a critical hit; fleeing refused or
   failed.

## Creativity, against the owner's "does the world respect what I'm trying to do"

**Respected:**
- humming to calm the mastiff;
- the crowd's reaction to a performance, though its coins were narrated and never paid.

**Told specifically, with little or no effect:**
- a blow at a wolf's leg (a slow appeared a round later);
- mud kicked in wolf 2's eyes, whose status landed on wolf 1;
- climbing a stump for high ground;
- a blow aimed at the eyes;
- a blow at the griffon's wing (a miss).

**Treated as talk, with no round:** singing a war ballad to draw the wolves, and a shrill note to distract the troll.

This matches what the code showed on 2026-11-21: fights have no notion of attention and no aimed blow, and the world's acts change
little that later rules read (docs/design/02, the read side).

## What worked

- Maren dropping the act when walked away from: it felt human.
- The combat log's hover, with the full working of each blow.
- The troll's set piece.

## Reported as bugs (not yet checked in the code)

- The mastiff spoke a line of dialogue.
- A speaker's label flickered between two names.
- "you wipe their hands and makes a deal with Maren".
- The death note says half the gold was lost when a quarter was (the player's trait).
- Maren was still listed as an ally after she left.
- Maren tossed a draught, then asked for it back.
- Character creation pours all 15 abilities and 15 traits into the story log.
- The pane's tab buttons shift, so a click on Board opened Stash.
- Tutorial voice in people's speech ("Does that make sense so far?", "Type search for wolves").
