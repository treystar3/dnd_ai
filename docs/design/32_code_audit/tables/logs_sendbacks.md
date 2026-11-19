# Why the game sends the model's answers back (logs-sendbacks)

Counted over every tracked `llm_calls.jsonl.gz` under docs/measure (prose_baseline, prose_a1, prose_a2): 44 play logs,
14,035 model calls, all Gemma 4 12B, recorded 2026-11-10/11 on a rented RTX 5090.

How to read the seconds: they are the 5090's. It writes 125 to 166 tokens a second in these logs; the minimum card writes about
31.5. A second try that took 2.1 s here is about 8 to 10 s on the minimum card. Shares (percent of model time) carry over; seconds
do not.

How to read "today": the record is about 130 features old, so each large group's logged raw answers were run through today's code
(guard.foreign, guard.check, hygiene.problem in the gateway's order; the Exchange and DialogueFrame contracts; opener_of). Checks
that compare by meaning (banter.repeats, retells) need the helper model and were not run; the phantom check (f701) and the stiff
speech check (f714) are newer than the record and do not appear in it.

A "request" is one call with its retries. "Lost" on a row is the time of the try that was sent back; "next" is the time of the try
that followed it. "Requests lost" failed every try (the player got a stand-in line or nothing).

Scripts and their outputs: scratchpad/audit/work/logs_sendbacks/ (load.py, groups.py, tally2.py, replay_gate.py, ids.py, broken.py,
script.py, amount.py, amount_today.py, frame_btw.py, cutoff.py, failed.py, by_arm.py, again.py, rewrites*.py, small_groups.py,
speakers_today.py, last_checks*.py, lost_exchange.py).

## 1. Totals

| | tries | with an error | requests | requests lost | model seconds | second and third tries | fresh() rewrites | written again in all |
|---|---|---|---|---|---|---|---|---|
| Everything | 14,035 | 1,089 | 13,012 | 66 | 21,496 | 999 s (4.6%) | 346 s | 1,345 s (6.3%) |
| The game's tasks | 11,276 | 556 | 10,761 | 41 | 20,205 | 744 s (3.7%) | 346 s (1.7%) | 1,090 s (5.4%) |
| The night bot's own lines (player_line) | 2,759 | 533 | 2,251 | 25 | 1,291 | 255 s (19.7%) | 0 | 255 s (19.7%) |
| Game tasks, default sampling (base1, base2, new1, new2, prose_a2, control) | 6,151 | 249 | | | 12,575 | 366 s (2.9%) | | |
| Game tasks, the four trial arms (dry, xtc, both, min_p; none kept) | 5,125 | 307 | | | 7,626 | 373 s (4.9%) | | |

The tries that were thrown away (the sent-back tries themselves) took 1,157 s of the game's 20,205 s (5.7%).
Chain lengths: 12,043 requests took one try, 916 two, 52 three, 1 four.

## 2. By task

| task | requests | tries | tries with an error | requests sent back | requests lost | seconds | second and third tries | share | fresh() rewrites |
|---|---|---|---|---|---|---|---|---|---|
| populate_place | 263 | 263 | 0 | 0 | 0 | 6,345 | 0 | 0% | |
| narrate | 1,472 (185 of them rewrites) | 1,647 | 190 | 147 | 15 | 3,328 | 309 s | 9.3% | 346 s (10.4%): 19.7% written again |
| npc_conversation | 701 | 746 | 47 | 38 | 2 | 2,200 | 80 s | 3.6% (plus 138 s of runaway first tries) | |
| interpret_action | 2,477 | 2,481 | 4 | 4 | 0 | 2,185 | 4 s | 0.2% | |
| player_line (the bot) | 2,251 | 2,759 | 533 | 508 | 25 | 1,291 | 255 s | 19.7% | |
| dialogue_frame | 750 | 883 | 141 | 119 | 8 | 1,121 | 136 s | 12.1% | |
| combat_narrate | 340 | 394 | 57 | 50 | 3 | 917 | 100 s | 10.9% | |
| hire_chat | 555 | 594 | 39 | 39 | 0 | 673 | 37 s | 5.5% | |
| exchange | 382 | 414 | 39 | 31 | 7 | 577 | 38 s | 6.5% | |
| combat_aftermath | 258 | 258 | 0 | 0 | 0 | 477 | 0 | 0% | |
| combat_opening | 180 | 193 | 16 | 13 | 3 | 395 | 18 s | 4.6% | |
| audit_compare | 924 | 924 | 0 | 0 | 0 | 274 | 0 | 0% | |
| audit_meaning | 924 | 924 | 0 | 0 | 0 | 254 | 0 | 0% | |
| persona_details | 132 | 141 | 10 | 9 | 1 | 237 | 12 s | 5.1% | |
| generate_passive_mechanics | 44 | 44 | 0 | 0 | 0 | 206 | 0 | 0% | |
| combat_interpret | 291 | 291 | 0 | 0 | 0 | 182 | 0 | 0% | |
| road_event | 52 | 54 | 2 | 2 | 0 | 143 | 4 s | 2.8% | |
| overheard | 469 | 469 | 0 | 0 | 0 | 125 | 0 | 0% | |
| board_stakes | 60 | 60 | 0 | 0 | 0 | 123 | 0 | 0% | |
| npc_profile | 146 | 146 | 0 | 0 | 0 | 122 | 0 | 0% | |
| ruling | 95 | 95 | 0 | 0 | 0 | 88 | 0 | 0% | |
| moment | 35 | 36 | 1 | 1 | 0 | 76 | 1 s | 1.1% | |
| canon_extract | 127 | 127 | 0 | 0 | 0 | 63 | 0 | 0% | |
| thread_telling | 22 | 24 | 2 | 2 | 0 | 52 | 3 s | 5.6% | |
| situation_parts | 6 | 6 | 0 | 0 | 0 | 21 | 0 | 0% | |
| clarify | 18 | 22 | 4 | 4 | 0 | 8 | 1 s | 15.0% | |
| work_offer_read | 15 | 15 | 0 | 0 | 0 | 5 | 0 | 0% | |
| discovery | 2 | 4 | 4 | 2 | 2 | 4 | 2 s | 40.6% | |
| party_intent, situation_agree, plausible_object, canon_check | 21 | 21 | 0 | 0 | 0 | 5 | 0 | 0% | |

A request that was sent back cost on average 2.1 s more for narrate, 2.0 s for combat_narrate, 2.1 s for npc_conversation,
1.1 s for dialogue_frame, 1.2 s for exchange, 0.9 s for hire_chat (5090 seconds).

## 3. By reason, largest first (game tasks: 556 send-backs)

| reason (where it is checked) | n | by task | lost s | next s | second try taken | request lost | today's code | what the reading found | settled with no new call? |
|---|---|---|---|---|---|---|---|---|---|
| A word joined with an underscore (hygiene.problem 'id', engine/hygiene.py 103) | 171 | narrate 87, combat_narrate 39, dialogue_frame 34, combat_opening 5, exchange 4, hire_chat 2 | 338 | 253 | 90% | 4% | still sent back, 171 of 171 | all 171 read by shape: 0 is a game label (none of the joined words stands in the request). 82 are two lower-case words (half_hidden, shirt_the), 60 a word with a trailing underscore, 15 word_Capital, 6 Name_Name; in 46 to 52 the underscore stands where a full stop was lost (mud_The dragonborn). 46 answers carry two or more | yes: a rule. hygiene.clean() already turns the underscore into a space; it needs a full stop when a capital or the end follows |
| Dialogue frame shows them going back to work (llm/contracts.py 1297) | 71 | dialogue_frame | 101 | 72 | 88% | 4% | still sent back, 71 of 71 | 42 right, 14 borderline (turns back toward the hearth), 15 false alarms (21%): returns their gaze, frogsong resumes, turns back toward you, until you return | yes: drop the sentence of `after` that carries the hit (48 of 71 have one sentence; 34 of 62 retries came back with `after` empty anyway) |
| A word not in English (guard.foreign, llm/gateway.py 332) | 54 | narrate 37, dialogue_frame 9, combat_narrate 5, hire_chat 2, combat_opening 1 | 112 | 86 | 89% | 2% | still sent back, 54 of 54 | all 54 real: 51 are one foreign word, 31 of them the same Korean word for "his"; Hangul 34, CJK 7, Latin-letter list 8, Cyrillic 3, other 2 | at the source: a grammar character rule would make 46 of 54 impossible to write; the 8 Latin-letter words still need the check |
| "A character came out broken" (hygiene.problem 'broken', engine/hygiene.py 99) | 46 | narrate 38, combat_narrate 3, combat_opening 3, dialogue_frame 2 | 104 | 69 | 39% | 39% | still sent back, 46 of 46 | 43 of 46 are a carriage return before a line break (\r\n), which clean() already mends on the way to the screen; 1 a backspace from a bad escape, 2 other. The reason quotes an invisible character, so the retry repeats it | yes for 43: make \r\n a line break before the gate |
| Amount not in the material (engine/banter.py 165) | 24 | exchange | 35 | 23 | 65% | 35% | still sent back, 24 of 24 (with the game's material) | 3 right (forty-two twice, four since we left); 21 false alarms (88%): 16 are the hire's own oath "By the Nine Winds", which the engine offers in the same request; twice as hard, twice as heavy, half-asleep, half their lives, three sieges (the hire's own past), those two on the left | no call was due for 21 |
| A hire says again what they said (banter.repeats, llm/contracts.py 859) | 20 | hire_chat | 23 | 18 | 100% | 0% | by meaning: not run | 20 of 20 literal near repeats; 8 or 9 are replies of two to four words (I am ready.), which the townsperson's check lets be (five-word floor at 1014) | no (a real repeat) |
| First person in the narrator's prose (hygiene 'first_person') | 15 | narrate 7, combat_opening 4, combat_narrate 3, dialogue_frame 1 | 30 | 21 | 60% | 40% | 8 of 15 are taken today ("mine" as in a mine road, mended by f693); 7 still sent back | the 7 are right (my, I outside speech) | no |
| A literal backslash-n (hygiene 'escape', engine/hygiene.py 97) | 15 | narrate 13, combat_opening 2 | 33 | 26 | 92% | 0% | still sent back, 15 of 15 | all 15 are a line break written as two characters | yes: clean() (line 191) already mends it |
| A heading of the request echoed in a frame (llm/contracts.py 1302) | 13 | dialogue_frame | 21 | 10 | 57% | 43% | validator unchanged | 13 of 13 right (WHY THIS LINE GETS A FRAME, ALREADY SHOWN THIS VISIT); 9 of 13 rows ended in a lost frame | yes for 11: the prose before the heading is a good frame; cut the field there |
| A townsperson repeats themselves (llm/contracts.py 1017) | 11 | npc_conversation | 27 | 15 | 78% | 0% | by meaning: not run | 11 of 11 right | no |
| Cut off at the length limit, "went round in circles" (llm/gateway.py 301) | 9 | npc_conversation | 138 | 23 | 100% | 0% | journal_note still in the grammar with no limit | all 9 ran away inside journal_note after a finished speech (2,048 tokens: 8.5 to 29.3 s here, about 65 s on the minimum card); no narration or speech ever ran away | at the source: a grammar length limit on the side field |
| A bracketed note (hygiene 'note') | 9 | combat_narrate 5, narrate 3, npc_conversation 1 | 26 | 16 | 50% | 33% | still sent back, 9 of 9 | 8 right ([Blessing] three times, [BRUTAL STRIKE], [REACTION] twice, [half-elf], [_]); 1 is the request's own rank notation ("an [E] rank job") | a mend could drop a bare tag; clean() does not do it today |
| Underscore or asterisk in a townsperson's speech (llm/contracts.py 1058) | 7 | npc_conversation | 14 | 7 | 80% | 20% | still sent back | all 7 are underscore joins of the same kind as the first row (6 in the dry arm); 0 asterisks | yes: the same rule |
| Persona details name a person or place | 7 | persona_details | 12 | 9 | 100% | 0% | not run (first round llm-checks-14) | 7 of 7 right: invented festival names (Frost-Turning, Midwinter Frost, Frostfire Eve) | no |
| Frame opens on another person | 7 | dialogue_frame | 7 | 5 | 80% | 0% | validator unchanged | 7 right; 5 from the min_p arm | no |
| JSON in the prose (hygiene 'json') | 6 | narrate 4, combat_narrate 1, dialogue_frame 1 | 12 | 9 | 60% | 20% | still sent back | right; clean() clears 4 of the 6 (the other 2 carry "my" as well) | yes for 4 |
| A reply with a question from one who never asks (engine/voices.py 145) | 6 | npc_conversation | 16 | 13 | 50% | 0% | same test today ("?" anywhere) | 2 right; 4 are an echo of the player's own word (Trouble? Well, ... / Strange things? Hard for me to say) | no call was due for 4 |
| Opens on a stock word (engine/voices.py 147) and the same opener twice (llm/contracts.py 1040) | 10 | npc_conversation 4, hire_chat 6 | 16 | 11 | 100% | 0% | same today (opener_of run on the logged lines) | 5 right (Well, ... / Right then.); 5 are no filler: See you then. See that you do. Right as rain. Right behind you (twice) | no call was due for 5; cutting the opener would break them |
| Coined name (truth.check_speech) | 6 | npc_conversation 3, exchange 2, hire_chat 1 | 8 | 5 | | 1 lost | not run | mixed: Rimlands right; Fallaby twice; Have, Choice, Hunger are stray capitals in garbled lines | no |
| Hire did not tell what they decided to tell (retells) | 5 | hire_chat | 6 | 7 | 100% | 0% | by meaning: not run | 5 of 5 right | no |
| Understanding cut off at 700 tokens | 4 | interpret_action | 13 | 4 | 100% | 0% | summary still unlimited | 4 runaways inside `summary` (house house house ...) | at the source: a grammar length limit |
| Clarify line uses a "game word" (llm/contracts.py 506) | 4 | clarify | 1 | 1 | 100% | 0% | same list today | 4 of 4 false alarms: "announce your intent to the room", "another action you intended" | no call was due |
| A find with no name (llm/contracts.py 1944) | 4 | discovery | 4 | 2 | 0% | 100% | validator unchanged | both discoveries of the record were lost: the grammar lets name be empty, the retry repeats it | at the source: required in the grammar |
| A reply with no words | 4 | npc_conversation | 11 | 7 | 50% | 50% | unchanged | 4 right | no |
| Speaker borrows another's nickname, a building the town lacks, holding talk, line count, repeats, echo | 13 | exchange 9, hire_chat 4 | 17 | 13 | | 1 lost | not run | borrowed nickname 3 right; "no smithy here" twice on a figure of speech (A forge that has cooled loses its strength quickly) | no |
| Content guard, sexual (data/rules/guard.yaml 27) | 1 | combat_opening | 1 | 1 | 100% | 0% | still sent back (also "a naked blade", "a cock crows", "Dick the carter") | false alarm: "it cocks its head toward you" | no call was due |
| Other (invalid JSON 3, placeholder 1, frame repeats the words said 2, road 2, thread 2, moment 1, plain words 1, empty 1, details 3) | 16 | | | | | | | not read to twenty: fewer than five each | |

The night bot (player_line, 533 send-backs): 451 are an empty object (`{ }` 425, `{}` 26): `line` is optional in the grammar and
refused when empty (llm/contracts.py 595-601); 160 s lost and 226 s of next tries. 65 lack a name the goal turns on (39 of those
lines were lost), 13 first person, 4 a JSON tail.

## 4. The critic's first tally, checked

| claim | the record | verdict |
|---|---|---|
| dialogue_frame 141 of 883 sent back, 71 by the going-back-to-work check | 141 of 883; 71 | confirmed. 119 of 750 frames were sent back at least once, 8 lost |
| narrate 190 of 1,647 | 190 of 1,647 | confirmed |
| narrate: 37 a broken character | 38 | corrected by one; 43 of all 46 "broken" answers are a carriage return |
| narrate: 37 not English | 37 | confirmed (54 over all tasks) |
| narrate: 13 a backslash n | 13 | confirmed (15 over all tasks) |
| (not in the tally) | 87 underscore joins | the largest narrate reason was missing from the tally: 87 of 190 |
| exchange 39 of 414, 24 for an amount not in the material | 39 of 414; 24 | confirmed; 21 of the 24 are false alarms, 16 of them the engine's own oath "By the Nine Winds" |
| "twice as hard", "half-asleep" were sent back | yes (twice as hard, twice as heavy, half-asleep, half their lives) | confirmed |
| discovery 4 of 4 | 4 of 4 tries, 2 of 2 requests lost | confirmed |

## 5. Default sampling against the four trial arms (per 1,000 narrator tries)

| reason | default (1,801 narrator tries) | arms (1,574) |
|---|---|---|
| underscore join | 77 (42.8) | 94 (59.7) |
| going back to work | 33 (18.3) | 38 (24.1) |
| not English | 24 (13.3) | 30 (19.1) |
| broken character (carriage return) | 13 (7.2) | 33 (21.0) |
| backslash-n | 6 (3.3) | 9 (5.7) |
| first person | 3 (1.7) | 12 (7.6) |
| amount not in the material (exchange) | 20 | 4 |
| cut off in journal_note | 7 | 2 |

The junk is not an effect of the arms: every large reason is there under the default sampling, at two thirds or more of the arms'
rate, except the carriage return (a third).

## 6. Requests lost (every try sent back): 41 in the game's tasks, 196 s spent on them

| task | lost | the tries' reasons |
|---|---|---|
| narrate | 15 | carriage return three times 5; carriage return twice 2 (one then a backslash-n); underscore then carriage return twice 1; underscore three times 1; underscore twice then a foreign word 1; carriage return twice then a foreign word 1; with first person 2; JSON twice 1; note twice 1 |
| dialogue_frame | 8 | heading twice 3; back to work, heading, heading 1; back to work, back to work, underscore 1; back to work, carriage return twice 1; underscore, foreign word, underscore 1; underscore, opens on another, heading 1 |
| exchange | 7 | amount twice 5 (three of them "By the Nine Winds" both times); nickname then amount (twice as heavy) 1; amount (half their lives) then a coined place 1 |
| combat_narrate | 3 | foreign word twice then underscore 1; first person then carriage return twice 1; note twice 1 |
| combat_opening | 3 | "mine" twice 2 (mended since, f693); carriage return twice 1 |
| npc_conversation | 2 | no words three times 1; underscore three times 1 |
| discovery | 2 | no name twice 2 |
| persona_details | 1 | not five details twice 1 |

About 30 of the 41 were lost to a fault a mend in place would settle or to a false alarm (11 of the 15 narrations, all 8 frames,
6 of the 7 exchanges, 5 of the 6 fight passages).

How often the second try was taken, by the first reason: underscore 90%, back to work 88%, not English 89%, backslash-n 92%;
carriage return 39% (39% of those requests were lost), amount 65% (35% lost), heading 57% (43% lost), first person 60% (40% lost),
no name in a find 0%.

## 7. What needs no second call

Of the game's 556 send-backs:

| kind | count | next-try seconds |
|---|---|---|
| Mended by the cleaner the game already has, or by one rule: underscore 178, carriage return 43, backslash-n 15, JSON tail 4, placeholder 1 | 241 | about 356 |
| False alarms, no send-back due: amount 21, back to work 15, "mine" 8 (mended since), opener 5, question 4, clarify 4, figure of speech 2, content guard 1 | 60 | about 45 |
| Right catches a mend in place would still settle: back to work 56 (drop the sentence), heading 11 (cut at the heading), bare tags about 7 | about 74 | about 78 |
| Stopped at the source by the grammar: another script 46, runaway side field 13, a find with no name 4 | 63 | about 101, plus 151 s of runaway first tries |
| In all | about 438 of 556 (79%) | about 580 of the game's 744 retry seconds (78%) |

What is left (about 118) are real faults of content that need new words: repeats 33, first person 7, a hire not telling what was
decided 5, a frame opening on another person 7, invented names, a reply with no words.

## 8. fresh() rewrites (scenes/voice.py), which are not errors in the log

185 of 1,287 narrations (14.4%) were written a second time on fresh()'s own judgement: 206 calls with their retries, 388 s
(346 s for the first try of each rewrite), 10.4% of narrate's model time: more than all of narrate's send-backs (309 s). By reason
(a rewrite may have several): worn words 105, a stale phrase 82, invented speech 15. Of the 82 stale-phrase rewrites, 21 named a
stock phrase of the list; 34 a five-word run that carries an image (links of your chain shirt); 27 named nothing but five-word
runs of two content words or fewer (at the far end of, in the center of the, the rest of the crowd, there is no sign of, he does
not look up), 24 of them with no other reason: 45 s.

## 9. Checked and not supported

The frame request's own examples ("He has turned back to the nets", "goes back to sleep") do not explain the going-back-to-work
frames: 11.4% of frames with neither example in the request were sent back for it, 8.2% with both.

Today's speaker checks run over the 1,254 replies the record took (555 hire, 699 townsperson): no asterisk, no quotation mark in a
hire's speech, no remember over 30 words, no impression over 25 words, no underscore: nothing more would be sent back today for
those faults.
