"""(f346) Names built from each people's sounds: every people can build men's, women's and family names; every name keeps its
people's rules (length, how many vowels or consonants run together) and the shared ones (no piece said twice running); the same seed
gives the same names; half-elves take human family names. There is no list of forbidden names - variety keeps any one name rare - so
the test pins the variety: thousands of possible names for every kind, and no name drawn often."""
import random, re, subprocess, sys
from collections import Counter
sys.path.insert(0, ".")
from npc import names
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
S = names.sounds()
check("every people of the world has sounds", set(world.peoples) <= set(S["peoples"]), set(world.peoples) - set(S["peoples"]))
for people in world.peoples:
    rules = S["peoples"][people]
    for kind in ("male", "female", "family"):
        rng = random.Random(f"t:{people}:{kind}")
        made = [names.build(people, kind, rng) for _ in range(300)]
        again = [names.build(people, kind, random.Random(f"t:{people}:{kind}")) for _ in range(1)]
        r = names._rules(people, kind)
        lo, hi = r.get("length", S["length"])
        check(f"{people} {kind}: every name keeps its length", all(lo <= len(n) <= hi for n in made), [n for n in made if not lo <= len(n) <= hi][:5])
        check(f"{people} {kind}: no letter three times running, no piece said twice running",
              not [n for n in made if re.search(r"(.)\1\1", n.lower()) or re.search(r"(.{2,})\1", n.lower())])
        check(f"{people} {kind}: capitalised, letters only", all(n[0].isupper() and n[1:].islower() and n.isalpha() for n in made), made[:5])
        check(f"{people} {kind}: variety (at least 40% of 300 differ)", len(set(made)) >= 120, len(set(made)))
        check(f"{people} {kind}: the same seed gives the same name", again[0] == made[0], (again[0], made[0]))
check("half-elves take human family names", names._rules("half_elf", "family") is S["peoples"]["human"])

# one-syllable first names for every people but the elves; elves never have one
for people in world.peoples:
    made = [names.build(people, g, random.Random(f"one:{people}:{g}:{i}")) for g in ("male", "female") for i in range(400)]
    ones = [n for n in made if names.syllables(n) == 1]
    if people == "elf":
        check("an elf's name is never one syllable", not ones, ones[:5])
    else:
        check(f"{people}: some first names are one syllable", len(ones) >= 10, (len(ones), made[:6]))
    fams = [names.build(people, "family", random.Random(f"onefam:{people}:{i}")) for i in range(400)]
    short = [n for n in fams if names.syllables(n) == 1]
    if people == "elf":
        check("an elf's family name is never one syllable", not short, short[:5])
    else:
        check(f"{people}: some family names are one syllable", len(short) >= 10, (len(short), fams[:6]))

# syllables are counted as they are said, near enough
for name, n in (("Brom", 1), ("Crane", 1), ("Lyle", 1), ("Aldric", 2), ("Gable", 2), ("Everard", 3), ("Cecilia", 4), ("Theodoric", 4)):
    check(f"'{name}' has {n} syllable{'s' if n > 1 else ''}", names.syllables(name) == n, names.syllables(name))

# humans' names keep the share of short and long names their table sets: 30 in 100 one syllable, 60 two, 8 three, 2 four or more
table = S["peoples"]["human"]["syllables"]
top = max(table)
for kind in ("male", "female", "family"):
    rng = random.Random(f"share:{kind}")
    counts = Counter(min(names.syllables(names.build("human", kind, rng)), top) for _ in range(8000))
    for n, weight in table.items():
        share, want = 100 * counts[n] / 8000, 100 * weight / sum(table.values())
        check(f"human {kind}: {want:.0f} in 100 have {n}{'+' if n == top else ''} syllable{'s' if n > 1 else ''} ({share:.1f})",
              abs(share - want) <= 2, share)

# family names are syllables, not English words run together - except humans' (and half-elves', which are human) and gnomes'
WORDS = ("stone", "iron", "doom", "hide", "fist", "beard", "skull", "moon", "star", "storm", "walker", "apple", "under", "foot",
         "bone", "blood", "fire", "frost", "wind", "flame", "tide", "dawn", "song", "brow", "helm", "fang", "jaw", "axe", "leaf")
for people in ("dwarf", "elf", "halfling", "orc", "genasi", "goliath", "dragonborn"):
    fams = [names.build(people, "family", random.Random(f"fam:{people}:{i}")) for i in range(400)]
    worded = [f for f in fams if any(f.lower().startswith(w) or f.lower().endswith(w) for w in WORDS)]      # a compound begins or ends in a word
    check(f"{people} family names are built from syllables, not words", len(worded) <= 4, worded[:8])
gfam = [names.build("gnome", "family", random.Random(f"fam:gnome:{i}")) for i in range(50)]
check("gnome family names are still tinkers' words run together", any(f.startswith(("Tumble", "Kettle", "Gear", "Cog", "Whistle")) for f in gfam), gfam[:5])

# variety, which is what keeps any one name rare
for people in world.peoples:
    for kind in ("male", "female", "family"):
        room = len(names.possible(people, kind))
        drawn = Counter(names.build(people, kind, random.Random(f"v:{people}:{kind}:{i}")) for i in range(3000)).most_common(1)[0]
        check(f"{people} {kind}: at least 1000 possible names ({room})", room >= 1000, room)
        check(f"{people} {kind}: no name drawn more than 1.5% of the time ({drawn[0]} {drawn[1] / 30:.2f}%)", drawn[1] <= 45, drawn)

# the shared rules on hand-picked cases
h = S["peoples"]["human"]
for name, ok in (("Dordor", False), ("Aaaron", False), ("Wilfred", True), ("Brenna", True), ("Thorin", True),
                 ("Homo", False), ("Thomo", True), ("Shagga", False), ("Dushagmok", True),
                 ("Analiaga", False), ("Vanalith", True), ("Dago", False), ("Dagorakk", True)):
    check(f"'{name}' is {'kept' if ok else 'refused'}", names.acceptable(name, h) is ok)

# the sampler the sounds are tuned with runs
out = subprocess.run([sys.executable, "tools/name_samples.py", "dwarf", "4"], capture_output=True, text=True)
check("tools/name_samples.py prints names", out.returncode == 0 and len(out.stdout.strip().splitlines()) == 5, out.stdout + out.stderr)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
