# pane-commands: the `#` commands as writers of game state

Everything below was run under simlib's stub (no model, no server), with scripts kept in
`C:/Users/tstil/AppData/Local/Temp/claude/dad68772ed0cbd02/d2ae1f65-36c6-4be3-9744-2919d03b2cce/scratchpad/audit/work/pane_commands/`.
Each script opened a save named `audit_pane-commands_*` and removed it in a `finally` block.

## 1. Each command that changes the character, sent in the middle of a fight

Fixture: a level 6 warrior (copper longsword, damage 7; copper chain shirt, armour 5) against a wolf with 5000 hp; a level 8 mage with
6 unspent points for the attribute rows; a summoner for the companion row. "Fresh" is `combat.fighter_from_character(character, id)`
built at that moment. Every line went through `WorldScene.play()`, the path the window uses.

| Command (who sends it) | In a fight | What it writes | Does the fighter follow | Is the fight's row saved | Operation | Seen |
|---|---|---|---|---|---|---|
| `#gearequip <uid>` (Gear pane, Equip) | taken | worn gear, pack; `save_player` | no | no | `command:gearequip` | greatsword in hand: fighter weapon 7.0, fresh 20.0. Helm on: armour 5.0, fresh 11.0, bonuses 0, fresh 1. Bow in hand: reach melee, fresh ranged; hold 3, fresh 0 |
| `#gearunequip <slot>` (Gear pane, Unequip) | taken | worn gear, pack; `save_player` | no | no | `command:gearunequip` | all but a helm taken off: fighter still "copper longsword" 7.0 and armour 5.0; fresh is "fists" 2.0 and armour 3.0. Next round: "Ironbound Vanguard attacks (copper longsword) wolf 1: 17 damage" |
| `#equip` / `#wield` / `#wear <name>` (typed; named in the help) | taken | the same | no | no | `command:equip` | scale armour on: fighter armour 5.0, fresh 8.0 |
| `#unequip` / `#remove <slot or name>` (typed) | taken | the same | no | no | `command:unequip` | as `#gearunequip` |
| `#enchant <n> <m>` then `yes` (typed, at an enchanter or workshop) | taken | the item, coin, reagent; `save_player` | no | no | `command:enchant`, then the answer's line | Keen bound into the worn longsword: fighter 0 bonuses and "copper longsword"; fresh 1 bonus and "copper longsword of Keenness" |
| `#attradd <attribute>` (Character pane, +) | taken | attributes, points, pools; `save_player` | in memory only: maximum pools, attributes, ward, armour (not weapon, bonuses, reach, moves) | **no** | `command:attradd` | mage: character and fighter con 21, int 33, hp 88/133, mana 114/128; the saved row still con 20, int 32, 85/130, 111/125. After the next typed line the fighter is con 20, int 32, hp 75/130, mana 111/125; the character keeps con 21, int 33, maximum health 133 |
| `#allocate con 2 int 2` then `yes` (typed) | taken | the same | the same | **no** | `command:allocate`, then the answer's line | the same loss at the next typed line |
| `#useitem <name>` (Pack pane, Use) | taken (`CombatScene.free_item`) | the pack, the fighter's pools | yes: it acts on the fighter | yes | `command:useitem` | memory equals row afterwards; a refresh made just before by `#attradd` is kept because this saves the row |
| `#compname <id> <name>` / `#name a = b` | taken | the companion's name; `save_player` | no: the ally keeps the old name | no | `command:compname` | companion "Fang", the fight's ally and the round's log still "Grey Wolf" |
| `#questabandon <id>` (Quests pane) | taken | the quest list | not applicable | not applicable | `command:questabandon` | "Abandoned: Something in the Greywood." in the middle of the fight |
| `#boardabandon <id>` (Board pane; the same handler) | **locked** | nothing | | | `command:boardabandon` | "Not in the middle of a fight." |
| `#prepare` / `#bring` | taken, refused by `loadout.change` | nothing | | | `command:prepare` | "You cannot change what you bring in the middle of a fight." |
| `#prebuff` / `#opener`, `#mount none`, `#pronoun` | taken | a preference or the mount; no fight number | not applicable | not applicable | one each | no difference between fighter and fresh |
| `#goto`, `#goroad`, `#maproad`, `#mapgo`, `#shopbuy`, `#shopsell`, `#boardaccept`, `#boardrequest`, `#boardjoin`, `#boardhire` | **locked** (`FIGHT_LOCKED`) | nothing | | | one each | "Not in the middle of a fight." |
| `#menu` | refused by its own check | nothing | | | `command:menu` | "Not in the middle of a fight. Finish it, or flee, first." |
| `#levelup` (debug only) | taken when debug is on | level, points | no (read, not run) | no | | not run: debug was off |

