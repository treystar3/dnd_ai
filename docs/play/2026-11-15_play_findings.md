# Play findings and their causes, 2026-11-15

Two sessions with the live model (Gemma 4 12B on llama-server, RTX 4070 Ti SUPER), played by hand through the window's page, on the
working tree of `foundations/phase3-switch` (f639 uncommitted).

- **Run 1:** 33 lines as Marda Quillfoot, level 1 throughout. Played by the session that knows the code.
- **Run 2:** 524 lines as Dagna Kettlewright, level 1 to 20 in about 3 h 44 min. Played by a reader who had never seen the game and read
  nothing in the repo. Its journal, with every line typed and the game's words, is `2026-11-15_blind_play_journal.md` beside this file.

## How the causes were found, and how far to trust them

Seven read-only readers each traced one class of fault in the code. The main claims were then read again in the code by the session, and
one was shown by a probe. Each cause below carries one of these marks:

- **[checked]** read in the code a second time by the session.
- **[shown]** reproduced by a small script.
- **[reader]** found by a reader with file and line, not read a second time.
- **[inferred]** follows from the code, but depends on what the model answered on that turn.
- **[not found]** no cause found.

The game's `logs/` folder is refused to this session, so nothing here comes from the record of what the model answered. Every
**[inferred]** would be settled by the turn log of that line.

Nothing was changed in the code. This file names causes and the class each belongs to; it proposes no patch for a single sentence.

## The few mechanisms behind most of it

1. **A passage is never checked against what the turn did.** `Narration` is bare text (`llm/contracts.py:1175`); the only checks are for
   machinery words, staleness and invented speech. Nothing compares the story with who is present, who is alive, what was found, who drank,
   what was delivered or what the clock says. Sections 2 and 9.
2. **Word lists read over the whole typed line.** Orders in a fight, leaving a dungeon, praying, finishing a yielded foe, talking to a
   hire, and naming a ware are each decided by a pattern that matches anywhere in the line, so an ability's own name, a companion named as
   an object, or a common word such as "out" fires them. Sections 1 and 4.
3. **A fight rebuilt from its saved row loses who the mentor is.** The tutorial's troll fight breaks on this. Section 1, case 1.7.
4. **The "part of it did not take" line is built from the wrong list.** It reads the steps that finished, not the operations that
   committed, so it says a paid contract did not happen. Section 3.
5. **The danger label measures one thing: whether the player survives a simulated fight.** Companions dying, health lost and the foe's
   level do not enter it. Section 5.
6. **Foe levels never look at the player's level.** A road draws its foes from a neighbouring wild's band; a dungeon's floors climb from
   the place's band; XP for a higher foe is capped at double. Together these make both the level 35 ghost and the fast second half.
   Section 5.
7. **The engine acts with no line to the player.** A foe out of reach, a failed search, a flight chance, a foe that yielded, a purchase's
   count: each is told only to the narrator, who may or may not say it. Sections 4 and 6.
8. **Handlers that ignore part of what was asked.** Using an item ignores its target; buying ignores the count; "until eight" becomes one
   of eight periods; a line is cut to three deeds though the owner's decision is fifteen. Sections 1, 2, 6 and 7.

---

## 1. A line that names a companion becomes an order

How an order is recognised in a fight **[checked]**: `CombatScene.order_of` (`scenes/combat_scene.py:473`) is a pattern with no model
call. The line is an order if it holds a living ally's first name anywhere (or "everyone", "party", "you two", "team") and any word from
`ORDER_WORDS` (`:444-451`). `order_kind` (`:456`) takes the earliest match. `give_orders` (`:504`) always prints "to guard you": an
order cannot name who is to be guarded (`engine/combat.py:2868` stores only the kind, and a foe for an attack). `turn()` (`:534-540`)
then runs only what `own_part` (`:544`) keeps, and `own_part` drops every clause that holds the name of an ally who was told.

