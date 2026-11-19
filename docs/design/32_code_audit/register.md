# Register of findings

One row a finding, both rounds. `checked` is the second reader's verdict: confirmed (shown or reproduced), plausible (the code agrees, not shown), refuted (do not act on it), blank (small, listed without a check). `known` marks a finding the owner's documents already record. The whole of each finding is in the findings files beside this one.

## Bugs (276)

| id | checked | weight | place | finding | known |
|---|---|---|---|---|---|
| engine2-1 | confirmed | high | engine/combat.py:3045 | A foe that broke, yielded or fell earlier in the foes' phase still takes its turn; a fallen one dies a second time and the kill is credited to the player |  |
| trace-fight-1 | confirmed | high | engine/combat.py:3045 | An enemy that fled or yielded earlier in the enemy phase still takes its turn that round |  |
| trace-fight-3 | confirmed | high | engine/damage.py:253 | In a trial of rank the player's own summon being beaten wins the trial |  |
| frontend-shipping-1 | confirmed | high | engine/data_check.py:1061 | A game built from this tree cannot start: the startup check reads .py source files that the build does not carry |  |
| speed-turn-2 | confirmed | high | engine/data_check.py:1061 | A built game cannot pass its own startup check: six of the check's scans read .py sources that the build does not ship |  |
| engine3-1 | confirmed | high | engine/enchanting.py:146 | One enchantment consumes the whole stack of the reagent |  |
| situations-1 | confirmed | high | engine/situation_parts.py:600 | A situation's own way met by a kill credits nobody: the same kill ends it won, ends it lost with its fallout, or ends nothing, by what its record held before | yes |
| logs-fields-7 | confirmed | high | llm/contracts.py:1943 | RE-RATE llm-checks-6: the model that ships loses finds to the missing name as well: 4 of 4 discovery calls in the Gemma record failed, both finds lost | yes |
| aged-save-6 | confirmed | high | scenes/arc_actions.py:213 | RE-RATE scenes1-3: its condition (all sixteen captive names in the save) holds from about line 1,500 of a fighter's play, so the divide by zero is on the ordinary path of every missing-person contract after that |  |
| scenes1-1 | confirmed | high | scenes/dungeon_actions.py:229 | A fight resumed after a reload has lost what it was for: a dungeon chamber won is not cleared, an arc's camp fight won does not move the arc |  |
| trace-save-2 | confirmed | high | scenes/dungeon_actions.py:229 | What a saved fight is for lives only on the scene: a fight resumed after a close or a crash ends without its consequences (dungeon chamber not cleared; by reading also Orenna's quest, an arc's camp, a town's gate) |  |
| scenes3-1 | confirmed | high | scenes/trial_actions.py:71 | Asking about the next rank starts the rank trial for a member who has not earned it |  |
| trace-save-1 | confirmed | high | scenes/world.py:943 | A save opened twice with no line typed between skips the whole opening, so the campaign's own places are never put back on the map (KeyError at a dungeon entrance, a home, a found place, the road's stop) | yes |
| people-8 | confirmed | medium | character/kit.py:109 | The starting companion's model call has no fallback; a model failure there stops the game at the first waking | yes |
| shell1-7 | confirmed | medium | core/updates.py:92 | UPDATE_CHECK = False does not stop the window's release check |  |
| dead-switches-1 | confirmed | medium | core/updates.py:98 | UPDATE_CHECK = False does not stop the update check in the windowed (built) game |  |
| data-1 | confirmed | medium | data/rules/events.yaml:142 | 'humanoid' is not a creature category: one war in three (and one boss-less invasion in six) draws its hosts from every category |  |
| trace-fight-4 | confirmed | medium | data/rules/stages.yaml:15 | A death by a tick, a torn wound, a rebound or Death's Door skips what a death sets off: the ties, morale, the summon's unmaking, who felled whom |  |
| situations-8 | confirmed | medium | engine/act.py:271 | The same line said again stands on its kept ruling and applies its changes again: trust +10 a repeat with no model call, 50 to 100 in five | yes |
| situations-6 | confirmed | medium | engine/act.py:485 | A situation's change that rests ('earlier') on a kept change outside that situation is dropped as resting on a change that was not kept |  |
| situations-7 | confirmed | medium | engine/act.py:505 | The one-change-a-person rule runs after the situation's check, so a change that rested on the dropped one without naming it stays | yes |
| situations-5 | confirmed | medium | engine/act.py:518 | On an act rolled on talk, a world change that says it rests on 'earlier' is kept as the act's own hand: the f604 rule covers only force and skill | yes |
| engine1-6 | confirmed | medium | engine/actions.py:257 | 'I sit down and give Odly the draught' reads as the player taking it: 'down' counts as a drinking verb after any one word | yes |
| llm-checks-10 | confirmed | medium | engine/banter.py:68 | The check for a hire telling what they hold also fires on owning a thing ('I have a staff') |  |
| logs-sendbacks-2 | confirmed | medium | engine/banter.py:165 | The amounts check on party talk refuses the hire's own oath, which the engine offered in the same request ('By the Nine Winds'), and idioms ('twice as hard', 'half-asleep'): 21 of 24 send-backs are false alarms and 6 exchanges were lost to them |  |
| engine1-4 | confirmed | medium | engine/battlefield.py:465 | approach() tells of a crossing and stamps the move when the fighter did not move (frostwelded, or no path) |  |
| engine1-3 | confirmed | medium | engine/behaviors.py:66 | A fleeing foe killed by the parting strike (No One Escapes) is still marked fled, and the player is told it fled |  |
| engine1-1 | confirmed | medium | engine/budget.py:177 | The first line after every launch is charged about 35 s of the 60 s budget for one embed request that takes about 1 s | yes |
| engine2-4 | confirmed | medium | engine/clock.py:72 | 'wait until two guards pass' is read as two o'clock: hour_named takes any number after 'until' as an hour, and its reading overrides the model's |  |
| engine2-3 | confirmed | medium | engine/combat.py:1451 | Lines told inside take_damage come before the blow that caused them: EVENTS has the foes break 'seeing the chief fall' before the hit and the fall |  |
| trace-fight-2 | confirmed | medium | engine/combat.py:1456 | A floor that holds a killing blow is undone by the torn wound in the same blow, and a tick passes every floor but the duel's and the first hunt's |  |
| engine2-2 | confirmed | medium | engine/combat.py:1599 | A death that is not the direct target of a blow is never told or credited: side damage from perks, and an ally or the player dying of a tick |  |
| fight-abilities-2 | confirmed | medium | engine/combat.py:2205 | The rest of an area spell, a sweep or a sweeping blow strikes foes who broke and ran at its first kill: they end both fled and dead |  |
| fight-abilities-6 | confirmed | medium | engine/combat.py:2336 | Blood Summons charges the mana as well as the health and is refused with no mana; Echoing's free first ability is refused when the pool is short |  |
| trace-fight-5 | confirmed | medium | engine/combat.py:2648 | start_turn treats every dead enemy as dead of an affliction: a second death line, a second morale roll, the kill credited to the player |  |
| fight-abilities-4 | confirmed | medium | engine/combat_perks.py:508 | Overcast buys through the named spell's once-a-fight lock and its day lock, and through any ability's cooldown, not only a spell's |  |
| fight-abilities-1 | confirmed | medium | engine/combat_perks.py:595 | Spell Echo repeats the spell onto the foe its third cast just killed: the foe falls twice and every kill perk pays twice |  |
| dead-switches-2 | confirmed | medium | engine/crashlog.py:26 | In a built game crash.log, refusals.jsonl and the audit log are written inside the bundle, not in logs/ beside the exe |  |
| engine3-2 | confirmed | medium | engine/entities.py:165 | gendered() adds -s/-es to any word after he/she/it: past tenses and already-agreed verbs are mangled in the prompts |  |
| engine3-3 | confirmed | medium | engine/events.py:882 | A dead ally's quests are tied off on the stored player inside an operation, then overwritten by the commit |  |
| engine3-4 | confirmed | medium | engine/events.py:1303 | People who flee a fallen town leave no vacancy: the post is recorded at the refuge, after the move |  |
| engine3-8 | confirmed | medium | engine/events.py:1415 | An assault on a town lives only on the scene object: a game closed during the fight at the gate decides nothing | yes |
| engine4-3 | confirmed | medium | engine/forge.py:36 | A reforge rolls spell power at full size on gear that a drop halves |  |
| logs-sendbacks-3 | confirmed | medium | engine/hygiene.py:99 | A carriage return before a line break is sent back as 'a character came out broken'; the reason quotes an invisible character, the retry repeats it, and 39% of those requests are lost | yes |
| engine4-1 | confirmed | medium | engine/inventory.py:240 | inventory.find matches by substring, and on every word of a whole typed line, so a wrong pack item is chosen |  |
| engine4-2 | confirmed | medium | engine/mapview.py:70 | A found place moves on the map, and the direction word to it changes, once the save is opened again |  |
| stale-copies-1 | confirmed | medium | engine/matters.py:292 | RE-RATE engine4-4: on_arrival's stale world-state save is the commonest lost update in play, loses the list row of every situation moment, and leaves those moments unclosed for days | yes |
| engine5-1 | confirmed | medium | engine/pulse.py:936 | remove_npc ties off the player's quests on a copy loaded from the save; three callers then commit the scene's own copy over it |  |
| engine6-4 | confirmed | medium | engine/quirks.py:590 | With three or more others present, none of the speaker's own gestures is checked for a repeat |  |
| engine6-3 | confirmed | medium | engine/recognition.py:43 | The return greeting gives the model the person's newest memory of anything as 'the last thing you remember of them' |  |
| engine6-2 | confirmed | medium | engine/severity.py:96 | A struck companion's memory is kept under minutes // 1440, a day behind clock.day: the model is told it happened 'yesterday' the minute it happens |  |
| situations-2 | confirmed | medium | engine/situation_parts.py:606 | Who a situation's end credits is read from the 40-row record window: a counted change pushed out by later ones leaves no contributor and the end is read as lost | yes |
| trace-fight-6 | confirmed | medium | engine/spellcraft.py:478 | Dominate on the last standing foe ends the fight as a win at once, with the foe unhurt |  |
| engine7-3 | confirmed | medium | engine/spellcraft.py:487 | Death's Door writes the target's health to zero itself instead of going through the damage path, so the floors and on-fall stages do not run | yes |
| fight-abilities-5 | confirmed | medium | engine/spellcraft.py:1107 | A charged spell or a wind-up technique loses every bonus fixed when it was begun: Archmage's Focus, Overchannel's blood, Headsman and the other heavy-ability perks |  |
| fight-abilities-3 | confirmed | medium | engine/summons.py:115 | A Bound summon made anew by casting its spell in a fight is gone again at the next fight: only a cast outside a fight mends the bond |  |
| engine7-1 | confirmed | medium | engine/truth.py:625 | truth.coined calls a given name 'no one' when it carries a contraction other than 's (Maren'll, Maren'd), so a sound reply is sent back to the model |  |
| logs-sendbacks-5 | confirmed | medium | llm/contracts.py:1297 | RE-RATE llm-checks-9: the back-to-work check is half of all frame send-backs (71 of 141, 9.5% of frames); 15 are false alarms the proposed pattern only partly clears, and dropping the sentence in place settles all 71 with no call |  |
| llm-checks-6 | confirmed | medium | llm/contracts.py:1943 | A find's name and description are optional in the grammar but demanded by the validator: both Qwen runs lost a discovery to it | yes |
| logs-sendbacks-7 | confirmed | medium | llm/contracts.py:1944 | RE-RATE llm-checks-6: not a Qwen quirk: both discoveries in the Gemma record were lost the same way (4 of 4 tries), so no find the model proposed in 44 runs was ever accepted | yes |
| logs-fields-5 | confirmed | medium | llm/contracts.py:2200 | A hire's detail weights are thrown away for one hire in three: the model gives seven (five details and two secrets) and the contract keeps only a list of five |  |
| llm-checks-7 | confirmed | medium | llm/gateway.py:198 | The looser last pass repeats the request as first made, and no pass checks that a townsperson's line is not the player's own: the player's last question was printed as the innkeeper's answer |  |
| min-card-1 | confirmed | medium | llm/gateway.py:239 | A retry is never asked of the budget: every try after the first, and the looser last pass, is handed at least the 8 s floor however far over the turn already is | yes |
| aged-save-1 | confirmed | medium | llm/gateway.py:384 | Every answer a contract refuses pins the whole stack of its turn in memory for the rest of the sitting |  |
| trace-threads-3 | confirmed | medium | llm/llama.py:435 | Embedding requests never carry the turn's deadline: a stalled embedder holds the turn for the full 120 s hang guard, then embeddings are off for the session | yes |
| llm2-2 | confirmed | medium | llm/llama.py:435 | An embed call has no turn deadline: a stalled embedder holds the turn for 120 seconds |  |
| shell1-8 | confirmed | medium | main.py:194 | In the built game crash.log, refusals.jsonl and the audit log land inside _internal, not in the logs folder the player is pointed to | yes |
| people-1 | confirmed | medium | npc/life.py:268 | Traits and the speech profile are rolled from the same seed, so a person's culture decides which traits they can have |  |
| scenes1-3 | confirmed | medium | scenes/arc_actions.py:211 | The plain arc story divides by zero once all sixteen captive names are in the save |  |
| scenes1-2 | confirmed | medium | scenes/arc_actions.py:390 | At an arc's last fight the dead leader is made a walking captive, and a leader who yielded is neither captive nor held |  |
| scenes1-5 | confirmed | medium | scenes/arc_actions.py:492 | A captive's arc step is matched by node id alone, so another arc's captive answers for, and completes, the current arc's step |  |
| scenes1-6 | confirmed | medium | scenes/arc_actions.py:507 | A threat is recorded as a promise of mercy: the captive's deal is read by substring | yes |
| scenes1-4 | confirmed | medium | scenes/arc_actions.py:799 | One beaten foe counts twice toward a hunt or bounty: once when it yields, again when it is finished or handed to the watch | yes |
| task-failures-2 | confirmed | medium | scenes/combat_scene.py:827 | A fight round whose telling fails shows no figure at all: the player can die reading 'The round is over.' | yes |
| scenes1-7 | confirmed | medium | scenes/combat_scene.py:1241 | The after-fight request lists hires who died in an earlier fight as having died in this one (a thirty-minute clock window) |  |
| aged-save-2 | confirmed | medium | scenes/field_actions.py:919 | Word of Recall is refused in the town reached after any road stop: the stop is remembered as the town behind you and is no longer on the map |  |
| scenes2-2 | confirmed | medium | scenes/guild_actions.py:397 | A yes to a person's request, said where a guild clerk stands, goes to the board and can take an unrelated contract |  |
| scenes2-1 | confirmed | medium | scenes/guild_actions.py:648 | A request handed in to the asker: the thanks (trust +5) is written on a second copy of them and then overwritten by the scene's own copy |  |
| scenes2-3 | confirmed | medium | scenes/inventory_actions.py:419 | coin_amount reads one number word from a short table of its own: 'twenty five silver' is 5 silver, 'fifteen silver' is no amount |  |
| scenes2-5 | confirmed | medium | scenes/inventory_actions.py:617 | Every gift, of any size, moves bond +1 (in code) and trust +2 (reaction rule) with no bound: 45 coppers make a hire devoted | yes |
| scenes2-4 | confirmed | medium | scenes/law_actions.py:478 | The answer to the watch is the first choice in menu order with any matching word start: 'fine, take me to jail' pays the fine, 'I won't pay, I run' pays | yes |
| scenes3-5 | confirmed | medium | scenes/orenna_actions.py:273 | Which fight is being fought (orenna_fight) is not in the save: a game reopened during the High Keeper fight loses the win | yes |
| typed-patterns-1 | confirmed | medium | scenes/party_actions.py:474 | The hire's follow-up is the reader wrong most often: after a hire speaks, the next line goes to them as chat unless it opens like an action, whoever the player was talking with | yes |
| task-failures-4 | confirmed | medium | scenes/quirk_actions.py:58 | A once-only writing that fails on the model is never asked again: a hire keeps no details or secrets, an arc its plain story, a companion's own words go unread | yes |
| scenes3-3 | confirmed | medium | scenes/quirk_actions.py:397 | A pending errand holds the hire's dict by reference: after any operation that does not stand (or a reload) the answer is paid for and the hire never hears it |  |
| task-failures-3 | confirmed | medium | scenes/road_actions.py:580 | At a road stop an act that only waits for its ruling is paid as help done: coin and reputation for a deed the game has not decided | yes |
| stale-copies-5 | confirmed | medium | scenes/road_actions.py:582 | Helping at a road stop reached from another stop raises KeyError: the stop's record still names the earlier stop, which is off the map |  |
| scenes3-6 | confirmed | medium | scenes/road_actions.py:727 | A defeat at a road stop leaves the stop on the map and its people untidied | yes |
| scenes3-2 | confirmed | medium | scenes/spell_actions.py:163 | A stale rank offer takes the teacher's fee and teaches nothing (and raises TypeError at the top rank) |  |
| scenes3-4 | confirmed | medium | scenes/voice.py:128 | A failed rewrite in voice.fresh throws away the valid draft |  |
| trace-replay-1 | confirmed | medium | scenes/world.py:342 | What the checks and prompts remember of the session is not in the save: the same save and the same line give other requests, another verdict and another state once the game has been closed and opened |  |
| world_py-2 | confirmed | medium | scenes/world.py:576 | A save closed in the middle of a talk with someone who is no resident of the place loses the talk when it is opened again |  |
| dead-families-1 | confirmed | medium | scenes/world.py:1438 | A deed the engine refused, its passage lost, is told to the player as done: "You see it through." |  |
| task-failures-1 | confirmed | medium | scenes/world.py:1438 | A lost passage is stood in for by 'No trouble. It's done.' whatever the deed came to: a failed theft, a half success, a hurt, an arrival | yes |
| world_py-1 | confirmed | medium | scenes/world.py:1928 | A silent line's telling is asked inline inside the tail: when the narrator fails the player reads nothing at all and the tail's ticks are lost |  |
| world_py-3 | confirmed | medium | scenes/world.py:1982 | A pane walk's arrival tail runs after the input has closed: no budget, not restartable, tellings asked inline |  |
| pane-commands-3 | confirmed | medium | scenes/world.py:2058 | The #enchant question keeps list positions: a pane command before the answer reorders the list, and 'yes' binds another enchantment into another item at another fee |  |
| pane-commands-2 | confirmed | medium | scenes/world.py:2117 | An attribute point spent in a fight refreshes the fighter in memory only: the fight's row is not saved, so the next typed line or a reopen puts the old fighter back |  |
| typed-patterns-3 | confirmed | medium | scenes/world.py:2585 | join_guild_rewrite takes the joining fee on substrings of the line and of the model's own summary: 'The guild hall feels warm tonight.' joins the guild | yes |
| pane-commands-1 | confirmed | medium | scenes/world.py:2770 | Gear and enchant commands are taken in the middle of a fight and change the character, but the fighter (weapon, armour, bonuses, reach) and its saved row stay as they were to the fight's end |  |
| trace-turn-1 | confirmed | medium | scenes/world.py:3441 | A walk to where the character already stands does nothing and says nothing: the turn ends on the generic 'Nothing comes of that here' line and is recorded as a walk done |  |
| trace-turn-2 | confirmed | medium | scenes/world.py:4353 | A few handlers say no with a bare console.note instead of refuse(): the step is recorded as done, the narrator is never told NOT DONE, and the refusal is not logged |  |
| typed-patterns-4 | confirmed | medium | scenes/world.py:4536 | on_other reads the whole line for a rest word, whichever step it is running: the night is slept twice, and 'I can't sleep, so I whittle a stick' sleeps fifteen hours | yes |
| trace-fight-7 | confirmed | medium | services/fight.py:519 | Taming or binding a foe takes it out of the fight without releasing who it was engaged with |  |
| shell1-1 | confirmed | medium | simbot.py:139 | The balance bot's fight-end wrapper rejects the game's call: no bot fight is ever recorded and a run ends at level 1 |  |
| tests-health-1 | confirmed | medium | simbot.py:139 | The bot's wrapper around party_after_fight does not take fight=, so every bot fight ends in a TypeError and the rest of the fight's end is skipped |  |
| shell1-2 | confirmed | medium | simbot.py:148 | The bot's pack wrapper returns None where the game reads a Stowed: every purchase a bot makes raises |  |
| shell1-3 | confirmed | medium | simbot.py:1489 | The bot still indexes a quest's deadline, which f491 removed: KeyError every cycle once it holds a contract |  |
| shell2-1 | confirmed | medium | storage/saves.py:122 | A deleted game moved back out of saves/_deleted is never listed again, and an unreadable index.json hides every game | yes |
| tools1-1 | confirmed | medium | tools/event_trial.py:75 | A Trial never closes its session or removes its stub, so on Windows each event case plays on the save the case before it left |  |
| tools1-3 | confirmed | medium | tools/latency.py:861 | The Fights section's 'operations rolled back' and 'fights let go at a load' can never be anything but 0 on a real night |  |
| tools2-1 | confirmed | medium | tools/nightbot.py:875 | The night bot never works a situation's contract: the posting goal ends 'done' three times a line, for the rest of the situation |  |
| tools2-3 | confirmed | medium | tools/nightrun.py:636 | nightrun --save NAME deletes saves/NAME unasked, whatever it is: a player's own game, or a folder outside saves |  |
| tools3-2 | confirmed | medium | tools/rerun.py:359 | Every replay leaves its scratch log folder in the temp directory: 11,716 folders and 2.2 GB on this machine |  |
| tools3-1 | confirmed | medium | tools/rerun.py:466 | A replay passes when the game stops short of the recording: calls left unserved and lines never asked are not compared |  |
| suite-speed-6 | confirmed | medium | tools/run_suite.py:371 | The default --outdir /tmp/meravia_suite is C:/tmp/meravia_suite to Python and the user's temp folder to Git Bash: both exist, and the failure line sends a reader to the other one |  |
| tools3-3 | confirmed | medium | tools/world_divergence.py:41 | The divergence yardstick counts only the situations the state still holds at the end (the last 30 finished), so it undercounts and overstates divergence | yes |
| frontend-shipping-2 | confirmed | medium | ui/gui/__init__.py:57 | A start that fails is told under the home page, and the window then closes itself: the player never learns why |  |
| frontend-shipping-3 | confirmed | medium | ui/gui/web/app.js:1554 | A line the server refuses leaves the page locked: four of the page's five senders never look at the answer |  |
| suite-speed-13 | confirmed | low | .claude/hooks/quick_suite.sh:13 | A quick run turned away by the lock is read as a run that died, and the Stop hook blocks | yes |
| unneeded-files-7 | confirmed | low | .gitignore:21 | The ignore line for installer/models.iss carries a trailing comment, so it ignores nothing; the test checks only that the words are there |  |
| shell1-13 | confirmed | low | bestiary_check.py:28 | bestiary_check prints weights the game does not use, and crashes on a safe place |  |
| people-4 | confirmed | low | character/creation.py:178 | Sworn Enemy's subject is matched by substring, so 'Dwarven' swears against people and 'Seashell' against fiends |  |
| dead-switches-5 | confirmed | low | core/updates.py:105 | The update's exit stops only the dormant start's server, not the one the load screen started |  |
| trace-threads-7 | confirmed | low | core/updates.py:106 | Leaving for the installer stops only the dormant path's server; on the live start path nothing is stopped before os._exit |  |
| leftovers-1 | confirmed | low | core/updates.py:121 | RE-RATE shell1-9: nothing proves the installer the game downloads and runs: no digest, no size, no look at where the link points, one fixed file name in the temp folder, and no limit of one download at a time | yes |
| shell1-9 | confirmed | low | core/updates.py:124 | A download cut short is run as the installer, and the next start blames the release |  |
| logs-sendbacks-12 | confirmed | low | data/rules/guard.yaml:27 | The content guard's sexual list holds bare words with common innocent senses and no allow list: 'it cocks its head toward you' was sent back, and 'a naked blade', 'a cock crows', 'Dick the carter' are today |  |
| situations-4 | confirmed | low | engine/act.py:426 | A person here who is a part of two situations: a change addressed to them by their p code always lands in the last-listed situation |  |
| situations-3 | confirmed | low | engine/act.py:482 | A change an act's ruling says someone else did is kept as the act's own doing when that someone is not coded as a part of that situation |  |
| situations-13 | confirmed | low | engine/act.py:864 | A failed act's 'hurt' takes health with no ledger row and no line to the player; the fall and a part's hazard write both |  |
| engine1-5 | confirmed | low | engine/banter.py:224 | banter.repeats breaks a tie between shared runs by set order, so its answer changes with PYTHONHASHSEED |  |
| fight-abilities-9 | confirmed | low | engine/battlefield.py:166 | A foe turned to the player's side is still a foe to sweeps, cleaves, arcs, splashes, ground effects and Unmaking, and Dominate leaves it engaged with the player |  |
| trace-fight-11 | confirmed | low | engine/behaviors.py:66 | A fleeing foe cut down by No One Escapes is still set as fled and told as running |  |
| engine2-7 | confirmed | low | engine/canon.py:294 | canon.journal() swallows every exception, so a journal row that fails to write is lost without a trace |  |
| fight-abilities-7 | confirmed | low | engine/combat.py:2009 | Shadowmark's free return is refused when the pool is below the price of a new cast |  |
| fight-abilities-8 | confirmed | low | engine/combat.py:2347 | A command with no companion to obey still costs the mana, the cooldown and the turn |  |
| engine2-6 | confirmed | low | engine/combat.py:2453 | The player's own movement is told as 'You crosses to ...' and 'you falls back behind the line': battlefield's third-person phrases are glued to 'you' |  |
| trace-fight-9 | confirmed | low | engine/combat.py:2493 | A grappled player can flee and fall back; the rule says the held cannot |  |
| trace-fight-10 | confirmed | low | engine/combat.py:3049 | An enemy whose coat turns after it has had its turn gets a second turn start in the same round |  |
| silent-excepts-4 | confirmed | low | engine/combat_perks.py:695 | Eight broad guards catch an Interrupt (a cancelled call, a replay that parted) as an ordinary failure and carry on |  |
| silent-excepts-1 | confirmed | low | engine/crashlog.py:29 | 27 guards in game code swallow a fault with no record anywhere (10 around a state change, 17 that answer for the fault); crashlog has no record-and-carry-on helper | yes |
| engine3-10 | confirmed | low | engine/domain_events.py:253 | A theft's witness line reads 'Saw them took ...' / 'Saw them tried to take ...' |  |
| engine3-5 | confirmed | low | engine/equipment.py:28 | A raw material or a trade good can be equipped: it leaves the pack into a slot named 'none' |  |
| situations-9 | confirmed | low | engine/events.py:658 | A situation lost (events.lose) does not hand its release to the scene's own copies of its people, as finish() does |  |
| engine3-6 | confirmed | low | engine/exits.py:146 | 'The first' / 'the second' at a fork picks by the alphabetical order of the side names, not the order the question lists |  |
| engine4-5 | confirmed | low | engine/features.py:35 | features.leaving reads the pronoun 'it' as the place, so 'past it' or 'leave it' turns a walk inside the place into a search |  |
| fight-abilities-11 | confirmed | low | engine/healing.py:122 | The transfer heal's price is not what its card says: the caster pays 30% of what it heals, the full price when it heals almost nothing, and nothing when no ally is named |  |
| engine4-4 | confirmed | low | engine/matters.py:265 | on_arrival asks the model inside the arrival operation while it holds the loaded world state | yes |
| trace-replay-4 | confirmed | low | engine/moments.py:115 | Opening a save rolls the place's moment for the period: a state change, and on a hit a model call, that the same session played without the break never makes |  |
| engine5-2 | confirmed | low | engine/moments.py:116 | on_enter saves the place it loaded before end(), wiping the town-memory row the ended moment just filed |  |
| stale-copies-2 | confirmed | low | engine/moments.py:116 | RE-RATE engine5-2: the lost town-memory row is not rare; it follows every situation moment that ends away from the player at a town's top place |  |
| fight-abilities-12 | confirmed | low | engine/movement.py:103 | RE-RATE trace-fight-9: wider reach and a fix to adjust: eight of the eleven movement abilities carry a grappled player out of the hold, and the grappled status stays on them | yes |
| engine5-11 | confirmed | low | engine/names.py:29 | names.vocab() builds the 'ordinary words' set from every YAML under data/, tool-written and untracked files included, so name mending can differ between checkouts |  |
| engine5-3 | confirmed | low | engine/orenna.py:110 | The seal frees the Bound Executioner by dropping it from the fighter list without ending its engagements |  |
| engine5-6 | confirmed | low | engine/pulse.py:382 | Three model calls in this area are still made inside an operation's transaction (the f470 residue) | yes |
| engine6-6 | confirmed | low | engine/quirks.py:246 | Curse checks match a curse as the start of any word: 'Hello' counts as 'hell', 'arsenal' as 'arse' |  |
| trace-replay-5 | confirmed | low | engine/quirks.py:469 | borrowed() names the first of another speaker's words by set order, so the reason sent back to the model changes with the process's hash seed |  |
| engine6-1 | confirmed | low | engine/reactions.py:101 | A dismissed hire's leaving is never recorded: the row is removed before MemberLeft is published, so departed() finds nobody |  |
| engine6-5 | confirmed | low | engine/ruling.py:197 | The daily cap on people ruled into a place lives only in memory: a save and reload resets it, and it is never pruned | yes |
| engine6-7 | confirmed | low | engine/session.py:133 | CampaignSession.close marks itself closed first and has no try/finally: one raise in the recorder leaves the store open and this campaign's state in place for the next |  |
| situations-10 | confirmed | low | engine/situation_parts.py:459 | _in_force takes 'no effect row carries this part' for 'still in force': an adopted condition reads resolved when its effect runs out and in force again a day later, when the row is pruned |  |
| situations-11 | confirmed | low | engine/situation_parts.py:1272 | A ruling's 'lost' on a good changes the part and leaves its holder's stock: goods the record says are lost are still on sale |  |
| engine7-4 | confirmed | low | engine/spellcraft.py:25 | spellcraft captures the 'spells' stream at import, so it is always the process's dice, never a bound actor's; and a `combat.rng` arm that can never run | yes |
| fight-abilities-10 | confirmed | low | engine/summons.py:76 | Two summon castings share one serial after a foe is tamed or bound between them, so the standing cap lets three castings stand |  |
| unneeded-files-17 | confirmed | low | eventrun.bat:8 | The launchers ask for Python 3.10 or newer, but tools/eventrun.py needs 3.12 | yes |
| frontend-shipping-6 | confirmed | low | installer/meravia.iss:33 | An update installs over the old folder and removes nothing: data files a release dropped stay and are read, because the game reads data by folder |  |
| llm1-2 | confirmed | low | llm/audit.py:85 | audit.record() promises never to raise but catches only OSError: an answer holding half a surrogate pair as an escape crashes the call it records |  |
| logs-sendbacks-13 | confirmed | low | llm/contracts.py:506 | A clarifying question is sent back for the ordinary words 'intent' and 'action': 4 of 18 in the record, all false alarms |  |
| llm1-7 | confirmed | low | llm/contracts.py:796 | Maren's reply is sent back when it runs past 900 characters, with 'answer in one to four short sentences' |  |
| logs-sendbacks-8 | confirmed | low | llm/contracts.py:1029 | The stock-opener check takes the first word alone and the no-question check takes any question mark: 'See you then.', 'Right behind you.' and 'Trouble? Well, ...' are sent back (9 of 16 hits are false alarms) |  |
| llm1-8 | confirmed | low | llm/contracts.py:1051 | _clean_note misses first-person notes written with 'i', 'My', 'we' or 'our' |  |
| llm-checks-12 | confirmed | low | llm/contracts.py:1054 | Narration of the speaker inside the speech field passes every check and is printed under their name |  |
| llm-checks-9 | confirmed | low | llm/contracts.py:1282 | The back-to-work check on a dialogue frame sends back any 'returns', 'turns back', 'gets back' or 'resum...', whatever the sentence means |  |
| llm-checks-14 | confirmed | low | llm/contracts.py:2212 | A hire's personal details are sent back for any capitalised word in mid-sentence, taken as a name |  |
| llm1-5 | confirmed | low | llm/contracts.py:2260 | A reply to two or more characters skips every speech check a single reply gets |  |
| min-card-3 | confirmed | low | llm/gateway.py:263 | A try cut at the turn's deadline is charged the task's expected size, not the time it ran: the budget then counts room that is already gone |  |
| llm2-3 | confirmed | low | llm/gateway.py:274 | A background call's logged seconds include its wait for the card, so the call log overstates model time |  |
| llm2-6 | confirmed | low | llm/llama.py:120 | A thinking call's room is worked out against 32,768 tokens while a slot holds 16,384 |  |
| llm2-4 | confirmed | low | llm/runtime.py:963 | After a chat restart fails, Try again brings the model back without the embedder for the rest of the session |  |
| llm2-5 | confirmed | low | llm/runtime.py:1198 | An update's forced exit no longer stops the model server: stop_for_game knows only the dormant start |  |
| shell1-17 | confirmed | low | main.py:53 | The built game's --terminal cannot read a line: the build has no console |  |
| shell1-6 | confirmed | low | main.py:156 | Quitting or closing the window during character creation leaves a dead game in the Load list |  |
| trace-threads-5 | confirmed | low | npc/backfill.py:80 | A turn that waits on a background job waits with no limit of its own and outside the budget |  |
| trace-threads-1 | confirmed | low | npc/backfill.py:88 | Background residents are applied outside any transaction and a fault in the apply is swallowed, leaving people saved at the place who are not its residents |  |
| people-5 | confirmed | low | npc/life.py:238 | A person whose goal has ended is handed a new one at their first conversation, past the engine's cooldown |  |
| llm-checks-11 | confirmed | low | npc/life.py:576 | A townsperson reply's remember goes into their memory with no bound and no check | yes |
| people-2 | confirmed | low | npc/prompts.py:421 | The default reply request lists every memory row under YOUR MEMORIES OF THEM, whoever or whatever the row is about | yes |
| trace-save-3 | confirmed | low | scenes/arc_actions.py:59 | What waits on the player's next line after a fight is on the scene only: the yielded foe's question and the road walk to resume are lost at a close |  |
| leftovers-5 | confirmed | low | scenes/arc_actions.py:425 | Several foes who yield in one fight each get the same label and the same note: the fight golden shows 'The captured one of Marrow Hask's guard is your captive now...' three times running | yes |
| task-failures-7 | confirmed | low | scenes/audit_actions.py:125 | When the audit's own model call fails, a line that was read rightly is asked back as unclear, and the turn is logged as stood | yes |
| scenes1-9 | confirmed | low | scenes/banter_actions.py:359 | Only the last companion picked can ever bring up their motive: the loop variable is used after its loop |  |
| scenes1-8 | confirmed | low | scenes/camp_actions.py:246 | Model calls still made inside an operation's transaction in this area: camp_intent, discovery, arc_story | yes |
| scenes1-10 | confirmed | low | scenes/camp_actions.py:260 | A camp guard numbered 10 or more is read as guard 1 |  |
| scenes1-11 | confirmed | low | scenes/dungeon_actions.py:154 | A dungeon cache is told as taken whole even when the pack was full and the item was left on the ground |  |
| scenes1-13 | confirmed | low | scenes/dungeon_actions.py:186 | A remade dungeon's stale delve postings are cleaned only from the board where the player stands, with every error swallowed |  |
| scenes1-12 | confirmed | low | scenes/dungeon_actions.py:261 | One dungeon chamber can be searched for coin without end |  |
| scenes2-6 | confirmed | low | scenes/guild_actions.py:419 | A delve posting whose dungeon is gone is 'struck from the board' only in a list that is thrown away |  |
| scenes2-10 | confirmed | low | scenes/inventory_actions.py:185 | Discard and show look among key items first, by substring of any one word, before the pack is looked at |  |
| typed-patterns-6 | confirmed | low | scenes/inventory_actions.py:273 | RE-RATE engine1-6: takes_oneself is wrong both ways on real lines (yes on 43 lines with no use, no on all 21 uses), and a drink taken beside a word to a companion is refused with a question | yes |
| scenes2-7 | confirmed | low | scenes/law_actions.py:315 | A picklock ability used on a lock is checked for its cooldown but never starts one |  |
| typed-patterns-2 | confirmed | low | scenes/listening.py:66 | to_the_named was wrong on 4 of its 4 firings on real lines: words said to the party are re-aimed at the townsperson the same line nods to | yes |
| unmeasured-tasks-11 | confirmed | low | scenes/mentor_actions.py:188 | Maren's first appearance: the model's passage is kept only if it spells 'greatsword' and 'crest' or 'badge', and the test meant for the enamelled A matches the article 'a' |  |
| trace-replay-3 | confirmed | low | scenes/party_actions.py:752 | The hire who spoke last is kept only on the scene: after the game is opened again the answer to a companion no longer goes to them |  |
| task-failures-5 | confirmed | low | scenes/party_actions.py:804 | A companion whose reply fails says one fixed quip, kept as their answer: 'Does this come out of my fee?' to a question about their past, twice running |  |
| stale-copies-4 | confirmed | low | scenes/pastime_actions.py:112 | A failed haggle's cooling of the seller is never saved: the same line's pulse reads the people here again and the change is gone |  |
| scenes3-7 | confirmed | low | scenes/road_actions.py:546 | A walk to a kept landmark that is stopped by a won ambush resumes toward a stop already taken off the map |  |
| scenes3-9 | confirmed | low | scenes/shop_actions.py:210 | A quiet shop-pane purchase calls the narrator when the Tavern Ear perk is owned |  |
| task-failures-6 | confirmed | low | scenes/world.py:494 | A creature sighted during a search is told inline in the search's transaction: when the narrator fails the search is taken back, and the same words can never pass | yes |
| world_py-4 | confirmed | low | scenes/world.py:817 | populate_place is called with the walk's transaction open, and its failure takes the walk back |  |
| min-card-7 | confirmed | low | scenes/world.py:1063 | People a place still lacks are asked for after the line is typed and before its budget opens: up to three uncounted tries with only the 120 s hang guard |  |
| trace-save-4 | confirmed | low | scenes/world.py:1607 | When a line's first operation fails and a later one stands, the input's count goes back and is never saved: the next line with the same words gets the same dice and the same operation ids | yes |
| trace-turn-4 | confirmed | low | scenes/world.py:1607 | An operation that fails before the line's first commit takes the input's count back while the line goes on: the input is never counted, and the next one shares its dice key and operation ids |  |
| trace-turn-3 | confirmed | low | scenes/world.py:2466 | The 'NOT DONE this turn' row for a fourth action and beyond is added after the line's passage is written, so the narrator never sees it |  |
| typed-patterns-5 | confirmed | low | scenes/world.py:2567 | move_to_present drops what the player says when the words open with go, run, head, walk or take me: 'Go ahead and stamp it. Who else is around here...' is left as a look | yes |
| world_py-6 | confirmed | low | scenes/world.py:2775 | A bare '#' raises IndexError in command(): logged as a crash, answered with 'Nothing happens' |  |
| trace-turn-6 | confirmed | low | scenes/world.py:2780 | A bare '#' crashes the command: IndexError, written to the crash log, told as a turn that failed |  |
| stale-copies-3 | confirmed | low | scenes/world.py:4013 | A goodbye to someone who is here on their routine is saved on an object the scene has already replaced; the next word with them writes it away |  |
| world_py-7 | confirmed | low | scenes/world.py:4133 | craft_boost lives only on the scene: the ability's cost and cooldown are saved, the boost is gone after a reload; its numbers are in code |  |
| pane-commands-4 | confirmed | low | services/fight.py:662 | refresh() overwrites what the fight has done to the fighter and follows only part of the character: one attribute click restores corroded armour, and after a gear change the fighter is a mix of old and new |  |
| aged-save-5 | confirmed | low | services/fight.py:905 | RE-RATE people-3: the sixteen captive names are used up between lines 1,000 and 1,500 of a fighter's play, not in 'a long campaign'; by line 6,000 ninety-two captives share them |  |
| people-3 | confirmed | low | services/fight.py:905 | Captive names come from a list of sixteen, so the 'named apart from every name in the save' promise fails from the seventeenth captive |  |
| shell1-4 | confirmed | low | simbot.py:1520 | The bot reads npc.work_offer, npc.quest_offer and npc.trust, fields the NPC record has not had since f480 and f481 |  |
| shell1-12 | confirmed | low | simreport.py:262 | simreport reads events and fields the bot does not write, and prints the gaps as findings about the game |  |
| shell2-4 | confirmed | low | storage/campaign.py:298 | A save in the old file layout is marked current before it is imported: no migration step ever runs on it, and a failed import is never tried again | yes |
| shell2-2 | confirmed | low | storage/campaign.py:844 | A memory made without a minute is the first one trimmed once a person is at their cap |  |
| shell2-6 | confirmed | low | storage/invariants.py:111 | The check of a hire's opinions has a branch that can never report: an opinion about an id nobody has passes |  |
| shell2-3 | confirmed | low | storage/saves.py:169 | discard() erases a save that has a character when its database cannot be read or is from a newer build |  |
| tools1-5 | confirmed | low | tools/balance.py:49 | tools/balance.py raises TypeError on every scenario: fighter_from_creature has no `band` parameter |  |
| tools1-14 | confirmed | low | tools/botreport.py:52 | level_section raises StatisticsError when a class has no fight with a known foe level, losing the whole report |  |
| tools1-7 | confirmed | low | tools/card_profile.py:215 | --write prints Python None into the card profile YAML; a missing rate then stops the game at import |  |
| tools1-8 | confirmed | low | tools/event_trial.py:207 | The day-by-day report drops every news row that had not yet reached the town on the day it was made | yes |
| tools1-6 | confirmed | low | tools/event_trial.py:442 | Trial reports are written inside the save folder that every next Trial deletes |  |
| tools1-13 | confirmed | low | tools/eventrun.py:254 | The bot looks for an event's contract at the first guild hall in the world, not the hall whose board holds it |  |
| tools1-12 | confirmed | low | tools/eventrun.py:396 | travel_line gives up by adding a spawn, person, hall or town id to given_up, which is only ever read as path ids |  |
| tools1-2 | confirmed | low | tools/eventrun.py:585 | The 'event never started' branch calls run.finish() before run.bot exists and dies with AttributeError |  |
| tools1-9 | confirmed | low | tools/interp_eval.py:60 | Bench has no close: the session stays open, the stub stays installed and two module functions stay replaced after evaluate() returns |  |
| tools1-4 | confirmed | low | tools/latency.py:81 | The 'Read tok/s' column divides read-plus-reused tokens by the time spent on the read ones only, overstating the card's read speed |  |
| tools2-10 | confirmed | low | tools/live_gate.py:128 | A gate that could not run leaves exit code 1, the code for a missed floor |  |
| tools2-2 | confirmed | low | tools/lora_dataset.py:67 | An answer taken only on the gateway's relaxed last pass is written into the training set as a first-try example |  |
| tools2-6 | confirmed | low | tools/nightbot.py:439 | Any conversation counts the bot's report as made: the report goal is popped by whoever it is talking to |  |
| leftovers-11 | confirmed | low | tools/nightbot.py:860 | The bot asks its model to search a place 'for' a contract's or a situation's title, and to go to a part of a place by its internal id; the line it then types is one no player would write |  |
| tools2-7 | confirmed | low | tools/nightrun.py:97 | A run given an out folder that already holds a run appends to its logs; the live gate then measures both runs as one |  |
| tools2-8 | confirmed | low | tools/nightrun.py:250 | On Windows with the output piped, one character outside the code page in a progress line ends the night with a turn written twice and no run.json |  |
| leftovers-3 | confirmed | low | tools/prose_baseline.sh:16 | prose_baseline.sh deletes the game's own call log twice and leaves none behind: its two measuring tools can only write to logs/llm_calls.jsonl, so the script clears and carries off the shared file | yes |
| tools2-5 | confirmed | low | tools/pulse_preview.py:96 | The pulse preview crashes on every run after the first: each run's first situation gets the same id |  |
| tools2-14 | confirmed | low | tools/pulse_preview.py:119 | The preview's fast-forward finds new news by the list's remembered length, which folding and the cap do not change | yes |
| tools3-6 | confirmed | low | tools/run_suite.py:45 | --changed never sees data/runtime/server.yaml, the JSON content files or the page's HTML and CSS | yes |
| tools3-7 | confirmed | low | tools/run_suite.py:371 | Hard-coded /tmp defaults land in C:/tmp on Windows, a different folder from Git Bash's /tmp |  |
| tools3-9 | confirmed | low | tools/situation_ab.py:492 | The blind reads parser takes the word 'a' after any number as a vote for A, on comment lines too |  |
| tools3-5 | confirmed | low | tools/voice_report.py:61 | The voice report no longer tells hires apart: its two patterns do not match the hire prompt, so every hire is one speaker, 'a hire' | yes |
| tools3-4 | confirmed | low | tools/world_report.py:55 | The world report counts game days from rows it does not count; 'parts' rows are dated minute 0, so a run gains a Day 1 and its per-day rates are diluted |  |
| trace-threads-8 | confirmed | low | ui/gui/__init__.py:41 | Closing the window in the middle of a turn cancels no model call: the process lingers up to 10 s, then the game thread is cut off wherever it is |  |
| shell2-5 | confirmed | low | ui/gui/__init__.py:67 | With the browser standing in for the window, closing the tab leaves the game and its model server running with nothing to stop them |  |
| pane-commands-5 | confirmed | low | ui/gui/bridge.py:121 | Once the bridge is closed and the game thread has not finished, the event stream writes pings with no pause: 89,449 in one second and a core and a half busy |  |
| frontend-shipping-10 | confirmed | low | ui/gui/web/app.js:67 | esc() does not escape quotes and is used inside attributes: a place name with a double quote breaks out of the tag |  |
| frontend-shipping-9 | confirmed | low | ui/gui/web/app.js:929 | The page keeps its own copy of the view names: 26 of the game's 49 are missing, and a view typed by one of them during a fight is never shown |  |
| frontend-shipping-8 | confirmed | low | ui/gui/web/app.js:1090 | On the home page the hidden story box holds the focus: Enter on the Load list or Settings loads the last game, or begins a new one |  |
| trace-turn-5 | plausible | medium | scenes/check_actions.py:81 | A check on a search or an improvised act replaces the action: on_search and the act's ruling never run, yet the step is recorded as done |  |
| frontend-shipping-4 | plausible | medium | tools/installer_files.py:50 | The installer copies the 8 GB of model files out of the temp folder without checking the copy, asks Setup for no room for them, and takes 'the file exists' for 'the file is whole' |  |
| typed-patterns-11 | plausible | low | engine/clock.py:72 | RE-RATE engine2-4: hour_named said yes on none of 1,896 real lines while the model filled the time on every timed wait; the override should go, not be narrowed | yes |
| silent-excepts-2 | plausible | low | engine/deeds.py:44 | deeds.log drops a ledger write without a word, and the reactions go on to act on a deed the save does not hold | yes |
| silent-excepts-3 | plausible | low | engine/events.py:399 | The town's thanks for a settled matter is skipped with no record at three places (events.py 399, 723, 1443) |  |
| silent-excepts-8 | plausible | low | engine/events.py:1207 | A read that fails is taken as an answer at thirteen places: level 1, not in town, an empty pack, nobody on the road, no board, no guard |  |
| engine5-4 | plausible | low | engine/pulse.py:358 | start_thread indexes world.pressures with a queued pressure id it never checks; a follow-on whose pressure the world lacks raises KeyError inside the pulse |  |
| llm1-3 | plausible | low | llm/audit.py:45 | In the built game the audit log is written inside the bundle, not beside the exe with the other logs |  |
| llm1-6 | plausible | low | llm/embed.py:89 | vectors() reads the cache again after the server call: a cached text trimmed meanwhile, or a short answer, is a KeyError | yes |
| silent-excepts-6 | plausible | low | llm/gateway.py:371 | The mends of an answer already taken (no dashes, names put right, the A1 mend count) can stop half way with no record (gateway.py 371 and 379) |  |
| leftovers-6 | plausible | low | llm/llama.py:443 | An embedding answer with status 200 and wrong-shaped vectors is taken as real: empty, short and all-zero vectors are cached and every check by meaning answers 'nothing alike'; nulls raise a TypeError outside the handler. The fake never answers so | yes |
| people-7 | plausible | low | npc/backfill.py:86 | A failed background batch is dropped without a word, and a fault while applying it leaves people saved but not in the place |  |
| silent-excepts-5 | plausible | low | scenes/law_actions.py:400 | Any fault while judging a lock or an object is told to the player as a fact of the world ('There is no lock here that you can find.') and filed as an ordinary refusal |  |
| silent-excepts-7 | plausible | low | storage/migrations.py:128 | Migration steps v8 and v6 are marked done when the player's row could not be read | yes |
| suite-speed-5 | plausible | low | tools/run_suite.py:285 | A killed run frees the lock at once while the tests it started run on in saves/, and the record of what it had finished is lost | yes |
| frontend-shipping-5 | plausible | low | ui/gui/__init__.py:49 | Without the WebView2 runtime the window opens on the old Internet Explorer engine and stays blank: the browser fallback is taken only when pywebview raises |  |
| leftovers-2 | refuted | low | installer/meravia.iss:141 | Setup downloads Microsoft's WebView2 bootstrapper with no hash and runs it silently: the one unpinned file on a page whose header says each is checked against its sha256 |  |
| llm-flow-9 | refuted | low | llm/backend.py:157 | think_room measures a thinking call against both slots' context (32,768) where one slot holds 16,384 | yes |

