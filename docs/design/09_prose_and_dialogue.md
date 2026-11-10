# 9. Better narration and more lifelike dialogue

Written against GOALS.md pillars 3, 4 and 5, and the owner's rules: the engine decides, the model writes; no length limits; no dashes;
thinking off; "infrastructure enhancements instead of more rules to give the narrator".

## What the code does now (measured on 06b393c)

| Finding | Evidence |
|---|---|
| Narration and speech are written **inside JSON**, under a grammar ("Respond only with JSON... with the prose in text") | `NARRATOR_SYSTEM`, `CONVERSATION_SYSTEM`; `llm/gbnf.py` |
| **One townsperson reply carries the speech plus 12 bookkeeping fields** (intent, reveals, trust_change, remember, gives, offers_work, offers_quest, journal_note, a promise...) | `llm/contracts.py NPCReply` |
| **System prompts are long lists of prohibitions:** the narrator's 5,951 characters hold 42 never/not/no/avoid; the conversation's 9,755 characters hold 53 | Counted |
| **Townsfolk prompts are large:** `npc_conversation` median 29,155 characters, p95 36,345; the owner's target is 14,000 at p95 | `data/measured/bundle_d_baseline.yaml`, `prompt_ceilings.yaml` |
| **Each narration's brief is a sentence of English instructions written at the call site**, e.g. "Describe the search and its fruitlessness" | 90 `self.narrate(f"...")` calls in `scenes/` |
| **Everyone shares one small set of exemplars** ("HOW PEOPLE SOUND HERE", 8 lines; "HOW NARRATION SOUNDS HERE", 3), so they all lean toward the same plain village register | `data/rules/voice.yaml exemplars` |
| **Stock-phrase lists are shown to the model** ("Avoid stock phrases like 'the air hangs heavy'...") as well as checked afterward | `scenes/voice.py DM_VOICE`, `STALE` |
| **Repetition samplers are off:** DRY 0.0, XTC 0.0, repeat penalty 1.0 except for 4 speech tasks | `data/rules/sampling.yaml` |
| **A conversation is sent as text inside one user message,** not as alternating chat turns | `npc/life.py converse` |
| **Strong parts to keep:** the worn-word watch, voice kits (a voice built from axes, with checks), culture, fluency and tells per speaker, the director, the dialogue frame chosen by reason, the canon of what someone has said about themselves, `fresh()`'s one rewrite, blind readings, the prose analysis | Throughout |

## Why this holds the writing back
1. **Writing inside a strict format costs quality.** A 2024 study found that format restrictions (JSON mode in particular) degraded
   reasoning, and the stricter the constraint the larger the drop. A rebuttal disputes how far that goes (dottxt). It's worth
   measuring on this game's own prose rather than assuming. For a 12B model writing a passage inside quotes, with escapes, it's a
   likely cost.
2. **A reply that's also a form.** When one call has to decide whether to reveal clue 3, by how much trust moves, whether to offer work
   and whether to give a key, *and* sound like a person, the speech gets what's left of the model's attention. That's when you get the
   "helpful villager" voice.
3. **Prohibitions name what they forbid.** A list of banned phrases and "never X" puts X in front of the model. Fifty such lines also
   compete for the attention of a 12B model on every token.
4. **The briefs at the call sites are the real creative direction,** and they're 90 hand-written sentences. They vary by author and
   mood, aren't data, and can't be rotated or measured.
5. **Shared exemplars make shared voices.** Showing everyone the same eight lines pulls the townsfolk toward one sound, which works
   against pillar 4.
6. **No memory of where a scene is going.** The narrator sees the last 3 passages, not the scene's open tension or a detail planted
   earlier that could pay off now. So each passage starts afresh.

## Recommendations (ordered by value for effort; every one measured with the project's tools)

### A. Quick, by data or prompt only

**A1. Test DRY and XTC on the prose and speech tasks only.**
- DRY penalises repeating sequences of tokens, which a plain repeat penalty doesn't catch; XTC sometimes removes the most likely tokens.
  Both target clichés.
- Use them on `narrate`, `combat_narrate`, `npc_conversation`, `hire_chat`, `exchange` and `dialogue_frame`. Never on interpretation or
  rulings.
- A/B with the prose analysis (reused phrases, repeated sentences, shared openings) and a blind reading. It's a sampling change, so it's
  inside the data hash: re-bless after.

**A2. Take the stock-phrase lists out of the prompts and keep them only in the checker** (`stale_phrases`, `worn`). The prompt states the
aim in positive terms ("say what is new; one exact detail") and the checker catches the slips.

**A3. Draw exemplars from a pool.**
- Grow `voice.yaml exemplars` into pools tagged by moment (arrival, night, interior, grief, fight, small talk, refusal, gossip), with
  about 30–60 lines each.
- Each call gets 3, drawn by tag and a seed and never the same 3 twice in a row.
- Fill the pools from the **best passages from night runs**, chosen by the blind readers. They are the game's own best writing, which
  the owner already judges.

**A4. Cut the system prompts down to a short card of what to do,** about 1,500 characters each. Each removed "never" either is already
checked by code (dashes: `undash`; invented speech: `invented_speech`; machinery: `hygiene`) or gets a check now. Prohibitions that can't
be checked stay as one line each.

### B. Infrastructure (the owner's preference)

