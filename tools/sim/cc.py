import sys, random, collections
import simlib
res = collections.Counter()
for cls in sys.argv[1:]:
    ok = 0
    for seed in range(40):
        st = simlib.Stub(cls, seed); simlib.install(st)
        try:
            simlib.make_character(cls, random.Random(seed)); ok += 1
        except Exception as e:
            err = str(e)[:80]
    print(cls, ok, "/40", "" if ok == 40 else err)
