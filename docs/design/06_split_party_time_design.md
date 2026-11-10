# 6. Design: time when players split up

Status: a proposal for the owner. It answers the open question in GOALS.md: "how does time work when players separate (one player
fighting while another travels for days, sleeping while another fights)?" It serves the multiplayer decisions of 2026-11-03 (a shared
campaign, players who split up and reunite, each player's model calls on their own card) and pillar 1 (the world keeps moving).

## What older designs teach

| Source | What it did | What we take |
|---|---|---|
| Gygax, AD&D DMG (1979) | "YOU CAN NOT HAVE A MEANINGFUL CAMPAIGN IF STRICT TIME RECORDS ARE NOT KEPT": a time record **per character**. The referee calls a halt when one group gets too far ahead | Each character has its own clock; there's a limit on how far apart clocks can get |
| West Marches (Ben Robbins) and its timekeepers | Groups' timelines **branch and fold back**: a group can't go somewhere another group's timeline already covers, and a group that's behind is brought **forward through downtime** when groups meet | Merging timelines when characters meet; a character behind catches up by spending downtime |
| Grognardia and others | When a group arrives where another already is, later in game time, **advance the group that's behind**, and narrate why ("the journey took longer") | Arriving somewhere moves your clock forward to that place's time, and the delay is narrated |
| Split-party GMing (the Alexandrian, Angry GM) | Don't keep the groups synced; cut forward and back; fix any contradiction with a small retcon. Game timekeeping is fuzzy enough to allow it | Precise ordering only where causality needs it (people, places, objects that were touched); fuzziness elsewhere |
| Baldur's Gate 3 co-op | Players roam freely and talk to NPCs separately; combat goes turn-based **for everyone, wherever they are**; the host's save is the authority | Avoid freezing everyone for one player's fight. Scenes and fights are local |
| Crusader Kings III multiplayer | One real-time clock; the slowest or lagging player sets the speed; nobody can play on alone | Avoid a single shared clock: it makes a talker wait for a traveller, or the reverse |
| Distributed simulation (Lamport clocks, conservative windows; general knowledge) | Ordering by "happened before"; a bounded window of how far ahead parts of the simulation can run | The rules for touching things, and the limit on how far ahead a player can get |

## The model in one paragraph
Every character carries **their own clock**. Every person, place, object and situation carries the **time it was last touched**.
- **Rule 1 (touch):** you can only act on something at or after the time it was last touched. If it's ahead of you, your clock moves
  forward to its time first, and the game narrates how that time passed.
- **Rule 2 (perceive):** you only see, hear or are told world facts dated at or before your own clock.
- **Rule 3 (window):** characters who are playing can't run more than a set amount of game time ahead of the slowest playing
  character.
- **The world catches up lazily**, place by place, when someone arrives (`pulse.catch_up` already works this way).
- **Characters together share one clock** (the party is one unit). Joining up means everyone moves forward to the latest clock among
  them.

