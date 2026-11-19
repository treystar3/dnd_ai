"""(f726) Speak: the smaller prompt, given only the decision (docs/design/28_phase4_plan.md, A4; npc/life.py converse and speak,
npc/prompts.py SPEAK_SYSTEM and speak_prompt, llm/contracts.py NPCSpeech, engine/reply.py words and told). With the switch on, a
townsperson is asked only to say what was decided: who they are first, what is plainly around them, what was said, and last what
they do with it and what they tell. Its answer is speech and a gesture. What they could have told and did not is not in the
request, so it cannot leak. Everything the engine does with a reply is done from the decision: what the player learned is what
was decided and the speech carries, a name is known when the speech gives it, an offer is the engine's figures. With the switch
off, the reply is asked for as it was.
Run: python tools/sim/reply_speak_726_test.py"""
import copy
import sys
import typing
sys.path.insert(0, ".")
sys.path.insert(0, "tools")
import simlib
stub = simlib.Stub("warrior", 4)
simlib.install(stub)
SHOWN = simlib.quiet_console(("narrate", "say", "note", "ledger", "debug"))
from engine import brief, data_check, guard, regard, reply, truth
from llm import contracts
from llm.gateway import LLMError
from npc import prompts
from pydantic import ValidationError

bad = []


def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x, file=sys.__stdout__)
    if not ok:
        bad.append(n)


if not hasattr(reply, "words") or not hasattr(contracts, "NPCSpeech") or not hasattr(prompts, "SPEAK_SYSTEM"):
    check("the speaking is built (engine/reply.py words, llm/contracts.py NPCSpeech, npc/prompts.py SPEAK_SYSTEM)", False)
    sys.exit(1)

# ---- the data: each intent in plain words, how a name, a gift, work and a request are told
INTENTS = set(typing.get_args(contracts.NPCDecision.model_fields["intent"].annotation))
K = reply.R["moves"]["kinds"]
check("every intent a reply has is in the table with its words (ordinary talk and sharing need none: the move says them); the tables pass their check",
      set(reply.R["intents"]) == INTENTS and all(isinstance(v, str) for v in reply.R["intents"].values()) and not reply.R["intents"]["small_talk"]
      and all(reply.R["intents"][i].strip() for i in ("leave", "refuse", "bargain", "lie", "withhold", "help", "threaten"))
      and reply.problems() == [] and not [p for p in data_check.check() if "reply.yaml" in p], reply.problems())
D = copy.deepcopy(reply.R)
D["intents"].pop("leave")
D["speak"]["lived"] = -1
D["tells"].pop("yours")
D["tells"]["work"] = "You offer them work."
D["decide"]["memories"] = -1
found = reply.problems(D)
check("an intent with no words, a telling that leaves out its figures or is not there, a reading given less than no memories, a speaker less than none of "
      "their own days: each is refused",
      all(any(w in p for p in found) for w in ("intents", "tells.work", "tells.yours", "decide.memories", "speak.lived")), found)

# ---- the contract: speech and a gesture, nothing else, held to the checks a reply's speech is
S = contracts.NPCSpeech.model_json_schema()
check("the answer is speech and a gesture and nothing else; it is someone's reply to the player", set(S["properties"]) == {"speech", "gesture"}
      and S["title"] == "NPCSpeech" and getattr(contracts.NPCSpeech, "REPLY", False) is True and contracts.NPCSpeech(speech="Aye.").spoken() == [("", "Aye.")], S["properties"])


def refused(ctx=None, **fields):
    try:
        contracts.NPCSpeech.model_validate(fields, context=ctx)
    except ValidationError as e:
        return str(e)
    return ""


check("its speech is checked as a reply's is: no markdown, never nothing at all, at most one trailing off, no stock opener twice running",
      "plain speech" in refused(speech="It is *fine*.") and "say something" in refused(speech="...") and "trailing" in refused(speech="Well... I... no.")
      and "opened your last line" in refused({"last": "Well, there it is."}, speech="Well, the mill is shut.") and not refused(speech="The mill is shut."),
      (refused(speech="It is *fine*."), refused(speech="..."), refused({"last": "Well, there it is."}, speech="Well, the mill is shut.")))
