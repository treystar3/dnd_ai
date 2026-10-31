"""Quirks: every hire rolls them; habits show at their moment; deeds draw a reaction once a day; flaws cost something and are seen; an errand
is asked once trust is there and answered by the next line; secrets come with trust; the voice pattern is checked; Maren lets things slip."""
import sys, random, shutil, re
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
import config
import ui.console as uc
SAID, NARR, NOTES = [], [], []
uc.say = lambda t, s="": SAID.append((s, t))
uc.dialogue = lambda b, s, t, a: SAID.append((s, t))          # (f325) a companion's framed words count as said under their name
uc.narrate = lambda t: NARR.append(t)
uc.note = lambda m, *a, **k: NOTES.append(m)
from engine import quirks, mentor
from engine import party as rules
from llm.contracts import CompanionReply
from pydantic import ValidationError
from scenes.world import WorldScene
from storage.campaign import CampaignStore, PlayerState
from npc.traits import load_traits
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/qk", ignore_errors=True)
st = CampaignStore.open_or_create("qk")
st.meta.seed = 5; st.meta.turn = 1; st.meta.minutes = 1800; st.save_meta()
ch, _ = simlib.make_character("warrior", random.Random(2))
st.save_player(PlayerState(character=ch, location="parth"))
w = WorldScene(st, load_world(), load_traits(), st.load_player())
config.TURN_LOG_PATH = "saves/qk/turns.jsonl"

def hire(i, temper, motive):
    m = {"id": f"h{i}", "name": ["Bram Voss", "Isel Quill", "Tavi Fell"][i], "role": ["fighter", "priest", "rogue"][i], "level": 3, "rank": "F", "permanent": True,
         "temper": temper, "motive": motive, "line": "will not take from the poor", "bond": 15, "memories": [], "said": [], "talk": [], "blurb": "a scarred sellsword"}
    quirks.roll(m, random.Random(i))
    return m

# the roll
ms = [hire(i, t, mo) for i, (t, mo) in enumerate([(["blunt", "dry"], "protect"), (["gentle", "devout"], "coin"), (["wary"], "wander")])]
check("every hire has a habit, a voice, a like and a dislike that differ", all(m["quirks"]["habit"] and m["quirks"]["voice"] and m["quirks"]["likes"] != m["quirks"]["dislikes"] for m in ms))
check("the roll is kept", (quirks.roll(ms[0], random.Random(99)), ms[0]["quirks"]["habit"] == hire(0, ["blunt"], "protect")["quirks"]["habit"])[1])
ms[0]["quirks"]["voice"] = "no_contractions"             # (f375) a voice with words to it: the draw no longer lands on one_sentence
check("the core carries the voice, habit and leanings, and growth only once trusted", "In speech" in quirks.core_lines(ms[0]) and "A habit" in quirks.core_lines(ms[0]) and "Approves of" in quirks.core_lines(ms[0]) and "changed" not in quirks.core_lines(ms[0]))
ms[0]["bond"] = 40
check("growth appears at trusted, by temperament", "changed" in quirks.core_lines(ms[0]) and quirks.growth(ms[0]) == quirks.Q["growth"]["trusted"]["blunt"])
ms[0]["bond"] = 15

# habits at their moment
w.player.party = ms[:2]; w.player.party_mode = "with"
for m in ms[:2]:
    m["quirks"]["habit"] = "first_watch" if m is ms[0] else "counts_fights"
got = w.habit_lines("rest")                              # (f412) handed to the rest's passage, never a line of their own
check("a rest habit shows at a rest, the first time for certain", any("first watch" in t for t in got), got)
check("...and not at another moment", not w.habit_lines("arrival"))
ms[1]["fights_total"] = 7
got = w.habit_lines("fight_end")
check("a fight-count habit says the real count", any("7" in t and "Isel" in t for t in got), got)

