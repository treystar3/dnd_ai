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

**The "before" (17 November, the whole gate on the real model, 42 lines, the switch not yet built):**

| Measure | Before |
|---|---|
| What a townsperson's reply reads, characters | median 17,750, 95th percentile 19,541 (9 replies; the target is 14,000) |
| What a companion's reply reads, characters | median 8,696, 95th percentile 9,282 (6 replies) |
| Replies accepted on the first try | 15 of 15 |
| Leaks | 0 of 4 marked lines answered |
| A talk turn, seconds | median 7.5, 95th percentile 12.8 (10 lines) |
| Spoken replies sent back as stiff | 0 of 16 |
| Lines read right | 217 of 252 (0.861) |

**What the run showed about the leak count:** the script begins in a town where nothing has happened yet. For its first thirty
lines the town had no news and no happening at all, so the four marked lines that counted had only the board's postings to
leak, and news reached the script only at its second town (line 32 on). As it stands the count cannot fail on news. Before the
measure of A6 the script needs its tempting lines where the town has news (after the road, or after days have passed), and the
report should say of the marked lines how many had news or a happening around them. The lines are the owner's to read.

(Part of f724's tests ran on the same machine's processor while the script was played; the model's time is the card's.)

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

**As built (f724, 17 November):**

- **The switch** is data/rules/reply.yaml `decide_then_speak` (false). Off, nothing below is rolled or kept. On, the decision is
  made for each reply to one character and shown on the debug console; the request for the reply is the one it was.
- **The decision** (engine/reply.py `Decision`): who speaks, to which character, the stance by its key, the move, whether the game
  forced it, and the candidates. It is the line's, a field of the turn's context: a new line has none, and a failed operation
  puts it back. The talk's last moves (no more than the run) are the scene's: put back by a failed operation, gone when the talk
  ends, and in the talk's record in the save once there are any.
