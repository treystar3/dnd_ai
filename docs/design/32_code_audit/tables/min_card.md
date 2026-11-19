# The 60 second limit on the minimum card: what the code allows and what the records price at

Audit part `min-card`, second round, 18 November 2026. CPU only: no model was started, nothing in the repository was changed.

**Everything here is an estimate, not a measurement on a 3060.** It assumes:

- The minimum card reads 756.8 prompt tokens a second and writes 31.7 (data/measured/card_profile.yaml, dated 2026-11-01). That file is itself scaled from an RTX A4000 night (`scaled_from`; its model tag, gemma4:12b, is the older runtime's spelling, and the game now runs llama-server with two slots); no 3060 has been timed. The last section, `How far this leans on the two rates`, prices the same lines at the read rate the tracked runs themselves imply: the writing rate holds, the reading rate does not.
- A call costs (prompt tokens - cached tokens) / read rate + answer tokens / write rate, from the server's own counts in each log row (tokens.prompt, tokens.cached, tokens.out). The cache is taken as it behaved on the recording card; both rates are taken as flat whatever the prompt's length.
- Nothing else is priced: checkpoint copies, the wait for a slot, embedding calls, the engine's own time, a background call sharing the card. On the recording cards these were small (wait 1 s of 256 s in the played session); the budget keeps 5 s of margin for them.
- A line is every call the log files under one turn number, the bot's own `player_line` and background calls left out. In the played session this matches the turn log call for call (42 of 42 rows). In the 44 tracked runs a pane command sent between two lines is filed under the line before it, so `whole line` there can join two inputs; `to the last required call` is the safer column.
- The 44 tracked runs are 10 and 11 November code (about 130 features back) on an RTX 5090, bot-played; the played session is today's code on a 4070 Ti SUPER, 42 scripted lines. The budget was live in all of them at these same two rates, so what it would drop or defer on a 3060 was already dropped or deferred.

## (a) What the budget may do with each task

engine/budget.py, data/rules/budget.yaml: limit 60 s, margin 5 s (so 55 s of room), floor 8 s, reserve 20 s, 4.0 characters a token, a deferred call waits 3 turns.

- **must run**: need `required`. allow() refuses it only when under 8 s are left (BudgetSpent). Its size is never weighed.
- **may defer / may drop**: need `optional`. allow() weighs prompt characters / 4 / read rate + `answer_tokens` / write rate against what is left, less the 20 s reserve while a required passage is still ahead.
- **not seen**: need `tool`; allow() and charge() return at once.
- The gateway asks allow() once, before a call's first try. Every try is charged after it ran. Each try is handed `max(8, room - spent)` seconds as its wall-clock limit.

Prices are seconds on the minimum card. `median` is a first try as recorded; `ceiling` is the largest prompt recorded read cold plus the site's max_tokens written. `tries` is what llm/gateway.py allows one call: its retries plus one, `+2` where the site passes a looser last pass (relaxed_context), `x2` where it goes through scenes/voice.py fresh (a draft and a rewrite, each with its tries).

| task | budget may | expected tokens | recorded median / max tokens | max_tokens | tries | median s | ceiling s | calls recorded |
|---|---|---:|---:|---:|---|---:|---:|---:|
| interpret_action | must run | 120 | 60 / 700 | 700 | 3 | 3.1 | 29.7 | 2481 (44 runs) |
| audit_meaning | must run | 60 | 22 / 35 | 120 | 2 | 0.9 | 4.1 | 924 (44 runs) |
| audit_compare | must run | 60 | 39 / 95 | 160 | 2 | 1.5 | 5.4 | 924 (44 runs) |
| clarify | must run | 60 | 34 / 43 | 120 | 2 | 1.4 | 4.2 | 22 (44 runs) |
| combat_interpret | must run | 60 | 47 / 51 | 200 | 3 | 2.7 | 7.6 | 291 (44 runs) |
| party_intent | must run | 40 | 12 / 12 | 100 | 3 | 0.8 | 3.6 | 8 (44 runs) |
| camp_intent | must run | 60 | none recorded | 150 | 3 |  | 4.7 | 0 |
| lesson_want | must run | 60 | none recorded | 120 | 2 |  | 3.8 | 0 |
| work_offer_read | must run | 50 | 19 / 23 | 120 | 3 | 0.8 | 4.0 | 15 (44 runs) |
| stranger_read | must run | 20 | none recorded | 60 | 2 |  | 1.9 | 0 |
| npc_conversation | must run | 120 | 150 / 2048 | 2048 | 3+2 | 11.5 | **73.3** | 746 (44 runs) |
| npc_decide | must run | 80 | none recorded | 200 | 3 |  | 6.3 | 0 |
| npc_profile | must run | 400 | 94 / 130 | 800 | 3 | 3.8 | 26.2 | 146 (44 runs) |
| populate_place | must run | 1500 | 275 / 311 | 3000 | 3 | 9.6 | **95.7** | 203 (44 runs) |
| hire_chat | must run | 110 | 56 / 139 | 2048 | 2+2 | 5.2 | **69.4** | 594 (44 runs) |
| canon_extract | must run | 120 | 2 / 262 | 280 | 2 | 1.2 | 10.3 | 127 (44 runs) |
| canon_check | must run | 20 | 14 / 14 | 40 | 2 | 0.7 | 1.5 | 2 (44 runs) |
| mentor_chat | must run | 150 | none recorded | 2048 | 3+2 |  | **64.6** | 0 |
| mentor_speech | must run | 400 | none recorded | 2048 | 2 |  | **64.6** | 0 |
| mentor_voice | must run | 200 | none recorded | 2048 | 2 |  | **64.6** | 0 |
| ruling | must run | 200 | 67 / 177 | 500 | 3 | 3.8 | 17.7 | 95 (44 runs) |
| act_ruling | must run | 260 | 217 / 217 | 700 | 3 | 9.1 | 24.3 | 1 (played) |
| plausible_object | must run | 80 | 20 / 20 | 200 | 2 | 1.1 | 6.8 | 2 (44 runs) |
| classify_field | must run | 400 | none recorded | 1200 | 2 |  | 37.9 | 0 |
| discovery | must run | 300 | 122 / 127 | 700 | 3 | 7.4 | 25.7 | 4 (44 runs) |
| road_event | must run | 350 | 345 / 545 | 900 | 3 | 13.1 | 30.9 | 54 (44 runs) |
| generate_lessons | must run | 900 | none recorded | 1400 | 3 |  | 44.2 | 0 |
| goddess_line | must run | 150 | none recorded | 800 | 3 |  | 25.2 | 0 |
| narrate | must run | 260 | 162 / 460 | 2048 | 3 x2 | 8.0 | **69.5** | 1600 (44 runs) |
| combat_opening | must run | 260 | 174 / 260 | 2048 | 3 x2 | 7.7 | **67.4** | 193 (44 runs) |
| combat_narrate | must run | 220 | 202 / 417 | 2048 | 3 x2 | 9.5 | **69.0** | 394 (44 runs) |
| combat_aftermath | must run | 260 | 191 / 366 | 2048 | 3 x2 | 7.8 | **67.5** | 258 (44 runs) |
| dialogue_frame | may drop | 120 | 66 / 229 | 2048 | 3 x2 | 4.9 | **68.4** | 883 (44 runs) |
| exchange | may defer | 200 | 90 / 265 | 2048 | 2+2 | 6.6 | **69.9** | 414 (44 runs) |
| overheard | may drop | 60 | 16 / 27 | 120 | 2 | 0.9 | 4.2 | 469 (44 runs) |
| pair_dynamic | may drop | 100 | none recorded | 160 | 2 |  | 5.0 | 0 |
| persona_details | may defer | 350 | 243 / 284 | 520 | 2 | 8.6 | 17.8 | 141 (44 runs) |
| moment | may drop | 200 | 232 / 394 | 700 | 3+2 | 9.2 | 24.2 | 36 (44 runs) |
| npc_parting | may drop | 120 | none recorded | 2048 | 3+2 |  | **64.6** | 0 |
| arc_story | may defer | 1200 | none recorded | 1800 | 3 |  | **56.8** | 0 |
| event_judge | may drop | 350 | none recorded | 900 | 3 |  | 28.4 | 0 |
| pulse_thread | may drop | 1200 | none recorded | 2400 | 3 |  | **75.7** | 0 |
| pulse_motive | may drop | 500 | none recorded | 900 | 3 |  | 28.4 | 0 |
| pulse_cataclysm | may drop | 1500 | none recorded | 2400 | 3 |  | **75.7** | 0 |
| thread_telling | may drop | 500 | 256 / 381 | 900 | 3 | 11.8 | 32.5 | 24 (44 runs) |
| situation_parts | may drop | 800 | 658 / 709 | 1400 | 3 | 22.7 | 46.2 | 2 (played) |
| situation_agree | may drop | 20 | 14 / 14 | 40 | 2 | 0.6 | 1.5 | 2 (played) |
| board_stakes | may drop | 900 | 279 / 676 | 1600 | 2 | 10.2 | 52.2 | 60 (44 runs) |
| loot_name | may drop | 60 | none recorded | 150 | 3 |  | 4.7 | 0 |
| legendary_name | may drop | 80 | none recorded | 250 | 3 |  | 7.9 | 0 |
| accessory_name | may drop | 80 | none recorded | 300 | 3 |  | 9.5 | 0 |
| named_spell | may drop | 80 | none recorded | 200 | 3 |  | 6.3 | 0 |
| spell_rank | may drop | 80 | none recorded | 200 | 3 |  | 6.3 | 0 |
| classify_concept | must run | 300 | none recorded | 800 | 3 |  | 25.2 | 0 |
| generate_actives | must run | 2000 | none recorded | 3600 | 3 |  | **113.6** | 0 |
| generate_passive_mechanics | must run | 1800 | none recorded | 2600 | 3 |  | **82.0** | 0 |
| interpret_creation_input | must run | 100 | none recorded | 300 | 3 |  | 9.5 | 0 |
| starting_kit | must run | 60 | none recorded | 200 | 3 |  | 6.3 | 0 |
| live_judge | not seen | 200 | none recorded |  |  |  |  | 0 |
| feat_reading | not seen | 20 | none recorded | 80 | 3 |  | 2.5 | 0 |
| feat_size | not seen | 10 | none recorded | 40 | 3 |  | 1.3 | 0 |
| player_line | not seen | 60 | none recorded |  |  |  |  | 0 |
| town_profile | not seen | 800 | none recorded |  |  |  |  | 0 |

Bold ceilings cannot be written inside the turn's 55 s even alone. Tasks with no row in the records were not played in either record.

### What the budget does not see

| path | where | what it means for the 60 s |
|---|---|---|
| A retry, and the looser last pass | llm/gateway.py:239-248 (allow() is at :184, before the loop) | Never asked of the budget. Each is handed at least the 8 s floor however far over the turn is. Run on the game's own gateway (work/min_card_budget_gaps.py): with 8.1 s left one reply made 5 tries, limits 8.1, 8, 8, 8, 8 s; the budget's count ended at 101 of 55. |
| A try cut at the turn's deadline | llm/gateway.py:262-263 | Charged the task's expected size, not the limit it ran to. Same script: a reply cut after 45.5 s is charged 9.6 s; the budget then counts 35.9 s left when none is, and allows a 27 s situation_parts or a 20 s thread_telling. |
| A required call's size | engine/budget.py:146-150 | A required call is refused only under 8 s left. populate_place (max_tokens 3000) and every prose task (2048) are let in with 8 s. |
| Calls from another thread | engine/budget.py:140, :164; npc/backfill.py:47 | The rest of a place's people (populate_place, 600 to 680 tokens, about 20 s alone) are neither charged nor refused, and share the card with the turn when let in (first round: llm-flow-4, trace-threads-2). |
| A turn waiting on a background job | npc/backfill.py:80-81 | First round: trace-threads-5. No limit, nothing charged. |
| No budget open: a pane walk's arrival | scenes/world.py:1982 | First round: world_py-3. |
| No budget open: the edge between two lines | scenes/world.py:1062-1063, :840-851 | After the line is typed and before budget.open(): apply_backfill() and repopulate(). repopulate asks populate_place with deadline None, so its only limit is the 120 s REQUEST_TIMEOUT. |
| No budget open: the opening, creation, the goddess | scenes/world.py:1073 (input kind `opening`), character/creation.py | By design (budget.yaml: 'before any turn, never budgeted'). generate_actives may write 3,600 tokens: 114 s on the card. |
| Embedding calls | engine/budget.py:173-181, llm/llama.py:435 | Charged 0.15 s a text whatever they took (first round: engine1-1), and carry no deadline (llm2-2, trace-threads-3). |
| Time that is neither reading nor writing | llm/llama.py:25, :319 | A slot's wait, checkpoint copies, a 503 while the model loads ('neither the deadline's clock nor a try counts the wait'). The 5 s margin is all that covers them. |
| A machine below the minimum | engine/budget.py:264 | deadline() is None by the owner's decision; the arithmetic still runs. |
| Tool tasks | engine/budget.py:143 | live_judge, feat_reading, feat_size, player_line, town_profile. |

