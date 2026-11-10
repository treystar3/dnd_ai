"""(f567) A fight's improvisation vocabulary lives in data (combat.yaml improv.effects), read by the resolver and the scene, and is held
to the code at start-up: every effect the resolver handles is in the data and nothing else is, each with what it is about, its odds
and the words that name it. Moving it changed nothing: the same effects, odds, words and readings as the table it replaced."""
import copy, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 67))
from engine import combat_improv, data_check

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

# the table as it stood in engine/combat_improv.py before the move
OLD = {
    "read_opening": ("watching it, studying how it moves, waiting for an opening, reading its guard, biding your time", 10,
                     ("watch", "opening", "study", "wait for", "bide", "its guard", "a gap")),
    "break_engagement": ("getting away, slipping free, putting something between you and them, escaping their reach", 0,
                         ("away", "escape", "between", "back off", "slip")),
    "gain_position": ("climbing, high ground, a vantage point, getting on top of something", 0,
                      ("climb", "high", "up ", "vantage", "leap onto", "on top")),
    "create_cover": ("cover, a shield of furniture or terrain, ducking behind something, blocking their line", 5,
                     ("cover", "behind", "barricade", "shield")),
    "distract": ("distracting, feinting, throwing sand or a cloak, drawing its eyes away, a trick", 5,
                 ("distract", "sand", "feint", "throw my", "trick", "eyes")),
    "force_move": ("pushing, tripping, knocking them into or off something, driving them back", -5, ("push", "shove", "trip", "knock", "drive")),
    "disable": ("tangling, pinning, blinding, jamming, fouling their weapon or legs", -10, ("tangle", "pin", "blind", "net", "jam", "foul")),
    "damage": ("hurting them with the surroundings: a dropped beam, a kicked brazier, a rockslide", -5,
               ("drop", "kick", "topple", "collapse", "brazier", "rocks")),
}

# ---- the same vocabulary, from data
check("the resolver reads the effects in the same order", list(combat_improv.EFFECTS) == list(OLD), list(combat_improv.EFFECTS))
check("...each about the same thing at the same odds", all(combat_improv.EFFECTS[k]["about"] == a and combat_improv.EFFECTS[k]["odds"] == o
                                                          for k, (a, o, _) in OLD.items()))
check("...named by the same words", all(tuple(combat_improv.FALLBACK_WORDS[k]) == w for k, (_, _, w) in OLD.items()),
      {k: combat_improv.FALLBACK_WORDS.get(k) for k in OLD})

def old_reading(words):
    low = words.lower()
    return next((k for k, (_, _, ws) in OLD.items() if any(w in low for w in ws)), "distract")

LINES = ["I watch the troll and look for an opening", "I kick the brazier over onto it", "I shove it back off the ledge",
         "I throw sand in its eyes", "I climb onto the cart", "I duck behind the barrels", "I jam my lance into its knee",
         "I slip away between the stalls", "I sing a little song", "I net the wolf", "I bring the rocks down on them"]
check("the same lines read as the same effects", all(combat_improv.effect_by_words(l) == old_reading(l) for l in LINES),
      [(l, combat_improv.effect_by_words(l), old_reading(l)) for l in LINES if combat_improv.effect_by_words(l) != old_reading(l)])

# ---- held to the code at start-up
check("the real data has no problems", data_check.improv_problems() == [], data_check.improv_problems())
I = copy.deepcopy(data_check._load("data/rules/combat.yaml")["improv"])
I["effects"]["distract"].pop("about")
I["effects"]["disable"]["odds"] = "hard"
I["effects"]["damage"]["words"] = []
I["effects"]["juggle"] = {"about": "juggling", "odds": 0, "words": ["juggle"]}
del I["effects"]["force_move"]
found = data_check.improv_problems(I)
for what in ("distract", "disable", "damage", "juggle", "force_move"):
    check(f"a broken row is named: {what}", any(what in p for p in found), found)
check("...and the start-up check runs it", "improv_problems" in open("engine/data_check.py", encoding="utf-8").read().split("def check()")[1].split("\ndef ")[0])

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