| # | Typed | Game | Cause |
|---|---|---|---|
| 1.1 | `I put everything into a Twin Hammer Strike to kill the owlbear before it turns on Kennard again.` | "You tell Kennard to attack the owlbear." | "Kennard" is in the line; "Strike" in the ability's name matches the attack pattern (`:449`). The whole line is one clause with his name in it, so `own_part` drops the player's strike. **[checked]** |
| 1.2 | `I step in front of Raerei and smash the ogre with Guard Breaker.` | "You tell Raerei to guard you." | "Raerei" is in the line; "Guard" in the ability's name **Guard Breaker** matches the guard pattern (`:448`). One clause, her name in it, dropped. **[checked]** |
| 1.3 | `"Kennard, guard Raerei!" Twin Hammer Strike on the giant boar.` | "You tell Raerei and Kennard to guard you." | Both are named, so both are told; who is guarded cannot be said. The strike itself survives here (`own_part` keeps a clause with a move's name and no ally's name). **[checked]** |
| 1.4 | `"Almund, get back out of its reach! Kennard, cover him!" ...` | "You tell Almund and Kennard to guard you." | "cover" is a guard word and comes before any other match. **[checked]** |
| 1.5 | `I stand my ground behind Kennard's shield and wait for the centaur to come to us.` | "You tell Kennard to guard you." | His name as an object, and "shield" is a guard word. **[checked]** |
| 1.6 | `"Raerei, see to your own wounds and stay behind me from here on." We go on to the next chamber.` (out of a fight, in a dungeon) | "Your party will hold back and come running if the alarm goes up." The move was dropped. | Out of a fight the interpreter model chose the party action; `party_hold` (`scenes/party_actions.py:806-812`) sets the whole party's mode and has no way to name one member. Why the move was dropped is **[not found]**. **[reader, inferred]** |
| 1.7 | Tutorial: `"Maren, attack the troll!"`, three wordings | "You tell Maren to attack the troll." then "Still waiting on you." each time | See below. **[shown]** |
| 1.8 | `I drink the healing draught, then use Twin Hammer Strike on wolf 1.` | Only the drink | The fight's interpreter returns one intent of one kind (`CombatIntent`, `scenes/combat_scene.py:441`); the free-item path (`:530`) needs an ally named. Nothing notices the strike was lost. **[reader, inferred]** |
| 1.9 | `"Maren, I'm nearly done for, take the other one!" I use Guard Breaker on wolf 2.` | Guard Breaker on wolf 3 | An order to attack with no foe named takes the fight's focus or the first foe (`:500`); the player's own target then came from the model or from `services/fight.py:344-345`, which replaces a target that is dead or gone with the closest foe. **[inferred]** |
| 1.10 | `We go to the Tilted Plough. I ask the innkeeper what a bed and a hot meal cost, and whether anyone here buys hides.` | "No one here buys hide." then "Three things at a time: not done - ..." | The interpreter returned more than three deeds; `ActionPlan.at_most_three` (`llm/contracts.py:646-658`) keeps the first three in the model's order and drops the rest (`scenes/world.py:2282` prints them). The owner's decision is a cap of 15 (GOALS.md:233, review Q31); the code still caps at 3. **[checked]** |

**1.7, the tutorial's order.** `mentor_strikes` (`engine/combat.py:2508`) and the "Still waiting" line (`scenes/mentor_actions.py:761`)
read `combat.mentor_ally.order`. The player's order is given to the Maren in `fight.fighters`. They start as one object
(`scenes/mentor_actions.py:842-843`). But `Combat.mentor_ally` is a field holding a whole fighter, so when the fight is rebuilt from its
saved row (`services/fight.py:315`, called from `give_back` at `scenes/world.py:1523` whenever an operation stands down or is rolled back)
it comes back as a second, separate fighter. A probe confirms it: after one round trip through the row the two are different objects,
and an order set on the one in the fight does not reach the one `mentor_strikes` reads. She then strikes only on the third stalled round
(`engine/combat.py:2514`), which is why the blind player's fourth wording seemed to work. The same split explains two more things seen
in that fight: the troll's scripted blow of 527 (`:2493`, dealt to `mentor_ally`) left her bar at 1317/1317, and the draught the tutor
asks for gave "+0 health". Class: any field of `Combat` that holds a fighter by value and is also in `fighters`. `reserves` and
`ally_reserves` hold fighters too, but those are not yet in the fight. Tests: `mentor_test.py` runs on the stub, where no operation
stands down, so the fight is never rebuilt mid-way.

**Class and where a fix lives.** An order should be recognised from who is addressed, not from a name anywhere in the line, and the
player's own ability names should never count as order words. An order needs a "whom" for guard. All of it is in `order_of`,
`order_kind` and `own_part`. Tests today: `orders_test.py` covers the patterns; nothing covers a line with a companion named as an
object, an ability whose name holds an order word, or the cap.

