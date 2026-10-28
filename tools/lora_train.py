"""(f361) Train a LoRA adapter on what tools/lora_dataset.py wrote.

    python tools/lora_train.py --task npc_conversation --data lora/data/train --out lora/adapters/npc_conversation --dry-run
    python tools/lora_train.py --task npc_conversation --data lora/data/train --out lora/adapters/npc_conversation --stage sft
    python tools/lora_train.py --task npc_conversation --data lora/data/train --out lora/adapters/npc_conversation --stage dpo --from lora/adapters/npc_conversation

Two stages. sft learns from the accepted answers (<task>.sft.jsonl); dpo then learns the difference between a rejected draft and the
answer that replaced it (<task>.pairs.jsonl), starting from the sft adapter (--from). The base model, rank, learning rate and the rest
come from data/rules/lora.yaml train, and any of them can be given here.

--dry-run reads the files, checks their shape, counts examples and rough tokens, and writes the Modelfile Ollama needs next to where the
adapter would go, without importing torch: it runs anywhere, including the test suite. A real run needs a GPU and
    pip install torch transformers peft trl datasets accelerate bitsandbytes
and the base model's weights from Hugging Face (the first run downloads them). --load-4bit holds the base in 4-bit (QLoRA) so a 12B
model trains on a 24 GB card, slowly; on an 80 GB card leave it off.

When it is done: `ollama create meravia-<task> -f <out>/Modelfile`, point config.MODEL at that tag for the task, and score it with
tools/lora_eval.py before trusting it."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml

L = yaml.safe_load((ROOT / "data" / "rules" / "lora.yaml").read_text(encoding="utf-8"))
T = L.get("train") or {}


def read_jsonl(path: Path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out


def check_shape(rows: list[dict], stage: str) -> list[str]:
    """What is wrong with the file for this stage, one line each; empty when it will train."""
    bad = []
    for i, r in enumerate(rows):
        if stage == "sft":
            m = r.get("messages")
            if not (isinstance(m, list) and [x.get("role") for x in m] == ["system", "user", "assistant"] and all(x.get("content") for x in m)):
                bad.append(f"row {i}: needs messages system, user, assistant, each with content")
        else:
            if not (isinstance(r.get("prompt"), list) and r.get("chosen") and r.get("rejected")):
                bad.append(f"row {i}: needs prompt (messages), chosen and rejected")
            elif r["chosen"][0].get("content") == r["rejected"][0].get("content"):
                bad.append(f"row {i}: chosen and rejected are the same")
        if len(bad) > 8:
            bad.append("...")
            break
    return bad


def rough_tokens(rows: list[dict]) -> int:
    chars = 0
    for r in rows:
        for m in r.get("messages") or r.get("prompt") or []:
            chars += len(m.get("content", ""))
        for k in ("chosen", "rejected"):
            for m in r.get(k) or []:
                chars += len(m.get("content", ""))
    return chars // 4


def modelfile(base_tag: str, adapter_dir: str) -> str:
    return (f"# Built by tools/lora_train.py. `ollama create meravia-<task> -f Modelfile`, then set config.MODEL (or the task's model) to that tag.\n"
            f"FROM {base_tag}\nADAPTER {adapter_dir}\n")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--task", required=True)
    ap.add_argument("--data", default="lora/data/train")
    ap.add_argument("--out", required=True, help="where the adapter and its Modelfile go")
    ap.add_argument("--stage", choices=("sft", "dpo"), default="sft")
    ap.add_argument("--from", dest="start_from", help="an adapter to continue from (dpo after sft)")
    ap.add_argument("--base", default=T.get("base"), help="Hugging Face id of the base model")
    ap.add_argument("--base-tag", default=None, help="the Ollama tag the adapter is applied to (default: config.MODEL)")
    ap.add_argument("--rank", type=int, default=int(T.get("rank", 16)))
    ap.add_argument("--alpha", type=int, default=int(T.get("alpha", 32)))
    ap.add_argument("--dropout", type=float, default=float(T.get("dropout", 0.05)))
    ap.add_argument("--epochs", type=float, default=float(T.get("epochs", 1)))
    ap.add_argument("--lr", type=float, default=float(T.get("learning_rate", 1e-4)))
    ap.add_argument("--max-length", type=int, default=int(T.get("max_length", 6144)))
    ap.add_argument("--mix", help="a general chat jsonl (messages rows) mixed in at lora.yaml train.general_mix, so the model keeps its English")
    ap.add_argument("--load-4bit", action="store_true")
    ap.add_argument("--dry-run", action="store_true", help="check the data and write the Modelfile; no training, no torch")
    args = ap.parse_args(argv)

    kind = "sft" if args.stage == "sft" else "pairs"
    path = Path(args.data) / f"{args.task}.{kind}.jsonl"
    if not path.exists():
        print(f"no {path}: run tools/lora_dataset.py first")
        return 2
    rows = read_jsonl(path)
    problems = check_shape(rows, args.stage)
    if problems:
        print("\n".join(problems))
        return 2
    mix = read_jsonl(Path(args.mix)) if args.mix else []
    share = float(T.get("general_mix", 0.15))
    take = min(len(mix), int(len(rows) * share / max(1e-9, 1 - share))) if mix else 0
    import config
    base_tag = args.base_tag or config.MODEL
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "Modelfile").write_text(modelfile(base_tag, "./adapter"), encoding="utf-8")
    print(f"{args.stage} on {path}: {len(rows)} examples, about {rough_tokens(rows):,} tokens" + (f", plus {take} general examples" if take else ""))
    print(f"base {args.base} (Ollama tag {base_tag}), rank {args.rank}, alpha {args.alpha}, lr {args.lr}, epochs {args.epochs}, max length {args.max_length}")
    print(f"Modelfile written to {out / 'Modelfile'}")
    if args.dry_run:
        return 0

    # ---- the real thing: imported here so the dry run and the tests never need torch
    import torch
    from datasets import Dataset
    from peft import LoraConfig, PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    tok = AutoTokenizer.from_pretrained(args.base)
    quant = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.bfloat16) if args.load_4bit else None
    model = AutoModelForCausalLM.from_pretrained(args.base, quantization_config=quant, torch_dtype=torch.bfloat16, device_map="auto")
    if args.start_from:
        model = PeftModel.from_pretrained(model, args.start_from, is_trainable=True)
        peft_config = None
    else:
        peft_config = LoraConfig(r=args.rank, lora_alpha=args.alpha, lora_dropout=args.dropout, bias="none", task_type="CAUSAL_LM",
                                 target_modules=list(T.get("targets") or ["q_proj", "k_proj", "v_proj", "o_proj"]))
    data = Dataset.from_list(rows + mix[:take])
    if args.stage == "sft":
        from trl import SFTConfig, SFTTrainer
        cfg = SFTConfig(output_dir=str(out / "checkpoints"), num_train_epochs=args.epochs, learning_rate=args.lr, max_length=args.max_length,
                        per_device_train_batch_size=1, gradient_accumulation_steps=8, logging_steps=10, save_strategy="epoch", bf16=True,
                        gradient_checkpointing=True, report_to=[])
        trainer = SFTTrainer(model=model, args=cfg, train_dataset=data, processing_class=tok, peft_config=peft_config)
    else:
        from trl import DPOConfig, DPOTrainer
        cfg = DPOConfig(output_dir=str(out / "checkpoints"), num_train_epochs=args.epochs, learning_rate=args.lr / 2, max_length=args.max_length,
                        per_device_train_batch_size=1, gradient_accumulation_steps=8, logging_steps=10, save_strategy="epoch", bf16=True,
                        gradient_checkpointing=True, beta=0.1, report_to=[])
        trainer = DPOTrainer(model=model, args=cfg, train_dataset=data, processing_class=tok, peft_config=peft_config)
    trainer.train()
    trainer.model.save_pretrained(str(out / "adapter"))
    tok.save_pretrained(str(out / "adapter"))
    print(f"adapter saved under {out / 'adapter'}; next: ollama create meravia-{args.task} -f {out / 'Modelfile'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
