# The order of the audit's fix plan

Read for this: docs/design/ROADMAP.md; GOALS.md whole (pillars, "How it is built", "Checking a change", the decisions table, open
questions); docs/design/32_code_audit.md sections 1, 3.1 and 9; the openings of docs 27, 28, 29 and 31; the Order section of all
22 workstream files and the full text of about sixty features where two workstreams met. Every feature's Needs line was parsed
and checked against the order below by a script (plan/work/depcheck.py): no stated need is broken; the thirteen that the script
lists are each marked "nothing" or "whichever lands first" by the feature itself. Every one of the 341 keys stands in exactly one
phase (plan/work/phases.py prints the count).

## 1. Overlaps between workstreams

Most twins were already found by the skeptics and say "one build". Where the text did not say who owns the piece, I say it here.
Five are new: SITUATIONS-17's fence already exists; PEOPLE_TALK-13 and REMOVALS_2-7 remove the same arguments; STALE_COPIES-11 is
one family of BUDGET_FLOW-10; TOWN_SERVICES-8 and RELOAD-11 edit the same function; GATE-20 and STARTUP_DATA-8 build the same list.

| Features | What is built twice | Who owns it, and what becomes of the other |
|---|---|---|
| TASK_FAILURE-16, STALE_COPIES-10 | npc/life.py _apply in one transaction; backfill collect under crashlog | STALE_COPIES-10 builds it; TASK_FAILURE-16 adds only its case of a job's own error to the same test. Adjacent in phase 9, after TASK_FAILURE-2 |
| TOWN_SERVICES-7, TRAVEL_PLACES-8 | void_dungeon_contracts over every board, the posting predicate | TOWN_SERVICES-7 owns the predicate and the board helper; TRAVEL_PLACES-8 adds the telling and every character. Their texts disagree on postings whose floor survives (TS-7 takes "Slay" postings off, which is option b; TP-8 asks a, b or c): one answer, given once |
| REMOVALS_2-7, PEOPLE_TALK-13 | removing the temperature argument at the same eight call sites (mentor, banter, party, quirk, canon) | REMOVALS_2-7 owns it with its startup check; PEOPLE_TALK-13 keeps only the owed pair line. Placed together in phase 18 |
| SITUATIONS-17, FIGHT_CORE-9, STALE_COPIES-12, FIGHT_ABILITIES-14, TOWN_SERVICES-9 | ratchets on reads of the first player | SITUATIONS-17 says engine/'s 128 reads of ws.player are counted by nothing; tools/sim/acting_character_630_test.py READS already counts them per engine file (events 28, truth 26, matters 17...). That test is the one fence: FIGHT_CORE-9 adds the fight's `.player` half to it; SITUATIONS-17 drops its fence half and keeps the moves of engine/stakes.py and engine/stay.py; STALE_COPIES-12 is text in doc 20; FIGHT_ABILITIES-14 lowers actor_632's per-directory counts; TOWN_SERVICES-9 adds its Memory count to 630 |
| STALE_COPIES-11, BUDGET_FLOW-10 | moving moment and thread_telling into asked_outside and out of RECORDED | BUDGET_FLOW-10 owns the mechanism and the ratchet over the goldens' rows; STALE_COPIES-11 is its arrival family, built first inside it with its door_loc test, and BUDGET_FLOW-10's list loses those two tasks |
| TOWN_SERVICES-8, RELOAD-11 | scenes/world.py lines 4100 to 4152, one function: the field ability's cost (TS-8) and the craft boost and its cooldown (R-11); both ask about an out-of-fight cooldown | TOWN_SERVICES-8 owns the one spend step; RELOAD-11 then keeps the boost on the record. Ordered TS-8, R-11, R-12 in phase 12; the two cooldown questions are one |
| GATE-20, STARTUP_DATA-8 | storage/statehash.py: "the game's data files" (GATE-20's helper) and "one named list of what is not the game" (SD-8) | STARTUP_DATA-8 owns the named list (with data/tools); GATE-20's vocabulary reads it. SD-8 before GATE-20 in phase 6 |
| CONTRACTS-16, TYPED_LINE-2 (part 4), TASK_FAILURE-11 | the audit's two model calls while doc 29 is pending | Doc 29 R1 and R3 own them. TYPED_LINE-2 parts 1 to 3 are R1's measure. CONTRACTS-16's two-shape verdict and TYPED_LINE-2 part 4 are alternatives: build at most one, and only if R3 slips past phase 4. TASK_FAILURE-11's handler mend holds under either and is built in phase 9 |
| GATE-21, doc 31 f731 | the building search of engine/truth.py:421-436 | Doc 31's engine/elsewhere.py owns it if approved; GATE-21 is one more trigger inside it. Built first, GATE-21 is moved there |
| BUDGET_FLOW-9, RELOAD-10, REMOVALS_2-12 | the input's count across give_back | RELOAD-10 owns it; BUDGET_FLOW-9 adds its test case; REMOVALS_2-12's comments follow. Adjacent in phase 3 |
| BUDGET_FLOW-26, REMOVALS_1-13 | NUM_CTX in llm/backend.py and config.py | BUDGET_FLOW-26 owns; REMOVALS_1-13 is the deletion in the same change |
| SHIPPING-1, STARTUP_DATA-1 | one reader of source in engine/data_check.py | SHIPPING-1 builds the reader and the "this is a build" answer; STARTUP_DATA-1 adds the once-a-process cache and the C loader. Adjacent in phase 6 |
| GATE-5, TYPED_LINE-3, TYPED_LINE-4, PEOPLE_TALK-14 | a whole-word matcher | GATE-5 owns engine/wordlist.py (phase 5); TYPED_LINE-3 and -4 read it. PEOPLE_TALK-14 plans a third matcher (word starts, after character/fit.py); it should be a mode of the same module |
| TYPED_LINE-5, GATE-7, STARTUP_DATA-10 | the number-word table | TYPED_LINE-5 lands first (phase 10) and makes engine/numbers.py and data/rules/numbers.yaml; GATE-7 and STARTUP_DATA-10 read it in phase 13 |
| RELOAD-5, RELOAD-13, TOOLS_BOTS-1 | marker files in storage/saves.py | RELOAD-5 owns the game's marker; TOOLS_BOTS-1's scratch marker refuses a folder carrying it. Ordered RELOAD-5, RELOAD-13, TOOLS_BOTS-1 |
| REMOVALS_1 and REMOVALS_2 twins | one census and its sweeps | 2-1 owns the census, 1-1 is its import sweep; 1-2 owns the names fence and KEPT table, 2-10 its sweep; 2-11 owns the seven wrappers with 1-4's tests; 1-6 removes the stat-passives step (phase 5, before CONTRACTS-5's floors), 2-8 adds its census rule later; 2-5 owns the motive step with 1-7; 1-10 and 2-13 one change; 1-17 and 2-4 one change, one answer |
| CONTRACTS-13, REMOVALS_2-6, PEOPLE_TALK-8 | the small readers' summaries; party_intent's dead kinds | CONTRACTS-13 owns PartyIntent and CombatIntent; REMOVALS_2-6 the camp half and the field fence; PEOPLE_TALK-8 deletes the handlers. One re-bless of stub_party, phase 14 |
| LONG_SAVE-12, BUDGET_FLOW-17 | "names near here" under a cap | BUDGET_FLOW-17 owns the helper; LONG_SAVE-12 uses it, after it in phase 14 |
| SUITE-7, TOOLS_BOTS-3 | simlib swap(), a stack of undoings | TOOLS_BOTS-3 comes first (phase 8) and builds it; SUITE-7 uses it |
| TESTS-7, SHIPPING-2 | node, playwright and CI | TESTS-7 owns the harness and the skip count; SHIPPING-2 the package job. One answer on node |
| TOOLS_BOTS-4, REMOVALS_2-2 | the reader of a call log | REMOVALS_2-2 (phase 1) builds read_calls for the file's form; TOOLS_BOTS-4 (phase 5) the meaning of a row, beside it, not a second file reader |
| TESTS-5, TOOLS_BOTS-6; BUDGET_FLOW-8, TASK_FAILURE-8 | land together | adjacent in phases 20 and 9 |
| FIGHT_CORE-2, FIGHT_ABILITIES-1 | in_fight(f) | FIGHT_CORE-2 owns it in engine/combat.py |
| FIGHT_CORE-3, FIGHT_ABILITIES-4 | the floors table | FIGHT_CORE-3 owns stages.yaml's table; FIGHT_ABILITIES-4 is one more column, one question |
| STARTUP_DATA-16, FIGHT_ABILITIES-13, REMOVALS_1-14 | code-held fight numbers | one answer; STARTUP_DATA-16 owns the move |
| CONTRACTS-4, PEOPLE_TALK-5, BUDGET_FLOW-8 | PersonaDetails' count and its said forms | CONTRACTS-4 sets the count from data first; PEOPLE_TALK-5 adds the said list held to it |
| CONTRACTS-15, PEOPLE_TALK-10, REMOVALS_1-19 | the profile request and its saved columns | PEOPLE_TALK-10 owns has_motive; CONTRACTS-15 the fields; REMOVALS_1-19 the columns, last |
| CONTRACTS-17, doc 29 R2 | per-call shaping of a contract (R2's plan_contract(offered) by hand) | CONTRACTS-17 owns the step; its design must list plan_contract among the hand-built forms (act.shape, decision_contract, many_reply, reply_contract) to move onto it, or R2 is a second shaping mechanism |

Same files, no conflict but an order: SUITE-2, SHIPPING-3, REMOVALS_1-12, LONG_SAVE-6 all edit llm/audit.py (phases 5 then 6, in
that order); GATE-19, REMOVALS_2-7, STARTUP_DATA-6 all edit sampling.yaml (13, 18, 19); TESTS-10, GATE-16, STARTUP_DATA-11 and
FIGHT_ABILITIES-4 edit tools/purity.py (FA-4 lands in phase 2, so TESTS-10 in phase 8 must keep its path); RELOAD-6 before
GATE-12 (the worn words are kept before what is counted changes); RELOAD-9's yield question becomes a standing question that
FIGHT_SCENE-3's table must list; CONTRACTS-12 and PEOPLE_TALK-14 both change Sworn Enemy at creation (tier, then subject).

## 2. Needs no feature states

- GATE-20 needs STARTUP_DATA-8's named list (or they share one helper).
- PEOPLE_TALK-14 needs GATE-5's engine/wordlist.py, with a word-start mode.
- SITUATIONS-17, STALE_COPIES-12 and FIGHT_CORE-9 need one fence, acting_character_630_test.py, not a second count in actor_632.
- RELOAD-11 needs TOWN_SERVICES-8 (same function; the cooldown answered once).
- Doc 29 R2 needs CONTRACTS-17, or CONTRACTS-17's design names plan_contract.
- STALE_COPIES-11 is a family of BUDGET_FLOW-10, and needs its asked_outside reading.
- BUDGET_FLOW-27 option (b) needs BUDGET_FLOW-10 (its own text says so in passing; it is placed four phases earlier).
- TYPED_LINE-3, -4, -5 and -8 (and TRAVEL_PLACES-5, -9, -10, TOWN_SERVICES-4, -5) need the owner's word that they are not the
  "fix rounds for misread lines" stopped on 17 November; only TYPED_LINE-6 and -7 ask it.
- TOWN_SERVICES-4 builds half of doc 05 step 4, which doc 20 left for "a plan of its own": it needs that plan's approval
  (CLAUDE.md: plan first past two modules).
- TASK_FAILURE-9 and doc 31 f732 change the same lines (scenes/world.py:3665-3682); BUDGET_FLOW-15 and doc 31 f731 change the same
  townsperson request and brief.yaml, and are measured in one gate run.
- CONTRACTS-1's reply_contract is where doc 30 Part 3 (the reply in two fields) would go.
- BUDGET_FLOW-3 (new embed numbers in data/runtime/server.yaml), BUDGET_FLOW-26 (reads server.slot_ctx) and STARTUP_DATA-7 need
  the owner: the project forbids reading that file, and GOALS.md (phase 3's row) still has the owner confirming what it holds.
- TOOLS_BOTS-4 needs REMOVALS_2-2's read_calls beside it.
- TRAVEL_PLACES-4 and LONG_SAVE-4 each move stub_short and want "one pass"; FIGHT_SCENE-5 and LONG_SAVE-3 want one recording. The
  order puts the crash fixes first, so each pair costs two re-blesses unless the owner pulls LONG_SAVE-1 and -4, or holds LONG_SAVE-3.
- Plans 29 and 31 and CONTRACTS-1 (the model-settings trial calls it f731) all claim f731.
- SUITE-1, -3, -5, -6, -8, -9 and -12 edit the owner's .claude files and CLAUDE.md: one go for all.

## 3. The phases

Criteria, in the task's order: (a) stops the game, loses a save or a player's progress, or breaks the minute on the minimum card;
(b) needed before the next released build; (c) small instruments ahead of the fixes they would find; (d) small certain fixes;
(e) savings in what the model writes and reads, batched by card session; (f) no change of behaviour; (g) designs. Inside a phase,
keys are in build order. A dependency moves a key earlier than its criterion only where named.

1. **Stops the game or loses a save** (18). The heavy rows 5, 6 and the seven small certain bugs; the road stop that strands a
   player and the save that will not open; a tool or the home page losing a game; a failed call that stops a new game. TESTS-1
   and REMOVALS_2-2 lead: the first makes every "the goldens do not move" true, the second makes the re-blesses of this phase and
   every later one cost a delta (skip it if the owner chooses (c)). All stub; no card.
2. **The fight** (14). Rows 3 and 4: a fled foe striking, a dead one dying twice, a rank won by a summon losing. FIGHT_CORE-9's
   fence first so the new code is counted; FIGHT_CORE-5 then -1 so stub_fight is re-read once. One live gate run covers FC-1,
   FC-5 and FA-5's lines.
3. **Close and reopen** (14). RELOAD-1 is the instrument (heavy row 7 and the scene's lost talk are what it catches) and comes
   first; then the fight's purpose, the attribute point, the talk, the yield, the input's count, the telling's memory.
4. **Progress lost outside a fight** (17). STALE_COPIES-1's check first, then each fix takes its site off its list; heavy row 8
   (SITUATIONS-4); coin paid for nothing; jobs and commissions lost.
5. **The 60 second turn** (24). Heavy row 11: CONTRACTS-1 is the only single call over 60 s; BUDGET_FLOW-1, -2, -3, REMOVALS_2-3
   (a 114 s call) and GATE-6 (up to five answers of 25 to 60 s). Row 9 (CONTRACTS-3, no find ever accepted) rides with it as the
   audit's own order asks. Small instruments lead because this phase is judged on the card: the gate's exit code, the logs'
   folder (SUITE-9, -1, -2, which also stop a suite run trimming the owner's play logs), a run's own rows, and the call-row
   reader and wait times the minute is read from. CONTRACTS-2 is the measure the contract changes are kept by. One card session.
6. **Release (1)** (13). Heavy row 10: a built game cannot start. SUITE-12 leads because this plan and docs 26 to 32 are
   untracked. Logs beside the exe, capped; the update switch; faults written down (TASK_FAILURE-2, which three later phases
   use); the embedder after Try again; what the build hashes.
7. **Release (2)** (17). CI builds, installs and starts the game (needs TESTS-2 and TESTS-7 first); a failed start is told; one
   way of leaving; the installer proven and complete; markup injection. Lowest weight last.
8. **Instruments** (19). What phases 9 to 16 are measured by: the bench and its rows, zeros never measured, the typed-line
   counts (TYPED_LINE-1), creation and the lesson recorded, the slot numbers (BUDGET_FLOW-12 answers the f536 open question), the
   contract floor test, the fences that see too little, the number count, the first-player counts.
9. **Failed model calls** (18). Built against the task matrix (TESTS-3), which needs TESTS-6's script. A lost passage that
   tells a no as done, a lost round, a search taken back, once-only writings, broad guards.
10. **Typed lines and carried things** (18). Coin and standing taken on a suspicion, a fine on a misread answer, numbers in
    words, the wrong thing sold. Subject to the 17 November stop (see section 5).
11. **The fight's remaining faults** (10). Steps told truly, one price and payer, locks, the command table, captives' labels.
12. **Small certain fixes** (18). Situations, people, town, field abilities, small savings with no measure (BF-24, BF-25).
13. **Savings (a), the checks** (20). GATE-1 alone removes about 215 of 556 second calls. Mends before the gate, false alarms,
    the narrator's rewrites. Card session 2.
14. **Savings (b), the contracts** (13). Bounds in the grammar, the shaping step, ids from the call. Card session 3. One
    re-bless of every golden with BUDGET_FLOW-11, back to back with CONTRACTS-6.
15. **Savings (c), the speaker's request** (16). With doc 28's switch and doc 31 if approved; one gate run for the leaks.
16. **Savings (d), the background lane** (10). Withdrawable jobs, creation's abilities while the class is read, births and
    people ahead (both on the owner's word), the arrival's tellings out of the transaction.
17. **A long campaign stays flat** (14). The store registry, caps, the route cache, narrow reads.
18. **Removals (1)** (15). The census, then the sweeps. Moved after the savings by the criteria; the removals workstream wanted
    its 130-file import sweep first, which the owner may prefer (it only edits imports).
19. **Data** (17). The key check, then the moves in one data-hash batch with the removals that edit the same files.
20. **The suite and the bot** (14). The quick run from git (the heaviest suite fix), its fences, the push marker, the width,
    the balance bot playing again. The owner may pull SUITE-3 and SUITE-14 to just after phase 7: they speed every Stop.
21. **Night tools and tidying** (13). The clean-up last, after nothing grows back.
22. **With plan 29, and the designs** (9). See below.

### Where the designs and this plan sit

- Phases 1 to 7 go before any more of phase 4 (doc 28 Part B, combat onto the one ruling) and before plans 29 and 31: they are
  faults in the game played today and in the next build. The decision of 17 November ("let's do your 5 infrastructure changes now
  then begin with phase 4") did not foresee them, so this is the owner's call.
- Doc 29 R1 (one corpus run) fits in card session 1 or 2; TYPED_LINE-2 parts 1 to 3 and CONTRACTS-16's measures are R1's.
  TYPED_LINE-9 part 2 after R1; BUDGET_FLOW-13 with R2; FIGHT_SCENE-6 is R4. CONTRACTS-17 (phase 14) should precede R2.
- Doc 31: GATE-21 inside f731; BUDGET_FLOW-15 measured with it; TASK_FAILURE-9 beside f732.
- TYPED_LINE-12 (the step, not the line) after R1 to R3, before or after phase 4 by the owner. FIGHT_CORE-8 is phase 4's can_take
  in narrow form (GOALS.md:177 puts combat states in phase 4). STALE_COPIES-13 and LONG_SAVE-17 feed multiplayer M1 (roadmap
  phase 5); STALE_COPIES-13 is written only if a night's lists from STALE_COPIES-1 say so.

### Card sessions

Seven phases need the model: 2 (one gate run), 5, 8 (BUDGET_FLOW-12's nights, BUDGET_FLOW-6), 13, 14, 15, 16. Phases 13 to 15
can share one session if built back to back; the minimum card's seconds remain priced from tokens until a timed 3060 night.

## 4. Questions for the owner

Gathered from all 153 features that ask; merged where two ask the same. The list is in the returned data (owner_questions). The
heaviest for the order itself: where this plan sits beside phase 4 and plans 29 and 31; the 17 November stop and the typed-line
fixes; the f731 number; the node question; the .claude files; one reading sitting for every new line a player sees.

## 5. Where the plan pulls against GOALS.md or the ROADMAP

1. **Phase 4 next.** GOALS.md (17 November) puts phase 4 after the five infrastructure changes. 341 features is several months;
   phases 1 to 7 are about 120. The owner must place them.
2. **"Fix rounds for misread lines stop"** (17 November). Phase 10 changes repairs and handlers that read the typed line. Most are
   the engine's own reading of the player's words (coin, numbers, an answer to the game's question), not the model's misreads,
   but TYPED_LINE-6 and -7 narrow existing repairs and ask; the rest should be asked the same.
3. **Sampling "Keep them as they are"** (GOALS.md:249): CONTRACTS-2 (a grammar rule in the sampler chain), GATE-19 (b), GATE-23,
   STARTUP_DATA-7 (b), BUDGET_FLOW-12 (b, a third slot against the two slots of GOALS.md:192), STARTUP_DATA-6 (the row is wrong).
4. **Code-held fight numbers wait for the balance pass** (2026-11-04): STARTUP_DATA-16 (b), FIGHT_ABILITIES-13, REMOVALS_1-14.
5. **Births asked after the line** (f597, f599): BUDGET_FLOW-19 (b). **The ask-back for a ruling** (f332, GOALS.md:182):
   TASK_FAILURE-11. **With the switch off no request changes** (f726): PEOPLE_TALK-16 (b), half of BUDGET_FLOW-15.
6. **data/runtime holds the server's launch settings** (GOALS.md:192): SHIPPING-4 and -17 put the window there; BUDGET_FLOW-3
   puts embed numbers in server.yaml, which no builder may read.
7. **Doc 20 (approved)**: TOWN_SERVICES-4 builds half of doc 05 step 4, left for its own plan; REMOVALS_1-17 and 2-4 reverse its
   plan for the old layout.
8. **Earlier review answers**: Q28 against D7 (SITUATIONS-6), Q20 against f420 (PEOPLE_TALK-6), Q15 (LONG_SAVE-4, TRAVEL_PLACES-3),
   Q30 (LONG_SAVE-7, -17), "Cooldowns stay" (RELOAD-11, TOWN_SERVICES-8).
9. **Stale saves ruled one by one** (2026-11-10): STALE_COPIES-13 would replace it; recommended to wait for the lists.
10. **Goldens**: about 45 features say they move a golden and about 50 more may. Each is intended and explained, never to pass;
    batched per phase, REMOVALS_2-2 first. FIGHT_ABILITIES-14 builds ahead of M1, which doc 20 left for M1.
11. **New lines a player reads**: about 30 features add some; the owner reads them first (GOALS.md:192, the human author's voice
    of f711). One reading sitting per phase keeps the builds moving.
12. **CLAUDE.md, plan first past two modules**: approving a phase can stand for the plan of its M features; the L features
    (CONTRACTS-17, GATE-7, GATE-23, BUDGET_FLOW-2, -10, -13, -20, FIGHT_CORE-1, -8, TESTS-3, STARTUP_DATA-3, FIGHT_SCENE-6,
    STALE_COPIES-13, LONG_SAVE-17, TYPED_LINE-12) each need a design read first.
13. **The 3060 itself**: GOALS.md asks for a timed night on a real minimum card; the audit priced it from tokens and the reading
    rate is uncertain by a factor of three. Phase 5 is only proven when that night is run.