## Use of the model (75)

| id | checked | weight | place | finding | known |
|---|---|---|---|---|---|
| logs-sendbacks-1 | confirmed | high | llm/contracts.py:1112 | RE-RATE llm-hot-7: the tracked record confirms the runaway side field (9 of 701 townsperson replies ran to 2,048 tokens, all nine inside journal_note) and widens it to the understanding's summary (4 of 2,477 lines ran to 700 tokens) | yes |
| min-card-2 | confirmed | high | llm/contracts.py:1112 | RE-RATE llm-checks-1: journal_note is the minimum card's breach of the 60 s limit, not only wasted writing: 9 of the 17 recorded lines over 60 s are a reply that ran to 2,048 tokens inside it, and on a 3060 that reply is cut and lost | yes |
| unmeasured-tasks-3 | confirmed | medium | character/creation.py:56 | One badly worded ability sends all fifteen back: the check knows which slot numbers failed, and the whole set is asked again, up to five whole answers |  |
| engine1-2 | confirmed | medium | engine/ability_slots.py:759 | Generated ability text is rejected on substring matches ('individual' reads as 'dual', 'amount of' as a mount), which sends the whole ability set back to the model |  |
| unmeasured-tasks-2 | confirmed | medium | engine/ability_slots.py:773 | RE-RATE engine1-2: wider reach. A third check in text_problem sends the ability set back: the element reading takes 'Grave Promise', 'Cold Steel', 'Iron Bark Stance' and 'Burnished Edge' on a plain technique as necrotic, cold, nature and fire |  |
| llm-hot-8 | confirmed | medium | engine/candidates.py:88 | The interpreter's PLACES list is filled to 32 with the insides of other towns on every line, whatever the words are about |  |
| engine2-5 | confirmed | medium | engine/canon.py:74 | first_person() turns a written detail into broken first person ('I hums', 'sent my small bits') and leaves 'He ...' details untouched; these lines feed canon_extract and canon_check |  |
| engine6-9 | confirmed | medium | engine/situations.py:585 | situation_parts is asked with free-string ids, so the model spends its answer inventing people the check then throws away |  |
| logs-fields-2 | confirmed | medium | llm/contracts.py:824 | A hire's reply writes impression and they_promised on every line: impression was filled 0 times in 1,182 replies, the promise 7 times, 4 of them on a line that promised nothing | yes |
| llm-hot-7 | confirmed | medium | llm/contracts.py:854 | Short side fields are kept short by a prompt rule and a rejection; the grammar could end them and is used that way for one field only | yes |
| llm-hot-4 | confirmed | medium | llm/contracts.py:1112 | journal_note (known): no request said a note was due, and all 12 replies wrote one, 40% of what the townsfolk wrote | yes |
| llm1-1 | confirmed | medium | llm/contracts.py:1112 | A townsperson's reply has a place for a journal note on every call; in the played session none was due and the note was 40% of what the model wrote | yes |
| llm-flow-7 | confirmed | medium | llm/gateway.py:336 | A passage is sent back and written whole again for one compound the model joined with an underscore ('broad_shouldered', 'mud_slick'), which the page's own cleaning would have mended: 5.8 s on 2 of 26 narrations |  |
| logs-sendbacks-4 | confirmed | medium | llm/gateway.py:336 | RE-RATE llm-flow-7 (with llm-checks-2, llm-hot-6): underscore joins are the largest single reason the game sends anything back, 171 of 556 (not 2 of 26), in six tasks; and the proposed mend needs a full-stop rule, since clean() glues two sentences in about 50 of them | yes |
| llm-hot-5 | confirmed | medium | llm/gbnf.py:221 | The grammar lets every reply be laid out over indented lines, and the model does: layout is 5 to 34% of what the structured tasks write | yes |
| llm2-1 | confirmed | medium | llm/llama.py:367 | The shared slot re-reads nearly every prompt and pays for checkpoints it never restores (the f536 question, measured) | yes |
| trace-fight-8 | confirmed | medium | scenes/combat_prompts.py:19 | A typed line that is no fight action has no reading: it is resolved as an improvised gamble and costs the round | yes |
| llm-flow-8 | confirmed | medium | scenes/voice.py:128 | fresh() throws a finished passage away and asks for it again on 5 of 24 narrations (worn words 3, stale phrase 2, invented speech 1): 14.6 s, 5.4% of turn time | yes |
| logs-sendbacks-11 | confirmed | low | engine/hygiene.py:97 | The gate sends back a literal backslash-n (15 of 15) and a stray JSON tail (4 of 6) that hygiene.clean() already mends on the way to the screen | yes |
| llm-checks-2 | confirmed | low | engine/hygiene.py:103 | A word the model joined with an underscore is sent back for a whole new call, though hygiene.clean mends the same thing in place: both narrator send-backs of the Gemma run | yes |
| llm-rest-1 | confirmed | low | engine/intent_audit.py:217 | The audit's unmatched_verb flag tests every bare word of the line, so a noun or a word inside the question asked sends the line to the audit | yes |
| typed-patterns-9 | confirmed | low | engine/intent_audit.py:217 | RE-RATE llm-rest-1: the audit's word test sends 43.7% of real lines to two more model calls; unmatched_verb fires on 165 of 1,887 lines, on nouns | yes |
| llm-rest-2 | confirmed | low | engine/intent_audit.py:284 | A 'does not match' from audit_compare has no effect when the second reading repeats the plan: no audit changed a plan in the played run | yes |
| typed-patterns-10 | confirmed | low | engine/intent_audit.py:284 | RE-RATE llm-rest-2: in the 54 tracked logs the audit did change plans: 173 of 917 audits led to a second reading and 138 of those came back different | yes |
| unmeasured-tasks-5 | confirmed | low | engine/mentor.py:735 | Maren's speech is sent back for ordinary words: 'game trail', 'half a mind', 'Two things', 'double back' and 'a model soldier' fail the figures check and the game-talk check |  |
| llm-rest-4 | confirmed | low | engine/stakes.py:93 | board_stakes text reaches a person's concern, place marks, town memory, news and a matter with no check that the names in it exist |  |
| engine7-2 | confirmed | low | engine/threads.py:524 | The thread_telling prompt is four fifths two lists the call does not need: every place id of the world, and the bestiary cut off alphabetically at 3000 characters |  |
| llm-rest-3 | confirmed | low | engine/towns.py:157 | Every profile of a town is handed all of the town's troubles and left to pick one: three of three Parth profiles took the same concern |  |
| logs-sendbacks-9 | confirmed | low | engine/voices.py:147 | RE-RATE llm-checks-13: in 1,340 speaker replies the mechanical faults are 17 (openers 10, underscores 7; no asterisk, no quotation mark, no over-long side field), and the proposed mend 'cut the opener' would break half of the opener hits |  |
| unmeasured-tasks-9 | confirmed | low | llm/contracts.py:68 | RE-RATE engine6-9: wider reach. Eight more answer fields are ids the engine knows, left as free strings: a wrong one sends the answer back (families, option_id, arc node ids, kit ids, discovery type, way and roles) or is silently lost (lesson effect and stat, cataclysm path id) | yes |
| logs-fields-9 | confirmed | low | llm/contracts.py:475 | A measure for the one-reader plan: summary is 46% of what the interpreter writes (0.9 s a typed line on the 3060) and R3 adds a words field beside it | yes |
| logs-fields-11 | confirmed | low | llm/contracts.py:496 | Eight more id fields are free strings although the engine holds the whole valid set for the call; the record shows what that costs today: 3 wrong values in about 1,900 | yes |
| leftovers-10 | confirmed | low | llm/contracts.py:595 | RE-RATE llm-checks-5: the night bot's line is this kind's worst case with Gemma: `{}` on 451 of 2,251 first tries (20%), which is 41% of every row sent back in the tracked logs | yes |
| logs-fields-4 | confirmed | low | llm/contracts.py:621 | audit_compare's reason is nine tenths of its answer and is only logged when the plan matched (744 of 924 audits) | yes |
| unmeasured-tasks-10 | confirmed | low | llm/contracts.py:629 | camp_intent writes a summary nothing reads, on every line typed at a camp |  |
| llm-checks-5 | confirmed | low | llm/contracts.py:642 | The reading of the player's message may be an empty list in the grammar, then is sent back for being empty | yes |
| logs-fields-10 | confirmed | low | llm/contracts.py:696 | Fields the engine knows it will not keep this call stay in the grammar in four more contracts: a moment's visitor, a posting's 'more', a profile's motive, a second caller's 'which' | yes |
| llm-hot-3 | confirmed | low | llm/contracts.py:1099 | A townsperson's reply asks for 12 fields on every line; 7 were never filled in 12 replies, and all are written after the speech the player is waiting for | yes |
| llm-checks-4 | confirmed | low | llm/contracts.py:1104 | reveals is a free list of strings: Gemma fills it with sentences from the prompt and made-up ids, which the engine then drops | yes |
| llm-hot-2 | confirmed | low | llm/contracts.py:1104 | reveals is a free list of strings: the model wrote 10 in 12 townsperson replies and the game kept none | yes |
| logs-fields-1 | confirmed | low | llm/contracts.py:1240 | The fight's reader writes a summary on every line and the game reads it only for kind 'other': half the answer, unread in all 291 fight lines of the record | yes |
| logs-sendbacks-10 | confirmed | low | llm/contracts.py:1302 | A frame that echoes a heading of the request is sent back, and 9 of 13 such rows ended in a lost frame, though the prose before the heading was a good frame in 11 |  |
| logs-fields-6 | confirmed | low | llm/contracts.py:1328 | The model picks each starting perk's number: tier chooses between the perk's two values, and the request shows it only the higher one | yes |
| llm-hot-6 | confirmed | low | llm/gateway.py:336 | One word joined with an underscore sends the narrator's whole passage back, though the engine already has the mend for it |  |
| llm-checks-8 | confirmed | low | llm/gateway.py:392 | A reply with two faults takes two retries: the checks stop at the first fault, and each retry carries only the last draft and its one reason |  |
| logs-sendbacks-6 | confirmed | low | llm/gbnf.py:233 | RE-RATE llm-checks-16: Gemma does write other scripts, 54 times in the record (37 narrations), nearly always one function word in mid-sentence (31 are the same Korean word for 'his'); a grammar character rule would stop 46 of the 54 | yes |
| llm-hot-11 | confirmed | low | npc/prompts.py:400 | A townsperson's request says the place, the hour and the town's state twice and carries the faith paragraph on every line | yes |
| unmeasured-tasks-8 | confirmed | low | scenes/arc_actions.py:168 | Three requests are mostly a whole-world list: arc_story sends every person's name in the save (81% of the request, no cap), discovery every place and road name (75%), pulse_thread every place id and road (51 to 70%) |  |
| llm-checks-3 | confirmed | low | scenes/party_actions.py:613 | The no-such-building check reads a town list the prompt withheld, so the first call is spent on a fact the speaker was never given | yes |
| logs-fields-3 | confirmed | low | scenes/quirk_actions.py:294 | A hire's line about a happening asks for the talk's five fields and reads two: remember was written and dropped in 114 of at least 210 such lines |  |
| logs-sendbacks-14 | confirmed | low | scenes/voice.py:51 | fresh() rewrites a whole passage for a five-word run of little words shared with the last four narrations ('at the far end of', 'in the center of the', 'the rest of the crowd'): 24 of the 82 stale-phrase rewrites had no other cause | yes |
| llm-hot-1 | confirmed | low | scenes/voice.py:114 | A narrator's draft that uses two worn words or one reused phrase is written again whole: 6 of 26 narrate calls in the played run were second passages | yes |
| dead-switches-7 |  | low | data/rules/sampling.yaml:46 | The list of narrator prose tasks is kept in four places and they disagree: the fight's aftermath and road events get no worn-word guard |  |
| llm-hot-12 |  | low | engine/brief.py:64 | YOU ALSO KNOW OF names every other fact a townsperson knows by its id, with no cap, and tells them it is theirs to tell | yes |
| engine2-10 |  | low | engine/canon.py:426 | settle_again asks the model again about the same two waiting claims on every keep when their bucket is full, and the claims behind them never get a turn |  |
| data-7 |  | low | engine/threads.py:525 | A thread's re-telling is sent the bestiary's names A to G only (cut at 3000 characters) and every place id, as the list of what may be named |  |
| llm-checks-13 |  | low | engine/voices.py:147 | Faults with a mechanical repair are sent back for a whole new reply: a stock opener, an asterisk, a quotation mark, a side field a few words too long |  |
| llm-rest-7 |  | low | llm/contracts.py:1243 | The three item-naming contracts accept an empty or run-on name, which then replaces the engine's own name on the item |  |
| llm-rest-9 |  | low | llm/contracts.py:1867 | event_judge is made to answer verdict, reason and ending, and the engine reads only changes | yes |
| llm-checks-15 |  | low | llm/contracts.py:1912 | A road event's kind is the engine's choice, yet the model is asked to write it and three checks test it; one can never fire and two test the same thing |  |
| llm-checks-16 |  | low | llm/gbnf.py:233 | A character of another alphabet is found only after the whole call; the grammar's char rule lets any character through |  |
| llm-hot-14 |  | low | npc/life.py:129 | Token ceilings and the budget's expected sizes are far from what the tasks write: 3,000 for residents that take 221 to 613, 700 for a reading that takes 103 at most | yes |
| llm-rest-12 |  | low | npc/life.py:248 | npc_profile carries a voice field the prompt tells the model to leave empty; it is stored, and two requests then print 'VOICE: plain' for everyone |  |
| people-12 |  | low | npc/prompts.py:6 | populate_place has the model copy every name back, and the engine never reads the copy |  |
| llm-rest-6 |  | low | scenes/audit_actions.py:79 | audit_meaning decides nothing: a paraphrase of the typed line, asked as its own request before audit_compare, which is given the typed line as well |  |
| scenes1-16 |  | low | scenes/banter_actions.py:850 | A pair's line is marked rewritten even when the rewrite call was dropped or failed; two temperature arguments do nothing |  |
| llm-rest-11 |  | low | scenes/camp_actions.py:313 | At a camp every typed line is read twice: camp_intent first, then interpret_action when the answer is none |  |
| scenes1-15 |  | low | scenes/combat_scene.py:1348 | Every naming request carries the whole, uncapped list of taken names |  |
| scenes2-11 |  | low | scenes/law_actions.py:105 | Model calls made while an operation holds the save's transaction open (the f470 residue, in this area's files) | yes |
| llm-rest-10 |  | low | scenes/party_actions.py:113 | party_intent still offers the model two kinds the engine throws away, and sends the hire roster it no longer uses |  |
| llm-hot-10 |  | low | scenes/party_actions.py:442 | A hire's one description (role, rank, blurb, Manner) goes whole to every reader: a fifth of the interpreter's request, and a stranger's inner manner to townsfolk |  |
| llm-rest-5 |  | low | scenes/quirk_actions.py:59 | A hire's details and secrets are written inline at the first line that touches the party, ahead of the narration the player waits for |  |
| llm-rest-8 |  | low | scenes/road_actions.py:625 | The road-hazard ruling asks for a full ruling and reads three fields of it | yes |
| scenes3-8 |  | low | scenes/voice.py:35 | The stock phrases the checker sends back and the ones the narrator is told to avoid are two hand-kept lists that differ | yes |
| tools3-8 |  | low | tools/think_ab.py:145 | think_ab no longer sends the request the game sends: the contract's own grammar for act_ruling, and a stale copy of the sampler list | yes |

