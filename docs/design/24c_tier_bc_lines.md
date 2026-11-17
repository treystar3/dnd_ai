# f712 Tiers B and C: every changed line, old beside new

For the owner to read before any of it is played (the voice guide: docs/design/24_line_pass.md). Tier B is the authored story content (Orenna, the mentor's fixed narration, the hires' errands, the clerk's fallbacks; the opening and send-off were left as they are, as the owner's own beats). Tier C is the notes printed from code. Six helpers drafted it, each in its own files; a blind reader who did not know which lines were rewritten then flagged about forty, and those were redone (the "new" lines below are the final text). Plain functional notes that already read well were kept and are not listed line by line.

Also changed in this pass: the shop pane printed the narrator's own third person line after a meal ("They eat and feel restored."); it now says "You eat, and feel better for it." The level up line now reads the same everywhere. The web panel's copy of "You don't know your way anywhere from here." matches the game's.

# Tier B review (tierB_review)

## data/world/orenna.yaml

- data/world/orenna.yaml:15 (contact.after)
  old: The stranger listens without moving. When you finish, something in their shoulders lets go, as if they have carried a weight a long way and only now found where to put it down.
  new: The stranger listens without moving. When you finish, their shoulders drop.
- data/world/orenna.yaml:36 (ruin.floors[0].mural, one sentence)
  old: Nothing here is carved as worship. Nothing here is carved as love.
  new: None of it is carved as worship, or as love.
- data/world/orenna.yaml:59 (ruin.floors[2].mural, one sentence)
  old: The freed peoples have turned on the gods who made them, and they are carved without mercy and without shame: refusing, striking, standing.
  new: The freed peoples have turned on the gods who made them, and the carvers were not ashamed of it. The carvings show them fighting back.
- data/world/orenna.yaml:71 (ruin.floors[3].mural, the ending)
  old: At the far end is a door of plain stone, carved with a single line, a place between breath and dust. You know it. It is where she is. It is the room where you met her.
  new: At the far end is a door of plain stone, carved with a single line. You know that door. She is behind it, in the room where you met her.
