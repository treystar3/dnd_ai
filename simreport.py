"""Reads sim_out/*_summary.json and *.jsonl and prints the findings."""

import collections
import itertools
import json
import statistics as st
import sys
from pathlib import Path

import os
OUT = Path(os.environ.get("SIM_OUT", "sim_out"))
CLASSES = [c for c in ("warrior", "mage", "summoner", "priest", "ranger", "bard", "smith", "paladin", "monk", "warlock") if (OUT / f"{c}_summary.json").exists()]
S = {c: json.loads((OUT / f"{c}_summary.json").read_text()) for c in CLASSES}
BANDS = [(1, 10), (10, 20), (20, 35), (35, 50), (50, 65), (65, 80), (80, 100), (100, 125), (125, 151)]


def events(c):
    return [json.loads(l) for l in open(OUT / f"{c}.jsonl")]


def _milestones(c):
    out = {}
    for e in events(c):
        if e["k"] == "tick":
            for lv in range(10, e["lv"] + 1, 5):
                out.setdefault(lv, (e["d"], e.get("deaths", 0)))
    return out


def pct(a, b):
    return f"{100 * a / b:.0f}%" if b else "-"


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0


def band_name(b):
    return f"{b[0]}-{b[1] - 1}"


def head(t):
    print("\n" + "=" * 100 + f"\n{t}\n" + "=" * 100)


from world.loader import load_world
W = load_world()
MS = {c: _milestones(c) for c in CLASSES}

# ---------------------------------------------------------------- 1. headline
head("1. HEADLINE")
for c in CLASSES:
    s = S[c]
    print(f"{c:<9} level {s['level']:>2} | day {s['day']:>4} | steps {s['steps']:>6} | deaths {len(s['deaths']):>3} | "
          f"guild rank {s['rank'] or '-'} | ended: {s['end']} | {s['secs']}s")
print("\nDay each level was reached (deaths so far in brackets):")
print(f"{'level':>7} " + " ".join(f"{c:>14}" for c in CLASSES))
for lv in range(10, 155, 5):
    row = []
    for c in CLASSES:
        m = MS[c].get(lv)
        row.append(f"{m[0]:>6} ({m[1]:>3})" if m else f"{'-':>14}")
    print(f"{lv:>7} " + " ".join(f"{x:>14}" for x in row))

# ---------------------------------------------------------------- 2. xp and time
head("2. WHERE XP, COIN AND TIME COME FROM")
for c in CLASSES:
    s = S[c]
    xp = s["xp_src"]; tot = sum(xp.values()) or 1
    print(f"\n{c}: XP sources: " + ", ".join(f"{k} {100 * v / tot:.0f}%" for k, v in sorted(xp.items(), key=lambda kv: -kv[1]) if v / tot > 0.01))
    inc = s["income"]; sp = s["spend"]
    print(f"   coin earned: " + ", ".join(f"{k} {v / 100:,.0f}s" for k, v in sorted(inc.items(), key=lambda kv: -kv[1])[:5]) +
          f" | spent: " + ", ".join(f"{k} {v / 100:,.0f}s" for k, v in sorted(sp.items(), key=lambda kv: -kv[1])[:5]))
    tm = s["cat_minutes"]; tt = sum(tm.values()) or 1
    print(f"   time: " + ", ".join(f"{k} {100 * v / tt:.0f}%" for k, v in sorted(tm.items(), key=lambda kv: -kv[1]) if v / tt > 0.02))
    print(f"   gear at the end: " + "; ".join(f"{sl}: {n} ({r}, lv{lv})" for sl, (n, r, lv) in list(s["equipment"].items())[:5]))
    print(f"   purse at the end: {s['coins'] / 100:,.0f} silver")

