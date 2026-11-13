"""(f622) A row of authored data holds no key its model does not know. Eight roles in data/world/roles.yaml were written as a table
on one line with a comma in the description and no quotes, so YAML ended the description at the comma and made keys of the rest
("Sells candles", then `rope` and `oil and sundries.`); the model dropped those keys in silence and every prompt was told half a role.
Nothing refused it: 39 of the 40 models the data loads into ignored a key they did not know. Now every loader of an authored file
builds its rows through core/yamlio.py row, which refuses such a key at any depth of the row. The models themselves are as they were:
a place is also read back from a save, and an older save's retired key must not stop it loading.
Run: python tools/sim/row_keys_622_test.py"""
import collections
import importlib
import os
import pkgutil
import shutil
import sys
import yaml
from pathlib import Path
sys.path.insert(0, ".")
sys.path.insert(0, "tools/sim")
from pydantic import BaseModel, ValidationError
from core import yamlio

# ---- the watch, set before anything loads: every mapping the YAML reader hands out, and every model built from one
authored = collections.defaultdict(list)          # a mapping's keys -> the mappings read with those keys (kept, so each stays itself)
inside = [0]                                      # how deep in yamlio.row the build is
through, around = collections.Counter(), []       # models built from an authored mapping: through row, and around it
models = {}                                       # ...and the models themselves


def keep(x) -> None:
    if isinstance(x, dict):
        if x:
            authored[frozenset(map(str, x))].append(x)
        for v in x.values():
            keep(v)
    elif isinstance(x, (list, tuple)):
        for v in x:
            keep(v)


def is_authored(data) -> bool:
    return isinstance(data, dict) and bool(data) and any(c is data or c == data for c in authored.get(frozenset(map(str, data)), ()))


def site() -> str:
    f = sys._getframe(2)
    while f and ("pydantic" in f.f_code.co_filename or f.f_code.co_filename == __file__ or f.f_code.co_filename.endswith("yamlio.py")):
        f = f.f_back
    return f"{os.path.relpath(f.f_code.co_filename).replace(os.sep, '/')}:{f.f_lineno}" if f else "?"


def seen(cls, data) -> None:
    if is_authored(data):
        if inside[0]:
            through[cls.__name__] += 1
            models[cls.__name__] = cls
        else:
            around.append((cls.__name__, site(), str(data.get("id") or data.get("name") or sorted(data)[:3])))


_load, _init, _validate = yamlio.safe_load, BaseModel.__init__, BaseModel.model_validate.__func__
_row = getattr(yamlio, "row", None)


def load(stream):
    out = _load(stream)
    keep(out)
    return out


def init(self, /, **data):
    seen(type(self), data)
    _init(self, **data)


init.__pydantic_base_init__ = True                # still the base's own: a model is validated as it is in the game, not through this


def validate(cls, obj, *a, **k):
    seen(cls, obj)
    return _validate(cls, obj, *a, **k)


def row(model, raw, *a, **k):
    inside[0] += 1
    try:
        return _row(model, raw, *a, **k)
    finally:
        inside[0] -= 1


yamlio.safe_load, BaseModel.__init__, BaseModel.model_validate = load, init, classmethod(validate)
if _row:
    yamlio.row = row

import simlib
stub = simlib.Stub("warrior", 3)
simlib.install(stub)
simlib.quiet_console()

bad = []
def check(n, ok, x=""):
    print(("ok   " if ok else "FAIL ") + n, "" if ok else x)
    if not ok: bad.append(n)


def refused(model, raw, where=""):
    """The keys a row is refused for ([] when it is taken), and the words of the refusal."""
    if not _row:
        return [], "core/yamlio.py has no row"
    try:
        yamlio.row(model, raw, where) if where else yamlio.row(model, raw)
    except ValidationError as e:
        return [".".join(map(str, x["loc"])) for x in e.errors() if x["type"] == "extra_forbidden"], str(e)
    except ValueError as e:
        return ["?"], str(e)
    return [], ""


