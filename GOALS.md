# Meravia: goals

This is what every change to the game is held to. Read it before building anything, and check the change against it before calling it
done (the checklist is at the end). It grows: when the owner decides something about what the game should be, it goes in here, in the
owner's words where there are any. Quoted lines are the owner's own (spelling tidied); the rest is drawn from the owner's feedback and
is open to correction.

## The goal

> The goal for this project is to be a sandbox rpg where the world feels alive and responsive to the player. No two runs through this
> game should feel the same and the systems should allow the player to play and interact with the world however they want in a fun and
> meaningful way.

> I want the world to feel alive and like something that can be explored and meaningfully interacted with. Right now they feel like
> stages in a play, there is what you can see but everything behind them is a facade not somewhere you can really go and do things at.

## The pillars

### 1. A world that is real, not a stage set

What the player is shown is somewhere they can go and something they can use. The world reacts to what the player does and keeps
moving when they are not looking.

- Anything the narration names (a cave mouth, a glowing pool, a back room) can be gone into, examined and acted on, or the game says
  plainly why not. Nothing is described that the game cannot back up.
- What the player does leaves marks: people remember it, news travels, towns change, and later scenes show it.
- The world changes on its own between visits (the pulse, threads, people's lives), and the player can find out what happened.
- Prose and game state agree. If the story says something was taken, killed, paid or found, the game says so too, and the other way
  round.

How we check: the night-run Consistency counts (facades, dead ends, prose that contradicts the engine) and the blind readings.

### 2. The game is a dungeon master

> The game should play to its strengths which is that it is an AI narrated game so it can create things just like a real life DND
> dungeonmaster would. If the Dungeon master hears a player narrate something and it makes sense, they react and therefore so does the
> game. ... For example investigating further into a cave should be accommodated for but not I grow wings and fly away.

- The player can try anything. What makes sense in the fiction is accommodated, and the world grows to hold it. What does not is
  refused in the world's own voice, never with a parser error.
- Impossible actions are refused, and never granted and then forgotten.
- Campaigns and pulse quests are open: "Campaigns and pulse quests like this should be open ended to how a player tackles them."
- A line the game fails to act on is a bug. It is logged, counted and fixed.

How we check: the ruling corpus and its evaluation, the refusals log, the night's "made room / said no" counts, and the blind readers'
notes on swallowed actions.

### 3. No two runs alike

- Seeds, generated places, people, threads, items and abilities make each run different.
- Moments the model writes are not repeated within a playthrough. "I don't want the random dancing to feel scripted."
- A line the game prints often is written as many lines, or handed to the narrator to tell in its own words. It is never stamped out
  the same way each time.
- An agreed exception: Maren's tutorial may be the same every run, because it can be skipped.

How we check: tools/world_divergence.py, the prose analysis (reused phrasing, repeated sentences, shared openings), and the blind readers'
repetition counts.

### 4. People who feel like people

- Everyone sounds like themselves. "Not everyone needs to be super memorable but they should still sound different enough even if
  mundane."
- Eccentric, never obnoxious. "Eccentric people often just are a little weird but it's in a more passive manner, they just are who they
  are. Weird and obnoxious can be those that make it an active show of how weird they are." The owner's touchstones are Final Fantasy's
  oddballs, such as Cait Sith and Kefka.
- A voice holds from line to line: an accent in every reply, the same name, pronoun, people and weapon every time.
- The party plays like a table: "similar to how a dnd campaign would feel in person where the party is all doing the same thing
  together." Companions remember what happened, including the ones who died, and talk about it.
- People answer what was said to them, and a short exchange stays short.

How we check: the blind readers' notes on voices and identity drift, voice tests, and live checks of dialogue.

### 5. Writing a reader wants to keep reading

The prose is judged "through the lens of an expert writer especially someone with a high understanding of fantasy like Tolkien". It
should feel natural, never "unnatural and ai".

- No dashes in the story. This is the owner's one exception to leaving the narrator's style alone. The game's own italic notes may
  keep theirs.
- No length limits on the narrator or the speakers. "Remove all restrictions from the llm narrator and npc responses that have to do
  with length." A passage is long or short by what it holds.
- Nothing stamps out the same paragraph shape every time (fight rounds, after-fight passages, monster entrances).
- Nothing jarring or sudden. Travel is narrated, and a road event comes in the middle of a journey, not out of nowhere. A road event
  where something noteworthy happens stops the walk there, so the player can act on it.
- No machinery in the story: no JSON, ids, notes, checklists, foreign words or broken text ever reaches the page.

How we check: the prose analysis by task, and the blind readings.

### 6. Fun, deep, fair play

- Systems have depth and room to grow. Spells, for example: flat cost and power, stronger versions later, names the model writes for
  each rank, rank-ups from books and teachers, and named spells as boss, dungeon and quest rewards.
- What the player sees in a stat, a cost or a choice makes sense for the character they built.
- Balance is tuned after the architecture is right. "We can do balance adjustments later as needed."

### 7. Easy and comfortable to play

- "I want readability to be easy."
- Nothing on screen jumps, flickers or vanishes while the player is reading. What just happened stays to be looked back on, such as the
  last fight's log.
- Details are one hover away, as in the character pane.
- Menus are plain: Continue, Load, New Game, Settings, Quit.

## How it is built

> Keep in mind an added goal of infrastructure that this game is built on should be scalable and easily modifiable. Nothing should
> bloat to extreme levels on a long campaign and changes and additions made later to systems should be easy.

> Let the architecture be made in a way that it can be expanded upon easily as the development cycle continues.

- **Infrastructure over patches.** Fix the system that let a problem happen, not the single instance: "I'd want to create a robust
  infrastructure that can handle a sandbox rpg environment", and "more infrastructure enhancements instead of more rules to give the
  narrator".
- **The engine decides; the model names, describes and speaks.** Every number, rule and state change is the engine's. What the model
  writes is checked before the player sees it.
- **Data is the source of truth.** Tunable numbers and content live in data/ (YAML) and are validated at startup (engine/data_check.py).
- **Nothing grows without bound over a long campaign.** Every store has a cap or a window, and every cost per turn stays flat as the save
  ages.
- **Every change is tested.** Every change gets a test in tools/sim and the full suite (tools/run_suite.py) passes before it is pushed.
  Night runs and blind readings measure what tests cannot.

## Checking a change

Before building, and again before calling it done:

1. Which pillar does this serve? Say so in the commit.
2. Does it leave a facade, something shown that cannot be used, or prose the game state does not back?
3. Does it add a line the player will see over and over in the same words?
4. Is it a rule for the narrator where infrastructure would do the job?
5. Will it bloat on a long campaign? Is it easy to extend later, with its numbers in data?
6. Does it keep identities straight: names, pronouns and voices?
7. Is it tested, and does the full suite pass?
8. Does it assume there is only ever one player, where a character's id would do? Multiplayer is a goal (owner's decision below): a
   store, a prompt or a view of the world that can only ever hold one player will have to be built twice.

