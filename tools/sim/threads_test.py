"""The engine's own situations (f331, engine/threads.py): every pressure builds a complete situation at every engine tier with no model
call, from a template for its kind with the place's own creatures and people in the parts; the same seed gives the same situation and
different seeds different ones; a hunt contract maps to a real creature; the pulse builds normal and uncommon tiers itself and falls back
to the engine when the model fails a rare one; effects and news carry the thread's id and ending a thread lifts only its own; when the
player comes where it is, one call re-tells only the lines nothing has copied yet; a kind has several shapes and the draw spreads them (f341)."""
import random
import shutil
import sys
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import encounters, events, matters, pulse, quests, threads
from llm import gateway

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

shutil.rmtree("saves/threads_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("threads_test")
store.meta.seed = 11; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(2))
char.level = 4
store.save_player(PlayerState(character=char, location="trading_square"))
ws = WorldScene(store, world, load_traits(), store.load_player())
ws.enter("trading_square"); ws.enter("tilted_plough"); ws.enter("trading_square")
now = ws.minutes
state = pulse.empty_state(now); store.save_world_state(state)

# ---- 1. the templates are sound, and every pressure builds at every engine tier
check("the templates and the pressures that use them check clean", threads.problems({k: v for k, v in world.pressures.items()}, (), set(world.places), set(world.bestiary)) == [])
missing, left, counts = [], [], []
for pid, pr in world.pressures.items():
    place = world.places.get(pr.place) or pulse.region_town(world, pr.place, random.Random(1))
    for tier in ("normal", "uncommon", "rare"):
        out = threads.build(store, world, state, place, pr, tier, random.Random(f"{pid}:{tier}"), now)
        if not out:
            missing.append((pid, tier)); continue
        prop, info = out
        text = " ".join([prop.title, prop.news, prop.truth, prop.reveal, prop.resolution, prop.fallout.description]
                        + [s.description for s in prop.stages] + [c.text for c in prop.clues] + [e.text for s in prop.stages for e in s.effects])
        if "{" in text or "}" in text:
            left.append((pid, tier, text[:80]))
        if len(prop.stages) != pulse.P["tiers"][tier]["stages"] or any(g not in world.knowledge_groups for g in prop.groups):
            counts.append((pid, tier))
check("every pressure builds a situation at normal, uncommon and rare", not missing, missing)
check("...with every slot filled", not left, left[:3])
check("...the tier's number of stages, and known groups", not counts, counts[:3])

# ---- 2. the parts are the place's own
pr = world.pressures["greywood_predators"]
prop, info = threads.build(store, world, state, world.places["greywood"], pr, "uncommon", random.Random(5), now)
ids = info["ids"]
check("a threat at the Greywood casts one of the wood's own creatures", ids.get("creature") in encounters.ensure_roster(store, world, "greywood"), ids.get("creature"))
check("...names Parth as its town and the Greywood as its wild", ids["town"] == "parth" and ids["wild"] == "greywood", ids)
check("...its clue holders are people of the town when there are any", all(store.npc_exists(c.holder) for c in prop.clues) and prop.clues, [c.holder for c in prop.clues])
check("...its kill path is that creature, and its hunt contract maps to a real posting about it",
      any(p.kind == "kill" and p.target == ids["creature"] for p in prop.paths) and prop.contract is not None
      and (quests.map_offer(world, store, prop.contract, "guild", "the guild", now, guild=True) or {}).get("creature") == ids["creature"],
      (prop.paths, prop.contract))
check("...its effects name real places and the severity scales them", all(e.place in world.places or e.place in world.roads for s in prop.stages for e in s.effects if e.place)
      and 0 <= info["severity"] <= 5, info["severity"])
parth = world.places["parth"]
prop2, info2 = threads.build(store, world, state, parth, world.pressures["the_hollow_stirs"], "normal", random.Random(5), now)
check("a mystery at Parth looks to the Greywood, the wildest place at its door, not the fields", info2["ids"]["wild"] == "greywood", info2["ids"])
check("the protected trades are nobody's quarrel", all(c.holder and store.load_npc(c.holder).role not in ("guild_master", "guild_clerk") for c in prop2.clues if store.npc_exists(c.holder)))

# ---- 3. the same seed gives the same situation; different seeds, different ones
a = threads.build(store, world, state, parth, world.pressures["inn_trouble"], "normal", random.Random(9), now)[0]
b = threads.build(store, world, state, parth, world.pressures["inn_trouble"], "normal", random.Random(9), now)[0]
check("the same seed builds the same situation", a.title == b.title and a.news == b.news and a.stages[0].description == b.stages[0].description)
many = {threads.build(store, world, state, parth, world.pressures["inn_trouble"], "normal", random.Random(i), now)[0].stages[0].description for i in range(12)}
check("...and twelve seeds do not all tell it the same way", len(many) >= 3, len(many))

