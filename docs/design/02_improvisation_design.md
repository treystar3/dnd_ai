# 2. Design: one improvisation ruling for every context

Status: a proposal for the owner. Serves pillar 2 (the game is a DM) first, then pillar 1 (a real world) and pillar 6 (fun, deep, fair
play). It replaces `engine/world_improv.py` and `engine/combat_improv.py`, and the improvisation branch of `engine/ruling.py`. It folds
`situation_parts.rule()` into the same call.

## Goals and limits (from GOALS.md)
- The player can try anything. What makes sense is accommodated; what doesn't is refused in the world's voice. Impossible acts are never
  granted.
- "The engine should prevent impossible outcomes without preventing unexpected ones." The model proposes; the engine validates and
  commits. Every number is the engine's.
- The same act under unchanged circumstances reuses its earlier ruling. Technical limits never become fictional ones.
- The p95 turn stays around 45 s on the 3060. Thinking is off.
- Data in YAML, checked by `data_check`. Every store capped. Keyed by character id (multiplayer).

## 1. Build on what exists

| Already exists | Reused as |
|---|---|
| `RulingChange` (closed `becomes` list, `because`, a `needs` chain) and `situation_parts.ruled()` / `keep_changes()` | The change format and checker for **every** target, not only situation parts |
| `Ruling` (sense, needs, requires, stakes, answer, instead) and `ruling.verdict()` | The "does it make sense" half of the one call |
| `capabilities.yaml` and `ruling.means_of()` | The check for abilities the character has |
| `features.adopt()` and the entity registry | Where things the act needs are created |
| `combat.contest()`, `add_status()`, `apply_rider()`, `battlefield` | The combat side of applying changes |
| `checks.chance()` / `checks.roll(rng=...)` | The one odds formula |
| `asked.compute()` | Caching a ruling per act |

## 2. Data (new and changed YAML)

### `data/rules/action_tags.yaml` (new)
```yaml
# What an action uses. A state that blocks or hinders a tag stops or slows every action using it, for any actor.
tags: [move, flight, swim, climb, sight, hearing, speech, gesture, grip, reach, breath, balance, will, spellcasting]
# Default tags for actions the engine already has; creatures and abilities add or override their own.
actions:
  attack_melee: [reach, grip]
  attack_ranged: [sight, grip]
  take_off: [flight]
  cast: [spellcasting, speech, gesture]
  flee: [move]
  talk: [speech]
```

### `data/rules/changes.yaml` (new; generalises the situation ruling's `becomes`)
```yaml
# Every change an act can make, on any target kind. The model names changes from this list; the engine applies them and sets the numbers.
changes:
  # on a person or creature (combat or not)
  hindered:   {on: [creature, person], args: [tag], tiers: true, lasts: [rounds, minutes, until_healed]}
  blocked:    {on: [creature, person], args: [tag], tiers: true, lasts: [rounds, minutes, until_healed]}
  moved:      {on: [creature, person, object], args: [to]}               # zone, row, part of a place, prone
  held:       {on: [creature, person], tiers: true, lasts: [rounds, minutes]}
  opened:     {on: [creature, person], tiers: true, lasts: [rounds]}     # exposed / guard opened
  harmed:     {on: [creature, person], tiers: true}                       # a damage tier; never a raw number
  # on a person: the situation ruling's words, kept as they are
  believes: {on: [person]}
  doubts: {on: [person]}
  warmer: {on: [person]}
  colder: {on: [person]}
  afraid: {on: [person]}
  angry: {on: [person]}
  grateful: {on: [person]}
  open: {on: [person]}
  wary: {on: [person]}
  hostile: {on: [person]}
  refusing: {on: [person]}
  terrified: {on: [person]}
  committed: {on: [person]}
  flees: {on: [person, creature]}
  surrenders: {on: [person, creature]}
  joins: {on: [person]}
  warns: {on: [person]}
  # on a part of a place, an object, a road
  state:      {on: [part, object, road], args: [becomes]}                 # features.yaml becomes: lit, dark, blocked, flooded, burning...
  access:     {on: [part, road], args: [open, closed, hidden]}
  broken: {on: [object, part]}
  mended: {on: [object, part]}
  destroyed: {on: [object, part]}
  found: {on: [object, evidence]}
  hidden_here: {on: [object]}
  # on a situation's own conditions (unchanged from f547)
  lifted: {on: [condition]}
  safe: {on: [person]}
  given_up: {on: [condition]}
  lost: {on: [condition]}
  tested: {on: [evidence]}
tier_numbers:                     # the engine's; tuned in the balance pass
  hindered: {minor: -10, moderate: -20, major: -35}     # odds points on actions using the tag
  rounds:   {minor: 1, moderate: 2, major: 4}
  minutes:  {minor: 30, moderate: 240, major: 1440}
  harmed:   {minor: 0.5, moderate: 0.8, major: 1.1}     # times the actor's weapon blow; "weapon" is 1.0
resistance:   {minion: 0, normal: 0, elite: 1, boss: 1, legendary: 2}   # tiers taken off a change on that target
repeat_steps: [0, 1, 2]           # tiers taken off the same trick on the same target, by repetition this fight or day
fail_modes:   [exposed, knocked_down, disarmed, hurt, noise, time_lost, object_breaks, noticed, target_repositions]
fast_path:    {similarity: 0.84}
cache:        {per_scene: 64}
```