# deeds and reactions
ms[0]["quirks"]["likes"], ms[0]["quirks"]["dislikes"] = "harvest", "flee"
ms[1]["quirks"]["likes"], ms[1]["quirks"]["dislikes"] = "shrine", "harvest"
b0, b1 = ms[0]["bond"], ms[1]["bond"]
SAID.clear(); w.deed("harvest")
check("one approves and one does not, each in a line under their name, and bond moves both ways", {s for s, _ in SAID} == {"Bram Voss", "Isel Quill"} and ms[0]["bond"] == b0 + 2 and ms[1]["bond"] == b1 - 2, (SAID, ms[0]["bond"], ms[1]["bond"]))
check("the deed is remembered, in their own words", any("skin and butcher" in x["text"] for x in ms[0]["memories"]))
SAID.clear(); w.deed("harvest")
check("not twice in a day", not SAID)
SAID.clear(); w.deed("bribe")
check("a deed nobody minds passes in silence", not SAID)

# flaws
ms[0]["quirks"]["flaw"] = "pocket"
got = []
for k in range(60):
    st.meta.minutes = 1800 + k * 7
    got.append(w.flaws_on_loot(200))
check("light fingers skim some takes and not others, and the skim is 10 to 20 percent", any(g < 200 for g in got) and all(160 <= g <= 200 for g in got), sorted(set(got)))
check("a caught skim or a quiet one is remembered either way", any("take" in x["text"] for x in ms[0]["memories"]))
st.meta.minutes = 1800
ms[0]["quirks"]["flaw"] = "drinker"
f0 = rules.fighter(ms[0], minutes=w.minutes).weapon_damage
ms[0]["hungover_until"] = w.minutes + 100
check("a hangover blunts the blade", rules.fighter(ms[0], minutes=w.minutes).weapon_damage < f0 and rules.fighter(ms[0], minutes=w.minutes + 200).weapon_damage == f0)
ms[0]["hungover_until"] = -1
ms[0]["quirks"]["flaw"] = "fair_weather"
f = rules.fighter(ms[0], minutes=w.minutes)
check("a fair-weather flaw rides on the fighter", f.flaw == "fair_weather" and not f.flaw_used)

# the voice pattern is checked
ms[0]["quirks"]["voice"] = "no_contractions"
def ok_reply(speech, m, player="Ironbound Vanguard", must=()):
    try:
        CompanionReply.model_validate({"speech": speech}, context={"member": m, "player": player, "recent": [], "must": list(must)}); return True
    except ValidationError:
        return False
check("no contractions means no contractions", not ok_reply("I don't think so.", ms[0]) and ok_reply("I do not think so.", ms[0]))
ms[0]["quirks"]["voice"] = "nickname"; ms[0]["quirks"]["nick"] = "Boots"
check("a nicknamer never uses the player's name", not ok_reply("Ironbound, come here.", ms[0]) and ok_reply("Boots, come here.", ms[0]))
check("a must word must survive", not ok_reply("Something else entirely.", ms[0], must=["forgive"]) and ok_reply("I do not forgive easily.", ms[0], must=["forgive"]))
check("a gesture may stand alone", CompanionReply.model_validate({"speech": "", "gesture": "shrugs"}, context={}).gesture == "shrugs")

# the voices added and removed
old = {"name": "Ragna Holloway", "quirks": {"voice": "third_person", "habit": "hums"}}
quirks.roll(old, random.Random(3))
check("a voice no longer in the data is rolled again, the rest kept", old["quirks"]["voice"] in quirks.Q["voices"] and old["quirks"]["habit"] == "hums")
t = {"name": "Ragna Holloway", "quirks": {"voice": "second_tongue", "tongue": "rime"}}
check("a second tongue gives its home and habits to the prompt, and no words of its own to copy", "Rimelands" in quirks.voice_prompt(t) and "'vesh'" not in quirks.voice_prompt(t) and "cold hearth" not in quirks.voice_prompt(t))
from engine import voice_profile as _vp
t2 = dict(t, quirks=dict(t["quirks"])); _vp.ensure(t2, random.Random(1))
_offers = []
for k in range(1500):
    t2["speech"]["word_at"] = None
    _offers += quirks.material(t2, random.Random(k), [], feature=_vp.culture_feature(t2, random.Random(k)))