# ---- 4. the pulse builds the ordinary tiers itself, and the thread says so
before = stub.calls.get("ThreadProposal", 0)
state = store.load_world_state()
ok = pulse.start_thread(store, world, ws.catalog, state, now, random.Random(3), tier="normal", pressure_id="greywood_predators")
store.save_world_state(state)
th = state["threads"][-1]
check("a normal situation starts with no model call", ok and stub.calls.get("ThreadProposal", 0) == before)
check("...and the thread record says the engine made it, from which template, how severe, and that it is not yet told",
      th["made_by"] == "engine" and threads.kind_of(th["template"]) == "threat" and "severity" in th and th["told"] is False and th.get("door"), {k: th.get(k) for k in ("made_by", "template", "severity", "told", "door")})
check("...its news carries its id", any(n.get("thread") == th["id"] for n in state["news"]), state["news"][-1])
check("...and so does every lasting effect it laid", all(e.get("thread") == th["id"] for e in state["effects"] if e.get("cause") == th["title"]) and any(e.get("thread") == th["id"] for e in state["effects"]), state["effects"])
ok = pulse.start_thread(store, world, ws.catalog, state, now, random.Random(4), tier="rare", place_id="parth")
check("a rare situation is still the model's", ok and stub.calls.get("ThreadProposal", 0) == before + 1 and state["threads"][-1]["made_by"] == "model")

# the model fails a rare one: the engine builds it; a campaign is not built by the engine
import httpx
class Broken:                                            # the gateway turns a timed-out call into an LLMError after its retries
    def chat(self, **kw):
        raise httpx.TimeoutException("no model")
_client = gateway._client
gateway._client = Broken()
state["cooldowns"] = {}
ok = pulse.start_thread(store, world, ws.catalog, state, now, random.Random(5), tier="rare", place_id="parth")
check("when the model fails a rare situation, the engine builds it", ok and state["threads"][-1]["made_by"] == "engine" and len(state["threads"][-1]["stages"]) == 3, (ok, state["threads"][-1].get("made_by")))
state["campaign"] = ""
ok = pulse.start_thread(store, world, ws.catalog, state, now, random.Random(6), tier="campaign", pressure_id="caravan_trouble")
check("...but a campaign waits for the model", not ok)
gateway._client = _client
store.save_world_state(state)

# ---- 5. a stage copied into the news keeps the id; ending a thread lifts only its own effects
state = store.load_world_state()
t1 = {"id": "x1", "title": "Same name", "tier": "normal", "place": "parth", "kind": "threat", "pressure": "", "stage": 0, "status": "active", "made": now,
      "stages": [{"description": "First.", "effects": []}, {"description": "Second, copied to the news.", "effects": []}], "fallout": {"description": "f", "effects": []},
      "times": [now, now + 600, now + 1200], "groups": ["everyone"], "paths": [], "contract": None, "made_by": "engine", "told": False}
t2 = dict(t1, id="x2", stages=[{"description": "Other.", "effects": []}], times=[now, now + 5000])
state["threads"] = [t1, t2]
state["effects"] = [{"kind": "danger", "place": "greywood", "value": 30, "until": now + 9999, "cause": "Same name", "thread": "x1"},
                    {"kind": "danger", "place": "greywood", "value": 30, "until": now + 9999, "cause": "Same name", "thread": "x2"},
                    {"kind": "prices", "place": "parth", "value": 10, "until": now + 9999, "cause": "Same name"}]
pulse.tick_threads(store, world, ws.catalog, state, now + 700, random.Random(0))
check("a stage the thread advances to is news with the thread's id", t1["stage"] == 1 and any(n.get("thread") == "x1" and "copied" in n["text"] for n in state["news"]))
store.save_world_state(state)
events.finish(ws, state, t1, "by test", "victory")
from engine import pulselog as _plog
check("the player ending a situation is a row of the world log, marked as theirs", any(r["kind"] == "end" and r.get("how") == "player" and r["text"].startswith("Same name - ended by") for r in _plog.LOG), [r for r in _plog.LOG if r["kind"] == "end"][-2:])
lifted = {(e["thread"] if e.get("thread") else "old"): e["until"] <= ws.minutes for e in state["effects"]}
check("ending a thread lifts its own effects by id, and the old ones by title, and leaves another thread's alone", lifted == {"x1": True, "old": True, "x2": False}, lifted)