# ---- the rule, on rows the game does not hold
from world.loader import Place, Road, Role, Town
from engine.pools import PoolRules
from engine.inventory import Recipe
check("core/yamlio.py has row, the one way an authored row becomes its model", bool(_row))
ROLE = {"id": "ropemaker", "description": "Twists rope", "hours": [7, 19]}
check("a row of keys its model knows is taken, and is the model as it was built before",
      _row and yamlio.row(Role, ROLE) == Role(**ROLE) and refused(Role, ROLE) == ([], ""), refused(Role, ROLE))
check("a key the model does not know is refused, and named", refused(Role, {**ROLE, "hemp and tar.": None})[0] == ["hemp and tar."],
      refused(Role, {**ROLE, "hemp and tar.": None}))
check("...a key of a row inside the row too (a ware a role sells)",
      refused(Role, {**ROLE, "sells": [{"id": "coil", "name": "a coil of rope", "price": 40, "pirce": 4}]})[0] == ["sells.0.pirce"],
      refused(Role, {**ROLE, "sells": [{"id": "coil", "name": "a coil of rope", "price": 40, "pirce": 4}]}))
TOWN = {"id": "parth", "landmarks": [{"name": "the Mill", "where": "parth", "note": "burned once"}], "festivals": [{"name": "Tallow", "season": "winter", "day": 3}]}
check("...and of one two deep (a town's landmark, its festival), each named where it stands",
      refused(Town, TOWN) == ([], "") and refused(Town, {**TOWN, "landmarks": [{**TOWN["landmarks"][0], "nots": "x"}],
                                                       "festivals": [{**TOWN["festivals"][0], "dayz": 2}]})[0] == ["landmarks.0.nots", "festivals.0.dayz"],
      refused(Town, {**TOWN, "landmarks": [{**TOWN["landmarks"][0], "nots": "x"}], "festivals": [{**TOWN["festivals"][0], "dayz": 2}]}))
PLACE = {"id": "ropewalk", "name": "the Ropewalk", "type": "workshop", "region": "south"}
check("a field that is a table of the author's own keys takes any (a place's stations, its audience)",
      refused(Place, {**PLACE, "stations": {"walk": {"anything": 1}}, "audience": {"keeper": "ropemaker", "whatever": True}}) == ([], ""),
      refused(Place, {**PLACE, "stations": {"walk": {"anything": 1}}, "audience": {"keeper": "ropemaker", "whatever": True}}))
check("a key written by its other name is the model's own (a road's `from`)",
      refused(Road, {"id": "r", "name": "the Tar Road", "from": "parth", "to": "ropewalk"}) == ([], ""),
      refused(Road, {"id": "r", "name": "the Tar Road", "from": "parth", "to": "ropewalk"}))
POOLS = yamlio.safe_load(Path("data/rules/pools.yaml").read_text(encoding="utf-8"))
first = next(iter(POOLS["pools"]))
check("a table that is one row (the pools) is held the same, a rule's own keys too",
      refused(PoolRules, POOLS) == ([], "") and refused(PoolRules, {**POOLS, "regen": 1})[0] == ["regen"]
      and refused(PoolRules, {**POOLS, "pools": {**POOLS["pools"], first: {**POOLS["pools"][first], "bse": 1}}})[0] == [f"pools.{first}.bse"],
      refused(PoolRules, {**POOLS, "pools": {**POOLS["pools"], first: {**POOLS["pools"][first], "bse": 1}}}))
keys, said = refused(Recipe, {"id": "tarred_rope", "name": "Tarred rope", "makes": {"rope": 1}, "ingredients": [], "tar": 2}, "recipes.yaml")
check("a loader that collects nothing itself is told the file, the row and the key",
      keys == ["?"] and all(w in said for w in ("recipes.yaml", "tarred_rope", "tar")) and "\n" not in said.strip(), said)
