"""Who of the companions speaks, and whom each answers (engine/party_director.py): synthetic moments, no model needed for the plans; the
deed path checked end to end with the stub (one exchange for two speakers, everyone with a view affected, silent ones remember keeping
quiet)."""
import collections, random, shutil, sys
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
from engine import banter, party_director as director, quirks
from engine import party as rules
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/dir", ignore_errors=True)
st = CampaignStore.open_or_create("dir")
st.meta.seed = 9; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/dir/turns.jsonl"

def hire(i, name, temper, role):
    m = {"id": f"d{i}", "name": name, "role": role, "level": 3, "rank": "F", "permanent": True, "temper": temper, "motive": "coin",
         "line": "will not take from the poor", "bond": 20, "memories": [], "said": [], "talk": [], "blurb": "a hired hand"}
    quirks.roll(m, random.Random(i))
    m["details"] = []
    return m

bram, isel, tam = hire(1, "Bram Voss", ["blunt", "dry"], "fighter"), hire(2, "Isel Quill", ["gentle", "devout"], "priest"), hire(3, "Tamsin Reed", ["wary", "cheerful"], "ranger")
crew = [bram, isel, tam]
names = {m["id"]: m["name"] for m in crew}
D = banter.B["banter"]["director"]

# ---- deeds
p = director.plan(director.beat_from_deed("skinning and butchering what they kill", {"d1": "approve", "d2": "disapprove"}), crew, random.Random(1), must_start=False)
check("two who see a deed differently both speak; the one with no view is silent", sorted(p.speaker_ids) == ["d1", "d2"], director.explain(p, names))
t2 = p.turns[1]
check("...and the second answers the first, seeing it the other way", t2.target == p.turns[0].speaker_id and t2.purpose == "disagree", p.turns)
check("...the first speaks to the player", p.turns[0].target == "player")
p = director.plan(director.beat_from_deed("running from a fight", {"d1": "disapprove", "d2": "disapprove", "d3": "disapprove"}), crew, random.Random(2), must_start=False)
check("all three mind a deed in the same way: the third does not pile on (a third needs more reason)", len(p.speaker_ids) == 2 and p.turns[1].purpose == "agree", director.explain(p, names))
p = director.plan(director.beat_from_deed("sleeping past midday", {}), crew, random.Random(3), must_start=False)
check("nobody with a view: nobody speaks", p.speaker_ids == [])

# ---- grave: someone hurt
p = director.plan(director.Beat("grave", "Bram is badly hurt, moving stiffly", "d1"), crew, random.Random(4))
check("Bram badly hurt: he speaks, and Isel, who looks after people, answers him", p.speaker_ids[:1] == ["d1"] and "d2" in p.speaker_ids
      and any(t.speaker_id == "d2" and t.target == "d1" and t.purpose == "look_after" for t in p.turns), director.explain(p, names))
check("...Tamsin, with no reason, is silent", "d3" not in p.speaker_ids, director.explain(p, names))

# ---- idle: sometimes one, sometimes two, sometimes all three; three the rarest
counts = collections.Counter()
for k in range(400):
    for m in crew:
        m.pop("banter_at", None); m.pop("started_at", None)
    counts[len(director.plan(director.Beat("idle", "the weather turns grey"), crew, random.Random(k)).speaker_ids)] += 1
print("     idle speakers over 400 moments:", dict(sorted(counts.items())))
check("idle talk: one, two and all three each happen", counts[1] and counts[2] and counts[3], counts)
check("...three together is the rarest", counts[3] < counts[2] and counts[3] < counts[1], counts)

# ---- fairness: nobody opens every idle exchange
starts = collections.Counter()
for k in range(60):
    p = director.plan(director.Beat("idle", "the road is quiet"), crew, random.Random(100 + k))
    starts[p.speaker_ids[0]] += 1
    director.spoke(p, {m["id"]: m for m in crew}, 1000 + k)
check("over many idle exchanges, each of the three opens some", len(starts) == 3 and max(starts.values()) < 40, starts)
for m in crew:
    m.pop("banter_at", None); m.pop("started_at", None)

# ---- what one was told is theirs alone
bram["memories"] = [{"day": 1, "text": "They told me their sister keeps bees near the mill.", "weight": 2}]
r_b = director.evaluate(bram, director.Beat("idle", "the bees near the mill"), crew, random.Random(1))
r_i = director.evaluate(isel, director.Beat("idle", "the bees near the mill"), crew, random.Random(1))
check("a moment close to what Bram was told counts for Bram", any("own life" in w_ for _, w_ in r_b.reasons), r_b.reasons)
check("...and never for Isel, who was not told", not any("own life" in w_ for _, w_ in r_i.reasons), r_i.reasons)
bram["memories"] = []