If a request seems to pull against a goal here, raise it with the owner before building. If the owner decides, record the decision
below.

## Owner's decisions

Newest first. Each is a call the owner made about what the game should be; follow it unless the owner changes it.

| Decision | Feature |
| --- | --- |
| How the game ships without Ollama, the owner choosing on 2026-11-05: "go with option 2", and for the code behind it, "let's go with the neutral". The game ships llama.cpp's `llama-server` in its own folder, started and stopped by the game itself, with the model files in a Steam depot of their own, so Steam installs the model with the game and there is no separate download. Chosen as the option with the best gameplay experience that keeps model calls on each player's own card; a hosted model stays out. The game reaches the model through an interface of its own (chat, embed, load, close, in the game's terms, not Ollama's), with the llama-server adapter behind it. A private copy of Ollama, the model inside the game's process, another engine and a hosted model were weighed and set aside (the rebuild plan's Steam without Ollama tab holds them). | (rebuild: the runtime bundle) |
| Bundle E's design questions, the owner taking the recommendations on 2026-11-04: "Go with your recommendation" (the rebuild plan's Bundle E design tab holds them in full). A third recording of play is kept beside the two, covering a won fight, its finds, a hire who dies mid-round and calls that fail. What the narrator has already described in a fight is saved with the fight, so a reloaded fight tells as one unbroken run. A fight the player started begins even when its opening cannot be written, and a plain line stands in. The opening is its own kind of call, priced as the narrator's passage. A won fight lists its finds before it is told, and Victory after. Venom that spreads is stopped by what would stop a fresh poisoning, and carries what it carries today. Triggers no rule reads are set aside, not deleted. The fixtures' coverage decides their number, about sixty to start. The night's recordings from before the change stop replaying exactly and serve as material. The fighter is built of parts, each holding its own fields. The blow's chain of multipliers is named in data and tested in order, left as code for the balance pass. The odds' simulations are measured on the card before any number changes. The two sets of lines a player reads when a fight cannot be told or is let go are the owner's to read first. | f493-f510 |
| Bundle E (combat onto the executor, then Stage 8), the owner taking the survey's recommendations on its thirteen questions on 2026-11-04: "go with your recommendations" (the rebuild plan's Bundle E survey tab holds them in full). Today's damage order is kept exactly and recorded as data; no balance number changes, but the four known divergences (hexed without a status row, Mend leaving bleeding's strength, venom spread skipping resist, stale status_from) are fixed as named bugs. Effect instances live on the saved fight, consistent across a reload. The fight's serial is set at construction and the odds simulation leaves no trace. No fight die is seeded by what was logged. Code-held fight numbers wait for the balance pass. Every model call of a fight is made outside a transaction; loot is named after the win commits. A fight saved mid-round is discarded by the migration. The fighter and the fight hold several player fighters in shape only. Fixtures of today's fights are recorded before the rewrite. The pane shows a round only once it stands. A fight born in the world's own operation tells its opening after its own commit. | f493- |
| Quests have no time limit: "let's get rid of quest time restrictions." A contract from the board, a personal request and an arc's contract stay in hand until they are done, handed in or given up. None is forfeit by the clock, and nothing tells time left. Decided 2026-11-03. | f491 |
| Bundle D's further questions, the owner taking the recommendations on 2026-11-03: "go with your recommendations" (the rebuild plan's Bundle D design tab holds them in full). A standing offer of work is withdrawn when the person's working day ends, the character leaves the town, or they offer other work; never by an hour count. A request is refused when the character says no, or when a new conversation with that person opens without it being taken; it is then released with a reason. A hire's own commitment is kept when a later reading says it is done, and released if the hire leaves or dies or the hirer lets it go; never by age or count. Past six, a new one is kept only as the hire's word. A bystander keeps the names and facts said aloud. People present at a moment keep it as their own memory. When a hire's settled past is full, a new claim waits unsettled and none is dropped. Deeds are recalled by a name learned later, for memories from Bundle D on. Memory caps start near 150 rows for a townsperson and 80 for a hire, tuned from the first night. Routines are drawn over the written world's places; newcomers to added places wait for Stage 4. The second recorded test session (stub_party) is kept in the repository. Short frames come from data only when a line has none or its frame failed. | f476-f490 |
| Bundle D (the rebuild's speaker briefs and memory), the owner taking the recommendations on its sixteen questions on 2026-11-03 (the rebuild plan's Bundle D design brief holds them in full). What townsfolk say they remember is kept as their claim, typed by the engine, never as fact. Obligations never lapse by age: an offer ends with a reason the person can give, and a refused request is released. A death is kept with a state, so the fallen are remembered past sixty days. News and rumour carry where they came from and how sure they are. Companions know the player's deeds only by being there or being told. Someone may hold a secret without knowing it until its gate opens. People reckon time from now and by seasons ("three days ago", "early this spring"), never by day numbers, with no named calendar for now. A person's habits, once settled, stay when a town gains a place. A town keeps the detail of what a player settled for a month, then a lasting mark. A promise made in words is remembered as a claim by the one it was made to; the engine judges only the obligations it makes. A change in someone's nature is kept as something that happened to them, not by rewriting who they are. A name heard in town talk is hearsay, usable but not as if introduced. With these: Maren is inside the rewrite; every call uses one context size, with prompt ceilings measured first; old saves are migrated with the least work; the sampling boosts stay out of Bundle D. Working decisions. | |
| A townsperson's view of each character is kept separate: "Let's keep them separate for now." How someone regards one character does not colour how they treat the people travelling with that character. A working decision, decided 2026-11-03. | |
| Multiplayer parties. No fixed cap on players: "I think the multiplayer goal shouldn't be capped at 4 players", and "let's try to keep it possible for more than 4 humans to be in a party together." When players travel together, "each player gets to bring along 1 companion of their choosing until there are 3 humans in the same party"; at three humans or more, "we can drop it to none for now." The companions not brought go on errands: they stay in their own player's party, and the pane shows where they are (review Q19). "Companions should belong to the player that hires them and return on visit to the next town": when the players split, each player's companions rejoin them at the next town that player visits. Working decisions, decided 2026-11-03. | |
| Multiplayer is a goal to build eventually: "multiplayer should be a goal to eventually implement and design decisions made now should keep that in mind for the future." Players share one campaign and can split up and reunite in it. "Model calls will run on each player's card individually": each player's own card serves the model calls for that player, as a single player's does today. Group narration: "it should be shared third person narration"; a player playing alone is still told as "you". How time works when players separate is open until it is researched (see Open questions). These are working decisions: "these aren't concrete and if changes are needed they can be while the game is in development." Decided 2026-11-03. | |
| The longest turn finishes within 60 seconds of model time on the RTX 3060 12 GB: the typed line's required calls (understanding, the outcome, its passage, and the embed calls those need), from the line typed to the last required line shown. One-time loads belong to a warm-up at the home page; background work and the window's pane re-runs are not counted. The budget is not raised; it is revisited only after a recorded night is re-timed on a real 3060 and the required path alone, with optional calls deferred and smaller prompts, still breaches the minute. The owner took this as a recommendation on 2026-11-02, with the Bundle C decisions below. | f459 |
| Bundle C (the rebuild's Stage 3), the owner taking the survey's and the design's recommendations on 2026-11-02 (the rebuild plan's Bundle C tabs hold them in full): each action of a typed line is its own operation, committed apart (a transfer and its payment together; the world's own work, the pulse and arrivals and the law, apart from the player's and able to fail apart; a partly committed line typed again is a new input). A committed action is never undone because its narration failed: the player reads a plain line telling what stood, from many lines in data, and a partly committed line is told as part of it stood. A question asked inside a turn ends the operation; its answer is the next typed line, Maren's tutorial included. Past the budget an optional call is deferred to a later turn, never to a thread, or dropped with its fallback; a required call still running is given a deadline from what is left, never an instruction to be brief; a crash between commit and display is told once on the next load, from data. What has been shown is not state. Measurements live outside the data hash and the budget's tunables in data/rules/budget.yaml; the record keeps a capped window. This narrows the f449 row's "rolled back whole" from the turn to the operation. | f459 |
| A turn the game cannot take leaves nothing behind and never ends the game. Whatever fails inside a turn, the model or the game itself, the turn is rolled back whole (the world's additions, the record and the caches come back as they were, with Bundle B), the player is told in the narrator's words, and the fault is written to logs/crash.log so it still surfaces. The same line failing twice running on the game's own fault is told to be left. The owner took these as recommendations on 2026-11-02 (with the four Bundle B decisions kept in the rebuild plan: the session is born when the save opens; the campaign world presents the map only in Bundle B; a simlib helper lands first). | f449 |
| How to get past a road hazard is never named in advance: "let's have the model stop naming checks", for road hazards only (the owner's choice of scope; rulings on what the player tries, and the reading of the player's line, still name the check an act takes). A hazard is what it is and how hard. The player decides how to get past it (review Q2), and whatever they do, pressing straight on included, is ruled in the moment like any other attempt. | f447 |
| The world is bigger than what is written: "Your game needs to accommodate plausible actions beyond authored content" and "the player's request should create an opportunity for adjudication, not an automatic entitlement to whatever they ask for." Meant broadly, not for any one example: "think of the broad picture of what the goal is trying to achieve." A plausible request (a person, a place, a thing, a service, a piece of news, a tie to someone's past) is a question put to the world. The engine rules on it from what is already true: yes, yes at a cost, not here but somewhere else, or no. The ruling is kept, a no included, so asking again never re-rolls it. The model writes the particulars inside the ruling. What is made is real (it works with the game's mechanics and stays), never a facade. The player's skill, time and coin decide how they find out, never what is there. It is bounded, and what is never visited fades. | rebuild plan, Stage 4 |
| The machine the game is built for: "Let's assume a minimum of a gtx 3060 to play this game with a maximum of a 1 minute for the longest turn." Read as the 12 GB RTX 3060 until the owner says otherwise (the 8 GB card cannot hold gemma4:12b with its context). Every turn, the longest included, finishes within 60 seconds on that card. | Gemma review |
| Pre-alpha: "we are in pre alpha so major reconstructions of the game should be done now rather than later if it helps serve the game overall". A rebuild that serves the goals is not put off to avoid churn; it is still built in tested steps, with the full suite passing before each push. | infrastructure review |
| Road events, Q2 in full ("You've read it correctly"): what stops the walk is anything the player could act on (a person met, someone in need, an ambush, a hazard, a find); a passing sight is told inside the walk. Nothing is settled for the player. A find: "it should narrate a scene and let the player pick up items they find if they choose". Hazards: "stop the player to decide how to get past". "Walking past someone in need should get a hire reaction either positive or negative" | f427 |
| A new game's start: "Leave the start to chance." | review Q1 |
| Road events: "road events should stop, all road events that something noteworthy happens should be a stop for the player"; a passing sight is not one: "no passing sights shouldn't stop" | review Q2 |
| Things that settle a matter: "have key items turn in be handed off but have a separate category for keepsakes which the player keeps" | review Q3 |
| Part pay for a late or ended contract: "Leave for balancing." | review Q4 |
| Flaws told only inside a passage, so they fire less: "Accept that it fires less." | review Q5 |
| A teaching hint (the skinning note): "Once per save per kind." | review Q6 |
| Companions and dithering: "They aren't explicitly told to react to dithering." | review Q7 |
| Nudging idle or looping play: "Nothing for now." | review Q8 |
| Fight prose: "Every blow stays in the prose." | review Q9 |
| Damage markers: "Rely on engine alignment alone for now and see if we can come up with a more elegant solution for consistency." | review Q10 |
| Encounters and XP scaled to the party: "We will come back to this in the balance phase." | review Q11 |
| Beasts far outmatched by the party: "far outmatched beasts should have a far smaller chance of attacking" | review Q12 |
| The kill XP curve and contract XP: "Leave for balance pass." | review Q13 |
| Bad-weather and storm rules apply only under open sky: "yes only under open sky" | review Q14 |
| Road stops and dungeon mouths for the rules of settlements: "they shouldn't count as settled. If a road stop is sufficiently populated it may" | review Q15 |
| The "Roads leave..." lines: "roads leave lines should come from map.yaml" | review Q16 |
| A far place named only in part: "For major cities they need to say it exactly but for places off a road or locations it can ask."; major cities are "places the map types as a city or major town" | review Q17 |
| Place names the narrator or a townsperson coins: "They should be walkable aliases." | review Q18 |
| A companion on an errand: "They do actually leave but still count as being in your party. They can be gone but the party pane still shows where they are and what they're doing if they're not with you." | review Q19 |
| Companions keeping gifts or coin: "Memory only for now but maybe return to this." | review Q20 |
| Dropping the "questions" voice quirk for saved hires: "Accept it." | review Q21 |
| Who joins a party exchange: "ideally it would depend on if the companions all have something to say. It shouldn't come off as a roll call but a real conversation" | review Q22 |
| Figure-of-speech habits against the f409 style rules: "Drop these habits for now." | review Q23 |
| Townsfolk get histories of their own: "npc's shouldn't feel like they were just spawned in they should feel like characters with a real backstory and history" | review Q24 |
| Old saves with wrong-gender profiles: "Whatever is the least work, don't worry about old saves for now." | review Q25 |
| People a companion's request is about: "Improvised people should be able to become real people if a narrative calls for it." | review Q26 |
| Foes yielding: "Foes anywhere can yield but they need a sufficiently high intelligence score to yield." | review Q27 |
| A bounty taken alive counts: "at hand over" | review Q28 |
| Ransoming captives: "remove that state and for now have it just raise reputation in the place you turned the captive over to" | review Q29 |
| An escaped captive coming back with a grudge: "It should be possible" | review Q30 |
| The cap of deeds in one line: "Raise the cap but keep an upper limit for a clear runaway case. Maybe a limit of 15 or 99."; the limit: "15 works for now" | review Q31 |
| Summoning, whether the engine knows what each summoner may call: "The engine should know" | review Q32 |
| A sensible improvised act can yield a real item: "this should be possible to create a real item for improvised acts" | review Q33 |
| Props for an act: "catalogued goods must be carried and trifles can be supplied by the place" | review Q34 |
| Item categories: "Item categories grow material families" | review Q35 |
| Notes raised by time in the middle of a turn print after the passage: "Below" | review Q36 |
| Model sampling (temperature, repeat penalty): "Keep them as they are for now." | review Q37 |
| Invented non-words in the prose: "Only reported." | review Q38 |
| "The games own italic notes with dashes can stay." No dashes is for the story (narration, speech, and what the narrator is handed); the game's own notes, lists and labels keep theirs. | f413 |
| Companion habits ("counts her coin on arriving") are handed to the narrator and told inside the passage of their moment, never on a line of their own. | f412 |
| An accent is in every line a speaker says, not rolled for some. | f410 |
| Travel is narrated; road events sit inside the journey (changed by review Q2: a noteworthy road event stops the walk). Dialogue must keep moving toward sounding human. | f408, f409 |
| The fight pane stays after a fight with that fight's log. Hovering an ability shows its full card. | f405 |
| While the world is thinking, the text does not move. "More below" is a clickable down arrow. | f402 |
| No dashes in speech either: every speaker, not only the narrator. | f403 |
| Character creation cards do not show "rank I"; everyone starts at rank I. | f401 |
| Buffs have no tiers. Summons are left as they are for now. Hired companions cast spells at the rank their level allows. | f400 |
| Spells: flat cost and power with stronger versions later. Light, moderate and heavy stay a melee mechanic. Cooldowns stay, including spells with a day-long cooldown. The model names spells for their rank, never in the style of "fire, fira, firaga". Rank-ups come from books and teachers. Named spells are boss, dungeon and quest rewards. | f397-f399 |
| The world grows to accommodate what makes sense, like a dungeon master; impossible things are refused. | slices 0-2 |
| Everyone starts with a weapon, whatever their class. The starting weapon is shown while attributes are allotted. | f389 |
| Character creation begins with who the character was: their people, he, she or they, and their look. | f388 |
| No length limits on the narrator or speakers. | f375 |
| Eccentric, not obnoxious; distinct even when mundane. | |
| Maren's tutorial may be the same every run, because it can be skipped. | |
| Names: one-syllable names are allowed for every people except the elves. Non-human surnames are built like their first names, never from English words. Gnomes keep their ridiculous names. | |
| Main menu: Continue, then Load, New Game, Settings, Quit. New Game is not an in-game pane. The title backdrop shows the centre of the map, not the coast. | |
| The gold accent is for dark mode only. | |

## Open questions

- Multiplayer's clock: how does time work when players separate (one player fighting while another travels for days, sleeping while another fights)? To be researched first: how MUDs and other shared worlds handled players who split up.
- Should a class's "main" attributes be the ones its abilities and weapon actually use? A mage was shown Dexterity as a main stat.
- Should the home page pick up a save folder copied in from an installed copy of the game?