## 2. The story says what the engine did not do

| # | What happened | Cause |
|---|---|---|
| 2.1 | `I use a healing draught on Raerei.` and `...pour a healing draught between her lips.`: the story has her drink; the player's health rose. | `on_use` (`scenes/inventory_actions.py:237-254`) never reads the intent's target; `consume` heals the player. The narrator is told "The player uses healing draught..." with the typed line, which names Raerei, and writes her drinking. `give` goes another way (`on_give`, `:530`, `give_to_hire`, `:493-528`) and does heal the hire. **[checked]** Class: any item used "on" someone. |
| 2.2 | The dead priest collapses again one room later, and is at camp next morning. | Death removes her from the party (`services/party.py:135`). Outside a fight the narrator gets a THE FALLEN line (`engine/truth.py:477-505`); the fight's narrator gets only living allies (`scenes/combat_scene.py:697`) and recent narration (`:757-764`), with no list of the dead. Nothing compares the people a passage names with who is alive. **[reader, inferred]** |
| 2.3 | `promote Kennard` in a monster den at night is told with a guild representative, a counter and a clerk. | `party_promote` (`scenes/party_actions.py:763-784`) checks no place and no clerk, and its event says "at the guild" (`:783`). Hiring does check the place (`scenes/guild_actions.py:227`). **[reader]** |
| 2.4 | Town gossip about the player told by "labourers" at a den's mouth. | `_narrate_now` (`scenes/world.py:2846-2851`) leaves the town text out at a dangerous place but still passes the news lines, under the header "WHAT PEOPLE HERE ARE TALKING ABOUT" (`scenes/world_prompts.py:190`). **[reader, inferred]** |
| 2.5 | A clerk at his desk in the story while the Board pane says "The clerk must be here". A watchman and a woman at the wood's edge who cannot be spoken to; a companion answers. | The pane asks `clerk_here()` (`scenes/guild_actions.py:69`); the narrator had "(no one)" in PEOPLE HERE and wrote one anyway. Speaking to someone unknown falls back to the last one spoken with (`scenes/world.py:3402-3408`). Narrated places are made real (`scenes/part_actions.py:215`); narrated people are not, and are not refused either. **[reader, inferred]** |
| 2.6 | One fanatic "hits the earth like a felled log", then yields, then is both bound and dead. He and she in one reply. | `yields()` (`services/fight.py:786-802`) picks its prisoner **among the dead** after the round's passage has already told the killing blow, and sets them to 1 health. Its own comment says this was done so that story and captive agree; the round's passage is written before it. **[checked]** |
| 2.7 | A centaur yielded; `Twin Hammer Strike on the centaur.` got "While you turn to other things, the centaur slips away." | `yield_intercept` (`scenes/arc_actions.py:54-77`) is two patterns. `YIELD_KILL` (`:35`) has "finish", "kill", "strike it down", not a plain attack or an ability's name. Anything matching neither clears the held foe. **[checked]** |
| 2.8 | Two bandits who yielded vanished from the enemy list with no line. | `_break` (`engine/behaviors.py:66-71`) marks them and writes only for the narrator and the log. **[reader, inferred]** |
| 2.9 | The priestess refuses the receipt, the game prints "delivered", she then says it was delivered earlier. Same with the watch captain. | Steps run in the order the interpreter wrote them (`scenes/world.py:2154-2158`): talk, then give. `drop_narrated_talk` (`:2474`) keeps a quoted talk first. She answers before the receipt reaches her; `on_give` then records the delivery (`scenes/guild_actions.py:492-497`) and asks her to speak again. **[reader, inferred]** |
| 2.10 | From the guild house, `We walk to the watch tower and I hand the sealed guild dispatch to the watch captain.`: a whole delivery and payment is told; nothing happened. | The move left the player in place and the give was refused or fell to someone else; the narrator still held the whole typed line. The check that a passage contradicts nothing runs only for turns where nothing happened at all (`scenes/world.py:2865`). **[reader, inferred]** |
| 2.11 | A centaur and a ghost speak and wait for an answer, then "cannot be reasoned with". Backing away is told while the fight goes on. | The fight has already begun on the encounter roll (`scenes/world.py:459-488`). The narrator is told "It holds its ground and warns the player off - they could still back away" (`scenes/combat_scene.py:253-255`), which no engine state stands behind. "Cannot be reasoned with" is `parley.why_not` (`engine/parley.py:17-23`): a centaur's category is not in `talk.categories` (`data/rules/combat.yaml:325-326`). **[reader]** |
| 2.12 | The mage calls the player "Sparrow" all session, and when asked says "You named yourself". | A quirk: `data/rules/quirks.yaml:44` `nickname`, with "Sparrow" in its list, drawn per hire (`engine/quirks.py:47-48`). Working as written; the speaker is given no reason for the name, so it invents one. **[checked]** |
| 2.13 | Parth mourns Maren Holt, who left alive. | `moved_on` (`engine/mentor.py:517`) writes her leaving to the journal with no `dead` flag. `_lost_lately` (`engine/towns.py:64-79`) then decides by a loose match of how she left against `death_reads_as`. **[checked]** that the flag is missing; that the match hit is **[inferred]**. Class: any journal writer of `npc_gone` that leaves the flag out. `mourning_seasons_430_test.py` covers the other writer only. |
| 2.14 | Dungeon rooms with canopy, rain, creek beds and wind. | A dungeon's place takes the biome of the place above (`engine/dungeons.py:109`); `family_of` asks biome before type (`engine/battlefield_builder.py:34`), so fights get forest ground though an `underground` family exists. The narrator's time label always adds the weather (`scenes/world.py:215-218`). The owner's decision that bad weather applies only under open sky (review Q14) is honoured by the engine but not by that label. **[reader]** |
| 2.15 | A cache already in the pack, then "the pouch proves empty... no longbow here". "Two silver coins" against "Found: 26 copper". A pack "holding wolfhide and bearfur" against "Harvested: nothing usable." | The cache goes straight to the purse and pack (`scenes/dungeon_actions.py:149-155`); a later "take the pouch" finds nothing lying there and is told so. The other two are the model ignoring the event it was given; the harvest event's `got` can be the words "nothing usable" (`scenes/work_actions.py:172-177`). **[reader, inferred]** |
| 2.16 | `go down` to floor 4: the room just left is described; the owlbear is only in the pane. Bites "barely touching" for a critical 18; a wolf told dead at 15 health. | The opening event names the foe but nothing requires the passage to. Damage figures are placed by tag (`scenes/combat_scene.py:66-118`), so a figure can sit in a sentence that tells something else. How hard a blow reads against what it did is unchecked. **[reader, inferred]** |
| 2.17 | "The sun is low" at 10:43 AM; "pre-dawn chill" at 1 PM. | The first is fixed text shown whatever the clock says (`data/world/mentor.yaml:437`). The others are the model with only the arrival's period given (`scenes/road_actions.py:353`). **[reader]** |

