# What the model writes, field by field, over the tracked record (logs-fields)

Made by the audit's scripts in scratchpad/audit/work (lf_measure.py, lf_checks.py, lf_hire.py, lf_hire2.py, lf_mech.py, lf_table.py) over every
llm_calls.jsonl.gz that git tracks under docs/measure: the play record (prose_baseline, prose_a1, prose_a2: 14,035 calls, 44 files, 32 tasks)
and the live-check record (3,985 calls, 10 files, 16 tasks). Nothing was run against a model.

How to read it:

- The record was made on a rented RTX 5090 (docs/measure/prose_baseline/README.md), about 130 features ago. Seconds are that card's. The two
  3060 columns convert tokens at the rates in data/measured/card_profile.yaml: 31.7 answer tokens a second, 756.8 prompt tokens a second.
- A field's share is its characters (key and value, compact) over the answer's characters, summed over the task; tokens a call is that share
  times the task's mean answer tokens. It is an estimate: tokens are not counted per field.
- 'In the answer' is how often the key was written; 'filled' how often its value was not empty, false or zero.
- 'Read by today' and 'verdict' were checked against the code at f730, not the code the record was made with. A field the record never
  shows (ActionIntent.mark, added since) is not listed.
- The player's lines in the play record are the night bot's (player_line), so shares that depend on what was typed are the bot's mix.

## 1. Every task of the play record

| task | calls | send-backs | seconds, sum | seconds, median | prompt tokens, median | answer tokens, median / max | cached share of prompt tokens | calls with nothing cached | hit the ceiling | layout share | 3060: read s if nothing cached | 3060: write s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| populate_place | 263 | 0 | 6345 | 1.51 | 694 | 281 / 680 | 0.2% | 213 | 0 | 18% | 0.9 | 8.9 |
| narrate | 1647 | 190 | 3328 | 1.96 | 2346 | 160 / 460 | 22.9% | 1052 | 0 | 1% | 3.1 | 5.0 |
| npc_conversation | 746 | 47 | 2200 | 2.35 | 5138 | 150 / 2048 | 8.4% | 323 | 9 | 7% | 6.8 | 4.7 |
| interpret_action | 2481 | 4 | 2185 | 0.81 | 3969 | 60 / 700 | 74.8% | 76 | 4 | 5% | 5.2 | 1.9 |
| player_line | 2759 | 533 | 1291 | 0.41 | 521 | 24 / 57 | 18.9% | 1633 | 0 | 4% | 0.7 | 0.8 |
| dialogue_frame | 883 | 141 | 1121 | 1.19 | 2133 | 66 / 229 | 16.0% | 579 | 0 | 2% | 2.8 | 2.1 |
| combat_narrate | 394 | 57 | 917 | 2.27 | 2890 | 202 / 417 | 25.7% | 282 | 0 | 0% | 3.8 | 6.4 |
| hire_chat | 594 | 39 | 673 | 1.02 | 2624 | 56 / 139 | 7.6% | 429 | 0 | 10% | 3.5 | 1.8 |
| exchange | 414 | 39 | 577 | 1.29 | 2849 | 90 / 265 | 9.1% | 314 | 0 | 4% | 3.8 | 2.8 |
| combat_aftermath | 258 | 0 | 477 | 1.75 | 1894 | 191 / 366 | 32.4% | 168 | 0 | 1% | 2.5 | 6.0 |
| combat_opening | 193 | 16 | 395 | 1.97 | 1727 | 174 / 260 | 11.3% | 163 | 0 | 1% | 2.3 | 5.5 |
| audit_compare | 924 | 0 | 274 | 0.29 | 221 | 39 / 95 | 0.1% | 756 | 0 | 6% | 0.3 | 1.2 |
| audit_meaning | 924 | 0 | 254 | 0.25 | 160 | 22 / 35 | 0.1% | 756 | 0 | 3% | 0.2 | 0.7 |
| persona_details | 141 | 10 | 237 | 1.61 | 819 | 243 / 284 | 15.5% | 79 | 0 | 8% | 1.1 | 7.7 |
| generate_passive_mechanics | 44 | 0 | 206 | 4.48 | 1050 | 928 / 982 | 0.0% | 44 | 0 | 19% | 1.4 | 29.3 |
| combat_interpret | 291 | 0 | 182 | 0.49 | 957 | 47 / 51 | 0.0% | 282 | 0 | 14% | 1.3 | 1.5 |
| road_event | 54 | 2 | 143 | 2.47 | 1742 | 345 / 545 | 4.4% | 50 | 0 | 4% | 2.3 | 10.9 |
| overheard | 469 | 0 | 125 | 0.22 | 277 | 16 / 27 | 0.1% | 364 | 0 | 11% | 0.4 | 0.5 |
| board_stakes | 60 | 0 | 123 | 2.06 | 970 | 279 / 676 | 0.0% | 48 | 0 | 17% | 1.3 | 8.8 |
| npc_profile | 146 | 0 | 122 | 0.8 | 616 | 94 / 130 | 0.1% | 93 | 0 | 3% | 0.8 | 3.0 |
| ruling | 95 | 0 | 88 | 0.98 | 1224 | 67 / 177 | 2.0% | 90 | 0 | 17% | 1.6 | 2.1 |
| moment | 36 | 1 | 76 | 1.98 | 1386 | 232 / 394 | 2.3% | 29 | 0 | 15% | 1.8 | 7.3 |
| canon_extract | 127 | 0 | 63 | 0.48 | 829 | 2 / 262 | 0.0% | 101 | 0 | 0% | 1.1 | 0.1 |
| thread_telling | 24 | 2 | 52 | 2.22 | 2930 | 256 / 381 | 8.3% | 17 | 0 | 4% | 3.9 | 8.1 |
| situation_parts | 6 | 0 | 21 | 3.39 | 1634 | 694 / 891 | 0.0% | 6 | 0 | 33% | 2.2 | 21.9 |
| clarify | 22 | 4 | 8 | 0.3 | 272 | 34 / 43 | 16.2% | 16 | 0 | 4% | 0.4 | 1.1 |
| work_offer_read | 15 | 0 | 5 | 0.32 | 122 | 19 / 23 | 0.1% | 13 | 0 | 27% | 0.2 | 0.6 |
| discovery | 4 | 4 | 4 | 1.06 | 2729 | 122 / 127 | 48.5% | 2 | 0 | 6% | 3.6 | 3.9 |
| party_intent | 8 | 0 | 2 | 0.31 | 326 | 12 / 12 | 0.1% | 5 | 0 | 25% | 0.4 | 0.4 |
| situation_agree | 9 | 0 | 2 | 0.2 | 203 | 14 / 14 | 14.7% | 6 | 0 | 10% | 0.3 | 0.4 |
| plausible_object | 2 | 0 | 1 | 0.34 | 360 | 20 / 20 | 0.0% | 2 | 0 | 20% | 0.5 | 0.6 |
| canon_check | 2 | 0 | 0 | 0.2 | 212 | 14 / 14 | 0.0% | 2 | 0 | 10% | 0.3 | 0.4 |

