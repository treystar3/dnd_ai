"""How hard a moment hits each companion (engine/severity.py): the same path for a death, a betrayal and something grim found; the level
from how grave it is and what the one it concerns is to them; how it changes the way they speak; what it leaves behind, once; a hire
killed mid-fight is reacted to at once, and the fight is always talked over afterwards. The stub stands in for the model."""
import re, collections, random, shutil, sys, types
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
from engine import party as rules, party_director as director, quirks, severity
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/sev", ignore_errors=True)
st = CampaignStore.open_or_create("sev")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 3000; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/sev/turns.jsonl"

def hire(i, name, temper, role, bond=20):
    m = {"id": f"s{i}", "name": name, "role": role, "level": 3, "rank": "F", "permanent": True, "temper": temper, "motive": "coin",
         "line": "will not take from the poor", "bond": bond, "memories": [], "said": [], "talk": [], "blurb": "a hired hand"}
    quirks.roll(m, random.Random(i))
    m["details"] = []
    m["speech"] = {"tells": {}}
    return m

bram, isel, tam = hire(1, "Bram Voss", ["blunt"], "fighter"), hire(2, "Isel Quill", ["gentle"], "priest"), hire(3, "Tamsin Reed", ["wary"], "ranger")
crew = [bram, isel, tam]
w.player.party = crew; w.player.party_mode = "with"; w.player.party_relations = {}
w.relations_seed()
w.relation(bram, tam)["score"] = 40                     # Bram and Tamsin: close
w.relation(isel, tam)["score"] = -10                    # Isel and Tamsin: grating
w.relation(bram, isel)["score"] = 10

# ---- the table: the same death, felt by what the dead one was to them
death = director.beat_from_event("Tamsin Reed has just been killed in front of them.", "heavy", "s3", "Tamsin Reed's death")
check("a close friend killed: devastated", w.hit_level(bram, death, crew) == "devastated", w.hit_level(bram, death, crew))
check("...someone they could not stand killed: sobered, not devastated", w.hit_level(isel, death, crew) == "sobered", w.hit_level(isel, death, crew))
w.relation(isel, tam)["score"] = 10
check("...someone they know a little: shaken", w.hit_level(isel, death, crew) == "shaken", w.hit_level(isel, death, crew))
w.relation(isel, tam)["score"] = -10

# ---- not only death: the same path for anything grave, by whom it concerns
betrayal = director.beat_from_event("The guild clerk who signed them on has sold the party's route to bandits.", "heavy", None, "the clerk's betrayal")
grim = director.beat_from_event("In the cellar, a family chained to the wall, long dead.", "heavy", None, "what was in the cellar")
check("a betrayal that concerns nobody in particular: shaken, for each of them", all(w.hit_level(m, betrayal, crew) == "shaken" for m in crew),
      [w.hit_level(m, betrayal, crew) for m in crew])
_rel = director.relevant
director.relevant = lambda m_, t_, p_=None, *a, **k: m_["id"] == "s2"
check("...something grim that stands out against one person's own life hits that one hardest", w.hit_level(isel, grim, crew) == "devastated"
      and w.hit_level(bram, grim, crew) == "shaken", (w.hit_level(isel, grim, crew), w.hit_level(bram, grim, crew)))
director.relevant = _rel
light = director.beat_from_event("Bram trips on a root and swears.", "light", "s1", "Bram tripping")
check("a light moment leaves everyone composed, however close", all(w.hit_level(m, light, crew) == "composed" for m in crew))
told = director.beat_from_words("My brother was killed by bandits last winter.", "s1", [], False, "heavy")
isel["bond"] = 40
check("the player's own loss, told and not seen, from someone who trusts them: shaken, a step below seeing it", w.hit_level(isel, told, crew) == "shaken",
      w.hit_level(isel, told, crew))
isel["bond"] = 20

# ---- how it changes the way they speak: each their own level, their own way of breaking
reqs = []
stub.exchange = lambda names_, first: (reqs.append(first), [{"speaker": n, "text": "No. No, no."} for n in names_ if n != "Tamsin Reed"])[1]
SAID.clear()
w.party_moment("Tamsin Reed has just been killed in front of them.", "heavy", "s3", "Tamsin Reed's death", in_fight=True)
txt = reqs[-1] if reqs else ""
check("killed mid-fight: everyone left speaks at once, in one exchange", sorted(w.last_plan.speaker_ids) == ["s1", "s2"], director.explain(w.last_plan, {m["id"]: m["name"] for m in crew}))
check("...Bram is told he is devastated, and how he breaks", re.search(r"This has devastated (them|him|her)", txt) and re.search(r"Right now (they are|he is|she is) devastated", txt), txt[:1500])
check("...Isel only sobered", re.search(r"This has sobered (them|him|her)", txt), txt[:1500])
check("...and in the middle of the fight it is one outburst each", "one short outburst" in txt and "WRITE 1 TO 2 LINES" in txt and "Bram Voss may answer with no words" in txt, txt[-700:])
check("...how Bram breaks is his own, kept on him", bool(bram["speech"]["tells"].get("devastated")), bram["speech"])

