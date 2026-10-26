"""Which names can the sounds make that are ordinary words? (f346) Lists every name data/world/name_sounds.yaml can build, for every
people and kind, and prints those found in a word list - to add to `words` there, or to leave buildable on purpose (Tom, Gale).

    python tools/name_words.py WORDLIST            WORDLIST: a plain text file, one word per line, most common first
    python tools/name_words.py WORDLIST --top 20000

Any list works; the one used for name_sounds.yaml was the 20,000 commonest English words from the wordfreq project's data. Human
and half-elf family names (English surnames) and gnome family names (silly compounds) are words on purpose and are not checked.
"""
import argparse
import sys

sys.path.insert(0, ".")
from npc import names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("wordlist")
    ap.add_argument("--top", type=int, default=20000, help="use only the first N words of the list")
    args = ap.parse_args()
    words = {}
    with open(args.wordlist, encoding="utf-8", errors="ignore") as f:
        for i, line in enumerate(f):
            if i >= args.top:
                break
            w = line.split("\t")[0].strip().lower()
            if w:
                words.setdefault(w, i)
    found = {}
    for people, rules in names.sounds()["peoples"].items():
        for kind in ("male", "female", "family"):
            if kind == "family" and (people == "gnome" or rules.get("family_from") or people == "human"):
                continue
            made = names.possible(people, kind)
            hits = sorted((n for n in made if n.lower() in words), key=lambda n: words[n.lower()])
            print(f"{people} {kind}: {len(made)} possible, {len(hits)} words{': ' + ', '.join(hits) if hits else ''}")
            for n in hits:
                found.setdefault(n, []).append(f"{people} {kind}")
    print(f"\n{len(found)} buildable names are words.")


if __name__ == "__main__":
    main()