The fiction never contradicts itself (nobody acts in someone else's past), nobody waits on anyone else for ordinary play, and the gap
between players stays bounded.

## Data (YAML in `data/rules/time.yaml`, checked at startup)
```yaml
window_days: 2            # rule 3: a playing character can't be more than this ahead of the slowest playing one
ask_jump_hours: 6         # rule 1: a forward move longer than this is asked about first (unless it's an arrival)
arrival_jump_free: true   # moving forward on arrival is narrated as the road taking longer; never asked about
offline_safe_kinds: [inn_room, home, guild_house, town]   # where a player who stops playing is "in downtime"
downtime_activities: [rest, work, train, craft, carouse, study]   # what a character behind spends a catch-up on
meanwhile_feed: true      # out of the story: a short line per major event of the other players (owner's choice)
```

## Storage changes (with doc 5's tables)
- `players.clock` (game minutes) per character. `CampaignMeta.minutes` becomes `frontier` (the slowest playing clock), used for
  cleanup and caps only.
- `touched_at` on `npcs`, `entities`, `threads`, and on each place's state. It's set to the actor's clock on every write. It never
  goes backward.
- `region_time` per settlement (the existing `pulse.town_of`): how far the world has been simulated there.
- Every world fact is already dated (`news.minute`, `deeds.minute`, `event_log.minute`, `effects.until`). Rule 2 filters queries on
  them.

## Pseudocode

```python
# engine/timeline.py (new): the only module that moves a character's clock
def act_at(scene, actor_id, targets: list[Ref]) -> int:
    """Before an operation: the clock the actor acts at, moved forward under rule 1, with the reason told."""
    me = clock_of(actor_id)
    ahead = max([touched_at(t) for t in targets] + [region_time(scene.place)], default=me)
    if ahead > me:
        gap = ahead - me
        if not scene.arriving and gap > T["ask_jump_hours"] * 60:
            return ask_jump(scene, actor_id, gap, why=targets)    # "Finding Aldric means letting 3 days pass..." (a question; the turn ends)
        spend_downtime(actor_id, me, ahead, how=scene.downtime_choice or "rest")   # heal, mana, needs, rent, and so on: what time does now
        narrate_jump(scene, actor_id, gap)                        # in the world's words; on arrival, "the road took longer than it should"
        me = ahead
    return me

def commit(op, actor_id, clock, targets):
    for t in targets:
        set_touched(t, max(touched_at(t), clock))
    set_clock(actor_id, clock + op.minutes)                       # what the action cost; travel, rest and fights advance it as now

def can_advance(actor_id, minutes) -> tuple[bool, str]:
    """Rule 3: a long action (travel, a long rest, crafting) that would carry this character past the window."""
    slow = min(clock_of(c) for c in playing() if c not in party_of(actor_id))
    over = clock_of(actor_id) + minutes - (slow + T["window_days"] * 1440)
    return (over <= 0, "" if over <= 0 else window_reason(over))

def perceive(actor_id, rows):
    """Rule 2: what this character can know: dated at or before their clock (news, rumours, the town's memory, the journal)."""
    c = clock_of(actor_id)
    return [r for r in rows if r.minute <= c]

def arrive(scene, actor_id, place):
    region = town_of(place)
    pulse.catch_up(region, to=clock_of(actor_id))                 # lazy: the world moves on here up to their time (existing code, per region)
    act_at(scene, actor_id, [place_ref(place)])                   # rule 1 if someone was here later: arrival makes up the difference
```

### Where it hooks in
- `scenes/world.py turn()`: work out `act_at` before the operation and `commit` after, per actor, using the TurnContext from the
  overhaul.
- `engine/clock.py`: `ws.minutes` reads the acting character's clock, not the campaign's.
- `pulse.catch_up(region, to)`: the existing catch-up, scoped to a region. Effects that cross regions (news travelling, a cataclysm
  spreading, follow-ons) are stored with their due time and applied when that region reaches it.
- **Every read of news, rumour or town memory goes through `perceive`:** `pulse.news_for`, `news_window`, `matters.town_memory`, the
  NPC brief (`engine/brief.py`), and the truth layer (`engine/truth.py`).
- **`travel` and `rest`:** check `can_advance` first. If it fails, the player gets in-world choices (below), not a block.

## Situations, from the player's side

### Splitting up
"I'll go to Elmshade; you take the ford." Each character leaves the party (the companion rules from the owner's decisions apply). From
then on each has their own clock. The `meanwhile_feed` (if on) gives each player a short line, out of the story, when another player
does something major ("Bryn fought the river wyrm at the ford"). In the world, word only arrives through the news system, which travels
at road speed. So the information asymmetry is real and fun: you hear of it in a tavern two days later.

### One player fights while the other travels for days
- The traveller's long walk is a long action. If it would carry them past the window, `can_advance` stops it. The game offers in-world
  choices:
  - travel only as far as the window allows (the walk stops at an inn or camp on the way, "you make camp at dusk");
  - spend the time in a way that doesn't move the clock as far (scouting, foraging, a short task);
  - or wait.
- Meanwhile the fighter's rounds advance their clock by minutes. They never wait for the traveller.
- **Nobody is ever frozen.** The window only caps how far *ahead* someone runs, and the player who's behind plays at full speed.

### One player sleeps while another fights
- A long rest moves the sleeper's clock eight hours ahead. That's fine within the window.
- If the fighter later reaches the inn where the sleeper is, rule 1 applies to the sleeper as a person (`touched_at` = their clock).
  The fighter arrives "in the morning", their clock moves forward, and the fight's healing and fatigue follow the time spent.

### Meeting up again
- Characters at the same place who choose to rejoin (the existing party invite) are synced: everyone moves to the latest clock among
  them, with downtime for those behind (rest by default, or a chosen activity).
- If the gap is longer than `ask_jump_hours`, each player is asked ("Joining Bryn means three days at the inn: rest, work or train?").
- Downtime gives something useful (healing, wages, training points through the existing work and training systems), so being behind
  isn't a punishment.

### A player stops playing (offline)
- **In a safe place** (`offline_safe_kinds`): they're in downtime. They don't count toward the window, so they never hold others back.
- **On the road or in a wild place:** the character makes camp (a single roll for a night event), then counts as being in downtime
  there.
- When they come back, they're offered a catch-up to the slowest *playing* character, through downtime, or they can play on from their
  own clock.

### Two players act on the same person at different times
- The host processes operations one at a time (the existing revision check, `StaleOperation`, catches stale writes).
- Rule 1 orders them. Suppose A, at day 10, has already turned the smith against outsiders, and B, at day 3, walks up. B's talk moves
  B forward to day 10 first, and the narration says so. Then the smith's mood toward B is the day-10 mood. B can't change what A did at
  day 10 from day 3.
- **This is the one place time-jumps will be noticed,** so the window has to stay small (a default of 2 days) and the jump has to be
  narrated well.

### Situations and their clocks
- A situation's stage timers run against its place's `region_time`, which only advances when someone is there or a catch-up runs.
- A situation two players both touch carries `touched_at`, so rule 1 orders them.
- The owner's rule that "only meaningful setbacks accelerate the clock" still holds per situation.

## Edge cases
- **Ping-pong:** two players repeatedly touching the same NPC at different clocks. The jumps are bounded by the window, and each player
  only moves forward, never back, so this can't loop.
- **An entity that's always ahead,** such as a fast player rushing around the map touching everything. The window caps it. Regions
  only move forward when visited, so the fast player doesn't speed up the whole world for the others; only the places they touched.
- **News from the future:** rule 2 filters it. A player at day 3 can't hear the day-10 rumour. When they reach day 10, it's waiting for
  them.
- **Items handed between players:** a hand-over needs both present, which means synced.
- **Combat involving players with different clocks:** a fight is a scene, and joining a scene means syncing. A player who comes
  running "to help" arrives at the fight's clock (rule 1 on the fight's `touched_at`). If they're too far behind, the fight may be over
  when they arrive, and that's honest.
- **Narration:** someone who's alone is told as "you". Once two players share a scene, it switches to shared third person (the owner's
  decision). The mode is decided per scene from who's present.