# ---- the plan, put to the line writer; the first speaker is checked
p = director.plan(director.beat_from_deed("skinning and butchering what they kill", {"d1": "approve", "d2": "disapprove"}), crew, random.Random(1), must_start=False)
txt = director.interaction(p, names)
check("the plan is said plainly: who opens, to whom, and whom the next answers", "speaks first, to the player" in txt and "seeing it the other way" in txt, txt)
from llm.contracts import Exchange
ex = Exchange.model_construct(lines=[type("L", (), {"speaker": s_, "text": t_, "gesture": ""})() for s_, t_ in (("Isel Quill", "No, not like that."), ("Bram Voss", "It is food."))])
check("an exchange that does not open with the planned first speaker is sent back",
      "speaks first" in (banter.check_exchange(ex, {"speakers": ["Bram Voss", "Isel Quill"], "lines": (2, 4), "first_speaker": "Bram Voss"}) or ""))

# ---- the deed, end to end: two speakers are one exchange; everyone with a view is affected; the silent remember keeping quiet
w.player.party = crew; w.player.party_mode = "with"; w.player.party_relations = {}
w.relations_seed()
bram["quirks"].update(likes="harvest", dislikes="flee", reacted={}); isel["quirks"].update(likes="spare", dislikes="harvest", reacted={})
tam["quirks"].update(likes="loot_dead", dislikes="harvest", reacted={})
calls = collections.Counter()
reqs_ = []
stub.exchange = lambda names_, first: (calls.update(["exchange"]), reqs_.append(first), [{"speaker": names_[i % len(names_)], "text": ["Leave the hide. It is ruined.", "The meat will still fetch a copper or two."][i]} for i in range(2)])[2]
stub.companion = lambda u: (calls.update(["companion"]), {"speech": "Fine work."})[1]
before = {m["id"]: m["bond"] for m in crew}
SAID.clear(); w.deed("harvest")
plan_ = w.last_plan
check("a deed three have views on: two speak, in one exchange (one model call), not one call each", calls["exchange"] == 1 and calls["companion"] == 0
      and len(plan_.speaker_ids) == 2, (calls, director.explain(plan_, names)))
check("...all three with a view are changed by it, spoken or not", all(m["bond"] != before[m["id"]] for m in crew), {m["name"]: (before[m["id"]], m["bond"]) for m in crew})
silent = [m for m in crew if m["id"] not in plan_.speaker_ids][0]
check("...and the one who kept quiet remembers keeping it to themselves", any("kept that to myself" in x["text"] for x in silent["memories"]), silent["memories"])
check("...the request carries the plan of who opens and whom the other answers", reqs_ and "WHO TAKES THE FLOOR" in reqs_[-1] and "seeing it the other way" in reqs_[-1], reqs_[-1][-800:] if reqs_ else "")
stub.exchange = None; stub.companion = None
w.player.party = []


# ---- f176: the subject opens; a shared fight is everyone's; the topic, not the hook's wording, is what is compared
for k in range(60):
    p = director.plan(director.beat_from_hook("personal", "Something of Tamsin Reed's own is on their mind, and they may bring it up in their own way: a rhyme about crows", tam), crew, random.Random(k))
    if p.speaker_ids[0] != "d3":
        break
check("whatever the others' dice, the one whose topic it is opens it", p.speaker_ids[0] == "d3", director.explain(p, names))
check("...and the beat compares only the topic, not the hook's wording around it", p.beat.text == "a rhyme about crows", p.beat.text)
sizes = collections.Counter(len(director.plan(director.beat_from_hook("lost_fight", "The party came off worse in the last fight.", None), crew, random.Random(k)).speaker_ids) for k in range(200))
check("after a lost fight (no one subject), they were all in it: usually two or more speak", sizes[1] < sizes[2] + sizes[3], sizes)

# ---- f176: seeing the same deed again and again wears in - the reaction gets rarer, and trust moves less, then not at all
from engine import quirks as _q
H = _q.Q["habituation"]
m = hire(9, "Vell Arn", ["blunt"], "fighter"); m["quirks"].update(dislikes="harvest", likes="spare", reacted={}); m["bond"] = 20
deltas = []
for day in range(1, 7):
    b0 = m["bond"]; _q.react(m, "harvest", "disapprove", day, spoke=True); deltas.append(m["bond"] - b0)