noted = contracts.decision_contract(["lore_a"], 1, noted=True)
check("the journal note is the reading's to write, asked for only when one is due; one in their own voice is dropped as a reply's was",
      "journal_note" in noted.model_json_schema()["properties"] and "journal_note" not in contracts.decision_contract(["lore_a"], 1).model_json_schema()["properties"]
      and noted(intent="small_talk", journal_note="Edda Reeve, the clerk at Parth; careful with her ledgers.").answers("player")[0].journal_note.startswith("Edda Reeve")
      and noted(intent="small_talk", journal_note="I must watch this one.").answers("player")[0].journal_note == "")

# ---- the engine's checks on the reading that the speaking needs
Cand = reply.Candidate


def decision(move="answer", cands=None, **k):
    d = reply.Decision("npc1", "player", move=move, **k)
    d.candidates = cands if cands is not None else [Cand("lore_a", "lore", "The mill grinds on rest days.", True), Cand("lore_b", "lore", "The ford floods in spring.", True),
                                                    Cand("news:0", "news", "Wolves took three sheep.", True)]
    return d


def story(name):
    return "sword" not in name.lower()


def fair(offer):
    if offer.task.strip().lower() in ("a job", "work"):
        return None
    return contracts.WorkOffer(task=offer.task.strip(), pay=min(offer.pay, 30), minutes=min(offer.minutes, 120))


d = reply.take(decision(), contracts.NPCDecision(intent="lie", shares=["lore_a"]), "player", story)
check("one who lies tells none of what is so", d.shares == () and d.intent == "lie" and any("lie" in x for x in d.dropped), (d.shares, d.dropped))
secret = [Cand("lore_a", "lore", "The mill grinds on rest days.", True), Cand("secret:arc", "secret", "The seal was cut at the mill.", True)]
got = [reply.take(decision("answer", list(secret), forced=True), contracts.NPCDecision(intent=i), "player", story) for i in ("lie", "withhold", "refuse")]
check("what the game has decided they tell is told truly: a reading that would lie, keep it back or refuse comes to a sharing",
      all(g.shares == ("secret:arc",) and g.intent == "share" for g in got), [(g.intent, g.shares) for g in got])
d = reply.take(decision(), contracts.NPCDecision(intent="help", offers_work=contracts.WorkOffer(task="stack the cordwood", pay=5000, minutes=900)), "player", story, fair)
e = reply.take(decision(), contracts.NPCDecision(intent="help", offers_work=contracts.WorkOffer(task="a job", pay=20)), "player", story, fair)
check("paid work is offered at the engine's figures, settled before they speak of it; work that is no real task is no offer",
      d.answer.offers_work.pay == 30 and d.answer.offers_work.minutes == 120 and e.answer.offers_work is None and any("work" in x for x in e.dropped), (d.answer.offers_work, e.dropped))
d = reply.take(decision(), contracts.NPCDecision(intent="small_talk", offers_quest=contracts.QuestOffer(kind="deliver", what="a letter", item="a letter")), "player", story)
e = reply.take(decision(), contracts.NPCDecision(intent="small_talk", offers_quest=contracts.QuestOffer(kind="deliver", what="it", to="the miller")), "player", story)
check("a delivery to no one is no request, and the decision's line says why; one to someone stands, and a thing not named is told in the table's words",
      d.answer.offers_quest is None and any("delivery to no one" in x for x in d.dropped) and "delivery to no one" in d.line() and e.answer.offers_quest is not None
      and any("the miller" in w and reply.R["tells"]["yours"] in w for w in reply.words(e)), (d.dropped, reply.words(e)))

# ---- the decision in plain words, and what they tell
full = reply.take(decision(), contracts.NPCDecision(intent="help", shares=["lore_b", "news:0"], told_own_name=True,
                                                     gives=contracts.GiftProposal(name="a wax seal", description="The reeve's seal."),
                                                     offers_work=contracts.WorkOffer(task="stack the cordwood", pay=5000, minutes=60)), "player", story, fair)
