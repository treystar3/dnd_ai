# Stale copies: what the instrument saw

Second round, part "stale-copies". Everything here was measured under simlib's stub (no model, no server), with a harness kept
outside the repository (scratchpad/audit/work/stale/stalewatch.py). The harness wraps the store's load and save methods for
people, the player, places, entities, the world state and the small key-value stores. Each loaded object carries a serial number,
its record id and the stored text it came from; each save compares the stored text with that base.

Classes of event:

- LOST: a copy is saved over a text another copy wrote since this one was loaded, and the save changes at least one field back.
- BENIGN: the same, but no field goes back (the stale copy already carried the other's change).
- GHOST: a copy that carries a save, or a load, from a transaction that was rolled back, saved afterwards.
- HELD_STALE: at the end of an input, or just before the scene reads its people again, a copy the scene holds lacks what the save has.
- HELD_DIRTY: the same moments, a copy the scene holds has a change that is in no save.

## 1. What ran

| Session | Inputs | Loads | Saves | Lost updates | Notes |
|---|---|---|---|---|---|
| tools/sim/world_script.py (its play) | script | 1,721 | 707 | 1 (people) | the script's own direct call, see pair F |
| data/replay/scripts/stub_fight.py | script | 645 | 140 | 0 | |
| data/replay/scripts/stub_party.py | script | 1,729 | 206 | 0 | |
| kept recording stub_short, replayed | 41 | 1,623 | 365 | 0 | 93 of 93 model calls matched, nothing parted |
| kept recording stub_party, replayed | 15 | 1,694 | 171 | 0 | 86 of 86 |
| kept recording stub_fight, replayed | 20 | 643 | 137 | 0 | 62 of 62 |
| night bot, 40 inputs, seed 39 | 40 | 1,474 | 347 | 0 | |
| night bot, 250 inputs, seed 11 | 250 | 19,907 | 2,654 | 5 (world 3, place 2) | |
| night bot, 120 inputs, seed 1, 2 hires | 120 | 9,950 | 1,409 | 1 (world) | |
| night bot, 12 sessions of 400 inputs (seeds 2 to 14, five personas, 0 to 3 hires, planted model failures) | 4,800 | 387,265 | 54,125 | 19 (world 16, place 3) | 5 game faults in 4 sessions, all one KeyError (finding 5) |
| my session: a day in town (talk, work, a request taken and handed in, buy, haggle, sell, steal, sleep) | 32 | 2,446 | 402 | 3 (people 2, world 1) | |
| my session: hires, a fight beside them, two hires and a realm ally lost, rest | 19 | 1,508 | 326 | 2 (player 1, world 1) | |
| my sessions: the pulse over 60, 40 and 100 days, talking and walking between | 272 | 38,901 | 7,463 | 13 (world) | "moments seen" read 1 at the end of each |
| probes: a failed haggle; a goodbye then a word; eight deeds on someone here on their routine | 43 | 3,653 | 543 | 1 (people) | the first two are outside the totals below |

About 5,700 inputs; 472,331 loads and 68,861 saves in the sessions whose counts were kept. 45 lost updates, 0 GHOST, 0 BENIGN: every
stale save seen put something back, and none followed a rollback. The three kept recordings replay under the harness with every
state, outcome and shown line the same, so the harness does not change play.

## 2. Lost updates, by the pair of call sites

| | The write that is lost | The stale save that undoes it | Record, fields | Times | Where seen | First round |
|---|---|---|---|---|---|---|
| A | engine/moments.py start (loads 191, saves 194), called from engine/matters.py _play_moment 312 | engine/matters.py on_arrival (loads 254, saves 292) | world state: moments_seen | 35 | 12 of 15 bot sessions, all 5 of my sessions | in the check text of engine4-4, rated small |
| B | engine/town_memory.py file (loads 74, saves 85), called from moments.close | engine/moments.py on_enter (loads 99, saves 116) | place: memory (the town's row for the ended moment) | 5 | 4 bot sessions | engine5-2, rated rare |
| C | engine/stakes.py done (loads 175, saves 180), called from guild_actions.py turn_in 648 | npc/life.py converse 458, saving the scene's copy (twice in one hand-in) | person: regard trust, regard moves | 2 | my town session | scenes2-1 |
| D | engine/pulse.py remove_npc (loads 936, saves 951), called from events.fallen_allies 882 | services/fight.py end 749 (party_after_fight), then the commit | player: quests, item_history | 1 | my party session | engine3-3, engine5-1 |
| E | scenes/world.py part_from 4013 (the object it took before advance) | npc/life.py converse 458, saving the copy refresh_present loaded at 604 | person: said, heard | 1 | the goodbye probe; the stale copy was held 12 times in the bot and town sessions and not saved there | new (finding 3) |
| F | engine/situation_parts.py register (loads 299, saves 305) | engine/situation_parts.py keep_changes 1304, saving the scene's copy | person: concern, concern_from, concern_state, mood, mood_source, mood_until | 1 | world_script only: the script calls register itself, without the game's reread_here | not a fault of the game |

What a player meets:

- A. Every moment a situation plays in front of the player through the moments machinery leaves no row in the playthrough's list
  of moments. Traced in four bot sessions (1,600 inputs): 20 moments began, 13 by the place's roll and 7 by a situation. All 7
  situation rows were written over; all 13 rolled rows stood. The list feeds four readers: the weights of the next shape
  (moments.py 74), the request and the contract's "unlike what was seen" check for the next model moment (134 to 143), and
  moments.tick's search for places to close from afar (241). So a situation's moment at a place the player walks out of is not
  closed when it ends. 5 of the 7 stayed on their place until the player came back, 205, 2,554, 3,561, 12,378 and 12,758 game
  minutes after their end (the last is 8.9 days). The town's memory of it and each witness's memory are then dated at the return.
- B. When that late close happens at a town's top place, on_enter's stale save wipes the town's memory row: 3 of those 5 (Parth
  twice, Saltmarsh Landing). All 13 rolled moments were closed by tick, none by on_enter. So in play pair B follows from pair A.
- C. The asker's thanks for a job done (trust +5, cause "job done") is gone after their reply: the save read 57 where it should
  read 62.
- D. A realm ally who gave the player a job dies beside them: the job is back in the journal with nobody to hand it to, and the
  line that said it came to nothing is gone.
- E. A goodbye said to someone who is here on their routine (the guild contractor at the Tilted Plough of an evening), then
  another word: their record no longer holds the parting line or what drew it.

## 3. Copies the scene holds

| What | Times | Verdict |
|---|---|---|
| Held copy lacks said and heard after part_from (11 at the end of an input, 1 before a re-read) | 12 | pair E waiting to happen |
| Resident's held copy has an old activity (doings.assign saved a second copy made by refresh_present 591 for a resident away by the hour, sent to the player by a summons) | 2 at the end of an input, 2 before a re-read | healed by run_pulse's re-read on the next line |
| Held copy lacks a relation the pulse changed (pulse.apply_one through situation_parts.register); the six FELT fields are patched by refresh, relations are not | 130 | healed each time by reread_here (scenes/world.py 659) |
| Held copy has a trust move that is in no save: a failed haggle (pastime_actions.py 112) | 2 | dropped by the same line's re-read (finding 4) |
| Held copy has a stock laid out and not yet saved | 4 | by design (save_npc_later, f470) |
| Held copy has a spent mood cleared in memory (moments.end 287 to 290), the save still holds the spent mood | 1 | harmless: every reader checks mood_until |

## 4. Writers that save a copy of their own while another copy is alive

Seen in the runs (at least; three samples were kept per pair and session). Each is safe only while every holder of the record reads
it again before saving.

- people (10): drift.people, matters._open_word, moments.close, pulse.apply_one, pulse.end_thread, pulse.resolver,
  situation_parts.register, situation_parts.release, stakes.done, arc_actions.bring_prisoners
- places (12): moments.on_enter, moments.start, pulse.apply_one, pulse.move_npc, pulse.post_contract, pulse.remove_npc,
  situation_parts.make_person, town_memory.file, town_memory.sweep, life._apply, arc_actions.bring_prisoners,
  guild_actions.on_accept_quest
- the player (1 in these runs): arc_actions.drop_prisoner (pulse.remove_npc in the party session)
- the world state (22): act._situation, deeds.log, events.after_deed, events.on_kills, events.read_ends, events.take_up_waiting,
  matters.bind_for, matters.on_arrival, matters.road_shown, matters.spoke, matters.try_find, moments.start, pulse.catch_up,
  situation_parts.adopt_all, situation_parts.birth, situation_parts.decline, situation_parts.missed,
  situation_parts.wait_for_room, standing.report, world_improv.apply_changes, road_actions.keep_landmark,
  road_actions.meet_closure
- entities (1): features.register

## 5. How many loads an input makes (two bot sessions of 400 inputs, counters only, no tagging)

| | steady, 3 hires | talker, no hires |
|---|---|---|
| Record loads an input | 65 | 62 |
| Loads of a record this same input had already loaded | 77% | 77% |
| ...with the row not written in between | 72% | 72% |
| Whole world-state loads an input | 19 | 20 |
| Time in loads | 5.9 s of 53.2 s played (11%) | 7.7 s of 63.4 s (12%) |
| Time in loads an input | 15 ms | 19 ms |

One live record per operation would take most of these loads away, but it is 15 to 19 ms an input against a model's seconds:
not a speed case.

## 6. The hand-made repairs, and what each is for

| Repair | Where | What it covers | What it leaves |
|---|---|---|---|
| The people here read again every pulse | scenes/world.py 699 to 702 | any second copy of a resident written during the line | the window inside the line (pairs C, E); drops unsaved changes (the haggle) |
| reread_here after a situation is born | scenes/world.py 674 to 679, called at 659 | what register wrote on fresh copies (130 times in these runs) | only this caller |
| run_pulse's player_text guard | scenes/world.py 687 to 691 | the pulse's remove_npc writing the player | the same writer called inside an operation (pair D); never fired in these runs |
| situation_parts.refresh, six FELT fields | engine/situation_parts.py 1737 to 1746, called at 830 and events.py 703 | a worry or mood released on a fresh copy | every other field (relations) |
| drift's sweep and parts_ended (500 ends kept) | engine/situation_parts.py 1749 to 1763, drift.py 108 | a worry a late stale save brought back, days after | a permanent pass for a fault that should not happen |
| npc_by_id and notice's _live | scenes/world.py 150 to 161, 197 to 208 | reactions change the object the caller will save | only code that asks through them |
| refresh_present re-points the partner | scenes/world.py 611 to 614 | the talk follows the fresh copy | the handler's own local reference (pair E) |
| asked_operation's deep copies put back in place | scenes/world.py 1468 to 1470, 1483 to 1485 | an attempt that stood down | references into a record held elsewhere (scenes3-3) |

## 7. Limits

- The instrument sees only what the sessions play. Pairs C, D and E came from sessions written to reach them; the bot never
  hands a request in by talking and lost no realm ally.
- It does not see a reference held to a dict inside a record across operations (scenes3-3): nothing stale is ever saved there.
- The f589 detector's own list named my wrapper as the site (it reads the calling frame), so its site names were not checked here;
  the first round's engine4-4 check read "engine.matters:on_arrival" from it.
- saves/, logs/ and the other closed folders were never read. Each campaign was named audit_stale-copies_... and removed in a
  finally block; the game's logs were pointed into the harness folder.
