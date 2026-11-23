# 36. B3: prose as plain text, the plan

The plan for docs/design/09 section B3, for the owner to approve before anything is built. Pillar 5 (writing a reader wants to keep
reading), and the precondition for streaming the narration (pillar 7) later. Written 22 November 2026 against play/faults at
350ce31, with f790 to f792 uncommitted beside it.

**Approved:** the owner on 2026-11-22, "okay let's begin B3 then", then "Yes, recommended answers" to the four questions below
(GOALS.md's decision row).

## What B3 is, and what it is not

Every model call today answers in JSON under a grammar (llm/llama.py:122 sends `"grammar"` always, `"stream": False`; there is no
stop sequence anywhere in llm/). The narrator's prompts end "Respond only with JSON matching the schema, with the prose in "text""
(scenes/combat_prompts.py:92, 129, 139 and the narrator's own). A failed check sends the draft back with "respond again with the
complete JSON" (llm/gateway.py:407).

B3 lets a task whose answer is only prose be answered as **plain text**: no grammar, a stop sequence, the prose as written. Doc 09's
case for it: writing inside a strict format is likely to cost a small model some quality (contested, so measured here, not
assumed), and plain text is what streaming needs.

Not B3: streaming itself (later, on top of this), the beats of B1, and the speech of townsfolk and companions (their answers carry
fields that must stay structured; B4's decide then speak already splits them, and they are a second slice).

## The first slice: the four narration tasks

`narrate`, `combat_opening`, `combat_narrate` and `combat_aftermath` all answer `Narration{text}` (llm/contracts.py:1204): one
prose field, no validators, about seven call sites (scenes/world.py:426, 453, 3291, 3296; scenes/combat_scene.py:879, 1283;
scenes/mentor_actions.py:179). They are 27% of a turn's time on the owner's card (docs/measure/2026-11-21_turn_split_4070tis.md)
and the passages a player reads most. Frames, the goddess, partings and speech come after, once this slice has measured well.

## How it works

The key choice: **the text is wrapped into the same contract object the moment it arrives.** A plain answer becomes
`Narration(text=...)` before anything reads it, so every check that walks the answer's fields (the output gate, the content guard,
undash, name mending, phantoms, the invented-speech and worn-word checks in `fresh`, `place_figures` and its blow markers) runs
unchanged. Only the request and the first parse differ.

1. **The switch, in data.** `data/rules/prose.yaml` (new, checked by engine/data_check.py): `plain_text: []`, the tasks answered as
   plain text. Shipped empty: off, the old path exactly, as decide_then_speak was put behind reply.yaml. Per task, so a task goes over
   only when its own measure holds.
2. **The contract says which field the text is.** A contract that can be plain names its one prose field (`Narration`: `text`). A
   task in `plain_text` whose contract names none is refused at startup by data_check.
3. **The request (llm/llama.py llama_body).** For a plain request: no grammar; a `stop` list from prose.yaml (the chat template's end
   of turn is the natural end; the list only guards against a run past it, Gemma 4's own markers `<|turn>` and `<turn|>` as the
   server's log prints its format); `n_predict` as now (no length limit is added, the owner's rule). Thinking stays off.
4. **The format line in the prompt.** The narrator's prompts end in one sentence about the JSON. That sentence comes from one place,
   chosen by the switch: the JSON line when off, "Write only the passage itself, as the player will read it." when on. No new rule
   is added to the prompt; one is swapped.
5. **The answer (llm/gateway.py).** A plain answer is trimmed and passed through a shape check of its own before it is wrapped: a
   label before the passage ("Here is the narration:"), the whole passage in quotes, markdown headings or bullets, or a JSON object
   are sent back with the reason, as the gate does today. Then `schema(**{field: text})`, and from there the path is the one that
   exists.
6. **The retry wording.** "Fix this and respond again with the complete JSON." becomes "Fix this and write the passage again." for a
   plain request; the cut-off message likewise.
7. **Recording and replay.** The neutral request records the plain flag, so a plain request hashes apart from a JSON one; the answer
   is recorded as the raw text. With the switch off nothing a golden sends changes, so the goldens replay as they are. The stub
   (simlib.Stub) answers a plain request with the text its `a_<Contract>` answer holds in the named field.

## Features, in order

| | What | Tests |
|---|---|---|
| f793 | The plain path behind the switch (off): prose.yaml and its check, the contract's prose field, llama_body without grammar and with `stop`, the shape check, the wrap, the retry wording, the recorded flag, the stub | A plain request has no grammar and has `stop`; each shape fault is sent back and a clean passage is wrapped; every existing check fires on a wrapped answer as on a JSON one (the gate's leak, a dash, a phantom, a worn word); switch off, a request is byte for byte what it was (the goldens replay); the stub answers both ways; a task without a prose field in `plain_text` is refused |
| f794 | The measuring tools read a plain answer: tools/prose_measure.py (which reads every answer as JSON today, so it would read no narration from the on arm), latency.py, voice_report.py, eventrun.py, lora_dataset.py, the audit's display, and tools/rerun.py's timing mode (which always sends a grammar). As built, f793 already swaps the format line by its exact sentence from prose.yaml, so f794 is this instead | Each tool reads a recorded plain answer as it reads a JSON one |
| measure | Off against on, on the live model, for the four tasks (below) | |
| f795 | If the measure holds: the four tasks turned on in prose.yaml, the goldens re-blessed with every moved row explained | golden_replay_test, the rebless skill |

## How it is measured, and the bar

The owner's rule for prose (2026-11-11): a prose change is kept only if its measures hold or improve against the span of two
baselines measured the same way. Doc 09 adds the readers' 60% bar from the thinking decision.

- **Arms:** off and on, alternating (on, off, on, off), the same script and seed, nothing else running on the card
  (local-measure lessons: one pair settles nothing, timings vary by a quarter).
- **Where:** the owner's 4070 Ti Super, with the owner's go for the card, or a rented pod. The 3060 figures are scaled.
- **Measures:** the prose analysis (reused phrasing, repeated sentences, shared openings: tools/prose_measure.py), worn words and
  stock phrases, first-try acceptance and send-backs by reason (the shape check's new reasons counted apart), names wrong,
  tokens written and seconds per call.
- **Readers:** blind pairs, both orders. Kept only if on is preferred at 60% or more and no measure gets worse beyond the two
  baselines' span.

## Risks

- **Without a grammar the model can wrap or annotate the passage** (a label, quotes, markdown, a note at the end). The shape check
  and the gate catch the known forms; a send-back rate that rises is a measured cost, and it decides the arm.
- **No measure of quality is certain.** The JSON cost doc 09 cites is disputed; if on does not beat off, B3 stops here and streaming
  is built on JSON instead (harder, but possible).
- **The goldens move when the switch goes on** (every narration request changes). That is f795's rebless, done once, with the reason.
- **Two formats to keep while the A/B runs.** The off path is deleted only after f795, if on wins.

## Questions for the owner

1. **Prose leaves JSON for these four tasks if the measures hold and the readers prefer it at 60%?** (Doc 09's question 1.)
   Recommended: yes.
2. **The first slice: the four narration tasks only,** with frames, the goddess, partings and speech after? Recommended: yes.
3. **The measure on your card** (the model server started, nothing else running), or a rented pod? Recommended: your card, at a
   time you name, since the pod costs money and your card is the one the numbers are for.
4. **Who reads the blind pairs:** you, or AI readers with your reading of a sample? Recommended: you read at least a sample. The
   question is whether the writing is better, and that is the one judgment that should not be AI judging AI.
