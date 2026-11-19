# f712: every pre-written line in a human author's voice

The owner, 2026-11-16: "Let's do a pass of all the pre written lines and make them read as human authors and not ai", after the
first f711 stand-ins read as "very ai and inhuman like". Pillar 5 (the prose). Nothing ships until the owner has read it.

## The voice (the guide every rewrite follows)

1. Say what happened, in the scene's own terms, as an author or a dungeon master at the table would. Second person, plain words.
2. Never talk about the telling, the words, the story, the passage, the moment "slipping away", or the world "keeping" or
   "remembering" anything. Never "it stands", "that holds", "nothing is lost".
3. Promise nothing later, and claim nothing the game cannot know.
4. Short. One idea a line. Contractions are fine. No chains of clauses joined by semicolons. No idiom that does not say plainly
   what happened ("that didn't come off", "nothing doing").
5. Vary the rhythm inside a list: six lines are six ways a person would say it, not one template six times.
6. No pronoun for a person whose gender the line cannot know; no dash characters; none of the banned machinery words (model,
   error, failed, answer, server...).
7. A game note that tells the player how to do something (a price, a command, why a step cannot be taken) stays clear first; the
   voice applies, but clarity wins.

## What there is (inventory, 2026-11-16)

About 1,260 lines a player reads as written:

- **Tier A, the narrator's fallbacks and the game's told lines (~376).** failures.yaml (234: a turn not taken, what stood, a won
  fight, a round, a fight begun, the goddess silent, character creation), told.yaml (52), voice.yaml partings and stand-ins (19),
  stay.yaml (28), moments.yaml endings (12), road.yaml barrier lines (7), body.yaml falls (5), doors.yaml endings (4), questions.yaml
  (6), launch.yaml (9). Most of the "AI voice" is here.
- **Tier B, authored story content (~200).** Orenna's scenes (~110), the mentor's fixed narration (~37), the hires' errands (18),
  the clerk's fallback lines (24), the opening and the send-off (12). Written as story; some may be the owner's own.
- **Tier C, notes in code (~685).** console.note / refuse / ledger strings in scenes/ and engine/: refusals, prices, how-tos, camp
  and travel notes ("You stop here, on the road. Onward to {onward}, or back to {back}."). Many are functional; some are prose.

Every rewrite keeps each list's checks (counts, placeholders, no machinery words, no dashes) and its placeholders. Recorded
sessions whose shown words change are re-blessed, each change explained.

## Calibration sample (for the owner to read before the rest is drafted)

**turn_not_taken** (a line that came to nothing; say it again). Old: "That slipped away before anything came of it. Nothing has
changed; say it again." / "The moment passed before anything happened. Everything stands where it stood; go again."
New:
- "Nothing happens. Try that again."
- "That didn't work. Try again."
- "Nothing came of that. Say it again, or put it another way."
- "Hold on, that didn't happen yet. Once more?"
- "Nothing's changed. Try that again."
- "That didn't happen. Give it another try."
- "That went nowhere. Try it again."
- "Not quite. Say it once more."
(The owner, on the first draft: "That didn't come off still reads strangely". Idioms that do not say plainly what happened are out.)

**victory_stood** (a won fight whose end went untold). Old: "The fight is won, and it stands. {xp} experience is yours; the
telling of the end slipped away." / "Won. The story of the end will have to wait; the end itself is sure."
New:
- "The fight's over, and you're still standing. {xp} experience."
- "That's the last of them. {xp} experience."
- "You win. {xp} experience for the trouble."
- "They're beaten. You catch your breath. {xp} experience."
- "It's over, and the field is yours. {xp} experience."
- "The last one goes down. You've earned {xp} experience."

**round_stood** (a round whose blows went untold). Old: "That exchange stands as it fell. The telling slipped away; the wounds did
not." / "That round is written in wounds, not words. It stands."
New:
- "You trade blows, and the round ends."
- "Steel meets steel. The round is over."
- "A hard exchange, and then a breath."
- "The round goes by in a blur of strikes."
- "Blows land on both sides. Another round done."
- "You give as good as you get, and the round passes."

**fight_begun** ({foe}, {count}: a fight's opening untold). Old: "No telling how it opened, only that it has: {foe}, {count}, and the
first moves already made." / "What began it is lost in the rush of it: {foe}, {count}, and your weapon already in hand."
New:
- "It comes to a fight: {foe}, {count}."
- "Weapons out. {foe}, {count}."
- "No time to think. {foe}, {count}, coming at you."
- "The quiet breaks. {foe}, {count}."
- "Here they come: {foe}, {count}."
- "It's a fight now. {foe}, {count}, and close."

## Questions for the owner

1. Does the sample's voice read right? (The rest is drafted to match it.)
2. Scope: Tier A for certain. Tier B too, or is that content yours and left as written? Tier C: rewrite the prose-like notes and
   leave purely functional ones (prices, commands) alone except for clear AI-isms?
3. Order: Tier A first, in batches by file, each batch read before the next is applied?
