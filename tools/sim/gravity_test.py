"""How heavy a topic is decides when it comes up (engine/gravity.py); the reply to something that matters answers it first; a secret is
retold as itself, in their own words; a gesture is written about them, never as 'I'; and a hire the player has let down goes cold instead
of walking out."""
import collections, sys, random, shutil
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
from engine import canon, context, gravity, quirks
from engine import party as rules
from llm import embed
from llm import contracts
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/grav", ignore_errors=True)
st = CampaignStore.open_or_create("grav")
st.meta.seed = 7; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/grav/turns.jsonl"

LIGHT, HEAVY, PERSONAL = "a food or drink they love", "the first time they saw someone die", "someone they owe, in money or otherwise"
def hire(i, bond):
    m = {"id": f"g{i}", "name": ["Bram Voss", "Isel Quill"][i], "role": "fighter", "level": 3, "rank": "F", "permanent": True,
         "temper": ["blunt", "dry"], "motive": "coin", "line": "will not take from the poor", "bond": bond, "memories": [], "said": [], "talk": [],
         "blurb": "a scarred sellsword",
         "detail_kinds": [quirks.Q["detail_first"], LIGHT, HEAVY, PERSONAL, "a song, rhyme or game from childhood"],
         "details": ["They grew up hauling nets on a grey shore.", "They love cider so cold it hurts the teeth.",
                     "They watched a neighbour drown in the river mud when they were nine.", "They owe a carter for a broken axle.",
                     "They still hum a skipping rhyme about three crows."]}
    quirks.roll(m, random.Random(i))
    return m

# ---- where weight comes from
m = hire(0, 15)
gs = [g for _, g in gravity.details(m)]
check("each detail carries the weight of the subject it was written to", gs == ["personal", "light", "heavy", "personal", "light"], gs)
check("every subject in the data has a weight", all(g in gravity.LEVELS for g in quirks.Q["detail_kinds"].values()))
w.player.party = [m, hire(1, 15)]
w.relations_seed()
w.party_after_fight = getattr(w, "party_after_fight")
w.pair_event(w.player.party[0], w.player.party[1], "Bram was carried out of a fight and the other saw it happen.", "heavy")
check("what a pair went through keeps the weight the event gave it", w.relation(*w.player.party)["history"][-1]["gravity"] == "heavy")
p = canon.review(m, [], [], 1, buckets={"trait": ["I am afraid of deep water since my brother drowned."],
                                       canon.WEIGHTS: {canon._norm("I am afraid of deep water since my brother drowned."): "heavy"}})
p.commit()
check("what they say about themselves keeps the weight the extractor gave it", any(x.get("gravity") == "heavy" for x in m.get("traits", [])), m.get("traits"))
check("...and the scene builder sees it", any(r.get("gravity") == "heavy" for r in canon.records(m, 1)))
f = contracts.ExtractedFact.model_validate({"speaker": "Bram", "kind": "trait", "text": "I hum.", "weight": "Weighty"})
check("an unknown weight from the model reads as personal", f.weight == "personal")

# ---- unasked: by the moment
rng = random.Random(3)
items = gravity.details(m)
at_arrival = {gravity.choose(items, "arrival", rng, m, 5000)[1] for _ in range(300)}
check("walking into a place, a heavy thing never comes up unasked", "heavy" not in at_arrival and "light" in at_arrival, at_arrival)
m["bond"] = 15
at_rest = {gravity.choose(items, "rest", rng, m, 5000)[1] for _ in range(300)}
check("at rest with someone they do not yet trust, still nothing heavy", "heavy" not in at_rest, at_rest)
m["bond"] = 40; m.pop("heavy_at", None)
at_rest = [gravity.choose(items, "rest", rng, m, 5000)[1] for _ in range(600)]
check("at rest with someone they trust, a heavy thing can come up, and light and personal ones are still most of it",
      "heavy" in at_rest and at_rest.count("heavy") < at_rest.count("light") + at_rest.count("personal"), {g: at_rest.count(g) for g in gravity.LEVELS})
gravity.raised(m, "heavy", 5000)
check("once one is raised, not another for days", not gravity.heavy_allowed(m, 5000 + 1440) and gravity.heavy_allowed(m, 5000 + gravity._G()["heavy_gap_days"] * 1440))

# ---- the banter hook: arrival small talk is never heavy
bram, isel = w.player.party
bram.update(details=m["details"], detail_kinds=m["detail_kinds"], bond=40)
isel.update(details=m["details"], detail_kinds=m["detail_kinds"], bond=40)
heavy_txt = m["details"][2]
w.player.party_last_fight = None
hits = []
for k in range(300):
    for x in (bram, isel):
        x.pop("heavy_at", None)
    kind, text, _ = w.banter_hook([bram, isel], "travel", random.Random(k))
    hits.append((kind, text))
