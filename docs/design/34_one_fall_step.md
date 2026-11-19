# 34. One fall step: the design note for FIGHT_CORE-1

The note the audit fix plan asks for before FIGHT_CORE-1 is built (docs/design/33_audit_fix_plan/fight_core.md, "A short design
note is agreed before building"). **Approved: the owner took the recommended answer on every question on 2026-11-19 ("Yes,
recommended answers", GOALS.md's top decision row); FIGHT_CORE-1 is built as f768, its departures from this note named in its
commit.** Pillars 1 (prose and game state agree)
and 6 (fun, deep, fair play); infrastructure. Written 19 November 2026, read against play/faults at f745. FIGHT_CORE-5, FIGHT_CORE-6
and FIGHT_ABILITIES-1 had not landed when it was read; this note assumes FIGHT_CORE-5 is in first, as the plan orders.

Six features wait on this one and carry questions that belong with it: FIGHT_CORE-2, -3 and -4, and FIGHT_ABILITIES-2, -4 and -5.
Their questions are asked here, once, at the end.

## What is wrong today

A death is handled in four places, each doing part of it:

- The tail of `_apply_damage` (engine/combat.py:1599-1618) tells the fall, records who struck it, and pays the kill. It does this
  only for the blow's own target.
- The blow path's stages (data/rules/stages.yaml `blow`: on_fall, release, morale, avenger, boss_after_damage) unmake a summon,
  untie the fallen, roll the rout, wake Avenger and tell the boss's fall. Only the blow path has them.
- `combat_perks.on_dot_death`, from `start_turn`'s branch for foes (engine/combat.py:2648), tells "succumbs", rolls the rout on its
  own die and pays the player. Only foes, and only at their own turn start.
- The rebound stage (engine/damage.py:421) and Death's Door (engine/spellcraft.py:486) write health themselves and tell a line, or
  not.

So how a death plays out depends on what killed. A player meets it as:

- **A death nobody mentions.** A Storm Chosen arc, a Conduit leap, thorns or a guard's share kills someone who was not the blow's
  target: the narrator is handed the damage but never the death, and is told not to add kills. The kill perks do not fire and the
  marks that wait for death (Reap, Pyre, Contagion) stay on the body. A companion or the player dead of poison at the start of a
  turn falls with no line at all, and `felled_by` is empty, so the hire's line cannot say who did it.
- **A death that sets nothing off.** A pack leader killed by a torn wound routs nobody (0 of 219 against 138 of 279 by a blow), the
  player stays tied to the corpse, and a bow then takes the point-blank step of -15 on every later shot. A Bound summon dead of
  poison is not marked fallen, so it can be cast again in the same fight. Retribution and Death's Door kill without release or rout.
- **A death told twice.** A foe killed earlier in the foes' phase still reaches its turn: a second fall line ("succumbs to what was
  done to it"), a second rout roll, and the kill paid to the player (Rampage heals, Grave Chorus gains an echo) for a kill that was
  not theirs (69 of 200 rounds). A foe dead of a curse at its own turn start rolls the rout twice (60 of 60). A pack-bond blow
  nested in the player's blow tells and pays its kill twice.

The findings are engine2-2, trace-fight-4 and trace-fight-5 (docs/design/32_code_audit).

## The fall step

One function, `fall`, in engine/damage.py, run at the moment a stage that writes health takes a fighter from standing to zero.
Each of the three health stages (`health`, `tick_health`, `tear_health`) notes the health just before it writes; the `fall` stage
after it compares. A fighter already at zero when the path began does not fall again, and a fighter raised and killed again falls
again, with no mark to clear. Nothing is queued and no field is added to the fight's row.

### Where it runs

| Path | Today, after the health is written | With the fall step |
|---|---|---|
| A blow (take_damage, `blow`) | health, on_fall, after_damage, healing_after_damage, release, morale, avenger, yields_break, boss_after_damage, second_wind, rebound; the fall told and paid in `_apply_damage`'s tail, for its own target only | health, **fall**, after_damage, healing_after_damage, yields_break, boss_after_damage (the bloodied turn only), second_wind, rebound |
| A poison's or a burn's tick (`dot_tick`) | tick_floor, tick_health, tick_on_tick, tick_duel_end; then, for a foe only, `on_dot_death` from `start_turn` | tick_floor, tick_health, **fall**, tick_on_tick, tick_duel_end |
| A torn wound (`tear`) | tick_floor, tear_health; nothing at the death itself | tick_floor, tear_health, **fall** |
| A rebound (the `rebound` stage) | the striker's health written, "collapses, undone by its own violence" told, nothing else | the stage calls `fall` for the striker |
| Death's Door (spellcraft.py:486) | health written to zero (or one in a duel or the first hunt), its own line, nothing else | the write stays (until FIGHT_ABILITIES-4 puts it on a path of its own), then `fall` |
| `start_turn` on a fighter already down | a foe gets `on_dot_death`: a second line, a second rout, the player paid | returns False at once and touches nothing |
| A summon dispersed or unmade (summons.disperse, combat_perks.unmaking) | writes zero on purpose | not a fall; both stay on tools/purity.py's list of health writes, named so |

`after_damage` and `healing_after_damage` move behind the fall: for a fighter who is down they do nothing but note `hurt_ally` on
the striker, and they draw no die, so no effect changes place. The names on_fall, release, morale and avenger leave engine/damage.py
STAGES and stages.yaml together (engine/data_check.py holds the two to each other both ways). `boss_after_damage` stays, for the
bloodied turn; the boss's fall moves into `fall` (bosses.after_damage splits into the bloodied turn and the fall).
engine/data_check.py `tables_problems` gains one rule: a path that names a health stage names `fall` straight after it, so a fourth
path (FIGHT_ABILITIES-4's kill outright) cannot forget it. tools/sim/tables_504_test.py's literals change with the lists, on purpose.

### What `fall` does, in order

| | Step | Today, on the blow path | Die |
|---|---|---|---|
| 1 | A summon is unmade (summons.on_fall: the volatile kind bursts; a Bound summon is marked fallen) | on_fall, first | the path's (below) |
| 2 | Every tie released (battlefield.release) | release | none |
| 3 | The fall told by its cause, in the story and the log; `felled_by` set from the one who caused it | the tail, much later, for the blow's target only | none |
| 4 | The boss's fall ("BOSS FALLS" and its last words) | boss_after_damage, after the rout | none |
| 5 | The rout, for a foe (behaviors.morale_on_death) | morale | the path's |
| 6 | Avenger, for an ally | avenger | none |
| 7 | The kill credited, or left for the blow's tail (see "Who is credited") | the tail | none |

Steps 1, 2, 5 and 6 keep today's order, so on the blow path the die is drawn exactly where it is drawn today: a summon's burst first,
then the rout. Step 3 is new at this place; FIGHT_CORE-5 has already put the blow's own line at the blow's mark, which is why the
fall's line lands after it and before the rout it causes.

**Step 4 moves.** Today the boss's last words come after the guards have broken at its death (stub_fight, recorded call 37: "One of
Marrow Hask's guard breaks, seeing Marrow Hask fall", then "BOSS FALLS"). The beat draws no die, it is the death itself, and
FIGHT_ABILITIES-5 will hold the rout to the end of the action anyway, which puts the boss's words before it. Moving it now means
recorded call 37 moves once, not twice. This is a choice the plan did not make; it is listed for the owner below.

## Who is credited, and where it is paid

The credit is one function in engine/combat.py beside `_apply_damage`: the killer's `kill_round`, `combat_perks.on_kill` (Rampage,
Grave Chorus, Deathleap, Headsman, Shadowstep, Plaguebearer, frozen ground, Devourer), the Risen Thrall or else the marks that wait
for death (Reap, Pyre, Contagion), Soul Harvest and Triumph. Today's tail and `on_dot_death` both become calls of it.

**The blow in progress.** For the blow's own target the credit stays where it is paid today, at the tail of `_apply_damage`, so no
number of an ordinary kill moves. To know which deaths are "the blow's own target", `_apply_damage` opens a record of the blow at its
head (striker, target, whether its tail has run, whom a fall named) and closes it in a `finally`. It is held on the fight as a pydantic
private attribute: not dumped, so neither the saved row nor the fingerprint holds it. When `fall` runs for a fighter who is the target
of an open blow whose tail has not yet run (the innermost such blow), it notes the one who caused the death on that blow and pays
nothing; the tail pays them. Any other death is paid inside `fall`, at once, to the one who caused it.

This settles more than the plan's narrower wording ("the path hands its Blow back to the tail"), for three reasons found in the code:

- **Everything that kills the target inside its own blow is paid at the tail today**: the main hit, a gear element's damage (1498,
  1521), Stormcaller (1533), a torn wound (1459), Death's Door (on_hit at 1454), Thermal Shock and Dormant Venom (after_hit). If
  only the main hit were held for the tail, those kills would be paid earlier, before Vampiric and the weapon's leech heal the
  striker, and Rampage (which heals only below a share of health) would fire where it does not today.
