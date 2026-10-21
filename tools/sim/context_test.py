"""What goes into a character's prompt for a scene (engine/context.py), the engine's hold on background concerns, recent lines sent only when
on topic, and what a character says about themselves becoming canon (engine/canon.py)."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
SAID = []
uc.say = lambda t, s="": SAID.append((s, t))
uc.narrate = lambda t: None
uc.note = lambda m, *a, **k: None
from engine import banter, canon, context, mentor, quirks
from engine import party as rules
from llm.contracts import CompanionReply
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/ctx", ignore_errors=True)
st = CampaignStore.open_or_create("ctx")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/ctx/turns.jsonl"

def hire(i, temper, motive):
    m = {"id": f"h{i}", "name": ["Bram Voss", "Isel Quill"][i], "role": ["fighter", "priest"][i], "level": 3, "rank": "F", "permanent": True,
         "temper": temper, "motive": motive, "line": "will not take from the poor", "bond": 15, "memories": [], "said": [], "talk": [], "blurb": "a scarred sellsword"}
    quirks.roll(m, random.Random(i))
    return m

bram, isel = hire(0, ["blunt", "dry"], "rank"), hire(1, ["gentle", "devout"], "protect")
bram["capped"] = True
w.player.party = [bram, isel]; w.player.party_mode = "with"
w.quirked(bram); w.quirked(isel)

# ---- concerns: the engine decides when a background matter comes up
keys = [c["key"] for c in w.companion_concerns(bram)]
check("a capped hire with the rank motive has two concerns: the promotion and what drives them", keys == ["promotion", "motive"], keys)
check("a question about the road does not bring the promotion", "rank allows" not in w.companion_core(bram, "how was the road?"))
check("a question about rank does", "rank allows" in w.companion_core(bram, "what about your rank in the guild?"))
check("a pressing scene never brings a concern unasked", all("rank allows" not in w.companion_core(bram, f"{x} is hurt and it shows", "pressing")
                                                              for x in ("Bram", "Isel")))
check("nothing comes into a prompt at random: every scene picks only by relevance", all(set(v) <= {"k"} for v in context.SCENES.values()))

def hooks(n=300):
    out = []
    for k in range(n):
        st.meta.minutes = 1800 + k * 7
        out.append(w.banter_hook([bram, isel], "travel", random.Random(k))[0])
    st.meta.minutes = 1800
    return out
h = hooks()
share = h.count("promotion") / len(h)
check("when nothing presses, the everyday things are always on offer, so the promotion is not the only topic", share < 0.4 and {"weather", "mundane"} <= set(h), (share, set(h)))
context.mark(bram, "promotion", w.minutes)
h2 = hooks()
check("once raised, the promotion is not a hook again until its cooldown has run", "promotion" not in h2, h2.count("promotion"))
core = w.companion_core(bram, "the weather is turning", "ease")
check("...and the prompt says it was raised lately, to leave it alone unless asked", "ALREADY RAISED LATELY" in core and "promotion" in core, core)
check("...but asked about it, it is there", "rank allows" in w.companion_core(bram, "what about your rank in the guild?"))
st.meta.minutes += context.COOLDOWN["promotion"] + 1
check("after the cooldown it is due again", context.due(bram, "promotion", w.minutes))
bram["raised"] = {}
k = context.note_spoken(bram, "I want my rank raised before the next contract.", w.minutes, w.companion_concerns(bram))
check("words that touch a concern mark it raised", "promotion" in k and not context.due(bram, "promotion", w.minutes), k)
bram["raised"] = {}

# ---- recent lines: only the ones on topic go into the prompt; the guard still has them all
said = ["I want my rank raised, and the fee paid.", "The guild fee is owed today.", "The wolves were thin this winter."]
r = banter.unsaid_rule(said, "how are the wolves this year?")
check("a recent line off the topic is not in the prompt", "fee" not in r and "wolves" in r, r)
check("with nothing on topic, no recent lines at all", banter.unsaid_rule(said[:2], "is it going to rain?") == "")
check("without a query (Maren's summaries) the last lines are all there", "fee" in banter.unsaid_rule(said))

# ---- after a hard fight with the promotion due, the banter about it does not carry the promotion
bram["hp_frac"], bram["hp_at"] = 0.35, w.minutes
w.player.party_last_fight = {"minute": w.minutes - 30, "won": True, "hard": True, "hurt": ["Bram Voss"], "carried": [], "fallen": []}
seen = []
stub.exchange = lambda names, first: (seen.append(first), [{"speaker": n, "text": f"{n.split()[0]} says something new {len(seen)} {i}."} for i, n in enumerate(names)])[1]
bram["said"] = ["The guild fee is owed today, and I want my rank."]
w.party_banter([bram, isel], "fight")
check("after a hard fight, the request carries neither the promotion nor his line about the fee", seen and "rank allows" not in seen[-1] and "guild fee" not in seen[-1], seen[-1][-1500:] if seen else "")
bram["hp_frac"] = 1.0; w.player.party_last_fight = {}

# ---- canon
check("claims are cleaned: empties, one-word and overlong ones dropped, at most two", canon.clean(["none", "Yes", "I was born in a mill town.", "x " * 40, "My mother sang.", "I kept goats."]) == ["I was born in a mill town.", "My mother sang."])
bad0 = canon.keep(bram, ["My father kept bees on the hill."], ["The river ferries stop running in winter."], 1)
check("a new fact about themselves becomes canon; one about the world becomes their belief", not bad0 and bram["canon"][-1]["text"] == "My father kept bees on the hill." and bram["beliefs"][-1]["text"].startswith("The river ferries"))
canon.keep(bram, ["My father kept bees on the hill."], [], 2)
check("the same fact again is not kept twice", sum(1 for c in bram["canon"] if "bees" in c["text"]) == 1)
check("canon comes back when the moment is about it", "kept bees" in w.companion_core(bram, "tell me about your father"))
import re as _re
def _canon(u):
    nums = {int(n): t for n, t in _re.findall(r"^(\d+)\. (.*)$", u, _re.M)}
    bees = next((n for n, t in nums.items() if "bees" in t), 0)
    sister = next((n for n, t in nums.items() if "sister" in t), 0)
    if "NEW STATEMENT: My father was a fisherman" in u and bees:
        return {"verdict": "contradicts", "which": bees}
    if "NEW STATEMENT: I have a younger sister" in u and sister:
        return {"verdict": "same", "which": sister}
    return {"verdict": "new", "which": 0}
stub.canon = _canon
b = canon.keep(bram, ["My father was a fisherman on the coast."], [], 3)
check("a claim that contradicts canon is caught and not kept", b and "bees" in b[0][1] and not any("fisherman" in c["text"] for c in bram["canon"]), (b, bram["canon"]))
check("details written about them are compared in their own voice", canon.first_person("They think of a younger sister who believes they are traveling the trade roads.")
      == "I think of a younger sister who believes I am traveling the trade roads.")
sis = {"id": "s", "name": "Isel", "details": ["They think of a younger sister who works a farm and believes they are traveling the trade roads."], "memories": []}
canon.keep(sis, ["I have a younger sister who thinks I travel the trade roads."], [], 3)
check("the same fact as a hire detail, said in their own words, is not kept again", not sis.get("canon"), sis.get("canon"))
sis["memories"].append({"day": 1, "text": "I told them something I tell nobody: I failed the rank test twice before I passed.", "weight": 3})
check("a secret they have told counts as already known", any("failed the rank test" in k for k in canon.known(sis)))
canon.keep(sis, [], [], 5, now=["I am paying for the dried meat and water."])
check("what is true of them only now is kept apart from their canon", not any("dried meat" in c["text"] for c in sis.get("canon", [])) and sis["state_now"][-1]["text"].startswith("I am paying"))
check("...offered back while it is fresh", any("dried meat" in r["text"] for r in canon.records(sis, 5)))
check("...and forgotten a couple of days later", not any("dried meat" in r["text"] for r in canon.records(sis, 8)))
canon.keep(sis, [], [], 8, now=["I am carrying a lantern."])
check("...and dropped from the record once stale", not any("dried meat" in x["text"] for x in sis["state_now"]))

# each kind of fact in its own bucket
from llm.contracts import Extracted
ex = Extracted.model_validate({"facts": [{"speaker": "Bram", "kind": "life", "text": "a"}, {"speaker": "Bram", "kind": "now", "text": "b"},
                                         {"speaker": "Bram", "about": "world", "kind": "life", "text": "c"}, {"speaker": "Bram", "kind": "plan", "text": "d"}]})
check("older or loose kinds are read sensibly", [f.kind for f in ex.facts] == ["backstory", "moment", "world", "intention"], [f.kind for f in ex.facts])
bk = {"id": "b", "name": "Bram", "memories": [], "details": []}
canon.keep(bk, [], [], 10, buckets={"backstory": ["My old man had a forge and a lot of debt."], "trait": ["I cannot swim a stroke."],
                                     "possession": ["I have a spare whetstone."], "intention": ["I mean to see the far north before my legs give out."],
                                     "commitment": ["I promised my sister I would write every winter."], "moment": ["I am paying for the dried meat."],
                                     "world": ["The ferries on the Wend stop in winter."]})
check("backstory and traits are canon; possessions, intentions, promises and today's facts are not",
      [c["text"] for c in bk["canon"]] == ["My old man had a forge and a lot of debt."] and bk["traits"][0]["text"].startswith("I cannot swim")
      and bk["possessions"] and bk["intentions"] and bk["commitments"] and bk["state_now"] and bk["beliefs"])
recs = {r["text"].split(":")[0] for r in canon.records(bk, 10)}
check("each is offered back under its own name", {"Your past (true; you said it before)", "True of you (you said it before)", "Something you own",
      "Something you mean to do", "Something you have promised, or owe", "True of you for now (you said it today)"} <= recs, recs)
later = {r["text"].split(":")[0] for r in canon.records(bk, 25)}
check("each keeps as long as such a thing stays true: today's facts and possessions fade, a plan and a promise last longer",
      "True of you for now (you said it today)" not in later and "Something you own" not in later and "Something you mean to do" in later
      and "Something you have promised, or owe" in later and "Your past (true; you said it before)" in later, later)
canon.keep(bk, [], [], 11, buckets={"possession": ["I have a spare whetstone."]})
check("the same possession said again refreshes it, not a second copy", len(bk["possessions"]) == 1 and bk["possessions"][0]["day"] == 11)
check("everything they have said about themselves is known to the extractor", len(canon.said_about_self(bk)) == 6)

# a draft that contradicts canon keeps nothing, not even its harmless parts
tx = {"id": "t", "name": "Tam", "memories": [], "details": [], "canon": [{"text": "My father was a smith.", "day": 1}]}
stub.canon = lambda u: {"verdict": "contradicts", "which": 1} if "fisherman" in u else {"verdict": "new", "which": 0}
bad_tx = canon.keep(tx, ["My mother ran an inn by the river.", "My father was a fisherman all his life."], [], 2)
check("a draft with one contradiction keeps none of its claims (the player never heard it)", bad_tx and [c["text"] for c in tx["canon"]] == ["My father was a smith."], tx["canon"])
p_tx = canon.review(tx, ["My mother ran an inn by the river."], [], 2)
check("reviewing a draft changes nothing until it is committed", not p_tx.bad and len(tx["canon"]) == 1)
p_tx.commit()
check("...and committing it keeps it", any("inn" in c["text"] for c in tx["canon"]))
check("settle(): a contradicting first draft is sent back with what is true, and nothing kept",
      canon.settle(canon.review(tx, ["My father was a fisherman."], [], 3), 0).startswith("ALREADY TRUE") and not any("fisherman" in c["text"] for c in tx["canon"]))
p_last = canon.review(tx, ["My father was a fisherman.", "I keep bees now and then."], [], 3)
canon.settle(p_last, 1)
check("...on the last try the line stands: its harmless claims are kept, the contradicting one never is",
      any("bees" in c["text"] for c in tx["canon"] + tx.get("traits", [])) and not any("fisherman" in c["text"] for c in tx["canon"]), tx["canon"])
stub.canon = None
from engine import voice_profile as _vp
fam_m = {"name": "F", "role": "fighter", "blurb": "a sellsword", "speech": {"background": "cook", "culture": "heartland"}}
check("their family is part of what they were given to begin with", any("cooks and innkeepers" in g for g in canon.given(fam_m)), canon.given(fam_m))
stub.canon = _canon

# hire_talk: a reply about themselves is read for new facts; a contradicting one is written once more, told what is true
calls = []
def comp(u):
    calls.append(u)
    if len(calls) == 1:
        return {"speech": "My father fished the cold coast, and I mended his nets."}
    return {"speech": "My father kept bees, and I got stung for it."}
stub.companion = comp
stub.extract = lambda u: {"facts": [{"speaker": "Bram Voss", "about": "self", "kind": "life", "text": "My father was a fisherman on the coast."},
                                     {"speaker": "Bram Voss", "about": "self", "kind": "now", "text": "I have a whetstone in my pack."}]} if "fished" in u else {"facts": []}
SAID.clear()
w.hire_talk(bram, "What did your father do?")
check("a reply that contradicts canon is written again, told what is already true", len(calls) == 2 and "NEVER CONTRADICT" in calls[1] and "kept bees" in calls[1], calls[-1][-600:])
check("...and the second answer is the one said", SAID and "bees" in SAID[-1][1], SAID)
check("the rejected draft's harmless claim (what they carry) was not kept either", not any("whetstone" in x["text"] for x in bram.get("state_now", []) + bram.get("possessions", []) + bram["canon"]))
n_ex = stub.calls.get("Extracted", 0)
w.hire_talk(bram, "How was the road today?")
check("a reply not about them is not read for facts (no extra call)", stub.calls.get("Extracted", 0) == n_ex)
stub.companion = None; stub.canon = None

# banter: what someone says about themselves becomes their canon, read in one call for the exchange
stub.exchange = lambda names, first: [{"speaker": names[0], "text": "I grew up hauling nets with my father, before I ever held a sword."},
                                      {"speaker": names[1], "text": "It shows in your hands."}]
stub.extract = lambda u: {"facts": [{"speaker": "Bram", "about": "self", "text": "I grew up hauling nets on the Saltmarch docks."}]}
n_ex = stub.calls.get("Extracted", 0)
w.party_banter([bram, isel], "travel")
check("what someone says about themselves in banter becomes their canon (named by first name or full)", any("hauling nets" in c["text"] for c in bram["canon"]), bram["canon"])
check("...in one extraction call for the whole exchange", stub.calls.get("Extracted", 0) == n_ex + 1, stub.calls.get("Extracted", 0) - n_ex)
stub.exchange = None; stub.extract = None

# a reaction line (deeds, secrets) follows the same rule: a contradicting draft is written again
cl_calls = []
def _cl(u):
    cl_calls.append(u)
    return {"speech": "My father fished the cold coast, you know." if len(cl_calls) == 1 else "Good. My father would have done the same, at his bees."}
stub.companion = _cl
stub.canon = lambda u: {"verdict": "contradicts", "which": 1} if "fisherman" in u else {"verdict": "new", "which": 0}
stub.extract = lambda u: {"facts": [{"speaker": "Bram Voss", "kind": "backstory", "text": "My father was a fisherman."}]} if "fished" in u else {"facts": []}
said_cl = w.companion_line(bram, ["the player has just told you about their father"], "(the player talked about family)")
check("a reaction line that contradicts canon is written again too, and nothing from the first draft is kept",
      len(cl_calls) == 2 and "bees" in said_cl and not any("fisherman" in c["text"] for c in bram["canon"]), (len(cl_calls), said_cl))
stub.companion = None; stub.canon = None; stub.extract = None

# ---- something of their own: quiet talk is about the people
bram["raised"] = {"promotion": st.meta.minutes}
h3 = hooks()
check("when nothing presses, something of their own is the likeliest topic", h3.count("personal") / len(h3) > 0.3, (h3.count("personal"), len(h3)))
check("small talk with nothing in it is rare filler", h3.count("mundane") / len(h3) < 0.12, h3.count("mundane"))
check("the small-talk hook has no wording to copy", "packs" not in __import__("engine.banter", fromlist=["B"]).B["banter"]["hooks"]["mundane"])
seen.clear()
stub.exchange = lambda names, first: (seen.append(first), [{"speaker": n, "text": ["My sister married a miller, and I have not written in a year.", "Then write to her tonight, before you lose the nerve."][i % 2]} for i, n in enumerate(names)])[1]
for k in range(40):
    st.meta.minutes = 5000 + k * 13
    if w.banter_hook([bram, isel], "travel", random.Random(st.meta.seed * 31 + st.meta.minutes))[0] == "personal":
        break
before = len(bram.get("topics_used", [])) + len(isel.get("topics_used", []))
_orig = w.banter_hook
_got = []
w.banter_hook = lambda *a, **kk: (_got.append(_orig(*a, **kk)), _got[-1])[1]
w.party_banter([bram, isel], "travel")
w.banter_hook = _orig
after = len(bram.get("topics_used", [])) + len(isel.get("topics_used", []))
check("a personal topic, once talked about, is marked used so the next one is new", after == before + 1, (before, after, k, bram.get("topics_used"), isel.get("topics_used")))
check("...and it was in the request as what brought the talk up", seen and "on their mind" in seen[-1])
used = bram.get("topics_used", []) + isel.get("topics_used", [])
check("a used topic is not offered again while it is remembered", all((w.personal_topic(m, random.Random(1)) or ("",))[0] not in m.get("topics_used", []) for m in (bram, isel)))
st.meta.minutes = 1800; stub.exchange = None; bram["raised"] = {}

# ---- what they were given is not new canon
from engine import voice_profile
isel["speech"] = voice_profile.roll(random.Random(1), "human", "rimelands", "learner")
n0 = len(isel.get("canon", []))
canon.keep(isel, ["I grew up speaking the tongue of the Rimelands of the far north."], [], 4)
check("saying again only what they were given (their home and tongue) is not kept as canon", len(isel.get("canon", [])) == n0, isel.get("canon"))

# ---- Maren
sysm = mentor.chat_system()
check("Maren's chat answers what was asked, said once (in how she speaks), not three times over", "Answers what was asked" in sysm and "ANSWER FIRST" not in sysm and sysm.count("unless they ask what to do next") == 0)
check("Maren's way of speaking has no example to copy about drinking", "drink" not in " ".join(quirks.Q["maren"]["blueprint"]).lower())

shutil.rmtree("saves/ctx", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