### `data/world/bestiary.yaml` (new optional fields)
```yaml
  actions: {bite: [reach], claw: [reach], take_off: [flight], breath: [breath]}   # tags per attack; defaults from the category
  parts:   {wing: {durability: 2, governs: [flight]}, eye: {durability: 1, governs: [sight]}}
  immune:  []          # tags it lacks entirely: a golem [sight, breath]
  rank:    boss        # read into resistance
```

`data_check.py` checks: every change's `on` kinds exist, every tag a part governs is in `tags`, and every `tier_numbers` key exists.

## 3. Contract (`llm/contracts.py`)

```python
class ActChange(BaseModel):                       # RulingChange, generalised
    n: int
    target: str                                    # a reference from the TARGETS list the prompt shows: "c2", "c2.wing", "p3", "f1", "s4.part2"
    becomes: str                                   # a name from changes.yaml (validated against the list in validation_context)
    tag: str = ""                                  # for hindered/blocked
    tier: Literal["minor", "moderate", "major"] = "minor"
    lasts: str = ""                                # from that change's lasts list
    to: str = ""                                   # for moved
    because: Literal["words", "coin", "goods", "force", "evidence", "earlier", "skill"] = "skill"
    about: int = 0
    needs: list[int] = []
    label: str = ""                                # the model's own name for it: "wing torn". Shown to the narrator, never read by rules

class ActRuling(BaseModel):                       # Ruling + JudgeVerdict.changes in one
    sense: Literal["yes", "cost", "no"]
    why: str = ""
    answer: str = ""; instead: list[str] = []      # for a no
    uses: list[str] = []                           # TARGETS it relies on ("f2: the brazier")
    needs: list[Need] = []                         # ordinary things the world may add (unchanged Need)
    requires: list[str] = []                       # capabilities
    stakes: Stakes = Stakes()                      # check and how hard
    changes: list[ActChange] = []                  # on success; the engine scales them for partial or strong
    fail: str = "exposed"                          # from fail_modes
    damage: Literal["none", "weapon", "environment"] = "none"
```
It's constrained by GBNF like every other contract. The answer budget is `ruling: answer_tokens: 260` (today it's 200), with short
reference codes keeping it compact.

## 4. The pipeline

```python
# engine/act.py (new): the only entry point for an act the fast handlers don't own
def act(scene, actor_id, intent, text) -> None:
    ctx = scene.context()                                   # Context(kind=combat|talk|explore|travel, place, fight, present, situations here)
    targets = targets_for(scene, ctx, intent)               # numbered TARGETS: c1 dragon (aloft: no; zone z2), c1.wing, p1 innkeeper, f1 the brazier...
    if (p := precheck(scene, ctx, intent, targets)):        # reach, altitude, range, earshot, gone or dead, capability
        return refuse(scene, intent, p)                     # worded by the narrator from the reason code (doc: refusals)
    key = ruling_key(actor_id, intent, targets, ctx)        # the act's words (normalised), target ids, and a hash of their relevant state
    r = scene.rulings.get(key) or fast_path(intent, targets, ctx) or ask_act_ruling(scene, ctx, intent, targets)
    if r is None:
        return clarify_or_defer(scene, intent)              # never a roll without a ruling (doc 3, bug 2)
    scene.rulings.put(key, r)
    v = validate(scene, ctx, r, targets)                    # section 5
    if not v.ok:
        return refuse(scene, intent, v.reason)
    outcome = resolve(scene, ctx, actor_id, v.ruling, targets)  # section 6
    publish(Acted(actor=actor_id, ctx=ctx.kind, degree=outcome.degree, changes=outcome.kept, targets=outcome.target_ids))
    situations_touched(scene, outcome)                      # section 7
    narrate_committed(scene, outcome)
```

