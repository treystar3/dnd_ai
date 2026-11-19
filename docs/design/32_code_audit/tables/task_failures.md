# Task failures: what the player sees, and what is lost, when one model task fails

Second round of the audit, finder `task-failures`. CPU only, simlib's stub as the model, no server started.

## How it was measured

- Harness: `scratchpad/audit/work/task_failures/tf_harness.py <scenario> <task> <mode>`. One process per cell. A layer on the
  model interface (`backend.wrap`, rank 15, inside the recorder) fails every call of ONE task title in ONE way:
  - `refused`: the answer comes back and its check refuses it on every try ("not json at all", finish stop);
  - `cut`: the answer is cut off (`{"x": "o`, finish length);
  - `too_big`: `Failure("too_big")`, the request is too big for the context;
  - `gone`: `Failure("unreachable")`, the server is gone;
  - `embed_gone` (run apart): every embed request raises `Failure("server")`.
- Read back for every input in which the failing task was asked: the recorder's page (`shown_text`), the per-table state digests
  against the baseline run, the turn log's row (stood, rolled_back, stand_in, world_failed, the operations), and a read-only probe
  after each input (coin, reputation, party details, waiting acts, the pending question).
- Baselines equal the kept recordings input for input (party 15 of 15, short 41 of 41, fight 20 of 20 state digests).
- Scenarios: the three golden scripts (`stub_short` 40 inputs, `stub_party` 14, `stub_fight` up to 80: 27 tasks), and two short
  ones written for this audit (`death`: a fight lost, the goddess, waking; `mentor`: Maren's meeting as typed lines, the walk to the
  guild hall, two questions to her). 228 cells run (57 task and scenario pairs by four ways), plus five baselines and three
  embedder runs.
- No cell stopped the game and none left a crash in the crash log. The only stop known is the first round's people-8 (starting_kit).

### The four ways of failing

Above the gateway only two things are read off a model failure: whether the turn's budget refused it, and whether the words were
someone's to speak. So the four ways gave the same outcome in 55 of 57 pairs. Where they differ:

| | refused | cut | too big | gone |
|---|---|---|---|---|
| tries of the failing call | 2, then the relaxed last pass (3 answers written) | 2, then the relaxed pass | 1 | 1 |
| charged to the line's 60 s budget | yes | yes | no (free) | no (free) |
| refusal kind filed | bad_answer | bad_answer | request_refused | model_down |
| seen difference (2 pairs) | mentor input 6: mentor_speech refused or cut used up the line's budget and the line's own passage was stood in **without being asked** (no narrate call made); short input 21: one more passage stood in. With too big or gone both passages were written | same | | |

### What each mark means

| mark | meaning | counts as |
|---|---|---|
| BACK | the line is rolled back and the player is told (a `turn_not_taken` line) | told, state whole |
| STAND | a stand-in line is shown and the state is whole | told, state whole |
| FALL | a written or engine fallback takes the call's place on the page; the game goes on, the state is whole | told, state whole |
| QUIET | a step of the world is put off or done by the engine; nothing the player needs telling | whole |
| ASK | the line is not done and the player is asked to say it another way | **told wrongly** |
| WRONG | a stand-in line is shown that says what did not happen, or leaves out what did | **finding** |
| LOST | the page stands, but something the save should hold is not kept, and is never asked for again | **finding** |
| PAID | state changed for a deed the game has not decided | **finding** |
| STOPS / NOTHING / HALF | the game stops / nothing shown / state half changed | none seen in a run |

## The table: tasks reached in a run

Each row is one task at one call site. "n" is the number of inputs in which the cell was seen, per way of failing.

