# Time and turn order in turn-based strategy, play-by-mail/cloud and asynchronous multiplayer games

Reading notes for the writer:

- "Fit" in every Inferences block means fit to the target design: a host-authoritative co-op role-playing game narrated in text, where one typed action can consume seconds or days of game time, players can be together in one scene or apart in one persistent world, sessions are live but players may drop out, and there is no cap on players.
- Evidence grades used below: **[primary]** = rulebook, official wiki/help page, developer article; **[fetched]** = page was opened and read in this session; **[snippet]** = claim rests on a search-result excerpt of a forum or page that was not opened in full, so the attribution to the exact URL is less certain; **[forum]** = the claim rests on forum posts only.
- Anything I know from background knowledge but could not source in this session is in a Gaps block, labelled as unverified. Nothing in Cited Findings is from memory.

---

## 1. Civilization (IV to VII): simultaneous turns, hybrid turns, timers, Pitboss/play-by-cloud, the "double move"

### Takeaway
Civilization's simultaneous mode is not true simultaneous resolution: everyone acts in real time inside one shared turn and the first click wins, which creates click races inside a turn and "double moves" across the turn boundary. The engine never solved it; communities did, with gentleman's agreements and, in slow Pitboss games, a turn timer split into per-side windows during war.

### Cited Findings

