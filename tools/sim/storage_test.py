"""The campaign store (storage/campaign.py): one SQLite file per campaign. A save in the old one-file-per-record layout is imported on
first open and the files moved aside; people are found through the index without parsing records; saves group into transactions; the
schema carries a version and migrations run once."""
import json, shutil, sys, time
from pathlib import Path
sys.path.insert(0, ".")
from storage.campaign import CampaignStore, PlayerState, PlaceState, CampaignMeta
from storage import migrations
from npc.models import NPC
import simlib, random
simlib.install(simlib.Stub("warrior", 1))
bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

root = Path("saves/_storage_test"); shutil.rmtree(root, ignore_errors=True)

# ---- the old layout, written by hand, then opened
(root / "npcs").mkdir(parents=True); (root / "places").mkdir()
(root / "campaign.json").write_text(CampaignMeta(name="_storage_test", seed=42, turn=7, minutes=5000, created="x").model_dump_json())
ch, _ = simlib.make_character("warrior", random.Random(1))
(root / "player.json").write_text(PlayerState(character=ch, location="parth").model_dump_json())
(root / "world_state.json").write_text(json.dumps({"last": 5000, "threads": [], "news": [{"text": "old news"}]}))
for i in range(40):
    n = NPC(id=f"n{i}", name=f"Person {i}", people="human", role="guild_contractor" if i % 10 == 0 else "farmer", location="parth" if i < 20 else "riverhaven",
            met_player=i % 4 == 0, name_known_to_player=i % 8 == 0, gone="left" if i % 7 == 0 else "", motive="wants rank" if i % 5 == 0 else "",
            tier="known" if i % 3 == 0 else "background", trust=40 + i)
    (root / "npcs" / f"{n.id}.json").write_text(n.model_dump_json())
(root / "places" / "parth.json").write_text(PlaceState(id="parth", populated=True, residents=["n0", "n1"]).model_dump_json())

t = time.perf_counter(); st = CampaignStore.open_or_create("_storage_test"); dt = time.perf_counter() - t
check("an old save is imported on first open", (root / "campaign.db").exists() and st.meta.seed == 42 and st.meta.turn == 7, (st.meta, dt))
check("...its files are moved aside, not deleted", (root / "legacy_json" / "npcs" / "n3.json").exists() and not (root / "npcs").exists())
check("...and nothing is lost: player, world state, places, people", st.load_player().location == "parth" and st.load_world_state()["news"][0]["text"] == "old news"
      and st.load_place("parth").residents == ["n0", "n1"] and len(st.list_npcs()) == 40)
check("...the save is at the current version", st.version == migrations.CURRENT, st.version)

# ---- the index: people found without parsing a record
rows = st.npc_rows(met_player=True, gone=False)
want = sorted(f"n{i}" for i in range(40) if i % 4 == 0 and i % 7 != 0)
check("met and still here, from the index", sorted(r.id for r in rows) == want, (sorted(r.id for r in rows), want))
check("...a row knows how to name itself", st.npc_rows(exclude=[])[0].label() == "Person 0" and st.npc_rows()[1].label() == "the farmer")
check("filters: role list, min trust, not a tier, location", [r.id for r in st.npc_rows(role=["guild_contractor"], min_trust=60, gone=False)] == ["n20", "n30"]
      and all(r.tier != "background" for r in st.npc_rows(not_tier="background")) and all(r.location == "riverhaven" for r in st.npc_rows(location="riverhaven")))
check("a motive filter and an exclusion", all(r.motive for r in st.npc_rows(motive=True)) and "n5" not in {r.id for r in st.npc_rows(exclude=["n5"])})
check("load_npcs: several at once, in the order asked, unknown ids skipped", [n.id for n in st.load_npcs(["n3", "zzz", "n1"])] == ["n3", "n1"])
n = st.load_npc("n2"); n.met_player = True; n.location = "riverhaven"; st.save_npc(n)
r = next(r for r in st.npc_rows() if r.id == "n2")
check("saving a person updates the index beside the record", r.met_player and r.location == "riverhaven")
check("npc_names comes from the index", "Person 2" in st.npc_names() and len(st.npc_names()) == 40)

# ---- transactions
p = st.load_player()
try:
    with st.transaction():
        p.location = "nowhere"; st.save_player(p)
        st.meta.turn = 99; st.save_meta()
        raise RuntimeError("boom")
except RuntimeError:
    pass
check("a transaction that fails leaves nothing behind", st.load_player().location == "parth" and CampaignStore.open_or_create("_storage_test").meta.turn == 7)
with st.transaction():
    p.location = "riverhaven"; st.save_player(p)
    with st.transaction():
        st.save_world_state({"last": 1, "nested": True})
check("...one that completes keeps everything, nested joins the outer", st.load_player().location == "riverhaven" and st.load_world_state().get("nested"))

# ---- the small blobs
st.save_combat('{"x": 1}'); check("combat saved and cleared", st.load_combat() == '{"x": 1}' and (st.save_combat(None) or st.load_combat() is None))
st.add_legendary_name("Dawnbreaker"); check("legendaries", st.legendary_names() == ["Dawnbreaker"])
st.save_story(["a", "b"], {"type": "narration", "text": "b"}); check("story", st.load_story() == (["a", "b"], {"type": "narration", "text": "b"}))
check("arcs and discoveries have their defaults", st.load_arcs()["arcs"] == [] and st.load_discoveries()["leads"] == [])

# ---- migrations run once, in order, and are recorded
calls = []
migrations.MIGRATIONS.append((migrations.CURRENT + 1, "test step", lambda s: calls.append(s.version)))
done = migrations.run(st)
check("a new migration runs once and moves the version", calls == [migrations.CURRENT] and st.version == migrations.CURRENT + 1 and len(done) == 1, (calls, done))
check("...and not again", migrations.run(st) == [] and st.version == migrations.CURRENT + 1)
migrations.MIGRATIONS.pop()

# ---- export for a look
st.export_json(root / "export")
check("export writes readable files", (root / "export" / "npcs" / "n2.json").exists() and json.loads((root / "export" / "player.json").read_text())["location"] == "riverhaven")

# ---- a fresh campaign
st.close(); shutil.rmtree(root)
st = CampaignStore.open_or_create("_storage_test")
check("a fresh campaign has a seed, no player, version current", st.meta.seed > 0 and not st.player_exists() and st.version == migrations.CURRENT)
st.close(); shutil.rmtree(root, ignore_errors=True)
print("\nFAILED: " + ", ".join(bad) if bad else "\nALL PASS")
sys.exit(1 if bad else 0)