# ---- what it leaves behind: a mood that lasts days for the devastated, a memory; once, however often it is talked of
check("Bram is left devastated for days", "devastated by Tamsin Reed's death" in rules.mood_now(bram, w.minutes + 2 * 1440), bram.get("mood"))
check("...and remembers being there", any("I was there for Tamsin Reed's death" in x["text"] for x in bram["memories"]), bram["memories"])
check("...Isel, only sobered, is left with no lasting mood", "Tamsin" not in (isel.get("mood") or ""), isel.get("mood"))
n0 = sum("Tamsin Reed's death" in x["text"] for x in bram["memories"])
w.leave_marks(crew, death)
check("...talked over again afterwards, it is not left twice", sum("Tamsin Reed's death" in x["text"] for x in bram["memories"]) == n0)
rules.set_mood(bram, "pleased about the weather", w.minutes + 60)
check("...and a passing mood does not cut it short", "devastated" in rules.mood_now(bram, w.minutes + 120))
stub.exchange = None

# ---- at a grave moment, the director's pick may react without words, whatever their own level (f186: a sobered Isel was forced to
# speak after "Tamsin." and asked about supplies; the model's Bram-only answer had been right)
check("sobered at a heavy moment: may be silent", severity.may_be_silent("sobered", "heavy") and not severity.may_be_silent("sobered"))
check("...below shaken at anything lighter: must speak", not severity.may_be_silent("sobered", "personal") and not severity.may_be_silent("composed"))
reqs2 = []
stub.exchange = lambda names_, first: (reqs2.append(first), [{"speaker": "Bram Voss", "text": "Tamsin."}])[1]
SAID.clear()
w.player.party = crew = [bram, isel]
w.party_moment("Tamsin Reed was killed in the last fight.", "heavy", "s3", "Tamsin Reed's death")
check("a Bram-only answer to a death is accepted on the first try: Isel is not forced to speak", len(reqs2) == 1 and SAID and
      all(spk == "Bram Voss" for spk, _ in SAID) and "Isel Quill" in reqs2[-1].split("WHO MAY SAY NOTHING", 1)[-1], (len(reqs2), SAID, reqs2[-1][-400:] if reqs2 else ""))
stub.exchange = None
w.player.party = crew = [bram, isel, tam]

# ---- the fight: the moment they go down, whether they are dead is decided, shown, and reacted to
from scenes.combat_scene import CombatScene
fake_fight = types.SimpleNamespace(story=[], fighters=[], felled_by={}, get=lambda fid: types.SimpleNamespace(id=fid, name="Tamsin Reed", alive=False, counters={}) if fid == "ally_s3" else None)
fake = types.SimpleNamespace(fight=fake_fight, ws=w, rng=random.Random(0))
outcomes = collections.Counter()
for k in range(200):
    tam.pop("down_fate", None)
    fake.rng = random.Random(k)
    killed = CombatScene.hires_down(fake)
    outcomes[tam["down_fate"]] += 1
check("a hire who goes down is decided dead or carried there and then (about half die, as party.yaml says)", 60 < outcomes["dead"] < 140, outcomes)
tam["down_fate"] = "dead"; fake_fight.story.clear()
check("...and once decided, it is not decided again", CombatScene.hires_down(fake) == [] and tam["down_fate"] == "dead")
tam.pop("down_fate"); fake.rng = random.Random(next(k for k in range(200) if random.Random(k).random() < rules.P["death_when_down"]))
killed = CombatScene.hires_down(fake)
check("...a death is told to the narrator as it happens", killed == [tam] and any("is dead" in s for s in fake_fight.story), fake_fight.story)
ally = types.SimpleNamespace(id="ally_s3", name="Tamsin Reed", alive=False, hp=0, max_hp=10)
w.player.party = list(crew)
w.party_after_fight([ally], [ally], won=True, hard=True)
check("...and the fight's end keeps the fate decided then: she is gone", tam not in w.player.party and w.player.party_last_fight.get("fallen_ids") == ["s3"],
      (w.player.party_last_fight, [m["name"] for m in w.player.party]))

# ---- afterwards, a fight in which one of them was killed is always talked over, and it is about her
talked = 0
_pb = w.party_banter
w.party_banter = lambda c, kind="travel": True
for k in range(50):
    st.meta.minutes = 9000 + k * 400; w._banter_due = "fight"
    w.player.party_last_fight = dict(w.player.party_last_fight, minute=st.meta.minutes - 5)
    before = getattr(w, "_banter_last", None)
    w.banter_tick()
    talked += getattr(w, "_banter_last", None) == st.meta.minutes