- **A blow that misses can still see its target die.** The miss returns at 1375, before the tail: a riposte answers it, the
  player's thorns kill the riposting foe, and nobody is paid. The `finally` pays it on the way out.
- **The nested pack-bond blow** (1576) has its own record, innermost, so it pays its own kill and the outer tail pays nothing.

The same private attribute is the home FIGHT_CORE-3 needs for "the blow in progress" and FIGHT_ABILITIES-5 for the held breaks, so
this feature builds it first and they add to it. FIGHT_CORE-3's open point (a state held on the fight and kept out of its row has no
precedent) is closed by this feature's test.

| Death | Who caused it (felled_by and the kill) | Paid where |
|---|---|---|
| The blow's target, by any harm of its own blow (the hit, its riders, its torn wound, a Death's Door it carries, Stormcaller) | the striker | the tail, as today |
| Side harm from a blow: Storm Chosen, Conduit, Superconductor, a splash or arc, a summon's burst or pulse, Unmaking's victims, Consecration, Starfall, a relic's nova | the one whose harm it was (the source the path was handed) | inside `fall` (new) |
| Thorns | the one wearing them | inside `fall` (new) |
| A guard's share, Martyr, Shared Skin | the striker of the blow that was shared | inside `fall` (new) |
| A rebound (Retribution, Spellmirror) | the one wearing it | inside `fall` (new) |
| A curse, burning ground, a static field, ball lightning, frostbite, a seed, Caustic Drip, Bramble Wrap | whoever laid it (each already passes its maker as the source) | inside `fall`; today a foe's is paid to the player by `on_dot_death` (the owner's question 1) |
| A poison's or a burn's tick | whoever laid it, read from `status_from` | inside `fall`; today a foe's is paid to the player, an ally's or the player's to nobody (question 1) |
| Death's Door from a curse at the start of a turn | the curse's caster | inside `fall` |
| Healing that an Unraveled fighter turns on itself (restore, 1243) | whoever laid Unraveled, not the healer | inside `fall` |
| A cause nobody recorded (a ground whose maker is gone from the list, a status laid with no source) | nobody: the fall is told without a name | the marks still run; no kill is paid |