**B1. The engine writes a beat; the model writes prose.** Replace the 90 instruction sentences with a typed **Beat** built by the engine:
```yaml
# data/rules/beats.yaml
kinds:
  search_fruitless: {focus: effort, register: low, show: [time spent, what was checked], withhold: [any find], angles: [hands, light, sound]}
  arrive:           {focus: place, register: by_place, show: [one person doing one thing], withhold: [names not given], angles: [first sight, sound, smell, a person]}
  blow_landed:      {focus: body, register: high, show: [the blow, its cost], withhold: [outcome beyond the numbers], angles: [weight, sound, aftermath]}
```
```python
Beat(kind="search_fruitless", facts=[...], focus="effort", register="low", angle=pick_angle(kind, recent), withhold=[...], callback=pick_callback(scene))
```
- The narrator gets the facts, plus **one angle**: a different sense or camera position each time, chosen by the engine from the kind's
  list, never the last one used.
- Variety becomes something the system produces, not something the prompt asks for.
- Briefs become data you can tune, test and measure per kind. Pillar 3's "never stamped out the same way" applies to the briefs
  themselves.

**B2. Scene memory and callbacks.** The engine keeps a small, capped `SceneThread` per scene: the open question or tension, a detail
planted earlier (from marks, the ground, an NPC's line), and the mood so far. Every so often the beat carries a **callback** ("the bent
nail you noticed by the door"). Paying off something planted earlier is what makes prose feel authored. It's capped and per scene, so it
doesn't grow.

**B3. Prose as plain text; structure stays where it's needed.**
- Narration, frames, combat telling and speech come out as **plain text**, with a stop sequence and the existing checks (`hygiene.clean`,
  `undash`, the invented-speech check, the hN markers for blows) run on the text.
- The fields that genuinely need structure (combat markers, the `before`/`after` of a frame) become simple text markers parsed by code,
  not JSON.
- Run the comparison the way `tools/situation_ab.py` and `think_ab.py` do: readers' preference across both orders, the prose measures
  and first-try acceptance. Keep the change only if readers prefer it (the owner's 60% bar from the thinking decision is a good bar
  here).

**B4. Decide, then speak (townsfolk and hires).** Split `NPCReply` into two calls:
1. **Decide**, a small structured call, or the engine itself where it can:
   - what they *do* with the player's line (intent),
   - which facts they share (`reveals`),
   - trust, gives, offers and memory, plus one **conversational move** (answer, deflect, ask back, change the subject, joke, go quiet,
     correct them), weighted by the voice kit, the stance and regard.
2. **Speak**, in plain text: a compact persona card plus the decision ("You'll tell them about the tracks by the mill, grudgingly; you
   want them gone before your husband's back; you change the subject to the price of salt").

Speech becomes the performance of a decision. That fits "the engine decides, the model speaks", makes lies and withholding deliberate,
and frees the voice. On cost: the decide call is short (about 100–150 tokens out) and the speak prompt shrinks a lot (see B5), so the
total should come out similar. Measure with `tools/latency.py`.

**B5. A prompt diet for the townsfolk, toward the owner's 14,000-character target.** Order the prompt as a person first, rules last:
- a **persona card** (who they are, what they want *right now*, what they won't say, how they talk, plus their *own* signature lines,
  see B6);
- **what they know, retrieved:** only the 3–6 facts relevant to this line, via the embedder (`engine/retrieval.py` exists);
- **the conversation as real alternating chat turns,** not a transcript pasted into one message. It's more natural for an instruction
  model, and caches better (doc 4);
- **a few rules,** only the ones code can't check.

**B6. Signature lines per character.** At profile time (`PROFILE_SYSTEM`), the model writes 4–6 example lines **for that person**,
checked against their voice kit (the checks already exist). They're kept on the NPC and shown as *their* exemplars instead of the shared
pool. Townsfolk then differ in sound, not just in content (pillar 4: "they should still sound different enough even if mundane"). The
voice-distinctness measure (overlap with themselves against others, 0.20 against 0.18 in the f350 run) is the test.

**B7. Wants and subtext for everyone.** `hire_subtext` and `hire_feeling` give hires something they won't say. Give townsfolk the same
through the persona card: one want for this conversation (from concern, motive, regard, situation parts) and one thing held back. Drama
in dialogue comes from a want meeting an obstacle, and the engine already knows both.

### C. Training (longest, biggest)

**C1. A LoRA trained on prose the blind readers preferred,** using the existing pipeline (`tools/lora_*`), for `narrate` and
`npc_conversation` first.

**C2. Preference pairs from what's already logged.** `fresh()` keeps drafts that were rewritten, and `LORA.md` notes "the draft a rewrite
replaced is never learned from". Use those drafts as the *rejected* side of preference pairs (DPO) against the accepted rewrites and
the readers' picks. The project already produces this data for free.

## How to measure each change (all existing tools)
- **Prose:** the prose analysis (reused phrasing, repeated sentences, shared openings), the worn-word counts and the blind readings
  (`tools/blind_review.md`).
- **Voices:** `tools/voice_report.py`, distinctness against self and others, the identity-drift notes.
- **Cost:** `tools/latency.py` p95 per task and first-try acceptance (`bundle_d_baseline.yaml` style).
- **A/B harness:** the readers' protocol from `situation_ab` and `think_ab` (both orders, a preference bar decided in advance).

## Suggested order
1. A1 to A4 (data and prompt only; one night each to measure).
2. B5 and B6 (smaller conversation prompts, signature lines).
3. B4 (decide, then speak), then B3 (plain-text prose), each behind a data switch with an A/B.
4. B1 and B2 (beats, scene memory), migrating the 90 call sites by kind.
5. C1 and C2 once the prompts are stable (an adapter learns the prompts it was trained on).

## Questions for the owner
1. Are you happy for prose to leave JSON if the readers prefer it?
2. Should signature lines be written by the model once per person, or partly hand-written for anchors and hires?
3. Should the conversational move (deflect, joke, go quiet) be rolled by the engine, or chosen by the decide call?
