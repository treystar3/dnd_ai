# 18. Plan: fixes for the class, after the audit of phase 2

Status: the plan, with the owner's answers of 2026-11-13 (section 7); nothing built. Written 2026-11-13 on `pillar2/class-fixes` (cut
from `pillar2/outside-combat`, PR #39) after the
owner's rule of the same day (GOALS.md "Infrastructure over patches": a fix names the class of cases it covers, never one scene) and
an audit of phase 2's 28 feature commits against it.

Feature numbers are provisional: each takes the next free number when it is built (f615 on).

## 1. What the audit found

25 of the 28 commits are general mechanisms. Four findings, each checked in the code:

1. **f612 is a patch.** It wrote the owner's ruling ("seeing in the dark can be a skill check using perception") into the corpus and
   changed nothing in the engine. In the game the act is still refused.
2. **f610 marks its class by hand.** `bounded: true` sits on the two lines that failed (the king, the dragon's hoard). Three lines
   of the same kind are unmarked: ordering the town to bow, the wolf pack accepting a leader, the merchant signing his shop over.
3. **The prompt quotes the corpus.** The act prompt's examples of an impossible act (engine/act.py:32, engine/ruling.py:41: a dragon
   summoned from nothing, conjured gold, making the sun set) are three corpus lines (data/replay/ruling_cases.yaml:32, 35, 41).
4. **Engine-written news carries a dash.** Six sites write lines like "<title> - lost." into the world's news and history
   (engine/pulse.py:592, 599; engine/events.py:647, 709, 1227, and a narrator direction at 1394). Not a patch, but it breaks the
   owner's no-dash rule, and it is one class.

One finding was looked at and needs no change. The cart wheel (f611) passes on a live run whether the danger is lifted or left, but
the engine lifts it only for force on a check of body or arms (act.yaml force_checks, f600), and tools/sim/ruling_either_611_test.py
holds each framing to exactly that. No wrong outcome can pass.

Two cases the pod left wrong were never patched and are planned here too: the granary's stallholder never made safe (part C), and
the guild hall jump ruled a cost (part D).

## 2. Part A: the measure is honest (tools and corpus only)

**A1. The prompt and the corpus are kept apart (f615).**
- Class: every example a prompt gives the model, against every line of every corpus.
- A check in tools/ruling_eval.py, run when a corpus is loaded and by a test in tools/sim: a corpus line that shares two or more
  content words with one example in engine/act.py SYSTEM or engine/ruling.py SYSTEM is refused, naming both.
- The three lines are replaced in the corpus by fresh ones of the same kind (a creature called from nothing, wealth from nothing,
  a command to the sky). The game's prompt is not touched, so no golden moves and the pod's numbers for the game stand.
- The first set's score keeps its size (50). The three old lines were right in every pass, so past scores read at most 3 high.

**A2. A case says what kind of act it is, and the bound follows the kind (f616).**
- Class: every act whose words claim more than saying them could bring about (a title claimed, a crowd commanded, a person
  persuaded past reason).
- A corpus case gets `kind: claim`. On the act's path a claim is right when the ruling is a no, or when it is bounded as f609
  bounds it: it says what it comes to, and changes and makes nothing. `bounded: true` is removed.
- The test checks the rule on every claim case in the corpus, not on the king's line alone, and that no other case is touched.
- The owner's answer (section 7): five lines are claims (the king, the dragon's hoard, ordering the town to bow, the wolf pack
  accepting a leader, the merchant signing his shop over), and a bounded plain yes is right as a bounded cost is.

## 3. Part B: a power the character lacks, decided by the engine (f618)

This replaces f612.

**What happens today.** The prompt tells the model that an act which "needs a power they do not have" is a no, and shows it what
the character has. So the model decides, and on the pod it ruled the dark tunnel a no in both passes. A no carries no `requires`,
so the engine never learns which power was missing. When the model does name the power (a yes with `requires: [darkvision]`), the
engine refuses on its own grounds (engine/act.py:310).

**Class:** every act that needs a capability of data/rules/capabilities.yaml the character does not have, on both ruling paths
(the act's, and the road hazards' old ruling).