W = reply.words(full)
check("the decision is told in plain words: the move, what the reading settled, the name given, the thing handed over, the work at the engine's figures",
      W[0] == K["answer"]["says"] and reply.R["intents"]["help"] in W and any("your name" in w for w in W) and any("a wax seal" in w for w in W)
      and any("stack the cordwood" in w and "30 copper" in w and "60 minutes" in w for w in W) and not any("5000" in w for w in W), W)
check("...and what they tell is the decided things in full, in the order decided, and no id", reply.told(full) == ["The ford floods in spring.", "Wolves took three sheep."], reply.told(full))
quest = reply.take(decision("part"), contracts.NPCDecision(intent="small_talk", offers_quest=contracts.QuestOffer(kind="hunt", what="wolves", count=3)), "player", story)
plain = reply.words(reply.take(decision("quiet"), contracts.NPCDecision(intent="small_talk"), "player", story))
check("a request is told as what they ask; ordinary talk is the move's words alone", any("wolves" in w and "3" in w for w in reply.words(quest)) and plain == [K["quiet"]["says"]],
      (reply.words(quest), plain))
leaving = reply.words(reply.take(decision("quiet"), contracts.NPCDecision(intent="leave"), "player", story))
check("one who leaves is told to say so aloud", any("aloud" in w for w in leaving), leaving)

# ---- the truth view: a piece of the town's left out of one reply
check("the guard reads the reading now that its lines are kept (what to remember, a gift's name, the work)", guard.guarded("npc_decide") and "npc_decide" not in guard.SKIP)
check("the rules for speaking are far shorter than the reply's were, and ask for no field but the words",
      len(prompts.SPEAK_SYSTEM) <= len(prompts.CONVERSATION_SYSTEM) - 2000
      and not any(w in prompts.SPEAK_SYSTEM for w in ("reveals", "trust_change", "offers_work", "offers_quest", "journal_note", "told_own_name", "remember:")),
      (len(prompts.SPEAK_SYSTEM), len(prompts.CONVERSATION_SYSTEM)))

check("the rules let them say the one false thing the game decides: one told that what they say is not so says it as if it were true",
      "is not so" in reply.R["intents"]["lie"] and "The one exception" in prompts.SPEAK_SYSTEM and "is not so, you answer what was asked with something false" in " ".join(prompts.SPEAK_SYSTEM.split()))
from engine import memory
M = type("M", (), {})


def row(**k):
    m = M()
    m.subject, m.kind, m.about = k.get("subject", ""), k.get("kind", "experienced"), k.get("about", "")
    return m


check("a memory is of a character by their id; one of their own days is about no one, and is no life's story, no clue held and no fact overheard",
      memory.of(row(subject="player"), "player") and not memory.of(row(subject="other"), "player") and not memory.of(row(), "player") and not memory.of(row(), "")
      and memory.lived(row()) and memory.lived(row(kind="heard")) and not memory.lived(row(subject="player")) and not memory.lived(row(kind="own_life"))
      and not memory.lived(row(kind="knows")) and not memory.lived(row(kind="heard", about="fact:well")) and not memory.lived(row(kind="knows", about="thread:t:0")))

# ---- in play
game = simlib.campaign("reply_speak_726", minutes=600, location="guild_house")
ws, store = game.scene, game.store
ws.enter(ws.player.location)
REQ, ASKED = [], []
real = simlib.below()
FAIL = [False]


def chat(**k):
    t = k["format"].get("title")
    if t in ("NPCReply", "NPCDecision", "NPCSpeech"):
        ASKED.append(t)
        REQ.append((t, k["messages"][0]["content"], k["messages"][1]["content"], k["format"]))
    if t == "NPCDecision" and FAIL[0]:
        raise LLMError("the model failed")
    return real.chat(**k)


spy = simlib.stand_in(chat=chat)
npc = sorted((n for n in ws.present if n.role not in ("guild_clerk", "guild_master")), key=lambda n: n.id)[0]
master = next(n for n in ws.present if n.role == "guild_master")     # the board is theirs whatever the line (brief.yaml always)
FIRST = npc.name.split()[0]


def cur(who=None):
    return next(n for n in ws.present if n.id == (who or npc).id)


