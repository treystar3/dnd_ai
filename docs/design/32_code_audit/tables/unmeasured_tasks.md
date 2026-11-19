# Unmeasured tasks: the per-task table (audit round 2, part `unmeasured-tasks`)

All sizes are of the real request, built by the game's own code under simlib's stub on the CPU (no model was called).
Scripts and raw rows: `scratchpad/audit/work/unmeasured/` (`m_newgame.py`, `m_lesson.py`, `m_rest.py`, `m_rest2.py`, `c_price.py`, `c_fields.py`; rows in `*.json`).

- **system / user**: characters of the two messages. **grammar**: characters of `llm/gbnf.py grammar(schema)` for the contract sent.
- **ceiling**: `max_tokens` on the call. **budget**: `answer_tokens` in `data/rules/budget.yaml` (the size the 60 s budget charges).
- **rows**: calls of this task in the 44 tracked records (`docs/measure/**/llm_calls.jsonl.gz`, 14,035 calls) + the played session (154 calls).
- Price rates: `data/measured/card_profile.yaml`, RTX 3060 12 GB: 756.8 tokens/s read, 31.7 tokens/s written; 4 characters a token (`budget.yaml`).
- Answer sizes are never from this audit: they are the budget's figure, or a recorded median where one exists.

## Character creation

| task (contract) | asked at | system | user | grammar | ceiling | budget | rows | when the model fails | fields never read / ids left free |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| goddess_line (GoddessLine), creation | scenes/goddess.py:372 `speak` | 4,256 | 875 to 1,443 | 226 | 800 | 150 | 0 | an authored stand-in line for the step (`failures.creation_stand_in`) | none |
| goddess_line, at a death | scenes/world.py:304 | 4,009 | 199 (+ up to 4 earlier lines) | 226 | 800 | 150 | 0 | `failures.goddess_silent` | none |
| interpret_creation_input (PlayerTurn), typed creation only | scenes/goddess.py `interpret` | 1,038 | 89 to 1,334 | 2,073 | 300 | 100 | 0 | not re-traced in this pass | the window's pages make no such call |
| classify_concept (AskedInterpretation) | character/creation.py `interpret_concept` | 5,629 | 241 | 2,527 | 800 | 300 | 0 | no engine fallback: she asks for the concept again (goddess.py:453) | `families` is `list[str]`, sent back if not in FAMILIES (contracts.py:68) |
| generate_actives (SlotNames) | character/creation.py:56 | 3,164 | 5,544 to 6,115 | 1,329 | 2,600 | 2,000 | 0 | strict x3, lenient x2, then "say yes again" (goddess.py:479) | none; a wording fault re-asks all 15 |
| generate_actives, the old one-call flow (ActiveSet) | character/creation.py:83 | 6,283 | 2,662 | 10,846 | 3,600 | 2,000 | 0 | reached only on ValueError/KeyError: 0 of 440 plans | the model chooses every mechanic |
| generate_passive_mechanics (MechanicSet), background lane | character/creation.py `generate_passives` | 1,905 | 2,359 to 2,709 | 961 | 2,600 | 1,800 | 44 + 1 (median 1,050 read, 926 written, max 982, 0 failed) | no engine fallback | `option_id` free string, count fixed by the validator not the grammar |
| starting_kit (StartingKit), weapon | character/kit.py `choose_weapon` | 1,889 | 416 to 559 | 526 | 200 | 60 | 0 | the engine's own rule picks (highest fitting attribute) | `weapon`, `companion` free strings checked after |
| starting_kit, companion (companion classes, at waking) | character/kit.py:109 | 1,889 | 2,951 | 526 | 200 | 60 | 0 | none: the game stops at the first waking (first round, people-8) | same |
| lesson_want (LessonWant) | scenes/lesson_ask.py:11 | 884 | 111 | 775 | 120 | 60 | 0 | word lists (`lessons.from_words`) | `effect`, `stat` free strings, dropped silently when unknown (lessons.py:73) |
| generate_lessons (LessonNames), 3 slots | scenes/lesson_ask.py:23 | 1,581 | 2,166 | 1,327 | 1,400 | 900 | 0 | strict, lenient, then the trainer "can't settle" (training_actions.py:152) | none |