check("...once it has a speech profile, its sayings are offered through the culture budget, and no home word while those are off", not any("'vesh'" in x or "'hrimma'" in x or "'skal'" in x or "'tor'" in x for x in _offers) and any("saying from home" in x for x in _offers))
check("...and not a word they used just now", all(_vp.culture_feature(dict(t2, said=["Sit down, vesh, before you fall."], speech=dict(t2["speech"], word_at=None)), random.Random(k)) != ("word", ("vesh", quirks.Q["tongues"]["rime"]["words"]["vesh"])) for k in range(300)))
check("...uses only its own words, and only a couple at a time", ok_reply("Skal, vesh. Cold, this place.", t) and not ok_reply("Aziri, is cold.", t) and not ok_reply("Skal, vesh, tor, hrimma.", t))
cu = {"name": "Bram Voss", "quirks": {"voice": "curses", "curses": ["ashes and rot", "gutless tick", "damn", "shit"]}}
config.PROFANITY = "mild"
check("at mild, the strong curse is not his to use and is refused", quirks.my_curses(cu) == ["ashes and rot", "gutless tick", "damn"] and not ok_reply("Shit, that hurt.", cu) and ok_reply("Damn, that hurt.", cu))
config.PROFANITY = "off"
check("at off, only the world's curses", quirks.my_curses(cu) == ["ashes and rot", "gutless tick"] and not ok_reply("Damn it.", cu))
config.PROFANITY = "strong"
check("at strong, all of his", "shit" in quirks.my_curses(cu) and ok_reply("Shit, that hurt.", cu))
config.PROFANITY = "mild"
def ok_r(speech, m, recent):
    try:
        CompanionReply.model_validate({"speech": speech}, context={"member": m, "player": "X", "recent": recent}); return True
    except ValidationError:
        return False
check("not in two breaths running", not ok_r("Damn, again.", cu, ["Ashes and rot, my ribs."]) and ok_r("Damn, again.", cu, ["My ribs.", "Fine."]))
check("a secret keeps its rarest words", quirks.must_words("I have a sister back home who thinks I guard caravans.") == ["caravans", "sister"])

# gestures
check("a repeated or wordy gesture is dropped, the words kept",
      quirks.keep_gesture("rolls his shoulder slowly", {"gestures": ["rolls his shoulder"], "gesture_now": True}) == "" and
      quirks.keep_gesture('says "no"', {"gestures": [], "gesture_now": True}) == "" and quirks.keep_gesture("rolls his shoulder", {"gestures": [], "gesture_now": True}) == "rolls his shoulder")
check("a gesture too soon after the last is dropped", quirks.keep_gesture("rubs his jaw", {"gestures": [], "gesture_now": False}) == "")
h = {}
quirks.note_line(h, "rubs his jaw")
check("after a gesture, the next few lines carry none", not quirks.gesture_state(h)["gesture_now"])
for _ in range(quirks.GESTURE_GAP):
    quirks.note_line(h, "")
check("...and then one may come again", quirks.gesture_state(h)["gesture_now"] and "rubs his jaw" in quirks.leaned_on(h))
check("a gesture is shown before the speech, under their name", quirks.shown("Fine.", "rolls his shoulder", "Bram Voss") == "(Bram rolls his shoulder.)\nFine.")
check("a capitalised verb is not taken for a name", quirks.shown("North.", "Looks toward the sun", "Isel Quill") == "(Isel looks toward the sun.)\nNorth.")
check("a pronoun is", quirks.shown("Fine.", "He leans on the wall.", "Bram Voss") == "(Bram leans on the wall.)\nFine.")
check("the gesture rule is the one given", "Never invent furniture, walls, weather, scenery, or held objects" in quirks.GESTURE_RULE)