Ceiling hits (tokens.finish = length; tokens.full was never true): 13 of 14,035. npc_conversation 9, every one inside journal_note at 2,048
tokens (8.5 to 29.3 s each on the 5090, 138 s together, each tried again). interpret_action 4, every one inside the summary of a 'look' step,
repeating a phrase ('...guild house house house...') to the 700 ceiling: 2.9 to 3.6 s on the 5090, about 22 s on the 3060, then tried again.
Live-check record: canon_extract 2 of 501 at its 280 ceiling.

## 2. Every task of the live-check record

| task | calls | send-backs | seconds, sum | seconds, median | prompt tokens, median | answer tokens, median / max | cached share of prompt tokens | calls with nothing cached | hit the ceiling | layout share | 3060: read s if nothing cached | 3060: write s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| exchange | 653 | 83 | 1177 | 1.72 | 3109 | 116 / 415 | 12.6% | 317 | 0 | 5% | 4.1 | 3.7 |
| dialogue_frame | 808 | 121 | 1108 | 1.32 | 1916 | 81 / 135 | 20.6% | 347 | 0 | 2% | 2.5 | 2.6 |
| live_judge | 1013 | 0 | 724 | 0.67 | 838 | 72 / 96 | 50.8% | 3 | 0 | 6% | 1.1 | 2.3 |
| hire_chat | 588 | 58 | 655 | 1.04 | 2544 | 60 / 121 | 43.1% | 129 | 0 | 10% | 3.4 | 1.9 |
| canon_extract | 501 | 2 | 260 | 0.51 | 885 | 2 / 280 | 0.3% | 225 | 2 | 0% | 1.2 | 0.1 |
| mentor_chat | 151 | 1 | 160 | 1.01 | 3072 | 52 / 193 | 46.6% | 21 | 0 | 3% | 4.1 | 1.6 |
| narrate | 36 | 3 | 65 | 1.73 | 2424 | 132 / 206 | 16.6% | 9 | 0 | 1% | 3.2 | 4.2 |
| persona_details | 31 | 1 | 54 | 1.65 | 808 | 237 / 265 | 17.7% | 16 | 0 | 8% | 1.1 | 7.5 |
| interpret_action | 30 | 0 | 34 | 1.06 | 3807 | 65 / 65 | 48.0% | 10 | 0 | 4% | 5.0 | 2.1 |
| pair_dynamic | 30 | 0 | 31 | 0.97 | 1018 | 123 / 150 | 7.8% | 13 | 0 | 5% | 1.3 | 3.9 |
| npc_profile | 30 | 0 | 27 | 0.83 | 567 | 94 / 117 | 0.0% | 30 | 0 | 3% | 0.7 | 2.9 |
| mentor_voice | 30 | 0 | 16 | 0.52 | 1260 | 29 / 53 | 66.6% | 3 | 0 | 4% | 1.7 | 0.9 |
| audit_meaning | 30 | 0 | 10 | 0.31 | 133 | 31 / 31 | 0.5% | 9 | 0 | 2% | 0.2 | 1.0 |
| audit_compare | 30 | 0 | 8 | 0.25 | 223 | 34 / 36 | 0.3% | 9 | 0 | 7% | 0.3 | 1.1 |
| canon_check | 14 | 0 | 3 | 0.22 | 206 | 14 / 14 | 6.8% | 5 | 0 | 10% | 0.3 | 0.4 |
| overheard | 10 | 0 | 3 | 0.28 | 290 | 16 / 20 | 0.1% | 6 | 0 | 10% | 0.4 | 0.5 |

## 3. Field by field, play record


### populate_place (play record: 263 calls, 263 answers read)

npc/life.py:129 (ResidentSet). First round: people-12 (name), llm-hot-5 (layout), llm-hot-14 (ceiling 3,000).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| residents[].slot | 100% | 100% | 36 | 4 | 4.5% | 12.4 | 0.39 | npc/life.py _apply matches it to the engine's slot | set known: the engine listed the slots; copied back |
| residents[].name | 100% | 100% | 87 | 47 | 11.3% | 31.7 | 1.00 | nothing: _apply takes the slot's own name | copied, then dropped (people-12) |
| residents[].epithet | 100% | 100% | 132 | 80 | 17.1% | 47.7 | 1.50 | the person's label | used |
| residents[].description | 100% | 100% | 495 | 427 | 64.0% | 178.5 | 5.63 | the person's description | words |

### npc_conversation (play record: 746 calls, 736 answers read)

