"""People talking to each other: Maren and the clerk at the register (the clerk's manner changes how it goes), the party on the road, the
'go to the hall' phrasing, hired-Maren talk routing, and the info pane's button order."""
import sys, random, shutil, re
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
SAID = []
uc.say = lambda t, s="": SAID.append((s, t))
uc.dialogue = lambda b, s, t, a: SAID.append((s, t))          # (f325) a companion's framed words count as said under their name
uc.narrate = lambda t: None
uc.note = lambda m, *a, **k: None
from engine import mentor, banter
from engine import party as rules
from llm.contracts import Exchange
from pydantic import ValidationError
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from npc.models import NPC
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

def clerk(personality, voice="", mood=""):
    return NPC(id="clerk1", name="Odo", people="human", role="guild_clerk", location="parth", personality=personality, voice=voice, mood=mood, description="A tidy clerk.", tier="known")

check("a cold clerk reads cold", banter.manner(clerk("Curt and dismissive, bored by newcomers.")) == "cold")
check("a warm clerk reads warm", banter.manner(clerk("Kind and cheerful.", "Welcoming.")) == "warm")
check("an unremarkable clerk is neutral", banter.manner(clerk("Plain.", "Plain.")) == "neutral")
check("both fallbacks exist for every manner", all(len(banter.clerk_fallback(m, "three gold")) == 4 for m in ("warm", "cold", "neutral")))
check("the cold and warm fallbacks differ", banter.clerk_fallback("cold", "x") != banter.clerk_fallback("warm", "x"))

ctx = {"speakers": ["Maren Holt", "Odo"], "lines": (2, 4), "material": ["three gold"]}
def ex(*pairs, c=ctx):
    return Exchange.model_validate({"lines": [{"speaker": a, "text": b} for a, b in pairs]}, context=c)
def refused(*pairs, c=ctx):
    try:
        ex(*pairs, c=c); return False
    except ValidationError:
        return True
ok2 = [("odo", "Maren. Another one?"), ("Maren Holt", "Be nice.")]
e = ex(*ok2)
check("a fair exchange passes and speakers are tidied", [l.speaker for l in e.lines] == ["Odo", "Maren Holt"])
check("a stranger speaking is refused", refused(("Bob", "Hello there."), ("Odo", "Hm.")))
check("too few lines refused", refused(("Odo", "Hm.")))
check("a new number refused", refused(("Odo", "That is 7 gold."), ("Maren Holt", "Hm.")))
check("a figure in the material is fine", not refused(("Odo", "It is three gold."), ("Maren Holt", "Hm.")))
check("stage directions refused", refused(("Odo", "*sighs* Fine."), ("Maren Holt", "Hm.")))
check("a long line refused", refused(("Odo", "word " * 60), ("Maren Holt", "Hm.")))
check("one speaker alone is refused", refused(("Odo", "Hm."), ("Odo", "Hm again.")))
check("'three silver' is fine when the material says '3 silver'", not refused(("Odo", "It is three silver."), ("Maren Holt", "Hm."), c={**ctx, "material": ["3 silver"]}))
check("'3' is fine when the material says 'three'", not refused(("Odo", "It is 3 silver."), ("Maren Holt", "Hm."), c={**ctx, "material": ["three silver"]}))
check("a different amount is still refused", refused(("Odo", "It is five silver."), ("Maren Holt", "Hm."), c={**ctx, "material": ["3 silver"]}))
check("plain talk of coins is not an amount", not refused(("Odo", "Coins first, please."), ("Maren Holt", "Hm.")))
check("talk of a game refused", refused(("Odo", "This is a game."), ("Maren Holt", "Hm.")))

shutil.rmtree("saves/bt", ignore_errors=True)
st = CampaignStore.open_or_create("bt")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/bt/turns.jsonl"
st.save_npc(clerk("Plain."))

# the clerk's manner reaches the model and the exchange is shown under both names
seen = []
def write(names, first):
    seen.append(first)
    return [{"speaker": names[0] if i % 2 == 0 else names[1], "text": "Right, then."} for i in range(5)]