**Class and where a fix lives.** One piece of infrastructure covers most of this section: a check of each passage against the turn's
ledger and the scene's roster (who is here, who is alive, what was given to whom, what was found), with a retry on a mismatch, the way
`contradicts_nothing` already works for empty turns. 2.1, 2.3, 2.6, 2.7, 2.13 and 2.14 are engine faults in their own right and need no
model in the fix.

## 3. Stand-in lines, some of them false

Where they live **[reader]**: `data/rules/failures.yaml`, read by `engine/failures.py`.

- `turn_not_taken` ("That never quite began...", "Not yet: nothing happened..."): the line's first operation was rolled back
  (`scenes/world.py:1095-1096`).
- `stood_any` ("Done, and kept...", "That stands as done...", "The thing is settled..."): the deed stood but its passage did not
  (`scenes/world.py:1297-1349`). `round_stood` is the same for a fight round (`scenes/combat_scene.py:748`).
- `part_stood` ("You got as far as this: ... The rest of the line did not take"): a later step failed (`scenes/world.py:1097-1098`).

| # | Fault | Cause |
|---|---|---|
| 3.1 | After a paid contract and a level: "The rest of the line did not take; say it again." Three times, each a "go to the hall and report" line. | The list it prints is `self.line_done`, filled only when a step finishes (`scenes/world.py:2271`). The walk and the hand-in are not steps: `prepare_talk` (`:1436-1467`) commits them as their own operations before the talk. When the clerk's reply then fails, the talk rolls back, the line reports "part", and the paid hand-in is not in the list. **[checked]** for the code path; that the reply failed is **[inferred]**. |
| 3.2 | Why the clerk's reply, a fight round or a climb up a rise failed to be written at all. | The gateway tries three times, stops early if the same refusal repeats, then raises (`llm/gateway.py:300-368`); the passage goes straight to the stand-in with no further try. Which check refused is in the audit log. **[reader]; cause [not found]** |
| 3.3 | `I give Raerei one of my healing draughts.` twice: "nothing has happened". | `on_give` removes the item, then asks for a spoken reply; if that fails the whole operation rolls back. The fault is logged (`scenes/world.py:1241-1249`); the player is shown nothing of why. **[reader]** |
| 3.4 | "Not from here. Get to a proper place first." then a successful find. | `on_explore` refuses on a road or in a dungeon (`scenes/explore_actions.py:60`); the plan held an explore step and a search step. **[reader]** |
| 3.5 | `We go on to the next chamber.` got "That still didn't come through - try it in different words." | `scenes/audit_actions.py:178, 200`: the clarifying question is asked once, any error is swallowed to a debug line (`:192`), and the pending flag is set even when the question came back empty (`:202`). Why that plain line stopped being read is **[not found]**. **[reader]** |
| 3.6 | "The tinker's losses is lost, for all that was done." and two more like it, at the end of travel. | These are situations of the world ending unresolved: `events.lose` (`engine/events.py:646-659`) prints `data/rules/doors.yaml:68`, `"{title} is lost, for all that was done."`. It runs after every pulse (`scenes/world.py:679`), and travel moves the clock. The template does not agree with a plural title, and the player has never been told the situation existed. **[reader]** |