# one speaker's words in another's mouth
br = {"name": "Bram Voss", "quirks": {"voice": "curses", "curses": ["ashes and rot", "gutless tick"]}}
iq = {"name": "Isel Quill", "quirks": {"voice": "second_tongue", "tongue": "rime"}}
check("Isel using Bram's curse is caught", quirks.borrowed(iq, "Ashes and rot, my shoulders.", [br]) != "")
check("an oath left over from a voice they no longer have is not theirs", quirks.markers({"name": "X", "quirks": {"voice": "plain", "oath": "old Harl's teeth"}}) == set())
check("their own words are theirs", quirks.borrowed(br, "Ashes and rot.", [iq]) == "")

# repeats follow the temperament; voices are told before, not refused after
check("a blunt one is plain about a repeat, never harsh (f422); a gentle one never unkind", "plainly" in quirks.repeat_manner({"temper": ["blunt"]})
      and "harsh" not in quirks.repeat_manner({"temper": ["blunt"]}) and "never" in quirks.repeat_manner({"temper": ["gentle"]}))
br2 = {"name": "Bram Voss", "quirks": {"voice": "curses", "curses": ["ashes and rot", "damn"]}, "said": ["Ashes and rot, that hurts."]}
check("the request says he has just cursed, and lists nobody's words (a list is a list the model reaches into)", "Only Bram uses" not in quirks.voice_notes(br2) and "ashes" not in quirks.voice_notes(br2) and "cursed only just now" in quirks.voice_notes(br2))
br2["said"] = ["Fine.", "Let us go."]
check("...and does not say it when he has not", "cursed only just now" not in quirks.voice_notes(br2))
from scenes import party_prompts as _pp
check("every companion is told to answer the conversation first", "Answer the conversation first" in _pp.TALK_SYSTEM)
check("the real promotion rule says there is no other procedure", "invent no" in quirks.Q["promotion_fact"] and "no list" in quirks.Q["promotion_fact"])

# memories: first person, merged by meaning, deeds folded
mm = {"name": "Bram Voss", "memories": []}
for t in ("They asked why I became a sellsword.", "They asked why I became a sellsword, and listened.", "They asked me why I became a sellsword and listened to my answer."):
    rules.remember(mm, 1, t, 2)
check("the same memory three ways is one memory, counted", len(mm["memories"]) == 1 and mm["memories"][0]["count"] == 3, mm["memories"])
ff = {"name": "Bram Voss", "memories": []}
for _ in range(4):
    rules.remember(ff, 1, "They told me their brother was killed by bandits.", 2, kind="fact")
check("a fact told again is still one fact, never counted", len(ff["memories"]) == 1 and ff["memories"][0]["count"] == 1 and "more than once" not in " ".join(rules.pick_memories(ff)))
mm["quirks"] = {"likes": "harvest", "dislikes": "flee", "reacted": {}}
for d in (1, 2, 3):
    quirks.react(mm, "flee", "disapprove", d)
fl = [x for x in mm["memories"] if x.get("key") == "deed:flee"]
check("repeated deeds fold into one first-person memory that counts", len(fl) == 1 and "3 times" in fl[0]["text"] and fl[0]["text"].startswith("I have seen them run from a fight"), fl)
check("no third-person 'the player was seen' memories", not any("the player was seen" in x["text"].lower() for x in mm["memories"]))

from engine import banter as _b
check("asking the same thing again lifts the repetition guard", _b.asked_again("What is your rank?", ["what's your rank again?"]) and not _b.asked_again("Do you have family?", ["What is your rank?"]))
check("the guard wants five words in common, not four", _b.repeats("Keep your blade close tonight.", ["Keep your blade clean, always."]) == "" and _b.repeats("Keep your hand on your hilt.", ["Keep your hand on your blade."]) != "")