# ---- 6. the re-telling: only what nothing has copied, once, when the player is there
state = store.load_world_state()
place = world.places["parth"]
prop, info = threads.build(store, world, state, place, world.pressures["seeker_arrives"], "uncommon", random.Random(2), now)
th = {"id": "t1", "title": prop.title, "tier": "uncommon", "place": "parth", "kind": prop.kind, "pressure": "seeker_arrives", "stage": 1, "status": "active", "made": now,
      "stages": [s.model_dump() for s in prop.stages], "fallout": prop.fallout.model_dump(), "times": [now, now + 600, now + 9000], "groups": ["everyone"],
      "paths": [], "contract": None, "made_by": "engine", "told": False, "template": info["template"], "severity": info["severity"], "words": info["words"],
      "truth": prop.truth, "reveal": "", "revealed": False, "resolution": prop.resolution, "door": "word",
      "clues": [{"text": c.text, "holder": c.holder, "npc": c.holder, "found": False} for c in prop.clues]}
first_stage, second_stage, clue0, clue1 = th["stages"][0]["description"], th["stages"][1]["description"], th["clues"][0]["text"], th["clues"][1]["text"]
u = threads.untold(th)
check("once a thread has moved on, its first stage is in the news and stays; the current one is still untold", u["stages"] == [] if len(th["stages"]) == 2 and th["stage"] == 1 else True)
th["stage"] = 0
u = threads.untold(th)
check("while the first stage is current nothing has copied it, so it may be re-told, and so may the later one", u["stages"] == [0, 1])
check("a word door's first clue is in its holder's head and stays; the second may be re-told", u["clues"] == [1], u["clues"])
from llm.contracts import ThreadTelling
_zero = ThreadTelling.model_validate({"stages": ["an extra stage the model wrote anyway"], "clues": ["x"], "truth": "The mill wheel is jammed."},
                                     context={"stages": 0, "clues": 1, "known": []})
check("(f369) a re-telling asked for no stages drops whatever the model writes for them instead of refusing the whole answer", _zero.stages == [] and _zero.clues == ["x"])
try:
    ThreadTelling.model_validate({"stages": ["one"], "clues": []}, context={"stages": 2, "clues": 0})
    check("...while a wrong count where stages were asked for is still refused", False)
except Exception:
    check("...while a wrong count where stages were asked for is still refused", True)
told = threads.tell(store, world, state, th, now)
check("the re-telling rewrites exactly those, in the world's words, and marks the thread told",
      told and th["told"] and th["stages"][0]["description"].startswith("(retold) ") and th["stages"][1]["description"].startswith("(retold) ")
      and th["clues"][0]["text"] == clue0 and th["clues"][1]["text"].startswith("(retold) ") and th["truth"].startswith("(retold) "),
      (th["stages"][0]["description"][:30], th["clues"][1]["text"][:30], th["truth"][:30]))
check("...the title is never re-told", th["title"] == prop.title)
check("...and a told thread is not told again", not threads.tell(store, world, state, th, now + 99999))

th2 = dict(th, id="t2", told=False, told_at=-10**9, stages=[{"description": first_stage, "effects": []}, {"description": second_stage, "effects": []}])
gateway._client = Broken()
told = threads.tell(store, world, state, th2, now)
check("when the model fails, the engine's own lines stand and the thread is not marked told", not told and not th2["told"] and th2["stages"][0]["description"] == first_stage)
gateway._client = _client
check("...and it is not tried again at once", not threads.tell(store, world, state, th2, now + 60) and not th2["told"])
check("...but is, later", threads.tell(store, world, state, th2, now + threads.T["telling"]["retry_hours"] * 60 + 1) and th2["told"])

# on arrival: one untold engine thread of the town is told
th3 = dict(th, id="t3", told=False, told_at=-10**9, stages=[{"description": first_stage, "effects": []}, {"description": second_stage, "effects": []}], door="scene", moment="", summons="")
state["threads"] = [th3]; state["door_log"] = {}
store.save_world_state(state)
ws._narrate_now = lambda event, player_text="": None
ws._door_loc = None
matters.on_arrival(ws)
t3 = next(t for t in store.load_world_state()["threads"] if t["id"] == "t3")
check("when the player is in the town, a situation the engine built there is re-told before any door opens", t3["told"] and t3["stages"][1]["description"].startswith("(retold) "), t3["stages"][1]["description"][:40])

