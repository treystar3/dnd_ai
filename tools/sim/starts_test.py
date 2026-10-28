"""(f367) Starting points: a save shaped as if the character had lived part of the game already: the clock moved on, the guild's record,
reputation, standing and heat by town, people met, titles, and situations already over that the town remembers as settled by the
player or let be; a cataclysm settled is one survived."""
import random, shutil, sys
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from engine import clock, pulse, standing, starts
from npc.traits import load_traits
from storage.campaign import CampaignStore, PlayerState
from world.loader import load_world
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

import yaml
groups = set(yaml.safe_load(open("data/rules/standing.yaml", encoding="utf-8"))["groups"])
check("the starting points are sound: groups, tiers, ranks, a past within the days", starts.problems(groups, set(pulse.P["tiers"]), set("FEDCBAS")) == []
      and set(starts.rotation()) <= set(starts.names()) and len(starts.names()) >= 4, starts.problems(groups, set(pulse.P["tiers"]), set("FEDCBAS")))
world = load_world(); catalog = load_traits()
towns = starts.towns_for(world, world.start_location)
check("the town keys resolve: home is the nearest town to where play begins (the fields outside Parth), near is one other town, region the home region's others",
      towns["home"] == ["parth"] and len(towns["near"]) == 1 and towns["near"][0] != towns["home"][0]
      and all(world.places[t].region == world.places[towns["home"][0]].region for t in towns["region"]), towns)
home, near = towns["home"][0], towns["near"][0]

def fresh(name):
    shutil.rmtree(f"saves/starts_test_{name}", ignore_errors=True)
    store = CampaignStore.open_or_create(f"starts_test_{name}"); store.meta.seed = 7; store.meta.minutes = 8 * 60; store.save_meta()
    char, _ = simlib.make_character("warrior", random.Random(2))
    char.name = "Tam Reed"
    player = PlayerState(character=char, location=world.start_location, guild_rank="B")
    store.save_player(player)
    return store, player

# ---- a veteran: a year behind them, a campaign ended by their hand, known by name
store, player = fresh("veteran")
done = starts.apply(store, world, catalog, player, "veteran", random.Random(3), "Tam Reed")
pl = store.load_player(); st = store.load_world_state()
check("the clock has moved on by the start's days", store.meta.minutes == 160 * 1440 + 8 * 60 and done["days"] == 160, store.meta.minutes)
check("the guild's record and the titles are theirs", pl.guild_done == {"F": 6, "E": 6, "D": 6, "C": 5, "B": 2} and pl.titles == ["Warden of the Wend"], (pl.guild_done, pl.titles))
check("reputation by town, and more for what they settled there", pl.reputation.get(home, 0) >= 30 + 12 and pl.reputation.get(near, 0) >= 14, pl.reputation)
check("standing with the town's groups, in the town's words", standing.word(standing.value(pl, home, "guild", clock.day(store.meta.minutes))) == standing.word(45.0)
      and standing.value(pl, near, "guild", clock.day(store.meta.minutes)) > 10, pl.standing)
met = [n for n in (store.load_npc(i) for i in store.load_place(home).residents) if n.met_player]
check("people in the home town already know them, by name, and trust them about as the start says", len(met) >= 10 and all(n.name_known_to_player for n in met)
      and all(60 <= n.trust <= 80 for n in met) and all(n.last_talk_day >= 0 for n in met), [(n.name, n.trust) for n in met][:4])
past = [t for t in st["threads"] if t.get("started_as") == "past"]
check("three situations are already over, built by the engine at their tiers, none active", len(past) == 3 and {t["tier"] for t in past} == {"campaign", "rare", "uncommon"}
      and all(t["status"] != "active" for t in past) and all(t["ended_at"] < store.meta.minutes for t in past), [(t["tier"], t["status"], t["title"]) for t in past])
camp = next(t for t in past if t["tier"] == "campaign")
check("the campaign was ended by the player, at home, and is a deed in the ledger", camp["result"] == "player" and camp["place"] == home
      and any(d["kind"] == "settled" and d["thread"] == camp["id"] for d in st["deeds"]) and len([d for d in st["deeds"] if d["kind"] == "settled"]) == 2)
memory = store.load_place(home).memory
check("the home town remembers it as settled by them, and the ignored one near remembers being asked",
      any("settled by Tam Reed" in m["text"] and camp["title"] in m["text"] for m in memory)
      and any("Tam Reed was asked" in m["text"] for m in store.load_place(near).memory), (memory, store.load_place(near).memory))
check("the history and the news carry the endings, dated before play begins", any(camp["title"] in h["text"] for h in st["history"]) and all(h["minute"] < store.meta.minutes for h in st["history"])
      and any(n.get("thread") == camp["id"] for n in st["news"]))
check("no campaign is running, so a new one may start", not st.get("campaign") and st.get("cataclysm_end", 0) == 0)
check("the first pulse begins now, not a year ago", st["last"] == store.meta.minutes)

# ---- a legend: a cataclysm survived
store, player = fresh("legend")
starts.apply(store, world, catalog, player, "legend", random.Random(4), "Tam Reed")
st = store.load_world_state(); pl = store.load_player()
check("a cataclysm settled is one survived and counted", st.get("cataclysms") == 1 and st.get("cataclysm_end", 0) > 0 and len(pl.titles) == 2
      and sum(1 for t in st["threads"] if t.get("tier") == "campaign") == 2, (st.get("cataclysms"), st.get("cataclysm_end")))
check("every other town of the region regards them", all(pl.reputation.get(t, 0) == 20 for t in towns["region"]) if towns["region"] else True, pl.reputation)

# ---- scarred: heat and a bad name
store, player = fresh("scarred")
starts.apply(store, world, catalog, player, "scarred", random.Random(5), "Tam Reed")
pl = store.load_player()
check("heat and a bad standing with the guards", pl.heat.get(home, {}).get("heat") == 2 and standing.value(pl, home, "guards", clock.day(store.meta.minutes)) < -20 and pl.reputation.get(home, 0) == -6,
      (pl.heat, pl.standing.get(home), pl.reputation))

# ---- green: nothing but the level
store, player = fresh("green")
done = starts.apply(store, world, catalog, player, "green", random.Random(6), "Tam Reed")
check("the green start changes nothing but the clock it leaves alone", store.meta.minutes == 8 * 60 and done["met"] == 0 and done["situations"] == [] and not store.load_player().reputation)
try:
    starts.apply(store, world, catalog, player, "nobody", random.Random(1), "x")
    check("an unknown start is refused", False)
except KeyError:
    check("an unknown start is refused", True)

for name in ("veteran", "legend", "scarred", "green"):
    shutil.rmtree(f"saves/starts_test_{name}", ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