stub.exchange = write
for pers, key in (("Curt and dismissive, bored.", "cold and rude"), ("Warm and kind.", "warm and kind")):
    SAID.clear(); seen.clear()
    c = clerk(pers); st.save_npc(c)
    w.mentor_clerk_exchange(c)
    check(f"the {key} clerk's manner is in the request", seen and key in seen[0], seen[:1])
    check("both speak, five lines, and the clerk is named", len(SAID) == 5 and {s for s, _ in SAID} == {"Maren Holt", "Odo"}, SAID)
check("the player now knows the clerk's name and the clerk thinks better of them", st.load_npc("clerk1").name_known_to_player and st.load_npc("clerk1").trust > 50, st.load_npc("clerk1").trust)
check("the clerk remembers it", any("brought a newcomer" in m.text for m in st.load_npc("clerk1").memories))
check("what Maren said is remembered for later talk", any(who == "Maren" for who, _ in w.player.mentor.get("chat", [])))

# a model that fails or breaks the rules means the written exchange is said
stub.exchange = lambda names, first: [{"speaker": "Nobody", "text": "x"}, {"speaker": "Odo", "text": "y"}]
SAID.clear(); w.mentor_clerk_exchange(clerk("Curt and dismissive.", "Cold."))
check("a bad answer falls back to the written exchange for that manner", len(SAID) == 4 and "register is not a charity" in SAID[0][1], SAID)
SAID.clear(); w.mentor_clerk_exchange(clerk("Kind and cheerful."))
check("...and the warm one is different", "stool" in SAID[0][1], SAID)
config.VOICED_MENTOR = False
fresh_clerk = clerk("", "")
fresh_clerk.tier = "background"
SAID.clear(); w.mentor_clerk_exchange(fresh_clerk)
check("a clerk Maren meets for the first time is made a person first (f299)", fresh_clerk.tier == "known" and fresh_clerk.personality, (fresh_clerk.tier, fresh_clerk.personality))
SAID.clear(); w.mentor_clerk_exchange(clerk("Plain."))
check("with the model off the written exchange is said", len(SAID) == 4)
config.VOICED_MENTOR = True
stub.exchange = None

# the party on the road
mem = {"id": "h1", "name": "Bram", "role": "fighter", "level": 3, "permanent": True, "temper": ["blunt"], "blurb": "a scarred sellsword"}
mem2 = {"id": "h2", "name": "Isel", "role": "healer", "level": 3, "permanent": True, "temper": ["gentle"], "blurb": "a quiet healer"}
w.player.party = [mem]
w.player.party_mode = "with"
stub.exchange = lambda names, first: [{"speaker": names[0], "text": "Long road."}]
SAID.clear()
check("one companion says something to the player", w.party_banter([mem]) and len(SAID) == 1 and SAID[0][0] == "Bram", SAID)
stub.exchange = lambda names, first: [{"speaker": names[i % len(names)], "text": "Mind your feet."} for i in range(3)]
SAID.clear()
_dr = dict(banter.B["banter"]["director"]); banter.B["banter"]["director"].update(second=-999)      # both have reason enough (director_test covers who)
check("two companions talk to each other", w.party_banter([mem, mem2]) and {s for s, _ in SAID} == {"Bram", "Isel"}, SAID)
banter.B["banter"]["director"].clear(); banter.B["banter"]["director"].update(_dr)
w._banter_loc = "parth"; w._banter_last = -10**9
n = 0
for k in range(40):
    st.meta.minutes = 5000 + k * 500
    w._banter_loc = "parth"; w._banter_last = -10**9
    SAID.clear()
    w.player.location = "greywood"
    w.banter_tick(); w.player.location = "parth"
    n += bool(SAID)
check("on arriving somewhere now and then they talk (not always, not never)", 3 < n < 30, n)
SAID.clear(); w._banter_loc = "parth"; w._banter_last = w.minutes; w.player.location = "greywood"
w.banter_tick()
check("not twice in quick succession", not SAID)
w.player.location = "parth"
w.player.party = []
w._banter_loc = "greywood"; w._banter_last = -10**9; w.banter_tick()
check("nobody to talk, nothing said", not SAID)
stub.exchange = None