# ---- 8. every ending lifts what the situation laid; the same news twice is one tale told again; a title is not worn twice at a place
state = store.load_world_state()
t9 = {"id": "x9", "title": "Lifted", "tier": "normal", "place": "parth", "kind": "threat", "pressure": "", "stage": 0, "status": "active", "made": now,
      "stages": [{"description": "s", "effects": []}], "fallout": {"description": "f", "effects": [{"kind": "danger", "place": "greywood", "value": 10, "days": 3}]},
      "times": [now, now + 10], "groups": ["everyone"], "paths": [], "contract": None, "made_by": "engine", "told": False, "door": ""}
state["threads"] = [t9]
state["effects"] = [{"kind": "danger", "place": "greywood", "value": 30, "until": now + 99999, "cause": "Lifted", "thread": "x9"}]
state["spawns"] = [{"id": "sp9", "thread": "x9", "place": "greywood", "creature": "wolf", "boss": True, "level": 3, "name": "the wolf", "need": 1, "kills": 0, "defeated": False, "from": now, "until": now + 99999}]
state["camps"] = [{"id": "c9", "thread": "x9", "place": "greywood", "until": now + 99999}]
pulse.tick_threads(store, world, ws.catalog, state, now + 20, random.Random(3))       # past its last stage: settled by others or left alone, either way it ends
check("a situation that ends without the player lifts its own effects, spawns and camps",
      t9["status"] != "active" and state["spawns"][0]["defeated"] and state["camps"][0]["until"] <= now + 20 + 2 * 1440
      and all(e["until"] <= now + 20 for e in state["effects"] if e.get("thread") == "x9" and e["value"] == 30),
      (t9["status"], state["spawns"][0]["defeated"], state["camps"][0]["until"], state["effects"]))
if t9["result"] == "ignored":
    check("...while the fallout it leaves behind stays", any(e["value"] == 10 and e["until"] > now + 20 for e in state["effects"]), state["effects"])
state["news"] = []
for k in range(3):
    pulse.add_news(state, "A traveler spared a captured outlaw.", "parth", now + k * 60, ["outlaws"])
pulse.add_news(state, "A traveler spared a captured outlaw.", "willowmead", now, ["outlaws"])
tales = [n for n in state["news"] if n["text"].startswith("A traveler spared")]
check("the same news from the same place is one tale told again, counted; from another place it is its own",
      len(tales) == 2 and sorted(n.get("times", 1) for n in tales) == [1, 3], [(n["origin"], n.get("times")) for n in tales])
check("...and it is told as such", pulse.news_text(max(tales, key=lambda n: n.get("times", 1))).endswith("That makes three times."), pulse.news_text(tales[0]))
state["threads"] = []
titles = []
for i in range(6):
    prop_i, _ = threads.build(store, world, state, parth, world.pressures["inn_trouble"], "normal", random.Random(100 + i), now)
    titles.append(prop_i.title)
    state["threads"].append({"id": f"tt{i}", "title": prop_i.title, "place": "parth", "status": "active"})
check("six situations of one kind at one town wear six different titles", len(set(titles)) == 6, titles)
words_x = threads.words_for(store, world, parth, world.pressures["inn_trouble"], random.Random(7), now)      # the words build() draws first from the same seed
state["threads"] = [{"id": f"u{i}", "title": threads.fill(l, words_x), "place": "parth", "status": "active"}
                    for i, l in enumerate(l for k in threads.shapes("social") for l in threads.T["templates"][k]["titles"])]
prop_x, _ = threads.build(store, world, state, parth, world.pressures["inn_trouble"], "normal", random.Random(7), now)
check("...and when every title is taken, the next says so", prop_x.title.endswith(" again"), prop_x.title)

# ---- 9. the finished records kept are the ones that ended last: the one ending now stays, however long ago it was made
state = store.load_world_state()
old_big = {"id": "big0", "title": "The oldest matter", "tier": "cataclysm", "place": "parth", "kind": "invasion", "pressure": "", "stage": 5, "status": "active", "made": now - 500 * 1440,
           "stages": [{"description": "s", "effects": []}], "fallout": {"description": "f", "effects": []}, "times": [now - 500 * 1440, now], "groups": ["everyone"], "paths": [], "contract": None, "made_by": "engine", "told": False}
state["threads"] = [old_big] + [{"id": f"fin{i}", "title": f"Small matter {i}", "tier": "normal", "place": "parth", "kind": "social", "pressure": "", "stage": 0, "status": "ended", "made": now - (40 - i) * 1440,
                                 "ended_at": now - (39 - i) * 1440, "stages": [{"description": "s", "effects": []}], "fallout": {"description": "f", "effects": []}, "times": [now, now], "groups": ["everyone"], "paths": [], "contract": None} for i in range(pulse.FINISHED_KEPT + 5)]
