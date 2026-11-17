"""(f725) Decide: a small call for what only reading the line can settle (docs/design/28_phase4_plan.md, A3; npc/life.py decide,
engine/reply.py take and fallback, llm/contracts.py NPCDecision, data/rules/reply.yaml). Before a townsperson speaks, a short
request asks what they do with what was said: the intent, which of the things they could tell they tell (by id, only of those
the engine offered, no more than the move lets them), the names, what is offered or handed over, what to keep. The engine checks
the answer as it checks a reply's, and when the reading fails the engine's own candidates are the whole decision. Behind the
switch: off, no such call is made; on, the words are then asked for with the decision made (f726).
Run: python tools/sim/reply_decide_725_test.py"""
import copy
import sys
import typing
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
SHOWN = simlib.quiet_console(("narrate", "say", "note", "ledger", "debug"))
from engine import budget, data_check, guard, reply
from llm import contracts
from llm.gateway import LLMError

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


if not hasattr(reply, "take"):
    check("engine/reply.py has the reading's checks (take)", False)
    sys.exit(1)

# ---- the data: what each move lets them tell, what it comes to when the reading fails, how it is said to the model
K = reply.R["moves"]["kinds"]
INTENTS = set(typing.get_args(contracts.NPCDecision.model_fields["intent"].annotation))
check("every move says how much it tells, what it comes to with no reading, and what it is in plain words; the tables pass their check",
      all(isinstance(s.get("most"), int) and s.get("intent") in INTENTS and str(s.get("says") or "").strip() for s in K.values())
      and reply.problems() == [] and not [p for p in data_check.check() if "reply.yaml" in p], reply.problems())
check("an answer tells the most, a part of one less, and turning it aside, a joke or a word or two tell nothing",
      K["answer"]["most"] > K["part"]["most"] >= 1 and all(K[m]["most"] == 0 for m in ("deflect", "joke", "quiet")), {m: s.get("most") for m, s in K.items()})
D = copy.deepcopy(reply.R)
D["moves"]["kinds"]["answer"]["most"] = -1
D["moves"]["kinds"]["part"]["intent"] = "sulk"
D["moves"]["kinds"]["quiet"].pop("says")
D["decide"]["lines"] = 0
found = reply.problems(D)
check("a move that tells less than nothing, comes to no intent a reply has, or has no words; a reading given no lines of the talk: each is refused",
      all(any(w in p for p in found) for w in ("kinds.answer", "kinds.part", "kinds.quiet", "decide.lines")), found)
check("the reading's intents are a reply's own", INTENTS == set(typing.get_args(contracts.NPCReply.model_fields["intent"].annotation)))

# ---- the task: known to the budget, asked outside an operation's transaction, explained, and (f726) read by the guard: its lines are kept
check("the task is the budget's (required, a small answer), asked outside the transaction, has its reason, and is read by the guard",
      budget.need("npc_decide") == "required" and budget.B["tasks"]["npc_decide"]["answer_tokens"] <= 120 and "npc_decide" in budget.B["asked_outside"]
      and guard.guarded("npc_decide") and not [p for p in data_check.check() if "npc_decide" in p or "budget.yaml" in p or "audit_log" in p],
      [p for p in data_check.check() if "npc_decide" in p or "budget.yaml" in p or "audit_log" in p])

# ---- the contract: the ids offered and no others, no more than the move lets them
C = contracts.decision_contract(["lore_a", "news:0"], 1)
S = C.model_json_schema()
check("the contract names the ids offered, and how many may be told; its title is the one contract's",
      S["title"] == "NPCDecision" and S["properties"]["shares"]["items"]["enum"] == ["lore_a", "news:0"] and S["properties"]["shares"]["maxItems"] == 1, S["properties"].get("shares"))
none = contracts.decision_contract([], 4).model_json_schema()
shut = contracts.decision_contract(["lore_a"], 0).model_json_schema()
check("with nothing offered, or a move that tells nothing, the answer has no place for an id at all", "shares" not in none["properties"] and "shares" not in shut["properties"])
check("what was promised is asked for only when the line may promise something, as a reply's is",
      "they_promised" not in S["properties"] and "they_promised" in contracts.decision_contract(["lore_a"], 1, promised=True).model_json_schema()["properties"]
      and contracts.decision_contract(["lore_a"], 1, promised=True).model_json_schema()["title"] == "NPCDecision")
check("the answer carries no words of theirs", not {"speech", "gesture"} & set(S["properties"]), sorted(S["properties"]))

# ---- the engine's checks on the reading
Cand = reply.Candidate


def decision(move="answer", cands=None, **k):
    d = reply.Decision("npc1", "player", move=move, **k)
    d.candidates = cands if cands is not None else [Cand("lore_a", "lore", "The mill grinds on rest days.", True), Cand("lore_b", "lore", "The ford floods in spring.", True),
                                                    Cand("news:0", "news", "Wolves took three sheep.", False, "trust 10, under 30"),
                                                    Cand("clue:t1:0", "clue", "Lantern light in the barn.", True)]
    return d


