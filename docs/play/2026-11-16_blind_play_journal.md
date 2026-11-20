# Blind play journal 2 - Meravia (after f654 to f672)

Played as a new player would, through the game's own page (main.py --gui, its page opened in the Claude browser pane), against the
game's own local model server. Goal: level 25. Code at eaa4bb7.

## WHERE I AM (rewritten as things change)
- Character: a slight young gnome woman, copper hair, ink-stained fingers, wire-mended spectacles. (more once made)

## LOG

### Session start - Mon Nov 16 2026, just after midnight by the computer clock

**Character creation**
- Step 1 "Who you were": the first screenshot after my clicks still showed the old choices (Human, they, lean, grown, brown); a
  second screenshot showed my picks had taken. Probably the page redrawing after each click; harmless, but a player would not see
  it. The live sentence reads "A slight young gnome woman with copper hair; ink-stained fingers and spectacles mended with wire." GOOD.
- Step 2 Name. Said in my own words: `My name is Pim Quillfeather. Why can I still feel my fingers?` She answered using the name
  ("It is beautiful, Pim Quillfeather") and then asked for it again ("Please, tell me, what is your name?"). SAME AS LAST TIME
  (CONFUSING). Typed it in the name box: shown in the story as `› Pim Quillfeather`, no `create:` prefix. FIXED (f671).
- Step 3 Calling: `a wandering scholar who hurls fire and frost at whatever threatens her, and reads the old ruins for lost spells`.
  Class "Ruin-Seeker". Her reading of me was lovely. No bracketed class card in the story this time. FIXED (f671).
- Step 4 Abilities: the 15 cards are also printed into the story column as a long numbered text list (ACTIVE ABILITIES 1..15),
  and later the traits (PASSIVE TRAITS 1..15) and an ATTRIBUTES block. The page already shows them as cards; in the story they are a
  wall of text. CONFUSING (mild). "Artisan's Insight" and "Mastery of Craft" are word for word the same card: SAME AS LAST TIME (8.2,
  left). Clicking a card showed no change in the screenshot right after; typing the three names in the box worked at once. GOOD.
- Step 5 Traits by typing three names: worked. GOOD.
- Step 6 Attributes: "Suggested for a Ruin-Seeker" gave STR 18 and CON 10, though my staff "hits harder with Intelligence" and every
  spell uses INT. CONFUSING: why strength for a scholar? Fast clicks on - and + were partly lost (the page redraws). Describing it,
  `a brilliant mind and a wise one, tougher than I look, quick on my feet, but not strong`, gave STR 10 DEX 14 CON 18 INT 26 WIS 22
  CHA 10: exactly right. GOOD. "Character saved to ..." no longer in the story. FIXED (f671).
- Woke in a fern hollow by the south fields near Parth, crude ash staff, 10 silver. Health 89, Mana 105.

**The tutorial (lines 1-24)**
- 1-2 Walking to Parth: fine. The square is alive (a smith, a dwarf reading a track). GOOD.
- 3-7 Maren stops me. CONFUSING (BROKEN-ish): she asked "where did you come by that, and what do you do?" three times though I
  answered both each time (`"The staff was lying beside me ... I'm a scholar"`; `"On the road, mostly ..."`). Only
  `"I found the staff in the field where I woke. I'm a mage. I fight with fire and frost."` moved her on. A player would think she
  is not listening.