check("trust moves less each time they see a deed they mind, then not at all", deltas[0] < deltas[1] <= deltas[2] <= 0 and deltas[-1] == 0, deltas)
check("...so a hire who cannot stand skinning loses only a little trust over it, however long the player keeps doing it", sum(deltas) >= -5, sum(deltas))
m2 = hire(8, "Odd Fell", ["blunt"], "fighter"); m2["quirks"].update(likes="harvest", reacted={}, deeds_seen={"harvest": 0}); rates = []
for seen in (0, 1, 2, 5):
    m2["quirks"]["deeds_seen"]["harvest"] = seen
    rates.append(sum(bool(_q.reaction(m2, "harvest", 99, random.Random(k))) for k in range(400)) / 400)
check("the more often they have reacted to it, the less likely they are to react again (never quite never)", rates[0] == 1.0 and rates[0] > rates[1] > rates[2] > rates[3] > 0, rates)
check("...and once a day at most, as before", _q.reaction(dict(m2, quirks=dict(m2["quirks"], reacted={"harvest": 7})), "harvest", 7) == "")

# ---- f176: an easy win is talked over now and then; a fight that mattered, usually
w.player.party = crew; w.player.party_mode = "with"
for m_ in crew:
    m_["hp_frac"] = 1.0
said_after = {"easy": 0, "hard": 0}
_pb = w.party_banter
w.party_banter = lambda c, kind="travel": said_after.update({key: said_after[key] + 1}) or True
for k in range(200):
    for key, last in (("easy", {"minute": 0, "won": True, "hard": False}), ("hard", {"minute": 0, "won": True, "hard": True})):
        w.player.party_last_fight = last
        st.meta.minutes = 5000 + k * 500; w._banter_due = "fight"; w._banter_last = -10**9
        st.meta.turn += 1                                # (f386) each fight's end is a turn of its own: the party's lines are counted by turn
        w.banter_tick()
w.party_banter = _pb
check("after an easy win the party talks now and then; after a hard fight, usually", said_after["easy"] < 80 and said_after["hard"] > 110, said_after)
w.player.party = []

# ---- f178: someone with something to say goes ahead of someone who only feels like talking
_rel = director.relevant
director.relevant = lambda m_, t_, p_=None, *a, **k: m_["id"] == "d2"
got = collections.Counter()
for k in range(300):
    for m_ in crew:
        m_.pop("banter_at", None); m_.pop("started_at", None)
    p = director.plan(director.Beat("idle", "the bees by the mill"), crew, random.Random(k))
    got["opens"] += p.speaker_ids[0] == "d2"
director.relevant = _rel
check("idle talk close to Isel's own life: she opens every time, whoever else feels chatty", got["opens"] == 300, got)

# ---- f178: the player speaks to one; whether the others join in depends on what was said
others = [isel, tam]
def said(text, named=(), party=False, weight="light", k=1):
    return director.plan(director.beat_from_words(text, "d1", list(named), party, weight), others, random.Random(k), must_start=False)
p = said("Nice boots. New?")
check("small talk to Bram ('nice boots'): nobody else joins in", p.speaker_ids == [], director.explain(p, names))
p = said("Isel patched you up well, didn't she?", named=["d2"])
check("words to Bram about Isel: Isel joins in, Tamsin does not", p.speaker_ids == ["d2"] and p.turns[0].target == "d1" and p.turns[0].purpose == "join",
      director.explain(p, names))
tam["memories"] = [{"day": 1, "text": "I grew up tracking deer through the pine hills above the river.", "weight": 2}]
p = said("Ever track deer through pine hills, up above a river?")
check("words to Bram close to Tamsin's own past: Tamsin joins in, Isel does not", p.speaker_ids == ["d3"], director.explain(p, names))
tam["memories"] = []
p = said("We leave at dawn. Everyone ready?", party=True)
check("words that concern the whole party: everyone else answers too", sorted(p.speaker_ids) == ["d2", "d3"], director.explain(p, names))
p = said("I killed the boy. He was unarmed and I killed him.", weight="heavy")
check("heavy words: everyone has a say", sorted(p.speaker_ids) == ["d2", "d3"], director.explain(p, names))
txt = director.interaction(said("We leave at dawn. Everyone ready?", party=True), names)
check("...and the plan tells the writer they are joining in what was said to Bram", "joins in, answering Bram Voss" in txt, txt)

# ---- f178: how heavy a moment is decides how many have a say: a death is heavy; a lost fight is not
for hk, hook, about_, left in (("fallen", "Tamsin Reed fell in a fight not long ago, and the gap is still there.", None, [bram, isel]),
                               ("carried", "Bram Voss was carried out of the last fight, and is only now back on their feet.", bram, crew)):
    sizes = collections.Counter(len(director.plan(director.beat_from_hook(hk, hook, about_), left, random.Random(k)).speaker_ids) for k in range(100))
    check(f"a heavy moment ({hk}): everyone still there has a say, every time", sizes == {len(left): 100}, sizes)