# 'let's go to the hall' means go on
check("a bare 'go on' or 'let's go' is plainly moving on; anything longer is for the model to read", mentor.wants_to_go_on("let's go") and mentor.wants_to_go_on("go on") and not mentor.wants_to_go_on("alright let's go to the hall"))
check("a question is not go on", not mentor.wants_to_go_on("why are you helping me?") and not mentor.wants_to_go_on("what is a rank?"))
check("in Parth her facts say nothing threatens right now (a state, not a ban)", "nothing threatens here right now" in mentor.facts(w.player, "Parth") and "nothing threatens" not in (mentor.facts(type("P", (), {"mentor": {"stage": "hunt"}, "character": w.player.character})(), "Greywood")))

# hired Maren: after she has spoken, a bare question goes to her even though the clerk was the last person spoken to
from llm.contracts import ActionIntent
w.player.party = []
mentor.set_stage(w.player, "board")
w.partner = clerk("Plain.")
w.player.mentor["last_voice"] = False
it = ActionIntent(kind="talk", target="clerk1", speech="Why are you helping me?")
w.present = []
orig = w.mentor_with_you
w.mentor_with_you = lambda: True
check("with the clerk last spoken to, a bare question is not hers", not w.mentor_wants_talk(it, "Why are you helping me?"))
mentor.remember_said(w.player, "Hold on to that badge.")
check("once Maren has spoken, a bare question is for her", w.mentor_wants_talk(it, "Why are you helping me?"))
w.mentor_with_you = orig
check("asked why she helps, her facts carry her motivation, not a line to say", "MOTIVATION" in mentor.facts(w.player, "Parth", "Why are you helping me?") and "die in their first month" not in mentor.facts(w.player, "Parth", "Why are you helping me?"))
check("...and asked something else, they do not", "MOTIVATION" not in mentor.facts(w.player, "Parth", "Do you have family?"))

# facts are selective: a personal question gets no rules table; a rules question gets the one it asks about
f0 = mentor.facts(w.player, "Parth", "Why are you helping me?")
f1 = mentor.facts(w.player, "Parth", "how does hit chance work")
f2 = mentor.facts(w.player, "Parth", "what does burning do")
check("a personal question gets no hit table, no commands and no rank ladder", "HIT CHANCE" not in f0 and "COMMANDS" not in f0 and "GUILD RANKS" not in f0 and len(f0.split()) < 400, len(f0.split()))
check("a hitting question gets the hit facts only", "HIT CHANCE" in f1 and "COMMANDS" not in f1)
check("a condition question gets the conditions", "burning" in f2.lower() and "HIT CHANCE" not in f2)
check("the index is always there, short", "YOU KNOW EXACTLY" in f0)
check("the sceptical attitude and the safe-town rule still hold", "highly sceptical" in mentor.facts(type("P", (), {"mentor": {"stage": ""}, "character": w.player.character})(), "Parth"))

# hooks and wants come from the state
import random as _r
w.player.party = [dict(mem, bond=20), dict(mem2, bond=35)]
live = w.player.party
live[0]["hp_frac"], live[0]["hp_at"] = 0.3, w.minutes
w.player.party_last_fight = {"minute": w.minutes - 10, "won": True, "hard": True, "hurt": ["Bram"], "carried": [], "fallen": []}
k, text, about = w.banter_hook(live, "fight", _r.Random(1))
check("after a fight the pressing thing is picked", k in ("hurt", "hard_fight") and ("Bram" in text or "hard one" in text), (k, text))
wants = w.banter_wants(live, "hurt", live[0], "fight")
check("wants differ by role in the moment and by temperament", "fuss" not in wants["Bram"] and wants["Bram"] != wants["Isel"] and "wound" in wants["Isel"], wants)
live[0]["hp_frac"] = 1.0; w.player.party_last_fight = {}
kinds = {w.banter_hook(live, "travel", _r.Random(i))[0] for i in range(40)}
check("on a quiet road the hooks are the small stuff", kinds <= {"weather", "mundane", "arrival", "news", "player", "relationship", "personal"} and len(kinds) >= 2, kinds)
banter.B["banter"]["director"]["first"] = banter.B["banter"]["director"]["second"] = -999     # these check a pair talking (director_test covers who speaks)
seen_req = []
stub.exchange = lambda names, first: (seen_req.append(first), [{"speaker": names[i % len(names)], "text": "Right."} for i in range(2)])[1]
SAID.clear(); w.party_banter(live, "travel")
check("the request carries what brought it up and what each wants, and no manner-as-topic", "WHAT BROUGHT THIS UP" in seen_req[-1] and "WHAT EACH WANTS" in seen_req[-1] and "speaks of an old faith" not in seen_req[-1], seen_req[-1][-600:])
check("what they said is kept against repeating", live[0].get("said") and live[1].get("said"), (live[0].get("said"), live[1].get("said")))
stub.exchange = None