check("arriving somewhere, the drowning never comes up unasked", not any(heavy_txt in t for _, t in hits) and any(k == "personal" for k, _ in hits))
rest_hits = []
for k in range(400):
    for x in (bram, isel):
        x.pop("heavy_at", None)
    kind, text, _ = w.banter_hook([bram, isel], "rest", random.Random(k))
    rest_hits.append(text)
check("at rest among people who trust each other, it can", any(heavy_txt in t for t in rest_hits))
for k in range(400):
    for x in (bram, isel):
        x.pop("heavy_at", None)
    if heavy_txt in w.banter_hook([bram, isel], "rest", random.Random(k))[1]:
        break
check("...and raising it starts the wait before the next heavy thing", bram.get("heavy_at") is not None or isel.get("heavy_at") is not None)

# ---- asked: a heavier record needs the moment to be clearly about it
recs = [{"kind": "detail", "text": "About them: they watched a neighbour drown in the river.", "gravity": "heavy"},
        {"kind": "detail", "text": "About them: they love the river in spring.", "gravity": "light"}]
got, _ = context.select(m, recs, "talk", "how was the river crossing?", 5000, random.Random(1))
check("a passing mention of the river brings the light thing, not the drowning", any("spring" in g for g in got) and not any("drown" in g for g in got), got)
got, _ = context.select(m, recs, "talk", "did you ever watch anyone drown in a river?", 5000, random.Random(1))
check("asked about it, the heavy thing comes in", any("drown" in g for g in got), got)

# ---- answering first, by meaning
_whole = embed.whole
def fake(scores):
    embed.whole = lambda text, others: scores[:len(others)]
fake([0.3, 0.6])
why = contracts.answers_first("The heat is heavy today.", {"said": "My brother was killed by bandits.", "scene": ["you are at Parth; it is midday, hot"]})
check("an answer that opens on the weather after the player shares a loss is sent back", "first words" in why, why)
fake([0.7, 0.4])
check("...one that opens on what they said stands", contracts.answers_first("I am sorry about your brother.", {"said": "My brother was killed by bandits.", "scene": ["hot"]}) == "")
embed.whole = lambda text, others: None
check("...and without the helper model nothing is judged", contracts.answers_first("The heat.", {"said": "x", "scene": ["y"]}) == "")
embed.whole = _whole
reqs = []
stub.companion = lambda u: (reqs.append(u), {"speech": "I am sorry about your brother. That is a hard thing."})[1]
_feel = w.hire_feeling
w.hire_feeling = lambda mm, t: "painful_told" if "killed" in t else ""      # judged by meaning in play; the word fallback here cannot
w.hire_talk(bram, "My brother was killed by bandits last winter.")
check("telling them something painful puts 'answer it first' into what they are told", reqs and quirks.Q["answer_told"]["rule"][:30] in reqs[0], reqs[0][-1500:] if reqs else "")
reqs.clear(); w.hire_talk(bram, "Nice weather for walking.")
check("...and small talk does not", reqs and quirks.Q["answer_told"]["rule"][:30] not in reqs[0])
stub.companion = None
w.hire_feeling = _feel

# ---- a secret retold as itself
secret = "I let my sister take the blame for the fire, and she has never said a word."
fake([0.5, 0.8])
check("a retelling closer to another thing of theirs than to the secret is sent back", "decided to tell" in contracts.retells("I hum a rhyme.", {"text": secret, "others": ["They hum a rhyme."]}))
fake([0.8, 0.4])
check("...one that is the secret, in other words, stands", contracts.retells("My sister took the blame for what I did.", {"text": secret, "others": ["They hum a rhyme."]}) == "")
embed.whole = lambda text, others: None
check("...and without the helper model its rarest words must survive", "keep the word" in contracts.retells("I did a bad thing once.", {"text": secret, "others": []}))
embed.whole = _whole

# ---- gestures in the first person
check("a gesture written as 'I turn my head' is dropped", quirks.keep_gesture("I turn my head away from the carcass", {"gesture_now": True, "gestures": []}, "Isel Quill") == "")
check("...one written about them is kept", quirks.keep_gesture("turns away from the carcass", {"gesture_now": True, "gestures": []}, "Isel Quill") != "")

# ---- cold, not gone
c = hire(0, -5)
check("a hire the player has let down is cold, and says so in how they are with the player", rules.bond_tier(c) == "cold" and "stopped expecting better" in w.hire_relation(c))
check("...nothing in the rules sends them away", not hasattr(rules, "quitters") and "leave_at" not in rules.P["bond"])


