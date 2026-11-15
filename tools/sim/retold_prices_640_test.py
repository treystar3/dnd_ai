"""(f640) A recording made again as another story (other dice from a line on: its inputs from there are other lines) has no kept
price to be held to line by line there, so its kept estimates from that input on are set to today's prices by the tool
(tools/latency.py --retold RECORDING --from N --note TEXT [--over I,J]), never by hand. Held here: the header says when, why and
from where; the inputs before N are the same lines and stay held to their kept prices (one grown dearer is refused: that is
--rekeep's); a recording that tells no other story is refused; a plain input over the limit is kept only when the command names
it, a fight input over the limit never; and the other recordings' prices are left as they were."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
simlib.install(simlib.Stub("warrior", 71))
import tempfile
from pathlib import Path
import yaml
import card_profile, latency
from engine import budget

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

text = Path(latency.BASELINE).read_text(encoding="utf-8")
base = yaml.safe_load(text)
limit = card_profile.budget_limit()
N = "f999: the dice moved, the bot plays another story"


def today(name):
    with budget.priced(**(base.get("priced_at") or {})):
        return {i: round(s, 1) for i, s in card_profile.estimate_inputs(latency.GOLDENS / name, expected=True)}


def block(lines, name):
    at = lines.index(f"  {name}:", lines.index("estimates:"))
    return at, next((k for k in range(at + 1, len(lines)) if not lines[k].startswith("    ")), len(lines))


def stale(name, start, grown=None):
    """The baseline with a recording's prices from `start` on as of another story: every one lower, the last input never priced,
    one too many. `grown`: an input before `start` kept a second under today's price, as if its line had grown dearer since."""
    lines = text.split("\n")
    at, end = block(lines, name)
    now = today(name)
    head = [x for x in lines[at + 1:end] if int(x.split(":")[0]) < start]
    if grown is not None:
        head = [f"    {grown}: {round(now[grown] - 1.0, 1)}" if x.startswith(f"    {grown}: ") else x for x in head]
    rows = [f"    {i}: {round(max(0.1, s - 1.0), 1)}" for i, s in sorted(now.items()) if i >= start][:-1] + ["    999: 5.0"]
    return "\n".join(lines[:at + 1] + head + rows + lines[end:])


with tempfile.TemporaryDirectory() as d:
    kept = Path(d) / "baseline.yaml"
    for name, start in (("stub_fight", 0), ("stub_short", 5)):
        now = today(name)
        new = {i: s for i, s in now.items() if i >= start}
        before = {int(i): s for i, s in base["estimates"][name].items() if int(i) < start}
        fights = latency.fight_inputs(latency.GOLDENS / name)
        plain_over = sorted(i for i, s in new.items() if s > limit and i not in fights)
        kept.write_text(text, encoding="utf-8", newline="")
        said = latency.retold(name, N, start, path=kept, over=plain_over)
        check(f"{name}: with its prices kept as they stand it tells no other story: refused, nothing written", said.startswith("refused")
              and "no other story" in said and kept.read_text(encoding="utf-8") == text, said)
        old = stale(name, start)
        kept.write_text(old, encoding="utf-8", newline="")
        check(f"{name}: against another story's prices the gate fails", bool(latency.gate(base=latency._yaml(kept)).get(name)))
        said = latency.retold(name, "", start, path=kept, over=plain_over)
        check(f"{name}: a retelling with no reason is refused, nothing written", said.startswith("refused") and "--note" in said
              and kept.read_text(encoding="utf-8") == old, said)
        if plain_over:
            said = latency.retold(name, N, start, path=kept)
            check(f"{name}: plain inputs over the limit that the command does not name are refused, nothing written, and named in the refusal",
                  said.startswith("refused") and all(str(i) in said for i in plain_over) and kept.read_text(encoding="utf-8") == old, said)
            said = latency.retold(name, N, start, path=kept, over=plain_over + [start])
            check(f"{name}: ...and so is naming one that is not over it", said.startswith("refused") and kept.read_text(encoding="utf-8") == old, said)
        low = min(now[i] for i in fights if i >= start) - 0.5
        said = latency.retold(name, N, start, path=kept, over=[i for i, s in new.items() if s > low and i not in fights], limit=low)
        check(f"{name}: a fight input over the limit is never kept, with every plain one named: refused for the fight, nothing written",
              said.startswith("refused") and "fight" in said and kept.read_text(encoding="utf-8") == old, said)
        if before:
            g = max(before)
            grown = stale(name, start, grown=g)
            kept.write_text(grown, encoding="utf-8", newline="")
            said = latency.retold(name, N, start, path=kept, over=plain_over)
            check(f"{name}: a line before the parting grown dearer than kept is not the retelling's to set: refused, nothing written",
                  said.startswith("refused") and "--rekeep" in said and f"input {g} " in said and kept.read_text(encoding="utf-8") == grown, said)
            said = latency.retold(name, N, g, path=kept, over=plain_over)
            check(f"{name}: ...and it is set only by naming the parting earlier, in the open",
                  not said.startswith("refused") and f"--from {g})" in kept.read_text(encoding="utf-8"), said)
            kept.write_text(old, encoding="utf-8", newline="")
        said = latency.retold(name, N, start, path=kept, over=plain_over, today="2026-01-01")
        after = kept.read_text(encoding="utf-8")
        got = yaml.safe_load(after)
        check(f"{name}: from input {start} on its kept prices are today's, whole: no input of the old story left, none of the new one missing",
              {i: s for i, s in got["estimates"][name].items() if i >= start} == new,
              [(i, got["estimates"][name].get(i), new.get(i)) for i in set(new) ^ {i for i in got["estimates"][name] if i >= start}][:4])
        check(f"{name}: ...the {len(before)} before it are kept as they were, not set to today's",
              {i: s for i, s in got["estimates"][name].items() if i < start} == before,
              ({i: s for i, s in got["estimates"][name].items() if i < start}, before))
        check(f"{name}: ...the other recordings' prices and everything else in the file as they were",
              {k: v for k, v in got.items() if k != "estimates"} == {k: v for k, v in base.items() if k != "estimates"}
              and all(got["estimates"][g] == base["estimates"][g] for g in base["estimates"] if g != name))
        head = after[:after.index("\nnight:")]
        check(f"{name}: ...and the header says when, by what, from where, why, and which plain inputs it keeps over the limit",
              "2026-01-01" in head and f"--retold {name} --from {start})" in head and "f999" in head
              and all(line.startswith("#") for line in head.split("\n")) and (not plain_over or "over the limit" in head), head[-600:])
        check(f"{name}: the gate then holds on it, and the limit with it",
              latency.gate(base=latency._yaml(kept))[name] == [] and latency.over_limit(base=latency._yaml(kept))[name] == [],
              (latency.gate(base=latency._yaml(kept))[name], latency.over_limit(base=latency._yaml(kept))[name]))
        check(f"{name}: said: {said[:90]}", name in said and f"{len(new)} inputs from {start} on" in said, said)
    kept.write_text(text, encoding="utf-8", newline="")
    said = latency.retold("stub_nowhere", N, path=kept)
    check("a recording the baseline does not keep is refused, nothing written", said.startswith("refused") and kept.read_text(encoding="utf-8") == text, said)
    said = latency.retold("stub_party", N, path=kept)
    check("a recording that was not made again is refused, nothing written", said.startswith("refused") and kept.read_text(encoding="utf-8") == text, said)

check("the kept baseline holds the gate and the limit on the three recordings as they stand",
      not any(latency.gate().values()) and not any(latency.over_limit(base=base).values()), (latency.gate(), latency.over_limit(base=base)))

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