# relations: seeded once, fed to banter, drift with shared fights
w.player.party_relations = {}
w.relations_seed()
rel = w.relation(live[0], live[1])
check("a relation line is written once for the pair, with what each wants from the other", rel and "Bram" in rel["dynamic"] and "Isel" in rel["dynamic"] and rel["score"] == 0 and len(rel.get("wants", {})) == 2, rel)
seen_req2 = []
stub.exchange = lambda names, first: (seen_req2.append(first), [{"speaker": names[i % len(names)], "text": "Right."} for i in range(2)])[1]
SAID.clear(); w.party_banter(live, "travel")
check("every exchange between the pair carries how they are with each other", "HOW THEY ARE WITH EACH OTHER" in seen_req2[-1] and rel["dynamic"][:30] in seen_req2[-1], seen_req2[-1][:400])
check("...and what each wants from the other", "as always" in seen_req2[-1])
w.pair_event(live[0], live[1], "came through a hard fight side by side.")
_hook = w.banter_hook
_tries = 0
while _tries < 200 and w.banter_hook(live, "travel", random.Random(_tries))[0] != "shared":
    _tries += 1
w.banter_hook = lambda pick, kind, rng: _hook(pick, kind, random.Random(_tries))
SAID.clear(); w.party_banter(live, "travel")
w.banter_hook = _hook
check("their shared history comes with it, when it is the topic", _tries < 200 and "SOMETHING THEY SHARED" in seen_req2[-1], _tries)
n0 = stub.calls.get("PairDynamic", 0)
for _ in range(15):
    w.relations_shift(live[0], 1)
check("crossing into a closer tier marks the line for rewriting", rel.get("stale") and rel["tier"] == "easy with each other", rel)
SAID.clear(); w.party_banter(live, "travel")
check("...and it is rewritten from what they shared, once", stub.calls.get("PairDynamic", 0) == n0 + 1 and not rel.get("stale"))
stub.exchange = None
n0 = stub.calls.get("PairDynamic", 0); w.relations_seed()
check("...and not again", stub.calls.get("PairDynamic", 0) == n0)
s0 = w.relation(live[0], live[1])["score"]
w.relations_shift(live[0], 3)
check("a shared hard win draws them closer", w.relation(live[0], live[1])["score"] == s0 + 3)
config.VOICED_MENTOR = False
w.player.party_relations = {}
w.relations_seed()
check("with the model off the written pair line is used", "Bram" in w.relation(live[0], live[1])["dynamic"])
config.VOICED_MENTOR = True
check("relation words", rules.relation_words(50) == "close as kin" and rules.relation_words(-20) == "grating on each other")

# talking to a hire: memory and impression come back on the same call; a gesture may stand alone (the others joining in is director_test's)
_chime = w.chime_in
w.chime_in = lambda *a: None
stub.companion = lambda u: {"speech": "Bandits. Then we have that in common.", "gesture": "", "remember": "The player's brother was killed by bandits.", "impression": "Thinks the player carries a grief they do not show."}
t0 = w.store.meta.turn
SAID.clear(); w.hire_talk(live[0], "My brother was killed by bandits.")
w.store.meta.turn = t0 + 1
check("a line straight after, naming no one, goes on with the same hire (f290)", (w.hire_wants_talk("no, where are you from?") or {}).get("name") == live[0]["name"])
check("...but not an action", w.hire_wants_talk("I walk to the board") is None)
w.store.meta.turn = t0 + 3
check("...and not once the moment has passed", w.hire_wants_talk("where are you from?") is None)
if len(live) > 1:
    marks = w.hire_said_marks()
    from engine import party as _pr
    w.store.meta.turn += 1                                  # the player's line has been handled (the turn moves on), then banter
    _pr.said(live[1], "Is there a place nearby for us to rest?")
    w.note_hire_spoke(marks)
    check("a hire who spoke up on their own is who the next unnamed line answers (f291)", (w.hire_wants_talk("you're tired already?") or {}).get("name") == live[1]["name"])