## Speed (46)

| id | checked | weight | place | finding | known |
|---|---|---|---|---|---|
| speed-turn-1 | confirmed | high | engine/data_check.py:367 | The startup check takes 9 to 12 seconds on every launch: a pure-Python YAML loader, files parsed up to six times, source scans redone each time |  |
| llm-checks-1 | confirmed | high | llm/contracts.py:1112 | A townsperson's reply always carries journal_note in its grammar; with no note due Gemma fills it anyway and the engine throws it away (about 44% of the reply's write time) | yes |
| suite-speed-2 | confirmed | high | tools/run_suite.py:61 | A quick run counts every untracked file as changed and picks tests by the bare word of its name: 437 of 519 tests today, with no tracked change in the list |  |
| data-6 | confirmed | medium | engine/data_check.py:20 | The startup check parses every data YAML with the pure-Python loader, most of them two to five times: 1.8 to 5 s at every start against 0.24 to 0.9 s | yes |
| engine3-7 | confirmed | medium | engine/data_check.py:20 | The startup check takes about 9 seconds: pure-Python YAML loader, the same files parsed up to 6 times, source files re-parsed per check |  |
| suite-speed-1 | confirmed | medium | engine/data_check.py:20 | The whole data check runs about 50 times a suite run on PyYAML's pure-Python loader: the 31 tests that call it take 460 s of the 1,706 s of test time | yes |
| llm-hot-15 | confirmed | medium | npc/prompts.py:61 | Known: the speaking and telling tasks' system prompts (5,000 to 8,900 chars) are read again on nearly every call, about 46% of all the session's reading | yes |
| unmeasured-tasks-1 | confirmed | medium | scenes/goddess.py:478 | Ten model calls stand between New Game and the first typed line (11 with a companion class, 18 in typed creation): 150 to 181 s of model time on the minimum card, about 66 s of it one foreground wait for the fifteen abilities |  |
| unmeasured-tasks-6 | confirmed | medium | scenes/mentor_actions.py:102 | A line Maren's free speech fails is asked for twice more before the written line shows: mentor_speech, mentor_speech again inside mentor_say, then mentor_voice, two attempts each | yes |
| llm-flow-6 | confirmed | medium | scenes/world.py:817 | The first people of a place and a person's profile are written inside the turn that needs them: 16.3 s here (6% of turn time), about 9.6 s for a new place and 3.5 s for a first talk on the minimum card |  |
| logs-fields-8 | confirmed | medium | scenes/world.py:3278 | RE-RATE llm-hot-14 (and llm-hot-7's note that summary never ran long): the interpreter's summary does run away, 4 of 2,481 readings wrote a repeated phrase to the 700-token ceiling | yes |
| suite-speed-8 | confirmed | medium | tools/run_suite.py:416 | The suite uses 4 of this machine's 28 logical processors, in name order with a 39 s test among the last twelve |  |
| speed-turn-3 | confirmed | medium | world/campaign.py:185 | Every stand-down for a model call throws away the map's caches: restore() moves the version though nothing on the map changed |  |
| speed-turn-5 | confirmed | low | engine/mapview.py:86 | The first line of every session pays a 1.1 to 1.4 second spring layout for 45 dungeon entrances, and the cost grows as the square of the places a save adds | yes |
| aged-save-4 | confirmed | low | engine/pulse.py:165 | The news window asks the map for a route for every news row each time the facts are built: 167 route questions and 21 to 29 ms of every plain line once the news is at its cap | yes |
| logs-sendbacks-15 | confirmed | low | llm/contracts.py:595 | The night bot's line is optional in the grammar and refused when empty: 451 of its 2,759 calls answered '{ }' and were asked again, a fifth of the bot's model time |  |
| llm-flow-1 | confirmed | low | llm/runtime.py:230 | The shared slot reads every prompt from its first token: 92 of its 105 requests followed another task and had nothing cached (61.9 s of reading, 23% of the run's turn time) | yes |
| min-card-6 | confirmed | low | llm/runtime.py:230 | RE-RATE llm-flow-1: at the minimum card's rates the shared slot's cold reads are the largest ordinary cost a line carries, 3.4 to 4.9 s a line (16 to 23% of all line time) | yes |
| llm-flow-2 | confirmed | low | llm/runtime.py:233 | Context checkpoints cost 27.6 s (10% of turn time) and were restored in 18 of 154 requests; on the shared slot 268 were made for 2 restores | yes |
| trace-threads-2 | confirmed | low | llm/worker.py:150 | A background call let in after max_wait or three cancels cannot be interrupted, so the turn's calls move to the understanding's slot and erase its cached prompt | yes |
| llm-flow-4 | confirmed | low | llm/worker.py:150 | A background job that never finds two idle seconds runs beside the turn 120 s later, for a place the player has left, pushes the turn's calls onto the understanding's slot, and meanwhile no other place can start its backfill | yes |
| unmeasured-tasks-7 | confirmed | low | scenes/mentor_actions.py:576 | RE-RATE llm-flow-6: different weight. In Maren's lesson the walk to the hall carries the hall's first people and a person's profile on top of three Maren and narrator calls: five required calls, 45 to 97 s on the minimum card, for a place known five lines ahead |  |
| llm-flow-5 | confirmed | low | scenes/world.py:1892 | A situation's birth is asked in the foreground after the passage: 10.4 s on 2 of 42 lines here, about 20 s each on the minimum card, while the player can read but not type | yes |
| llm-flow-3 | confirmed | low | scenes/world_prompts.py:73 | The understanding's request puts the PLACES list (changed by the typed words on 33 of 38 lines) second from the top, so 885 tokens are read again each line though 85% of the request's lines did not change | yes |
| llm-hot-13 | confirmed | low | scenes/world_prompts.py:296 | A dialogue frame reads about 2,200 tokens to write two sentences: its reading costs more than its writing, as do hire_chat, combat_interpret and canon_extract | yes |
| aged-save-3 | confirmed | low | storage/worldtables.py:169 | RE-RATE trace-save-5: reading the whole world 14 times a line is not 2 ms on an aged save but 45 to 55 ms, the largest part of a plain line that has gone from 8-17 ms to 100-190 ms | yes |
| tools2-4 | confirmed | low | tools/model_fence.py:97 | The model fence parses every .py under the folder, .venv, .buildenv and the worktree copies included: 24 s where the tracked files take 6 | yes |
| suite-speed-9 | confirmed | low | tools/run_suite.py:285 | Start-up is about 40% of all test time: each of 519 processes imports the game again (0.7 to 1.4 s) before its test begins |  |
| speed-turn-4 | confirmed | low | world/loader.py:272 | The route cache works out its signature over every place on every neighbors() and path() call: 144 thousand times in 46 turns | yes |
| engine1-8 |  | low | engine/ability_slots.py:132 | Rule files are read and parsed again on each call, four times with the slow pure-Python loader that f558 replaced |  |
| engine3-11 |  | low | engine/drift.py:269 | drift.standing() reloads the stored player on every pass, against the module's own note, and reads a stale record | yes |
| engine4-6 |  | low | engine/matters.py:145 | One talk turn parses the whole world state about five times in matters alone | yes |
| engine4-7 |  | low | engine/matters.py:339 | A pending summons loads every person of the town on every turn it cannot be sent |  |
| engine7-7 |  | low | engine/targets.py:92 | targets_for loads the whole world state twice in one call | yes |
| speed-turn-6 |  | low | engine/truth.py:432 | One route search per goal where the question is how far it is from here to each of many places: the town facet asks up to 102 searches for one prompt |  |
| people-11 |  | low | npc/life.py:100 | The residents plan runs in full before every input, loading every townsperson to read one field |  |
| scenes1-14 |  | low | scenes/arc_actions.py:137 | The arcs store is never trimmed and is read and parsed whole on every refresh of who is present |  |
| llm-hot-9 |  | low | scenes/world_prompts.py:73 | The interpreter's request puts the section that changes with every line third, so the sections that do not change are read again each time | yes |
| trace-save-5 |  | low | storage/campaign.py:584 | A plain line reads the whole operations row 13 times, the whole world 14 times and asks the schema 20 times: about 2 ms today, but the cost grows with the save | yes |
| shell2-10 |  | low | storage/campaign.py:595 | Every operation parses the whole record of the last 200 operations twice and writes it back whole |  |
| shell2-9 |  | low | storage/campaign.py:800 | The memory table's column list is asked of SQLite for every person loaded and every memory written |  |
| tools1-11 |  | low | tools/interp_eval.py:219 | The whole turn log is parsed again after every case to take its last row (quadratic in the corpus) |  |
| tools1-10 |  | low | tools/line_census.py:258 | The census walks the same (function, parameter) pairs about nine times over; every suite run pays about 7.5 s for it |  |
| frontend-shipping-11 |  | low | ui/gui/web/app.js:156 | The transcript is never trimmed and every line added forces a layout of all of it: the cost of a turn grows with the length of the sitting |  |
| people-10 |  | low | world/loader.py:272 | Every route lookup recomputes a signature over all places, and the campaign map's cache inherits it | yes |
| min-card-8 | refuted | medium | llm/gbnf.py:221 | RE-RATE llm-hot-5: layout in the grammar is the smallest of the five savings on the minimum card, 0.46 s a line (2.1% of line time), and does nothing for the lines near the limit |  |

## Dead code and unneeded files (79)

| id | checked | weight | place | finding | known |
|---|---|---|---|---|---|
| scenes3-10 | confirmed | medium | scenes/party_actions.py:73 | party_notice still tells the player to say 'recruit help'; the typed hiring path behind it cannot be reached | yes |
| unneeded-files-6 | confirmed | low | .gitignore:39 | Six tracked files that .gitignore says to leave out, and one more of their kind: sandbox run scripts with a path that exists nowhere, and their two reports (134 KB) | yes |
| unneeded-files-16 | confirmed | low | build_exe.bat:13 | The built game ships data/replay (2.07 MB of test recordings, saves and corpora), though the code says a build ships without it |  |
| unmeasured-tasks-4 | confirmed | low | character/creation.py:65 | The old one-call abilities flow is kept as a fallback nothing reaches: 0 of 440 plans raise, a model failure does not go there, no test runs it, and it would let the model choose every mechanic |  |
| people-14 | confirmed | low | character/creation.py:330 | Dead code in the people files: a save nobody reads, constants and functions with no caller | yes |
| dead-code-1 | confirmed | low | character/history.py:1 | (a) character/history.py is imported by nothing: the whole module is dead |  |
| people-13 | confirmed | low | character/history.py:1 | character/history.py has no importer |  |
| shell1-15 | confirmed | low | core/models.py:56 | CompanionKind and CompanionRole are defined and used nowhere |  |
| data-8 | confirmed | low | data/world/mentor.yaml:205 | Authored text and fields nothing reads: 13 keys of mentor.yaml (about 3.2 KB of lines) and five more fields in other world files | yes |
| dead-code-3 | confirmed | low | docs/patches/perf_easy_wins.patch:1 | (a) The two patch files under docs/patches are already applied to the tree |  |
| unneeded-files-9 | confirmed | low | docs/patches/perf_easy_wins.patch:1 | Both patch files are fully applied and can no longer apply; the two docs that describe them describe finished work (92 KB) |  |
| dead-code-2 | confirmed | low | docs/tests/improv_dice_repro_test.py:1 | (a) docs/tests/improv_dice_repro_test.py is a byte-for-byte copy of the test in tools/sim |  |
| dead-code-17 | confirmed | low | engine/ability_traits.py:160 | (e) Parameters no call passes and no body reads |  |
| engine1-9 | confirmed | low | engine/battlefield.py:89 | Definitions with no caller in any tracked file, and imports and parameters nothing reads | yes |
| dead-code-8 | confirmed | low | engine/behaviors.py:40 | (b) text_for() has no caller, so the 48 `text:` lines of data/world/families.yaml never reach the narrator | yes |
| dead-code-10 | confirmed | low | engine/canon.py:22 | (b) Eleven module constants that nothing reads |  |
| engine2-11 | confirmed | low | engine/canon.py:351 | Dead code in this area: canon.keep_now, STATE_DAYS, MAX_CANON, combat_perks._tick, seven unused 'import yaml', two unused parameters |  |
| engine3-13 | confirmed | low | engine/damage.py:49 | Parameters that are passed and never read: Blow.deep / resolve(deep=), nearest_zone(rng), spawn_fighters(player_lvl), discovery.names(data) |  |
| engine3-14 | confirmed | low | engine/events.py:20 | Unused imports: 'import yaml' in eleven engine files, JudgeVerdict in events.py |  |
| engine3-12 | confirmed | low | engine/events.py:454 | Names nothing uses: _scope_regions (and the scope_places key), assert_ok, ALLOW_TABLES, OFF_HAND_WEAPON_TAG, LEAVING, an 'if False' branch |  |
| engine4-9 | confirmed | low | engine/failures.py:15 | import yaml is unused in 17 modules of this bin (all load through core.yamlio) |  |
| engine4-8 | confirmed | low | engine/inventory.py:62 | Functions with no caller in the game: good_named, fits, martial.is_technique, and two no-op lines in lessons | yes |
| dead-switches-10 | confirmed | low | engine/loot.py:74 | combat.yaml conditional_rolls has been false since the first commit: the FITS table and its branch never run, and every rolled property is halved |  |
| engine5-7 | confirmed | low | engine/mentor.py:63 | The mentor's rank check is unreachable: rank_table, check_ranks and the `ranks` branch of check_speech have no caller, with chat_request, state and BUILDS |  |
| dead-code-7 | confirmed | low | engine/mentor.py:68 | (b, e) The check on Maren's rank numbers is never run: nothing passes `ranks`, and rank_table() has no caller |  |
| dead-code-19 | confirmed | low | engine/mentor.py:462 | (f) Seven old forms kept beside the one the game now uses |  |
| engine5-9 | confirmed | low | engine/pulse.py:19 | `import yaml` is unused in 17 of the 28 files; every load goes through core.yamlio |  |
| llm-rest-13 | confirmed | low | engine/pulse.py:716 | pulse_motive is a task nothing asks in play: the motive step has been the engine's since f360 and the model path sits behind a switch |  |
| dead-switches-8 | confirmed | low | engine/pulse.py:720 | motives.yaml engine: true since f360: the model's motive step (pulse_motive) is reachable only from one test |  |
| dead-code-6 | confirmed | low | engine/pulse_prompts.py:160 | (b, f) The old whole-event judge prompt and its request builder stay beside the parts judge | yes |
| engine5-8 | confirmed | low | engine/pulse_prompts.py:160 | Unreferenced functions, a whole unused prompt and parameters nothing reads across pulse, pulse_prompts, orenna, mounts, presence and needs | yes |
| dead-code-14 | confirmed | low | engine/quirks.py:203 | (c) Fourteen helpers that only their own tests call |  |
| engine6-10 | confirmed | low | engine/relevance.py:85 | Dead functions, parameters and imports in this bin | yes |
| dead-code-9 | confirmed | low | engine/retrieval.py:73 | (b) Twenty functions, two enums and one validator factory that nothing calls | yes |
| engine7-9 | confirmed | low | engine/spellcraft.py:12 | `import yaml` is unused in 20 of the 29 files (all load through core.yamlio); `import random` unused in spellcraft; a second `import re` inside a function |  |
| engine7-8 | confirmed | low | engine/spellcraft.py:106 | Names in this bin that nothing in the tracked files calls | yes |
| dead-code-20 | confirmed | low | llm/backend.py:97 | (f) legacy_failure and LEGACY_ERRORS serve a recording shape that load() already refuses |  |
| llm-checks-18 | confirmed | low | llm/contracts.py:1225 | StartingKit tests the weapon twice; the second test adds nothing |  |
| dead-code-5 | confirmed | low | llm/contracts.py:1372 | (b, f) The retired stat-passives creation step is still carried: contract, two prompts, request builder, stub answer, two constants |  |
| llm1-9 | confirmed | low | llm/contracts.py:1372 | StatPassive, StatPassiveSet and as_lists are reached by nothing |  |
| llm2-9 | confirmed | low | llm/gateway.py:30 | Small dead pieces across the model layer | yes |
| llm2-7 | confirmed | low | llm/prompts.py:141 | Three creation prompts nothing sends: PASSIVES_SYSTEM, STAT_PASSIVES_SYSTEM, stat_passives_user |  |
| dead-families-3 | confirmed | low | llm/prompts.py:320 | RE-RATE llm2-7: a duplicate of dead-code-5 (as are llm1-9 and shell1-14), and its fix as written stops the game at import: both prompts are still reached by name at llm/prompts.py:320 |  |
| dead-switches-20 | confirmed | low | runbal.sh:2 | runbal.sh and runfull*.sh change to a folder from another machine and are tracked against .gitignore | yes |
| dead-code-16 | confirmed | low | runfull.sh:1 | (d) Six root files are tracked although .gitignore excludes them: four run scripts with a Linux sandbox path and two old reports | yes |
| scenes1-19 | confirmed | low | scenes/combat_scene.py:709 | Dead code in these files: scene methods only tests call, unused imports and locals, a branch that cannot run, an unread data key |  |
| scenes2-13 | confirmed | low | scenes/intercepts.py:53 | Dead code in this area: an uncalled function, an unused constant, two unused parameters, repeated imports, overridden temperatures |  |
| scenes3-11 | confirmed | low | scenes/passive_hooks.py:6 | Unused imports, an unused constant, and temperature arguments that the sampling table overrides |  |
| world_py-9 | confirmed | low | scenes/world.py:3044 | weight_hint is write-only since f375: set in about 20 places, used by nothing | yes |
| world_py-10 | confirmed | low | scenes/world.py:3103 | exits_due is never set True: show_exits() without asked=True does nothing, at 11 call sites |  |
| world_py-11 | confirmed | low | scenes/world.py:4155 | npc_context has no caller; five imports are unused; one branch value is unreachable; reload_after_rollback is called only by tools | yes |
| shell1-14 | confirmed | low | simlib.py:497 | The stub's stat-passive answer, its four tables and every class's stats row answer a request nothing makes |  |
| shell1-16 | confirmed | low | simlib.py:868 | simlib.remembered still carries the path for saves from before typed memories, which no save it opens can take |  |
| dead-switches-13 | confirmed | low | storage/campaign.py:298 | The import of saves from before the database (9 to 21 October) marks them current before copying them in, so no migration step runs on them | yes |
| trace-turn-7 | confirmed | low | storage/campaign.py:606 | commit_operation's first_of_line save decides nothing: save_player already saves the meta on every commit | yes |
| dead-code-13 | confirmed | low | storage/campaign.py:875 | (c) forget_memory is called only by its test, so the `forgotten` flag is never set in play |  |
| shell2-11 | confirmed | low | storage/campaign.py:970 | Store methods nothing in the game calls: reindex_npcs, forget_memory (and the forgotten flag), list_npcs, export_json, npc_memories' min_importance | yes |
| trace-save-6 | confirmed | low | storage/campaign.py:970 | CampaignStore.reindex_npcs has no caller; forget_memory is called only by one test, so the forgotten column every memory query filters on is never set by the game |  |
| tools2-12 | confirmed | low | tools/lora_eval.py:75 | kit_breaks looks for a kit line the game stopped writing at f375: the sentence-length check never fires on a real prompt |  |
| tools2-13 | confirmed | low | tools/night_measure.py:60 | night_measure.Run.slot is never called |  |
| tools3-11 | confirmed | low | tools/rerun.py:34 | Names nothing reaches in these tools |  |
| unneeded-files-19 | confirmed | low | tools/run_suite.py:42 | A second copy of the repository sits under .claude/worktrees (105 MB) on a branch merged days ago; f717 taught the suite to step around it instead of removing it | yes |
| dead-code-15 | confirmed | low | tools/runstats.py:1 | (d) tools/runstats.py is named by no document, skill, hook, workflow, bat file, test or other tool |  |
| dead-code-4 | confirmed | low | tools/scratch/camp_probe.py:1 | (a, d) tools/scratch holds two probes that no longer run, by their own README | yes |
| tools3-10 | confirmed | low | tools/scratch/camp_probe.py:17 | tools/scratch holds two probes that no longer run | yes |
| suite-speed-12 | confirmed | low | tools/sim/runall.sh:2 | Five helper scripts in tools/sim cannot run any more |  |
| dead-switches-19 | confirmed | low | tools/sim/simreport.py:10 | tools/sim/simreport.py is an older copy of the root simreport.py that nothing runs |  |
| tests-health-14 | confirmed | low | tools/sim/tune_party.py:2 | Six files in tools/sim and four shell scripts at the root are scratch from the first commit that cannot run here, and root smoke_test.py is named like a test but never run | yes |
| unneeded-files-8 | confirmed | low | tools/sim/tune_party.py:2 | Scripts that cannot run or are stale copies: a second simreport.py, a tuner that reads /tmp/tune4.py, two probes their own README calls broken, a duplicated test | yes |
| shell2-12 | confirmed | low | ui/console.py:20 | Small dead pieces in the shell: an unused table, two unused imports, a saved stdout never read, a host that can never match | yes |
| dead-code-11 | confirmed | low | ui/gui/web/app.js:1530 | (b) The page handles a `fatal` event that nothing sends |  |
| dead-code-18 | plausible | low | core/models.py:123 | (e) The ability field buff_stat is copied through five modules and read by none |  |
| dead-switches-11 | plausible | low | data/rules/needs.yaml:9 | Hunger and fatigue have been switched off 'for now' since 12 October: a module and its hooks in six files run only in one test |  |
| dead-switches-9 | plausible | low | llm/runtime.py:1160 | The load screen has been on since f527; the 'dormant' start before the page and its fallbacks are kept for a tree without launch.yaml |  |
| dead-switches-17 | refuted | low | data/rules/reply.yaml:8 | decide_then_speak is off as shipped and awaits the owner: 386 lines and three call sites run only in tests and measuring runs | yes |
| dead-switches-12 | refuted | low | data/rules/sampling.yaml:29 | A1's sampling arms were measured and none kept, but the arms, DND_SAMPLING_ARM and their plumbing are still in | yes |
| unneeded-files-3 | refuted | low | docs/measure/prose_a1/README.md:1 | docs/measure is 37.3 MB of the 58.5 MB tracked tree (230 of 1,349 files) and no tool or test reads any of it | yes |
| unneeded-files-13 | refuted | low | docs/research/shared_world_time/report.md:1 | docs/research: six sets of raw reading notes (414 KB) kept beside the report they were written for, after the decision they fed was taken | yes |
| trace-threads-9 | refuted | low | llm/runtime.py:1160 | start_for_game, stop_for_game and _GAME (the 'dormant' start before the home page) cannot run while data/rules/launch.yaml is in the tree |  |

## Tests, data and the rest (108)

| id | checked | weight | place | finding | known |
|---|---|---|---|---|---|
| suite-speed-7 | confirmed | medium | .claude/hooks/known.py:28 | The push marker trusts any summary: a run of one test, of none, or of an earlier commit marks HEAD as passed |  |
| unneeded-files-2 | confirmed | medium | .claude/hooks/quick_suite.sh:9 | The stop hook adds a git worktree for each commit and never removes one: 46 in the temp folder, 1.4 GB; an emptied one turns the quick run into the whole suite |  |
| frontend-shipping-7 | confirmed | medium | .github/workflows/suite.yml:27 | Nothing builds or starts the packaged game, in CI or in the hooks; CI sees only pull requests and main, on Python 3.12, without requirements.txt |  |
| typed-patterns-7 | confirmed | medium | data/replay/interp_cases.yaml:1 | The corpus pins repairs that never fire in play and has no case for ones that fire most; nothing measures a repair on typed lines | yes |
| leftovers-4 | confirmed | medium | data/replay/scripts/stub_party.py:119 | The party golden keeps none of the claims its script plants: both lack a first-person word, so owned() drops them every time, and the recording pins no kept claim, no promise and no canon check | yes |
| unneeded-files-5 | confirmed | medium | docs/design/21_play_faults_plan.md:7 | Records that tracked files cite are not in git: docs/play (cited on 69 lines), docs/design/26 and five dated measure reports |  |
| data-2 | confirmed | medium | engine/needs.py:13 | Rules read with a silent default: 22 code defaults differ from the data's value, 3 keys are set nowhere, and 43 of 129 data files have no startup check beyond parsing | yes |
| typed-patterns-8 | confirmed | medium | scenes/world.py:2434 | The pattern faults of both rounds are one seam: every handler is handed the whole typed line beside its step, and 131 places read it again for a fact the step carries | yes |
| world_py-5 | confirmed | medium | scenes/world.py:4176 | Every guild contractor in all 13 guild halls is told they know the Greywood from their own jobs |  |
| shell1-5 | confirmed | medium | simbot.py:1741 | No test runs the bot's loop, so the harness has drifted from the engine five times with the suite green | yes |
| tests-health-4 | confirmed | medium | simlib.py:594 | The suite writes its stubbed model calls into the game's own logs/llm_calls.jsonl (and the turn, pulse and crash logs): simlib.install redirects none of them |  |
| trace-replay-2 | confirmed | medium | tools/acceptance.py:110 | Nothing in the suite plays one session straight and again with the game closed and opened part-way and compares them; this audit found the same kind of loss eight times by hand | yes |
| unneeded-files-1 | confirmed | medium | tools/rerun.py:359 | Every replay leaves a rerun_logs_ folder in the temp folder: 11,736 of them, 2.1 GiB, in nine days |  |
| suite-speed-4 | confirmed | medium | tools/run_suite.py:34 | A quick run does not see a change to a .json, .jsonl, .db, .gz, .html or .css file, to anything under data/runtime, or to the web page's script |  |
| pane-commands-6 | confirmed | medium | tools/sim/combat_allocate_test.py:37 | No test and no golden sends a command that changes the character through play() during a fight and then plays on, so the lost refresh and the stale fighter pass the suite |  |
| tests-health-5 | confirmed | medium | tools/sim/follow_test.py:12 | Four window tests skip their page checks and print a pass wherever node with playwright is missing, which is the owner's machine and CI: follow_test runs none of its 10 checks |  |
| tests-health-3 | confirmed | medium | tools/sim/party_test.py:60 | party_test has no check, no assert and no exit code: it cannot fail, and it has been writing a real error to a temp file nobody reads |  |
| suite-speed-3 | confirmed | medium | tools/suite_ran/sitecustomize.py:44 | A quick run never picks the fence tests that read the code as text: a change in engine/combat.py picks 10 tests and not the acting-character fence |  |
| data-5 | confirmed | medium | world/loader.py:229 | About 60 roster creatures can be met by no road in play, and 172 of 549 fit no place's wild roster; nothing at startup says so |  |
| aged-save-10 | confirmed | low | data/measured/prompt_ceilings.yaml:26 | mentor_chat's prompt ceiling (11,500) is under every mentor_chat request play builds: 38 of 38 in three plays, 12,555 to 16,106 characters with the stub's short text | yes |
| unmeasured-tasks-12 | confirmed | low | data/rules/budget.yaml:96 | No recording has ever held 19 of these 23 tasks: creation and Maren's lesson are outside every measured run, and their budget sizes are first guesses (the one recorded creation task writes half its guess) |  |
| data-3 | confirmed | low | data/rules/equipment.yaml:85 | Fourteen rules keys nothing reads, each promising a rule the engine does not apply (heavy armour's stamina recovery, a caught pickpocket's reputation loss, the sleep threshold) | yes |
| dead-families-2 | confirmed | low | data/rules/failures.yaml:36 | 18 of the 23 stood lists (108 lines) can never be shown, and three ledger kinds have no adder; the startup check demands six lines for each |  |
| task-failures-8 | confirmed | low | data/rules/failures.yaml:345 | Stand-in lines that read wrong where they are shown: a sentence opening on a lower-case creature name, 'Here they come' when the player struck first, 'The last one goes down' when they yielded, the goddess with no speaker | yes |
| leftovers-9 | confirmed | low | data/rules/failures.yaml:370 | When the traits cannot be written, one of the goddess's three lines asks for 'the three you were born with, once more': the traits, which the player has not been shown, while the page asks again for three abilities | yes |
| leftovers-8 | confirmed | low | data/world/mentor.yaml:132 | Maren tells a new caster 'you can't get mana back in the middle of this', but a mana tonic is sold in town and drunk in a fight, and siphon gear gives mana back on every hit | yes |
| data-4 | confirmed | low | engine/behaviors.py:15 | Tuning numbers typed into engine and scenes code beside the data file made for them (the worst twenty) | yes |
| aged-save-8 | confirmed | low | engine/obligations.py:141 | The registry's trim takes offers and obligations only: every captive's row and every released stock row stays (194 of 233 rows at 6,000 lines) |  |
| aged-save-7 | confirmed | low | engine/pulse.py:924 | The rows of people who are gone are never removed, nor a road stop's place row: half the people rows of an aged save belong to nobody left in the world | yes |
| unneeded-files-4 | confirmed | low | engine/recording.py:133 | The kept recordings' call logs are 31.3 MB of history (419 versions) because they are stored gzipped, which git cannot delta, with a timestamp in each |  |
| situations-12 | confirmed | low | engine/situation_parts.py:1239 | A part's beliefs list has no cap, and its only reader is a hash | yes |
| dead-switches-3 | confirmed | low | llm/audit.py:45 | The audit log is on as shipped and its folder has no cap: one file a session, never removed |  |
| aged-save-9 | confirmed | low | scenes/standing_actions.py:32 | Four more of the player's stores gain a key for every road stop and never lose it: standing_told, standing, last_in and the field's towns (the same kind as world_py-8) |  |
| silent-excepts-9 | confirmed | low | tools/event_eval.py:148 | Measuring tools report a zero or an empty result they did not measure (12 handlers in 6 tools); this guard hid a bug until f519 and is still there |  |
| tests-health-2 | confirmed | low | tools/sim/danger_500_test.py:79 | 15 checks in 14 tests end in `or True` and can never fail; 5 of them hide a claim that is false today |  |
| leftovers-7 | confirmed | low | tools/sim/fake_runtime.py:141 | The fake llama-server takes any command line: a flag the pinned build does not know stops the real server at once and passes every launch test |  |
| task-failures-9 | confirmed | low | tools/sim/stand_in_518_test.py:1 | No test fails each task in turn through a played session: doing so over the three kept scripts found a paid waiting act, hires left without details and fight rounds with no figures |  |
| stale-copies-6 | plausible | medium | storage/campaign.py:744 | Closing the class: the stale-save check over every record kind, read by every test, finds the rest; one live record per operation removes them and the hand-made repairs | yes |
| min-card-4 | plausible | low | data/measured/card_profile.yaml:13 | The minimum card's reading rate is not corroborated: the tool's own scaling rule gives 271 to 588 tokens a second from the 44 tracked runs against the 756.8 the budget prices every prompt at | yes |
| frontend-shipping-13 |  | low | .claude/hooks/known.py:42 | The push mark cannot tell a full suite run from a partial one, or this commit's run from an older one |  |
| suite-speed-11 |  | low | .claude/hooks/quick_suite.sh:10 | The Stop hook leaves one full checkout per commit in the temp folder: 47 registered worktrees, 1.4 GB |  |
| unneeded-files-15 |  | low | .claude/hooks/session_start.sh:6 | The session-start hook greps every .py under the project folder, untracked copies included, to print the highest feature number |  |
| unneeded-files-14 |  | low | .claude/workflows/meravia-bundle.js:54 | The bundle workflow sends its agents to data/rules/card_profile.yaml, which does not exist | yes |
| unneeded-files-20 |  | low | .gitignore:1 | The local .git is 123 MB, 85.5 MiB of it in 5,122 loose objects that have never been packed |  |
| people-15 |  | low | character/kit.py:45 | Tuning numbers and content written in code, one biome id among them | yes |
| dead-switches-6 |  | low | config.py:14 | DND_NUM_CTX / config.NUM_CTX no longer sets the model's context; its comment still says it does |  |
| dead-switches-4 |  | low | config.py:25 | The shipped sampling is set in two places: sampling.yaml and two defaults in config.py that are outside the data hash and the recording |  |
| dead-switches-16 |  | low | config.py:70 | Numbers the game plays by sit in config.py, outside data/, the data hash and the startup check | yes |
| shell1-11 |  | low | config.py:70 | Nine similarity thresholds the engine decides by live in config.py: outside data/, the start-up check and the data hash | yes |
| data-12 |  | low | data/replay/scripts/stub_party.py:205 | stub_party's closing census checks the lines the script itself typed; both golden scripts set up outside their try/finally |  |
| dead-switches-14 |  | low | data/rules/arcs.yaml:101 | Three on/off switches and a dozen tunables in data/rules are read by no code |  |
| data-11 |  | low | data/world/mentor.yaml:369 | The mentor's lines spell out numbers that data holds elsewhere: the joining fee and the wolf count |  |
| data-10 |  | low | data/world/roles.yaml:22 | Every good's price is written in goods.yaml and again in each seller's row of roles.yaml (29 rows); nothing checks they agree |  |
| unneeded-files-12 |  | low | docs/design/14_phase2_plan.md:3 | Design docs that say 'nothing built' for work that is built, and docs overtaken by a later one or finished (about 265 KB of the folder's 733 KB) |  |
| unneeded-files-10 |  | low | docs/design/README.md:1 | docs/design/README.md is the advisor's delivery note of 9 November, not an index: it lists 13 of the folder's 32 other files and gives setup steps long since done |  |
| unneeded-files-11 |  | low | docs/design/ROADMAP.md:21 | ROADMAP.md does not say where the work stands: phases 2 and 3 are built, two questions it lists as waiting were answered on 11 November, and the plans since are not in it |  |
| engine1-7 |  | low | engine/bosses.py:9 | Tuning numbers and card text live in code; bosses.py says 'All numbers are in data/rules/bosses.yaml' and they are not |  |
| engine2-9 |  | low | engine/combat.py:428 | Combat rules address the first player fighter (combat.player, 34 uses in this area) and the court reads ws.player (7 uses), not the acting character | yes |
| data-9 |  | low | engine/combat.py:771 | The health coefficients are held three times: pools.yaml for characters and twice as literals in combat.py for creatures |  |
| engine2-8 |  | low | engine/combat.py:2733 | Tuning numbers live in code across this area, and two module headers say they do not | yes |
| engine3-9 |  | low | engine/events.py:122 | The world's spawns list has no cap: defeated and expired rows are never dropped | yes |
| engine4-10 |  | low | engine/lessons.py:189 | Tuning numbers and word lists written in code instead of data/ | yes |
| engine5-10 |  | low | engine/orenna.py:86 | Tuning numbers and player-facing lines written in code rather than data/ |  |
| engine5-5 |  | low | engine/pulselog.py:18 | logs/pulse.jsonl is the one log with no cap: every pulse event is appended and nothing trims it |  |
| engine6-8 |  | low | engine/quirks.py:52 | curses.pick in quirks.yaml is never read (the code gives four curses, not three); other content and numbers of this bin sit in code |  |
| engine7-5 |  | low | engine/spellcraft.py:638 | Three acid effects cap corrosion at a literal 75 while Corrode reads the cap from data; Shield of Faith's half-health cap is a literal beside Barkskin's data cap | yes |
| engine7-10 |  | low | engine/stakes.py:172 | stakes reads ws.player where the acting character is meant, mixed with ws.acting in the same function | yes |
| engine7-6 |  | low | engine/voice_rules.py:87 | Tuning numbers written in code in this bin: trust bands, opener rounds, healing thresholds, status lengths, a marks cap and a news window | yes |
| dead-switches-15 |  | low | llm/audit.py:37 | audit_log.yaml's enabled switch is shadowed by config.AUDIT_LOG and never decides anything |  |
| trace-threads-6 |  | low | llm/audit.py:45 | logs/audit gains one file per session of up to 200 MB and nothing ever removes old ones |  |
| llm1-4 |  | low | llm/audit.py:47 | logs/audit gains a file every session and nothing ever removes one |  |
| llm-checks-17 |  | low | llm/contracts.py:796 | Two length limits are enforced by a send-back, on the mentor's speech and on a town moment's line | yes |
| llm1-10 |  | low | llm/contracts.py:1022 | Word lists and limits tuned from play are written in the contracts, not in data/ |  |
| trace-threads-4 |  | low | llm/gateway.py:240 | The call log's seconds include the worker's hold: the 132.29 s populate_place call was 120.00 s waiting to be let in, 1.43 s queued on the server and 10.85 s of model time | yes |
| llm2-8 |  | low | llm/runtime.py:234 | cache_idle_slots is sent on while the RAM cache is off, and the server turns it off at every start |  |
| frontend-shipping-12 |  | low | requirements.txt:3 | No requirement has an upper bound, play.bat fails outright when the optional window library cannot install, and each release is built with whatever versions are newest that day |  |
| scenes1-17 |  | low | scenes/camp_actions.py:503 | Tuning numbers and player-facing wording written in code in this area | yes |
| dead-code-12 |  | low | scenes/combat_scene.py:475 | (c) Three fight-scene methods are called only by tests; the game takes another path |  |
| scenes1-18 |  | low | scenes/dungeon_actions.py:48 | These files act on self.player, not the acting character | yes |
| scenes2-8 |  | low | scenes/field_actions.py:276 | Stores without a cap in the character's record: the per-day marks of field abilities, and item_history | yes |
| scenes2-9 |  | low | scenes/guild_actions.py:626 | Three writers move the asker's trust for one hand-in, one of them a number in code |  |
| scenes2-14 |  | low | scenes/inventory_actions.py:131 | Memories written past engine/memory.keep with the subject left at its default 'player' |  |
| scenes2-12 |  | low | scenes/mentor_actions.py:399 | Player-facing lines and tuning numbers written in code, not in data/ | yes |
| scenes3-12 |  | low | scenes/shop_actions.py:201 | Tuning numbers and player-facing lines written in scene code instead of data/ |  |
| world_py-8 |  | low | scenes/world.py:810 | player.visited gains a never-pruned id for every road stop entered (an uncapped store) |  |
| world_py-12 |  | low | scenes/world.py:2123 | Numbers and tables that decide game state are written in the scene instead of data/ |  |
| world_py-13 |  | low | scenes/world.py:3053 | _news_seen only grows for the whole sitting and is deep-copied at every operation (an uncapped store) |  |
| people-9 |  | low | services/fight.py:482 | Binding, taming and items act on self.player though the round has already resolved the acting fighter | yes |
| people-6 |  | low | services/fight.py:857 | A place's carcass list has no cap or window where it is written |  |
| dead-switches-18 |  | low | simbot.py:25 | Twelve of the bot's sixteen SIM_ environment switches are set nowhere and written down nowhere; the suite does not shield tests from them |  |
| shell1-10 |  | low | simlib.py:594 | Stubbed test runs write into the developer's own play logs |  |
| tests-health-9 |  | low | simlib.py:601 | The suite runs with the arrival split switched off: the path every player takes on entering a place (first four residents, the rest in the background) is run by 2 tests and no recording | yes |
| shell2-8 |  | low | storage/campaign.py:179 | Tuning numbers and lines the player reads sit in the storage code | yes |
| shell2-7 |  | low | storage/campaign.py:512 | The store loads and saves the first character whatever PlayerState it is handed | yes |
| data-13 |  | low | storage/statehash.py:198 | Files only tools read sit inside the game's data hash: lora.yaml, cards.yaml and two tables of towns.yaml |  |
| tools2-11 |  | low | tools/purity.py:17 | The pure-module fence lists three modules that were never written and skips a missing file without a word |  |
| tools2-9 |  | low | tools/purity.py:205 | The spatial and health write-path fences see only plain assignments: a list changed in place, /=, *=, /= and setattr pass, and one such write is in the tree |  |
| trace-save-7 |  | low | tools/rerun.py:359 | Each replay leaves a rerun_logs_* folder in the system temp directory for ever, and a replay that fails while opening its save leaves the replay source, the no-server guard and saves/rerun_<name>_<pid> behind |  |
| suite-speed-10 |  | low | tools/run_suite.py:254 | In a fresh checkout the first quick run picks by words and the second runs every test; a baseline folder that is not there runs everything without a word | yes |
| tests-health-6 |  | low | tools/sim/ability_traits_test.py:107 | 16 checks pass a constant: each names a behaviour the test never looks at |  |
| tests-health-13 |  | low | tools/sim/act_595_test.py:29 | Tests leave things behind and write outside saves/ and temp: at least 123 save folders, sim_out/ at the root, logs/audit_test, a file under data/measured, 12 temp folders |  |
| tests-health-11 |  | low | tools/sim/bus_454_test.py:106 | Tests pinned to exact text: 343 compared phrases are word for word in engine string constants, 81 in data lines, and 188 comparisons search source files as text | yes |
| tests-health-7 |  | low | tools/sim/flat_gear_test.py:16 | Checks under an `if` with no else run only when a fixture happens to be there: 9 such blocks (15 checks) did not run today, 4 of them behind a hasattr on a name that moved |  |
| tests-health-10 |  | low | tools/sim/mentor_voice_test.py:9 | About 1,800 lines of tests hold code the game never runs: two mentor switches nothing sets, thinking (off by decision) and the feats of the body (called by nothing, by decision) | yes |
| unneeded-files-18 |  | low | tools/sim/prose_steady_577_test.py:53 | Seven tests make a temp folder each run and never remove it (about 1,900 folders so far) |  |
| tests-health-8 |  | low | tools/sim/stamina_test.py:19 | 13 tests set no exit code: a failure shows only because the runner scans their output for a FAIL line |  |
| tests-health-12 |  | low | tools/sim/talk_deed_653_test.py:1 | A sixth of the suite's code is copied between files: the check helper is defined 510 times, and several groups of tests differ only by a list | yes |
| min-card-5 | refuted | low | engine/budget.py:36 | The second minimum card has no profile: a Vulkan machine is priced at the 3060's rates, and by the game's own cards table the RX 7600 XT writes a fifth slower | yes |
