"""(f346) Names built from each people's sounds: every people can build men's, women's and family names; every name keeps its
people's rules (length, how many vowels or consonants run together) and the shared ones (no rude or repeated pieces, never a name
another story owns); the same seed gives the same names; there is variety; half-elves take human family names."""
import random, re, subprocess, sys
sys.path.insert(0, ".")
from npc import names
from world.loader import load_world

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
S = names.sounds()
taken = {t.lower() for t in S["taken"]}
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
        check(f"{people} {kind}: none is a name another story owns or a blocked word", not [n for n in made if n.lower() in taken])
        check(f"{people} {kind}: no letter three times running, no piece said twice running",
              not [n for n in made if re.search(r"(.)\1\1", n.lower()) or re.search(r"(.{2,})\1", n.lower())])
        check(f"{people} {kind}: capitalised, letters only", all(n[0].isupper() and n[1:].islower() and n.isalpha() for n in made), made[:5])
        check(f"{people} {kind}: variety (at least 40% of 300 differ)", len(set(made)) >= 120, len(set(made)))
        check(f"{people} {kind}: the same seed gives the same name", again[0] == made[0], (again[0], made[0]))
check("half-elves take human family names", names._rules("half_elf", "family") is S["peoples"]["human"])

# the shared rules on hand-picked cases
h = S["peoples"]["human"]
for name, ok in (("Thorin", False), ("Legolas", False), ("Dordor", False), ("Aaaron", False), ("Wilfred", True), ("Brenna", True)):
    check(f"'{name}' is {'kept' if ok else 'refused'}", names.acceptable(name, h) is ok)

# the sampler the sounds are tuned with runs
out = subprocess.run([sys.executable, "tools/name_samples.py", "dwarf", "4"], capture_output=True, text=True)
check("tools/name_samples.py prints names", out.returncode == 0 and len(out.stdout.strip().splitlines()) == 5, out.stdout + out.stderr)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