## (b) Every recorded line at the minimum card's rates

| record | lines | calls | median | p90 | p95 | p99 | longest | over 45 s | over 60 s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| played session, whole line | 41 | 151 | 17.5 | 32.4 | 36.5 | 42.9 | 45.0 | 0 (0.0%) | 0 (0.00%) |
| played session, to the last required call | 41 |  | 15.5 | 24.7 | 32.4 | 37.5 | 39.8 | 0 (0.0%) | 0 (0.00%) |
| played session, nothing cached (every prompt read cold) | 41 |  | 21.8 | 39.8 | 43.2 | 47.9 | 48.6 | 2 (4.9%) | 0 (0.00%) |
| 44 tracked runs, whole line | 2620 | 11125 | 18.1 | 39.9 | 47.0 | 56.6 | 93.5 | 171 (6.5%) | 17 (0.65%) |
| 44 tracked runs, to the last required call | 2620 |  | 16.1 | 36.3 | 43.4 | 54.9 | 93.5 | 113 (4.3%) | 13 (0.50%) |
| 44 tracked runs, required calls only | 2620 |  | 15.8 | 30.3 | 36.2 | 49.6 | 93.5 | 47 (1.8%) | 11 (0.42%) |
| 44 tracked runs, nothing cached | 2620 |  | 22.7 | 47.2 | 54.1 | 70.0 | 101.7 | 308 (11.8%) | 65 (2.48%) |