def say(words, to=None, **more):
    stub.plan = [{"kind": "talk", "target": (to or npc).id, "speech": words, **more}]
    ws.turn(f'I say, "{words}"')
    stub.plan = None


def last(title):
    return [r for r in REQ if r[0] == title][-1]


def ids_of(fmt):
    return (((fmt.get("properties") or {}).get("shares") or {}).get("items") or {}).get("enum") or []


def told_in(u):
    """The lines under WHAT YOU TELL THEM in a speaking request."""
    if "WHAT YOU TELL THEM (" not in u:
        return []
    lines = [l.strip() for l in u.split("WHAT YOU TELL THEM (")[-1].split("):", 1)[1].splitlines() if l.strip()]
    return [l[2:] if l.startswith("- ") else l for l in lines]


from engine import pulse
real_window, real_happen = pulse.news_window, pulse.happenings_at
row = {"minute": ws.minutes, "origin": ws.player.location, "groups": ["everyone"], "times": 1}
pulse.news_window = lambda *a, **k: [{**row, "text": "Wolves were seen on the north road by the gate."}, {**row, "text": "The chandler's cat had kittens in the loft."}]
pulse.happenings_at = lambda *a, **k: ["A funeral crosses the square for the old ferryman."]
ASK = "Is the north road safe from wolves these days?"
real_roll = reply.roll_move
ROLLS = []


def answer(w, last, rng, forced=False):
    ROLLS.append(forced)
    return "answer"


