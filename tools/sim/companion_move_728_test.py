"""(f728) A companion's move (docs/design/28_phase4_plan.md A6). With decide then speak on, the engine settles what a companion
does with what was said to them before they are asked to speak, as it does for a townsperson (f724): one move a reply, from the
same table (data/rules/reply.yaml moves), on a die of its own, told to the model in the move's plain words. A companion needs no
reading of the line (they have nothing to gate and nothing to offer): the move, the feeling and subtext they already have, and
the slip (f727) are the whole decision. What weighs on a companion is felt and shown, never the subject (the subtext rule), so
turning to their own trouble is no move of theirs; and under a move that may be a look alone, the look is not held back. How they are with the one who hired them stands where a townsperson's trust does (the
bond's tier, reply.yaml companion.trust). With the switch off nothing is rolled, told or kept.
Run: python tools/sim/companion_move_728_test.py"""
import copy
import random
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
simlib.quiet_console()
from engine import party, quirks, reply, streams

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


if not hasattr(reply, "companion_weights"):
    check("a companion's move is built (engine/reply.py companion_weights, companion_move)", False)
    sys.exit(1)
R = reply.R
K = R["moves"]["kinds"]
SAYS = {spec["says"]: move for move, spec in K.items()}
HEAD = "WHAT YOU DO IN THIS REPLY"

# ---- the data: how each tier of the bond stands as trust, checked at startup
C = R.get("companion") or {}
tiers = [name for _, name in party.P["bond"]["tiers"]]
check("reply.yaml says how each tier of a companion's bond stands as trust (0 to 100), and the startup check passes",
      set(C.get("trust") or {}) == set(tiers) and all(isinstance(v, int) and 0 <= v <= 100 for v in C["trust"].values()) and reply.problems() == [],
      (C, reply.problems()))
order = [C["trust"][t] for t in tiers]
check("...a closer bond is never less trust", order == sorted(order), order)
for name, change in (("a tier with no number", lambda D: D["companion"]["trust"].pop(tiers[0])),
                     ("a tier the party does not have", lambda D: D["companion"]["trust"].update({"sworn": 80})),
                     ("a number over a hundred", lambda D: D["companion"]["trust"].update({tiers[-1]: 140})),
                     ("no table at all", lambda D: D.pop("companion"))):
    D = copy.deepcopy(R)
    change(D)
    check(f"the startup check refuses {name}", any("companion" in p for p in reply.problems(D)), reply.problems(D))


def hire(bond=15, **more):
    m = {"id": "h_728", "name": "Bram Voss", "role": "fighter", "level": 3, "rank": "F", "permanent": True, "temper": ["blunt", "dry"], "motive": "coin",
         "line": "will not take from the poor", "bond": bond, "memories": [], "said": [], "talk": [], "blurb": "a scarred sellsword", **more}
    quirks.roll(m, random.Random(0))
    return m


# ---- the weights: the same table, the bond where a townsperson's trust is, no stance
low, mid, high = (next(t for t in tiers if C["trust"][t] < R["moves"]["by_trust"]["low"]["below"]),
                  next(t for t in tiers if R["moves"]["by_trust"]["low"]["below"] <= C["trust"][t] < R["moves"]["by_trust"]["high"]["from"]),
                  next(t for t in tiers if C["trust"][t] >= R["moves"]["by_trust"]["high"]["from"]))
floor = {name: f for f, name in party.P["bond"]["tiers"]}
cold, plain, close = (hire(bond=max(floor[t], -50)) for t in (low, mid, high))
check("the hires stand in the tiers meant", [party.bond_tier(m) for m in (cold, plain, close)] == [low, mid, high], [party.bond_tier(m) for m in (cold, plain, close)])
w_cold, w_plain, w_close = (reply.companion_weights(m) for m in (cold, plain, close))
kit = __import__("engine.voices", fromlist=["kit_of"]).kit_of(plain)
check("a companion's moves are the table's own, weighed as a townsperson's of that trust, voice and no stance would be",
      w_plain == reply.weights("none", C["trust"][mid], kit) and set(w_plain) <= set(K), (w_plain, reply.weights("none", C["trust"][mid], kit)))
