# Engine code that reads the typed line by pattern: census and measure

Second round of the audit, part `typed-patterns`. Nothing in the repository was changed. Scripts and their outputs are in
`C:/Users/tstil/AppData/Local/Temp/claude/dad68772ed0cbd02/d2ae1f65-36c6-4be3-9744-2919d03b2cce/scratchpad/audit/work/tp/`.

## 1. In short

- The owner's own census (`tools/line_census.py`, f648) counts **324 places in 53 files, 166 reader functions**, all in `engine/` and
  `scenes/`. `services/` and `npc/` have none: `services/fight.py` matches fields of the fight intent, `npc/life.py` reads speech a model wrote.
- Run on 1,888 real typed lines with the plan the model gave for each, today's repairs **change the model's reading on 492 lines (26%)**
  and change its kinds on 411. Most of that is three repairs undoing one habit of the model (a talk made of the deed's own words, a
  look nobody asked for, a goodbye said twice). Those are right most of the time.
- The readers that are **wrong most often** are the ones that overrule a field the plan already filled: who is spoken to
  (`hire_followup`, `to_the_named`), which deed it is (`join_guild_rewrite`, `move_to_present`), whether it is a rest (`on_other`),
  whose the draught is (`used_on` with `takes_oneself`).
- Sorted: **62 functions (131 places) replace by a field of the plan; 93 functions (162 places) keep, as eight shared readers with a
  corpus test; 11 functions (31 places) remove.**
- The one piece of infrastructure: **a handler gets its step, not the line.** Section 5.

## 2. What was measured, and how

| Source | What it holds | Used for |
|---|---|---|
| 54 tracked logs under `docs/measure` (prose_baseline, prose_a1, prose_a2) | 2,759 lines typed by the night bot; 2,148 reached the interpreter (2,511 calls with retries; 1,896 distinct lines with a plan); 86 went to a hire as chat with no reading; 13 to a yielded foe; 3 to the party intercept; 1 to the exit intercept; 291 fight readings | every count below |
| `data/replay/interp_cases.yaml` | 252 cases, each a line, a scene, a plan and what should happen | which readers the corpus pins, set beside which ones fire in play |

Method, all with the model stubbed (no model was loaded):

1. **Repairs and intercepts** (`bench_run.py`): each logged line, in the scene the interpreter's own request describes (place, people,
   party, partner, pack), with the logged plan as the model's answer, through today's intercepts and repairs on the bench of
   `tools/interp_eval.py`. 1,888 distinct (line, scene, plan) cases; 36 more skipped because today's world lacks the place.
2. **The hire intercept** (`bench_run.py hl`, `hc`, `hcp`, `dbg_hire.py`, `dbg_goes.py`): the same lines with a hire having spoken the
   turn before, and the 77 distinct lines the old runs sent to a hire as chat, typed again at Parth's trading square.
3. **Pure readers** (`h2.py`): `is_rest`, `asks_camp`, `asks_room`, `is_pose`, `hour_named`, `takes_oneself`, `is_goodbye`,
   `direction_in`, `wants_back`, `is_question`, `first_person_action`, the party's 29 hint substrings, the looking words: each on
   every distinct line, set beside the plan's kinds and fields.
4. **Handlers that read the line again** (`verify_a.py`, `verify_b.py`): the handler called as the tests call it, with a plan and a line.
5. **The corpus** (`corpus_cover.py`): all 252 cases on the bench, counting which repairs fire and which intercepts take a line.