On the recording cards the same lines took a median of 5.9 s (played) and 4.4 s (44 runs), longest 15.4 s and 33.4 s: the minimum card is priced at about 2.9 times the 4070 Ti SUPER's time and 4.1 times the 5090's.

The budget's own arithmetic (characters / 4, engine/budget.py estimate) rebuilt from the same rows gives a median of 18.3 s and 13 lines over 60 s in the 44 runs: it tracks the token price. Measured: 4.07 characters a prompt token and 4.06 an answer token in the 44 runs, 4.07 and 3.81 in the played session, against the 4.0 in budget.yaml. The played session's own turn log agrees line by line (turn 32: budget_seconds 45, priced here 45.0; turn 33: 40 against 36.5), except turn 1, where one embedding request was charged 35 s (first round: engine1-1).

By group (whole line):

| group | lines | median | p95 | longest | over 45 s | over 60 s | replies cut off at 2,048 tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| played (18 Nov, today's code) | 41 | 17.5 | 36.5 | 45.0 | 0.0% | 0.00% | 0 of 12 |
| prose_a1 arms dry, xtc, both, min_p (20 runs, trial sampling) | 1186 | 18.0 | 47.3 | 86.3 | 6.9% | 0.67% | 2 of 278 |
| prose_a1/control (5 runs, shipped sampling) | 299 | 18.5 | 47.3 | 64.6 | 6.7% | 0.33% | 0 of 79 |
| prose_a2 (5 runs, a prompt change not kept) | 299 | 19.3 | 45.2 | 87.9 | 5.4% | 0.33% | 1 of 94 |
| prose_baseline (14 runs, shipped sampling) | 836 | 17.8 | 46.5 | 93.5 | 6.3% | 0.84% | 6 of 253 |

Where the time goes in the 44 runs: 21339 s reading, 35253 s writing (62% writing). Retries: 510 tries after a first (2456 s, 4.3% of all line time) on 424 lines; rewrites by fresh(): 204 (1160 s). The most tries one call took: 3. Retries begun when the budget's own count already left under the 8 s floor: 12 (98 s); lines whose budget count passed 55 s: 39.

Of the 17 lines over 60 s in the 44 runs, 9 hold a townsperson's reply cut off at 2,048 tokens, every one of them inside `journal_note` (5 a loop of escaped line breaks, 4 word salad); two more hold a reply that wrote 1,587 and 1,884 tokens in the same field and stopped by itself. On a real 3060 none of those 9 could finish: 2,048 tokens is 64.6 s of writing, the try would be cut at what was left of the turn (about 45 s in), the tries end there, and the reply is lost. So the 71 s priced below is what the answer costs, not what the player would wait: the wait would be about 55 s and no reply.

In the call lists, `(Nr+Mw)` is N prompt tokens read (not cached) and M tokens written.

### The ten worst lines, 44 tracked runs

| # | run, turn | whole | to last required | recorded wall | calls (seconds each; #n a retry, rw a rewrite, CUT ran to its token ceiling) |
|---:|---|---:|---:|---:|---|
| 1 | prose_baseline/new1/play_hunter_107, 54 | 93.5 | 93.5 | 20.9 | interpret_action 4.1 (1176r+81w), audit_meaning 1.0 (150r+24w), audit_compare 1.5 (229r+37w), npc_profile 3.5 (432r+94w), npc_conversation CUT 70.5 (4463r+2048w), npc_conversation#1 13.0 (1071r+366w) |
| 2 | prose_baseline/base2/play_hunter, 20 | 92.5 | 92.5 | 30.1 | interpret_action 8.3 (4708r+65w), audit_meaning 1.2 (187r+29w), audit_compare 1.6 (242r+40w), npc_profile 4.0 (635r+101w), npc_conversation CUT 71.6 (5315r+2048w), npc_conversation#1 5.9 (1071r+141w) |
| 3 | prose_a2/play_hunter_103, 50 | 87.9 | 87.9 | 22.6 | interpret_action 5.7 (1321r+125w), audit_meaning 0.9 (156r+23w), audit_compare 2.0 (273r+52w), npc_profile 3.7 (635r+92w), npc_conversation CUT 70.8 (4681r+2048w), npc_conversation#1 4.8 (1071r+106w) |
| 4 | prose_baseline/new2/play_hunter_101, 43 | 86.9 | 86.9 | 16.0 | interpret_action 6.4 (3009r+77w), audit_meaning 1.0 (237r+22w), audit_compare 1.7 (242r+44w), npc_conversation CUT 71.0 (4826r+2048w), npc_conversation#1 6.8 (1071r+172w) |
| 5 | prose_a1/xtc/play_hunter_107, 9 | 86.3 | 86.3 | 12.1 | interpret_action 6.2 (1899r+118w), audit_meaning 1.2 (196r+29w), audit_compare 1.7 (286r+41w), npc_conversation CUT 71.8 (5418r+2048w), npc_conversation#1 5.5 (1071r+129w) |
| 6 | prose_baseline/new2/play_talker_102, 47 | 84.8 | 84.8 | 15.7 | interpret_action 3.5 (1008r+69w), npc_conversation CUT 71.2 (5020r+2048w), npc_conversation#1 10.1 (5067r+107w) |
| 7 | prose_baseline/new1/play_talker_102, 11 | 84.5 | 84.5 | 19.3 | interpret_action 4.6 (1845r+69w), npc_profile 3.4 (600r+84w), npc_conversation CUT 71.5 (5186r+2048w), npc_conversation#1 4.9 (1071r+112w) |
| 8 | prose_baseline/base1/play_talker, 18 | 82.3 | 82.3 | 33.4 | interpret_action 4.2 (1830r+58w), npc_conversation CUT 71.9 (5492r+2048w), npc_conversation#1 6.2 (1071r+152w) |
| 9 | prose_a1/min_p/play_talker_102, 31 | 80.4 | 80.4 | 10.3 | interpret_action 4.7 (1833r+73w), npc_conversation CUT 71.9 (5486r+2048w), npc_conversation#1 3.8 (1071r+75w) |
| 10 | prose_a1/both/play_hunter_107, 27 | 72.0 | 62.2 | 15.2 | interpret_action 3.6 (827r+80w), populate_place 10.1 (768r+288w), hire_chat 5.2 (2910r+42w), dialogue_frame 3.8 (2132r+31w), overheard 0.9 (270r+16w), exchange 7.1 (3337r+84w), narrate 14.7 (2813r+349w), narrate#1 9.2 (402r+274w), narrate#2 7.7 (316r+232w), board_stakes 9.7 (1143r+260w) |

### The ten worst lines with no cut-off answer in them, 44 tracked runs

| # | run, turn | whole | to last required | recorded wall | calls (seconds each; #n a retry, rw a rewrite, CUT ran to its token ceiling) |
|---:|---|---:|---:|---:|---|
| 1 | prose_a1/both/play_hunter_107, 27 | 72.0 | 62.2 | 15.2 | interpret_action 3.6 (827r+80w), populate_place 10.1 (768r+288w), hire_chat 5.2 (2910r+42w), dialogue_frame 3.8 (2132r+31w), overheard 0.9 (270r+16w), exchange 7.1 (3337r+84w), narrate 14.7 (2813r+349w), narrate#1 9.2 (402r+274w), narrate#2 7.7 (316r+232w), board_stakes 9.7 (1143r+260w) |
| 2 | prose_a1/both/play_talker_102, 11 | 70.5 | 70.5 | 25.7 | interpret_action 3.5 (1402r+52w), npc_conversation 67.0 (5765r+1884w) |
| 3 | prose_a1/both/play_hunter_105, 4 | 67.7 | 67.7 | 23.8 | interpret_action 4.5 (1439r+83w), audit_meaning 1.1 (175r+29w), audit_compare 1.7 (259r+42w), npc_profile 3.7 (598r+93w), npc_conversation 56.7 (4992r+1587w) |
| 4 | prose_a1/min_p/play_hunter_103, 30 | 65.3 | 49.6 | 13.9 | interpret_action 4.4 (1242r+89w), interpret_action 3.6 (58r+111w), interpret_action 2.7 (36r+83w), clarify 1.4 (263r+34w), clarify#1 1.2 (81r+36w), interpret_action 4.7 (1336r+92w), interpret_action 5.2 (1309r+109w), interpret_action 5.4 (36r+170w), interpret_action 3.1 (1226r+46w), hire_chat 5.6 (2387r+77w), hire_chat#1 4.3 (148r+130w), narrate 8.0 (2219r+162w), exchange 10.0 (2682r+206w), dialogue_frame 5.7 (1997r+96w) |
| 5 | prose_a1/control/play_hunter_105, 2 | 64.6 | 50.3 | 11.8 | interpret_action 3.0 (588r+71w), audit_meaning 0.8 (140r+19w), audit_compare 1.5 (213r+39w), persona_details 8.2 (624r+235w), hire_chat 4.5 (2085r+56w), dialogue_frame 3.9 (2016r+40w), overheard 0.9 (264r+16w), hire_chat 5.4 (2299r+76w), hire_chat 2.7 (859r+50w), populate_place 10.3 (725r+297w), narrate 9.0 (2397r+184w), board_stakes 14.3 (956r+413w) |
| 6 | prose_a1/both/play_hunter_105, 13 | 61.3 | 61.3 | 12.4 | interpret_action 4.0 (773r+94w), audit_meaning 0.9 (153r+23w), audit_compare 1.6 (251r+40w), interpret_action 4.7 (163r+142w), interpret_action 3.0 (34r+94w), hire_chat 4.7 (2399r+48w), dialogue_frame 5.1 (2453r+59w), overheard 0.9 (287r+16w), exchange 5.9 (2378r+89w), populate_place 10.6 (696r+306w), narrate 11.5 (2647r+255w), narrate#1 8.3 (300r+252w) |
| 7 | prose_a1/both/play_hunter_105, 2 | 61.2 | 27.1 | 10.8 | interpret_action 2.7 (641r+60w), audit_meaning 0.8 (138r+18w), audit_compare 1.3 (207r+33w), ruling 3.7 (1234r+67w), populate_place 10.3 (725r+297w), narrate 8.2 (2477r+156w), persona_details 8.2 (624r+235w), persona_details 8.1 (474r+236w), board_stakes 17.8 (964r+523w) |
| 8 | prose_baseline/new2/play_hunter_101, 45 | 60.8 | 25.1 | 14.5 | interpret_action 4.8 (2938r+30w), populate_place 10.2 (669r+295w), narrate 10.1 (2691r+206w), exchange 11.2 (3542r+208w), dialogue_frame 5.8 (2018r+100w), board_stakes 18.6 (1289r+537w) |
| 9 | prose_a1/xtc/play_hunter_101, 43 | 59.9 | 59.9 | 11.0 | interpret_action 4.1 (1082r+85w), audit_meaning 0.9 (154r+22w), audit_compare 1.4 (233r+36w), hire_chat 5.2 (2499r+59w), dialogue_frame 4.9 (2184r+65w), overheard 0.9 (268r+16w), exchange 7.2 (3050r+99w), dialogue_frame 5.0 (1898r+80w), ruling 6.1 (1189r+143w), road_event 12.7 (1712r+332w), road_event#1 11.5 (385r+347w) |
| 10 | prose_baseline/new2/play_hunter_105, 2 | 59.7 | 30.3 | 15.2 | interpret_action 3.1 (592r+74w), hire_chat 4.9 (2312r+60w), hire_chat#1 2.3 (109r+68w), overheard 0.9 (274r+16w), populate_place 9.9 (725r+285w), narrate 9.1 (2413r+188w), persona_details 8.0 (624r+227w), persona_details 8.7 (446r+257w), board_stakes 12.7 (958r+362w) |

### The ten worst lines, played session (today's code)

| # | run, turn | whole | to last required | recorded wall | calls (seconds each; #n a retry, rw a rewrite, CUT ran to its token ceiling) |
|---:|---|---:|---:|---:|---|
| 1 | played, 32 | 45.0 | 34.0 | 14.4 | interpret_action 2.1 (785r+34w), populate_place 10.2 (497r+302w), moment 10.4 (1242r+278w), narrate 11.3 (2160r+269w), thread_telling 10.9 (2908r+224w) |
| 2 | played, 35 | 39.8 | 39.8 | 15.4 | interpret_action 8.6 (4105r+102w), audit_meaning 0.9 (170r+21w), audit_compare 1.4 (232r+36w), npc_profile 2.9 (438r+73w), npc_conversation 11.7 (4089r+201w), narrate 9.8 (2607r+201w), narrate rw 4.4 (48r+137w) |
| 3 | played, 33 | 36.5 | 24.4 | 15.1 | interpret_action 2.4 (1240r+23w), narrate 10.2 (2501r+220w), narrate rw 5.6 (91r+174w), narrate#1 rw 6.2 (237r+187w), exchange 5.8 (2606r+76w), dialogue_frame 6.2 (2129r+107w) |
| 4 | played, 34 | 35.7 | 10.1 | 10.5 | interpret_action 2.2 (985r+29w), narrate 7.9 (2720r+136w), situation_parts 24.4 (1520r+709w), situation_agree 0.7 (189r+14w), situation_agree 0.6 (103r+14w) |
| 5 | played, 22 | 32.4 | 32.4 | 10.5 | interpret_action 2.3 (1015r+30w), populate_place 9.7 (746r+276w), narrate 8.8 (2158r+188w), narrate#1 6.6 (252r+198w), narrate rw 5.0 (43r+157w) |
| 6 | played, 15 | 30.4 | 9.4 | 7.3 | interpret_action 1.9 (564r+36w), narrate 7.6 (2044r+154w), situation_parts 21.0 (1416r+606w) |
| 7 | played, 3 | 26.9 | 26.9 | 8.8 | interpret_action 1.7 (595r+30w), persona_details 8.0 (592r+230w), persona_details 8.4 (470r+246w), narrate 8.8 (1958r+196w) |
| 8 | played, 39 | 26.4 | 21.5 | 12.1 | interpret_action 3.3 (1373r+48w), npc_profile 2.7 (445r+68w), npc_conversation 15.5 (4256r+312w), dialogue_frame 4.9 (2207r+63w) |
| 9 | played, 16 | 24.7 | 24.7 | 7.9 | interpret_action 1.7 (639r+27w), populate_place 9.7 (766r+275w), narrate 8.9 (2546r+174w), narrate rw 4.5 (50r+140w) |
| 10 | played, 41 | 24.2 | 19.0 | 8.5 | interpret_action 5.1 (1433r+103w), audit_meaning 1.0 (169r+24w), audit_compare 1.6 (220r+41w), interpret_action 3.4 (136r+103w), hire_chat 5.5 (2633r+64w), hire_chat#1 2.3 (130r+69w), dialogue_frame 4.4 (2171r+48w), overheard 0.9 (281r+16w) |

## (c) The worst legal line, built from the code

One typed line may hold three actions (a fourth is told back as dropped). The line built here: walk into a place never entered, speak to someone never spoken to; then the world's part of the turn. scenes/world.py turn() order: the understanding; step 1 (enter: populate_place inside the walk, then moments.on_enter); its passage; step 2 (npc_profile, npc_conversation, the frame); budget.passage_shown(); the arrival (engine/matters.py on_arrival: a thread's telling); the tail; situation_births. A fight's opening and a birth cannot share a line: matters.on_arrival and situation_births both return when a fight is on, so the fight is priced as a second variant (the same line with a third action that starts one).