Entry points:
- `scenes/world.py on_other()` calls `act()`, replacing `ruling.run()`.
- `services/fight.py` routes the improvisation branch, and attacks with an aim ("at the wing, to stop it flying"), to `act()` with
  `ctx.kind == "combat"`, replacing `combat_improv.resolve()`.
- `events.after_deed()` keeps the instant, certain paths. Anything else touching a situation's parts goes through `act()`'s
  `situations_touched()`, replacing `judge()`/`_rule()` for situations that have parts.

## 5. Validation (pure; reads, never writes)

```python
def validate(scene, ctx, r, targets):
    if r.sense == "no":
        return Invalid(r.answer, instead=r.instead)
    if (miss := [c for c in r.requires if c not in means_of(scene)]):
        return Invalid(lacking(miss[0]))
    for ref in r.uses:
        if not targets.exists(ref):
            return Invalid(("missing", ref))     # no cover without something to hide behind
    kept, dropped = [], []
    for ch in r.changes:                         # in order, as one chain (situation_parts.ruled does this now)
        why = (unknown_change(ch) or wrong_target_kind(ch, targets) or immune(ch, targets)
               or needs_dropped(ch, dropped) or contradicts_world(scene, ch) or situation_rule(scene, ch))
        if why:
            dropped.append((ch, why))
            continue
        ch.tier = lower(ch.tier, RESISTANCE[targets.rank(ch.target)] + repeats(scene, ctx, ch))
        kept.append(ch)
    if r.needs and over_caps(scene, r.needs):     # owner's people caps; told in story terms, never "Nobody comes."
        r.needs = within_caps(scene, r.needs)
    return Valid(r.with_changes(kept), dropped=dropped)
```
`situation_rule()` is today's `situation_parts.ruled()` logic, unchanged, applied to changes whose target is a situation part.

## 6. Resolution

```python
def resolve(scene, ctx, actor_id, r, targets):
    a = actor(scene, actor_id)
    dice = ctx.fight.dice if ctx.kind == "combat" else scene.rng
    if r.sense == "yes" and not r.stakes.check:
        degree = "success"
    else:
        degree, _ = checks.roll(checks.chance(a, r.stakes.check, ...) + HARD[r.stakes.hard] + repeat_penalty(...), rng=dice, c=a)
    with scene.operation("act") as op:
        made = make_room(op, scene, r.needs)                 # features.adopt / ruling.appear, as today
        if degree in ("success", "strong success", "partial"):
            scale = {"strong success": +1, "success": 0, "partial": -1}[degree]
            for ch in r.changes:
                if is_control(ch) and ctx.kind == "combat":   # finding E: improvisation meets the same contest as abilities
                    grade = combat.contest(a.fighter, targets.fighter(ch.target), attrs_for(r), dice)
                    scale += {"full": 0, "partial": -1, "none": -9}[grade]
                apply_change(op, scene, ctx, ch, shift(ch.tier, scale))
            if r.damage != "none":
                deal(op, ctx, a, targets, r.damage, scale)
        else:
            apply_fail(op, scene, ctx, a, r.fail)
        op.record("acted", ruling=r, degree=degree)
    return Outcome(degree, kept=r.changes, made=made)

def apply_change(op, scene, ctx, ch, tier):
    if tier < 0:                                     # scaled away to nothing
        return
    t = targets.resolve(ch.target)
    match changes_yaml[ch.becomes]:
        case {"args": ["tag"]} if ctx.kind == "combat":
            add_status(ctx.fight, t, state_name(ch), rounds(ch, tier))   # a generic status carrying {prim, tag, tier}
        case {"args": ["tag"]}:
            entities.put_state(op, t, ch, tier)                          # on the person or creature record; ends by its `lasts`
        case _ if ch.becomes in SITUATION_WORDS:
            situation_parts.keep_change(op, scene, ch)                   # today's keep_changes, per change
        case {"on": [*kinds]} if "part" in kinds or "object" in kinds:
            features.change(scene, t, ch.becomes, degree_for(tier))      # or an object state
```