# ---- f170: weights as written, the told-something check, its margin
m2 = hire(0, 15); m2["detail_weights"] = ["personal", "light", "light", "personal", "light"]
check("a detail's weight is judged from what was written, over its subject's (a regret about a broken plate is light)", gravity.of_detail(m2, 2) == "light")
pd = contracts.PersonaDetails.model_validate({"details": ["a.", "b.", "c.", "d.", "e."], "secrets": [], "weights": ["light", "HEAVY", "personal", "light", "bogus"]})
check("weights the model gets wrong are dropped, and the subjects decide", pd.weights == [])
from engine import relevance as _rel
_seen = []
_pick = _rel.pick
_rel.pick = lambda q, items, k=2, floor=None: (_seen.append(items), [])[1]
w.hire_feeling(bram, "My sister died of the fever last winter.")        # told, not asked: a question is never a loss confided
_rel.pick = _pick
check("'painful' is judged against news of a loss in the player's own life, from the data", _seen and _seen[0] == [quirks.Q["answer_told"]["about"]] and "player's own life" in _seen[0][0])
calls = []
def fake2(table):
    def f(text, others):
        calls.append(others)
        return table[len(calls) - 1][:len(others)]
    embed.whole = f
fake2([[0.8, 0.2], [0.5, 0.3]])
check("a scene line about the very thing the player said (asked about the wound, the wound) is not counted against the answer",
      contracts.answers_first("It is a dull ache.", {"said": "How is the wound?", "scene": ["you are hurt", "it is midday, hot"]}) == "" and calls[1] == ["How is the wound?", "it is midday, hot"], calls)
calls.clear(); fake2([[0.2], [0.50, 0.53]])
check("an opening only a little closer to the scene than to what was said stands (short condolences score unsteadily)",
      contracts.answers_first("I am sorry.", {"said": "My brother was killed.", "scene": ["it is hot"]}) == "")
calls.clear(); fake2([[0.2], [0.3, 0.7]])
check("...one clearly about the scene is sent back", "first words" in contracts.answers_first("The heat is heavy.", {"said": "My brother was killed.", "scene": ["it is hot"]}))
embed.whole = _whole
check("a gesture is asked for as someone watching would put it", "never as they would say it" in quirks.GESTURE_RULE)


# ---- this reply's culture feature belongs to this person at this moment, not to the moment alone
from engine import voice_profile as _vp
a = hire(0, 15); b = hire(1, 15)
a["speech"] = _vp.roll(random.Random(1), "human", "rimelands", "learner"); b["speech"] = _vp.roll(random.Random(2), "dwarf", "ironvein", "fluent")
a["said"] = b["said"] = []
w.culture_now(a)
check("two people at the same minute with nothing said yet do not share one cached roll", w.culture_now(b) == w.culture_now(b) and b.get("_culture_key") != a.get("_culture_key"))
check("the cached roll is play state, reset with a new game", "_culture_key" in rules.TALK and "_culture" in rules.TALK)

check("a gesture with no word in it ('u.') is dropped; a one-word one ('shrugs') is kept",
      quirks.keep_gesture("u.", {"gesture_now": True, "gestures": []}, "Maren Holt") == "" and quirks.keep_gesture("shrugs", {"gesture_now": True, "gestures": []}, "Maren Holt") == "shrugs")

# ---- f172: sayings have a gap; a promotion waiting does not cut into a wound; Maren's objective by meaning
sv = {"name": "Isel Quill", "speech": _vp.roll(random.Random(3), "human", "rimelands", "learner"), "said": []}
sv["speech"]["strength"] = "strong"
got = []
for k in range(400):
    sv["said"].append(f"line {k}")
    kind, _ = _vp.culture_feature(sv, random.Random(k))
    if kind == "saying":
        got.append(len(sv["said"]))
gaps = [b - a for a, b in zip(got, got[1:])]
check("a saying from home, then none until they have said saying_gap more lines", got and all(g >= _vp.S["saying_gap"] for g in gaps), gaps[:10])
from engine import mentor
inj = hire(0, 15); inj.update(capped=True, rank="F", hp_frac=0.3, hp_at=w.minutes)
other = hire(1, 15)
w.player.party_last_fight = None
kinds = [w.banter_hook([inj, other], "rest", random.Random(k))[0] for k in range(400)]
check("with Bram badly hurt at rest, his waiting promotion never takes the talk", "promotion" not in kinds and "hurt" in kinds, collections.Counter(kinds) if "collections" in dir() else set(kinds))
inj.update(hp_frac=1.0)
kinds = [w.banter_hook([inj, other], "rest", random.Random(k))[0] for k in range(400)]
check("...and when nothing presses, it can come up with the small stuff", "promotion" in kinds, set(kinds))
mentor.set_stage(w.player, "board")
f_personal = mentor.facts(w.player, "Parth", "do you have family?")
f_next = mentor.facts(w.player, "Parth", "what should I do next? is there a contract on the guild board?")
f_beat = mentor.facts(w.player, "Parth", "anything", objective=True)
check("asked about her family, Maren is not told she is waiting on the wolf hunt", "waiting for them to take it" not in f_personal and "joined the guild" in f_personal)
check("...asked what to do next, she is", "waiting for them to take it" in f_next)
check("...and in a beat of her own, always", "waiting for them to take it" in f_beat)


