# 17. Multiplayer: where the game says "one player" today, and the plan to change it

Status: a survey and a plan, written 2026-11-12 against commit 18bc3a3 (branch `pillar2/outside-combat`, f605), with the owner's
answers of the same day in section 6. Nothing here is built. It brings doc 08 (the architecture) up to date with the code as it stands after the foundations features and phase 2,
keeps doc 06 (time when players split up) as it is, and adds what neither covers. Six read-only surveys of the code stand behind it
(storage, the scene and the turn, process-wide state, the world simulation, the model layer and prompts, the window and the
harnesses); the claims the plan rests on were then checked by hand. Line numbers are as of that commit.

The owner's decisions it serves (GOALS.md, 2026-11-03): players share one campaign and can split up and reunite; no fixed cap on
players; each player's model calls run on that player's own card; group narration is shared third person and a player alone is still
"you"; a party of humans shares its scenes and brings few companions (the numbers, changed on 2026-11-12, are in 3.9). Roadmap: the groundwork is phase 3, multiplayer itself
phase 5.

## 1. The short answer

The game says "one player" in seven layers. Three numbers size it:

- **About 1,340 uses of the scene's one player** (`self.player`, `ws.player`) in 54 files; doc 08 said 1,078.
- **About 900 calls that write to the one screen** (`console.*`) in game code.
- **19 module-level bindings a session owns**, and about a dozen more nobody resets, that hold one turn's or one player's state for
  the whole process.

Most of those 1,340 uses do not need editing. They mean "the character who is acting", and they stay right if the scene object a turn
runs on is bound to that character. What needs real work is smaller and harder: the uses that mean "the person at the screen" or "the
place the world looks from", the state held once per process, the one clock, the one revision every commit checks, the prompts and
checkers that enforce "you", and the complete absence of any notion of a client, a connection or a second machine.

Doc 08's shape holds: one host that owns the save and checks everything, clients that show output, send lines and serve their own
model. The survey found nothing against it and several things that make it cheaper than it looks (section 4).

## 2. Where the game specifies one player

Each table lists what assumes one player, where, and how hard it is to change: **mechanical** (a rename or a parameter),
**moderate** (a contained redesign of one module), **design** (a decision is needed first).

### 2.1 The record and the save

| What | Where | Change |
|---|---|---|
| One player record: `kv['player']` holds the one `PlayerState` | storage/campaign.py:448-470 | design (a players table) |
| A character's id defaults to the literal `"player"` | core/models.py:250 | mechanical, but that key is in the three recordings' dice |
| One clock, one input counter, one turn counter for the campaign (`CampaignMeta.minutes`, `steps`, `turn`) | storage/campaign.py:38-45 | design (doc 06) |
| **One revision that every commit checks, and every operation saves the player** | storage/campaign.py:539-568; scenes/world.py:1071-1087 | design |
| An operation does not record who acted | engine/operation.py:29-47 | mechanical |
| Eleven single rows that are really one player's: the talk, the open question, the deferred work, the fight, the notices | storage/campaign.py:500-533, 644-651 | moderate (key by character) |
| The world's lists are one JSON row, loaded and saved whole at 138 sites | storage/worldrow.py:57-83 | design (tables, doc 13) |
| A recording's inputs name no actor, and a replay refuses calls that overlap | engine/recording.py:14-24, 165 | design |
| The save list shows one character per save | storage/saves.py:87-109 | mechanical |

The fourth row is the one that matters most. Two players in different towns would still collide on every single commit, because each
commit bumps one number and rewrites the player row. Concurrency is impossible until that goes.

Already keyed by character: how each person regards each character (npc/models.py:34-47), a deed's `by`, a situation's `willing[by]`,
the kept act rulings and pending acts, a thing's owner, the journal's actor and target.

### 2.2 The scene and the turn

