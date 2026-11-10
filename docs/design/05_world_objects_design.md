# 5. Design: every thing in the world a real, saved object

Status: a proposal for the owner. Serves pillar 1 (a real world) first, then pillar 2 (the game is a DM), "nothing grows without
bound" and checklist item 8 (multiplayer). It's an **evolution of what exists**, not a new store. My earlier description ("there's no
shared object model") undersold the code.

## What already exists (and is good)
- **`entities` table** (`storage/campaign.py SCHEMA_V3`): `ref, kind, state, place, owner, deadline, json`, indexed by kind, owner and
  place, with lifecycles in `data/rules/lifecycles.yaml` and every state change published (`engine/entities.py`).
- **Parts of places** are already entities (`kind=feature`, `ref=feature:<place>:<slug>`), with depth, links, what they hold, states
  (`becomes`), budgets, and the player's `spot`.
- **Narration read-back** (`adopt_from_passage`) and **ruling-made parts** (`features.adopt(..., "ruled")`), for wild places.
- **People** have their own indexed table (`npcs`). **Situation goods** are stock entities (`situation_parts.give_stock`).

## The gaps
1. **Settled places don't have parts.** `features.grows_here()` returns False for towns and every building in one, so "the back room",
   "the cellar", "upstairs" and "the yard" get logged as facades.
2. **Objects aren't entities.** "A loose rock", "a rope left behind" and "the brazier" become marks (strings on a place) through
   `ruling.make_room` (`kind == "thing"`), so nothing can pick them up, break them or find them later.
3. **The narration read-back is a regex** limited to the feature kinds' words, and only runs in wild places.
4. **Threads, news, deeds, effects and history** live in one `world_state` JSON row that's read and written whole.
5. **Matching is done by words.** `part_of_here()` (any word of four letters or more) and `features.find()` decide what the player
   means.

## The design

### 5.1 Parts of settled places (closes gap 1)
`data/rules/features.yaml`, new kinds and growth by **place type**, alongside the existing growth by biome:
```yaml
kinds:
  room:     {words: [room, back room, side room, chamber, parlour, office, study], deeper: true}
  cellar:   {words: [cellar, basement, undercroft, storeroom, larder], deeper: true}
  upstairs: {words: [upstairs, loft, attic, gallery, landing, upper floor], deeper: true}
  yard:     {words: [yard, courtyard, back yard, garden, stable yard], deeper: false}
  kitchen:  {words: [kitchen, scullery, bakehouse], deeper: false}
  stall:    {words: [stall, booth, counter, bench], deeper: false}
  alley:    {words: [alley, lane, back lane, passage], deeper: true}
grows_by_type:                     # a building grows these; a town grows street parts
  inn:     [room, cellar, upstairs, kitchen, yard]
  tavern:  [room, cellar, kitchen, yard]
  smithy:  [yard, room, stall]
  temple:  [room, cellar, upstairs]
  shop:    [room, cellar, stall]
  house:   [room, cellar, upstairs, yard]
  guild_house: [room, upstairs, cellar, yard]
  town:    [alley, yard, stall]
budget_settled: {first_visit: 0, most: 6, per_hour: 2}    # nothing is made until something names it
access:                             # who may go where: the owner's rule of the world, checked by the engine
  private: [room, cellar, upstairs, kitchen]   # entering needs leave, a key, stealth or force (law.yaml decides the trespass)
```
- `grows_here()` becomes "a wild place, or a building, or a town", read from `grows_by_type`.
- A private part is reached by asking leave (a regard or willingness check on whoever owns it), by a lock (`engine/locks.py`), by
  sneaking, or by force. All of those already exist, so a back room is somewhere you can go, at a price, instead of a wall.
- Parts of a building are owned by the building's owner (`owner` column), so trespass, theft and regard work on them.

### 5.2 Objects as entities (closes gap 2)
```
kind: object      ref: object:<place>:<slug>[:<n>]
state: here | carried | broken | destroyed | hidden | gone
place: the place id; json.part: the feature ref it sits at
owner: an npc id, a character id, or ''
json: {name, what, tags: [heavy, flammable, sharp, container, light_source, climbable, cover], made_by: narrated|ruled|authored|situation,
       states: [...], seen_by: [character ids]}
```
- `ruling.make_room` `kind=="thing"` and doc 2's `needs` create objects instead of marks. A mark stays as what people *say* about a
  place.
- Object `tags` are what doc 2's `uses` checks against: cover needs `cover`, setting a fire needs `flammable` or a `light_source`.
- Picking an object up moves it into the inventory through the existing item path only when it matches an item template. Otherwise it's
  carried as an object (owner = the character), up to a cap per character.
- Caps: at most `objects_per_place` (data) objects per place that aren't owned or authored. The oldest unremarked ones go `gone` first.
  The cost per turn stays flat.

### 5.3 Reading back narration (closes gap 3)
After every narrated passage that describes a place (look, arrive, explore, the result of an act), run one small structured call on the
**background slot**:
```python
class Named(BaseModel):            # one per thing the passage names that the TARGETS/parts list doesn't hold
    name: str; kind: Literal["part", "object", "way", "person"]; what: str
    where: str = ""                 # 'in the corner', 'behind the bar': becomes the part it sits at
class PassageNames(BaseModel):
    named: list[Named] = []         # at most the per-passage budget (features.yaml adopt_per_passage)
```
- The engine creates **stubs**: entities with `state: stub` that hold only a name, kind and description. The details (what it holds,
  locks, an owner) are rolled the first time someone interacts with one. A stub costs one row and no model call.