try:
    kept = Place(**{**PLACE, "retired_key": 1})
except Exception as e:
    kept = e
check("the model itself is as it was: a place read back from a save keeps loading with a key since retired", isinstance(kept, Place), kept)

# ---- the loaders, on files the game does not hold: the shape that found it, a one-line table with a comma and no quotes
tmp = Path("saves/row_keys_622")
shutil.rmtree(tmp, ignore_errors=True)
(tmp / "towns").mkdir(parents=True)
from world import loader
from core import rules as core_rules
from npc import traits as npc_traits
(tmp / "roles.yaml").write_text("- {id: ropemaker, hours: [7, 19], description: Twists rope, hemp and tar., knowledge_groups: [merchants]}\n"
                                '- {id: caulker, hours: [7, 19], description: "Caulks hulls, decks and casks.", knowledge_groups: [merchants]}\n', encoding="utf-8")
problems = []
got = loader._load_list(tmp / "roles.yaml", Role, problems)
check("the world's loader refuses the row cut at its comma, naming the file, the row and the key, and takes the quoted one whole",
      list(got) == ["caulker"] and got["caulker"].description == "Caulks hulls, decks and casks." and len(problems) == 1
      and all(w in problems[0] for w in ("roles.yaml", "ropemaker", "hemp and tar.")), (list(got), problems))
(tmp / "towns" / "parth.yaml").write_text("id: parth\ncharacter: A mill town.\nlandmarks:\n  - {name: the Mill, where: parth, note: burned once, long ago}\n", encoding="utf-8")
problems = []
got = loader._load_towns(tmp / "towns", problems)
check("...a town's profile the same, two deep", not got and len(problems) == 1 and "parth.yaml" in problems[0] and "long ago" in problems[0], (got, problems))
real = yamlio.safe_load(Path("data/rules/stats.yaml").read_text(encoding="utf-8"))
(tmp / "stats.yaml").write_text(yaml.safe_dump([{**real[0], "covrs": "x"}] + real[1:]), encoding="utf-8")
try:
    core_rules._load(tmp / "stats.yaml", core_rules.StatDef)
    said = ""
except Exception as e:
    said = str(e)
check("the rules' loader refuses a stat with a key it does not know", "stats.yaml entry 1" in said and "covrs" in said, said[:300])
real = yamlio.safe_load(npc_traits.TRAITS_PATH.read_text(encoding="utf-8"))
(tmp / "traits.yaml").write_text(yaml.safe_dump(real[:3] + [{**real[3], "descripton": "x"}] + real[4:]), encoding="utf-8")
try:
    npc_traits.load_traits(tmp / "traits.yaml")
    said = ""
except Exception as e:
    said = str(e)
check("...and the traits' loader a trait", "descripton" in said and str(real[3]["id"]) in said, said[:300])

from engine import enchanting
kept_rules = enchanting.RULES
try:
    enchanting.RULES = {**kept_rules, "general": [{**kept_rules["general"][0], "fee_multipler": 9}]}
    enchanting._general_options()
    said = ""
except Exception as e:
    said = str(e)
finally:
    enchanting.RULES = kept_rules
check("a row that was built field by field is handed whole now (a general enchantment): its misspelt key is refused, not dropped",
      "fee_multipler" in said and "enchanting.yaml" in said and str(kept_rules["general"][0]["id"]) in said, said[:300])
whole = enchanting._general_options()
check("...and the general enchantments are what they were",
      list(whole) == [g["id"] for g in kept_rules["general"]] and all(whole[g["id"]].fee_multiplier == g.get("fee_multiplier", 1.0)
      and [e.model_dump() for e in whole[g["id"]].effects] == [{"trigger": "always", **e} for e in g["effects"]] for g in kept_rules["general"]),
      list(whole)[:4])