**The mechanism: the model names the need, the engine decides what lacking it means.**
- data/rules/capabilities.yaml: a capability may say what stands in for it: `without: {check, hard, told}`. A capability with no
  `without` stays a no with its `lacking` line, as today (flight, passing through walls). The owner's four (section 7):

  | Capability | Check | Difficulty | Told to the narrator as |
  |---|---|---|---|
  | darkvision | perception | fair | by slow care and what little can be made out, not by sight |
  | invisibility | stealth | hard | by cover and shadow, seen by anyone who looks straight at them |
  | mind_reading | insight | hard | by what a face and a voice give away, never the thought itself |
  | water_breathing | constitution | hard | on one held breath, no longer |
- One reader for both paths (engine/ruling.py): given what a ruling requires and what the character has, it returns one of three
  things: has it; lacks it with a stand-in; lacks it with none.
- A yes or a cost that requires a lacked capability with a stand-in is no longer refused. It becomes a cost rolled on the
  stand-in's check at its difficulty, or the ruling's own if that is harder. The narrator is told how it is done (`told`).
- The grammar's no may name what it lacks (`requires`, capabilities only). A no that names a lacked capability with a stand-in is
  turned into the same cost. So whichever way the model rules, the engine reaches the same answer.
- As built: the grammar makes `requires` a required key of a no, so a no says what power it wants, if any. No line was added to
  the prompt.
  The act ruling's request text changes, so goldens that hold one are re-blessed.
- engine/data_check.py: `without` names a real check or attribute and a real difficulty.

**Test (f618):** a table over every capability in the file, for a character with it and one without: stands, becomes a cost on
the stand-in's check, or is the `lacking` no. It runs on acts other than the tunnel (searching rocks for crabs in the dark, which
the pod refused) and on both ruling paths. tools/ruling_eval.py counts noes given for want of a power that has a stand-in.

**Measure:** the two dark cases on the pod, with the next session.

## 4. Part C: what follows from a change is the engine's (f619)

**What happens today.** A person a situation harms is "safe" only if the model asks for it as a change resting on an earlier one.
On the pod it lifted the granary's danger and never made the stallholder safe, in all six passes. The situation's ending is already
right without it (every threat resolved reads as achieved, engine/situation_parts.py reading()). What is wrong is the state between:
the part still says harmed, and the person keeps a worry the world no longer gives them.

**Class:** every state that is a consequence of other states, not an act of its own. `safe` is the first: a person at stake in a
situation's heart is safe when no threat of that heart is still in force.

**The mechanism.**
- data/rules/situations.yaml: a table of words the engine derives, each with the reading that makes it true (`safe`: no threat of
  the heart in force).
- One step in engine/situation_parts.py, run wherever a situation's parts change (an act's kept changes, a way met, the pulse):
  derived words are set by the engine, with their reason. The model may still ask for `safe` where it is an act (leading one
  person out while the danger stands); the authority rule stays.
- tools/ruling_eval.py judges a case's `moves` on what the engine leaves, kept and derived, not on the ruling's kept changes alone.

**Test (f619):** dangers lifted by an act, by a way and by the pulse, each leaving everyone at stake safe; a second danger still in
force leaves them harmed; a model's own `safe` still works. On situations other than the granary.

## 5. Part D: feats of the body, measured (design only, a pod probe first)

The guild hall jump is ruled a cost at fair in every pass, and the model never chose "beyond" in 198 rulings. The engine holds no
sizes: the guild hall is not a part of the place, so there is nothing to measure the jump against.

**Class:** every feat a body's strength bounds (a jump, a lift, a throw, a held breath).

**The idea.** The model describes the world, so it says how big the feat is (a jump of about 30 feet). The engine holds what a body
can do by its attributes (data) and refuses what is past it, with the nearest thing that would work. "beyond" then has no job and
can be removed.

**Not planned to build yet** (the owner, section 7: probe first). It rests on a 12B model giving honest sizes, which nothing has
measured. The next pod session carries a probe of 20 lines (ask for the size only, compare with sense). The design is written once
the probe's numbers are in.