pulse.end_thread(store, state, old_big, "ended", "The oldest matter - ran its course.", now)
check("a matter that ends keeps its record though it was the oldest made; the earliest-ended small ones go instead",
      any(x["id"] == "big0" and x["status"] == "ended" for x in state["threads"]) and not any(x["id"] == "fin0" for x in state["threads"]) and len([x for x in state["threads"] if x["status"] != "active"]) == pulse.FINISHED_KEPT,
      ([x["id"] for x in state["threads"]][:4], len(state["threads"])))

# ---- 10. a kind has several shapes (f341): each builds whole at every tier, the draw spreads them, a pressure's own template still wins
state = pulse.empty_state(now)
check("every kind has at least two shapes, the base one first", all(len(threads.shapes(k)) >= 2 and threads.shapes(k)[0] == k for k in threads.T["kind_weights"]),
      {k: threads.shapes(k) for k in threads.T["kind_weights"]})
sample = {"threat": "greywood_predators", "nature": "willowmead_floods", "mystery": "the_hollow_stirs", "social": "inn_trouble", "politics": "lethoria_court",
          "trade": "riverhaven_trade", "economic": "caravan_trouble", "work": "greyhollow_mines", "natural": "harvest_and_weather", "fortune": "far_wonder"}
broken = []
for kind, pid in sample.items():
    pr = world.pressures[pid]
    place = world.places.get(pr.place) or pulse.region_town(world, pr.place, random.Random(1))
    for key in threads.shapes(kind):
        for tier in ("normal", "uncommon", "rare"):
            out = threads.build(store, world, state, place, pr.model_copy(update={"template": key}), tier, random.Random(f"{key}:{tier}"), now)
            if not out:
                broken.append((key, tier, "nothing built")); continue
            prop, info = out
            text = " ".join([prop.title, prop.news, prop.truth, prop.reveal, prop.resolution, prop.fallout.description]
                            + [s.description for s in prop.stages] + [c.text for c in prop.clues] + [e.text for s in prop.stages for e in s.effects])
            if info["template"] != key or "{" in text or "}" in text or len(prop.stages) != pulse.P["tiers"][tier]["stages"]:
                broken.append((key, tier, info["template"], text[:60]))
check("every shape builds whole at every tier when a pressure names it, with every slot filled", not broken, broken[:3])
drawn = {threads.build(store, world, state, world.places["greywood"], world.pressures["greywood_predators"], "normal", random.Random(i), now)[1]["template"] for i in range(40)}
check("forty seeds of one threat at the Greywood draw at least three of its shapes", len(drawn) >= 3 and all(threads.kind_of(k) == "threat" for k in drawn), drawn)
same = [threads.build(store, world, state, world.places["greywood"], world.pressures["greywood_predators"], "uncommon", random.Random(21), now)[1]["template"] for _ in range(3)]
check("...and the same seed draws the same shape", len(set(same)) == 1, same)
w = threads.words_for(store, world, world.places["greywood"], world.pressures["greywood_predators"], random.Random(1), now)
w2 = {k: v for k, v in w.items() if k not in ("road", "creature", "creatures")}
picks = {threads.template_for(None, "threat", w2, random.Random(i))[0] for i in range(40)}
check("a shape whose needs the place cannot fill is never drawn: no road and no creature leaves only the lost party",
      picks == {"threat_missing"}, picks)
check("...and with nothing a threat needs, the kind falls back as before", threads.template_for(None, "threat", {k: v for k, v in w2.items() if k != "wild"}, random.Random(1))[0] == "social")
check("the checker refuses a shape with no base template, or one with no line a place can always fill",
      any("no base template" in x for x in (lambda T0: (threads.T["templates"].__setitem__("odd_shape", {"kind": "oddity", "titles": ["x"], "news": ["x"], "stages": [{"lines": ["x"]}], "fallout": {"lines": ["x"]}}), threads.problems(), threads.T["templates"].pop("odd_shape"))[1])(None))
      and any("every line needs a slot" in x for x in (lambda: (threads.T["templates"].__setitem__("thin_shape", {"kind": "social", "titles": ["{road}"], "news": ["x"], "stages": [{"lines": ["x"]}], "fallout": {"lines": ["x"]}}), threads.problems(), threads.T["templates"].pop("thin_shape"))[1])()))

shutil.rmtree("saves/threads_test", ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