# errands: asked once trusted, at the right place, answered by the next line
ms[0]["bond"] = 35; ms[0]["quirks"]["errand"] = ""
w._errand = None
check("an untrusting hire asks nothing", quirks.errand(ms[1]) is None and quirks.errand(ms[0]) is not None)
w.player.location = "guild_house"
SAID.clear(); NOTES.clear(); w.errands()
check("at a guild hall the protector asks for an hour to send coin home", SAID and SAID[-1][0] == "Bram Voss" and "coin home" in SAID[-1][1] and w._errand, SAID)
b0 = ms[0]["bond"]; m0 = w.minutes
check("yes is taken as yes: the hour passes, bond rises, it is remembered", w.errand_intercept("yes, take your time") and ms[0]["bond"] == b0 + 3 and w.minutes >= m0 + 60 and any("send coin home" in x["text"] for x in ms[0]["memories"]), (ms[0]["bond"], w.minutes - m0))
check("it is not asked again", ms[0]["quirks"]["errand"] == "yes" and quirks.errand(ms[0]) is None)
ms[1]["bond"] = 35; ms[1]["quirks"]["errand"] = ""; w.player.party = [ms[1]]
w.player.character.coins = 1000
SAID.clear(); w.errands()
check("the coin-hungry one asks for an advance anywhere safe", SAID and "advance" in SAID[-1][1], SAID)
c0 = w.player.character.coins; b1 = ms[1]["bond"]
check("no is remembered and costs a little trust", w.errand_intercept("no, not now") and ms[1]["bond"] == b1 - 1 and w.player.character.coins == c0 and any("refused" in x["text"] for x in ms[1]["memories"]))
check("a line that is neither leaves it standing for today", (setattr(w, "_errand", (ms[1], quirks.Q["errands"]["coin"])), not w.errand_intercept("look around"))[1])
w._errand = None
w.player.location = "parth"

# secrets with trust
ms[1]["bond"] = 35; ms[1]["quirks"]["told"] = 0
w.player.party = [ms[1]]
SAID.clear(); w.secrets()
_own = ms[1].get("secrets") or quirks.Q["secret_fallback"][ms[1]["motive"]]
check("at trusted, the first secret is told (their own, written when they were hired)", SAID and SAID[-1][0] == "Isel Quill" and _own[0][:20] in SAID[-1][1] and ms[1]["quirks"]["told"] == 1, SAID)
SAID.clear(); w.secrets()
check("the second waits for devoted", not SAID)
ms[1]["bond"] = 70
SAID.clear(); w.secrets()
check("...and comes at devoted", SAID and _own[1][:20] in SAID[-1][1] and ms[1]["quirks"]["told"] == 2, SAID)
check("a secret told is a heavy memory", any(x["weight"] == 3 and "nobody" in x["text"] for x in ms[1]["memories"]))

# Maren: her rest habits, what you told her comes back, and the things she lets slip
w.player.party = []
mentor.set_stage(w.player, "hunt")
w.player.mentor["chat"] = [["Player", "I woke up in a field with no memory of how I got there"], ["Maren", "Hm."]]
check("what the player told her is on her sheet", "no memory of how I got there" in mentor.facts(w.player, "Greywood"))
check("no beat makes her let something slip unasked (f289)", all(w.mentor_opening(b) == ("", "", []) for b in ("wolves", "troll", "return")))
check("...the truths are hers to tell when asked", "brother" in mentor.facts(w.player, "Greywood", "Do you have family back home? A brother or sister?"),
      mentor.facts(w.player, "Greywood", "Do you have family back home? A brother or sister?")[-400:])
NARR.clear()
w.mentor_with_you = lambda: True
fussed = 0
for k in range(30):
    st.meta.minutes = 1800 + k * 13
    w._habits_due = {}
    w.mentor_rest_habit()
    fussed += len(w.habits_due("rest"))