### Tag-aware rules (the one rules change)
```python
# engine/combat.py
def can_take(f, action) -> tuple[bool, str]:
    tags = action_tags(f, action)
    for s in f.carried.states:            # generic states from apply_change
        if s.prim == "blocked" and s.tag in tags:
            return False, s.label
    return True, ""

def tag_mod(f, action) -> int:
    return sum(TIER["hindered"][s.tier] for s in f.carried.states if s.prim == "hindered" and s.tag in action_tags(f, action))
```
These get called from `can_use`, `act_attack`, `act_flee`, the enemy action picker (`enemy_turn`) and `hit_parts`. Outside combat,
`checks.chance()` adds `tag_mod` for the acting character's own states. That's what makes "blind the cyclops", "gag the cultist" and
"ground the dragon" work for any target, without a rule per case.

### Parts with durability
A change aimed at `c1.wing` reduces that part's durability first. While durability is above 0, the change is applied one tier down
(hindered instead of blocked). That stops a single roll ending a boss fight.

## 7. Situations

`situations_touched(scene, outcome)` is called after every act. For each live situation whose `trouble_near()` includes the place, or
whose parts include a target, it passes the kept changes on those parts to the f549 end-reading. The model was already asked for them
in the same call: TARGETS lists situation parts, numbered as today's `parts_lines()` numbers them. There is **no second call, no tier
filter and no daily cap**. The repeated-act rule is the cache key.

## 8. Fast path and cache
- **Fast path:** the act's embedding is compared against `fast_path` patterns in `changes.yaml`, each a stored ruling with blanks
  for targets (sand in the eyes, tripping, cover behind a named object). Above the similarity threshold, the stored ruling is used with
  no model call. Its `uses` still have to exist.
- **Cache:** keyed on the act's normalised words, the target ids, and a hash of the targets' relevant state (position, states, a
  situation part's condition). Kept per scene and capped; a fight's cache is saved with the fight.

## 9. Performance (doc 4 has the measured base)
- Ordinary actions: unchanged.
- Improvisation outside combat: one call, as today, with an answer about 60 tokens larger, so roughly +2 s.
- Improvisation in combat: from 0 s (fast path or cache) to about +9–11 s for a new ruling. To keep the p95, merge the interpretation
  and the ruling for lines that aren't ordinary actions (one prompt read), and record a golden fight with improvisation for
  `tools/latency.py`.
- Situation rulings: fewer calls than today in practice, because the act already brings its changes.

## 10. Migration, in order (each step is a feature with its own tests; the suite passes at every step)
1. Fix the two bugs (doc 3). Move the combat effect list into data and use the shared odds formula.
2. `action_tags.yaml` and `changes.yaml`. Generic states in `effects.py` plus `can_take`/`tag_mod`, with no caller yet.
3. `ActRuling` and `engine/act.py`, outside combat only, behind a data switch. Run both paths on the ruling corpus
   (`tools/ruling_eval.py`) and compare false acceptances and false rejections.
4. Bring situation parts in. Retire `judge()` for situations with parts. Make improvised acts deeds.
5. Combat: switch the improvisation branch, then attacks with an aim. Re-bless `stub_fight` with a recorded improvisation fight.
6. Remove `world_improv.py` and `combat_improv.py`, leaving their phrase tables in data for the fast path.

## 11. Tests to add (tools/sim)
- `act_impossible_test`: wings with no flight capability is refused, and also refused when the model fails (deferred or a question).
- `act_reach_test`: a dragon aloft can't be reached with a melee spear; once it lands, it can. The refusal offers options.
- `act_tags_test`: `blocked flight` stops `take_off` for a creature and for an NPC; `hindered sight` lowers attack odds by the tier.
- `act_resist_test`: a boss takes one tier less; the third use of the same trick takes two tiers less; a control change meets `contest()`.
- `act_durability_test`: the first wing hit hinders, the second grounds.
- `act_situation_test`: an improvised act on a situation part (barring the granary) moves the situation, at every tier.
- `act_cache_test`: the same act under the same circumstances makes no second call; a changed circumstance does.
- `act_uses_test`: cover with nothing to hide behind is refused, or adds an ordinary object within its cap.
- `act_multiplayer_test`: two characters' acts keep their own caches and regard (keyed by actor).

## Questions for the owner
*Answered 2026-11-11 (GOALS.md, phase 2): 1 yes, when something real enables it; 2 yes, after phase 2; 3 yes, the reuse rule and the background slot's time budget replace them.*
1. Should improvised acts be able to match an ability's strength on a strong success, if something real enables it?
2. Should arcs become campaign-tier situations?
3. Should the judge's caps of 1 a day and 8 in all go, replaced by the reuse rule?