npc/life.py converse (NPCReply / NPCReplyPromised). First round: llm-checks-1, llm1-1, llm-hot-2, llm-hot-3, llm-hot-4, llm-hot-7.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| speech | 100% | 99% | 119 | 110 | 19.1% | 39.5 | 1.24 | shown | words |
| intent | 100% | 100% | 17 | 5 | 2.3% | 4.8 | 0.15 | engine/trust.py after_talk; scenes/world.py 3821-3867 | used (only share 665 and small_talk 71 of nine values seen) |
| reveals | 96% | 51% | 28 | 24 | 4.4% | 9.1 | 0.29 | npc/life.py: kept only ids the engine offered and the speech carries | set known: free strings (llm-hot-2); 245 of 477 items look like ids |
| trust_change | 100% | 4% | 17 | 2 | 2.3% | 4.7 | 0.15 | engine/trust.py, clamped | used; non-zero in 4% |
| told_own_name | 100% | 2% | 22 | 4 | 2.9% | 6.1 | 0.19 | npc/life.py apply_answer | used; true in 2% (llm-hot-3) |
| learned_player_name | 100% | 16% | 25 | 13 | 3.6% | 7.4 | 0.23 | apply_answer, only if the name is in the player's words | used |
| remember | 100% | 61% | 61 | 64 | 6.9% | 14.3 | 0.45 | kept in the person's memory | used (llm-checks-11: no bound) |
| journal_note | 100% | 86% | 133 | 128 | 47.8% | 98.8 | 3.12 | scenes/world.py: kept only when a note is due | not wanted on 684 of 736 calls, written on 584 of them and dropped: 42% of all reply tokens (llm-checks-1) |
| they_promised | 12% | 10% | 51 | 38 | 0.9% | 1.9 | 0.06 | apply_answer | used; in the grammar only when engine/brief.py promised() says so (f493) |
| gesture | 3% | 3% | 91 | 78 | 0.3% | 0.6 | 0.02 | shown | words |
| gives | 0% | 0% | 13 | 0 | 0.0% | 0.0 | 0.00 | apply_answer | used |
| offers_quest | 0% | 0% | 20 | 0 | 0.0% | 0.0 | 0.00 | apply_answer | used |

### interpret_action (play record: 2481 calls, 2477 answers read)