| # | task | asked from (operation) | scenario | refused | cut | too big | gone | n | what the player read | what is lost | finding |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | interpret_action | scenes/world.py interpret:3278 (the understanding, no operation) | short, party, fight | BACK | BACK | BACK | BACK | 125 | "Nothing happens. Try that again." (one of eight, never the last) | nothing | |
| 2 | audit_meaning | scenes/audit_actions.py meaning:79 via intent_audit.audit:262 | party, short | ASK | ASK | ASK | ASK | 2 | "I'm not sure what you meant. Could you say it another way?" (or the clarify task's question) | the line, read rightly, is not done; a pending question is kept; the turn log says stood all | task-failures-7 |
| 3 | audit_compare | scenes/audit_actions.py compare:83 via intent_audit.audit:263 | party, short | ASK | ASK | ASK | ASK | 2 | as row 2 | as row 2 | task-failures-7 |
| 4 | clarify | scenes/audit_actions.py ask_back:196 | death | FALL | FALL | FALL | FALL | 3 | the written note "I'm not sure what you meant. Could you say it another way?" | nothing | |
| 5 | combat_interpret | scenes/combat_scene.py interpret:439 (asked: line) | short, fight | BACK | BACK | BACK | BACK | 106 | a not-taken line | nothing (the round is not played) | |
| 6 | combat_opening | scenes/world.py tell:438 (asked: opening) | short, fight | STAND | STAND | STAND | STAND | 4 | "Here they come: bandit captain, one alone." / "It's a fight now. swarm of ravens, one alone, and close." | the opening passage | wording: task-failures-8 |
| 7 | combat_narrate | scenes/combat_scene.py narrate_round_now:836 (asked: round) | short, fight, death | WRONG | WRONG | WRONG | WRONG | 29 | "The round is over." and no figures at all; "You trade blows, and the round ends." on a round the player ran; "The round is over. You have died." | every blow and figure of the round | task-failures-2 |
| 8 | combat_aftermath | scenes/combat_scene.py aftermath_now:1232 (asked: aftermath) | fight | STAND | STAND | STAND | STAND | 1 | "That's the last of them. 4314 experience." then the ledger's "Victory. +4314 XP, ..." | the aftermath passage | wording: task-failures-8 |
| 9 | loot_name | scenes/combat_scene.py ask_name:1380 (asked: naming) | fight | FALL | FALL | FALL | FALL | 1 | "Found: Rare sabatons (rare) ..." (the engine's name) | the given name | |
| 10 | legendary_name | scenes/combat_scene.py ask_name:1365 (asked: naming) | fight | FALL | FALL | FALL | FALL | 1 | the same page; the engine's name and story stand | the model's name | |
| 11 | accessory_name | scenes/combat_scene.py ask_accessory_name:1337 (asked: naming) | fight | FALL | FALL | FALL | FALL | 1 | the same page | the model's name | |
| 12 | narrate, a line's passage | scenes/world.py _narrate_now:3081 (passage) | all five | WRONG | WRONG | WRONG | WRONG | 28 | a buy: "You settle up with the herbalist: 0G 1S 50C." (true). Everything else one of six `stood_any` lines: "Theft: failure" then "No trouble. It's done."; "Attempt: partial" then "You get it done."; "You come in at the wrong moment and come away bruised." then "You finish what you set out to do."; an arrival in a new town: "You manage it." | the passage; where a move ended; how an attempt went | task-failures-1 |
| 13 | narrate, the opening | scenes/world.py opening_passage:3007 | all five | STAND | STAND | STAND | STAND | 5 | "You get your bearings." / "You stand up." / "You take a breath and look around." | the opening passage | |
| 14 | narrate, a creature sighted | scenes/world.py narrate_with:411 from maybe_encounter:494 (inside action:search) | short, fight | BACK | BACK | BACK | BACK | 83 | a not-taken line, every time: 80 searches in a row in the fight script | the search; the same words draw the same sighting again, so it cannot pass while the narrator fails | task-failures-6 |
| 15 | narrate, Maren's look | scenes/mentor_actions.py mentor_look:179 (line) | mentor | FALL | FALL | FALL | FALL | 1 | her written description | nothing | |
| 16 | goddess_line | scenes/world.py goddess_now:304 (asked: goddess) | death | STAND | STAND | STAND | STAND | 1 | "Oh, child. Come here, out of the cold. You are not finished yet." shown as narration, with no speaker | her own words; the death stands | wording: task-failures-8 |
| 17 | populate_place, a walk | npc/life.py populate_place:188 from world.enter:817 (action:move, or Maren's line) | short, mentor | BACK | BACK | BACK | BACK | 37 | a not-taken line (33 of 40 inputs in short) | the walk | first round: world_py-4 |
| 18 | populate_place, the opening and each input's edge | world.enter:817 from run:1000; repopulate:847 from run:1063 | mentor | QUIET | QUIET | QUIET | QUIET | 9 | the same page | the place stays unpeopled and is asked again at every input's edge (pinned: goes_on_525_test) | |
| 19 | npc_profile | npc/life.py promote:241 from on_talk:3704 and mentor_clerk_exchange:199 | party, short, mentor | BACK | BACK | BACK | BACK | 12 | a not-taken line | the talk is not had | |
| 20 | npc_conversation | npc/life.py converse:439 (asked: action:talk) | party, short | BACK | BACK | BACK | BACK | 9 | a not-taken line (the list reply_not_come is still empty, the owner's to write) | nothing | |
| 21 | dialogue_frame | scenes/voice.py fresh:108 from narrate_dialogue:3969, companion_show:721, exchange_frame:177, mentor_show:68 | short, party, fight, mentor | FALL | FALL | FALL | FALL | 9 | the spoken line with the person's plain manner ("doesn't hurry") or none | the frame | |
| 22 | npc_parting | engine/partings.py line:102 | short | FALL | FALL | FALL | FALL | 1 | "the farmer: Good day to you." | nothing | |
| 23 | hire_chat | scenes/party_actions.py hire_talk:791; scenes/quirk_actions.py companion_line:287 | party, fight | WRONG | WRONG | WRONG | WRONG | 5 | asked where he learned to fight: "Does this come out of my fee?", and again the next time | their answer; the quip is kept as what they said | task-failures-5 |
| 24 | canon_extract | engine/canon.py extract:564 from read:658 (hire_talk:806) and read_exchange_claims:776 | party, fight | LOST | LOST | LOST | LOST | 3 | the same page: "In a town militia up north... that much I promise." | what they said of themselves and the promise are not kept, and the line is never read again | task-failures-4 |
| 25 | persona_details | scenes/quirk_actions.py persona_details:75 | party, fight | LOST | LOST | LOST | LOST | 2 | the same page | all three hires end with 0 details and 0 secrets (baseline 5 and 2 each); never asked again | task-failures-4 |
| 26 | overheard | engine/party_director.py read_words:101 | party | FALL | FALL | FALL | FALL | 2 | no one joins in | nothing | |
| 27 | exchange | scenes/banter_actions.py exchange:112 | party, fight | FALL | FALL | FALL | FALL | 3 | the exchange is not had | nothing | |
| 28 | party_intent | scenes/party_actions.py party_read:87 | party | FALL | FALL | FALL | FALL | 2 | the same page (read by its words) | nothing | |
| 29 | plausible_object | scenes/law_actions.py judge_object:105 (action:steal) | party | FALL | FALL | FALL | FALL | 1 | the same page | nothing | |
| 30 | act_ruling | engine/act.py ask:196 from act:590 (asked: action:other) and take_up:705 | short | PAID | PAID | PAID | PAID | 2 | the attempt beginning is told, then "You're paid for your trouble, and word of your help gets around." | the act waits unruled, yet coin 800 to 876 and Parth +2 are paid; two inputs later the act lapses as "came to nothing" and the pay stands | task-failures-3 |
| 31 | road_event | scenes/road_actions.py road_event:362 (action:move) | short | FALL | FALL | FALL | FALL | 1 | the walk goes on with no event | the event rolled | |
| 32 | thread_telling | engine/threads.py tell:532 (arrival) | short | FALL | FALL | FALL | FALL | 1 | the same page | the engine's own words stand; tried again at the next arrival | |
| 33 | situation_parts | engine/situations.py propose:585 (asked: parts, a world operation) | short | QUIET | QUIET | QUIET | QUIET | 6 | the same page | one of the birth's tries; past them the engine's own parts | |
| 34 | moment | engine/moments.py compose:142 (line) | mentor | FALL | FALL | FALL | FALL | 1 | a written moment | nothing | |
| 35 | stranger_read | scenes/mentor_actions.py mentor_read:505 | mentor | FALL | FALL | FALL | FALL | 1 | the same page (read by its words) | nothing | |
| 36 | mentor_speech | scenes/mentor_actions.py mentor_speak:124 | mentor | FALL | FALL | FALL | FALL | 5 | mentor_voice's lines, then her written ones | refused or cut: the tries used the budget and the line's passage was stood in unasked ("You finish what you set out to do.") | see the four ways |
| 37 | mentor_voice | scenes/mentor_actions.py mentor_voice:141 | mentor | FALL | FALL | FALL | FALL | 2 | her written lines, the same page | nothing | |
| 38 | mentor_chat | scenes/mentor_actions.py mentor_talk:289 | mentor | FALL | FALL | FALL | FALL | 2 | "Hm. Give me a second with that one. Ask me again." (the same line both times) | nothing | |

### The embedder gone

| scenario | embed calls, baseline | embed calls, embedder gone | what the player read | what is lost |
|---|---|---|---|---|
| party | 41 | 1 (the first fails; embeddings are off for the rest of the session) | the same pages but one gesture ("doesn't hurry" not shown) | nothing told and nothing to tell; every caller takes its word fallback, so which memories a hire is given differ |
| short, fight | 0 | 0 | the same | these scripts have no embedder |

Known from the first round: one failed embed call turns the embedder off for the session with no way back (llm2-4, trace-threads-3).

## Tasks not reached in a run: by reading

| task | call site | on a model failure (by reading) | mark |
|---|---|---|---|
| starting_kit | character/kit.py:109 | the error reaches main.guarded and the game stops (first round: people-8) | STOPS |
| classify_concept, generate_actives, generate_passive_mechanics, interpret_creation_input | scenes/creation | the goddess's `creation_fail` line and the step asked again; tools/sim/goes_on_525_test.py run once here: ALL PASS | STAND |
| camp_intent | scenes/camp_actions.py camp_read | read by its words | FALL |
| lesson_want | scenes/lesson_ask.py | read by its words | FALL |
| generate_lessons | scenes/training_actions.py:151 | "The instructor can't settle on what to teach you right now. Ask again in a moment." | told (a refusal), whole |
| work_offer_read | scenes/work_actions.py inferred_offer | no offer inferred | FALL |
| canon_check | engine/canon.py judge | the claim kept as unverified | FALL |
| ruling | engine/ruling.py:148 (a road hazard) | no ruling: pressing on is the act's own | FALL |
| classify_field | engine/field.py:95 | words | FALL |
| discovery | scenes/explore_actions.py:119 | no discovery | FALL |
| pair_dynamic | scenes/banter_actions.py:839 | the pair's old line stands, and is marked fresh (first round: scenes1-16) | FALL |
| arc_story | scenes/arc_actions.py:171 | the plain story; dressed later only when the budget deferred it, never after a model failure | LOST (task-failures-4) |
| event_judge | engine/situation_parts.py:1383 | the deed waits for a later turn | QUIET |
| situation_agree | engine/situations.py:201 | "unverified" | FALL |
| pulse_thread, pulse_cataclysm | engine/pulse.py:382, engine/events.py | the engine's own build; a cataclysm's spawns removed | QUIET |
| board_stakes | engine/stakes.py:93 | plain postings (the `guild` script here reached the board, but no posting asked for stakes) | FALL |
| named_spell, spell_rank | scenes/spell_actions.py | the plain name | FALL |
| pulse_motive, npc_decide | | never asked in play as shipped (first round: dead-switches-8, dead-switches-17) | |

## The stand-in lines, read

404 lines read (all of data/rules/failures.yaml, the eight companion quips, the two clarify notes, ATTEMPT_ONLY, Maren's fallback, the
instructor's refusal): **none carries a dash**, none a word of the machinery. Lines that read wrong where they are shown:

| list | line | where it read wrong | seen in a run |
|---|---|---|---|
| stood_any | "No trouble. It's done." / "You get it done." / "You manage it." | after a failed theft, a partial attempt, a hurt, a look, an arrival | yes (party 11, short 38, mentor 6 and 7, short 14 to 40) |
| round_stood | "You trade blows, and the round ends." | the player ran: "I run for it." then "You got away." | yes (fight 18) |
| round_stood | "A round passes, and the fight goes on." / "The fighting goes on. Another round done." | drawn at random also for the round that ends the fight | by reading (the round that killed the player drew "The round is over.") |
| fight_begun | "Weapons out. {foe}, {count}." / "No time to think. {foe}, {count}, coming at you." / "It's a fight now. {foe}, {count}, and close." | {foe} is the creature's name in lower case and opens a sentence | yes (fight 17: "It's a fight now. swarm of ravens, one alone, and close.") |
| fight_begun | "Here they come: ..." / "... coming at you." | the player struck first, from hiding | yes (fight 2: "I creep up on Marrow Hask and strike." then "Here they come: bandit captain, one alone.") |
| fight_begun | {foe} | a named person is told by their kind (Marrow Hask as "bandit captain") | yes (fight 2) |
| victory_stood | "The last one goes down." / "That's the last of them." | the last foes yielded and were taken alive | yes (fight 15: three captives) |
| goddess_silent | all six | her speech is shown by console.narrate, with no speaker (the model's line is console.say(..., "The Goddess")) | yes (death 5) |
| party.yaml quip | "Of course." (dry) | said in answer to anything asked: it agrees to it | by reading; "Does this come out of my fee?" seen (party 1, 2) |

## Findings by shared cause

1. **A stand-in does not know how the deed ended** (rows 12, 7, and the lines above): task-failures-1 (the line's passage: only 8 of
   33 ledger rows carry the facts a stand-in is filled from, and no row carries how a roll went) and task-failures-2 (a fight round:
   the figures live only in the model's passage).
2. **A model failure of a once-only writing is never asked again** (rows 24, 25, arc_story): task-failures-4. The queue for it exists
   (defer, run_deferred) and takes only the budget's deferrals.
3. **A step that only waits is counted as done** (row 30): task-failures-3.
4. **A telling asked inline, not as a passage** (row 14): task-failures-6, the third site of the first round's world_py-1 and world_py-3.
5. **One kind of failure, two rules for who speaks** (rows 20 and 23): a townsperson's failed reply takes the line back; a companion's
   says a fixed quip and keeps it: task-failures-5.
6. **A failed check of the reading is told as the player's unclear words** (rows 2, 3): task-failures-7.
7. **Wording of the lists**: task-failures-8.
8. **No test fails each task in turn through a played session**: task-failures-9.

Work files: `scratchpad/audit/work/task_failures/` (tf_harness.py, scenarios.py, scenarios_more.py, run_matrix.py, analyze.py,
summary.py, show.py, page.py, probe.py, diff_runs.py, ledger_facts.py, dash_check.py; `runs/` holds every cell's recording,
turn rows, probes and result; `cells_<scenario>.json` and `summary.txt` hold the readings).
