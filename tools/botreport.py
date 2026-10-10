"""Reads a folder of finished bot runs (default sim_out) and answers: are the bots fighting their own level, how many fights are rated
trivial, and do they swap gear as they go.

    python tools/botreport.py [folder] [compare_folder]
"""
import collections, json, statistics as st, sys
from pathlib import Path

BANDS = [(1, 10), (10, 25), (25, 50), (50, 75), (75, 100), (100, 125), (125, 151)]
CLASSES = "warrior paladin monk ranger smith mage warlock priest bard summoner".split()


def load(folder):
    out = {}
    for c in CLASSES:
        sp, ep = Path(folder) / f"{c}_summary.json", Path(folder) / f"{c}.jsonl"
        if not sp.exists():
            continue
        summ = json.loads(sp.read_text())
        ev = [json.loads(l) for l in ep.open()] if ep.exists() else []
        out[c] = (summ, ev)
    return out


def fights_of(summ, ev):
    f = [dict(e, lv=e["lv"]) for e in ev if e["k"] == "fight"]
    return f or summ["fights"]


def foe_level(f):
    lv = [x[1] for x in f["foes"] if len(x) > 1]
    return max(lv) if lv else None


def pct(a, b):
    return f"{100 * a / b:>3.0f}%" if b else "  - "


def band_of(lv):
    return next((b for b in BANDS if b[0] <= lv < b[1]), BANDS[-1])


def level_section(data):
    print("\nENEMY LEVEL vs YOUR LEVEL (strongest foe in each fight; 'near' = within 3 levels)")
    print(f"{'class':<9}{'fights':>7}{'near':>6}{'lower':>7}{'higher':>8}{'avg gap':>9}")
    allg = []
    for c, (s, ev) in data.items():
        fs = [f for f in fights_of(s, ev) if foe_level(f) is not None]
        gaps = [foe_level(f) - f["lv"] for f in fs]
        allg += gaps
        print(f"{c:<9}{len(fs):>7}{pct(sum(abs(g) <= 3 for g in gaps), len(gaps)):>6}{pct(sum(g < -3 for g in gaps), len(gaps)):>7}"
              f"{pct(sum(g > 3 for g in gaps), len(gaps)):>8}{st.mean(gaps):>9.1f}")
    print(f"{'ALL':<9}{len(allg):>7}{pct(sum(abs(g) <= 3 for g in allg), len(allg)):>6}{pct(sum(g < -3 for g in allg), len(allg)):>7}"
          f"{pct(sum(g > 3 for g in allg), len(allg)):>8}{st.mean(allg):>9.1f}")
    print("\n  by level band (all classes): fights, near-level %, avg gap")
    for b in BANDS:
        gaps = [foe_level(f) - f["lv"] for c, (s, ev) in data.items() for f in fights_of(s, ev) if foe_level(f) is not None and band_of(f["lv"]) == b]
        if gaps:
            print(f"    {b[0]:>3}-{b[1] - 1:<3} {len(gaps):>5}  near {pct(sum(abs(g) <= 3 for g in gaps), len(gaps))}  avg gap {st.mean(gaps):>5.1f}")


def label_section(data, title="HOW FIGHTS WERE RATED (the bot's pre-fight estimate)"):
    print(f"\n{title}")
    labels = ["trivial", "favorable", "even", "dangerous", "deadly"]
    print(f"{'class':<9}" + "".join(f"{l:>11}" for l in labels) + f"{'win':>6}{'fled':>6}{'died':>6}")
    tot = collections.Counter()
    out = collections.Counter()
    for c, (s, ev) in data.items():
        fs = fights_of(s, ev); n = len(fs)
        cnt = collections.Counter(f["label"] for f in fs); oc = collections.Counter(f["outcome"] for f in fs)
        tot.update(cnt); out.update(oc)
        print(f"{c:<9}" + "".join(f"{pct(cnt[l], n):>11}" for l in labels) + f"{pct(oc['victory'], n):>6}{pct(oc['fled'], n):>6}{pct(oc['defeat'], n):>6}")
    n = sum(tot.values())
    print(f"{'ALL':<9}" + "".join(f"{pct(tot[l], n):>11}" for l in labels) + f"{pct(out['victory'], n):>6}{pct(out['fled'], n):>6}{pct(out['defeat'], n):>6}")
    print("\n  trivial % by level band (all classes), and when the foe is within 3 levels of you")
    for b in BANDS:
        fs = [f for c, (s, ev) in data.items() for f in fights_of(s, ev) if band_of(f["lv"]) == b]
        near = [f for f in fs if foe_level(f) is not None and abs(foe_level(f) - f["lv"]) <= 3]
        if fs:
            print(f"    {b[0]:>3}-{b[1] - 1:<3} fights {len(fs):>5}  trivial {pct(sum(f['label'] == 'trivial' for f in fs), len(fs))}"
                  f"   near-level fights {len(near):>4}: trivial {pct(sum(f['label'] == 'trivial' for f in near), len(near))}")


def gear_section(data):
    print("\nGEAR CHANGES (equip passes that swapped something in, and items bought)")
    print(f"{'class':<9}{'levels':>7}{'swap events':>12}{'items swapped':>14}{'per 10 lv':>10}{'bought':>8}{'enchants':>9}{'worn avg ilvl':>14}{'gap to lvl':>11}")
    for c, (s, ev) in data.items():
        gears = [e for e in ev if e["k"] == "gear"]
        swapped = sum(e.get("n", 1) for e in gears)
        lv = s["level"]
        worn = [v["ilvl"] for v in s["gear_detail"].values()] if isinstance(s.get("gear_detail"), dict) else []
        avg = st.mean(worn) if worn else 0
        print(f"{c:<9}{lv:>7}{len(gears):>12}{swapped:>14}{swapped / max(1, lv / 10):>10.1f}{sum(e['k'] == 'bought' for e in ev):>8}"
              f"{sum(e['k'] == 'enchant' and e.get('ok') for e in ev):>9}{avg:>14.0f}{avg - lv:>11.0f}")
    print("\n  swap events by level band (all classes)")
    for b in BANDS:
        n = sum(1 for c, (s, ev) in data.items() for e in ev if e["k"] == "gear" and band_of(e["lv"]) == b)
        i = sum(e.get("n", 1) for c, (s, ev) in data.items() for e in ev if e["k"] == "gear" and band_of(e["lv"]) == b)
        print(f"    {b[0]:>3}-{b[1] - 1:<3} {n:>4} events, {i:>4} items")


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "sim_out"
    data = load(folder)
    print(f"{len(data)} classes in {folder}: " + ", ".join(f"{c} lv{s['level']}" for c, (s, e) in data.items()))
    level_section(data)
    label_section(data)
    gear_section(data)
    if len(sys.argv) > 2:
        old = load(sys.argv[2])
        label_section(old, f"FOR COMPARISON: {sys.argv[2]}")


if __name__ == "__main__":
    main()
