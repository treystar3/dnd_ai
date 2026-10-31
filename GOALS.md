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

If a request seems to pull against a goal here, raise it with the owner before building. If the owner decides, record the decision
below.

## Owner's decisions

Newest first. Each is a call the owner made about what the game should be; follow it unless the owner changes it.

| Decision | Feature |
| --- | --- |
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
| A far place named only in part: "For major cities they need to say it exactly but for places off a road or locations it can ask." | review Q17 |
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
| The cap of deeds in one line: "Raise the cap but keep an upper limit for a clear runaway case. Maybe a limit of 15 or 99." | review Q31 |
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

- Should a class's "main" attributes be the ones its abilities and weapon actually use? A mage was shown Dexterity as a main stat.
- Should the home page pick up a save folder copied in from an installed copy of the game?