sizes = collections.Counter(len(director.plan(director.beat_from_hook("lost_fight", "The party came off worse in the last fight.", None), crew, random.Random(k)).speaker_ids) for k in range(100))
check("...a lost fight is not heavy: not always everyone", sizes[3] < 100, sizes)
p = director.plan(director.beat_from_deed("picking up a rock from the road", {}), crew, random.Random(5), must_start=False)
check("an innocuous moment (picking up a rock, nobody has a view): nobody speaks", p.speaker_ids == [], director.explain(p, names))

# ---- f178: end to end - talking to Bram with Isel and Tamsin there
w.player.party = crew; w.player.party_mode = "with"
for m_ in crew:
    m_["hp_frac"] = 1.0; m_.pop("banter_at", None); m_.pop("started_at", None)
calls = collections.Counter()
stub.exchange = lambda names_, first: (calls.update(["exchange"]), [{"speaker": names_[i % len(names_)], "text": f"Ready enough, {chr(97 + i)}."} for i in range(2)])[1]
stub.companion = lambda u: (calls.update(["companion"]), {"speech": "Fine boots, aye."})[1]
stub.overheard = lambda u: (calls.update(["overheard"]), {"about": [], "party": False, "weight": "light"})[1]
w.hire_talk(bram, "Nice boots. New?")
check("talking to Bram about his boots: one read of the words, Bram answers, nobody joins in", calls["overheard"] == 1 and calls["exchange"] == 0
      and calls["companion"] == 1 and w.last_plan.speaker_ids == [], (calls, director.explain(w.last_plan, names)))
calls.clear()
stub.overheard = lambda u: (calls.update(["overheard"]), {"about": [], "party": True, "weight": "light"})[1]
st.meta.turn += 1                                        # (f386) the others join in once a turn: this is the next one
w.hire_talk(bram, "We leave at dawn. Everyone ready?")
check("'we leave at dawn, everyone ready?': Bram answers, then Isel and Tamsin join in, in one exchange", calls["exchange"] == 1
      and sorted(w.last_plan.speaker_ids) == ["d2", "d3"], (calls, director.explain(w.last_plan, names)))
stub.exchange = stub.companion = stub.overheard = None
w.player.party = []

# ---- f180: a moment counts as close to someone's own life only when it stands out from everyone else's
from engine import relevance as _rv
check("a line close to one person's records and not the others': it stands out", _rv.stands_out("the bees by the old mill", ["My sister keeps bees by the mill."], ["I grew up on a fishing boat."], 0.6, 0.04)[0])
check("...a line just as close to everyone's: it does not", not _rv.stands_out("the bees by the old mill", ["My sister keeps bees by the mill."], ["Bees swarmed the mill when I was small."], 0.6, 0.04)[0])
for m_ in crew:
    m_["memories"] = [{"day": 1, "text": "I started travelling with the others and signed on at the guild hall.", "weight": 2}]
r_ = [director.evaluate(m_, director.beat_from_words("Nice boots. New?", "d1", [], False, "light"), [isel, tam], random.Random(1), [bram]) for m_ in (isel, tam)]
check("small talk with nothing in it for anyone: nobody gets 'close to their own life'", not any("own life" in w_ for r in r_ for _, w_ in r.reasons), [x.reasons for x in r_])
for m_ in crew:
    m_["memories"] = []

# ---- f180: the embedding cache never drops a vector a request still needs, however long the game
from llm import embed as _em
class _FakeClient:
    def embed(self, model, input, keep_alive=None):
        return {"embeddings": [[float(len(t)), 1.0] for t in input]}
_saved = (_em.CACHE_SIZE, _em._client, _em.available, dict(_em._cache))
_em.CACHE_SIZE, _em._client, _em.available = 3, (lambda: _FakeClient()), (lambda: True)
_em._cache.clear()
ok_ = True
try:
    _em.vectors(["a", "bb", "ccc"])
    got_ = _em.vectors(["a", "dddd", "eeeee"])                 # "a" is cached; two new ones push the cache past its size
    ok_ = got_ is not None and len(got_) == 3
except KeyError as e:
    ok_ = False
check("a full cache keeps what the request still needs (the f179 KeyError)", ok_)
_em.CACHE_SIZE, _em._client, _em.available = _saved[:3]
_em._cache.clear(); _em._cache.update(_saved[3])

shutil.rmtree("saves/dir", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