- data/world/orenna.yaml:101 (trails.lecturer.results.strong success)
  old: ...the eyes closed by someone's hand, and, on the sill, a single wet thumbprint of ash-grey cloth. A watchman...
  new: ...the eyes closed by someone's hand, and a thread of undyed cloth caught on the sill. A watchman...
  (a "thumbprint of cloth" made no sense, and "ash-grey" contradicted the man's "plain undyed cloth")
- data/world/orenna.yaml:122 (trails.warning.results.success)
  old: ...Someone read the warning before its own recipient.
  new: ...Someone read the warning before the friend did.
- data/world/orenna.yaml:140 (executioner.fight_intro)
  old: He draws without hatred and without hurry, and looks at you the way a man looks at a weight he has been handed.
  new: He draws, unhurried. He looks tired more than angry.
- data/world/orenna.yaml:154 (registry.results.partial)
  old: The register is wrong in a way you can see but not read. Combined with the letters and the ledgers you already have, it can only mean one office.
  new: Someone has altered the register. You can't read what it said before, but set beside what the dead have told you, it points to one office.
  (the old line claimed the player already had the letters and ledgers, which a partial trail does not promise)
- data/world/orenna.yaml:155 (registry.results.failure)
  old: The register has been burned along one edge. You will have to confront him without it.
  new: The register has been burned along one edge. You'll have to face the holder of the seal without it.
- data/world/orenna.yaml:167 (confront.strong_evidence)
  old: You lay out the letters, the ledgers and the register, one by one, and with each the High Keeper's authority drains. By the end he has no witnesses left in the chapel at all.
  new: You lay out the letters, the ledgers and the register, one at a time. He reads each one. By the last, he has stopped glancing at the door.
  (matches what the engine does with strong evidence: no guards step in; the old "no witnesses left" clashed with the arrive line, where he is already alone)
- data/world/orenna.yaml:180 (confront.after[0])
  old: The chapel is very quiet. The seal lies in your hand. Whatever the oaths of this kingdom were worth, they are worth whatever the people make of them now.
  new: The chapel is very quiet. You stand there with the seal in your hand, and nobody comes.
- data/world/orenna.yaml:187 (blessing.arrive)
  old: That night you dream, or you do not. The light is thin and the cold is faint, and the voice is so tired that you lean toward it.
  new: That night you dream of a tired voice, so faint you have to lean in to hear it.

Kept as is: 53 lines (contact arrive/ask/speech/decline/go; murals 2 whole and the rest of 1, 3, 4; after_speech, to_order, coin_given; the order's arrive, speech, task; the trails' arrive lines and 10 of 12 results; the executioner's arrive, speech, press, warn, leave, yield; registry arrive, strong success, success; the High Keeper's arrive, speech, begin, seal.ask; Odrin's after[1]; blessing text, line "You said it. I heard.", gain, spent). Odrin's, the eldest's, the executioner's and the High Keeper's speech are their own formal voices (no contractions, by design) and were left alone. Not touched: yield_story (narrator), confront.lines and seal success/failure/quiet (not in my list).

## data/world/mentor.yaml (fixed narration only)

- data/world/mentor.yaml:166 (approach.narrate, paragraphs 2 to 5; paragraph 1 kept)
  old: She is difficult not to notice herself. Somewhere into her middle years and broad through the shoulders, she wears a fitted suit of plate that looks expensive without being ceremonial. The steel is darkly polished, its edges worked with restrained gold detailing, and the breastplate bears the shallow scratches and dents of armor that has actually seen use. / A heavy guild crest is fastened high on one shoulder. At its center sits an enamelled A, marking a rank only one step below the guild's highest. / A greatsword rests across her back in a scabbard worn pale along the edges. Between the armor, the blade, and the rank at her shoulder, she has the look of someone most people would think twice about approaching. / She watches you for another moment, her eyes lingering briefly on what you carry, then seems to make up her mind and comes your way.
  new: She'd be hard to miss anyway. She's somewhere in her middle years and broad through the shoulders, in fitted plate, good and well used. The steel is darkly polished and trimmed with a little gold, and the breastplate is scratched and dented from real use. / A heavy guild crest is fastened high on one shoulder, with an enamelled A at its center, one rank short of the top. / A greatsword hangs across her back, in a scabbard worn pale along the edges. / She looks you over a moment longer, then comes your way.
  (still five paragraphs, still "enamelled A", "greatsword", "crest": mentor_test checks these)
- data/world/mentor.yaml:193 (approach.interrupt)
  old: You have barely begun to do what you meant to when she steps into your path, and it will have to wait.
  new: You've barely started when she steps into your path. Whatever you meant to do will have to wait.
- data/world/mentor.yaml:262 (approach.skip_narrate, first paragraph)
  old: Whatever doubt she had about you seems to have passed. She gives you a small nod.
  new: She gives you a small nod.
- data/world/mentor.yaml:364 (troll_combat.miss_narrate)
  old: The troll's fist comes down on the spot where you were standing, and the earth bucks, and somehow it is not you it breaks.
  new: The troll's fist slams into the spot where you were standing. The ground jumps under your feet.
- data/world/mentor.yaml:400 (troll.scenes[0][0])
  old: The troll comes on in a rush, and the earth bucks under its feet. Maren does not retreat. She sets her boots, rolls one shoulder, and the greatsword leaves its scabbard in a single arc.
  new: The troll comes on in a rush, and the ground shakes under it. Maren doesn't back off. She sets her feet, rolls one shoulder, and draws the greatsword in one sweep.
- data/world/mentor.yaml:401 (troll.scenes[0][1])
  old: The sword wakes. Pale fire runs down the length of {weapon} from guard to point, and the air around her gutters like a snuffed lamp.
  new: Pale fire runs down {weapon} from guard to point, and the air around her goes cold and dim.
- data/world/mentor.yaml:402 (troll.scenes[0][2])
  old: The troll's fist comes down. She is not where it lands. She is inside its reach, one step and one breath, under the swing, close enough to smell the rot on it.
  new: The troll's fist comes down where she was. She's already inside its reach, under the swing, close enough to smell the rot on it.
- data/world/mentor.yaml:403 (troll.scenes[0][3])
  old: She spins. {weapon} comes round in a bright, ringing circle, her whole turn of the hips, every year she has ever swung it behind the blow, and the world goes white-gold at the edge of the arc.
  new: She spins, putting her hips and all her weight into it, and {weapon} comes round in a bright, ringing circle.
- data/world/mentor.yaml:404 (troll.scenes[0][4])
  old: For a heartbeat, nothing. The troll stands there with its mouth open, mid-roar. Then a seam of light opens from shoulder to hip, and the two halves slide apart and strike the leaf mould one after the other, with a sound like felled trees.
  new: For a moment nothing happens. The troll stands there with its mouth open, mid-roar. Then a line of light opens from its shoulder to its hip, and the two halves slide apart and hit the leaf mould one after the other.
- data/world/mentor.yaml:406 (troll.scenes[1][1])
  old: ...and draws {weapon} up from low behind her. The blade catches a shaft of light between the leaves and rings like a struck bell.
  new: ...and draws {weapon} up from low behind her. The blade rings as it comes.
- data/world/mentor.yaml:407 (troll.scenes[1][2])
  old: The sound is one clean note, as if the whole forest had been rung. The troll's charge dies mid-stride as the blade rises through the line of its body from hip to crown.
  new: The troll's charge stops mid-stride as the blade goes up through it, hip to crown.
- data/world/mentor.yaml:408 (troll.scenes[1][3])
  old: It takes one more step. Then the cut finds it, and it comes apart in a rush of dark blood and splintered bark, and the weight of it carries the pieces past her and into the trees.
  new: It takes one more step. Then it comes apart in a rush of dark blood, and its own weight carries the pieces past her and into the trees.
- data/world/mentor.yaml:410 (troll.aftermath)
  old: The fire ebbs out of the blade. Maren shakes the gore from it, and slides it home across her back as though she had done no more than swat a fly.
  new: The fire goes out of the blade. Maren shakes the gore off it and slides it home across her back. She isn't even breathing hard.
- data/world/mentor.yaml:437 (return.narrate)
  old: Maren has been a half step ahead the whole way back, watching the treeline, until the town walls come up out of the fields.
  new: Maren keeps a half step ahead the whole way back, watching the treeline, until the town walls come up out of the fields.

Kept as is: 27 lines (approach paragraph 1 and leave, skip_narrate's "Good hunting.", escort.walk, joined.narrate and narrate_open, joined.taken, arrive.narrate, found_narrate, fight_how, troll.narrate_arrive, troll.scenes[1][0], figure_kill, troll_combat how, join/hurt/guard/strike_narrate, run_fail x3, round_one_hint, hurt_potion, lessons.floor_potion, return.leave, chat.fallback, and the Fixed lines hurt, orders, orders_again, which already read as Maren talking).
Note: no code reads troll.scenes, figure_kill, miss_narrate, round_one_hint or joined.taken (grep of engine/, scenes/, services/); they look like dead data. Edited anyway, as listed.

## data/rules/quirks.yaml (errands ask / yes_line / no_line)

- data/rules/quirks.yaml:177 (errands.protect.ask)
  old: There is a guild courier here. I want an hour to send coin home. It will keep, if you would rather not.
  new: There's a guild courier here. I'd like an hour to send coin home. It can wait, if you'd rather not.
- data/rules/quirks.yaml:185 (errands.wander.ask)
  old: I have never been here. Give me an hour to walk it. I will find you.
  new: I've never been here. Give me an hour to walk around. I'll find you.
- data/rules/quirks.yaml:186 (errands.wander.yes_line)
  old: {name} is gone an hour and comes back with the look of someone who has seen a thing they wanted to see.
  new: {name} is gone an hour, and comes back in a good mood.
- data/rules/quirks.yaml:193 (errands.revenge.ask)
  old: Before we go. I want to ask the clerk after {target}. It will take no time.
  new: Before we go, I want to ask the clerk about {target}. It won't take long.
  (the errand costs 10 minutes, so "no time" was untrue)
- data/rules/quirks.yaml:194 (errands.revenge.yes_line)
  old: {name} speaks to the clerk a while, low, and comes back with nothing new in {their} face.
  new: {name} talks to the clerk a while, keeping {their} voice low, and comes back with nothing new.
- data/rules/quirks.yaml:202 (errands.atonement.ask)
  old: I would like an hour here. Alone, if you can spare it.
  new: I'd like an hour here. Alone, if you can spare it.
- data/rules/quirks.yaml:210 (errands.coin.ask)
  old: I will ask this once. An advance on my pay, {sum}. I have a reason and I would rather not say it.
  new: An advance on my pay, {sum}. I'd rather not say what for.
- data/rules/quirks.yaml:218 (errands.glory.ask)
  old: When you hand that in. Tell the clerk my part in it. Not for the coin. So it is written down somewhere.
  new: When you hand that in, tell the clerk my part in it. Not for the coin. I just want it written down somewhere.
- data/rules/quirks.yaml:220 (errands.glory.no_line)
  old: {name} says nothing, which is louder than most things {they} say.
  new: {name} doesn't argue. The answer stings, though.

Kept as is: 9 lines (protect yes/no, wander no, revenge no, atonement yes/no, coin yes/no, glory yes). coin.no_line is also spoken by the hire with the name cut off (scenes/quirk_actions.py:419), so it was left exactly as is. Every placeholder kept ({name}, {target}, {their}, {sum}, {they}).

## data/world/banter.yaml (clerk.fallback)

- data/world/banter.yaml:22 (warm, clerk)
  old: Maren Holt, as I live. And you have brought someone. Come in, come in, there is a stool if you want it.
  new: Maren Holt, as I live. And you've brought someone. Come in, come in, there's a stool if you want it.
- data/world/banter.yaml:23 (warm, maren)
  old: Not a scratch on this one. Sign them in before the stool gets all the credit.
  new: Not a scratch on this one. Sign them in before they lose their nerve.
- data/world/banter.yaml:24 (warm, clerk)
  old: Of course. Welcome to the guild. The fee is {fee} and then your name goes in the book.
  new: Of course. Welcome to the guild. The fee is {fee}, and then your name goes in the book.
- data/world/banter.yaml:28 (cold, maren)
  old: No, it is a book, and you are the person paid to write in it. Pen up, please. They are paying {fee} like everybody else.
  new: No, it's a book, and you're the one paid to write in it. Pen up, please. They're paying {fee} like everybody else.
- data/world/banter.yaml:30 (cold, maren)
  old: Politely, if you do not mind. It costs nothing, and I will remember who bothered.
  new: Politely, if you don't mind. Manners cost nothing.
- data/world/banter.yaml:33 (neutral, maren)
  old: For today. They need signing into the register, and I would take it as a kindness if you did it properly.
  new: For today. They need signing into the register, and I'd take it as a kindness if you did it properly.

Kept as is: 6 lines (warm "See? Nobody bites. Mostly."; the cold clerk's three lines, whose stiffness is the clerk being cold, and "register is not a charity" is pinned; neutral clerk x2 and "There. Not so terrible."). Maren's voice note says contractions; her lines now use them.

## data/opening.json and data/send_off.json

No change. Kept as is: opening 10 beats, send-off 2 beats. tools/sim/goes_on_525_test.py:164 calls these "the owner's own beats", so I treated them as the owner's writing. Candidates for the owner, not applied:
- opening beat 2: "You know it the way you know your own name: without being told, and without being able to say how." (doubled "without" reads a little written)
- opening beat 8: "There are things stirring in the world that no one is watching for ... I can send you with something to meet it." ("things stirring" is a stock phrase, and "it" does not agree with "things")
- send-off beat 2: "faster and faster, with no time to breathe, no time to understand." (the doubled "no time" tail; "wave" then "black water" mixes two images)

## Checks
- All six files load (yaml.safe_load / json.load).
- data_check.check() prints [] (no dash problems; data_words_problems clean for these files; hyphens in words like "grey-green" are allowed by DASHED).
- No golden in data/replay contains any of the old fragments.
- Ran: mentor_test, banter_test, orenna_chain_test, orenna_test, opening_test, playthrough_1030b_test, nightrun_review_test pass. goes_on_525_test fails one check, "without the lines, creation's own note is today's" (it wants "The model couldn't make sense of that"), which comes from someone else's scenes/ edits, not these files.

Tests that pin old wording:
- None of the changed lines is pinned. tools/sim/playthrough_1030b_test.py:171 passes the old skip_narrate text as its own literal to mentor_narrate (it does not read the yaml), so it still passes; update it only for consistency if wanted.
- tools/sim/banter_test.py:90 pins "register is not a charity" (kept unchanged).
- tools/sim/mentor_test.py:73 needs approach.narrate in 5 or more paragraphs containing "enamelled A"; still true.


# tierC1_review: scenes/world.py, exit_actions.py, road_actions.py, mount_actions.py, camp_actions.py

## scenes/world.py

- scenes/world.py:472
  old: Something stirs nearby, but you are not noticed and it passes you by.
  new: Something stirs nearby, but it doesn't see you and moves on.
- scenes/world.py:482
  old: A {creature} stirs nearby, but the animals have spoken for you and it passes by.
  new: A {creature} comes close, takes you for a friend, and wanders off.
- scenes/world.py:1879
  old: There's no enchanter here. You'll need to find one - perhaps somewhere magic is welcome.
  new: There's no enchanter here. Look for one somewhere magic is welcome.
- scenes/world.py:2325
  old: Three things at a time: not done - {steps}. Say it again when you are ready.
  new: Three things at a time. Left undone: {steps}. Say them again when you're ready.
- scenes/world.py:3005
  old: You are not anywhere you know the way from.
  new: You don't know your way anywhere from here.
- scenes/world.py:3357-3358
  old: ...The nearest is {name} in {town}{away}. Say where you want to go to head there.
  new: ...The nearest is {name} in {town}{away}. Name it if you want to head there.
  ("There is no {type} in {town}" kept: town_person_test.py:50 checks its absence.)
- scenes/world.py:3916
  old: You ready {ability} - it goes up the moment you strike.
  new: You ready {ability}. It takes effect the moment you strike.
- scenes/world.py:3924
  old: {ability} is a fighting technique - save it for a fight
  new: {ability} is a fighting technique, so save it for a fight
  (keeps "fighting technique" and "save it for a fight", both pinned.)
- scenes/world.py:4165
  old: Attacking people isn't supported yet.
  new: You can't pick a fight with the people here.

Kept as is: 98 lines (107 literal calls; plain functional notes, commands, prices, rest notes, way-closed notes, listings).
Debug-only output sent through console.note (left unchanged, for the lead): world.py:729-733 (#pulse pane: "PULSE - now ..."
and rows), 737-750 (#world: "WORLD - {season}...", threads, motive, effect, history, news), 724 and 2727 (the "#pulse/#world is a
debug ..." notes), 2783 ("[debug] Now level"), and the developer commands #events (2634), #check (2639), #audit (2721), #refusals
(2724). None reach a player outside --debug or dev commands except #events/#check, which are developer tools.
Not changed because code matches it: 2619 "Remembered here: {mark}" (tools/page_measures.py:173 counts lines starting with it,
hygiene_test.py:47, page_measures_test.py:45), although "Remembered" breaks voice rule 2; a rename needs those changed together.

## scenes/road_actions.py

- scenes/road_actions.py:712
  old: Your help is remembered, and repaid.
  new: You're paid for your trouble, and word of your help gets around.
- scenes/road_actions.py:739-740
  old: You search the camp. Stolen coin: {coins}. And {item}. / ...There is {item} too, but your pack is full.
  new: You search the camp. Stolen coin: {coins}. You also take {item}. / ...There's {item} too, but your pack is full.

Kept as is: 9 lines. Not changed: 417 "You stop here, on the road. Onward to {onward}, or back to {back}." (plain; matched by
simbot.py:47 and night_crashes_492_test.py), 375 ledger "On the road - {title}" (dash, but matched by simbot.py:45 startswith and
page_measures_test.py:90; changing it needs those together).

## scenes/exit_actions.py

- scenes/exit_actions.py:169
  old: You turn back and walk the road home.
  new: You turn back and walk the way you came.

Kept as is: 5 lines (plus the two fork questions, plain).

## scenes/mount_actions.py

Kept as is: 14 lines. (The stable listing at 26-27 uses " - " as a list separator, like the places and enchant listings in
world.py 1890, 1911, 3009-3013, 3048; left as UI listings, not story text.)

## scenes/camp_actions.py

- scenes/camp_actions.py:229
  old: You have not been seen. You could: {opts} - or describe your own way, or go elsewhere.
  new: You haven't been seen. You could: {opts}. Or try it your own way, or go elsewhere.
- scenes/camp_actions.py:362
  old: Someone out there is watching the treeline now. The camp is wary.
  new: Someone in the camp caught a glimpse of movement. The camp is wary now.
  (no treeline in a desert or a ruin)
- scenes/camp_actions.py:382
  old: You spot {flaw} - it will help you get close.
  new: You spot {flaw}. That will help you get close.
- scenes/camp_actions.py:404
  old: No guards are left - only the leader. You could ambush them, or charge in.
  new: There are no guards left, only the leader. You could ambush the leader, or charge in.
- scenes/camp_actions.py:419
  old: {who} is dealt with. +{xp} XP - LEVEL UP! You are now level {n}.
  new: {who} is dealt with. +{xp} XP. LEVEL UP! You are now level {n}.
  ("LEVEL UP!" kept: replay scripts match it.)
- scenes/camp_actions.py:434
  old: Someone has noticed men are missing. The camp is on edge.
  new: Someone has noticed guards are missing. The camp is on edge.
- scenes/camp_actions.py:457
  old: You catch them off guard - you will have the first moment.
  new: You catch them all off guard. The first move is yours.
- scenes/camp_actions.py:458
  old: You catch the leader off guard - you will have the first moment against them.
  new: You catch the leader off guard, and the first blow is yours.
- scenes/camp_actions.py:512
  old: {names} run(s) off into the dark.
  new: {names} run(s) off.
  (it can be day)

Kept as is: 9 lines.

## Tests that pin old wording

- tools/sim/plan_limit_test.py:53: "not done - search the square for tracks" (world.py:2325). New text gives
  "Left undone: search the square for tracks".
- data/replay/sessions/stub_short/turns.jsonl:35-36: shown_text "Your help is remembered, and repaid." (road_actions.py:712):
  golden needs a re-bless.
- ui/gui/web/app.js:509 (not a test, not my file): the window's places pane has its own copy of "You are not anywhere you know the
  way from."; change it to "You don't know your way anywhere from here." to match world.py:3005.
- tools/sim/road_stops_427_test.py:4 quotes "remembered, and repaid." in its docstring only (no check).
- tools/sim/ability_hunt_685_test.py:3 quotes the old "fighting technique - save it" in its docstring only; field_test.py:225 and
  surprise_test.py:114 still match.


# tierC2_review: field_actions, dungeon_actions, passive_hooks, spell_actions

## scenes/field_actions.py

- scenes/field_actions.py:48 (and :58, the same refusal twice)
  old: There's no one here to work on - say who you mean.
  new: There's no one here to work on. Say who you mean.
- scenes/field_actions.py:52
  old: {ability.name} is used in a fight, on a creature you face - wound one first, or hit it with all you have.
  new: {ability.name} is used in a fight, on a creature you face. Wound one first, or hit it with all you have.
- scenes/field_actions.py:56
  old: There is no need to make camp here - this place already has shelter.
  new: There's no need to make camp here. This place already has shelter.
- scenes/field_actions.py:86
  old: Nothing is left below to look for - it is cleared to the bottom.
  new: There's nothing left below to look for. The place is cleared to the bottom.
- scenes/field_actions.py:103
  old: You read the signs: things that live here - {names}.
  new: You read the signs. Things that live here: {names}.
- scenes/field_actions.py:120 (describe_chamber; shown after "You scout ahead:", also passed to the narrator as the fact)
  old: the next chamber is trapped - you see the trigger and will step around it.
  new: the next chamber is trapped, but you see the trigger and will step around it.
- scenes/field_actions.py:121
  old: a cache lies hidden in the next chamber - and it is locked.
  new: a cache lies hidden in the next chamber, and it's locked.
- scenes/field_actions.py:122
  old: the next chamber is quiet and empty - a safe place to rest.
  new: the next chamber is quiet and empty, a safe place to rest.
- scenes/field_actions.py:138
  old: You make camp. You can rest here undisturbed - sleep and you will wake fully restored.
  new: You make camp. You can rest here undisturbed, and if you sleep you'll wake fully restored.
- scenes/field_actions.py:205
  old: You fade into the dark. The next creature you meet in here can be slipped past.
  new: You fade into the dark. You can slip past the next creature you meet in here.
- scenes/field_actions.py:227
  old: For the next hour {who} move as one shadow: every attempt to go unseen is much easier, and it holds after the first.
  new: For the next hour {who} move quietly together, and stay much harder to spot.
- scenes/field_actions.py:248
  old: You search what you know, but there is nothing more to recall about this place.
  new: You search your memory, but there's nothing more you know about this place.
- scenes/field_actions.py:287
  old: It is pitch black down here and you carry no light. You'll be feeling your way - spotting traps and finding things is harder (-{n}). A torch from a chandler fixes that.
  new: It's pitch black down here and you carry no light. You'll be feeling your way, so spotting traps and finding things is harder (-{n}). A torch from a chandler fixes that.
- scenes/field_actions.py:324
  old: There are no traps to feel out here - save it for a dungeon.
  new: There are no traps to feel out here. Save it for a dungeon.
- scenes/field_actions.py:328
  old: It is cleared to the bottom - nothing is left to find.
  new: It's cleared to the bottom, with no traps left to find.
- scenes/field_actions.py:351
  old: Nothing that lives here answers to you - no beasts, only worse.
  new: Nothing here will answer you. Whatever lives here isn't an animal.
- scenes/field_actions.py:421
  old: {Name}: mood {mood}; what weighs on them - {weighs}; {trust}.
  new: {Name} {trust}, and their mood is {mood}. What weighs on them: {weighs}.
  (e.g. "The farmer is neutral toward you, and their mood is even. What weighs on them: nothing you can make out.")
- scenes/field_actions.py:512-517 (speak with the dead; a small restructure, see note)
  old: The dead answer: it was {who}, of about level {n}; it fell {dur} ago, to the player's own hand; it carried {x}.
  new: The dead answer. It was {who}, about level {n}. It fell {dur} ago, by your hand. It carried {x}.
  Note: the old note printed the narrator's fact list, so the player read "to the player's own hand". The facts list sent to the
  narrator is unchanged; the note is now built from its own list of sentences (same conditions, same facts), with a one-line (f712) comment.
- scenes/field_actions.py:558
  old: There is nothing to tend - you are whole and your companions are on their feet.
  new: There's nothing to tend. You're whole, and your companions are on their feet.
- scenes/field_actions.py:623
  old: You work the lock on the cache in {where} - it holds more than a plain one.
  new: You work open the lock on the cache in {where}.
- scenes/field_actions.py:660 (size up: the "what" shown in the note and given to the narrator)
  old: {count} {creature}s ahead - {word}
  new: {count} {creature}s ahead, {word}
- scenes/field_actions.py:673
  old: You size up {what}. You have found the weak point; the next fight here will go easier.
  new: You size up {what}. You've found the weak point, and the next fight here will go easier.
- scenes/field_actions.py:704 (returned to the fight's opening notes)
  old: You strike where you judged it weakest - its defenses are thinner.
  new: You strike where you judged it weakest.
- scenes/field_actions.py:709
  old: Your snare catches them - they come at you already hurt.
  new: Your snares catch them, and they come at you already hurt.
- scenes/field_actions.py:751
  old: You have nothing that can be reforged - a piece of weapon or armor with at least two rolls, not yet reforged, and not legendary.
  new: You have nothing that can be reforged. That takes a weapon or armor with at least two rolls, never reforged before, and not legendary.
- scenes/field_actions.py:757
  old: {item} - its rolls:
  new: The rolls on {item}:
- scenes/field_actions.py:841
  old: Nothing in your pack can be broken down - only unequipped weapons and armor, and nothing legendary.
  new: Nothing in your pack can be broken down. It has to be a weapon or armor you aren't wearing, and not legendary.
- scenes/field_actions.py:887 (returned to the fight's opening notes)
  old: Your Soul Tether holds: a companion that would fall will stand once more.
  new: Your Soul Tether binds your companions. If one of them falls, they'll get back up once.
- scenes/field_actions.py:905
  old: There is no town you have left that you could return to yet.
  new: There's no town behind you to return to yet.

## scenes/dungeon_actions.py

- scenes/dungeon_actions.py:35
  old: {Name} has shifted and been remade - your progress there is lost.
  new: {Name} has shifted and been remade. Your progress there is gone.
- scenes/dungeon_actions.py:76 (#dungeon text view)
  old: {NAME} - a {theme} beneath {place}. Remade in {days} days.
  new: {NAME}: a {theme} beneath {place}. Remade in {days} days.
- scenes/dungeon_actions.py:82
  old:   floor {n} [{letter}] - {done}/{total} chambers cleared{boss}
  new:   floor {n} [{letter}]: {done}/{total} chambers cleared{boss}
- scenes/dungeon_actions.py:129
  old: {label} - the master of this place waits here.
  new: {label}. The master of this place waits here.
- scenes/dungeon_actions.py:251
  old: You climb back out of {name}. Your progress is kept until it is remade.
  new: You climb back out of {name}. You'll pick up where you left off, unless the place is remade first.

## scenes/passive_hooks.py

- scenes/passive_hooks.py:385
  old: Your songs are all old ones tonight - the realm is quiet.
  new: There's no news worth singing about tonight, so you stick to the old songs.
- scenes/passive_hooks.py:415
  old: Everyone eats - {who} think(s) a little better of you for it (Campfire Cook).
  new: Everyone eats, and {who} think(s) a little better of you for it (Campfire Cook).
- scenes/passive_hooks.py:450
  old: ... You could make its like now - {rarity} work at the least (Reverse Engineer).
  new: ... You could make its like now, {rarity} work at the least (Reverse Engineer).

## scenes/spell_actions.py

- scenes/spell_actions.py:87
  old: Learned {new}: {card}, {mana} mana. It takes the place of {old} among the spells you bring; {old} stays in your book.
  new: Learned {new}: {card}, {mana} mana. It replaces {old} among the spells you bring. {old} stays in your book.
- scenes/spell_actions.py:109
  old: The {book} teaches rank {R}; none of your spells is at rank {R-1} to take it ({below} must grow first).
  new: The {book} teaches rank {R}, and none of your spells is at rank {R-1} yet ({below} must grow first).
- scenes/spell_actions.py:147 (a teacher's list row)
  old:   {i}. {spell} to rank {R} ({form}) - {fee}, {hours} hours
  new:   {i}. {spell} to rank {R} ({form}): {fee}, {hours} hours

## Kept as is

- scenes/field_actions.py: 58 lines (cooldown reason, pickpocket/audience/show refusals, scout/recall/haste/influence/shadow notes,
  torch, trap disarmed, beastspeak, swift step, barter, intimidate, pickpocket, commune, tinker, treat, bless, servant, picklock none,
  size-up/snare refusals, revivify, reforge prompts and answers, salvage, soul tether, word of recall, phantom steed)
- scenes/dungeon_actions.py: 12 lines
- scenes/passive_hooks.py: 8 lines
- scenes/spell_actions.py: 11 lines
- Not touched (model instructions): every narrate(...) and returned "They ..." / "Describe ..." string, NAME_SYSTEM, NAMED_SYSTEM,
  the speak-corpse facts list, pulse.add_news text, ask_next question data keys.

## Tests that pin old wording

None break. Four tests pin fragments that were deliberately kept:
- tools/sim/field_test.py:164 "no need" (camp refusal, so "There's no need..." keeps it, case-sensitive)
- tools/sim/field_test.py:97 "pitch black"; tools/sim/field_test.py:124 "trapped"; tools/sim/field_test.py:221 "already had your act"
- tools/sim/field_functions_test.py:219 "mood" lowercase in the read-the-room note; :273 "nothing to tend"
- tools/sim/taught_test.py:180 "used in a fight" (Bind a Beast refusal)
- tools/sim/forge_test.py:75 "nothing that can be reforged"
Run and passing: field_test, field_functions_test, taught_test, forge_test, spells_test, perks_world_test, perks_round2_test,
perk_test, perks_combat_test, arc_body_test, composed_508_test, tables_504_test, battlefield_test, big_field_test, hire_spells_test.
Goldens (data/replay/sessions) that show any of these notes were not checked; the lead's rebless pass covers them.


# tierC3 review: inventory, shop, property (home), training notes

(There is no scenes/home_actions.py. The home actions are in scenes/property_actions.py.)

## scenes/inventory_actions.py

- scenes/inventory_actions.py:52
  old: No room in your pack - {inv.label(leftover)} left on the ground here.
  new: No room in your pack, so you leave {inv.label(leftover)} on the ground here.
- scenes/inventory_actions.py:109
  old: {cap_first(key.name)} is a {quest/key} item - you can't {what} it.
  new: {cap_first(key.name)} is a {quest/key} item. You can't {what} it.
- scenes/inventory_actions.py:135
  old: {Quest/Key} item received: {key.name}{meant} - {key.description}
  new: {Quest/Key} item received: {key.name}{meant}. {key.description}
  (descriptions are written as capitalised sentences: guild badge, law keys, quest items)
- scenes/inventory_actions.py:210
  old: It is no longer with you.
  new: You don't have it anymore.
- scenes/inventory_actions.py:213 (journal line, item_history: "Got rid of {name}{unfinished} (day N).")
  old: " - it never reached {key.for_whom}"
  new: ", which never reached {key.for_whom}"
- scenes/inventory_actions.py:300
  old: Is the {g.name} for you or for someone else? Say that you take it yourself, or give it to the one you mean.
  new: Is the {g.name} for you or for someone else? Say you'll take it yourself, or give it to whoever it's for.
- scenes/inventory_actions.py:386
  old: Any coin worth taking is already in your purse ({money.fmt(...)}); none lies here.
  new: There's no coin lying here. Any worth taking is already in your purse ({money.fmt(...)}).
- scenes/inventory_actions.py:505 (refusal reason returned by fee_asked, shown by refuse)
  old: {What} is {price}; that is short of it, and you keep your coin.
  new: {What} is {price}. That's not enough, so you keep your coin.
- scenes/inventory_actions.py:507 (same)
  old: {npc} takes coin for {what} ({price}), not as a gift. Say it is for that, or say it is a gift; you keep your coin for now.
  new: {npc} takes coin for {what} ({price}), not as a gift. Say it's for that, or say it's a gift. Until then, you keep your coin.
- scenes/inventory_actions.py:661 (feeds the ledger "Handed over: {name}{meant}." and the journal "Gave {name} to {npc}{meant} (day N).")
  old: " - it was meant for {key.for_whom}"
  new: ", though it was meant for {key.for_whom}"
- scenes/inventory_actions.py:765
  old: The item box is full - kept {inv.label(leftover)}.
  new: The item box is full, so you keep {inv.label(leftover)} in your pack.
- scenes/inventory_actions.py:906
  old: Making {base} needs a {station} - there's one at {where}.
  new: Making {base} needs a {station}. There's one at {where}.
- scenes/inventory_actions.py:942
  old: No workshop needed - you have made this before (Practiced Hands).
  new: No workshop needed, since you've made this before (Practiced Hands).
- scenes/inventory_actions.py:945
  old: Crafting skill {before:.0f} -> {after:.0f}.
  new: Crafting skill: {before:.0f}, now {after:.0f}.
- scenes/inventory_actions.py:990
  old: . Ready in about a day - collect it while they're at work.
  new: . It'll be ready in about a day. Come by for it during their working hours.
- scenes/inventory_actions.py:1057-1058 (shop list rows, text console only)
  old: "  {name} ({detail} - {note}) - {price}"
  new: "  {name} ({detail}; {note}): {price}"
- scenes/inventory_actions.py:1064 (shop list rows)
  old: "  {name} - {total} (from {buyer})"
  new: "  {name}: {total} (from {buyer})"

Kept as is: 62 lines (refusals such as "You aren't carrying that.", "How much? Say an amount.", "You only have {..}.",
"There's no item box here.", ledgers "Gave/Stored/Took from the item box/Gathered/Made/Crafted/Commissioned/Delivered/Discarded",
"Kept.", "Left here: ... Items left behind vanish after N days.", the shop's "Nothing is sold here..." and "No one you have spoken
to sells here yet..." (pinned by two tests and already plain), the Symbiosis note, and the rest). Not touched as model-facing:
consume()'s effect string, the bribe effect lines, ledger.add say=, narrate(...) prompts.

## scenes/shop_actions.py

- scenes/shop_actions.py:67-68
  old: The room is yours tonight, free - you're well thought of here. / ... free - paid for with a song.
  new: The room is yours tonight, free. You're well thought of here. / ... free. Your song paid for it.
- scenes/shop_actions.py:91 (ROOM_SINGLY)
  old: A room is let one at a time, for the one night. Ask for a room.
  new: Rooms go one at a time, for one night. Ask for a room.
- scenes/shop_actions.py:150
  old: No more than {self.MOST_AT_ONCE} of a thing are sold at once.
  new: No one sells more than {self.MOST_AT_ONCE} of a thing at once.

Kept as is: 13 lines (SINGLY, "has only ... to sell", "... come to ..., and you have ...", "You can't afford ...", "You already have
a room here ...", the Paid/Bought/Sold ledgers, "A room upstairs is yours ...", "That is no longer on offer.").

## scenes/property_actions.py (the home actions)

- scenes/property_actions.py:47
  old: You own {name} in {town} - upgrades: {ids}.
  new: You own {name} in {town}. Upgrades: {ids}.
- scenes/property_actions.py:51-52
  old: For sale here: {name} - {price}. A land agent handles it; say 'buy a house'.
  new: For sale here: {name}, for {price}. The land agent handles the sale. Say 'buy a house'.
- scenes/property_actions.py:134-135
  old: You buy {h}: {price}. It is called 'your house in {town}' now; you can sleep there free, and keep your item box in it. Type #home.
  new: You buy {h} for {price}. It's 'your house in {town}' now. You can sleep there for free and keep your item box there. Type #home.

Kept as is: 19 lines (upgrade rows, "Say 'buy a garden' ...", purse, rebuild notes and refusal, upgrade prices and refusals, "No
houses are for sale here ...", "The land agent isn't here right now.", "From the garden: ...", "A hot meal at your own hearth
restores you.").

## scenes/training_actions.py

- scenes/training_actions.py:80
  old:   drills - {fee}, {hours} hours, once a day
  new:   drills: {fee}, {hours} hours, once a day
- scenes/training_actions.py:81
  old:   tutoring in {skills} - from {fee}, ...
  new:   tutoring in {skills}: from {fee}, ...
- scenes/training_actions.py:83-85
  old:   a new ability or passive trait - {fee}, {hours} hours (you know {n} of {m} abilities you can hold, {p} of {q} traits)
  new:   a new ability or passive trait: {fee}, {hours} hours (you hold {n} of {m} abilities and {p} of {q} traits)
- scenes/training_actions.py:91
  old: The instructor has nothing left to teach you in drills - the world is your teacher now.
  new: You've learned everything the instructor's drills can teach.
- scenes/training_actions.py:106
  old: LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate
  new: LEVEL UP! You are now level {c.level}, with {c.unspent_points} points to spend. Type #allocate.
- scenes/training_actions.py:144
  old: You can't take on another ability or trait yet - you'll have room for one more at level {nxt}.
  new: You can't take on another ability or trait yet. You'll have room for one more at level {nxt}.

Kept as is: 14 lines (fee refusal, "Training is with the guild's instructor ...", "The instructor teaches:", "You've drilled today
already ...", "Drilled for ...", "Studied ...", the wait line, "can't settle on what to teach you ...", "Learning one costs ...",
"Which one? Say its number or name.", "Learned {name}{uses}. Paid {fee}.", and the rest).

## Tests that pin old wording:

None of the changed strings are pinned. Checked and still passing by text:
- tools/sim/used_on_645_test.py:85,131 ("for you or for someone else": kept in the new line)
- tools/sim/golden_replay_test.py:67 ("LEVEL UP!": kept)
- tools/sim/walk_on_matter_662_test.py:36 calls ws.refuse("Any coin worth taking ...") itself; it pins nothing in this file.
- tools/sim/panels_test.py:188 and tools/sim/shop_view_test.py:25 pin "No one you have spoken to sells here yet ... Speak to them
  first": that line was left as is.
Goldens: data/replay/sessions/stub_fight/turns.jsonl holds "points to spend - #allocate", from combat_scene.py, not training.

## Notes for the lead
- The LEVEL UP line is the same string in arc_actions.py:605,686, combat_scene.py:1139, guild_actions.py:650 (not mine). Align
  those to the training wording if wanted.
- shop_actions.py:207,223: in a pane purchase of a meal or drink, console.note(effect) prints "They eat and feel restored." / "They
  drink." in the third person. The same string goes to the narrator prompt, so I left it; a separate player line would need code.
- property_actions.py:47 shows upgrade ids ("banquet_hall") rather than names; that is the expression, not the text, so left.


# tierC4_review: party, arc, guild, law, standing (Tier C notes)

## scenes/standing_actions.py

- scenes/standing_actions.py:75
  old: console.note("Nobody out here keeps a tally of you.")
  new: console.note("There's no one out here to have an opinion of you.")
- scenes/standing_actions.py:92
  old: console.note(f"What is being said about you in {self.world.places[town].name}:")
  new: console.note(f"What people are saying about you in {self.world.places[town].name}:")
- scenes/standing_actions.py:126
  old: console.note("Those who tell it have it right. There is nothing to correct.")
  new: console.note("People already have that one right. There's nothing to set straight.")
- scenes/standing_actions.py:131
  old: console.note("You set the record straight. The tale is told true from now on.")
  new: console.note("You set the record straight, and people believe you.")
- scenes/standing_actions.py:133
  old: console.note("You argue your case, but the tale has a life of its own. Nobody is convinced.")
  new: console.note("You argue your case. Nobody is convinced.")

## scenes/party_actions.py

- scenes/party_actions.py:72
  old: console.note("The clerk has heard where your trail leads: a fortified camp. The guild keeps adventurers who will go with you " "for a fee - say 'recruit help' to see who is free.")
  new: console.note("The clerk knows where your trail leads: a fortified camp. The guild has adventurers who'll go with you " "for a fee. Say 'recruit help' to see who's free.")
- scenes/party_actions.py:157
  old: console.note(f"{n.name} joins your party. She comes for her own reasons, and she is not paid. If she is hurt badly enough, she may not get up.")
  new: console.note(f"{n.name} joins your party. She's coming for her own reasons, not for pay. If she's hurt badly enough, she may not get up again.")
- scenes/party_actions.py:212
  old: state = "Dead - only a revival brings it back"
  new: state = "Dead. Only a revival will bring it back"
- scenes/party_actions.py:215
  old: state = "Fallen - back on its feet in " + clock.describe_duration(wait) if wait else "Fallen - ready to rise"
  new: state = "Fallen, back on its feet in " + clock.describe_duration(wait) if wait else "Fallen, but ready to get up"
- scenes/party_actions.py:860
  old: console.note("No one in your party by that name. Say whom to send away, or the whole party.")
  new: console.note("There's no one in your party by that name. Say who to send away, or send the whole party.")
- scenes/party_actions.py:906
  old: console.note("Your party will hold back and come running if the alarm goes up. They make no noise for you to answer for.")
  new: console.note("Your party will hold back and come running if the alarm goes up. On your own, you make less noise.")
- scenes/party_actions.py:916
  old: console.note("Your party moves beside you. Together you are loud.")
  new: console.note("Your party moves up beside you. As a group, you're a lot louder.")
- scenes/party_actions.py:1017
  old: console.note(f"{first} looks you over: there is nothing that needs tending.")
  new: console.note(f"{first} looks you over. Nothing needs tending.")
- scenes/party_actions.py:1020
  old: console.note(f"{first} has done what can be done for now; the rest wants rest and time.")
  new: console.note(f"{first} can't do more for now. What's left will take rest and time.")

## scenes/arc_actions.py

- scenes/arc_actions.py:63
  old: console.note(f"{names[:1].upper() + names[1:]} {'has' if one else 'have'} given up the fight and {'waits' if one else 'wait'} on you. "
  new: console.note(f"{names[:1].upper() + names[1:]} {'has' if one else 'have'} given up the fight and {'waits' if one else 'wait'} for you to decide. "
- scenes/arc_actions.py:109
  old: console.note(f"The fallen can be {loot.remains_words([e for e in foes if loot.has_remains(e)])} - say so if you want to.")   # (f672)
  new: console.note(f"The fallen can be {loot.remains_words([e for e in foes if loot.has_remains(e)])}. Say so if you want to.")   # (f672)
- scenes/arc_actions.py:299
  old: console.note("A body lies here, and it has something to tell - if only you could make it speak.")
  new: console.note("A body lies here. It could tell you something, if you had a way to make the dead speak.")
- scenes/arc_actions.py:345
  old: console.note(f"{skill.capitalize()} - {degree}: you find what the place was hiding.")
  new: console.note(f"{skill.capitalize()}: {degree}. You find what the place was hiding.")
- scenes/arc_actions.py:350
  old: console.note(f"You search {place} for hours and the place keeps its secret. You find the thread another way, at a cost of time.")
  new: console.note(f"You search {place} for hours and find nothing. In the end you pick up the trail another way, but it takes longer.")
- scenes/arc_actions.py:354
  old: console.note(f"{skill.capitalize()} - {degree}: nothing yet. You keep looking.")
  new: console.note(f"{skill.capitalize()}: {degree}. Nothing yet. You keep looking.")
- scenes/arc_actions.py:368
  old: console.note(f"You lay out what you know, but {who} does not break. It comes to blades. ({skill.capitalize()} - {degree})")
  new: console.note(f"You lay out what you know, but {who} won't give in. It comes to a fight. ({skill.capitalize()}: {degree})")
- scenes/arc_actions.py:372
  old: console.note(f"{skill.capitalize()} - {degree}: your proof is too strong. {who} gives way.")
  new: console.note(f"{skill.capitalize()}: {degree}. Faced with your proof, {who} gives way.")
- scenes/arc_actions.py:404
  old: console.note(f"{sn.get('npc_name') or info['leader']} will not be answering questions. On the body, and among what " "the camp leaves behind, you find what you came for.")
  new: console.note(f"{sn.get('npc_name') or info['leader']} won't be answering any questions. On the body and among what's left " "of the camp, you find what you came for.")
- scenes/arc_actions.py:570
  old: console.note("You learn of a hidden way near here. (A lead - try exploring.)")
  new: console.note("You learn of a hidden way near here. (A lead: try exploring.)")
- scenes/arc_actions.py:583
  old: console.note(f"{cap_first(npc.label(self.acting))} will say no more. You find the thread another way, at a cost of time.")
  new: console.note(f"{cap_first(npc.label(self.acting))} won't say any more. You find the trail another way, but it costs you time.")
- scenes/arc_actions.py:605
  old: console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
  new: console.note(f"LEVEL UP! You are now level {c.level}, with {c.unspent_points} points to spend. Type #allocate.")
- scenes/arc_actions.py:616
  old: console.note(f"This is bigger than it looked. The trail now has a name: {s['title']} - {total} steps to its end.")
  new: console.note(f"This is bigger than it looked. Now you know what it is: {s['title']}. {total} steps to the end.")
- scenes/arc_actions.py:684
  old: f"+{money.fmt(coins)}, +{xp} XP - hand in the contract at the guild.")
  new: f"+{money.fmt(coins)}, +{xp} XP. Hand in the contract at the guild.")
- scenes/arc_actions.py:686
  old: console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
  new: console.note(f"LEVEL UP! You are now level {c.level}, with {c.unspent_points} points to spend. Type #allocate.")
- scenes/arc_actions.py:690
  old: console.note(f"{gift.description[:-1]} - it is yours now. It will fight at your side, though it is no bonded companion.")
  new: console.note(f"{gift.description[:-1]}. It's yours now, and it will fight at your side, though it isn't a bonded companion.")
- scenes/arc_actions.py:793
  old: self.refuse("There is no one from the watch here to hand them to. Find a guard or a watch captain.")
  new: self.refuse("There's no one from the watch here to take a prisoner. Find a guard or a watch captain.")
- scenes/arc_actions.py:807
  old: + (" - and it counts toward your bounty." if bounty else "."))
  new: + (". It counts toward your bounty." if bounty else "."))
- scenes/arc_actions.py:890
  old: console.note("No chain or arc is running.")
  new: console.note("You aren't following any trail right now.")
- scenes/arc_actions.py:893
  old: console.note(f"{s['title'] if arc['revealed'] else s['hook_title']} - {arcs.step_text(arc)}")
  new: console.note(f"{s['title'] if arc['revealed'] else s['hook_title']}: {arcs.step_text(arc)}")

## scenes/guild_actions.py

- scenes/guild_actions.py:160
  old: why = f"Rank {q['letter']} - you are rank {self.rank}."
  new: why = f"Needs rank {q['letter']}. You're rank {self.rank}."
- scenes/guild_actions.py:199
  old: why = "Your party is full." if full else ("Join the guild first." if not self.rank else "") or away or (f"Wants {money.fmt(m['fee'])}; your purse holds {money.fmt(c.coins)}." if c.coins < m["fee"] else "")
  new: why = "Your party is full." if full else ("Join the guild first." if not self.rank else "") or away or (f"Wants {money.fmt(m['fee'])}. You have {money.fmt(c.coins)}." if c.coins < m["fee"] else "")
- scenes/guild_actions.py:215
  old: console.note(f"THE CONTRACT BOARD at {data['hall']} - your rank: {self.rank or 'not a member (joining fee ' + money.words(G['joining_fee']) + ')'}")
  new: console.note(f"THE CONTRACT BOARD at {data['hall']}. Your rank: {self.rank or 'not a member (joining fee ' + money.words(G['joining_fee']) + ')'}")
- scenes/guild_actions.py:245
  old: console.note("They have moved on; the roster has changed.")
  new: console.note("That adventurer has moved on. The roster has changed.")
- scenes/guild_actions.py:337
  old: + (" - you qualify: ask for the trial at a guild hall." if self.trial_due() else "."))
  new: + (". You qualify: ask for the trial at a guild hall." if self.trial_due() else "."))
- scenes/guild_actions.py:351
  old: self.refuse(f"The joining fee is {money.words(G['joining_fee'])}; you have {money.words(c.coins)}.")
  new: self.refuse(f"The joining fee is {money.words(G['joining_fee'])}. You have {money.words(c.coins)}.")
- scenes/guild_actions.py:401
  old: self.refuse(f"Only guild members can take contracts. Joining costs {money.words(G['joining_fee'])} - " "ask the clerk.")
  new: self.refuse(f"Only guild members can take contracts. Joining costs {money.words(G['joining_fee'])}. " "Ask the clerk.")
- scenes/guild_actions.py:405
  old: self.refuse("Contracts are taken from the board, with the clerk to record them.")
  new: self.refuse("You take contracts from the board, and the clerk has to be here to record them.")
- scenes/guild_actions.py:414
  old: self.refuse(f"That's a rank-{q['letter']} contract; you're rank {self.rank}.")
  new: self.refuse(f"That's a rank-{q['letter']} contract, and you're rank {self.rank}.")
- scenes/guild_actions.py:420
  old: self.refuse("That posting is out of date - the place has been remade. The clerk strikes it from the board.")
  new: self.refuse("That posting is out of date: the place has been remade. The clerk strikes it from the board.")
- scenes/guild_actions.py:424
  old: self.refuse(f"You can hold {limit} guild contracts at once - finish or abandon one first.")
  new: self.refuse(f"You can only hold {limit} guild contracts at once. Finish or abandon one first.")
- scenes/guild_actions.py:502
  old: console.note(f"{cap_first(s['name'])} is dead." if s["boss"] else f"The {s['name']} that were troubling this place are broken.")
  new: console.note(f"{cap_first(s['name'])} is dead." if s["boss"] else f"That's the end of the {s['name']} that were troubling this place.")
- scenes/guild_actions.py:539
  old: console.note(f"{q['title']}: delivered" + (" - collect your pay from the guild clerk." if q["guild"] else "."))
  new: console.note(f"{q['title']}: delivered" + (". Collect your pay from the guild clerk." if q["guild"] else "."))
- scenes/guild_actions.py:635
  old: f"{money.fmt(coins)} - +{xp} XP.")
  new: f"{money.fmt(coins)}. +{xp} XP.")
- scenes/guild_actions.py:650
  old: console.note(f"LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate")
  new: console.note(f"LEVEL UP! You are now level {c.level}, with {c.unspent_points} points to spend. Type #allocate.")
- scenes/guild_actions.py:679
  old: console.note(f"Request offered: [{q['letter']}] {q['title']} - {money.words(q['coins'])}, {q['xp']} XP. "
  new: console.note(f"Request offered: [{q['letter']}] {q['title']}, for {money.words(q['coins'])} and {q['xp']} XP. "

## scenes/law_actions.py

- scenes/law_actions.py:141
  old: console.note("A bad failure: the fumble is loud, and the town's heat rises (All or Nothing).")
  new: console.note("You fumble it, badly and loudly. People will talk about this (All or Nothing).")
- scenes/law_actions.py:183
  old: console.ledger(f"Key item taken: {rec['name']} - {rec['description']}")
  new: console.ledger(f"Key item taken: {rec['name']}. {rec['description']}")
- scenes/law_actions.py:292
  old: changed = " Their key no longer fits - the lock has been changed." if self.has_key(lock) else ""
  new: changed = " The key no longer fits. Someone has changed the lock." if self.has_key(lock) else ""
- scenes/law_actions.py:507
  old: menu = (f"You are under arrest - but your kind are not jailed. Pay the fine ({money.fmt(fine)}); what your purse cannot cover, " f"your name will. Or offer a bribe, or run.")
  new: menu = (f"You're under arrest, but your kind don't go to jail. Pay the fine ({money.fmt(fine)}), and what your purse can't cover " f"comes out of your good name here. Or offer a bribe, or run.")
- scenes/law_actions.py:538
  old: console.note("The guard is not swayed - he wants the fine.")
  new: console.note("The guard isn't swayed and still wants the fine.")
- scenes/law_actions.py:541
  old: console.note("The guard is not swayed. You are arrested.")
  new: console.note("The guard won't hear it. You're under arrest.")
- scenes/law_actions.py:573
  old: console.note("The guard refuses. You are arrested.")
  new: console.note("The guard refuses the bribe. You're under arrest.")
- scenes/law_actions.py:601
  old: console.note(f"No cell for you. You pay {money.fmt(paid)}" + (f"; the rest ({money.fmt(owed)}) is paid in standing here ({-lost})" if owed else "")
  new: console.note(f"No cell for you. You pay {money.fmt(paid)}" + (f". The rest ({money.fmt(owed)}) comes out of your standing here ({-lost})" if owed else "")

## Kept as is

- scenes/standing_actions.py: 10 lines
- scenes/party_actions.py: 37 lines
- scenes/arc_actions.py: 19 lines
- scenes/guild_actions.py: 35 lines
- scenes/law_actions.py: 15 lines

Left on purpose: list separators in tables ("Name - role, rank" in party/board listings, "[X] title - reward" on the
board), because they are table layout, not story text; arc_lines' " - " must stay (guild_actions.quest_rows splits on it).
Model-facing text left alone: narrate([THE GAME HAS DECIDED...]), ledger.add(say=...), the theft 'nothing' reasons fed to the
narrator, pulse.add_news rumor lines, verdict/how strings stored in the registry, Maren's mentor_say lines.

## Tests that pin old wording

- tools/sim/arc_site_test.py:112 "comes to blades" (now "It comes to a fight.", arc_actions.py:368). Fails until updated.

Checked and still passing with the new text: standing_test.py:154 "Nobody is convinced" (kept), hire_kit_test.py:160
"rest and time" (kept), arc_site_test.py:105 "gives way" (kept), law_test.py:203 "under arrest", playthrough3b_test.py:178
"Spare it, or finish it?", party_pane_test.py:63 "Fallen", locks_test.py:126 "no longer fits", clerk_test.py:73
"Completed: [F] Hunt 3 wolves", board_click_test.py:112 "CONTRACT BOARD"; tools/page_measures.py CLOSED_AS "Completed:" /
"Abandoned:" prefixes unchanged. Goldens (data/replay/sessions) that show these notes will need re-blessing.


# tierC5_review: Tier C notes in combat_scene, goddess, main, trial_actions, events, engine refusals, small scenes files

Small scenes/ files claimed (1 to 5 notes each, not owned by others): banter_actions, work_actions, audit_actions,
explore_actions, check_actions, pastime_actions, stats_actions. (gear_actions, part_actions, quirk_actions have 6 and were
left alone; mentor_actions and orenna_actions are Tier B.)

## scenes/combat_scene.py
- scenes/combat_scene.py:289 (shown in the fight pane, a sworn foe read)
  old: "slow - it cannot follow a quick step" / "fast - it will run you down"
  new: "slow: it can't keep up with a quick step" / "fast: it will run you down"
- scenes/combat_scene.py:646
  old: ... Use it once the fight is over; for now, pick one of your fighting abilities from the panel.
  new: ... Use it once the fight is over. For now, pick one of your fighting abilities from the panel.
- scenes/combat_scene.py:941
  old: No potions or draughts in a trial: you face the examiner with what you carry in your hands.
  new: No potions or draughts in a trial. You face the examiner with what's in your hands.
- scenes/combat_scene.py:947
  old: You have already used an item this turn. Do something else, and you can use another on your next turn.
  new: You've already used an item this turn. Do something else now, and use another next turn.
- scenes/combat_scene.py:1066
  old: The killing blow lands - and {item} burns white. You rise from the ashes at half strength; the fight is over. (It cannot do this again for {wait:g} days.)
  new: The killing blow lands, and {item} burns white. You rise from the ashes at half strength, and the fight is over. (It can't do this again for {wait:g} days.)
- scenes/combat_scene.py:1104
  old: They got away - nothing to show for it this time.
  new: They got away. You've nothing to show for this one.
- scenes/combat_scene.py:1139
  old: LEVEL UP! You are now level {c.level}. {c.unspent_points} points to spend - #allocate
  new: LEVEL UP! You are now level {c.level}, with {c.unspent_points} points to spend. Type #allocate.
  (matches the wording training_actions.py:106 already has; arc_actions 605/686 and guild_actions 650 still carry the old form, owned by others)
- scenes/combat_scene.py:1143
  old: The fallen can be {remains} - say so if you want to.
  new: The fallen can be {remains}. Say so if you want to.

## scenes/goddess.py
- scenes/goddess.py:103 and :143
  old: You leave the Threshold. No character was saved - run main.py to begin again.
  new: You leave the Threshold. No character was saved. Start the game again to begin.
- scenes/goddess.py:121 (fallback only when failures.yaml has no creation_fail line)
  old: The model couldn't make sense of that. Try saying it another way.
  new: She doesn't follow. Try saying it another way.
- scenes/goddess.py:139
  old: ... (build, age, hair, anything else) - or press Enter to be surprised.
  new: ... (build, age, hair, anything else). Or press Enter to be surprised.
- scenes/goddess.py:456 (fallback)
  old: The model couldn't read that concept this time. Nothing is lost - describe it again.
  new: She can't yet see who you mean to be. Describe it again.
- scenes/goddess.py:483 (fallback)
  old: The model couldn't shape your gifts this time. Nothing is lost - say yes again to retry.
  new: Your gifts haven't taken shape. Say yes again to try once more.
- scenes/goddess.py:517 (fallback)
  old: The model couldn't shape your innate traits this time. Nothing is lost - choose your three techniques again to retry.
  new: Your traits haven't taken shape. Choose your three techniques again to try once more.

## main.py
- main.py:122-123
  old: It was installed already and the game still reports {v}: the installer on the release was most likely built before its version number was raised. Installing it again will change nothing.
  new: You've installed it already, but the game still says {v}. The installer for that release was probably built before its version number went up, so installing it again won't change anything.
- main.py:191
  old: The model couldn't produce a usable answer and the game can't continue from this point.
  new: Something went wrong behind the scenes, and the game has to stop here.
- main.py:192
  old: If you were already playing, what the world had settled before it stopped is saved, and is told when you come back.
  new: If you were already playing, your game is saved up to where it stopped. You'll pick up from there next time.
- main.py:193
  old: If you were still creating your character, nothing was saved - run main.py to start creation again.
  new: If you were still making your character, nothing was saved. Start the game again to make one.
- main.py:194
  old: (details: {e} - see logs/llm_calls.jsonl and logs/crash.log)
  new: (For a bug report, see logs/llm_calls.jsonl and logs/crash.log: {e})
- main.py:198
  old: Interrupted. What the world had settled before it stopped is saved, and is told when you come back.
  new: Interrupted. Your game is saved up to where it stopped.
- main.py:208
  old: Something went wrong and the game has to stop. What the world had settled before it stopped is saved, and is told when you come back.
  new: Something went wrong and the game has to stop. Your game is saved up to where it stopped.

## scenes/trial_actions.py
- scenes/trial_actions.py:141
  old: You lose the trial. You keep rank {rank}. You may stand again in {d}.
  new: You lose the trial. You keep rank {rank}, and you can try again in {d}.

## engine/events.py
- engine/events.py:726 (tools/page_measures.py:32 matches "is ended[ ,:-]+by way of": ", " still matches, so "is ended" was kept)
  old: {title} is ended - {how}.
  new: {title} is ended, {how}.
- engine/events.py:883 (no pronoun for an ally of unknown gender)
  old: {n.name} is dead. They gave their life in the fight.
  new: {n.name} is dead, killed fighting at your side.
- engine/events.py:1379
  old: ... Your house there is in danger - though it is fortified.
  new: ... Your house there is in danger, though it's fortified.
- engine/events.py:1385
  old: {name} has fallen - and your house there is a ruin. Your things are safe in the item box.
  new: {name} has fallen, and your house there is in ruins. Your things are safe in the item box.
- engine/events.py:1445
  old: {name} holds. The gate is yours, and the town knows it.
  new: {name} holds. You kept the gate.
- engine/events.py:1447
  old: The gate is lost; what becomes of {name} is in other hands now.
  new: The gate is lost. What happens to {name} now is out of your hands.

## engine/combat.py (refusals shown as notes)
- engine/combat.py:1800
  old: {move} is struck through a melee weapon, and you have none in hand.
  new: {move} needs a melee weapon, and you have none in hand.
- engine/combat.py:1802
  old: {move} has given all it has this fight.
  new: {move} is used up for this fight.
- engine/combat.py:2928 (a focus order with no foe there)
  old: There is nothing there for them to take.
  new: There's no one there for them to attack.

## engine/movement.py
- engine/movement.py:86
  old: You are stone: you cannot use a movement ability until Stoneform ends.
  new: You're stone. No movement abilities until Stoneform ends.
- engine/movement.py:95
  old: {target} is not behind any guard - you can reach it without {move}.
  new: {target} is not behind any guard, so you can reach it without {move}.
- engine/movement.py:98
  old: Nothing is fighting you - there is nothing to pull free of.
  new: Nothing is fighting you, so there's nothing to pull free of.
- engine/movement.py:104
  old: You are held fast - nothing breaks a grapple but getting free of it.
  new: You're held fast. Get free of the grapple first.
- engine/movement.py:118
  old: No one has fallen in this fight yet - there is no body to step out of.
  new: No one has fallen in this fight yet, so there's no body to step out of.
- engine/movement.py:124
  old: No enemy is below half health - there is no blood to follow.
  new: No enemy is below half health yet, so there's no blood to follow.

## engine/taming.py
- engine/taming.py:49
  old: {name} is still too strong and wild - wear it down first.
  new: {name} is still too strong and wild. You'll have to wear it down first.
- engine/taming.py:51
  old: You already keep as many tamed companions as you can lead - release one first.
  new: You already have as many tamed companions as you can lead, so release one first.
- engine/taming.py:108
  old: You already keep as many bound creatures as you can lead - release one first.
  new: You already have as many bound creatures as you can lead, so release one first.

## engine/equipment.py
- engine/equipment.py:39
  old: You cannot bear the {item}: your gift will not suffer anything heavier than cloth (Glass Cannon).
  new: You can't wear the {item}: your gift allows nothing heavier than cloth (Glass Cannon).

## scenes/audit_actions.py
- scenes/audit_actions.py:176
  old: Reported. What you just read, your note and the calls behind it are saved in {path}. Nothing is sent anywhere.
  new: Reported. What you just read and your note are saved in {path}, with the game's records behind them. Nothing is sent anywhere.
- scenes/audit_actions.py:187
  old: That still didn't come through - try it in different words.
  new: Still not sure what you mean. Try it in different words.
- scenes/audit_actions.py:209
  old: I'm not sure what you meant - could you say it another way?
  new: I'm not sure what you meant. Could you say it another way?

## scenes/explore_actions.py
- scenes/explore_actions.py:98
  old: You find a way: {r.name} - {r.description}
  new: You find a way: {r.name}. {r.description}

## scenes/check_actions.py
- scenes/check_actions.py:59
  old: It goes badly, as it always does when it goes wrong for you (All or Nothing)[: hurt].
  new: When it goes wrong for you, it goes badly (All or Nothing)[: hurt].

## Kept as is
- scenes/combat_scene.py: 10 lines (603 one order a turn, 878 already down, 933 Frugal Hands, 948 two items, 960 you use, 574 you tell, 1032 You got away., 1099 follows you now, 1137 Victory ledger, 1219 Found ledger; pane lines 395 and the rest)
- scenes/goddess.py: 10 lines (106/146 back to menu, 162 how the world sees you, 197/506/533/557 That can't be done, 448/450, 474/476, 481, 510 waits)
- main.py: 6 lines (88 llama-server unreachable: a developer's hand-started backend only, 107 data problems, 112, 120 newer version, 154 Continuing as, 209 crash.log)
- scenes/trial_actions.py: 8 lines (49, 59, 63, 68, 77, 82, 116, 135)
- engine/events.py: 6 lines (776 survivors give, 870 come to stand, 889 carried out, 903 rebuilding, 1378 danger/walls, 1388 house stands)
- engine/combat.py: 11 refusals (1798, 1805, 1812, 1814, 2914, 2916, 2920, 2922, 2924, 3136, 3142)
- engine/movement.py: 11 refusals
- engine/taming.py: 8 refusals
- engine/equipment.py: 6 lines
- scenes/audit_actions.py: 0 (the narrate there is a model question)
- scenes/explore_actions.py: 3 lines (60, 90, 99)
- scenes/check_actions.py: 4 lines (35, 40 lucky break, 212, 221)
- scenes/work_actions.py: 3 lines (140, 171, 214)
- scenes/pastime_actions.py: 5 lines (59, 64, 74, 100, 119)
- scenes/stats_actions.py: 5 lines (the stats sheet, functional)
- scenes/banter_actions.py: 2 (narrate of model text, no literal strings)

## Tests that pin old wording
- tools/sim/goes_on_525_test.py:193 "The model couldn't make sense of that" (the goddess fallback, goddess.py:121)
- tools/sim/creation_page_test.py:161 "The model couldn't read that concept this time. Nothing is lost - describe it again." (a default set used only if failures.yaml has no concept lines; goddess.py:456)
- tools/sim/page_measures_test.py:42-43 feed "... is ended - by way of ..." as shown input; tools/page_measures.py:32 regex still matches the new ", by way of" (no change needed unless the lead wants the fixture to match)
- Kept so tests still pass: "works outside a fight" (playthrough1_test:114), "LEVEL UP!" and "You got away." (golden_replay_test:67), "stone" (buffs_test:156), "not behind any guard" (ability_move_test:67), "wear it down" (taming_test:23), "release one first" (taming_test:56, taught_test:117), "Nothing is sent anywhere" (guard_test:81), "not sure what you meant" (improv_test:94), "Something went wrong" (plays_on_llama_528_test:203), "You find a way" (simbot.py:51).
- Golden recordings that show any changed note (a fled fight, a Phoenix save, level up, skinning offer) may need re-blessing.