## Maren's lesson

| task (contract) | asked at | system | user | grammar | ceiling | budget | rows | when the model fails | fields never read / ids left free |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| mentor_speech (MentorSpeech) | scenes/mentor_actions.py:124 | 6,282 | 2,557 to 5,364 | 307 | 2,048 | 400 | 0 | mentor_say: mentor_speech again, then mentor_voice, then the written lines | none |
| mentor_chat (MentorReply) | scenes/mentor_actions.py `mentor_talk` | 6,246 | 6,436 to 7,630 | 465 | 2,048 | 150 | 0 | a written line | none (`moves_on` is read at 550, 561) |
| mentor_voice (MentorLines) | scenes/mentor_actions.py:141 | 2,848 | 1,005 to 2,606 | 358 | 2,048 | 200 | 0 | the lines as written | none |
| stranger_read (StrangerRead) | scenes/mentor_actions.py `mentor_read` | 598 | 147 | 247 | 60 | 20 | 0 | a word pattern | none |

## The world's other tasks

| task (contract) | asked at | system | user | grammar | ceiling | budget | rows | when the model fails | fields never read / ids left free |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| act_ruling (per-scene shape of ActRuling) | engine/act.py `ask` | 3,406 | 2,899 (9 targets) to 3,528 (17) | 28,895 to 42,742 (335 rules) | 700 | 260 | 0 + 1 (1,695 read, 217 written, 2.59 s) | the act waits, never rolled unruled | every field read; targets already an enum |
| arc_story (ArcStory) | scenes/arc_actions.py:171 | 1,752 | 3,251 (2,641 of it every person's name) | 2,026 | 1,800 | 1,200 | 0 | `plain_story` (first round scenes1-3: divides by zero after 16 names); deferred by the budget | node `id` free string, must be copied back in order |
| camp_intent (CampIntent) | scenes/camp_actions.py:246 | 1,674 | 320 | 823 | 150 | 60 | 0 | `keyword_intent` | `summary` never read |
| event_judge (JudgeVerdict), 7 parts | engine/situation_parts.py:1383 | 2,429 | 841 | 2,769 | 900 | 350 | 0 | the ruling waits or is dropped | `verdict`, `reason`, `ending` never read (first round llm-rest-9) |
| pulse_cataclysm (CataclysmProposal) | engine/events.py:1062 | 2,789 | 554 | 3,608 | 2,400 | 1,500 | 0 | no cataclysm this time | path `id` free string, a wrong one is silently lost (events.py:1097) |
| pulse_thread (ThreadProposal), normal | engine/pulse.py:383 | 4,741 | 7,234 (PLACES 3,112, ROADS 1,919) | 9,600 | 1,800 | 1,200 | 0 | the engine builds the situation where the tier allows, else none | not traced field by field |
| pulse_thread, rare and campaign | engine/pulse.py:383 | 6,568 | 9,898 to 9,995 | 9,600 | 2,400 | 1,200 | 0 | same | same |
| named_spell (SpellRankName) | scenes/spell_actions.py:180 | 521 | 85 | 314 | 200 | 80 | 0 | "The <Element> <form>" | none |
| spell_rank (SpellRankName) | scenes/spell_actions.py:68 | 783 | 239 | 314 | 200 | 80 | 0 | empty name and description handed to `spells.learn` | none |
| pair_dynamic (PairDynamic) | scenes/banter_actions.py:839 | 1,083 | 1,633 | 814 | 160 | 100 | 0 | the pair keeps its old line (first round scenes1-16) | none |
| clarify (Clarify) | scenes/audit_actions.py:196 | 524 | 295 | 343 | 120 | 60 | 22 (median 278 read, 34 written, 4 failed) | a plain note | `speaker` free string; unknown falls to the narrator |
| discovery (DiscoveryProposal) | scenes/explore_actions.py:119 | 1,644 | 6,293 (4,709 of it every place and road name) | 1,210 | 700 | 300 | 4 (all 4 failed: first round llm-checks-6) | nothing is found | `place_type`, `to`, `residents` free strings checked after |

## From New Game to the first line the player may type

Window (the creation pages), a class with no companion: **10 model calls**. A companion class: 11 (a second starting_kit at waking). Typed creation (terminal): 18 (7 interpret_creation_input and one more goddess_line).

| step | calls | read (chars) | read (s) | written (tokens, budget) | written (s) | note |
|---|---|---:|---:|---:|---:|---|
| name given | goddess_line | 5,392 | 1.8 | 150 | 4.7 | |
| calling given | classify_concept, goddess_line | 11,569 | 3.8 | 450 | 14.2 | |
| reading confirmed | generate_actives, goddess_line | about 14,500 | 4.8 | 2,150 | 67.8 | one foreground wait; ceiling 2,600 = 82 s |
| three abilities picked | generate_passive_mechanics (background, started at the step before), goddess_line, starting_kit, goddess_line | 17,082 | 5.6 | 2,160 (1,286 with the measured 926) | 68.1 (40.6) | |
| waking | narrate | 6,798 | 2.2 | 260 (155 measured median) | 8.2 (4.9) | start place south_fields: no residents call |
| **total** | **10** | **about 55,350 = 13,840 tokens** | **18.3** | **5,170 (4,191)** | **163 (132)** | **150 to 181 s of model time** |

Nothing here is prefix-cached in the sum: the first round (llm2-1, llm-flow-1) found the shared slot re-reads nearly every prompt.
Creation is outside the turn budget by `budget.yaml:96` ("before any turn, never budgeted").

## Maren's lesson, line by line (13 typed lines, to the wolves' appearance)

39 first-try calls; 318,040 chars = 79,510 tokens read (105 s); written 11,240 tokens by the budget's sizes (355 s), 7,245 with recorded medians where they exist (229 s).

| line | calls | read (s) | written (s, budget) | written (s, medians where recorded) | total (s) |
|---|---|---:|---:|---:|---:|
| 1 looks around (she approaches) | narrate, mentor_voice, dialogue_frame | 6.5 | 18.3 | 12.9 | 19 to 25 |
| 2 answers her | mentor_speech | 3.2 | 12.6 | 12.6 | 16 |
| 3 says where the sword came from | stranger_read, mentor_speech, dialogue_frame | 6.6 | 17.0 | 14.9 | 22 to 24 |
| 4 does not know the guild | mentor_speech | 3.5 | 12.6 | 12.6 | 16 |
| 5 asks a question | mentor_chat, mentor_speech | 7.9 | 17.4 | 17.4 | 25 |
| 6 "go on" (the walk to the hall) | mentor_voice, populate_place, moment x2, npc_profile, mentor_speech, narrate | 13.0 | 99.7 | 52.9 | 66 to 113 (the five required: 45 to 97) |
| 8 signs the register | interpret_action, narrate, mentor_speech, dialogue_frame | 14.4 | 28.4 | 20.7 | 35 to 43 |
| 9 takes the hunt | interpret_action x2, audit_meaning, audit_compare, mentor_speech, dialogue_frame, narrate | 19.1 | 36.0 | 23.9 | 43 to 55 |
| 11 a quoted question | mentor_chat | 4.2 | 4.7 | 4.7 | 9 |
| 12 walks to the Greywood | narrate, mentor_speech, dialogue_frame | 7.8 | 24.6 | 19.2 | 27 to 32 |
| 13 searches for tracks | interpret_action, mentor_voice, mentor_speech | 9.5 | 22.7 | 20.4 | 30 to 32 |

Not built: the fight with the wolves, the skinning, the troll, the return to the hall (the rest of the lesson).
