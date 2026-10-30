"""Speech profiles (engine/voice_profile.py, data/rules/speech.yaml): peoples and the cultures that raise them, fluency in Common, how
strongly a culture shows, and how each person shows what they feel - rolled once, compiled a few lines at a time into each reply."""
import sys, random, shutil, re, collections
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
from engine import quirks, voice_profile as vp
from engine import party as rules
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

S = vp.S
check("every people raises its children in cultures that exist", all(c in S["cultures"] for w in S["peoples"].values() for c in w))
check("all ten peoples can be hired", set(S["hire_peoples"]) == {"human", "dwarf", "halfling", "half_elf", "elf", "gnome", "goliath", "orc", "dragonborn", "genasi"})
check("every culture's tongue is defined somewhere", all(not c["tongue"] or c["tongue"] in quirks.Q["tongues"] or c["tongue"] in S["tongues"] for c in S["cultures"].values()))
allwords = [w for t in list(quirks.Q["tongues"].values()) + list(S["tongues"].values()) for w in t["words"]]
check("no word belongs to two tongues", len(allwords) == len(set(allwords)), [w for w, n in collections.Counter(allwords).items() if n > 1])
behaviour = [l for c in S["cultures"].values() for l in c["dialect"]] + [t["habits"] for t in S["tongues"].values()] + \
            [x for opts in S["tells"].values() for x in opts] + [x for opts in S["expression"].values() for x in opts] + [S["fluency"]["baseline"]]
check("dialect, habits, tells and expression are behaviour: no quoted lines to copy", not [l for l in behaviour if re.search(r"['\"]\w", l)],
      [l for l in behaviour if re.search(r"['\"]\w", l)])

# the roll
rng = random.Random(3)
profiles = [vp.roll(rng, "dwarf") for _ in range(400)]
cult = collections.Counter(p["culture"] for p in profiles)
check("a dwarf is mostly raised in Ironvein", cult["ironvein"] / 400 > 0.6, cult)
check("someone raised where Common is the home tongue speaks it natively", all(p["fluency"] == "native" for p in profiles if p["culture"] == "heartland"))
fl = collections.Counter(p["fluency"] for p in profiles if p["culture"] == "ironvein")
check("someone raised with a tongue of their own is mostly fluent, sometimes a learner, sometimes bilingual", fl["fluent"] > fl["learner"] > 0 and fl["native"] > 0, fl)
check("each has one tell for every feeling and one way of each kind of regard, kept", all(set(p["tells"]) == set(S["tells"]) and set(p["expression"]) == set(S["expression"]) for p in profiles[:20]))

# the roster
offers = rules.roster(7, "parth", 3, 5, 10, [])
check("hires on the list have a people and a speech profile", all(o.get("people") and o.get("speech") for o in offers))
many = [o for d in range(0, 400, 7) for o in rules.roster(7, "parth", d, 5, 10, [])]
dw = [o for o in many if o["people"] == "dwarf"]
from npc import names as _names
check("a dwarf on the list has a dwarf's name, built from dwarf sounds", dw and all(len(o["name"].split()) == 2 and (
    _names.acceptable(o["name"].split()[0], _names._rules("dwarf", "male")) or _names.acceptable(o["name"].split()[0], _names._rules("dwarf", "female")))
    for o in dw), [o["name"] for o in dw][:5])
check("humans are the most common, but others turn up", collections.Counter(o["people"] for o in many).most_common(1)[0][0] == "human" and len({o["people"] for o in many}) >= 6)
h = rules.new_hire(offers[0], 5, 3)
check("a new hire keeps their people and profile", h["people"] == offers[0]["people"] and h["speech"]["culture"] == offers[0]["speech"]["culture"])

