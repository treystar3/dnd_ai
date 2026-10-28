"""(f361) Score a model on a held-out run's prompts, against the model it would replace.

    python tools/lora_eval.py lora/data/eval/npc_conversation.sft.jsonl --model gemma4:12b --model meravia-npc --limit 60

Each example's prompt (system and user) goes to every model named, through Ollama with the task's contract as the JSON shape, the way
the gateway sends it. The answers are scored the way the game would judge them, without a model: does the answer fit the contract
(llm/contracts.py, validated without a scene's context), how many sentences end on a trailing participle, how many replies open on a
stock word or trail off, how long they run, and whether they break the measurable parts of the kit the prompt gave them (a sentence
past twenty words for a short-sentence speaker, a question from someone who never asks, two of the words the prompt said were worn out).
The logged answers score too, as the row called 'logged', so a tuned model is read against both the base and what the game accepted.

The task is the file's name (npc_conversation.sft.jsonl); its contract is data/rules/lora.yaml schemas. Writes a Markdown table, to
--out if given. Needs Ollama for any --model; the stub in tests stands in for it."""
from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import yaml

L = yaml.safe_load((ROOT / "data" / "rules" / "lora.yaml").read_text(encoding="utf-8"))


def schema_for(task: str):
    from llm import contracts
    name = (L.get("schemas") or {}).get(task)
    if not name or not hasattr(contracts, name):
        raise SystemExit(f"no contract known for task '{task}' (data/rules/lora.yaml schemas)")
    return getattr(contracts, name)


def examples(path: Path, limit: int | None) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                out.append(json.loads(line))
    return out[:limit] if limit else out


def ask(model: str, prompt: list[dict], schema, max_tokens: int) -> tuple[str, float]:
    """One answer from Ollama, shaped by the contract, timed. The gateway's own client, so a test's stub answers instead."""
    import config
    from llm import gateway
    start = time.perf_counter()
    r = gateway._client.chat(model=model, think=config.THINK, messages=prompt, format=schema.model_json_schema(),
                             options={"temperature": 0.8, "num_ctx": config.NUM_CTX, "num_predict": max_tokens}, keep_alive=config.KEEP_ALIVE)
    return (r.message.content or ""), time.perf_counter() - start


# ---------------------------------------------------------------- scoring

def strings_in(value) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [s for v in value.values() for s in strings_in(v)]
    if isinstance(value, list):
        return [s for v in value for s in strings_in(v)]
    return []


def kit_breaks(user: str, speech: str) -> int:
    """The measurable parts of the kit the prompt carried, broken by this reply: a sentence past twenty words for a short-sentence
    speaker, a question from one who never asks, two of the prompt's worn-out words leaned on."""
    breaks = 0
    if "none past twenty words" in user and any(len(re.findall(r"[A-Za-z'’]+", s)) > 20 for s in re.split(r"(?<=[.!?])\s+", speech)):
        breaks += 1
    if "never asks the stranger anything back" in user and "?" in speech:
        breaks += 1
    m = re.search(r"WORN OUT[^\n]*?:\s*([^\n]+)", user)
    if m:
        from engine import worn
        if len(worn.leaned_on(speech, [w.strip(" .") for w in m.group(1).split(",") if w.strip()])) >= 2:
            breaks += 1
    return breaks


def score(task: str, user: str, raw: str, schema) -> dict:
    from llm.contracts import opener_of
    from scenes.voice import STALE, participle_tails
    s = {"fits": 0, "sentences": 0, "tails": 0, "two_tails": 0, "opener": 0, "dots": 0, "stale": 0, "words": 0, "kit": 0}
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return s
    try:
        schema.model_validate_json(raw)
        s["fits"] = 1
    except Exception:
        pass
    text = " ".join(strings_in(data))
    speech = data.get("speech") or data.get("line") or text if isinstance(data, dict) else text
    sents = [x for x in re.split(r"(?<=[.!?])\s+", text.strip()) if x.strip()]
    tails = participle_tails(text)
    s.update(sentences=len(sents), tails=len(tails), two_tails=int(len(tails) >= 2), opener=int(bool(opener_of(speech))),
             dots=int(speech.count("...") + speech.count("…") >= 2), stale=int(any(p in text.lower() for p in STALE)),
             words=len(text.split()), kit=kit_breaks(user, speech))
    return s


def table(rows: dict[str, list[dict]], seconds: dict[str, list[float]]) -> str:
    head = "| Model | n | Fits | Tails/sentence | 2+ tails | Opener | Trails off | Stale | Kit breaks | Words | Seconds p50 |"
    out = [head, "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for name, ss in rows.items():
        n = len(ss) or 1
        sent = sum(x["sentences"] for x in ss) or 1
        pct = lambda k: f"{100 * sum(x[k] for x in ss) / n:.0f}%"
        secs = seconds.get(name) or []
        out.append(f"| {name} | {len(ss)} | {pct('fits')} | {sum(x['tails'] for x in ss) / sent:.2f} | {pct('two_tails')} | {pct('opener')} | {pct('dots')} | "
                   f"{pct('stale')} | {sum(x['kit'] for x in ss) / n:.2f} | {sum(x['words'] for x in ss) / n:.0f} | "
                   f"{(statistics.median(secs) if secs else 0):.1f} |")
    return "\n".join(out)


def evaluate(path: Path, models: list[str], limit: int | None = None, max_tokens: int = 600) -> tuple[dict, dict]:
    task = path.name.split(".")[0]
    schema = schema_for(task)
    exs = examples(path, limit)
    rows: dict[str, list[dict]] = {"logged": []}
    seconds: dict[str, list[float]] = {}
    for ex in exs:
        msgs = ex["messages"]
        user = msgs[1]["content"]
        rows["logged"].append(score(task, user, msgs[2]["content"], schema))
        for m in models:
            raw, took = ask(m, msgs[:2], schema, max_tokens)
            rows.setdefault(m, []).append(score(task, user, raw, schema))
            seconds.setdefault(m, []).append(took)
    return rows, seconds


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("file", help="an eval file from tools/lora_dataset.py, e.g. lora/data/eval/narrate.sft.jsonl")
    ap.add_argument("--model", action="append", default=[], help="an Ollama model to score; repeat for several (the logged answers always score)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--max-tokens", type=int, default=600)
    ap.add_argument("--out", help="write the table here as Markdown")
    args = ap.parse_args(argv)
    rows, seconds = evaluate(Path(args.file), args.model, args.limit, args.max_tokens)
    text = f"# {Path(args.file).name}\n\n" + table(rows, seconds) + "\n"
    print(text)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