| What | Where | Change |
|---|---|---|
| `WorldScene` is built on one `PlayerState`, rebound in six places | scenes/world.py:95-101, 551, 1273, 1391, 1665; arc_actions.py:791 | design |
| `acting` is that player's id; `characters()` returns a list of one | scenes/world.py:163-168, 1340-1342 | mechanical once there are several |
| About 31 fields that are one player's view or one line's state (`present`, `partner`, `convo`, `pending`, `combat`, `line_ops`, ...), plus 11 held and about 40 rolled-back names | scenes/world.py:102-133, 1019-1028 | design (the split in 3.2) |
| `turn()` is one line from one person: the line, its steps, the passage, the world's tick, arrival, the law, the tail | scenes/world.py:1505-1624, 2160-2181 | design |
| `advance()` moves the one clock and ticks one character's needs | scenes/world.py:372-389 | design (doc 06) |
| Who is here is worked out from one location | scenes/world.py:425-480 | design |
| The loop asks one person for a line; quitting saves one player and ends the game | scenes/world.py:858-930 | design |
| Code that takes a character id still reads the scene's player for the place and the sheet | engine/act.py (14 uses), engine/ruling.py (10), engine/targets.py:70-79 | mechanical |
| The party service is bound to one player; the cap is three companions for that player | services/party.py:32-52; data/rules/party.yaml:10 | moderate |
| **The owner's companion rule for a party of humans (3.9) is implemented nowhere** | searched code and data | design |
| A fight can hold several player fighters, but commands, panes, death, loot and experience serve the first | engine/combat.py:414-416; scenes/combat_scene.py:229-542, 859-957, 1240-1266 | design |
| Death moves the shared clock by days and wakes the one player elsewhere | scenes/combat_scene.py:1240-1266 | design |
| One conversation: one partner, one saved talk | scenes/world.py:1344-1359, 3300-3400 | design |

What the uses of the scene's player actually read: the place (335), the character sheet (281), the party (118), quests, reputation,
the road, homes and flags (128), and about 400 that pass the whole record on. The id-taking style the project already asks of new
code (`self.acting`, `actor_id`) has reached 22 files.

### 2.3 State held once for the whole process

Nothing in the game uses a context variable yet. What a turn needs is found by reaching for a module:

| What | Where | Belongs to |
|---|---|---|
| The one open operation; opening a second raises | engine/operation.py:68-100 | the turn |
| The turn's budget; opening a second silently replaces the first | engine/budget.py:189-196 | the turn |
| The ledger's rows, the turn log's open row and what was shown | engine/ledger.py:42-53; engine/turnlog.py:33-37 | the turn |
| The dice: one set, seeded from (seed, the campaign's input count, the line), which also reseeds Python's global `random` | engine/streams.py:44-56, 107 | the actor |
| The journal sink, the name map, the cast's pronouns, the last failure, the last question, a price discount | engine/canon.py; names.py; failures.py; questions.py; enchanting.py | the actor |
| **The screen: only story text goes through the channel.** The prompt for a line, the panes, the status block, the busy light, the fight's pane, the home page and creation are module attributes the window swaps, and each operation swaps them again to hold its lines | ui/console.py:35; ui/gui/bridge.py:265-276; scenes/world.py:1129-1150 | the client |
| The turn log and the recorder wrap console functions by assignment | engine/turnlog.py:162-173; engine/recording.py:174-190 | the process |
| A player's preferences (`#dialogue`, `#numbers`, `#debug`) are flags on `config` | scenes/world.py:2580-2588 | the client |
| The card's speeds and its "slow" flag | engine/budget.py:63-69 | the card |
| Every log (turns, model calls, refusals, the audit, crashes) is one file with no actor in its rows | engine/turnlog.py:56; llm/gateway.py:421-449; llm/audit.py | the process |

`engine/session.py:47-78` owns 19 of these with a known reset; the turn log's `SHOWN` and `COUNTS`, the audit's state, the gateway's
tallies and the refusal and crash lists are owned by nobody. The data loaders and pure caches are safe as they are.

Built already: the output channel object (f580) and the dice as an object (f581). Doc 13's file name for the context,
`engine/context.py`, is taken by another module.

### 2.4 The world looking from one place

| What | Where | Change |
|---|---|---|
| "Within reach" and the placement bands are measured from the one player's location | engine/pulse.py:204-212, 496-529 | moderate |
| A consequence rule starts at the one player's town and counts everyone's deeds as theirs | engine/consequences.py:47, 73-75 | moderate |
| Towns forget one player's standing; the pulse loads, edits and saves that player | engine/drift.py:266-292; scenes/world.py:548-553 | moderate |
| A cataclysm is due by the one player's level; a town falls less often when "the player" is in it | engine/events.py:101, 1182-1227 | design |
| Notices and assaults are single queues, drained by whoever pulses first | engine/events.py:1326-1373 | design |
| The town's moment, the town-memory sweep and closing old offers all start from the one location | engine/moments.py; town_memory.py:9-49; obligations.py:119-126 | moderate |
| **What "the player" knows of a matter is a bare flag on the matter**: answered, touched, revealed, summoned, a clue found | engine/matters.py:67-490; scenes/part_actions.py:164-183 | design |
| Told, trusted and protected each hold one character id; a second character overwrites the first | engine/situation_parts.py:1522-1558 | moderate |
| News of a deed carries a name only, and lands on whoever arrives in the far town | engine/standing.py:116, 147-169 | design |
| The journal's "lately" keeps only rows whose actor is the literal `"player"`; memories default their subject to it | engine/truth.py:520; engine/memory.py:72-94; quirks.py:362 | mechanical |
| The clock: 2 writers, about 81 callers of `advance`, about 590 reads | scenes/world.py:194-195, 375; engine/starts.py:67 | design (doc 06); the reads are mechanical |

World code reaches for "the" player 18 times in `engine/`, never in `npc/`. Doc 06's `touched_at` and `region_time` exist nowhere
yet. News is already filtered by place, travel time and group, but not by the receiver's own clock.

### 2.5 The model layer: one card

| What | Where | Change |
|---|---|---|
| One process-wide stack of model sources; `chat` and `embed` take no actor and no card | llm/backend.py:298-361, 522-533 | design (a router) |
| One worker with one foreground count: any turn's call pushes every background call aside | llm/worker.py:52-111 | moderate (a worker per card) |
| Cancelling a session's background work is keyed by campaign, so it would cancel everyone's | llm/worker.py:178-189 | moderate |
| One runtime, one server, one game per machine (the game lock) | llm/runtime.py:445, 936-939, 1109-1192 | design |
| **The model server must be on this machine: "a game never sends its prompts off the machine"** | llm/llama.py:477-494 | **the owner's decision** (section 6, question 1) |
| The budget prices every call at one card's measured speeds | engine/budget.py:63-69, 189-196 | design |
| One failed embedding turns embeddings off for everyone; one background job per save | engine/embed.py:20-23; npc/backfill.py:10-59 | moderate |

Ready: the interface itself is neutral (a request holds nothing of the machine), sources stack, a stand-in can play a remote card in
tests, the failure kinds (unreachable, deadline, cancelled) already map to what the gateway does, the worker only decides when a call
may start, and every model call is already prepared before its transaction opens (f470), which is exactly what a call to another
machine needs.

### 2.6 The prompts and the checkers: "you"

| What | Where | Change |
|---|---|---|
| The narrator's voice is written for "one player at the table", second person; six prompts inherit it | scenes/voice.py:11; world_prompts.py:106-254; combat_prompts.py:54-132 | moderate (a perspective block from data) |
| The voice's example passages are all "you" | data/rules/voice.yaml:38-53 | moderate |
| The road's scene and journey must be second person, and a validator enforces it | engine/road_prompts.py:23-28; llm/contracts.py:1815-1830 | moderate |
| **The checker rejects "the player" for seven narrator tasks, and a rewriter turns "the player" into "you" on every line that reaches the screen** | data/rules/hygiene.yaml:12-21; engine/hygiene.py:111-125, 202 | design |
| The trained adapters' system prompts say second person | data/rules/lora.yaml:38-40 | design |
| In a fight every fighter on the player's side is "you" (about 20 sites) | engine/combat.py:415-443 and the spell, movement and technique texts | design |
| The cast list given to every writer never lists a human; the player is one literal reference | engine/entities.py:59-112 | moderate |
| Contracts and requests hold one player name, one addressee | llm/contracts.py:863-1084; engine/party_director.py:98 | mechanical to moderate |

Twelve prompt modules, about 20 places that fix the perspective, 74 call sites into the model across 60 priced tasks. Doc 08 said the
checker "gains a rule"; in fact the existing rewriter would damage a shared third-person passage and has to become aware of the scene.

### 2.7 The window, the start and the harnesses

| What | Where | Change |
|---|---|---|
| One bridge with one inbox, one event log, one prompt state; no client, connection or channel anywhere | ui/gui/bridge.py:59-80 | design |
| The server binds to this machine only, with one token | ui/gui/server.py:134-139, 248-250 | moderate |
| A pane refreshes by the bridge injecting a command into the game loop, and a pane click uses up a dice step | ui/gui/bridge.py:196-225; scenes/world.py:940 | design |
| Start-up is one line of code for one player: home page, load, creation, scene, run; closing the window ends the game | main.py:71-171; ui/gui/__init__.py:14-52 | design |
| Creation runs before any scene or actor exists | scenes/goddess.py:70-220 | design |
| The test campaign makes one player and one scene; "two characters" makes only a second sheet | simlib.py:765-786, 921-931 | moderate |
| The night bot is one bot on one scene; parallel runs are separate games | tools/nightrun.py:418-651 | design |
| There is no networking code of any kind | searched | new |

Ready, and worth more than it looks: output is already a stream of plain events with ids, the stream replays from an id after a
reconnect, input is already lines with a small grammar, and there is a token check. Section 4.3 turns that into the wire protocol.

## 3. How each kind of assumption changes

### 3.1 Three meanings of "the player"

Every use of the scene's player means one of three things, and each gets its own home:

1. **The character acting** (most uses, by what they read in 2.2): the place they stand, their sheet, their party, their quests. Stays
   `self.player`, which becomes a view of the character the turn is bound to. No edit at the site.
2. **The person at a screen**: where a line is shown, who is asked, whose panes refresh, whose preferences apply. Moves to the
   actor's output channel and client.
3. **Where the world looks from**: reach, placement, the town's moment, whose level sets a cataclysm. Becomes "every character in
   play", through one helper that lists them.

The work is finding the uses that are 2 or 3, not editing 1,340 lines. A fence test (a scan of the syntax tree, as the project
already uses) keeps the count of each from growing while they are moved.

### 3.2 The scene splits in three

`WorldScene` today is three things in one object. They separate:

- **The actor's context** (one per human character): the player record, the clock, the dice, the output channel, the turn's
  registers (the operation, the budget, the ledger, the pending question, the last failure), the preferences, the card. Reached
  through a context variable, so code deep in the engine finds the right one without being handed it.
- **The scene** (one per place where at least one character is; a party travelling is one scene that moves): who is here, the
  residents, the conversation, the fight, the wildlife, the scene's clock. Shared by everyone in it.
- **The facade**: `WorldScene` stays as the object the 54 files talk to, bound to one scene and one actor for the length of a turn.
  This is what lets the rest of the code move a module at a time (doc 08 3.2 proposed it; the survey confirms it is the only cheap
  way through).

A private conversation inside a group is a small scene of its own.

### 3.3 The process-wide state moves onto the contexts

Each binding in 2.3 goes to the home in its last column. The 19 owned ones already have a reset and a rollback rule, so their move
is mechanical. Three need more than doc 08 or 13 said:

- **The whole output seam, not only text.** Asking for a line, the panes, the status block, the busy light and the fight's pane
  become methods of the channel. Holding an operation's lines, the turn log's tap and the recorder then wrap the channel, never the
  `console` module. Until this is done, a second player's turn would print to the first player's window.
- **Preferences leave `config`** for the actor.
- **Every log row names who acted**, and the model call log is one per actor.

### 3.4 The save

- **A players table** (one row per character: the record, the clock, the place, the party, online or not), migrated from the one
  row. The first character keeps the id `"player"` and, until M1, today's dice key (the owner's decision of 2026-11-10); every
  later one gets an id at creation.