**Class and where a fix lives.** What a line reports as done should be read from the operations that committed and their ledger rows,
never from a list of finished steps. Stand-ins shown to the player are marked on the turn log (`turnlog.py:127`) but, by
`engine/failures.py`'s own note, are not counted as failed turns; no test checks the "did not take" wording against what was committed.

## 4. Ordinary words read as another act

| # | Typed | Game | Cause |
|---|---|---|---|
| 4.1 | `...we step around the rigged stones, and go on to the next chamber.` | Left the dungeon, then came back in. 27 minutes. | `OUT_OF_DUNGEON` (`scenes/plan_repairs.py:79`) is `out|surface|climb|back up|leave|exit|...` and is searched over the whole line (`:299`): "point **out** the wires". Any move in a delve then becomes leaving. **[checked]** |
| 4.2 | `I kneel and jam the pressure plates...` | Also a prayer. 25 minutes. | `PRAYING` (`:89`) holds `kneel`; any "other" deed whose line matches becomes a prayer (`:247-248`). **[checked]** |
| 4.3 | `I search the thicker southern reaches of the forest for silverleaf...` | Four hours of travel into a level 35 ghost. | The exit patterns do not match this line, so the interpreter model most likely returned a move toward a neighbouring place: every neighbour is always on its list (`engine/candidates.py:70`), and the only gate, `far_unnamed`, asks nothing for a walk of 180 minutes or less or along a road (`scenes/world.py:3267-3290`). **[reader, inferred]** |
| 4.4 | An attack on a foe out of reach becomes a walk with no word why. `I close with the boar...` walked though it was "on you". | When `attack_access` fails, the action is spent on an approach and the reason goes only to the narrator (`engine/combat.py:1814-1818`). For a slow fighter (heavy armour, `data/rules/combat.yaml:157`) a step "advance" takes the whole round even when already engaged (`services/fight.py:568-573`); the prompt tells the model to set that step for "charge in and strike". The bear's "pivot away" is **[not found]**. **[reader]** |
| 4.5 | `We find the entrance to the Crooked Warren...`: three hours, nothing, no word of failure. `We take the stairs down...` told an arrival and did not move. | An unknown place in a dangerous zone becomes exploring (`scenes/world.py:3235-3238`), 2 to 4 hours, base chance 0.12, and a failure is only described (`scenes/explore_actions.py:70-74`). "the stairs" is in `WITHIN` (`scenes/plan_repairs.py:74-75`), which makes the move a look; only the `delve` kind descends. **[reader, part inferred]** |
| 4.6 | `I pocket the coins and we go on to the next chamber.`: the move dropped. | Picking up coins is refused (`scenes/inventory_actions.py:325-327`), and a refused pick-up halts the rest of the line because its kind is "needed by the rest" by default (`engine/actions.py:75`, `scenes/world.py:1784-1787`). **[reader]** |
| 4.7 | `Raerei is still white as a sheet. We sit under the pines for two hours...` taken as talk. | `hire_wants_talk` (`scenes/party_actions.py:505-514`) takes any line that names a hire and has none of a short list of act words. **[reader]** |
| 4.8 | `I buy a room for the night.` printed the price list. | `ware_asked` (`scenes/shop_actions.py:40-50`) matches the ware's id, the whole request inside the ware's name, or the request's **last** word: "night". **[checked]** |
| 4.9 | `I pay the 52 copper for a room and we sleep until morning.` paid and did not sleep. | The buy kind lists "sleep" among its own verbs (`engine/actions.py:63`), so the audit that looks for a verb no step covers is satisfied by the buy alone. **[reader, inferred]** |
| 4.10 | `"Both at once."` in answer to the game's own question: "There's no one here to give that to." | The answer is read again joined to the first line (`scenes/world.py:2217-2225`); the give had no target, and `named_here` matches only the whole role "guild clerk", never "the clerk" (`:2516`). **[reader, part inferred]** |
| 4.11 | Flight blocked twice, then worked, with no reason. In run 1 it was refused outright and `#menu` said to finish or flee. | Flight is one roll (`engine/combat.py:2462-2477`): base 35, minus 20 when engaged, plus 10 or 40 by distance (`data/rules/combat.yaml:174-179`). The chance is never shown. A tutorial fight refuses flight (`scenes/combat_scene.py:582`). **[reader]** |

