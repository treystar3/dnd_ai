"""Print names built from each people's sounds (data/world/name_sounds.yaml, f346), to read while writing or tuning them.

    python tools/name_samples.py                 10 full names for every people, men and women alternating
    python tools/name_samples.py dwarf 40        40 for one people
    python tools/name_samples.py --seed 3        another draw (the same seed always gives the same names)
"""
import argparse
import random
import sys

sys.path.insert(0, ".")
from npc import names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("people", nargs="?", default="")
    ap.add_argument("count", nargs="?", type=int, default=10)
    ap.add_argument("--seed", type=int, default=1)
    args = ap.parse_args()
    peoples = [args.people] if args.people else list(names.sounds()["peoples"])
    for people in peoples:
        rng = random.Random(f"{args.seed}:{people}")
        print(f"\n{people}")
        for i in range(args.count):
            gender = "male" if i % 2 == 0 else "female"
            print(f"  {'m' if gender == 'male' else 'f'}  {names.build(people, gender, rng)} {names.build(people, 'family', rng)}")


if __name__ == "__main__":
    main()
