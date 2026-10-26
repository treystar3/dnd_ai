"""The town profile drafting tool (f317): a draft is cut to what the map allows, written in the loader's shape, and checked by the
loader's own rules; a draft the loader would refuse is not kept."""
import sys, shutil
sys.path.insert(0, "."); sys.path.insert(0, "tools")
from pathlib import Path
import yaml
from world.loader import load_world
import draft_towns as dt

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)

world = load_world()
truth = yaml.safe_load(Path("data/rules/truth.yaml").read_text(encoding="utf-8"))
pulse = yaml.safe_load(Path("data/rules/pulse.yaml").read_text(encoding="utf-8"))
top = world.places["kelpmoor"]
req = dt.request(world, top, truth, pulse)
check("the request gives the town's places, roles, pressures, lore, size and the calendar", "THE TOWN'S PLACES" in req and "ROLES THE TOWN HAS" in req
      and "SEASONS: spring" in req and "kelpmoor - Kelpmoor" in req and "SIZE: its scale is" in req, req[:300])
vreq = dt.request(world, world.places["lethoria"], truth, pulse)
check("the capital's size is the capital's (places.yaml scale), with the quarters that means, and the writer is told it is the capital",
      "SIZE: its scale is capital" in vreq and "DISTRICTS: 6 to 9 quarters" in vreq and "ANCHORS: 6 to 8 people" in vreq and "THIS IS THE CAPITAL" in vreq
      and "DISTRICTS: 1 to 2 quarters" in one if (one := dt.request(world, world.places["willowmead"], truth, pulse)) else False)

roles = sorted({r for p in dt.town_places(world, "kelpmoor") for r in p.residents})
mine = [p.id for p in dt.town_places(world, "kelpmoor")]
d = dt.ProfileDraft(character="A fishing village on the salt marsh that smells of weed and tar, where every family has a boat and a grudge against the tide. People are slow to speak and slower to trust.",
                    landmarks=[{"name": "the old jetty", "where": mine[0], "note": "the long jetty the boats tie to"},
                               {"name": "a bridge in Parth", "where": "trading_square", "note": "wrong town"}],
                    districts=["The Weed Shore", "the net lofts"],
                    anchors=[{"role": roles[0], "note": "oldest hand on the shore"}, {"role": "dragon_tamer", "note": "nobody"}],
                    trouble=["The tide takes more of the shore each year."], secret="The jetty's piles are rotten and the elder knows.",
                    festivals=[{"name": "the Tide Fair", "season": "summer", "day": 5, "days": 2}, {"name": "x", "season": "monsoon", "day": 1}],
                    scale="village", guard="none", crowd={"market": "nets out, boats in"})
data, dropped = dt.fit(world, top, d, truth, pulse)
check("what the map does not allow is cut from the draft and said; a landmark placed nowhere stands in the town itself",
      len(data["landmarks"]) == 2 and data["landmarks"][1]["where"] == "kelpmoor" and len(data["anchors"]) == 1 and len(data["festivals"]) == 1
      and data["crowd"] == {"market": "nets out, boats in"} and len(dropped) == 3, dropped)
check("the writer is told where a landmark may stand, and the names other towns use", "WHERE A LANDMARK MAY STAND: kelpmoor, kelpmoor_inn" in req
      and "ALREADY USED" in req and "the Wend bridge" in req, [l for l in req.split("\n") if l.startswith(("WHERE", "ALREADY"))])
one = dt.request(world, world.places["willowmead"], truth, pulse)
check("...and a town that is one place is told so", "every landmark stands at willowmead" in one)
check("...districts are lower case and the rest is kept", data["districts"] == ["the weed shore", "the net lofts"] and data["scale"] == "village" and data["secret"])

out = Path("saves/draft_test_kelpmoor.yaml")
dt.write_profile(out, data, top.name)
raw = yaml.safe_load(out.read_text(encoding="utf-8"))
check("the file is written in the loader's shape, with a header saying it is a draft", raw["id"] == "kelpmoor" and raw["landmarks"][0]["name"] == "the old jetty"
      and out.read_text(encoding="utf-8").startswith("# Kelpmoor - the town's profile. DRAFTED"))
check("...and the loader's own check passes it", dt.check_file(world, out) == [], dt.check_file(world, out))
bad_data = dict(data, anchors=[{"role": "dragon_tamer", "note": "x"}])
dt.write_profile(out, bad_data, top.name)
check("a file the loader would refuse is caught by the same check", any("anchor role" in p for p in dt.check_file(world, out)))
out.unlink(missing_ok=True)

# the capital's anchors include the one who rules
vtop = world.places["lethoria"]
vd = dt.ProfileDraft(character=d.character, anchors=[{"role": "guild_master", "note": "x"}, {"role": "chamberlain", "note": "keeps the door"}, {"role": "guild_master", "note": "again"}], scale="capital")
vdata, vdropped = dt.fit(world, vtop, vd, truth, pulse)
check("the capital's anchors always include the monarch, and a role is an anchor once", vdata["anchors"][0]["role"] == "monarch"
      and [a["role"] for a in vdata["anchors"]] == ["monarch", "guild_master", "chamberlain"] and any("given twice" in x for x in vdropped), (vdata["anchors"], vdropped))
check("the palace is a place of the capital with the crown in it", "lethoria_palace" in [p.id for p in dt.town_places(world, "lethoria")]
      and world.places["lethoria_palace"].residents.get("monarch") == 1 and "monarch" in world.roles)

# the tool end to end, with a stand-in for the model
calls = []
def fake_generate(task, system, user, schema, **kw):
    calls.append(task)
    return d
dr = dt.draft(world, top, truth, pulse, fake_generate)
check("the draft is asked for as its own kind of call", calls == ["town_profile"] and dr is d)

print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad), bad if bad else "")
sys.exit(1 if bad else 0)