### Variant 1: a new place, a new person, a telling and a birth

| call | budget may | tries allowed | median prompt / answer tokens | first try, median s | every try allowed, s | at its ceiling, s |
|---|---|---|---:|---:|---:|---:|
| interpret_action | must run | 3 | 3969 / 60 | 3.2 | 7.3 | 29.7 |
| audit_meaning | must run | 2 | 160 / 22 | 0.9 | 1.7 | 4.1 |
| audit_compare | must run | 2 | 221 / 39 | 1.5 | 2.9 | 5.4 |
| populate_place | must run | 3 | 670 / 275 | 9.6 | 27.8 | **95.7** |
| moment | may drop | 3+2 | 1387 / 232 | 9.2 | 40.0 | 24.2 |
| narrate | must run | 3 x2 | 2307 / 162 | 8.1 | 34.9 | **69.5** |
| npc_profile | must run | 3 | 616 / 94 | 3.8 | 10.1 | 26.2 |
| npc_conversation | must run | 3+2 | 5132 / 150 | 11.3 | 31.2 | **73.3** |
| dialogue_frame | may drop | 3 x2 | 2108 / 66 | 4.8 | 15.9 | **68.4** |
| *budget.passage_shown(): the reserve is no longer kept* | | | | | | |
| thread_telling | may drop | 3 | 2919 / 256 | 11.9 | 28.9 | 32.5 |
| situation_parts | may drop | 3 | 1468 / 658 | 22.7 | 66.0 | 46.2 |
| situation_agree | may drop | 2 | 190 / 14 | 0.6 | 1.2 | 1.5 |
| situation_agree | may drop | 2 | 190 / 14 | 0.6 | 1.2 | 1.5 |
| **sum, no budget** | | | | **88.3** | **269.0** | **478.2** |