- 8-10 The guild explained, walk to the hall: good. CONFUSING (small): Maren calls Pim "they" ("This is Pim Quillfeather. They're
  looking to get started") though I chose "she" at creation. Later the narrator gave Maren "his stance" once.
- 11 `I count out three silver and hand them to Emlily.` Joined at once, one payment: "You join the adventurers' guild at rank F.
  Paid 0₲ 3Ş 0₵. The Board tab shows the contracts; Quests, the ones you hold." FIXED (6.3; f660, f672's wording).
- Board pane: one contract and Maren to hire. Accept and Hire buttons worked.
- 13 `"Thank you, Maren. Shall we go and find these wolves?" We set out for the Greywood.` Maren answered; nobody moved (2 minutes
  passed). CONFUSING: the walk in my line was dropped. `We walk to the Greywood.` alone worked.
- 15 Wolves: their arrival told once. FIXED (8.8).
- 17 `I drink the healing draught, then cast Twin Flare at wolf 2.` Drank (+16) AND cast. FIXED (1.8; f659).
- Prose against figures, as before (group E): "barely scraping the skin ... 12 damage"; Twin Flare's missed second hit told as me
  swinging my staff.
- 21 Troll: `I stay behind Maren and cast Chilling Touch at the troll.` No spell (mana unchanged; the fight log's round 1 has no cast)
  and the telling put me "between the beast and Maren's flank". BROKEN: my spell lost, and the opposite of where I said I stood.
- 22 Maren: "Maren tosses you a healing draught ... give it to me." `I give Maren a healing draught, then cast Chilling Touch at the
  troll.` -> "You have nothing like that to use in a fight." BROKEN: she said she tossed me one; I had none. (The spell after it was
  cast: f659's rest of the line held even when the draught part was refused.)
- 23 `"Maren, attack the troll!" I cast Twin Flare at the troll.` -> "You tell Maren to attack the troll." and my spell. Both done. GOOD.
- 24 Walking back: no "the sun is low" any more. FIXED (2.17). CONFUSING: we arrive inside the guild house and Maren says "You'd
  better get yourself over to the guild hall and hand in that contract".
- 25 Hand-in: paid 7S 50C, +310 XP, level 2. `#allocate int 3 con 2` then `y`. Fine.

**Parth, the south fields and the Greywood (lines 26-70), day 1 to day 2**
- Board: rank F holds 2 contracts at once ("You hold 2 guild contracts already"). Took Gather 6 yarrow and "Investigate: a history that
  was rewritten". Hired Pae Tamalaga (goliath fighter, 5S) and Morm Wooddale (priest, 6S). Taking the investigation printed
  "Lead: Something is wrong, and the first sign of it is at Kelpmoor. Ask there." GOOD.
- `"What do you sell, and how much for a healing draught?"` to the quartermaster: an answer, no coin spent. FIXED (6.2; f660).
  `"I'll take two healing draughts, then."` bought two, 3S. GOOD.
- `We walk to the Greywood and I gather yarrow ...` -> "Gathered: 2 silverleaf." CONFUSING: I asked for yarrow and was
  given silverleaf without a word that yarrow was not there; later `I gather yarrow` gave wild garlic. Gathering ignores which herb
  is asked. Morm told me where yarrow grows; the herbalist said "the south fields", and it was there, one or two an hour. GOOD that
  the people know.
- `#places` typed: the pane left "Last fight" for Places. FIXED (8.4).
- In the inn: `I ask the innkeeper where Kelpmoor is` (inside a line that also walked there) was not asked; Pae answered something
  else. Asked alone, the host answered: "Kelpmoor's southeast, about a day's journey". GOOD.
- `"Thank you." I buy a room for the night and we sleep until morning.` -> paid 50 copper for "a room for the night", "You slept in
  your room and woke fully rested", 2nd Day 6:00 AM. FIXED (4.8 and 4.9; f655, f656).
- BROKEN: every line naming Alulf the herbalist, whose yarrow it was ("Posted for Alulf Radcroft"), was undone with a stand-in and no
  reason: `We walk back to Parth. I give Alulf Radcroft the six yarrow for his contract.` -> "The deed is done, though no words came
  for it ... The remainder never began"; `I hand the herbalist the six yarrow.` -> "Not yet: nothing happened"; `I go to Alulf and tell
  him I have his six yarrow, and collect my pay.` -> "That one got away before it began." The same hand-in to the clerk worked
  at once (level 3). I could not see why (no logs for me); in a test campaign the same deeds raise no error, so it is likely the
  reading of the line failing. The player is never told which part of the world said no.
- The investigation at the south fields: nothing there, and no hint to look elsewhere beyond the first lead.
- Worg hunt: three searches (`We walk to the Greywood and search for worg tracks.`, `We push deeper ...`, `We hunt for the worgs`)
  each found a clue (Perception: success, strong success) and no worgs, with the clock standing still; only `I search for worgs.`
  brought them. CONFUSING: which words make a hunt happen. The check label reads "Perception: failure" with no dash. FIXED (8.9).
- `"Pae, take worg 1!" I cast Chilling Touch at worg 2.` -> both done, twice. GOOD.
- The narrator said I pulled on the rawhide armor when it was only found; `put on the rawhide studded armor` then really equipped it.
- The fight pane showed "healing draught x3", so at the troll I did hold the draught Maren tossed: "You have nothing like that to
  use in a fight" for `I give Maren a healing draught` was wrong. BROKEN (giving a draught to the tutor in the troll fight).

**Lines 71-85: worg pay, the tithe receipt, and why hand-overs were undone**
- `I skin the two worgs, then we walk back to Parth and I report the worg hunt to Emlily for my pay.` skinned and walked; the report
  (the third deed) was not done and nothing said so. Alone it worked: level 4.
- Hired Gusmund Ellisley (archer, 5S). Took "Deliver the guild tithe receipt to the priest at the temple of Parth".
- At the temple, `I tell the priest the guild sent me with their tithe receipt and hand it over.` -> "Not yet: nothing happened";
  `I hand the tithe receipt to the priest.` -> "The moment passed before anything happened." Same as with Alulf.
- I quit (`quit`), restarted the game with its --debug option, and Continue read "played today at 01:01", the time I left. FIXED
  (8.7; f672).
- With the debug view the same `I hand the tithe receipt to the priest.` worked ("Delivered: guild tithe receipt."), and showed why it
  had failed: the give step ran three times ("intent 1/1" three times). Each run met the priest for the first time ("promoted Berrisa
  Dunham ...") and asked for her reply inside the step, which stood down and ran again. This time the third run held; before, every
  try gave up as "nothing happened". BROKEN (engine): a hand-over to someone not met yet, needing their promotion and reply during
  the step, is undone at random, and the player is told only to try again. It explains every Alulf line. (Not code changed this
  session: the f470 rule that model calls come before an operation's writes.)
- Paid for the receipt (level 4, 590/650). Took "Bring 4 bear hide".
- In the Greywood, `We follow the bear's prints and musk deeper into the wood until we find it.` -> the story has a bear step out of
  the briars, but no fight began (no foes in the pane). BROKEN (narrated foe with no engine foe).
- `"Pae, hold it off!" I cast Chilling Touch at the bear.` -> taken whole as talk to Pae: no spell, no mana spent, and Pae said
  "Hold held firm. Bear fell." BROKEN, and it is mine: the hire intercept (f654) takes a line whose first sentence speaks to a
  companion even when the next sentence is the player's own deed said to no one. f654 only looked for the player's part inside the
  sentence spoken to them. Fix: a line with a clause of the player's own outside what is said to the companion goes to the reading.

**Lines 86-120: bears in the Greywood (level 5)**
- `I search for bears.` finds bears, boars and wolves reliably. Bears worth 91 to 282 XP; two level-1 wolves together, 1 XP.
- A foe out of reach: "You cannot strike brown bear from where you stand. You spend the turn getting there." FIXED (4.4; f661).
  Small: no "the" before the foe's name. And the narrator told me "scramble backward into the safety of the briars" that same turn.
- `Chilling Touch at the brown bear.` while it was still cooling down: "Chilling Touch isn't ready yet (1 more round). You attack
  instead." FIXED wording (8.9).
- `Twin Flare at the brown bear.` after the fight ended: "Twin Flare is a fighting technique - save it for a fight." GOOD.
- Skinning ruins about one hide in three ("Harvested: nothing usable."), so four bear hides took five bears.
- The fight's aftermath passage once fell to a stand-in: "operation aftermath rolled back: the turn's budget is spent (3 s left,
  the floor is 8 s)" -> "They are beaten. You are the better by 29 experience, whatever went unsaid." Fine as a stand-in.
- Morm asked "what name do you use? Where do you travel from?" twice, two days after signing on. CONFUSING (companion memory).
- `We walk back to Parth and I give the four bear hides to the smith, Ulard Heygate, for his contract.` (I held three.) The smith was
  not at his forge at 7 PM; the audit turned my hand-over into words to Pae ("since the smith is not present, they speak of the
  action to their companions"), and the passage then said "You present him with the four bear hides." BROKEN twice over: the story
  told a hand-over that never happened, and I was never told the smith was not there (a group C site: the audit changing a deed
  into talk says nothing to the player).
- `We go to the Tilted Plough. I buy a room for the night and we sleep until morning.` -> the audit refused its own fix ("the new
  plan has more steps than the first; only remove or correct steps, never add") and asked "Do you mean to head to the Tilted Plough
  now, or are you suggesting a different route?" CONFUSING: the audit wants a sleep step that f656 makes needless; it does not know
  the room is slept in. My answer `Yes, now.` then went to Pae as talk ("I am ready."). BROKEN: an answer to the game's own question
  taken by a companion. Two separate lines worked (room 54 copper, slept to 6 AM).
- Day 3: an elite bear (+845 XP), level 6. Companions reached level 3 and their health FELL (Pae 117 to 112, Morm 81 to 76): 5.8
  again, left for the balance pass by the owner's word.
- `I skin the brown bear carefully.` once went unanswered as a deed (only companion banter; no harvest, no time) and needed saying
  again. Skinning ruined three of six bear hides.
- THE CAUSE of the undone hand-overs, shown by the debug view on `I give the four bear hides to Ulard Heygate the smith.`:
  "operation action:give crashed and rolled back: Drift: board_stakes: the request at this point differs from the one asked
  (3cdefc... -> 774027...); what the operation read moved" -> "That never quite began. The world is as you left it; say it again."
  BROKEN (engine): the give operation's model request for "board_stakes" (the issuer's stake in the contract) is built from state the
  operation itself changes, so its re-run asks in other words and the drift guard throws the whole hand-over away. Every give to an
  issuer, a contract's person, can fail this way. Fix belongs where board_stakes is asked: ask it before the writes, or from what does
  not move.
- FIXED f673 (board stakes asked inside an operation). The hand-over then failed with a second drift, now in "hire_chat". A new debug
  note (f675) printing what moved between the attempts showed it was not the companion's words: the order of the asks moved. The
  first attempt had room in the turn's budget to rule on the town's situations (an "event ruling"); that ruling was asked and
  charged; the attempt run again found no room, the ruling waited, and the companion's reply came where the ruling's had been.
  FIXED f675: the budget's word inside an operation is read once and kept for its re-runs, like a model's answer.
- After f675 the give stood. But `I hand in the bear hide contract to Emlily.` gave the four hides to the clerk as a GIFT: "You are
  very kind to bring this back without any request for payment at all." The contract is the smith's (Quests: "for Ulard Heygate",
  now 0/4), and nothing said so. BROKEN: four hides (five bears) lost with no warning. Worse, reading the code: a give to the one who
  pays did the same, since the gift is taken before the hand-in that runs after the step. FIXED f676: goods a held contract asks
  for, given to the one who pays, hand it in; given to anyone else (or too few of them), the game asks first.
- STILL OPEN: the first line after the game starts often runs out of the turn's budget ("rolled back: npc_conversation: the turn's
  budget is spent (-1 s left)"), so the line is undone and must be typed again. The prompt cache is cold then, so every call is
  charged in full. Also: every give rules on every situation in town (four rulings on a gift to a clerk: "Gather 6 yarrow",
  "The land agent and the acolyte", "A name on the board", "Talk in Parth"), each finding nothing ("0 kept"), which spends that budget.
- CORRECTION, found later: the hide contract is the GUILD's (the clerk pays it); the Quests pane's "for Ulard Heygate" named only who
  asked for it. So the hand-in to Emlily was right, and what lost the hides was the second fault (the gift taken before the hand-in).
  FIXED f678: the pane says "for the guild, asked by Ulard Heygate". With f676, giving the hides to the smith asked first ("the
  guild's contract asks for that ... give them to the smith anyway?"), and `I hand the four bear hides to Emlily for the contract.`
  then completed it: "Completed: [F] Bring 4 bear hide. Emlily Wickley pays 7S 50C, +310 XP." GOOD.
- Asking Emlily for the hides back: "Of course you can take them; they are yours again." Nothing came back (words with no deed:
  BROKEN, a facade). `I take the bear hides back from Emlily's counter` was then narrated as done with an empty pack, and the next
  passage still had "the heavy bear hides shift over your arm". FIXED f677 (the engine refuses a good that does not lie here); the
  person's promise to return a thing is still words only (OPEN).
- Four more bears (lines ~130-170): two hides in four bears were ruined by skinning. Level 7 on the first bear. A round's narration
  failed three times once ("The round holds: what was struck was struck. The words for it did not come."): an honest stand-in.
- The narrator gives the player wounds they did not take: "Morm presses a cloth to the graze on your shoulder" at 143/144 health,
  after a fight in which nothing touched me. CONFUSING (repeated).
- The turn's budget again: `We go to the guild house and I hand the four bear hides to Emlily for the contract.` The walk stood;
  the give was rolled back ("narrate: the turn's budget is spent (-3 s left)") after four optional situation rulings, each ruling
  "0 kept". BROKEN (engine, OPEN): optional rulings spend the time the required passage needs, and the player's deed is undone.
  Rulings on Parth's situations also run on fights in the Greywood.
- Road to Kelpmoor (4th day): a REEF SHARK burst from a fissure in a dry salt road, and the cover offered was "a narrow doorway" and
  "an alley mouth" on open flats. CONFUSING (an encounter and a battlefield that do not fit the place). The passage also said my
  "pack heavy with hide" after the hides were handed in, and named me in the third person mid-round ("Pim Quillfeather watches
  from the rear") right after my own spell.
- Kelpmoor at 1 AM: `We find an inn and I buy a room for the night so we can sleep until morning.` -> the audit again refused its
  own fix ("more steps than the first") and asked "Do you mean to simply buy the room, or are you looking to settle the fee
  first?" CONFUSING (second time; owner decision f332 says ask). My answer `I just want to buy a room and sleep until morning.`
  became talk to the watchman and a wait: he said "Room for one night? Yes, I can show you where.", I slept to 6 AM, and no coin
  was paid (25S 13C before and after). BROKEN (words with no deed: a room offered by a man who has none to sell).
- The arc "Discrepancy in the Chronicles": the Story pane says "the first sign of it is at Kelpmoor. Ask there." I asked the
  watchman (twice), went to the Knotted Rope, the wharf and a watchful gnome, and tried to persuade the watchman: nothing. The
  watchman sent me to "Aldle or Nedie at the pier", names that are no one (the engine itself flagged the wharf: "refusal (facade):
  walked to 'kelpmoor_wharf' ... with nothing real there", yet the passage filled it with people). `We go to the Knotted Rope and I
  ask whether anyone has noticed something wrong` walked me into the tavern and then BACK OUT to the watchman ("You are back at
  Kelpmoor.") to answer. `I ... try to persuade him: "..."` rolled no check. BROKEN (a blind player cannot find the arc's contact:
  nothing points to them), CONFUSING (the walk out of the tavern; persuasion without a check).
- FIXED f679/f680 (code, after the Kelpmoor stall): arriving at an arc contact's place now names them, by name and trade, and the
  contact is there at any hour while their step is open. Not yet seen in this save (the step's town is behind me).
- Parth, 4th day: took three Greywood hunts in one line; the reading took two and dropped the third, and the audit asked "Do you
  mean to accept the contract, or are you trying to modify the list of targets?" (third confusing audit question). My answer
  re-ran the line: "You can hold 2 guild contracts at once" and "Three things at a time: not done - Accepting the contract to hunt
  2 boars.." GOOD (both told), small: a double full stop. A fix letting the audit add the rest of a list was built and withdrawn
  (the review showed it would let the model add buys, coin and attacks the player never asked for): OPEN for the owner.
- Bears (3, elite among them) and wolves (4): both handed in by words to Emlily, 310 XP each. Level 8. Emlily said "I have received
  these hides from you" for a hunt with no hides (CONFUSING), and the passage spelled her "Emily".
- "The matter of the land agent and the acolyte at the temple door is lost, for all that was done." and three more such lines for
  matters I never touched. CONFUSING: "for all that was done" says I tried.
- At the Tilted Plough, in two lines (go; buy a room and sleep): paid 53C and slept to morning. GOOD. A watchman "closed the
  distance" and gestured to me in the passage; my greeting got only companion talk (a man in the story, no one in the scene).
- The King's Pass road stop: a wolf hide jerkin (4 armor) picked up and equipped, a better armour than mine. GOOD (no ledger line
  said I took it; only the pack showed it).
- The Rat-King's Stronghold, floor 1 (orcs and orc war chiefs, level 8): "It is pitch black down here and you carry no light ...
  (-20). A torch from a chandler fixes that." GOOD and clear; but every passage after had "the sputtering orange glow of the torch"
  and "the circle of your torchlight". BROKEN (facade: the narrator ignores the dark the engine keeps). The last chamber's passage
  had "four subordinates" around the war chief; the engine had one foe (BROKEN, narrated foes again). A war chief yielded and was
  told TWICE in one round in different words ("gives up the fight and yields; what becomes of them is yours to say" and "The captured
  orc war chief throws down her weapon and yields. Question her, let her go, hand her to the watch, or put an end to it.");
  the fight's passage called the chief "he", the told line "her", and after I (not reading) attacked again the passage killed
  "Marek ... the captive man". CONFUSING (the yield told twice; a foe's sex changes line to line). Floor cleared, level 9.
- FIXED f681: the yielding is told once; the captive note now reads "... is your captive now, bound at your side. Question him, ...".
- Ironvein (6th day): at 4 AM the inn "No one here is selling anything." (the innkeeper keeps 6 AM on; the refusal does not say
  so, and the passage had a man wiping tankards: CONFUSING). Waited to 6, room bought. `We go to the Ironvein guild hall and I tell
  the clerk ...` read "the clerk" as Parth's Emlily ("aimed at 'emlily_wickley', who is not here") and asked; my answer
  `Heading to the guild hall.` got "That still didn't come through" and the tavern-master took my report. BROKEN (the clerk of
  the hall I am walking to; an answer to the game's own question not taken). Plain lines worked: floor 1 paid at Ironvein.
- The travel passage to Ironvein ran "noon to late afternoon ... by evening ... before dawn" for a three-hour night walk.
  CONFUSING (the passage's hours are not the clock's).
- Parth, 7th day: `I take the contract to hunt 2 giant crabs in the Shipwreck Shoals.` took "Hunt 3 sahuagins in the Tidepool Caves"
  with no word (the crab posting had left the board; the "2" was read as the second posting). FIXED f682.
- Kelpmoor, 7th day, on f679: "Someone in Kelpmoor should know more: Fipen Copperpot, the noble." GOOD (shown before the travel
  passage, a little early). Persuading him rolled nothing (plain talk, trust +1 a line toward a gate of 65). FIXED f683 (a social
  act in the player's own words rolls its check); after it: "persuasion: 49% ... rolled 23", success, and the clue: the battle maps
  moved to a manor in the Blackpine Forest.
- Road to the Blackpine: a level 15 mimic, told twice in two passages (the road's event and the encounter). Won in 4 rounds,
  +1230 XP, a bone crossbow: level 10. Arriving at the Blackpine, the arc's ending ran by itself: "Lore - success: your proof is
  too strong. Vance Thorne gives way. The Chronicles of the Great Siege is ended." I never chose to confront anyone, never learned
  what the Great Siege was, and the passage before had already shown "the captive Vance Thorne" bound beside me. CONFUSING (an
  ending decided for the player on arrival; the story's own name told only as it ends). The narrator also named a "Vance" walking
  with us in the passage after, which matches the captive.
- Parth, 9th-10th day: `I hand Vance Thorne over to the watchman.` -> "There's no one here to give that to.", though the arrival
  passage had "A lone watchman patrols the perimeter" (a narrated person no one can speak to, again). Discrepancy handed in by words
  (310 XP): "You have earned rank E on paper. To hold it you must win a trial ... say "I'd like to take the trial"." GOOD.
- The rank E trial: "Nobody dies here: the first blow that would end a fighter decides it. No potions or draughts. Your
  companions and hired party wait outside." GOOD and clear. Won against Eula Garth (level 14 mage) in 6 rounds, left at 63/164.
  The passage after had Pae and Morm "behind you" (they were outside). Rank E, level 10.
- Rank E contract "Hunt 4 awakened trees in the Blackpine Forest" (1600 XP), 10th-11th day. Road stops on nearly every leg (a bronze
  shield, a bone club), each one more line to type on a long road. A cult fanatic (level 13) yielded mid-search and became a
  second captive; the surrender was in the passage and f681's captive line followed (GOOD). BROKEN (again, the narrated-foe class):
  a search found signs, the passage showed the awakened tree itself "twitching ... vibrating", and `I cast Twin Flare at the
  awakened tree.` -> "Twin Flare is a fighting technique - save it for a fight." Following the tracks found it. Four trees,
  level 11; the trees hit hard but fire works.
- 12th-13th day: trees handed in (1600 XP, level 12), then "Hunt 4 ogres in the Greyhollow foothills" (1600 XP, level 13). An
  ettercap (+609) and two bandits (+607) on the roads. `We wait here until eight in the morning.` stopped at 6:00 (dawn): the hour
  named is not read (CONFUSING; "two hours" worked). `Twin Flare at the ogre.` with no ogre about was read as an attack on
  `hire:0-0`, Pae, and refused only because there was "nothing here to fight" (BROKEN, dangerous: an attack aimed at a companion
  for a foe not there). A passage ended with a stray `",` (JSON leaking into the story, BROKEN). Passages keep giving me "your
  torchlight" with no torch. Road stops on nearly every leg.
- Where it stands (13th day): Pim level 13, rank E, 1G 16S; party Pae, Morm, Gusmund level 6; two captives still walking bound
  with us (Vance Thorne, a cult fanatic) since no watchman could be found to take them; "Hunt 3 sahuagins in the Tidepool Caves"
  still held.
- FIXES after level 13 (the owner chose: fix the biggest open problems first, then play on):
  f684 a situation's ruling met in the player's own step waits and is ruled after the line, all of them while the budget has room
  (the give undone by four rulings); f685 a fighting spell or blow at a creature of the place that is only tracked goes looking for
  it and opens the fight with it, and an attack read as aimed at a companion hunts the creature the line names (the awakened tree,
  the ogre read as "hire:0-0"); f687 a wait until a clock hour waits until it; f688 a passage's stray closing quote and comma cut.
- Pae (a woman) on the hand-over: "Pae's jaw sets firmly while she watches the coins slip into another traveler's palm." No coins
  moved; hides did. CONFUSING (the companion's line misreads the deed).
- 14th day, the Grey Mountains (level 13 to 15), griffons for the guild: "Hunt 3 griffons" and "Bring 3 griffon down". With a
  griffon just killed, `I pluck the griffon's down carefully.` was once read as a harvest and once as an improvisation, refused and
  narrated beside "the drake's carcass" (BROKEN). `Chilling Touch on the griffon.` on the old build hunted a saber-toothed tiger
  (the substring fallback f689 removed); a fight with it won, level 15. A companion asked "Is there a dead griffon here I can still
  pluck?" answered "It bled out too much" (an invented reason, CONFUSING). Narration again puts "63 damage" and "graze, 14 damage"
  inside the prose sentences.
- FIXES: f689 a creature named in a line with no target read is read by whole words (no more tiger for a griffon); f690 a part of a
  fresh kill named in an improvised step (griffon down, boar meat, a wolf hide) is the harvest. Seen live after f690: the pluck
  line read as a harvest, "Harvested: raw griffon down x2", contract ready. GOOD.
- Ironvein, 14th day: `I go to the guild hall and hand in the griffon contracts.` was a walk and a talk to a guild contractor,
  shown as "the stout wanderer", who said "Let me see those papers then"; nothing was handed in (BROKEN). Naming the clerk worked:
  both paid, 3200 XP. FIX f691: a hand-in said to no one, or to someone here who pays for none of it, goes to the one who does.
  The hall passage gave the gnome clerk wire-rimmed spectacles (Pim's own), a quartermaster and a guild master who may not exist,
  and "watch From shadows" with a capital mid-sentence (small).
- Ironvein board (level 15): `I take the pegasus bounty and the gargoyle bounty.` took both (4/5 contracts toward rank D) and the
  page showed only "Heard of: the Ironcrown Peaks (on your map)" (BROKEN, the silent take seen earlier). FIX f692: a contract taken
  at the board is told whatever quiet lines the turn showed (the heard-of line, a change in the room, a companion's aside).
- Grey Mountains again (level 15 to 16), the pegasus bounty: a berserker opened a fight on arrival with "No telling how it opened,
  only that it has: berserker, one alone, and the first moves already made." (an odd line, CONFUSING). Two pegasi fled at low
  health ("They got away"), one an elite. After `I follow the hoof prints.` the debug rolled a pegasus and the engine held it in
  view, but the passage showed only tracks and a tuft of hair: a creature the engine has here, never shown (BROKEN, the other face
  of the narrated-foe class). `We chase the wounded pegasus` brought the bounty pegasus at full health while the passage told the
  wounded one collapsing (CONFUSING). One passage called the pegasus both "stallion" and "mare". Bounty killed.
- Leaving Ironvein at 12:50 PM the passage said "Morning light hits the road ahead" (the time-words class, still open).
- To the Ironcrown Peaks: "What you did stands; the telling of it slipped away." The passage was refused twice for the word "mine"
  in mining country (BROKEN). FIX f693: "mine" is first person only as a possessive; a king's numeral is no "I".
- The gargoyle bounty came to the search on the first try; killed in two rounds.
- Back at Ironvein at 7 PM: `We head back to Ironvein, to the guild hall, and I hand in both bounties.` The clerk keeps the desk
  by day and was gone; the talk went to the contractor, who said "Toss 'em over here", and nothing was handed in or paid, with no
  word why (BROKEN, words with no deed). FIX f694: work handed in that this listener does not take is told so, with who pays and
  whether they are here; the listener is told nothing was handed in. (Pae also started a tavern brawl in the guild hall and I paid
  60 copper for a round: fine, but "the next table over" in a guild hall is odd.)
- Ironvein, night of the 14th: `We take rooms at the inn and sleep until morning.` bought no room; the game said "You rested, but
  not as you would in a bed" and the passage said "You settle into bed alongside your companions" (BROKEN, both ways). FIX f695: a
  sleep that asks to take a room takes one, and the rest's passage is told where they slept. A craftswoman then came to my table
  at dawn with a parchment and beckoned me outside (a matter: "Rynn Bromrakk comes looking for the player").
- 15th day, Ironvein: at 6 AM the clerk "isn't here at this hour" (GOOD, plain); waited until nine (f687 worked live) and both
  bounties were paid, 4000 XP, level 17, 6/5 contracts toward rank D. Took the will-o'-wisp hunt and the giant snake bounty at
  Willowmead: the take was told (f692 live, GOOD).
- The road to Willowmead: an ambush passage read "a swarm of beetles (elite) surges forward" (BROKEN, the game's tag in the story),
  with "stacked crates ... a narrow doorway" on the open King's Road at night (town cover on a road, still open). FIX f696: a foe is
  named to a narrator plainly everywhere (the ambush, a sighting, the who-is-here, a risen thrall, a companion's orders).
- Two lizardfolk at the wetlands' edge; `Twin Flare at the beetles.` after the beetles were dead was fairly turned on the lizardfolk.
- `I search the marsh for will-o'-wisps.` ended a matter in passing: "Gone missing near the Willowmead wetlands is ended - by way of
  'Find what is in the Willowmead wetlands'" with nothing in the passage of anyone missing (CONFUSING: an ending the player did not
  see; the arc-endings class, still open).
- Willowmead wetlands, 16th day: the search passage showed "several points of light" among the reeds, but no wisp was in the engine
  (the narrated-foe class). `Twin Flare at the will-o'-wisps.` was then read as words to Pae, who answered (BROKEN). FIX f697: a line
  that opens with one of the character's own abilities is that ability. `I attack the will-o'-wisps.` was refused by the plan audit
  ("aimed at 'will-o'-wisps', who is not here") with the question "Do you mean to strike at the shadows, or something else?"
  (BROKEN). FIX f698: the audit lets an attack at a creature of this place go hunting.
- `I hunt through the reeds for the will-o'-wisps.` brought the giant constrictor snake bounty instead (fair: a bounty's target can
  come to a search); killed in three lines. Wisps still to find. Level 17.
- FIXES after level 15 (this stretch): f689 whole-word creature reading; f690 a fresh kill's part is the harvest; f691 a hand-in goes
  to who pays; f692 a contract taken is always told; f693 "mine" as a place is not the first person; f694 work handed in that the
  listener does not take is told so; f695 a sleep that asks for a room takes one, and the passage knows where they slept; f696 foes
  named plainly; f697 an ability opening the line is the ability; f698 the audit lets an attack at a creature of the place hunt.
- FIXES chosen with the owner (16th day, after level 17): f699 the plan audit may add a step the player's own words ask for, never a
  deed they did not (the owner's decision, in GOALS.md); f700 a creature in view is told to every passage and frame while it stays,
  and moves on after an hour; f701 a passage may not show a creature of the place the game does not have (sent back once, never the
  telling lost). The owner asked that no earlier decision be taken as law where it stands in the way.
- After the restart on f701 (Willowmead): the first line's passage timed out on the cold model ("the telling of it slipped away";
  the cold-first-try class, still open). A search found a real will-o'-wisp (one, level 10); the opening said "Two wisps emerge"
  (CONFUSING: a miscount f701 does not read, as "wisps" alone is no whole name). The opening was sent back once for "wire_mended"
  (the gear line's own word leaking, caught by hygiene). "The matter of a demand at Ironvein is lost, for all that was done." came
  in passing with nothing shown of it (the arc-endings class). Wisp killed, hunt 1/5. No passage was sent back as a phantom in the
  fight (no false rewrites seen).
- EXPLORATION AND IMPROVISATION (the owner's focus from the 16th day, level 17):
  - `I explore deeper into the wetlands` found a half-sunk stone ruin, and wading to it later moved me into a real part
    (`feature:willowmead_wetlands:half_buried_ruin`) with carvings on a standing wall. GOOD. The reading of the explore line added a
    seek for "giant constrictor snake" (a bounty already done) on its own (small). The Places pane still said "In the Willowmead
    wetlands: Nowhere else" while I stood in the ruin (CONFUSING).
  - `I press a page of my journal against the carvings and rub charcoal over it` was read as an attempt; the passage ended "as you
    try to capture the depth of those grooves" with no outcome, nothing was kept, and I carry no charcoal (CONFUSING: an attempt
    with no result, and a tool the pack does not hold).
  - `I climb up onto the standing wall to get a view across the marsh` worked, 35 minutes, but the view showed nothing the game
    holds: no landmark, no way on (a missed payoff for going high to look).
  - "A track north, you do not know where it ends" (Places pane): a fork (left in the wet, right on higher ground), and the right
    led to Willowmead village in 36 minutes. GOOD: a road out that is unknown and a choice of forks.
  - Willowmead: `I set up a stool by the road and offer to write letters for the villagers, a copper a page.` became a real work
    offer (write a page, 20 copper, an hour), and `I take the job you offered` was done and paid. GOOD (an improvised trade made
    real). But the passage set out a stool, parchment and ink pots I do not own and a small crowd of watchers (the narrator's
    invented props), and between the offer and the job the farmer said "I don't have a letter ready this very moment" (his words
    against his own offer). An intent's summary ended in "</div>" (HTML in the model's reading, unseen by the player).
  - To Greyhollow (18 hours): a road sight of "a jagged fissure in the limestone hillside" bleeding violet light; the walk went on
    past it (sights do not stop the walk) and it could not be gone back to. The passage after it told the journey over again in
    daylight ("dust rises behind each step") after the moonlit fissure, and Greyhollow, a mining town, had "docks" (CONFUSING).
    "The matter of the stranger the hall talks of is lost, for all that was done." in passing (the arc-endings class, again).
  - `We go back down the Old Quarry Road to the glowing fissure we passed.` became a ten-hour walk toward Parth, and on the road a
    black pudding of level 32 (637 health) ambushed a level 17 mage with level 8 companions: "danger estimate: deadly, 9% win rate"
    (BROKEN for play: an ordinary road with a foe nearly twice the player's level and no warning). Fled: "Breaking off was all but
    sure", got away. The flight's passage said "our tails", "we put distance" (the narrator's first person plural).
- FIXES the owner asked for after the exploration stretch ("build 1-5"): f702 a sight seen on the road is kept as a landmark of that
  road, listed under Places and walked back to; f703 an improvised act that works always tells what it came to ("It works: ...");
  f704 a climb made for the view makes out the real places around, with direction and walk, and puts them on the map; f705 no foe is
  met above its place's danger (the black pudding came from a level bug), and a road ambush is at most three levels over the party.
  The fourth, no props the pack lacks, was built and withdrawn: a word list of carried tools refused far too much ("the rope bridge",
  "I hammer on the door"), and it collides with decision Q34 ("trifles can be supplied by the place"). OPEN for the owner.
- The owner kept Q34, and asked that a supplied trifle come from somewhere real: f706 (a kit good the act uses is carried or the act
  is refused; a trifle the ruling names is made lying here and told where it came from).
- AFTER THE RESTART ON f706 (Parth, 17th day, level 17):
  - `I climb up onto the roof of the old granary to get a view` (partial): "the south fields (to the south, a few minutes' walk)"
    made out and put on the map. GOOD (f704 live).
  - `I copy the inscription on the old well onto a page by rubbing charcoal over it`: the ruling named no need, so no charcoal was
    made or placed, and the passage again conjured "a stick of burnt charcoal" and parchment (failure rolled). f706 asks the ruling
    to name such trifles; this time it did not (OPEN: the prompt request is not enough on its own; an engine side check is wanted).
  - To the Greyhollow foothills: 800 minutes walked straight through the night with no stop or road event (0.5 a leg over two
    legs: no event is a 1 in 4 chance, fine). The foothills were told "cleared of those threats recently" (true: the hunts there).
  - `We set off for Ironvein to hand in the snake bounty.` was REFUSED and asked back: "Are you telling the group we're leaving, or
    are you asking to start the trek?" (BROKEN: a plain move). The reading dropped the talk that only narrated the move (right);
    the audit then wanted that talk back, f699 refused the addition twice, and the whole line was refused over it. Fixed as f707:
    what the audit would add unasked is dropped, and the rest of its correction is weighed; a sound first reading stands.
  - Answering that question with `Start the trek to Ironvein.` went to Morm as chat ("intercept: hire took the line"): the party
    talked of leaving in three voices and nobody moved (BROKEN: a plain move lost). The line came straight after Morm spoke, and
    the followup's command list holds neither "start" nor "trek". Fixed as f708: a line naming a real place right after to / toward
    / for is a step for the reader, in any wording; a question about a place stays the hire's.
- AFTER THE RESTART ON f708 (the Greyhollow foothills, 18th day):
  - The first line after the restart ran out of the turn's budget on the cold model ("The moment passed before anything happened";
    the cold-start class, still open). Sent again, `We set off for Ironvein to hand in the snake bounty.` walked: "audit dropped
    its own unasked additions" (f707 live). GOOD.
  - The walk was 1800 minutes (30 hours) foothills to Greyhollow to Parth to Ironvein, straight through a night with no camp and no
    word of weariness (OPEN for the owner: a journey over a night could stop to camp, or say what the night cost).
  - On the King's Pass, a sight bearing on a matter: two dazed men under a sodden lean-to, "We dig. At night. I don't know for
    what. I know where." GOOD, a real hook, noted in the strip and kept under Places, "ON THE ROADS" (f702 live). The passage after
    it told the climb over again from its start (the retold-journey class).
  - Ironvein: a watch guard was "she" and "his chest" in one sentence (the sex-change class).
  - `We go back down the King's Pass to the two dazed men under the lean-to.` was taken by the way-out reader as leaving by the
    King's Pass: an 800 minute walk toward Parth (BROKEN: the kept sight was named by what was seen, never by its title "The Echo
    of the Greywood", and the line named the road). Fixed as f709: a landmark is named by what was seen there too, and a way out
    down its road to it goes to it.
  - On that road a bandit ambush (two, trivial at level 17), fought in two rounds. The passage carried props from Ironvein ("one
    guard's poleaxe and another miner's cart aren't within reach"), had the narrator walk me "toward the lean-to" that was not
    here, and turned the shortsword into a scimitar and boiled leather into a cuirass. "The guild here think well of you" was told
    on an empty road. My second spell named the axe bandit, who was already down; it went to the other with no word of that.
  - After the fight the walk went on to Parth in the same turn, and the budget ran out: both the fight's aftermath and the arrival
    were left untold ("It happened, and it holds. The story of it will have to wait"). I stand in Parth at 2 AM knowing nothing of
    getting there (CONFUSING: a road fight and the rest of a journey are too much for one turn's budget).
- AFTER THE RESTART ON f709 (Parth, 20th day, 2 AM):
  - `We go back up the King's Pass to the two dazed men under the lean-to.` walked 512 minutes (the kept distance) to a stop on the
    King's Pass, and the passage showed the two men under the lean-to. GOOD (f709 live). On the way another matter showed on the
    road: a fresh signpost, "BY ORDER OF THE SHEPHERD: ALL PASSAGE MUST BE REGISTERED" (Who rules Parth). "The guild here think
    well of you" was again told on an empty road. The arrival passage turned the road stop into a settlement on market day ("you
    crest the final rise toward the settlement... stalls line the central area") before finding the lean-to (CONFUSING).
  - `I crouch beside the two men and ask them gently where it is they dig at night.` went to Gusmund, my own archer: "Keep your voice
    down." (BROKEN for the payoff: the men a kept sight shows are words in a passage, not people of the game, so going back to them
    leads nowhere and the matter's hook ends there). OPEN for the owner: people a road sight shows made real at its stop, and a
    matter's people knowing its next clue.
- f710 built on the owner's go (the people a matter's road happening shows are people of the game, holding its next clue). After
  the restart on f710: `We walk on up the King's Pass to Ironvein.` (288 minutes, no road happening). On arriving, a matter fired
  ("Norvald Balarakk comes looking for the player", The market at Ironvein) but the turn's budget was spent: "The thing is settled.
  No passage came, and none is needed for it to be so." (CONFUSING: nothing was settled; someone came looking and the player was
  never shown it). Looking about the gate found nobody seeking me: the moment is lost (the budget-after-a-walk class, with a told
  line that says the opposite of what happened). f710 itself not yet seen live: both matters near here have already shown on the road.
- AFTER THE RESTART ON THE LINE PASS (f712, Ironvein, 20th day): `I go to the guild hall and hand in the giant snake bounty.` was
  handed in and paid (27 silver 50 copper; level 18), but the cold model's first turn spent the budget before the clerk's reply,
  and two stand-ins printed for one turn: "You see it through." and "You got as far as Go to the guild hall; the finished contract
  'Bounty: ...', paid 27 silver and 50 copper. The rest didn't happen." (CONFUSING: a step summary pasted mid-sentence with its
  capital and a semicolon, and "the rest didn't happen" though the hand-in was paid; only the clerk's words were lost). The
  part_stood line's {done} is built from what each operation "did": model summaries in the imperative, a paid line, a walked
  phrase; no join reads right. OPEN: have each operation record a finished clause ("you walked to the guild hall", "you handed in
  ... and were paid ..."), and print one stand-in, not two, when a passage is lost on a line that stood in part.
  - `We leave Ironvein and take the road toward the Ironcrown Peaks.` (155 minutes): the audit dropped a narrating talk to Pae and
    the move ran. A saber-toothed tiger met on the pass, killed in two rounds. The hires' level notes read "Pae Tamalaga has gone
    as far as an F-rank can on their own; they would need to be promoted." ("they" for Pae, whose sex the game knows, and a
    semicolon: engine/party text the line pass did not reach). The passage said "only stone remains" and then "tall grass". After
    the fight the party spoke like a machine: "Another fight finished now." / "Moving forward next. Route remains hard." (the
    companions' dialogue voice, an open goal).
  - `I scramble up the nearest crag to get a look at the peaks and the land below` failed its roll (fair), and the line's second
    step (look at the land below) was dropped with it; the passage ended "gravity remains absolute".
  - `I explore along the pass toward the cairns` found a real part (the dripping chamber, a pool under a hole in the ceiling); the
    climbers' belongings sought got no word. The Places pane still says "IN THE IRONCROWN PEAKS: Nowhere else" (open, as at the
    wetlands ruin). Going to the pool, the narrator walked me to the chamber I already stood in.
  - `We make camp by the pool and sleep until morning.` made no camp: a camp exists only as an ability's shelter use, and Pim has
    none, yet the rest line tells every player "a room at an inn, a camp or a temple" restores fully (OPEN for the owner: let
    anyone make a camp, with time and maybe a bedroll, or stop offering it to those who cannot). Sleeping in the open, a griffon
    (level 13) woke us at 2 AM; killed in four rounds. A line typed and sent while a turn was still running was dropped with no
    word (it was neither queued nor refused).
- NPC SPEECH (the owner's new focus, 21st day): the companions read as machine-made in nearly every line:
  Gusmund "Another fight finished now." / "My father taught me at home during winters. He said a steady hand makes same difference
  as heavy bow." (articles dropped); Pae "Moving forward next. Route remains hard." / "It is just a scratch. I can still hold my
  shield." (no contractions, a stock line, and Pae fights with a two-handed blade); Morm "It will need a dressing before we sleep.
  Even if she says it is small, the cold makes things worse." (stiff but sensible) / "The path is blocked by my own body now. I
  must find a flat place to stay." (nonsense). The speech rules (quirks.yaml style_rules) already ask for contractions and plain
  talk, and the exemplars (voice.yaml) are good human writing: the model does not hold to them in these calls. No townsperson
  spoke this stretch: every one tried was the narrator's invention (a merchant, a watchman), and a berserker talked down never
  spoke (a beast, no voice).
- Sleeping in the open on the Ironcrown Peaks: three attacks in about three hours (two griffons, a berserker): rest is all but
  impossible there (with the camp question above). The narration had "no caves to huddle inside" while we slept in a cave chamber.
- Ironvein at dawn: "the merchant isn't here at this hour." (a told line starting in lower case; the merchant was the arrival
  passage's invention). The narrator gave me "your half-empty grain cart".
- BROKEN: `I go to the Cinder Mug and lean on the bar.` became an 810 minute walk to Parth's trading square. Two lines before had
  been asked back ("ask the watchman" aimed at a watchman of another place; "go to the market square", which Ironvein has none
  of, asked against Parth's square 13 hours away); a line after a question is always read joined to the asked line (world.py
  understand, f321: "Read the earlier line and this answer together as one intention"), the joins chained, and the audit added
  the earlier lines' steps to the new one. On the King's Pass, a ghast (elite) on the way, killed.
- AFTER f713 to f716 (17 November, Parth to the Willowmead wetlands, 21st to 23rd day):
  - The loaded game's opening passage said "You move into the Cinder Mug" while Pim stood in Parth's trading square: the Cinder
    Mug is Ironvein's, and the last typed line had asked for it (the opening retells the last line as if it happened).
  - The first turn after loading spent its budget again (npc_conversation timed out with 10 s left). The new part line read well:
    "You went to the Tilted Plough, but you didn't manage to speak with the broad-shouldered host. Try that part again." But
    the silent-turn line printed with it: "Nothing comes of that here. Try it another way..." (CONTRADICTION: the walk stood;
    the silent check, refusal 'silent', should stand down when a part line is printed).
  - The host (Ediford Bardale) spoke like a person: "Not as quiet as I'd like it to be... Folks are starting to get twitchy about
    those woods again" / "A few folks passing through from the River Road mentioned they saw something... queer." But the engine
    logged both pieces of news as ones he does not know ("ignored reveals Ediford Bardale does not know: Willowmead slow, Travellers
    on the River Road say..."), and he said them anyway, nearly word for word: the knowledge gate is in the reveal record only;
    the truth view's "news that has reached here" puts the words in his mouth (LEAK, pillar 1).
  - The room and the night's sleep worked (full rest). Gusmund "is grey in the face... Last night's inn is still in him." (fine).
  - BROKEN: `After breakfast we set out along the River Road for the Willowmead wetlands.` was read as one talk to Pae, the whole
    unquoted line as her speech; nobody moved. (The narrated-talk repair turns such a talk into its other steps only when the
    interpreter gave other steps; here it gave none.) `We travel to the Willowmead wetlands.` worked: 530 minutes, a road happening
    on the way (a ring of stones round a faded ribbon), a crocodile on the causeway.
  - `We follow the causeway deeper into the wetlands...` while in the wetlands was read as a move to the Mirewater Fens, 18 hours
    away; the far-place question caught it ("Do you mean to head toward the Mirewater Fens, or are you looking for something else
    nearby?") and `Something nearby. We explore the wetlands around us.` explored (f713 let the question go: good).
  - Three fights in two hours of wandering (crocodile, three ghouls, a toad met and fled), then a will-o'-wisp at midnight in camp.
  - `I kneel by the ghouls and look for where they came from` ran a look and a search, and both passages told the same invented
    tracks (drag marks, frantic prints, slime on a branch: told twice in one turn). Following them (`We follow the slime trail and
    the drag marks into the reeds.`) led nowhere: an explore that re-described the marks (FACADE: a clue the engine does not hold).
  - `We leave the toad be and follow the slime trail...` fled the toad and dropped the trail step with no word (a flee ends the
    line; the part line does not cover a fight's turn).
  - f716 LIVE: `We find a dry rise off the causeway, make camp and sleep until morning.` moved to the mossy rise, made the camp
    ("You find a level patch of ground and make camp there."), slept; a wisp found us at 00:27 (the halved chance); after it,
    `We go back to sleep in camp until morning.` slept to dawn. The camp line printed before the passage that walks to the rise
    (ORDER: a told note is drawn before the turn's passage).
  - The narrator again gave Pae a heavy shield (she fights two handed), a toad "a mouth full of teeth", and armor plating to ghouls.
- NPC SPEECH, this stretch: a townsperson (the host) reads human. The companions read machine-made in almost every line:
  Gusmund "I have reached limit permitted by guild rank." / "Supply cost is secondary to safety in those marshes." / "Job stays
  finished now."; Morm "That cost remains uncounted on our ledger yet. Does it change current tide of what we expect today?" /
  "The wetlands are like tide pools when the water rises fast and heavy against stones." / "The ground stays heavy under my boots
  like rising tide water. Do we proceed past these reeds?"; Pae "Will do. Best leave before day gets too high." (fine) / "Good
  move. Better out than in." (wrong idiom) / "Mud is deep here." f714's check does not catch these: they hold one uncontracted
  pair or none. The cause is the tongues (quirks.yaml): the prompt says home shows "only now and then", and the model shows it in
  every line (rime: a small word left out before a noun, formal; salt: boats and weather for moods). OPEN for the owner: let the
  engine decide which lines let home show through (a share in data, like the material offer), and on the others ask for plain,
  fully correct English.