- **The single rows of 2.1 are keyed by character** (the talk, the open question, the notices) **or by scene** (the fight).
- **The world's lists become tables** with the acting character and the minute on each row (doc 13's migration v17, with the one
  re-record of the recordings the owner agreed to).
- **The one revision becomes a version per row.** An operation records the rows it read and the versions it saw; its commit is
  refused only if one of those changed. The player row is written only when the operation changed it. Two towns then commit freely,
  and two players persuading the same smith conflict exactly once, which is the case that should conflict.
- **What a character knows of a matter is kept by character**: answered, touched, revealed, summoned, a clue found, told, trusted
  and protected become maps by character id, as `willing` already is.

### 3.5 Time: the place keeps the clock

Doc 06 proposed a clock per character with a last-touched time on everything and a two-day window. The owner asked for deeper
research before choosing the window (docs/research/shared_world_time/report.md, with its notes beside it), and on
2026-11-12 took its recommendation in doc 06's place: **place clocks with agreed skips**. The rules, with the owner's answers in them:

| Rule | Statement |
|---|---|
| T1 The place keeps the clock | Each place has one clock. A place is the unit the world simulation already catches up: a whole settlement, a dungeon, a stretch of road. A character keeps a clock of their own for the time they have lived (billing, healing, needs). A fight is a closed scene inside its place; nobody is moved in time in the middle of one, and what it changes outside itself lands on the place's clock when it ends. |
| T2 Small drift, unasked | In a shared place the clock is the furthest among the playing characters there. One who is more than about **an hour** behind it is brought to within the hour at their next action outside a fight, with a narrated line and no question. |
| T3 A long action in a shared place is offered | When a player starts something longer than that hour (a night's sleep, a day's craft), each other playing character there is offered, at their next moment outside a fight, to pass the time too (rest, work, train) or to play on. The offer is out of the story and reveals no deeds, only the time on offer; a player waiting sees a count of how many the place waits on, and nothing else. Silence follows the host's wait-or-window setting. A sleeper's morning waits for a fight in the same town to end. |
| T4 Travel brings clocks level, forward only | Arrival is at the later of the leaving time plus the road, and the destination's clock. A gap of up to **12 hours** is told as delay on the road; a longer one is put to the traveller before leaving. A destination that is behind and empty catches up lazily. One that is behind with a player in it: **the resident is asked** (offered the skip, or plays on), and the arrival waits meanwhile. |
| T5 Effects land late, never early | What leaves one place for another (news, a follow-on, a spreading disaster) lands at the later of its due time and the receiving place's clock. A character knows what has landed where they are. News may therefore arrive later than the road alone explains; the owner accepts that. |
| T6 Running ahead is warned | Before an action that would leave a character more than **two days** ahead of the slowest playing character within reach, the game states the cost and asks. The host may turn the warning off. (The strict road-time rule stays in reserve for the day players may fight each other.) |
| T7 Offline | The character is walked to the nearest safe place and checked out of the world. On return they have rested, all is as it was, and they are **always brought level** with their friends within reach; the benefit of time away is capped. |
| T8 The world's own timers | A world-wide situation with a time limit (a cataclysm, a campaign-tier situation) runs on the slowest playing clock, and reaches each place by T5. |
| T9 Telling the time | Each player sees their own date and time of day, in relative words, as the game already tells time. |