Two smaller rules: a cause who has died or left the fight since is named in `felled_by` but not paid (a dead wolf's poison is still
its poison, but a dead fighter has no Rampage to fire); and a turned foe's fall rolls no rout among the foes once FIGHT_ABILITIES-2's
side function exists (until then it rolls as today).

### Who caused it must reach the function

- **The tick** reads `status_from[dot]` before the status ticks down.
- **The torn wound**: `afflictions.tear` is handed the attacker, and passes it to the path as the death's cause only. The path's
  `source` stays None, so no stage on the tear path reads anything new.
- **A family's venom** (behaviors.after_hit, which calls add_status with no source today). The plan says "pass the source". That
  would move numbers: the affliction law sizes a poison stack from its source's offensive power when there is a source, and from the
  target's health when there is none (engine/afflictions.py:66-68), and the perks that change how an affliction lands read it too. So
  add_status gains `by`, who laid it, written on the status's row for the record and read by nothing that sizes or turns it. The
  same `by` gives FIGHT_CORE-8 the holder of a family's grapple.
- **Copied afflictions**: Plaguebearer and Contagion copy statuses with no source. They record their layer (Plaguebearer the player
  who has it; Contagion the dead's own poisoner), or a poison carried on would kill unnamed.
- **Unraveled**: `restore` hands take_damage the one who laid Unraveled as the death's cause, beside the healer as the harm's source
  (the source stays, so the rebound and `last_hurt_by` read what they read today).

### What the fall line says

The line follows the cause. Most deaths use a line that exists today:

| Death | Foe | Ally | Player |
|---|---|---|---|
| The target of a blow (the hit, its riders, its torn wound, its Death's Door) | "falls and does not rise" | "falls to the first wolf's blow and does not rise" | "you fall to the first wolf's blow, and the world goes dark" |
| Any other harm (side harm, thorns, a share, a curse, ground, a seed) | "falls and does not rise" | "falls and does not rise" (the line today's code already gives with no striker) | "you fall, and the world goes dark" (the same) |
| A rebound | "collapses, undone by its own violence" (today's) | the same | "you collapse, undone by your own violence" |
| A poison's or a burn's tick | "succumbs to what was done to it and falls" (today's) | **new** | **new** |

The line just before a side death already says what struck ("lightning leaps from the blow into the second wolf", "the curse gnaws at
Bryn for 12"), so the fall line need not name it again. For a death that is not a blow on the fallen, `fall` writes one counter on
the fallen fighter (`fell_to`: the kind), read by the hire's lines in services/fight.py. It is written only on a death that is not a
blow, which no recording holds, so no recorded turn moves by it.

## The dice

| Path | Today | With the fall step |
|---|---|---|
| A blow's target, and side harm on the blow path (thorns, a share, an arc, a burst, a curse, burning ground, frostbite, a seed) | the rout and a summon's burst on the blow's die, at on_fall and morale | the same die at the same place: no draw moves (GOALS.md:198) |
| A foe dead of a curse, ground, frostbite or a seed at its own turn start | the blow's die, then a second rout on the keyed die in `on_dot_death` | the blow's die only; the second roll is gone |
| A foe's tick | the rout on its keyed die, `streams.keyed("morale", id, serial, round)` | the same key, so the same rout; a summon's burst on it too |
| An ally's, a summon's or the player's tick | nothing rolled | the death's keyed die (no rout for an ally; a summon's burst) |
| A torn wound | nothing; the path has no die at all (`rng` is None at afflictions.py:110) | the death's keyed die, for the rout and a summon's burst |
| A rebound, Death's Door | nothing rolled (both have the blow's die at hand) | the death's keyed die, so nothing is added to the turn's stream |

The keyed die keeps today's key, "morale", so a foe's death by a tick routs exactly as it does now; renaming it would move every such
rout in the fixtures for nothing. The credit draws no die (on_kill, the thrall, the marks, Soul Harvest and Triumph read none), so
paying a kill at the tail or inside `fall` moves no die, only the order of two heals.

## What changes in the recordings, and why

- **stub_fight, recorded calls 37 and 43, in lines only.** In both a companion's killing blow sets off a rout. After FIGHT_CORE-5 the
  blow's line comes first; here "falls and does not rise" moves up from the end of the action to straight after it, ahead of the
  rout, and in call 37 "BOSS FALLS" moves ahead of the rout too. The story and the log are in the fight's row, so those two turns'
  fingerprints move with their lines. No die moves: the rout keeps its draws, and the kills are paid at the tail as today. The hire's
  death and the companions' falls recorded there ("takes a killing blow", "goes down hard") all came from blows, so their lines keep
  today's words.
- **stub_short**: three torn wounds on the player and no death; nothing here moves it (FIGHT_CORE-5 moves its tear lines).
- **stub_party**: no fight.
- No recording holds a death by a tick, a tear, a rebound, thorns or a share ("succumbs", "rebounds", "Thorns" and "throws itself in
  the way" appear in none of the three), and none holds a family's venom, so `by` and `fell_to` move nothing recorded.
- **The data hash moves** (stages.yaml). The rebless skill reads the difference; a changed roll is a fault of the build, never a
  reason to re-record.
- **The fight fixtures** (tools/sim/fixtures/fights) move only in cases that hold one of these, read from the compare's printout and
  named in the commit: a death by side harm, thorns, a share, a rebound or Death's Door (now released, routed and paid; a paid kill
  can add a draw later, as a Grave Chorus echo is one more cast); a foe dead of a curse, ground, frostbite or a seed at its turn start
  (the second rout is gone); a foe that reached its turn already dead (no second fall, the player not paid); a tick death of an ally,
  a summon or the player (released, a summon bursting); a torn wound that kills (now a rout); and, by the owner's answer to question
  1, a tick death laid by a companion.
- **The live gate** (tools/live_gate.py, needs the card) once, with FIGHT_CORE-5's run if they land together: the narrator's EVENTS
  gain the falls and change order. Passages sent back and stand-ins on fight lines must not rise against
  docs/measure/2026-11-17_live_gate.md. No prompt changes.

## Tests

tools/sim/fall_once_test.py, written first and seen to fail, starting from audit/work/skeptic_engine2_2.py, skeptic_engine2_2e.py,
engine2_checks4.py, trace_fight_check2.py, skeptic_tf_b.py and skeptic_tf_d.py. Every case asserts one fall line, placed after the
line of what killed and before any rout it caused; one rout roll; `battlefield.validate == []`; `felled_by` set; the credit on the
one who caused it, once.

- Failing today, the finder's case: a Storm Chosen arc kills a goblin that was not the target, and no line of the round tells it.
- The kind, on cases other than the one that found it: thorns and a guard's share; a pack leader dead of a torn wound (the pack
  routs, nobody is tied to it, a bow takes no point-blank step); Retribution and Death's Door (released, routed); a Bound summon dead
  of poison (marked fallen, refused if cast again); a bursting summon dead of a torn wound (it bursts, on the keyed die); an ally
  and the player dead of a tick (told, `felled_by` names the wolf that laid it); a foe dead of a curse at its turn start (one rout);
  a foe felled earlier in the phase reaching `start_turn` (no second line, the player not paid, Rampage silent); a pack-bond blow
  that kills (told and paid once).
- Added by this note: a missed blow whose riposte meets the player's thorns and dies (paid once, to the player); a kill by a gear
  element's damage with Vampiric and Rampage (the heals and the health after them as today); a family's venom killing a companion
  (the wolf named, the stack the same size as without `by`); a poison carried on by Plaguebearer (its layer named); a cause dead
  before the death it caused (named, not paid); a companion revived and killed again (two falls); a hire dead of poison and one
  down alive from it (neither line says "blow"); data_check refusing a path with a health stage and no `fall`; the blow's record
  absent from the fight's dump.
- What must not move: an ordinary killing blow with no affliction draws the same dice from the blow's die as before, counted by
  wrapping the die; and a foe's tick death routs the same foes as before.
- tools/sim/tables_504_test.py's literals change with the lists.

## The new lines a player reads

For the owner to read before they ship. Each is an event the narrator is handed and tells in its own words, or a line in the fight's
log; none is printed the same way over and over in the story. Names are examples.

**A companion dead of a tick** (the narrator's event):

- "The first wolf's poison does its work, and Bryn falls and does not rise."
- "The fire the first wolf left on Bryn burns on, and Bryn falls and does not rise."
- with nobody recorded: "The poison does its work, and Bryn falls and does not rise." / "The fire burns on, and Bryn falls and does
  not rise."

**The player dead of a tick:**

- "The first wolf's poison does its work. You fall, and the world goes dark."
- "The fire the first wolf left on you burns on. You fall, and the world goes dark."

**A death by a torn wound.** The plan asks for one. This note proposes none: the tear always comes from a blow on the fallen, its own
line already says so ("The blow tears Bryn's wound open again, 7 more blood lost"), and the blow's fall line follows it ("Bryn falls
to the first wolf's blow and does not rise"). If the owner wants one all the same: "The wound will not close again, and Bryn falls
and does not rise."

**The hire's lines** (services/fight.py:448 and 455), for a death or a fall that was not a blow on them; a blow keeps today's words:

- dead: "Bryn does not get up again: Bryn is dead (killed by the first wolf, not by you)."
- down, alive: "Bryn goes down and lies still: alive, but out of the fight, and she will have to be carried."

The plan named only the first; the second says "goes down hard under the first wolf's blow" today and is as wrong for a poison.

**The fight's log** (the pane): "Bryn succumbs" for a tick, as a foe's already reads; "Bryn falls" for every other death.

## For the owner

1. **Whose kill is a death by something laid earlier** (a poison, a burn, a curse, burning ground, frostbite, a seed)? GOALS.md
   holds no ruling.
   - (a) The one who laid it, with the whole credit, as a blow is (recommended). It credits by fighter, which multiplayer needs
     (GOALS.md checklist 8). In play: your own poison finishing a wolf is your kill as a blow is, so Rampage, Grave Chorus and
     Deathleap fire as today and Soul Harvest, Triumph and the Risen Thrall now fire too; Bryn's poison finishing it is Bryn's kill,
     so your kill perks no longer fire for it.
   - (b) Always the player, with the whole credit. Every foe's death by an affliction pays your kill perks, Bryn's included, and Soul
     Harvest, Triumph and the Risen Thrall fire for all of them. It reads "the first player" once more, which FIGHT_CORE-9 counts.
   - (c) Exactly as today: the player is paid, but only `kill_round` and on_kill, never Soul Harvest, Triumph or the Thrall.
   - A correction to the plan: it said (b) moves no number of today's play. That is true only of (c), and (c) keeps a second, smaller
     kind of credit beside the one function, which is the shape this feature removes. With one credit function, (a) and (b) both
     move numbers, in opposite directions.
2. **Which floors hold against a tick, and against a kill outright** (FIGHT_CORE-3, with FIGHT_ABILITIES-4's column).

   This note proposes one simplification first: everything a blow carries is the blow. A torn wound is only ever torn by a blow
   (afflictions.tear has one caller, the blow itself), a gear element's damage rides it, and Death's Door fires from it. So a floor
   that holds a blow holds the whole of it, wherever in it the killing harm comes, and FIGHT_CORE-3's "later torn wound" column is
   the blow's column. That leaves the tick as the one open column, and a kill outright.

   | Floor | Its own words (card, line or rule) | A blow and all it carries | A tick, today |
   |---|---|---|---|
   | The duel | "nobody can die" | holds | holds |
   | The first hunt | "the player cannot die" | holds | holds |
   | Lifeline | "a companion that would fall" | holds | does not |
   | Soul Tether | "a killing blow is survived once" | holds | does not |
   | A boss's last stand | "the first killing blow does not kill" | holds | does not |
   | Orenna's Last Breath | "a blow would kill you" | holds | does not |
   | Deathless | "will not fall" | holds | does not |
   | Deathward | "once per fight, a killing blow" | holds | does not |
   | A foe that yields | "never dies" | holds | does not |

   ("A blow and all it carries" is today's answer for the blow's main part only; the whole-blow rule of FIGHT_CORE-3 makes it true
   of the rest, which no option here changes.)

   - (a) By their words: Deathless, Lifeline and a yielding foe hold a tick; Deathward, Last Breath, a boss's last stand and Soul
     Tether do not (the plan's recommendation).
   - (b) Every floor holds every harm, a once-a-fight floor spent by a tick as by a blow (recommended here). Three reasons. A curse,
     burning ground, frostbite and a seed already meet every floor today, because they run on the blow's path; only the poison and
     the burn tick past them, so (b) is the one rule that is already true of half the turn's harm. A boss's last stand is a set
     piece of the fight (it clears the boss's statuses, the poison with them, and changes its phase), and under (a) a poison tick
     skips it and the boss simply dies. Orenna's Last Breath is a quest's gift, and a player holding it would not expect a burn to
     get past it.
   - (c) Only the duel and the first hunt, as today.
   - Under (a) or (b), each floor that newly holds a tick needs its line with the harm named in place of "the blow": "The poison
     should have ended Bryn, but the bond with its master will not let it fall (Lifeline)"; "The fire should have killed you, but a
     thin, tired warmth catches you, and you rise whole (Orenna's Last Breath, now spent)". The owner reads each before it ships.
   - **A kill outright** (Death's Door: "kills a target below 15% health outright"): (a) every floor holds it (recommended, and it
     follows from "everything a blow carries is the blow"); (b) none does, since the card says outright. Bosses never die this way
     by the card, as now.
3. **Summons in a trial of rank** (FIGHT_CORE-4). The wrong win is fixed either way: only a duellist decides the duel.
   - (a) Yes: summons made in the fight stand beside the summoner, and one that is beaten is unmade by the fall step and decides
     nothing (recommended). A summon is the summoner's own ability, as a fire bolt is a mage's; companions and hires are kept out
     because a rank is won by the one who holds it, and a summon is part of them. Without summons the stub summoner has one damaging
     ability.
   - (b) No, refused in the trial as draughts are, in a line the owner reads first. Draft: "This trial is yours to stand alone, and
     nothing you call will stand in it with you."
   - Under (a): does the Bound summon walk in with the summoner, as in any fight (recommended: the door and the cast then agree with
     no refusal at all, and FIGHT_ABILITIES-3 writes its bond back at the trial's end), or stay at the door as today, with its spell
     refused inside? Draft of that refusal: "Your bond waits outside the ring. This trial is yours alone."
   - A summoner's rate of passing the trial after the fix is run and reported with the feature, not tuned (GOALS.md:198).
4. **A turned foe** (FIGHT_ABILITIES-2).
   - (1) The last unturned foe is gone and a dominated undead still stands. (a) The will lifts at once ("the will on the skeleton
     lifts, and it remembers its own side", a line that exists) and the fight goes on (recommended: the card promises a turn for some
     rounds, and nothing is won without a blow). (b) It flees with its side broken, as a Dread Regent foe does, and the fight is won.
     If the player is to be told why Dominate did not turn a lone foe, a new line, draft: "There is no one of its own left for it to
     turn on, and the will slides off the dead thing."
   - (2) Is a turned foe an ally for your blessings and heals? (a) No, it is only spared (recommended). (b) Yes, while the turn lasts.
   - (3) May its old side strike it? (a) Yes: one rule says who may strike whom, for foes as for the player (recommended: a foe that
     turns on its pack is fought back, and nobody is held at the line by someone they cannot answer). (b) No, as today, and a turned
     foe then holds nobody at the line.
   - With the fall step: a turned foe's fall rolls no rout among the foes and wakes no Avenger, by FIGHT_ABILITIES-2's side function.
5. **Two smaller choices of this note.** The boss's last words are told with its fall, before the guards break (step 4 above).
   Recommended; say if they should stay after the rout as today. And the new lines above: do they read right?

## The order the seven are built in

| | Feature | Why here | Waits on |
|---|---|---|---|
| 1 | FIGHT_CORE-1, the fall step | the six below stand on it; after FIGHT_CORE-5, in one pull request with it so stub_fight is read once | question 1 |
| 2 | FIGHT_CORE-2, one turn a round | high (a foe that left still wounds the player); small once `start_turn` refuses the fallen | nothing |
| 3 | FIGHT_ABILITIES-5, the rout after the action | rolls its rout in the fall step; with or straight after FIGHT_ABILITIES-1's third door, so the fixtures are read once; one live gate run then serves FIGHT_CORE-5, -1 and this, if the owner lets the gate wait for it | FIGHT_ABILITIES-1 |
| 4 | FIGHT_CORE-4, the trial's duellists | high (a rank won without a blow), small once the fall step unmakes a beaten summon; FIGHT_ABILITIES-3's trial case follows its answer | question 3 |
| 5 | FIGHT_CORE-3, the floors | edits the same stage lists; the tick and tear paths must already end in the fall step | question 2 |
| 6 | FIGHT_ABILITIES-4, the kill outright | one stage, one path and one column once the floors are declared | question 2, FIGHT_CORE-3, FIGHT_ABILITIES-1 |
| 7 | FIGHT_ABILITIES-2, a turned foe's side | after FIGHT_CORE-2 and FIGHT_CORE-6, which rewrite the same lines of finish_round and own the one way out | question 4, FIGHT_ABILITIES-1 |

FIGHT_CORE-4 is put ahead of FIGHT_CORE-3, against the plan's order, because it is the higher fault, it is small once this lands,
and its question is the quickest to answer; FIGHT_CORE-3 and FIGHT_ABILITIES-4 then go together on the one floors table.

## What it does not do

- **Defeat** is still declared on the first player's fall. A fight that goes on while another human stands is multiplayer's
  (GOALS.md:171, 198).
- **The rout in the middle of an area cast** is still applied at the fall; FIGHT_ABILITIES-5 holds it to the end of the action.
- **A blow struck at a corpse** (a perk's repeat aimed at the fallen) still lands until FIGHT_ABILITIES-1; it no longer falls or pays
  twice.
- **No prompt, sampler setting or turn budget** changes.