**How game time advances**
- Civ IV multiplayer: at the start of each turn the AIs move first in player-number order, then all humans move simultaneously; the turn only rolls when all humans have ended their turn (if no timer is set). An asterisk beside each name shows who has pressed End Turn, and a human can keep moving after pressing it until the last player ends. [forum, fetched] — [Apolyton: simultaneous moves in MP in practice](https://apolyton.net/forum/civilization-iv/civilization-iv-multiplaying/248115-simultaneous-moves-in-mp-in-practice)
- Civ IV shipped a "PitBoss" (Persistent Turn-Based Server) for games of up to 32 players who log on at any time to take their turn; Soren Johnson (Civ IV lead designer) wrote that "combined with simultaneous movement and a 24-hour turn timer", epic games became manageable. [primary, fetched] — [Johnson, "Analysis: Asynchronicity In Game Design", Game Developer 2009](https://www.gamedeveloper.com/game-platforms/analysis-asynchronicity-in-game-design)
- Civ IV offered both simultaneous turns and classic sequential turns, with play-by-email as the long-form sequential option. [snippet] — [Apolyton: Civilization 4 Multiplayer overview](https://apolyton.net/content.php/890-Civilization-4-Multiplayer)
- Civ V default online play: simultaneous human play with a tight turn timer that ends your turn by force if it runs down. [snippet; the excerpt is from a 2010 hands-on preview, either of these two] — [Game Informer multiplayer hands-on](https://gameinformer.com/games/civilization_v/b/pc/archive/2010/09/10/multiplayer-hands-on); [Shacknews Civ 5 multiplayer preview](https://shacknews.com/article/65521/civilization-5-multiplayer-preview)
- Civ V "hybrid" mode: human players at peace move simultaneously; players at war move in turn order. [forum, snippet] — [CivFanatics: Hybrid mode](https://forums.civfanatics.com/threads/hybrid-mode.532954); [CivFanatics: Hybrid Multiplayer, simultaneous in the DoW turn?](https://forums.civfanatics.com/threads/hybrid-multiplayer-simultaneous-in-the-dow-turn.527133)
- Civ VI: a 2016 article on the Firaxis multiplayer stream reported that hybrid mode returned under the name "Dynamic" moves. [snippet] — [GameSkinny: Civilization 6 multiplayer details](https://www.gameskinny.com/ffbbw/civilization-6-multiplayer-details)
- Civ VII: hotseat was added after launch (update 1.4.1 per a guide), where players share a device and either share a turn or take individual turns. [snippet] — [ludo.guide: Civ VII hotseat](https://www.ludo.guide/guide/civilization-vii/multiplayer-strategies/hotseat). A Steam poster recalled the developers saying there would be no option to switch between sequential and simultaneous turns online; this is second-hand. [forum, snippet] — [Steam: Civ VII discussion](https://steamcommunity.com/app/1295660/discussions/0/4431066036852067626)

**How simultaneous actions are ordered and conflicts resolved**
- There is no adjudication step: actions apply in the order the server receives them. Players describe the consequences as: the game state changing while you plan (enemy reinforcements arriving mid-turn), and moving your own units in sequence opening gaps that did not exist when the first unit moved. [forum, fetched] — [Apolyton thread](https://apolyton.net/forum/civilization-iv/civilization-iv-multiplaying/248115-simultaneous-moves-in-mp-in-practice)
- A forum poster's summary of the result: the player with the fastest mouse wrist gets the advantage of moving first. [forum, snippet] — [Apolyton: how will 1UPT affect simultaneous multiplaying](https://apolyton.net/articles/civilization-news/civ5/info-aa/9312366-how-will-1upt-affect-simultaneous-multiplaying)
- The click race persists in Civ VII: a CivFanatics thread is titled "Multiplayer: Stable? Click race?" and a Steam thread raises the "click race issue of combat (when playing simultaneous turns)". [forum, snippet] — [CivFanatics](https://forums.civfanatics.com/threads/multiplayer-stable-click-race.691709/latest); [Steam](https://steamcommunity.com/app/1295660/discussions/0/591762818429093281)

**The double move and community rules**
- Definition used by one community proposal: a double move is when a player plays two turns without his opponents playing in between (move last in turn N, first in turn N+1). The same proposal forbids double moves in wartime and bans invading as part of a double move. [forum, snippet] — [Apolyton: new diplo game, big discussion needed](https://apolyton.net/forum/civilization-iv/civilization-iv-multiplaying/233421-new-diplo-game-big-discussion-needed?p=7635752)
- One poster concluded there is no practical in-engine rule that stops double movement; "perceived abuses of double-turning" were a recurring source of conflict between players. [forum, snippet] — [CivFanatics: Simultaneous moves with PitBoss](https://forums.civfanatics.com/threads/simultaneous-moves-with-pitboss.165331/latest)
- The live-play gentleman's rule (Apolyton regular): the player declaring war must do so early enough in the turn that the opponent can respond, and may not declare and then keep moving in the same turn; after that first turn there are no restrictions. [forum, fetched] — [Apolyton thread](https://apolyton.net/forum/civilization-iv/civilization-iv-multiplaying/248115-simultaneous-moves-in-mp-in-practice)
- The slow-game (Pitboss) formal rule, from a voted Civ IV ruleset with a 40-hour turn timer: "Turns will be split between two warring teams/alliances". Phase 0 = 40:00 to 39:00 (Team 2), Phase 1 = 39:00 to 20:00 (Team 1), Phase 2 = 20:00 to 0:00 (Team 2). Moves, promotions, upgrades, gifts and drafts are legal only in your own phase. "The team that moved last in the turn of the declaration of war will get the last part of the turn." The declarer "has to finish moving all of their units and end their turn" within a limit. "The double move rule shall also be applicable to movement on the turn prior to the declaration of war." Each team gets three 24-hour timeouts (pauses). The ruleset passed 15 of 15 votes. [forum, fetched] — [CivFanatics: Ruleset vote (2010)](https://forums.civfanatics.com/threads/ruleset-vote.359261/)

**Slow or absent players; pacing control**
- Without a timer the turn waits for the slowest human; the advice in a co-op (humans versus AI) game was to drop time pressure entirely: "give yourselves all the time in the world." Team play of humans against AI "avoids double-move concerns between opponents." [forum, fetched] — [Apolyton thread](https://apolyton.net/forum/civilization-iv/civilization-iv-multiplaying/248115-simultaneous-moves-in-mp-in-practice)
- Pacing is set by the host through the timer and by the community through rulesets (timeouts per team, timer length). [forum, fetched] — [CivFanatics: Ruleset vote](https://forums.civfanatics.com/threads/ruleset-vote.359261/)

**Complaints and what designers changed**
- Hybrid mode complaints: one poster said it can make games take two or three times longer; another that simultaneous is "pretty much the only way" to play Civ V online. A bug report: a declaration of war mid-turn caused "a clickfest until the end of the turn" because the switch to sequential did not happen until the next turn. [forum, snippet] — [CivFanatics: Hybrid mode](https://forums.civfanatics.com/threads/hybrid-mode.532954); [CivFanatics: DoW turn](https://forums.civfanatics.com/threads/hybrid-multiplayer-simultaneous-in-the-dow-turn.527133)
- Civ III Play the World had earlier tried a "turnless" mode where all players move units at once. [snippet] — [GameSpot: Civ III Play the World preview](https://www.gamespot.com/articles/civilization-iii-play-the-world-updated-preview/1100-2894699/)

### Inferences
- The double move is a general property of any system where (a) time advances in discrete shared steps and (b) order of action inside a step is free. Whoever acts last in step N and first in step N+1 gets two actions with no reply. A text role-playing game with a shared "round" in a scene has the same exposure if input order is first-come-first-served.
- The Pitboss fix (split the window into per-side slots only while in conflict) and hybrid mode (simultaneous in peace, sequential in war) are the same idea: free ordering when actions do not interfere, forced alternation when they do. This maps directly onto "exploration is free-form, opposed actions are sequenced."
- Because the target game is co-op, most of the double-move harm disappears (the Apolyton thread says exactly this for humans-versus-AI). What remains is the co-op version: a fast typist taking several actions before a slow one gets any, and non-player characters reacting to one player twice before another player's action lands.
- The hybrid-mode bug (war declared mid-turn, mode switch only next turn) is a warning: a mode switch between free and sequenced time has to take effect at the instant of the triggering action, not at the next boundary.
- Fit: moderate as a pattern (hybrid free/sequenced), poor as an implementation (first-click-wins inside a shared turn rewards typing speed; "wait for all to end turn" stalls on the slowest player).

### Gaps
- I did not find a primary source for how Civ VI's "dynamic" turn timer computes its length, nor an official statement of Civ VII's online turn modes. Background knowledge, unverified here: Civ VI's dynamic timer lengthens as the game progresses with the number of cities and units a player controls, and Civ VI's play-by-cloud mode is asynchronous sequential or simultaneous with notification when it is your turn.
- The CivFanatics "Fixing MP: a gentleman's agreement" thread returned HTTP 429 and was not read: [link](https://forums.civfanatics.com/threads/fixing-mp-a-gentlemans-agreement.437944).
- No developer statement was found on why Firaxis never added an engine-level double-move guard.
- AI takeover of a disconnected human in Civ (the game substitutes an AI) is background knowledge only; not sourced here.

---

## 2. Paradox grand strategy (Europa Universalis IV, Stellaris, Hearts of Iron IV)

### Takeaway
Paradox games run one shared pausable real-time clock for everyone, so pacing is a social problem: the engine gives hot-join and configurable AI stand-ins for absent players, and every serious community then adds house rules on who may pause, a minimum speed everyone must sustain, protection windows for crashed players, and substitutes.

### Cited Findings

**How game time advances; who controls it**
- One clock, continuous days, shared by all players; speed and pause are the pacing tools. Community answers conflict on the default rights, which itself shows they are configurable: one EU4 poster says "anyone can change the speed at any time, everyone adjusts to that speed"; another says there are options that only allow the host to change speed; another that any player can pause by clicking the date unless the host disabled it in lobby settings; another that in EU4 there is a 30-second wait before someone else can unpause. [forum, snippet; conflicting] — [Steam EU4 thread A](https://steamcommunity.com/app/236850/discussions/0/1729837292631597047); [Steam EU4 thread B](https://steamcommunity.com/app/236850/discussions/0/5829358177507460443); [Steam EU4 thread C](https://steamcommunity.com/app/236850/discussions/0/864969953515601200)
- Hearts of Iron IV organised groups "usually appoint the host as the arbiter of speed, with a convention for requesting a pause. Without one, the campaign either crawls or leaves players behind." [snippet, community guide] — [GuildOrder: HoI4 MP hosting protocols](https://guildorder.com/th/games/hoi4/guides/mp-hosting-protocols)
- The HoI4 base game forces a pause or slowdown when a client lags, enough that a Workshop mod exists to remove it ("No forced Pause / Slowdown for MP Lag"). [snippet] — [Steam Workshop comments](https://steamcommunity.com/sharedfiles/filedetails/comments/2108723759)

**Hot-join and absent players**
- EU4 developer diary: the network engine was rewritten so that "if the host so desires, players can join a game already in progress through what we call hotjoin"; and "we ... now have a few options where you can tell the AI how they should govern the country while the human player is AWOL." [primary, snippet] — [EU4 Developer Diary 32, "The more the merrier"](https://forum.paradoxplaza.com/forum/threads/europa-universalis-iv-developer-diary-32-the-more-the-merrier.689790/post-15513135)
- Hot-join has been a known source of desynchronisation; Paradox acknowledged a case where a change applied only by hot-joiners desynced them. [primary, snippet] — [EU4 development diary, 31 October 2017](https://forum.paradoxplaza.com/forum/threads/eu4-development-diary-31st-of-october-2017.1052692/page-2)
- A 30-plus player session reported "massive desyncs all around"; pausing and waiting for hot-joiners did not fix it. [forum, snippet] — [Paradox forum: has anyone successfully started a 32 player session](https://admin-forum.paradoxplaza.com/forum/threads/has-anyone-successfully-started-a-32-player-session-yet.1419224)

**House rules (one full ruleset read; r/Europe EU4 campaign 6)** [forum/community ruleset, fetched] — [HackMD ruleset](https://hackmd.io/@JWDQgyGZQniOo_UhJSCyZw/ryzmm6bQP)
- Sessions: fixed weekly slot (Sundays 18:00 to 22:00), a 15-minute break at half time.
- Speed: every player must be able to hold at least speed 2; "repeated offenses of lagging" can get a player removed.
- Pause: only the host, moderators and players who have unconditionally surrendered may pause. Pauses are for breaks, surrenders, letting laggers catch up, and disputes.
- Absent without notice: the nation is protected for the first 15 minutes (moderators may extend to the whole session); with no contact after the break the nation becomes VACANT.
- Crash mid-session: protection until rejoin or session end; rejoining within 20 minutes does not consume the player's one-time protection.
- AI stand-in: players are told to pre-set AI behaviour (avoid declaring wars, seek fast peace, keep allies and rivals) "in the event they crash". If the player's AI declares war, the player can lose land even if protected.
- Substitutes: allowed with the original player's consent; substitutes "must follow the original player's plans as closely as possible".
- Hot-joins: scheduled (after each rehost, then hourly), with exceptional ones if an important player drops during a war.
- Other rulesets add: AI players (dropped or absent) may not be called into wars without consent; after a hot-join you may not declare on the dropped player's allies if the AI would not have joined; players AWOL for the first session, or any two sessions, are replaced permanently by a substitute or the AI. [community rulesets, snippet] — [HackMD ruleset (Chairswing)](https://hackmd.io/@Chairswing/rk3d2Pm4Y); [HackMD ruleset (efb)](https://hackmd.io/@efb-ruleset/SkyzjYq-w); [Steam group ruleset](https://steamcommunity.com/groups/Eu4MultiplayerSummer2015/discussions/3/530645446321206434)

**Complaints**
- Long-running Stellaris groups have no slow mode; the closest workaround one poster offered was the slowest speed with the game left running in the background. [forum, snippet] — [Steam Stellaris discussion](https://steamcommunity.com/app/281990/discussions/0/4203492762821134003)
- A Paradox forum thread on restarting after a pause describes a group that starts "below normal speed gradually building up speed if all players agree". [forum, snippet] — [Paradox forum: MP game speed](https://admin-forum.paradoxplaza.com/forum/threads/mp-game-speed.189251)

### Inferences
- The Paradox model is "one global clock at the pace of the slowest tolerated player". It scales badly with player count: more players means more pause requests and a lower sustainable speed. Communities cap it socially (minimum speed, restricted pause rights). For an uncapped-player text game, a single global real-time clock would be the wrong default.
- The valuable transferable pieces are the absence policies, which are all about protecting the absent player's stake without freezing the world: (1) a short grace window before anything changes, (2) a declared stand-in policy the player sets in advance ("avoid wars, seek fast peace"), (3) rules that others may not exploit the stand-in, (4) substitutes bound to the original player's plan, (5) scheduled re-entry points. A text role-playing game can make these engine rules: a dropped character goes into a safe "follows the party / stays put / finishes current task" posture chosen in advance, and the narrator may not put that character in new jeopardy.
- "Speed set by the slowest request" is, in a text game, simply "the scene does not advance past a point until the slowest present player has had a chance to act". The Paradox experience says this needs a bound (minimum speed, grace window), or the group "either crawls or leaves players behind".
- Fit: poor for the clock model itself; good as a source of drop-out and stand-in policy.

### Gaps
- The Paradox forum thread "Pauses and game speed in MP" returned HTTP 500 and was not read: [link](https://admin-forum.paradoxplaza.com/forum/threads/pauses-and-game-speed-in-mp.194985).
- I found no official (wiki or manual) statement of the default speed and pause rights in EU4, Stellaris, HoI4 or CK3; the forum answers conflict. Background knowledge, unverified here: in the Clausewitz-engine games any player can by default lower speed or pause while raising speed is effectively limited by the host or by the slowest client, and newer titles add host-only speed options and pause cooldowns.
- No source found in this session for Stellaris's behaviour when a player leaves (AI takes over the empire) or for its hot-join details.

---

## 3. Simultaneous planned turns ("WEGO"): Dominions, Diplomacy, Frozen Synapse, Laser Squad Nemesis, Combat Mission, Space Alert, Solium Infernum

### Takeaway
WEGO separates input from resolution: everyone writes orders against the same snapshot, then the host resolves all of them in a fixed, published phase order (with random order inside a phase where needed). It removes waiting and speed advantages, and its weak point is always the missing order: every game needs a deadline plus a defined default for "no moves received".

### Cited Findings

**Dominions (Illwinter): simultaneous orders, host resolves in a fixed sequence**
- "When a turn is hosted, all players' turn orders are resolved simultaneously" according to a published sequence of roughly 60 steps. Order of the major blocks: messages, research, recruitment, forging; rituals "cast in random order"; battles caused by rituals; assassinations; movement between friendly provinces, then movement into unfriendly provinces; main battle phase; events; admin (income, upkeep, unrest); victory check. [community wiki, fetched; tested 2022] — [Illwiki: Dominions 5 turn order](https://illwiki.com/dom5/turn-order)
- Conflict rules that fall out of the sequence: friendly movement resolves before hostile movement, so defenders can group before attackers arrive; if an intermediate province was taken in the magic phase, the army does not move; battles in the main phase occur in random order. [fetched] — [Illwiki](https://illwiki.com/dom5/turn-order)
- Ritual effects are processed before movement, so ritual attacks and assassins can kill a commander who was ordered to leave that turn (Dominions 4 page). [community wiki, snippet] — [Dominions 4 wiki (JP): Turn Resolution](https://wikiwiki.jp/dominions4/Turn%20Resolution)
- Hosting: the game has host options to generate a new turn and exit, and a host-time schedule option; third-party servers (Llamaserver) automate play by email. Most play-by-email games average one turn per day. [primary + snippet] — [Dominions 5 technical manual](https://www.illwinter.com/dom5/techmanual.html); [Wikipedia: Dominions 5](https://en.wikipedia.com/wiki/Dominions_5:_Warriors_of_the_Faith)

**Diplomacy: simultaneous secret orders, adjudication, deadlines, NMR and civil disorder**
- Johnson: Diplomacy is "the most successful asynchronous game" because all moves execute at once, so every player makes a decision every turn; sequential games (Risk, Carcassonne, Ticket to Ride) would "slow down to a painful crawl" if played asynchronously. But Diplomacy can stall if one player does not submit; the ideal asynchronous model progresses regardless of any individual. [primary, fetched] — [Johnson 2009](https://www.gamedeveloper.com/game-platforms/analysis-asynchronicity-in-game-design)
- No orders received: all of that player's units hold; retreats become disbands; when units must be removed, the unit furthest from a home supply centre goes first. [site rules, snippet] — [Backstabbr FAQ](https://backstabbr.com/faq); [MIT: Some Email Diplomacy Rules](https://stuff.mit.edu/~endeavor/Diplomacy/email_rules.html)
- Judge software: a power is marked CD (civil disorder) only after a grace period expires; then the phase is processed with incomplete orders. [primary, snippet] — [diplom.org Judge: deadline](https://diplom.org/Email/judge/deadline.html)
- House-rule spread: some leagues remove a player after two consecutive NMRs; others wait 24 hours, then seek a replacement and leave the power in CD until one is found; some GMs grant extensions on request and let orders be revised until the turn runs. [house rules, snippet] — [Octopus's Garden gunboat rules](https://burdonvale.nfshost.com/octopus/gunboat.html); [afpdip house rules](https://www.lspace.org/games/afpdip/files/murkyhs.html); [GT house rules](https://mainecav.org/diplomacy/gthr.html)
- Damage from missed turns: a Diplomatic Pouch author reports that in 10 online games he played, "EVERY game" was affected by a departing player, each with several turns of missed orders; a sudden collapse shifts the balance of power and rewards whoever happens to be adjacent. The CD removal formula ignores board position, so players must know it in advance to plan around it. [hobby zine article, fetched; anecdotal] — [Diplomatic Pouch: NMR/CD](https://diplom.org/Zine/S2013R/Hartl/nmrcd.htm)
- The newer rulebook edition adds a set civil-disorder removal procedure (do not remove a unit on a supply centre unless there is no option; start with the unit furthest from home). [forum, snippet] — [webDiplomacy forum: New Rulebook Edition](https://www.webdiplomacy.net/contrib/phpBB3/viewtopic.php?p=361025)

**Frozen Synapse / Laser Squad Nemesis / Combat Mission**
- Frozen Synapse: no time limit on planning; each player gives every unit waypoints, facing, stance and a default reaction; the player can simulate the turn against guessed enemy orders before committing; once all players commit, the server resolves about 5 seconds of action deterministically; each player takes turns at their own pace (asynchronous). [encyclopaedia, fetched] — [Wikipedia: Frozen Synapse](https://en.wikipedia.org/wiki/Frozen_Synapse)
- Laser Squad Nemesis: simultaneous turns, described by a commenter as "in some ways ... the best of both worlds". [forum, snippet] — [Hacker News comment](https://news.ycombinator.com/item?id=4899706)
- Combat Mission: both sides enter orders, then 60 seconds of action resolves for both at once. [forum, snippet; exact page not opened] — [Matrix Games forum post](https://forums.matrixgames.com/viewtopic.php?p=2954098)
- WEGO defined in the wargame literature: neither player knows what the other will do before committing; all orders for a window of game time resolve together. Criticism from one designer: simultaneous-move rules overhead gives too low a return compared with IGOUGO. [forum/blog, snippet; exact source page among these not confirmed] — [combatrules.com: Do we live simultaneously](https://www.combatrules.com/post/do-we-live-simultaneously); [Matrix: WEGO WWII Stalingrad dev diary](https://www.matrixgames.com/news/wego-wwii-stalingrad-dev-diary-1)

**Space Alert (co-op, real-time planning then resolution)**
- Co-op. A roughly 10-minute real-time "action round" in which players simultaneously program action cards onto personal boards, split into phases: when a phase's end is announced you can no longer change that phase's cards. Then a "resolution round" plays the cards step by step (turns 1 to 12) while threats advance. [encyclopaedia + rules summaries, snippet] — [Wikipedia: Space Alert](https://en.wikipedia.org/wiki/Space_Alert); [Order of Gamers rules summary](https://www.orderofgamers.com/downloads/SpaceAlert_v1.pdf)
- Reviewers flag "the disconnect between the planning phase and actually resolving all the actions". [review, snippet] — [I Slay the Dragon review](https://islaythedragon.com/game-reviews/its-time-to-panic-a-review-of-space-alert)

**Solium Infernum**
- All turns resolve simultaneously, "making for a more paranoid, less reactive style of play"; built for asynchronous play stretching over days or weeks; the 2009 original had a dedicated play-by-email following and the 2024 version keeps asynchronous matches for up to eight players. [press, snippet] — [PC Gamer on the reimagining](https://www.pcgamer.com/solium-infernum-is-getting-a-ground-up-re-imagining-from-the-creators-of-armello); [premortem.games interview](https://premortem.games/2024/02/07/to-hell-and-back-with-solium-infernum-by-league-of-geeks/)

### Inferences
- WEGO's essentials for a host-authoritative engine: (1) orders are written against one frozen snapshot; (2) the host resolves in a fixed, documented phase order; (3) ties inside a phase are broken by a rule (random in Dominions, "friendly before hostile" for movement); (4) an order whose precondition was invalidated earlier in the sequence fails cleanly (the Dominions army that "won't move"); (5) a missing order has a defined default (Diplomacy: hold).
- This fits the "together in one scene" case well: collect one intent per present player, resolve all at once in a fixed order, narrate once. It removes typing-speed advantage and the double move, and it matches what the play-by-post world independently arrived at (the GM "makes one post of 5 parts that addresses everyone's actions", see section 5).
- WEGO assumes a fixed quantum of game time per turn (5 seconds, 60 seconds, a month, a season). It does not by itself handle actions of very different lengths. An action that takes days has to be either split across many quanta or the quantum has to stretch to the shortest action in the batch. That is the gap the time-track model (section 7) fills.
- The Diplomacy record is the strongest evidence in this file that "wait for everyone" does not survive drop-outs: a deadline plus a harmless default is mandatory, and the default must be predictable so others can plan around it. For co-op the default should be protective ("hold", "follow", "keep doing what you were doing"), not punitive.
- The Space Alert complaint (plan and outcome feel disconnected) is a caution for a narrated game: a long gap between typing an intent and seeing its result weakens agency. Keep batches short.
- Fit: good for a shared scene with live players (short collection window, fixed resolution order, default for silence). Weak on its own for split parties and for mixed-length actions.

### Gaps
- No primary source found for Laser Squad Nemesis's or Combat Mission's turn rules (forum-level only), nor for Solium Infernum's exact order of resolution (background knowledge, unverified: a rotating "regent" token sets which player's orders resolve first each turn, and each player has a small number of order slots per turn).
- I did not find a canonical essay titled as a WEGO versus IGOUGO comparison; the definitions above rest on wargame forum and blog posts.

---

## 4. Real-time-over-days games: Neptune's Pride, Subterfuge, Travian/OGame-style browser games

### Takeaway
Games that let the world clock run in real time while players sleep produce one consistent complaint (things happen at 3 am; whoever checks most often wins), and designers answered with coarse ticks, turn-based variants with deadlines, scheduled future orders with a deterministic preview (Subterfuge's Time Machine), minimum action durations longer than a night's sleep, truces and vacation modes, and AI takeover after a fixed number of missed ticks or turns.

### Cited Findings

**Neptune's Pride (Iron Helmet)**
- Not truly real time: "everything happens in ticks. In a standard game a tick is 1 hour." Carriers move only at the end of a whole hour. [primary, snippet] — [Triton Codex FAQ](https://triton.ironhelmet.com/help/faq)
- Scale: a full game lasts a few weeks; a single jump takes "anything from 4 hours to an entire agonising day". The reviewer saw the slowness as a strength ("slow enough to feel intelligent") and noted you "can play it at the office". [press, fetched] — [Game Developer: The Icy Grandeur of Neptune's Pride](https://www.gamedeveloper.com/game-platforms/analysis-the-icy-grandeur-of-i-neptune-s-pride-i-)
- Turn-based variant: players submit, then the galaxy jumps a set number of ticks; games are advertised with a deadline and a jump size (example: "Turn Based, 48H Deadlines, 3 DAY Jumps"); if everyone submits early the jump fires early. One poster notes real-time games "actually run like turn based" because there are no partial ticks, and that turn-based games "allow players to get some sleep". [forum, snippet] — [Iron Helmet forum: 4D Chess game listing](https://forum.ironhelmet.com/t/4d-chess-6-turn-based-48h-deadlines-3-day-jumps/6395); [forum: fastest real time game speed](https://forum.ironhelmet.com/t/whats-the-fastest-real-time-game-speed/8922)
- Absent players: a player is switched to AI (AFK) after about 72 ticks of inactivity in real time, or 3 missed turn submissions in a turn-based game (user-reported figures). A developer post said the AI would not change existing orders or add new ones on the first missed turn; a later user reported the AI still altering orders. [forum, snippet] — [forum: When does someone turn into AI?](https://forum.ironhelmet.com/t/when-does-someone-turn-into-ai/1158); [forum: AI hijacking](https://forum.ironhelmet.com/t/ai-hijacking/5977)
- Complaints and changes: a forum user says the developer removed NP1's speed technology because players complained about unfairly losing their empire rapidly during sleep (second-hand). Another player: "there's no way to erase the pressure to/advantages of checking the game every hour". [forum, snippet] — [forum: Nostalgia for the original NP](https://forum.ironhelmet.com/t/nostalgia-for-the-original-np/6487); [forum: collected feedback from a newbie](https://forum.ironhelmet.com/t/a-bunch-of-collected-feedback-from-a-newbie/5320)

**Subterfuge (Ron Carmel, Noel Llopis)**
- Real time over about a week ("an average game lasts 7 to 10 days"). [encyclopaedia, snippet] — [Wikipedia: Subterfuge](https://en.wikipedia.org/wiki/Subterfuge_(video_game))
- Design goal: "Respect the player's time"; minimise time in the game. Stated problems: crucial things happen at 3 am, which favours whoever is awake; night alarms make the game a job; obsessive checkers beat players who check a few times a day. [primary, fetched] — [Game Developer: Quality of Life in Subterfuge](https://www.gamedeveloper.com/design/quality-of-life-in-subterfuge)
- Mechanisms: (1) the game is deterministic, so it can show the future from current knowledge; the player can act, "peek into the future to see if it produces the desired outcome", and undo. (2) The Time Machine lets the player scrub to a future moment and issue an order there as if it were the present (scheduled orders). (3) No "twitch" actions: anything resolving in under 8 hours (a sleep cycle) was treated as twitch and avoided; outposts are at least 10 hours apart at normal speed. (4) Specialist hires only at outposts, to prevent last-second changes. (5) Push notifications for anything important. [primary, fetched] — [Quality of Life in Subterfuge](https://www.gamedeveloper.com/design/quality-of-life-in-subterfuge)
- Limits: the preview only reflects what the player currently knows; hidden enemy subs make the prediction wrong. Scheduling depth is the paid feature (free accounts get a few queued orders). One designer had been getting up in the night to play Neptune's Pride, which the Time Machine was meant to prevent. [press, snippet] — [Kill Screen](https://www.killscreen.com/subterfuge-strategy-game-parents-and-busy-people/); [MCV: "We wanted to minimise the number of times per day a player has to check in"](https://www.mcvuk.com/we-wanted-to-minimise-the-number-of-times-per-day-a-player-has-to-check-in/)

**Travian, OGame-style persistent browser games**
- Johnson on the structural problem: in asynchronous persistent worlds zero-sum interaction is hard, because a player raided while asleep gets no chance to respond; Travian's Cranny (hides resources from raids) is a patch that he calls self-defeating; he recommends parallel competition (races) over direct attack. [primary, fetched] — [Johnson 2009](https://www.gamedeveloper.com/game-platforms/analysis-asynchronicity-in-game-design)
- Operator-side tools: Travian vacation mode protects villages but cannot be entered while attacking or under attack, and suspends inactivity deletion; truces make attacks landing in the window do nothing ("only submit greetings"); Travian Kingdoms birthday worlds had a nightly no-attack window from midnight to 8 am. [primary, snippet] — [Travian support: truce](https://support.travian.com/en/support/solutions/articles/7000065114-truce); [Kingdoms support: vacation mode](https://support.kingdoms.com/en/articles/179-vacation-mode); [Kingdoms birthday worlds](https://bday.kingdoms.com/2021/)

### Inferences
- These games show what happens if "the persistent world keeps running while a player is away" is taken literally: the absent player loses things with no chance to respond, and attention becomes the winning resource. For a co-op narrated game the lesson is that world time should not advance against a character whose player is not there to act, or should advance only in ways that are safe for that character.
- Subterfuge's three ideas transfer well and are independent of each other: (a) no consequential event may resolve faster than a player can reasonably respond; (b) long actions are scheduled in advance and the engine carries them out; (c) because the engine is deterministic, it can preview "where will I be when my long action ends" before the player commits. In a text game (c) is a cheap engine feature: "this will take until dusk; the others are currently at mid-morning."
- Neptune's Pride's turn-based variant ("advance by a fixed jump when all have submitted or the deadline passes, whichever is first") is the standard reconciliation of live and absent players and appears again in play-by-mail and Diplomacy. The "all submitted, so jump now" shortcut is what keeps a live session fast.
- AI takeover after N missed turns, with the stated intent that the stand-in does not overwrite the player's standing orders on the first miss, matches the Paradox "pre-set AI posture" idea. The complaint thread about the AI changing orders anyway shows players care most that the stand-in does not act against their plan.
- Fit: the real-time clock itself fits poorly (sessions are live, not week-long). Scheduled long actions, a preview of time cost, a floor on how fast harm can arrive, and "jump when all ready or at deadline" fit well.

### Gaps
- The Neptune's Pride official help pages did not render for fetching; all tick, deadline and AFK numbers above are from forum posts or search excerpts and should be treated as approximate.
- No OGame-specific source was found (vacation mode rules, fleet-save culture, complaints). No player complaint threads about sleep in Travian were found, only the operators' tools.
- Subterfuge's exact free-versus-paid queue limit and its handling of resigned players were not sourced.

---

## 5. Play-by-post and play-by-mail role-playing games, moderated PBM, forum "nation games"

### Takeaway
Human moderators of asynchronous role-playing games converge on the same practices: a stated posting cadence, a hard deadline after which the moderator "forges ahead" with defaults for the silent, one combined update answering everybody at once, and free splitting of the party into subgroups that each run at their own pace; the shared calendar is advanced by the moderator in whole "updates" whose in-world length is whatever the moderator declares.

### Cited Findings

**Play-by-post role-playing games**
- "It is much easier to split the party into various groups and have the GM run multiple groups simultaneously" in play-by-post than at a table; the author describes characters in a forum game quickly breaking into smaller groups pursuing their own goals. The GM can "make one post of 5 parts that addresses everyone's actions". Typical minimum cadence "once per day"; for dungeon crawls "one exploration turn per day"; about 15 to 20 minutes a day per player; a game can be declared "on pause on weekends". In combat each character states a default behaviour (an archer who stays back and shoots) and the GM runs most of the fight. [blog, fetched] — [Gorgon Bones: Play-by-post gaming, some notes and advice](https://gorgonbones.bearblog.dev/play-by-post-gaming-some-notes-and-advice/)
- "The post frequency of a pbp game tends to slow down to the post frequency of the slowest user." [forum, snippet] — [GamersPlane: Posting Rates as Expectations](https://gamersplane.com/forums/thread/22612?p=1046469)
- A GM who split the party into mini-groups and adjusted encounters reported that it "accelerated progress", while keeping one shared XP counter split equally. Another found that differing post frequency made coordinated party action very slow and moved to independent solo mini-quests. [forum, snippet] — [Paizo: Running a PbP AP faster](https://paizo.com/threads/rzs2mixs); [Reddit mirror: PotA play by post](https://reddit.birdcat.cafe/r/ElementalEvil/comments/1i89eqi/pota_play_by_post)
- Common cadence norms: 3 to 5 posting rounds a week; or one relevant post a day with one or two skipped days tolerated; "regularity, not speed, of posting seems to be the thing that keeps people in PbP games". [forum, snippet] — [GamersPlane: Fast Paced Play By Post](https://gamersplane.com/forums/thread/22065); [Paizo: What makes a successful play-by-post game](https://paizo.com/threads/rzs2ritb)

**Play-by-mail (commercial and moderated)**
- Orders must arrive before a deadline for each game turn; the interval between turns varies by game; gathering all players' turn cards and processing them at the same time gives simultaneous action for all players. [reference pages, snippet] — [Epistoludisme: Play-by-mail overview](https://epistoludisme.com/en/playbymail.php); [Wikipedia: Play-by-mail game](https://www.Wikipedia.com/wiki/PBEM)
- Cook on play-by-mail as an architecture: long response windows suit text and friend-based play; players are impatient and turn-based blocking can stall a game; the mitigation is to run about T/W games in parallel (response time over desired wait) so a turn is always arriving. [primary, fetched] — [Cook, "What I've learned about designing multiplayer games so far"](https://www.gamedeveloper.com/design/what-i-ve-learned-about-designing-multiplayer-games-so-far)

**Forum nation games (CivFanatics "NES"/"IOT" tradition and similar)**
- The moderator advances a shared calendar in "updates": one ruleset says each update "may consist of many years, perhaps even centuries"; another fixes "1 IRL Day = 6 months"; another "each Turn represents one In-Game Month". [forum, snippet] — [CivFanatics: A few questions about running a NES](https://forums.civfanatics.com/threads/a-few-questions-about-running-a-nes.633072/latest); [Supremacy forum: WW2 Roleplay rules](https://www.playsupremacy.com/en/forums/call-of-war-1942/call-of-war-1942-roleplaying/ww2-roleplay-rules-7d1c7542); [Clash Legends FAQ](https://sites.google.com/site/clashlegends/faq)
- Missed orders: a moderator states that at the deadline "if ... I do not have the entirety of the necessary orders I will forge ahead with the update regardless"; one ruleset applies in-world penalties (corruption, stagnation, instability); another moderator notes it is "VERY hard for a mod if people skip orders" because the mod must invent the missing orders without conflicting with neighbours; a stricter game assumes the government has collapsed; one bans after 3 days of unannounced inactivity. [forum, snippet] — [CivFanatics: Revolution IOT](https://forums.civfanatics.com/threads/revolution-iot.509081/page-7); [CivFanatics: NukeNES](https://forums.civfanatics.com/threads/nukenes-one-last-try.217343/page-9); [CivFanatics: LONES](https://forums.civfanatics.com/threads/lones-dawn-over-a-new-world.369102/page-6)

### Inferences
- Play-by-post practice is the closest precedent to the target game and its moderators chose, without theory: per-subgroup pacing (each split group advances on its own), batch resolution inside a subgroup (one combined post), defaults for the silent (stated default combat behaviour; "forge ahead"), and a calendar owned by the moderator.
- What play-by-post does not do rigorously is keep split groups' clocks consistent. A human GM lets group A play out an afternoon while group B plays three days, then hand-waves the reunion. A host-authoritative engine cannot hand-wave: it needs a rule for what happens when a character whose clock reads day 3 walks into a place where another character's clock reads day 1. This is the specific problem that the time-track model (section 7) solves by construction, and the play-by-post record does not.
- The moderator's hardest job in nation games (inventing orders for the absent without contradicting others) is the same job as a stand-in AI. The cheapest safe answer in the record is "no action": hold, or continue the last declared activity.
- "Regularity, not speed" suggests that predictable cadence matters more to retention than raw pace; a visible indication of whose input the scene is waiting on, and for how long, would serve the same purpose in a live session.
- Fit: very high as a source of practice; the missing piece is a formal rule for clock consistency between split groups.

### Gaps
- I found no source describing the turn structure of Legends (Midnight Games / Harlequin Games) or other specific moderated PBM games (Hyborian War, Monster Island, Middle-earth PBM). Background knowledge, unverified here: such games process all positions on a fixed real-world cycle (commonly two weeks), run each position's order list through a fixed phase sequence, and treat a missed turn as "no orders" or run standing orders.
- No source was found that states how play-by-post GMs formally reconcile different elapsed times between split groups; the practice appears to be informal.
- Skipping an absent player in initiative, and "post order is initiative order" versus group initiative, are common play-by-post practices I could not source in this session.

---

## 6. Asynchronous multiplayer design patterns: sync, async and in-between (Cook, Johnson)

### Takeaway
The literature treats synchrony as a spectrum set by how often players must exchange interactions and how long a reply may take; the two recurring recommendations are to prefer drop-in/drop-out "rooms" that still work with one player over fixed matches, and to prefer parallel or co-operative interaction over zero-sum interaction when players are not present together.

### Cited Findings
- Cook's definitions: an interaction is any moment players affect one another through a game system. Real-time: interactions overlap and a player perceives the response before moving on. Asynchronous: a player acts, leaves, and sees the response later; this requires persistence. Which mode players perceive depends on interaction frequency: a strategy game like Civilization might need contact about every five minutes, a twitch shooter about every 200 ms; chat can feel real-time even with long gaps. [primary, fetched] — [Cook 2014](https://www.gamedeveloper.com/design/what-i-ve-learned-about-designing-multiplayer-games-so-far)
- Cook's degrees of interaction: parallel (independent, like ghost racers), zero-sum (one player's gain blocks another), non-zero-sum (one player's gain helps others). [fetched] — [Cook 2014](https://www.gamedeveloper.com/design/what-i-ve-learned-about-designing-multiplayer-games-so-far)
- Cook's three architectures and their costs: match-based ("immensely problematic": narrow matchmaking window, late arrivals wait); room-based (persistent spaces players join or leave at any time; "join/leave in progress keeps average population steady"; rooms must work for one player because of the "remainder" problem; trade-off: synchronised starts are lost and players at different progress levels need handling); asynchronous (play-by-mail, visiting, ghosts). Recommendations: prefer room-based over match-based; build persistence because it enables asynchronous interaction; prototype at low population density. [fetched] — [Cook 2014](https://www.gamedeveloper.com/design/what-i-ve-learned-about-designing-multiplayer-games-so-far)
- Cook on group size: 2 players enable trade and co-operation; 3 to 4 alliances; 5 and up group-versus-group and leadership; 40 and up hierarchy; above roughly 150 to 250 people become abstractions. [fetched] — [Cook 2014](https://www.gamedeveloper.com/design/what-i-ve-learned-about-designing-multiplayer-games-so-far)
- Johnson: asynchronous play lets players experience a multiplayer game in "bite-sized chunks at different times for each player"; anyone who can find time for synchronous games can find time for asynchronous ones, but not the reverse. Asynchronous play favours mechanics that minimise waiting (simultaneous turns) and a clock that progresses regardless of any individual (fantasy sports score daily whether or not you log in). Strong zero-sum mechanics undermine the scheduling freedom that asynchrony offers; resolving conflict automatically (Duels) preserves conflict but turns it into a "black box" that takes control away from the player. Designers should stop "retrofitting synchronous mechanics into an asynchronous shell". [primary, fetched] — [Johnson 2009](https://www.gamedeveloper.com/game-platforms/analysis-asynchronicity-in-game-design)
- A simple framing from a third author: in an asynchronous loop the reaction comes from the game itself; in a synchronous one it depends on other players. [opinion piece, snippet] — [Game Developer: Synchronous or asynchronous gameplay](https://www.gamedeveloper.com/design/opinion-synchronous-or-asynchronous-gameplay)
- Cook's "Loops and Arcs" (Lost Garden, 2012): loops build mastery through repetition; arcs are single self-contained experiences, and a sequence of arcs creates a content treadmill. [secondary summary only, snippet] — [Bilibili repost/summary](https://www.bilibili.com/read/cv43709102)

### Inferences
- The target game is a "sometimes-sync" room in Cook's terms: live, join and leave in progress, must work with one player. His listed cost of rooms (players at different progress levels need handling) is, in this game, literally players at different points in game time.
- Mapping Cook's degrees onto the two situations: characters apart in the persistent world are in parallel interaction (each player's reaction comes from the engine, so they can run asynchronously at their own speed, as in Johnson's and the opinion piece's framing); characters together in a scene are in non-zero-sum real-time interaction and need a synchronisation rule. So the design needs two regimes and a clean hand-over between them, which is what Civ's hybrid mode attempted for peace and war.
- Johnson's "black box" warning applies to resolving an absent player's actions automatically: acceptable for safe continuation, not for decisions that matter.
- Combined model table (inference from all sections):

| Model | Clock | Order inside a step | Slow/absent player | Handles mixed-length actions | Fit for shared scene | Fit for split party |
|---|---|---|---|---|---|---|
| Sequential IGOUGO (classic Civ, PBEM) | per turn | fixed seat order | everyone waits | no | poor (waiting) | poor |
| Shared-turn free-for-all (Civ simultaneous) | per turn | first click wins | timer ends turn | no | poor (typing race, double move) | poor |
| Hybrid (Civ V/VI) | per turn | free in peace, alternating in conflict | timer | no | good as a pattern | n/a |
| Global pausable real time (Paradox) | continuous, one speed | real time | AI stand-in, protection rules | yes (durations) | poor above a few players | poor (one clock for all) |
| WEGO (Diplomacy, Dominions, Frozen Synapse) | fixed quantum | host phase order, random ties | deadline + default orders | weak (fixed quantum) | good | weak alone |
| Real time over days (Neptune's Pride, Subterfuge) | wall clock in ticks | tick order | scheduled orders, AI after N misses | yes (durations) | n/a | poor (harms the absent) |
| Time track (Thebes, Tokaido, Patchwork, Red November) | per-player position on one timeline | furthest back acts next | needs a rule (see section 7) | yes, natively | good | good |
| Tick initiative (Hackmaster, Exalted 2e, Feng Shui) | per-combatant next-action time | lowest next-action time acts | GM skips/acts for them | yes, natively | good in combat | n/a |

### Gaps
- Cook's original "Loops and Arcs" essay on Lost Garden was not opened; only a secondary summary was seen, and it does not address time or turn order directly.
- I found no Designer Notes (Soren Johnson) article specifically about simultaneous turns or multiplayer pacing in Civilization IV beyond the 2009 asynchronicity column; the podcast has an episode touching on why Frozen Synapse uses simultaneous turns, not read here.
- No Raph Koster writing on asynchronous time was located in this session.
- The term "sometimes-sync" was not found in a source; treat it as the brief's own label.

---

## 7. The time-track mechanic (Thebes, Tokaido, Patchwork, Glen More, Red November): each action costs time, the player furthest back acts next

### Takeaway
A time track replaces rounds with one shared timeline on which each player has a position; every action advances only the actor by its time cost, and the player furthest back always acts next, taking consecutive turns for as long as they remain last. It natively handles actions of different lengths and keeps all players' clocks mutually consistent, but in its tabletop form it is strictly one actor at a time and has no built-in answer for a player who stops acting.

### Cited Findings

**Core rule and origin**
- General definition: "a mechanic where the person who is furthest behind will always be the next person to take their turn"; thematically, more time has elapsed for the players furthest ahead. [glossary, snippet] — [Delaware library board game glossary: time track](https://sites.google.com/a/delawarelibrary.org/boardgames/glossary/time-track); catalogued as "Turn Order: Time Track" — [Spielbound taxonomy](https://www.spielbound.org/taxonomy/term/1514)
- Credited origin: Peter Prinz's Thebes (earlier self-published as Jenseits von Theben); popularised about ten years later by Uwe Rosenberg's Patchwork, who reused it in Nova Luna. Variations appear in Glen More, Glen More II, AuZtralia, Rocky Road a la Mode, Tokaido, PARKS and High Rise. A 2004 game, Neuland, had something similar in which players spent actions and moved that many spaces. [article, fetched] — [Meeple Mountain: Games We Love, Thebes](https://www.meeplemountain.com/articles/games-we-love-thebes-you-and-me-going-digging-by-the-sea/)

**Thebes in detail** [article, fetched] — [Meeple Mountain: Thebes](https://www.meeplemountain.com/articles/games-we-love-thebes-you-and-me-going-digging-by-the-sea/)
- The track has 52 spaces, one per week of a year, and loops; games last 2, 2.5 or 3 years by player count.
- Every action is priced in weeks: travel costs 1 week per route segment and is folded into the cost of whatever is done on arrival; a research card costs travel plus the weeks printed on it; an excavation costs travel plus however many weeks the player chooses to invest (more weeks, more finds); repeating the "refresh display" action costs 1, then 2, then 3 weeks.
- Turn order: the marker furthest back acts next. Ties on the same space: the marker on top (the one that arrived later) goes first. A player still furthest back after acting acts again immediately (example: moving from week 20 to 22 while everyone else is beyond 22).
- Calendar events hang off positions on the track: passing week 52 starts that player's new year and resets their once-per-year dig permits; the shared year marker advances when the last player crosses week 52.
- The author's praise: one device sets game length and turn order together and ties both to the theme of travelling archaeologists.

**Tokaido**
- The traveller furthest back on the road takes the next turn; if still last after moving, that traveller goes again immediately; a FAQ confirms a player can move twice in a row. [official rules host, snippet] — [Dized: Tokaido, playing the game](https://rules.dized.com/game/Bnz3BSthQUyJotDtJ_mG8w/rm_f3ZqyR2SYlUEmOlkzrw/playing-the-game); [Dized: Tokaido FAQ](https://rules.dized.com/game/Bnz3BSthQUyJotDtJ_mG8w/faq)
- The road has mandatory inns where all travellers stop, and a FAQ entry addresses skipping spaces to move further along the road (a big jump forward is allowed and trades turns for position). [official rules host, snippet] — [Dized: can I skip spaces](https://rules.dized.com/game/Bnz3BSthQUyJotDtJ_mG8w/qvg0-ttCSd-reaTkGHvelA/can-i-skip-spaces-to-move-further-along-the-road)

**Patchwork**
- Same mechanism; moving past the opponent on the time board hands them the turn; passing marked spaces on the track pays income; a marker on top of a stack goes first. Described as "arguably the game where the time track mechanic REALLY caught on". [mechanism page and article, snippet/fetched] — [Meeple Mountain: board games using Time Track](https://www.meeplemountain.com/mechanisms/time-track); [Meeple Mountain: Thebes](https://www.meeplemountain.com/articles/games-we-love-thebes-you-and-me-going-digging-by-the-sea/)

**Red November (co-op, time track in minutes)**
- Co-op. Each gnome has a "Time Keeper" on a 60-minute track; "the player whose Time Keeper is furthest back in time takes the next turn". Every action costs minutes. For a repair the player chooses how many minutes to spend, up to 10: more minutes means a better chance, and 10 minutes is an automatic success. [rules + blog, snippet/fetched] — [UltraBoardGames: Red November rules](https://www.ultraboardgames.com/red-november/game-rules.php); [Hiew's Boardgame Blog: Red November](http://hiewandboardgames.blogspot.com/2009/09/red-november.html)
- World events are attached to the timeline, not to rounds: after acting, the player draws one event card for each star space their marker passed; timed disasters sit at fixed minutes on the track and trigger when a marker passes them; the group wins by surviving until the track runs out. [blog, fetched] — [Hiew's Boardgame Blog](http://hiewandboardgames.blogspot.com/2009/09/red-november.html)
- Design consequence noted by a reviewer: the more you do in a turn, the more stars you pass and the more events you flip, "a nice bit of strategy and balance, as you choose between more actions and fewer, more appropriate ones". [review, snippet] — [Jesta ThaRogue: Red November first impressions](https://www.jestatharogue.com/tabletop-games/gameday-play-red-november/)

**Known properties (stated in the sources above)**
- Consecutive turns for whoever stays last: explicit in Thebes and Tokaido.
- Variable-length actions are native: Thebes digs and Red November repairs let the player choose the duration and get more for more time.
- One timeline serves three purposes at once: turn order, game length, and the schedule of world events (Thebes year rollover; Red November stars and timed disasters).
- Tie-break is needed and is conventionally "last to arrive acts first" (stacking).

**Complaints**
- I did not find, in this session, a forum thread or review that criticises the time-track mechanism as such. The Red November blogger called the game merely "alright" for other reasons (luck of disaster timing after the deck reshuffle). [blog, fetched] — [Hiew's Boardgame Blog](http://hiewandboardgames.blogspot.com/2009/09/red-november.html)
- A general downtime essay (not about time tracks) argues that single-action turns create an uneven rhythm of waiting through other players' turns and that designers over-correct against downtime. [blog, snippet] — [The Thoughtful Gamer: Downtime isn't a four-letter word](https://thethoughtfulgamer.com/2022/04/04/downtime-isnt-a-four-letter-word/)

### Inferences
- Why it is a direct candidate: it is the only model in this file that (a) prices each action in game time, (b) allows actions from seconds to days on one scale, and (c) guarantees that no player ever acts "in the past" of anything already resolved, because the actor is always the one whose clock is earliest. Property (c) is exactly the consistency guarantee that play-by-post GMs lack when split groups reunite (section 5). It is the same invariant as a discrete-event simulation: always process the pending event with the smallest timestamp.
- Mechanical properties that follow from the rule (my analysis, not from sources):
  - A long action is a big jump forward and then a long wait in real time while everyone else catches up. A character who "travels for three days" will not act again until every other active character has also reached that point. In a live session that is real waiting, and it is the model's main cost. Red November softens it by keeping the whole track short (60 minutes); Thebes by making long actions the rewarding ones.
  - Short actions give many consecutive turns. In a scene, a player taking six-second actions next to a player taking a ten-minute action will act many times in a row. That is correct in fiction but can read as one player hogging the scene; tick-initiative players made exactly this complaint about Feng Shui and Scion (section 8).
  - The actor order is strictly serial. With many players this is a queue. The fix available to a computer host that a board game lacks: characters who cannot affect each other before their clocks meet (different locations, no shared resources) can be resolved concurrently, each on a private clock, and only need ordering when their timelines could interact. The time track then only has to be enforced per location or per interacting group.
  - World events attached to the timeline (Red November's stars, Thebes's year rollover) raise a question the board games answer differently: does a world event fire when the first marker passes its time, when each marker passes it (Red November: per marker), or when the last marker passes it (Thebes's year marker: last player)? For a persistent shared world, "when the last active clock passes it" is the only choice that keeps the world consistent for everyone, and it means the world's own clock is the minimum of the active characters' clocks.
  - The model stalls on an absent player exactly like sequential turns do: if the furthest-back player stops acting, nobody behind them exists to move the minimum forward, and strictly nobody else may act. Board games never face this. The engine needs an explicit rule, and the other sections supply candidates: a response window, then an automatic "wait/hold" action that advances the silent character's clock to the next player's time (Diplomacy's "hold"; play-by-post's "forge ahead"), or removal of a disconnected character's marker from the ordering with a safe stand-in posture (Paradox rulesets).
  - Reunion is well defined: a character at day 3 arriving where another is at day 1 simply cannot act there until the day-1 character's clock reaches day 3, or the engine treats the arrival as an event scheduled at day 3 on that location's timeline. Either the traveller waits in real time, or the engine offers the earlier character a "pass time until the other arrives" action. Subterfuge's preview idea (section 4) is the natural companion: show the time cost and who is where on the timeline before the player commits.
  - Voluntary waiting has to be a first-class action ("I wait for the others", "I keep watch until something happens"), otherwise a player who wants to stay with a group whose clocks are ahead has no way to join them. Tokaido's big-jump option and Thebes's choice of how many weeks to dig are the board-game analogues.
- Fit: the best structural fit of the models surveyed, provided it is extended with (1) concurrency for characters whose timelines cannot interact, (2) a rule for silent or disconnected players, (3) a first-class wait/sync action and a time-cost preview, and (4) a decision on whether co-located players act strictly furthest-back-first or are batched WEGO-style when their clocks are within a small window of each other.

### Gaps
- The BoardGameGeek mechanism page for Time Track and BGG forum threads were not retrieved (two searches returned nothing BGG-specific), so "what players complained about" for this mechanic is thin. Background knowledge, unverified here: commonly voiced complaints are that Tokaido with few players becomes a blocking game about leaving the last player bad spaces; that in Patchwork the consecutive-turn rule is the core skill and confuses new players; and that time tracks produce uneven downtime because a player who jumps far ahead may sit out a long stretch.
- Geoffrey Engelstein and Isaac Shalev's "Building Blocks of Tabletop Game Design" has an entry on time-track turn order that would be the standard design reference; it was not accessed.
- Glen More's exact rule was not sourced beyond its listing as a time-track variant (background, unverified: players move along a circular tile track, the last player in line takes any tile ahead and jumps to its space, and players who took fewer tiles are compensated at scoring).
- The Red November rule on consecutive turns and on moving and acting within one turn's time budget was not confirmed from the rulebook itself.

---

## 8. Tick and count-up initiative in tabletop role-playing games (Hackmaster, Aces and Eights, Exalted 2e, Scion, Feng Shui, others)

### Takeaway
Several tabletop role-playing games replaced rounds with a running count on which each action schedules the actor's next action (the time-track idea applied to combat). Players who liked them praised flow, realism and unpredictability; players who disliked them cited bookkeeping, a "gamey" feel, the need for constant attention, and fast characters acting several times while slow ones sat idle.

### Cited Findings

**Hackmaster (Basic/5e) and Aces and Eights (Kenzer and Co.): count-up in seconds**
- "The system abolishes turns and starts combat at the first second and moves second-by-second." Starting count from a d12 plus initiative modifier (higher is worse); a smaller die when one side has the drop. After an attack, weapon speed sets when that character can attack again ("large weapons have high weapon speeds taking 10 or more seconds"). Movement happens second by second. [review, fetched] — [Gnome Stew: Hackmaster Basic review part 2, combat](https://gnomestew.com/hackmaster-basic-review-part-2-combat)
- There are no fixed rounds: with weapon speed 10 and an attack on count 7 the next attack is on 17, but the character can still do something else earlier (move away on count 8), and can parry, move or fight defensively between attacks. Players can change their declared action at any time, which restarts its timing. [review comments + forum, fetched/snippet] — [Gnome Stew](https://gnomestew.com/hackmaster-basic-review-part-2-combat); [EN World: Hackmaster Basic](https://www.enworld.org/threads/hackmaster-basic.267802/)
- Reception: "a flowing battle that lacks the predictability of traditional turn-based combat"; "the Count Up initiative was a lot of fun to use"; but "the bookkeeping for the overall count and the current count for all 5 combatants was a bit tricky", and count-up is "likely to be the hardest part of the combat system to master". Aids: a whiteboard or printed count board; a commenter says it "does get easier as you go" and reports six characters versus five or six monsters in about 15 minutes. [review, fetched] — [Gnome Stew](https://gnomestew.com/hackmaster-basic-review-part-2-combat)
- Hackmaster's count-up was adapted from the system Kenzer first used in Aces and Eights. A common table practice: players track their own counts, the GM tracks monsters, and a player who misses their count loses it ("tough"). [forum, snippet] — [EN World: Hackmaster Basic](https://www.enworld.org/threads/hackmaster-basic.267802/); [EN World: Initiative, second by second](https://www.enworld.org/threads/initiative-second-by-second.335397/)

**Exalted 2nd edition and Scion (White Wolf): ticks**
- One-second ticks; most characters act every three to six ticks; a Join Battle roll sets the start, with everyone else starting (difference in successes) ticks after the best roller, capped at 6. [review, snippet] — [RPG.net review of Exalted Second Edition](https://www.rpg.net/reviews/archive/18/18790.phtml)
- A playtester view: "it's not as much work as you might think as 90% of all actions take 5 ticks to complete". [forum, snippet] — [The RPG Site thread](https://therpgsite.com/index.php?msg=16122)
- Complaints: the tick system "was one of the things that killed 2nd Edition Exalted" for one poster; it felt "gamey and mechanical after the free-form initiative of 1st Edition". Another calls tick-based combat a pain and sometimes just uses the Join Battle result as a fixed turn order. A late joiner is compared against the original reaction count, so joining is slower if the initial winner was fast, even if that character has left the fight. [forum, fetched/snippet] — [EN World: Tick-based initiative systems, what are your experiences?](https://www.enworld.org/goto/post?id=4683864); [EN World, later post](https://www.enworld.org/goto/post?id=4715756)
- Scion: no rounds, a circular tick wheel; praised because "minor actions fit into the same time as major ones" and for its interaction with movement; criticised because it "requires players to pay a lot of attention", can leave some players "feeling left out or superfluous", and requires knowing tick modifiers. Verdict from one poster: "It works, which is the ultimate goal". [forum, fetched] — [EN World thread](https://www.enworld.org/goto/post?id=4683864)

**Feng Shui (shots; a count-down that resets each sequence)**
- A fight is split into sequences and shots. Each sequence everyone rolls initiative (one die plus Speed); the highest result is the shot on which the sequence starts; the count runs down to shot 1 and then a new sequence begins with new rolls. Acting lowers your own shot value by the action's cost, usually 3; simple actions can cost 1. "Keyframe" durations last until the same shot of the next sequence. At shots 2 and 1 a character may still take a 3-shot action with no carry-over debt. [rules briefing + blog, snippet] — [Feng Shui sequence and shots briefing](https://www.eyrie.org/~robotech/fengshui/shui-sequence.html); [The Alexandrian: Feng Shui, using the shot counter](https://thealexandrian.net/wordpress/43593/roleplaying-games/feng-shui-using-the-shot-counter); [Wikipedia: Initiative (role-playing games)](https://en.wikipedia.org/wiki/Initiative_(role-playing_games))
- Complaint: a base cost of three is small, so fast characters could act two or three times before an average character, leaving the slower player with little to do. [forum, fetched] — [EN World thread](https://www.enworld.org/goto/post?id=4683864)
- Table aid: a single shared shot-counter board with a token per character. [blog, snippet] — [The Alexandrian](https://thealexandrian.net/wordpress/43593/roleplaying-games/feng-shui-using-the-shot-counter)

**Others**
- Arduin is cited as one of the first games with tick initiative; a poster who adapted it to several D&D versions calls it "a more realistic way to handle acting order in combat" but notes it requires players to stay more engaged. A D&D 3.x tick house rule "feels faster-paced, whether it is or not". Deadlands (cards from Ace down, actions cost cards) is praised because the cards are "an excellent visual reminder". [forum, fetched] — [EN World thread](https://www.enworld.org/goto/post?id=4683864)

### Inferences
- These systems are the time track applied at a scale of seconds, and the player reports are the best available evidence of how the time-track mechanic feels in a role-playing game. The three recurring complaints each have a direct counterpart in a text game run by a computer:
  - Bookkeeping: this is the dominant complaint, and it disappears when the engine keeps the count. The mechanic's main tabletop cost is one a host-authoritative engine does not pay.
  - "Gamey and mechanical": the count was visible and constantly referenced at the table. In a narrated game the count can stay in the engine, with the narration expressing order and duration in words. The lesson is to keep the timeline out of the player's face except where it informs a decision (time-cost preview).
  - Idle slow characters and attention load: a real design risk that the engine does not remove. Feng Shui shows the failure case (cheap actions let fast characters lap slow ones); Exalted shows the mitigation (most actions cost about the same, so order stays close to round-robin). For a text game this suggests that within one scene most actions should fall into a few coarse duration bands, with long outliers explicitly flagged, so that co-located players get roughly alternating turns.
- Hackmaster's "change your action any time, which restarts its timing" is a useful rule for long actions: a character committed to a ten-minute task is not locked out of the scene, but interrupting forfeits the progress or the timing. That answers the time-track's "big jump then long wait" cost: the jump is provisional until the clock actually gets there.
- Exalted's late-joiner oddity (join time computed from a stale reference) is the tabletop version of the hot-join problem: a character entering a running timeline needs a well-defined entry time. The clean rule is "enter at the current minimum (or the scene's current time) plus an entry cost", not relative to anything historical.
- Feng Shui's per-sequence reset is a hybrid of rounds and ticks: it bounds how far anyone can get ahead (at most one sequence). A bounded window of this kind is one way to cap the wait caused by a big jump.
- Fit: high for scene-level and combat ordering, with the engine doing the counting, coarse duration bands, interruptible long actions and a defined entry time for joiners.

### Gaps
- Phoenix Command was not researched in this session (background knowledge, unverified: it uses very short phases with per-weapon action counts and is widely cited as too slow to run by hand).
- No rulebook text was consulted for Aces and Eights or Exalted 2e; mechanics above rest on reviews and forum descriptions.
- Complaints specifically about Exalted's physical "battle wheel" aid were not found.
- I did not find posts discussing tick initiative in play-by-post or online text play specifically, which would be the closest analogue to the target game.