# old saves
old = {"name": "Isel Quill", "quirks": {"voice": "second_tongue", "tongue": "rime"}}
vp.ensure(old, random.Random(1))
check("an old 'second tongue' hire becomes a Rimelands learner of Common, with a plain voice", old["speech"]["culture"] == "rimelands" and old["speech"]["fluency"] == "learner" and old["quirks"]["voice"] == "plain")
old2 = {"name": "Bram", "quirks": {"voice": "curses"}, "details": ["They grew up by a river."]}
vp.ensure(old2, random.Random(1))
check("an old hire with a past of their own is from the heartland, so nothing written contradicts it", old2["speech"]["culture"] == "heartland" and old2["people"] == "human")
_rolled = [(lambda q: (quirks.roll_voice(q, random.Random(k)), q["voice"])[1])({}) for k in range(1000)]
check("second tongue is never rolled as a voice now", "second_tongue" not in _rolled)
check("about three hires in ten have no marked voice", 0.24 < _rolled.count("plain") / 1000 < 0.37, _rolled.count("plain"))
check("every marked voice still turns up", set(_rolled) >= {v for v, s in quirks.Q["voices"].items() if s.get("weight", 1) > 0})
_cond = {"name": "Ada Fen", "quirks": {"voice": "questions"}}
_seen = [bool(quirks.voice_prompt(_cond, random.Random(k))) for k in range(400)]
check("a conditional voice is in some replies, not all", 0.35 < sum(_seen) / 400 < 0.65, sum(_seen))
check("...and always there when writing about them", quirks.voice_prompt(_cond) != "")
_pers = {"name": "Ada Fen", "quirks": {"voice": "no_contractions"}}
check("a persistent voice is in every reply", all(quirks.voice_prompt(_pers, random.Random(k)) for k in range(50)))

# compiling: a few lines, by the dice
learner = {"name": "Isel", "speech": vp.roll(random.Random(2), "human", "rimelands", "learner")}
learner["speech"]["strength"] = "moderate"
feats = []
for k in range(1000):
    learner["said"] = [f"line {i}" for i in range(k % 40)]       # lines said so far move on, so the gaps can run out
    feats.append(vp.culture_feature(learner, random.Random(k))[0])
shown = sum(1 for f in feats if f) / 1000
check("the culture budget: a moderate culture shows in about two replies in five, never more than one feature", 0.33 < shown < 0.47, shown)
check("...and each feature turns up", {"dialect", "saying"} <= set(feats), collections.Counter(feats))
check("(f410) a learner's accent is not rolled per reply: it is in every reply", "transfer" not in feats and vp.accent(learner)
      and "in every line" in vp.accent(learner), vp.accent(learner))
words = sum(1 for f in feats if f == "word") / 1000
check("home words are off for now: none is offered (speech.yaml culture.weights.word is 0)", words == 0, words)
learner["said"] = []
runs = [vp.compile(learner, random.Random(k), budget=6, feature=vp.culture_feature(learner, random.Random(k))) for k in range(400)]
check("the plain fact of a second language is a fact about them, not one more instruction", not any("second language" in l for r in runs for l in r) and "second language" in vp.who(learner))
check("a reply carries at most one line of their culture", all(sum(1 for l in r if "way of talking" in l or "home shows through" in l or "comparison" in l) <= 1 for r in runs))
offered_words = {f[1][0] for k in range(2000) for f in [vp.culture_feature(dict(learner, said=[], speech=dict(learner["speech"], word_at=None)), random.Random(k))] if f[0] == "word"}
check("...not even with the gap long passed", not offered_words, offered_words)
native = {"name": "Bram", "speech": vp.roll(random.Random(2), "human", "heartland")}
check("a native speaker never gets second-language lines", not any("second language" in l or "home shows" in l for k in range(100) for l in vp.compile(native, random.Random(k), budget=6)))
hurt = vp.compile(native, random.Random(1), emotion="hurting", budget=6)
check("what they feel right now shows their own way", any(l.startswith("Right now they are hurting") and native["speech"]["tells"]["hurting"] in l for l in hurt), hurt)
_warm = [vp.compile(native, random.Random(k), relation="affection", toward="Isel", budget=6) for k in range(400)]
check("warmth toward someone shows their own way", any("Toward Isel" in l and native["speech"]["expression"]["affection"] in l for w_ in _warm for l in w_))
_rate = sum(1 for w_ in _warm if any("Toward Isel" in l for l in w_)) / 400
check("...in some replies only: most replies are just the words", 0.2 < _rate < 0.4, _rate)
_rate_e = sum(1 for k in range(400) if any("Toward Isel" in l for l in vp.compile(native, random.Random(k), emotion="hurting", relation="affection", toward="Isel", budget=6))) / 400
check("...and more often when the moment is charged", _rate_e > _rate + 0.15, (_rate, _rate_e))
_R = dict(vp.S["regard"]); vp.S["regard"].update(show=1, emotional=1)
check("the fact line in every reply says their people and how they speak Common, and not where they were raised", vp.who(learner).startswith("A human; Common is their second language, still being learned") and "Rimelands" not in vp.who(learner), vp.who(learner))
check("...where they were raised is a record, carried when the moment touches it", {"kind": "origin", "text": "Raised in the Rimelands of the far north."} in vp.origin_records(learner), vp.origin_records(learner))
both = vp.compile(learner, random.Random(1), emotion="hurting", relation="affection", toward="Bram", budget=2)
check("with room for two, how they feel and how they are toward the other come first", len(both) == 2 and both[0].startswith("Right now") and both[1].startswith("Toward Bram"), both)
check("with no room, nothing is added", vp.compile(learner, random.Random(1), emotion="hurting", budget=0) == [])
vp.S["regard"].update(_R)