**Class and where a fix lives.** A repair that rewrites a deed should key on that deed's own summary or destination, not on the whole
typed line. Every repair is pinned by `interp_eval_test.py` through `data/replay/interp_cases.yaml`, which keeps a repair working on
the case that made it and says nothing about the lines it wrongly catches. GOALS.md:41 and :43 are the governing lines: an impossible
act is refused and never granted then forgotten; a line the game fails to act on is a bug that is logged and counted.

## 5. Danger, levels and XP

| # | Fault | Rule and cause |
|---|---|---|
| 5.1 | A level 35 ghost labelled "even" at level 7; level 20 to 23 monsters "trivial" while companions were level 9 or 10 and one died in round two. | `combat.danger` (`engine/combat.py:3065-3080`) simulates the fight 80 times with an automatic player and counts a win whenever the fight ends in victory: 97% trivial, 80% favorable, 55% even. Companions lost, health lost and how hard one blow lands do not count. A sturdy player with a healer survives fights that kill everyone around them. **[checked]** Covered by `danger_500_test.py`, which tests the estimate, not what the label means to a party. |
| 5.2 | The ghost was there at all. | A road's hostile event picks a wild place bordering either end (`scenes/road_actions.py:292-309`) and rolls a creature inside **that place's** danger band (`engine/encounters.py:73-97`). Greyhollow borders the Hollow Barrows, band 15 to 35; a ghost is level 26 to 40. The player's level is not asked; the one gate (`deterred`) is for bandits only. GOALS.md:214 says a far outmatched beast should attack far less. **[checked]** for the pick; band numbers **[reader]**. |
| 5.3 | 1,181 XP for a two-line fight; 3,098 for three bandits; levels 10 to 20 in 70 minutes. | `kill_xp` (`engine/leveling.py:75-81`, `data/rules/combat.yaml:283-291`): 25 x level^1.25 x rank, times up to 2 for a higher foe. XP to the next level is 100 x level^1.35. A foe six levels up is therefore worth about half a level, and dungeons supply them one after another. GOALS.md:215 leaves this for the balance pass. **[checked]** |
| 5.4 | Level 20 bandits with 90 health, a level 12 tree with 294. | Health is by level, constitution and size, times a pack factor of 0.45 for creatures that come in groups (`engine/combat.py:792-839`). Pack creatures are weak one by one by design, but their XP takes only the average of the pack's health and damage factors (`services/fight.py:811-816`), and a yielded one pays too (`:817`). **[reader]** |
| 5.5 | Floors marked "E" with levels 10, 15, 20, 22. | Floor levels climb from the place's band (`engine/dungeons.py:45-51`); the letter is only the guild's band for that level (`engine/quests.py:23`), and E covers 10 to 24. Working as written; the letter tells a level 13 player nothing about a level 22 floor. **[checked]** |
| 5.6 | The first fight took one character to 15 of 103 health; in run 1 the player sat at 1 health for twelve rounds and could not flee. | Three wolves at the player's level, fearless and never yielding (`scenes/mentor_actions.py:723-743`). A tutorial fight leaves any killing blow at 1 health with no limit (`engine/damage.py:302-309`) and refuses flight. Maren is not in this fight by design. So a character who misses often cannot lose, cannot leave and cannot be helped. **[reader]** |
| 5.7 | Ability costs rose without notice. | A cost is a share of a reference pool that grows with level (`engine/combat.py:1726-1755`, `engine/pools.py:72`). Working as written; nothing tells the player. The 16 seen during the trial is **[not found]**. **[reader]** |
| 5.8 | Companions' health fell on a level-up. | Hires use a calibration table whose health factor falls with level faster than raw health grows (`data/rules/combat.yaml:248`). A fault in the data. **[reader, inferred]** |
| 5.9 | A yielded centaur gave XP but no tally; a boar in the dungeon did not count; two gather contracts both "ready" on the same leaves. | `record_kills` (`scenes/guild_actions.py:472-488`) counts the dead only, and only where the quest's place is the player's place; a dungeon is another place. `quests.held` counts the pack live and reserves nothing. **[reader]** |
| 5.10 | Crafted plate listed at 25 times its iron; shops pay 30%; "lv 11" usable at level 5. | Value is by base, rarity, level and material (`engine/items.py:357`); inputs do not enter it. `sell_rate` is 0.3 (`data/rules/inventory.yaml:6`) and no pane says so. **[reader]** |
| 5.11 | Four bears, one hide. Ten armour with no visible effect. | One roll per carcass at about 0.6 (`scenes/work_actions.py:125-179`): three failures running is about a 6% chance, so this may be luck. Armour should cut about 40% at these levels (`engine/combat.py:1137`); why it did not is **[not found]** and may be a fault. **[reader]** |

