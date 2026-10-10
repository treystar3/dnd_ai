"""Stats document for one bot run.

    python tools/runstats.py <sim_out dir> <class> [compare_dir] > report.md

Reads <dir>/<class>.jsonl and <class>_summary.json written by simbot.py. If the run used SIM_IMMORTAL=1, "would have died" counts come from
the would_die events; otherwise real deaths are used. compare_dir (optional) adds a before/after table for a second run of the same class.
"""
import collections
import json
import statistics as st
import sys
from pathlib import Path

BANDS = [(1, 24), (25, 49), (50, 74), (75, 99), (100, 124), (125, 160)]


def band_of(lv):
    for a, b in BANDS:
        if a <= lv <= b:
            return f"{a}-{b}"
    return f"{BANDS[-1][0]}+"


def load(d, cls):
    rows = [json.loads(l) for l in open(Path(d) / f"{cls}.jsonl")]
    summ = json.load(open(Path(d) / f"{cls}_summary.json"))
    return rows, summ


def pct(a, b):
    return f"{a / b:.0%}" if b else "-"


def table(head, rows):
    out = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return "\n".join(out)


def fight_stats(rows):
    fights = [r for r in rows if r["k"] == "fight" and r.get("foes")]
    for f in fights:
        f["gap"] = max(x[1] for x in f["foes"]) - f["lv"]
        f["band"] = band_of(f["lv"])
        f["would"] = f.get("would_die", 0)
    return fights


def gap_bucket(g):
    return "higher (+4 or more)" if g >= 4 else "near (-3 to +3)" if g >= -3 else "lower (-4 to -10)" if g >= -10 else "far lower (below -10)"


def summarize(d, cls):
    rows, s = load(d, cls)
    fights = fight_stats(rows)
    return rows, s, fights


def core_metrics(fights):
    near = [f for f in fights if f["gap"] >= -3]
    hi = [f for f in fights if f["gap"] >= 4]
    return dict(fights=len(fights), near=len(near), near_trivial=sum(f["label"] == "trivial" for f in near),
                near_would=sum(1 for f in near if f["would"]), near_fled=sum(f["outcome"] == "fled" for f in near),
                avg_gap=st.mean(f["gap"] for f in fights) if fights else 0)