## Why not the alternatives
| Alternative | Problem |
|---|---|
| A single shared clock, advanced by everyone's actions | A traveller's two-day walk makes two days pass for a player in the middle of a conversation; a talker holds a traveller up |
| A single clock that waits for the slowest (CK3-style) | Fine for strategy at pausable speeds; for an RPG, it means a player's long rest needs everyone's agreement, and an absent player stops the campaign |
| No clocks at all, just "Hollywood time" (GM fudge) | Works at a table with one GM; this game's engine owns every number (healing, rent, quest stages, the pulse), so it needs real records, as Gygax argued |

## Migration (each a numbered feature; the suite passes at every step)
1. Add `players.clock`, and have `clock.minutes(ws)` read the actor's clock. For one player it equals the campaign clock, so the
   recordings don't change.
2. Add `touched_at` on writes (one player: always equal to the clock, so recordings don't change).
3. `perceive()` on every news and memory read (one player: a no-op).
4. `pulse.catch_up(region, to)`, regional and lazy. One player: the same results, checked by replaying the goldens.
5. `act_at`, `commit`, `can_advance` and the narrated jumps. Tests use two characters on one machine (the Stage 1 hotseat harness).
6. Merging the party clock, downtime choices and offline handling.
7. The out-of-story `meanwhile` feed (optional).

## Tests to add
- `clock_touch_test`: B (day 3) talking to an NPC A touched at day 10 moves B to day 10. B's healing and needs follow the time; the
  narrator is told the jump.
- `clock_perceive_test`: a day-10 rumour isn't in B's news until B reaches day 10.
- `clock_window_test`: a three-day walk past the window stops at a camp on the way, with in-world choices; no player is blocked from
  short actions.
- `clock_regroup_test`: rejoining puts both on the later clock; the one behind gets the downtime they chose.
- `clock_offline_test`: a player offline at an inn doesn't count toward the window; offline on the road makes camp.
- `clock_region_test`: a region nobody visits doesn't advance; on arrival, its situations and news catch up exactly to the arriving
  clock.
- `clock_single_player_test`: with one character, every golden replays exactly (nothing changes for single play).

## Questions for the owner
1. **The window:** 2 game days by default? Smaller makes jumps rarer and smaller; larger gives more freedom apart.
2. **The `meanwhile` feed:** on, off, or each player's choice? Off keeps it truer to the fiction; on keeps friends in touch.
3. **Rejoining a fight late:** honest (the fight may be over) or generous (the fight waits for anyone who sets out to help)?
4. **Offline on the road:** make camp automatically, or have the game walk them to the nearest safe place?
