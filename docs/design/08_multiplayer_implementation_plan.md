# 8. Implementing multiplayer: a plan grounded in the codebase

Goal (the owner's): players who can play together, and who can also split up and live in different parts of one world at the same
time. Each player's model calls run on their own card, group scenes get shared third-person narration, and there's no cap on the
number of players. It builds on doc 06 (time when players split up) and doc 07 (lessons from MUDs and MMOs).

## 1. What the code gives us, and what blocks us

| Asset (keep) | Where |
|---|---|
| The engine checks everything the model writes (contracts, GBNF grammars, checkers), so model output from any machine can be trusted *after* checking | `llm/contracts.py`, `llm/gbnf.py` |
| A turn is a set of all-or-nothing operations with records, rollback and recovery | `engine/operation.py`, `scenes/world.py turn()` |
| Model calls are prepared **before** a transaction opens ("the call first, outside any transaction", f470) | throughout `scenes/` |
| A commit is refused over unseen writes (`StaleOperation`) | `storage/campaign.py` |
| The game reaches the model through its own interface (chat, embed), with a worker that decides who may use the card | `llm/backend.py`, `llm/worker.py` |
| The UI is already a stream of JSON events plus a queue of input lines | `ui/gui/bridge.py`, `ui/gui/server.py` |
| A typed event bus with actor and target ids | `engine/domain_events.py` |
| How each person regards each character, kept per character; combat can hold several player fighters | `engine/regard.py`, `Combat.players` |

| Blocker (change) | Evidence |
|---|---|
| **One player record** | `PlayerState` in the single `kv['player']` row |
| **One scene that is one player's view** | `WorldScene` with `self.player` (about 1,078 uses), `present`, `partner`, the conversation |
| **Global, process-wide output** | about 670 `console.narrate/note/say/...` calls; `bridge` swaps `sys.stdout` |
| **Global per-campaign module state** | `session._owned()`: the ledger, `streams`, `turnlog`, `operation`, `budget`, `canon`, `questions`, `pulse.made_by`, ... |
| **Dice from one sequence** | `streams` reseeded per input from `CampaignMeta.steps` |
| **One global revision** | `operations.revision`: any two commits conflict, even in different towns |
| **One clock** | `CampaignMeta.minutes` |
| **Prompts for one "you"** | e.g. `world_prompts.py`: "The player is 'you', never named and never in the third person" |
| **The world centred on the player** | pulse placement bands, `consequences.tick`, `within_reach` |

## 2. Architecture

**A host that holds the authority, and clients that are thin and also serve the model.**

```
            ┌──────────────── HOST (one player's machine, or a dedicated server) ────────────────┐
            │  Engine: CampaignSession, the one SQLite save, the pulse, the operations            │
            │  ActorContext per character:   scene view · clock · dice · output channel          │
            │  ModelRouter:  call -> which card (the actor's own | the scene leader's | the host's)│
            │  Host llama-server: world/background calls (pulse, situations, background slot)    │
            └──────▲───────────────────────────▲───────────────────────────▲─────────────────────┘
       events/lines │       model RPC (chat/embed)│ events/lines              │ model RPC
            ┌───────┴────────┐          ┌──────────┴────────┐          ┌─────┴──────────────┐
            │ Client A: UI    │          │ Client B: UI       │          │ Client C: UI        │
            │ + llama-server  │          │ + llama-server     │          │ + llama-server      │
            └─────────────────┘          └────────────────────┘          └─────────────────────┘
```

**Why this shape:**
- **The game state lives in one place.** The game loads saves it can't rebuild, and the model is nondeterministic, so a lockstep
  peer-to-peer design (every client simulating the same world) won't work.
- **The owner's "model calls on each player's own card" decision is kept** by sending model calls *out* to the client that owns them.
  Clients never write state: what their model writes comes back as a proposal, and the host checks it, exactly as today.
- **Single player is the same program with one actor and a local client.** Nothing forks.

**Transport:** Steam Networking Sockets (relay, NAT traversal), or WebSocket for testing.
- **Clients to the host:** input lines and pane commands (today's `bridge.submit`).
- **The host to clients:** the existing event types (`text`, `status`, `panel`, `combat`, ...), each tagged with a channel.
- **Model calls:** `ChatRequest`/`Embedding` sent to the client's llama-server, with replies coming back.

## 3. The seven building blocks

### 3.1 Data: several characters in one save
- A `players(character_id PK, json, clock INTEGER, place TEXT, party TEXT, online INTEGER)` table, migrated from `kv['player']`.
- `PlayerState` stays as the per-character record (party, quests, reputation, homes: all already per character).
- New shared tables, as in doc 5: threads, deeds, news and effects, carrying `actor` and `minute`.
- `touched_at` on people, entities and places, and `region_time` per settlement (doc 06).
- **The `kv['operations']` revision becomes per-row versions.** Each operation records the rows it read (and their versions) and the
  rows it writes. A commit is refused only if a row it *read* changed. That's optimistic concurrency control, and it's what lets two
  towns commit independently.

### 3.2 ActorContext: no more process-wide state
```python
@dataclass
class ActorContext:
    character_id: str
    view: SceneView            # present, partner, convo, recent_narration, spot: today's WorldScene fields
    turn: TurnContext          # line_ops, passages, budget...: the 40 fields from scenes/world.py __init__
    dice: Streams              # seeded (campaign seed, character id, that character's input count)
    out: OutputChannel         # where console.* goes for this actor (one or more clients)
    clock: int                 # doc 06
ACTOR: ContextVar[ActorContext]
```
- `console.*` writes to `ACTOR.get().out`. The function bodies change, not the 670 call sites.
- Every module binding in `session._owned()` (the ledger rows, `turnlog`, `operation.CURRENT`, `budget`, `questions`, `asked`,
  `canon` caches) moves onto the actor or turn context. Most are already per-campaign "owned" bindings with a known reset, so it's a
  mechanical move.
- `streams` become per actor. Each player's dice depend only on their own inputs, so the order in which the host interleaves players
  never changes anyone's rolls. That keeps replays exact per actor. The world's own streams are seeded by region and `region_time`.
- **`self.player` becomes `ctx.actor`.** `WorldScene` becomes a thin facade (`scene.player` → `ACTOR.get().player`), so the 1,078 uses
  keep working while they're migrated a module at a time.

### 3.3 Running turns concurrently
- **A turn is prepare, then commit.** That's already the pattern: model calls outside transactions (f470), short transactions to
  write.
- **The host runs one turn thread per actor.** Their *model calls* overlap (they go to different cards), and their *commits* go one at
  a time through SQLite in milliseconds. With 4 players, total throughput is close to 4 single-player games, instead of the 4-times
  slowdown you'd get by running turns one after another.
- **Conflicts:** if a commit's read set changed (two players touched the same NPC), the operation is rolled back and **prepared
  again** with the new state, which may be another model call, at most once. After that it waits behind the other actor's operation.
  Acts in a shared scene are serialised by the scene (3.4), so this only happens to players who are apart.
- **The world's own operations** (pulse, arrival, law, the tail) run per region with a region lock, using lazy catch-up (doc 06/07).

### 3.4 Scenes: playing together
```python
class Scene:                         # one per place where at least one character is, or per party
    members: list[str]               # character ids present
    clock: int                       # the scene's clock; members are synced on entering (doc 06)
    leader: str                      # whose card writes the shared passage (rotates)
    beat: BeatWindow                 # collects lines for up to N seconds, or until all members have acted
```
- **Entering a scene syncs your clock** (doc 06 touch rule). Everyone in a scene sees the same world, so there's no phasing (doc 07).
- **Beats:** in a group scene, each member's lines in one window become **one plan with several actors**.
  - Each line is still interpreted on *its own* player's card, all at once.
  - The engine resolves them in order: speech, then movement, then actions, with ties broken by a die.
  - **One** passage is written, on the leader's card, in shared third person, and sent to every member.
  - A member who sends nothing in the window is shown "watching". No one waits longer than the window.
- **Talking with NPCs:** whoever spoke first holds the conversation. Others can interject (the director already scores who answers
  whom; `party_director` gains human members as speakers who never get dialogue written for them). A private conversation is possible
  (BG3's "private dialogue"): it becomes a sub-scene with only those two.
- **Fights:** `Combat.players` lists every human fighter. A round collects each human's command within the beat window, and anyone who
  doesn't answer gets the safe automatic action (`player_ai`, already used for the danger estimate). The fight's dice are the fight's
  own (and bug 1 from doc 3 has to be fixed first).
- **Companions:** the owner's rules (one companion each until 3 humans, none at 3 or more; the others go on errands and rejoin at the
  next town) live in `services/party.py`, which already owns joining and leaving.

### 3.5 Splitting up: living apart
- Leaving a scene (walking away, or "I'll take the ford") makes your own scene. From then on you run your own turns on your own clock,
  under the doc 06 rules (touch, perceive, window).
- **News between players goes through the world:** `pulse.add_news` with travel time. Hearing what your friend did becomes gameplay,
  and the optional out-of-story feed is for convenience (owner's choice).
- **Offline means checking out** (doc 07): out of the world at an inn or home; on the road, make camp first. Each player's companions
  check out with them.
- **The pulse looks around every online player:** `pulse.place_by_band` draws a band per player, weighted by how recently each was
  active. `consequences.tick` and `within_reach` run per player.

### 3.6 Model routing
```python
def route(task, ctx) -> Backend:
    if task in WORLD_TASKS:          # pulse_*, situation_parts, populate_place (background), thread_telling
        return HOST
    if ctx.scene.group and task in SHARED_TASKS:   # narrate, combat_narrate, exchange, dialogue_frame
        return card_of(ctx.scene.leader)
    return card_of(ctx.character_id)               # interpret_action, ruling, npc_conversation, hire_chat...
```
- It plugs in behind `llm/backend.py`: a `RemoteBackend(client)` implements `chat`/`embed` over the connection, and `llm/worker.py`
  keeps a worker **per card**.
- **If a client disconnects mid-call:** the call is retried on the host's card, or gets the stand-in line (the existing f518 path). The
  turn never hangs.
- **Prompts can't be cached across players:** each card has its own slots, so prompt-start caching (doc 4) stays per player and per
  task.
- **Cards below the minimum** (the "play slowly" path) slow down only their own player. In a group scene, the leader rotates away from
  a slow card.

### 3.7 Narration and prompts for several humans
- The narration mode comes from the scene: one human means "you"; several means **shared third person** (the owner's decision). A
  second-person "you" line can still go to one member for something only they perceive.
- The `who_is_who` and `cast_lines` checks (`engine/entities.py`) list every human character with their name and pronoun, so the
  identity checks the game already runs cover the players too.
- `world_prompts.py` and the other prompt modules get a `{perspective}` block from data, not a duplicated set of prompts.
- The checker for leaked game machinery gains a rule: never address a human by "you" in a group passage.

## 4. Order of work (each a numbered feature with its own tests; the suite passes at every step)

| Milestone | What | Proves | Size |
|---|---|---|---|
| **M0: preparation** (no behaviour change) | ActorContext with one actor; `console` through `ACTOR.out`; the owned bindings moved onto the context; per-actor dice (one actor = today's seed); the `players` table holding one row; the per-character clock equal to the campaign clock | Every golden replays exactly | Large, but mechanical |
| **M1: two characters, one machine, taking turns** | A hotseat harness in `simlib` (two actors, the stub model); scenes with members; syncing on scene entry; the doc 06 rules | Splitting up, rejoining, touch/perceive/window, companions' rules | Large |
| **M2: concurrent turns** | One thread per actor; per-row versions in place of the global revision; preparing again on a conflict; region locks for world operations | Two actors in different towns never block each other; a conflict on one NPC resolves exactly once | Medium |
| **M3: group scenes** | Beat windows; plans with several actors; shared third-person narration; group fights with several commands per round | A scene with 3 humans tells one passage per beat; a fight with 2 humans | Large |
| **M4: networking** | Host and client over WebSocket, then Steam; `RemoteBackend`; channels on the event stream; reconnecting; checking out on disconnect | Two machines, each paying for its own model calls | Large |
| **M5: polish** | The out-of-story feed, lobby and invites, host migration (save copies), a pass on turn time | Night runs with 2–4 bots on separate machines | Medium |

Build M0 together with the turn-stages overhaul (TurnContext) and the world-objects design (doc 5), since they touch the same code.

## 5. Tests and measurement
- **`mp_replay_test`:** a recorded session with two actors replays exactly, per actor, whatever order the host interleaved them in
  (per-actor dice).
- **`mp_isolation_test`:** actor A's output never reaches B's channel unless they're in the same scene.
- **`mp_conflict_test`:** two actors persuading the same NPC at once: one commits; the other is prepared again and sees the new state.
- **`mp_group_beat_test`:** three lines in one window become one plan and one passage; a member who's silent is shown watching.
- **`mp_disconnect_test`:** a client dropped mid-call: the call falls back to the host card; the character checks out.
- **`mp_pulse_test`:** with players in two regions, new situations are placed near both; a region nobody's in doesn't advance.
- **Night runs:** the night bot (`tools/nightbot.py`) runs 2–4 bot players on one host. Measure p95 turn time per player against the
  45-second target, the conflict and re-prepare rate, and passages per beat.

## 6. Questions for the owner
1. **The host:** one player's machine, or also a dedicated headless host for persistent worlds (doc 07's always-on mode)?
2. **The group beat window:** wait for everyone (up to N seconds), or move on with whoever answered?
3. **Private conversations within a group:** allowed?
4. **Players fighting each other:** allowed, by agreement, or never?
5. **Conflicts between players over the world** (both bargaining for the same item): first to commit, or ask the second player?
