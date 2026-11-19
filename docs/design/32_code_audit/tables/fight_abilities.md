# fight-abilities: what was run, and what it showed

All runs are CPU-only under simlib's stub. Scripts and their output are in `audit/work/` (fa_lib.py, fa_matrix.py, fa_edges.py,
fa_edges2.py, fa_edges3.py, fa_dbg1.py, fa_scene.py; outputs fa_matrix.out, fa_edges.out, fa_edges2.out, fa_scene_mage.out,
fa_scene_rest.out).

## 1. One ability a cast, across the tables (fa_matrix.py, bare fights)

After each cast: the cost left the right pool once; the cooldown began at cooldown + 1; the status or buff exists, carries its
source, and ends after its rounds; the fight written to its row and read back (services/fight.py row and resume) dumps the same.

| group | checks passed | checks failed | what the failures were |
|---|---|---|---|
| riders (21, on a stamina strike and a mana bolt) | 197 | 3 | two were my expectation (a mana damage ability is a ranked spell, tier light); one is the unused `rounds: 3` on rider ignite (minor) |
| shapes (16, stamina and mana) | 82 | 0 | |
| buffs (13: self, an ally, a fallen ally) | 115 | 13 | all in the bare engine only: a buff named for a fallen ally lands on the corpse (the service never offers the fallen) |
| commands (5) | 16 | 4 | the cost is paid with no companion to obey (finding 8) |
| heal forms (6: self, ally, fallen ally, whole ally) | 109 | 0 | nobody past their maximum; only Rescue raises the fallen; renew ends after 3 turns |
| summon forms (7) | 47 | 0 | bodies, placement, the fade round |
| martial forms and maneuvers | 77 | 0 | |
| ranked spell forms (charged released after a reload) | 25 | 0 | |

668 checks passed, 20 failed (classified above). No difference was found between a fight and the same fight read back from its row.

## 2. Through the real scene (fa_scene.py)

| fight | rounds | abilities asked for | closed and reopened after round 4 |
|---|---|---|---|
| mage, level 10, 3 wolves | 9 | flame_tongue, ignite, frost_ward in turn | every round's fight row and character record equal to the uninterrupted run |
| warrior, level 10, 3 wolves | 9 | brutal_strike, shield_wall, cleaving_sweep | equal |
| summoner, level 10, 3 wolves | 9 | call_the_pack, call_the_warden, hunt_together, spirit_dart | equal (4 summons standing and a bleeding companion at the close) |
| summoner, three fights | | the Bound spell cast in fight 2 | fight 3 begins without the Bound summon (finding 3) |

## 3. The edges (fa_edges.py, fa_edges2.py, fa_edges3.py)

| edge | result |
|---|---|
| a cast at zero mana or stamina (damage, heal, buff, summon, command, movement) | refused, nothing changes |
| an overcast | goes through the named spell's once-a-fight lock and day lock, and a technique's cooldown (finding 4) |
| a summon dying to a lasting effect | no burst, no dead mark, foes stay tied: the cause is trace-fight-4's |
| a tamed foe | leaves the fighter list; the next two summon castings share a serial (finding 10) |
| a dominated foe | struck by the player's sweeps and ground, still engaged with the player (finding 9) |
| movement while held | 8 of 11 movement kinds leave a grapple, the status stays (finding 12, RE-RATE trace-fight-9) |
| an area effect that reaches an ally | no true ally or the player was hurt by any of 268 abilities (Blood Price apart, by design); a turned foe is (finding 9) |
| healing past the maximum | never, in every heal form |
| an ability on a dead or fled target | the service re-aims the player's choice; Spell Echo does not (finding 1); an area cast strikes those who fled during it (finding 2) |
| a charged spell or wind-up | loses Archmage's Focus, Overchannel's blood and the heavy-ability perks (finding 5) |
| a free or blood-paid cast with the pool short | Blood Summons, Echoing (finding 6), Shadowmark's return (finding 7) |
| the transfer heal | 30% of what it heals, not the card's 60%; full price for a 5-point heal (finding 11) |