w.party_banter = _pb
check("a fight in which one of them died is always talked over afterwards", talked == 50, talked)
st.meta.minutes = 9000 + 50 * 400
w.player.party_last_fight = dict(w.player.party_last_fight, minute=st.meta.minutes - 5)
w.party_banter(w.player.party, "fight")
p = w.last_plan
check("...the talk afterwards is about her death, heavy, and concerns her", p.beat.weight == "heavy" and p.beat.concerns == "s3" and "Tamsin Reed" in p.beat.text,
      (p.beat.weight, p.beat.concerns, p.beat.text))

# ---- f183: how hard it hit is read before what it leaves behind changes their records
w.player.party = list(crew)
for m in w.player.party:
    m["hit_by"] = []
_rel = director.relevant
director.relevant = lambda m_, t_, p_=None, *a, **k: m_["id"] == "s2" and not any("cellar" in x["text"] for x in m_.get("memories", []))   # as the real check behaves: once all hold the memory, nobody stands out
w.party_moment("They have just forced open a cellar door and found a family chained to the wall, long dead.", "heavy", None, "what was in the cellar")
director.relevant = _rel
check("the report shows how it hit them as it happened (Isel, for whom it stands out, devastated), not after the memory it left",
      (w.last_hits or {}).get("Isel Quill") == "devastated", w.last_hits)

# ---- f183: a pair's summary carries who each is, never what they think of anyone else (it was copied onto the new pair)
w.relation(bram, isel)["views"] = {"s1": "thinks Isel fusses over everyone", "s2": "thinks Bram drinks too much"}
full = w.companion_core(bram)
lean = w.companion_core(bram, without=("view",))
check("everything about Bram includes what he thinks of Isel", "fusses over everyone" in full, full[-400:])
check("...but the summary a new pair is written from leaves it out", "fusses over everyone" not in lean and len(lean) > 40, lean[-300:])

# ---- f187: someone this moment has devastated may say the name again: the repetition guard stands down for them
w.player.party = list(crew)
for m in crew:
    m["hit_by"] = []
w.relation(bram, tam)["score"] = 40
bram["said"] = ["Tamsin."]
calls = {"n": 0}
def _ex(names_, first):
    calls["n"] += 1
    return [{"speaker": n, "text": "Tamsin." if n == "Bram Voss" else "She is gone, and there was nothing any of us could have done about it."} for n in names_ if n != "Tamsin Reed"]
stub.exchange = _ex
w.party_moment("Tamsin Reed has just been killed in front of them.", "heavy", "s3", "Tamsin Reed's death II")
check("devastated, Bram may say 'Tamsin.' again: no line refused for repeating it", calls["n"] == 1, calls)
calls["n"] = 0
isel["said"] = ["She is gone, and there was nothing any of us could have done about it."]
w.relation(isel, tam)["score"] = -10
w.party_moment("Tamsin Reed has just been killed in front of them.", "heavy", "s3", "Tamsin Reed's death III")
check("...but Isel, only sobered, is still held to saying something new", calls["n"] >= 2, calls)
stub.exchange = None

# ---- f187: the player's heavy words are not a shared moment: those who know them answer, by how well; and only those named are 'about'
from engine import party_director as director
for bond, want in ((5, False), (20, True), (40, True)):
    isel["bond"] = bond
    p = director.plan(director.beat_from_words("My brother was killed by bandits last winter.", "s1", [], False, "heavy"), [isel], random.Random(1), must_start=False)
    check(f"heavy words, Isel trusts the player {bond}: {'answers' if want else 'lets it be'}", (p.speaker_ids == ["s2"]) == want, director.explain(p, {"s2": "Isel"}))
    if want:
        check("...and the reason is that the player opened up, not that it is a moment everyone has a say in",
              any("opened up" in w_ for _, w_ in p.reactions[0].reasons) and not any("everyone has a say" in w_ for _, w_ in p.reactions[0].reasons), p.reactions[0].reasons)
isel["bond"] = 20
stub.overheard = lambda u: {"about": ["Isel Quill"], "party": False, "weight": "heavy"}
ids, party, weight = director.read_words("My brother was killed by bandits last winter.", "Bram Voss", "I am sorry.", [isel, tam])
check("the read names Isel, but the player's words never do: she is not who they are about", ids == [], ids)
ids, _, _ = director.read_words("Isel, you knew him too.", "Bram Voss", "", [isel, tam])
check("...when the words name her, she is", ids == ["s2"], ids)
stub.overheard = None

# ---- f187: a level says what it may not become: shaken or devastated, nobody shrugs it off
check("every level above composed rules out dismissing the moment", "takes it seriously" in severity.register("sobered").replace("they take", "takes")
      and "never dismisses" in severity.register("shaken") and "never anything that shrugs it off" in severity.register("devastated"),
      [severity.register(l) for l in ("sobered", "shaken", "devastated")])

shutil.rmtree("saves/sev", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