from engine import clock
day = clock.day(ws.minutes)
memory.keep(npc, "The seal on the grain store was cut from inside.", day=day, turn=-1, kind="knows", subject="", about="thread:none_726:0", state="held", importance=2)
memory.keep(npc, "I heard it said: The old well runs dry by midsummer.", day=day, turn=-1, kind="heard", subject="", source="someone", about="fact:well_726")
memory.keep(npc, "Somebody broke the miller's window.", day=day, turn=-1, kind="witnessed", subject="another_726")
memory.keep(npc, "The flood took the lower street.", day=day, turn=-1, kind="experienced", subject="")
memory.keep(npc, "{them} asked after the ferry.", day=day, turn=-1, kind="told", subject=ws.acting, source=ws.acting)
store.save_npc(npc)
HELD = ("seal on the grain store", "old well runs dry", "miller's window")
try:
    say("Fine weather today.")
    regard.own(cur(), ws.acting).trust = 50                                 # no stranger to them: the news is theirs to tell this character
    say(ASK)
    off = last("NPCReply")
    check("with the switch off the reply is asked for as it was: one call, the reply's whole contract and rules, and the town's news all in front of them",
          "NPCSpeech" not in ASKED and "NPCDecision" not in ASKED and off[1] == prompts.CONVERSATION_SYSTEM and "intent" in off[3]["properties"]
          and "chandler's cat" in off[2] and "Wolves were seen" in off[2], ASKED)
    check("...and every row of their memory but their life's story, whoever and whatever it is about (as it was)",
          all(w in off[2] for w in HELD + ("flood took the lower street", "asked after the ferry")), off[2][-1500:])

    reply.R["decide_then_speak"] = True
    reply.roll_move = answer
    ws.moves = []
    PICK = []

    def none_of_the_news(u, k):
        PICK[:] = ids_of(k["format"])
        return {"intent": "share", "shares": [i for i in PICK if not i.startswith(("news:", "happening:"))][:1]}

    def speak_it(u, k):
        return {"speech": " ".join(told_in(u)) or "Quiet enough, most days."}

    stub.decide_extra, stub.speech_extra = none_of_the_news, speak_it
    del ASKED[:], REQ[:]
    known_before = list(ws.player.character.knowledge)
    say(ASK)
    dec, on = last("NPCDecision"), last("NPCSpeech")
    d = ws.decision
    check("with it on they are asked for the reading, then the words; the old reply is not asked for",
          ASKED[:1] == ["NPCDecision"] and set(ASKED[1:]) == {"NPCSpeech"} and ASKED.count("NPCDecision") == 1, ASKED)
    check("the turn stood: asked twice outside the operation, played once", ws.stood is True and not ws.last_crash, (ws.stood, ws.last_crash))
    mine = on[2].split("YOUR MEMORIES OF THEM:")[1].split("YOUR OWN DAYS LATELY:")[0]
    check("what they remember of this character is theirs for the words, and their own days beside it; a clue they hold, a fact they overheard and "
          "what another character did are not in the request",
          "asked after the ferry" in mine and "flood took the lower street" in on[2].split("YOUR OWN DAYS LATELY:")[1][:200] and not any(w in on[2] for w in HELD), on[2][:1500])
    check("...and the reading has only what they remember of this character", "asked after the ferry" in dec[2] and "flood took" not in dec[2]
          and not any(w in dec[2] for w in HELD), dec[2][:900])
    check("the words are asked for under the short rules, and the answer has a place for speech and a gesture only",
          on[1] == prompts.SPEAK_SYSTEM and set(on[3]["properties"]) == {"speech", "gesture"}, sorted(on[3]["properties"]))
    check("the news was theirs to tell (offered to the reading)", "news:0" in PICK and "news:0" in [c.id for c in reply.offered(d)], PICK)
    check("...and not chosen, it is not in the speaking request at all; nor is the news that never bore on the line, nor the street's happening",
          "Wolves were seen" not in on[2] and "chandler's cat" not in on[2] and "funeral" not in on[2], on[2][-900:])
    lore_told = [c for c in d.candidates if c.id in d.shares]
    others = [c for c in d.candidates if c.id not in d.shares and c.text]
    check("what was decided is there in full, as what they tell; what they could have told and did not is not there",
          lore_told and all(" ".join(c.text.split()) in told_in(on[2]) for c in lore_told) and not any(" ".join(c.text.split()) in on[2] for c in others),
          ([c.id for c in lore_told], told_in(on[2])))
    check("...with no id, no index of what else they know, and no line for the journal", not any(f"[{c.id}]" in on[2] for c in d.candidates)
          and "YOU ALSO KNOW OF" not in on[2] and "JOURNAL NOTE DUE" not in on[2] and "YOU ALSO KNOW OF" in off[2])
    check("the person comes first and what they do with the line last: who they are, what was said, the move in plain words, what they tell",
          on[2].startswith("YOU ARE: " + npc.name) and 0 < on[2].index("THEY SAY:") < on[2].index("WHAT YOU DO IN THIS REPLY") < on[2].index("WHAT YOU TELL THEM")
          and K["answer"]["says"] in on[2].split("WHAT YOU DO IN THIS REPLY")[1], on[2][-700:])
    place = ws.world.places[npc.location]
    check("what is plainly around them is said once (the place's own lines are not given twice)", all(on[2].count(v) == 1 for v in place.visible) and
          any(off[2].count(v) == 2 for v in place.visible), [on[2].count(v) for v in place.visible])
    check("...and they still have who is here, the people they know, how they talk and the last of the talk",
          all(w in on[2] for w in ("WHO IS HERE", "PEOPLE YOU KNOW", "THIS CONVERSATION SO FAR", "THE PERSON IN FRONT OF YOU", "YOUR MEMORIES OF THEM")), on[2][:600])
    small, big = len(on[1]) + len(on[2]), len(off[1]) + len(off[2])
    check("the speaking request is smaller than the old reply's for the same line by 2,500 characters or more", small <= big - 2500, (small, big))
    learned = [i for i in ws.player.character.knowledge if i not in known_before]
    check("the engine acts from the decision: what the player learned is what was decided and the speech carried",
          set(learned) <= {c.id for c in lore_told} and all(c.id in ws.player.character.knowledge for c in lore_told if c.kind == "lore") and ws.convo[-1][0] == npc.name and all(c.text.split()[0] in ws.convo[-1][1] for c in lore_told),
          (learned, ws.convo[-1]))

    # the news chosen: it is told, in full; the other news is still not there; a piece's id is never kept
    def the_news(u, k):
        return {"intent": "share", "shares": [i for i in ids_of(k["format"]) if i.startswith("news:")][:1]}

    stub.decide_extra = the_news
    del REQ[:]
    known_before = list(ws.player.character.knowledge)
    say("And the wolves on the north road, have they been seen?")
    on = last("NPCSpeech")
    check("news that was chosen is told in full, and is in what they say; the other news is still not in the request",
          told_in(on[2]) == ["Wolves were seen on the north road by the gate."] and "chandler's cat" not in on[2] and "Wolves were seen" in ws.convo[-1][1],
          (told_in(on[2]), ws.convo[-1]))
    check("...and a piece of the town's is never kept by its id (it is its place in today's news, not the piece)",
          list(ws.player.character.knowledge) == known_before, [i for i in ws.player.character.knowledge if i not in known_before])

    # decided and not said: nothing is learned; a name is known only when the speech gives it
    stub.decide_extra = lambda u, k: {"intent": "share", "told_own_name": True,                 # something not yet learned, so that learning it would show
                                      "shares": [i for i in ids_of(k["format"]) if not i.startswith(("news:", "happening:")) and i not in ws.player.character.knowledge][:1]}
    stub.speech_extra = {"speech": "Ask me another day."}
    known_before = list(ws.player.character.knowledge)
    regard.own(cur(), ws.acting).name_known = False
    say("What do you know of the roads about this place?")
    check("what was decided and never said is not learned, and a name decided and never said is not known",
          ws.decision.shares and not set(ws.decision.shares) & set(known_before) and list(ws.player.character.knowledge) == known_before
          and regard.of(cur(), ws.acting).name_known is False,
          (ws.decision.line(), regard.of(cur(), ws.acting).name_known))
    stub.speech_extra = {"speech": f"{FIRST} is the name. Most here just shout it across the yard."}
    say("And what should I call you?")
    check("...said, it is known", regard.of(cur(), ws.acting).name_known is True and ws.decision.told_own_name is True)
    regard.own(cur(), ws.acting).name_known = False
    stub.decide_extra = {"intent": "small_talk", "told_own_name": False}
    stub.speech_extra = {"speech": f"I am {FIRST}, as I told you a moment since."}
    say("Who did you say you were?")
    check("...and said though the reading did not say so, it is known all the same: the words are what was heard",
          regard.of(cur(), ws.acting).name_known is True and ws.decision.told_own_name is False, ws.decision.line())

    # what the reading settled is what the engine keeps: the line to remember, the work at the engine's figures, the journal note
    from scenes.work_actions import offer_open
    ws.note_due = lambda who: who.id == npc.id
    stub.decide_extra = {"intent": "help", "remember": "The stranger asked after paid work.", "journal_note": f"{npc.name}, found at the guild house; has work for willing hands.",
                         "offers_work": {"task": "stack the cordwood", "pay": 5000, "minutes": 60}}
    stub.speech_extra = {"speech": "There's cordwood wants stacking, if you've the back for it."}
    del REQ[:]
    say("Have you any work for me?")
    dec, on = last("NPCDecision"), last("NPCSpeech")
    job = offer_open(store, cur(), ws.acting)
    check("work offered is recorded at the engine's figures, and they were told the same figures before they spoke",
          job and job["task"] == "stack the cordwood" and 0 < job["pay"] < 5000 and f"{job['pay']} copper" in on[2].split("WHAT YOU DO IN THIS REPLY")[1]
          and "5000" not in on[2], (job, on[2].split("WHAT YOU DO IN THIS REPLY")[1][:400]))
    check("...the line to remember is kept", any("asked after paid work" in m.text for m in cur().memories), [m.text for m in cur().memories][-3:])
    check("the journal note is asked of the reading when one is due, never of the words, and is kept",
          "JOURNAL NOTE DUE" in dec[2] and "journal_note" in dec[3]["properties"] and "JOURNAL NOTE DUE" not in on[2]
          and regard.of(cur(), ws.acting).journal_note.startswith(npc.name), (regard.of(cur(), ws.acting).journal_note, sorted(dec[3]["properties"])))
    del ws.note_due
    check("...and the reading now has what they remember of this character", "asked after paid work" not in dec[2] and "YOUR MEMORIES OF THEM" in dec[2], dec[2][:500])
    ws.wares_said = lambda who: ["a bronze bar: 40 copper", "an iron bar: 90 copper"]
    stub.decide_extra, stub.speech_extra = {"intent": "bargain"}, None
    del REQ[:]
    try:
        say("What will a bar of iron cost me?")
    finally:
        del ws.wares_said
    dec, on = last("NPCDecision"), last("NPCSpeech")
    check("...and what they sell, as the words have it with its prices", "an iron bar: 90 copper" in dec[2] and "an iron bar: 90 copper" in on[2]
          and "asked after paid work" in dec[2] and reply.R["intents"]["bargain"] in on[2], dec[2][:700])
    check("with nothing decided they are told they tell none of the town's news or others' business, and not that they know nothing: their wares are still theirs to speak of",
          "WHAT YOU TELL THEM: Nothing of the town, its news or other people's business" in on[2] and "Nothing of what you know" not in on[2], on[2][-300:])

    # a thing handed over, a request, a promise made to them: each from the decision, by the scene's own rules
    GOT, WANTS = [], []
    ws.receive_key_item = lambda gift, who: gift.name in GOT or GOT.append(gift.name)      # an operation run again from its start hands it over again, the same
    ws.record_quest_offer = lambda offer, who: (offer.kind, offer.what, offer.count) in WANTS or WANTS.append((offer.kind, offer.what, offer.count))
    try:
        stub.decide_extra = {"intent": "help", "gives": {"name": "a wax seal", "description": "The reeve's seal."}}
        stub.speech_extra = {"speech": "Take the seal, then. Mind you keep it dry."}
        del REQ[:]
        say("Might I carry your seal to the reeve?")
        does = last("NPCSpeech")[2].split("WHAT YOU DO IN THIS REPLY")[1]
        check("a thing the reading has them hand over is told to them before they speak, and is received", GOT == ["a wax seal"] and "a wax seal" in does, (GOT, does[:300]))
        stub.decide_extra = {"intent": "help", "gives": {"name": "a short sword", "description": "A plain blade."}}
        stub.speech_extra = {"speech": "No, that stays on my wall."}
        del REQ[:]
        say("Might I have the sword from your wall?")
        does = last("NPCSpeech")[2].split("WHAT YOU DO IN THIS REPLY")[1]
        check("...and what is no story object is neither told nor received", GOT == ["a wax seal"] and "sword" not in does and any("gift" in x for x in ws.decision.dropped),
              (GOT, ws.decision.dropped))
        stub.decide_extra = {"intent": "small_talk", "offers_quest": {"kind": "hunt", "what": "wolves", "count": 3}}
        stub.speech_extra = {"speech": "Three wolves, if you can manage it. They have had my hens."}
        del REQ[:]
        say("Is anything troubling you out here?")
        does = last("NPCSpeech")[2].split("WHAT YOU DO IN THIS REPLY")[1]
        check("a request the reading has them make is told to them and goes to the scene's record of requests", WANTS == [("hunt", "wolves", 3)] and "wolves" in does, (WANTS, does[:300]))
    finally:
        del ws.receive_key_item, ws.record_quest_offer
    stub.decide_extra = {"intent": "small_talk", "they_promised": "bring the hides tomorrow"}
    stub.speech_extra = {"speech": "See that you do."}
    del REQ[:]
    say("I promise I will bring the hides tomorrow.")
    check("a promise made to them is read by the reading and kept as theirs to remember", "they_promised" in last("NPCDecision")[3]["properties"]
          and any("promised me: bring the hides tomorrow" in m.text for m in cur().memories), [m.text for m in cur().memories][-3:])
    stub.speech_extra = None

    # the exemplars follow the decision: the sound of gossip only when news is told
    POOLS = []
    real_pool = ws.speech_pool
    ws.speech_pool = lambda who, stance, news: POOLS.append(list(news)) or real_pool(who, stance, news)
    try:
        stub.decide_extra = none_of_the_news
        say(ASK)
        stub.decide_extra = the_news
        say("Wolves on the north road, you say?")
    finally:
        del ws.speech_pool
    drawn = [p for i, p in enumerate(POOLS) if i == 0 or p != POOLS[i - 1]]          # an operation run again from its start draws again, the same
    check("how such talk sounds is drawn for what was decided: the news only when it is told", drawn == [[], ["Wolves were seen on the north road by the gate."]], POOLS)

    # a move that turns it aside: they are told so, and tell nothing
    stub.decide_extra, stub.speech_extra = {"intent": "withhold"}, None
    reply.roll_move = lambda w, last, rng, forced=False: "deflect"
    del REQ[:]
    say(ASK)
    on = last("NPCSpeech")
    check("one who turns it aside is told so in the move's words and is given nothing to tell", K["deflect"]["says"] in on[2] and reply.R["intents"]["withhold"] in on[2]
          and told_in(on[2]) == [] and "Wolves were seen" not in on[2], on[2][-500:])

    # the board hangs where anyone reads it: every posting is in the request, decided or not; the town's news is still only as decided
    reply.roll_move = answer
    stub.decide_extra, stub.speech_extra = {"intent": "small_talk"}, None
    del REQ[:]
    say("Is there any work on the board?", to=master)
    on = last("NPCSpeech")
    posted = [f for part in ws.decision.around for f in part if reply.kind_of(f) == "board"]
    flat = " ".join(on[2].split())
    check("asked about the board, every posting on it is in front of them though none was decided; the news not decided is still not",
          posted and not ws.decision.shares and all(" ".join(f.text.split()) in flat for f in posted) and "Wolves were seen" not in on[2],
          ([f.id for f in posted], ws.decision.line()))

    # the reading fails: the engine's own candidates are told, and they still speak from them
    FAIL[0] = True
    stub.speech_extra = speak_it
    del ASKED[:], REQ[:]
    try:
        say("What do you know of the roads about here?")
    finally:
        FAIL[0] = False
    on = last("NPCSpeech")
    d = ws.decision
    check("when the reading fails they speak from the engine's own decision: its candidates as what they tell, no old reply asked for",
          ASKED[-1] == "NPCSpeech" and "NPCReply" not in ASKED and d.read == "engine" and told_in(on[2]) == reply.told(d) and ws.stood is True and not ws.last_crash, (ASKED, d.line()))

    # leaving: only with a parting aloud, and then the talk ends from the decision
    stub.decide_extra, stub.speech_extra = {"intent": "leave"}, {"speech": "Quiet enough here."}
    reply.roll_move = lambda w, last, rng, forced=False: "quiet"
    del REQ[:]
    say("I should be going soon.")
    on = last("NPCSpeech")
    check("one who leaves is told to say so; with no parting in the words nobody walks off", "aloud" in on[2].split("WHAT YOU DO IN THIS REPLY")[1]
          and any(n.id == npc.id for n in ws.present) and ws.convo, on[2][-300:])
    stub.speech_extra = {"speech": "Good day to you, then."}
    say("And who keeps the ledgers here?")
    check("...with one, they step away and the talk is over", not any(n.id == npc.id for n in ws.present) and store.load_npc(npc.id).away_until > ws.minutes
          and not ws.convo, (ws.convo, store.load_npc(npc.id).away_until, ws.minutes))
finally:
    reply.R["decide_then_speak"] = False
    reply.roll_move = real_roll
    stub.decide_extra = stub.speech_extra = None
    pulse.news_window, pulse.happenings_at = real_window, real_happen

# ---- the truth view leaves out a piece by its id, and nothing else
pulse.news_window = lambda *a, **k: [{**row, "text": "Wolves were seen on the north road by the gate."}, {**row, "text": "The chandler's cat had kittens in the loft."}]
try:
    town = truth.Scene(ws)
    view = town.view(truth.viewer_for_npc(master, ws.world), "townsfolk")
    before = view.lines("news")
    view.hide |= {"news:0"}
    after = view.lines("news")
finally:
    pulse.news_window = real_window
check("a view can leave one piece out of one reply by its id; the rest of what is there stays", len(before) == 2 and after == before[1:] and "chandler's cat" in view.text()
      and "Wolves were seen" not in view.text(), (before, after))
spy()
game.close()

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), file=sys.__stdout__)
sys.exit(1 if bad else 0)