def main():
    d, cls = sys.argv[1], sys.argv[2]
    cmp_dir = sys.argv[3] if len(sys.argv) > 3 else None
    rows, s, fights = summarize(d, cls)
    immortal = bool(s.get("would_deaths")) or any(r["k"] == "would_die" for r in rows)
    would = [r for r in rows if r["k"] == "would_die"]
    out = []
    w = out.append
    ticks = [r for r in rows if r["k"] == "tick"]
    w(f"# Bot run report: {cls}, level 1 to {s['level']}\n")
    w(f"{s['end'].capitalize()}. {s['day']} in-game days, {s['steps']:,} actions, {s['secs'] // 60} minutes of real time to simulate. Guild rank {s['rank']}. "
      f"Mode: {'immortal (the bot cannot die; each would-be death is recorded and the bot carries on at 30% health)' if immortal else 'normal'}.\n")
    # --- overview
    w("## 1. Would-have-died\n")
    nd = len(would)
    w(f"The bot would have died in **{nd or len(s['deaths'])} fights** out of {len(fights):,} ({pct(nd, len(fights))}). "
      f"Once revived at 30% health it can be knocked out again in the same fight; counting every knock-out gives {sum(x['times'] for x in would) if would else 0:,} in total.\n")
    if would:
        wb = collections.Counter(band_of(x["lv"]) for x in would)
        fb = collections.Counter(f["band"] for f in fights)
        w(table(["Level band", "Fights", "Fights with a would-be death", "Rate", "Of those: won anyway", "Fled", "Lost"],
                [[b, fb[b], wb[b], pct(wb[b], fb[b]),
                  sum(1 for x in would if band_of(x["lv"]) == b and x["outcome"] == "victory"),
                  sum(1 for x in would if band_of(x["lv"]) == b and x["outcome"] == "fled"),
                  sum(1 for x in would if band_of(x["lv"]) == b and x["outcome"] not in ("victory", "fled"))] for b in [f"{a}-{c}" for a, c in BANDS] if fb[b]]))
        w("\nBy what the bot expected: the pre-fight rating of fights that would have killed it.\n")
        rc = collections.Counter(x.get("rate", 0) >= 0.97 and "rated trivial" or x.get("rate", 0) >= 0.55 and "rated even or better" or "rated dangerous or deadly" for x in would)
        w(table(["Pre-fight rating", "Would-be deaths"], [[k, v] for k, v in rc.most_common()]))
        w("\nCreatures behind the most would-be deaths (level 50+):\n")
        cc = collections.Counter()
        for x in would:
            if x["lv"] >= 50:
                cc[x["foes"][0][0]] += 1
        w(table(["Creature", "Would-be deaths"], [[k.replace('_', ' '), v] for k, v in cc.most_common(12)]))
        w("\nPlaces behind the most would-be deaths (level 50+):\n")
        pc = collections.Counter(x["place"] for x in would if x["lv"] >= 50)
        w(table(["Place", "Would-be deaths"], [[k.replace('_', ' '), v] for k, v in pc.most_common(10)]))
        w("\nEvery would-be death at level 100 or higher:\n")
        w(table(["Day", "Level", "Place", "Foes", "Rating", "Result"],
                [[x["d"], x["lv"], x["place"].replace('_', ' '), ", ".join(f"{f[0].replace('_', ' ')} L{f[1]} {f[2]}" for f in x["foes"][:3]), x.get("rate"), x["outcome"]]
                 for x in would if x["lv"] >= 100][:40]))
    # --- variety
    w("\n## 2. Enemy variety\n")
    kinds = collections.Counter(f[0] for r in fights for f in r["foes"])
    w(f"The bot fought **{len(kinds)} different creature kinds** over {sum(kinds.values()):,} enemies.\n")
    vb = collections.defaultdict(set)
    nb = collections.Counter()
    for r in fights:
        for f in r["foes"]:
            vb[r["band"]].add(f[0]); nb[r["band"]] += 1
    w(table(["Level band", "Fights", "Enemies", "Distinct kinds"], [[b, sum(1 for r in fights if r["band"] == b), nb[b], len(vb[b])] for b in [f"{a}-{c}" for a, c in BANDS] if nb[b]]))
    rk = collections.Counter(f[2] for r in fights for f in r["foes"])
    w(f"\nRanks: {', '.join(f'{k} {v}' for k, v in rk.most_common())}. Fights against a group of 2 or more: {pct(sum(len(r['foes']) >= 2 for r in fights), len(fights))}.\n")
    w("Most-fought creatures at level 100 and above:\n")
    hc = collections.Counter(f[0] for r in fights if r["lv"] >= 100 for f in r["foes"])
    w(table(["Creature", "Fights"], [[k.replace('_', ' '), v] for k, v in hc.most_common(15)]))
    zc = collections.Counter(r["place"] for r in fights if r["lv"] >= 100)
    w("\nWhere it fought at level 100 and above:\n")
    w(table(["Place", "Fights"], [[k.replace('_', ' '), v] for k, v in zc.most_common(12)]))
    # --- outleveling
    w("\n## 3. How often it outleveled its opponents\n")
    w("Gap = strongest enemy's level minus the bot's level.\n")
    heads = ["Level band", "Fights", "Avg gap", "Higher (+4 or more)", "Near (-3 to +3)", "Lower (-4 to -10)", "Far lower (below -10)", "Near-level fights rated trivial"]
    trs = []
    for a, c in BANDS:
        b = f"{a}-{c}"
        fs = [f for f in fights if f["band"] == b]
        if not fs:
            continue
        cnt = collections.Counter(gap_bucket(f["gap"]) for f in fs)
        nr = [f for f in fs if f["gap"] >= -3]
        trs.append([b, len(fs), f"{st.mean(f['gap'] for f in fs):+.1f}"] + [pct(cnt[k], len(fs)) for k in ("higher (+4 or more)", "near (-3 to +3)", "lower (-4 to -10)", "far lower (below -10)")] + [pct(sum(f["label"] == "trivial" for f in nr), len(nr)) + f" of {len(nr)}"])
    w(table(heads, trs))
    allc = collections.Counter(gap_bucket(f["gap"]) for f in fights)
    w(f"\nOver the whole run: {pct(allc['higher (+4 or more)'], len(fights))} of fights were against stronger enemies, {pct(allc['near (-3 to +3)'], len(fights))} near its own level, "
      f"{pct(allc['lower (-4 to -10)'], len(fights))} somewhat lower and {pct(allc['far lower (below -10)'], len(fights))} far lower.\n")
    # --- how fights went
    w("\n## 4. How the fights went\n")
    heads = ["Level band", "Won", "Fled", "Lost*", "Rated trivial", "Median health lost (wins)", "Fights with a would-be death"]
    trs = []
    for a, c in BANDS:
        b = f"{a}-{c}"
        fs = [f for f in fights if f["band"] == b]
        if not fs:
            continue
        hp = sorted(f["hp_lost"] for f in fs if f["outcome"] == "victory")
        trs.append([b, pct(sum(f["outcome"] == "victory" for f in fs), len(fs)), pct(sum(f["outcome"] == "fled" for f in fs), len(fs)),
                    pct(sum(f["outcome"] not in ("victory", "fled") for f in fs), len(fs)), pct(sum(f["label"] == "trivial" for f in fs), len(fs)),
                    f"{hp[len(hp) // 2]:.0%}" if hp else "-", pct(sum(1 for f in fs if f["would"]), len(fs))])
    w(table(heads, trs))
    w("\n*Lost: in immortal mode the bot is kept alive, so a fight it would have lost shows as won or fled; see the would-have-died column.\n")
    lab = collections.Counter(f["label"] for f in fights)
    w("\nPre-fight rating of all fights: " + ", ".join(f"{k} {pct(v, len(fights))}" for k, v in lab.most_common()) + ".\n")
    # --- quests
    w("\n## 5. Quest completion\n")
    taken = [r for r in rows if r["k"] == "quest_taken"]
    runs = [r for r in rows if r["k"] == "quest_run"]
    qs = s["quests"]
    w(f"Quests taken: {len(taken)}. Quest attempts run: {len(runs)} ({pct(sum(1 for r in runs if r.get('ok')), len(runs))} succeeded). Guild contracts completed by rank: "
      + ", ".join(f"{k} {v}" for k, v in s["guild_done"].items()) + f" (total {sum(s['guild_done'].values())}).\n")
    kinds_q = collections.defaultdict(lambda: [0, 0, 0.0])
    for q in qs:
        k = kinds_q[q["kind"]]
        k[0] += 1; k[1] += bool(q.get("ok")); k[2] += q.get("days", 0)
    w(table(["Quest kind", "Attempted", "Succeeded", "Success rate", "Avg days"], [[k, v[0], v[1], pct(v[1], v[0]), f"{v[2] / v[0]:.1f}"] for k, v in sorted(kinds_q.items(), key=lambda t: -t[1][0])]))
    tk = collections.Counter(r["qk"] for r in taken)
    w("\nQuests taken by kind: " + ", ".join(f"{k} {v}" for k, v in tk.most_common()) + ".\n")
    dg = s["dungeons"]
    if dg:
        w(f"Dungeon runs: {len(dg)} ({sum(1 for x in dg if x['result'] == 'done')} completed). Hunts given up on: {sum(1 for r in rows if r['k'] == 'hunt_gaveup')}.\n")
    # --- progression
    w("\n## 6. Progression pace\n")
    ms = s["milestones"]
    w(table(["Level", "Day", "Actions", "Real seconds"], [[k, v["day"], f"{v['steps']:,}", v["secs"]] for k, v in ms.items()]))
    xs = s["xp_src"]; tx = sum(xs.values())
    w("\nWhere experience came from: " + ", ".join(f"{k} {pct(v, tx)}" for k, v in sorted(xs.items(), key=lambda t: -t[1])[:6]) + ".\n")
    cm = s["cat_minutes"]; tm = sum(cm.values())
    w("Where in-game time went: " + ", ".join(f"{k} {pct(v, tm)}" for k, v in sorted(cm.items(), key=lambda t: -t[1])[:7]) + ".\n")
    # --- gear
    w("\n## 7. Gear and economy\n")
    gears = [r for r in rows if r["k"] == "gear"]
    bought = [r for r in rows if r["k"] == "bought"]
    gb = collections.Counter(band_of(r["lv"]) for r in gears)
    bb = collections.Counter(band_of(r["lv"]) for r in bought)
    w(table(["Level band", "Gear swaps", "Items bought", "Avg bought item level vs own level"],
            [[f"{a}-{c}", gb[f"{a}-{c}"], bb[f"{a}-{c}"], f"{st.mean(r['lvl'] - r['lv'] for r in bought if band_of(r['lv']) == f'{a}-{c}'):+.0f}" if bb[f"{a}-{c}"] else "-"] for a, c in BANDS]))
    gd = s["gear_detail"]
    il = [v["ilvl"] for v in gd.values() if isinstance(v, dict) and "ilvl" in v]
    if il:
        w(f"\nWorn gear at the end: {len(il)} pieces, average item level {st.mean(il):.0f} (bot level {s['level']}). Enchants applied: {len(s['enchants'])}. Rarity of items found: "
          + ", ".join(f"{k} {v}" for k, v in sorted(s['rarity_found'].items(), key=lambda t: -t[1])) + ".\n")
    w(f"Gold at the end: {s['coins'] / 10000:,.0f}. Titles: {', '.join(s['titles']) or 'none'}.\n")
    # --- compare
    if cmp_dir:
        rows2, s2, f2 = summarize(cmp_dir, cls)
        a, b = core_metrics([f for f in f2 if f["lv"] >= 75]), core_metrics([f for f in fights if f["lv"] >= 75])
        w(f"\n## 8. Compared with the earlier {cls} run ({cmp_dir}), levels 75 and up\n")
        w(table(["Measure", "Earlier run", "This run"], [
            ["Fights", a["fights"], b["fights"]],
            ["Average gap (enemy level minus own)", f"{a['avg_gap']:+.1f}", f"{b['avg_gap']:+.1f}"],
            ["Near-level fights", a["near"], b["near"]],
            ["Near-level fights rated trivial", pct(a["near_trivial"], a["near"]), pct(b["near_trivial"], b["near"])],
            ["Near-level fights fled", pct(a["near_fled"], a["near"]), pct(b["near_fled"], b["near"])],
            ["Real deaths / would-be deaths (whole run)", len(s2["deaths"]), len(would) or len(s["deaths"])],
            ["Days to level 150", s2["day"], s["day"]]]))
    w("\n## Notes\n")
    w("- A would-be death is any moment the bot's health reached zero. The fight then continued at 30% health, so a fight can show several.")
    w("- The bot is a stand-in for a competent player: it enchants gear, uses relics and abilities, and flees fights it rates deadly, so it is stronger than an average-gear player.")
    w("- The language model is stubbed in the simulation, so dialogue and story choices are not tested here.")
    print("\n".join(out))


if __name__ == "__main__":
    main()