check("one gone cold turns things aside more and answers less than one who is close; one who is close jokes more",
      w_cold["deflect"] > w_close["deflect"] and w_cold["answer"] < w_close["answer"] and w_close["joke"] > w_cold["joke"], (w_cold, w_close))
never, first = hire(speech={"kit": {"questions": "never"}}), hire(speech={"kit": {"questions": "first"}})
check("the habits of their voice weigh as a townsperson's do: one who never asks questions never asks back, one who asks first asks back more",
      "ask_back" not in reply.companion_weights(never) and reply.companion_weights(first)["ask_back"] > w_plain["ask_back"],
      (reply.companion_weights(never), reply.companion_weights(first)))
needy = [mv for mv, spec in K.items() if spec.get("needs")]
check("a move that needs a concern is never a companion's: what weighs on them is felt and shown, never the subject",
      needy and not any(mv in w for mv in needy for w in (w_cold, w_plain, w_close)), (needy, w_plain))
check("the table says under which moves a look alone is a whole reply", reply.wordless("quiet") and not reply.wordless("answer")
      and any("wordless" in p for p in reply.problems({**R, "moves": {**R["moves"], "kinds": {**K, "quiet": {**K["quiet"], "wordless": "yes"}}}})))

# ---- the roll: its own die, never the same move more than `running` times, the forced move when the game says so
n = int(R["moves"]["running"])
rolled = []
m = hire()
for k in range(200):
    move = reply.companion_move(m, random.Random(k))
    rolled.append(move)
    m["moves"] = (m.get("moves", []) + [move])[-n:]
runs = max(len(list(g)) for g in __import__("itertools").groupby(rolled)) if rolled else 0
check("over many replies a companion makes several different moves, each one of the table's", len(set(rolled)) >= 4 and set(rolled) <= set(K), set(rolled))
check(f"...and never the same one more than {n} times running", runs <= n, runs)
check("when the game has decided what the reply is, the move is the forced one, whatever the die",
      {reply.companion_move(hire(), random.Random(k), forced=True) for k in range(30)} == {R["moves"]["forced"]})

# ---- in a talk
game = simlib.campaign("companion_move_728", minutes=600, location="guild_house")
ws = game.scene
ws.enter(ws.player.location)
m = hire()
ws.player.party = [m]
ws.player.party_mode = "with"
reqs, answers = [], []
OPEN = ("Dry", "Mud", "Long", "Quiet", "Cold", "Fair", "Rough", "Slow", "Easy", "Hard", "Grey", "Kind")


def answer(u):                                  # a new opening and new words each time: the game's own checks send a repeat back
    reqs.append(u)
    answers.append(u)
    return {"speech": f"{OPEN[len(answers) % len(OPEN)]} going, and that makes {len(answers)} times I have told it."}


stub.companion = answer


def talk(words, turn):
    streams.begin(4, turn, words)
    reqs.clear()
    ws.hire_talk(m, words)
    return reqs[0] if reqs else ""             # the first asking: a retry's request ends with why it was sent back