check("at rests she fusses, now and then, in a visible way", 3 < fussed < 30, fussed)
check("(f413) ...handed to the rest's passage, never a line of its own", not NARR, NARR)

# the whole-loop hooks exist
import scenes.world as _w
src = open(_w.__file__, encoding="utf-8").read()
check("the world loop runs the quirk tick and the errand answer", "self.quirk_tick()" in src and any(i.method == "errand_intercept" for i in _w.WorldScene.INTERCEPT_TABLE) and "self.rest_quirks(sleeping)" in src)
src2 = open("scenes/combat_scene.py", encoding="utf-8").read()
check("fights show habits at start and publish the deeds at the end", 'ws.habits("fight_start")' in src2 and "LootedDead(" in src2 and "Fled(" in src2 and "flaws_on_loot" in src2)

# how they speak, what they feel, what is relevant, and their own small details
import config as _cfg
bp = quirks.blueprint({"temper": ["blunt", "dry"], "quirks": {"voice": "figures"}})
check("a blueprint is behaviour: two lines from the first temperament, one from the second", len(bp) == 3 and bp[0].startswith("Answers"), bp)
_seen = {l for k in range(30) for l in quirks.blueprint({"temper": ["blunt", "dry"], "quirks": {"voice": "figures"}}, random.Random(k))}
check("...and which of them appear changes from reply to reply", len(_seen) > 3, _seen)
check("...and a line the voice quirk contradicts is dropped", not any("metaphor" in b or "plain everyday words" in b for b in bp), bp)
check("subtext follows the situation and temperament", "hates being seen hurt" in quirks.subtext({"temper": ["proud"]}, "hurt_self") and quirks.subtext({"temper": ["gentle"]}, "nothing") == "")
check("the style rules carry the facts-and-colour split", "Free to invent" in quirks.style_block() and "Never invent" in quirks.style_block())
from engine import relevance
check("relevance keeps what bears on the moment and drops the rest", relevance.pick("how is your wound healing", ["Privately, wants to earn the next guild rank.", "A scar on his ribs from a wolf, still healing."], 2) == ["A scar on his ribs from a wolf, still healing."])
check("dialogue runs on Google's suggested Gemma settings; summaries run colder", _cfg.SAMPLING["hire_chat"]["temperature"] == 1.0 and _cfg.SAMPLING["hire_chat"]["top_k"] == 64 and _cfg.SAMPLING["pair_dynamic"]["temperature"] == 0.5)
w.player.party = [ms[0]]
ms[0].pop("details", None)
w.quirked(ms[0])
check("a hire gets their own small details once", len(ms[0]["details"]) == 5)
n0 = stub.calls.get("PersonaDetails", 0)
w.quirked(ms[0])
check("...and only once", stub.calls.get("PersonaDetails", 0) == n0)
core_q = w.companion_core(ms[0], "tell me about where you grew up")
check("asked about home, the core brings the detail about home and not the rest", "fishing village" in core_q and "Privately" not in core_q, core_q)
check("the full core, for writing about them, has everything", "Privately" in w.companion_core(ms[0]) or not ms[0].get("motive"))
ms[0]["capped"] = True; ms[0]["rank"] = "F"
check("a waiting promotion is not in the moment unless the moment is about it", "rank allows" not in w.companion_core(ms[0], "how was the road?") and "rank allows" in w.companion_core(ms[0], "what about your rank in the guild?"))
check("hurt is said in words, never a percent", all("percent" not in x for x in w.hire_now(dict(ms[0], hp_frac=0.3, hp_at=w.minutes), "")))

from engine import party as _party
_odd = sorted({k for _m in ms for k in _party.unclassified(_m)})
check("every field on a hire is classified in engine/party.py", not _odd, _odd)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")

import sys as _sys
_sys.exit(1 if bad else 0)