After closing the save and opening it again in the middle of the fight the fighter is still the old one in every "no" row: the fight
is resumed from its row, and no gear command writes the row.

The partial refresh mixes the two: after the gear was stripped, `#attradd strength` brought the fighter's armour to 3.0 (the new
gear) and left the weapon "copper longsword" 7.0 (the old).

## 2. A command that fails half way

A `RuntimeError` was raised after the state change and after `save_player`, at the command's last drawing step.

| Command | Where it was made to fail | State hash before | State hash after | Steps counter, worn gear, pack, attributes, points, health, fighter, memory against row |
|---|---|---|---|---|
| `#gearequip` (out of a fight) | the pane's redraw | 38f379d3cfbb | 38f379d3cfbb | all as before |
| `#useitem healing draught` (in a fight) | `CombatScene.show` | same | same | all as before; the draught is back in the pack |
| `#attradd` (in a fight) | `show_header` | same | same | all as before; the point is back |

So every command runs inside one operation and is given back whole when it fails.

## 3. Recording and replay

A session of 31 inputs was recorded with `session.record(folder, rows=True)`: 20 commands (12 of them during the fight: gear, attribute
points, a draught, views, a locked command, a rename) mixed with typed lines. It was then replayed the way `tools/rerun.py` does it,
under another save name, comparing after every input the state hash, the outcomes, the operations, what was presented and the words shown.

Result: **31 of 31 inputs matched; 25 of 25 recorded model calls served; no input left unasked; no fault.**

The commands are in the recording (the recorder wraps the console's `ask`, so a clicked command is an input like a typed one), and each
shows as one operation `command:<name>`. A view, a refused command and a locked command each commit one operation too and move the
state hash (the steps counter), which is the design (f721: each input is counted).

The three goldens in `data/replay/sessions` hold two commands in 76 inputs (`#useitem healing draught` and `#stats`); none holds a gear
command, an attribute point or an enchantment in a fight.

## 4. Can a command be sent while a turn is being answered

Through the real server (`ui/gui/server.py`) and a `Bridge`, no game behind it:

| State of the bridge | Line posted to `/input` | Answer |
|---|---|---|
| no prompt waiting (a turn is being answered) | `#gearequip x` | 409 "not at the main prompt" |
| no prompt waiting | `I attack` | 409 "not waiting" |
| the main prompt | `#gearequip x` | 200 |
| the main prompt, already answered | `#gearequip y` | 409 "not waiting" |
| a prompt that is not the main one | `#gearequip x` | 409 "not at the main prompt" |
| a prompt that is not the main one | ` #gearequip x` (a leading space) | 200: the server tests the raw text, the bridge strips it afterwards |
| a prompt that allows the menu | `#gearequip x` | 409 |
| a prompt that allows the menu | `#menu` | 200 |

So no command reaches the game while a turn is being answered. The fight uses the same main prompt as the rest of the game
(`scenes/world.py` 1061), so every command is let through between rounds.

## 5. The event stream once the bridge is closed

`Bridge.since()` skips its wait when the bridge is closed, and the server's event loop then writes a ping and asks again.

| State | Pings in one second | Bytes | Process CPU in that second |
|---|---|---|---|
| bridge open, nothing happening | 0 | 0 | 0.00 s |
| bridge closed, the game thread not finished | 89,449 | 715,592 | 1.56 s |
| the same, the page no longer reading | (the write blocks) | | 0.06 s |

It lasts until the game thread finishes: the rest of the turn when the window is closed in the middle of one (the launcher waits 10 s
for it), or the 10 s between `quit_game()` and the process leaving when an update is installed (`core/updates.py` 134-135).

## 6. Smaller measurements

- A view sent through `play()` costs 1.1 to 1.5 ms, 6 store writes and 1 operation record; its body alone about 0.1 ms. The pinned
  view adds one such input after every typed line. Not worth a finding.
- The Pack pane's Use button sends the good's name, not its uid. Of the 16 goods that carry the button, none has a name that finds
  another good in the pack (0 of all ordered pairs), so nothing goes wrong today.
- An ooze's corrosion: three hits took the fighter's armour from 5.0 to 3.893 with the counter at 24 of the cap 30; one `#attradd`
  put the armour back to 5.0 and left the counter at 24. With the row not saved (section 1) the next typed line puts 3.893 back, so
  the undoing lasts today only when a draught follows the click.