def story(name):
    return "sword" not in name.lower()


got = contracts.NPCDecision(intent="share", shares=["lore_b", "news:0", "made_up", "lore_b", "lore_a"], told_own_name=True, learned_name="Aldis", remember="The stranger asked after the ford.")
d = reply.take(decision(), got, "player", story)
check("an id that was not offered is dropped, as is one they would not share; one named twice is told once; the order is the reading's",
      d.shares == ("lore_b", "lore_a") and d.intent == "share" and d.read == "model" and d.told_own_name is True
      and any("made_up" in x for x in d.dropped) and any("news:0" in x for x in d.dropped), (d.shares, d.dropped))
check("...and what it means for the one spoken to is kept as a reply's block is: the name they gave, what to keep",
      d.answer.to == "player" and d.answer.learned_name == "Aldis" and "ford" in d.answer.remember, d.answer)
d = reply.take(decision("part"), contracts.NPCDecision(intent="share", shares=["lore_a", "lore_b", "clue:t1:0"]), "player", story)
check("no more is told than the move lets them: answering in part, one thing", d.shares == ("lore_a",) and len([x for x in d.dropped if "more than" in x]) == 2, (d.shares, d.dropped))
d = reply.take(decision("deflect"), contracts.NPCDecision(intent="share", shares=["lore_a"]), "player", story)
check("turning it aside, nothing is told whatever the reading says, and a sharing with nothing left to tell is ordinary talk",
      d.shares == () and d.dropped and d.intent == "small_talk", (d.shares, d.dropped, d.intent))
d = reply.take(decision("deflect"), contracts.NPCDecision(intent="refuse", shares=["lore_a"]), "player", story)
check("...any other intent is theirs as read", d.intent == "refuse" and d.shares == ())
secret = [Cand("lore_a", "lore", "The mill grinds on rest days.", True), Cand("secret:arc", "secret", "The seal was cut at the mill.", True)]
d = reply.take(decision("answer", secret, forced=True), contracts.NPCDecision(intent="small_talk", shares=[]), "player", story)
check("a secret whose gate the game has opened is told, whatever the reading says (the game decided it)", d.shares == ("secret:arc",), d.shares)
d = reply.take(decision("quiet", secret, forced=True), contracts.NPCDecision(intent="share", shares=["lore_a"]), "player", story)
check("...and it is told over and above what the move lets them", d.shares == ("secret:arc",), d.shares)
gift = contracts.GiftProposal(name="an old sword", description="A notched blade.")
d = reply.take(decision(), contracts.NPCDecision(intent="help", gives=gift), "player", story)
check("a gift that is no story object is not given", d.answer.gives is None and any("sword" in x for x in d.dropped), (d.answer.gives, d.dropped))
seal = contracts.GiftProposal(name="a wax seal", description="The reeve's seal.")
d1 = reply.take(decision(), contracts.NPCDecision(intent="help", gives=seal), "player", story)
d2 = reply.take(decision(), contracts.NPCDecision(intent="bargain", gives=seal), "player", story)
d3 = reply.take(decision(), contracts.NPCDecision(intent="help", gives=seal), "player", None)
check("a story object is given; not while they bargain over it; and not where nothing can say what a story object is",
      d1.answer.gives is not None and d2.answer.gives is None and d3.answer.gives is None, (d1.answer.gives, d2.answer.gives, d3.answer.gives))
both = contracts.NPCDecision(intent="help", offers_work=contracts.WorkOffer(task="stack the cordwood", pay=20), offers_quest=contracts.QuestOffer(kind="hunt", what="wolves", count=3))
d = reply.take(decision(), both, "player", story)
blank = reply.take(decision(), contracts.NPCDecision(intent="help", offers_work=contracts.WorkOffer(task="  "), offers_quest=contracts.QuestOffer(kind="hunt", what=" ")), "player", story)
check("paid work and a request are never offered in one breath (the work stands); an offer of nothing is no offer",
      d.answer.offers_work is not None and d.answer.offers_quest is None and blank.answer.offers_work is None and blank.answer.offers_quest is None,
      (d.answer, blank.answer))
check("the one rule for a gift is the scene's too (one place says what may be given)", reply.gift(seal, "help", story) is seal and reply.gift(gift, "help", story) is None
      and reply.gift(seal, "bargain", story) is None and reply.gift(None, "help", story) is None)

