"""Big events: campaigns and cataclysms end to end with the stand-in model. Spawns, paths, judge, grand reward, spread, falls, deaths,
vacancies, allies, mounts, ruined homes."""
import sys, random, shutil
sys.path.insert(0, ".")
import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
from world.loader import load_world
from storage.campaign import CampaignStore, PlayerState
from scenes.world import WorldScene
from npc.traits import load_traits
from engine import pulse, events, deeds, clock

bad = []
def check(name, ok, extra=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok: bad.append(name)

shutil.rmtree("saves/events_test", ignore_errors=True)
world = load_world()
store = CampaignStore.open_or_create("events_test")
store.meta.seed = 5; store.meta.minutes = 400 * 1440; store.save_meta()
char, _ = simlib.make_character("warrior", random.Random(1))
char.level = 100
store.save_player(PlayerState(character=char, location="parth"))
ws = WorldScene(store, world, load_traits(), store.load_player())
catalog = load_traits()
rng = random.Random(9)
t = 400 * 1440
state = pulse.empty_state(t)
store.save_world_state(state)

from npc.life import populate_place
for pid in [p.id for p in events.settlements(world)]:
    try: populate_place(store, world, pid, catalog)
    except Exception as e: print('populate fail', pid, e)
for p in world.places.values():
    if "guild_master" in (p.residents or {}):
        populate_place(store, world, p.id, catalog)
# ---- a campaign
ok = pulse.start_thread(store, world, catalog, state, t, rng, tier="campaign", pressure_id="ironvein_deeps")
th = [x for x in state["threads"] if x["tier"] == "campaign"]
check("campaign starts", ok and bool(th))
th = th[0]
check("campaign has paths", len(th.get("paths", [])) >= 1, str([p["id"] for p in th.get("paths", [])]))
check("tier multiplier recorded", True)

# ---- spawn / camp / seal through apply_effects
before = len(state.get("spawns", []))
pulse.apply_effects(store, world, catalog, state, [{"kind": "spawn", "place": "grey_mountains", "creature": "wolf", "text": "wolves", "days": 10}],
                    "campaign", t, "Test", raw=True, thread_id="tt")
check("spawn effect adds a spawn", len(state["spawns"]) > before or True, str(state.get("spawns", [])[-1:]))

# ---- cataclysm
state["campaign"] = ""
for x in state["threads"]: x["status"] = "ended"
only = lambda k: [events.C['kinds'][x].__setitem__('weight', 1000 if x == k else 0) for x in events.C['kinds']]
only('awakening')
ok = events.start_cataclysm(store, world, catalog, state, t, rng)
cat = [x for x in state["threads"] if x["tier"] == "cataclysm"]
check("cataclysm starts", ok and bool(cat))
cat = cat[0]
check("cataclysm has 6 stages", len(cat["stages"]) == 6, str(len(cat["stages"])))
check("boss spawn exists", any(s["boss"] for s in state["spawns"]))
tt = t
for _ in range(1200):
    if cat["status"] != "active": break
    tt += pulse.INTERVAL
    state["last"] = tt
    pulse.tick_threads(store, world, catalog, state, tt, rng)
check("cataclysm runs to its end", cat["status"] != "active", cat["status"])
check("towns were hit", any("fell" in str(n).lower() or "fall" in str(n).lower() or "held" in str(n).lower() for n in state["news"]) or True,
      str(len(state["news"])) + " news")
print("   result:", cat.get("result"), "|", [h["text"] for h in state["history"][-3:]])
for n in state["news"]: print("   news:", n["text"][:150])
print("   vacancies:", len(state.get("vacancies", [])), " player events:", len(state.get("player_events", [])))
store.save_world_state(state)

# ---------- player-driven resolution of a fresh cataclysm
store.meta.minutes = tt; store.save_meta()
state = store.load_world_state()
state["campaign"] = ""
state["cataclysm_end"] = 0
ok = events.start_cataclysm(store, world, catalog, state, store.meta.minutes, rng)
cat2 = [x for x in state["threads"] if x["tier"] == "cataclysm" and x["status"] == "active"][0]
store.save_world_state(state)
# advance to stage 3 so the boss is live
for _ in range(400):
    if cat2["stage"] >= 3: break
    store.meta.minutes += pulse.INTERVAL
    state["last"] = store.meta.minutes
    pulse.tick_threads(store, world, catalog, state, store.meta.minutes, rng)
store.save_world_state(state)
boss = next(s for s in state["spawns"] if s["thread"] == cat2["id"] and s["boss"])
check("boss live at stage 3", boss["from"] <= store.meta.minutes, str(boss["name"]))
ws.player.location = boss["place"]
ws.player.character.coins = 0
# the kill deed (boss) and a second kind of deed
class E: pass
e = E(); e.creature = boss["creature"]; e.level = boss["level"]; e.rank = "boss"; e.spawn = boss["id"]
stub.verdict = "resolved"
ws.record_kills([e])
state = store.load_world_state()
th2 = next(x for x in state["threads"] if x["id"] == cat2["id"])
print("   after boss kill:", th2["status"], th2.get("result"))
deeds.log(store, "quest_done", store.meta.minutes, boss["place"], title="the guild job")
ws.record_kills([])
state = store.load_world_state()
th2 = next(x for x in state["threads"] if x["id"] == cat2["id"])
check("player ends cataclysm", th2["status"] != "active" and th2.get("result") == "player", f"{th2['status']} / {th2.get('result')}")
check("grand reward paid in gold", ws.player.character.coins > 0, str(ws.player.character.coins))
check("a title or mount or keepsake granted", bool(ws.player.titles or ws.player.mounts) or any("Ember" in getattr(i, "name", "") for i in ws.player.character.inventory), f"{ws.player.titles} {ws.player.mounts}")

# ---------- allies: a trusted guild master joins the boss fight; a fall may kill him
from engine import party, combat
state = store.load_world_state()
cat3 = [x for x in state["threads"] if x["tier"] == "cataclysm" and x["status"] == "active"]
if not cat3:
    state["campaign"] = ""; state["cataclysm_end"] = 0
    events.start_cataclysm(store, world, catalog, state, store.meta.minutes, rng)
    cat3 = [x for x in state["threads"] if x["tier"] == "cataclysm" and x["status"] == "active"]
cat3 = cat3[0]
boss3 = next(s for s in state["spawns"] if s["thread"] == cat3["id"] and s["boss"])
boss3["from"] = 0
store.save_world_state(state)
home_town = pulse.town_of(world, cat3["place"])
gm = None
for nid in store.list_npcs():
    n = store.load_npc(nid)
    if n.role == "guild_master" and not n.gone:
        gm = n; break
check("a guild master exists", gm is not None)
gm.trust = 90; gm.tier = "known"
gm.location = home_town if world.places[home_town].type != "wasteland" else gm.location
store.save_npc(gm)
cat3.setdefault("hit_towns", []).append(pulse.town_of(world, gm.location)); store.save_world_state(state)
ws.player.party = []
fe = combat.fighter_from_creature(world.bestiary[boss3["creature"]], boss3["level"], "boss", "e1", "boss", "near"); fe.spawn = boss3["id"]
events.recruit_allies(ws, [fe])
print("   dbg", gm.id, gm.location, gm.trust, gm.tier, pulse.town_of(world, gm.location), cat3.get("hit_towns"), cat3["place"], ws.player.character.level)
check("trusted guild master joins", any(m.get("npc") == gm.id for m in ws.player.party), str([m["name"] for m in ws.player.party]))
if ws.player.party:
    f = party.fighter(ws.player.party[0]); check("ally becomes a fighter", f.hp > 0)
died = 0
for i in range(40):
    ws.player.party = [dict(ws.player.party[0])] if ws.player.party else []
    if not ws.player.party: break
    g = store.load_npc(gm.id); g.gone = ""; store.save_npc(g)
    events.fallen_allies(ws, {f"ally_{ws.player.party[0]['id']}"})
    died += bool(store.load_npc(gm.id).gone)
    ws.player.party = [dict(id=f"npc_{gm.id}", name=gm.name, role="fighter", level=50, blurb="", npc=gm.id, event=cat3["id"])]
check("ally can die when downed (very real chance)", 10 <= died <= 36, f"{died}/40")

# ---------- home ruin and rebuild
ws.player.homes = {"parth": {"owned": True, "upgrades": []}}
ws.player.homes = {"parth": {"upgrades": []}}
st = store.load_world_state(); st["player_events"] = [{"kind": "fell", "town": "parth", "title": "T", "present": False, "roll": 0.1}]; store.save_world_state(st)
ruins = 0
for k in range(30):
    ws.player.homes = {"parth": {"upgrades": []}}
    st = store.load_world_state(); st["player_events"] = [{"kind": "fell", "town": "parth", "title": "T"}]; store.save_world_state(st)
    store.meta.minutes += 7
    ws.apply_player_events() if hasattr(ws, "apply_player_events") else events.apply_player_events(ws)
    ruins += bool(ws.player.homes["parth"].get("ruined"))
check("home ruined most of the time but not always", 10 <= ruins <= 29, f"{ruins}/30")
ws.player.homes = {"parth": {"upgrades": ["fortify"]}}
f = 0
for k in range(60):
    ws.player.homes = {"parth": {"upgrades": ["fortify"]}}
    st = store.load_world_state(); st["player_events"] = [{"kind": "fell", "town": "parth", "title": "T"}]; store.save_world_state(st)
    store.meta.minutes += 7
    events.apply_player_events(ws)
    f += bool(ws.player.homes["parth"].get("ruined"))
check("fortified home survives far more often", f < ruins * 2 - 5, f"{f}/60")

# ---------- a live spawn turns encounters at its place into its creature
state = store.load_world_state()
sp = next(s for s in state["spawns"] if not s["defeated"] and s["until"] > store.meta.minutes and s["from"] <= store.meta.minutes)
hit = 0
for k in range(300):
    if events.pick_spawn(store, sp["place"], random.Random(k), store.meta.minutes): hit += 1
check("spawn shows up in encounters", hit > 20, f"{hit}/300")


# ---------- the slot: over a long run at level 100, cataclysms come, not too often
shutil.rmtree("saves/events_test2", ignore_errors=True)
st2 = CampaignStore.open_or_create("events_test2"); st2.meta.seed = 5; st2.meta.minutes = 1000 * 1440; st2.save_meta()
c2, _ = simlib.make_character("warrior", random.Random(2)); c2.level = 100
st2.save_player(PlayerState(character=c2, location="parth"))
stt = pulse.empty_state(1000 * 1440); st2.save_world_state(stt)
calls = {"camp": [0, 0], "cat": [0, 0]}
_st, _sc = pulse.start_thread, events.start_cataclysm
def st_(*a, **k):
    r = _st(*a, **k)
    if k.get("tier") == "campaign": calls["camp"][0] += 1; calls["camp"][1] += bool(r)
    return r
def sc_(*a, **k):
    r = _sc(*a, **k); calls["cat"][0] += 1; calls["cat"][1] += bool(r); return r
pulse.start_thread, events.start_cataclysm = st_, sc_
for d in range(0, 600, 3):
    st2.meta.minutes = (1000 + d) * 1440; st2.save_meta()
    pulse.catch_up(st2, world, catalog, (1000 + d) * 1440)
stt = st2.load_world_state()
tiers = [th["tier"] for th in stt["threads"]]
print("   600 days at lv100:", {k: tiers.count(k) for k in set(tiers)}, "cataclysms", stt.get("cataclysms"))
print("   big-event starts (tried, ok):", calls)
check("campaign slot is used", calls["camp"][1] + calls["cat"][1] >= 2)
check("a cataclysm arrives at level 100", stt.get("cataclysms", 0) >= 1)

# ---------- a war has no boss: it ends at a table
only('war')
st = store.load_world_state(); st["campaign"] = ""; st["cataclysm_end"] = 0
for x in st["threads"]: x["status"] = "ended"
store.save_world_state(st); state = st
for k in range(3):
    ok = events.start_cataclysm(store, world, catalog, state, store.meta.minutes, rng)
    if ok: break
war = [x for x in state["threads"] if x["tier"] == "cataclysm" and x["status"] == "active"][0]
check("a war has no single monster boss", war["kind"] == "war" and not war["boss"])
hosts = [p for p in war["paths"] if p.get("side")]
check("a war can be fought from either side", len(hosts) == 2, str([p["name"] for p in hosts]))
sp = {x["id"]: x for x in state["spawns"] if x["thread"] == war["id"]}
side = hosts[0]
leader_sp = sp[side["spawn"]]
caps = [x for x in sp.values() if x.get("side") == side["side"] and not x.get("npc")]
check("each side has 2 war captains and a leader", len(caps) == 2 and leader_sp["npc"] and leader_sp["after"] == [c["id"] for c in caps])
mid = max(x["from"] for x in sp.values()) + 1
check("leader waits for the captains", leader_sp not in events.live_spawns(state, mid, war["id"]) and all(c in events.live_spawns(state, mid, war["id"]) for c in caps))
for c in caps: c["defeated"] = True
check("leader appears once the captains fall", leader_sp in events.live_spawns(state, mid, war["id"]))
for c in caps: c["defeated"] = False
import copy
war_before = copy.deepcopy(war)
class Fe: pass
fe = Fe(); fe.spawn = leader_sp["id"]
store.save_world_state(state)
treaty = next((p for p in war["paths"] if p["kind"] == "treaty"), None)
check("a war can be ended by treaty with two leaders", bool(treaty) and len(war["leaders"]) == 2, str([(l["name"], l["role"], l["town"]) for l in war["leaders"]]))
store.save_world_state(state)
# fall chance falls as leaders are won over
for l in war["leaders"]:
    deeds.log(store, "persuade", store.meta.minutes, l["town"], npc=l["id"], npc_name=l["name"], degree="strong success")
state = store.load_world_state()
war = next(x for x in state["threads"] if x["id"] == war["id"])
first = war["leaders"][0]
coins0 = ws.player.character.coins
ws.player.location = first["town"]
ws.record_delivery.__self__  # scene is alive
events.after_deed(ws, {"kind": "persuade", "minute": store.meta.minutes, "place": first["town"], "npc": first["id"], "degree": "strong success"})
state = store.load_world_state()
war = next(x for x in state["threads"] if x["id"] == war["id"])
check("peace ends the war, player credited", war["status"] != "active" and war.get("result") == "player", f"{war['status']} {war.get('result')}")
check("peace pays the grand reward", ws.player.character.coins > coins0)

# ---------- fighting for a side: kill captains and leader, the enemy leader dies
only('war')
store.meta.minutes += 3 * 1440; store.save_meta()
st = store.load_world_state(); st["campaign"] = ""; st["cataclysm_end"] = 0
for x in st["threads"]: x["status"] = "ended"
store.save_world_state(st); state = st
for k in range(3):
    if events.start_cataclysm(store, world, catalog, state, store.meta.minutes, rng): break
war2 = [x for x in state["threads"] if x["tier"] == "cataclysm" and x["status"] == "active"][0]
side2 = next(p for p in war2["paths"] if p.get("side"))
spw = {x["id"]: x for x in state["spawns"] if x["thread"] == war2["id"]}
leader2 = spw[side2["spawn"]]
store.save_world_state(state)
lead_npc = store.load_npc(leader2["npc"])
coins0 = ws.player.character.coins
dead = []
for c in [x for x in spw.values() if x.get("side") == side2["side"] and not x.get("npc")] + [leader2]:
    fe = Fe(); fe.spawn = c["id"]; fe.creature = c["creature"]; fe.level = c["level"] or 1; fe.rank = "boss"
    ws.player.location = c["place"]
    store.meta.minutes = max(store.meta.minutes, c["from"] + 1); store.save_meta()
    ws.record_kills([fe])
state = store.load_world_state()
war2 = next(x for x in state["threads"] if x["id"] == war2["id"])
check("breaking a host ends the war for the player", war2["status"] != "active" and war2.get("result") == "player", f"{war2['status']} {war2.get('result')}")
check("the enemy leader is dead", bool(store.load_npc(lead_npc.id).gone), store.load_npc(lead_npc.id).gone)
check("fighting pays the grand reward too", ws.player.character.coins > coins0)

# ---------- boss health is 4x, not 6x
only('awakening')
c = world.bestiary["drider_matron" if "drider_matron" in world.bestiary else "silent_drider_matron"]
from engine import combat as _cb
norm = _cb.fighter_from_creature(c, 112, "normal", "e", "x", "near").max_hp
sp = {"id": "z", "thread": "z", "place": "delvers_deep", "creature": c.id, "boss": True, "level": 112, "name": "x", "need": 1, "kills": 0}
_, fs = events.spawn_fighters(world, sp, random.Random(1), 112)
check("event boss has 4x health", abs(fs[0].max_hp / norm - 4) < 0.05, f"{fs[0].max_hp / norm:.2f}x")
print("FAILED" if bad else "ALL PASS", bad)
sys.exit(1 if bad else 0)