What this changes from doc 06: no last-touched time on people and things (the place's one clock does that work); the window is a
warning, not a wall; a resident is asked instead of moved. What it keeps: lazy catch-up per region, a clock per character, checking
out when offline, nothing ever moving backward. Common groundwork, built first and changing nothing for one player: every read of
"now" names whose clock it means (there is no global present); one routine carries a character forward and applies all that elapsed
time does; effects between places follow T5. Sizes from the survey: two places write the clock today, about 81 call `advance`, and
the roughly 590 reads go through one property.

Still to choose: the cap on what time away may credit, and the length of the offer's window. The combination is new and was tested on
paper only (the report says where it rests on inference); the first two-character night is its first real test.

### 3.6 The world looks from every character

One helper, "the characters in play and where they are", replaces the 18 places world code loads "the" player. Reach and placement
are computed around each of them (a band is drawn for a character, weighted by how recently each played, as doc 08 3.5 says); a
consequence rule counts the deeds of the character it runs for; the town's moment and memory run for every town a character is in;
notices are addressed to a character or to a home.

### 3.7 The model: a router and a card per player

- A **router** sits below the gateway and above the sources. It picks the card by task: the world's own work (births, a
  situation's parts, the pulse) on the host's card; a shared passage on the scene leader's; everything else (the understanding, a
  ruling, a person's reply) on the acting player's.
- A **remote source** implements the same two calls (chat, embed) over the connection to a client, with a **worker per card**.
- **The budget is priced per card**: each client reports its measured profile when it joins, and a turn is priced on the card that
  will serve it. A slow card slows only its own player; the scene's leader moves off a slow card.
- **A card that drops mid-call**: the router retries on the host's card, and past that the call's written fallback stands, as today.
  (Doc 08 named a test stand-in as this path; the real path needs the router.)
- **Recordings**: one ordered stream of calls per actor, so two players' calls may overlap without breaking a replay.

### 3.8 Narration for several humans

The perspective becomes data, decided per scene from who is in it: one human is "you" exactly as today; several are shared third
person, by name. That one switch feeds the voice's rules and examples, the road's validator, the fight's "who", the cast list (which
must now list every human, with name and pronoun, so the identity checks cover them), and the screen's rewriter, which in a group
must leave "the player" for the checker to reject instead of turning it into "you". The trained adapters are a separate question
(section 6).