- **With the budget as coded, every call once at its median:** 47.5 s on the card (38.4 s of it required calls); the budget's own count ends at 47.8 s. dialogue_frame dropped; thread_telling dropped; situation_parts dropped; situation_agree not asked (no parts); situation_agree not asked (no parts)
- **With the budget as coded, every call once, but the townsperson's reply takes every try it is allowed (3, then the looser 2):** 67.5 s on the card (58.3 s of it required calls); the budget's own count ends at 67.7 s. dialogue_frame dropped; thread_telling dropped; situation_parts dropped; situation_agree not asked (no parts); situation_agree not asked (no parts)
- **With the budget as coded, every call takes every try the gateway allows, at medians:** 58.5 s on the card (58.5 s of it required calls); the budget's own count ends at 58.7 s. moment dropped; narrate ran, rewrite refused; npc_profile REFUSED; npc_conversation REFUSED; dialogue_frame dropped; thread_telling dropped; situation_parts dropped; situation_agree not asked (no parts); situation_agree not asked (no parts)
- **With the budget as coded, every call once at its ceiling:** 54.9 s on the card (54.9 s of it required calls); the budget's own count ends at 87.8 s. populate_place CUT at 16 s; moment dropped; narrate REFUSED; npc_profile REFUSED; npc_conversation REFUSED; dialogue_frame dropped; thread_telling dropped; situation_parts dropped; situation_agree not asked (no parts); situation_agree not asked (no parts)