was = R["decide_then_speak"]
try:
    R["decide_then_speak"] = False
    off = talk("How is the road treating you?", 1)
    check("with the switch off a companion is told no move and none is kept", off and HEAD not in off and "moves" not in m, (off[-300:], m.get("moves")))
    R["decide_then_speak"] = True
    seen, kept = [], []
    for t in range(2, 42):
        u = talk(f"How is the road treating you, on day {t}?", t)
        tail = u.split(HEAD, 1)[1] if HEAD in u else ""
        seen.append([mv for says, mv in SAYS.items() if says in tail])
        kept.append(list(m.get("moves") or []))
    check("with it on every reply's request ends by telling them the one move the engine rolled, in the move's plain words",
          all(len(s) == 1 for s in seen) and all(u for u in seen), seen[:5])
    check("...after what was said to them, as a thing settled and never words to say",
          HEAD in u and u.index(HEAD) > u.index("SAYS TO YOU") and "settled" in u.split(HEAD, 1)[1].split("\n")[0], u[-500:])
    check("...the move is kept on the companion for the next roll, never more than the run the rule looks back over",
          all(k and k[-1] == s[0] for k, s in zip(kept, seen) if s) and all(len(k) <= n for k in kept), kept[:5])
    check("...several different moves over a long talk, never one more than the rule allows running",
          len({s[0] for s in seen if s}) >= 3 and max(len(list(g)) for _, g in __import__("itertools").groupby(s[0] for s in seen if s)) <= n, [s[0] for s in seen if s])
    check("what is kept on a companion is a field the party knows (engine/party.py)", party.unclassified(m) == [], party.unclassified(m))

    def move_of(member, k, line="line"):
        streams.begin(4, 1000 + k, f"{line} {k}")
        return ws.hire_move(member, f"{line} {k}")

    # the die is its own, and the same line rolls the same
    streams.begin(4, 99, "the same line")
    before = streams.get("scene").getstate()
    a, b = ws.hire_move(m, "the same line"), ws.hire_move(m, "the same line")
    check("the move is rolled on a die of its own: the scene's dice do not move, and the same reply rolls the same",
          streams.get("scene").getstate() == before and a == b and a in K, (a, b))

    # told of a loss: the reply answers it first, so the move is the forced one
    feeling = ws.hire_feeling
    ws.hire_feeling = lambda member, text: "painful_told"
    forced = {move_of(m, k, "My brother was killed on the north road last winter,") for k in range(30)}
    ws.hire_feeling = lambda member, text: "hurt_self"
    hurt = {move_of(dict(m, moves=[]), k) for k in range(300)}
    ws.hire_feeling = feeling
    check("told of a loss in the player's own life, a companion's move is to answer it, whatever the die", forced == {R["moves"]["forced"]}, forced)
    check("one who is hurt is not sent to their own trouble by the move (the request already says it is felt and not said)",
          len(hurt) >= 3 and not set(needy) & hurt, hurt)

    # a look alone: whole under the quiet move, though a gesture was only just made; sent back under any other
    def look_alone(move):
        rolled, ws.hire_move = ws.hire_move, lambda member, text, feeling=None: move
        was_answer, stub.companion = stub.companion, lambda u: (reqs.append(u), {"speech": "", "gesture": "looks off down the road and says nothing"})[1]
        m["since_gesture"] = 0                              # a gesture was just made: one now comes too soon
        streams.begin(4, 500 + len(move), f"And the weather, {move}?")
        reqs.clear()
        try:
            ws.hire_talk(m, f"And the weather, {move}?")
        finally:
            ws.hire_move, stub.companion = rolled, was_answer
        return len(reqs)

    quiet_asks, answer_asks = look_alone("quiet"), look_alone("answer")
    check("under the quiet move a look alone stands on the first asking though a gesture was just made; under another move it is sent back",
          quiet_asks == 1 and answer_asks > 1, (quiet_asks, answer_asks))

    # another companion's reply to the same line is their own roll
    other = copy.deepcopy(m)
    other.update(id="h_728b", name="Sella Marrow")
    same = [move_of(dict(m, moves=[]), k) == move_of(dict(other, moves=[]), k) for k in range(60)]      # alike but for who they are
    check("two companions asked the same thing each roll their own", not all(same), same[:10])

    R["decide_then_speak"] = False
    check("...and with the switch off no move is rolled at all", ws.hire_move(m, "anything") == "")
finally:
    R["decide_then_speak"] = was
    game.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