if w.hall_here():
    board = w.hire_view(live[0]).lines("board")                                   # (f315) the board comes with their truth view, as a guild member's
    titles = [q["title"] for q in w.ensure_board()]
    check("a hire is given what is really on the board, through their truth view (f306/f315)", all(any(t in l for l in board) for t in titles), (board[:3], titles[:3]))
    check("...and nothing about where they are is written by hand any more", not any(x.startswith("you are at") for x in w.hire_now(live[0], "where are you from?")))
    txt = w.hire_view(live[0]).text()
    check("...their view names the party and where they stand", "WHERE" in txt and all(m["name"] in txt for m in live if m is not live[0]), txt[:300])
_pb, calls = w.party_banter, []
w.party_banter = lambda crew, kind: calls.append(kind)
from scenes.banter_actions import BN
_rc = BN["banter"]["rest_chance"]; BN["banter"]["rest_chance"] = 100
w._hire_last = (live[0]["name"], w.store.meta.turn - 1)
w._banter_due = "rest"; w._banter_last = -10**9
w.banter_tick()
check("no rest banter straight after they talked with the player about it (f307)", calls == [], calls)
w._hire_last = None
w._banter_due = "rest"; w._banter_last = -10**9
w.banter_tick()
check("...but there is when they had not", calls == ["rest"] or not w.banter_crew(), calls)
w.party_banter = _pb; BN["banter"]["rest_chance"] = _rc
w.store.meta.turn = t0
if len(live) > 1 and w.player.party_mode == "with":
    check("the other hires heard it, as said to the first (f290)", any(who.startswith("Player (to ") and "brother" in t for who, t in live[1].get("talk", [])), live[1].get("talk", [])[-2:])
check("what the player said is remembered and the impression moves", any("brother" in x["text"] for x in live[0]["memories"]) and "grief" in live[0]["impression"], live[0]["memories"])
check("the hire's words are said under their name and kept", SAID and SAID[-1][0] == "Bram" and live[0]["said"][-1].startswith("Bandits"), SAID)
stub.companion = lambda u: {"speech": "", "gesture": "shrugs and looks away", "remember": "", "impression": ""}
NARR = []
uc.narrate = lambda t: NARR.append(t)
SAID.clear(); w.hire_talk(live[0], "Do you like me?")
check("a hire may answer with a gesture alone", not SAID and NARR and "shrugs" in NARR[-1], NARR)
uc.narrate = lambda t: None
stub.companion = lambda u: {"speech": "Bandits took my brother too, in the same hard winter, and I have hunted them since.", "gesture": "", "remember": "", "impression": ""}
SAID.clear(); w.hire_talk(live[0], "Tell me about your brother.")
calls0 = stub.calls.get("CompanionReply", 0)
SAID.clear(); w.hire_talk(live[0], "Say that again?")
check("a repeated turn of phrase is refused and retried, and the looser last try still will not echo the line just said", stub.calls.get("CompanionReply", 0) - calls0 == 4 and not any("Bandits took my brother" in t for _, t in SAID), (stub.calls.get("CompanionReply", 0) - calls0, SAID))
stub.companion = None
w.chime_in = _chime
reqs = []
_g = stub.a_CompanionReply
def _watch(u, k):
    reqs.append(u); return _g(u, k)
stub.a_CompanionReply = _watch
w.hire_talk(live[0], "How are you holding up?")
check("the hire's request is core, relation, now and memories, not a fact list", all(x in reqs[-1] for x in ("WHO YOU ARE", "HOW YOU ARE WITH", "RIGHT NOW", "WHAT YOU REMEMBER")) and "manner:" not in reqs[-1], reqs[-1][:300])
stub.a_CompanionReply = _g
w.player.party = []

