"""Win-rate matrix: each finished bot's character against every creature that can appear in the far lands, at a given level."""
import sys, random, collections, copy
sys.path.insert(0, ".")
import simlib
simlib.install(simlib.Stub("warrior", 1))
from storage.campaign import CampaignStore
from engine import combat
from world.loader import load_world
LV = int(sys.argv[1]) if len(sys.argv) > 1 else 140
CL = "warrior mage summoner priest ranger bard smith paladin monk warlock".split()
world = load_world()
zones = ["ash_wastes", "cinder_caldera", "stormcrown_heights", "thunder_spires", "deep_roads_tunnels", "lightless_deep", "drowned_shore", "jade_maw_jungle", "sepulchre_fields"]
foes = {}
for z in zones:
    for cr in world.bestiary.values():
        if cr.unique or not cr.roster or world.places[z].biome not in cr.biomes or cr.rarity == "legendary" and False: continue
        lo, hi = max(world.places[z].danger[0], cr.levels[0]), min(world.places[z].danger[1], cr.levels[1])
        if lo <= hi and hi >= LV - 10: foes[cr.id] = (cr, min(max(LV, lo), hi))
res = {}
for c in CL:
    st = CampaignStore.open_or_create(f"sim_{c}")
    ch = st.load_player().character
    for fid, (cr, lv) in foes.items():
        wins = 0
        for rank in ("normal",):
            p = combat.fighter_from_character(ch); p.side = "player"
            n = max(1, min(cr.group[1], 2))
            es = [combat.fighter_from_creature(cr, lv, rank, f"e{i+1}", cr.name, "engaged") for i in range(n)]
            allies = []
            for comp in ch.companions:
                shape = world.bestiary.get(comp.creature)
                if shape:
                    allies.append(combat.companion_fighter(shape, ch.level, f"ally_{comp.id}", comp.name))
            from engine import taming
            allies = taming.strongest(allies, ch.level)
            cmb = combat.Combat(fighters=[p] + allies + es)
            label, rate = combat.danger(cmb, runs=24, seed=1)
        res[(c, fid)] = rate
    print(c, "level", ch.level, "done", flush=True)
print("\nfoes:", len(foes), "at level ~", LV)
print(f"{'class':<9} {'mean win':>8} {'<25%':>6} {'>=97%':>6}")
for c in CL:
    v = [res[(c, f)] for f in foes]
    print(f"{c:<9} {sum(v)/len(v):>8.2f} {sum(x < .25 for x in v)/len(v):>6.0%} {sum(x >= .97 for x in v)/len(v):>6.0%}")
print("\nhardest foes (mean win rate over classes) and easiest:")
avg = {f: sum(res[(c, f)] for c in CL) / len(CL) for f in foes}
srt = sorted(avg, key=avg.get)
for f in srt[:14]:
    print(f"  {f:<24} {foes[f][0].category:<12} {foes[f][0].size:<10} lv{foes[f][1]} avg {avg[f]:.2f} | " + " ".join(f"{c[:3]}{res[(c,f)]:.1f}" for c in CL))
print("easiest:", ", ".join(f"{f} {avg[f]:.2f}" for f in srt[-8:]))
