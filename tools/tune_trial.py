"""Trial of rank balance: a typically geared character against each rank's examiner, nobody able to die.

    python tools/tune_trial.py [rank_of_examiner (normal|elite)] [level_edge]
"""
import random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from engine import combat, party, quests
from tools.tune import geared

G = quests.G


def trial_rates(rank=None, edge=None, runs=120, seed=7, over=0):
    rank = rank or G["trial"]["rank"]
    out = []
    for letter in quests.LETTERS[1:]:
        lv = G["ranks"][letter]["requires"]["level"] + over
        rng = random.Random(seed)
        wins = rounds = 0
        n = 0
        for i in range(runs):
            role = G["trial"]["roles"][i % len(G["trial"]["roles"])]
            p = combat.fighter_from_character(geared(lv, rng))
            lvl = max(G["ranks"][letter]["requires"]["level"], lv) + (G["trial"]["level_edge"][letter] if edge is None else edge) + (G["trial"]["master_edge"] if letter == quests.LETTERS[-1] else 0)
            e = combat.fighter_from_creature(party.Shape({"id": "x", "name": "Ex", "role": role, "level": lvl}), lvl, rank, "e1", "Ex", "engaged")
            e.side = "enemy"
            c = combat.Combat(fighters=[p, e])
            c.duel = True
            res = combat.simulate(c, rng)
            n += 1; rounds += res.round - 1
            wins += res.over == "victory"
        out.append((letter, lv, wins / n, rounds / n))
    return out


if __name__ == "__main__":
    rank = sys.argv[1] if len(sys.argv) > 1 else None
    edge = int(sys.argv[2]) if len(sys.argv) > 2 else None
    print(f"examiner {rank or G['trial']['rank']}, edge {edge if edge is not None else 'from guild.yaml'}: rank  level  win  rounds")
    for letter, lv, w, r in trial_rates(rank, edge):
        print(f"  {letter}  {lv:>4}  {w:>5.0%}  {r:>5.1f}")