### 3.9 Playing together

Doc 08 3.4 stands: a beat collects each member's line, each is understood on its own player's card at the same moment, the engine
resolves them in order, and one passage is written on the leader's card. New from the survey:

- **A party is the unit of playing together** (the owner, 2026-11-12): "players should be able to party up and share
  narration/fights/scenes/etc. When they split up and leave the party is when these time changes should matter." Humans in one party
  share one scene, one passage, one fight and one clock; the time rules of 3.5 (drift, offers, arrivals, warnings) apply between a
  party and everyone outside it, never between its members. A long action inside a party (a night's rest) is the party's own, settled
  in its beat by the host's wait-or-window setting. Leaving the party is what gives a character a scene and a pace of their own.
- **Who comes along** (the owner, 2026-11-12, replacing the numbers of 2026-11-03), to be built in data and in the party service:

  | Humans in the party | The party is |
  |---|---|
  | 2 | player 1, player 1's companion of choice, player 2, player 2's companion of choice (each brings one if they have at least one) |
  | 3 | player 1, player 2, player 3, and player 1's companion of choice |
  | 4 or more | every player, and no companions |

  The companions not brought stay in their own player's party and go on errands, as decided on 2026-11-03. "Player 1" is the party's
  first member, the one the others joined (the owner, confirming).
- **A fight needs a command from each human** each round, with the safe automatic action for one who does not answer; today
  `player_ai` only drives the danger estimate.
- **Death, loot and experience** need rules for one of several (section 6).

## 4. The infrastructure

### 4.1 Shape

One **host** owns the save, runs the engine and the world, and checks everything a model writes, exactly as the game does today.
Each **client** is a window, a relay and that player's own model server. Clients never write state: what their model writes comes
back as a proposal and passes the same contracts, grammars and checkers. Single player is the same program with one actor and a
local client; nothing forks. The host can be one player's own machine.

### 4.2 Running several turns at once

One thread per actor on the host (the game already runs a game thread, a window thread and background model threads, with the rule
that an operation belongs to the thread that opened it). Model calls overlap because they go to different cards; commits pass one at
a time through the one SQLite writer in milliseconds. A commit refused for a changed row is prepared once more against the new
state. The world's own work runs per region under a region lock, catching up lazily when someone arrives (doc 06).

### 4.3 The wire

Today's window protocol is the starting point, and it is most of what is needed:

- **Host to client:** the existing events (`text`, `echo`, `panel`, `status`, `combat`, `prompt`, `busy`, `ended`, the home and
  creation pages), each with an id, replayed from the last id seen after a reconnect. Each gains the actor or scene it is for.
- **Client to host:** the existing lines: free text, `#view` commands, button commands.
- **New, host to client:** a model request (the machine-neutral request the recorder already writes) and its reply.
- **New, on joining:** a hello with the game's version and the hash of its data, so a client on other rules is refused in a clear
  line; the account and the character it plays; the card's measured profile.

**Multiplayer works through Steam's framework** (the owner, 2026-11-12: "I eventually want this to be playable through steam so
the multiplayer functionality should work through steam's framework"). What that gives and settles:

- **Transport:** Steam's networking sockets, carried over Steam's relay. Players connect by Steam identity, not by address, so
  nobody opens a port and the host need not be reachable from the internet; the relay also hides each player's address from the
  others. The messages above go over it unchanged: events and lines, and the model requests and replies to each player's card.
- **Finding and joining a game:** a Steam lobby per running campaign, joined by invitation from the Steam friends list or the
  overlay, and by "join game" on a friend who is playing. That is the "join any time" the owner chose: the joiner's Steam identity
  asks the host for a seat.
- **Identity:** the account is the Steam account. A seat in a campaign is held by a Steam identity, one character each.
- **Privacy:** prompts travel only to the machines of players in the game, as decided, over Steam's encrypted connections.
- **What stays the game's own:** the host's authority, the messages, the checking of everything a model writes, and saving. Steam
  carries the bytes and names the people; it decides nothing about the game.

Two things need building around it. The game is Python and the Steamworks SDK is a C++ library, so the game needs a binding (an
existing community wrapper or a small one of its own) inside the shipped executable. And the suite cannot run Steam, so the
transport sits behind one interface with two implementations: Steam for the shipped game, and a local one (loopback, or two
windows on one machine) for the tests, the hotseat harness and nights with several bots. Development before the game has its own
Steam app id uses Steam's public test app; the store page and app id are the owner's to set up.

### 4.4 Identity, joining and leaving

A seat per Steam account per campaign, mapped to a character id in the players table. Creation for a joiner runs on the host with
the joiner's card. A player who leaves is checked out (walked to the nearest safe place, as the owner decided) and does not hold the
others' clocks back. The save stays on the host; another player hosts by receiving a copy of it (whether Steam Cloud carries that
copy is open).