# material by culture
native["quirks"] = {"voice": "plain"}
offers_n = [x for k in range(600) for x in quirks.material(native, random.Random(k), [], feature=vp.culture_feature(native, random.Random(k)))]
check("a heartland native is offered a heartland saying now and then, never a foreign word", any("saying from home" in x for x in offers_n) and not any("home tongue" in x for x in offers_n))
dwarf = {"name": "Brokk", "quirks": {"voice": "plain"}, "speech": vp.roll(random.Random(5), "dwarf", "ironvein", "fluent")}
offers_d = []
for k in range(3000):
    dwarf["speech"]["word_at"] = None
    offers_d += quirks.material(dwarf, random.Random(k), [], feature=vp.culture_feature(dwarf, random.Random(k)))
check("an Ironvein dwarf is offered Ironvein sayings, and no home word while those are off", not any("home tongue" in x for x in offers_d)
      and any("Measure twice" in x or "crack runs" in x or "Stone remembers" in x for x in offers_d))
check("without the culture budget's say-so, no saying or word is offered", not [x for k in range(200) for x in quirks.material(dwarf, random.Random(k), []) if "home" in x])

# who their family were, apart from where
bg = collections.Counter(vp.roll(random.Random(k), "dwarf", "ironvein")["background"] for k in range(1000))
check("an Ironvein dwarf's family were miners in a minority of lives, not most", 0.1 < bg["miner"] / 1000 < 0.4 and bg["merchant"] > 0 and bg["cook"] > 0 and bg["noble"] > 0, bg)
check("a place can rule a trade out (no sailors raised under the mountains)", bg["sailor"] == 0)
check("who their family were is a record too, not in every reply", "Their family were" not in vp.who(dwarf) and any(r["text"].startswith("Their family were") for r in vp.origin_records(dwarf)))
check("an old hire whose life is already written gets no family trade that could contradict it", (lambda o: (vp.ensure(o, random.Random(3)), o["speech"]["background"])[1])({"name": "x", "details": ["They grew up by a river."]}) == "")
check("a word of another tongue is refused for them", "not a word of their tongue" in quirks.voice_check(dwarf, "Hrimma, that was close.", ""))

