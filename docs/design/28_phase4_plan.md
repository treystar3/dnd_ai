# 28. Phase 4: plan

Status: **approved by the owner on 17 November 2026** ("Approve as recommended": questions 1 to 5 as recommended below; question
6, the reading of the gate's script, is still the owner's). Written 17 November 2026, after the approach review (doc 26) and its
decisions (GOALS.md, the row of 2026-11-17). Each feature's "as built" is added under it as it lands.

Phase 4 in the roadmap is "the rewrites that sit on the groundwork": doc 02 steps 5 and 6 (combat onto the one ruling) and doc 09
section B (smaller prompts, decide then speak, beats). The owner's decision of 17 November puts the **speech work first**: decide
then speak, the smaller prompt, and the change to f410. This plan gives that part in full (Part A), the combat part in outline
(Part B), and names what is left for a plan of its own (Part C).

**Pillars:** 5 (people who sound like people), 4 (they differ from one another), 2 (the engine decides, the model speaks), 7 (a
turn inside its minute on the smallest card).

## What a spoken reply is today (read 17 November)

A townsperson's reply is one model call, `npc_conversation` (npc/life.py `converse`, npc/prompts.py `conversation_prompt`):

- **The prompt is the largest on the card.** Measured: median 29,155 characters, 95th percentile 36,345 (data/measured
  bundle_d_baseline.yaml); later prose runs put the 95th at 20,500 to 24,300. The owner's target is 14,000 (data/measured
  prompt_ceilings.yaml). It was never met.
- **Everything the person might know is in it:** the facts, the town's news and happenings (the truth view's "townsfolk" profile),
  the guild board, the land, the people they know, their motive marked private, their memories. A rule in the system prompt asks
  the model not to bring up what does not fit. That rule is where the news leak comes from: the model is given the news and told
  to hold it.
- **One answer carries thirteen fields:** the speech, a gesture, and eleven decisions (intent, the facts revealed, trust, names
  told and learned, what to remember, a gift, an offer of work, an offer of a quest, a journal note, a promise heard). The model
  decides and performs in the same breath. The system prompt spends about forty lines on how to fill the fields.
- **The accent (f410)** is one instruction, the same in every reply: "Their Common, in every line and the same each time". On this
  model that reads as the same grammar slip in every sentence.

A hired companion's reply (`hire_chat`) is already narrower: speech, gesture, a memory, an impression, a promise. The engine
gives it a subtext and a feeling. It carries the same accent line. Stiff companion speech was the owner's finding of 16 November
(f714 sends it back once).

The gate's baseline of 17 November, on the real model (docs/measure/2026-11-17_live_gate.md): talk turns take 8.4 s at the
median and 14.1 s at the 95th percentile; 0 of 23 spoken replies were sent back as stiff; the gate does not yet count leaks or
the size of the speaking prompt.

## Part A. The speech work

Six features. Each has its test in tools/sim first, the goals review, and the full suite. Everything new sits behind one switch
in data until A6, as act() did (f603), so the game played today does not change until the measures say it should.

### A1 (f723). The measures this work is judged by

The live gate (f719) gains three measures, taken from counts the game already makes or can make where the call is checked:

1. **The speaking prompt's size:** median and 95th percentile, in characters, for a townsperson's reply and for a companion's.
2. **Leaks:** of the replies in the gate's script, how many say a piece of news, a happening or a board posting that the engine did
   not choose to share in that reply. Counted by the words of the fact, as `reveals` is checked today (npc/life.py:423).
3. **Replies accepted on the first try,** by kind of speaker.

The gate's script gains talk lines that tempt a leak (asking a stranger about something else while the town has news). The
owner reads those lines with the forty already waiting.

Then the gate is run once more: that run is the "before".

**As built (f723, 17 November):**

- **Size and first tries:** nothing new is counted in the game. The run's own call log already holds what each first try read
  and how it ended, and the nights already measure it (tools/latency.py, f475). That measure is now `first_tries(calls, tasks)`,
  for one task or several together, and the gate reads each kind of speaker from it. Which tasks are which kind of speaker is
  data (data/replay/gate.yaml `speakers`: a townsperson is `npc_conversation`, a companion `hire_chat`), checked at startup
  against the budget's tasks, so `npc_decide` and whatever else phase 4 adds is one line of data.