- **The stance by its key:** `voice_rules.stance_kind` reads it from the line the talk was told, by the words before its colon
  (each stance's are its own, checked at startup), as the exemplar pool read it before; a talk kept in an old save needs nothing
  new.
- **The move:** seven moves and their weights in reply.yaml, bent by the stance, by trust (under 35, from 65) and by the voice
  kit's habits (one who never asks back never makes that move). Turning to their own trouble needs a concern. At most two the
  same running. When one of the lines they are given says, in the game's own words, what they must say in this reply (a check's
  result, work handed in, a secret's gate opened or shaken) the move is to answer; what the turn has settled so far, which they
  may only not speak against, forces nothing. Rolled on a die of its own (`move`, by the speaker and the reply's place in the
  talk), so no other draw moves. **The numbers are a first proposal and are the owner's.**
- **What they could share:** the truth's news, happenings and postings now carry ids (`news:`, `happening:`, `board:`); the
  ordinary day, "nothing is posted" and what the player holds are no pieces. `brief.lore` ranks the lore in the call it was, so
  the lore picked is the lore picked without the town; the pieces that share a word with the line are ranked in a call of their
  own, and at most `town_pieces` (2, brief.yaml) come with the lore. A facet the line asks for comes in whole: the board as
  before (it is in the view only then), the news and happenings when the line has one of the new `asked.news` words. Nothing
  comes in twice: a piece in the very words of lore they hold is left out.
- **Whether they would:** reply.yaml `share`, by kind. News needs trust at or over the line under which a person's examples are
  refusals (voice.yaml `refusal_trust`, 30); lore, a clue, a happening in the street and a posting are for anyone; a secret is
  theirs to tell only while its gate is open, and while it is shut nothing of it is written down (the owner's rule of f486). The
  gate is the secret's rule alone (checked at startup).
- **What it costs with the switch on:** no call to the speaking model. Where a piece of the town's shares a word with the line,
  the helper model that ranks the lore reads those pieces too (at most twelve short texts, on the turn's budget like the lore).
- **The words that ask for the news** (brief.yaml `asked.news`) are few on purpose: news, rumour, gossip, tidings, happening,
  lately, afoot. "Did you hear me?" and "What happened to your arm?" do not ask for the town's news. A line that asks in other
  words still gets the pieces that bear on it.
- **A piece's id is its place in today's window** (`news:0`), good for the one reply it is decided in. It is not the piece's
  identity: nothing may keep it to remember what was said (A4 keeps the words, as `reveals` does).
- **A line with two replies** keeps the last one's decision.
- **Not yet:** a reply to several characters at once (f487) has no decision; A4 gives it one.
- **The kept recordings** were made again: every input replayed the same; only the rules' hash moved (a new rules file, two new
  entries in brief.yaml).

### A3 (f725). Decide: a small call for what only reading the line can settle

Some decisions need the player's words read: do they leave, refuse, bargain; which of the candidates answers what was asked; is a
name told or learned; is work or a task offered; was something promised. Today these are fields of the one big answer.

A new task, `npc_decide`: a short prompt (who they are in three lines, the stance, what was said, the last lines of the talk, the
candidates as one line each with an id) and a small typed answer (intent, the ids shared, the offers, the names, the promise).
Expected: a prompt under 6,000 characters and an answer of about 80 tokens.

The engine checks the answer as it checks today's (an id that was not offered is dropped; a gift only of a story object; a
leave only with a parting).

**As built (f725, 17 November):**

- **The task** is `npc_decide` (npc/life.py `decide`), asked once before the reply when the switch is on, outside the talk's
  transaction like the reply itself. Registered where every task is (budget.yaml, required, 80 answer tokens as a first estimate;
  audit_log.yaml; not read as prose by the guard).
- **The answer** (llm/contracts.py `NPCDecision`): the intent, the ids told, a nudge to trust, the names given and learned, what
  to keep of it, a gift, paid work, a request, and what was promised them (asked for only when the line may promise something,
  as today). No words of theirs. The contract is made for each call: the server's grammar lets `shares` name only the ids
  offered and no more than the move allows; where nothing is offered, or the move tells nothing, the answer has no place for an
  id at all.
- **More in the answer than the plan listed:** the trust nudge and the line to remember. With them, everything the one commit
  path takes of a reply (`NPCAnswer`, npc/life.py `apply_answer`) comes from the reading, so A4 can commit from the decision
  alone. The journal note, when one is due, is not in the reading; A4 places it.
- **What a move lets them tell** is data (reply.yaml `moves.kinds.<move>.most`): an answer up to four things, a part or a
  question back one, turning it aside, a joke or a word or two none. With a move that tells nothing the request does not show
  what they know at all. **The owner's numbers; a first proposal.** Each move also has its words as the model is told them
  (`says`) and the intent the reply comes to when the reading fails (`intent`).
- **The engine's checks** (engine/reply.py `take`): an id not offered is dropped, as is one over what the move allows; a secret
  whose gate the game opened is told whatever was read, over and above the move; a gift only of a named story object and never
  while bargaining (the one rule, `reply.gift`, which the scene now uses for a reply's gift too); paid work and a request never
  together; an offer of nothing is none. What was taken out is on the debug line.
- **Not checked here:** "a leave only with a parting" needs the words, so it stays where the speech is checked and comes with A4.
- **When the reading fails** (`fallback`): the engine's candidates are the whole decision. They tell what was picked for the
  line, in its order, as far as the move allows; the reply comes to the move's intent; nothing is offered, given or learned.
  They speak all the same, and the line is not counted as broken.
- **The request** (npc/prompts.py `decide_request`, `DECIDE_SYSTEM`): who they are in three lines, how they know and trust the
  one in front of them, the stance, the move in plain words, the game's lines that bear on what they do, what they could tell
  (one line an id), the talk's last four lines, what was said. In the stand-in's town it comes to about 4,000 characters (2,400
  of rules, 1,600 of request). Its size on the real model is for the gate.
- **Which lines bear on what they do** is said where the lines are made (scenes/world.py `npc_context_parts`): how they stand
  with this character, what they want and have asked, how they have been. What they know (the guild's rules, their faith, the
  season, the places around, the index of their lore) is for the speech alone.
- **With the switch on at this step** the reading is made and kept on the decision, and the reply is still asked for and acted
  on as before: two calls, the second as large as ever. That is a state for building, not for play; A4 makes the second small.
- **For A4, before the reply acts on the reading:** it is not yet given what they sell (it may choose to bargain without
  their prices) or what they remember of this character (it nudges trust and writes what to keep without them); the guard does
  not read its `remember` for words in another script, which matters once that line is kept; and the reply's old rules for
  these fields stand beside the reading's until the old path goes.
- **The gate** does not yet show the reading's size on its own row; A6 adds it with the measure.
- **The kept recordings** were made again: every input replayed the same; only the rules' hash moved.

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

**As built (f726, 17 November):**

- **With the switch on a townsperson is asked twice:** the reading (A3), then the words (npc/life.py `speak`), under the same
  task as before (`npc_conversation`) with a new contract, `NPCSpeech`: speech and a gesture, held to every check a reply's
  speech was. The old whole reply is not asked for. With the switch off nothing changes: the kept recordings replay with no
  request different.
- **The request for the words** (npc/prompts.py `speak_prompt`), in this order: who they are; how they know and trust the one
  in front of them and what they remember of them; how they are for this talk and how they talk; the hour, then the truth's view
  of the place and who is here (said once: the old request gave the place's lines twice), the people they know and the places
  near; what they sell and what else is theirs to know; what they said lately, the talk's last lines, the examples; what was
  said; and last **what they do in this reply** (the move's words, then what the reading settled, engine/reply.py `words`) and
  **what they tell** (the decided things in full, no ids, `told`).
- **What is not in it:** the lore they could have told and did not; the town's news, happenings and postings that were not
  decided (the truth view leaves a piece out of one reply by its id, engine/truth.py `View.hide`; the ordinary day and "nothing
  is posted" stay); the line naming what else they know; the rule for the journal note; every rule for a field; and the rows of
  their memory that are things they hold to tell (a clue of a matter, a fact they overheard) or are about another character.
- **Their memory, by whom it is about** (engine/memory.py `of`, `lived`): the words get what they remember of the character in
  front of them, by id, and beside it up to four things of their own days that are about no one (reply.yaml `speak.lived`). The
  old request gave every row under "your memories of them", whoever it was about; with the switch off it still does.
- **A posting stays on the board.** When the line asks about the board, every posting is in the request whether or not one was
  decided: it hangs where anyone reads it. Postings are still among what the reading may choose, so one can be named twice.
- **One who lies** tells none of what is so, and the rules for speaking now say what a lie is: the one case where they answer
  with something false as if it were true, small and ordinary, naming no new person or place.
- **The rules** (`SPEAK_SYSTEM`) are 6,587 characters against the reply's 8,857. What stayed is what no code checks (what they
  may know and invent, how speech sounds, the shared style and world rules, which are 3,650 of it).
- **The decision in plain words** is data (reply.yaml `intents`, `tells`): each intent's words, and how a name given, a thing
  handed over, paid work and a request are told. Checked at startup.
- **The engine acts from the decision** through the one commit path (`apply_answer`): trust, the meeting, the name they were
  given, what to remember, the promise. What the player learned is the decided lore and clues whose words the speech carries. A
  piece of the town's is never kept by its id. Their own name is known when the speech has it, whatever the reading said (a
  name beginning with a title is matched by its first word only). A leaving still needs a parting in the words (the scene's
  check, unchanged). **Not held to the words:** a thing handed over, paid work, a request, the trust step and the line to
  remember are committed from the decision whether or not the speech speaks of them, as the old reply's were from its fields.
- **Paid work is the engine's figures before they speak of it:** the rule that holds an offer to honest wages is now one function
  (scenes/work_actions.py `settled`), used when the reading is taken and when the offer is recorded, so what they say is what is
  recorded. A request the game cannot track is still spoken and then dropped, as before (settling it first would build a
  place's roster inside the reply).
- **More checks on the reading** (engine/reply.py `take`): one who lies tells none of what is so; what the game decided they
  tell is told truly (a reading that would lie, keep it back or refuse comes to a sharing).
- **The reading is now given** what they remember of this character, by id (the latest four, reply.yaml `decide.memories`), and
  what they sell, and writes the journal note when one is due (asked for only then; the budget's 80 answer tokens for the
  reading were set before the note and are to be measured in A6). The guard reads it now that its lines are kept.
- **Their own work is answered: not in this step.** With the move rolled by the engine, a clerk asked about the board, or a
  seller asked a price, can roll a move that turns it aside. A rule for that was built with this step and taken out again on
  review: it is not in the plan and it changes the move rules of A2, so it is a proposal of its own (A4b, below), waiting on
  the owner.
- **A clue is never forced.** Under a move that tells nothing (a joke, a word or two, turning it aside) a clue they hold is not
  told, and the player asks again. A6's measure is where to see whether that slows a matter.
- **The examples follow the decision:** the sound of gossip is drawn only when news is told (before: whenever the town had news).
- **A reply to several characters at once** is not called by the scene today (only by tools/live_check.py); it keeps the old
  contract and has no decision. When the scene gains that path it takes one of these per speaker (brief.yaml `flat_each`).
- **Size, estimated, not measured.** Rebuilding the nine townsperson requests of the 17 November gate run by arithmetic
  (the new rules, less the place's second copy, the index line, the note's rule and the promise's; plus the decision's lines):
  median about 14,200 to 14,600 characters (was 17,750), 95th about 15,900 to 16,300 (was 19,541). **The target of 14,000 at
  the 95th is missed by about 2,000 on this estimate.** The reading adds about 4,300, so what is read for one reply, in all,
  goes up from about 17,750 characters to about 18,500 to 18,900, not down (the reading's answer is short, so the time may
  still fall; only A6 can say). What is still large and could be given
  only when the line bears on it, each a change of its own: the town's list when asked (1,500), the faith paragraph (750),
  the people they know (400 to 700), a seller's wares (300 to 650), and for guild folk the guild's rules (2,500). A6 measures
  size and time on the real model; whether these are needed is decided there.
- **The kept recordings** were made again: every input replayed the same, no request different; only the rules' hash moved.

### A4b. Their own work is answered (a proposal, not in the plan as approved; not built; waiting on the owner)

With the move rolled by the engine, someone asked for the very thing they are there for can roll a move that turns it aside: the
seller and a price, the clerk and the board. Two moves in the table do that (turn it aside; turn to their own trouble), about
one reply in six at the first weights.

- **Proposed:** the reading of the line (A3) gains one yes or no, `own_work`: what was said asks about this person's own work
  (what they sell and its price, the task or post they hold, how their trade is done). The engine does the rest: each move in
  reply.yaml says whether it turns away from what was asked (`away`), and when the reading says yes under such a move, the move
  becomes the forced one (answer). A joke or a word or two is still theirs to make; an intent alone lifts nothing; a failed
  reading lifts nothing.
- **Why the reading and not a list of words:** the first version (in f726's first draft) asked engine/brief.py whether the line
  had one of a role's words in it. Those lists are loose on purpose (they bring a facet into the brief), and the review found
  that as a rule for the move they would make every innkeeper answer any line with "where" or "room" in it. The reading reads
  the line already.
- **Size:** engine/reply.py, llm/contracts.py, npc/prompts.py, reply.yaml, a test. It changes nothing with the switch off.
- **If struck:** the measure of A6 will show how often it happens and how it reads; the weights of the two moves are the other
  way to make it rarer.

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

**As built (f727, 17 November):**

- **The data.** Each tongue's `habits` became two things (quirks.yaml: rime, sunscar, salt; speech.yaml: ironvein, eldervale,
  hrimgard, cinderhold): `manner`, how their Common sounds in every reply and never broken grammar, and `slips`, the slips of
  grammar that tongue gives (a list; Eldervale and Cinderhold have none). The split is a first proposal and the owner's to
  reword, like the rest of that file: what counted as a slip was the verb at the end and a joining word left out (Ironvein,
  which has two), a small word left out (Rime, Hrimgard), the wrong joining word (Sunscar), and a word reached for and
  described around (Salt). Two of these are judgement calls for the owner: Hrimgard's "rarely bothers with words for small
  things" was read as dropping small words, and could have meant not speaking of small matters; Salt's reaching for a word is
  a slip of vocabulary, not grammar, and was in every reply before, where now it comes one reply in two or six.
- **The voice line** (engine/voice_profile.py `manner`): as f410's line was, with the manner only. In every reply.
- **The slip** (`slip`): rolled for each reply on a die of its own (keyed by who they are and how many lines they have said, so
  no other roll moves): one reply in two for a learner, one in six for one whose Common is good (speech.yaml `slip.one_in`, the
  owner's numbers). The model is told which in plain words either way (`slip.shown`, `slip.clean`, data): "their Common slips
  once, in one sentence and no other", or "their Common is clean" (Common and not grammar, so the line is true of every kind
  of slip). A tongue with no slips has none rolled and nothing said of it; with more than one, the die picks which. Someone
  raised on Common is told nothing of either, as before.
- **Where:** a townsperson's reply and parting (`resident_lines`), with the switch on or off; a companion's reply and the
  party's talk among themselves (scenes/banter_actions.py). Where everything about a companion is given at once and no reply is
  being made, the manner is there and nothing is rolled. The mentor is untouched (her voice is written by hand).
- **The check** (engine/data_check.py `voice_problems`): a manner and a list of slips for every tongue, behaviour with no
  quoted words, `habits` refused; the odds whole numbers from 1; the two lines.
- **The kept recordings:** stub_short and stub_fight replayed with no request different. stub_party has two companions with a
  tongue of their own (Rime, Salt): three requests changed (two companion replies and one exchange), each only in that
  companion's line of habits becoming their manner and this reply's line on their Common (clean in four, slipped in one). No
  outcome and no shown word changed: the stand-in model answers the same.
- **Not measured here:** whether the real model now slips once and not everywhere. That is read in A6's blind pairs and in the
  next playtest (the standing note on whether speech reads as a person's).

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
| (none yet) | Their own work is answered (A4b: proposed on review of f726; the owner's to approve or strike) | no |

## Questions for the owner

1. **The move** (answer, ask back, deflect, joke, go quiet): rolled by the engine, or chosen by the decide call? Recommended: the
   engine rolls it. It is cheap, it varies by design, and it is the rule of the game (the engine decides).
2. **The bars of A6:** no leaks; time no more than 20% over; 60% in a blind reading of twenty pairs. Yours to set.
3. **The slip's odds:** one reply in two for a learner, one in six for good Common. Yours to set.
4. **The mentor:** left as she is in Part A. Agreed?
5. **After Part A:** combat onto the one ruling (Part B), or the one reader first? Recommended: the one reader's contained half
   first, since Part B would otherwise rework a reader that is about to be replaced.
6. **The gate's script:** the forty typed lines still wait for your reading (data/replay/gate_script.yaml), and A1 adds a few.