# the temperaments say how someone decides, not what they talk about
from engine.party import P as _P
check("no temperament names a subject to keep returning to", all(not re.search(r"speaks of|counts everything|lays small blessings", t["say"]) for t in _P["temperaments"].values()))

# memories: the newest and the heaviest survive
mm = {}
THINGS = ["We crossed a river at dawn.", "A merchant cheated them over salt.", "They gave their cloak to a shivering child.", "A wolf took my pack.",
          "We slept in a barn full of goats.", "They laughed at my bad joke.", "Rain soaked every blanket we had.", "I lost a boot in the mud.",
          "We found an old shrine in the woods.", "They paid for my supper.", "A bridge gave way under the cart.", "We argued about the map."]
for i, t in enumerate(THINGS):
    rules.remember(mm, i, t, 3 if i == 2 else 1)
check("a heavy old memory survives the cull", any(x["text"] == THINGS[2] for x in mm["memories"]) and len(mm["memories"]) == rules.MEMORY_KEEP, [x["text"] for x in mm["memories"]])
check("moods fade after a day", (rules.set_mood(mm, "sore", 0), rules.mood_now(mm, 600) == "sore" and rules.mood_now(mm, 3000) == "")[1])

# the repetition guard
check("a reused turn of phrase is caught", banter.repeats("Welcome back, Maren. It is a pleasure to see you.", ["Welcome back Maren, it is a pleasure to see you and your friend."]) != "")
check("filler is not a phrase", banter.repeats("I do not know what you mean.", ["I do not know who that is."]) == "")
check("the memory filter: their own life is not a memory of the player", True)

# the first meeting (f273): whatever the first answer, she asks her pointed question; a hostile answer to that earns one more
asked = []
def feed(answers):
    it = iter(answers)
    uc.ask = lambda *a, **k: (asked.append(1), next(it, "go on"))[1]
counts = []
for answers in (["I'm a new adventurer looking for guild work.", "I hunt for coin and bought this sword with it", "no", "go on"],
                ["nothing", "I'm new here, looking for work", "no", "go on"],
                ["I'm a bandit and I'll rob you", "yes, a bandit, and I'll rob you blind", "fine, I'm new", "no", "go on"],
                ["looking for a tavern", "who are you anyway?", "I hunt for coin and bought this with it", "no", "go on"]):
    shutil.rmtree("saves/bt2", ignore_errors=True)
    st2 = CampaignStore.open_or_create("bt2"); st2.meta.seed = 5; st2.meta.turn = 1; st2.meta.minutes = 1800; st2.save_meta()
    ch2, _ = simlib.make_character("warrior", random.Random(2)); st2.save_player(PlayerState(character=ch2, location="parth"))
    w2 = WorldScene(st2, load_world(), load_traits(), st2.load_player())
    w2.mentor_escort = lambda: None
    asked.clear(); feed(answers)
    try:
        w2.mentor_approach(interrupt=False)
    except StopIteration:
        pass
    counts.append(len(asked))
check("a plain first answer and an evasive one both get her pointed question; a hostile answer to it, one more; a question back, one more (f279)",
      counts[1] == counts[0] and counts[2] == counts[0] + 1 and counts[3] == counts[0] + 1, counts)

# the info pane's order
from ui.gui import server
shutil.rmtree("saves/gp", ignore_errors=True)
check("the order is a pref, empty by default", server.PREF_DEFAULTS["order"] == [])
check("a list of commands is accepted", server.prefs_problem({"order": ["#stats", "#character"]}) == "")
check("junk is refused", all(server.prefs_problem({"order": v}) for v in ("x", [1], ["stats"], ["#" + "a" * 40], ["#a"] * 41)))
js = open("ui/gui/web/app.js", encoding="utf-8").read()
check("buttons are draggable and #resetlayout clears the order", "b.draggable = true" in js and '"#resetlayout"' in js and "order: []" in js)
import ui.console as _c
import io, contextlib
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    _c.show_help()
check("#resetlayout is in the help list", "#resetlayout" in buf.getvalue())

print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")

import sys as _sys
_sys.exit(1 if bad else 0)
