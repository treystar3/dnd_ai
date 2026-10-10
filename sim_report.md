# Bot simulation report - enemy strength raised, bots fighting at their level

Ten classes played by bots from level 1 to level 150 on the real engine with a stand-in model. This is the third full run of the session
(run 1 = before the enemy-strength change, run 2 = stronger enemies, run 3 = stronger enemies plus bots that pick fights near their level
and skip contracts far below them). Run 3 also gives the monk bot legendary wraps carrying the new monk effects at levels 12, 35, 60, 90, 120.

Full per-class detail (xp and coin sources, gear at the end, travel, quests, deaths) is in `sim_report_full.txt`.
Rerun with `./runbal.sh`, then `python tools/botreport.py sim_out [older_run_folder]` and `python simreport.py`.

## Changes behind this run
- Creature health about 1.3-1.35x and damage about 1.5x from level 25 up (less below that); `creatures.calibration` in `data/rules/combat.yaml`.
- Bots choose hunting grounds whose enemies are close to their level, and skip hunts, bounties and dungeon floors below roughly 0.6-0.7 of their level.
- Four wraps-only legendary effects: Ki Strike, Open Palm, Flowing Step, Still Water.
- Earlier in the session: creature size scaling compressed, point-blank accuracy penalty for bows, stamina costs and momentum, enchant fees scaling with item level.

## Headline per class (run 3)
| Class | Day reached 150 | Deaths | Guild rank |
|---|---|---|---|
| Ranger | 367 | 11 | S |
| Mage | 368 | 10 | S |
| Smith | 490 | 35 | S |
| Monk | 540 | 28 | S |
| Summoner | 633 | 22 | S |
| Warlock | 845 | 15 | C |
| Paladin | 878 | 31 | D |
| Warrior | 1176 | 60 | D |
| Bard | 1183 | 28 | S |
| Priest | 1360 | 40 | D |

## Are the bots fighting enemies at their level?
Strongest enemy in each fight compared with the bot's level, all classes, 11,535 fights.

| Measure | Run 1 | Run 3 |
|---|---|---|
| Within 3 levels | 13% | 15% |
| Within 5 levels | - | 23% |
| Within 10 levels | - | 43% |
| More than 20 levels below | - | 27% |
| Average gap | -17 | -13 |

| Bot level | Within 3 levels | Average gap |
|---|---|---|
| 1-9 | 57% | -0.9 |
| 10-24 | 26% | -5.6 |
| 25-49 | 14% | -6.4 |
| 50-74 | 12% | -9.6 |
| 75-99 | 15% | -8.7 |
| 100-124 | 15% | -16.8 |
| 125-150 | 7% | -27.3 |

Through level 100 the bots mostly fight close to their level. From 100 up the world runs out of peers: even the top zones (levels 110-165) mostly spawn
creatures well under level 150. That is a content ceiling, not bot behaviour.

## How many fights are rated trivial?
Trivial means the bot's own pre-fight estimate gave at least a 97% chance to win.

| | Run 1 | Run 3 |
|---|---|---|
| All fights rated trivial | 91% | 80% |
| Favorable | 2% | 4% |
| Even | 1% | 2% |
| Dangerous | 1% | 2% |
| Deadly | 5% | 10% |
| Bot wins / flees / dies | 94% / 5% / 1% | 87% / 11% / 2% |

Fights within 5 levels of the bot (2,676): 65% trivial, bot wins 78%, about 20% of health lost, 7.3 rounds.

| Bot level | Fights rated trivial | Near-level fights rated trivial |
|---|---|---|
| 1-9 | 55% | 49% |
| 10-24 | 71% | 56% |
| 25-49 | 76% | 64% |
| 50-74 | 78% | 69% |
| 75-99 | 80% | 83% |
| 100-124 | 86% | 59% |
| 125-150 | 89% | 84% |

## Class comparison (fights within 5 levels of the bot)
| Class | Win | Health lost | Rated dangerous or deadly | Flees (all fights) |
|---|---|---|---|---|
| Ranger | 90% | 24% | 11% | 10% |
| Mage | 90% | 12% | 10% | 4% |
| Summoner | 88% | 22% | 10% | 4% |
| Warlock | 86% | 8% | 14% | 10% |
| Paladin | 84% | 28% | 16% | 10% |
| Monk | 80% | 21% | 20% | 14% |
| Priest | 77% | 20% | 22% | 11% |
| Smith | 73% | 23% | 22% | 9% |
| Bard | 66% | 16% | 36% | 15% |
| Warrior | 64% | 26% | 32% | 14% |

Warrior and bard are the weakest in close fights. Warrior, priest and bard are also the slowest to level, because the bots now skip easy contracts.
The monk finished wearing the legendary wraps with Still Water; the monk effects did not change its ranking much.

## Gear switching
Bots swap gear all the way through, but fall behind late.

| Class | Equip swaps | Items swapped per 10 levels | Bought | Enchants | Worn item level at 150 |
|---|---|---|---|---|---|
| Warrior | 52 | 3.6 | 28 | 46 | 104 |
| Paladin | 45 | 3.2 | 28 | 29 | 99 |
| Monk | 43 | 3.3 | 27 | 38 | 84 |
| Ranger | 39 | 3.4 | 32 | 37 | 99 |
| Smith | 43 | 3.4 | 26 | 35 | 94 |
| Mage | 42 | 3.7 | 25 | 34 | 97 |
| Warlock | 55 | 4.1 | 25 | 41 | 88 |
| Priest | 49 | 3.9 | 28 | 51 | 102 |
| Bard | 43 | 3.5 | 30 | 36 | 86 |
| Summoner | 42 | 3.7 | 26 | 45 | 78 |

Swaps peak between levels 10 and 100 (about 70-90 events per band across all classes) and fall to about 45 per band after 100. At level 150 the bots wear
gear 48-72 item levels behind them.

## Caveats
- One run per class, so differences of a few points between classes are noise.
- The bots fight mostly ordinary enemies, so this says little about boss balance; the class harness (`tools/tune_classes.py`) covers bosses.
- The ratings come from the bot's own 24-run estimate of each fight.

## Open questions
- Add higher-level creatures and zones for levels 100-165 so late-game characters have peers.
- Investigate the warrior and bard close-fight results.
- Late-game gear: bots stop upgrading after level 100.