### Variant 2: the same line with a third action that starts a fight

| call | budget may | tries allowed | median prompt / answer tokens | first try, median s | every try allowed, s | at its ceiling, s |
|---|---|---|---:|---:|---:|---:|
| interpret_action | must run | 3 | 3969 / 60 | 3.2 | 7.3 | 29.7 |
| audit_meaning | must run | 2 | 160 / 22 | 0.9 | 1.7 | 4.1 |
| audit_compare | must run | 2 | 221 / 39 | 1.5 | 2.9 | 5.4 |
| populate_place | must run | 3 | 670 / 275 | 9.6 | 27.8 | **95.7** |
| moment | may drop | 3+2 | 1387 / 232 | 9.2 | 40.0 | 24.2 |
| narrate | must run | 3 x2 | 2307 / 162 | 8.1 | 34.9 | **69.5** |
| npc_profile | must run | 3 | 616 / 94 | 3.8 | 10.1 | 26.2 |
| npc_conversation | must run | 3+2 | 5132 / 150 | 11.3 | 31.2 | **73.3** |
| dialogue_frame | may drop | 3 x2 | 2108 / 66 | 4.8 | 15.9 | **68.4** |
| combat_opening | must run | 3 x2 | 1718 / 174 | 7.6 | 36.4 | **67.4** |
| *budget.passage_shown(): the reserve is no longer kept* | | | | | | |
| **sum, no budget** | | | | **60.0** | **208.1** | **463.9** |

- **With the budget as coded, every call once at its median:** 47.5 s on the card (38.4 s of it required calls); the budget's own count ends at 47.8 s. dialogue_frame dropped; combat_opening REFUSED
- **With the budget as coded, every call once, but the townsperson's reply takes every try it is allowed (3, then the looser 2):** 67.5 s on the card (58.3 s of it required calls); the budget's own count ends at 67.7 s. dialogue_frame dropped; combat_opening REFUSED
- **With the budget as coded, every call takes every try the gateway allows, at medians:** 58.5 s on the card (58.5 s of it required calls); the budget's own count ends at 58.7 s. moment dropped; narrate ran, rewrite refused; npc_profile REFUSED; npc_conversation REFUSED; dialogue_frame dropped; combat_opening REFUSED
- **With the budget as coded, every call once at its ceiling:** 54.9 s on the card (54.9 s of it required calls); the budget's own count ends at 87.8 s. populate_place CUT at 16 s; moment dropped; narrate REFUSED; npc_profile REFUSED; npc_conversation REFUSED; dialogue_frame dropped; combat_opening REFUSED

How to read the budget lines.

- Once at medians, the two-action line already uses about 48 of the 55 s: the required calls alone are 38.5 s and the moment on entering 9.2 s. The budget holds it under 60 s by dropping the frame, the telling and the birth; in variant 2 the fight's opening finds 7.2 s left, under the 8 s floor, and is refused (the player reads a stand-in).
- One call retried is enough to pass the minute: the reply begins with 18.6 s left, its first try leaves 7.2 s, and its four further tries are each handed 8 s and each fit, because a retry reads only the draft. Nothing asks the budget between tries.
- With every try taken everywhere the budget ends the line early instead: the passage's rewrite and the whole talk are refused. The passage's second and third tries were themselves begun with under 8 s left.
- At ceilings the understanding alone takes 39 s (interpret_action at its 700 tokens is 22 s of writing: recorded 4 times in 2,481), and populate_place is cut at what is left. A cut try is charged its task's expected size: 47 s for populate_place (1,500 tokens against a recorded median of 275), 4 to 8 s for a prose task (120 to 260 tokens), whatever the seconds it ran.

### Single required calls that can pass 60 s alone

No budget rule can save these: a required call is let in with 8 s left and its size is never weighed. Only the deadline stops one, and a deadline's cut ends the tries with no reply.

| required task | max_tokens | writing it all, s | longest recorded, tokens | longest recorded, s | cut off at the ceiling in the records |
|---|---:|---:|---:|---:|---:|
| npc_conversation | 2048 | 64.6 | 2048 | 71.9 | 9 of 758 |
| populate_place | 3000 | 94.6 | 311 | 10.7 | 0 of 208 |
| hire_chat | 2048 | 64.6 | 139 | 7.3 | 0 of 601 |
| mentor_chat | 2048 | 64.6 | not recorded |  | 0 of 0 |
| mentor_speech | 2048 | 64.6 | not recorded |  | 0 of 0 |
| mentor_voice | 2048 | 64.6 | not recorded |  | 0 of 0 |
| narrate | 2048 | 64.6 | 460 | 18.6 | 0 of 1625 |
| combat_opening | 2048 | 64.6 | 269 | 10.8 | 0 of 194 |
| combat_narrate | 2048 | 64.6 | 417 | 17.3 | 0 of 396 |
| combat_aftermath | 2048 | 64.6 | 366 | 12.8 | 0 of 259 |

In 13,887 recorded calls only npc_conversation did it: 9 cut-offs (71 s each) and 2 replies of 57 and 67 s, all in journal_note. The narrator's longest passage in 1,625 calls was 460 tokens (18.6 s with its prompt). Optional tasks with the same exposure (the budget weighs their expected size, not their ceiling): dialogue_frame, exchange, npc_parting (2,048), pulse_thread and pulse_cataclysm (2,400: 75.7 s), arc_story (1,800: 56.8 s). Outside any budget: generate_actives (3,600: 113.6 s) and generate_passive_mechanics (2,600: 82 s), at creation.

## (d) What would bring the worst line down most