## 6. Buying, joining, rooms

| # | Fault | Cause |
|---|---|---|
| 6.1 | "four iron bars" and "2 iron bars" each bought one. | `buy_ware` (`scenes/shop_actions.py:82-114`) buys one, always; the intent's count is not read. No line states what was bought. **[checked]** |
| 6.2 | Asking the chandler what he sells bought a bandage at "25% off". | The model read the line as haggling; `on_haggle` (`scenes/pastime_actions.py:81-106`) prints the cut and then buys. Nothing checks that the line asked to buy. **[reader, inferred]** |
| 6.3 | Run 1: three silver paid to the clerk in words, still "Not a guild member", Join took three more. | Coin given to the clerk becomes joining only through `join_guild_rewrite` (`scenes/world.py:2395-2407`), which needs a guild word in the line, or the tutorial's "sign" stage. Otherwise it is a plain gift of coin (`on_give`, `scenes/inventory_actions.py:530`), and the coin is gone. Run 2 paid at the desk with Maren, which is the stage that works. **[checked]** for the rewrite. |
| 6.4 | Sleep needed a bought room in Greyhollow and was free in Eldervale. | Without a room, `on_wait` prints "You rested here" (`scenes/world.py:4127`) with no full recovery; it does not refuse. **[reader]** |

## 7. The clock

- **"Sleep until eight" gave 6:00, then noon.** The wait's hour is one of eight named periods (`llm/contracts.py:474`,
  `engine/clock.py:16`), so "eight" becomes dawn or morning and "two in the afternoon" becomes 13:00. **[reader]**
- **"Half an hour" walks of 2 to 7 minutes; long talks that take no time.** Each kind of deed has a fixed cost
  (`engine/clock.py:10-14`, `engine/actions.py:160`); travel is the map's minutes. What a speaker says about distance is the model's.
  **[reader]**
- **A typed line stamped 8:59 while the header read 9:19.** The page stamps the echo with the time from before the turn
  (`ui/gui/web/app.js:164`). **[reader, inferred]**
- **Run 1: a failed theft moved the clock from 9:27 AM to 1:21 PM.** `data/rules/law.yaml:55` allows 15 minutes. **[not found]**

## 8. Panes, creation and machinery on the page