Limits. The logged plans come from code about 130 features older than today's, so the lines that reached the old interpreter had
already passed the old intercepts: a count of what an intercept takes from them is a floor, and the hire run is a what-if (the state
"a hire spoke last turn" was set by hand; in the old runs 497 of 2,175 lines typed with a party came the turn after a hire spoke).
The bench scene is rebuilt from the interpreter's request, so wares, quests and the fight are missing: repairs that need them
(`buy_what_was_named`, `give_for_coin`, `carcass_part`, `one_harvest`) may fire less here than in play. The bot's fight lines are three
templates ("I use X on Y" 78, "I attack Y" 36, "I go for Y" 21 of 135 distinct) and none speaks to an ally, so the 24 places in
`scenes/combat_scene.py` could not be measured. The camp, the mentor's first stepping in and a yielded foe cannot be staged on the
bench (the census's own UNSTAGED list). Who was right is my reading of the line; the lines are printed so it can be checked.

## 3. What the patterns do to real lines

### 3.1 Repairs: how often each changes the model's reading, and how often it is wrong

| Repair | Fired on 1,888 logged lines | Wrong by reading | Fires in the corpus (252 cases) | Corpus cases that forbid it |
|---|---|---|---|---|
| narrated_talk | 195 | few; a leftover talk kept on some ("I approach the wolf and start skinning it for the hide." keeps a talk whose speech is "I approach the wolf") | 12 | 1 |
| drop_restatements | 89 (88 a look dropped) | 5 | 9 | 1 |
| deal_then_word | 70 | not read in full | 5 | 0 |
| one_goodbye | 56 | 0 of 14 read | **0** | 0 |
| quiet_parting | 35 | 0 of 10 read | 1 | 0 |
| gesture_only | 26 | 0; each turns a nod into an act that asks for a ruling call | 1 | 2 |
| move_to_present | 16 | **3** | 1 | 1 |
| audit_fix | 16 | not read | 2 | 0 |
| party_word | 14 | 2 | 1 | 1 |
| move_elsewhere | 6 | 0 | 18 | 5 |
| settle_targets | 5 | not read | 0 | 0 |
| name_the_target | 4 | 1 | 4 | 1 |
| to_the_named | 4 | **4** | 6 | 2 |
| wordless_talk | 4 | 0 | 1 | 0 |
| walk_after_word | 3 | 0 | 0 | 0 |
| join_guild | 1 | **1** | 2 | 2 |
| local_building | 1 | 1 arguable | 1 | 1 |
| scrub_markup | 1 | 0 | 2 | 1 |
| talk_to_deed | **0** | | 15 | 7 |
| coin_offered, tidy_fields | 0 | | 3 each | 1, 0 |
| give_for_coin, use_to_ability | 0 | | 2 each | 1 each |
| fishing, social_check, buy_what_was_named, grounded_item, carcass_part | 0 | | 1 each | 1 each |
| one_harvest | 0 | | 0 | 0 |

The corpus and the play do not weigh the same repairs: `one_goodbye` changed 56 real lines and no corpus case fires it;
`talk_to_deed` fires in 15 corpus cases and in none of 1,888 real lines; `move_elsewhere` 18 cases against 6 lines.

Examples, the wrong ones (the number in brackets is the case in `bench_out.jsonl`):

- **to_the_named, 4 of 4.** [1021] "I nod to the innkeeper and tell the group, 'Let's get moving toward the Adventurers' Guild House.'"
  The model: talk to the innkeeper, talk to a hire, move. After the repair: both talks to the innkeeper. The same on [1545] (butcher),
  [1679] (chandler), [1685] (tinker): "turn to the group", "tell my companions". Stub run (`verify_a.py`): also with "tell the
  others", "turn to my companions" and "tell everyone". The plan was right; the repair made it wrong.
- **join_guild, 1 of 1.** [189] "I tip my head slightly as a sign of respect. It has been an honor meeting all of you today."
  The model: a talk to the smith, summary "express gratitude to the guild master". After the repair: join_guild ("sign" from the line,
  "guild" from the model's own summary). Stub run: "The guild hall feels warm tonight." ("fee" in "feels"), "I tell the smith his
  design would suit the guild's door." ("sign" in "design"), "Ella, I'm only paying a visit to the guild today." all become
  join_guild, which takes the joining fee and sets rank F without a question (`scenes/guild_actions.py:353`).
- **move_to_present, 3 of 16.** [1597] "Go ahead and stamp it. Who else is around here that we need to talk to before we head out?"
  The model: talk to the clerk, look. After: look only; the words to the clerk are gone because the line opens with "Go". Stub run:
  the same for "Run that by me again, what does the contract pay?". [818] and [1668] ("I turn away from the group and start
  heading toward the door.") lose the walk and keep a talk to a clerk.
- **party_word, 2 of 14.** [82] "We're heading to the Temple of Parth next." at the guild house becomes a move to `parth` (the
  town), not `parth_temple`. [352] "We need to find Parth first." becomes a search for "Parth".
- **name_the_target, 1 of 4.** [457] "I turn to the clerk with the spectacles and offer my willow crossbow for sale." The model's
  talk named one clerk; the sale is put on the guild clerk, by the trade word.
- **drop_restatements, 5 of 89.** The dropped look was asked for in an inflected word the list (`LOOKING`, `scenes/plan_repairs.py:98`)
  lacks: [1661] "squinting at the charcoal marks" (the look was the only reading of the note), [1407] "keeping my eyes on the path
  ahead", [1796] "keep my eyes on the shadows", [1355] "watching him", [611] "listening to the dwarf's tale".

### 3.2 Intercepts: lines taken before the model reads them

| Intercept | On the logged lines | Wrong by reading |
|---|---|---|
| hire (a hire spoke the turn before; `hire_followup`) | what-if on 1,888 lines: **178 taken (9.4%)** | the model had read 9 as a talk to a hire; **169 otherwise**: 127 a talk to someone else here (116 to the person the player was already talking with), 22 a parting, 9 a walk, 2 a purchase, 2 a quest taken, 7 other deeds |
| hire, the old runs | 86 of 2,759 lines went to a hire as chat, never read | of the 77 distinct ones, **38 are still chat today** at Parth's square; at least 16 of the 38 are a step proposed or a deed (below) |
| yielded | 13 lines taken in the old runs | the verdict was not judged (it needs the fight); 4 of the 6 lines read also say what to do next ("I let it live and tell the group we're heading back to the Adventurers' Guild House."), and the turn's log shows no reading of that part |
| party | 3 lines taken in the old runs; today 4 of 1,881 lines pass its 29 substrings | in 2 of the 3 the player's own deed was never read ("I signal for the group to stay back and head toward the trees to find Parth.") |
| farewell (`is_goodbye`) | **0** of 2,759 lines; and 0 of the 92 parting speeches the model read | the bot does not type a bare goodbye; nothing to judge |
| exit | 1 line in the old runs | not judged |
| errand, trial, camp, mentor's four, spell_book | 0 on these lines (the state was not there) | not measured |

Lines the hire intercept still takes as chat today, a hire having spoken the turn before (stub runs, `dbg_hire.py`, `dbg_goes.py`):

- "We need to get to the Adventurers' Guild House before we do anything else." The walk never happens. `goes_to_place` tests only
  the first to / for / into of a line, because its pattern takes the rest of the line (`scenes/party_actions.py:501`): "need to" is
  tested, "to the Adventurers' Guild House" never is. The same for "Comfort is for people who aren't looking for a payday. Let's
  get to the Adventurers' Guild House."
- "Parth is our priority; let's move out.", "Forget the ale for now, we're headed straight to the Adventurers' Guild House."
  `party_proposal` reads only the opening of the line (`PROPOSAL`, anchored at the start).
- "We need to reach Riverhaven before the light fails completely." ("reach" is not a going word; Riverhaven is no part of this town.)
  "Let's focus on finding that wild garlic before the mud gets too deep." ("find" is a seeking word, "finding" is not.)
- "I don't have time for mercy; I finish off the lizardfolk." A deed in the second clause; `first_person_action` reads the first.
- "Six copper a bundle seems fair; tell me, have you noticed anything unusual in the market lately?" typed to the chandler the
  player is talking with: the model read a purchase and a question to the chandler; the hire answers instead. Nothing in
  `hire_followup` looks at the conversation partner.

### 3.3 Handlers: the line read again after the plan was made

| Reader | On the logged lines | Stub run |
|---|---|---|
| `on_other` + `is_rest` (`scenes/world.py:4536`) | 64 plans have an `other` step. `is_rest` says yes on 12 lines; the plan has a wait on 6 of them. 117 of the 123 waits the model read have no rest word at all. The one logged line of the shape, "I find some flat stones near the shrubs and lay down to rest." (other, then wait until dawn), is 13 words: one over the limit. | "I find a spot by the hearth and lie down to rest." with the plan (other, wait until dawn): 900 minutes, then 960 more, 31 hours. With the wait alone: 780. "I can't sleep, so I whittle a stick by the fire." (other): 900 minutes asleep, no ruling asked. |
| `used_on` + `takes_oneself` (`scenes/inventory_actions.py:265`) | 21 plans have a `use` step; `takes_oneself` says yes on none of them ("take a long drink from my flask", "take a swig", "finish my drink") and on 43 lines with no use at all ("I sit down", "a stranger like myself"). | "I pull a flask from my belt and take a long pull, then look over at Gwild." (a logged line; plan: use the draught, talk to Gwild): refused, "Is the healing draught for you or for someone else?" The name is the talk step's target. |
| `on_wait` + `hour_named` (`engine/clock.py:72`) | yes on 0 lines; the 24 waits with a time carried it in `wait_until` (17) or `wait_minutes` (4) | first round, engine2-4 |
| `first_person_action` (`engine/actions.py:193`) | yes on 1,442 lines; the plan has no deed on 95 of them ("I turn to the group and say...": a manner of speaking). The plan has a deed and it says no on **217 lines (11%)**: "Let's head to...", "We need to reach...", the bot's most common way to go somewhere. | feeds `hire_followup`, `drop_narrated_talk`, the mentor's intercept and the clarifying question's let-go |
| `is_pose` (`engine/world_improv.py:36`) | a pose word on 620 of 1,896 lines; read only for an act that worked | not run |
| the party's hint substrings (`scenes/party_actions.py:26`) | 4 of 1,881 lines typed with a party, once the guild's own name is cut out: tight | |

### 3.4 The audit's word test (`engine/intent_audit.py:200`, `risk_flags`): which lines get a second model reading

Run with today's code on the same lines, after today's repairs (`bench_run.py rf`): **825 of 1,887 lines (43.7%) are flagged**, each
flag two model calls (`audit_meaning`, `audit_compare`) and sometimes a third (a second `interpret_action`). The old logs agree:
917 of 2,148 interpreted lines (43%) ran both calls.

| Flag | Lines | Alone | What sets it |
|---|---|---|---|
| multi_intent | 697 | 506 | the plan has two steps or more |
| unmatched_verb | 165 | 74 | a bare word of the line is a verb of the action table and no step has its kind: board 53 ("the board"), give 41 ("I give a nod"), hand 26 ("my hand"), rest 14 ("the rest of those lizardfolk"), butcher 9 (the butcher), kill 4 ("the kill site") |
| other_intent | 86 | 13 | a step of kind other |
| money_context | 50 | 28 | a coin word beside a talk, a buy, a gift |
| unmarked_force | 33 | | a force word and no step marked force |
| invalid_step | 19 | | a step the situation cannot carry |
| unmentioned_buy | 4 | | a ware the line does not name |

What the second reading did, in the old logs: of the 917 audits, 173 lines were read again with a review note, and the second plan
differed from the first on 138 (kinds, targets, places or things). Most changes drop a talk to a hire made of the deed's own
words, which `narrated_talk` now does in code (195 lines above); one dropped a purchase nobody asked for ("I take the coin and head
for the door." had been read as buying eight healing draughts); some dropped the walk the line asked for ("I squint through the
fog and tell Alwick we need to push toward the Willowmead wetlands.").

## 4. The census, sorted

The rows are the 166 reader functions of the owner's census, with the places each holds (324 in all), the door the line comes in by,
what the function decides, the field of the plan that carries the fact (or the shared reader it belongs to), what pins it, and what
the logged lines showed. "N test files" is how many files under `tools/sim` name the function; the corpus counts are cases that fire
a repair or are taken by an intercept, and cases that forbid it (`not_by`). R2, R3 and R4 are the steps of
`docs/design/29_one_reader_plan.md` (an untracked draft).

The shared readers, by letter: **N** which thing of the engine's own list the words name (43 functions, 62 places); **A** who the line
speaks to (9, 35; `engine/addressing.py` is it); **Q** an answer to the game's own question (12, 27; `engine/questions.py` is it);
**W** plain word sets and stemmers that decide nothing alone (13, 17); **M** the game's own marks, # / * and quotes (7, 9);
**I** is it a question (4, 7; five copies with `join_guild_rewrite`'s own); **C** a number or a coin amount in words (3, 3);
**G** said and not denied (1 here; `NEGATED`, `UNPAID`, `YIELD_NOT`, `camp_refused`, `room_refused` and `engine/truth.py` are more copies).

What the census cannot see (its own note in `docs/design/21_play_faults_plan.md`): the line stored on the scene and read later
(`self.last_text` at `scenes/world.py:4201`, `self.line_text`, `self.fight_text`), a line handed on by keyword, a comparison with ==.

### Replace by a field of the plan (62 functions, 131 places)

| Reader | Places | Door | Decides | The plan's field, or the shared reader | Pinned by | On the logged lines |
|---|---|---|---|---|---|---|
| `engine/actions.py:201` first_person_action | 3 | turn | the line does a deed (not only speech) | a step whose kind is not talk; R3 `words` | 2 test files | yes on 1,442; plan has no deed on 95; plan has a deed and it says no on 217 |
| `engine/actions.py:263` takes_oneself | 1 | turn | the user takes the thing themself | use.target empty, and the name is another step's target | 2 test files | yes on 0 of 21 logged use steps; yes on 43 lines with no use (down, myself) |
| `engine/clock.py:72` hour_named | 1 | turn | the hour a wait lasts until | wait_until / wait_minutes (a clock hour is not in the closed list: one more value) | 1 test file | yes on 0 lines (24 waits carried their own time) |
| `engine/combat_improv.py:33` effect_by_words | 1 | fight:turn | what an improvised fight move is after | the fight intent (doc 29 R4) | 1 test file |  |
| `engine/exits.py:95` direction_in | 1 | turn | a compass direction in the line | move.destination as an offered exit id | no test names it | yes on 31 lines, 28 with a move |
| `engine/exits.py:105` match | 6 | intercept:exit | the line leaves by an exit (the exit intercept) | move.destination; the intercept becomes an offer (review 5.1 point 4) | corpus: takes 3, forbidden in 4 |  |
| `engine/features.py:38` leaving | 1 | turn | the walk leaves this place | move.destination resolved (engine4-5) | 30 test files |  |
| `engine/partings.py:37` is_goodbye | 2 | intercept:farewell | the line is only a goodbye | kind leave_conversation (92 logged plans); the intercept never fired on 2,759 logged lines | 2 test files; corpus: takes 2, forbidden in 1 | yes on 0 lines and on 0 of 92 parting speeches |
| `engine/world_improv.py:27` read_effect | 2 | turn | what an improvised act is after | the act ruling's own fields (f603) | 6 test files |  |
| `engine/world_improv.py:38` is_pose | 2 | turn | the act is only a gesture | the act ruling (sense) or R3 `words` | no test names it | a pose word on 620 of 1,896 lines; read only for an act that worked |
| `engine/world_improv.py:45` is_rest | 1 | turn | the line goes to sleep | kind wait + wait_until (117 of 123 logged waits have no rest word) | no test names it | yes on 12 lines, plan has a wait on 6; 117 waits without a rest word |
| `engine/world_improv.py:50` asks_camp | 2 | turn | the sleep makes a camp first | a field on wait: shelter = camp | 1 test file | yes on 2 lines, neither a wait |
| `engine/world_improv.py:55` asks_room | 2 | turn | the sleep takes a room first | a field on wait: shelter = room | no test names it | yes on 1 line, plan agrees |
| `scenes/camp_actions.py:56` keyword_intent | 1 | intercept:camp | what is done at the camp, when the model fails | the camp's kinds offered to the one reader (llm-rest-11) | no test names it; corpus: takes 0, forbidden in 0 |  |
| `scenes/camp_actions.py:63` keyword_methods | 1 | intercept:camp | how the camp is approached, when the model fails | the same | no test names it; corpus: takes 0, forbidden in 0 |  |
| `scenes/combat_scene.py:632` own_part | 2 | fight:turn | the player's own move in a line that orders | the fight intent (doc 29 R4) | 4 test files |  |
| `scenes/combat_scene.py:659` act | 3 | fight:turn | a word to the mentor, a foe or a companion mid-fight | fight intent kind talk + target | name too common to search |  |
| `scenes/combat_scene.py:892` past_item | 3 | fight:turn | the line uses a thing and then does more | fight intent item | no test names it |  |
| `scenes/combat_scene.py:916` ally_for_item | 5 | fight:turn | whom a draught is for in a fight | fight intent target | 1 test file |  |
| `scenes/guild_actions.py:569` payer_for_handin | 1 | turn | who pays for a hand-in | the step's target | no test names it |  |
| `scenes/inventory_actions.py:479` ware_paid_for | 1 | turn | the coin given pays for a ware | kind buy + ware | 1 test file |  |
| `scenes/inventory_actions.py:494` fee_asked | 2 | turn | the coin given pays a fee | the kind of the fee's deed (join_guild...) | no test names it |  |
| `scenes/inventory_actions.py:511` is_bribe | 1 | turn | the coin given is a bribe | checks (it already reads intent.checks first) | 1 test file |  |
| `scenes/inventory_actions.py:566` tithe_box | 1 | turn | the coin goes in the tithe box | give.target empty at a temple | 1 test file |  |
| `scenes/inventory_actions.py:962` on_commission | 2 | turn | the player's own material is used | a field on commission | no test names it |  |
| `scenes/listening.py:52` gesture_only | 2 | repair:gesture_only | a talk that is only a gesture | R3 `words` (the step's words hold no speech) | 1 test file; corpus: fires in 1, forbidden in 2 | 26 firings, sound; each costs a ruling call |
| `scenes/mentor_actions.py:510` mentor_read | 1 | turn | the words to the mentor are hostile | checks, or the mentor reply's own field | no test names it |  |
| `scenes/mentor_actions.py:570` mentor_talk_means_go | 2 | turn | a word to the mentor means go inside | kind move; an offer to the reader | 1 test file |  |
| `scenes/mentor_actions.py:629` mentor_quoted_turn | 4 | intercept:mentor_quoted | a quoted line is for the mentor | talk.target; an offer | no test names it; corpus: takes 1, forbidden in 1 |  |
| `scenes/mentor_actions.py:642` mentor_named_turn | 2 | intercept:mentor_named | a line naming the mentor is for her | talk.target; an offer | no test names it; corpus: takes 2, forbidden in 1 |  |
| `scenes/mentor_actions.py:656` mentor_go_hunt | 8 | intercept:mentor_hunt | the line sets out on the first hunt | move.destination; an offer | 1 test file; corpus: takes 2, forbidden in 1 |  |
| `scenes/part_actions.py:34` part_move | 2 | turn | the walk goes deeper into this place | move.destination as a part's ref (it reads the ref first) | no test names it |  |
| `scenes/part_actions.py:138` explore_parts | 1 | turn | the search goes deeper | search.seek / destination | no test names it |  |
| `scenes/part_actions.py:205` about_spot | 2 | turn | the search is about the spot stood on | search.seek | no test names it |  |
| `scenes/party_actions.py:44` keyword_party | 1 | intercept:party | which party order, when the model fails | the party's kinds offered to the one reader (llm-rest-10) | no test names it; corpus: takes 1, forbidden in 1 |  |
| `scenes/party_actions.py:98` party_turn | 2 | intercept:party | the line could be about the party (29 substrings) | an offer to the reader; 4 of 1,881 logged lines pass today | 5 test files; corpus: takes 1, forbidden in 1 | 4 of 1,881 pass the substrings |
| `scenes/party_actions.py:137` companion_join | 1 | intercept:party | a friend is asked along | an offer to the reader | 1 test file; corpus: takes 1, forbidden in 1 |  |
| `scenes/party_actions.py:378` party_proposal | 2 | intercept:party | the line proposes to go, search or rest | kinds move / search / wait (217 logged lines have a deed it and first_person_action miss) | no test names it; corpus: takes 1, forbidden in 1 | opens the line only; misses reach, get to, hit, finding |
| `scenes/party_actions.py:519` goes_to_place | 1 | intercept:hire | the line walks to a named place | move.destination | no test names it; corpus: takes 8, forbidden in 10 | tests only the first to/for/into of a line |
| `scenes/party_actions.py:540` hire_wants_talk | 3 | intercept:hire | the line is said to a hire (the hire intercept) | talk.target; the follow-up half is removed (178 of 1,888 taken, 169 against the plan) | 3 test files; corpus: takes 8, forbidden in 10 | 178 of 1,888 taken when a hire spoke last; 169 against the plan |
| `scenes/party_actions.py:566` own_deed | 3 | intercept:hire | a clause is the player's own deed | a step that is not talk | no test names it; corpus: takes 8, forbidden in 10 |  |
| `scenes/party_actions.py:633` hire_feeling | 2 | turn | how the words to a hire feel | the hire reply's own field | 3 test files |  |
| `scenes/party_actions.py:1029` tend_when_asked | 1 | intercept:hire | a hire is asked to tend wounds | an offer to the reader (kind + target) | 1 test file; corpus: takes 8, forbidden in 10 |  |
| `scenes/plan_repairs.py:193` social_check | 1 | repair:social_check | a talk is a persuasion, a threat or a lie | talk.checks (10 logged plans carry it; 0 firings on 1,888 lines) | 1 test file; corpus: fires in 1, forbidden in 1 | 0 firings |
| `scenes/plan_repairs.py:354` move_elsewhere | 5 | repair:move_elsewhere | a walk named no place | move.destination from the offered list (R2); 6 firings, all sound | 1 test file; corpus: fires in 18, forbidden in 5 | 6 firings, 0 wrong |
| `scenes/plan_repairs.py:375` walk_words | 2 | repair:move_elsewhere | the walk's own words | R3 `words` | 1 test file; corpus: fires in 18, forbidden in 5 |  |
| `scenes/plan_repairs.py:419` drop_restatements | 3 | repair:drop_restatements | a step repeats another step's words | R3: two steps that claim the same words are one (88 looks dropped, 5 wrongly) | no test names it; corpus: fires in 9, forbidden in 1 | 89 firings, 5 wrong |
| `scenes/plan_repairs.py:445` buy_what_was_named | 1 | repair:buy_what_was_named | the ware bought is the one named | buy.ware as an offered id (R2); 0 firings | 1 test file; corpus: fires in 1, forbidden in 1 | 0 firings |
| `scenes/property_actions.py:68` property_buy | 2 | turn | the line buys or rebuilds a property | kind buy + ware | 2 test files |  |
| `scenes/road_actions.py:624` get_past | 1 | turn | the line goes around a hazard | a field on move, or the act ruling | 4 test files |  |
| `scenes/spell_actions.py:41` spell_book_turn | 4 | intercept:spell_book | the line reads a spell book (an intercept) | kind use + item (on_use already reads a book) | 1 test file; corpus: takes 1, forbidden in 1 |  |
| `scenes/training_actions.py:49` on_train | 4 | turn | what is trained: a skill, a drill, an ability | a field on train (seek) | 2 test files |  |
| `scenes/trial_actions.py:55` trial_turn | 5 | intercept:trial | the line asks for the rank trial (an intercept) | an offer to the reader | no test names it; corpus: takes 3, forbidden in 1 |  |
| `scenes/world.py:2607` coin_offered | 4 | repair:coin_offered | a talk with coin named is a gift of coin | kind give + item; 0 firings | no test names it; corpus: fires in 3, forbidden in 1 | 0 firings |
| `scenes/world.py:2662` drop_narrated_talk | 1 | repair:narrated_talk | a talk made of the deed's own words | R3: two steps that claim the same words (195 firings, 10% of lines) | no test names it; corpus: fires in 12, forbidden in 1 | 195 firings, mostly sound |
| `scenes/world.py:2724` local_building | 2 | repair:local_building | a building named by kind is this town's | move.destination from the offered list (R2) | no test names it; corpus: fires in 1, forbidden in 1 | 1 firing, arguable |
| `scenes/world.py:3299` looks_like_exploring | 1 | turn | the walk is exploring | kind explore | no test names it |  |
| `scenes/world.py:3452` on_move | 1 | turn | the destination is a part's ref | reads the field: no line | 8 test files |  |
| `scenes/world.py:3816` on_talk | 1 | turn | the words to the person say a thing the handler acts on | the step's speech | 11 test files |  |
| `scenes/world.py:4323` toward_trail | 3 | turn | the walk follows a trail | move.destination / seek | no test names it |  |
| `scenes/world.py:4521` rest_asked | 1 | turn | until when the rest lasts | wait_until | no test names it |  |
| `scenes/world.py:4536` on_other | 1 | turn | an unnamed act is a rest, when the line has a rest word and 12 words or fewer | kind wait (the reader's own step) | 18 test files | 64 logged plans have an other step; stub: sleeps twice, sleeps on a negated line |

### Keep, as one shared reader with a corpus test (93 functions, 162 places)

| Reader | Places | Door | Decides | The plan's field, or the shared reader | Pinned by | On the logged lines |
|---|---|---|---|---|---|---|
| `engine/act.py:207` words_key | 1 | turn | a key for a ruling already made on the same words | W: decides nothing | 1 test file |  |
| `engine/addressing.py:77` _split_mine | 3 | intercept:party | the player's own deed inside words said to a companion | A (the one module); out of a fight the plan's steps | no test names it; corpus: takes 1, forbidden in 1 |  |
| `engine/addressing.py:111` addressed | 20 | intercept:party | who the line speaks to | A: the one reader; out of a fight talk.target carries it | 5 test files; corpus: takes 1, forbidden in 1 |  |
| `engine/addressing.py:192` spoken_of | 1 | fight:turn | a companion named, not spoken to | A | no test names it |  |
| `engine/brief.py:81` asked | 1 | turn | which topic the words ask about | W | name too common to search |  |
| `engine/candidates.py:36` points_back | 1 | turn | the line points back at something said before | builds the list offered to the model | no test names it |  |
| `engine/candidates.py:40` words | 1 | turn | the content words of the line | W; builds the list offered to the model | name too common to search |  |
| `engine/candidates.py:66` places | 1 | turn | places the words could name | N; builds the list offered to the model | name too common to search |  |
| `engine/convo.py:18` _norm | 1 | turn | word set of a question, to find a repeat | W | name too common to search |  |
| `engine/convo.py:28` is_question | 1 | turn | the line is a question | I: one of five copies | no test names it | yes on 184 lines, all with a talk |
| `engine/crafting.py:35` find_base | 1 | turn | which base item the words name | N; commission.item as an offered id (R2) | no test names it |  |
| `engine/crafting.py:101` pick_material | 1 | turn | which material the words name | N | no test names it |  |
| `engine/discovery.py:103` words | 1 | turn | content words of what is sought | W | name too common to search |  |
| `engine/discovery.py:122` match_lead | 1 | turn | which lead the sought words mean | N on search.seek | no test names it |  |
| `engine/elements.py:31` of_text | 1 | turn | which element the words name | N | 1 test file |  |
| `engine/encounters.py:48` matching | 4 | turn | a creature name made singular | W: one stemmer (inventory._stem is another) | 4 test files |  |
| `engine/exits.py:136` pick | 5 | turn | which fork the answer names | Q | name too common to search |  |
| `engine/exits.py:157` wants_back | 3 | turn | the answer turns back | Q | 1 test file |  |
| `engine/features.py:264` named_part | 1 | turn | which part of the place the words name | N | 1 test file |  |
| `engine/features.py:284` find | 1 | turn | which feature the words name | N | name too common to search |  |
| `engine/inventory.py:87` _plain_words | 1 | turn | stemmed words of a thing's name | W | no test names it |  |
| `engine/inventory.py:307` find_recipe | 1 | turn | which recipe the words name | N (engine4-1) | 1 test file |  |
| `engine/lessons.py:46` _has | 1 | turn | a lesson word in the line | W | name too common to search |  |
| `engine/lessons.py:53` from_words | 1 | turn | which stat or skill a lesson is asked in | N on the step's words | 2 test files |  |
| `engine/locks.py:15` words | 1 | turn | words of a lock or key | W | name too common to search |  |
| `engine/mentor.py:116` is_question | 2 | turn | the line is a question | I: one of five copies | no test names it |  |
| `engine/mentor.py:124` wants_to_go_on | 1 | turn | the answer says go on | Q | 1 test file |  |
| `engine/mentor.py:267` says_yes | 2 | turn | the answer is yes | Q (questions.yes_no exists) | 1 test file |  |
| `engine/mentor.py:281` addresses | 1 | turn | the line names this person | A | 2 test files |  |
| `engine/mentor.py:286` named | 1 | turn | the mentor's name is in the line (substring) | A | name too common to search |  |
| `engine/mentor.py:319` topics_in | 2 | turn | which lesson topic the words name | N | 1 test file |  |
| `engine/mounts.py:45` find | 1 | turn | which mount the words name | N | name too common to search |  |
| `engine/objects.py:25` _words | 1 | turn | words of an object | W | name too common to search |  |
| `engine/orenna.py:35` name_said | 1 | turn | her name is said (substring) | N | no test names it |  |
| `engine/party_director.py:112` named | 1 | turn | a companion's name in the line | A | name too common to search |  |
| `engine/property.py:63` find_upgrade | 1 | turn | which upgrade the words name | N | no test names it |  |
| `engine/questions.py:40` _opens_with | 1 | turn | the answer opens with a choice | Q: the module the others should use | no test names it |  |
| `engine/severity.py:73` is_silent | 3 | turn | a shown line is a gesture only | M | no test names it |  |
| `engine/situation_parts.py:1510` _words | 1 | turn | content words | W | name too common to search |  |
| `engine/situation_parts.py:1540` told_by | 1 | turn | a label is in the speech | N | 1 test file |  |
| `engine/taming.py:81` release | 2 | turn | which tamed creature the words name | N; release.target as an offered id | 20 test files |  |
| `engine/world_improv.py:166` what_of | 2 | turn | the words of the act, trimmed for the narrator | W: decides nothing | 1 test file |  |
| `scenes/arc_actions.py:52` yield_blow | 1 | intercept:yielded | the answer to a yielded foe strikes | Q | no test names it; corpus: takes 0, forbidden in 0 |  |
| `scenes/arc_actions.py:74` yield_intercept | 2 | intercept:yielded | kill or spare, the answer to a yielded foe | Q; the rest of the line goes on to the reader (13 logged lines, 4 with a second part lost) | 2 test files; corpus: takes 0, forbidden in 0 | 13 old lines taken; not re-run (needs a fight) |
| `scenes/arc_actions.py:507` secret_lines | 1 | turn | the speech promises the captive mercy | G: said and not denied (scenes1-6) | 1 test file |  |
| `scenes/camp_actions.py:260` camp_target | 3 | intercept:camp | which guard the words name | N (scenes1-10) | no test names it; corpus: takes 0, forbidden in 0 |  |
| `scenes/camp_actions.py:308` camp_turn | 1 | intercept:camp | the line is a # or / command | M | no test names it; corpus: takes 0, forbidden in 0 |  |
| `scenes/combat_scene.py:465` order_at | 2 | fight:turn | where an order's words end | A | no test names it |  |
| `scenes/combat_scene.py:495` orders_in | 5 | fight:turn | orders to companions in a fight line | A + N for the foe (scenes1-10) | 1 test file |  |
| `scenes/combat_scene.py:643` outside_ability | 1 | fight:turn | an ability named that is not brought | N | 1 test file |  |
| `scenes/combat_scene.py:859` foe_named | 1 | fight:turn | which foe the words name | N | no test names it |  |
| `scenes/combat_scene.py:902` names_consumable | 2 | fight:turn | a draught is named | N | no test names it |  |
| `scenes/explore_actions.py:26` part_of_here | 1 | turn | which part of the place a destination names | N | no test names it |  |
| `scenes/field_actions.py:516` field_speak_corpse | 2 | turn | which body the words name | N | 1 test file |  |
| `scenes/field_actions.py:750` pick_gear | 1 | turn | which gear the words name | N | no test names it |  |
| `scenes/field_actions.py:787` on_answer_reforge_keep | 2 | turn | the answer to the reforge question | Q + C | no test names it |  |
| `scenes/field_actions.py:814` on_answer_reforge_take | 4 | turn | new or old, the answer to the reforge question | Q | no test names it |  |
| `scenes/guild_actions.py:376` pick_posting | 2 | turn | which posting the words name | N + C; accept_quest.item | 2 test files |  |
| `scenes/inventory_actions.py:289` named_away | 1 | turn | someone of the town named who is not here | N | no test names it |  |
| `scenes/inventory_actions.py:412` coin_word | 1 | turn | coin is named | C | 1 test file |  |
| `scenes/inventory_actions.py:419` coin_amount | 1 | turn | how much coin | C: one number reader (scenes2-3) | no test names it |  |
| `scenes/law_actions.py:35` _words | 1 | turn | words of a thing | W | name too common to search |  |
| `scenes/law_actions.py:242` create_object | 1 | turn | a key is asked for | N | no test names it |  |
| `scenes/law_actions.py:478` on_answer_law | 1 | turn | pay, bribe, run or jail: the answer to the watch | Q (scenes2-4) | 1 test file |  |
| `scenes/listening.py:19` said | 1 | repair:grounded_item | a name's words are in the line | N: the rule the others should use | corpus: fires in 1, forbidden in 1 |  |
| `scenes/markup.py:11` segments | 1 | turn | the game's own markup in the line | M | no test names it |  |
| `scenes/markup.py:27` has_markup | 1 | turn | the line has markup | M | no test names it |  |
| `scenes/mentor_actions.py:381` mentor_intercept | 1 | intercept:mentor_intercept | the line is a # or / command | M | 5 test files; corpus: takes 0, forbidden in 0 |  |
| `scenes/party_actions.py:309` party_pick | 4 | intercept:party | which hire the words name | N + C | no test names it; corpus: takes 1, forbidden in 1 |  |
| `scenes/party_actions.py:454` hire_named | 1 | turn | a hire's first name is in the line | A | no test names it |  |
| `scenes/party_actions.py:678` hire_frame_reasons | 1 | turn | the line is a # or / command | M | no test names it |  |
| `scenes/party_actions.py:850` party_promote | 3 | intercept:party | which hire to promote | N | 1 test file; corpus: takes 1, forbidden in 1 |  |
| `scenes/party_actions.py:875` party_dismiss | 1 | intercept:party | which hire to dismiss | N | 2 test files; corpus: takes 1, forbidden in 1 |  |
| `scenes/passive_hooks.py:87` check_bonuses | 3 | turn | the words touch history or dark lore (a check bonus) | N on the step's words, whole words | 3 test files |  |
| `scenes/pastime_actions.py:88` only_asks | 3 | turn | the line only asks about a pastime | I: one of five copies | no test names it |  |
| `scenes/plan_repairs.py:310` ware_named | 1 | repair:talk_to_deed | which ware the words name | N | 1 test file; corpus: fires in 15, forbidden in 7 |  |
| `scenes/quirk_actions.py:24` is_answer | 3 | intercept:errand | the line answers a companion's errand | Q | no test names it; corpus: takes 1, forbidden in 1 |  |
| `scenes/quirk_actions.py:35` about_errand | 2 | intercept:errand | the line is about the errand asked | Q | no test names it; corpus: takes 1, forbidden in 1 |  |
| `scenes/road_actions.py:494` landmark_named | 1 | turn | which landmark the words aim at | N | 1 test file |  |
| `scenes/spell_actions.py:124` pick_line | 1 | turn | which spell line the words name | N | no test names it |  |
| `scenes/spell_actions.py:158` take_rank_lesson | 1 | turn | which numbered lesson | C | no test names it |  |
| `scenes/training_actions.py:74` asks_what | 1 | turn | the line asks what can be trained | I | no test names it |  |
| `scenes/training_actions.py:172` on_learn_ability | 2 | turn | which ability, by number or name | N + C | 2 test files |  |
| `scenes/world.py:871` quiet_return | 1 | turn | a place name in the words | N | 3 test files |  |
| `scenes/world.py:2087` equip_command | 1 | turn | the #equip command's words | M | 2 test files |  |
| `scenes/world.py:2711` those_named | 2 | turn | everyone here the line names | N / A | 1 test file |  |
| `scenes/world.py:3348` names_person | 1 | turn | a person named as a destination | N | 1 test file |  |
| `scenes/world.py:3401` names_far_place | 1 | turn | a far place named | N | no test names it |  |
| `scenes/world.py:3415` nearest_alike | 1 | turn | the nearest place of a like name | N | 2 test files |  |
| `scenes/world.py:3548` names_place | 1 | turn | which place the words name | N | 1 test file |  |
| `scenes/world.py:3580` travel_route | 1 | turn | a place on the way named | N | 3 test files |  |
| `scenes/world.py:4073` on_ability | 4 | turn | which ability the line names (substring) | N; ability as an offered id (R2) | 5 test files |  |
| `scenes/world.py:4380` creature_named | 1 | turn | which creature the words name | N | 1 test file |  |

### Remove (11 functions, 31 places)

| Reader | Places | Door | Decides | The plan's field, or the shared reader | Pinned by | On the logged lines |
|---|---|---|---|---|---|---|
| `engine/intent_audit.py:101` _content | 1 | turn | content words, for the audit's compare | goes with the audit (doc 29 R3) | no test names it |  |
| `engine/intent_audit.py:176` _words | 1 | turn | words of the line, for the audit's flags | goes with the audit | name too common to search |  |
| `engine/intent_audit.py:208` risk_flags | 2 | turn | the line is risky enough for a second model reading | R3's coverage check by code | 8 test files |  |
| `scenes/listening.py:80` to_the_named | 2 | repair:to_the_named | a talk to a companion is for a townsperson | talk.target already says who (4 of 4 logged firings wrong) | 2 test files; corpus: fires in 6, forbidden in 2 | 4 firings, 4 wrong |
| `scenes/party_actions.py:490` not_to_them | 7 | intercept:hire | the line is not for the hire who spoke last | talk.target; goes with hire_followup | no test names it; corpus: takes 8, forbidden in 10 | see hire_wants_talk |
| `scenes/plan_repairs.py:250` talk_to_deed | 3 | repair:talk_to_deed | a talk is really a deed | the plan's kind (0 firings on 1,888 lines; 15 corpus cases) | 1 test file; corpus: fires in 15, forbidden in 7 | 0 firings |
| `scenes/plan_repairs.py:285` line_part | 1 | repair:talk_to_deed | the clause a deed word stands in | R3 `words` | no test names it; corpus: fires in 15, forbidden in 7 |  |
| `scenes/plan_repairs.py:294` give_for_coin | 3 | repair:give_for_coin | a give for coin is a sale | kind sell (0 firings) | 1 test file; corpus: fires in 2, forbidden in 1 | 0 firings |
| `scenes/plan_repairs.py:383` fishing | 2 | repair:fishing | the line fishes | kind forage / other (0 firings) | 7 test files; corpus: fires in 1, forbidden in 1 | 0 firings |
| `scenes/world.py:2563` move_to_present | 2 | repair:move_to_present | a talk that is the line itself after a going word; a walk before a talk | R3: steps that claim the same words (3 of 16 logged firings wrong) | 3 test files; corpus: fires in 1, forbidden in 1 | 16 firings, 3 wrong |
| `scenes/world.py:2579` join_guild_rewrite | 7 | repair:join_guild | a talk at the clerk's is joining the guild | kind join_guild exists (1 of 1 logged firing wrong) | 1 test file; corpus: fires in 2, forbidden in 2 | 1 firing, 1 wrong |

## 5. The one piece of infrastructure

**A handler gets its step, not the line.** Today `run_step` calls `on_<kind>(intent, text)` and 131 places read `text` again for a
fact the step has, or should have, as a field. The eleven faults of the first round and the six here are that one seam:

- two readings of one line (the model's field and a pattern's) with no rule for which wins, so each handler chose for itself:
  `hour_named` overrules `wait_until`, `to_the_named` overrules `target`, `join_guild_rewrite` overrules `kind`;
- the whole line read for one step, so a word that belongs to another step decides this one (`on_other`'s rest, `used_on`'s name,
  `inventory.find` over every word of the line);
- the same small question answered by private copies: a name in words (43 functions), a number (3), a question (5), a denial (6).

The piece, in the order it can be built and measured (it is points 3 and 4 of section 5.1 of `docs/design/26_approach_review.md`,
which `docs/design/29_one_reader_plan.md` leaves as "a plan of its own after the measure"; this table is that measure):

1. **The step carries what its handler needs.** Most fields exist (`target`, `destination`, `ware`, `item`, `count`, `wait_until`,
   `wait_minutes`, `checks`). The measure says which few are missing: where a sleep is taken (`shelter`: camp, room or none, for
   `asks_camp` and `asks_room`), a clock hour for `wait_until`, the coin given as a number, the player's own material for a
   commission, and the words of the line the step stands for (R3's `words`). A handler that must match a name does it on the step's
   words, never on the whole line. The grammar keeps the answer closed; the 60 second turn is not touched (no new call).
2. **`on_<kind>(step)` loses its `text` parameter**, kind by kind. `tools/line_census.py` already counts the places per file; the
   ratchet of `tools/sim/line_patterns_648_test.py` then has a floor to reach: no place behind an `on_<kind>` door.
3. **One module for what stays a pattern** (the eight shared readers above), each with its table of lines in `data/replay` and one
   test: who is spoken to, an answer to the game's own question, a named thing of the engine's list, a number, a question, a denial,
   the game's marks. `engine/addressing.py` and `engine/questions.py` are two of them already; the other 100 or so functions call
   them instead of holding a copy.
4. **An intercept is an offer, not a taking.** The engine's test of state stays (a foe has yielded, a hire spoke last, the mentor
   is here); what the line means is the reader's, with the special act among its candidates. The rest of a line an intercept
   answers goes on to the reader. `hire_followup` is the first to go: it is the reader wrong most often.
5. **The measure stays as a tool.** The replay of logged lines through the bench (`bench_run.py` here, 61 seconds for 1,888 lines,
   no model) prints, per repair and per intercept, how often it fired and on which lines. Kept beside `tools/interp_eval.py`, it says
   before and after each step whether the count of changed readings fell, which is the owner's condition of 2026-11-17 ("kept
   only if the measure improves"), and it feeds the corpus with lines that were typed: the corpus has no case for the repair that
   fires most after the two big ones.

This keeps to the owner's rules: the engine still decides every number and state change (it stops deciding them from a substring);
nothing is added to a narrator prompt; no repair is written for a misread line (the decision of 2026-11-17); the model, its
settings and the turn budget are as they are. One thing pulls against a rule as written: point 1 adds fields to the interpreter's
answer, and R3's `words` makes the answer longer, which `docs/design/29_one_reader_plan.md` already prices.

## 6. Not measured

- The fight's readers (`scenes/combat_scene.py`, 24 places): the logged fight lines are three templates.
- The camp, the mentor's first stepping in, the yielded foe's answer on today's code: the bench cannot stage them.
- `deal_then_word` (70 firings), `audit_fix` (16), `settle_targets` (5): fired, not read line by line.
- What a human types. Every line here is the night bot's: full sentences, almost no bare commands, no typos, no "bye".