scenes/world.py:3278 (ActionPlan of ActionIntent, max_tokens 700). Planned: docs/design/29_one_reader_plan.md R2 (ids from the engine's list), R3 (a words field; summary stays).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| actions[].kind | 100% | 100% | 28 | 8 | 11.2% | 7.2 | 0.23 | the dispatch | used |
| actions[].destination | 31% | 31% | 28 | 11 | 4.1% | 2.6 | 0.08 | checked against the places the engine listed | set known (planned: doc 29 R2, f732) |
| actions[].summary | 100% | 100% | 92 | 71 | 46.4% | 29.5 | 0.93 | the words of the act, logs, dropped-step notes; several sites fall back to the typed line (intent.summary or text) | used; unbounded, ran to the 700 ceiling 4 times |
| actions[].target | 58% | 58% | 24 | 12 | 6.4% | 4.1 | 0.13 | checked against the people and things listed | set known (planned: doc 29 R2) |
| actions[].speech | 59% | 57% | 73 | 62 | 19.3% | 12.3 | 0.39 | the line said | used; 1,043 of 1,587 are a word-for-word piece of the typed line |
| actions[].item | 8% | 8% | 15 | 5 | 0.7% | 0.4 | 0.01 | checked against the pack | set known (planned: doc 29 R2) |
| actions[].seek | 16% | 15% | 21 | 11 | 1.7% | 1.1 | 0.03 | explore / ask | used (free words) |
| actions[].count | 2% | 2% | 10 | 1 | 0.1% | 0.1 | 0.00 | buy / sell / craft | used |
| actions[].ware | 1% | 1% | 14 | 4 | 0.1% | 0.1 | 0.00 | checked against the wares | set known (planned: doc 29 R2) |
| actions[].wait_minutes | 6% | 0% | 17 | 1 | 0.5% | 0.3 | 0.01 | wait | used |
| actions[].wait_until | 3% | 1% | 16 | 4 | 0.3% | 0.2 | 0.01 | wait | used |
| actions[].force | 1% | 0% | 14 | 4 | 0.1% | 0.1 | 0.00 | the act | used |
| actions[].checks | 0% | 0% | 24 | 14 | 0.1% | 0.0 | 0.00 | the act | used |
| actions[].ability | 0% | 0% | 17 | 4 | 0.0% | 0.0 | 0.00 | checked against the abilities | set known (planned: doc 29 R2) |

### dialogue_frame (play record: 883 calls, 882 answers read)

scenes/world.py (DialogueFrame).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| before | 100% | 96% | 155 | 154 | 63.6% | 44.5 | 1.40 | shown before the speech | words |
| after | 100% | 84% | 99 | 95 | 36.3% | 25.4 | 0.80 | shown after the speech | words |

### hire_chat (play record: 594 calls, 594 answers read)

scenes/party_actions.py:791 (a talk) and scenes/quirk_actions.py:287 (companion_line, a line about a happening): CompanionReply at both.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| speech | 100% | 100% | 72 | 60 | 46.8% | 26.6 | 0.84 | shown | words |
| gesture | 100% | 6% | 13 | 52 | 9.4% | 5.4 | 0.17 | shown | words; the empty key is written on 94% of replies |
| remember | 100% | 53% | 47 | 46 | 23.0% | 13.1 | 0.41 | party_actions.py:811 keeps it; quirk_actions.py:300-306 reads speech and gesture only | used in a talk; dropped at companion_line (filled in 53 of at least 77 such lines) |
| impression | 100% | 0% | 16 | 0 | 9.4% | 5.4 | 0.17 | party_actions.py:815 sets m['impression'] | never filled: 0 of 594 (0 of 588 in the live record); the empty key is written every time |
| they_promised | 100% | 1% | 19 | 27 | 11.4% | 6.5 | 0.20 | party_actions.py:813 keeps it as a memory | filled 7 of 594 (0 of 588 live), 4 of the 7 on a line with no promise in it; the empty key is written every time |

### exchange (play record: 414 calls, 414 answers read)

scenes/banter_actions.py:112 (Exchange of ExchangeLine).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| lines[].speaker | 100% | 100% | 51 | 25 | 16.7% | 15.7 | 0.50 | matched to the speakers the engine named (near_speaker mend, f587) | set known: 846 of 847 were a named speaker |
| lines[].text | 100% | 100% | 205 | 185 | 68.5% | 64.5 | 2.03 | shown | words |
| lines[].gesture | 100% | 16% | 26 | 30 | 10.1% | 9.5 | 0.30 | shown | words; the empty key is written in 765 of 847 lines |

### audit_compare (play record: 924 calls, 924 answers read)

scenes/audit_actions.py:83 (AuditVerdict). First round: llm-rest-2, llm-rest-6. Planned: doc 29 R3 (f733) removes both audit calls.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| matches | 100% | 80% | 15 | 4 | 10.4% | 4.2 | 0.13 | engine/intent_audit.py:266 | used |
| reason | 100% | 100% | 127 | 115 | 89.6% | 35.9 | 1.13 | intent_audit.py:268 only when matches is false; else audit_actions.py:233 logs it | logged only on 744 of 924 calls (matches true): 34 tokens each |

### audit_meaning (play record: 924 calls, 924 answers read)

scenes/audit_actions.py:79 (llm-rest-6).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| meaning | 100% | 100% | 84 | 71 | 100.0% | 22.4 | 0.71 | handed to audit_compare, logged | used by the next call only |

### persona_details (play record: 141 calls, 141 answers read)

scenes/quirk_actions.py:75 (PersonaDetails, max_tokens 520).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| details | 100% | 100% | 566 | 555 | 61.7% | 151.0 | 4.76 | the hire's five details | words |
| secrets | 100% | 100% | 284 | 273 | 31.3% | 76.7 | 2.42 | the hire's secrets | words |
| weights | 100% | 100% | 58 | 47 | 7.1% | 17.3 | 0.55 | quirk_actions.py:83 -> engine/gravity.py:34, only if the count equals the details | set known and count known; dropped whole in 56 of 141 (seven weights for five details and two secrets) |

### generate_passive_mechanics (play record: 44 calls, 44 answers read)

character/creation.py:150 (MechanicSet, max_tokens 2600): fifteen of eighteen offered.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| passives[].option_id | 100% | 100% | 262 | 37 | 9.6% | 89.6 | 2.83 | creation.py:160, checked against the offered ids | set known: 660 of 660 valid; a free string in the grammar |
| passives[].name | 100% | 100% | 411 | 261 | 15.1% | 140.5 | 4.43 | the perk's name | words |
| passives[].description | 100% | 100% | 1732 | 1477 | 64.3% | 598.8 | 18.89 | the perk's description | words |
| passives[].tier | 100% | 100% | 240 | 90 | 8.8% | 82.3 | 2.60 | engine/abilities.py:84-86: picks values[0] or values[1] of the perk | used: the model picks the perk's number (232 moderate, 428 light; 3 to 8 moderate a character) |

### combat_interpret (play record: 291 calls, 291 answers read)

scenes/combat_scene.py:439 (CombatIntent, max_tokens 200). Planned: doc 29 R4 (f734) closed id lists.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| kind | 100% | 100% | 17 | 7 | 17.2% | 7.6 | 0.24 | the dispatch | used (ability 210, attack 49, move 32, other 0) |
| target | 89% | 89% | 14 | 2 | 12.4% | 5.5 | 0.17 | matched to ENEMIES | set known (planned: doc 29 R4); 259 of 259 valid |
| ability | 72% | 72% | 27 | 14 | 18.5% | 8.2 | 0.26 | matched to YOUR ABILITIES | set known (planned: doc 29 R4) |
| summary | 100% | 100% | 48 | 35 | 49.1% | 21.7 | 0.69 | combat_scene.py:680 and services/fight.py:398, both only for kind other | not wanted: written 291 of 291, read 0 of 291; the typed line word for word in 249 |
| move | 11% | 11% | 16 | 6 | 2.7% | 1.2 | 0.04 | the move | used |

### road_event (play record: 54 calls, 54 answers read)

scenes/road_actions.py:362 (RoadEvent, max_tokens 900). First round: llm-checks-15 (kind).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| title | 100% | 100% | 30 | 19 | 2.1% | 7.6 | 0.24 | ledger line, the stop's name, the danger's cause | used |
| journey | 100% | 100% | 668 | 655 | 47.3% | 166.6 | 5.26 | shown | words |
| scene | 100% | 100% | 542 | 531 | 40.7% | 143.3 | 4.52 | shown | words |
| kind | 100% | 100% | 16 | 6 | 1.1% | 3.9 | 0.12 | checked against the kind the engine picked | copied (llm-checks-15) |
| news | 100% | 24% | 10 | 98 | 2.5% | 8.7 | 0.27 | road_effects: pulse.add_news | used when filled (24%) |
| effects[].kind | 91% | 91% | 16 | 6 | 1.0% | 3.5 | 0.11 | road_effects | used |
| effects[].text | 44% | 44% | 84 | 74 | 2.8% | 9.9 | 0.31 | road_effects | used |
| effects[].place | 46% | 46% | 21 | 10 | 0.7% | 2.5 | 0.08 | road_effects: a road or place id, else the road walked | set known |
| effects[].value | 46% | 46% | 11 | 2 | 0.4% | 1.3 | 0.04 | road_effects, clamped to road.yaml danger_effect | used |
| effects[].days | 46% | 46% | 9 | 1 | 0.3% | 1.1 | 0.03 | road_effects, clamped | used |
| effects | 9% | 0% | 13 | 0 | 0.1% | 0.3 | 0.01 |  |  |
| meets_role | 13% | 11% | 22 | 6 | 0.2% | 0.7 | 0.02 | road_actions.py:384, only if in world.roles | set known |

### overheard (play record: 469 calls, 469 answers read)

engine/party_director.py:101 (Overheard, max_tokens 120).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| about | 100% | 4% | 11 | 9 | 27.4% | 4.4 | 0.14 | party_director: a name counts only if it is a listener and named(text, name) | set known: 15 of 24 items were no listener; the engine's own name test decides it anyway |
| party | 100% | 55% | 13 | 4 | 31.8% | 5.2 | 0.16 | returned to the director | used |
| weight | 100% | 100% | 17 | 5 | 40.8% | 6.6 | 0.21 | returned to the director | used (light 435, personal 34) |

### board_stakes (play record: 60 calls, 60 answers read)

engine/stakes.py:93 (BoardStakes, max_tokens 1600).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| postings[].id | 100% | 100% | 48 | 24 | 4.7% | 15.1 | 0.48 | matched to the postings the engine listed | copied: 161 of 161 valid; a free string in the grammar |
| postings[].reason | 100% | 100% | 399 | 357 | 39.1% | 125.8 | 3.97 | the posting's stakes | words |
| postings[].result | 100% | 100% | 163 | 126 | 16.3% | 52.4 | 1.65 | the posting's stakes | words |
| postings[].more{} | 98% | 0% | 27 | 0 | 2.4% | 7.7 | 0.24 | stakes.py:108 only when the posting was marked MORE BEHIND IT | not wanted on 124 of 161 postings: 116 empty objects written, 8 written in full and dropped |
| postings[].more.truth | 55% | 55% | 182 | 171 | 13.3% | 42.9 | 1.35 | as above | used when wanted |
| postings[].more.reveal | 55% | 55% | 100 | 88 | 7.3% | 23.5 | 0.74 | as above | used when wanted |
| postings[].more.clue | 55% | 55% | 110 | 100 | 7.5% | 24.1 | 0.76 | as above | used when wanted |
| postings[].more.path.name | 55% | 55% | 29 | 19 | 2.0% | 6.5 | 0.20 | engine/matters.py:399, engine/events.py 281-289 | used; a slug in 21 of 45 |
| postings[].more.path.how | 55% | 55% | 15 | 6 | 1.4% | 4.5 | 0.14 | engine/matters.py:399 | used; only the kind word in 35 of 45 |
| postings[].more.path.kind | 55% | 55% | 14 | 4 | 1.2% | 3.7 | 0.12 | the path's kind | used |
| postings[].more.path.target | 55% | 55% | 28 | 16 | 2.0% | 6.4 | 0.20 | the path's target | used |

### npc_profile (play record: 146 calls, 146 answers read)

npc/life.py promote (NPCProfile). First round: llm-rest-12 (voice), llm-rest-3.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| personality | 100% | 100% | 258 | 240 | 64.5% | 60.9 | 1.92 | npc.personality | words |
| concern | 100% | 100% | 106 | 92 | 26.7% | 25.2 | 0.80 | npc.concern | words |
| motive | 100% | 29% | 12 | 72 | 8.7% | 8.2 | 0.26 | npc/life.py: kept only if has_motive | not wanted on 104 of 146 calls (the empty key is written) |

### moment (play record: 36 calls, 36 answers read)

engine/moments.py:142 (MomentProposal, max_tokens 700).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| title | 100% | 100% | 36 | 26 | 5.1% | 12.0 | 0.38 | the moment's title | used |
| line | 100% | 100% | 138 | 128 | 19.9% | 47.3 | 1.49 | shown | words |
| memory | 100% | 100% | 70 | 58 | 10.0% | 23.7 | 0.75 | kept by those present | used |
| doings[].who | 100% | 100% | 63 | 27 | 10.8% | 25.6 | 0.81 | checked against the roles present or 'everyone' | set known; 1 send-back of 36 (nobody there, a role invented) |
| doings[].doing | 100% | 100% | 244 | 206 | 33.9% | 80.6 | 2.54 | shown | words |
| visitor_epithet | 100% | 3% | 21 | 18 | 3.0% | 7.2 | 0.23 | engine/moments.py, only when a visitor was drawn | not wanted on 35 of 36 calls (the empty key is written) |
| visitor_look | 100% | 3% | 18 | 74 | 2.9% | 6.8 | 0.21 | as above | not wanted on 35 of 36 calls |
| visitor_doing | 100% | 3% | 19 | 58 | 2.9% | 6.9 | 0.22 | as above | not wanted on 35 of 36 calls |
| mishap | 72% | 53% | 107 | 96 | 8.6% | 20.5 | 0.65 | only when a mishap was drawn | used when asked |

### canon_extract (play record: 127 calls, 127 answers read)

engine/canon.py:564 (Extracted, max_tokens 280). The answer is {} in 113 of 127.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| facts | 21% | 0% | 11 | 0 | 8.5% | 1.4 | 0.04 |  |  |
| facts[].speaker | 11% | 11% | 47 | 21 | 10.2% | 1.6 | 0.05 | canon.py route: matched to the speakers given | set known: 29 of 29 valid |
| facts[].text | 11% | 11% | 118 | 98 | 29.9% | 4.8 | 0.15 | the claim kept | used |
| facts[].subject | 11% | 11% | 35 | 9 | 8.2% | 1.3 | 0.04 | route | used |
| facts[].kind | 11% | 11% | 30 | 10 | 7.0% | 1.1 | 0.04 | route | used |
| facts[].weight | 11% | 11% | 36 | 12 | 7.3% | 1.2 | 0.04 | route | used |
| facts[].lasts | 11% | 11% | 30 | 8 | 6.3% | 1.0 | 0.03 | route | used |
| facts[].common | 11% | 0% | 30 | 0 | 6.1% | 1.0 | 0.03 | route | used (false 29 of 29) |

### thread_telling (play record: 24 calls, 24 answers read)

engine/threads.py:532 (ThreadTelling, max_tokens 900): every field is kept on the matter.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| stages | 100% | 100% | 243 | 233 | 29.8% | 76.8 | 2.42 |  |  |
| clues | 100% | 100% | 248 | 239 | 22.4% | 57.7 | 1.82 |  |  |
| fallout | 92% | 92% | 162 | 150 | 14.7% | 37.9 | 1.19 |  |  |
| truth | 92% | 92% | 189 | 178 | 15.5% | 39.8 | 1.26 |  |  |
| reveal | 92% | 50% | 139 | 146 | 7.9% | 20.3 | 0.64 |  |  |
| resolution | 92% | 92% | 104 | 88 | 9.7% | 24.9 | 0.78 |  |  |

### clarify (play record: 22 calls, 22 answers read)

scenes/audit_actions.py:196 (Clarify, max_tokens 120).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| speaker | 100% | 100% | 21 | 8 | 19.9% | 6.8 | 0.21 | audit_actions.py: the present person with that id, else the narrator | set known: the ids are listed in the request; 1 of 22 outside them |
| line | 100% | 100% | 90 | 80 | 80.1% | 27.4 | 0.86 | shown | words |

### work_offer_read (play record: 15 calls, 15 answers read)

scenes/work_actions.py:98 (WorkOffer, max_tokens 120). 12 of 15 answers said no offer ('0' 7, 'none' 3, '' 2).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| task | 100% | 87% | 11 | 1 | 52.5% | 10.2 | 0.32 | inferred_offer: dropped when empty, digits or one of six no-words | used; the contract has no place to say no |
| minutes | 100% | 0% | 12 | 0 | 47.5% | 9.2 | 0.29 | the offer's length | used |

### discovery (play record: 4 calls, 4 answers read)

scenes/explore_actions.py:118 (DiscoveryProposal, max_tokens 700). 4 calls, 4 sent back: 'a find needs a name and a description' (llm-checks-6).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| found | 100% | 100% | 13 | 4 | 3.0% | 3.7 | 0.12 |  |  |
| place_type | 100% | 100% | 21 | 5 | 4.9% | 6.0 | 0.19 |  |  |
| description | 100% | 100% | 239 | 222 | 55.2% | 67.8 | 2.14 |  |  |
| residents | 50% | 50% | 26 | 13 | 2.9% | 3.6 | 0.11 |  |  |
| news | 100% | 100% | 132 | 122 | 30.7% | 37.6 | 1.19 |  |  |
| to | 50% | 50% | 27 | 19 | 3.2% | 4.0 | 0.13 |  |  |

### party_intent (play record: 8 calls, 8 answers read)

scenes/party_actions.py:87 (PartyIntent). First round: llm-rest-10.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| kind | 100% | 100% | 14 | 4 | 100.0% | 12.0 | 0.38 | the dispatch | used |

### situation_agree (play record: 9 calls, 9 answers read)

engine/situations.py:201 (CanonCheck, max_tokens 40).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| verdict | 100% | 100% | 16 | 3 | 61.5% | 8.6 | 0.27 | situations.py:205 | used |
| which | 100% | 11% | 10 | 1 | 38.5% | 5.4 | 0.17 | nothing at this call site (engine/canon.py:117 reads it for canon_check) | written, never read here |

### plausible_object (play record: 2 calls, 2 answers read)

scenes/law_actions.py:105 (ObjectVerdict, max_tokens 200).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| plausible | 100% | 0% | 18 | 0 | 51.4% | 10.3 | 0.32 |  |  |
| reason | 100% | 100% | 17 | 5 | 48.6% | 9.7 | 0.31 |  |  |

### canon_check (play record: 2 calls, 2 answers read)

engine/canon.py:110 (CanonCheck).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| verdict | 100% | 100% | 16 | 3 | 61.5% | 8.6 | 0.27 | canon.py:118 | used |
| which | 100% | 0% | 10 | 0 | 38.5% | 5.4 | 0.17 | canon.py:117 | used (0 in all 16) |

## 4. Field by field, live-check record (the tasks it adds or shows differently)


### exchange (live record: 653 calls, 653 answers read)

scenes/banter_actions.py:112 (Exchange of ExchangeLine).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| lines[].speaker | 100% | 100% | 67 | 28 | 16.0% | 22.5 | 0.71 | matched to the speakers the engine named (near_speaker mend, f587) | set known: 846 of 847 were a named speaker |
| lines[].text | 100% | 100% | 245 | 216 | 63.0% | 88.5 | 2.79 | shown | words |
| lines[].gesture | 100% | 54% | 54 | 44 | 16.7% | 23.5 | 0.74 | shown | words; the empty key is written in 765 of 847 lines |

### hire_chat (live record: 588 calls, 588 answers read)

scenes/party_actions.py:791 (a talk) and scenes/quirk_actions.py:287 (companion_line, a line about a happening): CompanionReply at both.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| speech | 100% | 100% | 100 | 88 | 59.1% | 37.1 | 1.17 | shown | words |
| gesture | 100% | 9% | 13 | 40 | 9.0% | 5.6 | 0.18 | shown | words; the empty key is written on 94% of replies |
| remember | 100% | 24% | 14 | 51 | 13.7% | 8.6 | 0.27 | party_actions.py:811 keeps it; quirk_actions.py:300-306 reads speech and gesture only | used in a talk; dropped at companion_line (filled in 53 of at least 77 such lines) |
| impression | 100% | 0% | 16 | 0 | 8.4% | 5.2 | 0.17 | party_actions.py:815 sets m['impression'] | never filled: 0 of 594 (0 of 588 in the live record); the empty key is written every time |
| they_promised | 100% | 0% | 19 | 0 | 9.9% | 6.2 | 0.20 | party_actions.py:813 keeps it as a memory | filled 7 of 594 (0 of 588 live), 4 of the 7 on a line with no promise in it; the empty key is written every time |

### canon_extract (live record: 501 calls, 499 answers read)

engine/canon.py:564 (Extracted, max_tokens 280). The answer is {} in 113 of 127.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| facts[].speaker | 8% | 8% | 44 | 18 | 8.4% | 1.1 | 0.03 | canon.py route: matched to the speakers given | set known: 29 of 29 valid |
| facts[].text | 8% | 8% | 101 | 85 | 20.5% | 2.6 | 0.08 | the claim kept | used |
| facts[].subject | 8% | 8% | 34 | 9 | 6.7% | 0.8 | 0.03 | route | used |
| facts[].kind | 8% | 8% | 36 | 15 | 6.6% | 0.8 | 0.03 | route | used |
| facts[].weight | 8% | 8% | 37 | 13 | 7.0% | 0.9 | 0.03 | route | used |
| facts[].lasts | 8% | 8% | 32 | 10 | 5.9% | 0.7 | 0.02 | route | used |
| facts[].common | 8% | 0% | 30 | 14 | 5.5% | 0.7 | 0.02 | route | used (false 29 of 29) |
| facts | 24% | 0% | 11 | 0 | 11.7% | 1.5 | 0.05 |  |  |

### mentor_chat (live record: 151 calls, 151 answers read)

scenes/mentor_actions.py:289 (MentorReply).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| speech | 100% | 100% | 157 | 145 | 86.6% | 53.2 | 1.68 | shown | words |
| gesture | 100% | 0% | 13 | 0 | 5.8% | 3.6 | 0.11 | shown | words; filled 0 of 151, the empty key is written |
| moves_on | 100% | 0% | 17 | 0 | 7.6% | 4.7 | 0.15 | mentor_actions.py: ends the talk | used; false 151 of 151 |

### persona_details (live record: 31 calls, 31 answers read)

scenes/quirk_actions.py:75 (PersonaDetails, max_tokens 520).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| details | 100% | 100% | 556 | 545 | 63.5% | 149.0 | 4.70 | the hire's five details | words |
| secrets | 97% | 97% | 274 | 264 | 30.0% | 70.4 | 2.22 | the hire's secrets | words |
| weights | 100% | 100% | 58 | 47 | 6.6% | 15.4 | 0.49 | quirk_actions.py:83 -> engine/gravity.py:34, only if the count equals the details | set known and count known; dropped whole in 56 of 141 (seven weights for five details and two secrets) |

### pair_dynamic (live record: 30 calls, 30 answers read)

scenes/banter_actions.py:839 (PairDynamic, max_tokens 160). First round: llm-checks-6 names its two thinks lines.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| dynamic | 100% | 100% | 162 | 149 | 39.1% | 48.0 | 1.51 |  |  |
| first_wants | 100% | 100% | 38 | 21 | 9.3% | 11.5 | 0.36 |  |  |
| second_wants | 100% | 100% | 40 | 22 | 10.7% | 13.1 | 0.41 |  |  |
| first_thinks | 100% | 100% | 90 | 72 | 20.8% | 25.5 | 0.80 |  |  |
| second_thinks | 100% | 100% | 89 | 70 | 20.1% | 24.7 | 0.78 |  |  |

### npc_profile (live record: 30 calls, 30 answers read)

npc/life.py promote (NPCProfile). First round: llm-rest-12 (voice), llm-rest-3.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| personality | 100% | 100% | 288 | 271 | 69.4% | 64.1 | 2.02 | npc.personality | words |
| concern | 100% | 100% | 106 | 92 | 27.6% | 25.5 | 0.80 | npc.concern | words |
| motive | 100% | 0% | 12 | 0 | 3.1% | 2.8 | 0.09 | npc/life.py: kept only if has_motive | not wanted on 104 of 146 calls (the empty key is written) |

### mentor_voice (live record: 30 calls, 30 answers read)

scenes/mentor_actions.py:141.

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| lines | 100% | 100% | 63 | 54 | 69.5% | 24.5 | 0.77 |  |  |
| reply | 87% | 43% | 36 | 50 | 30.5% | 10.8 | 0.34 |  |  |

### overheard (live record: 10 calls, 10 answers read)

engine/party_director.py:101 (Overheard, max_tokens 120).

| field | in the answer | filled | median chars, key and value | median chars of the value when filled | share of what the task writes | tokens a call (mean) | 3060 s a call | read by today | verdict |
|---|---|---|---|---|---|---|---|---|---|
| about | 100% | 10% | 11 | 13 | 26.6% | 4.4 | 0.14 | party_director: a name counts only if it is a listener and named(text, name) | set known: 15 of 24 items were no listener; the engine's own name test decides it anyway |
| party | 100% | 0% | 14 | 0 | 30.2% | 5.0 | 0.16 | returned to the director | used |
| weight | 100% | 100% | 20 | 8 | 43.2% | 7.1 | 0.22 | returned to the director | used (light 435, personal 34) |

## 5. The fields by kind

### Written, and not read (or read only to be logged or dropped)

| task.field | what happens to it | how often | cost on the 3060 |
|---|---|---|---|
| combat_interpret.summary | read only for kind other (scenes/combat_scene.py:680, services/fight.py:398) | written 291 of 291, kind other 0 of 291 | 21.3 tokens, 0.67 s on every fight line (49% of the answer) |
| audit_compare.reason | used only when matches is false; else logged | logged only on 744 of 924 | 34 tokens, 1.07 s on each audited line that matched |
| hire_chat.remember at companion_line | scenes/quirk_actions.py:300-306 reads speech and gesture only | filled in 53 of at least 77 such lines (61 of 133 in the live record) | about 13 tokens, 0.4 s a line (23% of a hire reply) |
| board_stakes.postings[].more, not asked for | engine/stakes.py:108 keeps it only for a posting marked MORE BEHIND IT | 8 written in full and dropped, 116 empty objects, of 124 not asked | 1,623 of 19,316 tokens (8%) |
| persona_details.weights | dropped whole when the count is not five | 56 of 141 (57 of the 58 drops in both records are seven weights) | 7% of the answer; the hire's details then weigh as their subjects do |
| situation_agree.which | engine/situations.py:205 reads the verdict only | 9 of 9 | about 4 tokens, 0.1 s |
| npc_conversation.journal_note, no note due | first round llm-checks-1 | 584 of 684 | 97.5 tokens, 3.08 s a reply; 42% of all reply tokens; all 9 ceiling hits |
| populate_place.residents[].name | first round people-12 | every resident | 11.4% of the answer, about 1.0 s a place |

### In the grammar on calls where the engine already knows it will keep nothing (the empty key is written)

| task.field | the engine's own test | not wanted | filled anyway |
|---|---|---|---|
| hire_chat.impression | none today; 'only if what you think of the player has just changed' (scenes/party_prompts.py:34) | - | filled 0 of 1,182 (both records) |
| hire_chat.they_promised | engine/brief.py promised() exists (f493) and is used for townsfolk only; it says yes on 9 of 1,182 lines | 1,173 | filled 7, of them 4 on a line with no promise (an old one said again) |
| moment.visitor_epithet, visitor_look, visitor_doing | ctx visitor (llm/contracts.py MomentProposal) | 35 of 36 | 0; the three empty keys are 19.5 tokens, 0.61 s a call |
| npc_profile.motive | has_motive (npc/life.py promote) | 104 of 146 | 0 |
| board_stakes.postings[].more | more_wanted (engine/stakes.py) | 124 of 161 | 8 |
| mentor_chat.gesture | - | - | 0 of 151 |
| exchange.lines[].gesture | - | - | empty in 765 of 847 lines (play), 46% (live) |

### Free strings where the engine knows every valid value

| task.field | the set the engine holds | what the record shows | status |
|---|---|---|---|
| situation_parts ids (who, holder, a, b, on, by, points_to) | the people and goods listed | 6 calls here | first round engine6-9 |
| interpret_action destination, target, item, ware, ability | the request's lists | - | planned: docs/design/29 R2 (f732) |
| combat_interpret target, ability, movement, buff_for | ENEMIES, YOUR ABILITIES, ALLIES | target 259 of 259 valid | planned: docs/design/29 R4 (f734) |
| npc_conversation.reveals | the ids of what they could tell | 477 items, 245 id-like | first round llm-hot-2; done on the decide path (decision_contract) |
| persona_details.weights | light, personal, heavy; exactly five | 821 of 821 values valid, the count wrong in 40% | new |
| generate_passive_mechanics.passives[].option_id | the eighteen offered ids | 660 of 660 valid | new (low: none failed) |
| board_stakes.postings[].id | the postings listed | 161 of 161 valid | new (low: none failed) |
| exchange.lines[].speaker | the two speakers | 846 of 847 valid (mended by near_speaker) | new (low) |
| canon_extract.facts[].speaker | the speakers given | 29 of 29 valid | new (low) |
| clarify.speaker | the ids under PEOPLE HERE, or narrator | 1 of 22 outside | new (low) |
| moment.doings[].who | the roles present, or everyone | 1 send-back of 36 (nobody present) | new (low) |
| overheard.about | the names listening | 15 of 24 items were no listener | new (low: the engine's own name test decides) |
| road_event.meets_role, effects[].place | world.roles; road and place ids | meets_role filled 6 of 54 | new (low) |

## 6. Tasks in this record that the first round's played session never reached

| task | where it is built | when it fires | calls here | prompt tokens, median | answer tokens, median | 5090 s, median | 3060 s (read with nothing cached + write) |
|---|---|---|---|---|---|---|---|
| player_line | tools/nightbot.py:1222 | the night bot writing the player's next line: a tool's call, never the game's | 2759 | 521 | 24 | 0.41 | 0.7 + 0.8 |
| board_stakes | engine/stakes.py:93, from scenes/guild_actions ensure_board | the guild board gets new postings (scenes/guild_actions.py:133): one call for the new postings together | 60 | 970 | 279 | 2.06 | 1.3 + 8.8 |
| road_event | scenes/road_actions.py:362 | a happening is rolled on a road walk (an ambush, or a find, meeting, sight, hazard, aid) | 54 | 1742 | 345 | 2.47 | 2.3 + 10.9 |
| ruling | engine/ruling.py:148 | today only the road hazard's ruling; 91 of the 95 here are the general ruling that f603 replaced | 95 | 1224 | 67 | 0.98 | 1.6 + 2.1 |
| clarify | scenes/audit_actions.py:196 | a typed line could not be read: someone present, or the narrator, asks back | 22 | 272 | 34 | 0.3 | 0.4 + 1.1 |
| work_offer_read | scenes/work_actions.py:98 | a townsperson's speech matched the pay and task words and the reply carried no offer | 15 | 122 | 19 | 0.32 | 0.2 + 0.6 |
| party_intent | scenes/party_actions.py:87 | a line read as hiring or directing the adventurers who travel with the player (party_actions.py:109) | 8 | 326 | 12 | 0.31 | 0.4 + 0.4 |
| discovery | scenes/explore_actions.py:118 | exploring beyond the known place, after the engine's roll said there is a find | 4 | 2729 | 122 | 1.06 | 3.6 + 3.9 |
| canon_check | engine/canon.py:110 | a statement someone makes about themselves is weighed against what is already true of them (canon.py vet) | 2 | 212 | 14 | 0.2 | 0.3 + 0.4 |
| situation_agree | engine/situations.py:201 | a new situation's part is near an established fact | 9 | 203 | 14 | 0.2 | 0.3 + 0.4 |
| plausible_object | scenes/law_actions.py:105 | a theft of, or a search for, a thing nobody listed (law_actions.py:248, 399) | 2 | 360 | 20 | 0.34 | 0.5 + 0.6 |
| mentor_chat | scenes/mentor_actions.py:289 | talking with Maren | 151 | 3072 | 52 | 1.01 | 4.1 + 1.6 |
| mentor_voice | scenes/mentor_actions.py:141 | Maren says written lines in her own words, with an answer to what the player just said | 30 | 1260 | 29 | 0.52 | 1.7 + 0.9 |
| pair_dynamic | scenes/banter_actions.py:839 | the line on how two hires are with each other is written (its trigger was not traced) | 30 | 1018 | 123 | 0.97 | 1.3 + 3.9 |
| live_judge | tools/live_check.py:201 | the live check's judge: a tool's call | 1013 | 838 | 72 | 0.67 | 1.1 + 2.3 |

The list of what the first round's session reached is the first round's own (its notes); thread_telling, situation_parts and moment were reached there.