# ---------------------------------------------------------------- 3. fights
head("3. FIGHTS BY LEVEL BAND")
for c in CLASSES:
    fights = S[c]["fights"]
    print(f"\n{c}:  band    fights  win   fled  died  rounds  hp-lost  rating  foe-lvl vs yours")
    for b in BANDS:
        fs = [f for f in fights if b[0] <= f["lv"] < b[1]]
        if not fs:
            continue
        rel = mean(mean(x[1] for x in f["foes"]) - f["lv"] for f in fs)
        print(f"        {band_name(b):>7} {len(fs):>7} {pct(sum(f['outcome'] == 'victory' for f in fs), len(fs)):>5} "
              f"{pct(sum(f['outcome'] == 'fled' for f in fs), len(fs)):>5} {pct(sum(f['outcome'] == 'defeat' for f in fs), len(fs)):>5} "
              f"{mean(f['rounds'] for f in fs):>7.1f} {100 * mean(f['hp_lost'] for f in fs):>7.0f}% {mean(f['rating'] for f in fs):>7.2f} {rel:>+9.1f}")

head("3b. DOES THE DANGER RATING TELL THE TRUTH? (fights the bot chose to fight)")
allf = [f for c in CLASSES for f in S[c]["fights"] if not f["fled_open"]]
print("rating shown   fights   actually won   died")
for lo, hi in [(0, .2), (.2, .4), (.4, .6), (.6, .8), (.8, .95), (.95, 1.01)]:
    fs = [f for f in allf if lo <= f["rating"] < hi]
    print(f"  {lo:.2f}-{min(hi, 1):.2f}   {len(fs):>6}   {pct(sum(f['outcome'] == 'victory' for f in fs), len(fs)):>10}   {pct(sum(f['outcome'] == 'defeat' for f in fs), len(fs)):>5}")
labels = collections.Counter(f["label"] for f in allf)
print("labels shown:", dict(labels))

# ---------------------------------------------------------------- 4. deaths
head("4. DEATHS")
for c in CLASSES:
    ds = S[c]["deaths"]
    print(f"\n{c}: {len(ds)} deaths | by band: " + ", ".join(f"{band_name(b)}: {sum(b[0] <= d['lv'] < b[1] for d in ds)}" for b in BANDS))
    byplace = collections.Counter(d["place"] for d in ds)
    print("   where: " + ", ".join(f"{p} {n}" for p, n in byplace.most_common(5)))
    foes = collections.Counter(f[0] for d in ds for f in d["foes"])
    print("   to: " + ", ".join(f"{k} {n}" for k, n in foes.most_common(6)))
    surprise = sum(1 for d in ds if d["rate"] >= 0.6)
    print(f"   rating at the start of the fight that killed them: {surprise} of {len(ds)} had been rated 60%+ winnable; "
          f"median {st.median(d['rate'] for d in ds):.2f}" if ds else "   none")

# ---------------------------------------------------------------- 5. guild
head("5. THE GUILD")
for c in CLASSES:
    s = S[c]; ev = events(c)
    ranks = []
    last = ""
    for e in ev:
        if e["k"] == "tick" and e.get("rank") and e["rank"] != last:
            ranks.append(f"{e['rank']}@day{e['d']}/lv{e['lv']}")
            last = e["rank"]
    print(f"\n{c}: rank timeline: {' -> '.join(ranks) or 'never joined'} | contracts done by letter: {s['guild_done']}")
    qs = s["quests"]
    by = collections.defaultdict(list)
    for q in qs:
        by[q.get("qk") or q.get("kind")].append(q)
    for k, v in sorted(by.items()):
        ok = [q for q in v if q["ok"]]
        print(f"   {k:<13} tried {len(v):>3} done {pct(len(ok), len(v)):>4} | avg {mean(q['days'] for q in ok):.1f} days when done | letters {dict(collections.Counter(q['letter'] for q in v))}")
    guild_xp = s["xp_src"].get("guild", 0)
    print(f"   contract XP {guild_xp:,} ({pct(guild_xp, sum(s['xp_src'].values()))} of all XP) | contract coin {s['income'].get('guild', 0) / 100:,.0f} silver")