### 4.5 Trust and privacy

- **Checking is unchanged**: the host validates every answer. But a ruling on a player's own act would run on that player's own
  card, so a modified client could always rule in its own favour with a perfectly valid answer. Among friends this may not matter;
  it is the owner's call (section 6, question 2).
- **Prompts would leave the machine** for a party member's computer. Today's code forbids that in words. That rule was written for
  hosted services; the owner should say whether a friend's card is within it (question 1).

### 4.6 Testing and measurement

- A **hotseat harness** in the test library: two actors, one process, the stand-in model, taking turns. Every milestone before the
  network is proven on it.
- **Recordings per actor**, replaying exactly whatever order the host interleaved the players in (per-actor dice make that true).
- Doc 08's six tests (replay, isolation, conflict, group beat, disconnect, pulse) and doc 06's seven clock tests.
- **Night runs with two to four bots on one host**, read per actor by the existing tools once log rows name the actor.
- **The host's own load is small.** Tonight's pod night measured the world's births at about 0.8 calls a game day and about 17
  seconds of a 3060 a game day (an estimate scaled from a 4090), so a host's card has room for the world beside its own player.

## 5. Order of work

Doc 08's milestones hold, with the survey's additions in bold. Each is a set of numbered features with tests; the suite passes at
every step.