# ---- f173: every answer to a re-asked question is exempt; gestures count across speakers; a misspelt given name is mended
from engine import convo
h = {"convo": []}
convo.record(h, "What is your rank?", "I'm an A rank. It took a while.", 1)
convo.record(h, "What is your rank, again?", "I told you already, I'm an A rank.", 2)
e = convo.find(h, "What is your rank?")
said_ = ["I'm an A rank. It took a while.", "The wolves are hungry.", "I told you already, I'm an A rank."]
check("asked a third time, none of the answers already given to it count as 'said lately'", convo.others_lately(said_, e) == ["The wolves are hungry."], convo.others_lately(said_, e))
st_ = quirks.gesture_state({"name": "Isel Quill", "gestured": []}, [{"name": "Bram Voss", "gestured": ["Bram adjusts the strap of the pack"]}])
check("a gesture someone else present just made counts against a new one, without their name", "adjusts the strap of the pack" in st_["gestures"], st_)
check("...so Isel adjusting the same strap is dropped", quirks.keep_gesture("adjusts the strap of the pack", st_, "Isel Quill") == "")
pd = contracts.PersonaDetails.model_validate({"details": ["He grew up in the Rimlands hauling crates.", "b is here.", "c is here.", "d is here.", "e is here."],
                                             "secrets": []}, context={"names": ["Bram", "Voss", "Rimelands"]})
check("'Rimlands' for 'Rimelands' is put right, not refused", pd.details[0] == "He grew up in the Rimelands hauling crates.", pd.details[0])
try:
    contracts.PersonaDetails.model_validate({"details": ["During the Feast of Stone they sang.", "b.", "c.", "d.", "e."], "secrets": []},
                                            context={"names": ["Bram", "Voss", "Rimelands"]})
    check("an invented name that is no misspelling is still refused", False)
except Exception as ex:
    check("an invented name that is no misspelling is still refused", "Feast" in str(ex), str(ex)[:200])


# ---- f174: three companions - all three are there every time; one, two or all of them speak; each has a view of the others and the player
from engine import banter as _bn
t1, t2, t3 = hire(0, 15), hire(1, 15), dict(hire(0, 15), id="g3", name="Tamsin Reed")
for t in (t1, t2, t3):
    t["impression"] = "Thinks the player is green, and honest about it."
w.player.party = [t1, t2, t3]; w.player.party_relations = {}
w.relations_seed()
rel_ = w.relation(t1, t2)
check("every pair's relation keeps what each privately thinks of the other", rel_ and set(rel_.get("views", {})) == {t1["id"], t2["id"]}, rel_)
asks = []
stub.exchange = lambda names, first: (asks.append((list(names), first)), [{"speaker": names[i % len(names)], "text": f"Line {i} about the road ahead, number {chr(97 + i)}."} for i in range(max(len(names), 3))])[1]
DR = _bn.B["banter"]["director"]; keep_d = dict(DR)
DR.update(first=-999, second=-999, third=-999); w.party_banter([t1, t2, t3], "travel")
DR.clear(); DR.update(keep_d)
check("all three can talk together", asks and len(asks[-1][0]) == 3, asks[-1][0] if asks else None)
req3 = asks[-1][1] if asks else ""
check("...each with what they think of the other two, and of the player",
      all(req3.count(f"Of {x}:") >= 2 for x in ("Bram", "Isel", "Tamsin")) and req3.count("Of the player:") >= 3, req3[:2500])
DR.update(second=999, third=999); w.party_banter([t1, t2, t3], "travel")
DR.clear(); DR.update(keep_d)
check("when only one has reason to speak, one does, and the others are named as there and listening", len(asks[-1][0]) == 1 and "listening" in asks[-1][1], asks[-1][0])
stub.exchange = None
from engine import banter as _b2
from llm.contracts import Exchange
ex = Exchange.model_construct(lines=[type("L", (), {"speaker": s_, "text": t_, "gesture": ""})() for s_, t_ in (("Bram Voss", "Right then."), ("Isel Quill", "Yes, indeed."), ("Bram Voss", "Fine by me."))])
check("when three are to speak, a reply where one of them never does is sent back",
      "everyone named" in (_b2.check_exchange(ex, {"speakers": ["Bram Voss", "Isel Quill", "Tamsin Reed"], "lines": (3, 6), "all_speak": True}) or ""))
c3 = w.companion_records(t1)
check("asked about another companion, what they think of them is there to be found", any(r["kind"] == "view" and "Isel" in r["text"] for r in c3))
w.player.party = []

shutil.rmtree("saves/grav", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