# in play
shutil.rmtree("saves/vt", ignore_errors=True)
st = CampaignStore.open_or_create("vt")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/vt/turns.jsonl"
m = rules.new_hire(dict(offers[0], temper=["blunt"], motive="coin", line="will not take from the poor"), 5, 1)
m["id"] = "h0"; m["name"] = "Brokk Deephall"; m["people"] = "dwarf"; m["speech"] = vp.roll(random.Random(9), "dwarf", "ironvein", "learner")
w.player.party = [m]; w.player.party_mode = "with"
reqs = []
stub.companion = lambda u: (reqs.append(u), {"speech": "It holds. The stitching is good work."})[1]
m["hp_frac"], m["hp_at"] = 0.3, st.meta.minutes
w.hire_talk(m, "How is the wound?")
check("talking to a hurt dwarf: their people is a fact", "A dwarf;" in reqs[-1] and "Ironvein" not in reqs[-1].split("HOW YOU SPEAK")[0], reqs[-1][:500])
how = reqs[-1].split("HOW YOU SPEAK:")[1].split("\n\n")[0]
from engine import voices as _voices
_k = len(_voices.lines(_voices.kit_of(m)))
check("how they speak holds at most six lines in any one reply, besides the kit", how.count(". ") + 1 <= 9 + _k and len(re.findall(r"(?<=[.;])\s+(?=[A-Z])", how)) + 1 <= 9 + _k, how)
check("...and how they show hurt is in how they speak", m["speech"]["tells"]["hurting"] in reqs[-1].split("HOW YOU SPEAK:")[1].split("\n\n")[0], reqs[-1][-1500:])
check("the details request knows where they come from", "Ironvein" in quirks.details_request(m, w.companion_core(m)))
_dr = quirks.details_request(m)
check("...and is a seed: family and home to draw on, motive and line for consistency only, and no habit, flaw or voice", "INSPIRATION" in _dr and "their family were" in _dr
      and "FOR CONSISTENCY ONLY" in _dr and "A habit" not in _dr and "weakness" not in _dr and "In speech" not in _dr, _dr)
check("...with the two secret themes of their motive, to be written from their own life", "SECRET THEMES" in _dr and quirks.secret_themes(m)[0] in _dr)
quirks.detail_subjects(m, random.Random(4))
dr = quirks.details_request(m, w.companion_core(m), ["They hum when they mend nets."])
check("the details are written to five subjects: their upbringing first, then four rolled from the pool", len(m["detail_kinds"]) == 5 and m["detail_kinds"][0] == quirks.Q["detail_first"]
      and all(k in quirks.Q["detail_kinds"] for k in m["detail_kinds"][1:]) and "SUBJECTS" in dr, m.get("detail_kinds"))
check("...with the party's other details given as already taken", "ALREADY TAKEN BY OTHERS" in dr and "mend nets" in dr)
check("there are fifty subjects to choose from, with the upbringing", len(quirks.Q["detail_kinds"]) + 1 == 50)
kinds = {tuple(quirks.detail_subjects({}, random.Random(k))) for k in range(30)}
check("no two hires are built from the same subjects (mostly)", len(kinds) > 25, len(kinds))
reqs.clear(); stub.companion = lambda u: (reqs.append(u), {"speech": "Under the mountain, among the deep halls of my people."})[1]
w.hire_talk(m, "Where were you raised, and what did your family do?")
check("...and where they were raised comes in when they are asked about it", "Raised in Ironvein" in reqs[0] and "Their family were" in reqs[0], reqs[0][:1500])
m["quirks"]["voice"] = "curses"; m["temper"] = ["blunt", "dry"]
vp.S["regard"].update(show=1, emotional=1)
how_, _ = w.companion_parts(m, "how is the wound?", emotion="hurting", relation="affection", toward="the player")
check("with three personality lines and a voice, only the two most pressing profile lines fit: feeling, then regard",
      re.search(r"Right now (they are|she is|he is) hurting", how_) and "Toward the player" in how_ and "way of talking" not in how_ and "home shows through" not in how_, how_)
vp.S["regard"].update(_R)
m["bond"] = 40
how_g, facts_g = w.companion_parts(m, "how is the wound?", emotion="hurting")
check("how they have changed with the player is in how they speak, counted in the budget, not a fact they recite",
      re.search(r"\b(they have|she has|he has) changed", how_g) and not re.search(r"\b(they have|she has|he has) changed", facts_g), (how_g, facts_g))
check("the screen never shows what drives a hire", "motive" not in w.hire_facts(m))
stub.companion = None
shutil.rmtree("saves/vt", ignore_errors=True)
from engine import party as _party
_odd = sorted({k for _m in [m] for k in _party.unclassified(_m)})
check("every field on a hire is classified in engine/party.py", not _odd, _odd)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