| Milestone | What | Proof | Size |
|---|---|---|---|
| **M0: groundwork, no behaviour change** (the roadmap's phase 3) | The turn's context and the actor's context, with one actor. The 19 owned bindings moved onto them. **The whole output seam under the channel** (prompts, panes, status, the fight's pane; holding, the turn log and the recorder wrapping the channel). **Preferences off `config`.** **Log rows name the actor; the operation names who acted.** The players table with one row; the world tables; **the single rows keyed by character**; **the literal "player" ids replaced by the character's id**; id-taking code reading the acting character through one helper. | Every recording replays exactly; fences on each moved name | Large, mechanical |
| **M1: two characters, one machine, taking turns** | Several player records; the hotseat harness; the scene split (scene, actor's view, facade); `characters()` real; **the world looking from every character** (the 18 sites); **knowledge of a matter per character**; per-actor dice; **the place clocks of 3.5** (the groundwork, then travel and the shared clock, then offers and pending arrivals, then the warning); **the companion rule**; **death for one of several** | Split, rejoin, touch, perceive, window; isolation of output | Large |
| **M2: turns at the same time** | A thread per actor; **row versions in place of the one revision, the player row written only when changed**; re-preparing once on a conflict; region locks; **the budget per actor**; **recordings per actor** | Two actors in two towns never block; one conflict on one person resolves once | Medium |
| **M3: group scenes** | Beats; several actors in one plan; **the perspective as data through the voice, the validators, the fight's text, the cast list and the screen's rewriter**; group fights with a command each; conversations with several human speakers; loot and experience shared | Three humans, one passage a beat; a fight with two humans | Large |
| **M4: the network** | The wire of 4.3 behind one transport interface: the local one for tests first, then Steam's networking, lobbies, invites and identity through a binding in the shipped executable; the router, the remote source, a worker and a profile per card; the hello; joining, creation for a joiner, reconnecting, checking out | Two machines, each paying for its own model calls | Large |
| **M5: polish** | The out-of-story "meanwhile" feed, the lobby and invites, hosting from a copied save, a pass on turn time | Nights with two to four bots on separate machines | Medium |

M0 changes nothing a player sees and is already the roadmap's phase 3, so it can start when phase 2 lands. Three small pieces of it
touch no turn code and could be built at any time: log rows naming the actor, the literal ids, and the id-taking code reading the
acting character through one helper.

## 6. The owner's answers (2026-11-12; GOALS.md holds them)

| Question | Answer |
|---|---|
| 1. Prompts on a friend's machine | Yes, party members only: a prompt may go to the machine of a player who is in the game, and nowhere else. Hosted services stay out. |
| 2. Ruling on your own card | On your own card. Which card judges stays a setting in data. |
| 3. The host | A player's machine. A dedicated host is not built first, and nothing blocks it later. |
| 4. Joining | One character per account per campaign. A new player may join a campaign already running; creation runs on the host with the joiner's card. |
| 5. What a companion learns | Shared in the same scene: whoever is there when it is learned knows it. One who was elsewhere does not, until told or until they find it. |
| 6. One of several falls | Down until the fight ends, and up wounded if the party wins. Today's death happens only when every human in the fight has fallen. |
| 7. The cataclysm and a town's shield | The highest level among the characters in play; any character in a town shields it. |
| 8. A consequence rule's deeds | Each character's own. A shared deed counts for each member who took part. |
| 9. A slow member in a group beat | A setting the host chooses: wait for everyone, or move on after the window. |
| 10. Private conversations in a group | Allowed, as a small scene of its own. |
| 11. Players fighting each other | Never, for now. The owner wants it eventually, so nothing built may rule it out (a fight's sides stay data, never "humans against the rest"). |
| 12. Two players after one thing | First to commit. The second's attempt is worked out again against the new state. |
| 13. The window between clocks | Replaced, after the research the owner asked for: place clocks with agreed skips (section 3.5). The two-day figure survives as a warning the host may turn off. |
| 14. The "meanwhile" feed | Off. Word of another player's deeds travels only through the world's news. (Doc 06's `meanwhile_feed` and M5's feed go.) |
| 15. Arriving late to a fight | Honest: it may be over. |
| 16. Offline on the road | The game walks the character to the nearest safe place. (Doc 06 proposed camping where they are.) |
| 17. A pane click's dice step | Only story inputs count. It goes into the one planned re-record. |
| 18. Embeddings | The host makes every stored vector. |
| 19. The trained adapters in a group | Off in group scenes until a third-person set is trained (doc 09 C). A player alone keeps the adapter. |

What these change in the plan above: section 4.5's two questions are settled (prompts to party members; rulings on one's own card);
3.9's death rule is "down until the fight ends"; 3.4's knowledge maps are filled for every character in the scene when something is
learned; 3.6 uses the highest level; M3 gains the host's beat setting; M5 loses the feed; M0's re-record carries the dice-step
change; and section 3.5's place clocks take the place of doc 06's time model.

## 7. Where doc 08 is out of date

- The counts: about 1,340 uses of the scene's player (not 1,078) and about 900 console calls (not 670).
- The output channel and the dice object are built (f580, f581); the contexts, the players table, the world tables and the
  migration are not. The feature numbers doc 13 gave them (f584 to f592) were used by other work.
- "console writes to the actor's channel" covers text only; the rest of the output seam is still swapped process-wide.
- The party service does not hold the owner's companion rule; nothing does. (The rule itself changed on 2026-11-12: section 3.9.)
- `player_ai` is used for the danger estimate only, not yet as a human fighter's fallback.
- The cast list and identity checks do not list human characters.
- The checker does not simply "gain a rule": the screen's rewriter works against shared narration today.
- "A worker per card" and the disconnect fallback need a router that does not exist; the budget, the card's profile and the
  embedder's state are process-wide.
- The loopback-only rule for the model server is not mentioned, and it is a stated decision.
- The player-centred world sites are 18, not 3.
- The home page, the save list, creation, the game lock, preferences, pane refreshes and the dice step a pane click uses are not
  mentioned.
- The night bot is one bot on one scene; a multi-bot night is new work.