## 6. Part E: the engine's own lines carry no dash (f617)

**Class:** every line the engine writes into the world's news and history.

- engine/pulse.py add_news and add_history, the one writer of each, pass their text through engine/hygiene.py undash, which the
  narrator's answers already go through.
- The six sites are reworded so they read well without it ("<title> is lost.").
- Test: every line in a played script's news and history has no dash; a ratchet over the engine's and the scenes' code for a
  spaced hyphen in text handed to either writer.

## 7. The owner's answers (2026-11-13)

1. **Stand-ins.** Asked which lacked powers fall back to a check beside darkvision (perception, fair, decided on 2026-11-12):
   "Invisibility, Reading a mind, Breathing water". So invisibility is stealth at hard, reading a mind is insight at hard, and
   breathing water is constitution at hard. The rest stay a no.
2. **Claims.** "All five, yes or cost": the king, the dragon's hoard, ordering the town to bow, the wolf pack and the merchant's
   shop are claims; a no is right, and so is a bounded cost or a bounded plain yes. This settles the question f613's measure left
   open (whether a plain yes counts on the king's line). The bound itself stays strict (2026-11-12: nothing made, nothing changed).
3. **Feats of the body.** "Probe first": a 20-line probe on the next pod session, the design from its numbers.
4. **Where it lands.** "A new branch": `pillar2/class-fixes`, with its own PR after #39. The rule's commit moves there, and #39
   stays as it was opened.

## 8. Order and size

| Step | Feature | Modules | Why here |
|---|---|---|---|
| 1 | A1 (f615) | tools/ruling_eval.py, the corpus, a test | the measure first, so later numbers are honest |
| 2 | A2 (f616) | tools/ruling_eval.py, the corpus, a test | the same |
| 3 | E (f617) | engine/pulse.py, six sites, a test | small, no decision needed |
| 4 | B (f618) | capabilities.yaml, engine/ruling.py, engine/act.py, llm/contracts.py, data_check, goldens | replaces the patch |
| 5 | C (f619) | situations.yaml, engine/situation_parts.py, tools/ruling_eval.py | the granary's class |
| 6 | pod session | | B and C measured, D's probe; about an hour, under $1 |

Each feature goes through the feature skill: a test first, the goals reviewer, the full suite, a GOALS row where the owner decided.

## 9. As built (2026-11-13)

The numbers above are the order of building: A1 f615, A2 f616, E f617, B f618, C f619. Where the build differs from the plan:

- **A1 (f615).** The check reads only the prompt's examples of a verdict (the bracketed lists on its `sense` lines), not every phrase
  of the prompt; the first cut matched instructions too and was corrected after review.
- **E (f617).** The writers take the dashes out (pulse.add_news, pulse.add_history, and standing.report for a deed's tale); the six
  sites were not reworded, since the writers cover them and any site added later. The test names the writers of news.
- **B (f618).** A no the engine turns into a cost has no words for what it comes to, and a yes's words assume the power, so a success
  on a stand-in is told as working only as far as the stand-in can bring about (f609's bound holds). The count of "noes given for
  want of a power that has a stand-in" was not built; the measure shows ", without <power>" on each such line.
- **C (f619).** The step runs where a situation is read (events.read_end, read_ends), which every change already reaches, and is
  shown to the narrator with the act's own changes. It gives the word back if a threat stands again. A heart that names no threat
  derives nothing. The measure runs the engine's own writers on a copy (tools/ruling_eval.py Dry) and writes nothing.

## 10. Part F: the lines the engine keeps and hands on (f620)

Written 2026-11-13 after f617's review, which found engine code still writing a spaced hyphen into lines outside news and history.
The owner approved it the same day as written ("Approve, build it": the journal left alone, the world's authored words as the next
feature). Built as f620; where the build differs from the plan is at the end of this part.

### What the trace found

Every string in the game's code that holds a dash was listed with the call it is handed to (676 of them), and every request in the
three kept recordings (250 calls) and a play of the world script was read for the dashes that reach a model.

**Already filtered, no change needed.** Most of the 676 pass one of five choke points that exist today:

| What | Choke point | Since |
|---|---|---|
| The story on screen (narration, speech) | ui/console.py guard_outputs: say, narrate, npc_says, dialogue | f396, f403 |
| Everything a model writes | llm/gateway.py undash_answer | f396, f403 |
| What the narrator is told happened (GAME EVENT) | scenes/world.py _narrate_now, narrate_with, opening_telling | f413 |
| A fight's story (61 `tell` sites, engine/bosses.py:81 and the three in engine/damage.py among them) | engine/combat.py tell | f413 |
| News, history, a deed's tale | engine/pulse.py add_news, add_history; engine/standing.py report | f617 |

**Not filtered: four kinds of line the engine keeps and later hands to a model as true.**

| Kind | Who reads it | Makers | A dash today |
|---|---|---|---|
| A townsperson's memory | every speaker's request (YOUR MEMORIES OF THEM) | 17 sites build `Memory(...)` in nine modules | engine/domain_events.py:521, 522, 628; engine/stakes.py:174. Seen in the recordings: "The stranger did the work I asked - mend the fence by the barn - and I paid 30 copper." |
| A hire's memory | the hire's own request | engine/party.py remember, the one writer | none in code; whatever a name or a title carries |
| A fact of the truth layer | the narrator and every speaker (engine/truth.py, 28 sites build `Fact(...)`) | the facets | a deed read back from the event log ("the stranger acted (...) - success", engine/domain_events.py:592); engine/property.py:41; the join in present_lines |
| A fight's story, second writer | the fight's narrator | engine/combat_improv.py:173 inserts into the story without `tell` | whatever the player's own words carry |

### The class and the mechanism

**Class:** every line the engine keeps or assembles as something true and hands to a model that writes prose. Not one site is
reworded; the filter goes where each kind of line is made, as f617 did for news.

- npc/models.py `Memory`: its text passes engine/hygiene.py undash when the memory is made, whoever makes it.
- engine/party.py `remember`: the same, on the one writer.
- engine/truth.py `Fact` and `View.present_lines`: a fact carries no dash, whatever facet built it and whoever reads it.
- engine/combat.py: the story's filter becomes one function that `tell` and engine/combat_improv.py both use, so the story has
  one way in.

### What stays as it is, and why

- **The game's own notes:** `console.note`, `console.ledger`, refusals (105 note sites). The owner's decision (f413): the game's
  notes keep their dashes. A refusal's reason is already filtered where it is handed on to the narrator (scenes/world.py:1650).
- **The fight's log:** engine/damage.py:266 to 326 ("should have fallen - the bond holds it to life") go to `combat.log`, the fight
  pane's list, not to the story.
- **The event log:** engine/canon.py:216 writes a row of the campaign's log. Only the player's rows are ever told, through the truth
  layer, which the `Fact` filter covers. The row itself is a record.
- **Logs:** pulselog, console.debug, error text.
- **Instructions:** system prompts, engine/ability_slots.py's notes for the naming model, engine/actions.py, the lines that tell a
  speaker how to behave ("private - share it only if it comes up naturally"). They are rules, not story, and their wording is what
  the pod's measures ran on.
- **Labels in a request:** the joins a request builder writes itself ("PLACE: Parth - ...", "WHO IS WHO: ...: he, orc - a hired
  mage", "id: label - role" in the interpreter's lists). f413: lists and labels keep theirs. Changing them would move every
  recording and every prompt the pod measured.

### Two questions for the owner

1. **The journal.** The character's `item_history` (engine/pulse.py:938, 942; scenes/inventory_actions.py:214, 565, 569) is read by
   the journal pane and by nothing else: no model is ever handed it. Is the journal the story, or one of the game's own lists?
   Recommended: the game's list (f413), left as it is. If it is the story, one more filter on the character's record covers all five
   sites.
2. **The world's authored words.** The larger share of the dashes a model is handed are not engine-written: they are in data/
   (about 50 lines in data/world: places, lore, roads, a boss's speech; "Roads leave in every direction - the Old Quarry Road...").
   That is a class of its own, with a precedent (engine/data_check.py already refuses a dash in two tables of story words).
   Recommended: the next feature after this one, either filtered where the world is loaded or reworded in the data with a startup
   check. Not part of f620.

### Tests (tools/sim/kept_lines_dash_620_test.py, written first)

- **Each maker, on shapes no site writes:** a memory, a hire's memory, a fact and a fight's story line made with each kind of dash
  come back without it, the words kept; a hyphen inside a word is left alone.
- **The class, played:** the world script plays whole; then a job done, a contract dropped and a gift go through the event bus with
  titles and names that hold a dash, a hire is told something, and an improvised act opens a fight's round. Every memory of every
  person in the save, every hire's memory, every line of the truth view under every profile of data/rules/truth.yaml, and the
  fight's story carry no dash.
- **The ratchet, at the model's door:** every request to a task whose answer is prose, in the three kept recordings and in the
  test's own play, is read line by line. A dash in it must be one of three things: a list mark at the start of a line; a string that
  stands in data/ (question 2's class, named in the test as open); or one of the label shapes the test lists by name with its reason
  (about 18 today). Any other dashed line fails the test and prints the line, so a new path that hands a model a dashed line is
  caught wherever the recordings or the play reach it. The recordings are re-blessed whenever a request changes, so the ratchet
  reads what the game sends today.
- **One way in:** the fight's story has no writer besides the shared function; a hire's memories have no writer besides `remember`.

### Recordings

Memories and the truth view are in the speakers' requests, so all three recordings move: the request text of calls that carry a
dashed memory or fact, and the state where a memory is kept. Call titles, order, outcomes and shown words must not move. Re-blessed
through the rebless skill, with the differences listed in the commit.

### Size

| Module | Change |
|---|---|
| npc/models.py | a validator on `Memory.text` |
| engine/party.py | one line in `remember` |
| engine/truth.py | `Fact` and `present_lines` |
| engine/combat.py, engine/combat_improv.py | one function for the story's way in |
| tools/sim/kept_lines_dash_620_test.py | new |
| data/replay/sessions | re-blessed |

### As built (2026-11-13)

- **The fight's story.** No new function: `tell` takes where in the story a line goes (`at`), and the improvised act's own line goes
  through it. The story grows in engine/combat.py alone.
- **A fact covers the place's own words too.** `Fact` filters every fact, so a line of a place that stands in data/ with a dash
  ("Roads leave in every direction - ...") is handed over without it where the truth layer hands it over. The same line still has
  its dash where a request reads the place directly (YOUR PLACE in a speaker's request, VISIBLE in the narrator's). Question 2's
  class is open as before; this is the part of it the truth layer already answers.
- **Not counted as a repair.** engine/hygiene.py `undash` takes `count=False` for a line the engine wrote, so the night's count of
  dashes mended (REPAIRS) stays a measure of what the models wrote. The four makers and `tell` use it. The older engine callers
  (news, history, a deed's tale, the narrator's event) still count; a small follow-up.
- **Recordings.** Two moved, not three: stub_fight sends no request that carries a dashed memory or fact and replays as it was.
  stub_short: two requests (the place's line in the truth view). stub_party: thirteen requests (the same line, the strangers beside
  the player, two memories) and the two memories' rows.
- **The ratchet.** It lets through a label's own dash and the words that make it that label, never the rest of its line, and a
  string of data/ only as the dash with two words either side of it as the data holds them (the goals review found the first cut
  let whole lines and common word pairs through). Sixteen labels are named. One line is named as known and open: "How people
  around here regard the stranger: unknown - just a stranger." It is one of the lines a speaker also knows right now
  (scenes/world.py npc_context), which mix rules and facts and which the plan left as written; the regard is the game's own label,
  handed over inside a fact. For the owner to rule on.
- **Old saves.** A townsperson's memory is filtered whenever it is read, so an old save's are too. A hire's memory kept before f620
  keeps its dash until it is told anew; no engine line ever wrote one, so only a name or a title could have put it there.
- **The test's deeds:** a job done, work done unasked, a contract walked away from and a gift, each with a dash in its words.

## 11. Part G: the words that stand in data/ (f621; built)

Written 2026-11-13, after f620 left the world's authored words as a class of its own. The owner approved it as written the same
day (reword in the data, with the check; the sorting stands). What was built, and where it left the plan, is under "As built".

### What the survey found

Every string in data/ was read (data/measured and data/replay left out): 240 hold a dash, in 35 files. By what the string is for:

| Kind | Strings | Where | What happens to them today |
|---|---|---|---|
| Told as true | 85 | data/world: places (5), lore (14), regions (3), roads (2), world.yaml (2), goods (1), relics (1), arcs' truths (4), roles' descriptions (8), creature families' lines (42); data/rules: a boss's lines (2), a motive's outcome (1) | handed to the narrator and the speakers, dash and all, where a request reads the data directly |
| Structure the engine reads | 55 | world/pressures.yaml descriptions (53), rules/brief.yaml clause_ends (2) | engine/threads.py `clause` splits a pressure's description at its " - "; brief.yaml lists the dash characters themselves |
| A rule for a model | 48 | what a naming model is to depict (ability_slots, healing, summons), a moment's brief, the frame and register rules (party, severity, speech, mentor), and the like | sent as instructions |
| A label in a pane | 48 | rules/field.yaml blurbs (30), ability and passive texts, effect descriptions | shown in the game's own panes |
| An author's note | 4 | world/bestiary.yaml notes | read by nobody |

Only 9 of the 240 appear in the kept recordings' requests to prose tasks, so the recordings cannot be the ratchet for this class.

### The class and the mechanism

**Class:** every string in data/ that the game tells as true.

**The words are cleaned in the data, and a check at startup keeps them clean.** That is how the project already handles the three
tables of story words it checks (engine/data_check.py: the words for how long ago, the battlefield's words, the improvised act's
lines), and it is GOALS.md's rule that data is the source of truth.

- data/rules/hygiene.yaml gets one table of what is **not** told: by file and key, with its kind (label, rule, structure, note)
  and a reason. About 25 entries cover the 155 strings of the last four rows above.
- engine/data_check.py gets one rule: every string under data/ whose file and key are not in that table carries no dash. The
  default is told, so a new file or a new key is checked without anyone having to add it anywhere, and the game does not start with
  a dashed line of the world in it. The rule also refuses a table entry that names a file or key that is not there.
- The 85 told strings are reworded once: the dash becomes the punctuation it stands for, the words stay. The mender
  (engine/hygiene.py undash) proposes each and every line is read. The proposal for all 85 is in the shared notes
  (`f621-data-words-preview.md`), for example:
  - "Roads leave in every direction - the Old Quarry Road north, ..." becomes "Roads leave in every direction: the Old Quarry Road north, ..."
  - "Greyhollow grew up around what lies under its hills - mining, timber and stonework - and sends ..." becomes "... its hills, mining, timber and stonework, and sends ..."
  - One line the mender gets wrong and is set by hand: "... something that only looks like one - no two tellings agree" must not
    become "one... no two tellings agree" (its rule for broken speech); it takes a colon.

**Why not filter where the world is loaded.** It would need no edit of the data, but: a dash in data is sometimes structure (it
would break `clause` on all 53 pressures unless told which keys to skip, which is the same table again); the mender misjudges
authored prose now and then, and at load nobody reads the result; and the file would no longer say what the game tells.

### What follows from it

- **The data hash moves,** so all three recordings are re-blessed on the new data. The requests that carry a reworded line change
  (a place's lines, lore, a role's description, a road). Call titles, order, outcomes and shown words must not move.
- **f620's ratchet tightens.** Today it lets any string of data/ through. After f621 it lets through only strings under the keys
  the table declares, so a told line of data can no longer pass it either.
- A place's line reads the same in the truth view and where a request reads the place directly (f620 left those apart).

### Tests (tools/sim/data_words_621_test.py, written first)

- The rule on trees it is handed, not on the game's files: a dashed string under a key nobody declared is refused, of each kind of
  dash, in a list, a nested table, a table written on one line and a key; a hyphen inside a word passes; a declared key passes; a
  new file is checked by default; an entry for a key that is not there is refused.
- The game's data passes the rule, and the table declares nothing that holds no dash.
- A pressure's description still gives its clauses (engine/threads.py), and brief.yaml's clause ends still read.
- The world loads, and no told string of a played script's requests holds a dash (f620's ratchet, with the tightened allowance).

### Questions for the owner

1. **Reword the 85 lines in the data, or filter at load?** Recommended: reword, with the check. The lines are in the preview.
2. **Is the sorting right?** Two calls are mine: creature families' lines are counted as told (their file says "one line the
   narrator is told"; 42 lines), and pane labels keep their dashes (f413).

### Found in passing, not part of this

- **Thirteen of the 52 roles load with their description cut short.** data/world/roles.yaml writes each role as a table on one line
  without quotes, so YAML ends the description at its first comma: the smith's is "Works the forge - tools", and "hinges",
  "horseshoes", "the odd blade." become keys nobody reads. Its class is a row of data holding keys its model does not know. It
  wants its own feature (the models refuse unknown keys, the thirteen lines get quotes); best done right after f621, since both
  edit roles.yaml.
- No reader of a creature family's line was found (engine/behaviors.py `text_for` has no caller): the file says the narrator is
  told it. To check when the families are next touched.

### Size

| Module | Change |
|---|---|
| data/rules/hygiene.yaml | the table of what is not told |
| engine/data_check.py | the rule |
| 12 files under data/ | 85 strings reworded |
| tools/sim/kept_lines_dash_620_test.py | the allowance reads the table |
| tools/sim/data_words_621_test.py | new |
| data/replay/sessions | re-blessed on the new data |

### As built (f621)

- **The rule:** engine/data_check.py `data_words_problems`, in the startup check. It reads every YAML and JSON file under data/
  (data/measured and data/replay left out), the keys too. The table is data/rules/hygiene.yaml `data_words`: 26 keys in 22 files.
  A key covers itself and all under it, named alone or as a dotted run (`frame.shows`).
- **138 strings reworded, not 85.** The plan left the 53 dashed descriptions of world/pressures.yaml alone as structure, because
  engine/threads.py `clause` cut them at the dash. The test, written first, showed they are also handed whole to three requests
  (engine/pulse.py `context_for_place`, engine/stakes.py "PRESSURES:", engine/situation_parts.py `trouble`). So they are told like
  the rest: the head now ends at a colon and `clause` cuts there (one line of code). Declaring them structure would have kept 53
  told lines with a dash behind a table entry.
- **How each was reworded:** the dash became a colon in 122. Sixteen went another way: a comma (a boss's last stand, a motive's
  outcome, the monarch's role, two pressures of the form "this, or that"), a semicolon (Frostholm's lore), parentheses for an
  aside between two dashes (three arcs' truths, Greyhollow's lore, the guild halls' lore), and one pressure (rimewind_march)
  made two sentences, its things after the colon. The Hollow's line took its colon by hand.
- **`clause` gives better clauses for three pressures.** "X - or Y" used to give only "or Y"; with a comma it gives either half.
  The Rimewind line used to give a broken half ("a winter hag or a frozen host - and Frostholm braces for a long"); it gives its
  things.
- **Five roles now load whole.** A colon inside a table written on one line needs quotes, so the smith, the guild master, the
  carpenter, the monarch and the chamberlain got them, and their descriptions no longer end at the first comma. The other eight
  cut-short roles, and the check that would refuse a row's unknown keys, are still the follow-up below.
- **f620's ratchet** lets through only strings under keys the table declares.
- **The recordings:** all three re-blessed on the new data. Titles, order, outcomes and shown words did not move. Requests that
  differ: stub_short 10, stub_party 16, stub_fight 1 (the boss's own line, handed to the naming of what it dropped). stub_fight's
  state differs at inputs 3 to 19, in kv: the boss's lines are kept in the fight while it lasts.
- **Not done:** rules written for a model (48 strings) keep their dashes, as planned; whether a model copies a dash from its own
  instructions is not measured here.

## 12. Part H: a row of data holds no key its model does not know (f622; built)

Found while f621 was checked (2026-11-13): eight roles in data/world/roles.yaml were written as a table on one line with a comma in
the description and no quotes. YAML ended the description at the comma and made keys of the rest ("Sells candles", then `rope` and
`oil and sundries.`); the model dropped those keys in silence, so every prompt that named the role was told half of it. f621 had
quoted five such roles because they needed a colon. The owner approved the plan below the same day ("Approve, build it").

### What the survey found

Every typed model built while the game's data loads was watched: 40 models, 4,687 rows. 39 of the 40 ignore a key they do not know.
From data, only the eight roles dropped any (chandler, wanderer, guild clerk, loremaster, engineer, water priest, noble, land agent;
nine stray keys).

### The class and the mechanism

**Class:** every row of an authored file that is built into a typed model, at any depth of the row.

- core/yamlio.py `row(model, raw, where="")` builds the model and refuses a key it does not know (pydantic's per-call
  `extra="forbid"`, which holds for the rows inside a row too; requirements.txt asks for 2.12, the first version with it).
- The seven loaders of authored files go through it: world/loader.py (the world's lists, a town's profile), core/rules.py (stats,
  triggers, mechanics, the passive families), engine/items.py (items, materials, gems, legendary effects), engine/inventory.py
  (goods, recipes), engine/enchanting.py (the general enchantments), engine/pools.py and npc/traits.py. A loader that collects
  problems keeps collecting them; one that does not is told the file, the row and the key.
- The models are not made strict. A place, an item and others are also read back from a save, and an older save's retired key must
  not stop it loading.
- A field that is the author's own table (a place's stations, a role's stock) takes any key, as before.

### Where the build differs from the plan

- **Seven loaders, not six.** npc/traits.py loads when a session starts, not when its module does, so the survey did not see it.
  The test's watch did.
- **The ratchet watches roads, not dropped keys.** The plan watched for a key dropped at load. The test instead keeps every
  mapping core/yamlio.py hands out and fails if one is handed whole to a model by any road but `row`: at import, at the startup
  check, at a session's start and through a short played script. So a loader that unpacks a row into its model is caught while its
  data is still clean. What it cannot see is under "Not covered".
- **A general enchantment's row is handed whole (the goals review).** It was built field by field, so a misspelt
  `fee_multiplier` on it was dropped and the watch above did not see it. The line that turns a material's effect into an
  enchantment's (engine/enchanting.py, the `flat` flag below) is as it was.
- **The recordings:** all three re-blessed on the new data. stub_short: one request differs (call 2, ResidentSet: "land_agent
  (Sells houses and lots in the city, and knows who is leaving and who is moving in.)"); no state, outcome or shown word differs.
  stub_party and stub_fight: no request differs.

### Not covered, said plainly

- **A mapping the code reads key by key, whether or not a model comes of it.** A stray key there is ignored unless a hand-written
  check holds it (the fight's tables are held both ways since f504 and f509). Known today: the top keys of world.yaml
  (world/loader.py load_world), Orenna's coin (scenes/orenna_actions.py), a battlefield's zones (engine/battlefield_builder.py),
  and every table that never becomes a model. That is a larger class of its own: it needs each table's keys written down.
- **What the test's watch cannot see:** a row read key by key (above); data read by another reader than core/yamlio.py (the
  startup check's own loader, JSON); a loader on a path the short played script does not walk.
- **A key dropped in code, not from data.** engine/enchanting.py turns a material's effect into an enchantment's and loses its
  `flat` flag (112 rows). No data sets that flag, so nothing is wrong today; a material effect given `flat: true` would become a
  percentage as an enchantment.
- **A model with an `__init__` of its own** is not held inside by the per-call check (tried: a stray key in one is taken). No
  model a row becomes has one, and the test fails if one gains it.