| # | Fault | Cause |
|---|---|---|
| 8.1 | `create:who {...}` and `create:stats {...}` in the story; "Character saved to saves\character.json"; "[ Locksmith Baker \| rogue \| focus: balanced ]". | The page echoes every input except those with a prefix in `HIDDEN` (`ui/gui/bridge.py:27`), and "create:" is not in it. The other two are `scenes/goddess.py:584` and `ui/console.py:302`. **[checked]** for the echo. `goes_on_525_test.py` exempts "Character saved". |
| 8.2 | Three attack cards word for word the same. | `assign_martial` (`engine/ability_slots.py:489`) picks each slot on its own; names are checked for duplicates (`llm/contracts.py:34`), mechanics are not. Passives do dedupe by mechanic (`character/creation.py:249`). **[reader]** |
| 8.3 | Asked for thrown knives, started with a dagger. The goddess says part of the calling "does not exist" and not which part. | `choose_weapon` (`character/kit.py:129-134`) filters to melee weapons when any ability is channelled. `scenes/goddess.py:465` passes what was adapted and does not ask her to name it. **[reader, inferred]** |
| 8.4 | `#places` and `#quests` after a fight leave the pane on "Last fight". | The fight pane's mode is reset only for clicked views (`ui/gui/web/app.js:928`), not typed ones. **[reader]** |
| 8.5 | A strip of notices pushes the tab row or the Shop list down under the pointer. | `#ticker` sits above the tabs in the page's flow (`ui/gui/web/index.html:12`); the panes' buttons are hidden commands, so the strip is never cleared between clicks. **[reader]** |
| 8.6 | "lv 1 · · 6 spell damage", "lv 6 · · lv 6". | The level is written by the shop (`scenes/shop_actions.py:248`), again by the page (`app.js:708`) and again by `items.summary` (`engine/items.py:426`). **[reader]** |
| 8.7 | The Continue card read "played today at 07:10" at about 09:50. | `touch()` (`storage/saves.py:62-67`) stamps when the game was **opened**, not when it was last played or saved. **[reader]** |
| 8.8 | The wolves' arrival told twice. | `mentor_actions.py:731` prints the fixed text, then the fight opens without `told=`; the troll's opening passes it (`:856`). **[reader]** |
| 8.9 | "(1 more rounds)"; "Theft" and "failure" joined by the dash character; "Type #board"; the tutor saying "press its button in the Items list"; "The fallen can be skinned" after a tree; "raw yew" from a pine; "the captured bandit isn't here" while standing there. | `engine/combat.py:1784`; `engine/checks.py:111`; `scenes/guild_actions.py:344` and `data/world/mentor.yaml:289`; `mentor.yaml:126-136`; `scenes/arc_actions.py:97` with harvest by category (`scenes/work_actions.py:159`); `scenes/world.py:3423-3427`. **[reader]** |
| 8.10 | The Board tab showed the Character sheet. "torchs". The chandler's goods never in the Shop pane. The card list jumping to the top. | **[not found]** (the first is thought to be a race between the heading and a pinned refresh, `app.js:1514-1515`, not proven). |

## 9. Run 1's findings against these causes

| Run 1 fault | Where it is above |
|---|---|
| Joining fee charged twice | 6.3 |
| Fight story and numbers disagree (a neck wound told with no attack in the log; knives at "the wolf that's almost dead" hit the one at full health) | 2.16, 1.9 |
| The first fight is a trap | 5.6 |
| The wolves' arrival told twice | 8.8 |
| Clock jump on a failed theft; "half an hour" in 7 minutes | 7 |
| Machinery on the page | 8.1, 8.9 |
| Creation mismatch and duplicate abilities | 8.2, 8.3 |
| The draught swallowing the dagger line | 1.8 |
| The notice strip shifting the tabs | 8.5 |
| Prose slips: wrong pronouns, "deer in headlights", a wall and dirt floor in a forest, "the final wolf collapses" with one left | Mechanism 1: unchecked passages. Not traced one by one. |
| A lead about a pony asked five times to three people and never answered | **Not traced.** |
| Maren rejecting a straight answer twice ("dodging my questions") | **Not traced.** |
| Maren's after-fight speech printed twice | **Not traced.** |
| The guild storeroom walked into unchallenged, then turned back | **Not traced.** |

## 10. What worked, so it is not lost in a fix

Dungeons (frame lines, traps that can be seen and acted on, a boss with a stage and a legendary), crafting at the forge, the rank
trial, companions with their own stories and a death that carried forward in their talk, people keeping hours, a contract payable at
another town's hall, the Stats, Places, Party and Gear panes, and short plain attack lines, which never once went wrong.