# ---- the game's own data
world0 = loader.authored()
CUT = {"chandler": "Sells candles, rope, oil and sundries.", "wanderer": "Someone on their way through, with a story of where from.",
       "guild_clerk": "Keeps the guild's contract board, records and coin box.", "loremaster": "Keeps the old songs, records and histories.",
       "engineer": "Designs the works, lifts and machines that keep the city running.",
       "water_priest": "Keeps the waters of the city, the hearth and the rites of Dahlira bound up with them.",
       "noble": "A member of a noble house, at home in the court.",
       "land_agent": "Sells houses and lots in the city, and knows who is leaving and who is moving in."}
check("the eight roles that loaded cut at a comma are whole, their words as they were written",
      all(world0.roles[r].description == d for r, d in CUT.items()), {r: world0.roles[r].description for r, d in CUT.items() if world0.roles[r].description != d})
lines = yamlio.safe_load(Path("data/world/roles.yaml").read_text(encoding="utf-8"))
short = [r.id for r in world0.roles.values() if not r.description.rstrip().endswith(".")]
check("...and every role's description is a whole sentence, each row of the file a role", not short and len(lines) == len(world0.roles) > 40,
      (short, len(lines), len(world0.roles)))
from engine import data_check
check("the game's data passes its startup check", data_check.check() == [], data_check.check()[:5])

# ---- the ratchet: whoever loads it, whenever, an authored mapping becomes a model through row alone
for pkg in ("core", "world", "character", "engine", "npc", "llm", "storage", "services", "scenes", "ui"):
    for m in pkgutil.walk_packages(importlib.import_module(pkg).__path__, pkg + "."):
        importlib.import_module(m.name)
npc_traits.load_traits()
import world_script
run = world_script.play("row_keys_622", stub)
ws = run.game.scene
ws.player.guild_rank = "F"
ws.enter("guild_house")
ws.party_service.hire(ws.party_roster()[0], ws.player.character.level)
ws.enter(world_script.PLACE)
run.game.store.close()
files = sum(len(v) for v in authored.values())
check("the watch saw the data load and a script played: thousands of mappings read, well over a thousand rows built through row, of twenty models or more",
      files > 5000 and sum(through.values()) > 1500 and len(through) >= 20, (files, sum(through.values()), sorted(through)))
shown = collections.Counter((c, s) for c, s, _ in around)
check("no model is built from an authored mapping by any other road (a new loader goes through core/yamlio.py row)", not around,
      "\n     " + "\n     ".join(f"{c} at {s} x{n}, e.g. {next(l for c2, s2, l in around if (c2, s2) == (c, s))}" for (c, s), n in shown.most_common(30)))
import typing


def held(cls, found: dict) -> dict:
    """A model and every model that stands inside its rows."""
    def inner(tp):
        if isinstance(tp, type) and issubclass(tp, BaseModel):
            yield tp
        for a in typing.get_args(tp):
            yield from inner(a)
    if cls.__name__ not in found:
        found[cls.__name__] = cls
        for f in cls.model_fields.values():
            for sub in inner(f.annotation):
                held(sub, found)
    return found


every = {}
for cls in models.values():
    held(cls, every)
own = sorted(n for n, c in every.items() if not getattr(c.__init__, "__pydantic_base_init__", False))
check("no model a row becomes, nor one inside it, has an __init__ of its own (the check would not reach past one)",
      len(every) > len(models) >= 20 and not own, (len(every), len(models), own))
probe = yamlio.safe_load("- {id: tarman, description: Boils tar, pitch and resin.}\n")[0]
before = len(around)
Role(**probe)
check("...and the watch does catch one that is (a row unpacked into its model, the key dropped in silence)",
      len(around) == before + 1 and around[-1][0] == "Role", around[-1:])
del around[before:]

shutil.rmtree(tmp, ignore_errors=True)
print("\nALL PASS" if not bad else "\nFAILED: " + ", ".join(bad))
sys.exit(1 if bad else 0)
