# f710: the people a road happening shows are people of the game

Pillars 1 (the world is real) and 2 (the player is understood). Found in the third blind play (docs/play/2026-11-16_blind_play_journal.md,
19th and 20th days): on the King's Pass a road happening bearing on a matter ("The voice from the Greywood") showed two dazed men under
a lean-to muttering "We dig. At night. I don't know for what. I know where." It was rolled a **sight**, so the walk went on past them
(f427), and f702 kept it as a landmark. f709 now walks back to it, and the passage shows the men again, but
`I crouch beside the two men and ask them where it is they dig at night.` went to Gusmund, my own archer: the men are words in a
passage, not people of the game, so the matter's hook ends where it was shown.

## What is there today (facts)

- A road happening's kind is rolled by the engine (road.yaml `kinds`), before the writer is called. Only `find`, `meeting`, `hazard`,
  `aid` (and an ambush) stop the walk (road.yaml `stops`, the owner's review Q2: "what stops the walk is anything the player could act
  on (a person met, someone in need...)"; "no passing sights shouldn't stop").
- A meeting or aid stop is given someone: `roads.make_stop` puts `residents={role: 1}` on the stop, and entering it makes the person
  through the normal resident call (npc/life.py populate_place). They talk like anyone; they leave with the stop ("moved on along
  the road", leave_road).
- A matter shown on the road (`matters.road_matter`, `road_lines`, `road_shown`) asks the writer to let the player learn the matter's
  next clue "as a thing seen or said", whatever the kind, and marks that clue found on the road.
- The engine already lets a person know a clue and tell it: `matters.hold` writes a "knows" memory row about thread:<id>:<n>;
  `clue_facts` puts it among WHAT YOU KNOW in their talk; a reply that reveals it is marked found by `mark_found` (f483).

So the fault is one of kind: a matter's happening rolled as a sight can show people saying things, which by Q2 is a person met.

## The change

1. **A matter's road happening that shows its clue as something said is a meeting.** When the road carries a matter and the kind
   rolled is a sight, the kind becomes a meeting: the walk stops, someone is there (the writer's meets_role, else road.yaml
   stop_roles.meeting, the wanderer). A find, hazard or aid rolled with a matter stays what it is (each already stops). A sight
   with no matter stays a sight, told inside the walk and kept as a landmark (f702), with nobody to talk to; the writer's sight
   instruction (STOP_MUST gains a `sight` entry) says what passes is seen from the road and no one there is spoken with.
2. **The person met holds the matter's next clue.** The clue the scene shows is found on the road as today. The person made at the
   stop is given the next unfound clue of that matter with `matters.hold`, so asking them about it can bring it out, marked found by
   whoever told it (`mark_found`), as with any holder in town. With no clue left, they still know what the scene showed (the stage),
   and talk like anyone met.
3. **Gone when the player walks on**, as every stop's people are (f423, leave_road): what they held and did not tell goes with them.
   The clue is not lost to the matter: it can still be found where the matter's own holders are (f483 binds holders in town).
4. Numbers and words in data: road.yaml `matter_meets: true` (a matter's sight becomes a meeting; false keeps today's behaviour) and
   the sight instruction's words; data_check rows.

## What it costs

- A matter's sight now stops the walk and makes one person (the resident call every meeting already makes). A matter shows on the
  road at most once (road_matter's `road` flag), so this is at most one more stop per matter.
- Goldens: a stub recording whose road event carries a matter and rolled a sight would change outcome (a stop instead of walking
  on); each change is read and explained before a rebless, as the rebless skill asks.

## Tests (tools/sim/road_people_710_test.py, written first, seen to fail)

- A road happening with a matter, rolled a sight, stops the walk at a stop with one person of the meets_role (else the wanderer).
- That person holds the matter's next unfound clue (a knows row); a reply revealing it marks it found by them; the clue the scene
  showed is found on the road as before.
- A sight with no matter still goes on, kept as a landmark, nobody there; its writer instruction says so.
- A find, hazard or aid with a matter stays its kind.
- Walking on removes the person as any stop's; the matter's clue stays findable in town.
- road.yaml `matter_meets: false` gives today's behaviour.
- A case other than the one that found it: a matter whose shown clue is a thing seen (a signpost, "BY ORDER OF THE SHEPHERD"), where the
  person met is a wanderer who saw it put up.

## Modules touched

scenes/road_actions.py (the kind, the hold after the stop is entered, STOP_MUST sight), engine/matters.py (the next clue after the shown
one, a small helper), data/rules/road.yaml, engine/data_check.py, the new test. No change to npc/, the talk path or the matter rules.

## Questions for the owner

1. **A matter's sight becomes a stop (recommended), or stays a passing sight?** Q2 says a person met stops the walk; a matter's
   happening is the one kind of sight that usually shows people who say something. Recommended: it becomes a meeting.
2. **The person met holds the next clue (recommended), or only what the scene showed?** Holding the next clue makes stopping worth it
   and uses the existing f483 machinery; holding nothing new makes the talk a dead end.
3. **Do the people of an ordinary sight (no matter) stay out of reach (recommended)?** A distant caravan or a shepherd on a far hill is
   seen, not met; the sight instruction says so, and f702 keeps it as a place to come back to.
