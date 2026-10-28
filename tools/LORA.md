# Teaching the model this game (LoRA)

The game decides; the model only writes. Every call it makes is logged with its prompt, the answer, the validator's reason when the
answer was sent back, and the retry that passed. That log is a dataset, and a LoRA adapter trained on it keeps the base model and adds
the game's habits: shorter prompts (the latency lever), fewer answers sent back, a consistent voice without the rule stack.

Rules and numbers: `data/rules/lora.yaml`. Tools: `tools/lora_dataset.py`, `tools/lora_eval.py`, `tools/lora_train.py`.

## 1. Collect

Night runs already log every call whole; since f361 they also keep every system prompt in full (`LOG_FULL_PROMPTS`). Keep each run's
folder. A two-hour run holds about 570 townsfolk replies, 700 narrations and 1,200 interpretations; five or six nights give the ten to
twenty thousand examples a first adapter wants. Freeze the prompts of the tasks you mean to train while collecting: an adapter learns the
prompts it was trained against.

## 2. Build the data

    python tools/lora_dataset.py --runs-dir logs/nightrun --out lora/data

The newest run is held out for evaluation (`--holdout` names one). Per task, under `lora/data/train/` and `lora/data/eval/`:

- `<task>.sft.jsonl`: accepted answers, `{"messages": [system, user, assistant]}`, filtered once more by the habits the game only nudges
  (two trailing participles, a stock opener, trailing off twice). The draft a rewrite replaced is never learned from.
- `<task>.pairs.jsonl`: a rejected draft against the answer that replaced it, same prompt, `{"prompt", "chosen", "rejected"}`: the
  gateway's retries and the narrator's rewrites. These teach exactly what the validators police.

`--prompts short` (the default) trains against the short system prompts in `lora.yaml` instead of the game's long ones, so the model
learns to behave as if the rules were there; at play time the rule prompt is then dropped. `--prompts full` keeps the game's own.
`lora/data/summary.md` says what was kept, what was dropped and why, and which rejection reasons the pairs carry.

## 3. Train

    python tools/lora_train.py --task npc_conversation --data lora/data/train --out lora/adapters/npc_conversation --dry-run
    python tools/lora_train.py --task npc_conversation --data lora/data/train --out lora/adapters/npc_conversation --stage sft
    python tools/lora_train.py --task npc_conversation --data lora/data/train --out lora/adapters/npc_conversation --stage dpo --from lora/adapters/npc_conversation/adapter

Needs a GPU and `pip install torch transformers peft trl datasets accelerate bitsandbytes`; `--load-4bit` fits a 12B base on a 24 GB
card. On one rented 80 GB card a pass over twenty thousand examples is a few hours. Mix in a general chat set with `--mix` (about 15%,
`lora.yaml train.general_mix`) so the model keeps reading ordinary English, which the interpreter depends on. The dry run checks the
files and writes the Modelfile without importing torch.

## 4. Measure before trusting it

    python tools/lora_eval.py lora/data/eval/npc_conversation.sft.jsonl --model gemma4:12b --model meravia-npc_conversation --limit 80

Every held-out prompt goes to each model; the answers are scored the way the game judges them, without a model: fits the contract,
trailing participles per sentence, stock openers, trailing off, stale phrases, the measurable parts of the kit broken, length, seconds.
The logged answers score as the row `logged`. The interpreter has its own evaluator, `tools/interp_eval.py --live`. An adapter is better
only if these move and the stub suite (`tools/run_suite.py`) still passes, since that checks the engine around the model.

## 5. Ship it

    ollama create meravia-npc_conversation -f lora/adapters/npc_conversation/Modelfile

The adapter is a file of tens of megabytes that Ollama loads over the base model. Point the task at the new tag (`config.MODEL`, or a
per-task model once the gateway has one) and, if the adapter was trained on short prompts, drop the matching rules from that task's
prompt builder: that is the moment the turn gets faster. A night run with the new tag is the last test.

## Order of attack

The interpreter first: classification-shaped, its evaluator exists, its prompts are the most stable, and a small tuned model could
replace a 1.2 second call with a faster one. The narrator and the townsfolk second, by preference pairs, because that is where the
habits live. Each cycle is measure, train, measure again.