# ---- the reading failed: the engine's candidates are the whole decision
empty = contracts.NPCAnswer(to="player")
f = reply.fallback(decision("answer"), empty)
check("with no reading, one who answers tells what was picked for the line, in its order, as many as the move lets them, and nothing they would not share",
      f.shares == ("lore_a", "lore_b", "clue:t1:0")[: K["answer"]["most"]] and f.intent == K["answer"]["intent"] and f.read == "engine" and f.answer is empty, (f.shares, f.intent))
f = reply.fallback(decision("deflect"), empty)
g = reply.fallback(decision("answer", []), empty)
h = reply.fallback(decision("quiet", secret, forced=True), empty)
check("...one who turns it aside tells nothing; one with nothing to tell only talks; an opened secret is told all the same",
      f.shares == () and f.intent == K["deflect"]["intent"] and g.shares == () and g.intent == "small_talk" and h.shares == ("secret:arc",), (f.intent, g.intent, h.shares))
check("the decision says what was read and by whom, where the debug console shows it", "read by the model: intent help" in d1.line() and "read by the engine" in f.line(), d1.line())

# ---- in play
game = simlib.campaign("reply_decide_725", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter(ws.player.location)
REQ, ASKED = [], []
real = simlib.below()


def chat(**k):
    t = k["format"].get("title")
    if t in ("NPCReply", "NPCDecision", "NPCSpeech"):
        ASKED.append(t)
        REQ.append((t, k["messages"][0]["content"], k["messages"][1]["content"], k["format"]))
    if t == "NPCDecision" and FAIL[0]:
        raise LLMError("the model failed")
    return real.chat(**k)


FAIL = [False]
spy = simlib.stand_in(chat=chat)
npc = sorted((n for n in ws.present if n.role not in ("guild_clerk", "guild_master")), key=lambda n: n.id)[0]


def say(words, **more):
    stub.plan = [{"kind": "talk", "target": npc.id, "speech": words, **more}]
    ws.turn(f'I say, "{words}"')
    stub.plan = None


say("Fine weather today.")
say("A quiet morning for it.")
check("with the switch off no reading is asked for", "NPCDecision" not in ASKED and not stub.calls.get("NPCDecision"), ASKED)
off = [r for r in REQ if r[0] == "NPCReply"][-1]


def ids_of(k):
    return (((k["format"].get("properties") or {}).get("shares") or {}).get("items") or {}).get("enum") or []


reply.R["decide_then_speak"] = True
try:
    del ASKED[:], REQ[:]
    PICK = []

    def planted(u, k):
        PICK[:] = ids_of(k)
        return {"intent": "share", "shares": PICK[:1] + ["never_offered"], "told_own_name": True, "remember": "The stranger asked how trade was."}

    stub.decide_extra = planted
    ws.moves = []
    now = next(n for n in ws.present if n.id == npc.id)                      # the scene's own record of them, as it stands
    now.motive = "to find a buyer for the old boat"
    store.save_npc(now)
    forced_move = reply.roll_move
    reply.roll_move = lambda w, last, rng, forced=False: "answer"            # this reply answers, so the reading has ids to choose from
    try:
        say("What do you know of this place, and the roads about it?")
    finally:
        reply.roll_move = forced_move
    d = ws.decision
    asked = [t for t in ASKED]
    check("with it on, the reading is asked for once, before the words (f726: the words alone, no whole reply)",
          asked[:1] == ["NPCDecision"] and asked.count("NPCDecision") == 1 and "NPCSpeech" in asked[1:] and "NPCReply" not in asked
          and stub.calls.get("NPCDecision") == 1, asked)
    check("...and the decision holds what was read, after the engine's checks: the id offered is told, the one never offered is not",
          d is not None and d.read == "model" and d.intent == "share" and (not PICK or d.shares == tuple(PICK[:1])) and "never_offered" not in d.shares
          and d.told_own_name is True and d.answer is not None and "trade" in d.answer.remember, (PICK, d and d.line()))
    check("...there was something to choose from (the lore picked for the line), each id one of the decision's candidates they would share",
          PICK and set(PICK) <= {c.id for c in reply.offered(d)}, (PICK, [c.id for c in d.candidates]))
    check("...the engine says so on the debug console", any(k == "debug" and "decided: move answer" in str(t) and "share" in str(t) for k, t in SHOWN), [t for k, t in SHOWN if k == "debug"][-2:])
    dec = [r for r in REQ if r[0] == "NPCDecision"][-1]
    on = [r for r in REQ if r[0] == "NPCSpeech"][-1]
    size = len(dec[1]) + len(dec[2])
    check("the reading's request is small: under 6,000 characters, system and all", size < 6000, size)
    check("...it has who they are, what was said, what they do with it in plain words, and what they could tell, one line an id",
          npc.name in dec[2] and "What do you know of this place" in dec[2] and K["answer"]["says"] in dec[2] and all(f"[{i}]" in dec[2] for i in PICK), dec[2][:400])
    check("...and not the places around, the index of what else they know, the town's list or how they talk (those are for the speech)",
          not any(w in dec[2] for w in ("PLACES AROUND HERE", "YOU ALSO KNOW OF", "WHAT THIS TOWN HAS", "HOW YOU TALK", "JOURNAL NOTE DUE",
                                        "THE GUILD'S RULES", "The season is", "Your people follow")), dec[2][:300])
    check("...but how they stand with this character and what they are after are in it, as the request for the words has them",
          all(w in dec[2] and w in on[2] for w in ("How people around here regard the stranger", "What you're working toward", "the old boat"))
          and "The season is" in on[2], dec[2][:900])
    check("the words are then asked for on their own (f726): no intent in that answer, and what they know besides is still theirs",
          on[1] != off[1] and "RIGHT NOW YOU ALSO KNOW" in on[2] and "intent" not in on[3]["properties"], sorted(on[3]["properties"]))
    check("the talk goes on as it did: they answered, the line stood", ws.stood is True and ws.convo and ws.convo[-1][0] == npc.name, (ws.stood, ws.convo[-1:]))

    # a move that tells nothing: no id is offered to the reading at all, and none is told
    del REQ[:]
    stub.decide_extra = {"intent": "withhold", "shares": ["lore_a"]}
    reply.roll_move = lambda w, last, rng, forced=False: "deflect"
    try:
        say("And who keeps the hall?")
    finally:
        reply.roll_move = forced_move
    dec = [r for r in REQ if r[0] == "NPCDecision"][-1]
    check("one who turns it aside is offered no id to tell, sees none of what they know in the request, and tells none",
          not ids_of({"format": dec[3]}) and ws.decision.shares == () and ws.decision.intent == "withhold" and "[" not in dec[2].split("THIS CONVERSATION SO FAR")[0].split("WHAT YOU")[-1],
          (ws.decision.line(), dec[2][-600:]))

    # the game has decided something in this turn: the reading is given the game's line
    del REQ[:]
    stub.decide_extra = None
    say("Come now, you can tell me.", checks=["persuasion"])
    dec = [r for r in REQ if r[0] == "NPCDecision"][-1]
    so_far = dec[2].split("THIS CONVERSATION SO FAR:")[1].split("THEY SAY:")[0].strip().splitlines()
    check("the reading is given the talk's last lines, not the whole talk", len(ws.convo) > len(so_far) == reply.R["decide"]["lines"], (len(ws.convo), so_far))
    check("what the game has decided in the turn is in the reading's request, and the move is the forced one", "THE GAME HAS DECIDED" in dec[2] and ws.decision.forced
          and ws.decision.move == reply.R["moves"]["forced"], (ws.decision.line(), dec[2][-300:]))

    # a secret whose gate the game has opened: the reading is told it is decided, by the game's own line, and it is told
    del REQ[:]
    stub.decide_extra = {"intent": "small_talk"}
    ws.secret_lines = lambda who, speech: (["[THE GAME HAS DECIDED: they have won you over. You tell them what you know now, in your own manner.]"],
                                           {"open": True, "pressed": True, "secret": {"kind": "arc", "node": "n1"}})
    ws.secret_text = lambda secret: "The seal was cut at the mill."
    ws.secret_after = lambda who, pending: None
    reply.roll_move = lambda w, last, rng, forced=False: "quiet"            # even with a move that tells nothing
    try:
        say("So what was it you saw?")
    finally:
        del ws.secret_lines, ws.secret_text, ws.secret_after
        reply.roll_move = forced_move
    dec = [r for r in REQ if r[0] == "NPCDecision"][-1]
    check("a secret the game has opened is in the reading's request as decided, with the game's own line, and is told whatever was read",
          "[secret:arc] The seal was cut at the mill. (the game has decided: you tell this)" in dec[2] and "they have won you over" in dec[2]
          and "WHAT YOU TELL THEM:" in dec[2] and not ids_of({"format": dec[3]}) and ws.decision.shares == ("secret:arc",) and ws.decision.forced,
          (ws.decision.line(), dec[2][-700:]))

    # the reading fails: the engine's candidates stand, and the talk goes on
    del ASKED[:]
    FAIL[0] = True
    reply.roll_move = lambda w, last, rng, forced=False: "answer"
    try:
        say("What do you know of the roads about here?")
    finally:
        reply.roll_move = forced_move
        FAIL[0] = False
    d = ws.decision
    check("when the reading fails the engine's own candidates are the decision, and they still speak",
          d is not None and d.read == "engine" and d.shares == tuple(c.id for c in reply.offered(d))[: K["answer"]["most"]] and "NPCSpeech" in ASKED and ws.stood is True,
          (d and d.line(), ASKED))
    check("...and the line is not counted as broken", not ws.last_crash, ws.last_crash)
finally:
    reply.R["decide_then_speak"] = False
    stub.decide_extra = None
spy()
game.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
