# f714 to f716: companions that sound like people, one honest line for a partial turn, and a camp anyone can make

Found in the third blind play (docs/play/2026-11-16_blind_play_journal.md, 20th and 21st days). The owner: "fix the question join
first then the rest" (f713 is done) and "pay attention to how npcs speak and if they come off as ai or human like".

## f714: companions that sound like people (pillar 5)

**What was heard.** Gusmund: "Another fight finished now." / "He said a steady hand makes same difference as heavy bow." Pae:
"Moving forward next. Route remains hard." / "It is just a scratch. I can still hold my shield." (she carries a two-handed blade).
Morm: "The path is blocked by my own body now. I must find a flat place to stay." Clipped, no contractions, articles dropped,
sometimes nonsense.

**What is there.** The dialogue style rules (quirks.yaml style_rules) already ask for contractions and plain talk, and the speech
exemplars (voice.yaml exemplars.speech) are good human lines. But the party's exchanges (scenes/banter_actions.py exchange: the
after-fight talk, two companions answering at once) are given **no speech exemplars at all**: only the single-speaker reply and the
townsfolk get them. And nothing checks what comes back for the stiffness the rules forbid.

**The change.**
1. Every exchange gets the speech exemplars (the small-talk pool, drawn as every other call draws them), at the end of its request
   as f583 does elsewhere. No new prompt rule.
2. A check on what anyone says, beside the gateway's others (validate, guard, hygiene, phantoms): a reply whose speech holds two
   or more uncontracted pairs a person would contract ("it is", "I am", "do not", "that is", "you are", "will not"...) is sent back
   once, with the reason "say it the way people talk: it's, don't, I'm", never on the last try, so nothing is lost. A speaker whose
   own way of speaking says otherwise (a voice note marked formal) is let be. The pairs, the count and the reason live in data
   (hygiene.yaml speech), checked at startup.
3. Measure before and after: the voice measures the project already keeps (tools/ voice and page measures) on a recorded night, and
   a blind reader on a sample of companion lines, as the line pass did.

**Not built:** a detector for dropped articles ("makes same difference"): no rule catches it without false alarms; the exemplars are
the lever. Gear consistency ("my shield"): a separate fault of what a speaker is told they carry.

## f715: one honest line when a turn stands in part (pillar 1)

**What was seen.** A hand-in was paid, then the turn's budget ran out before the clerk spoke. Two stand-ins printed: "You see it
through." and "You got as far as Go to the guild hall; the finished contract 'Bounty: ...', paid 27 silver and 50 copper. The rest
didn't happen." Step summaries pasted mid-sentence, and "the rest didn't happen" though the hand-in was paid; only the clerk's words
were lost.

**The change.**
1. What an operation records it did (engine/operation.did) is a finished clause in the second person, written where it happens:
   a walk "you walked to the guild hall" (failures.walked), a hand-in "you handed in Bounty: ... and were paid 27 silver and 50
   copper", any other step its own summary made into a clause by the same helper (lower first letter, "you" form when it is the
   player's imperative). The part_stood lines put {done} where a clause reads right.
2. When a line stood in part and its passage was also lost, one line is printed, not two: the part line, which already says what
   happened; the passage's own stand-in is dropped for that line.
3. "The rest didn't happen" is said only of what did not happen: the steps that did not commit are named (they are known:
   line_failed), never "the rest" when only words were lost.

## f716: a camp anyone can make (pillar 1) - a decision for the owner

**What was seen.** "We make camp by the pool and sleep until morning" made no camp: a camp exists only as an ability's shelter use
(field_actions.field_shelter), and Pim has none. The rest line tells every player "a room at an inn, a camp or a temple" restores
fully. Sleeping in the open on the Ironcrown Peaks drew three attacks in three hours.

**Options.**
- (A, recommended) Anyone can make a plain camp in the wilds: it takes time (say an hour), keeps the full night's rest it promises,
  and halves the chance of being found while sleeping; a shelter ability still makes the better, hidden camp ("undisturbed"). The
  numbers in data (field.yaml camp), for the balance pass to tune.
- (B) No plain camp: the rest line stops offering a camp to a character who cannot make one (it names only what they can use).
- (C) A camp needs a carried good (a bedroll or tent, bought in towns), else as B.

## Questions for the owner

1. f714: take the change (exemplars for every exchange, and the stiff-speech check sent back once)?
2. f715: take the change (finished clauses, one stand-in, "the rest" only for what did not happen)?
3. f716: A, B or C?