- People named in passing aren't made into NPCs. They become a "mention", and the existing f395 `appear` path turns one into a person
  if the player addresses them, within the owner's caps.
- **Fallback:** if the call fails or is deferred, keep today's regex adoption. In ordinary turns, this replaces the regex.
- **Latency:** it runs after the passage is shown, in the background lane (`server.yaml` `resume_idle_seconds`). The player is reading
  then, so it adds nothing to the turn. If the player acts before it finishes, the scene's own passage text is still matched by
  embedding (5.5).

### 5.4 Threads and deeds out of the JSON row (closes gap 4)
New tables (migration in `storage/migrations.py`, with the rows taken from `world_state` once):
```sql
CREATE TABLE threads (id TEXT PRIMARY KEY, status TEXT NOT NULL, tier TEXT NOT NULL, place TEXT NOT NULL, town TEXT NOT NULL DEFAULT '',
                      made INTEGER NOT NULL, ended INTEGER NOT NULL DEFAULT 0, json TEXT NOT NULL);
CREATE INDEX threads_live ON threads (status, town);
CREATE TABLE deeds (seq INTEGER PRIMARY KEY, minute INTEGER NOT NULL, kind TEXT NOT NULL, actor TEXT NOT NULL, place TEXT NOT NULL,
                    thread TEXT NOT NULL DEFAULT '', json TEXT NOT NULL);
CREATE INDEX deeds_recent ON deeds (place, minute);
CREATE TABLE news (id INTEGER PRIMARY KEY, minute INTEGER NOT NULL, place TEXT NOT NULL, thread TEXT NOT NULL DEFAULT '',
                   certainty TEXT NOT NULL, groups TEXT NOT NULL, json TEXT NOT NULL);
CREATE INDEX news_where ON news (place, minute);
CREATE TABLE effects (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, place TEXT NOT NULL, until INTEGER NOT NULL, thread TEXT NOT NULL DEFAULT '',
                      json TEXT NOT NULL);
CREATE INDEX effects_live ON effects (place, kind, until);
```
- Caps move from list-trimming to `DELETE ... WHERE` over an index: `deeds_keep` (300), `history_keep` and a news window. Ended threads
  are kept by `matters.remember` as the town's memory and then trimmed, as now.
- `world_state` keeps only the small scalars (`last`, `campaign`, `cooldowns`, `drift_last`).
- **The access layer comes first:** `pulse.load_threads(store, status=..., town=...)`, `pulse.save_thread(th)`, and so on.
  - The first feature just routes every `state["threads"]` read and write through it, still over the JSON row, with no behaviour
    change.
  - The second feature switches the storage under it.
  - That keeps each step small and the recordings exact.
- **Benefit:** `after_deed` loads the live threads near the deed, not all of them. Per-turn cost stays flat as the world ages, and
  thread rows can carry a `character` column later for multiplayer.

### 5.5 Find things by id and meaning, not by matching words (closes gap 5)
One resolver for "what does the player mean":
```python
def resolve_ref(scene, words: str) -> Ref | None:
    cands = scene.visible_refs()                           # parts, objects, stubs, people present, exits, situation parts here
    exact = by_name(cands, words)                          # names and kind words, as features.find does now
    if exact: return exact
    best = relevance.pick(words, [c.label for c in cands], 1, floor=FLOOR)   # the embedder; vectors cached per label
    return best and cands.of(best[0])
```
- It's used by movement (`scenes/world.py` around line 3030), searching, examining and doc 2's `targets_for()`.
- `part_of_here()` and `NOT_A_SPOT` retire. If nothing matches, the answer is "not here" (worded by the narrator), or a new stub if the
  ruling says the place would plausibly have one.

### 5.6 Multiplayer
- Entities already carry `owner`. Add `seen_by` (character ids) for what each character has discovered.
- The journal, the map and "what you know" read from `seen_by`. The world itself is shared.

## Migration order (each a numbered feature with its own tests; the suite passes at every step)
1. The thread and deed access layer over the JSON (no behaviour change; recordings exact).
2. Objects as entities: `make_room` creates objects; `uses` and tags.
3. Parts of settled places, with growth by type, access rules and ownership.
4. One resolver by id and meaning; retire `part_of_here`.
5. Background read-back of narration into stubs; the regex becomes the fallback.
6. Move threads, deeds, news and effects into their own tables (migration plus re-bless).
7. `seen_by` per character.

## Tests to add
- **settled_parts_test:**
  - "go to the back room" at the inn reaches a saved part;
  - the innkeeper's leave or a lock is required;
  - trespass goes through `law`.
- **objects_test:**
  - a ruled "loose rock" is an object you can pick up and throw;
  - cover needs a `cover` object;
  - the cap trims unowned objects.
- **readback_test:**
  - a passage naming "a glowing pool" and "a rope ladder" makes two stubs;
  - walking to one reaches it;
  - when the call fails, the regex still works.
- **resolver_test:** "the ladder", "rope" and "that ladder by the wall" all resolve to the same ref.
- **threads_table_test:** after migration the save loads identically, and `after_deed` reads only nearby threads (count the rows read).
- **long_campaign_test (extend):** the row counts of every new table stay under their caps after 1,000 simulated days.

## Questions for the owner
1. Should the parts of private buildings need leave, a key, stealth or force? That's what I'd recommend: it makes them real *and* gives
   the law and regard systems something to do.
2. Should named people in passing stay mentions until addressed? That's within the existing caps on new people.
3. Should the narration read-back run on every passage, or only on look, arrive and explore? Every passage is better for pillar 1, but
   it uses more of the background slot.