Each first-round saving applied alone to every recorded line, then together. `stable part cached` is an upper bound: it prices every first try as if the part of its prompt that does not change from call to call (chars - tail_chars in the log) were already in the slot's cache, for the tasks that share the second slot; `system message cached` is the same for the system message alone.

| saving (first-round finding) | seconds off a line, mean | share of all line time | median | p95 | longest | over 45 s | over 60 s |
|---|---:|---:|---:|---:|---:|---:|---:|
| as recorded [44 runs] | 0.00 | 0.0% | 18.1 | 47.0 | 93.5 | 171 (6.5%) | 17 (0.65%) |
| as recorded [played] | 0.00 | 0.0% | 17.5 | 36.5 | 45.0 | 0 (0.0%) | 0 (0.00%) |
| journal_note out of the reply unless a note is due (llm-checks-1, llm-hot-4, llm1-1) [44 runs] | 0.90 | 4.2% | 17.3 | 45.5 | 72.0 | 143 (5.5%) | 6 (0.23%) |
| journal_note out of the reply unless a note is due (llm-checks-1, llm-hot-4, llm1-1) [played] | 0.76 | 4.2% | 16.6 | 36.5 | 45.0 | 0 (0.0%) | 0 (0.00%) |
| the shared slot's prompts cached: stable part (llm2-1, llm-flow-1), upper bound [44 runs] | 4.89 | 22.7% | 13.8 | 37.7 | 87.1 | 53 (2.0%) | 11 (0.42%) |
| the shared slot's prompts cached: stable part (llm2-1, llm-flow-1), upper bound [played] | 3.63 | 19.8% | 12.8 | 32.1 | 41.4 | 0 (0.0%) | 0 (0.00%) |
| the shared slot's prompts cached: system message only [44 runs] | 3.39 | 15.7% | 15.1 | 40.6 | 89.7 | 71 (2.7%) | 12 (0.46%) |
| the shared slot's prompts cached: system message only [played] | 2.64 | 14.4% | 14.6 | 32.8 | 41.4 | 0 (0.0%) | 0 (0.00%) |
| first people and profiles written outside the turn (llm-flow-6) [44 runs] | 0.88 | 4.1% | 17.7 | 43.6 | 90.0 | 108 (4.1%) | 13 (0.50%) |
| first people and profiles written outside the turn (llm-flow-6) [played] | 1.53 | 8.3% | 15.2 | 35.7 | 36.9 | 0 (0.0%) | 0 (0.00%) |
| no layout in the grammar (llm-hot-5) [44 runs] | 0.46 | 2.1% | 17.7 | 45.9 | 92.7 | 146 (5.6%) | 15 (0.57%) |
| no layout in the grammar (llm-hot-5) [played] | 0.55 | 3.0% | 17.2 | 36.2 | 42.8 | 0 (0.0%) | 0 (0.00%) |
| no rewritten passages (llm-flow-8, llm-hot-1) [44 runs] | 0.44 | 2.1% | 17.7 | 46.2 | 93.5 | 153 (5.8%) | 17 (0.65%) |
| no rewritten passages (llm-flow-8, llm-hot-1) [played] | 0.72 | 3.9% | 17.5 | 35.4 | 45.0 | 0 (0.0%) | 0 (0.00%) |
| journal_note and layout together (grammar only) [44 runs] | 1.36 | 6.3% | 17.0 | 44.0 | 70.0 | 118 (4.5%) | 4 (0.15%) |
| journal_note and layout together (grammar only) [played] | 1.32 | 7.2% | 16.2 | 36.2 | 42.8 | 0 (0.0%) | 0 (0.00%) |
| journal_note, layout and the cache [44 runs] | 6.25 | 28.9% | 12.6 | 35.0 | 57.9 | 33 (1.3%) | 0 (0.00%) |
| journal_note, layout and the cache [played] | 4.95 | 26.9% | 10.5 | 29.7 | 39.2 | 0 (0.0%) | 0 (0.00%) |
| all five [44 runs] | 7.45 | 34.5% | 11.4 | 32.3 | 54.4 | 7 (0.3%) | 0 (0.00%) |
| all five [played] | 7.00 | 38.1% | 9.2 | 24.6 | 30.3 | 0 (0.0%) | 0 (0.00%) |

The same savings on the built line (variant 1, every call once at its median):

| saving | whole line, no budget, s | required calls, s | with the budget as coded, s |
|---|---:|---:|---:|
| as coded today | 88.3 | 38.4 | 47.5 |
| journal_note out unless due | 87.2 | 37.3 | 46.4 |
| stable part cached (upper bound) | 74.7 | 29.3 | 37.5 |
| first people and profile outside the turn | 74.9 | 25.0 | 46.2 |
| no layout | 82.9 | 36.9 | 45.4 |
| journal_note and layout | 81.7 | 35.8 | 44.3 |
| all four that touch a first try | 56.5 | 15.1 | 36.8 |

### Ranked

1. **journal_note out unless a note is due.** The only saving that removes a single call over 60 s. It takes the longest recorded line from 93.5 s to 72.0 s and the lines over 60 s from 17 to 6; on each of the nine worst lines it is worth 62 to 84 s. On an ordinary reply it is worth 1.1 s at the median (35 tokens of 150), 0.90 s a line over all lines.
2. **The shared slot's prompts cached.** The largest saving on an ordinary line: up to 4.9 s a line (23% of all line time), 3.4 s with the system messages alone. It takes the share of lines over 45 s from 6.5% to 2.0% but does little for the longest (still 87.1 s): reading is 38% of the time, and the worst lines are writing. It is also the one saving with no built answer: the first round found the RAM cache measured and lost (f537) and a third slot unmeasured on 12 GB.
3. **First people and profiles outside the turn.** Worth 0.88 s a line on average but all of it on the lines that are already long: 9.6 s on a first arrival and 3.8 s on a first talk, 13.4 s on the built line. Lines over 45 s: 6.5% to 4.1%.
4. **No rewritten passages.** 0.44 s a line; 5.4 s on each of the 204 rewritten passages (16% of first narrations). Lines over 45 s: to 5.8%. Nothing for the longest line.
5. **No layout in the grammar.** 0.46 s a line, spread thin: 0.9 s on a first arrival's residents, 0.3 s on a reply. Lines over 45 s: to 5.6%.

All five together: median 11.4 s, p95 32.3 s, longest 54.4 s, 0 lines over 60 s and 0.27% over 45 s, against 18.1, 47.0, 93.5, 17 and 6.53% as recorded. The two that are grammar only (journal_note and layout) leave 4 lines over 60 s and a longest of 70.0 s.