head("5b. DUNGEONS")
for c in CLASSES:
    ds = S[c]["dungeons"]
    done = [d for d in ds if d["result"] == "done"]
    died = [d for d in ds if d["result"] == "died"]
    print(f"\n{c}: {len(ds)} delves | cleared {len(done)} | died in {len(died)} | unfinished {len(ds) - len(done) - len(died)}")
    for d in ds[:60:max(1, len(ds) // 10)]:
        print(f"   {d['dungeon'][:30]:<30} {d.get('theme', '?'):<7} {d.get('letters', ''):<12} lv{d['lv']:>2} {d['kind']:<13} {d['result']} {d.get('days', '')}")

# ---------------------------------------------------------------- 6. travel
head("6. TRAVERSAL: DOES GOING SOMEWHERE MEAN SOMETHING?")
for c in CLASSES:
    s = S[c]
    tr = s["travel"]
    tmin = sum(t["min"] for t in tr)
    tot = sum(s["cat_minutes"].values()) or 1
    wild = [t for t in tr if t.get("wild")]
    print(f"\n{c}: {len(tr)} trips | {100 * s['cat_minutes'].get('travel', 0) / tot:.0f}% of game time spent walking | "
          f"avg trip {mean(t['min'] for t in tr) / 60:.1f}h | longest {max((t['min'] for t in tr), default=0) / 60:.0f}h")
    print(f"   trips ending in the wild: {len(wild)} of {len(tr)}; of those {pct(sum(t.get('enc', False) for t in wild), len(wild))} met something on arrival")
    long_ = [t for t in tr if t["min"] >= 480]
    print(f"   trips of 8+ hours: {len(long_)} - of which wild-bound met a fight: {pct(sum(t.get('enc', False) for t in long_ if t.get('wild')), len([t for t in long_ if t.get('wild')]))}; "
          f"town-bound (nothing on the way): {len([t for t in long_ if not t.get('wild')])}")
    print(f"   blocked by a closed route: {s['blocked']} times")
    vis = {k: v for k, v in s["visited"].items() if not k.startswith("_")}
    never = [p for p, pl in W.places.items() if p not in vis and p != s["visited"] and pl.type != "dungeon" and not p.startswith("dungeon_")]
    print(f"   places visited: {len(vis)} | never visited: {', '.join(sorted(never)[:14])}")
    order = sorted(vis.items(), key=lambda kv: kv[1]["day"])
    print("   first visits: " + ", ".join(f"{p}(d{v['day']},L{v['lv']})" for p, v in order[:22]))

# ---------------------------------------------------------------- 7. zones
head("7. DO THE WILD PLACES FEEL DIFFERENT? (what the bots actually met and got, pooled across classes)")
zone = collections.defaultdict(list)
for c in CLASSES:
    for f in S[c]["fights"]:
        zone[f["place"]].append(f)
print(f"{'place':<22}{'danger':>9}{'fights':>7}{'creatures':>10}{'xp/fight':>9}{'coin/f':>8}{'loot/f':>7}{'rare+':>6}{'win%':>6}{'foe-lv':>7}  most common")
for pid, fs in sorted(zone.items(), key=lambda kv: (W.places[kv[0]].danger or (0, 0))[0] if kv[0] in W.places else 0):
    if pid not in W.places or not W.places[pid].danger:
        continue
    kinds = collections.Counter(x[0] for f in fs for x in f["foes"])
    items_ = [i for f in fs for i in f["items"]]
    rare = sum(1 for r, _ in items_ if r in ("rare", "epic", "legendary"))
    d = W.places[pid].danger
    print(f"{pid:<22}{str(d[0]) + '-' + str(d[1]):>9}{len(fs):>7}{len(kinds):>10}{mean(f['xp'] for f in fs):>9.0f}{mean(f['coins'] for f in fs):>8.0f}"
          f"{len(items_) / len(fs):>7.2f}{rare:>6}{pct(sum(f['outcome'] == 'victory' for f in fs), len(fs)):>6}{mean(mean(x[1] for x in f['foes']) for f in fs):>7.0f}  "
          f"{', '.join(k for k, _ in kinds.most_common(3))}")
allk = collections.Counter(x[0] for c in CLASSES for f in S[c]["fights"] for x in f["foes"])
tot = sum(allk.values())
print(f"\ncreature kinds met overall: {len(allk)} of {len(W.bestiary)} | top 5 account for {100 * sum(n for _, n in allk.most_common(5)) / tot:.0f}% of all enemies: "
      + ", ".join(f"{k} {100 * n / tot:.0f}%" for k, n in allk.most_common(5)))
for c in CLASSES:
    seen, curve = set(), []
    fs = S[c]["fights"]
    for i, f in enumerate(fs, 1):
        seen |= {x[0] for x in f["foes"]}
        if i in (50, 200, 500, 1000, 2000, 4000):
            curve.append(f"{i}:{len(seen)}")
    print(f"   {c}: distinct creature kinds after N fights -> {' '.join(curve)}")

head("7b. LEVEL COVERAGE: how many places are worth visiting at each level?")
cov = {}
for lv in range(1, 76):
    z = [p.id for p in W.places.values() if p.danger and p.type != "dungeon" and p.id != "cracked_plains" and p.danger[0] <= lv <= p.danger[1]]
    cov[lv] = z
thin = [lv for lv, z in cov.items() if len(z) <= 1]
print("levels with only one zone (or none) in range:", thin)
print("level ranges by zone:", ", ".join(f"{p.id} {p.danger[0]}-{p.danger[1]}" for p in sorted((p for p in W.places.values() if p.danger and p.type != 'dungeon'), key=lambda p: p.danger[0])))
for lv in (5, 15, 25, 35, 45, 55, 65, 75):
    print(f"   level {lv}: {', '.join(cov[lv]) or 'nothing'}")

# ---------------------------------------------------------------- 8. static survey
head("8. THE WORLD AS GENERATED: how alike are places?")
def jac(a, b):
    return len(a & b) / len(a | b) if a | b else 0
sim_by_class = {}
for c in CLASSES:
    sv = S[c].get("survey", {})
    wild = {p: set(r["roster"]) for p, r in sv.items() if r.get("roster")}
    pairs = [(jac(wild[a], wild[b]), a, b) for a, b in itertools.combinations(wild, 2)]
    sim_by_class[c] = pairs
    print(f"\n{c} (seed {S[c]['seed']}): wild-zone rosters: mean overlap between two zones {mean(p[0] for p in pairs):.2f}; most alike: " +
          ", ".join(f"{a}/{b} {j:.2f}" for j, a, b in sorted(pairs, reverse=True)[:3]))
    for p, r in sorted(sv.items(), key=lambda kv: (kv[1].get("danger") or (0, 0))[0]):
        if r.get("roster"):
            others = set().union(*[wild[q] for q in wild if q != p]) if len(wild) > 1 else set()
            uniq = len(wild[p] - others)
            print(f"   {p:<22} {len(r['roster'])} kinds, {uniq} found nowhere else | {r['categories']}")
print("\nSame place, different campaigns (roster overlap between seeds):")
for p in [p for p, pl in W.places.items() if pl.danger and pl.type != "dungeon" and p != "cracked_plains"]:
    rs = [set(S[c]["survey"][p]["roster"]) for c in CLASSES if S[c].get("survey", {}).get(p, {}).get("roster")]
    if len(rs) > 1:
        print(f"   {p:<22} mean overlap {mean(jac(a, b) for a, b in itertools.combinations(rs, 2)):.2f}")

head("8b. TOWNS: what each settlement offers")
c0 = CLASSES[0]
sv = S[c0].get("survey", {})
tows = {p: r for p, r in sv.items() if r.get("residents") is not None and r.get("type") != "dungeon"}
def tokens(r):
    return {f"role:{k}" for k, _ in r["residents"]} | {f"ware:{w}" for w in r.get("wares", [])} | {f"st:{s}" for s in r.get("stations", [])} | \
           {f"people:{k}" for k, _ in r.get("peoples", [])}
tt = {p: tokens(r) for p, r in tows.items()}
pairs = sorted(((jac(tt[a], tt[b]), a, b) for a, b in itertools.combinations(tt, 2)), reverse=True)
print(f"{len(tows)} settlements/places with people. mean overlap of offerings between two settlements: {mean(p[0] for p in pairs):.2f}")
print("most alike: " + ", ".join(f"{a}/{b} {j:.2f}" for j, a, b in pairs[:5]))
print(f"\n{'place':<18}{'type':<8}{'people':>7}{'roles':>7}{'trade lv':>10}{'stock':>6}{'best item lv':>13}{'top rarity':>11}{'avg price(s)':>13}")
order = {"common": 1, "uncommon": 2, "rare": 3, "epic": 4}
for p, r in sorted(tows.items(), key=lambda kv: (kv[1].get("trade") or [0, 0])[0]):
    if not r.get("residents"):
        continue
    stock = r.get("stock", [])
    best = max((x[2] for x in stock), default=0)
    top = max((x[1] for x in stock), key=lambda q: order.get(q, 0), default="-")
    ap = mean(x[3] for x in stock) / 100 if stock else 0
    print(f"{p:<18}{r['type']:<8}{sum(n for _, n in r['residents']):>7}{len(r['residents']):>7}{str(r.get('trade')):>10}{len(stock):>6}{best:>13}{top:>11}{ap:>13.0f}")
print("\nCan a character find gear at their level? (best stock item level available anywhere)")
best_any = max((x[2] for r in tows.values() for x in r.get("stock", [])), default=0)
for lv in (10, 25, 40, 55, 70):
    ok = [p for p, r in tows.items() if any(x[2] >= lv * 0.8 for x in r.get("stock", []))]
    print(f"   level {lv}: {len(ok)} towns sell gear within 80% of that level ({', '.join(ok[:5])})")
print(f"   highest-level item for sale anywhere: {best_any}")

# ---------------------------------------------------------------- 9. alive
head("9. DOES THE WORLD MOVE WHILE YOU PLAY?")
for c in CLASSES:
    arr = [e for e in events(c) if e["k"] == "arrival"]
    s = S[c]["pulse"]
    nothing = [a for a in arr if a["happenings"] == 0 and a["news"] == 0 and a["price"] == 1.0]
    print(f"\n{c}: town arrivals {len(arr)} | something going on (situation/news/price change): {pct(len(arr) - len(nothing), len(arr))} | "
          f"with a visible situation {pct(sum(a['happenings'] > 0 for a in arr), len(arr))} | with news to hear {pct(sum(a['news'] > 0 for a in arr), len(arr))} | "
          f"prices off normal {pct(sum(a['price'] != 1.0 for a in arr), len(arr))}")
    print(f"   pulse: {s['threads']} situations {s['by_tier']} outcomes {s['by_status']} | history {s['history']} | news {s['news']} | live effects {s['effects_live']}")
    print(f"   people: {s['npcs_total']} generated, {s['npcs_met']} met, {s['npcs_with_motive']} with an active motive, {s['moods']} with a mood, {s['relations']} relationships | gone: {len(s['npcs_gone'])}")
    print(f"   campaign-defining events: {len(s.get('campaign_events', []))}; reputation: {s.get('reputation')}")

# ---------------------------------------------------------------- 10. bugs
head("10. BUGS AND ERRORS")
agg = collections.defaultdict(lambda: {"n": 0, "classes": set(), "ex": None})
for c in CLASSES:
    for k, v in S[c]["exceptions"].items():
        a = agg[k.split("@")[0][:110]]
        a["n"] += v["n"]; a["classes"].add(c); a["ex"] = a["ex"] or v
for k, a in sorted(agg.items(), key=lambda kv: -kv[1]["n"]):
    print(f"{a['n']:>5}x [{','.join(sorted(a['classes']))}] {k}")
    print("        " + " | ".join(l.strip() for l in a['ex']['tb'].splitlines()[-4:])[:300])
print("\ninvariant violations:", {c: {k: (v['n'], v['example']) for k, v in S[c]['violations'].items()} for c in CLASSES})

head("11. MODEL CALLS (the real-time cost with a local model)")
for c in CLASSES:
    calls = S[c]["stub_calls"]
    tot = sum(calls.values())
    print(f"{c}: {tot:,} requests over {S[c]['day']} game days / {S[c]['steps']} steps: " + ", ".join(f"{k} {v:,}" for k, v in sorted(calls.items(), key=lambda kv: -kv[1])[:6]))
print("(at roughly 2-4 seconds per call on a local 12B model, 100,000 calls is 55-110 hours of waiting)")

# ---------------------------------------------------------------- 12. the end game
head("12. END GAME (levels 100-150): is it too easy?")
FAR = {"ash_wastes", "cinder_caldera", "stormcrown_heights", "thunder_spires", "deep_roads_tunnels", "lightless_deep",
       "drowned_shore", "jade_maw_jungle", "sepulchre_fields"}
print(f"{'class':<9} {'d100':>5} {'d125':>5} {'d150':>5} | deaths 1-99 / 100+ | rank S? | far kills | hall | legendaries | coin(gold)")
for c in CLASSES:
    s = S[c]; ms = s["milestones"]
    d = lambda lv: (MS[c].get(lv) or ("-",))[0]
    late = [x for x in s["deaths"] if x.get("lv", 0) >= 100]
    far = sum(n for k, n in s["kills_by_place"].items() if k.replace("dungeon_", "") in FAR)
    hall = next((e.get("hall") for e in events(c) if e["k"] == "moved_hall"), "-")
    ranks = [e["rank"] for e in events(c) if e["k"] == "tick" and e.get("rank")]
    print(f"{c:<9} {d(100):>5} {d(125):>5} {d(150):>5} | {len(s['deaths']) - len(late):>9} / {len(late):<5} | {s['rank'] or '-':>7} | {far:>9} | {str(hall):<16} | {len(s['legendaries']):>4} | {s['coins'] / 10000:,.0f}")

print("\nHow hard the fights are, by band (pooled over classes): win%, fled%, died%, avg rounds, avg health lost, foe level vs yours")
for b in BANDS:
    fs = [f for c in CLASSES for f in S[c]["fights"] if b[0] <= f["lv"] < b[1]]
    if not fs: continue
    rel = mean(mean(x[1] for x in f["foes"]) - f["lv"] for f in fs)
    print(f"  {band_name(b):>8} n={len(fs):>5} win {pct(sum(f['outcome'] == 'victory' for f in fs), len(fs)):>4} fled {pct(sum(f['outcome'] == 'fled' for f in fs), len(fs)):>4} "
          f"died {pct(sum(f['outcome'] == 'defeat' for f in fs), len(fs)):>4} rounds {mean(f['rounds'] for f in fs):>5.1f} hp-lost {100 * mean(f['hp_lost'] for f in fs):>3.0f}% "
          f"rating {mean(f['rating'] for f in fs):>4.2f} foe {rel:+.1f}")

print("\nPer class, fights at level 100+: n, win%, avg health lost, share of fights that cost under 25% health, deaths")
for c in CLASSES:
    fs = [f for f in S[c]["fights"] if f["lv"] >= 100]
    if not fs: print(f"  {c:<9} none"); continue
    easy = sum(1 for f in fs if f["hp_lost"] < 0.25)
    print(f"  {c:<9} n={len(fs):>4} win {pct(sum(f['outcome'] == 'victory' for f in fs), len(fs)):>4} hp-lost {100 * mean(f['hp_lost'] for f in fs):>3.0f}% easy {pct(easy, len(fs)):>4} "
          f"deaths {sum(1 for x in S[c]['deaths'] if x.get('lv', 0) >= 100)} rounds {mean(f['rounds'] for f in fs):.1f}")

print("\nWhat they died to at level 100+ (pooled):")
foes = collections.Counter()
for c in CLASSES:
    for x in S[c]["deaths"]:
        if x.get("lv", 0) >= 100:
            for f in x["foes"][:1]:
                foes[f[0]] += 1
print("  " + (", ".join(f"{k} {n}" for k, n in foes.most_common(12)) or "none"))

print("\nGear at the end (slot: rarity, item level), and what was found over the run:")
for c in CLASSES:
    s = S[c]
    eq = ", ".join(f"{k}:{v[1][:3]}{v[2]}" for k, v in s["equipment"].items())
    print(f"  {c:<9} {eq}")
    print(f"            found {dict(s['rarity_found'])} | legendaries {[(l['name'], l['base'], l['effect'], 'lv' + str(l['lv'])) for l in s['legendaries']][:5]}")

print("\nWealth: homes and relics bought, coin at the end")
for c in CLASSES:
    s = S[c]
    print(f"  {c:<9} homes {s['homes']} relics {s['relics']} wealth buys {[(w[0], w[1]) for w in s['wealth_buys']]} coin {s['coins'] / 10000:,.0f} gold")

print("\nMana (casters) and parties/camps")
for c in CLASSES:
    s = S[c]
    m = s["mana"]
    print(f"  {c:<9} mana: hit empty in {m.get('fights_hit_empty', 0)}/{m.get('fights', 0)} fights, dry-round share {m.get('dry_round_share', 0):.2f}, avg low point {m.get('avg_low_point', 0):.2f} | "
          f"party fell {s['party'].get('fell', 0)} | camps {s['camp'].get('tries', 0)}")
