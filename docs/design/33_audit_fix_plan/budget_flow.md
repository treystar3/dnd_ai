# budget_flow: When and how the model is called

This workstream makes the turn's arithmetic true (every try asked, a cut try charged, a request priced as a base plus a rate), ends the model calls and waits the budget cannot see (embeds with no deadline, the pane walk's arrival, people asked for before the budget opens, a wait on a background job), and moves model work that need not sit in a line out of it (creation's abilities, births, the first people of a place the engine already knows is next). It builds seven pieces of infrastructure: one question the gateway asks before any later try; a card profile fitted as base plus rate by a tool that cannot write a broken file; a bounded, checked embed call; a ratchet that no main-thread call runs with no budget open; a worker that can withdraw one job; a recording that walks creation and Maren's lesson so their sizes are measured and not guessed; and a count of whole reads a plain line makes that may only fall. The prompt work (the interpreter's order and place list, a hire's description, a townsperson's request, system cards, whole-world lists) is planned as changes to what the engine sends, each measured before it is kept, and most of it rides on steps already in docs 09, 28 and 29. It leaves to the owner: the real 3060 night (GOALS.md line 205), the third slot and the checkpoint count (the f536 question), where a place's missing first people are asked for, whether a failed residents call takes the walk back, whether births leave the line for the background lane, the faith paragraph, the place-name warm-up, and the wording of any new script line. One rule holds for every feature below that says "Data hash: yes": a change under data/ (outside data/replay, data/measured and data/runtime) moves the hash the three goldens carry, so all three are made again for the hash (tools/sim/budget_data_459_test.py :94, isolation_456_test.py :127; the rebless skill, step 5) even when no recorded row changes.

## Features

### BUDGET_FLOW-1. Every try of a model call is asked of the budget, and a try cut at its deadline is charged what it was handed
- Fixes: min-card-1, min-card-3
- Pillar: 7 Easy and comfortable to play (the 60 second turn on the minimum card, GOALS.md lines 205-206); checklist 4, 5, 7
- Kind of case: any second request the gateway sends for one call (a retry, the relaxed pass, a send-back) and any try lost to its deadline, where today the turn's arithmetic is not asked or is told the wrong cost.
- Build: In engine/budget.py give Budget one method the gateway asks before every try after the first and before the relaxed pass (llm/gateway.py :197-198 and the loop at :239): the arithmetic of allow(), not the kept verdict of the asked-outside path, so a rerun answers the same. When it says no, the call stops trying and takes the road its need already has in data/rules/budget.yaml (required: BudgetSpent and the site's written fallback; optional: Deferred or Dropped). That refusal is raised between tries inside _generate, where generate()'s `except LLMError` would today answer it with the relaxed pass, a FALLBACKS entry and a model_down or bad_answer refusal: the build lets it out as the budget's own error (no relaxed call, no refusal filed, the failed tries still tallied, the turn log naming the budget). On a failure named deadline, charge the limit the try was handed through one Budget method instead of the expected size (:263); deadline is already in ENDS, so a cut try has no later try and the charge is the only change there; under SLOW, where there is no limit, the expected size stays. The stiff send-back already asks room_for_passage() at :359; point it at the same method so there is one question. Before giving a reply up for lack of room, check the draft in hand once under the relaxed context, which costs no call: the checks of :312-381 are lifted into one function that both passes call, never copied. No new number is needed (the floor and the reserve that deadline() and room_for_passage() read exist already). A switch in the recording's meta, as budget_cached was, keeps recordings made before it replaying on the old arithmetic.
- Test first: tools/sim/budget_tries_test.py, started from audit/work/min_card_budget_gaps.py: today a narrate whose first try fails with 7 s left gets a second try at the 8 s floor (worst case about 87 s for the line), and a try cut at 20 s is charged its expected 6 s. Second case: an optional exchange on its relaxed pass and a reply's send-back are each refused once the room is gone, the refusal files no model_down row and the failed tries stay counted; and an old recording's meta replays the old arithmetic (extend tools/sim/budget_468_test.py and budget_cached_538_test.py).
- Recordings: maybe: all three goldens hold failed tries (interpret_action in stub_short, npc_conversation in stub_party, combat_interpret and combat_narrate in stub_fight), so the new question would be asked in each; they carry the switch off and replay unchanged, and take the new arithmetic at their next intended rebless. None holds a try cut at a deadline. Data hash: no (no key is added; if the build finds it needs one, it goes in budget.yaml and the three are made again for the hash).
- Measure: none (stub suite); tools/latency.py --gate on the next night shows whether any line still passes 60 s.
- Size: M
- Needs: nothing
- Touches: contracts, task_failure, gate (GATE-2 keeps a checked draft whose rewrite failed: the same lines), tools_bots (TOOLS_BOTS-5 reads the same rows)
- Owner decides: nothing

### BUDGET_FLOW-2. The card profile prices a request as a base plus a rate, and the tool cannot write a profile the game cannot load
- Fixes: engine1-1, min-card-4, tools1-7
- Pillar: 7 Easy and comfortable to play (the 60 second turn; GOALS.md line 205); infrastructure; checklist 4, 5, 7
- Kind of case: every price the budget makes from data/measured/card_profile.yaml: a batch priced as so many single requests (231 place names charged 34.65 s for a request of about 1 s), a per-request fixed cost scaled as if it were reading, and a profile file that holds the word None.
- Build: tools/card_profile.py measure() fits reading as a per-request base plus a rate and an embed as a base plus a per-text marginal, scaled() scales only the rates by the card's figures, and it says so when its rows have no batch large enough to fit a marginal (the old number stays). scaled() does not scale an embed row at all today (only a chat row's read_ms and write_ms), so the design says what carries an embed's fit to the 3060 and prints it as an estimate. write() uses yaml.safe_dump, refuses --write when a rate is missing or not above zero, and drops the load measure (with the Loads column of tools/latency.py :78 and tools/rerun.py :505-506, :524-525). engine/budget.py load_profile() takes only numbers above zero and names a bad one at startup instead of failing float() at import; estimate() and Budget.embed() read base plus rate. Every place that holds the profile's keys learns the new ones: DEFAULT_PROFILE, priced, engine/recording.py :124 (the meta), tools/nightrun.py :231, tools/latency.py priced_at. tools/rerun.py replay() only updates the keys a recording has, so for a recording whose meta lacks the new numbers it clears them, or an old golden would be priced with the tree's base and marginal. engine/data_check.py checks the profile's shape. data/rules/cards.yaml gains the 4070 Ti SUPER (with its patterns entry) so the tool prints the spread between source cards (271 to 935 tokens a second for the 3060 today); that needs several source recordings handed to one run, not only the row. engine1-1 is mended in play only when the tool has rewritten the profile with a measured embed base and marginal; until then the 231-text batch is still charged 34.65 s. The rate itself waits on the real 3060 night, which is already the owner's plan.
- Test first: tools/sim/card_profile_fit_test.py, started from audit/work/tools1_card_profile.py and min_card_reprice.py: today a 231-text batch is charged 34.65 s and leaves 0.35 s for an optional call, and a profile written from a recording with no load row crashes the game's import. Second case: a three-text people_by_meaning batch and a 5,000-token reply prompt priced as base plus rate, and a recording with the old meta priced to the same second as today while the tree's profile holds the new numbers (tools/sim/card_profile_443_test.py :34 changes with the load measure).
- Recordings: no row moves (old meta, old price, once replay clears the new keys). Data hash: yes, by the new row in data/rules/cards.yaml, so the three goldens are made again for the hash; no, if STARTUP_DATA-8 has already moved cards.yaml out of the hashed tree. data/measured is outside the hash.
- Measure: the reading fit from the 44 tracked call logs under docs/measure (no card; the tool reads recording folders today, so it gains the reader tools/latency.py already has for call logs). No tracked log holds an embed row and no kept real-card recording holds embeds, so the embed base and marginal need one new recorded session with the embedder on (needs a model; the local card will do). The 3060's true rates need the card (the real-card night, owner's plan).
- Size: L: the design must settle how a base is told from a rate when a task's request sizes cluster (the least spread that allows a fit), what an embed's numbers are scaled by for the 3060, and how an old recording's meta is priced beside a tree that has the new keys.
- Needs: nothing
- Touches: tools_bots (TOOLS_BOTS-4 and -5 read the same rows), startup_data (STARTUP_DATA-8 moves cards.yaml)
- Owner decides: nothing (the real 3060 night is already decided, GOALS.md line 205)

### BUDGET_FLOW-3. An embed call has a deadline, and its answer is checked before it is kept
- Fixes: llm2-2, trace-threads-3, leftovers-6, llm1-6
- Pillar: infrastructure (the 60 second turn; "Nothing grows without bound"); checklist 4, 5, 7, 8
- Kind of case: the one model call that goes round the gateway: an embed request that may hang for the 120 s guard inside a line, and an answer (short, empty, null, zero) that is cached or raises out of the turn.
- Build: llm/backend.py embed(texts, deadline=None) through every source: NoServerSource, StandIn and Unstarted (llm/backend.py), the replayer (tools/rerun.py :295, which takes the argument and leaves it out of the row's fingerprint), llm/llama.py :429 (it passes None today, which request() turns into the 120 s guard), the runtime's wrapper (llm/runtime.py :1120) and embed_call (:824), whose restart of a dead embedder is bounded by the same limit, and the tests' fakes (tools/sim/failure_kinds_516_test.py :272, :422). llm/embed.py vectors() passes budget.deadline() when the caller's budget is open, else a short limit; under SLOW the hang guard stays. The two new numbers (the short limit, and the failures in a row before embeddings go off for the session) are wall-clock numbers of the server, so they live in data/runtime/server.yaml's embed section beside max_chars, checked by llm/runtime.py runtime_problems, as the findings asked and as Bundle F's decision places such numbers (GOALS.md line 192); a source that states none (a stand-in, a replay) goes off at the first failure as today, so no replay can part. A deadline is that call's own fallback (callers already take None). One check in vectors() before anything is cached: the count asked for, no empty row, one length, every number finite, a norm above zero; a bad answer returns None and counts as a failure. The normalising (:86) moves inside the try, and the answer is built from a local dict under one lock so another thread's trim cannot raise KeyError (:89). The off switch is one for the process today; note it against checklist 8 where doc 17 line 130 already lists it.
- Test first: tools/sim/embed_bounds_test.py, started from audit/work/check_trace_threads_3_embed.py: today a request held past the turn's deadline holds the line with the deadline ignored (held on tools/sim/fake_llama.py: a stand-in's embed function cannot be cut), and a row of nulls raises TypeError out of vectors(). Second case: a short count, a zero vector, and a trim on a second thread racing a read; tools/sim/embed_review_524_test.py still passes with the bounded restart.
- Recordings: no: stub_party's 41 embed rows (one of 203 texts) all pass the new check (one length, none empty or zero), and the deadline is not in a row's fingerprint. Data hash: no (data/runtime is outside it).
- Measure: none (stub suite)
- Size: M
- Needs: nothing
- Touches: task_failure, startup_data, shipping (SHIPPING-12 brings the embedder back on Try again: the same off switch), tests
- Owner decides: nothing

### BUDGET_FLOW-4. A pane walk's arrival runs inside the command's input, and a ratchet names every main-thread call or wait made with no budget open
- Fixes: world_py-3
- Pillar: 7 Easy and comfortable to play (the 60 second turn); infrastructure; checklist 4, 7, 8
- Kind of case: work the player waits for that runs outside any input, so no budget, deadline or log row covers it: today a pane walk's arrival ticks (close_input calls pane_arrival after the input has closed), and the two holes BUDGET_FLOW-27 closes.
- Build: scenes/world.py: the pane arrival runs inside command_input's input (a command opens a budget as a line does, input() :1074), as asked_operation('tail', ..., world=True) followed by run_passages(); play() hands it where the character stood. It cannot simply call turn_ticks: said_nothing, the turn count, resume_road and the hire's said marks are the typed line's. So the ticks become one declared list, each marked as every arrival's or the line's alone, read by both; today's hand-made subset (pane_arrival :1975-1991: sync_heard, orenna_tick, mentor_tick, quirk_tick, banter_tick, heard_flush) cannot then drift. Each tick a pane arrival gains from the list (run_deferred, collapse_check and stay_tick are the candidates) is a change in play, named in the feature and pinned by the test. The ratchet: beside operation.note_legacy in llm/gateway.py, and at backend.waiting for waits, note any main-thread call or wait made with no budget open once the loop has begun (a mark set when run() reaches its prompt: the opening has no budget by design, doc 27 f721). It starts as a named set that may only shrink (the pattern of RECORDED in tools/sim/prepared_470_test.py), holding exactly the two holes of BUDGET_FLOW-27; it is not asserted empty here. tools/sim/turn_driver_721_test.py reads the driver's code and must still find one of each. New code reads the place from the acting character, not self.player.
- Test first: tools/sim/no_bare_call_test.py, started from audit/work/world_py_pane.py: today a #goto walk with a hire along makes exchange, canon_extract and dialogue_frame calls with the budget closed and the transaction open. Second case: a different pane walk (#mapgo) is covered by the same driver, a command that moves nobody (#stats) makes no arrival work, and the ratchet's set equals the two named holes. Add the pane walk to tools/sim/prepared_470_test.py.
- Recordings: no: no golden holds a pane walk (their only commands are #stats and #useitem healing draught, and pane_arrival returns at once when nobody moved). Data hash: no.
- Measure: none (stub suite)
- Size: M
- Needs: nothing
- Touches: typed_line, travel_places, tests, task_failure (TASK_FAILURE-5 changes said_nothing in the same ticks)
- Owner decides: nothing

### BUDGET_FLOW-5. The worker can withdraw one job, and the save's one background job follows the player
- Fixes: llm-flow-4
- Pillar: 4 People who feel like people (a town is played with its people in it); infrastructure; checklist 4, 5, 8
- Kind of case: background work planned for a place or a choice the player has since left, which today cannot be taken back and runs two minutes late beside a turn.
- Build: llm/worker.py gains a cancel for one thread's call, waiting or in flight, as one atomic backend.withdraw(thread) that says whether it took: a waiting call is dropped and its thread told; a call in flight is cut the way a foreground call already cuts it, and not sent again. Today only cancel_session and close cancel. npc/backfill.py uses only the waiting case: when the save's one job is still waiting for a place the player has left, start() withdraws it and plans the present place; a job already sent is left to end (the owner's rule on running beside the turn stands) and populate_place plans the other place afresh on the way back. The withdrawn thread's Cancelled passes backfill's `except Exception`, done is set and nothing is applied. One job a save stays as the cap. BUDGET_FLOW-18 uses the in-flight case. For scripted measures the change is in tools/nightrun.py's script mode (what tools/live_gate.py :120 plays): it takes background people in at each input's edge, without setting streams.STRICT whole. The save's key and the acting character are passed in, not read from self.player.
- Test first: tools/sim/backfill_follows_test.py, started from tools/sim/backfill_test.py and worker_523_test.py: today a second start for a new place returns False while the left place's job waits, and that job is sent after max_wait beside a turn. Second case: a job already sent is not withdrawn by backfill and is applied on return; a withdrawn job's thread ends and nothing of it is written; a call in flight withdrawn by name is cut and not sent again.
- Recordings: no: the background lane is off in every golden (each meta has backfill None, and simlib sets life.FIRST_BATCH None). Data hash: no.
- Measure: the live gate's turn seconds before and after (needs a model; the local card will do).
- Size: M
- Needs: nothing
- Touches: gate, tools_bots (TOOLS_BOTS-5 changes the worker's hand-back), people_talk
- Owner decides: nothing (running beside the turn after the wait is decided, GOALS.md line 192)

### BUDGET_FLOW-6. A recording walks character creation and Maren's lesson, and mentor_chat's ceiling is written from it
- Fixes: unmeasured-tasks-12, aged-save-10
- Pillar: infrastructure (measured, not guessed; data/measured is written by tools only); checklist 4, 5, 7
- Kind of case: tasks no night ever plays, so their expected sizes and prompt ceilings are guesses or come from a fixture: the ten calls of creation, the mentor's tasks, mentor_chat's 11,500.
- Build: tools/nightrun.py: a script's setup may ask for the lesson, which leaves ws.player.mentor["never"] unset (:666), and the help text at :20-21 is made true. A second script beside data/replay/gate_script.yaml plays the lesson through, and talks to Maren again after the town has been walked, where her request is at its largest (about 16,100 characters against about 11,300 at the start), or the ceiling is written too low. A scripted creation pass drives scenes/goddess.py from the class reading to the passives; creation is before the campaign's recorder (nightrun's character comes from simlib.make_character :649), so its call log is what is read. tools/latency.py --ceilings then writes mentor_chat's ceiling from the run. This feature produces the recording and that one ceiling; the creation and mentor rows of the budget are written by BUDGET_FLOW-11's tool from the same run. Nothing in data/measured is edited by hand. New lines: the owner reads them first.
- Test first: tools/sim/nightrun_lesson_test.py, started from audit/work/unmeasured/m_lesson.py and m_newgame.py: today a scripted run can make no mentor_chat call, because the setup turns Maren off. Second case: the creation pass logs generate_actives and the passives job with their written sizes, under the stub.
- Recordings: no golden moves (these are measure sessions, not goldens). Data hash: no (data/replay and data/measured are outside it).
- Measure: one local recorded run of the lesson and of creation (needs a model; the local card will do; priced for the 3060 by the profile).
- Size: M
- Needs: nothing
- Touches: tools_bots, tests
- Owner decides: the lesson script's lines (the owner reads them first)

### BUDGET_FLOW-7. One of Maren's lines takes one ladder: free speech once, the written line re-voiced only while there is room, else as written
- Fixes: unmeasured-tasks-6
- Pillar: 7 Easy and comfortable to play; 4 People who feel like people; checklist 3, 4
- Kind of case: a speaker's line that falls back through several model tasks in turn, each with its own retries (up to six tries for one line at ten call sites).
- Build: scenes/mentor_actions.py: one method holds the ladder the ten sites of "if not self.mentor_speak(...): self.mentor_say(...)" spell out by hand (:426, :440, :445, :463, :529, :534, :610, :809, :867, :882): mentor_speak once; on failure the written line through at most one mentor_voice pass, and only while the budget says there is room (budget.room_for_passage() today; BUDGET_FLOW-1's one question once it is in); else the line as written, which GOALS.md line 54 accepts. The ladder skips mentor_say's own free-speech try (:102) only when it has already made one; the many sites that call mentor_say directly (the parting words at :583 among them) keep their free speech, so mentor_say itself is not changed for them. The ten sites call the one method; no prompt changes.
- Test first: tools/sim/mentor_ladder_test.py, started from tools/sim/mentor_voice_test.py and audit/work/unmeasured/m_lesson.py: today a failing stand-in costs six tries for one line. Second case: with no room left the written line is shown and no mentor_voice call is made; a different pair site (the desk line, :610) takes the same ladder; a direct mentor_say site still tries free speech once.
- Recordings: no: no golden holds a mentor task. Data hash: no.
- Measure: none (stub suite); the lesson recording of BUDGET_FLOW-6 shows the ladder's real cost.
- Size: S
- Needs: nothing
- Touches: task_failure, people_talk, removals (REMOVALS_2-14 takes the two mentor switches out of the same lines, after this)
- Owner decides: nothing

### BUDGET_FLOW-8. A companion's new quirk queues its details for the tail and never asks at the line's first touch of the party
- Fixes: llm-rest-5
- Pillar: 7 Easy and comfortable to play; checklist 4
- Kind of case: an optional call made ahead of the telling the player waits for, because its site calls the task itself instead of using the deferred queue the turn already has. (persona_details is already asked outside the transaction, data/rules/budget.yaml asked_outside: the cost is the seconds before the narration, not a held lock.)
- Build: scenes/quirk_actions.py quirked() (:51-60) queues with self.defer("persona", {"member": id}) and calls nothing; run_deferred_one already knows the kind, and persona_details keeps its Deferred catch for the tail's own pass. defer() writes the save, and quirked() is reached from fourteen sites (habit lines, banter, hiring, the tail's quirk_tick): where the store is not writable (storage/campaign.py writable(), the fence armed and no operation open) quirked() leaves the member as it found them and the next call inside an operation queues them, so no caller can raise WriteOutsideOperation. The queue ages an entry out after three lines of the story and waits through a fight (run_deferred), so details queued at a fight's start would be dropped untried: this lands with TASK_FAILURE-8, which gives an entry a count of tries in place of that age. The line that gave the quirk is told without the details (an empty list is a state the talk copes with), which the test pins.
- Test first: tools/sim/quirk_test.py gains a case: today quirked() makes a persona_details call at the first line that touches the party, before the telling. Second case: two members quirked in one line queue two jobs and the tail runs them in order under the budget; a member quirked at a fight's start still gets their details after it; quirked() called with the fence armed and no operation open writes nothing.
- Recordings: yes: stub_party (three persona_details calls, inputs 1 and 2) and stub_fight (two, input 2) move the calls to the tail, and the hire_chat and exchange requests in between lose the details; rebless (intended: the order). Data hash: no.
- Measure: none (stub suite)
- Size: S
- Needs: TASK_FAILURE-8 (the same lines, and the tries that keep a queued entry alive through a fight)
- Touches: task_failure, contracts (CONTRACTS-4 moves PersonaDetails' schema in the same two goldens: one rebless), people_talk
- Owner decides: nothing

### BUDGET_FLOW-9. An input keeps its count when an operation fails before the line's first commit
- Fixes: trace-turn-4
- Pillar: infrastructure (engine/streams.py: two inputs never share a key); checklist 7
- Kind of case: a failure inside an operation that runs before anything of the line has committed, after which the line goes on under the previous input's count and the next input shares its dice key and operation ids.
- Build: The same change as RELOAD-10 (trace-save-4 is this place seen from the save): built once, under one feature number, whichever workstream reaches it first. scenes/world.py give_back() (:1597-1625) and understood() (:1693-1694): keep steps and story_steps across store.reload_meta(), as asked_operation already does after a stand-down (:1486); the clock and the turn still go back. The count is given back in one place, the close of the input, and only when nothing of the line committed. engine/recording.py :272 and tools/rerun.py :413 collect an input's operations by its count, so they are right again without change.
- Test first: RELOAD-10's tools/sim/input_count_test.py holds the cases, and gains this finding's (audit/work/trace_turn_demo.py case E) if it lacks it: today a waiting act's operation fails, the line's other operations commit under the previous count, and the same line typed again draws the same ids. Second case: a board refresh failing during the understanding; and the existing "count given back" case stays true.
- Recordings: no: each golden holds one line not taken (stub_short inputs 6 and 7, stub_party 13 and 14, stub_fight 5 and 6), nothing of it committed, and that path still gives the count back at the close. Data hash: no.
- Measure: none (stub suite)
- Size: S
- Needs: RELOAD-10 (the same build; this entry adds only its test case when RELOAD-10 has landed)
- Touches: reload, typed_line, removals (REMOVALS_2 edits the same lines' comments)
- Owner decides: nothing

### BUDGET_FLOW-10. Every model call of play is asked outside its operation's transaction, and the ratchet reads what play reaches
- Fixes: engine5-6, scenes1-8, scenes2-11, world_py-4
- Pillar: infrastructure (GOALS.md "How it is built"; multiplayer, checklist 8; doc 08 line 95); checklist 4, 7
- Kind of case: the f470 residue: a task still called with the save's transaction open, so the store's lock is held for the whole call and a later failure throws the answer away.
- Build: Already planned in part: doc 14 lines 35-37 and doc 08 line 95 name the residue. The audit adds the list and the hole in the ratchet. RECORDED in tools/sim/prepared_470_test.py holds eighteen tasks and every one is accounted for: narrate's inline uses are TASK_FAILURE-5's; pulse_motive is removed, not moved, by REMOVALS_2-5; the other sixteen are this feature's, family by family, each named in data/rules/budget.yaml asked_outside and dropped from RECORDED: moment, pulse_thread, pulse_cataclysm, thread_telling (engine/pulse.py :382, :728; engine/moments.py :142; engine/threads.py); camp_intent, discovery, arc_story (scenes/camp_actions.py :246, explore_actions.py :119, arc_actions.py :171); road_event, ruling and party_intent, which the plan had not named and whose sites the design lists (the goldens hold road_event inside action:move and party_intent inside the line's operation); plausible_object, stranger_read, board_stakes, lesson_want, generate_lessons, classify_field; and populate_place inside the walk (scenes/world.py :817), which is in neither list. Live reads that go into a request (store.npc_names(), the names and threads of a discovery) are kept with asked.compute so a rerun asks the same and does not stop as a Drift. The ratchet's own short session reaches almost none of these, which is how populate_place slipped it. A recording's call rows already carry the operation each call was made in, so the ratchet reads the three goldens' rows (and the world script's) with no model and no replay: a call whose operation is not a telling and whose task is not in RECORDED fails. engine/asked.py problems() already checks the list at startup.
- Test first: tools/sim/prepared_470_test.py: today it passes while a walk into an unpeopled place makes populate_place inside the move's operation (audit/work/check_world_py_1_ratchet.py and world_py_populate.py; stub_short holds four such calls in action:move). Second case per family: a moment on entry, a discovery, an arc story each asked with no transaction open, and a resident written between two attempts does not lose the line.
- Recordings: yes: an operation that stands down and reruns changes the order of calls and writes. stub_short moves for populate_place (four, in action:move), road_event (one, in action:move) and thread_telling (two, in the arrival); stub_party for plausible_object (one, in action:steal) and party_intent (two, in the line's operation); stub_fight holds none of the sixteen (its two inline narrate calls are TASK_FAILURE-5's) and is made again only for the hash. Each family's move goes through the rebless skill (intended: the call leaves the transaction). Data hash: yes (asked_outside in budget.yaml, intended).
- Measure: none (stub suite)
- Size: L: the design must settle the order of the families, which live reads each request keeps, what a failed call leaves behind in each, and how many reblesses the families are grouped into.
- Needs: BUDGET_FLOW-27 (it settles where the first people of a place are asked for)
- Touches: situations, travel_places, typed_line, task_failure (TASK_FAILURE-5 takes narrate), removals (REMOVALS_2-5 takes pulse_motive out of the same list), tests
- Owner decides: a failed residents call on a walk. (a) The walk is taken back, as data says today (populate_place is required). (b) The walk stands and the people come later, the road a load already takes (the f525 path, repopulate), in the spirit of Bundle C's "a committed action is never undone because its narration failed" (GOALS.md line 206).

### BUDGET_FLOW-11. Answer ceilings come from the engine's count, and the budget's expected sizes from recordings
- Fixes: llm-hot-14, logs-fields-8
- Pillar: 7 Easy and comfortable to play (the 60 second turn); infrastructure; checklist 4, 5
- Kind of case: a structured answer allowed to run far past what the task ever writes (3,000 tokens for residents that take 221 to 613; 700 for a reading that takes 253 at most), and the budget's expected sizes kept by hand.
- Build: The ceilings of structured tasks are computed, not typed: populate_place (npc/life.py :129) from the slots asked times a measured size a slot, the interpreter (scenes/world.py :3278) from the most steps a plan may hold, each number in data with headroom above the largest honest answer on record. A tool (tools/latency.py or a small one beside it) writes the expected answer sizes from recordings to data/measured, and engine/budget.py reads them with data/rules/budget.yaml as the value when a task has no recording. data/measured is outside the data hash, so the sizes a session priced with go into the recording's meta, as the card profile does, and a replay reads them from there (a recording without them takes data/rules as today); otherwise a tool run would move every golden's arithmetic with no hash to say why. engine/data_check.py checks both files. The bound on the interpreter's summary and the other unspoken strings is CONTRACTS-6's helper and is not built twice; this feature adds the one rule logs-fields-8 asks for: a bounded field that arrives exactly full is a runaway and is emptied, not kept (the readers fall back to the typed line). Narration and speech keep their runaway ceiling: no length limit on the narrator or a speaker. Doc 29 R3 raises the interpreter's answer budget (120 tokens today) in its own rebuild; the number is set there once.
- Test first: tools/sim/answer_ceilings_test.py: today the residents request for three slots is sent with max_tokens 3000 and the reading with 700 (22 s on the 3060 for the 4 of 2,481 readings that ran away in summary). Second case: a nine-slot place gets a ceiling that fits its largest recorded answer; a summary at exactly its bound is emptied and the plan still stands; a recording with no sizes in its meta is priced as today.
- Recordings: yes: max_tokens is in the request's fingerprint, so interpret_action moves in all three goldens and populate_place in stub_short; one rebless, best back to back with CONTRACTS-6's move of the same ActionPlan and ResidentSet requests (intended: the request's ceiling). Data hash: yes (ceiling keys in data/rules).
- Measure: tools/interp_eval.py --live before and after (needs a model; the local card will do); the sizes come from the tracked call logs.
- Size: M
- Needs: CONTRACTS-6 (the bound's helper). BUDGET_FLOW-6 only for the creation and mentor rows, which can follow.
- Touches: contracts, startup_data, typed_line, tools_bots
- Owner decides: nothing

### BUDGET_FLOW-12. Every night says what each slot kept, so the f536 question is answered from numbers
- Fixes: llm2-1, llm-flow-1, llm-flow-2, min-card-6, trace-threads-2
- Pillar: 7 Easy and comfortable to play (the 60 second turn on the minimum card); checklist 4, 5
- Kind of case: the shared slot's cold reads and unused checkpoints (92 of 105 requests read from the first token; 268 checkpoints made for 2 restores), known as an open question and not yet measured where it matters.
- Build: Nothing is flipped here: the RAM cache was measured and the owner kept it off (tools/sim/cache_shape_537_test.py :28), the 32 checkpoints stay (zero loses the understanding's restores), and admission in llm/worker.py does not change. tools/night_measure.py slots() already gives the understanding's slot its cached share and each slot its prompts, restores and whole re-reads; it gains the same share for the shared slot and by task, the count of calls whose system text differs from the one before on its slot, checkpoints made against restored with their seconds (read through the one parser tools/latency.py :308-311 already has, not a second), and seconds a background call ran beside a turn. One arm of three slots (the map is already data: slot_of, chat_argv) is read on a real 3060 or the pod for whether it still fits beside the embedder and what it saves (at most about 0.7 s a line for the narrator). The cost of a background call beside a turn goes under the same question; the lever there, smaller background calls a few slots at a time with the number in data, is a design step to measure first. The owner corrects the wording of the open question in GOALS.md (the 12 Nov report answered slot 0).
- Test first: tools/sim/slots_536_test.py gains a case: today slots() gives a cached share for the understanding's slot only, nothing for the shared slot or by task, and no count of checkpoints made (its marks are restored and whole). Second case: a three-slot fixture is read by the same code with no change.
- Recordings: no. Data hash: no (the tool writes to data/measured and docs/measure).
- Measure: a pod night or the real 3060 night with the three-slot arm; needs the card.
- Size: M
- Needs: nothing
- Touches: tools_bots (TOOLS_BOTS-5 adds the wait to the same rows), shipping, startup_data (STARTUP_DATA-7 states the cache's shape in the same settings)
- Owner decides: after the measure. (a) Two slots stay (GOALS.md line 192). (b) A third slot for the narrator or the townsperson's reply, about 1 GiB more VRAM on the 12 GB card. And whether checkpoints are counted again once BUDGET_FLOW-13 is in.

### BUDGET_FLOW-13. The interpreter's request puts what does not change first and lists places by what the words are about
- Fixes: llm-flow-3, llm-hot-9, llm-hot-8
- Pillar: 7 Easy and comfortable to play; 2 The game is a dungeon master (the reading of a line); checklist 4, 5
- Kind of case: the request every typed line sends: sections that change each line placed first and third (TIME opens it, PLACES follows), so the slot re-reads what did not change, and place tiers that send neighbouring towns' insides and a by-meaning pick on lines that are not about going anywhere.
- Build: Already planned: doc 29, step R2 (the request rebuilt behind data/rules/reader.yaml; waiting on the owner). The audit adds three things to that rebuild. scenes/world_prompts.py interpret_request orders its sections by how often they change, the order kept in data and taken from a count over recorded requests (how often each section differs from the line before on the tracked nights), not from a hand list: the catalogues (abilities, pack, recipes) are shown or left out by the words' meaning, so once the floor below works they change from line to line and belong after the sections that do not. engine/candidates.py places() gives the neighbouring towns' insides and the by-meaning tier only when the engine's own features say the line is about going somewhere; this is built with R2 and not ahead of it, because only R2's `named` field lets a place that was not offered still be reached, and a gate that guesses wrong before then loses the destination. A tool writes the similarity a line with no match gets to data/measured, and engine/data_check.py checks that place_floor and about_floor in data/rules/interpret.yaml sit above it (today the about floor passed every line of the played run). No rule is added to the prompt.
- Test first: tools/sim/interpret_order_test.py, started from tools/sim/candidates_test.py and interpret_outside_497_test.py: today two requests at one place differ first in TIME and PLACES, and "I look around" lists insides of neighbouring towns. Second case: a line that names a far place still gets it (the named tier is untouched), and a talk line at a second town shares its head with the line before.
- Recordings: yes: every golden's interpreter request changes, so all three are re-blessed once, with R2 (intended: the request's order and list). Data hash: yes (order and gate keys in data/rules).
- Measure: tools/interp_eval.py --live on the 252-case corpus before and after, and the cached share from BUDGET_FLOW-12 (needs a model; the saving, 0.4 to 0.9 s a line, is counted for the 3060).
- Size: L: the design must settle what "about going" is in the engine's terms, which tiers the gate takes out, the order once the floors are measured, and the accuracy the corpus must hold.
- Needs: doc 29 R2 approved by the owner (BUDGET_FLOW-12 first if the cached saving is to be shown)
- Touches: typed_line, contracts, tests
- Owner decides: build with doc 29 R2 when it is approved (recommended, for the reason in Build), or the order alone as its own step ahead of it.

### BUDGET_FLOW-14. A party member's description is kept in parts, and each reader is given its own
- Fixes: llm-hot-10
- Pillar: 4 People who feel like people (a townsperson is not told a stranger's temper); 7; checklist 4, 6, 8
- Kind of case: one description string built once and sent whole to every reader, whatever that reader may know or use.
- Build: scenes/party_actions.py :442 keeps the hire's parts apart (who and role, pronoun, look, manner) on the hire's view; engine/truth.py gives each reader its own: id, name, role and pronoun to the interpreter (scenes/world.py :3235; the pronoun is what settles "her" and "him" on a party member, so it stays), the look to a townsperson (truth.py :207), the manner to the narrator and the frame. The same lines send one string for Maren and for story companions (kinds maren and companion at :3235 and truth.py :207-212), so the view covers every kind of party member, not hires alone. The parts come from the engine's records by id, so a second player's party is served by the same view.
- Test first: tools/sim/truth_test.py and hire_brief_488b_test.py gain a case: today the interpreter's request holds each hire's Manner text (a fifth of the request with two hires) and a townsperson's request holds a stranger's rank and temper. Second case: the narrator's request still holds the manner; a story companion gets the same split; "I ask her" with one woman in the party still reads as her.
- Recordings: yes: stub_party and stub_fight both carry hires, so their requests with the party along change and are re-blessed (intended), best in the same rebless as BUDGET_FLOW-13. Data hash: no.
- Measure: tools/interp_eval.py --live for the reading and the live gate for the speakers (needs a model; the local card will do).
- Size: M
- Needs: nothing
- Touches: people_talk, typed_line
- Owner decides: nothing

### BUDGET_FLOW-15. A townsperson's request says each thing once, and the line of what else they know has a cap
- Fixes: llm-hot-11, llm-hot-12
- Pillar: 4 People who feel like people; "Nothing grows without bound"; checklist 4, 5
- Kind of case: a speaker's request that repeats what the truth view already says (about 1,000 characters) and carries an index of every other fact by id with no cap (50 slugs for an innkeeper).
- Build: Already planned: doc 28, step A4 (f726, built: the speak prompt behind the switch in data/rules/reply.yaml, off until the owner's blind reading) says the place once and drops the index line on that path. The audit adds two things. On the path the goldens and play run today, npc/prompts.py _identity (:397-408) leaves out YOUR PLACE and what is visible when truth_text is given, as it already leaves out HERE WITH YOU; this half is built only if the switch stays off after the owner's reading, since the new path does not have the repeat. engine/brief.py :62-64 caps the index line from data/rules/brief.yaml, choosing by the ranking lore() already computes, for every speaker that uses the brief; the cap is built either way. The label's words live in brief.yaml and a change to them is measured like any change to what the model is asked. The faith paragraph is the owner's (engine/faith.py says belief shows in passing).
- Test first: tools/sim/brief_486_test.py gains a case: today an innkeeper with 50 known facts gets 50 ids on one line and the place twice. Second case: a hire's brief is capped by the same key; a speaker with three facts is unchanged.
- Recordings: yes: stub_short (four townsperson replies) and stub_party (eight) change their requests if the place's repeat goes, and any brief past the cap changes; re-blessed (intended). Data hash: yes (the cap in brief.yaml), so stub_fight is made again for the hash.
- Measure: the live gate before and after, leaks and the reading (needs a model; the local card will do).
- Size: M
- Needs: nothing
- Touches: people_talk, gate
- Owner decides: the faith paragraph. (a) In every reply, as today. (b) Only when the line bears on it, as doc 28 line 286 lists as possible.

### BUDGET_FLOW-16. The speakers' system text is short and stable, and the frame's request carries no line for what was not given
- Fixes: llm-hot-13, llm-hot-15
- Pillar: 5 Writing a reader wants to keep reading; 7 (2.9 s of system text re-read for each townsperson reply on the 3060); checklist 4
- Kind of case: constant system text of 5,000 to 8,900 characters read again on nearly every call of the shared slot (46% of the session's reading), and request lines that say only that something is absent.
- Build: Already planned: doc 09, step A4 (system cards of about 1,500 characters; ROADMAP.md phase 1) and the slot plan; the cards are not rebuilt or re-planned here. The audit adds to that step the per-task numbers that order the work (npc_conversation 8,857 characters, then narrate 5,185, dialogue_frame about 5,050, hire_chat 5,676) and the note that order on the slot matters as much as size, which BUDGET_FLOW-12 counts. What is built here is small: a ratchet on each speaking task's system text length that may only fall, so A4's gain cannot leak back; and scenes/world_prompts.py :293 builds the frame's gesture line only when the engine has a gesture, so "none given" is never sent. That line is the only one of its kind (the other "none" lines tell the reader a fact it uses), it saves about five tokens, and it changes what the model is asked, so it lands in the same change as A4's frame card and is read in that card's measure, not on its own. The frame keeps its three passages until the prose baseline tools show its rewrite rate with one against three; a cut on reading time alone can cost a second call.
- Test first: tools/sim/frame_request_test.py: today a frame with no gesture carries the gesture line. Second case: a frame with a gesture is byte for byte today's; the ratchet fails when a speaking task's system text grows by a character in a test copy.
- Recordings: yes: stub_short's two frames are the only kept ones that say "none given", and move with the gesture line; each card of A4 moves every golden that holds its task, in A4's own reblesses. Data hash: no for what is built here.
- Measure: the live gate and blind pairs per card, then a pod night for the reading saved; needs the card for the timing.
- Size: S (what the audit adds; A4 itself is sized in doc 09)
- Needs: nothing
- Touches: people_talk, gate
- Owner decides: nothing new (A4's cards are read by the owner as doc 09 says)

### BUDGET_FLOW-17. No request carries a whole-world list: names come from near the matter, under a cap, and a clash is named by the check
- Fixes: data-7, engine7-2, unmeasured-tasks-8
- Pillar: "Nothing grows without bound over a long campaign"; 1 A world that is real; checklist 4, 5
- Kind of case: a request that lists every place, road, creature or resident name of the world so the model can avoid or use them, growing with the save and in one place cut mid-name at 3,000 characters.
- Build: engine/threads.py :524-525 drops PLACES and CREATURES from thread_telling (the check's known set already holds every name), and the sentence in engine/pulse_prompts.py that points at them goes with them. engine/discovery.py: a taken name becomes a contract failure with a send-back that names the clash (today make_place returns None at :68 and the find is lost silently), and only then is names() cut to the places within reach. engine/pulse_prompts.py place_context gives the places and roads of the band within reach; scenes/arc_actions.py dress_arc gives the names near the arc's places, with the clash named by its contract. One helper gives "names near here" under caps kept in data, checked at startup; no list is cut by character count. LONG_SAVE-12 uses the same helper for taken item names, so it is built to serve both. Count arc_story clashes on the kept nights before its list is cut.
- Test first: tools/sim/world_lists_test.py, started from tools/sim/tellings_498_test.py: today a telling's request on the 232-place world holds every place and a creature list ending mid-name. Second case: a discovery that picks a taken name is sent back with the name and lands; a pulse thread's request stays the same size when the world doubles.
- Recordings: yes: stub_short holds two thread_telling requests, each with both lists (4,206 and 3,011 characters), and moves; re-blessed (intended). No golden holds a discovery, a pulse thread or an arc story. Data hash: yes (the caps).
- Measure: a scripted night (tools/nightrun.py --script) counting send-backs and clashes before and after (needs a model; the local card will do).
- Size: M
- Needs: nothing
- Touches: contracts (CONTRACTS-3 shapes the discovery's answer), situations, travel_places, long_save (LONG_SAVE-12 shares the helper)
- Owner decides: nothing

### BUDGET_FLOW-18. Creation's abilities are written while the player reads the class, not after they confirm
- Fixes: unmeasured-tasks-1
- Pillar: 7 Easy and comfortable to play (about 30 s of waiting at the confirm on the minimum card); checklist 4
- Kind of case: model work whose request is fixed some moments before its answer is needed, asked in the foreground at the moment of need.
- Build: character/creation.py gains an ActivesInBackground job on the pattern of PassivesInBackground (:90): scenes/goddess.py read_class starts it once the class is read, on_confirm_class (:478) takes its result (the typed confirm promotes the job, and a failed job is asked again in the foreground as today), and a decline withdraws it before read_class starts the next. The job starts at once in the reading time, so at a decline it is in flight, not waiting: it needs the in-flight case of BUDGET_FLOW-5's withdraw, or the old class's abilities go on being written beside the new reading. A fault in the engine's own plan of the abilities must still reach the scene as REMOVALS_2-3 leaves it (the gifts line, a second yes plans again), not be swallowed by the job's second try. The session owns the thread as it does the passives job.
- Test first: tools/sim/creation_passives_test.py gains a case, started from audit/work/unmeasured/m_newgame.py: today generate_actives is a foreground call after the confirm. Second case: a decline and a second class leaves no job of the first running and none of its calls sent again; a job that fails falls back to the foreground ask.
- Recordings: no (creation is before any turn and in no golden). Data hash: no.
- Measure: the creation pass of BUDGET_FLOW-6, seconds from confirm to the abilities shown (needs a model; the local card will do).
- Size: M
- Needs: BUDGET_FLOW-5
- Touches: task_failure, removals (REMOVALS_2-3 changes generate_actives' failure path)
- Owner decides: nothing

### BUDGET_FLOW-19. A situation's birth is written on the background lane and taken up at the next input's edge
- Fixes: llm-flow-5
- Pillar: 3 No two runs alike; 7 Easy and comfortable to play; checklist 4
- Kind of case: world work nobody is waiting for that is asked in the foreground at the end of a line.
- Build: Already planned: doc 14, section 8, line 298 (births on a background lane, listed as not in phase 2 and waiting on phase 3's turn context, which is built: engine/actor.py TurnContext). The audit adds only that scenes/world.py situation_births (:643-672, called at :1892) is today a foreground asked operation at the turn's end, and that the job must be droppable through BUDGET_FLOW-5's withdraw and taken up as an asked operation at the edge, never applied from the job's thread. Two standing decisions bear on it and the design answers both: births and waiting rulings are "asked after a later line, never before the player's line" (GOALS.md line 176), so in play the edge takes up only a job that has finished and never waits for one; and past the budget an optional call is "deferred to a later turn, never to a thread" (line 206, Bundle C), which the background lane of Bundle F came after. The background lane is off under the stub and in every golden (life.FIRST_BATCH None, meta backfill None), so the design states the road births take there: asked after the line as today, or the lane switched on for births with the edge waiting as STRICT does.
- Test first: tools/sim/births_546_test.py gains a case: today the parts call is made on the main thread inside the line. Second case: a birth whose place the player left before the edge is dropped and rolled again by the engine; with the lane off the birth is asked as today.
- Recordings: maybe: stub_short holds two situation_parts calls (inputs 35 and 37); they stay put if births follow the lane's switch, which is off in every golden, and move to the edge if the design turns the lane on for recorded sessions. Data hash: no.
- Measure: none to build (stub suite); tools/night_measure.py already counts births a game day and their seconds on the 3060 (the measure the f599 decision waits on, GOALS.md line 174), which says what the move would save.
- Size: M
- Needs: BUDGET_FLOW-5
- Touches: situations
- Owner decides: whether births leave the line. (a) Asked after the line, as decided (f597, f599). (b) Written on the background lane and taken up at the edge, as doc 14 foresaw; recommended only once the night's births a day and their seconds say it pays.

### BUDGET_FLOW-20. The first people of a place the engine knows is next are written ahead, and dropped when not wanted
- Fixes: llm-flow-6, unmeasured-tasks-7
- Pillar: 7 Easy and comfortable to play (about 9.6 s of a first entry, about 13 s of the escort's line on the minimum card); 4; checklist 4, 5, 8
- Kind of case: a required call for a place whose need the engine can see lines ahead (a destination already fixed, a place one step away), made inside the turn that arrives.
- Build: Count first: from the tracked night runs under docs/measure, how often the next place entered is one step from the last, and what the extra background seconds cost on the 3060; the hit rate decides whether it is built. If it is: plan on the main thread, ask on the background lane after the present place's own people, hold the answer in memory under a cap in data, and on entry use it only if npc/life.py _plan still gives the same slots, else ask as today. The first user is a destination the engine has fixed (Maren's escort to the hall, scenes/mentor_actions.py :576), then the places one step away. The job is withdrawn when the turn needs the card or the player goes elsewhere. Profiles stay in the turn until a voice kit can be drawn without a save write. npc/backfill.py's one job a save, only for a peopled place, both change with BUDGET_FLOW-27 and -5.
- Test first: tools/sim/people_ahead_test.py, started from audit/work/unmeasured/m_lesson.py and world_py_populate.py: today the escort's line makes five required calls, populate_place among them. Second case: a walk to a neighbouring town uses the held people when the plan is unchanged and asks afresh when the hour's shifts changed the slots; a held answer never written is gone at the cap.
- Recordings: maybe: the background lane is off in every golden, so stub_short's four first entries stay as recorded unless the design turns the lane on for recorded sessions; then it is re-blessed (intended: who asks, and when). Data hash: yes (the cap).
- Measure: the count from the tracked night runs first (no card); then the lesson recording of BUDGET_FLOW-6 and a night's first-entry turn seconds (needs a model; priced for the 3060).
- Size: L: the design must settle what counts as "known next", the hit rate that makes it worth building, when a held plan is stale, the cap, and how a recorded session fixes the job at the edge.
- Needs: BUDGET_FLOW-27, BUDGET_FLOW-5, BUDGET_FLOW-6
- Touches: travel_places, people_talk
- Owner decides: build it or not, once the hit rate and the 3060 price are counted.

### BUDGET_FLOW-21. One-time loads run behind the loading line when a campaign opens
- Fixes: speed-turn-5
- Pillar: 7 Easy and comfortable to play (GOALS.md line 205: one-time loads belong to a warm-up); checklist 4, 5
- Kind of case: work done once a session that today falls inside the first typed line (the map's spring layout, 1.1 to 1.4 s; the first embed of the world's place names).
- Build: scenes/world.py open_world (:934-952) warms mapview.layout(world) behind the loading line. open_world returns early when its operation stands from the last open (:943-945), so the call sits after that operation on both paths, not inside it after ensure_dungeons, or a save opened a second time would still run the spring on its first line. The decision names the home page for one-time loads; the layout needs the campaign's own map, so the campaign's opening is the earliest it can run. No bearing, state hash or recording moves. The same place can embed the world's place names with no budget open (the opening has none, doc 27 f721), which is the second half of the first-line charge BUDGET_FLOW-2 prices truly; that branch needs BUDGET_FLOW-3's limit for a call with no budget to be long enough for a whole-world batch, and it changes which embed calls a recording holds (stub_party holds 41 embed rows, one of 203 texts at its third input), so it is the owner's choice. Keeping positions with the save, or removing the spring, are separate changes that need the owner's nod (engine4-2, another workstream).
- Test first: tools/sim/open_warm_test.py, started from audit/work/speedturn_gate.py (SPEEDTURN_FIX=L): today the layout cache is empty after open_world and the first line runs the spring. Second case: a save opened again with nothing typed (the early return) runs no spring on its first line either; with the embed branch, the first line embeds only the typed words.
- Recordings: no for the layout. Yes for the embed branch (stub_party re-blessed, intended: the embed moves to the opening). Data hash: no.
- Measure: none (stub suite)
- Size: S
- Needs: nothing for the layout; BUDGET_FLOW-2 and BUDGET_FLOW-3 for the embed branch
- Touches: travel_places, reload
- Owner decides: the place-name warm-up. (a) Leave it: with BUDGET_FLOW-2 the first line is charged about a second and waits about a second. (b) Embed at the opening and re-bless the recordings that hold embed rows.

### BUDGET_FLOW-22. A plain line's whole reads are counted, and the count only falls
- Fixes: engine1-8, engine4-6, people-11
- Pillar: "every cost per turn stays flat as the save ages" (GOALS.md "How it is built"); checklist 4, 5
- Kind of case: per-line work that re-reads a whole thing it already has: a YAML file parsed on each call, the world state loaded ten times in one talk turn, every resident loaded to learn that nobody is missing.
- Build: engine/ability_slots.py (:131-144, :614-623) uses the loaded tables (summons.S["forms"], healing.H["forms"]) and engine/arcs.py perk_text (:246-249) uses core.rules.MECHANICS; engine/matters.py's ten load_world_state() calls take one loaded state a talk turn or the narrow reader engine/worldstate.threads(store, status), in line with doc 13's narrow readers; npc/life.py works out who is missing from an index (one query for roles and anchors) and returns before loading anyone. simlib counts whole-state loads, YAML parses and load_npc calls a line, and a test pins the counts for a look, a talk and a walk into a peopled town so they may only fall. The counter is the infrastructure: LONG_SAVE-14 moves the other fourteen whole loads of a plain line under it.
- Test first: tools/sim/line_reads_test.py, started from audit/work/people_plan_cost.py and tools/sim/narrow_reads_641_test.py: today a walk into a fully peopled town loads every resident, a talk line loads the world state ten times and an ability's description parses two files. Second case: the same counts on a save with twice the residents are no higher.
- Recordings: no, and it must not (same state, same calls). Data hash: no.
- Measure: none (stub suite)
- Size: M
- Needs: nothing
- Touches: long_save (LONG_SAVE-14 shares the counter), startup_data, people_talk
- Owner decides: nothing

### BUDGET_FLOW-23. Putting back a map that did not move leaves its version alone
- Fixes: speed-turn-3
- Pillar: "every cost per turn stays flat"; 7; checklist 4, 5
- Kind of case: an undo that marks a thing changed when nothing changed, so every cache keyed on its version is rebuilt on each stand-down of an asked operation.
- Build: world/campaign.py (:170-185): snapshot() carries the version; restore() returns at once when the version is unmoved and bumps it only when something was put back. link, add_place, add_road and remove_place already bump only on change, and the version only rises, so an equal version is an equal map. engine/session.py :182 and :201 are the only callers and pass the snapshot through whole.
- Test first: a case in tools/sim/campaign_world_451_test.py, started from audit/work/speedturn_gate.py (SPEEDTURN_FIX=A): today a stand-down with no map change raises the version and the layout and route caches are rebuilt on the line. Second case: an operation that added a road and failed is restored and the version does move; state digest and stub call count are the same before and after.
- Recordings: no. Data hash: no.
- Measure: none (stub suite)
- Size: S
- Needs: nothing
- Touches: travel_places, long_save (LONG_SAVE-13 keys the route cache on this version, so it gains the most from it)
- Owner decides: nothing

### BUDGET_FLOW-24. A pane command told to be quiet reaches no model call, whatever hook it passes
- Fixes: scenes3-9
- Pillar: 7 Easy and comfortable to play (a click answers at once); checklist 4
- Kind of case: a quiet path (a pane click, which scenes/shop_actions.py's own heading says makes no model call) whose passive hooks do not hear that it is quiet and narrate anyway.
- Build: The quiet is held where every hook must pass, not hook by hook: a quiet command marks the turn's context (engine/actor.py TurnContext), and self.narrate() says nothing to the model under that mark, so scenes/passive_hooks.py tavern_ear (reached from scenes/shop_actions.py :209-210) keeps its note and makes no call, and a hook written later cannot forget. tavern_ear's own read of the board makes no call inside the click's operation (the board is posted without its stakes there, scenes/guild_actions.py :111). New code reads the acting character, not self.player.
- Test first: tools/sim/shop_click_test.py gains a click by a character who owns the tavern_ear perk: today the stub's call count rises by a narrate. Second case: a typed purchase by the same character still narrates; and every quiet pane command (buy, buy from stock, sell) played by a character who owns every world perk makes no call.
- Recordings: no: no golden holds a shop click. Data hash: no.
- Measure: none (stub suite)
- Size: S
- Needs: nothing
- Touches: town_services
- Owner decides: nothing

### BUDGET_FLOW-25. A waiting claim with no room is passed over before the model is asked about it
- Fixes: engine2-10
- Pillar: "every cost per turn stays flat"; 4; checklist 4, 5
- Kind of case: a check that costs a model call made before a free engine test that would have ruled the item out, repeated every time because the item stays at the front.
- Build: engine/canon.py settle_again (:416-434) tests the bucket's room before vet() and takes the next claim when there is none, so a full bucket costs no canon_check call. The pass counts claims vetted, not claims looked at (again_per_keep), so roomless claims at the front no longer hold back the ones behind them. A claim passed over this way is not vetted, so one that would have been let go as already known waits in the list until its bucket has room; the list keeps its cap.
- Test first: a case in tools/sim/canon_route_test.py: today a claim waiting on a full bucket costs one canon_check call at every settle. Second case: a claim for a bucket with room behind it is vetted in the same pass; a bucket that empties lets the first claim through later.
- Recordings: no: no golden holds a canon_check call. Data hash: no.
- Measure: none (stub suite)
- Size: S
- Needs: nothing
- Touches: people_talk
- Owner decides: nothing

### BUDGET_FLOW-26. A thinking call's room is worked out against the slot it runs in
- Fixes: llm2-6
- Pillar: infrastructure (measuring runs that turn thinking on); checklist 4, 7
- Kind of case: two numbers for the context a call has (config.NUM_CTX 32,768; the slot's 16,384), with the guard reading the wrong one.
- Build: llm/backend.py think_room (:157) uses the slot's size from the settings (server.slot_ctx), not config.NUM_CTX and not the size the server granted, because the room feeds the recorder's fingerprint (the request's max_tokens holds it), which must hold nothing of the machine. The settings file is outside the data hash, so a thinking recording notes in its meta the slot size its room was worked from and replays with that. NUM_CTX defaults to it or goes; its only other use is the stand-ins' option (:169).
- Test first: tools/sim/thinking_room_534_test.py and num_ctx_425_test.py pin the old number and change with it, started from audit/work/llm2_think_room.py: today a 30,000-character prompt gets room 8,192 where the slot leaves 4,080. Second case: a 36,500-character prompt (npc_conversation's ceiling) ends thought_out and is not filed as too big.
- Recordings: no (kept recordings do not think: thinking is off by the owner's decision). Data hash: no.
- Measure: none (stub suite)
- Size: S
- Needs: nothing
- Touches: tools_bots, tests
- Owner decides: nothing

### BUDGET_FLOW-27. A place's missing first people are asked for inside an input, and a wait on a background job is bounded and charged
- Fixes: min-card-7, trace-threads-5
- Pillar: 7 Easy and comfortable to play (the 60 second turn); infrastructure; checklist 4, 7, 8
- Kind of case: the two ways the main thread waits on the model after the line is typed and before its budget opens or with no limit: scenes/world.py repopulate() (:840) asks for a place's people between the prompt and play(), and backfill.collect() promotes a pending job and waits for it with no deadline and no charge.
- Build: scenes/world.py repopulate() stops asking in the foreground between the prompt and the input. Under option (a) npc/backfill.py start() takes a place whose first people are still missing as well as a peopled one, and the edge only collects what has finished; where the background lane is off (life.FIRST_BATCH None: the stub suite and every golden) the people are asked as option (b) asks them, so every session has a stated road. backfill.collect(), when the caller owns an open budget, waits with budget.deadline() and charges the wait priced from the job's own request (its prompt and the slots it asked for), not from populate_place's table size (1,500 tokens is 47 s on the 3060 and would refuse the rest of the line); when the limit runs out npc/life.py populate_place returns the people who exist and plans nothing new while a job is pending, and the rest come in at a later edge. A recorded session's wait at the edge (streams.STRICT) is the one wait allowed with no budget, named in the ratchet. This empties the set BUDGET_FLOW-4's ratchet starts with. New code reads the place from the acting character, not self.player.
- Test first: tools/sim/people_edge_test.py, started from audit/work/check_trace_threads_5_wait.py and tools/sim/goes_on_525_test.py: today a save loaded standing in an unpeopled place whose ask failed makes a ResidentSet call before the line's budget opens, and re-entering a place whose job is pending waits uncharged and with no limit. Second case: with the lane off the same place is peopled inside the input and charged; a job that outlasts the limit leaves the people who exist and the line goes on; the ratchet's set is empty.
- Recordings: no: no golden runs the background lane (each meta has backfill None) and none holds a residents call that failed. Data hash: no.
- Measure: the live gate's turn seconds before and after (needs a model; the local card will do).
- Size: M
- Needs: BUDGET_FLOW-4 (the ratchet this empties). Option (b) also needs populate_place asked outside its operation, which is BUDGET_FLOW-10's.
- Touches: typed_line, travel_places, people_talk, tests
- Owner decides: where a place's missing first people are asked for. (a) On the background lane, so the typed line never waits and the people appear at a later edge (planned here). (b) As an asked operation at the head of the input, charged as a required call, so they are there for the line just typed (the shape take_up_acts has, doc 14 lines 144-148).

## No action

Nothing. Every finding given to this workstream is placed under a feature above; the re-rates and duplicates sit with the feature that fixes them.

## Order

1. BUDGET_FLOW-1: the budget's question before a later try; the mentor ladder and the bounded waits lean on it, and it is the worst-case line over 60 s.
2. BUDGET_FLOW-2: true prices; a profile the game cannot load stops it at import, and the first line loses 35 of its 55 s.
3. BUDGET_FLOW-3: an embed with no deadline can hold a line for 120 s.
4. BUDGET_FLOW-4: the pane walk inside its input, and the ratchet that names what is left outside a budget.
5. BUDGET_FLOW-27: the two holes the ratchet names, closed once the owner has said where the people are asked for.
6. BUDGET_FLOW-5: the worker's withdraw of one job; 18, 19 and 20 need it.
7. BUDGET_FLOW-6: the recording of creation and the lesson; 11, 18 and 20 are measured with it.
8. BUDGET_FLOW-7: the mentor's ladder, small.
9. BUDGET_FLOW-8: the quirk's details to the tail, small, with TASK_FAILURE-8.
10. BUDGET_FLOW-9: the input's count, built once with RELOAD-10; keeps a save's ids from repeating.
11. BUDGET_FLOW-10: the residue out of the transactions, family by family, after 27 has settled the people of a place.
12. BUDGET_FLOW-11: ceilings and expected sizes; one rebless of every golden, back to back with CONTRACTS-6.
13. BUDGET_FLOW-12: the slot numbers, before the prompt work that claims a cached saving.
14. BUDGET_FLOW-13: the interpreter's request, with doc 29 R2.
15. BUDGET_FLOW-14: the party's parts, in the same rebless as 13.
16. BUDGET_FLOW-15: the townsperson's request; the cap now, the repeat only if the speak switch stays off.
17. BUDGET_FLOW-16: the system-text ratchet, and the gesture line with doc 09 A4's frame card.
18. BUDGET_FLOW-17: whole-world lists, the discovery check first.
19. BUDGET_FLOW-18: creation's abilities in the background.
20. BUDGET_FLOW-19: births on the background lane (doc 14 line 298), on the owner's word.
21. BUDGET_FLOW-20: people written ahead, only after the count says it pays.
22. BUDGET_FLOW-21: the opening's warm-up; the layout at once, the embed branch on the owner's word.
23. BUDGET_FLOW-22: whole reads counted, flat as the save ages.
24. BUDGET_FLOW-23: the map's version, small.
25. BUDGET_FLOW-24: the quiet click, small.
26. BUDGET_FLOW-25: the waiting claim, small.
27. BUDGET_FLOW-26: the thinking room, for measuring runs only.

## Review

- Whole file: every "Data hash: yes" now says what it costs. A change under the hashed part of data/ makes the three goldens be made again for the hash even when no row moves (budget_data_459_test.py :94, isolation_456_test.py :127); the plan had written "no golden moves" beside a hash move in several features.
- BUDGET_FLOW-1: added what the gateway does with the new refusal. Raised between tries it would be caught by generate()'s `except LLMError` and answered with the relaxed pass and a model_down row, the opposite of the feature. Said that the draft check is the existing chain lifted into one function, that no new number is needed (so no hash move), and which failed tries the goldens hold.
- BUDGET_FLOW-2: the measure line was wrong. The tool reads recording folders, the tracked nights are call logs, none holds an embed row, and no kept real-card recording has embeds; so the embed fit needs one new recorded session (a model). Added: scaled() does not scale embeds today; rerun.replay() must clear the new keys for an old recording or the goldens are repriced; the other holders of the profile's keys; that engine1-1 is mended in play only once the profile is rewritten. Size M to L with what the design must settle. The cards.yaml hash move depends on STARTUP_DATA-8.
- BUDGET_FLOW-3: the two new numbers moved from data/rules/budget.yaml to data/runtime/server.yaml (wall-clock numbers of the server, Bundle F), so the data hash does not move and a replay, which states none, cannot part. Named every embed source (Unstarted, the runtime's wrapper and the tests' fakes were missed) and that the failing test must hold the request on fake_llama.py, since a stand-in function cannot be cut.
- BUDGET_FLOW-4: split. It keeps the pane walk (world_py-3) and the ratchet; min-card-7 and trace-threads-5 went to the new BUDGET_FLOW-27 with the owner's question, so the part with no question can be built now. The pane arrival cannot call turn_ticks whole (said_nothing, the turn count and resume_road are the line's): one declared list, and each tick a pane walk gains is named as a change in play. The ratchet starts as a named set that may only shrink, not "asserted empty", with a mark for when the loop begins and a hook for waits. Recordings changed from maybe to no (no golden holds a pane walk; checked the three).
- BUDGET_FLOW-5: the withdraw takes a call waiting or in flight, as one atomic call; backfill uses only the waiting case. BUDGET_FLOW-18 needs the in-flight case and the plan's cancel could not serve it. The gate's change belongs in nightrun's script mode. The reason no golden moves was wrong (it is that the lane is off in every golden, not that STRICT waits).
- BUDGET_FLOW-6: retitled; it writes the recording and mentor_chat's ceiling, and BUDGET_FLOW-11's tool writes the budget rows (the two features each named the other). The lesson script must reach Maren's largest request or the ceiling is written low.
- BUDGET_FLOW-7: "mentor_say no longer tries mentor_speak" would have taken free speech from every site that calls mentor_say directly; the ladder now skips that try only for the ten pair sites. Needs nothing (room_for_passage exists). The second test site was a direct mentor_say site, so not a case of the kind; changed to the desk line.
- BUDGET_FLOW-8: Recordings changed from maybe to yes (stub_party three calls, stub_fight two). Added the fence (defer writes the save and quirked() has fourteen callers) and that the queue drops an entry after three lines and waits through a fight, so it needs TASK_FAILURE-8. Corrected the kind: the call is already outside the transaction; the cost is seconds before the telling.
- BUDGET_FLOW-9: RELOAD-10 plans the same change for trace-save-4. Said so: one build, one test file; this entry carries the finding's id and its case. The recordings reason was false (every golden holds a line not taken) though the verdict, no, stands.
- BUDGET_FLOW-10: the title says every call and the list left six of RECORDED's eighteen unnamed (road_event, ruling, party_intent, pulse_cataclysm, thread_telling, narrate). All eighteen are now placed: narrate with TASK_FAILURE-5, pulse_motive with REMOVALS_2-5, sixteen here. The ratchet can read the goldens' rows, which carry each call's operation, with no replay. Named which goldens move. Needs BUDGET_FLOW-27, not 4.
- BUDGET_FLOW-11: the summary's bound is CONTRACTS-6's helper and was planned twice; this keeps the ceilings, the expected sizes and the "exactly full is emptied" rule. Expected sizes read from data/measured would change a replay's arithmetic with no hash to show it, so they go into the recording's meta as the profile does. Dropped "at most three steps" (the contract states no such bound). Needs CONTRACTS-6.
- BUDGET_FLOW-12: the failing test's claim was wrong: slots() already prints the understanding's cached share and the restores by slot, and latency already parses checkpoints made. Reworded to what is missing and to reuse the one parser.
- BUDGET_FLOW-13: the two halves pull against each other: once the about floor works, the catalogues change from line to line and cannot sit first. The order now comes from a count over recorded requests. The place gate is tied to R2 (only `named` lets a place that was not offered be reached). Needs the owner's word on doc 29 R2.
- BUDGET_FLOW-14: the pronoun must stay in what the interpreter gets. The same string goes out for Maren and story companions, so the view covers every party member. stub_fight carries hires too and moves.
- BUDGET_FLOW-15: the repeat of the place is built only if the speak switch stays off after the owner's reading; the cap either way. Named the goldens.
- BUDGET_FLOW-16: sized S: what is built is the ratchet and the gesture line; doc 09 A4 is not re-planned. The second test case named an exchange line that does not exist (one site, world_prompts.py :293). The gesture line is tied to A4's frame card so stub_short moves once and the prompt change is measured.
- BUDGET_FLOW-17: Recordings changed from maybe to yes: stub_short holds two thread_telling requests with both lists. The helper is shared with LONG_SAVE-12.
- BUDGET_FLOW-18: needs the in-flight withdraw, and must keep REMOVALS_2-3's fault path.
- BUDGET_FLOW-19: added the owner's question and the two decisions it touches (GOALS.md lines 176 and 206); "Owner decides: nothing" was not true for a move those decisions speak to. Recordings changed from yes to maybe (the lane is off in every golden).
- BUDGET_FLOW-20: Needs BUDGET_FLOW-27 in place of 4; Recordings from yes to maybe for the same reason as 19.
- BUDGET_FLOW-21: the layout call placed after ensure_dungeons inside the operation would be skipped on the early return, failing the plan's own second case; moved after the operation on both paths.
- BUDGET_FLOW-24: widened from one more parameter on each hook to one mark the narrator itself obeys, with a test over every quiet command and every world perk.
- BUDGET_FLOW-25: Recordings from maybe to no (no golden holds canon_check). Said what the reorder changes for a claim that would have been let go.
- BUDGET_FLOW-26: the settings file is outside the data hash, so a thinking recording notes the slot size in its meta.
- BUDGET_FLOW-27: new, from the split of 4.
- Open: BUDGET_FLOW-3 names data/runtime/server.yaml's embed section from the code that reads it (llm/runtime.py), not from the file, which this review may not open. Reading the file's embed keys settles the key names.
- Open: BUDGET_FLOW-8: whether any of quirked()'s fourteen callers runs with the fence armed and no operation open. The build's writable() guard is right either way; playing data/replay/scripts/stub_party.py with defer() called from quirked() and counting WriteOutsideOperation settles whether the guard is ever taken.
- Open: BUDGET_FLOW-11 and CONTRACTS-6 give a field that arrives at its bound two different ends (emptied here, cut at the last whole word there). One rule a field, declared with the bound; the two workstreams settle it when the helper is designed.
- Open: BUDGET_FLOW-15: whether the owner's blind reading of the speak prompt has been taken (docs/measure/2026-11-18_blind_reading_owner.md is untracked and was not read). It decides whether the place's repeat is built at all.
- Open: BUDGET_FLOW-19 and BUDGET_FLOW-20: whether a recorded session should run the background lane at all. It is off in every golden and under the stub today, so nothing in the suite walks the lane's code inside a played line; the design of 27 should say whether one kept script turns it on.
- Open: BUDGET_FLOW-2: whether the 44 tracked call logs spread a task's request sizes widely enough to tell a base from a rate. Running the fit over them (no card) settles it before the design is written.
