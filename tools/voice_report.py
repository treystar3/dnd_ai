"""(f350) How different people sound, measured from a run's logs/llm_calls.jsonl.

    python tools/voice_report.py path/to/llm_calls.jsonl [--samples N]

Reads every townsperson reply (npc_conversation) and hire reply (hire_chat) and reports: how many people spoke and how much; the four-word
runs said by several different people (the house voice); the stock openers; per speaker, words a line, stock openers, questions back and
trailing dots; and the test that matters: whether a person's vocabulary is more like their own earlier lines than like a stranger's. Then a
few people side by side. Run it after a night run to see whether the voice kit (engine/voices.py) is doing its work: the overlap of a person
with themselves should sit well above their overlap with others, and the house list should be short."""
from __future__ import annotations

import argparse, itertools, json, random, re, statistics as st, sys
from collections import Counter, defaultdict

STOP = set("the a an and or but of to in on at for with from by as is are was were be been it its i you your we they them their he she his her him this that these those there here not no yes do does did done have has had will would can could should may might if then than so just only all any some more most much very too also about into out up down over under off back again still what which who whom when where why how my me our us".split())


def words(s: str) -> list[str]:
    return [w for w in re.findall(r"[a-z']+", s.lower()) if w not in STOP and len(w) > 2]


def ngrams(s: str, n: int = 4) -> set[str]:
    w = re.findall(r"[a-z']+", s.lower())
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def opener(s: str) -> str:
    m = re.match(r"[\"“\s']*([A-Za-z]+)", s or "")
    return m.group(1).lower() if m else ""


def jac(a, b) -> float:
    A, B = set(a), set(b)
    return len(A & B) / max(1, len(A | B))


def load(path: str):
    speakers: dict[str, dict] = {}
    hires: dict[str, list[str]] = defaultdict(list)
    for line in open(path, encoding="utf-8"):
        r = json.loads(line)
        if r.get("error") or r.get("attempt", 0) != 0 or r.get("task") not in ("npc_conversation", "hire_chat"):
            continue
        u = next((m["content"] for m in r["messages"] if m["role"] == "user"), "")
        try:
            out = json.loads(r["raw"]) if isinstance(r["raw"], str) else r["raw"]
        except Exception:
            continue
        sp = (out or {}).get("speech", "") or ""
        if not sp.strip():
            continue
        if r["task"] == "npc_conversation":
            m = re.search(r"YOU ARE: ([^,\n]+), an? ([\w-]+) ([\w ]+?) at ([^\n.]+)", u)
            if not m:
                continue
            name, people, role, place = m.groups()
            d = speakers.setdefault(name, {"people": people, "role": role, "place": place, "lines": [],
                                            "kit": re.findall(r"^- (.*)", u.split("HOW YOU TALK")[1].split("\n\n")[0], re.M) if "HOW YOU TALK" in u else []})
            d["lines"].append(sp)
        else:
            m = re.search(r"WHO YOU ARE\n\s*(.*?)\n", u)
            who = (re.search(r"A hired \w+, (.*?)\.", m.group(1)) if m else None)
            hires[(who.group(1) if who else "a hire")[:40]].append(sp)
    return speakers, hires


def report(path: str, samples: int = 5) -> None:
    speakers, hires = load(path)
    big = {k: v for k, v in speakers.items() if len(v["lines"]) >= 8}
    print(f"townsfolk: {len(speakers)} people, {sum(len(v['lines']) for v in speakers.values())} lines; {len(big)} people with 8+ lines")
    if not speakers:
        return
    by_phrase: dict[str, set[str]] = defaultdict(set)
    for k, v in speakers.items():
        for l in v["lines"]:
            for g in ngrams(l):
                if sum(1 for x in g.split() if x not in STOP) >= 2:
                    by_phrase[g].add(k)
    house = sorted(((len(s), g) for g, s in by_phrase.items() if len(s) >= 4), reverse=True)[:20]
    print("\nTHE HOUSE VOICE: four-word runs said by 4+ different people (fewer, and shorter, is better)")
    for n, g in house:
        print(f"  {n:3d}  {g}")
    if not house:
        print("  (none)")
    op = Counter(opener(l) for v in speakers.values() for l in v["lines"])
    total = sum(op.values())
    print("\nOPENERS: " + ", ".join(f"{w} {n / total:.0%}" for w, n in op.most_common(8)))
    rows = []
    for k, v in sorted(big.items(), key=lambda kv: -len(kv[1]["lines"])):
        L = v["lines"]
        rows.append((k, v, len(L), st.mean(len(l.split()) for l in L),
                     sum(opener(l) in ("well", "oh", "ah", "aye", "hm", "hmm", "right", "now", "look") for l in L) / len(L),
                     sum("?" in l for l in L) / len(L), sum("..." in l for l in L) / len(L)))
    print("\nPER PERSON (8+ lines): lines, words a line, stock openers, asks back, trailing dots")
    for k, v, n, wl, stock, ask, dots in rows[:20]:
        print(f"  {k:26s} {v['role']:16s} {n:3d}  {wl:5.1f}  {stock:4.0%}  {ask:4.0%}  {dots:4.0%}")
    if len(rows) >= 2:
        print(f"  spread: words a line {min(r[3] for r in rows):.0f}..{max(r[3] for r in rows):.0f}; asks back {min(r[5] for r in rows):.0%}..{max(r[5] for r in rows):.0%}")
        keys = [r[0] for r in rows]
        within = [jac(words(" ".join(speakers[k]['lines'][:len(speakers[k]['lines']) // 2])), words(" ".join(speakers[k]['lines'][len(speakers[k]['lines']) // 2:]))) for k in keys]
        across = [jac(words(" ".join(speakers[a]['lines'])), words(" ".join(speakers[b]['lines']))) for a, b in itertools.combinations(keys, 2)]
        print(f"\nTHE TEST: vocabulary overlap of a person with their own earlier lines {st.mean(within):.2f} vs with a stranger {st.mean(across):.2f}"
              f" (a person should be more like themselves: the first well above the second)")
    rng = random.Random(4)
    pick = [r for r in rows if r[2] >= 10]
    rng.shuffle(pick)
    print(f"\nSIDE BY SIDE ({min(samples, len(pick))} people, 3 lines each):")
    seen, shown = set(), 0
    for k, v, *_ in pick:
        if v["role"] in seen:
            continue
        seen.add(v["role"]); shown += 1
        print(f"\n{k} ({v['people']} {v['role']})" + (f"\n  kit: {' | '.join(v['kit'])}" if v["kit"] else ""))
        for l in rng.sample(v["lines"], 3):
            print(f"   - {l[:200]}")
        if shown >= samples:
            break
    if hires:
        print("\nHIRES:")
        for k, L in sorted(hires.items(), key=lambda kv: -len(kv[1]))[:6]:
            print(f"  {k:40s} {len(L):3d} lines, {st.mean(len(l.split()) for l in L):.1f} words, {sum(opener(l) in ('well', 'oh', 'ah', 'aye') for l in L) / len(L):.0%} stock openers")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("path")
    ap.add_argument("--samples", type=int, default=5)
    a = ap.parse_args()
    report(a.path, a.samples)