- **Leaks, changed from the plan:** counted by the gate from what was shown, not in the game. Before decide then speak there is no
  "what the engine chose to share" to count against, so a leak is defined by the script: a line that asks about something else
  is marked (`tempts`, naming which of the town's news, happenings and board would be a leak in its reply), and a reply to a
  marked line that carries a piece of them is a leak. "Carries" is the rule a revealed fact is held to (npc/life.py `carries`,
  lifted out of `converse` and shared), with two of the piece's longer words at least. The reply is the first thing said aloud
  in the line's turn, its words alone (no label, gesture or narration around it; the party's talk after it is not the reply). A
  marked line counts only where the town had such a piece to bring up. A row is matched to its line by what was typed. A rough
  count: the report prints each reply it counted, who said it, beside the piece, to be read. The same measure holds before and
  after the switch. Beside it the gate reports how many of all spoken replies carried news or a happening, asked for or not.
- tools/nightrun.py: a scripted run's row keeps what was said aloud in its turn (who, the words alone) and, where something was
  said, what the town had around it as the turn closed: its news, its happenings (not the ordinary day anyone can see) and the
  board's postings by title. That reading changes nothing: the board is the one last posted and is never posted anew by the
  measure (a refresh is the game's, inside a turn, with a model call of its own).
- **Floors** (data/replay/gate.yaml, not set): `leaks`, `townsperson_prompt_p95_chars`, `first_try_share`.
- **The script:** eight lines are marked (the clerk's line about the postings is not: their subjects are often the news; the two camp lines after the fight tempt only news: the happening there is the fight itself). Six were there already; two are new, for the owner's reading with the forty: "I ask
  the smith how long they've had this forge." and "I ask whoever's serving what's in the stew."

### A2 (f724). The engine decides what it can

Before any call, the engine settles what it already knows how to settle, and writes it down as one **decision** for the reply
(a small typed record, kept on the turn's context):

- **The stance** (already rolled: engine/voice_rules.py `roll_stance`).
- **The move:** answer, answer in part, ask back, turn to their own trouble, deflect, joke, go quiet. Weighted by the stance,
  their trust in this character, and their voice kit; never the same move three replies running. Weights in data.
- **What they could share:** the candidate facts for this line, picked by meaning as today (engine/brief.py `lore`, four of
  twelve), now including the town's news, happenings and board, which today are pasted in whole. Each candidate carries whether
  this person would share it with this character: by trust, by whether it is theirs to tell, by the secret gates that exist
  (scenes/arc_actions.py).
- **The slip** (A5).

No model call yet. This step alone changes nothing a player reads; the old prompt is still built from the same things.

### A3 (f725). Decide: a small call for what only reading the line can settle

Some decisions need the player's words read: do they leave, refuse, bargain; which of the candidates answers what was asked; is a
name told or learned; is work or a task offered; was something promised. Today these are fields of the one big answer.

A new task, `npc_decide`: a short prompt (who they are in three lines, the stance, what was said, the last lines of the talk, the
candidates as one line each with an id) and a small typed answer (intent, the ids shared, the offers, the names, the promise).
Expected: a prompt under 6,000 characters and an answer of about 80 tokens.

The engine checks the answer as it checks today's (an id that was not offered is dropped; a gift only of a story object; a
leave only with a parting).

### A4 (f726). Speak: the smaller prompt, given only the decision

The speaking call is given a person first and rules last (doc 09 B5):

- **A persona card:** who they are, what is on their mind now, how they are with this character, how they talk (the voice kit,
  the sayings the engine offers, the slip line of A5).
- **Only what was decided:** the facts chosen in A2 and A3, in full, and the decision in plain words ("You tell them about the
  tracks by the mill, grudgingly. You ask what brings them here."). News that was not chosen is not in the prompt, so it cannot
  leak.
- **What is plainly around them:** the place, the hour and weather, who is here.
- **The last lines of the talk,** the examples of how such talk sounds (f583), and what was said.
- **A short system prompt:** the reply-field rules leave with the fields. What stays is what no code can check.

Its answer is speech and a gesture, nothing else. Target: the 95th percentile at or under 14,000 characters.

Everything the engine does with a reply today (memory, trust, offers recorded, names known, the parting) is done from the
decision, not from the speech. `reveals` are the decided facts whose words the speech carries, as now.

### A5 (f727). The voice in every line; the engine decides when grammar slips (the change to f410)

The owner's decision: a speaker's voice holds in every line (their words, their rhythm, the sayings the engine offers), and the
engine decides, reply by reply, whether a slip of grammar shows, telling the model so in plain words either way.

- engine/voice_profile.py `accent` becomes two things: the **voice line** (always: the manner of the tongue that is not broken
  grammar, such as "counts and measures things exactly", "the important word first") and the **slip** (rolled for each reply from
  the reply's dice: one habit of grammar from their tongue, such as the verb at the end, shown once in this reply, or not at all).
- The model is told which: "In this reply their grammar slips once: ..." or "In this reply their grammar is clean. Their voice
  is in their words and rhythm."
- The odds are data (data/rules/speech.yaml), by how well they speak Common. Proposed: one reply in two for a learner, one in six
  for someone whose Common is good. The owner's numbers.
- data/rules/speech.yaml and quirks.yaml: each tongue's `habits` are split into manner and grammar. This is wording and rules
  both, so the kept recordings are made again, each change listed.
- For townsfolk and companions alike. This feature does not need the switch: it replaces f410 outright, as decided.

### A6 (f728). Companions and the mentor; the measure; the switch

- **Companions:** no decide call is needed (a companion's reply has no facts to gate and no offers). The engine's decision for
  them is the move, the subtext and feeling they already have, and the slip. Their prompt is put in the same order (person first,
  rules last) and measured the same way.
- **The mentor** is left as she is: her replies are checked against her fact sheet by their own path, and she was not a finding.
- **The measure.** The gate is run with the switch off and on. Decide then speak is kept only if all three hold (the bars are the
  owner's; these are proposed):
  1. Leaks: none in the gate's talk lines.
  2. Time: a talk turn's 95th percentile no more than 20% over the "before".
  3. The owner prefers the new replies in a blind reading of twenty pairs, in both orders, at 60% or more (the bar used for the
     thinking decision). The same reading says whether speech reads as a person's or as a machine's (the standing playtest note).
- If kept: the switch is turned on, the kept recordings that hold a talk (stub_short, stub_party) are made again with each change
  listed, and one feature later the old path and the switch are removed. If not kept: the switch stays off, the measures are
  written up, and A5 and the measures of A1 stand on their own.

### What Part A does not do

- **The conversation as real chat turns** (doc 09 B5): the gateway and the recorder carry one system and one user message today.
  Proposed after A is measured, as a change of its own.
- **Signature lines for each person** (B6) and **a want for everyone** (B7): the persona card of A4 has the places for them. Each
  is a feature of its own after A6, with the owner's answer to doc 09's second question (written by the model once a person, or
  partly by hand for anchors and hires).

### Risks

- **Two calls where there was one.** The decide prompt is small and the speak prompt about half of today's, so the total read
  should be smaller; the measure of A6 decides, not the estimate.
- **A 12B model choosing ids.** It chooses ids today (`reveals`), from a longer list. If it chooses badly the engine's candidates
  of A2 can be made the whole decision (no call), which is the fallback the switch allows.
- **Recordings move** at A5 and when the switch turns on. Each by the rebless rule.

## Part B. Combat onto the one ruling (doc 02 steps 5 and 6), in outline

Outside a fight an improvised act is ruled by act() (engine/act.py, f594 to f603). Inside a fight it still goes through the old
list of effects (engine/combat_improv.py, scenes/combat_scene.py:679).

- **B1.** A fight's improvised act is ruled by act(): one ruling, the same odds, its changes applied to the fight. Behind a switch,
  measured on the ruling corpus and a recorded fight.
- **B2.** An attack with an aim (a leg, a weapon hand) through the same ruling.
- **B3.** engine/world_improv.py and engine/combat_improv.py removed; their phrase tables stay in data for the fast path. stub_fight
  made again with a recorded improvisation.

Detailed, with its own questions, when Part A is measured. It touches the fight's reader, which the one reader (doc 26, 5.1) would
also replace; the order between those two is the owner's (question 5).

## Part C. Not in this plan

Beats in place of the ninety hand-written briefs (doc 09 B1), scene memory and callbacks (B2), prose out of JSON (B3), invented
people adopted or sent back (doc 26, 5.2). Each needs the measures of Part A in place first, and B3 needs the owner's answer on
passages released a sentence at a time.

## Order and size

| Feature | What | Needs the real model |
|---|---|---|
| f723 | The gate's speech measures, and the "before" run | yes, one run (about forty minutes) |
| f724 | The engine's decision for a reply | no |
| f725 | The decide call | a short run |
| f726 | The speaking prompt | a short run |
| f727 | The voice and the slip (f410) | a short run |
| f728 | Companions; the measure; the switch | yes, two runs, and the owner's reading |

## Questions for the owner

1. **The move** (answer, ask back, deflect, joke, go quiet): rolled by the engine, or chosen by the decide call? Recommended: the
   engine rolls it. It is cheap, it varies by design, and it is the rule of the game (the engine decides).
2. **The bars of A6:** no leaks; time no more than 20% over; 60% in a blind reading of twenty pairs. Yours to set.
3. **The slip's odds:** one reply in two for a learner, one in six for good Common. Yours to set.
4. **The mentor:** left as she is in Part A. Agreed?
5. **After Part A:** combat onto the one ruling (Part B), or the one reader first? Recommended: the one reader's contained half
   first, since Part B would otherwise rework a reader that is about to be replaced.
6. **The gate's script:** the forty typed lines still wait for your reading (data/replay/gate_script.yaml), and A1 adds a few.