None of the five closes the two holes in the arithmetic itself (retries past the floor, a cut try charged its expected size): those decide what happens on the day a line does run long, whatever its usual length.

## How far this leans on the two rates

The profile's two rates come from one A4000 night of 1 November, scaled by tools/card_profile.py's rule (reading by the cards' compute, writing by their memory bandwidth, data/rules/cards.yaml). The same rule applied to the 44 tracked runs (RTX 5090, 14,035 calls) gives for the 3060:

| Rate | Profile (from the A4000 night) | From the 5090 runs, same rule | Reading |
|---|---|---|---|
| Writing, tokens a second | 31.7 | 30.4 (median of calls), 29.5 (pooled) | agrees within 7% |
| Reading, tokens a second | 756.8 | 271 (median of calls), 306 (pooled), 455 (prompts of 1,500 tokens and more), 588 (the fitted rate, fixed cost left out) | 1.3 to 2.8 times slower |

Reading is not one rate. A least-squares fit over the recorded reads gives a fixed cost a request plus a rate: on the 5090 `read_ms = 236 + tokens / 4,849 a second`, on the 4070 Ti SUPER (played session, 154 reads) `read_ms = 199 + tokens / 3,247 a second`. A read of under 100 tokens (a prompt almost wholly cached) still took 244 ms and 308 ms at the median. So a flat rate measured as the median of per-call rates (what the tool writes) depends on the mix of prompt sizes in the night it was measured on, and the fixed part does not scale with the card's compute at all. Writing also differs by task on the 5090 (prose 122 to 133 tokens a second, structured answers 180 to 290), so 31.7 is a mean over a mix as well; the pooled figure holds.

The same lines at three reading rates (writing kept at 31.7):

| Reading rate | Set | Median | p95 | Longest | Over 45 s | Over 60 s | To last required: p95 | To last required: over 60 s |
|---|---|---|---|---|---|---|---|---|
| 756.8 (the profile) | 44 runs | 18.1 | 47.0 | 93.5 | 6.5% | 0.65% (17) | 43.4 | 0.50% (13) |
| 756.8 (the profile) | played | 17.5 | 36.5 | 45.0 | 0.0% | 0.00% (0) | 32.4 | 0.00% (0) |
| 588 (5090 fit, scaled) | 44 runs | 20.4 | 51.4 | 97.1 | 9.3% | 1.30% (34) | 47.7 | 1.03% (27) |
| 588 (5090 fit, scaled) | played | 19.5 | 39.8 | 47.8 | 2.4% | 0.00% (0) | 33.9 | 0.00% (0) |
| 455 (5090 large prompts, scaled) | 44 runs | 23.3 | 56.9 | 103.2 | 12.9% | 3.32% (87) | 53.5 | 2.52% (66) |
| 455 (5090 large prompts, scaled) | played | 21.9 | 44.2 | 51.6 | 4.9% | 0.00% (0) | 36.0 | 0.00% (0) |

At the median-of-calls figure (271) the 44 runs price at a median of 32.1 s, p95 74.0 s and 12.75% of lines over 60 s, and the played session at 2 lines over 60 s; that figure counts the fixed cost of small reads as if it were rate, so it is the pessimistic end. What does not move with the read rate: the cut-off replies (64.6 s of writing each), the ranking in (d) except that the prompt cache gains (it is the only lever that removes reading), and the two holes in the budget's arithmetic. What does move: the share of lines over 45 s (6.5% to 12.9%) and whether the played session's longest line (45.0 s to 51.6 s) still clears the 55 s room. The budget itself estimates with the same 756.8, so on a card that reads at 455 it would allow optional calls it has no room for: its estimate of a 5,000 token reply prompt is 6.6 s where the card would take 11.0 s.

The A4000 is the nearer card (the 3060 has 0.66 of its compute, against 0.12 of the 5090's), so its figure may well be the better one. The point is that the rule gives a different 3060 from each source card, and only a timed night on the card settles it (GOALS.md already makes that the condition for revisiting the budget).

### The second minimum card

GOALS.md names two minimum cards; the limit holds on the Radeon RX 7600 XT 16 GB through Vulkan as on the 3060. There is one profile file and engine/budget.py reads only it, so a Vulkan machine is priced at the 3060's rates (data/rules/cards.yaml says f530 will price by the backend's minimum card; nothing reads its `minimum` or `patterns` but the startup check). By the same table the 7600 XT has 288 GB/s of memory bandwidth against 360, so it writes at 0.8 of the 3060's rate, 25.4 tokens a second: a second the budget counts as written is 1.25 s there, a 55 s count that is all writing is 69 s, and 2,048 tokens is 80.8 s. From a table, never a measure; Vulkan's own cost is not in it.

| Priced as | Set | Median | p95 | Longest | Over 45 s | Over 60 s | To last required: over 60 s |
|---|---|---|---|---|---|---|---|
| 3060 profile (read 756.8, write 31.7) | 44 runs | 18.1 | 47.0 | 93.5 | 6.5% | 0.65% (17) | 0.50% (13) |
| 3060 profile (read 756.8, write 31.7) | played | 17.5 | 36.5 | 45.0 | 0.0% | 0.00% (0) | 0.00% (0) |
| 7600 XT, both by the rule (read 1346.7, write 25.4) | 44 runs | 17.5 | 48.3 | 110.1 | 7.3% | 1.30% (34) | 0.80% (21) |
| 7600 XT, both by the rule (read 1346.7, write 25.4) | played | 16.8 | 39.1 | 49.3 | 2.4% | 0.00% (0) | 0.00% (0) |
| 7600 XT, writing by the rule, reading as the 3060 (read 756.8, write 25.4) | 44 runs | 20.7 | 55.1 | 114.4 | 10.8% | 2.67% (70) | 1.87% (49) |
| 7600 XT, writing by the rule, reading as the 3060 (read 756.8, write 25.4) | played | 20.1 | 42.9 | 53.7 | 4.9% | 0.00% (0) | 0.00% (0) |

## Scripts

All under the audit's work folder: min_card_reprice.py (the pricing and the savings), min_card_runaways.py and min_card_runaway_shape.py (answers that ran to their ceiling), min_card_sites.py (call sites by AST), min_card_budget_gaps.py (the two holes, on the game's own gateway with a stand-in source), min_card_rates.py, min_card_readfit.py and min_card_sensitivity.py (the last section), min_card_amd.py (the second minimum card), min_card_tables.py (this file).
